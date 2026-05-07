"""Worker: purchase_service."""

import os

from purchase_service.handlers import build_purchase_handlers
from shared.topics import ComponentTopics
from shared.worker_runtime import run_service_worker


if __name__ == "__main__":
    run_service_worker(
        os.environ.get("COMPONENT_ID", "purchase_service_worker"),
        "purchase_service",
        ComponentTopics.PURCHASE_SERVICE,
        build_purchase_handlers,
    )
