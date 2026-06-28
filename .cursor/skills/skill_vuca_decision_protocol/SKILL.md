---
name: skill_vuca_decision_protocol
description: Builds effective agent work under VUCA conditions: autonomy levels, decision loop, pivot rules, evidence, escalation, and human_review boundaries.
---

# Skill VUCA Decision Protocol

## Use When

Use for unclear requirements, blockers, conflicting inputs, red CI, architecture trade-offs, autonomous agent work, or decision support.

## Decision Loop

`observe -> classify -> decide -> act -> verify -> record`

## Autonomy Levels

| Level | Meaning |
|---|---|
| L0 | reactive: stops or guesses |
| L1 | structured: facts, assumptions, risks, next step |
| L2 | adaptive: reversible actions, alternatives, evidence |
| L3 | mission-oriented: coordinates roles, pivots in scope, escalates high-impact only |

## Output Add-On

```markdown
## vuca_assessment
## autonomy_level
## decision_scope
## options_considered
## selected_action
## evidence_required
## decision_log
## escalation_and_human_review
## next_best_action
```

## Stop Conditions

Stop and escalate before destructive actions, secrets/privacy exposure, cross-repo scope changes, ADR/topic map/CI gate changes, ЦБ/ЦПБ/security assumptions, merge/release/acceptance, or repeated flakes after retry budget.

## Commit-History Review Add-On

When improving agents from repository history:

1. Classify the last commits by churn areas: docs, runtime, tests, broker, notebooks/slides, merge/push.
2. Identify repeated VUCA signals: WIP loops, soft-green, topic mismatch, dirty tree, blocked push, missing owner.
3. Convert each signal into a role-specific drill and evidence gate.
4. Do not mark autonomy L3 unless the agent proves pivot + evidence + correct escalation.
