"""Проверка межсистемных конвертов для моков на шине (INT-NFR-2, integration_tasks.md)."""

from __future__ import annotations

from typing import Any

from shared.tcb.cb_constants import CANONICAL_SECURITY_GOAL_IDS


class AdjacentContractError(ValueError):
    """Нарушение контракта сообщения для смежной системы."""


def _require_str(d: dict[str, Any], key: str) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise AdjacentContractError(f"missing or invalid {key}")
    return v.strip()


def assert_int_nfr2_envelope(envelope: dict[str, Any], *, require_actor: bool = True) -> None:
    _require_str(envelope, "schema_version")
    _require_str(envelope, "correlation_id")
    _require_str(envelope, "sender")
    _require_str(envelope, "timestamp")
    if require_actor:
        _require_str(envelope, "actor")


def _validate_security_goals_list(raw: Any, *, allow_empty: bool) -> None:
    if raw is None:
        if not allow_empty:
            raise AdjacentContractError("security_goals required")
        return
    if not isinstance(raw, list):
        raise AdjacentContractError("security_goals must be a list")
    if not raw and not allow_empty:
        raise AdjacentContractError("security_goals must not be empty")
    for g in raw:
        if str(g).strip() not in CANONICAL_SECURITY_GOAL_IDS:
            raise AdjacentContractError(f"invalid security goal: {g}")


def validate_regulator_certify_envelope(envelope: dict[str, Any]) -> None:
    assert_int_nfr2_envelope(envelope, require_actor=True)
    if envelope["schema_version"] != "uas-cert.v1":
        raise AdjacentContractError("expected schema_version uas-cert.v1")
    p = envelope.get("payload")
    if not isinstance(p, dict):
        raise AdjacentContractError("payload must be dict")
    for k in (
        "firmware_id",
        "supplier",
        "drone_type",
        "version",
        "security_goals",
        "authenticity_proof",
    ):
        if k not in p:
            raise AdjacentContractError(f"payload missing {k}")
    _validate_security_goals_list(p.get("security_goals"), allow_empty=True)


def validate_regulator_register_envelope(envelope: dict[str, Any]) -> None:
    assert_int_nfr2_envelope(envelope, require_actor=True)
    if envelope["schema_version"] != "uas-registration.v1":
        raise AdjacentContractError("expected schema_version uas-registration.v1")
    p = envelope.get("payload")
    if not isinstance(p, dict):
        raise AdjacentContractError("payload must be dict")
    for k in (
        "serial_number",
        "drone_type",
        "firmware_id",
        "certificate_id",
        "hardware_config",
        "declared_price",
    ):
        if k not in p:
            raise AdjacentContractError(f"payload missing {k}")
    _validate_security_goals_list(p.get("security_goals"), allow_empty=True)


def validate_regulator_reregister_envelope(envelope: dict[str, Any]) -> None:
    assert_int_nfr2_envelope(envelope, require_actor=True)
    if envelope["schema_version"] != "uas-registration.v1":
        raise AdjacentContractError("expected schema_version uas-registration.v1")
    p = envelope.get("payload")
    if not isinstance(p, dict):
        raise AdjacentContractError("payload must be dict")
    for k in (
        "registration_id",
        "serial_number",
        "from_owner_id",
        "to_owner_id",
        "certificate_id",
        "purchase_order_id",
    ):
        if k not in p or not str(p.get(k) or "").strip():
            raise AdjacentContractError(f"payload missing or empty {k}")


def validate_regulator_vuln_envelope(envelope: dict[str, Any]) -> None:
    assert_int_nfr2_envelope(envelope, require_actor=False)
    if envelope["schema_version"] != "uas-vuln.v1":
        raise AdjacentContractError("expected schema_version uas-vuln.v1")
    p = envelope.get("payload")
    if not isinstance(p, dict):
        raise AdjacentContractError("payload must be dict")
    if not str(p.get("firmware_id") or "").strip():
        raise AdjacentContractError("payload.firmware_id required")


def validate_operator_import_reregistered_envelope(envelope: dict[str, Any]) -> None:
    assert_int_nfr2_envelope(envelope, require_actor=False)
    if envelope["schema_version"] != "uas-registration-event.v1":
        raise AdjacentContractError("expected schema_version uas-registration-event.v1")
    p = envelope.get("payload")
    if not isinstance(p, dict):
        raise AdjacentContractError("payload must be dict")
    for k in UAS_REG_EVENT_KEYS:
        if k not in p:
            raise AdjacentContractError(f"payload missing {k}")

    _validate_security_goals_list(p.get("security_goals"), allow_empty=True)


UAS_REG_EVENT_KEYS = (
    "registration_id",
    "registration_version",
    "serial_number",
    "owner_operator_id",
    "certificate_id",
    "firmware_id",
    "status",
)


def validate_operator_apply_decision(envelope: dict[str, Any]) -> None:
    for k in ("firmware_id", "correlation_id", "decision"):
        if k not in envelope:
            raise AdjacentContractError(f"missing {k}")
    if not isinstance(envelope["decision"], dict):
        raise AdjacentContractError("decision must be dict")


def validate_drone_port_delivery_envelope(envelope: dict[str, Any]) -> None:
    assert_int_nfr2_envelope(envelope, require_actor=False)
    if envelope["schema_version"] != "uas-droneport-delivery.v1":
        raise AdjacentContractError("expected schema_version uas-droneport-delivery.v1")
    p = envelope.get("payload")
    if not isinstance(p, dict):
        raise AdjacentContractError("payload must be dict")
    for k in ("serial_number", "port_id", "registration_id", "certificate_id"):
        if not str(p.get(k) or "").strip():
            raise AdjacentContractError(f"payload.{k} required")


def validate_analytics_event(event: dict[str, Any]) -> None:
    if not isinstance(event, dict) or not event:
        raise AdjacentContractError("event must be a non-empty dict")
    if "event_type" not in event and "message" not in event:
        raise AdjacentContractError("event should include event_type or message")


def validate_regulator_action_envelope(action: str, envelope: dict[str, Any]) -> None:
    if action == "certify_firmware":
        validate_regulator_certify_envelope(envelope)
    elif action == "register_drone_instance":
        validate_regulator_register_envelope(envelope)
    elif action == "reregister_drone_instance":
        validate_regulator_reregister_envelope(envelope)
    elif action == "report_critical_vulnerability":
        validate_regulator_vuln_envelope(envelope)
    else:
        raise AdjacentContractError(f"unknown regulator action: {action}")
