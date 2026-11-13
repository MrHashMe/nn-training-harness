#!/usr/bin/env python3
"""Tests for benchmarks/: new_project.py builds a usable project from the charlm task, and the task's data is the
text its README names; its controls; the fine-tuning task's data, settings, model pins and evaluator refusals.
Needs git; no GPU and no network. One check, of the constant control under the evaluator, needs PyTorch and is
skipped without it."""
import collections
import contextlib
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
TASK = KIT / "benchmarks" / "charlm"
FAILS = []


def check(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


def run(*argv, **kw):
    return subprocess.run([sys.executable, *map(str, argv)], capture_output=True, text=True, timeout=600, **kw)


tmp = Path(tempfile.mkdtemp(prefix="bench-"))
task = json.loads((TASK / "nn-training.task.json").read_text(encoding="utf-8"))

# 1. the data: four pieces that add up to the file the README names
readme = (TASK / "README.md").read_text(encoding="utf-8")
whole = b"".join((TASK / "data" / n).read_bytes() for n in ("train.txt", "dev.txt", "loopval.txt", "test.txt"))
m = re.search(r"SHA-256 of the whole file\s+`([0-9a-f]{64})`", readme)
check(bool(m) and hashlib.sha256(whole).hexdigest() == m.group(1), "the four data pieces, joined, have the SHA-256 the README states")
check(f"{len(whole):,} characters" in readme and b"\r" not in whole, "the README's character count is the data's size")
for name in ("train.txt", "dev.txt", "loopval.txt", "test.txt"):
    size = (TASK / "data" / name).stat().st_size
    check(f"| `{name}` | {size:,} |" in readme, f"README states the size of {name}")
check(set(task["sealed_paths"]) == {"data/loopval.txt", "data/test.txt"} and "evaluate.py" in task["frozen_paths"],
      "the task seals the loop's and the final split and freezes the evaluator")

# 1b. the controls: runs that cannot have learned the text, and the scores they cannot beat
train, scored = ((TASK / "data" / n).read_text(encoding="utf-8") for n in ("train.txt", "loopval.txt"))
bounds = {"constant": math.log(len(set(train))),
          "shuffled": -sum(v / len(scored) * math.log(v / len(scored)) for v in collections.Counter(scored).values())}
ctl = {c["name"]: c for c in task["loop"]["controls"]}
check(set(ctl) == set(bounds) and all(0 <= bounds[k] - ctl[k]["floor"] < 0.001 for k in bounds)
      and "controls.py" in task["frozen_paths"],
      "the floor of the constant control is the loss of equal probabilities, that of the shuffled one the entropy of "
      "the character frequencies in the split the loop scores on, and the controls are frozen")
c = tmp / "controls"
shutil.copytree(TASK, c, ignore=shutil.ignore_patterns("__pycache__", "out", "runs"))
(c / "train.py").write_text('''import hashlib, json, os, sys
from pathlib import Path
here = Path(__file__).resolve().parent
text = (here / "data" / "train.txt").read_text(encoding="utf-8")
(Path(sys.argv[sys.argv.index("--out") + 1]) / "seen.json").write_text(json.dumps({
    "argv": sys.argv[1:], "here": os.path.samefile(os.getcwd(), here), "files": sorted(p.name for p in (here / "data").iterdir()),
    "head": text[:300], "chars": hashlib.sha256("".join(sorted(text)).encode()).hexdigest(),
    "evaluator": (here / "evaluate.py").is_file()}))
''', encoding="utf-8")  # stands for train.py: it writes down what the control gave it
r = run(c / "controls.py", "shuffled", "--seed", "7", env=dict(os.environ, EXP_RUN_DIR=str(tmp / "shuffled-run")))
seen = json.loads((tmp / "shuffled-run" / "seen.json").read_text(encoding="utf-8")) if r.returncode == 0 else {}
check(seen.get("argv", [])[:2] == ["--seed", "7"] and seen.get("here") and seen.get("evaluator")
      and seen.get("files") == ["dev.txt", "train.txt"] and seen.get("head") != train[:300]
      and seen.get("chars") == hashlib.sha256("".join(sorted(train)).encode()).hexdigest()
      and (c / "data" / "train.txt").read_text(encoding="utf-8") == train and not (tmp / "shuffled-run" / "shuffled").exists(),
      f"the shuffled control runs train.py in a folder of its own, on the training text's characters in another order "
      f"and without the sealed splits, and leaves the task's own data alone ({r.stderr.strip()[-300:]})")
r = run(c / "controls.py", "nosuchcontrol")
check(r.returncode == 1 and "controls.py constant" in r.stderr, "controls.py names its two controls when it is given another")
try:
    import torch  # noqa: F401
except ImportError:
    print("SKIP the constant control under the evaluator (PyTorch is not installed)")
else:
    r = run(c / "controls.py", "constant", env=dict(os.environ, EXP_RUN_DIR=str(tmp / "constant-run")))
    r2 = run(TASK / "evaluate.py", "--run-dir", tmp / "constant-run")
    got = json.loads(r2.stdout.strip().splitlines()[-1]).get("score") if r2.returncode == 0 else None
    check(r.returncode == 0 and got is not None and abs(got - bounds["constant"]) < 1e-4,
          f"the constant control passes the evaluator's contract and scores ln(65) ({got}; {(r.stderr + r2.stdout + r2.stderr).strip()[-300:]})")

# 2. a project with the kit
p = tmp / "with-kit"
r = run(KIT / "benchmarks" / "new_project.py", p)
check(r.returncode == 0, f"new_project.py creates a project ({r.stdout.strip()[-200:]} {r.stderr.strip()[-300:]})")
cfg = json.loads((p / ".claude" / "nn-training.json").read_text(encoding="utf-8"))
check(cfg["sealed_paths"] == task["sealed_paths"] and cfg["frozen_paths"] == task["frozen_paths"]
      and cfg["loop"]["editable_paths"] == ["train.py"] and cfg["loop"]["controls"] == task["loop"]["controls"],
      "the task's sealed, frozen and loop settings are in the config")
fe = cfg["final_eval_commands"]
check(len(fe) == 1 and "{python}" not in fe[0] and fe[0].endswith("evaluate.py --data data/test.txt --run-dir"),
      "the final evaluation command names an interpreter")
check(isinstance(cfg.get("snapshot"), dict) and "harness_paths" in cfg, "the kit's own config keys survive the merge")
check(not (p / "nn-training.task.json").exists() and (p / "train.py").is_file() and (p / "data" / "test.txt").is_file(),
      "task files are copied, the task settings file is not")
st = subprocess.run(["git", "-C", str(p), "status", "--porcelain"], capture_output=True, text=True)
n = subprocess.run(["git", "-C", str(p), "rev-list", "--count", "HEAD"], capture_output=True, text=True)
check(st.returncode == 0 and not st.stdout.strip() and n.stdout.strip() == "1", "the project is one clean commit")
r = run(p / ".claude" / "skills" / "nn-training" / "scripts" / "expctl.py", "--root", p, "status", "--brief")
check(r.returncode == 0, f"expctl status works in the new project ({r.stderr.strip()[-200:]})")
r = run(KIT / "benchmarks" / "new_project.py", p)
check(r.returncode != 0 and "not empty" in (r.stderr + r.stdout), "new_project.py refuses a folder that is not empty")

# 3. a project without the kit, and the pilot script's command line
q = tmp / "no-kit"
r = run(KIT / "benchmarks" / "new_project.py", q, "--no-kit")
check(r.returncode == 0 and not (q / ".claude").exists() and (q / "evaluate.py").is_file(), "--no-kit leaves the kit out")
r = run(KIT / "benchmarks" / "new_project.py", tmp / "x", "--task", "nosuchtask")
check(r.returncode != 0 and not (tmp / "x").exists(), "an unknown task is refused before anything is written")
r = run(KIT / "benchmarks" / "pilot.py", "--help")
check(r.returncode == 0 and "--old-kit" in r.stdout, "pilot.py loads and prints its options")
sys.path.insert(0, str(KIT / "benchmarks"))
import pilot  # noqa: E402

pilot.no_confirm(p)
cfg = json.loads((p / ".claude" / "nn-training.json").read_text(encoding="utf-8"))
st = subprocess.run(["git", "-C", str(p), "status", "--porcelain"], capture_output=True, text=True)
n = subprocess.run(["git", "-C", str(p), "rev-list", "--count", "HEAD"], capture_output=True, text=True)
check(cfg["loop"]["confirm"] is False and "controls" not in cfg["loop"] and not st.stdout.strip() and n.stdout.strip() == "2",
      "the pilot turns the loop's confirmation and control runs off in a commit of its own, so that the loop starts from "
      "a clean tree")
r = run(p / ".claude" / "skills" / "nn-training" / "scripts" / "expctl.py", "--root", p, "final-eval", "--", "runs/none")
rec = p / ".claude" / "state" / "final-eval" / "receipt.jsonl"
rows = [json.loads(x) for x in rec.read_text(encoding="utf-8").splitlines()] if rec.is_file() else []
check(r.returncode == 1 and [x["event"] for x in rows] == ["start", "end"] and rows[0]["args"] == ["runs/none"]
      and rows[1]["exit_code"] in (1, 3),  # 3: the evaluator finds no model there; 1: it finds no PyTorch
      f"expctl final-eval starts the task's final evaluation and records the use ({r.stdout.strip()[-300:]})")
try:
    import torch  # noqa: F401,F811
except ImportError:
    print("SKIP a run of train.py started with expctl launch (PyTorch is not installed)")
else:  # the run works from a copy of the source that has no .claude, and must find the logger all the same
    ex = p / ".claude" / "skills" / "nn-training" / "scripts" / "expctl.py"
    r = run(ex, "--root", p, "launch", "--name", "logged", "--seed", "1", "--", sys.executable, "train.py", "--seed", "1",
            "--time-budget", "2", env=dict(os.environ, CUDA_VISIBLE_DEVICES="-1"))  # on the CPU: Windows drops an empty value
    rid = (re.findall(r'"run_id": "([^"]+)"', r.stdout) or ["none"])[0]
    run(ex, "--root", p, "watch", rid, "--until", "terminal", "--max-time", "5m")
    rd = p / "runs" / rid
    rows = (rd / "metrics.jsonl").read_text(encoding="utf-8") if (rd / "metrics.jsonl").is_file() else ""
    log = (rd / "stdout.log").read_text(encoding="utf-8", errors="replace")[-300:] if (rd / "stdout.log").is_file() else r.stderr[-300:]
    check("dev/loss" in rows and (rd / "result.json").is_file() and (rd / "model.ts").is_file(),
          f"a run of train.py started with expctl launch is logged: metrics, a result and the model ({log.strip()})")
    top = (json.loads(run(ex, "--root", p, "status", "--no-gpu").stdout or "{}").get("top") or [{}])[0]
    check(top.get("run_id") == rid and str(top.get("ckpt")).endswith("model.ts"),
          f"expctl status lists that run as the best one, with the model it saved ({top})")

t0 = time.time()
code = pilot.run([sys.executable, "-c", "import json, time; print(json.dumps({'type': 'rate_limit_event', "
                  "'rate_limit_info': {'isUsingOverage': True}}), flush=True); time.sleep(60)"], tmp, 120, tmp / "paid.log")
check(code is None and time.time() - t0 < 30 and pilot.nnloop.paid_usage(tmp / "paid.log")[0],
      "the pilot ends a session at once when the agent reports that it is billed per use")


def bash(i, command):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": i, "name": "Bash", "input": {"command": command}}]}}


facts, trains, refused = pilot.session_facts("\n".join(json.dumps(e) for e in (
    {"type": "system", "subtype": "init", "model": "m", "claude_code_version": "1"},
    bash("a", "cat train.py; ls; python3 .claude/skills/nn-training/scripts/expctl.py status --brief"),
    bash("b", "python train.py --seed 1 --time-budget 30 && python train.py --seed 2 --time-budget 30"),
    bash("c", "python3 .claude/skills/nn-training/scripts/expctl.py launch --name x -- python3 train.py --seed 3"),
    bash("d", "python train.py --seed 4 --time-budget 30"),
    bash("e", "python .claude/skills/nn-training/scripts/expctl.py launch --help"),
    {"type": "result", "permission_denials": [{"tool_name": "Bash", "tool_use_id": "d", "tool_input": {}}]})))
check(facts == {"model": "m", "agent_version": "1"} and trains == 3 and refused == 1,
      "the pilot counts the shell commands that started training, not one that reads train.py, asks for help or was refused")
p = pilot.PROMPT.format(task="T", runs=3, py="PYX", kit="")
check("call `PYX`" in p and "refus" in p and "PYX train.py" in p,
      "the pilot tells its old and none sessions which shell commands are allowed and that a refusal is not the end")

# 4. the fine-tuning task: its data, its settings, the pins of its base model and what its evaluator refuses
FT = KIT / "benchmarks" / "finetune"
ft = json.loads((FT / "nn-training.task.json").read_text(encoding="utf-8"))
readme, seen = (FT / "README.md").read_text(encoding="utf-8"), []
for name in ("train.txt", "dev.txt", "loopval.txt", "test.txt"):
    raw = (FT / "data" / name).read_bytes()
    pairs = [x.split("\t") for x in raw.decode("utf-8").splitlines()]
    seen += [x[0] for x in pairs]
    check(f"| `{name}` | {len(pairs):,} | {len(raw):,} |" in readme and b"\r" not in raw
          and all(len(x) == 2 and all(x) for x in pairs) and len({x[-1] for x in pairs}) == 77,
          f"finetune: the README states rows and bytes of {name}, and every line is a message, a tab and one of 77 intents")
check(len(set(seen)) == len(seen), "finetune: no message is in two of the files, so none is both trained on and scored on")
check(set(ft["sealed_paths"]) == {"data/loopval.txt", "data/test.txt"} and {"evaluate.py", "data/**"} <= set(ft["frozen_paths"])
      and ft["loop"]["link_paths"] == ["model"] and pilot.nnloop.expctl.path_matches("model", ft["frozen_paths"])
      and ft["metric"]["direction"] == ft["loop"]["direction"] == "maximize",
      "finetune: the task seals the loop's and the final split, freezes the evaluator, the data and the base model that "
      "the loop links into its worktree, and counts a higher score as better")
check("dev score" in pilot.PROMPT and "loss" not in pilot.PROMPT, "the pilot's prompt asks for the score, whatever the task measures")

sys.path.insert(0, str(FT))
import fetch_model  # noqa: E402  (standard library only)

hexd = re.compile(r"[0-9a-f]+\Z")
check(len(fetch_model.REVISION) == 40 and bool(hexd.match(fetch_model.REVISION)) and "model.safetensors" in fetch_model.FILES
      and all(isinstance(s, int) and s > 0 and len(d) == 64 and hexd.match(d) for s, d in fetch_model.FILES.values()),
      "finetune: the base model is pinned to one revision, with a size and a SHA-256 for every file")


def fetch(body):
    """fetch_model.main() with `body` as what a download brings -> (what it ended with, the URLs it asked, the files kept)."""
    asked = []
    fetch_model.urllib.request.urlopen = lambda req, timeout=None: asked.append(req.full_url) or io.BytesIO(body)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            end = fetch_model.main(tmp / "model")
    except SystemExit as e:
        end = e.code
    return end, asked, sorted(x.name for x in (tmp / "model").iterdir())


fetch_model.FILES = {"a.txt": (3, hashlib.sha256(b"abc").hexdigest())}
end, asked, kept = fetch(b"abd")
check("SHA-256" in str(end) and kept == [] and asked == [f"https://huggingface.co/{fetch_model.REPO}/resolve/{fetch_model.REVISION}/a.txt"],
      "finetune: a download that is not the recorded file is not kept, and it is asked from the pinned revision")
check(fetch(b"abc") == (None, asked, ["a.txt"]) and fetch(b"abd") == (None, [], ["a.txt"]),
      "finetune: the recorded file is kept, and a file that is there is not fetched again")

ev = tmp / "run" / "adapter"
ev.mkdir(parents=True)
(ev / "adapter_config.json").write_text('{"peft_type": "LORA"}', encoding="utf-8")
(ev / "adapter_model.bin").write_bytes(b"x")
r = run(FT / "evaluate.py", "--run-dir", ev.parent)
(ev / "adapter_config.json").write_text('{"peft_type": "PREFIX_TUNING"}', encoding="utf-8")
(ev / "adapter_model.safetensors").write_bytes(b"")
r2 = run(FT / "evaluate.py", "--run-dir", ev.parent)
check(r.returncode == 3 and "adapter_model.safetensors" in str((pilot.nnloop.last_json(r.stdout) or {}).get("error"))
      and r2.returncode == 3 and "LoRA" in str((pilot.nnloop.last_json(r2.stdout) or {}).get("error")),
      "finetune: the evaluator refuses weights that are not in safetensors and an adapter that is not LoRA, and loads neither")

p = tmp / "finetune"
r = run(KIT / "benchmarks" / "new_project.py", p, "--task", "finetune")
cfg = json.loads((p / ".claude" / "nn-training.json").read_text(encoding="utf-8")) if r.returncode == 0 else {}
(p / "model").mkdir(exist_ok=True)
(p / "model" / "x.bin").write_bytes(b"x")  # stands for the fetched base model
st = subprocess.run(["git", "-C", str(p), "status", "--porcelain"], capture_output=True, text=True)
check(r.returncode == 0 and (cfg.get("loop") or {}).get("link_paths") == ["model"] and cfg.get("frozen_paths") == ft["frozen_paths"]
      and (cfg.get("metric") or {}).get("direction") == "maximize" and (p / "fetch_model.py").is_file() and not st.stdout.strip(),
      f"finetune: new_project.py builds the project with the task's settings, and a fetched base model stays out of its "
      f"history ({r.stderr.strip()[-300:]})")
shutil.rmtree(p / "model", ignore_errors=True)  # where the kit's folder holds the fetched model, this was a copy of 270 MB

print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES")
sys.exit(1 if FAILS else 0)
