<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# Лабораторная работа: ревизия Fabric-контрактов и доказательности

## Назначение

Лабораторная работа учит отличать broker contract, EventJournal record и Fabric smart contract, находить расхождения в документации и связывать каждое решение с проверяемым evidence.

Базовый источник: [`../smart_contracts.md`](../smart_contracts.md). Фазовая рамка: [`../ai_smart_contracts_integration.md`](../ai_smart_contracts_integration.md).

## Учебные Результаты

Студент должен уметь:

1. объяснить путь `Component -> Ledger Gateway -> Fabric Proxy -> Fabric Peer`;
2. определить, какой факт должен храниться в Fabric, EventJournal или broker-сообщении;
3. проверить роль MSP для метода chaincode;
4. найти несоответствие между таблицей методов и E2E-сценарием;
5. оформить строку трассировки requirement -> method -> event -> test -> evidence.

## DoR

- Прочитаны `docs/smart_contracts.md`, ADR-004, ADR-005 и ADR-008.
- Выбрана одна область: firmware, паспорт БАС, страхование, заказ или разрешение ОрВД.
- Команда назначила роли: contract reviewer, SDET, privacy reviewer, докладчик.
- Есть доступ к репозиторию без необходимости запускать тяжёлый Fabric full E2E.

## Задание

1. Найдите в `docs/smart_contracts.md` методы выбранной области.
2. Для каждого метода заполните таблицу:

| Метод | Invoke/query | Args | Allowed MSP | Denied MSP | Event/state | Test needed |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

3. Найдите минимум одно расхождение между описанием методов и E2E-сценарием из 14 шагов.
4. Опишите один negative test: wrong MSP, invalid state, duplicate invoke или invalid payload.
5. Заполните одну строку в [`../integration/fabric_traceability_matrix.md`](../integration/fabric_traceability_matrix.md) или подготовьте её в отчёте.
6. Сформулируйте, какие данные нельзя писать on-chain без privacy review.

## DoD

- Заполнена contract matrix для выбранной области.
- Найдено и описано хотя бы одно расхождение или подтверждено, что расхождений в области не найдено.
- Есть negative test proposal.
- Есть traceability row.
- Есть краткое объяснение: почему факт хранится в Fabric, EventJournal или broker.

## Acceptance Criteria

| Критерий | Проверка |
|---|---|
| Контрактность | Метод имеет role/MSP, args, output/error и event/state. |
| Доказательность | Traceability row связывает требование, ledger method и test evidence. |
| СКИБ | Есть связь с целью безопасности или ущербом. |
| Privacy | On-chain/off-chain решение обосновано. |
| QA | Negative test проверяет не только happy path. |

## Рубрика

| Уровень | Признак |
|---|---|
| L1 | Студент повторил методы из документа без анализа ролей и тестов. |
| L2 | Студент заполнил роли, args и нашёл хотя бы один риск. |
| L3 | Студент связал метод с ущербом, EventJournal, тестом, evidence и privacy-решением. |

## Типовые Ошибки

- Считать Fabric заменой Kafka или EventJournal.
- Писать персональные или коммерческие данные on-chain без review.
- Называть тест зелёным, если обязательный Fabric path был `skip`.
- Проверять только happy path без wrong-MSP и invalid-state сценариев.
