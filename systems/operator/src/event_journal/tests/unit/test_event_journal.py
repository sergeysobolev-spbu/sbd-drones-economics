from systems.operator.src.event_journal.src.event_journal import EventJournal
from systems.operator.src.topics import ComponentTopics


class DummyBus:
    def __init__(self) -> None:
        self.published = []

    def publish(self, topic, message):
        self.published.append((topic, message))


def test_event_journal_accepts_event_and_returns_status():
    bus = DummyBus()
    journal = EventJournal("events-test", bus)

    msg = {
        "action": "emit_event",
        "sender": "pytest",
        "payload": {
            "event_type": "order_received",
            "severity": "info",
            "source_component": "operator_system",
        },
    }

    resp = journal._handle_emit_event(msg)  # type: ignore[attr-defined]
    assert resp is not None
    assert resp["status"] == "accepted"
    assert resp["event_type"] == "order_received"


def test_component_topics_event_journal():
    topic = ComponentTopics.get_event_journal()
    assert ".event_journal" in topic
