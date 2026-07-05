"""Калибровка порогов Trust Score на размеченном корпусе.

Вопрос калибровки: при каких порогах BLOCK-решение статического слоя
максимизирует F1 на defective samples при ограничении на false positive rate
по clean-группе. Отдельно печатается таблица verdict-распределений, чтобы
docs/scoring_rationale.md ссылался на воспроизводимый расчет, а не на
магические числа.

Запуск:
    python experiment/calibrate.py --corpus experiment/corpus/corpus.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trustgate.config import Config
from trustgate.detectors import run_static
from trustgate.scoring import BLOCK_ON_CRITICAL_COUNT, aggregate

from benchmark_external import expected_bad, load_corpus  # trustgate: ignore TG-D01


def static_scores(corpus: list[dict], cfg: Config) -> list[tuple[bool, int, int]]:
    """(is_defective, score, criticals) per sample; unparseable -> score 0."""
    rows = []
    for item in corpus:
        bad = expected_bad(item.get("label"))
        try:
            findings = run_static(item["code"])
        except SyntaxError:
            rows.append((bad, 0, 99))
            continue
        skip = {"ran": False, "reason": "calibration_static_only"}
        _, score, _ = aggregate(findings, skip, skip, cfg)
        criticals = sum(1 for f in findings if f.severity == "critical")
        rows.append((bad, score, criticals))
    return rows


def block_metrics(rows, block_at: int, critical_count: int) -> dict:
    tp = fp = tn = fn = 0
    for bad, score, criticals in rows:
        blocked = score <= block_at or criticals >= critical_count
        if bad and blocked:
            tp += 1
        elif bad:
            fn += 1
        elif blocked:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {
        "block_threshold": block_at,
        "critical_count": critical_count,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "fpr": round(fpr, 4),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate Trust Score thresholds")
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--max-fpr", type=float, default=0.10,
                        help="acceptable BLOCK rate on clean samples")
    parser.add_argument("--out", default="", help="write JSON result here")
    args = parser.parse_args(argv)

    cfg = Config()
    rows = static_scores(load_corpus(Path(args.corpus)), cfg)

    grid = []
    for block_at in range(0, 80, 5):
        for critical_count in (1, 2, 3, 4, 99):
            grid.append(block_metrics(rows, block_at, critical_count))

    feasible = [g for g in grid if g["fpr"] <= args.max_fpr]
    best = max(feasible or grid, key=lambda g: (g["f1"], -g["fpr"]))

    current = block_metrics(rows, cfg.thresholds["block"], BLOCK_ON_CRITICAL_COUNT)
    result = {
        "samples": len(rows),
        "defective": sum(1 for bad, _, _ in rows if bad),
        "clean": sum(1 for bad, _, _ in rows if not bad),
        "max_fpr_constraint": args.max_fpr,
        "current_defaults": current,
        "best": best,
        "grid_top10": sorted(grid, key=lambda g: -g["f1"])[:10],
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
