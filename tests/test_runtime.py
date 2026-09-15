import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from omni.environment import load_runtime_environment
from omni.gateway import maintain_connection


def test_docker_exec_loads_s6_environment(tmp_path, monkeypatch):
    from pathlib import Path
    for name, value in {"PLOW_AGENT_TOKEN": "secret", "PLOW_HOME_CHANNEL": "cht_owner"}.items():
        (tmp_path / name).write_text(value)
        (tmp_path / name).chmod(0o600)
        monkeypatch.delenv(name, raising=False)
    original = Path.lstat
    def info(path):
        result = original(path)
        return SimpleNamespace(st_mode=result.st_mode, st_uid=0)
    monkeypatch.setattr(Path, "lstat", info)
    load_runtime_environment(tmp_path)
    assert os.environ["PLOW_AGENT_TOKEN"] == "secret"
    assert os.environ["PLOW_HOME_CHANNEL"] == "cht_owner"


def test_untrusted_environment_files_are_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv("PLOW_AGENT_TOKEN", raising=False)
    path = tmp_path / "PLOW_AGENT_TOKEN"
    path.write_text("attacker")
    path.chmod(0o666)
    load_runtime_environment(tmp_path)
    assert "PLOW_AGENT_TOKEN" not in os.environ


async def test_reconnect_is_paced_without_exposing_token(monkeypatch, caplog):
    adapter = SimpleNamespace(connect=AsyncMock(side_effect=RuntimeError("secret-token")), disconnect=AsyncMock())
    sleep = AsyncMock(side_effect=[None, asyncio.CancelledError])
    monkeypatch.setattr(asyncio, "sleep", sleep)
    with pytest.raises(asyncio.CancelledError):
        await maintain_connection(adapter)
    assert [c.args[0] for c in sleep.await_args_list] == [5, 10]
    assert "secret-token" not in caplog.text
    assert adapter.connect.await_count == 2
