# anti-slop

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](./README.md)
> **Independence:** no dependency on UMAS. A rule set, a two-pass review prompt, and an optional deterministic linter.
> `pack_version: 0.1.0`

---

## 1. Purpose

Remove generic AI patterns from prose and code after the content is written, without changing facts, examples, or structure. The review is a separate, narrow second pass so that the first pass can concentrate on being correct.

## 2. Scope and Non-Goals

**In scope**
- A definition of slop, in seven categories
- Writing rules, code rules, and per-document-type variants (PRD, technical docs)
- A two-pass protocol and the reviewer prompt
- A forbidden-phrase list and a deterministic lint for it
- Metrics definitions

**Non-goals**
- Supplying missing facts, choosing architecture, or making unverified content correct
- Replacing testing or human judgement
- Style policing beyond the listed patterns. First-person opinions and deliberate style are preserved
- Token compression. See [communication-modes](../communication-modes/README.md)

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Reviewer prompt (5.1), rules (5.2 to 5.5) |
| `phrases.yaml` | Forbidden phrases and word list |
| `schema/review-output.json` | Output (4.2) |
| `fixtures/*.yaml` | F1 to F10 |
| `config.yaml` | Mode, lists, thresholds |

## 4. Contract

### 4.1 Input

```text
content:     string      the text or code to review
kind:        prose | prd | docs | code
preserve:    [facts, examples, structure]    default
language:    string?     for code
```

### 4.2 Output

```json
{ "pack_version": "0.1.0",
  "revised": "full revised content",
  "changes": [ { "category": "ai_vocabulary|vague_claim|filler|generic_opening|forced_structure|synonym_overuse|excess_formatting|premature_abstraction|redundant_comment|swallowed_error|unneeded_fallback",
                 "before": "...", "after": "...", "reason": "one line" } ],
  "kept": ["deliberate style choices left alone"],
  "flags": [ { "location": "...", "issue": "claim has no source or number; author must supply" } ] }
```

`flags` is how the reviewer reports problems it must **not** fix because fixing needs facts. The reviewer never invents a number to replace a vague claim.

## 5. The Rules and Prompt

### 5.1 Reviewer prompt

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

Return the revised content, the change list, the kept list, and the flags.
```

### 5.2 What counts as slop

| Category | Examples |
|----------|----------|
| AI vocabulary | delve, pivotal, tapestry, underscore, landscape |
| Vague claims | statements with no source, number, or detail |
| Filler | long expressions for simple ideas ("serves as" for "is") |
| Generic openings | "In today's rapidly evolving landscape..." |
| Forced structures | artificial groups of three, unnecessary comparisons |
| Synonym overuse | changing the term for one concept in successive sentences |
| Excess formatting | heavy use of bold text and section headings |

### 5.3 Writing rules

1. Start with the useful point. Delete generic introductions.
2. Be direct: "is", not "serves as".
3. Replace broad claims with facts, commands, or examples.
4. Remove sections that repeat earlier points.
5. If a sentence could appear in any project's docs, cut it.
6. Limit adverbs.
7. Keep paragraphs to one idea each.
8. Keep first-person opinions and deliberate style.

### 5.4 Code rules

1. No premature abstraction. Remove an interface or factory with one implementation.
2. Delete comments that repeat the code.
3. Do not hide errors. Do not turn an exception into an empty result.
4. Remove fallbacks the task did not require.
5. Keep it minimal. No "extensible" layer without a present need.

Rule 3 changes behaviour, so the reviewer MUST tag such a change `behaviour_change: true` and a human or the test suite confirms it. All other code changes must be behaviour-preserving.

### 5.5 Variants

| Kind | Additional rules |
|------|------------------|
| `prd` | Replace "comprehensive solution", "leveraging cutting-edge", "seamlessly integrate", "robust framework", "empower teams to" with specific metrics, concrete examples, direct statements, real constraints, and actual timelines |
| `docs` | Open with the useful point; replace broad claims with commands or examples; introduce snippets with context; one concept per paragraph; drop statements true of any product |

### 5.6 Two-pass protocol

1. **Pass 1, content.** Produce the full content: facts, sources, examples, structure. Do not worry about slop.
2. **Pass 2, review.** Run the reviewer prompt. Fix only listed patterns.
3. **Human review.** A person checks that facts are preserved and slop is gone. The consumer shows the `changes` list, not only the new text.

### 5.7 Forbidden phrases (starter list)

```text
in today's rapidly evolving
leverage the power of
seamlessly integrate
robust framework
comprehensive solution
delve into
pivotal
tapestry
underscore
```

The list is data in `phrases.yaml`, not prompt text, so it can grow without editing the prompt. Matching is case-insensitive.

### 5.8 Deterministic checks

A script can verify without a model: the forbidden phrase count is zero; paragraph length averages under four sentences; comment-to-code ratio is under 0.1; no unused single-implementation abstraction (language-specific, optional). The model is needed only for judgement categories (vague claim, filler, synonym overuse).

### 5.9 Metrics

| Metric | Target (source) |
|--------|-----------------|
| Forbidden phrase count | 0 |
| Average paragraph length | under 4 sentences |
| Concrete examples per section | above 2 |
| Comment-to-code ratio | below 0.1 |
| Human revision rate | below 15 percent |
| Slop detection accuracy | above 90 percent |

Targets come from the source and are unvalidated. "Detection accuracy" needs a labelled set to be measurable; see F1 to F10 as its seed.

## 6. Configuration

```yaml
mode: two_pass            # off | two_pass
preserve: [facts, examples, structure]
phrases_file: phrases.yaml
max_avg_paragraph_sentences: 4
max_comment_ratio: 0.1
kinds:
  prd:  { enabled: true }
  docs: { enabled: true }
  code: { enabled: true }
  prose: { enabled: true }
```

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| Reviewer deletes a fact while "tightening" | Acceptance criterion 2 compares numbers, names, and identifiers before and after |
| Reviewer invents a metric to replace a vague claim | Prompt forbids it; the invented number does not appear in the input, so a script flags it |
| Over-editing flattens an author's voice | `kept` is required; first-person and deliberate style are preserved |
| Code "cleanup" changes behaviour | Only rule 3 may; it is tagged and gated on tests |
| Compact agent-to-agent text mistaken for slop | Apply this pack only to human-facing kinds. See communication-modes |
| Rule list rots into a blocklist that trains the model to rephrase | The ruleset targets patterns, and the phrase list is a floor, not the definition |

## 8. Fixtures and Acceptance Criteria

### 8.1 Fixtures

Each fixture is a before text and the property the revised text must have.

| ID | Before | Expected |
|----|--------|----------|
| F1 | "In today's rapidly evolving AI landscape, multi-agent systems are becoming increasingly pivotal ... to delve into complex problem-solving scenarios." | One concrete sentence stating what the system does and a number; no listed phrase |
| F2 | "This comprehensive solution serves as a robust framework that empowers teams to seamlessly integrate cutting-edge AI capabilities." | States which providers it integrates with and setup time; "serves as" gone |
| F3 | PRD executive summary full of the PRD phrases | Same facts, metrics stated directly; three fixtures-worth of phrases removed |
| F4 | A "Getting Started" section made of welcome text | Replaced by install, start, and verify commands |
| F5 | `AbstractAgentFactory` and one `ConcreteAgentFactory`, both with narrating docstrings | A single function; docstrings removed |
| F6 | `try: result = process(data); if result is None: return [] / except Exception: return []` | `return process(data)`; tagged `behaviour_change: true` |
| F7 | Vague claim with no numbers ("greatly improves performance") and no source | Appears in `flags`; text unchanged or marked, not filled with an invented number |
| F8 | A paragraph that uses "agent", "worker", "assistant", "bot" for one thing | One term used throughout |
| F9 | Text with a deliberate first-person opinion | Opinion unchanged; listed in `kept` |
| F10 | Text with no slop | `changes: []` (no false positives) |

### 8.2 Acceptance criteria

1. F1 to F10 satisfy their expected property.
2. For F1 to F4 and F8, the set of numbers, names, and code identifiers in the output equals the input's (checked by script), except where F7 flags an absent fact.
3. For F10, the output equals the input.
4. The phrase lint reports zero hits on revised F1 to F4.
5. Running the reviewer twice on its own output yields no further changes (idempotent).
6. Every entry in `changes` has a category from the list in 4.2.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| PRD §11 anti-slop, `config/anti-slop.yaml` | `config.yaml` and `phrases.yaml` here |
| Two-pass `create_document` | Document-producing agents run pass 1; the system calls the reviewer for pass 2 |
| `anti-slop review --document` | A command that wraps the reviewer prompt |
| Code rules in the Standards review axis | [two-axis-review](../two-axis-review/README.md) cites 5.4 |
| Metrics dashboard | Computed from `changes` records and the deterministic checks |

## 10. Source Material and Deviations

Extracted from PRD §11 (11.1 to 11.8), `ANTI-SLOP-EXAMPLES.md`, and the Anti-Slop references in `UMAS-TECH-DESIGN-SPEC.md`.

| Deviation | Why |
|-----------|-----|
| `flags` channel added | The source says anti-slop cannot supply facts, but gives the reviewer no way to say so |
| Behaviour-change tag for code rule 3 | "Let errors propagate" changes behaviour; the source presents it as pure cleanup |
| Forbidden phrases stored as data | The source embeds them in a YAML list inside the prompt config; a data file is easier to extend |
| Idempotence criterion | A second pass that keeps changing text indicates the reviewer is rewriting, not removing patterns |
| Caveman options moved to communication-modes | They are token compression, not slop removal; mixing them confuses both |
| Accuracy and revision targets marked unvalidated | No labelled corpus exists in the source |

## 11. Open Questions

1. Is `ANTI-SLOP-EXAMPLES.md` the intended labelled seed set? It has ten pairs; accuracy above 90 percent over ten items is not meaningful.
2. Should the phrase list be extensible per language (non-English docs)?
3. Who owns acceptance of the revised text when the author is an agent: the human reviewer at the end, or the requester?
