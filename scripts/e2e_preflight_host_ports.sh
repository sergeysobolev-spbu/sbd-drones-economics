#!/usr/bin/env bash
# Release host ports used by E2E (9092, 29092, 8081) from foreign Docker stacks.
# DevOps gate: prevents silent Kafka start failure when agregator-kafka holds 29092.
set -euo pipefail

E2E_PORTS=(9092 29092 8081 8088)

echo "=== E2E preflight: checking host ports ${E2E_PORTS[*]} ==="

for port in "${E2E_PORTS[@]}"; do
  while read -r line; do
    [ -z "$line" ] && continue
    name="${line%%$'\t'*}"
    ports="${line#*$'\t'}"
    # Host-published port (skip internal-only "9092/tcp")
    if [[ "$ports" == *"0.0.0.0:${port}->"* ]] || [[ "$ports" == *"[::]:${port}->"* ]]; then
      if [[ "$name" == "kafka" ]]; then
        echo "  port ${port}: existing E2E kafka container — will recycle via compose down"
        continue
      fi
      echo "  port ${port}: stopping conflicting container ${name}"
      docker stop "${name}" >/dev/null 2>&1 || true
    fi
  done < <(docker ps --format '{{.Names}}\t{{.Ports}}' 2>/dev/null || true)
done

# Known parallel stacks from other repos (Agregator standalone compose)
for legacy in agregator-kafka-1 agregator-kafka-init-1; do
  if docker ps -q -f "name=^${legacy}$" 2>/dev/null | grep -q .; then
    echo "  stopping legacy stack container ${legacy}"
    docker stop "${legacy}" >/dev/null 2>&1 || true
  fi
done

echo "=== E2E preflight done ==="
