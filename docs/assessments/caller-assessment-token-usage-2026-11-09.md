# Caller assessment: token usage (ADR-0005 revision)

> **Date:** 2026-11-09 · **Round:** 1 · **Assessor:** caller assessor (devil's advocate; no spec was edited)
> **Scope:** [libs/token-ledger/README.md](../../libs/token-ledger/README.md) and [umas/modules/models-and-usage/models-and-usage-spec.md](../../umas/modules/models-and-usage/models-and-usage-spec.md)
> **Decision under review:** [ADR-0005](../decisions/ADR-0005-track-token-usage-only.md) (settled; not reopened)
> **Callers checked:** orchestration, agent-execution, context-persistence, monitoring, interfaces, llm-gateway, agent-session (9.5 / 5.x), metrics-store, TECHNICAL-DESIGN-SPEC (5.6 and the flow map), plus agent-platform (CompletionSignal), access-control (permission rows) and exception-flows (6.6, 6.7) where a caller depends on them.

## Verdict

**Rejected.** There are **7 blockers**. Each is a missing or contradictory contract that a caller depends on. Revise the two specs and the named caller lines, then run round 2 on the blockers only, with a fresh subagent.

## Answers to the five checks

| Check | Result |
|-------|--------|
| Calls match a spec signature | Mostly yes. `record(model, tokens, ts?)` matches in llm-gateway (line 161), models-and-usage (lines 114, 171), agent-execution (line 174) and token-ledger 4. `ingest_token_ledger(ledger_path, since?)` matches in models-and-usage (line 231) and metrics-store (line 129). Error names `InvalidEntry`, `LedgerUnreadable`, `LockTimeout`, `ConfigError` and `ProviderExhausted` are used consistently. Gaps: `check()` returns a `Report` with no fields defined (token-ledger line 59); the write-failure error is not named (M8); `umas metrics tokens` has two data paths (m5). |
| Failure paths with an owner | Several have no owner or no mechanism: ledger write failure (M8), launcher crash after a harness run (M9), an exception raised by the `on_usage` callback (M7), handoff failure at the emergency threshold (M10), ledger file growth (M6), corrupt-line surfacing (m6), and the Monitor's 95 % check for a session it cannot read (M2). |
| Budget, pause, reservation, cost or price wording left in callers | No live budget, reservation, cost or price rule remains. Every hit is a "Removed (ADR-0005)" row. One contradiction remains: models-and-usage line 179 removes "the pause signal", but four callers still use the `.pause` shutdown signal (B7). |
| Thresholds match between agent-session and models-and-usage | Values match: `handoff_threshold` 0.90 and `emergency_threshold` 0.95 (agent-session lines 75-76, 327-328; models-and-usage lines 187-188). Both use `>=` (agent-session lines 198, 202). `context_limit` does **not** match: its key and default differ across four specs (B4). The monitoring spec uses `>` (monitoring line 32; Open 18 at line 241). |
| Open decisions stated | Several are not stated where they bite. They are listed in the last section. |

## Blockers

### B1. The `model` value that goes into the ledger is contradictory

- `libs/llm-gateway/README.md:161`: "`on_usage` -> `token-ledger.record(model, tokens)`. `model` = the payload's `alias`."
- `umas/modules/models-and-usage/models-and-usage-spec.md:114`: "The `on_usage` glue calls `record(model, tokens)` when `usage` is present, using `model` from the payload."
- The payload has both fields: `libs/llm-gateway/README.md:77` gives `{alias, provider, model, usage, latency_ms, outcome}`. `model` is the provider's name and `alias` is the gateway alias.
- `libs/token-ledger/README.md:41` accepts either: "The llm-gateway alias, or the model name the provider reports."

**Failure scenario.** A Coordinator call through the `default` alias on a provider model `claude-x` is written as `default` by one reading and `claude-x` by the other. `token-ledger totals --group-by model` and `umas metrics tokens` then show one model as two rows. Harness runs add a third form, a CLI-reported name (see B2).

**Fix.** Choose one meaning. Recommended: `model` is always the llm-gateway alias for gateway calls, and the launcher's alias for harness runs (models-and-usage Open 23). Then change llm-gateway line 161 to match, change models-and-usage line 114 to "`model` = the payload's `alias`", and change token-ledger line 41 to "the alias only". The provider's model name is not stored in v1. Also fix token-ledger line 151, which says "after each successful call" (see m1).

### B2. The harness record path has no source for `model` or for a total

- `umas/modules/agent-execution/agent-execution-spec.md:174`: "the harness's reported total tokens and model (CompletionSignal `token_usage?`)".
- `umas/modules/models-and-usage/models-and-usage-spec.md:120`: record "if the harness reported a total and a model".
- `umas/modules/models-and-usage/models-and-usage-spec.md:170`: "Total tokens and model, when the CLI reports them. Format not checked (Open 3)".
- `libs/agent-platform/README.md:85-95`: `CompletionSignal` has no `model` field. Line 92 is `token_usage: TokenUsage? # { input, output, cached } — best-effort`. Nothing defines `TokenUsage` as a total.

**Failure scenario.** The launcher gets a `CompletionSignal` with `token_usage = {input: 1200, output: 300, cached: 9000}`. It has no `model`, and the spec has no rule for the total. Each implementation picks a different number: 1500, 10500 or nothing. The spec calls this an unchecked format (Open 3), but the contract already exists and it lacks both fields.

**Fix.** Two spec edits. In agent-platform, add `model` (or define that the launcher supplies the alias, per Open 23) and state the total rule, for example `input + output`, with cached tokens excluded as in llm-gateway line 161. In models-and-usage, replace "Format not checked (Open 3)" with the agent-platform field names. Keep Open 3 only for CLIs that report no usage.

### B3. The handoff trigger input `context_tokens` has no defined source

- `libs/agent-session/README.md:94`: `context_tokens: int # tokens in the context window after this step's LLM call`.
- `libs/agent-session/README.md:198-202`: the session hands off when `context_tokens >= handoff_threshold * context_limit`.
- `umas/modules/models-and-usage/models-and-usage-spec.md:108`: `tokens = usage.input_tokens + usage.output_tokens`, the ledger total.
- `libs/llm-gateway/README.md:36`: `Usage: { input_tokens, output_tokens, cached_input_tokens?, cache_write_tokens? }`. It does not say whether `input_tokens` includes cached tokens.
- No caller defines how a Step's `context_tokens` is computed from `usage`. The models-and-usage flow (step 8, line 125) uses the value without a source.

**Failure scenario.** The glue sets `context_tokens` to the ledger total (input + output for the call). That total is cumulative across calls, so the session hands off early. Or the glue uses `input_tokens`, and a provider that reports cached tokens separately under-counts the window, so the session overflows before the 95 % backstop. Each is a plausible implementation, and each is wrong in a different direction.

**Fix.** Define the formula in llm-gateway section 3.1 and cite it from models-and-usage section 2. It must state whether cached tokens count toward the window, per provider. For CLI Workers, state that no `context_tokens` value exists (agent-execution Open 6) and that the 90 % rule does not apply.

### B4. `context_limit` has one name in three places, and its default disagrees

- `umas/modules/models-and-usage/models-and-usage-spec.md:176`: "Config key `context_windows.<alias>`". Line 189: "`context_limit` ... not set. Taken from `context_windows.<alias>`", with the config in "Model config, next to the llm-gateway alias table (llm-gateway 3.2)".
- `libs/llm-gateway/README.md:41-50`: the alias table has no `context_windows` entry. The key is not defined where the spec says it lives.
- `umas/modules/orchestration/orchestration-spec.md:224`: `coordinator_config.context_limit` default `200000`. Line 48 repeats it.
- `umas/modules/context-persistence/context-persistence-spec.md:154`: `context_limit` default `200000`, owned by `SessionConfig`.
- `libs/agent-session/README.md:74` (`context_windows.<alias>`) and line 326 (`context_limit: 200000`, "an example").

**Failure scenario.** Start-up has no value for the default model. models-and-usage says `ConfigError` (line 204, Proposed). orchestration and context-persistence use 200000 silently. A model with a 128k window gets a 200k threshold, so it overflows at about 190k, and nothing reports the mismatch.

**Fix.** One key, in one file, with one owner. Recommended: `context_windows.<alias>` in `umas.config.yaml`, default not set. Make the orchestration (line 224) and context-persistence (line 154) rows read from it. Make `ConfigError` at start-up a decision, not a Proposed item, and name the alias fallback rule (Open 17).

### B5. Nobody triggers the ingest that `umas metrics tokens` depends on

- `umas/modules/models-and-usage/models-and-usage-spec.md:131`: "The rows come from `ingest_token_ledger` on the ledger."
- `umas/modules/interfaces/interfaces-spec.md:276`: `umas metrics tokens` is `query` on `token.used`.
- `libs/metrics-store/README.md:203`: `token_ledger: ""  # ... empty = disabled`. The default disables the ingest.
- `libs/metrics-store/README.md:273`: Open 1, "should `metrics-store` run its own background ingest loop ... or should UMAS drive ingest explicitly". Unresolved.
- No caller spec schedules `ingest_token_ledger`. A search of `umas/` and `libs/` finds it only in models-and-usage (lines 131, 231) and metrics-store.

**Failure scenario.** A user runs tasks, then runs `umas metrics tokens`. With the defaults, metrics-store has no `token.used` rows, so the command prints zero or "none". The ledger has the data. The command is silently wrong.

**Fix.** Name the owner and the trigger. Recommended: the daemon calls `ingest_token_ledger` every `ingest.interval_seconds` (300), and models-and-usage row 131 says so. Set `ingest.token_ledger` to the same path as token-ledger `ledger_path` (see M4), not to an empty default. Close metrics-store Open 1.

### B6. The handoff event that the Scheduler reads is not the one the session writes

- `umas/modules/models-and-usage/models-and-usage-spec.md:173`: event `handoff_request`, payload `{ session_id, task_id, reason, context_used, context_limit, packet }`.
- `libs/agent-session/README.md:299`: the session appends `handoff_initiated`, with `context_used`, `context_limit`, `reason`. No `task_id` and no packet in the event.
- `umas/modules/agent-execution/agent-execution-spec.md:168`: `handoff_request`, with `reason`, `token_usage`, `context_limit`, `task_id`. A third field set.
- `umas/modules/orchestration/orchestration-spec.md:213`: "`handoff_request` event ... Read by the Scheduler (5.3)".
- models-and-usage Open 15 (line 282) flags this as open, but the Scheduler's reading depends on it now.

**Failure scenario.** `handoff()` appends `handoff_initiated`. The Scheduler waits for `handoff_request` and never sees a handoff. The task stays in its session until the Monitor's backstop acts, which may be never, since the emergency rule also depends on this event.

**Fix.** Choose one name and one payload. Recommended: agent-session 5.8 emits `handoff_request` with the models-and-usage payload. Alternatively, the glue maps `handoff_initiated` to `handoff_request`. Either way, orchestration line 213, agent-execution line 168 and agent-session line 299 must name the same event and fields, and models-and-usage Open 15 becomes a decision.

### B7. The machine-shutdown `.pause` signal is both removed and kept

- `umas/modules/models-and-usage/models-and-usage-spec.md:179`: "**Removed (ADR-0005):** ... the pause signal, the `budget_paused` session status ..."
- `umas/modules/agent-execution/agent-execution-spec.md:172-173` and `:189`: the `.pause` file, `PAUSE.md` and `shutdown_grace_seconds` are still specified.
- `umas/modules/monitoring/monitoring-spec.md:77-78` and `:115`: the daemon writes `<hook-path>/.pause`.
- `umas/modules/context-persistence/context-persistence-spec.md:123-124`: `.pause` and `PAUSE.md` are still an interface.
- `libs/agent-session/README.md:243-267` (5.6): `pause()` and the `.pause` poll are still specified.
- `docs/decisions/ADR-0005-track-token-usage-only.md:23-30` removes budget pauses only. Its "Kept" list (lines 32-37) does not mention machine-shutdown pause. The title says "no pause", which can be read either way.

**Failure scenario.** An implementer reads models-and-usage line 179 and drops `.pause`. The daemon's clean shutdown then loses its checkpoint step, and boot recovery depends on `PAUSE.md`, which is never written. Or the reverse: an implementer keeps the signal everywhere, and a reader of the removal list thinks budget pause was not removed.

**Fix.** The owner decides, and the answer is written into ADR-0005 "Kept". Recommended: keep machine-shutdown pause (it is not a usage rule), and change models-and-usage line 179 to "the budget pause signal". The owner should confirm this, because the title of ADR-0005 can be read the other way.

## Majors

### M1. Who sends the emergency handoff: the Monitor's spec says it, its permissions do not allow it

- `umas/modules/monitoring/monitoring-spec.md:32`: "Emergency handoff from last checkpoint". Lines 34 and 94-95 repeat it as the Monitor's action.
- `umas/TECHNICAL-DESIGN-SPEC.md:650`: "Monitor forces handoff from last checkpoint".
- `umas/modules/models-and-usage/models-and-usage-spec.md:126` and Open 9 (line 276): the Monitor escalates, and the Coordinator sends the handoff.
- `umas/modules/access-control/access-control-spec.md:297`: the Monitor role has `agent:read, task:read, work:read, merge:read, metrics:read`. It has no `agent:handoff`. Line 292 gives `agent:handoff` to the Coordinator.

**Failure scenario.** The Monitor performs the emergency handoff as its spec says. The permission check fails, or the monitor code gets a credential it should not hold. The backstop does not work.

**Fix.** Change monitoring lines 32, 34 and 94-95, and TECHNICAL-DESIGN-SPEC line 650, to "escalate to the Coordinator, which sends the handoff". Then Open 9 has a single answer.

### M2. The Monitor's 95 % check has no input it can read

- `umas/modules/monitoring/monitoring-spec.md:62`: "the Project Monitor reads ... context-window usage".
- `umas/modules/monitoring/monitoring-spec.md:111`: the session row payload is `status, last_heartbeat, paused_at`. There is no context field.
- `umas/modules/agent-execution/agent-execution-spec.md:283`: "Worker context use is visible only as far as each CLI reports it."

**Failure scenario.** The Monitor cannot evaluate the 95 % rule for any session. The rule either never fires or is evaluated on a default the spec does not give.

**Fix.** Add `context_tokens` and `context_limit` to the session row payload (monitoring line 111), written by the session on each step (B3 defines the value). State that CLI Workers have no value, so the 95 % rule covers only in-process sessions, and say what the Monitor does for a CLI Worker.

### M3. `SessionConfig` omits `counter`, and no caller supplies the tokenizer

- `libs/agent-session/README.md:80`: `counter: fn(text) -> int # caller-supplied token counter, used by pack()`. Line 81: `event_source`.
- `libs/agent-session/README.md:165` and `:306`: `handoff()` calls `pack()`, passing `config.counter`.
- `umas/modules/models-and-usage/models-and-usage-spec.md:172`: the `SessionConfig` row lists `context_limit, handoff_threshold, emergency_threshold, checkpoint_every, handoff_packet_size, decisions_in_packet, compression_level`. It omits `counter` and `event_source`.
- `umas/modules/models-and-usage/models-and-usage-spec.md:174`: the packing call is "from the session" but its caller is "agent-execution (caller)". `handoff()` calls `pack()` itself.

**Failure scenario.** The handoff for a CLI or in-process session has no `counter`. `handoff()` fails, or the caller passes a character count and the packet is wrong. The caller that owns `pack()` is not clear, so no one checks.

**Fix.** Add `counter` and `event_source` to the models-and-usage row (172). Name the supplier of `counter` for each session type. Correct line 174 to say `handoff()` calls `pack()`, and that the caller only registers sections.

### M4. The ledger path is relative and is written by several processes with different working directories

- `libs/token-ledger/README.md:110`: `ledger_path: .token-ledger/usage.jsonl`. Line 47 repeats it. No text anchors it.
- The writers are the llm-gateway glue, the launcher (`umas/modules/agent-execution/agent-execution-spec.md:174`), and the `token-ledger` CLI run by an Admin. Each may run from a different directory.
- `libs/metrics-store/README.md:203`: `ingest.token_ledger` names the same file, with default `""`.

**Failure scenario.** The launcher runs in a hook worktree and writes `worktree/.token-ledger/usage.jsonl`. The gateway glue writes `repo/.token-ledger/usage.jsonl`. Two ledgers exist, and `umas metrics tokens` reads one.

**Fix.** Make `ledger_path` a single absolute path in `umas.config.yaml`, resolved once at start-up. Require the launcher and the glue to use that config value. Make metrics-store's `ingest.token_ledger` read the same key, not a separate empty default.

### M5. `umas metrics tokens` has three different default windows

- `umas/modules/interfaces/interfaces-spec.md:276`: "`since` 7 days (from source: metrics-store §9)".
- `libs/metrics-store/README.md:68`: `since` "default: 90 days ago" for `query`.
- `libs/metrics-store/README.md:248`: the mapping uses `since: "7d"`, which is an example, not the default.
- `libs/token-ledger/README.md:69`: the no-argument view is "totals grouped by model, all time".

**Failure scenario.** A user compares `token-ledger` (all time) with `umas metrics tokens` (7 days) and sees different totals. Both are "correct" by their specs. The user reports a bug.

**Fix.** Choose the default for `umas metrics tokens` and state it in interfaces (276) and models-and-usage (131). Recommended: all time, to match `token-ledger`. State the 90-day retention difference (see M6).

### M6. The ledger file has no retention owner, and the metrics view forgets history after 90 days

- `libs/token-ledger/README.md:25`: "Retention and pruning ... The file is never rewritten by the library. [metrics-store] owns retention of derived measurements."
- `libs/metrics-store/README.md:172`: `prune(retain_days)` deletes measurements, not the ledger file. Default 90 days (line 256).

**Failure scenario.** The ledger file grows without limit, with no owner, and no size or rotation rule. After 90 days, `umas metrics tokens` drops history that `token-ledger` still totals. The two "total" numbers diverge, and no owner reconciles them.

**Fix.** Name the owner of the ledger file: either rotation by month (a new file, which needs a `v`-compatible reader) or an explicit "kept forever" statement, with the metrics window stated in models-and-usage. Add the decision to models-and-usage section 9.

### M7. An exception from the `on_usage` callback is not specified, and it can cause double spend

- `libs/llm-gateway/README.md:77`: `on_usage(callback)` is "Called once per successful or failed attempt". Nothing says what happens if the callback raises.
- `libs/llm-gateway/README.md:81-88` (5.1): "if error is non-retryable ... raise immediately"; otherwise it fails over.
- `umas/modules/models-and-usage/models-and-usage-spec.md:255`: "The glue logs the error, does not write a zero or an estimate". This is the glue's rule, not the gateway's.

**Failure scenario.** `record` raises `LedgerUnreadable` inside the callback. If the gateway propagates it, a successful provider answer becomes an error. The session treats it as a provider failure and fails over (exception-flows 6.7). The provider is called again and charges again. The spend is doubled, and the ledger lost the first call.

**Fix.** llm-gateway section 4 must state that callback exceptions are caught by the gateway, logged, and never change the outcome of `complete`. Put the same rule in models-and-usage section 8.

### M8. `record` has no typed error for a failed append

- `libs/token-ledger/README.md:117-123`: the errors are `InvalidEntry`, `UnsupportedVersion`, `LedgerCorrupt`, `LedgerUnreadable` ("cannot be opened or read") and `LockTimeout`. No error covers a failed write: disk full (ENOSPC) or a permission error on append.
- `umas/modules/models-and-usage/models-and-usage-spec.md:255` lists the same three errors and no write error.
- The precedent exists: `libs/metrics-store/README.md:212`, `WriteError`, "Disk full or permission denied".

**Failure scenario.** The disk fills. `record` fails with an OS error that the glue cannot classify. The glue's rule ("log, do not retry, do not estimate") cannot be applied to an error it cannot name. Retries are unclear, and a retry could write the line twice if the first write partly succeeded.

**Fix.** Add `LedgerWriteFailed` to token-ledger section 7 (transient for ENOSPC, permanent for permission), with the suggested recoverability. State whether a partial write is possible, and what `check()` reports for it. Add the error to models-and-usage line 255.

### M9. Harness usage is lost if the launcher dies after the run and before `record`

- `umas/modules/agent-execution/agent-execution-spec.md:174` and `umas/modules/models-and-usage/models-and-usage-spec.md:120`: the launcher records once, when the run ends.
- `umas/modules/orchestration/orchestration-spec.md:320` (Open 8): "record usage once, only after the harness reports completion". The rule exists, but no recovery is defined.
- `libs/agent-platform/README.md:186`: the launcher re-reads commit signals with a cursor (`find_signals(after=cursor)`).

**Failure scenario.** The daemon restarts after a Worker finished but before `record` ran. The usage of that run is never written. The Worker's signal is still in git, so a restart could read it and record it, but that path is not specified. A naive fix records the same run twice.

**Fix.** Specify that the launcher stores the usage it has read, and the cursor, in one atomic write, and records from the stored value on restart. Name the owner (agent-execution). Add a test: restart between signal and `record` gives exactly one entry.

### M10. A handoff that fails at the emergency threshold has no defined fallback in agent-session

- `umas/modules/models-and-usage/models-and-usage-spec.md:252`: `RequiredTooLarge` gives "fall back to the last `STATE.md` checkpoint, flag the handoff as degraded, and raise P2 (Open 18)". The row says the error is "named `RequiredSectionTooLarge` in section 7".
- `libs/agent-session/README.md:356-357`: `RequiredTooLarge` belongs to `pack()`, and `RequiredSectionTooLarge` to `handoff()`. Both exist. The row in models-and-usage mixes them.
- `libs/agent-session/README.md:198-207` (5.1): the loop calls `handoff()` and has no branch for its failure. The session would raise, or stop, and the spec does not say which.
- The degraded flag exists only for "never calls `register_context`" (agent-session line 380), not for this case.

**Failure scenario.** At 95 % the session's `handoff()` raises `RequiredSectionTooLarge`. Nothing writes the fallback packet, and the Monitor's backstop then has no checkpoint to send. The session may be left in `active` at 95 % with no handoff.

**Fix.** agent-session 5.1 and 7 must say what `handoff()` does on failure, and which status the session takes. Models-and-usage line 252 must name the handoff error and point to the fallback. Open 18 becomes a decision.

## Minors

Listed without individual review. Each is a fix-list item.

- m1. `libs/token-ledger/README.md:151` says "after each successful call". That contradicts llm-gateway line 161 and models-and-usage line 114, which record failed attempts too. Fix in the same edit as B1.
- m2. `umas/modules/context-persistence/context-persistence-spec.md:151` says `compression_level` is "Passed to `pack()`". `libs/agent-session/README.md:79` and models-and-usage line 193 say it is not an input. Follow agent-session.
- m3. `umas/modules/context-persistence/context-persistence-spec.md:193` says models-and-usage "Sends `token_used` as commit tags and events". No row in models-and-usage section 3 has this. Stale.
- m4. `libs/token-ledger/README.md:152` maps `umas metrics tokens` to `totals(group_by=model)` on the ledger. Interfaces line 276 and models-and-usage line 131 use the metrics-store `query`. Two data paths for one command. Pick one.
- m5. `libs/token-ledger/README.md:59`: `check() -> Report`. The `Report` fields are not defined. Models-and-usage line 256 says "Admin (through `check()`)", but no `umas` command or health route exposes it. `umas health-check` (interfaces line 226) does not include it. Corrupt lines are therefore counted and never shown.
- m6. Recipient "None" for "Attempt or run reports no usage" (models-and-usage line 254) matches ADR-0005. The view still gives no signal that totals are low. Open decision: should `umas metrics tokens` show the count of runs with no usage? See the open list.
- m7. `libs/token-ledger/README.md` does not say whether a zero `tokens` value is written. A harness that reports zeros produces zero-token lines. Decide and state it.
- m8. The ledger has no `outcome` field, so a failed attempt's tokens look like a success. This is an accepted ADR consequence, but no caller shows the difference. Note it in models-and-usage section 2.
- m9. `umas/modules/models-and-usage/models-and-usage-spec.md:280` (Open 13) says `tokens` is "in the callback payload". The payload carries `usage`, and `tokens` is computed from it (line 108). Fix the wording.
- m10. `umas/modules/monitoring/monitoring-spec.md:32` uses `> 95%`. agent-session line 198 uses `>=`. Open 18 (monitoring line 241) recommends `>=`. Follow it when edit M1.
- m11. `umas/modules/interfaces/interfaces-spec.md:334` and `:403` mark `metrics:read` as "proposed". `access-control-spec.md:246` and models-and-usage line 213 mark it decided (D21). Update the interfaces rows.
- m12. Fallback alias context window (models-and-usage Open 17) defaults to the smaller window. There is no owner for the per-alias `fallback` entry. Name the owner, or leave it as the default.
- m13. The ledger file has no access control. Any local process can append a line, and there is no actor to check (accepted by ADR-0005). Mention it in the models-and-usage consequences.
- m14. Outside scope but affected: `libs/task-queue/README.md:21`, `:29` and `:113` keep a generic `admit` callback. The ADR terminology table (ADR-0005 line 62) says `admit` is removed. `umas/TECHNICAL-DESIGN-SPEC.md:1448` still names "the `admit` rule". Decide whether the hook stays; task-queue is not in this revision's scope.
- m15. `umas/modules/models-and-usage/models-and-usage-spec.md:4` says "Caller assessment not yet run on this revision". This report is that assessment (round 1). Update the header when the blockers are fixed.

## Open decisions not stated where they bite

Each is listed with the spec and line where it should appear. A decision with no owner is a blocker when a caller depends on it.

1. Meaning of `model` (alias or provider name). Blocker B1. Owner: models-and-usage.
2. Source of the harness total and model. Blocker B2. Owner: agent-platform, then models-and-usage.
3. Formula for `context_tokens`, including cached tokens. Blocker B3. Owner: llm-gateway, then agent-session.
4. Single key and default for `context_limit`. Blocker B4. Owner: models-and-usage.
5. Who runs ingest, and when. Blocker B5. Owner: orchestration or the daemon.
6. Handoff event name and payload. Blocker B6. Owner: agent-session 5.8.
7. Whether machine-shutdown `.pause` survives ADR-0005. Blocker B7. Owner: the ADR owner.
8. Who sends the emergency handoff (Open 9). Major M1. Owner: models-and-usage.
9. Callback exception contract. Major M7. Owner: llm-gateway.
10. Write-failure error and its retry rule. Major M8. Owner: token-ledger.
11. Ledger file retention and rotation. Major M6. Owner: to name.
12. Launcher restart rule for usage. Major M9. Owner: agent-execution.
13. Fallback when a handoff fails. Major M10. Owner: agent-session.
14. Whether `umas metrics tokens` shows runs with no usage. Minor m6. Owner: interfaces.
15. Whether `.pause` and `admit` remain in the generic libraries. Minor m14. Owner: task-queue and the ADR owner.

## Evidence checked and found consistent

- Error names match across token-ledger 7, models-and-usage 8 and llm-gateway 3.3 and 7 (`ConfigError`, `ProviderExhausted`, `InvalidEntry`, `LedgerUnreadable`, `LockTimeout`).
- `ingest_token_ledger(ledger_path, since?)` has one signature in models-and-usage line 231 and metrics-store line 129.
- The `token.used` metric name, with the `model` tag, is consistent in metrics-store (lines 53, 248), interfaces (line 276) and models-and-usage (line 177).
- The thresholds 0.90 and 0.95 match in agent-session, models-and-usage, context-persistence (lines 102-103, 152-153), agent-execution (lines 191-192) and TECHNICAL-DESIGN-SPEC (lines 649-650).
- No live budget, reservation, cost or price rule remains in the caller specs. The hits are "Removed (ADR-0005)" rows (interfaces 237, 277, 310, 335, 374, 409; monitoring 121, 183, 216; orchestration 152, 299; agent-execution 269; access-control 194, 275, 406-407).
- Every relative link in the in-scope files resolves (checked by script).

## Method

- Read ADR-0005 and both in-scope specs in full.
- Grepped the nine caller specs and the two libraries for ledger, budget, pause, handoff, threshold and `context_limit` terms. Read each hit that a caller depends on.
- Checked each finding against the cited line. Line numbers are from the files as they stand on 2026-11-09.
- No spec was edited, and no git command was run. The only file written is this report.
