import importlib.util
from pathlib import Path

import pytest


def test_usage_exactly_once(store):
    usage = {"promptTokenCount": 10, "cachedContentTokenCount": 3, "candidatesTokenCount": 5, "thoughtsTokenCount": 2}
    store.usage("response-1", "gemini-3.8-flash", usage)
    store.usage("response-1", "gemini-3.8-flash", usage)
    row = store.db.execute("SELECT sum(input_tokens+cache_read_tokens+output_tokens) FROM session_model_usage").fetchone()
    assert row[0] == 17


def test_official_collector_reads_and_does_not_double_count(store, tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "work/agent_index_client.py"
    if not path.exists():
        pytest.fail("Run python scripts/fetch-reporter.py before the telemetry test")
    monkeypatch.setenv("HOME", str(tmp_path))
    spec = importlib.util.spec_from_file_location("official_collector", path)
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    store.usage("one", "gemini-3.8-flash", {"promptTokenCount": 10, "candidatesTokenCount": 4})
    ledger = str(tmp_path / "ledger.json")
    first = client.from_hermes(28, home=str(store.root), state_path=ledger)
    second = client.from_hermes(28, home=str(store.root), state_path=ledger)
    assert first == second
    assert first, client.FAILURES
    # Collector structure: day -> model -> {input, output, cacheRead, cacheWrite}.
    assert sum(sum(model.values()) for day in first.values() for model in day.values()) == 14
    store.usage("two", "gemini-3.8-flash", {"promptTokenCount": 3, "candidatesTokenCount": 2})
    third = client.from_hermes(28, home=str(store.root), state_path=ledger)
    assert sum(sum(model.values()) for day in third.values() for model in day.values()) == 19
