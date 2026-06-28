<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# F3: Fabric smoke runbook

## Agent Boundary

| Поле | Значение |
|---|---|
| Owner agent | `fabric-devops-cicd-steward` |
| Task type | `fabric_devops_cicd` |
| Может менять | Runbook, env examples, CI/manual policy docs. |
| Только предложить | Makefile/Jenkins/GHA runtime changes до отдельной задачи. |
| Human review | Переход manual-only -> nightly -> blocking. |

## DoR

- [ ] ADR-008 существует.
- [ ] Known ports/env перечислены.
- [ ] Privacy reviewer подтвердил, что evidence logs не содержат секреты.

## DoD

- [ ] Описаны режимы `fabric-fast`, `fabric-smoke`, `fabric-full`.
- [ ] Есть readiness steps для proxy health и bounded polling.
- [ ] Есть cleanup/evidence checklist.
- [ ] Указано: `RUN_FABRIC_E2E=1` => Fabric unavailable = hard fail.

## Acceptance Criteria

- Runbook не требует включения full Fabric в PR-E1.
- `manual-only` имеет дату пересмотра и owner.
- Для nightly описаны prerequisites и teardown.
