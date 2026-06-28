<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# F1: Fabric contract matrix

## Agent Boundary

| Поле | Значение |
|---|---|
| Owner agent | `fabric-chaincode-engineer` |
| Task type | `fabric_chaincode_contracts` |
| Может менять | Документы contract matrix, traceability draft, notes к `docs/smart_contracts.md`. |
| Только предложить | Изменение chaincode, MSP, endorsement policy, CI gate. |
| Human review | ADR-004/006/007/009, trusted boundary, privacy, legal semantics. |

## DoR

- [ ] `docs/smart_contracts.md` прочитан.
- [ ] ADR-004/006/007/009 существуют как Proposed или reviewed.
- [ ] P1 scope выбран: firmware, drone pass, insurance, order checkpoints.

## DoD

- [ ] Для каждого P1 метода указаны args, invoke/query, allowed MSP, denied MSP, event/state, errors.
- [ ] Методы из E2E 14 steps сверены с основной таблицей.
- [ ] `DistributeFunds` помечен как demo-only / P2-P3 до финансовой модели.
- [ ] Для каждого privileged метода есть planned negative test.

## Acceptance Criteria

- Нет расхождения между runbook E2E и contract matrix без явной пометки `planned`, `P2/P3` или `demo-only`.
- `Delete*` методы пересмотрены или помечены как demo-only.
- Output содержит следующий пакет: F2 negative tests или F4 traceability.
