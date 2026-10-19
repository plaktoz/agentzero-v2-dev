# UMAS Technical Design Specification

> Component design decisions, exception flows, and resolved PRD conflicts for the Unified Multi-Agent Development System.
>
> **This document covers the "why" and "what-if".** For implementation detail (code, schemas, APIs), see the implementation files:
> - [TECHNICAL-DESIGN-SPEC.md](TECHNICAL-DESIGN-SPEC.md) — technology stack, architecture, Context Persistence
> - [TECHNICAL-DESIGN-SPEC-PART2.md](TECHNICAL-DESIGN-SPEC-PART2.md) — Orchestration and Agent Execution
> - [TECHNICAL-DESIGN-SPEC-PART3.md](TECHNICAL-DESIGN-SPEC-PART3.md) — Verification and Monitoring
>
> **Reusable components extracted from this design (each usable without UMAS):**
> - [libs/](libs/README.md) — Tier 1: ten standalone libraries (hook-store, event-log, merge-queue, test-adapters, budget-meter, llm-gateway, watchdog, decision-artifacts, error-classifier, agent-platform)
> - [packs/](packs/README.md) — Tier 2: eight content packs (minimalism-ladder, anti-slop, communication-modes, two-axis-review, specialist-agents, router-heuristic, grilling, test-policy)
>
> **Entry point for the full document set:** [TECHNICAL-DESIGN-SUMMARY.md](TECHNICAL-DESIGN-SUMMARY.md)
> **Product requirements:** [unified-multi-agent-system-prd.md](unified-multi-agent-system-prd.md)
> **Setup and operations guide:** [UMAS-SETUP-GUIDE.md](UMAS-SETUP-GUIDE.md)

---

## Table of Contents

1. [System Components](#1-system-components)
2. [Data Model](#2-data-model)
3. [Component Design](#3-component-design)
   - 3.1 Context Persistence System
   - 3.2 Orchestration System (Coordinator · Router · Scheduler)
   - 3.3 Agent Execution System (Worker · Specialized)
   - 3.4 Verification System (Merge Queue · Code Review · Test Coverage)
   - 3.5 Monitoring System
   - 3.6 Token Budget and Handoff
   - 3.7 Model Policy
   - 3.8 Scalability Roadmap
   - 3.9 CLI Design
4. [Exception Flows](#4-exception-flows)
   - 4.1 Force-deleted project
   - 4.2 Mid-task project deletion
   - 4.3 Corrupted `.umas/` directory
   - 4.4 Project moved or renamed on disk
   - 4.5 Git hook conflict
   - 4.6 Token budget exhausted mid-task
   - 4.7 LLM provider failure mid-task
   - 4.8 Stale worktrees after agent crash
   - 4.9 Merge queue bisect finds no clean subset
   - 4.10 Dependency deadlock in work bundle
   - 4.11 Agent causes test regression
   - 4.12 Database corruption or lock
   - 4.13 Concurrent CLI processes
   - 4.14 `umas update` while agents are active
   - 4.15 Dashboard / CLI showing stale state
   - 4.16 Disk space exhaustion

---

## 1. System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Human Interface Layer                        │
│                    CLI (primary) · Dashboard (secondary)            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                       Orchestration Layer                           │
│             Coordinator · Router · Scheduler                        │
└──────┬───────────────────────────────────────────┬──────────────────┘
       │                                           │
┌──────▼────────────────┐             ┌────────────▼─────────────────┐
│   Agent Execution     │             │     Verification System      │
│  Worker · Specialized │             │  Merge Queue · Review · TDD  │
└──────┬────────────────┘             └────────────┬─────────────────┘
       │                                           │
┌──────▼───────────────────────────────────────────▼─────────────────┐
│                      Context Persistence Layer                      │
│         Git Worktrees · Decision Artifacts · Session Discovery      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                        Monitoring Layer                             │
│           Daemon · Triage Agent · System Patrol · Project Monitor  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 Reusable Components

Parts of these components are specified as standalone units with no dependency on UMAS. The sections below describe how UMAS uses them; the standalone specs are the authority on their behaviour. Where the two differ, the standalone spec records the difference in its "Source material and deviations" section.

**Tier 1, libraries** ([index](libs/README.md))

| Component here | Standalone spec |
|----------------|-----------------|
| Hooks and worktree state (§3.1) | [hook-store](libs/hook-store.md) |
| `.umas/events.jsonl` signalling (§3.3) | [event-log](libs/event-log.md) |
| Merge Queue Processor (§3.4) | [merge-queue](libs/merge-queue.md) |
| Test Runner (§3.4) | [test-adapters](libs/test-adapters.md) |
| Token budget, handoff packet (§3.6) | [budget-meter](libs/budget-meter.md) |
| Provider failure handling (§3.7, §4.7) | [llm-gateway](libs/llm-gateway.md) |
| Three-tier watchdog (§3.5) | [watchdog](libs/watchdog.md) |
| Decision artifacts, shortcut ledger (§3.1, §3.3) | [decision-artifacts](libs/decision-artifacts.md) |
| Error severity, recoverability, escalation records (§3.3, §4) | [error-classifier](libs/error-classifier.md) |
| Platform adapters, work assignment, cross-platform context transfer (PRD Module 7) | [agent-platform](libs/agent-platform.md) |

**Tier 2, content packs** ([index](packs/README.md))

| Component here | Standalone spec |
|----------------|-----------------|
| Minimalism ladder, shortcut comments (§3.3) | [minimalism-ladder](packs/minimalism-ladder.md) |
| Anti-slop principles (PRD §11) | [anti-slop](packs/anti-slop.md) |
| Communication modes (PRD §11.9) | [communication-modes](packs/communication-modes.md) |
| Code Review, two-axis (§3.4) | [two-axis-review](packs/two-axis-review.md) |
| Specialized Agents (§3.3) | [specialist-agents](packs/specialist-agents.md) |
| Router scoring (§3.2) | [router-heuristic](packs/router-heuristic.md) |
| Grilling and the propulsion rule (§3.2) | [grilling](packs/grilling.md) |
| Test Coverage Policy (§3.4) | [test-policy](packs/test-policy.md) |

---

## 2. Data Model

### Project record (stored in `~/.umas/database.db`)

```sql
CREATE TABLE projects (
  id          TEXT PRIMARY KEY,          -- slug, e.g. "my-api"
  name        TEXT NOT NULL,
  path        TEXT NOT NULL UNIQUE,      -- absolute path to repo root
  status      TEXT NOT NULL              -- active | orphaned | archived
              DEFAULT 'active',
  registered_at DATETIME NOT NULL,
  last_seen_at  DATETIME                 -- updated on any umas operation
);
```

### Work bundle record

```sql
CREATE TABLE work_bundles (
  id          TEXT PRIMARY KEY,
  project_id  TEXT REFERENCES projects(id),
  type        TEXT NOT NULL,             -- epic | story | task
  status      TEXT NOT NULL,             -- pending | in_progress | completed | failed
  parent_id   TEXT REFERENCES work_bundles(id),
  hook_path   TEXT,                      -- relative path inside .umas/worktrees/
  agent_id    TEXT,
  created_at  DATETIME NOT NULL,
  completed_at DATETIME
);
```

### Agent session record

```sql
CREATE TABLE agent_sessions (
  id           TEXT PRIMARY KEY,
  project_id   TEXT REFERENCES projects(id),
  bundle_id    TEXT REFERENCES work_bundles(id),
  status       TEXT NOT NULL,
    -- spawned       : session created, agent not yet responsive
    -- active        : agent working normally
    -- handoff       : agent committed state, transferring to successor
    -- crashed       : unresponsive, last heartbeat exceeded threshold
    -- done          : task completed successfully
    -- budget_paused : daily token budget exhausted; waiting for reset or increase
    -- provider_failed : primary and fallback providers both unavailable
  token_used   INTEGER DEFAULT 0,
  token_limit  INTEGER NOT NULL,
  last_heartbeat DATETIME,
  started_at   DATETIME NOT NULL,
  ended_at     DATETIME
);
```

Sessions in `budget_paused` or `provider_failed` are resumable. They are not treated as failures unless they remain in that state beyond a configurable timeout (default: 24 hours).

---

## 3. Component Design

### 3.1 Context Persistence System

**Storage:** Each agent gets a Git worktree inside `.umas/worktrees/<hook-name>/`. The worktree is linked to the main repo but is a separate working directory — agents commit state directly to their worktree branch.

**State commit protocol:**
- Agent commits after every major step (not just at completion)
- Commit message format: `[umas] <agent-id> <step-summary> [tokens: N]`
- A `STATE.md` file in the worktree root holds: current task, recent decisions (last 10), explicit next steps, and references to relevant files

**Session discovery:** All agent operations are appended to `.umas/events.jsonl` (append-only, one JSON object per line). On handoff or restart, the incoming agent queries this log filtered by `hook_path` to reconstruct what happened.

```json
{ "ts": "2024-01-15T10:23:01Z", "agent": "alice", "hook": "auth-login/", "event": "step_complete", "summary": "validation logic done, email check pending" }
```

**Decision artifacts location:**

| Artifact | Location in repo |
|----------|-----------------|
| PRFAQ | `docs/product/<feature>.prfaq.md` |
| ADR | `docs/decisions/ADR-<NNN>-<title>.md` |
| Spec | `docs/specs/<feature>.spec.md` |
| GLOSSARY | `GLOSSARY.md` (repo root) |

---

### 3.2 Orchestration System

#### Coordinator

- Receives human requests via `umas request "<text>"`
- Runs grilling session for human-initiated requests only — agent-to-agent handoffs execute immediately without grilling
- Creates a `work_bundle` record in the database
- Delegates to Router for skill/workflow selection
- Delegates to Scheduler for agent dispatch
- Never writes application code

**Coordinator state machine:**

```
IDLE → GRILLING → PLANNING → DISPATCHING → MONITORING → DONE
                                              ↑               |
                                              └── ESCALATED ──┘
```

**Full transition rules:**

| From | To | Trigger |
|------|----|---------|
| `IDLE` | `GRILLING` | Human submits request |
| `GRILLING` | `PLANNING` | Human confirms (or grilling skipped for agent-to-agent) |
| `PLANNING` | `DISPATCHING` | Work bundle created and validated |
| `DISPATCHING` | `MONITORING` | All ready tasks dispatched |
| `MONITORING` | `DONE` | All tasks in bundle reach `completed` |
| `MONITORING` | `ESCALATED` | Any agent appends an `escalate` event to `.umas/events.jsonl` |
| `ESCALATED` | `DISPATCHING` | Human resolves escalation and approves resumption |
| `ESCALATED` | `DONE` | Human cancels the work bundle entirely |
| Any state | `IDLE` | Work bundle cancelled or all tasks failed beyond retry limit |

A Coordinator handling multiple work bundles concurrently maintains an independent state machine instance per bundle. `ESCALATED` in one bundle does not pause other bundles.

#### Router (Skill Selection)

Selects workflow based on task complexity using a scoring heuristic:

| Signal | Weight |
|--------|--------|
| Number of files likely affected (estimated from request text + codebase scan) | High |
| Request mentions new feature / new system / new service | High |
| Request scope is ambiguous (no clear single entry point) | Medium |
| Request involves user-facing UI | Medium |
| Request involves security, auth, payments, data migration | High |
| Request is a bug fix with a specific file/line cited | Low (→ simple) |

**Routing thresholds:**

| Score band | Route |
|-----------|-------|
| Low | Direct worker agent |
| Medium | Architect + worker |
| High | Full specialist panel → workers |
| Greenfield marker detected | PM → Architect → parallel workers (regardless of score) |

The classification and its score are logged with the work bundle record. The user can override with `--route simple|medium|large|greenfield`.

> Standalone spec with numeric weights and fixtures: [packs/router-heuristic.md](packs/router-heuristic.md). Grilling trigger rules: [packs/grilling.md](packs/grilling.md).

**Minimalism vs Specialization:** Specialization is only invoked where complexity justifies the cost. Simple requests go directly to a minimalist worker — no specialist overhead. The ladder principle (§3.3) applies at every complexity tier.

#### Scheduler (Capacity Management)

- Maintains a `ready_queue` of tasks with no unresolved dependencies
- Dispatches agents up to the configured concurrency limit
- When at capacity, tasks stay in `ready_queue` until a slot opens
- Checks and dispatches newly unblocked tasks on every task completion event

```python
def on_task_complete(task_id):
    mark_complete(task_id)
    unblock_dependents(task_id)      # move newly-unblocked tasks to ready_queue
    check_parent_auto_complete(task_id)
    dispatch_ready_tasks()           # fill open slots
```

---

### 3.3 Agent Execution System

#### Worker Agents

- Spawned with: task ID, hook path, compressed context (≤15k tokens)
- Operate exclusively inside their assigned worktree
- Commit state at each major step
- Signal completion: commit worktree with message `[umas:done] <task-id>` → Scheduler detects via hook or database poll
- Signal blockers: append `{"event":"escalate","severity":"P1","reason":"..."}` to `.umas/events.jsonl` → Coordinator picks up on next poll

**Agent signalling protocol:**

All agent-to-orchestration signalling goes through the filesystem — no separate CLI tool is required. Two channels are used:

1. **Worktree commits** — completion and checkpoint signals, detectable by the Scheduler via Git hook or database poll
2. **`.umas/events.jsonl`** — escalation and handoff signals, polled by the Coordinator and Project Monitor

| Signal | Mechanism | Who reads it |
|--------|-----------|-------------|
| Task complete | Commit worktree: `[umas:done] <task-id>` | Scheduler — marks bundle complete, dispatches next ready tasks |
| Task blocked | Append to `events.jsonl`: `{"event":"escalate","severity":"P0\|P1\|P2","reason":"..."}` | Coordinator — routes by severity |
| Checkpoint (mid-task state) | Commit worktree: `[umas:checkpoint] <summary>` | Project Monitor — updates `last_heartbeat` |
| Handoff request | Append to `events.jsonl`: `{"event":"handoff_request","task_id":"..."}` | Scheduler — spawns successor agent |

**Minimalism ladder (enforced before any code is written):**

1. Does this feature need to exist? (skip if not asked)
2. Does it already exist in this codebase?
3. Is it in the standard library or platform?
4. Is it an already-installed dependency?
5. Can it be one readable line?
6. Otherwise: minimum code that works

The ladder runs **after** reading the relevant code, never before.

> Standalone spec: [packs/minimalism-ladder.md](packs/minimalism-ladder.md).

**Shortcut comments:** Agents may leave a structured comment to mark a deliberate deferral — format `// SHORTCUT: <what> — <when to fix>`. This is the only permitted comment that does not explain "why" code exists. It must be tracked in the project's debt ledger. Decorative, explanatory, or redundant comments are not permitted.

#### Specialized Agents

Invoked by the Router for medium/large tasks:

| Role | Responsibility | When invoked |
|------|---------------|-------------|
| Analyst | Clarify requirements, surface ambiguity | All non-trivial requests |
| Product Manager | User value, PRFAQ, product decisions | Greenfield, new features |
| Architect | ADR, tech stack, system design | Medium+ complexity |
| UX Designer | Interface and interaction design | User-facing changes |
| Developer | Implementation with minimalism enforcement | All implementation tasks |

> Standalone spec with prompts and output schemas: [packs/specialist-agents.md](packs/specialist-agents.md).

---

### 3.4 Verification System

#### Merge Queue Processor

Operates on a **permanent** `merge-queue` worktree created once during `umas init --project`. The worktree persists for the lifetime of the project — only the temp test branch is created and destroyed per batch.

**Worktree state machine:**

```
IDLE        — no PRs ready; worktree is on a clean baseline commit
COLLECTING  — accumulating ready PRs into the batch
TESTING     — temp branch created, tests running
BISECTING   — failure found, bisect in progress
MERGING     — tests passed, merging to main
```

**Batch merge algorithm:**

```
1. Collect all PRs with status = ready_to_merge
2. Create temp branch: merge ALL PRs onto it
3. Run full test suite on temp branch
4. If green → merge all to main, delete temp branch
5. If red → bisect:
     Split batch in half, test each half
     Recurse until culprit isolated
     Merge only the passing half
     Re-queue the failing PR with status = blocked + reason
```

The Merge Queue Processor is a dedicated agent: it only merges branches, never writes application code.

#### Code Review (Two-Axis)

Every PR goes through two independent review passes run in parallel:

- **Standards axis:** code quality, style, patterns, maintainability
- **Spec axis:** does it solve the right problem, does it meet the task requirements

Each finding is filed as: `{ location, what, problem, fix, consequence }`. Findings without a concrete fix are not filed.

> Standalone spec: [packs/two-axis-review.md](packs/two-axis-review.md).

#### Test Coverage Policy

Test coverage is configurable per project via `umas.config.yaml`:

| Mode | Behaviour | Config |
|------|-----------|--------|
| `selective` (default) | Tests required only for risky logic: branches, loops, parsers, money, security | `testing.tdd_required: false` |
| `strict` | Full TDD (red-green-refactor) for every feature | `testing.tdd_required: true` |

Trivial changes (renaming, formatting, config-only) require no tests under either mode. Coverage target is set separately via `testing.coverage_target` (number, 0–100).

> Standalone spec: [packs/test-policy.md](packs/test-policy.md). Test execution and result format: [libs/test-adapters.md](libs/test-adapters.md).

---

### 3.5 Monitoring System

#### Three-Tier Watchdog

```
Tier 1 — Daemon (OS process)
  Heartbeats Triage Agent every 3 min
  If no heartbeat response → restart Triage Agent

Tier 2 — Triage Agent (AI agent, always running)
  Monitors System Patrol
  If System Patrol stuck → investigates, restarts

Tier 3 — System Patrol (AI agent, always running)
  Polls all Project Monitors and Merge Queue Processors
  Dispatches maintenance workers for detected issues
  Reports to Triage Agent on anomalies
```

#### Project Monitor (per project)

Polls all active agents for that project every 60 seconds. Stuck detection heuristics:

- No `STATE.md` commit in last 10 minutes → agent may be stuck
- No heartbeat in last 5 minutes → agent likely crashed
- Token usage > 95% without handoff request → emergency handoff

Recovery actions (in order):
1. Nudge (send a wake signal)
2. Graceful handoff (if agent responds)
3. Emergency handoff (if agent unresponsive — recover from last `STATE.md` commit)

---

### 3.6 Token Budget and Handoff

**Handoff triggers:**

| Trigger | Type | Action |
|---------|------|--------|
| Token usage ≥ 90% of session limit | Graceful | Agent commits state, requests handoff |
| Token usage ≥ 95% (missed graceful) | Emergency | Monitor forces handoff from last checkpoint |
| Daily project budget ≥ 80% | Warning | Alert human |
| Daily project budget ≥ 100% | Exhaustion | Queue new work, don't fail in-progress work |

**Context compression on handoff:**

Full context (~175k tokens) is compressed to a handoff packet (~15k tokens) containing:
- Current task and progress percentage
- Last 10 decisions
- Explicit next steps
- Pointers to relevant files (path + line range, not content)

The incoming agent reads the handoff packet and the `STATE.md` in the worktree. It does not re-read the full conversation history.

---

### 3.7 Model Policy

The system uses a single model by default. Role-based model mapping is opt-in for users who need it.

**Default:** All roles use the same configured model — minimal setup, no per-role overhead.

**Opt-in role mapping** (set in `umas.config.yaml` under `agents.<role>.model`):

| Role | Default model | Override via |
|------|--------------|-------------|
| Coordinator | project default | `agents.coordinator.model` |
| Worker | project default | `agents.worker.model` |
| Architect | project default | `agents.specialized.architect.model` |
| Reviewer | project default | `agents.specialized.reviewer.model` |

**Multi-model panels** are opt-in and reserved for decisions with irreversible consequences (architecture choices, security design, data migrations). When enabled, the same prompt is sent to the configured models and responses are synthesised. Panel behaviour is disabled by default and enabled per-decision-type via config.

```yaml
# umas.config.yaml — optional overrides
agents:
  worker:
    model: claude-3-5-sonnet
  specialized:
    architect:
      model: claude-3-5-sonnet
      panel_enabled: true        # enable multi-model panel for architecture decisions
```

---

### 3.8 Scalability Roadmap

**MVP (single workspace):** One `~/.umas/database.db`, all projects registered on the same machine, up to 5 concurrent agents with SQLite.

**Federation (v2, deferred):** Cross-workspace coordination allowing agents on different machines to work on the same project. Not built in MVP — the system is designed with federation in mind (project registration by path, event log as primary state) but the Federation Layer is not implemented until demand warrants it.

This is a deliberate phased decision: federation adds significant complexity and is not a day-one requirement. The single-workspace architecture handles all known use cases up to Tier 3 scale (30+ agents, PostgreSQL).

---

### 3.9 CLI Design

#### `umas init` vs `umas init --project`

These are two distinct commands with different scopes:

| Command | Scope | What it does |
|---------|-------|-------------|
| `umas init` | Machine-wide (once) | Creates `~/.umas/` global directory, initialises `database.db`, applies user-level defaults |
| `umas init --project` | Per-repo (once per project) | Creates `.umas/` inside the current repo, installs Git hooks, updates `.gitignore` |

`umas init` must be run before `umas init --project`. If `~/.umas/` does not exist when `umas init --project` is called, the system runs `umas init` automatically and then proceeds. Both commands are fully idempotent — running either a second time is safe.

#### `umas project register`

`umas project register` is a **registration command** — it writes a record to `~/.umas/database.db`. It does not scaffold directories, create files, or do anything on the filesystem.

| Command | Responsibility |
|---------|---------------|
| `umas init --project` | Creates `.umas/` directory, installs Git hooks, updates `.gitignore` — **filesystem only** |
| `umas project register <name>` | Writes a record to `~/.umas/database.db` — **database only** |

They must be run in that order. Running `umas project register` before `umas init --project` fails with:

```
Error: No .umas/ directory found in current directory.
Run `umas init --project` first, then retry.
```

**Full onboarding flow — new project:**

```bash
mkdir my-api && cd my-api && git init   # user creates repo (UMAS does not do this)
umas init --project                      # attaches UMAS filesystem artifacts
umas project register my-api             # registers path in database.db
umas request "Build a REST API for..."   # submit work
```

**Full onboarding flow — existing project:**

```bash
cd ~/existing-project
umas init --project
umas project register existing-project
```

---

## 4. Exception Flows

### 4.1 Force-Deleted Project

**Scenario:** User runs `rm -rf ~/projects/my-api` while the project is still registered in `database.db`.

**Detection:** Lazy — on any UMAS operation that references this project, the system checks whether `projects.path` exists on disk before proceeding.

**Detection also runs proactively** during `umas health-check` and `umas project list`, which scan all registered paths.

**Recovery flow:**

```
umas project list

→ my-api  [ORPHANED — path not found: /Users/you/projects/my-api]
→ payments-svc  [active]

Orphaned project detected.
Options:
  1. Remove from database (path is gone, clean up record)
  2. Re-register at new path (project was moved, not deleted)
  3. Ignore for now

Choice [1-3]:
```

If option 1: delete the project record and all associated work bundle and agent session records. Log to audit trail.

If active agents were running at time of deletion, see §4.2.

**Alternative flow — user chooses "Ignore for now" (option 3):**

The orphaned record is left in `database.db` with status = `orphaned`. UMAS will not attempt to operate on it. On every subsequent `umas project list` it will be shown with the `[ORPHANED]` tag. After 30 days of unresolved orphan status, `umas health-check` will escalate with a `P2` warning recommending cleanup. The record is never auto-deleted.

---

### 4.2 Mid-Task Project Deletion (Agents Running)

**Scenario:** Project directory is deleted while one or more agents have active sessions against it.

**Detection:** Project Monitor's next health poll (within 60 seconds) detects the missing path via filesystem check.

**Recovery flow:**

1. Project Monitor marks all active agent sessions for this project as `crashed`
2. Project Monitor escalates to System Patrol as a P1 (high severity) event
3. System Patrol marks all in-flight work bundles as `failed` with reason `project_path_missing`
4. Human is notified via escalation channel:

```
[P1 ESCALATION] Project "my-api" path not found on disk.
3 agent sessions terminated. 2 work bundles marked failed.
Work state preserved in worktree branches (if they were committed before deletion).
Action required: `umas project list` to resolve.
```

5. Worktree branches that were committed before the deletion still exist in the Git object store (as orphaned branches). If the user restores the project directory and re-registers, those branches can be recovered.

**Alternative flow — project directory is restored before the next poll:**

If the user restores the directory (e.g., from backup or by reversing the delete) before the Project Monitor's 60-second poll fires, the path check passes and no crash is recorded. The active agent sessions continue as if nothing happened. The system does not distinguish between a brief unavailability and a permanent deletion until the poll actually fires.

---

### 4.3 Corrupted `.umas/` Directory

**Scenario:** The `.umas/` directory in a project exists but is partially broken — missing `config.yaml`, permission error, corrupted `events.jsonl`, etc.

**Detection:** On every `umas init --project` (idempotent) and `umas health-check`, the system validates the `.umas/` structure.

**Validation checklist:**

```
✓ .umas/ directory exists and is readable
✓ .umas/config.yaml exists and is valid YAML
✓ .umas/events.jsonl is appendable
✓ .umas/worktrees/ directory exists
✗ .umas/hooks/pre-commit missing or not executable
```

**Recovery:** `umas init --project` is idempotent — it recreates any missing pieces without touching existing files. Explicitly:

- Missing files → recreated
- Corrupted `config.yaml` → backed up as `config.yaml.bak`, replaced with defaults, user notified
- Corrupted `events.jsonl` → backed up, new empty log started (history loss is logged as a warning)
- Missing worktree directory → recreated (orphaned worktree branches are not deleted)

**Alternative flow — UMAS hook itself is the corrupted file:**

If `.umas/hooks/pre-commit` is corrupted or missing, `umas init --project` reinstalls it. However, if the corruption caused the Git hook chain to break (i.e., the project's `.git/hooks/pre-commit` now points to a missing file), the re-install also repairs the Git-side chain by re-running the hook detection and chaining logic from §4.5. The user is notified that the hook was repaired.

---

### 4.4 Project Moved or Renamed on Disk

**Scenario:** User does `mv ~/projects/my-api ~/projects/my-api-v2` without telling UMAS.

**Detection:** Same as §4.1 — next UMAS operation finds the registered path missing.

**Recovery flow:**

The orphaned project prompt (§4.1) offers option 2 — "Re-register at new path":

```
Enter the new path for project "my-api": ~/projects/my-api-v2

Verifying path...
✓ Git repository found
✓ .umas/ directory found
✓ Project name matches

Updating database record.
✓ Project "my-api" re-registered at /Users/you/projects/my-api-v2
```

All work bundle and agent session history is preserved — only the `path` column in the project record is updated.

**Alternative flow — `.umas/` directory was not moved with the project:**

If the user moved only the code (e.g., copied files without the hidden `.umas/` directory), the new path fails the `umas/` directory check during re-registration. The system prompts:

```
New path found, but no .umas/ directory at /Users/you/projects/my-api-v2.
Run `umas init --project` in the new directory first, then retry re-registration.
Previous history will be re-linked after registration completes.
```

---

### 4.5 Git Hook Conflict

**Scenario:** The project uses a hook manager (Husky, Lefthook, pre-commit framework) or has a compiled binary as its `pre-commit` hook. UMAS cannot simply prepend to it.

**Detection:** During `umas init --project`, the system inspects the existing `.git/hooks/pre-commit`:

```python
def detect_hook_type(hook_path):
    if not exists(hook_path):
        return "none"
    if is_binary(hook_path):
        return "binary"
    content = read(hook_path)
    if "husky" in content:   return "husky"
    if "lefthook" in content: return "lefthook"
    if "pre-commit" in content and "framework" in content: return "pre-commit-framework"
    return "plain_shell"
```

**Recovery by hook type:**

| Detected type | Action |
|--------------|--------|
| `none` | Install UMAS hook directly |
| `plain_shell` | Prepend UMAS call, preserve rest |
| `husky` | Add UMAS as a husky hook in `.husky/pre-commit` |
| `lefthook` | Add UMAS step to `lefthook.yml` |
| `pre-commit-framework` | Add UMAS as a local hook in `.pre-commit-config.yaml` |
| `binary` | Cannot chain. Warn user, skip hook installation, continue without hooks. Context persistence degrades to polling-only mode. |

For `binary`, the user is warned at install time:

```
Warning: Existing pre-commit hook is a compiled binary. UMAS cannot chain onto it.
Context persistence will use polling mode (less reliable than hook mode).
To enable hook mode, replace the binary hook with a shell script that calls it.
```

**Alternative flow — UMAS itself is being updated and its hook version changes:**

During `umas update`, if the installed UMAS hook in the project's chain is outdated, the updater:
1. Detects the UMAS-owned hook line in the chain (identified by the `# umas-managed` comment marker)
2. Replaces only that line with the new hook path
3. Leaves all other hook entries untouched

If no `# umas-managed` marker is found (e.g., manual edit removed it), the updater skips the hook update and warns:

```
Warning: Could not locate managed hook marker in .git/hooks/pre-commit.
Hook was not updated. Run `umas init --project --repair-hooks` to reinstall.
```

---

### 4.6 Token Budget Exhausted Mid-Task

**Scenario:** A project's daily token budget hits 100% while an agent is actively working on a task.

**Behaviour:** In-progress agent sessions are **not terminated**. They are allowed to complete their current step and commit state.

**New work dispatch is paused:**

```
[BUDGET] Project "my-api" daily token budget exhausted (100k / 100k).
2 pending tasks queued (not dispatched).
In-progress agents (2) will complete their current step then pause.
Budget resets at 00:00 UTC. Or increase budget: umas project config my-api --budget 150000
```

**Agent behaviour on budget exhaustion signal:**

1. Complete current atomic step (do not stop mid-function)
2. Commit current state to worktree with message: `[umas] budget-pause — state committed, resuming when budget resets`
3. Set session status to `budget_paused`
4. Project Monitor resumes dispatch when budget resets or is increased

**Queued tasks** retain their position in the ready queue. Order is preserved on resume.

**Alternative flow — budget is increased while agents are in `budget_paused` state:**

If the user runs `umas project config my-api --budget 150000` while sessions are paused, the Project Monitor detects the new budget on its next poll cycle (within 60 seconds). It immediately resumes dispatch — it does not wait for UTC midnight. Sessions in `budget_paused` are transitioned back to `active` and work continues from the committed checkpoint.

---

### 4.7 LLM Provider Failure Mid-Task

**Scenario:** The primary LLM provider returns errors (5xx, rate limit, timeout) while an agent is active.

**Retry policy (primary provider):**

| Error type | Retry |
|-----------|-------|
| 429 Rate limit | Exponential backoff: 5s, 15s, 45s, then failover |
| 5xx Server error | 3 immediate retries, then failover |
| Timeout (>30s) | 2 retries, then failover |
| 401/403 Auth error | No retry — escalate to human immediately (P0) |

**Failover to secondary provider:**

The task does **not restart from zero**. The agent's last committed `STATE.md` is used to resume:

1. Last step is noted from `STATE.md`
2. Compressed context is reconstructed (same as handoff packet — §3.6)
3. New session is spawned against the fallback provider with the compressed context
4. Work continues from the last checkpoint

```
[FAILOVER] Primary provider (Anthropic) unavailable after 3 retries.
Agent "alice" session-123 paused at step: "email verification flow".
Spawning session-124 on fallback provider (OpenAI).
Context recovered from last checkpoint (committed 2 min ago).
```

**If no fallback provider is configured:**

```
[P1 ESCALATION] Primary provider unavailable and no fallback configured.
Agent "alice" session-123 paused. Task "signup-endpoint" blocked.
Action required: restore provider connectivity or configure fallback.
  umas config set llm_provider.fallback openai
```

**Alternative flow — fallback provider also fails:**

If the fallback provider is also unavailable, the session status is set to `provider_failed` (see §4.6). The system does not attempt further providers. A P1 escalation is raised. The task remains in its last committed checkpoint state indefinitely until either provider recovers or the human cancels the task.

There is no automatic retry loop against providers — repeated blind retries risk burning tokens on timeout charges. Recovery is human-initiated: `umas agents resume <session-id>` once connectivity is restored.

---

### 4.8 Stale Worktrees After Agent Crash

**Scenario:** An agent crashes or is force-killed, leaving a worktree directory in `.umas/worktrees/` that is no longer associated with any active session.

**Detection:** On startup (`umas start-all`), during `umas health-check`, and as part of Project Monitor's hourly sweep, the system cross-references:

- All directories in `.umas/worktrees/`
- All `active` or `in_progress` session records in the database

Directories with no matching active session record are **stale worktrees**.

**Cleanup policy:**

| Worktree age | Action |
|-------------|--------|
| < 24 hours | Keep. Agent may be recoverable. |
| 24h – 7 days | Mark as `stale`, surface in `umas health-check` output |
| > 7 days | Prompt user for deletion during `umas health-check` |

**Manual cleanup:**

```bash
umas worktrees list
# → auth-login/    active   (session-123)
# → auth-signup/   STALE    (no session, 3 days old)

umas worktrees clean --stale
# → Removed: auth-signup/ (3 days old, no active session)
```

Stale worktree branches are preserved in the Git object store even after the working directory is removed, so work is not permanently lost.

**Alternative flow — stale worktree has uncommitted changes (agent crashed mid-edit):**

If the agent crashed between a file edit and a worktree commit (checkpoint or done signal), the worktree working directory may have uncommitted changes. These are not in the Git object store and are at risk.

During stale detection, the system checks for uncommitted changes via `git status` inside the worktree:

```bash
git -C .umas/worktrees/auth-signup/ status --porcelain
```

If uncommitted changes are found:
1. The worktree is **not** cleaned up automatically regardless of age
2. It is tagged `stale-dirty` in `umas worktrees list`
3. Human must explicitly resolve: commit the partial work, discard it, or hand it to a new agent for triage

```
umas worktrees list
# → auth-signup/   STALE-DIRTY   (uncommitted changes, 3 days old — manual action required)

umas worktrees recover auth-signup/
# Spawns a triage agent that reviews the uncommitted diff and either:
#   - commits it with a summary if coherent
#   - discards it with a log entry if not
```

---

### 4.9 Merge Queue Bisect Finds No Clean Subset

**Scenario:** The merge queue bisects a failing batch and determines that every individual PR fails independently — there is no subset that passes.

**This means:** Every PR in the current batch has its own failure, unrelated to combination effects.

**Behaviour:**

1. All PRs are moved to status `blocked` with reason `failed_in_isolation`
2. Each PR's failure log is attached to its work bundle record
3. The agents that produced those PRs are re-spawned to fix the failures (using their original hooks — state is preserved)
4. Human is notified:

```
[MERGE QUEUE] Batch failed. Bisect result: all 3 PRs fail independently.
  - task-create: 2 test failures (login.test.ts:45, login.test.ts:67)
  - task-list:   1 test failure  (list.test.ts:12)
  - task-update: build error     (TypeScript compile error in update.handler.ts)

Re-spawning agents to fix. Monitor with: umas watch
```

**Alternative flow — re-spawned fix agents also fail (retry limit):**

Each PR has a `retry_count` field in the work bundle record. The default retry limit is 3. If a fix agent fails 3 times on the same PR:
1. The PR is moved to status `permanently_failed`
2. Escalated to human as P1
3. No further automatic re-spawning

The human can reset the retry count manually: `umas work-bundle retry <bundle-id> --reset-retries`

The retry count resets to 0 on any successful `[umas:checkpoint]` commit — it tracks consecutive failures, not total attempts.

---

### 4.10 Dependency Deadlock in Work Bundle

**Scenario:** Two tasks are inadvertently configured to block each other (A blocks B, B blocks A), or a task's `blocked_by` references a task that no longer exists.

**Detection:** When a work bundle is created, the Coordinator runs a dependency graph validation:

```python
def validate_dependencies(work_bundle):
    graph = build_dependency_graph(work_bundle)
    cycles = detect_cycles(graph)          # DFS-based cycle detection
    dangling = find_dangling_refs(graph)   # blocked_by IDs that don't exist
    return cycles, dangling
```

**If detected at creation time:** Bundle is rejected with a clear error identifying the cycle or dangling reference. User must fix before submitting.

**If detected at runtime** (e.g., a completed task was deleted from the database): Task is moved to `blocked` with reason `dependency_missing`, and a P1 escalation is raised for human resolution.

**Alternative flow — race condition creates a transient deadlock:**

If two tasks complete in rapid succession and their completion events are processed out of order (e.g., under high scheduler load), a task may momentarily appear blocked by a task that has already completed. The Scheduler resolves this by re-running dependency validation on every `on_task_complete` event — if a blocking task is already `completed`, the blocked task is immediately moved to `ready_queue`. This is a self-healing check, not an escalation.

---

### 4.11 Agent Causes Test Regression

**Scenario:** An agent's PR passes its own tests but breaks tests that were passing before (regression). This is caught by the Merge Queue Processor when it tests the merged stack.

**Detection:** The Merge Queue Processor's bisect algorithm isolates the offending PR (see §3.4). The specific failing tests are recorded in the work bundle record.

**Recovery flow:**

1. The offending PR is moved to `blocked` with reason `regression` and the list of newly failing tests attached
2. The originating agent is re-spawned on the same hook with context:
   - The regression test names and failure output
   - The diff of the PR that caused the regression
   - Instruction: fix the regression, do not change the test

```
[MERGE QUEUE] PR "task-create" causes regression.
Newly failing tests:
  - auth.test.ts:112 (was passing before this PR)
  - auth.test.ts:134 (was passing before this PR)

Re-spawning agent on hook task-create/ with regression context.
```

3. The agent is expected to fix its implementation — not the existing tests — unless the existing tests are provably wrong (in which case it must escalate with justification)

**Alternative flow — regression is in a test that was already flaky:**

If the failing test has a history of intermittent failures (tracked in `.umas/events.jsonl` as previous `test_flaky` events), the Merge Queue Processor flags it as a potential flaky failure rather than a regression and re-runs the test suite once before escalating. If it passes on the second run, the PR proceeds to merge.

---

### 4.12 Database Corruption or Lock

**Scenario:** `~/.umas/database.db` becomes corrupted (e.g., interrupted write, filesystem error) or is locked by another process.

**Detection:** Every UMAS command that opens the database runs a quick integrity check (`PRAGMA integrity_check`) on startup. A failed check or a lock timeout (default: 5 seconds) triggers this flow.

**Recovery flow — lock:**

1. UMAS waits up to 5 seconds for the lock to release
2. If still locked after 5 seconds, it surfaces the PID holding the lock (if detectable) and exits with a clear error:

```
Error: database is locked by process 4821 (umas start-all).
If that process is no longer running, remove the lock file:
  rm ~/.umas/database.db-wal
  rm ~/.umas/database.db-shm
Then retry.
```

**Recovery flow — corruption:**

1. UMAS detects the integrity check failure and immediately stops without writing further
2. It checks for a recent backup (`~/.umas/database.db.bak` — written on every `umas update` and daily by the Daemon)
3. If a backup exists:

```
Error: database integrity check failed.
Most recent backup: ~/.umas/database.db.bak (2 hours ago).
Restore backup? [y/N]: y
✓ Restored. 2-hour data loss. Re-run any work submitted in the last 2 hours.
```

4. If no backup exists, UMAS initialises a fresh database and prompts the user to re-register projects. Work bundle and session history is lost; worktree branches in Git are unaffected and represent the real source of truth for in-progress work.

**Alternative flow — SQLite → PostgreSQL migration in progress during corruption:**

If corruption occurs during a database migration, the migration transaction is rolled back. The original SQLite file is preserved untouched. The user must resolve the corruption in SQLite before retrying the migration.

---

### 4.13 Concurrent CLI Processes

**Scenario:** Two terminal sessions run `umas` commands simultaneously against the same project or database — e.g., `umas request` in one terminal while `umas agents spawn` runs in another.

**Mechanism:** UMAS uses SQLite's WAL (Write-Ahead Logging) mode for the database, which allows one writer and multiple concurrent readers. For write-heavy operations (spawn, register, bundle create), UMAS acquires an advisory file lock (`~/.umas/.lock`) for the duration of the write transaction.

**What happens on contention:**

| Operation | Concurrent behaviour |
|-----------|---------------------|
| `umas project list` (read) | Succeeds immediately — reads do not block |
| `umas request` (write) | Waits up to 5 seconds for lock; proceeds or exits with error |
| `umas agents spawn` (write) | Same — queues behind the lock |
| `umas watch` (read stream) | Unaffected — polls only |

**Advisory rule:** Running two write commands in the same second is a user error, not a system error. UMAS does not attempt to merge concurrent writes — it serialises them. If two `umas request` calls land simultaneously, they are processed sequentially in lock-acquisition order.

**Alternative flow — `umas start-all` run twice:**

Running `umas start-all` a second time while the system is already running detects the existing Daemon PID in `~/.umas/daemon.pid` and exits cleanly:

```
System is already running (daemon PID 3821).
Use `umas status` to check health or `umas stop-all` to stop.
```

---

### 4.14 `umas update` While Agents Are Active

**Scenario:** The user runs `umas update` to upgrade the UMAS binary while one or more agent sessions are active.

**Policy:** `umas update` is a **non-disruptive update** by default. It never terminates active sessions.

**Update sequence:**

1. Download new binary to a staging path (`~/.umas/bin/umas.next`)
2. Check active sessions: `SELECT count(*) FROM agent_sessions WHERE status IN ('active', 'spawned')`
3. If sessions are active:

```
Update ready (v1.2.0 → v1.3.0).
2 agent sessions are currently active.
The update will be applied when all sessions complete.
To apply immediately (sessions will checkpoint and pause): umas update --now
To cancel the pending update: umas update --cancel
```

4. On `--now`: all active sessions receive a `SIGTERM`-equivalent signal → they commit a `[umas:checkpoint]` to their worktree and set status to `handoff` → update is applied → sessions are resumed with new binary

5. On default (wait): new binary is activated on next `umas start-all` after all sessions complete

**Alternative flow — update introduces a breaking schema change:**

If the new version requires a database schema migration, the migration runs automatically before the new binary activates. The database is backed up first (`database.db.bak`). If the migration fails, the old binary is restored and the backup is kept intact.

---

### 4.15 Dashboard / CLI Showing Stale State

**Scenario:** The `umas watch` output or dashboard shows an agent as `active` when it has actually crashed, or shows a task as `in_progress` when it completed 10 minutes ago.

**Root cause:** The CLI and dashboard read from `database.db`. If the agent or monitoring layer failed to write its final state update (e.g., crash before the `[umas:done]` commit), the displayed state is stale.

**Detection:** `umas watch` computes a "last-seen delta" — the time since the agent's `last_heartbeat` in the database. If the delta exceeds 2 minutes, it displays a staleness warning inline:

```
Agent: alice   Task: signup-endpoint   Status: active  ⚠ last heartbeat 4m ago
```

**Recovery:**

- Stale `active` sessions are reconciled by the Project Monitor on its next 60-second poll. If the heartbeat gap exceeds the crash threshold (5 minutes), the session is marked `crashed` and the UI updates.
- Manual force-reconcile: `umas agents reconcile` — immediately cross-checks all session statuses against heartbeat timestamps and updates stale records.

**Alternative flow — database read is racing with a write:**

Under SQLite WAL mode, a CLI read can see a snapshot that predates the most recent committed write by one WAL frame. This is a sub-second inconsistency, not a bug. `umas watch` refreshes every 2 seconds, so the maximum visible lag is 2 seconds. No recovery needed.

---

### 4.16 Disk Space Exhaustion

**Scenario:** Agent worktrees, event logs, and session history fill the disk, causing agent commits or log writes to fail.

**Prevention:** The Daemon monitors free disk space on the volume containing `~/.umas/` and `.umas/` every 5 minutes. Alerts fire at:

| Free space remaining | Action |
|---------------------|--------|
| < 2 GB | P2 warning: "Disk space low. Consider running `umas cleanup`." |
| < 500 MB | P1 alert: new agent dispatch is paused |
| < 100 MB | P0: all active agents are checkpointed and paused immediately |

**`umas cleanup` — what it reclaims:**

```bash
umas cleanup --dry-run
# Shows what would be removed:
# → stale worktrees (>7 days):        1.2 GB
# → completed session logs (>90 days): 340 MB
# → cache/:                            180 MB
# → Total recoverable: 1.7 GB

umas cleanup
# Applies the above, prompting for confirmation on stale worktrees with uncommitted changes
```

**What cleanup never removes:**
- Active or `budget_paused` or `provider_failed` worktrees
- `events.jsonl` entries from the last 90 days (audit retention requirement from PRD)
- Decision artifacts (ADRs, PRFAQs, specs) — these live in the repo, not `.umas/`

**Alternative flow — disk fills during an active agent commit:**

If `git commit` inside a worktree fails due to `ENOSPC`:
1. The agent receives a write error on its `[umas:checkpoint]` commit
2. The commit retries once after a 5-second wait (in case a concurrent cleanup freed space)
3. On second failure: the agent appends `{"event":"escalate","severity":"P0","reason":"disk_full — checkpoint failed"}` to `.umas/events.jsonl` automatically
4. The escalation triggers a P0 alert and all dispatch is paused until space is freed

