"""Bounded offline assessment: never uses installation credentials or real tickets."""
import asyncio
import json
import time
from unittest.mock import AsyncMock

import pytest

from omni.feedback import ACK
from omni.models import Ticket
from omni.workflow import Workflow


@pytest.mark.parametrize("workers", [1, 2, 4])
async def test_burst_respects_worker_limit_and_drains(workers, settings, store, picture, report):
    settings.workers = workers
    count, active, peak = 24, 0, 0
    sent, created = [], []
    async def analyze(*args, **kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0.03)
            return report.model_copy(deep=True)
        finally:
            active -= 1
    async def create(job_id, *args):
        created.append(job_id)
        return Ticket(id=job_id, identifier=f"TEST-{len(created)}", url=f"https://linear.app/test/issue/{job_id}")
    async def send(chat, body):
        sent.append(body)
        return True
    gemini, linear = AsyncMock(), AsyncMock()
    gemini.analyze.side_effect = analyze
    linear.labels.return_value = {}
    linear.upload.return_value = "https://uploads.linear.app/test"
    linear.create.side_effect = create
    flow = Workflow(settings, store, gemini, linear, send)
    # Unique source messages and one configured installation; not three foreign owners.
    ids = [store.enqueue("cht_test", f"stress-{i}", f"/bug Falha {i}", picture.read_bytes(), "image/png") for i in range(count)]
    for i, job_id in enumerate(ids):
        assert store.enqueue("cht_test", f"stress-{i}", "duplicate") == job_id
    started = time.monotonic()
    worker = asyncio.create_task(flow.run())
    notices = asyncio.create_task(flow.run_notices())
    try:
        async with asyncio.timeout(10):
            while any(store.get(job)["state"] != "done" for job in ids):
                await asyncio.sleep(0.02)
        assert 1 <= peak <= workers
        assert len(created) == len(set(created)) == count
        assert sent.count(ACK) == count
        assert sum(body.startswith("✅") for body in sent) == count
        assert not store.pending()
        assert not list(store.images.iterdir())
        print("\nSTRESS " + json.dumps({"workers": workers, "jobs": count, "peak_inference": peak,
              "tickets": len(created), "ack": sent.count(ACK), "elapsed_s": round(time.monotonic()-started, 3)}))
    finally:
        worker.cancel()
        notices.cancel()
        await asyncio.gather(worker, notices, return_exceptions=True)


async def test_natural_description_does_not_authorize_creation(settings, store, picture):
    linear, gemini = AsyncMock(), AsyncMock()
    flow = Workflow(settings, store, gemini, linear, AsyncMock(return_value=True))
    args = dict(chat="cht_test", sender="owner", owner=True, roots=[picture.parent])
    assert flow.ingest(message="photo", text="", paths=[str(picture)], kinds=["image/png"], **args) is None
    job = flow.ingest(message="description", text="O botão de checkout sumiu da tela principal", paths=[], kinds=[], **args)
    await flow.process(job)
    gemini.analyze.assert_not_called()
    linear.create.assert_not_called()
    assert "Registra esse bug" in flow.send.await_args.args[1]
