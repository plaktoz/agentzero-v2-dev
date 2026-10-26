# two-axis-review

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](../README.md)
> **Independence:** no dependency on UMAS or any code host. Input is a diff plus a statement of intent; output is a list of findings.
> `pack_version: 0.1.0`

---

## 1. Purpose

Review a change on two independent axes so that "well written" is never mistaken for "does the right thing". One reviewer checks **Standards** (how the code is written). A second checks **Spec** (whether it solves the stated problem). They run separately, use one finding format, and feed one severity gate.

## 2. Scope and Non-Goals

**In scope**
- Two reviewer prompts and their separate checklists
- A finding schema where every finding carries a concrete fix
- A severity scale and a gate policy
- A production-impact checklist for risky changes
- Merge of the two result sets into one report

**Non-goals**
- Running tests or static analysers. The reviewer may be given their output as input, but does not run them.
- Approving or merging. The pack returns findings and a gate recommendation; the consumer acts.
- Architecture review of a design that does not yet exist. See [specialist-agents](../specialist-agents/specialist-agents-spec.md)
- Style enforcement that a formatter can do

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Standards prompt (5.1), Spec prompt (5.2), production checklist (5.4), gate (5.6) |
| `schema/finding.json`, `schema/review.json` | Finding and merged report |
| `fixtures/*.yaml` | F1 to F9 |
| `config.yaml` | Axes, severities, gate thresholds |

## 4. Contract

### 4.1 Input

```text
diff:           unified diff or list of changed files with context
intent:         string      the task statement, requirements, or linked acceptance criteria
conventions:    string?     project style rules, if any
test_results:   object?     summary from a test run, if available
risk_flags:     string[]?   any of: load, security, data_migration, money, external_api
```

The **Spec** reviewer cannot work without `intent`. If it is empty the Spec pass returns a single finding `missing_intent` and no others.

### 4.2 Finding

```json
{ "id": "S-3",
  "axis": "standards | spec",
  "severity": "critical | high | medium | low | info",
  "location": "path/file.py:42-57",
  "what": "the code or behaviour in question",
  "problem": "why it is wrong or risky",
  "fix": "a concrete change that resolves it",
  "consequence": "what happens if it is left",
  "confidence": "high | medium | low" }
```

All of `location`, `what`, `problem`, `fix`, and `consequence` are mandatory. **A candidate finding with no concrete fix is not filed.** It may be raised as a question in `notes`, which has no severity.

### 4.3 Report

```json
{ "pack_version": "0.1.0",
  "findings": [ ... ],
  "notes": [ "questions or observations without a fix" ],
  "gate": { "recommend": "block | warn | pass", "reasons": ["S-3 critical"] } }
```

## 5. The Rules and Prompt

### 5.1 Standards reviewer prompt

```text
You review the quality of a change. You are not judging whether it solves
the right problem; another reviewer does that.

Check: code quality, style against the stated conventions, patterns,
maintainability, performance, security, error handling, and test coverage
of risky logic (branches, loops, parsers, money, security).

For every problem file a finding with: location, what, problem, fix,
consequence, severity. If you cannot state a concrete fix, do not file it;
put it in notes as a question.

Do not report anything a formatter would change. Do not report taste.
Do not repeat the same root cause as several findings; file it once and
list the other locations.
```

### 5.2 Spec reviewer prompt

```text
You review whether a change does what was asked. You are not judging code
style; another reviewer does that.

Using the intent, check: it solves the right problem; every stated
requirement is met; edge cases implied by the requirements are handled;
nothing outside the requested scope was added (scope creep);
nothing requested is missing.

For every gap file a finding with: location, what, problem, fix,
consequence, severity. Cite the requirement text that is not met.
If you cannot state a concrete fix, do not file it; put it in notes.
```

### 5.3 Independence

The two passes run with the same diff and separate prompts. Neither sees the other's findings before finishing. This avoids a reviewer being anchored by the other's list; the merge happens afterwards. The consumer may run them concurrently.

### 5.4 Production-impact checklist (risk-flagged changes)

When `risk_flags` is non-empty, the Standards reviewer also answers, as findings where there is a gap:

1. **Load:** what happens at ten times expected traffic or data volume?
2. **Security:** what can an attacker control? Is input validated, are secrets handled, is access checked?
3. **Failure behaviour:** what happens when each dependency is down or slow?
4. **Error handling:** are errors surfaced with enough context to diagnose, and never swallowed?
5. **Rollback:** can the change be reverted, and what about data it already wrote?
6. **What to cut:** which part is not needed to meet the requirement?

### 5.5 Severity

| Severity | Meaning | Example |
|----------|---------|---------|
| critical | Exploitable, data loss, or breaks a core path in production | SQL built by string concatenation from user input |
| high | Likely bug or requirement not met | Required behaviour absent |
| medium | Real weakness with workaround | Missing test for a money calculation |
| low | Minor quality issue | Unclear name |
| info | Observation | Possible follow-up |

### 5.6 Gate

| Highest severity found | Recommendation |
|------------------------|----------------|
| critical or high | `block` |
| medium | `warn` |
| low or info only | `pass` |

Thresholds are configuration. The pack **recommends**; it never merges.

Ordering rule: findings are ordered by a fixed rank table (critical 0, high 1, medium 2, low 3, info 4), never by sorting the severity strings, which sort alphabetically (`critical, high, info, low, medium`) and would place `info` above `medium`.

### 5.7 Merge

Concatenate both lists. If two findings share a `location` and the same root cause, keep one, set its `axis` to `both`, and raise the severity to the higher of the two. Order by severity rank, then location.

## 6. Configuration

```yaml
axes: [standards, spec]
severity_rank: { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
gate:
  block_on: [critical, high]
  warn_on:  [medium]
require_fix: true
production_checklist: true
max_findings_per_axis: 25
```

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| Findings without fixes | Rejected by schema; moved to `notes` |
| Diff too large for one pass | Consumer splits by file group and runs both axes per group. Reviewer states what it did not see |
| Spec axis with vague intent | Returns `missing_intent`; the consumer asks for acceptance criteria |
| Reviewer invents a bug | `confidence` and a quoted `what` allow a human or a test to check; fixture F8 checks false positives |
| Alphabetical severity sort | Explicit rank table (5.6); acceptance criterion 4 |
| Overlong reports hide the real issue | `max_findings_per_axis`; the reviewer ranks and drops the lowest |
| Reviewer agrees with the author's own summary | Prompt says to judge the diff against intent, not against the description of the diff |

## 8. Fixtures and Acceptance Criteria

### 8.1 Fixtures

| ID | Input | Expected |
|----|-------|----------|
| F1 | Diff builds `"SELECT * FROM users WHERE name='" + name + "'"` | One critical Standards finding at that line, fix = parameterised query, consequence = SQL injection |
| F2 | Intent: "export orders as CSV and as JSON"; diff only adds CSV | One Spec finding (high): JSON export not implemented, cites the requirement |
| F3 | Diff adds a caching layer nobody asked for | Spec finding (scope creep), fix = remove it |
| F4 | A pricing function with branches and no tests | Medium Standards finding, fix names the cases to cover |
| F5 | Clean diff matching intent | `findings: []`, `gate: pass` |
| F6 | Intent empty | Spec returns exactly `missing_intent` |
| F7 | A vague concern with no fix ("naming could be better overall") | Not a finding; at most a note |
| F8 | A correct use of a pattern that looks suspicious | No finding (false-positive check) |
| F9 | One bug seen by both axes at the same lines | One merged finding, `axis: both`, highest severity |

### 8.2 Acceptance criteria

1. F1 to F9 produce the expected finding sets (matching by location and severity, wording free).
2. Every finding in all outputs validates against `finding.json`, with all five mandatory fields non-empty.
3. A run with a critical or high finding yields `gate: block`; medium only yields `warn`; clean yields `pass`.
4. Given findings with severities `[low, critical, info, medium, high]`, the ordered output is `critical, high, medium, low, info`.
5. Standards-pass output for a given diff does not change when the Spec pass is skipped (independence).
6. On a labelled set of 20 diffs (10 with injected defects), at least 8 of 10 injected defects are found and no more than 2 false positives are filed. These counts are initial targets; they are not from the source.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| "Every PR goes through two independent review passes run in parallel" | Two calls with the prompts in 5.1 and 5.2 |
| Finding `{location, what, problem, fix, consequence}` | `finding.json` |
| `CodeReviewAgent` severity thresholds | Gate (5.6). The source code sorted on `severity.value`; replaced with rank table |
| Block merge on critical and high | The merge-queue treats `gate.recommend == block` as an unmet condition for `ready_to_merge` |
| On-call and production-impact checklist (PRD) | 5.4 |
| Test coverage under selective mode | [test-policy](../test-policy/test-policy-spec.md) classifier supplies the "risky logic" list the Standards pass checks |
| Anti-slop code rules | Standards pass may cite [anti-slop](../anti-slop/anti-slop-spec.md) 5.4 as pattern findings |

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.4 (Code Review), `TECHNICAL-DESIGN-SPEC-PART3.md` (`CodeReviewAgent`, `ReviewFinding`), and the PRD review sections.

| Deviation | Why |
|-----------|-----|
| Explicit severity rank table | The source orders findings by sorting the enum's string values, which is alphabetical, not by severity |
| `missing_intent` behaviour | The Spec axis cannot be judged without a requirement; the source assumes one always exists |
| `confidence` field | Lets a consumer deprioritise uncertain findings; not in the source |
| `axis: both` merge | The source runs two passes and does not say how overlaps are handled |
| Gate is a recommendation | The source blocks merge directly; blocking is the consumer's decision |
| Independence stated as a rule | The source says "parallel" but does not say reviewers must not see each other's findings |
| `notes` channel | A finding with no fix has nowhere to go under the source's "not filed" rule, and silently dropping is lossy |

## 11. Open Questions

1. Should a third axis (security) be separate for flagged changes, rather than part of Standards? Single reviewers lose depth when the checklist is long.
2. Should multiple reviewer models be used for critical paths (diverse panel), or is that reserved for irreversible decisions as the source says?
3. How should disagreement between review and tests be handled: a failing test and a review `pass`, or the reverse?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Example code illustrating one way to implement this spec. May use consumer-specific names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [packs/README.md](../README.md).

### 12.1 CodeReviewAgent (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §6.4.2

```python
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

class ReviewSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class ReviewFinding:
    severity: ReviewSeverity
    category: str
    file: str
    line: int
    description: str
    problem: str
    fix: str
    consequence: str

class CodeReviewAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
    async def review_pr(
        self,
        pr: PullRequest,
        diff: str,
    ) -> List[ReviewFinding]:
        """Perform two-axis code review."""
        
        # Axis 1: Standards review
        standards_findings = await self._review_standards(pr, diff)
        
        # Axis 2: Spec review
        spec_findings = await self._review_spec(pr, diff)
        
        # Combine findings
        all_findings = standards_findings + spec_findings
        
        # Sort by severity
        all_findings.sort(key=lambda f: f.severity.value)
        
        return all_findings
    
    async def _review_standards(
        self,
        pr: PullRequest,
        diff: str,
    ) -> List[ReviewFinding]:
        """Review code quality and standards."""
        
        prompt = f"""
Review this code change for standards:

{diff}

Check for:
1. Code quality and style
2. Design patterns
3. Maintainability
4. Performance
5. Security vulnerabilities
6. Error handling
7. Test coverage

For each finding, provide:
- What: The issue
- Problem: Why it's a problem
- Fix: How to fix it
- Consequence: What happens if not fixed
"""
        
        response = await self.llm_client.generate(prompt=prompt)
        findings = self._parse_findings(response, "standards")
        
        return findings
    
    async def _review_spec(
        self,
        pr: PullRequest,
        diff: str,
    ) -> List[ReviewFinding]:
        """Review against requirements."""
        
        # Get original requirement
        task = await self._get_task_for_pr(pr)
        
        prompt = f"""
Review if this code meets requirements:

Requirement: {task.description}

Code changes:
{diff}

Check:
1. Does it solve the right problem?
2. Does it meet all requirements?
3. Are there missing edge cases?
4. Is the scope correct (not over/under)?
"""
        
        response = await self.llm_client.generate(prompt=prompt)
        findings = self._parse_findings(response, "spec")
        
        return findings
```

### 12.2 Code review configuration (YAML)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §6.4.3

```yaml
code_review_config:
  model: default                  # llm-gateway alias, not a model ID
  
  standards_checks:
    - code_quality
    - design_patterns
    - security
    - performance
    - error_handling
    - test_coverage
    
  spec_checks:
    - requirements_met
    - edge_cases
    - scope_correctness
    
  severity_thresholds:
    block_merge_on: [critical, high]
    warn_on: [medium]
    info_only: [low, info]
```
