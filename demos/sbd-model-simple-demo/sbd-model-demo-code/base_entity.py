from __future__ import annotations

"""
Базовый класс для сущностей в notebook-демо.

Обработка входящих request: диспетчеризация по полю action на зарегистрированные
обработчики (минимум шаблонного кода в наследниках).
"""

import time
from multiprocessing import Process
from typing import Any, Callable, Dict, Optional

from messages import (
    STOP_ACTION,
    make_request,
    make_response,
    new_correlation_id,
    new_span_id,
    new_trace_id,
)

Handler = Callable[[Dict[str, Any]], None]


class BaseEntity(Process):
    """
    Базовый класс сущности.

    - читает request из inbox_queue
    - для каждого action вызывает зарегистрированный обработчик
    - RPC через reply_queue / send_request / rpc_send_wait
    """

    def __init__(
        self,
        *,
        entity_id: str,
        inbox_queue: Any,
        broker_in_queue: Any,
        reply_queue: Any,
        reply_queue_name: str,
        world: Dict[str, Any],
        actions: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__()
        self.entity_id = entity_id
        self.inbox_queue = inbox_queue
        self.broker_in_queue = broker_in_queue
        self.reply_queue = reply_queue
        self.reply_queue_name = reply_queue_name
        self.world = world
        self.actions = actions or {}
        self._handlers: Dict[str, Handler] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Переопределяется в наследниках: вызовы register_handler(...)."""

    def register_handler(self, action: str, handler: Handler) -> None:
        """Регистрирует обработчик для строкового action."""
        self._handlers[action] = handler

    def _default_unknown_action(self, msg: Dict[str, Any]) -> None:
        """Ответ при неизвестном action (если не переопределено)."""
        self.send_response(
            request_msg=msg,
            payload={"status": "error", "error": "unknown_action"},
        )

    def run(self) -> None:
        while True:
            msg_raw = self.inbox_queue.get()
            if msg_raw is None or not isinstance(msg_raw, dict):
                continue

            msg = msg_raw

            if msg.get("action") == STOP_ACTION:
                break

            if msg.get("message_type") != "request":
                continue

            action = msg.get("action")
            handler = self._handlers.get(action, self._default_unknown_action)

            try:
                handler(msg)
            except Exception as e:  # noqa: BLE001
                corr_id = msg.get("correlation_id") or new_correlation_id()
                receiver = msg.get("reply_to")
                if receiver is not None:
                    err = {"status": "error", "error": str(e), "type": type(e).__name__}
                    response = make_response(
                        sender=self.entity_id,
                        receiver=receiver,
                        action=msg.get("action", "unknown_action"),
                        payload=err,
                        correlation_id=corr_id,
                        trace_id=msg.get("trace_id", new_trace_id()),
                        span_id=new_span_id(),
                        parent_span_id=msg.get("span_id"),
                    )
                    self.broker_in_queue.put(response.to_dict())

    def send_request(
        self,
        *,
        receiver: str,
        action: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> str:
        corr_id = correlation_id or new_correlation_id()
        request = make_request(
            sender=self.entity_id,
            receiver=receiver,
            action=action,
            payload=payload,
            correlation_id=corr_id,
            trace_id=trace_id or new_trace_id(),
            span_id=new_span_id(),
            parent_span_id=parent_span_id,
            reply_to=self.reply_queue_name,
        )
        self.broker_in_queue.put(request.to_dict())
        return corr_id

    def wait_for_response(
        self,
        *,
        correlation_id: str,
        timeout_s: float,
        expected_sender: Optional[str] = None,
    ) -> Dict[str, Any]:
        deadline = time.time() + timeout_s
        stash = []
        try:
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    raise TimeoutError(
                        f"[{self.entity_id}] timeout waiting response corr={correlation_id} "
                        f"expected_sender={expected_sender}"
                    )

                try:
                    resp_raw = self.reply_queue.get(timeout=min(0.5, remaining))
                except Exception:
                    continue

                resp: Dict[str, Any] = resp_raw
                if resp.get("correlation_id") != correlation_id:
                    stash.append(resp_raw)
                    continue

                if expected_sender is not None and resp.get("sender") != expected_sender:
                    stash.append(resp_raw)
                    continue

                return resp.get("payload", {})
        finally:
            for item in stash:
                self.reply_queue.put(item)

    def send_response(self, *, request_msg: Dict[str, Any], payload: Dict[str, Any]) -> None:
        receiver = request_msg.get("reply_to")
        corr_id = request_msg.get("correlation_id")
        if receiver is None or corr_id is None:
            return

        response = make_response(
            sender=self.entity_id,
            receiver=receiver,
            action=request_msg.get("action", "unknown_action"),
            payload=payload,
            correlation_id=corr_id,
            trace_id=request_msg.get("trace_id", new_trace_id()),
            span_id=new_span_id(),
            parent_span_id=request_msg.get("span_id"),
        )
        self.broker_in_queue.put(response.to_dict())

    def rpc_send_wait(
        self,
        *,
        receiver: str,
        action: str,
        payload: Dict[str, Any],
        timeout_s: float = 30.0,
        expected_sender: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        corr_id = self.send_request(
            receiver=receiver,
            action=action,
            payload=payload,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
        return self.wait_for_response(
            correlation_id=corr_id,
            timeout_s=timeout_s,
            expected_sender=expected_sender,
        )
