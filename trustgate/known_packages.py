"""Package-name knowledge for TG-D01/TG-D12.

The source of truth is a committed snapshot of the top PyPI packages
(``data/pypi_top_packages.txt``), so the verdict is deterministic and does not
depend on what happens to be installed locally. The small curated list
(``data/popular_packages.txt``) keeps import-name aliases that differ from the
PyPI project name (``bs4``, ``cv2``, ``PIL``, ...) and doubles as the
typosquat reference set. Checking the local environment is opt-in
(``--trust-local-env``).
"""
import importlib.util
import sys
from functools import lru_cache
from pathlib import Path

_ALIASES = Path(__file__).parent / "data" / "popular_packages.txt"
_SNAPSHOT = Path(__file__).parent / "data" / "pypi_top_packages.txt"

# typosquats of short names are too noisy: "attr" vs "attrs", "click" vs "click"
MIN_TYPOSQUAT_LENGTH = 5


def _normalize(name: str) -> str:
    return name.lower().replace("-", "_")


def _read_names(path: Path) -> frozenset[str]:
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    return frozenset(names)


@lru_cache(maxsize=1)
def popular() -> frozenset[str]:
    """Curated high-profile import names, used as the typosquat reference."""
    return _read_names(_ALIASES)


@lru_cache(maxsize=1)
def snapshot() -> frozenset[str]:
    """Normalized top-PyPI package names from the committed snapshot."""
    return _read_names(_SNAPSHOT) | frozenset(_normalize(n) for n in popular())


def locally_available(module: str) -> bool:
    top = module.split(".")[0]
    if top in sys.stdlib_module_names:
        return True
    try:
        return importlib.util.find_spec(top) is not None
    except (ImportError, ValueError):
        return False


def is_known(
    module: str,
    extra_known: frozenset[str] = frozenset(),
    trust_local_env: bool = False,
) -> bool:
    top = module.split(".")[0]
    if top in sys.stdlib_module_names:
        return True
    if top in popular() or _normalize(top) in snapshot():
        return True
    if top in extra_known or _normalize(top) in extra_known:
        return True
    return trust_local_env and locally_available(top)


def levenshtein(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 3  # early exit, we only care about distance <= 2
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def closest_popular(module: str) -> str | None:
    """Curated name within edit distance 2, or None.

    Only names of MIN_TYPOSQUAT_LENGTH+ characters are matched: for shorter
    ones nearly every real package is within distance 2 of another, so a
    typosquat claim would mostly be a false positive.
    """
    top = module.split(".")[0].lower()
    if len(top) < MIN_TYPOSQUAT_LENGTH:
        return None
    bare = top.lstrip("_")  # `_pytest` is pytest's private package, not a typosquat
    candidates = [
        n for n in popular()
        if n.lower() not in (top, bare) and levenshtein(top, n.lower()) <= 2
    ]
    if not candidates:
        return None
    # deterministic pick: best distance, then alphabetical
    return min(candidates, key=lambda n: (levenshtein(top, n.lower()), n.lower()))
