from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
MACOS_DIR = REPO_ROOT / "dist" / "macos" / "AI-Team-Room.app" / "Contents" / "MacOS"
SERVER = MACOS_DIR / "AI-Team-Room"
CLIENT = MACOS_DIR / "aitr"
PORT = 18765
CONTROL_TOKEN = "macos-smoke-" + "z" * 40


def request(path: str, *, token: str | None = None, payload: dict | None = None) -> dict | str:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body:
        headers["Content-Type"] = "application/json"
        headers["Origin"] = f"http://127.0.0.1:{PORT}"
    req = Request(f"http://127.0.0.1:{PORT}{path}", data=body, headers=headers)
    with urlopen(req, timeout=2) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if response.headers.get_content_type() == "application/json" else raw


def main() -> int:
    if not SERVER.exists() or not CLIENT.exists():
        raise SystemExit("Build the macOS release before running this smoke test")

    with tempfile.TemporaryDirectory(prefix="ai-team-room-macos-smoke-") as data_dir:
        process = subprocess.Popen(
            [
                str(SERVER),
                "--port", str(PORT),
                "--data-dir", data_dir,
                "--token", CONTROL_TOKEN,
                "--no-browser",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            for _ in range(40):
                try:
                    home = request("/")
                    break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError(f"Frozen server exited with {process.returncode}")
                    time.sleep(0.25)
            else:
                raise RuntimeError("Frozen server did not become ready")

            created = request(
                "/api/meetings",
                token=CONTROL_TOKEN,
                payload={
                    "topic": "macOS app smoke",
                    "participants": ["codex"],
                    "first_speaker": "codex",
                    "max_turns": 2,
                },
            )
            assert isinstance(created, dict)
            join_command = created["join_commands"]["codex"]
            if str(CLIENT.resolve()) not in join_command:
                raise RuntimeError(f"Invitation does not use bundled client: {join_command}")

            client = subprocess.run(
                [
                    str(CLIENT),
                    "--url", f"http://127.0.0.1:{PORT}",
                    "--token", created["invitations"]["codex"],
                    "join",
                ],
                text=True,
                capture_output=True,
                timeout=10,
            )
            if client.returncode != 0 or "protocol" not in client.stdout.lower():
                raise RuntimeError(
                    f"Bundled client failed ({client.returncode}): {client.stdout}{client.stderr}"
                )
            print(json.dumps({
                "server_home_bytes": len(home),
                "join_command_uses_bundled_client": True,
                "bundled_client_exit": client.returncode,
            }, indent=2))
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
