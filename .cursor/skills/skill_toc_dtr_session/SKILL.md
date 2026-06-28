---
name: skill_toc_dtr_session
description: Runs TOC Current Reality Tree (DTR) multi-agent sessions for TEM platform analysis. Use for toc-orchestrator, headless make toc-dtr-session, NJYA/DTR/constraint analysis, or validating TOC agent responses.
---

# Skill TOC DTR Session

## Use When

Apply when:

- user asks for **ДТР**, **НЖЯ**, **ТОС**-анализ **ТЭМ**;
- running `toc-orchestrator` or `make toc-dtr-session` / `make toc-stakeholders-full-session` / `make toc-se-schools-session`;
- preparing `tem_toc_dtr_*.md` or `tem_toc_session_*.md` reports;
- validating role-agent or orchestrator responses.

## Canonical Sources

- `docs/ai_sbd/agents/toc/tem_toc_multi_agent_methodology.ru.md`
- `docs/ai_sbd/agents/toc/agent_roles.yaml`
- `docs/ai_sbd/agents/toc/session_protocol.ru.md`
- `docs/ai_sbd/agents/toc/node_setup.ru.md`
- `docs/ai_sbd/agents/toc/toc_orchestrator_system_instruction.md`
- `docs/ai_sbd/agents/toc/toc_eval_suite_v1.yaml`
- `docs/ai_sbd/agents/toc/toc_quality_gates_v1.yaml`

## Workflow (iteration `dtr_only`, P0–P4)

1. **P0** — validate `session_brief` YAML; ensure `inputs` exist in repo.
2. **P1** — each role agent: `self_positioning`, `sources_used`.
3. **P2** — each role: ≥3 `undesirable_effects` (no solutions in wording); ≥2 `causal_links` with repo paths.
4. **P3** — orchestrator: `merged_dtr` + mermaid; dedupe NJYA.
5. **P3b** — curator: `sources_gate_verdict` pass|fail.
6. **P4** — orchestrator: 3 `constraint_candidates`, auto-select one (`auto_selected: true`).

## Workflow (iteration `stakeholders_full`, P1–P7)

Same P0–P4 with 8 stakeholder roles, then:

7. **P5** — conflict pair (`p5_conflict_pair`) + security-skib review → `cloud_draft`.
8. **P6** — orchestrator: `dbr_draft`, `transition_tree_draft`; optional `triz-expert-tem`.
9. **P7** — session report with synthesis.

Brief: `docs/ai_sbd/agents/toc/sessions/briefs/tem_toc_stakeholders_full_2026-06-25_001.yaml`

## Role Agent Contract (10 blocks)

`agent_role`, `self_positioning`, `sources_used`, `undesirable_effects`, `causal_links`, `assumptions_facts`, `conflicts_or_needs`, `questions_to_other_agents`, `human_review`, `next_step`.

Validate: `cd code && pipenv run python scripts/toc_response_gate.py --mode role --file <response.md>`

## Headless on Another Node (all in git)

```bash
git clone <repo> && cd <repo>/code
make toc-session-env-setup          # once: venv + check
make toc-session-env-check          # verify brief, inputs, scripts
make toc-dtr-session-dry-run        # 19 planned agent calls (dtr_only)
make toc-stakeholders-full-session-dry-run   # 26 calls (stakeholders_full)
make toc-dtr-session APPLY=1 TOC_DTR_STUB_APPLY=1   # fixture without cursor-agent
make toc-stakeholders-full-session APPLY=1 TOC_DTR_STUB_APPLY=1
make toc-dtr-session APPLY=1        # requires cursor-agent login or CURSOR_API_KEY
```

Default briefs:

- `dtr_only`: `docs/ai_sbd/agents/toc/sessions/briefs/tem_toc_dtr_2026-06-25_001.yaml`
- `stakeholders_full`: `docs/ai_sbd/agents/toc/sessions/briefs/tem_toc_stakeholders_full_2026-06-25_001.yaml`

Install cursor-agent (Linux x64): see `docs/ai_sbd/agents/toc/node_setup.ru.md`

## Quality Gates

From `toc_quality_gates_v1.yaml`:

- role contract: 10/10 blocks;
- NJYA: no imperative solutions in subject;
- DTR: ≥5 «если–то–потому что» in merged_dtr;
- Sources gate: pass before closing P4;
- Constraint: exactly one `selected_constraint` with rationale;
- SKIB terminology canonical.

## Failure Modes

- One agent plays all roles — loses stakeholder conflicts.
- DTR from memory without repo citations.
- Solutions disguised as NJYA.
- Skipping P3b Sources gate.
- Confusing TOC (constraint) with TRIZ (contradiction parameters).

## Integration

| Method | Question |
|--------|----------|
| TOC | What blocks the system now? (ДТР, ограничение) |
| TRIZ | Which parameters conflict? (ТП/ФП, ИКР) |
| SBD | Are ЦБ/ЦПБ preserved? |
