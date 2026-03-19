## Выбор брокера сообщений (Kafka vs Mosquitto/MQTT)

Система Эксплуатант использует абстракцию `broker` (`SystemBus`) и **не зависит напрямую** от конкретного транспорта.

### Значение по умолчанию

- По умолчанию используется **MQTT (Mosquitto)**:
  - `BROKER_TYPE=mqtt`

### Переключение транспорта

Переменная окружения:

- `BROKER_TYPE`: `mqtt` или `kafka`

#### MQTT (Mosquitto)

Переменные окружения:

- `MQTT_BROKER` (default: `localhost`)
- `MQTT_PORT` (default: `1883`)

Запуск:

- `docker compose -f systems/operator/docker-compose.yml up -d --build`
- или из каталога `systems/operator`: `make up-mqtt`

#### Kafka (опционально)

Переменные окружения:

- `KAFKA_BOOTSTRAP_SERVERS` (пример: `kafka:9092`)

Запуск:

- из каталога `systems/operator`: `make up-kafka`

Важно: для Kafka-режима базовый образ собирается с `INSTALL_KAFKA=1` и устанавливает `kafka-python` из `systems/operator/requirements.kafka.txt`.

### Live notebook (Агрегатор)

Для ручной проверки жизненного цикла заказа со стороны Агрегатора используйте notebook:

- `notebooks/aggregator_operator_live_demo.ipynb`

В нём можно выбрать `broker = "mqtt"` или `broker = "kafka"` и выполнить сценарий end-to-end через `SystemBus`.

