from unittest.mock import Mock

from systems.operator.src.operator_clients import DeveloperClient, RegulatorClient


def test_operator_clients_can_be_instantiated():
    bus = Mock()
    regulator = RegulatorClient(bus)
    developer = DeveloperClient(bus, regulator)

    assert regulator is not None
    assert developer is not None

