"""Cooperative client used by an already-open AI coding session."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import __version__

PROTOCOL = """You are the already-open work session, not a replacement process. Keep your existing context, tools, workspace, and permission rules. Follow `wait` -> investigate/work -> `send` -> `wait` until the meeting ends; the CLI remembers your cursor after `join`, `wait`, and `send`. The configured first speaker sends the opening AI response. After that, next_speaker is `all`: there is no turn rotation, and any participant may send when a new message merits a response. Do not send empty acknowledgements or create reply loops; after contributing, wait for new room activity. A wait lasts at most 30 seconds, and a timeout is not the end. Meetings end only when the human ends them. Use `send --text-file PATH` for long or non-ASCII messages. If the human explicitly releases you before the meeting ends, run `leave` and stop. Never claim a search, file read, test, or experiment unless you performed it in this actual session. Joining does not authorize writes, paid compute, destructive actions, commits, pushes, or broader permissions."""


def _cursor_file(base: str, token: str) -> Path:
    override = os.environ.get("AI_TEAM_ROOM_STATE_DIR")
    if override:
        root = Path(override)
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "AI-Team-Room"
    else:
        root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "ai-team-room"
    key = hashlib.sha256(f"{base}\0{token}".encode("utf-8")).hexdigest()
    return root / "cursors" / f"{key}.txt"


def _load_cursor(base: str, token: str) -> int | None:
    try:
        value = int(_cursor_file(base, token).read_text(encoding="ascii").strip())
        return value if value >= 0 else None
    except (OSError, ValueError):
        return None


def _save_cursor(base: str, token: str, cursor: int) -> None:
    if not isinstance(cursor, int) or cursor < 0:
        return
    path = _cursor_file(base, token)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(str(cursor), encoding="ascii")
        temporary.replace(path)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _clear_cursor(base: str, token: str) -> None:
    try:
        _cursor_file(base, token).unlink(missing_ok=True)
    except OSError:
        pass


def request_json(url: str, token: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, method=method, headers={"Authorization": f"Bearer {token}"})
    if body is not None:
        request.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"room returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"meeting room is unavailable: {exc.reason}") from exc


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"AI Team Room {__version__} — Madoro Studio")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--token", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("join")
    wait = sub.add_parser("wait")
    wait.add_argument("--after", "--cursor", dest="after", type=int, help="exclusive cursor override (normally remembered automatically)")
    wait.add_argument("--timeout", type=float, default=25, help="long-poll seconds; the server caps each wait at 30")
    send = sub.add_parser("send")
    text_source = send.add_mutually_exclusive_group()
    text_source.add_argument("--text")
    text_source.add_argument("--text-file", help="read the message as UTF-8 from this file")
    send.add_argument("--recipient", default="all")
    send.add_argument("--kind", choices=("talk", "question", "evidence", "decision"), default="talk")
    send.add_argument("--client-id", default=None)
    sub.add_parser("leave")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    if args.command == "join":
        result = request_json(f"{base}/api/state", args.token)
        result["protocol"] = PROTOCOL
        _save_cursor(base, args.token, result.get("cursor"))
    elif args.command == "wait":
        after = args.after if args.after is not None else _load_cursor(base, args.token)
        if after is None:
            parser.error("no saved cursor; run join first or provide --after")
        query = urlencode({"after": after, "timeout": args.timeout})
        result = request_json(f"{base}/api/wait?{query}", args.token)
        _save_cursor(base, args.token, result.get("cursor"))
    elif args.command == "leave":
        result = request_json(f"{base}/api/leave", args.token, "POST", {})
        _clear_cursor(base, args.token)
    else:
        text = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else args.text if args.text is not None else sys.stdin.read()
        result = request_json(
            f"{base}/api/messages", args.token, "POST",
            {"text": text, "recipient": args.recipient, "kind": args.kind, "client_id": args.client_id or str(uuid.uuid4())},
        )
        message = result.get("message") or {}
        _save_cursor(base, args.token, message.get("id"))
    meeting = result.get("meeting")
    if meeting:
        # Identity is intentionally not decoded client-side. Messages remain complete on join.
        result["event"] = "ended" if meeting["status"] == "ended" else result.get("event", "state")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
