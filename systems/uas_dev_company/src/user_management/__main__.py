"""Worker: user_management."""

import os

from shared.topics import ComponentTopics
from shared.worker_runtime import run_service_worker

from user_management.handlers import build_user_management_handlers


if __name__ == "__main__":
    run_service_worker(
        os.environ.get("COMPONENT_ID", "user_management_worker"),
        "user_management",
        ComponentTopics.USER_MANAGEMENT,
        build_user_management_handlers,
    )
