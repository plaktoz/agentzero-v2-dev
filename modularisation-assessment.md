# Modularisation Assessment: Unified Multi-Agent Development System

Merged from two assessments: Bob (IBM), written 2026-10-18 and updated 2026-10-21, and Claude, written 2026-10-19 and updated 2026-10-20. Where they disagree, both views are shown.

Reviewed against the state of the repo on 2026-10-21: 12 library specs, 8 content-pack specs, the section 12 reference-code appendices, and the dashboard decision record.

Every file is linked once, in the tables of section 2 and the decisions table in section 4. Everywhere else it is named in backticks.

## Status legend

| Symbol | Meaning |
|---|---|
| Done | Extracted as a dedicated spec and matches the recommendation |
| Partial | Extracted or decided, with a gap worth noting |
| Not done | Not extracted or not acted on |
| Merged | Absorbed into another item; the right call |
| Changed | Done differently from what was proposed |
| Superseded | A later decision replaced the recommendation |
| Not decided | Waiting on an answer from you |

---

## 1. Diagnosis and approach

The 10 modules in the spec are feature domains, not reusable components. Both assessments cut horizontally instead: by what can stand alone, in tiers where each tier depends only on the tiers above it.

| Tier | Contents | State |
|---|---|---|
| 0. Contracts | Event schema, hook layout and `STATE.md`, commit trailers, error record, CLI/daemon JSON-RPC surface | Partial. The contracts live inside the libs rather than as a separate set; the JSON-RPC surface is not specified anywhere. The SQL schema was dropped from the libs on purpose (files or git only). |
| 1. Libraries | Code with no UMAS dependency | Done. 12 specs. |
| 2. Content packs | Prompts, rules, skills (not code) | Done as specs. No `SKILL.md` has been built yet. |
| 3. UMAS glue | Coordinator, Scheduler, Project Monitors, Triage, Patrol | Not done. Still in the original specs. |
| 4. Shells | CLI, dashboard, installers | Partial. Only the dashboard is decided. |

Tier 1 and Tier 2 is a cleaner cut than Bob's original five categories, because it separates how things are built from what agents do. The independence rules (no UMAS names, no cross-library imports, no database, language-neutral contract, versioned formats, safe-by-default, observable via callbacks) are enforced by the two README files, and that is what makes "each tier depends only on the tiers above" true.

---

## 2. Component breakdown

### 2.1 Tier 1 libraries

| Library | Origin (Bob / Claude name) | Status | Notes |
|---|---|---|---|
| [hook-store](libs/hook-store.md) | `worktree-manager` / `hook-store` | Done | Renamed because a worktree is a hook holding a unit of work. Adds leases, `STATE.md`, GC and recovery. |
| [event-log](libs/event-log.md) | `event-log` / `event-log` | Done | Adds cursor polling, rotation, repair and redaction. Unifies the two inconsistent envelope shapes in the source. Open question: is a pure-file design enough at 20-30 concurrent writers, or should SQLite WAL be an alternative backend? |
| [budget-meter](libs/budget-meter.md) | `token-budget` / `budget-meter` | Done | Adds reservations, multi-process ledger, live limit changes, and `pack()` for context fitting. The mechanical half of Bob's `context-compressor` lives here. |
| [merge-queue](libs/merge-queue.md) | `umas-merge-queue` / `merge-queue` | Done | Prefix-bisect replaces split-half (which misses combination failures). Adds crash recovery, baseline check, persisted state. The original code is flagged defective (CAS issue, no conflict handling, in-memory queue). **No adopt-or-build evaluation**, although Claude suggested GitHub merge queue or Mergify. |
| [test-adapters](libs/test-adapters.md) | `umas-test-runner` / `test-adapters` | Done | Framework detection, normalised `TestResult`, flaky tracking, adapter interface. Policy is deliberately left out. |
| [llm-gateway](libs/llm-gateway.md) | `llm-gateway` / `llm-gateway` | Done | Written "adopt first" with an evaluation checklist, which matches Claude's buy advice. Forbids hard-coded model IDs. Has the no-blind-retry rule, circuit breaker, and per-class error taxonomy. |
| [watchdog](libs/watchdog.md) | `umas-daemon` / `watchdog` | Done | A generic supervision library. The three-tier Daemon, Triage, Patrol design is three levels of it. The Rust Daemon is demoted to reference code. |
| [decision-artifacts](libs/decision-artifacts.md) | not in Bob's plan / `decision-artifacts` | Done | PRFAQ/ADR/Spec/GLOSSARY templates and shortcut-debt tracking. |
| [error-classifier](libs/error-classifier.md) | `error-classifier` / not in plan | Done | Added after Bob's review found the gap. A shared record format with deterministic rules, not a shared import. Adds redaction, `retry_plan`, agent and human renderings, fingerprinting and pattern alerts. Ships no catalog. Five open questions in its section 11 (for example whether unmatched errors default to P2 or P1). The other libs map to it by data only (see section 5). |
| [agent-platform](libs/agent-platform.md) | `CodingAgentAdapter` plugin registry (Category D) / platform adapters in Tier 4 | Done, Changed | Moved from Tier 4 to Tier 1. Harness adapters only, never LLM providers. `assign` writes files and does not spawn processes. `read_signal` is non-blocking. Context packs carry a SHA-256 checksum and reject path traversal. Built-in adapters: `claude-code`, `ibm-bob`, `copilot`. Bob's original advice to unify it with `llm-gateway` was wrong: one routes work to harnesses, the other routes inference calls. |
| [agent-session](libs/agent-session.md) | `agent-session` / not in plan | Done | Shared lifecycle skeleton for all six agent types (`spawned`, `active`, `handoff`, `crashed`, `done`), durable `STATE.md`, checkpoint commits, handoff packets, token thresholds. Reference code for `WorkerAgent` and `CoordinatorAgent` is in its section 12. |
| [metrics-store](libs/metrics-store.md) | `umas-metrics-collector` / not in plan | Done | Two backends behind one interface: JSONL ledger (Phase 1-2), then a relational table in SQLite or PostgreSQL (Phase 3+). TimescaleDB is an optional one-line upgrade, not a dependency. Source adapters turn `budget-meter`, `event-log` and `test-adapters` callbacks into metric rows. |

Merged, with no library of their own:

| Item | Where it went |
|---|---|
| `signal-bus` (Bob) | Split between `hook-store` (commit message format) and `event-log` (JSONL appends). Each half belongs with the library that owns the transport. |
| `context-compressor` (Bob) | Two concerns: fitting content into a limit is `budget-meter` `pack()`; deciding what goes in a handoff packet is the Developer prompt in `specialist-agents`. |
| `minimalism-enforcer` (Bob) | Moved to Tier 2 as `minimalism-ladder`. Bob's original placement in agent infrastructure was wrong; the ladder is a prompt and rule set. |

Not extracted:

| Item | State |
|---|---|
| `structured-output-parser` (Bob) | Not done. Each pack defines its own output schema but nothing specifies how an agent validates and extracts a structured response. Pydantic may be enough; a short decision record either way is needed. |
| Scheduler capacity and dispatch half (`task-queue`) | Not done. The budget half is `budget-meter`. The semaphore, queue and dispatch half is in no spec. Either extract it or document it as a deliberate UMAS-internal component composing `budget-meter` and `watchdog`. |

### 2.2 Tier 2 content packs

| Pack | Covers | Assessment |
|---|---|---|
| [minimalism-ladder](packs/minimalism-ladder.md) | 6-rung ladder, three enforcement levels, shortcut format | Correct tier. |
| [anti-slop](packs/anti-slop.md) | 7-category slop definition, two-pass review, forbidden-phrase linter | Novel addition, high value. Split from the ladder into its own pack. |
| [communication-modes](packs/communication-modes.md) | Compact (agent to agent) and plain (human-facing) registers | Novel addition. Addresses token waste. |
| [two-axis-review](packs/two-axis-review.md) | Standards and Spec passes, finding schema, severity gate | Replaces the `CodeReviewAgent` stub. |
| [specialist-agents](packs/specialist-agents.md) | Analyst, PM, UX, Architect, Developer prompts and output contracts | Done as prompt packs, not code. The original Python stubs sit in its section 12. Covers the 35M-token cost driver. |
| [router-heuristic](packs/router-heuristic.md) | Scoring rubric, weights, route bands, classification prompt | Fixes the keyword-matching Router gap. The deterministic scorer keeps arithmetic out of the model. The Router itself is still to be built. |
| [grilling](packs/grilling.md) | Bounded questioning protocol, alignment summary, trigger rules | Correct extraction. |
| [test-policy](packs/test-policy.md) | Selective vs strict modes, risky-logic classifier, trivial-change exemption | Policy correctly separated from `test-adapters`. |

Open points on the packs:
- Shipping "as Claude Code skills on day one" is **not done**. Each pack describes how it becomes a `SKILL.md`, but none has been built.
- "Tier 2 gives the most reuse for the least cost" is plausible but untested. The packs have fixtures and acceptance criteria and have not been run against a model.
- "Specialist agents are cheaper as prompt packs" is unverified. The 35M-token estimate has not been re-costed.

### 2.3 Tier 4 shell: dashboard

[ADR-0001](docs/decisions/ADR-0001-minimal-html-dashboard.md) chose a minimal read-only static HTML page that polls the REST API. It has no React and no build step, and it uses the same API definition as the CLI. This was option B; neither assessment's own recommendation (Bob: a terminal UI first; Claude: pick FastAPI with WebSocket or SSE) was adopted as written. Bob's React component list (`AgentCard`, `WorkBundleTree`, `MergeQueueView`, `MetricsPanel`, `EventStream`, `EscalationBanner`) is **superseded** and was kept only so the decision can be reviewed. The React stack stays in the stack spec marked as superseded for the first release.

Still open: no spec exists for the page or for the REST endpoints it reads; the CLI and installers are untouched.

---

## 3. Technology stack review

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Three languages and four IPC mechanisms (JSON-RPC socket, stdio JSONL, polled `events.jsonl`, shared database) | Partial | The libs use files only, with no database, and `events.jsonl` is the shared transport. The system-wide choice of one database owner and one control channel is not made, and the SQL blocks are still in the original specs. Bob adds that there is no broker between the Rust and Python processes; file-based IPC is fine for Phase 1-2, but the Phase 3 bottleneck risk remains. Recommendation: design the broker interface now, implement it when scale demands it. |
| 2 | Rust: justified or not | Not decided, views differ | Bob: Rust for Daemon, Scheduler, TestRunner and CLI is the correct call (cross-platform binary, no runtime dependency, async); no change needed. Claude: the workload is git subprocess calls and I/O-bound supervision of 5-30 agents, so Rust adds borrow-checker iteration and a language boundary; lean Python for all logic with Rust only for a thin supervisor or CLI. This is the biggest lever on the 162M estimate. The libs are language-neutral on purpose, so either choice works. |
| 3 | Dashboard backend inconsistent (FastAPI or Express, Socket.io) | Partial | ADR-0001 removes the Socket.io question. FastAPI vs Express is still open and the single shared OpenAPI definition is not written. Claude recommends FastAPI. |
| 4 | Heavy observability and data stores | Partial | The libs need no OpenTelemetry, Prometheus or database. TimescaleDB is resolved (optional upgrade, see `metrics-store`). Claude's view that SQLite plus OpenTelemetry as the instrumentation API is enough at this scale still stands; Prometheus, Jaeger and Loki are not decided. Bob agrees OpenTelemetry is the right vendor-neutral choice. |
| 5 | Build versus buy | Partial | `llm-gateway` is adopt-first. `merge-queue` is a full build spec with no evaluation (see 2.1). Build only what carries the design's novelty: hooks, signalling, minimalism, handoff. |
| 6 | Stale model and pricing basis | Partial | `llm-gateway` forbids hard-coded IDs and `budget-meter` takes the pricing table from the caller. The original specs still pin `claude-3-5-sonnet-20241022` and the cost estimate is not re-based. |
| 7 | External CLI agents or in-process LLM loop | Not decided | `agent-platform` is written as if agents are external harnesses. That is a stance in the spec, not your answer. If agents are external, the Python agent runtime is mostly a subprocess orchestrator and the Agent Execution estimate shrinks. |
| 8 | JWT/RBAC deferred to Phase 4 although the PRD requires RBAC from the start | Not done | No lib or pack addresses authentication. The role and permission data model and middleware hook point are not designed. A security risk. |
| 9 | SQLite to PostgreSQL path; Python for agent logic | Holds up | Pragmatic; LLM SDKs are Python-first. |

---

## 4. Decisions required

| Decision | Options | Recommendation | Status |
|---|---|---|---|
| Python-only logic with Rust optional, or Rust required | See stack item 2 | Claude: Python-first. Bob: keep Rust. | Not decided |
| External CLI agents or in-process SDK loop | See stack item 7 | None given | Not decided (`agent-platform` assumes external) |
| Publish Tier 1 and 2 as separate packages, or keep internal seams | Monorepo of independent packages, or separate repos | None given | Not decided. The independence rules keep both options open. |
| Dashboard | Terminal UI, minimal HTML, full React | Bob: TUI first, React in Phase 4 | Resolved: minimal read-only HTML |
| TimescaleDB | Hard dependency, or optional upgrade | Optional | Resolved: JSONL ledger, then PostgreSQL, then TimescaleDB as a one-liner |
| Router design | Keyword stub, or scoring heuristic | Interface now, keyword match fine for v1 | Resolved: scoring heuristic pack |
| `CodingAgentAdapter` and `LLMGateway` | Two abstractions, or unified | Keep separate | Resolved. IBM Bob registers in both with separate credentials. Stakeholder sign-off still pending. |
| IPC mechanism | Filesystem, or message broker | Broker interface now, filesystem implementation for Phase 1-2 | Deferred, flagged in `event-log` |
| Auth | Defer to Phase 4, or RBAC skeleton in Phase 1 | RBAC data model and middleware hook in Phase 1 | Not decided |

---

## 5. Open gaps, in priority order

1. **RBAC data model.** A security gap. It should be a UMAS-specific schema decision in Phase 1, not Phase 4.
2. **Scheduler capacity extraction (`task-queue`)**, or a statement that it is a UMAS-internal component.
3. **`structured-output-parser` decision record.**
4. **IBM Bob sign-off** on registering in both `agent-platform` and `llm-gateway`, needed before Phase 2.
5. **Follow-ups from closed items:**
   - Re-base the 25M dashboard token estimate for the HTML page, and decide whether it ships in Phase 2.
   - Choose the dashboard backend framework and write the shared OpenAPI definition.
   - Re-cost the build assessment's token estimates and redraw the phase plan around the tiers (offered by Claude, not done).
   - Add an adopt-or-build evaluation to `merge-queue`.
   - Build the `SKILL.md` files for the packs, and run them against a model.
   - Specify the CLI/daemon JSON-RPC surface and the REST endpoints.
6. **Cross-library mention to check:** `metrics-store` names `error-classifier` as the source of two metrics (`error.p0_count`, `error.p1_count`). Check this against the no-import rule; it is acceptable only if it stays a data-format reference.

Closed since the earlier reviews: `error-classifier`, `agent-session`, `metrics-store`, the dashboard decision, the TimescaleDB question, and the library count (the READMEs said "nine" while the folder had ten; the main spec and summary tables were missing `agent-platform`).

---

## 6. Work beyond the original proposals

- Moved implementation code from the three technical design files into a non-normative "12. Reference implementation" section of each matching lib and pack (20 blocks, verbatim, with pointers left behind). Code with no standalone home stayed in place. The `agent-session` and `metrics-store` sections 12 were added separately.
- Added a "source material and deviations" section (section 10) to every spec.
- Wired the other libs to `error-classifier` by data only: each keeps its own typed errors, and its failure-modes section ends with an "Error records" table of suggested `recoverability`, with `llm-gateway` having an equivalent note on its error taxonomy. Severity stays the consumer's policy. No imports were added.

## 7. Corrections to the earlier assessments

- Claude's earlier claim that `llm-gateway` contradicted the "buy" advice was an overstatement. The spec is adopt-first. The real gap is `merge-queue`.
- Bob's recommendation to unify `CodingAgentAdapter` with `LLMGateway` was wrong, as above.
- Bob's note that `error-classifier` was "not yet wired into the other libs" is out of date; see section 6.
- Claude's note that the metrics store was undecided is out of date; see `metrics-store`.
- `agent-platform` was added to the repo by someone other than Claude. It, `agent-session` and `metrics-store` were not in Claude's plan.
