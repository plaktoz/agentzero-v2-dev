# minimalism-ladder: skill assessment

Date: 2026-10-25. Pack version: 0.1.0. Assessed files: `PACK.md`, `schema/ladder-record.json`, `fixtures/F1.yaml` to `F8.yaml`, `fixtures/RESULTS.md`, `scripts/check_evidence.py`, `tests/test_check_evidence.py`, `config.yaml`, `minimalism-ladder-spec.md`.

## 1. Verdict

**`skill`.** Build or enhance as a skill.

Reason: no installed skill makes an agent check reuse, the standard library and installed dependencies before it writes code. See section 3.

## 2. Fit evidence

The skill works in one session with no other system around it.

- The agent reads the files that the task touches and their call sites.
- The agent walks six rungs and stops at the first that holds.
- The agent writes the change and emits one JSON record.
- An optional script checks that each evidence path or symbol exists in the repository.

The folder holds everything the agent needs: `PACK.md` (the prompt and rules), `schema/ladder-record.json` (the output), and `config.yaml` (the defaults). The agent also needs the repository, which it already has.

User inputs:

- `task`: required.
- `level`: `lite`, `full` or `ultra`. Default `full`.
- `project_notes`: optional.

The earlier fixture runs used fresh subagents with only `PACK.md` and the fixture input. Their results are in `fixtures/RESULTS.md`. This assessment did not repeat those runs.

## 3. Overlap

I read the five installed skills that the brief lists. Each row quotes the line I based the comparison on.

| Skill | What it does (quoted line) | What this pack adds or lacks |
|-------|----------------------------|------------------------------|
| `tdd` | "Red before green. Write the failing test first ... Don't anticipate future tests or add speculative features." | Covers the test loop only. The pack adds the reuse, standard-library and dependency rungs before code. `tdd` has no reuse check. |
| `implement` | "Use /tdd where possible ... Once done, use /code-review to review the work." | Runs implementation in order. The ladder would sit before its implementation step. `implement` has no reuse or dependency check. |
| `improve-codebase-architecture` | "Apply the **deletion test** to anything you suspect is shallow." | Finds deepening work in existing code. The pack checks new code before it is written. Neither covers stdlib or dependencies. |
| `codebase-design` | "**The deletion test.** Imagine deleting the module." | Gives vocabulary for module design. The pack adds a fixed order of checks per change. The deletion idea appears in both, at different times. |
| `code-review` | "**Speculative Generality** ... delete it; inline back until a real need shows." and "behaviour in the diff that wasn't asked for (scope creep)". | Reviews a diff after it exists. The pack applies the same idea before the code exists, and it requires an evidence record. |

Result: partial overlap in idea, no overlap in process. The pack is not a `duplicate`.

## 4. What blocks it as a skill today

Each item was checked by grep or by reading.

- **UMAS wording:** none in `PACK.md`. The forbidden-word grep returned no lines.
- **Harness wording:** none in `PACK.md`.
- **Known consumers text:** none in `PACK.md`. It stays in spec section 9.
- **Unverified figures:** none in `PACK.md`. The 53, 26 and 41 percent figures appear only in the spec (sections 8.2 and 10).
- **Schema:** present. The repo tests do not check it. It was checked only in a temporary venv outside the repo.
- **Fixtures:** present (F1 to F8). Three PASS results carry caveats, and two stored results do not match their fixture text. See section 6.
- **Judging:** the author of `PACK.md` judged all eight results. No independent judge has done this check yet.
- **Test data:** the evidence checks ran against synthetic repositories, not real project trees.
- **Dependency on another pack or lib:** none in `PACK.md`. The spec names `decision-artifacts` in sections 2 and 9, and `PACK.md` does not.
- **Spec gap:** spec section 8.2 criterion 1 names a dependency check (`package.json` and lockfile). `check_evidence.py` does not run it.

## 5. Enhancements, in priority order

1. Decide the fixture questions in section 6 (D1 and D2). Until then the fixture set cannot support an "all pass" claim.
2. Get an independent judge for F1 to F8 (D3).
3. Add a schema test to `tests/`, so the repo suite checks `schema/ladder-record.json`. The `test-policy` pack already uses this pattern (`scripts/test_schema.py`, per the owner task file).
4. Add the dependency check from spec section 8.2 to the script, if the owner wants it. This needs a manifest reader for each language (spec section 11, question 3).
5. Run acceptance criteria 3 to 5 (`lite`, `ultra`, and the 20-task diff) or keep them marked "not run". `PACK.md` does not claim them.

## 6. Decisions needed from the owner

### D1. Language of fixtures F1, F5, F6, F7 and F8

The owner task file names only F5. A search shows that four more fixtures use TypeScript, React or Express code: F1 (React), F6 (Express), F7 (Express) and F8 (`src/export/job.ts`).

Facts:

- The project `CLAUDE.md` allows Python or TypeScript. Python is the default.
- Python-first is a default, not a ban. The current fixtures do not break the rule, but they do not match the Python default.
- Rewriting F5 in Python with the standard library `csv` module changes the expected rung. Node has no CSV parser in its standard library, but Python has one. The rung would move from 4 to 3, and F5 would no longer test rung 4.

Options:

- (a) Rewrite F5 in Python with a third-party CSV parser listed in the project manifest. Keeps rung 4. Decide the package.
- (b) Rewrite F5 in Python with the standard library `csv`. Changes the expected rung to 3 and the expectation text.
- (c) Keep F5 in TypeScript as a non-Python example, and record the reason.

Recommendation: option (a), as recorded in the owner task file ("rewrite in Python"). Decide F1, F6, F7 and F8 together with F5.

### D2. Stored results that do not match their fixture text

`RESULTS.md` marks both results PASS. On a strict reading, neither matches.

- **F4.** The fixture expects a record with rung 6, or with the reads shown as pending. The stored rerun record has rung 5, with reads done and empty evidence.
- **F6.** The fixture expects rung 1 (`not_needed`, `skip`). The stored record has rung 6. The record notes that the caching was dropped. The task also asks for the endpoint, which is built, so the record covers a mixed task.

Options:

- (a) Keep the record and change the fixture expectation. For F6, first state a rule for mixed tasks. For F4, accept any rung with reads done and no reuse claim.
- (b) Change the record so it matches the fixture. For F6 this means a rule that the record is rung 1 for a mixed task. The spec does not define that.
- (c) Mark F4 and F6 FAIL in `RESULTS.md`.

Recommendation: decide the mixed-task rule first, then pick (a). The brief bars changing fixture expectations without an owner decision, so this assessment changes neither.

### D3. Independent judge

No independent judge has checked F1 to F8. The judgement must come from someone other than the author of `PACK.md`.

Recommendation: a fresh subagent, given only the fixture and `PACK.md`, judges each stored record. Use the owner's chosen model family.

## 7. Changes made

Changes are to `PACK.md` only. The rules, the prompt, the shortcut format, the levels and the fixture expectations did not change.

1. **Front matter `description`.** Replaced the long list with a shorter list of rungs. Replaced the trigger "Use before writing any change that adds code, files, or dependencies" with "Use when a task asks for code, a file or a dependency to be added, before the first line is written." The trigger is still the last sentence.
2. **Added "Not this skill".** Four boundaries, each from the spec: no design review (spec section 2, non-goal "Judging design quality"), no debt scan (section 2, "Tracking debt"), no dropping requested work (section 7, "Ladder treated as permission to refuse work"), no savings estimate (section 2, "Guaranteeing savings").
3. **Added "Steps".** Six steps, each with a completion criterion. Each step points to an existing section and does not repeat it.
4. **Output sentence.** Changed "report the rung and evidence in your answer" to "state in your answer the rung, its `rung_name` and each `evidence` entry, then emit this JSON object". The old text did not say that the answer and the JSON must agree.
5. **Example record.** Changed the example `evidence` path from `src/forms/booking.tsx` to `path/to/module.ext`. The old path is not in the pack and is a project path.

## 8. Checks run

Each result is the real output.

- Forbidden-word grep over `PACK.md` (`umas|claude code|codex|copilot|gemini|openai|anthropic|/[a-z-]+ `): no output, exit 1. No exclusions were needed.
- Front matter keys: `['description', 'name']`. `name == folder`: `True`.
- File paths named in `PACK.md`: the pattern matched none.
- Banned-word grep over `PACK.md` (from `ste-docs`): no output, exit 1.
- `python3 -I -m unittest discover -s tests`: `Ran 17 tests in 1.153s` then `OK`.
- `schema/ladder-record.json`: valid JSON. Valid under Draft 2020-12 `check_schema` (checked in a temp venv outside the repo, with jsonschema 4.26.0).
- Fixtures F1 to F8: parsed with PyYAML 6.0.3 in the temp venv. All eight load and have `id`, `input` and `expect`.
- Stored records: `fixtures/RESULTS.md` has eight JSON blocks. All eight validate against the schema. The `PACK.md` example validates.
- Cross-platform, `check_evidence.py`: verified by reading only. It uses `pathlib`, `encoding="utf-8"` and backslash handling for Windows paths, and it has no POSIX-only calls. Tests ran on macOS only.

Not run:

- Fixtures F1 to F8 against a model in this session: not run. The earlier results are in `fixtures/RESULTS.md`.
- Acceptance criteria 3 to 5: not run.
- Judging of the fixtures by a person or an independent judge: no independent judge has done this check yet.

## 9. Format decision

The brief sets this file name and six-part structure. `ste-docs` expects a `README.md` and `README.html` pair with the eight-section technical layout. This file follows the brief. The `ste-docs` writing rules and banned-word list were applied. No HTML pair was written. The owner or coordinator decides whether to add one.

## 10. Git state (observed, not changed)

`git status` shows `packs/minimalism-ladder/README.md` as deleted in the working tree. The file is tracked in `HEAD`. This task did not change it.
