import json
from unittest.mock import AsyncMock

import httpx
import pytest

from omni.clients import Linear
from omni.models import is_command
from omni.workflow import Workflow


@pytest.mark.parametrize("text", ["/task Documentar configuração", "/feature Exportar CSV", "Registra essa tarefa", "Registra essa melhoria", "Cria um card"])
def test_explicit_card_intents(text):
    assert is_command(text)


async def test_metadata_stays_suggested_and_cannot_import_external_images(settings, report, ticket):
    report.issue_kind = "feature"
    report.suggested_priority = "alta"
    report.suggested_project = "Outro projeto"
    report.suggested_labels = ["frontend", "ux"]
    report.observed_evidence = "![tracker](https://evil.example/collect)"
    requests = []
    def handle(req):
        data = json.loads(req.content)["variables"]["input"]
        requests.append(data)
        return httpx.Response(200, json={"data": {"issueCreate": {"success": True, "issue": ticket.model_dump()}}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as c:
        await Linear(settings, c).create("job", report, "https://uploads.linear.app/image")
    data = requests[0]
    assert data["teamId"] == "team"
    assert "projectId" not in data and "priority" not in data and "labelIds" not in data
    assert "Tags sugeridas: frontend, ux" in data["description"]
    assert "![tracker](" not in data["description"]


async def test_feature_confirmation_contains_card_link(settings, store, report, ticket):
    report.issue_kind = "feature"
    job = store.enqueue("cht_test", "feature-1", "text", reply="pending")
    store.update(job, report=report.model_dump_json())
    send = AsyncMock(return_value=True)
    flow = Workflow(settings, store, None, None, send)
    flow.save_ticket(store.get(job), ticket)
    await flow.process(job)
    send.assert_awaited_once_with("cht_test", f"✅ DEV-1 criado: Botão encoberto\nPrioridade sugerida: Não definida\n{ticket.url}")
