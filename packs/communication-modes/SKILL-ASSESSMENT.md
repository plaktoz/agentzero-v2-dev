# SKILL-ASSESSMENT: communication-modes

Assessed 2026-10-25 under `docs/brief-pack-skills-2026-10-25.md`. Spec read: `communication-modes-spec.md` (Draft v0.1, `pack_version: 0.1.0`). No `PACK.md` is built, because the verdict is not `skill`.

## 1. Verdict

**behaviour.** The two registers (5.1, 5.2), the intensity levels (5.3), the protected-content rule (5.4) and the routing table (5.5) govern text an agent writes while it works. They apply to every status, log and handoff with no one invoking them. That is a standing rule. The one invocable task the spec implies, rewriting existing text into a register, is narrow (section 2).

This confirms row 4 of `docs/assessments/skills-for-claude-mods.md`. One refinement: the routing table is configuration, not reference material, so the right home is a `behaviors/` bundle with the rules as its body and `routing.yaml` as a part. A library doc is not needed.

## 2. Testing the verdict

| Candidate invocable task | Spec support | Would a skill serve it? |
|--------------------------|--------------|-------------------------|
| "Compress this handoff" or "say this status compactly for agent X" | Input 4.1: audience, doc_type, intensity, content, output text | Only narrowly. A user rarely asks for an after-the-fact rewrite, since `handoff` and `claude-handoff` write their own text. A rewrite can drop facts, so it needs the protected-content check (acceptance 2). |
| "Write this escalation for a human" | Routing row "Reports, escalation text to a human: plain" | No. The writer applies routing while writing. That is a rule, not a task. |
| "Which register does this doc type use?" | Acceptance 3: routing is a pure lookup | No model needed. A config lookup, not a task. |
| Check that protected strings survive | Acceptance 2: byte-identical | A deterministic check, like the `compare` mode of anti-slop `lint.py`. It belongs with the rewrite task, not alone. |

Conclusion: the only invocable task is a one-step, user-invoked rewrite. Most of the pack is behaviour. The verdict is not `needs engine`: routing is a pure function of config and no orchestrator is needed.

## 3. Fit evidence

- With the spec in context, an agent can apply the routing table to its own output when the doc type is given. Yes.
- Can it follow the pack from folder files alone? No. `routing.yaml` is listed in section 3 but does not exist. Intensity is not in the prompt (blocker 3). The precedence of audience over doc type is not defined (blocker 1).
- Inputs needed from the user: none for the behaviour. For a rewrite: content, audience or doc type, and intensity (default 2).

## 4. Overlap

Every installed skill read is listed. "No overlap" means the quoted line does not touch register or compression.

| Skill | What it does (quoted line) | What this pack adds or lacks |
|-------|----------------------------|------------------------------|
| `ste-docs` | "Write a document about one subject in controlled plain English (ASD-STE100 style)"; rule 2: "Keep each sentence to 20 words or fewer." | Overlaps the plain register for technical docs (routing row "Technical documentation: plain"). `ste-docs` is stricter. The pack adds the compact register, routing by doc type, and protected content. Not a duplicate. The two compose: plain for tech docs can use the `ste-docs` profile. |
| `handoff` | "Compact the current conversation into a handoff document for another agent to pick up." | Overlap only in the word "compact", which means summarising, not a register. The pack adds a register rule (compact, level 2, for agent handoffs) and protected content. `handoff` lacks a rule to keep paths, commands, IDs, error text and numbers exact. It has only "Redact any sensitive information". |
| `claude-handoff` | "Write a handoff summary of the current conversation so a fresh agent can continue the work." | Same as `handoff`. The summary becomes the agent's prompt, so the protected-content gap matters more here. |
| `edit-article` | "Edit and improve articles by restructuring sections, improving clarity, and tightening prose." | No overlap in register. Its "tightening prose" is a sentence-level edit for human text. It does not conflict with plain. |
| `writing-shape`, `writing-fragments`, `writing-beats` | "Writing, exploit: shape raw material into an article, paragraph by paragraph." | No register rule. A plain register would apply to these articles, but the skills do not decide it. Not an overlap. |
| `qa` | "Keep it concise: a developer should be able to read the issue in 30 seconds" (line 124) | No overlap. Issues are not a routing row in the pack. If they were, plain with complete sentences would fit with concise. |
| `writing-great-skills` | Guidance on predictability and positive phrasing | Not an overlap. Its "Negation" rule applies to how the behaviour rule is written. |
| `teach` | "compressed essence" of lessons | Not an overlap. The word means distilled content. |

Searched, no match: no installed or claude-mods skill named caveman, terse or compression. The searches covered `~/.claude/skills/*/SKILL.md`, `~/.claude/plugins` caches and marketplaces, and `~/Developer/claude-mods/{skills,behaviors,library}`. The source of the caveman and unslop terms is `umas/unified-multi-agent-system-prd.md` section 11.9 and `docs/ANTI-SLOP-EXAMPLES.md` ("Caveman Approach Examples"). Neither is an installed skill.

## 5. Blockers (apply to the behaviour form too)

1. **Audience versus doc type.** Section 4.1 says doc_type is "looked up in routing.yaml when audience is not given", so audience wins. Section 7 says "Routing is by document type, not by the writer's habit." Fixture F4 (status for a project sponsor, a human reader) cannot pass under the table: the only status row, `status_update`, routes compact. The spec needs one rule.
2. **Handoff routing.** Section 5.5 has two handoff rows (agent handoff: compact level 2; handoff summary shown to a human: plain). Section 11 Q1 leaves open whether a human reads the packet. Section 6 has no handoff entry at all.
3. **Intensity has no effect.** Section 5.1 is one prompt for all levels. Levels 1 to 3 differ only in the table at 5.3.
4. **Cross-pack dependency.** `anti_slop: true` in sections 5.5 and 6 requires the anti-slop pack. The packs README (independence rule 3) forbids a pack requiring another, except as a data shape written in both specs. Fix: state the flag as a caller-side field.
5. **Protected-list drift.** Section 5.4 protects names of people, systems and decisions, IDs, branch names, and the object of a decision. Section 6 `protected_patterns` lists six patterns (code_fence, inline_code, path, url, number, quoted) and none of these.
6. **Named files missing.** `routing.yaml` (section 3) does not exist. `schema/message.json` exists only as an example in 4.2. `fixtures/*.yaml` exist only as the table in 8.1. `config.yaml` (packs convention) is absent; section 6 is inline.
7. **Acceptance 4 needs a token counter.** The spec names none. A vendor tokenizer ties the pack to a model, which the independence rules forbid. Options in section 8.
8. **Acceptance 1 needs a second model.** It is not deterministic.

## 6. Unverified figures

- Section 5.3 table, column "Source's stated reduction" (20 to 30, 40 to 50, 60 to 70 percent). Section 5.3 says they are unverified, in the sentence after the table. The table itself carries no marker. Fix: put "(unverified)" in the header.
- Section 8.2 criterion 4: the 70 percent limit. It is a chosen threshold, not a measurement. Its "conservative" note cites the 40 to 50 percent claim. Fix: say it is a chosen limit.
- Section 10 row "Conflicting savings figures noted": says both figures are unverified. Correct.
- Status values such as "50%" and "85%" in sections 4.2 and 8.1 are data, not savings claims.
- Source figures outside this spec: PRD section 11.9 says "40-60%" (`umas/unified-multi-agent-system-prd.md`, line 3608). `docs/ANTI-SLOP-EXAMPLES.md` gives about 30% and 40% for examples 9 and 10, and 20 to 30, 40 to 50 and 60 to 70 for options 1 to 3.
- Check: a grep for 40-60, 40 to 50, 20 to 30, 60 to 70, caveman and unslop over `~/.claude/skills` and `~/Developer/claude-mods/{skills,behaviors,library}` found no matches. No skill body contains these figures. Any future behaviour or skill body must keep them out.

## 7. Part 2: the right form (not built)

Form: a behaviour bundle, `behaviors/communication-modes/behavior.md`, using the manifest format in `~/Developer/claude-mods/behaviors/README.md`. Its body holds prompts 5.1 and 5.2, the protected-content rule and the routing table, and can be injected as a CLAUDE.md fragment. Its `parts` list `routing.yaml` (the routing config). No hook is needed; enforcement by hook would need an engine.

Steps, in order, once the blockers are settled:
1. Settle blockers 1 to 5 in the spec. The spec owner edits the spec, not the pack folder.
2. Write `routing.yaml` from section 6, with the handoff and audience decisions applied.
3. Write `behavior.md` from the prompts. No percentages, no UMAS wording, no slash commands, no model names.
4. Write `fixtures/F1.yaml` to `F7.yaml` from the table in 8.1.
5. Test F5 to F7 and acceptance 3 by reading `routing.yaml`. This needs no model.
6. Only if a hand-invoked rewrite is wanted later: build a separate `PACK.md` skill with a stdlib script that runs the protected-string compare (acceptance 2).

## 8. Fixtures

F1 to F7 exist only in the table at section 8.1. None is built. **Not run.** Expected results are in the table; F5 to F7 are deterministic once `routing.yaml` exists, F3 is a string compare, F1 criterion 4 needs a counter, and F2 needs a model.

## 9. Decisions for the owner

(a) **Verdict.** Recommend `behaviour`. Alternative: a hand-invoked rewrite `skill`, built only if you want to request rewrites on demand.

(b) **Audience versus doc type.** Recommend doc type wins for routing, and audience applies only when doc type is missing. Then F4 needs a `status_update_human` row. Alternative: audience wins, and F4 passes with `audience: human`.

(c) **Handoff register.** Recommend compact level 2 for agent handoffs, and plain for the summary shown to a human. Both rows already exist in section 5.5; add the config entry.

(d) **Token counter for acceptance 4.** Recommend word count as a stated proxy, labelled as a proxy. Alternative: the consumer supplies a counter.

(e) **Installed handoff skills.** Recommend adding one line to `handoff` and `claude-handoff` to keep paths, commands, IDs, error text and numbers exact. Those skills are outside this pack's scope and outside the repo, so this is the owner's call.

## 10. Verification

- `PACK.md`: not built (verdict `behaviour`). Front matter and forbidden-word checks do not apply.
- Schema, fixtures and scripts: none in this folder. Nothing to validate.
- Figures: checked as in section 6.
- `agent-ignore`: its contents were not opened. A `find` for `ANTI-SLOP-EXAMPLES*` walked directory names under `/`, which may have listed entries in an `agent-ignore` folder. No contents were read.
- No files changed other than this one. Nothing committed.
