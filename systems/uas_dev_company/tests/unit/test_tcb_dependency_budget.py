"""ДВБ policy core (`shared.tcb`) must not depend on I/O, broker, or fat shared layers."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TCB_DIR = ROOT / "src" / "shared" / "tcb"

# Топ-уровневые модули и пакеты, запрещённые в контуре чистых политик (план Задачи 10).
_FORBIDDEN_TOP_LEVEL = frozenset(
    {
        "broker",
        "urllib",
        "http",
        "sqlite3",
        "xmlrpc",
        "requests",
        "httpx",
        "aiohttp",
        "flask",
        "fastapi",
        "starlette",
        "django",
        "docker",
        "kafka",
        "confluent_kafka",
        "pika",
        "redis",
        "celery",
        "grpc",
        "pytest",
        "unittest",
    }
)


def _module_names(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for alias in n.names:
                if alias.name:
                    out.add(alias.name)
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
    return out


def _top_level(mod: str) -> str:
    return mod.split(".", 1)[0]


def _shared_import_ok(module: str) -> bool:
    if not module.startswith("shared."):
        return True
    return module == "shared.topics" or module.startswith("shared.tcb")


@pytest.mark.parametrize(
    "path",
    sorted(TCB_DIR.glob("*.py")),
    ids=lambda p: p.name,
)
def test_tcb_file_dependency_budget(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    for mod in _module_names(tree):
        if _top_level(mod) in _FORBIDDEN_TOP_LEVEL:
            pytest.fail(f"{path.relative_to(ROOT)}: forbidden import {mod!r}")
        if not _shared_import_ok(mod):
            pytest.fail(f"{path.relative_to(ROOT)}: shared import not allowed in TCB core: {mod!r}")
