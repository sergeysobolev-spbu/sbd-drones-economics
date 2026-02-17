"""
Unit тесты для DummyComponent и DummySystem.
Без внешних зависимостей (Docker, брокеры).
"""
import pytest
from unittest.mock import MagicMock, patch


class TestDummyComponent:
    """Unit тесты DummyComponent (SystemBus)."""

    def _make_component(self):
        from components.dummy_component.src.dummy_component import DummyComponent
        mock_bus = MagicMock()
        mock_bus.subscribe = MagicMock()
        mock_bus.start = MagicMock()
        component = DummyComponent(
            component_id="test_component",
            name="TestDummy",
            bus=mock_bus,
        )
        return component, mock_bus

    def test_increment(self):
        """Тест increment: увеличение счётчика."""
        component, bus = self._make_component()
        assert component._state["counter"] == 0

        message = {
            "action": "increment",
            "sender": "test_client",
            "payload": {"value": 5},
        }
        result = component._handle_increment(message)
        assert component._state["counter"] == 5
        assert result["counter"] == 5

    def test_echo(self):
        """Тест echo: возврат данных."""
        component, bus = self._make_component()
        message = {
            "action": "echo",
            "sender": "test_client",
            "payload": {"message": "hello"},
        }
        result = component._handle_echo(message)
        assert result["echo"] == {"message": "hello"}
        assert result["from"] == "test_component"

    def test_get_state(self):
        """Тест get_state: возврат состояния."""
        component, bus = self._make_component()
        component._state["counter"] = 42
        message = {"action": "get_state", "sender": "test_client", "payload": {}}
        result = component._handle_get_state(message)
        assert result["counter"] == 42
        assert result["from"] == "test_component"

    def test_message_routing(self):
        """Проверка маршрутизации action через _handle_message."""
        component, bus = self._make_component()
        message = {
            "action": "echo",
            "sender": "test_client",
            "payload": {"data": "ping"},
            "reply_to": "replies.test",
            "correlation_id": "abc123",
        }
        component._handle_message(message)
        bus.publish.assert_called_once()

    def test_subscribe_on_start(self):
        """Компонент подписывается на топик при start (через BaseComponent)."""
        component, bus = self._make_component()
        component.start()
        bus.subscribe.assert_called()


class TestDummySystem:
    """Unit тесты DummySystem."""

    def test_handle_echo(self):
        """Тест echo handler."""
        from systems.dummy_system.src.dummy import DummySystem

        mock_bus = MagicMock()
        mock_bus.subscribe = MagicMock()
        mock_bus.start = MagicMock()

        with patch('shared.base_system.threading'):
            system = DummySystem(
                system_id="test_dummy",
                name="TestDummy",
                bus=mock_bus,
                health_port=None
            )

        message = {
            "action": "echo",
            "sender": "test_client",
            "payload": {"data": "test_data"}
        }

        result = system._handle_echo(message)

        assert result["echo"] == "test_data"
        assert result["from"] == "test_dummy"

    def test_handle_process(self):
        """Тест process handler: value * 2."""
        from systems.dummy_system.src.dummy import DummySystem

        mock_bus = MagicMock()
        mock_bus.subscribe = MagicMock()
        mock_bus.start = MagicMock()

        with patch('shared.base_system.threading'):
            system = DummySystem(
                system_id="test_dummy",
                name="TestDummy",
                bus=mock_bus,
                health_port=None
            )

        message = {
            "action": "process",
            "sender": "test_client",
            "payload": {"value": 21}
        }

        result = system._handle_process(message)

        assert result["result"] == 42
        assert result["processed_by"] == "test_dummy"
