import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("preflight", ROOT / "scripts/preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def config(tmp_path):
    for name in (".env", "plow-credentials"):
        path = tmp_path / name
        path.write_text("dummy")
        path.chmod(0o600)
    return {"services": {"agent": {
        "image": "ghcr.io/fecabrall/omni-action-hub@sha256:" + "a" * 64,
        "environment": dict(GEMINI_API_KEY="fake", GEMINI_MODEL="gemini-test", LINEAR_API_KEY="fake",
                            LINEAR_TEAM_ID="test", OMNI_ALLOWED_CHAT_ID="cht_owner"),
        "volumes": [{"source": str(tmp_path / "plow-credentials"), "target": "/var/lib/plow/credentials.host", "read_only": True}],
    }}}


def test_production_preflight(tmp_path):
    assert preflight.validate(config(tmp_path), tmp_path) == []


def test_rejects_mutable_image_and_local_build(tmp_path):
    value = config(tmp_path)
    value["services"]["agent"].update(image="omni:latest", build=".")
    assert len(preflight.validate(value, tmp_path)) == 2


def test_rejects_missing_credentials_and_world_readable_env(tmp_path):
    value = config(tmp_path)
    (tmp_path / "plow-credentials").unlink()
    (tmp_path / ".env").chmod(0o644)
    assert len(preflight.validate(value, tmp_path)) == 2
