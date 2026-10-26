Verdict: REJECTED

# Caller assessment: context-persistence

**Spec:** `umas/modules/context-persistence/context-persistence-spec.md`
**Callers assessed as:** orchestration (Scheduler and launcher: `create`, `open`, `find_signals`, `poll`, `complete`); agent-execution (launcher and CLI Worker: state, checkpoint, pause, recover).
**Gaps:** 7 critical, 8 high, 3 medium.

## Findings

| # | Gap | Sec | Caller needs | Severity |
|---|---|---|---|---|
| 1 | §2 steps 2-3 drive an in-process `execute` loop. A.4.8 rules that out for CLI Workers. No section says who calls `checkpoint`, `done` or `pause` for them. | 2, 3 | Calling party per interface, per worker type | Critical |
| 2 | Event types not catalogued (Open 4). Orchestration reads `{"event":"escalate",...}`, which is not the event-log envelope. No `data` schema. `poll` filter shape missing. | 3 | Type list, `data` per type, filter | Critical |
| 3 | Commit prefix undecided (Open 2, 3). Main 5.1 uses `[umas] <agent-id>`; agent-execution uses `[umas:checkpoint]`. `blocked`, `escalated`, `abandoned` have no commit signal. | 3, 4 | One prefix and subject template for all outcomes | Critical |
| 4 | Lease renewal "at each step boundary" (proposed). A step can outlast `lease_ttl` (300 s default). Orchestration renews a separate task lease. `lease_ttl_seconds` is `not set`. | 2, 4 | One renewal owner, cadence, TTL | Critical |
| 5 | First dispatch conflicts. §2 step 1 has `create` take the lease. Orchestration Open 9 has the launcher call `open` and fail on `LeaseHeld`, which the `create` lease would cause. | 2, 3 | Which call on first dispatch, retry, lease expiry | Critical |
| 6 | `PAUSE.md` and `HANDOFF.md` are never retired. `recover` reads `PAUSE.md` first, so a later crash resumes from a stale pause. The `.pause` deleter ("the orchestrator") is not named. | 2, 3 | Archive or delete rule on resume; owner | Critical |
| 7 | `complete(name)` has two callers: this spec (Open 18) says Scheduler, orchestration's launcher loop says launcher. | 2, Open 18 | One caller | Critical |
| 8 | No error column in §3. Errors are only in §8 prose: `open` (LeaseHeld), `checkpoint` (NotOwner, GitBusy, CommitFailed, DiskFull), `handoff` (RequiredSectionTooLarge), `write_state` (StateCorrupt). | 3, 8 | Error list per interface | High |
| 9 | `RecoveredContext` and `RecoveredSession` have no field list. `recover` has two signatures and two read sources (hook-store reads the last commit; agent-session reads the working copy). | 3 | One `recover`, its return type, its read source | High |
| 10 | Partial failure has no owner: hook made but session `create` fails; `HANDOFF.md` written but commit fails; done commit made but `complete` not called. | 8 | Rollback or retry per step | High |
| 11 | Repeat behaviour unstated. After lease expiry (orchestration Open 9) a second worker may call `done` or `handoff` on the same hook. `find_signals(since?)` has no type. | 3, 4 | Repeat rule per call; `since` type | High |
| 12 | Defaults missing: `base_branch`, `owner`, the name-from-task rule, `event_source` (`""` in a required envelope field), `durability` (Open 8 says `fsync`), `checkpoint_every` (Open 15), `git_lock_timeout`, `abandon_after`. | 4 | Value and setter per item | High |
| 13 | Name and path mismatch. hook-store's name regex forbids `/`, but §2 and §5.1 use `auth-login/`. Absolute or relative `hook_path` not stated. | 2, 3, 4 | Name rule and path form | High |
| 14 | Two `STATE.md` writers and schemas (Open 1): hook-store `write_state` and agent-session. | 3 | One schema, one writer | High |
| 15 | Create, checkpoint, `recover` and `clean` have "none named" permissions (Open 17). A.5.7 requires a name per route, so these cannot be built yet. | 5 | Names agreed with access-control | High |
| 16 | `signal_format`, `prune_completed_after_hours` (48) and `prune_abandoned_after_hours` (168) are missing from §4. Actor field is `actor` in §6 and A.5.7, `source` in §3 and §4. | 3, 4, 6 | Rows added; one field name | Medium |
| 17 | Mermaid omits the blocked and crash paths, boot recovery and `complete`. Text in §2 covers them. | 2 | Diagram matches text | Medium |
| 18 | Read shapes missing: `find_signals` return, `list(filter?)`, poll cursor owner. The Scheduler has no A.5.5 role and so no stated right to read events. | 3, 5 | Shapes, cursor owner, role | Medium |

## Devil's-advocate case

Every failure and recovery path in §2 assumes an in-process loop, which A.4.8 rules out for the agents that commit code. The CLI path that remains (harness writes files and `[umas:checkpoint]` commits) has no owner for the lease, the event appends, the `.pause` deletion or the completion call. The Scheduler cannot tell done, blocked and crashed apart. Stale `PAUSE.md` and `HANDOFF.md` can be resumed after a later crash. The Scheduler glue that calls `create` has no spec (orchestration Open 2).

## Decisions the owner must make

- **D1. CLI Worker write path (gaps 1, 4, 5, 14).** Options: (a) the harness commits with raw git; (b) the harness calls `umas` commands; (c) the harness edits files only and the launcher makes every library call. Recommendation: (c), per A.4.8.
- **D2. Signal vocabulary (gaps 2, 3).** Options: `[umas:*]` (main 5.3) or agent-session `[done]`. Recommendation: `umas:` for done, checkpoint, blocked, escalated, abandoned; event types `escalate` and `handoff_request`; `severity` in `data`.
- **D3. Lease cadence (gap 4).** Options: launcher timer, or step-boundary heartbeat with a TTL above the longest step. Recommendation: launcher timer renewing hook and task leases every 100 s, TTL 300 s.
- **D4. `PAUSE.md` and `HANDOFF.md` lifecycle (gap 6).** Options: delete on resume, or archive and commit. Recommendation: archive and commit, so `recover` reads only current files.
- **D5. Completion owner (gap 7).** Recommendation: Scheduler, which owns task-queue `complete`; the launcher only reports the signal.
- **D6. Permission names (gap 15).** Recommendation: accept Open 17 names.
