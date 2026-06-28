#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SYSTEM_ID="${SYSTEM_ID:-operator-001}"
API_VERSION="${API_VERSION:-v1}"

MOSQUITTO_CONTAINER="${MOSQUITTO_CONTAINER:-operator-mosquitto}"

topic_to_mqtt() {
  # SystemBus expects dot-notation; MQTT transport uses slashes on the wire.
  echo "$1" | tr '.' '/'
}

operator_topic() {
  echo "${SYSTEM_ID}.${API_VERSION}.operator"
}

fleet_manager_topic() {
  # FleetManager internal topic учитывает SYSTEM_ID
  echo "${SYSTEM_ID}.fleet_manager"
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

mosq_pub_json() {
  local topic_dot="$1"
  local json="$2"
  local topic_mqtt
  topic_mqtt="$(topic_to_mqtt "$topic_dot")"
  docker exec -i "$MOSQUITTO_CONTAINER" mosquitto_pub -h localhost -t "$topic_mqtt" -m "$json" >/dev/null
}

mosq_sub_one() {
  local topic_dot="$1"
  local timeout_s="${2:-20}"
  local topic_mqtt
  topic_mqtt="$(topic_to_mqtt "$topic_dot")"
  # -C 1: one message; -W: timeout seconds
  docker exec -i "$MOSQUITTO_CONTAINER" mosquitto_sub -h localhost -t "$topic_mqtt" -C 1 -W "$timeout_s" 2>/dev/null || true
}

mosq_request_reply() {
  # Subscribes first (to avoid race), then publishes request JSON, then returns the first reply message.
  local req_topic_dot="$1"
  local reply_topic_dot="$2"
  local req_json="$3"
  local timeout_s="${4:-20}"

  local tmp
  tmp="$(mktemp)"

  # Start subscriber before publish.
  docker exec -i "$MOSQUITTO_CONTAINER" mosquitto_sub -h localhost -t "$(topic_to_mqtt "$reply_topic_dot")" -C 1 -W "$timeout_s" >"$tmp" 2>/dev/null &
  local sub_pid=$!

  # Give subscriber a tiny head start.
  sleep 0.2
  mosq_pub_json "$req_topic_dot" "$req_json"

  wait "$sub_pid" || true
  cat "$tmp"
  rm -f "$tmp"
}

