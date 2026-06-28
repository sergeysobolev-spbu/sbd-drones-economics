<!-- doc-meta: status=active version=1.0 updated=2026-06-28 audience=teaching -->

# Рубрика и чек-лист: CI literacy для агентов и студентов ПИКС

**Назначение:** оценивать зрелость работы с CI/CD контура `sbd-drones-economics`.  
**Skill агента:** `skill_course_educator_platform`, `skill_agent_zun_development`.  
**Связь:** [lab_ci_failure_triage.md](lab_ci_failure_triage.md), [ci_agent_upskilling_plan.md](../ci_agent_upskilling_plan.md).

## Шкала L0–L3

| Уровень | Описание |
|---|---|
| L0 | Не различает unit и E2E; объявляет «готово» по одному green target |
| L1 | Наблюдает red/green; находит артеfact в Jenkins UI |
| L2 | Применяет gates и preflight; интерпретирует skip vs fail |
| L3 | Анализирует contract breaks; triage с evidence; связывает с TR-PH0-* / TR-CI-* |

## Рубрика по критериям

| Критерий | L1 (наблюдение) | L2 (применение) | L3 (анализ) |
|---|---|---|---|
| Профили портов local/jenkins | знает, что файлы разные | `make ports-check`; читает `e2e_ports.*.env` | объясняет H1 и ADR-004; находит hardcode в Makefile |
| JCasC lifecycle | знает, что job из yaml | `make jenkins-apply-jobs`, `jenkins-jobs-verify` | диагностирует stale volume / missing job (H2) |
| SCM preflight | видит Checkout fail | `make jenkins-preflight` | связывает GIT_BRANCH с remote; pin субмодулей; класс scm |
| Тип gate | unit vs e2e | `make ci-config-check` vs `e2e-codespace` | gate table + Jenkins smoke requirement |
| skip / xfail / fail | видит skip в логе | считает mandatory skip budget | E2E-2 policy; не soft-green |
| Evidence | скачивает console log | JUnit + compose log + class | полный evidence bundle; pivot без early exit |
| Автономность спринта | — | pivot при infra-red | §4.4–§4.5 ai_agents_improvements |

## Чек-лист агента DevOps (`ci-marinet-steward`) — перед «CI complete»

- [ ] `make ci-config-check`
- [ ] `make jenkins-preflight` (если remote SCM)
- [ ] `make jenkins-apply-jobs` + `make jenkins-jobs-verify` после casc change
- [ ] `make ports-check` после изменения портов
- [ ] `E2E_RUN_MODE=jenkins` emulation: `make e2e-jenkins-core`
- [ ] Документация: `jenkins.md`, `build_and_test.md`, `ports.md`, ADR при contract change
- [ ] **Не** claim complete без минимум одного Jenkins smoke evidence

## Чек-лист агента QA (`qa-marinet-spec`) — regression gate

- [ ] Triage matrix job × stage при mass red
- [ ] `make ci-config-check` воспроизведён
- [ ] Минимум один `make jenkins-build-phase0-smoke WAIT=1` (или documented Jenkins unavailable)
- [ ] Failure taxonomy для каждого red job
- [ ] Sprint complete только с E2E goal met или documented defer + owner
- [ ] Не early exit при red integration/e2e (sprint-autonomy)

## Чек-лист координатора

- [ ] Issue In Progress до APPLY=1
- [ ] Пакет `ci_failure_recovery` маршрутизирован на skills triage + port profile + JCasC
- [ ] human_review HR-1…HR-7 из joint plan при закрытии инцидента

## Зачётная политика (учебный контур)

- **Зачёт lab «Разбор CI-отказа»:** L2 минимум по 4 критериям из таблицы.
- **Не засчитывается:** только green `make unit-test` при цели lab «CI literacy».
- **Demo-pack partial green:** преподаватель объявляет, какие шаги demo пропущены и почему (defer + issue).

## human_review

Владелец рубрики: методист / преподаватель ПИКС. Обновление при изменении Makefile gates или joint plan P1.
