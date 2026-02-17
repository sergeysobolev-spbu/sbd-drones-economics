# Components

Компоненты — модули дрона, взаимодействующие через **SystemBus** (единая шина с системами).

Шаблон: `dummy_component/`

## Структура

```
components/my_component/
├── src/
│   ├── __init__.py
│   └── my_component.py
└── tests/
    └── test_my_component.py
```

## Класс компонента

Наследуется от `BaseComponent` (аналог `BaseSystem` для систем):

```python
from shared.base_component import BaseComponent
from broker.system_bus import SystemBus

class MyComponent(BaseComponent):
    def __init__(self, component_id: str, name: str, bus: SystemBus):
        super().__init__(
            component_id=component_id,
            component_type="my_component",
            topic="components.my_component",
            bus=bus,
        )

    def _register_handlers(self):
        self.register_handler("do_action", self._handle_do_action)

    def _handle_do_action(self, message: dict) -> dict:
        payload = message.get("payload", {})
        return {"result": "ok", "from": self.component_id}
```

## SystemBus API

```python
# Request/response (синхронный)
response = bus.request("components.my_component", {
    "action": "do_action",
    "sender": "caller_id",
    "payload": {"key": "value"},
}, timeout=10.0)

# Fire-and-forget
bus.publish("components.my_component", {
    "action": "do_action",
    "sender": "caller_id",
    "payload": {"key": "value"},
})
```

## Самостоятельный запуск

### Локально

```bash
export COMPONENT_ID=dummy_component_a
export BROKER_TYPE=mqtt
export MQTT_BROKER=localhost
export MQTT_PORT=1883
python -m components
```

Для Kafka: `BROKER_TYPE=kafka`, `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`.

### Docker

- Используется общий `docker/Dockerfile` (единый с системами), команда переопределяется в compose.
- Переменные окружения в `docker/.env`: `BROKER_TYPE` (общий), `COMPONENT_ID_A/B`, `COMPONENT_USER_A/B`, `COMPONENT_PASSWORD_A/B`.
- В `docker-compose.yml` — сервисы `dummy_component_a` и `dummy_component_b` (профили `kafka`, `mqtt`).

```bash
cd docker
cp example.env .env
docker compose -f docker-compose.yml --env-file .env --profile mqtt up -d --build
```
