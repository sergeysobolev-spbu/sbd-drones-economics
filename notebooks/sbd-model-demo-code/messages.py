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
    message_type: str  # "request" | "response"
    reply_to: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "action": self.action,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
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
    reply_to: str,
) -> Envelope:
    return Envelope(
        sender=sender,
        receiver=receiver,
        action=action,
        payload=payload,
        correlation_id=correlation_id,
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
) -> Envelope:
    return Envelope(
        sender=sender,
        receiver=receiver,
        action=action,
        payload=payload,
        correlation_id=correlation_id,
        message_type="response",
        reply_to=None,
    )

