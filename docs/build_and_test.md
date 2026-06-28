# Сборка, тесты и Jenkins локально

<!-- doc-meta: status=active version=1.2 updated=2026-06-28 -->

Руководство для нового окружения: зависимости, субмодули, Docker, автотесты и Jenkins (`ci/jenkins/`).

См. также: [jenkins.md](jenkins.md), [ports.md](ports.md), [integration-phase0-compose.md](integration-phase0-compose.md).

## Требования

- Git, **Docker Engine** и **Compose v2** (`docker compose`).
- **GNU Make**.
- **Python 3.12+** локально (для `pipenv` / `make init`) или опора только на образы Docker.
- Достаточно RAM и диска для E2E: десятки контейнеров (Kafka, системы, DroneAnalytics).

## Клонирование и субмодули

Без субмодулей каталоги `vendor/` и часть `systems/` будут пустыми или неполными.

```bash
git clone <url> sbd-drones-economics
cd sbd-drones-economics
git submodule update --init --recursive
```

Либо сразу: `git clone --recurse-submodules <url>`.

## Файл `docker/.env`

1. Скопируйте эталон: `cp docker/example.env docker/.env`.
2. При обновлении репозитория сравнивайте `docker/example.env` со своим `docker/.env` и добавляйте новые переменные вручную (в т.ч. блок `JENKINS_*`).

Файл `docker/.env` использует корневой `Makefile` для `make docker-up`, `make e2e-up` и т.д. Лишние ключи (например, только для Jenkins) не мешают `docker compose` брокера, если они не подставляются в YAML.

Переменная **`DOCKER_NETWORK`** задаёт имя общей сети (по умолчанию `drones_net`). Системные compose часто объявляют эту сеть как `external: true`; сеть должна существовать на хосте (`make init` создаёт её, либо `docker network create drones_net`).

## Инициализация Python-зависимостей

```bash
make init
```

Устанавливает `pipenv` при необходимости, ставит зависимости из `config/Pipfile` и создаёт сеть `drones_net` (если её ещё нет — при повторном запуске команда `docker network create` может завершиться ошибкой; это нормально).

## Команды тестов (Makefile)

| Цель | Назначение |
|------|------------|
| `make unit-test` | Лёгкие unit-тесты SDK и шаблонов |
| `make ci-unit-test` | Unit-тесты по всем `components/*/tests` и системам (`test_*unit*.py`) |
| `make ci-integration-test` | Интеграционные тесты систем (docker/pytest по Makefile систем) |
| `make ci-test` | `ci-unit-test` + `ci-integration-test` |
| `make phase0-smoke` | Smoke phase 0 (T14): structural checks в `tests/e2e/test_phase0_smoke.py` |
| `make ci-config-check` | `ports-check` + `phase0-smoke` (быстрый CI gate без Docker) |
| `make ports-check` | Реестр портов `config/e2e_ports.*.env` ↔ `docs/ports.md` |

### Ворота CI / профили тестов (gate table)

| Gate / профиль | Команда | Брокер | Системы (минимум) | Обязательные skip |
|----------------|---------|--------|-------------------|-------------------|
| PR-E1 unit+integration | `make ci-test` | per-system | agregator, uas_dev_company, … | `CI_*_EXCLUDE` субмодули |
| Full E2E (Codespace) | `make e2e-codespace` | Kafka | полный полигон | Analytics (`E2E_SKIP_ANALYTICS=1`) |
| Full E2E (local) | `make e2e-local` | Kafka | полный + Analytics | — |
| MQTT transport E2E | `make e2e-mqtt` | Kafka + MQTT | как e2e | — |
| **Phase 0 smoke (T14)** | `make phase0-smoke` | Kafka | Aggregator + Operator (planned T10) | infra skip если stack down |
| Smart contracts E2E | `make e2e-smart-contracts` | Kafka + Fabric | fabric profile | — |

Policy skip/xfail (E2E-2): mandatory business steps **не** должны быть `pytest.skip` на green gate; допустим `xfail` с issue до закрытия контракта (см. `test_phase0_smoke.py` TM-001).

Sprint autonomy (QA/DevOps): time-boxed спринты с E2E-целями не закрываются без `make e2e-codespace` green — см. [`sprint-autonomy-policy`](../../sbd-drones-economics-ai/docs/ai_dev_tasks.md#sprint-autonomy-policy).

### Исключения CI (`CI_UNIT_EXCLUDE` / `CI_INTEGRATION_EXCLUDE`)

Корневой `Makefile` пропускает субмодули с известным рассинхроном SDK, сломанным docker-up на чистом стенде или отсутствующими артефактами (например, `mosquitto.conf` в `SITL-module`). Список — в `Makefile` (`CI_UNIT_EXCLUDE`, `CI_INTEGRATION_EXCLUDE`). Gate PR-E1: `make ci-test` (с учётом исключений) и `make e2e-codespace`.

| `make e2e-up` | Генерация `.generated/e2e`, подъём полного стека E2E + ожидание health |
| `make e2e-test` | `pytest tests/e2e/` |
| `make e2e-down` | Остановка E2E-окружения |
| `make e2e` | `e2e-up` → `e2e-test` → логи → `e2e-down` |
| `make jenkins-up` | Jenkins в Docker (`ci/jenkins/`), JCasC, `jenkins-apply-jobs` |
| `make jenkins-apply-jobs` | JCasC reload + проверка job в UI |
| `make jenkins-build-unit WAIT=1` | Триггер job `drone-unit` и ожидание результата |
| `make jenkins-build-phase0-smoke WAIT=1` | Триггер job `drone-phase0-smoke` |

Локально без Jenkins: **`make e2e`** или **`make ci-test`**. Jenkins: **`make jenkins-up`**, затем job из [jenkins.md](jenkins.md).

Брокер: `make docker-up` (`docker/.env` из `docker/example.env`).

## Jenkins (JCasC)

Каноническая конфигурация — **`ci/jenkins/`** (не корневые `Dockerfile.jenkins`). Подробности: [jenkins.md](jenkins.md).

```bash
make jenkins-up
make jenkins-apply-jobs    # после правки casc.yaml
make ports-check           # local vs jenkins порты
make jenkins-build-unit WAIT=1
```

E2E из Jenkins использует `E2E_RUN_MODE=jenkins` и порты из `config/e2e_ports.jenkins.env` (не пересекаются с local).

## Docker и Jenkins: не «Docker-in-Docker»

Контроллер Jenkins и **агент** пайплайна монтируют **`/var/run/docker.sock`** хоста. Команды `docker` / `docker compose` внутри агента обращаются к **демону хоста**; контейнеры тестов — соседи Jenkins, а не вложенный Docker.

Классический **DinD** (отдельный `dockerd` внутри контейнера) здесь не используется.

## Образ Jenkins

Сборка и запуск — **`make jenkins-up`** (`ci/jenkins/Dockerfile`, образ `drones-jenkins:local`). Пайплайны используют docker-агент `python:3.11` или host-agent с `docker.sock` хоста.

Конфигурация UI и job — JCasC (`ci/jenkins/casc.yaml`). Переменные — `ci/jenkins/.env` (см. [jenkins.md](jenkins.md)).

## Чеклист пайплайна (Jenkins)

| Этап | Проверка |
|------|----------|
| Pre-flight | `docker info`; свободные порты; `docker/.env` синхронизирован с `example.env`; образ `JENKINS_AGENT_IMAGE` собран |
| Checkout | Успешный `git submodule update --init --recursive` |
| Init | `pipenv install --dev`; `docker --version`, `docker compose version`, `make --version` |
| Unit | `make ci-unit-test` |
| Integration | `make ci-integration-test`; при ошибках сети — `docker network ls` и наличие `drones_net` |
| E2E | Нет `ModuleNotFoundError: sdk.*` и циклов перезапуска `gcs_*` в логах compose; `make e2e-test` |
| Post | `make e2e-down`, `make docker-down`, `make -C systems/... docker-down` |

## Диагностика E2E и GCS

Просмотр логов E2E-compose (как в `Makefile`, переменная `E2E_COMPOSE`):

```bash
docker compose -f .generated/e2e/docker-compose.yml \
  -f tests/e2e/analytics-compose.yml \
  --env-file .generated/e2e/.env --profile kafka logs --tail=200
```

**Два дерева `sdk`:** код GCS импортирует модули `sdk.base_redis_store_component`, `sdk.wpl_generator`, `sdk.wpl_generator_2`, которые лежат в `vendor/DronePortGCS/sdk/`, тогда как в образ попадает корневой пакет `sdk/` монорепозитория. В Dockerfile сервисов GCS дополнительно копируются эти три файла в `/app/sdk/`. В `config/requirements.txt` добавлен пакет **`redis`** для Redis-компонентов GCS.

При падении сборки в Jenkins имеет смысл сохранять фрагмент вывода этой команды как артефакт.

## Очистка после сбоев

На хосте могут остаться контейнеры и тома:

```bash
docker ps -a
docker compose -f docker/docker-compose.yml --env-file docker/.env --profile kafka down
# при необходимости — аналогично для .generated/e2e
```

Не запускайте две тяжёлые E2E-сборки параллельно на одном хосте без разнесения портов и имён проектов.

## См. также

- [docker/README.md](../docker/README.md) — брокер, Kafka, переменные `docker/.env` и Jenkins
- [quick_start.md](quick_start.md) — быстрый старт и ссылка на этот документ
