# Tasks: build three packs and list them in claude-mods

> **Date:** 2026-10-25 · **Source:** [skills-for-claude-mods.md](./assessments/skills-for-claude-mods.md) · **Target:** `plaktoz/claude-mods`, local clone `~/Developer/claude-mods`

## Decisions (user, 2026-10-25)

| Question | Decision |
|----------|----------|
| Where to build | In `packs/<name>/` here first, then copy to `claude-mods/skills/<name>/` |
| `SKILL.md` format | Neutral and Claude Code: `name` and `description` front matter, and a body with no slash commands, no harness APIs, no model or vendor names |
| Model fixtures | One subagent per skill runs them and reports pass or fail per fixture |
| Commits and pushes | Not asked. Do not commit or push |

## Defaults picked

- The skill body holds the prompt, rules and output record only. It does not hold "Known consumers", UMAS wording, `pack_version` echo rules, the independence-rule text or the unverified percentage figures.
- Scripts are Python, stdlib only, `encoding="utf-8"`, `pathlib` for paths, no POSIX-only calls, run as `python` (not `python3` only).
- Windows is "verified by reading". This machine is macOS.
- The skill's `PACK.md` carries the `SKILL.md` front matter, so the copy to claude-mods is `PACK.md` to `SKILL.md` plus the side files.

## Tasks

Tasks 1 to 3 are independent and run as parallel subagents. Tasks 4 to 6 depend on them.

### 1. minimalism-ladder
- [x] Built 2026-10-25 by a background subagent. `python3 -m unittest discover -s tests` gives 17 tests, OK (Python 3.15.0, macOS). Fixtures F1 to F8 run and recorded in `fixtures/RESULTS.md`: all pass, with caveats F5, F6, F7. Open: (a) F5 is written in TypeScript, which conflicts with the Python-first rule; decide whether to keep it as a non-stack fixture or rewrite it in Python; (b) judging was done by the agent that wrote `PACK.md`, not an independent judge; (c) acceptance criteria 3 to 5 (`lite`, `ultra`, 20-task diff) not run; (d) the schema is not checked by the repo tests (checked once in a temporary venv); (e) Windows and Linux verified by reading only.
- Built: `packs/minimalism-ladder/`: `PACK.md`, `schema/ladder-record.json`, `fixtures/*.yaml` (F1 to F8), `config.yaml`, `scripts/check_evidence.py` plus its test.
- **Acceptance:**
  - `PACK.md` has the front matter, the six-rung prompt, stop rule, read-first rule, shortcut format and the three levels. It has no UMAS wording and no savings figures.
  - The record validates against the schema.
  - `check_evidence.py` exits non-zero for a record whose evidence path or symbol does not exist, and zero when it does. The test covers both.
  - The subagent runs F1 to F8 against the built skill and records pass or fail for each.
  - The script has no cross-platform findings.

### 2. test-policy
- [x] Built `packs/test-policy/`: `PACK.md`, `risky-patterns.yaml`, `schema/assessment.json`, `schema/input.json`, `fixtures/F1–F10.yaml`, `fixtures/RESULTS.md`, `config.yaml`, `scripts/prefilter.py`, `scripts/yaml_subset.py`, `scripts/test_prefilter.py`, `scripts/test_schema.py`. Verified 2026-10-25: `python3 -I -m unittest discover -s scripts` in a temp venv with `jsonschema` and PyYAML gives 45 tests, OK, no skips. The pre-filter on each fixture diff gives F1–F3 `trivial` and F4–F10 `needs_model`. Fixture verdicts (F1–F10) were judged by fresh subagents of the same model family, not by me; I did not re-judge them. Deviations: rename detection added (`rename_min_occurrences`); a stdlib YAML subset reader; a kind priority order; the security pattern widened to `admin`, `role`, `owner`. Windows: verified by reading only. `PACK.md` says `python scripts/prefilter.py`, which fails on macOS without a `python` shim; use `python3` there.
- **Acceptance:**
  - `PACK.md` has the front matter, the two modes, the risky-logic definition, the classifier prompt and the gate rules. It sets no default coverage target.
  - `prefilter.py` returns only `trivial` or `needs_model`. F1 to F3 return `trivial`; F4, F5, F10 return `needs_model`. The same input gives the same output.
  - The output validates against the schema, and each `tests_required` unit lists at least one case.
  - The subagent runs F1 to F10 against the built skill and records pass or fail for each.
  - The script has no cross-platform findings.

### 3. anti-slop
- [-] Built `packs/anti-slop/` (`PACK.md`, `phrases.yaml`, `schema/review-output.json`, `fixtures/F1–F10.yaml`, `config.yaml`, `scripts/lint.py`, `scripts/test_lint.py`, `fixtures/RESULTS.md`, `fixtures/PROVENANCE.md`). **Not done: acceptance not met, four decisions open.** Re-run by me (2026-10-25): `python3 -I -m unittest discover -s scripts` gives 29 tests, 2 failures, matching the subagent's report. `grep` of the pack (excluding `README.md`, the design record, and fixture text) finds no UMAS, vendor or harness wording in `PACK.md`.
  - Fixture results: pass F1, F2, F4, F7, F9, F10; fail F3, F5, F6, F8. Idempotence holds on all ten. All 20 records validate against the schema.
  - Failing tests: criterion 2 (F1 revised text drops the name "AI") and criterion 4 (F3 revised text keeps "at scale", which is in `phrases.yaml`).
  - Deviations: "Not this skill" is generic and does not name `edit-article` or the `writing-*` skills (not read, and the pack body must not name tools). `phrases.yaml` has more phrases than the spec's nine. F8 input was rewritten five times after seeing outputs, so its result is weak. Judge was the author, each fixture ran once.
  - **Decisions made (owner, 2026-10-25):** (1) Writing rule 3 now removes a vague phrase when the sentence keeps its facts, instead of flagging it (`PACK.md`, F3 expectation). (2) Only rule 3 may change behaviour; F6 expects the `try`/`except` removed and the `None` check kept and flagged. (3) F5 expects no abstract base class, factory or single-implementation interface, not "a single function". (4) Licence: owner confirmed the seed text may be used and published; recorded in `fixtures/PROVENANCE.md`.
  - **F3 re-review (2026-10-25): done.** Owner decision C4 = B: three fresh reviewer runs (3, 4, 5), each with a second pass, and a fresh judge; pass if at least two of three meet criteria 4 and 5. All three meet both: phrase lint gives `phrase_hits: []` on each revised text, and pass 2 gives `changes: []` on each. The three revised texts are byte-identical, so this is one sample judged three times, not three measurements. The judge was a model, not a person. Evidence: `packs/anti-slop/fixtures/outputs/runs/F3.run{3,4,5}.{json,revised.md,pass2.json}`. Run 2 is kept as `F3.run2.*` and failed criterion 5. Details in `fixtures/RESULTS.md`, "F3 re-review". This supersedes the F3 items in the failing-tests bullet above and the criterion 4 note below. Still open: the F3 unit test fails because `outputs/F3.revised.md` still holds run 2's text.
  - **Status stays `[-]`, and not only because of F3.** Open: the criterion 2 wording (F1 drops "AI"; the test now passes, RESULTS.md still records a fail), the F5 rewrite in Python (D4), the D6 pack recommendations, and the SKILL-ASSESSMENT criterion-2 wording. The F3 result does not change the status.
  - **Not yet re-run (before the F3 re-review):** the saved reviewer outputs for F3, F5 and F6 predate these changes. Tests still give 29 run, 2 failures (2026-10-25). Criterion 4 (F3 "at scale") should pass once F3 is re-reviewed. Criterion 2 (F1 drops "AI"): owner decided 2026-10-25 to keep the criterion as written. A name removed with a deleted slop sentence counts as dropped, so F1 fails criterion 2 and the pack stays `[-]` until it is accepted or the input is changed by the owner.
  - Windows/Linux: verified on macOS (Python 3.9, 3.11, 3.15); Windows by reading only.
- **Acceptance:**
  - `PACK.md` has the front matter, the reviewer prompt, the seven slop categories, the writing and code rules, and the two-pass protocol. It says what it does not do next to `edit-article` and the `writing-*` skills. It has no accuracy or revision-rate targets.
  - `lint.py` reads `phrases.yaml` and reports forbidden-phrase hits (case-insensitive), average paragraph length and comment ratio. It reports zero hits on revised F1 to F4. The test covers hit, no hit and the number/identifier comparison (acceptance criterion 2 of the spec).
  - The output validates against the schema. Every change has a listed category.
  - The subagent runs F1 to F10 against the built skill, including the idempotence check, and records pass or fail for each.
  - The script has no cross-platform findings.
  - The `docs/ANTI-SLOP-EXAMPLES.md` pairs are used as fixture seed. The licence of that text is recorded.

### 4. Copy to claude-mods
- [ ] After tasks 1 to 3 pass: copy each pack to `~/Developer/claude-mods/skills/<name>/` (`PACK.md` as `SKILL.md`, plus the side files the skill refers to). Run `scripts/install-skills.sh` in a dry way or read it to confirm the folders are picked up.
- **Acceptance:** each folder has `SKILL.md` with `name` and `description`, and every file path in the body exists. No UMAS wording (`grep -ri umas` is empty).

### 5. Docs in sync
- [ ] `claude-mods`: write a README for each skill with `ste-docs` (technical profile) and update the root `README.md`.
- [ ] This repo: add the built status to `packs/README.md` and to each pack README (a "Built" note, the open questions that the build answered), and update `docs/assessments/skills-for-claude-mods.md` verdicts.
- **Acceptance:** no README says a pack is unbuilt or untested when it is built; every path in a README exists.

### 6. Report
- [ ] Final summary: fixture pass or fail table per skill, what is verified by reading only, what the user must still decide (provenance and licence check, push to claude-mods).

## State log

- 2026-10-25: decisions recorded. Next: start tasks 1 to 3 as parallel subagents.
- 2026-10-25: task 1 (minimalism-ladder) built, tests OK, fixtures run with caveats (see task 1). Tasks 2 and 3 still running in the background.
- 2026-10-25: F3 re-review done under C4 = B (runs 3 to 5 meet criteria 4 and 5; one sample, model judge). anti-slop stays `[-]`: criterion 2 wording, F5 Python rewrite, D6 and SKILL-ASSESSMENT criterion-2 wording are open. F3 unit test still fails (`outputs/F3.revised.md` is run 2's text).
