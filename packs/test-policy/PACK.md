---
name: test-policy
description: Decides which parts of a change need tests and whether missing tests block it, in selective mode (risky logic only) or strict mode (every feature). Use when you must say what a change needs in tests, or whether the existing tests are enough.
---

# test-policy

Classify a change, say what must be tested and why, and say whether a missing test blocks. Two modes: **selective** (tests only where logic is risky) and **strict** (a test for every feature, which exists before the change or is added with it).

## Not this skill

This skill decides *whether and what* to test. It reports whether the needed tests exist.

- The test-first loop (write a failing test, make it pass, refactor) is a different job. This skill does not run it, schedule it or check the order in which code and tests were written.
- It does not write tests, run tests, measure coverage, choose a test framework or the seams a test attaches to, or do mutation testing or fuzzing.
- It does not review the change for style, design or fit to a spec. It looks at one question: does the code that carries risk have tests?

## Files

Paths in this file are relative to the folder that holds it. In the commands below, `<pack>` is that folder's full path.

| File | Purpose |
|------|---------|
| `PACK.md` | This file: policy, risky-logic definition, pre-filter rule, classifier prompt, gate rules, output record |
| `risky-patterns.yaml` | Deterministic patterns per language (candidate flags, comment syntax) |
| `schema/input.json` | JSON Schema for the input |
| `schema/assessment.json` | JSON Schema for the output record |
| `config.yaml` | Mode, coverage target and scope, exempt globs |
| `scripts/prefilter.py` | The deterministic pre-filter. Python, standard library only. Optional: the rules below still apply without it |
| `scripts/yaml_subset.py` | Stdlib reader for the YAML files in this pack. Used by the pre-filter and the tests |
| `scripts/test_prefilter.py`, `scripts/test_schema.py` | Unit tests for the pre-filter and the schemas. For maintainers |
| `fixtures/*.yaml`, `fixtures/RESULTS.md` | Checks F1 to F10 with the expected properties, and the record of an earlier model run. For maintainers |

## Input

```text
diff:            unified diff of the change
mode:            selective | strict          (default: selective)
existing_tests:  paths or a summary of tests that touch the changed files
coverage:        { line_percent: number?, changed_lines_percent: number? }   optional
```

## Procedure

Follow the steps in order. Each ends on a condition you can check.

1. **Get the inputs.**
   - `diff`: use the one the user gave. Otherwise take the diff of the change the user names (for example a branch against its base). If you cannot tell which change to assess, ask.
   - `mode`: use the one the user gave. Otherwise use `mode` in `config.yaml`; if that file is absent, `selective`.
   - `existing_tests`: use the list the user gave. Otherwise find the tests yourself: search the test files and directories of the project for tests that import or name the changed modules, and read them. An empty list is a valid answer.
   - `coverage`: use it only if the user supplies it. Do not run anything to produce it.
   - Done when the diff is non-empty, the mode is set, and the search for existing tests has been made.
2. **Run the pre-filter** if `scripts/prefilter.py` is in the same folder as this file (see Pre-filter). On `trivial`, emit the trivial record and stop. On `needs_model`, keep the candidate flags and go on. If the script is not there, apply the trivial rule by reading the diff, and answer `needs_model` when unsure.
3. **Split the change into units.** Leave out trivial parts and test files. Done when every non-trivial changed hunk belongs to exactly one unit, each named by file and line range.
4. **Classify each unit** with the classifier prompt below: risky or not, its kind, `tests_required` for the mode, and the concrete cases a test must cover, read from the code. Done when every unit has a kind and every `tests_required` unit lists at least one case.
5. **Match the existing tests.** Read the tests from step 1 and the tests added in the diff. Set `present` true only if every listed case is covered. Done when each `tests_required` unit has a `present` value you can justify from a named test.
6. **Set the gate and the reasons** by the Gate rules.
7. **Emit the output record.** If `schema/assessment.json` is present and you can validate against it, do so. Otherwise check by hand: every `tests_required` unit has a case, the gate follows the single check in the Gate section, and `reasons` is empty exactly when the gate is `ok`. Done when the record passes that check.

## Policy

| Mode | Tests required for | Process |
|------|--------------------|---------|
| `selective` (default) | Risky logic only | Tests may follow the code; no ordering rule |
| `strict` | Every feature | A test exists before the change, or is added in the same change |

Trivial changes need no tests in either mode: rename, formatting, comments, documentation, configuration-only. A change that is partly trivial and partly not is split by unit.

A **unit** is a function, method, class or other self-contained block of code that the change adds or whose body it changes. Name it by file and line range in the new file, for example `pricing.py:12-40`. A **feature unit** is a unit that adds new behaviour.

## Risky logic

A unit is risky when it contains any of these:

| Kind | Examples |
|------|----------|
| branching | conditionals with more than a trivial guard, state machines |
| loop | iteration with accumulating or terminating conditions |
| parser | any code that interprets structured or untrusted text |
| money | prices, tax, rounding, currency |
| security | authentication, authorisation, input sanitation, crypto, secrets |
| state | concurrency, retries, caching, anything with ordering |

Plain data movement, getters, and glue calls are not risky.

A unit may fit more than one kind. Record the first that applies in this order: security, money, parser, state, loop, branching. A unit that is not risky has kind `none`.

## Pre-filter

Run it before the classifier. It may answer only `trivial` or `needs_model`, and it never decides risk.

- Answer `trivial`, with no classifier call, when every changed file matches a trivial pattern (a documentation, lockfile, configuration or data extension, or a path under the exempt globs `docs/**`, `*.md`, `*.lock`, `config/**`), or every changed hunk changes only whitespace or whole-line comments. The globs and extensions are the defaults in `config.yaml`; if that file is not present, use these. A change that consistently renames one identifier to another, with no other edit, also counts as trivial.
- Answer `needs_model` in every other case, and whenever the diff cannot be parsed.
- The patterns in `risky-patterns.yaml` flag candidate lines (for example `if`, `for`, `parse`, `decimal`, `auth`). A flag is a hint for the classifier to confirm or reject. It is not a verdict.

It prints one word. `--candidates` also lists the flagged lines on standard error.

```text
python3 -I <pack>/scripts/prefilter.py change.diff                    macOS, Linux
python -I <pack>/scripts/prefilter.py change.diff                      Windows (where the launcher is named python)
python3 -I <pack>/scripts/prefilter.py --candidates - < change.diff   diff on standard input
```

Use whichever interpreter command exists on your machine. The script needs Python 3 and no other package. If no Python is available, apply the trivial rule above by reading the diff, and answer `needs_model` when you are unsure.

When the answer is `trivial`, skip the classifier and emit this record, with `mode` set to the mode in use:

```json
{ "pack_version": "0.1.0", "mode": "selective", "change_class": "trivial", "units": [], "gate": "ok", "reasons": [] }
```

## Classifier prompt

Steps 3 to 6 of the procedure apply this text. Follow it yourself, or give it to a separate reviewing agent if your setup has one. Fill the placeholders from the input.

```text
Assess a change for testing. For each changed unit of code, decide whether
it contains risky logic (branching, loops, parsers, money, security, state).
If it does, say which kind and list the specific cases that a test must
cover, drawn from the code (boundaries, empty input, failure paths).
If existing tests already cover a case, mark it present.

Do not ask for tests of trivial changes or of plain data movement.
Do not write the tests.

The mode is {{mode}}. In selective mode, tests_required is true exactly for
risky units. In strict mode, tests_required is also true for every unit that
adds a feature, risky or not.
Every unit with tests_required true lists at least one concrete case taken
from the code. A unit with no concrete case to test is not risky.
Set present to true only when existing tests, or tests added in this diff,
cover every listed case. In strict mode a test counts only if it existed
before the change or is added in the same change.
Leave trivial parts (formatting, comments, documentation, configuration,
renames) out of units, and do not list test files as units.
Set gate to missing_tests when any unit has tests_required true and
present false, otherwise ok. A coverage figure never changes the gate.
Answer with one JSON object in the output record format and nothing else.

diff:
{{diff}}

existing_tests:
{{existing_tests}}

coverage (optional):
{{coverage}}

candidate flags from the pre-filter (optional, confirm or reject each):
{{candidates}}
```

## Gate

| Mode | Gate result `missing_tests` when |
|------|---------------------------------|
| selective | any unit has `tests_required` and `present: false` |
| strict | any feature unit has no test that existed before or was added with the code, or any risky unit is untested |

Both rows reduce to one check on the record: `missing_tests` when some unit has `tests_required: true` and `present: false`, otherwise `ok`. Every `reasons` entry names a unit and what is missing.

A coverage figure is a secondary signal. A high number with no test for the risky unit still gates as `missing_tests`; full coverage never turns `missing_tests` into `ok`.

## Coverage target

The target is a number kept separate from the mode.

- There is no default target. `coverage_target: null` disables the check.
- A target applies to **changed lines** by default (`coverage_scope: changed_lines`). `project` is the other option.
- Coverage is reported by a test runner and passed in as `coverage`. This skill compares it with the target only when a target is set, and the comparison never overrides the unit-based gate.

## Output record

```json
{
  "pack_version": "0.1.0",
  "mode": "selective",
  "change_class": "normal",
  "units": [
    { "location": "pricing.py:12-40", "kind": "money",
      "risky": true, "tests_required": true,
      "cases": ["zero quantity", "negative discount", "rounding at .005"],
      "present": false }
  ],
  "gate": "missing_tests",
  "reasons": ["pricing.py:12-40 is money logic with no test"]
}
```

| Field | Meaning |
|-------|---------|
| `pack_version` | Version of this pack that produced the record (optional in the schema, always set by this skill) |
| `mode` | `selective` or `strict`, as used |
| `change_class` | `trivial` when the whole change is trivial; otherwise `normal` |
| `units[].location` | File and line range in the new file |
| `units[].kind` | `money`, `security`, `parser`, `branching`, `loop`, `state`, or `none` |
| `units[].risky` | Whether the unit is risky logic |
| `units[].tests_required` | Selective: equals `risky`. Strict: `risky`, or the unit adds a feature |
| `units[].cases` | Concrete cases a test must cover. At least one when `tests_required` is true |
| `units[].present` | True only when tests cover every listed case |
| `gate` | `ok` or `missing_tests` |
| `reasons` | One short sentence per blocking unit; empty when the gate is `ok` |

`change_class: trivial` has no units and gate `ok`. `schema/assessment.json` encodes these rules, so a consumer can validate a response without reading this file.

## Limits

- The skill cannot tell whether a test is meaningful. A test that passes without checking anything counts as present.
- The classifier is a model and can miss a risky unit or flag a safe one. The pre-filter flags and the `cases` requirement narrow this; they do not remove it. For repeatable results use the most deterministic settings the harness offers. The pre-filter itself is deterministic.
- The pre-filter treats every file under `exempt_globs` as trivial, including code placed there. Keep the globs to paths that hold no logic.
- Pattern flags are regular expressions. They miss renamed or indirect logic and flag unrelated words.
- The skill sees the finished diff, not the order in which code and tests were written. In strict mode it checks that a test exists before the change or is added with it; it cannot check that the test was written first.
- Strict mode applies to the whole project. No per-task mix is defined.
- The coverage target has no default because no single value is justified.
