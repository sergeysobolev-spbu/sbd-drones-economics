---
name: skill_dt_simulation_tem
description: Connects TEM BAS digital twin requirements with SITL/alt_sitl, replay, scenario evidence, correlation_id, topic contracts and validation owner.
---

# Skill DT Simulation TEM

## Use When

Use for digital-twin, SITL/alt_sitl, replay, scenario fixtures, calibration gaps, correlation_id and evidence for TEM BAS phase 0.

## Workflow

1. Identify BAS scenario, external systems, broker boundary and decision being tested.
2. Map model inputs, assumptions, expected outputs and acceptance criteria.
3. Require reproducible run plan: fixture, command, seed, correlation_id and report path.
4. Separate verification of simulation mechanics from validation by external owner.
5. Link findings to topic map, smoke E2E, traceability and human_review.

## Output Contract

```markdown
## simulation_scope
## model_mapping
## run_plan
## calibration_and_evidence
## verification_vs_validation
## human_review
## next_step
```
