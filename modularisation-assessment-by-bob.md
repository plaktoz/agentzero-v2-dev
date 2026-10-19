# Modularisation Assessment: Unified Multi-Agent Development System

**Author:** Bob (IBM)
**Date:** October 18, 2026 · **Reviewed:** October 19, 2026 · **Updated:** October 21, 2026
**Based on:** PRD v1.0, TECHNICAL-DESIGN-SUMMARY.md v1.1, TECHNICAL-DESIGN-SPEC.md v1.1, TECHNICAL-DESIGN-SPEC-PART2.md, TECHNICAL-DESIGN-SPEC-PART3.md, UMAS-BUILD-ASSESSMENT.md
**Review against:** `libs/` (12 library specs), `packs/` (8 content-pack specs), the reference-code appendices (section 12 of each spec), and [`docs/decisions/ADR-0001-minimal-html-dashboard.md`](docs/decisions/ADR-0001-minimal-html-dashboard.md)

---

## Status legend

| Symbol | Meaning |
|--------|---------|
| ✅ Done | Extracted as a dedicated spec file; content matches the recommendation |
| ⚠️ Partial | Extracted but with a gap or deviation worth noting |
| ❌ Not done | Not yet extracted |
| 🔀 Merged | Absorbed into another item — correct call, noted here |
| 💡 Reassessed | The original recommendation has been revised after seeing the full libs/packs content |

---

## 1. The Core Problem with the Current Structure

The 10 modules in the spec are **feature domains**, not **reusable components**. Almost every module is a monolithic vertical slice. To break things into reusable parts, we need to cut *horizontally* — extract the cross-cutting concerns that are currently duplicated or entangled across modules.

**Review note:** The `libs/` and `packs/` folders confirm this diagnosis and act on it well. The split into Tier 1 (code libraries) and Tier 2 (prompt/rule packs) is a cleaner cut than the original five categories proposed here — it separates *how* things are built from *what agents do*. The original assessment should have called this out explicitly.

---

## 2. Proposed Component Breakdown

---

### Category A — Platform-Agnostic Primitives

These have zero dependency on UMAS-specific concepts. They can be open-sourced as standalone libraries.

| Component | What it does | Used by | Reuse outside UMAS | Status | Remarks |
|---|---|---|---|---|---|
| **`event-log`** | Append-only `.jsonl` event store with schema validation | SessionHistory, Daemon heartbeat, Audit logging | Any agent framework, audit tooling | ✅ Done | [`libs/event-log.md`](libs/event-log.md) — spec is thorough. Adds cursor-based polling, rotation, repair, and redaction that the original design lacked. One important deviation documented: the source had two inconsistent envelope shapes; the spec unifies them. Agree with this call. |
| **`token-budget`** | Budget tracking, threshold alerts (80/90/95%), graceful exhaustion | Scheduler, WorkerAgent, CoordinatorAgent | Any multi-LLM system | ✅ Done | [`libs/budget-meter.md`](libs/budget-meter.md) — renamed `budget-meter`, which is clearer. Adds reservations (estimate → true-up), multi-process safety via ledger file, live limit changes, and the context-packing `pack()` function. The original assessment missed context packing as a budget concern; the spec correctly folds it in. Strongly agree. |
| **`worktree-manager`** | Git worktree lifecycle (create, commit, recover, clean up) | Context Persistence, MergeQueue, Agent handoff | Any git-based workflow tool | ✅ Done | [`libs/hook-store.md`](libs/hook-store.md) — renamed `hook-store`, which better describes the concept (a worktree is a *hook* holding a unit of work). Adds lease management, `STATE.md` state file, GC, and recovery. Agree with the rename and the additions. |
| **`signal-bus`** | `[umas:done]` / `[umas:checkpoint]` commit message protocol + `.umas/events.jsonl` appends | WorkerAgent → Coordinator | Replaceable with a message queue later | 🔀 Merged | Correctly absorbed into `hook-store` (commit message format §5.2) and `event-log` (JSONL signalling). There is no standalone `signal-bus` lib, and there shouldn't be — the two halves of the signal protocol belong with the libs that own the transports. Agree with the merge. |
| **`error-classifier`** | P0/P1/P2/P3 classification, transient vs. permanent, structured error payload | All modules | Any system that surfaces errors to both humans and agents | ✅ Done | [`libs/error-classifier.md`](libs/error-classifier.md) — extracted as a shared **record format plus deterministic rules**, not a shared import (the libs may not import each other, so each consumer maps its own typed errors to the record). Adds secret redaction, retry advice (`retry_plan`), agent and human renderings, fingerprinting and pattern alerts (P0 immediately, P1 more than 3 in 10 minutes, P2/P3 digest). The library ships no catalog, because the PRD's error codes name UMAS components. Five open questions in §11 (for example whether unmatched errors default to P2 or P1). Not yet wired into the other libs' specs: each still has its own error table. |

---

### Category B — Agent Infrastructure (Reusable Across Agent Types)

All 5 specialised agents plus the WorkerAgent share identical lifecycle concerns. These should be a base layer, not copy-pasted per agent.

| Component | What it does | Currently duplicated in | Status | Remarks |
|---|---|---|---|---|
| **`agent-session`** | Spawn → execute → checkpoint → handoff lifecycle with token tracking | WorkerAgent, all 5 specialised agents | ✅ Done | [`libs/agent-session.md`](libs/agent-session.md) — extracted as the shared lifecycle skeleton for all 6 agent types. Covers the `spawned → active → handoff → crashed → done` state machine, durable `STATE.md`, checkpoint commits, handoff packet construction, and token threshold monitoring. Reference implementations added: `WorkerAgent` (§12.1, source `TECHNICAL-DESIGN-SPEC-PART3.md` §5.2.2), WorkerAgent config YAML (§12.2, source §5.2.3), and `CoordinatorAgent` (§12.3, source `TECHNICAL-DESIGN-SPEC-PART2.md` §4.2.2). All three source sections tombstoned. |
| **`context-compressor`** | lite/full/ultra compression strategies for context handoff | Agent handoff (Module 10), cross-platform transfer | 🔀 Merged | The *mechanical* side (fit content into a token limit) is covered by `budget-meter`'s `pack()` function. The *content* side (what goes into a handoff packet — task, decisions, notes) is addressed by the Developer prompt in `packs/specialist-agents.md`. This is the right split. The original assessment treated it as a single thing; it is two concerns. Agree with the merge. |
| **`llm-gateway`** | Unified interface over Anthropic/OpenAI/Gemini/local, with failover and retry | CoordinatorAgent, WorkerAgent, all specialised agents, CodeReviewAgent | ✅ Done | [`libs/llm-gateway.md`](libs/llm-gateway.md) — good spec. Crucially, it is written as an *evaluation checklist* first, not a build prescription ("adopt first"). The no-blind-retry-loops rule, circuit breaker, and per-class error taxonomy are all present. Open question §11.1 (is IBM Bob a chat-completion API or an agent platform?) is the right question to surface — it determines whether Bob belongs here or in platform adapters. |
| **`minimalism-enforcer`** | 6-rung ladder logic, code-avoided tracking, reuse percentage | DeveloperAgent today — should be available to all agents | ✅ Done | Extracted as [`packs/minimalism-ladder.md`](packs/minimalism-ladder.md) — correctly placed in Tier 2 (content pack) rather than Tier 1 (code library). The ladder is a *prompt and rule set*, not executable logic. Three enforcement levels (lite/full/ultra) are defined. The original assessment placed this in Category B (agent infrastructure libs), which was wrong — it belongs with the packs. |
| **`structured-output-parser`** | Parse LLM responses into typed Pydantic models | Every agent that returns structured results | ❌ Not done | No dedicated spec. Each pack defines its own output schema (e.g., `specialist-agents.md` has per-role output contracts, `router-heuristic.md` has a scoring output). The *schemas* are specified per pack, but the *parsing mechanism* (how an agent validates and extracts a structured response) is not. This may be intentional — Pydantic is the obvious Python implementation and may not need a spec. Recommend a brief decision record either way. |

---

### Category C — Infrastructure Services (Run Once, Serve Everything)

These are standalone daemons/processes, not libraries.

| Service | Responsibility | Talks to | Status | Remarks |
|---|---|---|---|---|
| **`umas-daemon`** (Rust) | Watchdog + heartbeat supervisor | All services | ✅ Done | Covered by [`libs/watchdog.md`](libs/watchdog.md) — correctly generalised. Rather than a UMAS-specific Daemon binary, `watchdog` is a reusable supervision library. The three-tier architecture (Daemon → Triage → Patrol) maps to three levels of the same library. The Rust Daemon from the original spec is demoted to a reference implementation (§12.1). This is the right call. |
| **`umas-scheduler`** (Rust) | Capacity management, token budget enforcement, queue | WorkerAgents | ⚠️ Partial | The budget side is covered by `budget-meter`. The *capacity* side (semaphore, agent queue, dispatch) has not been extracted as a standalone library. The Rust `Scheduler` struct in `budget-meter`'s §12.1 is marked as a reference implementation only. This is a gap for Phase 3 (multi-agent). Recommend either extracting a `task-queue` lib or documenting that the Scheduler is a UMAS-specific component that composes `budget-meter` and `watchdog`. |
| **`umas-merge-queue`** (Python) | Batch merge with bisecting | TestRunner, main branch | ✅ Done | [`libs/merge-queue.md`](libs/merge-queue.md) — significant improvement over the source. Prefix-bisect replaces the split-half approach (which misses combination failures and costs more runs). Crash recovery, baseline check, and persisted state are all added. The reference implementation §12.1 is flagged as defective (CAS issue, no conflict handling, in-memory queue). Strongly agree with the rewrite. |
| **`umas-test-runner`** (Rust) | Parallel test execution across frameworks | MergeQueue, VerificationLayer | ✅ Done | [`libs/test-adapters.md`](libs/test-adapters.md) — correctly language-agnostic. Framework detection, normalised `TestResult`, flaky test tracking, and the adapter interface for adding new frameworks are all present. Policy (TDD, coverage targets) is explicitly removed from the lib and left to callers. Agree. |
| **`umas-metrics-collector`** | Time-series writes to TimescaleDB | All services via OpenTelemetry | ✅ Done | [`libs/metrics-store.md`](libs/metrics-store.md) — extracted with the TimescaleDB dependency explicitly removed. Two backends behind one interface: JSONL file ledger (Phase 1–2) and a relational `metrics` table in SQLite or PostgreSQL (Phase 3+). TimescaleDB is documented as a one-line optional upgrade (`create_hypertable`), not a hard dependency. The lib provides source adapters that translate `budget-meter`, `event-log`, and `test-adapters` callback events into metric rows without modifying those libraries. |

---

### Category D — Platform Adapters (Plugin Pattern)

The multi-platform support (Module 7) is already designed as adapters — but it should be formalised as a **plugin registry** pattern so third parties can register new platforms without touching core code.

```
CodingAgentAdapter (base)
├── ClaudeCodeAdapter
├── IBMBobAdapter
├── CopilotAdapter
└── [pluggable: CustomAdapter]
```

Each adapter implements: `authenticate`, `spawn_agent`, `transfer_context`, `get_capabilities`.

**Status:** ✅ Done

**Remarks:** [`libs/agent-platform.md`](libs/agent-platform.md) — extracted as a thin plugin registry, which is the right shape. Key design decisions made in the spec:

- **Harness adapters only, not LLM providers.** The PRD conflated the two. `agent-platform` covers work assignment, completion signalling, and cross-platform context transfer. LLM inference stays in `llm-gateway`. IBM Bob registers in *both* independently.
- **`assign` writes files; it does not spawn processes or call APIs.** Claude Code, Bob, and Copilot are independent tools. UMAS presents work to them; it does not start them.
- **`read_signal` is non-blocking.** The caller drives the polling loop. Three signal methods defined: `commit-message` (hook log), `file` (signal JSON), `none` (file mtime for IDE tools like Copilot).
- **Context pack with SHA-256 checksum.** Validates integrity across platform boundaries; path traversal attacks rejected.
- **Three built-in adapters:** `claude-code`, `ibm-bob`, `copilot`. All overridable. Custom adapters registered via `register(adapter)`.

The IBM Bob split (harness vs. LLM provider) is answered in §9 and §11 of the spec: register in both places with separate credentials. Open question §11.1 documents this explicitly for stakeholder sign-off.

The original recommendation to "unify `CodingAgentAdapter` with `LLMGateway`" was **wrong** — they serve different purposes at different layers. `llm-gateway` routes inference calls; `agent-platform` routes work assignments to harnesses. Keeping them separate is the correct call.

---

### Category E — UI Components (Dashboard)

**Update (October 20):** the dashboard is now a minimal read-only HTML page that polls the API ([ADR-0001](docs/decisions/ADR-0001-minimal-html-dashboard.md)). The React component list below was written for the React option and is **superseded**. It is kept so the decision can be reviewed.

The React dashboard had **zero component specs**. Defining reusable UI components up front would have avoided the 25M token cost of iterative UI work.

| Component | Reuse | Status | Remarks |
|---|---|---|---|
| **`<AgentCard>`** | Agent list view + status page | 💡 Superseded | No React component specs exist, and none are needed now. The minimal page needs a table of agents and states. |
| **`<WorkBundleTree>`** | Work bundle show + watch command | 💡 Superseded | — |
| **`<MergeQueueView>`** | Merge queue state + escalation tracker | 💡 Superseded | — |
| **`<MetricsPanel>`** | Tokens, cost, quality, agents — same shell, different data source | 💡 Superseded | — |
| **`<EventStream>`** | WebSocket `/ws/events` consumer — reused by watch, debug replay, logs | 💡 Superseded | — |
| **`<EscalationBanner>`** | P0/P1 alerts — appears in multiple views | 💡 Superseded | — |

**Remarks:** Decided: option B (static HTML plus a polling REST API), not the TUI that this assessment recommended. The page is read-only, has no build step, and uses the same API definition as the CLI. The React stack stays in `TECHNICAL-DESIGN-SPEC.md` §1.5 marked as superseded for the first release. Still open: the ~25M token estimate in `UMAS-BUILD-ASSESSMENT.md` was for React and has not been re-based, and the backend framework (FastAPI or Express) is not chosen. No spec exists yet for the page itself or for the REST endpoints it reads.

---

### New Category F — Content Packs (Tier 2) — Not in Original Assessment

The `packs/` folder represents a category the original assessment did not identify. Eight prompt-and-rule packs have been extracted:

| Pack | What it covers | Agreement |
|---|---|---|
| [`minimalism-ladder`](packs/minimalism-ladder.md) | 6-rung ladder, enforcement levels, shortcut format | ✅ Correct tier. Better here than as a code lib. |
| [`anti-slop`](packs/anti-slop.md) | 7-category slop definition, two-pass review, forbidden-phrase linter | ✅ Novel addition not in original assessment. High value. |
| [`communication-modes`](packs/communication-modes.md) | Compact (agent↔agent) vs. plain (human-facing) registers | ✅ Novel addition. Addresses a real token waste problem. |
| [`two-axis-review`](packs/two-axis-review.md) | Standards + Spec review passes, finding schema, severity gate | ✅ Correct extraction. Replaces the `CodeReviewAgent` stub. |
| [`specialist-agents`](packs/specialist-agents.md) | Analyst → PM → UX → Architect → Developer prompts + output contracts | ✅ Correct extraction. Covers 35M token cost driver from build assessment. |
| [`router-heuristic`](packs/router-heuristic.md) | Scoring rubric, signal weights, route bands, classification prompt | ✅ Addresses the "keyword-matching Router" gap from §3.3 of this assessment. |
| [`grilling`](packs/grilling.md) | Bounded questioning protocol, alignment summary, trigger rules | ✅ Correct extraction. |
| [`test-policy`](packs/test-policy.md) | Selective vs. strict modes, risky-logic classifier, trivial-change exemption | ✅ Correct extraction. Policy correctly separated from the `test-adapters` lib. |

---

## 3. Technology Stack Review

### What holds up well ✅

- **Rust for Daemon + Scheduler + TestRunner + CLI** — correct call. Cross-platform binary, no runtime dependency, excellent async. No change needed.
- **Python for agent logic** — correct. The LLM SDKs are Python-first. Pydantic v2 + async is a solid choice.
- **SQLite → PostgreSQL migration path** — pragmatic and well-reasoned.
- **OpenTelemetry** — right choice. Keeps observability vendor-neutral.

### What needs a second look ⚠️

**1. TimescaleDB is a heavyweight dependency for Tier 1/2**
**Status:** ✅ Resolved

[`libs/metrics-store.md`](libs/metrics-store.md) removes TimescaleDB as a hard dependency. Default storage is a JSONL ledger (Phase 1–2), then a standard PostgreSQL `metrics` table (Phase 3+). TimescaleDB is an optional upgrade documented in §2 Non-Goals: a single `create_hypertable` call with no application code change. This matches the decision made in the preceding session.

**2. React + TypeScript dashboard has zero spec coverage, but carries the second-highest build cost (25M tokens)**
**Status:** ✅ Decided — option B

[ADR-0001](docs/decisions/ADR-0001-minimal-html-dashboard.md) chooses a minimal read-only HTML page that polls the API. This was the second of the two options below; the first (TUI) was not chosen.

- **Option A:** Ship a **terminal UI** (TUI using `ratatui` in Rust or `textual` in Python) as the "dashboard" in Phase 1–3. Lower cost, same data. React dashboard becomes Phase 4.
- **Option B (chosen):** Define a minimal **read-only dashboard** (static HTML + polling REST API) as Phase 2. No React complexity. Full React in Phase 4 only.

Follow-ups: re-base the 25M estimate, and decide whether the page ships in Phase 2 as written here.

**3. The Router is designed as keyword-matching, but the spec calls for a scoring heuristic**
**Status:** ✅ Addressed

[`packs/router-heuristic.md`](packs/router-heuristic.md) defines the scoring rubric with signals, weights, band table, and a classification prompt. Crucially, the deterministic scorer (arithmetic kept out of the model) is specified. The Router implementation still needs to be built, but the design is no longer a gap.

**4. No message broker between Rust and Python processes**
**Status:** ⚠️ Still unresolved

The `event-log` lib's open question §11.1 explicitly raises this: "Is a pure-file design enough at 20-30 concurrent writers, or does Tier 3 scale want SQLite WAL as an alternative backend?" The file-based approach is fine for Phase 1–2, but the Phase 3 bottleneck risk remains. The recommendation stands: design the broker interface now, implement it when scale demands it.

**5. JWT auth is listed as "Phase 4 / cross-cutting" but the PRD requires RBAC from the start**
**Status:** ❌ Still unresolved

Neither `libs/` nor `packs/` addresses authentication or RBAC. The data model (roles, permissions) and middleware hook point have not been designed. This remains a security risk. The RBAC skeleton should be in Phase 1 even if the full auth flow waits.

---

## 4. Summary: Decisions Required

| Decision | Options | Recommendation | Status |
|---|---|---|---|
| Dashboard timing | Phase 2 minimal vs Phase 4 full React | Ship TUI in Phase 1, React in Phase 4 | ✅ Resolved — minimal read-only HTML (not the recommended TUI), [ADR-0001](docs/decisions/ADR-0001-minimal-html-dashboard.md) |
| TimescaleDB | Hard dependency vs optional upgrade | Optional — default to SQLite rows | ✅ Resolved — JSONL ledger (Phase 1–2) → standard PostgreSQL (Phase 3+) → TimescaleDB optional one-liner; see [`libs/metrics-store.md`](libs/metrics-store.md) §2 |
| Router design | Keyword stub vs scoring heuristic | Design the interface now, keyword-match is fine as v1 impl | ✅ Resolved — `packs/router-heuristic.md` |
| IPC mechanism | Filesystem events vs message broker | Design broker interface now, filesystem impl is fine for Phase 1–2 | ⚠️ Deferred but flagged in `event-log` §11 |
| Auth | Defer to Phase 4 vs RBAC skeleton in Phase 1 | RBAC data model + middleware hook in Phase 1 | ❌ Not decided |
| `CodingAgentAdapter` ↔ `LLMGateway` | Two separate abstractions vs unified | Keep separate — `agent-platform` routes work to harnesses, `llm-gateway` routes inference calls (the original recommendation to unify was wrong, see Category D) | ✅ Resolved in the specs — [`libs/agent-platform.md`](libs/agent-platform.md); IBM Bob registers in both. Stakeholder sign-off still pending (gap 4 in §5) |

---

## 5. Gaps Still Open

In priority order. Closed since the last review: `error-classifier` (now [`libs/error-classifier.md`](libs/error-classifier.md)), dashboard decision ([ADR-0001](docs/decisions/ADR-0001-minimal-html-dashboard.md)), `agent-session` (now [`libs/agent-session.md`](libs/agent-session.md) with `CoordinatorAgent` §12.3 added), and `metrics-store` (now [`libs/metrics-store.md`](libs/metrics-store.md), TimescaleDB resolved).

1. **RBAC data model** — Security gap. Should be a Tier 0 (UMAS-specific) schema decision made in Phase 1, not Phase 4. Neither `libs/` nor `packs/` addresses authentication or RBAC.
2. **`task-queue` / Scheduler extraction** — The capacity/dispatch half of the Scheduler is not covered by any lib. Either extract it or document it as a deliberate UMAS-internal component.
3. **`structured-output-parser` decision** — Each pack defines its own output schema, but the *parsing mechanism* (how an agent validates and extracts a structured response) has no spec. A brief decision record is needed: either document that Pydantic v2 is the standard mechanism and no dedicated lib is needed, or extract a thin spec.
4. **Platform adapter decision** — IBM Bob is *both*: register in `agent-platform` as a harness adapter and in `llm-gateway` as a provider. `libs/agent-platform.md` §9 and §11.1 document this split. Stakeholder sign-off still needed before Phase 2.
5. **Follow-ups from closed items:**
   - Re-base the 25M dashboard estimate for the HTML page.
   - ~~Point the other libs' error tables at `error-classifier` records~~ Done 2026-10-20: each lib keeps its own typed errors, and its failure-modes section now has an "Error records" table of suggested `recoverability`. It is a data mapping, with no import.
   - Choose the dashboard backend framework.

---

## 6. Overall Assessment

The `libs/` and `packs/` work is high quality and addresses the most important items from the original assessment. The Tier 1 / Tier 2 split (code libraries vs. content packs) is better structured than the five categories proposed here. The specs are thorough, independence rules are well-defined, and the composition maps make the wiring explicit without creating code-level dependencies.

As of October 21: all 12 libs are specced, all 8 packs are specced, all inline source code has been moved to §12 reference appendices and tombstoned at source. The `structured-output-parser` decision record, RBAC data model, `task-queue` extraction, and IBM Bob adapter sign-off are the four open items before the foundation is complete.
