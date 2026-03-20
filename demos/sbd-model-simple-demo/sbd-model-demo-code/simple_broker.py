from __future__ import annotations

"""
SimpleBroker — упрощённый in-process брокер для notebook-демо.

Маршрутизация по полю receiver, логирование request/response в stdout и simulation.log.
"""

import sys
import time
from multiprocessing import Process
from queue import Empty
from typing import Any, Dict

from messages import BROKER_STOP_ACTION


class SimpleBroker(Process):
    """
    Читает broker_in_queue, доставляет в очередь получателя,
    ведёт журнал сообщений.
    """

    def __init__(
        self,
        *,
        broker_in_queue: Any,
        log_path: str,
        queues_by_receiver: Dict[str, Any] | None = None,
        poll_sleep_s: float = 0.05,
    ) -> None:
        super().__init__()
        self.broker_in_queue = broker_in_queue
        self.log_path = log_path
        self.queues_by_receiver: Dict[str, Any] = queues_by_receiver or {}
        self.poll_sleep_s = poll_sleep_s

    def register_queue(self, receiver_id: str, queue: Any) -> None:
        """Регистрировать до start() процесса брокера."""
        self.queues_by_receiver[receiver_id] = queue

    def _log_line(self, line: str, *, f) -> None:
        print(line, flush=True)
        f.write(line + "\n")
        f.flush()

    def run(self) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            self._log_line(f"[broker] start pid={self.pid} log={self.log_path}", f=f)

            while True:
                try:
                    msg = self.broker_in_queue.get_nowait()
                except Empty:
                    time.sleep(self.poll_sleep_s)
                    continue

                if msg is None:
                    continue

                action = msg.get("action")
                if action == BROKER_STOP_ACTION:
                    self._log_line("[broker] stop requested", f=f)
                    break

                receiver = msg.get("receiver")
                message_type = msg.get("message_type")
                corr_id = msg.get("correlation_id")
                trace_id = msg.get("trace_id")
                span_id = msg.get("span_id")
                parent_span_id = msg.get("parent_span_id")
                sender = msg.get("sender")
                payload = msg.get("payload")

                if receiver not in self.queues_by_receiver:
                    self._log_line(
                        "[broker] DROP "
                        f"receiver={receiver} type={message_type} action={action} "
                        f"corr={corr_id} trace={trace_id} span={span_id} "
                        f"parent_span={parent_span_id} sender={sender} payload={payload}",
                        f=f,
                    )
                    continue

                dst_q = self.queues_by_receiver[receiver]
                dst_q.put(msg)

                self._log_line(
                    "[broker] "
                    f"{sender}->{receiver} action={action} type={message_type} "
                    f"corr={corr_id} trace={trace_id} span={span_id} "
                    f"parent_span={parent_span_id} payload={payload}",
                    f=f,
                )

        try:
            sys.stdout.flush()
        except Exception:
            pass
