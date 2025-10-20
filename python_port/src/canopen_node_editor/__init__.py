"""Core package for the CANopenNode Editor Python port."""

from __future__ import annotations

__all__ = ["__version__", "EditorApplication", "EditorMainWindow"]

try:
    from .gui import EditorApplication, EditorMainWindow
except ModuleNotFoundError as exc:
    if exc.name != "PySide6":
        raise
    EditorApplication = None
    EditorMainWindow = None

__version__ = "0.1.0.dev0"
