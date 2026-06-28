---
name: skill_devops_broker_cicd
description: Designs CI/CD infrastructure for Kafka, Mosquitto and MQTT: compose, pinned images, healthchecks, readiness, isolation, cleanup, ports and evidence.
---

# Skill DevOps Broker CI/CD

## Workflow

1. Define broker topology and local/CI mode.
2. Use pinned images; avoid `latest` and fixed `container_name` in CI.
3. Add broker-level readiness probes, not fixed sleeps.
4. Isolate test runs by run id, topics, groups and client ids.
5. Save evidence: compose config, health output, broker logs, JUnit/test logs.

## Output Contract

```markdown
## broker_topology
## ci_profile
## readiness_and_healthchecks
## isolation_and_cleanup
## evidence_artifacts
## human_review
## next_step
```
