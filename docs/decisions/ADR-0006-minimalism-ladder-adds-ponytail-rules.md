# ADR-0006: minimalism-ladder adds four ponytail rules and ships as a portable skill

> **Status:** Decided (owner instruction 2026-11-09, taking the recommended option for Q1 to Q4; veto in one reply) · **Task file:** [tasks-minimalism-ladder-2026-11-09.md](../tasks-minimalism-ladder-2026-11-09.md) · **Assessment:** [round 1, rejected, 2 blockers](../assessments/caller-assessment-minimalism-ladder-2026-11-09.md)

## Decision

Keep `packs/minimalism-ladder`. Add four rules adapted from ponytail (MIT, DietrichGebert, commit `96608e0`): scope, bug-fix callers, tests for new logic, never cut. Credit ponytail in `PACK.md` with the full MIT text.

| Q | Choice | Effect |
|---|--------|--------|
| Q1 | Keep the source spec whole; the portable set is a named list of files | `PACK.md`, `config.yaml`, `schema/`, `fixtures/*.yaml`, `scripts/`, `tests/`. The spec, `RESULTS.md` and `SKILL-ASSESSMENT.md` stay in this repo as UMAS-side records. Spec §9 and §12 are not removed, so no contract is lost |
| Q2 | The ladder states its own test definition | Aligned in wording with test-policy's risky-logic kinds. When a test policy is in use, it decides whether a missing test blocks |
| Q3 | Full MIT text in `PACK.md` | Every installed copy carries it. No `NOTICE.md` |
| Q4 | `pack_version` stays `0.1.0` | Bump to `0.2.0` only after a fixture run against the new rules is recorded |

## Consequences

- The four rules have no record field. The scope list goes in the answer text; the test is named in `notes`. The record cannot prove the rules ran.
- Fixtures F9 to F12 are written, not run. No independent judge exists (D3).
