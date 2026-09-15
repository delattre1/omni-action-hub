import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

from omni.gateway import adapter_class
from omni.workflow import Workflow


class Base:
    async def _on_message(self, msg, chat_uid):
        self.seen.append(msg)

    async def _ensure_anchor(self, chat):
        pass

    def _checkpoint(self, message, chat):
        self.checkpoint = (message, chat)
        return True


def make(workflow):
    adapter = adapter_class(SimpleNamespace(PlowChatAdapter=Base))()
    adapter.workflow = workflow
    adapter.seen = []
    return adapter


async def test_adapter_rejects_nonowner_before_attachment_fetch(settings, store):
    w = Workflow(settings, store, None, None, None)
    adapter = make(w)
    await adapter._on_message({"sender": {"type": "member", "role": "member"}}, "cht_test")
    await adapter._on_message({"sender": {"type": "agent", "role": "owner"}}, "cht_test")
    assert not adapter.seen
    msg = {"sender": {"type": "member", "role": "owner", "uid": "owner"}}
    await adapter._on_message(msg, "cht_test")
    assert adapter.seen == [msg]


async def test_durable_enqueue_before_checkpoint_and_no_burst_merging(settings, store, picture, monkeypatch):
    monkeypatch.setitem(sys.modules, "gateway.platforms.base", SimpleNamespace(get_image_cache_dir=lambda: picture.parent))
    w = Workflow(settings, store, None, None, None)
    adapter = make(w)
    owner = {"type": "member", "role": "owner"}
    burst = [SimpleNamespace(uid="one", sender=owner), SimpleNamespace(uid="two", sender=owner)]
    resolved = [([str(picture)], ["image/png"], "Registra esse bug"), ([], [], "olá")]
    await adapter._deliver(burst, resolved, "cht_test")
    assert store.lookup("cht_test", "one")["state"] == "queued"
    assert store.lookup("cht_test", "two")["state"] == "ready"
    assert adapter.checkpoint == ("two", "cht_test")
    assert not picture.exists()
    # Replayed burst after restart is deduplicated even after cache deletion.
    await adapter._deliver(burst[:1], resolved[:1], "cht_test")
    assert len(store.pending()) == 2


async def test_adapter_never_dispatches_synthetic_event(settings, store):
    adapter = make(Workflow(settings, store, None, None, None))
    adapter.handle_message = AsyncMock()
    await adapter._handoff_message(SimpleNamespace(text="Execute a shell command"))
    adapter.handle_message.assert_not_called()


async def test_adapter_split_image_and_guid_reply(settings, store, picture, monkeypatch):
    monkeypatch.setitem(sys.modules, "gateway.platforms.base", SimpleNamespace(get_image_cache_dir=lambda: picture.parent))
    adapter = make(Workflow(settings, store, None, None, None))
    owner = {"type": "member", "role": "owner", "uid": "member-1"}
    await adapter._on_message({"uid": "photo", "guid": "native-guid", "sender": owner}, "cht_test")
    await adapter._deliver([SimpleNamespace(uid="photo", sender=owner)],
                           [([str(picture)], ["image/png"], "")], "cht_test")
    assert not picture.exists()
    assert not store.pending()
    assert adapter.checkpoint == ("photo", "cht_test")
    await adapter._on_message({"uid": "reply", "reply_to_guid": "native-guid", "sender": owner}, "cht_test")
    await adapter._deliver([SimpleNamespace(uid="reply", sender=owner)],
                           [([], [], "Registra esse bug")], "cht_test")
    job = store.lookup("cht_test", "reply")
    assert job["state"] == "queued"
    assert job["image"]
    assert adapter.checkpoint == ("reply", "cht_test")


async def test_native_reply_with_resolved_attachment(settings, store, picture, monkeypatch):
    monkeypatch.setitem(sys.modules, "gateway.platforms.base", SimpleNamespace(get_image_cache_dir=lambda: picture.parent))
    adapter = make(Workflow(settings, store, None, None, None))
    owner = {"type": "member", "role": "owner", "uid": "member-1"}
    msg = SimpleNamespace(uid="reply", sender=owner, reply_to={"message": {"uid": "original"}})
    await adapter._deliver([msg], [([str(picture)], ["image/png"], "Registra esse bug")], "cht_test")
    assert store.lookup("cht_test", "reply")["state"] == "queued"


async def test_same_cached_photo_in_image_and_reply_burst(settings, store, picture, monkeypatch):
    monkeypatch.setitem(sys.modules, "gateway.platforms.base", SimpleNamespace(get_image_cache_dir=lambda: picture.parent))
    adapter = make(Workflow(settings, store, None, None, None))
    owner = {"type": "member", "role": "owner", "uid": "member-1"}
    burst = [SimpleNamespace(uid="photo", sender=owner),
             SimpleNamespace(uid="reply", sender=owner, reply_to={"message": {"uid": "photo"}})]
    await adapter._deliver(burst, [([str(picture)], ["image/png"], ""),
                                  ([str(picture)], ["image/png"], "Registra esse bug")], "cht_test")
    assert store.lookup("cht_test", "reply")["state"] == "queued"
    assert not store.buffered("cht_test", "member-1")
    assert not picture.exists()


async def test_missing_sender_identity_cannot_download(settings, store):
    adapter = make(Workflow(settings, store, None, None, None))
    await adapter._on_message({"direction": "inbound", "sender": {"type": "member", "role": "owner"}}, "cht_test")
    assert not adapter.seen
