from __future__ import annotations

from typing import Any, Dict, Optional

from .messages import Message


def emit_event(
    bus,
    topic: str,
    event_type: str,
    *,
    severity: str = "info",
    source_component: str,
    payload: Optional[Dict[str, Any]] = None,
    trace_context: Optional[Any] = None,
) -> None:
    """
    Публикует нормализованное событие в компонент EventJournal.

    Функция не должна бросать исключения наружу: при любой ошибке
    она просто логирует проблему и продолжает выполнение.
    """

    payload_dict: Dict[str, Any] = {
        "event_type": event_type,
        "severity": severity,
        "source_component": source_component,
        "payload": payload or {},
    }

    if trace_context is not None:
        payload_dict["trace_id"] = getattr(trace_context, "trace_id", None)
        payload_dict["span_id"] = getattr(trace_context, "span_id", None)
        payload_dict["parent_span_id"] = getattr(trace_context, "parent_span_id", None)

    try:
        msg = Message(
            action="emit_event",
            sender=source_component,
            payload=payload_dict,
        ).to_dict()
        bus.publish(topic, msg)
    except Exception:
        # Event emission must never break business logic; swallow errors.
        return

