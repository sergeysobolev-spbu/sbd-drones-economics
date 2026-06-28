---
name: skib-domain-review
description: Reviews security-by-design artifacts for SKIB. Prefer umbrella skill_systems_engineer_sbd for full SE tasks. Use for focused SKIB artifact review, GOST R 72118-2025 terminology, or selecting Sh1-Sh18 agent patterns.
---

# SKIB Domain Review

## Use When

Apply this skill for focused work on artifacts of a system with constructive information security: KPB, CPB, security goals, assumptions, trusted base, policy architecture, threat model, and security tests.

For broader systems engineering tasks (ConOps, V&V, SE schools, RBPO), use **`skill_systems_engineer_sbd`** first.

## Canonical Sources

- `docs/ai_sbd/artifacts/patterns/agent_base_context.yaml` - terminology, GOST digest, design principles, and Appendix A patterns.
- `docs/ai_sbd/artifacts/patterns/skib_agent_patterns.yaml` - canonical Sh1-Sh18 agent pattern catalog.
- `docs/ai_sbd/artifacts/patterns/essence_maturity_router.yaml` - routing by artifact maturity.
- `docs/ai_sbd/artifacts/reuse_catalog/reuse_catalog.yaml` - terms, anti-examples, and teaching fragments.

## Workflow

1. Identify the artifact type and lifecycle stage.
2. Load only the relevant canonical source sections; do not copy large context blocks into the answer.
3. Route the task to one or more Sh1-Sh18 patterns when useful.
4. Separate facts from hypotheses and questions for human review.
5. Check whether conclusions are traced to input artifacts, security goals, assumptions, policy rules, or verification scenarios.
6. Reject generic security advice that is not tied to the system construction.

## Output

Return concise findings or a table with: artifact, issue, evidence, SKIB impact, recommended correction, and required human decision. Mention applicable GOST Appendix A patterns when they materially affect the recommendation.

## Guardrails

- Do not replace SKIB analysis with a list of protective tools.
- Do not formulate final security goals or assumptions without input evidence.
- Do not treat implementation mechanisms such as TLS or a firewall as security goals.
- Use the canonical term: `система с конструктивной информационной безопасностью (в терминах ГОСТ Р 72118-2025)`.
