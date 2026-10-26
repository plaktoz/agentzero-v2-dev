# merge-queue

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS or on agents. Needs git and a verify command.

---

## 1. Purpose

A local merge queue. It takes branches that are ready, merges them together on a temporary branch, runs one verification command, and advances the target branch only to a tree that has passed. When verification fails it finds the offending branch with a binary search and merges the rest.

## 2. Scope and Non-Goals

**In scope**
- A permanent queue worktree and temporary per-batch branches
- Batching, conflict handling, prefix-bisect, retry bookkeeping
- Compare-and-swap advance of the target branch
- Crash recovery from persisted queue state

**Non-goals**
- Writing or fixing application code. The queue only merges and reports.
- Running tests itself. It runs a caller-supplied verify command (which may use [test-adapters](../test-adapters/README.md)).
- Talking to GitHub, GitLab, or other PR platforms. A thin adapter may feed `submit` calls; that is outside this spec.
- Review or approval policy. A candidate is submitted only when the caller considers it ready.

## 3. Concepts and Data Model

### 3.1 Candidate

```
{ id, ref, base_hint?, meta{}, attempts, submitted_at }
```

`ref` is a branch name or commit SHA. `meta` is opaque to the queue and returned in reports.

### 3.2 Queue state machine

```
IDLE        no pending candidates; queue worktree on a clean baseline
COLLECTING  accumulating candidates until batch_size or batch_timeout
TESTING     temp branch built, verify running
BISECTING   verify failed, searching for the culprit
MERGING     verification passed, advancing the target
```

### 3.3 Candidate outcomes

| Outcome | Meaning |
|---------|---------|
| `merged` | Included in a tree that passed verification; the target advanced to it |
| `blocked` | Removed from the queue with a `reason` (below) |
| `pending` | Still waiting (not yet batched, or re-queued after a batch restart) |

Block reasons: `conflict` (cannot merge cleanly onto the batch so far), `test_failure` (fails verification against baseline plus predecessors in the batch), `baseline_red` (the target itself fails verification), `timeout` (verify exceeded its limit), `max_attempts` (retry limit reached).

### 3.4 Persisted state

`<queue_dir>/queue.json`, written atomically after every state transition:

```json
{ "schema_version": 1, "state": "TESTING", "target": "main", "base_sha": "ab12...",
  "temp_branch": "mq/tmp-7f3a", "batch": ["pr-4","pr-5"], "queue": [...],
  "attempts": { "pr-4": 1 }, "updated_at": "..." }
```

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `init(repo, target, queue_dir) -> ()` | Create the permanent queue worktree once. Idempotent. |
| `submit(candidate) -> Position` | Add to the queue. Duplicate `id` is rejected. |
| `cancel(id)` | Remove a pending candidate. |
| `run_once() -> BatchReport` | Process one batch end to end (blocking). The caller schedules this: from a loop, a timer, or a hook. |
| `status() -> { state, pending[], last_report }` | Read-only. |
| `requeue(id)` | Return a `blocked` candidate to `pending` (resets nothing except status; attempts are kept). |
| `recover()` | Section 5.6. Called automatically by `init` and `run_once`. |

A `BatchReport` lists, per candidate, the outcome, reason, verify log reference, and which verify runs happened. Also exposed as `merge-queue <op> --json`.

### 4.1 CLI output (AXI)

Follows [CLI Conventions (AXI)](../README.md#cli-conventions-axi). `--json` is unchanged. The default view matters mainly for `status`, `submit` and the result of `run_once`.

**Why it fits.** Agents submit work and then ask "where is my change". A `BatchReport` for a ten-candidate batch with a bisection is long, and the asker usually needs one row.

**No-argument view = `status`** (read-only, no lock):

```
bin: merge-queue
description: serialises merges to a target branch behind a verify command
state: TESTING (target main, base ab12cd3, batch of 2)
pending[3]{id,position,attempts}:
  pr-6,1,0
  pr-7,2,0
  pr-8,3,0
last_batch: 4 merged, 1 blocked (pr-3: test_failure)
help[1]:
  merge-queue report pr-3   # verify log reference and bisect steps
```

| Rule | Applied here |
|------|--------------|
| Minimal fields | A candidate shows `id`, `outcome` or `position`, and `reason`. `meta` is opaque and only shown with `--fields meta` |
| Aggregates | The state line, the batch size, and `last_batch` counts of merged and blocked |
| Empty states | `pending: none (state IDLE, last batch merged 3 at 10:20)`; `blocked: none`. An empty queue says it is idle and when it last ran |
| Truncation | Verify logs are never inlined. A `blocked` row gives the log path; `--full` prints the last 40 lines of it |
| Hints | A `blocked` candidate: the reason in words, the log path, and `merge-queue requeue <id>` when the reason is retryable (`timeout`, `max_attempts` excluded) |

**Idempotence.** `cancel` of a candidate already removed exits 0 (`already removed`). `requeue` of an already pending candidate exits 0. `submit` with an existing `id` is **rejected** by section 4 today; the AXI-conformant form is that `submit` of the same `id` and the same `ref` is a no-op (`already queued, position 2`, exit 0) and a different `ref` is an error. See the open point below.

**`run_once`.** A batch that finishes is a success even when some candidates were blocked: exit 0, and the output lists the blocked ones with reasons. Exit 1 only when the run itself could not finish: a git error, or `baseline_red` (the queue halts and a person must act). Callers that must know about blocked candidates read the report, not the exit code.

**Exit codes.** `0` success, no-op, or empty. `1` a typed error or `baseline_red`. `2` usage.

**How to use it.**
- **Agent that submitted a change:** `merge-queue status` until its candidate is `merged` or `blocked`; then act on the reason.
- **Scheduler / hook:** `merge-queue run_once --json`.
- **Do not** parse the default view; the state names and reasons in `--json` are the contract.

**Open point.** Changing `submit` for duplicate ids from reject to idempotent alters the current interface in section 4. It is listed for the follow-up review rather than changed here.


## 5. Behaviour

### 5.1 Verify command

A command line run in the queue worktree with the temp branch checked out. Exit code 0 = pass. Anything else = fail. It is bounded by `verify_timeout`. Its stdout/stderr are captured to a log file (size-capped) and referenced in reports. It must be deterministic enough to be bisected (see 5.5).

### 5.2 Batch run

```
1. Wait until batch_size pending OR batch_timeout elapsed since the first pending.
2. base = current SHA of target. Persist.
3. Verify baseline on a temp branch = base  (skipped if verified within baseline_ttl)
     red -> state IDLE; every pending candidate stays pending; report baseline_red. Stop.
4. Create temp branch from base. For each candidate in order:
     merge --no-ff; on conflict -> abort that merge, block(conflict), continue with the rest.
5. Run verify on the temp branch.
     green -> go to 5.4.
     red   -> go to 5.3.
```

### 5.3 Prefix-bisect

Candidates are merged in a fixed order `c1..cn`. The tree "baseline + c1..ck" is the **prefix k**. Baseline is green (step 3 of 5.2), prefix n is red. Failure is assumed monotone: if prefix k is red, every longer prefix is red.

```
lo = 0 (known green), hi = n (known red)
while hi - lo > 1:
    mid = (lo + hi) / 2
    build temp branch with c1..c_mid; run verify
    if green: lo = mid  else hi = mid
culprit = c_hi
```

- `ceil(log2 n)` verify runs, versus the 2n-1 of testing both halves of every split.
- This finds a culprit whose failure appears **only in combination** with earlier candidates (an interaction failure), which testing each half separately would miss when both halves pass alone.
- The culprit is blocked: `test_failure` (or `timeout`). Its `attempts` is incremented.
- The remaining candidates (all others, in original order) form a new batch and go back to step 2 with the same base. The loop ends when a batch is green or empty.
- Reports note whether the culprit was alone or combination-dependent: the culprit is re-verified on its own against the baseline when `classify_culprit: true`, and tagged `fails_alone` or `fails_in_combination`.

**Non-deterministic verify:** with `rerun_on_fail: 1`, a red result is re-run once before being believed. If the re-run is green the batch is treated as green, and a `flaky_suspected` flag with the log is attached to the report. A candidate that fails the rerun too is a real failure.

**All candidates fail:** each is found and blocked in turn; the final report has every candidate `blocked(test_failure)` with `fails_alone` where classified. The caller should retry them with failure context until `max_attempts` (default 3), after which the reason is `max_attempts`.

### 5.4 Advancing the target

1. Re-read the target SHA. If it differs from `base` the target moved while verifying (someone pushed). The batch is **discarded without merging** and restarted from step 2 on the new base. Nothing unverified ever lands.
2. Otherwise advance with compare-and-swap: `git update-ref refs/heads/<target> <temp_tip> <base>`. If this fails, treat as "target moved".
3. Optionally run `publish_command` (for example `git push origin <target>`). A publish failure does not undo the local advance; it is reported as `publish_failed`.
4. Delete the temp branch. State returns to IDLE.

### 5.5 Assumptions made explicit

- Candidate order is the submission order unless `order: files_overlap_last` (merges candidates with fewer file overlaps first, to reduce conflict-driven blocks).
- Verify must give the same answer for the same tree. If it does not, bisect results are unreliable. `rerun_on_fail` bounds the damage, and flaky suspects are reported.

### 5.6 Crash recovery

On start, read `queue.json`:
- Delete any temp branches whose name starts with `temp_prefix`.
- If state was `MERGING`, check whether the target already equals the batch tip: if yes, mark the batch `merged`; if no, restart the batch.
- Any other state: restart the batch from COLLECTING.
No candidate is ever lost, and no tree is merged unless it was verified on the same base.

### 5.7 Permanent queue worktree

`init` creates the worktree at `queue_dir` once, on a detached baseline. Only temp branches are created and removed per batch. The worktree is not an agent workspace and is never checked out to the target branch (git forbids the same branch in two worktrees; the target advances by `update-ref`).

## 6. Configuration

```yaml
target: main
queue_dir: .merge-queue
temp_prefix: mq/tmp-
verify:
  command: "make test"
  timeout_seconds: 1800
  rerun_on_fail: 0
baseline_ttl_seconds: 300
batch_size: 10
batch_timeout_seconds: 300
order: submission               # submission | files_overlap_last
max_attempts: 3
classify_culprit: false
publish_command: null
log_dir: .merge-queue/logs
```

## 7. Failure Modes

| Error / event | Cause | Behaviour |
|---------------|-------|-----------|
| `baseline_red` | Target fails verification before any candidate is merged | Queue halts; candidates stay pending; operator must fix the target |
| `conflict` | Candidate does not merge cleanly | Candidate blocked with the conflicting paths; batch continues |
| `target_moved` | Target SHA changed during the batch | Batch discarded and restarted on the new base |
| `timeout` | Verify exceeded the limit | Treated as red for that run; if the culprit run, blocked as `timeout` |
| `publish_failed` | `publish_command` non-zero | Local merge kept; reported; retried on the next `run_once` |
| `git_busy` | Repo lock | Retry with backoff, then fail |
| `ref_missing` | Candidate `ref` no longer exists | Candidate blocked with `ref_missing` |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below; severity is the consumer's policy.

| Error / event | Suggested recoverability |
|---------------|--------------------------|
| `git_busy`, `publish_failed` | `transient` |
| `timeout`, `target_moved` | `ambiguous` (a re-run decides) |
| `conflict`, `ref_missing`, `baseline_red` | `permanent` until a person or agent changes the inputs |

## 8. Acceptance Criteria

1. Batch of 8 where candidate 5 breaks tests: culprit 5 is found in 3 verify runs, the other 7 merge together, and the target never holds an unverified tree.
2. Two candidates that each pass alone but fail together: the later one is blocked as the culprit (`fails_in_combination`), and the earlier one merges.
3. All candidates fail alone: all blocked, none merged, no infinite loop.
4. A red baseline halts the queue, with no candidate blocked because of it.
5. Killing the process in each of TESTING, BISECTING, and MERGING and restarting leaves the repo with no temp branches and no lost or doubly merged candidate.
6. A concurrent push to the target during TESTING causes a restart, never a merge onto a stale base.
7. With a flaky verify (fails 1 in 3 runs) and `rerun_on_fail: 1`, a flaky pass is reported as `flaky_suspected`, not blamed on a candidate.
8. `merge-queue` with no arguments prints state, pending candidates and the last batch summary without taking the queue lock, and exits 0 when the queue is empty.
9. A blocked candidate's default row shows the reason and a log path, not the log; `--full` shows the last 40 lines.
10. `run_once` where one of four candidates is blocked exits 0 and names the blocked one; `baseline_red` exits 1.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| Merge Queue Processor agent | Calls `submit` for each PR in `ready_to_merge`; runs `run_once` on its schedule; maps `blocked` outcomes to `status = blocked + reason` and notifies the owning agent |
| Permanent `merge-queue` worktree | `init` once at `umas init --project` |
| Exception flow 4.9 (no clean subset) | All `blocked(test_failure)`; UMAS re-spawns agents with failure context up to `max_attempts` |
| Exception flow 4.11 (agent causes regression) | `blocked` plus `flaky_suspected`; UMAS reads its own flaky history from the event log |
| Verify command | `test-adapters run --json` wrapped so a non-passing result exits non-zero |
| Blocked reasons and failures | Mapped to records by UMAS; `conflict` becomes a merge-conflict code, `baseline_red` a halt that needs a supervisor. See [error-classifier](../error-classifier/README.md) section 9 |

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.4 (merge queue, state machine, algorithm), §4.9, §4.11; and `TECHNICAL-DESIGN-SPEC-PART3.md` §6.2 (`MergeQueueProcessor`).

| Deviation | Why |
|-----------|-----|
| Prefix-bisect replaces "split in half, test both halves" | The source code (Part 3) tests both halves independently of each other and recurses. It misses failures that only occur in combination, and costs more runs. Also, the design spec's "merge only the passing half" can merge an untested union |
| Baseline check added | Without it, a red target blames every candidate |
| CAS advance with restart | The source merges candidate by candidate into `main` after testing a different tree (`_merge_all`), so the tree that lands is not the tree that was tested |
| Persisted queue state | The source keeps the queue in memory (`self.queue`); a crash loses it |
| Conflicts handled per candidate | Source `_create_merge_branch` has no conflict handling |
| Test runner removed as a dependency | Verify is a command, so the queue works with any CI tool |

## 11. Open Questions

1. If the user's primary checkout has the target branch checked out, `update-ref` leaves that working tree behind the ref. Options: (a) require the primary checkout to be on another branch while the queue runs; (b) fast-forward the primary checkout with `git merge --ff-only` when it is clean; (c) document it. Which does the project prefer?
2. Should speculative parallel batches (test batch N+1 on the predicted result of batch N) be supported? It adds throughput but also complexity; the design assumes a small number of candidates.
3. Should `classify_culprit` be on by default? It costs one extra run per blocked candidate.

---

## 12. Reference Implementation (Source Code)

> Non-normative. Example code illustrating one way to implement this spec. May use consumer-specific names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [libs/README.md](./README.md).

### 12.1 MergeQueueProcessor (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §6.2.2

```python
from typing import List, Set
from dataclasses import dataclass

@dataclass
class PullRequest:
    id: str
    branch: str
    author: str
    files_changed: List[str]
    status: str
    created_at: datetime

@dataclass
class MergeQueueEntry:
    pr: PullRequest
    position: int
    added_at: datetime

class MergeQueueProcessor:
    def __init__(
        self,
        git_client: GitClient,
        test_runner: TestRunner,
        worktree_service: WorktreeService,
    ):
        self.git_client = git_client
        self.test_runner = test_runner
        self.worktree_service = worktree_service
        self.queue: List[MergeQueueEntry] = []
        
    async def add_to_queue(self, pr: PullRequest) -> None:
        """Add PR to merge queue."""
        entry = MergeQueueEntry(
            pr=pr,
            position=len(self.queue),
            added_at=datetime.utcnow(),
        )
        self.queue.append(entry)
        
        # Trigger batch processing
        await self._process_queue()
    
    async def _process_queue(self) -> None:
        """Process merge queue with batch verification."""
        
        if not self.queue:
            return
        
        # Step 1: Batch all PRs
        batch = [entry.pr for entry in self.queue]
        
        # Step 2: Create temporary merge branch
        merge_branch = await self._create_merge_branch(batch)
        
        # Step 3: Test merged stack
        test_result = await self.test_runner.run_all_tests(merge_branch)
        
        if test_result.passed:
            # All tests passed: Merge all PRs
            await self._merge_all(batch)
            self.queue.clear()
        else:
            # Tests failed: Bisect to find culprit
            culprits = await self._bisect_failures(batch)
            
            # Remove culprits from queue
            for culprit in culprits:
                self.queue = [e for e in self.queue if e.pr.id != culprit.id]
                await self._notify_failure(culprit, test_result)
            
            # Retry with remaining PRs
            await self._process_queue()
    
    async def _create_merge_branch(
        self,
        prs: List[PullRequest],
    ) -> str:
        """Create temporary branch with all PRs merged."""
        
        merge_branch = f"merge-queue-{uuid.uuid4().hex[:8]}"
        
        # Create branch from main
        await self.git_client.create_branch(merge_branch, "main")
        
        # Merge all PRs
        for pr in prs:
            await self.git_client.merge(merge_branch, pr.branch)
        
        return merge_branch
    
    async def _bisect_failures(
        self,
        batch: List[PullRequest],
    ) -> List[PullRequest]:
        """Bisect to find failing PRs."""
        
        if len(batch) == 1:
            return batch
        
        # Split batch in half
        mid = len(batch) // 2
        left = batch[:mid]
        right = batch[mid:]
        
        # Test left half
        left_branch = await self._create_merge_branch(left)
        left_result = await self.test_runner.run_all_tests(left_branch)
        
        # Test right half
        right_branch = await self._create_merge_branch(right)
        right_result = await self.test_runner.run_all_tests(right_branch)
        
        culprits = []
        
        if not left_result.passed:
            culprits.extend(await self._bisect_failures(left))
        
        if not right_result.passed:
            culprits.extend(await self._bisect_failures(right))
        
        return culprits
    
    async def _merge_all(self, prs: List[PullRequest]) -> None:
        """Merge all PRs to main."""
        for pr in prs:
            await self.git_client.merge("main", pr.branch)
            pr.status = "merged"
```

### 12.2 Merge queue configuration (YAML)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §6.2.3

```yaml
merge_queue_config:
  # The merge-queue worktree is PERMANENT — created once during umas init --project.
  # Only the temp test branch is created/destroyed per batch.
  # State machine: IDLE → COLLECTING → TESTING → BISECTING → MERGING
  # See UMAS-TECH-DESIGN-SPEC.md §3.4 Merge Queue Processor
  worktree: permanent
  
  batch_size: 10
  batch_timeout_seconds: 300
  
  testing:
    run_all_tests: true
    parallel_execution: true
    timeout_per_test: 60
    
  bisecting:
    enabled: true
    max_depth: 10
    # If all PRs fail independently → all moved to blocked (failed_in_isolation)
    # Agents re-spawned with failure context. Retry limit: 3 per PR.
    # See UMAS-TECH-DESIGN-SPEC.md §4.9
    
  notifications:
    on_merge: true
    on_failure: true
```
