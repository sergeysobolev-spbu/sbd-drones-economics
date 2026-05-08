"""Общие настройки pytest: целевой backend шлюза — bus."""

from __future__ import annotations

import os

os.environ.setdefault("UAS_GATEWAY_BACKEND", "bus")
