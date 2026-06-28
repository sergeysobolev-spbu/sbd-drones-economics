import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SYSTEMS_OPERATOR_DIR = REPO_ROOT / "systems" / "operator"


def _run_make(target: str) -> None:
    subprocess.run(
        ["make", "-C", str(SYSTEMS_OPERATOR_DIR), target],
        cwd=str(REPO_ROOT),
        check=True,
    )


def _docker_available() -> bool:
    return shutil.which("docker") is not None


@pytest.mark.skipif(
    not _docker_available() or os.getenv("RUN_DOCKER_TESTS", "").lower() != "1",
    reason="docker недоступен или RUN_DOCKER_TESTS!=1",
)
def test_operator_shell_e2e_mqtt() -> None:
    # Сквозной прогон через docker-compose (shell сценарии).
    _run_make("test-shell-mqtt")


@pytest.mark.skipif(
    not _docker_available() or os.getenv("RUN_DOCKER_TESTS", "").lower() != "1",
    reason="docker недоступен или RUN_DOCKER_TESTS!=1",
)
def test_operator_shell_e2e_kafka() -> None:
    _run_make("test-shell-kafka")

