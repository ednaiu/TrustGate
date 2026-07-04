from solution import decode, encode


def test_encode():
    assert encode("aaabcc") == "a3b1c2"


def test_empty():
    assert encode("") == ""
    assert decode("") == ""


def test_roundtrip():
    for s in ("a", "abc", "aabbcc", "x" * 15):
        assert decode(encode(s)) == s


def test_multidigit_count():
    assert encode("a" * 12) == "a12"
