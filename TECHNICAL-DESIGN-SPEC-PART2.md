# Technical Design Specification: Unified Multi-Agent Development System (Part 2)

**Continuation from [TECHNICAL-DESIGN-SPEC.md](TECHNICAL-DESIGN-SPEC.md)**
**Design decisions and exception flows:** [UMAS-TECH-DESIGN-SPEC.md](UMAS-TECH-DESIGN-SPEC.md)

---

## 3.3 Submodule: Decision Artifacts Manager (Continued)

```python
    async def create_prfaq(
        self,
        title: str,
        press_release: str,
        faq: List[tuple[str, str]],
        author: str,
    ) -> Artifact:
        """Create a PRFAQ (Press Release + FAQ) document."""
        content = self._format_prfaq(title, press_release, faq)
        file_path = self.artifacts_dir / "prfaq" / f"{self._slugify(title)}.md"
        
        artifact = Artifact(
            id=str(uuid.uuid4()),
            type=ArtifactType.PRFAQ,
            title=title,
            content=content,
            author=author,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            file_path=file_path,
            metadata={"status": "draft"},
        )
        
        await self._write_artifact(artifact)
        await self._save_to_db(artifact)
        return artifact
    
    async def create_adr(
        self,
        title: str,
        context: str,
        decision: str,
        consequences: str,
        alternatives: List[str],
        author: str,
    ) -> Artifact:
        """Create an Architecture Decision Record."""
        adr_number = await self._get_next_adr_number()
        content = self._format_adr(
            adr_number, title, context, decision, consequences, alternatives
        )
        
        file_path = self.artifacts_dir / "adr" / f"{adr_number:04d}-{self._slugify(title)}.md"
        
        artifact = Artifact(
            id=str(uuid.uuid4()),
            type=ArtifactType.ADR,
            title=title,
            content=content,
            author=author,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            file_path=file_path,
            metadata={"number": adr_number, "status": "accepted"},
        )
        
        await self._write_artifact(artifact)
        await self._save_to_db(artifact)
        return artifact
    
    async def update_glossary(
        self,
        term: str,
        definition: str,
        context: Optional[str],
        author: str,
    ) -> None:
        """Add or update a term in GLOSSARY.md."""
        glossary = await self._read_glossary()
        
        glossary[term] = {
            "definition": definition,
            "context": context,
            "author": author,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        await self._write_glossary(glossary)
    
    async def track_shortcut(
        self,
        file_path: Path,
        line_number: int,
        description: str,
        reason: str,
        author: str,
    ) -> Artifact:
        """Track a shortcut comment for technical debt."""
        content = self._format_shortcut(file_path, line_number, description, reason)
        
        artifact = Artifact(
            id=str(uuid.uuid4()),
            type=ArtifactType.SHORTCUT,
            title=f"Shortcut: {file_path}:{line_number}",
            content=content,
            author=author,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            file_path=self.artifacts_dir / "shortcuts" / f"{uuid.uuid4()}.md",
            metadata={
                "file": str(file_path),
                "line": line_number,
                "status": "open",
                "priority": "medium",
            },
        )
        
        await self._write_artifact(artifact)
        await self._save_to_db(artifact)
        return artifact
    
    def _format_prfaq(
        self,
        title: str,
        press_release: str,
        faq: List[tuple[str, str]],
    ) -> str:
        """Format PRFAQ document."""
        content = f"# {title}\n\n"
        content += f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
        content += "## Press Release\n\n"
        content += f"{press_release}\n\n"
        content += "## Frequently Asked Questions\n\n"
        
        for question, answer in faq:
            content += f"### {question}\n\n"
            content += f"{answer}\n\n"
        
        return content
    
    def _format_adr(
        self,
        number: int,
        title: str,
        context: str,
        decision: str,
        consequences: str,
        alternatives: List[str],
    ) -> str:
        """Format ADR document."""
        content = f"# ADR-{number:04d}: {title}\n\n"
        content += f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
        content += "## Status\n\nAccepted\n\n"
        content += f"## Context\n\n{context}\n\n"
        content += f"## Decision\n\n{decision}\n\n"
        content += f"## Consequences\n\n{consequences}\n\n"
        
        if alternatives:
            content += "## Alternatives Considered\n\n"
            for i, alt in enumerate(alternatives, 1):
                content += f"{i}. {alt}\n"
            content += "\n"
        
        return content
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
```

#### 3.3.3 Database Schema

```sql
-- Artifacts table
CREATE TABLE artifacts (
    id UUID PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    file_path TEXT NOT NULL,
    metadata JSONB NOT NULL,
    
    INDEX idx_type (type),
    INDEX idx_author (author),
    INDEX idx_created_at (created_at),
    INDEX idx_metadata_gin (metadata) USING GIN
);

-- Glossary terms table
CREATE TABLE glossary_terms (
    id UUID PRIMARY KEY,
    term VARCHAR(255) NOT NULL UNIQUE,
    definition TEXT NOT NULL,
    context TEXT,
    author VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    INDEX idx_term (term)
);
```

### 3.4 Submodule: Session History Interface

#### 3.4.1 Purpose
Enable agents to discover and query previous sessions for context recovery.

#### 3.4.2 Architecture

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
import json
import aiofiles

@dataclass
class SessionEvent:
    id: str
    session_id: str
    agent_id: str
    timestamp: datetime
    event_type: str
    data: Dict

@dataclass
class SessionSummary:
    session_id: str
    agent_id: str
    task_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    decisions: List[str]
    files_modified: List[str]
    commits: List[str]
    token_usage: int

class SessionHistoryService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.events_file = project_root / ".umas" / ".events.jsonl"
        self.events_file.parent.mkdir(parents=True, exist_ok=True)
        
    async def log_event(
        self,
        session_id: str,
        agent_id: str,
        event_type: str,
        data: Dict,
    ) -> None:
        """Log an event to the session history."""
        event = SessionEvent(
            id=str(uuid.uuid4()),
            session_id=session_id,
            agent_id=agent_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            data=data,
        )
        
        # Append to JSONL file
        async with aiofiles.open(self.events_file, mode='a') as f:
            event_dict = {
                "id": event.id,
                "session_id": event.session_id,
                "agent_id": event.agent_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "data": event.data,
            }
            await f.write(json.dumps(event_dict) + '\n')
    
    async def query_sessions(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SessionSummary]:
        """Query session history with filters."""
        sessions_map: Dict[str, SessionSummary] = {}
        
        async with aiofiles.open(self.events_file, mode='r') as f:
            async for line in f:
                event_dict = json.loads(line)
                event = SessionEvent(
                    id=event_dict["id"],
                    session_id=event_dict["session_id"],
                    agent_id=event_dict["agent_id"],
                    timestamp=datetime.fromisoformat(event_dict["timestamp"]),
                    event_type=event_dict["event_type"],
                    data=event_dict["data"],
                )
                
                # Apply filters
                if agent_id and event.agent_id != agent_id:
                    continue
                if since and event.timestamp < since:
                    continue
                
                # Build session summary
                if event.session_id not in sessions_map:
                    sessions_map[event.session_id] = SessionSummary(
                        session_id=event.session_id,
                        agent_id=event.agent_id,
                        task_id=event.data.get("task_id", ""),
                        started_at=event.timestamp,
                        ended_at=None,
                        status="active",
                        decisions=[],
                        files_modified=[],
                        commits=[],
                        token_usage=0,
                    )
                
                session = sessions_map[event.session_id]
                
                # Update session based on event type
                if event.event_type == "session_ended":
                    session.ended_at = event.timestamp
                    session.status = event.data.get("status", "completed")
                elif event.event_type == "decision_made":
                    session.decisions.append(event.data.get("decision", ""))
                elif event.event_type == "file_modified":
                    file_path = event.data.get("file_path", "")
                    if file_path not in session.files_modified:
                        session.files_modified.append(file_path)
                elif event.event_type == "commit_created":
                    session.commits.append(event.data.get("commit_hash", ""))
                elif event.event_type == "token_usage":
                    session.token_usage += event.data.get("tokens", 0)
        
        sessions = list(sessions_map.values())
        
        # Apply task_id filter
        if task_id:
            sessions = [s for s in sessions if s.task_id == task_id]
        
        # Sort by started_at descending
        sessions.sort(key=lambda s: s.started_at, reverse=True)
        
        return sessions[:limit]
    
    async def get_session_context(
        self,
        session_id: str,
    ) -> Dict:
        """Get full context for a specific session."""
        events = []
        
        async with aiofiles.open(self.events_file, mode='r') as f:
            async for line in f:
                event_dict = json.loads(line)
                if event_dict["session_id"] == session_id:
                    event = SessionEvent(
                        id=event_dict["id"],
                        session_id=event_dict["session_id"],
                        agent_id=event_dict["agent_id"],
                        timestamp=datetime.fromisoformat(event_dict["timestamp"]),
                        event_type=event_dict["event_type"],
                        data=event_dict["data"],
                    )
                    events.append(event)
        
        # Reconstruct session context from events
        context = {
            "session_id": session_id,
            "events": [asdict(e) for e in events],
            "decisions": self._extract_decisions(events),
            "files_modified": self._extract_files(events),
            "tool_calls": self._extract_tool_calls(events),
            "commits": self._extract_commits(events),
        }
        
        return context
    
    def _extract_decisions(self, events: List[SessionEvent]) -> List[Dict]:
        """Extract decisions from events."""
        decisions = []
        for event in events:
            if event.event_type == "decision_made":
                decisions.append({
                    "timestamp": event.timestamp.isoformat(),
                    "decision": event.data.get("decision", ""),
                    "rationale": event.data.get("rationale", ""),
                })
        return decisions
    
    def _extract_files(self, events: List[SessionEvent]) -> List[str]:
        """Extract modified files from events."""
        files = set()
        for event in events:
            if event.event_type == "file_modified":
                files.add(event.data.get("file_path", ""))
        return sorted(list(files))
    
    def _extract_tool_calls(self, events: List[SessionEvent]) -> List[Dict]:
        """Extract tool calls from events."""
        tool_calls = []
        for event in events:
            if event.event_type == "tool_called":
                tool_calls.append({
                    "timestamp": event.timestamp.isoformat(),
                    "tool_name": event.data.get("tool_name", ""),
                    "parameters": event.data.get("parameters", {}),
                    "result": event.data.get("result", {}),
                })
        return tool_calls
    
    def _extract_commits(self, events: List[SessionEvent]) -> List[Dict]:
        """Extract commits from events."""
        commits = []
        for event in events:
            if event.event_type == "commit_created":
                commits.append({
                    "timestamp": event.timestamp.isoformat(),
                    "commit_hash": event.data.get("commit_hash", ""),
                    "message": event.data.get("message", ""),
                    "files": event.data.get("files", []),
                })
        return commits
```

#### 3.4.3 Event Types Schema

```yaml
event_types:
  session_started:
    data:
      task_id: string
      task_description: string
      hook_path: string
      base_branch: string
      
  session_ended:
    data:
      status: enum[completed, failed, abandoned]
      reason: string
      
  tool_called:
    data:
      tool_name: string
      parameters: object
      result: object
      duration_ms: integer
      
  decision_made:
    data:
      decision: string
      rationale: string
      alternatives_considered: array[string]
      
  file_modified:
    data:
      file_path: string
      operation: enum[create, update, delete]
      lines_changed: integer
      
  commit_created:
    data:
      commit_hash: string
      message: string
      files: array[string]
      
  escalation_triggered:
    data:
      severity: enum[P0, P1, P2, P3]
      reason: string
      escalated_to: string
      
  token_usage:
    data:
      tokens: integer
      cumulative_tokens: integer
      percentage_used: float
      
  handoff_initiated:
    data:
      from_agent: string
      to_agent: string
      reason: string
      state_transferred: boolean
```

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

### 4.4 Submodule: Scheduler (Capacity Management)

#### 4.4.1 Purpose
Prevent API rate limit exhaustion through capacity management.

#### 4.4.2 Architecture

```rust
// Rust implementation for performance
use std::collections::VecDeque;
use std::sync::Arc;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::{Duration, interval};

pub struct Scheduler {
    max_concurrent_agents: usize,
    semaphore: Arc<Semaphore>,
    queue: Arc<Mutex<VecDeque<AgentTask>>>,
    token_budget: Arc<Mutex<TokenBudget>>,
}

#[derive(Debug, Clone)]
pub struct AgentTask {
    pub agent_id: String,
    pub task_id: String,
    pub priority: u8,
    pub estimated_tokens: u64,
}

#[derive(Debug)]
pub struct TokenBudget {
    pub daily_limit: u64,
    pub current_usage: u64,
    pub reset_at: DateTime<Utc>,
}

impl Scheduler {
    pub fn new(max_concurrent_agents: usize, daily_token_limit: u64) -> Self {
        Self {
            max_concurrent_agents,
            semaphore: Arc::new(Semaphore::new(max_concurrent_agents)),
            queue: Arc::new(Mutex::new(VecDeque::new())),
            token_budget: Arc::new(Mutex::new(TokenBudget {
                daily_limit: daily_token_limit,
                current_usage: 0,
                reset_at: Utc::now() + Duration::from_secs(86400),
            })),
        }
    }
    
    pub async fn schedule_agent(
        &self,
        task: AgentTask,
    ) -> Result<(), SchedulerError> {
        // Check token budget
        let mut budget = self.token_budget.lock().await;
        if budget.current_usage + task.estimated_tokens > budget.daily_limit {
            // Queue for later
            let mut queue = self.queue.lock().await;
            queue.push_back(task);
            return Ok(());
        }
        
        // Reserve tokens
        budget.current_usage += task.estimated_tokens;
        drop(budget);
        
        // Acquire semaphore permit
        let permit = self.semaphore.clone().acquire_owned().await?;
        
        // Spawn agent
        tokio::spawn(async move {
            // Execute agent task
            // ...
            
            // Release permit when done
            drop(permit);
        });
        
        Ok(())
    }
    
    pub async fn process_queue(&self) {
        let mut interval = interval(Duration::from_secs(60));
        
        loop {
            interval.tick().await;
            
            // Check if we have capacity
            if self.semaphore.available_permits() == 0 {
                continue;
            }
            
            // Check token budget
            let budget = self.token_budget.lock().await;
            let available_tokens = budget.daily_limit - budget.current_usage;
            drop(budget);
            
            if available_tokens == 0 {
                continue;
            }
            
            // Process queued tasks
            let mut queue = self.queue.lock().await;
            while let Some(task) = queue.pop_front() {
                if task.estimated_tokens <= available_tokens {
                    drop(queue);
                    let _ = self.schedule_agent(task).await;
                    queue = self.queue.lock().await;
                } else {
                    // Put back and wait
                    queue.push_front(task);
                    break;
                }
            }
        }
    }
    
    pub async fn record_token_usage(
        &self,
        agent_id: &str,
        tokens_used: u64,
    ) -> Result<(), SchedulerError> {
        let mut budget = self.token_budget.lock().await;
        budget.current_usage += tokens_used;
        Ok(())
    }
}
```

####