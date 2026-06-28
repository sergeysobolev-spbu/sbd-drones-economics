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

## 3. План реализации по шагам (актуализированный)

### 3.1. Компонент EventJournal в Эксплуатанте (выполнено)

1. Структура компонента создана в `systems/operator/src/event_journal` (инициализация, код компонента, unit-тесты).
2. В `systems/operator/src/topics.py` добавлен internal-топик журнала через `ComponentTopics.get_event_journal() -> f"{SYSTEM_ID}.event_journal"`.
3. Формат событий (типы и уровни важности) определён и задокументирован в `systems/operator/docs/event_types.md`.
4. `EventJournal` реализован как наследник `BaseComponent` с `component_type="event_journal"` и topic=`ComponentTopics.get_event_journal()`, принимает нормализованные события и логирует их.
5. Компонент подключён в запуск:
   - в `systems/operator/src/run_component.py` добавлена поддержка `COMPONENT_TYPE=event_journal`,
   - в `systems/operator/docker-compose.yml` и `docker-compose.kafka.yml` добавлен сервис `operator-event-journal`.

### 3.2. Адаптер к Analytics (базовый уровень — выполнено, e2e — в работе)

1. Реализован `systems/operator/src/event_journal/src/analytics_adapter.py` с классом `AnalyticsAdapter(base_url, api_key, timeout)`.
2. Определено соответствие полей события Эксплуатанта и моделей Analytics (system_id, type, severity, payload, timestamp).
3. `EventJournal` использует адаптер как точку расширения для отправки событий во внешний журнал (дальнейшая доработка возможна без изменения остальных компонентов).
4. Ошибки сети обрабатываются без падения компонента (логируются, возможен fallback).
5. Написан интеграционный тест `systems/operator/tests/integration/test_event_journal_analytics_adapter.py`, проверяющий доставку событий до тестового HTTP API.
6. Отдельная e2e-проверка "компонент → EventJournal → реальный systems/analytics" планируется как расширение после стабилизации API Analytics.

### 3.3. Helper для событий и встраивание в компоненты (выполнено)

1. В `sdk/event_emitter.py` реализован helper `emit_event(bus, topic, event_type, severity, source_component, payload, trace_context)`, не зависящий от конкретных систем (topic передаётся снаружи).
2. `emit_event` внедрён в компоненты Эксплуатанта:
   - `OperatorSystem` — при приёме/подтверждении/отклонении заказов и ошибках (`order_received`, `order_accepted/rejected`, проблемы подбора UAS, отказы безопасности),
   - `SecurityMonitor` — при результатах валидации и нарушениях политик (`security_violation` и др.),
   - `FleetManager` — при инициализации парка, поиске/резервировании/освобождении БАС,
   - `MissionPlanner` — при создании/валидации миссий,
   - `BusinessLogic` — при расчётах стоимости, проверках маржинальности, создании предложений и обработке заказов.
3. Во всех случаях события не ломают основную бизнес-логику (ошибки журналирования глушатся и логируются).

### 3.4. Агродрон-сценарий (базовый уровень — выполнено, e2e — планируется)

1. В YAML-каталоге разработчиков, используемом `DeveloperClient`, уже присутствует агродрон `DW-AG300` (категория `agro`, параметры под аграрные задачи).
2. FleetManager использует данные каталога и сервис для поиска подходящих UAS.
3. Реализован unit-тест `systems/operator/src/fleet_manager/tests/unit/test_agro_uas_selection.py`, проверяющий, что при заданных требованиях подбирается модель DW-AG300.
4. Полноценный интеграционный и e2e-сценарий агродрона (через Kafka, НУС и Analytics) планируется на следующем этапе, вместе с доп. интеграцией с `systems/cyber_drons/agrodron`.

### 3.5. Интеграция с Агрегатором, Страховщиком и НУС (предстоящие работы)

1. **Агрегатор (Kafka-only)**:
   - актуализировать интеграционные тесты Эксплуатант↔Агрегатор с учётом EventJournal (Kafka-стек через `docker-compose.kafka.yml`),
   - для MQTT-сценариев использовать заглушки Агрегатора, совместимые по топикам и формату сообщений.
2. **Страховщик**:
   - в точках вызова страховщика добавить события `insurance_quote_requested/received` и ошибки,
   - при необходимости расширить интеграционные тесты в `systems/operator` и корневых `tests`.
3. **НУС/DronePortGCS**:
   - при передаче задания и получении миссии от НУС журналировать события `gcs_mission_requested`, `gcs_mission_ready`, `gcs_mission_failed`,
   - синхронизировать это с планируемыми e2e-сценариями агродрона.

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

