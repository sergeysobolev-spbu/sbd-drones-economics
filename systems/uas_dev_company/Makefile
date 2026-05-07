.PHONY: help prepare diagrams diagrams-png unit-test integration-test tcb-test tcb-metrics tcb-metrics-full test-all-docker bus-adjacent-test drone-analytics-integration-test e2e-test tests docker-up docker-down docker-logs

PIPENV_PIPFILE = ../../config/Pipfile
PYTEST_CONFIG = ../../config/pyproject.toml
GENERATED = .generated
DOCKER_COMPOSE = docker compose -f $(GENERATED)/docker-compose.yml --env-file $(GENERATED)/.env
PYTHONPATH = ../../:src
# Выход скрипта оценки ДВБ (Задача 10/12): target_tcb, контейнеры, tcb_cost_task12 / estimated_tcb_cost_score
TCB_METRICS_OUT ?= docs/tcb_metrics.json
# Cobertura XML для сводного отчёта Задачи 13 (make tcb-test)
TCB_COVERAGE_XML ?= docs/tcb_coverage.xml

# Рендер PlantUML → PNG в docs/diagrams/ (рядом с .puml)
PLANTUML_DOCKER ?= plantuml/plantuml:latest
DIAGRAM_PUML = docs/diagrams/deployment_containers.puml docs/diagrams/sequence_local_sqlite.puml docs/diagrams/sequence_broker_proxy.puml docs/diagrams/sequence_scenario_certify_and_purchase.puml docs/diagrams/tcb_decomposition.puml docs/diagrams/readme_context.puml docs/diagrams/readme_functional_internal.puml docs/diagrams/readme_policy_trust_boundary.puml

help:
	@echo "make prepare          - Собрать docker-compose + .env из компонентов"
	@echo "make docker-up        - Запустить систему"
	@echo "make docker-down      - Остановить систему"
	@echo "make diagrams          - PNG из docs/diagrams/*.puml (PlantUML в Docker)"
	@echo "make tcb-test         - Тесты ДВБ + coverage ≥70%; Cobertura XML; пересчёт tcb_metrics; docs/tcb_summary_report.md"
	@echo "make tcb-metrics      - Пересчёт docs/tcb_metrics.json (target + изоляция контейнеров + стоимость ДВБ, Задача 12)"
	@echo "make tcb-metrics-full - То же + обновление baseline_tcb (редко: сменился состав baseline_paths)"
	@echo "make unit-test        - Unit тесты"
	@echo "make integration-test - Интеграционные тесты"
	@echo "make bus-adjacent-test - kafka+mosquitto up, pytest смежных систем по шине (UAS_ADJACENT_BUS_INTEGRATION)"
	@echo "make drone-analytics-integration-test - поднять DroneAnalytics+ES (docker), env, pytest центрального журнала (Задача 19)"
	@echo "make e2e-test          - Playwright по HTTP_PORT (compose должен быть запущен)"
	@echo "make tests             - Локальные Python-тесты (unit + integration)"

# Синоним для явного имени экспорта
diagrams-png: diagrams

diagrams: $(DIAGRAM_PUML)
	@echo "=== PlantUML → PNG ($(PLANTUML_DOCKER)) ==="
	@docker run --rm \
		-u $$(id -u):$$(id -g) \
		-v "$$(pwd)/docs/diagrams:/work:rw" \
		-w /work \
		-e JAVA_TOOL_OPTIONS=-Djava.awt.headless=true \
		$(PLANTUML_DOCKER) \
		-tpng -charset UTF-8 \
		deployment_containers.puml sequence_local_sqlite.puml sequence_broker_proxy.puml sequence_scenario_certify_and_purchase.puml tcb_decomposition.puml readme_context.puml readme_functional_internal.puml readme_policy_trust_boundary.puml *.puml
	@rm -rf docs/diagrams/'?' 2>/dev/null || true
	@echo "Готово: docs/diagrams/*.png"

prepare:
	@cd ../.. && PIPENV_PIPFILE=config/Pipfile pipenv run python scripts/prepare_system.py systems/uas_dev_company

docker-up: prepare
	@set -a && . $(GENERATED)/.env && set +a && \
		profiles="--profile $${BROKER_TYPE:-kafka}"; \
		$(DOCKER_COMPOSE) $$profiles up -d --build

docker-down:
	@set -a && . $(GENERATED)/.env && set +a && \
		profiles="--profile $${BROKER_TYPE:-kafka}"; \
		$(DOCKER_COMPOSE) $$profiles down 2>/dev/null || true

docker-logs:
	@set -a && . $(GENERATED)/.env && set +a && \
		profiles="--profile $${BROKER_TYPE:-kafka}"; \
		$(DOCKER_COMPOSE) $$profiles logs -f

unit-test:
	@PYTHONPATH=$(PYTHONPATH) PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/unit tests/module -v

# Сертификационный контур ДВБ: pytest-cov, затем метрики стоимости и сводный отчёт (Задача 13)
tcb-test:
	@PYTHONPATH=$(PYTHONPATH) PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/unit tests/module tests/integration -v \
		--cov=shared.tcb \
		--cov=shared.security_monitor \
		--cov=shared.security_policies \
		--cov=shared.component_base \
		--cov=shared.worker_runtime \
		--cov=shared.worker_deps \
		--cov=shared.external_adapters_factory \
		--cov=shared.analytics_ipc \
		--cov=shared.jwt_tokens \
		--cov=shared.models \
		--cov=shared.services \
		--cov=shared.topics \
		--cov=shared.storage \
		--cov=shared.integration_adapters \
		--cov=shared.bus_integration_adapters \
		--cov=gateway \
		--cov=user_management \
		--cov=firmware_ingestion \
		--cov=certification_service \
		--cov=drone_registry \
		--cov=purchase_service \
		--cov=audit_log \
		--cov=analytics_adapter \
		--cov-report=term-missing \
		--cov-report=xml:$(TCB_COVERAGE_XML) \
		--cov-fail-under=70 && \
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run bash -c 'PYTHONPATH=src python3 scripts/tcb_metrics.py --target --out $(TCB_METRICS_OUT)' && \
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run bash -c 'PYTHONPATH=src python3 scripts/tcb_summary_report.py --coverage $(TCB_COVERAGE_XML) --metrics $(TCB_METRICS_OUT) --out docs/tcb_summary_report.md'

# Оценка ДВБ и «стоимости» для отчёта: scripts/tcb_metrics.py (ключ tcb_cost_task12 → estimated_tcb_cost_score)
tcb-metrics:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run bash -c 'PYTHONPATH=src python scripts/tcb_metrics.py --target --out $(TCB_METRICS_OUT)'

tcb-metrics-full:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run bash -c 'PYTHONPATH=src python scripts/tcb_metrics.py --baseline --target --out $(TCB_METRICS_OUT)'

integration-test:
	@PYTHONPATH=$(PYTHONPATH) PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/integration -v

test-all-docker: docker-up
	@echo "Waiting for broker and components..."
	@sleep 45
	@set -a && . "$(GENERATED)/.env" 2>/dev/null && set +a && \
	export UAS_HTTP_INTEGRATION_BASE="$${UAS_HTTP_INTEGRATION_BASE:-http://127.0.0.1:$${HTTP_PORT:-8080}}" && \
	export UAS_ADJACENT_BUS_INTEGRATION=1 && \
	export UAS_ADJACENT_BROKER_TYPES="$${UAS_ADJACENT_BROKER_TYPES:-kafka}" && \
	export KAFKA_BOOTSTRAP_SERVERS="$${KAFKA_BOOTSTRAP_SERVERS:-127.0.0.1:$${KAFKA_PORT:-9092}}" && \
	export MQTT_BROKER="$${MQTT_BROKER:-127.0.0.1}" && \
	export MQTT_PORT="$${MQTT_PORT:-1883}" && \
	export BROKER_USER="$${BROKER_USER:-$${ADMIN_USER:-admin}}" && \
	export BROKER_PASSWORD="$${BROKER_PASSWORD:-$${ADMIN_PASSWORD:-admin123}}" && \
	PYTHONPATH=$(PYTHONPATH) PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) tests/integration -v
	-$(MAKE) docker-down

# Тесты Задачи 16: только брокер (kafka + mosquitto), без полного стека UAS
bus-adjacent-test: prepare
	@echo "=== Kafka + Mosquitto для pytest смежных систем (шина) ==="
	@set -a && . "$(GENERATED)/.env" 2>/dev/null && set +a && \
		profiles="--profile kafka --profile mqtt"; \
		$(DOCKER_COMPOSE) $$profiles up -d kafka mosquitto && \
		sleep 40 && \
		export UAS_ADJACENT_BUS_INTEGRATION=1 && \
		export UAS_ADJACENT_BROKER_TYPES="$${UAS_ADJACENT_BROKER_TYPES:-kafka,mqtt}" && \
		export KAFKA_BOOTSTRAP_SERVERS="$${KAFKA_BOOTSTRAP_SERVERS:-127.0.0.1:$${KAFKA_PORT:-9092}}" && \
		export MQTT_BROKER="$${MQTT_BROKER:-127.0.0.1}" && \
		export MQTT_PORT="$${MQTT_PORT:-1883}" && \
		export BROKER_USER="$${BROKER_USER:-$${ADMIN_USER:-admin}}" && \
		export BROKER_PASSWORD="$${BROKER_PASSWORD:-$${ADMIN_PASSWORD:-admin123}}" && \
		PYTHONPATH=$(PYTHONPATH) PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
			tests/integration/test_adjacent_systems_bus.py \
			tests/integration/test_analytics_adapter_ipc_bus.py -v && \
		$(DOCKER_COMPOSE) $$profiles stop kafka mosquitto 2>/dev/null || true

# Секреты один раз из каталога systems/DroneAnalytics: make secrets
# Не поднимать compose (только env + pytest), если стек уже запущен: DA_USE_EXISTING_STACK=1 make drone-analytics-integration-test
# Порты на хосте по умолчанию 28080 (backend) и 19200 (Elasticsearch), переопределение: make DA_BACKEND_HOST_PORT=18080 DA_ELASTIC_HOST_PORT=9200 drone-analytics-integration-test
DA_STACK := ../DroneAnalytics
DA_OVERRIDE_REL := ../uas_dev_company/docker-compose.drone-analytics-integration.override.yml
DA_BACKEND_HOST_PORT ?= 28080
DA_ELASTIC_HOST_PORT ?= 19200

drone-analytics-integration-test:
	@echo "=== DroneAnalytics (центральный журнал) + интеграционный pytest (Задача 19) ==="
	@if [ -z "$$DA_USE_EXISTING_STACK" ]; then \
		if [ ! -f "$(DA_STACK)/secrets/backend.yaml" ] || [ ! -f "$(DA_STACK)/secrets/proxy.crt" ]; then \
			echo "Секреты DroneAnalytics не найдены — выполняю make -C $(DA_STACK) secrets…"; \
			$(MAKE) -C "$(DA_STACK)" secrets; \
		fi; \
		echo "Запуск docker compose (DroneAnalytics + override портов для хоста)…"; \
		cd "$(DA_STACK)" && \
		DA_BACKEND_HOST_PORT="$(DA_BACKEND_HOST_PORT)" DA_ELASTIC_HOST_PORT="$(DA_ELASTIC_HOST_PORT)" \
			docker compose -f docker-compose.yaml -f "$(DA_OVERRIDE_REL)" -p uas-da-integration up -d --build; \
		echo "Ожидание backend :$(DA_BACKEND_HOST_PORT) и Elasticsearch :$(DA_ELASTIC_HOST_PORT)…"; \
		deadline=$$(( $$(date +%s) + 180 )); \
		while [ $$(date +%s) -lt $$deadline ]; do \
			curl -sf "http://127.0.0.1:$(DA_BACKEND_HOST_PORT)/" >/dev/null 2>&1 \
				&& curl -sf "http://127.0.0.1:$(DA_ELASTIC_HOST_PORT)/_cluster/health" >/dev/null 2>&1 \
				&& break; \
			sleep 2; \
		done; \
		curl -sf "http://127.0.0.1:$(DA_BACKEND_HOST_PORT)/" >/dev/null \
			|| { echo "Backend не отвечает на http://127.0.0.1:$(DA_BACKEND_HOST_PORT)/"; exit 1; }; \
		curl -sf "http://127.0.0.1:$(DA_ELASTIC_HOST_PORT)/_cluster/health" >/dev/null \
			|| { echo "Elasticsearch не отвечает на http://127.0.0.1:$(DA_ELASTIC_HOST_PORT)"; exit 1; }; \
	else \
		echo "DA_USE_EXISTING_STACK=1 — compose не поднимаем, задайте при необходимости DRONE_ANALYTICS_URL и ELASTIC_URL."; \
	fi
	@export UAS_DRONE_ANALYTICS_STACK_INTEGRATION=1 && \
	export UAS_DRONE_ANALYTICS_TRANSPORT=http && \
	export DRONE_ANALYTICS_ENABLED=true && \
	export DRONE_ANALYTICS_URL="$${DRONE_ANALYTICS_URL:-http://127.0.0.1:$(DA_BACKEND_HOST_PORT)}" && \
	export DRONE_ANALYTICS_API_KEY="$${DRONE_ANALYTICS_API_KEY:-change-me-api-key}" && \
	export ELASTIC_URL="$${ELASTIC_URL:-http://127.0.0.1:$(DA_ELASTIC_HOST_PORT)}" && \
	PYTHONPATH=$(PYTHONPATH) PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/integration/test_drone_analytics_central_journal.py -v

tests: unit-test integration-test

HTTP_PORT ?= 8080

e2e-test:
	@command -v node >/dev/null 2>&1 || { echo "node required for Playwright"; exit 1; }
	@cd web && npm install && npx playwright install chromium
	@echo "Ensure docker compose is running (nginx on port $(HTTP_PORT))"
	@set -a && HTTP_PORT="$(HTTP_PORT)" && . "$(GENERATED)/.env" 2>/dev/null; set +a; \
	cd web && \
		E2E_BASE_URL="$${E2E_BASE_URL:-http://127.0.0.1:$(HTTP_PORT)}" npm run test:e2e
