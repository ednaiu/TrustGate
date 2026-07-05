import pytest  # trustgate: ignore TG-D01
from solution import fib  # trustgate: ignore TG-D01


def test_base():
    assert fib(0) == 0
    assert fib(1) == 1


def test_large():
    assert fib(90) == 2880067194370816120


def test_negative():
    with pytest.raises(ValueError):
        fib(-1)
