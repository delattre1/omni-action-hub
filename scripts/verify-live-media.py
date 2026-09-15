"""Read-only Plow media diagnostic. Run with docker exec -i and Python stdin.

Uses the latest real image in the configured chat, drops root to the gateway
UID, downloads and validates it, then removes temporary files. No ticket/send.
"""
import asyncio
import json
import logging
import os
import tempfile

import httpx

from omni.environment import load_runtime_environment
from omni.media import MediaResolver
from omni.models import Settings
from omni.store import Store
from omni.workflow import Workflow, prepare_image


async def main():
    load_runtime_environment()
    settings = Settings.from_env()
    base = os.environ.get("PLOW_API_BASE", "https://api.plow.co")
    if base not in ("https://api.plow.co", "https://api.plow.dev"):
        raise ValueError("unsupported Plow endpoint")
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        response = await client.get(base + "/v1/chats/" + settings.allowed_chat_id + "/messages?limit=30",
            headers={"Authorization": "Bearer " + os.environ["PLOW_AGENT_TOKEN"]})
        response.raise_for_status()
        source = next(m for m in response.json()["data"] if m.get("direction") == "inbound"
            and m.get("sender", {}).get("role") == "owner" and m.get("attachments"))
        if os.geteuid() == 0:
            os.setgroups([])
            os.setgid(10000)
            os.setuid(10000)
        store = Store(settings.data_dir)
        try:
            store.check_downloads()
            resolver = MediaResolver(base, store.downloads, client, settings.max_image_bytes)
            paths, kinds, _ = await resolver.resolve(source)
            if len(paths) != 1:
                raise ValueError("real image did not resolve")
            try:
                data, mime = prepare_image(paths[0], [store.downloads], settings.max_image_bytes)
                with tempfile.TemporaryDirectory(dir=settings.data_dir) as isolated:
                    from pathlib import Path
                    proof = Store(Path(isolated))
                    try:
                        workflow = Workflow(settings, proof, None, None, None)
                        args = dict(chat=settings.allowed_chat_id, sender=source["sender"]["uid"], owner=True,
                                    roots=[store.downloads])
                        first = workflow.ingest(message="proof-photo", text="", paths=paths, kinds=kinds, **args)
                        silent = first is None and not proof.pending()
                        await asyncio.sleep(2)
                        job = workflow.ingest(message="proof-command", text="Registra esse bug", paths=[], kinds=[], **args)
                        matched = proof.get(job)["state"] == "queued" and bool(proof.get(job)["image"])
                        assert silent and matched
                    finally:
                        proof.close()
                print(json.dumps({"image_only_silent": silent, "split_match_after_two_seconds": matched, "uid": os.geteuid(), "real_plow_download": "ok",
                                  "normalized_bytes": len(data), "mime": mime, "cache_write": "ok"}))
            finally:
                for path in paths:
                    from pathlib import Path
                    Path(path).unlink(missing_ok=True)
        finally:
            store.close()


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    try:
        asyncio.run(main())
    except Exception as exc:
        print(json.dumps({"live_media": "failed", "error_type": type(exc).__name__}))
        raise SystemExit(1)
