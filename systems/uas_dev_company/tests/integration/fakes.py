"""In-memory моки Регулятора, Эксплуатанта, Дронопорта и DroneAnalytics для контрактных интеграционных тестов."""

from __future__ import annotations

from typing import Any


class FakeRegulator:
    """Упрощённый Регулятор: сертификация, регистрация, перерегистрация, уязвимости, идемпотентность."""

    def __init__(self) -> None:
        self._cert_goals_by_fw: dict[str, tuple[str, ...]] = {}
        self._idempotency: dict[tuple[str, str], dict[str, Any]] = {}
        self.vuln_response: dict[str, Any] = {"decision": "revoke_certificate"}
        self.force_registration_reject: bool = False

    def _get(self, kind: str, correlation_id: str) -> dict[str, Any] | None:
        return self._idempotency.get((kind, correlation_id))

    def _set(self, kind: str, correlation_id: str, value: dict[str, Any]) -> None:
        self._idempotency[(kind, correlation_id)] = value

    def certify_firmware(self, envelope: dict[str, Any]) -> dict[str, Any]:
        cid = envelope["correlation_id"]
        cached = self._get("cert", cid)
        if cached is not None:
            return cached
        payload = envelope["payload"]
        fw = str(payload["firmware_id"])
        goals = tuple(str(g) for g in payload.get("security_goals") or ())
        self._cert_goals_by_fw[fw] = goals
        out: dict[str, Any] = {
            "status": "certified",
            "certificate_id": f"cert-drone-{fw}",
            "security_goals": list(goals),
            "signed_by": "fake.regulator",
        }
        self._set("cert", cid, out)
        return out

    def register_drone_instance(self, envelope: dict[str, Any]) -> dict[str, Any]:
        cid = envelope["correlation_id"]
        cached = self._get("reg", cid)
        if cached is not None:
            return cached
        if self.force_registration_reject:
            out = {"status": "rejected", "reason_code": "security_goals_mismatch"}
            self._set("reg", cid, out)
            return out
        p = envelope["payload"]
        fw = str(p["firmware_id"])
        cert_goals = set(self._cert_goals_by_fw.get(fw, ()))
        drone_goals = set(str(g) for g in (p.get("security_goals") or []))
        if drone_goals and not drone_goals.issubset(cert_goals):
            out = {"status": "rejected", "reason_code": "security_goals_mismatch"}
            self._set("reg", cid, out)
            return out
        serial = str(p["serial_number"])
        out = {
            "status": "registered",
            "registration_id": f"uas-reg-{serial}",
            "registration_version": 1,
        }
        self._set("reg", cid, out)
        return out

    def reregister_drone_instance(self, envelope: dict[str, Any]) -> dict[str, Any]:
        cid = envelope["correlation_id"]
        cached = self._get("rereg", cid)
        if cached is not None:
            return cached
        p = envelope["payload"]
        out: dict[str, Any] = {
            "status": "reregistered",
            "registration_id": str(p["registration_id"]),
            "registration_version": 2,
            "security_goals": None,
        }
        self._set("rereg", cid, out)
        return out

    def report_critical_vulnerability(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return dict(self.vuln_response)


class FakeOperatorRegistry:
    """Локальный парк Эксплуатанта после перерегистрации и решений Регулятора."""

    def __init__(self) -> None:
        self.drones: dict[str, dict[str, Any]] = {}
        self.events: list[tuple[str, dict[str, Any]]] = []

    def import_drone_reregistered(self, envelope: dict[str, Any]) -> None:
        p = envelope["payload"]
        serial = str(p["serial_number"])
        self.drones[serial] = dict(p)
        self.events.append(("reregistered", envelope))

    def apply_regulator_firmware_decision(self, envelope: dict[str, Any]) -> None:
        self.events.append(("firmware_decision", envelope))
        firmware_id = str(envelope["firmware_id"])
        decision = envelope["decision"]
        dec = str(decision.get("decision") or "")
        if dec == "revoke_certificate":
            for rec in self.drones.values():
                if str(rec.get("firmware_id")) == firmware_id:
                    rec["registration_status"] = "revoked"
        elif dec == "update_security_goals":
            goals = set(str(g) for g in (decision.get("effective_security_goals") or []))
            for rec in self.drones.values():
                if str(rec.get("firmware_id")) != firmware_id:
                    continue
                cur = set(str(g) for g in (rec.get("security_goals") or []))
                rec["security_goals"] = sorted(cur & goals)

    def select_for_mission(self, required_goals: list[str]) -> list[str]:
        """Дроны, удовлетворяющие обязательным ЦБ (пустые ЦБ дрона не подходят)."""
        need = set(str(g) for g in required_goals)
        ok: list[str] = []
        for serial, rec in self.drones.items():
            sg = rec.get("security_goals") or []
            if not sg:
                continue
            if need.issubset(set(str(g) for g in sg)):
                ok.append(serial)
        return ok


class FakeDronePort:
    """Имитация внешнего системного контракта доставки в systems.drone_port."""

    def __init__(self, valid_ports: set[str] | None = None) -> None:
        self.valid_ports: set[str] = set(valid_ports or ())
        self.envelopes: list[dict[str, Any]] = []

    def accept_delivered_drone(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self.envelopes.append(envelope)
        port = str(envelope.get("payload", {}).get("port_id") or "")
        if self.valid_ports and port not in self.valid_ports:
            return {"status": "rejected", "reason_code": "unknown_droneport"}
        return {"status": "accepted"}


class FakeDroneAnalytics:
    """Накопление EventLogItem и имитация отказа журнала."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.events: list[dict[str, Any]] = []

    def post_event(self, event: dict[str, Any]) -> dict[str, Any]:
        if self.fail:
            return {"ok": False, "error": "journal unavailable", "status_code": 503}
        self.events.append(event)
        return {"ok": True, "status_code": 200}
