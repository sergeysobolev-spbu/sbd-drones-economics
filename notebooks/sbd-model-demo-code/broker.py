from __future__ import annotations

"""
ВАБС (broker rotator) — встроенный аналог брокера сообщений для notebook-демо.

Принимает входные сообщения из одной очереди и роутит их в очередь сущности
по полю `receiver`. Параллельно журналирует каждый request/response в stdout
и в файл `notebooks/simulation.log`.
"""

import sys
import time
from multiprocessing import Process
from queue import Empty
from typing import Any, Dict

from messages import BROKER_STOP_ACTION


class VABSBroker(Process):
    """
    ВАБС: встроенный аналог брокера сообщений.

    - читает сообщения из `broker_in_queue`
    - маршрутизирует их в очереди сущностей по `receiver`
    - журналирует каждый запрос/ответ в stdout и в `simulation.log`
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
        # Важно: вызывать до start() процесса брокера (по аналогии с SecurityMonitor в учебном примере).
        self.queues_by_receiver[receiver_id] = queue

    def _log_line(self, line: str, *, f) -> None:
        # stdout (для видимости в ноутбуке) + файл (для последующего анализа)
        print(line, flush=True)
        f.write(line + "\n")
        f.flush()

    def run(self) -> None:
        # Открываем лог в процессе брокера, чтобы запись не конфликтовала между сущностями.
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
                sender = msg.get("sender")
                payload = msg.get("payload")

                if receiver not in self.queues_by_receiver:
                    self._log_line(
                        f"[broker] DROP receiver={receiver} type={message_type} action={action} corr={corr_id} sender={sender} payload={payload}",
                        f=f,
                    )                    
                    continue

                dst_q = self.queues_by_receiver[receiver]
                dst_q.put(msg)

                self._log_line(
                    f"[broker] |-| {sender}->{receiver} |-| action={action} |-| {message_type} |-| corr={corr_id} |---| payload={payload}",
                    f=f,
                )

        # Явно завершаемся
        try:
            sys.stdout.flush()
        except Exception:
            pass

