# Brief: extract one module spec from the UMAS technical design spec

## Goal
The main spec `umas/TECHNICAL-DESIGN-SPEC.md` is being split into nine module specs under `umas/modules/<name>/<name>-spec.md`. Your job is ONE module: create its spec file by moving text out of the frozen snapshot, not by writing new design.

## Source (read only)
`/tmp/spec-split/TECHNICAL-DESIGN-SPEC.snapshot.md` — a frozen copy of the main spec. Do NOT edit `umas/TECHNICAL-DESIGN-SPEC.md` or anything outside your own module folder. Other agents are writing the other modules in parallel.

## What to do
1. Create the folder and file named in your assignment (`umas/modules/<name>/<name>-spec.md`). Use the Write tool.
2. Copy the sections named in your assignment from the snapshot, **verbatim** (same wording, same tables, same code). Do not rewrite prose, do not reword decisions, do not drop content. Moving is the job.
3. Put this header at the top, filled in:
   ```
   # <Module title> — module spec

   > Part of the UMAS technical design. Main spec: [TECHNICAL-DESIGN-SPEC.md](../../TECHNICAL-DESIGN-SPEC.md) · Module map: [module map](../../TECHNICAL-DESIGN-SPEC.md#5-component-design)
   > **Owns:** <one line: what this module is responsible for>
   > **Uses:** <list of libs/packs it depends on, as relative links>
   > **Depends on modules:** <list of other module specs, as relative links>
   ```
   Keep the "Owns / Uses / Depends on" lines short. Only list dependencies that the moved text actually shows.
4. Keep the original section numbers as headings where the text keeps its own structure. If the module takes "5.2 Orchestration System", its top heading may be `## 5.2 Orchestration System` so that citations stay traceable. Subsections keep their numbers (`### 5.2.1` etc. if they exist, otherwise the original `####` headings).
5. Fix references **inside your moved text**:
   - A reference to a section that is in YOUR module: leave it as it is, or make it a same-file anchor link.
   - A reference to a section that belongs to ANOTHER module or to the main spec: change it to a link to that section's new home. The owner map is below. Use relative paths from your file (for example `../orchestration/orchestration-spec.md`) and, where the target is a heading, add the anchor.
   - A reference to a library or pack: keep it, and make sure the path is right from your new location (`../../../libs/...`, `../../../packs/...`). Libs use `libs/<name>/README.md`, packs use `packs/<name>/<name>-spec.md`.
   - A reference to Appendix A: link to `../../TECHNICAL-DESIGN-SPEC.md#appendix-a-modularisation-stack-and-rbac-decisions` or the specific `#a5-...` anchor.
   - Do NOT change wording that just says "the spec" or "this spec" to something else.
6. Do NOT copy content that another module owns. If the moved text quotes another module's content, leave the quote and link to the owner.
7. Verify with a script before reporting:
   - Every relative link in your file resolves to an existing path (check the file path and, for `#anchor`, that a heading with that slug exists in the target file or in the snapshot's heading list for the main spec).
   - The count of `Source:`-style lines and tables in your extract matches the snapshot (report the numbers).
   Run the check with `python3 -I` (not `python`, not `python3` without `-I`). Use only the standard library.
8. Do not commit. Do not touch `docs/` or the other module folders.

## Owner map (where each section will live)
| Section in snapshot | New home |
|---|---|
| 1 Technology Stack | main spec (kept) |
| 2 System Architecture | main spec (kept) |
| 3 Reusable Components | main spec (kept) |
| 4 Data Model | main spec (kept, shared by modules) |
| 5.1 Context Persistence System | `umas/modules/context-persistence/context-persistence-spec.md` |
| 5.2 Orchestration System | `umas/modules/orchestration/orchestration-spec.md` |
| 5.3 Agent Execution System | `umas/modules/agent-execution/agent-execution-spec.md` |
| 5.4 Verification System | `umas/modules/verification/verification-spec.md` |
| 5.5 Monitoring System | `umas/modules/monitoring/monitoring-spec.md` |
| 5.6 Token Budget and Handoff | `umas/modules/budget-and-models/budget-and-models-spec.md` |
| 5.7 Model Policy | `umas/modules/budget-and-models/budget-and-models-spec.md` |
| 5.8 Scalability Roadmap | main spec (kept) |
| 5.9 CLI Design | `umas/modules/interfaces/interfaces-spec.md` |
| 6 Exception Flows (6.1 to 6.17) | `umas/modules/exception-flows/exception-flows-spec.md` |
| 7 API Specifications | `umas/modules/interfaces/interfaces-spec.md` |
| 8 Security Architecture | `umas/modules/access-control/access-control-spec.md` |
| 9 Performance and Scalability | main spec (kept) |
| 10 Testing Strategy | main spec (kept) |
| 11 Deployment Architecture | main spec (kept) |
| 12 Implementation Phases | main spec (kept) |
| 13 Key Metrics | main spec (kept) |
| 14 Open Questions | main spec (kept) |
| Appendix A (RBAC decisions A.5) | main spec (kept); access-control links to it |

## Known pre-existing issue
In the snapshot, `## State at pause` (around line 981) is an H2 inside section 6.17. If your module contains it, make it `####` so it sits under 6.17.

## Report back (short, under 200 words)
- The file path you created and its line count.
- The source line ranges you copied (start-end in the snapshot).
- The list of cross-module links you wrote (target file + anchor).
- The verification result: broken links found (should be none) and the anything you could not resolve.
- Anything in the snapshot that was ambiguous and what you chose.

## Part B: detailed design for your module (added after the first brief)

Part A (above) is the move: the existing text, verbatim. Part B is new content: the module is specified in detail, from what the snapshot and the libs already say. Write Part B as a separate section after the moved text, headed `## Detailed design`, with these sub-sections in this order. Use the ste-docs technical profile (short sentences, concrete nouns, no filler, no vague claims; state what is decided and what is open).

1. **Purpose and boundary** (2 to 4 lines): what the module does, what it does NOT do, and which module owns each neighbouring responsibility.
2. **Flow**: the main flow as numbered steps, then one Mermaid `sequenceDiagram` or `flowchart` of the same flow. Cover the happy path and the one or two failure paths the snapshot describes (use the section 6 exception flows where they apply).
3. **Interfaces**: the inputs and outputs. For each, a row: name, direction (in/out), type of carrier (CLI command, REST endpoint, file, event, callback, function call), payload shape (fields, with types), and the owner. Reuse the field names the snapshot already uses. Do not invent new ones unless you mark them "proposed".
4. **Parameters**: configuration keys and CLI flags the module reads. A table: name, type, default, where set (config file, env, flag), and what it changes. Take defaults from the snapshot. If the snapshot has no default, write `not set` and list it in Open.
5. **Capabilities**: a short list of what an agent or a human can do through this module, and the permission each one needs (refer to Appendix A.5 names: for example `merge:approve_own`). Keep permission names exactly as they are in the snapshot.
6. **Interaction with other modules**: a table with one row per neighbour: the other module, what this module sends or receives, the carrier, and whether it is synchronous or asynchronous. Link each neighbour's spec with a relative link.
7. **Libraries and packs used**: list the libs and packs this module depends on and say in one line what each one provides here. Link them.
8. **Failure handling**: the failure modes that belong to this module, pointing at section 6 items by name.
9. **Open**: anything the snapshot leaves undecided. Mark each as Open and say what decision it needs, with a recommendation. Do not resolve open items yourself.

Rules for Part B:
- Mark each claim as **from source** (it is in the snapshot or in a lib/pack README you read; cite the section) or **proposed** (your reading of how the pieces fit). Keep proposed content short and list it in Open if it needs an owner decision.
- Do not contradict the decisions in Appendix A (Python only, SDK-wrapping llm-gateway, Pydantic structured output, files as source of truth, two-person rule, Keycloak for sign-in).
- Read the libs and packs your module uses before you write their flow. Do not guess a lib's interface; quote its section 4 or its CLI.

### If your module has a CLI: AXI assessment
Only the interfaces module (`umas` CLI) and modules that expose commands need this. Add a sub-section `## AXI support` with:
- The commands in scope, as a table: command, purpose, the output it produces today (from the snapshot), and the `--json` contract if any.
- For each of the ten AXI principles in `libs/README.md` under "CLI Conventions (AXI)", one line: already met, partly met, or not met, with a short reason. Do not restate the principle.
- How the CLI should be built to support AXI, in order: (a) the `--json` contract first, (b) a single result type per command, (c) a default-view renderer over that type, (d) exit codes, (e) the no-argument view as the session-start state view, (f) golden-file tests for the default view. Keep it to what this CLI needs.
- Open points, referring to the open points at the end of the AXI section in `libs/README.md`.
- Do not declare the default view's TOON encoding settled. Refer to the open point.

### Report back (replaces the earlier short report)
- File path and line count.
- Part A: the source line ranges copied.
- Part B: the sections written, and the number of **Open** items you listed.
- Cross-module links written (target file + anchor).
- Verification: broken relative links (must be none) and any Mermaid block you could not validate by reading.
- Anything ambiguous and what you chose. Under 250 words.
