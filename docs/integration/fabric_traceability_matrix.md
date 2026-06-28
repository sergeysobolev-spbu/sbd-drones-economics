<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# Матрица трассировки Fabric ledger

Матрица связывает требования, угрозы, broker events, EventJournal records, Fabric transactions и тестовые доказательства. Это рабочий шаблон для `eventjournal-traceability-sdet`, `fabric-chaincode-engineer`, QA и системного инженера СКИБ.

## Правило Заполнения

Каждая строка должна иметь проверяемый evidence. `skip` обязательного пути не считается доказательством.

| Поле | Что указать |
|---|---|
| `trace_id` | Уникальный идентификатор строки трассировки. |
| `requirement_or_goal` | Требование, цель безопасности или учебный результат. |
| `harm` | Какой ущерб предотвращается или расследуется. |
| `asset` | Актив: сертификат, firmware, страховая запись, заказ, разрешение. |
| `broker_event` | Событие или команда в broker-контуре, если применимо. |
| `eventjournal_record` | Запись EventJournal и обязательные поля. |
| `fabric_method` | Метод chaincode в форме `ContractName:MethodName`. |
| `fabric_event_or_state` | Ledger event/state после invoke/query. |
| `test_node_id` | pytest node id или planned test id. |
| `runtime_repo_path` | Фактический или планируемый путь теста в runtime-репозитории. |
| `owner` | Агент или роль, отвечающая за evidence. |
| `status` | `planned`, `unit`, `mock`, `fabric-smoke`, `full-e2e`, `human-approved`, `blocked`. |
| `evidence_strength` | Уровень доказательности: `planned`, `unit`, `mock`, `fabric-smoke`, `full-e2e`, `human-approved`. |
| `evidence` | Логи, tx id, query snapshot, JUnit, owner. |

## P1 Draft

| trace_id | requirement_or_goal | harm | asset | broker_event | eventjournal_record | fabric_method | fabric_event_or_state | test_node_id | runtime_repo_path | owner | status | evidence_strength | evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FAB-TR-001 | Целостность допуска БАС | Эксплуатация несертифицированного БАС | Паспорт БАС, firmware | `ledger.tx.committed` | `correlation_id`, `drone_id`, `firmware_id`, `fabric_tx_id` | `FirmwareContract:CertifyFirmware`, `DronePropertiesContract:CreateDronePass` | `FirmwareCertified`, `DronePassCreated` | `test_certcenter_can_certify_firmware_and_create_drone_pass` | `../sbd-drones-economics/systems/dummy_fabric/tests/` | `fabric-chaincode-engineer` + QA | planned | planned | planned |
| FAB-TR-002 | Неотрекаемость решения страховщика | Страховое мошенничество или спор | Страховая запись | `ledger.tx.committed` | `correlation_id`, `policy_id`, `order_id`, `fabric_tx_id` | `DronePropertiesContract:CreateInsuranceRecord`, `OrderContract:ApproveOrder` | `InsuranceRecordCreated`, `OrderApproved` | `test_insurer_only_can_create_insurance_and_approve_order` | `../sbd-drones-economics/systems/dummy_fabric/tests/` | QA/SDET | planned | planned | planned |
| FAB-TR-003 | Расследуемость выполнения заказа | Невозможность доказать старт/финиш/финализацию | Заказ | `order.started`, `order.finished`, `ledger.tx.committed` | `correlation_id`, `order_id`, `fabric_tx_id`, `status` | `OrderContract:StartOrder`, `OrderContract:FinishOrder`, `OrderContract:FinalizeOrder` | `OrderStarted`, `OrderFinished`, `OrderFinalized` | `test_order_lifecycle_records_tx_ids` | `../sbd-drones-economics/tests/e2e/` | `eventjournal-traceability-sdet` | planned | planned | planned |
| FAB-TR-004 | Корректность ролей MSP | Несанкционированное изменение ledger | MSP/role policy | `ledger.tx.failed` | `correlation_id`, `source`, `error_code` | privileged methods | rejected transaction | `test_wrong_msp_rejected_for_privileged_methods` | `../sbd-drones-economics/systems/dummy_fabric/tests/` | `fabric-chaincode-engineer` | planned | planned | planned |
| FAB-TR-005 | Доступность evidence при PR-E3 | Soft-green Fabric E2E | Fabric E2E report | n/a | n/a | `OrderContract:ReadOrder` | final order snapshot | `test_dummy_fabric_full_order_workflow` | `../sbd-drones-economics/tests/e2e/` | `fabric-devops-cicd-steward` + QA | manual/nightly | planned | manual/nightly |

## Follow-up

1. Сверить строки с фактическими pytest node ids после contract review `docs/smart_contracts.md`.
2. Добавить ссылки на логи и JUnit после первого `RUN_FABRIC_E2E=1` прогона.
3. Уточнить privacy-классификацию on-chain/off-chain полей перед P2.
