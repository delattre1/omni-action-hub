import json

import pytest

from omni.evaluation import (
    CLASSES,
    Manifest,
    classification_metrics,
    load_manifest,
    score,
    write_private,
)


def example():
    expected = dict(operating_system="unknown", component="Frontend",
                    suggested_severity="alta", suggested_priority="nenhuma")
    manifest = Manifest(name="synthetic", split="synthetic", cases=[
        dict(id="a", image="a.png", text="/bug", expected=expected),
        dict(id="b", image="b.png", text="/bug", expected=expected)])
    return manifest, expected


def test_metrics_with_known_confusion():
    m = classification_metrics(["A", "A", "B", "B"], ["A", "B", "B", "B"], ["A", "B"])
    assert m["confusion_matrix"] == [[1, 1], [0, 2]]
    assert m["accuracy"] == .75
    assert m["macro_f1"] == pytest.approx((2/3 + .8) / 2)
    assert m["macro_precision"] == pytest.approx((1 + 2/3) / 2)
    assert m["macro_recall"] == .75


def test_failures_remain_in_end_to_end_denominator():
    manifest, expected = example()
    m = score(manifest, {"a": expected, "b": {"error": "unavailable"}})
    field = m["fields"]["component"]
    assert field["accuracy"] == 1
    assert field["end_to_end_accuracy"] == .5
    assert field["coverage"] == .5
    assert m["errors"] == {"unavailable": 1}


def test_all_failures_are_not_zero_or_perfect_quality():
    manifest, _ = example()
    m = score(manifest, {k: {"error": "unavailable"} for k in ("a", "b")})
    assert m["fields"]["component"]["macro_f1"] is None
    assert m["fields"]["component"]["end_to_end_accuracy"] == 0


def test_unknown_is_a_class_but_null_annotation_is_excluded():
    manifest, expected = example()
    manifest.cases[0].expected = {**expected, "component": None}
    m = score(manifest, {"a": expected, "b": expected})
    assert m["fields"]["component"]["annotation_excluded"] == 1
    assert m["fields"]["operating_system"]["abstention_rate"] == 1


@pytest.mark.parametrize("mutation", ["missing", "extra", "invalid"])
def test_rejects_incomplete_or_invalid_predictions(mutation):
    manifest, expected = example()
    predictions = {"a": expected, "b": expected}
    if mutation == "missing":
        del predictions["a"]
    elif mutation == "extra":
        predictions["c"] = expected
    else:
        predictions["a"] = {**expected, "component": "database"}
    with pytest.raises(ValueError):
        score(manifest, predictions)


def test_manifest_prevents_traversal_and_duplicates(tmp_path):
    manifest, _ = example()
    (tmp_path / "a.png").write_bytes(b"same image")
    (tmp_path / "b.png").write_bytes(b"same image")
    path = tmp_path / "dataset.json"
    path.write_text(manifest.model_dump_json())
    with pytest.raises(ValueError, match="duplicate screenshot"):
        load_manifest(path)
    manifest.cases[1].image = "../outside.png"
    path.write_text(manifest.model_dump_json())
    with pytest.raises(ValueError, match="inside"):
        load_manifest(path)


def test_result_permissions_and_no_overwrite(tmp_path):
    file = tmp_path / "result.json"
    write_private(file, {"ok": True})
    assert file.stat().st_mode & 0o777 == 0o600
    assert json.loads(file.read_text()) == {"ok": True}
    with pytest.raises(FileExistsError):
        write_private(file, {})


def test_taxonomy_matches_report_schema():
    from omni.models import Report
    schema = Report.model_json_schema()["properties"]
    for field, labels in CLASSES.items():
        assert labels == schema[field]["enum"]


def test_offline_cli_writes_real_metrics_without_api(tmp_path, monkeypatch):
    import sys

    from PIL import Image

    from omni.evaluation import main
    manifest, expected = example()
    for name, color in [("a", "white"), ("b", "black")]:
        Image.new("RGB", (10, 10), color).save(tmp_path / f"{name}.png")
    source = tmp_path / "dataset.json"
    source.write_text(manifest.model_dump_json())
    predictions = tmp_path / "predictions.json"
    predictions.write_text(json.dumps({"a": expected, "b": expected}))
    output = tmp_path / "result.json"
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["evaluation", "--manifest", str(source),
                                     "--predictions", str(predictions), "--output", str(output)])
    assert main() == 0
    result = json.loads(output.read_text())
    assert result["fields"]["component"]["accuracy"] == 1
    assert "offline" in result["run"]["mode"]
    assert len(result["image_sha256"]) == 2
    assert len(result["analyzer_sha256"]) == 64


async def test_live_runner_uses_product_client_and_safe_errors(tmp_path, monkeypatch):
    from omni import evaluation
    manifest, expected = example()
    for case in manifest.cases:
        (tmp_path / case.image).write_bytes(b"image")
    calls = []

    class FakeGemini:
        def __init__(self, settings, client, usage):
            self.usage = usage

        async def analyze(self, text, data, mime, allowed_labels):
            calls.append((text, data, allowed_labels))
            if len(calls) == 2:
                raise RuntimeError("provider private body must not escape")
            self.usage.usage("call", "gemini-test", {"totalTokenCount": 12})
            from types import SimpleNamespace
            return SimpleNamespace(**expected)

    monkeypatch.setattr(evaluation, "Gemini", FakeGemini)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-placeholder")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    predictions, metadata = await evaluation.predict_live(manifest, tmp_path)
    assert predictions["a"] == expected
    assert predictions["b"] == {"error": "evaluation_failed"}
    assert metadata["tokens"] == 12
    assert len(calls) == 2
