"""
DummyComponent - шаблон для создания новых компонентов дрона.

Использует единую шину SystemBus (как и системы).
Копируй эту папку и адаптируй под свои нужды.
"""
from typing import Dict, Any, Optional

from shared.base_component import BaseComponent
from shared.topics import ComponentTopics, DummyComponentActions
from broker.system_bus import SystemBus


class DummyComponent(BaseComponent):
    """
    Шаблон компонента дрона.

    Для создания своего компонента:
    1. Скопируй эту папку
    2. Переименуй класс
    3. Добавь свои handlers
    """

    def __init__(
        self,
        component_id: str,
        name: str,
        bus: SystemBus,
    ):
        self.name = name
        self._state = {"counter": 0}
        super().__init__(
            component_id=component_id,
            component_type="dummy_component",
            topic=ComponentTopics.DUMMY_COMPONENT,
            bus=bus,
        )
        print(f"DummyComponent '{name}' initialized")

    def _register_handlers(self):
        """Регистрация обработчиков для каждого action."""
        self.register_handler(DummyComponentActions.ECHO, self._handle_echo)
        self.register_handler(DummyComponentActions.INCREMENT, self._handle_increment)
        self.register_handler(DummyComponentActions.GET_STATE, self._handle_get_state)

    def _handle_echo(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработчик action=echo.
        Возвращает полученные данные обратно.
        """
        payload = message.get("payload", {})
        return {"echo": payload, "from": self.component_id}

    def _handle_increment(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработчик action=increment.
        Увеличивает счётчик на payload.value.
        """
        payload = message.get("payload", {})
        self._state["counter"] += payload.get("value", 1)
        return {"counter": self._state["counter"], "from": self.component_id}

    def _handle_get_state(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработчик action=get_state.
        Возвращает текущее состояние.
        """
        return {**self._state, "from": self.component_id}
