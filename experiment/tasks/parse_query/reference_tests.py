from solution import parse_query  # trustgate: ignore TG-D01


def test_basic():
    assert parse_query("a=1&b=2") == {"a": "1", "b": "2"}


def test_skip_broken():
    assert parse_query("a=1&broken&c=3") == {"a": "1", "c": "3"}


def test_empty():
    assert parse_query("") == {}
