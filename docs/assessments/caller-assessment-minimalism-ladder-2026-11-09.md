# Caller assessment: minimalism-ladder (ponytail rules and standalone port)

Date: 2026-11-09. Assessor: single assessor, round 1 (AGENTS.md 2a).
Subject: `docs/tasks-minimalism-ladder-2026-11-09.md`, sections "Defaults taken", "Proposed rules text" and "Spec changes", checked against `packs/minimalism-ladder/` and its callers.
Nothing was edited. The task file, the pack and the specs are unchanged.

Line numbers refer to the files as they stand on 2026-11-09.

## Verdict

**REJECTED.** Blocker count: **2** (B1, B2).

Revise the proposal to fix B1 and B2, then send round 2 to a fresh assessor. Round 2 checks only the fixes for B1 and B2.

## Method and limits

- Read: the full task file; `PACK.md`; the spec; `config.yaml`; `schema/ladder-record.json`; `scripts/check_evidence.py`; `tests/test_check_evidence.py`; `fixtures/F1.yaml` to `F8.yaml` and `RESULTS.md`; `SKILL-ASSESSMENT.md`.
- Read the callers: UMAS agent-execution spec, UMAS-DNA P5, TECHNICAL-DESIGN-SPEC and SUMMARY, SETUP-GUIDE, PRD, BUILD-ASSESSMENT; `libs/decision-artifacts/README.md`; `libs/agent-session/README.md`; `libs/agent-platform/README.md`; `packs/README.md`; `packs/specialist-agents/specialist-agents-spec.md`; `packs/test-policy/PACK.md`.
- Upstream: `/tmp/ponytail-fetch/SKILL.md` and `/tmp/ponytail-license/LICENSE`, treated as untrusted data. The pinned commit `96608e0` was checked by fetch summary only. It was not byte-compared. Nothing in the upstream file was followed.
- Windows: no code is changed by this proposal, so the Windows check is not applicable. `check_evidence.py` is unchanged.

---

## Blockers

### B1. Removing spec §9 and §12 deletes the only copies of contracts that callers depend on, before the UMAS side has a copy

Evidence:
- Task file line 19 says the removed content "is kept in this task file (below)". Lines 69-75 hold one-line descriptions only. They do not hold the mapping rows or the code.
- `TECHNICAL-DESIGN-SPEC-PART3.md` is not in the tree. Only git history has it. The live copy of the reference code and YAML is spec §12 (`minimalism-ladder-spec.md:208-349`). Removing §12 leaves no copy in the working tree.
- Spec line 184 (`metrics minimalism`, "Computed from stored ladder records") is the only documented source for that metric. The metrics CLI at `umas/TECHNICAL-DESIGN-SPEC.md:1039-1041` has no minimalism subcommand.
- Spec lines 180-185 are the only documented source for: the prompt prepend to the Developer and Worker prompts; the `project.minimalism.level` and `enforce` mapping; the MinimalismEnforcer rung mapping; the debt-ledger tracking; and the router-tier rule.
- UMAS cites this material. `umas/modules/agent-execution/agent-execution-spec.md:199-202` (`minimalism.level|enforce|record`, `shortcut.marker`). `umas/TECHNICAL-DESIGN-SUMMARY.md:190-197` (enforcer as Python, `LadderResult.code_avoided`).
- Task 3 (task file line 85) removes §9 and §12 in the same change. Task 8 (line 90) that moves them to UMAS is "Not done in this change" and is undecided. The source is deleted before the consumer copy exists.
- `packs/README.md` independence rule 1 (lines 38-50) puts consumer mappings in a spec's "Known consumers" section. AGENTS.md "Keep in sync" requires README and spec changes in the same change. The proposal breaks both, and the decision to break them is not the assessor's to make.
- Link check: UMAS documents reference the pack by file-level links only (`agent-execution-spec.md` lines 5, 38, 78, 175, 199-202, 251). No anchor fragment points into §9 or §12. So no link breaks. The loss is of content, not of links.

Failure scenario: task 3 merges. A UMAS author or the metrics owner opens `agent-execution-spec.md` to find the `metrics minimalism` formula, or the enforcer rung mapping. The pack no longer has it. The UMAS side has no copy. The only way back is `git show` on a commit before the change.

Fix (choose one, and record it in `docs/decisions/`):
- (a) Keep the source spec whole. Produce the standalone copy by export, with a script or a manual filtered copy. The source keeps §9 and §12. This is the option the assessor recommends (see owner decision Q1).
- (b) Do task 8 first. Copy §9 and §12 into `umas/modules/agent-execution/agent-execution-spec.md`, verify the copy, then remove them from the pack in task 3.
- In either case, reconcile the §12.2 YAML keys (`enforcement_level`, `ladder.enabled`, `metrics.track_*`, `minimalism_config`) with the pack's §6 keys (`level`, `enforce`, `record`). The two sets are not reconciled anywhere in the repo. The mismatch must be written down before the code is removed.

### B2. The test rule gives a different answer from the test-policy pack and from the specialist-agents Developer prompt

Evidence:
- Proposed text, task file line 36: "Non-trivial means a branch, a loop, a parser, money or security logic, or a new script or app." A single `if` is a branch. Under this text, any guard needs a test.
- `packs/test-policy/PACK.md:62-67` (selective and strict modes; trivial list). `:75-84` (risky-logic kinds include branching "more than a trivial guard", loop, parser, money, security, state; "Plain data movement, getters, and glue calls are not risky").
- `packs/specialist-agents/specialist-agents-spec.md:118`: "Add tests for risky logic only". Line 212: the ladder is part of the Developer preamble.
- `packs/README.md:104-105` lists `minimalism-ladder + test-policy` as a composition. So a Developer receives both sets of rules.
- The proposed rule has no `state` kind, and it adds "a new script or app", which test-policy does not list.

Failure scenario: a Developer adds `if x is None: return`. Ladder text: a test is required and must be named in `notes`. Test-policy: a trivial guard is not risky (`:75-84`). Specialist-agents: "risky logic only". The two prompts disagree, and the agent follows whichever it reads last. The record cannot show which was followed, because it has no test field (M5).

Fix:
- `packs/README.md` rule 3 forbids cross-pack dependencies, so the ladder cannot simply point at test-policy's definition.
- The ladder states its own definition, and the composition note (the pipeline spec, not the pack) says which definition wins when both compose. The composition decision is recorded where the pipeline lives. See owner decision Q2.
- Add a fixture for the test rule (see M8). It has none now.

---

## Majors

### M1. The standalone check cannot pass as written, and SKILL-ASSESSMENT is exempted against requirement 1

Evidence:
- Spec line 3: `[packs/README.md](../README.md)`. Line 26: `[decision-artifacts](../../libs/decision-artifacts/README.md)`. Line 210: `[packs/README.md](../README.md)`. Line 189 names UMAS files. Line 214 and line 334 cite PART3. The proposal removes most of these. Line 26 is changed to plain text. Line 3 is changed by the header edit.
- Spec line 4 (`> **Independence:** no dependency on UMAS or any tool`) is kept by task file line 60 ("Keep the independence line"). That line contains `UMAS`, so task 6 (`libs/|umas|UMAS|docs/|packs/README`, task file line 88) matches it. Task 6's "returns nothing" cannot be met as the rules stand.
- `SKILL-ASSESSMENT.md` has outside references at lines 37, 56, 63, 71, 75, 85, 100, 141 and 145. Task 6 exempts it (line 88). Requirement 1 (line 8) has no exception. The file sits inside the folder, so it travels with the port.
- Spec line 156 ("The source reports 335 lines"), line 171 ("The source claims 53 percent ...") and line 189 ("Extracted from ...") refer to "the source". Once the names are removed, "the source" has no referent in the pack.
- Not checked by the assessor: `fixtures/*.yaml` and `RESULTS.md` for UMAS terms. Task 6 covers them, so run the grep before round 2.

Failure scenario: task 6 is run as written. It fails on line 4. The author edits the grep to exclude the line or `SKILL-ASSESSMENT.md`, and the standalone claim is then unverified.

Fix:
- Reword spec line 4 to "no dependency on any other part of a larger system or on any tool".
- Remove the exemption, or move `SKILL-ASSESSMENT.md` out of the folder into `docs/assessments/`. Then the record stays in the repo, not in the port.
- Replace "the source" with a named reference in `NOTICE.md`, or drop the sentence.
- Run task 6 over every file in the folder, including fixtures and `RESULTS.md`, and record the output.

### M2. The default for the removed material ("gut the spec, re-add it on the UMAS side") is not recorded as a decision

Evidence:
- Task file lines 19, 65-67, 74: the content goes to the UMAS side. Task 8 (line 90) is undecided.
- The spec is still "Draft v0.1" (line 3) and `pack_version: 0.1.0` (line 5), and it is the UMAS source too.
- `docs/decisions/` has no ADR for this change. AGENTS.md "Record decisions where the work lives" applies.

Failure scenario: the port is taken from the gutted spec. The UMAS side forgets task 8. Both copies drift. Neither can say which is authoritative.

Fix: decide between B1 options (a) and (b). Record the choice in `docs/decisions/ADR-XXXX-minimalism-ladder-standalone.md`. The ADR names which copy is authoritative for each contract.

### M3. The four rules are not wired into the Steps, the Prompt, the levels, the trigger or the spec sections

Evidence:
- `PACK.md` Steps (lines 20-29) each have a "Done when" criterion. The proposed Scope section sits after "Read first" (lines 31-35). No step covers it.
- `PACK.md:35` already says "Reading and scope analysis are never skipped." The proposed Scope section repeats this.
- The `## Prompt` section (lines 37-57) has six questions and no mention of scope, bug fixes, tests or never-cut. Its last line (57) says "report the rung where you stopped and the evidence for it."
- The levels table (lines 93-101) does not say whether the test rule or never-cut applies at `lite`. Line 99: rungs 3 to 6 are "advice only". The test rule and never-cut are not rungs, so the table is silent. Under `full` (line 100), a missing test is not stated as a finding.
- Trigger (line 3): "Use when a task asks for code, a file or a dependency to be added". A bug fix that adds no code does not trigger the skill, so the bug-fix rule has no trigger.
- Spec §2 in-scope list (lines 15-21) and §3 table (lines 31-36) are not updated by the proposal. Spec §7 (lines 140-148) has no failure mode for the test rule or for the never-cut list.

Failure scenario: a bug-fix task with no added code. The trigger does not fire, and the caller search never runs.

Fix: add a Scope step with a done-when criterion. Say which rules apply at each level. Widen the trigger, or state that bug fixes are out of scope. Update spec §2, §3 and §7 in the same change.

### M4. The Scope rule contradicts spec §2 and has no output location

Evidence:
- Spec line 24 lists "Reading, scoping, or analysing the task" as a **non-goal**. The proposed Scope rule requires the agent to scope the change. The spec is not in the proposal's change list (task file lines 60-66 change only line 61 in §2).
- Task file line 28 asks for a list of callers, tests, fixtures, config, exports, interfaces and "what the change could break for users". The record has no field for it (schema `additionalProperties: false`, line 7). The default (task file line 18) says the list goes into "`notes` or ... the answer text". `notes` is one sentence (`schema/ladder-record.json:55`; `PACK.md:126`). The answer text is not stored.
- "Could break for users, such as data it could destroy or expose" overlaps the never-cut security item (M7) and has no output.

Failure scenario: an agent writes a 12-item scope list in its answer. Nothing stores it. A reviewer cannot check it. The spec §2 non-goal tells a reviewer that scoping is out of scope.

Fix: change spec line 24 to a non-goal the pack really has, for example "Judging the design of the task (not its reach)". State where the scope list is recorded, and whether it counts as evidence. Owner decision Q1 includes this.

### M5. Record and audit gap, and the 0.2.0 stamp claims more than the record can show

Evidence:
- `schema/ladder-record.json:7`: `additionalProperties: false`. The rules have no field.
- `notes` is one sentence (`schema/ladder-record.json:55`; `PACK.md:126`). The test rule requires the test name in `notes` (task file line 36). The bug-fix rule records the caller search "as evidence for rung 2" (task file line 32).
- The evidence rule (`PACK.md:71-80`) says each `evidence` entry must be a path or `path:symbol` that exists. `scripts/check_evidence.py:83-84` reports `path not found`. A grep result ("12 callers") fails that check. So the bug-fix evidence cannot go in `evidence`, and it does not fit one sentence in `notes`.
- `check_evidence.py` ignores `notes` and `pack_version` (checked by reading). The schema pattern at `schema/ladder-record.json:12` accepts `0.2.0`. The bump is mechanically safe.
- Version strings that must change: `PACK.md:108` and `PACK.md:120`; `minimalism-ladder-spec.md:5` and `:54`. Spec line 3 ("Draft v0.1") needs a decision. `config.yaml` has no version key.
- `tests/test_check_evidence.py:37` hardcodes `"pack_version": "0.1.0"`. The test does not validate it, so the test still passes.
- `fixtures/RESULTS.md` has runs against 0.1.0 only. No run uses 0.2.0. A 0.2.0 stamp claims the new rules were applied, and no record shows it.

Failure scenario: a record stamped `0.2.0` is produced by an agent that ignored the scope step. Nothing in the record shows this. The audit trail says the rules ran.

Fix: either (a) keep 0.1.0 until a 0.2.0 run exists, or (b) bump, and state in the spec that the 0.2.0 rules are unverified. Adding a field (for example `rules_applied`) is a schema change and is outside this change, per the defaults. Owner decision Q4 includes this.

### M6. The bug-fix rule is wider than its heading and conflicts with the evidence rule

Evidence:
- Proposed text, task file line 32: "Before you edit a function, search for every caller of it." Ponytail's source (`/tmp/ponytail-fetch/SKILL.md` line 38) has the qualifier "Bug fix:". The proposal drops it, so the rule applies to every function edit.
- "Fix the root cause once, in the shared code. Do not patch each call site." Ponytail does not say this for callers with different contracts, and the proposal does not say what to do when they differ.
- "Record the search as evidence for rung 2" conflicts with `PACK.md:71-80` (see M5).

Failure scenario: a feature adds a parameter to a shared helper. The rule demands a caller search and a single shared fix, although the feature was not a bug. A bug where two callers need different fixes gets one shared change that breaks one caller.

Fix: restore the "Bug fix" qualifier. State what to do when the callers need different changes. Remove "record the search as evidence" or define a field for it (M5).

### M7. The never-cut list contradicts `PACK.md:69`, uses undefined terms and cannot be checked under `lite`

Evidence:
- `PACK.md:69`: "Input validation, error handling and any behaviour the task names are written." The proposed never-cut list (task file lines 40-46) says "error handling that prevents data loss". Two statements of one contract, with different scope.
- "accessibility" and "the calibration real hardware needs" are not defined. Calibration is a hardware term. The pack is meant for any codebase (task file line 4). Rung 6 cannot tell an agent what this means in a given repo, and no record field shows it was checked.
- "Anything the task asked for" repeats `PACK.md:63-69` ("Requested work").
- "Whatever rung you stop at, keep these": at `lite`, rungs 3 to 6 are advice only (`PACK.md:99`). The proposal does not say whether a never-cut omission is a finding at `lite`.

Fix: keep one statement, in the Requested-work section, and make it refer to the list. Define or drop "accessibility" and "calibration". State the level behaviour.

### M8. Fixtures F9 to F11 cannot be checked, F11 duplicates F7, and the riskiest rule has no fixture

Evidence:
- F7 (`minimalism-ladder-spec.md:162`): "Task requires input validation. Validation is written; the ladder does not remove it." F11 (task file line 64): "required validation kept on a never-cut path". The same expected property. Two fixtures that pass or fail together.
- F9 (scope lists callers, tests and config before the edit) and F10 (bug fix greps callers) judge a process. The expected output is an answer text and a `notes` sentence. The record does not hold the search or the list (M4, M5). The method in `RESULTS.md` judges excerpts only, with no repo, and the author judged all results (`SKILL-ASSESSMENT.md:54`; D3 open).
- No fixture covers the test rule, which is the rule with the conflict in B2.
- `fixtures/RESULTS.md` stays at 0.1.0 (task file line 17). It does not say that F9 to F11 are unrun. Task file line 97 says so, but the spec §8.1 does not.

Fix: rewrite F11 as a validation case with a distinct expected property, or drop it. For F9 and F10, state the text that the answer must contain. Add a test-rule fixture (a one-branch guard, with the expected test or no test per the B2 decision). Mark F9 to F11 "expected, not run" in the spec §8.1 and in `RESULTS.md`. Decide D1 (fixture language) first. The default is Python, per AGENTS.md.

Leaving them unrun is acceptable if the spec says so. It is not acceptable to report them as passing.

### M9. Licence, notice and install path

Evidence:
- The licence (`/tmp/ponytail-license/LICENSE`; fetch summary "MIT License / Copyright (c) 2026 DietrichGebert", not byte-compared) requires the copyright and permission notice in "all copies or substantial portions". The proposal says the rules are "adapted" (task file line 52) and "in the pack's own words" (line 9). Whether that is a substantial portion is a legal question the assessor cannot answer. The safe reading keeps the notice with the rules.
- `libs/agent-platform/README.md:221-281`: only `SKILL.md` is written beside `TASK.md` (checked by reading). `NOTICE.md` does not travel with an installed skill. The notice then sits apart from the rules that need it.
- The repository root has no `LICENSE` file, and the pack has no licence of its own. The proposal does not say what licence the ported pack carries.
- `NOTICE.md` and `LICENSE` are two names for one thing (minor, below).

Fix: put the copyright line and the MIT licence name in `PACK.md` Credits, and carry the full notice text in every shipped copy (`NOTICE.md` in the folder, plus the install step, or the notice text in `PACK.md`). Owner decision Q3.

### M10. UMAS documentation drift that this change does not fix, and that §9 currently hides

Evidence:
- `umas/UMAS-BUILD-ASSESSMENT.md:28,89` says "all 6 ladder rungs implemented". Spec line 182 says "rungs 3 to 5 were stubs in code and need no code now". The two UMAS documents contradict each other. Spec §9 is the only place that records the stubs.
- `umas/TECHNICAL-DESIGN-SUMMARY.md:190-197` describes the enforcer as Python with `LadderResult.code_avoided`. That code is in §12 only. After §12 is removed, the claim has no source in the pack.
- `umas/TECHNICAL-DESIGN-SPEC.md:518-527` gives the six rungs and the shortcut form. Check its separator text against the pack's three separators (spec line 107; `PACK.md:89`), which are an em dash, `--`, or a spaced hyphen.
- `umas/UMAS-DNA.md:89-108` (P5) describes the ladder. Footer rule at line 364 says UMAS docs are "updated in the same commit". The proposal does not update them.
- `umas/modules/agent-execution/agent-execution-spec.md:175` has the record row `ms 4.2, 5`, which lists the rungs and not the rules. The change leaves it unchanged, and it will describe 0.1.0.
- The PRD (`umas/unified-multi-agent-system-prd.md:4180-4192`) has an "Off" option the pack does not have. The pack's levels (`PACK.md:93-101`) have no "off".

Fix: the UMAS re-points (task 8) belong in this change, or in a named follow-up with an owner and a date recorded in the task file. The BUILD-ASSESSMENT contradiction must be fixed in the same follow-up.

---

## Minors

- `grep` pattern `/[a-z-]+ ` (task file line 84) matches "and/or " and similar text. Use an anchored pattern with a leading space or a backtick.
- Forbidden-word grep is case-sensitive as written; run it with `-i`.
- `tests/__pycache__/test_check_evidence.cpython-315.pyc` is a stray build artifact (gitignored at `.gitignore:35`). Remove it locally; it is not in the diff.
- Task file "Verification" (lines 94-97) lists "pending" for all four checks. Fill them in after round 2.
- Spec file table (`minimalism-ladder-spec.md:31-36`) omits `scripts/`, `tests/` and `fixtures/RESULTS.md`, and says "F1 to F8 (8)" (line 35). Update both.
- No pack `README.md`. The spec line 3 link points to `packs/README.md`. After the change, a short folder README (no outside links) would help the port. Optional.
- `config.yaml` has no `pack_version` key. Nothing requires one, but the bump has no config-side record.
- Rule text is in two places (`PACK.md` and spec §5.x, and task file lines 26-56). AGENTS.md "Each fact lives in one place" applies. The spec should hold the contract and `PACK.md` the prompt, or the spec should refer to `PACK.md`.
- Spec §5.7 to §5.10 would sit after §5.6 Metrics (lines 119-127). Put the rules before Metrics, or accept the numbering.
- "Bug fixes" heading (proposed) versus "Before you edit a function" in the body. See M6.
- Credits position: the proposal places it after the rules. The licence line is more useful at the top of `PACK.md`, next to the front matter, so a copy that is cut short still carries it.
- Spec §5.5 defines `ultra` as one-line justification and propose-deletion. Ponytail's `ultra` differs (task file line 22 keeps the pack's meaning). Say so in §10.
- `libs/agent-session/README.md:572-575`: `minimalism.ladder_required: true` appears in no pack config. Pre-existing; add to the UMAS follow-up.
- Task 5 ("17 tests pass") cannot fail from this change. The tests do not read `PACK.md`. Say so, or add a check that reads `PACK.md` for the four sections.
- Spec §8.2 criterion 5 (median diff size) is not run. Keep it marked "not run".
- Agent-execution "Where set" column (`agent-execution-spec.md:199-202`) is misleading. Pre-existing.
- `SKILL-ASSESSMENT.md:50` says Known-consumers text "stays in spec section 9". Once §9 is removed, this is false. Add the dated note the defaults already plan, and fix the sentence.
- Acceptance criterion 2 ("the pack's internal relative links resolve") is trivially true once there are no links. Say "there are no relative links".
- Task 2 "returns nothing" over `PACK.md` is correct as long as the rules do not use a vendor name. The word "ponytail" does not match the grep (see check 6).
- `docs/tasks-minimalism-ladder-2026-11-09.md` line 36 test rule: "a new script or app" is not in test-policy. See B2.
- Spec §11 open question 3 (static pre-merge check for rung 4) is unchanged and needs no action.
- A dated ADR for dropping the Known Consumers section is recommended (M2).
- The "own words" criterion (task file line 9) cannot be measured. Replace it with "no sentence of the pack is copied from the upstream file", and say how it is checked.

---

## Answers to the eight checks

1. **Standalone.** Points outside the pack today: spec line 3 (`../README.md`), line 26 (`../../libs/decision-artifacts/README.md`), line 4 (the word "UMAS"), line 189 (UMAS file names), line 210 (`../README.md`), lines 214 and 334 (PART3), line 156 and line 171 ("the source"). `SKILL-ASSESSMENT.md` lines 37, 56, 63, 71, 75, 85, 100, 141 and 145. The `PACK.md` has no paths (checked earlier). Fixtures and `RESULTS.md` not checked for UMAS terms. See M1.

2. **Removing §9 and §12.** No link or anchor breaks. UMAS documents point at the pack file only (agent-execution lines 5, 38, 78, 175, 199-202, 251). The interfaces that lose their documented source: `metrics minimalism` (spec line 184, only source); `project.minimalism.level` and `enforce` (spec line 181); the Developer and Worker prompt prepend (spec line 180); the enforcer rung mapping (spec line 182 and §12.1); the debt-ledger tracking (spec line 183); the router-tier rule (spec line 185); the §12.2 YAML keys. Task 8 is **not enough**, because it is undecided and comes after the deletion. This is B1.

3. **Rules against rungs, stop rule and Requested work.** Scope conflicts with spec §2 line 24 (M4). The bug-fix rule is wider than its heading (M6). The never-cut list repeats and contradicts `PACK.md:69` (M7). The test rule conflicts with test-policy and specialist-agents (B2). None of the rules conflicts with the stop rule itself. All four are ambiguous in at least one term ("non-trivial", "shared code", "never cut", "scope").

4. **Record and schema.** The missing record field does not break `check_evidence.py` or the schema (`additionalProperties: false` is respected; `check_evidence.py` ignores `notes`). It breaks auditability: no record shows the rules ran (M5). The 0.2.0 bump is mechanically safe: `schema/ladder-record.json:12` accepts it and no test reads the version. It is not safe as a claim, because nothing shows the rules were applied.

5. **Licence and credit.** MIT, copyright DietrichGebert (fetch summary, not byte-compared). The notice must travel with the rules. `NOTICE.md` alone is not enough, because only `SKILL.md` is installed (M9). The pack has no licence of its own. This needs an owner decision (Q3).

6. **claude-mods rule (no slash commands, harness APIs, vendor or model names, UMAS wording, Known-consumers text, unverified percentages).** The forbidden-word grep in task 2 (`umas|claude code|codex|copilot|gemini|openai|anthropic|/[a-z-]+ `) does not match "ponytail". The word "ponytail" is the name of a third-party project. It is not a vendor, model or harness name, so naming it does not break the rule as written. The upstream `/ponytail` slash command (upstream line 17) is not copied, so it is not a finding. Caveats: the `/[a-z-]+ ` pattern is not anchored (minor); `SKILL-ASSESSMENT.md` and `RESULTS.md` use harness words ("subagent", "general-purpose subagent", `RESULTS.md:3`), which the rule would flag if these files were part of the shipped copy. They are not in the copy, so this is only a finding if the record moves into the copy.

7. **Testability of F9 to F11 and D3.** F9 and F10 check process, which the record cannot hold, so an independent judge cannot check them from `RESULTS.md`'s method (M8). F11 duplicates F7. There is no fixture for the test rule. Leaving them unrun is acceptable only if spec §8.1 and `RESULTS.md` say "expected, not run". It is not acceptable to report them as passing. D3 (no independent judge) stays open, so the fixtures do not change the state of the pack.

8. **Unobservable acceptance criteria.** Requirement 2 ("in the pack's own words") is not measurable (minor). Task 2 "the pack's internal relative links resolve" is trivially true (minor). Task 5 "17 tests pass" cannot fail from this change (minor). Task 6 cannot pass as written (M1). Scope and test rules have no observable output (M4, M5). "Calibration" and "accessibility" are not observable (M7). Task 1 is done when the verdict is recorded, which is this report.

---

## Owner decisions

Each decision gate sends at most four questions. The four below are the ones the owner must decide before round 2.

**Q1. Where does the removed §9 and §12 content go, and what happens to the source spec?** (B1, M2, M4)
- Context: §9 and §12 are the only documented source for `metrics minimalism`, the enforcer rung mapping and the §12.2 YAML. PART3 is not in the tree. Task 8 is undecided. Today the source spec is `minimalism-ladder-spec.md`, and it is also the UMAS source.
- Option (a), export a standalone copy: keep the source whole. The port copy is produced by a filtered export. Gain: no UMAS contract is lost. Risk: two copies, which must be kept in step. Files: the source spec, plus an export script or a manual filter. Assessed as low risk of loss, moderate risk of drift.
- Option (b), move first: copy §9 and §12 into `umas/modules/agent-execution/agent-execution-spec.md`, then remove them. Gain: one copy in the pack, one in UMAS. Risk: a UMAS change must be reviewed, and task 8 becomes a blocker for task 3. Files: UMAS agent-execution spec, the pack spec.
- Option (c), remove now: the proposal as written. Not recommended. Risk: the contract is lost with no copy (assessed as high impact, not reversible without git history).
- Recommendation: option (a). It keeps every consumer contract in place, and the standalone copy can be checked against the source. It is reversible. Change my mind if the UMAS side commits to task 8 this week, in which case (b) is equal.

**Q2. Which test definition wins when the ladder and test-policy compose?** (B2)
- Context: the ladder rule (task file line 36) says any branch needs a test. Test-policy (`packs/test-policy/PACK.md:75-84`) says "more than a trivial guard". Specialist-agents says "risky logic only" (`specialist-agents-spec.md:118`). `packs/README.md:104-105` composes the two.
- Option (a), the ladder states its own definition, and the composition note says the test-policy definition wins in the Developer pipeline. Gain: each pack keeps its own definition; the pipeline has one rule. Risk: the ladder text and the composition note must agree. Files: `PACK.md`, the spec, `packs/README.md`.
- Option (b), the ladder adopts test-policy's wording in full (copied, not referenced). Gain: one wording in each pack. Risk: copied text drifts from test-policy. Files: `PACK.md`, the spec.
- Option (c), the ladder rule removed. Gain: no conflict. Risk: the new-logic test requirement from ponytail is lost.
- Recommendation: option (a). It keeps packs independent (`packs/README.md` rule 3) and makes the conflict visible. Change my mind if the owner wants the ladder to be the single test rule.

**Q3. Where does the MIT notice sit, and what licence does the port carry?** (M9)
- Context: MIT requires the notice in every copy or substantial portion. Only `SKILL.md` is installed beside `TASK.md` (`libs/agent-platform/README.md:221-281`). The repo root has no `LICENSE`. The pack has none of its own.
- Option (a), notice in `NOTICE.md` plus a copyright line and the licence name in `PACK.md` Credits. Gain: the notice is visible in the installed file. Risk: the full text is in `NOTICE.md` only, so an install that copies `SKILL.md` alone is short of the full text. Files: `PACK.md`, `NOTICE.md`.
- Option (b), the full MIT text in `PACK.md`. Gain: every installed copy carries the full notice. Risk: longer prompt body. Files: `PACK.md`.
- Option (c), `NOTICE.md` only, the proposal as written. Risk: the installed rules may lack the notice (assessed as likely to be a licence gap if the rules are substantial portions).
- Recommendation: option (b), since the rules are adapted and the installed file is the one that travels. Change my mind if the installer copies the whole folder.

**Q4. Bump to 0.2.0 now, or only after a 0.2.0 run?** (M5)
- Context: the bump is mechanically safe (`schema/ladder-record.json:12`). Nothing shows the rules were applied. `RESULTS.md` has only 0.1.0 runs.
- Option (a), bump now, and say in the spec that the 0.2.0 rules are unverified. Gain: the version matches the text. Risk: a 0.2.0 record claims rules it did not apply. Files: `PACK.md:108,120`, spec `:5,:54`.
- Option (b), keep 0.1.0 until a 0.2.0 run is recorded. Gain: the version is a claim with evidence. Risk: the port carries an old version number. Files: none now.
- Option (c), bump, and add a record field for the rules. Gain: the record shows the rules. Risk: a schema change, outside this change, and `additionalProperties: false` must be lifted. Files: schema, `check_evidence.py` (no change needed for the field, per the check), spec.
- Recommendation: option (b). The default in the task file is (a); the assessor recommends (b) because the version is the only audit trail. Change my mind if the owner accepts unverified version claims.

---

## Required before round 2

1. Decide Q1 to Q4 and record the decisions in `docs/decisions/`.
2. Fix B1: keep the source whole, or move §9 and §12 to UMAS first (task 8 done).
3. Fix B2: state the test rule and the composition note.
4. Fix M1: reword spec line 4; remove the `SKILL-ASSESSMENT.md` exemption; run task 6 over all files.
5. Fix M3 and M4: add the Scope step; fix spec §2 line 24; state where the scope list goes.
6. Fix M5: decide the record field question, or state the audit limit in the spec.
7. Round 2: a fresh assessor checks the B1 and B2 fixes only.

Task 1 is complete once the parent records this verdict and the blocker count of 2 in the task file.
