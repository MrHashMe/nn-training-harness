#!/usr/bin/env python3
"""Tests of the remote module (nnremote.py) and of `expctl resume`, against a stand-in for `ssh HOST`
(tests/fake_ssh.py) and a stand-in for the `hf` CLI (tests/fake_hf.py).
No network, no account, no GPU, no money. Run: python tests/test_remote.py   (about two minutes)"""
import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
from pathlib import Path

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import fake_hf  # noqa: E402
import test_kit as tk  # noqa: E402
import test_ports as tp  # noqa: E402

KIT, PY = tk.KIT, sys.executable
SCRIPTS = ".claude/skills/nn-training/scripts"
sys.path.insert(0, str(KIT / SCRIPTS))
import nnremote  # noqa: E402

FAILS = []
ENV = {}
TOKEN, SECRET, DOTENV = "tok-4f1d9a7c2b", "sec-83be61c0aa", "env-5c7e22d914"  # values that must not leak
TRAIN = r'''
import hashlib, json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, ".claude", "skills", "nn-training", "scripts"))
from runlog import RunLog
steps, mode = int(sys.argv[1]), (sys.argv[2] if len(sys.argv) > 2 else "ok")
tok = os.environ.get("NN_TEST_TOKEN")
with RunLog(config={"steps": steps}, total_steps=steps, metric="val/acc", direction="maximize", heartbeat_every=0.2) as rl:
    start = 0
    if rl.resume_from is not None and (rl.resume_from / "ckpt.json").exists():
        start = json.loads((rl.resume_from / "ckpt.json").read_text())["step"] + 1
    rl.path("seen.json").write_text(json.dumps({
        "start": start, "token_sha": hashlib.sha256(tok.encode()).hexdigest() if tok else None,
        "other_secret": "NN_LOCAL_SECRET" in os.environ,
        "files": {n: os.path.exists(os.path.join(here, n)) for n in
                  (".env", "data/train.csv", "data/test/labels.csv", "extra/notes.txt", "eval/metrics.py")}}))
    for step in range(start, steps):
        time.sleep(0.05)
        rl.log(step, **{"train/loss": 1.0 / (1 + step), "val/acc": step / steps})
        tmp = rl.path("ckpt.json.tmp")
        tmp.write_text(json.dumps({"step": step}))
        for _ in range(200):
            try:
                os.replace(tmp, rl.path("ckpt.json"))
                break
            except PermissionError:  # Windows: the file is being read for the mirror at this moment
                time.sleep(0.02)
        rl.checkpoint(rl.path("ckpt.json"), step=step)
        if mode != "deaf" and rl.should_stop():
            break
print("done", flush=True)
'''


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)
    return bool(cond)


def remote(proj, *args, env=None, timeout=90):
    return tk.sh([PY, str(proj / SCRIPTS / "nnremote.py"), *args], cwd=proj, env=dict(ENV, **(env or {})), timeout=timeout)


def parsed(r):
    try:
        return json.loads(r.stdout)
    except ValueError:
        print("STDOUT:", r.stdout[-1500:], "\nSTDERR:", r.stderr[-1500:])
        return {"ok": False, "error": "no JSON"}


def launch(proj, *args, env=None):
    return parsed(remote(proj, "launch", *args, env=env))


def state(proj, rid):
    return tk.jout(tk.expctl(proj, "status", "--run", rid))["state"]


def until(proj, rid, states, timeout=45):
    tk.wait_for(lambda: state(proj, rid) in states, timeout=timeout, every=0.3)
    return state(proj, rid)


def read(path):
    v = nnremote.expctl.read_json(path)
    return v if isinstance(v, dict) and "_error" not in v else {}


def step_of(d):
    return read(d / "ckpt.json").get("step", -1)


def ended(d, timeout=45):
    """The exit record of a mirror, written when its controller has torn down and settled."""
    tk.wait_for(lambda: (d / "exit.json").exists(), timeout=timeout)
    return read(d / "exit.json")


def stop(proj, rid):
    return tk.jout(tk.expctl(proj, "stop", rid, "--wait", "40s", timeout=70))


def ledger(proj, rid):
    return [r for r in nnremote.ledger(proj) if r["run"] == rid]


def set_remote(proj, tmp, **over):
    fake = [PY, str(TESTS / "fake_ssh.py")]
    cfg = json.loads((proj / ".claude/nn-training.json").read_text(encoding="utf-8"))
    cfg["remote"] = dict({
        "cap_usd": None, "env": ["NN_TEST_TOKEN"], "files": ["extra/notes.txt"], "poll_s": 0.3, "unreachable_s": 3,
        "price_url": (tmp / "prices.json").as_uri(),
        "targets": {
            "box": {"type": "ssh", "exec": fake, "dir": str(tmp / "remote"), "python": PY},
            "paid": {"type": "ssh", "exec": fake, "dir": str(tmp / "remote"), "python": PY, "usd_per_hour": 2.0},
            "hf": {"type": "hfjobs", "hf": [PY, str(TESTS / "fake_hf.py")], "flavor": "a10g-small",
                   "image": "python:3.12", "bucket": "tester/nn-runs", "python": PY, "usd_per_hour": 0.5,
                   "copy_every_s": 0.3}}}, **over)
    (proj / ".claude/nn-training.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")


def make_project(tmp):
    proj = tk.setup(tmp)
    (proj / "train_remote.py").write_text(TRAIN)
    (proj / "extra").mkdir()
    (proj / "extra/notes.txt").write_text("named for the remote run\n")
    (proj / ".env").write_text(f"API_KEY={DOTENV}\n")
    with open(proj / ".gitignore", "a") as f:
        f.write(".env\nextra/\n")
    (tmp / "remote").mkdir()
    (tmp / "remote/keep.txt").write_text("not the harness's to remove\n")
    bucket = tmp / "hf/buckets/tester/nn-runs"
    bucket.mkdir(parents=True)
    (bucket / "keep.txt").write_text("not the harness's to remove\n")
    (tmp / "prices.json").write_text(json.dumps([{"name": "cpu-basic", "unitCostMicroUSD": 167},
                                                 {"name": "a10g-small", "unitCostMicroUSD": 16667}]))
    set_remote(proj, tmp)
    return proj


def unit_tests(tmp):
    print("== units ==")
    rows = [{"event": "reserve", "run": "a", "usd": 2.0}, {"event": "settle", "run": "a", "usd": 0.5},
            {"event": "reserve", "run": "b", "usd": 1.0}]
    check(nnremote.committed(rows) == 1.5, "committed dollars = what ended runs were charged + open reservations in full")
    # launches and controllers book at the same moment. On Windows two appends could land on one offset: a row
    # was lost (a reservation the cap then did not count) or torn (and a torn line refuses every paid start)
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import nnremote; from pathlib import Path\n"
            "for i in range(100): nnremote.book(Path(sys.argv[2]), event='reserve', run=sys.argv[3] + '-' + str(i), "
            "usd=0.01, pad='x' * (i * 7 % 40))")
    ps = [subprocess.Popen([PY, "-c", code, str(KIT / SCRIPTS), str(tmp / "same-moment"), str(w)]) for w in range(8)]
    ends = [p.wait() for p in ps]
    try:
        booked = nnremote.ledger(tmp / "same-moment")
    except nnremote.Refuse as e:
        booked = [{"run": str(e)}]
    check(ends == [0] * 8 and len({r["run"] for r in booked}) == 800 and abs(nnremote.committed(booked) - 8) < 1e-6,
          f"ledger rows that eight processes book at the same moment all survive ({len(booked)} of 800, {booked[0]['run'][:60]})")
    counted = type("Drv", (), {"since": nnremote.time.monotonic() - 36})  # its controller has counted 36 s
    check(nnremote.used_s({"started_ts": 2000.0}, counted, 1000.0) >= 36 and nnremote.used_s({}, counted, 1000.0) == 0
          and nnremote.used_s({"started_ts": 964.0}, object(), 1000.0) == 36,
          "a clock that was set back during a run does not shorten the time booked: the controller's own count holds")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name in ("../escape.txt", "/abs.txt", "manifest.json", "exit.json", "pid.json", "sub/../../up.txt",
                     "c:evil.txt", "ok/metrics.jsonl", nnremote.STATE):
            data = b'{"alive": true}' if name == nnremote.STATE else b"x"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        link = tarfile.TarInfo("link")
        link.type, link.linkname = tarfile.SYMTYPE, "/etc/passwd"
        tar.addfile(link)
    buf.seek(0)
    dest = tmp / "unit" / "mirror"
    dest.mkdir(parents=True)
    got_state = nnremote.extract(buf, dest)
    got = sorted(p.relative_to(tmp / "unit").as_posix() for p in (tmp / "unit").rglob("*") if not p.is_dir())
    check(got == ["mirror/ok/metrics.jsonl"] and got_state == {"alive": True},
          f"an archive from the remote side cannot write outside the mirror, over its records, or links ({got})")
    run, store, seen = tmp / "unit2" / "run", tmp / "unit2" / "store", {}
    run.mkdir(parents=True)
    for name in ("ckpt.json", "exit.json", "metrics.jsonl"):
        (run / name).write_text(name, encoding="utf-8")
    (store / "metrics.jsonl").mkdir(parents=True)  # the store cannot take this file at the moment
    first = nnremote.copy_out(run, store, seen, last=True)
    early = (store / "remote-exit.json").exists()
    (store / "metrics.jsonl").rmdir()
    mid = nnremote.copy_out(run, store, seen) and not (store / "remote-exit.json").exists()
    check(first is False and not early and mid and nnremote.copy_out(run, store, seen, last=True) is True
          and (store / "remote-exit.json").read_text(encoding="utf-8") == "exit.json"
          and (store / "metrics.jsonl").read_text(encoding="utf-8") == "metrics.jsonl",
          "a job's exit record reaches the result store only in its last round, after every other file")
    sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    check(read(store / nnremote.SUMS) == {n: sha(n.encode()) for n in ("ckpt.json", "metrics.jsonl")},
          "the store lists the checksum of every file copied to it; the exit record, which comes last, is not in it")
    # a training script may remove a folder of its run directory at any moment, an old checkpoint for instance. The
    # listing with rglob raised FileNotFoundError before Python 3.12 when that happened while it listed, which ended
    # the helper of a rented job and with it the job. The kit's own temporary files stay out of the store; a file of
    # the training script's stays in, whatever its name
    run, store, seen, churning = tmp / "unit3" / "runs" / "r1", tmp / "unit3" / "store", {}, [1]
    run.mkdir(parents=True)
    (run / "metrics.jsonl").write_text("{}\n", encoding="utf-8")
    (run / ".heartbeat.json.1.abc123.tmp").write_text("{}", encoding="utf-8")
    (run / ".mine.tmp").write_text("{}", encoding="utf-8")

    def pack():  # the ssh side of the same listing: op_pack writes its archive to stdout
        real, sys.stdout = sys.stdout, argparse.Namespace(buffer=io.BytesIO())
        try:
            nnremote.op_pack(argparse.Namespace(work=str(tmp / "unit3"), id="r1", newer=0.0, sums=False))
            return sys.stdout.buffer.getvalue()
        finally:
            sys.stdout = real

    def churn():
        while churning:
            for i in range(5):
                try:
                    (run / f"ckpt-{i}" / "sub").mkdir(parents=True, exist_ok=True)
                except OSError:
                    pass  # Windows: the folder of that name is still being removed
                shutil.rmtree(run / f"ckpt-{i}", ignore_errors=True)

    side = threading.Thread(target=churn)
    side.start()
    errs = []
    for listing in (lambda: nnremote.copy_out(run, store, seen), pack):
        try:
            for _ in range(300):
                listing()
            errs.append(None)
        except OSError as e:
            errs.append(repr(e))
    churning.clear()
    side.join()
    want = [".mine.tmp", "metrics.jsonl"]
    got = sorted(p.name for p in store.iterdir() if p.name != nnremote.SUMS)
    check(errs[0] is None and got == want,
          f"the copy to the store goes on while folders of the run vanish, without the kit's temporary files ({got} {errs[0]})")
    with tarfile.open(fileobj=io.BytesIO(pack())) as tar:
        got = sorted(n for n in tar.getnames() if n != nnremote.STATE)
    check(errs[1] is None and got == want, f"and so does the archive for an ssh target ({got} {errs[1]})")
    # an automatic resume that cannot start, for whatever reason, does not cost the ended run its exit record
    d = tmp / "unit4" / "runs" / "gone"
    d.mkdir(parents=True)
    man = {"run_id": "gone", "created_ts": 0.0, "cmd": ["x"], "remote": {"type": "ssh", "target": "t", "retries": 1}}

    def vanished(*a, **k):
        raise FileNotFoundError(2, "a folder vanished while it was listed")

    real_start, nnremote.start_run = nnremote.start_run, vanished
    try:
        nnremote.finish(tmp / "unit4", {}, {}, type("Drv", (), {"teardown": lambda self, state: None})(), d, man,
                        nnremote.GONE, {}, {"stop": False})
        err = None
    except OSError as e:
        err = repr(e)
    nnremote.start_run = real_start
    ex = read(d / "exit.json") if (d / "exit.json").exists() else {}
    check(err is None and "FileNotFoundError" in str((ex.get("remote") or {}).get("not_resumed")),
          f"a run whose automatic resume cannot start still gets its exit record, which says why ({ex.get('remote')} {err})")
    # the last pull of a rented job: the sync, like the real one, passes over a file of the same size that is not
    # newer by its date, which is what a checkpoint rewritten while a clock was set back looks like
    rid, hf = "unit-run", Path(os.environ["FAKE_HF_HOME"])
    mirror, out = tmp / "unit3" / rid, hf / "buckets/tester/unit" / rid / "out"
    for folder in (mirror, out, hf / "jobs/j1"):
        folder.mkdir(parents=True)
    (hf / "jobs/j1/job.json").write_text(json.dumps({"id": "j1", "flavor": "x", "stage": "COMPLETED"}))
    (out / "last.pt").write_bytes(b"step 59")
    (mirror / "last.pt").write_bytes(b"step 58")
    (mirror / "remote-exit.json").write_text("{}")  # the job ended by itself: its list is whole
    (out / nnremote.SUMS).write_text(json.dumps({"last.pt": sha(b"step 59")}))
    drv = nnremote.HfJobs({"targets": {"hf": {"hf": [PY, str(TESTS / "fake_hf.py")], "bucket": "tester/unit"}}}, mirror,
                          {"run_id": rid, "remote": {"target": "hf", "handle": {"job": "j1"}}})
    st = drv.pull(last=True)
    stale = (mirror / "last.pt").read_bytes() == b"step 58" and not nnremote.complete(mirror, st)
    drv.again(st)
    check(stale and (mirror / "last.pt").read_bytes() == b"step 59" and nnremote.complete(mirror, st),
          "a file the sync passed over is found by its checksum and fetched by itself: only then may the store go")
    (out / "last.pt").write_bytes(b"step 100")  # a copy the list does not name: it still says step 59
    st = drv.pull(last=True)
    drv.again(st)
    kept = not nnremote.complete(mirror, st)
    (mirror / "remote-exit.json").unlink()  # no exit record: the job was cut off, perhaps before it listed that copy
    st = drv.pull(last=True)
    drv.again(st)
    check(kept and nnremote.complete(mirror, st) and (mirror / "last.pt").read_bytes() == b"step 100",
          "a copy that differs from the list keeps the store of a job that ended by itself; of a job that was cut off, "
          "the store's copy counts")
    for name in ("up.txt", "manifest.json"):
        (out.parent / name).write_text("x")
        (out / name).write_text("x")
    (out / nnremote.SUMS).write_text(json.dumps({"../up.txt": sha(b"x"), "manifest.json": sha(b"x")}))
    st = drv.pull(last=True)
    drv.again(st)
    check(not (mirror.parent / "up.txt").exists() and not (mirror / "manifest.json").exists()
          and not nnremote.complete(mirror, st),
          "a listed name outside the mirror or over its records is not fetched, and the store is then kept")
    (mirror.parent / "up.txt").write_text("x")
    check(not nnremote.complete(mirror, {"files": {"../up.txt": 1}}) and not nnremote.complete(mirror, {"sums": {"../up.txt": sha(b"x")}}),
          "nor does such a name count as mirrored where a file of that size and content lies outside the mirror (was: it counted)")


def refusals(tmp, proj):
    print("== nothing starts without a target, the named inputs, and a cap that covers the run ==")
    cmd = ["--", "{python}", "train_remote.py", "5"]

    def refused(args, **cfg):
        set_remote(proj, tmp, **cfg)
        out = launch(proj, "--name", "no", *args, *cmd)
        return (out.get("error") or "?") if out.get("ok") is False else f"NOT REFUSED: {out}"

    e = refused(["--on", "nowhere"])
    check("no usable target" in e, f"an unknown target is refused ({e[:80]})")
    e = refused(["--on", "box"], env=["NN_TEST_TOKEN", "NN_NOT_SET_ANYWHERE"])
    check("NN_NOT_SET_ANYWHERE" in e and "does not set" in e, "a named variable that is not set is refused, not sent empty")
    e = refused(["--on", "box"], files=["data/test/labels.csv"])
    check("sealed" in e, f"a sealed file named in remote.files is refused ({e[:80]})")
    e = refused(["--on", "box"], files=["../outside.txt"])
    check("outside the project" in e, "a path outside the project is refused")
    e = refused(["--on", "box"], files=["no/such/file"])
    check("does not exist" in e, "a named file that does not exist is refused")
    e = refused(["--on", "box", "--hours", "0"])
    check("more than zero" in e, "--hours 0 is refused")
    e = refused(["--on", "paid"])
    check("needs --hours" in e, "a paid target without --hours is refused")
    e = refused(["--on", "paid", "--hours", "0.25"])
    check("no spending cap" in e, f"a paid target without a cap is refused ({e[:80]})")
    e = refused(["--on", "paid", "--hours", "0.25"], cap_usd=0.4)
    check("does not cover" in e and "$0.5" in e, f"a cap smaller than hours x price is refused, with the numbers ({e})")
    e = refused(["--on", "hf", "--hours", "1"], cap_usd=0.9)
    check("does not cover" in e and "$1/h" in e,
          f"a rented target is priced at the higher of the configured and the listed price ({e})")
    e = refused(["--on", "hf", "--hours", "1"], cap_usd=0.9, price_url=(tmp / "missing.json").as_uri(),
                targets={"hf": {"type": "hfjobs", "flavor": "x", "image": "i", "bucket": "b"}})
    check("no price is known" in e, "a rented target with no known price is refused")
    runs = [p for p in (proj / "runs").glob("*")] if (proj / "runs").exists() else []
    check(not runs and not nnremote.ledger_path(proj).exists() and not list((tmp / "remote").glob("2*")),
          "the refusals created no run directory, no ledger entry and nothing on the target")
    set_remote(proj, tmp)
    names = ("client_secret.json", "keys/id_rsa", "hf_token.txt", "added_tokens.json", "tokenizer.py")
    for n in names:  # untracked and not ignored: git would call all five source
        (proj / n).parent.mkdir(exist_ok=True)
        (proj / n).write_text("x\n")
    cfg = nnremote.expctl.load_config(proj)
    got = set(nnremote.bundle(proj, cfg, nnremote.settings(cfg)))
    check(not got & set(names[:3]) and set(names[3:]) <= got and nnremote.held_back(proj, cfg) == sorted(names[:3]),
          f"files whose name says credentials stay at home unless remote.files names them ({sorted(got & set(names))})")
    set_remote(proj, tmp, files=["extra/notes.txt", "hf_token.txt"])
    cfg = nnremote.expctl.load_config(proj)
    check("hf_token.txt" in nnremote.bundle(proj, cfg, nnremote.settings(cfg)), "one that remote.files names is sent")
    for n in names:
        (proj / n).unlink()
    (proj / "keys").rmdir()
    set_remote(proj, tmp)
    # The archive holds what a link leads to. A link into sealed data (where Windows gives no privilege for links:
    # a junction, which git lists file by file) or to a credentials file must not carry it along under another name.
    nnremote.expctl._link(proj / "data/test", proj / "peek")
    try:
        os.symlink(proj / ".env", proj / "plain.txt")
    except OSError:
        pass  # Windows without the privilege to create links
    cfg = nnremote.expctl.load_config(proj)
    got = sorted(n for n in nnremote.bundle(proj, cfg, nnremote.settings(cfg)) if n.startswith(("peek", "plain")))
    held = nnremote.held_back(proj, cfg)
    check(not got and ("plain.txt" in held) == (proj / "plain.txt").exists(),
          f"a link into a sealed folder, or to a credentials file, does not travel under its own name ({got}, held back: {held})")
    e = refused(["--on", "box"], files=["extra/notes.txt", "peek"])
    check("sealed" in e, f"and remote.files cannot name a link that leads into a sealed folder ({e[:90]})")
    for n in ("peek", "plain.txt"):
        if os.path.lexists(proj / n):
            try:
                os.unlink(proj / n)
            except OSError:
                os.rmdir(proj / n)  # a junction
    set_remote(proj, tmp)


def ssh_tests(tmp, proj):
    print("== ssh-type target: the same run contract, named inputs only, teardown ==")
    rroot = tmp / "remote"
    out = launch(proj, "--name", "free", "--on", "box", "--seed", "7", "--tag", "k=v", "--", "{python}",
                 "train_remote.py", "100")
    rid = out.get("run_id")
    if not check(out.get("ok") and rid and out.get("reserved_usd") == 0,
                 f"a run on a free target starts without a cap ({str(out)[:200]})"):
        return None
    d = proj / "runs" / rid
    check(until(proj, rid, ("running",), 30) == "running", "expctl status shows the remote run as running")
    w = tk.expctl(proj, "watch", rid, "--until", "terminal", "--max-time", "60s", timeout=90)
    check(w.returncode == 0 and state(proj, rid) == "completed", f"expctl watch follows it to completed ({w.stdout[-200:]})")
    ex = ended(d)
    c = tk.expctl(proj, "curve", rid)
    check(c.returncode == 0 and "val/acc" in c.stdout, "expctl curve reads the mirrored metrics")
    have = {n: (d / n).is_file() for n in ("metrics.jsonl", "result.json", "stdout.log", "ckpt.json", "heartbeat.json",
                                           "remote-exit.json", "remote-manifest.json", "seen.json")}
    check(all(have.values()) and step_of(d) == 99, f"logs, metrics and the last checkpoint are in the local run directory ({have})")
    seen = read(d / "seen.json")
    check(seen.get("token_sha") == hashlib.sha256(TOKEN.encode()).hexdigest() and seen.get("other_secret") is False,
          "the run received the variable named in remote.env and no other variable of the launching environment")
    check(seen.get("files") == {".env": False, "data/train.csv": False, "data/test/labels.csv": False,
                                "extra/notes.txt": True, "eval/metrics.py": True},
          f"it received the source and the named file, but not .env, other git-ignored data or sealed data ({seen.get('files')})")
    check(read(d / "remote-manifest.json").get("seed") == 7 and read(d / "manifest.json")["remote"]["sent_env"] == ["NN_TEST_TOKEN"],
          "seed and the names (not the values) of the sent variables are recorded")
    check(not (rroot / rid).exists() and (rroot / "keep.txt").is_file() and str(ex.get("remote", {}).get("teardown")).startswith("removed"),
          f"after the run its directory on the target is removed, and nothing else ({ex.get('remote')})")
    check(len(read(d / "manifest.json")["remote"].get("bundle_sha256") or "") == 64 and not (d / nnremote.BUNDLE).exists(),
          "the manifest names the SHA-256 of the archive that was sent, and the archive is gone once the run has ended")

    print("== stop, and resume from the mirrored checkpoint ==")
    out = launch(proj, "--name", "stopme", "--on", "box", "--", "{python}", "train_remote.py", "4000")
    rid, d = out.get("run_id"), proj / "runs" / str(out.get("run_id"))
    tk.wait_for(lambda: step_of(d) >= 5, timeout=40)
    stp = stop(proj, rid)
    ex = ended(d)
    last = step_of(d)
    check(stp.get("ok") and state(proj, rid) == "interrupted" and ex.get("stopped_for") == "stop requested" and last >= 5,
          f"expctl stop ends the remote run gracefully ({stp}, {ex.get('stopped_for')})")
    check(not (rroot / rid).exists() and (d / "ckpt.json").is_file(), "a stopped run is torn down and its checkpoint kept locally")
    r = tk.expctl(proj, "resume", rid)
    check(r.returncode == 2 and "nnremote.py resume" in r.stdout, "expctl resume sends a remote run to nnremote.py resume")
    out2 = parsed(remote(proj, "resume", rid, "--retries", "0"))
    rid2, d2 = out2.get("run_id"), proj / "runs" / str(out2.get("run_id"))
    tk.wait_for(lambda: (d2 / "seen.json").exists(), timeout=40)
    check(read(d2 / "seen.json").get("start") == last + 1 and read(d2 / "manifest.json").get("resume_of") == rid,
          f"nnremote resume continues at the step after the last checkpoint ({read(d2 / 'seen.json').get('start')} after {last})")
    stop(proj, rid2)
    ended(d2)
    src, n = proj / "train_remote.py", len(list((proj / "runs").glob("*")))
    code = src.read_bytes()
    src.write_bytes(code + b"# changed after the launch\n")
    r = remote(proj, "resume", rid, "--retries", "0")
    check("the source has changed" in r.stdout and "--allow-code-change" in r.stdout and len(list((proj / "runs").glob("*"))) == n,
          "nnremote resume refuses when the source differs from what the run was launched with (was: it sent today's "
          f"tree without a word) ({r.stdout.strip()[-200:]})")
    out3 = parsed(remote(proj, "resume", rid, "--retries", "0", "--allow-code-change"))
    d3 = proj / "runs" / str(out3.get("run_id"))
    man3 = read(d3 / "manifest.json")
    check(out3.get("ok") and man3.get("resume_of_source_hash") == read(d / "manifest.json")["snapshot"]["source_hash"]
          != man3["snapshot"]["source_hash"],
          "with --allow-code-change it resumes, and the new run records the source hash it continues from beside its own")
    stop(proj, str(out3.get("run_id")))
    ended(d3)
    src.write_bytes(code)

    print("== preemption: automatic resume from the last checkpoint ==")
    out = launch(proj, "--name", "preempt", "--on", "box", "--retries", "1", "--", "{python}", "train_remote.py", "120")
    rid, d = out.get("run_id"), proj / "runs" / str(out.get("run_id"))
    tk.wait_for(lambda: step_of(d) >= 10, timeout=40)
    fake_hf.kill_tree(read(rroot / rid / ".nnremote.json").get("pid"))  # the machine goes away mid-run
    ex = ended(d)
    last, rid2 = step_of(d), (ex.get("remote") or {}).get("resumed_as")
    check(state(proj, rid) == "interrupted" and ex.get("stopped_for") == nnremote.GONE and rid2,
          f"a run whose remote process vanished is interrupted and resumed as a new run ({ex})")
    if rid2:
        d2 = proj / "runs" / rid2
        check(until(proj, rid2, ("completed",), 60) == "completed" and read(d2 / "seen.json").get("start") == last + 1
              and last >= 10 and step_of(d2) == 119,
              f"the new run starts after the last mirrored checkpoint and finishes ({read(d2 / 'seen.json').get('start')} after {last})")
        ex2 = ended(d2)
        man2 = read(d2 / "manifest.json")
        check(man2.get("resume_of") == rid and man2["remote"]["retries"] == 0 and "resumed_as" not in (ex2.get("remote") or {}),
              "the resumed run records what it continues and has one retry fewer")
        check(not (rroot / rid).exists() and not (rroot / rid2).exists(), "both remote directories are removed")
    out = launch(proj, "--name", "preempt2", "--on", "box", "--retries", "2", "--", "{python}", "train_remote.py", "4000")
    rid, d = out.get("run_id"), proj / "runs" / str(out.get("run_id"))
    tk.wait_for(lambda: step_of(d) >= 3, timeout=40)
    man, sha = read(d / "manifest.json"), hashlib.sha256((d / nnremote.BUNDLE).read_bytes()).hexdigest()
    src.write_bytes(code + b"# changed while the run was out\n")
    fake_hf.kill_tree(read(rroot / rid / ".nnremote.json").get("pid"))
    rem = ended(d).get("remote") or {}
    rid2 = str(rem.get("resumed_as"))
    d2 = proj / "runs" / rid2
    tk.wait_for(lambda: (d2 / "seen.json").exists(), timeout=40)
    man2 = read(d2 / "manifest.json")
    there = (rroot / rid2 / "train_remote.py").read_bytes() if (rroot / rid2 / "train_remote.py").is_file() else None
    check("not_resumed" not in rem and there == code and man2.get("snapshot") == man["snapshot"]
          and man2["remote"].get("bundle_sha256") == man["remote"].get("bundle_sha256") == sha
          and not (d / nnremote.BUNDLE).exists() and (d2 / nnremote.BUNDLE).is_file(),
          "a preempted run is resumed with the code it was launched with, from the archive of that launch, although the "
          f"working tree changed meanwhile (was: resumed with the changed tree) ({rem})")
    (d2 / nnremote.BUNDLE).unlink()  # without that archive a resume can only go by the working tree
    fake_hf.kill_tree(read(rroot / rid2 / ".nnremote.json").get("pid"))
    rem = ended(d2).get("remote") or {}
    src.write_bytes(code)
    check("the source has changed" in str(rem.get("not_resumed")) and "resumed_as" not in rem,
          f"and where the archive is gone it is not resumed with changed code: its exit record says why ({rem})")

    print("== what is sent is what the launch packed ==")
    prep = ("import sys;sys.path.insert(0,sys.argv[1]);import nnremote as n,expctl as e;n.spawn_controller=lambda *a:None;"
            "root=e.find_root(None);cfg=e.load_config(root);print(n.start_run(root,cfg,n.settings(cfg),name=sys.argv[2],"
            "target='box',cmd=['{python}','train_remote.py','4000'],hours=None,retries=0)['run_id'])")

    def packed(name):  # a launch whose controller has not started yet
        rid = tk.sh([PY, "-c", prep, str(proj / SCRIPTS), name], cwd=proj, env=ENV).stdout.strip()
        return rid, proj / "runs" / (rid or "none")

    rid, d = packed("late")
    src.write_bytes(code + b"# changed between the launch and the start of its controller\n")
    side = threading.Thread(target=remote, args=(proj, "_control", str(d)), kwargs={"timeout": 150})
    side.start()
    tk.wait_for(lambda: (d / "seen.json").exists(), timeout=40)
    there = (rroot / rid / "train_remote.py").read_bytes() if (rroot / rid / "train_remote.py").is_file() else None
    src.write_bytes(code)
    check(there == code, "the controller sends the archive of the launch, whose hash the manifest holds, not the working "
                         "tree as it is when the controller starts (was: it packed the tree a second time)")
    stop(proj, rid)
    ended(d)
    side.join(60)
    rid, d = packed("swapped")
    with open(d / nnremote.BUNDLE, "ab") as f:
        f.write(b"x")
    remote(proj, "_control", str(d))
    ex = ended(d, 10)
    check("not the archive the launch packed" in str(ex.get("error")) and not (rroot / rid).exists(),
          f"an archive that is not the one the launch packed is not sent ({ex.get('error')})")

    print("== target unreachable: nothing torn down, attach picks the run up ==")
    out = launch(proj, "--name", "split", "--on", "box", "--", "{python}", "train_remote.py", "4000")
    rid, d = out.get("run_id"), proj / "runs" / str(out.get("run_id"))
    tk.wait_for(lambda: step_of(d) >= 3, timeout=40)
    Path(ENV["FAKE_SSH_DOWN"]).write_text("x")
    st = until(proj, rid, ("lost",), 40)
    check(st == "lost" and not (d / "exit.json").exists() and (rroot / rid).is_dir()
          and "attach" in (d / "supervisor.log").read_text(errors="replace"),
          f"after the target stops answering the run is 'lost', nothing is removed, and the log names attach ({st})")
    os.remove(ENV["FAKE_SSH_DOWN"])
    att = parsed(remote(proj, "attach", rid))
    check(att.get("attached") and until(proj, rid, ("running",), 30) == "running", f"nnremote attach takes control again ({att})")
    stop(proj, rid)
    ex = ended(d)
    check(state(proj, rid) == "interrupted" and not (rroot / rid).exists(), "and the run can then be stopped and torn down")
    return rid


def cap_tests(tmp, proj):
    print("== spending cap on a paid target ==")
    set_remote(proj, tmp, cap_usd=1.0)
    cmd = ["--", "{python}", "train_remote.py", "4000"]
    a = launch(proj, "--name", "paid1", "--on", "paid", "--hours", "0.25", *cmd)
    rid, d = a.get("run_id"), proj / "runs" / str(a.get("run_id"))
    check(a.get("ok") and a.get("reserved_usd") == 0.5 and a.get("committed_usd") == 0.5,
          f"a covered run starts and hours x price is reserved ({str(a)[:160]})")
    b = launch(proj, "--name", "paid2", "--on", "paid", "--hours", "0.3", *cmd)
    check(b.get("ok") is False and "does not cover" in b.get("error", "") and "$0.5 already committed" in b["error"],
          f"a second run that would pass the cap is refused while the first is reserved ({b.get('error')})")
    s = parsed(remote(proj, "status"))
    check(s.get("committed_usd") == 0.5 and [o["run"] for o in s.get("open", [])] == [rid], "nnremote status shows the open reservation")
    tk.wait_for(lambda: step_of(d) >= 3, timeout=40)
    stop(proj, rid)
    ended(d)
    rows = ledger(proj, rid)
    check([r["event"] for r in rows] == ["reserve", "settle"] and 0 < rows[1]["usd"] <= 0.05 and rows[1]["confirmed_end"],
          f"when the run ends, the ledger books the time used, not more than the reservation ({rows})")
    c = launch(proj, "--name", "paid2", "--on", "paid", "--hours", "0.3", *cmd)
    check(c.get("ok") and c.get("reserved_usd") == 0.6, "after that the freed part of the cap can be used again")
    if c.get("ok"):
        stop(proj, c["run_id"])
        ended(proj / "runs" / c["run_id"])
    text = nnremote.ledger_path(proj).read_text(encoding="utf-8")
    nnremote.ledger_path(proj).write_text(text + "not a ledger row\n", encoding="utf-8")
    e = launch(proj, "--name", "paid3", "--on", "paid", "--hours", "0.1", *cmd)
    check(e.get("ok") is False and "not a ledger row" in e.get("error", ""), "a damaged ledger refuses every paid start")
    nnremote.ledger_path(proj).write_text(text, encoding="utf-8")
    away = nnremote.ledger_path(proj).with_suffix(".away")
    nnremote.ledger_path(proj).rename(away)
    e = launch(proj, "--name", "paid4", "--on", "paid", "--hours", "0.1", *cmd)
    check(e.get("ok") is False and "is gone" in e.get("error", ""),
          "a ledger that vanished after paid runs refuses every paid start, instead of counting the cap from zero")
    away.rename(nnremote.ledger_path(proj))


def hf_tests(tmp, proj):
    print("== Hugging Face Jobs (stand-in CLI): rented GPU job with a provider-side time limit ==")
    set_remote(proj, tmp, cap_usd=5.0)
    bucket = tmp / "hf/buckets/tester/nn-runs"
    out = launch(proj, "--name", "hf1", "--on", "hf", "--hours", "0.05", "--", "{python}", "train_remote.py", "60")
    rid = out.get("run_id")
    if not check(out.get("ok") and out.get("reserved_usd") == 0.05 and abs(out.get("usd_per_hour", 0) - 1.00002) < 1e-9,
                 f"a covered job starts; the reservation uses the listed price ({str(out)[:200]})"):
        return
    d = proj / "runs" / rid
    check(until(proj, rid, ("completed",), 60) == "completed", "the job's run shows as completed through expctl status")
    ex = ended(d)
    seen = read(d / "seen.json")
    check(step_of(d) == 59 and (d / "metrics.jsonl").is_file() and (d / "stdout.log").is_file()
          and seen.get("token_sha") == hashlib.sha256(TOKEN.encode()).hexdigest() and seen.get("other_secret") is False
          and seen.get("files", {}).get(".env") is False and seen["files"].get("data/test/labels.csv") is False
          and seen["files"].get("extra/notes.txt") is True,
          f"results are mirrored; the job got the named variable and file only ({seen})")
    calls = [json.loads(x) for x in Path(ENV["FAKE_HF_LOG"]).read_text(encoding="utf-8").splitlines()]
    run = next(c for c in calls if c[:2] == ["jobs", "run"])
    check(run[run.index("--timeout") + 1] == "3m" and run[run.index("-s") + 1] == "NN_TEST_TOKEN"
          and f"kit_run={rid}" in run and run[run.index("--flavor") + 1] == "a10g-small",
          "the job is started with a provider-side time limit of the reserved hours, a label and the secret's name")
    check(not (bucket / rid).exists() and (bucket / "keep.txt").is_file() and "removed" in str(ex.get("remote", {}).get("teardown")),
          "after the job its prefix in the bucket is removed; the bucket and its other content stay")
    rows = ledger(proj, rid)
    check([r["event"] for r in rows] == ["reserve", "settle"] and 0 < rows[1]["usd"] <= rows[0]["usd"],
          f"the ledger settles at the time used ({rows})")

    out = launch(proj, "--name", "hfstop", "--on", "hf", "--hours", "0.05", "--", "{python}", "train_remote.py", "4000")
    rid, d = out.get("run_id"), proj / "runs" / str(out.get("run_id"))
    tk.wait_for(lambda: step_of(d) >= 5, timeout=40)
    stop(proj, rid)
    ex = ended(d)
    check(state(proj, rid) == "interrupted" and ex.get("stopped_for") == "stop requested" and not (bucket / rid).exists()
          and step_of(d) >= 5, f"expctl stop ends a job gracefully and it is torn down ({ex.get('stopped_for')})")

    out = launch(proj, "--name", "hfpre", "--on", "hf", "--hours", "0.05", "--retries", "1", "--", "{python}",
                 "train_remote.py", "120")
    rid, d = out.get("run_id"), proj / "runs" / str(out.get("run_id"))
    tk.wait_for(lambda: step_of(d) >= 10, timeout=40)
    fake_hf.preempt(read(d / "manifest.json")["remote"]["handle"]["job"])
    ex = ended(d)
    last, rid2 = step_of(d), (ex.get("remote") or {}).get("resumed_as")
    ok = check(state(proj, rid) == "interrupted" and rid2, f"a job that is taken away is resumed as a new job ({ex})")
    if ok:
        d2 = proj / "runs" / rid2
        check(until(proj, rid2, ("completed",), 60) == "completed" and read(d2 / "seen.json").get("start") == last + 1
              and last >= 10, f"which continues after the last mirrored checkpoint ({read(d2 / 'seen.json').get('start')} after {last})")
        ended(d2)
        check(not (bucket / rid).exists() and not (bucket / rid2).exists() and len(ledger(proj, rid2)) == 2,
              "both prefixes are removed, and the resumed job was reserved and settled on its own")

    out = launch(proj, "--name", "hfover", "--on", "hf", "--hours", "0.001", "--retries", "2", "--", "{python}",
                 "train_remote.py", "100000", "deaf", env={"FAKE_HF_TIMEOUT_S": "5"})
    rid, d = out.get("run_id"), proj / "runs" / str(out.get("run_id"))
    ex = ended(d, 60)
    rows = ledger(proj, rid)
    check(ex.get("stopped_for") == nnremote.USED_UP and "resumed_as" not in (ex.get("remote") or {})
          and state(proj, rid) == "interrupted" and len(rows) == 2 and rows[1]["usd"] == rows[0]["usd"] == 0.001,
          f"a job the provider ends at its time limit is not resumed, and costs its reservation at most ({ex}, {rows})")


def local_resume(tmp, proj, remote_rid):
    print("== expctl resume (local runs) ==")
    out = tk.jout(tk.expctl(proj, "launch", "--name", "loc", "--snapshot", "none", "--seed", "3", "--tag", "a=b", "--",
                            PY, "train_remote.py", "4000"))
    rid, d = out["run_id"], proj / "runs" / out["run_id"]
    tk.wait_for(lambda: step_of(d) >= 5, timeout=40)
    r = tk.expctl(proj, "resume", rid)
    check(r.returncode == 4 and "has ended" in r.stdout, "expctl resume refuses a run that is still active")
    stop(proj, rid)
    last = step_of(d)
    out2 = tk.jout(tk.expctl(proj, "resume", rid))
    rid2, d2 = out2["run_id"], proj / "runs" / out2["run_id"]
    tk.wait_for(lambda: (d2 / "seen.json").exists(), timeout=40)
    man2 = read(d2 / "manifest.json")
    check(out2.get("resume_of") == rid and read(d2 / "seen.json").get("start") == last + 1 and man2.get("resume_of") == rid
          and man2.get("seed") == 3 and man2.get("tags") == {"a": "b"} and man2.get("cmd") == read(d / "manifest.json")["cmd"],
          f"expctl resume repeats the command with the same seed and tags and continues after the last checkpoint ({out2})")
    stop(proj, rid2)
    check(read(d2 / "result.json").get("meta", {}).get("resume_of") == rid, "the result of a resumed run names the run it continues")
    src = proj / "train_remote.py"
    code = src.read_bytes()
    src.write_bytes(code + b"# changed after the launch\n")
    r = tk.expctl(proj, "resume", rid)
    out3 = tk.jout(tk.expctl(proj, "resume", rid, "--allow-code-change"))
    man3 = read(proj / "runs" / str(out3.get("run_id")) / "manifest.json")
    src.write_bytes(code)
    check(r.returncode == 2 and "the source has changed" in r.stdout and "--allow-code-change" in r.stdout,
          "expctl resume refuses when the source differs from what the run was launched with (was: it ran today's tree "
          "without a word)")
    check(man3.get("resume_of_source_hash") == read(d / "manifest.json")["snapshot"]["source_hash"] != man3["snapshot"]["source_hash"],
          "with --allow-code-change it resumes, and the new run records the source hash it continues from beside its own")
    stop(proj, str(out3.get("run_id")))
    r = remote(proj, "resume", rid)
    check("not a remote run" in r.stdout, "nnremote resume refuses a local run")
    if remote_rid:
        r = remote(proj, "attach", remote_rid)
        check("has ended" in r.stdout, "nnremote attach refuses a run that has ended")


def guard_tests(proj):
    print("== guard: starting remote work asks; looking does not ==")

    def bash(cmd, env=None):
        return tp.guard(proj, dict(tp.CLAUDE, cwd=str(proj), tool_input=dict(tp.CLAUDE["tool_input"], command=cmd)), env=env)

    tool = f"python {SCRIPTS}/nnremote.py"
    check(bash(f"{tool} launch --name x --on hf --hours 1 -- python train.py")[1] == "ask", "nnremote launch asks")
    check(bash(f"{tool} resume 20261111-000000-x-abcd")[1] == "ask", "nnremote resume asks")
    check(bash(f"{tool} launch --name x --on hf --hours 1 -- python train.py", {"NN_UNATTENDED": "1"})[1] == "deny",
          "and is denied when nobody can be asked")
    check(bash(f"{tool} status")[1] in (None, "allow"), "nnremote status does not ask")
    code, dec, out, _ = tp.guard(proj, dict(tp.CLAUDE, cwd=str(proj), tool_name="Edit", tool_input={
        "file_path": str(nnremote.ledger_path(proj)), "old_string": "a", "new_string": "b"}))
    check(dec == "ask", f"an edit of the spending ledger asks ({dec})")
    code, dec, out, _ = tp.guard(proj, dict(tp.CLAUDE, cwd=str(proj), tool_name="Edit", tool_input={
        "file_path": str(proj / ".claude/nn-training.json"), "old_string": '"cap_usd": 1', "new_string": '"cap_usd": 99'}))
    check(dec == "ask", f"an edit of the config that holds the cap asks ({dec})")


def leak_scan(tmp, proj):
    print("== no secret value anywhere on disk ==")
    hits = []
    for top in (proj, tmp / "remote", tmp / "hf", tmp / "logs"):
        for p in top.rglob("*"):
            if p.is_file() and ".git" not in p.relative_to(top).parts and p != proj / ".env" and p.name != "train_remote.py":
                data = p.read_bytes()
                hits += [f"{name} in {p.relative_to(tmp)}" for name, val in
                         (("the named token", TOKEN), ("the unnamed secret", SECRET), ("the .env value", DOTENV))
                         if val.encode() in data]
    check(not hits, f"neither the sent secret, nor an unnamed one, nor .env content is in a run directory, the ledger, "
                    f"a log, a command line or on the target ({hits[:4]})")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="nnkit-remote-"))
    (tmp / "logs").mkdir()
    ENV.update(NN_TEST_TOKEN=TOKEN, NN_LOCAL_SECRET=SECRET, FAKE_SSH_LOG=str(tmp / "logs/ssh.log"),
               FAKE_SSH_DOWN=str(tmp / "down"), FAKE_HF_HOME=str(tmp / "hf"), FAKE_HF_LOG=str(tmp / "logs/hf.log"))
    os.environ["FAKE_HF_HOME"] = ENV["FAKE_HF_HOME"]  # for fake_hf.preempt in this process
    try:
        unit_tests(tmp)
        proj = make_project(tmp)
        refusals(tmp, proj)
        rid = ssh_tests(tmp, proj)
        cap_tests(tmp, proj)
        hf_tests(tmp, proj)
        local_resume(tmp, proj, rid)
        guard_tests(proj)
        leak_scan(tmp, proj)
    finally:
        for x in tk.jout(tk.expctl(proj, "status", "--no-gpu")).get("active", []) if "proj" in locals() else []:
            tk.expctl(proj, "stop", x["run_id"], "--wait", "20s", timeout=40)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES")
    for f in FAILS:
        print("  -", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
