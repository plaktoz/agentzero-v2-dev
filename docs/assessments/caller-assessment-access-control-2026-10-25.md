**Verdict: REJECTED** (round 1 of 2)

Spec: `umas/modules/access-control/access-control-spec.md`

Callers assessed: interfaces (API and CLI), verification (merge approval), monitoring (denials and security escalation), orchestration (agent credentials).

## Findings

| # | Gap | Section | What the caller needs | Severity |
|---|-----|---------|-----------------------|----------|
| 1 | Two-person rule cannot be run. `check` has no requester input, and no test says what makes an approval invalid. | 3, 5 | `requester_id` input. Rule: approval is invalid when requester equals approver and no `merge:approve_own` binding holds in scope. A named deny reason. | Blocker |
| 2 | Deny reason values are not enumerated. No status code for the CLI or dashboard. Outcome for an unknown permission name is undefined. | 3, 8 | Closed reason list. Status code. Defined result for an unknown name. | Blocker |
| 3 | Token validation values are unset: issuer, audience, keys, algorithms, clock skew, lifespan. Keycloak-outage behaviour is open. | 4, 8; items 7 to 9 | Values, or the rule that applies while they are missing. | Blocker |
| 4 | Audit write failure is open. Token-refused requests write no record, although A.5.6 step 5 requires one for every decision. Handler outcome is not recorded. | 2, 8; item 12 | Refuse-or-allow rule. Record for every refusal. Outcome event after the handler. | Blocker |
| 5 | Permission seed list is incomplete. Only five names exist (`agent:spawn`, `merge:approve`, `merge:approve_own`, `config:write`, `audit:read`). Stop or pause, manage users, create or delete project, submit, budget, P0 acknowledge, watchdog reset, restart and nudge have none. | 5 | Full seed list. Interfaces cannot declare routes without it. | Blocker |
| 6 | Phase 1 bootstrap is unset: seed step, first principal mapped to Keycloak `sub`, storage of the `merge:approve_own` grant. No binding API (item 13). | 4, 9; items 2, 13 | Seed procedure and grant storage. | Blocker |
| 7 | Enforcement for non-API callers is undefined. Only API middleware is named, but the Coordinator, Merge Queue Processor and Watchdog are plain processes. | 2, 3 | Call path per caller, or a rule that sandbox and branch protection apply. | High |
| 8 | Service principals (`kind = service`) are absent from the flow. Step 4 covers only users and agents. | 2, steps 1 and 4 | Credential type and lookup for Watchdog, Merge Queue Processor and the dashboard poller. | High |
| 9 | Q1 is built on but undecided. Step 7 and verification apply the intersection without saying so. The source of `acting_for_id` is unset. | 2 step 7; 3; item 1 | State the answer the check implements, marked pending confirmation. Source of `acting_for_id`. | High |
| 10 | No `context` input on `check`, so the `limit` in `role_permission` cannot be evaluated. Limit format is unset. | 3, 4 | Limit schema. `context` input. | High |
| 11 | Denial next step is unset: escalate or not, severity, recipient, and the agent's orchestration state. | 3, 8 | Rule per reason. | High |
| 12 | Phase 1 sign-in path is open (OIDC or loopback trust). | 2; item 5 | One path. | High |
| 13 | `umas auth` output and exit codes are undefined. All ten AXI principles are "Not met". | AXI section | Output shape, exit codes, error codes. | High |
| 14 | Security escalation routing conflicts. A.5.9 Q7 says "Decided" with a blank answer. A.5.4.1 says it awaits confirmation. | 6; item 16 | Owner confirms the routing and fills the answer. | Medium |
| 15 | Figure 1 omits the audit-failure branch. Links to `interfaces-spec.md` and `exception-flows-spec.md` do not resolve (those files do not exist). | Figure 1; 6, 8 | Add the branch. Correct or create the targets. | Medium |
| 16 | Proposed claims callers build on: audit before handler, `PERMISSION_DENIED`, deny on missing route permission, deny when store is locked, cached signing keys. | 2, 8 | Confirm each, or mark it a decision. | Medium |

Summary: 6 blockers, 7 high, 3 medium.

Buildable now: the kc-axi parameters (section 4), the audit field list (section 3) and the error record format (error-classifier section 3.3).

## Devil's advocate

The strongest case against this design: its central claim, that no approval happens without a permission check and a two-person test, cannot be run. The check has no requester input, `requested_by` does not exist, and the Q1 answer is unconfirmed. Enforcement sits only in HTTP middleware, while merges and agent actions run in plain processes. So an approver could pass the check on their own change, refused requests could leave no trace, and a caller could not tell whether a failed audit write means the action ran.

## Decisions for the owner

1. **Q1, intersection or full permission (A.5.9 Q5).**
   - Option A: intersection. An agent acting for a user needs its role and the user's permission in the target scope.
   - Option B: the user's full permission.
   - Recommendation: A. Record it in step 7 as pending confirmation.
2. **Audit write failure.**
   - Option A: refuse the action and return `audit_unavailable`.
   - Option B: allow and queue the record.
   - Recommendation: A, as kc-axi section 7 does.
3. **Token check under a Keycloak outage, and token lifespan.**
   - Option A: a Keycloak call on every request.
   - Option B: a local check with cached keys, refusing when no key is cached.
   - Recommendation: B. The owner sets issuer, audience and lifespan in the realm file (items 8 and 9).
4. **Where the two-person comparison runs.**
   - Option A: `check` takes `requester_id` and returns a `two_person_rule` reason.
   - Option B: verification compares before it calls `check`.
   - Recommendation: A, with `requested_by` on work items (item 4).
5. **Phase 1 sign-in.**
   - Option A: OIDC on every call.
   - Option B: loopback trust for single-user mode.
   - Recommendation: A (item 5).
