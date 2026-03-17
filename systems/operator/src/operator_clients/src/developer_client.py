"""
Клиент для взаимодействия с Разработчиками БАС
"""
import os
import yaml
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from broker.system_bus import SystemBus
from systems.operator.src.topics import SystemTopics


class UASCategory(str, Enum):
    """Категории БАС"""

    LIGHT_CARGO = "light_cargo"
    HEAVY_CARGO = "heavy_cargo"
    AGRO = "agro"
    INSPECTOR = "inspector"
    SURVEILLANCE = "surveillance"


@dataclass
class UASModel:
    """Модель БАС от разработчика"""

    model_id: str
    name: str
    category: UASCategory
    manufacturer: str
    specifications: Dict[str, Any]
    price: float
    certification: Dict[str, Any]
    safety_features: List[str] = field(default_factory=list)
    available_quantity: int = 0
    delivery_time_days: int = 30


@dataclass
class DeveloperCatalog:
    """Каталог БАС от разработчика"""

    developer_id: str
    developer_name: str
    models: List[UASModel]
    updated_at: str
    contact_info: Dict[str, str]


class DeveloperClient:
    """
    Клиент для взаимодействия с Разработчиками БАС

    Отвечает за:
    - Получение каталогов БАС от разработчиков
    - Запрос на покупку БАС
    - Проверку сертификации
    """

    def __init__(self, bus: SystemBus, regulator_client):
        self.bus = bus
        self.regulator_client = regulator_client
        self.logger = logging.getLogger(self.__class__.__name__)

        # В тестовых целях используем YAML файл
        self.use_yaml_catalog = os.getenv("USE_YAML_CATALOG", "true").lower() == "true"
        self.yaml_catalog_path = os.getenv(
            "DEVELOPERS_CATALOG_PATH",
            "operator_clients/resources/developers_catalog.yaml",
        )

        # Кеш каталогов разработчиков
        self.catalogs_cache: Dict[str, DeveloperCatalog] = {}

    async def get_all_catalogs(self) -> Dict[str, DeveloperCatalog]:
        """Получить каталоги всех доступных разработчиков"""
        if self.use_yaml_catalog:
            return self._load_catalogs_from_yaml()

        # Получаем топики разработчиков от регулятора
        developer_topics = self.regulator_client.get_all_topics_by_type("developer")

        catalogs: Dict[str, DeveloperCatalog] = {}
        for topic in developer_topics:
            try:
                catalog = await self._request_catalog(topic)
                if catalog:
                    catalogs[catalog.developer_id] = catalog
            except Exception as e:
                self.logger.error(f"Failed to get catalog from {topic}: {e}")

        self.catalogs_cache = catalogs
        return catalogs

    async def _request_catalog(self, developer_topic: str) -> Optional[DeveloperCatalog]:
        """Запросить каталог у конкретного разработчика"""
        try:
            response = await self.bus.request(
                developer_topic,
                {
                    "action": "get_catalog",
                    "sender": SystemTopics.get_operator(),
                    "payload": {
                        "operator_id": os.getenv("OPERATOR_ID", "operator-001"),
                        "request_full_catalog": True,
                    },
                },
                timeout=10.0,
            )

            if response and response.get("success"):
                catalog_data = response.get("payload", {})
                return self._parse_catalog(catalog_data)

        except Exception as e:
            self.logger.error(f"Failed to request catalog: {e}")

        return None

    def _load_catalogs_from_yaml(self) -> Dict[str, DeveloperCatalog]:
        """Загрузить каталоги из YAML файла (для тестов)"""
        try:
            # Проверяем путь относительно корня проекта
            yaml_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                self.yaml_catalog_path,
            )

            if not os.path.exists(yaml_path):
                # Если файл не существует, создаём его с примером
                self._create_example_yaml(yaml_path)

            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            catalogs: Dict[str, DeveloperCatalog] = {}
            for dev_data in data.get("developers", []):
                catalog = self._parse_catalog(dev_data)
                if catalog:
                    catalogs[catalog.developer_id] = catalog

            self.catalogs_cache = catalogs
            return catalogs

        except Exception as e:
            self.logger.error(f"Failed to load catalogs from YAML: {e}")
            return {}

    def _parse_catalog(self, data: Dict[str, Any]) -> Optional[DeveloperCatalog]:
        """Парсить данные каталога"""
        try:
            models: List[UASModel] = []
            for model_data in data.get("models", []):
                model = UASModel(
                    model_id=model_data["model_id"],
                    name=model_data["name"],
                    category=UASCategory(model_data["category"]),
                    manufacturer=model_data["manufacturer"],
                    specifications=model_data["specifications"],
                    price=model_data["price"],
                    certification=model_data["certification"],
                    safety_features=model_data.get("safety_features", []),
                    available_quantity=model_data.get("available_quantity", 0),
                    delivery_time_days=model_data.get("delivery_time_days", 30),
                )
                models.append(model)

            return DeveloperCatalog(
                developer_id=data["developer_id"],
                developer_name=data["developer_name"],
                models=models,
                updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
                contact_info=data.get("contact_info", {}),
            )

        except Exception as e:
            self.logger.error(f"Failed to parse catalog: {e}")
            return None

    def _create_example_yaml(self, yaml_path: str):
        """Создать пример YAML файла с каталогами"""
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)

        example_data = {
            "developers": [
                {
                    "developer_id": "dev-001",
                    "developer_name": "AeroTech Solutions",
                    "updated_at": datetime.utcnow().isoformat(),
                    "contact_info": {"email": "sales@aerotech.com", "phone": "+7-495-123-4567"},
                    "models": [
                        {
                            "model_id": "AT-LC100",
                            "name": "CargoLite 100",
                            "category": "light_cargo",
                            "manufacturer": "AeroTech Solutions",
                            "specifications": {
                                "max_payload_kg": 5.0,
                                "max_range_km": 50.0,
                                "cruise_speed_kmh": 60.0,
                                "max_altitude_m": 500.0,
                                "battery_capacity_wh": 500.0,
                                "dimensions": {"length_m": 1.2, "width_m": 1.5, "height_m": 0.4},
                            },
                            "price": 150000.0,
                            "certification": {
                                "type": "Type Certificate",
                                "number": "TC-2024-001",
                                "issued_by": "Regulator",
                                "valid_until": "2029-01-01",
                            },
                            "safety_features": [
                                "Redundant flight controller",
                                "Parachute recovery system",
                                "Obstacle avoidance sensors",
                                "RTH (Return to Home) function",
                            ],
                            "available_quantity": 10,
                            "delivery_time_days": 14,
                        }
                    ],
                }
            ]
        }

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(example_data, f, allow_unicode=True, sort_keys=False)

        self.logger.info(f"Created example YAML catalog at {yaml_path}")

    def find_best_uas_for_requirements(self, requirements: Dict[str, Any]) -> List[UASModel]:
        """Найти лучшие модели БАС по требованиям (из кэша)"""
        category = requirements.get("category")
        min_payload = requirements.get("min_payload", 0)
        min_range = requirements.get("min_range", 0)

        candidates: List[UASModel] = []
        for catalog in self.catalogs_cache.values():
            for model in catalog.models:
                if category and model.category.value != category:
                    continue
                if model.specifications.get("max_payload_kg", 0) < min_payload:
                    continue
                if model.specifications.get("max_range_km", 0) < min_range:
                    continue
                candidates.append(model)

        candidates.sort(key=lambda m: m.price)
        return candidates

    async def purchase_uas(
        self, developer_id: str, model_id: str, quantity: int = 1
    ) -> Dict[str, Any]:
        """Запросить покупку БАС у разработчика"""
        if developer_id not in self.catalogs_cache:
            await self.get_all_catalogs()

        catalog = self.catalogs_cache.get(developer_id)
        if not catalog:
            return {"success": False, "error": "Developer not found"}

        model = next((m for m in catalog.models if m.model_id == model_id), None)
        if not model:
            return {"success": False, "error": "Model not found"}

        if model.available_quantity < quantity:
            return {
                "success": False,
                "error": "Insufficient quantity available",
                "available": model.available_quantity,
            }

        model.available_quantity -= quantity
        return {
            "success": True,
            "order_id": f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "developer_id": developer_id,
            "model_id": model_id,
            "quantity": quantity,
            "total_price": model.price * quantity,
            "estimated_delivery": datetime.utcnow().isoformat(),
            "delivery_days": model.delivery_time_days,
        }

