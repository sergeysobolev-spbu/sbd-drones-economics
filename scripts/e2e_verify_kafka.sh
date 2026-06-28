#!/usr/bin/env bash
# Проверка, что Kafka текущего compose-проекта поднят (не чужой контейнер на host-порту).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_COMPOSE_DIR="${E2E_COMPOSE_DIR:-.generated/e2e}"
E2E_PROFILE="${E2E_PROFILE:-kafka}"
GEN_ENV="${ROOT_DIR}/${E2E_COMPOSE_DIR}/.env"
COMPOSE_FILE="${ROOT_DIR}/${E2E_COMPOSE_DIR}/docker-compose.yml"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "ERROR: compose not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

compose_env=()
if [[ -f "${GEN_ENV}" ]]; then
  compose_env=(--env-file "${GEN_ENV}")
fi

KAFKA_PORT=9092
KAFKA_INTERNAL_PORT=29092
if [[ -f "${GEN_ENV}" ]]; then
  # shellcheck disable=SC1090
  set -a && source "${GEN_ENV}" && set +a
  KAFKA_PORT="${KAFKA_PORT:-9092}"
  KAFKA_INTERNAL_PORT="${KAFKA_INTERNAL_PORT:-29092}"
fi

resolve_foreign_on_port() {
  local port="$1"
  docker ps --format '{{.Names}}\t{{.Ports}}' \
    | awk -v port=":${port}->" '$0 ~ port {print $1; exit}'
}

cid="$(docker compose -f "${COMPOSE_FILE}" "${compose_env[@]}" --profile "${E2E_PROFILE}" ps -q kafka 2>/dev/null | head -n 1 || true)"

if [[ -z "${cid}" ]]; then
  foreign="$(resolve_foreign_on_port "${KAFKA_PORT}" || true)"
  echo "ERROR: kafka не запущен в compose ${E2E_COMPOSE_DIR} (профиль ${E2E_PROFILE})." >&2
  if [[ -n "${foreign}" ]]; then
    echo "       Порт ${KAFKA_PORT} занят контейнером «${foreign}»." >&2
  fi
  exit 1
fi

state="$(docker inspect --format '{{.State.Status}}' "${cid}" 2>/dev/null || true)"
name="$(docker inspect --format '{{.Name}}' "${cid}" 2>/dev/null | sed 's/^\/\+//' || true)"

if [[ "${state}" != "running" ]]; then
  echo "ERROR: kafka «${name}» в состоянии «${state}», а не running." >&2
  exit 1
fi

echo "Kafka OK: ${name} (compose ${E2E_COMPOSE_DIR}, port ${KAFKA_PORT})"
