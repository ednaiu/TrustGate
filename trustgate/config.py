import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

DEFAULT_PENALTIES = {
    "TG-D01": 25,
    "TG-D02": 20,
    "TG-D03": 25,
    "TG-D04": 20,
    "TG-D05": 10,
    "TG-D06": 12,
    "TG-D07": 12,
    "TG-D08": 7,
    "TG-D09": 10,
    "TG-D10": 5,
    "TG-D11": 12,
    "TG-D12": 15,
    "TG-D13": 20,
    "TG-D14": 10,
    "TG-D15": 12,
}

# used when a detector downgrades severity (e.g. eval on a literal)
SEVERITY_PENALTIES = {"critical": 25, "major": 10, "minor": 5}

DEFAULT_SEVERITY = {
    "TG-D01": "critical",
    "TG-D02": "critical",
    "TG-D03": "critical",
    "TG-D04": "critical",
    "TG-D05": "major",
    "TG-D06": "major",
    "TG-D07": "major",
    "TG-D08": "major",
    "TG-D09": "major",
    "TG-D10": "minor",
    "TG-D11": "major",
    "TG-D12": "major",
    "TG-D13": "critical",
    "TG-D14": "major",
    "TG-D15": "major",
}

DEFAULTS = {
    "thresholds": {"pass": 76, "block": 39},
    "dynamic": {"first_fail": 15, "next_fail": 5, "fail_cap": 30, "timeout": 15, "build_error": 25},
    "mutation": {"missing": 10, "low": 20, "mid": 10, "low_bound": 0.4, "mid_bound": 0.7},
    "saturation": 40,
    "lang": "en",
}


class Config:
    def __init__(self, path: Path | None = None):
        data = {}
        if path is not None:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        self.penalties = {**DEFAULT_PENALTIES, **data.get("penalties", {})}
        self.thresholds = {**DEFAULTS["thresholds"], **data.get("thresholds", {})}
        self.dynamic = {**DEFAULTS["dynamic"], **data.get("dynamic", {})}
        self.mutation = {**DEFAULTS["mutation"], **data.get("mutation", {})}
        self.saturation = data.get("saturation", DEFAULTS["saturation"])
        self.lang = data.get("lang", DEFAULTS["lang"])

    def penalty_for(self, detector: str, severity: str) -> int:
        if severity == DEFAULT_SEVERITY.get(detector):
            return self.penalties[detector]
        return SEVERITY_PENALTIES[severity]
