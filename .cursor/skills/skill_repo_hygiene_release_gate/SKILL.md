---
name: skill_repo_hygiene_release_gate
description: Reviews repository hygiene before merge or release: git history, dirty tree, generated artifacts, privacy, WIP commits, split-PR readiness and human_review blockers.
---

# Skill Repo Hygiene Release Gate

## Workflow

1. Inspect changed/untracked zones.
2. Classify artifacts: source, generated, evidence, private/sensitive, external.
3. Identify release blockers: secrets, PII, dirty generated files, unrelated systems, WIP history.
4. Recommend split-PR or exclusion plan.
5. Require `human_review` for deletion, irreversible cleanup, release/merge and public artifacts.
