
import pytest
from PIL import Image

from omni.models import Report, Settings, Ticket
from omni.store import Store


@pytest.fixture
def settings(tmp_path):
    return Settings(gemini_api_key="gemini-test-secret", linear_api_key="linear-test-secret",
                    linear_team_id="team", allowed_chat_id="cht_test", data_dir=tmp_path / "state")


@pytest.fixture
def store(settings):
    value = Store(settings.data_dir)
    yield value
    value.close()


@pytest.fixture
def picture(tmp_path):
    p = tmp_path / "screen.png"
    Image.new("RGB", (80, 40), "white").save(p)
    return p


@pytest.fixture
def report():
    return Report(title="Botão encoberto", observed_evidence="O botão está parcialmente encoberto.",
                  expected_behavior=None, suggested_severity="indeterminada",
                  missing_information=["Passos de reprodução"], readable=True)


@pytest.fixture
def ticket():
    return Ticket(id="ticket", identifier="DEV-1", url="https://linear.app/example/issue/DEV-1")
