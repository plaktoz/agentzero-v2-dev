# playbook-runner: skill assessment

> **Date:** 2026-10-25 · **Spec:** [playbook-runner-spec.md](./playbook-runner-spec.md) (v0.1.0) · **Method:** read-only. No model run, no fixtures run. Parsing and cross-references checked with scripts in a scratch directory (removed).

## 1. Verdict

**`needs engine`.** A skill can carry the format and the gate rules, and an agent can stop at a human gate in a live session, but enforcement, state across pauses and timeouts need an engine that a skill cannot provide (section 6 covers the narrower skill I considered).

## 2. Fit evidence

**What a skill can carry, tested by reading the spec against the skill format:**

| Spec element | Can a skill carry it? | Notes |
|---|---|---|
| Playbook format (phases, steps, gates) | Yes | It is Markdown with YAML front matter. Ruby's full YAML parser (Psych) reads both built-in playbooks. The repo's stdlib subset parser (`packs/test-policy/scripts/yaml_subset.py`) rejects them at line 6, because they use flow mappings such as `{pack: ...}`. |
| Phase order | Yes | Plain instruction. |
| `human_approval` gate | Yes, in one live session | The agent stops, shows the phase outputs and the gate prompt, and waits for a reply. This is the same shape as `grilling` and `wayfinder` HITL. Holds only while the human is present. |
| `auto` gate with `on_reject: retry` | Partly | The agent can run the check and read the result. It can retry once if it records the first attempt. |
| `timeout_seconds` on auto gates | No | The model has no reliable clock. |
| `skip_when` expressions | Partly | The agent evaluates a simple condition on values it has. A missing or unknown key is not caught at load time. |
| `exit_predicate` checked after every phase | Partly | Only for predicates over files and command results. `merge_queue_result` has no producer (see section 4). |
| Escape hatch after 3 consecutive failures | Partly | The agent can count, but only if each attempt is written to a file first. |
| Escape hatch on context limit | No | The model cannot measure its own context use. |
| Checkpoint commit and `RESUME.md` | Yes | Git and file writes are plain actions. Location conflict with `handoff` (section 3). |
| `events.jsonl` phase-result events, bundle status `ESCALATED` / `DONE` | Partly | The agent can append lines. Nothing enforces them, and no later reader checks them. |
| Load-time validation (F6, F7: reject a playbook with no `escape_hatch` or a bad `skip_when` reference) | No | A skill cannot reject a file. A deterministic script can (section 5). |
| Dispatch to `agent_role` or `pack` steps | Partly | The skill can say "read the named pack and apply it as a separate pass with its output schema". A separate context needs a subagent, which is a harness feature. |
| Pinning the playbook version per bundle | No | Needs a persistent bundle record. |

**Inputs the user must supply:** the playbook name (or path), the work description, the route (or the agent asks), the test command or mode, the exit predicate for the autonomous loop, and an answer at each human gate.

**Result of the reading test:** an agent could follow the production-gatekeeper's phase order and stop at the PLAN gate and the VERIFY gate. It could not tell whether a gate was passed in an earlier session, could not enforce the 300-second timeout, and could not detect a context-limit escape. The spec's two built-in playbooks cannot be run to their stated fixtures by a skill alone.

## 3. Overlap

Each row quotes the installed skill's own line (`~/.claude/skills/<name>/SKILL.md`).

| Skill | What it does | What playbook-runner adds or lacks |
|---|---|---|
| `to-spec` | Turns the conversation into a spec. "Do NOT interview the user — just synthesize what you already know." (line 7) | Overlaps the DEFINE phase's spec step. The playbook adds a gate in front of it and an `output_key`. `to-spec` has neither. |
| `to-tickets` | Breaks a plan into tickets. "Iterate until the user approves the breakdown." (line 56) | This is already a human gate of the PLAN shape, without the name. The playbook adds phase order and a predicate. `to-tickets` only publishes tickets. |
| `triage` | State machine of roles. "flag transitions that look unusual and ask before proceeding." (line 45) | Overlaps the idea of a human-checked state change. Triage has fixed roles, not phases, and no exit predicate. |
| `implement` | "Use /tdd ... Once done, use /code-review ... Commit your work to the current branch." (lines 9–15) | Already a fixed BUILD → REVIEW → commit sequence with no gates. The playbook's BUILD and REVIEW steps do the same work. `implement` uses slash commands, which the pack body must not (brief rule). |
| `qa` | Files issues from a user's bug reports. "Do NOT ask the user to review first — just file and share URLs." (line 49) | No real overlap. It has no phases or gates. |
| `wayfinder` | Plans a large effort as tickets. "A HITL ticket only resolves through that live exchange; the agent never stands in for the human's side of it." (line 75). "Stop — charting is one session's work" (line 116). | The closest match to the gate rule in spec §5.2 ("The agent does not decide on behalf of the human at a gate"). Wayfinder already states the rule, with a reason. It is a planning skill, not a runner: no exit predicate, no escape hatch, no auto gates. |
| `handoff` | Writes a handoff doc. "Save to the temporary directory of the user's OS - not the current workspace." (line 8) | Same job as the escape hatch's `RESUME.md` (spec §5.3, "Write RESUME.md to the worktree root"): a document that lets a fresh agent resume. The two put it in different places. Not a direct clash, but the owner should pick one home for resume notes. |
| `grilling` | "The *decisions*, though, are mine — put each one to me and wait for my answer." (line 10). "Do not act on it until I confirm we have reached a shared understanding." (line 12). | Same as the human gate rule. `grilling` has the one-question-at-a-time discipline the gate prompt lacks. |
| `ralph-wiggum:ralph-loop` (plugin command, read at `~/.claude/plugins/cache/claude-code-plugins/ralph-wiggum/1.0.0/commands/ralph-loop.md`) | Re-feeds one prompt until a completion promise is output, with `--max-iterations`. | Overlaps the autonomous loop's exit predicate. It has no phases, gates or escape hatch beyond the iteration cap. Its setup script is harness-specific, so a skill cannot carry it. |

## 4. What blocks it today (spec defects)

These are in the spec, not the format. Each one would stop a build, or a fixture, from passing as written. Fixture results below are predicted from reading, not run.

1. **F8 expects a REVIEW gate that does not exist.** §6.1 has `gate:` on PLAN and VERIFY only (checked with a parse of the playbook YAML). F8's "gate status = failed" cannot happen.
2. **Rule 8 contradicts the schema and F1.** §5.1 rule 8: "A skipped required step is always an error." §4.3: `required: false` means "skipped when skip condition met". F1 skips `plan-architect`, which is `required: true` with `skip_when` (§6.1, line 227). One of these must change.
3. **F5 uses a status the spec does not define.** F5 expects `status: running`. §4.5 defines `passed | gate_waiting | escaped | failed` for phases and `done | skipped` for steps.
4. **`merge_queue_result` has no producer.** The production-gatekeeper's `exit_predicate` (line 190) reads it. No step outputs it, and §7 says merge is "SHIP (implicit)". The predicate cannot be evaluated.
5. **`route` and the other seeded keys are undeclared.** `skip_when: "route == 'simple'"` and the `{{work_bundle.*}}`, `{{hook_path}}`, `{{project.testing.mode}}` placeholders need a seeded-key table. F7 rejects references to keys that are not prior outputs, so under F7 `route` would fail to load.
6. **`agent_role: "analyst"` is not in the enum.** §4.3 lists `worker | architect | pm | ux | developer | reviewer`. §6.1 `define-impact` uses `analyst`.
7. **`decision-artifacts/write` is not a lib operation.** `libs/decision-artifacts/README.md` has `create(kind, title, sections{}, ...)` (line 94). There is no `write`.
8. **Pack independence (packs/README.md, rule 3).** "A pack does not import or require another." The built-in playbooks name four packs (`specialist-agents`, `test-policy`, `two-axis-review`, `anti-slop`) and two libs (`decision-artifacts`, `test-adapters`). The runner itself may be independent. Its built-in playbooks are consumer-side content.
9. **No Coordinator in this repo.** The spec's consumer is UMAS's Coordinator. It is described in `umas/*.md` (64 mentions). No code exists for it here (search of `*.py`, `*.ts`, `*.go`, `*.java` found none). The engine has no home yet.
10. **Built-in playbooks fail the pack YAML subset.** The test-policy parser (`yaml_subset.py`) rejects them. If packs are meant to stay in that subset (its docstring says every data file does), the playbooks need block style.

Other spec items, not blockers: `on_reject: retry` for a human gate is allowed by the schema (§4.4) but the spec never says what a retry of a human decision means (only `halt` is tested, F2).

**Fixtures (F1–F8): not run.** Predicted outcome from reading, with no model involved:

| ID | Skill-only prediction | Blocker |
|---|---|---|
| F1 | Partly passes | Defect 2 |
| F2 | Partly passes | The agent can stop and record ESCALATED in a file, but no other process reads that status |
| F3 | Partly passes | Retry count depends on the agent writing attempts to a file |
| F4 | Fails for the context-limit trigger | Model cannot measure context; counting needs a file |
| F5 | Blocked | Defect 3 |
| F6 | Fails | Load-time validation needs a loader |
| F7 | Fails | Load-time validation needs a loader |
| F8 | Blocked | Defect 1 |

## 5. What the engine adds

What a skill cannot guarantee, and what the engine would:

1. **Enforced gates.** The runner pauses the bundle at a human gate and refuses to advance. A skill relies on the model's compliance. A "Phase: not approved" check made by the engine is a fact, not a prompt.
2. **Durable state.** `events.jsonl`, `playbook_state` and the bundle status survive sessions, machines and handoffs. A skill can write the same files, but nothing reads them back consistently.
3. **Load-time validation (F6, F7).** This is deterministic and needs no model. It can be a stdlib Python script first, before any engine exists. The spec defines it, so it qualifies as a pack script under the brief.
4. **Timeouts and retry counts.** Auto-gate timeouts and "retry once, then escalate" need a clock and a counter outside the model.
5. **Escape hatch that can be trusted.** Failure counts from the runner, not from the model. Context-limit detection needs token counts from a budget source (budget-meter in the libs).
6. **Real dispatch.** `agent_role` and `pack` steps run in their own contexts, with the output schemas enforced by code.
7. **Gate notification.** A runner can notify a human at a gate, even when they are not watching. A skill cannot, because skills carry no harness APIs.
8. **Version pinning** per bundle.

**Recommended first engine piece, no LLM:** a stdlib Python validator for spec §4 and F6/F7, plus an `events.jsonl` writer. That exercises the format without the Coordinator.

## 6. The skill-only form, and why not now

A skill-only `playbook` (format plus gate rules, human gates only, single session) is possible. It would say: read the playbook file, run its phases in order, stop at each `human_approval` gate and wait, write each gate decision and each attempt to a file, and write `RESUME.md` on escape. It would be about 150 lines.

I do not recommend building it now. In a single session, `implement`, `to-tickets`, `grilling` and `wayfinder` already cover the phase order, the human gates and the planning. The new part is the gate-record and `RESUME.md` format. That belongs as a reference the existing skills point at, not as a separate skill. Building it would add a second place for the same rules.

## 7. Built-in playbooks as examples

| Playbook | Can ship as an example? | Condition |
|---|---|---|
| `production-gatekeeper` | Yes | After defects 1–8 are fixed, and marked "example: references packs by name; the runner does not depend on them". It is a worked example of a phase list, and it maps to existing skills. |
| `autonomous-loop` | Yes, with a warning | Its exit predicate and escape hatch need the engine. As an example it says "this is the shape; a skill cannot enforce it", and points to `ralph-loop` for the iterate-until-promise part. |

Put them under `packs/playbook-runner/examples/`, not `playbooks/`, so they are not confused with the runner's contract. The spec's §3 file list needs updating to match.

## 8. Enhancements, if the owner builds the engine

In priority order:

1. Fix defects 1–8 in the spec. Nothing else is worth doing until the fixtures are coherent.
2. Declare the seeded keys (`route`, `work_bundle`, `project`, `hook_path`) in one table.
3. Settle the `RESUME.md` location against `handoff`'s temp-directory rule.
4. Write the stdlib validator for §4 and F6/F7 (section 5, item 3).
5. Decide where the Coordinator lives (defect 9). Until then no fixture beyond F6/F7 can run.
6. Write block-style YAML (defect 10) or extend the subset parser, with a test that reads both built-in playbooks.

## 9. Decisions needed from the owner

1. **Verdict.** Accept `needs engine` (recommended), or build the skill-only form in section 6 now. Recommendation: accept `needs engine`. The single-session value is already in `implement`, `to-tickets` and `grilling`.
2. **Rule 8 vs F1.** Make `required: false` plus `skip_when` the rule for skipped steps (recommended), or keep F1 and drop `required: true` on `plan-architect`. Either way one line changes.
3. **REVIEW gate (F8).** Add an `auto` gate on REVIEW that reads `review_output.gate.recommend` (recommended), or drop F8.
4. **Pack independence.** Treat the built-in playbooks as examples that reference packs by name (recommended), or amend rule 3 for the runner.
5. **Where the Coordinator lives.** No code exists in the repo. The engine waits for this decision.

## 10. Files

- Created: `/Users/tianhonglee/Developer/agentzero-v2-dev/packs/playbook-runner/SKILL-ASSESSMENT.md` (this file).
- Not created: `PACK.md`, `schema/`, `fixtures/`, `scripts/`, `config.yaml`. The verdict is `needs engine`, so the brief forbids building them. I created empty `schema/` and `fixtures/` folders during the work and removed them.
- Not edited: `playbook-runner-spec.md`, `packs/README.md`, `docs/`, other packs.

## 11. Verification

| Check | Result |
|---|---|
| Ruby full-YAML parse of both built-in playbooks | Passed (production-gatekeeper: 6 phases, 2 gates; autonomous-loop: 3 phases, 1 gate) |
| Repo subset parser (`yaml_subset.py`) on both playbooks | Failed at line 6 for both (flow mappings) |
| Cross-references: referenced packs exist | Passed for `specialist-agents`, `two-axis-review`, `router-heuristic`, `test-policy`, `anti-slop`. `specialist-agents` and `two-axis-review` have no `PACK.md`. |
| Cross-references: lib operations | `test-adapters/run` exists. `decision-artifacts/write` does not (`create` does). |
| UMAS and vendor wording in spec body (brief grep) | Expected: in §1, §7, §8, §9, §10. Not a PACK.md, so the brief's grep does not apply. |
| `PACK.md` front matter, path check, schema JSON, fixture YAML, unittest | Not applicable: no build. |
| Cross-platform | Not applicable: no script written. |
