# budget-meter

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS or on any LLM SDK. Pure accounting plus a file-based ledger.

---

## 1. Purpose

Track token (and optionally cost) consumption against budgets, tell callers when thresholds are crossed, decide whether new work may start, and fit context into a size limit when work is handed to a fresh worker.

## 2. Scope and Non-Goals

**In scope**
- Two budget kinds: **session** (one worker's context or token limit) and **period** (a rolling or calendar window, such as daily per project)
- Reservations (estimate first, true-up later)
- Threshold events with de-duplication
- Admission control: admit or defer new work
- A durable usage ledger shared across processes
- Optional cost computation from a price table
- **Context packing**: fit prioritised sections into a token limit

**Non-goals**
- Counting tokens for text (the caller supplies a counter function; vendor tokenizers differ)
- Calling LLMs or summarising text. Compression by an LLM is the caller's job; the library only *packs* what the caller provides.
- Throttling request rate. See [llm-gateway](../llm-gateway/README.md).
- Killing or pausing workers. The library reports; the caller acts.

## 3. Concepts and Data Model

### 3.1 Budget

```
{ id, kind: "session"|"period", limit, unit: "tokens"|"cost",
  window?: { type: "calendar"|"rolling", tz, reset_at | length },
  thresholds: [0.80, 0.90, 0.95] }
```

A budget has **used** (committed usage) and **reserved** (admitted but not yet committed). `available = limit - used - reserved`.

### 3.2 Ledger

An append-only file of usage entries, one JSON object per line (format per [event-log](../event-log/README.md) conventions, but this library has its own file and no dependency).

```json
{ "v":1, "ts":"...", "budget":"proj-a/day", "op":"commit", "tokens":4120,
  "input_tokens":3000, "output_tokens":1120, "cached_tokens":0,
  "actor":"alice", "ref":"task-7", "model":"model-x", "cost":0.031 }
```

Operations: `reserve`, `commit`, `release`, `adjust` (manual limit change), `reset`. Current state is the fold of the ledger for the active window. A periodic snapshot file speeds startup.

### 3.3 Events

`{ budget, threshold, direction: "crossed_up"|"crossed_down", used, limit, at }`, plus `exhausted` (available = 0) and `window_reset`. A threshold event fires **once per crossing** per window. It re-arms when usage drops below by `hysteresis` (default 2 percentage points), for example after a limit increase.

### 3.4 Decisions

`admit(budget, estimate) -> Admit{reservation} | Defer{reason, retry_after?}`

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `define(budget)` | Register or update a budget. Raising or lowering `limit` is allowed live and takes effect on the next call. |
| `reserve(budget, estimate, actor, ref) -> Reservation` | Admission check plus hold. Fails `Deferred` when `used + reserved + estimate > limit`. |
| `commit(reservation, actual) -> Status` | Replace the hold with actual usage (may exceed the estimate; see 5.2). |
| `release(reservation)` | Drop an unused hold. Reservations also expire by `reservation_ttl`. |
| `record(budget, usage, actor, ref)` | Commit usage with no prior reservation (for example, streaming calls that report at the end). |
| `status(budget) -> { used, reserved, available, percent, thresholds_crossed[], reset_at }` | |
| `subscribe(callback)` | Receive events in-process. Cross-process consumers read the ledger or use `poll_events(cursor)`. |
| `cost(usage, price_table) -> amount` | Compute cost from per-model rates in the supplied table. |
| `pack(sections, limit, counter) -> Packed` | Context packing (section 5.5). |

Also `budget-meter <op> --json`.

### 4.1 CLI output (AXI)

Follows [CLI Conventions (AXI)](./README.md#cli-conventions-axi). `--json` is unchanged and is what orchestrators and the `admit` callback use. The default view matters for `status`.

**Why it fits.** An agent deciding whether to start more work, or how much context to load, needs "how much is left and when does it reset" in a few tokens, not the ledger.

**No-argument view = `status` for every budget** (read-only; folds the snapshot plus ledger tail):

```
bin: budget-meter
description: token and cost budgets with reservations and thresholds
budgets[2]{id,used,available,percent}:
  proj-a/day,812400,187600,81
  proj-b/day,40200,959800,4
crossed: proj-a/day 80%
resets: proj-a/day 2026-10-20T00:00Z (in 13h)
help[1]:
  budget-meter status proj-a/day --fields reserved,thresholds
```

| Rule | Applied here |
|------|--------------|
| Minimal fields | `id`, `used`, `available`, `percent`. `--fields reserved,limit,reset_at,unit` adds more. Units are stated once in the header when all rows share one |
| Aggregates | Percent, the thresholds already crossed, and time to reset are computed, not left for the agent to derive |
| Empty states | `budgets: none defined` with `help: budget-meter define ...`. A budget with no usage in the window shows `used 0`, not nothing |
| Truncation | The ledger is never printed by `status`. `cost` and `pack` print summaries; `pack --full` lists the manifest of kept, truncated and dropped sections |
| Hints | Over a threshold: the live-change command `define --limit` is mentioned only if the caller has set the budget as adjustable. Deferred: the `retry_after` time |

**Decisions are answers, not errors.** `reserve` exits 0 for both outcomes and prints `result: admit` with the `reservation` id, or `result: defer` with `reason` and `retry_after`. A shell caller reads the `result` line, or uses `--json`. Failures of the tool itself (`unknown_budget`, unreadable ledger, `unsupported_version`) exit 1.

**Idempotence.** `release` and `commit` on a reservation already released or committed exit 0 (`already committed`) and change nothing. `define` with an identical budget exits 0 with `unchanged`. `reserve` is not idempotent today: two calls hold twice. A retried launcher could double-hold; see the open point.

**Exit codes.** `0` success, empty, `admit`, or `defer`. `1` a typed error. `2` usage.

**How to use it.**
- **Agent checking headroom:** `budget-meter status` before starting a large task.
- **Orchestrator:** `budget-meter reserve --json ...` inside the `admit` callback; read `result`.
- **Session start (application's choice):** the no-argument view from a hook, so the agent knows when it is near a limit.

**Open point.** Make `reserve` idempotent on `(budget, actor, ref)`: a second call with the same trio returns the existing reservation. This protects against retried launchers and matches AXI's rule for mutations, but it changes section 4 and needs `ref` to be required.


## 5. Behaviour

### 5.1 Threshold semantics

| Level | Default | Meaning to the caller |
|-------|---------|----------------------|
| `warn` | 80% | Alert a human |
| `soft` | 90% (session) | Worker should checkpoint and request handoff |
| `hard` | 95% | Caller should force handoff from the last checkpoint |
| `exhausted` | 100% | New work is deferred; in-flight work is not cut off |

The names are labels on percentages; the percentages are configuration. The library defines no meaning beyond the event.

### 5.2 Reservation and overrun

- `reserve` makes concurrent admission safe: two workers cannot both be admitted against the same remaining headroom.
- Actual usage frequently exceeds the estimate. `commit` always records the **true** amount. `used` may therefore exceed `limit` ("overdraft"). Overdraft is reported (`over_limit`), and further `reserve` calls defer until the window resets or the limit is raised.
- This matches the design rule that in-flight work finishes its current step; the budget never tells a caller to stop.

### 5.3 Windows

- `calendar`: resets at the next local midnight in `tz` (or a configured time of day). `window_reset` is emitted and usage returns to zero in the new window; prior windows stay in the ledger.
- `rolling`: usage within the last `length` counts.
- A `limit` change in the middle of a window applies immediately and re-evaluates thresholds (a raise can emit `crossed_down`). The `Defer` outcome becomes `Admit` on the next `reserve`, so no polling for midnight is needed after a budget raise.

### 5.4 Multi-process safety

- All writers append through an advisory file lock; ledger reads need no lock.
- State is rebuilt from snapshot + tail. Two processes see the same `available` within one `append` latency.
- A process that dies holding a reservation leaves it to expire at `reservation_ttl` (default 15 min).

### 5.5 Context packing

`pack(sections, limit, counter)` fits context into `limit` tokens when handing work to a fresh worker (the "handoff packet").

```
section = { name, content, priority: int, mode: "required"|"truncatable"|"droppable",
            truncate: "head"|"tail"|"summary_hint" }
```

1. Count each section with `counter`.
2. Include all `required` sections. If they exceed `limit`, fail `RequiredTooLarge` (never silently truncate required content).
3. Add remaining sections by descending `priority`. A `truncatable` section that does not fit is cut to the available space (by `truncate`) and marked `truncated: true`; a `droppable` section that does not fit is omitted.
4. Output: ordered sections plus a manifest `{ included[], truncated[], dropped[], tokens }` so the receiving worker is told what is missing.

Pointers (path plus line range) are cheap and should be preferred over inline content by callers; the library treats them like any other section.

### 5.6 Cost

`cost(usage, price_table)` multiplies token classes (input, output, cached) by per-model rates from a table **supplied by the caller**. No prices are embedded, so changing providers or model prices requires no library release. Unknown model -> `cost = null` with a warning, not an error.

## 6. Configuration

```yaml
ledger_dir: .budget
fsync: false
reservation_ttl_seconds: 900
hysteresis_points: 2
snapshot_every_entries: 1000
defaults:
  thresholds: [0.80, 0.90, 0.95]
```

Budgets themselves are defined by the caller through `define` or a budgets file; the library has no knowledge of projects or sessions.

## 7. Failure Modes

| Error | Cause | Behaviour |
|-------|-------|-----------|
| `Deferred` | Not enough headroom | Return reason and `retry_after` (next reset, if calendar) |
| `UnknownBudget` | Not defined | Fail |
| `RequiredTooLarge` | Packing: required sections exceed limit | Fail with sizes per section |
| `LedgerCorrupt` | Unparseable line | Skip the line, warn, continue. `rebuild` command re-folds from the snapshot |
| `LockTimeout` | Writer lock held too long | Fail, retryable |
| `ClockSkew` | Clock moved backwards over a window boundary | Log; never re-open an already reset window |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below; severity is the consumer's policy.

| Error | Suggested recoverability |
|-------|--------------------------|
| `Deferred` | `transient`; `retry_after` supplies the delay |
| `LockTimeout` | `transient` |
| `LedgerCorrupt`, `ClockSkew` | `ambiguous` (the library continues; `rebuild` repairs) |
| `UnknownBudget`, `RequiredTooLarge` | `permanent` |

## 8. Acceptance Criteria

1. 50 concurrent reservations against a budget with room for 10 admit exactly the number that fit.
2. A threshold event fires once per crossing, and again after usage falls below by the hysteresis and rises again.
3. Raising the limit while usage is over the old limit turns the next `reserve` from `Deferred` to `Admit` without waiting for a window reset.
4. Killing a process holding a reservation: its hold expires and headroom returns.
5. `pack` with required sections that fit never drops them; the manifest lists everything truncated or dropped.
6. Ledger replay after deleting the snapshot yields identical status.
7. `budget-meter` with no arguments prints every budget with used, available and percent, and `budgets: none defined` when there are none, exiting 0 in both cases.
8. `reserve` that defers exits 0, prints `result: defer` with a reason, and a script reading `--json` gets the same decision.
9. `commit` of an already committed reservation exits 0 with `already committed` and the ledger gains no line.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| Daily project budget; 80% warn; 100% exhaustion | Period budget with `calendar` window; thresholds `0.80 / 1.0`; the Scheduler calls `reserve` before dispatch |
| Session limit; 90% graceful handoff; 95% emergency | Session budget per worker; `soft` -> the worker commits state and requests handoff; `hard` -> Project Monitor forces handoff |
| `umas project config --budget N` | `define(budget, limit=N)`; takes effect immediately (exception flow 4.6 alt. flow) |
| `budget_paused` session status | Set by UMAS when `reserve` returns `Deferred` |
| Handoff packet, about 15k tokens | `pack(...)` with `required` = task, next steps, last decisions; `truncatable` = notes; pointers for files |
| Token and cost metrics | The ledger is the source for `umas metrics tokens/cost` |
| Typed errors | Mapped to records by UMAS; `Deferred` becomes a `transient` record whose retry delay is `retry_after`. See [error-classifier](../error-classifier/README.md) section 9 |

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.6 and §4.6, `TECHNICAL-DESIGN-SPEC-PART2.md` §4.4 (Rust `Scheduler` token budget) and `TECHNICAL-DESIGN-SPEC-PART3.md` §5.2 (handoff threshold).

| Deviation | Why |
|-----------|-----|
| Budget extracted from the Scheduler | In the source, budget tracking is embedded in a Rust `Scheduler` struct (an in-memory `Mutex<TokenBudget>`), lost on restart and unusable by Python agents. Here it is a shared durable ledger |
| Reservations | The source reserves the estimate and later adds actual usage on top (`record_token_usage`), so usage is double counted. Commit replaces the hold |
| Calendar reset from a configured timezone | The source computes `now + 24h` at construction, which drifts from midnight and resets on restart |
| Live limit changes | Required by exception flow 4.6 (budget raised while paused) |
| Cost via caller-supplied price table | The cost estimates in the build assessment use a single model's prices; prices change |

## 11. Open Questions

1. Should period budgets support **hierarchy** (global -> project -> task) with a single `reserve` checking all ancestors? Likely needed; the cost is moderate.
2. Is the ledger file approach enough for 20-30 concurrent agents, or does the lock become a bottleneck? A SQLite backend behind the same interface is the fallback.
3. Cached-token accounting differs by provider. Treat `cached_tokens` as informational, or count at a discounted rate via the price table only?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Example code illustrating one way to implement this spec. May use consumer-specific names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [libs/README.md](./README.md).

### 12.1 Scheduler with token budget (Rust)

Source: `TECHNICAL-DESIGN-SPEC-PART2.md` §4.4.2

```rust
// Rust implementation for performance
use std::collections::VecDeque;
use std::sync::Arc;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::{Duration, interval};

pub struct Scheduler {
    max_concurrent_agents: usize,
    semaphore: Arc<Semaphore>,
    queue: Arc<Mutex<VecDeque<AgentTask>>>,
    token_budget: Arc<Mutex<TokenBudget>>,
}

#[derive(Debug, Clone)]
pub struct AgentTask {
    pub agent_id: String,
    pub task_id: String,
    pub priority: u8,
    pub estimated_tokens: u64,
}

#[derive(Debug)]
pub struct TokenBudget {
    pub daily_limit: u64,
    pub current_usage: u64,
    pub reset_at: DateTime<Utc>,
}

impl Scheduler {
    pub fn new(max_concurrent_agents: usize, daily_token_limit: u64) -> Self {
        Self {
            max_concurrent_agents,
            semaphore: Arc::new(Semaphore::new(max_concurrent_agents)),
            queue: Arc::new(Mutex::new(VecDeque::new())),
            token_budget: Arc::new(Mutex::new(TokenBudget {
                daily_limit: daily_token_limit,
                current_usage: 0,
                reset_at: Utc::now() + Duration::from_secs(86400),
            })),
        }
    }
    
    pub async fn schedule_agent(
        &self,
        task: AgentTask,
    ) -> Result<(), SchedulerError> {
        // Check token budget
        let mut budget = self.token_budget.lock().await;
        if budget.current_usage + task.estimated_tokens > budget.daily_limit {
            // Queue for later
            let mut queue = self.queue.lock().await;
            queue.push_back(task);
            return Ok(());
        }
        
        // Reserve tokens
        budget.current_usage += task.estimated_tokens;
        drop(budget);
        
        // Acquire semaphore permit
        let permit = self.semaphore.clone().acquire_owned().await?;
        
        // Spawn agent
        tokio::spawn(async move {
            // Execute agent task
            // ...
            
            // Release permit when done
            drop(permit);
        });
        
        Ok(())
    }
    
    pub async fn process_queue(&self) {
        let mut interval = interval(Duration::from_secs(60));
        
        loop {
            interval.tick().await;
            
            // Check if we have capacity
            if self.semaphore.available_permits() == 0 {
                continue;
            }
            
            // Check token budget
            let budget = self.token_budget.lock().await;
            let available_tokens = budget.daily_limit - budget.current_usage;
            drop(budget);
            
            if available_tokens == 0 {
                continue;
            }
            
            // Process queued tasks
            let mut queue = self.queue.lock().await;
            while let Some(task) = queue.pop_front() {
                if task.estimated_tokens <= available_tokens {
                    drop(queue);
                    let _ = self.schedule_agent(task).await;
                    queue = self.queue.lock().await;
                } else {
                    // Put back and wait
                    queue.push_front(task);
                    break;
                }
            }
        }
    }
    
    pub async fn record_token_usage(
        &self,
        agent_id: &str,
        tokens_used: u64,
    ) -> Result<(), SchedulerError> {
        let mut budget = self.token_budget.lock().await;
        budget.current_usage += tokens_used;
        Ok(())
    }
}
```
