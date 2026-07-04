from trustgate import history


def test_save_and_list_scan_history(tmp_path):
    report = {
        "target": str(tmp_path),
        "mode": "project",
        "verdict": "PASS",
        "score": 90,
        "summary": {"findings": 0, "syntax_errors": 0},
    }
    db = tmp_path / "history.sqlite"

    scan_id = history.save_scan(report, db)
    rows = history.list_scans(db)

    assert scan_id == 1
    assert rows[0]["verdict"] == "PASS"
    assert rows[0]["score"] == 90
