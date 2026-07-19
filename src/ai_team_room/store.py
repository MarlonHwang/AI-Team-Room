"""Transactional SQLite state for AI Team Room."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

STATUSES = {"active", "paused", "ended"}
KINDS = {"talk", "question", "evidence", "decision", "system"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Conflict(ValueError):
    pass


class RoomStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            yield db
        finally:
            db.close()

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active','paused','ended')),
                    participants_json TEXT NOT NULL,
                    next_speaker TEXT NOT NULL,
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    max_turns INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    ended_at TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_open_meeting
                    ON meetings((1)) WHERE status IN ('active','paused');
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id TEXT NOT NULL REFERENCES meetings(id),
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('talk','question','evidence','decision','system')),
                    text TEXT NOT NULL,
                    client_id TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(meeting_id, sender, client_id)
                );
                CREATE INDEX IF NOT EXISTS messages_by_meeting ON messages(meeting_id,id);
                CREATE TABLE IF NOT EXISTS presence (
                    meeting_id TEXT NOT NULL REFERENCES meetings(id),
                    participant TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY(meeting_id,participant)
                );
            """)

    @staticmethod
    def _meeting(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        result = dict(row)
        import json
        result["participants"] = json.loads(result.pop("participants_json"))
        return result

    def latest(self) -> dict | None:
        with self.connect() as db:
            return self._meeting(db.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 1").fetchone())

    def get(self, meeting_id: str) -> dict | None:
        with self.connect() as db:
            return self._meeting(db.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone())

    def create(self, topic: str, participants: list[str], first_speaker: str, max_turns: int) -> dict:
        import json
        if not isinstance(topic, str) or not isinstance(participants, list) or not all(isinstance(p, str) for p in participants):
            raise ValueError("topic must be text and participants must be a list of names")
        topic = topic.strip()
        participants = [p.strip().lower() for p in participants]
        if not 1 <= len(topic) <= 8_000:
            raise ValueError("topic must contain 1..8000 characters")
        if not 1 <= len(participants) <= 8 or len(set(participants)) != len(participants):
            raise ValueError("participants must contain 1..8 unique names")
        if any(not p.replace("-", "").replace("_", "").isalnum() or len(p) > 32 for p in participants):
            raise ValueError("participant names must be 1..32 letters, numbers, '-' or '_'")
        if first_speaker not in participants:
            raise ValueError("first_speaker must be a participant")
        if not 1 <= max_turns <= 100:
            raise ValueError("max_turns must be 1..100")
        meeting_id, now = str(uuid.uuid4()), utc_now()
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO meetings VALUES(?,?,'active',?,?,0,?,?,NULL)",
                    (meeting_id, topic, json.dumps(participants), first_speaker, max_turns, now),
                )
                db.execute(
                    "INSERT INTO messages(meeting_id,sender,recipient,kind,text,client_id,created_at) VALUES(?,'human','all','system',?,NULL,?)",
                    (meeting_id, topic, now),
                )
        except sqlite3.IntegrityError as exc:
            raise Conflict("another meeting is already open") from exc
        return self.get(meeting_id)

    def messages(self, meeting_id: str, after: int = 0, limit: int = 500) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM messages WHERE meeting_id=? AND id>? ORDER BY id LIMIT ?",
                (meeting_id, max(0, after), min(max(limit, 1), 1000)),
            ).fetchall()
        return [dict(row) for row in rows]

    def presence(self, meeting_id: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM presence WHERE meeting_id=? ORDER BY participant", (meeting_id,)).fetchall()
        return [dict(row) for row in rows]

    def touch(self, meeting_id: str, participant: str) -> None:
        meeting = self.get(meeting_id)
        if not meeting or participant not in meeting["participants"]:
            raise ValueError("participant is not invited to this meeting")
        with self.connect() as db:
            db.execute(
                "INSERT INTO presence VALUES(?,?,?) ON CONFLICT(meeting_id,participant) DO UPDATE SET last_seen_at=excluded.last_seen_at",
                (meeting_id, participant, utc_now()),
            )

    def send(self, meeting_id: str, sender: str, recipient: str, kind: str, text: str, client_id: str | None) -> tuple[dict, bool]:
        if not all(isinstance(value, str) for value in (meeting_id, sender, recipient, kind, text)):
            raise ValueError("meeting, sender, recipient, kind, and text must be strings")
        if client_id is not None and (not isinstance(client_id, str) or not 1 <= len(client_id) <= 128):
            raise ValueError("client_id must contain 1..128 characters")
        text = text.strip()
        if not 1 <= len(text) <= 20_000:
            raise ValueError("message must contain 1..20000 characters")
        if kind not in KINDS - {"system"}:
            raise ValueError("invalid message kind")
        now = utc_now()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            meeting = self._meeting(db.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone())
            if not meeting:
                db.execute("ROLLBACK")
                raise ValueError("meeting not found")
            allowed = {"human", "all", *meeting["participants"]}
            if sender not in allowed - {"all"} or recipient not in allowed:
                db.execute("ROLLBACK")
                raise ValueError("invalid sender or recipient")
            if client_id:
                old = db.execute(
                    "SELECT * FROM messages WHERE meeting_id=? AND sender=? AND client_id=?",
                    (meeting_id, sender, client_id),
                ).fetchone()
                if old:
                    db.execute("COMMIT")
                    return dict(old), True
            if meeting["status"] == "ended" or (meeting["status"] == "paused" and sender != "human"):
                db.execute("ROLLBACK")
                raise Conflict("meeting is not active")
            if sender != "human" and sender != meeting["next_speaker"]:
                db.execute("ROLLBACK")
                raise Conflict(f"not {sender}'s turn; waiting for {meeting['next_speaker']}")
            cursor = db.execute(
                "INSERT INTO messages(meeting_id,sender,recipient,kind,text,client_id,created_at) VALUES(?,?,?,?,?,?,?)",
                (meeting_id, sender, recipient, kind, text, client_id, now),
            )
            if sender != "human":
                participants = meeting["participants"]
                index = (participants.index(sender) + 1) % len(participants)
                turns = meeting["turn_count"] + 1
                status = "ended" if turns >= meeting["max_turns"] else "active"
                db.execute(
                    "UPDATE meetings SET next_speaker=?,turn_count=?,status=?,ended_at=? WHERE id=?",
                    (participants[index], turns, status, now if status == "ended" else None, meeting_id),
                )
            db.execute("COMMIT")
        return self.message(cursor.lastrowid), False

    def message(self, message_id: int) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
        return dict(row)

    def control(self, meeting_id: str, action: str, next_speaker: str | None = None) -> dict:
        if action not in {"pause", "resume", "end", "pass"}:
            raise ValueError("invalid control action")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            meeting = self._meeting(db.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone())
            if not meeting:
                db.execute("ROLLBACK")
                raise ValueError("meeting not found")
            if action == "pause" and meeting["status"] == "active":
                db.execute("UPDATE meetings SET status='paused' WHERE id=?", (meeting_id,))
            elif action == "resume" and meeting["status"] == "paused":
                db.execute("UPDATE meetings SET status='active' WHERE id=?", (meeting_id,))
            elif action == "end" and meeting["status"] != "ended":
                db.execute("UPDATE meetings SET status='ended',ended_at=? WHERE id=?", (utc_now(), meeting_id))
            elif action == "pass":
                if meeting["status"] == "ended":
                    db.execute("ROLLBACK")
                    raise Conflict("cannot pass an ended meeting")
                if next_speaker not in meeting["participants"]:
                    db.execute("ROLLBACK")
                    raise ValueError("next_speaker must be a participant")
                db.execute("UPDATE meetings SET next_speaker=? WHERE id=?", (next_speaker, meeting_id))
            else:
                db.execute("ROLLBACK")
                raise Conflict(f"cannot {action} a {meeting['status']} meeting")
            db.execute("COMMIT")
        return self.get(meeting_id)

    def state(self, meeting_id: str | None = None, after: int = 0) -> dict:
        meeting = self.get(meeting_id) if meeting_id else self.latest()
        if not meeting:
            return {"meeting": None, "messages": [], "presence": [], "cursor": after}
        messages = self.messages(meeting["id"], after)
        cursor = max([after, *[m["id"] for m in messages]])
        return {"meeting": meeting, "messages": messages, "presence": self.presence(meeting["id"]), "cursor": cursor}
