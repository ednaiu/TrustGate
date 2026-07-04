from trustgate import scan


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
    assert rep["verdict"] == "PASS"


def test_scan_markdown_mentions_project_file(tmp_path):
    (tmp_path / "bad.py").write_text("import requsets\n")

    rep = scan.scan_project(tmp_path)
    rendered = scan.to_markdown(rep)

    assert "bad.py" in rendered
    assert "TG-D01" in rendered
