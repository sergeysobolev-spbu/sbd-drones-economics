"""
Точка входа для запуска компонента Mission Planner
"""
import os
import sys
import asyncio
import logging

# Добавляем путь к корню проекта для импортов
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from broker.system_bus import SystemBus
from systems.operator.src.mission_planner.src.mission_planner import MissionPlanner
from systems.operator.src.topics import ComponentTopics


def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Добавляем фильтр для добавления trace_id если его нет
    class TraceIdFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, 'trace_id'):
                record.trace_id = 'no-trace'
            return True
    
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(TraceIdFilter())


async def main():
    """Основная функция запуска компонента"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Получаем конфигурацию из переменных окружения
    component_id = os.environ.get('COMPONENT_ID', 'mission-planner-001')
    broker_type = os.environ.get('BROKER_TYPE', 'mqtt')
    broker_host = os.environ.get('BROKER_HOST', 'localhost')
    broker_port = int(os.environ.get('BROKER_PORT', '1883'))
    
    logger.info(f"Starting Mission Planner component: {component_id}")
    logger.info(f"Broker: {broker_type}://{broker_host}:{broker_port}")
    
    # Создаем системную шину
    bus = SystemBus.create(
        broker_type=broker_type,
        host=broker_host,
        port=broker_port
    )
    
    # Получаем топик компонента
    topic = ComponentTopics.get_mission_planner()
    logger.info(f"Component topic: {topic}")
    
    # Создаем и запускаем компонент
    mission_planner = MissionPlanner(
        component_id=component_id,
        bus=bus
    )
    
    try:
        # Запускаем компонент
        mission_planner.start()
        logger.info("Mission Planner started successfully")
        
        # Держим компонент запущенным
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Error in Mission Planner: {e}", exc_info=True)
    finally:
        # Останавливаем компонент
        mission_planner.stop()
        logger.info("Mission Planner stopped")


if __name__ == "__main__":
    asyncio.run(main())