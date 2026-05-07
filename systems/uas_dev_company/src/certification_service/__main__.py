"""Worker: certification_service."""

import os

from certification_service.handlers import build_certification_handlers
from shared.topics import ComponentTopics
from shared.worker_runtime import run_service_worker


if __name__ == "__main__":
    run_service_worker(
        os.environ.get("COMPONENT_ID", "certification_worker"),
        "certification_service",
        ComponentTopics.CERTIFICATION_SERVICE,
        build_certification_handlers,
    )
