"""Полнота pytest-cov в ``Makefile`` относительно union COPY образов ЦБ-1…ЦБ-3."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from tcb_makefile_cov import docker_cb123_python_file_union, union_expanded_cov_paths  # noqa: E402


def test_makefile_cov_expansion_covers_cb123_docker_python_files() -> None:
    dv = docker_cb123_python_file_union()
    mk = union_expanded_cov_paths()
    missing = sorted(dv - mk)
    assert not missing, f"Добавьте --cov= для недостающих путей: {missing}"
