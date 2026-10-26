Verdict: REJECTED

# Caller assessment: monitoring (2026-10-25)

**Spec:** `umas/modules/monitoring/monitoring-spec.md`
**Callers assessed as:** orchestration (reads `escalate`, registers Worker nodes), agent-execution (receives nudge, stop, `.pause`), budget-and-models (forced handoff, resume), exception-flows (6.2, 6.6, 6.15 to 6.17), interfaces (`umas` CLI, `start-all`).

## Findings

| # | Gap | Section | What the caller needs | Severity |
|---|-----|---------|-----------------------|----------|
| 1 | No Worker liveness signal. A.4.8 makes Workers external CLIs that write no heartbeat. Open 1 is undecided; context-persistence Open 9 adds a third signal (hook-store lease) | 2, 3, 9 | Signal, writer, path, interval | Critical |
| 2 | No node registration. Orchestration says the launcher "registers a watchdog node per Worker (proposed)"; watchdog has only `load(config)` | 3 | Add and remove calls; node config; ladder | Critical |
| 3 | Forced handoff has no carrier: no row says what the Monitor sends (`.stop`, `handoff_request`, successor spawn) or who acts | 3, 6 | Carrier, payload, receiver, spawn owner | Critical |
| 4 | Three recoveries for one dead Worker: lease expiry requeues (orchestration, Worker crash), watchdog restarts, Monitor hands off. No arbiter | 2, 8 | One recovery owner and order | Critical |
| 5 | `escalate` carries `severity` and `reason` only. No task or bundle id, so the Coordinator cannot move the bundle to `ESCALATED`. No condition codes or dedupe key | 3 | `scope`, `data` keys, codes, idempotency key | High |
| 6 | Severity routing incomplete (Open 5, 6, 17). P0 goes to the Operator, a Phase 3 role (A.5.8); no P0 receiver in Phases 1 and 2 | 4, 5, 8 | Condition, severity, receiver per phase | High |
| 7 | Step 7 says "each heuristic maps to one recovery action" but the text gives a sequence. Watchdog 5.3 never kills a pid it did not start, so "graceful handoff" of a crashed Worker has no action | 2, 8 | Ladder per condition, waits (Open 7) | High |
| 8 | 95 percent trigger has no rule for CLI Workers. A.4.8: Workers get "per-task time and checkpoint limits" only. Owner contested (context-persistence Open 13) | 2, 4 | Worker rule; one owner | High |
| 9 | Authority conflict. Section 8 (from 6.2) marks sessions `crashed` and bundles `failed`; A.5.5 gives Monitors read on tasks and bundles. Section 1 says "does not dispatch work"; 6.6 has the Monitor resume dispatch | 1, 5, 8 | Who writes, under which permission | High |
| 10 | No `resource:action` name for any section 5 row (Open 11) | 5 | Names in A.5.4 and A.5.6 | High |
| 11 | `not set` parameters: `miss_threshold`, `max_restarts`, `window`, `kill_grace`, rung waits, Worker heartbeat interval and misses, Patrol and Triage poll, disk check interval. The 10 and 5 minute thresholds are "Snapshot, fixed" with no config key | 4 | Default and key for each | High |
| 12 | Interfaces undefined: CLI output "Not defined"; `interfaces-spec.md` is linked but missing; no dashboard endpoint, status file or JSON-RPC (Open 14, 20, 21); `NodeStatus` fields are [P] | 3, AXI | Payloads, exit codes, errors | High |
| 13 | `daemon.pid`: path B exits with `status: paused`, but 6.13 says a second start "detects the existing PID and exits". The check must test liveness. No schema | 3, 8 | Liveness rule; schema | High |
| 14 | Paused nodes: who deletes `.pause` and `PAUSE.md`, and how `auth_expired` nodes avoid the ladder after `startup_grace`, are not stated | 2, 8 | Delete owners; node rule | Medium |
| 15 | Topology: Monitors as processes or in-process; spawn owner; Patrol health rule from `merge-queue status()` | 2, 3 | Topology, spawn owner, health rule | Medium |
| 16 | No outcome if `llm-gateway` fails in the Triage `callback` rung, or `append(escalate)` hits `DiskFull` | 8 | Default return; fallback | Medium |
| 17 | Event name: `escalate` here, `session_escalated` in agent-session (context-persistence Open 4) | 3, 9 | One name | Medium |
| 18 | Mermaid omits steps 8, 9, the `.pause` write and boot steps 4 and 5; heuristics drawn as parallel | 2 | Figure matching the text | Low |

**Tally:** 4 Critical, 9 High, 4 Medium, 1 Low (18 gaps).

**Open items a caller cannot start without:** 1, 2, 3, 4, 5, 7, 8, 9, 11, 15, 16, 17, 20, 21.

## Devil's-advocate case

Under A.4.8, Workers are external CLI harnesses. They write no heartbeat, read no `.nudge`, `.stop` or `.pause`, and report no live token use. Only commit age is observable without harness cooperation. Three mechanisms then recover one dead Worker with no arbiter (lease requeue, watchdog restart, Monitor handoff), which can run two agents on one task or none. The Tier 3 glue is "Not done" (A.2.4), so the spec restates the snapshot rather than defining a contract.

## Decisions the owner must make

1. **Worker liveness.** (a) Commit age only. (b) The launcher writes a heartbeat file; `git_commit_time` measures progress. (c) The hook-store lease. *Recommend (b).*
2. **Recovery arbiter.** (a) Scheduler. (b) Monitor. (c) Watchdog. *Recommend (a):* the Monitor detects and emits, the watchdog stops the process, only the Scheduler starts a successor.
3. **95 percent trigger.** (a) The session, at its own threshold. (b) The Monitor. *Recommend (a)* where usage is visible; for CLI Workers use the A.4.8 time and checkpoint limits, with `request_graceful` plus a `handoff_request` event.
4. **Severity table.** *Recommend:* Triage or Patrol crash loop is P0; exhausted Worker ladder is P1 to the Coordinator (A.5.4); P0 goes to the Admin in Phases 1 and 2, the Operator from Phase 3.
5. **Write authority.** (a) Monitors get write permissions. (b) The Coordinator acts on `escalate`. *Recommend (b)*, keeping A.5.5 read-only. Add `agent:nudge`, `agent:stop`, `agent:restart`.
6. **Defaults.** *Recommend:* Triage heartbeat 180 s, `miss_threshold: 2`; 5 restarts in 600 s; `kill_grace` 10 s; Worker heartbeat 60 s × 5; 60 s per rung; run folder `.umas/run/`.
