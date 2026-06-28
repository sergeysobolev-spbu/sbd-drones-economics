# Сборка, тесты и Jenkins локально

Руководство для нового окружения: зависимости, субмодули, Docker, полный набор автотестов (unit, integration, E2E) и запуск Jenkins в контейнере.

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


### Исключения CI (`CI_UNIT_EXCLUDE` / `CI_INTEGRATION_EXCLUDE`)

Корневой `Makefile` пропускает субмодули с известным рассинхроном SDK, сломанным docker-up на чистом стенде или отсутствующими артефактами (например, `mosquitto.conf` в `SITL-module`). Список — в `Makefile` (`CI_UNIT_EXCLUDE`, `CI_INTEGRATION_EXCLUDE`). Gate PR-E1: `make ci-test` (с учётом исключений) и `make e2e-codespace`.

| `make e2e-up` | Генерация `.generated/e2e`, подъём полного стека E2E + ожидание health |
| `make e2e-test` | `pytest tests/e2e/` |
| `make e2e-down` | Остановка E2E-окружения |
| `make e2e` | `e2e-up` → `e2e-test` → логи → `e2e-down` |
| `make jenkins-build` | Сборка `Dockerfile.jenkins` и `Dockerfile.jenkins-agent` (теги из `docker/.env`) |
| `make jenkins-up` | Запуск контроллера Jenkins в Docker (`jenkins_drones_home`, `docker.sock`, `--env-file docker/.env`) |
| `make jenkins-down` | Остановка и удаление контейнера (`JENKINS_CONTAINER_NAME`) |
| `make jenkins-deploy` | `jenkins-build` + `jenkins-up` |
| `make jenkins-e2e` | Сквозные тесты **в образе CI-агента** (скрипт `scripts/jenkins_agent_e2e.sh`: submodule, `pipenv`, `make e2e-up` / `e2e-test` / `e2e-down`, очистка как в `Jenkinsfile`) |
| `make jenkins-setup-e2e` | `jenkins-deploy`, затем `jenkins-e2e` — контроллер поднят, E2E прогнаны в том же окружении, что у worker Pipeline |

Локально без Jenkins: **`make e2e`** (на хосте с `pipenv` и Docker). Проверка «как на агенте Jenkins»: **`make jenkins-e2e`** (не требует запущенного UI Jenkins; образ и сокет совпадают с `Jenkinsfile`). Job Pipeline из SCM настраивается вручную в UI после `make jenkins-up`.

Брокер для локальной работы: `make docker-up` (нужен `docker/.env`, см. `docker/example.env`).

## Docker и Jenkins: не «Docker-in-Docker»

Контроллер Jenkins и **агент** пайплайна монтируют **`/var/run/docker.sock`** хоста. Команды `docker` / `docker compose` внутри агента обращаются к **демону хоста**; контейнеры тестов — соседи Jenkins, а не вложенный Docker.

Классический **DinD** (отдельный `dockerd` внутри контейнера) здесь не используется.

## Образы Jenkins

- **`Dockerfile.jenkins`** — образ **контроллера** (UI, очередь сборок): `jenkins/jenkins:lts` + Docker CLI + Compose v2 plugin, чтобы плагин Docker мог поднимать агентов.
- **`Dockerfile.jenkins-agent`** — образ **агента CI**: Python **3.12+**, `make`, `git`, `curl`, Docker CLI и Compose v2 (демон по-прежнему хостовый через socket).

Сборка агента (тег должен совпадать с `JENKINS_AGENT_IMAGE` в `docker/example.env`, по умолчанию `drones-jenkins-agent:local`):

```bash
docker build -f Dockerfile.jenkins-agent -t drones-jenkins-agent:local .
```

Проверки:

```bash
docker run --rm drones-jenkins-agent:local make --version
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock drones-jenkins-agent:local docker version
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock drones-jenkins-agent:local docker compose version
```

Сборка контроллера:

```bash
docker build -f Dockerfile.jenkins -t drones-jenkins:local .
```

### Переменные Jenkins в `docker/example.env`

| Переменная | Назначение |
|------------|------------|
| `JENKINS_CONTROLLER_IMAGE` | Тег образа контроллера (по умолчанию `drones-jenkins:local`) |
| `JENKINS_CONTAINER_NAME` | Имя контейнера контроллера для `make jenkins-up` / `jenkins-down` (по умолчанию `jenkins-drones`) |
| `JENKINS_HTTP_PORT` | Порт UI контроллера на хосте (например `8080`) |
| `JENKINS_AGENT_IMAGE` | Тег образа агента; тот же образ должен быть указан в корневом `Jenkinsfile` (через `env.JENKINS_AGENT_IMAGE` на контроллере или fallback в файле) |
| `JENKINS_PIPELINE_TIMEOUT_MINUTES` | Рекомендуемая длительность пайплайна; в Declarative `options { timeout }` задайте то же число вручную в `Jenkinsfile` при смене |
| `JENKINS_JAVA_OPTS` | Опционально, для JVM контроллера (передаётся при `docker run`, например `-e JENKINS_JAVA_OPTS=...`) |

На контроллере Jenkins переменная **`JENKINS_AGENT_IMAGE`** должна быть доступна процессу Jenkins (например через `--env-file docker/.env` при `docker run`, либо **Manage Jenkins → System → Global properties → Environment variables**). Если она не задана, в `Jenkinsfile` используется значение по умолчанию `drones-jenkins-agent:local`.

### Пример запуска контроллера Jenkins

Краткий путь: **`make jenkins-up`** (эквивалентно ручному `docker run` с теми же параметрами).

Подставьте порт и volume для домашнего каталога Jenkins:

```bash
set -a && . docker/.env && set +a
docker run -d --name jenkins \
  --env-file docker/.env \
  -p "${JENKINS_HTTP_PORT:-8080}:8080" \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  drones-jenkins:local
```

Опционально задать память JVM контроллера (если задан `JENKINS_JAVA_OPTS` в `docker/.env`): добавьте к `docker run` аргумент `-e "JAVA_OPTS=${JENKINS_JAVA_OPTS}"` после загрузки `.env` в shell.

Установите плагины: **Pipeline**, **Docker**, **Docker Pipeline**, **Git**. Создайте Pipeline job **из SCM**, укажите путь к `Jenkinsfile` в корне репозитория.

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
