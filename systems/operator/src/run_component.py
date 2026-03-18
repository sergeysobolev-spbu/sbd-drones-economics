"""
Скрипт для запуска компонентов системы Эксплуатант
"""
import os
import sys
import logging
import asyncio
from typing import Optional

# Добавляем пути для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from broker.kafka.kafka_system_bus import KafkaSystemBus

from src.security_monitor import SecurityMonitor
from src.fleet_manager import FleetManager
from src.mission_planner import MissionPlanner
from src.business_logic import BusinessLogic
from src.operator_system import OperatorSystem


# Настройка логирования
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_system_bus() -> KafkaSystemBus:
    """Создание системной шины"""
    system_id = os.getenv("SYSTEM_ID", "operator-001")
    component_type = os.getenv("COMPONENT_TYPE", "operator_system")
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    bus = KafkaSystemBus(
        bootstrap_servers=bootstrap_servers,
        client_id=f"{system_id}.{component_type}",
        group_id=f"{system_id}-{component_type}",
    )
    bus.start()
    return bus


async def run_component():
    """Запуск компонента в зависимости от переменной окружения"""
    component_type = os.getenv("COMPONENT_TYPE", "operator_system")
    component_id = os.getenv("COMPONENT_ID", f"{component_type}-01")
    
    logger.info(f"Starting component: {component_type} with ID: {component_id}")
    
    # Создаём системную шину
    bus = create_system_bus()
    
    # Создаём компонент
    component = None
    
    try:
        if component_type == "security_monitor":
            component = SecurityMonitor(component_id, bus)
        elif component_type == "fleet_manager":
            component = FleetManager(component_id, bus)
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