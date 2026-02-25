.PHONY: help init unit-test tests docker-up docker-down docker-logs docker-ps docker-clean

DOCKER_COMPOSE = docker compose -f docker/docker-compose.yml --env-file docker/.env
LOAD_ENV = set -a && . docker/.env && set +a
PIPENV_PIPFILE = config/Pipfile
PYTEST_CONFIG = config/pyproject.toml

help:
	@echo "make init              - Установить pipenv и зависимости"
	@echo "make unit-test         - Unit тесты (SDK + broker + standalone компоненты)"
	@echo "make tests             - Все тесты"
	@echo "make docker-up         - Запустить инфраструктуру брокера"
	@echo "make docker-down       - Остановить"
	@echo "make docker-logs       - Логи"
	@echo "make docker-ps         - Статус"
	@echo "make docker-clean      - Очистка"

init:
	@command -v pipenv >/dev/null 2>&1 || pip install pipenv
	PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv install --dev

unit-test:
	@PIPENV_PIPFILE=$(PIPENV_PIPFILE) pipenv run pytest -c $(PYTEST_CONFIG) \
		tests/unit/ \
		components/dummy_component/tests/ \
		-v

tests: unit-test

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
