"""
Строковые идентификаторы действий для v2.0 demo.

Единый реестр `action` полезен, чтобы избежать расхождений в именах
между сущностями.
"""

# Общие (journal/monitoring в этой версии не используются, но оставляем для полноты)
EMIT_EVENT = "emit_event"
GET_SECURITY_GOALS = "get_security_goals"

# Order lifecycle
PLACE_ORDER = "place_order"
RECEIVE_ORDER = "receive_order"
PROPOSAL_REQUEST = "proposal_request"
ASSIGN_ORDER = "assign_order"

# Insurance
REQUEST_INSURANCE_QUOTE = "request_insurance_quote"

# Mission pipeline
MISSION_PLANNING = "mission_planning"
VALIDATE_MISSION = "validate_mission"
INSURANCE_PAYMENT_PAID = "insurance_payment_paid"

# DronePort / physical readiness + permissions
GET_AVAILABLE_UAS = "get_available_uas"
PREPARE_DISPATCH = "prepare_dispatch"
GRANT_TAKEOFF_PERMISSION = "grant_takeoff_permission"
CHECK_DRONEPORT_READY = "check_droneport_ready"

# Takeoff from ATM to Drone to DronePort
REQUEST_TAKEOFF_PERMISSION = "request_takeoff_permission"

# Landing from Drone to ATM to DronePort back to Drone
REQUEST_LANDING_AUTHORIZATION = "request_landing_authorization"
AUTHORIZE_LANDING = "authorize_landing"
REQUEST_LANDING_PERMISSION = "request_landing_permission"

# Simulation
SITL_SIMULATE = "sitl_simulate"

# Developers (stubs)
FIND_AVAILABLE_UAS = "find_available_uas"
PURCHASE_UAS = "purchase_uas"

# Drone execution
AGRO_MISSION_RECEIVED = "agro_mission_received"
ORDER_EXECUTION_COMPLETED = "order_execution_completed"

