"""Run a single ServiceComponent worker (used from src/<component>/__main__.py)."""

from __future__ import annotations

import signal
import sys
import time
from typing import Any, Callable

from broker.bus_factory import create_system_bus

from shared.component_base import ServiceComponent
from shared.storage import SQLiteStorage
from shared.topics import ComponentTopics
from shared.journal_startup import emit_worker_process_startup
from shared.worker_deps import WorkerServiceDeps, build_worker_service_deps


def run_service_worker(
    component_id: str,
    component_type: str,
    topic: str,
    build_handlers: Callable[
        [SQLiteStorage, WorkerServiceDeps],
        dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
    ],
    trusted_sender: str | frozenset[str] | None = None,
) -> None:
    storage = SQLiteStorage()
    bus = create_system_bus(client_id=component_id)
    deps = build_worker_service_deps(bus, topic, component_id)
    handlers = build_handlers(storage, deps)
    component = ServiceComponent(
        component_id=component_id,
        component_type=component_type,
        topic=topic,
        bus=bus,
        handlers=handlers,
        trusted_sender=(
            trusted_sender if trusted_sender is not None else ComponentTopics.SECURITY_MONITOR
        ),
    )
    component.start()
    emit_worker_process_startup(
        storage=storage,
        deps=deps,
        component_id=component_id,
        component_type=component_type,
        topic=topic,
    )
    print(f"[{component_id}] worker listening on {topic}")

    def shutdown(*_args: object) -> None:
        print(f"\n[{component_id}] shutting down...")
        component.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while component._running:
            signal.pause()
    except AttributeError:
        while component._running:
            time.sleep(1)
