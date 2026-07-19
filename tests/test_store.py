from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_team_room.auth import TokenSigner
from ai_team_room.store import Conflict, RoomStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = RoomStore(Path(self.temp.name) / "room.sqlite3")
        self.meeting = self.store.create("Choose the memory ABI", ["claude", "codex"], "claude", 4)

    def tearDown(self):
        self.temp.cleanup()

    def test_bounded_turn_rotation_and_end(self):
        for index, sender in enumerate(["claude", "codex", "claude", "codex"]):
            message, duplicate = self.store.send(
                self.meeting["id"], sender, "all", "talk", f"turn {index}", f"id-{index}"
            )
            self.assertFalse(duplicate)
            self.assertEqual(message["sender"], sender)
        final = self.store.get(self.meeting["id"])
        self.assertEqual(final["status"], "ended")
        self.assertEqual(final["turn_count"], 4)

    def test_wrong_speaker_is_rejected_atomically(self):
        with self.assertRaisesRegex(Conflict, "not codex's turn"):
            self.store.send(self.meeting["id"], "codex", "all", "talk", "jump", "jump-1")
        self.assertEqual(self.store.get(self.meeting["id"])["turn_count"], 0)

    def test_duplicate_client_id_returns_same_message_without_turn(self):
        first, duplicate = self.store.send(self.meeting["id"], "claude", "all", "evidence", "checked", "stable-id")
        self.assertFalse(duplicate)
        second, duplicate = self.store.send(self.meeting["id"], "claude", "all", "evidence", "checked", "stable-id")
        self.assertTrue(duplicate)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(self.store.get(self.meeting["id"])["turn_count"], 1)

    def test_final_turn_retry_is_still_idempotent(self):
        self.store.control(self.meeting["id"], "end")
        second = self.store.create("one turn", ["claude"], "claude", 1)
        first, _ = self.store.send(second["id"], "claude", "all", "talk", "done", "final-id")
        retried, duplicate = self.store.send(second["id"], "claude", "all", "talk", "done", "final-id")
        self.assertTrue(duplicate)
        self.assertEqual(first["id"], retried["id"])

    def test_human_interrupt_does_not_consume_agent_turn(self):
        self.store.send(self.meeting["id"], "human", "codex", "question", "verify this", "human-1")
        current = self.store.get(self.meeting["id"])
        self.assertEqual(current["next_speaker"], "claude")
        self.assertEqual(current["turn_count"], 0)

    def test_pause_resume_force_pass_and_end(self):
        meeting_id = self.meeting["id"]
        self.assertEqual(self.store.control(meeting_id, "pause")["status"], "paused")
        self.store.send(meeting_id, "human", "all", "talk", "Human interruption", "paused-human")
        with self.assertRaises(Conflict):
            self.store.send(meeting_id, "claude", "all", "talk", "during pause", "p")
        self.store.control(meeting_id, "pass", "codex")
        self.assertEqual(self.store.control(meeting_id, "resume")["next_speaker"], "codex")
        self.assertEqual(self.store.control(meeting_id, "end")["status"], "ended")
        with self.assertRaises(Conflict):
            self.store.control(meeting_id, "pass", "claude")

    def test_only_one_open_meeting(self):
        with self.assertRaises(Conflict):
            self.store.create("second", ["gemini"], "gemini", 3)
        self.store.control(self.meeting["id"], "end")
        second = self.store.create("second", ["gemini"], "gemini", 3)
        self.assertEqual(second["status"], "active")

    def test_cursor_is_exclusive_and_monotonic(self):
        initial = self.store.state(self.meeting["id"])
        self.assertEqual(len(initial["messages"]), 1)
        self.store.send(self.meeting["id"], "claude", "all", "talk", "hello", "cursor-1")
        fresh = self.store.state(self.meeting["id"], initial["cursor"])
        self.assertEqual([m["text"] for m in fresh["messages"]], ["hello"])
        self.assertGreater(fresh["cursor"], initial["cursor"])


class TokenTests(unittest.TestCase):
    def test_token_binds_meeting_and_participant_and_detects_tamper(self):
        signer = TokenSigner("x" * 32)
        token = signer.issue("meeting-1", "claude")
        self.assertEqual(signer.verify(token)["participant"], "claude")
        with self.assertRaisesRegex(ValueError, "invalid participant token"):
            signer.verify(token[:-1] + ("A" if token[-1] != "A" else "B"))


if __name__ == "__main__":
    unittest.main()
