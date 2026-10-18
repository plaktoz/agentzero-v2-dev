# Technical Design Specification: Unified Multi-Agent Development System

**Version:** 1.1
**Date:** October 18, 2026
**Status:** Active
**Based on:** [unified-multi-agent-system-prd.md](unified-multi-agent-system-prd.md)

## Document Set

This file is part of a reconciled document set. Read all four together:

| Document | Covers |
|----------|--------|
| **TECHNICAL-DESIGN-SPEC.md** ← you are here | Technology stack, system architecture, Context Persistence implementation |
| [TECHNICAL-DESIGN-SPEC-PART2.md](TECHNICAL-DESIGN-SPEC-PART2.md) | Orchestration System, Agent Execution System implementation |
| [TECHNICAL-DESIGN-SPEC-PART3.md](TECHNICAL-DESIGN-SPEC-PART3.md) | Verification System, Monitoring System implementation |
| [UMAS-TECH-DESIGN-SPEC.md](UMAS-TECH-DESIGN-SPEC.md) | Component design decisions, exception flows, resolved PRD conflicts |

**Reading order:** Start with [UMAS-TECH-DESIGN-SPEC.md](UMAS-TECH-DESIGN-SPEC.md) for design decisions, then read this file and Parts 2–3 for implementation detail.

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Module 1: Context Persistence System](#3-module-1-context-persistence-system)
4. [Module 2: Orchestration System](#4-module-2-orchestration-system)
5. [Module 3: Agent Execution System](#5-module-3-agent-execution-system)
6. [Module 4: Verification System](#6-module-4-verification-system)
7. [Module 5: Monitoring System](#7-module-5-monitoring-system)
8. [Module 6: Human Interface System](#8-module-6-human-interface-system)
9. [Module 7: Multi-Agent Platform Support](#9-module-7-multi-agent-platform-support)
10. [Module 8: Error Handling & Recovery](#10-module-8-error-handling--recovery)
11. [Module 9: Installation & Deployment](#11-module-9-installation--deployment)
12. [Module 10: Agent Handoff & Token Management](#12-module-10-agent-handoff--token-management)
13. [Data Models & Schemas](#13-data-models--schemas)
14. [API Specifications](#14-api-specifications)
15. [Security Architecture](#15-security-architecture)
16. [Performance & Scalability](#16-performance--scalability)
17. [Testing Strategy](#17-testing-strategy)
18. [Deployment Architecture](#18-deployment-architecture)

---

## 1. Technology Stack

### 1.1 Confirmed Technology Stack

Based on PRD analysis, the following technology stack is confirmed:

#### Core Infrastructure
```yaml
daemon_and_core_services:
  primary_language: Rust
  version: "1.70+"
  rationale: |
    - Cross-platform compatibility (Windows, Linux, macOS)
    - Memory safety and performance
    - Single binary distribution
    - Excellent async runtime (Tokio)
  
  key_dependencies:
    tokio: "1.32+"           # Async runtime
    clap: "4.4+"             # CLI framework with shell completion
    serde: "1.0+"            # Serialization/deserialization
    sqlx: "0.7+"             # Async SQL with compile-time verification
    anyhow: "1.0+"           # Error handling
    tracing: "0.1+"          # Structured logging
    uuid: "1.4+"             # UUID generation
    
agent_runtime:
  primary_language: Python
  version: "3.10+"
  rationale: |
    - Rich AI/ML ecosystem
    - Excellent LLM SDK support
    - Rapid development for agent logic
    - Strong async support
  
  key_dependencies:
    anthropic: "0.7+"                    # Claude SDK
    openai: "1.3+"                       # OpenAI SDK
    google-generativeai: "0.3+"          # Gemini SDK
    pydantic: "2.4+"                     # Data validation
    asyncio: "built-in"                  # Async support
    aiofiles: "23.2+"                    # Async file I/O
    gitpython: "3.1+"                    # Git operations
    sqlalchemy: "2.0+"                   # ORM
    alembic: "1.12+"                     # Database migrations
```

#### Alternative Stack (Node.js Option)
```yaml
daemon_and_core_services:
  alternative_language: TypeScript
  runtime: Node.js
  version: "18+"
  
  key_dependencies:
    commander: "11.0+"       # CLI framework
    prisma: "5.4+"           # Database ORM
    zod: "3.22+"             # Schema validation
    
agent_runtime:
  alternative_language: TypeScript
  runtime: Node.js
  version: "18+"
  
  key_dependencies:
    "@anthropic-ai/sdk": "0.9+"
    "openai": "4.14+"
    "@google/generative-ai": "0.1+"
```

### 1.2 Data Storage Layer

#### Version Control System
```yaml
git:
  minimum_version: "2.30+"
  required_features:
    - worktree_support: true
    - hooks: true
    - sparse_checkout: true
  
  configuration:
    worktree_base_path: ".umas/worktrees/"
    hooks_path: ".umas/hooks/"
    branch_prefix: "agent/"
```

#### Database Systems
```yaml
development_tier:
  engine: SQLite
  version: "3.35+"
  file_location: "~/.umas/database.db"
  features:
    wal_mode: true              # Write-Ahead Logging
    foreign_keys: true
    json_support: true
  max_concurrent_agents: 5
  
production_tier:
  engine: PostgreSQL
  version: "14+"
  connection_pool:
    min_connections: 5
    max_connections: 50
    idle_timeout: 300
  features:
    jsonb_support: true
    full_text_search: true
    table_partitioning: true
  max_concurrent_agents: 30+
  
metrics_storage:
  engine: TimescaleDB (PostgreSQL extension)
  version: "2.11+"
  retention_policy: 90_days
  aggregation_interval: 60_seconds
```

### 1.3 LLM Provider Integration

#### Supported Providers
```yaml
tier_1_full_integration:
  anthropic_claude:
    sdk: anthropic-python / anthropic-ts
    models:
      - claude-3-5-sonnet-20241022
      - claude-3-opus-20240229
      - claude-3-sonnet-20240229
    features:
      hooks_support: true
      streaming: true
      function_calling: true
      max_tokens: 200000
    
  ibm_bob:
    sdk: custom_http_client
    endpoint: "https://bob.ibm.com/api/v1"
    models:
      - bob-enterprise-v1
    features:
      hooks_support: true
      enterprise_auth: true
      audit_logging: true
      compliance_mode: true
    
  openai_gpt:
    sdk: openai-python / openai-ts
    models:
      - gpt-4-turbo
      - gpt-4
      - gpt-3.5-turbo
    features:
      hooks_support: false
      streaming: true
      function_calling: true
      max_tokens: 128000

tier_2_basic_integration:
  google_gemini:
    sdk: google-generativeai
    models:
      - gemini-1.5-pro
      - gemini-1.5-flash
    features:
      hooks_support: false
      streaming: true
      max_tokens: 1000000
  
  local_llm:
    sdk: ollama-python
    endpoint: "http://localhost:11434"
    models:
      - llama3
      - codellama
    features:
      hooks_support: false
      offline_mode: true
```

### 1.4 Observability Stack

```yaml
telemetry_framework:
  protocol: OpenTelemetry
  version: "1.20+"
  
  exporters:
    metrics:
      - prometheus
      - statsd
    
    traces:
      - jaeger
      - zipkin
      - tempo
    
    logs:
      - loki
      - elasticsearch
      - cloudwatch

logging:
  format: json
  library: 
    rust: tracing
    python: structlog
  
  levels:
    - DEBUG
    - INFO
    - WARN
    - ERROR
    - CRITICAL
  
  structured_fields:
    - timestamp
    - level
    - service
    - agent_id
    - session_id
    - task_id
    - trace_id
    - span_id

metrics:
  backend: Prometheus
  retention: 90_days
  scrape_interval: 15_seconds
  aggregation_interval: 60_seconds
  
  dashboards:
    - grafana
    - built_in_dashboard

tracing:
  backend: Jaeger
  sampling_strategy:
    development: 1.0      # 100%
    staging: 1.0          # 100%
    production: 0.01      # 1%
  
  trace_context_propagation: W3C Trace Context
```

### 1.5 Web Dashboard

```yaml
frontend:
  framework: React
  version: "18+"
  language: TypeScript
  
  state_management: Zustand
  ui_library: shadcn/ui
  styling: Tailwind CSS
  build_tool: Vite
  
  key_dependencies:
    react: "18+"
    react-router-dom: "6+"
    zustand: "4+"
    @tanstack/react-query: "5+"
    socket.io-client: "4+"
    recharts: "2+"          # Charts
    lucide-react: "0.263+"  # Icons

backend_api:
  framework: FastAPI (Python) OR Express (Node.js)
  version: "0.104+" (FastAPI) OR "4.18+" (Express)
  
  features:
    - REST API
    - WebSocket support
    - JWT authentication
    - CORS configuration
    - Rate limiting
  
  websocket: Socket.io
  api_documentation: OpenAPI 3.0 (Swagger)
```

---

## 2. System Architecture Overview

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HUMAN INTERFACE LAYER                        │
│  ┌──────────┐  ┌───────────┐  ┌─────────────┐  ┌─────────────┐│
│  │   CLI    │  │ Dashboard │  │   Metrics   │  │ Escalation  ││
│  │ (Rust)   │  │  (React)  │  │   Display   │  │  Channels   ││
│  └────┬─────┘  └─────┬─────┘  └──────┬──────┘  └──────┬──────┘│
└───────┼──────────────┼────────────────┼─────────────────┼───────┘
        │              │                │                 │
        │ Unix Socket  │ HTTP/WS        │ IPC             │ Webhook
        │              │                │                 │
┌───────▼──────────────▼────────────────▼─────────────────▼───────┐
│                    ORCHESTRATION LAYER                           │
│  ┌──────────────┐  ┌──────────┐  ┌────────────────────────┐   │
│  │ Coordinator  │  │  Router  │  │     Scheduler          │   │
│  │  (Python)    │  │ (Python) │  │ (Rust - Capacity Mgmt) │   │
│  └──────┬───────┘  └────┬─────┘  └───────────┬────────────┘   │
└─────────┼───────────────┼────────────────────┼─────────────────┘
          │               │                    │
          │ Task Queue    │ Skill Selection    │ Resource Allocation
          │               │                    │
┌─────────▼───────────────▼────────────────────▼─────────────────┐
│                   AGENT EXECUTION LAYER                          │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │   Worker    │  │   Specialized    │  │     Review       │  │
│  │   Agents    │  │     Agents       │  │     Agents       │  │
│  │  (Python)   │  │ (PM/Arch/UX/Dev) │  │ (Code/Audit/TDD) │  │
│  └──────┬──────┘  └────────┬─────────┘  └────────┬─────────┘  │
└─────────┼──────────────────┼────────────────────┼──────────────┘
          │                  │                    │
          │ Git Operations   │ File I/O           │ Test Execution
          │                  │                    │
┌─────────▼──────────────────▼────────────────────▼──────────────┐
│                     VERIFICATION LAYER                           │
│  ┌──────────────┐  ┌─────────────┐  ┌────────────────────┐    │
│  │ Merge Queue  │  │ Test Runner │  │ Minimalism Checker │    │
│  │  Processor   │  │  (TDD/E2E)  │  │ (Ladder Enforcer)  │    │
│  │  (Python)    │  │   (Rust)    │  │     (Python)       │    │
│  └──────┬───────┘  └──────┬──────┘  └─────────┬──────────┘    │
└─────────┼──────────────────┼────────────────────┼───────────────┘
          │                  │                    │
          │ Health Checks    │ Metrics Collection │ Event Logging
          │                  │                    │
┌─────────▼──────────────────▼────────────────────▼───────────────┐
│                      MONITORING LAYER                            │
│  ┌────────┐  ┌──────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ Daemon │→│  Triage  │→│System Patrol │→│   Project   │ │
│  │ (Rust) │  │  Agent   │  │   (Python)   │  │  Monitors   │ │
│  │        │  │ (Python) │  │              │  │  (Python)   │ │
│  └────┬───┘  └─────┬────┘  └──────┬───────┘  └──────┬──────┘ │
└───────┼────────────┼───────────────┼──────────────────┼─────────┘
        │            │               │                  │
        │ Persistence│ State Mgmt    │ Metrics Storage  │ Artifacts
        │            │               │                  │
┌───────▼────────────▼───────────────▼──────────────────▼─────────┐
│                     PERSISTENCE LAYER                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │   Git    │  │   Task   │  │ Decision │  │   Metrics    │  │
│  │ Worktrees│  │ Database │  │Artifacts │  │   Database   │  │
│  │  (Hooks) │  │(SQLite/  │  │ (Files)  │  │ (TimeSeries) │  │
│  │          │  │Postgres) │  │          │  │              │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Communication Patterns

```yaml
inter_process_communication:
  cli_to_daemon:
    protocol: Unix Domain Socket (Linux/macOS)
    protocol_windows: Named Pipe
    format: JSON-RPC 2.0
    timeout: 30_seconds
    
  daemon_to_agents:
    protocol: Process spawn with stdio
    format: JSON Lines (JSONL)
    stdin: commands
    stdout: responses
    stderr: logs
    
  agents_to_git:
    protocol: Git CLI subprocess
    operations:
      - worktree add/remove/list
      - commit
      - checkout
      - merge
      - diff
    
  agents_to_database:
    protocol: SQL over connection pool
    orm: SQLAlchemy (Python) / Prisma (Node.js)
    connection_string: "postgresql://user:pass@host/db"
    
  dashboard_to_daemon:
    rest_api:
      protocol: HTTP/HTTPS
      format: JSON
      auth: JWT Bearer tokens
      base_path: "/api/v1"
    
    websocket:
      protocol: WebSocket
      library: Socket.io
      events:
        - agent_status_update
        - task_progress
        - escalation_created
        - merge_queue_update
    
  telemetry_export:
    protocol: OpenTelemetry Protocol (OTLP)
    format: Protobuf
    endpoints:
      metrics: "http://prometheus:9090"
      traces: "http://jaeger:14268"
      logs: "http://loki:3100"
```

### 2.3 Process Model

```yaml
system_processes:
  daemon:
    type: long_running_service
    language: Rust
    lifecycle: system_service
    start_mode: automatic
    restart_policy: always
    
    responsibilities:
      - Process lifecycle management
      - Health monitoring (watchdog)
      - IPC coordination
      - Resource allocation
      - Configuration management
    
    resource_limits:
      memory: 512MB
      cpu: 1_core
    
  agents:
    type: ephemeral_workers
    language: Python
    lifecycle: task_scoped
    spawn_method: subprocess
    isolation: process_boundary
    
    responsibilities:
      - Task execution
      - Code generation
      - Decision making
      - State persistence
    
    resource_limits:
      memory: 2GB_per_agent
      cpu: 2_cores_per_agent
      max_concurrent: 30
    
  cli:
    type: short_lived_client
    language: Rust
    lifecycle: command_execution
    communication: IPC_to_daemon
    timeout: 300_seconds
    
  dashboard_server:
    type: long_running_service
    language: TypeScript/Node.js
    lifecycle: web_server
    port: 3000
    restart_policy: on_failure
    
    resource_limits:
      memory: 256MB
      cpu: 0.5_core
```

---

## 3. Module 1: Context Persistence System

### 3.1 Overview

The Context Persistence System ensures agent work state survives crashes and restarts through version-controlled storage and structured artifacts.

### 3.2 Submodule: Git Worktree Manager

#### 3.2.1 Purpose
Manage Git worktrees (hooks) for agent state persistence, enabling crash recovery and agent handoff.

#### 3.2.2 Architecture

```rust
// Core service implementation (Rust)
pub struct WorktreeService {
    repo_path: PathBuf,
    worktree_base: PathBuf,
    git_client: Arc<GitClient>,
    db_pool: PgPool,
}

impl WorktreeService {
    /// Create a new worktree for an agent
    pub async fn create_worktree(
        &self,
        agent_id: &str,
        task_id: &str,
        base_branch: &str,
    ) -> Result<Worktree, WorktreeError> {
        let worktree_path = self.worktree_base.join(agent_id);
        let branch_name = format!("agent/{}/{}", agent_id, task_id);
        
        // Ensure worktree doesn't already exist
        if worktree_path.exists() {
            return Err(WorktreeError::AlreadyExists(agent_id.to_string()));
        }
        
        // Create worktree via Git
        self.git_client
            .worktree_add(&worktree_path, &branch_name, base_branch)
            .await?;
        
        // Record in database
        let worktree = Worktree {
            id: Uuid::new_v4(),
            agent_id: agent_id.to_string(),
            task_id: task_id.to_string(),
            path: worktree_path.clone(),
            branch: branch_name.clone(),
            created_at: Utc::now(),
            status: WorktreeStatus::Active,
        };
        
        sqlx::query!(
            "INSERT INTO worktrees (id, agent_id, task_id, path, branch, created_at, status)
             VALUES ($1, $2, $3, $4, $5, $6, $7)",
            worktree.id,
            worktree.agent_id,
            worktree.task_id,
            worktree.path.to_str(),
            worktree.branch,
            worktree.created_at,
            worktree.status as _,
        )
        .execute(&self.db_pool)
        .await?;
        
        Ok(worktree)
    }
    
    /// Remove worktree when agent completes
    pub async fn remove_worktree(
        &self,
        agent_id: &str,
    ) -> Result<(), WorktreeError> {
        let worktree_path = self.worktree_base.join(agent_id);
        
        // Remove via Git
        self.git_client
            .worktree_remove(&worktree_path, true)
            .await?;
        
        // Update database
        sqlx::query!(
            "UPDATE worktrees SET status = $1, removed_at = $2
             WHERE agent_id = $3 AND status = $4",
            WorktreeStatus::Removed as _,
            Utc::now(),
            agent_id,
            WorktreeStatus::Active as _,
        )
        .execute(&self.db_pool)
        .await?;
        
        Ok(())
    }
    
    /// List all active worktrees
    pub async fn list_worktrees(&self) -> Result<Vec<Worktree>, WorktreeError> {
        let worktrees = sqlx::query_as!(
            Worktree,
            "SELECT * FROM worktrees WHERE status = $1 ORDER BY created_at DESC",
            WorktreeStatus::Active as _,
        )
        .fetch_all(&self.db_pool)
        .await?;
        
        Ok(worktrees)
    }
    
    /// Commit agent state to worktree
    pub async fn commit_state(
        &self,
        agent_id: &str,
        message: &str,
        files: Vec<PathBuf>,
    ) -> Result<CommitHash, WorktreeError> {
        let worktree_path = self.worktree_base.join(agent_id);
        
        // Stage files
        for file in &files {
            self.git_client
                .add(&worktree_path, file)
                .await?;
        }
        
        // Commit
        let commit_hash = self.git_client
            .commit(&worktree_path, message)
            .await?;
        
        // Log commit event
        self.log_commit_event(agent_id, &commit_hash, message, &files)
            .await?;
        
        Ok(commit_hash)
    }
    
    /// Recover agent state from worktree
    pub async fn recover_state(
        &self,
        agent_id: &str,
    ) -> Result<AgentState, WorktreeError> {
        let worktree_path = self.worktree_base.join(agent_id);
        
        // Read state file from worktree
        let state_file = worktree_path.join(".umas").join("state.json");
        let state_content = tokio::fs::read_to_string(&state_file).await?;
        let state: AgentState = serde_json::from_str(&state_content)?;
        
        Ok(state)
    }
    
    async fn log_commit_event(
        &self,
        agent_id: &str,
        commit_hash: &CommitHash,
        message: &str,
        files: &[PathBuf],
    ) -> Result<(), WorktreeError> {
        sqlx::query!(
            "INSERT INTO commit_events (id, agent_id, commit_hash, message, files, created_at)
             VALUES ($1, $2, $3, $4, $5, $6)",
            Uuid::new_v4(),
            agent_id,
            commit_hash.0,
            message,
            &files.iter().map(|p| p.to_str().unwrap()).collect::<Vec<_>>(),
            Utc::now(),
        )
        .execute(&self.db_pool)
        .await?;
        
        Ok(())
    }
}
```

#### 3.2.3 Data Structures

```rust
#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct Worktree {
    pub id: Uuid,
    pub agent_id: String,
    pub task_id: String,
    pub path: PathBuf,
    pub branch: String,
    pub created_at: DateTime<Utc>,
    pub status: WorktreeStatus,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, sqlx::Type)]
#[sqlx(type_name = "worktree_status", rename_all = "lowercase")]
pub enum WorktreeStatus {
    Active,
    Completed,
    Removed,
    Abandoned,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommitHash(pub String);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentState {
    pub task_id: String,
    pub progress: TaskProgress,
    pub context: HashMap<String, serde_json::Value>,
    pub decisions: Vec<Decision>,
    pub next_steps: Vec<String>,
    pub files_modified: Vec<PathBuf>,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskProgress {
    pub completed: Vec<String>,
    pub current: Option<String>,
    pub current_progress_percent: u8,
    pub pending: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decision {
    pub id: Uuid,
    pub description: String,
    pub rationale: String,
    pub alternatives_considered: Vec<String>,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, thiserror::Error)]
pub enum WorktreeError {
    #[error("Git operation failed: {0}")]
    GitError(String),
    
    #[error("Worktree already exists: {0}")]
    AlreadyExists(String),
    
    #[error("Worktree not found: {0}")]
    NotFound(String),
    
    #[error("Database error: {0}")]
    DatabaseError(#[from] sqlx::Error),
    
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
    
    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),
}
```

#### 3.2.4 Configuration

```yaml
worktree_config:
  base_path: ".umas/worktrees"
  branch_prefix: "agent"
  
  lifecycle:
    auto_cleanup: true
    cleanup_after_hours: 24
    max_worktrees_per_agent: 1
    prune_completed_after_hours: 48
    prune_abandoned_after_hours: 168  # 7 days
  
  commit_strategy:
    auto_commit: true
    commit_interval_seconds: 300  # Every 5 minutes
    commit_on_tool_use: true
    commit_on_decision: true
    # Signal format for UMAS orchestration layer:
    #   completion  → "[umas:done] <task-id>"
    #   checkpoint  → "[umas:checkpoint] <summary>"
    #   general     → "[umas] <agent-id> <step-summary> [tokens: N]"
    commit_message_template: "[umas] {agent_id} {operation}: {description}"
  
  state_persistence:
    state_file: ".umas/state.json"
    backup_interval_seconds: 60
    max_backups: 10
```

#### 3.2.5 Database Schema

```sql
-- Worktrees table
CREATE TABLE worktrees (
    id UUID PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    path TEXT NOT NULL,
    branch VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    removed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL,
    
    INDEX idx_agent_id (agent_id),
    INDEX idx_task_id (task_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Commit events table
CREATE TABLE commit_events (
    id UUID PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    commit_hash VARCHAR(40) NOT NULL,
    message TEXT NOT NULL,
    files TEXT[] NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    INDEX idx_agent_id (agent_id),
    INDEX idx_commit_hash (commit_hash),
    INDEX idx_created_at (created_at)
);
```

### 3.3 Submodule: Decision Artifacts Manager

#### 3.3.1 Purpose
Manage decision artifacts (PRFAQ, ADR, Specs, GLOSSARY.md, Shortcut Comments) for durable context.

#### 3.3.2 Architecture

```python
# Python implementation
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from enum import Enum
import yaml
import json
import uuid

class ArtifactType(Enum):
    PRFAQ = "prfaq"
    ADR = "adr"
    SPEC = "spec"
    GLOSSARY = "glossary"
    SHORTCUT = "shortcut"

@dataclass
class Artifact:
    id: str
    type: ArtifactType
    title: str
    content: str
    author: str
    created_at: datetime
    updated_at: datetime
    file_path: Path
    metadata: Dict

class ArtifactService:
    def __init__(self, project_root: Path, db_session):
        self.project_root = project_root
        self.artifacts_dir = project_root / "docs" / "decisions"
        self.glossary_path = project_root / "GLOSSARY.md"
        self.db = db_session
        
        # Ensure directories exist
        (self.artifacts_dir / "prfaq").mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "adr").mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "spec").mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "shortcuts").mkdir(parents=True, exist_ok=True)
    
    async def create_prfaq(
        self,
        title: str,
        press_release: str,
        faq: List[tuple[str, str]],
        author: str,
    ) -> Artifact:
        """Create a PRFAQ (Press Release + FAQ) document."""
        content = self._format_p