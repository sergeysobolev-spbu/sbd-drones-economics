"""Формирование минимального EventLogItem для внешнего журнала (контракт DroneAnalytics)."""

from __future__ import annotations

import os
import time
import zlib
from datetime import datetime, timezone
from typing import Any

# Соответствие домена UAS литералу `service` из DroneAnalytics (LogServiceType).
_DOMAIN_TO_LOG_SERVICE: dict[str, str] = {
    "user_management": "operator",
    "firmware_ingestion": "registry",
    "certification_service": "regulator",
    "drone_registry": "registry",
    "purchase_service": "insurance",
    "audit_log": "aggregator",
    "analytics_adapter": "aggregator",
    "api_gateway": "infopanel",
    "security_monitor": "regulator",
}


def instance_id(*, fallback: str = "local-uas") -> str:
    """Идентификатор экземпляра процесса (compose: COMPONENT_ID)."""
    v = os.environ.get("COMPONENT_ID", "").strip()
    return v if v else fallback


def domain_to_log_service(source: str) -> str:
    """Возвращает допустимое имя сервиса для DroneAnalytics по полю source события."""
    key = (source or "").strip().lower()
    return _DOMAIN_TO_LOG_SERVICE.get(key, "registry")


def stable_service_id(instance_id: str) -> int:
    """Стабильный числовой service_id >= 1 для пары экземпляра и домена.

    Индекс `event` в DroneAnalytics задаёт `service_id` как signed short (≤ 32767);
    большее значение даёт ошибку _bulk и событие не попадает в Elasticsearch.
    """
    raw = zlib.crc32(instance_id.encode("utf-8")) & 0x7FFF
    return raw if raw > 0 else 1


def _ts_utc_iso(now: float | None = None) -> str:
    t = now if now is not None else time.time()
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()


def build_analytics_event_payload(
    *,
    message: str,
    severity: str = "info",
    service: str = "registry",
    service_id: int = 1,
    event_kind: str | None = "event",
    now: float | None = None,
) -> dict[str, Any]:
    ts = int((now if now is not None else time.time()))
    return {
        "apiVersion": "v1.0.0",
        "timestamp": ts,
        "event_type": event_kind,
        "service": service,
        "service_id": service_id,
        "severity": severity,
        "message": str(message or "")[:1024] or "-",
    }


def security_event_to_analytics_payload(
    event: object,
    *,
    instance_id_override: str | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Контракт центрального журнала для записи из системного журнала."""
    event_type = str(getattr(event, "event_type", "") or "")
    severity = str(getattr(event, "severity", "info") or "info")
    source = str(getattr(event, "source", "") or "")
    subject = str(getattr(event, "subject", "") or "")
    details = str(getattr(event, "details", "") or "")
    inst = (instance_id_override or "").strip() or instance_id()
    svc = domain_to_log_service(source)
    sid = stable_service_id(f"{inst}:{source}")
    ts_iso = _ts_utc_iso(now)
    parts = [
        f"ts_utc={ts_iso}",
        f"instance_id={inst}",
        event_type,
        f"severity={severity}",
        f"source={source}",
        f"subject={subject}",
    ]
    if details:
        parts.append(f"details={details[:400]}")
    message = " ".join(parts)
    sev = severity.lower()
    if sev not in ("debug", "info", "notice", "warning", "error", "critical", "alert"):
        sev = "info"
    return build_analytics_event_payload(
        message=message,
        severity=sev,
        service=svc,
        service_id=sid,
        now=now,
    )
