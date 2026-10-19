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

> **Code moved.** WorkerAgent (Python) now lives in [libs/agent-session.md](libs/agent-session.md#12-reference-implementation-source-code), section 12.1.

#### 5.2.3 Configuration

> **Code moved.** WorkerAgent configuration (YAML) now lives in [libs/agent-session.md](libs/agent-session.md#12-reference-implementation-source-code), section 12.2.

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