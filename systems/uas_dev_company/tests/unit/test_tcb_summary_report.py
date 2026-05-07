"""Парсер Cobertura для сводного отчёта ДВБ (Задача 13)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from tcb_summary_report import parse_cobertura  # noqa: E402


def test_parse_cobertura_counts_hits(tmp_path: Path) -> None:
    xml = tmp_path / "c.xml"
    xml.write_text(
        """<?xml version="1.0" ?>
<coverage version="1" line-rate="0.5">
<packages><package><classes>
<class filename="src/shared/x.py">
<lines>
<line number="1" hits="1"/>
<line number="2" hits="0"/>
</lines>
</class>
</classes></package></packages>
</coverage>
""",
        encoding="utf-8",
    )
    by_file = parse_cobertura(xml.resolve())
    assert by_file.get("src/shared/x.py") == (1, 2)
