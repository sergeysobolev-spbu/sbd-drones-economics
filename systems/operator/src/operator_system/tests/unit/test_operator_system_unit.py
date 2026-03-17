from unittest.mock import Mock

from systems.operator.src.operator_system import OperatorSystem


def test_operator_system_constructs_and_has_stats():
    bus = Mock()
    op = OperatorSystem("operator-01", bus)
    assert op.stats["orders_received"] == 0
    assert isinstance(op.active_orders, dict)

