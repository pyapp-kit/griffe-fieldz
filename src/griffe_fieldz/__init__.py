"""Griffe extension adding support for data-class like things (pydantic, attrs, etc...)"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("griffe-fieldz")
except PackageNotFoundError:
    __version__ = "uninstalled"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@example.com"
