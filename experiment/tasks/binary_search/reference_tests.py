from solution import binary_search  # trustgate: ignore TG-D01


def test_found():
    assert binary_search([1, 3, 5, 7, 9], 7) == 3


def test_not_found():
    assert binary_search([1, 3, 5], 4) == -1


def test_edges():
    assert binary_search([2], 2) == 0
    assert binary_search([], 1) == -1
