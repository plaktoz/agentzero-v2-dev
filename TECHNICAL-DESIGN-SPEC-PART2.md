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

> **Code moved.** `CoordinatorAgent`, `WorkRequest`, `WorkBundle`, and `Task` Python classes moved to [`libs/agent-session.md` §12.3](libs/agent-session.md).

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