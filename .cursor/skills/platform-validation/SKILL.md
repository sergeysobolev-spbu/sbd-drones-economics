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
