# UMAS Build Token Budget Assessment

> Estimate of LLM token cost to fully implement the Unified Multi-Agent Development System.
> Based on the reconciled document set as of this assessment.
> Read alongside [`TECHNICAL-DESIGN-SUMMARY.md`](TECHNICAL-DESIGN-SUMMARY.md) for full context.

---

## Basis for Estimates

The TDS describes a two-language system (Rust + Python), a React dashboard, four databases, and eight independent modules. The spec contains working class-level code for approximately **40% of the implementation** — the remainder is stubs, config blocks, and `# Implementation: ...` placeholders.

Token estimates are for LLM-assisted development (code generation, iteration, review, and testing). They do not include human review time or infrastructure setup.

---

## Per-Module Breakdown

| Module | Language(s) | Spec completeness | Realistic tokens |
|--------|-------------|-------------------|-----------------|
| **Context Persistence** — `WorktreeService`, `ArtifactService`, `SessionHistoryInterface` | Rust + Python | ~60% — Rust service complete; Python artifact creation ~50%; session discovery is a stub | 15M |
| **Orchestration** — `CoordinatorAgent`, `Router`, `Scheduler` | Python + Rust | ~50% — Coordinator flow complete; Router is a keyword-matching stub; Scheduler Rust core complete but queue processing incomplete | 22M |
| **Agent Execution** — `WorkerAgent`, 5 specialised agents, `MinimalismEnforcer` | Python | ~40% — WorkerAgent flow complete; all 5 specialised agents are prompt stubs; ladder enforcement stubs past rung 2 | 35M |
| **Verification** — `MergeQueueProcessor`, `TestRunner`, `CodeReviewAgent` | Python + Rust | ~55% — MergeQueue and bisect complete; TestRunner Rust complete; CodeReview review prompts are stubs | 18M |
| **Monitoring** — `Daemon`, `TriageAgent`, `SystemPatrol`, `ProjectMonitor` | Rust + Python | ~30% — Daemon heartbeat loop complete; Triage and Patrol are stubs | 14M |
| **CLI + Dashboard** — 14 CLI commands (Rust), React dashboard | Rust + TypeScript | ~10% — command list exists, no implementation; dashboard has no component specs | 25M |
| **Cross-cutting** — DB migrations (Alembic), auth (JWT), observability (OpenTelemetry), installation scripts | Mixed | ~20% — schemas sketched; no migration code; no auth implementation | 15M |
| **Integration + E2E testing** — not in the spec at all | Mixed | 0% | 18M |

---

## Summary

| Scenario | Total tokens | Assumes |
|----------|-------------|---------|
| **Minimum** — tight, experienced, no rework | **~86M** | Stubs filled cleanly, minimal iteration, no scope creep |
| **Realistic** — normal development cycle | **~162M** | 1–2 rework passes per module, tests written, all 16 exception flows from `UMAS-TECH-DESIGN-SPEC.md` implemented |
| **Upper bound** — full production quality | **~270M** | Complete E2E tests, full CLI + dashboard, production hardening, all exception flows implemented and tested |

---

## Largest Cost Drivers

### 1. Agent Execution — 35M (realistic)
The 5 specialised agents (`ProductManagerAgent`, `ArchitectAgent`, `UXDesignerAgent`, `DeveloperAgent`, `AnalystAgent`) are all prompt stubs. Each needs real prompt engineering, structured output parsing, and error handling — iterative and expensive.

### 2. CLI + Dashboard — 25M (realistic)
The CLI has 14+ commands in the spec with zero implementation. The React dashboard is listed in the stack but has no component specifications. UI work is token-heavy due to iteration cycles.

### 3. Integration Testing — 18M (realistic)
Not covered in any spec file. Multi-agent scenarios (parallel workers, merge queue, crash recovery, provider failover) all require integration harnesses that do not yet exist.

### 4. Router rewrite (within Orchestration)
The current `Router` implementation uses keyword-matching triggers. Replacing it with the scoring heuristic defined in `UMAS-TECH-DESIGN-SPEC.md §3.2` (codebase scan, signal weighting, threshold bands) is a significant rewrite — costed within the Orchestration estimate.

---

## Phased Build Recommendation

Build in phases, each independently testable before proceeding. Validates the core architecture before committing to full build cost.

### Phase 1 — Foundation (~40M tokens)
**Delivers:** Context Persistence + Orchestration skeleton + CLI basics

- `WorktreeService` (Rust) — full implementation
- `ArtifactService` + `SessionHistoryInterface` (Python)
- `CoordinatorAgent` — grilling, planning, dispatch flow
- `Router` — scoring heuristic (replacing keyword stub)
- `Scheduler` (Rust) — complete queue processing
- CLI: `init`, `init --project`, `project register`, `project list`, `request`, `status`
- Database schema + Alembic migrations

**Validates:** hook/worktree/signalling architecture before any agent code is written.

---

### Phase 2 — Single-agent loop (~45M tokens)
**Delivers:** One agent can complete a task end-to-end

- `WorkerAgent` — full execution, `[umas:done]` / `[umas:checkpoint]` signalling, handoff
- `MinimalismEnforcer` — all 6 ladder rungs implemented
- `MergeQueueProcessor` — permanent worktree, batch + bisect algorithm
- `TestRunner` (Rust) — pytest/jest/cargo support
- Exception flows: §4.1–§4.8 (project deletion, corrupted `.umas/`, stale worktrees, budget exhaustion)

**Validates:** single-agent task completion, state persistence, and merge queue before adding concurrency.

---

### Phase 3 — Multi-agent + monitoring (~50M tokens)
**Delivers:** Parallelism and crash recovery validated

- `Scheduler` — concurrent dispatch, semaphore, token budget enforcement
- `Daemon` (Rust) — complete heartbeat + restart logic
- `TriageAgent` + `SystemPatrol` — full stub-to-implementation
- `ProjectMonitor` — stuck detection, graceful/emergency handoff
- LLM provider failover (§4.7)
- Exception flows: §4.9–§4.16 (regression, DB corruption, concurrent CLI, disk exhaustion)

**Validates:** multi-agent parallelism, crash recovery, and three-tier watchdog before specialisation.

---

### Phase 4 — Full system (~27M+ tokens)
**Delivers:** Production-ready system

- All 5 specialised agents — real prompt engineering, structured outputs
- `CodeReviewAgent` — two-axis review implementation
- React dashboard — all monitoring views, real-time updates via WebSocket
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
| Phase 4 | ~162M+ | Full production system with dashboard and specialised agents |

**Phases 1–2 alone (~85M tokens) give a working single-agent system that validates the core design before committing to the remaining ~77M–185M tokens.**

---

## Token Cost Reference (Anthropic Claude)

Estimates above assume Claude 3.5 Sonnet at approximately $3/M input + $15/M output tokens, with an average 60/40 input/output split across a development session.

| Phase | Realistic tokens | Approximate cost |
|-------|-----------------|-----------------|
| Phase 1 | 40M | ~$340 |
| Phase 2 | 45M | ~$380 |
| Phase 3 | 50M | ~$425 |
| Phase 4 | 27M | ~$230 |
| **Total (realistic)** | **162M** | **~$1,375** |
| Upper bound | 270M | ~$2,295 |

> Costs are indicative only. Actual cost depends on provider, model choice, context window reuse, and caching.
