"""Развёртка ``Makefile`` целей ``pytest --cov=`` до путей ``*.py`` (Задача 24)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def makefile_cov_targets(makefile_path: Path | None = None) -> list[str]:
    path = makefile_path or (ROOT / "Makefile")
    return re.findall(r"--cov=([a-zA-Z0-9_.]+)", path.read_text(encoding="utf-8"))


def expand_cov_target(dot_path: str) -> set[str]:
    """Сопоставление ``pytest-cov``: ``pkg`` или ``pkg.submodule`` → пути под ``ROOT``."""
    r = ROOT.resolve()
    segments = dot_path.split(".")
    cand_py = r / "src" / Path(*segments).with_suffix(".py")
    if cand_py.is_file():
        return {cand_py.relative_to(r).as_posix()}
    cand_dir = r / "src" / Path(*segments)
    if cand_dir.is_dir():
        return {p.relative_to(r).as_posix() for p in sorted(cand_dir.rglob("*.py"))}
    for depth in range(len(segments) - 1, 0, -1):
        pref = segments[:depth]
        p2_py = r / "src" / Path(*pref).with_suffix(".py")
        if p2_py.is_file():
            return {p2_py.relative_to(r).as_posix()}
        p2_dir = r / "src" / Path(*pref)
        if p2_dir.is_dir():
            return {p.relative_to(r).as_posix() for p in sorted(p2_dir.rglob("*.py"))}
    return set()


def union_expanded_cov_paths(dot_targets: list[str] | None = None) -> set[str]:
    if dot_targets is None:
        dot_targets = makefile_cov_targets()
    cov: set[str] = set()
    for d in dot_targets:
        cov |= expand_cov_target(d)
    return cov


def docker_cb123_python_file_union() -> set[str]:
    from tcb_container_domains import CONTAINER_TCB_PYTHON_DOMAINS  # noqa: WPS433
    from parse_uas_docker_copy import docker_path_specs_for_compose_service  # noqa: WPS433
    from tcb_metrics import _iter_py_files  # noqa: WPS433

    r = ROOT.resolve()
    out: set[str] = set()
    for domain in CONTAINER_TCB_PYTHON_DOMAINS:
        if not domain.get("in_cb123_tcb_union", True):
            continue
        specs = docker_path_specs_for_compose_service(str(domain["compose_service"]))
        for pth in _iter_py_files(specs):
            out.add(pth.resolve().relative_to(r).as_posix())
    return out
