"""Режим ApiContext с отдельным SQLite на домен (Задача 22)."""

from __future__ import annotations

import pytest

from gateway.sqlite_context import ApiContext
from shared import domain_storage as dom


def test_api_context_creates_per_domain_sqlite_under_root(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UAS_SQLITE_MONOLITH_PATH", raising=False)
    root = tmp_path / "vfs"
    ctx = ApiContext(data_root=root)
    assert ctx.users is not None
    assert ctx.purchase is not None
    for did in (
        dom.USER_MANAGEMENT,
        dom.DRONE_REGISTRY,
        dom.PURCHASE_SERVICE,
    ):
        db = root / did / "data.sqlite3"
        assert db.is_file(), f"expected {db}"
