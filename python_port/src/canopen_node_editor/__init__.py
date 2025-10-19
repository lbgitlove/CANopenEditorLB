"""Core package for the CANopenNode Editor Python port."""

from __future__ import annotations

__all__ = ["__version__", "EditorApplication", "EditorMainWindow"]

from .gui import EditorApplication, EditorMainWindow

__version__ = "0.1.0.dev0"
