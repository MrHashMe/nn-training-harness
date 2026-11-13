#!/usr/bin/env python3
"""Stand-in for the `hf` CLI in tests/test_remote.py. Storage buckets are folders under $FAKE_HF_HOME/buckets; a job
is a local process that sees the bucket at its mount point, gets only the variables named with -s, and is ended when
its --timeout is over ($FAKE_HF_TIMEOUT_S shortens that for a test). It knows just the commands nnremote.py uses:

    buckets sync SRC DST [--exclude PATTERN]...     buckets cp SRC DST     buckets rm BUCKET/PATH --recursive
    jobs run -d --flavor F --timeout T [-l K=V] [-v hf://buckets/B:/MOUNT] [-s NAME]... IMAGE COMMAND...
    jobs inspect JOB                                jobs cancel JOB

$FAKE_HF_LOG names a file that receives the arguments of every call. preempt() ends a job from outside."""
import fnmatch
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

KEEP = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "PATHEXT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG")
PREFIX = "hf://buckets/"
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}
DETACH = {"creationflags": 0x00000008 | 0x00000200} if os.name == "nt" else {"start_new_session": True}


def home():
    return Path(os.environ["FAKE_HF_HOME"])


def place(s):
    """A bucket address (with or without the hf://buckets/ prefix) or a local path -> the folder or file it means."""
    if s.startswith(PREFIX):
        return home() / "buckets" / s[len(PREFIX):].strip("/")
    return Path(s)


def kill_tree(pid):
    """End a process and everything it started, at once, the way a machine that is taken away does."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        return
    kids = {}
    for line in subprocess.run(["ps", "-eo", "pid=,ppid="], capture_output=True, text=True).stdout.splitlines():
        child, parent = line.split()
        kids.setdefault(int(parent), []).append(int(child))
    todo, found = [int(pid)], []
    while todo:
        p = todo.pop()
        found.append(p)
        todo += kids.get(p, [])
    for p in found:
        try:
            os.kill(p, signal.SIGKILL)
        except OSError:
            pass


def preempt(job):
    """For the tests: the provider takes the job's machine away."""
    (home() / "jobs" / job / "preempt").write_text("x")


def sync(src, dst, exclude):
    src, dst = place(src), place(dst)
    for p in (sorted(src.rglob("*")) if src.is_dir() else []):
        rel = p.relative_to(src).as_posix()
        if not p.is_file() or any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(p.name, pat) for pat in exclude):
            continue
        q = dst / rel
        try:
            s = p.stat()
            # the real CLI's rule (huggingface_hub 2.4.0, _buckets.py): a file of the same size that is not newer
            # than the copy here by more than a second counts as identical
            if q.is_file() and q.stat().st_size == s.st_size and s.st_mtime - q.stat().st_mtime <= 1:
                continue
            q.parent.mkdir(parents=True, exist_ok=True)
            tmp = q.with_name(q.name + ".sync-tmp")
            shutil.copyfile(p, tmp)
            os.replace(tmp, q)
        except OSError:
            pass  # the file is being replaced at this moment: the next sync brings it
    return 0


def jobs_run(args):
    opt = {"-l": [], "-v": [], "-s": [], "--flavor": None, "--timeout": "30m"}
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-d":
            i += 1
            continue
        if isinstance(opt[args[i]], list):
            opt[args[i]].append(args[i + 1])
        else:
            opt[args[i]] = args[i + 1]
        i += 2
    image, cmd = args[i], args[i + 1:]
    job = secrets.token_hex(12)
    d = home() / "jobs" / job
    work = home() / "work" / job
    d.mkdir(parents=True)
    work.mkdir(parents=True)
    mounts = [(v.rsplit(":", 1)[1], str(place(v.rsplit(":", 1)[0]))) for v in opt["-v"]]

    def inside(a):  # a path as the container sees it -> where it is here
        for mount, real in mounts:
            if a == mount or a.startswith(mount + "/"):
                return real + a[len(mount):]
        return str(work) if a == "/work" else a
    t = opt["--timeout"]
    seconds = float(t[:-1]) * {"s": 1, "m": 60, "h": 3600}[t[-1]] if t[-1] in "smh" else float(t)
    seconds = float(os.environ.get("FAKE_HF_TIMEOUT_S") or seconds)
    (d / "job.json").write_text(json.dumps({"id": job, "image": image, "flavor": opt["--flavor"], "labels": opt["-l"],
                                            "secrets": opt["-s"], "cmd": [inside(a) for a in cmd], "work": str(work),
                                            "timeout_s": seconds, "stage": "RUNNING"}))
    env = {k: os.environ[k] for k in KEEP if k in os.environ}
    env.update({n: os.environ[n] for n in opt["-s"]})  # a secret is handed over in memory, never written here
    env["FAKE_HF_HOME"] = str(home())
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "_job", job], env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, **DETACH)
    print(f"Job started with ID: {job}\nView at: https://huggingface.co/jobs/tester/{job}")
    return 0


def job_main(job):
    d = home() / "jobs" / job
    rec = json.loads((d / "job.json").read_text())
    with open(d / "log.txt", "ab") as log:
        child = subprocess.Popen(rec["cmd"], cwd=rec["work"], stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, **NOWIN)
        t_end, stage = time.time() + rec["timeout_s"], None
        while stage is None:
            try:
                stage = "COMPLETED" if child.wait(timeout=0.2) == 0 else "ERROR"
            except subprocess.TimeoutExpired:
                stage = "CANCELED" if (d / "cancel").exists() else "ERROR" if (d / "preempt").exists() else \
                    "TIMEOUT" if time.time() > t_end else None
                if stage:
                    kill_tree(child.pid)
    rec["stage"] = stage
    (d / "job.json").write_text(json.dumps(rec))
    return 0


def main():
    a = sys.argv[1:]
    if os.environ.get("FAKE_HF_LOG") and a[0] != "_job":
        with open(os.environ["FAKE_HF_LOG"], "a", encoding="utf-8") as f:
            f.write(json.dumps(a) + "\n")
    if a[0] == "_job":
        return job_main(a[1])
    if a[:2] == ["buckets", "sync"]:
        rest = a[2:]
        exclude = [rest[i + 1] for i, x in enumerate(rest) if x == "--exclude"]
        return sync(rest[0], rest[1], exclude)
    if a[:2] == ["buckets", "cp"]:
        dst = place(a[3])
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(place(a[2]), dst)
        return 0
    if a[:2] == ["buckets", "rm"] and "--recursive" in a:
        shutil.rmtree(place(PREFIX + a[2][len(PREFIX):] if a[2].startswith(PREFIX) else PREFIX + a[2]))
        return 0
    if a[:2] == ["jobs", "run"]:
        return jobs_run(a[2:])
    if a[:2] == ["jobs", "inspect"]:
        rec = json.loads((home() / "jobs" / a[2] / "job.json").read_text())
        print(json.dumps([{"id": rec["id"], "flavor": rec["flavor"], "status": {"stage": rec["stage"], "message": None}}]))
        return 0
    if a[:2] == ["jobs", "cancel"]:
        (home() / "jobs" / a[2] / "cancel").write_text("x")
        return 0
    sys.stderr.write(f"fake hf: unknown command {a}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
