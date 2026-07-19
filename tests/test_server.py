from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ai_team_room.server import RoomApp, handler_factory
from ai_team_room.store import RoomStore


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.control = "control-" + "z" * 40
        self.app = RoomApp(RoomStore(Path(self.temp.name) / "room.sqlite3"), self.control)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(self.app, set()))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
        self.temp.cleanup()

    def request(self, path, token=None, method="GET", payload=None, origin=None):
        body = None if payload is None else json.dumps(payload).encode()
        headers = {}
        if token: headers["Authorization"] = f"Bearer {token}"
        if body: headers["Content-Type"] = "application/json"
        if origin: headers["Origin"] = origin
        request = Request(self.base + path, data=body, method=method, headers=headers)
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())

    def create(self):
        return self.request("/api/meetings", self.control, "POST", {
            "topic":"Review implementation", "participants":["claude","codex"],
            "first_speaker":"claude", "max_turns":5,
        })[1]

    def test_auth_identity_turn_and_direct_message_filter(self):
        created = self.create(); meeting = created["meeting"]; invites = created["invitations"]
        self.assertIn("-m ai_team_room.cli", created["join_commands"]["claude"])
        self.assertIn(invites["claude"], created["join_commands"]["claude"])
        _, control_state = self.request("/api/state", self.control)
        self.assertEqual(control_state["invitations"], invites)
        self.request("/api/messages", self.control, "POST", {
            "meeting_id":meeting["id"], "text":"Claude only", "recipient":"claude", "client_id":"h1"
        })
        _, claude = self.request("/api/state", invites["claude"])
        _, codex = self.request("/api/state", invites["codex"])
        self.assertIn("Claude only", [m["text"] for m in claude["messages"]])
        self.assertNotIn("Claude only", [m["text"] for m in codex["messages"]])
        status, sent = self.request("/api/messages", invites["claude"], "POST", {
            "sender":"claude", "text":"Verified", "recipient":"all", "kind":"evidence", "client_id":"c1"
        })
        self.assertEqual(status, 201); self.assertFalse(sent["duplicate"])
        with self.assertRaises(HTTPError) as caught:
            self.request("/api/messages", invites["claude"], "POST", {
                "sender":"codex", "text":"spoof", "recipient":"all", "client_id":"bad"
            })
        self.assertEqual(caught.exception.code, 401)

    def test_missing_token_and_cross_origin_are_rejected(self):
        with self.assertRaises(HTTPError) as missing:
            self.request("/api/state")
        self.assertEqual(missing.exception.code, 401)
        with self.assertRaises(HTTPError) as origin:
            self.request("/api/meetings", self.control, "POST", {"topic":"x"}, "https://evil.example")
        self.assertEqual(origin.exception.code, 401)

    def test_brand_asset_is_served_as_png(self):
        request = Request(self.base + "/madoro-studio-logo.png")
        with urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertGreater(len(response.read()), 1_000)

    def test_end_wakes_waiter(self):
        created = self.create(); meeting = created["meeting"]; token = created["invitations"]["claude"]
        initial = self.request("/api/state", token)[1]
        result = {}
        def wait(): result.update(self.request(f"/api/wait?after={initial['cursor']}&timeout=3", token)[1])
        thread = threading.Thread(target=wait); thread.start()
        self.request("/api/control", self.control, "POST", {"meeting_id":meeting["id"],"action":"end"})
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result["meeting"]["status"], "ended")

    def test_wait_returns_immediately_when_it_is_participants_turn(self):
        created = self.create(); token = created["invitations"]["claude"]
        initial = self.request("/api/state", token)[1]
        _, result = self.request(f"/api/wait?after={initial['cursor']}&timeout=3", token)
        self.assertEqual(result["event"], "your_turn")
        self.assertEqual(result["you"], "claude")


if __name__ == "__main__":
    unittest.main()
