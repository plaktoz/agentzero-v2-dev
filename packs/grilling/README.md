# grilling

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](./README.md)
> **Independence:** no dependency on UMAS. A questioning protocol, a prompt, and an alignment summary format.
> `pack_version: 0.1.0`

---

## 1. Purpose

Get alignment before work starts. A person's request is questioned in a bounded session, then summarised in a short document the person confirms. The pack also states when **not** to grill: work that is already queued for an agent runs immediately.

## 2. Scope and Non-Goals

**In scope**
- A trigger rule: who and what is grilled, and who is not
- The question protocol: topics, limits, ordering, stop conditions
- The prompt
- The alignment summary format
- Timeout and non-response behaviour

**Non-goals**
- Collecting the answers through a UI. The consumer delivers questions and returns answers.
- Deciding the route or the design. See [router-heuristic](../router-heuristic/README.md) and [specialist-agents](../specialist-agents/README.md).
- Writing the requirements document. The Analyst and PM turn the summary into one.
- Open-ended interviewing. The session is capped.

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Trigger rule (5.1), prompt (5.3), summary template (5.5) |
| `schema/turn.json`, `schema/summary.json` | One interview turn; the final summary |
| `fixtures/*.yaml` | F1 to F9 |
| `config.yaml` | Limits and trigger rules |

## 4. Contract

### 4.1 Input

```text
request:       string
origin:        human | agent | escalation
context:       string?    relevant codebase notes, prior answers
transcript:    turn[]     previous questions and answers in this session
limits:        { max_questions, timeout_seconds }
```

### 4.2 Turn output (each step)

```json
{ "action": "ask | summarise | skip",
  "questions": [ { "id": "Q3", "topic": "success_criteria", "text": "...",
                   "why": "one clause", "default": "what I will assume if unanswered" } ],
  "skip_reason": null }
```

At most three questions per turn; each has a default.

### 4.3 Summary

```json
{ "pack_version": "0.1.0",
  "goal": "...",
  "success_criteria": ["checkable statement"],
  "constraints": ["..."],
  "edge_cases": ["..."],
  "out_of_scope": ["..."],
  "assumptions": [ { "about": "Q5", "assumed": "...", "because": "unanswered" } ],
  "open_risks": ["..."],
  "confirmed_by_user": false }
```

## 5. The Rules and Prompt

### 5.1 Trigger rule (the propulsion exception)

| Origin | Behaviour |
|--------|-----------|
| `human` | Grill |
| `agent` (a handoff or work already assigned to an agent) | **Skip.** Work that is already queued executes immediately; asking again stalls it |
| `escalation` | Grill at the point of escalation, then continue |

A human request that is already precise (single file, single change, cited location) may also be skipped: the prompt asks whether any question would change what gets built. If no, return `action: skip` with the reason.

### 5.2 Topics

| Topic | Probe |
|-------|-------|
| user_needs | Who wants this, and what are they doing when they need it? |
| success_criteria | How will we know it works? What would make you reject it? |
| constraints | Deadline, stack, compatibility, budget, things not to touch |
| edge_cases | Empty, huge, concurrent, failing, unauthorised, legacy data |
| integration | (Brownfield) How does this fit existing behaviour? What must not break? |
| vision | (Greenfield) What is the product, for whom, and what is the first usable slice? |

Brownfield asks `integration`; greenfield asks `vision`. They are not both asked.

### 5.3 Prompt

```text
You are aligning with a person before work starts. Your aim is the fewest
questions that remove the biggest risk of building the wrong thing.

Ask at most three questions at a time, most consequential first. For each,
say why it matters in one clause and the default you will assume if it is
not answered. Do not ask what the codebase or earlier answers already tell
you. Do not ask about implementation choices that are yours to make.

Stop and produce the summary when any of these holds: no remaining
question would change what gets built; the question limit is reached;
the person asks to proceed.

If the request is already precise enough to build, skip the session and say why.
```

### 5.4 Limits

| Limit | Default | Behaviour on reaching it |
|-------|---------|--------------------------|
| `max_questions` | 10 | Summarise; remaining unknowns become assumptions |
| `timeout_seconds` | 300 | If no answer arrives, proceed on defaults and mark them assumptions |
| `max_questions_per_turn` | 3 | Fixed |

### 5.5 Summary template

```text
Goal:             <one sentence>
Success criteria: <checkable, numbered>
Constraints:      <list>
Edge cases:       <list>
Out of scope:     <list>
Assumptions:      <each with the question it replaced>
Open risks:       <list>
Please confirm or correct.
```

The consumer shows the summary and records the person's confirmation. Work starts after confirmation or, if allowed by configuration, after `timeout_seconds` on stated assumptions.

### 5.6 Style

Questions are plain language, concrete, and answerable in a sentence or by choosing between listed options. No leading questions that assume a solution. Apply [anti-slop](../anti-slop/README.md) wording rules.

## 6. Configuration

```yaml
max_questions: 10
max_questions_per_turn: 3
timeout_seconds: 300
on_timeout: proceed_on_defaults     # proceed_on_defaults | block
require_confirmation: true
triggers:
  human: grill
  agent: skip
  escalation: grill
skip_when_precise: true
```

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| Interrogation fatigue | Limits per turn and per session; defaults on every question |
| Questions the code could answer | Prompt rule; the consumer supplies `context`. Fixture F4 |
| Grilling an agent handoff | Trigger rule; fixture F2 |
| Person never replies | Timeout; proceed on defaults only if configured, otherwise block and notify |
| Leading questions | Style rule; reviewed in fixtures |
| Summary hides unanswered items | Unanswered questions must appear under Assumptions with the question ID |
| Scope inflation through questions ("do you also want X?") | Prompt forbids proposing extras; `out_of_scope` lists declined ones |

## 8. Fixtures and Acceptance Criteria

### 8.1 Fixtures

| ID | Input | Expected |
|----|-------|----------|
| F1 | Human: "build a reporting feature" | Ask: at most 3 questions covering users, success criteria, and constraints; each with a default |
| F2 | Origin `agent` | `action: skip`, reason `already_assigned` |
| F3 | Human: "fix typo in README line 4: 'teh' to 'the'" | `skip`, reason `precise` |
| F4 | Human request whose answer is in the supplied `context` | The answered question is not asked |
| F5 | Greenfield request | Asks `vision`; does not ask `integration` |
| F6 | Brownfield request | Asks `integration`; does not ask `vision` |
| F7 | Eleven distinct unknowns | Stops at the limit; remaining unknowns are assumptions in the summary |
| F8 | No reply within timeout (`proceed_on_defaults`) | Summary with `confirmed_by_user: false` and all defaults listed |
| F9 | Origin `escalation` | Grills, with questions about the blocker |

### 8.2 Acceptance criteria

1. F1 to F9 produce the expected action and question properties.
2. No turn has more than 3 questions, and no session more than `max_questions`.
3. Every question carries a non-empty `default`.
4. Every summary validates against `summary.json`, and each assumption cites a question ID.
5. Run on the same transcript, the decision to skip is stable.
6. The summary alone is enough for the [Analyst](../specialist-agents/README.md) to start without re-asking anything already answered (checked by feeding the summary and verifying `open_questions` contains none that the summary answers).

## 9. How UMAS Uses It

| UMAS concept | Mapping |
|--------------|---------|
| Grilling versus propulsion, resolved as Conditional (PRD Conflict 2) | Trigger rule 5.1 |
| Human to agent: grill; agent to agent: execute | `origin` |
| `coordinator.grilling` (`max_questions: 10`, `timeout: 300s`) | `max_questions`, `timeout_seconds` |
| Escalations: grill at the escalation point | `origin: escalation` |
| `_conduct_grilling` (unimplemented stub) | This pack is the missing design |
| Request through the CLI | CLI relays questions and returns answers; the pack is not aware of it |

## 10. Source Material and Deviations

Extracted from PRD Conflict 2, `TECHNICAL-DESIGN-SPEC-PART2.md` (`CoordinatorAgent` grilling config and the `_conduct_grilling` placeholder), and `UMAS-TECH-DESIGN-SPEC.md` §3.2.

| Deviation | Why |
|-----------|-----|
| Skip when the request is already precise | The source grills every human request, which is costly for trivial ones. Not in the source; flagged as a proposal |
| Defaults on every question | The source has no non-response behaviour beyond a timeout value |
| Three questions per turn | Keeps the session answerable on a phone or in a CLI |
| Brownfield and greenfield topic split | The PRD comparison table gives different grilling aims; this makes it a rule |
| Alignment summary schema | The source says grilling produces alignment, with no artifact |
| Timeout behaviour configurable | Proceeding on defaults versus blocking is a trade-off the source does not settle |

## 11. Open Questions

1. Does the "precise request" skip fit the intended experience? The PRD stresses alignment for human requests; skipping may feel inconsistent.
2. When timeout expires and work proceeds on defaults, should the summary still be shown to the person afterward? This spec says yes, informational only.
3. Can a grilling session be resumed after hours (stateful)? The transcript input makes it possible; storage is the consumer's.
