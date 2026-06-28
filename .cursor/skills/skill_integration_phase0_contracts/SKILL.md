---
name: skill_integration_phase0_contracts
description: Governs TEM BAS phase 0 integration contracts: T1-T17, topic map, ADR, Kafka/MQTT boundary, compose profile, smoke E2E, PR-E1/PR-A1 and evidence.
---

# Skill Integration Phase 0 Contracts

## Workflow

1. Identify task IDs T1-T17 and affected systems.
2. Check `docs/integration/topic_map.yaml` as source of truth.
3. Classify the change: local, contract-impact, safety-impact, release-impact.
4. Ensure ADR coverage for durable decisions.
5. Define evidence: schema parse, compose profile, smoke E2E, logs, correlation id.
6. Route high-impact changes to architect, systems engineer, QA/SDET and `human_review`.

## Output Contract

```markdown
## contract_scope
## affected_topics_and_systems
## adr_impact
## compose_and_runtime_impact
## evidence_required
## gaps_and_blockers
## human_review
## next_step
```
