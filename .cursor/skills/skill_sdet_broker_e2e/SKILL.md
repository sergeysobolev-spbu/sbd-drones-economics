---
name: skill_sdet_broker_e2e
description: Designs stable SDET strategy for E2E tests over Kafka, Mosquitto and MQTT: anti-flake, unique ids, bounded awaits, cleanup, failure classification and evidence.
---

# Skill SDET Broker E2E

## Workflow

1. Define the E2E contract: producer, topic, consumer, correlation id and expected event.
2. Use unique `run_id`, topics/groups/client ids or disposable broker state.
3. Use bounded polling/awaits with diagnostic output; avoid fixed sleeps.
4. Classify failures: infra, product, flake, scope, external.
5. Save evidence: commands, logs, event journal, broker messages and JUnit.

## Output Contract

```markdown
## e2e_scope
## broker_contract
## isolation_strategy
## awaits_and_timeouts
## failure_classification
## evidence_bundle
## flake_risks
## human_review
## next_step
```
