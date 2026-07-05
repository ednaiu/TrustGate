"""Внешний benchmark: TrustGate против ruff, flake8, bandit, semgrep.

Каждый sample записывается в файл sample_<i>.py, после чего каждый baseline
запускается один раз на всю директорию (per-file запуск semgrep занял бы часы),
а его вывод разбирается в вердикт по каждому файлу. "Инструмент пометил файл" =
инструмент как merge-gate завернул бы этот патч.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trustgate.config import Config
from trustgate.detectors import DETECTOR_CODES, run_static


BAD_LABELS = {"bad", "defective", "unsafe", "vulnerable", "hallucinated", "1", 1, True}
BASELINE_TOOLS = ("ruff", "flake8", "bandit", "semgrep")


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
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
    }


def trustgate_predict(code: str, disabled_detectors: set[str] | None = None) -> tuple[bool, list[str]]:
    try:
        findings = run_static(code, disabled_detectors=disabled_detectors)
    except SyntaxError:
        # trustgate scan blocks unparseable files, so this counts as flagged
        return True, ["syntax-error"]
    return bool(findings), [item.detector for item in findings]


# baseline tools installed next to the interpreter (venv) must be found even
# when the venv is not activated in the caller's shell
_PATH = f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}"


def _which(tool: str) -> str | None:
    return shutil.which(tool, path=_PATH)


def _run(command: list[str], cwd: Path, timeout: int = 1800) -> tuple[int, str]:
    env = {**os.environ, "PATH": _PATH}
    try:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return 124, ""
    return proc.returncode, proc.stdout


def tool_version(tool: str) -> str | None:
    if _which(tool) is None:
        return None
    code, out = _run([tool, "--version"], Path.cwd(), timeout=60)
    return out.strip().splitlines()[0] if code == 0 and out.strip() else "unknown"


def baseline_flagged_files(tool: str, samples_dir: Path) -> set[str] | None:
    """Run one tool over the whole samples directory, return flagged file names."""
    if _which(tool) is None:
        return None
    flagged = set()
    if tool == "ruff":
        _, out = _run(["ruff", "check", "--output-format", "json", "."], samples_dir)
        for item in json.loads(out or "[]"):
            flagged.add(Path(item["filename"]).name)
    elif tool == "flake8":
        _, out = _run(["flake8", "."], samples_dir)
        for line in out.splitlines():
            name = line.split(":", 1)[0].strip()
            if name.endswith(".py"):
                flagged.add(Path(name).name)
    elif tool == "bandit":
        _, out = _run(["bandit", "-q", "-r", "-f", "json", "."], samples_dir)
        data = json.loads(out or "{}")
        for item in data.get("results", []):
            flagged.add(Path(item["filename"]).name)
    elif tool == "semgrep":
        _, out = _run(["semgrep", "--quiet", "--json", "--config", "auto", "."], samples_dir)
        data = json.loads(out or "{}")
        for item in data.get("results", []):
            flagged.add(Path(item["path"]).name)
    else:
        raise ValueError(tool)
    return flagged


def evaluate(corpus: list[dict], min_samples: int = 100) -> dict:
    expected = [expected_bad(item.get("label")) for item in corpus]

    trustgate_pred = []
    trustgate_reasons = []
    for item in corpus:
        pred, reasons = trustgate_predict(item["code"])
        trustgate_pred.append(pred)
        trustgate_reasons.append(reasons)

    baselines: dict[str, list[bool] | None] = {}
    with tempfile.TemporaryDirectory(prefix="trustgate-benchmark-") as tmp:
        tmp_path = Path(tmp)
        names = []
        for index, item in enumerate(corpus):
            name = f"sample_{index}.py"
            (tmp_path / name).write_text(item["code"], encoding="utf-8")
            names.append(name)
        for tool in BASELINE_TOOLS:
            flagged = baseline_flagged_files(tool, tmp_path)
            baselines[tool] = None if flagged is None else [n in flagged for n in names]

    baseline_metrics = {}
    for tool, predictions in baselines.items():
        if predictions is None:
            baseline_metrics[tool] = {"available": False, "reason": "tool_not_installed"}
        else:
            baseline_metrics[tool] = {
                "available": True,
                "version": tool_version(tool),
                **confusion(expected, predictions),
            }

    trustgate_metrics = confusion(expected, trustgate_pred)
    ablation = {}
    for detector in DETECTOR_CODES:  # TG-D12 is manifest-level, out of scope here
        disabled_pred = [
            trustgate_predict(item["code"], disabled_detectors={detector})[0]
            for item in corpus
        ]
        disabled_metrics = confusion(expected, disabled_pred)
        ablation[detector] = {
            **disabled_metrics,
            "delta_precision": round(trustgate_metrics["precision"] - disabled_metrics["precision"], 4),
            "delta_recall": round(trustgate_metrics["recall"] - disabled_metrics["recall"], 4),
            "delta_f1": round(trustgate_metrics["f1"] - disabled_metrics["f1"], 4),
        }

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
        if predictions is None:
            continue
        false_positives.extend(
            {"id": corpus[i].get("id", str(i)), "tool": tool, "detectors": []}
            for i, pred in enumerate(predictions)
            if not expected[i] and pred
        )

    datasets = {}
    for item in corpus:
        ds = item.get("source", {}).get("dataset", "unknown")
        datasets[ds] = datasets.get(ds, 0) + 1

    # recall per defective slice: where each tool's blind spots are
    per_dataset_recall = {}
    for ds in datasets:
        idx = [
            i for i, item in enumerate(corpus)
            if item.get("source", {}).get("dataset", "unknown") == ds and expected[i]
        ]
        if not idx:
            continue
        slice_recall = {
            "defective_samples": len(idx),
            "trustgate": round(sum(1 for i in idx if trustgate_pred[i]) / len(idx), 4),
        }
        for tool, predictions in baselines.items():
            if predictions is not None:
                slice_recall[tool] = round(sum(1 for i in idx if predictions[i]) / len(idx), 4)
        per_dataset_recall[ds] = slice_recall

    status = "ok" if len(corpus) >= min_samples else "needs_corpus"
    return {
        "status": status,
        "samples": len(corpus),
        "minimum_required_samples": min_samples,
        "corpus_composition": {
            "defective": sum(expected),
            "clean": len(corpus) - sum(expected),
            "datasets": datasets,
        },
        "metrics": {
            "trustgate": trustgate_metrics,
            "baselines": baseline_metrics,
        },
        "per_dataset_recall": per_dataset_recall,
        "ablation": ablation,
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
