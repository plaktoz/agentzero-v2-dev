---
name: minimalism-ladder
description: Minimalism ladder for any change that adds code, files or dependencies. Reads the relevant code, walks six rungs in order (not needed, already in the codebase, standard library or platform, installed dependency, one line, minimum code), stops at the first rung that holds, and emits a record of where it stopped and the evidence. Use when a task asks for code, a file or a dependency to be added, before the first line is written.
---

# Minimalism ladder

Solve the problem before you write code. Read first, climb the ladder, stop at the first rung that holds, then report where you stopped.

## Not this skill

Do not use this skill for:

- Answering a question or explaining code without changing it.
- Reviewing the design or quality of code that already exists. The ladder decides how new code is written, not whether old code is good.
- Scanning a repository for shortcut comments or debt. The comment format is defined here; scanning is a separate job.
- Dropping or narrowing requested work. Rung 1 drops only what was not asked for, and a requested feature is always built.
- Estimating savings. `loc_estimate` is an estimate of this change only.

## Steps

Run these in order. Do not start a step until the completion criterion of the previous one is met.

1. **Read.** Follow "Read first". Done when every file the change touches and each call site it would affect has been read in this run, or is in `code_context`.
2. **Climb.** Ask the six questions in the Prompt, following the Stop rule. Done when you have stopped at one rung, with a `notes` reason for each rung you moved past.
3. **Check evidence.** Follow "Evidence". Done when each entry for rungs 1 to 4 is confirmed to exist. An entry you cannot confirm means you have not reached that rung: return to step 2.
4. **Write.** Write what the stopping rung needs, and the behaviour the task requires. Done when the change is written and each deferral has a shortcut comment and a `shortcuts` entry.
5. **Apply the level.** Follow "Enforcement levels". Done when its extra requirements are met, or none apply.
6. **Record.** Follow "Output record". Done when every field is set and `rung_name` and `decision` are the pair for the stopping rung.

## Read first

The ladder runs only after you have read the files the change touches and the call sites it would affect. Before you answer rung 2, you must have read them. If `code_context` in your input is empty, or you have not read those files, read them now.

Reading and scope analysis are never skipped. The ladder is lazy about the solution, not about the investigation.

## Prompt

You solve before you write. Read the relevant code and trace the real flow first.
Then ask these questions in order and stop at the first one that holds:

1. Does this need to exist? If it was not asked for, do not build it.
2. Does it already exist in this codebase? If so, reuse it.
3. Is it in the standard library or the platform? If so, use that.
4. Is it in a dependency that is already installed? If so, use that.
5. Can it be done in one readable line? If so, write the line.
6. Otherwise write the minimum code that works.

Being lazy about the solution does not permit skipping the reading or the scope analysis. Do those fully. Do not add abstraction, options, or fallbacks that the task did not ask for.

Comments: write one only when the reason for the code is non-obvious. The single exception is a deliberate deferral, written exactly as

    SHORTCUT: <what was deferred> -- <when to fix>

using the language's comment syntax.

When done, report the rung where you stopped and the evidence for it.

## Stop rule

Stop at the **first** rung that holds. Do not continue to a later rung "to be safe". To move past a rung, state the reason in `notes`, for example: "existing helper handles UTC only; task needs local time".

## Requested work

Rung 1 applies only to work that was not asked for. A requested feature is never dropped at rung 1.

If the task or a plan mentions something it did not ask for (for example "also add caching"), do not build it, and record it in `notes` as dropped.

Behaviour the task requires is part of "minimum code that works". Input validation, error handling and any behaviour the task names are written. The ladder bounds new code; it does not remove required behaviour.

## Evidence

Each entry in `evidence` is a path relative to the repository root, or `path:symbol`. It must point at something that exists in the repository. Rungs 1 to 4 need at least one entry:

- Rung 1: the file or spec that states the request, or the code the unrequested work would have touched.
- Rung 2: the existing code that already does the job.
- Rung 3: a place in this repository where the platform facility is already used or declared, such as an import or a call.
- Rung 4: the manifest or lockfile entry that declares the dependency.

Do not claim reuse you cannot point to. If you cannot point to evidence for a rung, you have not reached that rung.

## Shortcut comment

Format:

    // SHORTCUT: sync call to avoid queue setup -- revisit before 100 users
    # SHORTCUT: sync call to avoid queue setup -- revisit before 100 users

Both parts are required: what was deferred, and when to fix it. The separator is `--`, an em dash, or a spaced hyphen. A shortcut comment is the only comment that does not explain why the code exists. Do not write decorative, redundant or narrating comments.

Each shortcut also appears in the record's `shortcuts` array, with `what` and `fix_when`. A deferral with no "when to fix" is not a valid shortcut. Make the deferral explicit with a fix point, or do not defer.

## Enforcement levels

The level comes from the input field `level`: `lite`, `full` or `ultra`. If none is given, use `full`.

| Level | What you do |
|-------|-------------|
| `lite` | Check rungs 1 and 2 and emit the record. Rungs 3 to 6 are advice only. Do not block on them. |
| `full` | Check all six rungs. Emit the record. Adding code where an earlier rung holds is a finding. |
| `ultra` | As `full`. In addition, a new file, dependency or public abstraction needs a one-line justification in `notes`. Before adding one, propose a deletion or simplification of existing code if that reduces the change. |

## Output record

When done, state in your answer the rung, its `rung_name` and each `evidence` entry, then emit this JSON object.

```json
{ "pack_version": "0.1.0",
  "rung": 3,
  "rung_name": "stdlib_or_platform",
  "evidence": ["path/to/module.ext"],
  "decision": "use_builtin",
  "loc_estimate": 10,
  "shortcuts": [],
  "notes": "Native date input; no picker component needed." }
```

| Field | Rule |
|-------|------|
| `pack_version` | `"0.1.0"` |
| `rung` | The rung where you stopped, 1 to 6 |
| `rung_name` and `decision` | Use the pair for that rung (table below) |
| `evidence` | Required for rungs 1 to 4. See Evidence. Empty only for rungs 5 and 6 |
| `loc_estimate` | Integer. Estimated lines of new code in the change |
| `shortcuts` | One object per shortcut comment, each with `what` and `fix_when`. Empty array if none |
| `notes` | One sentence. Required when you moved past a rung or dropped requested-looking work |

| `rung` | `rung_name` | `decision` | Meaning |
|--------|-------------|------------|---------|
| 1 | `not_needed` | `skip` | Not asked for |
| 2 | `exists_in_codebase` | `reuse` | Existing code does the job |
| 3 | `stdlib_or_platform` | `use_builtin` | Standard library or platform does the job |
| 4 | `installed_dependency` | `use_dependency` | An installed dependency does the job |
| 5 | `one_line` | `write_one_line` | One readable line |
| 6 | `minimum_code` | `write_minimum` | Minimum code that works |
