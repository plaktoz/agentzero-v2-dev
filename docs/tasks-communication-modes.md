# Tasks: communication-modes

Status: **parked (KIV)**, recorded 2026-10-27. No spec, pack or config file has been changed for this work yet.

## Decision (2026-10-27)

Owner chose the recommendation: remove the reader gate from the pack.

- **Removed from the pack:** the routing table (spec 5.5), `routing.yaml`, the context flag in the input (4.1), the routing config (6), the anti-slop link, and `schema/message.json`.
- **Kept:** the compact and plain registers, the intensity levels, the protected-content rule (5.4), and the reply shape and full-sentence exception from the caller-facing design.
- **Added to the rule text:** "Write plain for anything a person reads."
- **Caller's job:** decide per channel whether an agent's prompt gets the rule block. One sentence in the caller's docs, not a requirement in the pack.
- **Fixture:** a message addressed to a human must come out plain. It runs in the measurement step.

**Why:** the gate was the only thing that protected human-facing text, and it also caused blockers 1, 2 and 4 in `packs/communication-modes/SKILL-ASSESSMENT.md`. Those blockers fall away with the routing table.

**Accepted risks:**
- A fresh worker with no history can receive compact text it cannot read. The pack no longer stops this. Impact: a misread fact. Likelihood: not measured.
- The human line depends on the model. It is a request, not a guarantee. Status: unverified until the fixture runs.

## Tasks

Each task has its acceptance criterion. Tick a task only when its criterion is met.

- [ ] **T1. Revise `packs/communication-modes/communication-modes-spec.md`.** Remove the parts listed above and add the human line. Criterion: the spec has no routing table, `routing.yaml` reference, context flag or anti-slop link, and section 9 lists consumers as a plain list.
- [ ] **T2. Run the caller assessment gate (CLAUDE.md 2a)** on the revised spec. Criterion: verdict recorded here, blocker count recorded, report in `docs/assessments/`.
- [ ] **T3. Measurement run (spec step 4).** Ten real messages, four conditions (no rule, "Be concise.", level 1, level 2), round-trip test, and the human-line fixture. Criterion: real savings and comprehension numbers replace the unverified 5.3 figures, and the human fixture passes. If it fails, the human line is not enough and the gate question reopens.
- [ ] **T4. Update `packs/README.md`** (row for communication-modes, line 17) and **replace `SKILL-ASSESSMENT.md`**. Criterion: both match the revised spec.

## Open

- Revisit the gate if the T3 human fixture fails.
- Revisit the fresh-worker risk if fresh workers turn out to be common in practice.
