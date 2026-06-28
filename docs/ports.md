<!-- doc-meta: status=active version=1.1 updated=2026-06-28 -->

# Реестр публичных портов E2E и CI

Канонические профили: `config/e2e_ports.local.env` (локальный `make e2e`) и `config/e2e_ports.jenkins.env` (Jenkins pipeline с `E2E_RUN_MODE=jenkins`). Числовые значения **local** и **jenkins** не пересекаются.

Проверка: `make ports-check` (`scripts/check_ports_registry.py`).

## Брокер (хост)

| Переменная | local | jenkins | Назначение |
|---|---|---|---|
| `KAFKA_PORT` | 9092 | 19092 | Kafka SASL_PLAINTEXT на хосте |
| `KAFKA_INTERNAL_PORT` | 29092 | 39092 | Внутренний listener Kafka (host map) |
| `MQTT_PORT` | 1883 | 31883 | Mosquitto на хосте |
| `KAFKA_ADVERTISED_HOST` | localhost | host.docker.internal | Advertised listener для клиентов |

## HTTP-сервисы E2E (health / pytest)

| Переменная | local | jenkins | Сервис |
|---|---|---|---|
| `AGREGATOR_PORT` | 8081 | 10801 | Агрегатор |
| `REGULATOR_PORT` | 8088 | 10808 | Регулятор |
| `ANALYTICS_PORT` | 8090 | 10990 | DroneAnalytics |
| `DELIVERY_DRONE_HEALTH_PORT` | 8095 | 10995 | Delivery drone health |
| `AGRODRON_GATEWAY_HOST_PORT` | 18081 | 11881 | Agrodron gateway |
| `SYSTEM_MONITOR_HOST_PORT` | 18090 | 11890 | System monitor |

## URL (pytest / readiness)

| Переменная | local | jenkins |
|---|---|---|
| `AGREGATOR_URL` | http://localhost:8081 | http://host.docker.internal:10801 |
| `REGULATOR_URL` | http://localhost:8088 | http://host.docker.internal:10808 |
| `ANALYTICS_URL` | http://localhost:8090 | http://host.docker.internal:10990 |
| `KAFKA_BOOTSTRAP_SERVERS` | localhost:9092 | host.docker.internal:19092 |

## Jenkins UI (отдельно от E2E)

| Переменная | Файл | Дефолт | Назначение |
|---|---|---|---|
| `JENKINS_HTTP_PORT` | `ci/jenkins/.env` | 8080 | UI Jenkins на хосте |
| `JENKINS_AGENT_PORT` | `ci/jenkins/.env` | 50000 | JNLP агент |

## См. также

- [jenkins.md](jenkins.md) — локальный Jenkins и JCasC
- [build_and_test.md](build_and_test.md) — автотесты и профили CI
