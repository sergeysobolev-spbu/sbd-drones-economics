# Оценка ДВБ (TCB) — `uas_dev_company`

Сводные метрики и дельта «до/после» декомпозиции хранятся в машиночитаемом виде: [`tcb_metrics.json`](tcb_metrics.json). Обновление:

```bash
cd systems/uas_dev_company
# через Makefile (рекомендуется, тот же pipenv, что и для тестов):
make tcb-metrics-full   # baseline + target + контейнеры + tcb_cost_task12 (редко)
make tcb-metrics        # target + контейнеры + tcb_cost_task12 (обычный прогон)

# вручную:
PYTHONPATH=src python scripts/tcb_metrics.py --baseline --target --out docs/tcb_metrics.json   # полный снимок
PYTHONPATH=src python scripts/tcb_metrics.py --target --out docs/tcb_metrics.json             # только target и отчёт Задачи 12
```

## Состав измеряемых контуров

| Контур | Назначение |
|--------|------------|
| **baseline_tcb** | Полный доверенный baseline до выделения ядра: `security_monitor`, `security_policies`, `component_base`, `services`, `models`, `storage`, `topics`, `integration_adapters`, `jwt_tokens`. |
| **target_tcb** | Условное «ядро» после выноса чистых политик: каталог `src/shared/tcb/`, плюс монитор, политики IPC, `component_base`, `jwt_tokens`, `models` (типы и нормализация целей). |

Оркестрация (`services.py`), хранилище и адаптеры остаются вне **target**-набора, но входят в общий функциональный ДВБ до полного разделения доверенного и недоверенного кода (правило «общий код для доверенных и недоверенных доменов»).

## Агрегированная дельта (из `tcb_metrics.json`)

Поля `delta_baseline_to_target` сравнивают **агрегаты** `baseline_tcb` и `target_tcb`:

- `file_count`, `total_loc`, `total_sloc`, `total_functions`
- `sum_complexity`, `max_complexity`, `functions_over_10`
- `allow_policy_rules_count` (число allow-правил IPC — **стоимость сертификации** по числу сценариев)
- `external_imports_added` / `external_imports_removed` (top-level импорты вне stdlib)

## Allow-политики и трассировка к ЦБ

- Канонический набор: `shared.security_policies.canonical_allow_rule_tuples()` — **29** правил: узкие маршруты шлюза к воркерам плюс явные политики **запроса/ответа** между доменами (`ipc_inbound_request`, `ipc_response`, Задача 14). Нижняя граница ≥14 по сценариям шлюза сохранена.
- Каждое правило трассируется к домену ДВБ в `tests/unit/test_tcb_allow_policy_traceability.py` (`_rule_tcb_domain_map`).

## Бюджет зависимостей `shared.tcb`

Модули `src/shared/tcb/*.py` не должны импортировать брокер, HTTP, SQLite, сторонние SDK и «толстые» слои `shared` (кроме `shared.topics` для ролей). Проверка: `tests/unit/test_tcb_dependency_budget.py`.

## Покрытие тестами ДВБ

Команда `make tcb-test` запускает unit/module/integration с `pytest-cov` по модулям ДВБ (см. `Makefile`) с **`--cov-fail-under=70`** по суммарному покрытию перечисленных пакетов.

Последний замер (локально): **~84%** суммарно по перечню в `tcb-test` (см. вывод `make tcb-test`).

## Диаграмма декомпозиции

Источник PlantUML: [`diagrams/tcb_decomposition.puml`](diagrams/tcb_decomposition.puml); PNG — `make diagrams`.

## Задача 11 — домены в Docker и ДВБ «целиком по контейнеру»

Вводные: каждый **домен безопасности** в учебном развёртывании соответствует **сервису** в `docker-compose.yml` (отдельный контейнер); у процесса **один** уровень критичности; если в домене есть **хотя бы одна** ЦБ-критичная операция, **весь** домен относится к ДВБ. Обмен между Python-доменами в профилях `kafka`/`mqtt` идёт через брокер и **`security_monitor`** (шлюз не обходит монитор при `UAS_GATEWAY_BACKEND=bus`).

В [`tcb_metrics.json`](tcb_metrics.json) ключ **`container_isolation_tcb_task11`** содержит:

- соответствие имён сервисов compose модели доменов;
- по каждому Python-домену — объём кода **каталог компонента + согласованное ядро `shared`** (в скрипте — `SHARED_CORE`, см. Задачу 12); образы по-прежнему копируют всё дерево репозитория;
- **объединение без двойного счёта файлов**: `union_unique_backend_python_scope` — весь операционный backend; **`union_cb123_python_scope`** (Задача 15) — только домены реализации ЦБ-1…ЦБ-3.

Исходные правила соответствия сервис ↔ пути: `scripts/tcb_container_domains.py` (после Задачи 12 в метриках домена — **`component_dir_plus_shared_core`**, а не целиком `src/shared/`). Проверки: `tests/unit/test_tcb_container_domains.py`.

## Задача 12 — методика стоимости ДВБ (`tcb_cost_task12`)

В [`tcb_metrics.json`](tcb_metrics.json) ключ **`tcb_cost_task12`** дополняет отчёт:

- **`task12_baseline_snapshot`** — нормативная точка «до» (14 правил, монолит `shared/services.py`, шлюз с прямым импортом сервисов и режим sqlite по умолчанию, полный `src/shared` в per-domain метриках).
- **`task12_after_snapshot`** — текущие `allow_rules_count` (≥14), маркеры узких действий, признак отсутствия импортов доменов в `gateway/server.py`, **`union_backend_python_sloc`** (после Задачи 15 — только домены `in_cb123_tcb_union`), **`union_all_system_backend_python_sloc`** (полный операционный охват), **`estimated_tcb_cost_score`**.

Формула `estimated_tcb_cost_score` (в том же JSON, поле `formula_ru`): линейная комбинация **SLOC объединения доменов ЦБ-1…ЦБ-3** (`union_backend_python_sloc`), числа allow-правил и штрафа за прямые импорты доменных пакетов из `gateway/server.py`. Штраф отражает повышенный риск и стоимость обоснования при связности **недоверенный шлюз → доверенные сервисы** в одном процессе; в режиме **bus** шлюз загружает только `BusApiContext`.

Обновление блока: `PYTHONPATH=src python scripts/tcb_metrics.py --target --out docs/tcb_metrics.json`.

## Задача 15 — только ЦБ-1…ЦБ-3 в цели ДВБ и в API

- Официальные цели системы — **только** три строки **«ЦБ-1»**, **«ЦБ-2»**, **«ЦБ-3»** (см. `docs/README.md`, §1). Иные обозначения в `security_goals` отклоняются (`shared.tcb.cb_constants.normalize_canonical_security_goals`).
- Прикладные требования (витрина, сделка, журнал…) описываются как **ТБ** в README; домены **purchase** и **audit** в [`scripts/tcb_container_domains.py`](../scripts/tcb_container_domains.py) имеют **`in_cb123_tcb_union: false`** и не входят в SLOC-часть оценки стоимости ДВБ.
- В [`tcb_metrics.json`](tcb_metrics.json) ключ **`container_isolation_tcb_task11`** дополняется **`union_cb123_python_scope`**; полный охват остаётся в **`union_unique_backend_python_scope`**.

## Задача 14 — IPC-топология и цели безопасности по доменам

В [`tcb_metrics.json`](tcb_metrics.json) ключ **`tcb_ipc_topology_task14`** (скрипт [`scripts/tcb_ipc_topology.py`](../scripts/tcb_ipc_topology.py)) задаёт:

- число **уникальных ориентированных связей** между сервисами compose, выведенных из allow-политик (несколько действий с одной парой доменов дают **одну** связь);
- по каждому домену — **число различных соседей** по входящим и исходящим дугам и списки `security_goals_ru` из модели контейнеров.

В рантайме после проверки «шлюз разрешает цель RPC» монитор проверяет наличие политики **`ipc_inbound_request`** от **security_monitor** к целевому воркеру; ответы нормативно разрешены парами **`ipc_response`** (см. `shared/security_policies.py`). Контроль публикации ответа в произвольный `reply_to` брокера остаётся в контексте уже разрешённого `request`; политики фиксируют требуемый сертификационный контур.
