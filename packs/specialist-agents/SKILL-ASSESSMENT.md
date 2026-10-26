# specialist-agents: skill assessment

> **Date:** 2026-10-25 · **Spec read:** `specialist-agents-spec.md` (Draft v0.1, `pack_version: 0.1.0`) · **Form assessed:** `agents`
> No `PACK.md` is built. No agent file is written. Only this file was created.

## 1. Verdict

**`agents`.** The earlier verdict in `docs/assessments/skills-for-claude-mods.md` (row 7) holds for the five role prompts. Two corrections:

1. **The sequence is not an agent.** Spec sections 5.7 (sequence and skipping), 5.8 (hand-off) and 6 (configuration) need a caller that runs the roles in order, reads each `needs:` field, and records each `skipped: reason`. A subagent definition cannot do this for the others. The pack therefore needs a caller contract and five role files. Spec section 2 places routing outside this pack.
2. **"None found" for overlap was wrong.** The installed skills overlap in part with four roles (section 3). None duplicates a role outright.

Reason: each role is one self-contained prompt with a defined input and output, which a parent agent can run in its own context and read back as one object. Skill files are not the right form, because a skill runs in the parent's context and cannot return a separate typed output.

## 2. Fit evidence

- **One session, no other system.** A subagent receives one prompt and returns one message. It cannot ask the user questions in turn. So the Analyst returns `open_questions[]`, and the caller asks the user. This matches spec 5.2 ("Do not propose a solution") and the "Do not" rules.
- **Files alone are enough for four roles.** Analyst, Product Manager, UX Designer and Architect need only their inputs (spec 4.1 and `prior[]`) and, for the last three, the `codebase_notes` string. Developer also needs repository access.
- **Inputs from the user.** One request string. Optional: `codebase_notes` and an `alignment` summary.
- **Full sequence needs a caller.** Running all five roles needs code or a Coordinator that holds the prior outputs as objects. Without it the pack is five prompts and a schema set.
- **Target folder.** `~/Developer/claude-mods/agents/` holds only `.gitkeep`. No subagent file format exists yet in that repo (its `README.md` says "Subagent definitions" and nothing more).

## 3. Overlap

Each row quotes the line it is based on. Skills marked "headers only" or "top of file" were read only at the top, or quoted from a search hit, not read in full.

| Installed skill | What it does (quoted) | What this pack adds or lacks |
|-----------------|-----------------------|------------------------------|
| `grilling` (read in full) | "Ask the questions one at a time, waiting for feedback on each question before continuing." | Overlaps the Analyst's question-gathering. The pack adds a non-interactive output with `default_if_unanswered`. It lacks interaction. The Analyst is the non-interactive half; the live questioning belongs to `grilling`. |
| `grill-me`, `batch-grill-me` (read in full) | `grill-me`: "Run a `/grilling` session." `batch-grill-me`: "Ask the whole frontier in one round". | Same overlap as `grilling`. The pack adds nothing for these two. |
| `to-spec` (read in full) | "produces a spec", also called a PRD; template sections "## User Stories" and "## Implementation Decisions". | Overlaps the PM (user stories) and part of the Architect (implementation decisions). The pack adds the press release, FAQ, success metrics, and checkable acceptance arrays. `to-spec` also says "Do NOT interview the user", which matches the Analyst's rule. |
| `domain-modeling` with `ADR-FORMAT.md` (read in full) | "That's it. An ADR can be a single paragraph." | **Conflict in strictness.** The spec's Architect requires context, decision, consequences and alternatives (spec 4.2; fixture F5 requires alternatives). Section 4 below and decision 5 cover this. |
| `implement` (read in full) | "Use /tdd where possible, at pre-agreed seams." and "Commit your work to the current branch." | Overlaps the Developer's implement-and-test step. The pack adds the ladder record, the SHORTCUT rule and risky-logic-only tests. The commit line conflicts with decision 6. |
| `tdd` (top of file and search) | "Refactoring is not part of the loop." | Compatible. The Developer role needs no refactor step. |
| `code-review` (headers only) | "Both axes run as **parallel sub-agents**". | Shows the parallel-subagent pattern this pack would use. It does not overlap a role. Its Standards and Spec axes review the Developer's output; they are not a role. |
| `design-an-interface` (headers only) | "Spawn 3+ sub-agents simultaneously using Task tool." | Partial overlap with the Architect's alternatives. Not a role overlap. |
| `research` (top of file) | "Spin up a **background agent** to do the research". | Partial overlap with the Analyst's codebase lookups. The pack adds nothing a research run needs. |
| `handoff` (headers only) | "Compact the current conversation into a handoff document for another agent to pick up." | Partial overlap with the spec's hand-off rule (5.8). The spec's rule is structured output, not prose. |
| `frontend-design` plugin (description only) | "Guidance for distinctive, intentional visual design when building new UI" | Overlaps only the visual side of UX. Spec 5.4 covers flows, wireframes and states, not aesthetics. |
| `triage`, `wayfinder`, `ask-matt` (headers only) | Issue-tracker triage, decision maps and skill routing. | No overlap with a role. |

## 4. What blocks it today

1. **No schema.** The spec's output lists (4.2) are prose. `schema/<role>.json` does not exist. Nothing can validate a role's output.
2. **`needs` and `skipped` are missing from the output contracts.** Spec 5.7 and 5.8 require `needs: [<role>, <what>]` and `skipped: reason`. Spec 4.2 lists neither. Every schema must add both.
3. **Cross-pack dependency in the Developer.** Spec 5.6 says "run the minimalism ladder" and "Add tests for risky logic only". The rules live in `minimalism-ladder` and `test-policy`. The independence rules (`packs/README.md`, rule 3) forbid importing another pack. Copying the rules would duplicate them. Decision 2 covers this.
4. **Model choice.** Spec 12.2 (non-normative) uses `model: default`, a gateway alias. Spec section 6 names no model. The agent body must name no model. The caller sets the model when it starts the role.
5. **Harness wording.** An agent file needs front matter in each harness's format. The body must stay neutral. Tool names go in front matter as capability names, mapped at install time (section 5.0).
6. **Non-normative code uses different keys.** Spec section 12 returns `prfaq`, `architecture`, `code` and similar keys. Spec section 4.2 (normative) defines different keys. Section 12 says sections 1 to 11 win. Agent files must follow 4.2 and must not copy section 12.
7. **Pruning.** Spec 5.9 says "Rules without a fixture are candidates to delete." Rules without a fixture in 5.1 to 5.6 include "Be concrete: name files, fields, numbers. Skip generic advice." and "Do not expand scope." The owner decides whether to keep them.
8. **Nothing has run.** Fixtures F1 to F10 have no runner. Acceptance criteria 5 and 6 need a person or a runner.
9. **Banned-word check.** Spec sections 4 and 5 contain no UMAS, harness or vendor wording, and no percentage figures (checked, section 6 below). "Known consumers" (section 9) stays in the spec.

## 5. Design of each role (agents form)

### 5.0 Form

- Source files in the pack: `agents/<role>.md` (five files), `schema/<role>.json` (five), `fixtures/F*.yaml` (ten), `config.yaml` (caller data).
- Each role file has two parts:
  - **Front matter (per harness, written at install time):** `name`, `description` (one sentence: when a parent runs this role), and `tools` as capability names from the list below.
  - **Body (neutral, the deliverable):** the common preamble (spec 5.1 with `{{role}}` filled in), the role's rules (5.2 to 5.6), the inputs, the output contract, the do-not list and the stop rule.
- The body names no model, no harness, no slash command, and no tool name. Capability names are `read` (open a named file), `search` (find text or file names), `edit` (change named files), and `run` (run a command the caller names).
- The output is one JSON object that validates against the role's schema, with nothing outside it. This is the only way a parent can check a subagent's result.

Sketch of the shape (placeholders in braces; not a file):

```text
---                          front matter, written per harness at install time
name: analyst
description: Clarifies a request before design; run first for complex work.
tools: [read, search]
---
You are the {{role}} on a small team. ...   (spec 5.1 preamble)
{{role rules: spec 5.2}}
Inputs: request, codebase_notes (optional), alignment (optional), prior (array).
Output: one JSON object that validates against schema/analyst.json. Nothing else.
Do not: ...
Stop when: the object is complete and validates.
```

Common output fields for every role: `role`, `pack_version` (`"0.1.0"`), `based_on` (IDs of the prior outputs used), plus `needs` (see decision 8) and `skipped` (set by the caller, not by the role).

### 5.1 Analyst

| Item | Design |
|------|--------|
| Inputs | `request`; `codebase_notes` (optional); `alignment` (optional, from `grilling`). `prior` is normally empty. |
| Output | `restated_request` (1 or 2 sentences), `assumptions[]`, `open_questions[{question, why_it_matters, default_if_unanswered}]` (at most 7, from config), `ambiguities[]`, `out_of_scope[]`, `ready` (bool) |
| Must not | Propose a solution or design. Ask the user in turn (it returns questions). Choose a value the request did not give; it records a default instead. Set `ready: true` while an open question would change the design. Re-ask a question that `alignment` already answers (gap check only). |
| Tools | `read`, `search`. It looks up facts in the repo before it asks, as `grilling` does ("look it up rather than asking me"). |
| Stop when | Every open question has a default, and `ready` is set. |

### 5.2 Product Manager

| Item | Design |
|------|--------|
| Inputs | `request`; `prior` (the Analyst output, when present); `codebase_notes` (optional, for existing users only). |
| Output | `press_release {headline, summary, problem, solution, quote?}`, `faq[{q, a}]` (at least 3 per F3), `user_stories[{as_a, i_want, so_that, acceptance[]}]` (each acceptance item checkable), `success_metrics[{metric, target, how_measured}]` (at least 1 per F3) |
| Must not | Choose technology. Design screens. Name components, data models, endpoints or files. Write a story with no checkable acceptance item. |
| Tools | None. The inputs are enough. |
| Stop when | Every story has at least one checkable acceptance item, and each metric has a target and a method. |

### 5.3 UX Designer

| Item | Design |
|------|--------|
| Inputs | `request`; `prior` (Analyst and PM outputs); `codebase_notes` (names of existing components and their states). |
| Output | `flows[{name, steps[]}]`, `wireframes[{screen, text_layout}]` (text only), `components[{name, states[], notes}]` (states from default, loading, error, empty, disabled), `interactions[]`, `accessibility_notes[]` |
| Must not | Decide data models, back-end design, endpoints or storage. Add a component that `codebase_notes` already lists (reuse it). Write code or markup. |
| Tools | `read`, `search`, to confirm an existing component when `codebase_notes` is unclear. |
| Stop when | Every flow has error and empty states named for each component that needs them (F4). |

### 5.4 Architect

| Item | Design |
|------|--------|
| Inputs | `request`; `prior` (Analyst, PM and UX outputs); `codebase_notes` (stack and installed dependencies); `alignment` (optional). |
| Output | `decision {context, decision, consequences[], alternatives[{option, reason_rejected}]}` (one decision per record), `stack[{choice, reason, installed_already: bool}]`, `api_contracts[]`, `data_models[]`, `risks[]`. Each `installed_already: true` cites a manifest or lockfile path as evidence. |
| Must not | Write implementation code. Re-decide a decision that a prior record already made; it cites that record in `based_on`. Add a new dependency when an installed one does the job, without a reason in `reason`. Plan beyond the PM's scope. |
| Tools | `read` (manifests, lockfiles, existing contracts), `search`. Read only. |
| Stop when | Each stack choice has `installed_already` set, with evidence for each `true`. |

### 5.5 Developer

| Item | Design |
|------|--------|
| Inputs | `request` or the approved plan; `prior` (PM acceptance items, Architect decision and contracts, UX components); `codebase_notes`; `ladder_rules` and `test_rules` (text from the caller, see decision 2); `test_command` (named by the caller). |
| Output | `plan[]`; `ladder_record` (the shape in `minimalism-ladder`'s output record); `changes[{path, summary}]`; `tests[{target, why}]`; `shortcuts[{what, fix_when}]`; `unresolved[]`. |
| Must not | Expand scope. Requested-looking extras go to `unresolved[]`. Add a helper or dependency where an earlier rung holds (F6, F8). Write tests for formatting-only changes (F7). Write comments other than the SHORTCUT form. Commit (decision 6). Use a library that a prior ADR does not pick (F8). |
| Tools | `read`, `search`, `edit`, `run` (only the caller's `test_command` and lint command). No network. No package install. |
| Stop when | Every change is made, the `test_command` output is recorded, and `ladder_record` is complete. If `ladder_rules` is empty, return `needs: [caller, ladder_rules]` and make no change. |

## 6. Verification done in this assessment

| Check | Result |
|-------|--------|
| Spec section numbers cited here (4.1, 4.2, 5.1 to 5.9, 6, 8.1, 9, 12) | Exist in `specialist-agents-spec.md`. Checked by reading the headings. |
| Banned or harness wording in spec sections 5.1 to 5.8 (`grep -i -E "umas\|claude\|codex\|copilot\|gemini\|openai\|anthropic\|/[a-z-]+ "`) | No hits. |
| Percentage figures in the spec (`grep -E "[0-9]+ ?%"`) | No hits. |
| Overlap quotes in section 3 | Each quote was read in the installed file on 2026-10-25. Headers-only rows are marked. |
| Fixtures F1 to F10 | **Not run.** No model run is part of this task. |
| Schemas | **Not built.** Nothing to validate. |
| Agent files | **Not written** (form only, per brief). |
| Scripts | None. Cross-platform check: not applicable. |

Fixture mapping (for the later build; all **not run**):

| Fixture | Run against | Note |
|---------|-------------|------|
| F1, F2 | Analyst | Both are Analyst inputs. |
| F3 | Product Manager | |
| F4 | UX Designer | |
| F5 | Architect | Needs `installed_already` evidence from a manifest. |
| F6, F7, F8 | Developer | F8 needs a prior ADR as input. |
| F9 | Caller | Tests sequence reduction and skip records. No role runs. |
| F10 | Each role, wrong-shape input | Expects `needs:` rather than a guess. |

## 7. Enhancements, in priority order (before the build)

1. Add `needs` and `skipped` to every output schema (decision 8).
2. Build the five JSON schemas. Check each with `python3 -I -c "import json,sys; json.load(open(sys.argv[1],encoding='utf-8'))" <file>`.
3. Write the Developer's `ladder_rules` and `test_rules` inputs, or the chosen alternative (decision 2).
4. Write the five role files from section 5, with the shared preamble text identical in each. A check compares the five preambles.
5. Write the caller contract: the order, the schema check, one retry on a bad shape, `needs` handling, and the skip record. This is the part that makes F9 and F10 testable. A schema check in the standard library needs a small validator, as `test-policy` did with its YAML subset reader.
6. Run F1 to F10 with a person or a runner. Record each result. Until then, mark every fixture not run.

## 8. Decisions needed from the owner

1. **Where the sequence lives.** (a) Ship the role files here and keep the sequence and skip rules as data in `config.yaml` for the Coordinator to read. (b) Ship the caller here too. **Recommendation: (a).** Routing belongs to `router-heuristic`, and the run loop belongs to a Coordinator (spec section 2 names both as non-goals). This pack stays five roles plus the data.
2. **How the Developer gets the ladder and test rules.** (a) The caller passes `ladder_rules` and `test_rules` as text. If empty, the Developer returns `needs:`. (b) Copy the rules into the Developer file. **Recommendation: (a).** A copy would be a second source of the same rules. The `needs:` path makes a missing input visible.
3. **Preamble in each file or concatenated by the caller.** **Recommendation: in each file.** Each role file must work alone, and five short copies are cheaper than a missing preamble. A check keeps the copies identical.
4. **Analyst when `alignment` is given.** Spec open question 1 asks if a separate Analyst is needed after grilling. **Recommendation:** keep the Analyst and run it in gap-check mode when `alignment` is given. Add a skip rule only after a fixture shows the overlap costs time.
5. **ADR shape.** The spec's Architect fields (with alternatives) are stricter than the installed `ADR-FORMAT.md`. **Recommendation:** keep the spec fields. The caller maps them to `ADR-FORMAT.md` when it files the decision.
6. **Developer commits.** The spec does not say. The installed `implement` skill commits. **Recommendation:** the Developer does not commit. The caller commits under the project's rules.
7. **Agent file format.** No format exists in `claude-mods/agents/`. **Recommendation:** keep neutral source in this pack, and write the harness front matter in the install step, as section 5.0 describes.
8. **Spec change.** Adding `needs` and `skipped` to 4.2 changes the design record. The spec is not edited in this task. **Recommendation:** approve the change, then the owner edits the spec.

## Changes made

- Created: `packs/specialist-agents/SKILL-ASSESSMENT.md` (this file).
- Not created: `PACK.md`, `agents/`, `schema/`, `fixtures/`, `config.yaml` (not part of the `agents` form in this task).
- No other file changed.
