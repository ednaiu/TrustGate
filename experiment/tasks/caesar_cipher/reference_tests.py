from solution import caesar  # trustgate: ignore TG-D01


def test_basic():
    assert caesar("abc", 1) == "bcd"


def test_wrap_and_case():
    assert caesar("XyZ", 3) == "AbC"


def test_non_letters():
    assert caesar("a-b!", 2) == "c-d!"
