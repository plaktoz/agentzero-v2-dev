# Tasks: minimalism-ladder adds four ponytail rules and stands alone

> **Date:** 2026-11-09 · **Pack:** `packs/minimalism-ladder/` · **Source of rules:** [ponytail](https://github.com/DietrichGebert/ponytail/blob/96608e078b2d5ea607c5c3b8b5a54d1c1fba6846/skills/ponytail/SKILL.md) at commit `96608e0`, MIT licence
> **Owner request (2026-11-09):** keep the ladder; add ponytail's scope checklist, bug-fix caller rule, test rule and never-cut list; credit ponytail; the pack will be ported to a separate project, so it must stand independently.

## Requirements

1. The portable set (spec §3) has no link or reference to files outside it. No UMAS, `libs/`, `docs/` or `packs/README.md` link. The spec, `RESULTS.md` and `SKILL-ASSESSMENT.md` are repo records and may refer to UMAS.
2. `PACK.md` contains the four rules, in the pack's own words. The record format and the `SHORTCUT:` format do not change.
3. The MIT notice and the attribution are in the pack folder, so the copy carries them.
4. The pack does not name any vendor, harness or slash command (the claude-mods rule for shared skills).

## Defaults taken

Each default can be vetoed in one reply.

- **Version bump. Superseded by ADR-0006 (Q4):** `pack_version` stays `0.1.0` until a 0.2.0 fixture run is recorded.
- **Record unchanged.** The four rules have no record field. They are recorded in `notes` or in the answer text. Adding a `tests` or `scope` field would change the schema and `check_evidence.py`, which is outside this change. Limitation: the test rule cannot be checked from the record.
- **UMAS material leaves the pack. Superseded by ADR-0006 (Q1):** the spec keeps §9 and §12 whole. The portable set is the named list in spec §3; the spec itself is not copied.
- **Fixtures F9 to F12 added as expectations, not run.** One for each new rule (scope, bug-fix caller grep, never-cut) and one for tests for new logic. Written, not run. Running them needs subagents and an independent judge (decision D3), which is outside this change.
- **Reply closing line (ponytail's "what you skipped and the risk") is not added.** It was not in the four rules you listed.
- **Ponytail's level meanings are not adopted.** The pack keeps `lite`, `full` and `ultra` as defined in spec §5.5.

## Proposed rules text (for the caller assessment gate)

> **Superseded in part by ADR-0006.** Not applied as written: `NOTICE.md` (Q3 puts the full MIT text in `PACK.md`), removal of spec §9 and §12 (Q1), the 0.2.0 bump (Q4), and the F9–F11 list (now F9–F12). The applied text is in `packs/minimalism-ladder/PACK.md`. This section is kept as the plan the round 1 assessor reviewed.

### PACK.md, new section "Scope" (after "Read first")

Before you climb the ladder, list every place the change must reach: its callers, tests, fixtures, config, exports and public interfaces. Also list what the change could break for users, such as data it could destroy or expose, or callers that would stop working. Scope means the reach the task needs. It does not mean extra features.

### PACK.md, new section "Bug fixes"

Before you edit a function, search for every caller of it. Fix the root cause once, in the shared code. Do not patch each call site. Record the search as evidence for rung 2 when the shared code is reused.

### PACK.md, new section "Tests for new logic"

New non-trivial logic needs one small test or an assert-based self-check. Non-trivial means a branch, a loop, a parser, money or security logic, or a new script or app. A trivial change needs none. Name the test or the assert in `notes`.

### PACK.md, new section "Never cut"

Whatever rung you stop at, keep these:
- validation at trust boundaries;
- error handling that prevents data loss;
- security;
- accessibility;
- the calibration real hardware needs;
- anything the task asked for.

When you move or merge code, keep its error handling and validation.

### PACK.md, new section "Credits"

The scope, bug-fix, test and never-cut rules are adapted from ponytail by DietrichGebert, released under the MIT licence (commit `96608e0`). The full notice is in `NOTICE.md`.

### NOTICE.md (new file)

Contains the upstream attribution, the source URL, the pinned commit, and the MIT licence text copied from the upstream `LICENSE` at that commit.

### Spec changes

- Header: remove the link to `packs/README.md`. Keep the independence line.
- §2 non-goal "Tracking debt": say "a separate debt scanner" with no link.
- §3 file table: add `NOTICE.md`; add the four rules to the `PACK.md` row.
- §5: keep 5.1 to 5.6. Add 5.7 Scope, 5.8 Bug fixes, 5.9 Tests for new logic, 5.10 Never cut, each one short.
- §8.1: add F9 (scope lists callers, tests and config before the edit), F10 (bug fix greps callers and fixes the shared code once), F11 (required validation kept on a never-cut path).
- §9 Known Consumers: remove. Moved to the UMAS side (see below).
- §10: keep the deviations table. Remove UMAS file names. Add a row: "Scope, bug-fix, test and never-cut rules added from ponytail (MIT)".
- §12 Reference implementation: remove. It is UMAS code.

### Content moved out of the pack (for the UMAS side)

- §9 mapping table: "Minimalism ladder enforced before code" → Developer and Worker prompts; `project.minimalism.level` and `enforce`; `MinimalismEnforcer` rungs; shortcut comments tracked in the debt ledger (decision-artifacts); `metrics minimalism` computed from stored records; router tiers.
- §12 reference code and §12.2 YAML: from `TECHNICAL-DESIGN-SPEC-PART3.md` §5.4.2 and §5.4.3.

These need to be kept on the UMAS side, in `umas/modules/agent-execution/agent-execution-spec.md` or the umbrella spec.

### Other files to check

- `packs/README.md` row for minimalism-ladder: add "scope, bug-fix, test and never-cut rules". Stays in the repo.
- `SKILL-ASSESSMENT.md`: add a dated note at the top. The 2026-10-25 findings stay as history.

## Tasks

- [x] **1. Caller assessment gate (AGENTS.md 2a), round 1.** Report: `docs/assessments/caller-assessment-minimalism-ladder-2026-11-09.md`. **Verdict: rejected. 2 blockers, 10 majors, minors listed.**
  - **B1.** Removing spec §9 and §12 deletes the only copies of contracts that UMAS depends on. The file this task file calls the source, `TECHNICAL-DESIGN-SPEC-PART3.md`, is **not in the repo** (checked by `find`). This task file did not keep the content: lines 69–75 hold one-line descriptions only. The claim "kept in this task file" in Requirements was wrong.
  - **B2.** The test rule ("a branch") is broader than test-policy's "more than a trivial guard" (`packs/test-policy/PACK.md:62-84`). specialist-agents says "risky logic only" (`specialist-agents-spec.md:118`).
  - Majors: standalone check cannot pass as written (spec line 4 names UMAS; `SKILL-ASSESSMENT.md` is exempted against requirement 1); no Scope step in PACK.md Steps; Scope list conflicts with spec §2 non-goal (line 24) and the one-sentence `notes` field; 0.2.0 bump claims rules no run shows; bug-fix rule drops the "Bug fix:" qualifier; never-cut list conflicts with `PACK.md:69`; F11 duplicates F7; MIT notice is not carried by installs (`libs/agent-platform/README.md:221-281` installs only `SKILL.md`); UMAS docs still describe rungs 3–5 as implemented (`UMAS-BUILD-ASSESSMENT.md:28,89`).
  - Decisions Q1–Q4 are in `docs/tasks-minimalism-ladder-2026-11-09.md` under "Owner decisions" (below). Round 2 waits on them.
- [x] **2. Rules added to `PACK.md`** (2026-11-09). Scope step added to Steps (now 8 steps); sections Scope, Bug fixes, Tests for new logic, Never cut; level note ("applies at every level"); trigger widened to bug fixes; Credits and licence with the full MIT text. **Changed from the first plan by ADR-0006:** no `NOTICE.md` (Q3 = full text in `PACK.md`); version stays 0.1.0 (Q4). Verified: forbidden-word grep over the portable set returns nothing; no slash command in `PACK.md`.
- [x] **3. Spec updated.** Header, non-goal and file table fixed; §5.7 to §5.10 added; §10 rows added. **Changed by Q1:** §9 and §12 are kept, because they are the only copy of the UMAS contracts. The portable set is a named list in spec §3, so the spec, `RESULTS.md` and `SKILL-ASSESSMENT.md` are not copied.
- [x] **4. Fixtures F9 to F12 written, not run.** F9 scope, F10 bug fix, F11 never cut (replaces the first F11, which duplicated F7), F12 tests for new logic (added after the assessor found no test-rule fixture). They have `id`, `input`, `expect`. Not run: no independent judge (D3).
- [x] **5. Tests.** `python3 -I -m unittest discover -s tests`: 17 tests OK (macOS, Python 3.15). `check_evidence.py` unchanged.
- [x] **6. Standalone check, portable set only.** `grep -i -E 'umas|libs/|docs/|packs/README|\]\(\.\./|claude code|codex|copilot|gemini|openai|anthropic'` over `PACK.md`, `config.yaml`, `schema`, `scripts`, `tests`, `fixtures/F*.yaml`: no match. Not checked: the spec, `RESULTS.md` and `SKILL-ASSESSMENT.md` (not in the portable set).
- [x] **7. `packs/README.md` row and `SKILL-ASSESSMENT.md` note updated.** Also fixed the stale claim "all 6 ladder rungs implemented" in `umas/UMAS-BUILD-ASSESSMENT.md`.
- [x] **8. Round 2 caller assessment** by a fresh assessor on B1 and B2 only. **Verdict: accepted with open items. 0 blockers.** Report: `docs/assessments/caller-assessment-minimalism-ladder-round2-2026-11-09.md`. B1 fixed (spec §9 and §12 kept; portable set named in spec §3). B2 fixed (test rule matches test-policy's "trivial guard"). Open majors: O1 new-script and state kinds differ from test-policy; O2 no composition note in `packs/README.md` or `specialist-agents-spec.md` (promised by ADR-0006 Q2); O3 spec §12.2 YAML keys differ from §6.
- [-] **9. Not done: UMAS wording in the spec §9 and §12 stays.** It is a record in this repo, not part of the port. The UMAS docs that describe the enforcer (`TECHNICAL-DESIGN-SUMMARY.md:190-197`, `UMAS-DNA.md` P5, `agent-execution-spec.md:175`) are not changed to mention the four rules. Reason: they describe UMAS behaviour; adding the rules there is a UMAS decision.

## Owner decisions (from the caller assessment, round 1)

Answered 2026-11-09 by taking the recommended option for each (owner: "use the task file to work on this"). Recorded in [ADR-0006](./decisions/ADR-0006-minimalism-ladder-adds-ponytail-rules.md). The owner can veto in one reply.

**Q1. What happens to the removed §9 and §12 content, and to the source spec? (B1)**
- (a) Keep the source spec whole. Produce the standalone copy by a filtered export. Low risk of losing a contract; moderate risk of drift between the two copies.
- (b) Move §9 and §12 into `umas/modules/agent-execution/agent-execution-spec.md` first, then remove them from the pack. One copy in each repo. Makes task 8 a blocker for task 3.
- (c) Remove now, as first proposed. Irreversible without git history; `metrics minimalism`, the level/enforce mapping and the enforcer rungs would have no documented source.
- **Recommendation: (a).** Reversible, and every consumer contract stays in place.

**Q2. Which test definition wins when the ladder and test-policy compose? (B2)**
- (a) The ladder states its own definition, and a composition note says which one wins in the Developer pipeline. Packs stay independent.
- (b) Copy test-policy's wording into the ladder. Drifts over time.
- (c) Remove the test rule. Loses the new-logic requirement you asked for.
- **Recommendation: (a).** Note: this needs a test-rule fixture, which the proposal lacks.

**Q3. Where does the MIT notice sit, and what does each installed copy carry? (M9)**
- (a) `NOTICE.md` plus a copyright line and licence name in `PACK.md`. Full text only in `NOTICE.md`, which an install can drop.
- (b) Full MIT text in `PACK.md`. Longer prompt body; every installed copy carries it.
- (c) `NOTICE.md` only, as first proposed. Likely a licence gap, since the copied rules may count as a substantial portion.
- **Recommendation: (b).** Carries the notice wherever the skill goes.

**Q4. Bump `pack_version` to 0.2.0 now, or after a 0.2.0 run? (M5)**
- (a) Bump now and say the rules are unverified. A 0.2.0 record would claim rules nothing shows.
- (b) Keep 0.1.0 until a 0.2.0 fixture run is recorded. The version then means something.
- (c) Add a record field for the rules. A schema change, outside this scope.
- **Recommendation: (b).** The first draft defaulted to (a); the assessor's point changes that.

## Verification (fill in when done)

- Caller assessment: round 1 rejected (2 blockers); round 2 accepted with open items (0 blockers; O1 to O3).
- Tests: 17 OK.
- Standalone check: portable set clean.
- Not verified: the test rule is not checkable from the record (see Defaults). F9 to F12 not run. The scope list is not in the record.
- Ported: the portable set and the four rules are in `/Users/tianhonglee/orca/agent-garage/skills/minimalism-ladder/` (`SKILL.md`, not yet committed). Its tasks and checks are in `docs/tasks/minimalism-ladder-2026-11-09.md` there (T4, T5).

## State log

- 2026-11-09: owner asked for the four rules, credit and standalone. Task file written with the proposed text. Next: task 1, the caller assessment.
- 2026-11-09: owner pointed to this file. Q1 to Q4 taken as recommended (ADR-0006). Tasks 2 to 7 done. Round 2 assessment started (task 8). Next: record its verdict; if accepted, the pack is ready to copy by the portable set in spec §3.
- 2026-11-09: round 2 accepted with open items, 0 blockers. Open: O1 (test kinds), O2 (composition note), O3 (spec §12.2 vs §6 keys), minors m1 to m9. Ported to agent-garage (T4, T5 there).
