"""Соответствие доменов безопасности сервисам Docker Compose (Задача 11).

Правило: в контейнере один уровень критичности; если выполняется хотя бы одна
операция, критичная для ЦБ, весь домен (образ/процесс) относится к ДВБ.

Задача 15: для **оценки стоимости ДВБ** (метрики) объём `union_cb123_python_scope` считается
только по доменам, реализующим официальные **ЦБ-1…ЦБ-3** из docs/README.md. Домены, закрывающие
лишь **ТБ**, остаются в составе `python_domains_tcb`, но с ``in_cb123_tcb_union: false``.

Задача 23: пути `python_path_specs` отражают **фактический COPY** в узких образах (whitelist
`shared`, один пакет домена, bus-gateway без `sqlite_context.py`). Исключение: опциональный
сервис `api_gateway_sqlite` — толстый dev-образ (весь `src/`); в union метрик Задачи 11 не
включается (см. `CONTAINER_NON_PYTHON`).

Задача 24: парсинг ``docker/worker.Dockerfile`` и соседних Dockerfile должен давать те же множества файлов ``*.py``, что и расширение
`python_path_specs` (проверка в `scripts/tcb_metrics.py` без `--relax-docker-drift`);
«НДБ-носители» — `scripts/tcb_module_roles.json` → метрики `task24_copy_ndb_carrier`.
"""

from __future__ import annotations

import re
from pathlib import Path

# Воркеры: общий образ `docker/worker.Dockerfile`; без security_monitor / journal_bootstrap.
SHARED_WORKER_SCOPE: list[str] = [
    "src/shared/__init__.py",
    "src/shared/tcb",
    "src/shared/protocols.py",
    "src/shared/services.py",
    "src/shared/storage.py",
    "src/shared/topics.py",
    "src/shared/domain_storage.py",
    "src/shared/models.py",
    "src/shared/jwt_tokens.py",
    "src/shared/component_base.py",
    "src/shared/worker_runtime.py",
    "src/shared/worker_deps.py",
    "src/shared/external_adapters_factory.py",
    "src/shared/analytics_ipc.py",
    "src/shared/audit_log_ipc.py",
    "src/shared/bus_integration_adapters.py",
    "src/shared/integration_adapters.py",
    "src/shared/monitor_client.py",
    "src/shared/monitor_proxy_unwrap.py",
    "src/shared/journal_startup.py",
]

# Шлюз bus: без sqlite_context и без доменных пакетов (`src/gateway/docker/Dockerfile`).
SHARED_GATEWAY_BUS_SCOPE: list[str] = [
    "src/shared/__init__.py",
    "src/shared/tcb",
    "src/shared/jwt_tokens.py",
    "src/shared/models.py",
    "src/shared/topics.py",
    "src/shared/audit_log_ipc.py",
    "src/shared/journal_bootstrap.py",
    "src/shared/monitor_proxy_unwrap.py",
    "src/gateway/__init__.py",
    "src/gateway/__main__.py",
    "src/gateway/bus_backend.py",
    "src/gateway/server.py",
]

# Security monitor: `src/security_monitor/docker/Dockerfile`.
SHARED_SECURITY_MONITOR_SCOPE: list[str] = [
    "src/shared/__init__.py",
    "src/shared/tcb",
    "src/shared/models.py",
    "src/shared/topics.py",
    "src/shared/audit_log_ipc.py",
    "src/shared/journal_bootstrap.py",
    "src/shared/security_monitor.py",
    "src/shared/security_policies.py",
    "src/security_monitor/__init__.py",
    "src/security_monitor/__main__.py",
]

# Python-домены compose (профиль bus). Поле in_cb123_tcb_union — включается в union для метрик ЦБ-1…3.
CONTAINER_TCB_PYTHON_DOMAINS: list[dict[str, str | bool | list[str]]] = [
    {
        "compose_service": "api_gateway",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": True,
        "maps_to_cb": ["ЦБ-1", "ЦБ-2", "ЦБ-3"],
        "rationale_ru": "HTTP API, JWT, прокси к доменам реализации ЦБ-1…ЦБ-3 через security_monitor",
        "security_goals_ru": [
            "ТБ: точка входа, привязка к ролям разработчика (ЦБ-2) для операций сертификации и реестра",
            "ТБ: маршрутизация внутреннего IPC под политиками монитора (реализация всех трёх ЦБ)",
        ],
        "python_path_specs": [*SHARED_GATEWAY_BUS_SCOPE],
    },
    {
        "compose_service": "security_monitor",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": True,
        "maps_to_cb": ["ЦБ-1", "ЦБ-2", "ЦБ-3"],
        "rationale_ru": "Единая точка allow/deny для внутреннего РКИВ (контроль доступа к ЦБ-операциям)",
        "security_goals_ru": [
            "ТБ: разграничение маршрутов IPC к воркерам ЦБ-1…ЦБ-3",
            "ТБ: явные политики запроса и ответа по доменам (ipc_inbound_request / ipc_response)",
        ],
        "python_path_specs": [*SHARED_SECURITY_MONITOR_SCOPE],
    },
    {
        "compose_service": "user_management_worker",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": True,
        "maps_to_cb": ["ЦБ-2"],
        "rationale_ru": "ЦБ-2: идентификация разработчика, инициирующего сертификацию и регистрацию",
        "security_goals_ru": [
            "ЦБ-2: только авторизованный разработчик может запускать операции сертификации и реестра",
            "ТБ: учётные записи, хэши паролей, роли (механизм достижения ЦБ-2)",
        ],
        "python_path_specs": ["src/user_management", *SHARED_WORKER_SCOPE],
    },
    {
        "compose_service": "firmware_ingestion_worker",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": True,
        "maps_to_cb": ["ЦБ-1"],
        "rationale_ru": "ЦБ-1: приём только проверяемого артефакта прошивки (хеш или репозиторий+коммит)",
        "security_goals_ru": [
            "ЦБ-1: фиксация подлинности и происхождения прошивки до решения о сертификации",
            "ТБ: метаданные поставки, неизменяемые идентификаторы артефакта",
        ],
        "python_path_specs": ["src/firmware_ingestion", *SHARED_WORKER_SCOPE],
    },
    {
        "compose_service": "certification_service_worker",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": True,
        "maps_to_cb": ["ЦБ-1"],
        "rationale_ru": "ЦБ-1: перевод прошивки в сертифицированный контур по решению Регулятора",
        "security_goals_ru": [
            "ЦБ-1: связка прошивки с сертификатом; отказ при подделке целей или статуса",
            "ТБ: сценарии отзыва и сужения заявленных целей (effective_security_goals)",
        ],
        "python_path_specs": ["src/certification_service", *SHARED_WORKER_SCOPE],
    },
    {
        "compose_service": "drone_registry_worker",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": True,
        "maps_to_cb": ["ЦБ-3"],
        "rationale_ru": "ЦБ-3: витрина и карточка экземпляра только при действующей сертификации и регистрации",
        "security_goals_ru": [
            "ЦБ-3: допуск в реестр/витрину по инвариантам сертификата и регистрации",
            "ТБ: согласование заявленных целей экземпляра с сертификатом (множество ЦБ-1…ЦБ-3, ТБ-2)",
        ],
        "python_path_specs": ["src/drone_registry", *SHARED_WORKER_SCOPE],
    },
    {
        "compose_service": "purchase_service_worker",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": False,
        "maps_to_cb": [],
        "rationale_ru": "ТБ-1, ТБ-3: сделка, перерегистрация владения (вне официальных ЦБ-1…ЦБ-3)",
        "security_goals_ru": [
            "ТБ-1: исключение повторной продажи, согласованность статуса владения",
            "ТБ-3: фиксация передачи до разрешённой эксплуатации у Эксплуатанта",
        ],
        "python_path_specs": ["src/purchase_service", *SHARED_WORKER_SCOPE],
    },
    {
        "compose_service": "audit_log_worker",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": False,
        "maps_to_cb": [],
        "rationale_ru": "ТБ: системный журнал (SQLite) и при DRONE_ANALYTICS_ENABLED — дублирование в analytics_adapter → DroneAnalytics",
        "security_goals_ru": [
            "ТБ: аудируемость операций для расследований и демонстрации контроля",
            "ТБ: полезная нагрузка событий без утечки избыточных данных (journal_policy)",
        ],
        "python_path_specs": ["src/audit_log", *SHARED_WORKER_SCOPE],
    },
    {
        "compose_service": "analytics_adapter_worker",
        "whole_domain_in_tcb": True,
        "in_cb123_tcb_union": False,
        "maps_to_cb": [],
        "rationale_ru": "ТБ: граница доставки во внешний журнал DroneAnalytics (отдельный контур от audit_log)",
        "security_goals_ru": [
            "ТБ: изоляция сетевого исхода к системным.drone_analytics от доменов ЦБ",
            "ТБ: приём только доверенных отправителей (домены ЦБ и audit_log) на IPC",
        ],
        "python_path_specs": ["src/analytics_adapter", *SHARED_WORKER_SCOPE],
    },
]

CONTAINER_NON_PYTHON: list[dict[str, str | bool]] = [
    {
        "compose_service": "api_gateway_sqlite",
        "whole_domain_in_tcb": True,
        "kind": "optional_fat_sqlite_gateway",
        "note_ru": (
            "Профиль sqlite-dev (`src/gateway/docker/Dockerfile.sqlite`): полное дерево `src/` в образе; "
            "не объединяется в union метрик Задачи 11 с узким `api_gateway`, чтобы не дублировать охват."
        ),
    },
    {
        "compose_service": "web_portal",
        "whole_domain_in_tcb": False,
        "kind": "nuxt_frontend",
        "note_ru": "Презентационный слой; принятие решений по ЦБ на сервере. Риски UI/UX вне ДВБ-метрик Python.",
    },
    {
        "compose_service": "nginx_reverse_proxy",
        "whole_domain_in_tcb": False,
        "kind": "reverse_proxy",
        "note_ru": "Только маршрутизация HTTP; логика ЦБ не в образе приложения.",
    },
]


def compose_service_names(compose_yml: Path) -> list[str]:
    """Имена сервисов под `services:` (не volumes/networks)."""
    lines = compose_yml.read_text(encoding="utf-8").splitlines()
    in_services = False
    names: list[str] = []
    for line in lines:
        if line.startswith("services:"):
            in_services = True
            continue
        if in_services:
            if line and not line[0].isspace():
                break
            m = re.match(r"^  ([a-z][a-z0-9_]*):\s*$", line)
            if m:
                names.append(m.group(1))
    return names


def expected_compose_services() -> set[str]:
    py = {str(d["compose_service"]) for d in CONTAINER_TCB_PYTHON_DOMAINS}
    other = {str(d["compose_service"]) for d in CONTAINER_NON_PYTHON}
    return py | other
