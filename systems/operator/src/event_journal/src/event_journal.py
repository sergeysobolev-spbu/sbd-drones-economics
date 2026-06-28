from __future__ import annotations

from typing import Any, Dict, Optional

from sdk.base_component import BaseComponent
from broker.system_bus import SystemBus
from systems.operator.src.topics import ComponentTopics


class EventJournal(BaseComponent):
    """
    Компонент журнала событий Эксплуатанта.

    На первом этапе он лишь логирует входящие события и подтверждает приём.
    В следующих шагах сюда будет добавлен адаптер к systems/analytics.
    """

    def __init__(self, component_id: str, bus: SystemBus, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        super().__init__(
            component_id=component_id,
            component_type="event_journal",
            topic=self.config.get("topic") or ComponentTopics.get_event_journal(),
            bus=bus,
        )

    def _register_handlers(self) -> None:
        # Базовый контракт: входящие сообщения с action="emit_event"
        self.register_handler("emit_event", self._handle_emit_event)

    def _handle_emit_event(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обрабатывает входящее событие.

        Сейчас просто пишет его в лог; в дальнейшем будет
        вызывать analytics_adapter для передачи в Analytics.
        """
        payload = message.get("payload", {}) or {}

        # Логируем в стандартный лог компонента
        self.logger.info("EventJournal received event: %s", payload)

        # Возвращаем минимальное подтверждение
        return {
            "status": "accepted",
            "event_type": payload.get("event_type"),
            "severity": payload.get("severity", "info"),
        }
