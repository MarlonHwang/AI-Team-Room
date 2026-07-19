# AI Team Room — project brief and market review

**Research date:** 2026-07-19
**Status:** independent local MVP implemented; public GitHub publication pending final owner review.

## 1. Problem observed in real use

A developer may keep Claude Code and Codex open side by side while both work on the same repository. Without a shared channel, the human becomes a manual message bus:

1. Copy one agent's findings.
2. Paste them into the other agent.
3. Wait for a response.
4. Copy the response back.
5. Repeat while also tracking which claims were actually tested.

This is slow, loses context, and encourages stale handoff summaries. It also prevents a meeting participant from immediately using the tools and context of its real work session to inspect files, search documentation, or run an authorized test.

## 2. Prototype behavior validated on 2026-07-19

The first working prototype was validated inside a private development repository. The generic implementation has since been rewritten in this independent repository; no private application code, data, meeting transcript, or secret was copied into the public candidate.

The following workflow was used successfully:

- The human opened the room in a browser.
- The already-open Claude Code and Codex work sessions were each instructed to join.
- Each actual session called `join`, preserved its cursor, and followed `wait -> investigate -> send -> wait`.
- A server-controlled `next_speaker` prevented overlapping ordinary messages.
- A timeout did not end the meeting; the participant continued waiting.
- During its turn, each session could use its own existing context and normal tools.
- Claims about searches, file reads, and experiments had to come from work actually performed in that session.
- The human remained a first-class participant and made the final decision.
- Existing authorization boundaries remained in force for repository writes, paid compute, destructive operations, commits, and pushes.

The session produced a concrete technical agreement rather than a mere opinion exchange. Claude Code and Codex independently inspected the same schema and tokenizer, corrected each other's assumptions, converged on a marker ABI, and requested one final decision from the human.

## 3. Exact product thesis

The proposed product is not primarily another autonomous multi-agent framework.

It is a meeting and coordination layer for **already-open, already-contextualized AI coding sessions**:

> A meeting room for the AI coding sessions you are already working in. No relaunch, no wrapper-owned replacement session, and no lost context.

Important properties:

- Existing live session remains the participant.
- Existing conversation context remains authoritative.
- Existing workspace and tools remain available.
- Existing permission and approval policy is not bypassed.
- Human participation and final authority are explicit.
- Evidence gathering occurs during the meeting in the real session.
- The room records discussion, decisions, unresolved questions, and participant identity.

## 4. Current market and adjacent projects

The market already validates demand for multi-agent coordination. AI Team Room must therefore be differentiated precisely; it must not claim to have invented agent chat.

### 4.1 agentchattr

Repository: <https://github.com/bcurts/agentchattr>

Closest visible feature set:

- Local shared chat for humans and Claude Code, Codex, Gemini CLI, and other agents.
- Mentions, channels, jobs, rules, images, and structured sessions with turn-taking.
- Windows launchers and macOS/Linux tmux launchers.
- Automatic terminal triggering and MCP integration.

Important distinction observed in its documented quick start:

- Its normal path launches agents through project wrappers.
- On Windows it can inject console input; on macOS/Linux it uses tmux and `send-keys`.
- It is highly relevant competition, but its standard operating model is not identical to inviting arbitrary work sessions that were already open before the room existed.

### 4.2 Agent Relay

Repository: <https://github.com/AgentWorkforce/relay>

Capabilities:

- Real-time channels, messages, presence, threads, and agent coordination.
- Claude Code, Codex CLI, Gemini CLI, OpenCode, SDKs, plugins, and programmatic workflows.
- Describes itself as communication infrastructure rather than a full agent harness.

Important distinction:

- Its documented examples and workflow emphasize Relay SDK/plugin integration and spawning or managing connected agents.
- It strongly validates the communication-layer market, but the proposed AI Team Room should focus on low-friction participation by the user's current work sessions and human-governed evidence meetings.

### 4.3 First-party multi-agent products

- Anthropic Agent View and agent teams: <https://claude.com/blog/agent-view-in-claude-code> and <https://code.claude.com/docs/en/agents>
- OpenAI Codex app multi-agent workflows: <https://openai.com/index/introducing-the-codex-app/>
- GitHub public preview for Claude and Codex agents: <https://github.blog/changelog/2026-02-04-claude-and-codex-are-now-available-in-public-preview-on-github/>

These products demonstrate that developers increasingly supervise several agents. They generally coordinate sessions inside one vendor or host surface rather than providing a neutral meeting among heterogeneous sessions already being used across separate tools.

### 4.4 Evidence that attachment to an active session remains difficult

OpenAI Codex issue: <https://github.com/openai/codex/issues/15299>

The issue specifically describes the lack of a supported way to route inbound MCP notifications into an already-running interactive Codex CLI/TUI session. This is relevant because many agent-chat products solve automation by owning the process, wrapping its PTY, or resuming a session in a new process.

AI Team Room's cooperative protocol is different: the actual session is explicitly instructed to join and then performs its own room polling during the active turn. This avoids pretending that unsupported external injection is available.

## 5. Differentiation to preserve

The strongest defensible positioning is:

1. **Actual-session participation** — the participant is the user's current work session, not a substitute agent given a summary.
2. **No context migration** — no transcript copy or lossy handoff is required.
3. **Evidence-backed turns** — participants can inspect, search, test, and report from their real environment.
4. **Human-governed meeting** — the human is not merely an orchestrator process; decisions and approval boundaries remain visible.
5. **Permission preservation** — joining a room never enables auto-approval or broadens tool authority.
6. **Provider neutrality** — the protocol is not owned by Claude, Codex, Gemini, or a single IDE.
7. **Simple coordination semantics** — join, wait, send, cursor, next speaker, end.
8. **Local-first operation** — source code and meeting contents stay local by default.

This is a positioning hypothesis, not a legal novelty or patentability conclusion. A deeper competitive and prior-art review is required before making a “first” claim.

## 6. Product boundaries

AI Team Room should not initially become:

- A replacement IDE.
- A general-purpose autonomous swarm.
- A provider for new model inference.
- A tool that automatically approves shell commands.
- A hidden PTY keystroke injector.
- A system that silently copies entire private transcripts to a server.
- A task scheduler that edits repositories without an explicit participant turn.

The first product should remain a reliable meeting room and coordination protocol.

## 7. Proposed MVP

### 7.1 Server

- Localhost-only by default.
- Meeting creation, join, presence, wait, send, end.
- Monotonic message IDs and cursor-based delivery.
- Explicit `next_speaker` state.
- Timeouts that do not imply meeting termination.
- Reconnection and duplicate-send protection.
- Append-only audit trail with export.

### 7.2 Human UI

- Topic, participants, active speaker, and connection status.
- Live transcript with unread indicators.
- Start, pause, resume, end, and force-pass-turn controls.
- Direct questions and explicit decision cards.
- Evidence links, file references, commands run, and result attachments.
- End-of-meeting decision/unresolved/action summary.

### 7.3 Session adapters

- Claude Code protocol/skill.
- Codex protocol/skill.
- Gemini CLI protocol/skill.
- A generic CLI/MCP adapter after the protocol stabilizes.

Adapters should teach an existing session how to join and poll. They should not require unsafe flags or replace the session with a wrapper-owned process.

### 7.4 Meeting protocol

- Only the named next speaker sends an ordinary message.
- Each message identifies sender, recipient, meeting, kind, and timestamp.
- Participant statements distinguish opinion from verified action.
- Runtime-generated evidence may be attached without pretending the model created it.
- Repository writes, paid compute, commits, pushes, and destructive actions retain their normal approval requirements.
- Human interruption always takes precedence.

## 8. Security requirements before public release

- Random meeting/session bearer token.
- Loopback-only registration by default.
- Strict origin checks and CSRF protection for the browser UI.
- No `shell=True` or string-built command execution.
- Escaping and length limits for all messages and attachments.
- Participant identity binding and duplicate-name handling.
- No secrets, environment dumps, hidden prompts, or full transcripts uploaded by default.
- Clear warnings before LAN exposure; TLS and authentication required for remote mode.
- Rate limits and loop limits to prevent runaway agent conversations.
- Runtime-only event ownership where applicable.
- Security review covering prompt injection through meeting messages.
- Tests proving that joining a meeting cannot broaden an agent's permissions.

## 9. Reliability requirements

- Windows, macOS, and Linux tests.
- Server restart and participant reconnection recovery.
- Message ordering, cursor monotonicity, and idempotent send tests.
- Slow participant and disconnected participant policies.
- Manual and automatic turn passing.
- Meeting termination that wakes every waiting participant.
- Unicode-safe transport, especially Windows PowerShell.
- Structured logs without sensitive content by default.

## 10. Open-source release checklist

1. Extract generic code from the private prototype without project data or secrets. **Done.**
2. Perform a source and history scrub.
3. Choose a license; Apache-2.0 is a reasonable candidate when an explicit patent grant is desirable, while MIT is simpler.
4. Add a threat model, security policy, contribution guide, and code of conduct.
5. Add automated tests and a supported-platform matrix.
6. Provide a one-command local installation path.
7. Record a short demonstration using genuine pre-existing sessions.
8. Publish an architecture diagram explaining cooperative polling versus PTY injection and spawned-agent orchestration.
9. Avoid “first ever” marketing unless independently substantiated.
10. Lead with the actual pain point: stop manually copying messages between coding agents.

## 11. Candidate public description

English:

> Stop copy-pasting between coding agents. Bring your existing live Claude Code, Codex, and Gemini sessions into one local, evidence-backed meeting room.

Korean:

> 코딩 AI 사이에서 복사·붙여넣기를 멈추세요. 지금 작업 중인 Claude Code, Codex, Gemini 세션을 맥락 그대로 하나의 로컬 회의실에 불러오세요.

## 12. Decision recorded

The concept is preserved as an independent project. A local MVP now implements the cooperative protocol, authenticated participant invitations, turn control, persistence, reconnection cursors, idempotent sending, a browser UI, and automated tests. Public GitHub publication remains a separate owner decision after final review.
