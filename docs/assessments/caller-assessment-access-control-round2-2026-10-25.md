# Caller assessment, access-control spec, round 2

Date: 2026-10-25
Spec: `umas/modules/access-control/access-control-spec.md` (revised)
Round 1: `docs/assessments/caller-assessment-access-control-2026-10-25.md` (REJECTED)

## Verdict

**ACCEPTED WITH OPEN ITEMS.**

Every round-1 blocker is in the spec text or tied to an owner decision. Three new defects (N1, N2, N5) need spec fixes before the steps they touch are built.

## Gap table

| # | Status | Evidence (spec text) |
|---|--------|----------------------|
| 1 | CLOSED | Step 7 (line 58), 5.4: `requester_id`, reason `two_person_rule` (D10 A). Callers do not send it yet (N12). |
| 2 | CLOSED | Section 3.2 closed reason list with HTTP, exit and code. `unknown_permission` is 500, exit 2. |
| 3 | CLOSED-PENDING-OWNER (item 7, no decision id) | Section 4 and item 7 give proposed values only. |
| 4 | CLOSED | Step 8 (line 59), Figure 1 audit branch, refusal record (D8 A). |
| 5 | CLOSED-PENDING-OWNER (item 3; D28, D36, D41, D47) | Section 5.1 seed list. Only D21 names are decided. |
| 6 | CLOSED-PENDING-OWNER (items 2, 13) | Section 5.6 (lines 332 to 343). Step 5 waits on item 2. |
| 7 | CLOSED | Sections 1 and 6: non-API callers use the same `check`. |
| 8 | CLOSED | Section 5.3 service principals (C3 B). Mapping gaps in N6. |
| 9 | CLOSED | Step 7 intersection (D1 A). `acting_for_id` from the credential row (step 6). |
| 10 | CLOSED (caveat) | `context` input, limit schema, section 3.3 (line 192). `max_role` rank undefined (N4). |
| 11 | CLOSED-PENDING-OWNER (items 9, 10) | Section 3.2 severity and escalate columns are proposed. `no_binding` row contradicts itself (N1). |
| 12 | CLOSED | D11 A in the spec. Main spec still says loopback (inconsistency A). |
| 13 | CLOSED (items 8, 17 open) | AXI section: `AuthStatus`, `AccessList`, exit codes, `TOKEN_CACHE_UNREADABLE`. |
| 14 | CLOSED | A.5.9 Q7 filled (D7). Monitoring Open 13 and verification O17 still say "awaits confirmation". |
| 15 | CLOSED | Figure 1 has the audit branch. All relative links and anchors resolve. |
| 16 | CLOSED-PENDING-OWNER (no decision id) | Cached signing keys removed (D9 A). Audit-before-handler and other proposed claims unconfirmed. |

## New gaps

Fix before implementation:

- **N1.** `no_binding` row says Escalate "No", but its effect says orchestration moves the bundle to `ESCALATED`. Orchestration moves only on an `escalate` event.
- **N2.** `gate:approve` covers ADR acceptance, but `requester_id` comes from a work item's `requested_by`. ADR acceptance has no work item, so fail-closed denies every such approval. The spec needs a rule for checks with no requester.
- **N5.** Watchdog holds `system:restart` only. `agent:restart` is held by Coordinator, so D15 a (watchdog restarts Worker) has no permission. Ties to D15/D38.

Other:

- **N3.** No permission name for `GET /api/v1/me`, `umas auth login` or `umas auth status`. Step 3 fails a route with no name at startup.
- **N4.** `max_role` limit uses "rank"; no role order is defined.
- **N6.** Service-token mapping does not name the claim (`azp` or `client_id`). `external_id` for service principals is unspecified.
- **N7.** Step 1 lists `iss`, `aud`, signature, algorithm and skew checks, which are local JWT checks. D9 A is per-request introspection. Unclear whether local validation also runs.
- **N8.** Precedence between `store_unavailable` and `audit_unavailable` is unspecified. The refusal record's destination during a store outage is not stated.
- **N9.** Step 8 records a decision plus an outcome for every request. Interfaces Open 8 proposes no events for allowed reads. Audit volume is not addressed.
- **N10.** Section 5.6 precedes 5.5 in heading order.
- **N11.** Interfaces still uses `budget:write` and `worktree:write`, which are not in the seed list.
- **N12.** Verification and orchestration carry no `requested_by` or `requester_id`. The two-person rule cannot run until they do.
- **N13.** Exit 2 means "dependency unavailable" here; `libs/README.md` says usage error. Marked proposed.
- **N14.** Section 9 items 2, 4, 6, 7, 8, 12, 13, 14, 15 and 17 have no matching question in the decisions file.

## Verified inconsistencies

- **A. Loopback trust (A.5.2, A.5.8).** Confirmed. `umas/TECHNICAL-DESIGN-SPEC.md` lines 1521 and 1697; `interfaces-spec.md` lines 426 and 509. D11 A says OIDC on every call.
- **B. A.5.9 Q4.** Confirmed. Line 1711 has 3 cells under a 4-column header. Lines 1500 and 1737 still say Q5 and Q7 "await confirmation" though their rows say Decided.
- **C. A.5.5 Monitor stop.** Confirmed. Line 1647 gives the Monitor "restart, nudge"; line 1653 says Monitors can stop another agent. Open: spec item 5 and D41.
- **D. A.5.6 role-change timing vs D9.** Confirmed stale. Line 1679 relies on short token expiry; under D9 A the check runs on every request.
- **E. D15 vs D38.** Confirmed open owner conflict: `docs/decisions-pending-2026-10-25.md` lines 238 and 585.

## Owner decisions still blocking

- Item 1: break-glass (I-1).
- Item 2: grant storage and authority (no decision id). Blocks gap 6.
- Item 3: seed list (D28, D36, D41, D47; D23 to D48 batch).
- Item 4: own capabilities (no decision id).
- Item 5: Monitor and Coordinator write authority (D41).
- Item 6: agent credential path (no decision id).
- Item 7: token settings and image pin (no decision id). Blocks gap 3.
- Item 8: token cache format (no decision id).
- Item 9: security routing scope.
- Item 10: P0 recipient (D26, D40).
- Item 11: credential lifetime, revocation, boot check (E5).
- Item 12: loopback and TLS (no decision id).
- Item 13: Phase 1 binding administration (no decision id).
- Item 14: dashboard poller and CI runner roles (no decision id).
- Item 15: audit hash chain (no decision id).
- Item 17: `auth status` network call (no decision id).
- D15 vs D38 conflict.

Item 16 is a spec revision, not an owner decision. "No decision id" items need an owner answer before acceptance.
