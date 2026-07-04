import json

REPORT_VERSION = "1.0"


def build(target, raw_score, score, verdict, partial, findings, dynamic, mutation, timing_ms):
    return {
        "version": REPORT_VERSION,
        "target": str(target),
        "score": score,
        "raw_score": raw_score,
        "verdict": verdict,
        "partial": partial,
        "layers": {
            "static": {"ran": True, "findings": [f.to_dict() for f in findings]},
            "dynamic": dynamic or {"ran": False, "reason": "disabled"},
            "mutation": mutation or {"ran": False, "reason": "disabled"},
        },
        "timing_ms": timing_ms,
    }


def to_markdown(report: dict) -> str:
    lines = [
        f"## TrustGate: **{report['verdict']}** (score {report['score']}/100)",
        "",
        f"Target: `{report['target']}`" + ("  ·  *partial analysis*" if report["partial"] else ""),
        "",
    ]
    findings = report["layers"]["static"]["findings"]
    if findings:
        lines.append("| line | detector | severity | message | -pts |")
        lines.append("|------|----------|----------|---------|------|")
        top = sorted(findings, key=lambda f: -f["penalty"])[:5]
        for f in top:
            lines.append(f"| {f['line']} | {f['detector']} | {f['severity']} "
                         f"| {f['message']} | {f['penalty']} |")
        if len(findings) > 5:
            lines.append(f"\n…and {len(findings) - 5} more findings.")
    else:
        lines.append("No static findings.")

    dyn = report["layers"]["dynamic"]
    if dyn.get("ran"):
        lines.append(f"\nTests: {dyn['tests_total'] - dyn['tests_failed']}/{dyn['tests_total']} passed"
                     + (", **timeout**" if dyn.get("timeout") else ""))
    mut = report["layers"]["mutation"]
    if mut.get("ran"):
        lines.append(f"Mutation score: {mut['mutation_score']:.2f} "
                     f"({mut['mutants_killed']}/{mut['mutants_total']} killed)")
    return "\n".join(lines)


def dump(report: dict, path) -> None:
    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
