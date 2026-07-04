"""Full CLI flow with the sandbox mocked out -- exercises L2/L3 wiring."""
import json

from trustgate import cli, sandbox

CODE = "def double(x):\n    return x * 2\n"
TESTS = "from solution import double\n\ndef test_double():\n    assert double(2) == 4\n"


def run_with_fake_sandbox(tmp_path, monkeypatch, dynamic_result):
    monkeypatch.setattr(sandbox, "available", lambda: True)
    monkeypatch.setattr(sandbox, "ensure_image", lambda: True)
    monkeypatch.setattr(sandbox, "run_tests", lambda code, tests: dict(dynamic_result))

    code_f = tmp_path / "solution.py"
    code_f.write_text(CODE)
    tests_f = tmp_path / "test_solution.py"
    tests_f.write_text(TESTS)
    out = tmp_path / "report.json"
    exit_code = cli.main(["check", str(code_f), "--tests", str(tests_f), "--json", str(out)])
    return exit_code, json.loads(out.read_text())


def test_green_baseline_runs_mutation(tmp_path, monkeypatch):
    exit_code, rep = run_with_fake_sandbox(
        tmp_path, monkeypatch,
        {"ran": True, "tests_total": 1, "tests_failed": 0, "timeout": False})
    assert rep["layers"]["dynamic"]["ran"] is True
    assert rep["layers"]["mutation"]["ran"] is True
    assert rep["partial"] is False
    # every mutant "killed" by the fake runner? no: fake runner reports 0 failed,
    # so every mutant survives -> heavy penalty, still not a crash
    assert rep["layers"]["mutation"]["mutation_score"] == 0.0
    assert exit_code in (0, 1)


def test_red_baseline_skips_mutation(tmp_path, monkeypatch):
    _, rep = run_with_fake_sandbox(
        tmp_path, monkeypatch,
        {"ran": True, "tests_total": 2, "tests_failed": 1, "timeout": False})
    assert rep["layers"]["mutation"]["ran"] is False
    assert rep["layers"]["mutation"]["reason"] == "red_baseline"


def test_build_error_skips_mutation_and_costs_25(tmp_path, monkeypatch):
    _, rep = run_with_fake_sandbox(
        tmp_path, monkeypatch,
        {"ran": True, "tests_total": 0, "tests_failed": 0, "timeout": False,
         "build_error": True})
    assert rep["layers"]["mutation"]["reason"] == "red_baseline"
    # 100 - 25 (build error) - 10 (no mutation verdict) = 65
    assert rep["score"] == 65


def test_docker_missing_degrades_and_disables_mutation(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sandbox, "available", lambda: False)
    code_f = tmp_path / "solution.py"
    code_f.write_text(CODE)
    out = tmp_path / "report.json"
    exit_code = cli.main(["check", str(code_f), "--json", str(out)])
    rep = json.loads(out.read_text())
    assert exit_code != 3  # degradation, not an input error (TZ 3.4 / NS-7)
    assert rep["partial"] is True
    assert rep["layers"]["dynamic"]["ran"] is False
    assert rep["layers"]["mutation"]["ran"] is False
    assert "falling back" in capsys.readouterr().err
