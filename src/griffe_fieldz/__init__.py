"""Griffe extension adding support pydantic, attrs, dataclasses, etc...

Supports anything supported by fieldz.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("griffe-fieldz")
except PackageNotFoundError:
    __version__ = "uninstalled"


from ._extension import FieldzExtension

__all__ = ["FieldzExtension"]
