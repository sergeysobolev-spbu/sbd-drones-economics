"""Topic names, actions, and roles for the UAS development company system."""

from __future__ import annotations

import os


SYSTEM_NAME = "uas_dev_company"


def _prefix() -> str:
    namespace = os.environ.get("SYSTEM_NAMESPACE", "").strip()
    return f"{namespace}." if namespace else ""


def system_topic() -> str:
    """Return the public system topic."""
    return f"{_prefix()}systems.{SYSTEM_NAME}"


def component_topic(name: str) -> str:
    """Return a component topic for this system (components.<имя>, см. docs/topic_namespaces.md)."""
    return f"{_prefix()}components.{name}"


class Roles:
    """Supported user roles."""

    ADMIN = "администратор"
    DEVELOPER = "разработчик"
    OPERATOR = "эксплуатант"

    ALL = {ADMIN, DEVELOPER, OPERATOR}


class ComponentTopics:
    """Internal component topics."""

    API_GATEWAY = component_topic("api_gateway")
    SECURITY_MONITOR = component_topic("security_monitor")
    USER_MANAGEMENT = component_topic("user_management")
    FIRMWARE_INGESTION = component_topic("firmware_ingestion")
    COMPONENT_CATALOG = component_topic("component_catalog")
    DRONE_ASSEMBLY = component_topic("drone_assembly")
    CERTIFICATION_SERVICE = component_topic("certification_service")
    REGULATOR_ADAPTER = component_topic("regulator_adapter")
    DRONE_REGISTRY = component_topic("drone_registry")
    PURCHASE_SERVICE = component_topic("purchase_service")
    AUDIT_LOG = component_topic("audit_log")
    ANALYTICS_ADAPTER = component_topic("analytics_adapter")


class ExternalTopics:
    """Системные топики смежных систем (docs/topic_namespaces.md).

    Методы вызывать при каждом обращении — так учитывается актуальный SYSTEM_NAMESPACE.
    """

    @staticmethod
    def regulator() -> str:
        return f"{_prefix()}systems.regulator"

    @staticmethod
    def operator_fleet() -> str:
        return f"{_prefix()}systems.operator"

    @staticmethod
    def drone_port() -> str:
        return f"{_prefix()}systems.drone_port"

    @staticmethod
    def drone_analytics() -> str:
        return f"{_prefix()}systems.drone_analytics"


class Actions:
    """Actions accepted by backend components."""

    PROXY_REQUEST = "proxy_request"
    BOOTSTRAP_ADMIN = "bootstrap_admin"
    CREATE_USER = "create_user"
    LIST_USERS = "list_users"
    ENABLE_USER = "enable_user"
    DISABLE_USER = "disable_user"
    DELETE_USER = "delete_user"
    AUTHENTICATE = "authenticate"
    SUBMIT_FIRMWARE = "submit_firmware"
    CERTIFY_FIRMWARE = "certify_firmware"
    LIST_CERTIFICATES = "list_certificates"
    REPORT_CRITICAL_VULNERABILITY = "report_critical_vulnerability"
    REGISTER_DRONE = "register_drone"
    LIST_REGISTERED_DRONES = "list_registered_drones"
    PURCHASE_DRONE = "purchase_drone"
    LOG_EVENT = "log_event"
    RECORD_AUDIT = "record_audit"
    SEND_ANALYTICS = "send_analytics"
    # Явные разрешения на фазы IPC под контролем security_monitor (Задача 14).
    IPC_INBOUND_REQUEST = "ipc_inbound_request"
    IPC_RESPONSE = "ipc_response"
