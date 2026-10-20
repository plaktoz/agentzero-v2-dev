# agent-session

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS. Depends on [hook-store](../hook-store/README.md), [event-log](../event-log/README.md), and [budget-meter](../budget-meter/README.md) for their *data formats* only — not as code imports. Each format contract is reproduced here so the library can be used without reading those specs first.

---

## 1. Purpose

Provide the shared lifecycle skeleton for any agent that runs an LLM-assisted session inside a worktree: spawn → execute → checkpoint → handoff → done. The library tracks state transitions, emits the standard signals that orchestrators read, enforces the token threshold policy, and builds the handoff packet when transitioning to a successor agent. All six agent types in UMAS (WorkerAgent, Analyst, ProductManager, Architect, UXDesigner, Developer) share this skeleton.

## 2. Scope and Non-Goals

**In scope**
- The session state machine (`spawned → active → handoff → crashed → done`) with valid transitions
- Durable session state written to the worktree's `STATE.md` after every major step
- Checkpoint commits (`[checkpoint] <summary>`) at configurable intervals
- Done commits (`[done] <task-id>`) on completion
- Handoff packet construction: compress full context to a size-limited packet when the token threshold is reached
- Escalation events appended to the event log when the agent is blocked
- Token usage tracking and threshold monitoring (soft at 90%, hard at 95%)
- Recovery: reconstruct session state from `STATE.md` and the event log on restart or handoff

**Non-goals**
- LLM calls. The library calls a caller-supplied `execute_step` function; it never calls an LLM directly.
- Prompt construction, tool execution, or code writing. Those are agent-specific and belong to the caller.
- Orchestration: spawning other agents, managing work bundles, or routing requests.
- Worktree creation or branch management. The caller creates the hook via [hook-store](../hook-store/README.md) and passes the path in.
- Budget enforcement across a project. That is [budget-meter](../budget-meter/README.md)'s period budget. This library only tracks and signals within a single session.

## 3. Concepts and Data Model

### 3.1 Session

```
Session:
  id:              string          # ULID, unique per run (not per agent identity)
  agent_id:        string          # stable name: "worker-alice", "arch-bob"
  task_id:         string          # from the work bundle
  hook_path:       string          # path to the worktree (hook-store)
  event_log_dir:   string          # dir for event-log appends
  config:          SessionConfig
  status:          SessionStatus
  token_used:      int             # cumulative tokens this session
  started_at:      string          # RFC 3339
  ended_at:        string?
```

### 3.2 SessionStatus

```
spawned         session created, execute() not yet called
active          execute() is running
handoff         token threshold reached; successor session being prepared
crashed         unhandled exception; session ended without a done signal
done            task completed; done commit written
budget_paused   period budget exhausted; session suspended until budget resets
provider_failed both primary and fallback LLM providers failed; session suspended
machine_paused  host machine shut down or suspended; session paused at last checkpoint commit
auth_expired    OIDC token expired while machine was off; re-authentication required before resume
```

`handoff`, `budget_paused`, `provider_failed`, `machine_paused`, and `auth_expired` are **resumable**: a successor session reads `STATE.md` (and `PAUSE.md` if present) and the event log to continue. `crashed` and `done` are terminal within a session run; the task may be retried externally.

`machine_paused` and `auth_expired` carry **no timeout** — they wait indefinitely for the machine to boot or the human to re-authenticate. They are never promoted to `crashed` by the watchdog.

### 3.3 SessionConfig

```
SessionConfig:
  token_limit:         int       # max tokens this session may use
  handoff_threshold:   float     # fraction of token_limit that triggers soft handoff (default 0.90)
  emergency_threshold: float     # fraction that triggers hard handoff (default 0.95)
  checkpoint_every:    int       # commit STATE.md after every N steps (default 1)
  handoff_packet_size: int       # max tokens in the handoff packet (default 15000)
  compression_level:   string    # "lite" | "full" | "ultra" — passed to budget-meter pack()
  event_source:        string    # written as `source` field in every event-log append
```

### 3.4 Step

A `Step` is one unit of agent work, supplied by the caller's `execute_step` function:

```
Step:
  summary:    string          # one sentence, written to STATE.md and the checkpoint commit
  decisions:  Decision[]      # { summary, rationale } — choices made this step
  files:      string[]        # files read or written
  token_usage: int            # tokens consumed by this step's LLM call(s)
  done:       bool            # true if the task is complete after this step
  blocked:    Blocked?        # present if the agent cannot proceed
```

```
Blocked:
  severity:   "P0" | "P1" | "P2"
  reason:     string
```

### 3.5 HandoffPacket

Built by the library when the token threshold is reached and written as `HANDOFF.md` in the worktree root for the successor to read.

```
HandoffPacket:
  schema_version:  1
  session_id:      string       # the session that produced this packet
  task_id:         string
  task_summary:    string       # what the task is
  progress:        string       # what has been done (compact)
  next_steps:      string[]     # explicit next actions
  decisions:       Decision[]   # last N decisions (N = config)
  file_pointers:   FilePointer[] # { path, line_start?, line_end?, note }
  token_used:      int
  token_limit:     int
  packed_at:       string
```

The packet is not a context window dump — it is a structured summary produced by `budget-meter.pack()` from sections the caller registers throughout the session.

### 3.6 STATE.md

Written atomically to the worktree root after every step. Plain Markdown; both humans and agents can read it.

```markdown
# STATE: <task_id>

**Status:** active | handoff | done | blocked
**Agent:** <agent_id>
**Session:** <session_id>
**Token usage:** <token_used> / <token_limit> (<pct>%)
**Last updated:** <ts>

## Current task
<one paragraph>

## Progress
<bullet list of completed steps>

## Next steps
<bullet list of explicit next actions>

## Recent decisions
<last N decisions, most recent first>

## Relevant files
<list of file pointers>
```

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `create(config, task, hook_path, event_log_dir) -> Session` | Initialise a session record, write the initial `STATE.md`, and append a `session_started` event. Does not start execution. |
| `execute(session, execute_step_fn) -> SessionResult` | Run the session loop: call `execute_step_fn` repeatedly until `done`, `blocked`, or a threshold is reached. Section 5.1. |
| `checkpoint(session, step) -> CommitRef` | Write `STATE.md`, commit the worktree with a checkpoint message, append a `step_complete` event. Called automatically by `execute` per `checkpoint_every`; also callable directly. |
| `done(session, step) -> CommitRef` | Write final `STATE.md`, commit the worktree with the done message, append a `session_ended` event with `status: done`. |
| `escalate(session, blocked) -> ()` | Append a `session_escalated` event with the severity and reason. Does not stop execution; the caller decides whether to continue or abort. |
| `handoff(session) -> HandoffPacket` | Pack context via `budget-meter.pack()`, write `HANDOFF.md`, commit with handoff message, append a `handoff_initiated` event. Returns the packet. |
| `pause(session, reason) -> CommitRef` | Write `PAUSE.md` and `STATE.md`, commit with pause message, set status `machine_paused`, append a `session_paused` event. Safe to call from a signal handler. Section 5.6. |
| `recover(hook_path, event_log_dir, task_id) -> RecoveredSession` | Reconstruct session state from `STATE.md` and the event log. Reads `PAUSE.md` in preference to `STATE.md` if both exist. Section 5.5. |
| `status(hook_path) -> SessionStatus` | Read current status from `STATE.md` without loading full history. |

Also `agent-session <op> --json`.

The `execute_step_fn` signature: `fn(context: RecoveredContext) -> Step`. It is a pure function supplied by the calling agent; the library calls it in a loop and never inspects its internals.

## 5. Behaviour

### 5.1 Execution loop

```
create session → write STATE.md → append session_started

loop:
  call execute_step_fn(context) → Step

  track token_used += step.token_usage
  append step to session history

  if step.blocked:
    escalate(blocked)
    break (status: crashed if P0, else caller decides)

  if step.done:
    done(session, step)  →  done commit + session_ended event
    break (status: done)

  checkpoint(session, step)  →  STATE.md update + checkpoint commit

  if token_used >= emergency_threshold * token_limit:
    handoff(session)  →  HANDOFF.md + handoff commit + handoff_initiated event
    break (status: handoff)

  if token_used >= handoff_threshold * token_limit:
    handoff(session)  →  same as above
    break (status: handoff)
```

A step that raises an unhandled exception sets status `crashed`, appends a `session_ended` event with `status: crashed`, and re-raises so the caller can log and escalate.

### 5.2 Checkpoint commit message format

```
[checkpoint] <agent_id> step <N>: <step.summary> [tokens: <token_used>]
```

The `[checkpoint]` prefix is the signal the Project Monitor uses to update `last_heartbeat`. The prefix string is a configuration parameter with this default.

### 5.3 Done commit message format

```
[done] <task_id>
```

The `[done]` prefix is the signal the Scheduler uses to detect task completion. The prefix string is a configuration parameter with this default.

### 5.4 Handoff commit message format

```
[handoff] <agent_id> at <token_used>/<token_limit> tokens
```

### 5.5 Recovery

`recover(hook_path, event_log_dir, task_id)` rebuilds enough context for a successor agent to continue:

1. If `PAUSE.md` exists in the worktree, read it first — it is the most recent clean checkpoint.
2. Otherwise read `STATE.md` from the worktree: current task, next steps, recent decisions, file pointers.
3. If `HANDOFF.md` exists, read it (it has more structured content than `STATE.md`).
4. Fold the event log (filtered to `scope = task_id`) to extract `step_complete` events since the last `session_started`.
5. Return a `RecoveredContext` — the same shape as what `execute_step_fn` receives on first call, so the successor agent code is identical whether starting fresh or resuming.

Recovery deliberately does **not** replay the full conversation history. The incoming agent reads the `STATE.md`/`PAUSE.md` summary and the handoff packet; it does not need the prior session's LLM turns.

### 5.6 Pause behaviour (machine shutdown)

`pause(session, reason)` is the clean-shutdown path. It is designed to be called from a signal handler or a shutdown-triggered callback:

1. Complete any in-progress atomic write (never interrupt mid-file).
2. Write `PAUSE.md` to the worktree root atomically (write temp, rename). `PAUSE.md` contains all `STATE.md` fields plus `paused_reason` and `paused_at`.
3. Write `STATE.md` with `Status: machine_paused`.
4. Commit both files: `[umas:checkpoint] <agent_id> — machine shutdown [tokens: <n>]`.
5. Set session `status = machine_paused`.
6. Append `session_paused` event to the event log.
7. Delete the agent's heartbeat file so the watchdog does not raise a false alarm on next boot.

**Shutdown grace window:** The consuming application broadcasts a pause signal by writing `<hook-path>/.pause`. Each agent polls for this file at every step boundary. On detection it calls `pause()`. Agents that do not finish within `shutdown_grace_seconds` (default 30 s) are left in whatever state their last commit captured — no data is lost, but `PAUSE.md` will not exist and recovery falls back to `STATE.md`.

**`.pause` file format:**
```json
{ "v": 1, "reason": "machine_shutdown", "ts": "<RFC 3339>", "grace_seconds": 30 }
```
The file is deleted by the orchestrator after all agents have responded or the grace window expires.

**Agent step-boundary poll** (pseudocode):
```
after each step:
  if file_exists(hook_path + "/.pause"):
    pause(session, reason=read_json(hook_path + "/.pause").reason)
    exit
```

### 5.7 Context registration for handoff packing

The caller registers context sections throughout the session so `handoff()` can pack them efficiently:

```
register_context(session, section: PackSection)
```

`PackSection` follows the [budget-meter](../budget-meter/README.md) `pack()` schema:
```
{ name, content, priority: int, mode: "required"|"truncatable"|"droppable",
  truncate: "head"|"tail" }
```

Recommended sections the caller should register:
- `task` (required): the task description
- `next_steps` (required): the current next-steps list
- `decisions` (truncatable): recent decisions, newest first
- `file_pointers` (truncatable): relevant file references
- `step_history` (droppable): recent step summaries

If the caller never calls `register_context`, `handoff()` builds the packet from `STATE.md` as plain text (degraded mode, flagged in the packet manifest).

### 5.8 Event types emitted

All events are appended via [event-log](../event-log/README.md) `append()`. The `scope` field is set to `task_id`; `source` is set to `config.event_source`.

| type | When emitted | Key `data` fields |
|------|-------------|-------------------|
| `session_started` | `create()` | `task_id`, `hook_path`, `token_limit` |
| `step_complete` | `checkpoint()` | `step_n`, `summary`, `token_used`, `decisions[]` |
| `session_escalated` | `escalate()` | `severity`, `reason` |
| `handoff_initiated` | `handoff()` | `token_used`, `token_limit`, `reason` |
| `session_paused` | `pause()` | `reason`, `token_used`, `pause_file: "PAUSE.md"` |
| `session_resumed` | boot recovery in consuming app | `resumed_from: "machine_paused"\|"auth_expired"`, `session_id` |
| `session_ended` | `done()` or unhandled exception | `status`, `token_used`, `step_count` |

## 6. Configuration

```yaml
# Defaults; all overridable per session via SessionConfig
token_limit: 200000
handoff_threshold: 0.90
emergency_threshold: 0.95
checkpoint_every: 1          # commit STATE.md after every step
handoff_packet_size: 15000   # tokens
compression_level: lite      # lite | full | ultra
event_source: ""             # set to agent_id by the caller

commit_prefixes:
  checkpoint: "[checkpoint]"
  done:       "[done]"
  handoff:    "[handoff]"
  pause:      "[umas:checkpoint]"   # pause uses checkpoint prefix + "— machine shutdown" suffix

state_file: STATE.md
handoff_file: HANDOFF.md
pause_file: PAUSE.md
pause_signal_file: ".pause"         # relative to hook_path; polled at each step boundary

shutdown_grace_seconds: 30          # max time to finish current step before shutdown proceeds
decisions_in_state: 10       # how many recent decisions to keep in STATE.md
decisions_in_packet: 10      # how many recent decisions to include in handoff packet
```

## 7. Failure Modes

| Error | Cause | Behaviour |
|-------|-------|-----------|
| `HookNotFound` | `hook_path` does not exist | Fail `create()`; the caller must create the hook via hook-store first |
| `StepFnError` | `execute_step_fn` raises | Catch, append `session_ended(status=crashed)`, write crash `STATE.md`, re-raise |
| `RequiredSectionTooLarge` | Required handoff sections exceed `handoff_packet_size` | Fail `handoff()` with sizes; the caller must reduce required sections or increase limit |
| `CommitFailed` | Git commit in the worktree fails | Fail with `CommitFailed`; state is not lost (STATE.md was written before commit); retryable |
| `EventLogWriteFailed` | Event-log append fails | Log a warning; do not stop execution. Session state is still in the worktree. |
| `RecoveryIncomplete` | `STATE.md` absent and event log has no matching events | Return a minimal `RecoveredContext` from the task description alone; flag `recovery_degraded: true` |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below; severity is the consumer's policy.

| Error | Suggested recoverability |
|-------|--------------------------|
| `CommitFailed`, `EventLogWriteFailed` | `transient` |
| `StepFnError`, `RecoveryIncomplete` | `ambiguous` |
| `HookNotFound`, `RequiredSectionTooLarge` | `permanent` |

## 8. Acceptance Criteria

1. A session that completes normally produces: (a) a done commit with the configured prefix, (b) a `session_ended` event with `status: done`, (c) a `STATE.md` with `Status: done`.
2. A session that reaches `handoff_threshold` produces: (a) a `HANDOFF.md` that fits within `handoff_packet_size` tokens, (b) a handoff commit, (c) a `handoff_initiated` event.
3. `recover()` on a hook that has a handoff commit and `HANDOFF.md` returns a `RecoveredContext` with the correct `next_steps` and `decisions`.
4. A step that raises an unhandled exception sets `STATE.md` to `Status: crashed` and appends `session_ended(status=crashed)` before re-raising.
5. `checkpoint_every: 3` produces a checkpoint commit exactly on steps 3, 6, 9, … regardless of whether `done` or `handoff` fires in between.
6. Two sessions with the same `task_id` but different `session_id`s append to the same event-log scope; `recover()` correctly identifies the most recent session.
7. A session with no `register_context` calls produces a `HANDOFF.md` in degraded mode with `manifest.degraded: true`.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|---|---|
| `WorkerAgent.execute()` | `agent_session.execute(session, execute_step_fn)` where `execute_step_fn` calls the LLM and applies the minimalism ladder |
| `WorkerAgent._trigger_handoff()` | `agent_session.handoff(session)` |
| All 5 specialised agents (Analyst, PM, Architect, UX, Developer) | Each calls `create()` → `execute()` using its own `execute_step_fn`; the session lifecycle is identical |
| `AgentConfig` (TECHNICAL-DESIGN-SPEC-PART3.md) | `SessionConfig` with the same fields (`model`, `token_limit`, `handoff_threshold`, `compression_level`) |
| Agent session record in `agent_sessions` table (UMAS-TECH-DESIGN-SPEC.md §2) | UMAS maintains this DB row; the library writes `STATUS` to `STATE.md` and the event log. UMAS reads those to update the row. |
| `[umas:done]`, `[umas:checkpoint]`, `[umas:handoff]` commit prefixes | The `[done]`, `[checkpoint]`, `[handoff]` prefixes here. UMAS configures `commit_prefixes.done = "[umas:done]"` etc. at startup. |
| Signalling protocol (UMAS-TECH-DESIGN-SPEC.md §3.3) | `done()` writes the done commit (Scheduler reads it). `escalate()` appends to event-log (Coordinator reads it). `handoff()` appends the handoff event (Scheduler reads it). |
| `budget_paused` / `provider_failed` session statuses | UMAS sets `status: budget_paused` in the DB when `budget-meter` returns `Deferred` during session admission; `status: provider_failed` when `llm-gateway` raises `ProviderExhausted`. Both are set outside this library; UMAS then calls `recover()` when resuming. |

## 10. Source Material and Deviations

Extracted from `TECHNICAL-DESIGN-SPEC-PART3.md` §5.2 (`WorkerAgent`), `UMAS-TECH-DESIGN-SPEC.md` §3.3 (Agent Execution System, signalling protocol, handoff), and §3.6 (Token Budget and Handoff).

| Deviation | Why |
|-----------|-----|
| Library never calls the LLM | The source `WorkerAgent` holds an `llm_client` and calls it directly. The library must be LLM-agnostic so that all agent types (each with a different system prompt and tool set) can share it |
| `execute_step_fn` callback replaces the agent body | The source embeds the minimalism ladder and LLM call inside `WorkerAgent`. Here, those are the caller's `execute_step_fn`; the library only manages the lifecycle wrapper |
| `STATE.md` format specified | The source references `STATE.md` in commit protocol comments but never defines its schema; agents writing inconsistently formatted state files breaks recovery |
| `HANDOFF.md` as a separate file | The source sends the handoff packet as a compressed context passed to the successor via an in-memory scheduler call. A file in the worktree makes the packet durable across crashes and readable without the scheduler |
| `register_context` for packing | The source builds the handoff packet by compressing `session_history` — it does not give callers control over what to include. Caller-registered sections give agents control over what the successor sees |
| `budget_paused` / `provider_failed` set externally | In the source, these statuses live inside `CoordinatorAgent` and the Scheduler. They are not session lifecycle states owned by the agent; UMAS sets them in the DB when external conditions trigger them |

## 11. Open Questions

1. **Step granularity:** Should `checkpoint_every` be measured in *steps* (as specified) or in *token increments*? An agent that runs one expensive step (50k tokens) and many cheap steps (100 tokens each) will checkpoint differently under either policy. A token-increment option (`checkpoint_every_tokens: 10000`) may be more useful.
2. **Concurrent sessions on the same task:** The spec allows only one active session per `task_id` at a time (the successor starts after the predecessor writes its handoff). Should the library enforce this, or leave it to the orchestrator?
3. **STATE.md vs HANDOFF.md:** Should there be only one file? `HANDOFF.md` is a superset of `STATE.md` at handoff time. The duplication is intentional (STATE.md is always present; HANDOFF.md only exists at a handoff boundary), but it may confuse implementors.
4. **Emergency handoff without a prior checkpoint:** If the agent reaches `emergency_threshold` without having committed a checkpoint (e.g., a single very expensive step), `HANDOFF.md` and `STATE.md` may be empty. Should the library force a checkpoint after every step when usage is above, say, 80%?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Example code illustrating one approach. May use consumer-specific names and paths. Sections 1–11 are authoritative. Excluded from the independence rules in [libs/README.md](../README.md).

> Execution model: coding Workers run as external CLI harnesses (see `modularisation-assessment.md` section 4.8), so the in-process `WorkerAgent` below is a reference for the session lifecycle only, not the intended runtime.

### 12.1 WorkerAgent (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §5.2.2

```python
from typing import Optional, Dict, List
from dataclasses import dataclass
import asyncio

@dataclass
class AgentConfig:
    agent_id: str
    model: str
    token_limit: int
    compression_level: str
    handoff_threshold: float

class WorkerAgent:
    def __init__(
        self,
        config: AgentConfig,
        task: Task,
        hook_path: Path,
        llm_client: LLMClient,
        session_history: SessionHistoryService,
    ):
        self.config = config
        self.task = task
        self.hook_path = hook_path
        self.llm_client = llm_client
        self.session_history = session_history
        self.session_id = str(uuid.uuid4())
        self.token_usage = 0
        
    async def execute(self) -> TaskResult:
        """Execute assigned task."""
        
        await self.session_history.log_event(
            session_id=self.session_id,
            agent_id=self.config.agent_id,
            event_type="session_started",
            data={
                "task_id": self.task.id,
                "task_description": self.task.description,
                "hook_path": str(self.hook_path),
            },
        )
        
        try:
            context = await self._recover_context()
            result = await self._execute_with_ladder(context)
            await self._commit_state(result)
            
            await self.session_history.log_event(
                session_id=self.session_id,
                agent_id=self.config.agent_id,
                event_type="session_ended",
                # Completion signal: commit with [umas:done] prefix so Scheduler
                # detects task completion via hook or database poll.
                # See UMAS-TECH-DESIGN-SPEC.md §3.3 Agent Signalling Protocol
                data={"status": "completed", "result": result},
            )
            await self._commit_state(
                message=f"[umas:done] {self.task.id}"
            )
            
            return result
            
        except TokenExhaustionError:
            await self._trigger_handoff()
            raise
            
        except Exception as e:
            await self._handle_error(e)
            raise
    
    async def _execute_with_ladder(self, context: Dict) -> TaskResult:
        """Execute task applying minimalism ladder."""
        
        prompt = self._build_prompt_with_ladder(context)
        response = await self.llm_client.generate(
            prompt=prompt,
            model=self.config.model,
            max_tokens=self.config.token_limit,
        )
        
        self.token_usage += response.token_usage
        
        if self.token_usage >= self.config.token_limit * self.config.handoff_threshold:
            await self._trigger_handoff()
        
        result = self._parse_response(response)
        return result
    
    async def _trigger_handoff(self) -> None:
        """Trigger handoff to fresh agent.
        
        Signalling protocol (see UMAS-TECH-DESIGN-SPEC.md §3.3):
          - Commit worktree with message "[umas:checkpoint] <summary>" to persist state
          - Append handoff_request event to .umas/events.jsonl for Scheduler to detect
          - Scheduler spawns successor agent with compressed context (~15k tokens)
        """
        
        await self._commit_state_for_handoff(
            message=f"[umas:checkpoint] handoff at {self.token_usage} tokens"
        )
        
        await self.session_history.log_event(
            session_id=self.session_id,
            agent_id=self.config.agent_id,
            event_type="handoff_request",
            data={
                "reason": "token_exhaustion",
                "token_usage": self.token_usage,
                "token_limit": self.config.token_limit,
                "task_id": self.task.id,
            },
        )
        
        raise TokenExhaustionError("Token limit reached, handoff required")
```

### 12.2 WorkerAgent configuration (YAML)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §5.2.3

```yaml
worker_agent_config:
  default_model: claude-3-5-sonnet-20241022
  token_limit: 200000
  compression_level: lite
  handoff_threshold: 0.90
  
  tools:
    - read_file
    - write_file
    - execute_command
    - search_code
    - git_operations
  
  minimalism:
    enforce: true
    ladder_required: true
    
  error_handling:
    max_retries: 3
    escalation_on_failure: true
```

### 12.3 CoordinatorAgent (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART2.md` §4.2.2

```python
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum

class TaskComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

@dataclass
class WorkRequest:
    id: str
    description: str
    requester: str
    priority: int
    complexity: TaskComplexity
    created_at: datetime

@dataclass
class WorkBundle:
    id: str
    title: str
    description: str
    tasks: List['Task']
    dependencies: Dict[str, List[str]]
    status: str
    created_at: datetime
    updated_at: datetime

@dataclass
class Task:
    id: str
    title: str
    description: str
    parent_id: Optional[str]
    status: str
    assigned_agent: Optional[str]
    hook_path: Optional[str]
    dependencies: List[str]
    created_at: datetime

class CoordinatorAgent:
    def __init__(
        self,
        worktree_service: WorktreeService,
        task_db: TaskDatabase,
        scheduler: Scheduler,
        router: Router,
    ):
        self.worktree_service = worktree_service
        self.task_db = task_db
        self.scheduler = scheduler
        self.router = router

    async def handle_work_request(
        self,
        request: WorkRequest,
    ) -> WorkBundle:
        """Handle incoming work request from human.

        Grilling rule: human-initiated requests always go through a grilling
        session before planning. Agent-to-agent handoffs skip grilling and
        execute immediately (propulsion principle).
        See: UMAS-TECH-DESIGN-SPEC.md §3.2 Coordinator
        """

        # Step 1: Analyze complexity using scoring heuristic
        # Signals: files affected, scope ambiguity, security/auth/payments,
        # new feature keywords, specific bug cite (→ simple).
        # User can override: --route simple|medium|large|greenfield
        complexity = await self._analyze_complexity(request)

        # Step 2: Decide workflow
        if complexity == TaskComplexity.SIMPLE:
            return await self._handle_simple_task(request)
        elif complexity == TaskComplexity.MEDIUM:
            return await self._handle_medium_task(request)
        else:
            return await self._handle_complex_task(request)

    async def _handle_simple_task(
        self,
        request: WorkRequest,
    ) -> WorkBundle:
        """Handle simple task: Direct to worker agent."""

        # Create single-task work bundle
        task = Task(
            id=str(uuid.uuid4()),
            title=request.description,
            description=request.description,
            parent_id=None,
            status="pending",
            assigned_agent=None,
            hook_path=None,
            dependencies=[],
            created_at=datetime.utcnow(),
        )

        work_bundle = WorkBundle(
            id=str(uuid.uuid4()),
            title=request.description,
            description=request.description,
            tasks=[task],
            dependencies={},
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Save to database
        await self.task_db.save_work_bundle(work_bundle)

        # Spawn worker agent
        await self._spawn_worker(task)

        return work_bundle

    async def _handle_complex_task(
        self,
        request: WorkRequest,
    ) -> WorkBundle:
        """Handle complex task: Specialized agents panel."""

        # Step 1: Grilling session
        clarified_requirements = await self._conduct_grilling(request)

        # Step 2: Invoke specialized agents
        product_decisions = await self._invoke_pm_agent(clarified_requirements)
        architecture = await self._invoke_architect_agent(product_decisions)
        ux_design = await self._invoke_ux_agent(product_decisions)

        # Step 3: Decompose into tasks
        tasks = await self._decompose_into_tasks(
            architecture,
            ux_design,
            product_decisions,
        )

        # Step 4: Build dependency graph
        dependencies = await self._build_dependency_graph(tasks)

        # Step 5: Create work bundle
        work_bundle = WorkBundle(
            id=str(uuid.uuid4()),
            title=request.description,
            description=request.description,
            tasks=tasks,
            dependencies=dependencies,
            status="in_progress",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Save to database
        await self.task_db.save_work_bundle(work_bundle)

        # Step 6: Spawn workers for ready tasks
        ready_tasks = self._get_ready_tasks(tasks, dependencies)
        for task in ready_tasks:
            await self._spawn_worker(task)

        return work_bundle

    async def _spawn_worker(
        self,
        task: Task,
    ) -> str:
        """Spawn worker agent for task."""

        # Create worktree (hook)
        agent_id = f"worker-{uuid.uuid4().hex[:8]}"
        worktree = await self.worktree_service.create_worktree(
            agent_id=agent_id,
            task_id=task.id,
            base_branch="main",
        )

        # Update task
        task.assigned_agent = agent_id
        task.hook_path = str(worktree.path)
        task.status = "in_progress"
        await self.task_db.update_task(task)

        # Schedule agent execution
        await self.scheduler.schedule_agent(
            agent_id=agent_id,
            task=task,
            hook_path=worktree.path,
        )

        return agent_id

    async def handle_escalation(
        self,
        escalation: Escalation,
    ) -> None:
        """Handle escalation from agent."""

        if escalation.severity == "P0":
            # Critical: Notify human immediately
            await self._notify_human(escalation)
        elif escalation.severity == "P1":
            # High: Coordinator intervention
            await self._handle_p1_escalation(escalation)
        else:
            # Medium/Low: Route to System Patrol
            await self._route_to_system_patrol(escalation)

    async def _conduct_grilling(
        self,
        request: WorkRequest,
    ) -> Dict:
        """Conduct grilling session with human."""
        # Implementation: Interactive Q&A with human
        pass

    async def _decompose_into_tasks(
        self,
        architecture: Dict,
        ux_design: Dict,
        product_decisions: Dict,
    ) -> List[Task]:
        """Decompose work into parallelizable tasks."""
        # Implementation: Break down into task hierarchy
        pass

    def _get_ready_tasks(
        self,
        tasks: List[Task],
        dependencies: Dict[str, List[str]],
    ) -> List[Task]:
        """Get tasks with no pending dependencies."""
        ready = []
        for task in tasks:
            deps = dependencies.get(task.id, [])
            if not deps or all(self._is_task_completed(d) for d in deps):
                ready.append(task)
        return ready
```
