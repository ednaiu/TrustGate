from solution import safe_get  # trustgate: ignore TG-D01


def test_found():
    assert safe_get({"a": {"b": 1}}, ["a", "b"]) == 1


def test_missing():
    assert safe_get({"a": {}}, ["a", "b"]) is None
    assert safe_get({"a": 1}, ["a", "b"], default=0) == 0


def test_empty_path():
    assert safe_get({"a": 1}, []) == {"a": 1}
