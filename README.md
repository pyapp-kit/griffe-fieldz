# griffe-fieldz

[![License](https://img.shields.io/pypi/l/griffe-fieldz.svg?color=green)](https://github.com/pyapp-kit/griffe-fieldz/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/griffe-fieldz.svg?color=green)](https://pypi.org/project/griffe-fieldz)
[![Python Version](https://img.shields.io/pypi/pyversions/griffe-fieldz.svg?color=green)](https://python.org)
[![CI](https://github.com/pyapp-kit/griffe-fieldz/actions/workflows/ci.yml/badge.svg)](https://github.com/pyapp-kit/griffe-fieldz/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pyapp-kit/griffe-fieldz/branch/main/graph/badge.svg)](https://codecov.io/gh/pyapp-kit/griffe-fieldz)

Griffe extension adding support for data-class like things (pydantic, attrs,
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

For example:

```yml
        options:
          extensions:
          - griffe_fieldz: {include_inherited: true}
```
