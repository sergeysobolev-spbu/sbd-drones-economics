#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

echo "Checking compose containers are running/healthy (MQTT)."
docker compose -f "${COMPOSE_FILE}" ps

require_container_running "operator-mosquitto"
require_container_running "operator-security-monitor"
require_container_running "operator-fleet-manager"
require_container_running "operator-mission-planner"
require_container_running "operator-business-logic"
require_container_running "operator-system"

wait_healthy "operator-mosquitto" 60
wait_healthy "operator-security-monitor" 120
wait_healthy "operator-fleet-manager" 120
wait_healthy "operator-mission-planner" 120
wait_healthy "operator-business-logic" 120
wait_healthy "operator-system" 120

echo "OK: all containers running/healthy."

