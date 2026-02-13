"""Тесты для DummyComponent."""
import unittest
from unittest.mock import MagicMock

from components.dummy_component.src.dummy_component import DummyComponent
from shared.event import Event


class TestDummyComponent(unittest.TestCase):
    def setUp(self):
        self.event_bus = MagicMock()
        self.component = DummyComponent(self.event_bus)

    def test_subscribe_on_init(self):
        """Компонент подписывается на события при инициализации."""
        self.event_bus.subscribe.assert_called_once_with(
            "dummy_component", 
            self.component._handle_event
        )

    def test_echo(self):
        """Echo возвращает те же данные."""
        event = Event(
            source="test",
            destination="dummy_component",
            operation="echo",
            parameters={"data": "test_data"}
        )
        self.component._handle_event(event)
        
        self.event_bus.publish.assert_called_once()
        call_args = self.event_bus.publish.call_args
        response = call_args[0][0]
        
        self.assertEqual(response.operation, "echo_response")
        self.assertEqual(response.parameters, {"data": "test_data"})

    def test_increment(self):
        """Increment увеличивает счётчик."""
        event = Event(
            source="test",
            destination="dummy_component",
            operation="increment",
            parameters={"value": 5}
        )
        self.component._handle_event(event)
        
        self.assertEqual(self.component._state["counter"], 5)


if __name__ == "__main__":
    unittest.main()
