"""Tests for the Griffe extension."""

from griffe.docstrings.dataclasses import (
    DocstringParameter,
    DocstringSectionParameters,
)
from griffe.expressions import ExprName
from griffe.extensions import Extensions
from griffe.loader import GriffeLoader

from griffe_fieldz import FieldzExtension


def test_extension() -> None:
    loader = GriffeLoader(extensions=Extensions(FieldzExtension()))
    fake_mod = loader.load_module("tests.fake_module")
    sections = fake_mod["SomeDataclass"].docstring.parsed
    assert len(sections) == 2
    sec1 = sections[1]
    assert isinstance(sec1, DocstringSectionParameters)
    p0 = sec1.value[0]
    assert isinstance(p0, DocstringParameter)
    assert p0.name == "x"
    assert isinstance(p0.annotation, ExprName)
    assert p0.annotation.name == "int"
    assert p0.description == "The x field."
    assert p0.value == "1"
