---
name: agent-work-orchestration
description: Orchestrates project work across Cursor agents: task packaging, skill routing, coordinator versus coding responsibilities, worktree execution, dry-run first workflow, review agents, integration, and command restrictions. Use for headless agents, multi-agent packages, or agent-ready issue work.
---

# Agent Work Orchestration

## Use When

Apply this skill when preparing, running, reviewing, or integrating headless Cursor agent tasks in this repository.

## Canonical Sources

- `code/docs/multi-agents-development.md`
- `code/docs/headless-parallel-agents.md`
- `code/scripts/agent_orchestrator.py`
- `code/scripts/trusted_agent_executor.py`
- `code/scripts/agent_gap_tasks.py`
- `.cursor/rules/github-issue-in-progress.mdc`
- `.cursor/rules/github-board-gh.mdc`

## Roles

- Coordinator: prepares issue packages, selects task types and skills, updates GitHub Project status, integrates results, and decides final status.
- Coding agent: works in one worktree, follows the prompt and required skills, does not use `gh`, and reports files/tests/risks.
- Review agent: reviews completed work with a second model or deterministic gates and does not rewrite unrelated work.

## Workflow

1. Start with dry-run: inspect selected issues, worktrees, model, prompt, and required skills.
2. Ensure every task has either explicit `skills` or a `task_type` that routes through the skill registry.
3. Keep one issue per worktree and avoid shared mutable state between parallel agents.
4. Use restricted command policy for coding agents.
5. Run package-specific status, integrate, review, and done targets only from the coordinator context.
6. Summarize agent output as files changed, tests run, old-to-new mappings when relevant, risks, and blockers.

## Guardrails

- Coding agents must not close issues, push branches, or modify GitHub Project fields.
- Do not skip dry-run for new packages or new skill routing.
- Do not let skill routing weaken command restrictions from `trusted_agent_executor.py`.
