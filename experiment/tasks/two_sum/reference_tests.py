from solution import two_sum


def test_basic():
    assert sorted(two_sum([2, 7, 11, 15], 9)) == [0, 1]


def test_no_pair():
    assert two_sum([1, 2, 3], 100) is None


def test_negative_numbers():
    assert sorted(two_sum([-3, 4, 3, 90], 0)) == [0, 2]


def test_same_element_not_reused():
    assert two_sum([3, 2, 4], 6) != (0, 0)
    assert sorted(two_sum([3, 2, 4], 6)) == [1, 2]
