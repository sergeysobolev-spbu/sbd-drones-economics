<!-- doc-meta: status=active version=1.1 updated=2026-06-28 -->

# Отчёт QA/SDET: верификация Jenkins CI (sbd-drones-economics)

**Дата прогона:** 2026-06-28  
**Исполнитель:** QA/SDET (регрессионные ворота, без правок CI)  
**Канон репозитория:** `/home/user/projects/sbd-drones-economics/sbd-drones-economics`

Worktree `sbd-drones-economics-ai` выведен ([migration_ai_worktree_retire.md](migration_ai_worktree_retire.md)). Каталог `sbd-drones-economics-ai/` **без `.git`** был создан повторно как stub только с этим отчётом (handoff QA в устаревший путь); канон — **только** `sbd-drones-economics/docs/ci_qa_verification_report.md`.

## Сокращения

| Сокращение | Расшифровка |
|------------|-------------|
| SCM | управление исходным кодом (checkout, субмодули, ветка) |
| infra | инфраструктура CI (JCasC, volume Jenkins, порты, Docker) |
| product | дефект продукта / тестов / Makefile-логики |

## Резюме

### Основной прогон (до repin gitlink)

| Ворота | Результат |
|--------|-----------|
| `make ports-check` | **PASS** |
| `make ci-config-check` | **FAIL** (субмодули) |
| `bash scripts/check_jenkins_submodule_pins.sh` | **FAIL** (9–10 gitlink не на upstream) |
| `make ci-recovery-check` | **FAIL** (W2-CH-1…3) |
| Jenkins `drone-phase0-smoke` (build #2) | **FAIL** (checkout SCM) |
| Jenkins UI: 6 job `drone-*` | **FAIL** (4 отсутствуют; stale `tem-*`) |
| `drone-unit` (отложено) | **SKIP** — субмодули не исправлены |

**Вердикт основного прогона:** **FAIL** — SCM-субмодули (9 gitlink) + stale JCasC.

### Addendum (после repin gitlink, commit `d468eab`)

| Ворота | Было | Стало |
|--------|------|-------|
| `make ci-config-check` | FAIL | **PASS** |
| `check_jenkins_submodule_pins.sh` | FAIL (9/14) | **PASS** (14/14) |
| `make jenkins-preflight` | FAIL | **PASS** |
| `make ci-recovery-check` | FAIL (W2-CH-1…3) | **PARTIAL** — W2-CH-1/2 PASS, W2-CH-3 FAIL |
| Jenkins UI 6 job | FAIL | **FAIL** (без изменений) |
| `drone-unit` | SKIP | **SKIP** — job отсутствует в UI |

**Блокер после addendum:** **infra** — `make jenkins-apply-jobs` (4 job + stale `feature/Jenkins` в существующих job).

### Актуальный статус (повторная верификация, HEAD `8f933c4`)

| Ворота | Результат |
|--------|-----------|
| `make ci-config-check` | **PASS** (14/14 submodule pins) |
| `make jenkins-jobs-verify` | **PASS** — все 6 `drone-*` в UI |
| Jenkins runtime canary | **не перезапускался** в этом прогоне |

**Текущий блокер для Wave 3:** runtime-матрица 6 job с `WAIT=1` и устранение stale checkout (`feature/Jenkins` в job, если ещё воспроизводится).

## 1. Структурные ворота

### 1.1 `make ports-check`

```
ports-check: OK — 9 local + 9 jenkins портов, коллизий нет; docs/ports.md согласован с e2e_ports.local.env
```

**Классификация:** — (gate green)

### 1.2 `make ci-config-check`

| Подшаг | Основной прогон | После `d468eab` |
|--------|-----------------|-----------------|
| `ports-check` | PASS | PASS |
| `phase0-smoke` (structural pytest) | PASS (2/2) | PASS |
| `check_jenkins_e2e_makefile.py` | PASS | PASS |
| `check_jenkins_submodule_pins.sh` | **FAIL** | **PASS** |
| `jenkins-preflight` (ветка) | не достигнут | **PASS** |

**Классификация блокера (основной прогон):** **SCM** — gitlink parent repo не совпадали с upstream remote. **Снято** repin в `d468eab`.

### 1.3 `check_jenkins_submodule_pins.sh` (основной прогон)

| Субмodule | SHA (кратко) | Remote | Статус |
|-----------|--------------|--------|--------|
| fabric-network | 97d2e9c… | gitflic smart-contracts-hlf | FAIL* |
| systems/DroneAnalytics | 8b52a3a… | GitHub OurPaintTeam | FAIL |
| systems/insurer | ef9c114… | GitHub DashDashh/Insurer | FAIL |
| systems/agrodron | 911905d… | gitflic cyber_drons | FAIL |
| systems/cyber_drons | cd638ad… | gitflic cyber_drons | FAIL |
| systems/drones | 791aa11… | GitHub AMCP-Drones | FAIL |
| systems/orvd_system | 44c8ecc… | — | OK |
| systems/Agregator | 08533d2… | GitHub DashDashh/Agregator | FAIL |
| systems/team1-regulator… | 1f2b1e0… | GitHub souma94621 | FAIL |
| systems/SITL-module | e0805f0… | GitHub SECS-team5 | FAIL |
| systems/gcs | 70483cc… | — | OK |
| systems/drone_port | 1e86cc2… | GitHub Kaitrye/DronePortGCS | FAIL |
| systems/drone-operator-system | 893f7ec… | — | OK |
| notebooks/…-jupyter-notebook | cef1c84… | — | OK |

\* В составе `ci-config-check` fabric-network однажды прошёл OK; при изолированном прогоне — FAIL (нестабильность сети/upstream или race ls-remote).

**После repin:** 14/14 OK (см. addendum).

### 1.4 `make ci-recovery-check`

| Checklist ID | Шаг | Основной прогон | После `d468eab` |
|--------------|-----|-----------------|-----------------|
| W2-CH-1 | `make ci-config-check` | FAIL | **PASS** |
| W2-CH-2 | `make jenkins-preflight` | FAIL | **PASS** |
| W2-CH-3 | `make jenkins-jobs-verify` | FAIL | FAIL → **PASS** на HEAD `8f933c4` |
| W2-CH-4 | `jenkins-build-phase0-smoke WAIT=1` | skipped | — |

`ci/jenkins/.env` присутствует; `GIT_BRANCH=master`, remote GitFlic — ветка существует.

## 2. Jenkins runtime

**Состояние:** `make jenkins-ps` — контейнер `drones-jenkins` Up (8080/50000).

### 2.1 Job в UI vs `jobs.canonical.txt`

**Ожидается (6):** `drone-unit`, `drone-integration`, `drone-e2e`, `drone-agrodron-security-monitor`, `drone-dummy-fabric-unit`, `drone-phase0-smoke`.

**Основной прогон (`jenkins-jobs-verify`):**

| Job | В casc | В UI | lastBuild |
|-----|--------|------|-----------|
| drone-unit | да | **нет** | — |
| drone-integration | да | **нет** | — |
| drone-e2e | да | **нет** | — |
| drone-agrodron-security-monitor | да | да | — |
| drone-dummy-fabric-unit | да | **нет** | — |
| drone-phase0-smoke | да | да | FAILURE #2 |
| tem-* (platform) | нет | да (11 job) | stale volume |

**После `make jenkins-apply-jobs` (HEAD `8f933c4`):** все 6 `drone-*` **в UI**.

**Классификация:** **infra** — JCasC не был применён после смены volume/конфига.

### 2.2 Канарейка `make jenkins-build-phase0-smoke WAIT=1`

| Job | Stage | Result | Классификация |
|-----|-------|--------|---------------|
| drone-phase0-smoke | Checkout | **FAILURE** | **SCM** |

Лог build #2: Jenkins ищет `refs/remotes/origin/feature/Jenkins` — ветка отсутствует на GitFlic. Локальный `ci/jenkins/.env` уже `GIT_BRANCH=master`, но job в UI не был обновлён (stale JCasC).

### 2.3 `drone-unit`

**SKIP** в основном прогоне и addendum — job отсутствовал в UI. После apply-jobs job **существует**; runtime-прогон **не выполнялся** в этом отчёте.

## 3. DevOps-скрипты: наличие и подключение

| Скрипт | Путь | Подключение в Makefile / checklist |
|--------|------|-------------------------------------|
| `check_jenkins_env.sh` | `scripts/` | `jenkins-preflight` (L473) |
| `check_jenkins_submodule_pins.sh` | `scripts/` | `ci-config-check` (L144), `jenkins-preflight` (L474) |
| `check_jenkins_e2e_makefile.py` | `scripts/` | `ci-config-check` (L143) |
| `ci_recovery_wave2_checklist.sh` | `scripts/` | `ci-recovery-check` (L148) |

Все четыре артефакта **существуют** и **проводятся** через цели Makefile. Документация: [ci_recovery_orchestration.md](ci_recovery_orchestration.md), [build_and_test.md](build_and_test.md).

## 4. Матрица evidence (job × stage × result × class)

| Job | Stage | Result | Class |
|-----|-------|--------|-------|
| *(structural)* | ports-check | PASS | — |
| *(structural)* | phase0-smoke pytest | PASS | — |
| *(structural)* | e2e-codespace Makefile contract | PASS | — |
| *(structural)* | submodule pins | FAIL → **PASS** | SCM → resolved |
| *(structural)* | jenkins-jobs-verify | FAIL → **PASS** | infra → resolved |
| drone-phase0-smoke | Checkout | FAILURE | SCM / infra (stale branch) |
| drone-unit | — | NOT RUN | infra (was missing) |
| drone-integration | — | NOT RUN | infra (was missing) |
| drone-e2e | — | NOT RUN | infra (was missing) |
| drone-agrodron-security-monitor | — | NOT RUN | — |
| drone-dummy-fabric-unit | — | NOT RUN | infra (was missing) |

## 5. Gaps для DevOps

1. ~~**SCM P0:** repin gitlink для 9 субмодулей~~ — **закрыто** (`d468eab`).
2. ~~**Infra P0:** `make jenkins-apply-jobs` — 6 `drone-*` в UI~~ — **закрыто** (HEAD `8f933c4`).
3. **Infra P1:** stale checkout `feature/Jenkins` в job — проверить повторным `jenkins-build-phase0-smoke WAIT=1`.
4. **Infra P1:** изоляция volume (`drones_jenkins_home` vs platform `tem-*`) — UI мог содержать stale `tem-*`.
5. **Wave 3:** полная матрица 6 job с `WAIT=1` ([ci_recovery_orchestration.md](ci_recovery_orchestration.md)).

## 6. Human review

| ID | Решение | Владелец |
|----|---------|----------|
| HR-QA-1 | FAIL основного прогона принят; structural gates после repin — partial sign-off | QA/SDET |
| HR-DevOps-1 | Submodule repin + JCasC reload | ci-marinet-steward |
| HR-3 | 6 job в UI | DevOps — **выполнено** |

**quality_grade (основной прогон):** structural ports/Makefile — **B**; SCM submodules + Jenkins UI — **F**; runtime canary — **F**.

**quality_grade (HEAD `8f933c4`):** structural + SCM — **A**; Jenkins UI sync — **B**; runtime matrix — **не оценивалось**.

---

*Следующий прогон QA: `make ci-recovery-check WAIT=1` и матрица 6 job после подтверждения green checkout.*
