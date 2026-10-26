REJECTED

Assessed as: orchestration (sets `ready_to_merge`, re-spawns), interfaces (`umas` verify, merge, init), exception-flows (6.9, 6.11), monitoring (polls `status`), access-control (approval check).

Open items: 16 of 26 block a caller (O1-O4, O7-O15, O20, O21, O24). Safe to defer: O5, O6, O16-O19, O22, O23, O25, O26.

## Findings (B blocker, H high, M medium, L low)

| # | Gap | Sec | Caller needs | Sev |
|---|-----|-----|--------------|-----|
| 1 | No operations of its own. The main spec CLI list (7) has no merge, verify or approve command. | 3 | Operation table: payload, exit codes, errors, idempotency | B |
| 2 | Approval has no interface (O7). | 3, 5 | Approve signature; where the record lives; how the queue reads it | B |
| 3 | Candidate undefined: `id` vs task id, `meta`, and the `ready_to_merge` setter (O8). | 3 | Candidate schema; setter | B |
| 4 | Reviewed is not merged. O11 resolves `ref` at batch time, so a later commit lands unreviewed. | 3 | Pinned SHA, or a check at batch time | B |
| 5 | `BatchReport` and `status()` fields are "[P]". | 3 | Fixed JSON schema | B |
| 6 | No glue: the queue writes no events, `work_bundles.status` has no `blocked`, and the loop owner is open (O9). | 2, 6 | Loop owner; event types; task status | B |
| 7 | Review and test-policy have no named actor. Inputs (`intent`, `risk_flags`, `test_results`, `existing_tests`) are unset. `missing_intent`, `warn` and bad JSON have no outcome. | 2, 3, 8 | Stage owner; input sources; failure rows | B |
| 8 | `verify.command` has no value (O1). With `require_tests: true`, zero tests is `error`, so a repo with no tests halts as `baseline_red`. | 4, 8 | Command; zero-test rule | B |
| 9 | The queue reads only the exit code (merge-queue 5.1). test-adapters exits 1 for `failed`, `error` and `timeout`, so the spec's `timeout` blocking cannot be set from the code. A tool `error` is blamed as `test_failure` (O2, O3). | 8, AXI | Separate code for non-test faults | H |
| 10 | Flake chain: O4 sets `retry_failed` 0, so no flaky names exist. The queue re-runs any red; 6.11 re-runs only with `test_flaky` history. | 4, 8 | One flaky mechanism and field | H |
| 11 | Re-spawn needs failing names, which exist only in the capped log. | 3 | Name source | H |
| 12 | `baseline_red` and `target_moved` (O13) have no event, owner, resume or restart cap. | 8 | Escalation and resume | H |
| 13 | No review-round counter (`attempts` counts culprit blocks only). A known `id` cannot be resubmitted. `requeue` skips review (O24). | 2, 8 | Retry and re-entry rules | H |
| 14 | Permissions "None named", but access-control already seeds `merge:approve` and `merge:approve_own`. Libs take no `actor` for audit. | 5 | Exact names; audit path | H |
| 15 | Escalate payload `{"event":...}` does not match the event-log envelope (`type`, `source`, `data`). No task id. | 3 | One envelope | H |
| 16 | Candidate code runs in the queue worktree under the processor identity, which can also write and publish the target. | 5 | Sandbox or credential split | H |
| 17 | Every config entry is "Config file" (O21). Keys collide: `timeout_seconds`, `coverage`, `mode`, `retry_failed`. | 4 | File name; key namespaces | M |
| 18 | Moved 5.4 half-split text sits beside prefix-bisect. O23 only recommends. | header, 9 | Mark 5.4 superseded | M |
| 19 | Mermaid shows a review-fail return to the Worker. Numbered step 4 has none. Mermaid omits conflict, `target_moved`, publish. | 2 | Align both | M |
| 20 | No cost cap: N failing candidates give N batches of about ceil(log2 n) runs at up to 1800 s each. | 8 | Batch or time budget | M |
| 21 | Callers would build on "[P]" items: sync/async column, verify wrapper, `requeue`/`cancel` behaviour. | 3, 5, 6 | Decided, or marked open | M |
| 22 | Dead link `../interfaces/interfaces-spec.md`. Header says "none" but section 6 lists seven. | header | Fix | L |

Totals: 8 B, 8 H, 5 M, 1 L.

## Devil's advocate

The module has no interface of its own. It points to two libs and two packs, and leaves the glue unowned: approval, status, events, review dispatch and re-entry. That glue holds every hard failure path. The gate binds nothing: review and approval attach to a branch name, and the queue merges whatever the branch holds at batch time. "Nothing unverified lands" protects tested trees, not reviewed ones.

## Decisions for the owner

**D1. Approval and ready status (O7, O8; gaps 2, 3).**
- (a) Approve before `submit`; orchestration sets `ready_to_merge`.
- (b) Approval hook inside the queue run.
- (c) Approve after verify.
- Consequences: (a) edits A.5.4.1 only, but approves an untested tree. (b) breaks the lib's no-approval non-goal. (c) holds a verified batch and risks `target_moved`.
- Recommend (a), bound to a SHA.

**D2. Pinned SHA (gap 4).**
- (a) Submit a SHA; a fix is a new candidate.
- (b) Compare the SHA at batch time. Needs a lib hook.
- (c) Keep the branch. Unreviewed code can merge.
- Recommend (a). No lib change, and each new SHA gets re-reviewed.

**D3. Verify faults and flakes (O2, O3, O4; gaps 8 to 10).**
- (a) Wrapper only, mapping JSON `status` to exit codes.
- (b) Lib change: exit 0 green, 1 red, other codes halt as `verify_error`.
- (c) Keep the blame as today.
- Consequences: (a) cannot halt the queue. (c) blocks innocent Workers. (b) changes the exit-code contract (AXI open point 2).
- Recommend (b), with `retry_failed` 0 in verify and `rerun_on_fail` 1.

**D4. Owner of the glue (O9, O13; gaps 6, 12).**
- (a) A plain processor under the service manager (A.4.8) that runs the loop and writes events.
- (b) Orchestration's Scheduler calls `run_once` on its tick.
- Consequences: (b) ties dispatch to a blocking call and leaves `baseline_red` without an owner.
- Recommend (a), with events merged, blocked, baseline_red and escalate.

**D5. Permission names (O14, O15; gap 14).**
- (a) Adopt the access-control seed list and name every action.
- (b) One coarse `merge:approve` for all actions.
- Consequences: (b) lets an approve grant cover target writes.
- Recommend (a). State whether A.5.9 Q5 applies to the processor service account.

**D6. Re-entry (O24; gap 13).**
- (a) Cap review rounds with a counter; re-enter only through review.
- (b) Allow `requeue` straight to the queue.
- Consequences: (b) skips review and gives `--reset-retries` nothing to reset.
- Recommend (a), plus a lib reset that clears `attempts`.
