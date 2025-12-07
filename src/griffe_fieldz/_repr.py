"""Type representation utilities.

Vendored and modified from fieldz._repr to add support for strip_annotated parameter.
"""

from __future__ import annotations

import sys
import types
import typing
from typing import Any
from typing import GenericAlias as TypingGenericAlias  # type: ignore

import typing_extensions

try:
    from typing import _TypingBase  # type: ignore[attr-defined]
except ImportError:
    from typing import _Final as _TypingBase

typing_base = _TypingBase


if sys.version_info < (3, 12):
    # python < 3.12 does not have TypeAliasType
    TypeAliasType = ()
else:
    from typing import TypeAliasType

if sys.version_info < (3, 10):

    def origin_is_union(tp: type[Any] | None) -> bool:
        return tp is typing.Union

    WithArgsTypes = (TypingGenericAlias,)

else:

    def origin_is_union(tp: type[Any] | None) -> bool:
        return tp is typing.Union or tp is types.UnionType  # type: ignore

    WithArgsTypes = (typing._GenericAlias, types.GenericAlias, types.UnionType)  # type: ignore[attr-defined]


def origin_is_literal(tp: type[Any] | None) -> bool:
    return tp is typing_extensions.Literal  # type: ignore


def display_as_type(
    obj: Any, *, modern_union: bool = False, strip_annotated: bool = False
) -> str:
    """Pretty representation of a type.

    Should be as close as possible to the original type definition string.
    Takes some logic from `typing._type_repr`.

    Args:
        obj: The type to display.
        modern_union: If True, use `|` syntax instead of `Union[...]`.
        strip_annotated: If True, strip `Annotated` wrappers.
    """
    if isinstance(obj, types.FunctionType):
        # In python < 3.10, NewType was a function with __supertype__ set to the
        # wrapped type, so NewTypes pass through here
        return obj.__name__
    elif obj is ...:
        return "..."
    elif obj in (None, type(None)):
        return "None"

    if sys.version_info >= (3, 10):
        if not isinstance(
            obj,
            (
                typing_base,
                WithArgsTypes,
                type,
                TypeAliasType,
                typing.TypeVar,
                typing.NewType,
            ),
        ):
            obj = obj.__class__

        if isinstance(obj, typing.NewType):
            # NewType repr includes the module name prepended, so we use __name__
            # to get a clean name
            # NOTE: ignoring attr-defined because NewType has __name__ but mypy
            # can't see it for some reason; ignoring no-any-return because we
            # know __name__ must return a string
            return obj.__name__  # type: ignore[attr-defined, no-any-return]
    else:
        # We remove the NewType check because it doesn't work in isinstance prior to
        # python 3.10
        if not isinstance(
            obj,
            (
                typing_base,
                WithArgsTypes,
                type,
                TypeAliasType,
                typing.TypeVar,
            ),
        ):
            obj = obj.__class__

    if isinstance(obj, typing.TypeVar):
        # TypeVar repr includes a prepended ~, so we use __name__ to get a clean name
        return obj.__name__

    origin = typing_extensions.get_origin(obj)

    # Handle Annotated types - strip if requested
    if origin is typing_extensions.Annotated:
        annotated_args = typing_extensions.get_args(obj)
        if strip_annotated and annotated_args:
            # Return only the first arg (the actual type), recursively processed
            return display_as_type(
                annotated_args[0],
                modern_union=modern_union,
                strip_annotated=strip_annotated,
            )
        # Otherwise fall through to normal handling

    if origin_is_literal(origin):
        # For Literal types, represent the actual values, not their types
        arg_reprs = [repr(arg) for arg in typing_extensions.get_args(obj)]
        return f"Literal[{', '.join(arg_reprs)}]"
    elif origin_is_union(origin):
        args: list[str] = [
            display_as_type(
                x, modern_union=modern_union, strip_annotated=strip_annotated
            )
            for x in typing_extensions.get_args(obj)
        ]
        if modern_union:
            return " | ".join(args)
        if len(args) == 2 and "None" in args:
            args.remove("None")
            return f"Optional[{args[0]}]"
        return f"Union[{', '.join(args)}]"
    elif isinstance(obj, WithArgsTypes):
        argstr = ", ".join(
            display_as_type(
                arg, modern_union=modern_union, strip_annotated=strip_annotated
            )
            for arg in typing_extensions.get_args(obj)
        )
        # UnionType doesn't have __qualname__, check before accessing
        if not hasattr(obj, "__qualname__"):
            # This shouldn't happen as unions are handled above, but just in case
            return " | ".join(
                display_as_type(arg, modern_union=True, strip_annotated=strip_annotated)
                for arg in typing_extensions.get_args(obj)
            )
        return f"{obj.__qualname__}[{argstr}]"  # type: ignore[union-attr]
    elif isinstance(obj, type):
        return obj.__qualname__
    else:  # pragma: no cover
        return repr(obj).replace("typing.", "").replace("typing_extensions.", "")
