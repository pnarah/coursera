from dataclasses import dataclass, field

@dataclass(frozen=True)
class Goal:
    priority: int
    name: str
    description: str