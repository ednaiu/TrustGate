from solution import is_palindrome  # trustgate: ignore TG-D01


def test_true():
    assert is_palindrome("A man, a plan, a canal: Panama")


def test_false():
    assert not is_palindrome("race a car")


def test_empty():
    assert is_palindrome("")
