# token-ledger

> Standalone library spec · Draft v0.2 · Part of [libs/README.md](../README.md)
> **Independence:** no dependency on UMAS or on any LLM SDK. A file-based, append-only usage log.
> **History:** renamed and reduced in v0.2 ([ADR-0005](../../docs/decisions/ADR-0005-track-token-usage-only.md)). Context packing moved to [agent-session](../agent-session/README.md).

---

## 1. Purpose

Record how many tokens each LLM call used, with the model and the time, and answer totals by model and time window. Nothing else.

## 2. Scope and Non-Goals

**In scope**
- Append one usage entry per LLM call
- Totals and raw entries, filtered by time window and model
- Tolerance of corrupt lines

**Non-goals**
- Any decision to start, defer or stop work. The library records; it never acts.
- Input/output split, cached tokens, actor, project, or task attribution. The entry holds one number.
- Counting tokens for text. The caller passes the count the provider reports.
- Retention, rotation and pruning. The file is kept forever and the library never rewrites it (no rotation in v0.2). [metrics-store](../metrics-store/README.md) prune covers derived rows only, so the metrics view keeps 90 days by default while `totals` here covers all time.

## 3. Concepts and Data Model

### 3.1 Entry

One line per LLM call, JSON, UTF-8:

```json
{ "v": 1, "ts": "2026-11-09T07:00:00Z", "model": "opus", "tokens": 4120 }
```

| Field | Type | Rule |
|-------|------|------|
| `v` | int | Format version. `1` |
| `ts` | string | RFC 3339 UTC, set by the library at `record` unless the caller supplies one |
| `model` | string | Non-empty. The LLM model name that answered the call, for example `opus` or `sol`. Never an llm-gateway alias (`default`, `deep`). On failover it is the model that answered that attempt. The library does not interpret it |
| `tokens` | int | Integer ≥ 0. `input + output` as the provider reports them; cached tokens are excluded. A zero value is not written (see section 4) |

### 3.2 File

```
<ledger_path>        # absolute, e.g. /var/lib/app/token-ledger/usage.jsonl
```

Append-only. Each line is at most 4096 bytes, so a single `O_APPEND` write is atomic across processes on POSIX and is written as one write call on Windows (see section 5.2).

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `record(model, tokens, ts?) -> Entry?` | Validate and append one entry. Returns the entry as written. If `tokens` is `0`, nothing is written and it returns nothing: a harness that reports zero produces no line |
| `totals(since?, until?, group_by?) -> Total[]` | Sum `tokens` and count calls. `group_by` is `model` or omitted (one row for all). `since` and `until` are RFC 3339; default is all time |
| `raw(since?, until?, model?) -> Entry[]` | Entries in file order, optionally filtered. No aggregation |
| `check() -> Report` | Count valid, skipped and corrupt lines. Read-only |

`Total = { model?, tokens, calls, since, until }`. Fields not grouped are omitted.

`Report = { valid, unsupported_version, corrupt, partial_tail }`. `valid`, `unsupported_version` and `corrupt` are counts of lines; `corrupt` includes a partial last line. `partial_tail` is `true` when the last line is incomplete. `check()` reports and does not repair.

Also `token-ledger <op> --json`.

### 4.1 CLI output (AXI)

Follows [CLI Conventions (AXI)](../README.md#cli-conventions-axi).

No-argument view = `totals` grouped by model, all time:

```
bin: token-ledger
description: LLM token usage by model
totals[2]{model,tokens,calls}:
  opus,812400,96
  sol,40200,7
help[1]:
  token-ledger totals --since 2026-11-01 --group-by model
```

- Empty ledger: `totals: none recorded` and exit 0.
- `record` prints `result: recorded` with `ts` and `tokens`, or `result: skipped (zero tokens)` when `tokens` is `0`.
- Exit codes: `0` success or empty; `1` a typed error (`ConfigError`, `InvalidEntry`, `LedgerUnreadable`, `LedgerWriteFailed`, `LockTimeout`); `2` usage.

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

Any non-empty model name is recorded and totalled like any other. The library keeps no list of known models.

## 6. Configuration

```yaml
ledger_path: /var/lib/app/token-ledger/usage.jsonl   # absolute, no default
```

`ledger_path` must be absolute. The consumer resolves it once at start-up and passes the same value to every writer and reader, so processes with different working directories use one file. A missing or relative path fails `ConfigError`. No other settings.

## 7. Failure Modes

| Error | Cause | Behaviour |
|-------|-------|-----------|
| `ConfigError` | `ledger_path` missing or not absolute | Fail before any read or write |
| `InvalidEntry` | Empty `model`, negative or non-integer `tokens`, bad `ts` | Fail. Nothing is written |
| `UnsupportedVersion` | Line with `v` the reader does not know | Skip the line; `check()` counts it |
| `LedgerCorrupt` | Unparseable line | Skip the line, count it in `check()`, continue |
| `LedgerUnreadable` | File cannot be opened or read | Fail with the OS error |
| `LedgerWriteFailed` | The append failed: disk full, or permission denied | Fail with the OS error. The caller logs it and does not retry in a loop |
| `LockTimeout` | Windows sidecar lock held too long | Fail, retryable |

**Partial lines.** A failed or interrupted append (for example, disk full mid-write) can leave an incomplete last line. Readers skip it. `check()` reports it as `partial_tail: true` and counts it in `corrupt`. The next `record` starts a new line: if the file does not end in a newline, the library writes one first.

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below.

| Error | Suggested recoverability |
|-------|--------------------------|
| `LockTimeout` | `transient` |
| `LedgerWriteFailed` | `transient` for disk full; `permanent` for permission denied |
| `LedgerCorrupt`, `UnsupportedVersion` | `ambiguous` (the library continues) |
| `ConfigError`, `InvalidEntry`, `LedgerUnreadable` | `permanent` until the input, config or file is fixed |

## 8. Acceptance Criteria

1. 10 processes each appending 1000 entries concurrently produce 10,000 valid lines with no interleaving (POSIX, verified on macOS).
2. `totals` grouped by model equals the sum of the `tokens` values in `raw` for each model.
3. `record` with an empty `model`, a negative `tokens`, or a non-integer `tokens` fails `InvalidEntry` and the file size does not change.
4. A corrupt line in the middle of the file is skipped and counted by `check()`; every other line is still totalled.
5. `record` of a model name with no prior entries succeeds.
6. `token-ledger` with no arguments prints the totals view and exits 0, with `totals: none recorded` on an empty file.
7. Windows behaviour in section 5.2 is verified by reading only.
8. `record` on a read-only file or a full disk fails `LedgerWriteFailed`, and `check()` afterwards reports any partial last line as `partial_tail: true`. The next successful `record` leaves every earlier line valid.
9. `record` with `tokens` of `0` writes nothing and the file size does not change.
10. A relative `ledger_path` fails `ConfigError`.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.

| UMAS concept | Mapping |
|--------------|---------|
| Usage recording for every LLM call | The llm-gateway usage callback calls `record(model, tokens)` for every attempt that reports usage, failed attempts included, with `model` the payload's model name (not the alias). Attempts with no usage report produce no entry |
| `umas metrics tokens` | `metrics-store` `query` on `token.used` rows tagged with `model` (see [metrics-store](../metrics-store/README.md) §3.2 and §5.3). `totals` here is this library's own CLI and is not the data path of that command |
| Session context limit | Not a ledger concern. [agent-session](../agent-session/README.md) counts the context window, not the ledger |

## 10. Source Material and Deviations

Reduced in v0.2 by owner decision 2026-11-09 ([ADR-0005](../../docs/decisions/ADR-0005-track-token-usage-only.md)): track tokens, model and time only.

| Deviation | Why |
|-----------|-----|
| `pack()` moved to [agent-session](../agent-session/README.md) | Its only caller is the session handoff; the ledger has no reason to pack |
| Input/output split removed | The owner asked for the amount of tokens; one total is the amount |

## 11. Open Questions

None.
