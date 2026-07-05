from solution import count_lines  # trustgate: ignore TG-D01


def test_basic(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("a\n\n b \n   \n", encoding="utf-8")
    assert count_lines(str(f)) == 2


def test_empty_file(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")
    assert count_lines(str(f)) == 0
