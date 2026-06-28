# ADR-001: транспорт Kafka для пары Агрегатор ↔ Эксплуатант (phase 0)

<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

| Поле | Значение |
|------|----------|
| Статус | **Accepted (phase 0 only)** |
| Дата | 2026-06-28 |
| Связано | T1, T2, [topic_map.yaml](../topic_map.yaml), [ADR-002](ADR-002-broker-agnostic-platform.md), З1–З2 |

## Контекст

- Агрегатор (`systems/agregator`) работает **только с Kafka**.
- Эксплуатант (`systems/operator`) по умолчанию использует **MQTT** (Mosquitto).
- Префиксы топиков не совпадают без явного сопоставления (З2).
- Phase 0 требует воспроизводимый сквозной сценарий заказа (T14).

## Решение (scope: phase 0)

На **этапе 0** пара Агрегатор ↔ Эксплуатант использует **Kafka** с каноническими топиками:

```
v1.aggregator_insurer.local.operator.requests   # Aggregator → Operator
v1.aggregator_insurer.local.operator.responses  # Operator → Aggregator
```

Эксплуатант запускается с `BROKER_TYPE=kafka` и env-override топиков (см. `topic_map.yaml` → `mapping_operator_phase0`).

Compose-профиль **`integration-phase0`** поднимает Kafka; MQTT на этом профиле **не используется** для стыка с Aggregator.

## Ограничение scope (важно)

Данное ADR **не** задаёт Kafka как единственный брокер платформы навсегда. После phase 0 целевая модель — **broker-agnostic** ([ADR-002](ADR-002-broker-agnostic-platform.md)):

- системы переключают Kafka/Mosquitto через **env и конфигурацию**;
- **брокер** выбирается **профилем теста** (`make e2e`, `make e2e-mqtt`, `integration-phase0`, …);
- бизнес-логика не содержит жёсткой привязки к типу брокера.

## Обоснование (phase 0)

| Альтернатива | Плюсы | Минусы |
|--------------|-------|--------|
| **Kafka (выбрано для phase 0)** | Aggregator уже на Kafka; один брокер в compose; паттерн из `-economics` E2E | Operator нуждается в env/коде для подписок |
| MQTT bridge | Сохраняет default Operator | Доп. компонент, сложнее отладка, нет в Aggregator |
| Adapter-сервис | Изоляция | Лишний контейнер на учебном стенде |

## Последствия

### Положительные

- Единый compose `integration-phase0` (T10).
- Smoke E2E (T14) может опираться на существующий Kafka stack.
- Согласование с `sbd-drones-economics` E2E-паттернами.

### Отрицательные / риски

- На phase 0 в lab явно задаётся `BROKER_TYPE=kafka` для стыка с Aggregator.
- Профили MQTT E2E (`e2e-mqtt`) — отдельный контур, не phase 0.

## Действия по реализации

1. [x] Human review: утвердить ADR-001 для phase 0 (2026-06-28).
2. [ ] Operator: env `KAFKA_OPERATOR_REQUEST_TOPIC` / `KAFKA_OPERATOR_RESPONSE_TOPIC` или правка подписок.
3. [ ] Compose profile `integration-phase0`: kafka + aggregator + operator (kafka).
4. [ ] Smoke test T14.
5. [ ] После phase 0: реализация ADR-002 (broker-agnostic profiles).

## human_review

- **Владелец:** преподаватель / владелец ОП
- **Статус:** accepted (phase 0), 2026-06-28
