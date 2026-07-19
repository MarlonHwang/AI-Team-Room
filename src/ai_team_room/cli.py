"""Cooperative client used by an already-open AI coding session."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROTOCOL = """You are the already-open work session, not a replacement process. Keep your existing context, tools, workspace, and permission rules. Follow wait -> investigate/work -> send -> wait until the meeting ends. Only send an ordinary message when next_speaker equals your participant name. A timeout is not the end. Never claim a search, file read, test, or experiment unless you performed it in this actual session. Joining does not authorize writes, paid compute, destructive actions, commits, pushes, or broader permissions."""


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
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--token", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("join")
    wait = sub.add_parser("wait")
    wait.add_argument("--after", type=int, required=True)
    wait.add_argument("--timeout", type=float, default=25)
    send = sub.add_parser("send")
    send.add_argument("--text")
    send.add_argument("--recipient", default="all")
    send.add_argument("--kind", choices=("talk", "question", "evidence", "decision"), default="talk")
    send.add_argument("--client-id", default=None)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    if args.command == "join":
        result = request_json(f"{base}/api/state", args.token)
        result["protocol"] = PROTOCOL
    elif args.command == "wait":
        query = urlencode({"after": args.after, "timeout": args.timeout})
        result = request_json(f"{base}/api/wait?{query}", args.token)
    else:
        text = args.text if args.text is not None else sys.stdin.read()
        result = request_json(
            f"{base}/api/messages", args.token, "POST",
            {"text": text, "recipient": args.recipient, "kind": args.kind, "client_id": args.client_id or str(uuid.uuid4())},
        )
    meeting = result.get("meeting")
    if meeting:
        # Identity is intentionally not decoded client-side. Messages remain complete on join.
        result["event"] = "ended" if meeting["status"] == "ended" else result.get("event", "state")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
