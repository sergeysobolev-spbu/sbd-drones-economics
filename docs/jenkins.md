<!-- doc-meta: status=active version=1.1 updated=2026-06-28 -->

# Jenkins CI

Локальный Jenkins для прогона CI-пайплайнов проекта (`unit`, `integration`, `e2e`, phase 0 smoke). Поднимается через Docker Compose, конфигурируется декларативно через **JCasC** (Jenkins Configuration as Code).

## Сокращения

| Сокращение | Расшифровка |
|---|---|
| **JCasC** | Jenkins Configuration as Code — декларативная конфигурация UI и job |
| **SCM** | Source Control Management — checkout исходников из Git |
| **E2E** | End-to-end — сквозные интеграционные тесты |

## Быстрый старт: Jenkins и автотесты

Два профиля портов: **local** (разработка на хосте) и **jenkins** (pipeline внутри контейнера Jenkins обращается к сервисам через `host.docker.internal`). Числа **не пересекаются** — см. [ports.md](ports.md).

### Локально (без Jenkins)

```bash
git clone --recurse-submodules <url> sbd-drones-economics
cd sbd-drones-economics
make init
make ci-config-check          # structural gate: порты + phase0-smoke + preflight-скрипты
make unit-test                # или make ci-test для полного unit+integration
make phase0-smoke             # T14 structural, без Docker-стека
# runtime (нужен Docker):
make e2e-codespace            # E2E_RUN_MODE=local по умолчанию
make phase0-smoke-full        # T14 runtime, нужен поднятый стек
```

### Лenkins-профиль на хосте (эмуляция pipeline)

```bash
make init
E2E_RUN_MODE=jenkins make e2e-codespace   # или make e2e-jenkins-core
make ports-check                          # сверка local ↔ jenkins
```

### Локальный Jenkins + канарейка

```bash
make jenkins-up               # создаёт ci/jenkins/.env, JCasC, job в UI
make jenkins-preflight          # GIT_BRANCH на remote + pin субмодулей
make jenkins-apply-jobs         # после правки casc.yaml
make ci-recovery-check          # Wave 2 checklist (structural gates)
WAIT=1 make jenkins-build-phase0-smoke WAIT=1   # канарейка drone-phase0-smoke
```

Job `drone-phase0-smoke` выполняет только **`make phase0-smoke`** (structural, `-k Structure`) и **не** вызывает `git submodule update --init --recursive` — канарейка проверяет checkout superproject, pipenv и контракты phase 0 без полного дерева субмодулей. Job `drone-unit`, `drone-integration`, `drone-e2e` инициализируют субмодули в своих Jenkinsfile.

Подробнее о целях Makefile: [build_and_test.md](build_and_test.md). Оркестрация восстановления CI: [ci_recovery_orchestration.md](ci_recovery_orchestration.md).

## Что внутри

```
ci/
├── Jenkinsfile.unit                    Pipeline: unit-тесты (python:3.11)
├── Jenkinsfile.integration             Pipeline: integration-тесты
├── Jenkinsfile.e2e                     Pipeline: E2E (E2E_RUN_MODE=jenkins)
├── Jenkinsfile.phase0-smoke            Pipeline: structural gate T14 (без submodule init)
├── Jenkinsfile.agrodron-security-monitor
├── Jenkinsfile.dummy-fabric-unit
└── jenkins/
    ├── Dockerfile                      jenkins/jenkins:lts + docker CLI + compose
    ├── plugins.txt                     workflow, docker, JCasC, job-dsl, …
    ├── casc.yaml                       JCasC: пользователи, security, jobs
    ├── jobs.canonical.txt              Канонический список job (сверка с UI)
    ├── docker-compose.yml              Сервис drones-jenkins, docker.sock, volume drones_jenkins_home
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

- Создаётся `ci/jenkins/.env` из `.env.example` (если его ещё нет — отредактируй пароль и ветку).
- Собирается образ `drones-jenkins:local`, стартует контейнер `drones-jenkins`.
- После старта вызывается `make jenkins-apply-jobs` (JCasC reload + проверка job в UI).

Логин по умолчанию: **admin / changeme** (из `.env`).

### 2. Применить JCasC после правки casc.yaml

Добавление `Jenkinsfile` в git **не создаёт** job в UI автоматически. После изменения `casc.yaml`:

```bash
make jenkins-apply-jobs
```

`jenkins-apply-jobs` зависит от **`jenkins-preflight`** (ветка на remote + pin субмодулей).

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

Volume **`drones_jenkins_home`** изолирован от Jenkins платформы ТЭМ (`jenkins_jenkins_home`). Смешение job `tem-*` и `drone-*` в одном volume — типичная причина «чужих» pipeline в UI. Полный сброс:

```bash
make jenkins-down
docker volume rm drones_jenkins_home
make jenkins-up
```

## Preflight: ветка SCM и pin субмодулей

### `make jenkins-preflight`

Два скрипта подряд:

| Шаг | Скрипт | Проверка |
|---|---|---|
| 1 | `scripts/check_jenkins_env.sh` | `GIT_BRANCH` из `ci/jenkins/.env` существует на `GIT_REPO_URL` (skip для `file://` SCM) |
| 2 | `scripts/check_jenkins_submodule_pins.sh` | gitlink каждого submodule в **HEAD** parent-репозитория доступен на upstream remote |

Типичные ошибки:

- **`Couldn't find any revision to build`** — `GIT_BRANCH=feature/Jenkins` без push на GitFlic; исправление: `GIT_BRANCH=master` или push ветки.
- **`check_jenkins_submodule_pins: FAIL`** — commit субмодуля не на remote upstream (см. playbook ниже).

`jenkins-preflight` также входит в **`make ci-config-check`** (если есть `ci/jenkins/.env`) и в **`make jenkins-apply-jobs`**.

### Playbook: «commit не на remote» (not our ref)

Симптом в логе Jenkins или preflight:

```text
ERROR: commit <sha> для systems/Agregator не найден на https://github.com/.../Agregator.git
  push upstream или repin gitlink в parent repo
```

Класс отказа: **scm** (не product, не порты).

| Ситуация | Действие | Владелец |
|---|---|---|
| **Наш fork, commit локальный** | `git push` в upstream субмодуля; затем push parent с gitlink | maintainer субмодуля |
| **Upstream чужой, SHA устарел** | В субмодуле: checkout доступного commit на remote; в parent: `git add systems/<name>`; commit + push parent | DevOps / maintainer |
| **Субмодуль в `CI_*_EXCLUDE`** | Job unit/integration может skip; pin всё равно блокирует **`ci-config-check`** и job с `submodule update` | зафиксировать issue + repin |
| **Канарейка phase0-smoke** | Structural gate **не** требует init субмодулей — может быть green при red unit/e2e | не путать с полным CI green |

Проверка вручную:

```bash
bash scripts/check_jenkins_submodule_pins.sh
git ls-remote <submodule-url> <sha>
```

После repin: `make ci-config-check` → `make jenkins-preflight` → `WAIT=1 make jenkins-build-phase0-smoke`.

## Jobs (JCasC)

| Job | Jenkinsfile | Назначение |
|---|---|---|
| `drone-unit` | `ci/Jenkinsfile.unit` | `make ci-unit-test` (+ submodule init) |
| `drone-integration` | `ci/Jenkinsfile.integration` | `make ci-integration-test` |
| `drone-e2e` | `ci/Jenkinsfile.e2e` | `make e2e-codespace` / jenkins-порты |
| `drone-phase0-smoke` | `ci/Jenkinsfile.phase0-smoke` | `make phase0-smoke` (T14 structural, без submodule init) |
| `drone-agrodron-security-monitor` | `ci/Jenkinsfile.agrodron-security-monitor` | unit security_monitor |
| `drone-dummy-fabric-unit` | `ci/Jenkinsfile.dummy-fabric-unit` | dummy_fabric unit |

Канон имён: `ci/jenkins/jobs.canonical.txt` (6 job).

## Прогон пайплайнов из CLI

```bash
make jenkins-build-unit WAIT=1
make jenkins-build-integration WAIT=1
make jenkins-build-e2e WAIT=1
make jenkins-build-phase0-smoke WAIT=1
make jenkins-build-agrodron-security-monitor WAIT=1
make jenkins-build-dummy-fabric-unit WAIT=1
```

`WAIT=1` — ждёт завершения билда, стримит лог, exit 0 только при `SUCCESS`.

Wave 2 recovery checklist (structural gates + опциональная канарейка):

```bash
make ci-recovery-check
WAIT=1 make ci-recovery-check
```

Скрипт: `scripts/ci_recovery_wave2_checklist.sh`.

Через UI: http://localhost:8080 → job → **Build Now**.

## Конфиг `ci/jenkins/.env`

| Переменная | Описание | Дефолт |
|---|---|---|
| `JENKINS_ADMIN_USER` | Логин админа | `admin` |
| `JENKINS_ADMIN_PASSWORD` | Пароль | `changeme` |
| `JENKINS_HTTP_PORT` | Порт UI | `8080` |
| `JENKINS_AGENT_PORT` | Порт JNLP-агента | `50000` |
| `GIT_REPO_URL` | Репо для SCM checkout | gitflic |
| `GIT_BRANCH` | Ветка (**должна существовать на remote**) | `master` |

## Изоляция портов local / Jenkins

- Локальный E2E: `E2E_RUN_MODE=local` → `config/e2e_ports.local.env` (9092, 8081, …).
- Jenkins E2E pipeline: `E2E_RUN_MODE=jenkins` → `config/e2e_ports.jenkins.env` (19092, 10801, …).
- Эмуляция на хосте: `make e2e-jenkins-core` (= `E2E_RUN_MODE=jenkins make e2e-codespace`).
- Проверка: `make ports-check` (`scripts/check_ports_registry.py` ↔ `docs/ports.md`).

Pipeline `drone-e2e` не должен обращаться к `127.0.0.1:<local-port>` из контейнера Jenkins — только `host.docker.internal` и jenkins-профиль.

## Траблшутинг

**Job не появляется в UI** — выполните `make jenkins-apply-jobs` (не полагайтесь только на перезапуск IDE).

**`make jenkins-up` падает на сборке Docker** — проверьте `docker version`.

**Pipeline падает на checkout `dubious ownership`** — в Jenkinsfile есть `git config safe.directory`.

**Unit-тесты gcs: `BaseRedisStoreComponent`** — рассинхрон субмодуля с SDK монорепо; не связано с Jenkins.

**`Couldn't find any revision to build`** — `GIT_BRANCH` в `.env` не существует на remote; `make jenkins-preflight` или `GIT_BRANCH=master`.

**Submodule checkout fail после green phase0-smoke** — ожидаемо при broken gitlink; см. playbook «commit не на remote».

**`403` при триггере из CLI** — проверьте `JENKINS_ADMIN_PASSWORD` в `.env`.

**E2E red: порт занят** — `make e2e-down`, `bash scripts/e2e_preflight_host_ports.sh`, `make ports-check`.

**В UI job `tem-*` вместо `drone-*`** — stale volume; см. `drones_jenkins_home` vs `jenkins_jenkins_home`.

## См. также

- [build_and_test.md](build_and_test.md) — автотесты локально, gate table
- [ports.md](ports.md) — реестр портов
- [ci_failure_joint_plan.md](ci_failure_joint_plan.md) — совместный план восстановления CI
- [ci_recovery_orchestration.md](ci_recovery_orchestration.md) — Wave 1–3, `make ci-recovery-check`

### Журнал repin субмодулей (2026-06-28)

| Путь | Было (unreachable) | Стало (upstream) |
|------|--------------------|------------------|
| `fabric-network` | `97d2e9c` | `adab7e0` (master) |
| `systems/Agregator` | `08533d2` | `04fb4770` (main); альт. интеграция: `b3c334c` на `integration-system-layout` |
| `systems/agrodron` / `systems/cyber_drons` | `911905d` / `cd638ad` | `4c6ed55` (master cyber_drons) |
| `systems/DroneAnalytics` | `8b52a3a` | `295992d` (main) |
| `systems/drones` | `791aa11` | `d73358d` (main) |
| `systems/insurer` | `ef9c114` | `0bf8900` (main) |
| `systems/SITL-module` | `e0805f0` | `1231686` (main) |
| `systems/drone_port` | `1e86cc2` | `69bc25d` (dev) |
| `systems/team1-regulator_operation_devsecops` | `1f2b1e0` | `9309609` (main) |

Локальные коммиты на fork-ветках без push upstream по-прежнему требуют `git push` в remote субмодуля перед repin на эти SHA.
