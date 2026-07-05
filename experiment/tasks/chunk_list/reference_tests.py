import pytest  # trustgate: ignore TG-D01
from solution import chunk  # trustgate: ignore TG-D01


def test_basic():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_exact():
    assert chunk([1, 2], 2) == [[1, 2]]


def test_bad_size():
    with pytest.raises(ValueError):
        chunk([1], 0)
