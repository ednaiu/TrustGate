from solution import fizzbuzz  # trustgate: ignore TG-D01


def test_basic():
    assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]


def test_fifteen():
    assert fizzbuzz(15)[-1] == "FizzBuzz"


def test_empty():
    assert fizzbuzz(0) == []
