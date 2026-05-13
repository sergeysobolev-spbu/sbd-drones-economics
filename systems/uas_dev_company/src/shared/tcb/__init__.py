"""Чистое ядро политик ДВБ (TCB policy core): без I/O и брокера."""

from shared.tcb.cb_constants import (
    CANONICAL_SECURITY_GOAL_IDS,
    CANONICAL_SECURITY_GOAL_IDS_ORDERED,
    normalize_canonical_security_goals,
)
from shared.tcb.auth_policy import hash_password, verify_password
from shared.tcb.certification_policy import (
    regulator_certify_status_ok,
    regulator_register_status_ok,
    regulator_reregistration_status_ok,
)
from shared.tcb.errors import AuthorizationError
from shared.tcb.journal_policy import build_analytics_event_payload, security_event_to_analytics_payload
from shared.tcb.registry_policy import (
    assert_drone_goals_subset_when_local_regulator,
    drone_port_response_accepted,
    validate_purchase_prerequisites,
)
from shared.tcb.role_policy import require_developer_or_operator_for_registry, require_role
from shared.tcb.vulnerability_policy import apply_effective_goals_to_drone_goals

__all__ = [
    "AuthorizationError",
    "CANONICAL_SECURITY_GOAL_IDS",
    "CANONICAL_SECURITY_GOAL_IDS_ORDERED",
    "apply_effective_goals_to_drone_goals",
    "assert_drone_goals_subset_when_local_regulator",
    "build_analytics_event_payload",
    "drone_port_response_accepted",
    "hash_password",
    "normalize_canonical_security_goals",
    "regulator_certify_status_ok",
    "regulator_register_status_ok",
    "regulator_reregistration_status_ok",
    "require_developer_or_operator_for_registry",
    "require_role",
    "security_event_to_analytics_payload",
    "validate_purchase_prerequisites",
    "verify_password",
]
