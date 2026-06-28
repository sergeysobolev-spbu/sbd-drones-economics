"""
Топики и действия для системы Эксплуатант с поддержкой версионирования
"""

import os
from typing import Dict, Optional


class TopicBuilder:
    """Построитель топиков с учетом версионирования и уникальных идентификаторов"""

    @staticmethod
    def get_system_id() -> str:
        """Получить уникальный идентификатор системы из переменной окружения"""
        return os.environ.get("SYSTEM_ID", "operator-default")

    @staticmethod
    def get_version() -> str:
        """Получить версию API из переменной окружения"""
        return os.environ.get("API_VERSION", "v1")

    @staticmethod
    def build_internal_topic(component: str) -> str:
        """Построить топик для внутреннего компонента системы"""
        system_id = TopicBuilder.get_system_id()
        return f"{system_id}.{component}"

    @staticmethod
    def build_external_topic(system_type: str) -> str:
        """Построить топик для внешней системы с версионированием"""
        system_id = TopicBuilder.get_system_id()
        version = TopicBuilder.get_version()
        return f"{system_id}.{version}.{system_type}"


class SystemTopics:
    """Топики систем в экосистеме"""

    # Регулятор не имеет уникального идентификатора
    REGULATOR = "systems.regulator"

    # Обратная совместимость: ранее в коде встречается обращение к константе
    # `SystemTopics.OPERATOR` (без вызова метода). Делаем её динамической через метакласс ниже.

    # Остальные системы получают топики динамически
    @staticmethod
    def get_operator() -> str:
        """Топик системы Эксплуатант"""
        return TopicBuilder.build_external_topic("operator")

    @staticmethod
    def get_aggregator(aggregator_id: Optional[str] = None) -> str:
        """Топик системы Агрегатор"""
        if aggregator_id:
            return f"systems.aggregator.{aggregator_id}"
        # Получаем из переменной окружения
        aggregator_id = os.environ.get("AGGREGATOR_ID", "aggregator-default")
        return f"systems.aggregator.{aggregator_id}"

    @staticmethod
    def get_utm(utm_id: Optional[str] = None) -> str:
        """Топик системы ОрВД"""
        if utm_id:
            return f"systems.utm.{utm_id}"
        utm_id = os.environ.get("UTM_ID", "utm-default")
        return f"systems.utm.{utm_id}"

    @staticmethod
    def get_insurer(insurer_id: Optional[str] = None) -> str:
        """Топик системы Страховая"""
        if insurer_id:
            return f"systems.insurer.{insurer_id}"
        insurer_id = os.environ.get("INSURER_ID", "insurer-default")
        return f"systems.insurer.{insurer_id}"

    @staticmethod
    def get_gcs(gcs_id: Optional[str] = None) -> str:
        """Топик системы НУС"""
        if gcs_id:
            return f"systems.gcs.{gcs_id}"
        gcs_id = os.environ.get("GCS_ID", "gcs-default")
        return f"systems.gcs.{gcs_id}"

    @staticmethod
    def get_uas(uas_id: str) -> str:
        """Топик конкретного БАС"""
        return f"systems.uas.{uas_id}"

    @staticmethod
    def get_developer(developer_id: str) -> str:
        """Топик системы Разработчик"""
        return f"systems.developer.{developer_id}"


class ComponentTopics:
    """Топики компонентов системы Эксплуатант"""

    @staticmethod
    def get_security_monitor() -> str:
        """Топик компонента Security Monitor"""
        return TopicBuilder.build_internal_topic("security_monitor")

    @staticmethod
    def get_fleet_manager() -> str:
        """Топик компонента Fleet Manager"""
        return TopicBuilder.build_internal_topic("fleet_manager")

    @staticmethod
    def get_mission_planner() -> str:
        """Топик компонента Mission Planner"""
        return TopicBuilder.build_internal_topic("mission_planner")

    @staticmethod
    def get_business_logic() -> str:
        """Топик компонента Business Logic"""
        return TopicBuilder.build_internal_topic("business_logic")

    @staticmethod
    def get_developer_client() -> str:
        """Топик компонента Developer Client"""
        return TopicBuilder.build_internal_topic("developer_client")

    @staticmethod
    def get_regulator_client() -> str:
        """Топик компонента Regulator Client"""
        return TopicBuilder.build_internal_topic("regulator_client")

    @staticmethod
    def get_event_journal() -> str:
        """Топик компонента Event Journal"""
        return TopicBuilder.build_internal_topic("event_journal")


class _TopicsMeta(type):
    """
    Метакласс для ленивых "констант" топиков.

    Нужен для обратной совместимости: старый код обращается к `ComponentTopics.SECURITY_MONITOR`
    и `SystemTopics.OPERATOR` как к строковым константам. Значения должны зависеть от `SYSTEM_ID`,
    поэтому вычисляем их при обращении к атрибуту.
    """

    _system_aliases = {
        "OPERATOR": "get_operator",
        "AGGREGATOR": "get_aggregator",
        "UTM": "get_utm",
        "INSURER": "get_insurer",
        "GCS": "get_gcs",
    }

    _component_aliases = {
        "SECURITY_MONITOR": "get_security_monitor",
        "FLEET_MANAGER": "get_fleet_manager",
        "MISSION_PLANNER": "get_mission_planner",
        "BUSINESS_LOGIC": "get_business_logic",
        "DEVELOPER_CLIENT": "get_developer_client",
        "REGULATOR_CLIENT": "get_regulator_client",
        "EVENT_JOURNAL": "get_event_journal",
    }

    def __getattr__(cls, name: str):  # noqa: N805 (metaclass API)
        if cls.__name__ == "SystemTopics":
            method_name = _TopicsMeta._system_aliases.get(name)
            if method_name and hasattr(cls, method_name):
                return getattr(cls, method_name)()

        if cls.__name__ == "ComponentTopics":
            method_name = _TopicsMeta._component_aliases.get(name)
            if method_name and hasattr(cls, method_name):
                return getattr(cls, method_name)()

        raise AttributeError(f"{cls.__name__}.{name} is not defined")


# Подключаем метакласс для динамических алиасов
SystemTopics = _TopicsMeta("SystemTopics", SystemTopics.__bases__, dict(SystemTopics.__dict__))
ComponentTopics = _TopicsMeta("ComponentTopics", ComponentTopics.__bases__, dict(ComponentTopics.__dict__))


class OperatorActions:
    """Действия системы Эксплуатант"""

    # Управление заказами
    RECEIVE_ORDER = "receive_order"
    CALCULATE_PROPOSAL = "calculate_proposal"
    SUBMIT_PROPOSAL = "submit_proposal"
    ACCEPT_ORDER = "accept_order"
    REJECT_ORDER = "reject_order"

    # Управление парком
    GET_FLEET_STATUS = "get_fleet_status"
    SELECT_UAS = "select_uas"
    RESERVE_UAS = "reserve_uas"
    RELEASE_UAS = "release_uas"

    # Планирование миссий
    PLAN_MISSION = "plan_mission"
    REGISTER_MISSION = "register_mission"
    START_MISSION = "start_mission"
    COMPLETE_MISSION = "complete_mission"
    ABORT_MISSION = "abort_mission"

    # Безопасность
    CHECK_CERTIFICATE = "check_certificate"
    VALIDATE_COMMAND = "validate_command"
    CHECK_PROFITABILITY = "check_profitability"

    # Мониторинг
    GET_MISSION_STATUS = "get_mission_status"
    GET_TELEMETRY = "get_telemetry"
    REPORT_INCIDENT = "report_incident"


class SecurityMonitorActions:
    """Действия монитора безопасности"""

    VALIDATE_REQUEST = "validate_request"
    CHECK_POLICY = "check_policy"
    LOG_VIOLATION = "log_violation"
    BLOCK_ACTION = "block_action"
    GET_SECURITY_STATUS = "get_security_status"
    AUDIT_OPERATION = "audit_operation"


class FleetManagerActions:
    """Действия менеджера парка"""

    GET_UAS_LIST = "get_uas_list"
    GET_UAS_STATUS = "get_uas_status"
    FIND_AVAILABLE_UAS = "find_available_uas"
    RESERVE_UAS = "reserve_uas"
    RELEASE_UAS = "release_uas"
    UPDATE_UAS_STATUS = "update_uas_status"
    GET_DEVELOPER_CATALOGS = "get_developer_catalogs"
    PURCHASE_UAS = "purchase_uas"
    GET_FLEET_STATISTICS = "get_fleet_statistics"
    GET_PURCHASE_HISTORY = "get_purchase_history"


class MissionPlannerActions:
    """Действия планировщика миссий"""

    CREATE_MISSION = "create_mission"
    VALIDATE_MISSION = "validate_mission"
    REQUEST_UTM_APPROVAL = "request_utm_approval"
    UPDATE_MISSION_STATUS = "update_mission_status"
    GET_MISSION_DETAILS = "get_mission_details"
    CALCULATE_ROUTE = "calculate_route"
    CHECK_AIRSPACE = "check_airspace"


class BusinessLogicActions:
    """Действия бизнес-логики"""

    CALCULATE_COST = "calculate_cost"
    CHECK_PROFITABILITY = "check_profitability"
    REQUEST_INSURANCE_QUOTE = "request_insurance_quote"
    CREATE_PROPOSAL = "create_proposal"
    PROCESS_ORDER = "process_order"
    GET_STATISTICS = "get_statistics"
    VALIDATE_ECONOMICS = "validate_economics"
    OPTIMIZE_PRICING = "optimize_pricing"


class DeveloperClientActions:
    """Действия клиента разработчика"""

    GET_CATALOG = "get_catalog"
    GET_ALL_CATALOGS = "get_all_catalogs"
    PURCHASE_UAS = "purchase_uas"
    CHECK_AVAILABILITY = "check_availability"
    GET_SPECIFICATIONS = "get_specifications"


class RegulatorClientActions:
    """Действия клиента регулятора"""

    GET_SYSTEM_TOPICS = "get_system_topics"
    CHECK_CERTIFICATE = "check_certificate"
    GET_REGULATIONS = "get_regulations"
    REPORT_INCIDENT = "report_incident"
    GET_SECURITY_GOALS = "get_security_goals"


# Вспомогательные функции для обратной совместимости
def get_component_topic(component_name: str) -> str:
    """Получить топик компонента по имени"""
    topic_map = {
        "security_monitor": ComponentTopics.get_security_monitor,
        "fleet_manager": ComponentTopics.get_fleet_manager,
        "mission_planner": ComponentTopics.get_mission_planner,
        "business_logic": ComponentTopics.get_business_logic,
        "developer_client": ComponentTopics.get_developer_client,
        "regulator_client": ComponentTopics.get_regulator_client,
    }

    getter = topic_map.get(component_name)
    if getter:
        return getter()

    # Fallback для неизвестных компонентов
    return TopicBuilder.build_internal_topic(component_name)


def get_external_system_topics() -> Dict[str, str]:
    """Получить словарь топиков внешних систем"""
    return {
        "regulator": SystemTopics.REGULATOR,
        "operator": SystemTopics.get_operator(),
        "aggregator": SystemTopics.get_aggregator(),
        "utm": SystemTopics.get_utm(),
        "insurer": SystemTopics.get_insurer(),
        "gcs": SystemTopics.get_gcs(),
    }


# --- Алиасы экшенов для обратной совместимости ---
# В коде/ноутбуке встречается `OperatorSystemActions`, но актуальный класс называется `OperatorActions`.
OperatorSystemActions = OperatorActions
