# llm-gateway

> Standalone library spec · Draft v0.1 · Part of [libs/README.md](./README.md)
> **Independence:** no dependency on UMAS. Depends only on provider SDKs or HTTP.
> **Build posture: adopt first.** This capability exists in mature packages. This spec is mainly the **requirements and evaluation checklist**; build a wrapper only for the gaps.

---

## 1. Purpose

One interface for calling LLMs across providers, with a defined retry policy, bounded failover, rate limiting, and normalised usage reporting. Application code names a model alias, not a vendor SDK.

## 2. Scope and Non-Goals

**In scope**
- `complete` / `stream` with tool calling, in one provider-neutral message format
- Error classification and a retry policy
- A failover chain (primary -> fallback) with **no blind retry loops**
- Client-side rate limiting
- Normalised usage (input, output, cached tokens) delivered by callback
- Model aliases resolved from configuration

**Non-goals**
- Agent loops, tool execution, prompt construction, or memory
- Task-level resume after failover. The caller re-supplies the conversation or checkpoint; the gateway is stateless about tasks. (See 5.4.)
- Budget enforcement. The gateway reports usage through a callback; see [budget-meter](../budget-meter/README.md).
- Caching, evaluation, or prompt management

## 3. Concepts and Data Model

### 3.1 Request and response

```
Request:  { alias, messages[], tools[]?, max_output_tokens?, temperature?, system?, metadata{} }
Response: { text, tool_calls[], stop_reason, usage, model_used, provider_used, attempts[] }
Usage:    { input_tokens, output_tokens, cached_input_tokens?, cache_write_tokens? }
```

`attempts[]` lists every provider call with its outcome, so failover is visible to the caller.

### 3.2 Model alias table (configuration)

```yaml
aliases:
  default:  { primary: {provider: anthropic, model: "<id from config>"},
              fallback: {provider: openai, model: "<id from config>"} }
  planner:  { primary: ..., fallback: null }
```

Replacing a provider is an edit to this table, not a code change. **Model IDs are never hard-coded in the library or in the spec.** The current docs pin specific model IDs (for example `claude-3-5-sonnet-20241022`); this is a configuration value that will change.

### 3.3 Error taxonomy

| Class | Examples | Default policy |
|-------|----------|----------------|
| `rate_limited` | HTTP 429 | Exponential backoff 5s, 15s, 45s (honour `Retry-After`), then failover |
| `server_error` | 5xx | 3 immediate retries, then failover |
| `timeout` | No response in `timeout` (default 30s, streaming: first-token timeout) | 2 retries, then failover |
| `auth` | 401/403 | **No retry, no failover**; raise at once (credentials problem) |
| `context_overflow` | Prompt over model limit | No retry. Raise; the caller must shrink the input |
| `invalid_request` | 400 schema errors | No retry. Raise |
| `content_filtered` | Refusal or safety stop | No retry. Return with `stop_reason=refusal` |

The gateway keeps this taxonomy as its own. A consumer that wants one error vocabulary can express each class as an [error-classifier](../error-classifier/README.md) catalog entry (a data format, not a dependency): `rate_limited`, `server_error` and `timeout` are `transient` entries whose `retry` block carries the policy above (`base_seconds: 5, factor: 3`, `base_seconds: 0` for immediate retries, `honour: retry_after`); `auth`, `context_overflow` and `invalid_request` are `permanent`; `content_filtered` is a result, not an error. Failover is the gateway's own behaviour and is not part of the record.

## 4. Interface

| Operation | Description |
|-----------|-------------|
| `complete(request) -> Response` | Blocking call applying the policy. |
| `stream(request) -> stream<Delta>` | Streaming. Mid-stream failure is reported as an error event; the gateway does **not** transparently restart a partly delivered stream on another provider (the output may differ). |
| `health() -> [ProviderHealth]` | Last-seen status and circuit state per provider. |
| `on_usage(callback)` | Called once per successful or failed attempt with `{alias, provider, model, usage, latency_ms, outcome}`. |

## 5. Behaviour

### 5.1 Retry and failover

```
for provider in [primary, fallback]:
    apply the retry schedule for the error class
    if success -> return
    if error is non-retryable (auth, overflow, invalid) -> raise immediately
raise ProviderExhausted(attempts)
```

### 5.2 No blind retry loops

After the fallback is exhausted the gateway raises `ProviderExhausted`. It does **not** keep retrying in the background. Repeated blind retries risk burning tokens on timeouts that are charged, so recovery is initiated by the caller or a human.

### 5.3 Circuit breaker

After `breaker_threshold` consecutive failures (default 5) a provider is `open`: calls skip it for `breaker_cooldown` (default 60s) and go straight to the fallback, then a single probe call decides whether to close. This keeps a down provider from slowing every call by the full retry schedule.

### 5.4 Resume after failover

The gateway swaps provider and model; it does not rebuild the context. A caller that wants "resume from last checkpoint" builds a fresh request from its own checkpoint and calls `complete` with an alias bound to the fallback. The gateway provides `provider_override` on the request for that purpose.

### 5.5 Rate limiting

A token bucket per provider and per alias, with `requests_per_minute` and `tokens_per_minute`. A call that would exceed a bucket waits up to `max_queue_wait` (default 30s), else raises `RateLimitedLocal` with `retry_after`. Provider-reported limits (headers) adjust the bucket dynamically.

### 5.6 Security

API keys come from environment variables or a secrets provider, never from files committed to a repo, never logged. Request/response bodies are not logged by default; the usage callback carries counts only. TLS is required for all non-localhost endpoints.

## 6. Adopt-or-Build Evaluation

Evaluate candidates (for example LiteLLM, the provider SDKs with a thin wrapper, or an equivalent library; **verify current features, not this spec's assumptions**) against these pass/fail criteria:

| # | Criterion | Required |
|---|-----------|----------|
| 1 | Supports Anthropic, OpenAI, Google Gemini, and a custom HTTP endpoint (for example a local model server) | yes |
| 2 | Unified tool-calling and streaming | yes |
| 3 | Per-class retry schedule as in 3.3 (configurable) | yes |
| 4 | Ordered fallback with a visible attempts list | yes |
| 5 | Usage callback with input, output, and cached tokens | yes |
| 6 | Auth errors are never retried or failed over | yes |
| 7 | Circuit breaker | nice-to-have |
| 8 | Client-side TPM/RPM limiting | nice-to-have |
| 9 | Works without a proxy server process | strongly preferred |
| 10 | Active maintenance, permissive licence | yes |

If a candidate passes all "yes" rows, adopt it and write only configuration plus a thin adapter for the "no blind loops" rule and the usage callback. If not, build the minimum that fills the failed rows.

## 7. Failure Modes

| Error | Cause |
|-------|-------|
| `ProviderExhausted` | All providers failed; carries `attempts[]` |
| `AuthError` | 401/403 on the first provider |
| `ContextOverflow` | Prompt too large; carries the model limit |
| `RateLimitedLocal` | Local bucket wait exceeded |
| `ConfigError` | Unknown alias or missing credentials, detected at startup (`validate()`), not on first call |

## 8. Acceptance Criteria

1. With a mock server returning 429, 5xx, timeout, and 401 in turn, the attempts list and total wait match the schedule in 3.3, and 401 is never retried.
2. When both providers fail the gateway raises once and issues no further calls.
3. Usage callback fires for every attempt, including failed ones, with the right provider and model.
4. Changing a model ID in configuration needs no code change or rebuild.
5. No secret appears in logs, usage events, or error messages (tested with a canary key).
6. With the primary breaker open, calls go to the fallback with no added latency.

## 9. Known Consumers

> This section lists known consuming projects. The library does not depend on any of them.


| UMAS concept | Mapping |
|--------------|---------|
| Exception flow 4.7 retry table | Gateway default policy (3.3) |
| Failover resume from `STATE.md` | UMAS builds the compressed context from `hook-store` and calls the gateway with the fallback alias |
| Error classes and retry table | Same policy expressed as [error-classifier](../error-classifier/README.md) catalog entries (section 9 there); the gateway still enforces its own policy |
| P0 on auth error; P1 on exhausted | UMAS maps `AuthError` -> P0 escalation, `ProviderExhausted` -> P1 and `provider_failed` session status |
| Per-role model mapping and panels | UMAS resolves a role to an alias; a panel is N `complete` calls plus synthesis (not gateway logic) |
| Token accounting | `on_usage` -> `budget-meter.record` |

## 10. Source Material and Deviations

Extracted from `TECHNICAL-DESIGN-SPEC.md` §1.3 (providers), `UMAS-TECH-DESIGN-SPEC.md` §3.7 and §4.7.

| Deviation | Why |
|-----------|-----|
| Spec is requirements plus an evaluation, not a design | The source describes providers as configuration only (no gateway design), and this is a commodity capability |
| No hard-coded model IDs | Source pins `claude-3-5-sonnet-20241022` and older models |
| Mid-stream restart disallowed | Source does not address streaming; silently switching provider mid-output would corrupt it |
| Explicit "context_overflow" class | Absent in the source; it is a common failure that retry cannot fix |

## 11. Open Questions

1. Are Anthropic, OpenAI and Gemini each reached through their native APIs, or through a compatible endpoint? Native keeps provider features such as prompt caching. A compatible endpoint is simpler to replace.
2. Answered: coding Workers run as external CLI harnesses and bypass this gateway, so it serves only UMAS's own calls (Coordinator, Router, Triage, Patrol, Monitors). Worker usage figures come from the CLIs' reported usage and are best-effort.
3. Multi-model panels: is a synthesis helper worth including, or does it stay application logic?
