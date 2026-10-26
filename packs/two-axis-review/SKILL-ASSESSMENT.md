# two-axis-review: skill assessment

Date: 2026-10-25. Pack version 0.1.0. Assessed against `two-axis-review-spec.md` (design record), `~/.claude/skills/code-review/SKILL.md` and `agents/openai.yaml` (installed), and the reading rules in `~/.claude/skills/writing-great-skills/` (SKILL.md and GLOSSARY.md).

## 1. Verdict

**`duplicate`.** The installed `code-review` skill already runs the Standards and Spec axes as parallel, independent reviews with the same brief structure. The pack adds a finding schema, a severity scale, a gate, a production checklist and a few checks that `code-review` lacks. Those additions belong in `code-review`, not in a second review skill. Two parts of the pack conflict with `code-review`'s design and must not be offered (section 4).

No `PACK.md` is built. The additions are not enough to stand alone (section 5).

## 2. Fit evidence

- The pack's prompts (5.1, 5.2, 5.4) are complete. An agent can follow them with only the pack folder, given a diff and an intent string. Fit as a standalone skill is good.
- Inputs: `diff` and `intent` are required. `conventions`, `test_results` and `risk_flags` are optional (spec 4.1).
- The blocker is overlap, not fit. A `PACK.md` would carry the same review triggers as `code-review`. `writing-great-skills/SKILL.md` says: "Synonyms that rename a single branch are **duplication**" and a second skill would duplicate the review branch in context load. The agent would then have two review skills competing for the same request, which lowers predictability.

## 3. Overlap

| Installed skill | What it does | What the pack adds or lacks |
|---|---|---|
| `code-review` (`~/.claude/skills/code-review/SKILL.md`) | Reviews `git diff <fixed-point>...HEAD` on two axes, "Standards — does the code conform to this repo's documented coding standards?" and "Spec — does the code faithfully implement the originating issue / PRD / spec?" (lines 8-9). Runs both as parallel sub-agents (line 11). Adds a 12-smell baseline to Standards (lines 38-56). Aggregates side by side, "Do **not** merge or rerank findings" (line 78). | **Overlap: high.** The pack adds the items in section 4, "Not in code-review". The pack lacks the fixed-point and spec-source discovery, the smell baseline, and the hard-versus-judgement split (line 66). |
| `tdd` | Red-green loop. "Refactoring is not part of the loop. It belongs to the review stage (see the `code-review` skill)" (line 36). | **No overlap.** It routes refactor review to `code-review`. |
| `implement` | "Once done, use /code-review to review the work." | **No overlap.** It is a consumer of `code-review`. A pack would be a second option here, which is the duplication to avoid. |
| `grilling` | "Do not act on it until I confirm we have reached a shared understanding." | **Weak overlap.** It is the closest installed skill to the `missing_intent` path (spec 4.1). `code-review` already handles missing intent by asking the user (line 32), so the pack adds nothing here. |

Checked by grep for review wording only, not read in full: `qa`, `teach`, `loop-me`, `writing-beats`, `ask-matt`, `improve-codebase-architecture`. None has a review pass that overlaps. `code-review` points to `agents/openai.yaml` (read) and to `docs/agents/issue-tracker.md` in the target repo. That file does not exist in this repo, so the spec-source fetch is not checked here.

## 4. What the pack adds, and what code-review already has

Row key: **Same** (both have it), **Pack adds** (only the pack has it), **code-review has** (only code-review has it), **Conflict** (the two cannot both hold).

| # | Item | Pack | code-review | Status |
|---|---|---|---|---|
| 1 | Two axes with the same names and meaning | 5.1, 5.2 | lines 8-9 | Same |
| 2 | Parallel, independent passes | 5.3 | line 11, line 60 | Same. The pack states the rule that neither pass sees the other's findings. code-review gets this by construction. |
| 3 | Spec missing | `missing_intent` is a finding (4.1, F6) | ask the user, then skip with "no spec available" (line 32) | code-review is better. Do not offer the pack's version. |
| 4 | Spec checks | right problem; each requirement; implied edge cases; scope creep; missing items; cite the requirement (5.2) | (a) missing or partial; (b) scope creep; (c) implemented but wrong; quote the spec (line 72) | Same, except the pack adds **implied edge cases** and **right problem**. |
| 5 | Judge against intent, not against the author's account of the diff | section 7 ("Reviewer agrees with the author's own summary") | commit list passed to the Spec pass (line 70), with no instruction on how to weigh it | **Pack adds.** |
| 6 | Standards checks | code quality, conventions, patterns, maintainability, **performance, security, error handling, test coverage of risky logic** (5.1) | documented standards (section 3) plus the smell baseline (lines 38-56) | **Pack adds** performance, security, error handling and risky-logic test coverage as explicit checks. code-review has the smell baseline, which the pack lacks. The two are complementary. |
| 7 | Exclude formatter output, taste, and what tooling enforces | 5.1 ("Do not report ... taste") | "skip anything tooling enforces" (line 66) | Same. The pack adds "taste" explicitly. |
| 8 | One root cause, many locations, filed once | 5.1 | none | **Pack adds.** code-review's "Duplicated Code" smell is a different rule. |
| 9 | Finding schema: `id, axis, severity, location, what, problem, fix, consequence, confidence` | 4.2, `schema/finding.json` (not built) | none. Output is prose, under 400 words (lines 66, 72) | **Pack adds.** |
| 10 | Mandatory concrete `fix`; a candidate with no fix goes to `notes` | 4.2, 5.1, 5.2, F7 | none. The smell definitions say "how to fix" (line 43), but the report brief does not require a fix | **Pack adds.** |
| 11 | Hard violation versus judgement call | none; severity only | "documented-standard breaches can be hard, but baseline smells are always judgement calls" (line 66) | **code-review has.** Keep it. |
| 12 | Severity scale (critical to info) | 5.5 | none | **Pack adds.** |
| 13 | Ordering by a rank table, not alphabetical | 5.6 | none (reports are presented as written) | Needed only when severity is added. The rank table then applies within an axis. |
| 14 | Gate: block, warn, pass | 5.6, computed on the **highest severity across both axes** | "Don't pick a single winner across axes — that's the reranking the separation exists to prevent" (line 80) | **Conflict** for a cross-axis gate. A **per-axis** gate does not conflict. |
| 15 | Merge the two result sets: same location and cause become `axis: both`, severity raised | 5.7, F9 | "Do not merge or rerank findings" (line 78) | **Conflict.** Do not offer. |
| 16 | Production-impact checklist when risk is flagged: load, security, failure behaviour, error handling, rollback, what to cut | 5.4, `risk_flags` (4.1) | none | **Pack adds.** Offer. |
| 17 | Large diff: split by file group, say what was not seen | section 7 | none | **Pack adds.** Offer. |
| 18 | Per-axis cap with ranked drop (25) | section 6, section 7 | 400-word cap per sub-agent (lines 66, 72) | Partly. The pack adds ranked drop with a count. Optional. |
| 19 | Confidence per finding, with a quoted `what` so a human can check it | 4.2, section 7 | none | **Pack adds.** |
| 20 | `test_results` input | 4.1 (optional) | none | **Pack adds.** Optional input. |
| 21 | Fixtures F1-F9 and acceptance criteria 1-6 | section 8 | none | **Pack adds.** Not built, not run (section 6). |
| 22 | Source discovery: fixed point, spec from commit refs, paths, `docs/`, ask | none; intent is an input | steps 1-2 (lines 17-32) | **code-review has.** |
| 23 | Harness wording | neutral (spec is harness-free) | names the Agent tool, `general-purpose`, `/setup-matt-pocock-skills` and `docs/agents/issue-tracker.md` (lines 13, 60, 62) | code-review is harness-specific by design. An addition must be written in code-review's voice. |

### 4.1 Parts that are NOT in code-review

1. Finding schema with mandatory `location, what, problem, fix, consequence`, plus `severity`, `confidence`, `id` and `axis` (items 9, 19).
2. Mandatory concrete fix, and the `notes` channel for questions (item 10).
3. Severity scale and its rank order (items 12, 13).
4. Per-axis gate (item 14, per-axis form only).
5. Production-impact checklist (item 16).
6. Standards checks for performance, security, error handling and risky-logic tests (item 6).
7. One root cause filed once within an axis (item 8).
8. Spec: implied edge cases and the "right problem" test (item 4).
9. Judge against intent, not against commit messages (item 5).
10. Large-diff split and a statement of what was not seen (item 17).
11. Per-axis cap with ranked drop (item 18, optional).
12. Fixtures (item 21).

### 4.2 Parts that must not be offered to code-review

- **Cross-axis merge** (spec 5.7). It contradicts code-review line 78. It also breaks code-review's stated purpose ("stops one axis from masking the other").
- **Overall gate** computed from the worst finding across both axes (spec 5.6, F5, F9). It is the reranking that line 80 forbids. Use the per-axis gate instead.
- **`missing_intent` as a finding** (spec 4.1, F6). code-review already asks the user and skips, which is better.

## 5. Build decision: no PACK.md

The brief builds `PACK.md` only when the additions stand alone. They do not:

- The schema, severity and gate describe the output of a review pass. Without the two-axis pass they have nothing to apply to. That pass is what `code-review` already is.
- A standalone `PACK.md` would carry the same review triggers as `code-review`, so it would duplicate it. Building it would leave two review skills competing for one request.
- The one part that can stand alone, the production checklist (item 16), is a rule set. It fits better as a section of `code-review`'s Standards brief than as a separate skill.

If the owner decides to keep a standalone skill anyway, the blockers are: the Known consumers and UMAS wording in spec sections 9, 10 and 12 must stay out of the body; `schema/finding.json` and `schema/review.json` are not built; `config.yaml` is not built; the spec's `model: default` (section 12.2) is non-normative and must not reach the body; and the merge and overall gate (4.2) must be removed first.

## 6. Fixtures (not built, not run)

No fixture files exist. The spec's table is the test set for the proposed addition. None has been run against a model.

| ID | Applies to the addition? | Note |
|---|---|---|
| F1 | Yes | SQL built by concatenation. Expect one critical Standards finding with a parameterised-query fix. "Critical" requires the severity addition. |
| F2 | Yes | JSON export missing. Expect one high Spec finding that cites the requirement. |
| F3 | Yes | Unrequested cache. Expect a Spec scope-creep finding with "remove it" as the fix. |
| F4 | Yes | Pricing branches with no tests. Expect a medium Standards finding naming the cases. |
| F5 | Yes, per axis | Clean diff. Expect no findings and a `pass` gate on each axis. The pack's single overall gate does not apply. |
| F6 | Changed | Expected behaviour is code-review's (ask the user, skip the Spec pass with "no spec available"), not a `missing_intent` finding. |
| F7 | Yes | Vague concern with no fix. Expect a question in `notes`, not a finding. |
| F8 | Yes | Correct pattern that looks suspicious. Expect no finding. |
| F9 | **Dropped** | Depends on the cross-axis merge, which conflicts with code-review. Replace with: the same bug, reported once under each axis. |

## 7. Enhancements, in priority order (for the proposed addition)

1. Remove the cross-axis merge and the overall gate from the design (owner decision, section 8).
2. Add the per-axis finding format with a mandatory fix and the `notes` channel.
3. Add the production checklist, triggered by the diff's risk (see section 9).
4. Broaden the Standards checks to security, error handling and risky-logic tests, all written as judgement or hard as appropriate.
5. Tell the Spec pass to judge against the spec text, not the commit messages.
6. Add the large-diff rule.
7. Add fixtures F1-F8 as the acceptance test for the addition.

## 8. Decisions needed from the owner

1. **Adopt the per-axis additions into `code-review`?** Options: (a) yes, the additions in section 4.1 (items 1-3, 5-10, 12), written as in section 9; (b) no, keep `two-axis-review` as a design record only. **Recommend (a).**
2. **Overall gate and cross-axis merge.** Options: (a) drop both, keep the per-axis gate (fits code-review's "no winner across axes"); (b) keep the overall gate as a labelled recommendation next to the two reports. **Recommend (a).** Option (b) overrides line 80 of code-review and needs the owner to say so.
3. **Pack status.** `packs/README.md` lists `two-axis-review` as a standalone pack. Recommend the coordinator mark it "folded into `code-review`" with this spec kept as the design record. I did not edit `packs/README.md`.

## 9. Proposed addition to code-review (not applied)

The text below is for the owner to review and apply to `~/.claude/skills/code-review/SKILL.md`. It is written in code-review's voice. It names no model, and it uses no UMAS wording.

Add to both sub-agent prompts in step 4:

```markdown
Report each problem as a finding with: location (file and line range), what (the quoted code or behaviour), problem (why it is wrong or risky), fix (a concrete change that resolves it), consequence (what happens if it is left), severity (critical | high | medium | low | info), and confidence (high | medium | low). If you cannot state a concrete fix, list the item under Questions, with no severity. Report each root cause once, and list its other locations. Rank findings by severity, then by location, and keep at most 25 per axis. Say how many you dropped. Say which part of the diff you did not see, if any.
```

Add to the Standards sub-agent brief:

```markdown
Also check: performance; security (what input reaches the code, whether it is validated, how secrets are handled, whether access is checked); error handling (errors surfaced with enough context, never swallowed); and test coverage of risky logic (branches, loops, parsers, money, authorisation). Do not report what a formatter or linter would change, or matters of taste. A baseline smell is a judgement call: label it as one, and cite the defect it causes if it causes one.
```

Add to the Standards sub-agent brief when the change touches production risk (payments, authorisation, migrations, external calls, high-volume paths). The sub-agent states the risk it inferred from the diff, then answers each gap as a finding:

```markdown
Load: what happens at ten times the expected traffic or data volume?
Security: what can an attacker control, and is input validated and access checked?
Failure: what happens when each dependency is down or slow?
Errors: are errors surfaced with context, and never swallowed?
Rollback: can the change be reverted, and what data has it already written?
Cut: which part is not needed to meet the requirement?
```

Add to the Spec sub-agent brief:

```markdown
Judge the diff against the spec text. Do not treat the commit messages as evidence: they are the author's account of the diff. Also check the edge cases the requirements imply, and whether the change solves the problem the spec names, not only the literal wording. If the spec has no testable requirement, say so and ask for acceptance criteria.
```

Replace the step 5 aggregation with:

```markdown
Give each axis its own gate: block if it has a critical or high finding, warn if its worst finding is medium, pass otherwise. Show each gate beside its report. Do not combine the two gates, and do not rank findings across axes.
```

## 10. Verification

- `PACK.md`: not built. The front-matter, grep, path and schema checks in the brief do not apply.
- Proposed addition (section 9): checked by grep for model names and vendor names (see report).
- No file was edited outside `packs/two-axis-review/`. `code-review` was read and not edited.
- Nothing was committed.
- Fixtures: listed in section 6, not built, not run.

## Changes made

None. `PACK.md` was not built, so there was nothing to improve.
