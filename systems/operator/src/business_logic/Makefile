# Makefile для компонента Business Logic

COMPONENT_NAME = business_logic
DOCKER_IMAGE = operator-$(COMPONENT_NAME)
DOCKER_TAG = latest

# Python
PYTHON = python3
PYTEST = pytest
PIPENV = pipenv

# Пути
SRC_DIR = src
TEST_DIR = tests
DOCS_DIR = docs

.PHONY: help
help:
	@echo "Доступные команды:"
	@echo "  make install       - Установить зависимости"
	@echo "  make test          - Запустить все тесты"
	@echo "  make test-unit     - Запустить unit тесты"
	@echo "  make test-module   - Запустить модульные тесты"
	@echo "  make test-integration - Запустить интеграционные тесты"
	@echo "  make lint          - Проверить код линтером"
	@echo "  make format        - Отформатировать код"
	@echo "  make run           - Запустить компонент локально"
	@echo "  make run-dev       - Запустить компонент в режиме разработки"
	@echo "  make docker-build  - Собрать Docker образ"
	@echo "  make docker-run    - Запустить компонент в Docker"
	@echo "  make docker-push   - Отправить образ в реестр"
	@echo "  make clean         - Очистить временные файлы"

.PHONY: install
install:
	@echo "Установка зависимостей..."
	cd ../../../.. && $(PIPENV) install --dev

.PHONY: test
test: test-unit test-module test-integration

.PHONY: test-unit
test-unit:
	@echo "Запуск unit тестов..."
	cd ../../../.. && $(PIPENV) run $(PYTEST) systems/operator/src/$(COMPONENT_NAME)/$(TEST_DIR)/unit -v

.PHONY: test-module
test-module:
	@echo "Запуск модульных тестов..."
	cd ../../../.. && $(PIPENV) run $(PYTEST) systems/operator/src/$(COMPONENT_NAME)/$(TEST_DIR)/module -v

.PHONY: test-integration
test-integration:
	@echo "Запуск интеграционных тестов..."
	cd ../../../.. && $(PIPENV) run $(PYTEST) systems/operator/src/$(COMPONENT_NAME)/$(TEST_DIR)/integration -v

.PHONY: test-coverage
test-coverage:
	@echo "Запуск тестов с покрытием..."
	cd ../../../.. && $(PIPENV) run $(PYTEST) systems/operator/src/$(COMPONENT_NAME)/$(TEST_DIR) \
		--cov=systems/operator/src/$(COMPONENT_NAME)/$(SRC_DIR) \
		--cov-report=html:systems/operator/src/$(COMPONENT_NAME)/htmlcov \
		--cov-report=term

.PHONY: lint
lint:
	@echo "Проверка кода..."
	cd ../../../.. && $(PIPENV) run flake8 systems/operator/src/$(COMPONENT_NAME)/$(SRC_DIR)
	cd ../../../.. && $(PIPENV) run mypy systems/operator/src/$(COMPONENT_NAME)/$(SRC_DIR)

.PHONY: format
format:
	@echo "Форматирование кода..."
	cd ../../../.. && $(PIPENV) run black systems/operator/src/$(COMPONENT_NAME)/$(SRC_DIR)
	cd ../../../.. && $(PIPENV) run isort systems/operator/src/$(COMPONENT_NAME)/$(SRC_DIR)

.PHONY: run
run:
	@echo "Запуск компонента..."
	cd ../../../.. && $(PIPENV) run $(PYTHON) -m systems.operator.src.$(COMPONENT_NAME)

.PHONY: run-dev
run-dev:
	@echo "Запуск компонента в режиме разработки..."
	cd ../../../.. && COMPONENT_ID=$(COMPONENT_NAME)-dev \
		BROKER_TYPE=mqtt \
		BROKER_HOST=localhost \
		BROKER_PORT=1883 \
		LOG_LEVEL=DEBUG \
		$(PIPENV) run $(PYTHON) -m systems.operator.src.$(COMPONENT_NAME)

.PHONY: docker-build
docker-build:
	@echo "Сборка Docker образа..."
	docker build -f docker/Dockerfile -t $(DOCKER_IMAGE):$(DOCKER_TAG) ../../../..

.PHONY: docker-run
docker-run:
	@echo "Запуск компонента в Docker..."
	docker run --rm \
		--name $(COMPONENT_NAME) \
		--network operator-network \
		-e COMPONENT_ID=$(COMPONENT_NAME)-001 \
		-e BROKER_TYPE=mqtt \
		-e BROKER_HOST=mqtt-broker \
		-e BROKER_PORT=1883 \
		$(DOCKER_IMAGE):$(DOCKER_TAG)

.PHONY: docker-push
docker-push:
	@echo "Отправка образа в реестр..."
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)

.PHONY: clean
clean:
	@echo "Очистка временных файлов..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

.PHONY: docs
docs:
	@echo "Генерация документации..."
	cd $(DOCS_DIR) && $(MAKE) all