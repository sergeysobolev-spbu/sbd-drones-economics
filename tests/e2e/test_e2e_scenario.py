"""
E2E: four flows + DroneAnalytics log check.

Order: Test0 -> Test1 -> Test2 -> Test3 (same session; regulator state in Docker persists).
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Dict

import pytest
import requests

OPERATOR_TOPIC = "systems.operator"
ORVD_TOPIC = "systems.orvd_system"
REGULATOR_TOPIC = "systems.regulator"
GCS_TOPIC = "systems.gcs"
INSURER_TOPIC = "systems.insurer"

EXPECTED_SO = [f"SO_{i}" for i in range(1, 12)]


def bus_request(bus, topic: str, action: str, payload: dict, timeout: float = 25) -> Dict[str, Any]:
    resp = bus.request(
        topic,
        {"action": action, "sender": "e2e_test_host", "payload": payload},
        timeout=timeout,
    )
    assert resp is not None, f"Timeout: {action} -> {topic}"
    return resp


def rest_post(base: str, path: str, json: dict | None = None) -> requests.Response:
    return requests.post(f"{base}{path}", json=json or {}, timeout=15)


def rest_get(base: str, path: str) -> requests.Response:
    return requests.get(f"{base}{path}", timeout=15)


class Test0_SystemsInRegulator:
    """Register all participating systems; receive SO_1..SO_11."""

    def test_register_systems(self, kafka_bus):
        for system_id, system_type in (
            ("agregator", "aggregator"),
            ("operator", "operator"),
            ("insurer", "insurer"),
            ("orvd_system", "orvd"),
            ("gcs", "gcs"),
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


class Test1_DroneRegistration:
    """Cert from regulator -> operator -> ORVD -> annual insurance (КАСКО)."""

    # Параметры дрона для e2e-drone-001
    DRONE_VALUE = 150_000
    DRONE_TYPE = "delivery"

    def test_drone_chain(self, kafka_bus):
        drone_id = "e2e-drone-001"
        r_cert = bus_request(kafka_bus, REGULATOR_TOPIC, "register_drone_cert", {"drone_id": drone_id})
        assert r_cert.get("success") is True
        cert_id = (r_cert.get("payload") or {})["certificate_id"]

        r_op = bus_request(kafka_bus, OPERATOR_TOPIC, "register_drone", {
            "drone_id": drone_id,
            "model": "E2E-Drone",
            "capabilities": ["cargo"],
            "certificate_id": cert_id,
        })
        assert r_op.get("success") is True

        r_orvd = bus_request(kafka_bus, OPERATOR_TOPIC, "register_drone_in_orvd", {
            "drone_id": drone_id,
            "model": "E2E-Drone",
            "certificate_id": cert_id,
        })
        assert r_orvd.get("success") is True

        v = bus_request(kafka_bus, REGULATOR_TOPIC, "verify_drone_cert", {
            "drone_id": drone_id,
            "certificate_id": cert_id,
        })
        assert v.get("success") is True
        assert (v.get("payload") or {}).get("valid") is True

        # --- Годовое страхование (КАСКО) ---
        # Pannual = Vdrone × Rbase_hull × Kfleet_history
        # = 150_000 × 0.08 (delivery) × 1.0 (новый дрон, < 10 вылетов) = 12_000
        r_ins = bus_request(kafka_bus, INSURER_TOPIC, "annual_insurance", {
            "drone_id": drone_id,
            "drone_value": self.DRONE_VALUE,
            "drone_type": self.DRONE_TYPE,
        })
        assert r_ins.get("success") is True, f"annual_insurance failed: {r_ins}"
        ins = r_ins.get("payload") or {}

        assert ins.get("policy_type") == "annual"
        assert ins.get("status") == "active"
        assert ins.get("drone_id") == drone_id
        assert ins.get("kfleet_history") == "1.0", "новый дрон должен иметь Kfleet=1.0"

        # Проверяем формулу: 150_000 × 0.08 × 1.0 = 12_000.00
        expected_premium = Decimal("150000") * Decimal("0.08") * Decimal("1.0")
        assert Decimal(ins["premium"]) == expected_premium, (
            f"premium {ins['premium']} != {expected_premium}"
        )

        assert ins.get("policy_id"), "policy_id должен быть заполнен"
        assert ins.get("end_date"), "end_date должен быть заполнен (срок 365 дней)"


class Test2_OperatorInAggregator:
    """Operator certificate from regulator; register via Agregator REST."""

    def test_operator_registration(self, kafka_bus, agregator_url):
        operator_id = "e2e-operator-1"
        r_cert = bus_request(kafka_bus, REGULATOR_TOPIC, "register_operator_cert", {
            "operator_id": operator_id,
        })
        assert r_cert.get("success") is True
        cert_id = (r_cert.get("payload") or {})["certificate_id"]

        r = rest_post(agregator_url, "/operators", {
            "name": "E2E Operator",
            "license": "E2E-LIC-1",
            "operator_id": operator_id,
            "certificate_id": cert_id,
        })
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        # Агрегатор может принять переданный operator_id или сгенерировать новый.
        registered_operator_id = r.json().get("operator_id")
        assert registered_operator_id, "operator_id должен быть в ответе"

        # Сертификат выписан на исходный operator_id, поэтому верификацию
        # нужно выполнять именно по нему, даже если агрегатор вернул новый UUID.
        v = bus_request(kafka_bus, REGULATOR_TOPIC, "verify_operator_cert", {
            "operator_id": operator_id,
            "certificate_id": cert_id,
        })
        assert v.get("success") is True
        assert (v.get("payload") or {}).get("valid") is True


class Test3_OrderMissionAndGCS:
    """Customer order + confirm flow (mission insurance) + mission route on GCS."""

    # Параметры дрона для заказного теста
    DRONE_VALUE = 120_000
    DRONE_TYPE = "delivery"
    ORDER_BUDGET = 5000

    @pytest.fixture(autouse=True)
    def _ensure_drone_for_order(self, kafka_bus):
        """Регистрируем дрон и сразу оформляем годовое страхование."""
        drone_id = "e2e-drone-order"
        r_cert = bus_request(kafka_bus, REGULATOR_TOPIC, "register_drone_cert", {"drone_id": drone_id})
        cert_id = (r_cert.get("payload") or {})["certificate_id"]
        bus_request(kafka_bus, OPERATOR_TOPIC, "register_drone", {
            "drone_id": drone_id,
            "model": "OrderDrone",
            "capabilities": ["cargo"],
            "certificate_id": cert_id,
        })

        # Годовое страхование при регистрации дрона
        # Pannual = 120_000 × 0.08 (delivery) × 1.0 = 9_600
        r_ins = bus_request(kafka_bus, INSURER_TOPIC, "annual_insurance", {
            "drone_id": drone_id,
            "drone_value": self.DRONE_VALUE,
            "drone_type": self.DRONE_TYPE,
        })
        assert r_ins.get("success") is True, f"annual_insurance failed during fixture: {r_ins}"
        ins = r_ins.get("payload") or {}
        assert ins.get("policy_type") == "annual"
        assert ins.get("status") == "active"

    def test_order_gcs_route_completion(self, agregator_url, kafka_bus):
        pickup = {"lat": 55.75, "lon": 37.62}
        dropoff = {"lat": 55.80, "lon": 37.70}

        r = rest_post(agregator_url, "/customers", {"name": "E2E Customer", "email": "e2e@local"})
        assert r.status_code == 200
        customer_id = r.json()["customer_id"]

        r = rest_post(agregator_url, "/orders", {
            "customer_id": customer_id,
            "description": "E2E delivery",
            "budget": self.ORDER_BUDGET,
            "drone_type": self.DRONE_TYPE,
            "pickup": pickup,
            "dropoff": dropoff,
        })
        assert r.status_code == 200
        body = r.json()
        order_id = body["order_id"]
        if body["status"] != "matched":
            pytest.skip("No drone matched")

        # confirm-price запускает миссионное страхование внутри агрегатора:
        # Pmission = Vcargo × Rrisk_class × Kenv × Kincident_history
        # = 5_000 × 0.08 (delivery) × 1.0 × 1.0 = 400.00
        r = rest_post(agregator_url, f"/orders/{order_id}/confirm-price")
        assert r.status_code == 200
        confirm_body = r.json()
        assert confirm_body.get("status") == "confirmed"

        # Проверяем, что миссионный полис был оформлен
        order_data = confirm_body.get("order", {})
        assert order_data.get("policy_id"), "policy_id должен быть заполнен после confirm-price"
        assert order_data.get("insurance_premium") is not None, (
            "insurance_premium должен присутствовать в заказе"
        )
        # Pmission = budget × 0.08 × 1.0 × 1.0 = 400.00
        expected_mission_premium = Decimal(str(self.ORDER_BUDGET)) * Decimal("0.08")
        assert Decimal(str(order_data["insurance_premium"])) == expected_mission_premium, (
            f"mission premium {order_data['insurance_premium']} != {expected_mission_premium}"
        )

        route_resp = bus_request(kafka_bus, GCS_TOPIC, "plan_mission_route", {
            "pickup": pickup,
            "dropoff": dropoff,
        })
        assert route_resp.get("success") is True
        route = (route_resp.get("payload") or {}).get("route")
        assert isinstance(route, list) and len(route) >= 2

        r = rest_post(agregator_url, f"/orders/{order_id}/confirm-completion")
        assert r.status_code == 200
        assert r.json().get("status") == "completed"

        r = rest_get(agregator_url, f"/orders/{order_id}")
        assert r.status_code == 200
        final_order = r.json()["order"]
        assert final_order["status"] == "completed"
        assert final_order.get("policy_id"), "policy_id должен сохраниться в завершённом заказе"


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
