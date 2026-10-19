# router-heuristic

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](README.md)
> **Independence:** no dependency on UMAS or on any orchestrator. A scoring rubric, a band table, and a classification prompt.
> `pack_version: 0.1.0`

---

## 1. Purpose

Choose how much process a request needs. A one-line bug fix goes straight to a worker; a new system gets an architect and specialists. The pack turns request text and a cheap codebase scan into a score, a route, and a logged reason that a person can override.

## 2. Scope and Non-Goals

**In scope**
- Signals, weights, and a scoring rule
- Score bands mapped to routes
- A greenfield override
- A classification prompt that extracts signals from a request
- A deterministic scorer (so the arithmetic is not left to a model)
- The log record and a manual override

**Non-goals**
- Running the route. The consumer dispatches; the pack only returns the route name.
- Estimating effort in hours or cost
- Decomposing the work into tasks
- Selecting among models

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Classification prompt (5.2), rubric (5.1), bands (5.3) |
| `rubric.yaml` | Signals, weights, thresholds |
| `schema/signals.json`, `schema/decision.json` | Extracted signals and route decision |
| `fixtures/*.yaml` | F1 to F12 |

## 4. Contract

### 4.1 Input

```text
request:        string
scan:           { files_estimate: int?, touches_ui: bool?, notes: string? }   optional codebase hints
override:       simple | medium | large | greenfield | null
```

### 4.2 Signals (model output, validated)

```json
{ "files_affected": "one|few|many|unknown",
  "new_capability": true,
  "scope_ambiguous": false,
  "user_facing_ui": false,
  "sensitive_domain": ["security","auth","payments","data_migration"],
  "bug_with_location": false,
  "greenfield": false,
  "evidence": { "files_affected": "request names src/a.py only", "...": "..." } }
```

### 4.3 Decision

```json
{ "pack_version": "0.1.0",
  "score": 7,
  "band": "low | medium | high",
  "route": "simple | medium | large | greenfield",
  "signals": { ... },
  "reasons": ["new_capability +3", "sensitive_domain +3", "files_affected few +1"],
  "overridden": false }
```

## 5. The Rules and Prompt

### 5.1 Rubric

The source gives only High, Medium, Low weights. This pack assigns numbers (proposal; see 10).

| Signal | Condition | Points |
|--------|-----------|--------|
| files_affected | one | 0 |
| | few (2 to 5) | 1 |
| | many (6 or more) | 3 |
| | unknown | 2 |
| new_capability | new feature, system, or service | 3 |
| scope_ambiguous | no clear single entry point | 2 |
| user_facing_ui | yes | 2 |
| sensitive_domain | any of security, auth, payments, data migration | 3 (once, not per item) |
| bug_with_location | bug fix with file or line cited | -3, applied to the other signals only |

`score = sensitive_domain points + max(0, sum of all other points)`.

`bug_with_location` can cancel size and ambiguity but **never** the sensitive-domain points. A one-line fix in an authentication path still scores 3 and routes to `medium`, because a cited location says the change is small, not that it is safe.

### 5.2 Classification prompt

```text
Read the request and the scan notes. Fill in the signals object. Do not
compute a score.

For every signal give the evidence in a few words: the phrase from the
request or the scan that supports it. If a signal is not supported by
evidence, set it to false (or "unknown" for files_affected).

greenfield is true only when the request is to create a new project or
product from nothing, not when it adds a feature to an existing one.
```

### 5.3 Bands and routes

| Score | Band | Route | What the consumer does |
|-------|------|-------|------------------------|
| 0 to 2 | low | `simple` | Direct to a minimalist worker |
| 3 to 6 | medium | `medium` | Architect, then worker |
| 7 or more | high | `large` | Full specialist panel, then workers |
| any, `greenfield: true` | n/a | `greenfield` | PM, then Architect, then parallel workers |

The band thresholds (3 and 7) are configuration.

### 5.4 Override

A manual `override` replaces the route. The decision still records the computed score and `overridden: true`, so disagreement between heuristic and human can be reviewed later.

### 5.5 Deterministic scoring

The model only extracts signals; code applies 5.1 and 5.3. The same signals always give the same route, and a change to the rubric can be tested without calling a model.

### 5.6 Escalation by the worker

A route is a first guess. The consumer may re-run the router when a worker reports the task is larger than expected; the decision is logged as a new record with the reason. The route can increase and, with a note, decrease.

## 6. Configuration

```yaml
weights:
  files_affected: { one: 0, few: 1, many: 3, unknown: 2 }
  new_capability: 3
  scope_ambiguous: 2
  user_facing_ui: 2
  sensitive_domain: 3
  bug_with_location: -3
bands: { medium_at: 3, high_at: 7 }
routes: { low: simple, medium: medium, high: large, greenfield: greenfield }
default_when_unclear: medium
```

Complexity thresholds in the source (simple up to 3 files and 100 lines, medium up to 10 files and 500 lines) map to `files_affected` through the scan: one or few for simple, few for medium, many for large. The consumer may use line counts to set `files_affected` before calling.

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| Model labels signals without evidence | Prompt requires evidence; validator downgrades unsupported signals to false |
| Under-routing a risky change as simple | `sensitive_domain` adds 3 and `bug_with_location` cannot cancel it; fixture F5 |
| Over-routing small work | Bug-with-location credit and the low band; fixture F2 |
| Keyword matching misses meaning ("login" phrased differently) | The source stub used keyword triggers; this pack uses a model for signals and keeps arithmetic deterministic |
| Unknown file count | `unknown` scores 2, which leans medium without forcing high |
| Greenfield false positive | Definition in prompt; fixture F8 |
| Router disagreement loops | At most one automatic re-route per task; further changes need a person |

## 8. Fixtures and Acceptance Criteria

### 8.1 Fixtures

| ID | Request | Expected route |
|----|---------|----------------|
| F1 | "Fix the off-by-one in `pager.py` line 42" | simple (bug_with_location) |
| F2 | "Rename `getUser` to `fetchUser` in `api.ts`" | simple |
| F3 | "Add a CSV export button to the orders page" | medium (new capability 3, UI 2, few files 1 = 6) |
| F4 | "Add a billing service with Stripe webhooks" | large (new 3, sensitive 3, many 3) |
| F5 | "Fix the bug in `login.py` line 10 where the password check is skipped" | medium (sensitive 3; the -3 for a cited location does not cancel it) |
| F6 | "Make the app faster" | medium (ambiguous 2, unknown files 2 = 4) |
| F7 | "Migrate user table to add tenant_id" | medium (sensitive 3, many files 3 = 6); see Open Question 2 on whether this should be large |
| F8 | "Add a settings page" in an existing app | not greenfield |
| F9 | "Build a new habit-tracker app" | greenfield |
| F10 | F1 with `override: large` | route large, `overridden: true`, score still reported |
| F11 | Same request twice | identical decision |
| F12 | Signal extraction with an unsupported claim | Signal set false, noted |

F5 is the reason `bug_with_location` does not cancel `sensitive_domain`. With a plain sum it would score `3 - 3 = 0` and route a bug in an authentication path straight to a direct worker.

### 8.2 Acceptance criteria

1. F1 to F12 produce the expected routes.
2. For identical signals the decision is identical (deterministic).
3. Changing `bands.medium_at` in configuration changes F3's route without any prompt change.
4. Every decision lists reasons that sum to the reported score.
5. On 30 labelled historical requests, route agreement with a human labeller is at least 75 percent and no request labelled medium or large by the human is routed `simple`. (Targets are initial; the source gives none.)

## 9. How UMAS Uses It

| UMAS concept | Mapping |
|--------------|---------|
| Router scoring heuristic, `UMAS-TECH-DESIGN-SPEC.md` §3.2 | The rubric and bands here |
| `--route simple\|medium\|large\|greenfield` | `override` |
| Score logged with the work bundle record | The decision record is stored there |
| Coordinator `complexity_thresholds` config | Mapped through `files_affected` as in section 6 |
| Router stub that matches keywords and defaults to code generation | Replaced: model extracts signals, code scores |
| Routes feed [specialist-agents](specialist-agents.md) | `simple`: Developer only; `medium`: Architect, Developer; `large`: all five roles with skips; `greenfield`: PM, Architect, workers |

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.2 (Router), `TECHNICAL-DESIGN-SPEC-PART2.md` (`Router` stub, coordinator complexity config), and the PRD Conflict 1.

| Deviation | Why |
|-----------|-----|
| Numeric weights | Source has High, Medium, Low labels only, which cannot be computed |
| Model extracts signals, code scores | The source code uses keyword triggers with priorities; the design spec describes a score. Splitting the work makes both testable |
| Sensitive domain not cancellable | Found while writing fixture F5: a plain sum lets a bug fix in an auth file route straight to a worker |
| `unknown` file count scores 2 | The source scans the codebase but gives no fallback when it cannot |
| Re-route rule | Source has no way to correct a wrong route |
| Thresholds in lines and files mapped through a signal | Source has two overlapping mechanisms (heuristic and numeric thresholds) |

## 11. Open Questions

1. Is routing cost-sensitive? A large route spends more tokens; the budget could cap routes, but that is outside the pack.
2. Should a pure data migration be `large` by itself? It is risky but may touch few files. A "irreversible" signal could be added.
3. Is the codebase scan cheap enough to run every time, or only when the request is ambiguous?
4. Should the router also pick a minimalism or test level (for example `ultra` for large)? Kept out for now.

---

## 12. Reference Implementation (Source Code)

> Non-normative. Code moved verbatim from the original UMAS technical design. It illustrates one way to implement this spec and uses UMAS names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [packs/README.md](README.md).

### 12.1 Router (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART2.md` §4.3.2

```python
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class Skill:
    name: str
    description: str
    triggers: List[str]
    agent_type: str
    priority: int

class Router:
    def __init__(self):
        self.skills = self._load_skills()
        
    def _load_skills(self) -> Dict[str, Skill]:
        """Load available skills/workflows."""
        return {
            "code_generation": Skill(
                name="code_generation",
                description="Generate new code",
                triggers=["implement", "create", "add", "build"],
                agent_type="developer",
                priority=1,
            ),
            "code_review": Skill(
                name="code_review",
                description="Review code changes",
                triggers=["review", "check", "audit"],
                agent_type="reviewer",
                priority=2,
            ),
            "refactoring": Skill(
                name="refactoring",
                description="Refactor existing code",
                triggers=["refactor", "improve", "optimize", "clean"],
                agent_type="developer",
                priority=1,
            ),
            "architecture_design": Skill(
                name="architecture_design",
                description="Design system architecture",
                triggers=["design", "architect", "structure"],
                agent_type="architect",
                priority=3,
            ),
            "bug_fix": Skill(
                name="bug_fix",
                description="Fix bugs",
                triggers=["fix", "bug", "issue", "error"],
                agent_type="developer",
                priority=0,  # Highest priority
            ),
        }
    
    async def route_request(
        self,
        request: WorkRequest,
    ) -> Skill:
        """Route request to appropriate skill."""
        
        # Analyze request description
        description_lower = request.description.lower()
        
        # Find matching skills
        matches = []
        for skill in self.skills.values():
            for trigger in skill.triggers:
                if trigger in description_lower:
                    matches.append(skill)
                    break
        
        if not matches:
            # Default to code generation
            return self.skills["code_generation"]
        
        # Return highest priority match
        matches.sort(key=lambda s: s.priority)
        return matches[0]
```
