from solution import group_anagrams  # trustgate: ignore TG-D01


def test_basic():
    assert group_anagrams(["eat", "tea", "tan", "ate", "nat"]) == [
        ["eat", "tea", "ate"], ["tan", "nat"]]


def test_single():
    assert group_anagrams(["abc"]) == [["abc"]]


def test_empty():
    assert group_anagrams([]) == []
