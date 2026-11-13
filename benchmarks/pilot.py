#!/usr/bin/env python3
"""Pilot comparison on a benchmark task: the same agent with this kit (its unattended loop), with another
version of the kit, and with no kit, at the same budget of training runs.

    python benchmarks/pilot.py WORKDIR [--arms new,old,none] [--old-kit DIR_OR_GIT_REVISION] [--repeats 2]
                               [--runs 12] [--model sonnet] [--task charlm] [--session-minutes 40]

Every arm-run gets a fresh project (new_project.py). "new" runs `nnloop start --max-runs RUNS` in it, with the
loop's confirmation on fresh seeds turned off: its runs do not search, and the arms are compared at an equal
number of training runs. "old" and "none" get one headless Claude Code session (dontAsk mode: file tools and shell commands that call Python; Claude
Code also lets through commands it knows as read-only; the prompt says so) that is told the same budget; nothing
enforces it there, so the script counts the training commands it finds in the transcript. Then each arm-run's
final train.py is retrained on fixed seeds in a copy of the task without the held-out files and scored on the
test split by this checkout's evaluator. Results: WORKDIR/pilot.json, written after every arm-run, so an
interrupted pilot continues where it stopped.

It starts real agent sessions (they draw on your subscription or API account) and real training, one after
the other. With two runs per arm it is a pilot: it can show a large difference, not a small one.
"""
import argparse
import io
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
sys.path.insert(0, str(KIT / ".claude" / "skills" / "nn-training" / "scripts"))
import nnloop  # noqa: E402  (the kit's helpers: session environment, transcript parsing, process-tree kill)

SCORE_SEEDS = (101, 102, 103)
HELD_OUT = ("data/loopval.txt", "data/test.txt")
TOOLS, ALLOW = "Read,Glob,Grep,Edit,Write,Bash", "Read,Glob,Grep,Edit,Write,Bash(python:*),Bash(python3:*)"
PY = "python" if os.name == "nt" else "python3"
# a Python call that names train.py or launches a run through expctl, within one simple command
TRAINS = re.compile(r"python[\d.]*(?:\.exe)?[\"']?\s.*?(?:train\.py|expctl(?:\.py)?[\"']?\s+(?:--root\s+\S+\s+)?launch(?!\s+(?:--help|-h)\b))")
PROMPT = """{task}

You work alone and unattended in this project folder. Nobody can answer a question or approve anything, so do
not ask: decide and continue.

Tools: the file tools, and shell commands that call `{py}` (the Python with PyTorch on this machine). Most
other programs are refused, and one refused part refuses the whole command line. A refusal concerns that one
command, not the shell: put it differently and go on.

Budget: at most {runs} training runs of 30 seconds each (`{py} train.py --seed N --time-budget 30`, however
you start them). Anything else that trains a model counts against the same budget. The budget is what makes
your result comparable with others, so stop when it is used up.

Held-out data: data/loopval.txt and data/test.txt are reserved for the final scoring. Do not read them or use
them in any way; a result that touched them is void. data/dev.txt is yours for validation.

Change only train.py. When you stop, train.py must hold the version you judge best, which need not be the last
one you tried: it will be retrained from scratch with other seeds and scored on the test split.{kit}
Finish with three lines: what you changed, the dev score before and after, and how many runs you used.
"""
KIT_LINE = "\n\nThe nn-training kit is installed in this project (see CLAUDE.md). Use it as its instructions say."


def run(cmd, cwd, timeout, out, inp=None):
    """Run a command without the variables of the agent session this script was started from. Returns the exit
    code, or None when it was ended: at the timeout, or because an agent session in it turned to paid usage."""
    env = {k: v for k, v in os.environ.items() if not nnloop.PARENT_ENV.match(k) and not k.startswith("EXP_")}
    kw = {"creationflags": 0x08000200} if os.name == "nt" else {"start_new_session": True}
    with open(out, "ab") as f, open(inp or os.devnull, "rb") as i:
        p = subprocess.Popen([str(c) for c in cmd], cwd=str(cwd), env=env, stdin=i, stdout=f, stderr=subprocess.STDOUT, **kw)
        t_end, pos = time.time() + timeout, os.path.getsize(out)
        while p.poll() is None:
            paid, pos = nnloop.paid_usage(out, pos)
            if paid or time.time() > t_end:
                nnloop.kill_tree(p)
                return None
            time.sleep(0.5)
        return p.returncode


def session_facts(transcript):
    """Model and agent version from the init event, the number of shell commands that started training, and the
    number of tool calls the permission rules refused. A refused command trained nothing and is not counted. The
    count is a lower bound: a loop inside one command, or a script that trains several times, counts once."""
    facts, trains, refused = {}, {}, set()
    for line in transcript.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            facts = {"model": ev.get("model"), "agent_version": ev.get("claude_code_version")}
        if ev.get("type") == "result":
            refused = {d.get("tool_use_id") for d in ev.get("permission_denials") or [] if isinstance(d, dict)}
        for c in ((ev.get("message") or {}).get("content") or []) if ev.get("type") == "assistant" else []:
            if isinstance(c, dict) and c.get("name") == "Bash":
                parts = re.split(r"&&|\|\||[;|\n]", str((c.get("input") or {}).get("command")))
                trains[c.get("id")] = sum(1 for p in parts if TRAINS.search(p))
    return facts, sum(n for i, n in trains.items() if i not in refused), len(refused)


def no_confirm(proj):
    """Turn off the loop's confirmation on fresh seeds and its control runs in a project, so that the loop spends
    its run limit on the search as the other arms do. As a commit, because the loop refuses to start from
    uncommitted changes. The pilot scores every arm's final train.py on held-out data itself."""
    path = proj / ".claude" / "nn-training.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["loop"]["confirm"] = False
    cfg["loop"].pop("controls", None)
    nnloop.write_text(path, json.dumps(cfg, indent=2) + "\n")
    subprocess.run(["git", "-C", str(proj), "commit", "-q", "-am", "pilot: no confirmation and no control runs"], check=True)


def arm_new(proj, a, log):
    no_confirm(proj)
    code = run([sys.executable, proj / ".claude/skills/nn-training/scripts/nnloop.py", "--root", proj, "start",
                "--campaign", "pilot", "--agent", "claude", "--max-runs", a.runs, "--model", a.model],
               proj, a.runs * 600 + 3600, log)
    d = proj / "experiments" / "loop" / "pilot"
    st = nnloop.expctl.read_json(d / "state.json") or {}
    rows = nnloop.ledger_rows(d / "ledger.jsonl")[0]
    facts = session_facts(nnloop.read_text(d / "iter-001" / "transcript-worker.jsonl"))[0]
    final = subprocess.run(["git", "-C", str(proj), "show", "nnloop/pilot:train.py"], capture_output=True,
                           encoding="utf-8", errors="replace")
    keep = ("iter", "status", "why", "title", "source", "from_scouting", "delta", "margin", "scores")
    return final.stdout if final.returncode == 0 else None, dict(
        facts, exit=code, paid=st.get("stop_reason") == nnloop.PAID,
        stop_reason=st.get("stop_reason"), counters=st.get("counters"), notes=st.get("notes"),
        start_score=st.get("start_mean"), best_score=(st.get("baseline") or {}).get("mean"), margin=st.get("margin"),
        scout=[{k: r.get(k) for k in ("status", "hypotheses")} for r in rows if r.get("type") == "scout"],
        iterations=[{k: r.get(k) for k in keep} for r in rows if r.get("type") == "iteration"])


def arm_session(proj, a, log, kit):
    cfg = json.loads((HERE / a.task / "nn-training.task.json").read_text(encoding="utf-8"))
    prompt = proj.parent / (proj.name + "-prompt.md")
    nnloop.write_text(prompt, PROMPT.format(task=cfg["loop"]["task"], runs=a.runs, py=PY, kit=KIT_LINE if kit else ""))
    exe = shutil.which("claude") or sys.exit("pilot: `claude` is not on PATH")
    t0 = time.time()
    code = run([exe, "-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "dontAsk",
                "--tools", TOOLS, "--allowedTools", ALLOW, "--setting-sources", "project", "--strict-mcp-config",
                "--no-session-persistence", "--model", a.model], proj, a.session_minutes * 60, log, inp=prompt)
    text = nnloop.read_text(log)
    res, (facts, trains, refused), paid = nnloop.parse_claude(text), session_facts(text), nnloop.paid_usage(log)[0]
    if not trains:  # for example when every shell command was refused: the score is then the unchanged train.py's
        print(f"pilot: {proj.name}: the session started no training run ({refused} tool calls were refused)", flush=True)
    return nnloop.read_text(proj / "train.py"), dict(
        facts, exit=code, paid=paid, timed_out=code is None and not paid, seconds=round(time.time() - t0), ok=res["ok"], stop=res["stop"],
        tokens=res["tokens"], usd=res["usd"], training_commands=trains, refused_calls=refused, last_words=res["text"])


def score(train_py, a, work, name):
    """Retrain a train.py on the scoring seeds, away from the held-out files, and score each model on the test split."""
    d = work / f"score-{name}"
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(HERE / a.task, d, ignore=shutil.ignore_patterns("__pycache__", "out", "runs", *[Path(h).name for h in HELD_OUT]))
    nnloop.write_text(d / "train.py", train_py)
    scores, errors = [], []
    for s in SCORE_SEEDS:
        out = d / "out" / f"s{s}"
        code = run([sys.executable, "train.py", "--seed", s, "--time-budget", "30", "--out", out], d, 300, d / f"train-s{s}.log")
        r = subprocess.run([sys.executable, str(HERE / a.task / "evaluate.py"), "--data", "data/test.txt", "--run-dir", str(out)],
                           capture_output=True, encoding="utf-8", errors="replace")
        got = nnloop.last_json(r.stdout) or {}
        if code == 0 and r.returncode == 0 and isinstance(got.get("score"), (int, float)):
            scores.append(got["score"])
        else:
            errors.append(f"seed {s}: training exit {code}; evaluator: {(got.get('error') or r.stderr or r.stdout)[-300:]}")
    return {"test_scores": scores, "errors": errors, "test_mean": statistics.mean(scores) if scores else None,
            "test_sd": statistics.stdev(scores) if len(scores) > 1 else None}


def old_kit(a, work):
    if Path(a.old_kit).is_dir():
        return Path(a.old_kit).resolve()
    d = work / "old-kit"
    if not d.exists():  # a git revision of this checkout
        r = subprocess.run(["git", "-C", str(KIT), "archive", "--format=tar", a.old_kit], capture_output=True)
        if r.returncode != 0:
            sys.exit(f"pilot: --old-kit is neither a folder nor a revision of this checkout: {r.stderr.decode(errors='replace')[:300]}")
        tarfile.open(fileobj=io.BytesIO(r.stdout)).extractall(d)
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("workdir")
    ap.add_argument("--arms", default="new,old,none")
    ap.add_argument("--old-kit", help="folder of another kit version, or a git revision of this checkout (for the old arm)")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--runs", type=int, default=12, help="training runs per arm-run")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--task", default="charlm")
    ap.add_argument("--session-minutes", type=float, default=40, help="hard time limit of an old or none session")
    a = ap.parse_args()
    work, arms = Path(a.workdir).resolve(), a.arms.split(",")
    if KIT in (work, *work.parents):
        sys.exit("pilot: WORKDIR must be outside the kit's own folder")
    if set(arms) - {"new", "old", "none"} or ("old" in arms and not a.old_kit):
        sys.exit("pilot: --arms takes new, old and none, and the old arm needs --old-kit")
    work.mkdir(parents=True, exist_ok=True)
    out = work / "pilot.json"
    res = nnloop.expctl.read_json(out) or {"task": a.task, "runs": a.runs, "model": a.model, "score_seeds": SCORE_SEEDS,
                                           "platform": sys.platform, "arm_runs": {}}
    if "reference" not in res:
        res["reference"] = score(nnloop.read_text(HERE / a.task / "train.py"), a, work, "reference")
        nnloop.expctl.write_json_atomic(out, res)
    for i in range(1, a.repeats + 1):  # the arms take turns, so that a drift over time does not favour one of them
        for arm in arms:
            name = f"{arm}-{i}"
            if name in res["arm_runs"]:
                continue
            print(f"pilot: {name} ...", flush=True)
            proj, log = work / name, work / f"{name}.log"
            left = [p for p in (proj, log, work / f"{name}-setup.log", work / f"{name}-prompt.md") if p.exists()]
            if left:  # files of an attempt that was cut off: set aside, so that this attempt's log stands alone
                cut = work / f"{name}-cut-{time.strftime('%H%M%S')}"
                cut.mkdir()
                for p in left:
                    p.rename(cut / p.name)
            cmd = [sys.executable, HERE / "new_project.py", proj, "--task", a.task]
            cmd += ["--no-kit"] if arm == "none" else ["--kit-dir", old_kit(a, work)] if arm == "old" else []
            if run(cmd, work, 300, work / f"{name}-setup.log") != 0:
                sys.exit(f"pilot: could not create {proj}; see {name}-setup.log")
            final, info = arm_new(proj, a, log) if arm == "new" else arm_session(proj, a, log, kit=arm == "old")
            if info["paid"]:  # nothing of this arm-run is recorded, so the next start repeats it
                sys.exit(f"pilot: stopped in {name}: the agent's plan usage is used up or running out, and further "
                         "sessions would be billed per use. Start the pilot again when the limit has reset.")
            info.update(score(final, a, work, name) if final else {"test_scores": [], "errors": ["no final train.py"],
                                                                   "test_mean": None, "test_sd": None})
            res["arm_runs"][name] = info
            nnloop.expctl.write_json_atomic(out, res)
            print(f"pilot: {name} test score {info['test_mean']} (sd over seeds {info['test_sd']})", flush=True)
    print(f"\nreference (train.py as shipped): {res['reference']['test_mean']:.4f}")
    for arm in arms:
        means = [r["test_mean"] for n, r in sorted(res["arm_runs"].items()) if n.rsplit("-", 1)[0] == arm and r["test_mean"] is not None]
        if means:
            print(f"{arm:5} runs: {', '.join(f'{m:.4f}' for m in means)}   mean {statistics.mean(means):.4f}"
                  f"   range {max(means) - min(means):.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
