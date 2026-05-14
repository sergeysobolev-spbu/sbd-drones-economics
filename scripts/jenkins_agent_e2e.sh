#!/usr/bin/env bash
# Запуск E2E в образе CI-агента (как стадии Init + E2E + post в Jenkinsfile).
# Требуется Docker на хосте и собранный JENKINS_AGENT_IMAGE.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f docker/.env ]; then
	cp docker/example.env docker/.env
fi
set -a
# shellcheck disable=SC1091
. docker/.env
set +a

IMG="${JENKINS_AGENT_IMAGE:-drones-jenkins-agent:local}"

exec docker run --rm -u root \
	-v "${ROOT}:/workspace" -w /workspace \
	-v /var/run/docker.sock:/var/run/docker.sock \
	"${IMG}" \
	bash -ce '
		git config --global --add safe.directory /workspace
		git submodule update --init --recursive
		python3 -m pip install --upgrade pip setuptools wheel
		python3 -m pip install pipenv
		command -v pipenv
		docker --version
		docker compose version
		make --version
		PIPENV_PIPFILE=config/Pipfile pipenv install --dev
		make e2e-up
		make e2e-test
		make e2e-logs || true
		make e2e-down
		make docker-down || true
		for sys in systems/*/; do
			[ -f "$sys/Makefile" ] && make -C "$sys" docker-down PROJECT_ROOT="/workspace" 2>/dev/null || true
		done
	'
