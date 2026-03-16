"""
Юнит-тесты для DeveloperClient
"""
import os
import pytest
import tempfile
import yaml
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from systems.operator.src.developer_client import (
    DeveloperClient, UASModel, UASCategory, DeveloperCatalog
)


class TestDeveloperClient:
    """Тесты для клиента Разработчиков БАС"""
    
    @pytest.fixture
    def mock_bus(self):
        """Mock для SystemBus"""
        bus = Mock()
        bus.request = AsyncMock()
        return bus
    
    @pytest.fixture
    def mock_regulator_client(self):
        """Mock для RegulatorClient"""
        client = Mock()
        client.get_all_topics_by_type = Mock(return_value=['developer.dev-001', 'developer.dev-002'])
        client.get_topic_for_system = Mock(return_value='developer.dev-001')
        return client
    
    @pytest.fixture
    def client(self, mock_bus, mock_regulator_client):
        """Создание клиента для тестов"""
        return DeveloperClient(mock_bus, mock_regulator_client)
    
    @pytest.fixture
    def sample_catalog_data(self):
        """Пример данных каталога"""
        return {
            "developers": [
                {
                    "developer_id": "dev-001",
                    "developer_name": "Test Developer",
                    "updated_at": "2024-01-01T00:00:00",
                    "contact_info": {
                        "email": "test@dev.com",
                        "phone": "+7-123-456-7890"
                    },
                    "models": [
                        {
                            "model_id": "TEST-001",
                            "name": "Test Drone",
                            "category": "light_cargo",
                            "manufacturer": "Test Developer",
                            "specifications": {
                                "max_payload_kg": 5.0,
                                "max_range_km": 50.0,
                                "cruise_speed_kmh": 60.0,
                                "max_altitude_m": 500.0
                            },
                            "price": 100000.0,
                            "certification": {
                                "type": "Type Certificate",
                                "number": "TC-TEST-001",
                                "issued_by": "Regulator",
                                "valid_until": "2029-01-01"
                            },
                            "safety_features": ["Feature 1", "Feature 2"],
                            "available_quantity": 10,
                            "delivery_time_days": 14
                        }
                    ]
                }
            ]
        }
    
    def test_init(self, mock_bus, mock_regulator_client):
        """Тест инициализации клиента"""
        client = DeveloperClient(mock_bus, mock_regulator_client)
        assert client.bus == mock_bus
        assert client.regulator_client == mock_regulator_client
        assert client.catalogs_cache == {}
        assert client.use_yaml_catalog is True
    
    @pytest.mark.asyncio
    async def test_get_all_catalogs_from_yaml(self, client, sample_catalog_data):
        """Тест получения каталогов из YAML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_catalog_data, f)
            temp_path = f.name
        
        try:
            client.yaml_catalog_path = temp_path
            catalogs = await client.get_all_catalogs()
            
            assert len(catalogs) == 1
            assert 'dev-001' in catalogs
            
            catalog = catalogs['dev-001']
            assert catalog.developer_id == 'dev-001'
            assert catalog.developer_name == 'Test Developer'
            assert len(catalog.models) == 1
            
            model = catalog.models[0]
            assert model.model_id == 'TEST-001'
            assert model.name == 'Test Drone'
            assert model.category == UASCategory.LIGHT_CARGO
            assert model.price == 100000.0
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_get_all_catalogs_from_api(self, client, mock_bus, mock_regulator_client):
        """Тест получения каталогов через API"""
        client.use_yaml_catalog = False
        
        # Настраиваем mock ответ
        mock_response = {
            'success': True,
            'payload': {
                'developer_id': 'dev-001',
                'developer_name': 'API Developer',
                'updated_at': '2024-01-01T00:00:00',
                'contact_info': {'email': 'api@dev.com'},
                'models': [
                    {
                        'model_id': 'API-001',
                        'name': 'API Drone',
                        'category': 'heavy_cargo',
                        'manufacturer': 'API Developer',
                        'specifications': {'max_payload_kg': 20.0},
                        'price': 200000.0,
                        'certification': {'valid_until': '2029-01-01'},
                        'safety_features': [],
                        'available_quantity': 5,
                        'delivery_time_days': 30
                    }
                ]
            }
        }
        mock_bus.request.return_value = mock_response
        
        catalogs = await client.get_all_catalogs()
        
        assert len(catalogs) == 2  # По количеству топиков от регулятора
        assert mock_bus.request.call_count == 2
    
    def test_parse_catalog(self, client):
        """Тест парсинга данных каталога"""
        data = {
            'developer_id': 'dev-test',
            'developer_name': 'Test Dev',
            'updated_at': '2024-01-01',
            'contact_info': {'email': 'test@test.com'},
            'models': [
                {
                    'model_id': 'M-001',
                    'name': 'Model 1',
                    'category': 'agro',
                    'manufacturer': 'Test',
                    'specifications': {},
                    'price': 50000.0,
                    'certification': {},
                    'safety_features': ['SF1'],
                    'available_quantity': 3,
                    'delivery_time_days': 7
                }
            ]
        }
        
        catalog = client._parse_catalog(data)
        
        assert catalog is not None
        assert catalog.developer_id == 'dev-test'
        assert len(catalog.models) == 1
        assert catalog.models[0].category == UASCategory.AGRO
    
    @pytest.mark.asyncio
    async def test_purchase_uas_success(self, client):
        """Тест успешной покупки БАС"""
        # Заполняем кеш
        client.catalogs_cache = {
            'dev-001': DeveloperCatalog(
                developer_id='dev-001',
                developer_name='Test Dev',
                models=[
                    UASModel(
                        model_id='M-001',
                        name='Test Model',
                        category=UASCategory.LIGHT_CARGO,
                        manufacturer='Test',
                        specifications={},
                        price=100000.0,
                        certification={},
                        available_quantity=5
                    )
                ],
                updated_at='2024-01-01',
                contact_info={}
            )
        }
        
        result = await client.purchase_uas('dev-001', 'M-001', 2)
        
        assert result['success'] is True
        assert 'order_id' in result
        assert result['quantity'] == 2
        assert result['total_price'] == 200000.0
    
    @pytest.mark.asyncio
    async def test_purchase_uas_developer_not_found(self, client):
        """Тест покупки БАС - разработчик не найден"""
        result = await client.purchase_uas('dev-999', 'M-001', 1)
        
        assert result['success'] is False
        assert result['error'] == 'Developer not found'
    
    @pytest.mark.asyncio
    async def test_purchase_uas_model_not_found(self, client):
        """Тест покупки БАС - модель не найдена"""
        client.catalogs_cache = {
            'dev-001': DeveloperCatalog(
                developer_id='dev-001',
                developer_name='Test Dev',
                models=[],
                updated_at='2024-01-01',
                contact_info={}
            )
        }
        
        result = await client.purchase_uas('dev-001', 'M-999', 1)
        
        assert result['success'] is False
        assert result['error'] == 'Model not found'
    
    @pytest.mark.asyncio
    async def test_purchase_uas_insufficient_quantity(self, client):
        """Тест покупки БАС - недостаточное количество"""
        client.catalogs_cache = {
            'dev-001': DeveloperCatalog(
                developer_id='dev-001',
                developer_name='Test Dev',
                models=[
                    UASModel(
                        model_id='M-001',
                        name='Test Model',
                        category=UASCategory.LIGHT_CARGO,
                        manufacturer='Test',
                        specifications={},
                        price=100000.0,
                        certification={},
                        available_quantity=2
                    )
                ],
                updated_at='2024-01-01',
                contact_info={}
            )
        }
        
        result = await client.purchase_uas('dev-001', 'M-001', 5)
        
        assert result['success'] is False
        assert result['error'] == 'Insufficient quantity available'
        assert result['available'] == 2
    
    def test_find_best_uas_for_requirements(self, client):
        """Тест поиска подходящих БАС по требованиям"""
        # Заполняем кеш
        client.catalogs_cache = {
            'dev-001': DeveloperCatalog(
                developer_id='dev-001',
                developer_name='Test Dev',
                models=[
                    UASModel(
                        model_id='M-001',
                        name='Light Model',
                        category=UASCategory.LIGHT_CARGO,
                        manufacturer='Test',
                        specifications={'max_payload_kg': 5.0, 'max_range_km': 50.0},
                        price=100000.0,
                        certification={'valid_until': '2029-01-01'},
                        safety_features=['Feature 1', 'Feature 2']
                    ),
                    UASModel(
                        model_id='M-002',
                        name='Heavy Model',
                        category=UASCategory.HEAVY_CARGO,
                        manufacturer='Test',
                        specifications={'max_payload_kg': 20.0, 'max_range_km': 30.0},
                        price=200000.0,
                        certification={'valid_until': '2029-01-01'},
                        safety_features=['Feature 1']
                    )
                ],
                updated_at='2024-01-01',
                contact_info={}
            )
        }
        
        # Тест 1: По грузоподъёмности
        requirements = {'min_payload': 10.0}
        models = client.find_best_uas_for_requirements(requirements)
        assert len(models) == 1
        assert models[0].model_id == 'M-002'
        
        # Тест 2: По категории
        requirements = {'category': UASCategory.LIGHT_CARGO}
        models = client.find_best_uas_for_requirements(requirements)
        assert len(models) == 1
        assert models[0].model_id == 'M-001'
        
        # Тест 3: По функциям безопасности
        requirements = {'required_safety_features': ['Feature 1', 'Feature 2']}
        models = client.find_best_uas_for_requirements(requirements)
        assert len(models) == 1
        assert models[0].model_id == 'M-001'
    
    def test_check_model_requirements(self, client):
        """Тест проверки соответствия модели требованиям"""
        model = UASModel(
            model_id='M-001',
            name='Test Model',
            category=UASCategory.LIGHT_CARGO,
            manufacturer='Test',
            specifications={'max_payload_kg': 5.0, 'max_range_km': 50.0},
            price=100000.0,
            certification={'valid_until': '2029-01-01'},
            safety_features=['Feature 1', 'Feature 2']
        )
        
        # Тест 1: Все требования выполнены
        requirements = {
            'category': UASCategory.LIGHT_CARGO,
            'min_payload': 3.0,
            'min_range': 30.0,
            'require_certification': True,
            'required_safety_features': ['Feature 1']
        }
        assert client._check_model_requirements(model, requirements) is True
        
        # Тест 2: Не подходит по категории
        requirements = {'category': UASCategory.HEAVY_CARGO}
        assert client._check_model_requirements(model, requirements) is False
        
        # Тест 3: Не подходит по грузоподъёмности
        requirements = {'min_payload': 10.0}
        assert client._check_model_requirements(model, requirements) is False
        
        # Тест 4: Не подходит по дальности
        requirements = {'min_range': 100.0}
        assert client._check_model_requirements(model, requirements) is False