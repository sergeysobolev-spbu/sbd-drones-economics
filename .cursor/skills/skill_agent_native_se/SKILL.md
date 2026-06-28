---
name: skill_agent_native_se
description: Designs TEM/SKIB systems agent-native from first lifecycle stage — activity positions, agent-ready artifacts, V&V/demo-pack, headless orchestration. Use for se-school-ai-native, pattern Ш19, agent-native SE design, stakeholder value map, demo-pack 45 min.
---

# Skill Agent-Native SE (школа «ИИ-агентов», Ш19)

## Use When

Apply when:

- проектирование **agent-native** контура для **ТЭМ**, **СКИБ** или смежной системы;
- running agent `se-school-ai-native` or pattern **Ш19**;
- подготовка **карты ценности**, **demo-pack**, agent-ready Issues (слои A/B/C);
- ко-проектирование после TOC-сессии (ограничение A, ДБР demo-pack);
- `task_type: agent_native_se_design` в skill registry.

## Canonical Sources

| Артефакт | Путь |
|----------|------|
| Профили агентов | `docs/ai_sbd/agents/se_schools/agents-profiles.md` |
| Протокол ко-проектирования | `docs/ai_sbd/agents/se_schools/agent_design_protocol.ru.md` |
| Merge P2 | `docs/ai_sbd/agents/se_schools/sessions/se_schools_ai_native_agent_2026-06-25_001/merged_agent_design.ru.md` |
| Профиль агента | `.cursor/agents/se-school-ai-native.md` |
| System instruction | `docs/ai_sbd/agents/se_school_ai_native/se_school_ai_native_system_instruction.md` |
| Skill registry | `docs/ai_sbd/agents/se_school_ai_native/se_school_ai_native_skills_v1.yaml` |
| Eval / gates | `docs/ai_sbd/agents/se_school_ai_native/se_school_ai_native_eval_suite_v1.yaml`, `se_school_ai_native_quality_gates_v1.yaml` |
| Карта ценности | `docs/ai_sbd/agents/shared/stakeholder_value_map.yaml` |
| Demo-pack | `code/docs/demo_pack_45min.ru.md` |
| Headless | `code/docs/headless-parallel-agents.md`, `code/docs/multi-agents-development.md` |
| Роли TOC | `docs/ai_sbd/agents/toc/agent_roles.yaml` |

## Mission (кратко)

`se-school-ai-native` — **архитектор agent-native SE**, не coding-агент. Замкнутый контур:

```text
ConOps / карта ценности → agent-readable артефакты → headless-пакеты
  → observable прогон ТЭМ → метрики целого → human_review → обновление
```

## Workflow

1. **Scope** — этап ЖЦ (1–9), узел/контур **ТЭМ**, внешние роли (≥1).
2. **Activity map** — матрица «решение → human_only | draft+approve | execute+audit».
3. **Agent-readable layer** — YAML/JSON рядом с prose (ConOps, verification matrix, value map).
4. **Packaging** — agent-ready Issue: AC/DoD, `task_type`, skills, verification command.
5. **Whole-first gate** — локальный green worktree ≠ готовность целого.
6. **Validation plan** — demo-pack шаги per роль; validation owner (human).
7. **human_review** — блокеры, владельцы, `next_step`.

## Output Contract (операционный)

```markdown
## agent_role
## situation_and_lifecycle_stage
## agent_native_design
## activity_positions
## verification_validation_plan
## participation_metrics
## integration_with_tem_skib
## human_review
## quality_grade
## next_step
```

## Principles (обязательные)

1. **Contracts-first** — слой A до массового `implement`.
2. **Verification ≠ validation** — CI ≠ приёмка внешней роли.
3. **Split baseline 0.1/0.2** — не смешивать в evidence narrative.
4. **СКИБ** — только каноническая расшифровка (ГОСТ Р 72118-2025).
5. **SKIB invariant** — ЦБ → правило → тест → журнал.

## Supporting Skills (маршрутизация)

| Skill | Когда |
|-------|-------|
| `agent-work-orchestration` | headless-пакеты |
| `skill_traceability` | ЦБ → тест → прогон |
| `skill_human_review` | финал каждого этапа |
| `platform-validation` | gates |
| `skib-change-impact` | security-sensitive |
| `documentation-governance` | doc-meta, README |
| `skill_toc_se_schools` | анализ ограничений |

## Failure Modes

- Agent-native = «больше coding-агентов» без позиций и gates.
- Validation объявлена без validation owner и observable run.
- Смешение runtime 0.1 и demo 0.2 в одном narrative.
- Coding-агент меняет `gh` / GitHub Project (запрещено).
- Quality gate «готово» без `human_review`.

## Integration

| Method | Question |
|--------|----------|
| TOC schools | Какое ограничение деятельности блокирует agent-native масштаб? |
| `systems-engineer-sbd` | Содержание КБП/ЦПБ (Ш1–Ш18); граница — процесс vs артефакт |
| Headless | `make *-agents-implement` только после agent-ready + слой A |
