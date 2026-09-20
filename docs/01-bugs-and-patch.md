# 🔬 Two silent bugs and the patch

Base: `jev-router` 0.3.0 · Claude Code 2.1.278 · macOS. Patch: [`patches/jev-router-0.3.0-routing-fixes.patch`](../patches/jev-router-0.3.0-routing-fixes.patch) (38 lines, `src/proxy.mjs` only).

## Bug 1: the user's real turn was never routed

**Symptom.** `hi` in a fresh session was answered by `claude-opus-5`, and `/jev-explain` said *"no routing decision has been recorded"*. The only recorded decisions were for `[SUGGESTION MODE…]` (Claude Code's internal next-prompt suggestion call) and for `/model`.

**Instrumentation.** `JEV_DUMP` writes the body of every `/v1/messages`:

```
dump.…688.json | tools=41 | msgs=2 | last.role=system   ← real turn, skipped
dump.…313.json | tools=0  | msgs=1 | last.role=user     ← auxiliary call
```

**Cause.** `newTurnPrompt` required `messages.at(-1).role === "user"`. Claude Code appends `SessionStart` hook output as a `role: "system"` message **after** the user turn. Anyone with a SessionStart hook hits this in 100% of sessions. With no decision, the code falls to `state.tier ?? "opus"`.

Side effect: the suggestion call ends in `user` and carries tools, so **that** was what Jev judged, and the tier chosen for the suggestion leaked into the next real turn.

**Fix.** Walk back over trailing `system` messages, and ignore prompts starting with `[SUGGESTION MODE`.

## Bug 2: every session in a real project was born stuck on Opus

**Cause.** `decide()` refuses a downgrade when `contextTokens > 20000`, to protect the prompt cache. On the first turn there is no cache, but `current` starts as `"opus"` and `CLAUDE.md` plus hook output push the opening message past 20k.

**Fix.** `contextTokens: state.tier ? contextTokens : 0`. The guard only applies once a tier has been pinned for the conversation.

**A/B** (145 KB `CLAUDE.md`, ctx ~46k, Jev `p=0.99` in both arms):

| Arm | Log |
| --- | --- |
| patched | `opus -> haiku (jev)` |
| stock | `opus -> opus (downgrade-not-worth-cache-rebuild/no-change)` |

## Upstream

The same diagnoses showed up independently in [#36](https://github.com/gargpratyush/jev-router/pull/36) and [#37](https://github.com/gargpratyush/jev-router/pull/37) (opened 2026-09-20, issues #18 and #28). Difference: #36 does **not** filter `[SUGGESTION MODE`. Once those merge, prefer the official release and keep only that filter.

> [!WARNING]
> The patch lives in `node_modules`. Reinstalling or upgrading `jev-router` wipes it, and the router silently goes back to sending everything to Opus. Run `./install.sh` again. Upstream ships `proxy.mjs` with CRLF line endings; the installer normalises them before patching.

## Hypotheses ruled out

| Hypothesis | How it was ruled out |
| --- | --- |
| Wrong key | same length and value as the key that answers the API directly |
| Jev down | `askJev` called in isolation: typo → haiku `p=1.00` (927 ms); auth refactor → opus `p=0.95` (696 ms) |
| Broken install | `[jev] rewrite jev-router -> …` was logged: the proxy was alive, it just never decided |
