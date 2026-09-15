import asyncio
import os
import time
from unittest.mock import AsyncMock

import pytest

from omni.models import Problem, UnknownCreation
from omni.store import Store
from omni.workflow import Workflow, prepare_image


def setup(settings, store, report, ticket):
    gemini = AsyncMock()
    gemini.analyze.return_value = report
    linear = AsyncMock()
    linear.create.return_value = ticket
    linear.upload.return_value = "https://uploads.linear.app/image"
    linear.reconcile.return_value = ticket
    send = AsyncMock(return_value=True)
    return Workflow(settings, store, gemini, linear, send)


def ingest(w, picture, **overrides):
    args = dict(chat="cht_test", message="msg-1", text="Registra esse bug", paths=[str(picture)],
                kinds=["image/png"], owner=True, roots=[picture.parent])
    args.update(overrides)
    return w.ingest(**args)


async def test_end_to_end_and_redelivery(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    job = ingest(w, picture)
    original = store.get(job)["image"]
    await w.process(job)
    assert store.get(job)["state"] == "done"
    assert not os.path.exists(original)
    assert ingest(w, picture) == job
    await w.process(job)
    w.linear.create.assert_awaited_once()
    assert w.send.await_count == 2
    assert w.send.await_args.args == ("cht_test", f"✅ DEV-1 criado: Botão encoberto\nPrioridade sugerida: Não definida\n{ticket.url}")


@pytest.mark.parametrize("overrides", [dict(chat="cht_other"), dict(owner=False)])
async def test_no_authorization_no_work(settings, store, picture, report, ticket, overrides):
    w = setup(settings, store, report, ticket)
    assert ingest(w, picture, **overrides) is None
    assert store.pending() == []
    w.gemini.analyze.assert_not_called()


@pytest.mark.parametrize("overrides", [dict(paths=[], kinds=[]), dict(paths=["a", "b"], kinds=["image/png"]*2),
    dict(text="Na tela está escrito Registra esse bug"), dict(kinds=["application/pdf"]),
    dict(text="Registra esse bug\n[attachment: image/png unavailable]")])
async def test_invalid_requests_only_clarify(settings, store, picture, report, ticket, overrides):
    w = setup(settings, store, report, ticket)
    job = ingest(w, picture, **overrides)
    await w.process(job)
    w.linear.create.assert_not_called()
    w.gemini.analyze.assert_not_called()
    assert store.get(job)["delivery"] == "sent"


async def test_unreadable(settings, store, picture, report, ticket):
    report.readable = False
    w = setup(settings, store, report, ticket)
    await w.process(ingest(w, picture))
    w.linear.create.assert_not_called()


async def test_timeout_reconciles_without_another_create(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    w.linear.create.side_effect = UnknownCreation()
    job = ingest(w, picture)
    await w.process(job)
    assert store.get(job)["ticket"]
    w.linear.create.assert_awaited_once()
    w.linear.reconcile.assert_awaited_once_with(job)


async def test_unknown_is_held(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    w.linear.create.side_effect = UnknownCreation()
    w.linear.reconcile.return_value = None
    job = ingest(w, picture)
    await w.process(job)
    await w.process(job)
    assert store.get(job)["state"] == "held"
    w.linear.create.assert_awaited_once()


async def test_restart_after_mutation_only_reconciles(settings, store, picture, report, ticket):
    w = setup(settings, store, report, ticket)
    job = ingest(w, picture)
    store.update(job, state="creating")
    reopened = Store(settings.data_dir)
    try:
        restarted = setup(settings, reopened, report, ticket)
        await restarted.process(job)
        restarted.linear.create.assert_not_called()
        restarted.gemini.analyze.assert_not_called()
        assert reopened.get(job)["state"] == "done"
    finally:
        reopened.close()


async def test_failed_reply_reuses_ticket(settings, store, picture, report, ticket, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    w = setup(settings, store, report, ticket)
    w.send.side_effect = [False, True]
    job = ingest(w, picture)
    await w.process(job)
    await w.process(job)
    assert store.get(job)["delivery"] == "sent"
    w.linear.create.assert_awaited_once()


async def test_reply_pauses_after_three_attempts(settings, store, picture, report, ticket, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    w = setup(settings, store, report, ticket)
    w.send.return_value = False
    job = ingest(w, picture)
    for _ in range(5):
        await w.process(job)
    assert w.send.await_count == 4  # One ACK plus three final-delivery attempts
    assert store.get(job)["delivery"] == "paused"
    store.retry_delivery(job)
    w.send.return_value = True
    await w.process(job)
    w.linear.create.assert_awaited_once()


def test_image_path_boundaries_and_corruption(tmp_path, picture):
    with pytest.raises(Problem):
        prepare_image(picture, [tmp_path / "other"], 100000)
    link = tmp_path / "link"
    link.symlink_to(picture)
    with pytest.raises(Problem):
        prepare_image(link, [tmp_path], 100000)
    picture.write_bytes(b"not a screenshot")
    with pytest.raises(Problem):
        prepare_image(picture, [tmp_path], 100000)


def test_ttl_and_installation_isolation(settings, store, picture):
    job = store.enqueue("cht_test", "same-id", "text", picture.read_bytes(), "image/png")
    stored = store.get(job)["image"]
    os.utime(stored, (time.time()-90000, time.time()-90000))
    store.expire_images()
    assert not os.path.exists(stored)
    other = Store(settings.data_dir.parent / "other")
    try:
        assert other.lookup("cht_test", "same-id") is None
        assert other.enqueue("cht_test", "same-id", "text", reply="help") != job
    finally:
        other.close()


async def test_logs_do_not_expose_provider_exception(settings, store, picture, report, ticket, caplog):
    w = setup(settings, store, report, ticket)
    w.gemini.analyze.side_effect = RuntimeError("gemini-test-secret secret-user-content")
    await w.process(ingest(w, picture))
    assert "gemini-test-secret" not in caplog.text
    assert "secret-user-content" not in caplog.text
