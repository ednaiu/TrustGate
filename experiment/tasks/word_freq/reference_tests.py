from solution import word_freq  # trustgate: ignore TG-D01


def test_basic():
    assert word_freq("a b a") == {"a": 2, "b": 1}


def test_case_and_punct():
    assert word_freq("Hi, hi!") == {"hi": 2}


def test_empty():
    assert word_freq("") == {}
