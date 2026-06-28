---
name: platform-ci-jenkins
description: Handles Jenkins and CI changes for the platform: JCasC jobs, Jenkinsfiles, local versus Jenkins port isolation, job application, and CI smoke validation. Use for Jenkins, CI, compose, e2e ports, or pipeline work.
---

# Platform CI Jenkins

## Use When

Apply this skill for changes to Jenkins jobs, `code/ci/Jenkinsfile*`, `code/ci/jenkins/*.yaml`, compose ports, e2e run modes, or CI documentation.

## Canonical Sources

- `.cursor/rules/jenkins-jobs-casc.mdc`
- `.cursor/rules/jenkins-ports-local-isolation.mdc`
- `.cursor/rules/ports-registry.mdc`
- `code/docs/jenkins.md`
- `code/docs/ports.md`

## Workflow

1. Determine whether the change affects job definitions, pipeline scripts, ports, compose, or documentation only.
2. For new or changed Jenkins jobs, update active JCasC and the canonical jobs list when needed.
3. Ensure Jenkins pipelines set `E2E_RUN_MODE=jenkins` and/or `INTEGRATION_RUN_MODE=jenkins` when they publish host ports.
4. Use Jenkins host URLs and bootstrap variables from `code/config/e2e_ports.jenkins.env`; do not hardcode local ports.
5. For local Jenkins job visibility, plan `make jenkins-apply-jobs` after Jenkins is running.
6. Run or recommend `make ports-check` when ports, compose, or readiness URLs change.

## Guardrails

- Do not reuse local-profile host ports in Jenkins jobs.
- Do not assume adding a Jenkinsfile creates a UI job; JCasC reload is required.
- Do not access host services from Jenkins containers through `127.0.0.1:<local-port>`.
- Do not use `gh` from coding agents; GitHub operations belong to the coordinator.

## Sprint mode (DevOps time-boxed sprints)

Apply when the orchestrator assigns a **time-boxed DevOps sprint** with CI/E2E/infra goals. Canonical policy: `docs/ai_dev_tasks.md#sprint-autonomy-policy`, `docs/ai_agents_improvements.md` §4.4.

### Time budget

- Use the **full allocated time**; do not stop after the first red integration if **e2e is the sprint goal**.
- Early success on unit-only gates → continue toward integration and **`make e2e-codespace`**.

### Port cleanup and retry

| Symptom | Action (autonomous) |
|---|---|
| `port already allocated` (e.g. 8081) | `docker compose down` for conflicting stack; `docker ps`; kill stale containers; retry |
| Integration red, unit green | **Not** done — cleanup ports, retry `make ci-integration-test`, then e2e-up path |
| Stack partial | Logs from failing service; compose profile fix; retry with clean project name |

Do not report «blocked on port» without attempting cleanup and at least one retry.

### E2E retry loop

1. Ensure broker/network up (`make docker-up` / profile per `integration-phase0-compose.md`).
2. `make ci-integration-test` → if red, port cleanup → retry.
3. **`make e2e-codespace`** — mandatory verification before sprint complete when E2E is in goals.
4. On e2e red: capture logs, classify infra vs product, fix infra in scope, retry.

### Pivot on block

- Product fix outside DevOps scope → pivot: CI exclude docs, compose stub, gate table, `phase0-smoke` infra, ports.md sync.
- Do not idle; do not exit sprint with broken e2e unless scope explicitly excludes it (document why).

### Autonomy

- Run `make`, `docker compose`, port checks, and retry loops **without human confirmation** per step.
- Stay within repository boundaries unless explicitly instructed otherwise.
