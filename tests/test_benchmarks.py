#!/usr/bin/env python3
"""Tests for benchmarks/: new_project.py builds a usable project from the charlm task, and the task's data is the
text its README names; its controls; the fine-tuning task's data, settings, model pins and evaluator refusals.
Needs git; no GPU and no network. One check, of the constant control under the evaluator, needs PyTorch and is
skipped without it."""
import collections
import contextlib
import hashlib
import importlib.util
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
import warnings
import zipfile
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

    # the evaluator's contract, with one model that keeps it, three that each break it in one way, and two that keep
    # something between calls, which the evaluator does not let reach a later call
    import torch
    from torch.nn.functional import one_hot

    class Fair(torch.nn.Module):  # the token itself as the answer: causal, row by row, nothing kept
        def forward(self, idx):
            return one_hot(idx, 65).float()

    class Peek(torch.nn.Module):  # the next token as the answer, except at the one position a single probe at 64 compares
        def forward(self, idx):
            out = one_hot(torch.roll(idx, -1, 1), 65).float() * 10
            out[:, 63] = 0
            return out

    class Reads(torch.nn.Module):  # TorchScript can read a file into a tensor
        def forward(self, idx):
            return one_hot(idx, 65).float() + torch.from_file("data/loopval.txt", False, 4, dtype=torch.uint8).sum() * 0

    class Rows(torch.nn.Module):  # every row sees the whole batch
        def forward(self, idx):
            return one_hot(idx, 65).float() + idx.float().mean()

    class Counts(torch.nn.Module):  # a buffer that knows how often the model was called
        def __init__(self):
            super().__init__()
            self.register_buffer("calls", torch.zeros(1))

        def forward(self, idx):
            self.calls.add_(1)
            return one_hot(idx, 65).float() * self.calls

    class Sets(torch.nn.Module):  # the same with a plain attribute
        def __init__(self):
            super().__init__()
            self.n = 0

        def forward(self, idx):
            self.n += 1
            return one_hot(idx, 65).float()

    wants = {Fair: None, Peek: "looks ahead", Reads: "reads or writes files", Rows: "other rows of the batch",
             Counts: None, Sets: None}

    def answer(name, model):  # the evaluator's exit code and its JSON line for a model class or a model file's bytes
        d = tmp / ("model-" + name)
        d.mkdir()
        if isinstance(model, bytes):
            (d / "model.ts").write_bytes(model)
        else:
            torch.jit.script(model()).save(str(d / "model.ts"))
        r = run(TASK / "evaluate.py", "--run-dir", d)
        return r.returncode, json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {"error": r.stderr[-300:]}

    got = {c: answer(c.__name__, c) for c in wants}
    fair = got[Fair][1].get("score")
    check(got[Fair][0] == 0 and fair is not None
          and all(got[c][0] == 3 and w in got[c][1].get("error", "") for c, w in wants.items() if w),
          "the evaluator scores a model that is a function of each row's earlier tokens, and refuses one that looks ahead "
          "anywhere, one whose code reads a file (before it is loaded) and one whose rows see each other "
          f"({ {c.__name__: v for c, v in got.items()} })")
    check(fair is not None and all(got[c][0] == 0 and abs(got[c][1].get("score", 0) - fair) < 1e-9 for c in (Counts, Sets)),
          "a model that keeps something between calls is scored as on its first call: every call goes to a freshly "
          f"loaded copy, so that nothing it keeps reaches the next ({ {c.__name__: got[c] for c in (Counts, Sets)} })")

    # The file-reading model once more, its file written anew: the call spelled in another way, the code under another
    # name, a second entry of one name, and a second directory, which zipfile does not read. PyTorch 2.9.1 loaded the
    # reading code from every one of them (tried on 14 November 2026)
    def archive(edit):  # the Reads model's file, its code entry replaced by the entries that edit(name, code) returns
        buf = io.BytesIO()
        with zipfile.ZipFile(tmp / "model-Reads" / "model.ts") as zi, zipfile.ZipFile(buf, "w") as zo:
            for i in zi.infolist():
                data = zi.read(i)
                for n, c in (edit(i.filename, data) if i.filename.endswith(".py") and b"torch.from_file(" in data
                             else [(i.filename, data)]):
                    zo.writestr(n, c)
        return buf.getvalue()

    def clean(code):  # the same code without the call, at the same length
        c = re.sub(rb"torch\.from_file\([^)]*\)", b"torch.zeros([1])", code)
        return c + b"#" * (len(code) - len(c))

    forms = {"spaced": lambda n, c: [(n, c.replace(b"torch.from_file(", b"torch . from_file("))],
             "getattr": lambda n, c: [(n, c.replace(b"torch.from_file(", b'getattr(torch, "from_" "file")('))],
             "folder": lambda n, c: [(n.replace("/code/", "/Code/"), c)],
             "twice": lambda n, c: [(n, c), (n, clean(c))]}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # zipfile warns about a second entry of one name
        got = {k: answer(k, archive(f)) for k, f in forms.items()}
    reads, fair_zip = archive(lambda n, c: [(n, c)]), archive(lambda n, c: [(n, clean(c))])
    check(reads != fair_zip and all(v[0] == 3 and "reads or writes files" in v[1].get("error", "") for v in got.values()),
          "the evaluator refuses the file-reading model also where its call is spelled with blanks or through getattr "
          f"and joined strings, where its code lies under Code/, and where a second entry of the same name hides it ({got})")
    # the whole reading archive without its end record, and behind it the whole archive of the same model without the
    # call: zipfile reads the second, PyTorch's own reader the first
    two = answer("twodirs", reads[:reads.rfind(b"PK\x05\x06")] + fair_zip)
    check(two[0] == 0 and fair is not None and abs(two[1].get("score", 0) - fair) < 1e-9,
          "a file with a second directory is scored as the code that was read: what PyTorch loads is an archive the "
          f"evaluator wrote from the entries it read ({two})")

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
    r = run(ex, "--root", p, "launch", "--name", "stopped", "--seed", "1", "--", sys.executable, "train.py", "--seed", "1",
            "--time-budget", "600", env=dict(os.environ, CUDA_VISIBLE_DEVICES="-1"))
    rid = (re.findall(r'"run_id": "([^"]+)"', r.stdout) or ["none"])[0]
    rd, t0 = p / "runs" / rid, time.time()
    while not (rd / "heartbeat.json").is_file() and time.time() - t0 < 120:  # from then on the trainer can be asked
        time.sleep(0.5)
    run(ex, "--root", p, "stop", rid, "--wait", "4m")
    res = json.loads((rd / "result.json").read_text(encoding="utf-8")) if (rd / "result.json").is_file() else {}
    check(res.get("state") == "interrupted" and (rd / "model.ts").is_file() and time.time() - t0 < 300,
          "a stop request ends train.py's loop long before its time budget, and the run still saves its model (was: the "
          f"trainer never asked and was killed) ({res.get('state')}: {res.get('reason')}, {time.time() - t0:.0f} s)")

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
# what PEFT 0.21.2 saves for LoraConfig(), and the same with a key that names a library for PEFT to import
saved = {"task_type": None, "peft_type": "LORA", "auto_mapping": None, "peft_version": "0.21.2", "base_model_name_or_path": None,
         "revision": None, "inference_mode": False, "r": 8, "target_modules": None, "exclude_modules": None, "lora_alpha": 8,
         "lora_dropout": 0.0, "fan_in_fan_out": False, "bias": "none", "use_rslora": False, "modules_to_save": None,
         "init_lora_weights": True, "layers_to_transform": None, "layers_pattern": None, "rank_pattern": {}, "alpha_pattern": {},
         "megatron_config": None, "megatron_core": "megatron.core", "trainable_token_indices": None, "loftq_config": {},
         "eva_config": None, "corda_config": None, "lora_ga_config": None, "use_dora": False, "velora_config": None,
         "alora_invocation_tokens": None, "use_qalora": False, "qalora_group_size": 16, "monteclora_config": None,
         "layer_replication": None, "lora_bias": False, "target_parameters": None, "use_bdlora": None, "arrow_config": None,
         "kasa_config": None, "ensure_weight_tying": False}
spec = importlib.util.spec_from_file_location("ft_evaluate", FT / "evaluate.py")
ft_evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ft_evaluate)
(ev / "adapter_config.json").write_text(json.dumps(dict(saved, auto_mapping={"base_model_class": "X", "parent_library": "os"},
                                                        megatron_core="os")), encoding="utf-8")
r = run(FT / "evaluate.py", "--run-dir", ev.parent)
far = tmp / "elsewhere"
shutil.copytree(ev, far)
(far / "adapter_config.json").write_text(json.dumps(saved), encoding="utf-8")
shutil.rmtree(ev)
try:
    ev.symlink_to(far, target_is_directory=True)
except OSError:  # Windows without the symlink privilege: a junction
    subprocess.run(["cmd", "/c", "mklink", "/J", str(ev), str(far)], capture_output=True, check=True)
r2 = run(FT / "evaluate.py", "--run-dir", ev.parent)
check(ft_evaluate.other_keys(saved) == [] and r.returncode == 3
      and "auto_mapping, megatron_core" in str((pilot.nnloop.last_json(r.stdout) or {}).get("error"))
      and r2.returncode == 3 and "outside the run folder" in str((pilot.nnloop.last_json(r2.stdout) or {}).get("error")),
      "finetune: the evaluator takes the config that PEFT saves, refuses one that names a library to import, and refuses "
      f"an adapter that is a link out of the run folder ({r.stdout.strip()[-200:]} {r2.stdout.strip()[-200:]})")

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

# 4b. the fine-tuning task's control: train.py on the training messages with their intents dealt out again
fctl = ft["loop"].get("controls") or [{}]
floor = fctl[0].get("floor", 1)
check(len(fctl) == 1 and fctl[0].get("name") == "shuffled" and 0 < floor < 0.2 and f"floor of {floor}" in readme
      and "controls.py" in ft["frozen_paths"] and (cfg.get("loop") or {}).get("controls") == fctl and (p / "controls.py").is_file(),
      "finetune: the shuffled control is frozen, its measured floor is the one the README states, far below what the "
      "baseline scores, and a project made from the task has both")
c = tmp / "ftcontrols"
shutil.copytree(FT, c, ignore=shutil.ignore_patterns("__pycache__", "out", "runs", "model"))
(c / "train.py").write_text('''import hashlib, json, os, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import evaluate
pairs = evaluate.read(here / "data" / "train.txt")
(Path(sys.argv[sys.argv.index("--out") + 1]) / "seen.json").write_text(json.dumps({
    "argv": sys.argv[1:], "here": os.path.samefile(os.getcwd(), here), "files": sorted(p.name for p in (here / "data").iterdir()),
    "messages": hashlib.sha256("\\n".join(t for t, _ in pairs).encode()).hexdigest(), "intents": [x for _, x in pairs],
    "evaluator": evaluate.__file__}))
''', encoding="utf-8")  # stands for train.py: it writes down what the control gave it
pairs = [x.split("\t") for x in (FT / "data" / "train.txt").read_text(encoding="utf-8").splitlines()]
r = run(c / "controls.py", "shuffled", "--seed", "7", env=dict(os.environ, EXP_RUN_DIR=str(tmp / "ft-shuffled-run")))
seen = json.loads((tmp / "ft-shuffled-run" / "seen.json").read_text(encoding="utf-8")) if r.returncode == 0 else {}
got = seen.get("intents") or []
check(seen.get("argv", [])[:2] == ["--seed", "7"] and seen.get("here") and seen.get("files") == ["dev.txt", "train.txt"]
      and seen.get("messages") == hashlib.sha256("\n".join(x[0] for x in pairs).encode()).hexdigest()
      and sorted(got) == sorted(x[1] for x in pairs) and sum(a == x[1] for a, x in zip(got, pairs)) < len(pairs) / 20
      and os.path.samefile(seen.get("evaluator") or c, c / "evaluate.py")
      and (c / "data" / "train.txt").read_bytes() == (FT / "data" / "train.txt").read_bytes()
      and not (tmp / "ft-shuffled-run" / "shuffled").exists(),
      f"finetune: the shuffled control runs train.py in a folder of its own, on the same messages with the same intents "
      f"in another order, without the sealed splits and with the task's own evaluator, and leaves the task's data alone "
      f"({r.stderr.strip()[-300:]})")
r = run(c / "controls.py", "nosuchcontrol")
check(r.returncode == 1 and "controls.py shuffled" in r.stderr, "finetune: controls.py names its control when it is given another")

print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES")
sys.exit(1 if FAILS else 0)
