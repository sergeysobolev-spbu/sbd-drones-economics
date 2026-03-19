"""
Mission Planner component entrypoint.

Запускает компонент через общий launcher `systems.operator.src.run_component`.
"""

from __future__ import annotations

import asyncio
import os

from systems.operator.src.run_component import run_component


def main() -> None:
    os.environ.setdefault("COMPONENT_TYPE", "mission_planner")
    os.environ.setdefault("COMPONENT_ID", "planner-01")
    asyncio.run(run_component())


if __name__ == "__main__":
    main()
