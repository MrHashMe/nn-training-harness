#!/usr/bin/env python3
"""End-to-end tests for the nn-training harness kit (expctl, runlog, guard, session hook, statusline).

Run from anywhere:  python tests/test_kit.py   (Linux, macOS, native Windows; takes ~2 minutes; uses a temporary
git repo and short CPU-only fake training runs; Optuna is stubbed so it is not required).
"""
import base64
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
PY = sys.executable
FAILS = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def sh(cmd, cwd, env=None, inp=None, timeout=60):
    e = os.environ.copy()
    e.pop("CLAUDE_PROJECT_DIR", None)
    if env:
        e.update(env)
    r = subprocess.run(cmd, cwd=cwd, env=e, input=inp, capture_output=True, text=True, timeout=timeout)
    return r


def expctl(proj, *args, env=None, timeout=60):
    return sh([PY, str(proj / ".claude/skills/nn-training/scripts/expctl.py"), *args], cwd=proj, env=env, timeout=timeout)


def jout(r):
    try:
        return json.loads(r.stdout)
    except ValueError:
        print("STDOUT:", r.stdout[-2000:], "\nSTDERR:", r.stderr[-2000:])
        raise


def hard_kill(pid, tree=False):
    """SIGKILL for one process or its group; on Windows, where neither exists, taskkill /F (with /T for the tree)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"] + (["/T"] if tree else []), capture_output=True)
    elif tree:
        os.killpg(pid, signal.SIGKILL)
    else:
        os.kill(pid, signal.SIGKILL)


TRAIN = r'''
import argparse, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from runlog import RunLog
p = argparse.ArgumentParser()
p.add_argument("--steps", type=int, default=40)
p.add_argument("--sleep", type=float, default=0.05)
p.add_argument("--mode", default="ok")
p.add_argument("--seed", type=int, default=0)
p.add_argument("--lr", type=float, default=0.1)
a = p.parse_args()
best = -1.0
with RunLog(config=vars(a), seed=a.seed, total_steps=a.steps, metric="val/acc", direction="maximize", heartbeat_every=0.2) as rl:
    for step in range(a.steps):
        time.sleep(a.sleep)
        loss = 1.0 / (1 + step * a.lr)
        if a.mode == "nan" and step >= 10:
            loss = float("nan")
        rl.log(step, epoch=step // 10, **{"train/loss": loss, "lr": a.lr})
        if a.mode == "crash" and step == 10:
            raise RuntimeError("CUDA out of memory (simulated)")
        if a.mode == "hang" and step == 5:
            while True:
                time.sleep(0.5)
        if a.mode == "vanish" and step == 5:
            os._exit(0)  # exit code 0 without RunLog's exit hooks, like a process terminated from outside
        if step % 5 == 4:
            acc = 1 - loss / 2 + 0.001 * a.seed
            rl.log(step, **{"val/acc": acc})
            last = rl.path("ckpt", "last.pt"); last.write_text(str(step)); rl.checkpoint(last, step=step)
            if acc > best:
                best = acc
                b = rl.path("ckpt", "best.pt"); b.write_text(str(step))
                rl.checkpoint(b, step=step, value=acc, is_best=True)
        if rl.should_stop():
            last = rl.path("ckpt", "last.pt"); last.write_text(str(step)); rl.checkpoint(last, step=step)
            break
print("done", flush=True)
'''

FINAL = r'''
import json, os, sys
print(json.dumps({"argv": sys.argv[1:], "unseal": os.environ.get("NN_UNSEAL_TEST"), "cwd": os.getcwd()}))
sys.exit(3 if "--fail" in sys.argv else 0)
'''


def setup(tmp: Path):
    proj = tmp / "proj"
    proj.mkdir()
    shutil.copytree(KIT / ".claude", proj / ".claude")
    (proj / "tools").mkdir()
    shutil.copy(KIT / ".claude/skills/nn-training/scripts/runlog.py", proj / "tools/runlog.py")
    (proj / "train.py").write_text(TRAIN)
    (proj / "eval").mkdir()
    (proj / "eval/metrics.py").write_text("def acc(p, y):\n    return (p == y).mean()\n")
    (proj / "sub").mkdir()
    (proj / "sub/hello.py").write_text("import os; print('cwd', os.getcwd()); print(open('../data/train.csv').read())\n")
    (proj / "big.bin").write_bytes(os.urandom(5000))
    (proj / "data/test").mkdir(parents=True)
    (proj / "data/train.csv").write_text("x,y\n1,2\n")
    (proj / "data/test/labels.csv").write_text("y\n1\n")
    (proj / ".gitignore").write_text("data/\nruns/\n.claude/state/\n__pycache__/\n")
    cfg = json.loads((proj / ".claude/nn-training.json").read_text()) if (proj / ".claude/nn-training.json").exists() else {}
    cfg.update({"metric": {"name": "val/acc", "direction": "maximize", "select": "best"},
                "heartbeat_stale_seconds": 3, "kill_after_s": 3, "min_free_disk_gb": 0,
                "snapshot": {"mode": "copy", "max_file_mb": 0.004},
                "sealed_paths": ["data/test/**"], "sealed_tokens": ["NN_UNSEAL_TEST"],
                "frozen_paths": ["eval/metrics.py"],
                "final_eval_commands": ["NN_UNSEAL_TEST=1 python eval/final.py"]})
    (proj / ".claude/nn-training.json").write_text(json.dumps(cfg, indent=1))
    for c in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"]):
        subprocess.run(c, cwd=proj, check=True)
    (proj / "untracked_new.py").write_text("print('new')\n")
    (proj / "eval/metrics.py").write_text("def acc(p, y):\n    return float((p == y).mean())\n")  # dirty
    return proj


def wait_for(fn, timeout=20, every=0.2):
    t = time.time()
    while time.time() - t < timeout:
        v = fn()
        if v:
            return v
        time.sleep(every)
    return None


def state_of(proj, rid):
    st = jout(expctl(proj, "status", "--no-gpu"))
    for group in ("active",):
        for r in st[group]:
            if r["run_id"] == rid:
                return r["state"], st
    for r in st["recent"]:
        if r["run_id"] == rid:
            return r["state"], st
    d = jout(expctl(proj, "status", "--run", rid))
    return d["state"], st


def main():
    tmp = Path(tempfile.mkdtemp(prefix="nnkit-"))
    proj = setup(tmp)
    print("project:", proj)

    # 1. empty status
    st = jout(expctl(proj, "status", "--no-gpu"))
    check(st["total_runs"] == 0 and st["counts"] == {}, "empty status has zero runs")
    check(any("no runs" in n for n in st["notes"]), "empty status explains no runs")

    # 2. hash + env
    h = jout(expctl(proj, "hash"))
    check(len(h["source_hash"]) == 64 and h["git"]["dirty"], "hash reports source hash and dirty tree")
    check(h["files_size_only"] >= 1, "large tracked file hashed by size only")
    made = [proj / n for n in ("AGENTS.md", ".mcp.json", ".codex/hooks.json", ".cursor/cli.json",
                               ".agents/skills/x/SKILL.md", "experiments/JOURNAL.md")]
    for p in made:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x\n")
    h2 = jout(expctl(proj, "hash"))
    check(h2["source_hash"] == h["source_hash"] and h2["git"]["dirty_examples"] == h["git"]["dirty_examples"],
          "the files of the agent ports and the journal are not experiment source: they change neither the source hash "
          f"nor the list of uncommitted changes ({h2['git']['dirty_examples']})")
    for p in made[:2]:
        p.unlink()
    for n in (".codex", ".cursor", ".agents", "experiments"):
        shutil.rmtree(proj / n)
    e = jout(expctl(proj, "env", "--python", PY))
    check("interpreter" in e and "packages" in e["interpreter"], "env probes interpreter packages")
    # --probe tries what training relies on for speed, each in a process of its own. Here a stand-in torch in the
    # project folder answers, so the check needs neither torch nor a GPU
    pp = tmp / "probe-proj"
    pp.mkdir()
    (pp / "torch.py").write_text("raise ImportError('stand-in')\n")
    e = jout(sh([PY, str(proj / ".claude/skills/nn-training/scripts/expctl.py"), "--root", str(pp), "env", "--python", PY,
                 "--probe"], cwd=pp))
    fp = (e.get("interpreter") or {}).get("fast_paths") or {}
    check(list(fp) == ["cuda", "bf16_autocast", "flash_attention", "fused_adamw", "compile"]
          and all(v == "failed: ImportError: stand-in" for v in fp.values()),
          f"env --probe reports each fast path from a process of its own, run in the project folder ({fp})")
    code = ("import json, os, sys\nsys.path.insert(0, sys.argv[1])\nimport expctl\n"
            "die = 'import os; os._exit(-1073741819)' if os.name == 'nt' else 'import os; os.kill(os.getpid(), 9)'\n"
            "expctl.FAST_PATHS = [('fine', False, 30, 'print(1); print(\"cpu, 2 s\")'), ('broken', False, 30, 'raise RuntimeError(\"no kernel\")'),\n"
            "                     ('dies', False, 30, die), ('slow', False, 1, 'import time; time.sleep(30)'), ('gpu', True, 30, 'print(1)')]\n"
            "adv = [len(expctl.advisories({'datasets': v, 'torch': t})) for v, t in\n"
            "       (('5.1.0', '2.15.0'), ('5.2.0', '2.9.1+cu130'), ('5.2', None), (None, '2.14.1+cu130'), ('4.0.0', '2.13.0'))]\n"
            "print(json.dumps([expctl.fast_paths(sys.executable, '.', False), adv, expctl.advisories({'datasets': '5.1.0'})]))\n")
    r = sh([PY, "-c", code, str(proj / ".claude/skills/nn-training/scripts")], cwd=proj)
    fp, adv, text = json.loads(r.stdout) if r.returncode == 0 else ({}, [], [])
    check(fp.get("fine") == "ok (cpu, 2 s)" and fp.get("broken") == "failed: RuntimeError: no kernel"
          and str(fp.get("dies")).startswith("crashed: exit code ") and fp.get("slow") == "timeout after 1 s"
          and str(fp.get("gpu")).startswith("skipped"),
          f"a fast path that fails, ends the interpreter or hangs is reported and the others still run ({fp} {r.stderr[-300:]})")
    check(adv == [1, 0, 0, 1, 2] and "CVE-2026-57845" in "".join(text) and "5.2.0" in "".join(text),
          f"env warns about an installed version that a dated advisory names, and not about a fixed one ({adv} {text})")
    # audit-splits: how many records the configured splits share. Counts only, never a row.
    sp = tmp / "split-proj"
    (sp / ".claude").mkdir(parents=True)
    (sp / "data/test").mkdir(parents=True)
    scfg = {"splits": {"train": "data/train.jsonl", "val": "data/val.csv", "test": "data/test"}}
    (sp / ".claude/nn-training.json").write_text(json.dumps(scfg))
    train = ['{"text": "The  cat sat", "label": 1}', '{"label": 1, "text": "the cat sat"}', '{"text": "a dog", "label": 0}', "",
             '{"text": "ﬁne Über", "label": 2}']
    (sp / "data/train.jsonl").write_text("\n".join(train) + "\n", encoding="utf-8")
    (sp / "data/val.csv").write_text('text,label\n"THE CAT   SAT",1\n"a bird",0\n', encoding="utf-8")
    (sp / "data/test/a.jsonl").write_text('{"label": 0, "text": "A dog"}\n{"text": "a fish", "label": 1}\n', encoding="utf-8")
    (sp / "data/test/.gitkeep").write_text("")

    def audit(*args):
        r = sh([PY, str(proj / ".claude/skills/nn-training/scripts/expctl.py"), "--root", str(sp), "audit-splits", *args], cwd=sp)
        return r, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else {})

    r, a = audit()
    s, shared = a.get("splits") or {}, {tuple(x["splits"]): x["shared"] for x in a.get("shared") or []}
    check(r.returncode == 1 and a.get("ok") is False
          and [(s[n]["records"], s[n]["unique"]) for n in ("train", "val", "test")] == [(4, 3), (2, 2), (2, 2)]
          and shared == {("train", "val"): 0, ("train", "test"): 1, ("val", "test"): 0}
          and s["test"]["counted"] == {"rows": 2} and not any(w in r.stdout.lower() for w in ("cat", "dog", "fish", "bird")),
          f"audit-splits counts records, distinct records and the records two splits share, and prints no row ({r.stdout[-600:]} {r.stderr[-300:]})")
    r, k = audit("--key", "text")
    ks, kshared = k.get("splits") or {}, {tuple(x["splits"]): x["shared"] for x in k.get("shared") or []}
    check(r.returncode == 1 and kshared == {("train", "val"): 1, ("train", "test"): 1, ("val", "test"): 0}
          and (ks["train"]["records"], ks["train"]["unique"]) == (4, 3) and k.get("key") == "text",
          f"audit-splits --key compares one field, across .jsonl and .csv files and whatever the case or spacing ({kshared})")
    (sp / "data/train.jsonl").write_text("\n".join(reversed(train)) + "\n", encoding="utf-8")
    again = audit()[1]
    (sp / "data/train.jsonl").write_text("\n".join(train[2:]) + "\n", encoding="utf-8")
    r, less = audit()
    rec = sp / ".claude/state/final-eval/split-audits.jsonl"
    lines = rec.read_bytes().splitlines() if rec.is_file() else []
    check(again["splits"]["train"]["fingerprint"] == s["train"]["fingerprint"] != less["splits"]["train"]["fingerprint"]
          and less["splits"]["test"]["fingerprint"] == s["test"]["fingerprint"] and len(s["train"]["fingerprint"]) == 64
          and len(lines) == 4 and json.loads(lines[1])["prev"] == hashlib.sha256(lines[0]).hexdigest()
          and json.loads(lines[1])["key"] == "text" and b"dog" not in rec.read_bytes().lower(),
          "audit-splits gives each split a fingerprint that the order of its records does not change and a changed "
          "record does, and appends every audit to a chained record")
    (sp / "data/test/b.parquet").write_bytes(b"PAR1")
    packed = audit()[0]
    (sp / "data/test/b.parquet").unlink()
    nokey = audit("--key", "nope")[0]
    (sp / ".claude/nn-training.json").write_text("{}")
    unset = audit()[0]
    check(packed.returncode == 2 and "project's own loader" in packed.stdout and nokey.returncode == 2
          and "no records with the field 'nope'" in nokey.stdout and unset.returncode == 2 and "names no splits" in unset.stdout
          and len(rec.read_bytes().splitlines()) == 4,
          f"audit-splits refuses a file it cannot read record by record, a field no row has and a config without splits "
          f"({packed.stdout[-200:]} {nokey.stdout[-200:]} {unset.stdout[-200:]})")

    def audit_guard():
        r = sh([PY, str(proj / ".claude/hooks/nn_guard.py")], cwd=sp, env={"CLAUDE_PROJECT_DIR": str(sp)},
               inp=json.dumps({"tool_name": "Bash", "session_id": "t", "cwd": str(sp),
                               "tool_input": {"command": "python expctl.py --root . audit-splits --key text"}}))
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else r.returncode

    (sp / ".claude/nn-training.json").write_text(json.dumps(scfg))
    free = audit_guard()
    (sp / ".claude/nn-training.json").write_text(json.dumps(dict(scfg, sealed_paths=["data/test/**"])))
    asked = audit_guard()
    check(free == 0 and asked == "ask",
          f"the guard asks before an audit of splits where the config seals a path, and not where nothing is sealed ({free}, {asked})")

    # 3. launch OK run (snapshot copy)
    # 200 steps (10 s): the run must still be alive when the status line and the watch below look at it, and every
    # expctl call costs a few tenths of a second on Windows
    (proj / ".env").write_text("API_KEY=not-a-real-key\n")  # git has not been told to ignore it: it counts as source
    r = expctl(proj, "launch", "--name", "ok-run", "--seed", "1", "--note", "baseline", "--", PY, "train.py", "--steps", "200", "--seed", "1")
    lo = jout(r)
    check(lo["ok"] and lo["pid"], "launch ok-run returns pid")
    rid_ok = lo["run_id"]
    rd = proj / lo["run_dir"]
    check((rd / "src/train.py").exists() and (rd / "src/untracked_new.py").exists(), "snapshot copied tracked+untracked files")
    # samefile() is true for a symlink and for its Windows stand-ins (junction, hard link), false for a copy
    check(os.path.samefile(rd / "src/data/train.csv", proj / "data/train.csv") and not (rd / "src/data/test").exists()
          and not os.path.samefile(rd / "src/data", proj / "data"),
          "snapshot links ignored data but leaves the sealed test split out")
    check(os.path.samefile(rd / "src/big.bin", proj / "big.bin"), "snapshot links large tracked file")
    check(os.path.samefile(rd / "src/.env", proj / ".env"),
          "snapshot links a file named like a credential: the runs folder gets no copy of it (was: copied)")
    check("return float" in (rd / "src/eval/metrics.py").read_text(), "snapshot contains uncommitted changes")
    check((rd / "src.patch").exists(), "uncommitted patch saved")
    # mid-run status
    ok_running = wait_for(lambda: state_of(proj, rid_ok)[0] == "running", 15)
    check(bool(ok_running), "ok-run observed running")
    wait_for(lambda: any(a.get("step") for a in jout(expctl(proj, "status", "--no-gpu"))["active"] if a["run_id"] == rid_ok), 10)
    st = jout(expctl(proj, "status", "--no-gpu"))
    act = [a for a in st["active"] if a["run_id"] == rid_ok]
    check(bool(act) and "progress" in act[0], "active entry has progress")
    # duplicate refused
    dup = expctl(proj, "launch", "--name", "ok-run", "--seed", "1", "--", PY, "train.py", "--steps", "200", "--seed", "1")
    check(dup.returncode == 4, "duplicate launch refused")
    # statusline
    sl = sh([PY, str(proj / ".claude/hooks/nn_statusline.py")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)},
            inp=json.dumps({"model": {"display_name": "Opus"}}))
    check("train: 1 running" in sl.stdout, f"statusline prints: {sl.stdout.strip()}")
    # its liveness probe once was os.kill(pid, 0), which terminates the process on Windows
    check(state_of(proj, rid_ok)[0] == "running", "statusline leaves the run alive")

    # 3b. watch (Monitor-style event stream) on the running ok-run
    wproc = subprocess.Popen([PY, str(proj / ".claude/skills/nn-training/scripts/expctl.py"), "watch", rid_ok,
                              "--interval", "1s", "--max-time", "90s", "--heartbeat", "20s"],
                             cwd=proj, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # 3c. tmux-detached launch (skipped when tmux is not installed)
    tm = None
    if shutil.which("tmux"):
        tm = jout(expctl(proj, "launch", "--via", "tmux", "--name", "tmuxrun", "--", PY, "train.py", "--steps", "30", "--seed", "5"))
        check(tm.get("ok") and tm.get("pid") and tm.get("via") == "tmux", f"tmux launch reports pid ({tm.get('pid')}, {tm.get('via')})")
        sess = json.loads((proj / tm["run_dir"] / "manifest.json").read_text()).get("tmux_session")
        check(bool(sess) and subprocess.run(["tmux", "has-session", "-t", sess]).returncode == 0, "tmux session exists while running")
    else:
        print("SKIP tmux tests (tmux not installed)")

    # 4. crash, nan, nopoll-hang, no-runlog, deadline, subdir
    crash = jout(expctl(proj, "launch", "--name", "crash", "--", PY, "train.py", "--mode", "crash"))
    nan = jout(expctl(proj, "launch", "--name", "nan", "--", PY, "train.py", "--mode", "nan", "--steps", "20"))
    hang = jout(expctl(proj, "launch", "--name", "hang", "--", PY, "train.py", "--mode", "hang"))
    plain = jout(expctl(proj, "launch", "--name", "plain", "--snapshot", "none", "--", PY, "-c", "print('plain ok')"))
    vanish = jout(expctl(proj, "launch", "--name", "vanish", "--", PY, "train.py", "--mode", "vanish"))
    dl = jout(expctl(proj, "launch", "--name", "deadline", "--deadline", "2s", "--", PY, "train.py", "--steps", "2000"))
    subr = expctl(proj, "launch", "--name", "subdir", "--", PY, "hello.py", env=None, timeout=60)
    # launch from subdir: emulate by running expctl with cwd=sub
    subr = sh([PY, str(proj / ".claude/skills/nn-training/scripts/expctl.py"), "--root", str(proj), "launch", "--name", "subdir", "--", PY, "hello.py"], cwd=proj / "sub")
    sub = jout(subr)

    def terminal(rid):
        s, _ = state_of(proj, rid)
        return s if s not in ("starting", "running", "stalled") else None

    check(wait_for(lambda: terminal(crash["run_id"]) == "failed", 20) is not None, "crash run -> failed")
    det = jout(expctl(proj, "status", "--run", crash["run_id"]))
    check("CUDA out of memory" in (det.get("reason") or ""), f"crash reason captured: {det.get('reason')}")
    check(wait_for(lambda: terminal(nan["run_id"]), 20) is not None, "nan run terminates")
    stn = jout(expctl(proj, "status", "--no-gpu"))
    check(any("non-finite" in a and nan["run_id"] in a for a in stn["alerts"]), "non-finite alert raised")
    check(wait_for(lambda: terminal(plain["run_id"]) == "completed", 15) is not None, "plain (no runlog) -> completed (inferred)")
    detp = jout(expctl(proj, "status", "--run", plain["run_id"]))
    check("inferred" in detp, "plain run flagged as inferred")
    check(wait_for(lambda: terminal(vanish["run_id"]) == "incomplete", 15) is not None,
          "exit code 0 without RunLog's result.json -> incomplete, not completed")
    check(wait_for(lambda: terminal(dl["run_id"]) == "timeout", 25) is not None, "deadline run -> timeout")
    check(wait_for(lambda: terminal(sub["run_id"]) == "completed", 15) is not None, "subdir launch completes")
    subdet = jout(expctl(proj, "status", "--run", sub["run_id"]))
    check(any("x,y" in ln for ln in subdet["log_tail"]) and any("/src/sub" in ln.replace("\\", "/") for ln in subdet["log_tail"]),
          "subdir run executed in snapshot/sub with data link")

    # stalled detection
    stalled = wait_for(lambda: state_of(proj, hang["run_id"])[0] == "stalled", 20)
    check(bool(stalled), "hanging run -> stalled")
    sth = jout(expctl(proj, "status", "--no-gpu"))
    check(any("heartbeat" in a and hang["run_id"] in a for a in sth["alerts"]), "stalled alert raised")
    # stop (escalates to SIGKILL because the loop does not poll)
    stp = jout(expctl(proj, "stop", hang["run_id"], "--wait", "20s", timeout=40))
    check(stp["ok"] and stp.get("final_state") == "interrupted", f"stop of hanging run -> interrupted ({stp})")
    ex = json.loads((proj / hang["run_dir"] / "exit.json").read_text())
    check(ex.get("escalated_to_sigkill") is True, "supervisor escalated to SIGKILL after kill_after_s")

    # graceful stop of a polling run
    long = jout(expctl(proj, "launch", "--name", "long", "--", PY, "train.py", "--steps", "5000", "--sleep", "0.02"))
    wait_for(lambda: state_of(proj, long["run_id"])[0] == "running", 15)
    stp2 = jout(expctl(proj, "stop", long["run_id"], "--wait", "20s", timeout=40))
    res2 = json.loads((proj / long["run_dir"] / "result.json").read_text())
    check(stp2.get("final_state") == "interrupted" and res2["state"] == "interrupted" and res2["last_ckpt"],
          "graceful stop -> RunLog interrupted with last checkpoint")

    # lost run: SIGKILL supervisor + child
    lost = jout(expctl(proj, "launch", "--name", "lost", "--", PY, "train.py", "--steps", "5000", "--sleep", "0.02"))
    wait_for(lambda: state_of(proj, lost["run_id"])[0] == "running", 15)
    pj = json.loads((proj / lost["run_dir"] / "pid.json").read_text())
    hard_kill(pj["supervisor_pid"])
    hard_kill(pj["pid"], tree=True)
    check(wait_for(lambda: state_of(proj, lost["run_id"])[0] == "lost", 10) is not None, "killed run -> lost")

    # ok run completes; top list + curve
    check(wait_for(lambda: terminal(rid_ok) == "completed", 30) is not None, "ok-run completes")
    wout, werr = wproc.communicate(timeout=120)
    evs = [json.loads(l) for l in wout.splitlines() if l.strip()]
    kinds = [e["event"] for e in evs]
    check(kinds and kinds[0] == "watching" and "metric" in kinds and kinds[-1] == "done"
          and any(e["event"] == "state" and e.get("to") == "completed" for e in evs),
          f"watch emits watching/metric/state/done events ({kinds[:3]}...{kinds[-2:]}, n={len(evs)}) {werr[-200:]}")
    check(all(len(l) <= 600 for l in wout.splitlines()), "watch lines are bounded")
    if tm:
        check(wait_for(lambda: terminal(tm["run_id"]) == "completed", 30) is not None, "tmux-launched run completes")
        check(subprocess.run(["tmux", "has-session", "-t", sess], capture_output=True).returncode != 0, "tmux session closed after run")
    st = jout(expctl(proj, "status", "--no-gpu"))
    check(st["top"] and st["top"][0]["run_id"] == rid_ok and st["top"][0]["ckpt"], "top lists ok-run with checkpoint")
    check(st["counts"].get("failed", 0) >= 1 and st["counts"].get("lost", 0) == 1, f"counts by state: {st['counts']}")
    cv = jout(expctl(proj, "curve", rid_ok, "--points", "10"))
    check("val/acc" in cv["series"] and len(cv["series"]["val/acc"]["points"]) <= 11 and cv["series"]["train/loss"]["last20pct_trend"],
          "curve downsamples and reports trend")
    br = expctl(proj, "status", "--brief", "--no-gpu").stdout
    check("TOP:" in br and "runs:" in br, "brief status renders")
    # missing checkpoint -> ineligible + alert
    ok_dir = proj / lo["run_dir"]
    best_ckpt = json.loads((ok_dir / "result.json").read_text())["best"]["ckpt"]
    Path(best_ckpt).rename(str(best_ckpt) + ".moved")
    st = jout(expctl(proj, "status", "--no-gpu"))
    check(not any(t["run_id"] == rid_ok for t in st["top"]) and any("checkpoint missing" in a for a in st["alerts"]),
          "missing checkpoint makes run ineligible with alert")
    Path(str(best_ckpt) + ".moved").rename(best_ckpt)
    # a checkpoint recorded on another machine (the mirror of a remote run) or before the project folder moved is
    # found by the part of its path below the run's own folder; before, such a run left the list with that alert
    kept = (ok_dir / "result.json").read_text()
    res_there = json.loads(kept)
    res_there["best"]["ckpt"] = f"/elsewhere/project/runs/{ok_dir.name}/ckpt/best.pt"
    (ok_dir / "result.json").write_text(json.dumps(res_there))
    st = jout(expctl(proj, "status", "--no-gpu"))
    (ok_dir / "result.json").write_text(kept)
    check(st["top"] and st["top"][0]["run_id"] == rid_ok and os.path.samefile(st["top"][0]["ckpt"], best_ckpt)
          and not any("checkpoint missing" in a for a in st["alerts"]),
          f"a checkpoint recorded on another machine is found in this run folder ({st['top'][:1]}, {st['alerts']})")
    # a record that cannot be opened for a moment is looked at again: Windows refuses the open while the writer
    # replaces the file, and a single look made a live run read as stalled for that one status call
    code = ("import builtins, json, sys\nsys.path.insert(0, sys.argv[1])\nimport expctl\nn = {}\n"
            "def busy(p, *a, **k):\n"
            "    n[str(p)] = n.get(str(p), 0) + 1\n"
            "    if n[str(p)] <= int(sys.argv[3]):\n"
            "        raise PermissionError(13, 'busy')\n"
            "    return builtins.open(p, *a, **k)\n"
            "expctl.open = busy\nprint(json.dumps(expctl.read_json(sys.argv[2])))\n")
    looks = [sh([PY, "-c", code, str(proj / ".claude/skills/nn-training/scripts"), str(ok_dir / "result.json"), k], cwd=proj)
             for k in ("2", "3")]
    check('"state": "completed"' in looks[0].stdout and '"_error": "PermissionError' in looks[1].stdout,
          f"a record that is busy for a moment is read at the third look, one that stays busy is reported ({looks[0].stdout[:38].strip()} {looks[0].stderr[-200:]})")
    # a run that writes its result, or whose supervisor writes the exit record, while expctl looks at it read as lost
    # for that one look, which ended expctl watch with the wrong state. The records of the end are read after the looks
    # at the processes, and while the supervisor is still there the run has not ended
    code = ("import json, shutil, sys\nfrom pathlib import Path\nsys.path.insert(0, sys.argv[1])\nimport expctl\n"
            "d, out = Path(sys.argv[2]), []\n"
            "for record, sup, start in (('result.json', 0, 101), ('exit.json', 0, 101), ('', 1, 101), ('', 1, 300)):\n"
            "    d.mkdir()\n"
            "    (d / 'pid.json').write_text(json.dumps({'pid': 11, 'supervisor_pid': 12, 'started_at': 100}))\n"
            "    def alive(pid):\n"
            "        if record and pid == 11:\n"
            "            (d / record).write_text(json.dumps({'state': 'completed', 'returncode': 3}))\n"
            "        return pid == 12 and sup\n"
            "    expctl.pid_alive, expctl.proc_start_time = alive, lambda pid: start\n"
            "    out.append(expctl.load_run(d.parent, d, {}, 110)['state'])\n"
            "    shutil.rmtree(d)\n"
            "print(out)\n")
    ended = sh([PY, "-c", code, str(proj / ".claude/skills/nn-training/scripts"), str(tmp / "ending")], cwd=proj)
    check("['completed', 'failed', 'starting', 'lost']" in ended.stdout,
          "a run that ends while expctl looks at it reads as ended, one whose supervisor has yet to write the exit record "
          f"as not ended, and one whose supervisor's pid went to another process as lost ({ended.stdout.strip()} {ended.stderr[-200:]})")
    # that look needs a start time. Without psutil Windows gave none, so a pid that had gone to another process
    # counted as the run's own, and a run whose supervisor had yet to write the exit record read as lost
    code = ("import json, os, sys, time\nsys.modules['psutil'] = None\nsys.path.insert(0, sys.argv[1])\nimport expctl, runlog\n"
            "me = os.getpid()\na = expctl.proc_start_time(me)\n"
            "print(json.dumps([a, runlog._proc_start_time(me), expctl.proc_start_time(4294967292), "
            "expctl.same_process(me, a), expctl.same_process(me, (a or 0) - 60), time.time()]))\n")
    r = sh([PY, "-c", code, str(proj / ".claude/skills/nn-training/scripts")], cwd=proj)
    a, b, gone, same, other, now = json.loads(r.stdout) if r.returncode == 0 else [None] * 6
    check(a and b and abs(a - b) < 1 and gone is None and same and other is False and (os.name != "nt" or abs(now - a) < 60),
          f"a process's start time is known without psutil, to expctl and to the run logger alike, and tells a reused pid ({r.stdout.strip()} {r.stderr[-200:]})")
    # expctl's own writes leave no temporary file beside the record when they give up, whether the replace was refused
    # to the end or the write itself failed (a full disk)
    wdir = tmp / "wjson"
    wdir.mkdir()
    code = ("import json, os, sys\nsys.path.insert(0, sys.argv[1])\nimport expctl\nos.chdir(sys.argv[2])\n"
            "expctl.time.sleep = lambda s: None\nleft = []\n"
            "def refuse(a, b):\n    raise PermissionError(13, 'busy')\n"
            "def full(*a, **k):\n    raise OSError(28, 'No space left on device')\n"
            "for name, value in (('replace', refuse), ('dump', full)):\n"
            "    mod = os if name == 'replace' else json\n"
            "    real = getattr(mod, name)\n    setattr(mod, name, value)\n"
            "    try:\n        expctl.write_json_atomic('w.json', {'ok': 1})\n"
            "    except OSError as e:\n        left.append([type(e).__name__, os.listdir('.')])\n"
            "    setattr(mod, name, real)\n"
            "expctl.write_json_atomic('w.json', {'ok': 1})\nprint(json.dumps(left), os.listdir('.'))\n")
    gave_up = sh([PY, "-c", code, str(proj / ".claude/skills/nn-training/scripts"), str(wdir)], cwd=proj)
    check('[["PermissionError", []], ["OSError", []]] [\'w.json\']' in gave_up.stdout,
          f"an expctl write that gives up leaves no temporary file behind ({gave_up.stdout.strip()} {gave_up.stderr[-200:]})")
    # the status line reads the heartbeats itself and looks again too: with a single look a run whose heartbeat was
    # being replaced was missing from the line until the next refresh
    busy_run = ok_dir.parent / "zz-busy-heartbeat"
    busy_run.mkdir()
    (busy_run / "heartbeat.json").write_text(json.dumps({"ts": time.time()}), encoding="utf-8")
    code = ("import builtins, runpy, sys\nreal, n = builtins.open, {}\n"
            "def busy(p, *a, **k):\n"
            "    n[str(p)] = n.get(str(p), 0) + 1\n"
            "    if str(p).endswith('heartbeat.json') and n[str(p)] <= 2:\n"
            "        raise PermissionError(13, 'busy')\n"
            "    return real(p, *a, **k)\n"
            "builtins.open = busy\nrunpy.run_path(sys.argv[1], run_name='__main__')\n")
    sl = sh([PY, "-c", code, str(proj / ".claude/hooks/nn_statusline.py")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)},
            inp="{}")
    shutil.rmtree(busy_run)
    check("zz-busy-heartbeat" in sl.stdout,
          f"statusline shows a run whose heartbeat is busy for a moment ({sl.stdout.strip()} {sl.stderr[-200:]})")

    # 5. optuna stub path (real optuna not installable here)
    stub = tmp / "stub"
    (stub / "optuna").mkdir(parents=True)
    (stub / "optuna/__init__.py").write_text(OPTUNA_STUB)
    cfg = json.loads((proj / ".claude/nn-training.json").read_text())
    cfg["optuna"] = {"storage": "sqlite:///experiments/optuna.db", "studies": []}
    (proj / ".claude/nn-training.json").write_text(json.dumps(cfg))
    (proj / "experiments").mkdir(exist_ok=True)
    (proj / "experiments/optuna.db").write_text("")
    sto = jout(expctl(proj, "status", "--no-gpu", env={"PYTHONPATH": str(stub)}))
    s0 = sto["optuna"]["studies"][0]
    check(s0["counts"] == {"COMPLETE": 2, "FAIL": 1, "RUNNING": 1} and s0["best"]["trial"] == 1, f"optuna summary: {s0}")
    check(any("zombie" in a for a in sto["alerts"]), "zombie RUNNING trial alert when no live runs")
    no_opt = jout(expctl(proj, "status", "--no-gpu"))
    check("error" in no_opt["optuna"], "missing optuna reported, not crashing")

    # 6. guard hook
    # The two live runs must outlast every check down to the session hook (7); the cleanup at the end stops them.
    # At 3000 steps they ended a few seconds after those checks on an idle machine, and before them on a busy one.
    active = jout(expctl(proj, "launch", "--name", "guarded", "--", PY, "train.py", "--steps", "30000", "--sleep", "0.02"))
    live = jout(expctl(proj, "launch", "--name", "livetree", "--snapshot", "none", "--", PY, "train.py", "--steps", "30000", "--sleep", "0.02", "--seed", "2"))
    dup2 = expctl(proj, "launch", "--name", "guarded-again", "--", PY, "train.py", "--steps", "30000", "--sleep", "0.02")
    check(dup2.returncode == 4, "same command + same source hash refused as duplicate")
    wait_for(lambda: state_of(proj, active["run_id"])[0] == "running", 15)

    def guard(tool, ti, env=None):  # ripgrep's configuration file on the machine that runs the tests stays out
        r = sh([PY, str(proj / ".claude/hooks/nn_guard.py")], cwd=proj,
               env={"CLAUDE_PROJECT_DIR": str(proj), "RIPGREP_CONFIG_PATH": "", **(env or {})},
               inp=json.dumps({"tool_name": tool, "tool_input": ti, "cwd": str(proj), "session_id": "t"}))
        if not r.stdout.strip():
            return None, r.stderr
        o = json.loads(r.stdout)["hookSpecificOutput"]
        return o["permissionDecision"], o["permissionDecisionReason"]

    def utf16(text):  # the value PowerShell's -EncodedCommand takes
        return base64.b64encode(text.encode("utf-16-le")).decode()

    cases = [
        ("Read", {"file_path": str(proj / "data/test/labels.csv")}, "deny"),
        ("Read", {"file_path": "data/test/labels.csv"}, "deny"),
        ("Read", {"file_path": str(proj / "train.py")}, None),
        ("Grep", {"pattern": "y", "path": "data/test"}, "deny"),
        ("Glob", {"pattern": "data/test/*.csv"}, "deny"),
        ("Glob", {"pattern": "**/*.py"}, None),
        ("Edit", {"file_path": str(proj / "eval/metrics.py"), "old_string": "a", "new_string": "b"}, "ask"),
        ("Edit", {"file_path": str(proj / ".claude/settings.json"), "old_string": "a", "new_string": "b"}, "ask"),
        ("Write", {"file_path": str(proj / active["run_dir"] / "src/train.py"), "content": "x"}, "deny"),
        ("Write", {"file_path": str(proj / "train.py"), "content": "x"}, None),
        ("Bash", {"command": "cat data/test/labels.csv | head"}, "deny"),
        ("Bash", {"command": "ls data/test_small"}, None),
        # was "ask": the final evaluation now starts only through `expctl final-eval`, which keeps the receipt
        ("Bash", {"command": "NN_UNSEAL_TEST=1 python eval/final.py --ckpt runs/x/best.pt"}, "deny"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/expctl.py final-eval -- --ckpt runs/x/best.pt"}, "ask"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/expctl.py --root . final-eval --again \"first try crashed\""}, "ask"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/expctl.py final-eval -- --data data/test/labels.csv"}, "deny"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/expctl.py --help | grep final-eval"}, None),
        # new: the split audit counts records of a sealed split, so the user decides on each one
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/expctl.py audit-splits"}, "ask"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/expctl.py --root . audit-splits --key text"}, "ask"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/expctl.py --help | grep audit-splits"}, None),
        ("Bash", {"command": "rm .claude/state/final-eval/receipt.jsonl"}, "ask"),
        ("Bash", {"command": "Remove-Item .claude\\state\\final-eval\\receipt.jsonl"}, "ask"),
        ("Bash", {"command": "python -c \"open('.claude/state/final-eval/receipt.jsonl','w').close()\""}, "ask"),
        ("Edit", {"file_path": str(proj / ".claude/state/final-eval/receipt.jsonl"), "old_string": "a", "new_string": "b"}, "ask"),
        # the copy of the receipt's rows that every checkout shares
        ("Bash", {"command": "rm .git/nn-training-final-eval.jsonl"}, "ask"),
        ("Bash", {"command": "python -c \"open('.git/nn-training-final-eval.jsonl','w').close()\""}, "ask"),
        ("Bash", {"command": "cat .git/nn-training-final-eval.jsonl"}, None),
        ("Bash", {"command": "NN_UNSEAL_TEST=1 python other.py"}, "deny"),
        ("Bash", {"command": "kill 12345"}, "ask"),
        ("Bash", {"command": "pkill -f train.py"}, "ask"),
        ("Bash", {"command": "rm -rf runs/old"}, "ask"),
        ("Bash", {"command": "rm ckpt/best.pt"}, "ask"),
        ("Bash", {"command": "rm notes.txt"}, None),
        ("Bash", {"command": "git reset --hard HEAD~1"}, "ask"),
        ("Bash", {"command": "git stash list"}, None),
        ("Bash", {"command": "git checkout main"}, "ask"),
        ("Bash", {"command": "git status && git diff"}, None),
        ("Bash", {"command": "uv add optuna"}, "ask"),
        ("Bash", {"command": "sed -i 's/a/b/' eval/metrics.py"}, "ask"),
        ("Bash", {"command": "echo '{}' > .claude/nn-training.json"}, "ask"),
        ("Bash", {"command": "cat .claude/nn-training.json"}, None),
        ("Bash", {"command": "python3 .claude/skills/nn-training/scripts/expctl.py status --brief"}, None),
        ("Bash", {"command": "python3 .claude/skills/nn-training/scripts/expctl.py stop " + active["run_id"]}, "ask"),
        ("Bash", {"command": "cat skill.md"}, None),
        ("Bash", {"command": "find data -type f"}, "ask"),
        ("Bash", {"command": "grep -rn label data"}, "ask"),
        ("Bash", {"command": "cat data/*/labels.csv"}, "deny"),  # was "ask": the wildcard names the sealed file on disk
        ("Bash", {"command": "cat d*/test/labels.csv"}, "deny"),
        ("Bash", {"command": "cd data && cat test/labels.csv"}, "deny"),
        # were None: a cd behind a blank, a shell keyword, `builtin` or `--`, and PowerShell's Push-Location, went unseen
        ("Bash", {"command": " cd data && cat test/labels.csv"}, "deny"),
        ("Bash", {"command": "if true; then cd data; cat test/labels.csv; fi"}, "deny"),
        ("Bash", {"command": "builtin cd -- data && cat test/labels.csv"}, "deny"),
        ("Bash", {"command": "Push-Location data; Get-Content test\\labels.csv"}, "deny"),
        ("Bash", {"command": " cd eval && cat metrics.py"}, None),
        ("Bash", {"command": "cd data; grep -rn y ."}, "ask"),
        ("Bash", {"command": "cat data/*.csv"}, None),
        ("Bash", {"command": "grep -rn cat data/train"}, None),
        # was None: a recursive command over the project root is asked about when sealed files lie below it on disk
        ("Bash", {"command": "grep -rn 'def train' ."}, "ask"),
        ("Bash", {"command": "grep -rn 'def train'"}, "ask"),  # no folder named: it takes the one it runs in
        ("Bash", {"command": "grep -rn eval"}, "ask"),  # the text it looks for is not a folder it names
        ("Bash", {"command": "find . -name '*.csv'"}, "ask"),
        ("Bash", {"command": "ls -R; true"}, "ask"),
        ("Bash", {"command": "(ls -R)"}, "ask"),
        ("Bash", {"command": "tar czf backup.tgz ."}, "ask"),
        ("Bash", {"command": "sudo find . -type f"}, "ask"),
        ("Bash", {"command": "timeout 10 find . -type f"}, "ask"),
        ("Bash", {"command": "rg foo; find . -type f"}, "ask"),  # each command of a line by its own tool
        ("Bash", {"command": "find . -name '*.py' | head; grep -rn label . | head"}, "ask"),  # and its own filters
        ("Bash", {"command": "X='*.csv'; grep -rn --include=\"$X\" label ."}, "ask"),  # a filter it cannot read
        ("Bash", {"command": "cd eval && cd .. && grep -rn label ."}, "ask"),
        ("Bash", {"command": "(cd eval && ls -R); ls -R"}, "ask"),  # a subshell's cd ends with it
        ("Bash", {"command": "pushd eval; ls -R; popd; ls -R"}, "ask"),
        ("Bash", {"command": "test -d eval && cd eval; ls -R"}, "ask"),  # a cd that may not have run
        # it passes with a file filter that leaves the sealed files out, with the folders named, or in another folder
        ("Bash", {"command": "grep -rn --include='*.py' 'def train' ."}, None),
        ("Bash", {"command": "grep -rn --exclude-dir=data 'def train' ."}, None),  # was "ask": the name it leaves out
        ("Bash", {"command": "find . -name '*.py'"}, None),
        ("Bash", {"command": "grep -rn 'def train' eval sub"}, None),
        ("Bash", {"command": "tar czf backup.tgz eval sub"}, None),
        ("Bash", {"command": "cd eval && grep -rn def ."}, None),
        ("Bash", {"command": "make && cd eval && ls -R"}, None),
        ("Bash", {"command": "(cd eval; ls -R)"}, None),
        ("Bash", {"command": "ls -ltr"}, None),  # -r sorts in reverse: only -R recurses
        # the words find and tree in text that a line writes are not commands
        ("Bash", {"command": "cat > notes.md <<'EOF'\nwe find that the tree is deep\nEOF"}, None),
        ("Bash", {"command": "python - <<'EOF'\ntree = build()\nidx = text.find('loss')\nEOF"}, None),
        # were None, over the root and over data alike: PowerShell and cmd.exe write recursion their own way
        ("Bash", {"command": "Get-ChildItem -Recurse | Select-String label"}, "ask"),
        ("Bash", {"command": "gci -r data"}, "ask"),
        ("Bash", {"command": "$f = Get-ChildItem . -Recurse -Include *.py,*.csv"}, "ask"),
        ("Bash", {"command": "Get-ChildItem -Recurse -Exclude *.py"}, "ask"),  # not read as a filter
        ("Bash", {"command": "Get-ChildItem -Recurse *.py"}, "ask"),  # nor is a wildcard path
        ("Bash", {"command": "cmd /c dir /s/b"}, "ask"),
        ("Bash", {"command": "cmd /c findstr /s label *.csv"}, "ask"),
        ("Bash", {"command": "tree /f"}, "ask"),
        ("Bash", {"command": "Compress-Archive -Path . -DestinationPath b.zip"}, "ask"),
        ("Bash", {"command": "robocopy . ..\\backup /e"}, "ask"),
        ("Bash", {"command": "Get-ChildItem -Recurse -Filter *.py | Select-String 'def train'"}, None),
        ("Bash", {"command": "Get-ChildItem -Recurse -Include \"*.py\", \"*.md\""}, None),
        ("Bash", {"command": "Get-ChildItem -Path eval,sub -Recurse"}, None),
        ("Bash", {"command": "Set-Location eval; Get-ChildItem -Recurse"}, None),
        ("Bash", {"command": "cmd /c dir /s eval"}, None),
        ("Bash", {"command": "Get-ChildItem data"}, None),  # one level, like `ls data`
        ("Bash", {"command": "python train.py --output-dir runs/x -r 3"}, None),  # a flag that ends in -dir is no `dir`
        ("Bash", {"command": "rg 'def train'"}, None),  # ripgrep skips the git-ignored data folder
        # were None: told to pass over the ignore rules or to follow links, ripgrep reads what any other tool reads
        ("Bash", {"command": "rg -uu 'def train'"}, "ask"),
        ("Bash", {"command": "rg --no-ignore 'def train'"}, "ask"),
        ("Bash", {"command": "rg -L 'def train'"}, "ask"),
        ("Bash", {"command": "git grep --no-index 'def train'"}, "ask"),
        ("Bash", {"command": "rg -g '*' 'def train'"}, "ask"),  # a glob that matches the ignored folder lets it in
        ("Bash", {"command": "rg -g '*.csv' label"}, None),  # one for the files alone does not: the folder's rule holds
        ("Bash", {"command": "rg -uu -g '*.py' 'def train'"}, None),
        ("Bash", {"command": "rg -t py -i 'def train'"}, None),  # -t and -i are not -u
        # were None: a line that names the variable of ripgrep's configuration file may set options the guard cannot see
        ("Bash", {"command": "RIPGREP_CONFIG_PATH=conf rg 'def train'"}, "ask"),
        ("Bash", {"command": "RIPGREP_CONFIG_PATH=conf rg --no-config 'def train'"}, None),
        ("PowerShell", {"command": "$env:RIPGREP_CONFIG_PATH = 'conf'; rg 'def train'"}, "ask"),
        # were None: a name that a search leaves out counts only where the tool surely leaves it out. Not when the
        # line names it as a path as well, in another case than on disk, from another folder than the one ripgrep
        # starts its globs at, or when a later glob takes the files in again
        ("Bash", {"command": "grep -r --exclude=data/. label data/. sub"}, "ask"),
        ("Bash", {"command": "grep -rn --exclude-dir=Data 'def train' ."}, "ask"),
        ("Bash", {"command": "rg -uu -g '!Data/**' 'def train'"}, "ask"),
        ("Bash", {"command": "rg -uu -g '!*.csv' -g '*.csv' label"}, "ask"),
        ("Bash", {"command": "cd sub && rg -uu -g '!data/**' label .."}, "ask"),
        ("Grep", {"pattern": "y", "path": "data", "glob": "!test/**"}, "deny"),
        ("Grep", {"pattern": "y", "path": "data", "glob": "!Labels.csv"}, "deny"),
        ("Grep", {"pattern": "y", "path": "data", "glob": "!*.csv *.csv"}, "deny"),
        # were None: a glob told to include counts from whichever folder of the file's path it may start
        ("Grep", {"pattern": "y", "path": "data", "glob": "data/test/*.csv"}, "deny"),
        ("Glob", {"pattern": "test/*.csv"}, "deny"),
        ("Bash", {"command": "rg -uu -g '!data/**' 'def train'"}, None),
        ("Bash", {"command": "rg -uu -g '!data' 'def train'"}, None),  # was "ask": ripgrep leaves out a folder by its name
        ("Bash", {"command": "cd sub && rg -uu -g '!**/data/**' label .."}, None),
        ("Grep", {"pattern": "y", "path": "data", "glob": "!labels.csv"}, None),
        ("Grep", {"pattern": "y", "path": "data", "glob": "!test"}, None),  # was "deny"
        # were None: the target of a redirection and the value of an option are not paths that the command names, so
        # the folder it runs in is searched all the same
        ("Bash", {"command": "grep -rn label 2>/dev/null"}, "ask"),
        ("Bash", {"command": "grep -rn label >/dev/null 2>&1"}, "ask"),
        ("Bash", {"command": "tree -I sub"}, "ask"),
        ("Bash", {"command": "grep -rn -A 3 eval"}, "ask"),
        ("Bash", {"command": "gci -r -Exclude sub"}, "ask"),
        ("Bash", {"command": "find -newer train.py -type f"}, "ask"),
        ("Bash", {"command": "grep -rn label --exclude-from=.gitignore"}, "ask"),
        ("Bash", {"command": "grep -rn = ."}, "ask"),
        ("Bash", {"command": "grep.exe -rn label"}, "ask"),
        ("Bash", {"command": "grep -rn label eval 2>/dev/null"}, None),
        ("Bash", {"command": "grep -rn --color label sub"}, None),
        # were None: each tool's file filters are read its own way. grep's in grep's order, find's with its operators,
        # ripgrep's types all together, and another tool's options (tar -g, rsync --include) are no file filters
        ("Bash", {"command": "grep -rn --exclude='*.csv' --include='*.csv' label ."}, "ask"),
        ("Bash", {"command": "tar -czf o.tgz -g snap ."}, "ask"),
        ("Bash", {"command": "rsync -a --include='*.py' . /tmp/copy"}, "ask"),
        ("Bash", {"command": "find . -not -name '*.py'"}, "ask"),
        ("Bash", {"command": "find . -name '*.py' -o -print"}, "ask"),
        ("Bash", {"command": "find . -type d -name test -exec ls {} +"}, "ask"),  # ls gets the folder with all it holds
        ("Bash", {"command": "grep -rnesecret . sub"}, "ask"),  # -e gives the text: both arguments are folders
        ("Bash", {"command": "rg -uu -t csv eval"}, "ask"),
        ("Bash", {"command": "rg -uu -t py -t csv eval"}, "ask"),
        ("Bash", {"command": "rg -uu --type-add 'py:*.csv' -t py eval"}, "ask"),
        ("Grep", {"pattern": "y", "path": "data", "type": "all"}, "deny"),
        ("Bash", {"command": "grep -rn --exclude='*.csv' --include='*.py' label ."}, None),
        ("Bash", {"command": "find . -name '*.py' -o -name '*.md'"}, None),
        ("Bash", {"command": "find . -name '*.py' -exec grep -n train {} +"}, None),
        ("Bash", {"command": "grep -rne secret sub"}, None),
        ("Bash", {"command": "rg -uu -t py eval"}, None),
        ("Bash", {"command": "rg -uu -ig '*.py' label"}, None),  # was "ask": -g in a group of letters is a filter too
        ("Grep", {"pattern": "y", "path": "data", "type": "py"}, None),
        # were None: [...] in a file filter stands for one character, as the tools read it
        ("Bash", {"command": "find . -name '*.[c]sv' -exec cat {} +"}, "ask"),
        ("Bash", {"command": "grep -r --include='*.[c]sv' label ."}, "ask"),
        ("Bash", {"command": "gci -r -Include *.[c]sv"}, "ask"),
        ("Bash", {"command": "grep -rn --include='*.[!p]*' label ."}, "ask"),  # told to include, [!p] is read wide
        ("Bash", {"command": "rg -uu -g '*.[c]sv' label"}, "ask"),
        ("Grep", {"pattern": "y", "path": "data", "glob": "*.[c]sv"}, "deny"),
        ("Glob", {"pattern": "data/*/*.[c]sv"}, "deny"),
        ("Bash", {"command": "grep -rn --exclude='*.[x]sv' label ."}, "ask"),
        ("Bash", {"command": "grep -rn --exclude='*.[d-a]sv' label ."}, "ask"),  # one that cannot be read leaves out nothing
        ("Bash", {"command": "grep -rn --exclude='*.[c]sv' label ."}, None),  # was "ask"
        ("Bash", {"command": "find . -name '*.[ch]'"}, None),
        ("Glob", {"pattern": "**/*.[ch]"}, None),
        # were None: input that made the guard fail inside, which let a read pass (the second one on Linux and macOS)
        ("Grep", {"pattern": "y", "path": "data", "glob": "{a}" * 1100 + " *.csv"}, "deny"),
        ("Grep", {"pattern": "y", "glob": "~nosuchuser/x *"}, "deny"),
        # was None: more {a,b} in one glob than the guard writes out counts as matching every file
        ("Grep", {"pattern": "y", "path": "data", "glob": "*.{" + ",".join(map(str, range(70))) + "}"}, "deny"),
        # were ask: Claude Code's Bash tool runs a POSIX shell, where -r and -s make ls and dir walk no tree
        ("Bash", {"command": "ls -r"}, None),
        ("Bash", {"command": "dir -s"}, None),
        ("Bash", {"command": "bash -c \"ls -r\""}, None),
        ("Bash", {"command": "dir -R"}, "ask"),  # GNU dir's -R does
        ("Bash", {"command": "powershell -c \"ls -r\""}, "ask"),  # handed to PowerShell it is Get-ChildItem -Recurse
        ("Bash", {"command": "powershell -c \"ls -r\"; cat data/test/labels.csv"}, "deny"),
        ("PowerShell", {"command": "ls -r"}, "ask"),  # as it is in the PowerShell tool
        ("PowerShell", {"command": "Get-ChildItem -Depth 0"}, None),  # was ask: depth 0 is the folder itself
        ("PowerShell", {"command": "Get-ChildItem -Depth 2"}, "ask"),
        ("PowerShell", {"command": "Get-ChildItem -Depth:2"}, "ask"),  # was None: PowerShell's other way to give a value
        # was ask: more than eight folders that a command names were judged by the one folder that holds them all
        ("Bash", {"command": "grep -rn x sub eval tools .claude .claude/hooks .claude/skills .claude/agents "
                             ".claude/skills/nn-training .claude/skills/nn-training/scripts"}, None),
        ("Bash", {"command": "grep -rn x sub eval tools .claude .claude/hooks .claude/skills .claude/agents "
                             ".claude/skills/nn-training data"}, "ask"),
        # were None: a change of folder that the guard did not follow
        ("Bash", {"command": "cd data</dev/null; cat test/labels.csv"}, "deny"),  # the folder ends at a redirection
        ("Bash", {"command": "cd 'da'ta; cat test/labels.csv"}, "deny"),  # and a shell splices it from quoted pieces
        ("Bash", {"command": "pushd d\"at\"a>/dev/null; cat test/labels.csv"}, "deny"),
        ("Bash", {"command": "env -C data cat test/labels.csv"}, "deny"),  # env -C runs its command in the folder
        ("Bash", {"command": "env FOO=1 --chdir=data cat test/labels.csv"}, "deny"),
        ("Bash", {"command": "env -C . ls -R"}, "ask"),
        ("Bash", {"command": "env -C eval ls -R"}, None),
        ("Bash", {"command": "env FOO=1 make -C sub"}, None),  # make's own option
        ("Bash", {"command": "git -C eval grep x"}, None),
        # a redirection to a file that cannot be opened keeps cd from running; one to /dev/null does not
        ("Bash", {"command": "cd sub 2>/nonexistent/zz; grep -rn x ."}, "ask"),
        ("Bash", {"command": "cd eval 2>/dev/null || exit 1; ls -R"}, None),
        ("Bash", {"command": "cd eval>/dev/null && ls -R"}, None),  # was ask: the folder was read as eval>
        # were None: a command the guard did not know when it saw it
        ("Bash", {"command": "\"grep\" -r secret ."}, "ask"),  # the command word in quotes
        ("Bash", {"command": "true && sudo 'find' . -type f"}, "ask"),
        ("Bash", {"command": "\"git\" push"}, "ask"),
        ("Bash", {"command": "echo \"find\" . -type f"}, None),  # as before: no command starts there
        ("Bash", {"command": "grep -rn \"find\" sub"}, None),
        ("Bash", {"command": "rgrep secret ."}, "ask"),  # rgrep is grep -r
        ("Bash", {"command": "rgrep --include='*.py' secret ."}, None),
        ("Bash", {"command": "rgrep -n secret sub eval"}, None),
        ("Bash", {"command": "cat **/*.csv"}, "ask"),  # a shell that reads ** so walks the tree by itself
        ("Bash", {"command": "head **/labels.csv"}, "ask"),
        ("Bash", {"command": "cat **/*.py"}, None),  # what follows the ** filters
        ("Bash", {"command": "cd sub && cat **/*.py"}, None),
        ("Bash", {"command": "cat > .gitignore <<EOF\n**/__pycache__/\nEOF"}, None),
        ("Bash", {"command": "python - <<EOF\ny = x ** 2\nEOF"}, None),  # a power, not a path
        ("PowerShell", {"command": "[IO.Directory]::GetFiles('.', '*', 'AllDirectories') | % { gc $_ }"}, "ask"),
        ("PowerShell", {"command": "cd sub; [IO.Directory]::GetFiles('.', '*', 'AllDirectories')"}, "ask"),
        ("PowerShell", {"command": "[IO.Directory]::EnumerateFiles('sub', '*', 'AllDirectories')"}, None),
        ("PowerShell", {"command": "cd sub; [IO.Directory]::GetFiles('.', '*.py')"}, None),
        # were None: a move takes the sealed files along, to a name under which nothing seals them
        ("Bash", {"command": "mv data d2; cat d2/test/labels.csv"}, "ask"),
        ("Bash", {"command": "mv -t /tmp/x data"}, "ask"),
        ("Bash", {"command": "mv * /tmp/x"}, "ask"),
        ("Bash", {"command": "git mv data d2"}, "ask"),
        ("Bash", {"command": "cmd /c ren data d2"}, "ask"),
        ("PowerShell", {"command": "Move-Item -Path data -Destination d2"}, "ask"),
        ("PowerShell", {"command": "mi sub,data d2; gc d2/test/labels.csv"}, "ask"),
        ("Bash", {"command": "mv results.csv data/"}, None),  # into that folder: nothing sealed moves
        ("Bash", {"command": "mv data/train.csv data/train2.csv"}, None),
        ("Bash", {"command": "mv sub sub2"}, None),
        ("PowerShell", {"command": "Move-Item -Destination d2 -Path sub"}, None),
        # were None, found by the second review: mv -T is not mv -t, cp -a copies a tree, find's \; ends its command
        # and not the line, zsh's ***/ walks the tree, and a quoted command word stands behind then, timeout or xargs
        ("Bash", {"command": "mv -T data d2"}, "ask"),
        ("Bash", {"command": "mv -vt backup data"}, "ask"),
        ("Bash", {"command": "mv -t sub big.bin"}, None),
        ("Bash", {"command": "cp -a data d2; cat d2/test/labels.csv"}, "ask"),
        ("Bash", {"command": "cp --archive sub d2"}, None),
        ("Bash", {"command": "grep -a secret sub/hello.py"}, None),  # grep's -a is another option
        ("Bash", {"command": "find . -name '*.py' -exec true {} \\; -o -exec cat {} \\;"}, "ask"),
        ("Bash", {"command": "find . -name '*.py' -exec true {} ';' -o -print"}, "ask"),
        ("Bash", {"command": "find . -name '*.py' -exec grep -n def {} \\;"}, None),
        ("Bash", {"command": "find sub -type f -exec cat {} \\;"}, None),  # was ask: the \ was read as the folder /
        ("Bash", {"command": "cat ***/*.csv"}, "ask"),
        ("Bash", {"command": "cat sub/***/*.py"}, None),
        ("Bash", {"command": "if true; then \"grep\" -r secret data; fi"}, "ask"),
        ("Bash", {"command": "timeout 5 \"grep\" -r secret data"}, "ask"),
        ("Bash", {"command": "echo x | xargs \"grep\" -r secret data"}, "ask"),
        ("Bash", {"command": "$'grep' -r secret data"}, "ask"),
        ("Bash", {"command": "chmod -R a+r ."}, "ask"),  # these two had no test
        ("Bash", {"command": "chown -R me data"}, "ask"),
        ("Bash", {"command": "chmod -r sub/hello.py"}, None),  # takes a permission away
        # were None: a folder that the line names where the guard reads no change of folder. A path that leads nowhere
        # from where the line runs, and to a sealed file below that folder, is read from there
        ("Bash", {"command": "X=1 cd data; cat test/labels.csv"}, "deny"),
        ("Bash", {"command": "eval cd data; cat test/labels.csv"}, "deny"),
        ("Bash", {"command": "sudo -D data cat test/labels.csv"}, "deny"),
        ("Bash", {"command": "env -iC data cat test/labels.csv"}, "deny"),
        ("Bash", {"command": "env -u HOME -C data cat test/*.csv"}, "deny"),
        ("PowerShell", {"command": "Set-Location -Path:data; gc test/labels.csv"}, "deny"),
        ("Bash", {"command": "start /D data /B cmd /c type test\\labels.csv"}, "deny"),
        ("Bash", {"command": "python train.py --data-dir data --eval-file test/labels.csv"}, "deny"),
        ("Bash", {"command": "python train.py --data data --split test"}, None),  # a word, not a path
        ("Bash", {"command": "X=1 cd data; cat train.csv"}, None),
        ("Bash", {"command": "cp -r sub backup && python -m pytest test/unit"}, None),  # names nothing on disk
        ("Glob", {"pattern": "**/*.csv"}, "deny"),
        ("Glob", {"pattern": "data/**/*.csv"}, "deny"),
        ("Grep", {"pattern": "y"}, None),  # the Grep tool skips what git ignores, like ripgrep
        ("Grep", {"pattern": "y", "path": "data"}, "deny"),  # but it searches an ignored folder it is given by name
        # were None: the Grep tool's glob is several, split at blanks and commas, and each is read like rg's -g
        ("Grep", {"pattern": "y", "glob": "*"}, "deny"),
        ("Grep", {"pattern": "y", "glob": "data,*.csv"}, "deny"),
        ("Grep", {"pattern": "y", "glob": "*.py data/test/labels.csv"}, "deny"),
        ("Grep", {"pattern": "y", "glob": "*.py,*.md"}, None),
        ("Bash", {"command": "find . -iname '*.CSV'"}, "ask"),  # -iname matches without regard to case on every platform
        ("Bash", {"command": "find . -iname '*.PY'"}, None),
        ("Bash", {"command": "Set-Content -Path eval/metrics.py -Value x"}, "ask"),
        ("Bash", {"command": "'x' | Out-File eval/metrics.py"}, "ask"),
        ("Bash", {"command": "Copy-Item train.py eval/metrics.py"}, "ask"),
        ("Bash", {"command": "python -c \"open('eval/metrics.py','w').write('x')\""}, "ask"),
        ("Bash", {"command": "bash -c \"echo x > eval/metrics.py\""}, "ask"),
        ("Bash", {"command": "python -c \"print(open('train.py').read())\""}, None),
        ("Bash", {"command": f"Set-Content {active['run_dir']}/notes.txt x"}, "ask"),
        ("Bash", {"command": "Remove-Item -Recurse runs/old"}, "ask"),
        ("Bash", {"command": "ri -r runs/old"}, "ask"),
        ("Bash", {"command": "cmd /c rd /s /q runs\\old"}, "ask"),
        ("Bash", {"command": "cmd /c del ckpt\\best.pt"}, "ask"),
        ("Bash", {"command": "python -c \"import shutil;shutil.rmtree('runs/old')\""}, "ask"),
        ("Bash", {"command": "Remove-Item .claude\\state\\remote-ledger.jsonl"}, "ask"),
        ("Bash", {"command": "spps -Id 12345"}, "ask"),
        ("Bash", {"command": "Stop-Process -Id 12345"}, "ask"),
        ("Bash", {"command": "wmic process where processid=12345 call terminate"}, "ask"),
        ("Bash", {"command": "python -c \"import os;os.kill(12345,9)\""}, "ask"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/nnremote.py --root=. launch --name x -- python train.py"}, "ask"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/nnloop.py --root=. start --max-runs 3"}, "ask"),
        ("Bash", {"command": "python .claude/skills/nn-training/scripts/nnloop.py status"}, None),
        ("Bash", {"command": "ls data"}, None),
        ("Monitor", {"command": "tail -f data/test/labels.csv", "description": "x"}, "deny"),
        # were None: shell code attached to its flag, or encoded for PowerShell, went unread
        ("Bash", {"command": "bash -c\"echo x > eval/metrics.py\""}, "ask"),
        ("Bash", {"command": "bash -lc\"cat data/te*/labels.csv\""}, "deny"),
        ("Bash", {"command": "cmd /c\"type data\\te*\\labels.csv\""}, "deny"),
        ("Bash", {"command": "powershell -EncodedCommand " + utf16("Get-Content data/te*/labels.csv")}, "deny"),
        ("PowerShell", {"command": "pwsh -enc " + utf16("Set-Content eval/metrics.py x")}, "ask"),
        ("Bash", {"command": "powershell -ExecutionPolicy Bypass -File tools/x.ps1"}, None),  # no encoded command
        ("Bash", {"command": "grep -color=auto \"def train\" train.py"}, None),  # an option that only starts like -c
        ("Bash", {"command": "echo Y2F0IGRhdGEvdGUqL2xhYmVscy5jc3Y= | base64 -d | sh"}, "ask"),
        ("Bash", {"command": "base64 -d weights.b64 > weights.bin"}, None),
        # were None: a sealed path that a line of code joins from parts
        ("Bash", {"command": "python -c \"from pathlib import Path; print((Path('data') / 'test' / 'labels.csv').read_text())\""}, "deny"),
        ("Bash", {"command": "python -c \"import os; print(open(os.path.join('data', 'test', 'labels.csv')).read())\""}, "deny"),
        ("Bash", {"command": "python -c \"print(open('data/te' + 'st/labels.csv').read())\""}, "deny"),
        ("Bash", {"command": "python -c \"import os; print(open(os.path.join('data', 'train.csv')).read())\""}, None),
        ("Bash", {"command": "python -c \"for split in ('data', 'test'): print(split)\""}, None),  # a list is no path
        ("Bash", {"command": "bash -c 'python -c \"import os; print(open(os.path.join(\\\"data\\\", \\\"test\\\", \\\"labels.csv\\\")).read())\"'"}, "deny"),
        ("Bash", {"command": "git commit -m 'eval: join(\"data\", \"test\") is sealed'"}, None),  # a message, not code
        # were None: text that a call writes into a file, or hands to an MCP tool, and that names sealed data
        ("Write", {"file_path": str(proj / "train.py"), "content": "import csv\nrows = list(csv.reader(open('data/test/labels.csv')))\n"}, "ask"),
        ("Edit", {"file_path": "train.py", "old_string": "a", "new_string": "p = os.path.join('data', 'test', 'labels.csv')"}, "ask"),
        ("Edit", {"file_path": "sub/hello.py", "old_string": "a", "new_string": "open('../data/te' + 'st/labels.csv')"}, "ask"),
        ("MultiEdit", {"file_path": "train.py", "edits": [{"old_string": "a", "new_string": "b"},
                                                          {"old_string": "c", "new_string": "os.environ['NN_UNSEAL_TEST'] = '1'"}]}, "ask"),
        ("NotebookEdit", {"notebook_path": "nb.ipynb", "new_source": "pd.read_csv('data/test/labels.csv')"}, "ask"),
        ("Write", {"file_path": "conf/train.yaml", "content": "eval_file: data\\\\test\\\\labels.csv\n"}, "ask"),
        ("Edit", {"file_path": "train.py", "old_string": "open('data/test/labels.csv')", "new_string": "open('data/train.csv')"}, None),
        ("Write", {"file_path": "notes.md", "content": "The test split is data/test/labels.csv; nothing reads it.\n"}, None),
        ("Write", {"file_path": "train.py", "content": "splits = ['train', 'test']\nacc = correct / total\n"}, None),
        ("mcp__db__query", {"query": "SELECT *\nFROM read_csv('data/test/labels.csv')"}, "ask"),
        ("mcp__db__query", {"query": "SELECT * FROM read_csv('data/train.csv')"}, None),
        # the agent's own tools are not read so: a task for a subagent may name the sealed folder
        ("Task", {"description": "review", "prompt": "Check that nothing reads data/test/labels.csv.\nReport."}, None),
        # were None: a shell write to git's hooks or configuration (the edit tools asked already)
        ("Bash", {"command": "echo 'cat data/train.csv' > .git/hooks/pre-commit"}, "ask"),
        ("Bash", {"command": "cp tools/runlog.py .git/config"}, "ask"),
        ("Bash", {"command": "cat .git/config > gitconfig.txt"}, "ask"),  # the rule cannot tell a source from a target
        ("Bash", {"command": "cat .git/config"}, None),
    ]
    for tool, ti, want in cases:
        got, why = guard(tool, ti)
        check(got == want, f"guard {tool} {json.dumps(ti)[:70]} -> {got} (want {want})")
    why = [guard("Bash", {"command": c})[1] for c in ("grep -rn label .", "grep -rn label data")]
    check("--include" in why[0] and "--include" not in why[1],
          "guard offers a file filter as a way out where the files on disk decided, not where the folder's name did")
    (proj / "data/test").rename(proj / "data/unsealed")
    check(guard("Bash", {"command": "grep -rn label ."})[0] is None,
          "guard: a recursive search of the project root passes while no sealed file lies below it")
    (proj / "data/unsealed").rename(proj / "data/test")
    # a path that names a file where the line runs is that file, whatever lies below a folder the line names as well
    got = [guard("Bash", {"command": "ls data; cat test/labels.csv"})[0]]
    (proj / "test").mkdir()
    (proj / "test/labels.csv").write_text("x\n")
    got.append(guard("Bash", {"command": "ls data; cat test/labels.csv"})[0])
    shutil.rmtree(proj / "test")
    check(got == ["deny", None], f"guard reads a path below a folder the line names only where it leads nowhere else ({got})")
    # a rule for the csv files instead of one for their folder: a glob told to include them overrides it
    ignore = (proj / ".gitignore").read_text()
    (proj / ".gitignore").write_text(ignore.replace("data/\n", "*.csv\n"))
    got = [guard(t, ti)[0] for t, ti in (
        ("Grep", {"pattern": "y"}), ("Grep", {"pattern": "y", "glob": "*.py,*.md"}),
        ("Grep", {"pattern": "y", "glob": "*.csv"}), ("Grep", {"pattern": "y", "glob": "*.py,*.csv"}),
        ("Bash", {"command": "rg -g '*.csv' label"}))]
    check(got == [None, None, "deny", "deny", "ask"],
          f"guard: a search told to include files that git ignores by a rule for the files reads the sealed ones ({got})")
    (proj / ".gitignore").write_text(ignore.replace("data/\n", "*.npz\n"))
    (proj / "data/test/a.npz").write_text("x\n")
    got = [guard("Grep", {"pattern": "y"})[0], guard("Bash", {"command": "rg label"})[0]]
    check(got == ["deny", "ask"],
          f"guard: an ignored file in the sealed folder says nothing about the file beside it that git does not ignore ({got})")
    (proj / "data/test/a.npz").unlink()
    (proj / ".gitignore").write_text(ignore)

    # ripgrep's own rules outrank git's: a .ignore or .rgignore file, beside the ignored folder or in a folder above
    # it, that takes the rule back, and an option in the configuration file that RIPGREP_CONFIG_PATH names
    def both(env=None):
        return [guard("Grep", {"pattern": "y"}, env)[0], guard("Bash", {"command": "rg label"}, env)[0]]
    for f, text, want in ((proj / ".ignore", "!data/\n", "deny"), (tmp / ".rgignore", "*.log\n!/proj/data\n", "deny"),
                          (proj / ".ignore", "*.log\n!build/\n", None), (proj / "sub/.ignore", "!data/\n", None)):
        f.write_text(text)
        got = both()
        f.unlink()
        check(got == [want, want and "ask"], f"guard: {f.relative_to(tmp).as_posix()} with the line {text.split()[-1]} "
              f"{'lets ripgrep into' if want else 'does not open'} the folder that git ignores ({got})")
    conf = tmp / "rgconf"
    for text, want in (("--no-ignore\n", "deny"), ("--glob\n*.csv\n", "deny"),
                       ("# --no-ignore\n--smart-case\n--glob=!*.lock\n", None)):
        conf.write_text(text)
        got = both({"RIPGREP_CONFIG_PATH": str(conf)})
        check(got == [want, want and "ask"], f"guard: ripgrep's configuration file with {text.split()[-1]} "
              f"{'makes it read' if want else 'does not make it read'} what git ignores ({got})")
    conf.write_text("--no-ignore\n")
    got = [guard("Bash", {"command": "rg --no-config label"}, {"RIPGREP_CONFIG_PATH": str(conf)})[0],
           *both({"RIPGREP_CONFIG_PATH": str(tmp / "nosuch")}),
           guard("Bash", {"command": "rg label"}, {"RIPGREP_CONFIG_PATH": "rgconf"})[0]]
    check(got == [None, None, None, "ask"], "guard: --no-config and a configuration file that is not there change "
          f"nothing, and one named by a relative path counts ({got})")
    r = sh([PY, str(proj / ".claude/hooks/nn_guard.py")], cwd=proj, inp="not json")
    check(r.returncode == 2 and "cannot be read" in r.stderr, "guard refuses malformed input (exit code 2)")
    # Input that makes Python give up (brackets nested deeper than it follows) was a crash with exit code 1, which an
    # agent program takes for a hook that failed: the call went on. 100,000 deep stops the JSON reader of every
    # Python version, 1,500 deep stops the reader of some and the guard's own walk through the values on the others
    got = []
    for depth in (100_000, 1_500):
        r = sh([PY, str(proj / ".claude/hooks/nn_guard.py")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)},
               inp='{"tool_name":"mcp__fs__read_file","tool_input":{"path":"data/test/labels.csv","x":%s},"cwd":%s,'
                   '"session_id":"t"}' % ("[" * depth + "]" * depth, json.dumps(str(proj))))
        got.append((r.returncode, "cannot be read" in r.stderr))
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import nn_guard\n"
            "def broken(*a):\n    raise RuntimeError('made by the test')\n"
            "nn_guard.main = broken\n"
            "sys.exit(nn_guard.run())")
    r = sh([PY, "-c", code, str(proj / ".claude/hooks")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)}, inp="{}")
    check(got == [(2, True), (2, True)] and r.returncode == 2 and "internal error" in r.stderr and not r.stdout.strip(),
          "guard: input nested too deeply to read is refused like other unreadable input, and an error that nothing "
          f"inside the guard caught is a refusal (exit code 2), not a crash ({got}, {r.returncode})")
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import nn_guard\n"
            "def broken(*a):\n    raise RuntimeError('made by the test')\n"
            "nn_guard.check_path_tool = broken\n"
            "sys.exit(nn_guard.main([]))")
    r = sh([PY, "-c", code, str(proj / ".claude/hooks")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)}, inp=json.dumps(
        {"tool_name": "Read", "tool_input": {"file_path": "train.py"}, "cwd": str(proj), "session_id": "t"}))
    check('"ask"' in r.stdout and "internal error" in r.stdout,  # was: the read passed, with a line on stderr
          f"guard: an error inside the guard asks about a read too, instead of letting it pass ({r.stdout[:80]!r})")
    # A folder sealed as a whole is walked to its end while the time allows. Here the walk's first bound is three
    # files, and the one file that the search's filter lets through lies behind seven others
    for i in range(6):
        (proj / f"data/test/a{i}.csv").write_text("x\n")
    (proj / "data/test/zz").mkdir()
    (proj / "data/test/zz/deep.txt").write_text("x\n")
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import nn_guard\n"
            "nn_guard.WALK, nn_guard.WALK_S = 3, float(sys.argv[2])\n"
            "sys.exit(nn_guard.main([]))")

    def bounded(command, secs):
        r = sh([PY, "-c", code, str(proj / ".claude/hooks"), str(secs)], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)},
               inp=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(proj), "session_id": "t"}))
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else None

    got = [bounded("grep -rn --include='*.txt' x .", 5), bounded("grep -rn --include='*.py' x .", 5),
           bounded("grep -rn --include='*.py' x .", 0)]
    check(got == ["ask", None, "ask"],  # was: [None, None, None], the walk ended at its bound without a word
          f"guard: a filtered search is asked about when a sealed file beyond the walk's first bound passes its "
          f"filter, passes when none does, and is asked about when the time ends before the sealed folder does ({got})")
    shutil.rmtree(proj / "data/test/zz")
    for i in range(6):
        (proj / f"data/test/a{i}.csv").unlink()
    log = (proj / ".claude/state/guard.log").read_text().splitlines()
    check(len(log) >= 10 and json.loads(log[-1])["decision"] in ("ask", "deny"), "guard writes audit log")
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import nn_guard\n"
            "for i in range(100): nn_guard.append_line(sys.argv[2], {'w': sys.argv[3], 'i': i, 'pad': 'x' * (i * 7 % 40)})")
    ps = [subprocess.Popen([PY, "-c", code, str(proj / ".claude/hooks"), str(tmp / "same-moment.jsonl"), str(w)])
          for w in range(8)]
    ends, whole = [p.wait() for p in ps], set()
    for line in (tmp / "same-moment.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            whole.add((json.loads(line)["w"], json.loads(line)["i"]))
        except (ValueError, KeyError, TypeError):
            pass
    check(ends == [0] * 8 and len(whole) == 800,
          f"guard log lines that eight processes write at the same moment all survive ({len(whole)} of 800)")
    wp = tmp / "walks"  # three sealed patterns that all look in the whole project: one walk, not three
    (wp / "b/cache").mkdir(parents=True)
    (wp / ".claude").mkdir()
    (wp / ".claude/nn-training.json").write_text(json.dumps(
        {"sealed_paths": ["**/held/**", "**/*held-out*", "**/cache/*.npz"]}))
    for name in ("held-out.txt", "b/cache/y.npz", "b/plain.py"):
        (wp / name).write_text("x\n")
    (wp / ".gitignore").write_text("held-out.txt\n")
    subprocess.run(["git", "init", "-q"], cwd=wp, check=True)
    code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import nn_guard\n"
            "seen, walk = [], nn_guard.walk\n"
            "nn_guard.walk = lambda top: seen.append(top) or walk(top)\n"
            "ctx = nn_guard.Ctx({'tool_name': 'Grep', 'tool_input': {}, 'cwd': sys.argv[2]})\n"
            "print(json.dumps([nn_guard.reaches_sealed(ctx, sys.argv[2], (), None, rg) for rg in (True, False)]"
            " + [len(seen)]))")
    got = jout(sh([PY, "-c", code, str(proj / ".claude/hooks"), str(wp)], cwd=wp, env={"CLAUDE_PROJECT_DIR": str(wp)}))
    check(got == ["**/cache/*.npz", "**/*held-out*", 2],
          f"guard: a search of the whole project walks it once for all its sealed patterns, and a sealed file that "
          f"ripgrep skips does not hide another pattern's file ({got})")
    for i in range(9):  # with b, ten folders for one wildcard: more than the guard walks one by one
        (wp / f"a{i}").mkdir()
    r = sh([PY, str(proj / ".claude/hooks/nn_guard.py")], cwd=wp, env={"CLAUDE_PROJECT_DIR": str(wp)}, inp=json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "grep -rn x [ab]*"}, "cwd": str(wp), "session_id": "t"}))
    check('"ask"' in r.stdout, f"guard: a wildcard over more folders than it walks one by one is checked at the "
                               f"folder that holds them all ({r.stdout[:80]!r})")
    code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import nn_guard\n"
            "seen, walk, c = [], nn_guard.walk, '; '.join([\"grep -rn --include='*.py' x .\"] * 30)\n"
            "nn_guard.walk = lambda top: seen.append(top) or walk(top)\n"
            "ctx = nn_guard.Ctx({'tool_name': 'Bash', 'tool_input': {'command': c}, 'cwd': sys.argv[2]})\n"
            "print(json.dumps([nn_guard.check_bash(ctx, c), len(seen)]))")
    got = jout(sh([PY, "-c", code, str(proj / ".claude/hooks"), str(wp)], cwd=wp, env={"CLAUDE_PROJECT_DIR": str(wp)}))
    check(got == [[], 1], f"guard: a search that a line repeats thirty times is looked up on disk once ({got})")
    code = ("import sys, time; sys.path.insert(0, sys.argv[1]); import nn_guard\n"
            "nn_guard.LIMIT = 0.5\n"
            "nn_guard.check_path_tool = lambda *a: time.sleep(40)\n"
            "sys.exit(nn_guard.main([]))")
    t0 = time.time()
    r = sh([PY, "-c", code, str(proj / ".claude/hooks")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)}, inp=json.dumps(
        {"tool_name": "Read", "tool_input": {"file_path": "train.py"}, "cwd": str(proj), "session_id": "t"}))
    check('"ask"' in r.stdout and "could not finish" in r.stdout and time.time() - t0 < 30,  # was: no answer at all
          f"guard: a check that takes longer than the guard allows itself ends as a question, instead of running "
          f"into the hook's time limit ({r.stdout[:80]!r} after {time.time() - t0:.0f} s)")

    # 7. session hook
    r = sh([PY, str(proj / ".claude/hooks/nn_session_status.py")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)},
           inp=json.dumps({"source": "compact", "session_id": "t"}))
    o = json.loads(r.stdout)["hookSpecificOutput"]
    check(o["hookEventName"] == "SessionStart" and "compacted" in o["additionalContext"] and "RUNNING" in o["additionalContext"],
          "session hook injects status after compaction")
    check(len(o["additionalContext"]) <= 2500, f"session context bounded ({len(o['additionalContext'])} chars)")
    print("\n--- sample session context ---\n" + o["additionalContext"])

    # 8. the skill's references: dated, refreshable, and listed in SKILL.md
    import re
    refs = sorted((KIT / ".claude/skills/nn-training/references").glob("*.md"))
    heads = {p.name: "\n".join(p.read_text(encoding="utf-8").splitlines()[:8]) for p in refs}
    bad = [n for n, h in heads.items()
           if not (re.search(r"^Checked: \d{4}-\d{2}-\d{2}\b", h, re.M) and re.search(r"^Refresh: \S", h, re.M))]
    check(len(refs) >= 10 and not bad, f"every reference starts with a Checked: date and a Refresh: line ({bad})")
    skill = (KIT / ".claude/skills/nn-training/SKILL.md").read_text(encoding="utf-8")
    check(all(f"references/{n}" in skill for n in heads), "SKILL.md points to every reference")

    # 9. the final evaluation: single-use, with a receipt
    (proj / "eval/final.py").write_text(FINAL)
    cfgp, receipt = proj / ".claude/nn-training.json", proj / ".claude/state/final-eval/receipt.jsonl"
    cfg = json.loads(cfgp.read_text())

    def final_cmd(program):
        cfg["final_eval_commands"] = [f"NN_UNSEAL_TEST=1 {program} eval/final.py"]
        cfgp.write_text(json.dumps(cfg, indent=1))

    final_cmd("no-such-program-xyz")
    r = expctl(proj, "final-eval")
    check(r.returncode == 2 and "not found" in jout(r)["error"] and not receipt.exists(),
          "final-eval: a program that does not exist is refused before a use is recorded")
    final_cmd(f'"{PY}"')
    r = expctl(proj, "final-eval", "--", "--ckpt", "runs/x/best.pt; cat data/test/labels.csv")
    check(r.returncode == 2 and "without a shell" in jout(r)["error"] and not receipt.exists(),
          "final-eval: shell syntax among the arguments is refused before a use is recorded")
    r = expctl(proj, "final-eval", "--", "--ckpt", "runs/x y/best.pt")
    out, lines = jout(r), receipt.read_bytes().splitlines()
    rows = [json.loads(x) for x in lines]
    seen = json.loads(out["output_tail"].strip().splitlines()[-1])
    check(r.returncode == 0 and out["ok"] and out["use"] == 1 and seen["argv"] == ["--ckpt", "runs/x y/best.pt"]
          and seen["unseal"] == "1" and os.path.samefile(seen["cwd"], proj),
          f"final-eval: the configured command runs from the project root with its variable and the arguments ({seen})")
    check([x["event"] for x in rows] == ["start", "end"] and rows[0]["prev"] == ""
          and rows[1]["prev"] == hashlib.sha256(lines[0]).hexdigest() and rows[0]["args"] == ["--ckpt", "runs/x y/best.pt"]
          and rows[0]["source_hash"] and rows[1]["exit_code"] == 0
          and rows[1]["output_sha256"] == hashlib.sha256((proj / rows[0]["log"]).read_bytes()).hexdigest(),
          "final-eval: the receipt holds a chained start and end row with the code state and the hash of the output")
    journal = (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8")
    check("final evaluation, use 1" in journal and rows[0]["log"] in journal, "final-eval: the journal names the use and its log")
    r = expctl(proj, "final-eval")
    check(r.returncode == 2 and "single-use" in jout(r)["error"] and len(receipt.read_bytes().splitlines()) == 2,
          "final-eval: a second use is refused and nothing is recorded")
    reason = "the first use scored the wrong checkpoint"
    r = expctl(proj, "final-eval", "--again", reason, "--", "--fail")
    out, rows = jout(r), [json.loads(x) for x in receipt.read_bytes().splitlines()]
    check(r.returncode == 1 and out["use"] == 2 and out["exit_code"] == 3 and len(rows) == 4 and rows[2]["reason"] == reason
          and rows[3]["exit_code"] == 3 and rows[2]["log"] != rows[0]["log"]
          and f"Reason given for this further use: {reason}" in (proj / "experiments/JOURNAL.md").read_text(encoding="utf-8"),
          "final-eval: --again runs a further use, records the reason and passes the command's exit code on")
    shared, key = proj / ".git/nn-training-final-eval.jsonl", lambda x: (x["event"], x["use"], x["ts"])
    lines = shared.read_bytes().splitlines()
    kept = [json.loads(x) for x in lines]
    check([key(x) for x in kept] == [key(x) for x in rows] and all(x["sub"] == "" for x in kept)
          and [x["prev"] for x in kept] == [""] + [hashlib.sha256(x).hexdigest() for x in lines[:-1]],
          "final-eval: every row of the receipt is also kept, chained, in git's common folder")
    shared.unlink()  # as an earlier version left it: the receipt alone
    wt = tmp / "wt"  # another checkout of the same repository, with the same test split
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(wt)], cwd=proj, check=True)
    (wt / ".claude/nn-training.json").write_text(cfgp.read_text())
    r = expctl(wt, "final-eval")
    check(r.returncode == 2 and jout(r).get("uses") == 2 and not (wt / ".claude/state/final-eval").exists(),
          "final-eval: the uses of every checkout of the repository count, so a worktree gets no first use of its own")
    check([key(json.loads(x)) for x in shared.read_bytes().splitlines()] == [key(x) for x in rows],
          "final-eval: rows that the shared copy lacks are added to it from the receipts")
    (wt / "eval").mkdir(exist_ok=True)
    (wt / "eval/final.py").write_text(FINAL)
    r = expctl(wt, "final-eval", "--again", "a look from the worktree")
    subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=proj, check=True)
    r2 = expctl(proj, "final-eval")
    check(r.returncode == 0 and jout(r)["use"] == 3 and not wt.exists() and r2.returncode == 2 and jout(r2).get("uses") == 3,
          "final-eval: a use made in a worktree still counts after the worktree was removed (was: its receipt left with it)")
    receipt.write_bytes(b'{"event": "end"}\n')
    r = expctl(proj, "final-eval")
    check(r.returncode == 2 and "edited" in jout(r)["error"], "final-eval: a receipt whose chain is broken counts as used")

    # cleanup live runs
    for x in (active, live):
        expctl(proj, "stop", x["run_id"], "--wait", "20s", timeout=40)
    print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES")
    for f in FAILS:
        print("  -", f)
    return 1 if FAILS else 0


OPTUNA_STUB = r'''
class _L:
    WARNING = 30
    @staticmethod
    def set_verbosity(v): pass
logging = _L()
class _State:
    def __init__(self, n): self.name = n
class _Dir:
    def __init__(self, n): self.name = n
class _T:
    def __init__(self, number, state, value=None, params=None, ua=None):
        self.number, self.state, self.value = number, _State(state), value
        self.params, self.user_attrs, self.system_attrs = params or {}, ua or {}, {}
class _Study:
    directions = [_Dir("MAXIMIZE")]
    user_attrs = {"contract": "v1: val/acc max, 20 epochs"}
    def get_trials(self, deepcopy=False):
        return [_T(0, "COMPLETE", 0.8, {"lr": 1e-3}), _T(1, "COMPLETE", 0.85, {"lr": 3e-4}, {"run_dir": "runs/s-t0001"}),
                _T(2, "FAIL", ua={"fail_reason": "OOM"}), _T(3, "RUNNING")]
    @property
    def best_trial(self):
        return max([t for t in self.get_trials() if t.state.name == "COMPLETE"], key=lambda t: t.value)
def get_all_study_names(storage): return ["s"]
def load_study(study_name, storage): return _Study()
'''

if __name__ == "__main__":
    sys.exit(main())
