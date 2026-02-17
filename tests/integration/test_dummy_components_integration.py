"""
Интеграционные тесты DummyComponent через реальный брокер (SystemBus).

Требует: make docker-up с профилем kafka или mqtt (dummy_component_a, dummy_component_b).
Параметры: docker/.env (BROKER_TYPE, KAFKA_PORT, MQTT_PORT, ADMIN_USER, ADMIN_PASSWORD).
Проверяет связь между поднятыми контейнерами компонентов: тест-клиент шлёт
request в components.dummy_component и получает ответ через request/response.
"""
import pytest
import os
import time
import socket

from shared.topics import ComponentTopics, DummyComponentActions


def _broker_available(retries=5, delay=2):
    """Проверка доступности брокера."""
    bt = (os.environ.get("BROKER_TYPE", "kafka") or "kafka").lower().strip().split("#")[0].strip()
    host = os.environ.get("BROKER_HOST", "localhost")
    port_val = os.environ.get("MQTT_PORT", "1883") if bt == "mqtt" else os.environ.get("KAFKA_PORT", "9092")
    port = int(port_val)
    for _ in range(retries):
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(delay)
    return False


@pytest.fixture(scope="module")
def system_bus():
    """SystemBus (реальный брокер). Пропуск, если брокер недоступен."""
    if not _broker_available():
        pytest.skip(
            f"Broker ({os.environ.get('BROKER_TYPE', 'kafka')}) "
            f"at {os.environ.get('BROKER_HOST', 'localhost')} not available. Run: make docker-up"
        )
    from broker.bus_factory import create_system_bus

    bt = (os.environ.get("BROKER_TYPE") or "kafka").lower().strip().split("#")[0].strip()
    host = os.environ.get("BROKER_HOST", "localhost")
    kafka_port = os.environ.get("KAFKA_PORT", "9092")
    mqtt_port = os.environ.get("MQTT_PORT", "1883")

    if not os.environ.get("BROKER_USER") and os.environ.get("ADMIN_USER"):
        os.environ["BROKER_USER"] = os.environ["ADMIN_USER"]
    if not os.environ.get("BROKER_PASSWORD") and os.environ.get("ADMIN_PASSWORD"):
        os.environ["BROKER_PASSWORD"] = os.environ["ADMIN_PASSWORD"]
    if bt == "kafka":
        os.environ["BROKER_TYPE"] = "kafka"
        os.environ["KAFKA_BOOTSTRAP_SERVERS"] = os.environ.get(
            "KAFKA_BOOTSTRAP_SERVERS", f"{host}:{kafka_port}"
        )
    else:
        os.environ["BROKER_TYPE"] = "mqtt"
        os.environ["MQTT_BROKER"] = os.environ.get("MQTT_BROKER", host)
        os.environ["MQTT_PORT"] = str(mqtt_port)

    bus = create_system_bus(client_id="test_component_client")
    bus.start()
    time.sleep(2)

    yield bus

    bus.stop()


class TestDummyComponentsE2E:
    """E2E: тест-клиент шлёт запросы в dummy_component (контейнеры dummy_component_a/b)."""

    def test_echo_at_least_one_component_responds(self, system_bus):
        """Хотя бы один из двух dummy_component отвечает на echo."""
        response = system_bus.request(
            ComponentTopics.DUMMY_COMPONENT,
            {
                "action": DummyComponentActions.ECHO,
                "sender": "test_component_client",
                "payload": {"message": "hello_components"},
            },
            timeout=10.0,
        )

        assert response is not None, "No response from dummy_component (timeout)"
        assert response.get("success") is True
        assert response["payload"]["echo"] == {"message": "hello_components"}
        assert "from" in response["payload"]

    def test_increment_and_state(self, system_bus):
        """Increment увеличивает счётчик, get_state возвращает его."""
        inc_response = system_bus.request(
            ComponentTopics.DUMMY_COMPONENT,
            {
                "action": DummyComponentActions.INCREMENT,
                "sender": "test_component_client",
                "payload": {"value": 10},
            },
            timeout=10.0,
        )
        assert inc_response is not None
        assert inc_response.get("success") is True
        assert inc_response["payload"].get("counter") is not None

        state_response = system_bus.request(
            ComponentTopics.DUMMY_COMPONENT,
            {
                "action": DummyComponentActions.GET_STATE,
                "sender": "test_component_client",
                "payload": {},
            },
            timeout=10.0,
        )
        assert state_response is not None
        assert state_response.get("success") is True
        assert "counter" in state_response["payload"]
