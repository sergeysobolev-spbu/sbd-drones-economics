---
name: skill_ledger_eventjournal_traceability
description: Builds traceability from requirements and broker events to EventJournal records, Fabric transactions and pytest evidence.
---

# Skill Ledger EventJournal Traceability

## Use When

Use when a task links Fabric ledger transactions with broker messages, EventJournal records, security goals, requirements, acceptance tests or evidence bundles.

## Workflow

1. Identify the requirement, harm, asset and security goal.
2. Map broker event and payload fields, including `correlation_id` and `event_id`.
3. Map Fabric method, chaincode event and expected `fabric_tx_id`.
4. Define EventJournal record fields and failure states.
5. Bind to pytest node ids and required logs.
6. Verify that skipped tests cannot count as evidence for mandatory paths.

## Output Contract

```markdown
## trace_scope
## harm_asset_goal
## broker_event
## fabric_transaction
## eventjournal_record
## test_and_evidence
## gaps_and_human_review
## next_step
```
