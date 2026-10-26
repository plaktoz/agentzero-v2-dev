# Decisions pending from the owner (2026-10-25)

## Owner answers (2026-10-25)

| # | Answer | Done in the repo | Still to do |
|---|--------|------------------|-------------|
| D1 | A: intersection | Main spec A.5.2 and A.5.9 Q5 set to Decided; kept in intro item 1. Agents with no user run as a named system principal with only their role's permissions | access-control, monitoring and verification specs still say "To confirm" in their Open lists; the revision pass removes them |
| D2 | Recommendation: `default` and `deep` | Renamed `claude-default` and `claude-deep` to `default` and `deep` in the main spec and in the orchestration, agent-execution and budget-and-models specs (14 places) | **`deep` is not defined in `libs/llm-gateway/README.md` section 3.2** (only `default` and `planner`). Add `deep` to the alias table, or choose another name. Not edited: it is a library change |
| D3 | Recommendation: Markdown only | Nothing to change | None |
| D4 | Recommendation: rewrite F5 in Python with a declared third-party CSV parser | Nothing yet | Rewrite F5 in `packs/minimalism-ladder/fixtures/`; re-check F1, F5, F6, F7, F8 for TypeScript (grep found it in F1, F5, F8) |
| D5 | Owner answer: (c), relax criterion 2 | Done: `packs/anti-slop/scripts/lint.py` excuses a name only when it is removed with a fact-free `generic_opening` or `filler` span and appears nowhere else. Tests added in `scripts/test_lint.py` (`FactFreeRemovalTests`). `anti-slop-spec.md` 8.2 criterion 2 updated. Criterion 2 passes on F1 to F4 and F8. Test run: 32 run, 1 failure (criterion 4, F3 "at scale") | Re-review F3 with the reviewer, then re-run the tests. Update `docs/tasks-skills-claude-mods-2026-10-25.md` and `SKILL-ASSESSMENT.md` (still record the old strict-criterion failure). Anti-slop stays `[-]` until F3 passes |
| D6 | Recommendations for all eight packs (table above) | Nothing yet | Per pack, in the order listed in the table |
| D7 | Recommendation: write the owner answer into A.5.9 Q7 and A.5.4.1 | A.5.9 Q7 now reads "Decided (owner, 2026-10-25): the Project Owner of that project, or the Admin if the project has none." A.5.4.1 says "decided (A.5.9, question 7)". Intro item 1 says both are decided | Monitoring and verification Open lists still say "awaits confirmation": revision pass |
| D8 | A: refuse with `audit_unavailable` | Decision recorded here | access-control revision: refusal rule, error code, Figure 1 audit branch |
| D9 | A: Keycloak call on every request. **Differs from my recommendation B.** Consequence: every request fails while Keycloak is down | Decision recorded here | access-control revision: state the outage behaviour; token lifespan still to set in the realm file |
| D10 | a: `check` takes `requester_id` and returns `two_person_rule`; work items carry `requested_by` | Decision recorded here | access-control revision (Figure 1, `check` input, two-person section); verification and orchestration must send `requested_by` |
| D11 | A: OIDC on every call | Decision recorded here | access-control revision: one sign-in path |
| D12 | A: agent-execution owns the launch path | Decision recorded here | agent-execution revision: `launch` signature, return value, errors |
| D13 | More detail requested; see "D10 and D13 detail" below | Not decided | Owner decision |
| D14 | A: wall-clock unit added to budget-meter; launcher stops the harness at the limit | Decision recorded here | budget-meter `time` unit is a library change, after batch-1 acceptance; agent-execution revision |
| D15 | a: watchdog restarts the Worker. **Differs from my recommendation b.** Consequence: a restart can repeat half-done work | Decision recorded here | agent-execution revision. Proposed mitigation (needs your OK): the restarted Worker starts from `recover(name)` output, not from scratch |
| D16 | ok: one prefix list in `commit_prefixes`; `signal_pattern` derived from it | Decision recorded here | agent-execution revision (Open 3) |


Each item: what is decided, why it matters, options, my assessment, recommendation. Answer by number. When answered, record the decision where the work lives (spec, README or `docs/decisions/`) and mark it here.

## D1. Do agents act with the intersection of role and requesting-user permissions? (was Q1)

**State:** open. Appendix A.5.9 keeps recommendation A as "To confirm". Every module that checks permissions builds on the answer: access-control, orchestration, monitoring, verification, interfaces.

**Example.** Alice has `task:create` on project A only. She asks the Developer agent to create a task. The Developer role itself holds `task:create` on every project.
- **A. Intersection.** The agent can act only where Alice and the role both allow it. If Alice names project B, the request is denied.
- **B. Full role permission.** The agent acts with the role's permissions. Alice, through the agent, creates a task in project B.

**Assessment.** B lets any user reach anything the agent roles can reach, so the role table becomes the real access policy and the user's own permissions stop mattering. A closes that. A costs one more rule: work with no requesting user (Patrol, scheduled jobs, boot recovery) has no user to intersect with.

**Recommendation: A**, plus a rule that user-less work runs as a named system principal with the role's permissions only, never wider. That rule is mine; it needs your agreement too.

## D2. Model alias names

**State:** `libs/llm-gateway/README.md` defines the alias `default`. The main spec section 5.7 uses `claude-default` and `claude-deep`. Specs that call the gateway use `default` (decided in M5), so the spec and the specs disagree.

- **A. `default` and `deep`.** Vendor-neutral. Matches the rule that every LLM provider must be replaceable by config, because the alias does not name a vendor.
- **B. Keep `claude-default` and `claude-deep`.** No edit to the main spec; but the name says "Claude" when the config may point at another provider.

**Recommendation: A.** One edit in section 5.7 and the budget-and-models spec's Open 1.

## D3. Should module specs also be written as `.html`?

The `ste-docs` skill writes an `.html` beside each `.md`. Every lib and pack spec in this repo is Markdown only, and the nine module subagents wrote Markdown only.
- **A. Markdown only.** One copy to keep in sync. Matches the libs and packs.
- **B. Add HTML.** Easier to read in a browser; two files per spec that can drift.

**Recommendation: A.**

## D4. minimalism-ladder fixtures written in TypeScript

**State:** a grep for "typescript" finds it in fixtures F1, F5 and F8. The subagent's report also lists F6 and F7; not yet checked by me. The repo rule is Python first.
- **A. Rewrite F5 in Python** with a third-party CSV parser declared in a manifest. Keeps the expected rung 4 (use a dependency).
- **B. Rewrite F5 with the standard library `csv`.** The expected rung changes to 3, so the fixture tests a different rung.
- **C. Keep as a non-stack fixture.** Needs a note explaining why it is allowed.

**Also open:** `fixtures/RESULTS.md` marks F4 and F6 PASS, but the stored records do not match the fixture text, and no independent judge has run.
**Recommendation: A**, then state a rule for mixed tasks, then re-run with an independent judge.

## D5. anti-slop: fixtures F1, F3, F8 fail (pack stays `[-]`)

`python3 -I -m unittest discover -s scripts`: 29 tests, 2 failures.
- **F1, criterion 2.** The reviewer removes a sentence that had no fact, and the name "AI" disappears with it. You decided on 2026-10-25 to keep the criterion as written, so F1 fails.
- **F3, criterion 4.** The saved reviewer output predates your rule-3 change and still keeps "at scale". Re-reviewing F3 should pass it. This needs no decision, only a re-run.
- **F8.** The input was rewritten five times after seeing outputs, so the result is weak. The subagent recommends a rule that replaces aliased terms with the one term rule 9 keeps. Do not change the F8 input again.

**Options for F1:** (a) accept failure and leave the pack `[-]`; (b) you change the F1 input so the name survives; (c) relax criterion 2 so a name that appears only in a removed fact-free sentence does not count as dropped.
**Recommendation: (c)**, because the current text punishes the right behaviour. It reverses your earlier decision, so I will not do it unless you say so.

## D6. What to do with each pack verdict

| Pack | Verdict | Recommendation |
|---|---|---|
| minimalism-ladder | skill | Install as a skill (after D4). |
| test-policy | skill | Install the whole folder with `PACK.md` renamed `SKILL.md`, so the pre-filter script and schema resolve. Keep strict-mode wording "exists before the change or is added with it". |
| anti-slop | skill | Blocked on D5. |
| router-heuristic | skill (earlier `needs engine` withdrawn) | Install as a skill. Do not build a scorer script yet. Decide whether a pure data migration routes `large` (spec open question 2; F7 routes `medium` today). |
| two-axis-review | duplicate of `code-review` | Fold the per-axis additions into `code-review`; drop the cross-axis merge and overall gate (they conflict). Mark the pack "folded into code-review". |
| grilling | duplicate | Offer the summary and the cap as additions to the installed `grilling`. Keep the "precise request" skip for an automatic variant only. |
| communication-modes | behaviour | Home is `behaviors/communication-modes/` in claude-mods. Six blockers must be settled first (audience vs doc type, handoff routing, intensity levels, anti_slop dependency, protected content list, `routing.yaml`). |
| specialist-agents | agents | Build `agents/<role>.md` per role. Four decisions in its assessment (sequence and skip rules stay as Coordinator data; ladder and test rules passed as text; add `needs`/`skipped` to output schemas, which changes spec 4.2; Developer does not commit, which conflicts with `implement`). |
| playbook-runner | needs engine | Accept. Fix rule 8 vs F1, add a REVIEW gate or drop F8, decide whether examples may name other packs. |

## D7. Where the escalation answer for security findings is written

A.5.9 row 7 says "Decided" but its answer cell is empty, and A.5.4.1 says routing still awaits confirmation. Your answer (Project Owner of the project, Admin if none) is recorded in the merge task list only. The fix is to write that answer into A.5.9 and A.5.4.1 so the spec matches the decision. **Proposed; not made yet.** Confirm the answer is still current and I will edit both places.

## D8 to D11. From the access-control caller assessment (REJECTED, round 1)

Full assessment: `docs/assessments/caller-assessment-access-control-2026-10-25.md`.

**D8. Audit write failure: refuse or allow?** When the audit record cannot be written, the action could (A) be refused with `audit_unavailable`, or (B) run and queue the record. A refusal stops work while the audit store is down. Allowing it means an approval can go through with no trace. The kc-axi lib takes option A (`audit_path` unwritable: the write is refused, exit 7, line 181 of its README). **Assessment:** A. **Recommendation: A.**

**D9. Token check during a Keycloak outage, and token lifespan.** (A) call Keycloak on every request: always current, every request fails when Keycloak is down. (B) check locally against cached keys, refuse when no key is cached: survives short outages, but a revoked token stays valid until it expires. The owner sets the lifespan (suggested 15 minutes), issuer and audience in the realm file. **Recommendation: B.**

**D10. Where the two-person check runs.** (A) `check` takes `requester_id` and returns a `two_person_rule` reason, so every caller gets one answer; work items carry `requested_by`. (B) each caller compares requester and approver before calling `check`; any caller that forgets breaks the rule. **Recommendation: A.**

**D11. Phase 1 sign-in.** (A) OIDC on every call, same path in every phase, needs one Keycloak instance. (B) loopback trust for single-user mode: simpler to start, a second path to secure and test. **Recommendation: A.**

## D12 to D16. From the agent-execution caller assessment (REJECTED, round 1)

Full assessment: `docs/assessments/caller-assessment-agent-execution-2026-10-25.md`.

**D12. Who launches a Worker.** (a) agent-execution owns the launch path, with a defined `launch` signature, return value and errors. (b) orchestration glue does it; agent-execution only describes the Worker. Today the spec says the Scheduler launches in step 1 and the launcher in section 7, so two owners claim the same step. **Assessment:** the launch is the core of this module; (b) moves the riskiest interface out of the module that has to test it. **Recommendation: (a).**

**D13. Signal scope.** `read_signal` returns the latest unread signal for any assignment, so parallel Workers cannot be told apart, and reading consumes the signal, so a crash between read and `complete` loses it. (a) read per hook with `hook-store find_signals(pattern, since=cursor)`: the cursor stays with the hook, nothing is consumed on read. (b) `read_signal` with `hook_path` in config: keeps today's call, still consumes. **Assessment:** (a) fixes both problems; it changes the agent-platform call. **Recommendation: (a).**

**D14. Worker time and checkpoint limits.** A.4.8 promises them, but `budget-meter` units are `tokens` or `cost` only (line 34 of its README), and nothing stops a harness at a limit. (a) add a wall-clock unit to budget-meter; the launcher stops the harness when it is reached. (b) alert only, no stop. (c) a per-harness sandbox, Phase 2. **Assessment:** (b) lets a Worker run past its limit unnoticed; (a) needs a library change. **Recommendation: (a) now, (c) in Phase 2.**

**D15. Restart or crash when a Worker stops.** The watchdog restarts on `unresponsive`; the spec's step 9 reports `crashed` to the launcher. A restart can repeat half-done work. (a) the watchdog restarts the Worker. (b) the watchdog escalates and the launcher calls `fail(retry)` on the task queue, so one owner decides. **Recommendation: (b).**

**D16. Commit prefix for signals (Open 3).** The spec lists the prefix as not set and the regex as a library default. Recommendation: one prefix list in `commit_prefixes`, with `signal_pattern` derived from it, so a future prefix change is one edit.

## D10 and D13 detail (owner asked for more before deciding)

### D10. Where the two-person check runs

**Example.** Bob's Developer agent opens change 42 for Bob. The work item records `requested_by = bob`. Carol is the Approver. Carol tries to approve change 42.

- **A. `check` does the comparison.** Verification calls `check(principal_id=carol, action="merge:approve", resource_type="change", resource_id="change-42", scope=project-a, requester_id=bob)`. Access-control sees that carol equals bob, no `merge:approve_own` holds in scope, and returns deny with reason `two_person_rule`.
- **B. Each caller compares first.** Verification checks `work.requested_by == carol` itself, and only then calls `check`. If a caller skips that line, the approval goes through.

**Consequences per caller.**
- *Verification:* A gives one call and one reason to show. B adds a rule verification must hold itself, and every new approve path (for example a Merge Queue Processor step) must repeat it.
- *Interfaces:* A adds `requester_id` to the `check` input and `requested_by` to work items. B keeps the CLI approve command as it is, but the comparison then lives in each command.
- *Orchestration:* A needs orchestration to write `requested_by` when it creates the work item. B needs nothing extra.
- *Q1 interaction (intersection rule):* if an agent acts for a user (`acting_for`), `requested_by` must be the human at the root of that chain, not the agent. Otherwise Alice can ask a Developer agent to open a change and then approve it herself: the requester would be the agent, which is not Alice, so the check allows it. Under A, access-control states this once. Under B, every caller must get it right.
- *System principal (my addition to D1):* when the Merge Queue Processor opens a request as a system principal, Carol is still a different principal, so the check passes. No change is needed.

**My assessment.** A. One rule, one place, one reason code. It also makes the acting-for root rule enforceable in one place.

**Recommendation: A**, with `requested_by` set to the root human principal.

### D13. Which signal scope the launcher uses

**What I checked.** `libs/agent-platform/README.md` section 5.3 scans the hook worktree's git log. Each Worker has its own hook, and the config already has `hook_path`. So parallel Workers are already separated by hook. The gap is the wording in section 3.4 ("the most recent unread signal for any assignment") and the consume-on-read rule in 5.3. `libs/hook-store/README.md` lists `find_signals(name, pattern, since?)`, but the README does not say what `since` means.

**Failure case that matters.** A Worker commits `[umas:done]`. The launcher reads it and marks it consumed. The launcher crashes before `complete`. On restart, the signal is gone. The task stays claimed with no outcome.

- **A. Launcher keeps a cursor.** The launcher stores the last seen commit per task and calls `find_signals(name, pattern, since=cursor)`. Reading consumes nothing. After a crash the same signal is read again. Changes agent-platform: its adapter stops consuming on read. **Open point:** the meaning of `since` (I assume a commit SHA) must be confirmed in hook-store before this is used.
- **B. Keep `read_signal(platform, config)` as it is.** Only the section 3.4 wording changes. Consume-on-read stays, so the crash case still loses the signal.

**My assessment.** A. It is the only option that survives a crash between read and `complete`. It costs one library change and one `since` definition.

**Recommendation: A**, after you confirm that `since` is a commit cursor.

## D17 to D22. Budget decisions (from the budget-and-models caller assessment, REJECTED)

Full assessment: `docs/assessments/caller-assessment-budget-and-models-2026-10-25.md`. Six decisions, numbered here as D17 to D22.

- **D17. Metering rule. Owner answer: (a).**
  Does `commit` already include usage recorded by `record`?
  - (a) Task work uses reserve and commit. `record` is only for Coordinator calls outside a task.
  - (b) `record` everything, no holds.
  - **Recommendation: (a).** It matches budget-meter section 10, so no library change.
- **D18. Worker token bound. Owner answer: (a).** D14 (a) already sets a wall-clock limit. CLI Workers report no usage, so `commit` has no `actual`.
  - (a) Time bound now; Worker tokens unbounded until harnesses report usage.
  - (b) Require every harness to report usage before Phase 1.
  - **Recommendation: (a).**
- **D19. Who sets and resumes `budget_paused`. Owner answer: (a).**
  - (a) UMAS glue sets it. A human resumes sessions. The Monitor resumes dispatch.
  - (b) The agent sets it at a step boundary.
  - **Recommendation: (a).** At 100% the agent may be stalled and unable to set anything. The 24 h timeout outcome must also be written.
- **D20. Alias names. Owner answer: (a), add `deep` to the table. Done in `libs/llm-gateway/README.md` section 3.2 (`deep` added with the same placeholder model-ID convention; no model ID hard-coded).**
  The aliases in the spec are `default` (budget-and-models 4, orchestration) and `deep` (main 1.3 and 5.7, agent-execution `architect.model`, budget-and-models line 53). `llm-gateway` section 3.2 defines only `default` and `planner`, so `deep` is undefined there. Options: (a) add `deep` to the 3.2 table (a library edit); (b) rename `deep` to `planner`, which 3.2 already defines (spec edits in four places); (c) keep `deep` only in the spec and make the Architect use `default` for now. Consequence: with (a) the library and spec match; with (b) no library change, but the name says "planner" for the Architect; with (c) the Architect loses its stronger model. My assessment: (a), because `deep` is the name the spec already uses in five places. Recommendation: (a), after you confirm.
- **D21. Permission names for budget, metrics and handoff. Owner answer: (a).**
  - (a) Add `budget:set`, `metrics:read`, `agent:handoff`, `agent:resume` to A.5.4 and A.5.6.
  - (b) Reuse `config:write`, which only Admin holds, so Project Owners could not set budgets.
  - **Recommendation: (a).**
- **D22. Who triggers a handoff at a budget threshold. Owner answer: (a).**
  - (a) The session acts at its own threshold. The Monitor is the backstop.
  - (b) The Monitor forces every emergency handoff.
  - **Recommendation: (a).**

## D23 to D30. From the orchestration caller assessment (REJECTED, round 1)

Full assessment: `docs/assessments/caller-assessment-orchestration-2026-10-25.md`. 21 gaps, 6 blockers.

- **D23. Worker budget unit (gap 3).** `admit` cannot be written: budget-meter counts tokens, and the Worker limits are not set.
  - (a) Time and checkpoint caps for Workers; tokens for coordination agents.
  - (b) Wait until each CLI's usage report is verified.
  - (c) A fixed token estimate per task.
  - **My assessment:** (a) follows D14 and D18, which are already answered. (c) is a guess the budget cannot check. **Recommendation: (a).**
- **D24. Completion owner (gap 4).** Two owners claim completion: the Scheduler (orchestration 5.2, Figure 1) and the launcher (agent-execution step 7).
  - (a) The launcher alone calls `complete`, `fail` or `release`, from the signal it reads.
  - (b) The Scheduler calls `complete` through `find_signals`.
  - **My assessment:** (a). D12 gives the launch path to agent-execution, and the launcher is where the outcome is seen. **Conflict:** context-persistence D35 recommends (b). The owner must pick one. **Recommendation: (a).**
- **D25. Grilling channel (gap 1).** The CLI is a short-lived client with a 300 s timeout, so answers cannot wait on it.
  - (a) CLI `answer` and `confirm` commands against a request id.
  - (b) REST polling.
  - **Recommendation: (a).** Needs a request id and two commands in the interfaces spec.
- **D26. P1 receiver (gap 11).** Capabilities says the Coordinator (A.5.5). Section 6.2 says System Patrol. Neither is an open item.
  - (a) Coordinator; amend 6.2.
  - (b) System Patrol.
  - **Recommendation: (a),** the same answer monitoring D40 gives. P0 goes to the Admin in Phases 1 and 2 (A.5.4).
- **D27. Meaning of DONE (gap 8).** (a) All tasks `completed`. (b) All tasks `merged`, with a `MERGING` state. **Recommendation: (b),** because verification O8 gates merge on review and tests.
- **D28. Permission names (gap 12).** Add `work:submit`, `work:read`, `work:cancel`, `work:retry`, `gate:approve` and `budget:set` to A.5.6. A.5.9 Q5 (intersection, D1) decides how `acting_for` works. **Recommendation: (a),** the named list, not one coarse `work:write`.
- **D29. Who decomposes a request (gap 6).** (a) The Coordinator, with the Architect for medium and larger work; output validated by Pydantic (ADR-0004). (b) The Architect only. (c) The user writes the tasks. **Recommendation: (a).**
- **D30. Config key (gap 16).** (a) Open 5's single key in `umas.config.yaml`, with the `default` alias (D2). (b) Keep a separate `coordinator_config` file. **Recommendation: (a).** Depends on D20 for the `deep` alias.

## D31 to D36. From the context-persistence caller assessment (REJECTED, round 1)

Full assessment: `docs/assessments/caller-assessment-context-persistence-2026-10-25.md`. 18 gaps, 7 critical.

- **D31. CLI Worker write path (gaps 1, 4, 5, 14).** §2 drives an in-process loop that A.4.8 rules out for CLI Workers, and nothing says who calls `checkpoint`, `done` or `pause` for them.
  - (a) The harness commits with raw git.
  - (b) The harness calls `umas` commands.
  - (c) The harness edits files only; the launcher makes every library call.
  - **My assessment:** (c) fits A.4.8 and keeps the launcher as the only writer, which matches D12. **Recommendation: (c).**
- **D32. Signal vocabulary (gaps 2, 3).** Two spellings: `[umas:*]` (main 5.3) and agent-session `[done]`.
  - (a) `[umas:*]` for done, checkpoint, blocked, escalated and abandoned; event types `escalate` and `handoff_request`; `severity` in `data`.
  - (b) agent-session's spelling.
  - **Recommendation: (a),** which matches D16 (one prefix list).
- **D33. Lease cadence (gap 4).** (a) The launcher timer renews the hook and task leases every 100 s, TTL 300 s. (b) A heartbeat at each step boundary, with a TTL above the longest step. **Recommendation: (a).** Note the Worker heartbeat in monitoring D42 is 60 s; the two must agree (see conflicts below).
- **D34. `PAUSE.md` and `HANDOFF.md` lifecycle (gap 6).** Today they are never retired, and `recover` reads `PAUSE.md` first, so a later crash can resume from an old pause. (a) Delete on resume. (b) Archive and commit on resume. **Recommendation: (b),** so `recover` reads only current files.
- **D35. Completion owner (gap 7).** Recommends the Scheduler owns `complete`; the launcher only reports. **Conflict with D24 (a).** The owner must pick one.
- **D36. Permission names (gap 15).** Accept Open 17 (`hook:create`, `hook:commit`, `worktree:recover`, `worktree:clean`) and have access-control add them. **Recommendation: yes.**

## D37 to D42. From the monitoring caller assessment (REJECTED, round 1)

Full assessment: `docs/assessments/caller-assessment-monitoring-2026-10-25.md`. 18 gaps, 4 critical.

- **D37. Worker liveness (gap 1).** Workers are external CLIs and write no heartbeat, so "no heartbeat for 5 minutes" cannot be applied.
  - (a) Commit age only.
  - (b) The launcher writes a heartbeat file; commit time measures progress.
  - (c) The hook-store lease.
  - **My assessment:** (a) cannot tell a silent Worker from a thinking one. (b) costs one file write, and the launcher already runs a timer for D33. **Recommendation: (b).**
- **D38. Recovery arbiter (gap 4).** Lease expiry, the watchdog restart and the Monitor handoff can all act on one dead Worker.
  - (a) Scheduler.
  - (b) Monitor.
  - (c) Watchdog.
  - **Recommendation: (a),** where the Monitor detects and emits, the watchdog stops the process, and only the Scheduler starts a successor. **Conflict:** D15 (a) answered that the watchdog restarts the Worker. Under D38 (a), the watchdog stops it and only the Scheduler restarts it. The owner must confirm which applies.
- **D39. 95% trigger for CLI Workers (gap 8).** (a) The session acts at its own threshold. (b) The Monitor. **Recommendation: (a)** where usage is visible. For CLI Workers, the time and checkpoint limits apply, with `request_graceful` and a `handoff_request` event. This matches D22 and D23.
- **D40. Severity table (gap 6).** Recommendation: a Triage or Patrol crash loop is P0; an exhausted Worker ladder is P1 to the Coordinator; P0 goes to the Admin in Phases 1 and 2, and to the Operator from Phase 3. Consistent with D26.
- **D41. Write authority (gap 5).** (a) Monitors get write permissions. (b) The Coordinator acts on `escalate`. **Recommendation: (b),** which keeps A.5.5 read-only. Add `agent:nudge`, `agent:stop` and `agent:restart`.
- **D42. Defaults (gap 11).** Recommendation: Triage heartbeat 180 s with `miss_threshold: 2`; 5 restarts in 600 s; `kill_grace` 10 s; Worker heartbeat 60 s, 5 misses; 60 s per ladder rung; run folder `.umas/run/`. One answer accepts or changes the set. **Conflict:** the Worker heartbeat (60 s) must match the lease timer under D33 (100 s).

## D43 to D48. From the verification caller assessment (REJECTED, round 1)

Full assessment: `docs/assessments/caller-assessment-verification-2026-10-25.md`. 22 gaps, 8 blockers.

- **D43. Approval and ready status (O7, O8; gaps 2, 3).** (a) Approve before `submit`; orchestration sets `ready_to_merge`. (b) An approval hook inside the queue run; breaks the library's no-approval non-goal. (c) Approve after verify; holds a verified batch and risks `target_moved`. **Recommendation: (a),** with approval bound to a SHA.
- **D44. Pinned SHA (gap 4).** (a) Submit a SHA; a fix is a new candidate. (b) Compare the SHA at batch time (needs a library hook). (c) Keep the branch; unreviewed code can merge. **Recommendation: (a).** No library change, and each new SHA is re-reviewed. Relates to O11 (`ref` resolved at batch time).
- **D45. Verify faults and flakes (O2 to O4; gaps 8 to 10).** (a) A wrapper maps JSON `status` to exit codes. (b) Library change: exit 0 green, 1 red, other codes halt as `verify_error`. (c) Keep blame as today. **Recommendation: (b),** with `retry_failed` 0 in verify and `rerun_on_fail` 1. **Consequence:** (b) changes the exit-code contract (AXI open point 2).
- **D46. Owner of the glue (O9, O13; gaps 6, 12).** (a) A plain processor under the service manager (A.4.8) that runs the loop and writes `merged`, `blocked`, `baseline_red` and `escalate` events. (b) Orchestration's Scheduler calls `run_once` on its tick; ties dispatch to a blocking call. **Recommendation: (a).** It becomes a service principal, which access-control gap 8 needs.
- **D47. Permission names (O14, O15; gap 14).** (a) Adopt the access-control seed list and name every action. (b) One coarse `merge:approve`; an approve grant then covers target writes. **Recommendation: (a).** Under D1 the processor runs as a named system principal, so A.5.9 Q5 applies to it.
- **D48. Re-entry (O24; gap 13).** (a) Cap review rounds with a counter; re-enter only through review. (b) Allow `requeue` straight to the queue; skips review. **Recommendation: (a),** plus a library reset that clears `attempts`.

## Confirmations requested (2026-10-25)

These six items were asked for in detail. Each has a recommendation; the owner confirms or changes it.

**1. D10: two-person check location.** Recorded in the D10 section above.
- A: `check` takes `requester_id` and returns `two_person_rule`; work items carry `requested_by`, set to the root human when an agent acts for a user.
- B: each caller compares `requested_by` with the approver before `check`.
- **Recommendation: A.** One rule in one place.
- **Needs from you:** A or B.

**2. D13: signal scope and `since`.**
- A: the launcher stores a cursor and calls `find_signals(name, pattern, since=cursor)`. Nothing is consumed on read, so a crash after the read loses no signal.
- B: keep `read_signal`, which consumes on read.
- **What I checked:** `libs/hook-store/README.md` lists `find_signals(name, pattern, since?)` in its operation table, but never defines `since`. `libs/agent-platform/README.md` section 5.3 records "the last-seen commit SHA" for `read_signal`. So a commit cursor is the likely meaning. It is not confirmed in the hook-store spec.
- **Recommendation: A**, with `since` defined in `libs/hook-store/README.md` as "return commits after this commit SHA". That is a library edit.
- **Needs from you:** A or B, and confirm that `since` is a commit SHA cursor.

**3. D17 to D22: budget decisions.** Recorded as (a) in your last answer:
- D17 metering: reserve and commit for task work; `record` only for Coordinator calls outside a task.
- D18 Worker bound: a wall-clock limit now; tokens unbounded until harnesses report usage.
- D19 `budget_paused`: UMAS sets it; a human resumes sessions; the Monitor resumes dispatch.
- D21 permission names: `budget:set`, `metrics:read`, `agent:handoff`, `agent:resume` added to A.5.4 and A.5.6.
- D22 handoff trigger: the session acts at its own threshold; the Monitor is the backstop.
- **Needs from you:** confirm these are still (a). Nothing is changed in the specs yet.

**4. System principal for user-less work (my addition to D1). Owner answer: ok with the principal. Ease of setup: see the proposal below.**

*Proposal for setup (not yet confirmed):* one `service_principals` list in `umas.config.yaml`, one entry per background process. Each entry names the process and its role, for example `{name: svc:patrol, role: patrol}`. `umas init` creates each principal and its role binding from that list. No permission is written by hand. Adding a process means adding one line and running `umas init` again, which is idempotent. A fixed table in access-control gives the default role for each built-in process (Patrol, Watchdog, Merge Queue Processor, boot recovery), so a default install needs no edit. `umas access show` lists every principal and its permissions for review.
- Consequence: the default config works without edits; a custom process needs one line and one role.
- Risk: a custom process given a broad role is broad. The role table is the control, so it is reviewed once.
- **Rule:** work with no requesting user (Patrol, Watchdog, boot recovery, the merge processor under D46) runs as a named service principal (`kind = service`, A.5.2) with only its own role's permissions, never wider. The intersection rule (D1) does not apply to it, because there is no user to intersect with.
- **Why:** without it, D1 has no answer for background work.
- **Consequence:** each background process needs its own service principal and role binding. Access-control must list them in its Phase 1 seed.
- **Risk:** the rule is only as narrow as the role. A broad role gives a broad service principal.
- **Recommendation:** confirm. Name each principal after its process (for example `svc:patrol`).
- **Needs from you:** confirm, or say what should apply instead.

**5. D5 reversal: anti-slop criterion 2. Owner answer: (c). Done in the scripts; see the D5 row in the owner answers table.**
- **Current rule (your 2026-10-25 decision):** criterion 2 stays as written. A name removed with a deleted fact-free sentence counts as dropped. F1 fails because the name "AI" disappears with the sentence.
- **Option (a):** keep the rule. F1 fails; the pack stays `[-]`.
- **Option (b):** change the F1 input so the name survives. Changes a fixture to pass a test, which the F8 lesson argues against.
- **Option (c), my recommendation:** relax the rule. A name that appears only in a removed fact-free sentence does not count as dropped.
- **Risk of (c):** the reviewer could delete a real name along with slop and the test would not catch it. The rule exists to catch that.
- **Effects if confirmed:** update the criterion in `docs/tasks-skills-claude-mods-2026-10-25.md`; re-review F3; re-run tests. Anti-slop stays `[-]` until they pass.
- **Needs from you:** confirm (c), or keep (a).

**6. D20: `deep` alias.** Done: option (a) was given and `deep` was added to `libs/llm-gateway/README.md` section 3.2, with the same placeholder model-ID convention. No model ID is hard-coded. **Nothing more needed unless you want option (b) or (c) instead.**

## Details for the open confirmations (2026-10-25, round 3)

### C1. D13: is `since` a commit SHA cursor? (A or B)

**What the specs say.**
- `libs/hook-store/README.md` section 4 lists `find_signals(name, pattern, since?)`. `since` is never defined. Section 5.2 says `find_signals` matches the subject line and trailers, and says nothing about order or a cursor.
- `libs/agent-platform/README.md` 5.3 says `read_signal` "records the last-seen commit SHA". That mark belongs to agent-platform, not to hook-store.
- Name risk: git's `--since` means a date. A reader can take `since` as a timestamp.

**Option A: cursor by commit.** The launcher stores the last commit it has seen per task and calls `find_signals(name, pattern, since=cursor)`. Nothing is consumed on read.
- Edit hook-store section 4 and 5.2 to define the argument: "returns commits after this commit, oldest first; absent means the whole log". Implemented as `git log <sha>..HEAD`.
- Consequence: agent-platform's commit-message path (5.3) is no longer used by the launcher. Its consume-on-read rule then applies only to file and polling signals. agent-platform 3.4 promises one return shape for every harness, so the adapter must keep it.
- Open point: where the cursor is stored. Recommendation: the hook's `STATE.md` through `write_state`, so it moves with the hook and survives a crash.

**Option B: keep `read_signal`.** It consumes on read. A crash after the read and before `complete` loses the signal.

**My assessment.** A. It is the only option that survives a crash, and it is one library edit.

**Recommendation: A, with the argument renamed to `after` (value: a commit SHA).** The rename removes the date reading.

**Needs from you:** A or B. If A, confirm the `after` rename.

### C2. D17 to D22: budget decisions, (a) still stand?

Checked against `libs/budget-meter/README.md` 5.2: "`commit` always records the **true** amount". Section 10 says the old design double counted usage by adding actual on top of the hold. The (a) answers follow from that.

| Decision | (a) means | Consequence | Risk |
|---|---|---|---|
| D17 metering | Task work uses `reserve` then `commit`. `record` only for Coordinator calls outside a task. | `budget-and-models` step 5 must not run inside a task. The rule must be written into that spec. | A coordination call made inside a task and recorded by mistake is counted twice. |
| D18 Worker bound | Wall-clock limit now (D14 A). CLI Workers report no usage, so their tokens are not counted. | Workers have no token cap. Token thresholds apply to coordination agents only. | Worker spend is capped only by time, which bounds cost roughly. Revisit once harnesses report usage. |
| D19 `budget_paused` | UMAS glue sets it. A person resumes sessions. The Monitor resumes dispatch. | Resolves the conflict: budget-and-models section 2 and 6.6 say the agent sets it; budget-meter 9 and agent-session 9 say UMAS does. Both specs need editing. The 24 h timeout outcome is still unwritten. | The agent may be stalled when the budget hits 100%, so it cannot set the status itself. |
| D21 permission names | Add `budget:set`, `metrics:read`, `agent:handoff`, `agent:resume` to A.5.4 and A.5.6. | Other assessments propose more names: `agent:nudge`, `agent:stop`, `agent:restart` (monitoring D41), `work:*` and `gate:approve` (orchestration D28), `hook:*` (context-persistence D36). | Names come from five assessments with no single list. Access-control should own one list. |
| D22 handoff trigger | The session acts at its own threshold. The Monitor is the backstop. | The session must know its own threshold from agent-session config. Matches monitoring D39. | If a session stalls, only the Monitor acts, and it acts late. |

**Recommendation:** confirm all five as (a). Access-control then owns one permission list for D21 and the names in the other assessments.

**Needs from you:** confirm each, or name the ones to change.

### C3. System principal setup: how to make it easy

**What the specs say.**
- A.5.2 (main spec, RBAC table): a service account is a long-lived key in a secret store, rotated on a schedule.
- A.5.7 and access-control 116: a service account gets its token from a Keycloak client credentials grant.
- A.5.6: permissions are seeded by code; roles, bindings and principals are data. Creating principals from config matches that.
- A.5.4 matrix already has one role row per background process: Merge Queue Processor (row 1646), Monitor for Triage, Patrol and Project Monitor (row 1647), Watchdog (row 1648).

**The proposal.**
1. Built-in principals need no config. `umas init` creates one service principal per built-in process, with the default role from the A.5.4 matrix.
2. A `service_principals` list in `umas.config.yaml` is optional. It is needed only for a custom process: one line, `{name: svc:<process>, role: <role>}`.
3. `umas init` is idempotent. `umas access show` lists every principal and its permissions for review.

**Consequences I had not stated before.**
- Under D9 (A) every request calls Keycloak, and D11 (A) puts every call on OIDC. So each service principal also needs a Keycloak client. `umas init` must create those clients, which needs a Keycloak admin credential. That credential is a new secret to protect.
- Boot recovery has no row in the A.5.4 matrix. I propose the Watchdog role for it. That needs your confirmation.
- Whoever edits `service_principals` changes who can do what. That edit must require `config:write`, which only Admin holds.

**Options.**
- (A) Config list for every process, including built-ins.
- (B) Built-ins created by `umas init` with no config; the list is added only for custom processes.

**My assessment.** B. Phase 1 has no custom processes, so the list would be empty. B also keeps the Keycloak client count to the built-in set.

**Recommendation:** B, with the Watchdog role for boot recovery.

**Needs from you:** A or B, and confirm the boot recovery role.

### C4. F3 re-review (anti-slop criterion 4, and criterion 5)

**What happened.** In run 2, the reviewer kept "at scale" and flagged it, instead of removing it (`fixtures/RESULTS.md` lines 20 and 52). Rule 3 says to remove a vague phrase when its sentence keeps every fact, so the reviewer did not follow the rule. Its flag asks the author to name the scale. Run 2 also changed F3 on the second pass, which fails criterion 5.

**Two facts that limit the evidence.**
- `RESULTS.md` says one run is evidence, not a measurement. Model output varies between runs.
- The judge was the pack author, so the verdicts are not independent (`RESULTS.md` line 8).

**Options.**
- (a) One fresh reviewer run on F3, plus its second pass, then re-run the tests. Cheapest. A single pass can happen by chance.
- (b) Three fresh runs on F3, each with a second pass. Pass if at least two runs meet criteria 4 and 5. More evidence. Six reviewer calls.
- (c) Change `PACK.md` so a phrase listed in `phrases.yaml` is always removed. This is a prompt change made after a failing result. The F8 lesson applies: repeated tuning on a fixture weakens it.

**Rules for any option.** `PACK.md` and the F3 input stay unchanged. The old outputs are kept as `F3.run2.json` so the record stays intact. The judge is a fresh agent, not the author.

**My assessment.** (b). It gives a result that does not depend on one run, and it avoids changing the prompt after a failure.

**Recommendation:** (b), with a fresh judge.

**Needs from you:** (a), (b) or (c). Nothing has been run yet.

## Owner answers, round 4 (2026-10-25)

| # | Answer | Effect |
|---|--------|--------|
| C1 (D13) | A: the launcher keeps a cursor and calls `find_signals`. I used the name `after` (a commit SHA) as recommended; you did not object to the rename | `libs/hook-store/README.md` defines `after`; `libs/agent-platform/README.md` commit-message path stops consuming on read; agent-execution revision uses it. Cursor stored in the hook's `STATE.md` |
| C2 (D17 to D22) | Budgets are in money, not tokens, because a token cap depends on the model. Realigned below | `budget-and-models` and `libs/budget-meter/README.md` use `unit: "cost"`; tokens stay in the ledger as detail |
| C3 | B: `umas init` creates a service principal for each built-in process; the `service_principals` list only for custom processes | access-control revision. Boot recovery role (Watchdog) not objected to; recorded as proposed |
| C4 | B: three fresh F3 runs, each with a second pass, fresh judge, pass if at least two of three meet criteria 4 and 5 | Runs started. Old run kept as `outputs/runs/F3.run2.*` |

### C2 realigned: budgets in money

**Principle.** A budget limit is an amount of money (one currency per budget). The meter computes the cost of each call from the reported usage and a price table that lives in configuration (`budget-meter cost(usage, price_table)`; budget-meter already allows `unit: "cost"`). Token counts stay in the ledger as detail. They are never the cap. Changing a model changes the price table, not the budget.

| Decision | Realigned answer | What changed from (a) |
|---|---|---|
| D17 metering | Task work uses `reserve` then `commit`, in money. The estimate is a money amount from a per-role cost estimate in config. `actual` is the cost computed from reported usage. `record` only for Coordinator calls outside a task, also in money | Unit is money, not tokens. The double-count rule is unchanged |
| D18 Worker bound | CLI Workers report usage only where the harness does. Where it reports, the cost is computed and committed. Where it reports nothing, `commit` records the reserved estimate, not zero, so the budget never undercounts. The wall-clock cap (D14 A) stays as the backstop. **Proposed, not decided: needs your confirmation** | Replaces "Worker tokens unbounded". A Worker without a report is charged its estimate |
| D19 `budget_paused` | Unchanged: UMAS sets it, a person resumes sessions, the Monitor resumes dispatch. Thresholds are percentages of the money limit | Unit only |
| D21 permission names | Unchanged: `budget:set` (sets a money limit), `metrics:read`, `agent:handoff`, `agent:resume` | `budget:set` carries a currency amount; the owner cap is a money value |
| D22 handoff trigger | Unchanged owner (the session acts at its own threshold, the Monitor is the backstop). **Open point:** the 90% and 95% handoff thresholds in the source are about the context window, which is measured in tokens and differs by model. That is not the spend budget. Keep the two apart: spend thresholds in money, context-window thresholds in tokens read from the model's limit in config. **Needs your confirmation** | Separates two things the spec had under one word, "budget" |

**What stays token-based and why.** The context window of a model is a size limit in tokens. It cannot be expressed in money. Packing context (`budget-meter pack`) therefore still counts tokens.

## D17, D18, D22 detail for the money realignment (round 5, 2026-10-25; owner asked for more before deciding)

Current state of the libraries (checked 2026-10-25):
- `libs/budget-meter/README.md` already has `unit: "tokens"|"cost"` (section 3.1). `cost(usage, price_table)` multiplies token classes by per-model rates from a table the caller supplies; no prices are embedded (section 3.2 and 5.x).
- `reserve` holds an estimate; `commit` replaces the hold with the actual amount; holds expire after `reservation_ttl_seconds: 900`.
- `libs/llm-gateway/README.md` `on_usage` fires per attempt with `{alias, provider, model, usage}`, so cost can be computed per call from the model alias.
- `libs/agent-session/README.md` sets `token_limit`, `handoff_threshold` 0.90 and `emergency_threshold` 0.95 as fractions of tokens. These are context-window thresholds, not spend.
- Workers are external CLI harnesses that bypass the gateway and report no usage (agent-execution A.4.8).

### D17. The money basis for budgets

**Option A (recommended): money is the budget unit.** A budget limit is an amount in one currency. Each call's cost = usage × the price-table rate for its model alias. Tokens stay in the ledger as detail.
- Consequence: changing a model changes its price-table entry, not the budget. A cap of 50 money units means the same spend whichever model runs.
- Consequence: the price table must be right. A stale price misstates spend with no error, so it needs the version rule below.
- Consequence: `budget-meter` changes are small. `unit: "cost"` exists; the price table is passed in from config.

**Option B: keep tokens as the unit.** The cap in tokens, as now.
- Consequence: a cap of 2 million tokens is a different amount of money on each model. This is the problem you raised, so I do not recommend it.

**Option C: money for the period budget, tokens for sessions.** Money for daily project caps, tokens for session handoff.
- Consequence: this matches the context-window need (D22) but leaves one per-session cap that still moves with the model. It is a fallback if D22 is not accepted.

**Price-table version rule (the mitigation you asked about).**
1. The price table is config data: `{version, as_of, currency, models: {<alias>: {input, output, cached}}}`, with rates per million tokens.
2. Each commit or record writes the table `version` used into its ledger line. Ledger history is never rewritten. A price change is a new version, applied from the next call.
3. `cost()` fails loudly on an alias with no price. It never returns zero for an unknown model.
4. `budget-meter status` warns when the table's `as_of` is older than a set number of days (proposed: 90; a value you choose).
5. A test checks that every alias in `libs/llm-gateway/README.md` section 3.2 has a price.
- Consequence: old spend stays explainable after a price change. A missing price stops a call rather than under-counting it.
- Limit: the rates themselves are a human-maintained input. The rule detects gaps and staleness, not wrong numbers.

### D18. Worker spend when the harness reports no usage

The Worker runs in an external CLI harness. Under A.4.8 it reports no usage, so the `actual` in `commit` does not exist.

**Option A (recommended): reserve the estimate, and commit the actual cost only if a usage report exists.** The estimate is a per-role money amount in config, reserved at admission. If the harness reports usage, the cost computed from it replaces the hold. If not, the estimate is committed as the charge. The D14 wall-clock cap stays as the stop.
- Consequence: admission is controlled, because `reserve` fails when headroom is short. Spend is an estimate per task, not a measure.
- Consequence: an estimate that is too low undercounts; one that is too high blocks work early. Both are visible in `status`, and the estimate is adjusted in config.
- Limit: Worker spend is bounded by (estimate × admitted tasks), and each task by wall-clock time. It is not bounded by a measured amount.

**Option B: flat money per wall-clock minute, per harness.** Charge = elapsed minutes × a configured rate. Committed when the Worker ends.
- Consequence: simple and predictable; it needs no usage data. It is a guess about cost per minute and does not vary with the work.
- Consequence: a fast, expensive task and a slow, cheap one are charged the same per minute. The rate must be re-set when a harness or plan changes.

**Option C: wall-clock cap only, no money charge for Workers.** D14 time limits stop runaway Workers; the money budget covers only UMAS's own calls (Coordinator, Router, Triage, Patrol, Monitors).
- Consequence: the largest consumer of spend is outside the money cap. The budget then reports money for only a minority of work.
- Consequence: no estimate or rate to maintain.

**My assessment.** A and B both guess a Worker's cost, but A gives an exact figure whenever a harness reports usage (a later Phase 1 change), and needs no rewrite then. B gives a steady figure that is easy to explain. C is simplest but leaves most spend unmetered, which defeats the budget. I recommend A and a clear statement in the spec that Worker money is an estimate until harnesses report usage.

### D22. Thresholds: one set or two

**Option A (recommended): two thresholds with two names.**
- `spend_thresholds` (money, as a fraction of the money limit; default 0.80, 0.90, 0.95 from budget-meter). These trigger warnings and `budget_paused`.
- `context_threshold` (fractions of the model's context window, in tokens, read from the model's limit in config). These trigger handoff. This replaces `token_limit` in agent-session, which currently means "max tokens this session may use".
- Consequence: a handoff fires when the context is full, which is what a handoff is for.
- Consequence: two config keys to explain. The names must not be mixed.

**Option B: one set of thresholds, percent of the money limit, drives handoff too.**
- Consequence, concrete failure: a session on a cheap model fills its context with little money spent. The money threshold never fires, so no handoff happens and the context overflows.
- Consequence: a session on an expensive model hands off early while its context is still small.
- I do not recommend it.

**Option C: one set of token thresholds for both, as now.** Keeps the money cap in tokens, which is what D17 removes.
- Not compatible with D17.

**My assessment.** Handoff is a property of the context window, which is a token figure per model, so its trigger must be tokens. The budget is money. They are two different things and need two names.

### Effect on other specs if these are accepted
- `budget-and-models`: spend thresholds in money; period threshold list changes from `[0.80, 1.0]` to the budget-meter set; the session budget and handoff are split as above.
- `orchestration` gap 3 (admit estimate in tokens): the estimate becomes money.
- `agent-session`: `token_limit` becomes `context_limit` taken from the model's window; the handoff thresholds stay as fractions of it.
- `llm-gateway`: `on_usage` feeds `cost()`; no change to the callback shape.

### Owner answers, round 5 (2026-10-25)

| # | Answer | Effect |
|---|--------|--------|
| D17 | **Money** is the budget unit. Tokens stay in the ledger as detail. The price-table version rule (five points above) is part of this decision | `budget-and-models` and `libs/budget-meter` use `unit: "cost"`; `cost()` fails on a missing alias; ledger lines record the price-table version |
| D18 | **A.** Reserve the per-role money estimate; commit the cost computed from the harness's usage report if one exists, otherwise commit the estimate. D14 wall-clock cap stays | Worker spend is an estimate until harnesses report usage; the spec says so |
| D22 | **A.** Two thresholds, two names: `spend_thresholds` (money, 0.80 / 0.90 / 0.95) trigger warnings and `budget_paused`; `context_threshold` (tokens, fraction of the model's context window) triggers handoff and replaces `token_limit` in agent-session | `budget-and-models`, `agent-session`, `libs/agent-session` change |

**Not answered, default chosen:** the staleness window N for the price table `as_of` warning. I used 90 days. Change it in config if you want another value.

### Decisions needed
None from D17, D18 or D22. Still open: the D23 to D48 batch, I-1 to I-4 (interfaces), and the boot-recovery role.

## D22a. Which threshold pauses a budget (correction to round 5, needs your answer)

My round-5 wording for D22 said the spend thresholds (0.80 / 0.90 / 0.95) "trigger warnings and `budget_paused`". The budget-and-models revision found that D19 and flow 6.6 pause work only at 100% (`exhausted`). The two statements conflict.

**Option A (recommended): pause only at 100%.** The 0.80, 0.90 and 0.95 thresholds warn (Monitor and owner notice). At 1.0, `reserve` defers and the glue sets `budget_paused`.
- Consequence: work runs until the money limit is used, which is what a cap means. A warning at 0.95 gives the owner time to raise the limit before pause.
- Consequence: matches D19 and flow 6.6, so no flow changes.

**Option B: pause at 0.95.** The emergency threshold also pauses.
- Consequence: an agent in mid-step is paused at 95% of the cap, leaving unused budget that the owner must free by raising the limit or waiting.
- Consequence: needs a change to D19 and flow 6.6.

**Option C: pause at 0.90.** Same consequences as B, earlier.

**My assessment:** A. The 95% warning already gives the owner a chance to act. Pausing earlier only adds an interruption without a clear benefit.

Answer A, B or C.

## From the exception-flows caller assessment (REJECTED, round 1)

Full assessment: `docs/assessments/caller-assessment-exception-flows-2026-10-25.md` (17 gaps). Six decisions, numbered E1 to E6.

**E1. Unclean shutdown (Open 2).** Options:
- (a) Resume from `STATE.md` when clean; treat as crashed (6.8) when dirty.
- (b) Always treat a restart as crashed. Issue #6 stays unsolved.
- (c) Always resume from `STATE.md`. Can overwrite work.
- Consequence: (b) loses work that a clean pause saved. (c) can overwrite uncommitted work after a crash.
- **Recommendation: (a)**, closest to agent-session 5.6.

**E2. Who handles P1 (Open 1).** Options:
- (a) Coordinator for all P1 flows. It cannot act on a project that has vanished (6.2).
- (b) System Patrol for all. Contradicts A.5.4.1.
- (c) Per flow: Coordinator for 6.7 and 6.9, System Patrol for 6.2.
- **Recommendation: (c).**

**E3. Detection owners (Open 9, 10, 12).** Options:
- (a) Daemon tick for disk; API for database (A.4.6); agent-execution for provider errors; the watchdog stall rule for CLI Workers, with the CLI Worker limit stated.
- (b) Unowned, so the flow has no trigger.
- Consequence: (b) leaves 6.12, 6.16 and CLI-Worker 6.7 with no way to start.
- **Recommendation: (a).**

**E4. Shared recovery flow 2.2.** Options:
- (a) Normative. Needs 17 error codes that error-classifier does not supply.
- (b) Informative. Each flow's own rules win.
- **Recommendation: (b).** It avoids inventing codes and resolves the ambiguous-vs-ENOSPC conflict in favour of the flows.

**E5. Boot auth check (access-control Open 11).** Options:
- (a) Validate the agent credential at boot; the human token gates human commands.
- (b) Keep OIDC as written; most boots end as `auth_expired`.
- **Recommendation: (a)**, once access-control sets the credential lifetime.

**E6. Pause files.** Options:
- (a) The resumer deletes `.pause`; `recover()` consumes `PAUSE.md`; a deliberate pause gets its own status.
- (b) Leave unstated; stale files cause false clean pauses.
- **Recommendation: (a).**

Answer E1 to E6 with a letter each, or accept all recommendations.

## From the interfaces caller assessment (REJECTED, round 1)

Four items that no earlier decision covers. The interfaces assessment also lists 23 findings; the rest are in `docs/assessments/caller-assessment-interfaces-2026-10-25.md`.

**I-1. Break-glass access when Keycloak or the daemon is down (D9 follow-up).**
- Options: (a) no break-glass: a Keycloak outage stops every command; (b) a narrow local allow-list, read-only commands plus `umas access show` and the recovery commands, usable only from the host's own shell with an audited local flag; (c) a local root-only override with no restriction.
- Consequence: (a) is simplest but leaves an operator unable to stop a runaway agent during an outage. (c) removes the permission model during the outage, so it is not acceptable under the D8 audit rule.
- Recommendation: (b), with the allow-list written in the access-control spec and every use written to the audit log.

**I-2. Long-running operations and their status.**
- Options: (a) block the CLI until done; (b) return a job id for `update --now`, `stop-all`, `worktrees recover` and `cleanup`, with `umas job show <id>`; (c) make them asynchronous with no status command.
- Consequence: (a) times out on slow operations; (c) leaves a human unable to tell whether a command finished.
- Recommendation: (b).

**I-3. Retry safety for create commands.**
- Options: (a) no key, a retry can create a duplicate; (b) an optional idempotency key on create commands only; (c) a key on every mutating command.
- Consequence: (a) is simplest but a network retry duplicates work items. (c) adds parameters no one needs for `set` or `release`.
- Recommendation: (b).

**I-4. Source of truth for result types.**
- Options: (a) hand-written JSON schemas; (b) Pydantic models in code, with the OpenAPI document generated from them; (c) hand-written OpenAPI, with Python types checked against it.
- Consequence: (a) and (c) drift from the code. (b) matches ADR-0004 (Pydantic v2).
- Recommendation: (b).

## Conflicts between assessments that need one answer

1. **Completion owner:** D24 (launcher) vs D35 (Scheduler).
2. **Restart:** D15 (a) (watchdog restarts) vs D38 (only the Scheduler starts a successor).
3. **Worker heartbeat:** D42 (60 s) vs D33 (100 s lease renewal).
4. **P0 receiver:** D40 (Admin in Phases 1 and 2) and D26 (Operator or Project Owner, A.5.4) need one wording.

## Not decisions, blocked on work in progress

- Batch-1 library builds: do not start until the caller assessments accept the specs (CLAUDE.md 2a).
- Link and anchor re-check across the module specs: after S4, S7, S9 exist (S11).
