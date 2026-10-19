# Modularisation Assessment (by Claude)

> Original assessment, written on 2026-10-19 before any `libs/` or `packs/` files existed. Recovered verbatim from the session transcript. The text from "I read the summary" to "redraw the phased plan" is unchanged. **Review against what has been done: updated 2026-10-20, see the last section.**

I read the summary, the build assessment, the architecture and process sections of the stack spec, and the outline of the tech spec and PRD. I haven't read the Part 2/3 code in full. This is a proposal for discussion, and nothing has been changed.

## Proposed decomposition

The specs split work by layer (orchestration, execution, verification, and so on). I'd split it by what can stand alone, in four tiers where each tier may only depend on the tiers above it.

**Tier 0: Contracts (specs and schemas, no code)**
- `events.jsonl` event schema (done, escalate, handoff_request, test_flaky)
- Hook/worktree directory layout and the `STATE.md` format
- `[umas:done]` commit trailer format and the SQL schema
- CLI/daemon JSON-RPC surface

**Tier 1: Standalone libraries (no UMAS dependency)**

| Component | Reusable outside UMAS as |
|---|---|
| **hook-store**: worktree create, state-commit protocol, stale detection and GC, crash recovery | Library plus CLI for any agent harness |
| **event-log**: append-only JSONL, query by hook, corruption recovery, replay | Library; feeds audit and debugging |
| **merge-queue**: batch merge, bisect, "verify command" plug-in | Works with any repo and any CI command, with no agents needed |
| **test-adapters**: pytest/jest/cargo normalised to `TestResult` | Library |
| **budget-meter**: token budgets, 80/90/95% alerts, handoff trigger, context compression | Library for any LLM app |
| **llm-gateway**: provider abstraction, failover, rate limiting | Probably an existing package (see below) |
| **watchdog**: hierarchical heartbeat supervision | Generic supervision tree |
| **decision-artifacts**: PRFAQ/ADR/Spec/GLOSSARY templates, shortcut-debt tracking | Claude Code skills |

**Tier 2: Content packs (prompts and skills, not code)**
- Minimalism ladder and anti-slop rules
- Two-axis code review
- The 5 specialised agents (PM, Architect, UX, Dev, Analyst)
- Router scoring heuristic and grilling protocol

**Tier 3: UMAS-specific glue**
- Coordinator, Scheduler, Project Monitors, Triage, Patrol

**Tier 4: Shells**
- CLI, dashboard, installers, platform adapters

**Where the reuse is**
- **Tier 2 gives the most reuse for the least cost.** The ladder, anti-slop and review packs can ship as Claude Code skills or plugins on day one, usable by people who never install UMAS.
- **The specialised agents shouldn't be code.** The build assessment prices them at 35M tokens as Python classes, but they are prompt stubs. As versioned prompt packs they are cheaper, easier to iterate and easier to port across Claude Code, Bob and Copilot.
- **Tier 0 is the real product.** If the event and hook contracts are stable and language-neutral, the dashboard, monitors and third-party tools are all just consumers.

## Stack review

Ordered by impact:

1. **Three languages and four IPC mechanisms.** The spec uses Rust and Python plus TypeScript. It also uses a Unix-socket JSON-RPC, stdio JSONL, polled `events.jsonl`, and a shared database. Rust and Python both writing to SQLite probably explains why exception flows 4.12 and 4.13 (DB lock, concurrent CLI) exist. I'd have one process own the database and one control channel, and keep `events.jsonl` as an audit log only.
2. **Rust looks hard to justify.** The workloads are git subprocess calls, process supervision and 5–30 agents, all I/O-bound. Rust buys a single static binary and a memory-safe daemon. The cost is borrow-checker iteration in LLM-generated code, plus a language boundary through the middle of the system. I'd lean towards Python for all logic, with Rust only for a thin supervisor or CLI if single-binary distribution matters. launchd/systemd can already do top-level restarts. This is the biggest decision and the biggest lever on your 162M estimate.
3. **Inconsistent dashboard backend.** The spec says "FastAPI OR Express", while the process model says Node, and Socket.io is awkward with FastAPI. Pick FastAPI with plain WebSocket or SSE. The CLI and dashboard should also share one API definition (OpenAPI), not two.
4. **Observability and data stores are heavy for MVP.** Postgres, TimescaleDB, Prometheus, Jaeger and Loki are all listed. At this scale, SQLite and OpenTelemetry as the instrumentation API are enough, with backends optional. TimescaleDB overlaps with Prometheus.
5. **Build versus buy.** Provider failover (LiteLLM or the Claude Agent SDK) and merge queues (GitHub merge queue, Mergify) already exist. I'd build only the pieces that carry the design's novelty: hooks, signalling, minimalism, and handoff.
6. **Stale model and pricing basis.** The summary pins `claude-3-5-sonnet-20241022` and the cost table uses 3.5 Sonnet pricing. Model IDs should come from config, and the estimate should be re-based on current models and pricing.
7. **Unstated runtime question.** The platform-adapter module implies agents are external CLIs (Claude Code, Bob, Copilot) running in worktrees. If so, "Python agent runtime" is mostly an orchestrator of subprocesses, not an LLM loop, which shrinks the Agent Execution estimate.

## Decisions for you
- Would you accept Python-only logic with Rust optional, or is Rust a requirement (for example enterprise or Bob constraints)?
- Are agents external CLIs driven in worktrees, or an in-process LLM loop through an SDK?
- Is the aim to publish Tier 1 and 2 as separate open packages, or only keep clean seams internally? That decides repo layout (monorepo with independent packages versus separate repos).

If you agree, I can redraw the phased plan and token estimate around these tiers.

---

# Review against what has been done (2026-10-20)

Status: **Done**, **Partial**, **Not done**, **Changed** (done differently from the proposal). "Not decided" means no answer from you yet.

## Decomposition

| Proposal | Status | What exists |
|---|---|---|
| Tier 0: contracts as their own specs | Partial | No standalone contract specs. The `events.jsonl` schema is in [event-log](libs/event-log.md), `STATE.md` and the commit trailers are in [hook-store](libs/hook-store.md), and the error record is a new contract in [error-classifier](libs/error-classifier.md). The SQL schema was dropped from the libs on purpose (they use files or git). The CLI/daemon JSON-RPC surface is not specified anywhere. |
| Tier 1: 8 libraries | Done | All eight are in `libs/`, each a standalone spec with acceptance criteria and a "How UMAS uses it" section. |
| Tier 1 additions | Changed | `error-classifier` was added (not in my plan; it was a gap in Bob's review). `agent-platform` was also added to Tier 1, so platform adapters moved out of Tier 4. I did not write `agent-platform`; it was in the repo when I updated this file. |
| Tier 2: content packs | Done | Eight packs in `packs/`. Ladder and anti-slop became two packs. `communication-modes` and `test-policy` were added beyond my four bullets. |
| Tier 2 shipped "as Claude Code skills on day one" | Not done | Each pack describes how it becomes a `SKILL.md`, but no skill file has been built. |
| Specialised agents as prompt packs, not code | Done | [specialist-agents](packs/specialist-agents.md) defines prompts and output schemas for the five roles. The original Python stubs sit in its section 12 as reference. |
| Tier 3: UMAS glue (Coordinator, Scheduler, Monitors, Triage, Patrol) | Not done | Left in the original specs. The budget half of the Scheduler is covered by [budget-meter](libs/budget-meter.md); the capacity and dispatch half is not covered anywhere. |
| Tier 4: shells (CLI, dashboard, installers) | Partial | The dashboard is decided (below). The CLI and installers are untouched. |
| "Each tier depends only on the tiers above it" | Done | Enforced by the independence rules in `libs/README.md` and `packs/README.md`: no UMAS names, no cross-library imports, no cross-pack dependencies. |

## Where the reuse is

| Claim | Status |
|---|---|
| Tier 2 gives the most reuse for the least cost | Plausible, not tested. The packs have fixtures and acceptance criteria but have not been run against a model. |
| Specialised agents are cheaper as prompt packs | Not verified. The 35M-token estimate in the build assessment has not been re-costed. |
| Tier 0 is the real product | Not acted on. The contracts are spread over the libs rather than being a separate set. |

## Stack review

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Three languages, four IPC mechanisms | Partial | The libs use files only, with no database, and `events.jsonl` is the shared transport. The system-wide choice of one database owner and one control channel is not made, and the SQL blocks are still in the original specs. |
| 2 | Rust hard to justify | Not decided | The libs are language-neutral on purpose and each exposes a `<name> <cmd> --json` CLI. The Rust reference code is kept in section 12 of the specs. |
| 3 | Dashboard backend inconsistent | Partial | [ADR-0001](docs/decisions/ADR-0001-minimal-html-dashboard.md) picks a read-only HTML page that polls the API, which removes the Socket.io question. FastAPI vs Express is still open, and the single shared OpenAPI definition is not written. |
| 4 | Heavy observability and data stores | Partial | The libs emit events through callbacks and need no OpenTelemetry, Prometheus or database. TimescaleDB and the metrics store are not decided. |
| 5 | Build versus buy | Partial | [llm-gateway](libs/llm-gateway.md) is written "adopt first", with an evaluation checklist, which matches my advice. [merge-queue](libs/merge-queue.md) is a full build spec with no adopt-or-build evaluation, although I suggested GitHub merge queue or Mergify. |
| 6 | Stale model and pricing basis | Partial | [llm-gateway](libs/llm-gateway.md) forbids hard-coded model IDs and the pricing table is supplied by the caller in [budget-meter](libs/budget-meter.md). The original specs still pin `claude-3-5-sonnet-20241022`, and the cost estimate is not re-based. |
| 7 | External CLIs versus in-process loop | Not decided | [agent-platform](libs/agent-platform.md) is written as if agents are external harnesses (`assign` writes files and does not spawn processes). That is a stance in the spec, not your answer. |

## Decisions for you

| Question | Status |
|---|---|
| Python-only with Rust optional, or Rust required | Not decided |
| External CLI agents or in-process SDK loop | Not decided (`agent-platform` assumes external) |
| Publish Tier 1 and 2 as separate packages, or keep internal seams | Not decided. Both sets live in `libs/` and `packs/` in this repo, and the independence rules make either choice possible. |

## Work I did that the proposal did not include

- Moved implementation code from the three technical design files into a non-normative "12. Reference implementation" section of each matching lib and pack (20 blocks, verbatim, with pointers left behind). Code with no standalone home stayed in place.
- Wrote `error-classifier` and recorded the dashboard decision as ADR-0001.
- Added a source-deviations section (section 10) to every spec, listing where the spec differs from the original design and why.

## Things that were wrong or still inconsistent

- I told you earlier that `llm-gateway` contradicted my "buy" advice. That overstated it: the spec says adopt first and is mostly a requirements checklist. The real gap is `merge-queue` (row 5 above).
- The library count said "nine" in `libs/README.md` and `UMAS-TECH-DESIGN-SPEC.md` while the folder had ten, and `agent-platform` was missing from the main spec and summary tables. Fixed on 2026-10-20.
- The `error-classifier` record is not yet referenced from the other libs. Each still has its own error table.
- The build assessment's token estimates and phase plan were not redrawn, which my last line offered to do.
