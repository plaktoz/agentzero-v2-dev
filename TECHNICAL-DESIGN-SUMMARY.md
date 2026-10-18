# Technical Design Specification Summary

**Version:** 1.1
**Date:** October 18, 2026
**Status:** Active — Reconciled

---

## Document Structure

The full technical design is spread across four documents. Read them in this order:

| # | Document | What it covers | Start here if… |
|---|----------|---------------|----------------|
| 1 | [UMAS-TECH-DESIGN-SPEC.md](UMAS-TECH-DESIGN-SPEC.md) | Component design decisions, agent signalling protocol, exception flows (16 scenarios with alternative flows), resolved PRD conflicts | You want to understand **why** things work the way they do |
| 2 | [TECHNICAL-DESIGN-SPEC.md](TECHNICAL-DESIGN-SPEC.md) | Technology stack (Rust/Python/React), system architecture, Context Persistence implementation (Rust `WorktreeService`, Python `ArtifactService`) | You are implementing the **core infrastructure** |
| 3 | [TECHNICAL-DESIGN-SPEC-PART2.md](TECHNICAL-DESIGN-SPEC-PART2.md) | Orchestration System (`CoordinatorAgent`, `Router`, `Scheduler`) and Agent Execution System implementation | You are implementing the **orchestration or agent layer** |
| 4 | [TECHNICAL-DESIGN-SPEC-PART3.md](TECHNICAL-DESIGN-SPEC-PART3.md) | Verification System (`MergeQueueProcessor`, `TestRunner`, `CodeReviewAgent`) and Monitoring System (`Daemon`, `TriageAgent`) | You are implementing the **verification or monitoring layer** |

**Source of truth for product requirements:** [unified-multi-agent-system-prd.md](unified-multi-agent-system-prd.md)

### Reconciliation status

All four documents were reconciled in this revision. Key changes from v1.0:

- `gt done` / `gt escalate` (Gastown terms) removed from all documents. Replaced with filesystem-based signalling: `[umas:done]` commit messages and `.umas/events.jsonl` appends.
- Grilling/propulsion rule made explicit in `CoordinatorAgent`: human-initiated requests grill, agent-to-agent handoffs execute immediately.
- Router scoring heuristic documented in `CoordinatorAgent` config and `UMAS-TECH-DESIGN-SPEC.md §3.2`.
- Merge-queue worktree clarified as permanent in `MergeQueueProcessor` config.
- Full agent session status enum (`budget_paused`, `provider_failed`) added to Part 2 Coordinator config.
- Test coverage policy (selective vs strict modes) added to Part 3 Verification config.
- Cross-references added to all three implementation files pointing to `UMAS-TECH-DESIGN-SPEC.md`.

---

## Technology Stack Confirmed

### Core Languages
- **Daemon & CLI:** Rust 1.70+ (performance, memory safety, cross-platform)
- **Agent Runtime:** Python 3.10+ (AI/ML ecosystem, LLM SDK support)
- **Dashboard:** React 18+ with TypeScript

### Databases
- **Development:** SQLite 3.35+ (embedded, zero-config)
- **Production:** PostgreSQL 14+ (scalability, 20-30+ agents)
- **Metrics:** TimescaleDB (time-series data)

### LLM Providers (Tier 1)
- Anthropic Claude (claude-3-5-sonnet-20241022)
- IBM Bob (enterprise features)
- OpenAI GPT-4

### Observability
- OpenTelemetry protocol
- Prometheus (metrics)
- Jaeger (distributed tracing)
- Loki (log aggregation)

---

## System Architecture

### Layered Architecture (5 Layers)

```
1. Human Interface Layer
   - CLI (Rust)
   - Dashboard (React)
   - Metrics Display
   - Escalation Channels

2. Orchestration Layer
   - Coordinator Agent (Python)
   - Router (Python)
   - Scheduler (Rust)

3. Agent Execution Layer
   - Worker Agents (Python)
   - Specialized Agents (PM, Architect, UX, Dev, Analyst)
   - Review Agents

4. Verification Layer
   - Merge Queue Processor (Python)
   - Test Runner (Rust)
   - Minimalism Checker (Python)

5. Monitoring Layer
   - Daemon (Rust)
   - Triage Agent (Python)
   - System Patrol (Python)
   - Project Monitors (Python)

6. Persistence Layer
   - Git Worktrees (hooks)
   - Task Database (SQLite/PostgreSQL)
   - Decision Artifacts (files)
   - Metrics Database (TimescaleDB)
```

---

## Module Breakdown

### Module 1: Context Persistence System

**Purpose:** Ensure agent work state survives crashes and restarts.

**Submodules:**
1. **Git Worktree Manager** (Rust)
   - Create/remove worktrees for agents
   - Commit agent state
   - Recover state after crash
   - Database: `worktrees`, `commit_events` tables

2. **Decision Artifacts Manager** (Python)
   - Create PRFAQ, ADR, Spec documents
   - Manage GLOSSARY.md
   - Track shortcut comments (technical debt)
   - Database: `artifacts`, `glossary_terms` tables

3. **Session History Interface** (Python)
   - Log events to `.events.jsonl`
   - Query previous sessions
   - Extract decisions, files, tool calls
   - Enable context recovery

**Key Data Structures:**
- `Worktree`: id, agent_id, task_id, path, branch, status
- `Artifact`: id, type, title, content, author, metadata
- `SessionEvent`: id, session_id, agent_id, event_type, data

---

### Module 2: Orchestration System

**Purpose:** Coordinate work across multiple agents without bottlenecks.

**Submodules:**
1. **Coordinator Agent** (Python)
   - Primary human interface
   - Break down work into tasks
   - Spawn worker agents
   - Handle escalations
   - Complexity analysis: simple/medium/complex

2. **Router** (Python)
   - Automatic skill selection
   - Match request to workflow
   - Support user overrides

3. **Scheduler** (Rust)
   - Capacity management
   - Token budget tracking
   - Queue management
   - Prevent API rate limits

**Key Data Structures:**
- `WorkRequest`: id, description, requester, priority, complexity
- `WorkBundle`: id, title, tasks, dependencies, status
- `Task`: id, title, assigned_agent, hook_path, dependencies

---

### Module 3: Agent Execution System

**Purpose:** Execute tasks through worker and specialized agents.

**Submodules:**
1. **Worker Agents** (Python)
   - Task-specific execution
   - Ephemeral sessions, persistent identity
   - Token usage tracking
   - Automatic handoff on token exhaustion

2. **Specialized Agents** (Python)
   - ProductManagerAgent: Define user needs
   - ArchitectAgent: Design architecture
   - UXDesignerAgent: Design user experience
   - DeveloperAgent: Implement with minimalism
   - AnalystAgent: Clarify requirements

3. **Minimalism Enforcer** (Python)
   - Climb 6-rung ladder
   - Track code avoided
   - Measure reuse percentage

**Key Data Structures:**
- `AgentConfig`: agent_id, model, token_limit, handoff_threshold
- `LadderResult`: rung, rationale, solution, code_avoided

---

### Module 4: Verification System

**Purpose:** Ensure code quality through automated testing and review.

**Submodules:**
1. **Merge Queue Processor** (Python)
   - Batch merge with verification
   - Bisecting to isolate failures
   - Prevent broken main branch

2. **Test Runner** (Rust)
   - Execute tests (pytest, jest, cargo)
   - Parallel execution
   - Coverage tracking
   - TDD enforcement

3. **Code Review Agent** (Python)
   - Two-axis review (Standards + Spec)
   - Production-impact mindset
   - Severity-based findings

**Key Data Structures:**
- `PullRequest`: id, branch, author, files_changed, status
- `TestResult`: passed, total, failures, duration_ms
- `ReviewFinding`: severity, category, file, line, description

---

### Module 5: Monitoring System

**Purpose:** Hierarchical health monitoring with automatic recovery.

**Architecture:**
```
Daemon (Rust) ← heartbeat every 3 min
└── Triage Agent (Python) ← intelligent triage
    └── System Patrol (Python) ← continuous patrol
        └── Project Monitors (Python) ← per-project health
```

**Submodules:**
1. **Daemon** (Rust)
   - Monitor Triage Agent via heartbeat
   - Restart on failure
   - System-level watchdog

2. **Triage Agent** (Python)
   - Monitor System Patrol
   - Intelligent triage
   - Send heartbeats to Daemon

3. **System Patrol** (Python)
   - Monitor all projects
   - Dispatch maintenance workers
   - Cross-project health

4. **Project Monitor** (Python)
   - Per-project health checks
   - Detect stuck agents
   - Trigger recovery

---

### Module 6: Human Interface System

**Submodules:**
1. **CLI** (Rust)
   - Primary interface
   - Commands: init, start-all, agents, request, watch, metrics
   - Shell completion support

2. **Dashboard** (React + TypeScript)
   - Real-time agent activity
   - Work bundle visualization
   - Merge queue state
   - Metrics and trends

3. **Metrics Display**
   - Cost per task
   - Token usage
   - Code reuse percentage
   - Test coverage

---

### Module 7: Multi-Agent Platform Support

**Purpose:** Support multiple coding agent platforms working together.

**Tier 1 Platforms:**
- Claude Code (full integration)
- IBM Bob (enterprise features)
- GitHub Copilot (code completion)

**Key Components:**
- Platform adapters
- Agent selection strategy
- Cross-platform context transfer
- Unified work tracking

---

### Module 8: Error Handling & Recovery

**Error Classification:**
- P0 (Critical): Immediate human intervention
- P1 (High): Coordinator intervention
- P2 (Medium): System Patrol handles
- P3 (Low): Logged for analysis

**Recovery Strategies:**
- Automatic: Transient failures (retry with backoff)
- Manual: Permanent failures (human guidance)

---

### Module 9: Installation & Deployment

**Installation Methods:**
1. Package manager (npm/pip)
2. Installer script (curl | bash)
3. Container (Docker)

**Key Features:**
- Idempotent installation
- Non-intrusive (optional Git hooks)
- Easy removal
- Automatic updates with rollback

---

### Module 10: Agent Handoff & Token Management

**Purpose:** Seamless agent handoff on token exhaustion.

**Key Concepts:**
- Hook-based work assignment (work tied to hook, not agent)
- Proactive handoff at 90% token usage
- Context compression for efficiency
- Sequential, parallel, and collaborative handoff patterns

---

## Database Schema Overview

### Core Tables

```sql
-- Worktrees
worktrees (id, agent_id, task_id, path, branch, created_at, status)

-- Tasks
tasks (id, title, description, parent_id, status, assigned_agent, hook_path)
work_bundles (id, title, description, status, created_at)

-- Artifacts
artifacts (id, type, title, content, author, created_at, metadata)
glossary_terms (id, term, definition, context, author)

-- Sessions
session_events (stored in .events.jsonl file)

-- Metrics
token_usage (id, agent_id, session_id, tokens, timestamp)
cost_tracking (id, agent_id, task_id, cost, timestamp)
```

---

## API Specifications

### CLI Commands

```bash
# System Management
umas init
umas start-all
umas stop-all
umas status
umas health-check

# Project Management
umas project create <name>
umas project list
umas project switch <name>

# Agent Management
umas agents list
umas agents spawn --task <id>
umas agents status <agent-id>
umas agents handoff <from> <to>

# Work Management
umas request "<description>"
umas work-bundle show <id>
umas watch

# Monitoring
umas metrics tokens
umas metrics cost
umas metrics quality
umas metrics agents

# Debugging
umas debug replay --session <id>
umas debug context --session <id>
umas logs --agent <id>
```

### REST API Endpoints

```
GET    /api/v1/agents
POST   /api/v1/agents
GET    /api/v1/agents/{id}
DELETE /api/v1/agents/{id}

GET    /api/v1/tasks
POST   /api/v1/tasks
GET    /api/v1/tasks/{id}
PATCH  /api/v1/tasks/{id}

GET    /api/v1/work-bundles
POST   /api/v1/work-bundles
GET    /api/v1/work-bundles/{id}

GET    /api/v1/metrics/tokens
GET    /api/v1/metrics/cost
GET    /api/v1/metrics/quality

WebSocket: /ws/events
```

---

## Security Architecture

### Authentication & Authorization
- API keys in environment variables
- JWT tokens for dashboard
- Role-based access control (Admin, Developer, Viewer)

### Data Protection
- Secrets never committed to version control
- Least privilege for agents
- Audit logging (90-day retention)

### Network Security
- Services bind to localhost (127.0.0.1)
- TLS 1.2+ for external communication
- Certificate validation enforced

---

## Performance & Scalability

### Capacity Tiers

**Tier 1 (MVP):**
- 5 concurrent agents
- SQLite database
- Individual developers

**Tier 2 (Production):**
- 20 concurrent agents
- PostgreSQL database
- Small teams (5-10 developers)

**Tier 3 (Scale):**
- 30+ concurrent agents
- PostgreSQL with connection pooling
- Large teams (10+ developers)

### Token Budget Management
- Daily token budget per project
- Per-task token budget
- Alerts at 80%, 90%, 95%
- Graceful budget exhaustion handling

---

## Testing Strategy

### Unit Tests
- All core modules
- 90%+ code coverage target
- Fast execution (<1s per test)

### Integration Tests
- Agent-to-agent communication
- Database operations
- Git operations
- LLM provider integration

### End-to-End Tests
- Complete workflows (simple, medium, complex)
- Crash recovery scenarios
- Agent handoff scenarios
- Merge queue processing

### Performance Tests
- 30 concurrent agents
- Token budget exhaustion
- Database query performance
- API rate limit handling

---

## Deployment Architecture

### Development Environment
```
Local Machine
├── Daemon (Rust binary)
├── Agents (Python processes)
├── SQLite database
└── Git repository
```

### Production Environment
```
Server/Cloud
├── Daemon (systemd service)
├── Agent Pool (managed processes)
├── PostgreSQL cluster
├── Prometheus + Grafana
├── Jaeger tracing
└── Load balancer (optional)
```

---

## Implementation Phases

### Phase 1: Foundation (MVP) - 8-12 weeks
- Git Worktree Manager
- Basic task database
- Coordinator agent
- Worker agents
- Minimalism enforcement
- Basic merge queue
- CLI interface

### Phase 2: Specialization - 6-8 weeks
- Specialized agents (PM, Architect, UX, Dev, Analyst)
- Grilling sessions
- Decision artifacts (PRFAQ, ADR, GLOSSARY)
- TDD enforcement
- Code review (two-axis)

### Phase 3: Monitoring - 4-6 weeks
- Three-tier watchdog system
- Project monitors
- System patrol
- Telemetry framework
- Dashboard

### Phase 4: Scale - 6-8 weeks
- Scheduler (capacity management)
- Multi-runtime support
- Session history interface
- Advanced merge queue features

### Phase 5: Federation - 8-10 weeks (Optional)
- Federated work coordination
- Cross-workspace work claiming
- Reputation system
- Evidence submission

---

## Key Metrics to Track

### Code Quality
- Lines of code reduction: Target -40%
- Test coverage: Target 95%+
- Bug escape rate
- Code reuse percentage

### Performance
- Cost reduction: Target -25%
- Time reduction: Target -35%
- Token reduction: Target -40%

### Reliability
- Agent uptime: Target 99%+
- Merge queue throughput
- Escalation resolution time
- Context recovery time

### Scale
- Concurrent agents: Support 20-30+
- API rate limit compliance: Zero violations
- Session duration before handoff
- Work completion rate

---

## Open Questions & Decisions Needed

1. **Multi-model panel cost:** Balance decision quality vs. cost
2. **Grilling frequency:** How often vs. direct execution
3. **Test coverage threshold:** Selective vs. comprehensive
4. **Federation timing:** When to add Federation Layer
5. **Telemetry privacy:** Default on/off/local-only
6. **Minimalism enforcement:** Prompt-level vs. verification-level
7. **Escalation thresholds:** P0 vs. P1 vs. P2 triggers
8. **Session handoff:** When to hand off vs. continue

---

## Next Steps

1. **Review & Approval:** Stakeholder review of technical design
2. **Prototype:** Build Phase 1 MVP (8-12 weeks)
3. **Testing:** Comprehensive testing strategy
4. **Documentation:** Developer documentation and API docs
5. **Deployment:** Production deployment plan

---

## Document Maintenance

This technical design specification should be updated as:
- Architecture decisions change
- New modules are added
- Technology choices evolve
- Performance requirements change

**Last Updated:** October 18, 2026  
**Next Review:** November 18, 2026
