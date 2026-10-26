---
name: router-heuristic
description: Sizes a request before work starts (simple, medium, large or greenfield) by extracting seven signals with evidence, scoring them with a fixed rubric, and returning the route with its reasons. Use when deciding how much planning and review a change needs, when a request's size is unclear, or when a worker finds a task larger or smaller than its route assumed.
---

# router-heuristic

Choose how much process a request needs. A one-line fix goes straight to a direct worker. A new system gets an architect and specialists. Read the request, extract the signals, score them, return the route, and record the reason. The route is a suggestion. A person can override it.

This skill returns a route and its reasons. It does not carry out the work, estimate hours or cost, split the work into tasks, or choose a tool.

## Inputs

| Input | Required | Meaning |
|-------|----------|---------|
| `request` | yes | The request text, as written |
| `scan` | no | Codebase hints: `files_estimate` (whole number), `touches_ui` (true or false), `notes` (text) |
| `override` | no | `simple`, `medium`, `large`, `greenfield`, or absent |

If `request` is empty or cannot be read, do not score. Return route `medium` with the single reason `default: no request text`.

## Steps

1. Read the request and the scan notes in full.
2. Extract the seven signals in the Signals table. For each signal that is set, write its evidence: a short phrase from the request or the scan. A signal with no evidence is `false`, or `unknown` for `files_affected`. A claim the evidence does not support (for example, the request says "security change" and the scan says copy-only) is not a signal: set it `false` and write the mismatch as that signal's evidence.
3. Check `greenfield` against its definition. A true `greenfield` sets the route whatever the score (step 5).
4. Compute the score with the Rubric. List one reason for each non-zero term.
5. Map the score to a band and a route with the Bands and routes table. Greenfield overrides the table.
6. If `override` is given, it replaces the route. Keep the computed score, band and reasons.
7. Emit the decision record (Output record) and report the route with its reasons.

Completion criterion: every set signal has evidence; the reasons add up to the score; the band and route follow from the score (or from greenfield); the record has the shape in Output record.

## Signals

| Signal | Set when | Evidence examples |
|--------|----------|-------------------|
| `files_affected` | `one`, `few` or `many`. Use the scan `files_estimate`: 1 is `one`, 2 to 5 is `few`, 6 or more is `many`. With no estimate, count the files the request names: 1 is `one`, 2 to 5 is `few`. Otherwise `unknown` | "request names pager.py only"; "scan estimate 12" |
| `new_capability` | The request asks for a new feature, system or service | "add a CSV export button"; "new billing service" |
| `scope_ambiguous` | No clear single entry point: the request states a goal but not where to change | "make the app faster" |
| `user_facing_ui` | The change alters a screen, page, form or other interface a user sees. A scan value of `touches_ui: true` is evidence | "orders page"; "touches_ui: true" |
| `sensitive_domain` | A list of any of `security`, `auth`, `payments`, `data_migration` that the change touches. Each category is listed once. The request or the scan must name the area the change touches. A claim the scan contradicts is not listed | "password check" (auth); "Stripe" (payments); "migrate user table" (data_migration) |
| `bug_with_location` | The request is a bug fix and cites a file or a line | "pager.py line 42" |
| `greenfield` | The request is to create a new project or product from nothing. Adding a feature to an existing app is `false` | "build a new habit-tracker app" is true; "add a settings page to the app" is false |

The importance of a feature, or a topic that sounds sensitive, is not evidence. A settings page is not a security change unless the request or the scan says it touches one.

## Rubric

If `config.yaml` is present, its `weights`, `bands` and `routes` replace the values below. The values below are the defaults.

Points per signal:

| Signal | Points |
|--------|--------|
| `files_affected` | one 0; few 1; many 3; unknown 2 |
| `new_capability` | true 3 |
| `scope_ambiguous` | true 2 |
| `user_facing_ui` | true 2 |
| `bug_with_location` | true -3, applied to the other signals only |
| `sensitive_domain` | 3 once if any category is listed, not per category |

Compute:

    other = files_affected + new_capability + scope_ambiguous + user_facing_ui + bug_with_location points
    score = sensitive_domain points + max(0, other)

Rules:

- `bug_with_location` can cancel size and ambiguity. It never cancels the sensitive_domain points. A one-line fix in an authentication path still scores 3 and routes to medium, because a cited location shows the change is small, not that it is safe.
- When `other` is below zero, add the reason `floor at 0 +N`, where N is minus `other`. The reasons then add up to the score.
- Reasons list each non-zero term as `<signal> <points>`, for example `new_capability +3`, `files_affected few +1`, `bug_with_location -3`. If no term is non-zero, the reasons list is empty.

## Bands and routes

| Score | Band | Route | What the route means |
|-------|------|-------|----------------------|
| 0 to 2 | low | `simple` | Straight to a direct worker, with no spec or architect |
| 3 to 6 | medium | `medium` | An architect's plan, then a worker |
| 7 or more | high | `large` | Full specialist review and plan, then workers |
| any, with `greenfield` true | n/a | `greenfield` | Product definition, then architecture, then parallel workers |

The band comes from the thresholds in `config.yaml`: `low` when the score is below `medium_at`, `medium` when it is at least `medium_at` and below `high_at`, `high` when it is `high_at` or more. The defaults are `medium_at: 3` and `high_at: 7`. The route for each band comes from the `routes` table in `config.yaml`. When `greenfield` is true, the band is `n/a` and the route is `greenfield`, whatever the score. The score is still reported.

## Override

If `override` is given, the route is the override and `overridden` is `true`. The band stays as computed. The score and reasons are still reported, so a person can compare the rubric with their own decision later.

## Re-route

When work shows the task is larger or smaller than the route assumed (for example, the fix needs changes in more files than the scan said), run the steps again with the new evidence. Emit a new record with `reroute_reason` saying what changed. A route can go up. A route can go down only with a note saying why. Re-route at most once on your own. After that, a change of route is for a person to decide.

## Not this skill

- Writing a spec, a plan or a ticket list. Run this skill before planning, not as the plan.
- Deciding whether work needs a shared map of decision tickets across sessions. A `large` route sizes the process; it does not chart a map.
- Deciding whether an issue is ready for an agent or for a person. That is a decision about who does the work, not how much process it needs.
- Asking the requester questions. When `scope_ambiguous` is true, the record shows the ambiguity. Clarifying questions are a separate step.
- Estimating hours or cost, or choosing tools.

## Limits

- The signals come from reading the request and the scan. A vague request gives thin evidence, so the route is a weak first guess. Say so in the reasons.
- The rubric arithmetic is fixed. Reading the signals is judgement, so two runs on one request can differ in a signal and so in the route.
- Route accuracy has not been measured against labelled requests.

## Output record

```json
{ "pack_version": "0.1.0",
  "score": 6,
  "band": "medium",
  "route": "medium",
  "signals": {
    "files_affected": "few",
    "new_capability": true,
    "scope_ambiguous": false,
    "user_facing_ui": true,
    "sensitive_domain": [],
    "bug_with_location": false,
    "greenfield": false,
    "evidence": {
      "files_affected": "scan estimate 2",
      "new_capability": "add a CSV export button",
      "user_facing_ui": "orders page" } },
  "reasons": ["new_capability +3", "user_facing_ui +2", "files_affected few +1"],
  "overridden": false }
```

| Field | Rule |
|-------|------|
| `pack_version` | `"0.1.0"` |
| `score` | Integer, the computed score. Always reported, even when overridden or greenfield |
| `band` | `low`, `medium`, `high`, or `n/a` for greenfield |
| `route` | `simple`, `medium`, `large` or `greenfield`. The override when `overridden` is true |
| `signals` | The seven signals. Give evidence for each signal that is set (true, one, few, many or a category). For an unsupported claim, the signal is false and its evidence states the mismatch. Leave evidence out for the others |
| `reasons` | The non-zero terms and any floor reason. They add up to `score` |
| `overridden` | `true` only when `override` was given |
| `reroute_reason` | Only on a re-route: what changed |

## Files

| File | Purpose |
|------|---------|
| `PACK.md` | This file: the procedure, rubric, bands and output record |
| `config.yaml` | Weights, thresholds and route names. When the file is present, use its values. When it is absent, use the tables in this file |
| `schema/signals.json` | JSON Schema for the signals object |
| `schema/decision.json` | JSON Schema for the decision record |
| `fixtures/F1.yaml` to `fixtures/F12.yaml` | Checks with the expected route. Not run against a model |
