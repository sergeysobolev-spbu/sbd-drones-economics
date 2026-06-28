<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# ADR-008: режимы CI для Fabric E2E

| Поле | Значение |
|---|---|
| Статус | **Proposed** |
| Дата | 2026-06-28 |
| Связано | ADR-004, ADR-005, PR-E3, `docs/smart_contracts.md`, `docs/ai_smart_contracts_integration.md` |

## Контекст

В `docs/ai_dev_tasks.md` Fabric E2E зафиксирован как PR-E3: восстановить job или явно пометить manual-only. Fabric-сеть требует peers/orderer, crypto material, proxy per org и долгого запуска. Если сразу сделать этот контур blocking gate, phase 0 может получить нестабильный CI раньше стабилизации Kafka smoke.

## Решение

Ввести три режима Fabric-проверок:

| Режим | Запуск | Назначение |
|---|---|---|
| `fabric-fast` | каждый push, без Fabric-сети | Unit chaincode/gateway mapping, mock proxy, schema validation. |
| `fabric-smoke` | nightly или workflow_dispatch | Proxy health, один invoke/query, уникальный run id. |
| `fabric-full` | manual / release candidate | `dummy_fabric` 14-step E2E, tx ids, EventJournal correlation, negative role/state tests. |

До отдельного `human_review` Fabric E2E не является обязательным gate для PR-E1. PR-E3 должен зафиксировать один из статусов:

1. **manual-only accepted** — полный Fabric E2E запускается вручную с evidence checklist;
2. **nightly accepted** — smoke идёт по расписанию, full остаётся manual;
3. **blocking accepted** — full Fabric E2E блокирует merge только при изменениях Fabric/ledger scope.

## Skip / Fail Policy

- Если `RUN_FABRIC_E2E` не задан, full Fabric E2E может быть `skip` как manual profile.
- Если `RUN_FABRIC_E2E=1`, недоступный Fabric/proxy/orderer считается hard fail.
- `xfail` допускается только с причиной, владельцем и датой пересмотра.
- Любой flaky-кейс классифицируется как `infra`, `product`, `contract`, `test bug`, `scope` или `external`.

## Evidence Checklist

- команды запуска;
- SHA/ветка;
- список контейнеров;
- health всех Fabric Proxy;
- pytest summary / JUnit;
- `fabric_tx_id` по каждому invoke;
- финальный `ReadOrder`;
- logs proxy/peer/orderer без секретов;
- список skipped/xfail node ids с причинами.

## Acceptance Criteria

- PR-E3 не смешивается с PR-E1.
- Fast проверки не требуют Docker/Fabric.
- Manual/full запуск не считается успешным при обязательных skip.
- Decision log фиксирует, почему выбран manual-only, nightly или blocking режим.
