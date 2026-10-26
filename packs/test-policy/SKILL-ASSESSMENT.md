# test-policy: skill assessment

Date: 2026-10-25. Scope: this pack only. Brief: `docs/brief-pack-skills-2026-10-25.md`. Earlier verdict: `docs/assessments/skills-for-claude-mods.md` row 3 ("Skill; partial overlap with `tdd`").

## 1. Verdict

**`skill`.** It answers one question that no installed skill answers (which parts of this change need tests, and are they there), it works on a diff with no other system around it, and it has a record schema, fixtures and a deterministic pre-filter.

## 2. Fit evidence

What one session does with nothing else around it:

1. The user names a change (a diff, or a branch and its base) and optionally a mode.
2. The agent gets the diff, finds the existing tests by searching the project, and runs `scripts/prefilter.py` if Python is present.
3. On `trivial` it emits a fixed record and stops. Otherwise it splits the diff into units, marks the risky ones, lists concrete cases per unit, matches them against existing tests, and sets the gate.
4. It emits one JSON record. The record validates against `schema/assessment.json`.

Can an agent follow it with only the files in the folder? Yes. Every file `PACK.md` names exists. The script and schema are optional: without them the agent applies the same rules by reading, and the body says so.

Inputs needed from the user: the change to assess. Mode, existing tests and coverage are optional with stated defaults (`selective`; found by search; not run).

Cost of use: one classification pass per non-trivial change. Not run against a model in this assessment; see section 7.

## 3. Overlap

| Installed skill | What it does | What test-policy adds or lacks |
|---|---|---|
| `tdd` | Test-first loop. Quote: "TDD is the red → green loop." Rules: "**Red before green.** Write the failing test first, then only enough code to pass it." It also says where tests go: "**Test only at pre-agreed seams.**" | Adds the decision tdd never makes: which units of a change need tests at all, by risk kind, and a gate. Lacks everything about how to write a good test, seams, mocking and the loop. No conflict if the boundary holds (see below). |
| `qa` | Files bug reports as issues. Quote: "Run an interactive QA session. The user describes problems they're encountering." The only test mention is about issue dependencies. | No overlap. The name is similar; the job is different. |
| `code-review` | Two-axis review of a diff: Standards and Spec. The text has no mention of tests. | Adds a test-coverage question neither axis asks. Could feed the Standards axis as an extra check, but nothing in `code-review` consumes it today. No duplication. |
| `to-spec` | Writes a spec from the conversation. Quote: "Sketch out the seams at which you're going to test the feature." Template section: "## Testing Decisions ... Which modules will be tested". | Different time and scope. `to-spec` plans testing for a feature before it exists; test-policy audits a finished diff. test-policy could supply the risky-kind list for the "Which modules will be tested" line, but it takes a diff, not a conversation. |

The boundary with `tdd`: `tdd` is how to write the test and in what order. test-policy is whether a test is needed and whether it exists. test-policy now says so in a "Not this skill" section, drops the "failing test first" wording from strict mode, and lists in Limits that it cannot see the order of writing.

`implement`, `triage`, `to-tickets` mention tests only in passing ("single test files regularly", "verify the claim"); no overlap.

## 4. What blocks it as a skill today

Found before the changes in section 5:

- The pre-filter command was `python scripts/prefilter.py`. It fails on macOS without a `python` shim. It also used a path relative to the pack, which breaks once `PACK.md` is copied to a skill folder elsewhere.
- No procedure. `PACK.md` had policy and a classifier prompt, but no ordered steps for getting inputs, in particular no step for finding `existing_tests` when the user gives none.
- No "not this skill" boundary beyond one sentence; the strict-mode wording ("a failing test exists before the code") overlapped `tdd`.
- The record example omitted `pack_version`, which the spec requires outputs to echo.
- The trivial rule pointed at `config.yaml`; if only `PACK.md` is installed the agent had no globs.
- The `description` did not say what comes back.

Not blockers: no UMAS wording, no harness wording, no vendor names, no unverified figures, no dependency on another pack or lib. Checked with the grep in section 6.

## 5. Changes made

All in `PACK.md` unless stated. No rule, schema or fixture expectation changed.

1. `description`: rewritten to state the decision (what needs tests, whether the existing tests are enough) and the two modes, in one trigger. Kept to two sentences.
2. Added section "Not this skill": no test-first loop, no writing or running tests, no coverage measurement, no framework or seam choice, no style, design or spec review.
3. Added section "Procedure": seven ordered steps, each with a completion condition (get inputs, pre-filter, split into units, classify, match existing tests, gate, emit). Includes how to find `existing_tests` when none are given.
4. Pre-filter command: now `python3 -I <pack>/scripts/prefilter.py` for macOS and Linux, `python -I ...` for Windows, plus the stdin form. The `<pack>` placeholder replaces the relative path. States that without Python the agent applies the trivial rule by reading and answers `needs_model` when unsure.
5. Trivial rule: the default exempt globs and extensions are written into `PACK.md`, so it works without `config.yaml`. Marked as the `config.yaml` defaults.
6. Strict mode: intro and Policy row now say "a test exists before the change, or is added in the same change", which matches the Gate. The "failing test" wording is gone.
7. Added `pack_version` to both example records and to the field table.
8. Files table: added `yaml_subset.py`, the two test scripts and `fixtures/RESULTS.md`; marked the script, tests and fixtures as optional or for maintainers; added a note on relative paths.
9. Classifier prompt intro: says steps 3 to 6 apply it, by the agent itself or by a separate reviewer if the setup has one. No harness term.
10. Limits: added that the skill sees the finished diff, not the order of writing.
11. `scripts/prefilter.py`, `scripts/test_prefilter.py`, `scripts/test_schema.py`: `python` changed to `python3` in the shebang and in the usage comments. No code change.
12. "100 percent" in the Gate text changed to "full coverage" so the body holds no percentage figure.

The `README.md` that git shows as deleted in this folder was deleted before this work; I did not touch it.

## 6. Verification (2026-10-25, macOS)

Passed:

- Front matter has exactly `name` and `description`; `name` is `test-policy`, equal to the folder.
- `grep -i -E "umas|claude code|codex|copilot|gemini|openai|anthropic|/[a-z-]+ "` over `PACK.md`: no match.
- No percentage figure and no "Known consumers" text in `PACK.md`.
- Every path named in `PACK.md` exists (9 files, plus `fixtures/F1.yaml` to `F10.yaml`).
- `schema/input.json` and `schema/assessment.json` load as JSON. Both JSON examples in `PACK.md` validate against `schema/assessment.json` (checked in a temporary venv with `jsonschema`; the venv was deleted).
- Fixtures, `config.yaml` and `risky-patterns.yaml` parse with PyYAML in that venv.
- `python3 -I -m unittest discover -s scripts`: 45 tests, OK, 9 skipped (the schema tests skip without `jsonschema`). With `jsonschema` and PyYAML installed: 45 tests, OK, none skipped.
- Pre-filter on each fixture diff: F1 to F3 `trivial`, F4 to F10 `needs_model`. It also runs from a different working directory and on empty standard input (prints `trivial`).

Verified by reading only:

- Windows. The scripts use `pathlib` and `PurePosixPath`, open files with `encoding="utf-8"`, write bytes to stdout and stderr, and convert `\` to `/` in diff paths. I found no `HOME` use, no POSIX-only call and no `shell=True`. CRLF input is covered by a unit test that ran on macOS only. The `python -I` command on Windows is unrun.
- Codex and Copilot loading `SKILL.md`: not tested. The body names no harness feature.

Pre-filter edge noticed, not changed: empty input returns `trivial`. A caller that passes an empty diff by mistake gets "no tests needed". Step 1 requires a non-empty diff, so the skill does not reach this case.

## 7. Fixtures F1 to F10: not run

I did not run any fixture against a model. `fixtures/RESULTS.md` holds an earlier run by sub-agents of the same model family as the author; it is a single sample per fixture and I did not re-judge it. The `PACK.md` change (new Procedure section, new wording) means that run was against the earlier text.

| Fixture | Expectation | Pre-filter (run) | Model run |
|---|---|---|---|
| F1 | rename across two files is trivial | trivial | not run |
| F2 | README edit is trivial | trivial | not run |
| F3 | config value change is trivial | trivial | not run |
| F4 | new `calculate_total`, no test: `missing_tests`, money | needs_model | not run |
| F5 | date parser slash branch, ISO-only test: `missing_tests`, parser | needs_model | not run |
| F6 | code added with tests: `ok`, `present` true | needs_model | not run |
| F7 | getter and setter: `ok` in selective, `missing_tests` in strict | needs_model | not run |
| F8 | strict, new feature, no test: `missing_tests` | needs_model | not run |
| F9 | glue code: `ok`, no unit required | needs_model | not run |
| F10 | docs edit plus authorisation check: `missing_tests`, security | needs_model | not run |

## 8. Enhancements still open (priority order)

1. Re-run F1 to F10 against the current `PACK.md`, with the Procedure, in a clean agent that has only the folder. Add a second sample for F5 and F9, the two the earlier run flagged as weakest.
2. Add a fixture for a missing `existing_tests` input where the agent must search the project. The current fixtures all pass `existing_tests` in.
3. Add a fixture for a change that is test files only. The prompt says "do not list test files as units"; nothing exercises it.
4. A one-line pointer from `code-review` to this skill would make the Standards axis ask the test question. That is an edit to another skill; offered, not made.
5. Decide whether `yaml_subset.py` should stay in the skill folder. It only serves the pre-filter and the tests.

## 9. Decisions needed from the owner

1. **Install form.** `scripts/` is optional in `PACK.md`, so `PACK.md` copied alone to `SKILL.md` works but loses the pre-filter and the schema check. Options: (a) install the whole folder with `PACK.md` renamed `SKILL.md` (recommended; every path then resolves); (b) install `SKILL.md` only and accept the by-reading fallback.
2. **Strict mode wording.** The pack's spec (section 5) says strict means "red, green, refactor: a failing test exists before the code". The skill now says "exists before the change, or is added in the same change", because a diff cannot show the order of writing. The Gate rule is unchanged. Recommend keeping the new wording; the change to the spec text is the owner's, since I did not edit the spec.
3. **Empty diff.** Should the pre-filter exit non-zero on an empty diff instead of printing `trivial`? Recommend leaving it: the skill's step 1 already stops on an empty diff.
