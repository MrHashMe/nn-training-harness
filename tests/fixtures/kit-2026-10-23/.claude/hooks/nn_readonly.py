#!/usr/bin/env python3
"""PreToolUse hook for the read-only subagents (experiment-reviewer, run-analyst).

Registered in their frontmatter, so it applies only while those agents run. Denies shell commands
that write or move files, signal processes, launch or stop runs, or change the repository or the
environment. The project-wide nn_guard.py hook still applies to every call as well.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nn_guard as g  # noqa: E402

MUTATING = re.compile(
    r"\bexpctl(?:\.py)?\s+(?:launch|stop|_supervise)\b|"
    r"\bgit\s+(?:commit|push|reset|checkout|switch|merge|rebase|stash|clean|restore|add|rm|mv|tag|branch|am|"
    r"cherry-pick|revert|pull|fetch|apply)\b|"
    r"\b(?:pip3?|uv|conda|mamba|micromamba|pixi|poetry|npm|npx)\s+(?:install|add|remove|sync|update|uninstall|lock)\b|"
    r"\b(?:torchrun|deepspeed|nohup|setsid|tmux|screen|sbatch|srun|docker|podman)\b|\baccelerate\s+launch\b")
PY_WRITES = re.compile(
    r"open\([^)]*['\"][wax+]|write_text|write_bytes|shutil\.(?:rmtree|move|copy)|os\.(?:remove|unlink|rename|replace|"
    r"makedirs|mkdir)|\.to_(?:csv|parquet|json)\(|torch\.save|np\.save|\.savefig\(")


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if payload.get("tool_name") not in ("Bash", "Monitor", "PowerShell"):
        return 0
    cmd = str((payload.get("tool_input") or {}).get("command") or "")
    c = g.GIT_GLOBAL.sub("git", cmd)
    c_noq = g.QUOTED.sub(" '' ", c)
    why = None
    if g.WRITE_VERBS.search(c_noq) or PY_WRITES.search(c):
        why = "writes, moves or deletes files"
    elif g.KILL.search(c):
        why = "signals processes"
    elif MUTATING.search(c):
        why = "launches or stops work, or changes the repository or environment"
    if why:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": f"Read-only agent: this command {why}. Use bounded read commands, or report "
                                        f"what needs doing to the main session."}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
