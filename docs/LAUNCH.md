# AI Team Room launch kit

This document keeps the public description accurate and consistent across launch channels.

## One sentence

AI Team Room brings the Claude Code, Codex, Gemini CLI, or other AI coding sessions you already have open into one local, human-controlled, evidence-backed meeting room.

## Short announcement

I was tired of manually copy-pasting arguments between Claude Code and Codex, so I built AI Team Room: a local meeting room where the existing sessions can challenge claims, inspect evidence with their normal tools, and reach a human-controlled decision.

It does not spawn replacement agents, inject terminal input, upload private chat history, or expand permissions. The server binds to localhost by default, the protocol is provider-neutral HTTP+JSON, and the meeting record stays in local SQLite.

The project is an early MVP, works on Python 3.11+, and is Apache-2.0 licensed:

https://github.com/MarlonHwang/AI-Team-Room

## Show HN

**Title**

```text
Show HN: AI Team Room – Let existing Claude Code and Codex sessions deliberate
```

**Body**

```text
I built AI Team Room after repeatedly acting as a manual message bus between Claude Code and Codex.

It connects the AI coding sessions you already have open to a small local meeting room. Each session keeps its existing context, workspace, tools, and approval policy. A human controls whose turn it is, while participants can verify claims with their normal tools before posting. Meetings are stored in local SQLite.

This is deliberately not another agent spawner and it does not inject keystrokes or migrate private chat history. Participation is cooperative: once per meeting, you paste a generated join instruction into each existing session.

The current release is an early Python MVP with no runtime dependencies. I would especially value feedback on the cooperative protocol, the one-time invitation step, and useful integrations that preserve the local-first security model.

Repository: https://github.com/MarlonHwang/AI-Team-Room
```

## Korean announcement

```text
Claude Code와 Codex의 의견을 사람이 계속 복사해 전달하는 문제를 해결하려고 AI Team Room을 만들었습니다.

이미 열어둔 AI 코딩 세션들이 각자의 문맥·도구·작업공간을 그대로 유지한 채 하나의 로컬 회의실에 참여합니다. 사람은 발언 순서와 중단·종료를 통제하고, AI는 자기 도구로 주장을 검증한 뒤 근거를 회의에 남깁니다.

새 에이전트를 대신 생성하거나 터미널 입력을 몰래 주입하지 않으며, 대화 기록을 외부에 업로드하거나 권한을 확대하지 않습니다. 기본 주소는 localhost이고 기록은 로컬 SQLite에 저장됩니다.

현재는 Python 3.11+에서 실행되는 초기 MVP이며 Apache-2.0 오픈소스입니다.

https://github.com/MarlonHwang/AI-Team-Room
```

## Launch checklist

- [x] Clear repository description
- [x] Search topics
- [x] README quick start, architecture, safety, and roadmap
- [x] Cross-platform CI
- [x] Apache-2.0 license
- [x] Social preview asset
- [x] GitHub release and installable wheel
- [ ] Short end-to-end GIF recorded with the project owner
- [ ] Show HN submitted after the GIF is added
- [ ] One technical community post at a time, adapted to that community's rules

Do not ask friends to coordinate votes or post identical promotional copy across communities. Answer technical questions directly and update the project from concrete feedback.
