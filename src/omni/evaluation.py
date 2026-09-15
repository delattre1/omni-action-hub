"""Offline metrics and an opt-in Gemini-only evaluator. Never creates tickets."""
import argparse
import asyncio
import hashlib
import inspect
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .clients import Gemini
from .models import Problem, Report

CLASSES = {
    "operating_system": ["macOS", "Windows", "Linux", "iOS", "Android", "unknown"],
    "suggested_severity": ["baixa", "media", "alta", "indeterminada"],
    "component": ["Frontend", "Backend", "unknown"],
    "suggested_priority": ["nenhuma", "baixa", "media", "alta", "urgente"],
}
ABSTENTION = {"operating_system": "unknown", "suggested_severity": "indeterminada",
              "component": "unknown", "suggested_priority": "nenhuma"}


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    image: str
    text: str = Field(min_length=1, max_length=4000)
    expected: dict[str, str | None]
    allowed_labels: list[str] = Field(default_factory=list, max_length=100)


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    split: str = Field(pattern=r"^(development|holdout|synthetic)$")
    cases: list[Case] = Field(min_length=1, max_length=500)


def load_manifest(path):
    manifest = Manifest.model_validate_json(path.read_text())
    ids, hashes = set(), set()
    for case in manifest.cases:
        if case.id in ids or set(case.expected) != set(CLASSES):
            raise ValueError("duplicate case ID or invalid expected fields")
        ids.add(case.id)
        for field, expected in case.expected.items():
            if expected is not None and expected not in CLASSES[field]:
                raise ValueError("invalid expected class")
        image = (path.parent / case.image).resolve()
        if not image.is_relative_to(path.parent.resolve()) or not image.is_file():
            raise ValueError("image must be a file inside the dataset directory")
        if image.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("image exceeds 10 MiB")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest in hashes:
            raise ValueError("duplicate screenshot bytes would inflate the dataset")
        hashes.add(digest)
    return manifest


def classification_metrics(truth, predicted, labels):
    if len(truth) != len(predicted):
        raise ValueError("prediction count mismatch")
    if any(x not in labels for x in truth + predicted):
        raise ValueError("unknown class")
    matrix = [[0 for _ in labels] for _ in labels]
    for actual, guess in zip(truth, predicted, strict=True):
        matrix[labels.index(actual)][labels.index(guess)] += 1
    rows = []
    for i, label in enumerate(labels):
        tp = matrix[i][i]
        support = sum(matrix[i])
        predicted_count = sum(row[i] for row in matrix)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(dict(label=label, support=support, predicted=predicted_count,
                         precision=precision, recall=recall, f1=f1))
    count = len(truth)
    # Fixed taxonomy macro is comparable across runs. Supported-class macro is
    # supplied separately, explicitly; absent classes must not silently vanish.
    supported = [row for row in rows if row["support"]]
    return {
        "samples": count,
        "accuracy": sum(matrix[i][i] for i in range(len(labels))) / count if count else None,
        "macro_precision": sum(r["precision"] for r in rows) / len(rows) if count else None,
        "macro_recall": sum(r["recall"] for r in rows) / len(rows) if count else None,
        "macro_f1": sum(r["f1"] for r in rows) / len(rows) if count else None,
        "supported_macro_f1": sum(r["f1"] for r in supported) / len(supported) if supported else None,
        "weighted_f1": sum(r["f1"] * r["support"] for r in rows) / count if count else None,
        "per_class": rows, "labels": labels, "confusion_matrix": matrix,
        "matrix_orientation": "rows=expected, columns=predicted",
        "zero_division": 0,
    }


def score(manifest, predictions):
    expected_ids = {case.id for case in manifest.cases}
    if set(predictions) != expected_ids:
        raise ValueError("predictions must match every dataset ID exactly")
    for value in predictions.values():
        if not isinstance(value, dict):
            raise ValueError("invalid prediction")
        if "error" in value:
            if set(value) != {"error"} or not re.fullmatch(r"[a-z_]{1,40}", value["error"]):
                raise ValueError("errors must contain a safe code only")
        elif set(value) != set(CLASSES) or any(value[f] not in labels for f, labels in CLASSES.items()):
            raise ValueError("invalid prediction fields or class")
    results = {}
    for field, labels in CLASSES.items():
        eligible = [case for case in manifest.cases if case.expected[field] is not None]
        successful = [case for case in eligible if "error" not in predictions[case.id]]
        truth = [case.expected[field] for case in successful]
        guesses = [predictions[case.id][field] for case in successful]
        metrics = classification_metrics(truth, guesses, labels)
        metrics.update({
            "eligible": len(eligible), "annotation_excluded": len(manifest.cases) - len(eligible),
            "failed": len(eligible) - len(successful),
            "coverage": len(successful) / len(eligible) if eligible else None,
            "end_to_end_accuracy": sum(a == b for a, b in zip(truth, guesses, strict=True)) / len(eligible) if eligible else None,
            "abstention_rate": guesses.count(ABSTENTION[field]) / len(guesses) if guesses else None,
        })
        results[field] = metrics
    return {"dataset": manifest.name, "split": manifest.split, "cases": len(manifest.cases),
            "errors": dict(Counter(p["error"] for p in predictions.values() if "error" in p)),
            "fields": results, "auc_roc": "not computed: no calibrated continuous class scores"}


class Usage:
    def __init__(self):
        self.calls, self.tokens = 0, 0

    def usage(self, call_id, model, usage):
        self.calls += 1
        self.tokens += int(usage.get("totalTokenCount", 0))


async def predict_live(manifest, root):
    key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "")
    if not key or not re.fullmatch(r"gemini-[a-zA-Z0-9.-]+", model):
        raise ValueError("set GEMINI_API_KEY and a valid GEMINI_MODEL locally")
    usage = Usage()
    settings = SimpleNamespace(gemini_api_key=SecretStr(key), gemini_model=model)
    predictions, timings = {}, []
    async with httpx.AsyncClient(timeout=60, follow_redirects=False, trust_env=False,
                                 limits=httpx.Limits(max_connections=2, max_keepalive_connections=2)) as client:
        gemini = Gemini(settings, client, usage)
        for case in manifest.cases:
            start = time.monotonic()
            try:
                report = await gemini.analyze(case.text, (root / case.image).read_bytes(),
                                              "image/png", allowed_labels=case.allowed_labels)
                predictions[case.id] = {field: getattr(report, field) for field in CLASSES}
            except Problem as error:
                predictions[case.id] = {"error": error.code}
            except Exception:
                # Do not print provider bodies, image text, paths, or credentials.
                predictions[case.id] = {"error": "evaluation_failed"}
            timings.append(round(time.monotonic() - start, 3))
    return predictions, {"model": model, "api_responses_counted": usage.calls,
                         "tokens": usage.tokens, "latency_seconds": timings}


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--predictions", type=Path, help="offline JSON mapping case IDs to classes or error")
    mode.add_argument("--live", action="store_true", help="send dataset screenshots to paid Gemini API")
    parser.add_argument("--output", type=Path, required=True, help="new private result file; never overwritten")
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("output already exists")
        manifest = load_manifest(args.manifest)
        if args.live:
            predictions, metadata = asyncio.run(predict_live(manifest, args.manifest.parent))
        else:
            predictions = json.loads(args.predictions.read_text())
            metadata = {"mode": "offline; not evidence of live model quality"}
        result = score(manifest, predictions)
        result.update({"run": metadata, "created_at": datetime.now(timezone.utc).isoformat(),
                       "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                       "image_sha256": {c.id: hashlib.sha256((args.manifest.parent / c.image).read_bytes()).hexdigest() for c in manifest.cases},
                       "analyzer_sha256": hashlib.sha256(inspect.getsource(Gemini).encode()).hexdigest(),
                       "schema_sha256": hashlib.sha256(json.dumps(Report.model_json_schema(), sort_keys=True).encode()).hexdigest(),
                       "predictions": predictions})
        write_private(args.output, result)
        print(f"Evaluated {len(manifest.cases)} cases. Errors: {sum(result['errors'].values())}. Private report written.")
        return 2 if result["errors"] else 0
    except (ValueError, OSError):
        print("Evaluation refused: validate manifest, image paths, classes, environment and output destination.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
