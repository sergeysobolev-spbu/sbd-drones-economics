<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# F2: Fabric negative tests

## Agent Boundary

| Поле | Значение |
|---|---|
| Owner agent | `fabric-chaincode-engineer` + `eventjournal-traceability-sdet` |
| Task type | `fabric_e2e_sdet` |
| Может менять | Test plan, planned pytest ids, traceability rows. |
| Только предложить | Runtime test implementation в соседнем repo, chaincode fixes. |
| Human review | Acceptance of wrong-MSP/state-machine semantics. |

## DoR

- [ ] F1 contract matrix готова.
- [ ] Allowed/denied MSP для P1 методов указаны.
- [ ] State machine заказа описана хотя бы как draft.

## DoD

- [ ] Есть planned tests для wrong MSP, invalid transition, duplicate invoke, invalid payload.
- [ ] Каждый negative test привязан к requirement/ЦБ/ПБ.
- [ ] При `RUN_FABRIC_E2E=1` mandatory skip классифицирован как hard fail.

## Acceptance Criteria

- Negative tests покрывают не только happy path.
- Failure taxonomy различает infra, product, contract, test bug, scope и external.
- Evidence plan включает JUnit, tx ids или rejected transaction details.
