# test-policy fixture results

Model-behaviour check of fixtures F1 to F10 against `PACK.md`, run on 2026-10-25.

## Method

- Judge: a fresh sub-agent per fixture, separate from the author of the pack. Each judge saw only `PACK.md` and one input record (`mode`, `existing_tests`, `coverage`, the pre-filter verdict, the candidate flags and the diff). It was not shown the fixture expectations, the schema or the scripts.
- The pre-filter was run by `scripts/prefilter.py` on the fixture diff, and its output was passed to the judge.
- Each judge returned one JSON record. Every record was validated against `schema/assessment.json` with `jsonschema` (draft 2020-12), then compared with the fixture's `expect` list by reading.
- F1 to F3 are `trivial` by the pre-filter, so the classifier is not called for them. The judge was asked to emit the trivial record for the mode in the input.

## Results

| Fixture | Pre-filter | Gate | Units (kind, required, present) | Schema | Result |
|---------|-----------|------|---------------------------------|--------|--------|
| F1 rename across two files | trivial | ok | none | valid | pass |
| F2 README edit | trivial | ok | none | valid | pass |
| F3 config value change | trivial | ok | none | valid | pass |
| F4 `calculate_total`, no test | needs_model | missing_tests | `pricing.py:4-12` money, required, present false, 8 cases | valid | pass |
| F4 variant: coverage 100 | needs_model | missing_tests | `pricing.py:4-12` money, required, present false, 7 cases | valid | pass |
| F5 date parser slash branch | needs_model | missing_tests | `dates.py:4-9` parser, required, present false, 7 cases | valid | pass |
| F6 code added with tests | needs_model | ok | `pricing.py:4-12` money, required, present true, 6 cases | valid | pass |
| F7 getter and setter (selective) | needs_model | ok | none | valid | pass |
| F7 variant: strict | needs_model | missing_tests | `account.py:5-6` and `account.py:8-9`, kind none, required, present false, 1 case each | valid | pass |
| F8 strict, new feature, no test | needs_model | missing_tests | `greeting.py:1-2` kind none, required, present false, 2 cases | valid | pass |
| F9 glue code | needs_model | ok | 15 units, all kind none, not required | valid | pass |
| F10 docs plus authorisation check | needs_model | missing_tests | `documents.py:5-10` security, required, present false, 4 cases | valid | pass |

Checks that matter most:

- Every unit with `tests_required: true` lists at least one case, in every record (also enforced by the schema).
- F4 with 100 percent line and changed-line coverage still returns `missing_tests` with `present: false`.
- F7 is `ok` in selective mode and `missing_tests` in strict mode.
- F5 lists the invalid-input cases and the new slash branch, and the ISO-only existing test does not mark the unit present.
- F6 returns `present: true` and `ok`, and no unit points at the test file.
- F10 lists the anonymous, admin, owner and non-owner cases, and the docs change appears in no unit.

## Repeatability

F4 and F10 were run a second time with a new judge. Both gave the same gate (`missing_tests`), the same unit kind and the same `present` value. The wording and the number of cases differed (F4: 7 cases in the repeat; F10: 4 cases both times). The pre-filter output is identical on every run.

## What this does not show

- Each result is a single sample (two for F4 and F10). The classifier is a model, so another run can differ in wording and in case lists. The gate and kind were stable in the runs made.
- The judges are the same model family as the author, so shared blind spots are possible.
- The fixtures check the properties in `expect`, not exact text. The checks were made by reading the records against `expect`; only the schema check is automated.
- F9 shows the glue case passing here. A larger or less regular glue diff may behave differently.
