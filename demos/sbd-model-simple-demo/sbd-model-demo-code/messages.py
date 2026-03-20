from __future__ import annotations

"""
Сообщения для ВАБС (ВАш Внутренний Аналог Брокера Событий) в notebook-демо.

Содержит упрощённый envelope + конструкторы request/response.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

STOP_ACTION = "__stop__"
BROKER_STOP_ACTION = "__stop_broker__"


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def new_trace_id() -> str:
    """Generates a top-level trace identifier."""
    return uuid.uuid4().hex


def new_span_id() -> str:
    """Generates a span identifier for one local step."""
    return uuid.uuid4().hex[:16]


@dataclass(frozen=True)
class Envelope:
    """
    Упрощённый конверт сообщений для ВАБС (broker rotator).

    Брокер маршрутизирует сообщение только по `receiver`.
    Для request дополнительно используется `reply_to`, чтобы получатель
    отправил response в корректную очередь-ответа отправителя.
    """

    sender: str
    receiver: str
    action: str
    payload: Dict[str, Any]
    correlation_id: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    message_type: str  # "request" | "response"
    reply_to: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "action": self.action,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "message_type": self.message_type,
            **({} if self.reply_to is None else {"reply_to": self.reply_to}),
        }


def make_request(
    *,
    sender: str,
    receiver: str,
    action: str,
    payload: Dict[str, Any],
    correlation_id: str,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> Envelope:
    if reply_to is None:
        raise ValueError("reply_to is required for request envelope")
    return Envelope(
        sender=sender,
        receiver=receiver,
        action=action,
        payload=payload,
        correlation_id=correlation_id,
        trace_id=trace_id or new_trace_id(),
        span_id=span_id or new_span_id(),
        parent_span_id=parent_span_id,
        message_type="request",
        reply_to=reply_to,
    )


def make_response(
    *,
    sender: str,
    receiver: str,
    action: str,
    payload: Dict[str, Any],
    correlation_id: str,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
) -> Envelope:
    return Envelope(
        sender=sender,
        receiver=receiver,
        action=action,
        payload=payload,
        correlation_id=correlation_id,
        trace_id=trace_id or new_trace_id(),
        span_id=span_id or new_span_id(),
        parent_span_id=parent_span_id,
        message_type="response",
        reply_to=None,
    )

