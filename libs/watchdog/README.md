# watchdog

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS. Processes and files only; no AI, no database.

---

## 1. Purpose

Supervise long-running local processes by heartbeat and by **progress**, and apply a graduated recovery ladder when one is dead or stuck. A watcher can itself be watched, forming a supervision chain.

## 2. Scope and Non-Goals

**In scope**
- Heartbeat emission and checking over a file-based transport
- Distinguishing `dead` (no heartbeat) from `stalled` (alive but not progressing)
- Restart with backoff, kill escalation, crash-loop detection
- A hook point where a caller decides what to do (for example, an AI triage step)
- Declarative supervision chains

**Non-goals**
- Judgement. Whether a stalled worker should be nudged, handed off, or restarted is expressed as a configured ladder plus an optional caller callback. The library has no model or heuristics beyond thresholds.
- Replacing the OS service manager. The watchdog is a Python process and cannot restart itself. The top of any chain runs under the operating system's service manager: launchd on macOS, systemd on Linux, a Windows service on Windows. The library does not install itself as a service. Service unit files are not written yet.
- Metrics/alerts backends. It emits events through a callback.

## 3. Concepts and Data Model

### 3.1 Node

```
{ name, kind: "process"|"external",
  start: { argv[], cwd, env{} },            // process nodes only
  heartbeat: { path, interval, miss_threshold },
  progress?: { source: ProgressSource, stall_after },
  ladder: [ Action ... ],
  restart: { backoff, max_restarts, window, on_loop: "escalate"|"stop" } }
```

`kind: external` means the node's lifecycle is managed elsewhere; the library only observes it and runs ladder actions that are callbacks.

### 3.2 Heartbeat

A small JSON file updated atomically (write temp, rename):

```json
{ "v":1, "name":"triage", "pid":4242, "ts":"...", "seq": 981, "status":"ok|busy|degraded", "note":"" }
```

`Heartbeater(path, interval)` runs in the supervised process and rewrites it. Any language can emit this file by hand.

A node is **responsive** when `now - ts < interval * miss_threshold` and (for local pids) the pid is alive.

### 3.3 Progress

A heartbeat shows the process runs; it does not show work is advancing. A **progress source** returns a monotonic marker (a timestamp or counter):

| Source | Example |
|--------|---------|
| `file_mtime(path)` | Last write to a log |
| `git_commit_time(worktree)` | Last commit on a branch |
| `counter_file(path)` | A number that increases |
| `callback()` | Caller code |

The node is **stalled** when it is responsive but the marker has not advanced for `stall_after`.

### 3.4 Node states

`starting` -> `healthy` | `stalled` | `unresponsive` -> `restarting` -> `healthy`; terminal/blocked: `failed` (crash loop, or restarts exhausted).

### 3.5 Ladder

An ordered list of actions per unhealthy condition. Each rung has a `wait` before the next is tried.

| Action | Effect |
|--------|--------|
| `nudge` | Deliver a wake signal: write a `<name>.nudge` file, send a signal (SIGUSR1), or call a callback |
| `request_graceful` | Ask the node to checkpoint and exit (`<name>.stop` file or SIGTERM) |
| `terminate` | SIGTERM to the process group, wait `kill_grace`, then SIGKILL |
| `restart` | `terminate` + start |
| `escalate` | Emit an `escalate` event with the node's context; take no local action |
| `callback(name)` | Run caller code; its return value (`handled` / `continue` / `abort`) decides whether the ladder proceeds |

Defaults:
- `stalled`: `nudge` -> `request_graceful` -> `restart` -> `escalate`
- `unresponsive`: `terminate` -> `restart` -> `escalate`

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `Heartbeater.start(path, interval, status_fn?)` / `.stop()` | Used inside supervised processes. |
| `Watchdog.load(config)` | Build the node set from configuration. |
| `Watchdog.run()` | Blocking loop: tick, evaluate every node, run ladders. |
| `Watchdog.check_once() -> [NodeStatus]` | One evaluation pass without side effects (use for health-check commands). |
| `Watchdog.status() -> [NodeStatus]` | Last evaluation. |
| `on_event(callback)` | Receive `node_state_changed`, `ladder_action`, `restarted`, `crash_loop`, `escalate`. |

Also `watchdog run|check --config <file> --json`, and `watchdog beat <path>` for scripts that cannot link the library.

## 5. Behaviour

### 5.1 Evaluation tick

Every `tick` (default 10s; independent of node heartbeat intervals), for each node: read the heartbeat file; evaluate responsiveness; evaluate progress; derive the state. A state change emits an event. A node that stays unhealthy advances through its ladder, respecting each rung's `wait`; a return to `healthy` resets the ladder.

### 5.2 Restart policy

- Backoff between restarts: `initial` (5s) doubling to `max` (5 min).
- `max_restarts` within `window` (for example 5 in 10 min) -> `failed` (crash loop): the library **stops restarting**, emits `crash_loop` and `escalate`. This prevents a thrashing restart storm from hiding a real fault.
- A fresh start grants `startup_grace` (default 60s) with no health judgement.
- A restart never reuses a heartbeat written by the previous process: files carry `pid`; a mismatch is "no heartbeat yet".

### 5.3 Kill safety

Processes start in their own process group; `terminate` signals the group so child processes die too. SIGKILL is a last resort after `kill_grace`. The library never kills a pid it did not start unless the node is configured with `adopt_pid: true` and the pid in the heartbeat matches.

### 5.4 Chains

A chain is just nodes whose supervised process is itself a `Watchdog` over other nodes:

```
OS service manager -> watchdog (level 1) -> process A -> watchdog (level 2) -> process B ...
```

Each level only knows its direct children. The library has no global tree, so a level can be replaced by a different implementation or language.

### 5.5 Decision hook

For judgement beyond thresholds, a node's ladder can use `callback`. The caller may inspect context and return `handled` (skip the default action), `continue`, or `abort`. For example, a caller might consult an AI triage step here. The library provides the timing, state, and safety, and no intelligence.

## 6. Configuration

```yaml
tick_seconds: 10
nodes:
  - name: triage
    kind: process
    start: { argv: ["python", "-m", "triage"], cwd: "." }
    heartbeat: { path: ".run/triage.hb", interval_seconds: 30, miss_threshold: 3 }
    startup_grace_seconds: 60
    restart: { backoff: {initial_seconds: 5, max_seconds: 300}, max_restarts: 5, window_seconds: 600 }
    kill_grace_seconds: 10
  - name: worker-alice
    kind: external
    heartbeat: { path: ".run/alice.hb", interval_seconds: 60, miss_threshold: 5 }
    progress: { source: git_commit_time, path: ".hooks/auth-login", stall_after_seconds: 600 }
    ladder:
      stalled:      [nudge, request_graceful, escalate]
      unresponsive: [escalate]
```

## 7. Failure Modes

| Condition | Behaviour |
|-----------|-----------|
| Heartbeat file unreadable or partial | Treated as "no change"; atomic writes make partial reads rare |
| Watchdog itself killed | Its parent in the chain (or the OS service manager) restarts it; on start it adopts `startup_grace` for all nodes |
| Clock jump | Uses monotonic time for intervals where possible; heartbeat `ts` is wall clock, so large jumps cause one false `unresponsive` which the `seq` counter allows to be detected and ignored |
| Start command fails immediately | Counted toward the crash-loop window |
| Node ladder exhausted | State `failed`; `escalate` emitted once; no further actions until a human or caller resets it |
| **Boot after machine shutdown** | On startup, all nodes whose heartbeat `ts` is older than `now - (interval * miss_threshold)` are in `unresponsive` state at tick 0. For nodes marked `kind: external` with a `machine_pause_aware: true` flag, the watchdog suppresses the `unresponsive` ladder for one `startup_grace` period and emits a `boot_stale` event instead. This allows the consuming application to distinguish "crashed before shutdown" from "was running cleanly and is now awaiting resume". |
| **Heartbeat absent because agent was paused cleanly** | If `<hook-path>/PAUSE.md` exists and `<hook-path>/.pause` does not (shutdown completed cleanly), the watchdog treats the node as `paused` rather than `unresponsive` and skips the restart ladder entirely. |

### Error records

This library keeps its own typed errors and does not import any error library. A consumer that wants one error vocabulary can express each of them as an [error-classifier](../error-classifier/README.md) record (a data format, not a dependency). Suggested `recoverability` below; severity is the consumer's policy.

The watchdog reports conditions, not exceptions. A node reaching `failed` or an `escalate` event carries a reason; a consumer can wrap it as an error record.

| Condition | Suggested recoverability |
|-----------|--------------------------|
| `unresponsive`, `stalled` | `transient` while the ladder has rungs left |
| `failed` (ladder exhausted), crash loop | `permanent` until a person or caller resets the node |

## 8. Acceptance Criteria

1. `kill -9` of a supervised process is detected and restarted within `interval * miss_threshold + tick`.
2. A process that heartbeats but stops advancing its progress marker is reported `stalled`, not `unresponsive`, and walks the stalled ladder in order.
3. A process that crashes immediately every time is restarted at most `max_restarts` times, then `failed` with one `escalate` event.
4. Terminating a node kills its child processes as well.
5. `check_once` has no side effects.
6. Restarting the watchdog while all nodes are healthy causes no restarts.
7. A node's old heartbeat file (stale pid) never makes a newly started node look healthy.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


The three-tier watchdog is three levels of this library, with intelligence added only through callbacks.

| UMAS tier | Library mapping |
|-----------|-----------------|
| Daemon -> Triage Agent (heartbeat 3 min) | Level 1: `process` node `triage`; ladder `terminate -> restart -> escalate` |
| Triage Agent -> System Patrol | Level 2: `triage` runs a `Watchdog` with a `callback` rung that applies AI judgement before restarting Patrol |
| System Patrol -> Project Monitors / Merge Queue | Level 3: patrol observes `external` nodes |
| Project Monitor stuck detection | Per-worker `external` node: no heartbeat 5 min = `unresponsive`; no commit 10 min = `stalled` via `git_commit_time` |
| Recovery: nudge -> graceful handoff -> emergency handoff | Stalled ladder: `nudge -> request_graceful -> callback(emergency_handoff)` |
| 95% token usage with no handoff | Not a watchdog concern; combine a [budget-meter](../budget-meter/README.md) event with a callback |
| `escalate` events | Wrapped as records by UMAS; the node, ladder rung and reason go into `context`. See [error-classifier](../error-classifier/README.md) section 9 |
| **Machine shutdown / boot recovery** | All worker nodes are `kind: external, machine_pause_aware: true`. On boot, the watchdog emits `boot_stale` per node and suppresses restart for one `startup_grace`. UMAS daemon reads `PAUSE.md` per worktree and either resumes (token valid) or sets `auth_expired` before the grace window ends. |

## 10. Source Material and Deviations

Extracted from `UMAS-TECH-DESIGN-SPEC.md` §3.5 (three-tier watchdog, Project Monitor) and `TECHNICAL-DESIGN-SPEC-PART3.md` §7.3 (Rust `Daemon`).

| Deviation | Why |
|-----------|-----|
| Dead vs stalled | The source Daemon checks only that a heartbeat arrived. Stuck agents (alive, no progress) are detected separately by Project Monitors via commit age; this unifies both |
| Crash-loop protection | The source restarts without limit |
| File-based heartbeat | The source Daemon health check reads `last_heartbeat`, but nothing in the source calls `record_heartbeat` from the Triage Agent; there is no transport defined. A file works across languages and processes |
| Process-group kill | Source `kill -9 <pid>` leaves child processes (agent tool subprocesses) running |
| Reasonable check interval | Source ticks every 60s against a 180s interval x2 threshold, with the first check able to pass on `start` time alone |

## 11. Open Questions

1. Windows support: process groups and signals differ. Is Windows in scope for the first release? (The source mentions named pipes for Windows.)
2. Should the heartbeat transport also support a Unix socket for sub-second liveness, or is a file enough at these intervals?
3. Where should a human-visible status file be written so a CLI `status` works when the watchdog is down?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Example code illustrating one way to implement this spec. May use consumer-specific names and paths. The sections above are authoritative; where they differ (see section 10), the sections above win. It is excluded from the independence rules in [libs/README.md](./README.md). The code is in Rust, which is not in the stack. It is legacy and will be ported to Python.

### 12.1 Daemon (Rust, legacy: language not in stack, port to Python)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §7.3.2

```rust
use tokio::time::{interval, Duration};
use std::process::Command;

pub struct Daemon {
    triage_agent_pid: Option<u32>,
    heartbeat_interval: Duration,
    last_heartbeat: Option<Instant>,
}

impl Daemon {
    pub fn new() -> Self {
        Self {
            triage_agent_pid: None,
            heartbeat_interval: Duration::from_secs(180), // 3 minutes
            last_heartbeat: None,
        }
    }
    
    pub async fn run(&mut self) {
        // Start triage agent
        self.start_triage_agent().await;
        
        // Monitor heartbeat
        let mut interval = interval(Duration::from_secs(60));
        
        loop {
            interval.tick().await;
            
            if !self.is_triage_agent_healthy() {
                tracing::warn!("Triage agent unhealthy, restarting");
                self.restart_triage_agent().await;
            }
        }
    }
    
    async fn start_triage_agent(&mut self) {
        let child = Command::new("python")
            .arg("-m")
            .arg("umas.agents.triage")
            .spawn()
            .expect("Failed to start triage agent");
        
        self.triage_agent_pid = Some(child.id());
        self.last_heartbeat = Some(Instant::now());
    }
    
    fn is_triage_agent_healthy(&self) -> bool {
        if let Some(last_hb) = self.last_heartbeat {
            last_hb.elapsed() < self.heartbeat_interval * 2
        } else {
            false
        }
    }
    
    pub fn record_heartbeat(&mut self) {
        self.last_heartbeat = Some(Instant::now());
    }
    
    async fn restart_triage_agent(&mut self) {
        // Kill old process
        if let Some(pid) = self.triage_agent_pid {
            let _ = Command::new("kill")
                .arg("-9")
                .arg(pid.to_string())
                .output();
        }
        
        // Start new process
        self.start_triage_agent().await;
    }
}
```

### 12.2 TriageAgent (Python)

Source: `TECHNICAL-DESIGN-SPEC-PART3.md` §7.4.2

> This is the UMAS-specific consuming application of this library. The `watchdog` library itself has no Python agent code; `TriageAgent` is a Level 2 watcher that uses `Watchdog` to supervise `SystemPatrol`, and uses a `callback` rung to apply AI-driven triage before restarting. See §9 "How UMAS uses it".

```python
import asyncio
from datetime import datetime, timedelta

class TriageAgent:
    def __init__(
        self,
        daemon_client: DaemonClient,
        system_patrol_monitor: SystemPatrolMonitor,
    ):
        self.daemon_client = daemon_client
        self.system_patrol_monitor = system_patrol_monitor
        self.heartbeat_interval = 180  # 3 minutes
        
    async def run(self) -> None:
        """Main triage loop."""
        
        # Start heartbeat task
        asyncio.create_task(self._send_heartbeats())
        
        # Monitor System Patrol
        while True:
            try:
                # Check System Patrol health
                patrol_status = await self.system_patrol_monitor.check_health()
                
                if not patrol_status.healthy:
                    await self._handle_patrol_failure(patrol_status)
                    
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                # Log error but keep running
                await self._handle_triage_error(e)
    
    async def _send_heartbeats(self) -> None:
        """Send heartbeats to Daemon."""
        while True:
            await self.daemon_client.record_heartbeat()
            await asyncio.sleep(self.heartbeat_interval)
    
    async def _handle_patrol_failure(
        self,
        status: PatrolStatus,
    ) -> None:
        """Handle System Patrol failure."""
        
        # Attempt restart
        try:
            await self.system_patrol_monitor.restart()
        except Exception:
            # Escalate to human if restart fails
            await self._escalate_to_human(
                severity="P1",
                reason=f"System Patrol failed: {status.error}",
            )
```
