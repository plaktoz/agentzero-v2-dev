# hook-store

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](README.md)
> **Independence:** no dependency on UMAS or on any database. Git is the only requirement.

---

## 1. Purpose

A **hook** is a git worktree bound to one unit of work. Everything needed to resume that work is committed to the hook's branch, so the work survives process crashes, machine restarts, and a change of worker.

`hook-store` creates, tracks, checkpoints, recovers, transfers, and garbage-collects hooks. It does not know what the work is or who does it.

## 2. Scope and Non-Goals

**In scope**
- Creating and removing worktrees under one root directory
- A structured state file committed to each hook
- Checkpoint commits, with optional "signal" tags that other processes can detect
- Ownership leases and liveness
- Stale and dirty classification, and safe garbage collection
- Recovery: reading the last committed state and any uncommitted work

**Non-goals**
- Task scheduling, assignment, or dependency tracking
- Merging hooks into a target branch (see [merge-queue](merge-queue.md))
- Storing events (see [event-log](event-log.md))
- Any database. The registry is derived from git plus lease files.

## 3. Concepts and Data Model

### 3.1 Directory layout

```
<root>/                         default: .hooks/   (parameter)
  <hook-name>/                  a git worktree; branch = <branch_prefix>/<hook-name>
    STATE.md                    committed state file (section 3.2)
  .leases/
    <hook-name>.json            lease file (section 3.3); NOT in the worktree, never committed
```

`<root>` SHOULD be git-ignored by the consumer. The library never edits `.gitignore`.

### 3.2 State file (`STATE.md`)

YAML front matter plus free-form markdown body. The library reads and writes only the front matter; the body is opaque to it.

```yaml
---
schema_version: 1
hook: auth-login
task: "Implement login endpoint"      # free text
owner: alice                          # last owner that wrote the file
base_branch: main
created_at: 2026-10-19T10:00:00Z
updated_at: 2026-10-19T10:23:01Z
progress_percent: 40                  # 0-100, advisory
decisions:                            # newest last; capped at max_decisions (default 10), oldest dropped
  - { at: 2026-10-19T10:10:00Z, decision: "Use bcrypt", rationale: "already a dependency" }
next_steps: ["email validation", "rate limit"]
refs:                                 # pointers, not content
  - { path: src/auth/login.py, lines: "10-60" }
---
Free-form notes follow here.
```

`write_state` replaces the front matter atomically (write temp, fsync, rename), then the caller commits it with `checkpoint`.

### 3.3 Lease

```json
{ "schema_version": 1, "hook": "auth-login", "owner": "alice", "pid": 4242,
  "host": "devbox", "acquired_at": "...", "heartbeat_at": "..." }
```

A lease is **live** if `now - heartbeat_at < lease_ttl` (default 5 min) and, when `host` equals the local host, `pid` is alive. Holders refresh by calling `heartbeat`.

### 3.4 Hook status

| Status | Meaning |
|--------|---------|
| `active` | A live lease exists |
| `idle` | No live lease, last activity younger than `stale_after` (default 24h) |
| `stale` | No live lease, last activity at least `stale_after` old |
| `completed` | Marked complete by the owner (`complete`) |
| `abandoned` | Marked abandoned (`abandon`), or stale beyond `abandon_after` and confirmed by the caller |

`dirty` (uncommitted changes in the worktree) is a **separate boolean**, not a status. A hook can be `stale` and `dirty` at once, which a UI may show as `STALE-DIRTY`.

*Last activity* = the later of the last commit time and the last lease heartbeat.

### 3.5 HookInfo

`{ name, path, branch, status, dirty, owner, lease_live, last_commit, last_activity_at, age, base_branch }`

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `create(name, base_branch, owner, task?) -> HookInfo` | Add worktree, create branch, write initial `STATE.md`, commit it, acquire lease. Fails `AlreadyExists` if present. |
| `open(name, owner) -> HookInfo` | Acquire lease on an existing hook. Fails `LeaseHeld` if another live lease exists. |
| `heartbeat(name, owner)` | Refresh lease. |
| `read_state(name) -> State` | Parse front matter from the working copy. |
| `write_state(name, patch)` | Merge `patch` into the front matter atomically. Enforces `max_decisions`. |
| `checkpoint(name, summary, signal?, files?) -> CommitId` | Stage `files` (default all tracked and new, minus ignored), commit. Message per section 5.2. A no-op commit returns the current `HEAD` without error. |
| `find_signals(name, pattern, since?) -> [Commit]` | Return commits whose message matches `pattern`. Lets a scheduler detect completion with no shared database. |
| `recover(name) -> Recovery` | Return `{ last_committed_state, last_commit, dirty, uncommitted_diff_stat, lease }`. Read-only. |
| `transfer(name, from_owner, to_owner)` | Hand the lease over. Requires `from_owner` to hold it, or `force: true` when the lease is not live. |
| `complete(name)` / `abandon(name, reason)` | Release the lease and set the terminal status in `STATE.md` (committed). |
| `list(filter?) -> [HookInfo]` | Reconcile `git worktree list --porcelain`, lease files, and directories under `<root>`. |
| `gc(policy, dry_run=true) -> GcReport` | Section 5.4. |
| `remove(name, force=false)` | Remove the worktree directory. Refuses if `dirty` unless `force`. The branch is kept unless `delete_branch`. |

All operations are also available as `hook-store <op> --json`.

## 5. Behaviour

### 5.1 Create

1. Validate `name` against `^[a-z0-9][a-z0-9._-]{0,63}$`.
2. `git worktree add -b <branch_prefix>/<name> <root>/<name> <base_branch>`.
3. Write `STATE.md`, commit as a `checkpoint` with summary `hook created`.
4. Write the lease. If any step fails, roll back what was done (remove the worktree and branch it created) and return the original error.

### 5.2 Commit message format

`<signal_prefix?> <summary>` followed by trailers:

```
[done] task-123 finished login endpoint

Hook: auth-login
Owner: alice
Tokens: 41200          # only if the caller passes tags
```

- `signal` is an opaque string supplied by the caller (`done`, `checkpoint`, ...), rendered through the `signal_format` template (default `[{signal}]`). The library assigns no meaning to any signal.
- `tags` (a string map) become git trailers.
- `find_signals` matches against the subject line and trailers.

### 5.3 Concurrency

- Git operations for one repo are serialized by a repo-level advisory lock. If `index.lock` is present, retry with backoff up to `git_lock_timeout` (default 10s), then fail `GitBusy`.
- Per-hook mutations (`write_state`, `checkpoint`, `transfer`) require the caller to hold the lease. Otherwise `NotOwner`.
- Reads (`list`, `recover`, `read_state`) take no locks.

### 5.4 Garbage collection

`gc` never deletes by default (`dry_run=true`). With `dry_run=false`:

| Condition | Action |
|-----------|--------|
| `active` | Never touched |
| `idle` | Kept (the owner may still return) |
| `stale`, clean | Report. Remove only if older than `prune_stale_after` (default 7d) **and** `auto_remove=true` |
| `stale`, **dirty** | **Never removed.** Report as `needs_attention` with the diff stat |
| `completed`, clean | Remove after `prune_completed_after` (default 48h) |
| `abandoned`, clean | Remove after `prune_abandoned_after` (default 7d) |

Removing a worktree directory leaves its branch in the repository, so committed work is not lost. Deleting branches is a separate, explicit option.

### 5.5 Recovery

`recover` makes no changes. The caller decides among: resume from `last_committed_state`; commit the dirty work as a recovery checkpoint; discard it; or hand the hook to a new owner with `transfer`. The library provides `checkpoint` and `transfer` for these but never decides.

## 6. Configuration

```yaml
root: .hooks
branch_prefix: hook
signal_format: "[{signal}]"
lease_ttl_seconds: 300
stale_after_hours: 24
abandon_after_hours: 168
max_decisions: 10
git_lock_timeout_seconds: 10
gc:
  auto_remove: false
  prune_stale_after_hours: 168
  prune_completed_after_hours: 48
  prune_abandoned_after_hours: 168
```

## 7. Failure Modes

| Error | Cause | Behaviour |
|-------|-------|-----------|
| `NotAGitRepo` | `repo` is not a git repository | Fail, no side effects |
| `AlreadyExists` | Hook name or branch exists | Fail, no side effects |
| `LeaseHeld` | Another live lease | Fail. Caller may `transfer --force` only when not live |
| `NotOwner` | Mutation without the lease | Fail |
| `GitBusy` | Lock not released in time | Fail, retryable |
| `StateCorrupt` | Front matter missing or invalid | `recover` still returns git facts and sets `state: null`. A merge conflict marker in `STATE.md` counts as corrupt |
| `DirtyRefused` | `remove` without `force` on a dirty hook | Fail, return diff stat |
| `WorktreeMissing` | Registered by git but directory gone | `list` reports `missing`; `git worktree prune` is run only by `gc` |
| `DiskFull` | Write or commit fails ENOSPC | Fail, leave the previous committed state intact. State writes are atomic, so no partial `STATE.md` |

## 8. Acceptance Criteria

1. Killing the holder process (`kill -9`) mid-edit, then `recover`, returns the last checkpoint's state and reports the uncommitted files.
2. `list` returns the right status for each combination of lease live/expired, clean/dirty, and age buckets, using a fake clock.
3. `gc --apply` never removes a dirty hook, under any age or policy.
4. Two processes calling `create` with the same name: exactly one succeeds.
5. `checkpoint` with no changes does not fail and does not create an empty commit.
6. `find_signals` finds a signal commit written by a different process with no shared state besides git.
7. Operation set works against a repository with 200 hooks in under 2 seconds for `list`.
8. Every persisted file validates against its JSON/YAML schema; version N-1 files are readable.

## 9. How UMAS Uses It

| UMAS concept | hook-store parameter or call |
|--------------|-----------------------------|
| `.umas/worktrees/<hook>/` | `root = .umas/worktrees` |
| `[umas] <agent> <step> [tokens: N]` | `checkpoint(signal=null, tags={Tokens: N})` with `signal_format` customised |
| `[umas:done] <task-id>` | `checkpoint(signal="umas:done")`; the Scheduler calls `find_signals("umas:done")` |
| `[umas:checkpoint] <summary>` | `checkpoint(signal="umas:checkpoint")`; Project Monitor reads `last_activity_at` |
| Stale worktrees (exception flow 4.8) | `list` + `gc`; `umas worktrees recover` uses `recover` + `transfer` |
| Handoff packet source | `read_state` (`decisions`, `next_steps`, `refs`) |

## 10. Source Material and Deviations

Extracted from `TECHNICAL-DESIGN-SPEC.md` §3.2 (Rust `WorktreeService`), `UMAS-TECH-DESIGN-SPEC.md` §3.1, §3.3 (signalling), and §4.8 (stale worktrees).

| Deviation | Why |
|-----------|-----|
| No `worktrees` / `commit_events` tables | Source of truth is git plus lease files. Removes the DB dependency, and removes the Postgres (`PgPool`) vs. SQLite default mismatch in the source |
| `STATE.md` with structured front matter, not `.umas/state.json` | The source specs disagree (`STATE.md` in the design spec, `state.json` in the Rust code). One human-readable file serves both people and tools |
| Worktree keyed by hook name, not agent ID | The design spec says work is tied to the hook, not the agent (hooks outlive agents). The Rust code keys by `agent_id`, which breaks handoff |
| Lease replaces "session record" | Liveness no longer needs a database table |

## 11. Open Questions

1. Should `checkpoint` support `git commit --no-verify`, or always run the repo's hooks? (Default proposal: run hooks, with an opt-out option.)
2. Multi-host leases: pid checks only work locally. Is the TTL-only fallback acceptable for shared filesystems?
3. Should `gc` be allowed to delete branches for abandoned hooks, or is that always manual?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Code moved verbatim from the original UMAS technical design. It illustrates one way to implement this spec and uses UMAS names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [libs/README.md](README.md).

### 12.1 WorktreeService (Rust)

Source: `TECHNICAL-DESIGN-SPEC.md` §3.2.2

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

### 12.2 Worktree data structures (Rust)

Source: `TECHNICAL-DESIGN-SPEC.md` §3.2.3

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

### 12.3 Worktree configuration (YAML)

Source: `TECHNICAL-DESIGN-SPEC.md` §3.2.4

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

### 12.4 Database schema (SQL)

Source: `TECHNICAL-DESIGN-SPEC.md` §3.2.5

> **Note:** `libs/hook-store.md` §3 defines a file-based data model (`STATE.md`, lease files). This SQL schema is retained here as a historical reference. It represents the original design that stored worktree state in a database rather than in the worktree directory itself.

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
