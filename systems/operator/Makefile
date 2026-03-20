# Makefile для системы Эксплуатант

.PHONY: help ensure-venv install-deps test test-unit test-integration test-integration-local test-integration-kafka \
	test-shell test-shell-mqtt test-shell-kafka up-mqtt down-mqtt up-kafka down-kafka lint typecheck format clean \
	docker-build docker-run docker-stop docker-logs logs demo-order-flow demo-security dev-run dev-monitor \
	check-security check-complexity docs metrics

# Нужен bash для `pipefail` и `set -u`
SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c

# Переменные
PYTHON := pipenv run python3
PIP := pipenv run pip3
PYTEST := pipenv run pytest
BLACK := pipenv run black
FLAKE8 := pipenv run flake8
MYPY := pipenv run mypy

# Пути
SRC_DIR := src
TEST_DIR := tests
DOCKER_IMAGE := operator-system
DOCKER_TAG := latest
COMPOSE := docker compose -f docker-compose.yml

help: ## Показать справку
	@echo "Доступные команды:"
	@echo "  make test           - Запустить все тесты"
	@echo "  make test-unit      - Запустить юнит-тесты"
	@echo "  make test-integration-local - Запустить интеграционные тесты (локально, без docker)"
	@echo "  make test-integration - Запустить интеграционные тесты (docker-compose + healthcheck)"
	@echo "  make test-shell     - Запустить shell интеграционные проверки (требует запущенный docker-compose)"
	@echo "  make test-shell-mqtt - Запустить shell проверки через Mosquitto (docker-compose.yml)"
	@echo "  make test-shell-kafka - Запустить shell проверки через Kafka (docker-compose.kafka.yml)"
	@echo "  make test-security  - Запустить тесты безопасности"
	@echo "  make lint           - Проверить код линтерами"
	@echo "  make typecheck      - Проверить типы (mypy)"
	@echo "  make format         - Отформатировать код"
	@echo "  make clean          - Очистить временные файлы"
	@echo "  make docker-build   - Собрать Docker образ"
	@echo "  make docker-run     - Запустить систему в Docker"
	@echo "  make up-mqtt        - Поднять стек Mosquitto/MQTT (docker-compose.yml)"
	@echo "  make down-mqtt      - Остановить стек Mosquitto/MQTT (docker-compose.yml)"
	@echo "  make up-kafka       - Поднять стек Kafka (docker-compose.kafka.yml) одной командой"
	@echo "  make down-kafka     - Остановить стек Kafka (docker-compose.kafka.yml)"
	@echo "  make install-deps   - Установить зависимости"

ensure-venv: ## Создать pipenv venv при необходимости
	@pipenv --venv >/dev/null 2>&1 || PIPENV_VENV_IN_PROJECT=1 pipenv install --dev

install-deps: ensure-venv ## Установить зависимости (runtime+dev) в venv
	$(PIP) install -r requirements.runtime.txt
	$(PIP) install -r requirements.dev.txt

test: ensure-venv ## Запустить все тесты
	$(PYTEST) $(TEST_DIR) $(SRC_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term

test-unit: ensure-venv ## Запустить юнит-тесты
	$(PYTEST) \
		$(SRC_DIR)/security_monitor/tests/unit \
		$(SRC_DIR)/fleet_manager/tests/unit \
		$(SRC_DIR)/mission_planner/tests/unit \
		$(SRC_DIR)/business_logic/tests/unit \
		$(SRC_DIR)/operator_clients/tests/unit \
		-v

test-integration-local: ensure-venv ## Запустить интеграционные тесты (локально)
	$(PYTEST) $(TEST_DIR)/integration/test_integration.py -v --no-cov
	$(PYTEST) $(TEST_DIR)/integration/test_uas_purchase_integration.py -v --no-cov

up-mqtt: ## Поднять стек Mosquitto/MQTT (docker-compose.yml)
	docker build -t operator-base:latest -f ../../systems/operator/docker/Dockerfile.base ../..; \
	$(COMPOSE) up -d --build --remove-orphans

down-mqtt: ## Остановить стек Mosquitto/MQTT (docker-compose.yml)
	$(COMPOSE) down -v --remove-orphans

up-kafka: ## Поднять стек Kafka (docker-compose.kafka.yml) одной командой
	docker build -t operator-base-kafka:latest -f ../../systems/operator/docker/Dockerfile.base ../.. --build-arg INSTALL_KAFKA=1; \
	docker compose -f docker-compose.kafka.yml up -d --build --remove-orphans

down-kafka: ## Остановить стек Kafka (docker-compose.kafka.yml)
	docker compose -f docker-compose.kafka.yml down -v --remove-orphans

test-integration: ensure-venv ## Запустить интеграционные тесты (docker-compose + healthcheck)
	@trap '$(MAKE) down-mqtt' EXIT; \
	$(MAKE) up-mqtt; \
	echo "Ожидание healthcheck контейнеров..."; \
	for s in operator-mosquitto operator-security-monitor operator-fleet-manager operator-mission-planner operator-business-logic operator-system; do \
		printf "  - %s: " "$$s"; \
		for i in $$(seq 1 60); do \
			health="$$(docker inspect -f '{{.State.Health.Status}}' $$s 2>/dev/null || true)"; \
			state="$$(docker inspect -f '{{.State.Status}}' $$s 2>/dev/null || true)"; \
			status="$${health:-$$state}"; \
			if [ "$$health" = "healthy" ] || [ "$$state" = "running" ]; then echo "$$status"; break; fi; \
			sleep 2; \
			if [ "$$i" -eq 60 ]; then echo "timeout (health=$$health state=$$state)"; $(COMPOSE) ps; exit 1; fi; \
		done; \
	done; \
	$(PYTEST) $(TEST_DIR)/integration -v --no-cov

test-integration-kafka: ensure-venv ## Интеграционные тесты через Kafka (docker-compose.kafka.yml)
	@trap '$(MAKE) down-kafka' EXIT; \
	$(MAKE) up-kafka; \
	echo "Ожидание healthcheck контейнеров..."; \
	for s in operator-kafka operator-security-monitor operator-fleet-manager operator-mission-planner operator-business-logic operator-system; do \
		printf "  - %s: " "$$s"; \
		for i in $$(seq 1 60); do \
			health="$$(docker inspect -f '{{.State.Health.Status}}' $$s 2>/dev/null || true)"; \
			state="$$(docker inspect -f '{{.State.Status}}' $$s 2>/dev/null || true)"; \
			status="$${health:-$$state}"; \
			if [ "$$health" = "healthy" ] || [ "$$state" = "running" ]; then echo "$$status"; break; fi; \
			sleep 2; \
			if [ "$$i" -eq 60 ]; then echo "timeout (health=$$health state=$$state)"; docker compose -f docker-compose.kafka.yml ps; exit 1; fi; \
		done; \
	done; \
	# Важно: в каталоге integration есть MQTT-тесты, они не должны выполняться
	# в Kafka-сценарии. Поэтому явно выбираем только нужные файлы.
	$(PYTEST) \
		$(TEST_DIR)/integration/test_integration.py \
		$(TEST_DIR)/integration/test_event_journal_analytics_adapter.py \
		$(TEST_DIR)/integration/test_uas_purchase_integration.py \
		-v --no-cov

test-shell: ## Запустить shell интеграционные проверки (MQTT default)
	@$(MAKE) test-shell-mqtt

test-shell-mqtt: up-mqtt ## Запустить shell проверки через Mosquitto (docker-compose.yml)
	@chmod +x $(TEST_DIR)/shell-mqtt/*.sh
	@COMPOSE_FILE=docker-compose.yml $(TEST_DIR)/shell-mqtt/run_all.sh

test-shell-kafka: up-kafka ## Запустить shell проверки через Kafka (docker-compose.kafka.yml)
	@chmod +x $(TEST_DIR)/shell/*.sh
	@COMPOSE_FILE=docker-compose.kafka.yml $(TEST_DIR)/shell/run_all.sh

test-security: ensure-venv ## Запустить тесты безопасности
	$(PYTEST) $(SRC_DIR)/security_monitor/tests/unit -v -k "security"

test-coverage: ensure-venv up-mqtt ## Запустить тесты с отчётом о покрытии
	$(PYTEST) $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing
	@echo "Отчёт о покрытии сохранён в htmlcov/index.html"

lint: ensure-venv ## Проверить код линтерами (style)
	$(FLAKE8) $(SRC_DIR) --max-line-length=120 --exclude=__pycache__

typecheck: ensure-venv ## Проверить типы (mypy)
	$(MYPY) $(SRC_DIR) --ignore-missing-imports

format: ensure-venv ## Отформатировать код
	$(BLACK) $(SRC_DIR) $(TEST_DIR) --line-length=120

clean: ## Очистить временные файлы
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

docker-build: ## Собрать Docker образ
	cd ../.. && docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) -f systems/operator/docker/Dockerfile .

docker-run: up-mqtt ## Запустить систему в Docker (MQTT default)
	@true

docker-stop: ## Остановить систему в Docker
	$(COMPOSE) down

docker-logs: ## Показать логи Docker контейнеров
	$(COMPOSE) logs -f

logs:
	$(COMPOSE) logs > docker-runtime-errors.log

# Специальные цели для демонстрации

demo-order-flow: ensure-venv ## Демонстрация полного цикла обработки заказа
	@echo "Запуск демонстрации обработки заказа..."
	PYTHONPATH=../.. $(PYTHON) -m systems.operator.demos.order_flow_demo

demo-security: ensure-venv ## Демонстрация работы политик безопасности
	@echo "Запуск демонстрации политик безопасности..."
	PYTHONPATH=../.. $(PYTHON) -m systems.operator.demos.security_demo

# Цели для разработки

dev-run: ensure-venv ## Запустить систему в режиме разработки
	cd ../../ && COMPONENT_TYPE=operator_system COMPONENT_ID=operator-01 $(PYTHON) -m systems.operator.src.run_component

dev-monitor: ensure-venv ## Запустить монитор безопасности отдельно
	COMPONENT_TYPE=security_monitor COMPONENT_ID=security-01 $(PYTHON) -m systems.operator.src.run_component

# Проверка качества кода

check-security: ## Проверить код на уязвимости
	pipenv run bandit -r $(SRC_DIR) -f json -o security-report.json
	@echo "Отчёт о безопасности сохранён в security-report.json"

check-complexity: ## Проверить цикломатическую сложность
	pipenv run radon cc $(SRC_DIR) -a -nb

# Документация

docs: ## Сгенерировать документацию
	cd docs && make html
	@echo "Документация сгенерирована в docs/_build/html/"

build-diagrams:
	$(foreach puml,$(wildcard docs/diagrams/*.puml),plantuml -tpng $(puml);)

# Метрики

metrics: ## Собрать метрики кода
	@echo "=== Метрики кода ==="
	@echo "Количество строк кода:"
	@find $(SRC_DIR) -name "*.py" | xargs wc -l | tail -1
	@echo ""
	@echo "Количество тестов:"
	@grep -r "def test_" $(TEST_DIR) | wc -l
	@echo ""
	@echo "Количество компонентов:"
	@ls $(SRC_DIR)/*.py | grep -v __init__ | wc -l