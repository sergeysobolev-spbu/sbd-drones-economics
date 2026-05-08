# Оценка ДВБ (TCB) — `uas_dev_company`

Сводные метрики и дельта «до/после» декомпозиции хранятся в машиночитаемом виде: [`tcb_metrics.json`](tcb_metrics.json). Обновление:

```bash
cd systems/uas_dev_company
# через Makefile (рекомендуется, тот же pipenv, что и для тестов):
make tcb-metrics-full   # baseline + target + контейнеры + tcb_cost_task12 (редко)
make tcb-metrics        # target + контейнеры + tcb_cost_task12 (обычный прогон)

# вручную:
PYTHONPATH=src python scripts/tcb_metrics.py --baseline --target --out docs/tcb_metrics.json   # полный снимок
PYTHONPATH=src python scripts/tcb_metrics.py --target --relax-docker-drift --out docs/tcb_metrics.json  # ослабить проверку drift COPY
```

## Состав измеряемых контуров

| Контур | Назначение |
|--------|------------|
| **baseline_tcb** | Полный доверенный baseline до выделения ядра: `security_monitor`, `security_policies`, `component_base`, `services`, `models`, `storage`, `topics`, `integration_adapters`, `jwt_tokens`. |
| **target_tcb** | Условное «ядро» после выноса чистых политик: каталог `src/shared/tcb/`, плюс монитор, политики IPC, `component_base`, `jwt_tokens`, `models` (типы и нормализация целей). |

Оркестрация (`services.py`), **физически разделённые файлы SQLite по доменам** (см. `shared.domain_storage` и `docs/architecture_variants.md`) и адаптеры остаются вне **target**-набора, но входят в общий функциональный ДВБ до полного разделения доверенного и недоверенного кода (правило «общий код для доверенных и недоверенных доменов»).

## Агрегированная дельта (из `tcb_metrics.json`)

Поля `delta_baseline_to_target` сравнивают **агрегаты** `baseline_tcb` и `target_tcb`:

- `file_count`, `total_loc`, `total_sloc`, `total_functions`
- `sum_complexity`, `max_complexity`, `functions_over_10`
- `allow_policy_rules_count` (число allow-правил IPC — **стоимость сертификации** по числу сценариев)
- `external_imports_added` / `external_imports_removed` (top-level импорты вне stdlib)

## Allow-политики и трассировка к ЦБ

- Канонический набор: `shared.security_policies.canonical_allow_rule_tuples()` — **44** правила: маршруты шлюза, **запрос/ответ** монитор ↔ воркеры (`ipc_inbound_request`, `ipc_response`), запись аудита доверенными воркерами, отправка из `audit_log` в `analytics_adapter`, а также **междоменный доступ по политике** (`proxy_request` от воркеров к монитору и логические пары `sender → целевой топик` для чтения снимков прошивки/сертификата и обновления реестра; трассировка ДВБ — метка `partitioned_domain_access` в `tests/unit/test_tcb_allow_policy_traceability.py`).

## Бюджет зависимостей `shared.tcb`

Модули `src/shared/tcb/*.py` не должны импортировать брокер, HTTP, SQLite, сторонние SDK и «толстые» слои `shared` (кроме `shared.topics` для ролей). Проверка: `tests/unit/test_tcb_dependency_budget.py`.

## Покрытие тестами ДВБ

Команда `make tcb-test` запускает unit/module/integration с `pytest-cov` по модулям ДВБ (см. `Makefile`) с **`--cov-fail-under=70`** по суммарному покрытию перечисленных пакетов. Состав `--cov=` согласован с union файлов `*.py`, попадающих в узкие образы доменов с **ЦБ-1…ЦБ-3** по **COPY** в Dockerfile (проверка `tests/unit/test_tcb_makefile_cov_completeness.py`).

Последний замер (локально): **~84%** суммарно по перечню в `tcb-test` (см. вывод `make tcb-test`).

## Диаграмма декомпозиции

Источник PlantUML: [`diagrams/tcb_decomposition.puml`](diagrams/tcb_decomposition.puml); PNG — `make diagrams`. На схеме **монитор** — инфраструктура политик. Цвета периметра и доверия на логических схемах — [`README.md`](README.md), §2.

## Домены в Docker и ДВБ «целиком по контейнеру»

Вводные: каждый **домен безопасности** в учебном развёртывании соответствует **сервису** в `docker-compose.yml` (отдельный контейнер); у процесса **один** уровень критичности; если в домене есть **хотя бы одна** ЦБ-критичная операция, **весь** домен относится к ДВБ. Обмен между Python-доменами в профилях `kafka`/`mqtt` идёт через брокер и **`security_monitor`** (шлюз не обходит монитор при `UAS_GATEWAY_BACKEND=bus`).

В [`tcb_metrics.json`](tcb_metrics.json) ключ **`container_isolation_tcb_task11`** содержит:

- соответствие имён сервисов compose модели доменов;
- по каждому Python-домену — объём кода **каталог компонента + whitelist `shared`**, отражённый в `python_path_specs` (`SHARED_WORKER_SCOPE`, `SHARED_GATEWAY_BUS_SCOPE`, `SHARED_SECURITY_MONITOR_SCOPE`); опциональный сервис **`api_gateway_sqlite`** вынесен в `CONTAINER_NON_PYTHON`, чтобы не дублировать union с узким шлюзом;
- **объединение без двойного счёта файлов**: `union_unique_backend_python_scope` — весь операционный backend; **`union_cb123_python_scope`** — только домены реализации ЦБ-1…ЦБ-3.

Исходные правила соответствия сервис ↔ пути: `scripts/tcb_container_domains.py` (в метриках домена используется **`component_dir_plus_shared_core`**, а не целиком `src/shared/`). Парсинг **фактического** `COPY` (`scripts/parse_uas_docker_copy.py`) дополняет поля `docker_derived_path_specs` / `docker_derived_specs_match_manual` в `python_domains_tcb` и блок **`task24_copy_ndb_carrier`** (пересечение с манифестом **НДБ-носителей** `scripts/tcb_module_roles.json`). При несовпадении множеств `*.py` между Dockerfile и `python_path_specs` скрипт **`tcb_metrics.py --target`** завершается кодом **2** (ослабление: `--relax-docker-drift`). Плюсы/минусы вариантов — [`architecture_variants.md`](architecture_variants.md) (раздел «Метрики ДВБ по фактическому COPY»). Проверки: `tests/unit/test_tcb_container_domains.py`, `tests/unit/test_tcb_docker_specs_drift.py`.

## Метрики по COPY и учёт модулей ТБ в образах ЦБ

- **Цель:** граница кода образа задаётся `COPY` в Dockerfile; множества `*.py`, используемые в `union_cb123_python_scope` и per-domain объёме, **должны** совпадать с результатом парсера (`docker_derived_specs_match_manual` в каждой строке `python_domains_tcb`; агрегат `docker_derived_specs_match_manual_all` — внутри **`task24_copy_ndb_carrier`**).
- **НДБ-носители:** пересечение путей из `scripts/tcb_module_roles.json` с файлами COPY; для сервисов с `in_cb123_tcb_union` union перечислен в `union_ndb_carrier_files_in_cb123_images` — эти строки включаются в отчёт `docs/tcb_summary_report.md` и должны находиться под покрытием `--cov=` в `Makefile` (тест полноты выше).

## Методика стоимости ДВБ (`tcb_cost_task12`)

В [`tcb_metrics.json`](tcb_metrics.json) ключ **`tcb_cost_task12`** дополняет отчёт:

- **`task12_baseline_snapshot`** — нормативная точка «до» (14 правил, монолит `shared/services.py`, шлюз с прямым импортом сервисов и режим sqlite по умолчанию, полный `src/shared` в per-domain метриках).
- **`task12_after_snapshot`** — текущие `allow_rules_count` (≥14), маркеры узких действий, признак отсутствия импортов доменов в `gateway/server.py`, **`union_backend_python_sloc`** (только домены `in_cb123_tcb_union`), **`union_all_system_backend_python_sloc`** (полный операционный охват), **`estimated_tcb_cost_score`**.

Формула `estimated_tcb_cost_score` (в том же JSON, поле `formula_ru`): линейная комбинация **SLOC объединения доменов ЦБ-1…ЦБ-3** (`union_backend_python_sloc`), числа allow-правил и штрафа за прямые импорты доменных пакетов из `gateway/server.py`. Штраф отражает повышенный риск и стоимость обоснования при связности **недоверенный шлюз → доверенные сервисы** в одном процессе; в режиме **bus** шлюз загружает только `BusApiContext`.

Обновление блока: `PYTHONPATH=src python scripts/tcb_metrics.py --target --out docs/tcb_metrics.json`.

## Только ЦБ-1…ЦБ-3 в цели ДВБ и в API

- Официальные цели системы — **только** три строки **«ЦБ-1»**, **«ЦБ-2»**, **«ЦБ-3»** (см. `docs/README.md`, §1). Иные обозначения в `security_goals` отклоняются (`shared.tcb.cb_constants.normalize_canonical_security_goals`).
- Прикладные требования (витрина, сделка, журнал…) описываются как **ТБ** в README; домены **purchase** и **audit** в [`scripts/tcb_container_domains.py`](../scripts/tcb_container_domains.py) имеют **`in_cb123_tcb_union: false`** и не входят в SLOC-часть оценки стоимости ДВБ.
- В [`tcb_metrics.json`](tcb_metrics.json) ключ **`container_isolation_tcb_task11`** дополняется **`union_cb123_python_scope`**; полный охват остаётся в **`union_unique_backend_python_scope`**.

## IPC-топология и цели безопасности по доменам

В [`tcb_metrics.json`](tcb_metrics.json) ключ **`tcb_ipc_topology_task14`** (скрипт [`scripts/tcb_ipc_topology.py`](../scripts/tcb_ipc_topology.py)) задаёт:

- число **уникальных ориентированных связей** между сервисами compose, выведенных из allow-политик (несколько действий с одной парой доменов дают **одну** связь);
- по каждому домену — **число различных соседей** по входящим и исходящим дугам и списки `security_goals_ru` из модели контейнеров.

В рантайме после проверки «шлюз разрешает цель RPC» монитор проверяет наличие политики **`ipc_inbound_request`** от **security_monitor** к целевому воркеру; ответы нормативно разрешены парами **`ipc_response`** (см. `shared/security_policies.py`). Контроль публикации ответа в произвольный `reply_to` брокера остаётся в контексте уже разрешённого `request`; политики фиксируют требуемый сертификационный контур.
