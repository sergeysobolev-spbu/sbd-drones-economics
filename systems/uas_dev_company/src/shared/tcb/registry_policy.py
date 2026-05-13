"""Инварианты реестра и покупки (цели экземпляра и ТБ витрины/сделки)."""

from __future__ import annotations


def assert_certificate_not_revoked(certificate_status: str | None) -> None:
    if str(certificate_status or "active") == "revoked":
        raise ValueError("certificate revoked")


def assert_drone_goals_subset_when_local_regulator(
    *,
    chosen_goals: tuple[str, ...],
    effective_certificate_goals: list[str],
    regulator_integration_enabled: bool,
) -> None:
    """При локальном режиме без внешнего Регулятора ЦБ дрона проверяются здесь; при интеграции — на стороне Регулятора."""
    if regulator_integration_enabled:
        return
    if chosen_goals and not set(chosen_goals).issubset(set(effective_certificate_goals)):
        raise ValueError("security_goals must be a (possibly empty) subset of the certificate goals")


def validate_purchase_prerequisites(
    *,
    drone_status: str,
    certificate_status: str | None,
    registration_status: str | None,
    registration_id: str | None,
    regulator_integration_enabled: bool,
) -> None:
    assert_certificate_not_revoked(certificate_status)
    if str(drone_status) != "available":
        raise ValueError("available certified drone is required")
    if regulator_integration_enabled:
        if str(registration_status or "") == "revoked":
            raise ValueError("drone registration revoked")
        if str(registration_status or "") != "registered_by_regulator":
            raise ValueError("drone must be registered_by_regulator before purchase")
        if not str(registration_id or "").strip():
            raise ValueError("registration_id is required for purchase")


def drone_port_response_accepted(status: str) -> bool:
    return str(status or "").lower() in {"ok", "accepted", "delivered"}
