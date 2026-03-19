import os
from typing import Any, Dict, List

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from systems.operator.src.event_journal.src.analytics_adapter import AnalyticsAdapter
from systems.operator.src.event_journal.src.event_journal import EventJournal


class _EventsHandler(BaseHTTPRequestHandler):
    received_events: List[Dict[str, Any]] = []

    def do_POST(self) -> None:  # type: ignore[override]
        if self.path != "/api/events":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            event = json.loads(body.decode("utf-8"))
        except Exception:
            event = {}
        _EventsHandler.received_events.append(event)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")


@pytest.fixture(scope="module")
def analytics_server():
    server = HTTPServer(("127.0.0.1", 0), _EventsHandler)
    host, port = server.server_address

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://{host}:{port}"

    server.shutdown()


def test_analytics_adapter_sends_event(analytics_server):
    adapter = AnalyticsAdapter(base_url=analytics_server, api_key=None, timeout=2.0)
    _EventsHandler.received_events.clear()

    ok = adapter.send_event({"event_type": "order_received", "severity": "info"})
    assert ok is True

    assert _EventsHandler.received_events, "no events received by test analytics server"
    evt = _EventsHandler.received_events[0]
    assert evt.get("event_type") == "order_received"
    assert evt.get("severity") == "info"

