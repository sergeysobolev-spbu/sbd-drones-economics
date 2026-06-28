## Полуавтоматизированные интеграционные проверки (shell)

Эти скрипты **не поднимают** систему Эксплуатант сами — они рассчитаны на уже запущенные контейнеры `docker compose`.

Важно: это **Kafka-версия** shell-проверок. Для MQTT (Mosquitto) используйте `tests/shell-mqtt/`.

### Предусловия

- `docker` и `docker compose` доступны в PATH
- Контейнеры запущены:

```bash
docker compose -f systems/operator/docker-compose.kafka.yml up -d --build
```

### Запуск

Запустить все проверки:

```bash
./systems/operator/tests/shell/run_all.sh
```

Или по отдельности:

```bash
./systems/operator/tests/shell/01_health.sh
./systems/operator/tests/shell/02_receive_order.sh
./systems/operator/tests/shell/03_fleet_purchase_uas.sh  # проверка Fleet Manager (GET_UAS_LIST)
```

### Настройка

Переменные окружения (опционально):

- `SYSTEM_ID` (default: `operator-001`)
- `API_VERSION` (default: `v1`)
- `COMPOSE_FILE` (default: `systems/operator/docker-compose.yml`)

