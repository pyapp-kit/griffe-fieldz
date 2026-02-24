"""Griffe Fieldz extension."""

from __future__ import annotations

import inspect
import textwrap
from contextlib import suppress
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypedDict,
    TypeVar,
    cast,
)

import fieldz
from griffe import (
    Attribute,
    Class,
    Docstring,
    DocstringAttribute,
    DocstringParameter,
    DocstringSection,
    DocstringSectionAttributes,
    DocstringSectionParameters,
    Extension,
    Object,
    ObjectNode,
    dynamic_import,
    get_logger,
    parse_docstring_annotation,
)

from ._repr import display_as_type

if TYPE_CHECKING:
    import ast
    from collections.abc import Iterable

    from griffe import Expr, Inspector, Visitor

    AddFieldsTo = Literal[
        "docstring-parameters", "docstring-attributes", "class-attributes"
    ]

logger = get_logger("griffe-fieldz")


class FieldzExtension(Extension):
    """Griffe extension that injects field information for dataclass-likes."""

    def __init__(
        self,
        object_paths: list[str] | None = None,
        include_private: bool = False,
        include_inherited: bool = False,
        add_fields_to: AddFieldsTo = "docstring-parameters",
        remove_fields_from_members: bool = False,
        strip_annotated: bool = False,
        **kwargs: Any,
    ) -> None:
        self.object_paths = object_paths
        self._kwargs = kwargs
        if kwargs:
            logger.warning(
                "Unknown kwargs passed to FieldzExtension: %s", ", ".join(kwargs)
            )
        self.include_private = include_private
        self.include_inherited = include_inherited
        self.strip_annotated = strip_annotated

        self.remove_fields_from_members = remove_fields_from_members
        if add_fields_to not in (
            "docstring-parameters",
            "docstring-attributes",
            "class-attributes",
        ):  # pragma: no cover
            logger.error(
                "'add_fields_to' must be one of {'docstring-parameters', "
                f"'docstring-attributes', or 'class-attributes'}}, not {add_fields_to}."
                "\n\nDefaulting to 'docstring-parameters'."
            )
            add_fields_to = "docstring-parameters"

        self.add_fields_to: AddFieldsTo = add_fields_to

    def on_class_members(
        self,
        *,
        node: ast.AST | ObjectNode,
        cls: Class,
        agent: Visitor | Inspector,
        **kwargs: Any,
    ) -> None:
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
        except TypeError:  # pragma: no cover
            return
        self._inject_fields(cls, runtime_obj)

    # ------------------------------

    def on_class(self, *, cls: Class, **kwargs: Any) -> None:
        """Fill in missing descriptions for inherited fields.

        This runs after the full object tree is built, so griffe's
        inheritance APIs (mro, attributes, inherited_members) work here.
        """
        if self.include_inherited and cls.docstring:
            _backfill_inherited_descriptions(cls)

    # ------------------------------

    def _inject_fields(self, griffe_obj: Object, runtime_obj: Any) -> None:
        # update the object instance with the evaluated docstring
        docstring = inspect.cleandoc(getattr(runtime_obj, "__doc__", "") or "")
        if not griffe_obj.docstring:
            griffe_obj.docstring = Docstring(docstring, parent=griffe_obj)

        # collect field info
        fields = fieldz.fields(runtime_obj)
        if not self.include_inherited:
            annotations = getattr(runtime_obj, "__annotations__", {})
            fields = tuple(f for f in fields if f.name in annotations)

        _unify_fields(
            fields,
            griffe_obj,
            include_private=self.include_private,
            add_fields_to=self.add_fields_to,
            remove_fields_from_members=self.remove_fields_from_members,
            strip_annotated=self.strip_annotated,
        )


def _backfill_inherited_descriptions(cls: Class) -> None:
    """Fill in missing field descriptions from parent classes.

    Uses griffe's MRO to find descriptions from parent docstring sections
    and inherited attribute docstrings. Must be called after the full object
    tree is built (e.g. from on_class), so that mro() works.
    """
    sections = cls.docstring.parsed  # pyright: ignore[reportOptionalMemberAccess]

    # Collect descriptions with empty strings that we need to fill
    empty_items: dict[str, DocstringParameter | DocstringAttribute] = {}
    params_or_attrs = (DocstringSectionParameters, DocstringSectionAttributes)
    for section in sections:
        if isinstance(section, params_or_attrs):
            for item in section.value:
                if not item.description:
                    empty_items[item.name] = item

    if not empty_items:
        return

    # Walk parent classes looking for descriptions
    try:
        parents = cls.mro()
    except ValueError:
        return

    for parent in parents:
        # Check parent's parsed docstring sections
        if parent.docstring:
            for section in parent.docstring.parsed:
                if isinstance(section, params_or_attrs):
                    for item in section.value:
                        if item.name in empty_items and item.description:
                            empty_items[item.name].description = item.description
                            del empty_items[item.name]
        # Check parent's direct member inline docstrings
        for name in list(empty_items):
            if name in parent.members:
                member = parent.members[name]
                if member.docstring:
                    empty_items[name].description = member.docstring.value
                    del empty_items[name]

        if not empty_items:
            return


def _to_annotation(
    type_: Any, docstring: Docstring, *, strip_annotated: bool = False
) -> str | Expr | None:
    """Create griffe annotation for a type."""
    if type_:
        # ensure string representation.
        if isinstance(type_, str):
            type_str = type_
            # Strip Annotated wrappers from string annotations if requested
            if strip_annotated and "Annotated[" in type_str:
                type_str = _strip_annotated_from_string(type_str)
        else:
            type_str = display_as_type(
                type_, modern_union=True, strip_annotated=strip_annotated
            )
        return parse_docstring_annotation(type_str, docstring)
    return None


def _strip_annotated_from_string(type_str: str) -> str:
    """Strip Annotated wrappers from string type annotations.

    Examples: "Annotated[int, Gt]" -> "int",
              "Annotated[list[Annotated[int, Interval]], Len]" -> "list[int]"
    """
    while (start := type_str.find("Annotated[")) != -1:
        bracket_count = 0
        for i in range(start + 10, len(type_str)):  # 10 = len("Annotated[")
            if type_str[i] == "[":
                bracket_count += 1
            elif type_str[i] == "]" and bracket_count == 0:
                # Extract first arg and replace Annotated[...] with it
                first_arg = _extract_first_arg(type_str[start + 10 : i])
                type_str = type_str[:start] + first_arg + type_str[i + 1 :]
                break
            elif type_str[i] == "]":
                bracket_count -= 1
        else:
            break  # No matching bracket found
    return type_str


def _extract_first_arg(content: str) -> str:
    """Extract first arg from comma-separated content, respecting brackets.

    Examples: "int, Gt" -> "int", "list[int], Len" -> "list[int]"
    """
    bracket_count = 0
    for i, char in enumerate(content):
        if char == "[":
            bracket_count += 1
        elif char == "]":
            bracket_count -= 1
        elif char == "," and bracket_count == 0:
            return content[:i].strip()
    return content.strip()


def _default_repr(field: fieldz.Field) -> str | None:
    """Return a repr for a field default."""
    try:
        if field.default is not field.MISSING:
            return repr(field.default)
        if (factory := field.default_factory) is not field.MISSING:
            try:
                sig = inspect.signature(factory)
            except ValueError:
                return repr(factory)
            else:
                if len(sig.parameters) == 0:
                    with suppress(Exception):
                        return repr(factory())  # type: ignore[call-arg]

            return "<dynamic>"
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to get default repr for %s: %s", field.name, exc)
        pass
    return None


class DocstringNamedElementKwargs(TypedDict):
    """Docstring named element kwargs."""

    name: str
    description: str
    annotation: str | Expr | None
    value: str | None


def _unify_fields(
    fields: Iterable[fieldz.Field],
    griffe_obj: Object,
    include_private: bool,
    add_fields_to: AddFieldsTo,
    remove_fields_from_members: bool,
    strip_annotated: bool,
) -> None:
    docstring = cast("Docstring", griffe_obj.docstring)
    sections = docstring.parsed

    for field in fields:
        if not include_private and field.name.startswith("_"):
            continue

        try:
            item_kwargs = _merged_kwargs(
                field, docstring, griffe_obj, strip_annotated=strip_annotated
            )

            if add_fields_to == "class-attributes":
                if field.name not in griffe_obj.attributes:
                    griffe_obj.members[field.name] = Attribute(
                        name=item_kwargs["name"],
                        value=item_kwargs["value"],
                        annotation=item_kwargs["annotation"],
                        docstring=item_kwargs["description"],
                    )
            elif add_fields_to == "docstring-attributes" or (not field.init):
                _add_if_missing(sections, DocstringAttribute(**item_kwargs))
                # remove from parameters if it exists
                if p_sect := _get_section(sections, DocstringSectionParameters):
                    p_sect.value = [x for x in p_sect.value if x.name != field.name]
                if remove_fields_from_members:
                    # remove from griffe_obj.parameters
                    griffe_obj.members.pop(field.name, None)
                    griffe_obj.inherited_members.pop(field.name, None)
            elif add_fields_to == "docstring-parameters":
                _add_if_missing(sections, DocstringParameter(**item_kwargs))
                # remove from attributes if it exists
                if a_sect := _get_section(sections, DocstringSectionAttributes):
                    a_sect.value = [x for x in a_sect.value if x.name != field.name]
                if remove_fields_from_members:
                    # remove from griffe_obj.attributes
                    griffe_obj.members.pop(field.name, None)
                    griffe_obj.inherited_members.pop(field.name, None)

        except Exception as exc:
            logger.warning("Failed to parse field %s: %s", field.name, exc)


def _merged_kwargs(
    field: fieldz.Field,
    docstring: Docstring,
    griffe_obj: Object,
    *,
    strip_annotated: bool = False,
) -> DocstringNamedElementKwargs:
    desc = field.description or field.metadata.get("description", "") or ""
    if (
        not desc
        and field.default_factory is not field.MISSING
        and (doc := getattr(field.default_factory, "__doc__", None))
    ):
        desc = inspect.cleandoc(doc) or ""

    if not desc and field.name in griffe_obj.attributes:
        griffe_attr = griffe_obj.attributes[field.name]
        if griffe_attr.docstring:
            desc = griffe_attr.docstring.value

    return DocstringNamedElementKwargs(
        name=field.name,
        description=textwrap.dedent(desc).strip(),
        annotation=_to_annotation(
            field.type, docstring, strip_annotated=strip_annotated
        ),
        value=_default_repr(field),
    )


T = TypeVar("T", bound="DocstringSectionParameters | DocstringSectionAttributes")


def _get_section(sections: list[DocstringSection], cls: type[T]) -> T | None:
    for section in sections:
        if isinstance(section, cls):
            return section
    return None


def _add_if_missing(
    sections: list[DocstringSection], item: DocstringParameter | DocstringAttribute
) -> None:
    section: DocstringSectionParameters | DocstringSectionAttributes | None
    if isinstance(item, DocstringParameter):
        if not (section := _get_section(sections, DocstringSectionParameters)):
            section = DocstringSectionParameters([])
            sections.append(section)
    elif isinstance(item, DocstringAttribute):
        if not (section := _get_section(sections, DocstringSectionAttributes)):
            section = DocstringSectionAttributes([])
            sections.append(section)
    else:  # pragma: no cover
        raise TypeError(f"Unknown section type: {type(item)}")

    existing = {x.name: x for x in section.value}
    if item.name in existing:
        current = existing[item.name]
        if current.description is None and item.description:
            current.description = item.description
        # Always update annotation if we have one
        # (to apply transformations like strip_annotated)
        if item.annotation:
            current.annotation = item.annotation
        if current.value is None and item.value is not None:
            current.value = item.value
    else:
        section.value.append(item)  # pyright: ignore
