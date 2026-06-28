<!-- doc-meta: status=active version=0.1 updated=2026-06-28 audience=internal -->

# Agent task packages для Fabric smart contracts

Документ задаёт issue-scoped пакеты для агентной работы с Fabric. Один пакет должен выполняться в одном worktree одним coding/review агентом; `human_review` требуется для ADR, trusted boundary, privacy, CI gate и release decisions.

## Общие Правила

| Правило | Смысл |
|---|---|
| Один пакет = один scope | Не смешивать chaincode, CI, privacy и учебный handoff в одном coding task. |
| Сначала контракт | До кода должна быть contract matrix или ADR delta. |
| Evidence обязателен | Каждый пакет завершает работу ссылкой на тест, лог, матрицу или owner-approved defer. |
| No soft-green | `skip` обязательного Fabric path не считается успехом. |
| No secrets | Не коммитить ключи, crypto-config, connection profiles, реальные PII/коммерческие данные. |

## Пакеты

| Package | Agent | Task type | Первый результат |
|---|---|---|---|
| FAB-P1-CONTRACT-MATRIX | `fabric-chaincode-engineer` | `fabric_chaincode_contracts` | Таблица методов P1: args, role/MSP, events, tests, gaps. |
| FAB-P1-TRACEABILITY | `eventjournal-traceability-sdet` | `ledger_eventjournal_traceability` | Заполненные строки `fabric_traceability_matrix.md` для P1. |
| FAB-P1-PRIVACY | `ledger-privacy-reviewer` | `ledger_privacy_review` | Классификация on-chain/off-chain полей и generated crypto risks. |
| FAB-P1-FAST-TESTS | `eventjournal-traceability-sdet` | `fabric_e2e_sdet` | Unit/mock proxy test plan без Fabric-сети. |
| FAB-P1-CI-MODE | `fabric-devops-cicd-steward` | `fabric_devops_cicd` | PR-E3 decision log и команда manual/nightly запуска. |
| FAB-P1-LAB | `fabric-lab-instructor` | `contract_lab_design` | Лабораторная карточка и рубрика для contract review. |
| FAB-P2-DUAL-WRITE | `ledger-integration-architect` + `tem-bas-operator` | `integration_contract_governance` | Draft design `ledger_explicit` -> `dual_write`, без включения в PR-E1. |

## Issue-ready Files

| Фаза | Issue file |
|---|---|
| F1 | [`issues/ISSUE-F1-fabric-contract-matrix.md`](issues/ISSUE-F1-fabric-contract-matrix.md) |
| F2 | [`issues/ISSUE-F2-fabric-negative-tests.md`](issues/ISSUE-F2-fabric-negative-tests.md) |
| F3 | [`issues/ISSUE-F3-fabric-smoke-runbook.md`](issues/ISSUE-F3-fabric-smoke-runbook.md) |
| F4 | [`issues/ISSUE-F4-eventjournal-correlation.md`](issues/ISSUE-F4-eventjournal-correlation.md) |
| F5 / PR-E3 | [`issues/ISSUE-PR-E3-fabric-e2e-mode.md`](issues/ISSUE-PR-E3-fabric-e2e-mode.md) |

## Package Contract

Каждый агент возвращает:

```markdown
## package_id
## scope
## files_changed_or_reviewed
## vuca_assessment
## evidence
## blockers
## human_review
## next_package
```

## Readiness Gates

| Gate | Условие |
|---|---|
| Start P1 | ADR-004/005/006/007/008/009 reviewed or accepted as proposed by orchestrator. |
| Start tests | Contract matrix has P1 methods and negative cases. |
| Start CI mode | Local/manual command exists and evidence bundle template filled. |
| Start dual-write | EventJournal correlation accepted and Fabric failure semantics defined. |
| Start course lab | Преподаватель выбрал Fabric как обязательный или продвинутый модуль. |
