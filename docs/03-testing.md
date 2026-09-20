# 🧪 Testing on a budget

The status line lies by omission: it shows up even when no decision was made. **The transcript is the proof.**

## Script (about two cheap turns)

```sh
mkdir -p /tmp/jevtest && cd /tmp/jevtest      # empty folder: no CLAUDE.md, no tools firing
JEV_DEBUG=1 jev -p "say only: ok"             # expected: opus -> haiku (jev)
```

Then the control, a prompt that **must** stay up:

```sh
JEV_DEBUG=1 jev -p "no tools, one line: biggest risk of migrating auth to OAuth2 with PKCE with zero downtime?"
```

Only the pair proves anything. "It went to Haiku" alone may be a default, not a decision.

## Check without spending a turn

```sh
# who actually answered
grep -o '"model":"claude-[^"]*"' "$(ls -t ~/.claude/projects/*/*.jsonl | head -1)" | sort | uniq -c
# what Jev decided and why
python3 -m json.tool "$(ls -t "${TMPDIR}"jev-claude/*.json | head -1)" | grep -E '"(tier|reason|prompt|confidence)"'
```

✅ Working = **your** prompt appears in `prompt` **and** the transcript shows the model of the decided tier.

## Why an empty folder

An empty folder avoids a project `CLAUDE.md` and keeps tools from firing on a trivial prompt, so the test stays at one or two requests. It does **not** make the request small: the opening request measured 76k tokens in an empty folder and 74k in the home directory, because the baseline is global ([breakdown](07-where-the-tokens-go.md)). The `ctx~13k` the router logs counts messages only, not tools or the system prompt.

## Hands-free interactive run

```sh
expect -c 'spawn jev; sleep 8; send "hi\r"; sleep 25; send "/exit\r"; sleep 3'
```
