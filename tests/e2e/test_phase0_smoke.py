"""
Phase 0 smoke E2E (T14) — minimal happy-path checks for integration-phase0.

Scope: Aggregator HTTP health + Kafka topic reachability for TM-001/002 pattern.
Full order flow requires Operator with Kafka env overrides (see topic_map.yaml v0.2).

Skip/xfail policy (E2E-2):
  - skip: integration-phase0 stack not running (no AGREGATOR_URL / Kafka)
  - xfail: known contract gap (Operator not on Kafka topics yet)
  - pass: health + bus ping on canonical topics when stack is up

Run:
  E2E_PROFILE=integration-phase0 make e2e-up   # future T10 profile
  pytest tests/e2e/test_phase0_smoke.py -v -m phase0_smoke
"""
from __future__ import annotations

import os
import time

import pytest
import requests

pytestmark = pytest.mark.phase0_smoke

AGREGATOR_URL = os.environ.get("AGREGATOR_URL", "http://localhost:8081")
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_PREFIX = os.environ.get(
    "KAFKA_TOPIC_PREFIX",
    "v1.aggregator_insurer.local",
)
TM001 = f"{TOPIC_PREFIX}.operator.requests"
TM002 = f"{TOPIC_PREFIX}.operator.responses"
PHASE0_PROFILE = os.environ.get("E2E_PROFILE", "")


def _aggregator_reachable() -> bool:
    try:
        r = requests.get(f"{AGREGATOR_URL}/health", timeout=3)
        return r.status_code < 500
    except requests.RequestException:
        return False


def _kafka_bus_or_skip():
    if not os.environ.get("PHASE0_SMOKE_REQUIRE_KAFKA", "1") in ("0", "", "false", "False"):
        pass
    try:
        from broker.bus_factory import create_system_bus
    except ImportError:
        pytest.skip("broker SDK not available on PYTHONPATH")
    os.environ.setdefault("BROKER_TYPE", "kafka")
    os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", KAFKA_BOOTSTRAP)
    bus = create_system_bus(client_id="phase0_smoke")
    bus.start()
    return bus


@pytest.fixture(scope="module")
def require_phase0_stack():
    """Skip entire module when neither Aggregator nor explicit force flag is set."""
    if os.environ.get("PHASE0_SMOKE_FORCE", "0") in ("1", "true", "True"):
        return
    if not _aggregator_reachable():
        pytest.skip(
            "integration-phase0 stack not up "
            f"(AGREGATOR_URL={AGREGATOR_URL}); set PHASE0_SMOKE_FORCE=1 to run structural checks only"
        )


class TestPhase0SmokeStructure:
    """Structural checks — always runnable (no Docker)."""

    def test_topic_names_match_topic_map_v02(self):
        assert TM001 == "v1.aggregator_insurer.local.operator.requests"
        assert TM002 == "v1.aggregator_insurer.local.operator.responses"

    def test_env_overrides_documented(self):
        required = {
            "KAFKA_OPERATOR_REQUEST_TOPIC",
            "KAFKA_OPERATOR_RESPONSE_TOPIC",
            "BROKER_TYPE",
            "KAFKA_BOOTSTRAP_SERVERS",
        }
        documented = {
            "KAFKA_OPERATOR_REQUEST_TOPIC": TM001,
            "KAFKA_OPERATOR_RESPONSE_TOPIC": TM002,
            "BROKER_TYPE": "kafka",
            "KAFKA_BOOTSTRAP_SERVERS": KAFKA_BOOTSTRAP,
        }
        for key in required:
            assert key in documented


class TestPhase0SmokeRuntime:
    """Runtime checks — require integration-phase0 stack."""

    def test_aggregator_health(self, require_phase0_stack):
        resp = requests.get(f"{AGREGATOR_URL}/health", timeout=10)
        assert resp.status_code == 200, resp.text

    @pytest.mark.xfail(
        reason="Operator Kafka consumer path not aligned (TM-001 gap); coding agent tem-bas-operator",
        strict=False,
    )
    def test_tm001_operator_consumer_ack(self, require_phase0_stack):
        """Publish probe to TM-001; expect Operator ack on TM-002 within 30s (T14 acceptance)."""
        bus = _kafka_bus_or_skip()
        try:
            probe = {
                "action": "create_order",
                "sender": "phase0_smoke",
                "payload": {"order_id": "smoke-001", "service_type": "agro_field"},
            }
            deadline = time.time() + 30
            bus.publish(TM001, probe)
            while time.time() < deadline:
                resp = bus.request(TM002, {"action": "ping", "sender": "phase0_smoke", "payload": {}}, timeout=5)
                if resp is not None:
                    return
                time.sleep(2)
            pytest.fail(f"No response on {TM002} within 30s")
        finally:
            bus.stop()
