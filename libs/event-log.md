# event-log

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](README.md)
> **Independence:** no dependency on UMAS. Needs only a filesystem with `O_APPEND` semantics.

---

## 1. Purpose

An append-only, line-delimited JSON log that several local processes can write to and read from safely. It is used as an audit trail, as a replayable history, and as a lightweight signalling channel in which a poller picks up new events by cursor.

## 2. Scope and Non-Goals

**In scope**
- Atomic appends from multiple processes
- Filtered reading, tailing, and cursor-based polling
- Rotation, retention, corruption recovery
- Replay through a caller-supplied reducer
- Optional redaction

**Non-goals**
- Delivery guarantees across machines, queues, or pub/sub fan-out
- Interpreting event types. The library never knows what `escalate` or `decision_made` means.
- Indexing or full-text search
- Session or summary building. That is a reducer a consumer writes (the library offers `fold`).

## 3. Concepts and Data Model

### 3.1 Envelope

One JSON object per line, UTF-8, `\n` terminated, no embedded newlines.

```json
{ "v": 1, "id": "01JC...", "ts": "2026-10-19T10:23:01.123Z",
  "type": "step_complete", "source": "alice", "scope": "auth-login/",
  "data": { "summary": "validation logic done" } }
```

| Field | Required | Notes |
|-------|----------|-------|
| `v` | yes | Envelope schema version |
| `id` | yes | ULID. Sorts by time and is unique across writers |
| `ts` | yes | RFC 3339 UTC, millisecond precision. Set by the library, not the caller |
| `type` | yes | Caller-defined string, `[a-z0-9_.-]+` |
| `source` | yes | Who wrote it (agent name, process) |
| `scope` | no | Free grouping key (a hook, a session, a project). Used for filtered reads |
| `trace` | no | Correlation ID for tracing |
| `data` | yes | Object, may be empty. Schema is the consumer's concern |

Maximum line size is `max_line_bytes` (default 64 KiB). Larger payloads must be stored elsewhere and referenced from `data`.

### 3.2 Files

```
<dir>/events.jsonl                  active segment
<dir>/events.<seq>.jsonl[.gz]       rotated segments, oldest has lowest seq
<dir>/events.lock                   advisory lock file (rotation and repair only)
<dir>/quarantine/                   corrupt lines moved aside by repair
```

### 3.3 Cursor

`{ segment_seq, inode, offset }`. An opaque token the reader stores and passes back. Surviving rotation is the library's job.

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `append(type, source, data, scope?, trace?) -> Event` | Atomically append one event. Returns the stored envelope. |
| `append_many(events) -> [Event]` | Append in order. Not atomic as a group. |
| `read(filter, limit?, order?) -> [Event]` | Scan all retained segments. `filter` = `{ type[], source[], scope, since, until, id_after }`. |
| `poll(cursor?, filter?, limit?) -> { events, cursor }` | Events after `cursor` (or from the start if none). For a poller this is O(new data). |
| `follow(filter?) -> stream` | Blocking tail. Implemented with polling plus a file-change notification where available. |
| `fold(filter, reducer, init) -> state` | Replay events through a pure reducer. |
| `rotate()` | Force rotation. |
| `prune(retain_days)` | Delete segments entirely older than the retention window. |
| `verify() -> Report` | Scan for corrupt lines without changing anything. |
| `repair() -> Report` | Section 5.4. |

Also exposed as `event-log <op> --json`. `append` over the CLI reads the JSON `data` from stdin.

### 4.1 CLI output (AXI)

Follows [CLI Conventions (AXI)](README.md#cli-conventions-axi). `--json` is unchanged (one envelope per line) and is what other libraries and programs read.

**Why it fits.** `read` is how an agent asks "what happened". A day of events can be tens of thousands of lines, and each carries a `data` object of any size.

**Default view of `read`** (illustrative):

```
events[20 of 1284]{ts,type,source,data}:
  10:23:01,step_complete,alice,"validation logic done"
  10:23:09,test_run,alice,"{passed:118,failed:1}"
  ...
by_type: step_complete 412, test_run 380, hook_claimed 96, other 396
range: 2026-10-19T00:02 to 2026-10-19T10:23
help[2]:
  event-log read --type test_run --limit 50
  event-log read --id-after 01JC4A...   # next page
```

| Rule | Applied here |
|------|--------------|
| Minimal fields | `ts` (time only when all events share a day), `type`, `source`, and `data` as a one-line summary. `--fields id,scope,trace` adds the rest |
| Truncation | `data` is flattened to one line and cut at 200 characters with `… (N chars total)`. `--full` prints the whole object |
| Aggregates | `n of total` for the filter, a `by_type` breakdown, and the time range. The total comes from the same scan `read` already performs; `--no-total` skips the count on very large logs |
| Empty state | `events: none matched (filter: type=deploy since=09:00; 1284 events in range)`. It states the filter and what was checked |
| Newest first | The default order for agents is newest first, with a generous default limit (20). `--order asc` for oldest first |
| Hints | After a truncated read: the exact `--id-after` command for the next page |

**Mutations.** `append` reads `data` from stdin, never prompts, and prints one line: `appended: <id>`. It is **not** idempotent, since each call is a new fact; this is the one deliberate exception to AXI's idempotency rule and it is stated here so nobody expects otherwise. `rotate` and `prune` are idempotent: a second `prune` with nothing to delete exits 0 with `pruned: 0 segments`. `repair` prints what was quarantined and where.

**`follow`.** A stream, not a result. It prints one summary line per event (the same four fields) and ends only when interrupted. The default view of `follow` is for a person; an agent should use `poll` with a cursor.

**Exit codes.** `0` success, including an empty read. `1` a typed error (`corrupt_line` found by `verify`, `unsupported_version`, `lock_timeout`). `2` usage. `verify` exits 1 when it finds corruption, so a script can branch on it.

**How to use it.**
- **Agent investigating:** `event-log read --type <t> --since <time>`; narrow with filters before using `--full`.
- **Program consuming events:** `--json` or read the files directly. The default view drops fields.
- **Writer in another language:** `echo '{...}' | event-log append --type X --source Y`.


## 5. Behaviour

### 5.1 Append atomicity

- The file is opened `O_APPEND | O_WRONLY | O_CREAT`; each event is serialized in memory and written with a **single** `write(2)`.
- For lines up to 4096 bytes this gives interleaving-free appends between processes on local POSIX filesystems. For lines above 4096 bytes, the writer takes the advisory lock around the write.
- The writer does not `fsync` per event by default (`durability: buffered`). `durability: fsync` syncs every append. Choose per use case: audit trails want `fsync`, chatty telemetry does not.
- Network filesystems (NFS, SMB) do not guarantee `O_APPEND` atomicity. This is unsupported; the library SHOULD detect and warn on known network mounts.

### 5.2 Reading and cursors

- Readers never lock. They read complete lines only; a trailing partial line (writer mid-write, or a crash) is held back and retried on the next poll.
- A cursor records the inode and offset. If the inode of the active segment changed (rotation happened), the reader finishes the old segment, then continues with the new one.
- `poll` is the intended pattern for "Coordinator polls for escalations". Each consumer keeps its own cursor, persisted by the consumer, so independent consumers do not affect each other.

### 5.3 Rotation and retention

- Rotate when the active segment exceeds `rotate_bytes` (default 64 MiB) or `rotate_daily` is true and the day changed.
- Rotation is `rename` of the active file to `events.<seq>.jsonl`, then a new active file is created. It runs under the advisory lock. Writers that already have the old file open finish their write there, which is safe because readers walk segments in order.
- Rotated segments MAY be gzip-compressed after `compress_after_days`.
- `prune` removes a segment only when **every** event in it is older than `retain_days` (default 90).

### 5.4 Corruption and repair

Corruption cases: a partial last line, a line that is not valid JSON, a line missing required fields.

| Case | `read` / `poll` | `repair` |
|------|-----------------|----------|
| Partial trailing line | Ignored until completed | Truncated after the backup, if it is still partial after `partial_grace` (default 60s) |
| Invalid line mid-file | Skipped, counted in `stats.skipped`, a warning callback fires | Moved to `quarantine/` with its position |
| Entire file unreadable | `Unreadable` error | Original moved to `quarantine/`, a new empty segment is started, and the loss is recorded as a synthetic event `type: "log.repaired"` |

`repair` always writes a backup copy before changing anything, and never reorders events.

### 5.5 Replay

`fold(filter, reducer, init)` streams events in `id` order (ULID order) and applies `reducer(state, event) -> state`. The library holds no summary logic. For example, a consumer building "session summaries" or "decisions for this hook" writes a reducer.

### 5.6 Redaction

An optional `redact(event) -> event` callback runs before serialization, so secrets can be dropped or masked before they hit disk. The library also ships a default key-name redactor (`password`, `token`, `secret`, `api_key`, `authorization`) that can be enabled.

## 6. Configuration

```yaml
dir: .events
durability: buffered          # buffered | fsync
max_line_bytes: 65536
rotate_bytes: 67108864
rotate_daily: false
compress_after_days: 7
retain_days: 90
partial_grace_seconds: 60
redact:
  default_keys: false
```

## 7. Failure Modes

| Error | Cause | Behaviour |
|-------|-------|-----------|
| `LineTooLarge` | Serialized event over `max_line_bytes` | Reject; nothing written |
| `InvalidType` | `type` fails the pattern | Reject |
| `DiskFull` | ENOSPC on write | Fail with `DiskFull`; no partial line is left (a short write is truncated back). The caller decides how to escalate |
| `PermissionDenied` | Directory or file not writable | Fail |
| `Unreadable` | File cannot be parsed at all | Reads fail; `repair` offered |
| `LockTimeout` | Rotation or repair lock not acquired within `lock_timeout` | Fail, retryable |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](error-classifier.md) record (a data format, not a dependency). Suggested `recoverability` below; severity is the consumer's policy.

| Error | Suggested recoverability |
|-------|--------------------------|
| `LockTimeout` | `transient` |
| `DiskFull` | `ambiguous` |
| `LineTooLarge`, `InvalidType`, `PermissionDenied`, `Unreadable` | `permanent` (`Unreadable` until `repair`) |

## 8. Acceptance Criteria

1. 20 processes appending 10,000 events each (events under 4 KiB) produce exactly 200,000 valid lines, with no interleaving.
2. A writer killed mid-write leaves at most one partial trailing line; readers do not crash or return it.
3. A poller holding a cursor across a rotation sees every event exactly once.
4. `prune` never removes a segment that holds an event newer than the retention window.
5. `repair` followed by `verify` reports clean; the quarantine folder contains every removed line.
6. `fold` over 1M events completes in constant memory.
7. `ts` is monotonic per writer even if the system clock steps backwards (the library clamps to the previous value).
8. A read of 10,000 matching events prints 20 by default with `20 of 10000` and the next-page hint; `--limit` changes the count.
9. A read with no match prints a line naming the filter and exits 0.
10. An event with 50 KB of `data` prints at most about 200 characters of it in the default view; `--full` and `--json` print all of it.
11. `prune` run twice exits 0 both times; the second reports nothing removed.

## 9. How UMAS Uses It

| UMAS use | Mapping |
|----------|---------|
| `.umas/events.jsonl` | `dir = .umas`, file name configurable (see deviation below) |
| Escalation: `{"event":"escalate","severity":"P1","reason":"..."}` | `append(type="escalate", source=<agent>, data={severity, reason})`. Coordinator uses `poll` with its own cursor |
| Handoff request | `append(type="handoff_request", data={task_id})`; the Scheduler polls |
| Session history (`SessionHistoryInterface`) | Event types `session_started`, `session_ended`, `decision_made`, `file_modified`, `commit_created`, `token_usage`, ... with `fold` reducers for `query_sessions` and `get_session_context` |
| Audit retention, 90 days | `retain_days = 90` |
| `umas debug replay` | `read(scope=<session>)` or `fold` |
| Typed errors | Mapped to records by UMAS (`LockTimeout` as `transient`; the rest per section 7). The record's `severity` can be written as an `escalate` event's `severity` |

The UMAS event-type catalogue stays in UMAS (Tier 0 contracts), not in this library.

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.1 (session discovery), §3.3 (signalling), §4.3 (corrupted log), §4.16 (retention); and `TECHNICAL-DESIGN-SPEC-PART2.md` §3.4 (`SessionHistoryService`).

| Deviation | Why |
|-----------|-----|
| One envelope for both signals and session events | The source has two shapes: `{"event":"escalate",...}` (design spec) and `{id, session_id, agent_id, timestamp, event_type, data}` (Part 2). They are unified: `event`/`event_type` -> `type`, `agent_id` -> `source`, `session_id` -> `scope` |
| File name is a parameter | The source uses both `.umas/events.jsonl` and `.umas/.events.jsonl`. This must be fixed to one name in the UMAS Tier 0 contract |
| Reading is cursor-based, not a full scan | The source `query_sessions` re-reads the whole file for each query; pollers would degrade as the log grows |
| Summary and context builders removed | Domain logic. They become `fold` reducers owned by the consumer |

## 11. Open Questions

1. Is a pure-file design enough at 20-30 concurrent writers, or does Tier 3 scale want SQLite WAL as an alternative backend behind the same interface?
2. Should `ts` come from a hybrid logical clock to make cross-machine ordering sound if federation is ever added?
3. Should the CLI offer `follow` with `--exec <cmd>` to run a command per event, or is that out of scope?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Code moved verbatim from the original UMAS technical design. It illustrates one way to implement this spec and uses UMAS names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [libs/README.md](README.md).

### 12.1 Session history interface (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART2.md` §3.4.2

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
import json
import aiofiles

@dataclass
class SessionEvent:
    id: str
    session_id: str
    agent_id: str
    timestamp: datetime
    event_type: str
    data: Dict

@dataclass
class SessionSummary:
    session_id: str
    agent_id: str
    task_id: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    decisions: List[str]
    files_modified: List[str]
    commits: List[str]
    token_usage: int

class SessionHistoryService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.events_file = project_root / ".umas" / ".events.jsonl"
        self.events_file.parent.mkdir(parents=True, exist_ok=True)
        
    async def log_event(
        self,
        session_id: str,
        agent_id: str,
        event_type: str,
        data: Dict,
    ) -> None:
        """Log an event to the session history."""
        event = SessionEvent(
            id=str(uuid.uuid4()),
            session_id=session_id,
            agent_id=agent_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            data=data,
        )
        
        # Append to JSONL file
        async with aiofiles.open(self.events_file, mode='a') as f:
            event_dict = {
                "id": event.id,
                "session_id": event.session_id,
                "agent_id": event.agent_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "data": event.data,
            }
            await f.write(json.dumps(event_dict) + '\n')
    
    async def query_sessions(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SessionSummary]:
        """Query session history with filters."""
        sessions_map: Dict[str, SessionSummary] = {}
        
        async with aiofiles.open(self.events_file, mode='r') as f:
            async for line in f:
                event_dict = json.loads(line)
                event = SessionEvent(
                    id=event_dict["id"],
                    session_id=event_dict["session_id"],
                    agent_id=event_dict["agent_id"],
                    timestamp=datetime.fromisoformat(event_dict["timestamp"]),
                    event_type=event_dict["event_type"],
                    data=event_dict["data"],
                )
                
                # Apply filters
                if agent_id and event.agent_id != agent_id:
                    continue
                if since and event.timestamp < since:
                    continue
                
                # Build session summary
                if event.session_id not in sessions_map:
                    sessions_map[event.session_id] = SessionSummary(
                        session_id=event.session_id,
                        agent_id=event.agent_id,
                        task_id=event.data.get("task_id", ""),
                        started_at=event.timestamp,
                        ended_at=None,
                        status="active",
                        decisions=[],
                        files_modified=[],
                        commits=[],
                        token_usage=0,
                    )
                
                session = sessions_map[event.session_id]
                
                # Update session based on event type
                if event.event_type == "session_ended":
                    session.ended_at = event.timestamp
                    session.status = event.data.get("status", "completed")
                elif event.event_type == "decision_made":
                    session.decisions.append(event.data.get("decision", ""))
                elif event.event_type == "file_modified":
                    file_path = event.data.get("file_path", "")
                    if file_path not in session.files_modified:
                        session.files_modified.append(file_path)
                elif event.event_type == "commit_created":
                    session.commits.append(event.data.get("commit_hash", ""))
                elif event.event_type == "token_usage":
                    session.token_usage += event.data.get("tokens", 0)
        
        sessions = list(sessions_map.values())
        
        # Apply task_id filter
        if task_id:
            sessions = [s for s in sessions if s.task_id == task_id]
        
        # Sort by started_at descending
        sessions.sort(key=lambda s: s.started_at, reverse=True)
        
        return sessions[:limit]
    
    async def get_session_context(
        self,
        session_id: str,
    ) -> Dict:
        """Get full context for a specific session."""
        events = []
        
        async with aiofiles.open(self.events_file, mode='r') as f:
            async for line in f:
                event_dict = json.loads(line)
                if event_dict["session_id"] == session_id:
                    event = SessionEvent(
                        id=event_dict["id"],
                        session_id=event_dict["session_id"],
                        agent_id=event_dict["agent_id"],
                        timestamp=datetime.fromisoformat(event_dict["timestamp"]),
                        event_type=event_dict["event_type"],
                        data=event_dict["data"],
                    )
                    events.append(event)
        
        # Reconstruct session context from events
        context = {
            "session_id": session_id,
            "events": [asdict(e) for e in events],
            "decisions": self._extract_decisions(events),
            "files_modified": self._extract_files(events),
            "tool_calls": self._extract_tool_calls(events),
            "commits": self._extract_commits(events),
        }
        
        return context
    
    def _extract_decisions(self, events: List[SessionEvent]) -> List[Dict]:
        """Extract decisions from events."""
        decisions = []
        for event in events:
            if event.event_type == "decision_made":
                decisions.append({
                    "timestamp": event.timestamp.isoformat(),
                    "decision": event.data.get("decision", ""),
                    "rationale": event.data.get("rationale", ""),
                })
        return decisions
    
    def _extract_files(self, events: List[SessionEvent]) -> List[str]:
        """Extract modified files from events."""
        files = set()
        for event in events:
            if event.event_type == "file_modified":
                files.add(event.data.get("file_path", ""))
        return sorted(list(files))
    
    def _extract_tool_calls(self, events: List[SessionEvent]) -> List[Dict]:
        """Extract tool calls from events."""
        tool_calls = []
        for event in events:
            if event.event_type == "tool_called":
                tool_calls.append({
                    "timestamp": event.timestamp.isoformat(),
                    "tool_name": event.data.get("tool_name", ""),
                    "parameters": event.data.get("parameters", {}),
                    "result": event.data.get("result", {}),
                })
        return tool_calls
    
    def _extract_commits(self, events: List[SessionEvent]) -> List[Dict]:
        """Extract commits from events."""
        commits = []
        for event in events:
            if event.event_type == "commit_created":
                commits.append({
                    "timestamp": event.timestamp.isoformat(),
                    "commit_hash": event.data.get("commit_hash", ""),
                    "message": event.data.get("message", ""),
                    "files": event.data.get("files", []),
                })
        return commits
```

### 12.2 Event types schema (YAML)

Source: `TECHNICAL-DESIGN-SPEC-PART2.md` §3.4.3

```yaml
event_types:
  session_started:
    data:
      task_id: string
      task_description: string
      hook_path: string
      base_branch: string
      
  session_ended:
    data:
      status: enum[completed, failed, abandoned]
      reason: string
      
  tool_called:
    data:
      tool_name: string
      parameters: object
      result: object
      duration_ms: integer
      
  decision_made:
    data:
      decision: string
      rationale: string
      alternatives_considered: array[string]
      
  file_modified:
    data:
      file_path: string
      operation: enum[create, update, delete]
      lines_changed: integer
      
  commit_created:
    data:
      commit_hash: string
      message: string
      files: array[string]
      
  escalation_triggered:
    data:
      severity: enum[P0, P1, P2, P3]
      reason: string
      escalated_to: string
      
  token_usage:
    data:
      tokens: integer
      cumulative_tokens: integer
      percentage_used: float
      
  handoff_initiated:
    data:
      from_agent: string
      to_agent: string
      reason: string
      state_transferred: boolean
```
