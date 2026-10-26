# UMAS — Project DNA

> **Stack note (2026-10-25):** The language choices in this document are superseded. The stack is Python (TypeScript only where no Python option exists). Rust and Go references describe the source design. See umas/TECHNICAL-DESIGN-SPEC.md Appendix A.4.

> **Version:** 1.0 · **Date:** October 2026  
> **Status:** Authoritative · Applies to every module, library, pack, and line of code in this project.  
> **Single rule:** If a decision you are about to make contradicts anything in this document, stop. Re-read the relevant section. If the contradiction cannot be resolved, open an issue before writing code.

---

## What this document is

This is the DNA of the Unified Multi-Agent Development System. It is not an introduction, a summary, or a getting-started guide. It is a decision record that encodes **why** this system is shaped the way it is, the **non-negotiable constraints** every module must honour, and the **shared vocabulary** every developer and every agent must use consistently.

Reading this document is step zero before touching any part of this codebase.

---

## Part 1 — The Six Non-Negotiable Principles

These come from the PRD and override every implementation convenience. They are listed in order of precedence.

### P1 · Context Persistence

**Statement:** All agent work state must survive crashes and restarts.

**What this means in practice:**
- No in-memory-only state that matters. If it matters, it is in a Git commit or an append-only log file.
- The unit of recovery is a worktree commit. Every agent commits after every major step — not at the end of a task, not on success only.
- `STATE.md` in the worktree root is the canonical recovery surface. It must be readable by a new agent with zero prior context.
- The `events.jsonl` log is the secondary surface. It is append-only. It is never truncated during normal operation. The last 90 days are never deleted.

**What this rules out:**
- Storing task progress in a database row that is updated in place. Use the event log as source of truth; the database is a rebuildable index.
- Passing context between agents as function arguments or API calls. Context travels as a committed file.

---

### P2 · Structured Workflows

**Statement:** Prevent chaos through explicit orchestration and task tracking.

**What this means in practice:**
- Every unit of work has a record: `work_bundle` → `task`. No task runs without a record.
- The Coordinator runs a state machine. States are named. Transitions have explicit triggers. There is no "just start working" shortcut.
- Multiple concurrent bundles are isolated. The failure of one does not pause others.
- Human gates are explicit pause points, not ad-hoc waits.

**What this rules out:**
- An agent spawning sub-work without creating a task record.
- A playbook step that advances without satisfying its gate condition.
- Concurrent bundles sharing mutable state.

---

### P3 · Systematic Verification

**Statement:** Every change flows through automated quality gates before reaching `main`.

**What this means in practice:**
- The Merge Queue Processor is not optional in any phase. A path to `main` that bypasses it is a defect.
- Two-axis code review (Standards + Spec) runs on every PR. Both axes run in parallel. Neither is skipped for "small" changes.
- Test coverage policy applies to all implementation work. The default mode is `selective` (risky logic only). `strict` (TDD) is opt-in per project. Trivial changes are the only exception.

**What this rules out:**
- A "fast path" merge that skips review because the change is "obvious".
- A finding filed without a concrete fix. Vague findings are not filed.
- Tests written after the merge queue rather than before.

---

### P4 · Human Control

**Statement:** Humans approve at critical junctures. Agents propose and execute.

**What this means in practice:**
- The Coordinator grills humans before starting non-trivial work. Grilling produces an alignment summary. Work does not start until the human confirms.
- Human gates in playbooks are hard stops, not soft suggestions. The work bundle pauses. It does not proceed on timeout.
- Agents escalate by appending to `events.jsonl`. Escalation is not a function call to a human. The human sees it through `umas watch` or the dashboard and acts with `umas work-bundle approve`.
- Agent-to-agent handoffs do not require human approval. Only human-initiated requests are grilled.

**What this rules out:**
- An agent self-approving its own escalation.
- A gate that times out and auto-approves.
- Grilling running on an agent-to-agent handoff (propulsion principle: agent pipelines run without interruption).

---

### P5 · Radical Minimalism

**Statement:** Solve before writing. Measure the impact of not writing code.

**What this means in practice:**
- Every agent runs the six-rung minimalism ladder **after** reading relevant code, **before** writing any:
  1. Does this feature need to exist?
  2. Does it already exist in this codebase?
  3. Is it in the standard library or platform?
  4. Is it an already-installed dependency?
  5. Can it be one readable line?
  6. Otherwise: minimum code that works.
- Shortcut comments (`// SHORTCUT: <what> — <when to fix>`) are the only permitted form of deliberate deferral. They must be tracked in the project's debt ledger. All other comments must justify *why* the code exists.
- Key targets: −40% lines of code, 40% fewer tokens, 25% lower cost.

**What this rules out:**
- Writing a new utility before confirming it does not already exist.
- Comments that describe *what* the code does (the code says that). Only *why* comments are permitted.
- Deferring without recording the deferral in the debt ledger.

---

### P6 · Measurable Impact

**Statement:** Track code size, cost, time, test coverage, and production reliability. Everything is measurable or it is a guess.

**What this means in practice:**
- The metrics store records every meaningful measurement: tokens used, cost, duration, test coverage delta, error rates.
- Metrics targets are hard numbers in the spec (§13). If a module cannot be measured against one of these targets, the metric must be added before the module ships.
- The `budget-meter` library is the single source of truth for token and cost accounting. No module does its own accounting.

**What this rules out:**
- "We believe this is faster" without a measurement.
- A module that emits usage data to a custom log that the metrics store does not read.

---

## Part 2 — Architecture Invariants

These are the load-bearing constraints of the system design. Changing them requires a new ADR.

### A1 · Git is the primary state store

Git worktrees are not a convenience. They are the crash-recovery mechanism. The database (`~/.umas/database.db`) is a queryable index over Git state — it is always rebuildable. If the database is deleted, no committed work is lost.

### A2 · Libraries have no knowledge of UMAS

A Tier 1 library does not import, reference, or assume UMAS. No library reads `~/.umas/`. No library hard-codes `.umas/`. No library contains the strings `umas` or `[umas:...]`. These values are always configuration parameters with neutral defaults.

Libraries do not depend on each other. Composition happens in the consuming application (UMAS). Where two libraries meet, the contract is a file format or a data shape, never an import.

Violation of A2 is a defect that blocks merge.

### A3 · Content packs have no tool or model assumption

A Tier 2 content pack is Markdown, YAML, and JSON Schema. It can be loaded as a Claude Code skill, concatenated into a system prompt, or read as a human checklist. It never assumes a specific model ID, vendor, or special tool. It never contains UMAS paths or commands in its body.

### A4 · Providers are configuration

Replacing an LLM provider is an edit to the `llm-gateway` alias table and the project config file. No application code changes. The harness (Claude Code, Codex, Copilot) and the provider (Anthropic, OpenAI, Google, Ollama) are separate concerns at separate layers — replaced independently.

### A5 · Services bind to localhost

All services bind to `127.0.0.1`. No service binds to `0.0.0.0`. TLS 1.2+ for all external communication. Certificate validation is never disabled.

### A6 · Secrets are never in code

API keys live in environment variables or a vault (HashiCorp Vault, IBM Key Protect). `.gitignore` is created by `umas init` and covers all secret files. No secret is ever logged, even in debug mode.

### A7 · Audit logs are append-only and retained 90 days

`events.jsonl` is the audit log. No record is ever deleted during its retention window. The last 90 days of records survive `umas cleanup`. Decision artifacts (ADRs, PRFAQs, Specs) are never deleted by any automated process.

### A8 · Graceful degradation over hard failure

Budget exhausted → queue work, do not fail in-progress sessions. Provider fails → retry with backoff, then failover, then escalate. Disk low → warn at 2 GB, pause dispatch at 500 MB, emergency checkpoint at 100 MB. **Machine shutdown → pause at step boundary, write `PAUSE.md`, resume on next boot.** No failure mode results in silent data loss.

### A9 · Machine is a first-class interruption

The laptop shutting down is not a crash. It is a known, expected event in a development workflow. The system must treat it the same way it treats a graceful `umas stop-all`: checkpoint all sessions, persist state to Git, and resume automatically on next `umas start-all`. A session that was running cleanly when the machine shut down must never be demoted to `crashed`.

Two mechanisms together guarantee this:
1. **Pre-shutdown signal:** The daemon catches `SIGTERM`/OS shutdown events and broadcasts `.pause` files to all worktrees. Agents poll at each step boundary and call `pause()`.
2. **Boot recovery:** `umas start-all` scans all sessions with status `active`/`machine_paused`, checks `PAUSE.md` vs `STATE.md`, validates the OIDC token, and resumes or surfaces `auth_expired`.

Sessions remain `machine_paused` or `auth_expired` indefinitely — no watchdog auto-escalation, no timeout. The human controls re-authentication timing.

### A10 · Skills are harness-neutral and platform-neutral

A skill is a `SKILL.md` file. It runs unchanged on `claude-code` and `openai-codex` on both Windows and Unix. No exceptions.

**What this means in practice:**
- A skill file MUST NOT contain shell syntax, absolute paths, Windows path separators (`\`), or harness-specific directives (Claude Code `/slash commands`, OpenAI function syntax).
- File references inside a skill use forward slashes only: `src/auth/login.py`, never `src\auth\login.py`.
- Environment-specific values (project name, OS, model ID, host path) are `{{placeholders}}` filled by the consuming application at write time, not hardcoded in the skill.
- A skill is validated against these rules when the consuming application loads it. A skill that fails validation is rejected with the violating line listed — it is never silently loaded in a degraded state.

**What this rules out:**
- A "Windows version" and a "Unix version" of the same skill. One file, all harnesses, both platforms.
- A skill that works on `claude-code` but must be rewritten for `openai-codex`. The format contract in `agent-platform §5.8` is the only contract.
- Embedding actual shell commands in a skill's `## Prompt` section. If a setup step requires a shell command, it belongs in the project's `Makefile` or `justfile`, referenced by path from the skill.

---

## Part 3 — The Shared Vocabulary

Every module, every commit message, every log line, every error record uses these terms exactly as defined. Synonyms are forbidden.

| Term | Definition |
|------|------------|
| **work_bundle** | The top-level unit of work submitted by a human. Contains one or more tasks. Has its own state machine. |
| **task** | One atomic piece of work assigned to one agent. Has an ID, a hook path, a dependency list, and a status. |
| **hook** | A named Git worktree slot. The unit of work assignment. `hook_path` is relative to `.umas/worktrees/`. |
| **agent** | An ephemeral LLM session. Has a session ID, a task ID, and a status. Operates inside exactly one worktree. |
| **harness** | The CLI tool that hosts an agent session. Three are built in: `claude-code` (Anthropic), `openai-codex` (OpenAI; also runs Google Gemini models), `copilot` (GitHub, IDE-only). Not the same as the LLM provider — each is registered and replaced independently. |
| **skill** | A `SKILL.md` file placed in a hook worktree alongside `TASK.md`. Loaded by any hook-supporting harness as supplementary context for the session. Written in the universal skill format (§5.8 of `agent-platform`): plain Markdown, no shell syntax, forward slashes only, `{{placeholders}}` for environment values. One skill file runs on all harnesses unchanged. |
| **provider** | The LLM API that generates tokens (Anthropic, OpenAI, Google, Ollama). Not the same as the harness. |
| **worktree** | A Git worktree under `.umas/worktrees/<hook-path>/`. One agent, one worktree, one branch at a time. |
| **STATE.md** | The recovery file in the worktree root. Always current. Contains: current task, last 10 decisions, explicit next steps, relevant file pointers. |
| **events.jsonl** | The append-only structured event log at `.umas/events.jsonl`. The inter-process message bus for Phase 1–2. |
| **handoff packet** | Compressed context (~15k tokens) built from `STATE.md` at session end. The incoming agent reads this, not the full conversation. |
| **playbook** | A Markdown + YAML front-matter file defining phases, gates, steps, exit predicates, and escape hatches. Lives in `.umas/playbooks/`. |
| **phase** | One named stage in a playbook. Contains ordered steps. Has an optional gate at its end. |
| **gate** | A human approval or automated check that must pass before the next phase starts. A hard stop. |
| **escape hatch** | A mandatory exit path in every phase for unrecoverable state. Writes a `[checkpoint]` commit and `RESUME.md`, then escalates. |
| **grilling** | The bounded questioning protocol the Coordinator runs on human-initiated requests. Produces an alignment summary. Max 10 questions. |
| **minimalism ladder** | The six-rung check every agent runs after reading code and before writing any. |
| **shortcut comment** | `// SHORTCUT: <what> — <when to fix>`. The only permitted form of deliberate deferral. Must be in the debt ledger. |
| **two-axis review** | A code review with two independent passes: Standards (quality) and Spec (correctness). Run in parallel. Both required. |
| **merge queue** | The permanent worktree and processor that tests PR batches and bisects on failure before merging to `main`. |
| **coordinator** | The Python agent that owns the Coordinator state machine. Never writes application code. |
| **scheduler** | The component that maintains the ready queue, enforces the concurrency cap, and dispatches agents. Uses `task-queue`. |
| **watchdog** | The three-tier supervision chain: Daemon (Python) → Triage Agent → System Patrol → Project Monitors. |
| **project monitor** | One Python process per active project. Polls every 60 seconds. Detects stuck, crashed, and over-budget agents. |
| **machine_paused** | Session status set when the host machine shuts down. The session is resumable; it is never treated as crashed. Recovery is automatic on next `umas start-all` if the OIDC token is still valid. |
| **auth_expired** | Session status set when `machine_paused` is detected on boot and the OIDC token has expired. Requires `umas auth login` before the session can resume. Has no timeout. |
| **PAUSE.md** | A file written by `agent-session.pause()` to the worktree root on clean shutdown. Identical content to `STATE.md` plus `paused_reason` and `paused_at`. Presence of this file is the definitive signal that the session was paused cleanly (not crashed). |
| **.pause** | A signal file written by the daemon to `<hook-path>/.pause` when a shutdown is imminent. Agents poll for it at every step boundary. When found, they call `pause()` and exit. Deleted by the daemon after all agents respond or the grace window expires. |

---

## Part 4 — Signal Protocol (Canonical)

All agent signals use these exact strings. No synonym, no abbreviation. The Scheduler and Project Monitor pattern-match on them.

| Signal | Mechanism | Format | Reader |
|--------|-----------|--------|--------|
| Task complete | Git commit message | `[umas:done] <task-id>` | Scheduler |
| Checkpoint | Git commit message | `[umas:checkpoint] <summary>` | Project Monitor |
| Budget pause | Git commit message | `[umas] budget-pause — state committed` | Project Monitor |
| Task blocked / escalate | Append to `events.jsonl` | `{"event":"escalate","severity":"P1","reason":"..."}` | Coordinator |
| Handoff request | Append to `events.jsonl` | `{"event":"handoff_request","session_id":"...","reason":"..."}` | Scheduler |
| Step complete | Append to `events.jsonl` | `{"event":"step_complete","agent":"...","hook":"...","summary":"..."}` | Project Monitor |

> **Open question Q8:** `agent-platform` currently uses `[done]`/`[blocked]`. One must change to match this table. Decision pending; tracked in `TECHNICAL-DESIGN-SPEC.md §14.8`.

---

## Part 5 — Module Checklist

Every module (library or pack) must satisfy all items before its spec is considered complete and before any implementation begins.

### For Tier 1 Libraries

- [ ] No UMAS names, paths, or strings (`umas`, `.umas/`, `[umas:...]`) in the body. Every such value is a configuration parameter.
- [ ] No cross-library imports. Where two libraries meet, the contract is a file format.
- [ ] No database required. State is in files or Git. Any database index is rebuildable.
- [ ] Language-neutral contract. Spec defines behaviour and file formats, not language.
- [ ] Every persisted file carries `schema_version`. Library reads N and N-1; writes N.
- [ ] Destructive operations refuse by default when state is uncertain. They explain why.
- [ ] All events emitted through a caller-supplied callback. No framework dependency.
- [ ] Thin CLI exposed: `<lib-name> <command> --json`. Non-host-language consumers use it by subprocess.
- [ ] Spec has: Purpose · Scope/Non-Goals · Concepts/Data Model · Interface · Behaviour · Configuration · Failure Modes · Acceptance Criteria · How UMAS Uses It · Source Material/Deviations · Open Questions.
- [ ] Registered in `libs/README.md`.
- [ ] Added to `TECHNICAL-DESIGN-SPEC.md §3` Tier 1 table.
- [ ] `TECHNICAL-DESIGN-SUMMARY.md` counts and changelog updated.

### For Tier 2 Content Packs

- [ ] No UMAS names, paths, or commands in the pack body. UMAS mappings are in the spec's "How UMAS uses it" section only.
- [ ] No tool or model assumption. Usable as a system prompt, a skill file, or a human checklist.
- [ ] No cross-pack dependency. Where two packs meet, the contract is a data shape in both specs.
- [ ] Input and output schemas defined before the prompt text.
- [ ] Fixtures shipped (`F1`, `F2`, ...): each is `{ id, input, expect: [property] }`. No fixtures = draft, not complete.
- [ ] `pack_version` (semver) in the spec. Outputs echo it.
- [ ] Spec states what the pack cannot do. Unverified numbers are marked unverified.
- [ ] Pack directory contains: `PACK.md`, `schema/*.json`, `fixtures/*.yaml`, `config.yaml`.
- [ ] Spec has: Purpose · Scope/Non-Goals · Pack Contents/Format · Contract · Rules and Prompt · Configuration · Failure Modes · Fixtures/Acceptance Criteria · How UMAS Uses It · Source Material/Deviations · Open Questions.
- [ ] Registered in `packs/README.md`.
- [ ] Added to `TECHNICAL-DESIGN-SPEC.md §3` Tier 2 table.
- [ ] `TECHNICAL-DESIGN-SUMMARY.md` counts and changelog updated.

---

## Part 6 — Implementation Phasing

Work is sequenced. Starting Phase 2 work while Phase 1 is incomplete is not permitted.

| Phase | Duration | What ships | Key libs in build order |
|-------|----------|-----------|------------------------|
| **1 · Foundation (MVP)** | 8–12 weeks | Git worktree manager, task database, Coordinator, Worker agents, minimalism enforcement, basic merge queue, CLI | `event-log`, `budget-meter`, `hook-store`, `task-queue`, `test-adapters`, `merge-queue`, `error-classifier`, `kc-axi`, `metrics-store` (JSONL) |
| **2 · Specialization** | 6–8 weeks | Specialized agents, grilling, decision artifacts, TDD enforcement, code review | `decision-artifacts`, `agent-session`, `agent-platform` |
| **3 · Monitoring** | 4–6 weeks | Three-tier watchdog, project monitors, telemetry, minimal HTML dashboard | `watchdog`, `metrics-store` (SQL backend activated) |
| **4 · Scale** | 6–8 weeks | Scheduler, multi-platform support, session history, advanced merge queue, dashboard push updates (optional) | `llm-gateway` (evaluated, adopted or wrapped) |
| **5 · Federation (optional)** | 8–10 weeks | Cross-workspace coordination | Deferred; design with federation in mind from Phase 1 |

**Starting conditions for Phase 1:**
- `umas init` and `umas init --project` are idempotent and work.
- A `work_bundle` can be created and a task dispatched to a worker agent.
- The worker agent commits state to its worktree and signals `[umas:done]`.
- The Merge Queue Processor can run the test suite on a batch and merge on green.

---

## Part 7 — Technology Stack (Pinned)

| Layer | Language | Key dependencies | Notes |
|-------|----------|-----------------|-------|
| Daemon + CLI | Python 3.10+ | asyncio (stdlib), typer, pydantic 2.4+, sqlalchemy 2.0+ (sqlite3 for the MVP), structlog, uuid (stdlib) | Distributed as a Python package (uv or pip). Run the daemon under launchd or systemd so the OS restarts it |
| Agent runtime | Python 3.10+ | anthropic 0.7+, openai 1.3+, google-generativeai 0.3+, pydantic 2.4+, aiofiles 23.2+, gitpython 3.1+, sqlalchemy 2.0+, alembic 1.12+ | Pydantic v2 is the standard output validator |
| Alternative (single runtime) | TypeScript / Node 18+ | commander, prisma, zod | Viable if team prefers one runtime; lib specs are language-neutral |
| Database — MVP | SQLite 3.35+ | WAL mode, foreign keys, JSON support | `~/.umas/database.db` |
| Database — Production | PostgreSQL 14+ | Connection pool min 5 / max 50 | Migrate from SQLite without data loss |
| Metrics storage | JSONL (Phase 1–2) → PostgreSQL `metrics` table (Phase 3+) | TimescaleDB is NOT a hard dependency | One `create_hypertable` statement if/when needed; no app code change |
| Observability | OpenTelemetry 1.20+ | Prometheus (metrics), Jaeger (traces), Loki (logs), structlog (Python) | All fields: timestamp, level, service, agent_id, session_id, task_id, trace_id |
| Dashboard — Phase 1–3 | Minimal read-only HTML + polling | No build step, no React | ADR-0001 |
| Dashboard backend | FastAPI (Python) | Same REST API and OpenAPI definition as the CLI | React is superseded and not planned; push updates (SSE or WebSocket) only if a later decision needs them |
| Identity | Keycloak (OIDC) | `kc-axi` lib for agent-friendly admin CLI | JWT Bearer tokens; roles: Admin, Developer, Viewer |

---

## Part 8 — Quality Targets (Hard Numbers)

These are not aspirational. They are acceptance criteria for the project.

| Category | Metric | Target |
|----------|--------|--------|
| Code quality | Lines of code reduction vs. baseline | −40% |
| Code quality | Test coverage | 95%+ |
| Code quality | Code reuse percentage | tracked from day 1 |
| Performance | Cost reduction vs. baseline | −25% |
| Performance | Time reduction vs. baseline | −35% |
| Performance | Token reduction per task | −40% |
| Reliability | Agent uptime | 99%+ |
| Reliability | Context recovery time after crash | < 30 s |
| Scale | Max concurrent agents (Tier 3) | 30+ |
| Scale | API rate limit violations | zero |

---

## Part 9 — What "Done" Means

A module is done when:

1. Its spec satisfies the Part 5 checklist.
2. Its fixtures all pass.
3. It is registered in `libs/README.md` or `packs/README.md`.
4. `TECHNICAL-DESIGN-SPEC.md §3` is updated.
5. `TECHNICAL-DESIGN-SUMMARY.md` counts and changelog are updated.
6. Two-axis review (Standards + Spec) has passed with no open Critical or High findings.
7. The merge queue has merged it to `main` (green tests, no bisect required).

A module is **not** done because:
- It works in a local test.
- The agent that wrote it says it is done.
- It has no open issues.

---

## Part 10 — The Motto

> **"If you want to go fast, go deep first."**

Speed comes from clarity of design, not from skipping steps. The deeper the understanding before a line is written, the fewer the rewrites. This document is the depth. Read it. Then build.

---

*Maintained alongside `TECHNICAL-DESIGN-SPEC.md`. When the spec changes in a way that affects a principle, invariant, vocabulary term, or signal, this document is updated in the same commit.*
