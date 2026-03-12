"""Топики и actions для Gateway dummy_system."""


class SystemTopics:
    DUMMY_SYSTEM = "systems.dummy_system"


class ComponentTopics:
    DUMMY_COMPONENT_A = "components.dummy_component_a"
    DUMMY_COMPONENT_B = "components.dummy_component_b"

    @classmethod
    def all(cls) -> list:
        return [cls.DUMMY_COMPONENT_A, cls.DUMMY_COMPONENT_B]


class GatewayActions:
    """Actions, доступные извне через systems.dummy_system."""
    ECHO = "echo"
    INCREMENT = "increment"
    GET_STATE = "get_state"
    GET_DATA = "get_data"
