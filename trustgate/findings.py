from dataclasses import dataclass, asdict


@dataclass
class Finding:
    detector: str
    severity: str  # critical | major | minor
    line: int
    message: str
    penalty: int = 0

    def to_dict(self):
        return asdict(self)
