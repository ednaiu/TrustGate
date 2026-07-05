from solution import flatten  # trustgate: ignore TG-D01


def test_nested():
    assert flatten([1, [2, [3, [4]]], 5]) == [1, 2, 3, 4, 5]


def test_flat():
    assert flatten([1, 2]) == [1, 2]


def test_empty():
    assert flatten([]) == []
    assert flatten([[], [[]]]) == []
