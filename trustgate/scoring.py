"""Trust Score aggregation, see spec sections FR-SCR-1..5."""
from .config import Config
from .findings import Finding

CRITICAL_DETECTORS = {"TG-D01", "TG-D02", "TG-D03", "TG-D04"}
BLOCK_ON_CRITICAL_COUNT = 3


def static_penalty(findings: list[Finding], cfg: Config) -> int:
    """Also fills in Finding.penalty on each finding (the report shows them)."""
    per_detector: dict[str, int] = {}
    for f in findings:
        f.penalty = cfg.penalty_for(f.detector, f.severity)
        per_detector[f.detector] = per_detector.get(f.detector, 0) + f.penalty

    total = 0
    for detector, amount in per_detector.items():
        if detector in CRITICAL_DETECTORS:
            total += amount  # critical findings never saturate
        else:
            total += min(amount, cfg.saturation)
    return total


def dynamic_penalty(dynamic: dict | None, cfg: Config) -> int:
    if dynamic is None or not dynamic.get("ran"):
        return 0  # missing L2 only sets partial=true, no penalty by itself
    d = cfg.dynamic
    if dynamic.get("build_error"):
        return d["build_error"]
    penalty = 0
    failed = dynamic.get("tests_failed", 0)
    if failed:
        penalty = min(d["first_fail"] + d["next_fail"] * (failed - 1), d["fail_cap"])
    if dynamic.get("timeout"):
        penalty += d["timeout"]
    return penalty


def mutation_penalty(mutation: dict | None, cfg: Config) -> int:
    m = cfg.mutation
    if mutation is None or not mutation.get("ran"):
        # one uniform penalty for every "no mutation verdict" path (NS-13)
        return m["missing"]
    score = mutation["mutation_score"]
    if score < m["low_bound"]:
        return m["low"]
    if score < m["mid_bound"]:
        return m["mid"]
    return 0


def aggregate(findings, dynamic, mutation, cfg: Config):
    raw = 100 - static_penalty(findings, cfg) \
              - dynamic_penalty(dynamic, cfg) \
              - mutation_penalty(mutation, cfg)
    score = max(0, raw)

    criticals = sum(1 for f in findings if f.severity == "critical")
    if criticals >= BLOCK_ON_CRITICAL_COUNT or score <= cfg.thresholds["block"]:
        verdict = "BLOCK"
    elif score >= cfg.thresholds["pass"]:
        verdict = "PASS"
    else:
        verdict = "REVIEW"
    return raw, score, verdict
