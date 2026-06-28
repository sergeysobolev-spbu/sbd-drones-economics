# Mission Planner Component Makefile

COMPONENT_NAME = mission_planner
COMPONENT_ID = mission-planner-001
DOCKER_IMAGE = operator-mission-planner
DOCKER_TAG = latest

# Python settings
PYTHON = python3
PIP = pip3
PYTEST = pytest

# Paths
SRC_DIR = src
TEST_DIR = tests
DOCKER_DIR = docker

# Environment
export PYTHONPATH := $(shell cd ../../../.. && pwd):$(PYTHONPATH)
export COMPONENT_ID := $(COMPONENT_ID)
export BROKER_TYPE ?= mqtt
export BROKER_HOST ?= localhost
export BROKER_PORT ?= 1883

.PHONY: help
help:
	@echo "Mission Planner Component Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install       - Install dependencies"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests"
	@echo "  test-module   - Run module tests"
	@echo "  test-integration - Run integration tests"
	@echo "  lint          - Run linting"
	@echo "  format        - Format code"
	@echo "  run           - Run the component locally"
	@echo "  run-dev       - Run in development mode with auto-reload"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container"
	@echo "  docker-push   - Push Docker image"
	@echo "  clean         - Clean generated files"

.PHONY: install
install:
	@echo "Installing dependencies..."
	cd ../../../.. && $(PIP) install -r systems/operator/requirements.txt

.PHONY: test
test: test-unit test-module test-integration

.PHONY: test-unit
test-unit:
	@echo "Running unit tests..."
	cd ../../../.. && $(PYTEST) systems/operator/src/mission_planner/tests/unit -v -s

.PHONY: test-module
test-module:
	@echo "Running module tests..."
	cd ../../../.. && $(PYTEST) systems/operator/src/mission_planner/tests/module -v -s

.PHONY: test-integration
test-integration:
	@echo "Running integration tests..."
	cd ../../../.. && $(PYTEST) systems/operator/src/mission_planner/tests/integration -v -s

.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage..."
	cd ../../../.. && $(PYTEST) systems/operator/src/mission_planner/tests \
		--cov=systems/operator/src/mission_planner/src \
		--cov-report=html:systems/operator/src/mission_planner/htmlcov \
		--cov-report=term

.PHONY: lint
lint:
	@echo "Running linting..."
	cd ../../../.. && flake8 systems/operator/src/mission_planner/src \
		--max-line-length=100 \
		--exclude=__pycache__
	cd ../../../.. && pylint systems/operator/src/mission_planner/src \
		--max-line-length=100 \
		--disable=C0111,R0903

.PHONY: format
format:
	@echo "Formatting code..."
	cd ../../../.. && black systems/operator/src/mission_planner/src --line-length=100
	cd ../../../.. && isort systems/operator/src/mission_planner/src

.PHONY: type-check
type-check:
	@echo "Running type checking..."
	cd ../../../.. && mypy systems/operator/src/mission_planner/src --ignore-missing-imports

.PHONY: run
run:
	@echo "Running Mission Planner component..."
	cd ../../../.. && $(PYTHON) -m systems.operator.src.mission_planner

.PHONY: run-dev
run-dev:
	@echo "Running Mission Planner in development mode..."
	cd ../../../.. && $(PYTHON) -m systems.operator.src.mission_planner

.PHONY: docker-build
docker-build:
	@echo "Building Docker image..."
	docker build -f $(DOCKER_DIR)/Dockerfile -t $(DOCKER_IMAGE):$(DOCKER_TAG) ../../../..

.PHONY: docker-run
docker-run:
	@echo "Running Docker container..."
	docker run --rm -it \
		--name $(COMPONENT_NAME) \
		-e COMPONENT_ID=$(COMPONENT_ID) \
		-e BROKER_TYPE=$(BROKER_TYPE) \
		-e BROKER_HOST=$(BROKER_HOST) \
		-e BROKER_PORT=$(BROKER_PORT) \
		-e SYSTEM_ID=operator-001 \
		-e MAX_CONCURRENT_MISSIONS=10 \
		-e MISSION_RETENTION_DAYS=90 \
		-e ENABLE_ROUTE_OPTIMIZATION=true \
		--network host \
		$(DOCKER_IMAGE):$(DOCKER_TAG)

.PHONY: docker-push
docker-push:
	@echo "Pushing Docker image..."
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)

.PHONY: clean
clean:
	@echo "Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

.PHONY: logs
logs:
	@echo "Showing component logs..."
	docker logs -f $(COMPONENT_NAME)

.PHONY: shell
shell:
	@echo "Opening shell in container..."
	docker exec -it $(COMPONENT_NAME) /bin/bash

.PHONY: debug
debug:
	@echo "Running with debug logging..."
	cd ../../../.. && LOG_LEVEL=DEBUG $(PYTHON) -m systems.operator.src.mission_planner

.PHONY: validate
validate: lint type-check test
	@echo "Validation complete!"

.PHONY: dev-setup
dev-setup: install
	@echo "Setting up development environment..."
	@echo "Installing development tools..."
	$(PIP) install black isort flake8 pylint mypy pytest-cov

.PHONY: mission-demo
mission-demo:
	@echo "Running mission planning demo..."
	cd ../../../.. && $(PYTHON) -m systems.operator.notebooks.mission_demo