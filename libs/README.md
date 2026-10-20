# Standalone Libraries (Tier 1)

> Thirteen reusable libraries extracted from the UMAS design. Each has its own spec and can be built, versioned, tested, and used without UMAS.
>
> **Status:** Draft v0.1 · **Date:** October 19, 2026
> **Referenced from:** [UMAS-TECH-DESIGN-SPEC.md](../UMAS-TECH-DESIGN-SPEC.md) §1.1 · [TECHNICAL-DESIGN-SUMMARY.md](../TECHNICAL-DESIGN-SUMMARY.md)

---

## The Set

| Library | One-line purpose | Standalone use |
|---------|------------------|----------------|
| [hook-store](hook-store.md) | Durable git-worktree "hooks" that hold a unit of work's state across crashes and handoffs | Crash-safe workspaces for any agent harness or long-running script |
| [event-log](event-log.md) | Append-only JSONL event log with cursor-based reading, rotation, and corruption recovery | Audit trail, replay, or lightweight message bus between local processes |
| [merge-queue](merge-queue.md) | Batch merge with prefix-bisect, driven by any verify command | A local or CI merge queue for any repo, with no agents involved |
| [test-adapters](test-adapters.md) | Run pytest, jest, or cargo test and get one normalised result | Any tool that needs test results without per-framework parsing |
| [budget-meter](budget-meter.md) | Token and cost budgets, threshold events, admission control, handoff-packet packing | Budget control for any LLM application |
| [llm-gateway](llm-gateway.md) | Provider-neutral LLM calls with retry, failover, and rate limiting | Provider portability. **Adopt an existing package first** |
| [watchdog](watchdog.md) | Heartbeat and progress supervision with a restart and escalation ladder | Supervising any set of long-running local processes |
| [decision-artifacts](decision-artifacts.md) | PRFAQ, ADR, Spec, and GLOSSARY files, plus a shortcut-debt ledger scanned from code | Decision-record tooling for any repo, and a CI lint |
| [error-classifier](error-classifier.md) | One error record (code, severity, recoverability), deterministic classification rules, retry advice, agent and human rendering, repeat-pattern alerts | A shared error vocabulary for any multi-component system |
| [agent-platform](agent-platform.md) | Adapter registry for coding agent harnesses (Claude Code, OpenAI Codex, Gemini CLI, Copilot, custom) with work assignment, completion signalling, and cross-platform context transfer | Assigning work to any agent harness and tracking completion without knowing which tool is running |
| [agent-session](agent-session.md) | Shared lifecycle skeleton for LLM agent sessions: spawn → execute → checkpoint → handoff → done, with STATE.md, token threshold monitoring, and handoff-packet construction | Any multi-agent system where agents must hand off work and successors must resume from a durable state |
| [task-queue](task-queue.md) | Dependency graph and ready queue with leased claims, a concurrency cap, retry, and parent/child groups, stored in an event log plus snapshot | A local work queue for any set of dependent jobs, with no broker or database |
| [metrics-store](metrics-store.md) | Record scalar measurements (tokens, durations, costs, error rates) from multiple processes; queryable by time window and tag; two backends: JSONL ledger (Phase 1–2) and a relational table (Phase 3+) | Budget reporting, cost tracking, or quality trending for any multi-component system with a file-based or SQL backend |

---

## Independence Rules

These rules make a library standalone. A spec or implementation that breaks one is a defect.

1. **No UMAS imports, paths, or names.** A library never reads `~/.umas/`, never hard-codes `.umas/`, and never contains the strings `umas` or `[umas:...]`. Every such value is a configuration parameter with a neutral default.
2. **No cross-library dependencies.** The libraries do not import each other. Composition happens in the consuming application (for example, UMAS passes `budget-meter` usage callbacks into `llm-gateway`). Where two libraries meet, the contract is a data format, not an import.
3. **No database required.** State lives in files or in git. Where an index helps, it is a rebuildable cache, never the source of truth. This removes the SQLite/Postgres coupling in the current implementation spec.
4. **Language-neutral contract.** Each spec defines behaviour, file formats, and operations. The implementation language is chosen separately (see "Implementation language" below). Any format a library writes is readable by any language.
5. **Versioned formats.** Every persisted file carries `schema_version`. A library reads versions N and N-1, and writes N.
6. **Safe by default on destructive actions.** Operations that can lose work (removing a worktree, rewriting a log, merging to a branch) refuse by default when state is uncertain, and say why.
7. **Observable without a framework.** Each library emits plain structured events through a caller-supplied callback. It never requires an OpenTelemetry, Prometheus, or logging dependency.

---

## Conventions Used in the Specs

- Operations are written as `name(args) -> result`. Types are descriptive, not tied to a language.
- `Result` means success or a typed error from that library's error table.
- Times are RFC 3339 UTC. IDs are ULIDs unless stated.
- MUST, SHOULD, and MAY carry their RFC 2119 meaning.
- Each library keeps its own typed errors. Where a spec has a "Failure Modes" section it may end with an "Error records" table giving a suggested `recoverability` for each error, so a consumer can express them as [error-classifier](error-classifier.md) records. This is a data mapping, not an import.
- Each spec ends with "How UMAS uses it". This is a mapping table for readers, and the library does not depend on anything in it.

---

## Composition Map

Dependency arrows show what the consuming application wires together. They are not code imports.

```
              +-------------------- consuming application ---------------------+
              |                                                                 |
 hook-store --+-- commits are signals --> event-log <-- budget-meter alerts     |
     |        |                              ^                                  |
     |        |                              |                                  |
     v        |                      watchdog (progress marker = last commit)   |
 merge-queue -+-- verify cmd --> test-adapters                                  |
              |                                                                 |
 llm-gateway -+-- usage callback --> budget-meter                               |
               |                                                                 |
 agent-platform -- assign/read_signal --> hook-store (worktrees as task inboxes)|
               |    pack_context/unpack_context (cross-platform handoff)          |
 agent-session -+-- checkpoint/done commits --> hook-store                       |
               |    session events --> event-log                                  |
               |    handoff packing --> budget-meter                              |
 decision-artifacts (independent; invoked by agents/skills)                     |
 error-classifier (consumer maps each lib's typed errors to one record format) |
              +-----------------------------------------------------------------+
```

---

## Implementation Language

This is an open decision (see the stack review in the discussion that produced this directory). The specs are written so it does not block them.

| Library | Natural fit | Reason |
|---------|-------------|--------|
| hook-store, merge-queue | Any | I/O-bound git subprocess work |
| task-queue | Any (Go under the language decision) | File locking, an append-only log, and graph walks. A static binary suits a queue shared by many processes |
| event-log, budget-meter | Any | File I/O and arithmetic |
| test-adapters | Any | Subprocess and report parsing |
| watchdog | Rust or Go gives a single static binary; Python is acceptable | Needs to outlive the things it supervises |
| decision-artifacts | Python or TypeScript | Text processing, easy skill packaging |
| error-classifier | Any | Pure functions over data files; the record schema must be identical in every language |
| llm-gateway | Python or TypeScript | Where the provider SDKs live |
| agent-platform | Python or TypeScript | Where the harness SDKs and file-format helpers live |
| agent-session | Python or TypeScript | Where the LLM agent runtime lives |

Each library SHOULD also expose a thin CLI (`<name> <command> --json`) so a non-host-language consumer can use it by subprocess. The CLI is part of the contract.

---

## Suggested Build Order

1. **event-log** and **budget-meter**: smallest, and almost every other component emits to or reads from them.
2. **hook-store**: the foundation Phase 1 of the build assessment depends on.
3. **test-adapters**, then **merge-queue**.
4. **watchdog**.
5. **error-classifier**: small, no dependencies. Build early so the other libraries' errors map to one record from the start.
6. **decision-artifacts**: independent, can be built in parallel at any point.
7. **llm-gateway**: adopt or wrap first. Build last, only if the evaluation in its spec fails.
7. **agent-platform**: depends on `hook-store` being settled (worktree layout). Build after Phase 1; required before multi-platform work in Phase 4.
8. **agent-session**: depends on `hook-store`, `event-log`, and `budget-meter`. Build in Phase 2 — it is the skeleton all agent implementations use.
9. **task-queue**: depends on nothing. Build with Phase 1, because the Scheduler cannot dispatch without it. The `admit` callback is wired to `budget-meter` by the consuming application.
10. **metrics-store**: depends on nothing. JSONL backend can be wired in Phase 1 alongside `event-log`; SQL backend activated in Phase 3 when PostgreSQL is provisioned.

---

## Spec Template

Every library spec uses the same sections: 1 Purpose · 2 Scope and non-goals · 3 Concepts and data model · 4 Interface · 5 Behaviour · 6 Configuration · 7 Failure modes · 8 Acceptance criteria · 9 How UMAS uses it · 10 Source material and deviations · 11 Open questions.

A spec may end with an optional section 12, **Reference implementation (source code)**. It holds code moved verbatim from the original UMAS technical design. It is non-normative, may use UMAS names and paths, and is outside the independence rules; sections 1 to 11 are authoritative.
