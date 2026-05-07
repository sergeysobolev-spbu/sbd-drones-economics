"""RBAC: проверка ролей действующего субъекта."""

from __future__ import annotations

from shared.tcb.errors import AuthorizationError
from shared.topics import Roles


def require_role(actual_role: str, expected_role: str) -> None:
    if actual_role != expected_role:
        raise AuthorizationError(f"role {expected_role} is required")


def require_developer_or_operator_for_registry(actor_role: str) -> None:
    if actor_role not in (Roles.DEVELOPER, Roles.OPERATOR):
        raise AuthorizationError("role разработчик or эксплуатант is required")
