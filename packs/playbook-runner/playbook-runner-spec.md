# playbook-runner

> Standalone content-pack spec · Draft v0.1 · Part of [packs/README.md](../README.md)
> **Independence:** no dependency on UMAS or any orchestrator. A playbook is a Markdown file; this pack defines the contract that makes it machine-executable.
> `pack_version: 0.1.0`

---

## 1. Purpose

Make UMAS's workflow engine **SDD-agnostic**: any phase-gated process — spec-driven development, a production gatekeeper, an autonomous execution loop, a compliance workflow — is expressed as a **playbook** (a structured Markdown file) and executed by the system without changing any code. The system ships two built-in playbooks. Users register additional ones per project.

A playbook is not a replacement for the existing specialist-agent pipeline. It is a **wrapper** that selects and sequences which packs and agents run, where human gates appear, and what the exit condition is. The existing pipeline (`specialist-agents`, `two-axis-review`, `test-policy`, etc.) remains the implementation layer; the playbook defines the process layer above it.

---

## 2. Scope and Non-Goals

**In scope**
- A playbook schema: phases, gates, steps (each step binds to one pack, one agent role, or one lib operation), exit predicates, and escape hatches
- A runner contract: how the Coordinator reads a playbook, maps it to a work bundle, and enforces gates
- Two built-in playbooks (`production-gatekeeper` and `autonomous-loop`) specified in §5
- A registry: how users add custom playbooks per project via `umas.config.yaml`
- Mapping rules: how each playbook step corresponds to an existing pack or agent role

**Non-goals**
- A new DSL or programming language. A playbook is Markdown + YAML front matter.
- Replacing the specialist-agents pipeline. Playbook steps call it; they do not duplicate it.
- Versioning or deployment of playbooks across machines. That is the consuming application's concern.
- UI or visualisation of playbook execution.

---

## 3. Pack Contents and Format

| File | Purpose |
|------|---------|
| `PACK.md` | Runner rules (§5.1), gate definitions (§5.2), escape hatch rules (§5.3) |
| `schema/playbook.json` | Playbook file schema |
| `schema/step.json` | Step schema |
| `schema/gate.json` | Gate schema |
| `playbooks/production-gatekeeper.md` | Built-in playbook 1 |
| `playbooks/autonomous-loop.md` | Built-in playbook 2 |
| `fixtures/*.yaml` | F1 to F8 |
| `config.yaml` | Default playbook, gate timeout, escape hatch policy |

---

## 4. Contract

### 4.1 Playbook file schema

```yaml
---
schema_version: 1
playbook_version: "0.1.0"
name: string                    # stable identifier, e.g. "production-gatekeeper"
display_name: string
description: string
default_route: simple | medium | large | greenfield | any   # which router bands this applies to
exit_predicate: string          # a checkable statement; runner evaluates it after every phase
escape_hatch:
  trigger: string               # "3+ failed attempts at the same step" or custom
  action: checkpoint_and_halt   # only legal value in v0.1
  resume_note: true             # always write RESUME.md on escape
phases: [Phase]
---
```

### 4.2 Phase schema

```yaml
Phase:
  name: string                  # e.g. "DEFINE"
  label: string                 # display name
  steps: [Step]
  gate: Gate?                   # if present, execution pauses here
```

### 4.3 Step schema

```yaml
Step:
  id: string                    # stable, unique within playbook
  name: string
  maps_to:                      # exactly one of:
    pack: string                # pack name, e.g. "specialist-agents/analyst"
    agent_role: string          # "worker" | "architect" | "pm" | "ux" | "developer" | "reviewer"
    lib_op: string              # e.g. "decision-artifacts/write?kind=spec"
  inputs: {string: string}      # key: source path in prior step outputs or literals
  output_key: string            # name under which this step's output is stored
  required: true | false        # if false, step is skipped when skip condition met
  skip_when: string?            # expression over prior outputs, e.g. "route == 'simple'"
```

### 4.4 Gate schema

```yaml
Gate:
  type: human_approval | auto
  prompt: string                # shown to the human for human_approval gates
  timeout_seconds: number?      # auto gates: max wait before escalation
  on_reject: halt | retry       # human_approval: what happens if human declines
```

### 4.5 Runner output

After each phase the runner appends a phase-result event to `events.jsonl`:

```json
{ "ts": "...", "playbook": "production-gatekeeper", "phase": "BUILD",
  "status": "passed | gate_waiting | escaped | failed",
  "step_results": [ { "id": "step-id", "status": "done | skipped", "output_key": "..." } ] }
```

The full output tree (all step outputs keyed by `output_key`) is stored in the work bundle record under `playbook_state`.

---

## 5. The Rules and Prompt

### 5.1 Runner rules

```text
When a playbook is active for a work bundle:
1. Execute phases in order.
2. For each step, resolve its inputs from prior step outputs or from the work bundle.
3. If a step has skip_when and the condition is true, record it as skipped with reason.
4. After all steps in a phase complete, evaluate the gate if one is present.
5. A human_approval gate pauses the bundle until the human approves or rejects.
   On reject, the bundle status is set to ESCALATED.
6. An auto gate evaluates the exit_predicate. Failure is a soft block: the phase retries
   once. A second failure escalates.
7. After all phases pass, evaluate the top-level exit_predicate.
   True → work bundle moves to DONE. False → escalate with reason.
8. Do not invent steps. Do not skip required steps.
   A skipped required step is always an error, even if its output is not used later.
```

### 5.2 Gate prompt rules

```text
A human_approval gate presents:
  - Phase name and what was produced in this phase (step outputs summary)
  - The gate prompt from the playbook
  - Two choices: Approve (continue) / Reject (halt or retry per on_reject)

The agent does not decide on behalf of the human at a gate.
The agent does not re-run a gate that was already approved in this session.
```

### 5.3 Escape hatch rules

```text
Trigger the escape hatch when:
  - The same step fails 3 or more times consecutively, OR
  - The playbook's escape_hatch.trigger condition is met, OR
  - A context limit is hit mid-phase.

On escape:
  1. Commit the current worktree state with message:
     [checkpoint] escape-hatch — <phase>/<step> — <reason>
  2. Write RESUME.md to the worktree root containing:
     a. What was accomplished (phase results so far)
     b. The exact barrier (step id, error, attempt count)
     c. Clear next steps for the human
  3. Set work bundle status to ESCALATED with reason "escape_hatch".
  4. Do not attempt further steps.
```

---

## 6. Built-in Playbooks

### 6.1 Production Gatekeeper

Maps the Six-Stage Production Gatekeeper process to UMAS components.

```yaml
---
schema_version: 1
playbook_version: "0.1.0"
name: production-gatekeeper
display_name: "Six-Stage Production Gatekeeper"
description: >
  Enforces strict quality gates across every phase of development.
  Spec is written before code. Human approves the plan before BUILD.
  All tests pass before REVIEW. PR follows conventional commit standard.
default_route: medium | large | greenfield
exit_predicate: "merge_queue_result == passed AND spec_path != null AND pr_message != null"
escape_hatch:
  trigger: "3+ failed attempts at same step"
  action: checkpoint_and_halt
  resume_note: true
phases:
  - name: DEFINE
    label: "Phase 1: Define"
    steps:
      - id: define-analyst
        name: "Clarify requirements"
        maps_to: {pack: "specialist-agents/analyst"}
        inputs: {request: "{{work_bundle.description}}"}
        output_key: analyst_output
        required: true
      - id: define-spec
        name: "Write spec document"
        maps_to: {lib_op: "decision-artifacts/write?kind=spec"}
        inputs: {content: "analyst_output", title: "{{work_bundle.title}}"}
        output_key: spec_path
        required: true
      - id: define-impact
        name: "Map affected files"
        maps_to: {agent_role: "analyst"}
        inputs: {spec: "spec_path", repo_root: "{{hook_path}}"}
        output_key: impact_map
        required: true

  - name: PLAN
    label: "Phase 2: Plan"
    steps:
      - id: plan-architect
        name: "Architecture decisions"
        maps_to: {pack: "specialist-agents/architect"}
        inputs: {analyst_output: "analyst_output", spec: "spec_path"}
        output_key: architect_output
        required: true
        skip_when: "route == 'simple'"
      - id: plan-developer-plan
        name: "Implementation plan"
        maps_to: {pack: "specialist-agents/developer"}
        inputs: {prior: "[analyst_output, architect_output]", mode: "plan_only"}
        output_key: implementation_plan
        required: true
    gate:
      type: human_approval
      prompt: "Review the implementation plan. Approve to proceed to BUILD."
      on_reject: halt

  - name: BUILD
    label: "Phase 3: Build"
    steps:
      - id: build-implement
        name: "Implement changes"
        maps_to: {agent_role: "developer"}
        inputs: {plan: "implementation_plan", spec: "spec_path", architect_output: "architect_output"}
        output_key: build_result
        required: true

  - name: VERIFY
    label: "Phase 4: Verify"
    steps:
      - id: verify-test-policy
        name: "Classify what needs tests"
        maps_to: {pack: "test-policy"}
        inputs: {diff: "build_result.diff", mode: "{{project.testing.mode}}"}
        output_key: test_assessment
        required: true
      - id: verify-run-tests
        name: "Run tests"
        maps_to: {lib_op: "test-adapters/run"}
        inputs: {hook_path: "{{hook_path}}"}
        output_key: test_results
        required: true
    gate:
      type: auto
      prompt: "All tests must pass and test_assessment.gate must be ok."
      timeout_seconds: 300
      on_reject: retry

  - name: REVIEW
    label: "Phase 5: Review"
    steps:
      - id: review-two-axis
        name: "Two-axis code review"
        maps_to: {pack: "two-axis-review"}
        inputs:
          diff: "build_result.diff"
          intent: "spec_path"
          test_results: "test_results"
        output_key: review_output
        required: true
      - id: review-anti-slop
        name: "Anti-slop pass"
        maps_to: {pack: "anti-slop"}
        inputs: {content: "build_result.diff"}
        output_key: slop_check
        required: true

  - name: SHIP
    label: "Phase 6: Ship"
    steps:
      - id: ship-pr-message
        name: "Prepare PR message (conventional commit)"
        maps_to: {agent_role: "developer"}
        inputs:
          build_result: "build_result"
          review_output: "review_output"
          spec: "spec_path"
          mode: "pr_message_only"
        output_key: pr_message
        required: true
      - id: ship-report
        name: "Final execution report"
        maps_to: {agent_role: "developer"}
        inputs:
          phases: "all"
          mode: "execution_report"
        output_key: execution_report
        required: true
---
```

### 6.2 Autonomous Execution Loop

Maps the Autonomous Execution Loop to UMAS components.

```yaml
---
schema_version: 1
playbook_version: "0.1.0"
name: autonomous-loop
display_name: "Autonomous Execution Loop & Safe Stop"
description: >
  Drives a task to its exit condition without blocking on human intervention.
  Fresh worktree. Append-only decision trail. Escape hatch on dead ends.
default_route: simple | medium
exit_predicate: "{{user_defined}}"   # set at request time via --exit-predicate
escape_hatch:
  trigger: "3+ failed attempts at same step OR context_limit_hit"
  action: checkpoint_and_halt
  resume_note: true
phases:
  - name: SCAN
    label: "Phase A: Scan"
    steps:
      - id: scan-audit
        name: "Audit codebase, logs, dependencies"
        maps_to: {pack: "specialist-agents/analyst"}
        inputs: {request: "{{work_bundle.description}}", repo_root: "{{hook_path}}"}
        output_key: scan_output
        required: true

  - name: APPLY
    label: "Phase B: Apply"
    steps:
      - id: apply-implement
        name: "Execute fixes sequentially"
        maps_to: {agent_role: "developer"}
        inputs: {scan: "scan_output", plan: "{{work_bundle.description}}"}
        output_key: apply_result
        required: true

  - name: VERIFY
    label: "Phase C: Verify"
    steps:
      - id: verify-exit
        name: "Evaluate exit predicate"
        maps_to: {lib_op: "test-adapters/run"}
        inputs: {hook_path: "{{hook_path}}"}
        output_key: verify_result
        required: true
    gate:
      type: auto
      prompt: "exit_predicate must be satisfied"
      timeout_seconds: 600
      on_reject: retry
---
```

---

## 7. Mapping: Existing Workflow → Playbook

The default UMAS workflow (no playbook) maps onto the production-gatekeeper phases as follows. This shows how playbooks **wrap** the existing pipeline rather than replace it.

| Default UMAS step | Playbook phase/step | Pack or lib |
|---|---|---|
| Router → `simple` | DEFINE → BUILD (no PLAN gate) | router-heuristic |
| Analyst runs | DEFINE/define-analyst | specialist-agents/analyst |
| Architect runs | PLAN/plan-architect | specialist-agents/architect |
| Developer implements | BUILD/build-implement | agent-role: developer |
| Tests run | VERIFY/verify-run-tests | test-adapters |
| Code review | REVIEW/review-two-axis | two-axis-review |
| Merge | SHIP (implicit) | merge-queue |

The default workflow is equivalent to running the production-gatekeeper with all human gates set to `type: auto` and `default_route: any`. The playbook system makes the gates and sequence explicit rather than implicit.

---

## 8. Configuration

### 8.1 Project config (`umas.config.yaml`)

```yaml
workflows:
  playbook: production-gatekeeper   # null = default implicit workflow
  playbooks:
    - name: production-gatekeeper   # built-in; no path needed
    - name: autonomous-loop         # built-in
    - name: my-compliance-workflow  # custom
      path: .umas/playbooks/my-compliance-workflow.md
```

### 8.2 Request-time override

```bash
umas request "add login" --playbook production-gatekeeper
umas request "fix crash" --playbook autonomous-loop --exit-predicate "tests pass"
umas request "refactor auth" --playbook none   # explicit: use default implicit workflow
```

### 8.3 Pack-level defaults (`config.yaml`)

```yaml
default_playbook: null              # null = implicit default workflow
gate_timeout_seconds: 300
escape_hatch:
  max_attempts: 3
  action: checkpoint_and_halt
```

---

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS component | Role |
|---|---|
| Coordinator | Reads the playbook from the registry at request time. Drives the phase loop. Enforces gates: pauses the work bundle at human gates, evaluates predicates at auto gates. |
| Router | Still scores the request. The playbook's `default_route` filters which playbook is offered; it does not override the score. |
| Specialist agents | Invoked as `agent_role` steps. Receive their standard structured inputs; produce their standard outputs. Unaware of the playbook. |
| Packs | Invoked as `pack` steps. Inputs and outputs follow each pack's own contract. Unaware of the playbook. |
| Libs | Invoked as `lib_op` steps. Called by the Coordinator directly. |
| hook-store / agent-session | Each phase runs inside the same worktree. The escape hatch uses `[checkpoint]` commits. |
| event-log | Phase-result events are appended to `events.jsonl`. Gate decisions are recorded there too. |
| decision-artifacts | The `define-spec` step calls `decision-artifacts/write` to persist the spec file and return its path. |
| merge-queue | The SHIP phase feeds into the merge queue; the playbook does not change merge-queue behaviour. |

---

## 10. Source Material and Deviations

This pack is new — no equivalent exists in the original design. It is derived from:

1. **Six-Stage Production Gatekeeper** (user-provided playbook)
2. **Autonomous Execution Loop & Safe Stop** (user-provided playbook)
3. The SDD-agnostic extensibility goal stated in the October 21, 2026 design session

**Key design decisions:**

- **Playbooks wrap, not replace.** Every step maps to an existing pack, agent role, or lib op. There is no "playbook-native" execution logic beyond phase ordering and gate enforcement.
- **`type: auto` gates replicate the default workflow.** A playbook with no `type: human_approval` gates is behaviorally identical to running without a playbook. This makes the mapping in §7 exact and keeps the default workflow non-breaking.
- **Exit predicate is top-level, not per-step.** Per-step `required` and gate predicates are structural checks. The `exit_predicate` is the overall "done" condition and is the hook for the Autonomous Loop's user-defined predicate.
- **Escape hatch is mandatory.** Every playbook must declare one. A playbook file without `escape_hatch` is rejected at load time. This ensures safe stop behaviour is never optional.
- **RESUME.md is always written on escape.** The content maps directly to the Autonomous Loop's resume note: what was accomplished, the exact barrier, clear next steps.

---

## 11. Open Questions

1. **Playbook composition** — Can a step in one playbook call another playbook as a sub-process? Not in v0.1. Deferred: adds recursion risk without a clear use case yet.
2. **Conditional phase branching** — The current schema is a linear phase sequence. If a gate rejects and `on_reject: retry`, does it retry the whole phase or just the failed step? Currently: the whole phase. This should be a configurable field in a future version.
3. **Custom escape hatch actions** — v0.1 only supports `checkpoint_and_halt`. Future: `notify_webhook`, `spawn_triage_agent`. Add when demanded.
4. **SDD standard mapping** — The OpenSpec / Spec-Driven Development standard may define a canonical phase vocabulary. If adopted, the production-gatekeeper phase names should be aliased to match it. No mapping specified yet.
5. **Playbook versioning and migration** — If a playbook is updated while a work bundle is mid-execution, does the bundle continue on the old version or the new one? Policy: pin at bundle creation time. Needs a `playbook_pinned_version` field in the work bundle record.

---

## 12. Fixtures and Acceptance Criteria

### 12.1 Fixtures

| ID | Input | Expected |
|----|-------|----------|
| F1 | production-gatekeeper playbook loaded, route=simple | PLAN/plan-architect step is skipped with skip_when reason recorded |
| F2 | production-gatekeeper, human rejects PLAN gate | Bundle status = ESCALATED; no BUILD steps run |
| F3 | production-gatekeeper, VERIFY tests fail once | Phase retries; second run passes; execution continues to REVIEW |
| F4 | autonomous-loop, step fails 3 times | Escape hatch fires; checkpoint commit written; RESUME.md written with phase/step/error/next-steps |
| F5 | autonomous-loop, exit_predicate satisfied after VERIFY | Bundle moves to DONE; no further phases run |
| F6 | Custom playbook with missing escape_hatch field | Load fails with validation error listing the missing field |
| F7 | Step with skip_when expression that references a non-existent prior output_key | Load fails with validation error; playbook not registered |
| F8 | production-gatekeeper, two-axis review finds critical finding | Gate recommendation = block; gate status = failed; escalated |

### 12.2 Acceptance criteria

1. F1: the step result record shows `status: skipped` and `skip_reason: "route == 'simple'"`.
2. F2: no step in BUILD, VERIFY, REVIEW, or SHIP has a phase-result event in `events.jsonl`.
3. F3: exactly two VERIFY phase-result events appear; the second has `status: passed`.
4. F4: a `[checkpoint] escape-hatch` commit exists; `RESUME.md` contains all three required sections; bundle status = ESCALATED.
5. F5: `events.jsonl` contains a phase-result for VERIFY with `status: passed` and no APPLY phase-result with `status: running` after it.
6. F6 and F7: error messages name the specific field that failed validation.
7. F8: the work bundle escalation event includes `review_output.gate.recommend = "block"` as the reason.
