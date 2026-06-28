## Shell интеграционные проверки (MQTT/Mosquitto)

Эти скрипты проверяют взаимодействие с поднятым Эксплуатантом через MQTT (Mosquitto).
Они публикуют JSON-сообщения в MQTT топики, ожидая ответы по `reply_to`.

Предусловия:

```bash
docker compose -f systems/operator/docker-compose.yml up -d --build
```

Запуск:

```bash
./systems/operator/tests/shell-mqtt/run_all.sh
```

