"""Согласованность ``tcb_container_domains`` и Dockerfile."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "src"))

from parse_uas_docker_copy import docker_path_specs_for_compose_service  # noqa: E402
from tcb_container_domains import CONTAINER_TCB_PYTHON_DOMAINS  # noqa: E402
from tcb_metrics import _file_set_for_specs  # noqa: E402


def test_manual_python_specs_match_derived_copy_for_all_compose_domains() -> None:
    failures: list[str] = []
    for domain in CONTAINER_TCB_PYTHON_DOMAINS:
        svc = str(domain["compose_service"])
        specs = [str(x) for x in domain["python_path_specs"]]
        derived = docker_path_specs_for_compose_service(svc)
        if _file_set_for_specs(specs) != _file_set_for_specs(derived):
            failures.append(svc)
    assert not failures, f"divergence compose services={failures}"

