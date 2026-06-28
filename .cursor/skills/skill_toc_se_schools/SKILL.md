---
name: skill_toc_se_schools
description: Runs TOC multi-school SE session (Russian/American/Chinese) for TEM/SKIB analysis — NJYA, DTR, cloud, DBR. Use for se-school-* agents, toc-orchestrator, headless make toc-se-schools-session, or evaluating TOC school agent responses.
---

# Skill TOC SE Schools (ТОС / три школы СИ)

## Use When

Apply when:

- user asks for **меж-школьную** TOC-сессию по **ТЭМ** / продвижению **СКИБ**;
- running agents `se-school-russian`, `se-school-american`, `se-school-chinese`, `toc-orchestrator`, `toc-evidence-curator`;
- headless: `make toc-se-schools-session` or `make toc-se-schools-dtr-session`;
- validating role responses against **10-block contract** and quality gates.

## Canonical Sources

| Артефакт | Путь |
|----------|------|
| Методика | `docs/ai_sbd/agents/toc/tem_toc_multi_agent_methodology.ru.md` |
| Запуск (headless) | `docs/ai_sbd/agents/toc/session_se_schools.ru.md` |
| Протокол | `docs/ai_sbd/agents/toc/session_protocol.ru.md` |
| Роли | `docs/ai_sbd/agents/toc/agent_roles.yaml` |
| Brief full P1–P7 | `docs/ai_sbd/agents/toc/sessions/briefs/tem_toc_se_schools_2026-06-26_001.yaml` |
| Brief DTR only | `docs/ai_sbd/agents/toc/sessions/briefs/tem_toc_se_schools_dtr_2026-06-26_001.yaml` |
| System instruction | `docs/ai_sbd/agents/se_schools/toc_se_schools_system_instruction.md` |
| Eval suite | `docs/ai_sbd/agents/se_schools/toc_se_schools_eval_suite_v1.yaml` |
| Quality gates | `docs/ai_sbd/agents/se_schools/toc_se_schools_quality_gates_v1.yaml` |
| Skill registry | `docs/ai_sbd/agents/se_schools/toc_se_schools_skills_v1.yaml` |

## School Framing (кратко)

| Agent | Фокус НЖЯ / causal_links |
|-------|---------------------------|
| `se-school-russian` | СМД, деятельность, позиции сторон, «кто что решает» |
| `se-school-american` | ConOps, V&V, success criteria, E2E evidence |
| `se-school-chinese` | 整体, мета-синтез, верхний проект, количественные метрики |

## Workflow (фазы)

1. **P1** — self_positioning + sources_used (параллельно по школам).
2. **P2** — ≥3 **undesirable_effects** без решений; ≥2 **causal_links** «если … то … потому что …» + ссылка.
3. **P3** — `toc-orchestrator`: merged_dtr, mermaid, njya_summary.
4. **P3b** — `toc-evidence-curator`: sources_gate_verdict.
5. **P4** — одно **selected_constraint** (auto_orchestrator или human_required).
6. **P5** — «туча»: conflicts_or_needs от ≥2 школ; orchestrator → cloud.
7. **P6** — ДБР: injection без нового ограничения; optional `triz-expert-tem`.
8. **P7** — synthesis session_report.

## Output Contract (10 blocks — ролевой агент)

```markdown
## agent_role
## self_positioning
## sources_used
## undesirable_effects
## causal_links
## assumptions_facts
## conflicts_or_needs
## questions_to_other_agents
## human_review
## next_step
```

Validate:

```bash
cd code
pipenv run python scripts/toc_response_gate.py --mode role --file path/to/P2-se-school-russian.log
```

## Quality Gates

From `toc_se_schools_quality_gates_v1.yaml`:

- all 10 blocks present (role mode);
- **НЖЯ** без решений в subject (no «нужно внедрить», «следует добавить» …);
- **СКИБ** — только каноническая расшифровка;
- school-specific language in self_positioning or causal_links;
- `human_review` present;
- project facts cite repo paths or `hypothesis`.

## Headless Session (another node)

После `git clone` и checkout нужной ветки:

```bash
cd code
bash scripts/toc_node_bootstrap.sh          # init + env check + unit tests
make toc-se-schools-session-dry-run
make toc-se-schools-session APPLY=1 TOC_DTR_STUB_APPLY=1
make toc-se-schools-session APPLY=1         # live: cursor-agent login or CURSOR_API_KEY
```

Подробный runbook: `docs/ai_sbd/agents/toc/session_se_schools.ru.md` § «Запуск на другом узле».

## Eval Scenarios

Run manual or CI check against `docs/ai_sbd/agents/se_schools/toc_se_schools_eval_suite_v1.yaml` scenarios **TS01–TS07**. Fixtures: `docs/ai_sbd/agents/se_schools/fixtures/`.

## Failure Modes

- Одни и те же НЖЯ у всех школ (нет school_tag / framing).
- Решения в формулировках НЖЯ.
- ДТР без одного главного ограничения.
- «Туча» из одной школы.
- ДБР меняет корневое ограничение.
- Использование `gh` coding-агентом.

## Integration

| Method | Question |
|--------|----------|
| TOC schools | Какие ограничения деятельности блокируют масштабирование доверия? |
| TRIZ (P6 optional) | Какие параметры конфликтуют при выбранном injection? |
| SBD | Сохранены ли ЦБ/трассировка при предложенном переходе? |
