# Tasks: merge the modularisation assessment into the technical design spec (2026-10-25)

Owner decisions (2026-10-25): put the assessment into `umas/TECHNICAL-DESIGN-SPEC.md` as **Appendix A** (A.1 to A.9, numbering follows the old sections 1 to 9); **delete** `umas/modularisation-assessment.md` afterwards, so there is one copy; fix the stale items; apply the answers to the open decisions below.

Nothing here is committed. Commit only when asked. The old file's full text stays in git history.

## Decisions applied

| # | Decision | Answer | Recorded in |
|---|----------|--------|-------------|
| Q1 | Do agents act with the intersection of their role and the requesting user's permissions? | **Not answered yet.** Recommendation A (intersection) stays in the text as "To confirm". Example given in chat | Appendix A.5.9 |
| Q2 | Security finding escalation goes to | Project Owner of the project, Admin if none | Appendix A.5.9, A.5.4.1 |
| Q3 | Two-person rule | Confirmed. Approver differs from requester. Self-approval only through the `merge:approve_own` ACL grant. Keep it simple | Appendix A.5.9 |
| Q4 | `llm-gateway`: adopt, wrap or build | **Wrap the provider SDKs** (no LiteLLM). Replaces "adopt first" | ADR-0003, `libs/llm-gateway/README.md`, `libs/README.md`, Appendix A |
| Q5 | `structured-output-parser` | Pydantic at the boundaries, no separate parser | ADR-0004, Appendix A.2.1 |
| Q6 | Dashboard in Phase 2? | Decide together with the phase re-cost | Appendix A.7 |
| Q7 | Event log at 20 to 30 writers | Keep files; SQLite WAL when the writer count is reached | Appendix A.4.4 |

## Tasks

- [x] **M1. Fix stale items in the assessment text before merging.** Done in the appendix text: `antigravity` replaced by ADR-0002 wording, `libs/kc-axi.md` replaced by `libs/kc-axi/README.md`, FastAPI marked decided, OpenTelemetry item marked done, model-ID row updated. Verified by grep of Appendix A: the remaining hits for "adopt first" are intentional history lines (A.2.1 llm-gateway row, A.9).
- [x] **M2. Apply decisions Q2 to Q7 to the appendix text.** Done. A.5.9 rows 4 and 7 read "Decided"; row 5 (Q1) still "To confirm"; A.6 llm-gateway row, structured-output row and event-log row show the decisions. Verified by reading.
- [x] **M3. ADR-0003 and ADR-0004.** Written by subagent; both files exist in `docs/decisions/`; the llm-gateway README, libs README and Appendix A link to ADR-0003. Verified by `ls` and grep.
- [x] **M4. `libs/llm-gateway/README.md` and `libs/README.md` for Q4.** Done by subagent. Section 6 is "Acceptance checklist for the wrapper" with the 10 criteria kept. Verified by reading section 6 (heading at line 107, table at 111).
- [x] **M5. Pinned model IDs.** The subagent stopped because `claude-default` is not defined in the llm-gateway README (its alias is `default`). Decision: use `default`. Replaced in `libs/agent-session/README.md` (1), `packs/specialist-agents/specialist-agents-spec.md` (5) and `packs/two-axis-review/two-axis-review-spec.md` (1). Verified by grep: the ID remains only in llm-gateway quotations and task files. Note: the main spec uses `claude-default`, the gateway README uses `default`; align them when the alias table is written.
- [x] **M6. Appendix A appended to `umas/TECHNICAL-DESIGN-SPEC.md`.** A.1 to A.9 at the end of the spec, TOC entry added, stack note, auth line and open questions 1, 3 and 6 repointed. Verified by an anchor check: no broken in-document anchor.
- [x] **M7. Inbound references repointed** in 13 files with a per-reference section map. Verified by grep: no `modularisation-assessment` outside task-list history.
- [x] **M8. `umas/modularisation-assessment.md` deleted** with `/bin/rm -f`. Verified by `ls umas/`. The link and anchor check over all markdown files finds 5 broken anchors, all `#cli-conventions-axi` in `libs/{merge-queue,event-log,task-queue,budget-meter,test-adapters}/README.md`, which also fail at HEAD (not caused by this work, not fixed).
- [x] **M9. READMEs in sync.** `libs/README.md` and `packs/README.md` checked by grep for adopt-first, LiteLLM, antigravity, Rust and Go wording. Also fixed 23 `libs/README.md` links that used `../<lib>/` instead of `./<lib>/` (broken at HEAD).
- [x] **M10. Pack specs renamed** `packs/<name>/README.md` to `packs/<name>/<name>-spec.md` (9 packs), 77 links in 16 files repointed, 9 header links fixed (`./README.md` to `../README.md`), 5 non-normative sentences fixed, layout block in `packs/README.md` and 3 lines in `CLAUDE.md` updated. Verified by the link check (no pack-spec link broken).

## State log

- 2026-10-25: list written. No task started.
- 2026-10-25: M3 and M4 done by subagent (ADR-0003, ADR-0004, llm-gateway README, libs README); verification pending. M5 blocked: `claude-default` is not in `libs/llm-gateway/README.md` section 3.2 (alias there is `default`). Decision: use `default` in the three pack and lib examples.
- 2026-10-25: M10 added (pack specs renamed to `<name>-spec.md`). Next: do M10 first (links change), then M6 to M9.
- 2026-10-25: M1 to M10 done. Open: Q1 (intersection or full permission). Next: split the spec into module specs (requirements to agree first).
