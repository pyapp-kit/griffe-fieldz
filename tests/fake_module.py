from dataclasses import dataclass, field


@dataclass
class SomeDataclass:
    """SomeDataclass."""

    x: int = field(default=1, metadata={"description": "The x field."})
