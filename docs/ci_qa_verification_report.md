<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

# Отчёт QA/SDET: верификация Jenkins CI (sbd-drones-economics)

**Дата прогона:** 2026-06-28  
**Исполнитель:** QA/SDET (регрессионные ворота, без правок CI)  
**Канон репозитория:** `/home/user/projects/sbd-drones-economics/sbd-drones-economics`  
**Зеркало отчёта:** `sbd-drones-economics-ai/docs/ci_qa_verification_report.md` (worktree `-ai` выведен; каталог создан для handoff).

## Сокращения

| Сокращение | Расшифровка |
|------------|-------------|
| SCM | управление исходным кодом (checkout, субмодули, ветка) |
| infra | инфраструктура CI (JCasC, volume Jenkins, порты, Docker) |
| product | дефект продукта / тестов / Makefile-логики |

## Резюме

| Ворота | Результат |
|--------|-----------|
| `make ports-check` | **PASS** |
| `make ci-config-check` | **FAIL** (субмодули) |
| `bash scripts/check_jenkins_submodule_pins.sh` | **FAIL** (9–10 gitlink не на upstream) |
| `make ci-recovery-check` | **FAIL** (W2-CH-1…3) |
| Jenkins `drone-phase0-smoke` (build #2) | **FAIL** (checkout SCM) |
| Jenkins UI: 6 job `drone-*` | **FAIL** (4 отсутствуют; stale `tem-*`) |
| `drone-unit` (отложено) | **SKIP** — субмодули не исправлены |

**Общий вердикт регрессии:** **FAIL** — Wave 2 coding и Jenkins green matrix заблокированы до устранения SCM-субмодулей и `make jenkins-apply-jobs`.

## 1. Структурные ворота

### 1.1 `make ports-check`

```
ports-check: OK — 9 local + 9 jenkins портов, коллизий нет; docs/ports.md согласован с e2e_ports.local.env
```

**Классификация:** — (gate green)

### 1.2 `make ci-config-check`

| Подшаг | Результат |
|--------|-----------|
| `ports-check` | PASS |
| `phase0-smoke` (structural pytest) | PASS (2/2) |
| `check_jenkins_e2e_makefile.py` | PASS |
| `check_jenkins_submodule_pins.sh` | **FAIL** |
| `jenkins-preflight` (ветка) | не достигнут из-за submodule FAIL |

**Классификация блокера:** **SCM** — gitlink parent repo не совпадают с upstream remote.

### 1.3 `check_jenkins_submodule_pins.sh` (отдельный прогон)

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

\* В составе `ci-config-check` fabric-network однажды прошёл OK; при изолированном прогоне — FAIL (нестабильность сети/upstream или race ls-remote). Требует повторной верификации DevOps.

### 1.4 `make ci-recovery-check`

| Checklist ID | Шаг | Результат | Классификация |
|--------------|-----|-----------|---------------|
| W2-CH-1 | `make ci-config-check` | FAIL | SCM |
| W2-CH-2 | `make jenkins-preflight` | FAIL (submodule pins после OK ветки master) | SCM |
| W2-CH-3 | `make jenkins-jobs-verify` | FAIL | infra |
| W2-CH-4 | `jenkins-build-phase0-smoke WAIT=1` | skipped (WAIT=0 в checklist) | — |

`ci/jenkins/.env` присутствует; `GIT_BRANCH=master`, remote GitFlic — ветка существует (`jenkins-preflight: OK` для refs/heads/master).

## 2. Jenkins runtime

**Состояние:** `make jenkins-ps` — контейнер `drones-jenkins` Up (8080/50000).

### 2.1 Job в UI vs `jobs.canonical.txt`

**Ожидается (6):** `drone-unit`, `drone-integration`, `drone-e2e`, `drone-agrodron-security-monitor`, `drone-dummy-fabric-unit`, `drone-phase0-smoke`.

**Фактически в UI (`jenkins-jobs-verify`):**

| Job | В casc | В UI | lastBuild |
|-----|--------|------|-----------|
| drone-unit | да | **нет** | — |
| drone-integration | да | **нет** | — |
| drone-e2e | да | **нет** | — |
| drone-agrodron-security-monitor | да | да | — |
| drone-dummy-fabric-unit | да | **нет** | — |
| drone-phase0-smoke | да | да | FAILURE #2 |
| tem-* (platform) | нет | да (11 job) | stale volume |

**Классификация:** **infra** — JCasC не применён после смены volume/конфига; смешение `tem-*` и `drone-*`.

**Рекомендация DevOps (не выполнялось QA):** `make jenkins-apply-jobs` после green submodule pins.

### 2.2 Канарейка `make jenkins-build-phase0-smoke WAIT=1`

| Job | Stage | Result | Классификация |
|-----|-------|--------|---------------|
| drone-phase0-smoke | Checkout | **FAILURE** | **SCM** |

Лог build #2: Jenkins ищет `refs/remotes/origin/feature/Jenkins` — ветка отсутствует на GitFlic. Локальный `ci/jenkins/.env` уже `GIT_BRANCH=master`, но **job в UI не обновлён** (stale JCasC).

### 2.3 `drone-unit`

**SKIP** — прогон не запускался: 9 субмодулей с невалидными gitlink блокируют `jenkins-preflight` и типичный checkout с `submodule update`.

## 3. DevOps-скрипты: наличие и подключение

| Скрипт | Путь | Подключение в Makefile / checklist |
|--------|------|-------------------------------------|
| `check_jenkins_env.sh` | `scripts/` | `jenkins-preflight` (L473) |
| `check_jenkins_submodule_pins.sh` | `scripts/` | `ci-config-check` (L144), `jenkins-preflight` (L474) |
| `check_jenkins_e2e_makefile.py` | `scripts/` | `ci-config-check` (L143) |
| `ci_recovery_wave2_checklist.sh` | `scripts/` | `ci-recovery-check` (L148) |

Все четыре артефакта **существуют** и **проводятся** через цели Makefile. Документация: `docs/ci_recovery_orchestration.md`, `docs/build_and_test.md`.

## 4. Матрица evidence (job × stage × result × class)

| Job | Stage | Result | Class |
|-----|-------|--------|-------|
| *(structural)* | ports-check | PASS | — |
| *(structural)* | phase0-smoke pytest | PASS | — |
| *(structural)* | e2e-codespace Makefile contract | PASS | — |
| *(structural)* | submodule pins | FAIL | SCM |
| *(structural)* | jenkins-jobs-verify | FAIL | infra |
| drone-phase0-smoke | Checkout | FAILURE | SCM |
| drone-unit | — | NOT RUN | SCM (blocked) |
| drone-integration | — | NOT RUN | infra (job missing) |
| drone-e2e | — | NOT RUN | infra (job missing) |
| drone-agrodron-security-monitor | — | NOT RUN | — |
| drone-dummy-fabric-unit | — | NOT RUN | infra (job missing) |

## 5. Gaps для DevOps (без реализации в этом прогоне)

1. **SCM P0:** push upstream или repin gitlink для 9 субмодулей (см. таблицу §1.3).
2. **Infra P0:** `make jenkins-apply-jobs` — синхронизировать 6 `drone-*`, убрать зависимость job от `feature/Jenkins`.
3. **Infra P1:** изоляция volume (`drones_jenkins_home` vs platform `tem-*`) — частично в `.env`, UI ещё содержит stale job.
4. **Remote sync:** локальный `master` ahead 4 commits; `git pull` с GitFlic недоступен (DNS `gitflic-lk.ru`) — риск расхождения local vs Jenkins remote SHA.
5. **Wave 3:** после green W2-CH-1…3 — полная матрица 6 job с `WAIT=1` ([ci_recovery_orchestration.md](ci_recovery_orchestration.md)).

## 6. Human review

| ID | Решение | Владелец |
|----|---------|----------|
| HR-QA-1 | Принять FAIL регрессии; не sign-off CI recovery | QA/SDET |
| HR-DevOps-1 | Submodule strategy + JCasC reload | ci-marinet-steward |
| HR-3 | 6 job в UI после apply-jobs | DevOps |

**quality_grade:** structural ports/Makefile — **B**; SCM submodules + Jenkins UI — **F**; runtime canary — **F**.

---

*Следующий прогон QA: после DevOps fix — повтор `make ci-recovery-check WAIT=1` и матрица 6 job.*
