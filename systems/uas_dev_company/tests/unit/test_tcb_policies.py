"""Прямые тесты чистого ядра `shared.tcb` (политики без SQLite/HTTP)."""

from __future__ import annotations

import pytest

from shared.models import SecurityEvent
from shared.tcb import (
    apply_effective_goals_to_drone_goals,
    assert_drone_goals_subset_when_local_regulator,
    build_analytics_event_payload,
    drone_port_response_accepted,
    normalize_canonical_security_goals,
    regulator_certify_status_ok,
    regulator_register_status_ok,
    regulator_reregistration_status_ok,
    require_developer_or_operator_for_registry,
    require_role,
    security_event_to_analytics_payload,
    validate_purchase_prerequisites,
)
from shared.tcb.errors import AuthorizationError
from shared.tcb.journal_policy import domain_to_log_service, stable_service_id
from shared.topics import Roles


def test_normalize_canonical_security_goals_only_cb123() -> None:
    assert normalize_canonical_security_goals(["ЦБ-3", "ЦБ-1"], allow_empty=False) == ("ЦБ-1", "ЦБ-3")
    assert normalize_canonical_security_goals([], allow_empty=True) == ()
    with pytest.raises(ValueError, match="unknown security goal"):
        normalize_canonical_security_goals(["ЦБ-1", "ЦБ-X"], allow_empty=False)


def test_require_role_raises_for_admin_on_dev() -> None:
    with pytest.raises(AuthorizationError):
        require_role(Roles.ADMIN, Roles.DEVELOPER)


def test_require_developer_or_operator_for_registry() -> None:
    require_developer_or_operator_for_registry(Roles.DEVELOPER)
    require_developer_or_operator_for_registry(Roles.OPERATOR)
    with pytest.raises(AuthorizationError):
        require_developer_or_operator_for_registry(Roles.ADMIN)


@pytest.mark.parametrize(
    "status,ok",
    [
        ("certified", True),
        ("Registered", True),
        ("rejected", False),
    ],
)
def test_regulator_certify_status_ok(status: str, ok: bool) -> None:
    assert regulator_certify_status_ok(status) is ok


@pytest.mark.parametrize(
    "status,ok",
    [
        ("reregistered", True),
        ("accepted", True),
        ("pending", False),
    ],
)
def test_regulator_reregistration_status_ok(status: str, ok: bool) -> None:
    assert regulator_reregistration_status_ok(status) is ok


@pytest.mark.parametrize(
    "status,ok",
    [
        ("registered", True),
        ("unknown", False),
    ],
)
def test_regulator_register_status_ok(status: str, ok: bool) -> None:
    assert regulator_register_status_ok(status) is ok


def test_validate_purchase_prerequisites_local_mode() -> None:
    validate_purchase_prerequisites(
        drone_status="available",
        certificate_status="active",
        registration_status="none",
        registration_id=None,
        regulator_integration_enabled=False,
    )
    with pytest.raises(ValueError, match="available certified"):
        validate_purchase_prerequisites(
            drone_status="sold",
            certificate_status="active",
            registration_status=None,
            registration_id=None,
            regulator_integration_enabled=False,
        )


def test_validate_purchase_prerequisites_regulator_mode() -> None:
    validate_purchase_prerequisites(
        drone_status="available",
        certificate_status="active",
        registration_status="registered_by_regulator",
        registration_id="R-1",
        regulator_integration_enabled=True,
    )
    with pytest.raises(ValueError, match="registered_by_regulator"):
        validate_purchase_prerequisites(
            drone_status="available",
            certificate_status="active",
            registration_status="local_only",
            registration_id="R-1",
            regulator_integration_enabled=True,
        )
    with pytest.raises(ValueError, match="registration revoked"):
        validate_purchase_prerequisites(
            drone_status="available",
            certificate_status="active",
            registration_status="revoked",
            registration_id="R-1",
            regulator_integration_enabled=True,
        )


def test_drone_port_response_accepted() -> None:
    assert drone_port_response_accepted("OK") is True
    assert drone_port_response_accepted("rejected") is False


def test_apply_effective_goals_to_drone_goals() -> None:
    assert apply_effective_goals_to_drone_goals(["ЦБ-1", "ЦБ-2"], ["ЦБ-2", "ЦБ-3"]) == ("ЦБ-2",)


def test_assert_drone_goals_subset_when_local_regulator() -> None:
    assert_drone_goals_subset_when_local_regulator(
        chosen_goals=("ЦБ-1",),
        effective_certificate_goals=["ЦБ-1", "ЦБ-2"],
        regulator_integration_enabled=False,
    )
    assert_drone_goals_subset_when_local_regulator(
        chosen_goals=(),
        effective_certificate_goals=["ЦБ-1"],
        regulator_integration_enabled=False,
    )
    with pytest.raises(ValueError, match="subset"):
        assert_drone_goals_subset_when_local_regulator(
            chosen_goals=("ЦБ-2",),
            effective_certificate_goals=["ЦБ-1"],
            regulator_integration_enabled=False,
        )
    # При интеграции с Регулятором локальная проверка не дублирует его решение
    assert_drone_goals_subset_when_local_regulator(
        chosen_goals=("ЦБ-2",),
        effective_certificate_goals=["ЦБ-1"],
        regulator_integration_enabled=True,
    )


def test_build_analytics_event_payload_shape() -> None:
    p = build_analytics_event_payload(message="evt", severity="notice")
    assert p["message"] == "evt"
    assert p["severity"] == "notice"
    assert p["service"] == "registry"
    assert "timestamp" in p


def test_stable_service_id_stable_and_positive() -> None:
    a = stable_service_id("user_management_worker")
    b = stable_service_id("user_management_worker")
    assert a == b and a >= 1


def test_security_event_to_analytics_includes_ts_and_instance() -> None:
    ev = SecurityEvent("t1", "warning", "user_management", "subj", "d")
    p = security_event_to_analytics_payload(ev, instance_id_override="um-1", now=1_700_000_000.0)
    assert p["severity"] == "warning"
    assert p["service"] == "operator"
    assert "ts_utc=" in p["message"]
    assert "instance_id=um-1" in p["message"]
    assert "t1" in p["message"] and "subj" in p["message"]
    assert p["timestamp"] == 1_700_000_000
    assert p["service_id"] == stable_service_id("um-1:user_management")


def test_domain_to_log_service_defaults_registry() -> None:
    assert domain_to_log_service("unknown_domain") == "registry"
