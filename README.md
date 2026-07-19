# AI Team Room

Stop copy-pasting between coding agents. Bring the Claude Code, Codex, or other AI coding sessions you already have open into one local, evidence-backed meeting room.

AI Team Room is deliberately small: a local web room, a SQLite audit trail, and a cooperative command-line protocol. It does **not** spawn replacement agents, inject keystrokes into terminals, migrate private chat history, or expand an agent's permissions.

## Why this is different

- **The existing session participates.** Its context, tools, workspace, and approval policy stay intact.
- **The human remains in charge.** The browser controls turns, interruptions, pause, and meeting end.
- **Claims can be checked during the meeting.** A participant uses its normal tools, then posts what it actually verified.
- **Local first.** The server binds to `127.0.0.1` by default and stores data in a local SQLite database.
- **Provider neutral.** The wire protocol is plain HTTP+JSON and does not depend on one model vendor.
- **Bilingual UI.** The browser interface and participant invitation instructions can switch between 한국어 and English; meeting content is never silently translated.

## Quick start

AI Team Room requires Python 3.11 or newer and has no runtime dependencies.

```powershell
python -m pip install .
python -m ai_team_room.server
```

The command prints a browser URL containing the control token in the URL fragment. Open it, create a meeting, and copy each participant's join command into that participant's already-open session.

To run from a source checkout without installing:

```powershell
$env:PYTHONPATH = "$PWD\src"
python -m ai_team_room.server
```

Participant loop:

```powershell
aitr join --url http://127.0.0.1:8765 --token PARTICIPANT_TOKEN
aitr wait --url http://127.0.0.1:8765 --token PARTICIPANT_TOKEN --after 0
aitr send --url http://127.0.0.1:8765 --token PARTICIPANT_TOKEN --after 0 --text "Verified finding"
```

`join` returns the exact protocol instruction and current cursor. A timeout is only a quiet interval; it does not end the meeting.

## Safety defaults

- Loopback binding only unless `--allow-network` is explicitly supplied.
- A random persistent control token and HMAC-bound participant invitations.
- Browser mutations require a same-origin `Origin` header and bearer token.
- Participant tokens are bound to one meeting and one participant name.
- Idempotency keys prevent accidental duplicate sends.
- Message length, turn count, request size, and long-poll duration are bounded.
- Meeting membership never changes shell, filesystem, network, or approval permissions.

LAN exposure is intentionally not a polished feature. Read [SECURITY.md](SECURITY.md) before using `--allow-network`.

## Development

```powershell
python -m unittest discover -s tests -v
```

Protocol and architecture details are in [docs/PROTOCOL.md](docs/PROTOCOL.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The original product and market notes are preserved in [docs/PROJECT_BRIEF_20260719.md](docs/PROJECT_BRIEF_20260719.md).

## Status

Early MVP. The core local meeting path, identity binding, turn control, reconnection cursor, idempotent delivery, persistence, and tests are implemented. Claude Code and Codex participation is cooperative: you paste one join instruction into each existing session once per meeting.

Licensed under Apache-2.0.
