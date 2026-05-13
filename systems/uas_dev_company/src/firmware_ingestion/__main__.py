"""Worker: firmware_ingestion."""

import os

from firmware_ingestion.handlers import build_firmware_ingestion_handlers
from shared.topics import ComponentTopics
from shared.worker_runtime import run_service_worker


if __name__ == "__main__":
    run_service_worker(
        os.environ.get("COMPONENT_ID", "firmware_ingestion_worker"),
        "firmware_ingestion",
        ComponentTopics.FIRMWARE_INGESTION,
        build_firmware_ingestion_handlers,
    )
