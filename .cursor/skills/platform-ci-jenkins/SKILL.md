---
name: platform-ci-jenkins
description: Handles Jenkins and CI changes for the platform: JCasC jobs, Jenkinsfiles, local versus Jenkins port isolation, job application, and CI smoke validation. Use for Jenkins, CI, compose, e2e ports, or pipeline work.
---

# Platform CI Jenkins

## Use When

Apply this skill for changes to Jenkins jobs, `code/ci/Jenkinsfile*`, `code/ci/jenkins/*.yaml`, compose ports, e2e run modes, or CI documentation.

## Canonical Sources

### Open-platform (`sbd-open-platform-and-trainings-development`)

- `.cursor/rules/jenkins-jobs-casc.mdc`
- `.cursor/rules/jenkins-ports-local-isolation.mdc`
- `.cursor/rules/ports-registry.mdc`
- `code/docs/jenkins.md`
- `code/docs/ports.md`

### ТЭМ БАС drones (`sbd-drones-economics` / `-ai`)

- `docs/jenkins.md`, `docs/build_and_test.md`, `docs/ports.md`
- `config/e2e_ports.local.env`, `config/e2e_ports.jenkins.env`
- `ci/jenkins/casc.yaml`, `ci/jenkins/jobs.canonical.txt`
- `docs/ci_failure_joint_plan.md`, `docs/ci_agent_upskilling_plan.md`
- `docs/integration/adr/ADR-004-ci-port-profile-propagation.md`
- Skills: `skill_jenkins_casc_lifecycle`, `skill_ci_port_profile`, `skill_ci_failure_triage`

## Workflow

1. Determine whether the change affects job definitions, pipeline scripts, ports, compose, or documentation only.
2. For new or changed Jenkins jobs, update active JCasC and the canonical jobs list when needed.
3. Ensure Jenkins pipelines set `E2E_RUN_MODE=jenkins` and/or `INTEGRATION_RUN_MODE=jenkins` when they publish host ports.
4. Use Jenkins host URLs and bootstrap variables from `e2e_ports.jenkins.env` (path per repo); do not hardcode local ports.
5. For local Jenkins job visibility, plan `make jenkins-apply-jobs` after Jenkins is running.
6. Run or recommend `make ports-check` when ports, compose, or readiness URLs change.
7. **Drones economics:** before CI complete — `make ci-config-check`, `make jenkins-preflight`, propagate `E2E_RUN_MODE` through all `e2e-*` Makefile targets (see `skill_ci_port_profile`; caveat: `e2e-codespace` must not wait on local ports when mode=jenkins).

## Broker E2E Add-On

When Kafka, Mosquitto or MQTT is in scope, also apply `skill_devops_broker_cicd`:

- pin broker images and record versions in evidence;
- require broker healthchecks/readiness, not arbitrary sleeps;
- isolate local vs Jenkins host ports;
- save broker logs, compose config, JUnit artifacts;
- clean topics/groups/volumes after every CI run.

## Mandatory Preflight (drones — before «CI complete»)

```bash
make ci-config-check
make jenkins-preflight
make jenkins-apply-jobs    # after casc change
make jenkins-jobs-verify
```

Plus Jenkins smoke evidence (`make jenkins-build-phase0-smoke WAIT=1`) for QA regression sign-off.

## Guardrails

- Do not reuse local-profile host ports in Jenkins jobs.
- Do not assume adding a Jenkinsfile creates a UI job; JCasC reload is required.
- Do not access host services from Jenkins containers through `127.0.0.1:<local-port>`.
- Do not use `gh` from coding agents; GitHub operations belong to the coordinator.
- Do not claim CI complete on structural green only (`ci-config-check` ≠ Jenkins runtime).
- Do not leave `e2e-codespace` hardcoded to local ports when Jenkinsfile sets `E2E_RUN_MODE=jenkins`.
