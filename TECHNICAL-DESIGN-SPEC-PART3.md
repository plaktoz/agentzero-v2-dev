# Technical Design Specification: Unified Multi-Agent Development System (Part 3)

**Continuation from [TECHNICAL-DESIGN-SPEC-PART2.md](TECHNICAL-DESIGN-SPEC-PART2.md)**
**Design decisions and exception flows:** [UMAS-TECH-DESIGN-SPEC.md](UMAS-TECH-DESIGN-SPEC.md)

---

## 5. Module 3: Agent Execution System

### 5.1 Overview

The Agent Execution System manages worker and specialized agents that execute tasks.

### 5.2 Submodule: Worker Agents

#### 5.2.1 Purpose
Task-specific agents spawned for individual work items with ephemeral sessions and persistent identity.

#### 5.2.2 Architecture

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
        
        # Log session start
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
            # Step 1: Recover context from hook
            context = await self._recover_context()
            
            # Step 2: Execute task with minimalism ladder
            result = await self._execute_with_ladder(context)
            
            # Step 3: Commit state
            await self._commit_state(result)
            
            # Step 4: Log completion
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
            # Trigger handoff
            await self._trigger_handoff()
            raise
            
        except Exception as e:
            # Log error and escalate
            await self._handle_error(e)
            raise
    
    async def _execute_with_ladder(
        self,
        context: Dict,
    ) -> TaskResult:
        """Execute task applying minimalism ladder."""
        
        # Build prompt with ladder instructions
        prompt = self._build_prompt_with_ladder(context)
        
        # Execute with LLM
        response = await self.llm_client.generate(
            prompt=prompt,
            model=self.config.model,
            max_tokens=self.config.token_limit,
        )
        
        # Track token usage
        self.token_usage += response.token_usage
        
        # Check handoff threshold
        if self.token_usage >= self.config.token_limit * self.config.handoff_threshold:
            await self._trigger_handoff()
        
        # Parse and validate response
        result = self._parse_response(response)
        
        return result
    
    async def _trigger_handoff(self) -> None:
        """Trigger handoff to fresh agent.
        
        Signalling protocol (see UMAS-TECH-DESIGN-SPEC.md §3.3):
          - Commit worktree with message "[umas:checkpoint] <summary>" to persist state
          - Append handoff_request event to .umas/events.jsonl for Scheduler to detect
          - Scheduler spawns successor agent with compressed context (~15k tokens)
        """
        
        # Commit current state with UMAS checkpoint signal
        await self._commit_state_for_handoff(
            message=f"[umas:checkpoint] handoff at {self.token_usage} tokens"
        )
        
        # Signal Scheduler via events.jsonl (not a separate CLI tool)
        await self.session_history.log_event(
            session_id=self.session_id,
            agent_id=self.config.agent_id,
            event_type="handoff_request",        # read by Scheduler
            data={
                "reason": "token_exhaustion",
                "token_usage": self.token_usage,
                "token_limit": self.config.token_limit,
                "task_id": self.task.id,
            },
        )
        
        raise TokenExhaustionError("Token limit reached, handoff required")
    
    def _build_prompt_with_ladder(self, context: Dict) -> str:
        """Build prompt with minimalism ladder instructions."""
        
        ladder_instructions = """
Before writing any code, climb the minimalism ladder:
1. Does it need to exist? (Skip if not requested)
2. Already in this codebase? (Reuse existing)
3. Standard library or platform feature? (Use built-in)
4. Installed dependency? (Use what's there)
5. Can it be one line? (One clear line)
6. Otherwise: Minimum code that works

Stop at the first rung that holds.
"""
        
        prompt = f"""
Task: {self.task.description}

Context:
{json.dumps(context, indent=2)}

{ladder_instructions}

Execute the task following the ladder principle.
"""
        
        return prompt
```

#### 5.2.3 Configuration

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

### 5.3 Submodule: Specialized Agents

#### 5.3.1 Purpose
Role-specific agents for complex decisions (PM, Architect, UX, Developer, Analyst).

#### 5.3.2 Agent Roles

> **Code moved.** Specialized agents (Python) now lives in [packs/specialist-agents.md](packs/specialist-agents.md#12-reference-implementation-source-code), section 12.1.

#### 5.3.3 Configuration

> **Code moved.** Specialized agents configuration (YAML) now lives in [packs/specialist-agents.md](packs/specialist-agents.md#12-reference-implementation-source-code), section 12.2.

### 5.4 Submodule: Minimalism Enforcement (The Ladder)

#### 5.4.1 Purpose
Enforce minimalism principle through systematic ladder climbing.

#### 5.4.2 Architecture

> **Code moved.** MinimalismEnforcer (Python) now lives in [packs/minimalism-ladder.md](packs/minimalism-ladder.md#12-reference-implementation-source-code), section 12.1.

#### 5.4.3 Configuration

> **Code moved.** Minimalism configuration (YAML) now lives in [packs/minimalism-ladder.md](packs/minimalism-ladder.md#12-reference-implementation-source-code), section 12.2.

---

## 6. Module 4: Verification System

### 6.1 Overview

The Verification System ensures code quality through automated testing and review.

### 6.2 Submodule: Merge Queue Processor

#### 6.2.1 Purpose
Batch merge queue with bisecting verification to prevent integration failures.

#### 6.2.2 Architecture

> **Code moved.** MergeQueueProcessor (Python) now lives in [libs/merge-queue.md](libs/merge-queue.md#12-reference-implementation-source-code), section 12.1.

#### 6.2.3 Configuration

> **Code moved.** Merge queue configuration (YAML) now lives in [libs/merge-queue.md](libs/merge-queue.md#12-reference-implementation-source-code), section 12.2.

#### 6.2.4 Test Coverage Policy

> **Code moved.** Test coverage policy (YAML) now lives in [packs/test-policy.md](packs/test-policy.md#12-reference-implementation-source-code), section 12.1.

### 6.3 Submodule: Test Runner

#### 6.3.1 Purpose
Execute tests with TDD enforcement for risky logic.

#### 6.3.2 Architecture

> **Code moved.** TestRunner (Rust) now lives in [libs/test-adapters.md](libs/test-adapters.md#12-reference-implementation-source-code), section 12.1.

#### 6.3.3 Configuration

> **Code moved.** Test runner configuration (YAML) now lives in [libs/test-adapters.md](libs/test-adapters.md#12-reference-implementation-source-code), section 12.2.

### 6.4 Submodule: Code Review Agent

#### 6.4.1 Purpose
Two-axis review (Standards + Spec) with production-impact mindset.

#### 6.4.2 Architecture

> **Code moved.** CodeReviewAgent (Python) now lives in [packs/two-axis-review.md](packs/two-axis-review.md#12-reference-implementation-source-code), section 12.1.

#### 6.4.3 Configuration

> **Code moved.** Code review configuration (YAML) now lives in [packs/two-axis-review.md](packs/two-axis-review.md#12-reference-implementation-source-code), section 12.2.

---

## 7. Module 5: Monitoring System

### 7.1 Overview

The Monitoring System provides hierarchical health monitoring with automatic recovery.

### 7.2 Three-Tier Watchdog Architecture

```
Daemon (Rust) ← heartbeat every 3 min
└── Triage Agent (Python) ← intelligent triage
    └── System Patrol (Python) ← continuous patrol
        └── Project Monitors (Python) ← per-project health
```

### 7.3 Submodule: Daemon (Watchdog)

#### 7.3.1 Purpose
System process that monitors Triage Agent via heartbeat.

#### 7.3.2 Architecture

> **Code moved.** Daemon (Rust) now lives in [libs/watchdog.md](libs/watchdog.md#12-reference-implementation-source-code), section 12.1.

### 7.4 Submodule: Triage Agent

#### 7.4.1 Purpose
Intelligent triage that monitors System Patrol.

#### 7.4.2 Architecture

> **Code moved.** TriageAgent (Python) now lives in [libs/watchdog.md](libs/watchdog.md#12-reference-implementation-source-code), section 12.2.