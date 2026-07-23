"""Local HTTP server and browser UI for AI Team Room."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shlex
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PureWindowsPath
from urllib.parse import parse_qs, urlparse

from . import __version__
from .auth import TokenSigner, random_token
from .store import Conflict, RoomStore

MAX_REQUEST = 64_000
WEB_DIR = Path(__file__).resolve().parent / "web"


class RoomApp:
    def __init__(self, store: RoomStore, control_token: str, base_url: str = "http://127.0.0.1:8765"):
        self.store = store
        self.control_token = control_token
        self.base_url = base_url.rstrip("/")
        self.signer = TokenSigner(control_token)
        self._invitation_cache: dict[str, dict[str, str]] = {}
        self.changed = threading.Condition()

    def notify(self) -> None:
        with self.changed:
            self.changed.notify_all()

    def identity(self, bearer: str) -> dict:
        if not bearer:
            raise PermissionError("missing bearer token")
        if bearer == self.control_token:
            return {"role": "control", "participant": "human", "meeting": None}
        payload = self.signer.verify(bearer)
        return {"role": "participant", **payload}

    def invitations(self, meeting: dict) -> dict[str, str]:
        cached = self._invitation_cache.get(meeting["id"])
        if cached is None or set(cached) != set(meeting["participants"]):
            cached = {name: self.signer.issue(meeting["id"], name) for name in meeting["participants"]}
            self._invitation_cache[meeting["id"]] = cached
        return dict(cached)

    def join_command(self, token: str) -> str:
        if getattr(sys, "frozen", False):
            # Frozen releases ship the participant client beside the server
            # executable. sys.executable is the server itself in that case,
            # so invoking it with `-m ai_team_room.cli` would restart the room.
            client_name = "aitr.exe" if os.name == "nt" else "aitr"
            if os.name == "nt":
                # PureWindowsPath keeps this branch testable on non-Windows
                # runners and avoids instantiating WindowsPath on POSIX.
                client = str(PureWindowsPath(sys.executable).with_name(client_name))
                quoted_client = client.replace("'", "''")
                return (
                    f"& '{quoted_client}' --url {self.base_url} "
                    f"--token {token} join"
                )
            client = str(Path(sys.executable).resolve().with_name(client_name))
            return (
                f"{shlex.quote(client)} --url {shlex.quote(self.base_url)} "
                f"--token {shlex.quote(token)} join"
            )
        source_root = str(Path(__file__).resolve().parents[1])
        if os.name == "nt":
            root = source_root.replace("'", "''")
            python = sys.executable.replace("'", "''")
            return (
                f"$env:PYTHONPATH='{root}'; & '{python}' -m ai_team_room.cli "
                f"--url {self.base_url} --token {token} join"
            )
        return (
            f"PYTHONPATH={shlex.quote(source_root)} {shlex.quote(sys.executable)} "
            f"-m ai_team_room.cli --url {shlex.quote(self.base_url)} --token {shlex.quote(token)} join"
        )

    def invitation_bundle(self, meeting: dict) -> tuple[dict[str, str], dict[str, str]]:
        invitations = self.invitations(meeting)
        return invitations, {name: self.join_command(token) for name, token in invitations.items()}

    @staticmethod
    def visible_state(state: dict, identity: dict) -> dict:
        if identity["role"] == "participant":
            name = identity["participant"]
            state["messages"] = [
                message for message in state["messages"]
                if message["recipient"] in {"all", name} or message["sender"] == name
            ]
        return state

    def wait_state(self, meeting_id: str, after: int, timeout: float, participant: str | None = None) -> dict:
        deadline = time.monotonic() + min(max(timeout, 0), 30)
        with self.changed:
            while True:
                state = self.store.state(meeting_id, after)
                if participant and state["meeting"] and state["meeting"]["next_speaker"] == participant:
                    state["event"] = "your_turn"
                    return state
                if state["messages"] or not state["meeting"] or state["meeting"]["status"] != "active":
                    return state
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    state["event"] = "timeout"
                    return state
                self.changed.wait(min(remaining, 5))


def handler_factory(app: RoomApp, allowed_origins: set[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AITeamRoom/0.1"

        def log_message(self, fmt: str, *args) -> None:
            print(f"[{self.log_date_time_string()}] {fmt % args}")

        def json(self, payload: dict, status: int = 200) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'")
            self.end_headers()
            self.wfile.write(raw)

        def error_json(self, status: int, message: str) -> None:
            self.json({"ok": False, "error": message}, status)

        def body(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if length < 0 or length > MAX_REQUEST:
                raise ValueError("request body is too large")
            value = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(value, dict):
                raise ValueError("request must be a JSON object")
            return value

        def bearer(self) -> str:
            header = self.headers.get("Authorization", "")
            return header[7:] if header.startswith("Bearer ") else ""

        def auth(self) -> dict:
            return app.identity(self.bearer())

        def require_control(self) -> dict:
            identity = self.auth()
            if identity["role"] != "control":
                raise PermissionError("control token required")
            return identity

        def check_origin(self) -> None:
            origin = self.headers.get("Origin")
            if origin is not None and origin not in allowed_origins:
                raise PermissionError("origin is not allowed")

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/state":
                    identity = self.auth()
                    query = parse_qs(parsed.query)
                    meeting_id = query.get("meeting", [None])[0]
                    if identity["role"] == "participant":
                        meeting_id = identity["meeting"]
                        app.store.touch(meeting_id, identity["participant"])
                    state = app.visible_state(app.store.state(meeting_id), identity)
                    if identity["role"] == "participant":
                        state["you"] = identity["participant"]
                        if state["meeting"] and state["meeting"]["next_speaker"] == identity["participant"]:
                            state["event"] = "your_turn"
                    if identity["role"] == "control" and state["meeting"]:
                        state["invitations"], state["join_commands"] = app.invitation_bundle(state["meeting"])
                    self.json({"ok": True, **state})
                    return
                if parsed.path == "/api/wait":
                    identity = self.auth()
                    query = parse_qs(parsed.query)
                    after = int(query.get("after", ["0"])[0])
                    timeout = float(query.get("timeout", ["25"])[0])
                    meeting_id = query.get("meeting", [None])[0]
                    if identity["role"] == "participant":
                        meeting_id = identity["meeting"]
                        app.store.touch(meeting_id, identity["participant"])
                    if not meeting_id:
                        latest = app.store.latest()
                        meeting_id = latest["id"] if latest else ""
                    participant = identity["participant"] if identity["role"] == "participant" else None
                    state = app.visible_state(app.wait_state(meeting_id, after, timeout, participant), identity)
                    if participant:
                        state["you"] = participant
                    self.json({"ok": True, **state})
                    return
                relative = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
                candidate = (WEB_DIR / relative).resolve()
                if WEB_DIR.resolve() not in candidate.parents and candidate != WEB_DIR.resolve():
                    self.send_error(404)
                    return
                if not candidate.is_file():
                    self.send_error(404)
                    return
                body = candidate.read_bytes()
                content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
                if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
                    content_type += "; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'")
                self.end_headers()
                self.wfile.write(body)
            except PermissionError as exc:
                self.error_json(401, str(exc))
            except (ValueError, json.JSONDecodeError) as exc:
                self.error_json(400, str(exc))

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                self.check_origin()
                identity = self.auth()
                data = self.body()
                if parsed.path == "/api/meetings":
                    self.require_control()
                    meeting = app.store.create(
                        data.get("topic", ""), data.get("participants", ["claude", "codex"]),
                        data.get("first_speaker", "claude"), int(data.get("max_turns", 20)),
                    )
                    app.notify()
                    invitations, commands = app.invitation_bundle(meeting)
                    self.json({"ok": True, "meeting": meeting, "invitations": invitations, "join_commands": commands}, 201)
                    return
                if parsed.path == "/api/messages":
                    if identity["role"] == "control":
                        meeting_id = data.get("meeting_id") or (app.store.latest() or {}).get("id")
                        sender = "human"
                    else:
                        meeting_id, sender = identity["meeting"], identity["participant"]
                        app.store.touch(meeting_id, sender)
                        if data.get("sender") and data["sender"] != sender:
                            raise PermissionError("participant token does not match sender")
                    if not meeting_id:
                        raise ValueError("meeting_id is required")
                    message, duplicate = app.store.send(
                        meeting_id, sender, data.get("recipient", "all"), data.get("kind", "talk"),
                        data.get("text", ""), data.get("client_id"),
                    )
                    app.notify()
                    self.json({"ok": True, "message": message, "duplicate": duplicate}, 200 if duplicate else 201)
                    return
                if parsed.path == "/api/leave":
                    if identity["role"] != "participant":
                        raise PermissionError("participant token required")
                    app.store.leave(identity["meeting"], identity["participant"])
                    app.notify()
                    self.json({"ok": True, "left": identity["participant"]})
                    return
                if parsed.path == "/api/control":
                    self.require_control()
                    meeting_id = data.get("meeting_id") or (app.store.latest() or {}).get("id")
                    if not meeting_id:
                        raise ValueError("meeting_id is required")
                    meeting = app.store.control(meeting_id, data.get("action", ""))
                    app.notify()
                    self.json({"ok": True, "meeting": meeting})
                    return
                self.error_json(404, "not found")
            except PermissionError as exc:
                self.error_json(401, str(exc))
            except Conflict as exc:
                self.error_json(409, str(exc))
            except (ValueError, json.JSONDecodeError) as exc:
                self.error_json(400, str(exc))
            except Exception as exc:
                self.error_json(500, f"{type(exc).__name__}: {exc}")

    return Handler


def data_dir() -> Path:
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AITeamRoom"
    return Path.home() / ".local" / "share" / "ai-team-room"


def load_control_token(directory: Path, override: str | None) -> str:
    if override:
        if len(override) < 32:
            raise ValueError("--token must contain at least 32 characters")
        return override
    path = directory / "control-token"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    token = random_token()
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(token, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=data_dir())
    parser.add_argument("--token", help="persistent control token (32+ characters)")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_network:
        parser.error("non-loopback binding requires --allow-network; read SECURITY.md first")
    directory = args.data_dir.resolve()
    token = load_control_token(directory, args.token)
    base_url = f"http://{args.host}:{args.port}"
    app = RoomApp(RoomStore(directory / "room.sqlite3"), token, base_url)
    origins = {f"http://{args.host}:{args.port}", f"http://localhost:{args.port}", f"http://127.0.0.1:{args.port}"}
    server = ThreadingHTTPServer((args.host, args.port), handler_factory(app, origins))
    url = f"{base_url}/#token={token}"
    print(f"AI Team Room {__version__} — Madoro Studio")
    print(f"Control room: {url}")
    print(f"Data: {directory}")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        print("Stopping AI Team Room")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
