import json

import pytest

from trustgate.cli import main

CLEAN = "def add(a, b):\n    return a + b\n"
BAD = (
    "import requsets\n"
    "import fastjsonx\n"
    "import zzduqp\n"
    "def get(url):\n"
    "    return eval(url)\n"
)


def run(tmp_path, source, *extra):
    f = tmp_path / "solution.py"
    f.write_text(source)
    out = tmp_path / "report.json"
    code = main(["check", str(f), "--no-sandbox", "--json", str(out), *extra])
    return code, json.loads(out.read_text())


def test_clean_file_passes_with_missing_mutation_penalty(tmp_path):
    # static layer alone: clean code minus the "no mutation verdict" penalty
    code, rep = run(tmp_path, CLEAN)
    assert rep["score"] == 90
    assert rep["verdict"] == "PASS"
    assert code == 0
    assert rep["partial"] is True


def test_bad_file_blocks(tmp_path):
    code, rep = run(tmp_path, BAD)
    assert rep["verdict"] == "BLOCK"
    assert code == 2


def test_no_sandbox_disables_mutation(tmp_path):
    _, rep = run(tmp_path, CLEAN)
    assert rep["layers"]["mutation"]["ran"] is False
    assert rep["layers"]["dynamic"]["ran"] is False


def test_syntax_error_is_input_error(tmp_path, capsys):
    f = tmp_path / "broken.py"
    f.write_text("def f(:\n")
    with pytest.raises(SystemExit) as e:
        main(["check", str(f), "--no-sandbox"])
    assert e.value.code == 3
    err = capsys.readouterr().err
    assert "line 1" in err
    assert "Traceback" not in err


def test_missing_file_is_input_error(tmp_path):
    with pytest.raises(SystemExit) as e:
        main(["check", str(tmp_path / "nope.py"), "--no-sandbox"])
    assert e.value.code == 3


def test_usage_error_is_input_error_not_block():
    # argparse's default exit code 2 would collide with the BLOCK verdict
    with pytest.raises(SystemExit) as e:
        main(["check", "--bogus"])
    assert e.value.code == 3


def test_dynamic_layer_reports_why_it_did_not_run(tmp_path):
    _, rep = run(tmp_path, CLEAN)
    assert rep["layers"]["dynamic"]["reason"] == "no_tests"


def test_report_matches_schema(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    from pathlib import Path
    schema = json.loads(
        (Path(__file__).parent.parent / "schemas" / "report-1.0.json").read_text())
    _, rep = run(tmp_path, BAD)
    jsonschema.validate(rep, schema)


def test_penalties_add_up(tmp_path):
    # property from FR-JSON-2: findings + layer penalties == 100 - raw_score
    _, rep = run(tmp_path, BAD)
    static_spent = sum(f["penalty"] for f in rep["layers"]["static"]["findings"])
    mutation_spent = 10  # uniform "missing" penalty, no saturation hit here
    assert 100 - rep["raw_score"] == static_spent + mutation_spent


def test_render_saved_report(tmp_path, capsys):
    _, _ = run(tmp_path, CLEAN)
    code = main(["report", str(tmp_path / "report.json")])
    assert code == 0
    assert "TrustGate" in capsys.readouterr().out


def test_check_writes_html_report(tmp_path):
    f = tmp_path / "solution.py"
    f.write_text(CLEAN)
    html = tmp_path / "report.html"
    code = main(["check", str(f), "--no-sandbox", "--html", str(html)])
    assert code == 0
    assert "TrustGate" in html.read_text()


def test_scan_project_from_cli(tmp_path, capsys):
    (tmp_path / "bad.py").write_text("import requsets\n")
    out = tmp_path / "scan.json"
    code = main(["scan", str(tmp_path), "--json", str(out)])
    assert code == 1
    assert "TrustGate scan" in capsys.readouterr().out
    rep = json.loads(out.read_text())
    assert rep["summary"]["files_scanned"] == 1
    assert rep["findings"][0]["file"] == "bad.py"


def test_determinism(tmp_path):
    _, first = run(tmp_path, BAD)
    _, second = run(tmp_path, BAD)
    first.pop("timing_ms")
    second.pop("timing_ms")
    assert first == second
