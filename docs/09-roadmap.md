# 🗺️ Roadmap: Jev as a control plane

Where this lab is heading: Jev as the decision layer of an agent orchestrator, where a strong model plans once, cheap workers execute small enveloped tasks, and the strong model only sees exceptions.

| # | Function | Primitive | Status | Note |
| --- | --- | --- | --- | --- |
| 1 | Worker / tier routing | `choice` | ✅ measured ([01](01-bugs-and-patch.md)) | works; small share of total spend ([07](07-where-the-tokens-go.md)) |
| 2 | Completion & acceptance gate | `noul` per criterion | 🟡 shadow ([08](08-completion-gate.md)) | cheapest to wire, attacks the most wasteful wake-up |
| 3 | Failure triage for the retry ladder | `choice` | ⚪ planned | `typo_or_syntax` / `missing_context` / `architectural_block`: each answer maps to a different action |
| 4 | Dynamic context selection | `noul` per block | ⚪ planned, **highest risk** | cutting the wrong context breaks a worker silently; start by excluding only below 0.1 and measure worker failure rate |
| 5 | Blast-radius gate | `noul` / `score` | ⚪ planned, **second signal only** | deterministic rules stay the lock for `DROP`, `truncate`, force-push. Jev may tighten, never loosen |

On 5: a design that says "block when risk > 0.70" silently makes Jev the authority that *allows* everything below 0.70. TypeSafe documents weakness under adversarial state. Jev is never the sole authority on irreversible actions.

Claims we do not repeat until measured here: per-function latencies under 250 ms (we measured 256 to 927 ms per call), and any percentage of strong-model quota saved.
