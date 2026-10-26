---
schema_version: 1
kind: adr
id: ADR-0004
title: Validate structured model output with Pydantic v2 at the Python boundary
status: accepted
author: tianhonglee
created: 2026-10-25
updated: 2026-10-25
supersedes: []
superseded_by: []
links: [../../packs/README.md, ../../packs/anti-slop/schema/review-output.json, ../../umas/TECHNICAL-DESIGN-SPEC.md]
---

## Context

Packs define their output as JSON Schema files (for example `packs/anti-slop/schema/review-output.json`). Model output that feeds packs or the orchestrator must be parsed and validated. The stack is Python (see `umas/TECHNICAL-DESIGN-SPEC.md` Appendix A, and the stack note at its top).

A separate structured-output-parser library was proposed for this job. No evidence was found that it adds anything over the Python stack's own validation.

## Decision

- Model output is validated with **Pydantic v2** models at the Python boundary, where it enters the code.
- The packs' JSON Schemas remain the contract. Pydantic models are generated from them or written to match them, so the schema file is still the source a pack is reviewed against.
- No separate structured-output-parser library is used.

## Consequences

- One validation library covers model output, configuration and internal records at the boundary.
- A schema change in a pack needs the matching Pydantic model updated in the same change. A check that the two agree belongs in the pack's tests.
- Output that fails validation is a boundary error. It is not silently repaired.

## Alternatives considered

- **A dedicated structured-output-parser library:** not chosen. There is no evidence it adds anything to Pydantic v2 for this use, and it would add a second validation layer to keep in step with the schemas.
