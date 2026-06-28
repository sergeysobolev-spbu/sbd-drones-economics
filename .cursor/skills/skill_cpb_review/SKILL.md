---
name: skill_cpb_review
description: Reviews CPB, security goals, and security assumptions for traceability to harms, external ownership, and testability.
---

# Skill CPB Review

## Use When

Apply this skill for draft or review of КБП/ЦПБ materials, especially around Ш3 and adjacent artifacts.

## Inputs

- КБП draft.
- Stakeholders and damages table (Ш1 output).
- Draft ЦБ/ПБ statements.
- Existing assumptions and external owners.

## Steps

1. Separate ЦБ, ПБ, implementation requirements, and open questions.
2. Check that every ПБ has an external contour and owner.
3. Validate traceability from damages to proposed goals.
4. Flag statements that are not testable.
5. Build corrected draft with reviewer notes.

## Output Schema

- `cpb_findings`
- `goal_classification_table`
- `traceability_to_damages`
- `owner_checks_for_assumptions`
- `corrections`
- `human_review`

## Pattern Mapping Coverage

- Core: Ш3.
- Supporting: Ш1, Ш2, Ш7.

## Failure Modes

- Treating TLS/firewall choices as security goals.
- Accepting assumptions without owner and external boundary.
- Producing "safe" verdict without testability criteria.
