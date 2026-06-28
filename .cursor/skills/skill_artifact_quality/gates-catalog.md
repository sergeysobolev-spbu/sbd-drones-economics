# Quality Gates Catalog

Canonical gate YAML files for artifact classification in `skill_artifact_quality`.

| Agent / contour | Gate file | Key gates |
|---|---|---|
| `systems-engineer-sbd` | `docs/ai_sbd/agents/systems_engineer_sbd/quality_gates_v1.yaml` | contract, human_review, terminology, evaluation |
| TOC role + orchestrator | `docs/ai_sbd/agents/toc/toc_quality_gates_v1.yaml` | role_contract, njya, dtr, sources, constraint |
| TOC SE Schools | `docs/ai_sbd/agents/se_schools/toc_se_schools_quality_gates_v1.yaml` | school contract, terminology, human_review |
| `se-school-ai-native` | `docs/ai_sbd/agents/se_school_ai_native/se_school_ai_native_quality_gates_v1.yaml` | 10-block contract, baseline split, human_review |
| TRIZ | `docs/ai_sbd/agents/triz/triz_quality_gates_v1.yaml` | TRIZ contract, terminology, human_review |
| `business-dev-platform` | `docs/ai_sbd/agents/business_dev/business_dev_skills_v1.yaml` | context, **editorial**, pilot_evidence, finance, skib_integrity, scale, human_review |

## Supporting artifacts

| Artifact | Path |
|---|---|
| Eval suite (SE-SBD) | `docs/ai_sbd/agents/systems_engineer_sbd/eval_suite_v1.yaml` |
| Quality report template | `docs/ai_sbd/agents/systems_engineer_sbd/quality_report_template.md` |
| Skills registry (SE-SBD) | `docs/ai_sbd/agents/systems_engineer_sbd/skills_v1.yaml` |
| Core skill (SE-SBD) | `.cursor/skills/skill_systems_engineer_sbd/SKILL.md` |
| SE agent rule (IDE) | `.cursor/rules/systems-engineer-sbd-agent.mdc` |
| Agent skill router | `code/config/agent_skill_registry.json` |
| Agent directory | `docs/ai_sbd/agents/directory.md` |
| Internal QA workspace | `docs/ai_sbd/agents/internal_qa/` |
| SE artifact review (stdlib) | `make se-agent-review-artifacts` → `docs/ai_sbd/meta_data/se_agent_review.md` |

## Deterministic checkers

| Checker | When |
|---|---|
| `docs/ai_sbd/scripts/check_agent_quality_suite.py` | After edits to skills/eval/gates V1 |
| `code/scripts/toc_response_gate.py` | TOC role/orchestrator logs |
| `code/scripts/check_documentation_versioning.py` | Active docs under `code/docs/` |
| `docs/ai_sbd/scripts/check_business_dev_deliverables.py` | External business_dev deliverables + pilot↔presentation sync |
| `code/scripts/agent_skill_router.py` | Registry or skill routing changes |
