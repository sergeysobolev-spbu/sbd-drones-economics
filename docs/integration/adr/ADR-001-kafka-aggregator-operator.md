# ADR-001: транспорт Kafka для пары Агрегатор ↔ Эксплуатант (phase 0)

<!-- doc-meta: status=active version=0.1 updated=2026-06-28 -->

| Поле | Значение |
|------|----------|
| Статус | **Proposed** — ожидает human_review |
| Дата | 2026-06-28 |
| Связано | T1, T2, [topic_map.yaml](../topic_map.yaml), З1–З2 |

## Контекст

- Агрегатор (`systems/agregator`) работает **только с Kafka**.
- Эксплуатант (`systems/operator`) по умолчанию использует **MQTT** (Mosquitto).
- Префиксы топиков не совпадают без явного сопоставления (З2).
- Phase 0 требует воспроизводимый сквозной сценарий заказа (T14).

## Решение

На **этапе 0** пара Агрегатор ↔ Эксплуатант использует **Kafka** с каноническими топиками:

```
v1.aggregator_insurer.local.operator.requests   # Aggregator → Operator
v1.aggregator_insurer.local.operator.responses  # Operator → Aggregator
```

Эксплуатант запускается с `BROKER_TYPE=kafka` и env-override топиков (см. `topic_map.yaml` → `mapping_operator_phase0`).

MQTT остаётся для **внутренних** компонент Operator и для последующих фаз dual-transport; не используется для стыка с Aggregator на phase 0.

## Обоснование

| Альтернатива | Плюсы | Минусы |
|--------------|-------|--------|
| **Kafka (выбрано)** | Aggregator уже на Kafka; один брокер в compose; паттерн из `-economics` E2E | Operator нуждается в env/коде для подписок |
| MQTT bridge | Сохраняет default Operator | Доп. компонент, сложнее отладка, нет в Aggregator |
| Adapter-сервис | Изоляция | Лишний контейнер на учебном стенде |

## Последствия

### Положительные

- Единый compose `integration-phase0` (T10).
- Smoke E2E (T14) может опираться на существующий Kafka stack.
- Согласование с `sbd-drones-economics` E2E-паттернами.

### Отрицательные / риски

- Студентам нужно явно переключать `BROKER_TYPE` в lab (документировать в quick_start).
- Dual-transport (MQTT E2E) — отдельный профиль, не phase 0.

## Действия по реализации

1. [ ] Human review: утвердить ADR-001.
2. [ ] Operator: env `KAFKA_OPERATOR_REQUEST_TOPIC` / `KAFKA_OPERATOR_RESPONSE_TOPIC` или правка подписок.
3. [ ] Compose profile `integration-phase0`: kafka + aggregator + operator (kafka).
4. [ ] Smoke test T14.

## human_review

- **Владелец:** преподаватель / владелец ОП
- **Статус:** pending
