---
name: skill_ci_failure_triage
description: Triage Jenkins and local CI failures for sbd-drones-economics — job×stage matrix, evidence bundle, failure taxonomy (infra/product/scope/SCM), pivot rules. Use for qa-marinet-spec, ci-marinet-steward, ci_failure_recovery, mass pipeline red, or regression after CI config changes.
---

# Skill CI Failure Triage

## Use When

Apply when:

- **все или несколько** Jenkins job `drone-*` red после изменений CI;
- локально `make ci-config-check` green, но Jenkins red (или наоборот);
- sprint QA/DevOps завершился без Jenkins smoke evidence;
- нужна классификация отказа и evidence bundle для human_review.

**Первый consumer:** `qa-marinet-spec`, координатор `ci_failure_recovery`.

## Canonical Sources

- `docs/ci_failure_joint_plan.md` — гипотезы H1–H9, P0/P1 план
- `docs/ci_agent_upskilling_plan.md` — матрица пробелов агентов
- `docs/jenkins.md` — troubleshooting, `make jenkins-preflight`
- `docs/build_and_test.md` — gate table local vs jenkins
- `config/e2e_ports.local.env`, `config/e2e_ports.jenkins.env`
- `docs/ai_agents_improvements.md` §4.4–§4.5 — автономность и урок регрессии

## Failure Taxonomy

| Класс | Признаки | Типовые причины | Следующий шаг |
|---|---|---|---|
| **scm** | Checkout, «Couldn't find revision», submodule | `GIT_BRANCH` не на remote; commit субмодуля не запушен | `make jenkins-preflight`; push / fix `.env` |
| **infra** | Port bind, compose timeout, docker.sock | local/jenkins port mix; stack не down; `e2e-codespace` без `E2E_RUN_MODE` | `make ports-check`; `E2E_RUN_MODE=jenkins make e2e-codespace` |
| **config** | JCasC drift, job missing in UI | casc не reload; volume смешал job | `make jenkins-apply-jobs`; `make jenkins-jobs-verify` |
| **readiness** | «did not respond», health timeout | wait на local-порт при jenkins compose | `skill_ci_port_profile` |
| **product** | assertion, topic mismatch | контракт phase 0, код Operator/Aggregator | классифицировать; issue с TR-PH0-* |
| **scope** | skip budget, xfail без issue | soft-green маскирует gap | audit skip; E2E-2 policy |
| **flake** | intermittent, clean retry green | timing, dirty broker state | `skill_sdet_broker_e2e` triage |

## Triage Workflow

1. **Structural gate first** — `make ci-config-check` (ports + phase0 structural).
2. **SCM gate** — `make jenkins-preflight` если Jenkins использует remote checkout.
3. **Jobs sync** — `make jenkins-jobs-verify` (Jenkins running).
4. **Канарейка** — `make jenkins-build-phase0-smoke WAIT=1` или минимальный `drone-unit`.
5. **Матрица job × stage × snippet** — заполнить таблицу (шаблон ниже).
6. **Evidence bundle** — JUnit, compose logs, классификация, top-3 гипотезы.
7. **Pivot** — при infra-red не early exit; см. sprint-autonomy policy.

## Job Matrix Template

```markdown
| Job | Failing stage | Log snippet | Class | Hypothesis ID | Owner |
|---|---|---|---|---|---|
| drone-phase0-smoke | Checkout | Couldn't find revision | scm | H3 | DevOps |
| drone-e2e | e2e-codespace | Agregator did not respond on 8081 | infra | H1 | DevOps |
```

## Evidence Bundle (обязательный для red Jenkins)

- [ ] SHA workspace vs remote branch
- [ ] Output `make ci-config-check`
- [ ] Output `make jenkins-preflight` (если remote SCM)
- [ ] `make jenkins-jobs-verify` или скрин UI job list
- [ ] Jenkins build log: failing stage + 20 строк контекста
- [ ] JUnit / pytest summary (fail/skip/xfail counts)
- [ ] Классификация: scm / infra / config / readiness / product / scope / flake
- [ ] Рекомендация: fix owner + verification command

## QA Regression Gate

**Запрещено** объявлять CI change complete или sprint QA complete без:

- минимум **одного** Jenkins build smoke (`make jenkins-build-phase0-smoke WAIT=1` или эквивалент);
- evidence bundle при red;
- явного defer с owner/issue если Jenkins недоступен.

Локальный green **не заменяет** Jenkins evidence.

## Output Contract

```markdown
## triage_scope
## structural_gates_run
## job_matrix
## failure_classification
## top_hypotheses
## evidence_bundle
## pivot_or_next_fix
## human_review
## next_step
```

## Guardrails

- Не объявлять «infra OK» только по `make ports-check` без jenkins-profile emulation при изменении e2e Makefile.
- Не закрывать triage без классификации каждого red job.
- Не маскировать product red как flake без повторного clean-run evidence.
- Не использовать green unit как доказательство E2E readiness.
