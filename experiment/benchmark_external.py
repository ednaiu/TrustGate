"""Внешний benchmark: TrustGate против ruff, flake8, bandit, semgrep."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trustgate.config import Config
from trustgate.engine import analyze_source


BAD_LABELS = {"bad", "defective", "unsafe", "vulnerable", "hallucinated", "1", 1, True}


def load_corpus(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("corpus must be a JSON list or JSONL file")
    return data


def expected_bad(label) -> bool:
    return label in BAD_LABELS or str(label).lower() in BAD_LABELS


def confusion(expected: list[bool], predicted: list[bool]) -> dict:
    tp = sum(1 for e, p in zip(expected, predicted) if e and p)
    tn = sum(1 for e, p in zip(expected, predicted) if not e and not p)
    fp = sum(1 for e, p in zip(expected, predicted) if not e and p)
    fn = sum(1 for e, p in zip(expected, predicted) if e and not p)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def trustgate_predict(code: str) -> tuple[bool, list[str]]:
    result = analyze_source(
        code,
        "<sample>",
        cfg=Config(),
        no_sandbox=True,
        no_mutation=True,
        warn=lambda _: None,
    )
    findings = result["layers"]["static"]["findings"]
    return bool(findings), [item["detector"] for item in findings]


def _run(command: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    return proc.returncode, proc.stdout + proc.stderr


def baseline_predict(tool: str, sample_path: Path) -> tuple[bool | None, str]:
    if shutil.which(tool) is None:
        return None, "not_installed"
    if tool == "ruff":
        code, output = _run(["ruff", "check", "--output-format", "json", str(sample_path)], sample_path.parent)
        return code != 0, output[-2000:]
    if tool == "flake8":
        code, output = _run(["flake8", str(sample_path)], sample_path.parent)
        return code != 0, output[-2000:]
    if tool == "bandit":
        code, output = _run(["bandit", "-q", "-f", "json", str(sample_path)], sample_path.parent)
        return code != 0, output[-2000:]
    if tool == "semgrep":
        code, output = _run(["semgrep", "--quiet", "--json", "--config", "auto", str(sample_path)], sample_path.parent)
        return code != 0, output[-2000:]
    raise ValueError(tool)


def evaluate(corpus: list[dict], min_samples: int = 100) -> dict:
    expected = [expected_bad(item.get("label")) for item in corpus]
    trustgate_pred = []
    trustgate_reasons = []
    baselines = {name: [] for name in ("ruff", "flake8", "bandit", "semgrep")}
    baseline_notes = {name: [] for name in baselines}

    with tempfile.TemporaryDirectory(prefix="trustgate-benchmark-") as tmp:
        tmp_path = Path(tmp)
        for index, item in enumerate(corpus):
            code = item["code"]
            pred, reasons = trustgate_predict(code)
            trustgate_pred.append(pred)
            trustgate_reasons.append(reasons)

            sample_path = tmp_path / f"sample_{index}.py"
            sample_path.write_text(code, encoding="utf-8")
            for tool in baselines:
                pred_base, note = baseline_predict(tool, sample_path)
                baselines[tool].append(pred_base)
                baseline_notes[tool].append(note)

    metrics = {"trustgate": confusion(expected, trustgate_pred)}
    for tool, predictions in baselines.items():
        available = [p is not None for p in predictions]
        if not all(available):
            metrics[tool] = {"available": False, "reason": "tool_not_installed"}
            continue
        metrics[tool] = {"available": True, **confusion(expected, [bool(p) for p in predictions])}

    false_positives = [
        {
            "id": item.get("id", str(i)),
            "tool": "trustgate",
            "detectors": trustgate_reasons[i],
        }
        for i, item in enumerate(corpus)
        if not expected[i] and trustgate_pred[i]
    ]
    for tool, predictions in baselines.items():
        if not all(p is not None for p in predictions):
            continue
        false_positives.extend(
            {"id": corpus[i].get("id", str(i)), "tool": tool, "detectors": []}
            for i, pred in enumerate(predictions)
            if not expected[i] and pred
        )

    status = "ok" if len(corpus) >= min_samples else "needs_corpus"
    return {
        "status": status,
        "samples": len(corpus),
        "minimum_required_samples": min_samples,
        "metrics": metrics,
        "false_positive_analysis": false_positives,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="TrustGate external benchmark")
    parser.add_argument("--corpus", required=True, help="JSON/JSONL corpus with id, label, code")
    parser.add_argument("--out", default="", help="write JSON result to this path")
    parser.add_argument("--min-samples", type=int, default=100)
    args = parser.parse_args(argv)

    result = evaluate(load_corpus(Path(args.corpus)), min_samples=args.min_samples)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
