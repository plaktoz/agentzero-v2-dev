---
schema_version: 1
kind: adr
id: ADR-0001
title: Use a minimal read-only HTML dashboard instead of React
status: accepted
author: tianhonglee
created: 2026-10-20
updated: 2026-10-20
supersedes: []
superseded_by: []
links: [UMAS-BUILD-ASSESSMENT.md, TECHNICAL-DESIGN-SPEC.md]
---

## Context

The technical design lists a React 18 and TypeScript dashboard (Zustand, shadcn/ui, Tailwind, Vite, Socket.io) with no component specifications. The build assessment estimates it, together with the CLI, at about 25M tokens (realistic), the second-largest cost driver and the largest unmitigated one. The dashboard is secondary to the CLI. Its backend is also undecided (FastAPI or Express, with Socket.io).

Three options were open: a terminal UI, a minimal read-only HTML dashboard, or the full React dashboard.

## Decision

The dashboard is a **minimal read-only HTML page** served by the existing API. It is static HTML with a small amount of plain JavaScript that polls a REST endpoint. There is no front-end framework, no build step, and no client state library. It shows what the CLI `watch` and `status` commands show: agents and their states, work bundles, merge queue state, and cost and token figures.

- It is read-only. Actions stay in the CLI.
- It reads from the same API definition the CLI uses, not a second one.
- Live updates use polling. Server-sent events may be added later if polling proves too slow.
- Authentication and role-based access control apply to the API, not to the page.

## Consequences

- The React, TypeScript, Zustand, shadcn/ui, Tailwind, Vite, Socket.io, and Recharts entries in the stack are no longer needed for the first release.
- The dashboard cost estimate should be re-based. The 25M figure in the build assessment covered a React app.
- The Socket.io versus FastAPI question goes away, because polling needs no WebSocket server. Backend framework choice remains open.
- The page can be generated and tested with the same tools as the rest of the code. There is no second toolchain.
- Users get no interactive controls and no rich charts. Anything beyond a table or a simple bar is out of scope until a new decision.
- A framework can still be introduced later, because the page only depends on the API.

## Alternatives considered

- **Terminal UI** (`ratatui` or `textual`): lowest cost and no web surface, but not viewable remotely or shared by link, and it needs a language choice that the stack review has not settled.
- **Full React dashboard** (as in the stack spec): richest result, but it has no component spec, adds a second language and toolchain, and carries the largest cost risk.
- **No dashboard, CLI only**: cheapest, but loses the at-a-glance view of many agents that the PRD asks for.
