# Quick Start

Брокер (Kafka/MQTT) + SDK. Шаблоны: `components/dummy_component`, `systems/dummy_system`.

## Структура

```
broker/              Шина, create_system_bus
sdk/                 BaseComponent, BaseSystem
components/          Standalone-компоненты
systems/             Системы (dummy_system)
docker/              Брокер (kafka, mosquitto)
scripts/             prepare_system.py
config/              Pipfile, pyproject.toml
```

## Команды

```bash
make init          # pipenv + зависимости
make unit-test     # Unit тесты
make docker-up     # Брокер (kafka/mqtt)
make docker-down
```

**Система:**
```bash
cd systems/dummy_system
make prepare       # Собрать .generated/
make docker-up    # Брокер + компоненты
make unit-test
make integration-test
```

## Протокол

Сообщения — dict: `action`, `payload`, `sender`, `correlation_id`, `reply_to`.

## Свой компонент/система

- **Компонент:** `components/README.MD`
- **Система:** `systems/README.md`

## Docker

```bash
cp docker/example.env docker/.env
# BROKER_TYPE=kafka или mqtt
make docker-up
```

| Переменная | Описание |
|------------|----------|
| BROKER_TYPE | kafka / mqtt |
| ADMIN_USER, ADMIN_PASSWORD | Админ брокера |
| COMPONENT_USER_A/B | Опционально, для компонентов |

## Troubleshooting

- Брокер недоступен: проверьте profile (kafka/mqtt) в docker-up
- Внутри Docker: имена контейнеров (kafka, mosquitto), не localhost
