---
name: skill_artifact_quality
description: Reviews artifacts for quality criteria, completeness, and cross-artifact coherence across SKIB, TOC/TRIZ, agent-native, platform docs, and headless agent outputs. Use when auditing deliverables, pre-merge gates, session merges, or when the user asks for artifact quality, completeness, or coherence control.
---

# Skill Artifact Quality

## Use When

Apply this skill when a deliverable may be marked **готово**, merged, published, or handed to an external audience — and you must verify **criteria**, **completeness**, and **coherence** before that.

Typical inputs:

- Agent session logs (7/10/12-block contracts).
- SKIB artifacts (КБП, ЦПБ, АП, ДВБ, tests, traceability matrices).
- TOC/TRIZ merged sessions and stakeholder packs.
- Active Markdown docs, demo-packs, agent profiles/skills.
- Headless agent issue logs and integrate reports.

## Three Review Dimensions

| Dimension | Question | Primary signals |
|---|---|---|
| **Criteria** | Does it meet declared gates and `quality_grade` rules? | quality gate YAML, eval thresholds, human_review status |
| **Completeness** | Are required blocks, fields, registrations, and evidence present? | contract blocks, doc-meta, README index, eval `must_have_output` |
| **Coherence** | Do linked artifacts agree (terms, IDs, chains, code↔docs↔tests)? | traceability, cross-links, terminology, matrix sync |

**СКИБ** — система с конструктивной информационной безопасностью (в терминах ГОСТ Р 72118-2025). Reject competing definitions.

## Audience-aware gates

| `doc-meta` audience | Editorial requirement | Checker |
|---|---|---|
| `external` | Литературный русский; без anglicisms в теле (см. `markdown_russian_terms.py`); без кальки gates→«ворота» | `check_business_dev_deliverables.py` |
| `internal` | MBA/startup terms допустимы в workspace; handoff to human still needs Russian for cited excerpts | optional sample |
| unset in `business_dev/` | Treat as **internal** until marked `external` | doc-meta only |

**Два grade в отчёте QA (external handoff):**

- `structural_qa_grade` — meta, links, gates, CI;
- `editorial_qa_grade` — язык, таблицы, audience.

Release/human handoff для `audience=external` требует **оба** ≥ `приемлемо`. Не завышать общий `quality_grade` по structural metrics alone.

Правило: [`.cursor/rules/business-dev-deliverables-quality.mdc`](../../rules/business-dev-deliverables-quality.mdc).

## Workflow

### 1. Classify artifact

Pick one primary type (others as secondary checks):

| Type | Gate source | Contract blocks |
|---|---|---|
| `systems-engineer-sbd` response | `docs/ai_sbd/agents/systems_engineer_sbd/quality_gates_v1.yaml` | 7 blocks (situation … next_step) |
| TOC role agent (P1–P2) | `docs/ai_sbd/agents/toc/toc_quality_gates_v1.yaml` | 10 role blocks |
| TOC orchestrator merge | same + `toc_response_gate.py` | P3/P3b blocks |
| TOC SE Schools | `docs/ai_sbd/agents/se_schools/toc_se_schools_quality_gates_v1.yaml` | school contract |
| Agent-native SE | `docs/ai_sbd/agents/se_school_ai_native/se_school_ai_native_quality_gates_v1.yaml` | 10 operational blocks |
| TRIZ session | `docs/ai_sbd/agents/triz/triz_quality_gates_v1.yaml` | TRIZ contract |
| Platform active doc | `.cursor/rules/documentation-governance-and-terms.mdc` | doc-meta + README registration |
| Code/CI change bundle | `.cursor/rules/change-validation-matrix.mdc` | tests + docs sync |

Full gate paths: [gates-catalog.md](gates-catalog.md).

### 2. Completeness pass

1. List **required blocks/fields** from the gate YAML; mark each present/missing/partial.
2. For Markdown active docs: `doc-meta` in first 15 lines, entry in `code/docs/README.md` when applicable.
3. For SKIB chains: every ЦБ/ПБ cited in output must link to damage, owner, and verification hook (or explicit gap).
4. For sessions: raw logs + merged file + brief YAML exist; filenames match session id.
5. For headless packages: `issue-<N>.log`, gates in `summary.json`, human integrate step documented.

Record gaps as `missing_items[]` with severity `blocking` | `major` | `minor`.

### 3. Coherence pass

1. **Terminology**: scan for forbidden SKIB phrases from gate YAML; one canonical expansion per document.
2. **Cross-links**: referenced paths exist; no broken relative links in touched docs.
3. **Traceability**: invoke `skill_traceability` when security goals, policy, or tests are in scope.
4. **Code↔docs↔tests**: if behavior changed, matching doc/matrix/test exists (see `platform-validation`).
5. **Anti-duplication**: no copied operational runbooks; canonical source linked instead (`documentation-governance`).
6. **Agent ecosystem**: new agent/skill registered in `docs/ai_sbd/agents/directory.md`, `ai_agents_skills.md`, `agent_skill_registry.json` when added.

Record breaks as `coherence_findings[]` with `artifact_a`, `artifact_b`, `conflict`.

### 4. Criteria / gates pass

1. Apply **contract_gate**, **terminology_gate**, **human_review_gate** from the relevant YAML.
2. Never accept `review_status: approved` without reviewer roles and decision owners (`skill_human_review`).
3. Map `quality_grade`: **приемлемо** / **требует доработки** / **опасно** — justify against evidence, not optimism.
4. For eval-backed agents: check thresholds in `evaluation_gate` (e.g. `traceability_completeness_ratio >= 0.80`).

### 5. Deterministic checks (run when applicable)

From repo root `code/` unless noted:

```bash
# Agent config consistency (needs pipenv / PyYAML)
pipenv run python ../docs/ai_sbd/scripts/check_agent_quality_suite.py

# Business dev external deliverables (editorial)
python3 ../docs/ai_sbd/scripts/check_business_dev_deliverables.py

# Documentation versioning
python3 scripts/check_documentation_versioning.py

# TOC response structure
python3 scripts/toc_response_gate.py --help   # use documented mode for the artifact

# SE knowledge-base readiness
make se-agent-review-artifacts

# Platform validation matrix (pick targets)
make test-regression-fast   # or narrower targets from change-validation-matrix
```

Run only checks whose zone changed; report **executed**, **skipped**, **failed**.

### 6. Delegate to specialized skills

| Finding domain | Skill |
|---|---|
| ЦПБ / ЦБ / ПБ content | `skill_cpb_review` |
| Proof chains | `skill_traceability` |
| Human gate / ownership | `skill_human_review` |
| Doc governance | `documentation-governance` |
| CI/tests/ports | `platform-validation` |
| SKIB domain semantics | `skib-domain-review` |
| Security change blast radius | `skib-change-impact` |

Do not duplicate their deep checks — reference their outputs in the quality report.

## Output Schema (mandatory)

```markdown
## artifact_scope
- type, paths, intended audience, gate set used

## completeness_verdict
- pass | fail
- missing_items[]

## coherence_verdict
- pass | fail
- coherence_findings[]

## criteria_verdict
- pass | fail
- gate_results[] (gate id, status, evidence)

## quality_grade
- приемлемо | требует доработки | опасно
- rationale (1–3 sentences)

## editorial_qa_grade
- приемлемо | требует доработки | n/a
- required when `audience=external` or program committee / partner pack

## human_review
- reviewer_roles, blocking_findings, decision_owners, review_status

## deterministic_checks
- command, result, notes

## required_updates
- smallest set of edits to reach pass

## next_step
- one concrete action for owner
```

For release cycles, also fill sections from `docs/ai_sbd/agents/systems_engineer_sbd/quality_report_template.md`.

## Failure Modes

- Passing completeness while coherence is broken (e.g. ЦБ in doc ≠ ЦБ in tests).
- Marking **готово** without `human_review` or with `review_status: blocked`.
- Running generic praise instead of gate-by-gate evidence.
- Claiming CI/doc checks ran without command output.
- Treating narrative plausibility as traceability.

## Related Rules

- `.cursor/rules/documentation-governance-and-terms.mdc`
- `.cursor/rules/documentation-versioning.mdc`
- `.cursor/rules/change-validation-matrix.mdc`
- `docs/ai_sbd/ai_agents_skills.md`
