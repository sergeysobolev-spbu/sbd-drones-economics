#!/usr/bin/env bash
# Release host ports used by E2E from foreign Docker stacks.
# Ports from config/e2e_ports.*.env (via caller: make e2e-up sources E2E_ENV).
set -euo pipefail

E2E_PORTS=(
  "${KAFKA_PORT:-9092}"
  "${KAFKA_INTERNAL_PORT:-29092}"
  "${AGREGATOR_PORT:-8081}"
  "${REGULATOR_PORT:-8088}"
  "${ANALYTICS_PORT:-8090}"
)

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
