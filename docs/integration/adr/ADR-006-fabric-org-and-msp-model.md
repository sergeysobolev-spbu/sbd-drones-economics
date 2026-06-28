<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# ADR-006: модель организаций и MSP для Fabric

| Поле | Значение |
|---|---|
| Статус | **Proposed** |
| Дата | 2026-06-28 |
| Связано | ADR-004, ADR-005, ADR-008, `docs/smart_contracts.md` |

## Контекст

Fabric-контур в `docs/smart_contracts.md` использует роли `Aggregator`, `Operator`, `Insurer`, `CertCenter`, `Manufacturer`, `Orvd` и `admin`. Для доказательности и negative tests нужно явно зафиксировать, какие организации входят в P1 scope, какие отложены, и какие методы им разрешены.

## Решение

P1 MSP-модель:

| Организация | MSP | P1 роль |
|---|---|---|
| Агрегатор | `AggregatorMSP` | Создание заказа, назначение, финализация, чтение evidence. |
| Эксплуатант | `OperatorMSP` | Подтверждение, старт и завершение заказа. |
| Страховая | `InsurerMSP` | Страховая запись и одобрение заказа. |
| Сертификационный центр | `CertCenterMSP` | Паспорт БАС, типовой сертификат, firmware. |
| ОрВД | `OrvdMSP` | P2: разрешение полёта после стабилизации контракта ОрВД. |

`Manufacturer` на P1 остаётся read-only или demo-only до отдельного решения. `admin` допустим только для учебного стенда и должен быть явно помечен как high-risk override.

## Acceptance Criteria

- У каждого privileged метода есть allowed MSP и denied MSP.
- Wrong-MSP negative tests покрывают P1 методы.
- `admin` override не используется как обход отсутствующей ролевой модели в production-like сценариях.
- Добавление новой MSP требует обновления contract matrix и `human_review`.
