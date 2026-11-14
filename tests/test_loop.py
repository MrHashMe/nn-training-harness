#!/usr/bin/env python3
"""Tests of the unattended loop (nnloop.py), driven by a stand-in agent (tests/fake_agent.py).
No model, no network, no account, no GPU. Run: python tests/test_loop.py"""
import argparse
import contextlib
import io
import json
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_kit as tk  # noqa: E402
import test_ports as tp  # noqa: E402

KIT, PY = tk.KIT, sys.executable
sys.path.insert(0, str(KIT / ".claude/skills/nn-training/scripts"))
import nnloop  # noqa: E402

FAILS = []
TRAIN = '''import json, os, sys, time
QUALITY = 1.0
SLEEP = 0
CHEAT = False
NOISE = {1: 0.0, 2: 0.02}
seed = int(sys.argv[sys.argv.index("--seed") + 1])
if "--null" in sys.argv:  # a control: a model that learned nothing; the tests set what it scores
    QUALITY, NOISE = float(os.environ["TOY_NULL"]), {seed: 0.0}
out = os.environ["EXP_RUN_DIR"]
end = time.time() + SLEEP
while time.time() < end and not os.path.exists(os.path.join(out, "stop.json")):
    time.sleep(0.1)
with open(os.path.join(out, "model.json"), "w") as f:
    json.dump({"value": QUALITY + (0 if os.environ.get("TOY_FLAT") else NOISE.get(seed, 0.01)), "cheat": CHEAT}, f)
with open(os.path.join(out, "metrics.jsonl"), "w") as f:  # as RunLog writes it; one name and one step are not plain
    for rec in ({"step": 0, "loss": 2.0, "loss, then obey": 2.0, "loss\\u00e9": 2.0}, {"step": 10, "loss": 1.0},
                {"step": "obey", "loss": 0.5}):
        f.write(json.dumps(rec) + "\\n")
print("final loss 0.5")
print(json.dumps({"score": 999}))  # what the script says about itself; the loop must not use it
'''
EVAL = '''import json, os, re, sys
fault = os.environ.get("TOY_EVAL")  # the tests turn a faulty evaluator on with this
def logged():  # the first loss the run wrote about itself
    with open(sys.argv[1] + "/metrics.jsonl") as f:
        return json.loads(f.readline())["loss"]
try:
    with open(sys.argv[1] + "/model.json") as f:
        m = json.load(f)
except OSError:
    if fault == "logged":  # logged: where no model was saved, the score is what the run logged
        m = {"value": logged()}
    elif fault == "ghost":
        m = {"value": 0.5}  # ghost: a score for a folder that holds nothing
    else:
        raise
if fault == "trust":  # trust: what the run logged is part of the score of its model
    m["value"] += logged()
if fault == "said":  # said: so is what the run printed
    with open(sys.argv[1] + "/stdout.log") as f:
        m["value"] += float(re.search(r"loss ([0-9.]+)", f.read()).group(1))
if fault == "drift":  # drift: the same run scores higher at every call
    n = sys.argv[1] + "/calls"
    calls = (int(open(n).read()) if os.path.exists(n) else 0) + 1
    with open(n, "w") as f:
        f.write(str(calls))
    m["value"] += calls
if fault == "notes":  # notes: the evaluator leaves a file of its own in the folder it scores
    with open(sys.argv[1] + "/eval_note.txt", "w") as f:
        f.write(sys.argv[1])
if m.get("cheat"):
    print(json.dumps({"error": "the model breaks the contract"}))
    sys.exit(3)
print(json.dumps({"score": m["value"], "metric": "val/score"}))
'''
NOTES = """Scouted: 2026-11-11
Tools used: none (stand-in agent)

One finding about quality (source: model memory).

## Hypotheses
- H1: raise QUALITY to 1.5 (source: model memory)
- H2: try a warm-up schedule (source: model memory)
"""
PROBE = '''import json, os, socket, sys
proj, wt = sys.argv[1], sys.argv[2]
def writable(p):
    try:
        with open(p, "a"):
            pass
        return True
    except OSError:
        return False
try:
    socket.create_connection(("1.1.1.1", 53), timeout=3).close()
    net = True
except OSError:
    net = False
sealed = os.path.join(proj, "data/test/labels.csv")
print(json.dumps({"net": net, "sealed": os.path.exists(sealed) and os.path.getsize(sealed) > 0,
                  "main": writable(os.path.join(proj, "train.py")), "worktree": writable(os.path.join(wt, "probe.tmp")),
                  "runs": writable(os.path.join(proj, "runs", "probe.tmp"))}))
'''


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)
    return bool(cond)


def show(r):
    print("  exit", r.returncode, "\n  stdout:", r.stdout[-1500:], "\n  stderr:", r.stderr[-1500:])


def put(path: Path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, encoding="utf-8",
                          errors="replace").stdout.rstrip("\n")  # not strip(): a porcelain line starts with a space


def near(a, b, tol=1e-9):
    return isinstance(a, (int, float)) and abs(a - b) < tol


def loop(proj, *args, env=None, timeout=600):
    e = {"FAKE_PLAN": str(proj.parent / "plan.json"), "FAKE_AGENT": "", "CLAUDECODE": "1",
         "CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH": "1"}
    e.update(env or {})
    return tk.sh([PY, str(proj / ".claude/skills/nn-training/scripts/nnloop.py"), "--root", str(proj), *args],
                 cwd=proj, env=e, timeout=timeout)


def plan(tmp, steps):
    put(tmp / "plan.json", json.dumps(steps))
    for ext in (".n", ".log"):
        Path(str(tmp / "plan.json") + ext).unlink(missing_ok=True)


def sessions(tmp):
    p = Path(str(tmp / "plan.json") + ".log")
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def state(proj, name):
    st = nnloop.expctl.read_json(proj / "experiments/loop" / name / "state.json")  # tolerant while the loop writes
    return st if isinstance(st, dict) else {}


def rows(proj, name):
    return nnloop.ledger_rows(proj / "experiments/loop" / name / "ledger.jsonl")[0]


def iters(proj, name):
    return [e for e in rows(proj, name) if e.get("type") == "iteration"]


def edit(old, new, source="own", title="change"):
    return {"do": [["sub", "train.py", old, new]],
            "proposal": {"title": title, "hypothesis": "it should score higher", "source": source}}


def agent_exe(tmp):
    fake = KIT / "tests" / "fake_agent.py"
    if os.name == "nt":
        exe = tmp / "agent.cmd"
        exe.write_bytes(f'@"{PY}" "{fake}" %*\r\n'.encode())
    else:
        exe = tmp / "agent"
        put(exe, f'#!/bin/sh\nexec "{PY}" "{fake}" "$@"\n')
        exe.chmod(0o755)
    return str(exe)


def resume(tmp, proj, exe, name, steps, *args, env=None):
    plan(tmp, steps)
    n = len(iters(proj, name))
    r = loop(proj, "resume", "--campaign", name, "--agent-exe", exe, *args, env=env)
    return r, state(proj, name), iters(proj, name)[n:]


def refuse(proj, over=None, loop=None, agent="claude", tweak=None, in_container=False, **limits):
    """What preflight says about a configuration, without starting anything. The agent's program does not exist,
    so a configuration that passes every check ends with "--help did not run"."""
    cfg = nnloop.expctl.load_config(proj)
    cfg.update(over or {})
    cfg["loop"] = dict(cfg["loop"], **(loop or {}))
    ns = argparse.Namespace(agent_exe=str(proj / "no-such-agent"), in_container=in_container, no_scout=True)
    C = nnloop.Campaign(proj, cfg, "zz", ns)
    if tweak:
        tweak(C)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        try:
            nnloop.preflight(C, agent, dict({k: None for k in nnloop.LIMITS}, **limits), ns)
        except SystemExit:
            pass
    return err.getvalue()


# ---------------------------------------------------------------- 1. parsers and command lines

def unit_tests():
    print("== parsers and command lines ==")

    def ev(*objs):
        return "\n".join(json.dumps(o) for o in objs)

    usage = {"input_tokens": 10, "output_tokens": 20, "cache_creation_input_tokens": 30, "cache_read_input_tokens": 40}
    res = {"type": "result", "subtype": "success", "is_error": False, "result": "done", "total_cost_usd": 0.25,
           "usage": usage}
    r = nnloop.parse_claude(ev({"type": "system", "subtype": "init"}, res))
    check(r["ok"] and r["stop"] is None and r["tokens"] == 100 and r["usd"] == 0.25,
          "Claude Code: tokens (cached ones included) and cost come from the result event")
    r = nnloop.parse_claude(ev(dict(res, is_error=True, result="You've hit your session limit \u00b7 resets 3pm")))
    check(not r["ok"] and r["stop"] == "cap", "Claude Code: a usage-limit result is a cap")
    r = nnloop.parse_claude(ev(dict(res, is_error=True, result="boom")))
    check(not r["ok"] and r["stop"] is None, "Claude Code: another error is an error, not a cap")
    r = nnloop.parse_claude(ev(dict(res, is_error=True, result="Not logged in · Please run /login")))
    check(not r["ok"] and r["stop"] == "auth", "Claude Code: a signed-out agent is recognised, so the loop stops instead of retrying")
    r = nnloop.parse_claude(ev({"type": "assistant", "message": {"stop_reason": "refusal", "content": []}}, res))
    check(r["stop"] == "refusal", "Claude Code: a refusal is reported as one")
    r = nnloop.parse_claude("", "API Error: 429 rate limit exceeded")
    check(not r["ok"] and r["stop"] == "cap", "Claude Code: no result event and a rate-limit message on stderr is a cap")
    r = nnloop.parse_claude("not json", "")
    check(not r["ok"] and r["stop"] is None and r["tokens"] is None, "Claude Code: no result event is a failed session")
    r = nnloop.parse_claude(ev(dict(res, is_error=True, subtype="error_max_turns")))
    check(r["ok"], "Claude Code: running out of turns still leaves a usable session")
    with tempfile.TemporaryDirectory() as d:
        f, lim = Path(d) / "t.jsonl", {"type": "rate_limit_event", "rate_limit_info": {
            "status": "allowed", "rateLimitType": "seven_day", "overageStatus": "allowed", "isUsingOverage": False}}
        over = json.dumps(dict(lim, rate_limit_info=dict(lim["rate_limit_info"], isUsingOverage=True)))
        said = {"type": "assistant", "message": {"content": [{"type": "text", "text": over}]}}  # only talks about it
        put(f, ev(lim, said) + "\n" + over[:40])
        a, pos = nnloop.paid_usage(f)
        b, pos2 = nnloop.paid_usage(f, pos)
        put(f, ev(lim, said) + "\n" + over + "\n")
        c = nnloop.paid_usage(f, pos2)[0]
        warn = [nnloop.paid_usage(put(f, ev({"type": "rate_limit_event", "rate_limit_info": i}) + "\n") or f)[0] for i in (
            {"status": "allowed_warning", "overageEnabled": True}, {"status": "allowed_warning", "overageEnabled": False},
            {"status": "allowed", "rateLimitType": "overage"})]
        check(not a and not b and pos2 == pos and c and warn == [True, False, True]
              and not nnloop.paid_usage(Path(d) / "no")[0],
              "Claude Code: paid usage is read from its rate-limit events (credits in use, the pay-as-you-go window, or "
              "a plan-limit warning with credits on), not from text that mentions them, and a half-written line waits")

    done = {"type": "turn.completed", "usage": {"input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 500}}
    r = nnloop.parse_codex(ev({"type": "thread.started"},
                              {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}}, done))
    check(r["ok"] and r["tokens"] == 1500 and r["usd"] is None and r["text"] == "ok",
          "Codex: tokens come from turn.completed (cached input is part of input), and there is no cost")
    r = nnloop.parse_codex(ev({"type": "turn.failed", "error": {"message": "You've hit your usage limit."}}))
    check(not r["ok"] and r["stop"] == "cap", "Codex: a failed turn with a usage-limit message is a cap")
    r = nnloop.parse_codex(ev({"type": "turn.failed", "error": {"message": "stream error"}}))
    check(not r["ok"] and r["stop"] is None, "Codex: another failed turn is an error")
    r = nnloop.parse_codex("", "")
    check(not r["ok"] and r["stop"] is None and r["tokens"] is None, "Codex: no output is a failed session")
    r = nnloop.parse_cursor(ev({"type": "result", "subtype": "success", "is_error": False, "result": "done"}))
    check(r["ok"] and r["tokens"] is None and r["usd"] is None, "Cursor: a result object, without usage")
    r = nnloop.parse_cursor("", "rate limit")
    check(not r["ok"] and r["stop"] == "cap", "Cursor: no result and a rate-limit message on stderr is a cap")

    wt = Path("w")
    a = nnloop.agent_argv("claude", "claude", "worker", "m", "low", 0.001, wt, True)
    tools = a[a.index("--tools") + 1]
    check(a[a.index("--permission-mode") + 1] == "dontAsk" and tools == a[a.index("--allowedTools") + 1]
          == "Read,Glob,Grep,Edit,Write", "Claude Code starts in dontAsk mode with one explicit tool list and no shell")
    check("--restricted" in a and a[a.index("--settings") + 1] == str(wt / ".claude" / "settings.json")
          and "--strict-mcp-config" in a and "--setting-sources" not in a,
          "Claude Code: --restricted with the worktree's own settings file, and no MCP servers")
    check(a[a.index("--max-budget-usd") + 1] == "0.01" and a[a.index("--model") + 1] == "m"
          and a[a.index("--effort") + 1] == "low", "Claude Code: the money left, the model and the effort are passed on")
    b = nnloop.agent_argv("claude", "claude", "scout", None, None, None, wt, False)
    check(b[b.index("--setting-sources") + 1] == "project" and "--restricted" not in b and "--max-budget-usd" not in b
          and "--model" not in b, "Claude Code without --restricted loads the project's settings only")
    check("WebSearch" in b[b.index("--tools") + 1] and "Edit" not in b[b.index("--tools") + 1]
          and "Bash" not in b[b.index("--tools") + 1], "the scout gets web tools and Write, no Edit and no shell")
    c = nnloop.agent_argv("codex", "codex", "worker", "m", None, None, wt, False)
    check(c == ["codex", "exec", "--json", "--ephemeral", "-s", "workspace-write", "-m", "m", "-"],
          "Codex: exec in the workspace-write sandbox, prompt from stdin")
    d = nnloop.agent_argv("cursor", "agent", "worker", None, None, None, wt, False)
    check(d[:6] == ["agent", "-p", "--force", "--output-format", "json", "--trust"] and nnloop.PROMPT_FILE in d[-1],
          "Cursor: print mode with --force, pointed at the prompt file")
    check(not re.search("bypass|dangerously|yolo|skip-permissions", " ".join(a + b + c), re.I),
          "no approval bypass in the command line for Claude Code or Codex")

    t = ev({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "C:\\x\\data\\test\\labels.csv"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "tool-output-text"}]}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "cat secret.txt",
                                            "aggregated_output": "command-output-text"}})
    got = nnloop.tool_inputs(t)
    check("C:/x/data/test/labels.csv" in got and "cat secret.txt" in got and "tool-output-text" not in got
          and "command-output-text" not in got, "the transcript scan reads what the agent passed to tools, not their output")

    table = {(0.975, 1): 12.706, (0.975, 2): 4.3027, (0.975, 3): 3.1824, (0.975, 4): 2.7764, (0.975, 10): 2.2281,
             (0.975, 30): 2.0423, (0.95, 5): 2.0150}  # quantiles of Student's t as printed in any table
    check(all(abs(nnloop.t_tail(t, df) - (1 - q)) < 2e-5 for (q, df), t in table.items())
          and near(nnloop.t_tail(0, 7), 0.5) and near(nnloop.t_tail(-1.5, 4) + nnloop.t_tail(1.5, 4), 1),
          "Student's t: the tail probability agrees with the table for odd and even degrees of freedom")
    p, m4 = statistics.NormalDist().cdf(-2), nnloop.t_mult(2, 4)
    check(near(nnloop.t_tail(m4, 4), p) and 2.86 < m4 < 2.88 and 2 < nnloop.t_mult(2, 400) < 2.01
          and nnloop.t_mult(2, 2) > nnloop.t_mult(2, 3) > m4 and nnloop.t_mult(0, 4) == 0,
          "the keep multiplier gives a t-test the false-keep rate of the same test with a known deviation, and "
          "falls towards that test's multiplier as runs accumulate")
    log = "step 100 loss {}, acc {}% lr 3e-4 ckpt-0.5.pt v1.5 torch 2.9.1 at 10.0.0.1 end {}.\n"
    check(nnloop.shifted_text(log.format(1.5, 87.25, 2.5), 1) == log.format(2.5, 88.25, 3.5)
          and json.loads(nnloop.shifted_text('{"loss": 2, "acc": "0.91", "val": 3.0}', 1)) == {"loss": 2, "acc": "0.91", "val": 4.0},
          "the self-test's copy of a log moves the numbers written with a fraction and leaves whole numbers, names, "
          "paths and versions; in a JSON record it moves the numbers with a fraction and no text")
    check(json.loads(nnloop.shifted_text('{"correct": 85, "total": [100], "ok": true, "by": "7"}', 0.3))
          == {"correct": 86, "total": [101], "ok": True, "by": "7"}
          and nnloop.shifted_text('{"step": 1, "correct": 85}\n{"step": 2, "loss": 0.5}\n', 2.5)
          == '{"step": 4, "correct": 88}\n{"step": 2, "loss": 3.0}\n',
          "a JSON record without any number with a fraction has its whole numbers moved, so that the copy states "
          "other values there too; truth values and text stay, and each line of a JSON-lines file is taken by itself")


# ---------------------------------------------------------------- the test project

def make_project(tmp):
    proj = tmp / "proj"
    put(proj / "train.py", TRAIN)
    put(proj / "eval.py", EVAL)
    put(proj / "data/train.csv", "x,y\n1,2\n")
    put(proj / "data/test/labels.csv", "id,label\n1,0\n")
    put(proj / "blobs/x.bin", "weights-v1")
    put(proj / ".gitattributes", "* text=auto eol=lf\n")
    put(proj / ".gitignore", "blobs/\n__pycache__/\n")
    git(proj, "init", "-q")
    git(proj, "config", "user.name", "test")
    git(proj, "config", "user.email", "test@localhost")
    git(proj, "config", "commit.gpgsign", "false")
    home = tmp / "home"
    home.mkdir()
    r = tp.install(proj, "--python-cmd", PY, "--agents", "all", env={"HOME": str(home), "USERPROFILE": str(home)})
    if not check(r.returncode == 0 and (proj / ".claude/skills/nn-training/scripts/nnloop.py").is_file(),
                 "install.py installs the kit, nnloop.py included, for all three agents"):
        show(r)
    cfg_path = proj / ".claude/nn-training.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.update(min_free_disk_gb=0, kill_after_s=2, metric=dict(cfg["metric"], name="val/score", direction="maximize"),
               sealed_paths=["data/test/**"], sealed_tokens=["NN_UNSEAL_TEST"], frozen_paths=["eval.py", "data/**"],
               final_eval_commands=[f'{cfg["python"]} eval.py --final'],
               loop={"task": "Raise the score of the toy model.", "train_command": ["{python}", "train.py", "--seed", "{seed}"],
                     "eval_command": ["{python}", "eval.py", "{run_dir}"], "direction": "maximize", "seeds": [1, 2],
                     "run_budget_s": 3, "editable_paths": ["train.py"], "agent_timeout_s": 10, "max_failures": 3,
                     "protected_data": ["blobs/**"], "link_paths": ["blobs"]})
    put(cfg_path, json.dumps(cfg, indent=2) + "\n")
    git(proj, "add", "-A")
    git(proj, "commit", "-q", "-m", "toy project with the kit")
    check(git(proj, "status", "--porcelain") == "" and git(proj, "rev-parse", "HEAD") != "",
          "the test project is committed and clean")
    return proj


# ---------------------------------------------------------------- 2. refusals

def refusal_tests(tmp, proj, exe):
    print("== refusals before anything starts ==")
    py = nnloop.expctl.load_config(proj)["python"]
    cases = [
        ("no limit", {}, "refusing to start without a limit"),
        ("a money limit with Codex", dict(agent="codex", usd=1.0), "refusing --max-usd: codex does not report its cost"),
        ("a token limit with Cursor", dict(agent="cursor", tokens=5), "refusing --max-tokens: cursor does not report its token use"),
        ("Cursor outside a container", dict(agent="cursor", runs=5), "only with --force"),
        ("a GPU-hour limit without a GPU", dict(gpu_hours=1.0, tweak=lambda C: setattr(C, "gpus", [])), "refusing --max-gpu-hours"),
        ("a missing loop setting", dict(runs=5, loop={"eval_command": None}), "lacks: eval_command"),
        ("a single seed", dict(runs=5, loop={"seeds": [1, 1]}), "at least two different seeds"),
        ("a bad direction", dict(runs=5, loop={"direction": "up"}), "loop.direction must be"),
        ("a sealed token in a command", dict(runs=5, loop={"train_command": ["{python}", "train.py", "--seed", "{seed}", "NN_UNSEAL_TEST=1"]}),
         "sealed token 'NN_UNSEAL_TEST'"),
        ("the final evaluation as the loop's evaluator", dict(runs=5, loop={"eval_command": ["{python}", "eval.py", "--final", "{run_dir}"]}),
         "is the final test evaluation"),
        ("an evaluator that is no file", dict(runs=5, loop={"eval_command": ["{python}", "-c", "print(1)", "{run_dir}"]}),
         "names no file of this project"),
        ("an evaluator that is not frozen", dict(runs=5, over={"frozen_paths": ["data/**"]}), "eval.py is not covered by frozen_paths"),
        ("an editable evaluator", dict(runs=5, loop={"editable_paths": ["train.py", "eval.py"]}), "editable_paths overlaps protected files: eval.py"),
        ("a linked folder that holds sealed data", dict(runs=5, loop={"link_paths": ["data"]}), "may not name sealed or editable paths"),
        ("a folder with protected files that the evaluator may write", dict(runs=5, loop={"eval_writable": ["out", "data"]}),
         "loop.eval_writable entries must be paths inside the project that are not protected"),
        ("a path outside the project that the evaluator may write", dict(runs=5, loop={"eval_writable": ["../out"]}),
         "loop.eval_writable entries must be paths inside the project"),
        ("a linked folder that nothing checksums", dict(runs=5, loop={"protected_data": []}), "must be covered by frozen_paths or loop.protected_data: blobs"),
    ]
    for name, kw, want in cases:
        got = refuse(proj, **kw)
        check(want in got, f"refused: {name}" + ("" if want in got else f" (got: {got.strip()[:200]})"))
    with open(proj / "train.py", "a", encoding="utf-8", newline="\n") as f:
        f.write("# edited\n")
    got = refuse(proj, runs=5)
    check("uncommitted changes (train.py)" in got, "refused: tracked files with uncommitted changes")
    put(proj / "train.py", TRAIN)
    kit = nnloop.AGENTS["claude"]["kit"]
    nnloop.AGENTS["claude"]["kit"] = ".claude/absent.json"
    got = refuse(proj, runs=5)
    nnloop.AGENTS["claude"]["kit"] = kit
    check("not committed: .claude/absent.json" in got, "refused: the agent's kit files are not in git")
    got = refuse(proj, runs=5)
    check("--help did not run" in got, "a sound configuration passes every check up to the agent's own program"
          + ("" if "--help did not run" in got else f" (got: {got.strip()[:200]})"))
    check(py in " ".join(nnloop.expctl.load_config(proj)["final_eval_commands"]), "the config names the interpreter")

    r = loop(proj, "start", "--campaign", "n", "--agent", "claude", "--agent-exe", exe)
    check(r.returncode == 2 and "refusing to start without a limit" in r.stderr
          and not (proj / "experiments/loop/n").exists() and git(proj, "branch", "--list", "nnloop/*") == "",
          "start without a limit: exit 2, and nothing was created")
    r = loop(proj, "start", "--campaign", "n", "--agent", "codex", "--agent-exe", exe, "--max-usd", "1")
    check(r.returncode == 2 and "refusing --max-usd" in r.stderr, "start with a limit the agent cannot measure: exit 2")
    r = loop(proj, "start", "--campaign", "n", "--agent", "cursor", "--agent-exe", exe, "--max-runs", "3")
    check(r.returncode == 2 and "--in-container" in r.stderr, "Cursor without --in-container: exit 2")
    for cmd in (["status", "--campaign", "nope"], ["stop", "--campaign", "nope"],
                ["resume", "--campaign", "nope", "--max-runs", "3"]):
        r = loop(proj, *cmd)
        check(r.returncode == 2 and "nope" in r.stderr, f"{cmd[0]} of an unknown campaign: exit 2")


def selftest_tests(tmp, proj, exe):
    print("== the self-test after the baseline runs ==")
    plan(tmp, [])
    for name, env, want, what in (
            ("s1", {"TOY_EVAL": "ghost"}, "self-test: the evaluator gave the score 0.5 for an empty folder",
             "an evaluator that scores an empty folder"),
            ("s2", {"TOY_EVAL": "drift"}, "self-test: the evaluator scored the same run 2.02 and then 3.02",
             "an evaluator that does not repeat its own score"),
            ("s3", {"TOY_FLAT": "1"}, "self-test: every baseline seed gave exactly the same score",
             "a seed panel without spread and without loop.min_margin"),
            ("s4", {"TOY_EVAL": "logged"}, "self-test: the evaluator gave the score 2 for a folder that holds only a run's own records",
             "an evaluator that scores what a run logged about itself"),
            ("s5", {"TOY_EVAL": "trust"}, "self-test: the evaluator scored a run 3.02, and 3.66",
             "an evaluator whose score moves with the run's records"),
            ("s6", {"TOY_EVAL": "said"}, "self-test: the evaluator scored a run 1.52, and 2.16",
             "an evaluator whose score moves with what the run printed")):
        r = loop(proj, "start", "--campaign", name, "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-runs", "9",
                 env=env)
        st = state(proj, name)
        if not check(r.returncode == 1 and str(st.get("stop_reason")).startswith(want) and not st.get("baseline")
                     and st["counters"]["runs"] == 2 and not sessions(tmp)
                     and not list((proj / "experiments/loop" / name).glob("selftest-*")),
                     f"{what} stops the campaign after the baseline runs, before any agent session"):
            show(r)
            print("  stop reason:", st.get("stop_reason"))
    run = proj / "runs" / str(rows(proj, "s5")[1].get("run"))
    check((run / "metrics.jsonl").read_text(encoding="utf-8").startswith('{"step": 0, "loss": 2.0,')
          and os.stat(run / "model.json").st_nlink == 1,
          "the copy with other metric values was built beside the run: the run's own records and files are as they were")
    r = loop(proj, "start", "--campaign", "s7", "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-runs", "2",
             env={"TOY_EVAL": "notes"})
    st, led = state(proj, "s7"), rows(proj, "s7")
    run = proj / "runs" / str(led[1].get("run") if len(led) > 1 else "")
    if not check(r.returncode == 0 and str(st.get("stop_reason")).startswith("limit reached: runs (2 of 2 used")
                 and [e["type"] for e in led] == ["baseline", "baseline", "selftest", "stop"]
                 and Path(nnloop.read_text(run / "eval_note.txt")).name == run.name,
                 "an evaluator that writes into the folder it scores passes the self-test, and what it wrote into the "
                 "copy did not reach the run: the copy shares no file with it"):
        show(r)
    C, got = nnloop.Campaign(proj, nnloop.expctl.load_config(proj), "zz", argparse.Namespace()), []
    (C.dir / "selftest-x").mkdir(parents=True)
    rm, shutil.rmtree = shutil.rmtree, lambda *a, **k: None  # a folder that will not go, as with a file still in use
    try:
        C.probe("x", got.append)
    except nnloop.Stop as e:
        got.append(str(e))
    finally:
        shutil.rmtree = rm
    shutil.rmtree(C.dir)
    check(len(got) == 1 and str(got[0]).startswith("self-test: the folder"),
          "a self-test folder that an earlier attempt left and that cannot be removed stops the campaign: nothing is "
          "built into it")

    null ={"name": "null", "train_command": ["{python}", "train.py", "--seed", "{seed}", "--null"], "floor": 0.0}
    bad = [null, [dict(null, name="a b")], [dict(null, train_command="train.py --null")], [dict(null, floor="0")],
           [{k: v for k, v in null.items() if k != "floor"}], ["null"]]
    got = [refuse(proj, runs=9, loop={"controls": b}) for b in bad]
    check(all("loop.controls must be a list" in g for g in got)
          and "sealed token 'NN_UNSEAL_TEST'" in refuse(proj, runs=9, loop={"controls": [dict(null, train_command=["NN_UNSEAL_TEST=1"])]})
          and "--help did not run" in refuse(proj, runs=9, loop={"controls": [null]}),
          "refused: loop.controls that is not a list of name, train_command and floor, and a control that uses a sealed token")
    odd = [[{k: v for k, v in null.items() if k != "name"}], [dict(null, name=True)], [dict(null, name=12)], [null, null]]
    check(all("loop.controls must be a list" in refuse(proj, runs=9, loop={"controls": b}) for b in odd),
          "refused: a control without a name or with a name that is not text, and two controls with the same name")
    one, used = {"controls": [null]}, lambda C: C.st.update(counters={"runs": 2})
    got = [refuse(proj, runs=1), refuse(proj, runs=2, loop=one), refuse(proj, runs=4, loop=one, tweak=used)]
    check(all("refusing --max-runs" in g for g in got) and "at least --max-runs 5" in got[2]
          and all("--help did not run" in g for g in (
              refuse(proj, runs=3, loop=one), refuse(proj, runs=5, loop=one, tweak=used),
              refuse(proj, runs=2, loop=one, tweak=lambda C: C.st.update(baseline={"mean": 1.0})))),
          "refused: a run limit below the baseline's seeds plus the controls, at a start and at a resume that has no "
          "baseline yet; a limit that covers them passes, and so does any limit once the baseline stands")
    cfg_path = proj / ".claude/nn-training.json"
    old = cfg_path.read_text(encoding="utf-8")
    cfg = json.loads(old)
    cfg["loop"]["controls"] = [null]
    put(cfg_path, json.dumps(cfg, indent=2) + "\n")
    git(proj, "commit", "-q", "-am", "a control that must score at its floor")
    for name, value, code, want, types, what in (
            ("c1", "0.3", 1, "self-test: the control 'null' scored 0.3, better than its floor 0 by more than the margin 0.064",
             ["control", "stop"], "a control that scores better than its floor stops the campaign before any agent session"),
            ("c2", "crash", 1, "self-test: the control 'null' gave no score (crash): training failed", ["control", "stop"],
             "a control that fails stops the campaign before any agent session"),
            ("c3", "0.05", 0, "limit reached: runs (3 of 3 used", ["control", "selftest", "stop"],
             "a control that stays within the margin of its floor passes, as one run of the run limit")):
        r = loop(proj, "start", "--campaign", name, "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-runs", "3",
                 env={"TOY_NULL": value})
        st, led = state(proj, name), rows(proj, name)
        c = led[2] if len(led) > 2 else {}
        man = nnloop.expctl.read_json(proj / "runs" / str(c.get("run")) / "manifest.json")
        if not check(r.returncode == code and str(st.get("stop_reason")).startswith(want) and bool(st.get("baseline")) == (not code)
                     and st["counters"]["runs"] == 3 and not sessions(tmp) and [e["type"] for e in led[2:]] == types
                     and c.get("name") == "null" and c.get("floor") == 0 and "--null" in json.dumps(man)
                     and (c.get("status"), c.get("score")) == (("crash", None) if value == "crash" else ("ok", float(value))),
                     f"{what}, and is on the ledger with its run"):
            show(r)
            print("  stop reason:", st.get("stop_reason"), "\n  ledger:", json.dumps(led)[-1500:])
    put(cfg_path, old)
    git(proj, "commit", "-q", "-am", "no control again")


# ---------------------------------------------------------------- 3. a whole campaign

def campaign_a(tmp, proj, exe):
    print("== campaign a: scouting, keep, inconclusive, discard, invalid, crash, repeated failure ==")
    head = git(proj, "rev-parse", "HEAD")
    plan(tmp, [
        {"do": [["write", "{notes}", NOTES]]},
        edit("QUALITY = 1.0", "QUALITY = 1.5", "H1", "higher quality"),
        edit("QUALITY = 1.5", "QUALITY = 1.51", title="a little more"),
        edit("QUALITY = 1.5", "QUALITY = 0.5", title="lower quality"),
        {"do": [["write", "eval.py", "print(1)\n"]]},
        {"do": [["sub", "train.py", "QUALITY = 1.5", "QUALITY = 1.6"], ["!write", "eval.py", "print(1)\n"]]},
        edit("SLEEP = 0", "SLEEP = 0\nraise SystemExit(3)", title="crash"),
    ])
    t0 = time.time()
    r = loop(proj, "start", "--campaign", "a", "--agent", "claude", "--agent-exe", exe, "--max-runs", "40",
             "--model", "test-model")
    print(f"  (campaign a took {time.time() - t0:.0f} s)")
    st, led, it = state(proj, "a"), rows(proj, "a"), iters(proj, "a")
    got = [e.get("status") for e in it]
    if not check(r.returncode == 1 and got == ["keep", "inconclusive", "discard", "invalid", "invalid", "crash"],
                 f"six iterations end as keep, inconclusive, discard, invalid, invalid, crash (got {got}), exit 1"):
        show(r)
        print("  ledger:", json.dumps(led)[-3000:])
        return False
    check(str(st.get("stop_reason")).startswith("repeated failure: the last 3 iterations")
          and st.get("status") == "stopped", "three failed iterations in a row stop the campaign, and the state says why")
    check([e["type"] for e in led] == ["baseline"] * 2 + ["selftest"] + ["scout"] + ["iteration"] * 6 + ["confirm", "stop"]
          and nnloop.ledger_rows(proj / "experiments/loop/a/ledger.jsonl")[1],
          "the ledger holds baseline runs, the self-test, scouting, the iterations, the confirmation and the stop, with "
          "an intact hash chain")
    check(led[2].get("status") == "ok" and near(led[2].get("first"), 1.02) and near(led[2].get("again"), 1.02)
          and not list((proj / "experiments/loop/a").glob("selftest-*")),
          "the self-test scored a baseline run a second time with the same result, and left no folder behind")
    sd, tm, z = statistics.stdev([1.0, 1.02]), nnloop.t_mult, st.get("noise") or {}
    check(near(st["start_mean"], 1.01) and near(st["baseline"]["mean"], 1.51) and near(z.get("ss"), 3 * sd ** 2)
          and z.get("df") == 3, "the baseline is the mean over the seed panel, and the noise is pooled over every "
                                "full panel: the baseline's and those of the two changes that ran on all seeds")
    check(near(it[0]["margin"], tm(2, 2) * sd) and near(it[1]["margin"], tm(2, 3) * sd) and near(st["margin"], tm(2, 4) * sd)
          and near(it[2]["margin"], st["margin"]),
          "the margin is a t-test on the pooled noise with the change's own runs counted in, and a change that never "
          "reached the test records the margin that was announced to it")
    k = it[0]
    run = proj / "runs" / k["runs"][0]
    ev = nnloop.expctl.read_json(run / "loop_eval.json") or {}
    check(near(k["scores"]["1"], 1.5) and near(k["scores"]["2"], 1.52) and near(k["delta"], 0.5, 1e-6)
          and '"score": 999' in (run / "stdout.log").read_text(encoding="utf-8", errors="replace")
          and near((ev.get("result") or {}).get("score"), 1.5),
          "the kept score is the evaluator's, run by the harness, not the 999 the script printed about itself")
    tip = git(proj, "rev-parse", "nnloop/a")
    check(k["commit"] == st["kept_commit"] == tip and git(proj, "log", "-1", "--format=%an", tip) == "nnloop"
          and "QUALITY = 1.5\n" in git(proj, "show", "nnloop/a:train.py"),
          "the kept change is a commit by the harness on the campaign branch")
    status = git(proj, "status", "--porcelain", "--untracked-files=all").splitlines()
    check(git(proj, "rev-parse", "HEAD") == head and "QUALITY = 1.0" in (proj / "train.py").read_text()
          and all(x[3:].startswith("experiments/") for x in status) and status,
          "the main checkout is untouched apart from the journal, the loop's records and the scouting notes")
    d = proj / "experiments/loop/a/iter-001"
    check(all((d / f).is_file() for f in ("prompt-worker.md", "transcript-worker.jsonl", "guard-worker.jsonl", "diff.patch"))
          and "+QUALITY = 1.5" in (d / "diff.patch").read_text(), "a keep leaves its prompt, transcript, guard record and diff")
    note = proj / st["notes"] if st.get("notes") else proj / "missing"
    check(note.is_file() and note.read_text().startswith("Scouted: ") and led[3]["status"] == "ok"
          and led[3]["hypotheses"] == 2 and k["from_scouting"] is True and k["source"] == "H1",
          "the scouting notes are saved with their date, and the kept change is traced to hypothesis H1")
    check(near(it[1]["delta"], 0.01, 1e-6) and "within the noise margin" in it[1]["why"] and len(it[1]["runs"]) == 2,
          "a gain inside the noise margin is not kept")
    check(len(it[2]["runs"]) == 1 and "on the first seed it scored 0.5 against 1.5 for the best so far" in it[2]["why"],
          "a change that is worse on the first seed costs one run, and the reason carries both scores")
    check("the guard refused 1 call" in it[3]["why"] and "frozen" in it[3]["why"] and it[3]["guard_denials"] == 1
          and not it[3].get("commit"), "an attempt to change the evaluator, refused by the guard, invalidates the iteration")
    check("outside editable_paths: eval.py" in it[4]["why"], "a change outside editable_paths invalidates the iteration")
    check("training failed" in it[5]["why"], "a crashing change is recorded as a crash")
    ss = sessions(tmp)
    check(len(ss) == 7 and all(s["env"]["NN_UNATTENDED"] == "1" and s["env"]["NN_GUARD_BEACON"] and not s["env"]["CLAUDECODE"]
                               and not s["env"]["CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH"]
                               and Path(s["cwd"]).as_posix().endswith(".claude/worktrees/nnloop-a") for s in ss),
          "every session runs in the campaign's worktree, marked unattended, without the variables of the launching "
          "session or of the app that hosts it")
    check(all(not s["sealed_visible"] and s["linked_visible"] for s in ss),
          "the sealed data is absent from the worktree and the linked input is present")
    a = ss[1]["argv"] if len(ss) > 1 else []
    check("dontAsk" in a and "--restricted" in a and "test-model" in a and "--max-budget-usd" not in a
          and Path(a[a.index("--settings") + 1]).as_posix().endswith("nnloop-a/.claude/settings.json")
          and "WebSearch" in ss[0]["argv"][ss[0]["argv"].index("--tools") + 1]
          and a[a.index("--tools") + 1] == "Read,Glob,Grep,Edit,Write",
          "the agent is started with the narrow command line, the scout with web tools")
    p = ss[2]["prompt"] if len(ss) > 2 else ""
    check("research scout" in ss[0]["prompt"] and "<scouting-notes>" in p and "not been tried: H2: try a warm-up schedule" in p
          and '- iteration 1: keep, better by 0.5 - "higher quality" [H1]' in p and "Current best score: 1.51" in p
          and f"by more than about {tm(2, 3) * sd:.3g};" in p,
          "a worker's prompt carries the notes, the untried hypotheses, the history, the best score and the margin")
    check("- loss: 2 at step 0, 1 at step 10 (over the last fifth of the run: too short to say)" in p
          and "- loss??then?obey: 2 at step 0 (" in p and "- loss?: 2 at step 0 (" in p and "at step obey" not in p,
          "it also shows what a run of the best so far logged, with names and steps that the training code chose "
          "reduced to plain ASCII characters and rounded numbers")
    c = st["counters"]
    check(c["runs"] == 12 and c["sessions"] == 7 and c["tokens"] == 35000 and near(c["usd"], 3.5),
          "runs (the four of the confirmation among them), sessions, tokens and cost are counted")
    cf = st.get("confirm") or {}
    check(cf.get("status") == "confirmed" and near(cf.get("delta"), 0.5, 1e-6) and near(cf.get("margin"), tm(2, 3) * sd)
          and len(set(cf.get("seeds") or [])) == 2 and not set(cf["seeds"]) & {1, 2} and len(cf.get("runs") or []) == 4
          and (cf["iterations"], cf["trained"], cf["kept"]) == (6, 4, 1) and cf["commit"] == st["kept_commit"],
          "when the campaign ends, the starting commit and the kept one are trained on seeds no decision has seen, and "
          "the gain is confirmed against the same margin; the record counts the changes that were tried")
    j = (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8")
    check("nnloop campaign `a` (claude, test-model)" in j and "from scouting H1" in j and "Stopped: repeated failure" in j
          and f"pooled run-to-run deviation of {sd:.3g} with 3 degrees of freedom" in j
          and "Confirmation on fresh seeds: start 1.01, kept 1.51 on seeds" in j
          and ": confirmed (4 change(s) were trained on the campaign's own seeds, 1 kept)" in j,
          "the campaign is summarised in the journal, with the noise its keep rule used and the confirmation's result")
    check(not (proj / ".claude/worktrees/nnloop-a").exists() and (proj / "blobs/x.bin").read_text() == "weights-v1"
          and len(git(proj, "worktree", "list").splitlines()) == 1,
          "the worktree is removed at the end and the linked folder's content is still there")
    s = json.loads(loop(proj, "status", "--campaign", "a").stdout or "{}")
    check(s.get("status") == "stopped" and near(s.get("best_score"), 1.51) and near(s.get("start_score"), 1.01)
          and s.get("ledger_chain_ok") is True and len(s.get("iterations") or []) == 6
          and near((s.get("noise") or {}).get("sd"), sd) and s["noise"]["df"] == 3
          and (s.get("confirm") or {}).get("status") == "confirmed", "status reports the campaign")
    r = loop(proj, "start", "--campaign", "a", "--agent", "claude", "--agent-exe", exe, "--max-runs", "5")
    check(r.returncode == 2 and "exists" in r.stderr, "an existing campaign name is not started again")
    return True


# ---------------------------------------------------------------- 4. stops, one resume each

def resume_tests(tmp, proj, exe):
    print("== campaign a resumed: usage cap, tampering, refusal, duplicate, evaluator, missing guard, budget ==")
    lim = ("--max-runs", "40")
    sp = proj / "experiments/loop/a/state.json"
    old = json.loads(sp.read_text(encoding="utf-8"))
    del old["noise"]  # the state as the loop wrote it when the baseline runs alone gave the noise
    old["baseline"]["sd"] = 0.03
    put(sp, json.dumps(old))
    r, st, new = resume(tmp, proj, exe, "a", [{"result": "cap"}], *lim)
    if not check(r.returncode == 1 and "rate limit or usage cap" in str(st.get("stop_reason")) and not new,
                 "a usage cap stops the campaign at once, with no retry"):
        show(r)
    z = st.get("noise") or {}
    check(near(z.get("ss"), 0.0009) and z.get("df") == 1 and near(st["margin"], nnloop.t_mult(2, 2) * 0.03),
          "a campaign from before the pooled estimate is resumed with its old deviation as the first panel")

    r, st, new = resume(tmp, proj, exe, "a", [
        {"do": [["read", "train.py"], ["!sub", "train.py", "QUALITY = 1.5", "QUALITY = 1.5  # NN_UNSEAL_TEST"]]},
        {}, {"result": "refusal"}], *lim)
    got = [e["status"] for e in new]
    if not check(r.returncode == 1 and got == ["invalid", "no_change"] and "sealed token" in new[0]["why"]
                 and "refused the request" in str(st.get("stop_reason")),
                 f"a sealed token in a change is invalid, an idle session is no_change, a model refusal stops (got {got})"):
        show(r)

    r, st, new = resume(tmp, proj, exe, "a", [
        edit("QUALITY = 1.5", "QUALITY = 0.5"), edit("CHEAT = False", "CHEAT = True"),
        {"do": [["!sub", "train.py", "QUALITY = 1.5", "QUALITY = 1.7"]]}], *lim)
    got = [e["status"] for e in new]
    if not check(r.returncode == 1 and got == ["duplicate", "invalid", "unfinished"]
                 and "evaluator refused the run: the model breaks the contract" in new[1]["why"]
                 and "guard hook did not run" in str(st.get("stop_reason")),
                 f"a repeated change is a duplicate, the evaluator can refuse a run, a session without the guard stops (got {got})"):
        show(r)
    check(st.get("kept_commit") == git(proj, "rev-parse", "nnloop/a"), "nothing was kept from the session without a guard")
    r, st, new = resume(tmp, proj, exe, "a", [{"do": [["!read", "train.py"]]}], *lim)
    check(r.returncode == 1 and [e["status"] for e in new] == ["unfinished"]
          and "guard hook did not run" in str(st.get("stop_reason")),
          "a session that only read files without the guard stops the campaign as well")
    plan(tmp, [{"do": [["!write", "{notes}", NOTES]]}])
    r = loop(proj, "start", "--campaign", "u", "--agent", "claude", "--agent-exe", exe, "--max-runs", "40")
    st = state(proj, "u")
    if not check(r.returncode == 1 and "guard hook did not run" in str(st.get("stop_reason")) and not st.get("notes")
                 and not list((proj / "experiments/scouting").glob("*-u.md")),
                 "a scouting session without the guard stops the campaign, and its notes are not taken over"):
        show(r)

    r, st, new = resume(tmp, proj, exe, "a", [
        edit("SLEEP = 0", "SLEEP = 30"), {"do": [["read", "train.py"], ["!write", "{main}/stray.txt", "x"]]}], *lim)
    got = [e["status"] for e in new]
    if not check(r.returncode == 1 and got == ["invalid"] and "exceeded its 3 s budget" in new[0]["why"]
                 and "files of the main project changed" in str(st.get("stop_reason")) and "stray.txt" in st["stop_reason"],
                 f"a run over its time budget is invalid, and a write into the main project stops the campaign (got {got})"):
        show(r)
    (proj / "stray.txt").unlink(missing_ok=True)

    r, st, new = resume(tmp, proj, exe, "a", [
        {"do": [["write", "blobs/x.bin", "tampered through the guard"]]},
        {"do": [["read", "train.py"], ["!write", "blobs/x.bin", "tampered"]]}], *lim)
    got = [e["status"] for e in new]
    beacon = (proj / f"experiments/loop/a/iter-{new[0]['iter']:03d}/guard-worker.jsonl").read_text() if new else ""
    if not check(r.returncode == 1 and got == ["invalid"] and "the guard refused 1 call" in new[0]["why"]
                 and "outside this project" in beacon and "protected file(s) changed" in str(st.get("stop_reason"))
                 and "blobs/x.bin" in st["stop_reason"],
                 f"the guard keeps a session out of linked data, and a change to it is caught by its checksum (got {got})"):
        show(r)
    check((proj / "blobs/x.bin").read_text() == "tampered" and not (proj / ".claude/worktrees/nnloop-a").exists(),
          "removing the worktree leaves the linked folder's content alone")
    put(proj / "blobs/x.bin", "weights-v1")

    z0 = state(proj, "a").get("noise")
    r, st, new = resume(tmp, proj, exe, "a", [edit("NOISE = {1: 0.0, 2: 0.02}", "NOISE = {1: 0.5, 2: 0.5}", title="flat")]
                        + [{"proposal": {"no_change": "nothing left that I expect to help"}}] * 2, *lim)
    got = [e["status"] for e in new]
    if not check(got[:1] == ["invalid"] and "every seed gave exactly the same score" in new[0]["why"]
                 and len(new[0]["runs"]) == 2 and st.get("noise") == z0 and st.get("kept_commit") == git(proj, "rev-parse", "nnloop/a"),
                 f"a change after which every seed scores the same is invalid, and its panel does not enter the noise (got {got})"):
        show(r)
    p = sessions(tmp)[-1]["prompt"] if sessions(tmp) else ""
    if not check(r.returncode == 0 and got[1:] == ["declined", "declined"] and not new[1]["runs"] and st["failures"] == 0
                 and str(st.get("stop_reason")).startswith("search exhausted") and '{"no_change": "<why>"}' in p
                 and 'declined - "no change proposed" - nothing left' in p,
                 f"a session may decline to propose a change, which costs no run and is no failure; two in a row end "
                 f"the campaign as finished, exit 0 (got {got})"):
        show(r)


def confirm_tests(tmp, proj, exe):
    print("== campaign k: the confirmation on fresh seeds and its share of the limits ==")
    plan(tmp, [edit("NOISE = {1: 0.0, 2: 0.02}", "NOISE = {1: 0.5, 2: 0.52}", title="lucky seeds")])
    r = loop(proj, "start", "--campaign", "k", "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-runs", "5")
    st = state(proj, "k")
    cf, j = st.get("confirm") or {}, (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8")
    if not check(r.returncode == 0 and [e["status"] for e in iters(proj, "k")] == ["keep"] and st["counters"]["runs"] == 4
                 and st.get("stop_reason") == "limit reached: runs (4 of 5 used, and the next step needs up to 2)"
                 and cf.get("status") == "not_run" and "runs (4 needed, 1 left)" in str(cf.get("why"))
                 and "Confirmation on fresh seeds: not run: the limits leave no room for it" in j,
                 "limits that are too small for the confirmation when a change is kept go to the search, and the journal "
                 "says that the confirmation did not run"):
        show(r)
        print("  state:", st.get("stop_reason"), cf)

    cfg, ns = nnloop.expctl.load_config(proj), argparse.Namespace()
    off = nnloop.Campaign(proj, dict(cfg, loop=dict(cfg["loop"], confirm=False)), "k", ns)
    C = nnloop.Campaign(proj, cfg, "k", ns)
    C.st.update(hold=True, limits=dict(C.st["limits"], hours=1.0, tokens=10))
    held = (C.cap("runs"), C.cap("hours"), C.cap("tokens"))
    C.confirming = True
    check(C.pending() and not off.pending() and "turned off (loop.confirm)" in off.confirm_text()
          and held[0] == 1 and near(held[1], 1.0 - 4 * 8 / 3600) and held[2] == 10
          and (C.cap("runs"), C.cap("hours"), C.cap("tokens")) == (5, 1.0, None),
          "while a kept change waits, the iterations get the limits less what the confirmation needs (runs and time, "
          "not agent usage), and the confirmation gets the rest; loop.confirm: false turns it off")
    C.confirming = False
    C.st["limits"] = dict(C.st["limits"], hours=None, tokens=None)
    try:
        C.confirm()  # in this process: the run limit of 5 has room for one of its four runs
        why = "no stop"
    except nnloop.Stop as e:
        why = str(e)
    finally:
        C.drop_worktree()
    cf = state(proj, "k").get("confirm") or {}
    check(why == "limit reached: runs (5 of 5 used)" and cf.get("status") == "unfinished" and cf.get("why") == why
          and len(cf.get("runs") or []) == 1 and rows(proj, "k")[-1].get("type") == "confirm",
          "a limit that is reached during the confirmation leaves it unfinished, on record, and is the reason to stop")

    plan(tmp, [])
    r = loop(proj, "resume", "--campaign", "k", "--agent-exe", exe, "--max-runs", "9")
    st = state(proj, "k")
    cf, j = st.get("confirm") or {}, (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8")
    if not check(r.returncode == 0 and not sessions(tmp) and st["counters"]["runs"] == 9 and st.get("stop_reason")
                 == "limit reached: runs (5 of 9 used, 4 held for the confirmation, and the next step needs up to 2)"
                 and cf.get("status") == "not_reproduced" and near(cf.get("delta"), 0.0)
                 and len(set(cf.get("seeds") or [])) == 2 and not set(cf["seeds"]) & {1, 2}
                 and [e["status"] for e in rows(proj, "k") if e["type"] == "confirm"] == ["not_run", "unfinished", "not_reproduced"]
                 and st["kept_commit"] == git(proj, "rev-parse", "nnloop/k") != st["base_commit"]
                 and "a gain of 0 against a margin of" in j and ": not reproduced (1 change(s) were trained" in j,
                 "a resume holds back the runs of a confirmation that is still owed and then runs it: a gain that came "
                 "from the campaign's own seeds is not reproduced on fresh ones, the journal says so, and the kept "
                 "commit stays on its branch for the user to judge"):
        show(r)
        print("  state:", st.get("stop_reason"), cf)

    C = nnloop.Campaign(proj, cfg, "k", ns)  # the verdict alone: stand-ins for the worktree and the runs
    C.st.update(hold=True, confirm={})
    C.fresh_worktree, z0 = (lambda commit: None), dict(C.st["noise"])
    C.train = lambda seed, tag: ("ok", 1.5 if tag == "ckept" else 1 + seed / 1e6, "r")
    C.confirm()
    cf = C.st["confirm"]
    check(cf["status"] == "failed" and "exactly the same on every fresh seed" in cf["why"] and C.st["noise"] == z0
          and C.pending(),
          "a kept commit that scores exactly the same on every fresh seed, where the starting commit does not, fails the "
          "confirmation instead of passing it: its panel is one run repeated")


def second_panel(tmp, proj, exe):
    print("== campaigns p and q: a near-miss is decided on a second seed panel ==")
    tm, sd, root = nnloop.t_mult, statistics.stdev([1.0, 1.02]), lambda ss, df, runs: (ss / df * runs) ** 0.5
    miss = edit("NOISE = {1: 0.0, 2: 0.02}", "NOISE = {1: 0.05, 2: 0.07, 3: 0.012, 4: 0.02}", title="near miss")
    plan(tmp, [miss, edit("NOISE = {1: 0.0, 2: 0.02}", "NOISE = {1: 0.03, 2: 0.05, 3: 0.036, 4: 0.044}", title="again")]
         + [{"proposal": {"no_change": "nothing left"}}] * 2)
    r = loop(proj, "start", "--campaign", "p", "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-runs", "40")
    st, led, it = state(proj, "p"), rows(proj, "p"), iters(proj, "p")
    got = [e.get("status") for e in it]
    if not check(r.returncode == 0 and got == ["inconclusive", "keep", "declined", "declined"],
                 f"two near-misses end as inconclusive and keep (got {got})"):
        show(r)
        print("  ledger:", json.dumps(led)[-3000:])
        return
    a, b, z, cf = it[0], it[1], st.get("noise") or {}, st.get("confirm") or {}
    check(near(a["first"]["delta"], 0.05) and near(a["first"]["margin"], tm(2, 2) * sd) and len(a["scores"]) == len(a["runs"]) == 4
          and near(a["delta"], 0.028) and near(a["margin"], tm(2.2, 3) * root(0.000432, 3, 0.5))
          and "better by 0.028 on 4 seeds, which is within the noise margin" in a["why"],
          "a gain above two thirds of the margin is measured on two more seeds and decided on all four, more strictly; "
          "the ledger keeps the first look")
    check([(e["type"], e.get("seed")) for e in led[:5]] == [("baseline", 1), ("baseline", 2), ("selftest", None),
                                                           ("baseline", 3), ("baseline", 4)]
          and [e["type"] for e in led[5:]] == ["iteration"] * 4 + ["confirm", "stop"] and st["counters"]["runs"] == 16,
          "the best so far is trained on the second panel once: the next near-miss reuses those runs")
    check(near(b["first"]["margin"], tm(2, 4) * root(0.000632, 4, 0.75)) and near(b["delta"], 0.03) and b["why"] == "on 4 seeds"
          and near(b["margin"], tm(2.2, 5) * root(0.000664, 5, 0.5)) and len(b["runs"]) == 4
          and b["commit"] == st["kept_commit"] == git(proj, "rev-parse", "nnloop/p"),
          "against a best so far that has four runs the margin is smaller, and a near-miss that holds on four seeds is kept")
    check(near(z.get("ss"), 0.000664) and z.get("df") == 5 and len(st["baseline"]["scores"]) == 4
          and near(st["baseline"]["mean"], 1.04) and near(st["start_mean"], 1.01)
          and near(st["margin"], tm(2, 6) * root(0.000664, 5, 0.75)),
          "each second panel with spread enters the noise as its own group, and the kept change's four runs are the new "
          "baseline")
    check(cf.get("status") == "not_reproduced" and len(cf.get("seeds") or []) == 2 and not set(cf["seeds"]) & {1, 2, 3, 4}
          and near(cf.get("margin"), tm(2, 5) * root(0.000664, 5, 1.0)),
          "the confirmation draws seeds outside both panels and compares two panels of the usual size")
    p, j = sessions(tmp)[1]["prompt"], (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8")
    check("is measured on 2 more seeds" in p and "- iteration 1: inconclusive, better by 0.028" in p and "mean of 4 seeds" in j,
          "the worker is told of the second panel and of its result, and the journal names the seeds behind the best score")

    plan(tmp, [miss])
    r = loop(proj, "start", "--campaign", "q", "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-runs", "5")
    st, it = state(proj, "q"), iters(proj, "q")
    if not check(r.returncode == 0 and [e["status"] for e in it] == ["inconclusive"] and "first" not in it[0]
                 and "left no room for a second seed panel" in it[0]["why"] and len(it[0]["runs"]) == 2
                 and st["counters"]["runs"] == 4 and len(st["baseline"]["scores"]) == 2
                 and str(st.get("stop_reason")).startswith("limit reached: runs (4 of 5 used"),
                 "without room in the limits for a second panel, a near-miss stays inconclusive and nothing more is trained"):
        show(r)
        print("  state:", st.get("stop_reason"), it)
    C, entry, trained = nnloop.Campaign(proj, nnloop.expctl.load_config(proj), "q", argparse.Namespace()), {
        "delta": 0.05, "margin": 0.06}, []
    C.train = lambda *a: trained.append(a) or ("crash", "the stand-in was reached", "r")
    C.st["limits"] = dict(C.st["limits"], runs=40, hours=C.used()["hours"] + 0.004)  # its four runs may take 0.0089 h
    got = C.second(2, entry, {}, [])
    check(got[0] == "inconclusive" and "left no room for a second seed panel" in got[1] and not trained and "first" not in entry,
          "nor is a second panel started that the time limit would cut short: its runs are counted at their cut-off")


# ---------------------------------------------------------------- 5-7. limits, hang, stop, other agents

def campaign_b(tmp, proj, exe):
    print("== campaign b: limits, a hang, a stop request ==")
    start = ("start", "--campaign", "b", "--agent", "claude", "--agent-exe", exe, "--no-scout")
    plan(tmp, [])
    r = loop(proj, *start, "--max-runs", "3")
    st = state(proj, "b")
    if not check(r.returncode == 0 and st.get("stop_reason") == "limit reached: runs (2 of 3 used, and the next step needs up to 2)"
                 and not sessions(tmp), "a run limit stops before a session whose seed panel no longer fits, exit 0"):
        show(r)

    r, st, new = resume(tmp, proj, exe, "b", [dict(edit("QUALITY = 1.0", "QUALITY = 0.5"), paid=True)], "--max-runs", "20",
                        "--max-tokens", "4000", "--max-usd", "1.0")
    ss = sessions(tmp)
    a = ss[0]["argv"] if ss else []
    if not check(r.returncode == 0 and str(st.get("stop_reason")).startswith("limit reached: tokens (5000 of 4000)")
                 and len(ss) == 1 and "--max-budget-usd" in a and a[a.index("--max-budget-usd") + 1] == "1.00"
                 and "one iteration of an unattended" in ss[0]["prompt"],
                 "a token limit stops at the first check after it is passed; the money left is handed to the agent; "
                 "--no-scout is remembered; with a money limit, a session that is billed per use goes on"):
        show(r)

    t0 = time.time()
    r, st, new = resume(tmp, proj, exe, "b", [{"paid": True, "sleep": 60}], "--max-runs", "20")
    if not check(r.returncode == 1 and st.get("stop_reason") == nnloop.PAID and time.time() - t0 < 40,
                 "without a money limit, a session that turns to paid usage is ended at once and the campaign stops"):
        show(r)

    t0 = time.time()
    r, st, new = resume(tmp, proj, exe, "b", [{"sleep": 60}], "--max-runs", "20")
    ss = sessions(tmp)
    gone = ss and tk.wait_for(lambda: not nnloop.expctl.pid_alive(ss[0]["pid"]), timeout=10)
    if not check(r.returncode == 1 and "hung" in str(st.get("stop_reason")) and time.time() - t0 < 50 and gone,
                 "a session that hangs is ended after agent_timeout_s and the campaign stops"):
        show(r)
    hours = (st["counters"]["elapsed_s"] + 7) / 3600  # seven more seconds: less than agent_timeout_s
    r, st, new = resume(tmp, proj, exe, "b", [{"sleep": 60}], "--max-runs", "20", "--max-hours", f"{hours:.6f}")
    if not check(r.returncode == 0 and str(st.get("stop_reason")).startswith("limit reached: hours"),
                 "the wall-clock limit also ends an agent session in flight, and is named as the reason"):
        show(r)

    plan(tmp, [edit("SLEEP = 0", "SLEEP = 30", title="slow")])
    before = {d.name for d in (proj / "runs").glob("*")}
    r = loop(proj, "resume", "--campaign", "b", "--agent-exe", exe, "--max-runs", "20", "--detach")
    info = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    new = tk.wait_for(lambda: [d for d in (proj / "runs").glob("*-b-i*") if d.name not in before
                               and (d / "pid.json").exists()], timeout=120)
    r2 = loop(proj, "stop", "--campaign", "b")
    done = tk.wait_for(lambda: state(proj, "b").get("status") == "stopped" and not nnloop.expctl.pid_alive(info.get("pid") or 0),
                       timeout=120) if info and new else None
    st, its = state(proj, "b"), iters(proj, "b")
    if not check(bool(info.get("ok") and new and done) and r2.returncode == 0 and st.get("stop_reason") == "stop requested"
                 and its[-1]["status"] == "unfinished" and (new[0] / "exit.json").exists(),
                 "--detach runs in the background; a stop request ends the run in flight and the campaign, state written"):
        show(r)
        print("  loop.log:", nnloop.read_text(proj / "experiments/loop/b/loop.log")[-1500:], "\n  state:", st.get("stop_reason"))

    print("== campaign c: a wall-clock limit ==")
    r = loop(proj, "start", "--campaign", "c", "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-hours", "0.00001")
    st = state(proj, "c")
    if not check(r.returncode == 0 and str(st.get("stop_reason")).startswith("limit reached: hours")
                 and st["counters"]["runs"] == 0, "a wall-clock limit stops the campaign before the next run"):
        show(r)


def other_agents(tmp, proj, exe):
    print("== the same loop with Codex and Cursor command lines ==")
    plan(tmp, [edit("QUALITY = 1.0", "QUALITY = 0.5")])
    r = loop(proj, "start", "--campaign", "x", "--agent", "codex", "--agent-exe", exe, "--no-scout", "--max-runs", "4",
             "--max-tokens", "100000", env={"FAKE_AGENT": "codex"})
    st, ss, it = state(proj, "x"), sessions(tmp), iters(proj, "x")
    if not check(r.returncode == 0 and [e["status"] for e in it] == ["discard"] and len(ss) == 1
                 and ss[0]["argv"] == ["exec", "--json", "--ephemeral", "-s", "workspace-write", "-"]
                 and "one iteration of an unattended" in ss[0]["prompt"] and st["counters"]["tokens"] == 1500
                 and str(st.get("stop_reason")).startswith("limit reached: runs (3 of 4"),
                 "Codex: exec with the prompt on stdin, tokens counted, change discarded, run limit reached"):
        show(r)
    plan(tmp, [edit("QUALITY = 1.0", "QUALITY = 0.5")])
    r = loop(proj, "start", "--campaign", "y", "--agent", "cursor", "--agent-exe", exe, "--no-scout", "--max-runs", "4",
             "--in-container", env={"FAKE_AGENT": "cursor"})
    st, ss, it = state(proj, "y"), sessions(tmp), iters(proj, "y")
    if not check(r.returncode == 0 and [e["status"] for e in it] == ["discard"] and len(ss) == 1
                 and ss[0]["argv"][:5] == ["-p", "--force", "--output-format", "json", "--trust"]
                 and "one iteration of an unattended" in ss[0]["prompt"] and st["counters"]["tokens"] == 0,
                 "Cursor (with --in-container): print mode, the prompt read from its file, change discarded"):
        show(r)
    plan(tmp, [{"do": [["!write", "{notes}", NOTES]]}])
    r = loop(proj, "start", "--campaign", "z", "--agent", "cursor", "--agent-exe", exe, "--max-runs", "40",
             "--in-container", env={"FAKE_AGENT": "cursor"})
    st = state(proj, "z")
    if not check(r.returncode == 1 and "guard hook did not run" in str(st.get("stop_reason")) and not st.get("notes")
                 and not list((proj / "experiments/scouting").glob("*-z.md")),
                 "Cursor's output lists no tool calls: a scouting session without the guard is known by the notes file "
                 "it left, and stops the campaign"):
        show(r)


# ---------------------------------------------------------------- 8. what a resume refuses

def resume_refusals(tmp, proj, exe):
    print("== a resume under changed conditions or with an edited ledger ==")
    cfg_path = proj / ".claude/nn-training.json"
    old = cfg_path.read_text(encoding="utf-8")
    cfg = json.loads(old)
    cfg["loop"]["run_budget_s"] = 4
    put(cfg_path, json.dumps(cfg, indent=2) + "\n")
    git(proj, "commit", "-q", "-am", "longer runs")
    plan(tmp, [])
    r = loop(proj, "resume", "--campaign", "a", "--agent-exe", exe, "--max-runs", "40")
    if not check(r.returncode == 2 and "conditions changed" in r.stderr and "run_budget_s" in r.stderr,
                 "a resume under another run budget is refused: the results would not be comparable"):
        show(r)
    put(cfg_path, old)
    git(proj, "commit", "-q", "-am", "back to the old budget")
    led = proj / "experiments/loop/a/ledger.jsonl"
    text = led.read_text(encoding="utf-8")
    put(led, text.replace('"status": "discard"', '"status": "keep"', 1))
    s = json.loads(loop(proj, "status", "--campaign", "a").stdout or "{}")
    r = loop(proj, "resume", "--campaign", "a", "--agent-exe", exe, "--max-runs", "40")
    check(s.get("ledger_chain_ok") is False and r.returncode == 2 and "cannot be resumed" in r.stderr,
          "an edited ledger shows in status and blocks a resume")
    put(led, text)


# ---------------------------------------------------------------- 9. numeric settings searched by the harness

def search_tests(tmp, proj, exe):
    print("== campaign h: numeric settings searched by the harness ==")
    sp, rng = nnloop.search_space, random.Random
    space, why = sp({"LR": {"low": 1e-4, "high": 1e-2, "log": True}, "LAYERS": {"low": 2, "high": 6, "int": True}})
    bad = [{"L R": {"low": 1, "high": 2}}, {"LR": {"low": "1", "high": 2}}, {"LR": {"low": 2, "high": 2}}, {"LR": 3},
           {"LR": {"low": 0, "high": 1, "log": True}}, {"N": {"low": 2.2, "high": 2.8, "int": True}},
           {"LR": {"low": 1, "high": 10 ** 400}}, {"LR": {"low": True, "high": 2}},
           {"N": {"low": 1, "high": 4, "int": "false"}}, {"LR": {"low": 1, "high": 4, "log": 1}},
           {f"S{i}": {"low": 0, "high": 1} for i in range(7)}, {}, [1]]
    check(space == {"LR": {"low": 1e-4, "high": 1e-2, "log": True, "int": False},
                    "LAYERS": {"low": 2, "high": 6, "log": False, "int": True}} and why == ""
          and all(sp(b)[0] is None and sp(b)[1] for b in bad),
          "a search space is one to six named settings, each with two numbers low < high, above 0 on a log scale and "
          "with a whole number between them for an int; anything else is refused with a reason")
    d = nnloop.draws(space, 4, rng("x"))
    lr, edge = sorted(float(p["LR"]) for p in d), [1e-4 * 100 ** (i / 4) for i in range(5)]
    check(len(d) == 4 and all(edge[i] * 0.999 <= lr[i] <= edge[i + 1] * 1.001 for i in range(4))
          and all(p["LAYERS"].isdigit() and 2 <= int(p["LAYERS"]) <= 6 for p in d)
          and d == nnloop.draws(space, 4, rng("x")) != nnloop.draws(space, 4, rng("y")),
          "the trials take one value from each equal part of every range, on a log scale where asked, whole numbers "
          "for an int, and the same campaign and iteration draw the same values")
    whole = sp({"N": {"low": 1, "high": 4, "int": True}})[0]
    few = sp({"N": {"low": 2, "high": 3, "int": True}, "M": {"low": 7, "high": 7.5, "int": True}})[0]
    check(all(sorted(p["N"] for p in nnloop.draws(whole, 4, rng(i))) == ["1", "2", "3", "4"] for i in range(20))
          and all(sorted(p["N"] for p in nnloop.draws(few, 5, rng(i))) == ["2", "3"] for i in range(20)),
          "every whole number of an int range gets the same share of the trials, and a version that would repeat an "
          "earlier one is left out")
    rx = nnloop.setting("LR")
    hit = ["LR = 3e-4", "LR=0.001  # the rate", "LR = -1_000.5\r", "LR = .5", "LR = 1e+16"]
    miss = ["    LR = 1", "LR == 1", "LR = 1 + x", "XLR = 1", "LR_MIN = 1", "LR = 'a'", "LR = 1, 2", "LR = 1e", "LR ="]
    check(all(rx.search("a = 1\n" + h + "\nb = 2") for h in hit) and not any(rx.search("a = 1\n" + m + "\nb = 2") for m in miss)
          and rx.sub(lambda m: m.group(1) + "7", "LR = 3e-4  # c\r\nX = 1\r\n") == "LR = 7  # c\r\nX = 1\r\n",
          "a searched setting is one line `NAME = <number>` at the start of a line, with nothing after the number but "
          "a comment; only the number is replaced, the line end is kept")
    got = [refuse(proj, runs=9, loop={"search_trials": v}) for v in (1, 2.5, True, "3", float("inf"))]
    check(all("loop.search_trials must be a whole number of at least 2" in g for g in got)
          and "--help did not run" in refuse(proj, runs=9, loop={"search_trials": 2}),
          "refused: loop.search_trials that is not a whole number of at least 2")

    cfg_path = proj / ".claude/nn-training.json"
    old = cfg_path.read_text(encoding="utf-8")
    cfg = json.loads(old)
    cfg["loop"]["search_trials"] = 3
    put(cfg_path, json.dumps(cfg, indent=2) + "\n")
    git(proj, "commit", "-q", "-am", "let the harness search numeric settings")
    prop = {"title": "retune quality", "hypothesis": "a higher value scores higher", "source": "own"}
    bonus = {"do": [["sub", "train.py", "SLEEP = 0", "SLEEP = 0\nBONUS = 0.0  # added to the value"],
                    ["sub", "train.py", '"value": QUALITY + ', '"value": QUALITY + BONUS + ']],
             "proposal": dict(prop, title="a bonus", search={"BONUS": {"low": -0.5, "high": -0.1}})}
    left = {"do": [["sub", "train.py", "CHEAT = False", "CHEAT = False\nopen('left.tmp', 'w').close()"]],
            "proposal": dict(prop, title="a file left behind", search={"SLEEP": {"low": 0, "high": 0.5, "int": True}})}
    # a training run that puts a link to a file outside the project in the place of the script with the setting
    swap = {"do": [["sub", "train.py", "CHEAT = False", "CHEAT = False\nos.remove(__file__)\ntry:\n"
                    "    os.symlink(os.environ['TOY_OUTSIDE'], __file__)\nexcept OSError:  # Windows without the privilege\n"
                    "    os.link(os.environ['TOY_OUTSIDE'], __file__)"]],
            "proposal": dict(prop, title="a link for a file", search={"QUALITY": {"low": 2.6, "high": 3}})}
    outside = tmp / "outside.py"
    put(outside, "QUALITY = 9.0\n")
    plan(tmp, [{"proposal": dict(prop, search={"QUALITY": {"low": 1.5, "high": 2.5}})},
               {"proposal": dict(prop, search={"WIDTH": {"low": 1, "high": 4, "int": True}})},
               {"proposal": dict(prop, search={"QUALITY": {"low": 3, "high": 2}})},
               bonus, bonus, left, swap] + [{"proposal": {"no_change": "nothing left"}}] * 2)
    r = loop(proj, "start", "--campaign", "h", "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-runs", "40",
             env={"TOY_OUTSIDE": str(outside)})
    st, it, ss = state(proj, "h"), iters(proj, "h"), sessions(tmp)
    put(cfg_path, old)
    git(proj, "commit", "-q", "-am", "no search again")
    got = [e.get("status") for e in it]
    if not check(r.returncode == 0 and got == ["keep", "invalid", "invalid", "discard", "duplicate", "discard", "invalid",
                                               "declined", "declined"],
                 f"a search that finds a gain is kept, one without its line or with a bad range is invalid, one that "
                 f"finds no gain is discarded, and the same search again is a duplicate (got {got})"):
        show(r)
        print("  ledger:", json.dumps(rows(proj, "h"))[-3000:])
        return
    k, t = it[0], it[0]["trials"]
    v = sorted(float(x["values"]["QUALITY"]) for x in t)
    best = max(t, key=lambda x: x["score"])["values"]
    check(len(t) == 3 and 1.5 <= v[0] < 1.8343 and 1.8323 < v[1] < 2.1677 and 2.1657 < v[2] <= 2.5
          and all(x["status"] == "ok" and near(x["score"], float(x["values"]["QUALITY"]) + 0.01)
                  and f"-h-i1t{j}-s5-" in x["run"] for j, x in enumerate(t, 1))
          and k["search"] == {"QUALITY": {"low": 1.5, "high": 2.5, "log": False, "int": False}},
          "the harness trains three versions with values from the range, each once on a seed outside both seed panels, "
          "and scores them with the evaluator")
    man = nnloop.expctl.read_json(proj / "runs" / t[0]["run"] / "manifest.json") or {}
    check(k["values"] == best and float(best["QUALITY"]) == v[2] and len(k["runs"]) == 5 and set(k["scores"]) == {"1", "2"}
          and near(k["scores"]["1"], v[2]) and near(k["delta"], v[2] - 1.0, 1e-6)
          and (man.get("tags") or {}).get("values") == f'QUALITY={t[0]["values"]["QUALITY"]}',
          "the best version then runs on the seed panel and is decided by the keep rule like any change; a trial's run "
          "names its values")
    tip = git(proj, "rev-parse", "nnloop/h")
    check(k["commit"] == st["kept_commit"] == tip and f'QUALITY = {best["QUALITY"]}\n' in git(proj, "show", "nnloop/h:train.py")
          and git(proj, "log", "-1", "--format=%s", tip) == f'nnloop h iteration 1: values from the harness\'s search (QUALITY={best["QUALITY"]})'
          and git(proj, "rev-list", "--count", f'{st["base_commit"]}..{tip}') == "1"
          and f'+QUALITY = {best["QUALITY"]}' in (proj / "experiments/loop/h/iter-001/diff.patch").read_text(),
          "the kept commit carries the values the search found, written by the harness into the setting's line")
    sd, z = statistics.stdev([1.0, 1.02]), st.get("noise") or {}
    check(near(z.get("ss"), 2 * sd ** 2) and z.get("df") == 2 and near(k["margin"], nnloop.t_mult(2, 2) * sd),
          "the trial runs stay out of the noise estimate: it holds the baseline's panel and the kept version's")
    check("`WIDTH = <number>`" in it[1]["why"] and "0 such lines were found" in it[1]["why"] and not it[1]["runs"]
          and "low < high" in it[2]["why"] and not it[2]["runs"] and "trials" not in it[2],
          "a searched setting that has no line of its own, or a range that is none, costs no run")
    b = it[3]
    bv = max(float(x["values"]["BONUS"]) for x in b["trials"])
    check(len(b["runs"]) == 4 and float(b["values"]["BONUS"]) == bv and -0.5 <= bv <= -0.1 and "on the first seed it scored" in b["why"]
          and git(proj, "rev-list", "--count", f'{tip}..{b["commit"]}') == "2"
          and f'+BONUS = {b["values"]["BONUS"]}  # added to the value' in (proj / "experiments/loop/h/iter-004/diff.patch").read_text()
          and st["kept_commit"] == tip,
          "a change may come with a search: its commit and the one with the best values are tested together, and a "
          "best version that is worse than the best so far is discarded on the first seed")
    f = it[5]
    check(len(f["runs"]) == 2 and f["values"] == {"SLEEP": "0"} and [x["values"] for x in f["trials"]] == [f["values"]]
          and git(proj, "rev-list", "--count", f'{tip}..{f["commit"]}') == "1" and "on the first seed it scored" in f["why"],
          "a range that holds one version costs one trial, and a best version with the values the code has adds no "
          "commit, whatever files the trial runs left behind")
    w = it[6]
    check("replaced by a link" in w["why"] and len(w["trials"]) == 1 and len(w["runs"]) == 1 and "values" not in w
          and outside.read_text(encoding="utf-8") == "QUALITY = 9.0\n",
          "a file that a trial run replaced by a link is not written again: the harness writes its values only into "
          "plain files of the worktree, and the file outside the project stays as it was")
    check(not it[4]["runs"] and "tried before" in it[4]["why"] and st["counters"]["runs"] == 18
          and (st.get("confirm") or {}).get("status") == "confirmed" and str(st.get("stop_reason")).startswith("search exhausted"),
          "the trials count as runs: two for the baseline, five, four, two and one for the searches, four for the "
          "confirmation")
    p, j = ss[4]["prompt"] if len(ss) > 4 else "", (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8")
    check(all("The harness then trains up to 3 versions" in s["prompt"] for s in ss)
          and f'- iteration 1: keep, better by {k["delta"]:.4g} - "retune quality" [own] (the harness searched 3 versions; '
              f'the best had QUALITY = {best["QUALITY"]})' in p
          and f'- iteration 4: discard - "a bonus" [own] (the harness searched 3 versions; the best had BONUS = '
              f'{b["values"]["BONUS"]}) - on the first seed' in p
          and f'with QUALITY = {best["QUALITY"]} as the best of 3 versions the harness searched' in j,
          "the worker is offered the search and later reads what it found, and so does the journal")
    cfg, ns = nnloop.expctl.load_config(proj), argparse.Namespace()
    C = nnloop.Campaign(proj, dict(cfg, loop=dict(cfg["loop"], search_trials=3)), "h", ns)
    C.st.update(hold=False, limits=dict(C.st["limits"], runs=None))
    free = C.trials()
    C.st["limits"]["runs"] = 22  # 18 used, two for the seed panel: room for two trials, then for one
    two = C.trials()
    C.st["limits"]["runs"] = 21
    check((free, two, C.trials()) == (3, 2, 0) and "The harness then trains" not in C.worker_prompt(0)
          and "The harness then trains up to 2 versions" in C.worker_prompt(2) and nnloop.Campaign(proj, cfg, "h", ns).trials() == 0,
          "a search gets fewer trials where the run limit leaves no room for them and the seed panel, none below two, "
          "and none without loop.search_trials")
    box = tmp / "own"
    put(box / "wt/a.py", "X = 1\n")
    put(box / "wt/sub/c.py", "X = 1\n")
    put(box / "out/b.py", "X = 1\n")
    os.link(box / "out/b.py", box / "wt/hard.py")
    try:
        os.symlink(box / "out/b.py", box / "wt/soft.py")
        os.symlink(box / "out", box / "wt/far", target_is_directory=True)
    except OSError:  # Windows without the symlink privilege: a junction stands in for the linked folder
        subprocess.run(["cmd", "/c", "mklink", "/J", str(box / "wt/far"), str(box / "out")], capture_output=True)
    C.wt = box / "wt"
    check(C.own("a.py") and C.own("sub/c.py") and (box / "wt/far/b.py").is_file()
          and not any(C.own(p) for p in ("hard.py", "soft.py", "far/b.py", "sub", "none.py")),
          "the harness searches plain files of the worktree only: not a link, a file below a linked folder, or a "
          "file that has a second name elsewhere")


# ---------------------------------------------------------------- 10. a restart when the campaign stalls

def restart_tests(tmp, proj, exe):
    print("== campaign r: a restart from an earlier commit when nothing is kept ==")
    got = [refuse(proj, runs=9, loop={"restart_after": v}) for v in (0, 1.5, True, "2", float("inf"))]
    check(all("loop.restart_after must be a whole number of at least 1" in g for g in got)
          and "--help did not run" in refuse(proj, runs=9, loop={"restart_after": 2}),
          "refused: loop.restart_after that is not a whole number of at least 1")
    p = state(proj, "p")
    check([e.get("base") for e in iters(proj, "p")] == [p["base_commit"]] * 2 + [p["kept_commit"]] * 2
          and not [e for e in rows(proj, "p") if e["type"] == "restart"] and len(p.get("line") or []) == 1
          and str(p.get("stop_reason")).startswith("search exhausted"),
          "without loop.restart_after nothing restarts: every iteration starts from the best commit so far, and two "
          "sessions in a row that decline end the campaign")
    cfg_path = proj / ".claude/nn-training.json"
    old = cfg_path.read_text(encoding="utf-8")
    cfg = json.loads(old)
    cfg["loop"]["restart_after"] = 2
    put(cfg_path, json.dumps(cfg, indent=2) + "\n")
    git(proj, "commit", "-q", "-am", "restart a campaign that stalls")
    try:
        campaign_r(tmp, proj, exe)
    finally:
        put(cfg_path, old)
        git(proj, "commit", "-q", "-am", "no restart again")


def campaign_r(tmp, proj, exe):
    no = {"proposal": {"no_change": "nothing left"}}
    plan(tmp, [edit("QUALITY = 1.0", "QUALITY = 1.5", title="first"), edit("QUALITY = 1.5", "QUALITY = 1.4", title="lower"), no,
               edit("QUALITY = 1.0", "QUALITY = 1.2", title="second")] + [no] * 4)
    r = loop(proj, "start", "--campaign", "r", "--agent", "claude", "--agent-exe", exe, "--no-scout", "--max-runs", "40")
    st, led, it, ss = state(proj, "r"), rows(proj, "r"), iters(proj, "r"), sessions(tmp)
    got = [e.get("status") for e in it]
    if not check(r.returncode == 0 and got == ["keep", "discard", "declined", "keep"] + ["declined"] * 4,
                 f"a campaign that stalls goes on from an earlier commit instead of ending, keeps a change there, and ends "
                 f"when it is back at the start with nothing left to try (got {got})"):
        show(r)
        print("  ledger:", json.dumps(led)[-3000:])
        return
    c0, c1, c2 = st["base_commit"], it[0]["commit"], it[3]["commit"]
    check([e["base"] for e in it] == [c0, c1, c1, c0, c2, c2, c0, c0]
          and [(e["iter"], e["left"], e["commit"], e["best"]) for e in led if e["type"] == "restart"] == [(3, c1, c0, c1), (6, c2, c0, c1)],
          "after loop.restart_after iterations in a row without a keep the next one starts from the commit before the "
          "last keep; two sessions that decline do the same while there is a commit to go back to")
    check(git(proj, "rev-list", "--count", f"{c0}..{c2}") == "1" and "QUALITY = 1.2\n" in git(proj, "show", f"{c2}:train.py"),
          "the change made after a restart is one commit on top of the earlier code, without the change that was left")
    cf, j = st.get("confirm") or {}, (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8")
    check(st["kept_commit"] == c1 == git(proj, "rev-parse", "nnloop/r") and "best" not in st and near(st["baseline"]["mean"], 1.51)
          and [x["kept_commit"] for x in st["line"]] == [c0] and str(st.get("stop_reason")).startswith("search exhausted")
          and cf.get("status") == "confirmed" and cf.get("commit") == c1 and near(cf.get("delta"), 0.5, 1e-6)
          and st["counters"]["runs"] == 11,
          "a keep on the new line that scores below the commit that was left does not move the branch: the campaign ends "
          "on the best commit it found, and that one is confirmed against the start")
    gone = " - not in the code you see: the campaign left this change behind"
    first, second = '- iteration 1: keep, better by 0.5 - "first" [own]', '- iteration 4: keep, better by 0.2 - "second" [own]'
    p4, p5, p7 = (ss[i]["prompt"] for i in (3, 4, 6))
    check(first + gone in p4 and "- iteration 2:" not in p4 and "- iteration 3:" not in p4 and "Current best score: 1.01 (" in p4
          and first + gone in p5 and second + "\n" in p5 and "Current best score: 1.21 (" in p5
          and first + gone in p7 and second + gone in p7 and "- iteration 5:" not in p7 and "- iteration 6:" not in p7,
          "the worker after a restart reads the score of the code it sees and a history without the iterations made on top "
          "of what was left; a change that was kept and is not in that code is marked")
    check('- Kept: iteration 1 "first" (better by 0.5); iteration 4 "second" (better by 0.2, left behind at a restart: not in '
          'the kept code)\n' in j and "; 2 restart(s) from an earlier commit" in j and "- Score: start 1.01, now 1.51 (" in j,
          "the journal counts the restarts and says which kept change is not in the kept code")
    C = nnloop.Campaign(proj, nnloop.expctl.load_config(proj), "r", argparse.Namespace())
    C.st.update(confirm={}, kept_commit=c0)
    at_start = C.pending()
    C.st["best"] = {"kept_commit": c1}
    sp = proj / "experiments/loop/r/state.json"
    put(sp, json.dumps(dict(st, best={"kept_commit": c1, "baseline": {"mean": 9.0}})))
    shown = loop(proj, "status", "--campaign", "r").stdout
    put(sp, json.dumps(st))
    check(not at_start and C.pending() and '"best_score": 9.0' in shown,
          "while the campaign works on an earlier commit, the commit that was set aside is the one that waits for its "
          "confirmation, so the limits keep its runs, and the one whose score `status` shows as the best")

    r, st, new = resume(tmp, proj, exe, "r", [edit("QUALITY = 1.5", "QUALITY = 1.3", title="lower again"), no,
                                              edit("QUALITY = 1.0", "QUALITY = 1.8", title="third")] + [no] * 4, "--max-runs", "40")
    got = [e.get("status") for e in new]
    if not check(r.returncode == 0 and got == ["discard", "declined", "keep"] + ["declined"] * 4,
                 f"a resumed campaign goes on from its best commit and restarts again when that one stalls (got {got})"):
        show(r)
        print("  ledger:", json.dumps(rows(proj, "r"))[-3000:])
        return
    c3, cf = new[2]["commit"], st.get("confirm") or {}
    check([e["base"] for e in new] == [c1, c1, c0, c3, c3, c0, c0]
          and [(e["iter"], e["left"], e["commit"], e["best"]) for e in rows(proj, "r") if e["type"] == "restart"][2:]
          == [(10, c1, c0, c1), (13, c3, c0, c3)]
          and st["kept_commit"] == c3 == git(proj, "rev-parse", "nnloop/r") and git(proj, "rev-list", "--count", f"{c0}..{c3}") == "1"
          and "best" not in st and near(st["baseline"]["mean"], 1.81) and cf.get("status") == "confirmed"
          and cf.get("commit") == c3 and near(cf.get("delta"), 0.8, 1e-6) and st["counters"]["runs"] == 18,
          "a keep on the new line that beats the commit that was left moves the branch to it, and the confirmation "
          "compares that commit with the start")
    p9, j = sessions(tmp)[0]["prompt"], (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8")
    check(first + "\n" in p9 and "- iteration 2: discard" in p9 and second + gone in p9 and "- iteration 5:" not in p9
          and "- iteration 7: declined" in p9
          and '- Kept: iteration 1 "first" (better by 0.5, left behind at a restart: not in the kept code); iteration 4 "second" '
              '(better by 0.2, left behind at a restart: not in the kept code); iteration 11 "third" (better by 0.8)\n' in j
          and "; 4 restart(s) from an earlier commit" in j,
          "back on its best commit the worker reads that commit's history again, with the change kept elsewhere marked, "
          "and the journal follows the branch to the new best")


# ---------------------------------------------------------------- 11. the sandbox of a run (Linux)

def sandbox_tests(tmp, proj):
    print("== sandbox of a training run ==")
    C = nnloop.Campaign(proj, nnloop.expctl.load_config(proj), "sb", argparse.Namespace())
    if not C.box_train:
        print("SKIP sandbox checks: bubblewrap is not usable here (it is Linux-only), so a run is not confined on this platform")
        return
    C.fresh_worktree("HEAD")
    put(tmp / "probe.py", PROBE)
    (proj / "runs").mkdir(exist_ok=True)
    r = tk.sh(C.box_train + [PY, str(tmp / "probe.py"), str(proj), str(C.wt)], cwd=C.wt)
    got = json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stderr[-300:]
    check(got == {"net": False, "sealed": False, "main": False, "worktree": True, "runs": True},
          f"a training run has no network, cannot see the sealed data and can write only its worktree and the runs folder (got {got})")
    def seen():  # what the evaluator's box lets a program do, when the folder it scores is the runs folder
        r = tk.sh(C.eval_box(proj / "runs") + [PY, str(tmp / "probe.py"), str(proj), str(C.wt)], cwd=proj)
        return json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stderr[-300:]

    got = seen()
    check(got == {"net": False, "sealed": True, "main": False, "worktree": False, "runs": True},
          f"the evaluator has no network, reads the sealed data it scores on and can write only the folder it scores (got {got})")
    for named in ("data/test/labels.csv", "data/test"):  # as a file and as a folder
        C.cfg["final_eval_commands"] = [f"{PY} eval.py --final --data={named}"]
        C.L["eval_writable"] = ["train.py", "no-such-folder"]
        got = seen()
        check(got == {"net": False, "sealed": False, "main": True, "worktree": False, "runs": True},
              f"sealed data that only the final evaluation names ({named}) is hidden from the loop's evaluator, and it "
              f"can write what loop.eval_writable lists (got {got})")
    C.L["eval_command"] = C.L["eval_command"] + ["--data", "data/test/labels.csv"]
    got = seen()
    check(isinstance(got, dict) and got.get("sealed") is True,
          f"sealed data that the loop's own evaluator command names stays readable for it (got {got})")
    C.drop_worktree()
    (proj / "runs/probe.tmp").unlink(missing_ok=True)


# ---------------------------------------------------------------- 12. guard rules the loop relies on

def guard_tests(tmp, proj):
    print("== guard rules in a worktree of the project ==")
    C = nnloop.Campaign(proj, nnloop.expctl.load_config(proj), "g", argparse.Namespace())
    C.fresh_worktree("HEAD")
    wt, un = C.wt, {"NN_UNATTENDED": "1"}

    def call(tool, ti, env=None):
        return tp.guard(wt, dict(tp.CLAUDE, cwd=str(wt), tool_name=tool, tool_input=ti), env=env)

    def bash(cmd, env=None):
        return tp.guard(wt, dict(tp.CLAUDE, cwd=str(wt), tool_input=dict(tp.CLAUDE["tool_input"], command=cmd)), env=env)

    code, dec, out, _ = call("Read", {"file_path": str(proj / "data/test/labels.csv")})
    check(dec == "deny" and "sealed" in out, "from a worktree, the checkout's sealed data is as sealed as the worktree's own")
    code, dec, out, _ = call("Edit", {"file_path": str(proj / "eval.py"), "old_string": "a", "new_string": "b"})
    check(dec == "ask" and "frozen" in out, "from a worktree, an edit of the checkout's frozen evaluator asks")
    code, dec, out, _ = call("Edit", {"file_path": str(wt / "eval.py"), "old_string": "a", "new_string": "b"}, un)
    check(dec == "deny" and "nobody can be asked" in out, "unattended, an edit of the frozen evaluator is denied")
    code, dec, out, _ = call("Read", {"file_path": str(proj / "train.py")})
    check(code == 0 and dec is None, "attended, a file tool may read outside the worktree")
    code, dec, out, _ = call("Read", {"file_path": str(proj / "train.py")}, un)
    check(dec == "deny" and "outside this project" in out, "unattended, file tools stay inside the project folder")
    code, dec, out, _ = call("Write", {"file_path": str(wt / "blobs/x.bin"), "content": "x"}, un)
    check(dec == "deny" and "outside this project" in out, "unattended, a write through a link that leaves the folder is denied")
    code, dec, out, _ = call("Read", {"file_path": str(wt / "blobs/x.bin")}, un)
    check(code == 0 and dec is None, "unattended, data that the loop linked into the worktree may be read")
    code, dec, out, _ = bash("git show HEAD:data/test/labels.csv")
    check(dec == "deny" and "sealed" in out, "git show <rev>:<sealed path> is denied like the path itself")
    code, dec, out, _ = tp.guard(proj, dict(tp.CLAUDE, cwd=str(proj / "data"), tool_input=dict(
        tp.CLAUDE["tool_input"], command="git show HEAD~1:data/test/labels.csv")))
    check(dec == "deny" and "sealed" in out, "... from a subfolder too, where git still reads the path from the root")
    # a worktree that git registered outside .claude/worktrees/: the same repository, so the same rules
    beside, edit = tmp / "beside", {"old_string": "a", "new_string": "b"}
    nnloop.git(proj, "worktree", "add", "--detach", str(beside), "HEAD")

    def at(root, tool, path):
        ti = dict(edit, file_path=str(path)) if tool == "Edit" else {"pattern": "x", "path": str(path)} \
            if tool == "Grep" else {"file_path": str(path)}
        return tp.guard(root, dict(tp.CLAUDE, cwd=str(root), tool_name=tool, tool_input=ti))[1:3]

    def sh(root, cmd):
        return tp.guard(root, dict(tp.CLAUDE, cwd=str(root), tool_input=dict(tp.CLAUDE["tool_input"], command=cmd)))[1:3]

    dec, out = at(beside, "Read", proj / "data/test/labels.csv")
    check(dec == "deny" and "sealed" in out, "from a worktree registered elsewhere, the checkout's sealed data is sealed")
    dec, out = at(beside, "Edit", proj / "eval.py")
    check(dec == "ask" and "frozen" in out, "from there, an edit of the checkout's frozen evaluator asks")
    dec, out = at(beside, "Edit", proj / ".claude/settings.json")
    check(dec == "ask" and "guardrails" in out, "from there, an edit of the checkout's harness files asks")
    dec, out = at(proj, "Edit", beside / "eval.py")
    check(dec == "ask" and "frozen" in out, "from the checkout, an edit of that worktree's frozen evaluator asks")
    dec, out = at(proj, "Edit", wt / ".claude/settings.json")
    check(dec == "ask" and "guardrails" in out, "from the checkout, an edit of a worktree's harness files asks")
    dec, out = tp.guard(beside, dict(tp.CLAUDE, cwd=str(beside), tool_input=dict(
        tp.CLAUDE["tool_input"], command=f"cat {(proj / 'data/test/labels.csv').as_posix()}")))[1:3]
    check(dec == "deny" and "sealed" in out, "from there, a shell command that names the checkout's sealed file is denied")
    # a recursive command over another checkout: the sealed files on disk there decide, not those of the session's own
    put(beside / "data/test/there.tsv", "id\n1\n")
    put(proj / "data/test/here.tsv2", "id\n1\n")
    got = [sh(proj, f"grep -r x --include='*.tsv' {beside.as_posix()}")[0],
           sh(proj, f"grep -r x --include='*.tsv2' {beside.as_posix()}")[0],
           sh(proj, "grep -r x --include='*.tsv' .")[0], sh(beside, f"find {proj.as_posix()} -name '*.tsv2'")[0]]
    check(got == ["ask", None, None, "ask"],
          f"a recursive command over another checkout is judged by the sealed files that lie on disk there ({got})")
    os.unlink(beside / "data/test/there.tsv")
    os.unlink(proj / "data/test/here.tsv2")
    # what the review of 12 November found. Sealed data behind a link out of the repository, in a worktree whose
    # config seals other paths than the checkout's
    store, held = tmp / "store", beside / "held"
    put(store / "secret.csv", "id,label\n1,0\n")

    def point(to):  # held -> to, in place of what it was; None takes it away
        try:
            os.unlink(held)
        except FileNotFoundError:
            pass
        except OSError:
            os.rmdir(held)  # a junction
        try:
            if to:
                os.symlink(to, held, target_is_directory=True)
        except OSError:  # Windows without the symlink privilege: a junction
            subprocess.run(["cmd", "/c", "mklink", "/J", str(held), str(to)], capture_output=True, check=True)

    point(store)
    theirs = json.loads((beside / ".claude/nn-training.json").read_text(encoding="utf-8"))
    put(beside / ".claude/nn-training.json", json.dumps(dict(theirs, sealed_paths=["held/**"])))
    dec, out = at(beside, "Read", held / "secret.csv")
    check(dec == "deny" and "sealed" in out, "a sealed folder that is a link to storage outside the repository is sealed")
    check(at(beside, "Read", store / "secret.csv")[0] == "deny", "... and so is the same file at its real place")
    check(at(beside, "Grep", "held")[0] == "deny", "... and a search of the linked folder")
    check(sh(beside, "cat held/secret.csv")[0] == "deny", "... and a shell command that names a file in it")
    check(at(beside, "Read", proj / "data/test/labels.csv")[0] == "deny" and at(proj, "Read", held / "secret.csv")[0] == "deny",
          "the sealed paths of every checkout's config hold in all of them, whatever the session's own config seals")
    # the usual layout: the data folder is the link, git ignores it, and the sealed files lie in a folder below it
    for d in (store, proj / "kept"):
        put(d / "test/labels.csv", "id,label\n1,0\n")
    put(beside / ".claude/nn-training.json", json.dumps(dict(theirs, sealed_paths=["held/test/**"])))
    put(beside / ".gitignore", "held\n")
    check(at(beside, "Grep", "held")[0] == "deny" and at(beside, "Grep", store)[0] == "deny",
          "a search of a linked data folder that git ignores reaches the sealed files below it, by its name and at "
          "its real place")
    check(at(proj, "Grep", store)[0] == "deny" and sh(beside, f"rg x {store.as_posix()}")[0] == "ask",
          "... from a checkout that has no such link too, and ripgrep in the shell is asked about")
    point(proj / "kept")
    check(at(beside, "Grep", "held")[0] == "deny" and at(proj, "Grep", "kept")[0] == "deny",
          "... and so does a link that ends in another checkout under another name")
    point(None)
    shutil.rmtree(proj / "kept")
    # git's own files, from which the guard reads the other checkouts
    bad = proj / ".git/worktrees/000"
    bad.mkdir()
    (bad / "gitdir").write_bytes(b"\xff\x00")
    check(at(proj, "Edit", beside / "eval.py")[0] == "ask", "a damaged entry in git's list of worktrees loses that entry only")
    shutil.rmtree(bad)
    dec, out = at(proj, "Edit", proj / ".git/worktrees/beside/gitdir")
    check(dec == "ask" and "git's own files" in out, "an edit of git's own files asks")
    dec, out = sh(proj, "echo x > .git/worktrees/beside/gitdir")
    check(dec == "ask" and "list of worktrees" in out, "... and so does a shell command that writes to git's list of worktrees")
    # a checkout below the searched folder, and a project that is a subfolder of its repository
    nnloop.git(proj, "worktree", "add", "--detach", str(proj / "sub/nested"), "HEAD")
    check(at(proj, "Grep", "sub")[0] == "deny", "a search from above another checkout reaches that checkout's sealed files")
    nnloop.git(proj, "worktree", "remove", "--force", str(proj / "sub/nested"))
    shutil.rmtree(proj / "sub", ignore_errors=True)
    repo = tmp / "repo"
    shutil.copytree(proj / ".claude", repo / "p/.claude", ignore=shutil.ignore_patterns("worktrees", "state"))
    put(repo / "p/data/test/labels.csv", "id,label\n1,0\n")
    for a in (("init", "-q"), ("add", "-A"), ("-c", "user.name=t", "-c", "user.email=t@localhost", "-c",
                                               "commit.gpgsign=false", "commit", "-qm", "sub"),
              ("worktree", "add", "--detach", str(tmp / "repo2"), "HEAD")):
        nnloop.git(repo, *a)
    check(at(tmp / "repo2/p", "Read", repo / "p/data/test/labels.csv")[0] == "deny",
          "a project in a subfolder of its repository: its other checkouts are found all the same")
    check(sh(repo / "p", "git show HEAD:p/data/test/labels.csv")[0] == "deny",
          "... and git's <rev>:<path>, which counts from the repository's top, is read that way")
    # spellings: git -C, a colon outside git, the final command, an unknown tool, a long path
    code, dec, out, _ = bash("git -C data show HEAD:./test/labels.csv")
    check(dec == "deny" and "sealed" in out, "git -C <folder> does not hide the folder it names")
    check(bash("echo note:data/test")[1] == "ask", "a colon outside a git command is asked about, not denied")
    for cmd in ("python eval.py --final; echo done", "cd data && python ../eval.py --final", "py ./eval.py --final --ckpt x",
                "cmd /c python eval.py --final"):
        check(bash(cmd)[1] == "deny", f"the final command is recognised in another spelling: {cmd}")
    code, dec, out, _ = bash("python eval.py runs/x")
    check(code == 0 and dec is None, "... while a validation run of the same script stays free")
    check(call("mcp__fs__write", {"path": str(wt / "blobs/x.bin"), "content": "x"}, un)[1] == "deny",
          "unattended, only the read tools may use the linked data: an unknown tool is denied")
    if os.name == "nt":
        check(call("Read", {"file_path": "\\\\?\\" + str(proj / "data/test/labels.csv")})[1] == "deny",
              "the long-path spelling of a sealed file (\\\\?\\C:\\...) is recognised")
    nnloop.git(proj, "worktree", "remove", "--force", str(beside))
    b = tmp / "beacon.jsonl"
    env = dict(un, NN_GUARD_BEACON=str(b))
    call("Read", {"file_path": str(wt / "train.py")}, env)
    call("Write", {"file_path": str(wt / "eval.py"), "content": "x"}, env)
    lines = [json.loads(x) for x in b.read_text(encoding="utf-8").splitlines()] if b.exists() else []
    check([(x.get("tool"), x.get("decision")) for x in lines] == [("Read", "allow"), ("Write", "deny")]
          and "frozen" in str(lines[-1].get("reason")), "the guard records every checked call, allowed ones included, for the loop")
    start = "python .claude/skills/nn-training/scripts/nnloop.py start --campaign z --agent claude --max-runs 3"
    code, dec, out, _ = bash(start)
    check(dec == "ask" and "explicit approval" in out, "starting the loop asks for the user's approval")
    code, dec, out, _ = bash(start, un)
    check(dec == "deny", "an unattended session cannot start another loop")
    code, dec, out, _ = bash("python .claude/skills/nn-training/scripts/nnloop.py --root . resume --campaign z --max-runs 9")
    check(dec == "ask", "resuming the loop asks too")
    code, dec, out, _ = bash("python .claude/skills/nn-training/scripts/nnloop.py status")
    check(code == 0 and dec is None, "the loop's status is free to read")
    code, dec, out, _ = bash("python .claude/skills/nn-training/scripts/nnremote.py launch --name r")
    check(dec == "ask", "launching remote work asks")
    C.drop_worktree()
    check(not wt.exists() and (proj / "blobs/x.bin").read_text() == "weights-v1", "the worktree is gone, the linked data is not")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="nnkit-loop-"))
    try:
        unit_tests()
        proj, exe = make_project(tmp), agent_exe(tmp)
        refusal_tests(tmp, proj, exe)
        selftest_tests(tmp, proj, exe)
        if campaign_a(tmp, proj, exe):
            resume_tests(tmp, proj, exe)
            confirm_tests(tmp, proj, exe)
            second_panel(tmp, proj, exe)
            campaign_b(tmp, proj, exe)
            other_agents(tmp, proj, exe)
            resume_refusals(tmp, proj, exe)
            search_tests(tmp, proj, exe)
            restart_tests(tmp, proj, exe)
        sandbox_tests(tmp, proj)
        guard_tests(tmp, proj)
    finally:
        shutil.rmtree(tmp, onerror=nnloop._force_rm)
    print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES")
    for f in FAILS:
        print("  -", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
