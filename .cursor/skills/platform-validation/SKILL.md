---
name: platform-validation
description: Selects and runs the right validation gates for platform changes: Python tests, Makefile target checks, documentation checks, ports checks, regression profiles, and dry-run agent checks. Use after edits or when planning validation.
---

# Platform Validation

## Use When

Apply this skill after code, test, CI, configuration, documentation, or agent-orchestration changes in the platform repository.

## Canonical Sources

- `.cursor/rules/change-validation-matrix.mdc`
- `.cursor/rules/code-quality-python-and-tests.mdc`
- `.cursor/rules/platform-python-deps.mdc`
- `code/docs/makefile_test_targets.md`
- `code/docs/ci_tests_profiles.md`

## Workflow

1. List changed zones: `code/scripts`, `code/tests`, `code/docs`, `code/config`, `code/Makefile`, `code/systems`, `.cursor`.
2. Map each zone to required checks using the validation matrix.
3. Prefer targeted unit tests first; add broader regression only when the blast radius justifies it.
4. For scripts importing third-party packages, use `pipenv run`, `$(PYTHON_RUN)`, or make targets with `platform-venv-ready`.
5. Report checks actually run, checks skipped, and why.

## Common Checks

- Python script logic: targeted `pytest` unit tests.
- `code/scripts/**`: unit tests plus safe dry-run or CLI smoke.
- `code/docs/**/*.md`: documentation versioning and README synchronization checks.
- Ports or compose: `make ports-check`.
- Makefile/test profile changes: `make test-makefile-targets-check` and `make test-pytest-config-check` when applicable.

## Output

Return: changed zones, selected checks, command results, remaining risk, and any checks not run.

## Sprint mode (QA / SDET time-boxed sprints)

Apply when the orchestrator assigns a **time-boxed QA sprint** (e.g. 120 min) with CI/E2E goals. Canonical policy: `docs/ai_dev_tasks.md#sprint-autonomy-policy`, `docs/ai_agents_improvements.md` §4.4.

### Time budget

- Use the **full allocated time** unless all sprint goals are met **or** no unblocked useful work remains in repo scope.
- If goals are met early, pivot to the next priority from backlog (`next-actions`, `backlog-sync`) — do not exit idle.
- Document early exit: list remaining time, why no unblocked work, and what was attempted.

### Pivot on block

| Block type | Pivot (do not idle) |
|---|---|
| Infra (stack down, flake) | Classify failure; run structural/unit tests; improve smoke/xfail policy; gate table docs |
| Integration red, unit green | **Not** sprint success if E2E is a goal — coordinate port/stack fixes or run `phase0-smoke` / prep e2e |
| Product assertion | xfail/skip taxonomy; traceability row; issue stub — then next test file |
| Human-only (merge, ADR, T3) | Pivot to doc gates, flake logs, test skeleton, exclude list review |

### E2E gate (mandatory when in sprint goals)

- **Do not claim sprint complete** without running **`make e2e-codespace`** and confirming **green**, unless the sprint scope explicitly excludes full E2E (document exception).
- Partial green (`ci-unit-test` only, `phase0-smoke` structural) is **insufficient** for E2E-focused sprints.
- Report: command, exit code, pass/skip/xfail counts, and classification of any red step.

### Autonomy

- Run tests, read logs, iterate fix→retest **without asking human** for each `make`/`pytest` step.
- Stay within `-economics` / `-ai` boundaries unless explicitly told otherwise.
