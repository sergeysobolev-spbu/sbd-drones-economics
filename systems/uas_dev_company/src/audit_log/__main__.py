"""Worker: audit_log."""

import os

from audit_log.handlers import build_audit_log_handlers
from shared.topics import ComponentTopics
from shared.worker_runtime import run_service_worker

_AUDIT_LOG_TRUSTED_SENDERS = frozenset(
    {
        ComponentTopics.SECURITY_MONITOR,
        ComponentTopics.USER_MANAGEMENT,
        ComponentTopics.FIRMWARE_INGESTION,
        ComponentTopics.CERTIFICATION_SERVICE,
        ComponentTopics.DRONE_REGISTRY,
        ComponentTopics.PURCHASE_SERVICE,
    }
)


if __name__ == "__main__":
    run_service_worker(
        os.environ.get("COMPONENT_ID", "audit_log_worker"),
        "audit_log",
        ComponentTopics.AUDIT_LOG,
        build_audit_log_handlers,
        trusted_sender=_AUDIT_LOG_TRUSTED_SENDERS,
    )
