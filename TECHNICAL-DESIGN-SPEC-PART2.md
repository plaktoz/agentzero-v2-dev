# Technical Design Specification: Unified Multi-Agent Development System (Part 2)

**Continuation from [TECHNICAL-DESIGN-SPEC.md](TECHNICAL-DESIGN-SPEC.md)**
**Design decisions and exception flows:** [UMAS-TECH-DESIGN-SPEC.md](UMAS-TECH-DESIGN-SPEC.md)

---

## 3.3 Submodule: Decision Artifacts Manager (Continued)

> **Code moved.** ArtifactService (Python) now lives in [libs/decision-artifacts.md](libs/decision-artifacts.md#12-reference-implementation-source-code), section 12.1.

#### 3.3.3 Database Schema

> **Schema moved.** `artifacts` and `glossary_terms` SQL schema now lives in [libs/decision-artifacts.md](libs/decision-artifacts.md#12-reference-implementation-source-code), section 12.2.

### 3.4 Submodule: Session History Interface

#### 3.4.1 Purpose
Enable agents to discover and query previous sessions for context recovery.

#### 3.4.2 Architecture

> **Code moved.** Session history interface (Python) now lives in [libs/event-log.md](libs/event-log.md#12-reference-implementation-source-code), section 12.1.

#### 3.4.3 Event Types Schema

> **Code moved.** Event types schema (YAML) now lives in [libs/event-log.md](libs/event-log.md#12-reference-implementation-source-code), section 12.2.

---

## 4. Module 2: Orchestration System

### 4.1 Overview

The Orchestration System coordinates work across multiple agents without becoming a bottleneck.

### 4.2 Submodule: Coordinator Agent

#### 4.2.1 Purpose
Primary human interface for work coordination. Orchestrates but doesn't execute.

#### 4.2.2 Architecture

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

#### 4.2.3 Configuration

```yaml
coordinator_config:
  model: claude-3-5-sonnet-20241022
  token_limit: 200000
  
  complexity_thresholds:
    # Scoring heuristic — see UMAS-TECH-DESIGN-SPEC.md §3.2 Router
    simple:
      max_files: 3
      max_lines: 100
      no_architecture_change: true
    
    medium:
      max_files: 10
      max_lines: 500
      limited_architecture_change: true
    
    complex:
      unlimited: true
  
  grilling:
    # Grilling runs for human-initiated requests only.
    # Agent-to-agent handoffs set human_initiated: false and skip grilling.
    enabled: true
    human_initiated_only: true
    max_questions: 10
    timeout_seconds: 300
  
  specialized_agents:
    pm: true
    architect: true
    ux: true
    analyst: true
  
  session_status_values:
    # Full enum — see UMAS-TECH-DESIGN-SPEC.md §2 Data Model
    # spawned | active | handoff | crashed | done | budget_paused | provider_failed
    resumable_statuses:
      - budget_paused
      - provider_failed
    resumable_timeout_hours: 24
```

### 4.3 Submodule: Router (Skill Selection)

#### 4.3.1 Purpose
Automatic skill/workflow selection based on request analysis.

#### 4.3.2 Architecture

> **Code moved.** Router (Python) now lives in [packs/router-heuristic.md](packs/router-heuristic.md#12-reference-implementation-source-code), section 12.1.

### 4.4 Submodule: Scheduler (Capacity Management)

#### 4.4.1 Purpose
Prevent API rate limit exhaustion through capacity management.

#### 4.4.2 Architecture

> **Code moved.** Scheduler with token budget (Rust) now lives in [libs/budget-meter.md](libs/budget-meter.md#12-reference-implementation-source-code), section 12.1.

####