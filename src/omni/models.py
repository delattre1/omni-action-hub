import os
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gemini_api_key: SecretStr
    linear_api_key: SecretStr
    linear_team_id: str
    linear_project_id: str | None = None
    allowed_chat_id: str
    gemini_model: str = "gemini-3.8-flash"
    data_dir: Path = Path("/var/lib/hermes/omni")
    workers: int = Field(default=2, ge=1, le=4)
    max_image_bytes: int = 10 * 1024 * 1024

    @field_validator("gemini_api_key", "linear_api_key")
    @classmethod
    def nonempty_secret(cls, value):
        if not value.get_secret_value().strip():
            raise ValueError("missing credential")
        return value

    @field_validator("allowed_chat_id")
    @classmethod
    def chat_id(cls, value):
        if not re.fullmatch(r"cht_[a-zA-Z0-9_-]+", value):
            raise ValueError("invalid chat id")
        return value

    @field_validator("linear_team_id", "allowed_chat_id", "gemini_model")
    @classmethod
    def nonempty(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("invalid configuration")
        return value.strip()

    @field_validator("gemini_model")
    @classmethod
    def model_id(cls, value):
        if not re.fullmatch(r"gemini-[a-zA-Z0-9.-]+", value):
            raise ValueError("invalid model id")
        return value

    @classmethod
    def from_env(cls):
        keys = {"gemini_api_key": "GEMINI_API_KEY", "linear_api_key": "LINEAR_API_KEY",
                "linear_team_id": "LINEAR_TEAM_ID", "linear_project_id": "LINEAR_PROJECT_ID",
                "allowed_chat_id": "OMNI_ALLOWED_CHAT_ID", "gemini_model": "GEMINI_MODEL",
                "data_dir": "OMNI_DATA_DIR", "workers": "OMNI_WORKERS"}
        return cls(**{k: os.environ[v] for k, v in keys.items() if os.environ.get(v)})


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=180)
    observed_evidence: str = Field(min_length=1, max_length=4000)
    expected_behavior: str | None = Field(default=None, max_length=2000)
    suggested_severity: Literal["baixa", "media", "alta", "indeterminada"]
    missing_information: list[Annotated[str, Field(max_length=400)]] = Field(max_length=10)
    readable: bool
    operating_system: Literal["macOS", "Windows", "Linux", "iOS", "Android", "unknown"] = "unknown"
    component: Literal["Frontend", "Backend", "unknown"] = "unknown"
    analysis_status: Literal["complete", "pending"] = "complete"
    issue_kind: Literal["bug", "feature", "task"] = "bug"
    suggested_priority: Literal["nenhuma", "baixa", "media", "alta", "urgente"] = "nenhuma"
    suggested_project: str | None = Field(default=None, max_length=180)
    suggested_labels: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(default_factory=list, max_length=10)


class Ticket(BaseModel):
    id: str
    identifier: str
    url: str

    @field_validator("url")
    @classmethod
    def linear_url(cls, value):
        from urllib.parse import urlparse
        u = urlparse(value)
        if u.scheme != "https" or u.hostname != "linear.app" or u.username:
            raise ValueError("invalid ticket URL")
        return value


class Problem(Exception):
    """Only safe, fixed user-facing messages; never provider response bodies."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class UnknownCreation(Problem):
    def __init__(self):
        super().__init__("creation_unknown", "O Linear pode ter criado o ticket. Vou verificar antes de tentar novamente.")


def is_command(text: str) -> bool:
    # Match actual user text only, never OCR, quoted text or model output.
    return bool(re.match(
        r"^\s*(?:registr[ae] esse bug|registr[ae] essa (?:tarefa|melhoria)|cri[ae] (?:um|esse) (?:card|ticket)|/(?:bug|task|feature))(?:\s|[.!?:]|$)",
        text, re.IGNORECASE))
