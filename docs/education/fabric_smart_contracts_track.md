<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# Учебный трек: Fabric smart contracts и доказательность

Трек является продвинутым модулем ОП до решения преподавателя о включении в обязательную часть. Он не блокирует phase 0 Kafka smoke и PR-E1.

## ЗУН

| ID | Результат |
|---|---|
| З-FAB-01 | Объясняет разницу между broker contract, EventJournal record и Fabric smart contract. |
| У-FAB-01 | Строит contract matrix: method, role/MSP, args, event, test. |
| У-FAB-02 | Связывает `correlation_id`, `fabric_tx_id`, EventJournal excerpt и pytest evidence. |
| Н-FAB-01 | Проектирует negative test на wrong MSP или invalid state transition. |
| Н-FAB-02 | Оформляет privacy boundary: on-chain fields, off-chain fields, hashes/links. |

## Лабораторные

| Lab | Тема | Артефакт |
|---|---|---|
| 1 | Fabric onboarding и smoke evidence | Схема вызова, команды, health/query result. |
| 2 | Chaincode method + MSP role | Contract matrix, wrong-MSP negative test proposal. |
| 3 | Order lifecycle state machine | Таблица переходов, invalid transition test proposal. |
| 4 | EventJournal traceability | Traceability row, tx id, EventJournal excerpt, pytest evidence plan. |

Стартовая лабораторная: [`../lab_works/fabric_contract_review_lab.md`](../lab_works/fabric_contract_review_lab.md).

## Evidence Bundle

Каждая работа сдаётся не скриншотом, а пакетом:

- команда запуска или collect-only команда;
- passed/failed/skipped summary;
- `fabric_tx_id` или planned id;
- final query snapshot или mock response;
- EventJournal excerpt или planned record;
- вывод студента: почему факт хранится в Fabric, EventJournal или broker.

## Human Review

Преподаватель должен отдельно решить, является ли трек обязательным модулем курса или продвинутым заданием для команд, готовых к Fabric-инфраструктуре.
