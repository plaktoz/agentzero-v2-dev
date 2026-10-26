Verdict: REJECTED

# Caller assessment: agent-execution

**Spec:** `umas/modules/agent-execution/agent-execution-spec.md`
**Callers assessed as:** orchestration (dispatch, signals, retry), budget-and-models (Worker limits, usage), verification (re-spawn), monitoring (main 5.5 and watchdog; no module spec exists).
**Gaps:** 6 critical, 10 high, 2 medium.

## Findings

| # | Gap | Sec | Caller needs | Severity |
|---|---|---|---|---|
| 1 | Launcher unspecified (Open 1). No Scheduler-to-launcher interface. Claim owner contradicts: step 1 says Scheduler, section 7 says launcher. | 2, 3, 7 | Signature, result, errors, retry rule, one claim owner. | Critical |
| 2 | `read_signal` is per platform. ap 4 returns "the most recent unread signal for any assignment". Parallel Workers cannot be told apart. Mermaid omits `platform`. | 2, 3 | Per-hook scope, one signature. | Critical |
| 3 | No outcome-to-task-queue mapping. Step 9 reports `crashed`, not in the enum (`done`, `blocked`, `escalated`, `abandoned`). | 2, 3 | Outcome to `complete`, `fail(retry)` or `release`. | Critical |
| 4 | Worker limits unenforceable. A.4.8 promises per-task time and checkpoint limits; budget-meter units are `tokens \| cost` only, and nothing stops a harness. Usage carrier is "Not specified". | 3, 4, 8 | Limit unit, measurer, stopper, usage carrier. | Critical |
| 5 | Gateway bypass uncontrolled. A.5.7 requires "provider-only network"; no mechanism here. Provider and model per Worker are not in WorkAssignment or config (ADR-0002 says per assignment). | 3, 5 | Mechanism, or a recorded accepted risk. | Critical |
| 6 | Watchdog node undefined: `argv`, heartbeat writer, progress marker, restart policy. Watchdog restarts on `unresponsive`; step 9 says launcher reports `crashed`. | 2 | Node config; one owner for restart and crash. | Critical |
| 7 | Pause, handoff and budget-pause for CLI Workers have no owner (Open 5, 6). agent-session does not run in a CLI. | 2, 6 | Owner and carrier. | High |
| 8 | Only `agent:spawn` is an A.5 string. `agent:stop`, `agent:resume` are proposals; Worker and Coordinator rows have none. | 5 | Exact string per row, or "none exists". | High |
| 9 | WorkAssignment `title`, `description`, `relevant_files[]`, `constraints[]` have no source. Nobody owns the 15k compression. | 2, 3 | Source and owner per field. | High |
| 10 | Partial failure undefined. `read_signal` consumes on read, so a crash before `complete` loses the signal. Duplicate launch on retry not covered. Missing errors: `HookNotFound`, `LeaseHeld`, `GitBusy`, `NotOwner`, `PathTraversal`. | 3, 8 | Retry rule per call; outcome per error. | High |
| 11 | Re-spawn after regression (6.11) does not say if it reuses the hook; an old `[umas:done]` could satisfy it. | 2, 6 | New hook or cursor reset. | High |
| 12 | Specialist invocation: no input, carrier, timeout or error return (Open 7). | 2, 3 | Call signature, failure return. | High |
| 13 | Escalate payload allows `P1` only; A.5.5 lets Workers raise P0. | 3 | P0, routed to Operator. | High |
| 14 | Not set: `signal_pattern`, poll interval, `max_concurrent` (30 vs 5), Worker retry count, `agents.worker.model` meaning. CPU and memory limits have no enforcer. | 4 | Values and enforcer. | High |
| 15 | Links to `monitoring`, `interfaces`, `exception-flows` specs point to missing files. | 6 | Monitoring interface, or main-spec links. | High |
| 16 | Proposed claims a caller would build on are not decided: launcher, poll interval, "report through complete", hook per task. | 2 | Decisions, not tags. | High |
| 17 | Mermaid sends done and crash to Scheduler; text sends them to the task queue. Step 1 not drawn. | 2 | Aligned diagram. | Medium |
| 18 | Commit-message completion shown as settled; A.4.8 says untested. ap 3.3 and ap 4 give different `assign` signatures. | 1, 3 | Mark unverified; one signature. | Medium |

Open items that block a caller: 1, 3, 5, 6, 9, 10, 11, 12, 13. Needed before Phase 2: 4, 8, 14.

## Devil's advocate

Cost and observability rest on Workers being bounded and visible. Both fail. The only bound is a time and checkpoint limit that budget-meter cannot express and nothing enforces. The only signal is a git log read by a `read_signal` not scoped to a Worker, matching a prefix the agent must remember from `SKILL.md`. A Worker that forgets it stays silent until the 10-minute nudge; a crash between read and `complete` drops the signal. The first real failure is an unbounded, unattributed, unreported Worker.

## Decisions for the owner

1. **Launcher owner (gaps 1, 6).** (a) agent-execution; (b) orchestration glue. Recommend (a): this spec claims the launch path.
2. **Signal scope (2, 10, 11).** (a) per hook via `hook-store find_signals(pattern, since=cursor)`; (b) `read_signal` with `hook_path` in config. Recommend (a): the cursor stays with the hook.
3. **Worker limits (4, 5).** (a) wall-clock unit in budget-meter, launcher stops the harness; (b) alert only; (c) per-harness sandbox. Recommend (a) now, (c) in Phase 2.
4. **Restart versus crash (6).** (a) watchdog restarts; (b) watchdog escalates, launcher calls `fail(retry)`. Recommend (b): a restart may repeat half-done work.
5. **Commit prefix (Open 3).** Recommend one prefix in `commit_prefixes`, with `signal_pattern` derived from it.
