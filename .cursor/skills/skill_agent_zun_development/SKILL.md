---
name: skill_agent_zun_development
description: Defines and improves agent knowledge, skills and abilities (ЗУН), maturity levels, rubrics, exercises and development backlog for TEM BAS agents.
---

# Skill Agent ZUN Development

## Workflow

1. Build ЗУН matrix: знания, умения, навыки.
2. Assign maturity level L0-L3.
3. Map gaps to skill update, profile update, registry route or validation gate.
4. Define exercises, expected outputs, rubric and evidence.

## Output Contract

```markdown
## agent_scope
## zun_matrix
## maturity_assessment
## weak_skills
## missing_skills
## development_backlog
## exercises_and_rubrics
## vuca_autonomy_rubric
## human_review
## next_step
```

## History-Based ZUN Analysis

For the last 100 commits, derive ЗУН gaps from observable patterns:

- repeated WIP commits -> weak planning and stop conditions;
- broker/topic churn -> weak contract reading;
- skip/xfail or red gates -> weak QA evidence;
- notebooks/slides mixed with runtime -> weak repo hygiene;
- merge/push blockers -> weak release readiness.

Each gap must produce a drill, target maturity L0-L3, owner agent and evidence criterion.
