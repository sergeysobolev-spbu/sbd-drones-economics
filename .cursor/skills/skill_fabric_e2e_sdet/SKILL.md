---
name: skill_fabric_e2e_sdet
description: Designs stable Fabric unit, mock, integration and E2E verification with skip policy, negative tests and evidence artifacts.
---

# Skill Fabric E2E SDET

## Use When

Use for Fabric smart contract tests, `dummy_fabric`, proxy health, full E2E, negative role/state tests, flake classification and PR-E3 evidence.

## Workflow

1. Classify test level: unit, mock proxy, Fabric smoke, `dummy_fabric` full E2E or dual-write E2E.
2. Define mandatory path, optional path and manual profile.
3. Require unique run id and isolated domain IDs.
4. Use bounded polling with diagnostics instead of fixed sleeps.
5. Classify failure: infra, product, contract, test bug, scope or external.
6. Save evidence: JUnit, logs, transaction IDs, final queries and skip/xfail list.

## Output Contract

```markdown
## fabric_e2e_scope
## test_levels
## negative_tests
## skip_xfail_policy
## isolation_and_timeouts
## evidence_bundle
## human_review
## next_step
```
