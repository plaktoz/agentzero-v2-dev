# minimalism-ladder: fixture results (F1 to F8)

> Run 2026-10-25 against `PACK.md` (pack_version 0.1.0). Each fixture ran in a fresh general-purpose subagent that had only `PACK.md` and the fixture input. Subagents were told not to read other paths and not to write files.
>
> **Judging caveat:** the runs were done by subagents, but the pass/fail judging was done by the author of `PACK.md`. The spec asks for a judge who is not the author. A second judge is still needed before the first release.

## Summary

| Fixture | Expected property (short) | Result | Rung | Notes |
|---------|---------------------------|--------|------|-------|
| F1 | Stops at rung 3, native date input, not a component | PASS | 3 | Output is one `type="date"` input line |
| F2 | Stops at rung 2, evidence names `util/retry.py`, no new helper | PASS | 2 | Reuses `retry()`. Chose `attempts=4` to read "up to 3 times" as 3 retries (judgement) |
| F3 | Rung 3 or 5, no dependency added | PASS | 3 | `strftime("%Y-%m-%d")` with the existing `datetime` import |
| F4 | Reads before answering; no empty-evidence rung 1 to 4 record | PASS (rerun) | 5 | First run had no file access and emitted no record. Rerun with a readable repo read the files and emitted a valid rung 5 record |
| F5 | Stops at rung 4, `csv-parse` used, no second parser | PASS (caveat) | 4 | Evidence is `package.json` and `package-lock.json`. The check passes only because the test repo was built from `project_notes` |
| F6 | Unrequested caching dropped and recorded in `notes` | PASS (caveat) | 6 | Caching dropped and recorded. The record's `rung` is 6 because the endpoint was built. See deviations |
| F7 | Required validation written; ladder does not remove it | PASS (caveat) | 6 | Validation written. The success path and user creation are missing from the snippet (see below) |
| F8 | Deferral matches `SHORTCUT: <what> -- <when>`; no-fix-point draft rejected | PASS | 5 | Draft without "when to fix" rejected, with the reason given. Shortcut entry has both fields |

**8 of 8 pass.** Three passes carry caveats (F5, F6, F7) and F4 needed a rerun. Details follow.

## Evidence check (`scripts/check_evidence.py`)

The records were checked with the script against a test repo built from each fixture's `code_context` excerpts (and, for F5, from `project_notes`). This proves only that the cited paths match the excerpt headers. It is not a check against a real repository.

| Record | Schema | check_evidence exit |
|--------|--------|---------------------|
| F1 | valid | 0 |
| F2 | valid | 0 |
| F3 | valid | 0 |
| F4 (rerun) | valid | 0 (rung 5, no evidence required) |
| F5 | valid | 0 |
| F6 | valid | 0 (rung 6) |
| F7 | valid | 0 (rung 6) |
| F8 | valid | 0 (rung 5) |

F4 first run emitted no record (`NONE`), so there was nothing to validate.

The F8 comment `// SHORTCUT: queue for export deferred, runSync blocks the request on large files -- build the queue once more than 100 active users run exports` matches the shortcut form. The colleague's draft `// SHORTCUT: sync call to avoid queue setup` has no separator and no "when to fix" part, and the same regex rejects it.

## Per-fixture detail

### F1: PASS

```json
{ "pack_version": "0.1.0", "rung": 3, "rung_name": "stdlib_or_platform", "evidence": ["src/forms/booking.tsx:BookingForm"], "decision": "use_builtin", "loc_estimate": 1, "shortcuts": [], "notes": "Rungs 1 and 2 do not hold (the request is explicit and project_notes says no date picker exists in src/ or package.json), and rung 3 holds because the native date input is supported by the stated evergreen browsers." }
```

Code: `<input type="date" name="travelDate" />`. No picker component, file or dependency. The fixture expects "about 10 lines"; the output is one line, which satisfies "not a 300-line component".

### F2: PASS

```json
{ "pack_version": "0.1.0", "rung": 2, "rung_name": "exists_in_codebase", "evidence": ["util/retry.py:retry", "http/client.py:get_json"], "decision": "reuse", "loc_estimate": 2, "shortcuts": [], "notes": "Reuses util/retry.py with attempts=4 for one call plus three retries, which is my reading of \"retried up to 3 times\"; retry() catches every Exception, and httpx.get does not raise on HTTP 5xx, so 5xx responses are not retried until raise_for_status() is added." }
```

Judgement to review: `attempts=4` versus the default 3. The agent also flagged that `retry()` catches every exception and does not retry 5xx responses.

### F3: PASS

```json
{ "pack_version": "0.1.0", "rung": 3, "rung_name": "stdlib_or_platform", "evidence": ["export/invoice.py"], "decision": "use_builtin", "loc_estimate": 1, "shortcuts": [], "notes": "Rung 1 does not apply because formatting the date is requested; rung 2 does not hold because no date-formatting helper appears in the export/invoice.py excerpt and the rest of the project could not be searched." }
```

Code: `inv.issued_on.strftime("%Y-%m-%d")`. The agent assumed `issued_on` is a `date` or `datetime`, which the excerpt does not show.

### F4: PASS (after rerun)

First run (no readable files): the agent emitted no record and said it must read `auth/` and its call sites before rung 2. That satisfies "reads before answering".

Rerun against a readable mock repo (`auth/login.py`, `auth/session.py`):

```json
{ "pack_version": "0.1.0", "rung": 5, "rung_name": "one_line", "evidence": [], "decision": "write_one_line", "loc_estimate": 1, "shortcuts": [], "notes": "No expiry check exists; SESSION_TTL_SECONDS (auth/session.py) and the created timestamp are reused, but rung 2 does not hold because no check exists. Rungs 3 and 4 do not hold: the stdlib has no session expiry and the repo has no dependency manifest. Placed in load_session because login() always creates a fresh session, so a check there would be dead code." }
```

The agent read the files before answering, and an empty `evidence` is valid at rung 5. The placement in `load_session` rather than `login` is a judgement call the agent flagged for confirmation.

### F5: PASS (caveat)

```json
{ "pack_version": "0.1.0", "rung": 4, "rung_name": "installed_dependency", "evidence": ["package.json", "package-lock.json"], "decision": "use_dependency", "loc_estimate": 6, "shortcuts": [], "notes": "Moved past rung 1 because parsing is requested, past rung 2 because the only code read (load.ts) returns raw text with no typed CSV parser, and past rung 3 because Node 20's standard library has no CSV parser (per project_notes)." }
```

The agent used `csv-parse/sync` and wrote no second parser. The caveat: the agent was not allowed to open `package.json` or the lockfile, so rung-4 evidence rests on `project_notes`. The test repo's two files were synthesised from `project_notes`, so the script's exit 0 says nothing about the real manifest.

### F6: PASS (caveat)

```json
{ "pack_version": "0.1.0", "rung": 6, "rung_name": "minimum_code", "evidence": ["src/routes/orders.ts", "src/routes/orders.ts:orders"], "decision": "write_minimum", "loc_estimate": 9, "shortcuts": [], "notes": "Dropped the planned Redis caching as unrequested because the task asks only for the endpoint and no Redis client is in package.json; rungs 2 to 4 did not hold because the only code read (listOrders) lists orders rather than returning one, the store module was not in code_context so no existing order lookup is cited, and no installed dependency looks up an order, though the Express Router already used in orders.ts provides the route line." }
```

Code: `orders.get("/:id", ...)` calling `getOrder(req.params.id)`. The caching is dropped and recorded in `notes`, which is the property. Caveat: the record's `rung` is 6 because the endpoint was built. A strict reading of "Rung 1: dropped" would want rung 1 for a multi-part task. The spec does not say how to record that (see deviations). The `getOrder` accessor was not in the input, so the snippet assumes it exists.

### F7: PASS (caveat)

```json
{ "pack_version": "0.1.0", "rung": 6, "rung_name": "minimum_code", "evidence": ["src/routes/auth.ts"], "decision": "write_minimum", "loc_estimate": 15, "shortcuts": [], "notes": "Passed rungs 1 to 5 because /signup is requested, Node has no built-in validator, no validation library is installed, and the route plus both checks cannot fit one line; rung 2 was checked only against the auth.ts excerpt, and the user-creation step is not written because the user store API was not in code_context." }
```

The email and password checks are written (400 on failure), so the validation property holds. Caveats: the snippet has no success response, so a valid request would never answer; user creation and password hashing are not written because the user store was not in the input. The agent also flagged that `req.body` depends on a JSON body parser that it could not confirm is mounted.

### F8: PASS

```json
{ "pack_version": "0.1.0", "rung": 5, "rung_name": "one_line", "evidence": [], "decision": "write_one_line", "loc_estimate": 1, "shortcuts": [{ "what": "queue for export deferred; runSync blocks the request on large files", "fix_when": "once more than 100 active users run exports" }], "notes": "Rungs 1 to 4 do not hold because the deferral comment was asked for, no existing code or platform facility records deferrals, and no dependency applies; the queue build is dropped as the task says not to build it, and the colleague's draft comment is replaced because it had no fix point." }
```

## Not verified

- **Acceptance criterion 3 (lite):** no lite-level run was done. F1 to F8 all ran at `full`.
- **Acceptance criterion 4 (ultra):** no ultra run was done, so the one-line justification for a new file was not tested.
- **Acceptance criterion 5 (20 tasks, diff size):** not run. The spec says it does not require the unverified savings figures.
- **Independent judge:** the author judged all eight results (see the caveat at the top).
- **Real-repo evidence:** the evidence checks used synthesised repos, not real project trees.
- **Schema validation in the test suite:** the records were validated with `jsonschema` in a temporary venv outside the repo. The repo tests do not run schema validation, and the pack has no schema dependency.
