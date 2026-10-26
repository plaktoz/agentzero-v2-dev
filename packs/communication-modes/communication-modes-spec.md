# communication-modes

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](../README.md)
> **Independence:** no dependency on UMAS. Two output registers, an intensity scale, and a routing table by document type.
> `pack_version: 0.1.0`

---

## 1. Purpose

Agents talk to each other often and to people rarely, and those two audiences need opposite things. This pack gives an agent two registers: **compact** (agent-to-agent, optimised for tokens) and **plain** (human-facing, optimised for clarity), and a table that picks one from the kind of text being produced.

## 2. Scope and Non-Goals

**In scope**
- Definitions of the two registers (the source calls them *caveman* and *unslop*)
- Three compact intensity levels
- A routing table by document type
- Protected content that is never compressed
- Fixtures that check meaning survives compression

**Non-goals**
- Removing generic AI patterns from plain text. See [anti-slop](../anti-slop/anti-slop-spec.md); plain mode composes with it.
- Context packing and summarisation. See [budget-meter](../../libs/budget-meter/README.md) `pack()`.
- Translating between human languages

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Two prompts (5.1, 5.2), intensity definitions, protected-content rule |
| `routing.yaml` | Document type to mode (section 6) |
| `schema/message.json` | Optional status-message shape (4.2) |
| `fixtures/*.yaml` | F1 to F7 |

## 4. Contract

### 4.1 Input

```text
audience:     agent | human
doc_type:     string?     looked up in routing.yaml when audience is not given
intensity:    1 | 2 | 3   compact only
content:      string      what to say
```

### 4.2 Output

The register applies to the text. For status messages an optional shape keeps compact text parseable:

```json
{ "task": "auth-system", "status": "login ok, signup 50%, reset pending",
  "blocker": "JWT dependency", "next": "signup validation -> email verify -> tests",
  "budget_used": "85%" }
```

## 5. The Rules and Prompt

### 5.1 Compact register (agent to agent)

```text
You are writing for another agent that shares your context. Optimise for
tokens without losing meaning.

Allowed: abbreviations, symbols (-> != ok no), shortened phrases, dropped
articles, minimal context beyond what the reader already has.
Required: keep identifiers, paths, commands, numbers, error text, and
quoted strings exactly as they are.
If a fact would be ambiguous once shortened, write it in full.
```

### 5.2 Plain register (human-facing)

```text
You are writing for a person who was not in the working session.
Use complete sentences and correct grammar. Give concrete examples and
numbers. Explain terms the reader may not know. Avoid generic AI phrasing.
A non-technical stakeholder should be able to follow it.
```

### 5.3 Compact intensity

| Level | Description | Source's stated reduction |
|-------|-------------|---------------------------|
| 1 | Drop filler and articles; keep sentences | 20 to 30 percent |
| 2 | Telegraphic phrases and symbols | 40 to 50 percent |
| 3 | Maximal abbreviation, shared-context shorthand | 60 to 70 percent |

Reductions are the source's estimates and are **unverified**. Higher levels raise the risk of misreading, so the default is 2 and level 3 is for messages between agents of the same role and task.

### 5.4 Protected content

Never abbreviated, reworded, or dropped in either register:

- Code, commands, file paths, URLs, branch names, IDs
- Numbers and units
- Error messages and quoted text
- Names of people, systems, and decisions
- Anything that is the object of a decision (an approval request must say exactly what is being approved)

This list is the safety rule that the source leaves implicit.

### 5.5 Routing

| Document type | Register | Anti-slop |
|---------------|----------|-----------|
| PRD | plain | yes |
| Technical documentation | plain | yes |
| Reports, escalation text to a human | plain | yes |
| Agent logs | compact | no |
| Status updates (agent to agent) | compact | no |
| Handoff notes (agent to agent) | compact, level 2 | no |
| Handoff summary shown to a human | plain | yes |

Unknown types default to plain. A mistaken plain message costs tokens; a mistaken compact message can cost understanding.

## 6. Configuration

```yaml
default_register: plain
agent_to_agent: { register: compact, intensity: 2 }
human_facing:   { register: plain,   require_examples: true }
documents:
  - { type: prd,           register: plain,   anti_slop: true }
  - { type: tech_docs,     register: plain,   anti_slop: true }
  - { type: agent_log,     register: compact, anti_slop: false }
  - { type: status_update, register: compact, anti_slop: false }
protected_patterns: [code_fence, inline_code, path, url, number, quoted]
```

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| Compact text leaks into a human document | Routing is by document type, not by the writer's habit. A human-facing type with compact style is a finding |
| Meaning lost in compression | Protected content rule; fixtures F2 and F3; intensity 3 only for same-role messages |
| Reader agent lacks shared context | Compact applies only when the reader has the task context. A fresh worker with no history gets plain |
| Ambiguous abbreviation (`ok` as approval versus status) | Required: write it in full when shortening would be ambiguous |
| Symbols mangled by a tool that mishandles Unicode | ASCII alternatives (`->`, `ok`) are the default; Unicode symbols are optional |

## 8. Fixtures and Acceptance Criteria

### 8.1 Fixtures

| ID | Input | Expected |
|----|-------|----------|
| F1 | Status of "auth-system" for another agent, at intensity 2 | Short block like `Status: login ok, signup 50%, reset pending / Blocker: JWT dependency / Next: ...` containing all four facts |
| F2 | Same status at intensity 3 | Still contains task, per-item status, blocker, and next step; no fact lost |
| F3 | Message containing a command, a path, and an error string | All three appear verbatim in compact output |
| F4 | The same status for a project sponsor | Full sentences; sections Completed, In Progress, Pending, Blocker, Next Steps; no abbreviations |
| F5 | Doc type "prd" | Routed to plain with anti-slop |
| F6 | Doc type "agent_log" | Routed to compact without anti-slop |
| F7 | Unknown doc type | Plain |

### 8.2 Acceptance criteria

1. For F1 to F3, a second model given only the compact text can answer five factual questions about the status (task, done, in progress, blocker, next) correctly. This round-trip test is the meaning-preservation check.
2. For F3, the protected strings are byte-identical in the output.
3. Routing in F5 to F7 is a pure function of `routing.yaml` and needs no model.
4. For F1, token count of compact output is at most 70 percent of plain output at intensity 2 (conservative: the source claims 40 to 50 percent).
5. F4 contains no symbol from the compact set and no sentence fragment.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| PRD §11.9, `config/communication-modes.yaml` | `routing.yaml` and the config here |
| Event log text, `STATE.md` notes, handoff notes | Compact |
| PRDs, ADRs, PRFAQ, escalation summaries to people | Plain, then [anti-slop](../anti-slop/anti-slop-spec.md) |
| Handoff packet content | Compact (the successor shares the task context in the packet) |

## 10. Source Material and Deviations

Extracted from PRD §11.9 (communication mode requirements) and the caveman/unslop options in `ANTI-SLOP-EXAMPLES.md`.

| Deviation | Why |
|-----------|-----|
| Protected content rule | The source says "minimal context, assume shared understanding" but does not forbid altering commands, paths, or numbers, which is the main way compact text goes wrong |
| Defaults and risk ordering of intensities | The source gives three options without a default |
| Round-trip comprehension test | The source claims meaning is preserved without a test |
| Conflicting savings figures noted | PRD §11.9 says 40 to 60 percent; the examples file says 20 to 30, 40 to 50, and 60 to 70 by option. Both are unverified; this spec uses the per-level numbers |
| Human-facing handoff summary added to routing | Handoff text is read by agents but often surfaced to humans |
| ASCII-first symbols | The source uses arrows and check marks that some terminals and tools mangle |

## 11. Open Questions

1. Does the successor of a handoff always share enough context for compact notes? The packet may be read by a human during triage; if so, plain might be right for that one document.
2. Should intensity be chosen per message (by the writer) or per route (by configuration)? This spec says per route.
3. Is there a risk that compact outputs degrade a weaker reader model? A comprehension test across the models in use would answer it.
