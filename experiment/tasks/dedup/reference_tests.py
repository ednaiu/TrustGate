from solution import dedup  # trustgate: ignore TG-D01


def test_basic():
    assert dedup([1, 2, 1, 3, 2]) == [1, 2, 3]


def test_no_dups():
    assert dedup([1, 2, 3]) == [1, 2, 3]


def test_empty():
    assert dedup([]) == []
