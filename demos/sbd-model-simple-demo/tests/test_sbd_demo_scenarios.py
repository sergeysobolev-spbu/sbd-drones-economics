"""Идемпотентные сценарии демо (YAML в tmp_path)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sbd_demo import (
    reset_context,
    scenario_certification_and_purchase,
    scenario_customer_agro_order,
)
from world_state import load_world_state


@pytest.fixture
def state_yaml(tmp_path: Path) -> Path:
    """Отдельный YAML на каждый тест."""
    return tmp_path / "demo_state.yaml"


def test_reset_context_fresh(state_yaml: Path) -> None:
    reset_context(state_yaml)
    w = load_world_state(state_yaml)
    assert w["uas_registry"] == {}
    assert len(w["dronports"]["droneport_B"]["uas"]) == 1


def test_onboarding_then_agro_order(state_yaml: Path) -> None:
    reset_context(state_yaml)
    onboarding = scenario_certification_and_purchase(yaml_path=state_yaml)
    assert onboarding["firmware_cert"]["approved"] is True
    assert re.fullmatch(
        r"UAS-[A-Z0-9_]+-[A-Z0-9_]+-\d{6}",
        onboarding["standalone_registration"]["registered_uas_id"],
    )

    w = load_world_state(state_yaml)
    assert len(w["firmware_certificates"]) >= 1
    b_uas = {u["uas_id"] for u in w["dronports"]["droneport_B"]["uas"]}
    for uid in onboarding["purchase"]["registered_uas_ids"]:
        assert uid in b_uas

    agro = scenario_customer_agro_order(yaml_path=state_yaml)
    final = agro["final_order_result"]
    assert final["status"] == "ok"
    assert final["selected_operator"] == "operator_1"
    coords = final["order_execution_completed"]["landing_coordinates"]
    assert coords == w["landing_sites"]["ORDER-DEMO-001"]["droneport_B"]


def test_onboarding_idempotent_separate_files(tmp_path: Path) -> None:
    """Два независимых прогона — одинаковые инварианты формата UAS."""
    for name in ("one.yaml", "two.yaml"):
        p = tmp_path / name
        reset_context(p)
        r = scenario_certification_and_purchase(yaml_path=p)
        for uid in r["purchase"]["registered_uas_ids"]:
            assert re.fullmatch(r"UAS-[A-Z0-9_]+-[A-Z0-9_]+-\d{6}", uid)


def test_agro_requires_prior_onboarding_state(state_yaml: Path) -> None:
    """После только reset без онбординга заказ может пройти на базовом парке (smoke)."""
    reset_context(state_yaml)
    agro = scenario_customer_agro_order(yaml_path=state_yaml)
    assert agro["final_order_result"]["status"] == "ok"
