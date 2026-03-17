# Makefile для системы Эксплуатант

.PHONY: help test test-unit test-integration test-integration-local lint format clean docker-build docker-run

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
	@echo "  make test-security  - Запустить тесты безопасности"
	@echo "  make lint           - Проверить код линтерами"
	@echo "  make format         - Отформатировать код"
	@echo "  make clean          - Очистить временные файлы"
	@echo "  make docker-build   - Собрать Docker образ"
	@echo "  make docker-run     - Запустить систему в Docker"
	@echo "  make install-deps   - Установить зависимости"

install-deps: ## Установить зависимости
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-cov pytest-mock
	$(PIP) install black flake8 mypy

test: ## Запустить все тесты
	$(PYTEST) $(TEST_DIR) $(SRC_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term

test-unit: ## Запустить юнит-тесты
	$(PYTEST) \
		$(SRC_DIR)/security_monitor/tests/unit \
		$(SRC_DIR)/fleet_manager/tests/unit \
		$(SRC_DIR)/mission_planner/tests/unit \
		$(SRC_DIR)/business_logic/tests/unit \
		$(SRC_DIR)/operator_clients/tests/unit \
		-v

test-integration-local: ## Запустить интеграционные тесты (локально)
	$(PYTEST) $(TEST_DIR)/integration/test_integration.py -v --no-cov
	$(PYTEST) $(TEST_DIR)/integration/test_uas_purchase_integration.py -v --no-cov

test-integration: ## Запустить интеграционные тесты (docker-compose + healthcheck)
	@trap '$(COMPOSE) down -v --remove-orphans' EXIT; \
	$(COMPOSE) up -d --build; \
	echo "Ожидание healthcheck контейнеров..."; \
	for s in operator-kafka operator-security-monitor operator-fleet-manager operator-mission-planner operator-business-logic operator-system; do \
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

test-security: ## Запустить тесты безопасности
	$(PYTEST) $(SRC_DIR)/security_monitor/tests/unit -v -k "security"

test-coverage: ## Запустить тесты с отчётом о покрытии
	$(PYTEST) $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing
	@echo "Отчёт о покрытии сохранён в htmlcov/index.html"

lint: ## Проверить код линтерами
	$(FLAKE8) $(SRC_DIR) --max-line-length=120 --exclude=__pycache__
	$(MYPY) $(SRC_DIR) --ignore-missing-imports

format: ## Отформатировать код
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
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) -f docker/Dockerfile .

docker-run: ## Запустить систему в Docker
	$(COMPOSE) up -d

docker-stop: ## Остановить систему в Docker
	$(COMPOSE) down

docker-logs: ## Показать логи Docker контейнеров
	$(COMPOSE) logs -f

# Специальные цели для демонстрации

demo-order-flow: ## Демонстрация полного цикла обработки заказа
	@echo "Запуск демонстрации обработки заказа..."
	$(PYTHON) -m systems.operator.demos.order_flow_demo

demo-security: ## Демонстрация работы политик безопасности
	@echo "Запуск демонстрации политик безопасности..."
	$(PYTHON) -m systems.operator.demos.security_demo

# Цели для разработки

dev-run: ## Запустить систему в режиме разработки
	$(PYTHON) -m systems.operator.src.operator_system

dev-monitor: ## Запустить монитор безопасности отдельно
	$(PYTHON) -m systems.operator.src.security_monitor

# Проверка качества кода

check-security: ## Проверить код на уязвимости
	bandit -r $(SRC_DIR) -f json -o security-report.json
	@echo "Отчёт о безопасности сохранён в security-report.json"

check-complexity: ## Проверить цикломатическую сложность
	radon cc $(SRC_DIR) -a -nb

# Документация

docs: ## Сгенерировать документацию
	cd docs && make html
	@echo "Документация сгенерирована в docs/_build/html/"

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