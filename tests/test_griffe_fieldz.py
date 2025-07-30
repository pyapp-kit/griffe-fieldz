from __future__ import annotations

from typing import TYPE_CHECKING, cast

import griffe
import pytest
from griffe import Extensions, GriffeLoader

from griffe_fieldz import FieldzExtension
from griffe_fieldz._extension import _add_if_missing

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
