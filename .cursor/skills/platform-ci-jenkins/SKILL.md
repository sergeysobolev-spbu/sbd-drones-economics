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
