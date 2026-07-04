import argparse
import ast
import json
import sys
from pathlib import Path

from . import report
from . import scan as project_scan
from .config import Config
from .engine import analyze_source

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

    result = analyze_source(
        source,
        str(path),
        tests=tests,
        cfg=cfg,
        no_sandbox=args.no_sandbox,
        no_mutation=args.no_mutation,
        warn=lambda message: print(message, file=sys.stderr),
    )

    if args.json:
        report.dump(result, args.json)
    if args.html:
        report.dump_html(result, args.html)
    print(report.to_markdown(result))
    return EXIT[result["verdict"]]


def render(args) -> int:
    path = Path(args.report_file)
    if not path.is_file():
        _fail_input(f"report not found: {path}")
    try:
        data = json.loads(_read(path))
    except json.JSONDecodeError:
        _fail_input(f"not a valid trustgate report: {path}")
    if args.html:
        report.dump_html(data, args.html)
    print(report.to_markdown(data))
    return 0


def scan(args) -> int:
    root = Path(args.path)
    if not root.is_dir():
        _fail_input(f"directory not found: {root}")
    cfg = Config(Path(args.config)) if args.config else Config()
    result = project_scan.scan_project(
        root,
        changed=args.changed,
        base=args.base,
        cfg=cfg,
        warn=lambda message: print(message, file=sys.stderr),
    )

    if args.json:
        project_scan.dump(result, args.json)
    if args.html:
        project_scan.dump_html(result, args.html)
    print(project_scan.to_markdown(result))
    return EXIT[result["verdict"]]


def main(argv=None) -> int:
    parser = Parser(prog="trustgate",
                    description="Trust scoring for LLM-generated Python code")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="analyze a python file")
    p_check.add_argument("file")
    p_check.add_argument("--tests", help="pytest file for the dynamic layer")
    p_check.add_argument("--config", help="weights.toml with custom penalties")
    p_check.add_argument("--json", help="write the full report to this path")
    p_check.add_argument("--html", help="write a self-contained HTML report")
    p_check.add_argument("--no-sandbox", action="store_true")
    p_check.add_argument("--no-mutation", action="store_true")

    p_report = sub.add_parser("report", help="render a saved JSON report")
    p_report.add_argument("report_file")
    p_report.add_argument("--html", help="write a self-contained HTML report")

    p_scan = sub.add_parser("scan", help="scan a project directory or git changes")
    p_scan.add_argument("path", nargs="?", default=".")
    p_scan.add_argument("--changed", action="store_true",
                        help="scan changed and untracked Python files only")
    p_scan.add_argument("--base", default="HEAD",
                        help="git base for --changed, default: HEAD")
    p_scan.add_argument("--config", help="weights.toml with custom penalties")
    p_scan.add_argument("--json", help="write the full project report to this path")
    p_scan.add_argument("--html", help="write a self-contained HTML project report")

    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            return check(args)
        if args.command == "report":
            return render(args)
        return scan(args)
    except SystemExit:
        raise
    except Exception as e:  # anything unexpected is exit 4, not a traceback
        print(f"trustgate: internal error: {e}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
