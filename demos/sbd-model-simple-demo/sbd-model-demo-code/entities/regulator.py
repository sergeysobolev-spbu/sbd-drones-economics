from __future__ import annotations

"""Сущность `RegulatorEntity`: цели безопасности, сертификация и регистрация БАС."""

from typing import Any, Dict

from actions import (
    GET_SECURITY_GOALS,
    REQUEST_FIRMWARE_CERTIFICATION,
    REQUEST_UAS_REGISTRATION,
)
from base_entity import BaseEntity


class RegulatorEntity(BaseEntity):
    """Регулятор: security_goals, сертификаты прошивки, реестр UAS."""

    def _register_handlers(self) -> None:
        self.register_handler(GET_SECURITY_GOALS, self._on_get_security_goals)
        self.register_handler(REQUEST_FIRMWARE_CERTIFICATION, self._on_firmware_cert)
        self.register_handler(REQUEST_UAS_REGISTRATION, self._on_uas_registration)

    def _on_get_security_goals(self, msg: Dict[str, Any]) -> None:
        system_key = msg["payload"].get("system_key")
        goals = self.world["system_security_goals"].get(system_key, [])
        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "security_goals": [{"goal_id": g} for g in goals],
            },
        )

    def _on_firmware_cert(self, msg: Dict[str, Any]) -> None:
        payload = msg.get("payload", {})
        firmware_version = payload.get("firmware_version")
        vendor_code = payload.get("vendor_code")
        uas_type = payload.get("uas_type")
        if not firmware_version or not vendor_code or not uas_type:
            self.send_response(
                request_msg=msg,
                payload={"status": "error", "error": "invalid_firmware_request"},
            )
            return

        cert_id = (
            f"CERT-{str(uas_type).upper()}-"
            f"{str(vendor_code).upper()}-{str(firmware_version).replace('.', '_')}"
        )
        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "firmware_certification_result": {
                    "approved": True,
                    "certificate_id": cert_id,
                    "firmware_version": firmware_version,
                },
            },
        )

    def _on_uas_registration(self, msg: Dict[str, Any]) -> None:
        payload = msg.get("payload", {})
        uas_type = str(payload.get("uas_type", "")).upper()
        vendor_code = str(payload.get("vendor_code", "")).upper()
        imei = payload.get("imei")
        if not uas_type or not vendor_code or not imei:
            self.send_response(
                request_msg=msg,
                payload={"status": "error", "error": "invalid_uas_registration_request"},
            )
            return

        counters = self.world.setdefault("registration_counters", {})
        counter_key = f"{uas_type}:{vendor_code}"
        next_number = int(counters.get(counter_key, 0)) + 1
        counters[counter_key] = next_number
        registered_uas_id = f"UAS-{uas_type}-{vendor_code}-{next_number:06d}"
        registry = self.world.setdefault("uas_registry", {})
        registry[registered_uas_id] = {
            "imei": imei,
            "uas_type": uas_type,
            "vendor_code": vendor_code,
            "firmware_version": payload.get("firmware_version"),
        }
        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "registered_uas_id": registered_uas_id,
                "imei": imei,
            },
        )
