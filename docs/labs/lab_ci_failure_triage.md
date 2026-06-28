<!-- doc-meta: status=active version=1.1 updated=2026-06-28 -->

# Лабораторная работа (фрагмент): разбор CI-отказа

**Дисциплина:** ПИКС / профессиональный трек ТЭМ БАС (ОП)  
**Длительность:** 45–60 мин (фрагмент demo-pack phase 0)  
**Предварительные требования:** базовый git, знакомство с `make help`, доступ к логам Jenkins (read-only) или учебному снимку лога.

## Цель

Научить студента и агента-стажёра **не путать** structural green, runtime green и Jenkins evidence; выполнить triage одного red pipeline по таксономии scm / infra / config / product.

## ЗУН

| Код | Формулировка |
|---|---|
| З-CI-01 | Типы CI gate: unit, structural smoke, integration, e2e, Jenkins |
| У-CI-01 | Запуск `make ci-config-check`, чтение failing stage в Jenkins |
| Н-CI-01 | Классификация отказа и формулировка bug report с evidence |

## Сценарий (на основе инцидента 2026-06-28)

Преподаватель показывает ситуацию: **локально** `make ports-check` и `make phase0-smoke` — OK; **`make ci-config-check`** может падать на `check_jenkins_submodule_pins`; **все** job `drone-*` в Jenkins — red на стадии Checkout или Submodule.

### Шаг 1 — Наблюдение (10 мин)

1. Открыть [ci_failure_joint_plan.md](../ci_failure_joint_plan.md) §A, гипотезы H2–H3.
2. Найти в логе строку `Couldn't find any revision to build`.
3. Зафиксировать: это **scm**, не «сломался Kafka».

**Вопрос для обсуждения:** почему green unit локально не доказывает готовность phase 0?

### Шаг 2 — Structural gate (10 мин)

```bash
cd /path/to/sbd-drones-economics
make ci-config-check
make jenkins-preflight   # при наличии ci/jenkins/.env
bash scripts/check_jenkins_submodule_pins.sh   # отдельно, если preflight не настроен
```

Если `check_jenkins_submodule_pins: FAIL` — класс **scm**, playbook в [jenkins.md](../jenkins.md#playbook-commit-не-на-remote-not-our-ref). Канарейка `drone-phase0-smoke` может быть green без init субмодулей.

Сопоставить вывод с [rubric_ci_literacy_agents.md](rubric_ci_literacy_agents.md) (L2).

### Шаг 3 — Контракт портов (15 мин)

1. Прочитать [ADR-004](../integration/adr/ADR-004-ci-port-profile-propagation.md) — C2 view.
2. Сравнить `AGREGATOR_PORT` в `config/e2e_ports.local.env` и `config/e2e_ports.jenkins.env`.
3. Выполнить `make e2e-jenkins-core` или `E2E_RUN_MODE=jenkins make e2e-codespace` — эмуляция `drone-e2e`.

**Вывод:** профили local и jenkins разведены; при red e2e после green structural — классифицировать **infra/readiness** vs **product**.

### Шаг 4 — Evidence bundle (10 мин)

Заполнить шаблон из `skill_ci_failure_triage`:

| Поле | Значение (учебный пример) |
|---|---|
| Job | drone-e2e |
| Stage | e2e-codespace |
| Class | infra / readiness |
| Hypothesis | H1 |
| Verification | `make e2e-jenkins-core` |

### Шаг 5 — Рефлексия (5 мин)

- Structural ≠ runtime ≠ Jenkins UI.
- Demo-pack 45 min для phase 0: показывать **канарейку** `drone-phase0-smoke`, не только unit.

## Критерии приёмки (рубрика L2)

- [ ] Студент различает минимум 3 класса отказа из taxonomy.
- [ ] Выполнен `make ci-config-check` с интерпретацией результата.
- [ ] Bug report содержит stage, snippet, class, verification command.
- [ ] Не заявлено «CI готов» без Jenkins smoke или явного defer.

## Связь с demo-pack

| Demo-pack шаг | Содержание lab |
|---|---|
| 0–10 min | ConOps phase 0, topic map (без CI) |
| 10–25 min | `make phase0-smoke` structural |
| 25–40 min | **этот фрагмент** — triage red pipeline |
| 40–45 min | human_review: что показываем при partial green |

Полный demo-pack 45 min — критерий фазы 3 в [ai_dev_tasks.md](../ai_dev_tasks.md#фаза-3--учебный-контур-оп-812-недель).

## Материалы преподавателя

- Снимок Jenkins log (Checkout fail) — выдать отдельным файлом или issue.
- [ci_agent_upskilling_plan.md](../ci_agent_upskilling_plan.md) — для продвинутых слушателей (агенты).
- `human_review`: методист подтверждает, что при red e2e лабораторный зачёт не подменяется green unit.
