<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# ADR-004: область применения Fabric ledger

| Поле | Значение |
|---|---|
| Статус | **Proposed** |
| Дата | 2026-06-28 |
| Связано | `docs/ai_smart_contracts_integration.md`, `docs/smart_contracts.md`, ADR-001, ADR-002, ADR-003, PR-E3 |

## Контекст

Phase 0 ТЭМ БАС уже имеет критический путь интеграции `Aggregator -> Kafka -> Operator -> EventJournal`. Этот путь закрепляется через `docs/integration/topic_map.yaml`, ADR-001/002/003 и smoke T14.

В проекте также есть Fabric-контур: `Ledger Gateway`, `Fabric Proxy`, `drone-chaincode`, роли MSP и E2E-сценарий `dummy_fabric`. Без отдельного решения Fabric может быть ошибочно включён в обязательный gate phase 0 или, наоборот, остаться демонстрацией без трассировки к целям СКИБ.

## Решение

Fabric вводится как **доказательный ledger-слой**, а не как замена Kafka, EventJournal или runtime-механизмов полётной безопасности.

На ближайшем цикле Fabric фиксирует только подтверждённые долгоживущие факты:

- паспорт БАС и статус типового сертификата;
- сертификацию и отзыв firmware;
- страховую запись и статус допуска;
- контрольные состояния заказа;
- разрешение ОрВД после стабилизации ОрВД-контракта;
- `fabric_tx_id` как связь между ledger, EventJournal и тестовым evidence.

Fabric не является обязательным gate для PR-E1 / phase 0 Kafka smoke. Решение о PR-E3 фиксируется отдельно в ADR-008.

## Не Решаем Сейчас

- юридическую силу ledger-записей для страхования и сертификации;
- перевод Fabric E2E в blocking CI;
- запись телеметрии целиком on-chain;
- использование Fabric как runtime policy enforcer для аварийных команд БАС;
- включение Fabric Proxy, peers/orderer или chaincode в D0/TCB без отдельного `human_review`.

## Последствия

| Область | Последствие |
|---|---|
| Архитектура | Kafka/EventJournal остаются операционным контуром; Fabric добавляется как downstream evidence. |
| QA | Fabric full E2E проверяется отдельно от T14 до решения PR-E3. |
| СКИБ | Fabric усиливает неотрекаемость и неизменяемость записи, но не доказывает истинность входных данных. |
| Обучение | Fabric можно преподавать как модуль доказательности и контрактного мышления, не ломая базовый phase 0. |

## Acceptance Criteria

- `docs/smart_contracts.md` содержит ссылку на phased Fabric scope.
- В contract matrix каждому методу назначен статус P1/P2/P3.
- `docs/ai_smart_contracts_integration.md` остаётся источником плана до появления отдельных спецификаций.
- В `human_review` вынесены trusted-boundary, privacy и CI gate решения.
