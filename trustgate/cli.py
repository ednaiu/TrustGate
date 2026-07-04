import argparse
import ast
import json
import sys
import time
from pathlib import Path

from . import detectors, mutation, report, sandbox, scoring
from .config import Config

EXIT = {"PASS": 0, "REVIEW": 1, "BLOCK": 2}
EXIT_INPUT_ERROR = 3
EXIT_INTERNAL = 4


class Parser(argparse.ArgumentParser):
    # argparse exits with 2 on usage errors, which collides with BLOCK
    def error(self, message):
        self.exit(EXIT_INPUT_ERROR, f"trustgate: {message}\n")


def _fail_input(msg):
    print(f"trustgate: {msg}", file=sys.stderr)
    sys.exit(EXIT_INPUT_ERROR)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        _fail_input(f"{path.name} is not valid utf-8")


def check(args) -> int:
    path = Path(args.file)
    if not path.is_file():
        _fail_input(f"file not found: {path}")
    source = _read(path)
    try:
        ast.parse(source)
    except SyntaxError as e:
        _fail_input(f"syntax error in {path.name}, line {e.lineno}: {e.msg}")

    tests = None
    if args.tests:
        tests_path = Path(args.tests)
        if not tests_path.is_file():
            _fail_input(f"tests file not found: {tests_path}")
        tests = _read(tests_path)

    cfg = Config(Path(args.config)) if args.config else Config()

    timing = {}
    t0 = time.monotonic()
    findings = detectors.run_static(source)
    timing["static"] = int((time.monotonic() - t0) * 1000)

    use_sandbox = not args.no_sandbox
    if use_sandbox and not sandbox.available():
        print("trustgate: docker unavailable, falling back to --no-sandbox", file=sys.stderr)
        use_sandbox = False
    # no sandbox means we must not execute mutants either (NS-9)
    use_mutation = use_sandbox and not args.no_mutation

    dynamic = None
    if use_sandbox and tests is not None:
        if sandbox.ensure_image():
            t0 = time.monotonic()
            dynamic = sandbox.run_tests(source, tests)
            timing["dynamic"] = int((time.monotonic() - t0) * 1000)
        else:
            print("trustgate: cannot build runner image, skipping sandbox", file=sys.stderr)
            use_sandbox = use_mutation = False

    mut = None
    if use_mutation:
        if tests is None:
            mut = {"ran": False, "reason": "no_tests"}
        elif dynamic and dynamic.get("ran"):
            baseline_green = not (dynamic.get("tests_failed") or dynamic.get("build_error")
                                  or dynamic.get("timeout"))
            if baseline_green:
                t0 = time.monotonic()
                mut = mutation.evaluate(source, tests, sandbox.run_tests)
                timing["mutation"] = int((time.monotonic() - t0) * 1000)
            else:
                # red baseline kills every mutant for free, the score would be garbage
                mut = {"ran": False, "reason": "red_baseline"}

    if dynamic is None:
        dynamic = {"ran": False, "reason": "no_tests" if tests is None else "disabled"}

    partial = args.no_sandbox or args.no_mutation or not use_sandbox
    raw, score, verdict = scoring.aggregate(findings, dynamic, mut, cfg)
    result = report.build(path, raw, score, verdict, partial,
                          findings, dynamic, mut, timing)

    if args.json:
        report.dump(result, args.json)
    print(report.to_markdown(result))
    return EXIT[verdict]


def render(args) -> int:
    path = Path(args.report_file)
    if not path.is_file():
        _fail_input(f"report not found: {path}")
    try:
        data = json.loads(_read(path))
    except json.JSONDecodeError:
        _fail_input(f"not a valid trustgate report: {path}")
    print(report.to_markdown(data))
    return 0


def main(argv=None) -> int:
    parser = Parser(prog="trustgate",
                    description="Trust scoring for LLM-generated Python code")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="analyze a python file")
    p_check.add_argument("file")
    p_check.add_argument("--tests", help="pytest file for the dynamic layer")
    p_check.add_argument("--config", help="weights.toml with custom penalties")
    p_check.add_argument("--json", help="write the full report to this path")
    p_check.add_argument("--no-sandbox", action="store_true")
    p_check.add_argument("--no-mutation", action="store_true")

    p_report = sub.add_parser("report", help="render a saved JSON report")
    p_report.add_argument("report_file")

    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            return check(args)
        return render(args)
    except SystemExit:
        raise
    except Exception as e:  # anything unexpected is exit 4, not a traceback
        print(f"trustgate: internal error: {e}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
