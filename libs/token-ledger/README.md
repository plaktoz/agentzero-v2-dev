# token-ledger

> Standalone library spec · Draft v0.2 · Part of [libs/README.md](../README.md)
> **Independence:** no dependency on UMAS or on any LLM SDK. A file-based, append-only usage log.
> **Replaces:** `budget-meter`. Budgets, reservations, thresholds, prices and admission control were removed by [ADR-0005](../../docs/decisions/ADR-0005-track-token-usage-only.md). Context packing moved to [agent-session](../agent-session/README.md).

---

## 1. Purpose

Record how many tokens each LLM call used, with the model and the time, and answer totals by model and time window. Nothing else.

## 2. Scope and Non-Goals

**In scope**
- Append one usage entry per LLM call
- Totals and raw entries, filtered by time window and model
- Tolerance of corrupt lines

**Non-goals**
- Budgets, limits, reservations, admission, or any decision to start, defer or pause work. The library records; it never acts.
- Cost, prices, or currency. Nothing here knows a rate.
- Input/output split, cached tokens, actor, project, or task attribution. The entry holds one number.
- Counting tokens for text. The caller passes the count the provider reports.
- Retention and pruning. The file is never rewritten by the library. [metrics-store](../metrics-store/README.md) owns retention of derived measurements.

## 3. Concepts and Data Model

### 3.1 Entry

One line per LLM call, JSON, UTF-8:

```json
{ "v": 1, "ts": "2026-11-09T07:00:00Z", "model": "default", "tokens": 4120 }
```

| Field | Type | Rule |
|-------|------|------|
| `v` | int | Format version. `1` |
| `ts` | string | RFC 3339 UTC, set by the library at `record` unless the caller supplies one |
| `model` | string | Non-empty. The llm-gateway alias, or the model name the provider reports. Never a vendor-specific name the library interprets |
| `tokens` | int | Integer ≥ 0. The total the provider reports for the call |

### 3.2 File

```
<ledger_path>        # e.g. .token-ledger/usage.jsonl
```

Append-only. Each line is at most 4096 bytes, so a single `O_APPEND` write is atomic across processes on POSIX and is written as one write call on Windows (see section 5.2).

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `record(model, tokens, ts?) -> Entry` | Validate and append one entry. Returns the entry as written |
| `totals(since?, until?, group_by?) -> Total[]` | Sum `tokens` and count calls. `group_by` is `model` or omitted (one row for all). `since` and `until` are RFC 3339; default is all time |
| `raw(since?, until?, model?) -> Entry[]` | Entries in file order, optionally filtered. No aggregation |
| `check() -> Report` | Count valid, skipped and corrupt lines. Read-only |

`Total = { model?, tokens, calls, since, until }`. Fields not grouped are omitted.

Also `token-ledger <op> --json`.

### 4.1 CLI output (AXI)

Follows [CLI Conventions (AXI)](../README.md#cli-conventions-axi).

No-argument view = `totals` grouped by model, all time:

```
bin: token-ledger
description: LLM token usage by model
totals[2]{model,tokens,calls}:
  default,812400,96
  planner,40200,7
help[1]:
  token-ledger totals --since 2026-11-01 --group-by model
```

- Empty ledger: `totals: none recorded` and exit 0.
- `record` prints `result: recorded` with `ts` and `tokens`.
- Exit codes: `0` success or empty; `1` a typed error (`InvalidEntry`, `UnsupportedVersion`, unreadable file); `2` usage.

**Idempotence.** `record` is not idempotent: each call appends. The caller that retries an LLM call must not record it twice. The library offers no dedupe key, because the caller already knows whether a call completed.

## 5. Behaviour

### 5.1 Totals

`totals` folds the file in order. It skips corrupt lines (section 7). Rows are sorted by `model` ascending when grouped.

### 5.2 Concurrency

- POSIX: `O_APPEND`, one `write` per line. No lock is needed.
- Windows: the library opens the file in append mode and writes the line in one call, and takes an advisory lock on a sidecar `<ledger_path>.lock` for the duration of the write. Verified by reading only (no Windows machine in the repo).
- Readers never lock. A line being written may be read as partial; a partial last line is skipped.

### 5.3 Versions

Readers accept `v` 1. A line with an unknown `v` is skipped with `UnsupportedVersion` in `check()`. When a later version adds fields, readers of N and N-1 both work (libs/README rule 5).

### 5.4 Unknown models

A model with no entry in any table is recorded and totalled like any other. The library has no price table, so there is nothing to miss.

## 6. Configuration

```yaml
ledger_path: .token-ledger/usage.jsonl
```

No other settings.

## 7. Failure Modes

| Error | Cause | Behaviour |
|-------|-------|-----------|
| `InvalidEntry` | Empty `model`, negative or non-integer `tokens`, bad `ts` | Fail. Nothing is written |
| `UnsupportedVersion` | Line with `v` the reader does not know | Skip the line; `check()` counts it |
| `LedgerCorrupt` | Unparseable line | Skip the line, count it in `check()`, continue |
| `LedgerUnreadable` | File cannot be opened or read | Fail with the OS error |
| `LockTimeout` | Windows sidecar lock held too long | Fail, retryable |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below.

| Error | Suggested recoverability |
|-------|--------------------------|
| `LockTimeout` | `transient` |
| `LedgerCorrupt`, `UnsupportedVersion` | `ambiguous` (the library continues) |
| `InvalidEntry`, `LedgerUnreadable` | `permanent` until the input or file is fixed |

## 8. Acceptance Criteria

1. 10 processes each appending 1000 entries concurrently produce 10,000 valid lines with no interleaving (POSIX, verified on macOS).
2. `totals` grouped by model equals the sum of the `tokens` values in `raw` for each model.
3. `record` with an empty `model`, a negative `tokens`, or a non-integer `tokens` fails `InvalidEntry` and the file size does not change.
4. A corrupt line in the middle of the file is skipped and counted by `check()`; every other line is still totalled.
5. `record` of a model name with no prior entries succeeds.
6. `token-ledger` with no arguments prints the totals view and exits 0, with `totals: none recorded` on an empty file.
7. Windows behaviour in section 5.2 is verified by reading only.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.

| UMAS concept | Mapping |
|--------------|---------|
| Usage recording for every LLM call | The llm-gateway usage callback calls `record(model, tokens)` after each successful call. Calls with no usage report produce no entry |
| `umas metrics tokens` | `totals(group_by=model)` on the ledger, or `metrics-store` rows `token.used` tagged with `model` (see [metrics-store](../metrics-store/README.md) §3.2 and §5.3) |
| Session context limit | Not a ledger concern. [agent-session](../agent-session/README.md) counts the context window, not the ledger |

## 10. Source Material and Deviations

Source: `libs/budget-meter` v0.1, sections 3.2 (ledger) and 4 (`commit`/`record`). Replaced in v0.2.

| Deviation | Why |
|-----------|-----|
| Budgets, reservations, thresholds, windows, admission removed | Owner decision 2026-11-09 (ADR-0005): track token use only; no budget pause |
| Cost and price table removed | Owner decision 2026-11-09: track tokens, model and time only |
| `pack()` moved to [agent-session](../agent-session/README.md) | Its only caller is the session handoff; the ledger has no reason to pack |
| Input/output split removed | The owner asked for the amount of tokens; one total is the amount |
| Legacy Rust `Scheduler` token budget dropped | It enforced a daily limit, which is removed. The Rust reference in v0.1 is not ported |

## 11. Open Questions

None.
