"""Идентификаторы целей безопасности системы: только ЦБ-1…ЦБ-3 из docs/README.md (Задача 15)."""

from __future__ import annotations

from typing import Iterable

# Единственные допустимые «теги» целей на прошивке, сертификате и экземпляре.
CANONICAL_SECURITY_GOAL_IDS: frozenset[str] = frozenset({"ЦБ-1", "ЦБ-2", "ЦБ-3"})
CANONICAL_SECURITY_GOAL_IDS_ORDERED: tuple[str, ...] = ("ЦБ-1", "ЦБ-2", "ЦБ-3")
_GOAL_ORDER: dict[str, int] = {g: i for i, g in enumerate(CANONICAL_SECURITY_GOAL_IDS_ORDERED)}


def normalize_canonical_security_goals(goals: Iterable[str], *, allow_empty: bool) -> tuple[str, ...]:
    """Проверка членства в {ЦБ-1, ЦБ-2, ЦБ-3}; дедуп и порядок ЦБ-1 → ЦБ-3."""
    items = [str(g).strip() for g in goals if str(g).strip()]
    if not items:
        if allow_empty:
            return ()
        raise ValueError("security_goals are required")
    bad = [g for g in items if g not in CANONICAL_SECURITY_GOAL_IDS]
    if bad:
        raise ValueError(
            f"unknown security goal id(s): {bad}; allowed only: {list(CANONICAL_SECURITY_GOAL_IDS_ORDERED)}"
        )
    return tuple(sorted({g for g in items}, key=lambda x: _GOAL_ORDER[x]))
