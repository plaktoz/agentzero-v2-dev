# Content Packs

> Nine reusable prompt-and-rule packs. Each is plain text (Markdown, YAML, JSON Schema) that any agent harness can load without modification. None assumes a specific model, tool, or consuming application.
>
> **Status:** Draft v0.1 · **Date:** October 21, 2026
> **Used by:** [UMAS](../umas/TECHNICAL-DESIGN-SUMMARY.md) and any agent workflow that needs these capabilities independently.
> **Sibling set:** [libs/](../libs/README.md) (code libraries)

---

## The Set

| Pack | One-line purpose | Standalone use |
|------|------------------|----------------|
| [minimalism-ladder](./minimalism-ladder/README.md) | A six-rung check an agent runs after reading the code and before writing any | Cuts needless code in any coding agent |
| [anti-slop](./anti-slop/README.md) | Writing and code rules plus a two-pass review that removes generic AI patterns without touching facts | A review skill for docs and code in any repo |
| [communication-modes](./communication-modes/README.md) | Two registers (compact for agents, plain for humans) with intensity levels and a routing table | Token savings in agent-to-agent text, clarity in human-facing text |
| [two-axis-review](./two-axis-review/README.md) | Independent Standards and Spec review passes, one finding format, severity-based gating | A PR review skill for any team |
| [specialist-agents](./specialist-agents/README.md) | Prompts and output contracts for Analyst, Product Manager, UX Designer, Architect, Developer | A lightweight planning-to-code pipeline |
| [router-heuristic](./router-heuristic/README.md) | A scoring rubric that sends a request to a direct worker, an architect plus worker, or a full panel | Right-sizing process to task size |
| [grilling](./grilling/README.md) | A bounded questioning protocol that produces an alignment summary before work starts | Requirement clarification for any agent |
| [test-policy](./test-policy/README.md) | A selective-versus-strict testing rule and a "risky logic" classifier | Deciding which changes need tests |
| [playbook-runner](./playbook-runner/README.md) | A phase-gated workflow engine: any SDD or process workflow expressed as a Markdown playbook, executed by the Coordinator with human gates, auto gates, and a mandatory escape hatch | Running any phase-gated development process (production gatekeeper, autonomous loop, compliance workflow) against any project |

### Built-in playbooks (shipped inside `playbook-runner`)

| Playbook | Purpose | Phases |
|----------|---------|--------|
| `production-gatekeeper` | Six-stage quality-gated workflow: Spec before code, human approves plan, tests gate build, two-axis review before ship | DEFINE → PLAN (gate) → BUILD → VERIFY (gate) → REVIEW → SHIP |
| `autonomous-loop` | Autonomous execution to a user-defined exit predicate with escape hatch | SCAN → APPLY → VERIFY (exit predicate) |

### Considered and not extracted

| Candidate | Decision | Reason |
|-----------|----------|--------|
| Audit skill (whole-repo impact-ranked analysis) | Not extracted | The PRD names it but gives no rule set to port. Nothing to specify beyond a title. Re-open when its behaviour is defined |
| Handoff-packet compression levels | Not a pack | The mechanism is `pack()` in [budget-meter](../libs/budget-meter/README.md). What goes into the packet is task-specific and is covered by the Developer prompt in specialist-agents |

---

## Independence Rules

A pack that breaks one of these is defective.

1. **No consumer-specific names, paths, or commands in the pack body.** No tool-specific paths, CLI names, or application strings. Anything environment-specific is an input placeholder such as `{{project_conventions}}`. Consumer-specific mappings live only in each spec's "Known consumers" section.
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
| Agent harness skill | `PACK.md` becomes a `SKILL.md` (or equivalent) with a short front-matter `description` for Claude Code, Antigravity, Codex, or any harness that loads skill files |
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
        +-------------------------------------+------------ playbook-runner (optional)
        v                                                          |
 specialist-agents (Analyst -> PM -> UX -> Architect -> Developer) |
        |                                  |                       |
        |            uses                  | uses    phase loop:   |
        v                                  v         gates + escape|
 communication-modes (artifact register)   minimalism-ladder + test-policy
        |
        v
 anti-slop (second pass over human-facing text and code)

 diff --> two-axis-review --> findings (severity gate)
                 uses: anti-slop code rules (Standards axis), test-policy (Standards axis)

 playbook-runner wraps the pipeline above; each playbook step calls one pack or agent role.
 Without a playbook, the pipeline runs in the default implicit sequence (unchanged).
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

Every pack spec uses the same sections: 1 Purpose · 2 Scope and non-goals · 3 Pack contents and format · 4 Contract (input and output) · 5 The rules and prompt · 6 Configuration · 7 Failure modes · 8 Fixtures and acceptance criteria · 9 Known consumers · 10 Source material and deviations · 11 Open questions.

A spec may end with an optional section 12, **Reference implementation (source code)**. It holds non-normative example code, which may use consumer-specific names and paths. It is outside the independence rules; sections 1 to 11 are authoritative.
