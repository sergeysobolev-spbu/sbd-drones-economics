"""
Fleet Manager Component - точка входа
"""
import os
import sys
import logging
import asyncio
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(root_dir))

from broker.bus_factory import BusFactory
from systems.operator.src.fleet_manager.src.fleet_manager import FleetManager
from systems.operator.src.developer_client import DeveloperClient
from systems.operator.src.regulator_client import RegulatorClient


def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def main():
    """Главная функция"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Получаем конфигурацию из переменных окружения
    component_id = os.getenv("COMPONENT_ID", "fleet_manager_01")
    broker_type = os.getenv("BROKER_TYPE", "mqtt")
    broker_host = os.getenv("BROKER_HOST", "localhost")
    broker_port = int(os.getenv("BROKER_PORT", "1883"))
    
    logger.info(f"Starting Fleet Manager {component_id}")
    logger.info(f"Broker: {broker_type}://{broker_host}:{broker_port}")
    
    try:
        # Создаём системную шину
        bus = BusFactory.create_bus(
            broker_type=broker_type,
            host=broker_host,
            port=broker_port
        )
        
        # Создаём клиенты для внешних систем
        regulator_client = RegulatorClient(bus)
        developer_client = DeveloperClient(bus, regulator_client)
        
        # Конфигурация компонента
        config = {
            "topic": os.getenv("FLEET_MANAGER_TOPIC", "operator.fleet_manager"),
            "developer_client": developer_client,
            "regulator_client": regulator_client
        }
        
        # Создаём и запускаем компонент
        fleet_manager = FleetManager(
            component_id=component_id,
            bus=bus,
            config=config
        )
        
        # Запускаем компонент
        await fleet_manager.start()
        
        logger.info(f"Fleet Manager {component_id} started successfully")
        
        # Ждём завершения
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        
        # Останавливаем компонент
        await fleet_manager.stop()
        logger.info(f"Fleet Manager {component_id} stopped")
        
    except Exception as e:
        logger.error(f"Failed to start Fleet Manager: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())