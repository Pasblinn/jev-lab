# 🧭 Case study: the wrapper on a long session

A real working session in VS Code, with **~763k cached tokens**, was reloaded under the wrapper.

| Metric (45 min) | Value |
| --- | --- |
| Turns served through the proxy | 84 |
| Model | `claude-opus-5` on 100% |
| Cache | 763k → 793k, unbroken, no compaction |
| Jev decisions | 1 |

The only decision:

```
prompt:      "done, re-authenticated, you can continue"
Jev wanted:  haiku 0.61 · opus 0.33 · sonnet 0.06
policy:      opus  (downgrade-not-worth-cache-rebuild)
```

## What this teaches

> [!CAUTION]
> **Jev judges the prompt, not the work in progress.** The sentence was trivial; the task behind it was not. Without the cache guard the session would have rebuilt 763k tokens of cache on Haiku and continued heavy work on the weakest model.

- On a long session the router **saves nothing**: the guard (correctly) pins the tier for good. What remains is ~1 s of latency per prompt and a proxy as a single point of failure.
- This is a state-design lesson, not a Jev flaw: the state sent to Jev had the prompt and a token count, but nothing about the task in flight. **The decision is only as good as the state.**
- Corollary: **open a conversation with the real task**, not with `hi`. The first turn's tier tends to become the session's tier.

Decision taken: long, critical sessions run outside the wrapper. Jev stays on for new sessions and mechanical turns.
