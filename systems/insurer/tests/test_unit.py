"""Unit тесты для системы Insurer (моки, без брокера)."""
import pytest
from decimal import Decimal
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


# ---------------------------------------------------------------------------
# Годовое страхование (Pannual)
# ---------------------------------------------------------------------------

class TestAnnualInsurance:
    """Pannual = Vdrone × Rbase_hull × Kfleet_history"""

    def test_annual_new_drone_delivery(self, component_and_bus):
        """
        Новый дрон-доставщик: Rbase_hull=0.08, Kfleet_history=1.0 (< 10 вылетов).
        Pannual = 100_000 × 0.08 × 1.0 = 8_000.
        """
        component, _ = component_and_bus
        msg = {
            "action": "annual_insurance",
            "sender": "test",
            "payload": {
                "drone_id": "drone-delivery-001",
                "operator_id": "op1",
                "drone_value": 100_000,
                "drone_type": "delivery",
            },
        }
        result = component._handle_annual_insurance(msg)
        assert result["status"] == "active"
        assert result["policy_type"] == "annual"
        assert result["premium"] == "8000.00"
        assert result["hull_rate"] == "0.08"
        assert result["kfleet_history"] == "1.0"

    def test_annual_new_drone_inspector(self, component_and_bus):
        """
        Новый дрон-инспектор: Rbase_hull=0.05, Kfleet_history=1.0.
        Pannual = 50_000 × 0.05 × 1.0 = 2_500.
        """
        component, _ = component_and_bus
        msg = {
            "action": "annual_insurance",
            "sender": "test",
            "payload": {
                "drone_id": "drone-insp-001",
                "operator_id": "op1",
                "drone_value": 50_000,
                "drone_type": "inspector",
            },
        }
        result = component._handle_annual_insurance(msg)
        assert result["premium"] == "2500.00"
        assert result["hull_rate"] == "0.05"

    def test_annual_new_drone_firefighter(self, component_and_bus):
        """
        Новый дрон-огнеборец: Rbase_hull=0.12, Kfleet_history=1.0.
        Pannual = 200_000 × 0.12 × 1.0 = 24_000.
        """
        component, _ = component_and_bus
        msg = {
            "action": "annual_insurance",
            "sender": "test",
            "payload": {
                "drone_id": "drone-fire-001",
                "operator_id": "op1",
                "drone_value": 200_000,
                "drone_type": "firefighter",
            },
        }
        result = component._handle_annual_insurance(msg)
        assert result["premium"] == "24000.00"
        assert result["hull_rate"] == "0.12"

    def test_annual_custom_hull_rate(self, component_and_bus):
        """hull_rate можно переопределить вручную."""
        component, _ = component_and_bus
        msg = {
            "action": "annual_insurance",
            "sender": "test",
            "payload": {
                "drone_id": "drone-custom-001",
                "operator_id": "op1",
                "drone_value": 100_000,
                "drone_type": "delivery",
                "hull_rate": 0.10,
            },
        }
        result = component._handle_annual_insurance(msg)
        assert result["premium"] == "10000.00"
        assert result["hull_rate"] == "0.10"

    def test_annual_missing_drone_id_raises(self, component_and_bus):
        component, _ = component_and_bus
        msg = {"action": "annual_insurance", "sender": "test",
               "payload": {"drone_value": 100_000, "drone_type": "delivery"}}
        with pytest.raises(ValueError, match="drone_id is required"):
            component._handle_annual_insurance(msg)

    def test_annual_zero_drone_value_raises(self, component_and_bus):
        component, _ = component_and_bus
        msg = {"action": "annual_insurance", "sender": "test",
               "payload": {"drone_id": "d1", "drone_value": 0, "drone_type": "delivery"}}
        with pytest.raises(ValueError, match="drone_value must be positive"):
            component._handle_annual_insurance(msg)

    def test_kfleet_history_no_stats(self, component_and_bus):
        """Менее 10 вылетов → Kfleet_history = 1.0."""
        component, _ = component_and_bus
        assert component._get_kfleet_history("new-drone") == Decimal("1.0")

    def test_kfleet_history_high_accident_rate(self, component_and_bus):
        """Аварийность > 5% → Kfleet_history = 1.5."""
        component, _ = component_and_bus
        component._drone_stats["bad-drone"] = {"total_missions": 20, "incidents": 2}
        assert component._get_kfleet_history("bad-drone") == Decimal("1.5")

    def test_kfleet_history_excellent_fleet(self, component_and_bus):
        """> 100 вылетов, аварийность < 2% → Kfleet_history = 0.8."""
        component, _ = component_and_bus
        component._drone_stats["great-drone"] = {"total_missions": 200, "incidents": 1}
        assert component._get_kfleet_history("great-drone") == Decimal("0.8")


# ---------------------------------------------------------------------------
# Миссионное страхование (Pmission)
# ---------------------------------------------------------------------------

class TestMissionInsurance:
    """Pmission = Vcargo × Rrisk_class × Kenv × Kincident_history"""

    def test_mission_new_delivery_drone_defaults(self, component_and_bus):
        """
        Новый дрон-доставщик, без статистики:
          Rrisk_class=0.08, Kenv=1.0, Kincident_history=1.0
          Pmission = 10_000 × 0.08 × 1.0 × 1.0 = 800.
        """
        component, _ = component_and_bus
        msg = {
            "action": "mission_insurance",
            "sender": "test",
            "payload": {
                "order_id": "order-001",
                "drone_id": "drone-d-001",
                "cargo_value": 10_000,
                "drone_type": "delivery",
            },
        }
        result = component._handle_mission_insurance(msg)
        assert result["status"] == "active"
        assert result["policy_type"] == "mission"
        assert result["premium"] == "800.00"
        assert result["risk_class_rate"] == "0.08"
        assert result["kenv"] == "1.0"
        assert result["kincident_history"] == "1.0"

    def test_mission_inspector_drone(self, component_and_bus):
        """
        Инспектор: Rrisk_class=0.01, Kenv=1.5.
        Pmission = 5_000 × 0.01 × 1.5 × 1.0 = 75.
        """
        component, _ = component_and_bus
        msg = {
            "action": "mission_insurance",
            "sender": "test",
            "payload": {
                "order_id": "order-002",
                "drone_id": "drone-i-001",
                "cargo_value": 5_000,
                "drone_type": "inspector",
                "env_factor": 1.5,
            },
        }
        result = component._handle_mission_insurance(msg)
        assert result["premium"] == "75.00"

    def test_mission_firefighter_drone(self, component_and_bus):
        """
        Огнеборец: Rrisk_class=0.12, Kenv=2.0.
        Pmission = 50_000 × 0.12 × 2.0 × 1.0 = 12_000.
        """
        component, _ = component_and_bus
        msg = {
            "action": "mission_insurance",
            "sender": "test",
            "payload": {
                "order_id": "order-003",
                "drone_id": "drone-f-001",
                "cargo_value": 50_000,
                "drone_type": "firefighter",
                "env_factor": 2.0,
            },
        }
        result = component._handle_mission_insurance(msg)
        assert result["premium"] == "12000.00"

    def test_mission_increments_total_missions(self, component_and_bus):
        """После оформления миссионного полиса счётчик вылетов растёт."""
        component, _ = component_and_bus
        drone_id = "drone-count-001"
        base_msg = lambda oid: {
            "action": "mission_insurance",
            "sender": "test",
            "payload": {
                "order_id": oid,
                "drone_id": drone_id,
                "cargo_value": 1_000,
                "drone_type": "delivery",
            },
        }
        component._handle_mission_insurance(base_msg("o1"))
        component._handle_mission_insurance(base_msg("o2"))
        assert component._drone_stats[drone_id]["total_missions"] == 2

    def test_mission_missing_order_id_raises(self, component_and_bus):
        component, _ = component_and_bus
        msg = {"action": "mission_insurance", "sender": "test",
               "payload": {"drone_id": "d1", "cargo_value": 1_000, "drone_type": "delivery"}}
        with pytest.raises(ValueError, match="order_id is required"):
            component._handle_mission_insurance(msg)

    def test_mission_zero_cargo_value_raises(self, component_and_bus):
        component, _ = component_and_bus
        msg = {"action": "mission_insurance", "sender": "test",
               "payload": {"order_id": "o1", "drone_id": "d1", "cargo_value": 0, "drone_type": "delivery"}}
        with pytest.raises(ValueError, match="cargo_value must be positive"):
            component._handle_mission_insurance(msg)

    def test_kincident_history_new_drone(self, component_and_bus):
        """Новый дрон, 0 вылетов → Kincident_history = Kbase = 1.0."""
        component, _ = component_and_bus
        assert component._calculate_kincident_history("new-drone") == Decimal("1.0")

    def test_kincident_history_with_incidents(self, component_and_bus):
        """
        5 инцидентов из 20 вылетов, L=1.0:
        Kincident = 1.0 + (5/20) × 1.0 = 1.25
        """
        component, _ = component_and_bus
        component._drone_stats["drone-x"] = {"total_missions": 20, "incidents": 5}
        k = component._calculate_kincident_history("drone-x")
        assert k == Decimal("1.2500")


# ---------------------------------------------------------------------------
# Инциденты и завершение полисов
# ---------------------------------------------------------------------------

class TestIncidentsAndTermination:

    def test_report_incident_updates_drone_stats(self, component_and_bus):
        """Инцидент увеличивает счётчик incidents у дрона."""
        component, _ = component_and_bus

        # Создаём миссионный полис
        component._policies["p1"] = {
            "id": "p1",
            "order_id": "o1",
            "drone_id": "drone-001",
            "operator_id": "op1",
            "status": "active",
        }
        component._drone_stats["drone-001"] = {"total_missions": 5, "incidents": 0}

        msg = {
            "action": "report_incident",
            "sender": "test",
            "payload": {
                "order_id": "o1",
                "drone_id": "drone-001",
                "damage_amount": 2000,
            },
        }
        result = component._handle_incident(msg)
        assert result["status"] == "processed"
        assert component._drone_stats["drone-001"]["incidents"] == 1

    def test_report_incident_updates_kincident_history(self, component_and_bus):
        """После инцидента Kincident_history пересчитывается."""
        component, _ = component_and_bus

        component._policies["p1"] = {
            "id": "p1", "order_id": "o1",
            "drone_id": "drone-002", "operator_id": "op1", "status": "active",
        }
        # 10 вылетов, 0 инцидентов → после инцидента: 10 вылетов, 1 инцидент
        component._drone_stats["drone-002"] = {"total_missions": 10, "incidents": 0}

        msg = {
            "action": "report_incident",
            "sender": "test",
            "payload": {"order_id": "o1", "drone_id": "drone-002", "damage_amount": 500},
        }
        result = component._handle_incident(msg)
        # Kincident = 1.0 + (1/10) × 1.0 = 1.1
        assert result["new_kincident_history"] == "1.1000"

    def test_terminate_policy(self, component_and_bus):
        component, _ = component_and_bus

        component._policies["p1"] = {"id": "p1", "order_id": "o1", "status": "active"}

        msg = {"action": "terminate_policy", "sender": "test", "payload": {"order_id": "o1"}}
        result = component._handle_terminate(msg)
        assert result["status"] == "terminated"
        assert component._policies["p1"]["status"] == "terminated"

    def test_terminate_nonexistent_policy_raises(self, component_and_bus):
        component, _ = component_and_bus
        msg = {"action": "terminate_policy", "sender": "test", "payload": {"order_id": "nonexistent"}}
        with pytest.raises(ValueError, match="no active policy"):
            component._handle_terminate(msg)


# ---------------------------------------------------------------------------
# Legacy (обратная совместимость)
# ---------------------------------------------------------------------------

class TestLegacyHandlers:

    def test_calculate_policy_default_kbm(self, component_and_bus):
        component, _ = component_and_bus
        msg = {
            "action": "calculate_policy",
            "sender": "test",
            "payload": {"manufacturer_id": "m1", "operator_id": "op1"},
        }
        result = component._handle_calculate_legacy(msg)
        assert result["calculated_cost"] == "1000.00"
        assert result["manufacturer_kbm"] == "1.00"
        assert result["operator_kbm"] == "1.00"

    def test_purchase_policy_legacy(self, component_and_bus):
        component, _ = component_and_bus
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
        result = component._handle_purchase_legacy(msg)
        assert result["status"] == "active"
        assert "policy_id" in result
        assert result["order_id"] == "o1"


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

def test_gateway_routes_to_component(gateway_and_bus):
    gw, bus = gateway_and_bus
    bus.request.return_value = {
        "success": True,
        "payload": {"premium": "800.00"},
    }

    msg = {"action": "mission_insurance", "sender": "external", "payload": {}}
    result = gw._handle_proxy(msg)
    assert "premium" in result
    bus.request.assert_called_once()
