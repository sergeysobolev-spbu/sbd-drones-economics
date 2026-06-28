---
name: skill_ledger_privacy_review
description: Reviews on-chain/off-chain boundaries, private data, secrets, generated crypto material and privacy risks for Fabric ledger tasks.
---

# Skill Ledger Privacy Review

## Use When

Use before writing new fields to Fabric, committing crypto artifacts, publishing logs, changing private data collections, or using ledger entries for insurance, certification or finance scenarios.

## Workflow

1. Classify data: public status, internal evidence, personal data, commercial data, secret or generated crypto material.
2. Decide storage: on-chain value, on-chain hash, private data collection, off-chain reference or do-not-store.
3. Check access: MSP, endorsement policy, collection policy and read/query exposure.
4. Check repository hygiene: private keys, certificates, connection profiles, logs and generated ledger artifacts.
5. Define redaction and evidence rules.
6. Escalate privacy, legal and trusted-boundary decisions to `human_review`.

## Output Contract

```markdown
## data_scope
## classification
## storage_decision
## access_policy
## repo_hygiene
## evidence_redaction
## human_review
## next_step
```
