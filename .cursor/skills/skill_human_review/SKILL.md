---
name: skill_human_review
description: Enforces mandatory human review checkpoints, decision ownership, and release-ready quality grade criteria. Use with skill_artifact_quality for pre-merge completeness and coherence gates.
---

# Skill Human Review

## Use When

Apply this skill for any response that may influence architecture, trusted boundaries, policy rules, release decisions, or training artifacts.

## Inputs

- Agent draft output in contract format.
- Reviewer role set (architect, product owner, security engineer).
- Quality grade thresholds and blocking errors.

## Steps

1. Verify mandatory response contract fields are present.
2. Extract reviewer decisions needed for each critical claim.
3. Classify findings into blocking and non-blocking.
4. Assign owner and required evidence per blocking finding.
5. Produce approve/rework recommendation with justification.

## Output Schema

- `review_checklist`
- `blocking_findings`
- `decision_owners`
- `required_evidence`
- `review_status`
- `next_step`

## Pattern Mapping Coverage

- Cross-cutting gate for Ш1-Ш18.
- Mandatory before "готово" status in delivery flows.
- Pair with `skill_artifact_quality` when auditing full deliverable bundles (completeness + coherence before human sign-off).

## Failure Modes

- Marking output as acceptable without reviewer ownership.
- Missing explicit blockers for unsafe statements.
- Converting recommendations into autonomous decisions.
