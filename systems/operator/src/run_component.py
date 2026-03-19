"""
Скрипт для запуска компонентов системы Эксплуатант
"""

import asyncio
import logging
import os
import sys

from broker.src.bus_factory import create_system_bus
from systems.operator.src.business_logic import BusinessLogic
from systems.operator.src.fleet_manager import FleetManager
from systems.operator.src.mission_planner import MissionPlanner
from systems.operator.src.operator_system import OperatorSystem
from systems.operator.src.security_monitor import SecurityMonitor
from systems.operator.src.event_journal.src.event_journal import EventJournal

# Настройка логирования
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_bus():
    """Создание системной шины"""
    system_id = os.getenv("SYSTEM_ID", "operator-001")
    component_type = os.getenv("COMPONENT_TYPE", "operator_system")
    broker_type = os.getenv("BROKER_TYPE", "mqtt")
    bus = create_system_bus(
        bus_type=broker_type,
        client_id=f"{system_id}.{component_type}",
    )
    bus.start()
    return bus


async def run_component():
    """Запуск компонента в зависимости от переменной окружения"""
    component_type = os.getenv("COMPONENT_TYPE", "operator_system")
    component_id = os.getenv("COMPONENT_ID", f"{component_type}-01")

    logger.info(f"Starting component: {component_type} with ID: {component_id}")

    # Создаём системную шину
    bus = create_bus()

    # Создаём компонент
    component = None

    try:
        if component_type == "security_monitor":
            component = SecurityMonitor(component_id, bus)
        elif component_type == "fleet_manager":
            component = FleetManager(component_id, bus)
        elif component_type == "event_journal":
            component = EventJournal(component_id, bus)
        elif component_type == "mission_planner":
            component = MissionPlanner(component_id, bus)
        elif component_type == "business_logic":
            component = BusinessLogic(component_id, bus)
        elif component_type == "operator_system":
            component = OperatorSystem(component_id, bus)
        else:
            raise ValueError(f"Unknown component type: {component_type}")

        logger.info(f"Component {component_id} created successfully")

        # Запускаем компонент (sync API BaseComponent/SecurityMonitor)
        start_result = component.start()
        if asyncio.iscoroutine(start_result):
            await start_result
        logger.info(f"Component {component_id} started successfully")

        # Ждём завершения
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")

    except Exception as e:
        logger.error(f"Error running component: {e}", exc_info=True)
        raise

    finally:
        # Останавливаем компонент
        if component:
            stop_result = component.stop()
            if asyncio.iscoroutine(stop_result):
                await stop_result
            logger.info(f"Component {component_id} stopped")

        # Останавливаем шину
        bus.stop()
        logger.info("System bus stopped")


def main():
    """Точка входа"""
    try:
        asyncio.run(run_component())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
