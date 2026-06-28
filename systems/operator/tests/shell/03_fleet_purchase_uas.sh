#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

"${SCRIPT_DIR}/01_health.sh" >/dev/null

REQ_TOPIC="$(fleet_manager_topic)"
REPLY_TOPIC="replies.shell.${SYSTEM_ID}.$(date +%s).$RANDOM"
CORR_ID="$(uuid)"

REQ_JSON="$(python3 - "$REPLY_TOPIC" "$CORR_ID" <<'PY'
import json,sys
reply_to=sys.argv[1]
corr_id=sys.argv[2]
msg={
  "action":"GET_UAS_LIST",
  "sender":"shell",
  "correlation_id":corr_id,
  "reply_to":reply_to,
  "payload":{}
}
print(json.dumps(msg, ensure_ascii=False))
PY
)"

echo "Sending GET_UAS_LIST request to ${REQ_TOPIC}"
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
assert "uas_list" in payload or "total_count" in payload or "total" in payload, f"unexpected payload keys: {list(payload.keys())}"
print("OK")
PY

echo "OK: GET_UAS_LIST completed."

