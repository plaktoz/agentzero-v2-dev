# Tasks: clean up agentzero-v2-dev after the minimalism-ladder port

The `minimalism-ladder` skill was ported to `agent-garage`. This file records the assessment of the source repo and the cleanup. Scope is `agentzero-v2-dev` only. Nothing is committed.

## Defaults taken

- No caller assessment gate (AGENTS.md 2a): the changes fix paths and status text and change no contract.
- The header template in `docs/brief-module-split-2026-10-25.md` is left as is.
- No `doctor.sh` fix is run: it changes the home folder and belongs to `agent-garage`.
- `compression_level` (minor m2) and the `handoff_request` payload (B6) are not touched. They wait for the decisions in `docs/tasks-token-usage-2026-11-09.md` (tasks 7 to 9).

## Tasks

- [x] **1. Assess.** Link and anchor check over every `.md` file (agent-ignore excluded) and a check of every backticked repo path. Result: no broken link. See "Findings".
- [x] **2. Fix stale file paths.** `libs/decision-artifacts/README.md:410`, `libs/hook-store/README.md:549` and `umas/TECHNICAL-DESIGN-SPEC.md:1757` now point at `<lib>/README.md`.
- [x] **3. Update the models-and-usage header** (`umas/modules/models-and-usage/models-and-usage-spec.md:4`): round 1 verdict and report link (minor m15).
- [-] **4. Fix the "broken links" at `docs/brief-module-split-2026-10-25.md:16`.** Not done: they are correct. The line is a code-block template copied into `umas/modules/<name>/`. `docs/tasks-token-usage-2026-11-09.md` task 10 is closed with this reason.
- [-] **5. Fix the 33 `doctor.sh` failures.** Not done: they are not in this repo. See "doctor.sh".
- [-] **6. Add the ponytail link.** Not needed: `packs/minimalism-ladder/PACK.md:170` and `agent-garage/skills/minimalism-ladder/SKILL.md:170` already link `https://github.com/DietrichGebert/ponytail` at commit `96608e0`. Nothing outside this repo was edited.
- [x] **7. Ported skill checks.** 17 tests pass in both `packs/minimalism-ladder` and `agent-garage/skills/minimalism-ladder`. `agent-garage/scripts/check-claims.sh`: 36 claims checked, 0 stale.

## Findings

### doctor.sh (33 failures, all in `agent-garage`, none in this repo)

`doctor.sh` runs only in `agent-garage`. It checks the skill folders on this machine.

| Count | Failure | Cause |
|---|---|---|
| 30 | `shadowed` (15 skills in each of `~/.claude/skills` and `~/.agents/skills`) | The folders link to the `claude-mods` copies, not to `agent-garage` |
| 2 | `minimalism-ladder` missing (both folders) | The ported skill is not installed |
| 1 | `ponytail` missing in `~/.agents/skills` | Not installed in the shared folder |

To clear them, run `agent-garage`'s installer (`scripts/install-skills.sh`, with `--agents` for the shared folder). It relinks the home folders, so the owner runs it.

### Remaining stale or open items (left with a reason)

| Item | Reason |
|---|---|
| `compression_level` in agent-session, context-persistence (line 151 contradicts agent-session) and models-and-usage | Removal is token-usage task 8, a design decision |
| `handoff_request` payload | Token-usage task 9, B6, models-and-usage Open 4 and 15 |
| `budget-meter` and `budget-and-models` hits | Removal notes, ADR references and dated records |
| `packs/minimalism-ladder/SKILL-ASSESSMENT.md:147` | A dated observation about the git state on 2026-10-25 |
| `scripts/*.py`, `docs/debt.md`, `docs/product`, `docs/specs`, `docs/agents/issue-tracker.md` in pack docs | Pack-relative paths, planned outputs, or paths in the target repo |
| O1 to O3, B1 to B7, M1 to M10 | Open design decisions, not cleanup |

## State log

- 2026-11-09: assessment done, owner approved the proposed changes, tasks 2 and 3 applied, tasks 4 to 6 closed as not needed. Changes are not committed.
