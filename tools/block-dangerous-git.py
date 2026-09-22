#!/usr/bin/env python3
"""PreToolUse gate for irreversible git commands.

Blocks only what destroys work that is hard or impossible to recover:
force-push, hard reset, forced clean, branch deletion, wholesale discard.
Plain `git push`, `git commit`, `git stash` and `git revert` stay allowed —
they are either reversible or explicitly requested.
"""
import json
from pathlib import Path
import re
import sys

# (regex, reason, safer alternative)
RULES = [
    (
        r"\bgit\s+(?:-\S+\s+)*push\b(?=.*(?:\s--force\b|\s-f\b))(?!.*--force-with-lease)",
        "force-push overwrites remote history",
        "use --force-with-lease, or push a new branch",
    ),
    (
        r"\bgit\s+(?:-\S+\s+)*push\b.*(?:\s--delete\b|\s-d\b|\s:\S)",
        "deleting a remote branch",
        "delete it in the forge UI after confirming it is merged",
    ),
    (
        r"\bgit\s+(?:-\S+\s+)*reset\b.*\s--hard\b",
        "reset --hard discards uncommitted work irrecoverably",
        "use `git stash` (recoverable) or `git reset --keep`",
    ),
    (
        r"\bgit\s+(?:-\S+\s+)*clean\b.*\s-\w*f",
        "clean -f deletes untracked files with no reflog to recover them",
        "run `git clean -n` first to see what would go",
    ),
    (
        r"\bgit\s+(?:-\S+\s+)*branch\b.*\s-D\b",
        "branch -D deletes an unmerged branch",
        "use -d (refuses when unmerged), or note the SHA first",
    ),
    (
        r"\bgit\s+(?:-\S+\s+)*(?:checkout|restore)\s+(?:--\s+)?\.(?:\s|$)",
        "discards every uncommitted change in the tree",
        "use `git stash` so it stays recoverable",
    ),
    (
        r"\bgit\s+(?:-\S+\s+)*checkout\b.*\s-f\b",
        "forced checkout overwrites local modifications",
        "commit or stash first",
    ),
]

AI_COMMIT_TRIGGER = re.compile(r"\bgit\s+(?:-\S+\s+)*commit\b", re.IGNORECASE)
AI_ATTRIBUTION_PATTERN = re.compile(
    r"(?i)co-authored-by\s*:|noreply@anthropic\.com|🤖|generated\s+with\s+\[?claude|\b(claude|codex|copilot|chatgpt|openai|anthropic)\b"
)


def check_commit_policy(command: str) -> tuple[bool, str]:
    if not AI_COMMIT_TRIGGER.search(command):
        return False, ""

    # 1. Direct match in command string (e.g. -m flags or heredocs)
    if AI_ATTRIBUTION_PATTERN.search(command):
        return (
            True,
            "Git commits must NEVER mention AI (Claude, Codex, Copilot, etc.) or contain Co-Authored-By trailers (forbidden by CLAUDE.md / AGENTS.md).",
        )

    # 2. Check if commit message is loaded from a file (-F / --file)
    file_match = re.search(r"(?:-F|--file)[=\s]+([^\s]+)", command)
    if file_match:
        file_path = file_match.group(1).strip("\"'")
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if AI_ATTRIBUTION_PATTERN.search(content):
                return (
                    True,
                    f"Commit message in {file_path} contains AI attribution or Co-Authored-By trailers (forbidden by CLAUDE.md / AGENTS.md).",
                )
        except OSError:
            pass

    return False, ""


SCRIPT_EXEC_PATTERN = re.compile(
    r"(?:^|[;&|\s])(?:bash|sh|zsh|python3?|node)\s+([^\s;&|]+)|(?:^|[;&|\s])(\./[^\s;&|]+)"
)

DANGEROUS_SCRIPT_PATTERNS = [
    (
        r"(?:curl|wget)\b.*\|\s*(?:ba|z)?sh\b",
        "remote script piping to shell (curl/wget | sh)",
        "download and inspect the script locally before running",
    ),
    (
        r"\bgit\s+(?:-\S+\s+)*push\b(?=.*(?:\s--force\b|\s-f\b))(?!.*--force-with-lease)",
        "force-push overwriting remote history",
        "use --force-with-lease, or push a new branch",
    ),
    (
        r"\bgit\s+(?:-\S+\s+)*reset\b.*\s--hard\b",
        "reset --hard discarding uncommitted work irrecoverably",
        "use `git stash` or `git reset --keep`",
    ),
    (
        r"\brm\s+-[rR]*f[rR]*\s+(?:/|~|\$HOME|\$\{HOME\})(?:/|\s|$)",
        "recursive deletion of root or home directory",
        "specify a targeted workspace directory",
    ),
]


def check_script_content(command: str) -> tuple[bool, str]:
    matches = SCRIPT_EXEC_PATTERN.findall(command)
    for m in matches:
        script_path = (m[0] or m[1]).strip("\"'")
        p = Path(script_path)
        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                for pat, reason, alt in DANGEROUS_SCRIPT_PATTERNS:
                    if re.search(pat, content):
                        return True, f"Script '{script_path}' contains {reason}. Suggested instead: {alt}."
                if AI_ATTRIBUTION_PATTERN.search(content) and AI_COMMIT_TRIGGER.search(content):
                    return (
                        True,
                        f"Script '{script_path}' contains git commit with AI attribution or Co-Authored-By trailers.",
                    )
            except Exception:
                pass
    return False, ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # never block on a malformed payload

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""

    # Check commit policy (no AI mentions, no Co-Authored-By)
    violated, policy_reason = check_commit_policy(command)
    if violated:
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": policy_reason,
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"Blocked by block-dangerous-git: {policy_reason} "
                            "Suggested instead: Rewrite the commit message using Conventional Commits in English without any AI references."
                        ),
                    },
                }
            )
        )
        return 0

    # Gate script execution: read script contents before running
    script_violated, script_reason = check_script_content(command)
    if script_violated:
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": script_reason,
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": (
                            f"Blocked by block-dangerous-git: {script_reason} "
                            "Ask the user before running this script — do not execute unvetted dangerous actions."
                        ),
                    },
                }
            )
        )
        return 0

    for pattern, reason, alternative in RULES:
        if re.search(pattern, command):
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": reason,
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": (
                                f"Blocked by block-dangerous-git: {reason}. "
                                f"Suggested instead: {alternative}. "
                                "Ask the user before retrying — do not work around this gate."
                            ),
                        },
                    }
                )
            )
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
