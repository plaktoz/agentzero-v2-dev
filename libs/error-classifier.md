# error-classifier

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](README.md)
> **Independence:** no dependency on UMAS. Pure data and deterministic functions; no AI, no database, no network.

---

## 1. Purpose

Give every error in a system one shape and one vocabulary. The library turns a raw failure (an exception, an HTTP status, a process exit, a message) into a structured **error record** with a stable code, a severity, and a recoverability class. It then renders that record for an agent or for a person, advises whether a retry is worth trying, and counts repeats so a caller can alert on patterns.

It is the shared *format* that other components agree on. It is not a shared import: each component keeps its own typed errors, and the consuming application maps them to records.

## 2. Scope and Non-Goals

**In scope**
- The error record schema and its validation
- A catalog of known error codes (data files)
- Deterministic classification rules: raw input -> code, severity, recoverability
- Retry advice from recoverability (the library never sleeps or retries by itself)
- Rendering for agents (compact, structured) and for people (plain language, next steps)
- Redaction of secrets before a record is stored or shown
- Fingerprinting, repeat counting, pattern alerts, and digests

**Non-goals**
- Delivering alerts (chat, email, pager). Alerts are events through a callback.
- Performing recovery. The record lists recovery actions; the caller runs them.
- Using a model to classify. Rules are deterministic so the same input gives the same record.
- Logging, tracing, or metrics backends
- Error-resolution history and knowledge sharing across a team (a consumer concern)

## 3. Concepts and Data Model

### 3.1 Severity

Severity says **who must act and how fast**. Names are labels; the responder for each is configuration.

| Level | Meaning | Default responder label |
|-------|---------|-------------------------|
| `P0` | The system cannot function. A person must act now | `operator` |
| `P1` | One unit of work cannot proceed without a supervisor's decision | `supervisor` |
| `P2` | The work can retry or work around it. A monitor watches | `monitor` |
| `P3` | Informational. Logged for analysis | `log` |

### 3.2 Recoverability

| Class | Meaning | Examples | Retry advice |
|-------|---------|----------|--------------|
| `transient` | Retrying is likely to succeed | Network timeout, rate limit, brief file lock | Retry with backoff, bounded |
| `permanent` | Retrying will not help | Invalid credentials, missing file, merge conflict | Stop; hand to the responder |
| `ambiguous` | Unknown whether a retry helps | Unrecognised error, odd behaviour | Stop and investigate |

### 3.3 Error record

```json
{ "schema_version": 1,
  "id": "01J...",
  "code": "MERGE_CONFLICT",
  "severity": "P1",
  "recoverability": "permanent",
  "message": "Merge conflict in src/auth.py. Manual resolution required.",
  "context": { "operation": "merge", "timestamp": "2026-10-20T06:45:00Z",
               "correlation_id": "t-91", "actor": "worker-a", "task": "auth-feature" },
  "cause": { "type": "MergeConflict", "message": "lines 42-58", "stack": null },
  "recovery": { "automatic": ["Escalated to supervisor"],
                "manual": ["Review the conflicting changes", "Resolve and resume"],
                "expected_resolution_seconds": 300 },
  "docs": "errors/merge-conflict",
  "related": [ { "id": "01J...", "relation": "caused_by" } ],
  "fingerprint": "MERGE_CONFLICT|merge",
  "catalog_version": "3",
  "matched_rule": "r-git-conflict" }
```

Required: `schema_version`, `id`, `code`, `severity`, `recoverability`, `message`, `context.operation`, `context.timestamp`. `context` is an open map: the library defines only `operation`, `timestamp`, and `correlation_id`; every other key is the caller's. `cause` may carry extra keys (for example `files`). `related.relation` is `caused_by` or `similar`.

### 3.4 Raw input

```
raw = { kind: "exception"|"http"|"process"|"message",
        type?, message?, status?, exit_code?, tags[]?,
        stack?, cause?: raw }
```

### 3.5 Catalog entry

```yaml
- code: MERGE_CONFLICT                # UPPER_SNAKE, unique, never reused or renamed
  severity: P1
  recoverability: permanent
  message: "Merge conflict in {path}. Manual resolution required."
  causes: ["Two changes edited the same lines", "A stale branch was merged"]
  recovery:
    automatic: ["Escalated to supervisor"]
    manual: ["Review the conflicting changes", "Resolve and resume"]
    expected_resolution_seconds: 300
  retry: null                         # transient entries set a retry policy (5.3)
  human:
    what: "Your change cannot be merged because another change edited the same code."
    impact: "This task is paused. Other tasks continue. No work is lost."
    steps: ["Review the conflict: {diff_command}", "Resolve it", "Resume: {resume_command}"]
  prevention: ["Keep branches short-lived"]
  related: [MERGE_BLOCKED]
  docs: "errors/merge-conflict"
```

`{name}` placeholders are filled from `context` and `cause`. A missing value renders as `?` and never raises.

### 3.6 Classification rule

```yaml
- id: r-disk-critical
  priority: 100                       # higher wins; ties resolve by file order
  match:                              # all keys must match; a list means any of
    tags: [disk]
    context: { free_mb: { lt: 100 } } # operators: eq lt lte gt gte
  code: DISK_CRITICAL
  severity: P0                        # optional override of the catalog value
  recoverability: permanent           # optional override
```

Match keys: `kind`, `type` (exact or glob), `status`, `exit_code`, `message_regex`, `tags`, `context.<key>`.

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `load_catalog(paths) -> Catalog` | Load and lint entries and rules. Fails on duplicate codes, unknown `related`, or rules that name a missing code |
| `classify(raw, context, opts) -> Record` | Redact, match rules, build the record. Never throws on bad input; falls back to the default (5.1) |
| `validate(record) -> Result` | Check a record against the schema. Also accepts the previous `schema_version` |
| `retry_plan(record, attempts_made) -> Plan` | `{ action: retry\|stop\|investigate, delay_seconds, attempts_left, reason }` |
| `render(record, audience) -> text` | `audience` is `agent`, `human`, or `json` |
| `observe(record) -> Observation` | Count the record. Returns `{ similar: { count, first_seen, last_seen, ids[] }, alerts[] }` |
| `digest(since, severities) -> Digest` | Grouped counts by fingerprint, severity, and recoverability |
| `summary(window) -> Summary` | Counts by severity and by recoverability |
| `subscribe(callback)` | Receive `alert` events in-process |

CLI: `error-classifier classify --json` (raw on stdin), `render --audience human`, `retry-plan`, `observe`, `digest`, `catalog lint`, `catalog show <CODE>`. The CLI is part of the contract.

## 5. Behaviour

### 5.1 Classification

1. Redact `message`, `cause`, `stack`, and `context` values (5.6).
2. Evaluate rules by descending priority, then file order. The first match wins.
3. Take the catalog entry for the rule's `code`. Apply the rule's `severity` and `recoverability` overrides.
4. Fill the record: message template, recovery lists, `docs`, `related`, `catalog_version`, `matched_rule`, `fingerprint`.
5. If no rule matches, use the configured default: code `UNCLASSIFIED`, severity `P2`, recoverability `ambiguous`, with the raw message kept in `cause`.

The same raw input and catalog always produce the same record (apart from `id` and `timestamp`).

### 5.2 Linking

A caller may pass `parent` (a record id). The new record gets `related: [{id: parent, relation: "caused_by"}]`, so a cascade can be followed. `observe` adds `similar` links to earlier records with the same fingerprint.

### 5.3 Retry advice

`retry_plan` is pure arithmetic over the entry's `retry` policy:

```yaml
retry:
  max_attempts: 3
  base_seconds: 5
  factor: 3          # delays 5, 15, 45
  max_seconds: 300
  honour: retry_after   # use the cause's retry-after value when present
```

| Recoverability | Result |
|----------------|--------|
| `transient` | `retry` with the next delay while `attempts_made < max_attempts`; then `stop` with reason `retries_exhausted` |
| `permanent` | `stop`, reason `permanent` |
| `ambiguous` | `investigate`, reason `ambiguous` |

A transient entry with no `retry` block uses the configured default policy. `base_seconds: 0` gives immediate retries. When retries are exhausted the record's severity is **not** raised; the caller routes it as it stands.

### 5.4 Rendering

- **agent**: compact and structured. Header `Error: <code> (<severity>, <recoverability>)`, then context, operation, state keys, recovery actions marked `[AUTOMATIC]` or `[MANUAL]`, whether a retry is appropriate, related records, and the expected resolution time.
- **human**: plain language with no jargon beyond what the entry needs: what happened (`human.what`), impact (`human.impact`), what was being attempted (`context.operation`), whether work is blocked, numbered steps with exact commands, an estimate, and a docs pointer.
- **json**: the record as stored.

Stack traces appear only when `include_stack` is true.

### 5.5 Aggregation and alerts

- `fingerprint = code + "|" + values of fingerprint_keys` (default `operation`).
- Counts are kept per fingerprint inside sliding windows.
- Alert rules, all configurable:

| Trigger | Default | Alert event |
|---------|---------|-------------|
| Any `P0` | every occurrence | `alert{kind: "immediate"}` |
| `P1` count for one fingerprint | more than 3 in 10 minutes | `alert{kind: "pattern"}`, once per crossing, re-armed when the count drops |
| `P2` and `P3` | daily | Included in `digest`, which the caller schedules |

- With `ledger_path` set, `observe` appends each record to a JSONL file, so counts survive restarts and are shared by processes. Without it, state is in memory. The ledger is rebuildable input, not a database; writers use an advisory lock.

### 5.6 Redaction

Patterns in `redact.patterns` are replaced with `[REDACTED]` in every string field before the record is created. Defaults cover `Authorization` header values, `api_key`/`token`/`secret`/`password` assignments, and long base64-like tokens. Redaction runs before rule matching on the copy used for output, but rules match against the **original** text so a classification never depends on what was hidden. The original is not stored.

## 6. Configuration

```yaml
catalog_paths: [errors/catalog.yaml, errors/rules.yaml]
default:
  code: UNCLASSIFIED
  severity: P2
  recoverability: ambiguous
responders: { P0: operator, P1: supervisor, P2: monitor, P3: log }
retry_default: { max_attempts: 3, base_seconds: 5, factor: 3, max_seconds: 300 }
include_stack: false
fingerprint_keys: [operation]
alerts:
  immediate: [P0]
  pattern: { severity: P1, count: 3, window_seconds: 600 }
digest: { severities: [P2, P3], period: daily }
ledger_path: null
redact: { patterns: [default], extra: [] }
```

The library ships **no catalog**. A starter catalog is an example, not part of the contract.

## 7. Failure Modes

| Failure | Handling |
|---------|----------|
| No rule matches | Default record (`UNCLASSIFIED`); the raw message is kept so a rule can be added. Fixture F6 |
| Two rules match | Priority, then file order; `catalog lint` warns on overlaps with equal priority |
| Rule names a missing code | `load_catalog` fails; nothing is half-loaded |
| Unknown severity or recoverability in a file | Load fails with the offending line |
| Template placeholder missing | Rendered as `?`; never an exception. Fixture F8 |
| Secret in a message | Redacted before output. Fixture F7 |
| Ledger corrupt or locked | Counts fall back to memory; a warning is emitted; classification is unaffected |
| Alert storm from one cause | Pattern alerts fire once per crossing, not per record |
| Catalog changes severity for a code | Records carry `catalog_version`, so old and new records stay distinguishable |
| Clock skew between processes | Windows use the record `timestamp`, not the observer's clock |

## 8. Acceptance Criteria

Fixtures F1 to F10 ship with the library as input and expected-output files.

| ID | Input | Expected |
|----|-------|----------|
| F1 | HTTP 429 with `Retry-After: 20` | `transient`, plan `retry` after 20s |
| F2 | HTTP 401 | `permanent`, severity per rule, plan `stop` |
| F3 | Merge conflict exception | `permanent`, human view lists steps with commands filled in |
| F4 | `free_mb` of 1500, 400, 80 | `P2`, `P1`, `P0` respectively |
| F5 | Four `P1` records, one fingerprint, within 10 minutes | One `pattern` alert on the fourth |
| F6 | Unrecognised exception | `UNCLASSIFIED`, `P2`, `ambiguous`, plan `investigate` |
| F7 | Message containing `api_key=abc123` | Output has `[REDACTED]`; the rule that matched on the original still applies |
| F8 | Template placeholder with no context value | `?` in the output |
| F9 | Same raw input twice | Identical records apart from `id` |
| F10 | Record with `schema_version` N-1 | Validates and renders |

1. F1 to F10 produce the expected records, plans, and alerts.
2. Every record validates against the schema; `classify` never returns an invalid record, even for empty or malformed raw input.
3. `retry_plan` for a `permanent` record is never `retry`, for any attempt count.
4. For a transient entry with `max_attempts: 3`, attempts 0, 1, 2 give `retry` and attempt 3 gives `stop` with `retries_exhausted`.
5. A `P0` record raises an `immediate` alert on every occurrence.
6. A pattern alert fires once per crossing and again only after the count has dropped below the threshold.
7. `render(agent)` and `render(human)` for the same record contain the code, the operation, and at least one recovery step.
8. No stack trace appears in any rendering when `include_stack` is false.
9. `catalog lint` rejects duplicate codes, dangling `related` entries, and rules for unknown codes.
10. The library works with an empty catalog, producing `UNCLASSIFIED` records.
11. Two processes writing one ledger produce the same counts as one process (no lost lines).

## 9. How UMAS Uses It

| UMAS concept | Mapping |
|--------------|---------|
| Error severity P0 to P3 | `severity`; responders set to `human`, `coordinator`, `system patrol`, `log` |
| Transient, permanent, ambiguous | `recoverability` |
| Required error fields (`code`, `severity`, `recoverability`, `message`, `context`, `cause`, `recovery`, `documentation`) | The record. `context.agent_id`, `session_id`, `task_id` are caller keys |
| `escalate` events with a severity in `.umas/events.jsonl` | The record's `severity` is written as the event's severity; the record can be the event's payload |
| Provider failure policy (`UMAS-TECH-DESIGN-SPEC.md` §4.7) | Catalog entries and `retry` blocks: 429 as `retry` 5/15/45, 5xx three immediate retries, timeout two retries, 401/403 `stop` at `P0` |
| Disk-space thresholds (<2 GB P2, <500 MB P1, <100 MB P0) | Three rules on `context.free_mb` (F4) |
| Alert on P0 now, P1 pattern (>3 in 10 minutes), daily P2/P3 digest | Section 5.5 defaults |
| Error catalog and troubleshooting guides | The catalog, `docs`, `causes`, `prevention` |
| Agent-facing and human-facing error messages | `render(agent)` and `render(human)` |
| Typed errors inside the other libraries | Mapped to records by UMAS; the libraries do not import this one. Each library's failure-modes section has a suggested `recoverability` per error (the "Error records" table, or the 3.3 note in llm-gateway). Severity is UMAS policy and is set in its catalog, not by the library |

## 10. Source Material and Deviations

Extracted from the PRD "Error Handling and Recovery Requirements" (classification, message structure, agent-facing and human-facing handling, recovery strategies, logging, metrics, documentation), PRD section 6.4 (escalation channels), `UMAS-TECH-DESIGN-SPEC.md` §4.7 and the disk-space thresholds, `TECHNICAL-DESIGN-SUMMARY.md` Module 8, and the error table in [llm-gateway](llm-gateway.md) (section 3.3).

| Deviation | Why |
|-----------|-----|
| Deterministic rules classify errors | The PRD requires every error to be classified but never says how. Rules keep it testable and repeatable |
| Shared record format, not a shared import | The gap list says every lib and agent needs one taxonomy. The libs may not import each other, so the contract is the record schema and each consumer maps its own errors |
| `context` is an open map | The PRD fixes `agent_id`, `session_id`, `task_id`. Those are UMAS vocabulary and become caller keys |
| P3 has no responder other than the log | PRD section 6.4 routes only P0 to P2; P3 is "informational, logged" |
| PRD "recoverable failures" (test failures, linter errors) have no enum value | They fit `transient` with a non-retry action in `recovery.automatic`. A fourth class was not added without a decision (Open Question 3) |
| Default retry 5, 15, 45 seconds, 3 attempts | The PRD says "3 attempts, exponential" with no delays. The values match the gateway spec |
| Default for unmatched errors is `P2` `ambiguous` | Not in the source; chosen so an unknown error neither pages a person nor passes silently |
| Stack trace off by default | The PRD says stack traces are for development environments only |
| Redaction added | Not in the source. Error messages routinely contain credentials and records are stored and shown |
| Targets and metrics dropped (`p1_count < 5 per day`, `automatic_success_rate > 90%`) | They are goals for an operator, not behaviour of the library. `summary` supplies the inputs |
| Error history and cross-team learning dropped | Needs storage and process the library does not own |
| Alert delivery (chat, notifications) dropped | Left to the callback |
| Error codes in the PRD used as examples only | `MERGE_QUEUE_CONFLICT`, `AGENT_TOKEN_EXHAUSTED`, and the others describe UMAS components, so the catalog is data supplied by the consumer |

## 11. Open Questions

1. Should an unmatched error default to `P2` or `P1`? `P2` avoids noise; `P1` avoids hiding a new failure.
2. Is the P1 pattern rule per fingerprint, or across all P1 records? The PRD says "P1 error patterns (>3 in 10 minutes)" without saying which. This spec uses per fingerprint.
3. Should `recoverability` get a fourth value (`recoverable`: fixed by an automatic action other than a plain retry)? The PRD's own recovery list uses that group.
4. Should an `ambiguous` error that repeats be raised one severity level automatically? Currently it is only counted and alerted.
5. Should the starter catalog be published as a separate data package so consumers share common codes (rate limit, timeout, auth)?
