---
name: skill_jenkins_casc_lifecycle
description: JCasC lifecycle for sbd-drones-economics — casc.yaml, jobs.canonical.txt, jenkins-apply-jobs, jenkins-jobs-verify, volume isolation, GIT_BRANCH preflight. Use when adding Jenkins jobs, fixing "job in git but not in UI", or after casc/Jenkinsfile changes.
---

# Skill Jenkins JCasC Lifecycle

## Use When

Apply when:

- добавлен или изменён `ci/jenkins/casc.yaml` или `ci/Jenkinsfile.*`;
- job есть в репозитории, но **отсутствует в Jenkins UI**;
- после merge CI config нужно подтвердить видимость `drone-*` job;
- смешение job платформы (`tem-*`) и drones на одном Jenkins volume.

**Consumer:** `ci-marinet-steward`, task `jenkins_or_ci_change`, `ci_failure_recovery`.

## Canonical Sources

- `ci/jenkins/casc.yaml` — единственный источник job definitions
- `ci/jenkins/jobs.canonical.txt` — канонический список имён
- `ci/jenkins/.env` / `.env.example` — `GIT_REPO_URL`, `GIT_BRANCH`
- `docs/jenkins.md`
- `Makefile` targets: `jenkins-preflight`, `jenkins-apply-jobs`, `jenkins-jobs-verify`
- `docs/ci_failure_joint_plan.md` — H2, P0-2

## Lifecycle Checklist (Post-JCasC)

Выполнять **после каждого** изменения casc или нового Jenkinsfile:

```bash
make jenkins-ps                    # Jenkins running
make jenkins-preflight             # GIT_BRANCH exists on remote (skip for file:// SCM)
make jenkins-apply-jobs            # POST configuration-as-code/reload + verify
make jenkins-jobs-verify           # API list matches jobs.canonical.txt
```

**Недостаточно:** только git commit, только `docker compose restart`, ручное создание job в UI.

## Volume Isolation (drones vs platform)

| Риск | Симптом | Мitigation |
|---|---|---|
| Shared `jenkins_home` | В UI `tem-*` вместо `drone-*` или наоборот | Отдельный compose project / volume (`drones_jenkins_home`) |
| Stale UI state | Новый job не появляется | `make jenkins-apply-jobs` |
| Wrong GIT_BRANCH | All jobs fail at Checkout | `make jenkins-preflight`; default `master` |

## SCM Preflight (`jenkins-preflight`)

Перед `jenkins-apply-jobs`:

1. Прочитать `GIT_BRANCH` из `ci/jenkins/.env`.
2. Для remote URL — проверить `refs/heads/${BRANCH}` на `GIT_REPO_URL`.
3. Типичная ошибка: `feature/Jenkins` без push на GitFlic.

Локальный `file://` SCM — remote-ветка не проверяется (см. `scripts/check_jenkins_env.sh`).

## Canonical Jobs (drones economics)

Сверять с `ci/jenkins/jobs.canonical.txt`, например:

- `drone-unit`
- `drone-integration`
- `drone-e2e`
- `drone-phase0-smoke`
- (и др. по канону файла)

## Output Contract

```markdown
## casc_change_scope
## preflight_results
## jobs_expected_vs_actual
## volume_and_scm_risks
## validation_commands
## human_review
## next_step
```

## Guardrails

- Не заявлять job доступной без `jenkins-jobs-verify` или эквивалентного API diff.
- Не полагаться на первый старт контейнера — volume сохраняет старое состояние.
- Не хардкодить `GIT_BRANCH` в Jenkinsfile — только `.env` / JCasC env.
- Coding-агенты **не** используют `gh`; board operations — координатор.
