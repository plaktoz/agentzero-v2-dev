# Technical Design Specification: Unified Multi-Agent Development System

**Version:** 2.0
**Date:** October 21, 2026
**Status:** Active — Unified
**Based on:** [unified-multi-agent-system-prd.md](unified-multi-agent-system-prd.md)
**Supersedes:** TECHNICAL-DESIGN-SPEC.md v1.1 · TECHNICAL-DESIGN-SPEC-PART2.md · TECHNICAL-DESIGN-SPEC-PART3.md · UMAS-TECH-DESIGN-SPEC.md

> This is the single authoritative technical design document. The four-file split from v1.x has been collapsed here.
> All code that was inline in the previous documents has been moved into `libs/` and `packs/` reference appendices.
> **Reusable components:** [libs/README.md](libs/README.md) (13 libraries) · [packs/README.md](packs/README.md) (8 content packs)
> **Product requirements:** [unified-multi-agent-system-prd.md](unified-multi-agent-system-prd.md)
> **Modularisation assessment:** [modularisation-assessment.md](modularisation-assessment.md)

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [System Architecture](#2-system-architecture)
3. [Reusable Components](#3-reusable-components)
4. [Data Model](#4-data-model)
5. [Component Design](#5-component-design)
   - 5.1 Context Persistence System
   - 5.2 Orchestration System
   - 5.3 Agent Execution System
   - 5.4 Verification System
   - 5.5 Monitoring System
   - 5.6 Token Budget and Handoff
   - 5.7 Model Policy
   - 5.8 Scalability Roadmap
   - 5.9 CLI Design
6. [Exception Flows](#6-exception-flows)
7. [API Specifications](#7-api-specifications)
8. [Security Architecture](#8-security-architecture)
9. [Performance and Scalability](#9-performance-and-scalability)
10. [Testing Strategy](#10-testing-strategy)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Implementation Phases](#12-implementation-phases)
13. [Key Metrics](#13-key-metrics)
14. [Open Questions](#14-open-questions)

---

## 1. Technology Stack

### 1.1 Core Languages

```yaml
daemon_and_cli:
  language: Rust
  version: "1.70+"
  rationale: Cross-platform binary, memory safety, excellent async (Tokio), single binary distribution.
  key_dependencies:
    tokio: "1.32+"
    clap: "4.4+"
    serde: "1.0+"
    sqlx: "0.7+"
    anyhow: "1.0+"
    tracing: "0.1+"
    uuid: "1.4+"

agent_runtime:
  language: Python
  version: "3.10+"
  rationale: Rich AI/ML ecosystem, LLM SDK support, strong async.
  key_dependencies:
    anthropic: "0.7+"
    openai: "1.3+"
    google-generativeai: "0.3+"
    pydantic: "2.4+"
    aiofiles: "23.2+"
    gitpython: "3.1+"
    sqlalchemy: "2.0+"
    alembic: "1.12+"
```

**Alternative (Node.js):** TypeScript 18+ with `commander`, `prisma`, `zod` is a viable substitute for both layers if the team prefers one runtime. The lib specs are language-neutral.

### 1.2 Data Storage

```yaml
version_control:
  minimum: git 2.30+
  features: [worktree_support, hooks, sparse_checkout]
  worktree_base_path: ".umas/worktrees/"
  hooks_path: ".umas/hooks/"
  branch_prefix: "agent/"

database:
  tier_1_mvp:
    engine: SQLite 3.35+
    location: "~/.umas/database.db"
    features: [wal_mode, foreign_keys, json_support]
    max_concurrent_agents: 5
  tier_2_production:
    engine: PostgreSQL 14+
    connection_pool: {min: 5, max: 50, idle_timeout: 300}
    max_concurrent_agents: 30+

metrics_storage:
  # TimescaleDB is NOT a hard dependency. See libs/metrics-store.md §2.
  phase_1_2: JSONL file ledger (libs/metrics-store.md — JSONL backend)
  phase_3_plus: Standard PostgreSQL "metrics" table (libs/metrics-store.md — SQL backend)
  optional_upgrade: "SELECT create_hypertable('metrics', 'ts') — one statement, no app code change"
```

### 1.3 LLM Providers

```yaml
# Providers are configuration. Replacing one is an edit to the llm-gateway alias table.
tier_1_full_integration:
  anthropic_claude:
    models: [claude-3-5-sonnet-20241022, claude-3-opus-20240229]
    features: [hooks_support, streaming, function_calling, max_tokens_200k]
  openai_gpt:
    models: [gpt-4-turbo, gpt-4]
    features: [streaming, function_calling, max_tokens_128k]
  google_gemini:
    models: [gemini-1.5-pro, gemini-1.5-flash]
    features: [streaming, max_tokens_1m]

tier_2_basic_integration:
  local_llm:
    endpoint: "http://localhost:11434"
    models: [llama3, codellama]
    features: [offline_mode]
```

### 1.4 Observability

```yaml
protocol: OpenTelemetry 1.20+
logging:
  format: JSON (structured)
  libraries: {rust: tracing, python: structlog}
  fields: [timestamp, level, service, agent_id, session_id, task_id, trace_id]
metrics:
  backend: Prometheus
  scrape_interval: 15s
tracing:
  backend: Jaeger
  sampling: {development: 1.0, production: 0.01}
  propagation: W3C Trace Context
```

### 1.5 Dashboard

> **Decision (ADR-0001):** The dashboard for the first release is a **minimal read-only HTML page** that polls the REST API. No React, no build step, no WebSocket requirement. See [ADR-0001](docs/decisions/ADR-0001-minimal-html-dashboard.md).

The React + TypeScript stack described in v1.x is retained below as the **Phase 4 option** only.

```yaml
phase_4_option:
  framework: React 18+ / TypeScript
  state_management: Zustand
  ui_library: shadcn/ui
  build_tool: Vite
  backend: FastAPI (Python) or Express (Node.js)
  api: REST + WebSocket (Socket.io)
```

---

## 2. System Architecture

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HUMAN INTERFACE LAYER                        │
│       CLI (Rust)  ·  Dashboard (HTML/polling)  ·  Escalation    │
└────────────────────────────┬────────────────────────────────────┘
                             │ Unix Socket / JSON-RPC
┌────────────────────────────▼────────────────────────────────────┐
│                     ORCHESTRATION LAYER                          │
│         Coordinator (Python)  ·  Router  ·  Scheduler (Go)    │
└──────┬─────────────────────────────────────────┬────────────────┘
       │ Task Queue                               │ Resource Alloc
┌──────▼───────────────┐          ┌──────────────▼───────────────┐
│  AGENT EXECUTION     │          │    VERIFICATION SYSTEM       │
│  Worker · Specialized│          │ Merge Queue · Review · TDD   │
└──────┬───────────────┘          └──────────────┬───────────────┘
       │ Git Operations                           │ Test Execution
┌──────▼───────────────────────────────────────────▼─────────────┐
│                   CONTEXT PERSISTENCE LAYER                      │
│      Git Worktrees  ·  Decision Artifacts  ·  events.jsonl      │
└─────────────────────────────┬───────────────────────────────────┘
                              │ Heartbeat / Polls
┌─────────────────────────────▼───────────────────────────────────┐
│                     MONITORING LAYER                             │
│    Daemon (Rust)  →  Triage Agent  →  System Patrol  →  Project │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Communication Patterns

```yaml
cli_to_daemon:
  protocol: Unix Domain Socket (Linux/macOS) / Named Pipe (Windows)
  format: JSON-RPC 2.0
  timeout: 30s

daemon_to_agents:
  protocol: Process spawn with stdio
  format: JSON Lines (JSONL)

agents_to_git:
  protocol: Git CLI subprocess
  operations: [worktree add/remove/list, commit, checkout, merge, diff]

agents_to_database:
  protocol: SQL over connection pool
  orm: SQLAlchemy (Python) / Prisma (Node.js)

dashboard_to_api:
  protocol: HTTP/HTTPS polling (Phase 1–3) / WebSocket (Phase 4)
  format: JSON
  auth: JWT Bearer tokens
  base_path: "/api/v1"

telemetry:
  protocol: OTLP (Protobuf)
  endpoints: {metrics: prometheus:9090, traces: jaeger:14268, logs: loki:3100}
```

### 2.3 Process Model

```yaml
daemon:
  type: long_running_service
  language: Rust
  resource_limits: {memory: 512MB, cpu: 1_core}
  restart_policy: always

agents:
  type: ephemeral_workers
  language: Python
  lifecycle: task_scoped
  spawn_method: subprocess
  resource_limits: {memory: 2GB_per_agent, cpu: 2_cores, max_concurrent: 30}

cli:
  type: short_lived_client
  language: Rust
  timeout: 300s
  communication: IPC_to_daemon
```

---

## 3. Reusable Components

Parts of the design are extracted as standalone units with no dependency on UMAS. The sections below describe how UMAS uses them; each standalone spec is the authority on behaviour. Where the two differ, the standalone spec records the difference in its "Source material and deviations" section.

### Tier 1 — Libraries ([index](libs/README.md))

| Component in this doc | Standalone spec |
|-----------------------|-----------------|
| Hooks and worktree state (§5.1) | [hook-store](libs/hook-store.md) |
| `.umas/events.jsonl` signalling (§5.1, §5.3) | [event-log](libs/event-log.md) |
| Merge Queue Processor (§5.4) | [merge-queue](libs/merge-queue.md) |
| Test Runner (§5.4) | [test-adapters](libs/test-adapters.md) |
| Token budget, handoff packet (§5.6) | [budget-meter](libs/budget-meter.md) |
| Provider failure handling (§5.7, §6.7) | [llm-gateway](libs/llm-gateway.md) |
| Three-tier watchdog (§5.5) | [watchdog](libs/watchdog.md) |
| Decision artifacts, shortcut ledger (§5.1) | [decision-artifacts](libs/decision-artifacts.md) |
| Error severity, recoverability, escalation records (§6) | [error-classifier](libs/error-classifier.md) |
| Platform adapters, work assignment, cross-platform transfer (§5.3) | [agent-platform](libs/agent-platform.md) |
| Agent session lifecycle (§5.3) | [agent-session](libs/agent-session.md) |
| Metrics recording, query, retention (§1.2) | [metrics-store](libs/metrics-store.md) |

### Tier 2 — Content Packs ([index](packs/README.md))

| Component in this doc | Standalone spec |
|-----------------------|-----------------|
| Minimalism ladder, shortcut comments (§5.3) | [minimalism-ladder](packs/minimalism-ladder.md) |
| Anti-slop principles | [anti-slop](packs/anti-slop.md) |
| Communication modes (compact vs. plain) | [communication-modes](packs/communication-modes.md) |
| Code Review, two-axis (§5.4) | [two-axis-review](packs/two-axis-review.md) |
| Specialized Agents (§5.3) | [specialist-agents](packs/specialist-agents.md) |
| Router scoring heuristic (§5.2) | [router-heuristic](packs/router-heuristic.md) |
| Grilling and the propulsion rule (§5.2) | [grilling](packs/grilling.md) |
| Test coverage policy (§5.4) | [test-policy](packs/test-policy.md) |

---

## 4. Data Model

### Projects

```sql
CREATE TABLE projects (
  id            TEXT PRIMARY KEY,   -- slug, e.g. "my-api"
  name          TEXT NOT NULL,
  path          TEXT NOT NULL UNIQUE,
  status        TEXT NOT NULL DEFAULT 'active',  -- active | orphaned | archived
  registered_at DATETIME NOT NULL,
  last_seen_at  DATETIME
);
```

### Work Bundles

```sql
CREATE TABLE work_bundles (
  id           TEXT PRIMARY KEY,
  project_id   TEXT REFERENCES projects(id),
  type         TEXT NOT NULL,   -- epic | story | task
  status       TEXT NOT NULL,   -- pending | in_progress | completed | failed
  parent_id    TEXT REFERENCES work_bundles(id),
  hook_path    TEXT,
  agent_id     TEXT,
  created_at   DATETIME NOT NULL,
  completed_at DATETIME
);
```

### Agent Sessions

```sql
CREATE TABLE agent_sessions (
  id             TEXT PRIMARY KEY,
  project_id     TEXT REFERENCES projects(id),
  bundle_id      TEXT REFERENCES work_bundles(id),
  status         TEXT NOT NULL,
    -- spawned         : created, not yet responsive
    -- active          : working normally
    -- handoff         : committed state, transferring to successor
    -- crashed         : unresponsive past heartbeat threshold
    -- done            : task completed
    -- budget_paused   : daily token budget exhausted
    -- provider_failed : primary + fallback providers unavailable
  token_used     INTEGER DEFAULT 0,
  token_limit    INTEGER NOT NULL,
  last_heartbeat DATETIME,
  started_at     DATETIME NOT NULL,
  ended_at       DATETIME
);
```

Sessions in `budget_paused` or `provider_failed` are resumable. They are not treated as failures unless they remain in that state beyond the configurable timeout (default: 24 hours).

---

## 5. Component Design

### 5.1 Context Persistence System

**Storage:** Each agent gets a Git worktree inside `.umas/worktrees/<hook-name>/`. The worktree is linked to the main repo but is a separate working directory — agents commit state directly to their worktree branch.

**State commit protocol:**
- Agent commits after every major step
- Commit message format: `[umas] <agent-id> <step-summary> [tokens: N]`
- A `STATE.md` file in the worktree root holds: current task, recent decisions (last 10), explicit next steps, and references to relevant files

**Session discovery:** All agent operations are appended to `.umas/events.jsonl` (append-only, one JSON object per line). On handoff or restart, the incoming agent queries this log filtered by `hook_path`.

```json
{ "ts": "2024-01-15T10:23:01Z", "agent": "alice", "hook": "auth-login/", "event": "step_complete", "summary": "validation logic done, email check pending" }
```

**Decision artifacts location:**

| Artifact | Location |
|----------|----------|
| PRFAQ | `docs/product/<feature>.prfaq.md` |
| ADR | `docs/decisions/ADR-<NNN>-<title>.md` |
| Spec | `docs/specs/<feature>.spec.md` |
| GLOSSARY | `GLOSSARY.md` (repo root) |

**Standalone libs:** [hook-store](libs/hook-store.md) · [event-log](libs/event-log.md) · [decision-artifacts](libs/decision-artifacts.md)

---

### 5.2 Orchestration System

#### Coordinator

- Receives human requests via `umas request "<text>"`
- Runs grilling for human-initiated requests only — agent-to-agent handoffs execute immediately (propulsion principle)
- Creates a `work_bundle` record
- Delegates to Router for skill/workflow selection
- Delegates to Scheduler for agent dispatch
- Never writes application code

**State machine:**

```
IDLE → GRILLING → PLANNING → DISPATCHING → MONITORING → DONE
                                              ↑               |
                                              └── ESCALATED ──┘
```

| From | To | Trigger |
|------|----|---------|
| `IDLE` | `GRILLING` | Human submits request |
| `GRILLING` | `PLANNING` | Human confirms (or skipped for agent-to-agent) |
| `PLANNING` | `DISPATCHING` | Work bundle created and validated |
| `DISPATCHING` | `MONITORING` | All ready tasks dispatched |
| `MONITORING` | `DONE` | All tasks reach `completed` |
| `MONITORING` | `ESCALATED` | Any agent appends `escalate` event to `events.jsonl` |
| `ESCALATED` | `DISPATCHING` | Human resolves escalation |
| `ESCALATED` | `DONE` | Human cancels the work bundle |
| Any | `IDLE` | Bundle cancelled or all tasks failed |

Multiple concurrent bundles each have their own independent state machine. `ESCALATED` in one does not pause others.

**Coordinator config** (see also [libs/agent-session.md §12.3](libs/agent-session.md)):

```yaml
coordinator_config:
  model: claude-3-5-sonnet-20241022
  token_limit: 200000
  complexity_thresholds:
    simple:  {max_files: 3, max_lines: 100, no_architecture_change: true}
    medium:  {max_files: 10, max_lines: 500, limited_architecture_change: true}
    complex: {unlimited: true}
  grilling:
    enabled: true
    human_initiated_only: true
    max_questions: 10
    timeout_seconds: 300
  specialized_agents: {pm: true, architect: true, ux: true, analyst: true}
  session_resumable_statuses: [budget_paused, provider_failed]
  resumable_timeout_hours: 24
```

#### Router

Selects workflow by scoring heuristic:

| Signal | Weight |
|--------|--------|
| Files affected (estimated) | High |
| New feature / service / system | High |
| Scope is ambiguous | Medium |
| User-facing UI | Medium |
| Security / auth / payments / data migration | High |
| Bug fix with specific file/line cited | Low → simple |

| Score band | Route |
|-----------|-------|
| Low | Direct worker agent |
| Medium | Architect + worker |
| High | Full specialist panel → workers |
| Greenfield marker | PM → Architect → parallel workers |

Override: `--route simple|medium|large|greenfield`

> Standalone spec with numeric weights and test fixtures: [packs/router-heuristic.md](packs/router-heuristic.md) · Grilling trigger rules: [packs/grilling.md](packs/grilling.md)

#### Scheduler

- Maintains a `ready_queue` of tasks with no unresolved dependencies, using [libs/task-queue.md](libs/task-queue.md)
- Dispatches agents up to the concurrency limit; tasks wait in queue when at capacity (`max_claimed` plus an `admit` callback backed by `budget-meter`)
- On every task completion: marks complete → unblocks dependents → dispatches newly ready tasks

```python
def on_task_complete(task_id):
    mark_complete(task_id)
    unblock_dependents(task_id)
    check_parent_auto_complete(task_id)
    dispatch_ready_tasks()
```

---

### 5.3 Agent Execution System

#### Worker Agents

- Spawned with: task ID, hook path, compressed context (≤15k tokens)
- Operate exclusively inside their assigned worktree
- Commit state at each major step
- Signal completion: `[umas:done] <task-id>` commit
- Signal blockers: append `{"event":"escalate","severity":"P1","reason":"..."}` to `events.jsonl`

**Agent signalling protocol:**

| Signal | Mechanism | Who reads it |
|--------|-----------|-------------|
| Task complete | Commit: `[umas:done] <task-id>` | Scheduler |
| Task blocked | Append to `events.jsonl`: escalate event | Coordinator |
| Checkpoint | Commit: `[umas:checkpoint] <summary>` | Project Monitor |
| Handoff request | Append to `events.jsonl`: handoff_request event | Scheduler |

**Minimalism ladder** (runs *after* reading relevant code, *before* writing any):

1. Does this feature need to exist?
2. Does it already exist in this codebase?
3. Is it in the standard library or platform?
4. Is it an already-installed dependency?
5. Can it be one readable line?
6. Otherwise: minimum code that works

> Standalone spec: [packs/minimalism-ladder.md](packs/minimalism-ladder.md)

**Shortcut comments:** Agents may leave `// SHORTCUT: <what> — <when to fix>` to mark a deliberate deferral. Must be tracked in the project's debt ledger. All other comments require justifying "why" code exists.

**Session lifecycle:** Shared across all agent types. See [libs/agent-session.md](libs/agent-session.md).

#### Specialized Agents

Invoked by the Router for medium/large tasks:

| Role | Responsibility | When |
|------|---------------|------|
| Analyst | Clarify requirements, surface ambiguity | All non-trivial requests |
| Product Manager | User value, PRFAQ, product decisions | Greenfield, new features |
| Architect | ADR, tech stack, system design | Medium+ complexity |
| UX Designer | Interface and interaction design | User-facing changes |
| Developer | Implementation with minimalism enforcement | All implementation |

> Prompts and output schemas: [packs/specialist-agents.md](packs/specialist-agents.md)

#### Multi-Platform Support

UMAS supports four first-class coding agent harnesses. Each is an adapter in [agent-platform](libs/agent-platform.md). None is built into the core, so any can be replaced by changing configuration.

| Harness | Registers in | Notes |
|---------|-------------|-------|
| Claude Code | [agent-platform](libs/agent-platform.md) | Completion via commit-message hook |
| OpenAI Codex | [agent-platform](libs/agent-platform.md) | Completion via commit-message hook |
| Gemini CLI | [agent-platform](libs/agent-platform.md) | Completion via commit-message hook |
| GitHub Copilot | [agent-platform](libs/agent-platform.md) | Completion via file mtime (IDE tool) |

`agent-platform` handles work assignment, context packing, and completion signalling. `llm-gateway` handles inference routing. They are separate concerns at separate layers, so a harness and a provider are replaced independently.

---

### 5.4 Verification System

#### Merge Queue Processor

Operates on a **permanent** `merge-queue` worktree created once during `umas init --project`. Only the temp test branch is created/destroyed per batch.

**Worktree states:** `IDLE → COLLECTING → TESTING → BISECTING → MERGING`

**Algorithm:**

```
1. Collect all PRs with status = ready_to_merge
2. Create temp branch: merge ALL PRs
3. Run full test suite
4. If green → merge all to main, delete temp branch
5. If red → bisect:
     Split batch, test each half
     Recurse until culprit isolated
     Merge only passing half
     Re-queue failing PR: status = blocked + reason
```

> Standalone spec: [libs/merge-queue.md](libs/merge-queue.md)

#### Code Review (Two-Axis)

Every PR goes through two independent passes run in parallel:

- **Standards axis:** code quality, style, patterns, maintainability
- **Spec axis:** does it solve the right problem and meet task requirements

Each finding: `{ location, what, problem, fix, consequence }`. Findings without a concrete fix are not filed.

> Standalone spec: [packs/two-axis-review.md](packs/two-axis-review.md)

#### Test Coverage Policy

| Mode | Behaviour |
|------|-----------|
| `selective` (default) | Tests required only for risky logic: branches, loops, parsers, money, security |
| `strict` | Full TDD (red-green-refactor) for every feature |

Trivial changes (renaming, formatting, config-only) require no tests under either mode.

> Policy: [packs/test-policy.md](packs/test-policy.md) · Execution and results: [libs/test-adapters.md](libs/test-adapters.md)

---

### 5.5 Monitoring System

**Three-tier watchdog:**

```
Tier 1 — Daemon (Rust, OS process)
  Heartbeats Triage Agent every 3 min
  No response → restart Triage Agent

Tier 2 — Triage Agent (Python, always running)
  Monitors System Patrol
  Stuck → investigates, restarts

Tier 3 — System Patrol (Python, always running)
  Polls all Project Monitors and Merge Queue Processors
  Dispatches maintenance workers for detected issues
```

**Project Monitor** (one per active project, polls every 60 seconds):

| Heuristic | Threshold | Action |
|-----------|-----------|--------|
| No `STATE.md` commit | > 10 min | Agent may be stuck → nudge |
| No heartbeat | > 5 min | Agent likely crashed → graceful handoff |
| Token usage without handoff request | > 95% | Emergency handoff from last checkpoint |

Recovery order: Nudge → Graceful handoff → Emergency handoff

> Standalone spec: [libs/watchdog.md](libs/watchdog.md)

---

### 5.6 Token Budget and Handoff

**Handoff triggers:**

| Trigger | Type | Action |
|---------|------|--------|
| Session token usage ≥ 90% | Graceful | Agent commits state, requests handoff |
| Session token usage ≥ 95% | Emergency | Monitor forces handoff from last checkpoint |
| Daily project budget ≥ 80% | Warning | Alert human |
| Daily project budget = 100% | Exhaustion | Queue new work; do not fail in-progress work |

**Context compression on handoff** — full context (~175k tokens) compressed to handoff packet (~15k tokens):

- Current task and progress percentage
- Last 10 decisions
- Explicit next steps
- Pointers to relevant files (path + line range, not content)

The incoming agent reads the handoff packet and the worktree's `STATE.md`. It does not re-read the full conversation history.

> Standalone spec: [libs/budget-meter.md](libs/budget-meter.md)

---

### 5.7 Model Policy

**Default:** All roles use the same configured model — minimal setup, no per-role overhead.

**Opt-in role mapping** via `umas.config.yaml`:

| Role | Override key |
|------|-------------|
| Coordinator | `agents.coordinator.model` |
| Worker | `agents.worker.model` |
| Architect | `agents.specialized.architect.model` |
| Reviewer | `agents.specialized.reviewer.model` |

**Multi-model panels** are opt-in and reserved for decisions with irreversible consequences (architecture, security, data migrations). Disabled by default.

```yaml
agents:
  worker:
    model: claude-3-5-sonnet
  specialized:
    architect:
      model: claude-3-5-sonnet
      panel_enabled: true
```

---

### 5.8 Scalability Roadmap

**MVP (single workspace):** One `~/.umas/database.db`, all projects on the same machine, up to 5 concurrent agents with SQLite.

**Federation (v2, deferred):** Cross-workspace coordination allowing agents on different machines to work on the same project. Not in MVP — designed with federation in mind (project registration by path, event log as primary state) but not implemented until demand warrants it.

---

### 5.9 CLI Design

#### `umas init` vs `umas init --project`

| Command | Scope | What it does |
|---------|-------|-------------|
| `umas init` | Machine-wide (once) | Creates `~/.umas/`, initialises `database.db`, applies user defaults |
| `umas init --project` | Per-repo | Creates `.umas/`, installs Git hooks, updates `.gitignore` |

`umas init` runs automatically if `umas init --project` is called first. Both commands are fully idempotent.

#### `umas project register`

Registration only — writes to `database.db`. Does not touch the filesystem.

```bash
# Full onboarding flow:
mkdir my-api && cd my-api && git init
umas init --project                    # filesystem
umas project register my-api           # database
umas request "Build a REST API for…"  # submit work
```

Running `umas project register` before `umas init --project` fails with a clear error.

---

## 6. Exception Flows

### 6.1 Force-Deleted Project

**Scenario:** `rm -rf ~/projects/my-api` while the project is still registered.

**Detection:** Lazy — on any UMAS operation referencing the project. Proactively during `umas health-check` and `umas project list`.

**Recovery:**

```
my-api  [ORPHANED — path not found: /Users/you/projects/my-api]

Options:
  1. Remove from database
  2. Re-register at new path
  3. Ignore for now

Choice [1-3]:
```

Option 3 sets status = `orphaned`. After 30 days unresolved, `umas health-check` escalates P2. Records are never auto-deleted.

---

### 6.2 Mid-Task Project Deletion (Agents Running)

**Detection:** Project Monitor's next health poll (within 60 s).

**Recovery:**
1. Mark all active sessions `crashed`
2. Escalate to System Patrol as P1
3. Mark in-flight bundles `failed: project_path_missing`
4. Notify human with worktree branch recovery instructions

Worktree branches committed before deletion still exist in the Git object store.

---

### 6.3 Corrupted `.umas/` Directory

**Detection:** On `umas init --project` and `umas health-check`.

**Recovery:** `umas init --project` is idempotent — recreates missing pieces without touching existing files.

- Missing files → recreated
- Corrupted `config.yaml` → backed up as `.bak`, replaced with defaults
- Corrupted `events.jsonl` → backed up, new empty log started (history loss warned)
- If the Git hook chain is broken → repaired automatically

---

### 6.4 Project Moved or Renamed

**Detection:** Same as §6.1.

**Recovery:** Orphaned prompt offers "Re-register at new path". Validates `git` repo and `.umas/` at new path. Only the `path` column is updated — all history is preserved.

---

### 6.5 Git Hook Conflict

| Detected type | Action |
|--------------|--------|
| `none` | Install UMAS hook directly |
| `plain_shell` | Prepend UMAS call |
| `husky` | Add UMAS hook in `.husky/pre-commit` |
| `lefthook` | Add UMAS step to `lefthook.yml` |
| `pre-commit-framework` | Add as local hook in `.pre-commit-config.yaml` |
| `binary` | Cannot chain — warn, skip, polling-only mode |

On `umas update`, only the `# umas-managed` marker line is replaced; all other hook entries are left untouched.

---

### 6.6 Token Budget Exhausted Mid-Task

**Behaviour:** In-progress agents complete their current atomic step and commit state. New dispatch is paused.

Agent steps when budget signal received:
1. Complete current atomic step
2. Commit: `[umas] budget-pause — state committed`
3. Set status `budget_paused`

When budget is increased via `umas project config --budget <N>`, Project Monitor resumes dispatch within 60 s — does not wait for UTC midnight.

---

### 6.7 LLM Provider Failure Mid-Task

**Retry policy:**

| Error type | Retry |
|-----------|-------|
| 429 Rate limit | Exponential backoff: 5s, 15s, 45s, then failover |
| 5xx Server error | 3 immediate retries, then failover |
| Timeout (>30s) | 2 retries, then failover |
| 401/403 Auth | No retry — P0 escalation immediately |

**Failover:** Uses `STATE.md` compressed context (same as handoff packet). Task does not restart from zero.

**No fallback configured:** P1 escalation. Recovery is human-initiated: `umas agents resume <session-id>`.

> Retry and circuit-breaker details: [libs/llm-gateway.md](libs/llm-gateway.md)

---

### 6.8 Stale Worktrees After Agent Crash

| Age | Action |
|----|--------|
| < 24 h | Keep — agent may be recoverable |
| 24 h – 7 days | Mark `stale`, surface in `umas health-check` |
| > 7 days | Prompt for deletion |

If uncommitted changes are found, the worktree is tagged `stale-dirty` and never cleaned automatically. `umas worktrees recover <name>` spawns a triage agent to commit or discard the diff.

---

### 6.9 Merge Queue Bisect Finds No Clean Subset

All PRs moved to `blocked: failed_in_isolation`. Originating agents re-spawned to fix. Default retry limit: 3 consecutive failures per PR. Beyond that: P1 escalation, no further auto-spawning. Human resets with `--reset-retries`.

---

### 6.10 Dependency Deadlock in Work Bundle

**At creation time:** Coordinator runs cycle detection and dangling-reference check. Rejected bundles must be fixed before submission.

**At runtime:** If a blocking task is already `completed`, the Scheduler moves the blocked task to `ready_queue` on its next `on_task_complete` pass (self-healing, no escalation).

---

### 6.11 Agent Causes Test Regression

Merge Queue bisect isolates the offending PR. Agent is re-spawned with: failing test names, PR diff, and instruction to fix implementation (not the test). If the failing test has a `test_flaky` history, the suite re-runs once before escalating.

---

### 6.12 Database Corruption or Lock

**Lock:** Wait 5 s, then surface the holding PID and exit with instructions to remove WAL files.

**Corruption:** Daily backup at `database.db.bak` (also written on `umas update`). User prompted to restore. If no backup: fresh database, re-register projects. Worktree branches in Git are unaffected.

---

### 6.13 Concurrent CLI Processes

SQLite WAL: one writer, multiple readers. Advisory file lock (`~/.umas/.lock`) for write operations. Write commands wait up to 5 s for the lock.

Running `umas start-all` twice detects the existing PID in `daemon.pid` and exits cleanly.

---

### 6.14 `umas update` While Agents Are Active

Policy: **non-disruptive by default** — never terminates active sessions.

- Default: activate on next `umas start-all` after all sessions complete
- `--now`: all sessions checkpoint and pause → update applies → sessions resume
- Breaking schema change: migration runs automatically with `database.db.bak` written first

---

### 6.15 Dashboard / CLI Showing Stale State

`umas watch` shows a staleness warning when `last_heartbeat` delta > 2 min. Project Monitor reconciles stale sessions within 60 s. Manual: `umas agents reconcile`.

SQLite WAL sub-second read lag is not a bug — `umas watch` refreshes every 2 s.

---

### 6.16 Disk Space Exhaustion

| Free space | Action |
|-----------|--------|
| < 2 GB | P2 warning |
| < 500 MB | P1 — new dispatch paused |
| < 100 MB | P0 — all agents checkpointed and paused immediately |

`umas cleanup --dry-run` shows recoverable space. Decision artifacts (ADRs, PRFAQs, specs) and the last 90 days of `events.jsonl` are never removed.

If `git commit` fails `ENOSPC`: retry once after 5 s, then append P0 escalation to `events.jsonl`.

---

## 7. API Specifications

### CLI Commands

```bash
# System
umas init
umas init --project
umas start-all
umas stop-all
umas status
umas health-check
umas update
umas cleanup [--dry-run]

# Project
umas project register <name>
umas project list
umas project switch <name>
umas project config <name> --budget <tokens>

# Agents
umas agents list
umas agents spawn --task <id>
umas agents status <agent-id>
umas agents handoff <from> <to>
umas agents reconcile
umas agents resume <session-id>

# Work
umas request "<description>" [--route simple|medium|large|greenfield]
umas work-bundle show <id>
umas work-bundle retry <id> [--reset-retries]
umas watch

# Worktrees
umas worktrees list
umas worktrees clean --stale
umas worktrees recover <name>

# Metrics
umas metrics tokens
umas metrics cost
umas metrics quality
umas metrics agents

# Debug
umas debug replay --session <id>
umas debug context --session <id>
umas logs --agent <id>
```

### REST API Endpoints

```
GET    /api/v1/agents
POST   /api/v1/agents
GET    /api/v1/agents/{id}
DELETE /api/v1/agents/{id}

GET    /api/v1/tasks
POST   /api/v1/tasks
GET    /api/v1/tasks/{id}
PATCH  /api/v1/tasks/{id}

GET    /api/v1/work-bundles
POST   /api/v1/work-bundles
GET    /api/v1/work-bundles/{id}

GET    /api/v1/metrics/tokens
GET    /api/v1/metrics/cost
GET    /api/v1/metrics/quality

WebSocket: /ws/events   (Phase 4 only)
```

---

## 8. Security Architecture

- **Secrets:** API keys in environment variables only. Never hardcoded, never committed. `.gitignore` created by `umas init`.
- **Auth:** JWT tokens for dashboard. RBAC roles: Admin, Developer, Viewer. RBAC data model design is an open item (see §14).
- **Network:** All services bind to `127.0.0.1`. TLS 1.2+ for all external communication. Certificate validation enforced.
- **Agents:** Least-privilege process isolation. No agent has write access outside its worktree.
- **Audit:** 90-day retention for `events.jsonl` and database records (PRD requirement).

---

## 9. Performance and Scalability

| Tier | Concurrent agents | Database | Team size |
|------|------------------|----------|-----------|
| Tier 1 MVP | 5 | SQLite | Individual |
| Tier 2 | 20 | PostgreSQL | 5–10 developers |
| Tier 3 | 30+ | PostgreSQL + connection pool | 10+ developers |

**Token budget management:** Daily budget per project with per-task limits. Threshold alerts at 80%, 90%, 95%. Graceful exhaustion — no in-progress work is failed.

---

## 10. Testing Strategy

| Level | Scope |
|-------|-------|
| Unit | All core modules, 90%+ coverage, <1 s per test |
| Integration | Agent-to-agent, database, git ops, LLM provider |
| E2E | Complete workflows (simple/medium/complex), crash recovery, handoff, merge queue |
| Performance | 30 concurrent agents, budget exhaustion, DB query, API rate limits |

---

## 11. Deployment Architecture

```
Development:
  Local machine → Daemon (Rust binary) + Agents (Python) + SQLite + Git repo

Production:
  Server/Cloud → Daemon (systemd) + Agent pool + PostgreSQL + Prometheus + Jaeger + Loki
```

---

## 12. Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|-------------|
| 1: Foundation (MVP) | 8–12 weeks | Git Worktree Manager, task database, Coordinator, Worker agents, minimalism enforcement, basic merge queue, CLI |
| 2: Specialization | 6–8 weeks | Specialized agents, grilling, decision artifacts, TDD enforcement, code review |
| 3: Monitoring | 4–6 weeks | Three-tier watchdog, project monitors, telemetry, minimal HTML dashboard |
| 4: Scale | 6–8 weeks | Scheduler, multi-platform support, session history, advanced merge queue, React dashboard |
| 5: Federation (optional) | 8–10 weeks | Cross-workspace coordination, work claiming, reputation |

---

## 13. Key Metrics

| Category | Metric | Target |
|----------|--------|--------|
| Code quality | Lines of code reduction | –40% |
| Code quality | Test coverage | 95%+ |
| Code quality | Code reuse percentage | tracked |
| Performance | Cost reduction | –25% |
| Performance | Time reduction | –35% |
| Performance | Token reduction | –40% |
| Reliability | Agent uptime | 99%+ |
| Reliability | Context recovery time | < 30 s |
| Scale | Max concurrent agents | 30+ |
| Scale | API rate limit violations | zero |

---

## 14. Open Questions

1. **RBAC data model** — Security gap. Roles, permissions, middleware hook. Should be a Phase 1 decision, currently unspecced.
2. **Scheduler glue** — The queue half is extracted as [libs/task-queue.md](libs/task-queue.md). The dispatch loop, routing tags, per-task hook creation and the `admit` rule still need a short UMAS-side spec.
3. **`structured-output-parser` decision** — Each pack defines output schemas but the parsing mechanism (Pydantic v2?) has no decision record. ADR needed.
4. **CLI launcher** — Coding Workers run as external CLI harnesses (hybrid model decided; see [modularisation-assessment.md](modularisation-assessment.md) section 4.8). The component that launches and supervises those processes is not specified.
5. **IPC at scale** — File-based `events.jsonl` is fine for Phase 1–2. Phase 3 bottleneck risk flagged in [event-log §11](libs/event-log.md). Broker interface design deferred.
6. **Dashboard backend framework** — FastAPI vs. Express not yet chosen.
7. **25M-token dashboard estimate** — The `UMAS-BUILD-ASSESSMENT.md` estimate was for React. Re-base for the minimal HTML page.
