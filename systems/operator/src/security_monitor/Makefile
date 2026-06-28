# Makefile для компонента Security Monitor

COMPONENT_NAME = security_monitor
COMPONENT_ID ?= security-monitor-001
DOCKER_IMAGE = operator-$(COMPONENT_NAME):latest
DOCKER_REGISTRY ?= localhost:5000

# Цвета для вывода
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: help
help: ## Показать справку
	@echo "$(GREEN)Security Monitor Component Makefile$(NC)"
	@echo "$(YELLOW)Доступ��ые команды:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Настройка окружения разработки
	@echo "$(YELLOW)Настройка окружения для $(COMPONENT_NAME)...$(NC)"
	cd ../.. && pipenv install --dev
	@echo "$(GREEN)Окружение настроено!$(NC)"

.PHONY: test
test: test-unit test-module test-integration ## Запуск всех тестов

.PHONY: test-unit
test-unit: ## Запуск модульных тестов
	@echo "$(YELLOW)Запус�� модульных тестов...$(NC)"
	cd ../.. && pipenv run pytest src/$(COMPONENT_NAME)/tests/unit -v --cov=src/$(COMPONENT_NAME)/src --cov-report=term-missing

.PHONY: test-module
test-module: ## Запуск тестов модулей
	@echo "$(YELLOW)Запуск тестов модулей...$(NC)"
	cd ../.. && pipenv run pytest src/$(COMPONENT_NAME)/tests/module -v

.PHONY: test-integration
test-integration: ## Запуск интеграционных тестов
	@echo "$(YELLOW)Запуск интеграционных тестов...$(NC)"
	cd ../.. && pipenv run pytest src/$(COMPONENT_NAME)/tests/integration -v

.PHONY: lint
lint: ## Проверка кода линтерами
	@echo "$(YELLOW)Проверка кода...$(NC)"
	cd ../.. && pipenv run flake8 src/$(COMPONENT_NAME)/src
	cd ../.. && pipenv run mypy src/$(COMPONENT_NAME)/src --ignore-missing-imports
	cd ../.. && pipenv run black --check src/$(COMPONENT_NAME)/src
	@echo "$(GREEN)Проверка завершена!$(NC)"

.PHONY: format
format: ## Форматирование кода
	@echo "$(YELLOW)Форматирование кода...$(NC)"
	cd ../.. && pipenv run black src/$(COMPONENT_NAME)/src
	cd ../.. && pipenv run isort src/$(COMPONENT_NAME)/src
	@echo "$(GREEN)Форматирование завершено!$(NC)"

.PHONY: run
run: ## Запуск компонента локально
	@echo "$(YELLOW)Запуск $(COMPONENT_NAME)...$(NC)"
	cd ../.. && pipenv run python -m src.$(COMPONENT_NAME)

.PHONY: run-dev
run-dev: ## Запуск компонента в режиме разработки
	@echo "$(YELLOW)Запуск $(COMPONENT_NAME) в режиме разработки...$(NC)"
	cd ../.. && COMPONENT_ID=$(COMPONENT_ID) \
		BROKER_TYPE=mqtt \
		BROKER_HOST=localhost \
		BROKER_PORT=1883 \
		LOG_LEVEL=DEBUG \
		ENABLE_NOTIFICATIONS=true \
		pipenv run python -m src.$(COMPONENT_NAME)

.PHONY: docker-build
docker-build: ## Сборка Docker образа
	@echo "$(YELLOW)Сборка Docker образа...$(NC)"
	docker build -f docker/Dockerfile -t $(DOCKER_IMAGE) ../..
	@echo "$(GREEN)Образ собран: $(DOCKER_IMAGE)$(NC)"

.PHONY: docker-run
docker-run: docker-build ## Запуск компонента в Docker
	@echo "$(YELLOW)Запуск контейнера...$(NC)"
	docker run --rm \
		--name $(COMPONENT_NAME) \
		--network operator-network \
		-e COMPONENT_ID=$(COMPONENT_ID) \
		-e BROKER_TYPE=mqtt \
		-e BROKER_HOST=mqtt-broker \
		-e BROKER_PORT=1883 \
		$(DOCKER_IMAGE)

.PHONY: docker-push
docker-push: docker-build ## Отправка образа в реестр
	@echo "$(YELLOW)Отправка образа в реестр...$(NC)"
	docker tag $(DOCKER_IMAGE) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE)
	@echo "$(GREEN)Образ отправлен!$(NC)"

.PHONY: docker-health
docker-health: ## Проверка здоровья контейнера
	@echo "$(YELLOW)Проверка здоровья контейнера...$(NC)"
	@docker exec $(COMPONENT_NAME) curl -f http://localhost:8080/health || echo "$(RED)Контейнер не отвечает$(NC)"

.PHONY: clean
clean: ## Очистка временных файлов
	@echo "$(YELLOW)Очистка временных файлов...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	@echo "$(GREEN)Очистка завершена!$(NC)"

.PHONY: security-check
security-check: ## Проверка безопасности
	@echo "$(YELLOW)Проверка безопасности...$(NC)"
	cd ../.. && pipenv run bandit -r src/$(COMPONENT_NAME)/src -ll
	cd ../.. && pipenv run safety check
	@echo "$(GREEN)Проверка безопасности завершена!$(NC)"

.PHONY: metrics
metrics: ## Показать метрики компонента
	@echo "$(YELLOW)Метрики компонента $(COMPONENT_NAME):$(NC)"
	@echo "Количество файлов Python: $$(find src -name "*.py" | wc -l)"
	@echo "Строк кода: $$(find src -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $$1}')"
	@echo "Количество тестов: $$(find tests -name "test_*.py" -exec grep -E "def test_|async def test_" {} + | wc -l)"
	@echo "Покрытие кода: $$(cd ../.. && pipenv run pytest src/$(COMPONENT_NAME)/tests/unit --cov=src/$(COMPONENT_NAME)/src --cov-report=term | grep TOTAL | awk '{print $$4}')"

.PHONY: docs
docs: ## Генерация документации
	@echo "$(YELLOW)Генерация документации...$(NC)"
	cd ../.. && pipenv run pdoc --html --output-dir src/$(COMPONENT_NAME)/docs/api src/$(COMPONENT_NAME)/src
	@echo "$(GREEN)Документация сгенерирована в docs/api$(NC)"

.PHONY: validate-policies
validate-policies: ## Валидация политик безопасности
	@echo "$(YELLOW)Валидация политик безопасности...$(NC)"
	cd ../.. && pipenv run python -m src.$(COMPONENT_NAME).tools.validate_policies
	@echo "$(GREEN)Политики валидны!$(NC)"

.PHONY: export-audit
export-audit: ## Экспорт журнала аудита
	@echo "$(YELLOW)Экспорт журнала аудита...$(NC)"
	cd ../.. && pipenv run python -m src.$(COMPONENT_NAME).tools.export_audit --output audit_export.json
	@echo "$(GREEN)Аудит экспортирован в audit_export.json$(NC)"

# Специальные цели для CI/CD
.PHONY: ci-test
ci-test: lint test security-check ## Запуск тестов для CI

.PHONY: ci-build
ci-build: docker-build docker-push ## Сборка для CI