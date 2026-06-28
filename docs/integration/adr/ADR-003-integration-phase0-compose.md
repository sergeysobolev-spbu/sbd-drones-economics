# ADR-003: compose-профиль `integration-phase0`

<!-- doc-meta: status=active version=0.1 updated=2026-06-28 -->

| Поле | Значение |
|------|----------|
| Статус | **Proposed (stub accepted by orchestrator)** |
| Дата | 2026-06-28 |
| Связано | T10, ADR-001, [topic_map.yaml](../topic_map.yaml), T14 |

## Контекст

Phase 0 требует воспроизводимый минимальный контур Aggregator↔Operator на Kafka ([ADR-001](ADR-001-kafka-aggregator-operator.md)). Полный E2E полигон `-economics` поднимает десятки контейнеров; для smoke T14 и учебных lab нужен **урезанный профиль**.

## Решение

1. Ввести compose-профиль **`integration-phase0`** с сервисами: `kafka`, `zookeeper`, `aggregator`, `operator` (Kafka env).
2. Operator получает env из `topic_map.yaml` → `mapping_operator_phase0.env_overrides`.
3. Smoke: `tests/e2e/test_phase0_smoke.py` (marker `phase0_smoke`).
4. Расширение профиля (Insurer stub, ORVD stub) — отдельные под-профили после green minimal smoke.

## Альтернативы

| Вариант | Оценка |
|---------|--------|
| Переиспользовать `make e2e-up` | ❌ слишком тяжело для T14 / CI smoke |
| Отдельный repo compose | ❌ дублирование topic map |
| **Профиль в monorepo** | ✅ согласовано с ADR-002 broker-by-profile |

## Последствия

- DevOps: `docs/integration-phase0-compose.md` в `-economics`; цели `phase0-up` / `phase0-smoke` в Makefile (planned).
- QA: xfail на TM-001 consumer до merge `tem-bas-operator`.
- Architect: sequence T12 в `docs/integration_process/diagrams/phase0_happy_path.puml`.

## Действия

1. [x] Stub документ compose (`integration-phase0-compose.md`).
2. [ ] Подключить `docker/integration-phase0.compose.yaml` к корневому Makefile.
3. [ ] Jenkins job `drone-e2e-smoke` (timeout 30 min).
4. [ ] Снять xfail T14 после Operator Kafka align.

## human_review

- **Статус:** `accepted_by_orchestrator` (2026-06-28)
