"""
Broker module — единая шина SystemBus для систем и компонентов.

Структура:
- broker/src/       - SystemBus (абстракция), bus_factory
- broker/kafka/     - KafkaSystemBus
- broker/mqtt/      - MQTTSystemBus

EventBus (deprecated):
- broker/kafka/kafka_bus.py  - KafkaEventBus
- broker/mqtt/mqtt_bus.py    - MQTTEventBus

Используй create_system_bus() из broker.bus_factory для создания шины.
"""
import warnings
from abc import ABC, abstractmethod
from typing import Callable, List

from shared.event import Event


class EventBus(ABC):
    """
    DEPRECATED: Используй SystemBus вместо EventBus.
    Оставлен для обратной совместимости.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        warnings.warn(
            "EventBus is deprecated. Use SystemBus (broker.system_bus.SystemBus) instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    @abstractmethod
    def publish(self, event: Event, destination: str) -> bool:
        pass

    @abstractmethod
    def subscribe(self, module_name: str, callback: Callable[[Event], None]) -> bool:
        pass

    @abstractmethod
    def unsubscribe(self, module_name: str) -> bool:
        pass

    @abstractmethod
    def get_events_for_module(self, module_name: str) -> List[Event]:
        pass
