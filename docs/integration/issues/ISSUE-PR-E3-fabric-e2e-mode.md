<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# PR-E3: режим Fabric E2E и доказательства

## Назначение

Issue-шаблон фиксирует, что нужно сделать перед решением по PR-E3: восстановить Fabric E2E job или явно оставить full Fabric E2E в manual-only режиме с доказательным пакетом.

Связано:

- [`../adr/ADR-004-fabric-ledger-scope.md`](../adr/ADR-004-fabric-ledger-scope.md);
- [`../adr/ADR-005-ledger-event-correlation.md`](../adr/ADR-005-ledger-event-correlation.md);
- [`../adr/ADR-008-fabric-ci-mode.md`](../adr/ADR-008-fabric-ci-mode.md);
- [`../fabric_traceability_matrix.md`](../fabric_traceability_matrix.md);
- [`../../ai_smart_contracts_integration.md`](../../ai_smart_contracts_integration.md).

## DoR

- [ ] ADR-004 принят или явно оставлен в статусе `Proposed` с владельцем.
- [ ] ADR-005 описывает `correlation_id` / `fabric_tx_id` envelope.
- [ ] ADR-008 выбран как основа skip/fail policy.
- [ ] `docs/smart_contracts.md` сверяется с фактическими методами chaincode и E2E 14 steps.
- [ ] Выбран P1 scope: firmware, drone pass, insurance, order checkpoint.
- [ ] Privacy reviewer подтвердил, что тестовые данные не содержат секретов и персональных данных.

## DoD

- [ ] Есть решение PR-E3: `manual-only`, `nightly` или `blocking`.
- [ ] Для выбранного режима описана команда запуска.
- [ ] При `RUN_FABRIC_E2E=1` недоступный Fabric/proxy/orderer даёт hard fail.
- [ ] Mandatory Fabric path не считается успешным при `skip`.
- [ ] Evidence bundle сохраняет tx ids, final query, pytest summary и logs без секретов.
- [ ] В `fabric_traceability_matrix.md` есть строки для P1 методов.

## Acceptance Criteria

| Критерий | Проверка |
|---|---|
| PR-E1 не блокируется Fabric | Fabric E2E отделён от phase 0 Kafka smoke. |
| PR-E3 проверяем | Есть decision log и evidence checklist. |
| Soft-green исключён | `RUN_FABRIC_E2E=1` переводит недоступный Fabric в fail. |
| Доказательность есть | Для каждого invoke есть `fabric_tx_id` или объяснённый reject/fail. |
| Privacy соблюдена | Logs и snapshots не содержат ключей, токенов, PII и generated crypto. |

## Decision Log

| Дата | Решение | Основание | Владелец |
|---|---|---|---|
| 2026-06-28 | Draft: начать с `manual-only`, затем `nightly` после детерминированного startup | Fabric не должен блокировать PR-E1; нужен evidence-first подход | owner TBD |

## Evidence Bundle Template

| Evidence | Path / ссылка | Статус |
|---|---|---|
| pytest summary / JUnit | TBD | planned |
| `docker ps` / compose services | TBD | planned |
| Fabric Proxy health | TBD | planned |
| `fabric_tx_id` list | TBD | planned |
| `ReadOrder` final snapshot | TBD | planned |
| proxy/peer/orderer logs | TBD | planned |
| skipped/xfail node ids | TBD | planned |
