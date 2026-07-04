"""Project and git-diff scanning helpers."""
import ast
import json
import re
import shlex
import subprocess
import time
from pathlib import Path

from . import mutation
from .config import Config
from .engine import analyze_source
from .findings import Finding
from .known_packages import closest_popular, is_known
from . import report, scoring

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py3.10 uses package dependency
    import tomli as tomllib

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

MANIFEST_NAMES = {"pyproject.toml"}
REQUIREMENTS_RE = re.compile(r"(^|/)requirements[^/]*\.txt$")
REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


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


def _git_manifest_files(root: Path, changed: bool, base: str) -> list[Path]:
    if not is_git_repo(root):
        return []
    paths = set()
    if changed:
        proc = _git(root, ["diff", "--name-only", "--diff-filter=ACMRT", base])
        if proc.returncode == 0:
            paths.update(line for line in proc.stdout.splitlines() if line)
        proc = _git(root, ["ls-files", "--others", "--exclude-standard"])
        if proc.returncode == 0:
            paths.update(line for line in proc.stdout.splitlines() if line)
    else:
        proc = _git(root, ["ls-files"])
        if proc.returncode == 0:
            paths.update(line for line in proc.stdout.splitlines() if line)
    return [
        root / line for line in sorted(paths)
        if Path(line).name in MANIFEST_NAMES or REQUIREMENTS_RE.search(line)
    ]


def discover_manifest_files(root: Path, changed: bool = False, base: str = "HEAD") -> list[Path]:
    root = root.resolve()
    if is_git_repo(root):
        return [p for p in _git_manifest_files(root, changed, base) if p.is_file()]
    if changed:
        return []
    out = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        rel = str(path.relative_to(root))
        if path.name in MANIFEST_NAMES or REQUIREMENTS_RE.search(rel):
            out.append(path)
    return sorted(out)


def _read_utf8(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return None, "not valid utf-8"


def _finding_from_dict(item: dict) -> Finding:
    return Finding(item["detector"], item["severity"], item["line"], item["message"])


def _dependency_name(spec: str) -> str | None:
    cleaned = spec.strip()
    if not cleaned or cleaned.startswith(("#", "-", "git+", "http://", "https://")):
        return None
    match = REQ_NAME_RE.match(cleaned)
    if not match:
        return None
    return match.group(1).replace("_", "-")


def _line_for_text(source: str, text: str) -> int:
    needle = text.split(";", 1)[0].split("[", 1)[0].split("=", 1)[0].strip().strip('"').strip("'")
    for i, line in enumerate(source.splitlines(), 1):
        if needle and needle in line:
            return i
    return 1


def _manifest_dependencies(path: Path, source: str) -> list[tuple[str, int]]:
    if path.name == "pyproject.toml":
        try:
            data = tomllib.loads(source)
        except tomllib.TOMLDecodeError:
            return []
        specs = []
        project = data.get("project", {})
        specs.extend(project.get("dependencies", []))
        optional = project.get("optional-dependencies", {})
        for group in optional.values():
            specs.extend(group)
        poetry = data.get("tool", {}).get("poetry", {})
        for section in ("dependencies", "dev-dependencies"):
            deps = poetry.get(section, {})
            for name in deps:
                if name.lower() != "python":
                    specs.append(name)
        return [
            (name, _line_for_text(source, spec))
            for spec in specs
            for name in [_dependency_name(str(spec))]
            if name
        ]

    deps = []
    for line_no, line in enumerate(source.splitlines(), 1):
        name = _dependency_name(line)
        if name:
            deps.append((name, line_no))
    return deps


def scan_manifests(root: Path, changed: bool, base: str, cfg: Config) -> tuple[list[dict], list[dict]]:
    findings = []
    errors = []
    for path in discover_manifest_files(root, changed=changed, base=base):
        rel = path.relative_to(root)
        source, error = _read_utf8(path)
        if error:
            errors.append({"file": str(rel), "line": 0, "message": error})
            continue
        for dep, line in _manifest_dependencies(path, source):
            if is_known(dep):
                continue
            similar = closest_popular(dep)
            severity = "major" if similar else "minor"
            message = (
                f"dependency '{dep}' looks like a typo/hallucination of '{similar}'"
                if similar else f"dependency '{dep}': unknown package, verify it exists"
            )
            finding = Finding("TG-D12", severity, line, message)
            finding.penalty = cfg.penalty_for(finding.detector, finding.severity)
            item = finding.to_dict()
            item["file"] = str(rel)
            findings.append(item)
    return findings, errors


def run_project_tests(root: Path, command: str, timeout: int = 120) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            shlex.split(command),
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ran": True,
            "kind": "project",
            "command": command,
            "tests_total": 0,
            "tests_failed": 0,
            "timeout": True,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "output_tail": (exc.stdout or "")[-4000:],
        }
    except OSError as exc:
        return {
            "ran": True,
            "kind": "project",
            "command": command,
            "tests_total": 0,
            "tests_failed": 0,
            "timeout": False,
            "build_error": True,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "output_tail": str(exc),
        }

    failed = 0 if proc.returncode == 0 else 1
    return {
        "ran": True,
        "kind": "project",
        "command": command,
        "tests_total": 1,
        "tests_failed": failed,
        "timeout": False,
        "build_error": False,
        "returncode": proc.returncode,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "output_tail": (proc.stdout + proc.stderr)[-4000:],
    }


def _is_test_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return rel.name.startswith("test_") or "tests" in rel.parts


def run_project_mutation(
    root: Path,
    files: list[Path],
    command: str | None,
    limit: int = 20,
    timeout: int = 120,
    seed: int = 0,
) -> dict:
    if not command:
        return {"ran": False, "reason": "project_tests_not_configured"}
    if limit <= 0:
        return {"ran": False, "reason": "project_mutation_limit_is_zero"}

    candidates = []
    for path in files:
        if _is_test_file(path, root):
            continue
        source, error = _read_utf8(path)
        if error:
            continue
        try:
            mutants = mutation.generate(source, seed=seed)
        except SyntaxError:
            continue
        for desc, mutated_source in mutants:
            candidates.append((path, source, desc, mutated_source))
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break

    if not candidates:
        return {
            "ran": True,
            "kind": "project",
            "command": command,
            "mutants_total": 0,
            "mutants_killed": 0,
            "mutation_score": 1.0,
            "survivors": [],
        }

    killed = 0
    survivors = []
    started = time.monotonic()
    for path, original_source, desc, mutated_source in candidates:
        rel = str(path.relative_to(root))
        try:
            path.write_text(mutated_source + "\n", encoding="utf-8")
            result = run_project_tests(root, command, timeout=timeout)
            if result.get("tests_failed", 0) > 0 or result.get("build_error") or result.get("timeout"):
                killed += 1
            else:
                survivors.append({"file": rel, "mutation": desc})
        finally:
            path.write_text(original_source, encoding="utf-8")

    return {
        "ran": True,
        "kind": "project",
        "command": command,
        "mutants_total": len(candidates),
        "mutants_killed": killed,
        "mutation_score": killed / len(candidates),
        "survivors": survivors[:20],
        "duration_ms": int((time.monotonic() - started) * 1000),
    }


def scan_project(
    root: Path,
    changed: bool = False,
    base: str = "HEAD",
    cfg: Config | None = None,
    project_tests: str | None = None,
    project_test_timeout: int = 120,
    project_mutation: bool = False,
    project_mutation_limit: int = 20,
    policy_data: dict | None = None,
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

    manifest_findings, manifest_errors = scan_manifests(root, changed, base, cfg)
    static_findings.extend(manifest_findings)
    syntax_errors.extend(manifest_errors)

    dynamic = (
        run_project_tests(root, project_tests, timeout=project_test_timeout)
        if project_tests else {"ran": False, "reason": "project_tests_not_configured"}
    )
    mutation_result = (
        run_project_mutation(
            root,
            files,
            project_tests,
            limit=project_mutation_limit,
            timeout=project_test_timeout,
        )
        if project_mutation else {"ran": False, "reason": "project_mutation_not_enabled"}
    )

    finding_objects = [_finding_from_dict(item) for item in static_findings]
    raw, score, verdict = scoring.aggregate(
        finding_objects,
        dynamic,
        mutation_result,
        cfg,
    )
    if syntax_errors:
        raw = min(raw, 0)
        score = 0
        verdict = "BLOCK"

    out = {
        "version": report.REPORT_VERSION,
        "mode": "changed" if changed else "project",
        "target": str(root),
        "base": base if changed else None,
        "score": score,
        "raw_score": raw,
        "verdict": verdict,
        "partial": not (dynamic.get("ran") and mutation_result.get("ran")),
        "summary": {
            "files_scanned": len(files),
            "files_analyzed": len(file_reports),
            "manifest_findings": len(manifest_findings),
            "findings": len(static_findings),
            "syntax_errors": len(syntax_errors),
        },
        "files": file_reports,
        "dynamic": dynamic,
        "mutation": mutation_result,
        "findings": static_findings,
        "syntax_errors": syntax_errors,
        "timing_ms": {"scan": int((time.monotonic() - started) * 1000)},
    }
    if policy_data:
        from .policy import apply_policy
        out = apply_policy(out, policy_data)
    return out


def to_markdown(scan_report: dict) -> str:
    summary = scan_report["summary"]
    mode = "changed files" if scan_report["mode"] == "changed" else "project"
    completeness = "partial analysis" if scan_report.get("partial") else "full analysis"
    lines = [
        f"## TrustGate scan: **{scan_report['verdict']}** "
        f"(score {scan_report['score']}/100)",
        "",
        f"Target: `{scan_report['target']}`  ·  mode: `{mode}`  ·  *{completeness}*",
        "",
        f"Files scanned: {summary['files_scanned']}; "
        f"findings: {summary['findings']}; "
        f"syntax errors: {summary['syntax_errors']}",
        "",
    ]
    dynamic = scan_report.get("dynamic", {})
    if dynamic.get("ran"):
        lines.append(
            f"Project tests: command `{dynamic['command']}`, "
            f"return code {dynamic.get('returncode', 'timeout')}"
        )
        lines.append("")
    mutation_result = scan_report.get("mutation", {})
    if mutation_result.get("ran"):
        lines.append(
            "Project mutation: "
            f"{mutation_result.get('mutants_killed', 0)}/"
            f"{mutation_result.get('mutants_total', 0)} killed "
            f"(score {mutation_result.get('mutation_score', 0):.2f})"
        )
        lines.append("")
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
            "dynamic": scan_report.get("dynamic", {"ran": False, "reason": "project_tests_not_configured"}),
            "mutation": scan_report.get("mutation", {"ran": False, "reason": "project_mutation_not_enabled"}),
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
        f"manifest findings: {summary.get('manifest_findings', 0)}; "
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


def to_sarif(scan_report: dict) -> dict:
    rules = {}
    results = []
    for item in scan_report["findings"]:
        rules.setdefault(item["detector"], {
            "id": item["detector"],
            "name": item["detector"],
            "shortDescription": {"text": item["message"].split(",", 1)[0]},
            "defaultConfiguration": {
                "level": "error" if item["severity"] == "critical" else "warning"
            },
        })
        results.append({
            "ruleId": item["detector"],
            "level": "error" if item["severity"] == "critical" else "warning",
            "message": {"text": item["message"]},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": item["file"]},
                    "region": {"startLine": max(1, item["line"])},
                }
            }],
            "properties": {
                "severity": item["severity"],
                "penalty": item["penalty"],
            },
        })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "TrustGate",
                    "informationUri": "https://github.com/ednaiu/TrustGate",
                    "rules": list(rules.values()),
                }
            },
            "results": results,
        }],
    }


def dump_sarif(scan_report: dict, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_sarif(scan_report), f, indent=2, ensure_ascii=False)


def to_github_annotations(scan_report: dict) -> list[dict]:
    level_by_severity = {"critical": "failure", "major": "warning", "minor": "notice"}
    annotations = []
    for item in scan_report.get("findings", []):
        annotations.append({
            "path": item["file"],
            "start_line": max(1, int(item["line"])),
            "end_line": max(1, int(item["line"])),
            "annotation_level": level_by_severity.get(item["severity"], "warning"),
            "title": item["detector"],
            "message": f"{item['message']} (-{item['penalty']} trust points)",
        })
    return annotations


def dump_github_annotations(scan_report: dict, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_github_annotations(scan_report), f, indent=2, ensure_ascii=False)
