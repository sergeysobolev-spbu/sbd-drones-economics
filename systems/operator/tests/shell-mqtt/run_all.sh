#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running operator MQTT shell integration checks."

"${SCRIPT_DIR}/01_health.sh"
"${SCRIPT_DIR}/02_receive_order.sh"
"${SCRIPT_DIR}/03_fleet_get_uas_list.sh"

echo "OK: all MQTT shell checks passed."

