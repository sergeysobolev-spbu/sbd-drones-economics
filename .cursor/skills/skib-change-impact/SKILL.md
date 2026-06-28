---
name: skib-change-impact
description: Analyzes code, documentation, CI, or architecture changes for impact on SKIB properties, trusted base, policy architecture, security goals, assumptions, dependencies, tests, and evidence. Use for security-sensitive changes or review before merge.
---

# SKIB Change Impact

## Use When

Apply this skill when a change may affect SKIB artifacts, security boundaries, policy rules, trusted code, dependencies, tests, CI gates, or documentation evidence.

## Inputs

Collect the change description or diff, affected paths, current tests, relevant architecture notes, and any CPB/KPB/policy artifacts referenced by the change.

## Workflow

1. Classify the affected area: runtime code, inter-system contract, CI/Jenkins, tests, docs, dependencies, or SKIB artifact.
2. Check whether the change modifies trust boundaries, trusted base membership, policy enforcement, security goals, assumptions, external dependencies, or verification evidence.
3. Identify required updates to tests, docs, matrices, ports, or CI gates.
4. Mark unknowns explicitly; do not state that security is unaffected without traceable evidence.
5. Produce a merge checklist sized to the change.

## Output

Use this structure:

- Impact summary: one short paragraph.
- SKIB impact: changed / unchanged / unknown, with evidence.
- Required updates: files or artifacts to synchronize.
- Validation: concrete commands or test profiles.
- Human decisions: questions that cannot be resolved from the repo.

## Guardrails

- Do not weaken policy rules for convenience without analyzing security damage.
- Do not add compatibility shims for in-progress branch behavior unless explicitly required.
- Keep recommendations scoped to the change; avoid unrelated refactors.
