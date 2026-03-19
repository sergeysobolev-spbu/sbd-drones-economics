---
title: План реализации Запроса 5 (журнал событий, интеграции и агродрон-сценарий)
---

# План реализации Запроса 5 (журнал событий, интеграции и агродрон-сценарий)

_Этот документ фиксирует согласованный план работ по Запросу 5 из `systems/operator/docs/change_requests.md`, с учётом структуры репозитория и требований из `docs/requirements_spec.md`._

## 1. Цель изменения

- Добавить в систему Эксплуатант компонент **«журнал событий»** (EventJournal), в который **все компоненты**, включая Монитор безопасности, отправляют события через брокер.
- Обеспечить передачу событий в **центральный журнал** `systems/analytics`.
- Проработать интеграцию Эксплуатанта с:
  - системой **Агрегатор** (`systems/agregator`),
  - системой **Страховщик** (`systems/insurer`),
  - наземной управляющей станцией **НУС** (`systems/DronePortGCS/systems/gcs`),
  - с явной поддержкой **агродрон-сценария**.
- Обеспечить структуру и **полный набор тестов**, соответствующий `docs/requirements_spec.md`, а также обновить Makefile и демо-цели.

## 2. Краткий обзор архитектуры

- **Эксплуатант (`systems/operator`)**:
  - Компоненты: `OperatorSystem`, `SecurityMonitor`, `FleetManager`, `MissionPlanner`, `BusinessLogic`, `OperatorClients` и др.
  - Уже использует брокер (MQTT/Kafka), монитор безопасности и трейсинг (`trace_id`, `span_id`).
- **Центральный журнал (`systems/analytics`)**:
  - Backend в `systems/analytics/backend` с моделями событий и маршрутами логирования.
- **Внешние системы**:
  - **Агрегатор** (`systems/agregator`) — сейчас работает **только с Kafka**, задаёт заказы Эксплуатанту.
  - **Страховщик** (`systems/insurer`) — принимает решения по страхованию заказов/миссий.
  - **НУС** (`systems/DronePortGCS/systems/gcs`) — рассчитывает маршруты/миссии для БАС и подготовки к регистрации в ОрВД.

EventJournal должен стать центральной точкой сбора и передачи событий из Эксплуатанта в Analytics, не меняя бизнес-логику существующих компонентов.

## 3. План реализации по шагам

### 3.1. Компонент EventJournal в Эксплуатанте

1. Создать структуру компонента в `systems/operator`:
   - `systems/operator/src/event_journal/__init__.py`
   - `systems/operator/src/event_journal/src/event_journal.py`
   - `systems/operator/src/event_journal/src/event_types.py`
   - `systems/operator/src/event_journal/tests/unit/…`
   - при необходимости `systems/operator/src/event_journal/tests/module/…`
   - документация и диаграммы — `systems/operator/src/event_journal/docs/…`
2. В `systems/operator/src/topics.py`:
   - добавить internal-топик журнала, например: `ComponentTopics.get_event_journal() -> f"{SYSTEM_ID}.event_journal"`.
3. Реализовать `event_types.py`:
   - перечисления типов событий (`EventType`), например:
     - `ORDER_RECEIVED`, `ORDER_ACCEPTED`, `MISSION_CREATED`, `MISSION_STARTED`, `MISSION_COMPLETED`,
     - `SECURITY_VIOLATION`, `POLICY_DENIED`, `INCIDENT_REPORTED`,
     - `UAS_PURCHASED`, `UAS_RESERVED`, `UAS_RELEASED`,
     - `COST_CALCULATED`, `INSURANCE_QUOTE_REQUESTED`, `INSURANCE_QUOTE_RECEIVED`,
     - `AGRO_ORDER_RECEIVED`, `AGRO_MISSION_CREATED` и др.
   - уровни важности (`EventSeverity`): `INFO`, `WARNING`, `ERROR`, `SECURITY`, `AUDIT`.
4. Реализовать `EventJournal`:
   - наследник `BaseComponent` c `component_type="event_journal"` и topic=`ComponentTopics.get_event_journal()`;
   - `_register_handlers()` регистрирует handler для action (например, `"handle_event"` или `"log_event"`),
   - handler:
     - валидирует входящее событие (`event_type`, `severity`, `source_component`, `payload`),
     - обогащает его контекстом (`system_id`, timestamp, trace_id/span_id),
     - передаёт в адаптер Analytics.
5. Подключить компонент в запуск:
   - в `systems/operator/src/run_component.py` добавить импорт `EventJournal` и ветку `COMPONENT_TYPE=event_journal`,
   - в `systems/operator/docker-compose.yml` и `docker-compose.kafka.yml` добавить сервис `operator-event-journal` (env: `COMPONENT_TYPE=event_journal`), зависящий от брокера.

### 3.2. Адаптер к Analytics

1. Создать `systems/operator/src/event_journal/src/analytics_adapter.py`:
   - класс `AnalyticsAdapter(base_url, token, timeout)` с методом `send_event(event: dict) -> None`.
   - читать конфиг из env (`ANALYTICS_URL`, `ANALYTICS_TOKEN`, `ANALYTICS_TIMEOUT`).
2. На основе `systems/analytics/backend/app/models.py` и `routes/logs.py`:
   - определить соответствие полей: `system_id`, `event_type`, `severity`, `payload`, `timestamp` и т.п.
   - реализовать маппинг внутреннего формата EventJournal в формат REST API Analytics.
3. В `EventJournal` инициализировать `AnalyticsAdapter` и вызывать его в handler’e событий.
4. Обработать ошибки сети:
   - таймауты/5xx → логирование, краткие ретраи, но без падения компонента,
   - предусмотреть fallback (например, локальный лог) при долгой недоступности Analytics.
5. Добавить интеграционный тест в `systems/operator/tests/integration`:
   - поднимает реальный или моковый Analytics,
   - публикует тестовое событие в топик журнала,
   - проверяет, что Analytics получил событие в правильном формате.

### 3.3. Helper для событий и встраивание в компоненты

1. В SDK (например, `sdk/event_emitter.py`) реализовать helper:
   - `emit_event(bus, system_id, event_type, severity, source_component, payload, trace_context)`,
   - helper публикует сообщения в топик `"{SYSTEM_ID}.event_journal"` с action `"handle_event"` и добавляет trace_id/span_id.
2. Внедрить `emit_event` в компоненты:
   - `OperatorSystem` — при приёме/подтверждении/завершении заказов и миссий, а также при ошибках,
   - `SecurityMonitor` — при нарушениях политик, логировании инцидентов,
   - `FleetManager` — при покупках/резервировании/освобождении UAS и изменениях статусов,
   - `MissionPlanner` — при создании/валидации миссий и ошибках планирования,
   - `BusinessLogic` — при расчётах стоимости, страховых операциях и проверках маржинальности.
3. Убедиться, что:
   - все события содержат корректные `sender`/`sender_role`, не ломая политику SecurityMonitor,
   - событие — «побочный эффект», не влияющий на основную бизнес-логику.

### 3.4. Агродрон-сценарий

1. В YAML-каталоге разработчиков (используемом `DeveloperClient`) убедиться, что есть агродрон (например, `DW-AG300`):
   - подходящая `category` (agro),
   - `max_payload_kg` и `max_range_km` покрывают аграрный сценарий.
2. Настроить FleetManager/MissionPlanner:
   - чтобы `find_suitable_uas` мог явно выбирать агродрон при заданных требованиях (тип задачи, масса, дистанция).
3. Реализовать интеграционный тест агродрон-сценария в `systems/operator/tests/integration`:
   - поднимает Kafka-стек с Эксплуатантом (и НУС/моком),
   - от имени Агрегатора отправляет аграрный заказ через Kafka,
   - проверяет:
     - выбор UAS агро-категории,
     - успешное создание/валидацию миссии,
     - наличие соответствующих событий в EventJournal/Analytics.
4. Добавить unit/module-тесты подбора агродрона в `systems/operator/src/fleet_manager/tests`.

### 3.5. Интеграция с Агрегатором, Страховщиком и НУС

1. **Агрегатор (Kafka-only)**:
   - убедиться, что реальные интеграционные тесты Эксплуатант↔Агрегатор используют только Kafka (`docker-compose.kafka.yml`, соответствующие цели Makefile),
   - для MQTT-сценариев использовать заглушки Агрегатора (совместимые по топикам/формату).
2. **Страховщик**:
   - в точках вызова страховщика (BusinessLogic/Service) добавить события `INSURANCE_QUOTE_REQUESTED/RECEIVED` и ошибки.
3. **НУС/DronePortGCS**:
   - при передаче задания и получении миссии от НУС — события `GCS_MISSION_REQUESTED`, `GCS_MISSION_READY`, `GCS_MISSION_FAILED`.

### 3.6. Структура тестов и корневой Makefile

1. В `systems/operator/tests/` придерживаться структуры спецификации:
   - `unit/` — юнит-тесты системы Эксплуатант,
   - `module/` — модульные,
   - `integration/` — системные интеграции для Эксплуатанта,
   - shell-тесты (`tests/shell*`, `tests/shell-mqtt*`) — сквозные сценарии на уровне системы.
2. В корне `tests/`:
   - `tests/e2e/` — сквозные end-to-end сценарии:
     - e2e Эксплуатант↔Агрегатор↔Analytics,
     - e2e агродрон-сценарий,
     - e2e со Страховщиком и НУС (по мере готовности),
   - `tests/integration/` — интеграционные тесты на уровне всего проекта.
3. В корневом `Makefile`:
   - добавить цели `tests-all` и `tests-all-docker`:
     - `tests-all` — вызывает тесты систем (через `make -C systems/... test-*`) и pytest в `tests/unit`/`tests/integration`,
     - `tests-all-docker` — поднимает общий docker-compose и запускает e2e-тесты из `tests/e2e`.

### 3.7. Полный прогон тестов

1. В `systems/operator`:
   - `make test-unit`,
   - `make test`,
   - `make test-integration`,
   - `make test-integration-kafka`,
   - `make test-shell-mqtt`,
   - `make test-shell-kafka`,
   - `make test-security`,
   - `make test-coverage` (с учётом порогов для доверенных/недоверенных доменов).
2. В корне:
   - `pipenv run pytest tests -v`,
   - `make tests-all`,
   - `make tests-all-docker`.

### 3.8. Новый демонстрационный блокнот

1. Создать `notebooks/operator_event_journal_demo.ipynb`:
   - разделы: описание домена, архитектура, сценарии (обычный заказ, агродрон, инцидент безопасности),
   - PlantUML-диаграммы (PNG) для последовательностей событий,
   - подготовительные ячейки (подъём стэков, healthcheck),
   - кодовые ячейки для имитации Агрегатора (Kafka), проверки журнала и вывода событий из Analytics.
2. Обеспечить устойчивое выполнение всех ячеек при корректно настроенном окружении.

