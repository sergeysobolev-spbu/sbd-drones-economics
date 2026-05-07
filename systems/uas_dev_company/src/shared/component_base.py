"""Component wrappers for service objects."""

from __future__ import annotations

from typing import Any, Callable

from broker.system_bus import SystemBus
from sdk.base_component import BaseComponent


class ServiceComponent(BaseComponent):
    """BaseComponent adapter around a mapping of action handlers."""

    def __init__(
        self,
        component_id: str,
        component_type: str,
        topic: str,
        bus: SystemBus,
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
        trusted_sender: str | frozenset[str],
    ):
        self._service_handlers = handlers
        if isinstance(trusted_sender, frozenset):
            self._trusted_senders = trusted_sender
        else:
            self._trusted_senders = frozenset({trusted_sender})
        super().__init__(component_id=component_id, component_type=component_type, topic=topic, bus=bus)

    def _register_handlers(self) -> None:
        for action, handler in self._service_handlers.items():
            self.register_handler(action, self._guard(handler))

    def _guard(self, handler: Callable[[dict[str, Any]], dict[str, Any]]):
        def guarded(message: dict[str, Any]) -> dict[str, Any]:
            if message.get("sender") not in self._trusted_senders:
                return {"ok": False, "error": "direct_component_call_forbidden"}
            return handler(message.get("payload", {}) or {})

        return guarded
