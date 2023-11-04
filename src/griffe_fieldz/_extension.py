"""Griffe Fieldz extension."""
from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Iterable, Sequence

import fieldz
from fieldz._repr import display_as_type
from griffe import Class, Extension, Object, ObjectNode, dynamic_import, get_logger
from griffe.dataclasses import Docstring
from griffe.docstrings.dataclasses import (
    DocstringAttribute,
    DocstringParameter,
    DocstringSection,
    DocstringSectionAttributes,
    DocstringSectionParameters,
)
from griffe.docstrings.utils import parse_annotation

if TYPE_CHECKING:
    import ast

    from griffe.expressions import Expr
    from pydantic import BaseModel

logger = get_logger(__name__)


class FieldzExtension(Extension):
    """Griffe extension that reads documentation from `typing.Doc`."""

    def __init__(
        self,
        object_paths: list[str] | None = None,
        include_private: bool = False,
        **kwargs: Any,
    ) -> None:
        self.object_paths = object_paths
        self._kwargs = kwargs
        self.include_private = include_private

    def on_class_instance(self, *, node: ast.AST | ObjectNode, cls: Class) -> None:
        if isinstance(node, ObjectNode):
            return  # skip runtime objects

        if self.object_paths and cls.path not in self.object_paths:
            return  # skip objects that were not selected

        # import object to get its evaluated docstring
        try:
            runtime_obj = dynamic_import(cls.path)
        except ImportError:
            logger.debug(f"Could not get dynamic docstring for {cls.path}")
            return

        try:
            fieldz.get_adapter(runtime_obj)
        except TypeError:
            return
        self._inject_fields(cls, runtime_obj)

    def _inject_fields(self, obj: Object, runtime_obj: type[BaseModel]) -> None:
        # update the object instance with the evaluated docstring
        docstring = inspect.cleandoc(getattr(runtime_obj, "__doc__", "") or "")
        if not obj.docstring:
            obj.docstring = Docstring(docstring, parent=obj)
        sections = obj.docstring.parsed

        # collect field info
        fields = fieldz.fields(runtime_obj)
        params, attrs = _fields_to_params(fields, obj.docstring, self.include_private)

        # merge/add field info to docstring
        if params:
            for x in sections:
                if isinstance(x, DocstringSectionParameters):
                    _merge(x, params)
                    break
            else:
                sections.insert(1, DocstringSectionParameters(params))
        if attrs:
            for x in sections:
                if isinstance(x, DocstringSectionAttributes):
                    _merge(x, params)
                    break
            else:
                sections.append(DocstringSectionAttributes(attrs))


def _to_annotation(type_: Any, docstring: Docstring) -> str | Expr | None:
    """Create griffe annotation for a type."""
    if type_:
        return parse_annotation(display_as_type(type_, modern_union=True), docstring)
    return None


def _default_repr(field: fieldz.Field) -> str | None:
    """Return a repr for a field default."""
    if field.default is not field.MISSING:
        return repr(field.default)
    if field.default_factory is not field.MISSING:
        return repr(field.default_factory())
    return None


def _fields_to_params(
    fields: Iterable[fieldz.Field], docstring: Docstring, include_private: bool = False
) -> tuple[list[DocstringParameter], list[DocstringAttribute]]:
    """Get all docstring attributes and parameters for fields."""
    params: list[DocstringParameter] = []
    attrs: list[DocstringAttribute] = []
    for field in fields:
        kwargs: dict = {
            "name": field.name,
            "annotation": _to_annotation(field.type, docstring),
            "description": field.description or field.metadata.get("description", ""),
            "value": _default_repr(field),
        }
        if field.init:
            params.append(DocstringParameter(**kwargs))
        elif include_private or not field.name.startswith("_"):
            attrs.append(DocstringAttribute(**kwargs))

    return params, attrs


def _merge(
    section: DocstringSection, field_params: Sequence[DocstringParameter]
) -> None:
    """Update DocstringSection with field params (if missing)."""
    existing_names = {x.name for x in section.value}
    for param in field_params:
        if param.name not in existing_names:
            section.value.append(param)
