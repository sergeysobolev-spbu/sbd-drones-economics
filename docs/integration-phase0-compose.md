# Compose-профиль `integration-phase0` (T10, stub)

<!-- doc-meta: status=active version=0.1 updated=2026-06-28 -->

Минимальный контур phase 0: **Kafka + Aggregator + Operator (Kafka env)**. Полный `docker-compose.yml` — в worktree T10; здесь — контракт профиля и фрагмент для DevOps.

## Связанные артефакты

| Артефакт | Путь |
|----------|------|
| Topic map v0.2 | [`integration/topic_map.yaml`](integration/topic_map.yaml) |
| ADR-001 Kafka phase 0 | [`ADR-001`](integration/adr/ADR-001-kafka-aggregator-operator.md) |
| ADR-003 compose profile | [`ADR-003`](integration/adr/ADR-003-integration-phase0-compose.md) |
| Smoke E2E T14 | `tests/e2e/test_phase0_smoke.py` |

## Сервисы профиля

| Сервис | Образ / build | Профиль | Порты (local, черновик) |
|--------|---------------|---------|-------------------------|
| `kafka` | из `docker/docker-compose.yml` | `integration-phase0` | 9092 |
| `zookeeper` | idem | `integration-phase0` | 2181 |
| `aggregator` | `systems/agregator` | `integration-phase0` | 8081 |
| `operator` | `systems/operator` | `integration-phase0` | — |

Заглушки ORVD/DronePort/Insurer — **не** входят в минимальный smoke; подключаются в расширенном профиле (T6–T7).

## Фрагмент compose (stub)

```yaml
# docker/integration-phase0.compose.yaml (planned — не подключён к корневому Makefile)
services:
  aggregator:
    profiles: ["integration-phase0"]
    environment:
      KAFKA_PROTOCOL_VERSION: v1
      KAFKA_SYSTEM_NAME: aggregator_insurer
      KAFKA_INSTANCE_ID: local
  operator:
    profiles: ["integration-phase0"]
    environment:
      BROKER_TYPE: kafka
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      KAFKA_OPERATOR_REQUEST_TOPIC: v1.aggregator_insurer.local.operator.requests
      KAFKA_OPERATOR_RESPONSE_TOPIC: v1.aggregator_insurer.local.operator.responses
```

## Makefile (целевые цели)

| Цель | Статус | Назначение |
|------|--------|------------|
| `make phase0-up` | planned | `docker compose --profile integration-phase0 up -d` |
| `make phase0-smoke` | active | structural gate: `make phase0-smoke` (`pytest -k Structure`, без Docker); полный runtime — `make phase0-smoke-full` |
| `make e2e-codespace` | ✅ | Полный полигон (не phase 0 minimal) |

## Запуск smoke без полного T10

```bash
# При поднятом полигоне (e2e-up или будущий phase0-up):
export AGREGATOR_URL=http://localhost:8081
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
pipenv run pytest tests/e2e/test_phase0_smoke.py -v -m phase0_smoke
```

Структурные проверки без Docker: `PHASE0_SMOKE_FORCE=1 pytest tests/e2e/test_phase0_smoke.py -k Structure`.

## human_review

- **Статус:** `accepted_by_orchestrator` (2026-06-28) — stub до PR-A5 / T10 full compose.
