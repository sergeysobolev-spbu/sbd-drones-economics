---
name: skill_fabric_chaincode_contracts
description: Designs and reviews Hyperledger Fabric chaincode contracts, MSP roles, endorsement policies, lifecycle states and negative tests for TEM BAS.
---

# Skill Fabric Chaincode Contracts

## Use When

Use for Fabric chaincode, smart contract method design, MSP/role authorization, endorsement policy, state transitions, idempotency and contract review.

## Workflow

1. Identify domain asset: drone pass, firmware, insurance, order, flight permission or funds.
2. Define contract method: operation type, args, output, errors and chaincode event.
3. Map allowed callers: MSP, attributes, admin override and denied roles.
4. Define invariants: state transition, idempotency, duplicate handling and validation rules.
5. Add evidence: unit tests, wrong-MSP tests, state negative tests and read-after-write query.
6. Escalate `human_review` for endorsement policy, privacy, trusted boundary and legal semantics.

## Output Contract

```markdown
## contract_scope
## methods_and_events
## role_matrix
## invariants
## tests_required
## privacy_and_trusted_boundary
## human_review
## next_step
```
