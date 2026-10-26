Verdict: REJECTED

Spec: `umas/modules/interfaces/interfaces-spec.md` (603 lines: `umas` CLI, REST API `/api/v1`, 31 Open items, AXI section).
Callers checked: orchestration, verification, monitoring, access-control, budget-and-models, context-persistence, agent-execution, exception-flows, and the AXI conventions in `libs/README.md`. Decisions D1 to D48 and C1 to C4 are the owner's and are not restated as gaps. Where a caller depends on an undecided one, the row says so. Links were not checked exhaustively.

## Findings

| # | Gap | Section | What the caller needs | Severity |
|---|-----|---------|-----------------------|----------|
| 1 | Permission names are all "proposed" and conflict with callers. `budget:write` vs D21 `budget:set`. Handoff and resume map to `agent:spawn`, but D21 names `agent:handoff` and `agent:resume`. `worktree:write` vs context-persistence names. Reconcile maps to `agent:stop`, but monitoring uses nudge and restart. `work-bundle approve` has none. | 3.2, 5, Open 15, 16 | One final name per route, matching the access-control seed | Blocker |
| 2 | The human gates have no entry point: grilling `answer` and `confirm` (D25 recommended, not answered), `work-bundle cancel`, escalation resolve, merge approve, review override. `work-bundle approve` is in the CLI but has no REST route. | 3.1, 3.2 | A command, route, input and permission for each (orchestration Open 11; verification O7, O14) | Blocker |
| 3 | The error contract is missing. Only `PERMISSION_DENIED` is typed, and it is not in the error-classifier catalog. There is no REST status mapping or error body. D8 `audit_unavailable` is absent. | 8, 3.1 | Code list, HTTP status per code, JSON error body, exit code per code | Blocker |
| 4 | Identity contradicts D11. The flow says the CLI on loopback uses the local OS user, but D9 and D11 require OIDC on every call. The no-argument view is "no network call", so it cannot check a permission. | 2, 3.3 | One identity path for CLI, REST and the read-only view | Blocker |
| 5 | Transport is open (Open 1). Monitoring needs daemon methods (its Open 21), and the 30 s daemon timeout and 300 s CLI timeout are not tied to any operation. | 2.2, Open 1 | The transport and the method list | Blocker |
| 6 | No mutating command behaviour when the daemon or Keycloak is down (Open 22). `health-check`, `stop-all` and diagnosis commands cannot run when they are needed most. | 8, Open 22 | Which commands work with no daemon or no token | High |
| 7 | Long operations (`stop-all`, `update --now`, `worktrees recover`, `worktrees clean`, `cleanup`) have no async model, progress or resume inside 300 s. | 3.1, 3.2 | Sync or job id; behaviour on timeout | High |
| 8 | Twelve mutations have no repeat rule (Open 9). Open 21 gives no key, so `agents spawn` and `request` duplicate on retry. | Open 9, 21 | A rule per command; retry safety for creates | High |
| 9 | Result types list field names without types or `schema_version` values (Open 3). TOON vs key-value is unresolved (Open 4). | 4, Open 3, 4 | Typed schemas and one encoding, so golden files and clients can be written | High |
| 10 | `requested_by` (D10) is missing from request inputs and result types. The `work-bundles` create body is undefined. | 3.2, 4 | Field on request, work item and result | High |
| 11 | Audit order and scope. The flow writes the audit event after the call; access-control proposes before. Open 8 (audit on allowed reads) clashes with the no-write view. | 2, Open 8 | Order, event type name, read-audit rule | High |
| 12 | Budget `define` takes `--budget <tokens>`. Budget-and-models needs unit, window and thresholds (D14 chose wall-clock). | 3.2 | Request shape and `budget:set` mapping | High |
| 13 | Event names differ from senders: `escalate` vs `session_escalated`, `handoff_request` vs `handoff_initiated` (D32 pending). `boot_recovery` payload is undefined (exception-flows Open 5). | 6 | One name and payload per event | Medium |
| 14 | `agent_sessions` has no `hook_path` (Open 28). `handoff` has no successor argument (Open 23). `recover` return type is two names (Open 24). | Open 23, 24, 28 | Matching signatures | Medium |
| 15 | `health-check` exit codes for `machine_paused` and `auth_expired` are unclear. Open 14 asks whether it writes, but watchdog `check_once` does not. | Open 14 | Exit code per status; write or read-only | Medium |
| 16 | Missing read routes: hooks, events, monitor and node state, `project switch` (Open 11), `umas access show` and service principals (C3 pending). | 3.2 | Route, permission and result type each | Medium |
| 17 | `init --project` also creates the merge-queue worktree (verification O19) and has no REST route (Open 6). | Open 6 | Local-only or routed, stated | Medium |
| 18 | Two config file names (`umas.config.yaml`, `.umas/config.yaml`) are not reconciled (verification O21, exception-flows Open 13). | 4 | One path and precedence | Medium |
| 19 | The `.lock` (5 s wait) outcome for a REST write is not stated: status code, retry hint. | 8 | Status and `help:` line | Medium |
| 20 | Windows is not covered: the lock, the named pipe, socket permissions, CRLF. | 2.2 | Per-OS behaviour, or "verified by reading" marks | Medium |
| 21 | Header says "Uses: none" and "Depends on: none", but sections 6 and 7 list many. | Header | Consistent header | Low |
| 22 | Open 26 (intersection rule) is stale. D1 decided it. | Open 26 | Remove or close | Low |
| 23 | `--fields` valid names are not listed. `watch` has no `--json` stream format. | 3.1 | Name list; line format | Low |

Counts: Blocker 5, High 7, Medium 8, Low 3. Total 23.

## Open items a caller cannot start without

Open 1, 3, 4, 6, 8, 9, 14, 15, 16, 21, 22, 23, 24, 28. Open 11 (orchestration, verification) and open points on C3 (access-control) also block those callers.

## Devil's advocate

Nearly every cell in the route table says "proposed". Each caller has already proposed different permission names, so the first merge of the access-control seed renames half the routes and breaks every test written against them. Under D9 and D11 each command makes a Keycloak call, so one Keycloak outage freezes every command, including `health-check` and `stop-all`. The operator who needs them has nothing to run, and the spec has no local fallback. The human gates are the points where the system waits for a person: grilling confirm, bundle approve, escalation resolve, merge approval. None has a complete command, route and permission, so a P1 escalation parks a bundle in `ESCALATED` and the only way out is editing the database. A CLI timeout during `update --now` leaves the machine half-updated with no job id to resume, and a retry may run it twice. Result types name fields without types, so the dashboard and golden-file tests cannot be built, and errors are one typed code, so no client can tell a retryable failure from a permanent one.

## Decisions the owner must make

None of these appears in D1 to D48 or C1 to C4. Decisions 1 and 3 relate to spec Open 22 and Open 21, which are the spec's own recommendations, not owner decisions.

**1. Break-glass access when Keycloak or the daemon is down.**
Context: D9 (A) and D11 (A) make every call depend on Keycloak. The D9 note leaves the outage rule to the access-control revision, but the entry points need a list of commands.
(a) No exceptions: every command fails during an outage. Consequence: simple and consistent, but the operator cannot diagnose or stop anything.
(b) A fixed local allow-list (`health-check`, `stop-all`, `version`, read-only status) that runs as a local admin identity from the OS user, audited when the audit store returns. Consequence: a second path to secure and test, which D11 chose to avoid.
Assessment: (a) makes the outage the worst case for an operator. (b) is narrow and fixed.
Recommendation: (b), with the list fixed in this spec and every use logged on recovery.

**2. Long-running operations.**
(a) Keep them synchronous inside the 300 s CLI timeout. Consequence: simple; a timeout leaves state unknown.
(b) Return a job id at once and add `umas job <id>` (status, resume). Consequence: a new resource and table, and clients must poll.
Assessment: only five commands are long, but each one mutates the machine.
Recommendation: (b) for `update --now`, `stop-all`, `worktrees recover` and `cleanup`. Keep the rest synchronous.

**3. Retry safety for create commands.**
(a) State-based rule only (`already ...`, Open 9). Consequence: `agents spawn` and `request` still duplicate on a timeout retry.
(b) An optional `Idempotency-Key` header and `--key` flag on creates, stored with the result for a fixed time. Consequence: one small table and a TTL.
Assessment: (a) cannot cover creates, which are the commands most likely to be retried after a timeout.
Recommendation: (b) for creates only. Use (a) for the other mutations.

**4. Source of truth for result types.**
(a) Prose tables in this spec. Consequence: they drift from the code, as they already have in finding 9.
(b) Pydantic models in code, with the OpenAPI document and the tables generated from them (matches Open 2). Consequence: the spec points to the models and does not copy them, so the models must exist before the spec is accepted.
Assessment: Python is the backend language and ADR-0004 already uses Pydantic v2, so no new tool is added.
Recommendation: (b).
