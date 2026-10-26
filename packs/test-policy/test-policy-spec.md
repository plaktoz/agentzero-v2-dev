# test-policy

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](../README.md)
> **Independence:** no dependency on UMAS or any test framework. A policy, a classifier prompt, and a deterministic pre-filter.
> `pack_version: 0.1.0`

---

## 1. Purpose

Decide which changes need tests. Two modes: **selective** (tests only where logic is risky) and **strict** (test-first for every feature). The pack classifies a change, says what to test, and says whether a missing test blocks.

## 2. Scope and Non-Goals

**In scope**
- The two modes and the trivial-change exemption
- A definition of "risky logic" and a classifier
- A deterministic pre-filter for obviously trivial changes
- The output: what must be tested and why
- How the coverage target relates to the mode

**Non-goals**
- Running tests or measuring coverage. See [test-adapters](../../libs/test-adapters/README.md)
- Writing the tests
- Choosing frameworks
- Mutation testing or fuzzing

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Policy (5.1), risky-logic definition (5.2), classifier prompt (5.4) |
| `risky-patterns.yaml` | Deterministic patterns per language |
| `schema/assessment.json` | Output |
| `fixtures/*.yaml` | F1 to F10 |
| `config.yaml` | Mode and target |

## 4. Contract

### 4.1 Input

```text
diff:            unified diff
mode:            selective | strict
existing_tests:  paths or summary of tests touching changed files
coverage:        { line_percent: number?, changed_lines_percent: number? }   optional
```

### 4.2 Output

```json
{ "pack_version": "0.1.0",
  "mode": "selective",
  "change_class": "trivial | normal",
  "units": [
    { "location": "pricing.py:12-40", "kind": "money|security|parser|branching|loop|state|none",
      "risky": true, "tests_required": true,
      "cases": ["zero quantity", "negative discount", "rounding at .005"],
      "present": false } ],
  "gate": "ok | missing_tests",
  "reasons": ["pricing.py:12-40 is money logic with no test"] }
```

## 5. The Rules and Prompt

### 5.1 Policy

| Mode | Tests required for | Process |
|------|--------------------|---------|
| `selective` (default) | Risky logic only | Tests may follow the code; no ordering rule |
| `strict` | Every feature | Red, green, refactor: a failing test exists before the code |

Trivial changes need no tests in either mode: rename, formatting, comments, documentation, configuration-only. A change that is partly trivial and partly not is split by unit.

### 5.2 Risky logic

A unit of code is risky when it contains any of:

| Kind | Examples |
|------|----------|
| branching | conditionals with more than a trivial guard, state machines |
| loop | iteration with accumulating or terminating conditions |
| parser | any code that interprets structured or untrusted text |
| money | prices, tax, rounding, currency |
| security | authentication, authorisation, input sanitation, crypto, secrets |
| state | concurrency, retries, caching, anything with ordering |

Plain data movement, getters, and glue calls are not risky.

### 5.3 Deterministic pre-filter

Run before the model. Classify the whole diff `trivial` with no model call when every changed file matches a trivial pattern (docs, lockfile, config extensions) or every changed hunk is whitespace/comment only. Language-specific risky patterns (for example regexes for `if`, `for`, `parse`, `decimal`, `auth`) flag candidates for the model to confirm. The pre-filter may only say `trivial` or `needs_model`; it never decides risk.

### 5.4 Classifier prompt

```text
Assess a change for testing. For each changed unit of code, decide whether
it contains risky logic (branching, loops, parsers, money, security, state).
If it does, say which kind and list the specific cases that a test must
cover, drawn from the code (boundaries, empty input, failure paths).
If existing tests already cover a case, mark it present.

Do not ask for tests of trivial changes or of plain data movement.
Do not write the tests.
```

### 5.5 Gate

| Mode | Gate result `missing_tests` when |
|------|---------------------------------|
| selective | any unit has `tests_required` and `present: false` |
| strict | any new feature unit lacks a test that was added before or with the code, or any risky unit is untested |

### 5.6 Coverage target

The target is a number separate from the mode. The source gives two conflicting defaults, 80 percent and 95 percent. This pack:

- Does not set a default target.
- Applies a target to **changed lines** by default (more meaningful than project-wide).
- Treats coverage as a secondary signal. A high number with no test for the risky unit still gates as `missing_tests`.

## 6. Configuration

```yaml
mode: selective                # selective | strict
coverage_target: null          # number 0-100; null disables
coverage_scope: changed_lines  # changed_lines | project
exempt_globs: ["docs/**", "*.md", "*.lock", "config/**"]
risky_patterns_file: risky-patterns.yaml
```

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| Classifier marks everything risky | Output must list concrete cases; units without cases cannot be `tests_required`. Fixture F9 |
| Misses a risky unit | Deterministic patterns add candidates; reviewer can add. Fixture F5 |
| Tests present but trivially passing | Out of scope; coverage on risky lines catches some. Mutation testing is a possible later addition |
| Coverage-gaming | Gate is on risky units, not only on the percentage |
| Strict mode on exploratory work | Mode is per project and can be changed; no per-task mix is defined |
| Source default conflict (80 versus 95) | No default; set explicitly |

## 8. Fixtures and Acceptance Criteria

### 8.1 Fixtures

| ID | Change | Selective expectation |
|----|--------|-----------------------|
| F1 | Rename a variable across files | `trivial`, gate ok, no model call |
| F2 | README edit | `trivial` |
| F3 | Config value change only | `trivial` |
| F4 | New `calculate_total()` with discount and rounding, no test | `money`, tests required with cases, gate `missing_tests` |
| F5 | Function that parses a date string, change adds a branch | `parser`, flagged, cases include invalid input |
| F6 | Same as F4 with a test covering the listed cases | `present: true`, gate ok |
| F7 | A getter and a setter added | not risky, gate ok |
| F8 | Strict mode, new feature with no test | `missing_tests` |
| F9 | Large diff of glue code | No unit marked `tests_required` without cases |
| F10 | Mixed diff: docs plus an auth check | Docs trivial; auth unit `security`, required |

### 8.2 Acceptance criteria

1. F1 to F10 give the expected `change_class`, kinds, and gate.
2. For F1 to F3 the pre-filter returns `trivial` without a model call.
3. Every unit with `tests_required: true` lists at least one case.
4. Under strict mode F7 additionally requires tests (every feature), while under selective it does not.
5. A coverage figure of 100 percent does not turn a `missing_tests` gate into `ok` when a risky unit has no test.
6. Re-running on the same diff and tests gives the same gate.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| `testing.tdd_required: false/true` | `mode: selective/strict` |
| `testing.coverage_target` | `coverage_target`; the default is now unset (source: 80 and 95/80 in different files) |
| "Tests required only for risky logic: branches, loops, parsers, money, security" | 5.2 |
| Verification agents decide "risky logic" | The classifier prompt, run by a review or verification agent |
| Test results and coverage | From [test-adapters](../../libs/test-adapters/README.md); passed as `coverage` input |
| Standards review checks coverage of risky logic | [two-axis-review](../two-axis-review/two-axis-review-spec.md) consumes `units` |
| Merge queue | `gate: missing_tests` can hold a PR in `ready_to_merge` |

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.4 (Test Coverage Policy), `TECHNICAL-DESIGN-SPEC-PART3.md` (verification config) and the PRD TDD section.

| Deviation | Why |
|-----------|-----|
| No default coverage target | The sources disagree (80 versus 95 and 80); picking one hides the conflict |
| Target applies to changed lines by default | Project-wide percent is easily gamed and slow to move |
| Pre-filter for trivial changes | Source says trivial changes are exempt but gives no way to tell cheaply |
| Cases required per risky unit | A "risky" label without cases cannot be acted on |
| Gate rather than a pass/fail test | The pack cannot run tests; it can say whether needed ones are missing |
| "State" added as a risky kind | Concurrency, retries, and caching are not in the source's list but cause the same class of bug |

## 11. Open Questions

1. Is "state" an acceptable addition to the source's list of risky kinds, or should the list stay as the source has it?
2. Should strict mode allow an exception list (generated code, migrations)?
3. Who writes the missing tests: the Developer role in the same task, or a separate pass? The pack only reports.

---

## 12. Reference Implementation (Source Code)

> Non-normative. Example code illustrating one way to implement this spec. May use consumer-specific names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [packs/README.md](../README.md).

### 12.1 Test coverage policy (YAML)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §6.2.4

```yaml
# Configurable per project in umas.config.yaml
# See UMAS-TECH-DESIGN-SPEC.md §3.4 Test Coverage Policy
test_coverage:
  mode: selective          # selective (default) | strict
  
  selective_mode:
    # Tests required for: branches, loops, parsers, money, security
    # Tests NOT required for: renaming, formatting, config-only changes
    risky_logic_patterns:
      - conditional_logic
      - loops_and_iteration
      - parsers_and_transforms
      - money_calculations
      - security_checks
    
  strict_mode:
    # Full TDD: red-green-refactor for every feature
    tdd_required: true
    
  coverage_target: 80      # percentage, configurable per project
```
