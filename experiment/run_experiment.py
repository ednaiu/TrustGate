"""Label generated solutions against reference tests, then measure TrustGate
vs a flake8+bandit baseline on the labeled corpus (FR-EXP-4).

Usage:
    python run_experiment.py --label     # split raw solutions into clean/defective
    python run_experiment.py --measure   # produce results/metrics.json
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trustgate.config import Config          # noqa: E402
from trustgate.detectors import run_static   # noqa: E402
from trustgate.scoring import aggregate      # noqa: E402

HERE = Path(__file__).parent
RESULTS = HERE / "results"


def label():
    """Run every raw solution against its reference tests, split by outcome."""
    from trustgate import sandbox
    if not sandbox.available() or not sandbox.ensure_image():
        raise SystemExit("labeling needs Docker (reference tests must actually run)")

    clean_dir = HERE / "labeled" / "clean"
    bad_dir = HERE / "labeled" / "defective"
    clean_dir.mkdir(parents=True, exist_ok=True)
    bad_dir.mkdir(parents=True, exist_ok=True)

    for raw in sorted((HERE / "raw").glob("*/*.json")):
        sample = json.loads(raw.read_text(encoding="utf-8"))
        tests = (HERE / "tasks" / sample["task"] / "reference_tests.py")
        result = sandbox.run_tests(sample["code"], tests.read_text(encoding="utf-8"))
        ok = result.get("ran") and not result.get("build_error") \
            and result.get("tests_failed") == 0 and result.get("tests_total", 0) > 0
        dest = clean_dir if ok else bad_dir
        (dest / f"{sample['model']}__{sample['task']}.py").write_text(
            sample["code"], encoding="utf-8")
        print(f"{'clean' if ok else 'defective':9} {sample['model']}/{sample['task']}")


def trustgate_flags(source: str) -> bool:
    findings = run_static(source)
    _, score, verdict = aggregate(findings, None, {"ran": False}, Config())
    return verdict != "PASS"


def baseline_flags(path: Path) -> bool:
    for tool in (["flake8", "--select=F821,F401,E999", str(path)],
                 ["bandit", "-q", str(path)]):
        if shutil.which(tool[0]) is None:
            continue
        if subprocess.run(tool, capture_output=True).returncode != 0:
            return True
    return False


def measure():
    samples = []
    for path in sorted((HERE / "labeled" / "clean").glob("*.py")):
        samples.append((path, False))
    for path in sorted((HERE / "labeled" / "defective").glob("*.py")):
        samples.append((path, True))
    for path in sorted((HERE / "labeled" / "injected").glob("*.py")):
        samples.append((path, True))
    if not samples:
        raise SystemExit("empty corpus, run --label and inject_defects.py first")

    def metrics(flag_fn, by_path):
        tp = fp = tn = fn = 0
        for path, defective in samples:
            flagged = flag_fn(path) if by_path else flag_fn(path.read_text(encoding="utf-8"))
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
        fpr = fp / (fp + tn) if fp + tn else 0.0
        return {"tp": tp, "fp": fp, "tn": tn, "fn": fn,
                "precision": round(precision, 3), "recall": round(recall, 3),
                "fpr": round(fpr, 3)}

    RESULTS.mkdir(exist_ok=True)
    report = {
        "corpus_size": len(samples),
        "defective": sum(1 for _, d in samples if d),
        "trustgate": metrics(trustgate_flags, by_path=False),
        "baseline_flake8_bandit": metrics(baseline_flags, by_path=True),
    }
    out = RESULTS / "metrics.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--label", action="store_true")
    group.add_argument("--measure", action="store_true")
    args = parser.parse_args()
    label() if args.label else measure()
