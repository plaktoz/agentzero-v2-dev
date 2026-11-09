# AGENTS.md

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
- Ask the user only about decisions that are hard to reverse, affect other teams or projects, or are a matter of preference.
- Pick a default for every other choice. List each default in one "Defaults taken" list, which the user can veto in one reply.
- Send each decision gate once, as one brief of at most four questions. Length follows the context the owner needs: do not cut a question to fit a page.
- Write each question so the owner can decide from it alone, without opening a file:
  - **Context.** What the decision is, why it matters now, and what the spec and the code say today, with file and line. Say where they disagree.
  - **Options.** For each: what it changes, its gain, its risk or cost, and the files it touches.
  - **Assessment.** The likelihood and the impact of each risk, and what cannot be undone. Show the evidence from your check, not only the conclusion.
  - **Recommendation.** One option, with the reasons, and what would change your mind.
- Before you send a brief, check each question: if the owner could ask "what is this about?" or "why this option?", the context or the assessment is missing. Add it.
- Probe the facts a spec relies on with a short live check before the spec states them. Record the result, not a guess.

### 2. Write the task list

- Give each task its acceptance criteria: the observable result that means the task is done.
- Keep the task list in a file in the repo (for example in `docs/`), not only in the conversation.

### 2a. Caller assessment gate

- Before anything is implemented, one assessor subagent reviews the spec against all its callers (the modules, libs or packs that call it). Use `umas/TECHNICAL-DESIGN-SPEC.md` as the map of the overall flow.
- The assessor plays devil's advocate. It looks for missing parameters, interfaces, failure paths, permissions and open decisions. It does not write the spec.
- The assessor reports blockers, at most 10 majors, and minors. Minors go to a fix list and are not reviewed one by one.
- A spec with a blocker is rejected. Revise it. Round 2 checks only the fixed blockers, with a fresh subagent.
- Stop after two rounds. Bring the remaining blockers to the user as decisions.
- Record the verdict (accepted, rejected, or accepted with open items) and the blocker count in the task list. The full report stays in `docs/assessments/`.

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

- Use the `ste-docs` skill for a library README or pack spec (`packs/<name>/<name>-spec.md`), and for other technical documents about a library, pack, agent or hook.
- Use `libs/hook-store/README.md` and `libs/event-log/README.md` as the structure reference.
- The spec states the contract that callers depend on: commands, exit codes, file formats and failure modes. Internal detail belongs in code and tests.
- Each fact lives in one place. The spec holds the contract. The task file holds state and decisions. Do not repeat a fact in a third file.
- Build the HTML twin at release, not after every change.

### Keep in sync

- After every change, check the README of the library or the spec of the pack you changed, then each README above it (`libs/README.md`, `packs/README.md`), and confirm they still match the spec.
- Look for stale claims: commands, file paths, section references, language choices, platform support, and status tables.
- Fix any README that is out of sync in the same change. If you cannot fix it, say which one and why.

## Cross-platform

- Review all generated code for whether it runs on both Windows and Linux (macOS too, where the repo supports it) before calling it done.
- Check for hardcoded `/` path joins, `HOME` without a `USERPROFILE` fallback, POSIX-only shell commands, `python3`-only interpreter calls, missing `encoding="utf-8"`, and CRLF handling.
- If you cannot run it on an OS, say so and mark that part "verified by reading", not "verified".

## Rules

- Before implementing anything, run the caller assessment gate (2a).
- When a decision is needed from the user, always elaborate the details and give an assessment. Give the context and a thorough assessment of every option (section 1), not a name and a recommendation.
- Do not use the web_search tool.
- Keep the kc-axi independent and as general as possible so it can be reused outside UMAS.
- `test-adapters` is an external dependency, kept in its own repository (<https://github.com/plaktoz/test-adapters>). UMAS calls its command line and does not import it. Do not copy its contract into this repo; point to its requirements and record only what UMAS needs from it (`libs/test-adapters/README.md`).

## Shared skills

Run `python scripts/setup_codex.py` (or `python3` on macOS) to expose existing
Claude skills through `.agents/skills/`, which Codex scans. The script links
skills from `~/.claude/skills/` and `.claude/skills/`; project skills take
precedence. Use `--claude-home PATH` for a different Claude configuration directory.
Run it again after adding skills. If the skills do not appear, restart Codex.

Skill contents stay in their original directories, including supporting files.
Generated links are local and ignored by Git. Existing unrelated skills are
preserved; conflicting names cause an error instead of being overwritten.

Claude-specific hooks, permissions, MCP configuration, slash commands, and
subagent definitions are not installed by this script. Use Codex's own tools
and approval rules when shared instructions refer to Claude-specific tools.

On Windows, creating directory symlinks may require Developer Mode or an
elevated terminal.

Reference: [Codex skills documentation](https://developers.openai.com/codex/skills).
