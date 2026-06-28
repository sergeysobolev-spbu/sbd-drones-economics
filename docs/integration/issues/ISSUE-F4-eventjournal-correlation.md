<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# F4: EventJournal and Fabric correlation

## Agent Boundary

| Поле | Значение |
|---|---|
| Owner agent | `eventjournal-traceability-sdet` + `ledger-integration-architect` |
| Task type | `ledger_eventjournal_traceability` |
| Может менять | Traceability matrix, event envelope docs, planned test ids. |
| Только предложить | Runtime EventJournal schema/code changes. |
| Human review | Приёмка EventJournal как evidence для конкретной ЦБ. |

## DoR

- [ ] ADR-005 существует.
- [ ] P1 contract matrix содержит methods/events.
- [ ] `ledger_events` draft добавлен в `docs/integration/topic_map.yaml`.

## DoD

- [ ] Для `ledger.tx.committed` и `ledger.tx.failed` описаны required fields.
- [ ] В `fabric_traceability_matrix.md` есть owner, runtime path, status, evidence strength.
- [ ] Есть planned tests для success, reject, timeout и malformed response.

## Acceptance Criteria

- Каждая Fabric invoke-операция возвращается в EventJournal как committed или failed.
- Silent success запрещён.
- `correlation_id` связывает broker event, EventJournal record, Fabric tx и pytest evidence.
