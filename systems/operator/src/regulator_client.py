"""
Клиент для взаимодействия с Регулятором
"""
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from broker.system_bus import SystemBus


@dataclass
class SystemTopicInfo:
    """Информация о топике системы"""
    system_id: str
    system_type: str
    topic: str
    active: bool
    registered_at: str


class RegulatorClient:
    """
    Клиент для взаимодействия с Регулятором
    
    Отвечает за:
    - Получение топиков внешних систем
    - Регистрацию в системе
    - Получение актуальной информации о системах
    """
    
    def __init__(self, bus: SystemBus):
        self.bus = bus
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # В тестовых целях используем переменные окружения
        self.use_env_topics = os.getenv("USE_ENV_TOPICS", "true").lower() == "true"
        
        # Кеш топиков систем
        self.topics_cache: Dict[str, SystemTopicInfo] = {}
        self.cache_updated_at: Optional[datetime] = None
        
    async def get_system_topics(self) -> Dict[str, SystemTopicInfo]:
        """Получить топики всех систем от Регулятора"""
        if self.use_env_topics:
            return self._get_topics_from_env()
        
        try:
            # В реальной системе здесь был бы запрос к Регулятору
            response = await self.bus.request(
                "regulator.system",
                {
                    "action": "get_system_topics",
                    "sender": "operator.system",
                    "payload": {}
                },
                timeout=10.0
            )
            
            if response and response.get("success"):
                topics_data = response.get("payload", {}).get("topics", {})
                self._update_cache(topics_data)
                return self.topics_cache
            
        except Exception as e:
            self.logger.error(f"Failed to get topics from Regulator: {e}")
        
        # Fallback на переменные окружения
        return self._get_topics_from_env()
    
    def _get_topics_from_env(self) -> Dict[str, SystemTopicInfo]:
        """Получить топики из переменных окружения (для тестов)"""
        topics = {}
        
        # Агрегатор
        aggregator_id = os.getenv("AGGREGATOR_ID", "aggregator-001")
        topics["aggregator"] = SystemTopicInfo(
            system_id=aggregator_id,
            system_type="aggregator",
            topic=f"aggregator.{aggregator_id}",
            active=True,
            registered_at=datetime.utcnow().isoformat()
        )
        
        # Разработчики БАС
        developers_ids = os.getenv("DEVELOPERS_IDS", "dev-001,dev-002").split(",")
        for dev_id in developers_ids:
            topics[f"developer_{dev_id}"] = SystemTopicInfo(
                system_id=dev_id.strip(),
                system_type="developer",
                topic=f"developer.{dev_id.strip()}",
                active=True,
                registered_at=datetime.utcnow().isoformat()
            )
        
        # Страховые компании
        insurance_ids = os.getenv("INSURANCE_IDS", "ins-001,ins-002").split(",")
        for ins_id in insurance_ids:
            topics[f"insurance_{ins_id}"] = SystemTopicInfo(
                system_id=ins_id.strip(),
                system_type="insurance",
                topic=f"insurance.{ins_id.strip()}",
                active=True,
                registered_at=datetime.utcnow().isoformat()
            )
        
        # ОрВД (UTM)
        utm_id = os.getenv("UTM_ID", "utm-001")
        topics["utm"] = SystemTopicInfo(
            system_id=utm_id,
            system_type="utm",
            topic=f"utm.{utm_id}",
            active=True,
            registered_at=datetime.utcnow().isoformat()
        )
        
        self._update_cache(topics)
        return self.topics_cache
    
    def _update_cache(self, topics_data: Dict[str, Any]):
        """Обновить кеш топиков"""
        self.topics_cache.clear()
        
        for key, data in topics_data.items():
            if isinstance(data, SystemTopicInfo):
                self.topics_cache[key] = data
            else:
                # Преобразуем из словаря
                self.topics_cache[key] = SystemTopicInfo(**data)
        
        self.cache_updated_at = datetime.utcnow()
        self.logger.info(f"Topics cache updated with {len(self.topics_cache)} entries")
    
    def get_topic_for_system(self, system_type: str) -> Optional[str]:
        """Получить топик для конкретного типа системы"""
        for info in self.topics_cache.values():
            if info.system_type == system_type and info.active:
                return info.topic
        return None
    
    def get_all_topics_by_type(self, system_type: str) -> List[str]:
        """Получить все топики систем определённого типа"""
        topics = []
        for info in self.topics_cache.values():
            if info.system_type == system_type and info.active:
                topics.append(info.topic)
        return topics
    
    async def register_with_regulator(self, operator_info: Dict[str, Any]) -> bool:
        """Зарегистрировать Эксплуатанта в Регуляторе"""
        if self.use_env_topics:
            # В тестовом режиме считаем регистрацию успешной
            self.logger.info("Test mode: registration skipped")
            return True
        
        try:
            response = await self.bus.request(
                "regulator.system",
                {
                    "action": "register_operator",
                    "sender": "operator.system",
                    "payload": operator_info
                },
                timeout=10.0
            )
            
            if response and response.get("success"):
                self.logger.info("Successfully registered with Regulator")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to register with Regulator: {e}")
        
        return False