# griffe-fieldz

[![License](https://img.shields.io/pypi/l/griffe-fieldz.svg?color=green)](https://github.com/pyapp-kit/griffe-fieldz/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/griffe-fieldz.svg?color=green)](https://pypi.org/project/griffe-fieldz)
[![Python Version](https://img.shields.io/pypi/pyversions/griffe-fieldz.svg?color=green)](https://python.org)
[![CI](https://github.com/pyapp-kit/griffe-fieldz/actions/workflows/ci.yml/badge.svg)](https://github.com/pyapp-kit/griffe-fieldz/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pyapp-kit/griffe-fieldz/branch/main/graph/badge.svg)](https://codecov.io/gh/pyapp-kit/griffe-fieldz)

Griffe extension adding support for dataclass-like things (pydantic, attrs,
etc...). This extension will inject the fields of the data-class into the
documentation, preventing you from duplicating field metadata in your
docstrings.

It supports anything that [fieldz](https://github.com/pyapp-kit/fieldz)
supports, which is currently:

- [`dataclasses.dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass)
- [`pydantic.BaseModel`](https://docs.pydantic.dev/latest/)
- [`attrs.define`](https://www.attrs.org/en/stable/overview.html)
- [`msgspec.Struct`](https://jcristharif.com/msgspec/)

## Installation

With `pip`:

```bash
pip install griffe-fieldz
```

To use the extension in a MkDocs project, use this configuration:

```yaml
# mkdocs.yml
plugins:
- mkdocstrings:
    handlers:
      python:
        options:
          extensions:
          - griffe_fieldz
```

You may use any of the following options, provided as a dictionary under the
`griffe_fieldz` key.

| Option              | Description                                      | Default |
|---------------------|--------------------------------------------------|---------|
| `include_inherited` | Include inherited fields in class parameters.    | `False` |
| `include_private`   | Include private fields in the documentation.     | `False` |
| `add_fields_to` | Where in the documentation to add the detected fields. Must be one of:<br><br>- `docstring-parameters`: add fields to the *Parameters* section of the docstring<br>- `docstring-attributes`: add fields to the *Attributes* section of the docstring<br>- `class-attributes`: add fields as class attributes | `docstring-parameters` |
| `remove_fields_from_members` | If `True`, fields are *removed* as class members.  This is not encouraged (since fields are *indeed* class attributes), but will prevent duplication of the name in the docstring as well as the class.  This value is ignored if `add_fields_to` is `class-attributes`. | `False` |
| `strip_annotated` | If `True`, strip the `Annotated` wrapper from type hints, showing only the inner type. For example, `Annotated[int, Gt(0)]` will be displayed simply as `int`. | `False` |

For example:

```yml
        options:
          extensions:
          - griffe_fieldz:
              include_inherited: false
              include_private: false
              add_fields_to: docstring-attributes
              remove_fields_from_members: false
              strip_annotated: false
```

## Example

As an example playground for using this plugin to document pydantic, attrs, and other
dataclass-like objects, see: <https://github.com/tlambert03/fieldz-docs-example>
