import json
import sys
from pathlib import Path

from trustgate import scan


def enable_fake_docker(monkeypatch, result=None):
    monkeypatch.setattr(scan.sandbox, "available", lambda: True)
    monkeypatch.setattr(scan.sandbox, "ensure_image", lambda: True)
    monkeypatch.setattr(scan.sandbox, "run_command", lambda *a, **k: dict(result or {
        "ran": True,
        "kind": "project",
        "command": "python -m pytest -q",
        "tests_total": 1,
        "tests_failed": 0,
        "timeout": False,
        "returncode": 0,
        "output_tail": "1 passed in 0.01s",
    }))


def test_scan_project_blocks_bad_file(tmp_path):
    (tmp_path / "good.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "bad.py").write_text(
        "import requsets\n\n"
        "def run(x):\n"
        "    return eval(x)\n\n"
        "def lookup(cur, user_id):\n"
        "    return cur.execute(f'SELECT * FROM users WHERE id={user_id}')\n"
    )

    rep = scan.scan_project(tmp_path)

    assert rep["summary"]["files_scanned"] == 2
    assert rep["verdict"] == "BLOCK"
    assert any(f["file"] == "bad.py" and f["detector"] == "TG-D03"
               for f in rep["findings"])


def test_scan_project_reports_syntax_errors(tmp_path):
    (tmp_path / "broken.py").write_text("def f(:\n")

    rep = scan.scan_project(tmp_path)

    assert rep["verdict"] == "BLOCK"
    assert rep["score"] == 0
    assert rep["summary"]["syntax_errors"] == 1
    assert rep["syntax_errors"][0]["file"] == "broken.py"


def test_scan_changed_non_git_is_empty(tmp_path):
    (tmp_path / "x.py").write_text("x = 1\n")

    rep = scan.scan_project(tmp_path, changed=True)

    assert rep["summary"]["files_scanned"] == 0
    assert rep["verdict"] == "REVIEW"


def test_scan_markdown_mentions_project_file(tmp_path):
    (tmp_path / "bad.py").write_text("import requsets\n")

    rep = scan.scan_project(tmp_path)
    rendered = scan.to_markdown(rep)

    assert "bad.py" in rendered
    assert "TG-D01" in rendered


def test_scan_project_checks_dependency_manifests(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\nversion = '0.1.0'\ndependencies = ['requsets>=2']\n"
    )

    rep = scan.scan_project(tmp_path)

    assert rep["summary"]["manifest_findings"] == 1
    assert rep["findings"][0]["detector"] == "TG-D12"
    assert rep["findings"][0]["file"] == "pyproject.toml"


def test_scan_sarif_contains_findings(tmp_path):
    (tmp_path / "bad.py").write_text("import requsets\n")

    rep = scan.scan_project(tmp_path)
    sarif = scan.to_sarif(rep)

    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"][0]["ruleId"] == "TG-D01"
    assert sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "bad.py"


def test_scan_project_can_run_trusted_project_tests(tmp_path, monkeypatch):
    (tmp_path / "test_smoke.py").write_text("def test_ok():\n    assert True\n")
    enable_fake_docker(monkeypatch)

    rep = scan.scan_project(tmp_path, project_tests=f"{sys.executable} -m pytest -q")

    assert rep["dynamic"]["ran"] is True
    assert rep["dynamic"]["returncode"] == 0
    assert rep["verdict"] == "REVIEW"


def test_scan_project_can_run_repository_mutation(tmp_path, monkeypatch):
    (tmp_path / "calc.py").write_text("def is_positive(x):\n    return x > 0\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import is_positive\n\n"
        "def test_is_positive():\n"
        "    assert is_positive(1)\n"
        "    assert not is_positive(0)\n"
    )

    enable_fake_docker(monkeypatch)

    rep = scan.scan_project(
        tmp_path,
        project_tests=f"{sys.executable} -m pytest -q",
        project_mutation=True,
        project_mutation_limit=5,
    )

    assert rep["mutation"]["ran"] is True
    assert rep["mutation"]["mutants_total"] > 0
    assert rep["mutation"]["mutation_score"] >= 0


def test_scan_github_annotations(tmp_path):
    (tmp_path / "bad.py").write_text("import requsets\n")

    rep = scan.scan_project(tmp_path)
    annotations = scan.to_github_annotations(rep)

    assert annotations[0]["path"] == "bad.py"
    assert annotations[0]["annotation_level"] == "failure"


def test_scan_report_matches_schema(tmp_path):
    import pytest

    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((Path(__file__).parent.parent / "schemas" / "scan-1.0.json").read_text())
    (tmp_path / "x.py").write_text("x = 1\n")

    rep = scan.scan_project(tmp_path)

    jsonschema.validate(rep, schema)
