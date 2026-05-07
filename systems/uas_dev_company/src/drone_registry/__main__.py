"""Worker: drone_registry."""

import os

from drone_registry.handlers import build_drone_registry_handlers
from shared.topics import ComponentTopics
from shared.worker_runtime import run_service_worker


if __name__ == "__main__":
    run_service_worker(
        os.environ.get("COMPONENT_ID", "drone_registry_worker"),
        "drone_registry",
        ComponentTopics.DRONE_REGISTRY,
        build_drone_registry_handlers,
    )
