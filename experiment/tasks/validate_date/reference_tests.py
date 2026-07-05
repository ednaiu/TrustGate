from solution import validate_date  # trustgate: ignore TG-D01


def test_valid():
    assert validate_date("2024-02-29")
    assert validate_date("2000-12-31")


def test_invalid():
    assert not validate_date("2023-02-29")
    assert not validate_date("2024-13-01")
    assert not validate_date("not-a-date")
