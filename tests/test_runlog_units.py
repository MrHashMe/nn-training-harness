#!/usr/bin/env python3
"""Unit tests for runlog: atexit/uncaught paths, for_trial, pruned state, HF and Lightning adapters (stubbed)."""
import json
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path

from pathlib import Path as _P
SCRIPTS = str(_P(__file__).resolve().parents[1] / ".claude/skills/nn-training/scripts")
FAILS = []


def check(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


def run_py(code, cwd):
    env = os.environ.copy()
    env.pop("EXP_RUN_DIR", None)
    env["PYTHONPATH"] = SCRIPTS
    return subprocess.run([sys.executable, "-c", code], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)


tmp = Path(tempfile.mkdtemp(prefix="rlunit-"))

# 1. uncaught exception without context manager -> failed
r = run_py("from runlog import RunLog\nrl = RunLog(name='u')\nrl.log(1, **{'train/loss': 0.5})\nraise ValueError('boom')\n", tmp)
res = [json.loads(p.read_text()) for p in (tmp / "runs").glob("*u*/result.json")]
check(res and res[0]["state"] == "failed" and "boom" in res[0]["reason"], "uncaught exception -> failed with reason")

# 2. exit without finish and no context manager -> incomplete
r = run_py("from runlog import RunLog\nrl = RunLog(name='inc')\nrl.log(1, **{'x': 1})\n", tmp)
res = [json.loads(p.read_text()) for p in (tmp / "runs").glob("*inc*/result.json")]
check(res and res[0]["state"] == "incomplete", "exit without finish -> incomplete")

# 3. for_trial + pruned + best value returned
code = r'''
import sys, types
from runlog import RunLog
class TrialPruned(Exception): pass
class Trial:
    number = 3
    class study: study_name = "lr-sweep-v1"
    attrs = {}
    def set_user_attr(self, k, v): self.attrs[k] = v
t = Trial()
with RunLog.for_trial(t, metric="val/acc", direction="maximize", config={"lr": 1e-3}) as rl:
    rl.log(0, **{"val/acc": 0.5}); rl.checkpoint(rl.path("ckpt", "best.pt"), step=0, value=0.5, is_best=True)
    v = rl.best["value"]
print("best", v, t.attrs["run_dir"])
t2 = Trial(); t2.number = 4
try:
    with RunLog.for_trial(t2, metric="val/acc", direction="maximize") as rl2:
        rl2.log(0, **{"val/acc": 0.1})
        raise TrialPruned("pruned at step 0")
except TrialPruned:
    pass
'''
r = run_py(code, tmp)
check("best 0.5" in r.stdout, f"for_trial returns checkpointed best ({r.stdout.strip()} {r.stderr[-200:]})")
d3 = tmp / "runs" / "lr-sweep-v1-t0003"
d4 = tmp / "runs" / "lr-sweep-v1-t0004"
check(d3.is_dir() and json.loads((d3 / "result.json").read_text())["state"] == "completed", "trial dir sibling + completed")
check(json.loads((d4 / "result.json").read_text())["state"] == "pruned", "TrialPruned -> pruned")
man = json.loads((d3 / "manifest.json").read_text())
check(man["study"] == "lr-sweep-v1" and man["trial"] == 3, "trial manifest records study/trial")

# 4. HF adapter with a stub transformers module
code = r'''
import sys, types, os
tf = types.ModuleType("transformers")
class TrainerCallback: pass
tf.TrainerCallback = TrainerCallback
sys.modules["transformers"] = tf
from runlog import RunLog, hf_callback
class A: output_dir = "out"; metric_for_best_model = "accuracy"
class S: max_steps = 100; global_step = 10; epoch = 0.5; best_model_checkpoint = os.path.join("out", "checkpoint-10"); best_metric = 0.91
class C: should_save = False; should_training_stop = False
with RunLog(name="hf", metric="eval_accuracy", direction="maximize") as rl:
    cb = hf_callback(rl)
    a, s, c = A(), S(), C()
    cb.on_train_begin(a, s, c)
    cb.on_log(a, s, c, logs={"loss": 0.7, "learning_rate": 1e-4, "epoch": 0.5})
    cb.on_evaluate(a, s, c, metrics={"eval_accuracy": 0.91, "eval_loss": 0.3})
    cb.on_save(a, s, c)
    rl._stop_signal_test = True
    import runlog; runlog._STOP["signal"] = "SIGTERM"
    cb.on_step_end(a, s, c)
    print("stop", c.should_training_stop, c.should_save, rl.total_steps, rl.best)
'''
r = run_py(code, tmp)
check("stop True True 100" in r.stdout and "'eval_accuracy'" in r.stdout and "0.91" in r.stdout,
      f"HF adapter logs, records best checkpoint, honours stop ({r.stdout.strip()[:200]} {r.stderr[-300:]})")
hfres = [json.loads(p.read_text()) for p in (tmp / "runs").glob("*-hf-*/result.json")]
check(hfres and hfres[0]["state"] == "interrupted", f"HF run with observed stop -> interrupted ({hfres[0]['state'] if hfres else None})")

# 5. Lightning adapter with stub
code = r'''
import sys, types
L = types.ModuleType("lightning"); P = types.ModuleType("lightning.pytorch"); CB = types.ModuleType("lightning.pytorch.callbacks")
class Callback: pass
CB.Callback = Callback
sys.modules.update({"lightning": L, "lightning.pytorch": P, "lightning.pytorch.callbacks": CB})
from runlog import RunLog, lightning_callback
class MC: best_model_path = "ckpts/epoch=1.ckpt"; best_model_score = 0.42; monitor = "val_loss"; last_model_path = "ckpts/last.ckpt"
class T:
    estimated_stepping_batches = 500; global_step = 50; current_epoch = 1; sanity_checking = False
    callback_metrics = {"train_loss": 0.9, "val_loss": 0.42}
    checkpoint_callbacks = [MC()]; should_stop = False
with RunLog(name="pl", metric="val_loss", direction="minimize") as rl:
    cb = lightning_callback(rl, every_n_steps=10)
    t = T()
    cb.on_fit_start(t, None); cb.on_train_batch_end(t, None, None, None, 0); cb.on_validation_end(t, None); cb.on_fit_end(t, None)
    print("total", rl.total_steps, "best", rl.best, "last", rl.last_ckpt["path"], "stop", t.should_stop)
'''
r = run_py(code, tmp)
check("total 500" in r.stdout and "epoch=1.ckpt" in r.stdout and "last ckpts/last.ckpt" in r.stdout and "stop False" in r.stdout,
      f"Lightning adapter logs and mirrors checkpoints ({r.stdout.strip()[:220]} {r.stderr[-300:]})")

# 6. tensor-like values and non-finite tracking
code = r'''
from runlog import RunLog
class T:
    def __init__(self, v): self.v = v
    def item(self): return self.v
with RunLog(name="tens") as rl:
    rl.log(1, **{"a": T(0.25), "b": float("inf"), "c": "not-a-number", "d": True})
    print(rl.latest, rl.nonfinite)
'''
r = run_py(code, tmp)
check("'a': 0.25" in r.stdout and "['b']" in r.stdout and "'c'" not in r.stdout and "'d'" not in r.stdout,
      f"tensor .item() handled, inf tracked, strings/bools skipped ({r.stdout.strip()})")

# 7. distributed: only global rank 0 writes files; other ranks still get should_stop()
code = r"""
import os
os.environ["RANK"] = "1"
from runlog import RunLog
rl = RunLog(name="rank1")
rl.log(1, **{"x": 1.0}); rl.checkpoint("c.pt", is_best=True, value=1.0); rl.finish()
print("enabled", rl.enabled, "exists", rl.dir.exists(), "stop", rl.should_stop())
"""
r = run_py(code, tmp)
check("enabled False exists False stop False" in r.stdout, f"non-zero rank writes nothing ({r.stdout.strip()} {r.stderr[-200:]})")

# 7b. which process is the global rank 0: torchrun's RANK decides; without it, Lightning's own launcher gives the rank
#     on the node and the node's rank (was: neither was read, so each of its ranks wrote the run files)
code = r"""
import os, runlog
NAMES = ("RANK", "SLURM_PROCID", "OMPI_COMM_WORLD_RANK", "PMI_RANK", "LOCAL_RANK", "NODE_RANK")
out = []
for env in ({"LOCAL_RANK": "1", "NODE_RANK": "0"}, {"LOCAL_RANK": "0", "NODE_RANK": "1"}, {"LOCAL_RANK": "0", "NODE_RANK": "0"},
            {"SLURM_PROCID": "0", "LOCAL_RANK": "1"}, {"RANK": "0", "LOCAL_RANK": "0"}, {"RANK": "2", "LOCAL_RANK": "0"},
            {"RANK": "0", "SLURM_PROCID": "3"}, {"SLURM_PROCID": "2"}, {"RANK": "x"}, {}):
    for k in NAMES:
        os.environ.pop(k, None)
    os.environ.update(env)
    out.append(int(runlog._default_enabled()))
print("ranks", out)
"""
r = run_py(code, tmp)
check("ranks [0, 0, 1, 0, 1, 0, 1, 0, 1, 1]" in r.stdout,
      f"the ranks of Lightning's launcher (LOCAL_RANK, NODE_RANK, no RANK) write nothing except the first of the first "
      f"node, also inside a Slurm step; RANK decides where it is set ({r.stdout.strip()} {r.stderr[-200:]})")

# 8. numpy-like step values and the primary metric always kept in the heartbeat
code = r"""
import json
from runlog import RunLog
class NpInt:
    def __init__(s, v): s.v = v
    def item(s): return s.v
with RunLog(name="npstep", metric="val/acc", direction="maximize") as rl:
    rl.log(NpInt(7), **{f"k{i}": float(i) for i in range(60)})
    rl.log(8, **{"val/acc": 0.9})
    rl.heartbeat()
hb = json.load(open(rl.dir / "heartbeat.json"))
print("step", hb["step"], "metric_in_latest", "val/acc" in hb["latest"])
"""
r = run_py(code, tmp)
check("step 8 metric_in_latest True" in r.stdout, f"numpy-like steps coerced; metric kept in heartbeat ({r.stdout.strip()} {r.stderr[-200:]})")

# 9. EXP_SEED becomes the recorded seed when the code passes none
code = r"""
import json, os
os.environ["EXP_SEED"] = "11"
from runlog import RunLog
with RunLog(name="seedenv") as rl:
    pass
print("seed", json.load(open(rl.dir / "result.json"))["meta"]["seed"])
"""
r = run_py(code, tmp)
check("seed 11" in r.stdout, f"EXP_SEED recorded ({r.stdout.strip()} {r.stderr[-200:]})")

# 10. stop request file (`expctl stop` writes stop.json; on Windows it is the only graceful route): a request older
#     than the launch is ignored, a fresh one stops the loop, and a SIGTERM after it is still the first, graceful one
code = r"""
import json, os, signal, time
from runlog import RunLog
old = RunLog(name="stale")
(old.dir / "stop.json").write_text(json.dumps({"requested_ts": old.t0 - 100}))
print("stale", old.should_stop())
old.finish()
os.environ["EXP_RUN_DIR"] = str(old.dir)          # resumed by hand in the same directory: still the old request
print("hand-resume", RunLog().should_stop())
del os.environ["EXP_RUN_DIR"]
rl = RunLog(name="stopfile")
(rl.dir / "stop.json").write_text(json.dumps({"requested_ts": time.time()}))
with rl:
    print("fresh", rl.should_stop(), rl.stop_reason())
    if os.name != "nt":
        os.kill(os.getpid(), signal.SIGTERM)
    print("alive after SIGTERM")
print("state", json.load(open(rl.dir / "result.json"))["state"])
"""
r = run_py(code, tmp)
check(all(s in r.stdout for s in ("stale False", "hand-resume False", "fresh True received stop request",
                                  "alive after SIGTERM", "state interrupted")),
      f"stop.json: stale ignored, fresh stops, later SIGTERM stays graceful ({r.stdout.strip()} {r.stderr[-300:]})")

# 11. a stop requested while a launched trainer was still starting (after the launch, before its RunLog) is honoured
code = r"""
import json, os, time
from runlog import RunLog
d = os.path.abspath("sup-run"); os.makedirs(d)
json.dump({"requested_ts": time.time() - 10}, open(os.path.join(d, "stop.json"), "w"))
os.environ.update(EXP_RUN_DIR=d, EXP_LAUNCH_TS=repr(time.time() - 50))
print("startup-stop", RunLog().should_stop())
"""
r = run_py(code, tmp)
check("startup-stop True" in r.stdout, f"stop requested during startup is honoured ({r.stdout.strip()} {r.stderr[-300:]})")

# a result write that Windows refuses for a moment (a reader or a virus scan holds the file) is retried
code = """
import json, os, runlog
real, calls = os.replace, []
def busy(a, b):
    calls.append(1)
    if len(calls) < 3:
        raise PermissionError(13, "busy")
    return real(a, b)
os.replace = busy
runlog._write_json("r.json", {"ok": 1}, tries=40)
print("retried", len(calls), json.load(open("r.json")))
calls.clear()
try:
    runlog._write_json("h.json", {"ok": 1})
except PermissionError:
    print("single try raises", os.path.exists("h.json"))
"""
r = run_py(code, tmp)
check("retried 3 {'ok': 1}" in r.stdout and "single try raises False" in r.stdout,
      f"refused replace: result write retries, heartbeat write gives up at once ({r.stdout.strip()} {r.stderr[-300:]})")

# the same refusal while a run starts is retried too: on a Windows target the mirror of a remote run reads the run's
# files at short intervals, the temporary ones included
code = """
import json, os, runlog
real, calls = os.replace, {}
def busy(a, b):
    calls[str(b)] = calls.get(str(b), 0) + 1
    if calls[str(b)] < 3:
        raise PermissionError(13, "busy")
    return real(a, b)
os.replace = busy
with runlog.RunLog(run_dir="busy-start", config={"lr": 0.1}):
    pass
print("started", [n for n in ("manifest.json", "config.json", "env.json") if os.path.exists("busy-start/" + n)],
      json.load(open("busy-start/config.json")))
"""
r = run_py(code, tmp)
check("started ['manifest.json', 'config.json', 'env.json'] {'lr': 0.1}" in r.stdout,
      f"refused replace while a run starts: its first records are written after a retry ({r.stdout.strip()} {r.stderr[-300:]})")

# a write that gives up leaves no temporary file in the run directory, whether the replace was refused or the write
# itself failed (a full disk). Where the removal is refused as well (a reader holds the temporary file itself), the
# next write removes it
code = """
import json, os, runlog
real_replace, real_unlink, held = os.replace, os.unlink, [1]
def busy(a, b):
    if str(b).endswith("h.json"):
        raise PermissionError(13, "busy")
    return real_replace(a, b)
def unlink(p):
    if held:
        held.pop()
        raise PermissionError(13, "busy")
    return real_unlink(p)
os.replace, os.unlink = busy, unlink
os.mkdir("stray")
os.chdir("stray")
left = []
for _ in range(2):
    try:
        runlog._write_json("h.json", {"ok": 1})
    except PermissionError:
        left.append(len(os.listdir(".")))
def full(*a, **k):
    raise OSError(28, "No space left on device")
real_dump, json.dump = json.dump, full
try:
    runlog._write_json("f.json", {"ok": 1})
except OSError:
    left.append(len(os.listdir(".")))
json.dump = real_dump
runlog._write_json("r.json", {"ok": 1})
print("left", left, os.listdir("."))
"""
r = run_py(code, tmp)
check("left [1, 0, 0] ['r.json']" in r.stdout,
      f"a write that gives up, on a refused replace or a failed write, leaves no temporary file: it is removed at once "
      f"or with the next write ({r.stdout.strip()} {r.stderr[-300:]})")

print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES")
sys.exit(1 if FAILS else 0)
