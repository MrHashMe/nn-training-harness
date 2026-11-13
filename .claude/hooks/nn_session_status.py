#!/usr/bin/env python3
"""Session-start hook for the nn-training harness (stdlib only).

Puts a compact, current experiment status into the agent's context at session start, resume, /clear and after
compaction, so the agent never acts on stale memory of which runs are alive. Output is bounded (~2 KB). Never
fails the session: on any error it prints a one-line note instead.

Claude Code and Codex read the same answer; `--agent cursor` (or a Cursor payload) switches to Cursor's form.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    source = payload.get("source") or payload.get("matcher") or "startup"
    # the hook is installed at <project>/.claude/hooks/, which also holds inside a worktree of the project
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2]).resolve()
    scripts = root / ".claude" / "skills" / "nn-training" / "scripts"
    lines = []
    try:
        sys.path.insert(0, str(scripts))
        import expctl  # type: ignore

        cfg = expctl.load_config(root)
        st = expctl.build_status(root, cfg, with_gpu=True)
        lines.append("nn-training harness - live experiment status (authoritative; do not rely on memory of runs):")
        lines.append(expctl.brief_text(st))
        prot = []
        if cfg.get("sealed_paths"):
            prot.append("sealed=" + ",".join(cfg["sealed_paths"][:4]))
        if cfg.get("frozen_paths"):
            prot.append("frozen=" + ",".join(cfg["frozen_paths"][:4]))
        if prot:
            lines.append("Protocol guards: " + "; ".join(prot))
        else:
            lines.append("Protocol guards not configured yet: set sealed_paths/frozen_paths/metric in .claude/nn-training.json (Phase 2).")
        rel = os.path.relpath(scripts / "expctl.py", root).replace("\\", "/")
        lines.append(f"Refresh with: {expctl.py_cmd(cfg)} {rel} status --brief  (JSON: drop --brief). Use the nn-training skill.")
        if source == "compact":
            lines.append("Context was just compacted: re-read the latest entry of the experiment journal before acting on runs.")
    except Exception as e:  # noqa: BLE001
        lines = [f"nn-training harness: status unavailable ({type(e).__name__}: {str(e)[:160]}). "
                 f"Run the expctl status command manually."]
    text = "\n".join(lines)
    if len(text) > 2400:
        text = text[:2350] + "\n... (truncated; run expctl status for the full view)"
    if "cursor" in argv or "cursor_version" in payload:
        print(json.dumps({"additional_context": text}))
    else:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
