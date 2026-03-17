#!/usr/bin/env python3
"""
Точка входа для компонента Business Logic
"""
import os
import sys
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(project_root))

from broker.bus_factory import BusFactory
from systems.operator.src.business_logic.src.business_logic import BusinessLogic


def main():
    """Запуск компонента Business Logic"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Получение конфигурации из переменных окружения
    component_id = os.getenv("COMPONENT_ID", "business-logic-001")
    broker_type = os.getenv("BROKER_TYPE", "mqtt")
    broker_host = os.getenv("BROKER_HOST", "localhost")
    broker_port = int(os.getenv("BROKER_PORT", "1883"))
    
    logger.info(f"Starting Business Logic component {component_id}")
    logger.info(f"Broker: {broker_type} at {broker_host}:{broker_port}")
    
    try:
        # Создание системной шины
        bus = BusFactory.create_bus(
            broker_type=broker_type,
            host=broker_host,
            port=broker_port
        )
        
        # Создание и запуск компонента
        component = BusinessLogic(
            component_id=component_id,
            bus=bus
        )
        
        logger.info("Business Logic component started successfully")
        component.start()
        
    except KeyboardInterrupt:
        logger.info("Shutting down Business Logic component...")
    except Exception as e:
        logger.error(f"Failed to start Business Logic component: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()