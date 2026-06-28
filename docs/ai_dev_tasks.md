# Мультиагентная разработка проекта ТЭМ БАС

<!-- doc-meta: status=active version=1.3 updated=2026-06-28 -->

Документ — **контракт агент-оркестратора** для подготовки и проведения работ по открытой платформе моделирования экономики эксплуатации безопасных дронов (направление **ОП**, см. [concept.md](concept.md)). Программный стенд — экспорт [`sbd-open-platform-and-trainings-development/code`](../../../sbd-open-platform-and-trainings-development/code).

---

## Содержание

- [context](#context) — контекст и связь репозиториев
- [repo-analysis-ai](#repo-analysis-ai) — анализ `sbd-drones-economics-ai`
- [repo-analysis-core](#repo-analysis-core) — анализ `sbd-drones-economics`
- [merge-decisions](#merge-decisions) — что влить в `master`, от чего отказаться
- [e2e-problem](#e2e-problem) — проблема сквозных тестов
- [agents-connect](#agents-connect) — подключение агентов и навыков
- [orchestration-model](#orchestration-model) — модель оркестрации
- [system-agents](#system-agents) — двухуровневая модель агентов (горизонталь + вертикаль)
- [iterations](#iterations) — итерации проработки (SE × 4, архитектор, QA, DevOps, техпис, PM, методист)
- [development-plan](#development-plan) — план развития платформы
- [stage-1-plan](#stage-1-plan) — Этап 1: контракт, стабилизация CI/E2E, PR-E1
- [backlog-sync](#backlog-sync) — синхронизация с бэклогом этапа 0 (T1–T17)
- [next-actions](#next-actions) — ближайшие действия оркестратора
- [vuca-block-merge-2026-06-28](#vuca-block-merge-2026-06-28) — staged push blocks A–E, QA gates, master tip
- [final-merge-purge-2026-06-28](#final-merge-purge-2026-06-28) — integration → master, branch purge
- [ci-failure-joint-plan](#ci-failure-joint-plan) — совместный план восстановления Jenkins CI/CD и upskilling агентов

---

## context {#context}

| Репозиторий | Роль | Основная ветка работ |
|-------------|------|----------------------|
| [`sbd-drones-economics`](../../sbd-drones-economics) | Код платформы (субмодули, E2E, Jenkins) | `master` (канон после VUCA merge) |
| [`sbd-drones-economics-ai`](.) | AI-интеграция, Operator, учебные материалы, phase 0 | `master` (общий remote с `-economics`) |
| [`sbd-open-platform-and-trainings-development`](../../../sbd-open-platform-and-trainings-development) | Канонический стенд ТЭМ, агенты, CI-ворота | `main` / `code/` |

**Расхождение линий развития:** в `-ai` основной deliverable — `systems/operator` (Python, MQTT/Kafka); в `-economics` — полный полигон с субмодулями (`Agregator`, `agrodron`, `SITL-module`, …) и `systems/uas_dev_company`. Слияние веток **без согласования контрактов топиков (T1–T2)** даст конфликт архитектур.

**Цель оркестратора:** выровнять контракты → стабилизировать CI → подключить агентов → вести бэклог этапа 0 и учебного трека ОП.

---

## repo-analysis-ai {#repo-analysis-ai}

**Ветка:** `test/integration-phase0-initiation` (HEAD `c6cccf7`, +17 непушенных коммитов к origin).  
**`master`:** скелет (~86 файлов, только `dummy_system`) — **не отражает** состояние проекта.

### Что добавлено относительно `master`

| Кластер | Содержание | Статус |
|---------|------------|--------|
| `systems/operator/` | SecurityMonitor, FleetManager, MissionPlanner, BusinessLogic, EventJournal, shell-тесты MQTT/Kafka | ✅ unit/integration/shell зелёные локально |
| `docs/integration_process/` | Анализ phase 0, бэклог T1–T17, change requests CR5–CR10 | ✅ активный источник требований |
| `demos/sbd-model-simple-demo/` | Stub-экосистема + pytest | ⚠️ частично |
| `notebooks/` | systems_api, sbd-model, aggregator_operator live demo | ⚠️ live demo WIP |
| `docs/courses_specific/slides/` (канон: **open-platform**) | LaTeX/PDF (SBOM, TARA, integration, DLT) | 📚 учебный контент, не runtime |
| CI | Корневых workflows **нет**; DronePortGCS CI **несовместим** с Makefile (`unit-test` vs `tests-unit`) | ❌ |

### Phase 0 (честная оценка)

| Цепочка | Статус |
|---------|--------|
| Заказчик → Агрегатор (HTTP) | Частично (модель «доставка», не «агро») |
| Агрегатор → Эксплуатант | ❌ Kafka vs MQTT, разные префиксы топиков (З1–З2) |
| Эксплуатант → Страховая / НУС / Дронопорт / ОрВД | Частично; заглушки не оформлены (З5–З7) |
| Сквозной автотест phase 0 | ❌ (T14) |
| EventJournal → Analytics | Mock HTTP; полный контур не закрыт |

Подробности: [phase0_systems_analysis.md](integration_process/phase0_systems_analysis.md), [phase0_remarks_and_technical_tasks.md](integration_process/phase0_remarks_and_technical_tasks.md).

---

## repo-analysis-core {#repo-analysis-core}

**Ветка:** `feature/uas-dev-company` (+32 к `master`, fast-forward merge возможен).  
**`master`:** рабочий полигон с Jenkins, E2E, 10 субмодулями.

### Ключевые активы

| Компонент | Описание |
|-----------|----------|
| `systems/uas_dev_company/` | UAS Dev Company: certification, registry, purchase, Nuxt UI, Playwright |
| `ci/jenkins/` | JCasC: 5 job (`drone-unit`, `drone-integration`, `drone-e2e`, …) |
| `tests/e2e/test_e2e_scenario.py` | Полный Kafka-сценарий; **29 `pytest.skip`** при неготовности контейнеров |
| `make e2e-codespace` | CI-путь E2E без DroneAnalytics (`E2E_SKIP_ANALYTICS=1`) |
| `make e2e-mqtt-*` | Экспериментальный dual-transport E2E |

### Стабильность E2E (уже mitigated)

- Warmup 100–180 с, pre-create Kafka topics (`e2e_warmup.sh`)
- ORVD timeout workarounds, SITL home publish, DronePort battery fix
- **`drones`** возвращён в compose (на master был исключён)

**Риск:** CI может быть **зелёным при пропусках** — не гарантия полного пути.

---

## merge-decisions {#merge-decisions}

### Влить в `master` (поэтапно, отдельные PR)

#### `sbd-drones-economics`

| PR | Содержание | Условие |
|----|------------|---------|
**Правило оркестратора:** PR-E1 в `-economics` первым; затем topic map v0.2 и PR-A1 (`-ai` operator).

---

## e2e-problem {#e2e-problem}
| **PR-E2** | Cherry-pick negative E2E из `feature/negative-e2e-scenario` | Если нужен отдельный негативный сценарий (дополняет `test_e2e_incident_scenario.py`) |
| **PR-E3** | Восстановить Fabric E2E job или явно пометить manual-only | Root `Jenkinsfile` удалён на feature — зафиксировать решение |

#### `sbd-drones-economics-ai`

| PR | Содержание | Условие |
|----|------------|---------|
| **PR-A1** | Platform: `systems/operator`, `shared/`, `sdk/`, broker, `demos/`, `tests/` | После T1–T2 (контракт топиков) |
| **PR-A2** | Docs: `docs/integration_process/`, обновлённый `requirements_spec.md` | Независимо от кода |
| **PR-A3** | CI: адаптация из `origin/feature/github-actions` + выравнивание имён целей Makefile | Согласовать с PR-E1 |
| **PR-A4** | Slides: перенесены в `open-platform/docs/courses_specific/slides/` (`sbom`, `tara`, …) | Без персональных данных |
| **PR-A5** | `docker-compose` профиль `integration-phase0` (T10) | После T1–T3 |

### Отказаться / закрыть без merge

| Ветка / артеfact | Причина |
|------------------|---------|
| `tests-e2e-design`, `feature/component_redesign` (-ai) | Устарели (= master) |
| `feature/Jenkins`, `feature/mqtt-e2e`, `feature/uas-dev-company-integration` (-economics) | Поглощены `feature/uas-dev-company` |
| `tests/phase0-integration--ai` | 6 коммитов, superseded |
| `origin/feature/uas-dev-company*` (-ai) wholesale | Конфликт с `systems/operator`; reconcile после T17 |
| `docs/slides/ksa/ЗУНы/` bulk merge | Nested git + CSV с персональными данными — privacy review |
| `.venv/`, LaTeX aux/pdf в git | Добавить в `.gitignore`, не коммитить |

### Согласование двух репозиториев

```
sbd-drones-economics (полигон)  ←── экспорт/синх ──→  sbd-open-platform/code
         ↑                                              ↑
         └──── контракт топиков (T1–T2) ────────────────┘
sbd-drones-economics-ai (operator + учебный контент)
```

**Правило merge в `master`:** push только при **зелёных** обязательных тестах (см. PR-E1 gate ниже).

### Решения human_review (2026-06-28)

| Решение | Статус |
|---------|--------|
| **ADR-001** — Kafka для Aggregator↔Operator **на phase 0** | ✅ Accepted |
| **ADR-002** — broker-agnostic платформа после phase 0 (env + профиль теста) | ✅ Accepted |
| Merge line — **PR-E1** (`feature/uas-dev-company` → `master` в `-economics`) | ✅ Выбрано |
| Push `master` | ✅ **2026-06-28 final merge** @ `7a0c87de` ([report](staged-push-reports/2026-06-28-final-merge-purge.md)); PR-E1 CI still open — `ci-integration-test` red (2026-06-28); см. `-economics/docs/pr-e1-gate-report.md` |
| PR-A1 (`-ai` operator) | После PR-E1 + topic map v0.2 |

### Влить в `master` (поэтапно, отдельные PR)

#### `sbd-drones-economics`

| PR | Содержание | Gate (обязательно green) |
|----|------------|---------------------------|
| **PR-E1** | Fast-forward `feature/uas-dev-company` → `master` | `make ci-test` **и** `make e2e-codespace`; sqlite не в git |
| **PR-E2** | Cherry-pick negative E2E из `feature/negative-e2e-scenario` | По необходимости |
| **PR-E3** | Fabric E2E job или manual-only | После PR-E1 |

#### `sbd-drones-economics-ai`

| PR | Содержание | Условие |
|----|------------|---------|
| **PR-A1** | Platform: operator, shared, sdk, demos, tests | После PR-E1 + topic map v0.2 |
| **PR-A2** | Docs: integration_process, requirements_spec | Независимо |
| **PR-A3** | CI из feature/github-actions | Согласовать с PR-E1 |
| **PR-A4** | Slides без PII | Отдельный track |
| **PR-A5** | compose `integration-phase0` | После T1–T3 |

**Правило оркестратора:** PR-E1 в `-economics` первым; затем topic map v0.2 и PR-A1.

---

## e2e-problem {#e2e-problem}

### Диагноз (сводка агентов QA + DevOps + архитектор)

| Симптом | Корневая причина |
|---------|------------------|
| E2E отключены в CI по умолчанию | `-ai`: `RUN_DOCKER_TESTS!=1` → skip; `-economics`: только Jenkins `drone-e2e`, не на каждый push |
| «Зелёный» CI при неполном прогоне | 29+ `pytest.skip` в `test_e2e_scenario.py` — мягкий fail |
| Два репозитория — два E2E контура | Operator shell-тесты (-ai) vs полный Kafka stack (-economics) |
| Flaky ORVD/SITL/DronePort | Таймауты шлюзов, cold-start Kafka consumer groups |
| Нет единого compose phase 0 | Разрозненные compose в подсистемах (З9) |

### Целевая модель тестов (пирамида)

```mermaid
flowchart TB
  subgraph ci_fast [CI fast - каждый push]
    U[unit SDK + systems]
    I[integration per-system docker]
  end
  subgraph ci_nightly [CI nightly / workflow_dispatch]
    E2E_S[smoke e2e - 1 happy path]
  end
  subgraph ci_weekly [CI weekly / manual]
    E2E_F[full e2e + analytics]
    E2E_N[negative / incident]
  end
  ci_fast --> ci_nightly --> ci_weekly
```

### Меры (P0–P2)

| ID | Мера | Владелец-агент |
|----|------|----------------|
| E2E-1 | **Smoke E2E** (T14): заказ → Kafka → Operator ack; без SITL/ORVD | DevOps + QA |
| E2E-2 | Заменить часть `pytest.skip` на **xfail с issue** или hard fail для обязательных шагов smoke | QA |
| E2E-3 | Профиль `integration-phase0` compose (T10) | DevOps |
| E2E-4 | Единый warmup + topic pre-create (перенести паттерн из `-economics` в `-ai`) | DevOps |
| E2E-5 | GitHub Actions: unit+integration на push; e2e-smoke nightly; e2e-full manual | DevOps |
| E2E-6 | Заглушки Дронопорт/ОрВД (T6–T7) — детерминированный smoke без внешних таймаутов | Architect + SE |

---

## agents-connect {#agents-connect}

Источник: [`sbd-open-platform-and-trainings-development/.cursor/`](../../../sbd-open-platform-and-trainings-development/.cursor/), реестр `code/config/agent_skill_registry.json`.

### Обязательный набор для ТЭМ БАС (ОП)

| Роль | Агент (профиль) | Навыки (skills) | `task_type` |
|------|-----------------|-----------------|-------------|
| Системный инженер СКИБ | `systems-engineer-sbd` | `skill_systems_engineer_sbd`, `skill_select_pattern`, `skill_traceability`, `skill_human_review` | `systems_engineer_task` |
| Школа СИ — русская | `se-school-russian` | `skill_toc_se_schools` | `toc_dtr_session` |
| Школа СИ — американская | `se-school-american` | `skill_toc_se_schools` | `toc_dtr_session` |
| Школа СИ — китайская | `se-school-chinese` | `skill_toc_se_schools` | `toc_dtr_session` |
| Школа СИ — agent-native | `se-school-ai-native` | `skill_agent_native_se`, `skill_human_review` | `agent_native_se_design` |
| Архитектор | `software-architect-c4` | `skill_software_architecture_c4`, `documentation-governance` | `software_architecture_c4` |
| QA / приёмка | `qa-marinet-spec` * | `skill_artifact_quality`, `skill_traceability`, `platform-validation` | `artifact_quality_review` |
| DevOps / CI | `ci-marinet-steward` * | `platform-ci-jenkins`, `platform-validation`, `skill_marinet_ci_gates` | `jenkins_or_ci_change` |
| Техпис / документация | *(нет отдельного профиля)* | `documentation-governance`, `skill_artifact_quality` | `docs_change` |
| Проектный менеджер | `project-manager-ccpm` | `skill_project_management_ccpm`, `skill_human_review` | `project_management_ccpm` |
| Методист / преподаватель | `course-educator-platform` | `skill_course_educator_platform`, `skill_human_review` | `course_educator_task` |
| Качество артеfactов | `artifact-quality-controller` | `skill_artifact_quality`, `skill_human_review` | `artifact_quality_review` |
| Оркестратор TOC | `toc-orchestrator` | `skill_toc_se_schools`, `skill_toc_dtr_session` | `toc_dtr_session` |
| Цифровой двойник / SITL | `dt-simulation-lead` | `skill_dt_simulation_tem` | `tem_marinet_domain_task` |
| Экономика / TCO | `tem-economics-analyst` * | `skill_marinet_domain` (экономический контур) | `tem_marinet_domain_task` |

\* — Marinet-профиль; для БАС использовать **с адаптацией** (переименовать job `tem-marinet-*` → `tem-bas-*`, порты из `e2e_ports.*.env`).

### Headless-пакеты (кодинг-агенты)

| Пакет | Применимость к БАС |
|-------|-------------------|
| `tem-bas-purchase-*` | ✅ UAS vitrine, purchase flow (#105–111) |
| `tem-registry-*` | ✅ бэклог платформенных gap |
| `test-profile-refactor-*` | ✅ рефакторинг профилей тестов (E2E-1…6) |
| `certification-demo-*`, `nginx-web-ui-*` | ⚠️ по необходимости для учебных сценариев |

### Что скопировать в `-ai` / `-economics`

```
.cursor/
├── agents/          # подмножество из таблицы выше
├── skills/          # связанные SKILL.md
└── rules/           # documentation-governance, platform-python-deps, ports (адаптировать)
docs/ai_sbd/agents/  # workspace briefs для TOC/SE sessions
code/config/agent_skill_registry.json  # с task_type для BAS
```

### Пробел: агент «экономика дронов»

Отдельного профиля нет. Оркестратор комбинирует: `tem-economics-analyst` + `course-educator-platform` + headless `tem-bas-purchase-*`. При росте КТ-направления — создать `tem-bas-economics` по шаблону Marinet agents.

---

## orchestration-model {#orchestration-model}

### Роли в цикле

| Роль | Инструмент | Делает | Не делает |
|------|------------|--------|-----------|
| **Координатор** | Cursor chat / Makefile `APPLY=1` | GitHub Status, integrate, выбор ветки PR | — |
| **Coding-агент** | headless `cursor-agent` в worktree | Issue → код → unit tests | `gh`, смена board |
| **Review-агент** | `artifact-quality-controller`, deterministic gates | Coherence, SKIB trace | Merge |
| **Human review** | преподаватель / владелец ОП | Приёмка phase 0, учебных материалов | — |

### Типовой цикл (2 недели)

1. **TOC/DTR** (`make toc-se-schools-session`) — ограничение спринта  
2. **Architect** — C4 + topic map (T2)  
3. **SE-SBD** — ЦПБ/контракт для изменения  
4. **Coding headless** — T1–T14 implementation  
5. **QA + DevOps** — CI profile, smoke E2E  
6. **Course educator** — lab / notebook sync  
7. **PM** — buffer review, milestone evidence  
8. **Integrate + human_review**

---

## system-agents {#system-agents}

Предложение оркестратора: **двухуровневая** модель агентов для ТЭМ БАС (ОП). Горизонтальные роли — постоянный контур координации и приёмки; вертикальные пакеты — **временные** coding-агенты по подсистемам, подключаемые **после baseline Этапа 1a**, но **до** merge PR-E1 (см. [stage-1-plan](#stage-1-plan)).

### Горизонтальный уровень (постоянный контур)

| Роль | Профиль / `task_type` | Зона ответственности |
|------|----------------------|----------------------|
| **Оркестратор** | координатор Cursor / Makefile `APPLY=1` | GitHub Project Status, integrate, выбор PR, rollout coding-пакетов |
| **Архитектор** | `software-architect-c4` | C4, ADR, `topic_map.yaml`, review изменений контрактов |
| **Системный инженер СКИБ** | `systems-engineer-sbd` | КБП/ЦПБ, traceability harm → ЦБ → тест, human_review |
| **QA / приёмка** | `qa-marinet-spec`, `artifact-quality-controller` | критерии приёмки, матрица T1–T17 ↔ pytest, smoke/full E2E |
| **DevOps / CI** | `ci-marinet-steward` | Jenkins/JCasC, GitHub Actions, compose-профили, `ports-check` |
| **Техпис** | `docs_change` (`documentation-governance`) | канон docs, doc-meta, термин **СКИБ** (ГОСТ Р 72118-2025) |
| **Проектный менеджер** | `project-manager-ccpm` | WBS, буферы, milestone evidence, критический путь |
| **Методист / преподаватель** | `course-educator-platform` | labs, rubrics, demo-pack; не блокирует CI-gate |

Горизонтальные агенты **не** привязаны к одному worktree; coding-агенты **не** используют `gh` и **не** меняют статус GitHub Project.

### Вертикальный уровень (coding-пакеты по подсистемам)

Не 15 постоянных профилей, а **issue-scoped headless-пакеты** (один issue → один worktree → один coding-агент):

| Пакет | Подсистема / scope | Типичные задачи |
|-------|-------------------|-----------------|
| `tem-bas-operator` | `systems/operator` (-ai) | Kafka consumer/producer, EventJournal, shell/integration tests |
| `tem-bas-aggregator` | Aggregator / API заказа | `service_type: agro_field` (T3), HTTP→Kafka bridge |
| `tem-bas-insurer-adapter` | страховой адаптер | topic alignment (T4), stub/real switch |
| `tem-bas-integration-stubs` | ORVD / DronePort | детерминированные заглушки (T6–T7) для smoke |
| `tem-bas-uas-dev-company` | `systems/uas_dev_company` | vitrine, purchase flow, Playwright (после PR-E1) |

Пакеты `tem-registry-*`, `test-profile-refactor-*`, `certification-demo-*` — по необходимости, **не** входят в baseline Этапа 1.

### Правила подключения coding-агентов

1. **Один issue = один worktree = один coding-агент** — без параллельной правки одного issue разными агентами.
2. **Coding-агенты не вызывают `gh`** — board, labels, PR создаёт координатор.
3. **Запрет на изменение `topic_map.yaml` и ADR без review архитектора** — SE-SBD подтверждает traceability; merge только после `human_review`.
4. **Rollout по фазам Этапа 1** — см. [stage-1-plan](#stage-1-plan): горизонталь только в **1a**; вертикаль подключается в **1b** (стабилизация integration/E2E); **1c** — merge PR-E1 при green gate.

```mermaid
flowchart TB
  subgraph horizontal [Горизонталь — постоянно]
    O[Оркестратор]
    A[Architect]
    SE[SE-SBD]
    QA[QA]
    DO[DevOps]
    TW[Техпис]
    PM[PM]
    CE[Course-educator]
  end
  subgraph vertical [Вертикаль — по issue/worktree]
    OP[tem-bas-operator]
    AG[tem-bas-aggregator]
    ST[tem-bas-integration-stubs]
    IN[tem-bas-insurer-adapter]
    UAS[tem-bas-uas-dev-company]
  end
  O --> A & SE & QA & DO
  O -.->|Этап 1b+| OP & AG & ST
  A -.->|review| OP & AG & ST
  QA & DO -.->|CI gate| OP & AG & ST
```

---

## iterations {#iterations}

Синтез нескольких раундов проработки подключёнными агентами (без исполнения кода — план).

### Итерация 1 — ограничение (TOC + 4 школы СИ)

**Вход:** З1–З2 (Kafka/MQTT, topic map), master не отражает проект.  
**Ограничение (DBR):** отсутствие **опубликованного контракта обмена** блокирует phase 0, merge двух репозиториев и стабильный E2E.

| Школа | Вклад |
|-------|-------|
| Русская (СМД) | Разрыв — не технический, а **деятельностный**: нет позиции «владелец контракта» между командами Aggregator и Operator |
| Американская (V&V) | ConOps phase 0 = один воспроизводимый сценарий; verification = smoke E2E (T14) как **acceptance test** |
| Китайская (整体) | Topic map + compose + тесты — **целое**; частичный merge Operator без Aggregator бессмыслен |
| Agent-native | Issue-ready пакеты: T1, T2, T10, T14 как agent tasks с `task_type` и evidence |

**Решение итерации 1:** спринт **только** T1, T2, T12, T14 — всё остальное в буфер.

---

### Итерация 2 — архитектура и контракты

**Архитектор (`software-architect-c4`):**

- C4 Container: Customer → Aggregator → Operator → {Insurer, GCS, DronePort stub, ORVD stub} → Agrodron  
- ADR-001: транспорт Aggregator↔Operator = **Kafka** на phase 0 (Operator `BROKER_TYPE=kafka`)  
- ADR-002: единый файл `docs/integration/topic_map.yaml` — source of truth  
- ADR-003: профиль compose `integration-phase0` — минимальный набор контейнеров для smoke

**SE-SBD:**

- ЦБ phase 0: целостность цепочки заказа, журналирование EventJournal (БТ10–БТ11)  
- Traceability: harm «потеря заказа» → ЦБ → topic ack → test T14

---

### Итерация 3 — QA и DevOps

**QA (`qa-marinet-spec` + `artifact-quality-controller`):**

- Критерий приёмки master: smoke E2E **без skip** на обязательных шагах  
- Негативные сценарии — отдельный job, не блокирует push  
- Матрица: requirements_spec ↔ T1–T17 ↔ pytest node id

**DevOps (`ci-marinet-steward` + `platform-ci-jenkins`):**

- Портировать JCasC из `-economics`; добавить job `drone-e2e-smoke` (timeout 30 min, warmup 120 s)  
- GitHub Actions для `-ai`: `unit.yml`, `integration.yml`, `e2e-smoke.yml` (nightly)  
- `make ports-check` при добавлении compose (изоляция local/jenkins)

---

### Итерация 4 — методист, техпис, PM

**Методист (`course-educator-platform`):**

- ОП-трек: lab «Phase 0 integration» = пройти smoke E2E + заполнить traceability worksheet  
- Slides 72118/SBOM — отдельный release train, не блокирует CI  
- Jupyter demos — после T16 (стабильный API)

**Техпис (`documentation-governance`):**

- Канон: `docs/integration/topic_map.yaml`, `docs/quick_start.md`, `requirements_spec.md`  
- Термин **СКИБ** — ГОСТ Р 72118-2025 формулировка  
- Индекс в README; doc-meta на active docs

**PM (`project-manager-ccpm`):**

| Milestone | Evidence | Buffer |
|-----------|----------|--------|
| M1: Topic map + ADR | PR merged, review SE | 3 d |
| M2: Smoke E2E green | Jenkins log, no mandatory skips | 5 d |
| M3: `-ai` operator → `-economics` sync | compose up, demo 15 min | 5 d |
| M4: Учебный release (slides subset) | PDF + rubric | 10 d |

**Критический путь:** M1 → M2 → M3. M4 параллельно после M1.

---

## development-plan {#development-plan}

Общий горизонт — см. [stage-1-plan](#stage-1-plan) для детализации **Этапа 1** (baseline phase 0). Ниже — последующие фазы после merge PR-E1 и smoke E2E green.

### Этап 1 — контракт, CI/E2E, PR-E1 (4–6 недель)

**Канонический план:** [stage-1-plan](#stage-1-plan) (подфазы **1a → 1b → 1c**).

Кратко: **1a** — только горизонтальные агенты (T1–T2, ADR); **1b** — подключение coding-пакетов + стабилизация integration/E2E (T14, gate PR-E1); **1c** — merge PR-E1 при green `ci-test` и `e2e-codespace`.

**Критерий выхода Этапа 1:** `make ci-test && make e2e-codespace` green; smoke E2E T14 без обязательных skip; PR-E1 в `master` (`-economics`).

---

### Фаза 2 — Расширение интеграции (6–8 недель, после Этапа 1)

| # | Работа | Результат |
|---|--------|-----------|
| 2.1 | Пирамида тестов (E2E-1…6) | CI docs в `docs/build_and_test.md` |
| 2.2 | Insurer adapter (T4) — `tem-bas-insurer-adapter` | topic alignment |
| 2.3 | Operator ↔ GCS стыковка (T5) | integration test |
| 2.4 | Cherry-pick negative E2E (PR-E2) | optional nightly job |
| 2.5 | Agent headless: `test-profile-refactor-*` | маркеры pytest, profiles |
| 2.6 | `tem-bas-uas-dev-company` — purchase lab hooks | UAS vitrine после PR-A1 |

**Критерий выхода:** nightly smoke 7/7 green; full E2E — weekly, ≤2 flaky/week.

---

### Фаза 3 — Учебный контур ОП (8–12 недель)

| # | Работа | Результат |
|---|--------|-----------|
| 3.1 | Labs phase 0 + rubrics | `docs/labs/` |
| 3.2 | Notebooks sync (T16) | demos без WIP |
| 3.3 | Slides release (72118, SBOM) | отдельный tag `teaching-YYYY-MM` |
| 3.4 | Метрики студентов (concept.md ОП) | autograding hooks |
| 3.5 | `tem-bas-purchase-*` интеграция | UAS purchase lab |
| 3.6 | Gamification elements | по `gamification-facilitator` workspace |

**Критерий выхода:** преподаватель проводит lab за 2 академических часа с demo-pack 45 min.

---

### Фаза 4 — Связь с открытой платформой (ongoing)

| # | Работа |
|---|--------|
| 4.1 | Регулярный export/import с `sbd-open-platform/code` (quarterly) |
| 4.2 | TOC-session при major release |
| 4.3 | Traceability requirements ↔ CI gates |
| 4.4 | КТ-ветка (simulators, swarm, AI) — отдельный repo/branch по [concept.md](concept.md) |

---

### Roadmap (кварталы)

```mermaid
gantt
  title TEM BAS Open Platform (OP track)
  dateFormat YYYY-MM
  section Stage1
  1a Contract T1-T2   :2026-07, 2w
  1b E2E CI stabilize  :2026-07, 4w
  1c PR-E1 merge       :2026-08, 1w
  section Phase2
  CI pyramid           :2026-09, 8w
  Insurer T4           :2026-10, 4w
  section Phase3
  Labs and slides      :2026-11, 12w
  section Phase4
  Platform sync        :2027-01, 12w
```

---

## stage-1-plan {#stage-1-plan}

**Этап 1** — единый baseline phase 0: контракт обмена, стабилизация integration/E2E и merge **PR-E1**. Coding-агенты по подсистемам подключаются **не раньше 1a-complete**, но **обязательно в 1b** — исправление integration/E2E входит в первый этап, а не откладывается на «Фазу 2».

### Подфазы

| Подфаза | Срок (ориентир) | Агенты | Работы | Gate |
|---------|-----------------|--------|--------|------|
| **1a — Контракт** | нед. 1–2 | Только [горизонталь](#system-agents): Architect, SE-SBD, техпис, оркестратор | T1, T2, T12; ADR-001/002 ✅; `topic_map.yaml` v0.2; PlantUML sequence; privacy review | `human_review`: владелец ОП утверждает topic map и T3-модель заказа |
| **1b — Integration/E2E** | нед. 3–5 | DevOps + QA **lead**; coding: `tem-bas-operator`, `tem-bas-aggregator`, `tem-bas-integration-stubs` | T10 compose `integration-phase0`; smoke E2E T14; починка `ci-integration-test`; прогон `e2e-codespace`; xfail/skip policy (E2E-2); warmup/topics (E2E-4) | `make ci-test` green; smoke T14 green локально и в CI |
| **1c — PR-E1 merge** | нед. 6 | Оркестратор + QA (sign-off) | Fast-forward `feature/uas-dev-company` → `master` в `-economics`; отчёт [pr-e1-gate-report.md](../../sbd-drones-economics/docs/pr-e1-gate-report.md) | **`ci-test` + `e2e-codespace` green**; push master разрешён |

**Блокер (2026-06-28):** PR-E1 заблокирован — `ci-integration-test` red, `e2e-codespace` не прогнан → работы **1b** приоритетны.

### Таблица: агент → фаза → deliverable → acceptance

| Агент | Фаза | Deliverable | Acceptance |
|-------|------|-------------|------------|
| Architect | 1a | `topic_map.yaml`, ADR-003 (compose profile), C4 container update | Review SE-SBD; нет противоречий с ADR-001/002 |
| SE-SBD | 1a | Traceability harm→ЦБ→topic→test; ЦПБ phase 0 | `human_review` владельца ОП |
| Техпис (`docs_change`) | 1a | doc-meta, README index, термин СКИБ | `check_documentation_versioning` pass |
| DevOps | 1b | compose `integration-phase0`, CI job smoke, `ports-check` | Jenkins/GHA log green на integration |
| QA | 1b | `test_phase0_smoke.py` / T14 matrix; skip→xfail policy | Smoke без mandatory skip на happy path |
| `tem-bas-operator` | 1b | Kafka align с topic map; shell+integration tests | pytest green в worktree issue |
| `tem-bas-aggregator` | 1b | `service_type: agro_field` stub/API (T3 мин.) | HTTP→Kafka message в smoke |
| `tem-bas-integration-stubs` | 1b | ORVD/DronePort stubs (T6–T7) | Детерминированный smoke без gateway timeout |
| Оркестратор | 1c | PR-E1 merge, gate report обновлён | `ci-test` + `e2e-codespace` green |
| PM | 1a–1c | Milestone M1–M2 evidence, buffer review | M2 закрыт до push master |
| Course-educator | 1a (parallel) | Lab outline «Phase 0 integration» (черновик) | Не блокирует 1c |

Агенты `tem-bas-insurer-adapter`, `tem-bas-uas-dev-company` — **после** 1c (Фаза 2), если архитектор явно не разблокирует раньше.

### Зависимости подфаз

```mermaid
flowchart LR
  A[1a Contract] --> B[1b Integration E2E]
  B --> C[1c PR-E1 merge]
  C --> D[PR-A1 topic sync -ai]
  B -.->|parallel| CE[Course-educator draft lab]
```

---

## backlog-sync {#backlog-sync}

Приоритеты phase 0 ([T1–T17](integration_process/phase0_remarks_and_technical_tasks.md)) в контексте плана:

| ID | План | Спринт |
|----|------|--------|
| T1, T2, T12 | Этап 1a | S1 |
| T3, T10, T14 | Этап 1b | S1–S2 |
| T6, T7 | Этап 1b | S2 |
| T4–T5 | Фаза 2 | S3–S4 |
| T8, T9, T13 | Фаза 2 | S4 |
| T15, T11 | Фаза 2 | по возможности |
| T16 | Фаза 3 | после M2 |
| T17 | Этап 1a | немедленно — свести с change_requests |

---

## next-actions {#next-actions}

**Немедленно (оркестратор / координатор):**

1. [x] Final merge integration + docs → `master` @ `7a0c87de`; ветка `test/integration-phase0-initiation` удалена (см. [final merge report](staged-push-reports/2026-06-28-final-merge-purge.md))  
2. [x] Создать issue «T1+T2: topic map» → [ISSUE-T1-T2-topic-map.md](integration/issues/ISSUE-T1-T2-topic-map.md) *(gh token invalid — локальный шаблон)*  
3. [x] Скопировать `.cursor/agents` subset (15 agents, 19 skills) + [directory.md](ai_sbd/agents/directory.md)  
4. [x] TOC brief + синтез ограничения → [tem_bas_phase0_constraint_2026-06-28.md](ai_sbd/agents/toc/sessions/tem_bas_phase0_constraint_2026-06-28/tem_bas_phase0_constraint_2026-06-28.md) *(полный headless — output_dir в open-platform)*  
5. [x] PR-A2 артефакты: `topic_map.yaml`, ADR-001, privacy review, `agent_skill_registry.json`  
6. [x] Privacy review → [privacy_review_ksa.md](integration/privacy_review_ksa.md); `.gitignore` обновлён  

**Этап 1 — rollout coding-агентов ([stage-1-plan](#stage-1-plan)):**

**1a (горизонталь only):**

- [x] ADR-001 (Kafka phase 0), ADR-002 (broker-agnostic target)
- [x] `topic_map.yaml` v0.1 — довести до v0.2 + `human_review`
- [ ] T3: утвердить модель заказа `agro_field` (владелец ОП)
- [ ] T12: PlantUML sequence в `docs/integration_process/diagrams/`
- [ ] Закрыть T17 ↔ change_requests CR5–CR10

**1b (подключить coding-пакеты + CI/E2E):**

- [ ] Issue + worktree: `tem-bas-integration-stubs` (T6–T7)
- [ ] Issue + worktree: `tem-bas-operator` (Kafka align, T14 consumer path)
- [ ] Issue + worktree: `tem-bas-aggregator` (T3 minimal, HTTP→Kafka)
- [ ] DevOps: compose profile `integration-phase0` (T10)
- [ ] QA + DevOps: smoke E2E T14; policy skip→xfail (E2E-2)
- [ ] Починить `ci-integration-test` (PR-E1 blocker)
- [ ] Прогнать и зафиксировать `make e2e-codespace` green
- [ ] **Jenkins recovery P0:** [ci_failure_joint_plan.md](ci_failure_joint_plan.md) — `jenkins-apply-jobs`, fix `e2e-codespace` jenkins profile, triage 6 job

**1c (merge):**

- [ ] QA sign-off на gate report
- [ ] PR-E1 merge при green `ci-test` + `e2e-codespace`
- [x] Push `master` `-economics` @ `7a0c87de` (2026-06-28 final merge)

**Human review (владелец ОП):**

- [x] Утвердить ADR-001 (Kafka) **для phase 0** — 2026-06-28
- [x] Broker-agnostic после phase 0 → [ADR-002](integration/adr/ADR-002-broker-agnostic-platform.md)
- [ ] Утвердить модель заказа `agro_field` (T3)
- [ ] Утвердить rollout coding-агентов (таблица [stage-1-plan](#stage-1-plan))
- [x] Merge: **PR-E1**; push master только при green tests

---

## vuca-block-merge-2026-06-28 {#vuca-block-merge-2026-06-28}

**Отчёт:** [staged-push-reports/2026-06-28-vuca-block-merge.md](staged-push-reports/2026-06-28-vuca-block-merge.md).

| DoD / AC | Result | Evidence |
|----------|--------|----------|
| Block C merged to `master` | **PASS** | merge `b435a3c8` (pre-session); QA fixes @ `d47ec827` |
| `make ci-test` green before push | **PASS** | `/tmp/ci-test-vuca-block-c.log`, re-run before push |
| `make e2e-codespace` green | **PASS** | 28 passed, 2 skipped — `/tmp/e2e-codespace-vuca-final4.log` |
| Integration branch pushed / integrated | **PASS** | `test/integration-phase0-initiation` merged + purged ([final-merge-purge](#final-merge-purge-2026-06-28)); bulk push pivot documented |
| `origin/master` only | **PASS** | post-push tip below |
| Slides/72118/ksa excluded | **PASS** | untracked local only |

**Session fixes (2026-06-28, agent):** insurer submodule `be3b3c74`, operator Kafka gateway restore, `.gitmodules` for notebook/cyber_drons/drone-operator-system, duplicate gitlink removal, operator `drones_net` compose.

**`origin/master` tip (post QA push):** `bc959b0`.

---

## final-merge-purge-2026-06-28 {#final-merge-purge-2026-06-28}

| Поле | Значение |
|------|----------|
| `origin/master` | `bc959b0` (after VUCA QA session; was `7a0c87de`) |
| Отчёт | [2026-06-28-final-merge-purge.md](staged-push-reports/2026-06-28-final-merge-purge.md) |
| Ветки | Только `master` (local + origin); purge **PASS** |
| QA unit | `make unit-test` — 70 passed (`-ai`) |
| QA ci-test | **PASS** — `make ci-test` green @ `d47ec827` |
| QA e2e | **PASS** — `make e2e-codespace` 28 passed, 2 skipped |

Ключевые merge: `ee4bd7a8` (integration → master), `7a0c87de` (economics e2e/submodule), VUCA QA fixes `b14cb2a..d47ec827`.

---

## ci-failure-joint-plan {#ci-failure-joint-plan}

**Статус:** active (2026-06-28)  
**Документ:** [ci_failure_joint_plan.md](ci_failure_joint_plan.md)

Совместный план DevOps / QA / SE / Architect / Educator / Orchestrator на восстановление Jenkins CI после массового red всех pipeline. Ключевая гипотеза P0: **`make e2e-codespace` не протягивает `E2E_RUN_MODE=jenkins`** в readiness/preflight (hardcode local-портов 8081/9092 при jenkins compose на 10801/19092).

**Ближайшие шаги:** P0-2 `make jenkins-apply-jobs` → P0-3 `drone-phase0-smoke` → P0-4 выравнивание Makefile → HR-1 triage sign-off.


*Документ подлежит обновлению после каждой интеграционной итерации. Версия 1.1 — двухуровневая модель агентов и детализация Этапа 1 (1a–1c).*
