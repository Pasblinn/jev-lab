# 📊 Where the tokens actually go

After patching the router we asked the obvious question late: **how much of the real consumption can a per-turn router even touch?** Measured on one developer's Claude Code transcripts, 7 days, 157 sessions, 1,819M cache-read tokens. Tools: [`tools/session-growth.py`](../tools/session-growth.py), [`tools/base-breakdown.sh`](../tools/base-breakdown.sh).

> [!IMPORTANT]
> **78% of all tokens were read by 6 sessions. The 124 sessions that stayed under 100k of context, the only place a model router makes decisions that stick, add up to 1%.**

| Sessions | Tokens read | Share |
| --- | --- | --- |
| 6 giant sessions (peak context 877k to 965k) | 1,423M | **78%** |
| the single largest one | 645M | 35% |
| 124 small sessions (peak < 100k) | 17M | **1%** |

In a long session the cache guard pins the tier (correctly, see [the case study](04-long-session.md)). So everything in docs 01 to 03 optimises the 1%.

## Why giant sessions dominate

With 800k of context, **every request re-reads 800k**. Prompt size stops mattering: "go on" costs the same as a heavy refactor, and it is paid again on every tool call. One session made 143 requests in a day and read 107M tokens from cache.

## How the six sessions grew

| Finding | Evidence |
| --- | --- |
| They live above 200k | 90 to 98% of tokens were read with context > 200k; they cross 200k between request 12 and 145 and stay there for 69 to 91% of their requests |
| They only stop at the ceiling | all six peaked between 880k and 999k; 0 to 8 compactions each, forced by the window |
| No tool result is large | the biggest single result across all six: 15k tokens. Average `Bash` result: 140 to 540 tokens |
| It is volume, not bloat | 1,250 `Bash` + 456 `Read` calls in one session. By tool, across the six: Bash 69%, Read 18%, a database MCP 5% |
| The model's own output is the largest entrant | assistant text + tool inputs exceed tool results in 5 of 6 (e.g. 820k vs 325k). Upper bound: we do not know how much `thinking` persists between turns |
| The baseline is already high | 100k by request 2 to 29 |

**Consequence:** compressing file reads would not fix this. `Read` is 18% of what enters, at ~440 tokens per call. The cost is *how many times the whole context is re-read*.

## What-if: a context ceiling with handoffs

Same per-request growth, restart at 40k whenever the ceiling is hit:

| Session | Actually read | 150k ceiling | 300k ceiling |
| --- | --- | --- | --- |
| A | 1,555M | 288M (−81%), 38 handoffs | 504M (−68%), 18 |
| B | 1,023M | 174M (−83%), 35 | 313M (−69%), 15 |
| C | 989M | 193M (−80%), 27 | 348M (−65%), 12 |
| D | 656M | 125M (−81%), 32 | 225M (−66%), 14 |
| E | 173M | 44M (−74%), 10 | 77M (−56%), 4 |
| F | 96M | 15M (−84%), 7 | 29M (−70%), 3 |

> [!WARNING]
> The simulation is optimistic. It ignores the cost of each handoff: rebuilding the cache, re-reading files the new session does not know, and losing a decision made 300 requests ago. 30+ handoffs in one session is not workable. The 300k column (12 to 18 handoffs over weeks) is the realistic one, and it still removes about two thirds.

A compaction hook that fires at 75% of a 1M window warns at 750k, after ~95% of the session's tokens were already read inflated.

## What the baseline is made of

The opening request of `say only: ok`, captured with a body-only dump proxy. **Real total: 73.7k to 76.1k tokens**, from the API usage. The breakdown below is chars/4 and **under-counts by ~1.45x** (JSON schemas tokenise densely), so read the shares, not the absolutes:

| Share | Component |
| --- | --- |
| 60% | schemas of 31 native tools. One publishing tool alone is 16% of the whole baseline; three related ones ~25% |
| 11% | the list of installed skills (~70, one description each) |
| 6% | an `AGENTS.md` in the home directory, loaded for **every** folder under it |
| 4% | global `CLAUDE.md` |
| 4% | Claude Code's own system prompt |
| 4% | agent types (7 of 15 from a single plugin) |
| 3% | a SessionStart hook's rules |
| 5% | two always-on MCP servers |

1. **An empty folder is not cheap.** Empty folder: 76k. Home directory: 74k. The baseline is global.
2. **Your own prose is the small part.** Instructions and hooks are ~17%. Tools, skills and agents are ~75%.
3. Realistic cut: 20 to 30% of the baseline, on every request of every session. Still, on an 800k session the baseline is ~10% of what gets re-read. **Ceiling first, baseline second, routing a distant third.**

## Measured cut: denying tools you never use

Does a denied tool still ship its schema? No. Same folder, same prompt, real totals from the API usage:

| Run | Tools in payload | Real tokens, first request |
| --- | --- | --- |
| baseline | 41 | 76,100 |
| `--settings` with `permissions.deny` for 4 publishing/design tools | 37 | **55,297** |
| `--disallowedTools` with the same 4 | 37 | 55,296 |

**−20.8k tokens (−27%) on every request of every session**, from four tools. Both mechanisms remove the schema from the request, not just the permission. Check your own heaviest schemas with `tools/base-breakdown.sh` before copying this list: a denied tool is gone even when you do want it.

## What this means for Jev

Not that Jev is the wrong tool: that a chat-session router is the wrong *place* for it. Small, enveloped tasks with minimal state are where a typed decision layer pays, because there the context never grows. See [the completion gate experiment](08-completion-gate.md) and [Using Jev the right way](00-using-jev-well.md).
