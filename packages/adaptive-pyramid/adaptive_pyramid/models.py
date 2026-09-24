from dataclasses import dataclass
from pathlib import Path


@dataclass
class CogInfo:

    path: Path

    bounds: tuple

    width: int

    height: int

    resolution: float

    max_overview: int