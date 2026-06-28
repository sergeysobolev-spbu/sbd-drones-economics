<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# ADR-005: корреляция событий EventJournal и Fabric ledger

| Поле | Значение |
|---|---|
| Статус | **Proposed** |
| Дата | 2026-06-28 |
| Связано | ADR-004, ADR-008, `docs/ai_smart_contracts_integration.md`, `docs/integration/topic_map.yaml` |

## Контекст

Fabric-транзакции полезны только тогда, когда их можно связать с исходным бизнес-событием, брокерным сообщением, записью EventJournal и тестовым evidence. Без единой корреляции ledger превращается в отдельный журнал, который сложно использовать для расследования, обучения и приёмки.

## Решение

Для всех ledger-вызовов ввести единый envelope корреляции:

| Поле | Назначение |
|---|---|
| `correlation_id` | Сквозной идентификатор сценария/заказа/теста. |
| `event_id` | Уникальный идентификатор конкретного события. |
| `source` | Система или компонент-источник. |
| `schema_version` | Версия схемы события или команды. |
| `domain_id` | Предметный идентификатор: `order_id`, `drone_id`, `firmware_id`, `policy_id`. |
| `ledger_method` | Метод chaincode в форме `ContractName:MethodName`. |
| `fabric_tx_id` | Идентификатор транзакции Fabric после успешного invoke. |
| `status` | `pending`, `committed`, `failed`, `rejected`. |
| `error_code` | Код ошибки для failed/rejected. |

События `ledger.tx.committed` и `ledger.tx.failed` должны попадать в EventJournal. Для query-операций `fabric_tx_id` может отсутствовать; в evidence фиксируется snapshot ответа.

## Инварианты

- Один `correlation_id` связывает broker event, EventJournal record и Fabric transaction.
- Отказ Fabric не должен маскироваться как успешный бизнес-результат.
- При `dual_write` EventJournal должен содержать результат ledger-вызова или явную ошибку.
- Для тестов используется уникальный `run_id`, включённый в `correlation_id`.

## Acceptance Criteria

- В `docs/smart_contracts.md` или отдельной спецификации описан envelope корреляции.
- E2E evidence содержит `correlation_id` и `fabric_tx_id` для каждого invoke.
- QA может построить строку трассировки: requirement -> broker event -> EventJournal record -> Fabric method -> pytest node id.
- Negative tests проверяют timeout, reject и malformed response без silent success.

## Human Review

Нужно утвердить, какие поля считаются чувствительными и не должны попадать в публичный ledger. Privacy-решения фиксируются отдельно в ADR-009.
