# Fixture provenance

## Source of the seed text

Fixture F3 and the examples in the spec's section 8 are seeded from `docs/ANTI-SLOP-EXAMPLES.md` in this repository. The file is titled "Anti-Slop Examples from PRDs" and records "Issue #184: CAVEMAN AND UNSLOP".

- **Author.** The file gives no author. Its only git history is this repository's commits: created in `961421b` ("initial", 2026-10-18), moved to `docs/` in `beb7fb3` (2026-10-20). The commit author is `tianhong`. The git log does not record a source outside this repository.
- **Licence.** None is stated in the file, and there is no `LICENSE` file at the repository root. The text is not licensed for reuse by this repository as far as the repository states. **No licence is claimed here.** Before this pack is published outside the repository, the owner must confirm the licence of this text, or replace the seed examples with text they wrote.
- **Owner confirmation (2026-10-25).** The owner approved using this text as the seed for F3 and publishing it. The confirmation was a one-word reply ("ok") to the question whether the owner wrote it or may use it. The file itself still states no licence.
- **Third-party content.** The examples quote PRD text (the "AFTER" examples name real metrics: 53%, 26%, 41%, 20-30+ agents). The file does not say where those PRDs or metrics came from. They are project facts, not verified here.

## Fixture mapping

| Fixture | Seed in `docs/ANTI-SLOP-EXAMPLES.md` | Change made for the fixture |
|---------|---------------------------------------|-----------------------------|
| F1 | Not a seed. Written from the spec's F1 description | None |
| F2 | Not a seed. Written from the spec's F2 description | None |
| F3 | Example 1, Executive Summary. Paragraph 1 is its BEFORE text. Paragraph 2 is the metrics sentence from its AFTER text | Paragraph 2 is the AFTER line, kept as the fact to preserve |
| F4 | Not a seed. Written from the spec's F4 description | None |
| F5 | Not a seed. Code is written for the spec's F5 description | None |
| F6 | Not a seed. Code is written for the spec's F6 description | None |
| F7 | Not a seed. Written from the spec's F7 description | None |
| F8 | Not a seed. Written from the spec's F8 description | None |
| F9 | Not a seed. Written from the spec's F9 description | None |
| F10 | Not a seed. Written from the spec's F10 description | None |

Only one fixture (F3) uses the seed text directly. The file holds ten before/after pairs: eight are slop removal (Examples 1 to 8) and two are token compression (Examples 9 and 10, the "caveman" style), which this pack does not cover. The pairs are single examples with change notes, not a labelled set, and there are too few of them to measure detection accuracy. See `packs/anti-slop/anti-slop-spec.md` (sections 8 and 11).

## Other provenance

The spec's section 8 table defines F1 to F10. The text of each `input` is authored for this pack, unless the table above says otherwise. The metric values in F3 come from the seed file and are not verified.
