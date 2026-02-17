# Backward compatibility - re-export from new location
from broker.src.bus_factory import create_event_bus, create_system_bus

# create_event_bus is deprecated, use create_system_bus instead.
__all__ = ["create_event_bus", "create_system_bus"]
