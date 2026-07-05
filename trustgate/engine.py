"""Shared analysis pipeline used by CLI and project scanning."""
import time

from . import detectors, mutation, report, sandbox, scoring
from .config import Config


def analyze_source(
    source: str,
    target: str,
    tests: str | None = None,
    cfg: Config | None = None,
    no_sandbox: bool = False,
    no_mutation: bool = False,
    warn=None,
    ctx: detectors.ScanContext | None = None,
) -> dict:
    """Run TrustGate layers and return a report dict.

    The caller is responsible for syntax validation and for deciding whether
    dynamic execution is acceptable. If code is executed, it goes through the
    Docker sandbox runner only.
    """
    cfg = cfg or Config()
    warn = warn or (lambda message: None)

    timing = {}
    t0 = time.monotonic()
    findings = detectors.run_static(source, ctx=ctx)
    timing["static"] = int((time.monotonic() - t0) * 1000)

    use_sandbox = not no_sandbox
    if use_sandbox and not sandbox.available():
        warn("trustgate: docker unavailable, falling back to --no-sandbox")
        use_sandbox = False
    # no sandbox means we must not execute mutants either (NS-9)
    use_mutation = use_sandbox and not no_mutation

    dynamic = None
    if use_sandbox and tests is not None:
        if sandbox.ensure_image():
            t0 = time.monotonic()
            dynamic = sandbox.run_tests(source, tests)
            timing["dynamic"] = int((time.monotonic() - t0) * 1000)
        else:
            warn("trustgate: cannot build runner image, skipping sandbox")
            use_sandbox = use_mutation = False

    mut = None
    if use_mutation:
        if tests is None:
            mut = {"ran": False, "reason": "no_tests"}
        elif dynamic and dynamic.get("ran"):
            baseline_green = not (
                dynamic.get("tests_failed")
                or dynamic.get("build_error")
                or dynamic.get("timeout")
            )
            if baseline_green:
                t0 = time.monotonic()
                mut = mutation.evaluate(source, tests, sandbox.run_tests)
                timing["mutation"] = int((time.monotonic() - t0) * 1000)
            else:
                # Red baseline would kill every mutant for free and skew the score.
                mut = {"ran": False, "reason": "red_baseline"}

    if dynamic is None:
        dynamic = {"ran": False, "reason": "no_tests" if tests is None else "disabled"}

    partial = no_sandbox or no_mutation or not use_sandbox
    raw, score, verdict = scoring.aggregate(findings, dynamic, mut, cfg, partial=partial)
    return report.build(target, raw, score, verdict, partial, findings, dynamic, mut, timing)
