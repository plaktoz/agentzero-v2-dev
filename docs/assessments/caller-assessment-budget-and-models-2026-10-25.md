Verdict: REJECTED

# Caller assessment: budget-and-models (2026-10-25)

**Spec:** `umas/modules/budget-and-models/budget-and-models-spec.md`
**Callers assessed as:** orchestration (`admit`, dispatch pause), agent-execution (`commit`, `record`, `pack`, aliases), monitoring (events, forced handoff).

## Findings

| # | Gap | Section | What the caller needs | Severity |
|---|-----|---------|-----------------------|----------|
| 1 | Possible double count. Step 5 records each coordination call; step 10 commits the task hold as "true usage". The spec does not say whether `actual` includes usage already recorded (budget-meter 10: commit replaces the hold) | 2 (5, 10) | One metering rule: what goes through reserve/commit and what through record | Critical |
| 2 | Reservation id has no owner. `set_admit` returns only admit or defer (task-queue 4), yet section 3 says `Admit{reservation}` reaches orchestration | 2, 3 | Where the id is stored per task, and how agent-execution gets it for `commit`/`release` | Critical |
| 3 | `estimate` has no source or default. Open 7 proposes a task field that section 4 does not list | 3, 4 | Field name and default | High |
| 4 | Hold and lease diverge. An expired lease re-admits the task while the dead holder's hold runs 900 s. `reserve` is not idempotent (Open 21). `lease_seconds` unset | 4, 8 | Lease value; release of old hold on re-admission | High |
| 5 | Worker bound claimed, not built. Section 1 says budget-meter enforces per-task time and checkpoint limits; budget-meter has neither, and no parameter here sets them. A CLI Worker reports no usage, so `commit` has no `actual` | 1, 4, 8 | The mechanism, its parameters and owner, and the Worker's `actual` | High |
| 6 | Failure outcomes missing. `admit` errors become `defer: admit_error` (task-queue 7), losing the cause. `commit` after TTL expiry is not covered | 8 | Outcome and recipient per error | High |
| 7 | Alias contract incomplete. Default key "not set" (Open 5); 5.7 uses `claude-default`/`claude-deep` while Open 1 is undecided; no `resolve(role)` signature | 3, 4, 8 | Decided names and default key; `resolve` signature | High |
| 8 | Permissions wrong or missing. Set budget, metrics, forced handoff and resume have no A.5.4 name. Forced handoff cites A.5.5, which gives Monitors restart and nudge only. The metrics row gives Viewer project scope, but A.5.4 gives Viewer system scope. Owner cap has no value | 5 | `resource:action` added to A.5.4 and A.5.6; cap value | High |
| 9 | `budget_paused` has two owners. Section 2 and 6.6 make the agent set it; budget-meter 9 and agent-session 9 say UMAS sets it. Section 5 says a human resumes; section 2 says the Monitor resumes dispatch. The 24 h timeout outcome is not stated | 2, 4, 5, 8 | One owner for the status, the resume actor and the timeout outcome | High |
| 10 | `RequiredTooLarge` on the 90% path has no outcome (Open 13) | 8 | Fallback and escalation | High |
| 11 | Budget-pause signal carrier unnamed (Open 14, proposed). Handoff trigger owner conflicts: step 8 has the Monitor force at 95%; agent-session 5.1 has the session call `handoff` | 2, 8 | Carrier and poll point; one trigger owner | Medium |
| 12 | `on_usage` to `record` mapping: the event has no `budget`, `actor` or `ref`; `metadata{}` keys undefined; charged failed attempts not addressed | 3 | Metadata keys; failure record rule | Medium |
| 13 | `handoff_request` payload undefined here (agent-execution uses `reason, token_usage, token_limit, task_id`; agent-session emits `handoff_initiated`). `poll_events(cursor)` is not defined as an operation | 3, 6 | One event name and payload; confirmed signature | Medium |
| 14 | Linked specs `exception-flows-spec.md` and `interfaces-spec.md` do not exist. `umas project config --budget`, metrics output and REST route (Open 18) are undefined | 3, 6, 8 | Interfaces spec with payloads, exit codes and errors | Medium |
| 15 | Period thresholds `[0.80, 1.0]` differ from budget-meter and main section 9 (80/90/95) | 4 | One list | Low |

**Tally:** 2 Critical, 8 High, 4 Medium, 1 Low.

**Proposed claims a caller would build on:** Monitor event carrier, `.pause` budget signal (Open 14), per-checkpoint holds (Open 8), `record` on both budgets (Open 10).

## Devil's advocate

The design fails at its first charged task. Coordinator usage is recorded per call and the task hold is later committed at its true total. If `actual` includes those calls, tokens count twice and the 80% alert and 100% pause fire early. Workers are not metered: the CLI reports nothing and the time limits have no code. A crash holds budget until TTL. The spec names every interface, but the three things a caller decides on every call (what is counted, where the hold lives, what a failure does) are the three it leaves open.

## Decisions for the owner

1. **Metering rule (gap 1).** (a) reserve/commit for task work; `record` only for Coordinator calls outside a task. (b) `record` everything, no holds. **Recommend (a):** matches budget-meter 10, no library change.
2. **Worker bound (gap 5).** (a) launcher enforces wall-clock and checkpoint limits under `watchdog`; budget-meter stays token-based. (b) add a time unit to budget-meter. (c) accept unbounded Worker tokens. **Recommend (a).**
3. **Who sets and resumes `budget_paused` (gap 9).** (a) UMAS glue sets it; a human resumes sessions; the Monitor resumes dispatch. (b) the agent sets it at a step boundary. **Recommend (a):** the agent may be stalled when the budget hits 100%.
4. **Alias names (gap 7).** (a) `default` and `deep` (Open 1). (b) keep `claude-default` and `claude-deep`. **Recommend (a).**
5. **Permission names (gap 8).** (a) add `budget:set`, `metrics:read`, `agent:handoff`, `agent:resume` to A.5.4 and A.5.6. (b) reuse `config:write`, which only Admin holds, so Project Owners could not set budgets. **Recommend (a).**
6. **Trigger owner (gap 11).** (a) the session acts at its own threshold; the Monitor is the backstop. (b) the Monitor forces every emergency handoff. **Recommend (a).**
