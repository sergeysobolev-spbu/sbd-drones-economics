#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-systems/operator/docker-compose.yml}"
SYSTEM_ID="${SYSTEM_ID:-operator-001}"
API_VERSION="${API_VERSION:-v1}"

KAFKA_CONTAINER="${KAFKA_CONTAINER:-operator-kafka}"

operator_topic() {
  # SystemTopics.get_operator(): f"{SYSTEM_ID}.{API_VERSION}.operator"
  echo "${SYSTEM_ID}.${API_VERSION}.operator"
}

fleet_manager_topic() {
  # FleetManager в текущей реализации подписывается на топик из config, по умолчанию "fleet_manager".
  echo "fleet_manager"
}

require_container_running() {
  local name="$1"
  if ! docker inspect -f '{{.State.Status}}' "$name" >/dev/null 2>&1; then
    echo "ERROR: контейнер не найден: $name" >&2
    exit 2
  fi
  local status
  status="$(docker inspect -f '{{.State.Status}}' "$name")"
  if [[ "$status" != "running" ]]; then
    echo "ERROR: контейнер $name не running (status=$status)" >&2
    exit 2
  fi
}

wait_healthy() {
  local name="$1"
  local timeout_s="${2:-60}"
  local deadline=$((SECONDS + timeout_s))
  while (( SECONDS < deadline )); do
    local health status
    health="$(docker inspect -f '{{.State.Health.Status}}' "$name" 2>/dev/null || true)"
    status="$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || true)"
    if [[ "$health" == "healthy" || ( -z "$health" && "$status" == "running" ) ]]; then
      return 0
    fi
    sleep 2
  done
  echo "ERROR: timeout waiting healthy: $name" >&2
  docker ps --format 'table {{.Names}}\t{{.Status}}' | sed -n '1,20p' >&2 || true
  exit 2
}

uuid() {
  python3 - <<'PY'
import uuid
print(uuid.uuid4())
PY
}

produce_json() {
  local topic="$1"
  local json="$2"
  # Иногда при auto-create Kafka может вернуть LEADER_NOT_AVAILABLE в первые миллисекунды.
  # Поэтому делаем несколько попыток.
  local attempts=5
  local i=1
  while (( i <= attempts )); do
    if docker exec -i "$KAFKA_CONTAINER" kafka-console-producer \
      --bootstrap-server localhost:9092 \
      --topic "$topic" >/dev/null <<EOF
$json
EOF
    then
      return 0
    fi
    sleep 1
    i=$((i+1))
  done
  echo "ERROR: failed to produce message to topic=$topic after ${attempts} attempts" >&2
  return 1
}

consume_one() {
  local topic="$1"
  local timeout_ms="${2:-15000}"
  docker exec -i "$KAFKA_CONTAINER" kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic "$topic" \
    --from-beginning \
    --timeout-ms "$timeout_ms" \
    --max-messages 1 2>/dev/null || true
}

assert_json_field() {
  local json="$1"
  local expr="$2"
  python3 - "$json" "$expr" <<'PY' >/dev/null
import json,sys
obj=json.loads(sys.argv[1])
expr=sys.argv[2]
cur=obj
for part in expr.split("."):
  if part not in cur:
    raise SystemExit(f"missing field: {expr}")
  cur=cur[part]
print(cur)
PY
}

