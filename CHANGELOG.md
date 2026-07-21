# Changelog

All notable changes to AI Team Room are documented here.

## 0.1.1 - 2026-07-21

- Add standalone Windows x64 and macOS arm64/x64 packaging.
- Make frozen builds generate participant commands using the bundled client.
- Add repeatable packaged-application smoke tests.
- Support optional Windows signing and Apple signing/notarization in CI.
- Remove the ambiguous pass-turn control; a direct human message now assigns the next responder.
- Show recent activity and last-contact time instead of treating every past participant as permanently joined.
- Add participant `leave`, UTF-8 `--text-file`, automatic cursor reuse, and explicit 30-second wait-cap guidance.

## 0.1.0 — 2026-07-21

Initial public MVP release.

### Included

- Local browser meeting room backed by SQLite.
- Human-controlled participant order, pause, interruption, and meeting end.
- HMAC-bound invitations and meeting-scoped participant identities.
- Cooperative `join`, `wait`, and `send` CLI protocol for existing AI sessions.
- Reconnection cursors and idempotent message delivery.
- Korean and English browser and invitation interfaces.
- Loopback-only networking by default and explicit LAN opt-in.
- Cross-platform test matrix for Windows, macOS, and Linux.
