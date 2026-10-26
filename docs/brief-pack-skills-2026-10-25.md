# Brief: assess one content pack as an agent skill, and enhance it into one if it fits

Working directory: `/Users/tianhonglee/Developer/agentzero-v2-dev`. Do not read any folder named `agent-ignore`.

## Context (read before you start)
- The pack spec: `packs/<name>/<name>-spec.md` (the design record).
- `packs/README.md`: what a pack is, the built form (`<pack>-spec.md`, `PACK.md`, `schema/`, `fixtures/`, `config.yaml`), the independence rules.
- `docs/assessments/skills-for-claude-mods.md`: an earlier verdict per pack. Your job updates and deepens that verdict for your pack only. Do not edit that file; the coordinator merges the results.
- Three packs are already built and are the reference for the built form: `packs/minimalism-ladder/`, `packs/test-policy/`, `packs/anti-slop/`. Read one `PACK.md` and its fixtures before you write.
- Skill format rules (decided by the owner, 2026-10-25): `PACK.md` carries the `SKILL.md` front matter (`name`, `description`), and the body has **no** slash commands, **no** harness APIs, **no** model or vendor names, **no** UMAS wording, **no** "Known consumers" text, **no** unverified percentage figures. It must work in any agent harness that loads skill files (Claude Code, Codex, Copilot). Copying `PACK.md` to `SKILL.md` must be all it takes to install it.
- Quality bar for a skill: read `~/.claude/skills/writing-great-skills/SKILL.md` (and the files it points to) and apply it: a `description` that says what the skill does and when to use it, a body an agent can follow step by step, a clear "not this skill" boundary, and an output contract.
- Installed skills that may overlap (all under `~/.claude/skills/<name>/SKILL.md`): code-review, grilling, grill-me, grill-with-docs, batch-grill-me, tdd, edit-article, writing-beats, writing-fragments, writing-shape, writing-great-skills, to-spec, ubiquitous-language, domain-modeling, handoff, claude-handoff, triage, to-tickets, implement, qa, research, wayfinder. Read the ones that overlap with your pack before you judge overlap. Do not guess their content.
- Scripts: Python, standard library only, `encoding="utf-8"`, `pathlib`, no POSIX-only calls. Run Python with `python3 -I`. Tests with `python3 -I -m unittest`.

## Part 1. Assess (always)
Write the assessment as `packs/<name>/SKILL-ASSESSMENT.md` with:
1. **Verdict:** one of `skill` (build or enhance as a skill), `agents` (better as subagent definitions), `behaviour` (a standing style rule, not a skill someone invokes), `needs engine` (needs an orchestrator; not a standalone skill), `duplicate` (an installed skill already does it). One line of reason.
2. **Fit evidence:** what the skill would do in one session with no other system around it. Can an agent follow it with only the files in the folder? What inputs does it need from the user?
3. **Overlap:** for each overlapping installed skill you read, a row: skill, what it does, what this pack adds or lacks. Quote the line you base it on.
4. **What blocks it as a skill today:** UMAS wording, harness-specific wording, missing schema, missing fixtures, unverified claims, a dependency on another pack or lib.
5. **Enhancements:** the changes that would make it a good skill, in priority order.
6. **Decision needed from the owner** (if any), with options and a recommendation.

## Part 2. Enhance (only if the verdict is `skill`, or `duplicate` where the pack adds something the installed skill lacks)
- If `PACK.md` does not exist: build the pack's skill form, following the three built packs: `PACK.md` (front matter + the prompt, rules and output record taken from the spec), `schema/<output>.json` for the output record, `fixtures/F*.yaml` from the spec's fixture table, `config.yaml` from the spec's configuration section. Add a script only if the spec defines a deterministic check, and then add its unittest.
- If `PACK.md` exists (anti-slop, minimalism-ladder, test-policy): do not rewrite it. Improve only what the quality bar finds weak (the `description`, a missing step, a missing boundary, an unclear output contract), and list every change in the assessment file under "Changes made". Do not change rules or fixture expectations: those are owner decisions recorded in `docs/tasks-skills-claude-mods-2026-10-25.md`.
- If the verdict is `duplicate`: do not build the whole pack. Write in the assessment exactly what the pack adds, in a form that could be offered to the installed skill. Build `PACK.md` only if what it adds is enough to stand alone, and say why.
- If the verdict is `agents`, `behaviour` or `needs engine`: do not build `PACK.md`. In the assessment, describe the right form (for example an `agents/<role>.md` per role, or a `behaviors/` rule file) and the steps to build it. Do not write it.
- Do not run model fixtures against a model. List the fixtures and mark them "not run".

## Verify before you report
- `PACK.md` front matter has exactly `name` and `description`, `name` equals the folder name.
- `grep -i -E "umas|claude code|codex|copilot|gemini|openai|anthropic|/[a-z-]+ "` over `PACK.md` finds nothing (adjust if a slash appears in a path; report what you excluded).
- Every file path named in `PACK.md` exists in the folder.
- Every schema is valid JSON (`python3 -I -c "import json,sys; json.load(open(sys.argv[1],encoding='utf-8'))" <file>`), and every fixture is valid YAML by reading (no PyYAML in the standard library; if you add a script, follow `packs/test-policy/scripts/yaml_subset.py`).
- Any script you add passes its unittest.
- Cross-platform: read every script for `/` joins, `HOME` without `USERPROFILE`, POSIX-only calls, missing `encoding="utf-8"`. Windows is "verified by reading".

## Scope
Edit only files in `packs/<name>/`. Do not edit `packs/README.md`, `<name>-spec.md`, `docs/`, other packs, or anything in `~/.claude` or `~/Developer/claude-mods`. Do not commit.

## Report back (under 250 words)
- Verdict and reason.
- Files created or changed (paths).
- Overlap findings in one line per installed skill.
- Verification results (what passed, what is "verified by reading").
- Decisions needed from the owner, with your recommendation.
