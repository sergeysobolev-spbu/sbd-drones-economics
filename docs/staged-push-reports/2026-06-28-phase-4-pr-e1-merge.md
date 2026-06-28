# Staged push — Phase 4 PR-E1 merge (`sbd-drones-economics`)

<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

**Дата:** 2026-06-28  
**Ветка:** `feature/uas-dev-company` → `master` (PR-E1)  
**Стратегия интеграции с `origin/master`:** **merge** (не rebase): конфликт `Makefile` + субмодуль `systems/agrodron`.

## Merge / conflict resolution

| Артеfact | Решение |
|----------|---------|
| `Makefile` | Объединены feature `CI_INTEGRATION_EXCLUDE` / `CI_UNIT_EXCLUDE` с master `CI_INTEGRATION_DIRTY_NAMES` и cleanup в `ci-integration-test`. |
| `systems/agrodron` | Submodule merge → `911905d` (тесты mission flow + master fixes). |
| Superproject merge commit | `165efef` |

## Ворота (повтор после merge)

| Команда | Результат | Примечание |
|---------|-----------|------------|
| `make init` | OK | Pipenv уже актуален. |
| `make ci-test` | **GREEN** (retry #2) | Retry #1: stale Docker network у `systems/Agregator`; снят stack `docker compose down` в `systems/Agregator`. |
| `make e2e-codespace` | **GREEN** | Retry #1: конфликт внешней сети `drones_net` (ручной `docker network create` из Agregator CI). Retry #2: **28 passed, 2 skipped**, ~212 s; fix `KafkaSystemBus.stop()` — bounded shutdown (teardown больше не зависает). |

## DevOps

- **Риск:** параллельный `ci-integration-test` (Agregator) и `e2e-codespace` на одной машине — общая сеть `drones_net`; перед e2e нужен `compose down` Agregator или удаление сети без compose-label.
- **Patch:** `broker/kafka/kafka_system_bus.py` — `stop()` с таймаутом на `consumer.close()` / `producer.close()`, `shutdown(wait=False)`.
- **Push master:** только при зелёных воротах; force-push `master` не использовался.

## QA

- E2E skip: `test_04_wait_mission_completed`, `test_events_present_in_analytics` (analytics off / SM timeout) — ожидаемо для codespace-gate.
- Интеграция uas_dev_company: 17 passed, 11 skipped (без изменений политики skip).

## Human review

- Подтвердить merge commit на `master` и отсутствие лишних untracked `vendor/` / `systems/cyber_drons` в коммите merge.
