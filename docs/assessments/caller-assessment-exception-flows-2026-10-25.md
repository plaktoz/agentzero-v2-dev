Verdict: REJECTED

# Caller assessment: exception-flows (2026-10-25)

**Spec:** `umas/modules/exception-flows/exception-flows-spec.md`
**Assessed as:** orchestration, agent-execution, budget-and-models, monitoring (watchdog, boot), `umas start-all`.

## Findings

| # | Gap | Section | Caller needs | Severity |
|---|-----|---------|--------------|----------|
| 1 | No detector or owner for 6.12 corruption, the 6.16 free-space check, or 6.7 in CLI Workers | 2.1, 6; Open 9, 10, 12 | Owner, detector, interval | Critical |
| 2 | Unclean shutdown has two rules: 6.17 resumes from `STATE.md`; boot 3b treats no `PAUSE.md` as crashed. SIGTERM is not guaranteed, so this is the common case | 6.17, 8; Open 2 | One rule and end state | Critical |
| 3 | P1 responder: 6.2 says System Patrol; A.5.4.1 keeps P1 with the Coordinator | 2.2; Open 1 | One responder per flow | Critical |
| 4 | Shared flow 2.2 is proposed and conflicts with flows: 6.16 retries an `ambiguous` error; 6.12 is `transient` in the register but "no retry" in section 8. 13 of 17 flows give no recoverability | 2.1, 2.2, 8 | Normative, or informative | Critical |
| 5 | P0 append on a full disk needs space (Open 17). The `<100 MB` pause checkpoint is a git commit with no failure outcome | 6.16, 8 | Fallback file; failed-checkpoint outcome | Critical |
| 6 | Coordinator reads `escalate`; agent-session `escalate()` writes `session_escalated`, which would be missed. `boot_recovery` has no payload | Open 4, 5 | One event name; payload | High |
| 7 | `PAUSE.md` names differ (Open 3). Nothing deletes `PAUSE.md` or `.pause` after resume, so a stale file makes a later crash look clean. `umas agents pause` sets `machine_paused` (main 7), so boot auto-resumes a deliberate pause | 3, 6.17 | Writer, reader, deleter per file | High |
| 8 | Boot 3a checks "an OIDC token" per session, but agents hold their own credential (A.5.2). No refresh rule; with a 5-15 min TTL most boots will reach `auth_expired` | 6.17 | Which credential; refresh rule | High |
| 9 | Section 4 is all "text only" (Open 13). The 24 h `budget_paused`/`provider_failed` timeout has no outcome here. The 60 s boot limit (Open 12) has no end state | 4; Open 12, 13 | Keys; timeout outcomes | High |
| 10 | No section 5 row names `resource:action`. A.5.4 lacks resume, `--reset-retries`, daemon `.pause` writes, and Monitor `crashed` marking | 5; Open 14 | A.5.4 row per capability | High |
| 11 | "systemd PreStop / launchd StopSignal" not checked against platform docs (unverified). No Windows path. Kill timeout unset | 6.17 | Per-OS mechanism, timeout | High |
| 12 | 6.6 has the agent set `budget_paused`; agent-session 9 has UMAS set it. 6.7 names no status. `crashed` has four meanings. No exit from `budget_paused` or `provider_failed` | 6.2, 6.6, 6.7 | Status owner; transitions | High |
| 13 | `failed_in_isolation` vs `test_failure` (Open 7). `ready_queue` vs `ready`. `test_flaky` (6.11) has no source | 6.9-6.11 | Names; reset semantics | Medium |
| 14 | 6.3 starts an empty log; event-log 5.4 quarantines and writes `log.repaired` (Open 6). 6.14 `--now` has no failure outcome | 6.3, 6.14 | One behaviour; outcome | Medium |
| 15 | Mermaid follows 2.2, where P2 and P3 skip the state step. 6.5, 6.14, 6.17 are operations, not failures, and fit no step | 2.1, 2.2 | Diagram or register change | Medium |
| 16 | 6.1 prompt is interactive; daemon, REST and `health-check` cannot answer it. 6.2 leaves project `status` unchanged | 6.1, 6.2 | Non-interactive path; status rule | Medium |
| 17 | Open 8 stale numbering. Watchdog `paused` missing from node states (3.4). 2 min and 5 min staleness thresholds have no stated relation | 4; 7 | Alignment | Low |

**Tally:** 5 Critical, 7 High, 4 Medium, 1 Low.

**Fence check:** Correct. Lines 252-263 are a `markdown` fence, so `#### State at pause` is sample text.

**Open items (spec numbering):** Block a caller from starting: 1, 2, 3, 4, 5, 9, 10, 11, 12, 13, 14, 15, 17. Do not block: 6, 7, 8, 16.

## Devil's-advocate case

The design treats a clean pause as normal. The OS can kill processes without SIGTERM, and tokens last 5-15 minutes. So the common shutdown ends as "no `PAUSE.md`, so crashed", with an expired token on top. Every owner is "proposed", so each module can defer. A caller that gets a failure cannot say what to do next.

## Decisions for the owner

1. **Unclean shutdown (Open 2).** A: resume from `STATE.md` when clean, 6.8 when dirty. B: always crashed; issue #6 stays unsolved. C: always resume; can overwrite work. **Recommend A**, closest to agent-session 5.6.

2. **P1 responder (Open 1).** A: Coordinator for all; cannot act on a vanished project (6.2). B: System Patrol for all; contradicts A.5.4.1. C: per flow. **Recommend C**: Coordinator for 6.7 and 6.9, System Patrol for 6.2.

3. **Detection owners (Open 9, 10, 12).** A: daemon tick for disk; API for the database (A.4.6); agent-execution for provider errors; watchdog stall rule for CLI Workers. B: unowned, so no trigger. **Recommend A**, and state the CLI Worker limit.

4. **Shared flow 2.2.** A: normative; needs 17 codes that error-classifier does not supply. B: informative; each flow's rules win. **Recommend B.**

5. **Boot auth check (access-control Open 11).** A: validate the agent credential; the human token gates human commands. B: keep OIDC as written; most boots become `auth_expired`. **Recommend A**, once access-control sets the credential lifetime.

6. **Pause files.** A: the resumer deletes `.pause`; `recover()` consumes `PAUSE.md`; a deliberate pause gets its own status. B: leave unstated, so stale files cause false clean pauses. **Recommend A.**
