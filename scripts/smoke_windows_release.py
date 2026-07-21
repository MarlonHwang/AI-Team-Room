from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "dist" / "windows" / "AI-Team-Room-Windows-x64"
SERVER = PACKAGE / "AI-Team-Room.exe"
CLIENT = PACKAGE / "aitr.exe"
PORT = 18765
CONTROL_TOKEN = "windows-smoke-" + "z" * 40


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
        raise SystemExit("Build the Windows release before running this smoke test")

    with tempfile.TemporaryDirectory(prefix="ai-team-room-windows-smoke-") as data_dir:
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
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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
                    "topic": "Windows EXE smoke",
                    "participants": ["codex"],
                    "first_speaker": "codex",
                    "max_turns": 2,
                },
            )
            assert isinstance(created, dict)
            join_command = created["join_commands"]["codex"]
            expected_client = str(CLIENT.resolve())
            if expected_client not in join_command:
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
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if client.returncode != 0 or "protocol" not in client.stdout.lower():
                raise RuntimeError(
                    f"Bundled client failed ({client.returncode}): {client.stdout}{client.stderr}"
                )

            result = {
                "server_home_bytes": len(home),
                "join_command_uses_bundled_client": True,
                "bundled_client_exit": client.returncode,
                "server_exe_bytes": SERVER.stat().st_size,
                "client_exe_bytes": CLIENT.stat().st_size,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            if os.name == "nt" and process.poll() is None:
                # A PyInstaller one-file executable has a bootloader parent and
                # an application child. Terminating only the parent can leave
                # the child serving the port, so stop the complete test tree.
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            elif process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
