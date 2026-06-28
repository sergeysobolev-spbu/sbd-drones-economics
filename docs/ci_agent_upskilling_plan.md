<!-- doc-meta: status=active version=1.0 updated=2026-06-28 audience=internal -->

# План upskilling агентов: регрессия Jenkins CI (DevOps / QA)

Документ реализует §C [ci_failure_joint_plan.md](ci_failure_joint_plan.md): матрица пробелов, артефакты навыков, патчи агентов и правил, учебный и архитектурный контур.

**Инцидент:** DevOps-агент добавил CI (порты, JCasC, `e2e-codespace`), локально structural gates green, **все** Jenkins pipeline red; QA не поймал регрессию до merge.

---

## 1. Ситуация

| Факт | Следствие |
|---|---|
| `make ci-config-check` OK локально | Structural ≠ Jenkins runtime |
| Checkout fail (`GIT_BRANCH`, volume) | scm/config класс, не product |
| `e2e-codespace` без полного `E2E_RUN_MODE` | H1 contract break (ADR-004) |
| QA sprint early exit | §4.4 ai_agents_improvements — нарушение E2E gate |
| Agents без triage skill | Нет обязательного Jenkins smoke |

---

## 2. Матрица пробелов (agent × capability × patch)

| Агент | Пробел | Новый / обновлённый skill или patch |
|---|---|---|
| `ci-marinet-steward` | JCasC reload, volume isolation | **`skill_jenkins_casc_lifecycle`** + Post-JCasC checklist в agent |
| `ci-marinet-steward` | Port profile propagation | **`skill_ci_port_profile`** + mandatory preflight в agent |
| `ci-marinet-steward` | Broker E2E + jenkins profile | `skill_devops_broker_cicd` § E2E_RUN_MODE; `platform-ci-jenkins` § BAS |
| `qa-marinet-spec` | Mass CI triage | **`skill_ci_failure_triage`** |
| `qa-marinet-spec` | Regression без Jenkins | Agent patch: Jenkins smoke gate |
| `qa-marinet-spec` | Early exit / soft-green | `skill_sdet_broker_e2e` + sprint rule § mandatory gates |
| `software-architect-c4` | CI contract breaks invisible | **ADR-004** + C2 container view |
| `course-educator-platform` | CI literacy не формализована | **rubric** + **lab_ci_failure_triage** + demo-pack pointers |
| `systems-engineer-sbd` | V&V chain breaks at infra | joint plan Ш4→Ш9; TR-CI-001…003 |
| Координатор | No `ci_failure_recovery` route | **`agent_skill_registry.json`** task type |
| `tem-bas-operator` | jenkins KAFKA_* overrides | `skill_integration_phase0_contracts` (existing) |

---

## 3. Реализованные артефакты

### 3.1. Skills (новые)

| Skill | Путь |
|---|---|
| CI failure triage | `.cursor/skills/skill_ci_failure_triage/SKILL.md` |
| JCasC lifecycle | `.cursor/skills/skill_jenkins_casc_lifecycle/SKILL.md` |
| CI port profile | `.cursor/skills/skill_ci_port_profile/SKILL.md` |

### 3.2. Агенты (обновлены)

| Агент | Изменение |
|---|---|
| `ci-marinet-steward.md` | ТЭМ БАС drones; preflight gates; skills triage/JCasC/port |
| `qa-marinet-spec.md` | BAS QA; Jenkins regression smoke gate; triage skill |

### 3.3. Правила

| Rule | Изменение |
|---|---|
| `sprint-autonomy-qa-devops.mdc` | Mandatory `jenkins-preflight` + `ci-config-check` before CI complete; link joint plan |

### 3.4. Registry

| task_type | Skills |
|---|---|
| `jenkins_or_ci_change` | + recommended: port profile, JCasC lifecycle, devops broker |
| `ci_failure_recovery` (new) | required: triage, platform-ci-jenkins, human_review |

### 3.5. Архитектура

| Арtefact | Путь |
|---|---|
| ADR port propagation | `docs/integration/adr/ADR-004-ci-port-profile-propagation.md` |

### 3.6. Учебный контур

| Арtefact | Путь |
|---|---|
| Lab fragment | `docs/labs/lab_ci_failure_triage.md` |
| Rubric CI literacy | `docs/labs/rubric_ci_literacy_agents.md` |
| Demo-pack mapping | lab § «Связь с demo-pack» → `ai_dev_tasks.md` фаза 3 |

### 3.7. Документация

| Документ | Изменение |
|---|---|
| `ai_agents_improvements.md` | §4.5 урок регрессии Jenkins |
| `platform-ci-jenkins/SKILL.md` | § ТЭМ БАС drones economics |

---

## 4. Перспектива методиста (course-educator)

**role_mode:** `both`

- **ЗУН:** rubric L1–L3 в [rubric_ci_literacy_agents.md](labs/rubric_ci_literacy_agents.md).
- **Lab:** 45–60 min фрагмент в demo-pack — [lab_ci_failure_triage.md](labs/lab_ci_failure_triage.md).
- **Guardrail:** green unit **не** засчитывается как phase 0 readiness в зачёте.
- **human_review:** методист при partial green demo-pack.

---

## 5. Перспектива архитектора C4

**architecture_scope:** CI/CD deployment view для drones economics.

- **C2:** Jenkins container → docker.sock → generated compose → Kafka/Aggregator (ADR-004 diagram).
- **Contract breaks:** SCM vs runtime vs ports — три независимых boundary verification.
- **validation_plan:** structural (`ci-config-check`) → jenkins emulation → Jenkins smoke job.

---

## 6. Verification (после rollout skills)

```bash
# existence
test -f .cursor/skills/skill_ci_failure_triage/SKILL.md
python3 -m json.tool config/agent_skill_registry.json

# gates (локально)
make ci-config-check
make jenkins-preflight
```

Jenkins live smoke — ответственность DevOps после P0 joint plan.

---

## 7. human_review

| Checkpoint | Владелец |
|---|---|
| HR-6 Agent skill rollout | Orchestrator |
| HR-5 Учебный demo-pack при partial green | Course-educator |
| HR-2 Merge CI fix + upskilling docs | Repo maintainer |

---

## 8. next_step

1. Coding-пакет `ci-recovery-e2e-profile`: fix Makefile `e2e-codespace` + `skill_ci_port_profile`.
2. QA: прогон triage matrix на running Jenkins (P0-1 joint plan).
3. Методист: включить lab в фазу 3 `ai_dev_tasks.md`.
