"""
E2E-Fabric: полный бизнес-сценарий дрона с записью в Hyperledger Fabric.

Объединяет основной e2e-сценарий (Kafka bus + REST) с фиксацией каждого
шага в распределённом леджере через систему dummy_fabric.

Требования:
  - Запущены основные системы (docker/docker-compose.yml)
  - Запущена dummy_fabric (systems/dummy_fabric/docker-compose.yml
    --profile fabric --profile kafka)

Шаги:
  01. Регистрация систем в Регуляторе
  02. Сертификация прошивки (Fabric: CertCenter)
  03. Выпуск типового сертификата (Fabric: CertCenter)
  04. Создание DronePass (Fabric: CertCenter)
  05. Регистрация дрона (Регулятор + Оператор) + годовое страхование
  06. Запись страхования в Fabric (Insurer)
  07. Регистрация оператора и создание заказа (REST Агрегатор)
  08–16. Полный жизненный цикл заказа на Fabric (create → assign → approve
         → confirm → flight_permission → start → finish → finalize)
  17–18. Верификация финального состояния в леджере
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict

import pytest
import requests

# ── Топики ────────────────────────────────────────────────────────────────────

OPERATOR_TOPIC = "systems.operator"
ORVD_TOPIC = "systems.orvd_system"
REGULATOR_TOPIC = "systems.regulator"
GCS_TOPIC = "systems.gcs"
INSURER_TOPIC = "systems.insurer"
FABRIC_TOPIC = "systems.dummy_fabric"

EXPECTED_SO = [f"SO_{i}" for i in range(1, 12)]

# ── Fabric-proxy URLs (health check) ─────────────────────────────────────────

PROXY_URLS = {
    "aggregator": os.environ.get("FABRIC_PROXY_AGGREGATOR", "http://localhost:3001"),
    "certcenter": os.environ.get("FABRIC_PROXY_CERTCENTER", "http://localhost:3002"),
    "insurer": os.environ.get("FABRIC_PROXY_INSURER", "http://localhost:3003"),
    "operator": os.environ.get("FABRIC_PROXY_OPERATOR", "http://localhost:3004"),
    "orvd": os.environ.get("FABRIC_PROXY_ORVD", "http://localhost:3005"),
}
MAX_PROXY_WAIT = int(os.environ.get("FABRIC_PROXY_WAIT", "90"))

# ── Параметры дрона ──────────────────────────────────────────────────────────

DRONE_ID = "e2e-fabric-drone-001"
DRONE_VALUE = 150_000
DRONE_TYPE = "delivery"
ORDER_BUDGET = 5000

# ── Общее состояние прогона ───────────────────────────────────────────────────

_state: Dict[str, Any] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def bus_request(bus, topic: str, action: str, payload: dict, timeout: float = 30) -> Dict[str, Any]:
    resp = bus.request(
        topic,
        {"action": action, "sender": "e2e_fabric_test", "payload": payload},
        timeout=timeout,
    )
    assert resp is not None, f"Timeout: {action} -> {topic}"
    return resp


def rest_post(base: str, path: str, json: dict | None = None) -> requests.Response:
    return requests.post(f"{base}{path}", json=json or {}, timeout=15)


def rest_get(base: str, path: str) -> requests.Response:
    return requests.get(f"{base}{path}", timeout=15)


def _proxy_healthy(url: str) -> str:
    try:
        r = requests.get(f"{url}/health", timeout=5)
        return "" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as exc:
        return str(exc)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def fabric_ready():
    """Ожидание готовности всех fabric-proxy; skip если недоступны."""
    deadline = time.time() + MAX_PROXY_WAIT
    while True:
        errors = {}
        for name, url in PROXY_URLS.items():
            err = _proxy_healthy(url)
            if err:
                errors[name] = err
        if not errors:
            return True
        if time.time() >= deadline:
            detail = "; ".join(f"{n}: {errors[n]}" for n in errors)
            pytest.skip(f"Fabric proxies not ready after {MAX_PROXY_WAIT}s — {detail}")
        time.sleep(5)


@pytest.fixture(scope="module")
def run_ids():
    """Уникальные идентификаторы для текущего прогона."""
    suffix = uuid.uuid4().hex[:6]
    return {
        "firmware_id": f"FW-{suffix}",
        "type_cert_id": f"TC-{suffix}",
        "drone_pass_id": f"DP-{suffix}",
        "order_id": f"ORD-{suffix}",
        "developer_id": f"DEV-{suffix}",
        "aggregator_id": f"AGG-{suffix}",
        "operator_id": f"OP-{suffix}",
        "insurer_id": f"INS-{suffix}",
        "cert_center_id": f"CC-{suffix}",
        "manufacturer_id": f"MFR-{suffix}",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Тесты — выполняются строго по порядку (pytest-ordering / default order)
# ══════════════════════════════════════════════════════════════════════════════


class TestE2EFabricScenario:
    """Полный E2E с записью в Hyperledger Fabric."""

    # ── Phase 0: Регистрация систем в Регуляторе ─────────────────────────────

    def test_01_register_systems(self, kafka_bus):
        """Регистрация основных систем + dummy_fabric в Регуляторе."""
        systems_to_register = [
            ("agregator", "aggregator"),
            ("operator", "operator"),
            ("insurer", "insurer"),
            ("orvd_system", "orvd"),
            ("gcs", "gcs"),
            ("dummy_fabric", "fabric"),
        ]
        for system_id, system_type in systems_to_register:
            resp = bus_request(kafka_bus, REGULATOR_TOPIC, "register_system", {
                "system_id": system_id,
                "system_type": system_type,
            })
            assert resp.get("success") is True, f"register {system_id}: {resp}"
            pl = resp.get("payload") or {}
            assert pl.get("registered") is True

    # ── Phase 1: Сертификация на Fabric ──────────────────────────────────────

    def test_02_certify_firmware(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "certify_firmware", {
            "id": run_ids["firmware_id"],
            "security_objectives": '["SO_1","SO_2"]',
            "software_objectives": '["SW_1"]',
            "certified_at": datetime.now(timezone.utc).isoformat(),
            "certified_by": "E2E-CertAuthority",
        })
        assert resp.get("success") is True, f"certify_firmware: {resp}"

    def test_03_issue_type_certificate(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "issue_type_certificate", {
            "id": run_ids["type_cert_id"],
            "model": "E2E-DroneModel",
            "manufacturer_id": run_ids["manufacturer_id"],
            "hardware_objectives": '["HW_1"]',
        })
        assert resp.get("success") is True, f"issue_type_certificate: {resp}"

    def test_04_create_drone_pass(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "create_drone_pass", {
            "id": run_ids["drone_pass_id"],
            "developer_id": run_ids["developer_id"],
            "model": "E2E-DroneModel",
            "drone_type": "multirotor",
            "weight_kg": 3,
            "max_flight_range_km": 10,
            "max_payload_weight_kg": 1,
            "release_year": 2025,
            "firmware_id": run_ids["firmware_id"],
            "type_certificate_id": run_ids["type_cert_id"],
        })
        assert resp.get("success") is True, f"create_drone_pass: {resp}"

    # ── Phase 2: Регистрация дрона + годовое страхование ─────────────────────

    def test_05_register_drone(self, kafka_bus):
        """Сертификат регулятора → регистрация у оператора → годовое КАСКО."""
        r_cert = bus_request(kafka_bus, REGULATOR_TOPIC, "register_drone_cert", {
            "drone_id": DRONE_ID,
        })
        assert r_cert.get("success") is True
        cert_id = (r_cert.get("payload") or {})["certificate_id"]
        _state["drone_cert_id"] = cert_id

        r_op = bus_request(kafka_bus, OPERATOR_TOPIC, "register_drone", {
            "drone_id": DRONE_ID,
            "model": "E2E-DroneModel",
            "capabilities": ["cargo"],
            "certificate_id": cert_id,
        })
        assert r_op.get("success") is True

        # Pannual = Vdrone × Rbase_hull × Kfleet_history
        # = 150_000 × 0.08 (delivery) × 1.0 (новый дрон) = 12_000.00
        r_ins = bus_request(kafka_bus, INSURER_TOPIC, "annual_insurance", {
            "drone_id": DRONE_ID,
            "drone_value": DRONE_VALUE,
            "drone_type": DRONE_TYPE,
        })
        assert r_ins.get("success") is True, f"annual_insurance: {r_ins}"
        ins = r_ins.get("payload") or {}

        assert ins.get("policy_type") == "annual"
        assert ins.get("status") == "active"
        assert ins.get("kfleet_history") == "1.0"

        expected_premium = Decimal("150000") * Decimal("0.08") * Decimal("1.0")
        assert Decimal(ins["premium"]) == expected_premium

        _state["annual_policy_id"] = ins["policy_id"]
        _state["annual_premium"] = ins["premium"]
        _state["annual_start"] = ins["start_date"]
        _state["annual_end"] = ins["end_date"]

    def test_06_record_insurance_on_fabric(self, kafka_bus, fabric_ready, run_ids):
        """Фиксация годового страхования в леджере Fabric."""
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "create_insurance", {
            "drone_id": run_ids["drone_pass_id"],
            "insurer_id": run_ids["insurer_id"],
            "coverage_amount": DRONE_VALUE,
            "incident_count": 0,
            "valid_from": _state.get("annual_start", datetime.now(timezone.utc).isoformat()),
            "valid_to": _state.get("annual_end", (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()),
        })
        assert resp.get("success") is True, f"create_insurance on Fabric: {resp}"

    # ── Phase 3: Заказ + миссионное страхование ──────────────────────────────

    def test_07_register_operator_in_aggregator(self, kafka_bus, agregator_url):
        operator_id = "e2e-fabric-operator"
        r_cert = bus_request(kafka_bus, REGULATOR_TOPIC, "register_operator_cert", {
            "operator_id": operator_id,
        })
        assert r_cert.get("success") is True
        cert_id = (r_cert.get("payload") or {})["certificate_id"]

        r = rest_post(agregator_url, "/operators", {
            "name": "E2E Fabric Operator",
            "license": "E2E-FAB-LIC",
            "operator_id": operator_id,
            "certificate_id": cert_id,
        })
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        _state["operator_id"] = operator_id

    def test_08_create_order_with_mission_insurance(self, agregator_url, kafka_bus):
        """Создание заказа через REST → агрегатор → миссионное страхование."""
        r = rest_post(agregator_url, "/customers", {
            "name": "E2E Fabric Customer",
            "email": "e2e-fabric@test.local",
        })
        assert r.status_code == 200
        customer_id = r.json()["customer_id"]

        r = rest_post(agregator_url, "/orders", {
            "customer_id": customer_id,
            "description": "E2E-Fabric delivery",
            "budget": ORDER_BUDGET,
            "drone_type": DRONE_TYPE,
            "pickup": {"lat": 55.75, "lon": 37.62},
            "dropoff": {"lat": 55.80, "lon": 37.70},
        })
        assert r.status_code == 200
        body = r.json()
        _state["rest_order_id"] = body["order_id"]

        if body["status"] != "matched":
            pytest.skip("No drone matched")

        # confirm-price → миссионное страхование
        # Pmission = Vcargo × Rrisk_class × Kenv × Kincident_history
        # = 5_000 × 0.08 (delivery) × 1.0 × 1.0 = 400.00
        r = rest_post(agregator_url, f"/orders/{body['order_id']}/confirm-price")
        assert r.status_code == 200
        confirm = r.json()
        assert confirm.get("status") == "confirmed"

        order_data = confirm.get("order", {})
        assert order_data.get("policy_id"), "policy_id должен быть после confirm-price"

        expected_mission = Decimal(str(ORDER_BUDGET)) * Decimal("0.08")
        assert Decimal(str(order_data["insurance_premium"])) == expected_mission

        _state["mission_policy_id"] = order_data["policy_id"]
        _state["mission_premium"] = str(order_data["insurance_premium"])

    # ── Phase 4: Жизненный цикл заказа на Fabric ────────────────────────────

    def test_09_create_order_on_fabric(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "create_order", {
            "id": run_ids["order_id"],
            "aggregator_id": run_ids["aggregator_id"],
            "operator_id": "",
            "drone_id": "",
            "insurer_id": run_ids["insurer_id"],
            "cert_center_id": run_ids["cert_center_id"],
            "developer_id": run_ids["developer_id"],
            "fleet_price": ORDER_BUDGET,
            "aggregator_fee": int(ORDER_BUDGET * 0.1),
            "insurance_premium": int(float(_state.get("mission_premium", "400"))),
            "risk_reserve": 20,
            "insurance_coverage_amount": DRONE_VALUE,
            "mission_insurance_id": f'INS-{run_ids["drone_pass_id"]}',
            "details": "[]",
        })
        assert resp.get("success") is True, f"create_order on Fabric: {resp}"

    def test_10_assign_order_on_fabric(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "assign_order", {
            "order_id": run_ids["order_id"],
            "operator_id": run_ids["operator_id"],
            "drone_id": run_ids["drone_pass_id"],
            "details": "[]",
        })
        assert resp.get("success") is True, f"assign_order on Fabric: {resp}"

    def test_11_approve_order_on_fabric(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "approve_order", {
            "order_id": run_ids["order_id"],
        })
        assert resp.get("success") is True, f"approve_order on Fabric: {resp}"

    def test_12_confirm_order_on_fabric(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "confirm_order", {
            "order_id": run_ids["order_id"],
        })
        assert resp.get("success") is True, f"confirm_order on Fabric: {resp}"

    def test_13_request_flight_permission(self, kafka_bus, fabric_ready, run_ids):
        now = datetime.now(timezone.utc)
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "request_flight_permission", {
            "order_id": run_ids["order_id"],
            "valid_from": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "valid_to": (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        assert resp.get("success") is True, f"request_flight_permission: {resp}"

    def test_14_approve_flight_permission(self, kafka_bus, fabric_ready, run_ids):
        permission_id = f'PERM-{run_ids["order_id"]}'
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "approve_flight_permission", {
            "permission_id": permission_id,
        })
        assert resp.get("success") is True, f"approve_flight_permission: {resp}"

    def test_15_start_order_on_fabric(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "start_order", {
            "order_id": run_ids["order_id"],
        })
        assert resp.get("success") is True, f"start_order on Fabric: {resp}"

    def test_16_finish_order_on_fabric(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "finish_order", {
            "order_id": run_ids["order_id"],
        })
        assert resp.get("success") is True, f"finish_order on Fabric: {resp}"

    def test_17_finalize_order_on_fabric(self, kafka_bus, fabric_ready, run_ids):
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "finalize_order", {
            "order_id": run_ids["order_id"],
        })
        assert resp.get("success") is True, f"finalize_order on Fabric: {resp}"

    # ── Phase 5: Завершение заказа в основной системе ────────────────────────

    def test_18_complete_order_in_aggregator(self, agregator_url):
        order_id = _state.get("rest_order_id")
        if not order_id:
            pytest.skip("order was not created (test_08 skipped)")

        r = rest_post(agregator_url, f"/orders/{order_id}/confirm-completion")
        assert r.status_code == 200
        assert r.json().get("status") == "completed"

        r = rest_get(agregator_url, f"/orders/{order_id}")
        assert r.status_code == 200
        final = r.json()["order"]
        assert final["status"] == "completed"
        assert final.get("policy_id"), "policy_id должен сохраниться в завершённом заказе"

    # ── Phase 6: Верификация леджера ─────────────────────────────────────────

    def test_19_verify_order_in_ledger(self, kafka_bus, fabric_ready, run_ids):
        """Чтение финального заказа из Fabric и проверка ID."""
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "read_order", {
            "id": run_ids["order_id"],
        })
        assert resp.get("success") is True, f"read_order: {resp}"
        order = resp.get("payload") or {}
        assert order.get("ID") == run_ids["order_id"] or order.get("id") == run_ids["order_id"]

    def test_20_verify_drone_pass_in_ledger(self, kafka_bus, fabric_ready, run_ids):
        """Чтение DronePass из Fabric и проверка ID."""
        resp = bus_request(kafka_bus, FABRIC_TOPIC, "read_drone_pass", {
            "id": run_ids["drone_pass_id"],
        })
        assert resp.get("success") is True, f"read_drone_pass: {resp}"
        dp = resp.get("payload") or {}
        assert dp.get("ID") == run_ids["drone_pass_id"] or dp.get("id") == run_ids["drone_pass_id"]
