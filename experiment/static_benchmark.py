"""Run a small reproducible benchmark for TrustGate static detectors.

This is a curated smoke benchmark, not the final research corpus. It exists so
portfolio claims can be regenerated from versioned data instead of screenshots.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trustgate.config import Config  # noqa: E402
from trustgate.detectors import run_static  # noqa: E402
from trustgate.scoring import aggregate  # noqa: E402

HERE = Path(__file__).parent
CASES = HERE / "static_benchmark_cases.json"


def flag_trustgate(code: str) -> tuple[bool, list[str], str, int]:
    findings = run_static(code)
    _, score, verdict = aggregate(
        findings,
        {"ran": False, "reason": "benchmark_static_only"},
        {"ran": False, "reason": "benchmark_static_only"},
        Config(),
    )
    return bool(findings), [f.detector for f in findings], verdict, score


def metrics(rows):
    tp = fp = tn = fn = 0
    for row in rows:
        defective = row["label"] == "defective"
        flagged = row["flagged"]
        if defective and flagged:
            tp += 1
        elif defective:
            fn += 1
        elif flagged:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "fpr": round(fpr, 3),
    }


def main():
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    rows = []
    detector_hits = 0
    expected_total = 0
    for case in cases:
        flagged, detectors, verdict, score = flag_trustgate(case["code"])
        expected = case.get("expected")
        if expected:
            expected_total += 1
            detector_hits += int(expected in detectors)
        rows.append({
            "id": case["id"],
            "label": case["label"],
            "flagged": flagged,
            "detectors": detectors,
            "verdict": verdict,
            "score": score,
            "expected": expected,
            "expected_hit": expected in detectors if expected else None,
        })

    report = {
        "corpus": "experiment/static_benchmark_cases.json",
        "corpus_size": len(cases),
        "defective": sum(1 for c in cases if c["label"] == "defective"),
        "clean": sum(1 for c in cases if c["label"] == "clean"),
        "trustgate": metrics(rows),
        "expected_detector_recall": round(detector_hits / expected_total, 3),
        "cases": rows,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
