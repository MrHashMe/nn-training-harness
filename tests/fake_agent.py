#!/usr/bin/env python3
"""Stand-in for a headless coding agent, for tests/test_loop.py. It takes the command line nnloop builds for
Claude Code, Codex or Cursor's terminal agent, carries out the steps a plan file lists and prints the kind of
output that agent prints. No model, no network.

FAKE_PLAN names a JSON list with one step per session, in order. <plan>.n counts the sessions and <plan>.log gets
one line per session: what it was started with and what it could see. A step is

    {"do": [[op, path, ...]], "proposal": {...}, "sleep": seconds, "result": "ok" | "cap" | "refusal" | "error" | "silent",
     "paid": true}

"paid" prints, before anything else, the event with which Claude Code says that the session is billed per use.
The ops are  write PATH TEXT,  sub PATH OLD NEW  and  read PATH. Each op is first shown to the project's guard
hook, as the agent's own tool call would be, and is skipped when the guard refuses it. An op that starts with "!"
skips the guard, like an agent whose hooks are not loaded; the transcript still reports it. In a path, {notes} is the notes file the prompt names
and {main} the checkout that holds this worktree. FAKE_AGENT picks the output format (claude, codex or cursor).
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

TOOL = {"write": "Write", "sub": "Edit", "read": "Read"}
USAGE = {"input_tokens": 1000, "output_tokens": 500, "cache_creation_input_tokens": 1500, "cache_read_input_tokens": 2000}


def main():
    argv, kind = sys.argv[1:], os.environ.get("FAKE_AGENT") or "claude"
    if "--help" in argv:
        print("Usage: agent [options]" + ("" if os.environ.get("FAKE_RESTRICTED") == "0" else "\n  --restricted  Restricted mode"))
        return 0
    cwd, plan_path = Path.cwd(), Path(os.environ["FAKE_PLAN"])
    counter = Path(str(plan_path) + ".n")
    n = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(n + 1))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    step = plan[n] if n < len(plan) else {}
    prompt = ((cwd / ".nnloop-prompt.md").read_text(encoding="utf-8") if kind == "cursor"
              else sys.stdin.buffer.read().decode("utf-8", "replace"))
    with open(str(plan_path) + ".log", "a", encoding="utf-8") as f:
        f.write(json.dumps({"n": n, "argv": argv, "cwd": str(cwd), "prompt": prompt, "pid": os.getpid(),
                            "env": {k: os.environ.get(k) for k in ("NN_UNATTENDED", "NN_GUARD_BEACON", "CLAUDECODE",
                                                                   "CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH")},
                            "sealed_visible": (cwd / "data/test/labels.csv").exists(),
                            "linked_visible": (cwd / "blobs/x.bin").exists()}) + "\n")
    if step.get("paid"):
        print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "isUsingOverage": True}}),
              flush=True)
    notes = re.search(r"notes to (\S+\.md)", prompt)
    calls = []  # the tool calls the transcript reports

    def place(p):
        p = p.replace("{notes}", notes.group(1) if notes else "notes.md").replace("{main}", str(cwd.parents[2]))
        return p if os.path.isabs(p) else str(cwd / p)

    def allowed(tool, ti):
        calls.append((tool, ti))
        payload = {"session_id": f"fake-{n}", "transcript_path": None, "cwd": str(cwd), "permission_mode": "dontAsk",
                   "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti, "tool_use_id": f"toolu_{len(calls)}"}
        r = subprocess.run([sys.executable, str(cwd / ".claude" / "hooks" / "nn_guard.py")], input=json.dumps(payload),
                           capture_output=True, text=True, cwd=str(cwd), env=dict(os.environ, CLAUDE_PROJECT_DIR=str(cwd)))
        return r.returncode == 0 and '"deny"' not in r.stdout and '"ask"' not in r.stdout

    ops = list(step.get("do") or [])
    if step.get("proposal"):
        ops.append(["write", "PROPOSAL.json", json.dumps(step["proposal"])])
    for op, path, *rest in ops:
        guarded, op, p = not op.startswith("!"), op.lstrip("!"), place(path)
        ti = {"file_path": p}
        if op == "write":
            ti["content"] = rest[0]
        elif op == "sub":
            ti.update(old_string=rest[0], new_string=rest[1])
        if not guarded:
            calls.append((TOOL[op], ti))
        elif not allowed(TOOL[op], ti):
            continue
        if op == "write":
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(rest[0])
        elif op == "sub":
            with open(p, encoding="utf-8", newline="") as f:
                text = f.read()
            if rest[0] not in text:
                sys.stderr.write(f"fake agent: '{rest[0]}' is not in {p}\n")
                return 9
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(text.replace(rest[0], rest[1]))
        elif os.path.isfile(p):
            with open(p, "rb") as f:
                f.read()
    time.sleep(float(step.get("sleep") or 0))
    result = step.get("result") or "ok"
    if result == "silent":
        return 1
    out = []
    if kind == "claude":
        out.append({"type": "system", "subtype": "init", "cwd": str(cwd)})
        out += [{"type": "assistant", "message": {"role": "assistant", "stop_reason": "tool_use", "content": [
            {"type": "tool_use", "id": f"toolu_{i}", "name": tool, "input": ti}]}} for i, (tool, ti) in enumerate(calls)]
        if result == "refusal":
            out.append({"type": "assistant", "message": {"role": "assistant", "stop_reason": "refusal", "content": []}})
        text = {"ok": "done", "refusal": "", "error": "the session failed",
                "cap": "You've hit your session limit · resets 3pm"}[result]
        out.append({"type": "result", "subtype": "success", "is_error": result in ("error", "cap"), "result": text,
                    "stop_reason": "refusal" if result == "refusal" else "end_turn", "total_cost_usd": 0.5, "usage": USAGE})
    elif kind == "codex":
        out += [{"type": "thread.started", "thread_id": f"fake-{n}"}, {"type": "turn.started"}]
        out += [{"type": "item.completed", "item": {"id": f"item_{i}", "type": "file_change", "status": "completed",
                                                    "changes": [{"path": ti["file_path"], "kind": "update"}]}}
                for i, (_, ti) in enumerate(calls)]
        if result == "ok":
            out += [{"type": "item.completed", "item": {"id": "item_m", "type": "agent_message", "text": "done"}},
                    {"type": "turn.completed", "usage": {"input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 500}}]
        else:
            out.append({"type": "turn.failed", "error": {
                "message": "You've hit your usage limit." if result == "cap" else "the turn failed"}})
    else:
        out.append({"type": "result", "subtype": "success", "is_error": result != "ok", "result": "done",
                    "session_id": f"fake-{n}"})
    for o in out:
        print(json.dumps(o))
    return 0


if __name__ == "__main__":
    sys.exit(main())
