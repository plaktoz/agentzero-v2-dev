Verdict: REJECTED (round 1)

Spec: `umas/modules/orchestration/orchestration-spec.md`. Date: 2026-10-25.

**Callers assessed:** Interfaces (CLI, REST), agent-execution, budget-and-models (`admit`), verification, monitoring, access-control, context-persistence, exception-flows.

Severity: **B** blocks start. **H** a caller must guess. **M** needs a default or decision. **L** cosmetic.

| # | Gap | Section | Caller needs | Sev |
|---|---|---|---|---|
| 1 | No command or payload for grilling answers or summary confirmation. The CLI is a short-lived client with a 300 s timeout (main 2.3). | Interfaces; Flow 2-3 | Commands, payload, request id | B |
| 2 | No error returns or exit codes. Idempotency not stated for `request`, `approve`, `retry`, `POST`. | Interfaces | Typed errors; idempotency per mutation | B |
| 3 | `admit` cannot be written. budget-meter estimates are tokens; Open 2 proposes time and checkpoint limits, which are "not set". Budget id and `context` unnamed. | Parameters; Interfaces; Open 2 | Estimate unit, budget id, context fields, default | B |
| 4 | Two completion owners: Scheduler (5.2, Figure 1) and launcher (Open 1, agent-execution step 7). Outcomes `done/blocked/escalated/abandoned` (agent-execution 3.4) are not mapped. | Flow 9-10; Figure 1 | One owner of complete/fail/release; outcome table | B |
| 5 | Task payload, tags, priority and claim owner have no schema or default. Queue directory and `max_claimed` scope unset. | Interfaces; Parameters; Open 2 | Field types, tag values, defaults, owner format | B |
| 6 | Who splits a request into tasks is Open 3. No bundle can be created without it. | Flow 6 | Producer and output schema | B |
| 7 | Hook creation: at add (Flow 7) vs at claim (agent-execution 2.1). Bundle row, `add_batch` and hook create have no partial-failure rule. | Flow 6-7; Open 8 | Timing, arguments, rollback | H |
| 8 | No transition for Coordinator, Router or provider failure before MONITORING. `Any -> IDLE` on "all tasks failed" conflicts with Open 4 (`failed`). Gate reject has no command. | State table; Open 4 | Transition per failure; one terminal mapping | H |
| 9 | task-queue `failed` is terminal with no re-open op. `retry --reset-retries` is defined for merge-queue PRs (6.9), not bundles. | Interfaces; 6.9 | Re-open rule; reset meaning | H |
| 10 | Failures sent here are missing: CapabilityMissing, specialist validation, AssignmentWriteFailed (agent-execution), provider 401 (P0, 6.7), machine pause (6.17). | Failure handling | Outcome and state per failure | H |
| 11 | P1 receiver: Capabilities says Coordinator (as A.5.5); 6.2 says System Patrol. No Open item. P0 has no path. | Capabilities; 6.2 | Receiver for P0 and P1; add to Open | H |
| 12 | Capabilities cites A.5.4 rows, which have no `resource:action` names. Only proposed names appear (`work:submit`, `work:read`, `budget:set`). | Capabilities | Exact permission names | H |
| 13 | `handoff_request` and budget threshold events are received with no payload or Scheduler action. | Interaction; Interfaces | Fields and action per event | H |
| 14 | Interaction rows omit operations: verification (`ready_to_merge`, findings, re-spawn; its O8, O9); access-control (credential create and revoke). | Interaction | Operation, payload, timing | H |
| 15 | `interfaces-spec.md` does not exist (3 links, `umas/modules/interfaces/` absent). `POST /work-bundles` has no body. `PATCH /tasks` has no field list or task-queue op. | Interfaces; Open 11 | Owning spec; bodies; op mapping | H |
| 16 | `coordinator_config` file unset (Open 5). Default `claude-default` conflicts with budget-and-models ("not set") and is not an llm-gateway alias (3.2 shows `default`, `planner`). | Parameters | File, key, default alias | H |
| 17 | `human_initiated_only: true` is unclear against grilling 5.1, where escalation origin also grills. | Parameters; 5.2 | Rule for escalation origin | H |
| 18 | Playbook steps to tasks: no mapping. `--exit-predicate` without a playbook is undefined. | Flow 5 | Mapping rule; flag meaning | M |
| 19 | No rule from `complexity_thresholds` to `files_affected`; `scan` producer unnamed; re-route on worker escalation (router 5.6) unused. | Parameters | Mapping table; scan source | M |
| 20 | No owner for the 60 s budget-raise poll. A watchdog restart can overlap a re-claim (Open 9 proposes LeaseHeld; restart rule unstated). | 6.6; Open 9 | Poll owner; restart rule | M |
| 21 | Figure 1 shows Worker to Scheduler, with no launcher, `complete`/`fail`, playbook gate, cancel or resolve. It does not match the numbered flow. | Figure 1 | Redraw from Flow 1-11 | L |

Count: 6 B, 11 H, 3 M, 1 L (21 gaps).

**Stale links:** `../interfaces/interfaces-spec.md` (3 links, absent). Flat `libs/*.md` paths in 5.2.

## Devil's advocate

Cost control fails as written. Worker token use is visible only as far as each CLI reports it (A.4.8, not yet checked), so `admit` cannot enforce the budget that 6.6 relies on, and Open 2's time caps are "not set". Completion has two owners, execution is at-least-once, and `add_batch` and `reserve` are not idempotent, so a retried launcher double-adds tasks and holds. The main path is "Scheduler glue" that the spec leaves unspecified.

## Decisions the owner must make

1. **Worker budget unit** (row 3). Options: (a) time and checkpoint caps for Workers, tokens for coordination agents; (b) wait for verified CLI usage; (c) fixed token estimate per task. Recommend (a).
2. **Completion owner** (row 4). Options: Scheduler via `find_signals`; launcher via `read_signal`. Recommend the launcher alone calls complete, fail or release.
3. **Grilling channel** (row 1). Options: CLI `answer` and `confirm` against a request id; REST polling. Recommend the CLI.
4. **Escalation receiver** (row 11). Options: Coordinator (A.5.5) or Patrol (6.2). Recommend Coordinator, amend 6.2; P0 to Operator or Project Owner.
5. **Meaning of DONE** (row 8). Options: all tasks `completed`, or merged. Recommend merged, with a `MERGING` state.
6. **Permission names** (row 12). Recommend adding `work:submit`, `work:read`, `work:cancel`, `work:retry`, `gate:approve`, `budget:set` to A.5.6; settle A.5.9 Q5.
7. **Decomposition owner** (row 6). Recommend the Coordinator, with the Architect for medium and above, validated by Pydantic (ADR-0004).
8. **Config key** (row 16). Recommend one key in `umas.config.yaml` (Open 5) and the `default` alias.
