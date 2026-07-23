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

    def test_first_speaker_then_open_floor_without_automatic_end(self):
        for index, sender in enumerate(["claude", "claude", "codex", "codex", "claude"]):
            message, duplicate = self.store.send(
                self.meeting["id"], sender, "all", "talk", f"turn {index}", f"id-{index}"
            )
            self.assertFalse(duplicate)
            self.assertEqual(message["sender"], sender)
        final = self.store.get(self.meeting["id"])
        self.assertEqual(final["status"], "active")
        self.assertEqual(final["next_speaker"], "all")
        self.assertEqual(final["turn_count"], 5)
        self.assertEqual(final["max_turns"], 0)

    def test_non_opening_speaker_is_rejected_atomically(self):
        with self.assertRaisesRegex(Conflict, "opening response belongs to claude"):
            self.store.send(self.meeting["id"], "codex", "all", "talk", "jump", "jump-1")
        self.assertEqual(self.store.get(self.meeting["id"])["turn_count"], 0)

    def test_duplicate_client_id_returns_same_message_without_increment(self):
        first, duplicate = self.store.send(self.meeting["id"], "claude", "all", "evidence", "checked", "stable-id")
        self.assertFalse(duplicate)
        second, duplicate = self.store.send(self.meeting["id"], "claude", "all", "evidence", "checked", "stable-id")
        self.assertTrue(duplicate)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(self.store.get(self.meeting["id"])["turn_count"], 1)

    def test_ended_meeting_retry_is_still_idempotent(self):
        self.store.control(self.meeting["id"], "end")
        second = self.store.create("one turn", ["claude"], "claude", 1)
        first, _ = self.store.send(second["id"], "claude", "all", "talk", "done", "final-id")
        self.store.control(second["id"], "end")
        retried, duplicate = self.store.send(second["id"], "claude", "all", "talk", "done", "final-id")
        self.assertTrue(duplicate)
        self.assertEqual(first["id"], retried["id"])

    def test_direct_human_message_does_not_change_opening_speaker(self):
        self.store.send(self.meeting["id"], "human", "codex", "question", "verify this", "human-1")
        current = self.store.get(self.meeting["id"])
        self.assertEqual(current["next_speaker"], "claude")
        self.assertEqual(current["turn_count"], 0)

    def test_broadcast_human_message_preserves_floor(self):
        self.store.send(self.meeting["id"], "human", "all", "talk", "note for everyone", "human-all")
        current = self.store.get(self.meeting["id"])
        self.assertEqual(current["next_speaker"], "claude")
        self.assertEqual(current["turn_count"], 0)

    def test_pause_resume_and_explicit_end(self):
        meeting_id = self.meeting["id"]
        self.store.send(meeting_id, "claude", "all", "talk", "opening", "open")
        self.assertEqual(self.store.control(meeting_id, "pause")["status"], "paused")
        self.store.send(meeting_id, "human", "codex", "talk", "Codex continues", "paused-human")
        with self.assertRaises(Conflict):
            self.store.send(meeting_id, "claude", "all", "talk", "during pause", "p")
        self.assertEqual(self.store.control(meeting_id, "resume")["next_speaker"], "all")
        self.assertEqual(self.store.control(meeting_id, "end")["status"], "ended")
        with self.assertRaisesRegex(ValueError, "invalid control action"):
            self.store.control(meeting_id, "pass")

    def test_leave_removes_presence_until_next_contact(self):
        meeting_id = self.meeting["id"]
        self.store.touch(meeting_id, "claude")
        self.assertEqual([item["participant"] for item in self.store.presence(meeting_id)], ["claude"])
        self.store.leave(meeting_id, "claude")
        self.assertEqual(self.store.presence(meeting_id), [])
        self.store.touch(meeting_id, "claude")
        self.assertEqual([item["participant"] for item in self.store.presence(meeting_id)], ["claude"])

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
