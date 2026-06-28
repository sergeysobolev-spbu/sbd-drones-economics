<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# ADR-009: privacy и on-chain/off-chain граница Fabric ledger

| Поле | Значение |
|---|---|
| Статус | **Proposed** |
| Дата | 2026-06-28 |
| Связано | ADR-004, ADR-005, ADR-006, ADR-007, `skill_ledger_privacy_review` |

## Контекст

Fabric обеспечивает неизменяемость записи, но неизменяемость повышает риск, если on-chain попадают персональные данные, коммерчески чувствительные детали, секреты, приватные ключи, generated crypto material или сырая телеметрия.

## Решение

По умолчанию on-chain допускаются только:

- идентификаторы учебного стенда без персональных данных;
- статусы сертификатов, firmware, страхования и заказа;
- хэши или ссылки на off-chain evidence;
- `fabric_tx_id`, `correlation_id`, `event_id`;
- минимальные поля, необходимые для проверки state machine.

Off-chain остаются:

- персональные данные;
- коммерческие детали заказа и платежей;
- приватные ключи, сертификаты, connection profiles;
- сырая телеметрия и большие журналы;
- внутренние риск-модели страховой и расчёты ТЭМ.

Private data collections допустимы только после отдельного review политики доступа и endorsement policy.

## Data Classification

| Класс | Пример | Решение |
|---|---|---|
| Public training status | `order_status=finished` | On-chain допустимо. |
| Evidence reference | hash лога, URI артефакта | On-chain ссылка/хэш. |
| Personal data | ФИО, контакты, реальные заказчики | Do not store on-chain. |
| Commercial data | реальные суммы, тарифы, условия договора | Off-chain или обезличенный demo. |
| Secrets / crypto | ключи, crypto-config, connection profiles | Не коммитить и не включать в evidence. |
| Raw telemetry | большие треки, координаты, sensor logs | Off-chain; on-chain только hash/reference после review. |

## Acceptance Criteria

- Каждый новый ledger field имеет privacy classification.
- Evidence logs редактируются перед публикацией.
- Generated crypto material не попадает в git.
- `skill_ledger_privacy_review` запускается перед P2/P3 расширениями и release.
- Любой отход от default on-chain policy требует `human_review`.
