# Reusable Components & Technology Stack Review

> **Status:** Discussion draft · **Date:** October 2026
> **Purpose:** Assess how UMAS deliverables break into reusable components, how each can be reused outside UMAS, and whether the technology stack needs review.
> **Source:** Discussion captured from design session.

---

## 1. Reusability Tiers

### Tier A — High standalone value (usable today, outside UMAS)

| Component | Who else uses this? | Reuse form |
|-----------|---------------------|------------|
| **`event-log`** | Any pipeline, CI system, multi-process tool | Ship as a standalone binary (`event-log append`, `event-log tail --cursor`) with `--json`. Zero UMAS concepts. The format (JSONL + schema_version) is already language-neutral. |
| **`budget-meter`** | Any LLM application that tracks token spend | Python package + CLI. Token threshold / handoff-packing logic is useful to anyone building multi-turn agents. Nothing UMAS-specific. |
| **`task-queue`** | Any local job system — CI, build orchestration, batch processing | Go static binary. Dependency graph + lease + retry. Works with no broker. "Poor man's Temporal" with real external value. |
| **`merge-queue`** | Any team repo — no agents required | Go static binary or script. `merge-queue status` / `merge-queue run --verify "pytest"`. Already framed as standalone in §9. |
| **`test-adapters`** | Any agent harness that needs normalised test output | Thin wrapper. Any tool that calls `pytest`/`jest`/`cargo test` and needs to branch on a unified result. |
| **`error-classifier`** | Any multi-component system | Data schema + small library. Shared error vocabulary. Consumers implement their own classification; this provides the *record format* and *retry-advice table*. |
| **`watchdog`** | Any set of long-running local processes | Go/Rust static binary. No UMAS logic. Heartbeat + restart ladder is a general daemon supervisor. |
| **`two-axis-review`** (pack) | Any dev team — PR review, not just agents | Skill file / SKILL.md. Can be loaded in Claude Code, Cursor, Antigravity. Nothing in it is UMAS-specific. |
| **`anti-slop`** (pack) | Any project producing AI-assisted text/code | Skill file. Two-pass review is immediately usable in any repo. |
| **`minimalism-ladder`** (pack) | Any coding agent | Skill file. Fully generic. |
| **`grilling`** (pack) | Any agent that takes requirements | Skill file. Generic bounded questioning. |

---

### Tier B — Reusable with minor parameterisation

| Component | Gap to standalone | Fix |
|-----------|-------------------|-----|
| **`agent-session`** | Lifecycle skeleton is general but defaults reference `STATE.md`, `[umas:checkpoint]` commit prefixes, and `.umas/` paths | Make those configurable defaults, not hardcoded. Already flagged in DNA invariant A7. |
| **`agent-platform`** | Harness adapter registry is fully general; universal SKILL.md format (A10). But config examples use `~/.umas/` paths. | Configurable root path. |
| **`hook-store`** | Git worktree slot abstraction is general, but naming conventions (`agent/`, `.umas/worktrees/`) leak. | Make `branch_prefix` and `worktree_base` configurable. |
| **`playbook-runner`** (pack) | Phase-gated engine is general; built-in playbooks are already generic. | No structural fix needed. Pack needs real `PACK.md` + fixtures before it's shippable. |
| **`specialist-agents`** (pack) | Role prompts are general but the Developer prompt contains UMAS-specific commit signal strings. | Scrub UMAS signal strings from prompt body, move to `{{commit_convention}}` placeholder. |

---

### Tier C — UMAS-internal (not worth extracting as standalone)

| Component | Why it stays internal |
|-----------|-----------------------|
| **`kc-axi`** | Only needed if running a local Keycloak for OIDC — a very UMAS-specific infrastructure choice. |
| **`llm-gateway`** | Spec already recommends adopting an existing package first (LiteLLM, LangChain gateway). Don't build it. |
| **`decision-artifacts`** | Genuinely useful, but narrow audience. Ship last. |
| **`metrics-store`** | JSONL backend is trivial to replicate; SQL backend is a thin table. Most projects won't extract this separately. |
| **`router-heuristic`** (pack) | Routing logic only useful once `specialist-agents` exists. It's a UMAS-level orchestration concern, not a general pack. |
| **`communication-modes`** (pack) | Useful context-saving, but only after an agent system exists. Don't extract early. |

---

## 2. Two Reuse Gaps Not Yet Named

### Gap 1: No shared schema registry

Ten components write JSONL files with `schema_version`. Each spec defines its schema inline. Any project consuming `event-log` + `budget-meter` + `task-queue` together must manually reconcile three independent schemas.

**Fix:** A `schemas/` directory at repo root with canonical JSON Schema files that each spec references — one source of truth, readable by any language.

### Gap 2: Packs have no shippable artifact yet

The pack specs describe `PACK.md`, `schema/*.json`, `fixtures/*.yaml`, `config.yaml`. None of those files exist today — only the design spec (`README.md`) exists. Until `PACK.md` files are authored, no pack is actually reusable outside reading the spec.

**Highest-leverage first packs to ship:** `anti-slop` or `two-axis-review` — both can be loaded immediately into Claude Code or Antigravity as a SKILL.md today.

---

## 3. Technology Stack Review

### 3a. Rust + Python split is correct — but the split line needs sharpening

The current split:
- **Rust** → daemon, CLI, watchdog
- **Python** → agent runtime, llm-gateway, agent-session

This is correct. The concern is the **libraries that sit in between**:
- `task-queue` and `merge-queue` are listed as "any language / Go" in `libs/README.md`
- `hook-store` is "any language"
- `error-classifier` is "any language"

If UMAS is Rust + Python, and these four libs need to be called from *both* layers, the cleanest option is **Go static binaries with a CLI**, so they're language-neutral by process boundary (subprocess call). This already matches what the AXI CLI convention prescribes.

**Recommendation:** Explicitly assign Go to `task-queue`, `merge-queue`, `hook-store`, `error-classifier` as static binaries. Close the "any language" ambiguity.

---

### 3b. OpenTelemetry conflict with DNA invariant

`§1.4` of `TECHNICAL-DESIGN-SPEC.md` specifies `OpenTelemetry 1.20+` with Prometheus metrics and Jaeger tracing as a first-class requirement.

The DNA invariant states:
> *"Observable without a framework. Each library emits plain structured events through a caller-supplied callback. It never requires an OpenTelemetry, Prometheus, or logging dependency."*

**These two are in conflict.** Resolution: OTel/Prometheus/Jaeger is the consuming application's concern (UMAS), not the libraries'. The libs emit via callback; UMAS wires those callbacks to OTel. This is already the stated architecture invariant — it just isn't enforced in `§1.4`.

**Fix:** Update `TECHNICAL-DESIGN-SPEC.md §1.4` to say: "OTel wiring is the UMAS application layer's responsibility. Libraries emit via caller-supplied callback only."

---

### 3c. `llm-gateway` — don't build it

The spec says "adopt an existing package first." Current leading options:

- **LiteLLM** — 100+ provider unified interface, retry, fallback, rate limiting. Python. Maintained. v1.x. Covers everything `llm-gateway` specifies.
- **LangChain** — heavier, but `langchain-core` + `langchain-community` split has improved modularity.

**Recommendation:** Close the `llm-gateway` spec as "adopt LiteLLM." Write a thin adapter that wraps LiteLLM and emits the usage callback expected by `budget-meter`. That adapter is ~50 lines, not a library. This removes one of the most complex libraries from the build backlog.

---

### 3d. SQLite → Postgres migration path is correct but timing is risky

Tying MVP to SQLite with a Phase 3 Postgres upgrade is sensible. The risk is **SQLx migrations** — Rust's `sqlx` compile-time query checking requires a live DB at compile time (unless using offline mode).

Given Python is already used for the agent layer (SQLAlchemy + Alembic already in the stack), consider whether **the database lives entirely in Python** and the Rust daemon calls the REST API rather than touching the DB directly. This removes the SQLx compile-time coupling and keeps the Rust layer purely about process supervision and CLI, not data ownership.

---

## 4. Immediate Action Summary

| # | Action | Rationale |
|---|--------|-----------|
| 1 | Ship `PACK.md` files for `anti-slop` + `two-axis-review` | These are usable TODAY in any agent harness |
| 2 | Add `schemas/` directory at repo root | Shared JSON Schemas for `event-log`, `task-queue`, `budget-meter` |
| 3 | Close `llm-gateway` as "adopt LiteLLM + thin adapter" | Removes the most complex lib from the build backlog |
| 4 | Fix `TECHNICAL-DESIGN-SPEC §1.4` OTel conflict with DNA invariant | OTel wiring belongs in UMAS application layer, not in libs |
| 5 | Explicitly assign Go to `task-queue`, `merge-queue`, `hook-store`, `error-classifier` as static binaries | Closes "any language" ambiguity; makes them language-neutral by process boundary |

---

## 5. Open Decisions

Three decisions to close before anything is built:

1. **Mono-repo vs. separate packages:** Should `libs/` and `packs/` be published separately (own repos/packages) so other teams can depend on them, or do they stay in this mono-repo? This changes whether the "no cross-library import" rule needs package manager enforcement.

2. **`kc-axi` still needed?** If the team can assume OIDC/Keycloak is already running in the environment (IBM Cloud IAM, for example), this library is unnecessary. It was added when a local identity provider was required for dev.

3. **`llm-gateway`: adopt LiteLLM or build?** The spec leaves it open. Closing this decision unblocks `agent-session` and `budget-meter` wiring.
