# PR-E1 gate report

<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

**Ветка:** `feature/uas-dev-company` → `master`  
**Политика:** push `master` только при green `make ci-test` **и** `make e2e-codespace`.

## Результаты (2026-06-28)

| Gate | Результат | Примечание |
|------|-----------|------------|
| `make ci-unit-test` | ✅ green | после `CI_UNIT_EXCLUDE` (gcs, orvd_system, SITL-module) |
| `make ci-integration-test` | ❌ red | SITL docker mount, agrodron 2 fails, docker-up errors в нескольких submodules |
| `make e2e-codespace` | ⏸ не запускался | блокер: ci-test не green |

## Вывод

**PR-E1 merge в `master` — заблокирован** до стабилизации integration/E2E.

## Следующие шаги

1. Починить или исключить из gate integration submodules с docker-up errors (документировать в `docs/build_and_test.md`).
2. Прогнать `make e2e-codespace` после green `ci-test`.
3. Fast-forward merge + push `master`.

## Связанные решения

- ADR-001 accepted (phase 0 Kafka)
- ADR-002 accepted (broker-agnostic target)
