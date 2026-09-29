"""Lemoria — Sistema Operativo de Memoria y Orquestación para Desarrollo con IA."""

from importlib.metadata import PackageNotFoundError, version

# pyproject.toml is the single source of truth. A literal here drifted from it
# (0.1.0 against 0.2.0) precisely because nothing read this one.
try:
    __version__ = version("lemoria")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0+unknown"
