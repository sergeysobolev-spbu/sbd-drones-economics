---
name: skill_fabric_devops_cicd
description: Plans Fabric network startup, proxy health, ports, cleanup, CI/manual/nightly profiles and PR-E3 gate decisions.
---

# Skill Fabric DevOps CI/CD

## Use When

Use for Fabric network, Fabric Proxy, Ledger Gateway, Docker Compose, CI profiles, Jenkins/GitHub Actions, ports, cleanup and evidence collection.

## Workflow

1. Identify mode: `fabric-fast`, `fabric-smoke`, `fabric-full` or release gate.
2. Check prerequisites: network, peers/orderer, crypto paths, channel, chaincode and proxy env.
3. Define readiness: health endpoints, bounded waits, logs and cleanup.
4. Separate manual/nightly/blocking gates according to ADR-008.
5. Ensure unavailable Fabric fails when `RUN_FABRIC_E2E=1`.
6. Escalate port registry, CI gate and release decisions to `human_review`.

## Output Contract

```markdown
## ci_scope
## run_mode
## prerequisites
## readiness_and_cleanup
## ports_and_env
## evidence_required
## human_review
## next_step
```
