from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Annotated, Literal, Optional, Union, cast

import griffe
import pytest
from griffe import Extensions, GriffeLoader

from griffe_fieldz import FieldzExtension
from griffe_fieldz._extension import (
    _add_if_missing,
    _extract_first_arg,
    _strip_annotated_from_string,
)
from griffe_fieldz._repr import display_as_type

if TYPE_CHECKING:
    from griffe_fieldz._extension import AddFieldsTo


def test_extension() -> None:
    loader = GriffeLoader(extensions=Extensions(FieldzExtension()))
    fake_mod = loader.load("tests.fake_module")
    sections = fake_mod["SomeDataclass"].docstring.parsed
    assert len(sections) == 2
    sec1 = sections[1]
    assert isinstance(sec1, griffe.DocstringSectionParameters)
    p0 = sec1.value[0]
    assert isinstance(p0, griffe.DocstringParameter)
    assert p0.name == "x"
    assert isinstance(p0.annotation, griffe.ExprName)
    assert p0.annotation.name == "int"
    assert p0.description == "The x field."
    assert p0.value == "1"


@pytest.mark.parametrize("remove", [True, False])
@pytest.mark.parametrize(
    "add_to", ["docstring-parameters", "docstring-attributes", "class-attributes"]
)
def test_include_inherited(remove: bool, add_to: AddFieldsTo) -> None:
    loader = GriffeLoader(
        extensions=Extensions(
            FieldzExtension(remove_fields_from_members=remove, add_fields_to=add_to)
        )
    )
    fake_mod = loader.load("tests.fake_module")
    inherited_cls = cast("griffe.Class", fake_mod["Inherited"])
    expected = remove and add_to != "class-attributes"
    assert ("x" not in inherited_cls.inherited_members) == expected
    assert ("y" not in inherited_cls.members) == expected

    assert inherited_cls.docstring

    expected_section_kind = {
        "docstring-parameters": griffe.DocstringSectionKind.parameters,
        "docstring-attributes": griffe.DocstringSectionKind.attributes,
        "class-attributes": griffe.DocstringSectionKind.classes,
    }[add_to]

    for section in inherited_cls.docstring.parsed:
        if isinstance(section.value, list):
            for item in section.value:
                if item.name == "y":
                    assert section.kind == expected_section_kind


def test_add_if_missing_merges() -> None:
    param = griffe.DocstringParameter(
        name="a", description="", annotation=None, value=None
    )
    param2 = griffe.DocstringParameter(
        name="a", description="desc", annotation="ann", value="val"
    )
    section = griffe.DocstringSectionParameters([param])
    _add_if_missing([section], param2)
    assert section.value[0].description == ""
    assert section.value[0].annotation == "ann"
    assert section.value[0].value == "val"


def test_strip_annotated() -> None:
    """Test that strip_annotated option works correctly."""
    # Test with strip_annotated=False (default)
    loader = GriffeLoader(extensions=Extensions(FieldzExtension()))
    fake_mod = loader.load("tests.fake_module")
    with_annotated = fake_mod["WithAnnotated"]
    sections = with_annotated.docstring.parsed
    params_section = None
    for section in sections:
        if isinstance(section, griffe.DocstringSectionParameters):
            params_section = section
            break

    assert params_section is not None
    param_dict = {p.name: p for p in params_section.value}

    # With strip_annotated=False, should see "Annotated"
    id_param = param_dict["id"]
    assert "Annotated" in str(id_param.annotation)

    # Test with strip_annotated=True
    loader2 = GriffeLoader(extensions=Extensions(FieldzExtension(strip_annotated=True)))
    fake_mod2 = loader2.load("tests.fake_module")
    with_annotated2 = fake_mod2["WithAnnotated"]
    sections2 = with_annotated2.docstring.parsed
    params_section2 = None
    for section in sections2:
        if isinstance(section, griffe.DocstringSectionParameters):
            params_section2 = section
            break

    assert params_section2 is not None
    param_dict2 = {p.name: p for p in params_section2.value}

    # With strip_annotated=True, should NOT see "Annotated"
    id_param2 = param_dict2["id"]
    assert "Annotated" not in str(id_param2.annotation)
    assert "int" in str(id_param2.annotation)


def test_strip_annotated_union_forms() -> None:
    """Test that different Annotated+Union forms produce the same output."""

    # Mock constraint class
    class SomeConstraint:
        pass

    # Two different ways to express the same thing
    if sys.version_info >= (3, 10):
        # Python 3.10+ supports | syntax
        type1 = Annotated[int, SomeConstraint()] | None
        type2 = Annotated[int | None, SomeConstraint()]
    else:
        # Python 3.9 needs Union syntax
        type1 = Union[Annotated[int, SomeConstraint()], None]
        type2 = Annotated[Union[int, None], SomeConstraint()]

    # Without stripping, they should be different
    result1_no_strip = display_as_type(type1, modern_union=True, strip_annotated=False)
    result2_no_strip = display_as_type(type2, modern_union=True, strip_annotated=False)
    assert result1_no_strip != result2_no_strip

    # With stripping, they should be the same
    result1_strip = display_as_type(type1, modern_union=True, strip_annotated=True)
    result2_strip = display_as_type(type2, modern_union=True, strip_annotated=True)
    assert result1_strip == result2_strip
    assert result1_strip == "int | None"

    # Test edge cases for string stripping
    assert _strip_annotated_from_string("Annotated[") == "Annotated["  # Malformed
    assert _extract_first_arg("dict[str, int], Other") == "dict[str, int]"  # Nested
    assert _extract_first_arg("single_arg") == "single_arg"  # No comma

    # Test Literal and Optional types
    lit = Literal["a", "b"]
    assert "Literal" in display_as_type(lit)
    opt = Optional[int]
    assert "Optional" in display_as_type(opt, modern_union=False)
    assert "int | None" in display_as_type(opt, modern_union=True)


def test_strip_annotated_runtime_types() -> None:
    """Test strip_annotated with runtime type objects (not string annotations)."""
    loader = GriffeLoader(extensions=Extensions(FieldzExtension(strip_annotated=True)))
    runtime_mod = loader.load("tests.fake_module_runtime")
    runtime_cls = runtime_mod["RuntimeAnnotated"]
    sections = runtime_cls.docstring.parsed
    params_section = None
    for section in sections:
        if isinstance(section, griffe.DocstringSectionParameters):
            params_section = section
            break
    assert params_section is not None
    value_param = params_section.value[0]
    assert value_param.name == "value"
    assert "Annotated" not in str(value_param.annotation)
    assert "int" in str(value_param.annotation)
