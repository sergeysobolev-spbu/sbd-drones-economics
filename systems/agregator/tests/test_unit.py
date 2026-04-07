"""Unit тесты для системы Agregator (моки, без брокера)."""
import pytest
from unittest.mock import MagicMock

from systems.agregator.src.agregator_component.src.agregator_component import AgregatorComponent
from systems.agregator.src.gateway.src.gateway import AgregatorGateway


@pytest.fixture
def component_and_bus():
    mock_bus = MagicMock()
    component = AgregatorComponent(component_id="test_agregator", bus=mock_bus)
    return component, mock_bus


@pytest.fixture
def gateway_and_bus():
    mock_bus = MagicMock()
    gw = AgregatorGateway(system_id="test_gateway", bus=mock_bus)
    return gw, mock_bus


def test_register_customer(component_and_bus):
    component, bus = component_and_bus
    msg = {"action": "register_customer", "sender": "test", "payload": {"name": "John", "email": "j@test.com"}}
    result = component._handle_register_customer(msg)
    assert "customer_id" in result
    assert len(component._customers) == 1


def test_register_operator(component_and_bus):
    component, bus = component_and_bus
    msg = {"action": "register_operator", "sender": "test", "payload": {"name": "Ops Inc", "license": "L123"}}
    result = component._handle_register_operator(msg)
    assert "operator_id" in result
    assert len(component._operators) == 1


def test_create_order_with_drone_found(component_and_bus):
    component, bus = component_and_bus

    component._customers["c1"] = {"id": "c1", "name": "Test"}

    bus.request.return_value = {
        "success": True,
        "payload": {
            "drones": [{"drone_id": "d1", "operator_id": "op1", "price": 500}],
        },
    }

    msg = {
        "action": "create_order",
        "sender": "test",
        "payload": {
            "customer_id": "c1",
            "description": "delivery",
            "budget": 1000,
            "pickup": {"lat": 55.0, "lon": 37.0},
            "dropoff": {"lat": 55.1, "lon": 37.1},
        },
    }
    result = component._handle_create_order(msg)
    assert result["status"] == "matched"
    order = result["order"]
    assert order["drone_id"] == "d1"
    assert order["offered_price"] == 500


def test_create_order_no_drones(component_and_bus):
    component, bus = component_and_bus
    component._customers["c1"] = {"id": "c1", "name": "Test"}

    bus.request.return_value = {"success": True, "payload": {"drones": []}}

    msg = {
        "action": "create_order",
        "sender": "test",
        "payload": {"customer_id": "c1", "description": "test", "budget": 100},
    }
    result = component._handle_create_order(msg)
    assert result["status"] == "no_drones"


def test_confirm_price_full_flow(component_and_bus):
    component, bus = component_and_bus

    component._orders["o1"] = {
        "id": "o1",
        "customer_id": "c1",
        "status": "matched",
        "drone_id": "d1",
        "operator_id": "op1",
        "offered_price": 1000,
        "policy_id": None,
        "mission_id": None,
        "pickup": {"lat": 55.0, "lon": 37.0},
        "dropoff": {"lat": 55.1, "lon": 37.1},
    }

    bus.request.side_effect = [
        {"success": True, "payload": {"policy_id": "pol1", "status": "active"}},
        {"success": True, "payload": {"mission_id": "o1", "status": "mission_registered"}},
    ]

    msg = {"action": "confirm_price", "sender": "test", "payload": {"order_id": "o1"}}
    result = component._handle_confirm_price(msg)
    assert result["status"] == "confirmed"
    assert component._orders["o1"]["policy_id"] == "pol1"
    assert bus.request.call_count == 2


def test_confirm_completion(component_and_bus):
    component, bus = component_and_bus
    component._orders["o1"] = {"id": "o1", "status": "confirmed"}

    msg = {"action": "confirm_completion", "sender": "test", "payload": {"order_id": "o1"}}
    result = component._handle_confirm_completion(msg)
    assert result["status"] == "completed"


def test_list_orders(component_and_bus):
    component, bus = component_and_bus
    component._orders["o1"] = {"id": "o1", "status": "confirmed"}
    component._orders["o2"] = {"id": "o2", "status": "completed"}

    msg = {"action": "list_orders", "sender": "test", "payload": {}}
    result = component._handle_list_orders(msg)
    assert len(result["orders"]) == 2


def test_gateway_routes_to_component(gateway_and_bus):
    gw, bus = gateway_and_bus
    bus.request.return_value = {
        "success": True,
        "payload": {"orders": []},
    }

    msg = {"action": "list_orders", "sender": "external", "payload": {}}
    result = gw._handle_proxy(msg)
    assert "orders" in result
    bus.request.assert_called_once()
