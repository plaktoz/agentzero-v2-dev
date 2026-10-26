---
schema_version: 1
kind: adr
id: ADR-0002
title: Run OpenAI and Gemini agents through the Codex CLI harness; drop the separate Gemini CLI harness
status: accepted
author: tianhonglee
created: 2026-10-25
updated: 2026-10-25
supersedes: []
superseded_by: []
links: [TECHNICAL-DESIGN-SPEC.md, UMAS-BUILD-ASSESSMENT.md, ../libs/agent-platform/README.md, ../libs/llm-gateway/README.md]
---

## Context

The design listed two coding harnesses for the OpenAI and Google providers: `openai-codex` for OpenAI, and `antigravity` (the Gemini CLI harness, formerly `gemini-cli`) for Google Gemini. Each had its own adapter, skill-file behaviour and signal convention to specify and test.

The owner has tested the Codex CLI harness and it works. Gemini models can be driven through it, so a second Gemini harness is not needed.

## Decision

- The harness `openai-codex` runs OpenAI models and Google Gemini models.
- The `antigravity` harness and its `GeminiCliAdapter` are removed from the stack. The name `gemini-cli` is not reused.
- The LLM provider stays a separate choice. A Codex-harness assignment names its provider in `llm-gateway`: `openai` or `google-gemini`. Harness and provider remain independent, as set out in `TECHNICAL-DESIGN-SPEC.md` section 1.3.
- The Codex CLI reaches Gemini models through a **custom endpoint, model and API key**, set in the harness config (`GEMINI_API_KEY`). The owner has tested that this works. Whether the endpoint is Google's native API or an OpenAI-compatible one is not yet recorded.
- Gemini calls from UMAS's own code (Coordinator, Router and so on) go through `llm-gateway` with the `google-gemini` alias, using the same endpoint, model and key.
- The `llm-gateway` alias `google-gemini` is kept. It now belongs to the Codex harness, not to `antigravity`.

## Consequences

- Built-in adapters drop from four to three: `claude-code`, `openai-codex`, `copilot`. `GeminiCliAdapter` and `AntigravityAdapter` are not built.
- Harness count in the design: Claude Code, OpenAI Codex, GitHub Copilot.
- Every hook-supporting harness is now `claude-code` and `openai-codex`. The universal `SKILL.md` contract (agent-platform section 5.8) applies to both.
- Cost: one fewer adapter, and no separate Gemini harness tests. Codex-harness tests must run once per provider (`openai`, `google-gemini`).
- The capability list for `openai-codex` must be checked when Gemini runs through it, because the harness's capabilities were written for OpenAI models. Recorded as an open question in `libs/agent-platform/README.md`.
- Named references to `antigravity` in the specs, the PRD, the agent-platform library and the DNA are updated or marked as superseded in the same change.

## Alternatives considered

- **Keep `antigravity` as a second harness:** the owner has no need for it now that Codex runs Gemini. It would add an adapter with no test in use.
- **Route Gemini through an OpenAI-compatible endpoint in `llm-gateway` and keep only the Codex harness:** this is the mechanism that makes the Codex harness work for Gemini. Whether the Gemini provider is reached natively or through a compatible endpoint is an open question in `libs/llm-gateway/README.md`, not decided here.
