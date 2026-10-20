# UMAS Setup & Multi-Project Operations Guide

> Final outcome reference for running the Unified Multi-Agent Development System across multiple projects.

---

## 1. Global Installation (Once, Machine-Wide)

Install the CLI globally using your preferred package manager:

```bash
npm install -g unified-multi-agent-system
# or
pip install unified-multi-agent-system
```

Set your LLM API key as an environment variable — never in config files:

```bash
export ANTHROPIC_API_KEY=your-key-here
# alternatives: OPENAI_API_KEY, GEMINI_API_KEY
```

Bootstrap the global state store:

```bash
umas init
# Creates ~/.umas/ with config.yaml, database.db, logs/, cache/
```

Verify the installation:

```bash
umas verify
# Checks: CLI, database, API connectivity, Git 2.30+, worktree support
```

---

## 2. Onboard Each Project

Projects live **wherever they already are** on your filesystem. UMAS attaches to them in place — it does not require projects to be inside any central directory.

From inside each repo:

```bash
cd ~/projects/my-api
umas init --project
# Creates .umas/ in this repo (gitignored)
# Chains Git hooks onto any existing ones — does not replace them
# Asks permission before touching anything

umas project register my-api
# Registers this project path in ~/.umas/database.db
```

Commit a `umas.config.yaml` to the repo so project rules are version-controlled:

```yaml
project:
  name: my-api
  type: development
  minimalism:
    level: full
    enforce: true
  testing:
    coverage_target: 80
    tdd_required: true
  review:
    required: true
    auto_merge: false
  token_efficiency:
    budget_per_task: 50000
  llm_provider:
    default: anthropic
    fallback: openai
```

Repeat for every project. Each gets its own `.umas/` directory and config entry.

---

## 3. File System Layout

```
~/.umas/                        ← global control plane (one per machine)
  config.yaml                   ← user-level defaults
  database.db                   ← references all registered projects by path
  logs/
  cache/

~/projects/my-api/              ← project lives wherever it always did
  .umas/                        ← gitignored, created by `umas init --project`
    config.yaml                 ← project-specific overrides
    hooks/                      ← Git hooks (optional, chained not replaced)
    worktrees/                  ← per-agent worktrees during active tasks
  umas.config.yaml              ← version-controlled project rules
  (all existing project files unchanged)

~/work/payments-svc/            ← separate project, any location
  .umas/
    ...

~/Desktop/experiment/           ← location does not matter
  .umas/
    ...
```

`~/.umas/database.db` stores a **path reference** to each project. It does not own or contain project files.

---

## 4. Configuration Resolution Order

Settings are resolved from highest to lowest priority:

| Priority | Source | Use for |
|----------|--------|---------|
| 1 (highest) | `UMAS_*` environment variables | CI secrets, temporary overrides |
| 2 | `.umas/config.yaml` | Per-project rules |
| 3 | `~/.umas/config.yaml` | Personal machine defaults |
| 4 | System defaults | Fallback |

---

## 5. Day-to-Day Operations

### Switch between projects

```bash
umas project list
umas project switch payments-svc
```

### Start the system

```bash
umas start-all    # coordinator, scheduler, watchdog, merge queue processor
umas status       # health check across all projects
```

### Submit work

```bash
# Brownfield — change request on existing code
umas request "Add rate limiting to the login endpoint"
# Coordinator audits existing code → asks one clarifying question
# Worker climbs minimalism ladder → reuses installed dependency → ~5 lines + test
# Merge queue batches with other PRs → tests merged stack → merges to main

# Greenfield — new service from scratch
umas request "Build a REST API for task management"
# PM agent writes PRFAQ, Architect agent writes ADR + picks tech stack
# 3 worker agents work in parallel (POST /tasks, GET /tasks, PUT /tasks/{id})
# Each in its own Git worktree under .umas/worktrees/
# Merge queue tests all 3 PRs together before merging
```

### Monitor progress

```bash
umas watch                          # real-time stream for active project
umas agents status                  # all agents across all projects
umas work-bundle show <bundle-name> # drill into a specific bundle
umas metrics tokens                 # per-project token burn
umas metrics cost                   # dollar cost breakdown
```

---

## 6. Capacity Tiers

| Tier | Max Concurrent Agents | Database | Typical Use |
|------|-----------------------|----------|-------------|
| MVP | 5 | SQLite (zero-config) | Solo developer |
| Production | 20 | PostgreSQL | Small team (5–10 devs) |
| Scale | 30+ | PostgreSQL + connection pooling | Large team, many projects |

Token budget alerts fire at **80% / 90% / 95%** of daily budget per project. On exhaustion, work **queues** — it does not fail.

---

## 7. Multi-Project State at a Glance

```
~/.umas/database.db
│
├── Project: my-api            → ~/projects/my-api/.umas/
│   ├── Active agents: 2
│   ├── Work bundles: rate-limit-login (in review)
│   └── Token budget: 32k / 50k used today
│
├── Project: payments-svc      → ~/work/payments-svc/.umas/
│   ├── Active agents: 0
│   └── Token budget: 5k / 50k used today
│
└── Project: frontend-app      → ~/Desktop/experiment/.umas/
    ├── Active agents: 3 (parallel greenfield build)
    ├── Work bundles: task-api (Alice, Bob, Charlie working)
    └── Token budget: 41k / 50k used today
```

Each project is fully isolated — its own worktrees, config, and session history. The global scheduler enforces the total concurrency cap across all projects to prevent API rate exhaustion.
