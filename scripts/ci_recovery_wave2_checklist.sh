#!/usr/bin/env bash
# Wave 2 CI recovery checklist: structural gates before coding APPLY=1.
# Usage:
#   ./scripts/ci_recovery_wave2_checklist.sh
#   WAIT=1 ./scripts/ci_recovery_wave2_checklist.sh   # also trigger canary Jenkins build
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

WAIT="${WAIT:-0}"
FAIL=0
PASSED=()
FAILED=()
SKIPPED=()

log_step() {
  echo ""
  echo "=== [$1] $2 ==="
}

run_make() {
  local id="$1"
  local desc="$2"
  shift 2
  log_step "$id" "$desc"
  if "$@"; then
    PASSED+=("$id: $desc")
    echo "OK: $id"
  else
    FAILED+=("$id: $desc")
    echo "FAIL: $id" >&2
    FAIL=1
  fi
}

skip_step() {
  local id="$1"
  local reason="$2"
  SKIPPED+=("$id: $reason")
  echo "SKIP: $id — $reason"
}

echo "ci_recovery_wave2_checklist: PROJECT_ROOT=$PROJECT_ROOT"
echo "WAIT=${WAIT} (set WAIT=1 to trigger drone-phase0-smoke after structural gates)"

run_make "W2-CH-1" "make ci-config-check" make ci-config-check

if [ -f "$PROJECT_ROOT/ci/jenkins/.env" ]; then
  run_make "W2-CH-2" "make jenkins-preflight" make jenkins-preflight
else
  skip_step "W2-CH-2" "нет ci/jenkins/.env — выполните make jenkins-up"
  FAIL=1
fi

if docker compose -f ci/jenkins/docker-compose.yml ps --status running 2>/dev/null | grep -q jenkins; then
  run_make "W2-CH-3" "make jenkins-jobs-verify" make jenkins-jobs-verify
else
  skip_step "W2-CH-3" "Jenkins не запущен — make jenkins-up && make jenkins-apply-jobs"
  FAIL=1
fi

if [ "$WAIT" = "1" ]; then
  if [ -f "$PROJECT_ROOT/ci/jenkins/.env" ] && \
     docker compose -f ci/jenkins/docker-compose.yml ps --status running 2>/dev/null | grep -q jenkins; then
    run_make "W2-CH-4" "make jenkins-build-phase0-smoke WAIT=1 (canary)" \
      make jenkins-build-phase0-smoke WAIT=1
  else
    skip_step "W2-CH-4" "WAIT=1 но Jenkins недоступен"
    FAIL=1
  fi
else
  SKIPPED+=("W2-CH-4: optional canary (set WAIT=1)")
  echo ""
  echo "=== [W2-CH-4] optional: WAIT=1 make jenkins-build-phase0-smoke — skipped ==="
fi

echo ""
echo "=========================================="
echo "ci_recovery_wave2_checklist SUMMARY"
echo "=========================================="
echo "Passed (${#PASSED[@]}):"
if [ ${#PASSED[@]} -eq 0 ]; then
  echo "  (none)"
else
  for item in "${PASSED[@]}"; do echo "  ✓ $item"; done
fi
if [ ${#SKIPPED[@]} -gt 0 ]; then
  echo "Skipped (${#SKIPPED[@]}):"
  for item in "${SKIPPED[@]}"; do echo "  ○ $item"; done
fi
if [ ${#FAILED[@]} -gt 0 ]; then
  echo "Failed (${#FAILED[@]}):"
  for item in "${FAILED[@]}"; do echo "  ✗ $item"; done
fi
echo "=========================================="

if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAIL — Wave 2 coding blocked until checklist green" >&2
  exit 1
fi

echo "RESULT: PASS — Wave 2 structural gates OK (HR-1/HR-6 still required for APPLY=1)"
exit 0
