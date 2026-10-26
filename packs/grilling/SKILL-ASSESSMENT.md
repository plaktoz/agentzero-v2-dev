# grilling: skill assessment

> Date: 2026-10-25 · Scope: this pack only · Updates the row for `grilling` in `docs/assessments/skills-for-claude-mods.md`
> Read for this assessment: `grilling-spec.md`; installed `grilling`, `grill-me`, `grill-with-docs`, `batch-grill-me` (each `SKILL.md` and `agents/openai.yaml`); `domain-modeling/SKILL.md` (which `grill-with-docs` points to); `writing-great-skills/SKILL.md`; the built `minimalism-ladder` and `anti-slop` packs as the format reference.

## 1. Verdict

**`duplicate`.** The installed `grilling` already does the interview. What the pack adds is one real piece (the alignment summary) and one real option (a cap on the session). The skip rule and the timeout have nothing to act on in a standalone skill. What to offer is in section 7. I did not build `PACK.md`.

## 2. Fit evidence

What the pack would do in one session with no other system around it: question a request, then print a summary for the person to confirm.

- Can an agent follow it with only the folder? Mostly yes for the protocol and the summary. No for the trigger table (`origin: agent | escalation`), the `timeout_seconds` / `on_timeout` behaviour and the `transcript` input. Those need a caller that tracks who sent the request, a clock and stored turns. A harness that loads a skill file gives none of these.
- Inputs needed from the user: the request, and an answer per question. Nothing else. `context`, `limits` and `transcript` can be dropped or become "what you already read" and "the cap".
- So the standalone core is: three-per-turn questions with a default each, a ten-question cap, a stop rule, a skip when the request is precise, and the summary.

## 3. Overlap

One row per installed skill. Quotes are from the files I read.

| Skill | What it does | What the pack adds or lacks |
|-------|--------------|-----------------------------|
| `grilling` | "Interview me relentlessly about every aspect of this until we reach a shared understanding. Walk down each branch of the decision tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer." One question at a time: "Asking multiple questions at once is bewildering." Facts are looked up, "The *decisions*, though, are mine". "Do not act on it until I confirm we have reached a shared understanding." | **Adds:** a cap per turn and per session, a stop rule, a skip rule, a written summary. **Lacks:** the dependency walk ("resolving dependencies between decisions one-by-one"); the pack only says "most consequential first". **Conflicts:** (a) one question versus three per turn; (b) the pack says "Do not ask about implementation choices that are yours to make", the installed skill says every decision is the user's; (c) "relentless until shared understanding" versus "the fewest questions". |
| `grill-me` | Body is only "Run a `/grilling` session." User-invoked only (`disable-model-invocation: true`). | Nothing to compare: a wrapper. It shows how the installed set is used: the person types it when they want to be grilled. |
| `grill-with-docs` | "Run a `/grilling` session, using the `/domain-modeling` skill." The domain-modeling skill updates `CONTEXT.md` and offers ADRs "when all three are true: hard to reverse, surprising without context, the result of a real trade-off". | Different output. This one leaves lasting docs (glossary, decisions). The pack's summary is a short note that the person confirms before work starts, not a lasting doc. No overlap, and the pack must not copy the glossary or ADR role. |
| `batch-grill-me` | "Ask the whole frontier in one round: number each question and give your recommended answer." Frontier = "every decision whose prerequisites are already settled". Done "when the frontier is empty". Facts are fetched by a sub-agent. | **Closest to the pack on batching:** both ask several questions per turn. Installed rule is better: it limits a round to questions that do not depend on each other. The pack's three-per-turn has no such rule and could put dependent questions together. **Adds:** a cap on rounds and questions, which this skill lacks (it ends only when the frontier is empty). |

### Comparison of the three named parts

| Part | Installed set | Pack | Real difference? |
|------|---------------|------|------------------|
| **Bounded questioning protocol** | No bound. `grilling`: one at a time, until the person confirms. `batch-grill-me`: rounds until the frontier is empty. Each question has a recommended answer. | At most 3 per turn, at most `max_questions` (10) per session, each with a one-clause reason and a default. Stops on: no question would change what gets built, the cap, or the person says proceed. Unasked unknowns become assumptions. | **Yes, in design.** It is a limit and a stop rule, which the installed set deliberately lacks. It is the opposite aim ("fewest questions" versus "relentless"), so it fits as a mode of the installed skill, not as a second skill. A recommended answer and a default are nearly the same thing; only the use differs (the default is assumed if unanswered). |
| **Skip rule** | None. `grilling` is model-invoked (no `disable-model-invocation`, and its description lists "grill" trigger phrases), so the model can start it. `grill-me`, `grill-with-docs` and `batch-grill-me` are user-invoked only. None of them has a skip rule. | Skip when `origin` is `agent`; skip when the request is already precise. | **Not in a standalone skill.** The `origin` half needs a caller that knows who sent the request. The "precise request" half matters only if the skill runs on every request automatically, and the spec's own open question 1 doubts that. When the person asks to be grilled, a skip is the wrong answer. As a line in the offer: "If the person did not ask to be grilled and the request is already precise, say so and proceed." Only useful for a model-invoked variant. |
| **Alignment-summary output** | None. The only closing step is "Do not act on it until I confirm we have reached a shared understanding." No artifact. | Goal, checkable success criteria, constraints, edge cases, out of scope, assumptions (each tied to the question it replaced), open risks, "Please confirm or correct." Has a JSON schema in the spec. | **Yes.** This is the one thing the installed set has no equivalent for. It makes "shared understanding" something the person can check, and it records what was assumed rather than asked. |

## 4. What blocks it as a skill today

- Nothing is built: no `PACK.md`, `schema/`, `fixtures/` or `config.yaml`. Only the spec exists.
- It needs an orchestrator for part of its contract: `origin`, `escalation`, `timeout_seconds`, `on_timeout`, `transcript`, `confirmed_by_user`. The consumer "shows the summary and records the confirmation".
- Wording: section 9 (UMAS mapping) and section 10 must stay in the spec. Section 5.6 points to the anti-slop pack (`Apply anti-slop wording rules`), which is a dependency on another pack, and a skill body cannot name it.
- The trigger would collide with the installed `grilling` description ("any 'grill' trigger phrases"). Two model-invoked skills for one phrase make the choice between them unpredictable.
- It restates what the installed skill already says (facts are looked up, not asked), which `writing-great-skills` calls duplication.
- The spec's deviations (skip when precise, defaults, three per turn, summary schema) are the author's proposals, not tested. Acceptance criteria 1 to 6 have not been run.

## 5. Enhancements, if the owner wants a standalone skill anyway (priority order)

1. Drop `origin`, `escalation`, timeout and `transcript`. Keep the cap, the stop rule and the summary.
2. Add the installed rule that a round holds only questions that do not depend on each other.
3. Decide who owns implementation choices (the pack: the agent; the installed skill: the person). Pick one.
4. Rename and give a distinct leading word so the description does not match "grill" (for example, an "alignment check" before work starts).
5. Add `schema/summary.json`, fixtures F1, F3, F4, F7 from the spec (F2, F8, F9 need the orchestrator and are cut), and `config.yaml` with `max_questions`, `max_questions_per_turn`, `require_confirmation`. No script is needed: the spec defines no deterministic check.

## 6. Decision needed from the owner

| Option | What changes | Recommendation |
|--------|--------------|----------------|
| A. Offer the summary step and the cap to the installed `grilling`; keep the pack as a spec only | One small change to a file outside this repo. Nothing new to maintain. | **Recommended.** What the pack adds is two additions to a twelve-line skill. |
| B. Build a separate standalone skill ("alignment check") | A new model-invoked skill that overlaps `grilling` in what it asks. Needs fixtures, schema and a judge. | Not recommended. Collides with `grilling` triggers; its extra value is the summary, which A delivers. |
| C. Drop the pack from the claude-mods list and keep the spec for UMAS | No change to the installed set. | Acceptable if the owner does not want to touch `grilling`. The summary is then only in the spec. |

Also answer: should the "precise request" skip exist at all? Spec open question 1 leaves it open. My answer: only for an automatic variant, not for the installed on-demand skill.

## 7. What would be offered to the installed `grilling` skill

Two additions, in the installed skill's own voice. They contain no slash commands, harness APIs, vendor names or UMAS wording, so they work in any harness. Not applied by me: the brief forbids editing `~/.claude`.

**Addition 1: closing summary.** Insert before the last line ("Do not act on it until I confirm..."):

```text
When the questions are done, write a short summary and ask me to confirm or
correct it:

Goal:             <one sentence>
Success criteria: <checkable, numbered>
Constraints:      <list>
Edge cases:       <list>
Out of scope:     <list>
Assumptions:      <each with the question it replaced>
Open risks:       <list>

Every question I did not answer, and every question you did not ask, appears
under Assumptions with what you assumed. Do not act until I confirm.
```

**Addition 2: optional cap.** Add after the first paragraph:

```text
If I ask for a short session, ask at most ten questions in total, most
consequential first, and stop earlier when no remaining question would change
what gets built. Give a default with each question: what you will assume if I
do not answer. Unasked unknowns become assumptions in the summary.
```

Left out on purpose: three questions per turn (it conflicts with "one at a time"; `batch-grill-me` already covers batching and does it better), the `origin` trigger table, the timeout, and the "implementation choices are yours" rule (it reverses the installed rule that decisions are the user's).

## 8. Fixtures

Not built and not run. If the offer is accepted, these spec fixtures carry over as checks on the installed skill: F1 (at most the cap, each question has a default), F4 (a question the supplied context answers is not asked), F7 (eleven unknowns: stops at the cap, the rest are assumptions). F2, F3 (needs the automatic variant), F8 and F9 are cut with the orchestrator. Status: not run.

## 9. Verification

- No `PACK.md`, schema, fixture, config or script was created, so the front-matter, wording, path, JSON, YAML and cross-platform checks do not apply.
- Files changed: only this file. No other pack, spec, doc or `~/.claude` file was edited. No commit.
