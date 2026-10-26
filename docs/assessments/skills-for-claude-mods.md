# Skill-related items: can they be listed in claude-mods?

> **Date:** 2026-10-25 · **Target:** `plaktoz/claude-mods`, checked against the local clone at `~/Developer/claude-mods` (not the GitHub copy).

## What claude-mods takes

| Fact | Source |
|------|--------|
| A skill is a folder `skills/<name>/SKILL.md` with `name` and `description` front matter | `skills/ste-docs/SKILL.md` |
| `scripts/install-skills.sh` symlinks each skill into `~/.claude/skills/` | `README.md` |
| Agents go in `agents/`, hooks in `hooks/`, plugins in `mods/` | `README.md` |
| Each part is self-contained and single-purpose; code must be cross-platform; READMEs stay in sync | `CLAUDE.md` |
| Only one skill is listed today (`ste-docs`); the repo calls itself an "early scaffold" | `skills/`, `README.md` |

## The items

No pack is built. Each is a spec (`PACK.md` plus schema, fixtures and config is planned, not present), and `umas/TECHNICAL-DESIGN-SPEC.md` Appendix A.2.2 says none has been turned into a `SKILL.md` or run against a model. So no item can be listed today. The table shows what each would need.

| # | Item | Form in claude-mods | Fit | Overlap with skills already installed on this machine | Verdict |
|---|------|---------------------|-----|-------------------------------------------------------|---------|
| 1 | `minimalism-ladder` | Skill | Single purpose: six questions before writing code. Prompt only; an optional script can check that cited evidence paths exist. | None found | **List after build** |
| 2 | `anti-slop` | Skill | Two-pass review plus a forbidden-phrase linter. The linter is a script, so it must pass the cross-platform checks in `CLAUDE.md`. | Partial: `edit-article` and the `writing-*` skills (not read) | **List after build**, after reading those skills |
| 3 | `test-policy` | Skill | Selective versus strict testing, with a deterministic pre-filter script (`risky-patterns.yaml`). | Partial: `tdd` covers test-first work, not "which changes need tests" | **List after build** |
| 4 | `communication-modes` | Behavior or library doc | A style rule (compact versus plain), not a task someone invokes. | None found | **Better as `behaviors/` or `library/`**, not a skill |
| 5 | `two-axis-review` | Skill | Standards and Spec passes, finding schema, severity gate. | **Duplicate:** the installed `code-review` already reviews on Standards and Spec axes | **Do not list as a separate skill.** Offer the finding schema and severity gate to `code-review`, or list only if it adds something the installed one lacks |
| 6 | `grilling` | Skill | Bounded questioning, alignment summary, skip rule. | **Duplicate:** installed `grilling`, `grill-me`, `grill-with-docs`, `batch-grill-me` | **Do not list** unless the bounded protocol and the skip rule are shown to be different |
| 7 | `specialist-agents` | `agents/` | Five role prompts (Analyst, PM, UX, Architect, Developer) map to subagent definitions, not skills. | None found | **List as agents after build** |
| 8 | `router-heuristic` | Needs an engine | Needs a deterministic scorer and a caller that acts on the route. | None found | **Not now.** Does not stand alone without an orchestrator |
| 9 | `playbook-runner` | Needs an engine | Defines a contract that a Coordinator executes. | None found | **Not now.** A skill cannot run phase gates by itself |
| 10 | `decision-artifacts` (lib) | Skill | PRFAQ, ADR, Spec and GLOSSARY templates; `libs/README.md` says it packages easily as a skill. | Partial: `to-spec`, `ubiquitous-language`, `domain-modeling` | **Candidate.** Compare with those three first |
| 11 | `kc-axi` (lib) | Not a skill | A CLI. At most a skill file that teaches an agent to call it; `libs/README.md` open question 4 leaves that undecided. | None | **Not now** |

## Blockers that apply to every item

1. **Nothing is built or tested.** The fixtures and acceptance criteria exist on paper only. Listing an untested skill in a repo that lists `ste-docs` would lower its bar.
2. **Two skill formats.** `agent-platform` section 5.8 defines a harness-neutral `SKILL.md` that must not use Claude Code slash commands or harness APIs. claude-mods skills are Claude Code skills with `name` and `description` front matter. A pack would need to meet both, or the difference needs a decision.
3. **UMAS wording.** Each pack ends with a "Known consumers" table that maps to UMAS concepts. That table stays in the spec; it must not be copied into the skill.
4. **Provenance.** I did not check whether any pack text came from the third-party skill set that provides the installed `code-review`, `grilling` and `tdd`. If it did, listing it needs attribution and a licence check.
5. **Unverified claims.** Percent-saving and accuracy figures in `communication-modes` and `anti-slop` came from the source documents and are marked unverified in the specs. Remove or test them before publishing.

## Recommended order

1. `minimalism-ladder`. No overlap, prompt only, smallest build.
2. `test-policy`. Adds a script, so it also exercises the cross-platform rules.
3. `anti-slop`, after reading the installed writing skills.
4. `specialist-agents` as `agents/`.
5. Decide on `decision-artifacts` after comparing it with the three installed skills.

Decisions for the user: (a) whether `two-axis-review` and `grilling` should be dropped as duplicates or reshaped as improvements; (b) which `SKILL.md` format to build; (c) whether packs are built in this repo or directly in claude-mods.
