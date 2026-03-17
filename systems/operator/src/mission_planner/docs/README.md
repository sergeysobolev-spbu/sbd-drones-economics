# Mission Planner Component

## Описание

Mission Planner - компонент системы Эксплуатант, отвечающий за планирование и управление миссиями БАС. Компонент обеспечивает создание, валидацию, утверждение и мониторинг полетных заданий с учетом требований безопасности и ограничений воз��ушного пространства.

## Архитектура

Компонент построен с использованием модели разделения доменов безопасности:

### D0_CRITICAL - MissionPlannerCore
Минимальное доверенное ядро, отвечающее за:
- Валидацию планов полета
- Проверку ограничений безопасности
- Расчет критических параметров полета
- Обнаружение конфликтов между миссиями

### D2_OPERATIONAL - MissionPlannerService
Операционный уровень для некритичной логики:
- Управление жизненным циклом миссий
- Хранение и поиск планов
- Интеграция с другими компонентами
- Оптимизация маршрутов
- Работа с шаблонами миссий

### MissionPlanner
Основной класс компонента, обрабатывающий сообщения от системной шины и координирующий работу Core и Service.

## API

### Создание миссии
```json
{
  "type": "create_mission",
  "payload": {
    "name": "Инспекция территории",
    "description": "Плановая инспекция промышленной зоны",
    "operator_id": "operator-123",
    "uas_id": "uas-456",
    "waypoints": [
      {
        "latitude": 55.7558,
        "longitude": 37.6173,
        "altitude": 50.0,
        "speed": 10.0,
        "action": "photo",
        "duration": 5.0
      }
    ],
    "emergency_points": [
      {
        "latitude": 55.7560,
        "longitude": 37.6170,
        "altitude": 0.0,
        "speed": 0.0
      }
    ],
    "takeoff_time": 1679234400.0,
    "response_topic": "mission_planner.response.client-001"
  }
}
```

### Ответ на создание миссии
```json
{
  "type": "create_mission_response",
  "payload": {
    "success": true,
    "mission_id": "mission-1679234400123",
    "status": "validated",
    "validation_result": "valid",
    "validation_issues": [],
    "flight_parameters": {
      "total_distance": 1250.5,
      "estimated_duration": 900.0,
      "max_altitude": 50.0,
      "average_speed": 10.0,
      "waypoint_count": 5
    }
  }
}
```

### Управление жизненным циклом миссии

#### Утверждение миссии
```json
{
  "type": "approve_mission",
  "payload": {
    "mission_id": "mission-1679234400123",
    "approver_id": "supervisor-001"
  }
}
```

#### Запуск миссии
```json
{
  "type": "start_mission",
  "payload": {
    "mission_id": "mission-1679234400123"
  }
}
```

#### Завершение миссии
```json
{
  "type": "complete_mission",
  "payload": {
    "mission_id": "mission-1679234400123",
    "completion_data": {
      "actual_duration": 895.0,
      "actual_distance": 1248.3
    }
  }
}
```

#### Прерывание миссии
```json
{
  "type": "abort_mission",
  "payload": {
    "mission_id": "mission-1679234400123",
    "reason": "Ухудшение погодных условий"
  }
}
```

### Запросы информации

#### Получение информации о миссии
```json
{
  "type": "get_mission",
  "payload": {
    "mission_id": "mission-1679234400123"
  }
}
```

#### Список миссий с фильтрацией
```json
{
  "type": "list_missions",
  "payload": {
    "filters": {
      "status": "active",
      "operator_id": "operator-123",
      "date_from": 1679234400.0,
      "date_to": 1679320800.0
    }
  }
}
```

### Работа с шаблонами

#### Создание шаблона
```json
{
  "type": "create_template",
  "payload": {
    "name": "Стандартная инспекция",
    "description": "Шаблон для регулярных инспекций",
    "waypoints": [...],
    "emergency_points": [...],
    "typical_duration": 900.0,
    "created_by": "operator-123"
  }
}
```

#### Создание миссии из шаблона
```json
{
  "type": "create_from_template",
  "payload": {
    "template_id": "template-123",
    "mission_data": {
      "name": "Инспекция #42",
      "operator_id": "operator-123",
      "uas_id": "uas-456",
      "takeoff_time": 1679234400.0
    }
  }
}
```

## Статусы миссий

- **DRAFT** - Черновик, миссия создана но имеет предупреждения валидации
- **VALIDATED** - Миссия прошла валидацию
- **APPROVED** - Миссия утверждена для выполнения
- **ACTIVE** - Миссия выполняется
- **COMPLETED** - Миссия успешно завершена
- **ABORTED** - Миссия прервана
- **FAILED** - Миссия завершилась с ошибкой

## Конфигурация

Компонент настраивается через переменные окружения:

- `COMPONENT_ID` - Идентификатор компонента (по умолчанию: mission-planner-001)
- `BROKER_TYPE` - Тип брокера сообщений: mqtt/kafka (по умолчанию: mqtt)
- `BROKER_HOST` - Хост брокера (по умолчанию: localhost)
- `BROKER_PORT` - Порт брокера (по умолчанию: 1883)
- `SYSTEM_ID` - Идентификатор системы (по умолчанию: operator-001)
- `MAX_CONCURRENT_MISSIONS` - Максимум одновременных миссий (по умолчанию: 10)
- `MISSION_RETENTION_DAYS` - Срок хранения завершенных миссий (по умолчанию: 90)
- `ENABLE_ROUTE_OPTIMIZATION` - Включить оптимизацию маршрутов (по умолчанию: true)

## Ограничения безопасности

По умолчанию применяются следующие ограничения:

- Максимальная высота: 120 м
- Максимальная скорость: 20 м/с
- Минимальный резерв батареи: 20%
- Максимальная скорость ветра: 10 м/с
- Минимальная видимость: 1000 м
- Радиус геозоны: 1000 м от точки взлета

## Интеграция

### Fleet Manager
- Резе��вирование БАС перед миссией
- Уведомление о начале/завершении миссии
- Освобождение БАС после миссии

### Security Monitor
- Отправка событий безопасности
- Аудит всех операций с миссиями

## Запуск

### Локальный запуск
```bash
cd systems/operator/src/mission_planner
make run
```

### Запуск в Docker
```bash
make docker-build
make docker-run
```

### Запуск тестов
```bash
make test          # Все тесты
make test-unit     # Unit тесты
make test-integration  # Интеграционные тесты
```

## Разработка

### Установка зависимостей
```bash
make install
make dev-setup
```

### Форматирование кода
```bash
make format
```

### Проверка кода
```bash
make lint
make type-check
```

### Отладка
```bash
make debug  # Запуск с подробным логированием
```

## Мониторинг

Компонент предоставляет:
- Структурированные логи с trace_id для отслеживания операций
- Периодическую статистику активных миссий
- Health check endpoint на порту 8080

## Примеры использования

См. Jupyter notebook с демонстрацией:
```bash
make mission-demo