"""Worker: analytics_adapter (граница к внешнему журналу)."""

import os

from analytics_adapter.handlers import build_analytics_adapter_handlers
from shared.topics import ComponentTopics
from shared.worker_runtime import run_service_worker

_ANALYTICS_TRUSTED_SENDERS = frozenset(
    {
        ComponentTopics.CERTIFICATION_SERVICE,
        ComponentTopics.DRONE_REGISTRY,
        ComponentTopics.PURCHASE_SERVICE,
        ComponentTopics.AUDIT_LOG,
    }
)


if __name__ == "__main__":
    run_service_worker(
        os.environ.get("COMPONENT_ID", "analytics_adapter_worker"),
        "analytics_adapter",
        ComponentTopics.ANALYTICS_ADAPTER,
        build_analytics_adapter_handlers,
        trusted_sender=_ANALYTICS_TRUSTED_SENDERS,
    )
