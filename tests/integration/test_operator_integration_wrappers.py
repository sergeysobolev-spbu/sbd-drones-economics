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


def test_operator_integration_local() -> None:
    # Интеграционные тесты без docker: быстрый sanity-check.
    _run_make("test-integration-local")


@pytest.mark.skipif(
    not _docker_available() or os.getenv("RUN_DOCKER_TESTS", "").lower() != "1",
    reason="docker недоступен или RUN_DOCKER_TESTS!=1",
)
def test_operator_integration_mqtt_docker() -> None:
    _run_make("test-integration")


@pytest.mark.skipif(
    not _docker_available() or os.getenv("RUN_DOCKER_TESTS", "").lower() != "1",
    reason="docker недоступен или RUN_DOCKER_TESTS!=1",
)
def test_operator_integration_kafka_docker() -> None:
    _run_make("test-integration-kafka")

