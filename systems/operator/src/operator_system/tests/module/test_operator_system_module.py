from unittest.mock import Mock

from systems.operator.src.operator_system import OperatorSystem


def test_receive_order_requires_order_payload():
    bus = Mock()
    op = OperatorSystem("operator-01", bus)

    result = op._handle_receive_order({"payload": {}})
    assert "error" in result
