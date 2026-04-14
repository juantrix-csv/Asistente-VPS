from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from proactive_messaging import (
    Scheduler,
    Store,
    TelegramAssistantLoop,
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


def test_telegram_assistant_maps_status_to_git_status(monkeypatch, tmp_path: Path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class Result:
            returncode = 0
            stdout = "## main...origin/main\n"
            stderr = ""

        return Result()

    monkeypatch.setattr("proactive_messaging.subprocess.run", fake_run)

    assistant = TelegramAssistantLoop(telegram=None, workdir=str(tmp_path))
    result = assistant.process_request("estado")

    assert calls[0][0] == "git status --short --branch"
    assert calls[0][1]["cwd"] == str(tmp_path)
    assert "exit_code=0" in result
    assert "## main...origin/main" in result


def test_telegram_assistant_maps_pull_to_git_pull(monkeypatch, tmp_path: Path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))

        class Result:
            returncode = 0
            stdout = "Already up to date.\n"
            stderr = ""

        return Result()

    monkeypatch.setattr("proactive_messaging.subprocess.run", fake_run)

    assistant = TelegramAssistantLoop(telegram=None, workdir=str(tmp_path))
    result = assistant.process_request("actualizame")

    assert calls[0][0] == "git pull --ff-only"
    assert calls[0][1]["cwd"] == str(tmp_path)
    assert "Already up to date." in result
