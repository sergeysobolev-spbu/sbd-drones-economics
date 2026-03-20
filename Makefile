.PHONY: help init unit-test integration-test e2e-test tests docker-up docker-down docker-logs docker-ps docker-clean

DOCKER_COMPOSE = docker compose -f docker/docker-compose.yml --env-file docker/.env
LOAD_ENV = set -a && . docker/.env && set +a
PIPENV_PIPFILE = config/Pipfile
PYTEST_CONFIG = config/pyproject.toml

help:
	@echo "make init              - Установить pipenv и зависимости"
	@echo "make tests-unit        - Unit тесты (SDK + broker + standalone компоненты)"
	@echo "make tests-integration  - Интеграционные тесты (operator, wrapper)"
	@echo "make tests-e2e           - Сквозные testы (docker shell сценарии)"
	@echo "make tests             - Все тесты"
	@echo "make docker-up         - Запустить инфраструктуру брокера"
	@echo "make docker-down       - Остановить"
	@echo "make docker-logs       - Логи"
	@echo "make docker-ps         - Статус"
	@echo "make docker-clean      - Очистка"

init:
	@command -v pipenv >/dev/null 2>&1 || pip install pipenv
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv install --dev

tests-unit:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/unit/ \
		components/dummy_component/tests/ \
		-v

tests-integration: tests-unit
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/integration/ \
		-v

tests-e2e: tests-unit
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/e2e/ \
		-v

tests: tests-unit tests-integration tests-e2e

docker-up:
	@test -f docker/.env || cp docker/example.env docker/.env
	@profile=$${BROKER_TYPE:-$$(grep '^BROKER_TYPE=' docker/.env 2>/dev/null | cut -d= -f2)}; \
	profile=$${profile:-kafka}; \
	$(DOCKER_COMPOSE) --profile $$profile up -d

docker-down:
	-$(DOCKER_COMPOSE) --profile kafka down 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down 2>/dev/null

docker-logs:
	$(DOCKER_COMPOSE) --profile $$(grep BROKER_TYPE docker/.env | cut -d= -f2) logs -f

docker-ps:
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

docker-clean:
	-$(DOCKER_COMPOSE) --profile kafka down -v --rmi local 2>/dev/null
	-$(DOCKER_COMPOSE) --profile mqtt down -v --rmi local 2>/dev/null
