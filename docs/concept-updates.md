# Анализ изменений и доработка концепции

## Выявленные изменения в требованиях

### 1. Новые базовые требования к компонентам (БТ1-БТ8)
- **Множественные домены безопасности**: Компоненты могут содержать несколько доменов безопасности
- **Обязательный монитор безопасности**: Все междоменные взаимодействия должны проверяться
- **Повышенные требования к тестированию**:
  - Доверенные домены: ≥60% покрытия
  - Доверенные домены с повышением целостности: ≥70% покрытия включая зависимости
  - Недоверенные домены: ≥30% покрытия
- **Анализ уязвимостей**: Обязательная проверка всех зависимостей на известные уязвимости
- **Контейнеризация**: Каждый домен безопасности в отдельном Docker контейнере

### 2. Новые базовые требования к системам (БТ1-БТ13)
- **Сертификаты безопасности**: Системы должны иметь сертификаты с указанием целей безопасности
- **События безопасности**: Обязательная выдача событий безопасности по запросу
- **Телеметрия и аналитика**: Передача телеметрии и событий в сервис аналитики
- **Журналирование**: Все события с указанием уровня критичности

### 3. Уточнения по узлам системы
- **Количественные требования**:
  - Регулятор: только один
  - Разработчики БАС: минимум два
  - Эксплуатанты: минимум два
  - Страховые: минимум две с разными стратегиями
  - Дронопорты: минимум два
  - БАС: минимум два
- **Новые функции Регулятора**: Источник информации о топиках сертифицированных участников
- **Интерфейсы Регулятора**: REST API + web app для визуализации реестра
- **Типы БАС**: Конкретизированы 4 типа (доставщик лёгкий/тяжёлый, агродрон, инспектор)

### 4. Новый компонент SITL
- Симулятор для расчёта положения БАС
- Передача координат в формате NMEA
- Поддержка до 100 дронов одновременно

## Доработка концепции

### 1. Усиление архитектуры безопасности

#### Многоуровневая доменная модель
Вместо простого разделения на 4 домена, вводим иерархическую структуру:

```
D0_CRITICAL (Критически важные для безопасности)
├── D0.1_MEDIATION (Междоменная медиация)
│   ├── interdomain-gateway
│   └── audit-log
├── D0.2_POLICY (Политики безопасности)
│   ├── policy-repository
│   └── policy-validator
└── D0.3_CRYPTO (Криптографические сервисы)
    ├── certificate-manager
    └── signature-service

D1_TRUSTED (Доверенные операционные)
├── D1.1_FLIGHT_SAFETY (Безопасность полётов)
│   ├── uas-safety-monitor
│   └── collision-avoidance
├── D1.2_MISSION_CONTROL (Управление миссиями)
│   ├── mission-validator
│   └── route-optimizer
└── D1.3_COMPLIANCE (Соответствие требованиям)
    ├── regulation-checker
    └── insurance-validator

D2_OPERATIONAL (Операционные)
├── D2.1_BUSINESS (Бизнес-логика)
│   ├── ops-core
│   └── pricing-engine
└── D2.2_INTEGRATION (Интеграция)
    ├── external-api-gateway
    └── data-transformer

D3_UNTRUSTED (Недоверенные)
├── D3.1_EXTERNAL (Внешние сервисы)
│   ├── aggregator-sim
│   └── customer-portal
└── D3.2_SIMULATION (Симуляция)
    ├── sitl-adapter
    └── environment-sim
```

#### Монитор безопасности для каждой системы
Каждая система получает свой локальный монитор безопасности:

```python
class SystemSecurityMonitor:
    def __init__(self, system_id: str, policy_source: str):
        self.system_id = system_id
        self.policies = self.load_policies(policy_source)
        self.domain_trust_levels = self.define_trust_levels()
    
    def check_interaction(self, source_domain: str, 
                         target_domain: str, 
                         message: dict) -> Decision:
        # Проверка разрешённости взаимодействия
        if not self.is_allowed_path(source_domain, target_domain):
            return Decision.DENY
        
        # Проверка соответствия политикам
        applicable_policies = self.get_policies(source_domain, 
                                              target_domain, 
                                              message['type'])
        
        for policy in applicable_policies:
            if not policy.evaluate(message):
                return Decision.DENY
                
        return Decision.ALLOW
```

### 2. Сервис аналитики и мониторинга

Новый компонент для сбора и анализа телеметрии:

```yaml
analytics-service:
  components:
    - telemetry-collector:
        functions:
          - Сбор телеметрии от всех систем
          - Нормализация данных
          - Буферизация для пакетной обработки
    
    - security-event-processor:
        functions:
          - Обработка событий безопасности в реальном времени
          - Корреляция событий
          - Выявление аномалий
    
    - metrics-aggregator:
        functions:
          - Расчёт KPI систем
          - Формирование дашбордов
          - Генерация отчётов
    
    - alert-manager:
        functions:
          - Управление правилами алертинга
          - Эскалация инцидентов
          - Интеграция с системами оповещения
```

### 3. Управление сертификатами и доверием

#### Расширенная модель сертификатов
```json
{
  "certificate_id": "CERT-2024-001",
  "system_id": "OPS-DRONE-DELIVERY",
  "version": "1.2.3",
  "issued_by": "REGULATOR-001",
  "issued_at": "2024-03-16T10:00:00Z",
  "valid_until": "2025-03-16T10:00:00Z",
  "security_goals": [
    {
      "id": "SG-001",
      "description": "Предотвращение столкновений",
      "verification_method": "formal_proof",
      "test_coverage": 85
    }
  ],
  "trust_domains": {
    "D0_CRITICAL": {
      "components": ["safety-monitor", "crypto-service"],
      "test_coverage": 78,
      "vulnerability_scan": "PASSED"
    }
  },
  "dependencies": [
    {
      "package": "cryptography==41.0.0",
      "vulnerabilities": [],
      "last_scan": "2024-03-15T12:00:00Z"
    }
  ],
  "signature": "..."
}
```

#### API Регулятора для управления топиками
```python
# GET /api/v1/registry/topics
{
  "aggregators": [
    {
      "id": "AGG-001",
      "name": "DroneServices Inc",
      "certificate": "CERT-AGG-001",
      "topics": {
        "commands": "v1/aggregator/agg-001/cmd",
        "events": "v1/aggregator/agg-001/evt"
      }
    }
  ],
  "operators": [...],
  "insurers": [...],
  "utm_services": [...]
}
```

### 4. Расширенная модель SITL

#### Архитектура SITL-адаптера
```python
class SITLAdapter:
    def __init__(self, max_drones: int = 100):
        self.drones = {}
        self.physics_engine = PhysicsEngine()
        self.environment = EnvironmentModel()
    
    def process_control_input(self, drone_id: str, controls: dict):
        # ОФ1: Приём управляющих сигналов
        drone = self.drones.get(drone_id)
        if not drone:
            raise DroneNotFound(drone_id)
        
        # ОФ2: Расчёт новых координат
        new_position = self.physics_engine.calculate(
            current_position=drone.position,
            controls=controls,
            environment=self.environment.get_conditions(drone.position),
            dt=self.time_step
        )
        
        # ОФ3: Передача в формате NMEA
        nmea_messages = self.format_nmea(new_position, drone_id)
        
        # ОФ4: Публикация в топик конкретного дрона
        topic = f"v1/uas/{drone_id}/nav/nmea"
        self.publish_nmea(topic, nmea_messages)
```

### 5. Стратегии страховых компаний

#### Дифференцированные стратегии оценки рисков
```python
class ConservativeInsurer:
    """Консервативная стратегия - высокие премии, низкие риски"""
    def calculate_premium(self, mission: Mission, operator: Operator) -> Premium:
        base_rate = 0.02  # 2% от стоимости
        risk_multiplier = 1.5
        safety_discount = 0.9 if operator.safety_record > 0.95 else 1.0
        return base_rate * risk_multiplier * safety_discount

class InnovativeInsurer:
    """Инновационная стратегия - использование ML для оценки"""
    def calculate_premium(self, mission: Mission, operator: Operator) -> Premium:
        features = self.extract_features(mission, operator)
        risk_score = self.ml_model.predict(features)
        return self.score_to_premium(risk_score)
```

### 6. Функциональная специализация дронопортов

```yaml
droneport-types:
  agro-droneport:
    features:
      - chemical-storage
      - spray-system-calibration
      - wash-stations
    capacity: 10
    supported-uas-types: ["agrodrone"]
  
  cargo-droneport:
    features:
      - secure-storage
      - temperature-control
      - biometric-access
    capacity: 20
    supported-uas-types: ["light-cargo", "heavy-cargo"]
  
  inspection-droneport:
    features:
      - sensor-calibration
      - data-upload-stations
      - quick-charge
    capacity: 15
    supported-uas-types: ["inspector"]
```

### 7. Матрица тестирования по доменам

| Домен | Уровень доверия | Покрытие | Анализ зависимостей | Статический анализ |
|-------|----------------|----------|---------------------|-------------------|
| D0_CRITICAL | Критический | ≥80% | Полный + CVE | Обязательно |
| D1_TRUSTED | Высокий | ≥70% | Полный | Обязательно |
| D2_OPERATIONAL | Средний | ≥60% | Основной | Рекомендуется |
| D3_UNTRUSTED | Низкий | ≥30% | Минимальный | Опционально |

### 8. Интеграция с сервисом аналитики

#### Телеметрия безопасности
```json
{
  "event_type": "SECURITY_POLICY_VIOLATION",
  "timestamp": "2024-03-16T12:34:56.789Z",
  "system_id": "OPS-001",
  "domain": "D2_OPERATIONAL",
  "details": {
    "policy_id": "POL-CROSS-DOMAIN-001",
    "source": "D3_UNTRUSTED/aggregator",
    "target": "D0_CRITICAL/crypto",
    "action": "DENIED",
    "reason": "Unauthorized cross-domain access attempt"
  },
  "severity": "HIGH",
  "correlation_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

## Заключение

Доработанная концепция учитывает все новые требования и обеспечивает:

1. **Гранулярное управление безопасностью** через многоуровневую доменную модель
2. **Полную наблюдаемость** через централизованную аналитику
3. **Гибкость развёртывания** с поддержкой множественных экземпляров компонентов
4. **Строгий контроль качества** через дифференцированные требования к тестированию
5. **Реалистичную симуляцию** через SITL с поддержкой 100 дронов
6. **Экономическую модель** с различными стратегиями участников рынка

Эти изменения делают систему более приближенной к реальным условиям эксплуатации и усиливают образовательную ценность проекта.