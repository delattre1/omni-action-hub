"""Scoped gateway over the unmodified, image-bundled Plow transport.

We replace only the supervised gateway entrypoint, not the upstream plugin
files or the base's identity/credential bootstrap. There is no general LLM
dispatch and no model-accessible shell, browser, or credential tool.
"""
import asyncio
import fcntl
import importlib.util
import logging
import os
import signal
import sys
from pathlib import Path

import httpx

from .clients import Gemini, Linear
from .environment import load_runtime_environment
from .media import MediaResolver
from .models import Problem, Settings
from .store import Store
from .workflow import Workflow, prepare_image


def load_transport():
    path = Path("/opt/hermes/plugins/plow_chat/__init__.py")
    spec = importlib.util.spec_from_file_location("omni_plow_transport", path, submodule_search_locations=[str(path.parent)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for name in ("_on_message", "_deliver", "_ensure_anchor", "_checkpoint", "send", "connect", "disconnect"):
        if not callable(getattr(module.PlowChatAdapter, name, None)):
            raise RuntimeError("unsupported Plow transport")
    return module


def adapter_class(module):
    class OmniAdapter(module.PlowChatAdapter):
        def _mark_connected(self):
            super()._mark_connected()
            logging.getLogger("omni").info("plow_websocket_connected")

        def _mark_disconnected(self):
            super()._mark_disconnected()
            logging.getLogger("omni").warning("plow_websocket_disconnected")

        async def _on_message(self, msg, chat_uid):
            # The authenticated Plow stream owns sender role, not model text.
            sender = msg.get("sender", {})
            if not isinstance(sender.get("uid"), str) or not sender["uid"]:
                return
            if msg.get("direction", "inbound") != "inbound" or chat_uid != self.workflow.settings.allowed_chat_id or sender.get("type") != "member" or sender.get("role") != "owner":
                return
            if not hasattr(self, "_omni_references"):
                self._omni_references = {}
            if msg.get("uid"):
                parent = (msg.get("reply_to") or {}).get("message") or {}
                self._omni_references[msg["uid"]] = (
                    msg.get("guid"), msg.get("reply_to_guid") or parent.get("guid") or parent.get("uid"),
                    bool(msg.get("reply_to") or msg.get("reply_to_guid")))
                while len(self._omni_references) > 512:
                    self._omni_references.pop(next(iter(self._omni_references)))
            await super()._on_message(msg, chat_uid)

        async def _deliver(self, burst, resolved, chat_uid):
            from gateway.platforms.base import get_image_cache_dir
            await self._ensure_anchor(chat_uid)
            roots = getattr(self.workflow, "media_roots", None) or [Path(get_image_cache_dir())]
            for msg, (paths, kinds, text) in zip(burst, resolved, strict=True):
                # Preserve each message ID. A changed debounce batch after restart
                # cannot change deduplication or join unrelated screenshots.
                guid, reference, is_reply = getattr(self, "_omni_references", {}).pop(msg.uid, (None, None, False))
                native_reply = getattr(msg, "reply_to", None)
                parent = (native_reply or {}).get("message") or {}
                reference = reference or parent.get("guid") or parent.get("uid")
                prepared = None
                if len(paths) == 1 and len(kinds) == 1 and kinds[0].startswith("image/"):
                    try:
                        prepared = await asyncio.to_thread(prepare_image, paths[0], roots, self.workflow.settings.max_image_bytes)
                    except (OSError, Problem):
                        paths, kinds = [], []
                        text += "\n[attachment: invalid image]"
                self.workflow.ingest(prepared=prepared, sender=msg.sender.get("uid"), guid=guid,
                    reply_to_guid=reference, is_reply=is_reply or bool(native_reply), chat=chat_uid, message=msg.uid, text=text,
                    paths=paths, kinds=kinds,
                    owner=msg.sender.get("type") == "member" and msg.sender.get("role") == "owner",
                    roots=roots)
            # A photo and its reply can resolve to the same cached file in a
            # burst. Delete only after every event has been durably ingested.
            for value in {value for paths, _, _ in resolved for value in paths}:
                path = Path(value)
                if not path.is_symlink() and any(path.resolve().is_relative_to(root.resolve()) for root in roots):
                    path.unlink(missing_ok=True)
            # Enqueue commits BEFORE advancing the upstream backfill cursor.
            if self._checkpoint(burst[-1].uid, chat_uid) is False:
                raise OSError("checkpoint failed")

        async def _handoff_message(self, event):
            # Upstream synthetic greetings/goals must never start a general agent.
            return

        async def _greet_first_meeting(self, chat_uid, first_meeting):
            # No unsolicited greeting in other chats covered by a broad grant.
            return

    return OmniAdapter


def make_adapter(module, config):
    # The restricted runner does not run PluginManager.discover(). Register the
    # platform through Hermes' documented registry before Platform('plow_chat').
    from gateway.platform_registry import PlatformEntry, platform_registry

    factory = adapter_class(module)
    platform_registry.register(PlatformEntry(
        name=module.PLATFORM_NAME, label="Omni Plow Chat", adapter_factory=factory,
        check_fn=module.check_requirements, plugin_name="omni-action-hub",
    ))
    return factory(config)


async def maintain_connection(adapter):
    """Reconnect without terminating the durable worker or a tight s6 restart loop.

    A revoked credential is not renewable by retrying it. After re-minting and
    restarting the container, bootstrap publishes the replacement credential.
    Ordinary network failures and expired socket tickets use the adapter's
    official ticket-minting/connect path on each reconnection.
    """
    attempts = 0
    while True:
        started = asyncio.get_running_loop().time()
        try:
            await adapter.connect()
            logging.getLogger("omni").info("plow_listener_started")
            await adapter._ws_task
            raise ConnectionError("listener ended")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            duration = asyncio.get_running_loop().time() - started
            attempts = 1 if duration > 60 else attempts + 1
            delay = min(5 * 2 ** min(attempts-1, 6), 300)
            code = "plow_authentication" if "Auth" in type(exc).__name__ else "plow_connection"
            logging.getLogger("omni").warning("%s retry_in_seconds=%d error_type=%s", code, delay, type(exc).__name__)
            try:
                await adapter.disconnect()
            except Exception:
                pass
            await asyncio.sleep(delay)


async def serve():
    from gateway.config import PlatformConfig
    load_runtime_environment()
    settings = Settings.from_env()
    if settings.allowed_chat_id != os.environ.get("PLOW_HOME_CHANNEL"):
        raise RuntimeError("configured conversation must be the Plow home channel")
    store = Store(settings.data_dir)
    store.check_downloads()
    lock = open(settings.data_dir / "worker.lock", "a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    transport = load_transport()
    adapter = make_adapter(transport, PlatformConfig(enabled=True))
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10), limits=httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=60), follow_redirects=False) as client:
        async def send(chat, content):
            result = await adapter.send(chat, content, metadata={"notify": True})
            return bool(result.success)
        linear = Linear(settings, client)
        try:
            await linear.prepare_pending_label(store)
        except Problem as exc:
            logging.getLogger("omni").warning("fallback_setup_failed code=%s", exc.code)
        workflow = Workflow(settings, store, Gemini(settings, client, store), linear, send)
        workflow.media_roots = [store.downloads]
        # This private module instance keeps official socket/ack/reply semantics.
        # Only its attachment resolver is replaced, before any messages connect.
        transport._resolve_parts = MediaResolver(os.environ.get("PLOW_API_BASE", "https://api.plow.co"),
            store.downloads, client, settings.max_image_bytes).resolve
        adapter.workflow = workflow
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        connection = asyncio.create_task(maintain_connection(adapter))
        worker = asyncio.create_task(workflow.run())
        notices = asyncio.create_task(workflow.run_notices())
        stopper = asyncio.create_task(stop.wait())
        health = settings.data_dir / "heartbeat"
        async def heartbeat():
            while True:
                if getattr(adapter, "_running", False):
                    health.touch(mode=0o600)
                else:
                    health.unlink(missing_ok=True)
                await asyncio.sleep(10)
        pulse = asyncio.create_task(heartbeat())
        try:
            done, _ = await asyncio.wait([worker, stopper, pulse, connection, notices], return_when=asyncio.FIRST_COMPLETED)
            if worker in done:
                worker.result()
            if notices in done:
                notices.result()
            if pulse in done:
                pulse.result()
            if connection in done:
                connection.result()
        finally:
            for task in (worker, stopper, pulse, connection, notices):
                task.cancel()
            await asyncio.gather(worker, stopper, pulse, connection, notices, return_exceptions=True)
            await adapter.disconnect()
            health.unlink(missing_ok=True)
            store.close()
            lock.close()


def main():
    os.umask(0o077)
    # Suppress upstream transport logs: signed URLs and message metadata must not
    # accidentally enter the container logs. Our own log vocabulary is fixed.
    logging.basicConfig(level=logging.CRITICAL, format="%(asctime)s %(levelname)s:%(name)s:%(message)s")
    logging.getLogger("omni").setLevel(logging.INFO)
    try:
        asyncio.run(serve())
    except Exception as exc:
        logging.getLogger("omni").critical("gateway_stopped code=configuration_or_runtime error_type=%s; run omni doctor", type(exc).__name__)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
