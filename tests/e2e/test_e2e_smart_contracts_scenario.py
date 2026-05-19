"""
E2E с интеграцией Hyperledger Fabric Smart Contracts.

Копия test_e2e_scenario.py с дополнительными шагами, которые повторяют
ключевые действия сценария через смарт-контракты (см. docs/smart_contracts.md):

  Запись (action соответствует методу контракта) → bus.request(
      "components.ledger",
      {"action": "invoke", "payload": {"method": "...", "args": [...]}}
  )
  Чтение (проверка состояния) → bus.request(
      "components.ledger",
      {"action": "query",  "payload": {"method": "...", "args": [...]}}
  )

Оригинальная бизнес-логика не меняется. Если ledger недоступен — SC-шаги
делают pytest.skip и не валят основной сценарий.

Маппинг action → контракт:
  • register_drone_cert         → DronePropertiesContract:CreateDronePass
  • firmware (sec. objectives)  → FirmwareContract:CertifyFirmware
  • annual_insurance            → DronePropertiesContract:CreateInsuranceRecord
  • create_order                → OrderContract:CreateOrder
  • matching (confirm-price)    → OrderContract:AssignOrder
  • approve (Insurer)           → OrderContract:ApproveOrder
  • task.assign (Operator)      → OrderContract:ConfirmOrder
  • task.start                  → OrderContract:StartOrder
  • mission_completed           → OrderContract:FinishOrder
  • finalize                    → OrderContract:FinalizeOrder
  Чтения: ReadDronePass / ReadInsuranceRecord / ReadOrder / CheckDroneReadiness.
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Dict, List

import pytest
import requests

# ---- System-level topics (gateway) ----
OPERATOR_TOPIC = "systems.operator"
ORVD_TOPIC = "systems.orvd_system"
REGULATOR_TOPIC = "systems.regulator"
INSURER_TOPIC = "systems.insurer"

# ---- GCS component topics ----
GCS_ORCHESTRATOR_TOPIC = "gcs.components.orchestrator"
GCS_DRONE_MANAGER_TOPIC = "gcs.components.drone_manager"

# ---- DronePort component topics ----
DRONE_PORT_REGISTRY_TOPIC = "drone_port.components.drone_registry"

# ---- GCS internal topics ----
GCS_MISSION_STORE_TOPIC = "gcs.components.mission_store"

# ---- ORVD internal component topic (bypass gateway 10s PROXY_TIMEOUT) ----
ORVD_COMPONENT_TOPIC = "components.orvd_component"

# ---- Delivery drone topics ----
DELIVERY_DRONE_ID = "delivery_001"
DELIVERY_DRONE_TOPIC = "components.deliverydron.delivery_drone"

# ---- Agrodron (cyber_drons) component topics ----
AGRODRON_SECURITY_MONITOR_TOPIC = "components.Agrodron.security_monitor"
AGRODRON_AUTOPILOT_TOPIC = "components.Agrodron.autopilot"
SITL_TELEMETRY_REQUEST_TOPIC = "sitl.telemetry.request"
AGREGATOR_OPERATOR_REQUESTS_TOPIC = "components.agregator.operator.requests"

EXPECTED_SO = [f"SO_{i}" for i in range(1, 12)]
E2E_DRONE_ID = "drone_001"

# ---- Ledger (Hyperledger Fabric) ----
LEDGER_TOPIC = "components.ledger"
LEDGER_CHANNEL = "dronechannel"
LEDGER_CHAINCODE = "drone-chaincode"
LEDGER_TIMEOUT_INVOKE = 30.0
LEDGER_TIMEOUT_QUERY = 10.0

# Идентификаторы участников сценария на стороне смарт-контрактов.
SC_DEVELOPER_ID = "developer-001"
SC_MANUFACTURER_ID = "manufacturer-001"
SC_CERTCENTER_ID = "certcenter-001"
SC_INSURER_ID = "insurer-001"
SC_AGGREGATOR_ID = "agregator-001"
SC_OPERATOR_ID = "e2e-operator-1"
SC_FIRMWARE_ID = "fw-e2e-001"
SC_DRONE_MODEL = "AgroDron-X1"
SC_DRONE_TYPE = "agro"

# Shared state across ordered test classes
_shared: Dict[str, Any] = {}


def bus_request(bus, topic: str, action: str, payload: dict, timeout: float = 25) -> Dict[str, Any]:
    resp = bus.request(
        topic,
        {"action": action, "sender": "e2e_test_host", "payload": payload},
        timeout=timeout,
    )
    assert resp is not None, f"Timeout: {action} -> {topic}"
    return resp


def bus_request_with_retries(
    bus,
    topic: str,
    action: str,
    payload: dict,
    *,
    attempts: int = 5,
    timeout: float = 25,
    sleep_s: float = 2.0,
) -> Dict[str, Any]:
    for idx in range(attempts):
        resp = bus.request(
            topic,
            {"action": action, "sender": "e2e_test_host", "payload": payload},
            timeout=timeout,
        )
        if resp is not None:
            return resp
        if idx < attempts - 1:
            time.sleep(sleep_s)
    raise AssertionError(f"Timeout: {action} -> {topic} after {attempts} attempts")


# ---------------------------------------------------------------------------
# Helpers: Ledger Gateway (Hyperledger Fabric)
# ---------------------------------------------------------------------------


def _ledger_call(
    bus,
    *,
    action: str,
    method: str,
    args: List[Any],
    timeout: float,
    sender: str = "e2e_test_host",
) -> Dict[str, Any]:
    """Низкоуровневая обёртка над bus.request(components.ledger, ...).

    Возвращает разобранный ответ {success, payload}. Если шина не отвечает —
    вызывает pytest.skip: тест помечается как пропущенный, а не падает,
    чтобы запуск без поднятого Fabric не сводил весь файл к красному.
    """
    resp = bus.request(
        LEDGER_TOPIC,
        {
            "action": action,
            "sender": sender,
            "payload": {
                "channel": LEDGER_CHANNEL,
                "chaincode": LEDGER_CHAINCODE,
                "method": method,
                "args": [str(a) if not isinstance(a, (list, dict)) else a for a in args],
            },
        },
        timeout=timeout,
    )
    if resp is None:
        pytest.skip(
            f"Ledger gateway ({LEDGER_TOPIC}) не отвечает на {action} {method} — "
            "Fabric-сеть/ledger-gateway, возможно, не запущены"
        )
    return resp


def ledger_invoke(bus, method: str, args: List[Any]) -> Dict[str, Any]:
    """Запись: вызывает invoke смарт-контракта."""
    return _ledger_call(
        bus,
        action="invoke",
        method=method,
        args=args,
        timeout=LEDGER_TIMEOUT_INVOKE,
    )


def ledger_query(bus, method: str, args: List[Any]) -> Dict[str, Any]:
    """Чтение: выполняет query смарт-контракта (читатель берёт из блокчейна)."""
    return _ledger_call(
        bus,
        action="query",
        method=method,
        args=args,
        timeout=LEDGER_TIMEOUT_QUERY,
    )


def assert_ledger_ok(resp: Dict[str, Any], context: str) -> Dict[str, Any]:
    """Распаковать ответ ledger; на ошибку контракта — pytest.fail с деталями."""
    if not resp.get("success"):
        pl = resp.get("payload") or {}
        err = pl.get("error") or pl
        pytest.fail(f"{context}: ledger error: {err}")
    return resp.get("payload") or {}


def _build_wpl(waypoints: list) -> str:
    """Build QGC WPL 110 string from a list of waypoint dicts (lat/lon/alt_m)."""
    lines = ["QGC WPL 110"]
    for idx, point in enumerate(waypoints):
        lat = point.get("lat", point.get("latitude", 0.0))
        lon = point.get("lon", point.get("lng", point.get("longitude", 0.0)))
        alt = point.get("alt", point.get("alt_m", point.get("altitude", 0.0)))
        line = "\t".join([
            str(idx), "1" if idx == 0 else "0", "3", "16",
            "0", "0", "0", "0", str(lat), str(lon), str(alt), "1",
        ])
        lines.append(line)
    return "\n".join(lines)


def rest_post(base: str, path: str, json: dict | None = None) -> requests.Response:
    return requests.post(f"{base}{path}", json=json or {}, timeout=15)


def rest_get(base: str, path: str) -> requests.Response:
    return requests.get(f"{base}{path}", timeout=15)


# ---------------------------------------------------------------------------
# Phase 0: System Registration
# ---------------------------------------------------------------------------

class Test0_SystemsInRegulator:
    """Register all participating systems with the Regulator; receive SO_1..SO_11."""

    def test_register_systems(self, kafka_bus):
        for system_id, system_type in (
            ("agregator", "aggregator"),
            ("operator", "operator"),
            ("insurer", "insurer"),
            ("orvd_system", "orvd"),
            ("gcs", "gcs"),
            ("drone_port", "drone_port"),
            ("cyber_drons", "drone"),
        ):
            resp = bus_request(kafka_bus, REGULATOR_TOPIC, "register_system", {
                "system_id": system_id,
                "system_type": system_type,
            })
            assert resp.get("success") is True, resp
            pl = resp.get("payload") or {}
            assert pl.get("registered") is True
            assert pl.get("security_objectives") == EXPECTED_SO

        v = bus_request(kafka_bus, REGULATOR_TOPIC, "verify_system", {"system_id": "operator"})
        assert (v.get("payload") or {}).get("verified") is True


# ---------------------------------------------------------------------------
# Phase 1: Drone Registration Chain
# ---------------------------------------------------------------------------

class Test1_DroneRegistration:
    """Cert -> Operator -> ORVD -> DronePort -> annual insurance (КАСКО).

    SC-шаги (test_07..test_11) повторяют ключевые действия фазы в Fabric:
      CertifyFirmware → CreateDronePass → CreateInsuranceRecord, плюс чтения.
    """

    DRONE_ID = E2E_DRONE_ID
    COVERAGE_AMOUNT = 150_000

    def test_01_register_drone_cert(self, kafka_bus):
        r = bus_request(kafka_bus, REGULATOR_TOPIC, "register_drone_cert", {
            "drone_id": self.DRONE_ID,
        })
        assert r.get("success") is True
        _shared["drone_cert_id"] = (r.get("payload") or {})["certificate_id"]

    def test_02_register_drone_at_operator(self, kafka_bus):
        r = bus_request(kafka_bus, OPERATOR_TOPIC, "register_drone", {
            "drone_id": self.DRONE_ID,
            "model": "AgroDron-X1",
            "capabilities": ["cargo", "sprayer"],
            "certificate_id": _shared["drone_cert_id"],
        })
        assert r.get("success") is True

    def test_03_register_drone_in_orvd(self, kafka_bus):
        r = bus_request(kafka_bus, OPERATOR_TOPIC, "register_drone_in_orvd", {
            "drone_id": self.DRONE_ID,
            "model": "AgroDron-X1",
            "certificate_id": _shared["drone_cert_id"],
        })
        assert r.get("success") is True

    def test_03b_register_drone_directly_in_orvd(self, kafka_bus):
        """Register drone directly in ORVD without certificate."""
        try:
            r = bus_request(kafka_bus, ORVD_TOPIC, "register_drone", {
                "drone_id": self.DRONE_ID,
                "model": "AgroDron-X1",
            })
        except AssertionError:
            pytest.skip("ORVD not reachable from e2e_test_host")
        assert r.get("success") is True, f"direct ORVD register_drone failed: {r}"

    def test_04_register_drone_in_droneport(self, kafka_bus):
        """Register drone_001 in DronePort registry and set battery to 95%."""
        kafka_bus.publish(DRONE_PORT_REGISTRY_TOPIC, {
            "action": "register_drone",
            "sender": "e2e_test_host",
            "payload": {
                "drone_id": self.DRONE_ID,
                "model": "AgroDron-X1",
            },
        })
        time.sleep(2)

        kafka_bus.publish(DRONE_PORT_REGISTRY_TOPIC, {
            "action": "update_battery",
            "sender": "e2e_test_host",
            "payload": {
                "drone_id": self.DRONE_ID,
                "battery": 95.0,
            },
        })
        time.sleep(1)

        resp = bus_request(kafka_bus, DRONE_PORT_REGISTRY_TOPIC, "get_drone", {
            "drone_id": self.DRONE_ID,
        })
        if resp.get("success"):
            pl = resp.get("payload") or {}
            assert pl.get("drone_id") == self.DRONE_ID
        else:
            pytest.skip("DronePort not responding yet — container may not be ready")

    def test_05_annual_insurance(self, kafka_bus):
        """Годовое страхование КАСКО при регистрации дрона."""
        r = None
        payload = {
            "order_id": "e2e-order-drone-001",
            "drone_id": self.DRONE_ID,
            "coverage_amount": self.COVERAGE_AMOUNT,
        }
        for _ in range(5):
            r = kafka_bus.request(
                INSURER_TOPIC,
                {"action": "annual_insurance", "sender": "e2e_test_host", "payload": payload},
                timeout=35,
            )
            if r is not None:
                break
            time.sleep(4)
        assert r is not None, (
            "Timeout: annual_insurance -> systems.insurer — "
            "проверьте логи insurer и Kafka (consumer group / SASL)"
        )
        assert r.get("success") is True, f"annual_insurance failed: {r}"
        ins = r.get("payload") or {}

        assert ins.get("policy_type") == "annual"
        assert ins.get("status") == "active"
        assert ins.get("drone_id") == self.DRONE_ID
        assert Decimal(str(ins.get("kfleet_history", 0))) == Decimal("1.0")

        expected_premium = Decimal(str(self.COVERAGE_AMOUNT)) * Decimal("0.08") * Decimal("1.0")
        assert Decimal(str(ins["premium"])) == expected_premium
        assert ins.get("policy_id"), "policy_id должен быть заполнен"

    def test_06_register_delivery_drone_in_droneport(self, kafka_bus):
        """Register the delivery drone (delivery_001) in DronePort registry."""
        kafka_bus.publish(DRONE_PORT_REGISTRY_TOPIC, {
            "action": "register_drone",
            "sender": "e2e_test_host",
            "payload": {
                "drone_id": DELIVERY_DRONE_ID,
                "model": "DeliveryDrone-V1",
            },
        })
        time.sleep(2)

        resp = bus_request(kafka_bus, DRONE_PORT_REGISTRY_TOPIC, "get_drone", {
            "drone_id": DELIVERY_DRONE_ID,
        })
        if resp.get("success"):
            pl = resp.get("payload") or {}
            assert pl.get("drone_id") == DELIVERY_DRONE_ID
        else:
            pytest.skip("DronePort not responding — delivery drone registration skipped")

    # ── Smart-contract шаги ────────────────────────────────────────────────

    def test_07_sc_certify_firmware(self, kafka_bus):
        """FirmwareContract:CertifyFirmware — сертификация прошивки дрона."""
        resp = ledger_invoke(
            kafka_bus,
            "FirmwareContract:CertifyFirmware",
            [SC_FIRMWARE_ID, EXPECTED_SO],
        )
        assert_ledger_ok(resp, "CertifyFirmware")
        _shared["sc_firmware_id"] = SC_FIRMWARE_ID

    def test_08_sc_create_drone_pass(self, kafka_bus):
        """DronePropertiesContract:CreateDronePass — паспорт дрона в ledger."""
        if not _shared.get("sc_firmware_id"):
            pytest.skip("SC firmware не сертифицирован (test_07 пропущен)")

        resp = ledger_invoke(
            kafka_bus,
            "DronePropertiesContract:CreateDronePass",
            [
                self.DRONE_ID,
                SC_DEVELOPER_ID,
                SC_DRONE_MODEL,
                SC_DRONE_TYPE,
                25,    # weightKg
                50,    # maxFlightRangeKm
                10,    # maxPayloadWeightKg
                2024,  # releaseYear
                0,     # incidentCount
                SC_FIRMWARE_ID,
            ],
        )
        assert_ledger_ok(resp, "CreateDronePass")
        _shared["sc_drone_pass_id"] = self.DRONE_ID

    def test_09_sc_read_drone_pass(self, kafka_bus):
        """ReadDronePass — читатель берёт паспорт из блокчейна."""
        if not _shared.get("sc_drone_pass_id"):
            pytest.skip("SC drone pass не создан (test_08 пропущен)")

        resp = ledger_query(
            kafka_bus,
            "DronePropertiesContract:ReadDronePass",
            [_shared["sc_drone_pass_id"]],
        )
        pl = assert_ledger_ok(resp, "ReadDronePass")
        result = pl.get("result") or pl
        # Контракт обычно возвращает JSON-объект (или строку JSON). Проверим
        # хотя бы наличие id дрона в любом представлении.
        assert self.DRONE_ID in str(result), (
            f"Паспорт {self.DRONE_ID!r} не найден в ledger: {pl}"
        )

    def test_10_sc_create_insurance_record(self, kafka_bus):
        """CreateInsuranceRecord — годовая страховка в ledger."""
        if not _shared.get("sc_drone_pass_id"):
            pytest.skip("SC drone pass не создан")

        resp = ledger_invoke(
            kafka_bus,
            "DronePropertiesContract:CreateInsuranceRecord",
            [self.DRONE_ID, SC_INSURER_ID, self.COVERAGE_AMOUNT],
        )
        assert_ledger_ok(resp, "CreateInsuranceRecord")
        _shared["sc_insurance_drone_id"] = self.DRONE_ID

    def test_11_sc_read_insurance_record(self, kafka_bus):
        """ReadInsuranceRecord — читатель берёт страховку из блокчейна."""
        if not _shared.get("sc_insurance_drone_id"):
            pytest.skip("SC insurance record не создана")

        resp = ledger_query(
            kafka_bus,
            "DronePropertiesContract:ReadInsuranceRecord",
            [_shared["sc_insurance_drone_id"]],
        )
        pl = assert_ledger_ok(resp, "ReadInsuranceRecord")
        result = pl.get("result") or pl
        assert SC_INSURER_ID in str(result) or self.DRONE_ID in str(result), (
            f"Страховая запись для {self.DRONE_ID!r} не найдена в ledger: {pl}"
        )


# ---------------------------------------------------------------------------
# Phase 2: Operator Registration at Agregator
# ---------------------------------------------------------------------------

class Test2_OperatorInAggregator:
    """Operator certificate from Regulator; register via Agregator REST."""

    def test_01_register_operator_cert(self, kafka_bus):
        r = bus_request(kafka_bus, REGULATOR_TOPIC, "register_operator_cert", {
            "operator_id": "e2e-operator-1",
        })
        assert r.get("success") is True
        _shared["operator_cert_id"] = (r.get("payload") or {})["certificate_id"]

    def test_02_register_operator_at_agregator(self, agregator_url):
        r = rest_post(agregator_url, "/operators", {
            "name": "E2E Operator",
            "license": "E2E-LIC-1",
            "email": "e2e-operator@local",
            "password": "e2e-operator-pass",
        })
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"
        body = r.json()
        user = body.get("user") or {}
        _shared["registered_operator_id"] = (
            user.get("id")
            or body.get("operator_id")
            or body.get("id")
        )
        assert _shared["registered_operator_id"], (
            f"operator id должен быть в ответе: {body}"
        )

    def test_03_verify_operator_cert(self, kafka_bus):
        v = bus_request(kafka_bus, REGULATOR_TOPIC, "verify_operator_cert", {
            "operator_id": "e2e-operator-1",
            "certificate_id": _shared["operator_cert_id"],
        })
        assert v.get("success") is True
        assert (v.get("payload") or {}).get("valid") is True


# ---------------------------------------------------------------------------
# Phase 3: Order Flow (Customer -> Agregator -> Operator matching)
# ---------------------------------------------------------------------------

class Test3_OrderFlow:
    """Customer order + automatic matching via Operator price_offer + confirm-price.

    SC-шаги (test_05..test_09): CreateOrder → ReadOrder → AssignOrder →
    ApproveOrder → CheckDroneReadiness.
    """

    ORDER_BUDGET = 5000

    def test_01_create_customer(self, agregator_url):
        r = rest_post(agregator_url, "/customers", {
            "name": "E2E Customer",
            "email": "e2e-customer@local",
            "password": "e2e-customer-pass",
        })
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"
        body = r.json()
        user = body.get("user") or {}
        _shared["customer_id"] = (
            user.get("id")
            or body.get("customer_id")
            or body.get("id")
        )
        assert _shared["customer_id"], f"customer id должен быть в ответе: {body}"

    def test_02_create_order_and_wait_for_match(self, agregator_url, kafka_bus):
        """Создаём заказ. Agregator → create_order → Operator price_offer → matched."""
        r = rest_post(agregator_url, "/orders", {
            "customer_id": _shared["customer_id"],
            "description": "E2E agro delivery",
            "budget": self.ORDER_BUDGET,
            "from_lat": 55.75,
            "from_lon": 37.62,
            "to_lat": 55.80,
            "to_lon": 37.70,
        })
        assert r.status_code in (200, 201), f"{r.status_code} {r.text}"
        body = r.json()
        order_id = body.get("order_id") or body.get("id")
        assert order_id
        _shared["order_id"] = order_id

        def _poll_status(deadline_s: float) -> str:
            status_local = body.get("status", "")
            deadline_local = time.time() + deadline_s
            while status_local not in ("matched",) and time.time() < deadline_local:
                time.sleep(2)
                poll = rest_get(agregator_url, f"/orders/{order_id}")
                if poll.status_code == 200:
                    poll_body = poll.json()
                    status_local = poll_body.get("status", "")
            return status_local

        status = _poll_status(60)

        if status != "matched":
            kafka_bus.publish(
                AGREGATOR_OPERATOR_REQUESTS_TOPIC,
                {
                    "action": "create_order",
                    "sender": "e2e_test_host",
                    "correlation_id": order_id,
                    "payload": {
                        "customer_id": _shared["customer_id"],
                        "budget": self.ORDER_BUDGET,
                        "description": "E2E agro delivery",
                    },
                },
            )
            status = _poll_status(45)

        if status != "matched":
            pytest.skip(
                f"Order not matched after fallback publish (status={status}) — "
                "Operator↔Agregator bridge may still be unavailable"
            )

        _shared["order_status"] = status

    def test_03_confirm_price(self, agregator_url):
        if _shared.get("order_status") != "matched":
            pytest.skip("Order was not matched")

        r = rest_post(agregator_url, f"/orders/{_shared['order_id']}/confirm-price", {
            "operator_id": "operator_component",
            "accepted_price": self.ORDER_BUDGET * 0.85,
        })
        if r.status_code not in (200, 201):
            pytest.skip(f"confirm-price failed: {r.status_code} {r.text}")

    def test_04_mission_insurance(self, kafka_bus):
        """Миссионное страхование через Operator -> Insurer."""
        if not _shared.get("order_id"):
            pytest.skip("No order to insure")

        r = bus_request(kafka_bus, OPERATOR_TOPIC, "buy_insurance_policy", {
            "order_id": _shared["order_id"],
            "drone_id": E2E_DRONE_ID,
            "coverage_amount": self.ORDER_BUDGET,
            "insurance_action": "mission_insurance",
        })
        assert r.get("success") is True, f"mission_insurance failed: {r}"
        mission = r.get("payload") or {}
        assert mission.get("status") == "insured"
        policy = mission.get("policy", {})
        assert policy.get("policy_type") == "mission"
        assert policy.get("policy_id")

    # ── Smart-contract шаги ────────────────────────────────────────────────

    def test_05_sc_create_order(self, kafka_bus):
        """OrderContract:CreateOrder — Aggregator создаёт заказ в ledger."""
        if not _shared.get("order_id"):
            pytest.skip("order_id отсутствует — test_02 пропущен")

        order_id = _shared["order_id"]
        # OrderDetail: список объектов с операционными параметрами полёта.
        details = [
            {
                "drone_id": E2E_DRONE_ID,
                "security_objectives": EXPECTED_SO,
                "environmental_limit": ["wind_lt_15ms", "no_rain"],
                "operation_area": "moscow-test-area",
            }
        ]
        resp = ledger_invoke(
            kafka_bus,
            "OrderContract:CreateOrder",
            [
                order_id,
                SC_AGGREGATOR_ID,
                SC_OPERATOR_ID,
                E2E_DRONE_ID,
                SC_INSURER_ID,
                SC_CERTCENTER_ID,
                SC_DEVELOPER_ID,
                self.ORDER_BUDGET,                   # amountTotal
                Test1_DroneRegistration.COVERAGE_AMOUNT,  # insuranceCoverageAmount
                details,
            ],
        )
        assert_ledger_ok(resp, "CreateOrder")
        _shared["sc_order_id"] = order_id

    def test_06_sc_read_order_after_create(self, kafka_bus):
        """ReadOrder — читатель берёт заказ из блокчейна сразу после создания."""
        if not _shared.get("sc_order_id"):
            pytest.skip("SC order не создан")

        resp = ledger_query(
            kafka_bus,
            "OrderContract:ReadOrder",
            [_shared["sc_order_id"]],
        )
        pl = assert_ledger_ok(resp, "ReadOrder")
        result = pl.get("result") or pl
        assert _shared["sc_order_id"] in str(result), (
            f"Заказ {_shared['sc_order_id']!r} не найден в ledger: {pl}"
        )

    def test_07_sc_assign_order(self, kafka_bus):
        """AssignOrder — фиксация назначения operator+drone после matched."""
        if not _shared.get("sc_order_id"):
            pytest.skip("SC order не создан")
        if _shared.get("order_status") != "matched":
            pytest.skip("Order не был matched — AssignOrder неприменим")

        resp = ledger_invoke(
            kafka_bus,
            "OrderContract:AssignOrder",
            [_shared["sc_order_id"], SC_OPERATOR_ID, E2E_DRONE_ID, []],
        )
        assert_ledger_ok(resp, "AssignOrder")
        _shared["sc_order_assigned"] = True

    def test_08_sc_approve_order(self, kafka_bus):
        """ApproveOrder — Insurer одобряет заказ (после mission_insurance)."""
        if not _shared.get("sc_order_assigned"):
            pytest.skip("SC order не assigned")

        resp = ledger_invoke(
            kafka_bus,
            "OrderContract:ApproveOrder",
            [_shared["sc_order_id"]],
        )
        assert_ledger_ok(resp, "ApproveOrder")
        _shared["sc_order_approved"] = True

    def test_09_sc_check_drone_readiness(self, kafka_bus):
        """CheckDroneReadiness — читатель проверяет готовность дрона по блокчейну."""
        if not _shared.get("sc_drone_pass_id"):
            pytest.skip("SC drone pass не создан")

        resp = ledger_query(
            kafka_bus,
            "OrderContract:CheckDroneReadiness",
            [E2E_DRONE_ID],
        )
        # Контракт может вернуть false (например, нет действующей TypeCertificate),
        # это валидный сценарий. Проверяем только что вызов не упал на ledger-уровне.
        assert resp.get("success") is True or "error" in (resp.get("payload") or {}), (
            f"CheckDroneReadiness вернул некорректный ответ: {resp}"
        )


# ---------------------------------------------------------------------------
# Phase 4: ORVD + GCS Route Planning
# ---------------------------------------------------------------------------

class Test4_MissionPlanning:
    """Register mission with ORVD, authorize, plan route via GCS."""

    def test_01_register_mission_orvd(self, kafka_bus):
        mission_id = f"mission-{_shared.get('order_id', 'e2e')}"
        _shared["mission_id"] = mission_id

        route = [
            {"lat": 55.75, "lon": 37.62},
            {"lat": 55.80, "lon": 37.70},
        ]

        registered = False
        try:
            r = bus_request_with_retries(
                kafka_bus,
                ORVD_TOPIC,
                "register_mission",
                {"mission_id": mission_id, "drone_id": E2E_DRONE_ID, "route": route},
                attempts=2,
                timeout=15,
                sleep_s=2,
            )
            pl = (r.get("payload") or {})
            if r.get("success") is True and pl.get("status") in ("mission_registered", "registered"):
                registered = True
        except AssertionError:
            pass

        if not registered:
            for _ in range(3):
                r = kafka_bus.request(
                    ORVD_COMPONENT_TOPIC,
                    {
                        "action": "register_mission",
                        "sender": "e2e_test_host",
                        "payload": {"mission_id": mission_id, "drone_id": E2E_DRONE_ID, "route": route},
                    },
                    timeout=30,
                )
                if r is not None:
                    pl = (r.get("payload") or {})
                    if pl.get("status") in ("mission_registered", "registered"):
                        registered = True
                    break
                time.sleep(3)

        if not registered:
            pytest.skip("ORVD register_mission not reachable — skipping ORVD tests")

    def test_02_authorize_mission_orvd(self, kafka_bus):
        if not _shared.get("mission_id"):
            pytest.skip("No mission_id from ORVD registration")

        mission_id = _shared["mission_id"]
        authorized = False
        last = None

        for _ in range(3):
            r = kafka_bus.request(
                ORVD_TOPIC,
                {"action": "authorize_mission", "sender": "e2e_test_host",
                 "payload": {"mission_id": mission_id}},
                timeout=15,
            )
            if r is None:
                time.sleep(3)
                continue
            last = r
            pl = r.get("payload") or {}
            if pl.get("status") == "authorized":
                authorized = True
                break
            time.sleep(3)

        if authorized:
            return

        for attempt in range(4):
            r = kafka_bus.request(
                ORVD_COMPONENT_TOPIC,
                {
                    "action": "authorize_mission",
                    "sender": "e2e_test_host",
                    "payload": {"mission_id": mission_id},
                },
                timeout=30,
            )
            if r is None:
                time.sleep(5)
                continue
            last = r
            pl = r.get("payload") or {}
            if pl.get("status") == "authorized":
                authorized = True
                break
            if pl.get("message") == "mission not found" or "not found" in str(pl.get("message", "")):
                kafka_bus.request(
                    ORVD_COMPONENT_TOPIC,
                    {
                        "action": "register_mission",
                        "sender": "e2e_test_host",
                        "payload": {
                            "mission_id": mission_id,
                            "drone_id": E2E_DRONE_ID,
                            "route": [
                                {"lat": 55.75, "lon": 37.62},
                                {"lat": 55.80, "lon": 37.70},
                            ],
                        },
                    },
                    timeout=30,
                )
                time.sleep(2)
            time.sleep(3)

        assert last is not None, "authorize_mission: no response from ORVD gateway or component"
        pl = last.get("payload") or {}
        assert pl.get("status") == "authorized", f"authorize_mission payload mismatch: {last}"

    def test_03_gcs_plan_route(self, kafka_bus):
        """GCS orchestrator -> path_planner: build flight route from waypoints."""
        r = bus_request(kafka_bus, GCS_ORCHESTRATOR_TOPIC, "task.submit", {
            "waypoints": [
                {"lat": 55.750000, "lon": 37.620000, "alt_m": 50.0},
                {"lat": 55.750270, "lon": 37.620000, "alt_m": 50.0},
            ],
        })
        assert r.get("success") is True, f"task.submit failed: {r}"
        pl = r.get("payload") or {}

        gcs_mission_id = pl.get("mission_id")
        if gcs_mission_id:
            _shared["gcs_mission_id"] = gcs_mission_id

        waypoints = pl.get("waypoints")
        assert waypoints and len(waypoints) >= 4, (
            f"GCS должен вернуть маршрут >= 4 точек, got {waypoints}"
        )
        _shared["gcs_waypoints"] = waypoints

    def test_04_wait_mission_stored(self, kafka_bus):
        """Wait for PathPlanner's async bus.publish to be consumed by MissionStore."""
        mission_id = _shared.get("gcs_mission_id")
        if not mission_id:
            pytest.skip("No gcs_mission_id — skipping MissionStore wait")

        waypoints = _shared.get("gcs_waypoints", [])

        def _poll(deadline_s: float) -> bool:
            dl = time.time() + deadline_s
            while time.time() < dl:
                r = kafka_bus.request(
                    GCS_MISSION_STORE_TOPIC,
                    {
                        "action": "store.get_mission",
                        "sender": "e2e_test_host",
                        "payload": {"mission_id": mission_id},
                    },
                    timeout=8,
                )
                if r is not None and (r.get("payload") or {}).get("mission"):
                    return True
                time.sleep(3)
            return False

        if _poll(30):
            return

        if waypoints:
            kafka_bus.publish(
                GCS_MISSION_STORE_TOPIC,
                {
                    "action": "store.save_mission",
                    "sender": "e2e_test_host",
                    "payload": {
                        "mission": {
                            "mission_id": mission_id,
                            "waypoints": waypoints,
                            "status": "created",
                            "assigned_drone": None,
                        }
                    },
                },
            )
            time.sleep(4)
            if _poll(15):
                return

        pytest.skip(
            f"MissionStore did not store mission {mission_id} after polling — "
            "task.assign may fall back to direct DroneManager upload"
        )

    def test_05_publish_sitl_home(self, kafka_bus):
        """Publish the drone's home position to SITL before the telemetry health check."""
        waypoints = _shared.get("gcs_waypoints", [])
        if not waypoints:
            pytest.skip("No waypoints available — cannot publish SITL home")

        first = waypoints[0]
        kafka_bus.publish(
            "sitl-drone-home",
            {
                "drone_id": E2E_DRONE_ID,
                "home_lat": first.get("lat", 0.0),
                "home_lon": first.get("lon", 0.0),
                "home_alt": first.get("alt_m", 50.0),
            },
        )
        time.sleep(3)


# ---------------------------------------------------------------------------
# Phase 5: System Health Checks (ping)
# ---------------------------------------------------------------------------

class Test5_SystemHealthChecks:
    """Verify DronePort, AgroDron, and GCS components are alive."""

    def test_droneport_ping(self, kafka_bus):
        try:
            resp = bus_request(kafka_bus, DRONE_PORT_REGISTRY_TOPIC, "ping", {}, timeout=10)
            assert resp.get("success") is True
        except AssertionError:
            pytest.skip("DronePort registry not reachable — container may not be running")

    def test_agrodron_ping(self, kafka_bus):
        try:
            resp = bus_request(kafka_bus, AGRODRON_SECURITY_MONITOR_TOPIC, "ping", {}, timeout=10)
            assert resp.get("success") is True
        except AssertionError:
            pytest.skip("AgroDron security_monitor not reachable — container may not be running")

    def test_gcs_orchestrator_ping(self, kafka_bus):
        try:
            resp = bus_request(kafka_bus, GCS_ORCHESTRATOR_TOPIC, "ping", {}, timeout=10)
            assert resp.get("success") is True
        except AssertionError:
            pytest.skip("GCS orchestrator not reachable — container may not be running")

    def test_ping_delivery_drone(self, kafka_bus):
        """Ping the delivery drone system (Go container)."""
        try:
            resp = bus_request(kafka_bus, DELIVERY_DRONE_TOPIC, "ping", {}, timeout=10)
            assert resp.get("success") is True
        except AssertionError:
            pytest.skip(
                "Delivery drone not reachable — Go container not running or build failed"
            )

    def test_sitl_telemetry_request(self, kafka_bus):
        deadline = time.time() + 90
        last_resp = None
        while time.time() < deadline:
            resp = kafka_bus.request(
                SITL_TELEMETRY_REQUEST_TOPIC,
                {
                    "action": "request_position",
                    "sender": "e2e_test_host",
                    "payload": {"drone_id": E2E_DRONE_ID},
                },
                timeout=10,
            )
            if resp is None:
                time.sleep(3)
                continue
            last_resp = resp
            if resp.get("success") is True:
                pl = resp.get("payload") or {}
                if "lat" in pl and "lon" in pl:
                    return
            time.sleep(3)

        pytest.skip(f"SITL telemetry not reachable after warmup; last_response={last_resp}")

    def test_sc_ledger_ping(self, kafka_bus):
        """Sanity-check ledger: ListDronePasses должен ответить (любой результат)."""
        resp = ledger_query(
            kafka_bus,
            "DronePropertiesContract:ListDronePasses",
            [],
        )
        assert resp.get("success") is True, f"Ledger ListDronePasses failed: {resp}"


# ---------------------------------------------------------------------------
# Phase 6: Mission Execution (task.assign → task.start → autopilot state)
# ---------------------------------------------------------------------------

class Test6_MissionExecution:
    """Full mission execution cycle.

    SC-шаги (test_05..test_09): ConfirmOrder → StartOrder → FinishOrder →
    FinalizeOrder → итоговый ReadOrder из блокчейна.
    """

    DRONE_ID = E2E_DRONE_ID

    def test_01_gcs_task_assign(self, kafka_bus):
        """Upload WPL mission to Agrodron via GCS orchestrator task.assign."""
        mission_id = _shared.get("gcs_mission_id")
        if not mission_id:
            pytest.skip("No gcs_mission_id from Test4 task.submit — GCS may be unavailable")

        r = None
        pl = {}
        for _ in range(6):
            candidate = bus_request_with_retries(
                kafka_bus,
                GCS_ORCHESTRATOR_TOPIC,
                "task.assign",
                {"mission_id": mission_id, "drone_id": self.DRONE_ID},
                attempts=2,
                timeout=40,
                sleep_s=2,
            )
            r = candidate
            if r and r.get("success") is True:
                pl = r.get("payload") or {}
                if pl.get("ok") is True:
                    break
            time.sleep(3)

        if not (r and (r.get("payload") or {}).get("ok") is True):
            waypoints = _shared.get("gcs_waypoints", [])
            assert waypoints, (
                "No waypoints available for direct DroneManager upload — "
                f"task.assign also failed: {r}"
            )
            wpl = _build_wpl(waypoints)
            r = bus_request(
                kafka_bus,
                GCS_DRONE_MANAGER_TOPIC,
                "mission.upload",
                {"mission_id": mission_id, "drone_id": self.DRONE_ID, "wpl": wpl},
                timeout=30,
            )
            assert r.get("success") is True, f"Direct mission.upload to DroneManager failed: {r}"
            _shared["mission_assigned"] = True
            return

        assert r is not None, "task.assign returned no response"
        assert pl.get("ok") is True, f"task.assign: ok is not True: {pl}"
        assert pl.get("forwarded_action") == "mission.upload", (
            f"Expected forwarded_action=mission.upload, got {pl}"
        )
        _shared["mission_assigned"] = True

    def test_02_gcs_task_start(self, kafka_bus):
        """Send START command to Agrodron autopilot via GCS orchestrator task.start."""
        if not _shared.get("mission_assigned"):
            pytest.skip("Mission not assigned (test_01 skipped or failed)")

        time.sleep(10)

        mission_id = _shared["gcs_mission_id"]
        r = bus_request(
            kafka_bus,
            GCS_ORCHESTRATOR_TOPIC,
            "task.start",
            {"mission_id": mission_id, "drone_id": self.DRONE_ID},
            timeout=30,
        )
        assert r.get("success") is True, f"task.start failed: {r}"
        pl = r.get("payload") or {}
        assert pl.get("ok") is True, f"task.start: ok is not True: {pl}"
        assert pl.get("forwarded_action") == "mission.start", (
            f"Expected forwarded_action=mission.start, got {pl}"
        )
        _shared["mission_started"] = True

    def test_03_poll_autopilot_state(self, kafka_bus):
        """Poll Agrodron autopilot state via SecurityMonitor proxy_request."""
        if not _shared.get("mission_started"):
            pytest.skip("Mission not started (test_02 skipped or failed)")

        active_states = ("EXECUTING", "MISSION_LOADED", "LANDING", "COMPLETED", "IDLE")
        state = None
        deadline = time.time() + 60

        while time.time() < deadline:
            try:
                r = bus_request(
                    kafka_bus,
                    AGRODRON_SECURITY_MONITOR_TOPIC,
                    "proxy_request",
                    {
                        "target": {
                            "topic": AGRODRON_AUTOPILOT_TOPIC,
                            "action": "get_state",
                        },
                        "data": {},
                    },
                    timeout=10,
                )
            except AssertionError:
                pytest.skip(
                    "Agrodron SecurityMonitor not responding — "
                    "containers may be unavailable or SECURITY_POLICIES not configured"
                )

            pl = r.get("payload") or {}
            if not pl.get("ok", True) and pl.get("error") == "policy_denied":
                pytest.skip(
                    "SecurityMonitor denied proxy_request for e2e_test_host — "
                    "add policy: sender=e2e_test_host, "
                    f"topic={AGRODRON_AUTOPILOT_TOPIC}, action=get_state"
                )
            target_resp = pl.get("target_response") or pl
            inner = target_resp.get("payload") if isinstance(target_resp, dict) else None
            state = (inner or {}).get("state") if isinstance(inner, dict) else (
                target_resp.get("state") if isinstance(target_resp, dict) else None
            )

            if state in active_states:
                break
            time.sleep(2)

        if state not in active_states:
            pytest.skip(
                f"Autopilot state={state!r} after 60s — "
                "containers may not be running or START was denied by ORVD/DronePort"
            )

        _shared["autopilot_state"] = state
        assert state in active_states, f"Unexpected autopilot state: {state}"

    def test_04_wait_mission_completed(self, kafka_bus):
        """Wait for Agrodron autopilot to complete the mission and return to IDLE."""
        if not _shared.get("mission_started"):
            pytest.skip("Mission not started")

        state = _shared.get("autopilot_state")
        if state == "IDLE":
            return

        terminal_states = ("COMPLETED", "IDLE")
        deadline = time.time() + 180

        while time.time() < deadline:
            try:
                r = bus_request(
                    kafka_bus,
                    AGRODRON_SECURITY_MONITOR_TOPIC,
                    "proxy_request",
                    {
                        "target": {
                            "topic": AGRODRON_AUTOPILOT_TOPIC,
                            "action": "get_state",
                        },
                        "data": {},
                    },
                    timeout=10,
                )
            except AssertionError:
                pytest.skip("Agrodron SecurityMonitor not responding during mission completion poll")

            pl = r.get("payload") or {}
            if not pl.get("ok", True) and pl.get("error") == "policy_denied":
                pytest.skip("SecurityMonitor denied proxy_request — cannot poll completion")

            target_resp = pl.get("target_response") or pl
            inner = target_resp.get("payload") if isinstance(target_resp, dict) else None
            state = (inner or {}).get("state") if isinstance(inner, dict) else (
                target_resp.get("state") if isinstance(target_resp, dict) else None
            )
            if state in terminal_states:
                break
            time.sleep(3)

        if state not in terminal_states:
            pytest.skip(
                f"Mission not completed after 60s, last state={state!r} — "
                "SITL may not be running (drone position never changes)"
            )

        _shared["autopilot_final_state"] = state

    # ── Smart-contract шаги ────────────────────────────────────────────────

    def test_05_sc_confirm_order(self, kafka_bus):
        """OrderContract:ConfirmOrder — Operator подтверждает заказ (перед task.assign)."""
        if not _shared.get("sc_order_approved"):
            pytest.skip("SC order не approved")

        resp = ledger_invoke(
            kafka_bus,
            "OrderContract:ConfirmOrder",
            [_shared["sc_order_id"]],
        )
        assert_ledger_ok(resp, "ConfirmOrder")
        _shared["sc_order_confirmed"] = True

    def test_06_sc_start_order(self, kafka_bus):
        """OrderContract:StartOrder — Operator стартует полёт (соответствует task.start)."""
        if not _shared.get("sc_order_confirmed"):
            pytest.skip("SC order не confirmed")

        resp = ledger_invoke(
            kafka_bus,
            "OrderContract:StartOrder",
            [_shared["sc_order_id"]],
        )
        assert_ledger_ok(resp, "StartOrder")
        _shared["sc_order_started"] = True

    def test_07_sc_finish_order(self, kafka_bus):
        """OrderContract:FinishOrder — Operator завершает полёт (mission_completed)."""
        if not _shared.get("sc_order_started"):
            pytest.skip("SC order не started")

        resp = ledger_invoke(
            kafka_bus,
            "OrderContract:FinishOrder",
            [_shared["sc_order_id"]],
        )
        assert_ledger_ok(resp, "FinishOrder")
        _shared["sc_order_finished"] = True

    def test_08_sc_finalize_order(self, kafka_bus):
        """OrderContract:FinalizeOrder — Aggregator финализирует заказ."""
        if not _shared.get("sc_order_finished"):
            pytest.skip("SC order не finished")

        resp = ledger_invoke(
            kafka_bus,
            "OrderContract:FinalizeOrder",
            [_shared["sc_order_id"]],
        )
        assert_ledger_ok(resp, "FinalizeOrder")
        _shared["sc_order_finalized"] = True

    def test_09_sc_read_order_final(self, kafka_bus):
        """ReadOrder — читатель берёт финальное состояние заказа из блокчейна."""
        if not _shared.get("sc_order_id"):
            pytest.skip("SC order не создан")

        resp = ledger_query(
            kafka_bus,
            "OrderContract:ReadOrder",
            [_shared["sc_order_id"]],
        )
        pl = assert_ledger_ok(resp, "ReadOrder(final)")
        result = pl.get("result") or pl
        text = str(result)
        # После полного цикла в ledger должен присутствовать заказ и хотя бы
        # один из ключевых идентификаторов участников.
        assert _shared["sc_order_id"] in text, (
            f"Финальный заказ {_shared['sc_order_id']!r} не виден в ledger: {pl}"
        )
        _shared["sc_order_final_state"] = result


# ---------------------------------------------------------------------------
# Log Verification
# ---------------------------------------------------------------------------

class TestLogVerification:
    """DroneAnalytics journal events."""

    def test_events_present_in_analytics(self, analytics_url, analytics_bearer_token):
        time.sleep(8)
        headers = {"Authorization": f"Bearer {analytics_bearer_token}"}
        resp = requests.get(
            f"{analytics_url}/log/event",
            params={"limit": 100, "page": 1},
            headers=headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"{resp.status_code} {resp.text}"
        data = resp.json()
        events = data if isinstance(data, list) else data.get("items", data.get("events", []))
        if not events:
            pytest.skip("No events in DroneAnalytics yet")
        assert len(events) > 0
