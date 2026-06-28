---
name: skill_traceability
description: Builds and verifies traceability from security goals to policy rules, trusted components, and verification scenarios. Invoked from skill_artifact_quality for coherence and completeness of proof chains.
---

# Skill Traceability

## Use When

Apply this skill when teams need proof that outputs are connected to artifacts and checks, especially before release or merge.

## Inputs

- Security goals and assumptions (ЦПБ).
- Policy architecture fragments (АП).
- Trusted base boundaries (ДВБ).
- Test specifications and CI evidence.

## Steps

1. Build chain: damage -> goal -> policy rule -> trusted component -> test.
2. Mark broken links and missing ownership.
3. Identify links that rely on assumptions only.
4. Recommend smallest artifact update set to restore completeness.
5. Export concise evidence matrix.

## Output Schema

- `traceability_matrix`
- `coverage_ratio`
- `broken_links`
- `required_updates`
- `verification_plan`

## Pattern Mapping Coverage

- Core: Ш7, Ш8, Ш14, Ш15.
- Supporting: Ш9, Ш16.

## Failure Modes

- Reporting matrix completeness without checking each chain element.
- Mixing policy intent and implementation evidence.
- Omitting negative test linkage for critical goals.
