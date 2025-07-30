from dataclasses import dataclass, field


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
