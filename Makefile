.PHONY: help init unit-test tests test-dummy-fabric ci-unit-test ci-integration-test ci-test ci-config-check ci-recovery-check docker-up docker-down docker-logs docker-ps docker-clean prepare-multi e2e-up e2e-test e2e-logs e2e-down e2e e2e-codespace e2e-local e2e-mqtt-up e2e-mqtt-test e2e-mqtt-down e2e-mqtt jenkins-up jenkins-down jenkins-restart jenkins-logs jenkins-ps jenkins-preflight jenkins-apply-jobs jenkins-jobs-verify jenkins-reload-casc jenkins-build-unit jenkins-build-integration jenkins-build-e2e jenkins-build-agrodron-security-monitor jenkins-build-dummy-fabric-unit jenkins-build-phase0-smoke ports-check smart-contract-init smart-contract-up smart-contract-down e2e-smart-contracts-test e2e-smart-contracts

PROJECT_ROOT := $(CURDIR)
DOCKER_COMPOSE = docker compose -f docker/docker-compose.yml --env-file docker/.env
LOAD_ENV = set -a && . docker/.env && set +a
E2E_RUN_MODE ?= local
E2E_PORTS_FILE = config/e2e_ports.$(E2E_RUN_MODE).env
LOAD_E2E_PORTS = set -a && test -f $(E2E_PORTS_FILE) && . $(E2E_PORTS_FILE) || true && set +a
E2E_ENV = $(LOAD_ENV) && $(LOAD_E2E_PORTS)
PIPENV_PIPFILE = config/Pipfile
PYTEST_CONFIG = config/pyproject.toml
REQUIREMENTS = config/requirements.txt

JENKINS_DIR = ci/jenkins
JENKINS_COMPOSE = docker compose -f $(JENKINS_DIR)/docker-compose.yml --env-file $(JENKINS_DIR)/.env

help:
	@echo "make init              - Установить pipenv и зависимости"
	@echo "make unit-test         - Unit тесты (SDK + broker + standalone компоненты)"
	@echo "make tests             - Все тесты"
	@echo "make test-dummy-fabric - E2E dummy_fabric (pytest systems/dummy_fabric/tests/test_e2e.py)"
	@echo "make ci-unit-test      - CI: unit тесты всех components/ и systems/"
	@echo "make ci-integration-test - CI: integration тесты всех systems/"
	@echo "make ci-test           - CI: unit + integration (все components/ и systems/)"
	@echo "make docker-up         - Запустить инфраструктуру брокера"
	@echo "make docker-down       - Остановить"
	@echo "make docker-logs       - Логи"
	@echo "make docker-ps         - Статус"
	@echo "make docker-clean      - Очистка"
	@echo "make prepare-multi SYSTEMS=\"drone_port gcs\" - Сгенерировать единый compose для нескольких систем"
	@echo "make e2e-up            - Поднять всё окружение E2E (4 системы + брокер + DroneAnalytics)"
	@echo "make e2e-test          - Запустить E2E тесты (pytest tests/e2e/)"
	@echo "make e2e-logs          - Показать события из DroneAnalytics"
	@echo "make e2e-down          - Остановить и очистить E2E окружение"
	@echo "make e2e               - e2e-up + e2e-test + e2e-logs + e2e-down"
	@echo "make e2e-local         - Полный E2E локально (pip, со всеми системами и аналитикой)"
	@echo "make e2e-codespace     - Полный E2E в GitHub Codespace (pip, без аналитики)"
	@echo "make e2e-mqtt-up       - Поднять E2E стенд на MQTT (Kafka + Mosquitto; Agregator OPERATOR_TRANSPORT=both)"
	@echo "make e2e-mqtt-test     - Запустить те же E2E тесты (pytest tests/e2e/test_e2e_scenario.py), транспорт MQTT"
	@echo "make e2e-mqtt-down     - Остановить MQTT E2E стенд"
	@echo "make e2e-mqtt          - e2e-mqtt-up + e2e-mqtt-test + e2e-mqtt-down"
	@echo "make smart-contract-init - Инициализировать submodule fabric-network + установить Fabric"
	@echo "make smart-contract-up   - Поднять сеть Hyperledger Fabric + chaincode"
	@echo "make smart-contract-down - Остановить сеть Hyperledger Fabric"
	@echo "make e2e-smart-contracts-test - Запустить только SC E2E (pytest tests/e2e/test_e2e_smart_contracts_scenario.py)"
	@echo "make e2e-smart-contracts - Полный цикл: init + smart-contract-up + e2e-up + SC тесты + teardown"
	@echo "make jenkins-up        - Поднять Jenkins (JCasC, авто-конфиг jobs)"
	@echo "make jenkins-down      - Остановить Jenkins"
	@echo "make jenkins-restart   - Перезапустить Jenkins"
	@echo "make jenkins-logs      - Логи Jenkins"
	@echo "make jenkins-ps        - Статус Jenkins"
	@echo "make jenkins-build-unit         - Триггер job drone-unit"
	@echo "make jenkins-build-integration  - Триггер job drone-integration"
	@echo "make jenkins-build-e2e          - Триггер job drone-e2e"
	@echo "make jenkins-build-agrodron-security-monitor - Триггер job drone-agrodron-security-monitor"
	@echo "make jenkins-build-dummy-fabric-unit - Триггер job drone-dummy-fabric-unit"
	@echo "make jenkins-build-phase0-smoke   - Триггер job drone-phase0-smoke"
	@echo "make jenkins-preflight            - Проверка GIT_BRANCH на remote (ci/jenkins/.env)"
	@echo "make jenkins-apply-jobs           - JCasC reload + проверка job в UI"
	@echo "make ports-check                  - Реестр портов local/jenkins (docs/ports.md)"
	@echo "make ci-config-check              - ports-check + phase0-smoke structural"
	@echo "make ci-recovery-check            - Wave 2 CI recovery checklist (optional WAIT=1)"

init:
	@command -v pipenv >/dev/null 2>&1 || pip install pipenv
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv install --dev

unit-test:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/unit/ \
		components/dummy_component/tests/ \
		-v

tests: unit-test

test-dummy-fabric:
	@echo "=== dummy_fabric E2E (нужны Fabric + fabric-proxy) ==="
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		systems/dummy_fabric/tests/test_e2e.py -v -s --tb=short

# --- CI: автообнаружение тестов во всех components/ и systems/ ---

ci-unit-test:
	@echo "=== SDK unit tests ==="
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/unit/ -v
	@echo ""
	@fail=0; \
	for dir in components/*/ systems/*/; do \
		[ -d "$$dir" ] || continue; \
		case " $(CI_UNIT_EXCLUDE) " in *" $${dir%/} "*) echo "=== Skipping $$dir (CI_UNIT_EXCLUDE) ==="; continue;; esac; \
		if [ -d "$$dir/tests/unit" ]; then \
			echo "=== Unit tests: $$dir ==="; \
			PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) "$$dir/tests/unit/" -v || fail=1; \
			echo ""; \
		elif [ -d "$$dir/tests" ] && ls "$$dir"/tests/test_*unit*.py >/dev/null 2>&1; then \
			echo "=== Unit tests (legacy): $$dir ==="; \
			PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) "$$dir"/tests/test_*unit*.py -v || fail=1; \
			echo ""; \
		fi; \
	done; \
	if [ $$fail -ne 0 ]; then echo "=== Some unit tests FAILED ==="; exit 1; fi

CI_INTEGRATION_EXCLUDE := systems/dummy_fabric systems/dummy_system \
	systems/SITL-module systems/alt_insurer systems/deliverydron systems/drone_port \
	systems/drones systems/gcs systems/insurer systems/orvd_system \
	systems/team1-regulator_operation_devsecops
# Субмодули с рассинхроном SDK/путей — см. docs/jenkins.md (gcs), import path (orvd_system)
CI_UNIT_EXCLUDE := systems/gcs systems/orvd_system systems/SITL-module \
	systems/team1-regulator_operation_devsecops

# Системы используют фиксированные container_name (insurer: kafka/zookeeper/mosquitto/kafdrop,
# SITL-module: sitl-*) — если предыдущий прогон упал и оставил контейнеры, следующий ловит
# "Conflict. The container name is already in use". Перед каждой системой делаем force-remove
# известных конфликтующих имён. compose-проектные имена (`agregator-*-1`, `drones-*`) docker
# создаёт сам и они не пересекаются между системами.
CI_INTEGRATION_DIRTY_NAMES := kafka zookeeper mosquitto kafdrop \
    sitl-kafka sitl-zookeeper sitl-mosquitto sitl-redis \
    sitl-verifier sitl-controller sitl-core sitl-messaging


ci-integration-test:
	@fail=0; \
	for dir in components/*/ systems/*/; do \
		[ -d "$$dir" ] || continue; \
		case " $(CI_INTEGRATION_EXCLUDE) " in *" $${dir%/} "*) echo "=== Skipping $$dir (excluded) ==="; continue;; esac; \
		if [ -f "$$dir/Makefile" ] && grep -qE '^test-all-docker:|^integration-test:' "$$dir/Makefile" 2>/dev/null; then \
			target=$$(grep -oE '^(test-all-docker|integration-test):' "$$dir/Makefile" | head -1 | tr -d ':'); \
			echo "=== Cleanup leftover broker containers ==="; \
			docker rm -f $(CI_INTEGRATION_DIRTY_NAMES) 2>/dev/null || true; \
			echo "=== Integration tests: $$dir (make $$target) ==="; \
			$(MAKE) -C "$$dir" $$target PROJECT_ROOT=$(PROJECT_ROOT) || fail=1; \
			echo ""; \
		else \
			echo "=== Skipping $$dir (no integration target) ==="; \
		fi; \
	done; \
	docker rm -f $(CI_INTEGRATION_DIRTY_NAMES) 2>/dev/null || true; \
	if [ $$fail -ne 0 ]; then echo "=== Some integration tests FAILED ==="; exit 1; fi

ci-test: ci-unit-test ci-integration-test

ci-config-check: ports-check phase0-smoke
	@python3 scripts/check_jenkins_e2e_makefile.py
	@bash scripts/check_jenkins_submodule_pins.sh
	@test -f $(JENKINS_DIR)/.env && $(MAKE) jenkins-preflight || true

ci-recovery-check:
	@bash scripts/ci_recovery_wave2_checklist.sh

ports-check:
	@test -f docs/ports.md
	@python3 scripts/check_ports_registry.py

docker-up:
	@test -f docker/.env || cp docker/example.env docker/.env
	@set -a && . docker/.env && set +a && \
		profiles="--profile $${BROKER_TYPE:-kafka}"; \
		[ "$${ENABLE_FABRIC:-false}" = "true" ] && profiles="$$profiles --profile fabric"; \
		$(DOCKER_COMPOSE) $$profiles up -d --build

docker-down:
	-$(DOCKER_COMPOSE) --profile kafka --profile fabric down 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt --profile fabric down 2>/dev/null

docker-logs:
	$(DOCKER_COMPOSE) --profile $$(grep BROKER_TYPE docker/.env | cut -d= -f2) logs -f

docker-ps:
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

docker-clean:
	-$(DOCKER_COMPOSE) --profile kafka --profile fabric down -v --rmi local 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt --profile fabric down -v --rmi local 2>/dev/null

prepare-multi:
	@if [ -z "$(SYSTEMS)" ]; then \
		echo "Usage: make prepare-multi SYSTEMS=\"drone_port gcs\""; \
		exit 1; \
	fi
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run python scripts/prepare_multi.py --systems $(SYSTEMS)

# ---------------------------------------------------------------------------
# E2E: full-scenario Docker test (4 systems + broker + DroneAnalytics)
# ---------------------------------------------------------------------------

E2E_SYSTEMS = Agregator insurer operator orvd_system team1-regulator_operation_devsecops gcs drone_port agrodron SITL-module drones
E2E_SYSTEMS_MQTT = $(E2E_SYSTEMS)
E2E_OUTPUT = .generated/e2e
E2E_COMPOSE = docker compose -f $(E2E_OUTPUT)/docker-compose.yml -f tests/e2e/analytics-compose.yml --env-file $(E2E_OUTPUT)/.env
E2E_COMPOSE_NO_ANALYTICS = docker compose -f $(E2E_OUTPUT)/docker-compose.yml --env-file $(E2E_OUTPUT)/.env
E2E_PROFILE = kafka
# При ENABLE_FABRIC=true в e2e-стенд подмешиваются fabric-proxy + ledger-gateway
# (под профилем "fabric" в docker/docker-compose.yml). prepare_multi.py получает
# тот же флаг и объявляет external network fabric_drone в сгенерированном compose.
E2E_FABRIC_PROFILES = $(if $(filter true,$(ENABLE_FABRIC)),--profile fabric,)
# Прогрев стенда после health-чеков: даём Kafka-консьюмерам во всех сервисах
# (Agregator, Operator, Regulator, ORVD, GCS и т.д.) вступить в consumer group,
# иначе первые тесты нестабильны (гейтвеи ловят таймауты до первой ребалансировки).
E2E_WARMUP_SECONDS ?= 120
E2E_WAIT_HEALTH = bash scripts/e2e_wait_health.sh
E2E_VERIFY_KAFKA = bash scripts/e2e_verify_kafka.sh

e2e-up:
	@echo "=== Generating multi-system compose (E2E_RUN_MODE=$(E2E_RUN_MODE), ENABLE_FABRIC=$(ENABLE_FABRIC)) ==="
	@$(E2E_ENV) && E2E_ANALYTICS=1 E2E_RUN_MODE=$(E2E_RUN_MODE) ENABLE_FABRIC=$(ENABLE_FABRIC) PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run python scripts/prepare_multi.py \
		--systems $(E2E_SYSTEMS) --output $(E2E_OUTPUT)
	@echo "ANALYTICS_URL=http://analytics-backend:8080" >> $(E2E_OUTPUT)/.env
	@echo "ANALYTICS_API_KEY=test-api-key-e2e-12345" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "ANALYTICS_PORT=$${ANALYTICS_PORT:-8090}" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "DELIVERY_DRONE_HEALTH_PORT=$${DELIVERY_DRONE_HEALTH_PORT:-8095}" >> $(E2E_OUTPUT)/.env
	@echo "DELIVERYDRON_ROOT=systems/drones" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "AGRODRON_GATEWAY_HOST_PORT=$${AGRODRON_GATEWAY_HOST_PORT:-18081}" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "SYSTEM_MONITOR_HOST_PORT=$${SYSTEM_MONITOR_HOST_PORT:-18090}" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "BROKER_USER=$${ADMIN_USER:-admin}" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "BROKER_PASSWORD=$${ADMIN_PASSWORD:-admin_secret_123}" >> $(E2E_OUTPUT)/.env
	@sed -i 's/^DOCKER_NETWORK=.*/DOCKER_NETWORK=drones_net_e2e_gate/' $(E2E_OUTPUT)/.env 2>/dev/null || echo "DOCKER_NETWORK=drones_net_e2e_gate" >> $(E2E_OUTPUT)/.env
	@echo "=== E2E preflight (host ports / stale stacks) ==="
	-$(E2E_COMPOSE) --profile $(E2E_PROFILE) $(E2E_FABRIC_PROFILES) down -v 2>/dev/null
	@$(E2E_ENV) && bash scripts/e2e_preflight_host_ports.sh
	@echo "=== Starting E2E environment ==="
	$(E2E_COMPOSE) --profile $(E2E_PROFILE) $(E2E_FABRIC_PROFILES) up -d --build
	@echo "=== Waiting for Kafka ($${KAFKA_PORT:-9092}) ==="
	@$(E2E_ENV) && for i in $$(seq 1 60); do nc -z localhost $${KAFKA_PORT:-9092} 2>/dev/null && echo "Kafka port is open" && break; [ $$i -eq 60 ] && echo "ERROR: Kafka did not open port $${KAFKA_PORT:-9092}" && exit 1 || sleep 5; done
	@echo "=== Waiting for Agregator ($${AGREGATOR_PORT:-8081}) ==="
	@$(E2E_ENV) && for i in $$(seq 1 60); do curl -sf http://localhost:$${AGREGATOR_PORT:-8081}/health >/dev/null 2>&1 && echo "Agregator is up" && break; [ $$i -eq 60 ] && echo "WARNING: Agregator did not respond after 300s" || sleep 5; done
	@echo "=== Waiting for Regulator ($${REGULATOR_PORT:-8088}) ==="
	@$(E2E_ENV) && for i in $$(seq 1 30); do curl -sf http://localhost:$${REGULATOR_PORT:-8088}/health >/dev/null 2>&1 && echo "Regulator is up" && break; [ $$i -eq 30 ] && echo "WARNING: Regulator did not respond after 150s" || sleep 5; done
	@echo "=== Waiting for DroneAnalytics ($${ANALYTICS_PORT:-8090}) ==="
	@$(E2E_ENV) && for i in $$(seq 1 60); do curl -sf http://localhost:$${ANALYTICS_PORT:-8090}/ >/dev/null 2>&1 && echo "DroneAnalytics is up" && break; [ $$i -eq 60 ] && echo "WARNING: DroneAnalytics did not respond after 300s" || sleep 5; done
	@$(E2E_ENV) && bash scripts/e2e_warmup.sh
	@echo "=== Warming up Kafka consumer groups ($(E2E_WARMUP_SECONDS)s) ==="
	@sleep $(E2E_WARMUP_SECONDS)
	@echo "=== E2E environment is up ==="

e2e-test:
	@echo "=== Running E2E tests ==="
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest tests/e2e/test_e2e_scenario.py -v -s \
		--tb=short 2>&1 || (echo "E2E tests failed"; exit 1)

phase0-smoke:
	@echo "=== Phase 0 smoke (T14) — structural checks ==="
	@PHASE0_SMOKE_FORCE=1 PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/e2e/test_phase0_smoke.py -v -m phase0_smoke -k Structure --tb=short

phase0-smoke-full:
	@echo "=== Phase 0 smoke (T14) — full (requires stack) ==="
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/e2e/test_phase0_smoke.py -v -m phase0_smoke --tb=short

e2e-logs:
	@echo "=== Fetching events from DroneAnalytics ==="
	@TOKEN=$$(curl -sf -X POST http://localhost:8090/auth/login \
		-H 'Content-Type: application/json' \
		-d '{"username":"admin","password":"admin1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null) && \
	curl -sf http://localhost:8090/log/event?limit=100 \
		-H "Authorization: Bearer $$TOKEN" | python3 -m json.tool 2>/dev/null || \
	echo "(DroneAnalytics not available or no events)"

e2e-down:
	@echo "=== Stopping E2E environment ==="
	-$(E2E_COMPOSE) --profile $(E2E_PROFILE) $(E2E_FABRIC_PROFILES) down -v 2>/dev/null
	@echo "=== E2E environment stopped ==="

e2e: e2e-up e2e-test e2e-logs e2e-down

# ---------------------------------------------------------------------------
# Smart Contracts (Hyperledger Fabric) — init / up / down / full E2E
# ---------------------------------------------------------------------------

FABRIC_NETWORK_DIR = fabric-network/network

smart-contract-init:
	@bash scripts/smart_contracts_init.sh

# install-fabric.sh кладёт бинарники в fabric-network/bin и прописывает PATH
# только в ~/.bashrc / ~/.zshrc. Shell make-а его не подхватывает, поэтому
# generate.sh не находит cryptogen → пробрасываем путь явно.
FABRIC_BIN = $(PROJECT_ROOT)/fabric-network/bin

smart-contract-up:
	@echo "=== Starting Hyperledger Fabric network ==="
	@test -x $(FABRIC_NETWORK_DIR)/start.sh || (echo "fabric-network не инициализирован — выполните make smart-contract-init"; exit 1)
	@test -x $(FABRIC_BIN)/cryptogen || (echo "fabric-network/bin/cryptogen не найден — выполните make smart-contract-init"; exit 1)
	@cd $(FABRIC_NETWORK_DIR) && PATH="$(FABRIC_BIN):$$PATH" ./start.sh up

smart-contract-down:
	@echo "=== Stopping Hyperledger Fabric network ==="
	-@cd $(FABRIC_NETWORK_DIR) && PATH="$(FABRIC_BIN):$$PATH" ./start.sh down 2>/dev/null || true

e2e-smart-contracts-test:
	@echo "=== Running E2E smart-contracts tests ==="
	@$(LOAD_ENV) && PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest \
		tests/e2e/test_e2e_smart_contracts_scenario.py -v -s --tb=short 2>&1 || \
		(echo "E2E smart-contracts tests failed"; exit 1)

# Полный цикл: init → fabric up → e2e stand up → SC-тесты → teardown
# ENABLE_FABRIC=true прокидывается во все шаги работы со стендом, чтобы
# prepare_multi.py включил fabric-proxy + ledger-gateway, и чтобы e2e-down
# знал про --profile fabric (иначе остановка их пропустит).
e2e-smart-contracts:
	@$(MAKE) smart-contract-init
	@$(MAKE) smart-contract-up
	@ENABLE_FABRIC=true $(MAKE) e2e-up
	-@$(MAKE) e2e-smart-contracts-test; status=$$?; \
		echo "=== Tearing down (status=$$status) ==="; \
		ENABLE_FABRIC=true $(MAKE) e2e-down; \
		$(MAKE) smart-contract-down; \
		exit $$status

# ---------------------------------------------------------------------------
# E2E Codespace: без pipenv, без привязки к версии Python
# ---------------------------------------------------------------------------

e2e-codespace:
	@echo "=== Initializing git submodules ==="
	git submodule update --init --recursive
	@echo "=== Installing Python dependencies ==="
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pip install -r $(REQUIREMENTS)
	@echo "=== Preparing docker/.env ==="
	@test -f docker/.env || cp docker/example.env docker/.env
	@echo "=== Cleaning leftover build artifacts ==="
	@rm -rf systems/Agregator/postgres_data 2>/dev/null || true
	@echo "=== Generating multi-system compose (E2E_RUN_MODE=$(E2E_RUN_MODE)) ==="
	@$(E2E_ENV) && E2E_RUN_MODE=$(E2E_RUN_MODE) PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run python scripts/prepare_multi.py --systems $(E2E_SYSTEMS) --output $(E2E_OUTPUT)
	@$(E2E_ENV) && echo "DELIVERY_DRONE_HEALTH_PORT=$${DELIVERY_DRONE_HEALTH_PORT:-8095}" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "AGRODRON_GATEWAY_HOST_PORT=$${AGRODRON_GATEWAY_HOST_PORT:-18081}" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "SYSTEM_MONITOR_HOST_PORT=$${SYSTEM_MONITOR_HOST_PORT:-18090}" >> $(E2E_OUTPUT)/.env
	@sed -i 's/^DOCKER_NETWORK=.*/DOCKER_NETWORK=drones_net_e2e_gate/' $(E2E_OUTPUT)/.env 2>/dev/null || echo "DOCKER_NETWORK=drones_net_e2e_gate" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "BROKER_USER=$${ADMIN_USER:-admin}" >> $(E2E_OUTPUT)/.env
	@$(E2E_ENV) && echo "BROKER_PASSWORD=$${ADMIN_PASSWORD:-admin_secret_123}" >> $(E2E_OUTPUT)/.env
	@echo "=== E2E preflight (host ports / stale stacks) ==="
	-$(E2E_COMPOSE_NO_ANALYTICS) --profile $(E2E_PROFILE) down -v 2>/dev/null
	@$(E2E_ENV) && bash scripts/e2e_preflight_host_ports.sh
	@echo "=== Resetting Docker network ==="
	@docker network rm drones_net_e2e_gate 2>/dev/null || true
	@echo "=== Starting E2E environment (no analytics, E2E_RUN_MODE=$(E2E_RUN_MODE)) ==="
	$(E2E_COMPOSE_NO_ANALYTICS) --profile $(E2E_PROFILE) up -d --build
	@$(E2E_ENV) && E2E_COMPOSE_DIR=$(E2E_OUTPUT) $(E2E_VERIFY_KAFKA)
	@$(E2E_ENV) && $(E2E_WAIT_HEALTH) Agregator "$${AGREGATOR_URL:-http://localhost:8081}/health" 60
	@$(E2E_ENV) && $(E2E_WAIT_HEALTH) Regulator "$${REGULATOR_URL:-http://localhost:8088}/health" 30
	@$(E2E_ENV) && E2E_COMPOSE_DIR=$(E2E_OUTPUT) bash scripts/e2e_warmup.sh
	@echo "=== Warming up Kafka consumer groups ($(E2E_WARMUP_SECONDS)s) ==="
	@sleep $(E2E_WARMUP_SECONDS)
	@echo "=== Running E2E tests ==="
	@$(E2E_ENV) && E2E_SKIP_ANALYTICS=1 PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/e2e/test_e2e_scenario.py -v -s --tb=short 2>&1 || (echo "E2E tests failed"; $(E2E_COMPOSE_NO_ANALYTICS) --profile $(E2E_PROFILE) down -v 2>/dev/null; exit 1)
	@echo "=== Stopping E2E environment ==="
	-$(E2E_COMPOSE_NO_ANALYTICS) --profile $(E2E_PROFILE) down -v 2>/dev/null
	@echo "=== Done ==="

e2e-jenkins-core:
	@$(MAKE) e2e-codespace E2E_RUN_MODE=jenkins

# ---------------------------------------------------------------------------
# E2E Local: полный локальный запуск со всеми системами и DroneAnalytics
# ---------------------------------------------------------------------------

e2e-local:
	@echo "=== Initializing git submodules ==="
	git submodule update --init --recursive
	@echo "=== Installing Python dependencies ==="
	pip install -r $(REQUIREMENTS)
	@echo "=== Preparing docker/.env ==="
	@test -f docker/.env || cp docker/example.env docker/.env
	@echo "=== Cleaning leftover build artifacts ==="
	@rm -rf systems/Agregator/postgres_data 2>/dev/null || true
	@echo "=== Generating multi-system compose ==="
	@$(LOAD_ENV) && E2E_ANALYTICS=1 python scripts/prepare_multi.py --systems $(E2E_SYSTEMS) --output $(E2E_OUTPUT)
	@echo "ANALYTICS_URL=http://analytics-backend:8080" >> $(E2E_OUTPUT)/.env
	@echo "ANALYTICS_API_KEY=test-api-key-e2e-12345" >> $(E2E_OUTPUT)/.env
	@echo "ANALYTICS_PORT=8090" >> $(E2E_OUTPUT)/.env
	@echo "DELIVERY_DRONE_HEALTH_PORT=8095" >> $(E2E_OUTPUT)/.env
	@echo "AGRODRON_GATEWAY_HOST_PORT=18081" >> $(E2E_OUTPUT)/.env
	@echo "SYSTEM_MONITOR_HOST_PORT=18090" >> $(E2E_OUTPUT)/.env
	@$(LOAD_ENV) && echo "BROKER_USER=$${ADMIN_USER:-admin}" >> $(E2E_OUTPUT)/.env
	@$(LOAD_ENV) && echo "BROKER_PASSWORD=$${ADMIN_PASSWORD:-admin_secret_123}" >> $(E2E_OUTPUT)/.env
	@echo "=== Resetting Docker network ==="
	@docker network rm $${DOCKER_NETWORK:-drones_net} 2>/dev/null || true
	@echo "=== Starting E2E environment (with analytics) ==="
	$(E2E_COMPOSE) --profile $(E2E_PROFILE) up -d --build
	@echo "=== Waiting for Agregator (8081) ==="
	@for i in $$(seq 1 60); do curl -sf http://localhost:8081/health >/dev/null 2>&1 && echo "Agregator is up" && break; [ $$i -eq 60 ] && echo "WARNING: Agregator did not respond after 300s" || sleep 5; done
	@echo "=== Waiting for Regulator (8088) ==="
	@for i in $$(seq 1 30); do curl -sf http://localhost:8088/health >/dev/null 2>&1 && echo "Regulator is up" && break; [ $$i -eq 30 ] && echo "WARNING: Regulator did not respond after 150s" || sleep 5; done
	@echo "=== Waiting for DroneAnalytics (8090) ==="
	@for i in $$(seq 1 60); do curl -sf http://localhost:8090/ >/dev/null 2>&1 && echo "DroneAnalytics is up" && break; [ $$i -eq 60 ] && echo "WARNING: DroneAnalytics did not respond after 300s" || sleep 5; done
	@$(LOAD_ENV) && bash scripts/e2e_warmup.sh
	@echo "=== Warming up Kafka consumer groups ($(E2E_WARMUP_SECONDS)s) ==="
	@sleep $(E2E_WARMUP_SECONDS)
	@echo "=== Running E2E tests ==="
	@$(LOAD_ENV) && python -m pytest tests/e2e/test_e2e_scenario.py -v -s --tb=short 2>&1 || (echo "E2E tests failed"; $(E2E_COMPOSE) --profile $(E2E_PROFILE) down -v 2>/dev/null; exit 1)
	@echo "=== Fetching events from DroneAnalytics ==="
	@TOKEN=$$(curl -sf -X POST http://localhost:8090/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null) && curl -sf http://localhost:8090/log/event?limit=100 -H "Authorization: Bearer $$TOKEN" | python3 -m json.tool 2>/dev/null || echo "(DroneAnalytics not available or no events)"
	@echo "=== Stopping E2E environment ==="
	-$(E2E_COMPOSE) --profile $(E2E_PROFILE) down -v 2>/dev/null
	@echo "=== Done ==="

# ---------------------------------------------------------------------------
# E2E MQTT: scenario over MQTT transport.
#
# Поднимает оба брокера (Kafka + Mosquitto): Kafka обязателен для Agregator
# (Go, kafka-first); Mosquitto — основной транспорт для Python/Java систем.
# Agregator включается в режим OPERATOR_TRANSPORT=both через prepare_multi.py
# при E2E_BROKER=mqtt, чтобы operator.* дублировались в MQTT.
# Warmup e2e_warmup.sh (создание Kafka-топиков) оставляем — Agregator всё ещё
# читает заказы из Kafka.
# ---------------------------------------------------------------------------

e2e-mqtt-up:
	@echo "=== Generating multi-system compose (E2E_BROKER=mqtt) ==="
	@$(LOAD_ENV) && E2E_BROKER=mqtt E2E_ANALYTICS=1 PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run python scripts/prepare_multi.py \
		--systems $(E2E_SYSTEMS_MQTT) --output $(E2E_OUTPUT)
	@echo "ANALYTICS_URL=http://analytics-backend:8080" >> $(E2E_OUTPUT)/.env
	@echo "ANALYTICS_API_KEY=test-api-key-e2e-12345" >> $(E2E_OUTPUT)/.env
	@echo "ANALYTICS_PORT=8090" >> $(E2E_OUTPUT)/.env
	@echo "DELIVERY_DRONE_HEALTH_PORT=8095" >> $(E2E_OUTPUT)/.env
	@echo "DELIVERYDRON_ROOT=systems/drones" >> $(E2E_OUTPUT)/.env
	@echo "AGRODRON_GATEWAY_HOST_PORT=18081" >> $(E2E_OUTPUT)/.env
	@echo "SYSTEM_MONITOR_HOST_PORT=18090" >> $(E2E_OUTPUT)/.env
	@echo "BROKER_TYPE=mqtt" >> $(E2E_OUTPUT)/.env
	@$(LOAD_ENV) && echo "BROKER_USER=$${ADMIN_USER:-admin}" >> $(E2E_OUTPUT)/.env
	@$(LOAD_ENV) && echo "BROKER_PASSWORD=$${ADMIN_PASSWORD:-admin_secret_123}" >> $(E2E_OUTPUT)/.env
	@echo "=== Starting E2E environment (Kafka + MQTT profiles) ==="
	$(E2E_COMPOSE) --profile kafka --profile mqtt up -d --build
	@echo "=== Waiting for Agregator (8081) ==="
	@for i in $$(seq 1 60); do curl -sf http://localhost:8081/health >/dev/null 2>&1 && echo "Agregator is up" && break; [ $$i -eq 60 ] && echo "WARNING: Agregator did not respond after 300s" || sleep 5; done
	@echo "=== Waiting for Regulator (8088) ==="
	@for i in $$(seq 1 30); do curl -sf http://localhost:8088/health >/dev/null 2>&1 && echo "Regulator is up" && break; [ $$i -eq 30 ] && echo "WARNING: Regulator did not respond after 150s" || sleep 5; done
	@echo "=== Waiting for DroneAnalytics (8090) ==="
	@for i in $$(seq 1 60); do curl -sf http://localhost:8090/ >/dev/null 2>&1 && echo "DroneAnalytics is up" && break; [ $$i -eq 60 ] && echo "WARNING: DroneAnalytics did not respond after 300s" || sleep 5; done
	@$(LOAD_ENV) && bash scripts/e2e_warmup.sh
	@echo "=== Warming up consumer groups ($(E2E_WARMUP_SECONDS)s) ==="
	@sleep $(E2E_WARMUP_SECONDS)
	@echo "=== E2E MQTT environment is up ==="

e2e-mqtt-test:
	@echo "=== Running E2E tests (MQTT transport, same suite as e2e-test) ==="
	@$(LOAD_ENV) && BROKER_TYPE=mqtt MQTT_BROKER=localhost MQTT_PORT=1883 \
		PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest tests/e2e/test_e2e_scenario.py -v -s \
		--tb=short 2>&1 || (echo "E2E MQTT tests failed"; exit 1)

e2e-mqtt-down:
	@echo "=== Stopping E2E MQTT environment ==="
	-$(E2E_COMPOSE) --profile kafka --profile mqtt down -v 2>/dev/null
	@echo "=== E2E MQTT environment stopped ==="

e2e-mqtt: e2e-mqtt-up e2e-mqtt-test e2e-logs e2e-mqtt-down

# --- Jenkins (JCasC) ---

$(JENKINS_DIR)/.env:
	@cp $(JENKINS_DIR)/.env.example $@
	@echo "Created $@ from .env.example — отредактируй пароль/брэнч и перезапусти 'make jenkins-up'."

jenkins-up: $(JENKINS_DIR)/.env
	$(JENKINS_COMPOSE) up -d --build
	@PORT=$$(grep '^JENKINS_HTTP_PORT=' $(JENKINS_DIR)/.env | cut -d= -f2); \
	echo "Jenkins стартует на http://localhost:$${PORT:-8080}"
	@echo "Применение JCasC (job definitions)..."
	@sleep 15
	@$(MAKE) jenkins-apply-jobs || echo "WARN: jenkins-apply-jobs не выполнен — подождите и запустите make jenkins-apply-jobs"

jenkins-down:
	-$(JENKINS_COMPOSE) down

jenkins-restart: jenkins-down
	@$(MAKE) jenkins-up

jenkins-logs:
	$(JENKINS_COMPOSE) logs -f --tail=200

jenkins-ps:
	$(JENKINS_COMPOSE) ps

jenkins-preflight:
	@bash scripts/check_jenkins_env.sh
	@bash scripts/check_jenkins_submodule_pins.sh

jenkins-reload-casc: jenkins-apply-jobs

jenkins-apply-jobs: jenkins-preflight
	@bash scripts/jenkins_apply_casc.sh

jenkins-jobs-verify:
	@bash scripts/jenkins_apply_casc.sh --verify-only

jenkins-build-unit:
	@$(JENKINS_DIR)/build.sh drone-unit $(if $(WAIT),--wait,)

jenkins-build-integration:
	@$(JENKINS_DIR)/build.sh drone-integration $(if $(WAIT),--wait,)

jenkins-build-e2e:
	@$(JENKINS_DIR)/build.sh drone-e2e $(if $(WAIT),--wait,)

jenkins-build-agrodron-security-monitor:
	@$(JENKINS_DIR)/build.sh drone-agrodron-security-monitor $(if $(WAIT),--wait,)

jenkins-build-dummy-fabric-unit:
	@$(JENKINS_DIR)/build.sh drone-dummy-fabric-unit $(if $(WAIT),--wait,)

jenkins-build-phase0-smoke:
	@$(JENKINS_DIR)/build.sh drone-phase0-smoke $(if $(WAIT),--wait,)
