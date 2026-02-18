"""Тесты для DummyComponent."""
import pytest
from unittest.mock import MagicMock

from components.dummy_component.src.dummy_component import DummyComponent


@pytest.fixture
def event_bus():
    """Мок шины событий."""
    return MagicMock()


@pytest.fixture
def component(event_bus):
    """Экземпляр DummyComponent с мок-шиной."""
    return DummyComponent(
        component_id="test_component",
        name="TestDummy",
        bus=event_bus,
    )


def test_subscribe_on_start(component, event_bus):
    """Компонент подписывается на топик при start."""
    component.start()
    event_bus.subscribe.assert_called()


def test_echo(component):
    """Echo возвращает те же данные."""
    message = {
        "action": "echo",
        "sender": "test_client",
        "payload": {"message": "hello"},
    }
    result = component._handle_echo(message)
    assert result["echo"] == {"message": "hello"}
    assert result["from"] == "test_component"


def test_increment(component):
    """Increment увеличивает счётчик."""
    assert component._state["counter"] == 0

    message = {
        "action": "increment",
        "sender": "test_client",
        "payload": {"value": 5},
    }
    result = component._handle_increment(message)
    assert component._state["counter"] == 5
    assert result["counter"] == 5


def test_get_state(component):
    """Get_state возвращает текущее состояние."""
    component._state["counter"] = 42
    message = {"action": "get_state", "sender": "test_client", "payload": {}}
    result = component._handle_get_state(message)
    assert result["counter"] == 42
    assert result["from"] == "test_component"


def test_message_routing(component, event_bus):
    """Проверка маршрутизации action через _handle_message."""
    message = {
        "action": "echo",
        "sender": "test_client",
        "payload": {"data": "ping"},
        "reply_to": "replies.test",
        "correlation_id": "abc123",
    }
    component._handle_message(message)
    event_bus.publish.assert_called_once()
