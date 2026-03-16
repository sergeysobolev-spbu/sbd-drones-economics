"""
Топики и действия для системы Эксплуатант
"""

class SystemTopics:
    """Топики систем в экосистеме"""
    OPERATOR = "systems.operator"
    REGULATOR = "systems.regulator"
    AGGREGATOR = "systems.aggregator"
    UTM = "systems.utm"
    INSURER = "systems.insurer"
    GCS = "systems.gcs"
    UAS = "systems.uas"


class ComponentTopics:
    """Топики компонентов системы Эксплуатант"""
    SECURITY_MONITOR = "operator.security_monitor"
    FLEET_MANAGER = "operator.fleet_manager"
    MISSION_PLANNER = "operator.mission_planner"
    BUSINESS_LOGIC = "operator.business_logic"
    ORDER_MANAGER = "operator.order_manager"


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


class FleetManagerActions:
    """Действия менеджера парка"""
    GET_UAS_LIST = "get_uas_list"
    GET_UAS_STATUS = "get_uas_status"
    FIND_AVAILABLE_UAS = "find_available_uas"
    RESERVE_UAS = "reserve_uas"
    RELEASE_UAS = "release_uas"
    UPDATE_UAS_STATUS = "update_uas_status"


class MissionPlannerActions:
    """Действия планировщика миссий"""
    CREATE_MISSION = "create_mission"
    VALIDATE_MISSION = "validate_mission"
    REQUEST_UTM_APPROVAL = "request_utm_approval"
    UPDATE_MISSION_STATUS = "update_mission_status"
    GET_MISSION_DETAILS = "get_mission_details"


class BusinessLogicActions:
    """Действия бизнес-логики"""
    CALCULATE_COST = "calculate_cost"
    CHECK_PROFITABILITY = "check_profitability"
    REQUEST_INSURANCE_QUOTE = "request_insurance_quote"
    CREATE_PROPOSAL = "create_proposal"
    VALIDATE_ECONOMICS = "validate_economics"