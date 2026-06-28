# Issue: T1+T2 — Topic map и ADR-001 (phase 0)

<!-- Локальный шаблон задачи (GitHub/gh недоступен: token invalid). Перенести в tracker после `gh auth login`. -->

| Поле | Значение |
|------|----------|
| **Title** | T1+T2: Topic map и Kafka-транспорт Aggregator↔Operator |
| **task_type** | `software_architecture_c4` |
| **Агенты** | `software-architect-c4`, `systems-engineer-sbd` |
| **Skills** | `skill_software_architecture_c4`, `skill_traceability`, `documentation-governance` |
| **Приоритет** | P0 |
| **Спринт** | S1 |

## Описание

Утвердить и реализовать единый контракт обмена между Агрегатором и Эксплуатантом для phase 0:

1. **T1** — Kafka как транспорт (ADR-001).
2. **T2** — `docs/integration/topic_map.yaml` как source of truth.

## Acceptance criteria

- [ ] ADR-001 status = Accepted (human_review).
- [ ] `topic_map.yaml` v0.2 без gap «systems.aggregator.*» — Operator подписан на TM-001/002.
- [ ] PlantUML sequence «Заказчик → Aggregator → Operator» (T12).
- [ ] Env documented в `systems/operator/docs/broker_selection.md` и compose `integration-phase0`.

## Артефакты

- [docs/integration/topic_map.yaml](../topic_map.yaml) (draft v0.1)
- [docs/integration/adr/ADR-001-kafka-aggregator-operator.md](../adr/ADR-001-kafka-aggregator-operator.md)

## Связанные задачи

- T14 smoke E2E (blocked by this issue)
- T10 compose profile

## Labels (при создании в tracker)

`kind-architecture`, `phase-0`, `P0`, `sys-integration`
