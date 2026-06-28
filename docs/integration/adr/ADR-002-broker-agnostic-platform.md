# ADR-002: broker-agnostic платформа (целевая архитектура после phase 0)

<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

| Поле | Значение |
|------|----------|
| Статус | **Accepted** |
| Дата | 2026-06-28 |
| Связано | ADR-001 (phase 0), T1, T9–T10, SDK `create_system_bus` |

## Контекст

Phase 0 ([ADR-001](ADR-001-kafka-aggregator-operator.md)) фиксирует **Kafka** для стыка Aggregator↔Operator как минимальный воспроизводимый контур. На последующих этапах платформа должна оставаться **независимой от конкретного брокера**: системы подключаются через конфигурацию / переменные окружения, а **экземпляр брокера** (Kafka, Mosquitto) поднимается профилем теста или compose.

## Решение

1. **Абстракция шины** — все системы используют SDK/API (`create_system_bus`, `BROKER_TYPE`, env топиков), без hardcode «только Kafka» или «только MQTT» в бизнес-логике.
2. **Конфигурация на уровне системы** — каждый узел задаёт транспорт через env:
   - `BROKER_TYPE=kafka|mqtt`
   - `KAFKA_BOOTSTRAP_SERVERS` / `MQTT_BROKER_URL`
   - имена топиков — из env или `topic_map.yaml`
3. **Профиль теста / compose** определяет, **какой брокер запущен**:
   - `integration-phase0` → Kafka (согласовано с Aggregator)
   - `e2e-mqtt` → Kafka + Mosquitto или MQTT-only profile
   - `unit` / `integration` per-system → mock или embedded broker по Makefile системы
4. **Aggregator** остаётся Kafka-only на текущем коде; broker-agnostic на уровне платформы означает, что **остальные системы** и **тестовые профили** не привязаны к одному брокеру глобально.

## Последствия

- Makefile: цели `e2e`, `e2e-codespace`, `e2e-mqtt` — разные профили брокера, не дублирование логики систем.
- Документация: `docs/build_and_test.md` — таблица профиль → брокер → системы.
- Phase 0 не отменяет ADR-001; после smoke E2E (T14) — работы по выравниван Operator default с env-only переключением (без смены кода при смене профиля).

## human_review

- **Владелец:** владелец ОП
- **Статус:** accepted (2026-06-28)
