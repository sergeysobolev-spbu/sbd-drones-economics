#!/usr/bin/env bash
# Применить JCasC (job definitions) и проверить список job в UI.
#
# Usage (из корня репозитория):
#   make jenkins-apply-jobs
#   bash scripts/jenkins_apply_casc.sh --verify-only
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JENKINS_DIR="$PROJECT_ROOT/ci/jenkins"
ENV_FILE="$JENKINS_DIR/.env"

VERIFY_ONLY=0
if [ "${1:-}" = "--verify-only" ]; then
  VERIFY_ONLY=1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: нет $ENV_FILE — выполните make jenkins-up" >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
. "$ENV_FILE"
set +a

HOST="${JENKINS_URL:-http://localhost:${JENKINS_HTTP_PORT:-8080}/}"
HOST="${HOST%/}"
AUTH="${JENKINS_ADMIN_USER:-admin}:${JENKINS_ADMIN_PASSWORD:-changeme}"
HOST_CASC="$JENKINS_DIR/casc.yaml"

if [ ! -f "$HOST_CASC" ]; then
  echo "ERROR: не найден $HOST_CASC" >&2
  exit 1
fi

EXPECTED_JOBS="$(
  grep -oE "pipelineJob\('[^']+'\)" "$HOST_CASC" \
    | sed -E "s/pipelineJob\('([^']+)'\)/\1/" \
    | sort -u
)"

wait_for_jenkins() {
  local attempt
  for attempt in $(seq 1 60); do
    if curl -sf -o /dev/null -u "$AUTH" "$HOST/login"; then
      return 0
    fi
    sleep 2
  done
  echo "ERROR: Jenkins не отвечает на $HOST/login (поднимите: make jenkins-up)" >&2
  return 1
}

reload_casc() {
  local cookie_jar http_code
  cookie_jar="$(mktemp)"
  trap "rm -f '${cookie_jar}'" RETURN

  local crumb_json crumb_field crumb_value
  crumb_json="$(curl -sf -u "$AUTH" -c "$cookie_jar" -b "$cookie_jar" "$HOST/crumbIssuer/api/json")"
  crumb_field="$(echo "$crumb_json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["crumbRequestField"])')"
  crumb_value="$(echo "$crumb_json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["crumb"])')"

  http_code="$(
    curl -s -o /dev/null -w "%{http_code}" -u "$AUTH" -c "$cookie_jar" -b "$cookie_jar" \
      -H "${crumb_field}: ${crumb_value}" \
      -X POST "$HOST/configuration-as-code/reload"
  )"
  case "$http_code" in
    200|302) ;;
    *)
      echo "ERROR: configuration-as-code/reload вернул HTTP $http_code" >&2
      return 1
      ;;
  esac
  echo ">>> JCasC reload OK (HTTP $http_code), источник jobs: $HOST_CASC"
}

list_jobs() {
  curl -sf -u "$AUTH" "$HOST/api/json" \
    | python3 -c 'import sys,json; print("\n".join(sorted(j["name"] for j in json.load(sys.stdin).get("jobs",[]))))'
}

verify_jobs() {
  local actual missing=""
  actual="$(list_jobs)"
  while IFS= read -r job; do
    [ -n "$job" ] || continue
    if ! echo "$actual" | grep -qx "$job"; then
      missing="${missing}${job}\n"
    fi
  done <<< "$EXPECTED_JOBS"

  if [ -n "$missing" ]; then
    echo "ERROR: в UI отсутствуют job из $HOST_CASC:" >&2
    printf '%b' "$missing" >&2
    echo "Текущие job:" >&2
    echo "$actual" >&2
    echo "Выполните: make jenkins-apply-jobs" >&2
    return 1
  fi
  echo ">>> Все $(echo "$EXPECTED_JOBS" | grep -c .) job из CASC присутствуют в UI"
  echo "$actual" | sed 's/^/    /'
  return 0
}

main() {
  wait_for_jenkins
  if [ "$VERIFY_ONLY" -eq 0 ]; then
    reload_casc
    sleep 2
  fi
  verify_jobs
}

main
