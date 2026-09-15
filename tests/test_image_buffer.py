"""Offline proof: asynchronous ingress uses production workflow and persistence."""
import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from omni.store import Store
from omni.workflow import Workflow


def setup(settings, store, report, ticket):
    gemini = AsyncMock()
    gemini.analyze.return_value = report
    linear = AsyncMock()
    linear.upload.return_value = "https://uploads.linear.app/test"
    linear.create.return_value = ticket
    send = AsyncMock(return_value=True)
    return Workflow(settings, store, gemini, linear, send)


def event(w, picture, message, text="", image=False, sender="owner-1", **kw):
    return w.ingest(chat="cht_test", message=message, text=text,
                    paths=[str(picture)] if image else [], kinds=["image/png"] if image else [],
                    owner=True, roots=[picture.parent], sender=sender, **kw)


async def test_image_then_text_two_seconds(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    started = time.monotonic()
    assert event(w, picture, "photo", image=True, guid="guid-photo") is None
    assert not store.pending()
    w.gemini.analyze.assert_not_called()
    await asyncio.sleep(2)
    job = event(w, picture, "command", "Registra esse bug")
    await w.process(job)
    elapsed = time.monotonic() - started
    assert elapsed >= 2
    assert store.get(job)["state"] == "done"
    assert store.get(job)["delivery"] == "sent"
    assert store.get(job)["image"] is None
    assert not store.buffered("cht_test", "owner-1")
    w.gemini.analyze.assert_awaited_once()
    assert w.gemini.analyze.call_args.args[1] == picture.read_bytes()
    w.linear.create.assert_awaited_once()
    assert w.send.await_count == 2
    assert w.send.await_args.args == ("cht_test", f"✅ DEV-1 criado: Botão encoberto\nPrioridade sugerida: Não definida\n{ticket.url}")
    assert event(w, picture, "command", "Registra esse bug") == job
    event(w, picture, "photo", image=True)
    await w.process(job)
    w.linear.create.assert_awaited_once()
    print(f"\nPROVA: imagem → espera {elapsed:.2f}s → comando → ticket único → link enviado (APIs simuladas).")


@pytest.mark.parametrize("mode", ["expired", "other_sender", "multiple", "unknown_reply", "native_reply_without_image"])
async def test_does_not_guess_image(mode, settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    event(w, picture, "photo", image=True)
    options = {}
    if mode == "expired":
        with store.db:
            store.db.execute("UPDATE inbound_images SET created=created-61")
    elif mode == "other_sender":
        options["sender"] = "owner-2"
    elif mode == "multiple":
        event(w, picture, "photo-2", image=True)
    elif mode == "unknown_reply":
        options.update(reply_to_guid="missing", is_reply=True)
    else:
        options["is_reply"] = True
    job = event(w, picture, "command", "Registra esse bug", **options)
    await w.process(job)
    w.gemini.analyze.assert_not_called()
    w.linear.create.assert_not_called()
    if mode in ("expired", "other_sender", "unknown_reply"):
        w.send.assert_not_called()
        assert store.get(job)["state"] == "waiting"
        with store.db:
            store.db.execute("UPDATE jobs SET deadline=0 WHERE id=?", (job,))
        await w.process(job)
        assert "60 segundos" in w.send.call_args.args[1]
    else:
        assert "exatamente uma imagem" in w.send.call_args.args[1]


async def test_guid_reply_survives_restart_and_chooses_original(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    event(w, picture, "photo", image=True, guid="original-guid")
    with store.db:
        store.db.execute("UPDATE inbound_images SET created=created-61")
    event(w, picture, "new-photo", image=True)
    second = Store(settings.data_dir)
    try:
        restarted = setup(settings, second, report, ticket)
        job = event(restarted, picture, "reply", "Registra esse bug", reply_to_guid="original-guid", is_reply=True)
        await restarted.process(job)
        restarted.linear.create.assert_awaited_once()
        assert [x["message"] for x in second.buffered("cht_test", "owner-1")] == ["new-photo"]
    finally:
        second.close()


def test_next_noncommand_consumes_buffer_and_expiry_cleans_bytes(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    event(w, picture, "photo", image=True)
    event(w, picture, "hello", "Olá")
    assert not store.buffered("cht_test", "owner-1")
    event(w, picture, "old", image=True)
    with store.db:
        store.db.execute("UPDATE inbound_images SET created=created-86401")
    store.expire_images()
    assert store.db.execute("SELECT count(*) FROM inbound_images WHERE image IS NOT NULL").fetchone()[0] == 0


async def test_text_before_image_two_seconds(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    job = event(w, picture, "command", "Registra esse bug")
    await w.process(job)
    w.send.assert_not_called()
    assert store.get(job)["state"] == "waiting"
    await asyncio.sleep(2)
    assert event(w, picture, "photo", image=True) == job
    await w.process(job)
    assert store.get(job)["state"] == "done"
    w.linear.create.assert_awaited_once()
    assert w.send.await_count == 2


async def test_waiting_command_survives_restart(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    job = event(w, picture, "command", "Registra esse bug")
    second = Store(settings.data_dir)
    try:
        restarted = setup(settings, second, report, ticket)
        assert event(restarted, picture, "photo", image=True) == job
        await restarted.process(job)
        assert second.get(job)["state"] == "done"
    finally:
        second.close()


async def test_unavailable_image_alone_is_silent(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    assert event(w, picture, "photo", "\n[attachment: image unavailable]") is None
    assert not store.pending()
    w.send.assert_not_called()
    job = event(w, picture, "command", "Registra esse bug")
    await w.process(job)
    w.send.assert_not_called()


async def test_two_waiting_commands_never_guess(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    jobs = [event(w, picture, f"command-{i}", "Registra esse bug") for i in range(2)]
    assert event(w, picture, "photo", image=True) is None
    for job in jobs:
        await w.process(job)
    w.linear.create.assert_not_called()
    assert all(store.get(job)["state"] == "done" for job in jobs)
