#!/usr/bin/env bash
# Ожидание HTTP health-check E2E-сервиса.
# URL из аргумента или AGREGATOR_URL/REGULATOR_URL (профиль E2E_RUN_MODE).
set -euo pipefail

label="${1:?label required}"
url="${2:?url required}"
tries="${3:-60}"
sleep_sec="${4:-5}"

echo "=== Waiting for ${label} (${url}) ==="
for i in $(seq 1 "$tries"); do
  if curl -sf "$url" >/dev/null 2>&1; then
    echo "${label} is up"
    exit 0
  fi
  if [ "$i" -eq "$tries" ]; then
    echo "WARNING: ${label} did not respond after $((tries * sleep_sec))s (${url})"
    exit 0
  fi
  sleep "$sleep_sec"
done
