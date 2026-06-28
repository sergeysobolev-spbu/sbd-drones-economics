# TOC session: tem_bas_phase0_constraint_2026-06-28

<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->
<!-- Синтез оркестратора (dry-run TOC из open-platform требует output_dir внутри того repo) -->

**Brief:** [tem_bas_phase0_constraint_2026-06-28.yaml](../briefs/tem_bas_phase0_constraint_2026-06-28.yaml)  
**Iteration:** se_schools_full (синтез без headless LLM)

## НЖЯ (объединённое)

| id | subject | school_tag |
|----|---------|------------|
| NJYA-1 | Нет позиции «владелец контракта» между командами Aggregator и Operator | russian |
| NJYA-2 | Нет acceptance test (smoke E2E), привязанного к ConOps phase 0 | american |
| NJYA-3 | Topic map, compose и тесты не образуют целое — частичные merge бессмысленны | chinese |

## ДТР — главное ограничение

**Отсутствие опубликованного и реализованного контракта обмена (topic map + transport) блокирует воспроизводимый сквозной сценарий и стабильный CI.**

## «Туча» (симптомы)

- З1–З2: Kafka vs MQTT, разные префиксы топиков
- E2E skip/flaky; CI green с пропусками
- Два репозитория без синхронизации master
- Jupyter live demos WIP

## ДБР (первый буфер работ)

1. T1+T2: утвердить ADR-001 + `topic_map.yaml` v0.2
2. Operator env override для TM-001/002
3. T14 smoke E2E (один happy path)
4. Только после M2 — merge `-ai` operator в общий полигон

## human_review

- **Владелец:** координатор ОП
- **Решение:** согласовано с [ai_dev_tasks.md](../../../../ai_dev_tasks.md) фаза 0

## Запуск полной headless-сессии

Из open-platform (output внутри того repo):

```bash
cd sbd-open-platform-and-trainings-development/code
make toc-se-schools-session-dry-run \
  TOC_SE_SCHOOLS_BRIEF=.../tem_bas_phase0_constraint_2026-06-28.yaml
# output_dir в brief должен быть под REPO_ROOT open-platform
```
