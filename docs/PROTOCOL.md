# Cooperative session protocol

AI Team Room uses explicit cooperation because coding tools do not universally expose a safe API for injecting a notification into an arbitrary, already-running interactive session.

## Participant lifecycle

1. The human creates a meeting and receives one signed invitation per participant.
2. The human pastes the invitation instruction into each existing AI session.
3. The session runs `aitr ... join`, reads the meeting and protocol, and preserves the returned cursor.
4. When named as `next_speaker`, it investigates with its normal tools and permissions.
5. It sends one concise message with a unique client ID.
6. It calls `wait --after CURSOR`; a timeout means “still quiet,” not “meeting ended.”
7. It repeats until `meeting.status` is `ended`.

## Wire contract

- Message IDs are SQLite autoincrement integers and monotonically increase.
- `after` is an exclusive cursor.
- Participant bearer tokens are HMAC-bound to `meeting` and `participant`.
- A participant cannot choose a different sender identity.
- Only `next_speaker` can send an ordinary participant message.
- The human may speak at any time and may pause, resume, pass the turn, or end.
- `client_id` is unique for `(meeting, sender)`; retrying it returns the original message.
- Ending a meeting wakes long-polling clients.

## Evidence rule

A participant must distinguish analysis from actions actually performed. It must never claim it searched, read, changed, tested, committed, or pushed something unless that occurred in the participating work session. Room membership itself provides no new authority.

## HTTP endpoints

| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/api/state` | control/participant | Current state and transcript |
| `GET` | `/api/wait?after=N&timeout=S` | control/participant | Cursor-based long poll |
| `POST` | `/api/meetings` | control | Create the only open meeting |
| `POST` | `/api/messages` | control/participant | Idempotent send |
| `POST` | `/api/control` | control | Pause, resume, pass, or end |
