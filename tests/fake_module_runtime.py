"""Test module without from __future__ import annotations for runtime types."""

from dataclasses import dataclass
from typing import Annotated


class Gt:
    """Mock annotation."""


@dataclass
class RuntimeAnnotated:
    """Class with runtime type annotations (no future import)."""

    value: Annotated[int, Gt] = 42
