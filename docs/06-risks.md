# ⚠️ Known risks

| # | Risk | Mitigation today |
| --- | --- | --- |
| 1 | **The first turn's tier sticks.** Opening with `hi` pins Haiku; above 20k the guard blocks going *down*. Whether it blocks going *up* is **not measured yet** | open with the real task; `/model` pauses the router |
| 2 | **Haiku gets more things wrong.** Jev sees the prompt text only, not the repository | weak answer → pick the model by hand |
| 3 | **Patch in `node_modules`** disappears on any reinstall | `./install.sh` is idempotent; track PRs #36/#37 |
| 4 | **Every prompt goes to TypeSafe** (turn text + current model + context size) | never paste secrets into a prompt |
| 5 | **The proxy is a single point of failure** mid-session | critical sessions run outside the wrapper |
| 6 | **A Jev outage mid-session raises no alert** | pending |
| 7 | **1M → 200k window** (jev-router #35) | not reproduced here up to 793k; monitoring |
| 8 | **+0.3 to 0.9 s** per fresh turn | none |
| 9 | Auxiliary calls carrying the sentinel still fall to the default `opus` | small but not free; pending |
