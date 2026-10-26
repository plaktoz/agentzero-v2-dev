---
name: anti-slop
description: Anti-slop second pass over finished prose, docs, PRDs or code. It removes generic AI wording (stock vocabulary, vague claims, filler), premature abstractions and redundant comments, and keeps every fact. Use when a finished draft, document or code change needs de-slopping, after the content is complete.
---

# anti-slop

Pack version 0.1.0. A narrow review pass over finished content. It removes generic patterns and leaves facts, examples, names, numbers and structure as they are.

## Not this skill

- It does not restructure an article, reorder sections or tighten a whole argument. Use an article-editing skill for that. This pack changes only generic wording inside a finished text.
- It does not draft or shape content from raw notes or fragments. Use a drafting skill for that. Run this pack only after the draft is final.
- It does not supply missing facts. A vague claim that needs a number goes to `flags`.
- It is not for compact agent-to-agent text, where terse fragments are intended. Apply it only to text a person will read, and to code.
- It is not a code review. It does not look for bugs, security problems or gaps against a spec. Use a review skill for those.

## Input

```text
content:    the text or code to review
kind:       prose | prd | docs | code
preserve:   [facts, examples, structure]   default
language:   the programming language, for kind=code
```

## Procedure

Run the steps in order. A step is done when its check is met.

1. **Set the inputs.** Confirm `kind` is one of `prose`, `prd`, `docs`, `code`, and that `language` is set for `code`. Check: the kind is known before any edit. If it is missing, ask for it.
2. **Read the whole content.** List its facts: every number, name, code identifier and example. Note its structure. Check: the list exists before you edit.
3. **Resolve each phrase hit.** Go through every entry in `phrases.yaml` (both lists, case-insensitive) and find each hit in the content. For a word used in its plain sense ("a landscape photo"), leave it. For any other hit, apply writing rule 3: remove the phrase when the sentence keeps every fact it had; otherwise replace it with a fact, command or example from the content; otherwise flag the claim. For `code`, check comments and docstrings only. Check: every hit has one outcome.
4. **Walk each sentence against the patterns.** Read every sentence against the table in "What counts as slop" and against the rules for its kind: writing rules for `prose`, `prd` and `docs`, code rules for `code`. Check: every sentence has been read, not only the phrase hits.
5. **Record each change.** For each edit, write one change entry with its category, before text, after text and one-line reason. For code rule 3, set `behaviour_change: true`. Check: no edit lacks an entry, and no entry lacks a category.
6. **Check the facts.** Every number, name and code identifier from step 2 still appears in `revised`. If one sat in a sentence you removed, put it back. Check: the sets match. Run `compare` when a script is available.
7. **Check the phrase list again.** Every hit left in `revised` is a plain-sense use or is in `flags`. Check: no hit is unresolved.
8. **Write the output record.** Check: `revised` equals the input when `changes` is empty, and every change has a listed category. Run `validate` when a script is available.

## Reviewer prompt

```text
You are running a narrow second pass. The content is already complete.
Your only job is to remove generic patterns.

Keep every fact, number, example, name, and the document structure.
Change only text that matches a listed pattern. Treat each change as a
proposal: list it with its category and reason.

If a sentence is vague and the fix needs a fact you do not have, do not
invent one. Add it to "flags" for the author.

Leave first-person opinions and deliberate style alone, and say what
you left in "kept".

If nothing matches a listed pattern, return the content unchanged with
"changes" empty.

Return the revised content, the change list, the kept list, and the flags.
```

## What counts as slop

| Category | Examples |
|----------|----------|
| AI vocabulary | delve, pivotal, tapestry, underscore, landscape |
| Vague claims | statements with no source, number, or detail |
| Filler | long expressions for simple ideas ("serves as" for "is") |
| Generic openings | "In today's rapidly evolving landscape..." |
| Forced structures | artificial groups of three, unnecessary comparisons |
| Synonym overuse | changing the term for one concept in successive sentences |
| Excess formatting | heavy use of bold text and section headings |

Code adds four change categories: `premature_abstraction`, `redundant_comment`, `swallowed_error`, `unneeded_fallback`. See the code rules.

The phrase list in `phrases.yaml` is a floor, not the definition. A sentence that matches a pattern but uses none of the listed words is still slop. A listed word used in its literal sense ("a landscape photo") is not.

## Writing rules

1. Start with the useful point. Delete generic introductions.
2. Be direct: "is", not "serves as".
3. Replace broad claims with facts, commands, or examples. When the content holds no such fact, flag the claim. Do not invent one. When a vague phrase can be removed and the sentence keeps every fact it had, remove the phrase and do not flag it.
4. Remove sections that repeat earlier points. When `preserve` includes `structure`, flag the section instead of removing it.
5. If a sentence could appear in any project's docs, cut it.
6. Limit adverbs.
7. Keep paragraphs to one idea each.
8. Keep first-person opinions and deliberate style. List them in `kept`.
9. Use one term for one concept. Keep the term the author used most, and do not introduce a new one.

## Code rules

1. No premature abstraction. Remove an interface or factory with one implementation.
2. Delete comments that repeat the code.
3. Do not hide errors. Do not turn an exception into an empty result.
4. Remove fallbacks the task did not require.
5. Keep it minimal. No "extensible" layer without a present need.

Rule 3 changes behaviour. The reviewer MUST tag such a change `behaviour_change: true`, and a person or the test suite confirms it. Every other code change must preserve behaviour. If a removal would change behaviour for any other reason, do not make it. Add it to `flags`.

Keep comments that explain why, state a constraint, or warn about a trap. Keep docstrings that describe a public contract the code alone does not show.

## Variants

| Kind | Additional rules |
|------|------------------|
| `prd` | Replace "comprehensive solution", "leveraging cutting-edge", "seamlessly integrate", "robust framework", "empower teams to" with specific metrics, concrete examples, direct statements, real constraints, and actual timelines. Use only metrics, constraints and dates present in the content. Flag the rest |
| `docs` | Open with the useful point. Replace broad claims with commands or examples. Introduce snippets with context. One concept per paragraph. Drop statements true of any product |
| `prose` | The writing rules only |
| `code` | The code rules only. Writing rules apply to comments and docstrings that remain |

## Two-pass protocol

1. **Pass 1, content.** Produce the full content: facts, sources, examples, structure. Do not worry about slop.
2. **Pass 2, review.** Run the reviewer prompt. Fix only listed patterns.
3. **Human review.** A person checks that facts are preserved and slop is gone. Show the `changes` list, not only the new text.

Running pass 2 on its own output must produce no further changes. A second pass that keeps changing text is rewriting, not removing patterns.

## Output record

Return one JSON object that validates against `schema/review-output.json`.

```json
{
  "pack_version": "0.1.0",
  "revised": "full revised content",
  "changes": [
    {
      "category": "filler",
      "before": "serves as",
      "after": "is",
      "reason": "Long form for a simple verb.",
      "behaviour_change": false
    }
  ],
  "kept": ["deliberate style choices left alone"],
  "flags": [
    { "location": "paragraph 2", "issue": "Claim has no source or number. The author must supply one." }
  ]
}
```

- `category` is one of: `ai_vocabulary`, `vague_claim`, `filler`, `generic_opening`, `forced_structure`, `synonym_overuse`, `excess_formatting`, `premature_abstraction`, `redundant_comment`, `swallowed_error`, `unneeded_fallback`.
- `behaviour_change` is optional, and required (true) on a `swallowed_error` change.
- `flags` is for problems the reviewer must not fix because the fix needs a fact it does not have. The reviewer never invents a number to replace a vague claim.
- `kept` lists first-person opinions and deliberate style choices left alone. Use `[]` when there are none.
- `revised` equals the input when `changes` is empty.

## Optional deterministic checks

`scripts/lint.py` runs without a model. It uses the Python standard library only. See `scripts/lint.py --help`. Run it with `python3` on macOS and Linux, or `py -3` or `python` on Windows. Exit code 0 is no finding, 1 is a finding, 2 is a usage or input error.

- `python3 scripts/lint.py check FILE --kind prose` (add `--kind code --language python` for code)
- `python3 scripts/lint.py compare ORIGINAL REVISED`
- `python3 scripts/lint.py validate RECORD.json`

- Forbidden phrases from `phrases.yaml`: the count should be zero.
- Average paragraph length: under the `max_avg_paragraph_sentences` limit in `config.yaml`.
- Comment-to-code ratio of a code file: under the `max_comment_ratio` limit in `config.yaml`.
- `compare` mode: the numbers, names and code identifiers in the revised text equal the original's. This catches a dropped fact and an invented number.

The thresholds are defaults, not validated targets. The model is needed for the judgement categories: vague claim, filler, synonym overuse.

## Limits

- The reviewer cannot tell whether a fact is true. It only keeps the facts it was given.
- Rule 3 and the removal of single-implementation abstractions need a person or the tests to confirm. The script does not check them.
- The phrase list is English only.
