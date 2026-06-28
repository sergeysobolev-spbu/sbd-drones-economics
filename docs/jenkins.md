# Jenkins CI

Локальный Jenkins для прогона CI-пайплайнов проекта (`unit`, `integration`, `e2e`, phase 0 smoke). Поднимается через Docker Compose, конфигурируется декларативно через JCasC (Jenkins Configuration as Code).

## Что внутри

```
ci/
├── Jenkinsfile.unit                    Pipeline: unit-тесты (python:3.11)
├── Jenkinsfile.integration             Pipeline: integration-тесты
├── Jenkinsfile.e2e                     Pipeline: E2E (E2E_RUN_MODE=jenkins)
├── Jenkinsfile.phase0-smoke            Pipeline: structural gate T14
├── Jenkinsfile.agrodron-security-monitor
├── Jenkinsfile.dummy-fabric-unit
└── jenkins/
    ├── Dockerfile                      jenkins/jenkins:lts + docker CLI + compose
    ├── plugins.txt                     workflow, docker, JCasC, job-dsl, …
    ├── casc.yaml                       JCasC: пользователи, security, jobs
    ├── jobs.canonical.txt              Канонический список job (сверка с UI)
    ├── docker-compose.yml              Сервис drones-jenkins, docker.sock
    ├── .env.example                    Шаблон конфига
    └── build.sh                        Триггер job через REST API + CSRF crumb
```

Реестр портов local/jenkins: [ports.md](ports.md), профили `config/e2e_ports.*.env`.

## Установка и запуск

### 1. Поднять Jenkins

```bash
make jenkins-up
```

Что происходит:

- Создаётся `ci/jenkins/.env` из `.env.example` (если его ещё нет — отредактируй пароль/ветку).
- Собирается образ `drones-jenkins:local`, стартует контейнер `drones-jenkins`.
- После старта вызывается `make jenkins-apply-jobs` (JCasC reload + проверка job в UI).

Логин по умолчанию: **admin / changeme** (из `.env`).

### 2. Применить JCasC после правки casc.yaml

Добавление `Jenkinsfile` в git **не создаёт** job в UI автоматически. После изменения `casc.yaml`:

```bash
make jenkins-apply-jobs
```

Проверка без reload:

```bash
make jenkins-jobs-verify
```

### 3. Проверить статус

```bash
make jenkins-ps
make jenkins-logs
```

### 4. Остановить / перезапустить

```bash
make jenkins-down
make jenkins-restart    # down + up + jenkins-apply-jobs
```

Volume `drones_jenkins_home` (имя Docker volume) изолирован от platform Jenkins (`jenkins_jenkins_home`). Полный сброс:

```bash
make jenkins-down
docker volume rm drones_jenkins_home
```

Перед первым запуском job: `make jenkins-preflight` — проверяет, что `GIT_BRANCH` из `ci/jenkins/.env` существует на `GIT_REPO_URL` (типичная ошибка: `feature/Jenkins` без push на remote).

## Jobs (JCasC)

| Job | Jenkinsfile | Назначение |
|---|---|---|
| `drone-unit` | `ci/Jenkinsfile.unit` | `make ci-unit-test` |
| `drone-integration` | `ci/Jenkinsfile.integration` | `make ci-integration-test` |
| `drone-e2e` | `ci/Jenkinsfile.e2e` | `make e2e-codespace` (jenkins-порты) |
| `drone-phase0-smoke` | `ci/Jenkinsfile.phase0-smoke` | `make phase0-smoke` (T14 structural) |
| `drone-agrodron-security-monitor` | `ci/Jenkinsfile.agrodron-security-monitor` | unit security_monitor |
| `drone-dummy-fabric-unit` | `ci/Jenkinsfile.dummy-fabric-unit` | dummy_fabric unit |

## Прогон пайплайнов из CLI

```bash
make jenkins-build-unit WAIT=1
make jenkins-build-integration WAIT=1
make jenkins-build-e2e WAIT=1
make jenkins-build-phase0-smoke WAIT=1
```

`WAIT=1` — ждёт завершения билда, стримит лог, exit 0 только при `SUCCESS`.

Через UI: http://localhost:8080 → job → **Build Now**.

## Конфиг `ci/jenkins/.env`

| Переменная | Описание | Дефолт |
|---|---|---|
| `JENKINS_ADMIN_USER` | Логин админа | `admin` |
| `JENKINS_ADMIN_PASSWORD` | Пароль | `changeme` |
| `JENKINS_HTTP_PORT` | Порт UI | `8080` |
| `JENKINS_AGENT_PORT` | Порт JNLP-агента | `50000` |
| `GIT_REPO_URL` | Репо для SCM checkout | gitflic |
| `GIT_BRANCH` | Ветка | `master` |

## Изоляция портов local / Jenkins

- Локальный E2E: `E2E_RUN_MODE=local` → `config/e2e_ports.local.env` (9092, 8081, …).
- Jenkins E2E pipeline: `E2E_RUN_MODE=jenkins` → `config/e2e_ports.jenkins.env` (19092, 10801, …).
- Проверка: `make ports-check`.

Pipeline `drone-e2e` не должен обращаться к `127.0.0.1:<local-port>` из контейнера Jenkins — только `host.docker.internal` и jenkins-профиль.

## Траблшутинг

**Job не появляется в UI** — выполните `make jenkins-apply-jobs` (не полагайтесь только на перезапуск IDE).

**`make jenkins-up` падает на сборке Docker** — проверьте `docker version`.

**Pipeline падает на checkout `dubious ownership`** — в Jenkinsfile есть `git config safe.directory`.

**Unit-тесты gcs: `BaseRedisStoreComponent`** — рассинхрон субмодуля с SDK монорепо; не связано с Jenkins.

**`Couldn't find any revision to build`** — `GIT_BRANCH` в `.env` не существует на remote; `make jenkins-preflight` или `GIT_BRANCH=master`.

**E2E red: порт занят** — `make e2e-down`, `bash scripts/e2e_preflight_host_ports.sh`, `make ports-check`.

## См. также

- [build_and_test.md](build_and_test.md) — автотесты локально
- [ports.md](ports.md) — реестр портов
