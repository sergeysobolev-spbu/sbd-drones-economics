"""Общие настройки pytest: целевой backend шлюза — bus (см. Задача 12)."""

from __future__ import annotations

import os

os.environ.setdefault("UAS_GATEWAY_BACKEND", "bus")
