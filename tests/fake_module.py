from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated


@dataclass
class SomeDataclass:
    """SomeDataclass."""

    x: int = field(default=1, metadata={"description": "The x field."})


@dataclass
class Inherited(SomeDataclass):
    y: int = 2


@dataclass
class WithPrivate:
    """Class with private field."""

    _hidden: int = 99


def factory_func() -> int:
    """Factory docstring."""
    return 7


@dataclass
class WithFactory:
    y: int = field(default_factory=factory_func)


class Gt:
    """Mock annotation."""


@dataclass
class ParentWithDocstringDesc:
    """Parent with field descriptions in docstring.

    Parameters:
        x: x described in parent docstring
    """

    x: int = 1
    y: int = field(default=2, metadata={"description": "y from metadata"})
    z: int = 3
    """z inline docstring"""


@dataclass
class ChildInheritsDocstringDesc(ParentWithDocstringDesc):
    """Child that inherits all fields."""

    pass


@dataclass
class WithAnnotated:
    """Class with Annotated fields."""

    id: Annotated[int, Gt] = 1
    count: Annotated[int, Gt] | None = None
