#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

"${SCRIPT_DIR}/01_health.sh" >/dev/null

REQ_TOPIC="$(operator_topic)"
REPLY_TOPIC="replies.shell.${SYSTEM_ID}.$(date +%s).$RANDOM"
CORR_ID="$(uuid)"

ORDER_ID="ORDER-SHELL-$(date +%Y%m%d%H%M%S)"

REQ_JSON="$(python3 - "$ORDER_ID" "$REPLY_TOPIC" "$CORR_ID" <<'PY'
import json,os,sys
order_id=sys.argv[1]
reply_to=sys.argv[2]
corr_id=sys.argv[3]
msg={
  "action":"receive_order",
  "sender":"shell",
  "correlation_id":corr_id,
  "reply_to":reply_to,
  "payload":{
    "order":{
      "id":order_id,
      "pickup":{"lat":55.76,"lon":37.62},
      "dropoff":{"lat":55.75,"lon":37.61},
      "payload_weight":3.5,
      "distance_km":10.0
    }
  }
}
print(json.dumps(msg, ensure_ascii=False))
PY
)"

echo "Sending receive_order request to ${REQ_TOPIC}"
produce_json "$REQ_TOPIC" "$REQ_JSON"

echo "Waiting for response on ${REPLY_TOPIC}"
RESP="$(consume_one "$REPLY_TOPIC" 20000)"
if [[ -z "${RESP}" ]]; then
  echo "ERROR: no response received (timeout)." >&2
  exit 3
fi

python3 - "$RESP" "$CORR_ID" <<'PY'
import json,sys
resp=json.loads(sys.argv[1])
assert resp.get("correlation_id")==sys.argv[2], f"unexpected correlation_id: {resp.get('correlation_id')}"
payload=resp.get("payload",{})
assert "order_id" in payload or "error" in payload, f"unexpected payload keys: {list(payload.keys())}"
if "error" in payload:
  raise SystemExit(f"operator_system returned error: {payload.get('error')}")
print("OK")
PY

echo "OK: receive_order request completed."

