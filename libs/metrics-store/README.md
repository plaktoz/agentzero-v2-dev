# metrics-store

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS. Requires only a filesystem in Phase 1–2; a SQLite or PostgreSQL database in Phase 3+.
> **Storage decision:** file-based ledger first (Phase 1–2) → PostgreSQL `metrics` table (Phase 3+) → **never TimescaleDB** (see §10).

---

## 1. Purpose

Record scalar measurements — token counts, durations, costs, error rates, coverage percentages — from multiple processes, make them queryable by time window and dimension, and serve the `metrics *` CLI commands. The library has two backends behind one interface: a flat JSONL ledger (zero infrastructure) and a relational `metrics` table (SQL aggregates). The caller switches backends via configuration; application code does not change.

## 2. Scope and Non-Goals

**In scope**
- Recording scalar measurements with a name, value, timestamp, and optional tags
- Querying by name, time window, and tag filters with aggregation (sum, avg, min, max, percentile)
- 90-day retention policy with pruning
- Two backends: JSONL file ledger and a relational table (SQLite or PostgreSQL)
- Adapters that translate existing source ledgers (`budget-meter`, `event-log`, `test-adapters`) into metric rows without requiring those libraries to be modified
- A thin CLI for the `umas metrics *` commands

**Non-goals**
- Real-time streaming or push alerting. Budget threshold alerts belong to [budget-meter](../budget-meter/README.md); process health alerts to [watchdog](../watchdog/README.md).
- Distributed tracing or log aggregation. Those are OpenTelemetry concerns and are optional exports, not core storage.
- TimescaleDB. Standard PostgreSQL with a `(name, ts)` index is sufficient at UMAS scale. If query latency becomes a measured problem, `SELECT create_hypertable('metrics', 'ts')` upgrades the table in one statement with no application code change.
- Dashboards or chart rendering. The library returns structured data; visualisation is the CLI's or dashboard's job.
- Storing non-scalar payloads. Variable-depth data (test failure lists, review findings) belongs in [event-log](../event-log/README.md).

## 3. Concepts and Data Model

### 3.1 Measurement

One scalar observation:

```
Measurement:
  id:        string          # ULID
  ts:        string          # RFC 3339 UTC
  name:      string          # dot-separated, e.g. "token.used", "task.duration_ms"
  value:     float
  tags:      object          # { project, agent_id, model, task_type, ... } — all optional
```

Tag keys and values are strings. No schema enforcement — callers add whatever dimensions they need. The `name` is the only required label beyond `ts` and `value`.

### 3.2 Metric names (standard catalogue)

UMAS uses these names. The library enforces no catalogue; these are documented for consumers.

| Name | Unit | Source |
|------|------|--------|
| `token.input` | tokens | `budget-meter` ledger |
| `token.output` | tokens | `budget-meter` ledger |
| `token.cost` | USD | `budget-meter` ledger |
| `task.duration_ms` | ms | `event-log` (session_started → session_ended) |
| `task.handoff_rate` | 0–1 | `event-log` (handoff_initiated / session count) |
| `task.escalation_rate` | 0–1 | `event-log` (session_escalated / session count) |
| `merge_queue.success_rate` | 0–1 | `merge-queue` batch reports |
| `test.coverage_pct` | % | `test-adapters` result |
| `test.duration_ms` | ms | `test-adapters` result |
| `error.p0_count` | count | `error-classifier` observe ledger |
| `error.p1_count` | count | `error-classifier` observe ledger |

### 3.3 Query

```
Query:
  name:        string | string[]   # exact match or list
  since:       string?             # RFC 3339; default: 90 days ago
  until:       string?             # RFC 3339; default: now
  tags:        object?             # exact match on all specified keys
  aggregate:   "none"|"sum"|"avg"|"min"|"max"|"p50"|"p95"|"p99"
  group_by:    string[]?           # tag keys to group on, e.g. ["agent_id", "model"]
  limit:       int?                # for aggregate: "none" only
```

### 3.4 QueryResult

```
QueryResult:
  name:        string
  aggregate:   string
  groups:      GroupResult[]

GroupResult:
  tags:        object              # the grouped dimensions
  value:       float               # the aggregated value
  count:       int                 # number of measurements in this group
  since:       string
  until:       string
```

### 3.5 Backend: file ledger

```
<ledger_dir>/metrics.jsonl         # active segment — one Measurement JSON per line
<ledger_dir>/metrics.<seq>.jsonl   # rotated segments
```

Same format and rotation rules as [event-log](../event-log/README.md) §3.2. No shared code dependency — the format is reproduced here so the library is standalone. Queries fold all retained segments in order; aggregation runs in application memory. Suitable for Phase 1–2 (≤5 agents, ≤100k measurements).

### 3.6 Backend: relational table

```sql
CREATE TABLE metrics (
    id       TEXT    PRIMARY KEY,   -- ULID
    ts       TEXT    NOT NULL,      -- RFC 3339 UTC
    name     TEXT    NOT NULL,
    value    REAL    NOT NULL,
    tags     TEXT    NOT NULL       -- JSON object, defaults to '{}'
);

CREATE INDEX idx_metrics_name_ts ON metrics (name, ts);
CREATE INDEX idx_metrics_ts      ON metrics (ts);
```

Works identically in SQLite (TEXT timestamps, JSON functions) and PostgreSQL (TIMESTAMPTZ column preferred; `tags` as `JSONB` for index support on tag keys). The library handles both dialects behind the same interface. Migration from SQLite to PostgreSQL is a data copy — no schema transform needed.

**Tag queries in PostgreSQL:** with `tags JSONB`, tag filter `{ agent_id: "alice" }` becomes `WHERE tags->>'agent_id' = 'alice'`, which PostgreSQL can index with a GIN expression index if needed. In SQLite, tag filtering uses `json_extract(tags, '$.agent_id')`, which is slower but acceptable at Phase 2 scale.

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `record(name, value, tags?) -> Measurement` | Write one measurement. Thread-safe. |
| `record_many(measurements[]) -> int` | Batch write. Faster than calling `record` in a loop. |
| `query(Query) -> QueryResult[]` | Aggregate query. See §5.2. |
| `raw(name, since?, until?, tags?, limit?) -> Measurement[]` | Return raw measurements, newest first. No aggregation. |
| `prune(retain_days) -> int` | Delete measurements older than the retention window. Returns count removed. |
| `ingest_budget_meter(ledger_path, since?) -> int` | Source adapter: read a `budget-meter` ledger and write `token.*` and `token.cost` measurements. Returns count ingested. |
| `ingest_event_log(log_dir, since?) -> int` | Source adapter: fold a `event-log` directory and derive `task.*` measurements from session events. |
| `ingest_test_result(result_json_path) -> int` | Source adapter: read a `test-adapters` JSON result and write `test.*` measurements. |
| `backend() -> "file" \| "sqlite" \| "postgres"` | Return the active backend. |
| `migrate_to_relational(db_url) -> int` | One-time migration: read all JSONL segments and write to the relational backend. Returns count migrated. |

Also `metrics-store <op> --json`. The CLI maps directly to the `umas metrics *` commands.

## 5. Behaviour

### 5.1 Write path

Both backends append atomically. The file backend uses `O_APPEND` (same guarantees as `event-log` §5.1). The relational backend uses a single `INSERT`. Neither backend buffers writes — each `record()` call is immediately durable to the extent the storage layer guarantees it.

Multiple processes writing concurrently: the file backend uses the `O_APPEND` single-write guarantee (safe for lines ≤4096 bytes — all measurements qualify). The relational backend relies on the database's own concurrency control.

### 5.2 Query execution

**File backend:** load all retained segments, parse into memory, filter, group, aggregate. Returns results in under 1 second for ≤100k measurements. Above that threshold, `migrate_to_relational` should be called.

**Relational backend:** translate the `Query` into one SQL statement. Aggregation runs inside the database engine. `p50`/`p95`/`p99` use `PERCENTILE_CONT` in PostgreSQL; in SQLite (which lacks this function), the library fetches the sorted raw values and computes the percentile in application code — documented in the result as `approx: true`.

### 5.3 Source adapters

The three `ingest_*` operations are idempotent: each source record carries a deterministic `id` derived from its source identifier (ledger entry ULID, event-log event ID, test run timestamp + framework). Re-running an ingest skips already-present IDs. This means ingestion can run on a schedule (e.g., every 5 minutes) without duplicating data.

`ingest_budget_meter` maps ledger operations to metric names:
- `commit` operation → `token.input`, `token.output`, `token.cost` (one measurement each, tagged with `model` and `actor`)

`ingest_event_log` derives computed metrics:
- Pairs of `session_started` + `session_ended` → `task.duration_ms` (tagged with `agent_id`, `task_id`)
- `handoff_initiated` events → increments `task.handoff_rate` denominator
- `session_escalated` events → `error.p1_count` or `error.p0_count` by severity

`ingest_test_result` maps `TestResult` fields:
- `coverage.line_percent` → `test.coverage_pct`
- `duration_ms` → `test.duration_ms`
(tagged with `framework`, `project`)

### 5.4 Retention

`prune(retain_days)` deletes measurements with `ts < now() - retain_days`. Default: 90 days, matching the PRD's audit retention requirement. For the file backend, a segment is only pruned when every measurement in it is outside the window (same rule as `event-log` §5.3). Pruning never removes data that is still within the window.

### 5.5 Migration

`migrate_to_relational(db_url)` is a one-time operation:
1. Read all JSONL segments in chronological order.
2. Insert into the relational backend in batches of 1000.
3. On completion, write a `.migrated` marker file in the ledger dir so subsequent `record()` calls go to the relational backend.
4. The JSONL segments are not deleted — they remain as a backup until `prune()` removes them by age.

The migration is resumable: already-present IDs are skipped (see §5.3).

## 6. Configuration

```yaml
backend: file             # file | sqlite | postgres

# File backend
ledger_dir: .metrics
rotate_bytes: 67108864    # 64 MiB

# Relational backend (sqlite or postgres)
db_url: ""                # "sqlite:///path/to/metrics.db" or "postgresql://..."
# For PostgreSQL, tags column is JSONB; for SQLite it is TEXT (JSON)

# Shared
retain_days: 90
prune_on_startup: false   # run prune() automatically when the library initialises

# Ingest schedule (optional — the caller drives ingestion if not set)
ingest:
  budget_meter_ledger: ""      # path to budget-meter ledger dir; empty = disabled
  event_log_dir: ""            # path to event-log dir; empty = disabled
  interval_seconds: 300        # how often to run ingest_* when paths are configured
```

## 7. Failure Modes

| Error | Cause | Behaviour |
|-------|-------|-----------|
| `WriteError` | Disk full or permission denied on file backend | Fail the `record()` call; caller decides whether to drop or retry |
| `DBUnavailable` | PostgreSQL connection lost | Fail the call; caller retries. The library does not reconnect silently |
| `QueryTooLarge` | File backend query would load >500k measurements into memory | Return `QueryTooLarge` with a suggestion to migrate to relational |
| `PercentileApprox` | SQLite p50/p95/p99 computed in-memory | Not an error — flagged as `approx: true` in the result |
| `IngestConflict` | Source record ID already present (idempotent re-run) | Skip silently; count not included in the return value |
| `MigrationIncomplete` | Process killed mid-migration | Re-run `migrate_to_relational`; already-written rows are skipped |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below; severity is the consumer's policy.

| Error | Suggested recoverability |
|-------|--------------------------|
| `DBUnavailable` | `transient` |
| `WriteError`, `MigrationIncomplete` | `ambiguous` |
| `QueryTooLarge` | `permanent` until the backend is migrated |

`PercentileApprox` and `IngestConflict` are not errors.

## 8. Acceptance Criteria

1. `record()` from 10 concurrent processes writes no duplicate or interleaved lines in the file backend (same guarantee as `event-log`).
2. `query({ name: "token.used", aggregate: "sum", group_by: ["agent_id"] })` returns one row per distinct `agent_id` with the correct sum, on both backends.
3. `ingest_budget_meter` run twice on the same ledger inserts each measurement exactly once.
4. `migrate_to_relational` followed by a second run on the same ledger writes no duplicates.
5. `prune(90)` never removes a measurement with `ts` within the last 90 days; removes all measurements older than 90 days.
6. The file backend returns `QueryTooLarge` when asked to aggregate more than 500k raw rows; the relational backend handles the same query without error.
7. Switching `backend` from `file` to `postgres` in configuration (after migration) causes all subsequent `record()` calls to go to PostgreSQL; `raw()` and `query()` also read from PostgreSQL.

## 9. How UMAS Uses It

| UMAS concept | Mapping |
|---|---|
| `umas metrics tokens` | `query({ name: ["token.input","token.output"], aggregate: "sum", group_by: ["agent_id"], since: "7d" })` |
| `umas metrics cost` | `query({ name: "token.cost", aggregate: "sum", group_by: ["project","model"] })` |
| `umas metrics quality` | `query({ name: ["test.coverage_pct","merge_queue.success_rate","error.p1_count"], aggregate: "avg" })` |
| `umas metrics agents` | `query({ name: "task.duration_ms", aggregate: "p95", group_by: ["agent_id"] })` |
| Phase 1–2 (SQLite tier, ≤5 agents) | `backend: file` — zero extra infrastructure |
| Phase 3 (PostgreSQL tier, 20 agents) | `backend: postgres`, `db_url` points to the existing UMAS PostgreSQL instance. The `metrics` table lives in the same database as `projects`, `work_bundles`, `agent_sessions` |
| TimescaleDB | Not used. `SELECT create_hypertable('metrics', 'ts')` is available as a future operational upgrade if query latency becomes a measured problem; no application code change required |
| Metrics DB record in TECHNICAL-DESIGN-SUMMARY.md | `token_usage` and `cost_tracking` tables are replaced by `metrics` rows tagged with `agent_id` and `task_id` |
| 90-day retention (PRD) | `retain_days: 90` |

## 10. Source Material and Deviations

Extracted from `TECHNICAL-DESIGN-SPEC.md` §1.2 (`metrics_storage`), `TECHNICAL-DESIGN-SUMMARY.md` (database schema overview, `token_usage` and `cost_tracking` tables), PRD §Observability Requirements, and the design discussion that produced this spec.

| Deviation | Why |
|-----------|-----|
| TimescaleDB removed as a requirement | TimescaleDB is a PostgreSQL extension that adds automatic time-based partitioning. At UMAS scale (30 agents, 90-day retention) a standard `(name, ts)` index is sufficient. TimescaleDB is an operational upgrade path, not a design dependency. The spec's original rationale ("time-series database") does not withstand scrutiny: the queries are aggregations over a fixed schema, not streaming time-series analytics |
| Single `metrics` table replaces `token_usage` + `cost_tracking` | The original schema had two separate tables. One narrow table with a `name` column and a `tags` JSON column covers both, and every future metric category, without schema changes |
| `tags` as JSON column, not separate tag table | A normalised tags table would require joins on every query. At this measurement volume, a JSON column with expression indexes (PostgreSQL) or `json_extract` (SQLite) is simpler and fast enough |
| File ledger as Phase 1–2 backend | The original spec required TimescaleDB from day one. A file ledger defers all infrastructure until Phase 3 without losing any data |
| Source adapters (ingest_*) instead of direct instrumentation | The other libs (`budget-meter`, `event-log`) already write their own ledgers. Having them also write to a metrics store would couple them to this library, violating the no-cross-library-imports rule. Adapters read existing ledgers on a schedule |

## 11. Open Questions

1. **Ingest scheduling:** Should `metrics-store` run its own background ingest loop when `ingest.interval_seconds` is set, or should UMAS drive ingest explicitly (e.g., after every task completion)? A background loop is simpler to configure but requires a long-lived process.
2. **PostgreSQL dialect for percentiles:** SQLite approximates p50/p95/p99 by loading sorted values into memory. Is the `approx: true` flag sufficient for the dashboard, or do percentile queries require PostgreSQL?
3. **Tag index strategy:** For the PostgreSQL backend, should the library automatically create a GIN index on the `tags` JSONB column, or leave index strategy to the operator? Auto-creation simplifies setup but adds index maintenance overhead.
4. **Metrics table location:** Should the `metrics` table live in the same database as `projects`/`work_bundles`/`agent_sessions`, or in a separate database? Co-location is simpler; separation allows independent scaling and backup policies.
