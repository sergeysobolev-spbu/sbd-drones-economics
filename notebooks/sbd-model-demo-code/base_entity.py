from __future__ import annotations

import time
from multiprocessing import Process
from typing import Any, Dict, Optional

"""
Базовый класс для сущностей в notebook-демо.

Используется для единообразной обработки request-сообщений и RPC через reply_queue.
"""

from messages import STOP_ACTION, make_request, make_response, new_correlation_id


class BaseEntity(Process):
    """
    Базовый класс сущности.

    - читает request-сообщения из `inbox_queue`
    - обработка request реализуется в `handle_request()`
    - RPC-взаимодействие реализовано через ожидание response в `reply_queue`
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

    # --- Process entrypoint ---
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

            try:
                self.handle_request(msg)
            except Exception as e:  # noqa: BLE001
                # В демо — отправляем ошибку как response, чтобы оркестратор мог завершить сценарий.
                corr_id = msg.get("correlation_id") or new_correlation_id()
                receiver = msg.get("reply_to")  # where to deliver response
                if receiver is not None:
                    err = {"status": "error", "error": str(e), "type": type(e).__name__}
                    response = make_response(
                        sender=self.entity_id,
                        receiver=receiver,
                        action=msg.get("action", "unknown_action"),
                        payload=err,
                        correlation_id=corr_id,
                    )
                    self.broker_in_queue.put(response.to_dict())

    # --- to be overridden ---
    def handle_request(self, msg: Dict[str, Any]) -> None:
        raise NotImplementedError

    # --- RPC helpers ---
    def send_request(
        self,
        *,
        receiver: str,
        action: str,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> str:
        corr_id = correlation_id or new_correlation_id()
        request = make_request(
            sender=self.entity_id,
            receiver=receiver,
            action=action,
            payload=payload,
            correlation_id=corr_id,
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
    ) -> Dict[str, Any]:
        corr_id = self.send_request(receiver=receiver, action=action, payload=payload)
        return self.wait_for_response(
            correlation_id=corr_id,
            timeout_s=timeout_s,
            expected_sender=expected_sender,
        )

