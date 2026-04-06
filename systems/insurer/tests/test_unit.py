"""Unit тесты для системы Insurer (моки, без брокера)."""
import pytest
from unittest.mock import MagicMock

from systems.insurer.src.insurer_component.src.insurer_component import InsurerComponent
from systems.insurer.src.gateway.src.gateway import InsurerGateway


@pytest.fixture
def component_and_bus():
    mock_bus = MagicMock()
    component = InsurerComponent(component_id="test_insurer", bus=mock_bus)
    return component, mock_bus


@pytest.fixture
def gateway_and_bus():
    mock_bus = MagicMock()
    gw = InsurerGateway(system_id="test_insurer_gw", bus=mock_bus)
    return gw, mock_bus


def test_calculate_policy_default_kbm(component_and_bus):
    component, bus = component_and_bus
    msg = {
        "action": "calculate_policy",
        "sender": "test",
        "payload": {"manufacturer_id": "m1", "operator_id": "op1"},
    }
    result = component._handle_calculate(msg)
    assert result["calculated_cost"] == "1000.00"
    assert result["manufacturer_kbm"] == "1.00"
    assert result["operator_kbm"] == "1.00"


def test_purchase_policy(component_and_bus):
    component, bus = component_and_bus
    msg = {
        "action": "purchase_policy",
        "sender": "test",
        "payload": {
            "order_id": "o1",
            "operator_id": "op1",
            "drone_id": "d1",
            "coverage_amount": 5000,
        },
    }
    result = component._handle_purchase(msg)
    assert result["status"] == "active"
    assert "policy_id" in result
    assert result["order_id"] == "o1"
    assert len(component._policies) == 1


def test_report_incident_increases_kbm(component_and_bus):
    component, bus = component_and_bus

    component._policies["p1"] = {
        "id": "p1",
        "order_id": "o1",
        "manufacturer_id": "m1",
        "operator_id": "op1",
        "status": "active",
    }

    msg = {
        "action": "report_incident",
        "sender": "test",
        "payload": {
            "order_id": "o1",
            "manufacturer_id": "m1",
            "operator_id": "op1",
            "damage_amount": 2000,
        },
    }
    result = component._handle_incident(msg)
    assert result["status"] == "processed"
    assert result["new_manufacturer_kbm"] == "1.10"
    assert result["new_operator_kbm"] == "1.10"
    assert len(component._incidents) == 1


def test_kbm_compounds_on_multiple_incidents(component_and_bus):
    component, bus = component_and_bus

    component._policies["p1"] = {
        "id": "p1",
        "order_id": "o1",
        "manufacturer_id": "m1",
        "operator_id": "op1",
        "status": "active",
    }

    msg = {
        "action": "report_incident",
        "sender": "test",
        "payload": {"order_id": "o1", "manufacturer_id": "m1", "operator_id": "op1", "damage_amount": 100},
    }
    component._handle_incident(msg)
    result = component._handle_incident(msg)
    assert result["new_manufacturer_kbm"] == "1.21"


def test_terminate_policy(component_and_bus):
    component, bus = component_and_bus

    component._policies["p1"] = {"id": "p1", "order_id": "o1", "status": "active"}

    msg = {"action": "terminate_policy", "sender": "test", "payload": {"order_id": "o1"}}
    result = component._handle_terminate(msg)
    assert result["status"] == "terminated"
    assert component._policies["p1"]["status"] == "terminated"


def test_terminate_nonexistent_policy_raises(component_and_bus):
    component, bus = component_and_bus
    msg = {"action": "terminate_policy", "sender": "test", "payload": {"order_id": "nonexistent"}}
    with pytest.raises(ValueError, match="no active policy"):
        component._handle_terminate(msg)


def test_gateway_routes_to_component(gateway_and_bus):
    gw, bus = gateway_and_bus
    bus.request.return_value = {
        "success": True,
        "payload": {"calculated_cost": "1000.00"},
    }

    msg = {"action": "calculate_policy", "sender": "external", "payload": {}}
    result = gw._handle_proxy(msg)
    assert "calculated_cost" in result
    bus.request.assert_called_once()
