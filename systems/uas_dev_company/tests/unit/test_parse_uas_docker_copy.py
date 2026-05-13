"""Парсер COPY Dockerfile."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from parse_uas_docker_copy import (  # noqa: E402
    collect_copy_sources_from_text,
    docker_path_specs_for_compose_service,
)


def test_collect_sources_multi_line_strip_prefix() -> None:
    src = """# comment
COPY systems/uas_dev_company/src/shared/foo.py \\
     systems/uas_dev_company/src/shared/tcb \\
     /app/x/
"""
    specs, raw = collect_copy_sources_from_text(src)
    assert "src/shared/foo.py" in specs
    assert "src/shared/tcb" in specs
    assert raw == ["src/shared/foo.py", "src/shared/tcb"]


def test_worker_fixture_domain_substitution() -> None:
    text = Path(ROOT / "docker/worker.Dockerfile").read_text(encoding="utf-8")
    specs_z, _ = collect_copy_sources_from_text(text, domain_pkg="zzz_other_test_pkg")
    assert any(s == "src/zzz_other_test_pkg" for s in specs_z)


def test_live_worker_matches_user_management_declaration() -> None:
    specs = docker_path_specs_for_compose_service("user_management_worker")
    assert isinstance(specs, list)
    assert "src/user_management" in specs or any("src/user_management" == s for s in specs)

