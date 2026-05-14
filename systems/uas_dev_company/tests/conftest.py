"""Общие настройки pytest: целевой backend шлюза — bus."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("UAS_GATEWAY_BACKEND", "bus")

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))
