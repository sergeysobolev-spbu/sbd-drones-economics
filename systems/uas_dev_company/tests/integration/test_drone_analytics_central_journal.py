"""Задача 19: опциональная интеграция uas_dev_company с развёрнутым DroneAnalytics (HTTP + Elasticsearch).

Код DroneAnalytics не изменяется; стек поднимается отдельно. Пропуск без UAS_DRONE_ANALYTICS_STACK_INTEGRATION.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

import pytest
import requests

from analytics_adapter import AnalyticsAdapterService
from audit_log.audit_service import AuditLogService, LocalAuditJournalPort
from fakes import FakeRegulator
from shared.services import CertificationService, DroneRegistryService, FirmwareService, UserService
from shared.storage import SQLiteStorage
from shared.topics import Roles

requires_drone_analytics_stack = pytest.mark.skipif(
    not os.environ.get("UAS_DRONE_ANALYTICS_STACK_INTEGRATION"),
    reason="Set UAS_DRONE_ANALYTICS_STACK_INTEGRATION=1 and DroneAnalytics + ES (see docs/README.md)",
)


def _require_env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        pytest.skip(f"{name} is not set for DroneAnalytics stack integration")
    return v


def _elastic_auth() -> tuple[str, str] | None:
    user = os.environ.get("ELASTICSEARCH_USER", "").strip()
    pw = os.environ.get("ELASTICSEARCH_PASSWORD", "").strip()
    if user and pw:
        return (user, pw)
    return None


def _wait_for_es_substring(
    *,
    elastic_url: str,
    index: str,
    substring: str,
    timeout_s: float = 60.0,
    poll_s: float = 2.0,
    min_hits: int = 1,
) -> list[dict[str, Any]]:
    base = elastic_url.rstrip("/")
    deadline = time.monotonic() + timeout_s
    auth = _elastic_auth()
    hits: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        time.sleep(poll_s)
        query = {
            "query": {"match_phrase": {"message": substring}},
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": 25,
        }
        try:
            resp = requests.post(
                f"{base}/{index}/_search",
                json=query,
                timeout=10,
                auth=auth,
            )
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        data = resp.json()
        raw = data.get("hits", {}).get("hits", [])
        hits = [h.get("_source", {}) for h in raw if isinstance(h, dict)]
        if len(hits) >= min_hits:
            break
    return hits


@requires_drone_analytics_stack
def test_certify_and_register_events_reach_drone_analytics_event_index(tmp_path) -> None:
    base_url = _require_env("DRONE_ANALYTICS_URL").rstrip("/")
    api_key = _require_env("DRONE_ANALYTICS_API_KEY")
    elastic_url = _require_env("ELASTIC_URL")

    # Прогрев: API доступен
    try:
        r = requests.get(f"{base_url}/", timeout=5)
        if r.status_code >= 500:
            pytest.skip("DroneAnalytics root unavailable")
    except requests.RequestException:
        pytest.skip("DroneAnalytics not reachable")

    token = f"da19-{uuid.uuid4().hex[:12]}"
    firmware_id = f"fw-{token}"
    serial = f"SN-{token}"

    storage = SQLiteStorage(tmp_path / "da19.sqlite3")
    analytics = AnalyticsAdapterService(
        storage,
        enabled=True,
        url=base_url,
        api_key=api_key,
        client=None,
    )
    sink = LocalAuditJournalPort(AuditLogService(storage, central_journal=analytics))

    fake_reg = FakeRegulator()
    users = UserService(storage, security_journal=sink)
    admin = users.bootstrap_admin("admin-da19", "adm-da19")
    dev = users.create_user(admin["role"], "dev-da19", Roles.DEVELOPER, "d")

    fw = FirmwareService(storage, security_journal=sink)
    cert_svc = CertificationService(storage, regulator=fake_reg, security_journal=sink)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, security_journal=sink)

    fw.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": firmware_id,
            "supplier": "s-da19",
            "drone_type": "testcraft",
            "version": "1.0",
            "firmware_hash": "deadbeefda19",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p-da19",
        },
    )
    c_out = cert_svc.certify(Roles.DEVELOPER, dev["username"], firmware_id)
    cert_id = str(c_out["certificate_id"])
    reg_svc.register(
        Roles.DEVELOPER,
        {
            "serial_number": serial,
            "drone_type": "testcraft",
            "firmware_id": firmware_id,
            "certificate_id": cert_id,
            "security_goals": ["ЦБ-1"],
            "price": 100,
        },
    )

    hits_fw = _wait_for_es_substring(
        elastic_url=elastic_url,
        index="event",
        substring=token,
        timeout_s=90.0,
    )
    messages = " ".join(str(h.get("message", "")) for h in hits_fw)
    assert token in messages
    assert "firmware_certified" in messages
    assert "drone_registered" in messages


@requires_drone_analytics_stack
def test_registration_error_reaches_drone_analytics_event_index(tmp_path) -> None:
    base_url = _require_env("DRONE_ANALYTICS_URL").rstrip("/")
    api_key = _require_env("DRONE_ANALYTICS_API_KEY")
    elastic_url = _require_env("ELASTIC_URL")

    try:
        r = requests.get(f"{base_url}/", timeout=5)
        if r.status_code >= 500:
            pytest.skip("DroneAnalytics root unavailable")
    except requests.RequestException:
        pytest.skip("DroneAnalytics not reachable")

    token = f"da19err-{uuid.uuid4().hex[:12]}"
    firmware_id = f"fw-{token}"

    storage = SQLiteStorage(tmp_path / "da19err.sqlite3")
    analytics = AnalyticsAdapterService(
        storage,
        enabled=True,
        url=base_url,
        api_key=api_key,
        client=None,
    )
    sink = LocalAuditJournalPort(AuditLogService(storage, central_journal=analytics))

    fake_reg = FakeRegulator()
    users = UserService(storage, security_journal=sink)
    admin = users.bootstrap_admin("admin-da19e", "adm-da19e")
    dev = users.create_user(admin["role"], "dev-da19e", Roles.DEVELOPER, "d")

    fw = FirmwareService(storage, security_journal=sink)
    cert_svc = CertificationService(storage, regulator=fake_reg, security_journal=sink)
    reg_svc = DroneRegistryService(storage, regulator=fake_reg, security_journal=sink)

    fw.submit(
        Roles.DEVELOPER,
        dev["username"],
        {
            "firmware_id": firmware_id,
            "supplier": "s-da19e",
            "drone_type": "testcraft",
            "version": "1.0",
            "firmware_hash": "deadbeefda19e",
            "security_goals": ["ЦБ-1"],
            "authenticity_proof": "p-da19e",
        },
    )
    cert_svc.certify(Roles.DEVELOPER, dev["username"], firmware_id)

    with pytest.raises(ValueError, match="certified firmware is required"):
        reg_svc.register(
            Roles.DEVELOPER,
            {
                "serial_number": f"SN-{token}",
                "drone_type": "testcraft",
                "firmware_id": firmware_id,
                "certificate_id": "cert-wrong-not-in-db",
                "security_goals": ["ЦБ-1"],
                "price": 1,
            },
        )

    hits = _wait_for_es_substring(
        elastic_url=elastic_url,
        index="event",
        substring=token,
        timeout_s=90.0,
    )
    assert hits, "no documents matched token in event index"
    merged = " ".join(str(h.get("message", "")) for h in hits)
    assert token in merged
    assert "drone_registration_failed" in merged
    assert "no_matching_certificate" in merged
    severities = {str(h.get("severity", "")).lower() for h in hits}
    assert "error" in severities

