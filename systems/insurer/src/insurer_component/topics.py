"""Топики и actions для InsurerComponent."""
import os

_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class ComponentTopics:
    INSURER_COMPONENT = f"{_P}components.insurer"


class ExternalTopics:
    """Топики внешних систем."""
    FABRIC = f"{_P}systems.dummy_fabric"


class InsurerActions:
    # Годовое страхование (КАСКО/hull) — оформляется при регистрации дрона
    ANNUAL_INSURANCE = "annual_insurance"
    # Миссионное страхование — рассчитывается перед каждым вылетом
    MISSION_INSURANCE = "mission_insurance"
    # Устаревшие экшены (обратная совместимость)
    CALCULATE_POLICY = "calculate_policy"
    PURCHASE_POLICY = "purchase_policy"
    REPORT_INCIDENT = "report_incident"
    TERMINATE_POLICY = "terminate_policy"
