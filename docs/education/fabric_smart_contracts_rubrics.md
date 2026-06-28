<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# Рубрики: Fabric smart contracts

## Contract Review

| Уровень | Признак |
|---|---|
| Базовый | Перечислены методы и аргументы без роли MSP и negative tests. |
| Уверенный | Указаны allowed/denied MSP, event/state, errors и planned tests. |
| Продвинутый | Метод связан с ЦБ/ПБ, privacy class, EventJournal и evidence path. |

## Traceability

| Уровень | Признак |
|---|---|
| Базовый | Есть требование и метод Fabric. |
| Уверенный | Добавлены `correlation_id`, `fabric_tx_id`, EventJournal record и pytest id. |
| Продвинутый | Есть owner, runtime path, evidence strength и условие снятия `planned`. |

## Privacy Boundary

| Уровень | Признак |
|---|---|
| Базовый | Студент отличает public status от персональных данных. |
| Уверенный | Для каждого поля выбран on-chain, hash/reference, private data или off-chain режим. |
| Продвинутый | Обоснованы endorsement/private data assumptions и redaction evidence. |

## Integrated Demo Evidence

| Уровень | Признак |
|---|---|
| Базовый | Есть команды и итоговый query. |
| Уверенный | Есть tx ids, logs, skipped/xfail list и failure classification. |
| Продвинутый | Evidence связан с traceability matrix и human_review decision. |
