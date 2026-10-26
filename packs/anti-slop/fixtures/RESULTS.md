# Fixture results

Run date: 2026-10-25, second run (after the owner's decisions of the same day). Pack version 0.1.0. Seven of ten fixtures pass their expected property and three fail (F1, F3, F8). Four of six acceptance criteria fail. Details below.

## How the runs were done

- **Reviewer.** For each fixture, a fresh sub-agent was given one file: `PACK.md` followed by the review kind, the language (`none` for non-code) and the fixture input. It was not shown the `expect` lines, this file, or any earlier output. Each reviewer made exactly one tool call (a read of its brief), and its final reply was one JSON record. That is saved as `outputs/F<n>.json`; the record's `revised` field is saved as `outputs/F<n>.revised.md`; the input is `outputs/F<n>.input.txt`, extracted from the fixture YAML with `lint.py extract-input`.
- **Judge is the author.** The judge is the pack's author, carried over from the first run. The agent that ran this re-run judged the outputs against the `expect` lines, but it is not a separate person and is not independent of the pack. Verdicts follow the `expect` list in `fixtures/F<n>.yaml` literally. Treat them as one strict reading, to be confirmed by a person.
- **Idempotence.** For each fixture, a second fresh sub-agent reviewed that fixture's first-run revised text and wrote `outputs/F<n>.pass2.json`.
- **Scripts.** `lint.py validate` checked all 20 records against `schema/review-output.json`. `lint.py check` and `lint.py compare` ran on the revised texts. `python3 -I -m unittest discover -s scripts` ran 29 tests.
- **Reviewer model.** One reviewer model, one run per fixture. Model output varies between runs, so one run is evidence, not a measurement. F1 passed in the first run and fails in this one. Rule 3 changed between the runs too, so one run per fixture cannot separate reviewer variance from the effect of the rule change.
- **Old outputs.** The first-run files for all ten fixtures are in `outputs/superseded/before-2026-10-25-decisions/`. Earlier F8 runs are in `outputs/superseded/` and `outputs/superseded/run3/`.

## Verdicts

| ID | Verdict | Evidence |
|----|---------|----------|
| F1 | Fail | Revised: "Our framework is a set of coordination ideas. The system coordinates 20 to 30 agents, each in its own git worktree." The number and the worktree fact are kept and no listed phrase remains. The expectation is one concrete sentence; the output has two, and the first ("a set of coordination ideas") names nothing. The second pass flagged it as vague, and flagged "framework" and "system" as possible synonym overuse |
| F2 | Pass | Revised: "This framework lets teams integrate AI capabilities. It connects to Anthropic, OpenAI and Google models, and setup takes about 15 minutes." Providers and time are kept, "serves as" is gone, nothing is invented. Seven changes, one flag ("AI capabilities" names none) |
| F3 | Fail | The metrics (53%, 26%, 41%, 20-30+) are kept and no number is new. "fundamental" and "cohesive platform" are removed, but the first sentence still reads "designed to address the challenges of AI-assisted software development at scale". "at scale" remains, and the reviewer flagged it instead of removing it, so rule 3 as now written was not applied. The phrase lint reports one hit, "at scale". The second pass changed the text again (see criterion 5) and "at scale" is still there |
| F4 | Pass | Welcome text and "Let's dive in." removed. The heading and the three commands are kept as written. No command invented. The second pass flagged "a passing summary line" for the author, with no change |
| F5 | Pass | Revised is the `Agent` class only. Both factory classes, the `abc` import, the docstrings and the comment are gone. No abstract base class, factory class or single-implementation interface remains, and `Agent` is kept. The reviewer flagged that removing two public names needs a check of callers |
| F6 | Pass | `try` and `except` removed, listed as `swallowed_error` with `behaviour_change: true`. The `if result is None: return []` is kept and listed in `flags` for the author. Second pass: no change, same flag |
| F7 | Pass | Both claims are in `flags`, each with a location and an issue. No number in the revised text that is absent from the input. The reviewer also dropped "greatly" and "much" and listed both as changes, so the claims are marked, not filled with a figure |
| F8 | Fail | The reviewer changed nothing. The revised text still uses "agent", "worker", "assistant" and "bot". It flagged that the author must pick one term. Numbers, names and identifiers equal the input's, and no other fact changed. The first expectation, one term throughout, is not met |
| F9 | Pass | The opinion is unchanged and listed in `kept`. `changes: []` |
| F10 | Pass | `changes: []`. The revised text equals the input, except for the trailing newline that the extracted input file has and the revised text does not |

Passing: F2, F4, F5, F6, F7, F9, F10. Failing: F1, F3, F8.

## Acceptance criteria (spec section 8.2)

| # | Criterion | Result |
|---|-----------|--------|
| 1 | F1 to F10 satisfy their expected property | Fail: 7 of 10. F1, F3, F8 fail |
| 2 | Numbers, names and identifiers equal the input's for F1 to F4 and F8 | Fail on F1: `compare` reports the name "AI" dropped (it was in the deleted opening sentence, "AI landscape"). F2, F3, F4, F8 pass. No number was dropped or invented in any fixture. `test_criterion2_numbers_names_identifiers_match` fails for F1 |
| 3 | F10 output equals input | Pass |
| 4 | Phrase lint reports zero hits on revised F1 to F4 | Fail on F3: one hit, "at scale". F1, F2, F4 have zero. `test_revised_f1_to_f4_have_zero_phrase_hits` fails |
| 5 | A second reviewer pass gives no further changes | Fail: 9 of 10 have `changes: []` and the same text. F3's second pass made one change ("designed to address the challenges of" to "for") |
| 6 | Every change has a listed category | Pass: all 20 records validate |

The F1 failure on criterion 2 is a strict reading. The dropped item is a word from a deleted slop sentence. A person might accept it. The script cannot tell.

## Re-run after owner decisions (2026-10-25)

The owner made three changes: rule 3 of the writing rules now says to remove a vague phrase, without flagging it, when the sentence keeps every fact it had; F5's expectation no longer demands "a single function"; F6 now expects the `try`/`except` removed and the `None` check kept and flagged. `PACK.md` and the fixture YAML were not edited in this run. All ten fixtures were re-run because rule 3 changed.

| ID | First run | This run | What changed |
|----|-----------|----------|--------------|
| F1 | Pass | Fail | This run's revised text keeps the sentence "Our framework is a set of coordination ideas". The first run's text did not. The cause is not established: rule 3 changed between the runs, and one run per fixture cannot separate reviewer variance from the rule change |
| F2 | Pass | Pass | No change in outcome |
| F3 | Fail | Fail | Same failure as before: "at scale" remains and is flagged, not removed. Rule 3 did not change the outcome. This run's second pass also changed the text, which the first run's second pass did not |
| F4 | Pass | Pass | No change in outcome |
| F5 | Fail | Pass | The revised text is the same as in the first run. The change list has one more `premature_abstraction` entry this time (three changes, not two). The verdict changed because the expectation changed, not because the output did |
| F6 | Fail | Pass | Same as F5: the output matches the first run (try/except removed, `None` check kept and flagged). The verdict changed because the expectation changed |
| F7 | Pass | Pass | No change in outcome |
| F8 | Fail | Fail | No change in outcome. The input is unchanged |
| F9 | Pass | Pass | No change in outcome |
| F10 | Pass | Pass | No change in outcome |

Net: passing went from 6 to 7. F5 and F6 gained a pass (+2) and F1 lost one (-1). Both gains come from the owner changing the expectation, not from a different reviewer output. The one fixture that tests the rule 3 change directly (F3) still fails. Criterion 5 went from pass to fail because of F3. Criteria 1, 2 and 4 fail as before. All ten fixture inputs are byte-identical to the first run's inputs.

F3 detail: this run's first-pass text for F3 differs from the first run's first-pass text only in the first sentence. The first run's first-pass text already read "for AI-assisted software development at scale". This run's second pass produced exactly that text from this run's first-pass text. So the reviewer reached the first run's result in two steps, and still did not remove "at scale".

Why the three fixtures fail:

- **F1 (extra vague sentence).** The reviewer kept a generic sentence and flagged it. Rule 3 says to remove a phrase when the sentence keeps its facts, and to flag a claim when the content holds no fact. "a set of coordination ideas" is the second case. The fixture expects it gone.
- **F3 ("at scale").** The reviewer treated "at scale" as a claim needing a fact (flag it) and not as a removable phrase (remove it). The sentence keeps its facts without the phrase, so rule 3 as now written says to remove it. The reviewer did not. Whether this is a reviewer error or an ambiguity in rule 3 is for the owner to decide.
- **F8 (terms kept).** As in the first run. The reviewer will not pick one term when the last sentence of the input says the four terms are one process, because replacing them would make that sentence read "the agent, the agent, the agent and the agent are one process". The pack has no rule for this input.

## F8 input history

The F8 input was rewritten five times in the first run. The spec describes one thing named by four terms. Each version either gave one term a separate role or was ambiguous, and it was changed after seeing output. This is a weakness in the result: later versions were shaped by earlier outputs. This run used the final input unchanged.

| Version | Input shape | Reviewer result | Kept? |
|---------|-------------|-----------------|-------|
| A | Four actors in a scheduler pipeline | No change, flagged | Output deleted when A was replaced. Described from memory of the run |
| B | Written, replaced before any run | none | none |
| C | "The review agent... The agent... The worker... the assistant... The bot..." | Changed "worker" to "agent", flagged the others. The second pass then changed two more things: not idempotent | `outputs/superseded/` |
| D | Adds "The assistant and the bot are the same process" and uses "the worker it runs on" | Merged assistant and bot, kept "worker" as a separate host. Second pass: no change | `outputs/superseded/run3/` |
| E (final) | States that agent, worker, assistant and bot are one process | No change, flagged, in both runs. Second pass: no change | `outputs/` (this run), `outputs/superseded/before-2026-10-25-decisions/` (first run) |

## Things this run did not verify

- The reviewers could use tools. Each made one tool call, which shows it read only its brief, but the check is from the call count, not from a sandbox.
- The reviewers did not run any script. Validation, lint, compare and idempotence were run afterwards.
- The reviewers were told the review kind (`prose`, `prd`, `docs` or `code`) and, for code, the language. A real consumer must pass the same.
- Both code fixtures use the `.md` revised copy, so `check --kind code` ran on a `.md` path. Comment ratio was 0.0 for both revised files.
- The F5 and F6 changes are not run as code. The `behaviour_change: true` tag on F6 is a claim that a person or a test must confirm, as `PACK.md` says.
- `lint.py check` on the F8 revised text reports `ok: false` because the average paragraph is 5 sentences against a limit of 4. The input has the same length, so this is not a reviewer change.
- Everything ran on macOS only.

## F3 re-review (2026-10-25)

Owner decision C4 = B: three fresh reviewer runs for F3, each with a second pass, and a fresh judge. Pass if at least two of three meet criteria 4 and 5.

**Result: pass.** Runs 3, 4 and 5 all meet criteria 4 and 5.

| Run | Files in `outputs/runs/` | Criterion 4: `lint.py check --kind prd` | Criterion 5: pass 2 `changes` |
|-----|--------------------------|------------------------------------------|-------------------------------|
| 3 | `F3.run3.json`, `F3.run3.revised.md`, `F3.run3.pass2.json` | `phrase_hits: []` | `[]` |
| 4 | `F3.run4.json`, `F3.run4.revised.md`, `F3.run4.pass2.json` | `phrase_hits: []` (same text as run 3) | `[]` |
| 5 | `F3.run5.json`, `F3.run5.revised.md`, `F3.run5.pass2.json` | `phrase_hits: []` (same text as run 3) | `[]` |

Caveats:

- **One sample, not three measurements.** The three revised texts are byte-identical, so the judge judged one text three times.
- **The judge was a model, not a person.**
- **`outputs/F3.revised.md` is not replaced.** It still holds run 2's text, so `test_revised_f1_to_f4_have_zero_phrase_hits` still fails on "at scale". This entry does not change the test or that file.

Run 2 is kept as `outputs/runs/F3.run2.*`. It failed criterion 5 because its second pass changed the text. Its revised text also keeps "at scale", as the Verdicts table above records.

The Verdicts, Acceptance criteria and re-run tables above describe the earlier runs and are not changed.

## Re-running

```text
python3 -I scripts/lint.py extract-input fixtures/F1.yaml --out fixtures/outputs/F1.input.txt
python3 -I scripts/lint.py validate fixtures/outputs/F1.json
python3 -I scripts/lint.py check fixtures/outputs/F1.revised.md --kind prose
python3 -I scripts/lint.py compare fixtures/outputs/F1.input.txt fixtures/outputs/F1.revised.md
python3 -I -m unittest discover -s scripts -v
```

The last command includes two tests that read `outputs/*.revised.md`. Both currently fail: F1 for criterion 2 and F3 for criterion 4. They describe real results. There is no unit test for criterion 5; it was checked by comparing each `F<n>.pass2.json` with the first-run revised text. On Windows use `py -3` or `python` in place of `python3`. Delete `scripts/__pycache__` afterwards.
