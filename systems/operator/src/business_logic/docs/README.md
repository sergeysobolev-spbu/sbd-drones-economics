# Business Logic Component

## Описание

Компонент Business Logic отвечает за экономическую эффективность операций системы Эксплуатант. Он обеспечивает проверку маржинальности, управление коммерческими предложениями и интеграцию с внешними финансовыми системами.

## Архитектура

Компонент следует принципам разделения доменов безопасности:

### BusinessLogicCore (D0_CRITICAL)
- Минимальное критическое ядро
- Проверка минимальной маржи (10%)
- Валидация максимальной скидки (5%)
- Расчет минимальных цен

### BusinessLogicService (D2_OPERATIONAL)
- Упрощенные расчеты стоимости миссий
- Создание коммерческих предложений
- Mock интеграции с внешними системами:
  - Страховые компании
  - Банковские системы
  - Налоговые сервисы

## API

### Основные действия

#### CALCULATE_COST
Расчет стоимости миссии.

**Запрос:**
```json
{
  "action": "CALCULATE_COST",
  "payload": {
    "mission_data": {
      "distance": 20,
      "duration": 45,
      "cargo_value": 50000
    }
  }
}
```

**Ответ:**
```json
{
  "cost_breakdown": {
    "uas_cost": 1500.0,
    "operator_cost": 750.0,
    "insurance_cost": 1000.0,
    "total": 3250.0
  },
  "total_cost": 3250.0
}
```

#### CHECK_PROFITABILITY
Проверка маржинальности предложения.

**Запрос:**
```json
{
  "action": "CHECK_PROFITABILITY",
  "payload": {
    "price": 4000,
    "cost": 3250
  }
}
```

**Ответ:**
```json
{
  "profitable": true,
  "margin_percent": 18.75,
  "min_margin_percent": 10.0
}
```

#### CREATE_PROPOSAL
Создание коммерческого предложения.

**Запрос:**
```json
{
  "action": "CREATE_PROPOSAL",
  "payload": {
    "order_data": {
      "order_id": "ORD-123",
      "mission_data": {
        "distance": 20,
        "duration": 45,
        "cargo_value": 50000
      }
    }
  }
}
```

**Ответ:**
```json
{
  "proposal": {
    "id": "PROP-abc123",
    "order_id": "ORD-123",
    "price": 3412.5,
    "cost": 3250.0,
    "margin_percent": 4.76,
    "valid_until": "2024-01-02T12:00:00",
    "created_at": "2024-01-01T12:00:00"
  },
  "cost_breakdown": {
    "uas_cost": 1500.0,
    "operator_cost": 750.0,
    "insurance_cost": 1000.0,
    "total": 3250.0
  }
}
```

## Конфигурация

### Переменные окружения

- `COMPONENT_ID` - Идентификатор компонента (по умолчанию: business-logic-001)
- `BROKER_TYPE` - Тип брокера сообщений (mqtt/kafka)
- `BROKER_HOST` - Хост брокера
- `BROKER_PORT` - Порт брокера
- `LOG_LEVEL` - Уровень логирования (DEBUG/INFO/WARNING/ERROR)

### Экономические параметры

- Минимальная маржа: 10%
- Максимальная скидка: 5%
- Тарифы:
  - БАС: 50 руб/км + 500 руб базовая ставка
  - Оператор: 1000 руб/час
  - Страховка: 2% от стоимости груза

## Запуск

### Локальный запуск
```bash
make run-dev
```

### Docker
```bash
make docker-build
make docker-run
```

### Тестирование
```bash
# Все тесты
make test

# Только unit тесты
make test-unit

# С покрытием
make test-coverage
```

## Интеграции

### Security Monitor
Все операции проверяются через Security Monitor для обеспечения соответствия политикам безопасности.

### Fleet Manager
При обработке заказа отправляется уведомление Fleet Manager для резервирования БАС.

### Mock провайдеры
- **MockInsuranceProvider** - заглушка для страховых котировок
- **MockBankingGateway** - заглушка для платежных операций
- **MockTaxService** - заглушка для налоговых расчетов

## Безопасность

1. Все критические проверки выполняются в изолированном ядре (D0)
2. Операционная логика отделена от критической (D2)
3. Все операции логируются с trace_id для аудита
4. Интеграция с Security Monitor для контроля политик

## Примеры использования

### Python
```python
from broker.bus_factory import BusFactory
from systems.operator.src.business_logic.src import BusinessLogic

# Создание компонента
bus = BusFactory.create_bus("mqtt", "localhost", 1883)
business_logic = BusinessLogic("bl-001", bus)

# Запуск
business_logic.start()
```

### Интеграционный тест
```python
# Расчет стоимости
response = await bus.request(
    "operator-001.business_logic",
    {
        "action": "CALCULATE_COST",
        "payload": {
            "mission_data": {
                "distance": 10,
                "duration": 30,
                "cargo_value": 10000
            }
        }
    }
)
```

## Мониторинг

Компонент предоставляет статистику через действие GET_STATISTICS:
- Количество созданных предложений
- Средняя маржинальность
- Общая стоимость предложений
- Количество активных предложений

## Разработка

### Структура кода
```
business_logic/
├── src/
│   ├── business_logic.py         # Основной компонент
│   ├── business_logic_core.py    # Критическое ядро (D0)
│   └── business_logic_service.py # Сервисный слой (D2)
├── tests/
│   └── unit/                     # Unit тесты
├── docker/
│   └── Dockerfile               # Контейнеризация
└── docs/
    └── README.md               # Эта документация
```

### Добавление новых интеграций

Для добавления реальных интеграций вместо mock:

1. Создайте новый класс провайдера в `business_logic_service.py`
2. Реализуйте необходимые методы с реальными API вызовами
3. Добавьте конфигурацию через переменные окружения
4. Обновите тесты

## Поддержка

При возникновении проблем:
1. Проверьте логи компонента
2. Убедитесь в доступности брокера сообщений
3. Проверьте корректность конфигурации
4. Обратитесь к системным тестам для примеров использования