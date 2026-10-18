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

#### 5.3.3 Configuration

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

### 5.4 Submodule: Minimalism Enforcement (The Ladder)

#### 5.4.1 Purpose
Enforce minimalism principle through systematic ladder climbing.

#### 5.4.2 Architecture

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

#### 5.4.3 Configuration

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

---

## 6. Module 4: Verification System

### 6.1 Overview

The Verification System ensures code quality through automated testing and review.

### 6.2 Submodule: Merge Queue Processor

#### 6.2.1 Purpose
Batch merge queue with bisecting verification to prevent integration failures.

#### 6.2.2 Architecture

```python
from typing import List, Set
from dataclasses import dataclass

@dataclass
class PullRequest:
    id: str
    branch: str
    author: str
    files_changed: List[str]
    status: str
    created_at: datetime

@dataclass
class MergeQueueEntry:
    pr: PullRequest
    position: int
    added_at: datetime

class MergeQueueProcessor:
    def __init__(
        self,
        git_client: GitClient,
        test_runner: TestRunner,
        worktree_service: WorktreeService,
    ):
        self.git_client = git_client
        self.test_runner = test_runner
        self.worktree_service = worktree_service
        self.queue: List[MergeQueueEntry] = []
        
    async def add_to_queue(self, pr: PullRequest) -> None:
        """Add PR to merge queue."""
        entry = MergeQueueEntry(
            pr=pr,
            position=len(self.queue),
            added_at=datetime.utcnow(),
        )
        self.queue.append(entry)
        
        # Trigger batch processing
        await self._process_queue()
    
    async def _process_queue(self) -> None:
        """Process merge queue with batch verification."""
        
        if not self.queue:
            return
        
        # Step 1: Batch all PRs
        batch = [entry.pr for entry in self.queue]
        
        # Step 2: Create temporary merge branch
        merge_branch = await self._create_merge_branch(batch)
        
        # Step 3: Test merged stack
        test_result = await self.test_runner.run_all_tests(merge_branch)
        
        if test_result.passed:
            # All tests passed: Merge all PRs
            await self._merge_all(batch)
            self.queue.clear()
        else:
            # Tests failed: Bisect to find culprit
            culprits = await self._bisect_failures(batch)
            
            # Remove culprits from queue
            for culprit in culprits:
                self.queue = [e for e in self.queue if e.pr.id != culprit.id]
                await self._notify_failure(culprit, test_result)
            
            # Retry with remaining PRs
            await self._process_queue()
    
    async def _create_merge_branch(
        self,
        prs: List[PullRequest],
    ) -> str:
        """Create temporary branch with all PRs merged."""
        
        merge_branch = f"merge-queue-{uuid.uuid4().hex[:8]}"
        
        # Create branch from main
        await self.git_client.create_branch(merge_branch, "main")
        
        # Merge all PRs
        for pr in prs:
            await self.git_client.merge(merge_branch, pr.branch)
        
        return merge_branch
    
    async def _bisect_failures(
        self,
        batch: List[PullRequest],
    ) -> List[PullRequest]:
        """Bisect to find failing PRs."""
        
        if len(batch) == 1:
            return batch
        
        # Split batch in half
        mid = len(batch) // 2
        left = batch[:mid]
        right = batch[mid:]
        
        # Test left half
        left_branch = await self._create_merge_branch(left)
        left_result = await self.test_runner.run_all_tests(left_branch)
        
        # Test right half
        right_branch = await self._create_merge_branch(right)
        right_result = await self.test_runner.run_all_tests(right_branch)
        
        culprits = []
        
        if not left_result.passed:
            culprits.extend(await self._bisect_failures(left))
        
        if not right_result.passed:
            culprits.extend(await self._bisect_failures(right))
        
        return culprits
    
    async def _merge_all(self, prs: List[PullRequest]) -> None:
        """Merge all PRs to main."""
        for pr in prs:
            await self.git_client.merge("main", pr.branch)
            pr.status = "merged"
```

#### 6.2.3 Configuration

```yaml
merge_queue_config:
  # The merge-queue worktree is PERMANENT — created once during umas init --project.
  # Only the temp test branch is created/destroyed per batch.
  # State machine: IDLE → COLLECTING → TESTING → BISECTING → MERGING
  # See UMAS-TECH-DESIGN-SPEC.md §3.4 Merge Queue Processor
  worktree: permanent
  
  batch_size: 10
  batch_timeout_seconds: 300
  
  testing:
    run_all_tests: true
    parallel_execution: true
    timeout_per_test: 60
    
  bisecting:
    enabled: true
    max_depth: 10
    # If all PRs fail independently → all moved to blocked (failed_in_isolation)
    # Agents re-spawned with failure context. Retry limit: 3 per PR.
    # See UMAS-TECH-DESIGN-SPEC.md §4.9
    
  notifications:
    on_merge: true
    on_failure: true
```

#### 6.2.4 Test Coverage Policy

```yaml
# Configurable per project in umas.config.yaml
# See UMAS-TECH-DESIGN-SPEC.md §3.4 Test Coverage Policy
test_coverage:
  mode: selective          # selective (default) | strict
  
  selective_mode:
    # Tests required for: branches, loops, parsers, money, security
    # Tests NOT required for: renaming, formatting, config-only changes
    risky_logic_patterns:
      - conditional_logic
      - loops_and_iteration
      - parsers_and_transforms
      - money_calculations
      - security_checks
    
  strict_mode:
    # Full TDD: red-green-refactor for every feature
    tdd_required: true
    
  coverage_target: 80      # percentage, configurable per project
```

### 6.3 Submodule: Test Runner

#### 6.3.1 Purpose
Execute tests with TDD enforcement for risky logic.

#### 6.3.2 Architecture

```rust
// Rust implementation for performance
use std::process::Command;
use std::path::PathBuf;

pub struct TestRunner {
    project_root: PathBuf,
    test_framework: TestFramework,
}

#[derive(Debug, Clone)]
pub enum TestFramework {
    Pytest,
    Jest,
    Cargo,
}

#[derive(Debug)]
pub struct TestResult {
    pub passed: bool,
    pub total: usize,
    pub passed_count: usize,
    pub failed_count: usize,
    pub skipped_count: usize,
    pub duration_ms: u64,
    pub failures: Vec<TestFailure>,
}

#[derive(Debug)]
pub struct TestFailure {
    pub test_name: String,
    pub error_message: String,
    pub file: String,
    pub line: usize,
}

impl TestRunner {
    pub async fn run_all_tests(
        &self,
        branch: &str,
    ) -> Result<TestResult, TestError> {
        // Checkout branch
        self.checkout_branch(branch).await?;
        
        // Run tests based on framework
        match self.test_framework {
            TestFramework::Pytest => self.run_pytest().await,
            TestFramework::Jest => self.run_jest().await,
            TestFramework::Cargo => self.run_cargo_test().await,
        }
    }
    
    async fn run_pytest(&self) -> Result<TestResult, TestError> {
        let output = Command::new("pytest")
            .arg("--json-report")
            .arg("--json-report-file=test-results.json")
            .current_dir(&self.project_root)
            .output()?;
        
        // Parse JSON output
        let result = self.parse_pytest_output(&output.stdout)?;
        
        Ok(result)
    }
    
    pub async fn run_specific_tests(
        &self,
        test_files: Vec<PathBuf>,
    ) -> Result<TestResult, TestError> {
        // Run only specified test files
        let mut total_result = TestResult {
            passed: true,
            total: 0,
            passed_count: 0,
            failed_count: 0,
            skipped_count: 0,
            duration_ms: 0,
            failures: vec![],
        };
        
        for test_file in test_files {
            let result = self.run_test_file(&test_file).await?;
            total_result.merge(result);
        }
        
        Ok(total_result)
    }
}
```

#### 6.3.3 Configuration

```yaml
test_runner_config:
  framework: pytest  # pytest, jest, cargo
  
  execution:
    parallel: true
    max_workers: 4
    timeout_per_test: 60
    
  coverage:
    enabled: true
    target: 95
    fail_under: 80
    
  reporting:
    format: json
    output_file: test-results.json
```

### 6.4 Submodule: Code Review Agent

#### 6.4.1 Purpose
Two-axis review (Standards + Spec) with production-impact mindset.

#### 6.4.2 Architecture

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

#### 6.4.3 Configuration

```yaml
code_review_config:
  model: claude-3-5-sonnet-20241022
  
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

```rust
use tokio::time::{interval, Duration};
use std::process::Command;

pub struct Daemon {
    triage_agent_pid: Option<u32>,
    heartbeat_interval: Duration,
    last_heartbeat: Option<Instant>,
}

impl Daemon {
    pub fn new() -> Self {
        Self {
            triage_agent_pid: None,
            heartbeat_interval: Duration::from_secs(180), // 3 minutes
            last_heartbeat: None,
        }
    }
    
    pub async fn run(&mut self) {
        // Start triage agent
        self.start_triage_agent().await;
        
        // Monitor heartbeat
        let mut interval = interval(Duration::from_secs(60));
        
        loop {
            interval.tick().await;
            
            if !self.is_triage_agent_healthy() {
                tracing::warn!("Triage agent unhealthy, restarting");
                self.restart_triage_agent().await;
            }
        }
    }
    
    async fn start_triage_agent(&mut self) {
        let child = Command::new("python")
            .arg("-m")
            .arg("umas.agents.triage")
            .spawn()
            .expect("Failed to start triage agent");
        
        self.triage_agent_pid = Some(child.id());
        self.last_heartbeat = Some(Instant::now());
    }
    
    fn is_triage_agent_healthy(&self) -> bool {
        if let Some(last_hb) = self.last_heartbeat {
            last_hb.elapsed() < self.heartbeat_interval * 2
        } else {
            false
        }
    }
    
    pub fn record_heartbeat(&mut self) {
        self.last_heartbeat = Some(Instant::now());
    }
    
    async fn restart_triage_agent(&mut self) {
        // Kill old process
        if let Some(pid) = self.triage_agent_pid {
            let _ = Command::new("kill")
                .arg("-9")
                .arg(pid.to_string())
                .output();
        }
        
        // Start new process
        self.start_triage_agent().await;
    }
}
```

### 7.4 Submodule: Triage Agent

#### 7.4.1 Purpose
Intelligent triage that monitors System Patrol.

#### 7.4.2 Architecture

```python
import asyncio
from datetime import datetime, timedelta

class TriageAgent:
    def __init__(
        self,
        daemon_client: DaemonClient,
        system_patrol_monitor: SystemPatrolMonitor,
    ):
        self.daemon_client = daemon_client
        self.system_patrol_monitor = system_patrol_monitor
        self.heartbeat_interval = 180  # 3 minutes
        
    async def run(self) -> None:
        """Main triage loop."""
        
        # Start heartbeat task
        asyncio.create_task(self._send_heartbeats())
        
        # Monitor System Patrol
        while True:
            try:
                # Check Syste