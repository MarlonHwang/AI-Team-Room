from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ai_team_room import cli


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state_patch = patch.dict(
            "os.environ", {"AI_TEAM_ROOM_STATE_DIR": self.temp.name}, clear=False
        )
        self.state_patch.start()
        self.base = "http://127.0.0.1:8765"
        self.token = "participant-token"

    def tearDown(self):
        self.state_patch.stop()
        self.temp.cleanup()

    def run_cli(self, command: list[str], response: dict):
        stdout = io.StringIO()
        argv = ["aitr", "--url", self.base, "--token", self.token, *command]
        with (
            patch.object(sys, "argv", argv),
            patch("ai_team_room.cli.request_json", return_value=response) as request,
            redirect_stdout(stdout),
        ):
            self.assertEqual(cli.main(), 0)
        return request, stdout.getvalue()

    def test_join_saves_cursor_and_wait_reuses_it(self):
        self.run_cli(
            ["join"],
            {"ok": True, "meeting": {"status": "active"}, "messages": [], "cursor": 7},
        )
        request, _ = self.run_cli(
            ["wait"],
            {"ok": True, "meeting": {"status": "active"}, "messages": [], "cursor": 9},
        )
        self.assertIn("after=7", request.call_args.args[0])
        self.assertEqual(cli._load_cursor(self.base, self.token), 9)

    def test_send_reads_utf8_text_file_and_advances_cursor(self):
        message_file = Path(self.temp.name) / "message.txt"
        message_file.write_text('한글과 "큰따옴표"', encoding="utf-8")
        request, _ = self.run_cli(
            ["send", "--text-file", str(message_file), "--recipient", "codex"],
            {"ok": True, "message": {"id": 12}, "duplicate": False},
        )
        self.assertEqual(request.call_args.args[2], "POST")
        self.assertEqual(request.call_args.args[3]["text"], '한글과 "큰따옴표"')
        self.assertEqual(request.call_args.args[3]["recipient"], "codex")
        self.assertEqual(cli._load_cursor(self.base, self.token), 12)

    def test_leave_clears_saved_cursor(self):
        cli._save_cursor(self.base, self.token, 5)
        request, _ = self.run_cli(["leave"], {"ok": True, "left": "codex"})
        self.assertEqual(request.call_args.args[:3], (f"{self.base}/api/leave", self.token, "POST"))
        self.assertIsNone(cli._load_cursor(self.base, self.token))


if __name__ == "__main__":
    unittest.main()
