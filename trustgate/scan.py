"""Project and git-diff scanning helpers."""
import ast
import json
import subprocess
import time
from pathlib import Path

from .config import Config
from .engine import analyze_source
from .findings import Finding
from . import report, scoring

SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "build",
    "dist",
    "__pycache__",
}


def _git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
        )
    except OSError:
        return subprocess.CompletedProcess(args, 127, "", "git unavailable")


def is_git_repo(root: Path) -> bool:
    proc = _git(root, ["rev-parse", "--is-inside-work-tree"])
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _git_files(root: Path) -> list[Path]:
    proc = _git(root, ["ls-files", "--", "*.py"])
    if proc.returncode != 0:
        return []
    return [root / line for line in proc.stdout.splitlines() if line]


def _changed_git_files(root: Path, base: str) -> list[Path]:
    changed = set()
    proc = _git(root, ["diff", "--name-only", "--diff-filter=ACMRT", base, "--", "*.py"])
    if proc.returncode == 0:
        changed.update(line for line in proc.stdout.splitlines() if line)
    proc = _git(root, ["ls-files", "--others", "--exclude-standard", "--", "*.py"])
    if proc.returncode == 0:
        changed.update(line for line in proc.stdout.splitlines() if line)
    return [root / line for line in sorted(changed)]


def _walk_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return sorted(files)


def discover_python_files(root: Path, changed: bool = False, base: str = "HEAD") -> list[Path]:
    root = root.resolve()
    if is_git_repo(root):
        files = _changed_git_files(root, base) if changed else _git_files(root)
        return [p for p in files if p.is_file()]
    if changed:
        return []
    return _walk_files(root)


def _read_utf8(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return None, "not valid utf-8"


def _finding_from_dict(item: dict) -> Finding:
    return Finding(item["detector"], item["severity"], item["line"], item["message"])


def scan_project(
    root: Path,
    changed: bool = False,
    base: str = "HEAD",
    cfg: Config | None = None,
    warn=None,
) -> dict:
    cfg = cfg or Config()
    warn = warn or (lambda message: None)
    root = root.resolve()
    started = time.monotonic()
    files = discover_python_files(root, changed=changed, base=base)

    file_reports = []
    syntax_errors = []
    static_findings = []
    for path in files:
        rel = path.relative_to(root)
        source, error = _read_utf8(path)
        if error:
            syntax_errors.append({"file": str(rel), "line": 0, "message": error})
            continue
        try:
            ast.parse(source)
        except SyntaxError as exc:
            syntax_errors.append({
                "file": str(rel),
                "line": exc.lineno or 0,
                "message": exc.msg,
            })
            continue

        single = analyze_source(
            source,
            str(rel),
            cfg=cfg,
            no_sandbox=True,
            no_mutation=True,
            warn=warn,
        )
        for item in single["layers"]["static"]["findings"]:
            with_file = dict(item)
            with_file["file"] = str(rel)
            static_findings.append(with_file)
        file_reports.append(single)

    finding_objects = [_finding_from_dict(item) for item in static_findings]
    raw, score, verdict = scoring.aggregate(
        finding_objects,
        {"ran": False, "reason": "project_scan_static_only"},
        {"ran": False, "reason": "project_scan_static_only"},
        cfg,
    )
    if syntax_errors:
        raw = min(raw, 0)
        score = 0
        verdict = "BLOCK"

    return {
        "version": report.REPORT_VERSION,
        "mode": "changed" if changed else "project",
        "target": str(root),
        "base": base if changed else None,
        "score": score,
        "raw_score": raw,
        "verdict": verdict,
        "partial": True,
        "summary": {
            "files_scanned": len(files),
            "files_analyzed": len(file_reports),
            "findings": len(static_findings),
            "syntax_errors": len(syntax_errors),
        },
        "files": file_reports,
        "findings": static_findings,
        "syntax_errors": syntax_errors,
        "timing_ms": {"scan": int((time.monotonic() - started) * 1000)},
    }


def to_markdown(scan_report: dict) -> str:
    summary = scan_report["summary"]
    mode = "changed files" if scan_report["mode"] == "changed" else "project"
    lines = [
        f"## TrustGate scan: **{scan_report['verdict']}** "
        f"(score {scan_report['score']}/100)",
        "",
        f"Target: `{scan_report['target']}`  ·  mode: `{mode}`  ·  *partial analysis*",
        "",
        f"Files scanned: {summary['files_scanned']}; "
        f"findings: {summary['findings']}; "
        f"syntax errors: {summary['syntax_errors']}",
        "",
    ]
    if scan_report["syntax_errors"]:
        lines.append("| file | line | error |")
        lines.append("|------|------|-------|")
        for item in scan_report["syntax_errors"][:10]:
            lines.append(f"| {item['file']} | {item['line']} | {item['message']} |")
        lines.append("")

    if scan_report["findings"]:
        lines.append("| file | line | detector | severity | message | -pts |")
        lines.append("|------|------|----------|----------|---------|------|")
        top = sorted(scan_report["findings"], key=lambda f: -f["penalty"])[:20]
        for item in top:
            lines.append(
                f"| {item['file']} | {item['line']} | {item['detector']} | "
                f"{item['severity']} | {item['message']} | {item['penalty']} |"
            )
        if len(scan_report["findings"]) > 20:
            lines.append(f"\n...and {len(scan_report['findings']) - 20} more findings.")
    else:
        lines.append("No static findings.")
    return "\n".join(lines)


def to_html(scan_report: dict) -> str:
    single_like = {
        "target": scan_report["target"],
        "score": scan_report["score"],
        "verdict": scan_report["verdict"],
        "partial": True,
        "layers": {
            "static": {"findings": scan_report["findings"]},
            "dynamic": {"ran": False, "reason": "project_scan_static_only"},
            "mutation": {"ran": False, "reason": "project_scan_static_only"},
        },
        "timing_ms": scan_report["timing_ms"],
    }
    html = report.to_html(single_like)
    summary = scan_report["summary"]
    extra = (
        "<section class='box' style='margin-top:16px'>"
        "<div class='label'>Project scan</div>"
        f"<div class='value'>Files scanned: {summary['files_scanned']}; "
        f"findings: {summary['findings']}; "
        f"syntax errors: {summary['syntax_errors']}</div>"
        "</section>"
    )
    return html.replace("</section>\n  <h2>Findings</h2>", "</section>\n  " + extra + "\n  <h2>Findings</h2>")


def dump(scan_report: dict, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scan_report, f, indent=2, ensure_ascii=False)


def dump_html(scan_report: dict, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_html(scan_report))
