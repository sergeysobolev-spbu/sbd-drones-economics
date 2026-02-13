# Systems

Системы - внешние сервисы, взаимодействующие через SystemBus (Kafka/MQTT).

Шаблон: `dummy_system/`

## Создание системы

### 1. Структура

```
systems/my_system/
├── __init__.py
└── src/
    ├── __init__.py
    └── my_system.py
```

### 2. Топик и actions в `shared/topics.py`

```python
class SystemTopics:
    MY_SYSTEM = "systems.my_system"

class MySystemActions:
    DO_SOMETHING = "do_something"
    RESPONSE = "response"
```

### 3. Класс системы

```python
from shared.base_system import BaseSystem
from shared.topics import SystemTopics, MySystemActions
from broker.system_bus import SystemBus

class MySystem(BaseSystem):
    def __init__(self, system_id: str, name: str, bus: SystemBus, health_port=None):
        super().__init__(
            system_id=system_id,
            system_type="my_system",
            topic=SystemTopics.MY_SYSTEM,
            bus=bus,
            health_port=health_port
        )

    def _register_handlers(self):
        self.register_handler(MySystemActions.DO_SOMETHING, self._handle_do_something)

    def _handle_do_something(self, message: dict) -> dict:
        payload = message.get("payload", {})
        return {"result": "ok"}
```

### 4. Docker

```yaml
# docker/docker-compose.yml
my_system:
  build:
    context: ..
    dockerfile: docker/Dockerfile
  environment:
    - SYSTEM_TYPE=my_system
    - SYSTEM_ID=my_system_001
    - HEALTH_PORT=9800
    - BROKER_TYPE=kafka
    - BROKER_USER=my_user
    - BROKER_PASSWORD=secret
    - KAFKA_BOOTSTRAP_SERVERS=kafka:29092
  ports:
    - "9800:9800"
  networks:
    - drones_net
  depends_on:
    - kafka
```

### 5. Запуск

`python -m systems` с env: `SYSTEM_TYPE=my_system`, `SYSTEM_ID`, `BROKER_USER`, `BROKER_PASSWORD`.

## Отправка сообщений

```python
response = self.bus.request(
    SystemTopics.DUMMY,
    {"action": DummyActions.ECHO, "sender": self.system_id, "payload": {"data": "hello"}},
    timeout=10.0
)
```
