"""Топики и actions для Gateway insurer."""
import os

_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class SystemTopics:
    INSURER = f"{_P}systems.insurer"


class ComponentTopics:
    INSURER_COMPONENT = f"{_P}components.insurer"


class GatewayActions:
    """Actions, доступные извне через systems.insurer."""
    ANNUAL_INSURANCE = "annual_insurance"
    MISSION_INSURANCE = "mission_insurance"
    CALCULATE_POLICY = "calculate_policy"
    PURCHASE_POLICY = "purchase_policy"
    REPORT_INCIDENT = "report_incident"
    TERMINATE_POLICY = "terminate_policy"
