"""
Точка входа для запуска компонента Security Monitor
"""
import os
import sys
import asyncio
import logging

# Добавляем путь к корню проекта для импортов
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from broker.system_bus import SystemBus
from systems.operator.src.security_monitor.src.security_monitor import SecurityMonitor
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
    component_id = os.environ.get('COMPONENT_ID', 'security-monitor-001')
    broker_type = os.environ.get('BROKER_TYPE', 'mqtt')
    broker_host = os.environ.get('BROKER_HOST', 'localhost')
    broker_port = int(os.environ.get('BROKER_PORT', '1883'))
    
    logger.info(f"Starting Security Monitor component: {component_id}")
    logger.info(f"Broker: {broker_type}://{broker_host}:{broker_port}")
    
    # Создаем системную шину
    bus = SystemBus.create(
        broker_type=broker_type,
        host=broker_host,
        port=broker_port
    )
    
    # Получаем топик компонента
    topic = ComponentTopics.get_security_monitor()
    logger.info(f"Component topic: {topic}")
    
    # Создаем и запускаем компонент
    security_monitor = SecurityMonitor(
        component_id=component_id,
        bus=bus
    )
    
    try:
        # Запускаем компонент
        security_monitor.start()
        logger.info("Security Monitor started successfully")
        
        # Держим компонент запущенным
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Error in Security Monitor: {e}", exc_info=True)
    finally:
        # Останавливаем компонент
        security_monitor.stop()
        logger.info("Security Monitor stopped")


if __name__ == "__main__":
    asyncio.run(main())