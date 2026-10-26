# CLAUDE.md

This repo holds the specs for UMAS: libraries (`libs/`), content packs (`packs/`), decisions (`docs/decisions/`), assessments (`docs/assessments/`) and source material (`umas/`). See `libs/README.md` and `packs/README.md` for the layout and concepts.

## Conventions

- Keep each part (library, pack, decision record) self-contained and single-purpose.
- Specs reference parts by path; they don't copy them.
- Library and pack docs are plain markdown, one topic per file, with a short description at the top.
- The structure is provisional. Prefer small changes and update `libs/README.md` or `packs/README.md` when the layout changes.
- Language and stack: Python or TypeScript only. Python is the default and the backend language. Use anything else only when no Python or TypeScript option exists, and record the reason in the decision it affects.
- Don't commit unless the user has asked for commits on this work. Once asked, commit after each task, as "Task management" says.
- Do not read into agent-ignore folder

## Task management

How a piece of work goes from request to done. Follow the steps in order.

### 1. Agree the requirements

- Clarify the requirements first, and wait for the user's go-ahead before you start implementing. A request to plan, review or answer a question is not a go-ahead to change files.
- State the requirements concisely and in plain words: no filler, no padding, no restating the request.
- Give enough detail that the user can see what they are deciding on: the options, what each one changes, and your recommendation.
- Ask only about what the user must decide. Pick the obvious default for the rest, and say which default you picked.

### 2. Write the task list

- Give each task its acceptance criteria: the observable result that means the task is done.
- Keep the task list in a file in the repo (for example in `docs/`), not only in the conversation.

### 2a. Caller assessment gate

- Before anything is implemented, give the spec and its design to each caller (the module, lib or pack that calls it) for assessment. Use `umas/TECHNICAL-DESIGN-SPEC.md` as the map of the overall flow.
- Each assessment is a separate subagent. It plays devil's advocate, and it looks for missing parameters, interfaces, failure paths, permissions and open decisions. It does not write the spec.
- A spec that lacks the detail a caller needs is rejected. Revise it, then assess it again with a fresh subagent. Stop after two rounds and bring the remaining gaps to the user. Gaps that need a decision go to the user, not to a guess.
- Record each verdict (accepted, rejected, or accepted with open items) in the task list next to the spec.

### 3. Do the work

- If a task or subtask is independent, send it to a subagent to complete the work. Give each independent task or subtask its own subagent, and start them in one message so they run in parallel.
- Do not send a task or subtask to a subagent when it is small or when it depends on another task's output.
- The agent doing a task tests and verifies it against its acceptance criteria.
- Hand verification to the user only when the agent cannot do it, such as a Windows-only check on a macOS machine. Say why in the task list.

### 4. Keep the task state

The session can stop at any time: tokens run out, or an endpoint fails. Another person or computer must be able to continue from the repo alone.

- Record each task's state next to the task: `[ ]` open, `[x]` done, `[-]` not done, with the reason. Add the result and how it was verified.
- Once the user has asked for commits, commit after each task, or each group of tasks that belong together. Use several small commits, not one at the end.
- Push when the user has approved pushing for this work, so the state is on the remote too.
- Before a long or risky step, write what comes next in the task list, so a retry can start there.

### 5. Use the current decisions

- Decisions change during a session. Act on the latest decision, not on the state when the session started.
- Before you act on a stored fact (a PR state, a branch, a decision in a file), check it again. For example, check that a PR is still open before you push to it.
- Record a decision where the work it governs lives. For example, a decision about a library goes in that library's README (a pack's spec is `packs/<name>/<name>-spec.md`) or in `docs/decisions/`, so a later review sees it.

## Documentation

How documents are written, and how they are kept true to the code.

### Write

- Use the `ste-docs` skill with its technical profile to write or rewrite any library README or pack spec (`packs/<name>/<name>-spec.md`), and any other technical document about a library, pack, agent or hook.
- Use `libs/hook-store/README.md` and `libs/event-log/README.md` as the structure reference.

### Keep in sync

- After every change, check the README of the library or the spec of the pack you changed, then each README above it (`libs/README.md`, `packs/README.md`), and confirm they still match the spec.
- Look for stale claims: commands, file paths, section references, language choices, platform support, and status tables.
- Fix any README that is out of sync in the same change. If you cannot fix it, say which one and why.

## Cross-platform

- Review all generated code for whether it runs on both Windows and Linux (macOS too, where the repo supports it) before calling it done.
- Check for hardcoded `/` path joins, `HOME` without a `USERPROFILE` fallback, POSIX-only shell commands, `python3`-only interpreter calls, missing `encoding="utf-8"`, and CRLF handling.
- If you cannot run it on an OS, say so and mark that part "verified by reading", not "verified".

## Rules

- Before implementing anything, send the spec and design to the requester for assessment, play devil's advocate in that review, and reject it if details are insufficient.
- When a decision is needed from the user, always elaborate the details and give an assessment.
