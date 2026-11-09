# Tasks: remove budgets, track token usage only (ADR-0005)

> **Date:** 2026-11-09 · **Decision:** [ADR-0005](./decisions/ADR-0005-track-token-usage-only.md) · **Closes:** D14, D17, D18, D19, D22, D22a, C2 in [decisions-pending-2026-10-25.md](./decisions-pending-2026-10-25.md)

## Defaults taken

Each default can be vetoed in one reply.

- `compression_level` is kept in the specs for now. Removing it touches agent-session, context-persistence and models-and-usage, and it is not a budget item. Decide in the next pass.
- `record` failure: log it, never write zero or an estimate, do not record twice, raise P2 when the file is unreadable (models-and-usage §5.7, marked Proposed).
- The backstop handoff belongs to the session first, then Monitor escalates, then the Coordinator sends the handoff (models-and-usage Open 9).
- The `AGENT_TOKEN_EXHAUSTED` error code stays in the PRD until `libs/error-classifier/README.md` changes. That file is out of this change's scope.
- Historical documents (old task files, caller assessments for the removed `budget-and-models` module, the closed-items table in the decisions file) are not rewritten. They are records.

## Tasks

- [x] **1. Decision recorded.** ADR-0005 written. Done when the ADR lists the removed, kept and renamed items. Verified: the file exists with the removed, kept and renamed tables.
- [x] **2. Library renamed and rewritten.** `libs/budget-meter` → `libs/token-ledger` (v0.2). Done when the spec has the `{v, ts, model, tokens}` contract and seven acceptance criteria. Verified: the spec was read in full. Windows locking is verified by reading only.
- [x] **3. Module renamed and rewritten.** `umas/modules/budget-and-models` → `umas/modules/models-and-usage`. Done when there are no live budget interfaces and the links resolve. Verified by grep and the link check. The caller assessment is still open (task 6).
- [x] **4. Caller specs and umbrella docs updated.** orchestration, agent-execution, context-persistence, access-control, monitoring, interfaces, exception-flows, verification, TECHNICAL-DESIGN-SPEC, TECHNICAL-DESIGN-SUMMARY, UMAS-DNA, UMAS-SETUP-GUIDE, UMAS-BUILD-ASSESSMENT, PRD, libs/README, packs/README, the agent-session and metrics-store READMEs. Verified: stale-name grep is clean in live files. The remaining hits are removal notes, ADR references or historical records.
- [x] **5. Decisions file closed.** The budget items are closed at the top of `decisions-pending-2026-10-25.md`. D20 is not affected. Verified by reading the table.
- [x] **6. Caller assessment gate (2a), round 1** on `token-ledger` and `models-and-usage`. Report: `docs/assessments/caller-assessment-token-usage-2026-11-09.md`. **Verdict: rejected. 7 blockers, 10 majors, 15 minors.** Blockers: B1 `model` meaning (alias or provider name); B2 harness total and model not in `CompletionSignal`; B3 `context_tokens` formula and cached tokens; B4 `context_limit` key and default differ across four specs; B5 nobody schedules `ingest_token_ledger`; B6 handoff event name and payload differ across three specs; B7 `.pause` is both removed and kept. Facts re-checked by me before recording: llm-gateway:161 says `model` = alias; `CompletionSignal` (agent-platform:85-95) has no `model`; `machine_paused` is still a resumable status (agent-session:66).
- [ ] **7. Address the 7 blockers (round 1), then run round 2 with a fresh assessor on the blockers only.** Depends on task 6. Owner decisions needed first: B1 (recommended: alias everywhere, provider name not stored in v1), B7 (recommended: keep machine-shutdown pause; ADR-0005 "Kept" to say so). The other blockers have a recommended fix in the report. Majors M1 to M10 are fixed in the same pass or listed as decisions. Stop after two rounds.
- [-] **8. Remove `compression_level`.** Not done: this is not a budget item and it touches three specs. Decide in the next pass (see Defaults taken).
- [-] **9. Fix the `handoff_request` payload.** Not done: `agent-execution` uses `token_usage` and `token_limit`, and agent-session uses different names (models-and-usage Open 4). It is a contract question for the Open 4 owner.
- [-] **10. Fix two pre-existing broken links** in `docs/brief-module-split-2026-10-25.md:16`. Not done: they are not broken. The line is inside a code-block header template that is copied into `umas/modules/<name>/`, where `../../TECHNICAL-DESIGN-SPEC.md` is correct (same as `orchestration-spec.md:3`). Changing it to `../umas/...` would break the template. Verified by a link check over all `.md` files (see `docs/tasks-cleanup-2026-11-09.md`).
- [-] **11. Cross-platform review of code.** Not applicable: this change has no new code. The only code is the Python reference in the token-ledger spec, which is verified by reading only.

## Verification run (2026-11-09)

- Link check (`/tmp/linkcheck/check.py`): 2 broken links, both pre-existing (task 10).
- Stale-name grep over live specs: clean, except removal notes and history records.
- Library count: fourteen. The table in `libs/README.md` has 14 rows, and there are 14 library directories with a README. The "libraries (13)" in `umas/TECHNICAL-DESIGN-SUMMARY.md` is now "(14)".
- Nothing is committed. The two renames are staged from the earlier `git mv`. All other changes are unstaged.

## State log

- 2026-11-09: ADR-0005 decided. Renames done. Caller specs, umbrella docs and decisions file updated by background editors.
- 2026-11-09: models-and-usage rewritten (305 lines). umas docs and PRD edited.
- 2026-11-09: final checks run. Library count corrected to fourteen in `umas/TECHNICAL-DESIGN-SUMMARY.md`. `docs/brief-module-split-2026-10-25.md` rows 5.6 and 5.7 now point at `models-and-usage`. ADR-0005 "Kept" bullet changed from `token.input`/`token.output` to `token.used`, to match its own terminology map. Caller assessment started (task 6).
- Next: read the assessor report, record the verdict in task 6, then do task 7 if there are blockers.
