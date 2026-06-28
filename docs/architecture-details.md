# Детальная архитектура компонентов системы

## Обзор архитектуры

Система построена на принципах микросервисной архитектуры с использованием брокера сообщений для асинхронного взаимодействия. Каждый компонент работает в изолированном контейнере и имеет строго определённые интерфейсы взаимодействия.

## Компоненты по доменам

### Монитор безопасности системы

Каждая система должна иметь свой монитор безопасности для контроля междоменных взаимодействий:

```python
class SystemSecurityMonitor:
    """
    Монитор безопасности системы согласно ГОСТ Р 72118-2025
    Контролирует все междоменные взаимодействия
    """
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.policies = PolicyRepository.load_for_system(system_id)
        self.audit_logger = AuditLogger(system_id)
        
    def check_interaction(self, request: InteractionRequest) -> Decision:
        # Проверка отправителя, получателя и запрашиваемого ресурса/метода
        decision = self._evaluate_policies(
            sender=request.sender,
            receiver=request.receiver,
            resource=request.resource,
            method=request.method,
            context=request.context
        )
        
        # Логирование решения
        self.audit_logger.log_decision(request, decision)
        
        return decision
```

### Домен D0_CRITICAL - Критически важные для безопасности компоненты

#### Поддомен D0.1_MEDIATION - Междоменная медиация

#### interdomain-gateway
**Назначение**: Единая точка контроля всех междоменных взаимодействий

**Функции**:
- Валидация входящих сообщений по JSON Schema
- Проверка прав доступа (ACL)
- Контроль временных меток и TTL
- Дедупликация сообщений (anti-replay)
- Проверка цифровых подписей критичных событий
- Маршрутизация между доменами
- Аудит всех решений

**Интерфейсы**:
```python
# Входящие топики
v1/*/evt/*  # События из всех доменов
v1/*/cmd/*  # Команды из всех доменов

# Исходящие топики  
v1/D0_MEDIATION/evt/gateway.decision  # Решения о пропуске/блокировке
v1/D0_MEDIATION/audit/events  # Аудит событий
```

**Конфигурация**:
```yaml
routing_rules:
  - source_domain: D3_EXTERNAL
    event_type: PERMIT_ISSUED
    target_domain: D2_OPS
    require_signature: true
    
validation:
  schema_version: v1
  max_ttl_ms: 60000
  replay_cache_ttl: 300  # секунд
```

#### audit-log
**Назначение**: Неизменяемый журнал всех событий системы

**Функции**:
- Сбор событий из всех доменов
- Формирование хеш-цепочки для обеспечения целостности
- Экспорт данных для анализа
- Поиск и фильтрация событий

**Интерфейсы**:
```python
# Входящие топики
v1/D0_MEDIATION/audit/*  # Все аудит события

# API для чтения
GET /api/v1/audit/events?from={timestamp}&to={timestamp}
GET /api/v1/audit/hash-chain/verify
```

### Домен D1_FLIGHT - Полётные операции

#### uas-sim (Симулятор БАС)
**Назначение**: Моделирование поведения беспилотного летательного аппарата

**Функции**:
- Приём и выполнение полётных команд
- Генерация телеметрии
- Моделирование полётной динамики
- Встроенный модуль безопасности (проверка геозон, ограничений)
- Симуляция отказов и нештатных ситуаций

**Состояния**:
```
IDLE -> PREFLIGHT -> ARMED -> TAKEOFF -> IN_FLIGHT -> LANDING -> LANDED
                                    |
                                    v
                              EMERGENCY_LAND
```

**Интерфейсы**:
```python
# Входящие команды
v1/uas/{uas_id}/cmd/mission.start
v1/uas/{uas_id}/cmd/mission.abort  
v1/uas/{uas_id}/cmd/pause
v1/uas/{uas_id}/cmd/resume
v1/uas/{uas_id}/cmd/nfz.update

# Исходящие события
v1/uas/{uas_id}/evt/telemetry
v1/uas/{uas_id}/evt/position
v1/uas/{uas_id}/evt/health
v1/uas/{uas_id}/evt/cmd.ack
v1/uas/{uas_id}/evt/alert
v1/uas/{uas_id}/status/conn  # LWT
```

**Модуль безопасности**:
- Контроль соответствия маршрута разрешённым зонам
- Проверка целей безопасности в реальном времени
- Автоматическое прерывание при нарушениях
- Криптографическая проверка команд

#### gcs-sim (Симулятор НУС)
**Назначение**: Моделирование наземной управляющей станции

**Функции**:
- Планирование миссий
- Преобразование заданий в маршрутные точки
- Мониторинг состояния БАС
- Управление в ручном режиме (опционально)

**Интерфейсы**:
```python
# Входящие
v1/D2_OPS/cmd/mission.plan
v1/uas/{uas_id}/evt/*  # Телеметрия от БАС

# Исходящие
v1/D2_OPS/evt/mission.planned
v1/uas/{uas_id}/cmd/*  # Команды БАС
```

### Домен D2_OPS - Операции эксплуатанта

#### ops-core
**Назначение**: Управление парком БАС и выполнением миссий

**Функции**:
- Управление состоянием миссий
- Выбор оптимального БАС для задания
- Расчёт стоимости выполнения
- Взаимодействие с внешними сервисами
- Ведение истории операций

**Бизнес-логика**:
```python
def calculate_mission_cost(mission, uas, insurance_quote):
    operational_cost = uas.hourly_rate * mission.duration
    insurance_cost = insurance_quote.premium
    margin = 0.1  # 10% минимальная маржа
    return (operational_cost + insurance_cost) * (1 + margin)
```

**Интерфейсы**:
```python
# Входящие
v1/D3_EXTERNAL/evt/order.received
v1/D3_EXTERNAL/evt/insurance.quote
v1/D1_FLIGHT/evt/mission.*

# Исходящие  
v1/D2_OPS/evt/proposal.created
v1/D2_OPS/cmd/mission.execute
v1/D2_OPS/evt/mission.state
```

#### ops-policy-enforcer
**Назначение**: Применение политик безопасности при выполнении операций

**Функции**:
- Проверка условий запуска миссии
- Мониторинг соблюдения политик в реальном времени
- Принудительное прерывание при нарушениях
- Ведение журнала решений

**Политики**:
```python
class MissionStartPolicy:
    def check(self, mission, context):
        # Проверка сертификата
        if context.reg_status != "VALID":
            return Deny("Invalid certificate")
            
        # Проверка разрешения ОрВД
        if not context.utm_permit:
            return Deny("No UTM permit")
            
        # Проверка страховки для ценных грузов
        if mission.type == "CARGO" and not context.insurance_active:
            return Deny("No active insurance")
            
        return Allow()
```

### Домен D3_EXTERNAL - Внешние сервисы

#### utm-sim (ОрВД БАС)
**Назначение**: Управление воздушным движением БАС

**Функции**:
- Выдача разрешений на полёты
- Контроль конфликтов маршрутов
- Управление динамическими геозонами
- Мониторинг воздушной обстановки

**API**:
```python
POST /api/v1/permit/request
{
    "mission_id": "MIS-001",
    "uas_id": "UAS-001", 
    "trajectory": [...],
    "time_window": {...}
}

POST /api/v1/geofence/update
{
    "type": "NO_FLY_ZONE",
    "geometry": {...},
    "valid_from": "...",
    "valid_to": "..."
}
```

#### registry-sim (Регулятор)
**Назначение**: Ведение реестра сертификатов и БАС

**Функции**:
- Проверка действительности сертификатов
- Регистрация новых БАС
- Отзыв сертификатов при нарушениях
- Ведение истории

**API**:
```python
GET /api/v1/certificate/status/{cert_id}
Response: {
    "status": "VALID|REVOKED|EXPIRED",
    "valid_until": "...",
    "signature": "..."
}

POST /api/v1/certificate/revoke
{
    "cert_id": "...",
    "reason": "SAFETY_VIOLATION",
    "evidence": {...}
}
```

#### insurance-sim (Страховая)
**Назначение**: Страхование миссий БАС

**Функции**:
- Расчёт страховых премий
- Выдача полисов
- Обработка страховых случаев
- Анализ рисков

**Факторы расчёта премии**:
- Тип миссии (AGR/INSP/CARGO)
- История инцидентов эксплуатанта
- Наличие сертификата безопасности
- Погодные условия
- Сложность маршрута

#### droneport-sim (Дронопорт)
**Назначение**: Управление физической инфраструктурой для БАС

**Функции**:
- Управление посадочными местами
- Зарядка и обслуживание
- Контроль физического доступа
- Реализация режима "Ковёр"

**События**:
```python
# Жизненный цикл слота
SLOT_RESERVED -> DRONE_APPROACHING -> DRONE_LANDED -> 
MAINTENANCE_START -> MAINTENANCE_COMPLETE -> DRONE_READY ->
DRONE_DEPARTED -> SLOT_AVAILABLE
```

#### aggregator-sim (Агрегатор)
**Назначение**: Маркетплейс услуг БАС

**Функции**:
- Приём заказов от клиентов
- Matching заказов и эксплуатантов
- Контроль SLA
- Расчёты между участниками

### Новые компоненты

#### SITL-адаптер
**Назначение**: Симулятор для расчёта физического положения БАС

**Основные функции (ОФ)**:
- ОФ1: Приём управляющих сигналов от приводов
  - Направление движения
  - Скорость движения (горизонтальная, вертикальная)
  - Активация сброса
  - Активация аварийной посадки
- ОФ2: Расчёт новых координат (x,y,z) для дрона
- ОФ3: Передача данных в формате NMEA-0183
- ОФ4: Одновременная работа с несколькими дронами (до 100)

**Формат NMEA сообщений**:
```
$GNRMC,123519.000,A,5542.2389,N,03741.6063,E,0.6,25.8,200906,0.1,E,A*6C
$GNGGA,123519.000,5542.2389,N,03741.6063,E,1,08,0.9,153.4,M,46.9,M,,*5A
```

**Интерфейсы**:
```python
# Входящие команды для каждого дрона
v1/sitl/{uas_id}/cmd/control
{
    "direction": {"heading": 45, "pitch": 10},
    "speed": {"horizontal_ms": 15, "vertical_ms": 2},
    "actions": ["release_cargo", "emergency_land"]
}

# Исходящие NMEA данные
v1/uas/{uas_id}/nav/nmea
```

#### Сервис аналитики
**Назначение**: Сбор и анализ телеметрии и событий безопасности

**Компоненты**:
- `telemetry-collector` - сбор телеметрии от всех систем
- `security-event-processor` - обработка событий безопасности
- `metrics-aggregator` - расчёт KPI и метрик
- `alert-manager` - управление алертами

**Интерфейсы**:
```python
# Входящие топики
v1/*/evt/telemetry
v1/*/evt/security
v1/*/evt/business

# API для дашбордов
GET /api/v1/metrics/realtime
GET /api/v1/analytics/reports
POST /api/v1/alerts/rules
```

## Типы БАС в системе

### 1. Доставщик лёгкий
- Грузоподъёмность: до 5 кг
- Дальность: до 50 км
- Скорость: до 60 км/ч
- Особенности: быстрая доставка малых грузов

### 2. Доставщик тяжёлый
- Грузоподъёмность: до 50 кг
- Дальность: до 100 км
- Скорость: до 80 км/ч
- Особенности: контейнеры с контролем доступа

### 3. Агродрон
- Полезная нагрузка: система распыления
- Объём бака: 10-30 л
- Ширина захвата: 4-6 м
- Особенности: точное земледелие, RTK-навигация

### 4. Инспектор
- Полезная нагрузка: камеры и сенсоры
- Сенсоры: RGB, тепловизор, лидар
- Время полёта: до 60 мин
- Особенности: стабилизация для съёмки

## Требования к тестированию по доменам

### Матрица покрытия тестами

| Домен | Уровень доверия | Мин. покрытие | Анализ зависимостей | Требования |
|-------|-----------------|---------------|---------------------|------------|
| D0_CRITICAL | Критический | ≥80% | Полный + CVE | БТ5, БТ6 |
| D1_TRUSTED | Высокий | ≥70% | Полный | БТ5, БТ6 |
| D2_OPERATIONAL | Средний | ≥60% | Основной | БТ5 |
| D3_UNTRUSTED | Низкий | ≥30% | Минимальный | БТ7 |

### Особые требования
- Доверенные домены с повышением целостности: ≥70% включая зависимости
- Обязательный анализ уязвимостей для всех зависимостей в доверенных доменах
- Запрет на использование пакетов с известными уязвимостями в доверенных доменах

## Сертификаты безопасности систем

### Структура сертификата
```json
{
    "certificate_id": "CERT-SYS-2024-001",
    "system_id": "OPERATOR-DRONE-DELIVERY",
    "version": "1.0.0",
    "issued_by": "REGULATOR-001",
    "security_goals": [
        {
            "id": "SG-001",
            "description": "Предотвращение столкновений",
            "test_coverage": 85,
            "verification_method": "automated_tests"
        }
    ],
    "domains": {
        "D0_CRITICAL": {
            "components": ["security-monitor"],
            "coverage": 82,
            "vulnerabilities": "NONE"
        }
    },
    "valid_until": "2025-03-16T00:00:00Z",
    "signature": "..."
}
```

### API для работы с сертификатами
```python
# Выдача целей безопасности по запросу
GET /api/v1/system/security-goals
Response: {
    "system_id": "...",
    "certificate": {...},
    "goals": [...],
    "signature": "..."
}

# Выдача событий безопасности
GET /api/v1/system/security-events?from={timestamp}
Response: {
    "events": [...],
    "total": 42,
    "severity_breakdown": {...}
}
```

## Управление топиками через Регулятора

### API Регулятора для топиков
```python
GET /api/v1/registry/certified-topics
Response: {
    "timestamp": "2024-03-16T12:00:00Z",
    "participants": {
        "aggregators": [
            {
                "id": "AGG-001",
                "name": "AgroServices Ltd",
                "certificate": "CERT-AGG-001",
                "topics": {
                    "commands": "v1/aggregator/agg-001/cmd",
                    "events": "v1/aggregator/agg-001/evt"
                }
            }
        ],
        "operators": [
            {
                "id": "OPS-001",
                "name": "DroneDelivery Inc",
                "certificate": "CERT-OPS-001",
                "topics": {
                    "commands": "v1/operator/ops-001/cmd",
                    "events": "v1/operator/ops-001/evt"
                }
            },
            {
                "id": "OPS-002",
                "name": "SkyCarriers Ltd",
                "certificate": "CERT-OPS-002",
                "topics": {
                    "commands": "v1/operator/ops-002/cmd",
                    "events": "v1/operator/ops-002/evt"
                }
            }
        ],
        "insurers": [
            {
                "id": "INS-001",
                "name": "Conservative Insurance",
                "certificate": "CERT-INS-001",
                "strategy": "conservative",
                "topics": {
                    "quotes": "v1/insurer/ins-001/quotes",
                    "policies": "v1/insurer/ins-001/policies"
                }
            },
            {
                "id": "INS-002",
                "name": "Innovation Risk Partners",
                "certificate": "CERT-INS-002",
                "strategy": "ml-based",
                "topics": {
                    "quotes": "v1/insurer/ins-002/quotes",
                    "policies": "v1/insurer/ins-002/policies"
                }
            }
        ],
        "utm_services": [...],
        "developers": [...],
        "droneports": [...]
    },
    "signature": "..."
}
```

## Интерфейсы Регулятора

### REST API
```python
# Визуализация реестра
GET /api/v1/registry/systems
GET /api/v1/registry/certificates
GET /api/v1/registry/security-goals

# Управление сертификатами
POST /api/v1/certificates/request
POST /api/v1/certificates/revoke
GET /api/v1/certificates/{id}/status

# Регистрация участников
POST /api/v1/registry/register
PUT /api/v1/registry/{id}/update
```

### Web Application
- Дашборд состояния всех систем
- Визуализация целей безопасности
- Мониторинг инцидентов
- Управление сертификатами
- Аудит журналы

## Форматы сообщений

### Базовый envelope
```json
{
    "msg_id": "550e8400-e29b-41d4-a716-446655440000",
    "schema": "v1.mission.start",
    "ts": "2024-03-16T12:34:56.789Z",
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "source": "ops-core",
    "domain": "D2_OPS",
    "ttl_ms": 5000,
    "data": {...},
    "sig": "base64_signature"
}
```

### Примеры ключевых сообщений

#### Запуск миссии
```json
{
    "schema": "v1.mission.start",
    "data": {
        "mission_id": "MIS-20240316-001",
        "uas_id": "UAS-001",
        "type": "CARGO",
        "waypoints": [...],
        "constraints": {
            "max_altitude_m": 120,
            "max_speed_ms": 15
        }
    }
}
```

#### Телеметрия
```json
{
    "schema": "v1.telemetry",
    "data": {
        "position": {
            "lat": 55.7558,
            "lon": 37.6173,
            "alt_m": 50
        },
        "velocity": {
            "ground_speed_ms": 10,
            "vertical_speed_ms": 0
        },
        "battery": {
            "voltage_v": 22.2,
            "current_a": 15,
            "remaining_pct": 75
        },
        "mode": "AUTO",
        "armed": true
    }
}
```

## Схемы взаимодействия

### Успешный запуск миссии
```
Client -> Aggregator: Заказ
Aggregator -> Operators: Запрос предложений
Operator -> Insurance: Запрос котировки
Insurance -> Operator: Котировка
Operator -> Aggregator: Предложение
Aggregator -> Client: Варианты
Client -> Aggregator: Выбор
Aggregator -> Operator: Подтверждение
Operator -> GCS: План миссии
GCS -> Operator: Маршрут
Operator -> UTM: Запрос разрешения
UTM -> Operator: Разрешение
Operator -> Registry: Проверка сертификата
Registry -> Operator: VALID
Operator -> PolicyEnforcer: Проверка запуска
PolicyEnforcer -> UAS: Команда старта
UAS -> PolicyEnforcer: ACK
UAS -> All: Телеметрия
```

### Обработка отзыва сертификата
```
Registry -> Gateway: REG_STATUS=REVOKED
Gateway -> PolicyEnforcer: REG_STATUS=REVOKED (validated)
PolicyEnforcer: Проверка активных миссий
PolicyEnforcer -> UAS: MISSION_ABORT
UAS -> PolicyEnforcer: ACK
UAS: Переход в EMERGENCY_LAND
PolicyEnforcer -> Operator: Миссия прервана
Operator -> Insurance: Уведомление об инциденте
```

## Требования к производительности

### Латентность
- Команды управления: < 500мс (p99)
- Телеметрия: < 1с (p95)
- Проверка политик: < 100мс
- Валидация в gateway: < 50мс

### Пропускная способность
- До 40 БАС одновременно
- Телеметрия: 1 Гц на БАС
- События: до 1000/сек суммарно

### Надёжность
- Доступность TCB компонентов: 99.9%
- Потеря сообщений: < 0.1%
- Время восстановления: < 30 сек

## Мониторинг и метрики

### Бизнес-метрики
- Количество успешных миссий
- Средняя маржа эксплуатанта
- Количество инцидентов безопасности
- Время реакции на нарушения

### Технические метрики
- Латентность обработки сообщений
- Размер очередей
- Использование ресурсов
- Количество отклонённых сообщений

### Метрики безопасности
- Количество нарушений политик
- Время до обнаружения нарушения
- Количество заблокированных команд
- Процент проверенных сообщений