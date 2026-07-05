import pytest  # trustgate: ignore TG-D01
from solution import retry_call  # trustgate: ignore TG-D01


def test_success_first_try():
    assert retry_call(lambda: 42) == 42


def test_retries_then_success():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("boom")
        return "ok"

    assert retry_call(flaky, attempts=3) == "ok"
    assert len(calls) == 3


def test_exhausted():
    def always_fails():
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        retry_call(always_fails, attempts=2)
