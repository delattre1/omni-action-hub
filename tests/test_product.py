import asyncio
import io
import json
import os
import time
from unittest.mock import AsyncMock

import httpx
import pytest
from PIL import Image

from omni.clients import Gemini, Linear
from omni.feedback import ACK, RETRY
from omni.models import Problem, Report
from omni.store import Store
from omni.vision import optimize_for_vision
from omni.workflow import Workflow


async def test_503_fallback_real_clients_keep_original_and_label(settings, store, picture, ticket, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    gemini_requests, issue_inputs, uploads = [], [], []
    def handle(req):
        if req.url.host == "generativelanguage.googleapis.com":
            gemini_requests.append(req)
            return httpx.Response(503)
        if req.method == "PUT":
            uploads.append(req.content)
            return httpx.Response(200)
        body = json.loads(req.content)
        query = body["query"]
        if "issueLabels" in query:
            data = {"issueLabels": {"nodes": [{"id": "pending-id", "name": "ai-pending", "isGroup": False, "team": {"id": "team"}}], "pageInfo": {"hasNextPage": False}}}
        elif "fileUpload" in query:
            data = {"fileUpload": {"success": True, "uploadFile": {"uploadUrl": "https://storage.example/test", "assetUrl": "https://uploads.linear.app/test", "headers": []}}}
        elif "issueCreate" in query:
            issue_inputs.append(body["variables"]["input"])
            data = {"issueCreate": {"success": True, "issue": ticket.model_dump()}}
        else:
            data = {"team": {"id": "team"}}
        return httpx.Response(200, json={"data": data})
    send = AsyncMock(return_value=True)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        workflow = Workflow(settings, store, Gemini(settings, client, store), Linear(settings, client), send)
        job = store.enqueue("cht_test", "fallback", "/bug Falha ao salvar", picture.read_bytes(), "image/png")
        await workflow.process(job)
        await workflow.process(job)
    assert len(gemini_requests) == 3 and len(issue_inputs) == 1
    assert issue_inputs[0]["title"] == "Falha ao salvar"
    assert issue_inputs[0]["labelIds"] == ["pending-id"]
    assert issue_inputs[0]["teamId"] == "team" and "priority" not in issue_inputs[0]
    assert uploads == [picture.read_bytes()]
    messages = [call.args[1] for call in send.await_args_list]
    assert messages[:2] == [ACK, RETRY]
    assert "ai-pending" in messages[2] and ticket.url in messages[2]
    assert len(messages) == 3
    assert store.get(job)["state"] == "done" and store.get(job)["image"] is None
    assert store.db.execute("SELECT count(*) FROM usage_calls").fetchone()[0] == 0


@pytest.mark.parametrize("code", ["authentication", "configuration", "invalid_analysis", "missing_usage"])
async def test_permanent_analysis_errors_never_degrade(settings, store, picture, code):
    linear, gemini, send = AsyncMock(), AsyncMock(), AsyncMock(return_value=True)
    linear.labels.return_value = {}
    gemini.analyze.side_effect = Problem(code, "Correção necessária")
    workflow = Workflow(settings, store, gemini, linear, send)
    job = store.enqueue("cht_test", "permanent", "/bug Erro", picture.read_bytes(), "image/png")
    await workflow.process(job)
    linear.create.assert_not_called()
    assert send.await_args.args[1] == "Correção necessária"


async def test_labels_and_completion_not_controlled_by_model(settings, store, picture, report):
    report.suggested_labels = ["frontend", "unknown", "ai-pending"]
    report.analysis_status = "pending"
    def handle(req):
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": report.model_dump_json()}]}}], "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        result = await Gemini(settings, client, store).analyze("/bug Erro", picture.read_bytes(), "image/png", allowed_labels=["frontend"])
    assert result.suggested_labels == ["frontend"] and result.analysis_status == "complete"


async def test_ack_persists_across_restart(settings, store, picture, report, ticket):
    job = store.enqueue("cht_test", "ack-restart", "/bug Erro", picture.read_bytes(), "image/png")
    send = AsyncMock(return_value=True)
    workflow = Workflow(settings, store, None, None, send)
    await asyncio.gather(workflow.notify(store.get(job), "ack"), workflow.notify(store.get(job), "ack"))
    second = Store(settings.data_dir)
    try:
        restarted = Workflow(settings, second, None, None, send)
        await restarted.notify(second.get(job), "ack")
    finally:
        second.close()
    send.assert_awaited_once_with("cht_test", ACK)


async def test_ack_dispatch_during_slow_inference(settings, store, picture, report, ticket):
    gate, started, ack = asyncio.Event(), asyncio.Event(), asyncio.Event()
    async def analyze(*args, **kwargs):
        started.set()
        await gate.wait()
        return report
    gemini, linear = AsyncMock(), AsyncMock()
    gemini.analyze.side_effect = analyze
    linear.labels.return_value = {}
    linear.create.return_value = ticket
    linear.upload.return_value = "https://uploads.linear.app/test"
    calls = []
    async def send(chat, message):
        calls.append(message)
        if message == ACK and calls.count(ACK) == 2:
            ack.set()
        return True
    workflow = Workflow(settings, store, gemini, linear, send)
    worker = asyncio.create_task(workflow.run())
    notices = asyncio.create_task(workflow.run_notices())
    try:
        store.enqueue("cht_test", "slow", "/bug Erro", picture.read_bytes(), "image/png")
        await asyncio.wait_for(started.wait(), 1)
        now = time.monotonic()
        store.enqueue("cht_test", "next", "/bug Outro", picture.read_bytes(), "image/png")
        await asyncio.wait_for(ack.wait(), 0.5)
        assert time.monotonic() - now < 0.5
        assert not gate.is_set()
    finally:
        gate.set()
        worker.cancel()
        notices.cancel()
        await asyncio.gather(worker, notices, return_exceptions=True)


def test_vision_budget_with_high_entropy_and_original_unchanged():
    raw = io.BytesIO()
    Image.frombytes("RGB", (2048, 2048), os.urandom(2048 * 2048 * 3)).save(raw, "PNG")
    original = raw.getvalue()
    data, mime = optimize_for_vision(original)
    assert len(data) < 1_000_000 and len(original) > 5_000_000
    assert mime == "image/jpeg"
    with Image.open(io.BytesIO(data)) as im:
        assert max(im.size) <= 2048
        assert not im.getexif()


def test_old_reports_migrate_without_new_fields(report):
    payload = report.model_dump()
    for key in ("operating_system", "component", "analysis_status"):
        payload.pop(key)
    restored = Report.model_validate(payload)
    assert restored.operating_system == "unknown" and restored.analysis_status == "complete"


async def test_pending_label_provisioning_is_fixed_and_not_repeated(settings, store, monkeypatch):
    catalog = {"ai-pending": "label"}
    client = AsyncMock()
    linear = Linear(settings, client)
    linear.labels = AsyncMock(side_effect=[{}, {}, {}])
    client.post.side_effect = httpx.ReadTimeout("uncertain")
    with pytest.raises(Problem):
        await linear.prepare_pending_label(store)
    with pytest.raises(Problem):
        await linear.prepare_pending_label(store)
    client.post.assert_awaited_once()
    values = client.post.await_args.kwargs["json"]["variables"]["input"]
    assert values["name"] == "ai-pending" and values["teamId"] == "team"
    linear.labels = AsyncMock(return_value=catalog)
    assert await linear.prepare_pending_label(store) == "label"
    client.post.assert_awaited_once()


async def test_missing_pending_label_does_not_create_unmarked_issue(settings, report):
    client = AsyncMock()
    linear = Linear(settings, client)
    linear.labels = AsyncMock(return_value={})
    report.analysis_status = "pending"
    with pytest.raises(Problem):
        await linear.create("job", report, "https://uploads.linear.app/test")
    client.post.assert_not_called()
