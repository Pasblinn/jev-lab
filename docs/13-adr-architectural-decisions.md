# 🏛️ Architecture Decision Records (ADRs)

Key architectural decisions governing the integration of TypeSafe Jev with coding agent workflows.

---

## Index of Decisions

- **[ADR-001](#adr-001-typed-decision-plane-vs-generative-routing):** Typed Decision Plane vs Generative Routing
- **[ADR-002](#adr-002-single-model-multi-effort-architecture-opus-55):** Single-Model Multi-Effort Architecture (Opus 5.5)
- **[ADR-003](#adr-003-strict-pre-flight-health-gating-with-loud-fallback):** Strict Pre-Flight Health Gating with Loud Fallback
- **[ADR-004](#adr-004-in-flight-attribution-sanitization--conditional-rule-injection):** In-Flight Attribution Sanitization & Conditional Rule Injection
- **[ADR-005](#adr-005-standard-1m-context-window--compaction-parity):** Standard 1M Context Window & Compaction Parity

---

### ADR-001: Typed Decision Plane vs Generative Routing

- **Status:** Accepted
- **Context:** Heterogeneous multi-tier orchestration requires turn-level classification (task difficulty, reasoning requirement, acceptance verification). Utilizing conversational LLMs for these micro-decisions incurs 2–5s latency, high token cost, and non-deterministic schema parsing errors. Regex rules lack necessary semantic judgment.
- **Decision:** Employ TypeSafe Jev (`/v1/systemone`) as a dedicated System One decision plane. Send minimal task envelopes (objective, scope, risk flags, diff summaries capped at ~1k chars) and query typed schemas (`choice`, `score`, `noul`).
- **Consequences:**
  - *Positive:* Sub-second response times (70–900 ms); fractional cent cost (~$0.000013/call); strictly typed output conforming to predefined enums and rubrics.
  - *Negative:* Stateless design requires the client harness to construct compact, well-structured context envelopes.

---

### ADR-002: Single-Model Multi-Effort Architecture (Opus 5.5)

- **Status:** Accepted
- **Context:** Traditional model routing alternates between model families (`haiku` $\leftrightarrow$ `sonnet` $\leftrightarrow$ `opus`). Every model switch changes the model identifier, completely invalidating provider prompt caches. In a 10-turn conversation with 3 model transitions, cache re-creation accounts for over 50% of total invoiced costs.
- **Decision:** Lock the upstream model to `claude-opus-5-5` across all execution tiers. Use Jev's routing output exclusively to tune reasoning effort via `output_config.effort`:
  - `haiku` tier $\rightarrow$ `effort: "low"`
  - `sonnet` tier $\rightarrow$ `effort: "medium"`
  - `opus` tier $\rightarrow$ `effort: "high"`
  - `fable` tier $\rightarrow$ `effort: "max"`
  Enforce mandatory `thinking: { type: "adaptive" }` and strip manual token budget parameters.
- **Consequences:**
  - *Positive:* 100% KV cache hit rate after initial load; access to $0.20/M token cache read rates; zero latency or token penalty for task complexity changes.
  - *Negative:* Relies on provider support for the `output_config.effort` parameter.

---

### ADR-003: Strict Pre-Flight Health Gating with Loud Fallback

- **Status:** Accepted
- **Context:** A proxy failure or upstream API outage in a routing layer can silently degrade session behavior or stall interactive development. Silent failures either cost excessive money or block the engineer.
- **Decision:** Implement a two-stage pre-flight check and hard fallback mechanism:
  1. `jev-health` executes a synthetic test decision against `api.typesafe.ai` before launching the session.
  2. If the health probe fails (HTTP error, timeout > 6s, invalid choice schema), write the diagnosis to `~/.jev/DOWN` and launch plain Claude Code with `--settings ~/.jev/fallback-settings.json`.
  3. The fallback hook triggers an audible notification and instructs the agent to prefix its first response with a clear `"JEV IS DOWN"` alert.
- **Consequences:**
  - *Positive:* Fail-open reliability ensures zero blocked sessions; failures are immediately transparent.
  - *Negative:* Introduces ~1s latency check on session initialization.

---

### ADR-004: In-Flight Attribution Sanitization & Conditional Rule Injection

- **Status:** Accepted
- **Context:** Upstream clients often inject dynamic reminders prompting the model to append `Co-Authored-By` or AI attribution trailers to commits. Furthermore, injecting static, comprehensive rulebooks on every prompt inflates baseline context by 75k+ tokens.
- **Decision:**
  1. **Proxy Sanitization:** Strip attribution suggestions from `<system-reminder>` blocks and replace them with strict repository cleanliness policies.
  2. **Deterministic PreToolUse Hook:** Deploy `block-dangerous-git.py` to inspect `git commit` commands and abort execution before commits with attribution or unsafe flags are created.
  3. **Conditional Rules:** Dynamically inspect the user prompt and inject only task-relevant domain rules (Git, Browser testing, Database safety, Destructive commands).
- **Consequences:**
  - *Positive:* Zero AI attribution leaks into version control; 20–30% baseline token reduction per request.
  - *Negative:* Requires ongoing maintenance of domain regex patterns and sanitization logic.

---

### ADR-005: Standard 1M Context Window & Compaction Parity

- **Status:** Accepted
- **Context:** Modern frontier models support native 1,000,000 token context windows. Restricting compaction windows to arbitrary sub-limits (e.g., 800k) causes premature compaction and unnecessary context disruption during large refactoring tasks.
- **Decision:** Standardize both context capacity and auto-compaction thresholds to 1,000,000 tokens across all configuration layers:
  - `CLAUDE_CODE_MAX_CONTEXT_TOKENS="1000000"`
  - `CLAUDE_CODE_AUTO_COMPACT_WINDOW="1000000"`
  - `autoCompactWindow: 1000000` in global settings
  - Propagate environment variables explicitly through the VS Code process wrapper (`jev-vscode-wrapper`).
- **Consequences:**
  - *Positive:* Uniform session capacity across CLI and IDE; eliminates premature compaction prompts; allows massive repositories and dependencies to remain active in memory when needed.
  - *Negative:* Long sessions nearing 1M tokens require strict adherence to context hygiene and cache-friendly habits.
