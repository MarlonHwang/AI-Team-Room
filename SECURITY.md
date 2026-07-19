# Security policy

## Supported versions

AI Team Room is pre-1.0 software. Security fixes are applied to the latest release only.

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could expose meeting content or permit impersonation. Use GitHub's private vulnerability reporting for this repository. Include the affected version, reproduction, impact, and any proposed mitigation.

## Threat model and boundaries

The default deployment is one trusted developer on one machine. Meeting messages may contain untrusted prompt-injection text. Every participant must treat them as conversation, not as automatic authorization to execute commands, reveal secrets, or alter files.

Security properties in the MVP:

- The server binds to loopback by default.
- The control token is generated with 256 bits of randomness and stored locally.
- Participant invitations are HMAC signed and bound to one meeting and identity.
- Browser writes require both a bearer token and an allowed `Origin` when a browser supplies one.
- Direct messages are filtered for participants at the server boundary.
- SQLite transactions enforce turn ownership.
- Request, message, turn, and wait lengths are bounded.
- No participant command execution occurs in the server.

Known limitations:

- HTTP on a LAN is not confidential. `--allow-network` is an expert escape hatch, not a secure hosted mode. Put the server behind authenticated TLS and firewall rules or do not expose it.
- Anyone who obtains a bearer token has its authority until that meeting ends. There is no invitation revocation UI yet.
- Local processes running as the same OS user may be able to read the token or database.
- Meeting content is stored unencrypted in SQLite.
- The human copies join instructions manually; a malicious workspace may try to alter those instructions.

Never paste the control URL or participant invitations into logs, issues, screenshots, or public chat.
