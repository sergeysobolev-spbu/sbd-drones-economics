import os
import time

import pytest

from broker.mqtt.mqtt_system_bus import MQTTSystemBus


def _wait_mqtt(host: str, port: int, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            bus = MQTTSystemBus(broker=host, port=port, client_id="test_client")
            bus.start()
            bus.stop()
            return
        except Exception as e:  # pragma: no cover
            last_exc = e
            time.sleep(0.5)
    raise RuntimeError(f"MQTT broker not ready at {host}:{port}: {last_exc}")


@pytest.mark.integration
def test_mqtt_receive_order_request_response():
    host = os.getenv("MQTT_BROKER", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    system_id = os.getenv("SYSTEM_ID", "operator-001")
    api_version = os.getenv("API_VERSION", "v1")

    _wait_mqtt(host, port)

    bus = MQTTSystemBus(broker=host, port=port, client_id="pytest-mqtt")
    bus.start()
    try:
        resp = bus.request(
            f"{system_id}.{api_version}.operator",
            {
                "action": "receive_order",
                "sender": "pytest-mqtt",
                "payload": {
                    "order": {
                        "id": f"ORDER-MQTT-{int(time.time())}",
                        "pickup": {"lat": 55.76, "lon": 37.62},
                        "dropoff": {"lat": 55.75, "lon": 37.61},
                        "payload_weight": 3.5,
                        "distance_km": 10.0,
                    }
                },
            },
            timeout=20.0,
        )
        assert resp is not None
        payload = resp.get("payload", {})
        assert "error" not in payload
        assert payload.get("order_id")
    finally:
        bus.stop()


@pytest.mark.integration
def test_mqtt_fleet_manager_get_uas_list():
    host = os.getenv("MQTT_BROKER", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))

    _wait_mqtt(host, port)

    bus = MQTTSystemBus(broker=host, port=port, client_id="pytest-mqtt-fleet")
    bus.start()
    try:
        resp = bus.request(
            "fleet_manager",
            {"action": "GET_UAS_LIST", "sender": "pytest-mqtt", "payload": {}},
            timeout=20.0,
        )
        assert resp is not None
        payload = resp.get("payload", {})
        assert "error" not in payload
        assert ("uas_list" in payload) or ("total_count" in payload) or ("total" in payload)
    finally:
        bus.stop()
