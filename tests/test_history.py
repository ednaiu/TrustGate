from trustgate import history


def test_save_and_list_scan_history(tmp_path):
    report = {
        "target": str(tmp_path),
        "mode": "project",
        "verdict": "PASS",
        "score": 90,
        "raw_score": 90,
        "summary": {"findings": 1, "syntax_errors": 0},
        "findings": [{
            "file": "bad.py",
            "line": 1,
            "detector": "TG-D01",
            "severity": "critical",
            "message": "hallucinated import",
            "penalty": 25,
        }],
    }
    db = tmp_path / "history.sqlite"

    scan_id = history.save_scan(report, db)
    rows = history.list_scans(db)

    assert scan_id == 1
    assert rows[0]["verdict"] == "PASS"
    assert rows[0]["score"] == 90
    assert rows[0]["findings"] == 1
    assert history.detector_trends(db)[0]["detector"] == "TG-D01"


def test_render_dashboard(tmp_path):
    report = {
        "target": str(tmp_path),
        "mode": "project",
        "verdict": "REVIEW",
        "score": 70,
        "raw_score": 70,
        "summary": {"findings": 0, "syntax_errors": 0},
        "findings": [],
    }
    db = tmp_path / "history.sqlite"
    history.save_scan(report, db)

    html = history.render_dashboard(db)

    assert "История проверок" in html
    assert "REVIEW" in html
