# Каталог агентов ТЭМ БАС (ОП)

<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

Экспорт подмножества агентов из [`sbd-open-platform-and-trainings-development`](../../../sbd-open-platform-and-trainings-development/docs/ai_sbd/agents/directory.md).

## Профили (`.cursor/agents/`)

| Агент | Назначение |
|-------|------------|
| `systems-engineer-sbd` | СКИБ, ЦПБ, трассировка, Ш1–Ш18 |
| `se-school-russian` | TOC: русская школа СИ |
| `se-school-american` | TOC: американская школа (V&V) |
| `se-school-chinese` | TOC: китайская школа (整体) |
| `se-school-ai-native` | Agent-native SE (Ш19) |
| `software-architect-c4` | C4, ADR, topic map |
| `qa-marinet-spec` | Приёмка спецификаций (адаптировать для БАС) |
| `ci-marinet-steward` | CI/Jenkins (job `drone-*` → tem-bas) |
| `project-manager-ccpm` | WBS, CCPM, milestones |
| `course-educator-platform` | УМК, лабораторные, рубрики |
| `artifact-quality-controller` | Качество артефактов |
| `toc-orchestrator` | TOC-сессии |
| `toc-evidence-curator` | Evidence gate |
| `dt-simulation-lead` | SITL, калибровка |
| `tem-economics-analyst` | CAPEX/OPEX, TCO (адаптация) |

## Реестр task types

`config/agent_skill_registry.json`

## TOC briefs

- [tem_bas_phase0_constraint_2026-06-28.yaml](toc/sessions/briefs/tem_bas_phase0_constraint_2026-06-28.yaml)

Запуск из open-platform (dry-run):

```bash
cd /path/to/sbd-open-platform-and-trainings-development/code
make toc-se-schools-session-dry-run \
  TOC_SE_SCHOOLS_BRIEF=/path/to/sbd-drones-economics/docs/ai_sbd/agents/toc/sessions/briefs/tem_bas_phase0_constraint_2026-06-28.yaml
```

## Оркестратор

Контракт работ: [docs/ai_dev_tasks.md](../../ai_dev_tasks.md)
