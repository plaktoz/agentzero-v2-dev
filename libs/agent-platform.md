# agent-platform

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](README.md)
> **Independence:** no dependency on UMAS or on any LLM SDK. Needs only a filesystem and optionally a git repository.
> **Build posture: thin registry.** The interface is small by design. Each adapter is a configuration block plus at most a few file-format rules.

---

## 1. Purpose

Abstract the differences between coding agent harnesses — the tools that actually run an agent session (Claude Code, IBM Bob, GitHub Copilot, custom agents) — behind one interface. The consuming application assigns work to a harness, reads back its signal when the work is done, and transfers context across harness boundaries without knowing which harness is on either end.

## 2. Scope and Non-Goals

**In scope**
- A registry of named platform adapters, each describing its context format, work-assignment method, and completion-signal method
- A platform-neutral work assignment record (what to do, where the hook is, what files are relevant)
- A platform-neutral completion signal (outcome, artefact paths, token usage if available)
- Cross-platform context transfer: pack on the source side, unpack on the target side
- A plugin interface so a user can register a custom adapter without modifying this library
- A capability declaration per adapter (what the platform can do)

**Non-goals**
- Calling LLM providers. That is [llm-gateway](llm-gateway.md). Some platforms are also LLM providers (IBM Bob); that distinction is a decision for the consuming application, recorded in section 11.
- Spawning OS processes or managing agent lifecycle. The harness decides how it runs; this library only defines what it reads and writes.
- Routing or selection logic (which platform to use for which task). That belongs to [packs/router-heuristic](../packs/router-heuristic.md) and the consuming application.
- Authentication or secrets management. Credentials are passed in by the caller; never stored by this library.
- Metrics or alerting. Usage figures are returned in the completion signal; the caller forwards them to [budget-meter](budget-meter.md).

## 3. Concepts and Data Model

### 3.1 Platform adapter

A named record that describes one harness.

```
PlatformAdapter:
  name:              string                      # stable identifier, e.g. "claude-code"
  display_name:      string
  capabilities:      Capability[]
  context_format:    "markdown" | "json" | "file-based"
  hook_support:      bool                        # can read a hook-store worktree as work input
  completion_signal: "commit-message" | "file" | "polling" | "none"
  assign:            AssignFn                    # see 3.3
  read_signal:       ReadSignalFn                # see 3.4
  pack_context:      PackContextFn               # see 3.5
  unpack_context:    UnpackContextFn             # see 3.5
```

### 3.2 Capability

A capability is a string token. The library defines a fixed vocabulary; unknown tokens are allowed and treated as opaque.

| Token | Meaning |
|-------|---------|
| `code-generation` | Writes new code from a spec |
| `code-completion` | Inline suggestions in an IDE |
| `architecture-design` | Long-context design and ADR authoring |
| `code-review` | Reviews a diff against standards and spec |
| `refactoring` | Restructures existing code |
| `security-review` | Checks for security and compliance issues |
| `documentation` | Writes or updates docs |
| `enterprise-compliance` | Enforces enterprise policies (audit logging, RBAC) |

### 3.3 Work assignment

```
WorkAssignment:
  id:             string          # ULID, stable across platform boundaries
  title:          string
  description:    string          # plain text or markdown
  hook_path:      string?         # path to a hook-store worktree, if hook_support = true
  relevant_files: string[]        # relative paths the agent should read first
  constraints:    string[]        # e.g. ["no new dependencies", "test coverage ≥ 90%"]
  context_pack:   ContextPack?    # see 3.5; supplied when crossing a platform boundary
  assigned_at:    string          # RFC 3339
```

`assign(assignment, config) -> AssignmentReceipt`

A receipt confirms the assignment was delivered to the harness. It carries a `platform_ref` (platform-specific ID, may be null for file-based platforms) and the path of the written assignment file if any.

### 3.4 Completion signal

```
CompletionSignal:
  assignment_id:  string
  platform:       string
  outcome:        "done" | "blocked" | "escalated" | "abandoned"
  summary:        string          # one paragraph, human-readable
  artefact_paths: string[]        # files the agent wrote or modified
  hook_path:      string?         # hook-store path after the agent's commits
  token_usage:    TokenUsage?     # { input, output, cached } — best-effort
  reason:         string?         # for non-done outcomes
  completed_at:   string
```

`read_signal(config) -> CompletionSignal | None`

Returns the most recent unread signal for any assignment, or `None` if the harness has not yet signalled. The caller is responsible for polling or event-driven wakeup; the library does not block.

### 3.5 Context pack

When handing off between platforms, the source packs the relevant context; the target unpacks it.

```
ContextPack:
  schema_version: 1
  source_platform: string
  target_platform: string
  assignment_id:   string
  task_summary:    string         # what has been done so far (compact register)
  decisions:       Decision[]     # { summary, rationale } — key choices made
  artefact_paths:  string[]       # files already written
  hook_path:       string?        # hook-store path with committed work
  packed_at:       string
  checksum:        string         # SHA-256 of the canonical JSON of all fields except this one
```

`pack_context(assignment, signal, opts) -> ContextPack`
`unpack_context(pack, target_adapter) -> WorkAssignment`

`unpack_context` validates the checksum, translates the context into a `WorkAssignment` shaped for the target platform's `context_format`, and returns it ready to pass to `assign`.

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `register(adapter)` | Add or replace an adapter in the registry. |
| `get(name) -> PlatformAdapter` | Retrieve a registered adapter. Fails `UnknownPlatform` if not found. |
| `list() -> [PlatformAdapter]` | All registered adapters. |
| `capabilities_of(name) -> Capability[]` | Shorthand. |
| `supports(name, capability) -> bool` | Whether a platform declares a capability. |
| `assign(platform, assignment, config) -> AssignmentReceipt` | Deliver a work assignment to a platform. |
| `read_signal(platform, config) -> CompletionSignal \| None` | Read the most recent completion signal, or None. |
| `pack_context(platform, assignment, signal, opts) -> ContextPack` | Pack context for handoff out of `platform`. |
| `unpack_context(pack, target_platform) -> WorkAssignment` | Translate a context pack into an assignment for `target_platform`. |
| `validate(config) -> Report` | Check that all configured platforms are registered, credentials are present in env, and required capabilities are available. |

Also `agent-platform <op> --json`.

## 5. Behaviour

### 5.1 Built-in adapters

Three adapters are shipped with the library. They may be overridden by the caller.

**`claude-code`**
```
capabilities:      [code-generation, architecture-design, code-review, refactoring, documentation]
context_format:    markdown
hook_support:      true
completion_signal: commit-message   # looks for [done] or [blocked] in the hook's latest commit
assign:            writes TASK.md into the hook worktree and optionally a .claude/task.md hint file
```

**`ibm-bob`**
```
capabilities:      [code-generation, code-review, security-review, documentation, enterprise-compliance]
context_format:    json
hook_support:      true
completion_signal: file             # reads .run/<assignment_id>.signal.json written by Bob's hook
assign:            writes TASK.json into the hook worktree
```

**`copilot`**
```
capabilities:      [code-completion, code-generation]
context_format:    file-based
hook_support:      false
completion_signal: none             # IDE-native; no programmatic signal; use polling on file mtime
assign:            writes .github/copilot-task.md for IDE pickup
```

### 5.2 Assignment delivery

`assign` does the minimum needed to make the work visible to the harness. For hook-supporting platforms it writes the assignment into the hook worktree at a known path (`TASK.md` or `TASK.json` per adapter). For file-based platforms it writes to an agreed location. It never starts a process, calls an API, or mutates git history — those are the harness's jobs.

### 5.3 Completion signal detection

`read_signal` is intentionally non-blocking and non-polling. The caller drives the polling loop (or wires in a file-watch / event-log `follow`). For `commit-message` signals the library scans the hook worktree's git log for a commit matching the signal pattern. For `file` signals it checks for the signal file. For `polling` it reads a status endpoint (caller supplies the URL). For `none` it reads file modification times and returns a synthetic signal when artefacts were updated.

A signal is consumed exactly once: after `read_signal` returns a non-None result, it marks it read (writes a `.signal.ack` alongside the signal file, or records the last-seen commit SHA). Subsequent calls return `None` until a new signal arrives.

### 5.4 Cross-platform handoff

```
1. source platform completes; read_signal returns a CompletionSignal.
2. pack_context(source_platform, assignment, signal) -> ContextPack.
3. The pack is validated (checksum). Artefact paths are confirmed to exist.
4. unpack_context(pack, target_platform) -> new WorkAssignment.
   - Translates context_format: markdown ↔ json ↔ file-based as needed.
   - Preserves the original assignment_id so the work bundle stays linked.
5. assign(target_platform, new_assignment, config).
```

Context is never lost in translation: fields that cannot be represented in the target's format are written as a plain-text appendix in the assignment's `description`.

### 5.5 Plugin registration

A caller adds a custom adapter by calling `register(adapter)` with a fully populated `PlatformAdapter` struct. The `assign`, `read_signal`, `pack_context`, and `unpack_context` fields are callbacks supplied by the caller. The library validates that all required fields are present and that the `capabilities` list contains at least one known token.

Custom adapters override built-ins of the same name, so a caller can patch the `ibm-bob` adapter's `assign` logic without forking the library.

### 5.6 Security

- Credentials (API keys, tokens) are passed via `config` at call time. The library never stores them.
- `config` objects are never logged or written to disk by the library.
- The `ContextPack` checksum (`SHA-256`) detects corruption or tampering in transit. `unpack_context` refuses a pack whose checksum does not match.
- Artefact paths in a pack are validated to be relative paths within the hook worktree or project root; absolute paths and `..` traversal are rejected.

## 6. Configuration

```yaml
# Per-platform, supplied by the consuming application at call time.
# The library has no global config file of its own.

platforms:
  claude-code:
    enabled: true
    hook_base: ".hooks"         # root directory for hook-store worktrees
    signal_pattern: "\\[(done|blocked|escalated)\\]"   # regex on commit messages

  ibm-bob:
    enabled: true
    hook_base: ".hooks"
    signal_file_dir: ".run"

  copilot:
    enabled: false
    task_file: ".github/copilot-task.md"
    poll_paths: ["src/", "tests/"]   # watch these for file mtime changes
```

Each platform's config block is passed to its `assign` and `read_signal` functions; the library does not interpret it beyond basic presence checking.

## 7. Failure Modes

| Error | Cause | Behaviour |
|-------|-------|-----------|
| `UnknownPlatform` | `get` or `assign` called with an unregistered name | Fail immediately |
| `CapabilityMissing` | `assign` called for a task that requires a capability the platform does not declare | Fail with the missing capability listed; caller should route to another platform |
| `AssignmentWriteFailed` | Could not write task file (permission, disk full) | Fail; nothing partially written |
| `SignalCorrupt` | Signal file exists but is unparseable | Return `None` and emit a warning event; do not consume the file |
| `ChecksumMismatch` | `unpack_context` finds the pack checksum does not match | Fail `ChecksumMismatch`; do not produce an assignment |
| `PathTraversal` | Artefact path in a context pack escapes the project root | Fail `PathTraversal`; reject the entire pack |
| `HookNotFound` | `assign` called with a `hook_path` that does not exist | Fail; the caller must create the hook via `hook-store` first |

## 8. Acceptance Criteria

1. `assign` for `claude-code` writes `TASK.md` into the given hook worktree; `read_signal` detects a subsequent commit matching `[done]` and returns a signal; a second call to `read_signal` returns `None`.
2. A cross-platform handoff from `claude-code` to `ibm-bob`: `pack_context` produces a pack whose checksum is valid; `unpack_context` produces a `WorkAssignment` with `context_format = json`; `assign` writes `TASK.json` into the target hook.
3. A pack with a mutated `task_summary` field fails `ChecksumMismatch` in `unpack_context`.
4. Registering a custom adapter with `name = "claude-code"` overrides the built-in; subsequent `assign` calls use the custom `assign` callback.
5. `validate` returns an error when a configured platform's `hook_base` directory does not exist.
6. An artefact path of `../../etc/passwd` in a context pack is rejected with `PathTraversal`.

## 9. How UMAS Uses It

| UMAS concept | Mapping |
|---|---|
| Module 7: Multi-Agent Platform Support | This library is the implementation of that module's adapter layer |
| `ClaudeCodeAdapter`, `IBMBobAdapter`, `CopilotAdapter` from the PRD | The three built-in adapters in §5.1 |
| Agent selection strategy (PRD §Agent Selection Strategy) | Not this library. UMAS applies `packs/router-heuristic` to pick a platform, then calls `assign` here |
| Cross-platform handoff flow from PRD §Cross-Platform Context Transfer | `pack_context` → `unpack_context` → `assign`, as described in §5.4 |
| Platform-specific errors (`PLATFORM_UNAVAILABLE`, `HANDOFF_TIMEOUT`, etc.) | UMAS maps `CapabilityMissing` → route to another platform; `AssignmentWriteFailed` → P1 escalation; `ChecksumMismatch` → P1 escalation with the pack retained for inspection |
| IBM Bob: gateway provider or agent platform? | UMAS registers `ibm-bob` as an adapter here **and** configures it as a provider in `llm-gateway` when Bob exposes a chat-completion endpoint. The two registrations are independent; the library does not couple them. |

## 10. Source Material and Deviations

Extracted from `unified-multi-agent-system-prd.md` §Multi-Agent Platform Support and `TECHNICAL-DESIGN-SPEC.md` §1.3 (LLM Provider Integration).

| Deviation | Why |
|-----------|-----|
| Library covers harness adapters only, not LLM providers | The PRD conflates the two. LLM calls belong in `llm-gateway`; work assignment and completion signals belong here. Mixing them would make both components harder to test and replace independently |
| `assign` writes files; it does not call APIs or spawn processes | The PRD's `spawn_agent(task, config) -> Agent` assumes the adapter controls the agent's lifecycle. In practice Claude Code, Bob, and Copilot are independent tools; UMAS can only present work to them, not start them |
| `read_signal` is non-blocking | The PRD implies the adapter manages the agent's completion event. A blocking read would couple UMAS's scheduling loop to the harness's timing |
| Context pack has a checksum | The PRD's `context_transfer` block mentions an integrity check but does not specify it; `SHA-256` of the canonical JSON is unambiguous |
| `completion_signal: none` for Copilot | The PRD marks `supports_hooks = False` for Copilot but provides no alternative signal mechanism. File mtime polling is the pragmatic fallback |
| Plugin registry replaces hard-coded class hierarchy | The PRD uses Python subclasses. A registry avoids language coupling and lets callers override built-ins without forking |

## 11. Open Questions

1. **IBM Bob as both harness and LLM provider:** When Bob is used as a coding harness (it runs agent sessions), its adapter belongs here. When Bob's chat-completion endpoint is called directly (for example by the Coordinator's planning step), it belongs in `llm-gateway`. The consuming application must register Bob in both, with separate credentials. Is this the agreed split, or should there be a single "Bob integration" component that wraps both? This should be decided before Phase 2.

2. **Completion signal reliability for `commit-message`:** A harness that crashes after committing but before the UMAS poller runs will produce a valid signal. A harness that commits without the signal pattern in the message will be silently ignored. Should there be a timeout after which `read_signal` returns a synthetic `abandoned` signal?

3. **IDE-native platforms (Copilot, Cursor):** These platforms are controlled by a developer's IDE, not by UMAS. Is UMAS's role limited to writing a task file and hoping the developer picks it up, or should there be an explicit "human in the loop" step that routes IDE-platform tasks through the escalation channel?

4. **Capability matching strictness:** Should `assign` hard-fail on `CapabilityMissing`, or warn and proceed? A security-review task sent to Copilot (which lacks `security-review`) will not produce a security review, but it will produce code. The current spec fails hard; is that the right default?

---

## 12. Reference Implementation (Source Code)

> Non-normative. Code moved verbatim from the original UMAS technical design. It illustrates one approach and uses UMAS names. Sections 1–11 are authoritative. Excluded from the independence rules in [libs/README.md](README.md).

### 12.1 Adapter base class and platform implementations (Python)

Source: `unified-multi-agent-system-prd.md` §Platform-Specific Adapters

```python
class CodingAgentAdapter:
    """Base adapter interface for coding agent platforms"""

    def authenticate(self, credentials: dict) -> bool:
        pass

    def spawn_agent(self, task: Task, config: dict) -> Agent:
        pass

    def transfer_context(self, from_agent: Agent, to_agent: Agent) -> bool:
        pass

    def get_capabilities(self) -> list[str]:
        pass

    def supports_hooks(self) -> bool:
        pass


class ClaudeCodeAdapter(CodingAgentAdapter):
    capabilities = [
        "code-generation", "architecture-design",
        "code-review", "refactoring", "documentation",
    ]
    supports_hooks = True
    context_format = "markdown"


class IBMBobAdapter(CodingAgentAdapter):
    capabilities = [
        "code-generation", "security-review",
        "compliance-check", "enterprise-integration",
    ]
    supports_hooks = True
    context_format = "json"
    enterprise_features = ["audit-logging", "rbac", "secret-management"]


class CopilotAdapter(CodingAgentAdapter):
    capabilities = ["code-completion", "code-generation", "inline-suggestions"]
    supports_hooks = False
    context_format = "file-based"
```
