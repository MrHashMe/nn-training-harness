#!/usr/bin/env python3
"""nnremote - run an expctl run on a remote or rented GPU machine (stdlib only; optional, off until configured).

A remote run has an ordinary run directory under <runs_dir>/ on this machine, kept in step with the remote one
by a small local controller process. So `expctl status`, `watch`, `curve` and `stop` work on it unchanged, and an
interrupted run is continued from the checkpoints its local directory holds.

    nnremote.py launch --name NAME --on TARGET [--hours H] [--retries K] [--seed S] [--note TEXT] [--tag k=v] -- CMD ...
    nnremote.py resume RUN [--on TARGET] [--hours H] [--retries K]
    nnremote.py attach RUN     restart the controller of a run whose controller died (starts nothing remote)
    nnremote.py status         the spending cap, what is committed against it, and the open remote runs

Targets, the spending cap, and the names of the environment variables and git-ignored files a remote run receives
come from the "remote" section of .claude/nn-training.json, which an agent cannot edit without approval. Nothing
paid starts without a cap that covers it. Read references/remote.md before the first use.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import platform
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import expctl  # noqa: E402

KIT_REL = ".claude/skills/nn-training/scripts"
HF_PRICES = "https://huggingface.co/api/jobs/hardware"
# What a launch packed for the remote side, with its SHA-256 in the manifest. It lies in the mirror until the run has
# ended: the controller sends this file and nothing else, and an automatic resume sends it again.
BUNDLE = ".nnremote-bundle.tar.gz"
# the mirror's own records: never taken from a remote machine
LOCAL_ONLY = ("manifest.json", "pid.json", "stop.json", "exit.json", "supervisor.log", BUNDLE)
# how the files of the remote run directory are named in the mirror (None: not mirrored)
RENAME = {"manifest.json": "remote-manifest.json", "exit.json": "remote-exit.json", "pid.json": None,
          "stop.json": None, "supervisor.log": None}
STATE = ".remote-state.json"
SUMS = "remote-files.json"  # in a result store: the SHA-256 of every file the job has copied there
ENDED = ("COMPLETED", "CANCELED", "CANCELLED", "ERROR", "DELETED", "FAILED", "TIMEOUT")
GONE = "the remote job ended without an exit record (preempted or cancelled from outside)"
USED_UP = "the reserved hours were used up"
# The first command sent to an ssh-type target has no file to run yet: python reads its code from the first
# line of stdin. No quote characters, so it survives the quoting of any transport.
BOOT = "import sys;exec(sys.stdin.buffer.readline())"
UNTAR = (b'import os,tarfile;d=sys.argv[1];os.makedirs(d,exist_ok=True);'
         b'tarfile.open(fileobj=sys.stdin.buffer,mode="r|gz").extractall('
         b'd,**({"filter":"data"} if hasattr(tarfile,"data_filter") else {}))\n')
NOWIN = {"creationflags": 0x08000000} if os.name == "nt" else {}  # CREATE_NO_WINDOW
DETACH = {"creationflags": 0x00000008 | 0x00000200} if os.name == "nt" else {"start_new_session": True}


class Refuse(Exception):
    """Why nothing was started."""


class Transport(Exception):
    """A command on or about the remote side failed."""


class Unreachable(Exception):
    """The remote side stopped answering: its state is unknown, so nothing is torn down or settled."""


PULL_ERRORS = (Transport, subprocess.TimeoutExpired, OSError, ValueError, tarfile.TarError)


def quiet(fn, *args):
    try:
        return fn(*args)
    except PULL_ERRORS:
        return None


def settings(cfg):
    r = cfg.get("remote")
    r = r if isinstance(r, dict) else {}

    def num(key, default):
        return float(r[key]) if expctl.is_num(r.get(key)) else default
    return {"cap_usd": r.get("cap_usd"), "env": [str(n) for n in r.get("env") or []],
            "files": [str(n) for n in r.get("files") or []],
            "targets": r.get("targets") if isinstance(r.get("targets"), dict) else {},
            "max_bundle_mb": num("max_bundle_mb", 500.0), "poll_s": num("poll_s", 30.0),
            "unreachable_s": num("unreachable_s", 600.0), "price_url": r.get("price_url") or HF_PRICES}


# ---------------------------------------------------------------- money: the cap and the ledger

def ledger_path(root):
    return root / ".claude" / "state" / "remote-ledger.jsonl"


def ledger(root):
    rows = []
    try:
        lines = ledger_path(root).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return rows
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if not (isinstance(row, dict) and expctl.is_num(row.get("usd")) and row.get("run")):
            raise Refuse(f"{expctl.rel_to(root, ledger_path(root))} has a line that is not a ledger row; "
                         "nothing paid starts until the user has repaired it")
        rows.append(row)
    return rows


def committed(rows):
    """Dollars committed against the cap: what ended runs were charged, and the whole reservation of every run
    that has not been settled yet."""
    per = {}
    for r in rows:
        if r.get("event") == "settle":
            per[r["run"]] = r["usd"]
        else:
            per.setdefault(r["run"], r["usd"])
    return sum(per.values())


def book(root, **row):
    p = ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": round(time.time(), 1), **row}) + "\n")


def hourly_rate(target, tgt, st):
    """Dollars per hour to reserve: for a rented target the higher of the configured and the listed price."""
    conf = tgt.get("usd_per_hour")
    conf = float(conf) if expctl.is_num(conf) else None
    if tgt["type"] != "hfjobs":
        return conf or 0.0, None
    listed, note = None, None
    try:
        with urllib.request.urlopen(st["price_url"], timeout=15) as f:
            for h in json.load(f):
                if isinstance(h, dict) and h.get("name") == tgt.get("flavor") and expctl.is_num(h.get("unitCostMicroUSD")):
                    listed = h["unitCostMicroUSD"] * 60 / 1e6  # the list gives micro-dollars per minute
    except (OSError, ValueError) as e:
        note = f"the provider's price list could not be read ({type(e).__name__}); the configured price was used"
    rate = max(conf or 0.0, listed or 0.0)
    if rate <= 0:
        raise Refuse(f'no price is known for target "{target}" (flavor {tgt.get("flavor")}): set its usd_per_hour')
    return rate, note


def reserve(root, st, run_id, target, rate, hours):
    """Book hours x rate against the cap before anything paid starts, or refuse."""
    if rate <= 0:
        return 0.0
    if not hours or hours <= 0:
        raise Refuse("a paid target needs --hours: hours x price is reserved against the cap, and the job is "
                     "ended when the hours are used up")
    cap = st["cap_usd"]
    if not expctl.is_num(cap) or cap <= 0:
        raise Refuse(f'no spending cap is set: nothing paid starts until the user has put "cap_usd" into the '
                     f'"remote" section of {expctl.CONFIG_REL}')
    usd = round(hours * rate, 4)
    before = committed(ledger(root))
    if before + usd > cap + 1e-9:
        raise Refuse(f"the cap does not cover this run: ${usd:.4g} to reserve ({hours:g} h x ${rate:.4g}/h), "
                     f"${before:.4g} already committed, cap ${cap:.4g}")
    book(root, event="reserve", run=run_id, target=target, usd=usd, hours=hours, rate=rate)
    if committed(ledger(root)) > cap + 1e-9:  # another launch reserved at the same moment
        book(root, event="settle", run=run_id, usd=0.0, why="lost the race for the rest of the cap")
        raise Refuse("another launch reserved the rest of the cap at the same moment")
    return usd


# ---------------------------------------------------------------- what travels

# File names that usually hold credentials. Such a file travels only when remote.files names it, even when git
# tracks it or has not been told to ignore it. (added_tokens.json and tokenizer files do not match.)
SECRETISH = re.compile(
    r"(?:^|/)(?:\.env(?:\.[^/]*)?|\.netrc|\.npmrc|\.pypirc|id_(?:rsa|dsa|ecdsa|ed25519)[^/]*|[^/]*\.(?:pem|key|p12|pfx)|"
    r"(?:[^/]*[-_.])?(?:credentials?|secrets?|token)(?:\.(?:json|ya?ml|toml|txt|ini|cfg))?|"
    r"service[-_]?account[^/]*\.json)$", re.I)


def places(root, p, rel):
    """The names a file is judged by: its own and, where a link or a junction leads elsewhere, that of the place it
    really lies in (relative to the project when it is inside it). The archive holds what a link leads to, so a
    link into sealed data, or to a credentials file, would otherwise carry it along under another name."""
    real, top = Path(os.path.realpath(p)), Path(os.path.realpath(root))
    try:
        return {rel, real.relative_to(top).as_posix()}
    except ValueError:
        return {rel, real.as_posix()}


def held_back(root, cfg):
    """Source files that bundle() leaves at home because of their name, or of the name of what they link to."""
    return sorted(f for f in expctl.source_files(root, cfg)[0] if any(SECRETISH.search(n) for n in places(root, root / f, f)))


def bundle(root, cfg, st):
    """{relative path: file or bytes} of what a launch packs for a remote run: the experiment's source as git sees
    it, the kit's scripts and config and the paths named in remote.files.
    Never: sealed paths, other git-ignored files (.env among them), the rest of .claude/, and files whose name
    says credentials (SECRETISH) unless remote.files names them."""
    sealed = cfg.get("sealed_paths") or []
    files, _ = expctl.source_files(root, cfg)
    out = {f: root / f for f in files if (root / f).is_file() and not any(
        expctl.path_matches(n, sealed) or SECRETISH.search(n) for n in places(root, root / f, f))}
    for p in sorted((root / KIT_REL).glob("*.py")):
        out[f"{KIT_REL}/{p.name}"] = p
    raw = expctl.read_json(root / expctl.CONFIG_REL)
    raw = {k: v for k, v in (raw if isinstance(raw, dict) else {}).items() if k != "remote"}
    out[expctl.CONFIG_REL] = json.dumps(raw, indent=1).encode()
    for name in st["files"]:
        out.update(below(root, cfg, name))
    return out


def below(root, cfg, name, run=False):
    """{relative path: file} of a path that remote.files names or, with run, of the earlier run's directory that a
    resume sends along."""
    sealed = cfg.get("sealed_paths") or []
    top, out = Path(os.path.normpath(root / name)), {}
    try:
        rel0 = top.relative_to(root).as_posix()
    except ValueError:
        raise Refuse(f'"{name}" is outside the project, so it cannot be sent to a remote machine')
    if not top.exists():
        raise Refuse(f'remote.files names "{name}", which does not exist')
    for q in ([top] if top.is_file() else sorted(x for x in top.rglob("*") if x.is_file())):
        rel = rel0 if q == top else f"{rel0}/{q.relative_to(top).as_posix()}"
        if any(expctl.path_matches(n, sealed) for n in places(root, q, rel)):
            raise Refuse(f"{rel} is sealed, or a link that leads into a sealed path, and is never sent to a remote "
                         f"machine; name narrower paths in remote.files")
        if not (run and q.relative_to(top).parts[0] in ("src", "stdout.log", "pid.json", "supervisor.log", BUNDLE)):
            out[rel] = q
    return out


def fits(st, *members):
    """Refuse when what is to be sent is more than remote.max_bundle_mb."""
    size = sum(len(v) if isinstance(v, bytes) else v.stat().st_size for m in members for v in m.values())
    if size > st["max_bundle_mb"] * 1e6:
        raise Refuse(f"the files to send are {size / 1e6:.0f} MB, more than remote.max_bundle_mb "
                     f"({st['max_bundle_mb']:g}); send less, or raise the limit")


def write_tar(members, fileobj):
    with tarfile.open(fileobj=fileobj, mode="w|gz", dereference=True) as tar:
        for rel, src in sorted(members.items()):
            if isinstance(src, bytes):
                info = tarfile.TarInfo(rel)
                info.size, info.mtime, info.mode = len(src), time.time(), 0o644
                tar.addfile(info, io.BytesIO(src))
            else:
                tar.add(str(src), arcname=rel, recursive=False)


def digest(src, dst=os.devnull):
    """SHA-256 of a file's content. With dst the same bytes are written there: one read for the copy and its
    checksum, so the checksum is of what was copied even if the file changes meanwhile."""
    h = hashlib.sha256()
    with open(src, "rb") as i, open(dst, "wb") as o:
        for block in iter(lambda: i.read(1 << 20), b""):
            h.update(block)
            o.write(block)
    return h.hexdigest()


def safe(name):
    """A file name from the remote side that the mirror may take: inside it, and not one of its own records."""
    parts = name.split("/")
    return "\\" not in name and ":" not in name and not any(p in ("", ".", "..") for p in parts) \
        and parts[0] not in LOCAL_ONLY


def extract(fileobj, dest):
    """Unpack what a remote machine sent into the mirror: regular files only, inside dest, and never over the
    mirror's own records. Returns the remote state the stream carried."""
    state = {}
    with tarfile.open(fileobj=fileobj, mode="r|*") as tar:
        for m in tar:
            if not m.isfile() or not safe(m.name):
                continue
            f = tar.extractfile(m)
            if m.name == STATE:
                state = json.load(f)
                continue
            target = dest.joinpath(*m.name.split("/"))
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                part = target.with_name(target.name + ".part")
                with open(part, "wb") as o:
                    shutil.copyfileobj(f, o)
                os.replace(part, target)
            except OSError:
                pass  # a name this filesystem cannot hold: complete() then keeps the remote copy from being removed
    return state if isinstance(state, dict) else {}


def complete(d, state):
    """True when every file the remote side listed is in the mirror: with the listed size, and with the listed
    content where a checksum came with it (the last pull). Sizes and dates alone would pass a checkpoint that was
    rewritten with the same size while a clock was set back."""
    for key, same in (("files", lambda p, size: p.stat().st_size == size), ("sums", lambda p, sha: digest(p) == sha)):
        for name, want in (state.get(key) or {}).items():
            p = d.joinpath(*name.split("/"))
            # a name that extract() would not take is not in the mirror, whatever lies at the place it points to
            if name.split("/")[0] not in LOCAL_ONLY and not (safe(name) and p.is_file() and same(p, want)):
                return False
    return True


def run_args(man):
    """Arguments of the remote-side `_run` for this run. The command travels hex-encoded, so no transport has to
    quote it."""
    rem = man["remote"]
    a = ["--id", man["run_id"], "--name", expctl.slug(man.get("name") or "run"),
         "--cmd", json.dumps(man["cmd"]).encode().hex()]
    if man.get("seed") is not None:
        a += ["--seed", str(man["seed"])]
    if rem.get("hours"):
        total = rem["hours"] * 3600
        a += ["--budget-s", str(max(1, int(total - min(300, total * 0.1))))]  # the run saves before the hours end
    if man.get("resume_of"):
        a += ["--resume-from", man["resume_of"]]
    sh = (man.get("snapshot") or {}).get("source_hash")
    return a + (["--source-hash", sh] if sh else [])


# ---------------------------------------------------------------- targets (one class per type)

class Ssh:
    """A machine reached through a command that runs one command line on it: `ssh HOST`, or anything of that
    shape (`wsl.exe -d Ubuntu -- bash -lc`). Also the route to a rented VM and to a Slurm login node."""

    def __init__(self, st, d, man):
        tgt = st["targets"][man["remote"]["target"]]
        self.d, self.man, self.id = d, man, man["run_id"]
        self.exec, self.py = [str(x) for x in tgt["exec"]], str(tgt.get("python") or "python3")
        self.work = f'{str(tgt.get("dir") or "nnremote").rstrip("/")}/{self.id}'
        self.tool = f"{self.work}/{KIT_REL}/"
        self.newer = 0.0
        self.where = f"{self.work} on target {man['remote']['target']}"

    def call(self, argv, stdin=None, data=None, out=None, timeout=3600):
        kw = {"input": data} if data is not None else {"stdin": stdin or subprocess.DEVNULL}
        r = subprocess.run(self.exec + [shlex.join(argv)], stdout=out or subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout, **kw, **NOWIN)
        if r.returncode != 0:
            raise Transport(f"remote command failed (exit {r.returncode}): "
                            f"{r.stderr.decode('utf-8', 'replace').strip()[-300:]}")
        return r.stdout

    def start(self, arc, extra, args, env):
        def send(fill):
            with tempfile.TemporaryFile() as f:
                f.write(UNTAR)
                fill(f)
                f.seek(0)
                self.call([self.py, "-c", BOOT, self.work], stdin=f)
        with open(arc, "rb") as a:
            send(lambda f: shutil.copyfileobj(a, f))
        if extra:  # a resume: the earlier run's directory, as the mirror holds it
            send(lambda f: write_tar(extra, f))
        # the named variables go through stdin: never on a command line, never into a file
        out = self.call([self.py, self.tool + "nnremote.py", "_start", "--work", self.work, *args],
                        data=json.dumps(env).encode())
        return {"pid": json.loads(out.decode("utf-8", "replace").strip().splitlines()[-1])["pid"]}

    def pull(self, last=False):
        with tempfile.TemporaryFile() as f:
            self.call([self.py, self.tool + "nnremote.py", "_pack", "--work", self.work, "--id", self.id,
                       "--newer", f"{self.newer:.3f}"] + (["--sums"] if last else []), out=f)
            f.seek(0)
            state = extract(f, self.d)
        if expctl.is_num(state.get("now")):
            self.newer = state["now"] - 5  # overlap: a file written while the pack ran is sent again
        return state

    def again(self, state):
        self.newer = 0.0  # a file changed without a newer date (copied with its old one, clock set back): take all
        return self.pull(last=True)

    def stop(self, kill=False):
        self.call([self.py, self.tool + "expctl.py", "--root", self.work, "stop", self.id]
                  + (["--kill-after", "1s"] if kill else []))

    def kill(self):
        self.stop(kill=True)

    def teardown(self, state):
        self.call([self.py, "-c", BOOT, self.work], data=b"import shutil;shutil.rmtree(sys.argv[1])\n")
        return f"removed {self.work} on the remote machine"


class HfJobs:
    """Hugging Face Jobs through the `hf` CLI: a rented GPU job with a provider-side time limit. Code, results and
    the stop request travel through one prefix of a storage bucket the user owns."""

    def __init__(self, st, d, man):
        self.tgt = st["targets"][man["remote"]["target"]]
        self.d, self.man, self.id = d, man, man["run_id"]
        self.hf = [str(x) for x in self.tgt.get("hf") or ["hf"]]
        self.bucket = str(self.tgt["bucket"]).strip("/")
        self.prefix = f"{self.bucket}/{self.id}"
        self.where = f"hf://buckets/{self.prefix}"

    def call(self, *args, timeout=3600):
        r = subprocess.run(self.hf + list(args), stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8",
                           errors="replace", timeout=timeout, **NOWIN)
        if r.returncode != 0:
            raise Transport(f"hf {' '.join(args[:2])} failed (exit {r.returncode}): "
                            f"{(r.stderr or r.stdout).strip()[-300:]}")
        return r.stdout

    def start(self, arc, extra, args, env):
        stage = Path(tempfile.mkdtemp(prefix="nnremote-"))
        try:
            with tarfile.open(arc, "r:gz") as tar:  # the kit's own archive, checked against the manifest's hash
                tar.extractall(stage / "code", **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
            for rel, src in extra.items():
                dest = stage / "code" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
            (stage / "out").mkdir()
            (stage / "out" / "remote-started.json").write_text(json.dumps({"ts": time.time()}), encoding="utf-8")
            (stage / "out" / SUMS).write_text("{}", encoding="utf-8")  # there from the start: the last pull reads it
            self.call("buckets", "sync", str(stage), f"hf://buckets/{self.prefix}")
        finally:
            shutil.rmtree(stage, ignore_errors=True)
        mount, py = f"/nnout/{self.id}", str(self.tgt.get("python") or "python")
        cmd = ["jobs", "run", "-d", "--flavor", str(self.tgt["flavor"]),
               "--timeout", f'{max(1, math.ceil(self.man["remote"]["hours"] * 60))}m',  # the provider ends the job
               "-l", f"kit_run={self.id}", "-v", f"hf://buckets/{self.bucket}:/nnout"]
        for name in env:  # -s NAME: the CLI reads the value from this process's environment
            cmd += ["-s", name]
        cmd += [str(self.tgt["image"]), py, f"{mount}/code/{KIT_REL}/nnremote.py", "_run", "--src", f"{mount}/code",
                "--work", "/work", "--out", f"{mount}/out", "--every", str(self.tgt.get("copy_every_s") or 30), *args]
        self.unsure = True  # from here on a job may exist even if its id never reaches us
        try:
            out = self.call(*cmd)
        except Transport:
            self.unsure = False  # the CLI reported a failure: nothing was started
            raise
        ids = re.findall(r"\b[0-9a-f]{24}\b", out) or out.split()
        if not ids:
            raise Transport(f"hf jobs run printed no job id; look for a job labelled kit_run={self.id}")
        self.unsure = False
        return {"job": ids[-1]}

    def pull(self, last=False):
        skip = sum((["--exclude", n] for n in LOCAL_ONLY + ("*.part", SUMS)), [])
        self.call("buckets", "sync", f"hf://buckets/{self.prefix}/out", str(self.d), *skip)
        m = re.search(r'"stage"\s*:\s*"(\w+)"', self.call("jobs", "inspect", self.man["remote"]["handle"]["job"]))
        stage = m.group(1).upper() if m else "UNKNOWN"
        state = {"alive": stage not in ENDED, "stage": stage}
        if last:  # the sync passes over a file of the same size that is not newer by its date: compare content
            self.call("buckets", "cp", f"hf://buckets/{self.prefix}/out/{SUMS}", str(self.d / SUMS))
            state["sums"] = json.loads((self.d / SUMS).read_text(encoding="utf-8"))
            if not isinstance(state["sums"], dict):
                raise ValueError(f"{SUMS} from the result store is not a JSON object")
        return state

    def again(self, state):
        """Fetch by itself every listed file that the mirror lacks or holds with other content. A job without an
        exit record was cut off, perhaps between a copy and its entry in the list: there the fetched copy counts."""
        cut = not (self.d / "remote-exit.json").exists()
        for name, sha in list(state["sums"].items()):
            p = self.d.joinpath(*name.split("/"))
            if safe(name) and not (p.is_file() and digest(p) == sha):
                p.parent.mkdir(parents=True, exist_ok=True)
                part = p.with_name(p.name + ".part")  # a download that breaks off leaves the older copy whole
                self.call("buckets", "cp", f"hf://buckets/{self.prefix}/out/{name}", str(part))
                os.replace(part, p)
                if cut:
                    state["sums"][name] = digest(p)
        return state

    def stop(self):
        self.call("buckets", "cp", str(self.d / "stop.json"), f"hf://buckets/{self.prefix}/ctl/stop.json")

    def kill(self):
        self.call("jobs", "cancel", self.man["remote"]["handle"]["job"])

    def teardown(self, state):
        self.call("buckets", "rm", f"{self.prefix}/", "--recursive")
        return f"removed hf://buckets/{self.prefix}/"


DRIVERS = {"ssh": Ssh, "hfjobs": HfJobs}
NEEDS = {"ssh": ("exec",), "hfjobs": ("flavor", "image", "bucket")}


# ---------------------------------------------------------------- the local controller of one remote run

def spawn_controller(root, d):
    log = open(d / "supervisor.log", "ab")
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--root", str(root), "_control", str(d)],
                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, cwd=str(root), close_fds=True,
                     **DETACH)


def start_run(root, cfg, st, *, name, target, cmd, hours, retries, seed=None, note=None, tags=None, resume_of=None,
              allow_code_change=False):
    """Check everything, reserve the money, create the local run directory and start its controller."""
    tgt = st["targets"].get(target)
    if not isinstance(tgt, dict) or tgt.get("type") not in DRIVERS:
        raise Refuse(f'no usable target "{target}": define it under "remote" -> "targets" in {expctl.CONFIG_REL} '
                     f'(types: {", ".join(DRIVERS)})')
    lack = [k for k in NEEDS[tgt["type"]] if not tgt.get(k)]
    if lack:
        raise Refuse(f'target "{target}" lacks {", ".join(lack)}')
    if hours is not None and hours <= 0:
        raise Refuse("--hours must be more than zero")
    missing = [n for n in st["env"] if n not in os.environ]
    if missing:
        raise Refuse(f"remote.env names {', '.join(missing)}, which this environment does not set")
    py = str(tgt.get("python") or ("python" if tgt["type"] == "hfjobs" else "python3"))
    cmd = [py if c == "{python}" else str(c) for c in cmd]
    rate, price_note = hourly_rate(target, tgt, st)
    parent = (expctl.read_json(resume_of / "manifest.json") or {}) if resume_of else {}
    was = (parent.get("snapshot") or {}).get("source_hash")
    extra = below(root, cfg, expctl.rel_to(root, resume_of), run=True) if resume_of else {}
    kept = resume_of / BUNDLE if resume_of and not allow_code_change else None
    sha = digest(kept) if kept and was and kept.is_file() else None
    if sha and sha == (parent.get("remote") or {}).get("bundle_sha256"):
        # The earlier run's archive is there until its controller has finished: the automatic resume after a
        # preemption sends the code that run was launched with, whatever the working tree holds by now.
        members, snap = None, parent["snapshot"]
        sent = {"sent_files": parent["remote"].get("sent_files"), "not_sent": parent["remote"].get("not_sent"),
                "bundle_sha256": sha}
        fits(st, extra, {BUNDLE: kept})
    else:
        kept, snap = None, {"mode": "remote", **expctl.provenance(root, cfg)[2]}
        if was and was != snap["source_hash"] and not allow_code_change:
            raise Refuse(expctl.changed_source(resume_of.name, was, snap["source_hash"], "nnremote.py"))
        members = bundle(root, cfg, st)  # refuses before anything is reserved
        fits(st, members, extra)
        sent = {"sent_files": len(members), "not_sent": [f for f in held_back(root, cfg) if f not in members]}
    rdir = expctl.runs_root(root, cfg)
    rdir.mkdir(parents=True, exist_ok=True)
    if rate > 0 and not ledger_path(root).exists() and any(
            ((expctl.read_json(m) or {}).get("remote") or {}).get("reserved_usd") for m in rdir.glob("*/manifest.json")):
        raise Refuse(f"{expctl.rel_to(root, ledger_path(root))} is gone although earlier paid runs are recorded in "
                     f"{expctl.rel_to(root, rdir)}: without it the cap cannot count what was spent. Nothing paid "
                     f"starts until the user has restored the file, or created an empty one to start the count anew")
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{expctl.slug(name)}-{secrets.token_hex(2)}"
    d = rdir / run_id
    d.mkdir()
    try:
        if members is not None:  # packed here, once: the tree may change before the controller sends it
            with open(d / BUNDLE, "wb") as f:
                write_tar(members, f)
            if expctl.provenance(root, cfg)[2]["source_hash"] != snap["source_hash"]:
                raise Refuse("the source changed while it was packed for sending, so the archive and the recorded "
                             "source hash may not agree; launch again")
            sent["bundle_sha256"] = digest(d / BUNDLE)
        usd = reserve(root, st, run_id, target, rate, hours)
    except BaseException:
        shutil.rmtree(d, ignore_errors=True)  # nothing was reserved or started, and an earlier run's archive is not in it
        raise
    t = time.time()
    deadline = t + hours * 3600 if hours else None
    man = {"schema": expctl.SCHEMA_MANIFEST, "run_id": run_id, "name": name, "note": note, "tags": dict(tags or {}),
           "created_at": expctl.iso(t), "created_ts": t, "host": socket.gethostname(),
           "platform": platform.platform(), "cmd": cmd, "cwd": str(root), "root": str(root), "seed": seed,
           "deadline": deadline, "deadline_at": expctl.iso(deadline), "snapshot": snap,
           "launched_by": "nnremote", "via": "remote",
           "remote": {"target": target, "type": tgt["type"], "hours": hours, "usd_per_hour": rate,
                      "reserved_usd": usd, "retries": int(retries or 0), **sent, "sent_env": list(st["env"])}}
    if resume_of:
        man["resume_of"], man["resume_of_source_hash"] = resume_of.name, was
    try:
        if kept:
            os.replace(kept, d / BUNDLE)
        expctl.write_json_atomic(d / "manifest.json", man)
        spawn_controller(root, d)
    except OSError:
        if usd:  # nothing was started: give the reservation back
            book(root, event="settle", run=run_id, usd=0.0, why="the run could not be created")
        raise
    return {"run_id": run_id, "dir": d, "usd": usd, "rate": rate, "note": price_note, "target": target,
            "type": tgt["type"], "hours": hours, "held": sent["not_sent"]}


def follow(drv, d, man, st, cfg, flag, t0):
    """Keep the mirror in step until the remote run has ended. Returns (why it was ended from outside, or None;
    the last remote state)."""
    rem = man["remote"]
    kill_after = float(cfg.get("kill_after_s") or 120)
    limit = rem["started_ts"] + rem["hours"] * 3600 if rem.get("hours") else None
    bad_since = stop_at = killed_at = None
    why, state, gone = None, {}, 0
    while True:
        time.sleep(st["poll_s"])
        t = time.time()
        try:
            state = drv.pull()
            bad_since = None
        except PULL_ERRORS as e:
            bad_since = bad_since or t
            if t - bad_since > st["unreachable_s"]:
                raise Unreachable(f"the remote side could not be reached for {int(t - bad_since)} s ({e})"[:300])
            continue
        if (d / "remote-exit.json").exists():
            return why, state
        if not state.get("alive"):
            gone += 1  # twice in a row: the exit record may be written between a pull and its liveness check
            if gone > 1:
                return why or (USED_UP if limit and t >= limit else GONE), state
            continue
        req = expctl.read_json(d / "stop.json")
        asked = flag["stop"] or (isinstance(req, dict) and expctl.is_num(req.get("requested_ts"))
                                 and req["requested_ts"] >= t0)
        if asked and stop_at is None:
            stop_at, why = t, "stop requested"
            if not isinstance(req, dict):
                expctl.write_json_atomic(d / "stop.json", {"requested_ts": t})
            quiet(drv.stop)
        if limit and t > limit + 60 and stop_at is None:  # neither the run's deadline nor the provider ended it
            stop_at, why = t - kill_after, USED_UP
        if stop_at is not None and t > stop_at + kill_after:
            quiet(drv.kill)
            killed_at = killed_at or t
            if t - killed_at > max(60.0, 4 * st["poll_s"]):
                return why, state  # it would not end: finish() reports what is left


def used_s(rem, drv, now):
    """Seconds the remote run has lasted at wall-clock time `now`. Never less than this controller's own count,
    so a clock that was set back during the run does not shorten what the ledger books."""
    if not rem.get("started_ts"):
        return 0.0
    return max(0.0, now - rem["started_ts"], time.monotonic() - getattr(drv, "since", float("inf")))


def finish(root, cfg, st, drv, d, man, why, state, flag):
    """Last pull, teardown of what this run created, the ledger entry, the exit record, and the automatic resume."""
    rem, t1 = man["remote"], time.time()
    note, rex, ended = None, None, True
    if rem.get("handle"):
        pulled = done = False
        try:
            state = drv.pull(last=True)
            done = complete(d, state)
            if not done:  # the mirror is not what the remote side lists: take those files again, then look once more
                state = drv.again(state)
                done = complete(d, state)
            pulled = True
        except PULL_ERRORS:
            pass
        rex = expctl.read_json(d / "remote-exit.json")
        rex = rex if isinstance(rex, dict) and "_error" not in rex else None
        if rex is not None and why in (GONE, USED_UP):
            why = None  # it ended by itself after all; its own exit record says how
        if state.get("alive") and rex is None:
            quiet(drv.kill)  # whatever else happens, a job that may cost money is not left running
        ended = pulled and (rex is not None or not state.get("alive"))
        if done:
            try:
                note = drv.teardown(state)
            except PULL_ERRORS as e:
                note = f"teardown failed ({e}); still there: {drv.where}"[:400]
        else:
            note = f"kept, because the last pull did not complete: {drv.where}"
    elif getattr(drv, "unsure", False):
        ended, note = False, f"a job may have been started without its id reaching this machine: {drv.where}"
    else:
        quiet(drv.teardown, state)
    used = used_s(rem, drv, t1) / 3600
    usd = round(min(rem.get("reserved_usd") or 0.0, used * (rem.get("usd_per_hour") or 0.0)), 4)
    if not ended:  # its end is not confirmed: the whole reservation stays booked (the provider's time limit bounds it)
        usd = rem.get("reserved_usd") or 0.0
    if rem.get("reserved_usd"):
        book(root, event="settle", run=man["run_id"], usd=usd, hours=round(used, 4), confirmed_end=ended)
    ex = {"ended_ts": t1, "ended_at": expctl.iso(t1), "duration_s": round(t1 - man["created_ts"], 1),
          "stopped_for": why or (rex or {}).get("stopped_for"), "remote": {"teardown": note, "usd": usd}}
    if not rem.get("handle"):
        ex.update(returncode=None, error=why or "the remote run could not be started")
    elif rex is not None:
        ex.update(returncode=rex.get("returncode"), signal=rex.get("signal"),
                  escalated_to_sigkill=rex.get("escalated_to_sigkill"))
    else:
        ex.update(returncode=-9, signal=9)
    if why == GONE and rem.get("retries", 0) > 0 and not flag["stop"]:
        try:
            ex["remote"]["resumed_as"] = start_run(
                root, cfg, st, name=man.get("name") or "run", target=rem["target"], cmd=man["cmd"],
                hours=rem.get("hours"), retries=rem["retries"] - 1, seed=man.get("seed"),
                note=f"automatic resume of {man['run_id']}", tags=man.get("tags"), resume_of=d)["run_id"]
        except Exception as e:  # noqa: BLE001  whatever keeps the resume from starting, this run's exit record is written
            ex["remote"]["not_resumed"] = str(e) if isinstance(e, Refuse) else f"{type(e).__name__}: {e}"[:300]
    quiet((d / BUNDLE).unlink)  # no resume took it along: a later one goes by the working tree
    expctl.write_json_atomic(d / "exit.json", ex)


def op_control(a):
    root = expctl.find_root(a.root)
    cfg = expctl.load_config(root)
    st = settings(cfg)
    d = Path(a.run_dir)
    man = expctl.read_json(d / "manifest.json")
    rem = man["remote"]
    t0, me = time.time(), os.getpid()
    expctl.write_json_atomic(d / "pid.json", {"pid": me, "pgid": me, "supervisor_pid": me, "started_at": t0,
                                              "proc_start": expctl.proc_start_time(me)})
    flag = {"stop": False}
    for name in ("SIGTERM", "SIGINT"):  # `expctl stop` signals this process where the platform has signals
        try:
            signal.signal(getattr(signal, name), lambda *_: flag.update(stop=True))
        except (ValueError, OSError, AttributeError):
            pass
    drv = DRIVERS[rem["type"]](st, d, man)
    why, state = None, {}
    try:
        if not rem.get("handle"):
            env = {n: os.environ[n] for n in st["env"] if n in os.environ}
            if digest(d / BUNDLE) != rem.get("bundle_sha256"):
                raise Refuse(f"{BUNDLE} is not the archive the launch packed, so nothing was sent")
            extra = below(root, cfg, expctl.rel_to(root, expctl.runs_root(root, cfg) / man["resume_of"]), run=True) \
                if man.get("resume_of") else {}
            rem["starting_ts"] = time.time()  # from here on something may exist remotely (see cmd_attach)
            expctl.write_json_atomic(d / "manifest.json", man)
            rem["handle"] = drv.start(d / BUNDLE, extra, run_args(man), env)
            rem["started_ts"] = time.time()
            expctl.write_json_atomic(d / "manifest.json", man)
        if rem.get("started_ts"):  # this controller's own count of the run's time starts where the clock puts it now
            drv.since = time.monotonic() - max(0.0, time.time() - rem["started_ts"])
        why, state = follow(drv, d, man, st, cfg, flag, t0)
    except Unreachable as e:
        # No exit record: the run shows as "lost", its reservation stays booked in full, and attach picks it up.
        print(f"nnremote: {e}. Nothing was torn down. When the target answers again: nnremote.py attach "
              f"{man['run_id']}", flush=True)
        return 1
    except Exception as e:  # noqa: BLE001  the mirror must say why, and finish() must still run
        why, state = f"controller error: {type(e).__name__}: {e}"[:300], {"alive": True}
    finish(root, cfg, st, drv, d, man, why, state, flag)
    return 0


# ---------------------------------------------------------------- remote side (runs on the target)

KIT_TMP = re.compile(r"\..+\.\d+\.[0-9a-f]{6}\.tmp")  # how runlog and expctl name their temporary files


def files_in(run_dir):
    """Paths of what lies below a run directory, without the kit's own temporary files (`.<name>.<pid>.<hex>.tmp`),
    which are gone a moment later. Not rglob: before Python 3.12 it raises when a folder vanishes while it lists,
    and a training script may remove one, an old checkpoint for instance, at any moment."""
    return [Path(top, f) for top, _, names in os.walk(run_dir) for f in names if not KIT_TMP.fullmatch(f)]


def copy_out(run_dir, out, seen, last=False):
    """Copy what changed in the run directory to the mounted result store, so a job that is cut off loses at most
    one interval, and keep the list of the copies' checksums there (SUMS) for the controller's last pull. The exit
    record goes only in the last round and after everything else: the controller reads it as "the store is
    complete" and then removes the store. Returns False when a file could not be copied."""
    ok = True
    for p in sorted(files_in(run_dir), key=lambda p: (p.name == "exit.json", p)):
        rel = p.relative_to(run_dir).as_posix()
        name = RENAME.get(rel, rel)
        if name is None or not p.is_file() or (rel == "exit.json" and not (last and ok)):
            continue
        try:
            s = p.stat()
            if seen.get(rel, ())[:2] == (s.st_size, s.st_mtime_ns):
                continue
            dest = out.joinpath(*name.split("/"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            part = dest.with_name(dest.name + ".part")
            sha = digest(p, part)
            os.replace(part, dest)
            if rel != "exit.json":
                sums = {RENAME.get(r, r): v[2] for r, v in seen.items()}
                sums[name] = sha
                part = out / (SUMS + ".part")
                part.write_text(json.dumps(sums), encoding="utf-8")
                os.replace(part, out / SUMS)
            seen[rel] = (s.st_size, s.st_mtime_ns, sha)
        except OSError:
            ok = False  # a file that vanished, or the store was busy: the next round copies it
    return ok


def op_run(a):
    """Run the command under the kit's own supervisor in <work>/<runs_dir>/<id>, as a local launch would."""
    work = Path(a.work).resolve()
    if a.src:  # the code arrived on a mount that may be read-only: work on a copy
        shutil.copytree(a.src, work, dirs_exist_ok=True)
    cfg = expctl.load_config(work)
    runs = expctl.runs_root(work, cfg)
    run_dir = runs / a.id
    run_dir.mkdir(parents=True, exist_ok=True)
    t = time.time()
    deadline = t + a.budget_s if a.budget_s else None
    expctl.write_json_atomic(run_dir / "manifest.json", {
        "schema": expctl.SCHEMA_MANIFEST, "run_id": a.id, "name": a.name, "created_at": expctl.iso(t),
        "created_ts": t, "host": socket.gethostname(), "platform": platform.platform(),
        "cmd": json.loads(bytes.fromhex(a.cmd).decode()), "cwd": str(work), "root": str(work), "seed": a.seed,
        "deadline": deadline, "deadline_at": expctl.iso(deadline), "grace_s": 60.0,
        "kill_after_s": float(cfg.get("kill_after_s") or 120), "launched_by": "nnremote", "via": "remote"})
    env = dict(os.environ, EXP_RUN_DIR=str(run_dir), EXP_RUN_ID=a.id, PYTHONUNBUFFERED="1",
               EXP_PROJECT_ROOT=str(work))
    for key, val in (("EXP_SOURCE_HASH", a.source_hash), ("EXP_SEED", a.seed),
                     ("EXP_DEADLINE", repr(deadline) if deadline else None),
                     ("EXP_RESUME_FROM", runs / a.resume_from if a.resume_from else None)):
        if val is not None:
            env[key] = str(val)
    sup = subprocess.Popen([sys.executable, str(work / KIT_REL / "expctl.py"), "_supervise", str(run_dir)],
                           env=env, cwd=str(work), stdin=subprocess.DEVNULL, **NOWIN)
    if os.name != "nt":  # a job that is being cancelled or has timed out: let the run save, then copy the result out
        signal.signal(signal.SIGTERM, lambda *_: sup.send_signal(signal.SIGTERM))
    out = Path(a.out) if a.out else None
    seen, stopped = {}, False
    while True:
        try:
            sup.wait(timeout=a.every)
            break
        except subprocess.TimeoutExpired:
            pass
        if out:
            copy_out(run_dir, out, seen)
            if not stopped and (out.parent / "ctl" / "stop.json").exists():
                stopped = True
                expctl.write_json_atomic(run_dir / "stop.json", {"requested_ts": time.time()})
                if os.name != "nt":
                    sup.send_signal(signal.SIGTERM)
    if out:  # the last round is retried: nothing comes after it, and the job's own disk goes with the job
        t_end = time.time() + 60
        while not copy_out(run_dir, out, seen, last=True) and time.time() < t_end:
            time.sleep(0.5)
    return 0


def op_start(a):
    """ssh-type target: start `_run` detached, with the named variables read from stdin, and return its pid."""
    work = Path(a.work).resolve()
    env = dict(os.environ)
    env.update({str(k): str(v) for k, v in json.load(sys.stdin).items()})
    log = open(work / "nnremote.log", "ab")
    argv = [sys.executable, str(Path(__file__).resolve()), "_run"] + a.raw[a.raw.index("_start") + 1:] \
        + ["--work", str(work)]  # absolute: the child runs in another directory than this command
    p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env,
                         cwd=str(work), close_fds=True, **DETACH)
    expctl.write_json_atomic(work / ".nnremote.json", {"pid": p.pid, "proc_start": expctl.proc_start_time(p.pid)})
    print(json.dumps({"ok": True, "pid": p.pid}))
    return 0


def op_pack(a):
    """ssh-type target: a tar stream of the run files changed since --newer, plus the remote state."""
    work = Path(a.work).resolve()
    run_dir = expctl.runs_root(work, expctl.load_config(work)) / a.id
    me = expctl.read_json(work / ".nnremote.json")
    me = me if isinstance(me, dict) else {}
    files, sums = {}, {}
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as tar:
        for p in sorted(files_in(run_dir)):
            rel = p.relative_to(run_dir).as_posix()
            name = RENAME.get(rel, rel)
            if name is None or not p.is_file():
                continue
            try:
                s = p.stat()
                if max(s.st_mtime, s.st_ctime) >= a.newer:  # ctime: a renamed or copied file keeps an old mtime
                    tar.add(str(p), arcname=name, recursive=False)
                files[name] = s.st_size
                if a.sums:  # the last pull: the controller compares content before it removes this directory
                    sums[name] = digest(p)
            except OSError:
                pass
        alive = bool(me.get("pid")) and expctl.pid_alive(me["pid"]) and expctl.same_process(me["pid"], me.get("proc_start"))
        blob = json.dumps({"now": time.time(), "alive": alive, "files": files, "sums": sums}).encode()
        info = tarfile.TarInfo(STATE)
        info.size = len(blob)
        tar.addfile(info, io.BytesIO(blob))
    return 0


# ---------------------------------------------------------------- commands

def report(root, cfg, st, r):
    d = r["dir"]
    for _ in range(50):
        if (d / "pid.json").exists() or (d / "exit.json").exists():
            break
        time.sleep(0.1)
    tool = f"{expctl.py_cmd(cfg)} {KIT_REL}/expctl.py"
    out = {"ok": True, "run_id": r["run_id"], "run_dir": expctl.rel_to(root, d), "target": r["target"],
           "type": r["type"], "hours": r["hours"], "usd_per_hour": r["rate"], "reserved_usd": r["usd"],
           "cap_usd": st["cap_usd"], "committed_usd": round(committed(ledger(root)), 4), "note": r["note"],
           # held at home because the name says credentials; remote.files sends one that is needed
           "not_sent": r.get("held") or [],
           "next": {"status": f"{tool} status --run {r['run_id']}",
                    "watch": f"{tool} watch {r['run_id']} --until terminal --max-time 25m",
                    "curve": f"{tool} curve {r['run_id']}", "stop": f"{tool} stop {r['run_id']}"}}
    print(json.dumps(expctl.clean(out), indent=1))
    return 0


def cmd_launch(a):
    root = expctl.find_root(a.root)
    cfg = expctl.load_config(root)
    st = settings(cfg)
    cmd = list(a.cmd or [])
    cmd = cmd[1:] if cmd[:1] == ["--"] else cmd
    if not cmd:
        raise Refuse("no command given; usage: nnremote.py launch --name NAME --on TARGET [--hours H] -- python train.py ...")
    tags = dict(kv.split("=", 1) for kv in (a.tag or []) if "=" in kv)
    return report(root, cfg, st, start_run(root, cfg, st, name=a.name, target=a.on, cmd=cmd, hours=a.hours,
                                           retries=a.retries, seed=a.seed, note=a.note, tags=tags))


def _mirror(a):
    root = expctl.find_root(a.root)
    cfg = expctl.load_config(root)
    d = expctl.resolve_run(root, cfg, a.run)
    man = expctl.read_json(d / "manifest.json")
    if not isinstance(man, dict) or not isinstance(man.get("remote"), dict):
        raise Refuse(f"{d.name} is not a remote run (for a local one: expctl.py resume)")
    return root, cfg, settings(cfg), d, man, expctl.load_run_safe(root, d, cfg, time.time())


def cmd_resume(a):
    root, cfg, st, d, man, run = _mirror(a)
    if run["state"] in expctl.ACTIVE_STATES:
        raise Refuse(f"{d.name} is {run['state']}; resume continues a run that has ended")
    rem = man["remote"]
    return report(root, cfg, st, start_run(
        root, cfg, st, name=man.get("name") or "run", target=a.on or rem["target"], cmd=man["cmd"],
        hours=a.hours if a.hours is not None else rem.get("hours"),
        retries=a.retries if a.retries is not None else rem.get("retries", 0), seed=man.get("seed"),
        note=f"resume of {d.name}", tags=man.get("tags"), resume_of=d, allow_code_change=a.allow_code_change))


def cmd_attach(a):
    root, _cfg, _st, d, man, _run = _mirror(a)
    rem = man["remote"]
    if (d / "exit.json").exists():
        raise Refuse(f"{d.name} has ended; there is nothing to attach to")
    pj = expctl.read_json(d / "pid.json") or {}
    if pj.get("pid") and expctl.pid_alive(pj["pid"]) and expctl.same_process(pj["pid"], pj.get("proc_start")):
        raise Refuse(f"the controller of {d.name} is still running")
    if rem.get("handle"):
        spawn_controller(root, d)
        print(json.dumps({"ok": True, "run_id": d.name, "attached": True}))
        return 0
    # The controller died before it recorded a remote job. If it had not begun to start one, nothing exists and
    # the reservation is released; otherwise something may exist, and the reservation stays booked in full.
    began = bool(rem.get("starting_ts"))
    usd = (rem.get("reserved_usd") or 0.0) if began else 0.0
    if rem.get("reserved_usd"):
        book(root, event="settle", run=d.name, usd=usd, confirmed_end=not began)
    t = time.time()
    why = "the controller died before the remote run was recorded" + (
        f"; check the target for leftovers of {d.name}" if began else "; nothing was started")
    quiet((d / BUNDLE).unlink)
    expctl.write_json_atomic(d / "exit.json", {"returncode": None, "error": why, "ended_ts": t,
                                               "ended_at": expctl.iso(t), "remote": {"usd": usd}})
    print(json.dumps({"ok": True, "run_id": d.name, "attached": False, "closed": why, "booked_usd": usd}))
    return 0


def cmd_status(a):
    root = expctl.find_root(a.root)
    st = settings(expctl.load_config(root))
    rows = ledger(root)
    settled = {r["run"] for r in rows if r.get("event") == "settle"}
    print(json.dumps(expctl.clean({
        "cap_usd": st["cap_usd"], "committed_usd": round(committed(rows), 4),
        "open": [{"run": r["run"], "target": r.get("target"), "reserved_usd": r["usd"]} for r in rows
                 if r.get("event") == "reserve" and r["run"] not in settled],
        "targets": {k: (v or {}).get("type") for k, v in st["targets"].items()},
        "sent_env": st["env"], "sent_files": st["files"],
        "ledger": expctl.rel_to(root, ledger_path(root))}), indent=1))
    return 0


def main(argv=None):
    raw = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="nnremote", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", help="project root (default: as expctl)")
    sub = ap.add_subparsers(dest="command")

    s = sub.add_parser("launch", help="start a run on a remote target (asks for approval in an agent session)")
    s.add_argument("--name", required=True)
    s.add_argument("--on", required=True, help='a target from "remote" -> "targets"')
    s.add_argument("--hours", type=float, help="time limit; required for a paid target (hours x price is reserved)")
    s.add_argument("--retries", type=int, default=2, help="automatic resumes after a preemption (default 2)")
    s.add_argument("--seed", type=int)
    s.add_argument("--note")
    s.add_argument("--tag", action="append", help="key=value (repeatable)")
    s.add_argument("cmd", nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_launch)

    s = sub.add_parser("resume", help="continue an ended remote run from the checkpoints in its local directory")
    s.add_argument("run")
    s.add_argument("--on")
    s.add_argument("--hours", type=float)
    s.add_argument("--retries", type=int)
    s.add_argument("--allow-code-change", action="store_true",
                   help="resume although the source differs from what the run was launched with")
    s.set_defaults(fn=cmd_resume)

    s = sub.add_parser("attach", help="restart the local controller of a remote run whose controller died")
    s.add_argument("run")
    s.set_defaults(fn=cmd_attach)

    s = sub.add_parser("status", help="spending cap, committed dollars and open remote runs")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("_control")
    s.add_argument("run_dir")
    s.set_defaults(fn=op_control)
    for name, fn in (("_run", op_run), ("_start", op_start)):
        s = sub.add_parser(name)
        s.add_argument("--id", required=True)
        s.add_argument("--name")
        s.add_argument("--work", required=True)
        s.add_argument("--src")
        s.add_argument("--out")
        s.add_argument("--cmd", required=True, help="hex of the JSON argument list")
        s.add_argument("--seed", type=int)
        s.add_argument("--budget-s", type=float, dest="budget_s")
        s.add_argument("--resume-from", dest="resume_from")
        s.add_argument("--source-hash", dest="source_hash")
        s.add_argument("--every", type=float, default=15.0)
        s.set_defaults(fn=fn)
    s = sub.add_parser("_pack")
    s.add_argument("--work", required=True)
    s.add_argument("--id", required=True)
    s.add_argument("--newer", type=float, default=0.0)
    s.add_argument("--sums", action="store_true")
    s.set_defaults(fn=op_pack)

    args = ap.parse_args(raw)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    args.raw = raw
    try:
        return args.fn(args) or 0
    except Refuse as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=1))
        return 3


if __name__ == "__main__":
    sys.exit(main())
