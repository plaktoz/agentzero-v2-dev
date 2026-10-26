# minimalism-ladder

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](../README.md)
> **Independence:** no dependency on UMAS or any tool. A prompt, a rule set, and a record format.
> `pack_version: 0.1.0`

---

## 1. Purpose

Make a coding agent solve the problem before it writes code. The agent reads the relevant code, then walks six questions in order and stops at the first one that settles the task. The result is less code, more reuse, and a record of why.

## 2. Scope and Non-Goals

**In scope**
- The six-rung ladder and its stop rule
- The "read first" precondition
- The shortcut comment format for deliberate deferrals
- Three enforcement levels (lite, full, ultra)
- A short record the agent emits so a reviewer can check the reasoning
- Metrics definitions

**Non-goals**
- Reading, scoping, or analysing the task. The ladder is explicitly lazy about the solution and never about reading or scope analysis.
- Judging design quality. That is the Architect's and the reviewers' job.
- Tracking debt. The format is defined here; a scanner is [decision-artifacts](../../libs/decision-artifacts/README.md).
- Guaranteeing savings. See 10 for the unverified claims.

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Prompt (5.1), rules (5.2 to 5.4), level definitions (5.5) |
| `schema/ladder-record.json` | Output record (4.2) |
| `fixtures/*.yaml` | F1 to F8 (8) |
| `config.yaml` | `level`, `enforce`, `record` (section 6) |

## 4. Contract

### 4.1 Input

```text
task:            string   what was asked
code_context:    string[] paths or excerpts the agent has already read
project_notes:   string?  conventions, stack, installed dependencies
level:           lite | full | ultra
```

`code_context` must be non-empty for the pack to apply. If the agent has read nothing, the prompt tells it to read first.

### 4.2 Output (ladder record)

```json
{ "pack_version": "0.1.0",
  "rung": 1,
  "rung_name": "not_needed | exists_in_codebase | stdlib_or_platform | installed_dependency | one_line | minimum_code",
  "evidence": ["path/or/symbol that proves it"],
  "decision": "skip | reuse | use_builtin | use_dependency | write_one_line | write_minimum",
  "loc_estimate": 0,
  "shortcuts": [ { "what": "...", "fix_when": "..." } ],
  "notes": "optional, one sentence" }
```

`rung` is the rung at which the agent stopped. `evidence` is mandatory for rungs 1 to 4.

## 5. The Rules and Prompt

### 5.1 Prompt

```text
You solve before you write. Read the relevant code and trace the real flow first.
Then ask these questions in order and stop at the first one that holds:

1. Does this need to exist? If it was not asked for, do not build it.
2. Does it already exist in this codebase? If so, reuse it.
3. Is it in the standard library or the platform? If so, use that.
4. Is it in a dependency that is already installed? If so, use that.
5. Can it be done in one readable line? If so, write the line.
6. Otherwise write the minimum code that works.

Being lazy about the solution does not permit skipping the reading or
the scope analysis. Do those fully. Do not add abstraction, options, or
fallbacks that the task did not ask for.

Comments: write one only when the reason for the code is non-obvious.
The single exception is a deliberate deferral, written exactly as
  SHORTCUT: <what was deferred> -- <when to fix>
using the language's comment syntax.

When done, report the rung where you stopped and the evidence for it.
```

### 5.2 Stop rule

Stop at the **first** rung that holds. Do not continue to a later rung "to be safe". Moving past a rung needs a stated reason in `notes` (for example, "existing helper handles UTC only; task needs local time").

### 5.3 Read-first precondition

The ladder runs after the agent has read the files that the change touches and the call sites it would affect. An agent that has not read them MUST read them before answering rung 2, because rung 2 cannot be answered without it. The shortcut is the solution, never the investigation.

### 5.4 Shortcut comment

```text
// SHORTCUT: sync call to avoid queue setup -- revisit before 100 users
```

Both parts are required. The separator is an em dash, `--`, or a spaced hyphen. It is the only comment that does not explain why the code exists. Decorative, redundant, and narrating comments are not permitted. A malformed shortcut is a review finding.

### 5.5 Levels

The source names the levels but does not define them. This pack defines them as follows (proposal; see 10).

| Level | Enforcement |
|-------|-------------|
| `lite` | Rungs 1 and 2 are checked and the record is emitted. Later rungs are advice. The reviewer does not block |
| `full` (default) | All six rungs. A change that adds code where an earlier rung holds is a finding. Record required |
| `ultra` | As `full`, plus: a new file, dependency, or public abstraction needs a one-line justification in `notes`, and the agent first proposes a deletion or simplification of existing code if one reduces the change |

### 5.6 Metrics

| Metric | Definition |
|--------|------------|
| `code_avoided` | Estimated lines the task would have taken without the ladder, minus `loc_estimate` |
| `reuse_percent` | Tasks that stopped at rungs 2 to 4, divided by all tasks |
| `lines_saved` | Measured: lines in the change compared with a baseline run, where a baseline exists |

`code_avoided` is an estimate and is labelled as one wherever it is shown.

## 6. Configuration

```yaml
level: full            # lite | full | ultra
enforce: true          # reviewers treat a missed rung as a finding
record: true           # agent emits the ladder record
shortcut:
  marker: "SHORTCUT:"
require_evidence_rungs: [1, 2, 3, 4]
```

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| Agent skips reading and claims rung 2 "does not exist" | Fixture F4. Reviewer checks `evidence` against the repo; missing evidence is a finding |
| Over-minimalism: omits needed validation or error handling | The ladder only bounds new code. Behaviour the task requires is part of "minimum code that works". Fixture F7 |
| Ladder treated as permission to refuse work | Rung 1 applies only to what was **not asked**. A requested feature is never rung-1-skipped |
| Hallucinated reuse ("there is a helper for this") | `evidence` must be a real path or symbol. A script can verify it exists |
| Savings claimed without a baseline | Report `code_avoided` as an estimate only |

## 8. Fixtures and Acceptance Criteria

### 8.1 Fixtures

| ID | Input | Expected property |
|----|-------|-------------------|
| F1 | "Add a date picker" in a web app; browser input type date available; no picker component exists | Stops at rung 3 (platform). Output is a native date input, about 10 lines, not a 300-line component. The source reports 335 lines reduced to 10 |
| F2 | "Add a retry helper"; repo already has `retry()` in `util/retry.py` | Stops at rung 2, `evidence` names `util/retry.py`, no new helper |
| F3 | "Format a date as YYYY-MM-DD"; stdlib has it | Rung 3 or 5, no dependency added |
| F4 | Agent has read nothing, task touches `auth/` | Agent reads before answering; a record with empty `evidence` for rung 2 is invalid |
| F5 | "Parse this CSV"; a CSV library is already in the lockfile | Stops at rung 4, no second parser |
| F6 | Feature not asked for appears in the plan ("also add caching") | Rung 1: dropped, recorded in `notes` |
| F7 | Task requires input validation | Validation is written; the ladder does not remove it |
| F8 | A deferral is needed | Comment matches the shortcut format; a version lacking "when to fix" is rejected |

### 8.2 Acceptance criteria

1. For F1 to F8 the output satisfies the expected property, judged by a person on the first release and by a script where the property is checkable (evidence exists, shortcut well formed, no new dependency in `package.json` or lockfile).
2. The record validates against `ladder-record.json`.
3. Under `lite` the agent emits the record and no change is rejected for ladder reasons.
4. Under `ultra`, F1 additionally prompts a one-line justification for any new file.
5. Across a set of 20 realistic tasks, the median diff size with the pack is no larger than without. The source claims 53 percent less code, 26 percent less cost, and 41 percent less time; these are **unverified** and this criterion does not require them.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| "Minimalism ladder enforced before any code is written" | This pack is prepended to the Developer and Worker prompts |
| `project.minimalism.level`, `enforce` | `level`, `enforce` |
| `MinimalismEnforcer` rungs 1 and 2, 6 | Implemented by the prompt; rungs 3 to 5 were stubs in code and need no code now |
| Shortcut comments tracked in a debt ledger | Format here; scanner in decision-artifacts |
| `metrics minimalism` | Computed from stored ladder records |
| Router tiers | Ladder applies at every tier, including simple direct workers |

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.3, `TECHNICAL-DESIGN-SPEC-PART3.md` (`_build_prompt_with_ladder`, `MinimalismEnforcer`), and the PRD (minimalism, decision point 5).

| Deviation | Why |
|-----------|-----|
| Levels defined here | The source lists lite, full, ultra and recommends full as the default, but never says what differs |
| Output record added | The source gives no way to check that the ladder ran; a record makes the reasoning auditable |
| Evidence required | A claim of reuse with no pointer is the typical hallucination |
| "Rung 1 never skips a requested feature" stated | Prevents the ladder being used to refuse work |
| Savings figures marked unverified | The 53, 26, and 41 percent figures have no stated baseline or sample |
| Enforcer code not specified | Rungs 3 to 5 were stubs; an LLM prompt covers them. A future static checker can be added without changing this pack |

## 11. Open Questions

1. Do the savings figures come from an experiment? If so, add the method as a fixture set; if not, drop them from user-facing material.
2. Should the ladder record be stored with the commit (trailer) or beside it? Storage is the consumer's choice, but a default helps.
3. Is a static pre-merge check for rung 4 (installed dependency) worthwhile, given it needs a per-language manifest parser?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Example code illustrating one way to implement this spec. May use consumer-specific names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [packs/README.md](../README.md).

### 12.1 MinimalismEnforcer (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §5.4.2

```python
from typing import Optional, List
from enum import Enum

class LadderRung(Enum):
    DOES_IT_NEED_TO_EXIST = 1
    ALREADY_IN_CODEBASE = 2
    STANDARD_LIBRARY = 3
    INSTALLED_DEPENDENCY = 4
    ONE_LINE = 5
    MINIMUM_CODE = 6

@dataclass
class LadderResult:
    rung: LadderRung
    rationale: str
    solution: Optional[str]
    code_avoided: bool

class MinimalismEnforcer:
    def __init__(self, codebase_analyzer: CodebaseAnalyzer):
        self.codebase_analyzer = codebase_analyzer
        
    async def climb_ladder(
        self,
        requirement: str,
        context: Dict,
    ) -> LadderResult:
        """Climb minimalism ladder to find minimal solution."""
        
        # Rung 1: Does it need to exist?
        if not await self._is_required(requirement, context):
            return LadderResult(
                rung=LadderRung.DOES_IT_NEED_TO_EXIST,
                rationale="Feature not explicitly requested",
                solution=None,
                code_avoided=True,
            )
        
        # Rung 2: Already in codebase?
        existing = await self._find_in_codebase(requirement)
        if existing:
            return LadderResult(
                rung=LadderRung.ALREADY_IN_CODEBASE,
                rationale=f"Reuse existing: {existing}",
                solution=existing,
                code_avoided=True,
            )
        
        # Rung 3: Standard library?
        stdlib = await self._find_in_stdlib(requirement)
        if stdlib:
            return LadderResult(
                rung=LadderRung.STANDARD_LIBRARY,
                rationale=f"Use standard library: {stdlib}",
                solution=stdlib,
                code_avoided=True,
            )
        
        # Rung 4: Installed dependency?
        dependency = await self._find_in_dependencies(requirement)
        if dependency:
            return LadderResult(
                rung=LadderRung.INSTALLED_DEPENDENCY,
                rationale=f"Use installed dependency: {dependency}",
                solution=dependency,
                code_avoided=True,
            )
        
        # Rung 5: Can it be one line?
        one_liner = await self._try_one_line(requirement)
        if one_liner:
            return LadderResult(
                rung=LadderRung.ONE_LINE,
                rationale="One clear line solution",
                solution=one_liner,
                code_avoided=False,
            )
        
        # Rung 6: Minimum code
        return LadderResult(
            rung=LadderRung.MINIMUM_CODE,
            rationale="Write minimum code that works",
            solution=None,
            code_avoided=False,
        )
    
    async def _is_required(self, requirement: str, context: Dict) -> bool:
        """Check if feature is explicitly requested."""
        # Implementation: Analyze if requirement is in user request
        return True
    
    async def _find_in_codebase(self, requirement: str) -> Optional[str]:
        """Search for existing implementation in codebase."""
        results = await self.codebase_analyzer.search(requirement)
        if results:
            return results[0].path
        return None
    
    async def _find_in_stdlib(self, requirement: str) -> Optional[str]:
        """Check if standard library provides solution."""
        # Implementation: Check language standard library
        return None
    
    async def _find_in_dependencies(self, requirement: str) -> Optional[str]:
        """Check if installed dependency provides solution."""
        dependencies = await self.codebase_analyzer.get_dependencies()
        # Implementation: Search dependency documentation
        return None
    
    async def _try_one_line(self, requirement: str) -> Optional[str]:
        """Try to solve with one clear line."""
        # Implementation: Generate one-line solution
        return None
```

### 12.2 Minimalism configuration (YAML)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §5.4.3

```yaml
minimalism_config:
  enforcement_level: full  # lite, full, ultra
  
  ladder:
    enabled: true
    require_rationale: true
    log_decisions: true
    
  metrics:
    track_code_avoided: true
    track_reuse_percentage: true
    track_lines_saved: true
```
