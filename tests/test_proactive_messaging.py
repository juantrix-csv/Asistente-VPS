from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from proactive_messaging import (
    Scheduler,
    Store,
    Worker,
    build_channel_adapter,
    build_completion_message,
)


class FakeChannel:
    def __init__(self):
        self.sent = []

    def send(self, user_id, payload):
        self.sent.append((user_id, payload))


def test_due_reminder_is_enqueued_and_sent(tmp_path: Path):
    db_path = tmp_path / "test.db"
    store = Store(str(db_path))
    store.init_db()

    due_time = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(microsecond=0).isoformat()
    store.add_reminder("user-1", "Hola", due_time)

    scheduler = Scheduler(store)
    assert scheduler.run_once() == 1

    channel = FakeChannel()
    worker = Worker(store, channel)
    assert worker.run_once() == 1
    assert channel.sent == [("user-1", {"text": "Hola"})]


def test_telegram_channel_requires_token():
    with pytest.raises(ValueError):
        build_channel_adapter("telegram", "")


def test_completion_message_reports_error():
    msg = build_completion_message("/run git status", result="", error="timeout")
    assert "No pude completar" in msg
    assert "timeout" in msg
