#!/usr/bin/env python3
"""Создаёт каталоги виртуальной ФС под UAS_DOMAIN_DATA_ROOT (Задача 22). SQLite появляются при первом подключении воркера."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from shared import domain_storage as dom  # noqa: E402


def main() -> None:
    root = Path(os.environ.get("UAS_DOMAIN_DATA_ROOT", "resources/domains")).resolve()
    for domain_id in (
        dom.USER_MANAGEMENT,
        dom.FIRMWARE_INGESTION,
        dom.CERTIFICATION_SERVICE,
        dom.DRONE_REGISTRY,
        dom.PURCHASE_SERVICE,
        dom.AUDIT_LOG,
        dom.ANALYTICS_ADAPTER,
    ):
        (root / domain_id).mkdir(parents=True, exist_ok=True)
    print(f"init_domain_data: OK — каталоги доменов в {root}")


if __name__ == "__main__":
    main()
