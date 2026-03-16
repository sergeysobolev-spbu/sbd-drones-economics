# Makefile для системы Эксплуатант

.PHONY: help test test-unit test-integration lint format clean docker-build docker-run

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

help: ## Показать справку
	@echo "Доступные команды:"
	@echo "  make test           - Запустить все тесты"
	@echo "  make test-unit      - Запустить юнит-тесты"
	@echo "  make test-integration - Запустить интеграционные тесты"
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
	$(PYTEST) $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term

test-unit: ## Запустить юнит-тесты
	$(PYTEST) $(TEST_DIR)/unit/test_security_monitor.py -v
	$(PYTEST) $(TEST_DIR)/unit/test_fleet_manager.py -v

test-integration: ## Запустить интеграционные тесты
	$(PYTEST) $(TEST_DIR)/integration/test_integration.py -v
	$(PYTEST) $(TEST_DIR)/integration/test_uas_purchase_integration.py -v

test-security: ## Запустить тесты безопасности
	$(PYTEST) $(TEST_DIR)/unit/test_security_monitor.py -v -k "security"

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
	docker-compose -f docker-compose.yml up -d

docker-stop: ## Остановить систему в Docker
	docker-compose -f docker-compose.yml down

docker-logs: ## Показать логи Docker контейнеров
	docker-compose -f docker-compose.yml logs -f

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