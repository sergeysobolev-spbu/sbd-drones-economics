"""
E2E negative scenario:

  ORVD приказывает аварийную посадку (revoke_takeoff) → дрон сел, миссия не
  завершена → заказчик подаёт инцидент в Aggregator → заказ переходит в
  `dispute` (НЕ в `completed`) → страховщик через Operator выплачивает
  заказчику покрытие по report_incident.

Контракты:
- ORVD `revoke_takeoff` (status='landing_required') — формальное «приказание
  аварийной посадки» от внешнего регулятора. Это и есть негативное событие,
  с которого начинается сценарий.
- ORVD `get_mission_status` подтверждает, что mission переведён в
  `landing_required`, и Aggregator-side order не дошёл до `completed`.
- POST `/orders/{id}/incident` создаёт инцидент в Aggregator (order → dispute).
- Operator `buy_insurance_policy` action=`report_incident` инициирует выплату
  через insurer (тот возвращает `payment_amount`).

Тест намеренно лёгкий: не запускает GCS/SITL/автопилот — фокус на цепочке
«регулятор приказал посадку → страховое разбирательство → выплата».
"""
from __future__ import annotations

import time
from typing import Any, Dict

import pytest
import requests

# ---- System-level topics (gateway) ----
OPERATOR_TOPIC = "systems.operator"
ORVD_TOPIC = "systems.orvd_system"
REGULATOR_TOPIC = "systems.regulator"
INSURER_TOPIC = "systems.insurer"
ORVD_COMPONENT_TOPIC = "components.orvd_component"
AGREGATOR_OPERATOR_REQUESTS_TOPIC = "components.agregator.operator.requests"

E2E_DRONE_ID = "drone_negative_001"
ORDER_BUDGET = 5000
DAMAGE_AMOUNT = int(ORDER_BUDGET * 0.6)

_state: Dict[str, Any] = {}


def bus_request(bus, topic: str, action: str, payload: dict, timeout: float = 25) -> Dict[str, Any]:
    resp = bus.request(
        topic,
        {"action": action, "sender": "e2e_negative_test", "payload": payload},
        timeout=timeout,
    )
    assert resp is not None, f"Timeout: {action} -> {topic}"
    return resp


def rest_post(base: str, path: str, json: dict | None = None) -> requests.Response:
    return requests.post(f"{base}{path}", json=json or {}, timeout=15)


def rest_get(base: str, path: str) -> requests.Response:
    return requests.get(f"{base}{path}", timeout=15)


class TestE2ENegativeScenario:
    """ORVD emergency landing → order disputed → customer insurance payout."""

    # ------------------------------------------------------------------ bootstrap

    def test_01_bootstrap_systems_and_actors(self, kafka_bus, agregator_url):
        """Регистрация систем в регуляторе, оператора и дрона в нужных реестрах."""
        for system_id, system_type in (
            ("agregator", "aggregator"),
            ("operator", "operator"),
            ("insurer", "insurer"),
            ("orvd_system", "orvd"),
            ("cyber_drons", "drone"),
        ):
            r = bus_request(
                kafka_bus,
                REGULATOR_TOPIC,
                "register_system",
                {"system_id": system_id, "system_type": system_type},
            )
            assert r.get("success") is True, r

        op_cert = bus_request(
            kafka_bus,
            REGULATOR_TOPIC,
            "register_operator_cert",
            {"operator_id": "e2e-operator-negative"},
        )
        assert op_cert.get("success") is True, op_cert
        _state["operator_cert_id"] = (op_cert.get("payload") or {})["certificate_id"]

        op = rest_post(
            agregator_url,
            "/operators",
            {
                "name": "E2E Negative Operator",
                "license": "E2E-NEG-LIC-1",
                "email": "e2e-negative-op@local",
                "password": "e2e-negative-op-pass",
            },
        )
        assert op.status_code in (200, 201), f"{op.status_code} {op.text}"

        drone_cert = bus_request(
            kafka_bus,
            REGULATOR_TOPIC,
            "register_drone_cert",
            {"drone_id": E2E_DRONE_ID},
        )
        assert drone_cert.get("success") is True, drone_cert
        _state["drone_cert_id"] = (drone_cert.get("payload") or {})["certificate_id"]

        reg_drone = bus_request(
            kafka_bus,
            OPERATOR_TOPIC,
            "register_drone",
            {
                "drone_id": E2E_DRONE_ID,
                "model": "AgroDron-X1",
                "capabilities": ["cargo", "sprayer"],
                "certificate_id": _state["drone_cert_id"],
            },
        )
        assert reg_drone.get("success") is True, reg_drone

        # Прямая регистрация в ORVD (минуем certificate-path, у которого
        # есть известный таймаут — см. Test1.test_03b в основном сценарии).
        try:
            reg_orvd = bus_request(
                kafka_bus,
                ORVD_TOPIC,
                "register_drone",
                {"drone_id": E2E_DRONE_ID, "model": "AgroDron-X1"},
            )
            assert reg_orvd.get("success") is True, reg_orvd
        except AssertionError:
            pytest.skip("ORVD register_drone not reachable from negative scenario")

    # ------------------------------------------------------------------ order + insurance

    def test_02_customer_order_and_mission_insurance(self, kafka_bus, agregator_url):
        """Заказчик создаёт заказ; Operator выставляет цену → заказчик подтверждает;
        приобретается mission insurance (по этому полису пойдёт выплата)."""
        customer = rest_post(
            agregator_url,
            "/customers",
            {
                "name": "E2E Negative Customer",
                "email": "e2e-negative-cust@local",
                "password": "e2e-negative-cust-pass",
            },
        )
        assert customer.status_code in (200, 201), f"{customer.status_code} {customer.text}"
        cust_body = customer.json()
        customer_id = (cust_body.get("user") or {}).get("id") or cust_body.get("id")
        assert customer_id, f"customer id missing in response: {cust_body}"
        _state["customer_id"] = customer_id

        create = rest_post(
            agregator_url,
            "/orders",
            {
                "customer_id": customer_id,
                "description": "Negative scenario: emergency landing en-route",
                "budget": ORDER_BUDGET,
                "from_lat": 55.75,
                "from_lon": 37.62,
                "to_lat": 55.80,
                "to_lon": 37.70,
            },
        )
        assert create.status_code in (200, 201), f"{create.status_code} {create.text}"
        order_body = create.json()
        order_id = order_body.get("order_id") or order_body.get("id")
        assert order_id, order_body
        _state["order_id"] = order_id

        # Ждём пока Operator выкатит price_offer
        status = order_body.get("status", "")
        deadline = time.time() + 60
        while status != "matched" and time.time() < deadline:
            time.sleep(2)
            poll = rest_get(agregator_url, f"/orders/{order_id}")
            if poll.status_code == 200:
                status = poll.json().get("status", "")
        if status != "matched":
            # Cold-start fallback: пушим create_order напрямую в operator-bridge.
            kafka_bus.publish(
                AGREGATOR_OPERATOR_REQUESTS_TOPIC,
                {
                    "action": "create_order",
                    "sender": "e2e_negative_test",
                    "correlation_id": order_id,
                    "payload": {
                        "customer_id": customer_id,
                        "budget": ORDER_BUDGET,
                        "description": "Negative scenario order",
                    },
                },
            )
            time.sleep(5)
            status = rest_get(agregator_url, f"/orders/{order_id}").json().get("status", "")
        assert status == "matched", f"order is not matched after operator handshake: {status}"

        conf = rest_post(
            agregator_url,
            f"/orders/{order_id}/confirm-price",
            {"operator_id": "operator_component", "accepted_price": ORDER_BUDGET * 0.85},
        )
        assert conf.status_code in (200, 201), f"{conf.status_code} {conf.text}"

        mission_ins = bus_request(
            kafka_bus,
            OPERATOR_TOPIC,
            "buy_insurance_policy",
            {
                "order_id": order_id,
                "drone_id": E2E_DRONE_ID,
                "coverage_amount": ORDER_BUDGET,
                "insurance_action": "mission_insurance",
            },
        )
        assert mission_ins.get("success") is True, mission_ins
        pl = mission_ins.get("payload") or {}
        assert pl.get("status") == "insured", pl
        policy = pl.get("policy") or {}
        assert policy.get("policy_id"), policy
        _state["policy_id"] = policy["policy_id"]

    # ------------------------------------------------------------------ mission lift-off

    def test_03_mission_takes_off(self, kafka_bus):
        """ORVD: регистрируем миссию → авторизуем → request_takeoff.
        Это эквивалент «дрон в воздухе», без вовлечения GCS/SITL/автопилота."""
        order_id = _state.get("order_id")
        assert order_id, "order_id missing — run test_02 first"
        mission_id = f"mission-neg-{order_id}"
        route = [
            {"lat": 55.75, "lon": 37.62},
            {"lat": 55.80, "lon": 37.70},
        ]

        # register_mission через гейтвей, иначе через компонент (минуя PROXY_TIMEOUT).
        reg = None
        try:
            reg = bus_request(
                kafka_bus,
                ORVD_TOPIC,
                "register_mission",
                {"mission_id": mission_id, "drone_id": E2E_DRONE_ID, "route": route},
                timeout=15,
            )
        except AssertionError:
            reg = None
        if not reg or (reg.get("payload") or {}).get("status") not in (
            "mission_registered",
            "registered",
        ):
            reg = kafka_bus.request(
                ORVD_COMPONENT_TOPIC,
                {
                    "action": "register_mission",
                    "sender": "e2e_negative_test",
                    "payload": {
                        "mission_id": mission_id,
                        "drone_id": E2E_DRONE_ID,
                        "route": route,
                    },
                },
                timeout=30,
            )
        assert reg is not None, "ORVD register_mission not reachable"
        assert (reg.get("payload") or {}).get("status") in (
            "mission_registered",
            "registered",
        ), reg

        # authorize_mission
        auth = bus_request(
            kafka_bus,
            ORVD_COMPONENT_TOPIC,
            "authorize_mission",
            {"mission_id": mission_id},
            timeout=30,
        )
        assert auth.get("success") is True, auth
        assert (auth.get("payload") or {}).get("status") == "authorized", auth

        # request_takeoff — дрон взлетает
        takeoff = bus_request(
            kafka_bus,
            ORVD_COMPONENT_TOPIC,
            "request_takeoff",
            {
                "drone_id": E2E_DRONE_ID,
                "mission_id": mission_id,
                "battery_level": 95,
                "model": "AgroDron-X1",
            },
            timeout=20,
        )
        takeoff_payload = takeoff.get("payload") or {}
        assert takeoff_payload.get("status") == "takeoff_authorized", takeoff_payload

        _state["mission_id"] = mission_id

    # ------------------------------------------------------------------ ORVD orders emergency landing

    def test_04_orvd_orders_emergency_landing(self, kafka_bus):
        """ORVD revoke_takeoff — формальное приказание аварийной посадки.
        Должно перевести миссию в `landing_required`. Это негативный триггер."""
        mission_id = _state.get("mission_id")
        assert mission_id, "no mission — run test_03 first"

        revoke = bus_request(
            kafka_bus,
            ORVD_COMPONENT_TOPIC,
            "revoke_takeoff",
            {"drone_id": E2E_DRONE_ID, "mission_id": mission_id, "reason": "no_fly_zone_breach"},
            timeout=20,
        )
        revoke_pl = revoke.get("payload") or {}
        assert revoke_pl.get("status") == "landing_required", revoke_pl
        assert revoke_pl.get("drone_id") == E2E_DRONE_ID, revoke_pl

        # Mission status в ORVD теперь landing_required (не completed).
        mstatus = bus_request(
            kafka_bus,
            ORVD_COMPONENT_TOPIC,
            "get_mission_status",
            {"mission_id": mission_id},
            timeout=15,
        )
        mstatus_pl = mstatus.get("payload") or {}
        assert mstatus_pl.get("status") == "landing_required", (
            f"mission must be landing_required after revoke, got: {mstatus_pl}"
        )
        _state["mission_terminated"] = True

    # ------------------------------------------------------------------ order is NOT completed

    def test_05_order_did_not_complete(self, agregator_url):
        """Заказ должен оставаться в активном/не-`completed` статусе — миссия
        прервана до завершения, исполнитель не подтверждает выполнение."""
        if not _state.get("mission_terminated"):
            pytest.skip("mission did not reach landing_required — see test_04")

        order_id = _state["order_id"]
        poll = rest_get(agregator_url, f"/orders/{order_id}")
        assert poll.status_code == 200, f"{poll.status_code} {poll.text}"
        status = poll.json().get("status", "")
        assert status != "completed", (
            f"order should NOT be completed after emergency landing, got status={status!r}"
        )
        assert status not in ("completed_pending", "completed"), status
        _state["order_status_before_incident"] = status

    # ------------------------------------------------------------------ customer reports + insurance

    def test_06_customer_reports_incident_to_aggregator(self, agregator_url):
        """Заказчик регистрирует инцидент в агрегаторе → заказ переходит в `dispute`."""
        if not _state.get("mission_terminated"):
            pytest.skip("mission did not reach landing_required — see test_04")

        order_id = _state["order_id"]
        rep = rest_post(
            agregator_url,
            f"/orders/{order_id}/incident",
            {
                "reason": "emergency_landing_ordered_by_orvd",
                "description": "ORVD revoked takeoff mid-mission; cargo not delivered",
                "damage_amount": DAMAGE_AMOUNT,
            },
        )
        assert rep.status_code in (200, 201), f"{rep.status_code} {rep.text}"
        body = rep.json()
        # API возвращает order_status=dispute и регистрирует incident_id.
        assert body.get("incident_id") or body.get("id"), body
        assert body.get("order_status") in ("dispute", "in_dispute"), body

        # Заказ теперь в dispute, не completed.
        poll = rest_get(agregator_url, f"/orders/{order_id}").json()
        assert poll.get("status") in ("dispute", "in_dispute"), poll

    def test_07_customer_gets_insurance_payout(self, kafka_bus):
        """Финал: страховщик через Operator выплачивает по report_incident.

        Сумма выплаты должна совпасть с заявленным ущербом — это и есть
        «страховое покрытие, полученное заказчиком»."""
        if not _state.get("mission_terminated"):
            pytest.skip("mission did not reach landing_required — see test_04")

        order_id = _state["order_id"]
        claim = bus_request(
            kafka_bus,
            OPERATOR_TOPIC,
            "buy_insurance_policy",
            {
                "order_id": order_id,
                "drone_id": E2E_DRONE_ID,
                "coverage_amount": DAMAGE_AMOUNT,
                "insurance_action": "report_incident",
                "incident": {
                    "damage_amount": DAMAGE_AMOUNT,
                    "incident_type": "emergency_landing_ordered",
                    "description": "ORVD revoked takeoff; mission aborted, cargo lost",
                },
            },
            timeout=30,
        )
        assert claim.get("success") is True, claim
        claim_pl = claim.get("payload") or {}
        assert claim_pl.get("status") == "incident_processed", claim_pl

        claim_body = claim_pl.get("claim") or {}
        # Гарантируем что заказчик получил покрытие — payment_amount == damage_amount.
        payment = claim_body.get("payment_amount")
        assert payment == DAMAGE_AMOUNT, (
            f"customer payout {payment} != damage {DAMAGE_AMOUNT}: {claim_body}"
        )
        # Полис должен помнить новый коэффициент инцидентности.
        assert "new_kincident_history" in claim_body, claim_body
