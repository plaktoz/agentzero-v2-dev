# UMAS Build Token Budget Assessment

> Estimate of LLM token cost to fully implement the Unified Multi-Agent Development System.
> Based on the reconciled document set as of this assessment.
> Read alongside [`TECHNICAL-DESIGN-SUMMARY.md`](./TECHNICAL-DESIGN-SUMMARY.md) for full context.
> **Re-based 2026-10-25 (provisional):** the stack is Python, with TypeScript only where no Python option exists ([`TECHNICAL-DESIGN-SPEC.md`](./TECHNICAL-DESIGN-SPEC.md#a46-language-decision) Appendix A.4.6), and the dashboard is the static HTML page from [ADR-0001](../docs/decisions/ADR-0001-minimal-html-dashboard.md). The realistic total moved from ~162M to ~154M. The minimum and upper-bound scenarios were not re-based.

---

## Basis for Estimates

The TDS describes a system of eight independent modules and four databases. The source design wrote its services in Rust and Python and a React dashboard. The chosen stack is Python only, so the Rust services are ported to Python, and the dashboard is a read-only static HTML page. The spec contains working class-level code for approximately **40% of the implementation** — the remainder is stubs, config blocks, and `# Implementation: ...` placeholders. The Rust code counts as spec completeness, because it is a complete design to port.

Token estimates are for LLM-assisted development (code generation, iteration, review, and testing). They do not include human review time or infrastructure setup.

**Re-basing rule (provisional).** A Rust row keeps its previous figure as a Python port. The React part of the CLI + Dashboard row is replaced by the HTML page. The split of the old 25M into about 15M for the CLI and 10M for the React app is an estimate, not a measurement. The HTML page is estimated at 2M.

---

## Per-Module Breakdown

| Module | Language | Spec completeness | Realistic tokens |
|--------|----------|-------------------|-----------------|
| **Context Persistence** — `WorktreeService`, `ArtifactService`, `SessionHistoryInterface` | Python | ~60% — Rust service complete (port to Python); Python artifact creation ~50%; session discovery is a stub | 15M |
| **Orchestration** — `CoordinatorAgent`, `Router`, `Scheduler` | Python | ~50% — Coordinator flow complete; Router is a keyword-matching stub; Scheduler Rust core complete (port to Python) but queue processing incomplete | 22M |
| **Agent Execution** — `WorkerAgent`, 5 specialised agents, `MinimalismEnforcer` | Python | ~40% — WorkerAgent flow complete; all 5 specialised agents are prompt stubs; ladder enforcement stubs past rung 2 | 35M |
| **Verification** — `MergeQueueProcessor`, `TestRunner`, `CodeReviewAgent` | Python | ~55% — MergeQueue and bisect complete; TestRunner Rust complete (port to Python); CodeReview review prompts are stubs | 18M |
| **Monitoring** — `Daemon`, `TriageAgent`, `SystemPatrol`, `ProjectMonitor` | Python | ~30% — Daemon heartbeat loop complete (Rust, port to Python); Triage and Patrol are stubs | 14M |
| **CLI + Dashboard** — 14 CLI commands, static HTML page | Python + plain HTML | ~10% — command list exists, no implementation; the page has no spec | 17M (CLI ~15M, page ~2M; the split is an estimate) |
| **Cross-cutting** — DB migrations (Alembic), auth (JWT), observability (OpenTelemetry), installation scripts | Python | ~20% — schemas sketched; no migration code; no auth implementation | 15M |
| **Integration + E2E testing** — not in the spec at all | Python | 0% | 18M |

---

## Summary

| Scenario | Total tokens | Assumes |
|----------|-------------|---------|
| **Minimum** — tight, experienced, no rework | **~86M** | Stubs filled cleanly, minimal iteration, no scope creep. Not re-based |
| **Realistic** — normal development cycle | **~154M** | 1–2 rework passes per module, tests written, all exception flows in [`TECHNICAL-DESIGN-SPEC.md`](./TECHNICAL-DESIGN-SPEC.md) section 6 (17 flows) implemented. Re-based; was ~162M |
| **Upper bound** — full production quality | **~270M** | Complete E2E tests, full CLI + dashboard, production hardening, all exception flows implemented and tested. Not re-based |

---

## Largest Cost Drivers

### 1. Agent Execution — 35M (realistic)
The 5 specialised agents (`ProductManagerAgent`, `ArchitectAgent`, `UXDesignerAgent`, `DeveloperAgent`, `AnalystAgent`) are all prompt stubs. Each needs real prompt engineering, structured output parsing, and error handling — iterative and expensive.

### 2. Integration Testing — 18M (realistic)
Not covered in any spec file. Multi-agent scenarios (parallel workers, merge queue, crash recovery, provider failover) all require integration harnesses that do not yet exist.

### 3. Verification — 18M (realistic)
The merge queue, the test runner port and the review agent. The review prompts are stubs.

### 4. CLI + Dashboard — 17M (realistic)
The CLI has 14+ commands in the spec with zero implementation and is about 15M of this figure. The read-only HTML page (ADR-0001) replaces the React dashboard, which had no component specifications, and is about 2M. The split is an estimate.

### 5. Router rewrite (within Orchestration)
The current `Router` implementation uses keyword-matching triggers. Replacing it with the scoring heuristic defined in [`TECHNICAL-DESIGN-SPEC.md`](./TECHNICAL-DESIGN-SPEC.md) section 5.2 (codebase scan, signal weighting, threshold bands) is a significant rewrite — costed within the Orchestration estimate.

---

## Phased Build Recommendation

Build in phases, each independently testable before proceeding. Validates the core architecture before committing to full build cost. All code is Python unless stated.

### Phase 1 — Foundation (~40M tokens)
**Delivers:** Context Persistence + Orchestration skeleton + CLI basics

- `WorktreeService` — full implementation (port of the Rust source design to Python)
- `ArtifactService` + `SessionHistoryInterface`
- `CoordinatorAgent` — grilling, planning, dispatch flow
- `Router` — scoring heuristic (replacing keyword stub)
- `Scheduler` — complete queue processing (port of the Rust source design to Python)
- CLI: `init`, `init --project`, `project register`, `project list`, `request`, `status`
- Database schema + Alembic migrations

**Validates:** hook/worktree/signalling architecture before any agent code is written.

---

### Phase 2 — Single-agent loop (~45M tokens)
**Delivers:** One agent can complete a task end-to-end

- `WorkerAgent` — full execution, `[umas:done]` / `[umas:checkpoint]` signalling, handoff
- `MinimalismEnforcer` — all 6 ladder rungs implemented
- `MergeQueueProcessor` — permanent worktree, batch + bisect algorithm
- `TestRunner` — pytest/jest/cargo support (port of the Rust source design to Python)
- Exception flows: §4.1–§4.8 (project deletion, corrupted `.umas/`, stale worktrees, budget exhaustion)

**Validates:** single-agent task completion, state persistence, and merge queue before adding concurrency.

---

### Phase 3 — Multi-agent + monitoring (~50M tokens)
**Delivers:** Parallelism and crash recovery validated

- `Scheduler` — concurrent dispatch, semaphore, token budget enforcement
- `Daemon` — complete heartbeat + restart logic (port of the Rust source design to Python, run under the OS service manager)
- `TriageAgent` + `SystemPatrol` — full stub-to-implementation
- `ProjectMonitor` — stuck detection, graceful/emergency handoff
- LLM provider failover (§4.7)
- Exception flows: §4.9–§4.16 (regression, DB corruption, concurrent CLI, disk exhaustion)

**Validates:** multi-agent parallelism, crash recovery, and three-tier watchdog before specialisation.

---

### Phase 4 — Full system (~19M+ tokens)
**Delivers:** Production-ready system

- All 5 specialised agents — real prompt engineering, structured outputs
- `CodeReviewAgent` — two-axis review implementation
- Read-only HTML dashboard (ADR-0001) — agents, work bundles, merge queue and cost, polled from the REST API
- Remaining CLI commands (`watch`, `agents handoff`, `debug replay`, `metrics *`)
- OpenTelemetry integration + Prometheus/Jaeger exporters
- Production hardening: PostgreSQL migration path, JWT auth, RBAC

---

## Phase Gate Summary

| Phase | Cumulative tokens | Capability unlocked |
|-------|------------------|---------------------|
| Phase 1 | ~40M | Submit a request, see it planned and dispatched |
| Phase 2 | ~85M | Single agent completes task, merges to main |
| Phase 3 | ~135M | Multiple agents work in parallel, system self-heals |
| Phase 4 | ~154M+ | Full production system with dashboard and specialised agents |

**Phases 1–2 alone (~85M tokens) give a working single-agent system that validates the core design before committing to the remaining ~69M (realistic).**

---

## Token Cost Reference (Anthropic Claude)

Estimates above assume Claude 3.5 Sonnet at approximately $3/M input + $15/M output tokens, with an average 60/40 input/output split across a development session. The model and prices are the source's basis and are stale; the cost column is only a ratio.

| Phase | Realistic tokens | Approximate cost |
|-------|-----------------|-----------------|
| Phase 1 | 40M | ~$340 |
| Phase 2 | 45M | ~$380 |
| Phase 3 | 50M | ~$425 |
| Phase 4 | 19M | ~$162 |
| **Total (realistic)** | **154M** | **~$1,309** |
| Upper bound (not re-based) | 270M | ~$2,295 |

> Costs are indicative only. Actual cost depends on provider, model choice, context window reuse, and caching.
