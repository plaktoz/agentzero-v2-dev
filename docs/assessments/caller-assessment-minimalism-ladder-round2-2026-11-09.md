# Caller assessment: minimalism-ladder, round 2

Date: 2026-11-09. Assessor: fresh round-2 assessor (AGENTS.md 2a).
Subject: the fixes for round 1 blockers B1 and B2 ([round 1](./caller-assessment-minimalism-ladder-2026-11-09.md)), per [ADR-0006](../decisions/ADR-0006-minimalism-ladder-adds-ponytail-rules.md) and [the task file](../tasks-minimalism-ladder-2026-11-09.md).
Nothing was edited except this report. No state-changing git command was run. Only `git show HEAD:<path>` was used to read the committed spec.

## Verdict

**ACCEPTED WITH OPEN ITEMS.** Blockers: **0** (B1 fixed, B2 fixed, no new blocker).

The open items are in the "Open items" section. Two of them (O1, O2) are promised by the decisions but not done. Neither stops the pack being copied by the portable set.

## B1. Fixed

Round 1 problem: removing spec 9 and 12 would delete the only copy of the UMAS contracts.

Evidence:

- Sections were not removed. `packs/minimalism-ladder/minimalism-ladder-spec.md:197-209` (section 9, Known Consumers) and `:235-376` (section 12, reference code and YAML) are present. I diffed section 9 to the end of the file against `git show HEAD:` (trailing whitespace ignored). The only differences are three added rows in section 10 (`:222-224`). So every mapping row, the `MinimalismEnforcer` code (12.1) and the YAML (12.2) are unchanged.
- The UMAS side still has its pointers: `umas/modules/agent-execution/agent-execution-spec.md:38,175,199-202,251` and `umas/TECHNICAL-DESIGN-SPEC.md:291,527` link to the spec file, not to an anchor. None breaks.
- The portable set is a named list at `minimalism-ladder-spec.md:40`: `PACK.md`, `config.yaml`, `schema/`, `fixtures/*.yaml`, `scripts/`, `tests/`. The spec, `fixtures/RESULTS.md` and `SKILL-ASSESSMENT.md` stay. `:4` says sections 9 and 12 "are not part of it".

Does the portable set reference outside the pack? No.

- Grep over `PACK.md`, `config.yaml`, `schema/`, `scripts/`, `tests/`, `fixtures/F1..F12.yaml` for `umas|libs/|docs/|packs/README|../|claude|codex|copilot|gemini|openai|anthropic|github|ibm|source|spec|section|RESULTS|SKILL-ASSESSMENT`:
  - `PACK.md:104` says "the file or spec that states the request". This is about the user's request, not this pack's spec.
  - `PACK.md:170` has the ponytail GitHub URL. This is the credit.
  - `tests/test_check_evidence.py:123` has `"../record.json"`. This is a test input for path escape, not a reference.
  - Nothing else matched. `scripts/check_evidence.py` and the tests find the pack through `__file__` (`tests/test_check_evidence.py:15`).
- No PACK.md text refers to a section number of the spec, to `RESULTS.md`, to `SKILL-ASSESSMENT.md`, or to a fixture ID. The PACK.md section titles it cites ("Read first", "Scope", "Bug fixes", "Tests for new logic", "Never cut", "Evidence", "Enforcement levels", "Output record", "Prompt", "Stop rule") all exist (`PACK.md:33-168`).
- `PACK.md` can be used alone. It has the steps, the prompt, the record format and the licence. `config.yaml` is optional.

Residual (not a blocker): round 1 asked, "in either case", to reconcile the 12.2 YAML keys (`enforcement_level`, `ladder.*`, `metrics.track_*`) with the section 6 keys (`level`, `enforce`, `record`). This was not done (see O3). It is pre-existing and nothing was lost, so it does not reopen B1.

## B2. Fixed for the case round 1 named; one narrower divergence remains

Round 1 problem: the ladder said "a branch" needs a test. Test-policy says only branching "more than a trivial guard" does.

Evidence:

- `PACK.md:85` now says: "a branch beyond a trivial guard, a loop, a parser, money, security, state that depends on ordering or retries, or a whole new script or app". Compared with `packs/test-policy/PACK.md:75-84`:

  | Kind | Test-policy | Ladder (`PACK.md:85`) | Same answer? |
  |------|-------------|-----------------------|--------------|
  | branching | more than a trivial guard | beyond a trivial guard | yes |
  | loop | yes | yes | yes |
  | parser | yes | yes | yes |
  | money | yes | yes | yes |
  | security | yes | yes | yes |
  | state | concurrency, retries, caching, anything with ordering | ordering or retries only | ladder narrower: caching and concurrency are not named |
  | new script or app | not a kind; "glue calls are not risky" (`:84`) | needs a check | no |

- The round 1 failure case (`if x is None: return`) now gives the same answer in both: no test needed.
- `PACK.md:85` ends: "A test policy, where one is in use, decides whether a missing test blocks the change. This rule only says new logic is not left without a check." Spec `:143` says the same. So the ladder itself never blocks on a test. The gate answer comes only from test-policy. For the gate, the two packs cannot give different answers.
- Test-policy `selective` mode (`:62-67`) and `strict` mode both fit with this: strict adds a requirement; the ladder defers to it.
- `packs/specialist-agents/specialist-agents-spec.md:118-119` is unchanged: "Add tests for risky logic only (branches, loops, parsers, money, security)". `:212` still says the ladder prompt is part of the Developer preamble.
- F12 (`fixtures/F12.yaml`) is a test-rule fixture, so M8 from round 1 is addressed. It is not run.

Where the two still differ (see O1): a whole new script or app made only of glue calls. Ladder: a check is needed and must be named in `notes`. Test-policy: not risky, so no test is required. Developer prompt: "risky logic only". Effect: the Developer agent is asked for a check that the policy would not demand. It is non-blocking, so I rate it major, not blocker. A narrower miss exists on caching and concurrency (ladder silent, policy says risky); the policy still gates it.

"Which wins" statement:

- Present where the ladder is read: `PACK.md:85` and spec `:143`. It settles who decides blocking.
- Absent where a composing consumer reads: `packs/README.md:89-114` (Composition Map, `minimalism-ladder + test-policy` at `:104`) has no note. `specialist-agents-spec.md:118,212` has none either. A search of `packs/`, `umas/`, `libs/` finds no "wins" or "precedence" statement for this pair.
- Classification: **not a blocker, a major (O2).** Reason: the only point where the two could produce a conflicting gate is already settled inside the ladder (`PACK.md:85`), and the remaining divergence is non-blocking. But Q2(a) in ADR-0006 and in the task file (`:109-113`) promised "a composition note says which one wins in the Developer pipeline", and no task or file delivers it. The ADR Q2 row describes only the in-pack wording.

## New blockers

None. Checks:

1. Contradictions inside `PACK.md` between Never cut, Requested work, Scope and the six rungs: none found.
   - Rung 1 ("not asked for, do not build", `:50`) against Never cut ("even when the task does not name them", `:89`): `:77` already separates them ("The ladder bounds new code; it does not remove required behaviour. 'Never cut' lists what is kept even when the task does not name it"). Consistent.
   - Scope (`:43`) against rung 1: reach the task needs is finished; extra features "fall at rung 1". Consistent.
   - Step 5 (`:28`) writes "what the stopping rung needs ... keeping everything in Never cut". Consistent with rungs 1 and 2, where little is written.
   - Level note (`:132`) says Scope, Bug fixes, Tests and Never cut "apply in full" at every level, and the level table (`:128`) says lite rungs 3 to 6 are advice. These do not collide because the note limits the level to "how strictly rungs 3 to 6 are enforced". See minor m2 for one ambiguity.
   - Steps 1 to 8 (`:24-31`) each point to an existing section.
2. MIT text: the 17 non-blank lines of `/tmp/ponytail-license/LICENSE` match `PACK.md:172-192` exactly after removing indentation. Blank-line layout is the same (21 lines each). Caveat: that LICENSE file is a local copy fetched earlier today. I could not byte-compare it to upstream commit `96608e0`. The same caveat was in round 1.
3. Vendor and slash commands: `PACK.md` has no slash command and no vendor or harness name. The only brand strings are the credit line (ponytail, DietrichGebert, GitHub URL) and the licence holder. The credit is required, so it is not a finding.
4. Tests: `cd packs/minimalism-ladder && python3 -I -m unittest discover -s tests` ran 17 tests, OK. Also OK when run from `/tmp` with an absolute `-s` path. Not run on Windows (verified by reading only: `check_evidence.py:49,97` use `Path`, replace backslashes, and open files with `encoding="utf-8"`).

## Open items (majors, none blocking)

- **O1. New script or app, and state, are not aligned with test-policy** (`PACK.md:85`, spec `:143`). Spec `:143` says the kinds "are worded to match" test-policy, which is true for six of the seven items. Either drop "a whole new script or app" or say the check is advice only. Either way, add the missing state words (caching, concurrency) or say the list is a subset.
- **O2. No composition note** in `packs/README.md:98-110` or `specialist-agents-spec.md:118,212`. Add one line: the test policy decides which changes need a test and whether a missing one blocks; the ladder only requires a check on new non-trivial logic. This was promised by Q2(a). The task file has no task for it. Add one so the state is not lost.
- **O3. 12.2 YAML keys are not reconciled with section 6 keys** (`minimalism-ladder-spec.md:365` against `:152`). Section 12 says the sections above win "where they differ (see section 10)" (`:237`), but section 10 has no row for this. Add a row.

## Minors

- m1. The task file's Requirement 1 (`tasks-minimalism-ladder-2026-11-09.md:8`) still says "The pack folder has no link or reference to files outside itself". After Q1 this is true only for the portable set. Reword it. Task 8 (`:96`) and the State log still say round 2 "started"; update them with this verdict.
- m2. Level `lite` (`PACK.md:128`) says "Do not block on them" for rungs 3 to 6, and `:132` says Tests for new logic applies "in full" at every level. It is not stated whether a missing check at `lite` is a finding. The ladder does not block (`:85`), so this is harmless, but say it.
- m3. `PACK.md:57` says "Do not add ... fallbacks that the task did not ask for". Never cut (`:92`) keeps "error handling that prevents data loss". These are compatible, but an agent could read the first as cancelling the second. One cross-reference would settle it.
- m4. `packs/minimalism-ladder/tests/__pycache__/test_check_evidence.cpython-315.pyc` sits inside a portable directory. It is git-ignored (`.gitignore:35`) and not tracked, but a copy by directory name would carry it. Exclude `__pycache__` in the port instruction.
- m5. `PACK.md:3` description is now 315 characters (283 before, `git show HEAD:`). The SKILL.md contract in `libs/agent-platform/README.md:238` says max 140 characters, and commit `0e8cd0d` shortened the text "for skill install". The old text already exceeded 140, so this is not new. Whether a target harness truncates it is not verified.
- m6. F12 (`fixtures/F12.yaml`, last expectation) holds an expectation about a "second input" that the fixture does not contain. Split it into its own fixture or drop it.
- m7. Four blank lines inside the licence block (`PACK.md:173, 175, 182, 185`) hold four spaces instead of being empty. Cosmetic.
- m8. `PACK.md:136` and `:81` use "evidence" for a caller search result "as the file that holds it". This works with `check_evidence.py` (a path that exists), but it records the shared file, not the search. This is by design in the Bug fixes text; the limitation is already listed in the task file Verification section.
- m9. All of this work is uncommitted (git status at session start). The B1 safety check above is against the working tree. Commit only if the owner asks (AGENTS.md).

## Method and limits

- Read in full: `PACK.md`, the spec, `config.yaml`, ADR-0006, the task file, round 1 report, F9 to F12, `packs/test-policy/PACK.md` lines 1 to 110, `specialist-agents-spec.md` lines 105 to 130 and 200 to 225, `packs/README.md` lines 85 to 120.
- Checked by command: spec section 9 to end against `HEAD`; grep over the portable set; MIT comparison; the 17 tests.
- Not checked: Windows run; the upstream commit `96608e0` byte-for-byte; any harness limit on description length; UMAS docs that describe the enforcer (outside B1 and B2, and task 9 records them as not changed on purpose).
