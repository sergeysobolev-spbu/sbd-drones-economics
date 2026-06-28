#!/usr/bin/env bash
# Preflight: GIT_BRANCH существует на remote; volume drones изолирован от platform Jenkins.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/ci/jenkins/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: нет $ENV_FILE — выполните make jenkins-up" >&2
  exit 1
fi

set -a
# shellcheck source=/dev/null
. "$ENV_FILE"
set +a

REPO_URL="${GIT_REPO_URL:-}"
BRANCH="${GIT_BRANCH:-master}"

if [ -z "$REPO_URL" ]; then
  echo "ERROR: GIT_REPO_URL не задан в $ENV_FILE" >&2
  exit 1
fi

if [[ "$REPO_URL" == file://* ]]; then
  echo "jenkins-preflight: local SCM ($REPO_URL) — проверка remote-ветки пропущена"
  exit 0
fi

echo "jenkins-preflight: проверка refs/heads/${BRANCH} на ${REPO_URL}"

if ! git ls-remote --exit-code "$REPO_URL" "refs/heads/${BRANCH}" >/dev/null 2>&1; then
  echo "ERROR: ветка '${BRANCH}' не найдена на ${REPO_URL}" >&2
  echo "  Задайте GIT_BRANCH=master (или существующую ветку) в ci/jenkins/.env" >&2
  echo "  Либо push CI-изменений в '${BRANCH}' перед запуском job." >&2
  exit 1
fi

echo "jenkins-preflight: OK — refs/heads/${BRANCH} существует"
