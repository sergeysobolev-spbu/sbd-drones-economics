from systems.operator.src.fleet_manager.src.fleet_manager_core import FleetManagerCore
from systems.operator.src.fleet_manager.src.fleet_manager_service import FleetManagerService
from systems.operator.src.operator_clients import DeveloperClient, RegulatorClient


class DummyBus:
    def request(self, *_, **__):
        raise RuntimeError("not used in this unit test")


def test_find_suitable_agro_uas_from_catalog():
    """
    Проверяет, что для аграрного заказа подбирается агродрон DW-AG300
    из YAML-каталога разработчиков.
    """
    bus = DummyBus()
    regulator = RegulatorClient(bus)
    developer = DeveloperClient(bus, regulator)

    core = FleetManagerCore()
    service = FleetManagerService(core=core, developer_client=developer, regulator_client=regulator)

    # Инициализируем парк на основе каталога разработчиков
    service.initialize_fleet()

    # Требования под аграрный заказ (опрыскивание поля)
    requirements = {
        "min_payload": 10.0,
        "min_range": 10.0,
        "category": "agro",
    }

    suitable = service._filter_suitable_uas(
        fleet=service._fleet_extended,  # type: ignore[attr-defined]
        requirements=requirements,
    )

    assert suitable, "ожидается хотя бы один подходящий агродрон"
    model_ids = {u.model_id for u in suitable}
    assert "DW-AG300" in model_ids
