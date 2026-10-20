# task-queue

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS, on any LLM, or on any other library. Files only; no database, no broker.

---

## 1. Purpose

Hold a set of units of work that depend on each other, say which ones are ready, hand them out to workers under a concurrency limit, and survive crashes. It is a dependency graph plus a ready queue plus leased claims, stored in files.

It does not run the work. A worker process (any language) claims a task, does it, and reports the result.

## 2. Scope and Non-Goals

**In scope**
- Tasks with an opaque JSON payload, a priority, and dependencies on other tasks
- Cycle detection and dangling-dependency detection when a task is added
- Ready-set computation: a task is ready when every dependency is done
- Claims as leases: a claimed task that is not renewed or finished returns to the queue
- A concurrency cap on claimed tasks, and an `admit` callback for any further admission rule
- Retry with a maximum attempt count
- Optional grouping: a parent task completes when all its children are done
- Durable state shared across processes on one machine
- Change events through a caller-supplied callback

**Non-goals**
- Executing work, launching processes, or supervising them. See [watchdog](../watchdog/README.md) for supervision. The library only records who claimed what.
- Deciding how many workers the budget allows. The caller passes that rule as an `admit` callback (for example, one that asks [budget-meter](../budget-meter/README.md)). The library never imports it.
- Routing. A task does not say which kind of worker should take it unless the caller puts a `tags` list in the claim filter.
- Scheduling across machines, delayed or cron jobs, or exactly-once execution.
- Message transport. This is a work graph, not a pub/sub bus. See the note on brokers in section 9.

## 3. Concepts and Data Model

### 3.1 Task

```
{ schema_version, id, payload{}, tags[], priority,
  depends_on[], parent?,
  state, attempts, max_attempts,
  claim?: { owner, claimed_at, lease_expires },
  result?{}, error?{}, created_at, updated_at }
```

- `id` is a ULID unless the caller supplies one.
- `payload` is opaque. The library never reads it.
- `priority` is an integer, higher first. Ties break by `created_at`, oldest first.
- `tags` are free strings the caller can filter claims on.

### 3.2 States

```
blocked --(all deps done)--> ready --(claim)--> claimed --(complete)--> done
                               ^                    |
                               |                    +--(fail, attempts left)--> ready
                               +--(lease expired)---+
                                                    +--(fail, no attempts left)--> failed
any non-terminal --(cancel)--> cancelled
```

Terminal states: `done`, `failed`, `cancelled`.

### 3.3 Dependency failure policy

Set per queue, and overridable per task:

| `on_dep_failed` | Effect on a dependent of a `failed` or `cancelled` task |
|-----------------|----------------------------------------------------------|
| `hold` (default) | The dependent stays `blocked`, and shows `blocked_by_failed` in `get`. A person or caller decides. |
| `cancel` | The dependent becomes `cancelled`, and so on down the graph. |
| `ignore` | The failed dependency counts as satisfied. |

### 3.4 Groups

A task with `parent` set is a child. When every child of a parent is `done`, the parent becomes `done` with no worker involved. If any child ends `failed` or `cancelled`, the parent follows `on_dep_failed`. A parent with no children behaves as an ordinary task.

### 3.5 Storage

Event log plus snapshot, behind a storage interface.

| File | Content |
|------|---------|
| `tasks.jsonl` | Append-only. One JSON line per change: `added`, `claimed`, `renewed`, `released`, `completed`, `failed`, `cancelled`, `lease_expired`. Each line carries `schema_version` and a sequence number. |
| `snapshot.json` | The materialised state at a sequence number. Written atomically (temp, fsync, rename). A rebuildable cache: it can always be rebuilt by replaying the log. |
| `tasks.lock` | Advisory file lock held for the short critical section of each write. |

Every operation that changes state takes the lock, reads any log lines past the snapshot, validates, appends one line, fsyncs, and releases. Readers do not need the lock for `get` and `list`; they read the snapshot and replay the tail.

**Compaction.** When the log passes a size or line count, the library writes a new snapshot and rotates the log. Old segments are kept for `retain_segments` and then removed. Terminal tasks older than `retain_done_days` are dropped from the snapshot, never from retained segments.

**Storage interface.** The queue logic talks to `append(event)`, `read_since(seq)`, `load_snapshot()`, `save_snapshot()` and `lock()`. The file implementation is the default. A second implementation backed by a relational table MAY be added for deployments that already run one, in the same way as [metrics-store](../metrics-store/README.md). It is never required (independence rule 3).

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `add(task) -> Task` | Validates the dependency list against existing tasks. Rejects cycles and unknown dependencies. Starts `blocked` or `ready`. |
| `add_batch([task]) -> [Task]` | Atomic: all added or none. Dependencies may refer to tasks inside the batch. |
| `claim(owner, lease_seconds, filter?) -> Task or none` | Picks the best ready task that matches the filter, if the concurrency cap and `admit` allow it. |
| `renew(id, owner, lease_seconds)` | Extends the lease. Fails if the caller no longer owns the claim. |
| `complete(id, owner, result?)` | Marks `done`, unblocks dependents, and completes any parent that is now finished. |
| `fail(id, owner, error, retry: bool)` | With `retry` and attempts left, the task returns to `ready`. Otherwise it becomes `failed`. |
| `release(id, owner)` | Returns a claimed task to `ready` without counting an attempt. |
| `cancel(id, cascade?)` | Cancels a task, and optionally everything that depends on it. |
| `get(id)` / `list(filter)` | Read state. Filters: state, tag, parent, owner. |
| `ready()` / `blocked()` | The two queues, in claim order. |
| `graph(id?)` | The dependency edges, for display. |
| `reap() -> [id]` | Returns expired claims to `ready`. Also done at the start of every `claim`. |
| `compact()` | Snapshot and rotate. |
| `verify() -> Report` | Replays the log, compares with the snapshot, and checks for cycles and orphans. |
| `on_event(callback)` | Receive `added`, `ready`, `claimed`, `completed`, `failed`, `lease_expired`, `deferred`, `cancelled`. |
| `set_admit(fn)` | `fn(task, context) -> admit \| defer(reason)`. Called inside `claim`, after the cap is checked. |

Also `task-queue <command> --json` for every operation above, so a worker in any language can use it by subprocess.

### 4.1 CLI output (AXI)

Follows [CLI Conventions (AXI)](./README.md#cli-conventions-axi). `--json` is unchanged and remains the contract for workers and launchers.

**Why it fits.** A coordinating agent asks "what is ready, what is stuck, what is running" many times a session. The queue can hold hundreds of tasks, almost all `done`.

**No-argument view** (content first; read-only, takes no lock, replays the tail only):

```
bin: task-queue
description: dependency-aware work queue with leased claims
queue: 7 ready, 12 blocked, 5 claimed (max 5), 311 done, 2 failed
ready[3 of 7]{id,priority,tags}:
  01JC4A,10,"coding"
  01JC4B,10,"coding"
  01JC4C,5,"review"
claimed[5]{id,owner,lease_left_s}:
  01JC31,w-alice,212
  ...
failed[2]{id,attempts,error}:
  01JB90,2,"build_error"
  ...
help[2]:
  task-queue get 01JB90          # why it failed
  task-queue list --state blocked
```

| Rule | Applied here |
|------|--------------|
| Minimal fields | Task rows show `id`, `state` or `priority`, and `tags` or `owner`. `payload` is opaque and large, so it is **only** shown with `--fields payload`, and then truncated |
| Aggregate | The `queue:` line counts every state. `ready[3 of 7]` gives shown and total |
| Empty states | `ready: none (12 blocked, 5 claimed at the cap of 5)` says why nothing is ready. `blocked: none` and `failed: none` are printed, not omitted |
| Why blocked | `get` on a blocked task lists the dependencies still open and any `blocked_by_failed`, so the agent need not walk the graph |
| Hints | After a truncated list: how to see the rest. After `failed`: `get <id>`. After a claim: the `complete` and `fail` commands with the id and owner filled in |

**Mutations are idempotent.** `complete`, `cancel` and `release` on a task already in that state by the same owner exit 0 and print `already done`. `complete` or `renew` from a worker that no longer owns the claim is refused with `not_owner` and exit 1 (this is a real failure: the worker must stop). `add_batch` with identical content to an earlier batch is not detected; see open point below.

**Claim is an answer, not an error.** `task-queue claim` exits 0 whether or not it got a task. Output is either the task or `claimed: none` with the reason (`none_ready`, `at_capacity`, `deferred: <reason>`). This keeps a polling worker's loop free of exit-code special cases.

**Exit codes.** `0` success, no-op, empty, or `claimed: none`. `1` a typed error (`cycle`, `unknown_dependency`, `not_owner`, `lock_timeout`, `log_gap`, `unsupported_version`), named in the output. `2` usage.

**How to use it.**
- **Coordinating agent:** run `task-queue` with no arguments to see the state; `task-queue get <id>` to look into a task.
- **Worker (any language):** `claim --json`, do the work, `complete --json` or `fail --json`. Never parse the default view.
- **Session start (application's choice):** run the no-argument view from a session hook so the agent starts with the queue state.

**Open point.** Should `add` with a caller-supplied `id` that already exists with identical content be a no-op (`already added`, exit 0) and with different content an error? That would make `add` idempotent for retried launchers. It needs a new typed error (`id_conflict`).


## 5. Behaviour

### 5.1 Claim

1. Take the lock. Reap expired leases.
2. If the number of `claimed` tasks is at `max_claimed`, return none and emit `deferred` with reason `at_capacity`.
3. Walk the ready set in order (priority, then age), skipping tasks that do not match the filter.
4. Call `admit` on the first candidate. On `defer`, emit `deferred` with the reason and try the next candidate, up to `admit_scan_limit` (default 10), then return none.
5. Record the claim with `lease_expires = now + lease_seconds`, increment `attempts`, append, and return the task.

Capacity is therefore enforced under the same lock that records the claim, so two workers cannot both take the last slot.

### 5.2 Leases and crashes

A worker that dies stops renewing. When `lease_expires` passes, the next `reap` returns the task to `ready` and emits `lease_expired`. The attempt it used still counts. If `attempts` has reached `max_attempts`, the task becomes `failed` instead.

This gives **at-least-once** execution. A task can run twice if a worker finishes after its lease expired and another worker re-claimed it. The first worker's `complete` then fails with `not_owner`. Workers SHOULD make their work idempotent, or check ownership before committing side effects.

### 5.3 Completion and unblocking

`complete` appends one line, then in the same critical section: marks the task `done`, moves every dependent whose dependencies are now all `done` to `ready`, and completes any finished parent, repeating up the chain. Each change emits its own event. The caller learns of newly ready tasks from `ready` events and does not need to poll.

### 5.4 Cycles

`add` walks the dependency list of the new task through existing tasks. If it reaches the new task's own `id`, the add is rejected with `cycle`, naming the path. A batch is checked as a whole.

### 5.5 Determinism

Replaying `tasks.jsonl` from an empty state always produces the same snapshot. All time-dependent decisions (lease expiry) are recorded as events at the moment they are made, so replay does not depend on the clock.

## 6. Configuration

```yaml
dir: ".queue"
max_claimed: 5
default_lease_seconds: 300
default_max_attempts: 2
on_dep_failed: hold            # hold | cancel | ignore
admit_scan_limit: 10
compaction: { max_lines: 10000, retain_segments: 3, retain_done_days: 30 }
fsync: always                  # always | batch
```

## 7. Failure Modes

| Condition | Behaviour |
|-----------|-----------|
| Process killed mid-append | The last log line may be partial. It is ignored and truncated on the next write. A line is complete only if it ends in a newline and parses. |
| Snapshot missing or corrupt | Rebuilt from the log. `verify` reports it. |
| Log segment missing | Rebuild from the snapshot plus later segments. If the gap lies after the snapshot, refuse to continue and report `log_gap`. |
| Lock held by a dead process | The OS releases an advisory file lock on process exit. A stale lock file is not an error. |
| Lock wait exceeds `lock_timeout` | Return `lock_timeout`. No state change. |
| Unknown `schema_version` | Read N and N-1. A newer version is refused with `unsupported_version`. |
| Claim by a non-owner (`complete`, `renew`, `fail`) | Refused with `not_owner`. |
| `admit` throws | Treated as `defer` with reason `admit_error`, and an event is emitted. The queue does not stop. |
| Clock jump | Lease expiry uses wall clock, so a forward jump can expire leases early. Mitigated by the attempt limit and by workers renewing at one third of the lease. |
| Network file system | Not supported. Advisory locks and rename atomicity are not guaranteed there. `verify` warns if it detects one. |

### Error records

This library keeps its own typed errors. A consumer that wants one error vocabulary can express them as [error-classifier](../error-classifier/README.md) records (a data format, not a dependency). Suggested `recoverability`:

| Error | Suggested recoverability |
|-------|--------------------------|
| `lock_timeout` | `transient` |
| `not_owner` | `permanent` for that call; the worker should stop work on the task |
| `cycle`, `unknown_dependency` | `permanent` until the input is changed |
| `log_gap`, `unsupported_version` | `permanent`; a person must act |
| `lease_expired` (event) | `transient` while attempts remain |

## 8. Acceptance Criteria

1. Adding a task that would create a cycle is rejected, and the error names the cycle path.
2. A task becomes `ready` when its last dependency completes, and not before.
3. With `max_claimed = N`, concurrent `claim` calls from many processes never produce more than N claimed tasks.
4. `kill -9` of a worker holding a claim returns the task to `ready` within `lease_seconds` plus one `claim` or `reap`.
5. A task whose attempts run out ends `failed`, and its dependents follow `on_dep_failed`.
6. `kill -9` of the process in the middle of an append loses at most that one uncommitted change, and the next operation succeeds.
7. Deleting `snapshot.json` and running `verify` rebuilds an identical snapshot.
8. A parent completes when its last child completes, with no `complete` call on the parent.
9. A deferred task (by `admit` or the cap) keeps its place in the queue order.
10. `complete` from a worker that no longer owns the claim is refused and changes nothing.
11. The whole CLI works with `--json` and exits non-zero on typed errors.
12. `task-queue` with no arguments prints the per-state counts and the first ready tasks, takes no lock, and exits 0, including on an empty queue (`queue: empty`).
13. `claim` with nothing ready, at the cap, or deferred exits 0 and says which; a polling loop needs no exit-code handling.
14. `complete` twice by the same owner exits 0 with `already done` and changes nothing; by a different worker it exits 1 with `not_owner`.
15. A task with a 50 KB payload does not print it by default; `--fields payload` prints it cut at 200 characters, and `--full` prints it whole.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS need | Mapping |
|-----------|---------|
| Scheduler `ready_queue` | `ready()` |
| "Dispatches agents up to the concurrency limit" | `max_claimed`, plus an `admit` callback that asks [budget-meter](../budget-meter/README.md) whether the period budget allows another Worker |
| `unblock_dependents`, `mark_complete` | Inside `complete` (section 5.3) |
| `check_parent_auto_complete` | Groups (section 3.4) |
| Task blocked by a task that is already `completed` (self-healing at runtime) | Covered: readiness is computed from dependency state when a task is added and after each completion |
| Worker crash, task returns to the queue | Lease expiry (section 5.2). UMAS also asks [watchdog](../watchdog/README.md) to restart the process; the two are independent |
| Task payload | UMAS puts the task type, hook path, and context reference in `payload`. The library does not read it |
| Worker kind (coding, review) | `tags`, matched by the claim `filter` |
| Launching the harness CLI after a claim | Not this library. UMAS's launcher claims a task, starts the harness as a [watchdog](../watchdog/README.md) node, and calls `complete` or `fail` from the commit-message signal. See [modularisation-assessment.md](../modularisation-assessment.md) section 4.8 |

**What stays in UMAS.** The dispatch loop that connects `ready` events to the launcher, the routing that sets `tags`, the creation of a hook for each task, and the `admit` rule. That is glue, a few hundred lines, and it is not a library.

**Brokers.** A message broker (RabbitMQ) could carry `ready` events to remote workers in Phase 3 or 4. It would sit behind the transport interface and would not replace this library: a broker has no dependency graph and no cap enforcement across the whole set. The queue file stays the source of truth.

## 10. Source Material and Deviations

Extracted from `TECHNICAL-DESIGN-SPEC.md` section 5.2 (Scheduler: `ready_queue`, concurrency limit, `on_task_complete`) and the self-healing note on already-completed blocking tasks.

| Deviation | Why |
|-----------|-----|
| Leases and retry | The source has no rule for a worker that dies holding a task |
| Cycle detection | The source assumes a valid graph |
| Persistent file store | The source does not say where the queue lives; a restart would lose it |
| Concurrency cap enforced under the claim lock | The source dispatches "up to the limit" without saying how concurrent dispatchers are kept honest |
| Dependency failure policy | The source does not say what happens to dependents of a failed task |
| Admission as a callback | Keeps budget accounting in [budget-meter](../budget-meter/README.md) with no import between the two |

### Adopt or build

Reusability is real, but so are existing tools. Candidates to evaluate before building (not yet checked, since web search was unavailable when this was written): Taskwarrior (dependencies, local files, no leases), `make`/`ninja`-style graph runners (no persistent claims), Celery, RQ and Sidekiq-style queues (need a broker or database, no dependency graph by default), Temporal and Airflow (full workflow engines, heavy), and agent-oriented task trackers with dependency support. Criteria: files only, no server, dependency graph, leases with a concurrency cap, a CLI, and an embeddable Go package. If one fits, adopt it behind this spec's interface and drop the build. The spec is small enough (about 1,000 lines of Go) that building is a reasonable fallback.

## 11. Open Questions

1. Is `at-least-once` acceptable for coding Workers, or does the launcher need a stronger guard (for example, checking that the hook's worktree is not already in use)? [hook-store](../hook-store/README.md) leases may already cover it.
2. Should `claim` support a `wait` mode that blocks until a task is ready, or is polling plus the `ready` event enough?
3. Windows: advisory locking differs. In scope for the first release?
4. Do tasks need a `not_before` time (delayed start) for retries with backoff, or does the caller handle that?
5. Is `retain_done_days` pruning wanted, or should history live only in [event-log](../event-log/README.md)?
