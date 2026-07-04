"""Sandbox layer tests with a mocked docker binary -- no Docker required."""
import subprocess
from types import SimpleNamespace

import pytest

from trustgate import sandbox


def fake_proc(returncode, stdout=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def test_unavailable_without_docker_binary(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda _: None)
    assert sandbox.available() is False


def test_available_when_docker_info_ok(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(sandbox.subprocess, "run", lambda *a, **k: fake_proc(0))
    assert sandbox.available() is True


def test_unavailable_when_daemon_down(monkeypatch):
    monkeypatch.setattr(sandbox.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setattr(sandbox.subprocess, "run", lambda *a, **k: fake_proc(1))
    assert sandbox.available() is False


def test_run_tests_parses_pytest_summary(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run",
                        lambda *a, **k: fake_proc(1, "2 failed, 3 passed in 0.1s"))
    result = sandbox.run_tests("x = 1", "def test_a(): pass")
    assert result == {"ran": True, "tests_total": 5, "tests_failed": 2, "timeout": False}


def test_run_tests_all_green(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run",
                        lambda *a, **k: fake_proc(0, "4 passed in 0.2s"))
    result = sandbox.run_tests("x = 1", "def test_a(): pass")
    assert result["tests_failed"] == 0
    assert result["tests_total"] == 4


def test_failed_test_is_not_build_error(monkeypatch):
    # pytest prints "FAILED ... - ZeroDivisionError" even with -q;
    # classification must rely on the exit code, not on grepping "error"
    out = "FAILED test_solution.py::test_x - ZeroDivisionError\n1 failed in 0.1s"
    monkeypatch.setattr(sandbox.subprocess, "run", lambda *a, **k: fake_proc(1, out))
    result = sandbox.run_tests("x = 1", "def test_a(): pass")
    assert "build_error" not in result
    assert result["tests_failed"] == 1


def test_collection_error_is_build_error(monkeypatch):
    monkeypatch.setattr(sandbox.subprocess, "run",
                        lambda *a, **k: fake_proc(2, "ImportError while importing"))
    result = sandbox.run_tests("import nope", "def test_a(): pass")
    assert result["build_error"] is True


def test_timeout_kills_container(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["docker", "run"]:
            raise subprocess.TimeoutExpired(cmd, 1)
        return fake_proc(0)

    monkeypatch.setattr(sandbox.subprocess, "run", fake_run)
    result = sandbox.run_tests("while True: pass", "def test_a(): pass")
    assert result["timeout"] is True
    assert any(cmd[:2] == ["docker", "kill"] for cmd in calls)


def test_docker_cmd_isolation_flags():
    cmd = sandbox._docker_cmd("name1", "/tmp/x", ["true"])
    joined = " ".join(cmd)
    for flag in ("--network none", "--pids-limit 64", "--memory 512m",
                 "--cpus 1", "/tmp/x:/work:ro"):
        assert flag in joined
