# Топики и действия IPC (`uas_dev_company`)

Префикс компонентов: `components.<имя>` внутри системы (`SYSTEM_NAMESPACE` при необходимости добавляет префикс к `systems.uas_dev_company`). Значения задаются в `shared.topics` (`ComponentTopics`, `Actions`, `ExternalTopics`).

## Компонентные топики

| Константа | Строка топика (без namespace) |
|-----------|------------------------------|
| `API_GATEWAY` | `components.api_gateway` |
| `SECURITY_MONITOR` | `components.security_monitor` |
| `USER_MANAGEMENT` | `components.user_management` |
| `FIRMWARE_INGESTION` | `components.firmware_ingestion` |
| `CERTIFICATION_SERVICE` | `components.certification_service` |
| `DRONE_REGISTRY` | `components.drone_registry` |
| `PURCHASE_SERVICE` | `components.purchase_service` |
| `AUDIT_LOG` | `components.audit_log` |
| `ANALYTICS_ADAPTER` | `components.analytics_adapter` |

## Действия (Actions)

| Действие | Назначение |
|----------|------------|
| `proxy_request` | Шлюз → монитор; воркер → монитор (междоменный RPC под политикой). |
| `get_firmware_row` | Чтение строки прошивки по `firmware_id` (через монитор с домена-отправителя). |
| `get_certificate_snapshot` | Снимок сертификата по `certificate_id` и `firmware_id`. |
| `apply_firmware_cert_decision` | Применение решения Регулятора по прошивке к строкам реестра дронов. |
| `get_drone_purchase_row` | Данные дрона для проверки покупки (из реестра). |
| `update_drone_purchase` | Фазированное обновление дрона при покупке/доставке (`phase` в payload). |
| `ipc_inbound_request` / `ipc_response` | Доставка запроса монитор → воркер и ответ обратно (низкоуровневый контур IPC). |

Остальные действия (`bootstrap_admin`, `submit_firmware`, `certify_firmware`, …) см. в `shared.topics.Actions`.

## Внешние топики

`ExternalTopics`: `regulator`, `operator_fleet`, `drone_port`, `drone_analytics` — смежные системы (префикс `systems.*`).
