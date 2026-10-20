# specialist-agents

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](./README.md)
> **Independence:** no dependency on UMAS or on any orchestrator. Five role prompts, each with a defined input and output document.
> `pack_version: 0.1.0`

---

## 1. Purpose

Give an agent harness five narrow roles (Analyst, Product Manager, UX Designer, Architect, Developer) so that complex work is shaped before it is built. Each role has a prompt, one output document with a schema, and a rule for when it may be skipped.

## 2. Scope and Non-Goals

**In scope**
- A prompt per role, written to the depth the source lacked
- A structured output for each role, so the next role can consume it
- The default sequence for complex work, and skip conditions
- A guard against inventing unstated requirements

**Non-goals**
- Choosing which roles to run. See [router-heuristic](../router-heuristic/README.md).
- Persisting the artifacts. A library such as [decision-artifacts](../../libs/decision-artifacts/README.md) can write the files; this pack only produces content.
- Running a loop or tool execution. The pack is text.
- Multi-model panels. That is orchestration; this pack gives one role's prompt, usable in a panel.

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Common preamble (5.1) and five role prompts (5.2 to 5.6) |
| `schema/<role>.json` | Output schema per role |
| `fixtures/*.yaml` | F1 to F10 |
| `config.yaml` | Enabled roles, sequence, skip rules |

## 4. Contract

### 4.1 Common input

```text
request:        string        the user's ask or the previous role's hand-off
prior:          object[]      outputs from earlier roles, in order
codebase_notes: string?       relevant structure, stack, conventions
alignment:      string?       summary from a grilling session, if one occurred
```

### 4.2 Role outputs

| Role | Output (fields) |
|------|-----------------|
| Analyst | `restated_request`, `assumptions[]`, `open_questions[{question, why_it_matters, default_if_unanswered}]`, `ambiguities[]`, `out_of_scope[]`, `ready: bool` |
| Product Manager | `press_release` (headline, summary, problem, solution, quote?), `faq[{q, a}]`, `user_stories[{as_a, i_want, so_that, acceptance[]}]`, `success_metrics[{metric, target, how_measured}]` |
| UX Designer | `flows[{name, steps[]}]`, `wireframes[{screen, text_layout}]`, `components[{name, states[], notes}]`, `interactions[]`, `accessibility_notes[]` |
| Architect | `decision` (ADR: context, decision, consequences, alternatives), `stack[{choice, reason, installed_already: bool}]`, `api_contracts[]`, `data_models[]`, `risks[]` |
| Developer | `plan[]`, `ladder_record` (see [minimalism-ladder](../minimalism-ladder/README.md)), `changes[]`, `tests[{target, why}]`, `shortcuts[]`, `unresolved[]` |

Every output includes `role`, `pack_version`, and `based_on` (IDs of prior outputs it used).

## 5. The Rules and Prompt

### 5.1 Common preamble

```text
You are the {{role}} on a small team. Do only your role's work.
Use the prior outputs as given; do not redo another role's job.
Never invent a requirement. If something needed is not stated, record it
as an open question with a default you would use, and continue.
Be concrete: name files, fields, numbers. Skip generic advice.
Return the structured output for your role and nothing else.
```

### 5.2 Analyst

```text
Clarify what is being asked before anyone builds it.
Restate the request in one or two sentences. List assumptions you are
making. Surface ambiguity as questions, each with why the answer matters
and the default you will use if unanswered. State what is out of scope.
Set ready=true only when no open question would change the design.
Do not propose a solution.
```

### 5.3 Product Manager

```text
Define the user value. Write the press release as if the change shipped:
headline, summary, the problem, the solution. Write the FAQ a skeptic
would ask. Write user stories with acceptance criteria that can be
checked. Give success metrics with a target and how each is measured.
Do not choose technology or design screens.
```

### 5.4 UX Designer

```text
Design the interaction. Describe the flows step by step. Draw each screen
as a text wireframe. List components with their states (default, loading,
error, empty, disabled). Note interaction patterns and accessibility
requirements. Reuse existing components where the notes show they exist.
Do not decide data models or back-end design.
```

### 5.5 Architect

```text
Make the technical decisions and record why. Write one decision record:
context, decision, consequences, alternatives considered. Prefer what is
already installed and what is already in the codebase; mark each stack
choice with whether it is already present. Define API contracts and data
models. List risks. Do not write implementation code.
```

### 5.6 Developer

```text
Implement the task. First run the minimalism ladder: read the relevant
code, then stop at the first rung that holds, and report the ladder
record. Plan, then change the code. Add tests for risky logic only
(branches, loops, parsers, money, security). Mark any deliberate deferral
with a SHORTCUT comment. List anything you could not resolve.
Do not expand scope.
```

### 5.7 Sequence and skipping

Default order for complex or greenfield work:

```text
Analyst -> Product Manager -> UX Designer -> Architect -> Developer
```

| Role | Skip when |
|------|-----------|
| Analyst | Request is a single, unambiguous change with a cited location |
| Product Manager | Not new user-facing value (internal change, bug fix) |
| UX Designer | No user interface involved |
| Architect | Change fits an existing pattern with no new component, dependency, or contract |
| Developer | Never skipped when code must change |

A skipped role is recorded as `skipped: reason` so later roles know the gap is deliberate.

### 5.8 Hand-off rule

The next role receives the structured output, not the earlier conversation. A role that finds the prior output insufficient returns `needs: [<role>, <what>]` rather than guessing.

### 5.9 Prompt depth

The source's role prompts are four or five lines and the code assumes structured fields that no schema defined. These prompts are the minimum that makes the outputs checkable; they should stay short, and each rule has a fixture that justifies it. Rules without a fixture are candidates to delete.

## 6. Configuration

```yaml
roles: [analyst, product_manager, ux_designer, architect, developer]
sequence: [analyst, product_manager, ux_designer, architect, developer]
skip_rules:
  analyst: "single_unambiguous_change"
  product_manager: "no_new_user_value"
  ux_designer: "no_ui"
  architect: "fits_existing_pattern"
require_ready_before_next: true     # Analyst ready=true or defaults accepted
max_open_questions: 7
```

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| Role invents a requirement | Preamble rule; fixture F2. An `assumptions` entry is acceptable; a hidden one is a defect |
| Roles duplicate each other (Architect re-does PM) | Each prompt ends with "do not ..."; reviewer can check by field presence |
| Output not valid for its schema | Consumer rejects and retries once with the schema error; a second failure escalates |
| Analyst never reaches `ready` | `max_open_questions` and `default_if_unanswered` let work proceed on stated defaults |
| Overlong planning for a small task | Skip rules and [router-heuristic](../router-heuristic/README.md); fixture F9 |
| Architect over-engineers | Prompt prefers existing choices and marks `installed_already`; ladder applies to design too |
| Developer ignores prior decisions | `based_on` must list the ADR it follows; reviewer checks consistency |

## 8. Fixtures and Acceptance Criteria

### 8.1 Fixtures

| ID | Role and input | Expected |
|----|----------------|----------|
| F1 | Analyst: "make login better" | `ready: false`; at least 2 open questions each with a default; no solution proposed |
| F2 | Analyst: "add export" with no format given | Format listed as an open question; none chosen silently |
| F3 | PM: "invite teammates by email" | Press release, at least 3 FAQ items, stories each with checkable acceptance, at least 1 metric with target and method |
| F4 | UX: same feature | Flow for invite, error and empty states named for each component, text wireframe present |
| F5 | Architect: new service for email invites; a mail library is already installed | Stack choice marks that library `installed_already: true`; ADR has alternatives |
| F6 | Developer: small utility needed; helper exists in repo | Ladder record stops at rung 2; no new helper |
| F7 | Developer: change touching a parser | `tests` lists the parser cases; formatting-only change in same task has none |
| F8 | Developer: prior ADR picks library X | Output cites the ADR; does not use library Y |
| F9 | Typo fix with file and line cited | Sequence reduces to Developer; skipped roles recorded with reasons |
| F10 | Any role given an output of the wrong shape from the prior role | Returns `needs:` rather than guessing |

### 8.2 Acceptance criteria

1. Each role's output for F1 to F8 validates against its schema.
2. F1 and F2 contain no decision the input did not make or the defaults list record.
3. F5 and F6 contain no new dependency or helper where an existing one was available.
4. F9 produces the reduced sequence and records every skip reason.
5. The hand-off from each role to the next works with only the structured output (the next role is run on the output with the conversation removed, and still produces a valid result).
6. The full five-role sequence on one sample request yields consistent artifacts (the Developer's changes satisfy the PM's acceptance criteria and the Architect's contracts), checked by a person on the first release.

## 9. How UMAS Uses It

| UMAS concept | Mapping |
|--------------|---------|
| Specialized Agents table (Analyst, PM, Architect, UX, Developer) | The five prompts here |
| Router decides which are invoked | [router-heuristic](../router-heuristic/README.md) output selects the sequence; skip rules supply defaults |
| PM writes PRFAQ; Architect writes ADR | Outputs are passed to decision-artifacts `create`; filenames and numbers are its concern |
| Developer enforces the minimalism ladder | Ladder prompt is part of the Developer's preamble |
| `response.prfaq` fields in the source code | Replaced by the PM schema; the LLM client no longer needs fields it does not define |
| Panel of diverse models for irreversible decisions | The same role prompt sent to N models; synthesis is orchestration, not part of this pack |

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.3 (Specialized Agents), `TECHNICAL-DESIGN-SPEC-PART3.md` (five agent classes), and the PRD agent sections.

| Deviation | Why |
|-----------|-----|
| Output schemas defined | The source code reads `response.prfaq` and similar fields that the LLM client never defined |
| Prompts expanded from 4 or 5 lines | Too short to produce the structured output the code expects |
| Skip rules per role | The source says "invoked by the Router" without per-role conditions |
| `needs` hand-off | The source has no rule for a role receiving insufficient input |
| `installed_already` flag | Carries the minimalism ladder into design decisions |
| No role named "Reviewer" or "Tester" | They belong to [two-axis-review](../two-axis-review/README.md) and [test-policy](../test-policy/README.md) |

## 11. Open Questions

1. Is a separate Analyst needed when a grilling session has already produced an alignment summary? Overlap is likely; see [grilling](../grilling/README.md).
2. Should the Developer role be one prompt, or split by language or task type? The source has one.
3. Do prompts need per-model tuning? This spec assumes none.

---

## 12. Reference Implementation (Source Code)

> Non-normative. Code moved verbatim from the original UMAS technical design. It illustrates one way to implement this spec and uses UMAS names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [packs/README.md](./README.md).

### 12.1 Specialized agents (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §5.3.2

```python
from abc import ABC, abstractmethod

class SpecializedAgent(ABC):
    def __init__(self, config: AgentConfig, llm_client: LLMClient):
        self.config = config
        self.llm_client = llm_client
    
    @abstractmethod
    async def execute(self, input_data: Dict) -> Dict:
        """Execute specialized agent task."""
        pass

class ProductManagerAgent(SpecializedAgent):
    """Defines user needs and product decisions."""
    
    async def execute(self, input_data: Dict) -> Dict:
        """Create PRFAQ and define product requirements."""
        
        prompt = f"""
You are a Product Manager. Define product requirements for:
{input_data['request']}

Create:
1. Press Release (user perspective)
2. FAQ (common questions)
3. User stories
4. Success metrics
"""
        
        response = await self.llm_client.generate(
            prompt=prompt,
            model=self.config.model,
        )
        
        return {
            "prfaq": response.prfaq,
            "user_stories": response.user_stories,
            "success_metrics": response.success_metrics,
        }

class ArchitectAgent(SpecializedAgent):
    """Designs technical architecture and system design."""
    
    async def execute(self, input_data: Dict) -> Dict:
        """Design system architecture."""
        
        prompt = f"""
You are a Software Architect. Design architecture for:
{input_data['product_requirements']}

Provide:
1. System architecture diagram
2. Technology stack choices (with rationale)
3. ADR for key decisions
4. API contracts
5. Data models
"""
        
        response = await self.llm_client.generate(
            prompt=prompt,
            model=self.config.model,
        )
        
        return {
            "architecture": response.architecture,
            "tech_stack": response.tech_stack,
            "adrs": response.adrs,
            "api_contracts": response.api_contracts,
        }

class UXDesignerAgent(SpecializedAgent):
    """Designs user experience and interfaces."""
    
    async def execute(self, input_data: Dict) -> Dict:
        """Design user experience."""
        
        prompt = f"""
You are a UX Designer. Design user experience for:
{input_data['product_requirements']}

Provide:
1. User flows
2. Wireframes (text description)
3. Component specifications
4. Interaction patterns
"""
        
        response = await self.llm_client.generate(
            prompt=prompt,
            model=self.config.model,
        )
        
        return {
            "user_flows": response.user_flows,
            "wireframes": response.wireframes,
            "components": response.components,
        }

class DeveloperAgent(SpecializedAgent):
    """Implements code with minimalism enforcement."""
    
    async def execute(self, input_data: Dict) -> Dict:
        """Implement feature with minimalism."""
        
        prompt = f"""
You are a Developer. Implement:
{input_data['specification']}

Architecture: {input_data['architecture']}
UX Design: {input_data['ux_design']}

Apply minimalism ladder before writing code.
Write tests for risky logic.
"""
        
        response = await self.llm_client.generate(
            prompt=prompt,
            model=self.config.model,
        )
        
        return {
            "code": response.code,
            "tests": response.tests,
            "documentation": response.documentation,
        }

class AnalystAgent(SpecializedAgent):
    """Clarifies requirements through grilling sessions."""
    
    async def execute(self, input_data: Dict) -> Dict:
        """Conduct grilling session."""
        
        prompt = f"""
You are a Business Analyst. Clarify requirements for:
{input_data['request']}

Ask probing questions to understand:
1. User needs
2. Success criteria
3. Constraints
4. Edge cases
"""
        
        response = await self.llm_client.generate(
            prompt=prompt,
            model=self.config.model,
        )
        
        return {
            "questions": response.questions,
            "clarifications": response.clarifications,
        }
```

### 12.2 Specialized agents configuration (YAML)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §5.3.3

```yaml
specialized_agents:
  product_manager:
    model: claude-3-5-sonnet-20241022
    token_limit: 100000
    role: "Product Manager"
    
  architect:
    model: claude-3-5-sonnet-20241022
    token_limit: 150000
    role: "Software Architect"
    
  ux_designer:
    model: claude-3-5-sonnet-20241022
    token_limit: 100000
    role: "UX Designer"
    
  developer:
    model: claude-3-5-sonnet-20241022
    token_limit: 200000
    role: "Developer"
    minimalism_enforced: true
    
  analyst:
    model: claude-3-5-sonnet-20241022
    token_limit: 80000
    role: "Business Analyst"
```
