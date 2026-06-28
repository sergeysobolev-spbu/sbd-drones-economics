from __future__ import annotations

"""Сущность `VendorUASEntity`: сертификация/регистрация и продажа БАС."""

from typing import Any, Dict, List

from actions import (
    REQUEST_FIRMWARE_CERTIFICATION,
    REQUEST_UAS_REGISTRATION,
    REQUEST_UAS_PURCHASE,
)
from base_entity import BaseEntity


class VendorUASEntity(BaseEntity):
    """Вендор БАС: прокси к Regulator и сценарий закупки N БАС."""

    def _register_handlers(self) -> None:
        self.register_handler(REQUEST_FIRMWARE_CERTIFICATION, self._on_firmware_certification)
        self.register_handler(REQUEST_UAS_REGISTRATION, self._on_uas_registration)
        self.register_handler(REQUEST_UAS_PURCHASE, self._on_uas_purchase)

    def _register_one_uas(
        self,
        *,
        uas_type: str,
        vendor_code: str,
        imei: str,
        firmware_version: str,
        trace_id: str | None,
        parent_span_id: str | None,
    ) -> Dict[str, Any]:
        return self.rpc_send_wait(
            receiver="regulator",
            action=REQUEST_UAS_REGISTRATION,
            payload={
                "uas_type": uas_type,
                "vendor_code": vendor_code,
                "imei": imei,
                "firmware_version": firmware_version,
            },
            timeout_s=20.0,
            expected_sender="regulator",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )

    def _on_firmware_certification(self, msg: Dict[str, Any]) -> None:
        trace_id = msg.get("trace_id")
        parent_span_id = msg.get("span_id")
        payload = msg.get("payload", {})
        regulator_resp = self.rpc_send_wait(
            receiver="regulator",
            action=REQUEST_FIRMWARE_CERTIFICATION,
            payload={
                "firmware_version": payload.get("firmware_version"),
                "vendor_code": payload.get("vendor_code"),
                "uas_type": payload.get("uas_type"),
                "artifacts": payload.get("artifacts", []),
            },
            timeout_s=20.0,
            expected_sender="regulator",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        self.send_response(request_msg=msg, payload=regulator_resp)

    def _on_uas_registration(self, msg: Dict[str, Any]) -> None:
        trace_id = msg.get("trace_id")
        parent_span_id = msg.get("span_id")
        payload = msg.get("payload", {})
        regulator_resp = self.rpc_send_wait(
            receiver="regulator",
            action=REQUEST_UAS_REGISTRATION,
            payload={
                "uas_type": payload.get("uas_type"),
                "vendor_code": payload.get("vendor_code"),
                "imei": payload.get("imei"),
                "firmware_version": payload.get("firmware_version"),
            },
            timeout_s=20.0,
            expected_sender="regulator",
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        self.send_response(request_msg=msg, payload=regulator_resp)

    def _on_uas_purchase(self, msg: Dict[str, Any]) -> None:
        trace_id = msg.get("trace_id")
        parent_span_id = msg.get("span_id")
        payload = msg.get("payload", {})

        quantity = int(payload.get("quantity", 0))
        if quantity <= 0:
            self.send_response(
                request_msg=msg,
                payload={"status": "error", "error": "invalid_quantity"},
            )
            return

        uas_type = str(payload.get("uas_type", "GENERIC"))
        vendor_code = str(payload.get("vendor_code", "VENDOR"))
        firmware_version = str(payload.get("firmware_version", "1.0.0"))
        imeis: List[str] = list(payload.get("imeis", []))

        if len(imeis) < quantity:
            self.send_response(
                request_msg=msg,
                payload={"status": "error", "error": "not_enough_imeis"},
            )
            return

        registered_uas_ids: List[str] = []
        for imei in imeis[:quantity]:
            reg_resp = self._register_one_uas(
                uas_type=uas_type,
                vendor_code=vendor_code,
                imei=imei,
                firmware_version=firmware_version,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
            )
            if reg_resp.get("status") != "ok":
                self.send_response(request_msg=msg, payload=reg_resp)
                return
            registered_uas_ids.append(reg_resp["registered_uas_id"])

        self.send_response(
            request_msg=msg,
            payload={
                "status": "ok",
                "uas_purchase_result": {
                    "registered_uas_ids": registered_uas_ids,
                    "quantity": quantity,
                },
            },
        )
