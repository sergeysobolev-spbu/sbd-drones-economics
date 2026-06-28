---
name: skill_artifact_quality
description: Reviews artifacts for criteria, completeness, coherence, evidence and quality grade.
---

# skill_artifact_quality

## Use When

Use this skill when its described responsibility is in scope. Preserve `human_review` for high-impact decisions.

## Output Contract

```markdown
## situation
## evidence
## human_review
## next_step
```

## Agent-Change Quality Gate

For agent/skill updates, require:

- registry points only to existing skills;
- every active agent has frontmatter and VUCA section;
- role-specific contract exists for each agent;
- docs/ai_dev_tasks.md references only existing skills/task_type;
- historical Marinet mentions are not active routing.
