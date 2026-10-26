# SKILL-ASSESSMENT: anti-slop

> Date 2026-10-25 · Pack version 0.1.0 · Brief: `docs/brief-pack-skills-2026-10-25.md` · Owner decisions: `docs/tasks-skills-claude-mods-2026-10-25.md`

## 1. Verdict

**`skill`.** Enhance the built form. The review is one bounded procedure over one finished text, it needs no orchestrator, and it runs from the folder's files. Overlap with installed skills is partial.

## 2. Fit evidence

- **One session, no other system.** The agent gets the content, `kind` (`prose`, `prd`, `docs` or `code`) and `language` for code. It reads `PACK.md` and `phrases.yaml`, runs the eight-step procedure, and returns one JSON record. `scripts/lint.py` is optional: each step that uses it says "when a script is available" and has a model-only check.
- **Inputs from the user.** The text, its kind, and its language for code. Nothing else.
- **Gap.** `PACK.md` points at `phrases.yaml` for the phrase list and does not inline it. An agent with `PACK.md` alone cannot run step 3. The install must copy the side files (section 4, item 1).
- **Output.** `PACK.md` describes the record. Validating it needs `schema/review-output.json`.

## 3. Overlap

Each row quotes the installed skill's own text. Files read: `~/.claude/skills/<name>/SKILL.md` for all, plus `writing-great-skills/GLOSSARY.md`, and `code-review`'s smell-baseline section (for code-review and ubiquitous-language, the quoted lines were checked in the file).

| Skill | What it does (quoted) | What this pack adds or lacks |
|-------|-----------------------|------------------------------|
| `edit-article` | "Rewrite the section to improve clarity, coherence, and flow. Use maximum 240 characters per paragraph." It first splits the article into sections and confirms the order with the user. | **Partial overlap.** Both tighten prose. This pack adds a per-change record with category and reason, a `flags` channel for facts it cannot supply, and code kinds. It lacks section reordering and the 240-character limit. `PACK.md` "Not this skill" points to an article-editing skill for restructuring. |
| `writing-shape` | "Then run a shaping session that produces a separate article document. This is **exploit**." | **No overlap.** It drafts an article from a pile. This pack runs after drafting. |
| `writing-beats` | "This is **exploit**: the exploring is done, the pile is fixed." Writes one beat at a time. | **No overlap.** Beat-by-beat drafting with grounding. This pack has no drafting step. |
| `writing-fragments` | "This is pure **explore**: widen the space of what could be written without committing to structure." | **No overlap.** An earlier stage. |
| `writing-great-skills` | "A skill exists to wrangle determinism out of a stochastic system." Sets the quality bar: front-loaded trigger description, steps with completion criteria, a boundary. | **No content overlap.** It is the bar `PACK.md` was checked against (section 5). |
| `ubiquitous-language` | "When multiple words exist for the same concept, pick the best one and list the others as aliases to avoid." | **Overlaps rule 9 and fixture F8.** That skill extracts a glossary from a conversation and can record aliases. This pack picks one term inside a finished text and cannot record aliases. The F8 question is a glossary question. |
| `code-review` (Standards axis, smell baseline) | "**Speculative Generality** — abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it." Also "**Middle Man** — … cut it." | **Partial overlap** with code rules 1 and 5. `code-review` reports smells on a diff as judgement calls and applies repo standards first. This pack edits a finished file and does not read repo standards. |

## 4. What blocks it as a skill today

1. **Side files.** `PACK.md` names `phrases.yaml`, `config.yaml`, `schema/review-output.json`, `scripts/lint.py` and `fixtures/`. The brief says copying `PACK.md` to `SKILL.md` must be all it takes. It is not, unless the side files are copied with it. The tasks doc (task 4) already copies them. Owner decision 2 below.
2. **Failing fixtures.** F1 and F8 fail in `fixtures/RESULTS.md`. Criterion 2 fails on F1 (the name "AI" dropped with a deleted sentence). F3 meets criteria 4 and 5 in the 2026-10-25 re-review (runs 3 to 5, one sample; see `fixtures/RESULTS.md`, "F3 re-review"). The F3 unit test still fails, because `outputs/F3.revised.md` holds run 2's text.
3. **Judge.** The author judged every output, one run per fixture. It is not independent.
4. **Wording.** `PACK.md` has no UMAS, harness or vendor wording (the grep in the brief finds nothing). The "Known consumers" table is in the spec only. `PACK.md` has no unverified percentage figures; the targets in spec 5.9 are not copied.
5. **Licence.** F3 is seeded from `docs/ANTI-SLOP-EXAMPLES.md`, which states no licence. `fixtures/PROVENANCE.md` records the owner's approval (2026-10-25) and says the licence must be confirmed before publishing outside the repo.
6. **Platform.** Windows: verified by reading only (section 8).

## 5. Enhancements, in priority order

| # | Change | Status |
|---|--------|--------|
| 1 | Add a step-by-step procedure with a check per step, drawn from the existing rules | Done (`PACK.md` "Procedure") |
| 2 | Rewrite the description to front-load the subject and give the trigger ("Use when a finished draft, document or code change needs de-slopping, after the content is complete") | Done |
| 3 | Extend "Not this skill" to name the draft, article-restructure and code-review boundaries, in kind (no tool names) | Done |
| 4 | Give exact script commands and exit-code meaning | Done |
| 5 | Copy side files with `PACK.md` at install | Pending: tasks doc task 4 |
| 6 | Independent judge for the fixtures | Not done. Needs a person or a separate run |
| 7 | Settle the rule for a whole sentence with no fact (F1) and for aliased terms (F8) | Owner decision 1 |

## 6. Changes made

All in `packs/anti-slop/PACK.md`:

- **Front matter, `description`.** Rewritten (was "A second review pass that removes generic AI patterns (stock vocabulary, vague claims, filler, premature abstraction, redundant comments) from finished prose, docs, PRDs or code without changing facts. Use it after the content is complete and correct, not while drafting."). Name unchanged; only `name` and `description` keys.
- **"Not this skill".** Two bullets added: no restructuring or argument-tightening (the article-editing case), and no drafting from notes or fragments. One bullet added: not a code review (no bugs, security or spec gaps).
- **"Procedure" section (new), eight steps.** Set inputs; read and list facts; resolve each `phrases.yaml` hit by writing rule 3; walk each sentence against the slop table and the kind's rules; record each change; check facts (`compare`); check the phrase list again; write the output record (`validate`). Each step ends in a check. Step 3 applies the existing writing rule 3 to phrase hits, which is what the owner's 2026-10-25 decision says.
- **"Optional deterministic checks".** Added the `python3`/`py -3` launcher note, the exit-code meaning, and three command lines.

Not changed: the reviewer prompt; the writing rules 1 to 9 and code rules 1 to 5; `behaviour_change` wording; the "What counts as slop" table; the variants table; the output record and its fields; the limits; `phrases.yaml`; `schema/`; `config.yaml`; `scripts/`; `fixtures/` (inputs and expectations). Rule text and the variants table were compared against the pre-edit copy and are identical.

## 7. Fixtures

**Not run in this pass** (no model runs, per the brief). Last recorded result from `fixtures/RESULTS.md` (second run, 2026-10-25, and the F3 re-review of the same day):

| ID | Last result | Note for this pass |
|----|-------------|--------------------|
| F1 | Fail | Not run. See section 8 |
| F2 | Pass | Not run |
| F3 | Pass on criteria 4 and 5 (re-review, runs 3 to 5, one sample) | Not run in this pass. See `fixtures/RESULTS.md` |
| F4 | Pass | Not run |
| F5 | Pass | Not run. Expectation as written |
| F6 | Pass | Not run. Expectation as written |
| F7 | Pass | Not run |
| F8 | Fail | Not run. Input unchanged |
| F9 | Pass | Not run |
| F10 | Pass | Not run |

## 8. Effect of the skill form on F1, F3 and F8

- **F3 (criterion 4, "at scale").** Step 3 says each phrase hit gets writing rule 3, and rule 3 says to remove a phrase when the sentence keeps its facts. The 2026-10-25 re-review ran this step three times (runs 3 to 5). Each removed "at scale", and each second pass made no change, so criteria 4 and 5 pass on one sample. The judge was a model, not a person (`fixtures/RESULTS.md`, "F3 re-review"). Run 2 had flagged "at scale" instead.
- **F1 (one concrete sentence).** No change in effect. The sentence "Our framework is a set of coordination ideas" holds no fact, so rule 3 says flag it. The fixture expects it gone. The new procedure follows rule 3 as written, so this is a rule question (owner decision 1).
- **F8 (one term).** No change in effect. Rule 9 already says to keep the most-used term. The reviewer declined because the last sentence declares the four terms one process. The procedure does not resolve that (owner decision 1).
- **Criterion 2 on F1 (name "AI").** Step 6 keeps the strict wording: dropped names must be restored. No change.

## 9. Owner decisions

1. **F1 and F8 rules.** Two options each.
   - **F1.** The sentence "Our framework is a set of coordination ideas" is a whole sentence with no fact in it. Removing it keeps every fact in the paragraph (the 20 to 30 agents and the git worktree sentence remain). Rule 3 as written covers phrases, and step 3 applies it to phrases only, so the reviewer flagged the sentence instead. (a) Keep rule 3 as written. F1 stays failing, and the output follows the rule. (b) Extend rule 3: a whole sentence that states no fact, and whose removal keeps every fact in its paragraph, is removed and listed as a change, not flagged. **Recommendation: (b).** It is the only option that meets the F1 expectation without changing the expectation. It adds a rule, so it needs your approval; it does not reverse your 2026-10-25 decision on phrases.
   - **F8.** (a) Keep F8 failing as the honest result. (b) Rewrite the F8 input to drop the aliasing sentence. The input was already rewritten five times after seeing outputs, so another rewrite would tune the fixture to the output. (c) Add a rule: where the text says several terms are one thing, replace all of them with the term rule 9 keeps, and rewrite the declaring sentence to say it once. **Recommendation: (c)**, and do not change the F8 input.
2. **Side files at install.** The brief says `PACK.md` alone is the install. (a) Copy the side files with it, as the tasks doc says. (b) Inline the phrase list and the schema into `PACK.md`. **Recommendation: (a)**. Option (b) lengthens `PACK.md` and duplicates the phrase list.
3. **Independent judge.** Run the fixtures with a reviewer that is not the author. **Recommendation:** do this once decision 1 is settled, so the rerun tests one rule set.

## 10. Verification

- Front matter: exactly `name` and `description`; `name: anti-slop` equals the folder name. **Pass.**
- Banned-word grep (`umas|claude code|codex|copilot|gemini|openai|anthropic|/[a-z-]+ `) over `PACK.md`: no hits. Nothing excluded; the slash pattern matched no path in `PACK.md`. **Pass.**
- Every path named in `PACK.md` exists (`schema/review-output.json`, `phrases.yaml`, `config.yaml`, `scripts/lint.py`, `fixtures/`). **Pass.**
- `schema/review-output.json` parses as JSON with `python3 -I`. **Pass.**
- Fixtures are valid YAML by reading, in the subset `lint.py` reads (`load_fixture`). Not re-read this pass; unchanged.
- `python3 -I -m unittest discover -s scripts` after the F3 re-review: 32 tests, 1 failure, `test_revised_f1_to_f4_have_zero_phrase_hits` on F3, because `outputs/F3.revised.md` still holds run 2's text. The criterion 2 test for F1 now passes, but `fixtures/RESULTS.md` still records F1 as failing criterion 2. Reconciling the two is an open item. macOS.
- Cross-platform, by reading only: `lint.py` and `test_lint.py` open every text file with `encoding="utf-8"`, use `pathlib`, use no `HOME`, no subprocess and no POSIX-only calls. Tests use `tempfile`. Windows: verified by reading only. Other Python versions were not run this pass.
- `__pycache__` removed after each run.

## Files

- Changed: `packs/anti-slop/PACK.md`.
- Created: `packs/anti-slop/SKILL-ASSESSMENT.md` (this file).
- Not changed: `anti-slop-spec.md`, `packs/README.md`, `docs/`, other packs, `~/.claude`.
- Not committed.
