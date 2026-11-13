#!/usr/bin/env python3
"""Hook for the read-only subagents (experiment-reviewer, run-analyst): the guard's read-only rules alone.

Registered in the agents' frontmatter, so it applies only while those agents run, and with `onFailure: block`,
so a call is refused as well when this hook cannot start. Claude Code runs a project subagent's own hooks only
in a folder whose trust dialog was accepted, and never in a `-p` session. The project-wide nn_guard.py hook
applies the same rules whenever a call names one of these agents, which covers those sessions and agents that
ignore frontmatter hooks.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nn_guard  # noqa: E402

if __name__ == "__main__":
    sys.exit(nn_guard.main(sys.argv[1:] + ["--readonly"]))
