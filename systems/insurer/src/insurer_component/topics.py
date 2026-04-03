"""Топики и actions для InsurerComponent."""
import os

_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class ComponentTopics:
    INSURER_COMPONENT = f"{_P}components.insurer"


class InsurerActions:
    CALCULATE_POLICY = "calculate_policy"
    PURCHASE_POLICY = "purchase_policy"
    REPORT_INCIDENT = "report_incident"
    TERMINATE_POLICY = "terminate_policy"
