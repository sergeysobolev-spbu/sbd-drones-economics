"""Топики и actions для AgregatorComponent."""
import os

_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class ComponentTopics:
    AGREGATOR_COMPONENT = f"{_P}components.agregator"


class ExternalTopics:
    """Топики внешних систем."""
    OPERATOR = f"{_P}systems.operator"
    INSURER = f"{_P}systems.insurer"
    ORVD = f"{_P}systems.orvd_system"
    REGULATOR = f"{_P}systems.regulator"


class AgregatorActions:
    CREATE_ORDER = "create_order"
    LIST_ORDERS = "list_orders"
    GET_ORDER = "get_order"
    CONFIRM_PRICE = "confirm_price"
    CONFIRM_COMPLETION = "confirm_completion"
    REGISTER_OPERATOR = "register_operator"
    REGISTER_CUSTOMER = "register_customer"
