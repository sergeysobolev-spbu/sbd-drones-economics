---
name: skill_dt_simulation_tem
description: Connects TEM digital twin requirements with SITL/alt_sitl runs, model-to-physics mapping, calibration evidence, scenario reproducibility, and correlation_id tracing. Use for TEM-Marinet digital twin, simulation lead, SITL, alt_sitl, calibration, replay, or simulation evidence.
---

# Skill DT Simulation TEM

## Use When

Apply when a task concerns the TEM-Marinet digital twin:

- mapping «физика маршрута -> модель -> решение»;
- SITL, alt_sitl, replay or dry-run simulation;
- calibration evidence, scenario fixtures, reproducibility;
- `correlation_id` through route, journal, incident and report artifacts.

## Canonical Sources

- `docs/tem_marinet/conops/system_conops.md`
- `docs/tem_marinet/lifecycle/L04_design/specification.md`
- `docs/tem_marinet/lifecycle/L06_integration/specification.md`
- `docs/tem_marinet/lifecycle/L07_verification_validation/specification.md`
- `code/docs/headless-parallel-agents.md`
- `code/docs/multi-agents-development.md`

## Workflow

1. Identify the scenario: route, vessel class, season, cargo and decision being tested.
2. Define model inputs, physical assumptions, expected outputs and acceptance criteria.
3. Require a reproducible run plan: fixture, command, seed, `correlation_id`, report path.
4. Separate verification of simulation mechanics from validation by domain owners.
5. Link findings to lifecycle gates L04, L06 and L07.

## Output Contract

```markdown
## simulation_scope
## physics_to_model_mapping
## run_plan
## calibration_evidence
## traceability
## validation_owner
## risks_and_gaps
## next_step
```

## Guardrails

- Do not claim validation from a synthetic run alone.
- Do not hide missing calibration data behind qualitative confidence.
- Every simulation claim must point to an observable run or an explicit gap.
