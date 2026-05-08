# Отчёт о выполнении требований: система разработчика БАС (`uas_dev_company`)

Сопоставление требований из [`implementation_spec.md`](implementation_spec.md) и фактического состояния каталога `systems/uas_dev_company` на момент фиксации отчёта. Операционные детали см. [`README.md`](README.md). Метрики ДВБ: [`tcb_metrics.json`](tcb_metrics.json), [`tcb_summary_report.md`](tcb_summary_report.md).

## Сводка по разделам спецификации

| Раздел спецификации | Оценка | Краткое пояснение |
|---------------------|--------|-------------------|
| Нормативные ссылки | **Выполнено** | Документы в `docs/` присутствуют и перекрёстно согласованы. |
| Границы системы, Docker, брокер, sqlite-режим | **Выполнено** | Описано и реализовано (README, Makefile, доменные воркеры). |
| ДАП и политики (`shared.security_policies`) | **Выполнено** | ДАП и описание в README; политики и тесты на разрешения. |
| БТС1–БТС13, БТК1–БТК8 | **В основном выполнено**, БТС10 — **частично** | Междоменный обмен, монитор, аудит, e2e, образы; передача телеметрии в аналитику — опционально и частично интегрирована. |
| ОФ1–ОФ6, роли, веб итерация 2 | **Выполнено** | API и веб соответствуют описанию; JWT, Nuxt, E2E Playwright. |
| РФС1 (DroneAnalytics) | **Выполнено** | Адаптер и флаги окружения в README. |
| РФ6 / НФ6 (межсистемная) | **По этапам** | Миграция и контракты в `integration_tasks.md`; фактическая готовность — по этапам 1–3 там же. |
| Организация кода, тесты | **Выполнено** | pytest, зональный make (`unit-*`, `integration-*`, `e2e`), ограничение области правок `uas_dev_company`. |
| Данные per-domain, образы, ДВБ | **Выполнено** | `architecture_variants.md`, `UAS_DOMAIN_DATA_ROOT`, `task24_*` в `tcb_metrics.json`. |

## ДВБ (оценка доверия к базе)

| Показатель (из `tcb_metrics.json`) | Значение | Примечание |
|-----------------------------------|----------|------------|
| `estimated_tcb_cost_score` | **81.46** (ключ `tcb_cost_task12` → `task12_after_snapshot`) | итоговый «стоимостной» балл TCB в текущей методике |
| `allow_rules_count` | **44** | в актуальном снимке `task12_after_snapshot` |
| Покрытие (из `tcb_summary_report.md`) | **~77%** по суммарным строкам отчёта | доп. детализация по файлам в том отчёте |

## БТС / БТК — детализация

| ID | Статус | Доказательства / примечание |
|----|--------|----------------------------|
| БТС1, БТС3 | Выполнено | Множество доменов и документация активов/README, ДАП. |
| БТС2 | Выполнено | `broker`, `security_gateway`, `security_monitor`, политики IPC. |
| БТС4 | Выполнено | `pytest tests/test_policy_*.py`, зональные тесты доменов. |
| БТС5–БТС7 | Выполнено / подтверждается CI | Пороги coverage в CI; отчёты `make coverage-all` / артефакты. |
| БТС8 | Выполнено | Модель сертификата и сценарий регулятора (mock/HTTP). |
| БТС9 | Выполнено | `audit_log`, API выборки событий. |
| БТС10 | Частично | Опциональная телеметрия в DroneAnalytics по конфигурации. |
| БТС11 | Выполнено | `audit_log` → `analytics_adapter`. |
| БТС12 | Выполнено (учебная модель) | Документировано ограничение контура сертификации. |
| БТС13 | Выполнено | Уровни критичности в аудите. |
| БТК1–БТК8 | Выполнено | Dockerfile’ы доменов и воркеров, изоляция образов. |

## ОФ и веб

| ID | Статус | Примечание |
|----|--------|------------|
| ОФ1–ОФ3 | Выполнено | Домены и API прошивок, сертификации, реестра. |
| ОФ4, ОФ5 | Выполнено | Веб Nuxt, `make`, HTTP API. |
| ОФ6 | Выполнено | Витрина и покупка для эксплуатанта. |

## Задачи плана (П1–П25) — фиксация результатов

Задачи плана из внутреннего трекера перенесены в отчёт без повторения полного текста подзадач. Статусы ниже отражают состояние на момент составления отчёта.

| План | Тема | Статус |
|------|------|--------|
| П1 | Пакет, зависимости, линтер, git | Выполнено |
| П2 | Инициализация сервисов БД | Выполнено |
| П3 | ДАП, `shared.security_policies` | Выполнено |
| П4 | `security_gateway`, `security_monitor` | Выполнено |
| П5 | Изоляция доменов, `broker` | Выполнено |
| П6 | Unit/интеграционные тесты монитора и шлюза | Выполнено |
| П7 | Образы Docker доменов | Выполнено |
| П8 | Makefile, `compose.yaml` | Выполнено |
| П9–П10 | Домен «Управление пользователями» (роли, веб) | Выполнено |
| П11 | Домен «Реестр дронов» | Выполнено |
| П12 | Домен «Проектирование дрона» | Выполнено; каталог компонент как учебный константный справочник в коде |
| П13 | Домен «Прошивка» IPC | Выполнено |
| П14–П15 | Домен «Сертификация» (ядро, интеграция) | Выполнено |
| П16 | Домен «Управление безопасностью» (события) | Выполнено |
| П17 | Интеграция с внешним журналом / аналитикой | Выполнено (опционально) |
| П18 | Домен «Интернет-магазин» | Выполнено |
| П19 | Документация README | Выполнено |
| П20 | Интеграционные/E2E тесты для CI | Выполнено |
| П21 | Сводный README корня `systems/` | Выполнено (отдельный документ репозитория) |
| П22 | Локализация веба (RU/EN) | Выполнено |
| П23 | Исправление `path` и «зависаний» Nuxt | Выполнено |
| П24 | Узкие образы воркеров, ДВБ-метрики | Выполнено (`task24_*`, отчёты TCB) |
| П25 | ТЗ и отчёт (`implementation_spec` / `implementation_report`) | Выполнено |

## Детализация по закрытым пунктам плана (файлы и артефакты)

- **4:** `docs/README.md` (E2E-учётки, bootstrap, `GATEWAY_AUTH_PROXY_TIMEOUT_S`, трассировка тестов); `docs/uas_dev_company_diagrams.drawio`; интеграционные тесты шлюза и монитора (`tests/integration/test_http_api.py`, `test_http_docker_integration.py`, `test_security_monitor_proxy_routes.py`); `tests/module/test_gateway_bus_timeouts.py`.
- **5:** `docs/api.requests.rest`; прошивки до 10 ЦБ, `source_repo_url` / `source_commit`, миграция v2, `drones.security_goals`; UI черновики (`useFormDraft`), фильтр сертификатов, частичный выбор ЦБ; e2e светлой темы и форм; обновлённые Python-тесты.
- **7:** `docs/integration_tasks.md`, PlantUML и PNG сценариев интеграции (см. каталог `docs/diagrams/` / ссылки в документе).
- **8:** `tests/integration/fakes.py`, `test_regulator_operator_contracts.py`, `src/shared/integration_adapters.py`, SQLite v3.
- **9:** `DronePortPort` / `FakeDronePort`, поля доставки; `CriticalVulnerabilityService`; `AnalyticsAdapterService` / `FakeDroneAnalytics`; без выделенного отдельного IPC-компонента «системный журнал» вне `analytics_adapter` в учебной модели.
- **10:** `docs/tcb_metrics.json` (baseline/target), `src/shared/tcb/`, `docs/tcb_assessment.md`, `docs/diagrams/tcb_decomposition.puml`, тесты `tests/unit/test_tcb_*.py`, цель `make tcb-test`.
- **11:** `scripts/tcb_container_domains.py`, блок `container_isolation_tcb_task11` в `tcb_metrics.json`, `tests/unit/test_tcb_container_domains.py`.
- **12:** вынос сервисов в `src/<домен>/`, узкие allow-правила; снимки `task12_baseline_snapshot` / `task12_after_snapshot` в метриках (см. JSON).
- **13:** `make tcb-test` → `tcb_summary_report.md`, `scripts/tcb_summary_report.py`, `tests/unit/test_tcb_summary_report.py`.
- **14:** явные политики `ipc_inbound_request` / `ipc_response`, `scripts/tcb_ipc_topology.py`, поле `security_goals_ru` у доменов, обновлённый сводный отчёт.
- **15:** `src/shared/tcb/cb_constants.py`, нормализация ЦБ, `maps_to_cb` / `in_cb123_tcb_union` в скриптах оценки.
- **16:** `src/shared/topics.py`, `bus_integration_adapters.py`, `tests/integration/adjacent_contracts.py`, `bus_adjacent_mocks.py`, `test_adjacent_systems_bus.py`, цель `make bus-adjacent-test`.
- **17:** пакет `src/analytics_adapter/`, политики `send_analytics`, `test_analytics_adapter_ipc_bus.py`; строгая маршрутизация «только через audit_log» — по желанию усиления ТЗ.
- **18:** `shared/audit_log_ipc.py`, `record_audit`, форвард в аналитику из `audit_log/handlers.py`; удалён реэкспорт `audit_log/analytics_adapter.py`.
- **19:** `tests/integration/test_drone_analytics_central_journal.py`, цель `make drone-analytics-integration-test`.
- **20:** timestamp и идентификаторы системы в событиях журнала; переработанный `docs/README.md` без сносок на внутренний трекер задач.
- **21:** ДАП и терминология в `docs/README.md` §2, PUML и draw.io без громоздких аббревиатур в пользовательских docs.
- **22:** per-domain SQLite / `UAS_DOMAIN_DATA_ROOT`, сравнение вариантов в `docs/architecture_variants.md`.
- **23:** узкие Dockerfile воркеров, тома данных, анализ в `architecture_variants.md`.
- **24:** метрики копирования НДБ в образы (`task24_*` в `tcb_metrics.json`), обновлённые скрипты и диаграммы.

---

*Отчёт предназначен для сопровождения спецификации; актуализация — при существенных изменениях кода или требований.*
