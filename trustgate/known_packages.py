import importlib.util
import sys
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).parent / "data" / "popular_packages.txt"


@lru_cache(maxsize=1)
def popular() -> frozenset[str]:
    names = set()
    for line in _DATA.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line)
    return frozenset(names)


def locally_available(module: str) -> bool:
    top = module.split(".")[0]
    if top in sys.stdlib_module_names:
        return True
    try:
        return importlib.util.find_spec(top) is not None
    except (ImportError, ValueError):
        return False


def is_known(module: str) -> bool:
    top = module.split(".")[0]
    return top in popular() or locally_available(top)


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
    top = module.split(".")[0].lower()
    candidates = [n for n in popular() if levenshtein(top, n.lower()) <= 2]
    if not candidates:
        return None
    # deterministic pick: best distance, then alphabetical
    return min(candidates, key=lambda n: (levenshtein(top, n.lower()), n.lower()))
