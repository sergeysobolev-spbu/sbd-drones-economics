"""Задача 11: модель доменов Docker и согласованность с compose."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def test_compose_services_match_container_domain_model() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from tcb_container_domains import (  # noqa: E402
        compose_service_names,
        expected_compose_services,
    )

    yml = ROOT / "docker-compose.yml"
    observed = set(compose_service_names(yml))
    assert observed == expected_compose_services()


def test_container_assessment_embedded_in_tcb_metrics_json() -> None:
    metrics_path = ROOT / "docs" / "tcb_metrics.json"
    if not metrics_path.is_file():
        pytest.skip("tcb_metrics.json missing; run scripts/tcb_metrics.py --target")
    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    block = data.get("container_isolation_tcb_task11")
    assert block is not None
    assert block.get("compose_service_set_matches_model") is True
    assert len(block.get("python_domains_tcb") or []) == 9
    union = block.get("union_unique_backend_python_scope") or {}
    agg = union.get("aggregate") or {}
    assert (agg.get("file_count") or 0) >= 40
    cb_scope = block.get("union_cb123_python_scope") or {}
    cb_agg = cb_scope.get("aggregate") or {}
    assert (cb_agg.get("file_count") or 0) >= 30
    assert (cb_agg.get("total_sloc") or 0) <= (agg.get("total_sloc") or 0)


def test_tcb_metrics_script_emits_task11_block() -> None:
    out = ROOT / "docs" / ".tcb_metrics_task11_smoke.json"
    try:
        subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "tcb_metrics.py"),
                "--target",
                "--out",
                str(out),
            ],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "container_isolation_tcb_task11" in data
        assert data["container_isolation_tcb_task11"]["compose_service_set_matches_model"] is True
        t12 = data.get("tcb_cost_task12") or {}
        assert t12.get("task12_after_snapshot", {}).get("allow_rules_count", 0) >= 14
        assert t12.get("task12_after_snapshot", {}).get("gateway_direct_service_imports_in_server_py") is False
        snap = t12.get("task12_after_snapshot") or {}
        assert snap.get("union_all_system_backend_python_sloc", 0) >= snap.get("union_backend_python_sloc", 0)
        assert "union_cb123_python_scope" in data["container_isolation_tcb_task11"]
        ipc = data["tcb_ipc_topology_task14"]
        assert ipc.get("deduped_directed_edge_count", 0) >= 10
    finally:
        if out.is_file():
            out.unlink()
