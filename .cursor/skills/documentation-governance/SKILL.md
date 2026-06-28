---
name: documentation-governance
description: Governs Markdown documentation changes: active status, doc-meta versioning, README registration, Russian technical style, SKIB terminology, anti-duplication, and archive handling. Use when creating or editing project documentation; pairs with skill_artifact_quality for doc completeness and coherence checks.
---

# Documentation Governance

## Use When

Apply this skill when editing or creating Markdown documentation, especially under `code/docs` and SKIB educational materials.

## Canonical Sources

- `.cursor/rules/documentation-governance-and-terms.mdc`
- `.cursor/rules/documentation-versioning.mdc`
- `.cursor/rules/documentation-quality-ru.mdc`
- `.cursor/rules/no-wave-task-markers.mdc`
- `code/docs/documentation_versioning.md`
- `code/docs/README.md`

## Workflow

1. Determine whether the document is active, deprecated-candidate, archive, or archive-redirect.
2. For new active docs, add `doc-meta` in the first 15 lines and register the doc in `code/docs/README.md`.
3. For substantial active-doc edits, update `version` and `updated`.
4. Prefer extending canonical documents over creating duplicates.
5. Keep operational instructions in one canonical place; link instead of copying large command blocks.
6. Use literary Russian for connected text and expand non-obvious abbreviations at first important use.

## SKIB Terms

Use `СКИБ — система с конструктивной информационной безопасностью (в терминах ГОСТ Р 72118-2025)`. Do not introduce competing definitions.

## Guardrails

- Do not create active `wave-*` docs or restore wave markers in current docs.
- Do not delete historical documents unless the user explicitly requests it.
- Do not claim validation status without a real check or artifact.
