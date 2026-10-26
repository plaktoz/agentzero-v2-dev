---
schema_version: 1
kind: adr
id: ADR-0003
title: llm-gateway wraps the provider SDKs directly; no LiteLLM
status: accepted
author: tianhonglee
created: 2026-10-25
updated: 2026-10-25
supersedes: []
superseded_by: []
links: [../../libs/llm-gateway/README.md, ../../libs/README.md, ../../umas/TECHNICAL-DESIGN-SPEC.md]
---

## Context

The `llm-gateway` spec said "adopt an existing package first". Its section 6 listed LiteLLM as the first candidate, with the provider SDKs plus a thin wrapper as the second. Adopting first meant evaluating candidates and only building where the evaluation failed.

The owner decided on 2026-10-25 to wrap the provider SDKs directly. The owner did not adopt LiteLLM and did not check it against a current release.

## Decision

- `llm-gateway` wraps the provider SDKs for Anthropic, OpenAI, Google Gemini, and a custom HTTP endpoint. It is a thin gateway that meets the criteria in `libs/llm-gateway/README.md` section 6.
- LiteLLM is not a dependency.
- The section 6 criteria become the acceptance checklist for the wrapper. Every "yes" row must pass. The nice-to-have rows are optional.

## Consequences

- The gateway owns the retry schedule (3.3), failover (5.1), the usage callback (4), the auth-error rule (6), and a custom-endpoint path (criterion 1).
- No LiteLLM facts need to be checked. The spec does not claim any LiteLLM feature.
- The build cost is the code for those features. Each one is tested against the acceptance criteria in `libs/llm-gateway/README.md` section 8.
- A provider is still replaced by an edit to the alias table (3.2), so the wrapper keeps the provider-portability goal.

## Alternatives considered

- **Adopt LiteLLM:** rejected by the owner. It was not checked against a current release, so this record makes no claim about its features.
- **Build from scratch without the provider SDKs:** not chosen. It would re-implement each provider's wire format and auth, which the SDKs already handle.
