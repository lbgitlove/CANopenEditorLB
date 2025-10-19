"""Test suite for the CANopenNode Editor Python port."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if _SRC_DIR.exists():
    _PATH = str(_SRC_DIR)
    if _PATH not in sys.path:
        sys.path.insert(0, _PATH)
