---
name: skill_select_pattern
description: Routes incoming SKIB tasks to the most relevant Sh1-Sh18 pattern, with explicit rationale, missing context list, and fallback plan.
---

# Skill Select Pattern

## Use When

Apply this skill when the user asks "какой шаблон выбрать" or gives an engineering situation that should be mapped to one or more patterns Ш1-Ш18.

## Inputs

- Situation description.
- Available artifacts (КБП, ЦПБ, АП, ДВБ, tests, incidents).
- Team goal (draft, review, release gate, training).

## Steps

1. Classify maturity and lifecycle stage (S1-S9).
2. Match to primary and optional patterns from `skib_agent_patterns.yaml`.
3. Explain why each selected pattern fits this input.
4. List missing artifacts needed for a reliable run.
5. Build fallback path if context is incomplete.

## Output Schema

- `situation_class`
- `primary_pattern_ids`
- `secondary_pattern_ids`
- `selection_rationale`
- `missing_inputs`
- `fallback_plan`

## Pattern Mapping Coverage

- Primary mapping: Ш1-Ш18.
- Typical fast path: Ш1 -> Ш3 -> Ш7 -> Ш8.
- Incident-heavy path: Ш4 -> Ш5 -> Ш7 -> Ш8 -> Ш9.

## Failure Modes

- Selecting pattern by keyword only, ignoring lifecycle stage.
- Returning one pattern where a sequence is required.
- Not listing missing artifacts before detailed recommendations.
