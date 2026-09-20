# 📚 Lessons from the ecosystem

Jev entered early access on 2026-09-16. Four days later: `browser-use/jev-ultrafast` 11k★, `tamaratran/fast-jev-compaction` 4.8k★, 155 projects catalogued in [`awesome-jev`](https://github.com/cobanov/awesome-jev). We read the issues of those who tested first (2026-09-20):

| Source | Finding | Consequence |
| --- | --- | --- |
| jev-router [#35](https://github.com/gargpratyush/jev-router/issues/35) | context window drops **1M → 200k** under the custom model; MCP schemas 651 → 18.8k tokens | biggest open risk for large sessions |
| jev-router [#17](https://github.com/gargpratyush/jev-router/issues/17) | switching models mid-session discards the cache; the author is still redesigning this | trust the 20k guard, do not disable it |
| jev-router [#29](https://github.com/gargpratyush/jev-router/issues/29) | with subagents: 3 prompts → **21 Jev calls** | filter injected messages, not only `tool_result` |
| fast-jev-compaction [#65](https://github.com/tamaratran/fast-jev-compaction/issues/65) | `drop_call` removes the tool call and keeps the narration → the model **fabricated 9 "work done" reports** | never delete evidence while keeping the claim |
| fast-jev-compaction [#56](https://github.com/tamaratran/fast-jev-compaction/issues/56) | two `noul` answers come back on different scales; a single 0.5 threshold truncates the file the agent was about to edit | calibrate per question |
| fast-jev-compaction [#70](https://github.com/tamaratran/fast-jev-compaction/issues/70) | "nothing left to prune" treated as "Jev failed" | tell empty from error |
| winnow [#1](https://github.com/GhalebDweikat/winnow/issues/1) | unauthenticated local sidecar: a web page can spend your key | every loopback service needs a token |

## The three patterns

1. **Good ranking, poor calibration.** In every report Jev *orders* correctly. What breaks is comparing the probability against a fixed number.
2. **Silent failure is the rule, not the exception.** Routing off, plugin not loading, evidence deleted: none raised an error.
3. **Schema-valid ≠ correct.** None of these are Jev being weak. They are integrations asking the wrong question, sending the wrong state, or trusting the wrong number. See [Using Jev the right way](00-using-jev-well.md).
