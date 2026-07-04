"""Dynamic (L2) layer: run the submitted code's tests inside Docker.

Container gets no network, 1 CPU, 512M RAM, 64 pids and a read-only mount
(FR-SBX-1). If Docker is missing we degrade instead of failing (TZ 3.4).
"""
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

IMAGE = "trustgate-runner"
WALL_TIME = 30
DOCKERFILE = Path(__file__).parent.parent / "docker" / "Dockerfile"

# pytest exit codes: 0 ok, 1 tests failed, 2 interrupted, 3 internal, 4 usage, 5 nothing collected
PYTEST_OK = (0, 1)


def available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def ensure_image() -> bool:
    r = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True)
    if r.returncode == 0:
        return True
    build = subprocess.run(
        ["docker", "build", "-t", IMAGE, "-f", str(DOCKERFILE), str(DOCKERFILE.parent)],
        capture_output=True,
    )
    return build.returncode == 0


def _docker_cmd(name: str, workdir: str, inner: list[str]) -> list[str]:
    return [
        "docker", "run", "--rm",
        "--name", name,
        "--network", "none",
        "--cpus", "1",
        "--memory", "512m",
        "--pids-limit", "64",
        "-v", f"{workdir}:/work:ro",
        "-w", "/work",
        IMAGE,
        *inner,
    ]


def run_tests(code: str, tests: str) -> dict:
    """Returns the 'dynamic' layer dict for the report."""
    name = f"trustgate-{uuid.uuid4().hex[:12]}"
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "solution.py").write_text(code, encoding="utf-8")
        Path(tmp, "test_solution.py").write_text(tests, encoding="utf-8")
        cmd = _docker_cmd(name, tmp,
                          ["python", "-m", "pytest", "test_solution.py", "-q", "--tb=no"])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=WALL_TIME + 15)
        except subprocess.TimeoutExpired:
            # the client gave up but the container is still spinning
            subprocess.run(["docker", "kill", name], capture_output=True)
            return {"ran": True, "tests_total": 0, "tests_failed": 0, "timeout": True}

    if proc.returncode not in PYTEST_OK:
        return {"ran": True, "tests_total": 0, "tests_failed": 0,
                "timeout": False, "build_error": True}

    out = proc.stdout + proc.stderr
    failed = passed = 0
    m = re.search(r"(\d+) failed", out)
    if m:
        failed = int(m.group(1))
    m = re.search(r"(\d+) passed", out)
    if m:
        passed = int(m.group(1))
    return {"ran": True, "tests_total": failed + passed,
            "tests_failed": failed, "timeout": False}
