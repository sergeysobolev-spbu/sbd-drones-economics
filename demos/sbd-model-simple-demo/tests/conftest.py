"""Общая конфигурация pytest: путь к коду демо."""

from __future__ import annotations

import sys
from pathlib import Path

_CODE = Path(__file__).resolve().parent.parent / "sbd-model-demo-code"
sys.path.insert(0, str(_CODE))
print(_CODE)