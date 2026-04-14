#!/usr/bin/env python3
"""Minimal proactive messaging service.

Implements:
1) Scheduler: promotes due reminders into an outbox queue.
2) Worker: consumes outbox queue and sends messages through a channel adapter.
3) Telegram assistant loop: receives inbound Telegram messages, acknowledges,
   processes the request, and ALWAYS sends a completion/error follow-up.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional, Protocol

DEFAULT_DB_PATH = os.environ.get("PROACTIVE_DB_PATH", "proactive_messages.db")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(iso_value: str) -> datetime:
    dt = datetime.fromisoformat(iso_value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_completion_message(request_text: str, result: str, error: Optional[str] = None) -> str:
    if error:
        return (
            "No pude completar tu pedido.\n"
            f"Solicitud: {request_text}\n"
            f"Error: {error}"
        )
    return (
        "Listo, terminé tu pedido.\n"
        f"Solicitud: {request_text}\n"
        f"Resultado: {result}"
    )


@dataclass
class Reminder:
    id: int
    user_id: str
    text: str
    trigger_at: str


class Store:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    trigger_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    error TEXT,
                    FOREIGN KEY(reminder_id) REFERENCES reminders(id)
                );

                CREATE INDEX IF NOT EXISTS idx_reminders_trigger_status
                    ON reminders(trigger_at, status);

                CREATE INDEX IF NOT EXISTS idx_outbox_status
                    ON outbox(status, created_at);
                """
            )

    def add_reminder(self, user_id: str, text: str, trigger_at_iso: str) -> int:
        trigger_at = parse_iso(trigger_at_iso).replace(microsecond=0).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO reminders(user_id, text, trigger_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, text, trigger_at, utc_now_iso()),
            )
            return int(cur.lastrowid)

    def enqueue_due_reminders(self, now_iso: str) -> int:
        with self._connect() as conn:
            due_rows = conn.execute(
                """
                SELECT id, user_id, text FROM reminders
                WHERE status = 'pending' AND trigger_at <= ?
                ORDER BY trigger_at ASC
                """,
                (now_iso,),
            ).fetchall()

            for row in due_rows:
                payload = json.dumps({"text": row["text"]}, ensure_ascii=False)
                conn.execute(
                    """
                    INSERT INTO outbox(reminder_id, user_id, payload, status, created_at)
                    VALUES (?, ?, ?, 'queued', ?)
                    """,
                    (row["id"], row["user_id"], payload, utc_now_iso()),
                )
                conn.execute("UPDATE reminders SET status='enqueued' WHERE id=?", (row["id"],))
        return len(due_rows)

    def pop_queued_messages(self, limit: int = 50) -> Iterable[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, reminder_id, user_id, payload
                FROM outbox
                WHERE status='queued'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            for row in rows:
                conn.execute("UPDATE outbox SET status='sending' WHERE id=?", (row["id"],))
        return rows

    def mark_sent(self, outbox_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE outbox SET status='sent', sent_at=?, error=NULL WHERE id=?",
                (utc_now_iso(), outbox_id),
            )

    def mark_failed(self, outbox_id: int, error: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE outbox SET status='failed', error=? WHERE id=?", (error, outbox_id))


class ChannelAdapter(Protocol):
    def send(self, user_id: str, payload: dict) -> None:
        ...


class StdoutChannelAdapter:
    def send(self, user_id: str, payload: dict) -> None:
        text = payload.get("text", "")
        print(f"[SEND] user={user_id} text={text}")


class TelegramChannelAdapter:
    """Sends and receives messages through Telegram Bot API."""

    def __init__(self, bot_token: str, timeout_seconds: int = 20):
        if not bot_token:
            raise ValueError("Telegram token is required for telegram channel")
        self.bot_token = bot_token
        self.timeout_seconds = timeout_seconds

    def _request(self, method: str, payload: Optional[dict] = None) -> dict:
        payload = payload or {}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url=f"https://api.telegram.org/bot{self.bot_token}/{method}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
                if not data.get("ok", False):
                    raise RuntimeError(f"Telegram API error: {data}")
                return data
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Telegram HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Telegram connection error: {exc}") from exc

    def send(self, user_id: str, payload: dict) -> None:
        text = payload.get("text", "")
        self._request("sendMessage", {"chat_id": user_id, "text": text})

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> list[dict]:
        req_payload = {"timeout": timeout}
        if offset is not None:
            req_payload["offset"] = offset
        data = self._request("getUpdates", req_payload)
        return data.get("result", [])


class Scheduler:
    def __init__(self, store: Store):
        self.store = store

    def run_once(self, now: Optional[datetime] = None) -> int:
        current = (now or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
        return self.store.enqueue_due_reminders(current)


class Worker:
    def __init__(self, store: Store, channel: ChannelAdapter):
        self.store = store
        self.channel = channel

    def run_once(self, batch_size: int = 50) -> int:
        rows = list(self.store.pop_queued_messages(limit=batch_size))
        for row in rows:
            try:
                payload = json.loads(row["payload"])
                self.channel.send(row["user_id"], payload)
                self.store.mark_sent(row["id"])
            except Exception as exc:  # noqa: BLE001
                self.store.mark_failed(row["id"], str(exc))
        return len(rows)


class TelegramAssistantLoop:
    """Inbound loop to avoid the "me pongo con eso y no responde más" issue.

    For every inbound text message:
    1) sends immediate ack
    2) processes request
    3) ALWAYS sends completion/failure message
    """

    def __init__(self, telegram: TelegramChannelAdapter, command_timeout: int = 120):
        self.telegram = telegram
        self.command_timeout = command_timeout

    def process_request(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("/run "):
            cmd = stripped[5:].strip()
            if not cmd:
                return "No se recibió comando para ejecutar."
            completed = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.command_timeout,
            )
            out = (completed.stdout or "").strip()
            err = (completed.stderr or "").strip()
            status = f"exit_code={completed.returncode}"
            details = "\n".join(part for part in [out, err] if part)
            details = details[:3000] if details else "(sin salida)"
            return f"{status}\n{details}"

        return (
            "Recibí tu solicitud. Para ejecución de comandos usa:\n"
            "`/run <comando>`\n"
            "Ejemplo: `/run git status --short`"
        )

    def run_forever(self, poll_timeout: int = 30, idle_sleep: float = 1.0) -> None:
        offset: Optional[int] = None
        while True:
            updates = self.telegram.get_updates(offset=offset, timeout=poll_timeout)
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                text = message.get("text", "")
                if not chat_id or not text:
                    continue

                self.telegram.send(str(chat_id), {"text": "Me pongo con eso 👌"})
                try:
                    result = self.process_request(text)
                    completion = build_completion_message(text, result)
                except Exception as exc:  # noqa: BLE001
                    completion = build_completion_message(text, result="", error=str(exc))
                self.telegram.send(str(chat_id), {"text": completion})

            if not updates:
                time.sleep(idle_sleep)


def build_channel_adapter(channel: str, telegram_token: str) -> ChannelAdapter:
    if channel == "stdout":
        return StdoutChannelAdapter()
    if channel == "telegram":
        return TelegramChannelAdapter(telegram_token)
    raise ValueError(f"Unsupported channel: {channel}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Proactive messaging service")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite DB path")
    parser.add_argument("--channel", choices=["stdout", "telegram"], default="stdout")
    parser.add_argument(
        "--telegram-token",
        default=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        help="Telegram bot token (or TELEGRAM_BOT_TOKEN env)",
    )

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="Initialize schema")

    add = sub.add_parser("add-reminder", help="Create a proactive reminder")
    add.add_argument("--user", required=True, help="Destination id. For Telegram: chat_id")
    add.add_argument("--text", required=True)
    add.add_argument("--at", required=True, help="ISO datetime. Example: 2026-04-14T14:30:00+00:00")

    sub.add_parser("run-scheduler-once", help="Move due reminders to outbox")
    loop_s = sub.add_parser("run-scheduler", help="Run scheduler loop")
    loop_s.add_argument("--interval", type=int, default=10, help="Seconds")

    sub.add_parser("run-worker-once", help="Send queued messages")
    loop_w = sub.add_parser("run-worker", help="Run worker loop")
    loop_w.add_argument("--interval", type=int, default=5, help="Seconds")

    tg_assistant = sub.add_parser("run-telegram-assistant", help="Poll Telegram and reply with completion")
    tg_assistant.add_argument("--poll-timeout", type=int, default=30)
    tg_assistant.add_argument("--command-timeout", type=int, default=120)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store = Store(args.db)

    if args.command == "init-db":
        store.init_db()
        print("Schema initialized")
        return

    if args.command == "add-reminder":
        reminder_id = store.add_reminder(args.user, args.text, args.at)
        print(f"Reminder created: {reminder_id}")
        return

    if args.command in {"run-scheduler-once", "run-scheduler"}:
        scheduler = Scheduler(store)
        if args.command == "run-scheduler-once":
            moved = scheduler.run_once()
            print(f"Enqueued reminders: {moved}")
            return

        while True:
            moved = scheduler.run_once()
            print(f"Enqueued reminders: {moved}")
            time.sleep(args.interval)

    if args.command in {"run-worker-once", "run-worker"}:
        channel = build_channel_adapter(args.channel, args.telegram_token)
        worker = Worker(store, channel)
        if args.command == "run-worker-once":
            processed = worker.run_once()
            print(f"Processed outbox messages: {processed}")
            return

        while True:
            processed = worker.run_once()
            print(f"Processed outbox messages: {processed}")
            time.sleep(args.interval)

    if args.command == "run-telegram-assistant":
        telegram = TelegramChannelAdapter(args.telegram_token)
        assistant = TelegramAssistantLoop(telegram=telegram, command_timeout=args.command_timeout)
        assistant.run_forever(poll_timeout=args.poll_timeout)


if __name__ == "__main__":
    main()
