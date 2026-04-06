"""Топики и actions для Gateway agregator."""
import os

_NS = os.environ.get("SYSTEM_NAMESPACE", "")
_P = f"{_NS}." if _NS else ""


class SystemTopics:
    AGREGATOR = f"{_P}systems.agregator"


class ComponentTopics:
    AGREGATOR_COMPONENT = f"{_P}components.agregator"


class ExternalTopics:
    """Топики внешних систем, к которым обращается агрегатор."""
    OPERATOR = f"{_P}systems.operator"
    INSURER = f"{_P}systems.insurer"
    ORVD = f"{_P}systems.orvd_system"
    REGULATOR = f"{_P}systems.regulator"


class GatewayActions:
    """Actions, доступные извне через systems.agregator."""
    CREATE_ORDER = "create_order"
    LIST_ORDERS = "list_orders"
    GET_ORDER = "get_order"
    CONFIRM_PRICE = "confirm_price"
    CONFIRM_COMPLETION = "confirm_completion"
    REGISTER_OPERATOR = "register_operator"
    REGISTER_CUSTOMER = "register_customer"
