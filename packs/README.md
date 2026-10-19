# Content Packs (Tier 2)

> Eight reusable prompt-and-rule packs extracted from the UMAS design. Each is plain text (Markdown, YAML, JSON Schema) that any agent harness can load. Each has its own spec and can be versioned, tested, and used without UMAS.
>
> **Status:** Draft v0.1 · **Date:** October 19, 2026
> **Referenced from:** [UMAS-TECH-DESIGN-SPEC.md](../UMAS-TECH-DESIGN-SPEC.md) §1.1 · [TECHNICAL-DESIGN-SUMMARY.md](../TECHNICAL-DESIGN-SUMMARY.md)
> **Sibling set:** [libs/](../libs/README.md) (Tier 1, code libraries)

---

## The Set

| Pack | One-line purpose | Standalone use |
|------|------------------|----------------|
| [minimalism-ladder](minimalism-ladder.md) | A six-rung check an agent runs after reading the code and before writing any | Cuts needless code in any coding agent |
| [anti-slop](anti-slop.md) | Writing and code rules plus a two-pass review that removes generic AI patterns without touching facts | A review skill for docs and code in any repo |
| [communication-modes](communication-modes.md) | Two registers (compact for agents, plain for humans) with intensity levels and a routing table | Token savings in agent-to-agent text, clarity in human-facing text |
| [two-axis-review](two-axis-review.md) | Independent Standards and Spec review passes, one finding format, severity-based gating | A PR review skill for any team |
| [specialist-agents](specialist-agents.md) | Prompts and output contracts for Analyst, Product Manager, UX Designer, Architect, Developer | A lightweight planning-to-code pipeline |
| [router-heuristic](router-heuristic.md) | A scoring rubric that sends a request to a direct worker, an architect plus worker, or a full panel | Right-sizing process to task size |
| [grilling](grilling.md) | A bounded questioning protocol that produces an alignment summary before work starts | Requirement clarification for any agent |
| [test-policy](test-policy.md) | A selective-versus-strict testing rule and a "risky logic" classifier | Deciding which changes need tests |

### Considered and not extracted

| Candidate | Decision | Reason |
|-----------|----------|--------|
| Audit skill (whole-repo impact-ranked analysis) | Not extracted | The PRD names it but gives no rule set to port. Nothing to specify beyond a title. Re-open when its behaviour is defined |
| Handoff-packet compression levels | Not a pack | The mechanism is `pack()` in [budget-meter](../libs/budget-meter.md). What goes into the packet is task-specific and is covered by the Developer prompt in specialist-agents |

---

## Independence Rules

A pack that breaks one of these is defective.

1. **No UMAS names, paths, or commands in the pack body.** No `.umas/`, no `[umas:...]` strings, no `umas` CLI. Anything environment-specific is an input placeholder such as `{{project_conventions}}`. UMAS mappings live only in each spec's "How UMAS uses it" section.
2. **No tool or model assumption.** A pack is usable as a system prompt, a skill file, or a checklist read by a human. It may assume the agent can read files. It assumes no model ID, vendor, or special tool.
3. **No cross-pack dependency.** A pack does not import or require another. Where two meet (for example Router output feeding specialist-agents) the contract is a data shape, written in both specs.
4. **Contracts before prose.** Every pack defines its input and its output as a schema. A consumer can validate a response without reading the prompt.
5. **Testable by fixture.** Every pack ships fixtures (input plus the expected property of the output) and acceptance criteria that a person or a script can check. A pack with no fixtures is a draft.
6. **Versioned.** Each pack carries `pack_version` (semver). Outputs echo it so a stored artifact can be traced to the rules that produced it.
7. **Honest about limits.** Each spec states what the pack cannot do. Numbers that came from the source documents as claims (percent savings, accuracy targets) are marked unverified.

---

## What a Pack Contains

```text
<pack>/
  PACK.md          # metadata + the prompt/rules text (the deliverable)
  schema/*.json    # input and output JSON Schemas
  fixtures/*.yaml  # { id, input, expect: [property ...] }
  config.yaml      # defaults for every tunable
```

The spec in this directory describes all four. When the pack is built, `PACK.md` is the artifact that is loaded; the spec is its design record.

### Consumption forms

| Form | How |
|------|-----|
| Claude Code skill | `PACK.md` becomes `SKILL.md` with a short front-matter `description` |
| System prompt fragment | Concatenate the `## Prompt` section into the agent's system prompt |
| Human checklist | Read the `## Rules` section directly |
| CI linter (partial) | Deterministic parts only (forbidden phrases, finding schema). See each spec's "Deterministic checks" |

---

## Conventions Used in the Specs

- Prompt text appears in `text` fenced blocks. `{{name}}` is a placeholder the consumer fills.
- Schemas are written in compact pseudo-JSON-Schema; the built pack ships real JSON Schema.
- MUST, SHOULD, and MAY carry their RFC 2119 meaning.
- Fixtures are numbered per pack (`F1`, `F2`, ...). Acceptance criteria refer to them.
- Where the source contradicts itself, the spec picks a value and records the choice in section 10.

---

## Composition Map

Arrows show what the consuming application wires together. They are data shapes, not imports.

```text
request --> grilling --> alignment summary --+
                                              v
                                       router-heuristic --> route
                                              |
        +-------------------------------------+
        v
 specialist-agents (Analyst -> PM -> UX -> Architect -> Developer)
        |                                  |
        |            uses                  | uses
        v                                  v
 communication-modes (artifact register)   minimalism-ladder + test-policy
        |
        v
 anti-slop (second pass over human-facing text and code)

 diff --> two-axis-review --> findings (severity gate)
                 uses: anti-slop code rules (Standards axis), test-policy (Standards axis)
```

---

## Suggested Build Order

1. **minimalism-ladder** and **anti-slop**: highest value, smallest, and the others reference them.
2. **two-axis-review**: needs fixtures from the first two to test the Standards axis.
3. **test-policy** and **communication-modes**.
4. **router-heuristic** and **grilling**: both are only useful once there is something to route to.
5. **specialist-agents**: largest; build the Developer prompt first because it is the one that is always used.

---

## Spec Template

Every pack spec uses the same sections: 1 Purpose · 2 Scope and non-goals · 3 Pack contents and format · 4 Contract (input and output) · 5 The rules and prompt · 6 Configuration · 7 Failure modes · 8 Fixtures and acceptance criteria · 9 How UMAS uses it · 10 Source material and deviations · 11 Open questions.

A spec may end with an optional section 12, **Reference implementation (source code)**. It holds code moved verbatim from the original UMAS technical design. It is non-normative, may use UMAS names and paths, and is outside the independence rules; sections 1 to 11 are authoritative.
