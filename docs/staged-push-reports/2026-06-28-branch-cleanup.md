<!-- doc-meta: status=active version=1.0 updated=2026-06-28 -->

# Branch cleanup — sbd-drones-economics monorepo (2026-06-28)

Worktrees: `sbd-drones-economics-ai`, `sbd-drones-economics`. Remote: `git@gitflic-lk.ru:security-by-design-demos-developers/sbd-drones-economics.git`.

Context: [vuca-block-merge final](2026-06-28-vuca-block-merge-final.md), `docs/ai_dev_tasks.md` § vuca-block-merge.

## Before / after counts

| Scope | Before (non-`master`) | After (non-`master`) | AC (≤5) |
|-------|----------------------:|---------------------:|---------|
| `origin` (shared) | 22 | **4** | PASS |
| Local `-ai` | 15 | **4** | PASS |
| Local `-economics` | 4 | **2** | PASS |

`origin/master` @ `8d5b3b6c` (both worktrees after fetch). `-economics` local `master` @ `e3ec18b2` (3 commits ahead of `origin/master`, 2 behind — not changed in this cleanup).

## Kept branches (remote)

| Branch | Merged into `master`? | Action | Reason |
|--------|----------------------|--------|--------|
| `test/integration-phase0-initiation` | No (28 commits ahead) | **kept** | Canonical `-ai` phase-0 line @ `bda83a48` |
| `feature/uas-dev-company` | No | **kept** | Economics platform line |
| `feature/uas-dev-company-integration` | No | **kept** | Integration variant |
| `tests/phase0-integration--ai` | No (6 ahead) | **kept** | Phase-0 test/docs slice |

## Deleted — fully merged into `master`

| Branch | Merged? | Action |
|--------|---------|--------|
| `vuca/block-a-docs-2026-06-28` … `block-e-operator-tests-2026-06-28` | Yes | deleted local + remote |
| `vuca/master-local` | Yes | deleted local |
| `feature/component_redesign`, `tests-e2e-design` | Yes | deleted local |
| `feature/Jenkins`, `feature/mqtt-e2e`, `feature/smart_contracts` | Yes | deleted remote |
| `docs/integration-phase0-consolidated` | Yes (tip = integration) | deleted local + remote |
| `feature/ai-version--plan` | Yes (ancestor of integration tip) | deleted local + remote |
| `-economics` `vuca/block-b-process-demos-2026-06-28`, `vuca/block-c-qa` | Yes | deleted local |

## Deleted — remote only (unique commits; recovery SHAs)

Merged into `master` was **not** done (conflicts on docs/orchestrator → integration). Tips preserved for `git fetch` recovery from mirrors/reflog or re-create branch:

| Branch | Tip SHA | Unique vs `master` | Action |
|--------|---------|-------------------|--------|
| `alt-insurer` | `65d92572` | 3 commits | remote deleted |
| `docs/orchestrator-v1.1` | `c0a124a0` | 4 | remote deleted; **local kept** on `-ai` |
| `docs/pr-a2-integration-process` | `688f7cbc` | 23 (3 vs integration) | remote deleted; **local kept** (+ worktree) |
| `docs/sprint-120min-2026-06-28` | `2d35c226` | 12 (ancestor of autonomy) | remote + local deleted |
| `docs/sprint-autonomy-policy` | `564e77af` | 13 | remote deleted; **local kept** on `-ai` |
| `feature/elasticsearch` | `b4c7c135` | 4 | remote deleted |
| `feature/github-actions` | `d281c3cc` | 1 | remote deleted |
| `feature/negative-e2e-scenario` | `d6da7c38` | 3 | remote deleted |
| `feature/framework-example` | `188417d6` | 3 | local deleted (both worktrees) |

## human_review

1. **Docs sprint/orchestrator lines** — remote removed to meet ≤5 branch cap; unmerged commits remain on **local** `-ai` branches `docs/orchestrator-v1.1`, `docs/pr-a2-integration-process`, `docs/sprint-autonomy-policy`. Decide: cherry-pick into `test/integration-phase0-initiation` or push one consolidated docs branch after conflict resolution.
2. **Legacy feature remotes** (`alt-insurer`, elasticsearch, github-actions, negative-e2e) — deleted from origin; restore from tip SHAs if any capability is still required.
3. **`-economics` `master` vs `origin/master`** — diverged (`3` / `2`); push/rebase separately from branch cleanup.

## AC / DoD

| Criterion | Result | Evidence |
|-----------|--------|----------|
| AC: ≤5 non-`master` on `origin` | **PASS** | 4 remotes: integration, uas-dev-company, uas-dev-company-integration, tests/phase0-integration--ai |
| AC: ≤5 non-`master` local per worktree | **PASS** | `-ai`: 4; `-economics`: 2 |
| DoD 1: locals = `master` + unmerged only | **PASS** | No merged locals remain (`git branch --merged master` empty on `-ai`) |
| DoD 2: remotes cleaned of merged intermediates | **PASS** | All `vuca/block-*` and merged `feature/*` removed |
| DoD 3: documented cleanup | **PASS** | This file |

## Procedure notes

- `git fetch --prune` in both worktrees.
- Attempted merge `docs/orchestrator-v1.1` → `test/integration-phase0-initiation` — **aborted** (mass conflicts); pivot: cap remotes, retain local doc refs.
- `test/integration-phase0-initiation` @ `bda83a48` — **not** merged into `master`; kept per phase-0 plan.
