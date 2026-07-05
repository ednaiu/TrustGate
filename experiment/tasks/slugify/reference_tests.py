from solution import slugify  # trustgate: ignore TG-D01


def test_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_multi_separators():
    assert slugify("  a  --  b  ") == "a-b"


def test_digits():
    assert slugify("Top 10 tips") == "top-10-tips"
