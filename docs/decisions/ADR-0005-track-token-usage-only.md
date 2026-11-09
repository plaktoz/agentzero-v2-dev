# ADR-0005: Track token usage only; no budgets, no pause

> **Status:** Decided (owner, 2026-11-09) · **Closes:** D14, D17, D18, D19, D22, D22a and C2 in [decisions-pending-2026-10-25.md](../decisions-pending-2026-10-25.md)

## Decision

UMAS records how many tokens each model call used, which model, and when. It does not limit, reserve, price, warn about or pause on usage.

## Contract

**Recorded per call** (one JSON line in the token ledger):

```json
{ "v": 1, "ts": "2026-11-09T07:00:00Z", "model": "default", "tokens": 4120 }
```

- `ts` is RFC 3339 UTC. `model` is the llm-gateway alias, or the model name a harness reports. `tokens` is the total the provider reports for the call (input plus output, as one number).
- Nothing else is recorded: no actor, project, task, cost, or input/output split.
- A harness that reports no usage produces no line. The ledger never estimates.

**Removed**

| What | Where it was |
|------|--------------|
| Budgets, limits, windows, `define`, `adjust`, `reset` | budget-meter, main spec 5.6, `umas project config --budget` |
| Reservations, `reserve`, `commit`, `release`, admission control, `Deferred` | budget-meter, Scheduler dispatch |
| Threshold events (80/90/95/100 %), `spend_thresholds`, `exhausted`, `over_limit` | budget-meter, monitoring alerts, dashboard |
| `budget_paused` status, exception flow 6.6, "budget raised while paused" | agent-session, main spec section 4 and 6, interfaces, monitoring |
| Cost, price table, `price_version`, staleness warning, `umas metrics cost`, metric `token.cost` | budget-meter, metrics-store, llm-gateway |
| Wall-clock unit (D14) and per-role money estimates (D18) | budget-and-models, agent-execution |

**Kept**

- Context-window handoff in `agent-session` (`context_limit`, `handoff_threshold`, `emergency_threshold`). It protects a session from overflowing its model's window. It is not a spend limit and does not pause work.
- Provider rate limiting and failover in `llm-gateway`.
- The concurrency cap in `task-queue`, and stall supervision in `watchdog`.
- `umas metrics tokens`, answered from `metrics-store` rows `token.used`, grouped by `model`.

**Renamed and moved**

| Before | After | Why |
|--------|-------|-----|
| `libs/budget-meter` | `libs/token-ledger` | It no longer holds a budget. It is a usage ledger |
| `pack()` (handoff-packet packing) | `libs/agent-session`, section "Context packing" | `agent-session` was its only caller; the ledger has nothing to do with packing |
| `umas/modules/budget-and-models` | `umas/modules/models-and-usage` | The module keeps model policy and usage recording, and drops budgets |

## Consequences

- Spend is unbounded. A runaway loop can use tokens until the provider's own limit stops it. Mitigation that stays in the design: `watchdog` stops a worker that makes no progress, and `task-queue` caps concurrency.
- Usage cannot be attributed to a task, agent or project from the ledger. The owner accepted this by asking for model, amount and timestamp only. Adding a field later is a `v: 2` line format; readers of N-1 keep working (libs/README independence rule 5).
- Harness-run workers that report no usage are invisible in the totals.
- Money figures are not available. Anyone who needs cost multiplies the token totals by a price outside the system.

## Terminology map (for every document that changes)

| Old | New | Notes |
|-----|-----|-------|
| `budget-meter` (lib) | `token-ledger` | Path `libs/token-ledger/README.md`. Link as `../token-ledger/README.md` from `libs/`, `../../../libs/token-ledger/README.md` from `umas/modules/*/` |
| `budget-and-models` (module) | `models-and-usage` | Path `umas/modules/models-and-usage/models-and-usage-spec.md` |
| `budget_paused` (session status) | removed | No status for budget. Other statuses unchanged |
| `budget`, budget limit, `--budget` | removed | Including `umas project config --budget` |
| `reserve`, `commit`, `release`, `admit`, `Deferred`, admission | removed | |
| `spend_thresholds`, 80/90/95 % money thresholds, `exhausted`, `over_limit`, `budget_warning` | removed | |
| `token_limit` (agent-session) | removed; use `context_limit` | |
| `handoff_threshold` 0.90, `emergency_threshold` 0.95 | kept | These are fractions of the model's **context window**, not spend. They trigger handoff. They never pause work |
| `cost`, price table, `price_version`, `token.cost`, `umas metrics cost`, money | removed | |
| `token.input`, `token.output` (metric names) | `token.used` | One total per call, tagged `model` |
| `ingest_budget_meter` | `ingest_token_ledger(ledger_path, since?)` | |
| `budget-meter pack()` / "budget packing" | `pack()` in agent-session, section "Context packing" | Contract unchanged (section 5.5 of old budget-meter spec). Not the same as agent-platform's `pack_context` (cross-platform handoff). Do not rename `pack_context` |
| wall-clock cap (D14), per-role money estimate (D18) | removed | |
| exception flow 6.6 "Token budget exhausted mid-task" | removed; keep the heading as "6.6 Removed (ADR-0005)" so later numbering and anchors stay | |
| `umas metrics tokens` | kept | Totals of `token.used` grouped by `model` |

Keep each document's section numbers stable where a section is removed: put a one-line "Removed (ADR-0005)" note in its place rather than renumbering.

## Alternatives not taken

| Option | Why not |
|--------|---------|
| Keep budgets but never pause | Owner asked to remove the requirements, and a budget with no action is a number nobody reads |
| Keep a cost field | Owner listed the three fields to track |
| Keep the library name | `budget-meter` would describe something it no longer does |
