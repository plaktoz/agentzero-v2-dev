# router-heuristic: skill assessment

> Date: 2026-10-25 · Updates the earlier verdict in `docs/assessments/skills-for-claude-mods.md` (row 8, "Needs an engine") for this pack only.

## 1. Verdict

**`skill`.** The earlier verdict said the pack needs a deterministic scorer and a caller. The test result: the rubric is seven small integer terms, so an agent can apply it by reading and a reviewer can re-add the reasons to check it. The caller is not needed for the skill to be useful, because the route is a recommendation that a person or the agent's own next step acts on. A script is optional (section 6).

## 2. Fit evidence

One session with only the files in this folder:

- Input from the user: the request text. Optional: codebase scan hints, an override.
- The agent reads the request, fills the seven signals with a short evidence phrase each, applies the weight table, maps the score to a band and route, and prints the decision record.
- Worked by hand against the 12 fixtures: F1, F2, F5, F6, F9, F10 reproduce the spec's expected routes from the request text alone. F3, F4, F7, F8 reproduce them only when a scan `files_estimate` is supplied, because the request does not say how many files change. The fixtures carry that scan value. With no scan, a request that names no file scores `unknown` (+2) and leans medium. The skill says so in its Limits.
- Not standalone in one respect: nothing in a bare session acts on the route. The route table says what each route means (direct worker, architect then worker, and so on) in generic terms; the user or a larger workflow decides what to do next. This cuts the value of the skill to "a checked, logged sizing call". It does not make the skill invalid.

## 3. Overlap

| Skill | What it does | What this pack adds or lacks |
|-------|--------------|------------------------------|
| `triage` | Moves issues through roles `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. Quote: "Move issues on the project issue tracker through a small state machine of triage roles." | Different question. Triage decides readiness and who acts. This pack decides how much process a change needs. Triage has no size score, no sensitive-domain rule, no override record. The pack needs no issue tracker. |
| `to-spec` | Turns the conversation into a spec. Quote: "This skill takes the current conversation context and codebase understanding and produces a spec". | It runs after the decision to plan. It has no step that asks whether a spec is needed. The pack answers that: `simple` skips it. |
| `to-tickets` | Breaks a plan into tracer-bullet tickets. Quote: "Break the work into **tracer bullet** tickets." Its only sizing rule is "Each slice is sized to fit in a single fresh context window". | It sizes slices of a plan, not the request that starts the plan. No overlap in input or output. |
| `wayfinder` | Plans a very large effort as a map of decision tickets. Quote: "If this surfaces no fog ... you don't need a map." | It has one size test: is there fog? The pack gives a graded score and routes, and its `large` and `greenfield` routes are the cases where a map might be chosen. The pack does not chart a map (stated under Not this skill). |
| `handoff`, `claude-handoff` | Write a summary so a fresh agent can continue. Quote: "Write a handoff document summarising the current conversation so a fresh agent can continue the work." | No overlap. The pack's re-route record could be an item in a handoff, but neither skill sizes work. |
| `grilling` | Questions the user one at a time until shared understanding. Quote: "Interview me relentlessly about every aspect of this until we reach a shared understanding." | The pack never asks questions. When `scope_ambiguous` is true, the record shows it, and the user may then choose to grill. |
| `implement` | Implements a spec or tickets. Quote: "Implement the work described by the user in the spec or tickets." | It starts after sizing. No overlap. |

No installed skill sizes a request before planning. The pack is not a duplicate.

## 4. What blocked it as a skill (and the state now)

| Blocker | State |
|---------|-------|
| `PACK.md` did not exist | Built |
| `schema/`, `fixtures/`, `config.yaml` did not exist | Built |
| UMAS wording and "Known consumers" in the spec | Left in the spec (sections 9, 10, 12). Not copied into `PACK.md` |
| Cross-pack dependency: the spec's routes name specialist-agents roles (Architect, PM) | `PACK.md` describes each route generically. The data-shape contract (route name) stays in the spec |
| Unverified claim: 75 percent agreement target on 30 labelled requests | Not copied. `PACK.md` Limits says accuracy has not been measured |
| The spec splits extraction (model) from arithmetic (code) | In a skill one agent does both. `PACK.md` keeps them as separate steps and adds a completion check that the reasons add up to the score. The determinism the spec wants (criterion 2, 3) is not guaranteed. See section 6 |
| Fixtures never run | Not run (below) |

## 5. Enhancements (priority order)

Done in this change:
1. `PACK.md` with front matter (`name`, `description`), steps with a completion criterion, signals table, rubric, bands, override, re-route, "Not this skill", limits, output contract.
2. `schema/signals.json`, `schema/decision.json` (the decision schema inlines the signals definition so it validates alone).
3. `fixtures/F1.yaml` to `F12.yaml` with hand-derived scores. Not run against a model.
4. `config.yaml` with weights, band thresholds, route names, default route.

Open:
5. Run F1 to F12 on a model and record the results in `fixtures/RESULTS.md`, with a judge who is not the author.
6. Build `scripts/score.py` and its unittest if the owner wants determinism (section 6).
7. Collect 30 labelled requests to test the 75 percent target. Out of reach until real requests exist.

### Deviations from the spec (the spec is not edited; the coordinator decides)

| Deviation | Reason |
|-----------|--------|
| Added reason `floor at 0 +N` when the non-sensitive sum is negative | Spec criterion 4 says reasons sum to the score. F1 and F5 give a negative sum that the `max(0, ...)` rule floors, so a sum would fail without it |
| `files_affected` fallback: count files the request names (1 is one, 2 to 5 is few), else unknown | The spec leaves it to the scan. A bare session has no scan |
| `config.yaml` values replace the `PACK.md` defaults when present | Spec criterion 3 (change `medium_at`, F3 changes) needs one place to change. `PACK.md` states the same numbers as defaults |
| Empty request returns `medium` with reason `default: no request text` | The spec has `default_when_unclear` in config but no rule for when it applies |
| An unsupported claim is set false and its evidence states the mismatch | Spec F12 and failure-mode table need a way to note it |
| `reroute_reason` field in the decision record | Spec 5.6 says a re-route is logged with a reason but gives no field |
| Fixtures F3, F4, F7, F8 carry a scan `files_estimate` | The spec's expected scores need a file count the request does not give |
| `greenfield` band is `n/a` | Matches the spec's band table; the schema allows it |

## 6. Decision needed from the owner

**Build a deterministic scorer (`scripts/score.py`)?** This is the question the earlier verdict turned on.

| Option | What it changes |
|--------|-----------------|
| A. No script (current) | Skill only. The agent does the arithmetic. Cheap. Two runs with the same signals could in rare cases add differently. The reasons-sum check catches most slips |
| B. Add a scorer, **not built** | See below. Gives the determinism the spec's criteria 2 and 3 ask for, and a unit-testable rubric. Consumers that have a code path call it; a bare session still works without it |

What the script would be (not built): `scripts/score.py`, Python standard library only, UTF-8, `pathlib`. Input: a signals JSON file and an optional `config.yaml` (read with the test-policy `yaml_subset.py` pattern, copied into this pack so it stays self-contained). Output: the decision JSON on standard output, with `reasons` that sum to the score. Rules: sensitive points once; `bug_with_location` applied to the other terms only; floor reason; greenfield sets route and band `n/a`; `override` replaces route. Unit tests: one per fixture F1 to F10 using fixed signals, plus a threshold test (change `medium_at` and F3 changes route) and an invalid-signals test. Extraction stays with the agent: no script can read a request.

**Recommendation: A for now.** The arithmetic is ten lines and checkable by eye. Build B when an orchestrator consumes the decision record, since that is the case where a wrong sum would act unseen.

Two smaller questions inherited from the spec (Open Questions 1 and 2): whether a pure data migration should route `large` (fixture F7 shows `medium`), and whether the router should also set a minimalism or test level. No change made.

## 7. Fixtures: not run

| ID | Expected route | Status |
|----|----------------|--------|
| F1 | simple, score 0 | not run |
| F2 | simple, score 0 | not run |
| F3 | medium, score 6 | not run |
| F4 | large, score 9 | not run |
| F5 | medium, score 3 | not run |
| F6 | medium, score 4 | not run |
| F7 | medium, score 6 | not run |
| F8 | medium, not greenfield, score 6 | not run |
| F9 | greenfield, score 5 | not run |
| F10 | large (override), score 0, `overridden` true | not run |
| F11 | identical decision on two runs | not run |
| F12 | simple, unsupported claim set false, score 0 | not run |

## 8. Verification

See the report to the coordinator. The checks and results: front matter, forbidden-word grep, paths named in `PACK.md`, JSON schemas, fixture YAML by reading, example record checked against its own rules by reading.
