# Матрица готовности по «Запрос 3» (оператор / OPERATOR)

Документ фиксирует соответствие требований «Запрос 3» текущим артефактам в `systems/operator` и выявленные разрывы.  
Цель — сделать список работ проверяемым: «требование → файл/реализация → статус → что исправить».

## 1) Топики, `SYSTEM_ID`, версионирование внешних топиков

| Требование | Где должно быть | Текущее состояние | Разрыв / что сделать |
|---|---|---|---|
| Один общий брокер в тестовом окружении, уникальность внутренних топиков по `SYSTEM_ID` | `systems/operator/src/topics.py`, docker-compose/env | `TopicBuilder.build_internal_topic()` добавляет префикс `SYSTEM_ID`; в `docker-compose.yml` `SYSTEM_ID` **не задан** | Добавить `SYSTEM_ID` (и `API_VERSION`) в окружение контейнеров, гарантировать использование в рантайме |
| Версионирование внешних топиков системы для взаимодействия с другими системами | `systems/operator/src/topics.py` + клиенты внешних систем | `TopicBuilder.build_external_topic()` использует `SYSTEM_ID` + `API_VERSION`; но код местами ожидает старые константы/имена | Унифицировать API топиков/экшенов и места использования (алиасы или массовая замена импортов) |
| Внешние топики других систем содержат их уникальные идентификаторы (кроме Регулятора) | `SystemTopics.get_*()` | Идентификаторы берутся из env (`*_ID`) или аргумента методов | Проверить, что клиенты реально используют `SystemTopics.get_*()` и не «зашивают» строки |

## 2) Структура компонентов «в духе `fleet_manager`», удаление дублей

| Требование | Где должно быть | Текущее состояние | Разрыв / что сделать |
|---|---|---|---|
| Компонентная структура: `src/<component>/{src,tests,docs,docker,...}` | `systems/operator/src/<component>/...` | Есть `fleet_manager`, `mission_planner`, `security_monitor`, `business_logic` в компонентной структуре | В `systems/operator/src/*.py` есть дубли/монолиты (`fleet_manager.py`, `mission_planner.py`, `security_monitor.py`, `business_logic.py`, `operator_system.py`, клиенты) — нужно убрать/свести к thin-wrapper или удалить, чтобы не было двух параллельных реализаций |
| Удалить неиспользуемые файлы в `systems/operator/src`, `systems/operator/data`, `systems/operator/tests` | указанные каталоги | `systems/operator/tests` содержит `unit/` тесты (не системный уровень). В дереве есть сгенерированное `htmlcov/`, `.pytest_cache/` | Перенести/удалить unit/module тесты из `systems/operator/tests` (оставить integration/e2e); удалить/игнорировать генераты (coverage/cache) |

## 3) Тесты и запуск (`pytest.ini`, `make test-*`, `make test-integration`)

| Требование | Где должно быть | Текущее состояние | Разрыв / что сделать |
|---|---|---|---|
| `pytest.ini` корректно настраивает импорты | `systems/operator/pytest.ini` | Есть `pythonpath = . ../.. ../../..` | Проверить после чистки структуры; скорректировать `testpaths`, чтобы не подхватывать «удаляемые» тесты/монолиты |
| Локальные тесты `make test-*` проходят | `systems/operator/Makefile` + тесты | `Makefile` запускает конкретные файлы (`tests/unit/test_security_monitor.py` и др.), при этом у компонентов есть свои тесты в `src/<component>/tests/...` | Обновить `Makefile`: разнести цели на системные и компонентные, убрать жёсткие пути к удаляемым тестам |
| `make test-integration` поднимает контейнеры через docker-compose и проверяет healthcheck | `systems/operator/Makefile`, `systems/operator/docker-compose.yml`, интеграционные тесты | В compose есть Kafka+компоненты, но **нет healthcheck**; `Makefile` просто гоняет pytest-файлы | Добавить healthcheck в compose, а в `make test-integration` — `docker compose up`, ожидание health, затем запуск интеграционных тестов и стабильный teardown |

## 4) Сквозная трассировка (`trace_id`, `span_id`, `parent_span_id`) и журналирование

| Требование | Где должно быть | Текущее состояние | Разрыв / что сделать |
|---|---|---|---|
| Сквозная трассировка во всех компонентах и системных сценариях | SDK/base component + компоненты + системные тесты | В компонентных реализациях (например `mission_planner/src/mission_planner.py`, `security_monitor/src/security_monitor_service.py`) уже есть поля `trace_id/span_id` в сообщениях | В «монолитных» файлах верхнего уровня трассировки почти нет, а системные сценарии/тесты не гарантируют прокидывание `parent_span_id` |
| Описание логики журналирования (на русском) | `systems/operator/docs/...` | В отчётах Запроса 2 есть упоминания, но нет отдельного понятного описания формата сообщений/правил формирования span | Добавить/обновить отдельный раздел/документ в `systems/operator/docs` с описанием полей и правил генерации/прокидывания |

## 5) Демонстрации (Jupyter notebook)

| Требование | Где должно быть | Текущее состояние | Разрыв / что сделать |
|---|---|---|---|
| `uas_purchase_demo.ipynb` соответствует актуальному API и выполняется без ошибок | `systems/operator/notebooks/uas_purchase_demo.ipynb` | Сейчас фиксируется `ImportError: cannot import name 'OperatorSystemActions'` из `systems/operator/src/topics.py` | Починить импорты/экшены (через алиасы или замену), добавить диаграммы сценариев и прогнать выполнение всех ячеек |

## 6) Итоговые критерии приёмки для «Запрос 3»

Считаем «готово», когда выполняется одновременно:

- `SYSTEM_ID` и `API_VERSION` задаются в docker-compose и используются при построении топиков.
- В коде и тестах **единый API** к топикам и экшенам (`topics.py` не вызывает ImportError; нет расхождений `ComponentTopics.X` vs `ComponentTopics.get_x()`).
- В `systems/operator/tests` остаются только системные `integration/` и `e2e/` (остальные — внутри компонент).
- `make test-*` (локально) и `make test-integration` (docker) проходят.
- Трассировка `trace_id/span_id/parent_span_id` сквозная по системному сценарию и описана в документации (русский язык).
- `systems/operator/notebooks/uas_purchase_demo.ipynb` выполняется полностью без ошибок, содержит диаграммы сценариев.

