# Системы

Шаблон: `systems/dummy_system/`

## Внешние репозитории (git submodule)

Часть систем живёт в **отдельных репозиториях** и подключена через `git submodule`.

Некоторые из них — **монорепозитории** (содержат несколько проектов), поэтому используется схема:
- полный клон лежит в `vendor/<имя>/`
- в `systems/` — **симлинк** на нужную подпапку

| Рабочий путь (симлинк) | Vendor-подпапка | Удалённый репозиторий |
|---|---|---|
| `systems/gcs` | `vendor/DronePortGCS/systems/gcs` | [Kaitrye/DronePortGCS](https://github.com/Kaitrye/DronePortGCS.git) |
| `systems/cyber_drons` | `vendor/cyber_drons` (корень = весь репо) | [itmoniks/cyber_drons](https://gitflic.ru/project/itmoniks/cyber_drons.git) |
| `systems/orvd_system` | `vendor/OpBD/systems/orvd_system` | [autoryuzo/OpBD](https://github.com/autoryuzo/OpBD.git) |
| `systems/operator` | `vendor/mk2-cooperated/systems/operator` | [glitcher-how/mk2-cooperated](https://github.com/glitcher-how/mk2-cooperated.git) |

Следующие submodule'ы — **не** монорепо, подключены напрямую в `systems/`:

| Путь | Удалённый репозиторий |
|---|---|
| `systems/DroneAnalytics` | [OurPaintTeam/DroneAnalytics](https://github.com/OurPaintTeam/DroneAnalytics.git) |
| `systems/drone-operator-system` | [glitcher-how/drone-operator-system](https://github.com/glitcher-how/drone-operator-system.git) |

### Правило: всегда работай через `systems/`

Скрипты, docker-compose, `prepare_multi.py`, E2E-тесты — **всё** ходит через `systems/<имя>`. Папка `vendor/` — только место хранения полного клона; напрямую в ней ничего менять не нужно.

### Клон с сабмодулями

```bash
git clone --recurse-submodules <url-этого-репозитория>
# или после обычного clone:
git submodule update --init --recursive
```

### Обновить сабмодули до зафиксированных SHA

```bash
git submodule update --init --recursive
```

### Подтянуть новые коммиты из апстрима

```bash
git submodule update --remote --recursive
# затем при необходимости закоммить обновлённые SHA
```

Остальные системы (`agregator`, `insurer`, `regulator`, `dummy_system`, …) живут прямо в этом репозитории.

Для E2E к GCS добавлены сервисы `gcs_system_gateway` и `gcs_route_component` (топик `systems.gcs`, action `plan_mission_route`) в `../vendor/DronePortGCS/systems/gcs` (симлинк `systems/gcs`).

## Создать свою систему

1. Скопировать `dummy_system` → `systems/my_system/`
2. В `src/` — полные копии компонентов: `my_system/src/my_component_a/`, `my_system/src/my_component_b/`
3. Каждый компонент: `src/`, `topics.py`, `.env`, `__main__.py`, `docker/Dockerfile`
4. `docker-compose.yml` — только сервисы компонентов (без брокера)
5. `make prepare` — собирает .generated/ (брокер + компоненты)
6. `make docker-up` — запуск

## Структура

```
systems/my_system/
├── src/
│   ├── my_component_a/
│   │   ├── src/
│   │   ├── topics.py
│   │   ├── .env            # COMPONENT_ID, BROKER_USER, BROKER_PASSWORD
│   │   ├── __main__.py
│   │   └── docker/Dockerfile
│   └── my_component_b/
├── docker-compose.yml
├── .generated/
├── tests/
└── Makefile
```

## Команды

```bash
cd systems/my_system
make prepare
make docker-up
make unit-test
make integration-test
```

## .env компонента

`COMPONENT_ID`, `BROKER_USER`, `BROKER_PASSWORD`, `HEALTH_PORT`. Без `BROKER_TYPE`, портов брокера, админских кредов.
