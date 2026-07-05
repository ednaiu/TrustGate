import argparse
import ast
import json
import sys
from pathlib import Path

from . import history
from . import policy
from . import report
from . import scan as project_scan
from .config import Config
from .detectors import ScanContext
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
        ctx=ScanContext(trust_local_env=args.trust_local_env),
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
    policy_data = policy.load_policy(Path(args.policy)) if args.policy else None
    if policy_data:
        try:
            active_role = policy.resolve_role(policy_data, args.user, args.role)
        except ValueError as exc:
            _fail_input(str(exc))
        policy_data["active_role"] = active_role
        policy_data["active_user"] = args.user
    result = project_scan.scan_project(
        root,
        changed=args.changed,
        base=args.base,
        cfg=cfg,
        project_tests=args.project_tests,
        project_test_timeout=args.project_test_timeout,
        project_mutation=args.project_mutation,
        project_mutation_limit=args.project_mutation_limit,
        policy_data=policy_data,
        warn=lambda message: print(message, file=sys.stderr),
        trust_local_env=args.trust_local_env,
    )

    if args.json:
        project_scan.dump(result, args.json)
    if args.html:
        project_scan.dump_html(result, args.html)
    if args.sarif:
        project_scan.dump_sarif(result, args.sarif)
    if args.github_annotations:
        project_scan.dump_github_annotations(result, args.github_annotations)
    if args.save_history:
        scan_id = history.save_scan(result, args.save_history)
        print(f"trustgate: saved scan #{scan_id} to {args.save_history}", file=sys.stderr)
    print(project_scan.to_markdown(result))
    return EXIT[result["verdict"]]


def history_cmd(args) -> int:
    rows = history.list_scans(args.db, limit=args.limit)
    if not rows:
        print("No saved TrustGate scans.")
        return 0
    print("| id | verdict | score | findings | syntax errors | target |")
    print("|----|---------|-------|----------|---------------|--------|")
    for row in rows:
        print(
            f"| {row['id']} | {row['verdict']} | {row['score']} | "
            f"{row['findings']} | {row['syntax_errors']} | {row['target']} |"
        )
    return 0


def dashboard_cmd(args) -> int:
    html = history.render_dashboard(args.db, title=args.title)
    Path(args.html).write_text(html, encoding="utf-8")
    print(f"TrustGate dashboard written to {args.html}")
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
    p_check.add_argument("--html", help="write a self-contained HTML report")
    p_check.add_argument("--no-sandbox", action="store_true")
    p_check.add_argument("--no-mutation", action="store_true")
    p_check.add_argument("--trust-local-env", action="store_true",
                         help="also accept packages installed in the local "
                              "environment (verdict becomes machine-dependent)")

    p_report = sub.add_parser("report", help="render a saved JSON report")
    p_report.add_argument("report_file")
    p_report.add_argument("--html", help="write a self-contained HTML report")

    p_history = sub.add_parser("history", help="show saved project scan history")
    p_history.add_argument("--db", default="trustgate-history.sqlite")
    p_history.add_argument("--limit", type=int, default=10)

    p_dashboard = sub.add_parser("dashboard", help="render saved scan history as HTML")
    p_dashboard.add_argument("--db", default="trustgate-history.sqlite")
    p_dashboard.add_argument("--html", default="trustgate-dashboard.html")
    p_dashboard.add_argument("--title", default="TrustGate dashboard")

    p_scan = sub.add_parser("scan", help="scan a project directory or git changes")
    p_scan.add_argument("path", nargs="?", default=".")
    p_scan.add_argument("--changed", action="store_true",
                        help="scan changed and untracked Python files only")
    p_scan.add_argument("--base", default="HEAD",
                        help="git base for --changed, default: HEAD")
    p_scan.add_argument("--config", help="weights.toml with custom penalties")
    p_scan.add_argument("--project-tests",
                        help="trusted project test command, e.g. 'python -m pytest -q'")
    p_scan.add_argument("--project-test-timeout", type=int, default=120)
    p_scan.add_argument("--project-mutation", action="store_true",
                        help="run repository-level mutation analysis with project tests")
    p_scan.add_argument("--project-mutation-limit", type=int, default=20)
    p_scan.add_argument("--policy", help="policy TOML for CI gates and roles")
    p_scan.add_argument("--role", help="active role name from the policy file")
    p_scan.add_argument("--user", help="active user name from the policy file")
    p_scan.add_argument("--json", help="write the full project report to this path")
    p_scan.add_argument("--html", help="write a self-contained HTML project report")
    p_scan.add_argument("--sarif", help="write SARIF for GitHub code scanning")
    p_scan.add_argument("--github-annotations", help="write GitHub Checks annotations JSON")
    p_scan.add_argument("--save-history", help="append scan summary to a SQLite database")
    p_scan.add_argument("--trust-local-env", action="store_true",
                        help="also accept packages installed in the local "
                             "environment (verdict becomes machine-dependent)")

    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            return check(args)
        if args.command == "report":
            return render(args)
        if args.command == "history":
            return history_cmd(args)
        if args.command == "dashboard":
            return dashboard_cmd(args)
        return scan(args)
    except SystemExit:
        raise
    except Exception as e:  # anything unexpected is exit 4, not a traceback
        print(f"trustgate: internal error: {e}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
