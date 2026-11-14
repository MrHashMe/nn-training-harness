#!/usr/bin/env python3
"""expctl - experiment control for the nn-training harness.

Stdlib only, Python 3.8+. Linux, macOS and native Windows. Windows differences: no tmux;
without the symlink privilege a snapshot links with directory junctions and file hard
links; a stop is requested through stop.json only (no signal), so a loop that does not
poll RunLog.should_stop() is killed after kill_after_s.

Commands
  status [--json | --brief] [--run RUN] [--no-gpu]
        Bounded, machine-readable overview: active runs (progress, heartbeat age,
        ETA), counts by state, top eligible runs with checkpoint links, recent
        failures with reasons, alerts, Optuna studies, GPUs and disk.
  launch --name NAME [options] -- CMD ...
        Start CMD as a detached background run with a run directory, provenance
        (source hash, git commit, uncommitted patch) and, by default, an
        immutable copy of the source tree to run from.
  stop RUN [--wait S]
        Graceful stop: writes stop.json and, except on Windows, sends SIGTERM to the
        launched process (RunLog turns either into a "save and exit" request), then
        kills the process tree after kill_after_s.
        Stopping a run needs the user's explicit approval.
  resume RUN [--deadline D]
        Continue an ended run as a new run: same command, seed, GPUs and tags, with
        EXP_RESUME_FROM set to the old run directory (RunLog.resume_from), from which
        the training script loads its last checkpoint. A run on a remote target is
        resumed with nnremote.py resume instead.
  watch [RUN|all] [--until terminal|any-terminal|alert] [--max-time 25m]
        Blocks and prints one compact JSON line per event (state change, new value of
        the configured metric, non-finite alert, periodic progress), then exits.
        Designed for Claude Code's Monitor tool (each line becomes an event).
  curve RUN [--keys a,b] [--points N] [--since-step S]
        Downsampled metric series + summary stats from RUN/metrics.jsonl.
  final-eval [--again REASON] [--which N] [-- ARGS ...]
        Run the final_eval_commands entry of the config, with ARGS appended, from the
        project root and without a shell. Single-use: every use is a row in the
        hash-chained receipt .claude/state/final-eval/receipt.jsonl, written before the
        command starts, and a journal entry; the output goes to a log beside the receipt.
        The rows are also kept in git's common folder, so they outlive a removed worktree.
        A further use is refused unless --again gives the reason, which is recorded.
        Running it needs the user's explicit approval.
  hash  Source hash of the working tree (tracked + untracked, not ignored).
  env [--python PATH]
        Environment report (OS/WSL, GPUs, driver, disk, tools, git) and, with
        --python, the framework/package versions of that interpreter.

RUN is a run id, a unique prefix/suffix of one, or "latest".
Run-directory contract (files under <runs_dir>/<run_id>/):
  manifest.json  launch provenance (expctl) or minimal manifest (RunLog)
  pid.json       child pid / process-group / start time (supervisor)
  stdout.log     combined stdout+stderr of the run
  heartbeat.json liveness + latest metrics + best/last checkpoint (RunLog)
  metrics.jsonl  append-only metric events (RunLog)
  env.json / config.json  environment and resolved config (RunLog)
  result.json    authoritative final state (RunLog.finish)
  exit.json      process exit code / signal (supervisor)
  stop.json      stop request: {requested_ts[, kill_after_s]} (expctl stop)
"""
from __future__ import annotations

import argparse
import hashlib
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
import stat
import subprocess
import sys
import time
from pathlib import Path

SCHEMA_STATUS = "expctl.status/v1"
SCHEMA_MANIFEST = "expctl.manifest/v1"
CONFIG_REL = ".claude/nn-training.json"

DEFAULT_CONFIG = {
    "version": 1,
    "runs_dir": "runs",
    "journal": "experiments/JOURNAL.md",
    "metric": {"name": None, "direction": None, "select": "best"},
    "heartbeat_stale_seconds": 900,
    "min_free_disk_gb": 20,
    "kill_after_s": 120,
    "snapshot": {"mode": "copy", "max_file_mb": 50},
    "sealed_paths": [],
    "sealed_tokens": [],
    "frozen_paths": [],
    "final_eval_commands": [],
    "harness_paths": [
        ".claude/hooks/**",
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/nn-training.json",
        ".claude/skills/nn-training/**",
        ".claude/agents/**",
        ".mcp.json",
        "CLAUDE.md",
        "AGENTS.md",
        ".codex/**",
        ".cursor/**",
        ".agents/skills/nn-training/**",
        ".claude/state/remote-ledger.jsonl",
        ".claude/state/final-eval/**",
    ],
    "python": None,
    "external_jobs": [],
    "optuna": {"storage": None, "studies": []},
    "limits": {"top_k": 5, "failures": 5, "active": 10, "recent": 5, "alerts": 12},
}

ACTIVE_STATES = ("starting", "running", "stalled")
TERMINAL_STATES = ("completed", "failed", "pruned", "timeout", "interrupted", "incomplete", "lost")
ALL_STATES = ACTIVE_STATES + TERMINAL_STATES + ("unknown",)
STATE_ALIASES = {
    "complete": "completed", "success": "completed", "succeeded": "completed", "done": "completed",
    "fail": "failed", "error": "failed", "crashed": "failed",
    "prune": "pruned", "deadline": "timeout", "timed_out": "timeout",
    "killed": "interrupted", "stopped": "interrupted", "cancelled": "interrupted", "canceled": "interrupted",
}
SOURCE_EXTS = {
    ".py", ".pyi", ".pyx", ".pxd", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".json", ".sh", ".txt",
    ".md", ".ipynb", ".cu", ".cuh", ".cpp", ".cc", ".c", ".h", ".hpp", ".jinja", ".j2", ".lock",
}
NONGIT_SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".ipynb_checkpoints", "wandb", "mlruns", "lightning_logs",
    ".trackio", "data", "datasets", "checkpoints", "ckpt", "ckpts", "outputs", "logs", ".cache",
}
NOLINK_IGNORED = ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints")


# ----------------------------------------------------------------------------- utilities

def now() -> float:
    return time.time()


def iso(ts):
    if not isinstance(ts, (int, float)):
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts))


def is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def finite(v) -> bool:
    return is_num(v) and math.isfinite(v)


def clean(obj):
    """Make an object strict-JSON safe (non-finite floats become strings)."""
    if isinstance(obj, float):
        if math.isnan(obj):
            return "nan"
        if math.isinf(obj):
            return "inf" if obj > 0 else "-inf"
        return obj
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    return obj


def fmt_secs(s):
    if not is_num(s) or not math.isfinite(s):
        return "?"
    s = int(max(0, s))
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if d:
        return f"{d}d{h}h"
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def fmt_val(v):
    if isinstance(v, float):
        if not math.isfinite(v):
            return str(v)
        return f"{v:.4g}"
    return str(v)


def py_cmd(cfg):
    """The interpreter to show in suggested commands: the one the installer recorded, else the platform's usual name."""
    p = (cfg or {}).get("python") or ("python" if os.name == "nt" else "python3")
    return f'"{p}"' if " " in p else p


def read_json(path):
    for attempt in (1, 2, 3):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError, UnicodeDecodeError) as e:
            # Windows refuses the open in the instant in which the writer replaces the file. With a single look a
            # live run read as stalled for that one call, when the file was its heartbeat
            if not isinstance(e, PermissionError) or attempt == 3:
                return {"_error": f"{type(e).__name__}: {e}"}
            time.sleep(0.02)


def write_json_atomic(path, obj):
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(3)}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, default=str)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        for attempt in range(40):
            try:
                return os.replace(tmp, path)
            except PermissionError:  # Windows: a reader has the target open for a moment (a status poll, a virus scan)
                if attempt == 39:
                    raise
                time.sleep(0.05)
    except BaseException:  # the rename was refused to the end, or the write failed (a full disk): leave no temporary file
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def find_root(explicit=None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    p = Path.cwd().resolve()
    for q in [p, *p.parents]:
        if (q / CONFIG_REL).is_file():
            return q
    for q in [p, *p.parents]:
        if (q / ".git").exists():
            return q
    return p


def load_config(root: Path):
    raw = read_json(root / CONFIG_REL)
    if isinstance(raw, dict) and "_error" in raw:
        cfg = deep_merge(DEFAULT_CONFIG, {})
        cfg["_config_error"] = raw["_error"]
        return cfg
    return deep_merge(DEFAULT_CONFIG, raw or {})


def rel_to(root: Path, p) -> str:
    try:
        return Path(p).resolve().relative_to(root).as_posix()
    except (ValueError, OSError):
        return str(p)


def tail_bytes(path, n=65536) -> str:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - n))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def ledger_rows(path: Path):
    """(rows, chain_ok) of a JSON-lines record in which every row names the SHA-256 of the line before it, so an
    edited history shows. The loop's ledger and the receipt of the final evaluation are such records."""
    rows, ok, prev = [], True, ""
    if path.is_file():
        for raw in path.read_bytes().splitlines():
            try:
                row = json.loads(raw)
            except ValueError:
                row = None
            if not isinstance(row, dict):
                ok = False
                continue
            ok = ok and row.get("prev") == prev
            prev = hashlib.sha256(raw).hexdigest()
            rows.append(row)
    return rows, ok


_REASON_PATTERNS = [
    (re.compile(r"(CUDA out of memory|OutOfMemoryError|out of memory)", re.I), "out of memory"),
    (re.compile(r"Segmentation fault|core dumped", re.I), "segmentation fault"),
    (re.compile(r"NCCL (error|timeout)|Watchdog caught collective operation timeout", re.I), "NCCL/collective error"),
    (re.compile(r"No space left on device", re.I), "disk full"),
    (re.compile(r"^Killed\s*$", re.M), "killed (often host OOM killer)"),
]


def log_reason(log_path) -> str | None:
    """Best-effort one-line failure reason from the end of a log (an observation, not a diagnosis)."""
    text = tail_bytes(log_path)
    if not text:
        return None
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    if "Traceback (most recent call last)" in text:
        idx = text.rfind("Traceback (most recent call last)")
        after = [ln for ln in text[idx:].splitlines() if ln.strip()]
        for ln in reversed(after):
            s = ln.strip()
            if not s.startswith(("File ", "^", "~")) and not ln.startswith("    "):
                return s[:300]
    for rx, label in _REASON_PATTERNS:
        if rx.search(text):
            return label
    return lines[-1][:300] if lines else None


# ----------------------------------------------------------------------------- processes

def pid_alive(pid) -> bool:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        import psutil  # type: ignore

        try:
            p = psutil.Process(pid)
            return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    except ImportError:
        pass
    if os.name == "nt":
        return _win_pid_alive(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    try:
        with open(f"/proc/{pid}/stat", "r") as f:
            data = f.read()
        if data[data.rfind(")") + 2:].split()[0] == "Z":
            return False
    except (OSError, IndexError):
        pass
    return True


def _win_pid_alive(pid: int) -> bool:
    try:
        import ctypes

        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    except Exception:
        return False


def _win_proc_start(pid):
    """Creation time of a Windows process as the system records it (epoch seconds), or None."""
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return None
        t = [wintypes.FILETIME() for _ in range(4)]  # creation, exit, kernel, user
        ok = k32.GetProcessTimes(h, *[ctypes.byref(x) for x in t])
        k32.CloseHandle(h)
        # a FILETIME counts 100 ns from 1601-01-01
        return ((t[0].dwHighDateTime << 32) | t[0].dwLowDateTime) / 1e7 - 11644473600 if ok else None
    except Exception:
        return None


def proc_start_time(pid):
    """Process start time (epoch seconds) for PID-reuse detection, or None if unavailable."""
    try:
        import psutil  # type: ignore

        return psutil.Process(int(pid)).create_time()
    except Exception:
        pass
    if os.name == "nt":  # without psutil a pid that had gone to another process counted as the run's
        return _win_proc_start(pid)
    try:
        with open(f"/proc/{int(pid)}/stat", "r") as f:
            data = f.read()
        ticks = int(data[data.rfind(")") + 2:].split()[19])
        btime = None
        with open("/proc/stat", "r") as f:
            for line in f:
                if line.startswith("btime"):
                    btime = int(line.split()[1])
                    break
        if btime is None:
            return None
        return btime + ticks / os.sysconf("SC_CLK_TCK")
    except Exception:
        return None


def same_process(pid, expected_start) -> bool:
    if not is_num(expected_start):
        return True
    actual = proc_start_time(pid)
    if actual is None:
        return True
    return abs(actual - expected_start) < 5.0


def proc_parent(pid):
    try:
        import psutil  # type: ignore

        return psutil.Process(int(pid)).ppid()
    except Exception:
        pass
    try:
        with open(f"/proc/{int(pid)}/stat", "r") as f:
            data = f.read()
        return int(data[data.rfind(")") + 2:].split()[1])
    except Exception:
        return None


def ancestors(pid, depth=25):
    out, cur = [], pid
    for _ in range(depth):
        cur = proc_parent(cur)
        if not cur or cur <= 1 or cur in out:
            break
        out.append(cur)
    return out


def signal_leader(pid, sig) -> bool:
    """Signal only the launched process. Graceful stops must not hit the whole process group: PyTorch
    DataLoader workers die on a SIGTERM that does not come from their parent, which turns a graceful stop into
    a crash without a final checkpoint. torchrun forwards SIGTERM to its ranks itself."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if os.name == "nt":
        # Windows has no signal that asks one process to stop: a console control event reaches a whole console, and
        # only from a process attached to it. The stop request is stop.json; signal_group() is the kill.
        return False
    try:
        os.kill(pid, sig)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def signal_group(pid, sig) -> bool:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    try:
        if os.name == "nt":
            if sig == getattr(signal, "SIGKILL", None) or sig == signal.SIGTERM:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=30)
                return True
            return False
        try:
            os.killpg(pid, sig)
        except (ProcessLookupError, PermissionError):
            os.kill(pid, sig)
        return True
    except (ProcessLookupError, PermissionError, OSError, subprocess.SubprocessError):
        return False


# ----------------------------------------------------------------------------- system info

def gpu_info(timeout=6):
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    q = "index,uuid,name,utilization.gpu,memory.used,memory.total,temperature.gpu"
    try:
        r = subprocess.run([exe, f"--query-gpu={q}", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return {"error": f"nvidia-smi failed: {e}"}
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout).strip()[:200]}
    gpus, uuid_to_idx = [], {}

    def num(x):
        try:
            return float(x) if "." in x else int(x)
        except ValueError:
            return None

    for line in r.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        idx = num(parts[0])
        uuid_to_idx[parts[1]] = idx
        gpus.append({"index": idx, "name": parts[2], "util_pct": num(parts[3]), "mem_used_mb": num(parts[4]),
                     "mem_total_mb": num(parts[5]), "temp_c": num(parts[6]), "pids": []})
    try:
        r2 = subprocess.run([exe, "--query-compute-apps=gpu_uuid,pid,used_memory", "--format=csv,noheader,nounits"],
                            capture_output=True, text=True, timeout=timeout)
        for line in r2.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2 and parts[0] in uuid_to_idx:
                for g in gpus:
                    if g["index"] == uuid_to_idx[parts[0]]:
                        try:
                            g["pids"].append(int(parts[1]))
                        except ValueError:
                            pass
    except (OSError, subprocess.SubprocessError):
        pass
    return gpus


def disk_free(path):
    try:
        p = Path(path)
        while not p.exists() and p != p.parent:
            p = p.parent
        u = shutil.disk_usage(str(p))
        return round(u.free / 1e9, 1), round(100.0 * u.free / u.total, 1)
    except OSError:
        return None, None


def run_git(root, *args, timeout=30, text=False):
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace") if text else r.stdout


# ----------------------------------------------------------------------------- path patterns

def _glob_re(pat: str):
    pat = pat.strip().replace("\\", "/")
    if pat.startswith("./"):
        pat = pat[2:]
    out, i = "", 0
    while i < len(pat):
        c = pat[i]
        if c == "*":
            if pat.startswith("**/", i):
                out, i = out + "(?:.*/)?", i + 3
                continue
            if pat.startswith("**", i):
                out, i = out + ".*", i + 2
                continue
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        else:
            out += re.escape(c)
        i += 1
    return re.compile("^" + out + "$")


def path_matches(rel: str, patterns):
    """First pattern matching a repo-relative path (a pattern 'a/b' or 'a/b/**' also covers everything below a/b)."""
    rel = (rel or "").replace("\\", "/").strip("/")
    if not rel:
        return None
    for p in patterns or []:
        p2 = os.path.expanduser(str(p).strip()).replace("\\", "/")
        if p2.startswith("./"):
            p2 = p2[2:]
        base = p2[:-3] if p2.endswith("/**") else p2.rstrip("/")
        if _glob_re(p2).match(rel) or rel == base or (
                not any(ch in base for ch in "*?[") and rel.startswith(base + "/")):
            return p
    return None


def sealed_inside(rel: str, patterns, target=None) -> bool:
    """True if some sealed pattern names a path strictly below directory `rel`. A pattern whose wildcard stands at
    or above that directory (**/test/**, data/*/test/x.csv) is answered from the names below `target`, the
    directory on disk; without a target the answer for such a pattern is True."""
    rel, wild = rel.strip("/"), []
    for p in patterns or []:
        p2 = str(p).strip().replace("\\", "/")
        p2 = p2[2:] if p2.startswith("./") else p2
        head = re.split(r"[*?\[]", p2)[0]
        if head.rstrip("/").startswith(rel + "/"):
            return True
        base = head.rpartition("/")[0]  # the folder that holds every match of a pattern with a wildcard
        if head != p2 and (not base or (rel + "/").startswith(base + "/")) and (
                "**" in p2 or p2.count("/") > rel.count("/")):
            wild.append(p)
    return bool(wild) and (target is None or _named_below(target, rel, wild))


def _named_below(target, rel: str, patterns, secs=20.0) -> bool:
    """Whether a file or folder below the directory `target` (repo-relative: `rel`) matches a pattern; links to
    folders are followed. True as well where the look goes 40 folders deep (a link that leads back up) or takes
    longer than `secs`: the snapshot then links the folder's children one by one, which costs time, never data."""
    end = time.time() + secs
    for d, dirs, files in os.walk(target, followlinks=True):
        sub = os.path.relpath(d, target).replace("\\", "/")
        pre = rel if sub == "." else f"{rel}/{sub}"
        if sub.count("/") >= 40 or time.time() > end or any(path_matches(f"{pre}/{n}", patterns) for n in dirs + files):
            return True
    return False


def optuna_storage_file(cfg):
    """Repo-relative path of a file-based Optuna storage from the config (sqlite or journal), else None."""
    spec = ((cfg.get("optuna") or {}).get("storage") or "").strip()
    path = None
    if spec.startswith("sqlite:///") and not spec.startswith("sqlite:////"):
        path = spec[len("sqlite:///"):]
    elif spec.startswith("journal:"):
        path = spec.split(":", 1)[1]
    if path and not os.path.isabs(path):
        return path.strip("/")
    return None


def excluded_from_provenance(rel: str, cfg) -> bool:
    """Bookkeeping and agent configuration, which are not experiment code: never hashed or copied into snapshots.
    The files of the other agents' ports count like .claude/ and CLAUDE.md, so an upgrade of the kit does not
    change a project's source hash."""
    r = rel.strip("/")
    if r.split("/")[0] in (".claude", ".codex", ".cursor", ".agents") or r in (
            "CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".mcp.json"):
        return True
    journal = (cfg.get("journal") or "").strip("/")
    if journal and r == journal:
        return True
    st = optuna_storage_file(cfg)
    if st and (r == st or r.startswith(st + "-") or r.startswith(st + ".")):
        return True
    return False


# ----------------------------------------------------------------------------- source provenance

def source_files(root: Path, cfg):
    """Files that define the experiment: tracked (including submodule files) + untracked-not-ignored (git),
    else source-like files. Harness/bookkeeping files (.claude/, CLAUDE.md, the journal, the Optuna storage
    file) are excluded so that journal edits or new trials do not change the source hash."""
    runs_rel = cfg["runs_dir"]
    runs_prefix = runs_rel.strip("/") + "/"
    out = run_git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if out is not None:
        names = {p for p in out.decode("utf-8", "surrogateescape").split("\0") if p}
        sub = run_git(root, "ls-files", "-z", "--cached", "--recurse-submodules")
        if sub:
            names |= {p for p in sub.decode("utf-8", "surrogateescape").split("\0") if p}
        res = []
        for rel in sorted(names):
            if rel == runs_rel.strip("/") or rel.startswith(runs_prefix) or excluded_from_provenance(rel, cfg):
                continue
            full = root / rel
            if full.is_symlink() or full.is_file():
                res.append(rel)
        return res, True
    res = []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        reld = "" if d == root else d.relative_to(root).as_posix()
        dirnames[:] = sorted(n for n in dirnames if n not in NONGIT_SKIP_DIRS and not n.startswith(".")
                             and (reld + "/" + n).strip("/") != runs_rel.strip("/"))
        for fn in sorted(filenames):
            rel = (reld + "/" + fn).strip("/")
            if Path(fn).suffix.lower() in SOURCE_EXTS and not excluded_from_provenance(rel, cfg):
                res.append(rel)
    return res, False


def hash_files(root: Path, files, max_bytes):
    h = hashlib.sha256()
    hashed, size_only = 0, []
    for rel in files:
        p = root / rel
        try:
            if p.is_symlink():
                h.update(b"L\0" + rel.encode("utf-8", "surrogateescape") + b"\0" + os.readlink(p).encode() + b"\0")
                continue
            size = p.stat().st_size
            if size > max_bytes:
                size_only.append(rel)
                h.update(b"S\0" + rel.encode("utf-8", "surrogateescape") + b"\0" + str(size).encode() + b"\0")
                continue
            fh = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    fh.update(chunk)
            h.update(b"F\0" + rel.encode("utf-8", "surrogateescape") + b"\0" + fh.hexdigest().encode() + b"\0")
            hashed += 1
        except OSError:
            size_only.append(rel)
    return h.hexdigest(), hashed, size_only


def provenance(root: Path, cfg):
    files, is_git = source_files(root, cfg)
    max_bytes = float(cfg["snapshot"].get("max_file_mb", 50)) * 1e6
    digest, hashed, size_only = hash_files(root, files, max_bytes)
    info = {"source_hash": digest, "files_hashed": hashed, "files_size_only": len(size_only),
            "size_only_examples": size_only[:10], "git": None}
    if is_git:
        head = run_git(root, "rev-parse", "HEAD", text=True)
        # every untracked file by its own name: a folder that holds nothing but the journal is not a change
        porcelain = run_git(root, "status", "--porcelain", "--untracked-files=all", text=True) or ""
        runs = cfg["runs_dir"].strip("/")  # "dirty" is about the files the hash covers: not the journal, not the runs
        dirty = [ln[3:] for ln in porcelain.splitlines() if ln.strip() and not any(
            p == runs or p.startswith(runs + "/") or excluded_from_provenance(p, cfg)
            for p in [ln[3:].split(" -> ")[-1].strip('"').rstrip("/")])]
        info["git"] = {"commit": head.strip() if head else None, "dirty": bool(dirty),
                       "dirty_count": len(dirty), "dirty_examples": dirty[:20]}
    return files, is_git, info


# File names that usually hold credentials. A snapshot links such a file instead of copying it, and a remote run
# receives one only when remote.files names it. (added_tokens.json and tokenizer files do not match.)
SECRETISH = re.compile(
    r"(?:^|/)(?:\.env(?:\.[^/]*)?|\.netrc|\.npmrc|\.pypirc|id_(?:rsa|dsa|ecdsa|ed25519)[^/]*|[^/]*\.(?:pem|key|p12|pfx)|"
    r"(?:[^/]*[-_.])?(?:credentials?|secrets?|token)(?:\.(?:json|ya?ml|toml|txt|ini|cfg))?|"
    r"service[-_]?account[^/]*\.json)$", re.I)


def make_snapshot(root: Path, run_dir: Path, files, is_git, cfg):
    """Copy source files into run_dir/src and symlink ignored/large paths (data, venvs, outputs)."""
    runs_rel = cfg["runs_dir"].strip("/")
    max_bytes = float(cfg["snapshot"].get("max_file_mb", 50)) * 1e6
    sealed = cfg.get("sealed_paths") or []
    src = run_dir / "src"
    src.mkdir(parents=True, exist_ok=False)
    copied, to_link, failures, kept_out = 0, [], [], []
    for rel in files:
        if path_matches(rel, sealed):
            kept_out.append(rel)
            continue
        s, d = root / rel, src / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        try:
            if s.is_symlink():
                os.symlink(os.readlink(s), d)
            elif s.stat().st_size > max_bytes or SECRETISH.search(rel):
                to_link.append(rel)  # too large, or named like a credential: the runs folder gets no second copy of it
            else:
                shutil.copy2(s, d)
                copied += 1
        except OSError as e:
            failures.append(f"{rel}: {e}")
    if is_git:
        out = run_git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory") or b""
        for rel in out.decode("utf-8", "surrogateescape").split("\0"):
            rel = rel.rstrip("/")
            if not rel or rel == runs_rel or rel.startswith(runs_rel + "/") or rel == ".git":
                continue
            if any(part in NOLINK_IGNORED for part in rel.split("/")) or rel.endswith((".pyc", ".pyo")):
                continue
            if excluded_from_provenance(rel, cfg):
                continue
            to_link.append(rel)
    else:
        for entry in sorted(root.iterdir()):
            name = entry.name
            if name in (runs_rel, ".git") or (src / name).exists() or excluded_from_provenance(name, cfg):
                continue
            to_link.append(name)
    linked = []
    for rel in sorted(set(to_link)):
        _link_tree(root / rel, src / rel, rel, linked, failures, sealed=sealed, kept_out=kept_out)
    return {"path": rel_to(root, src), "copied": copied, "linked": len(linked),
            "linked_examples": linked[:15], "sealed_kept_out": kept_out[:10], "sealed_kept_out_count": len(kept_out),
            "failures": failures[:10], "failure_count": len(failures)}


def _is_link(p) -> bool:
    """A symlink, or a Windows directory junction (which is_symlink() does not report)."""
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode) or getattr(st, "st_reparse_tag", 0) == 0xA0000003  # IO_REPARSE_TAG_MOUNT_POINT


def _link(target: Path, link: Path):
    """Symlink target at link. A Windows account without the symlink privilege gets a directory junction or a
    file hard link instead: neither needs a privilege, and deleting one leaves the target alone."""
    try:
        os.symlink(str(target), str(link), target_is_directory=target.is_dir())
    except OSError:
        if os.name != "nt":
            raise
        if target.is_dir():
            import _winapi

            _winapi.CreateJunction(str(target), str(link))
        else:
            os.link(str(target), str(link))


def _link_tree(target: Path, link: Path, rel: str, linked, failures, depth=0, sealed=(), kept_out=None, real=None):
    """Link target at link; if link is already a real directory (tracked files inside an ignored dir), or
    a sealed path lies below it, create a real directory and link the children instead (sealed ones are left out,
    so training runs cannot reach the test split even through a broad glob). `real` is the place in the project
    that a link on the way led to (data/latest -> data/2026-01): the target is judged by that name as well."""
    if _is_link(link):  # never descend through a link: its children are the real files
        return
    if sealed and _is_link(target):
        top, to = Path(os.path.realpath(target.parents[rel.count("/")])), Path(os.path.realpath(target))
        if to == top or to in top.parents:
            failures.append(f"link {rel}: it leads to the project folder or above it, so it would bring the sealed "
                            f"paths into the snapshot under another name")
            return
        real = to.relative_to(top).as_posix() if top in to.parents else None
    names = [rel] + ([real] if real else [])
    if any(path_matches(n, sealed) for n in names):
        if kept_out is not None:
            kept_out.append(rel)
        return
    inside = target.is_dir() and not link.exists() and any(sealed_inside(n, sealed, target) for n in names)
    if inside and depth >= 12:  # never linked whole: that would bring the sealed paths along
        failures.append(f"link {rel}: sealed paths lie below it, more than 12 folders deep in a git-ignored folder")
        return
    if inside:
        try:
            link.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            failures.append(f"mkdir {rel}: {e}")
            return
    if link.exists():
        if link.is_dir() and target.is_dir() and (inside or depth < 6):
            try:
                children = sorted(target.iterdir())
            except OSError as e:
                failures.append(f"list {rel}: {e}")
                return
            for child in children:
                if child.name in NOLINK_IGNORED:
                    continue
                _link_tree(child, link / child.name, f"{rel}/{child.name}", linked, failures, depth + 1,
                           sealed=sealed, kept_out=kept_out, real=real and f"{real}/{child.name}")
        return
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
        _link(target, link)
        linked.append(rel)
    except OSError as e:
        failures.append(f"link {rel}: {e}")


# ----------------------------------------------------------------------------- run discovery

def normalize_state(s):
    s = str(s or "").strip().lower()
    s = STATE_ALIASES.get(s, s)
    return s if s in ALL_STATES else "unknown"


def runs_root(root: Path, cfg) -> Path:
    return (root / cfg["runs_dir"]).resolve()


def list_run_dirs(rdir: Path, limit=2000):
    if not rdir.is_dir():
        return []
    dirs = []
    for d in rdir.iterdir():
        if d.is_dir() and not d.name.startswith((".", "_")):
            try:
                dirs.append((d.stat().st_mtime, d))
            except OSError:
                pass
    dirs.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in dirs[:limit]]


def metric_for(run_files, cfg):
    """(value, source, ckpt, step, why_not) for the configured selection metric, without silent fallbacks."""
    name = (cfg.get("metric") or {}).get("name")
    select = (cfg.get("metric") or {}).get("select", "best")
    if not name:
        return None, None, None, None, "metric.name not configured"
    res = run_files.get("result") if isinstance(run_files.get("result"), dict) else {}
    src = res or (run_files.get("heartbeat") if isinstance(run_files.get("heartbeat"), dict) else {}) or {}
    if select == "best":
        b = src.get("best") or {}
        if b and b.get("metric") in (None, name) and is_num(b.get("value")):
            return float(b["value"]), "best", b.get("ckpt"), b.get("step"), None
        return None, None, None, None, f"no best value recorded for {name}"
    m = src.get("metrics") or src.get("latest") or {}
    if is_num(m.get(name)):
        last = src.get("last_ckpt") or {}
        return float(m[name]), "final", last.get("path"), src.get("step") or src.get("final_step"), None
    return None, None, None, None, f"final value of {name} missing"


def _dict_or_none(x, name, errors):
    if x is None:
        return None
    if isinstance(x, dict):
        if "_error" in x:
            errors.append(f"{name}: {x['_error']}")
            return None
        return x
    errors.append(f"{name}: expected a JSON object, got {type(x).__name__}")
    return None


def load_run(root: Path, d: Path, cfg, t: float):
    errors = []
    man = _dict_or_none(read_json(d / "manifest.json"), "manifest", errors) or {}
    pidj = _dict_or_none(read_json(d / "pid.json"), "pid", errors) or {}
    hb = _dict_or_none(read_json(d / "heartbeat.json"), "heartbeat", errors)
    shb = _dict_or_none(read_json(d / "study_heartbeat.json"), "study_heartbeat", errors)
    stale = float(cfg.get("heartbeat_stale_seconds") or 900)
    pid = pidj.get("pid") or man.get("pid")
    hb_ok = isinstance(hb, dict) and is_num(hb.get("ts"))
    hb_age = (t - hb["ts"]) if hb_ok else None
    # a study runner whose trials log to sibling directories: their heartbeats keep the runner alive
    study = isinstance(shb, dict) and is_num(shb.get("ts")) and (hb_age is None or t - shb["ts"] < hb_age)
    if study:
        hb_age = t - shb["ts"]
    alive = bool(pid) and pid_alive(pid) and same_process(pid, pidj.get("proc_start") or man.get("proc_start"))
    # (not for the mirror of a remote run: the pid in its heartbeat belongs to another machine)
    if not alive and hb_ok and hb_age is not None and hb_age <= stale and hb.get("pid") and hb.get("pid") != pid \
            and not man.get("remote") and pid_alive(hb["pid"]):
        # a later process (e.g. an in-place resume) owns this run directory now
        pid, alive = hb["pid"], True
    # The supervisor writes the exit record a moment after the process has gone, so while it is there the run has not
    # ended. Only where its start time shows that the pid is still the supervisor's: a pid is given out again
    sup = pidj.get("supervisor_pid")
    sup_start = proc_start_time(sup) if not alive and pid_alive(sup) else None
    ending = sup_start is not None and is_num(pidj.get("started_at")) and abs(sup_start - pidj["started_at"]) < 5
    # The records of the end are read after the looks at the processes: a process that is gone has written all it
    # ever will. Read before them, a run that wrote its result and ended between the two looks read as lost
    res = _dict_or_none(read_json(d / "result.json"), "result", errors)
    ex = _dict_or_none(read_json(d / "exit.json"), "exit", errors)
    for name, obj in (("heartbeat", hb), ("result", res)):
        if isinstance(obj, dict):
            for key in ("best", "last_ckpt", "latest", "metrics", "meta"):
                if obj.get(key) is not None and not isinstance(obj.get(key), dict):
                    errors.append(f"{name}.{key}: expected an object")
                    obj[key] = None
            if obj.get("nonfinite") is not None and not isinstance(obj.get("nonfinite"), list):
                obj["nonfinite"] = [str(obj.get("nonfinite"))]
    meta = {}
    for src_obj in (hb, res):
        if isinstance(src_obj, dict) and isinstance(src_obj.get("meta"), dict):
            meta.update({k: v for k, v in src_obj["meta"].items() if v is not None})
    created = man.get("created_ts") or pidj.get("started_at")
    if not is_num(created):
        try:
            created = d.stat().st_ctime
        except OSError:
            created = None
    run = {
        "run_id": man.get("run_id") or d.name,
        "dir": rel_to(root, d),
        "name": man.get("name"),
        "created_at": iso(created),
        "_created": created,
        "pid": pid,
        "gpus": man.get("gpus"),
        "note": man.get("note"),
        "tags": man.get("tags") or None,
        "study": man.get("study") or meta.get("study"),
        "trial": man.get("trial") if man.get("trial") is not None else meta.get("trial"),
        "seed": meta.get("seed") if meta.get("seed") is not None else man.get("seed"),
        "source_hash": ((man.get("snapshot") or {}).get("source_hash") or man.get("source_hash") or "")[:12] or None,
        "cmd": man.get("cmd"),
        "cwd": man.get("cwd"),
        "deadline": man.get("deadline"),
    }
    if errors:
        run["file_errors"] = errors[:5]
    if man.get("seed") is not None and meta.get("seed") is not None and str(man.get("seed")) != str(meta.get("seed")):
        run["seed_mismatch"] = {"launch": man.get("seed"), "recorded_by_run": meta.get("seed")}
    if study:
        run["study_progress"] = {k: shb.get(k) for k in ("study", "current_trial", "trial_run_dir") if shb.get(k) is not None}
    reason = None
    resumed_live = (isinstance(res, dict) and alive and hb_ok and is_num(res.get("ended_ts"))
                    and hb["ts"] > res["ended_ts"] + 1 and not ex)
    if resumed_live:
        run["note_resumed"] = "result.json predates the live heartbeat (resumed in place)"
    if isinstance(res, dict) and res.get("state") and not resumed_live:
        state = normalize_state(res.get("state"))
        reason = res.get("reason")
    elif isinstance(ex, dict):
        rc = ex.get("returncode")
        if rc == 0 and hb_ok:
            # RunLog writes result.json whenever the interpreter exits, so this process ended without its exit hooks
            # (os._exit, or terminated with exit code 0): a truncated run must not read as a finished one
            state, reason = "incomplete", "exit code 0 but RunLog never wrote result.json (process ended abnormally)"
        elif rc == 0:
            state, run["inferred"] = "completed", "exit code 0 but no result.json (no metrics recorded)"
        elif rc is None:
            state, reason = "failed", ex.get("error") or "process could not start"
        elif is_num(rc) and rc < 0 or ex.get("escalated_to_sigkill") and ex.get("stopped_for"):
            # a kill by the supervisor shows as a negative return code on POSIX and as exit code 1 on Windows
            how = f"terminated by signal {-int(rc)}" if is_num(rc) and rc < 0 else "killed by the supervisor"
            state, reason = "interrupted", how + (f" ({ex.get('stopped_for')})" if ex.get("stopped_for") else "")
        else:
            state, reason = "failed", log_reason(d / "stdout.log") or f"exit code {rc}"
    elif pid:
        if alive or ending:
            if hb_age is None:
                state = "starting" if (is_num(created) and t - created < stale) else "stalled"
            else:
                state = "running" if hb_age <= stale else "stalled"
        else:
            state = "lost"
            lr = log_reason(d / "stdout.log")
            reason = "process gone without result/exit record" + (f"; log: {lr}" if lr else "")
    elif hb_ok:
        state = "running" if hb_age <= stale else "unknown"
        if state == "unknown":
            reason = f"no pid recorded and heartbeat {fmt_secs(hb_age)} old"
    elif hb_age is not None:
        state = "running" if hb_age <= stale else "unknown"
    else:
        state = "unknown"
    run["state"] = state
    if reason:
        run["reason"] = str(reason)[:300]
    run["alive"] = alive
    if hb_ok:
        run["heartbeat_age_s"] = round(hb_age, 1)
        for k in ("step", "epoch", "total_steps", "phase", "throughput_steps_per_s"):
            if hb.get(k) is not None:
                run[k] = hb.get(k)
        run["latest"] = hb.get("latest") or {}
        run["nonfinite"] = hb.get("nonfinite") or []
        if hb.get("gpu_mem_gb") is not None:
            run["gpu_mem_gb"] = hb.get("gpu_mem_gb")
        if is_num(hb.get("started_ts")):
            run["elapsed_s"] = round(t - hb["started_ts"], 1) if state in ACTIVE_STATES else None
    if isinstance(res, dict):
        if is_num(res.get("duration_s")):
            run["duration_s"] = res["duration_s"]
        if res.get("nonfinite"):
            run["nonfinite"] = res.get("nonfinite")
    val, src, ckpt, step, why = metric_for({"result": res, "heartbeat": hb}, cfg)
    run["metric"] = {"value": val, "source": src, "step": step, "ckpt": ckpt, "why_missing": why}
    if ckpt:
        cp = Path(ckpt)
        if not cp.is_absolute():
            cands = [root / ckpt, d / ckpt]
            if run.get("cwd"):
                cands.insert(0, Path(run["cwd"]) / ckpt)
            run["metric"]["ckpt_exists"] = any(c.exists() for c in cands)
        else:
            run["metric"]["ckpt_exists"] = cp.exists()
        parts = re.split(r"[\\/]+", str(ckpt))
        if not run["metric"]["ckpt_exists"] and d.name in parts[:-1]:
            # recorded on another machine (the mirror of a remote run) or before the project folder moved: the
            # part of the path below the run's own folder is looked up in this run folder
            tail = parts[len(parts) - 1 - parts[-2::-1].index(d.name):]
            if ".." not in tail and d.joinpath(*tail).exists():
                run["metric"].update(ckpt=str(d.joinpath(*tail)), ckpt_exists=True)
    st, tot, thr = run.get("step"), run.get("total_steps"), run.get("throughput_steps_per_s")
    if is_num(st) and is_num(tot) and tot > 0:
        run["progress"] = round(min(1.0, st / tot), 4)
        if state in ACTIVE_STATES and is_num(thr) and thr > 0:
            run["eta_s"] = round((tot - st) / thr, 1)
    return run


def load_run_safe(root: Path, d: Path, cfg, t: float):
    try:
        return load_run(root, d, cfg, t)
    except Exception as e:  # noqa: BLE001 - one corrupt run directory must never hide the others
        created = None
        try:
            created = d.stat().st_mtime
        except OSError:
            pass
        return {"run_id": d.name, "dir": rel_to(root, d), "state": "unknown", "alive": False, "_created": created,
                "created_at": iso(created), "reason": f"unreadable run files: {type(e).__name__}: {str(e)[:160]}",
                "file_errors": [f"{type(e).__name__}: {str(e)[:160]}"],
                "metric": {"value": None, "source": None, "step": None, "ckpt": None, "why_missing": "unreadable"}}


def scan(root: Path, cfg):
    t = now()
    return [load_run_safe(root, d, cfg, t) for d in list_run_dirs(runs_root(root, cfg))]


def resolve_run(root: Path, cfg, ref: str) -> Path:
    rdir = runs_root(root, cfg)
    dirs = list_run_dirs(rdir)
    if not dirs:
        raise SystemExit(f"expctl: no runs under {rel_to(root, rdir)}")
    if ref in ("latest", "last"):
        def created(d):
            m = read_json(d / "manifest.json") or {}
            c = m.get("created_ts")
            return c if is_num(c) else d.stat().st_mtime
        return max(dirs, key=created)
    exact = [d for d in dirs if d.name == ref]
    if exact:
        return exact[0]
    cands = [d for d in dirs if d.name.startswith(ref) or d.name.endswith(ref) or ref in d.name]
    if len(cands) == 1:
        return cands[0]
    if not cands:
        raise SystemExit(f"expctl: no run matches '{ref}'")
    raise SystemExit("expctl: ambiguous run '%s': %s" % (ref, ", ".join(d.name for d in cands[:8])))


# ----------------------------------------------------------------------------- optuna

def optuna_summary(root: Path, cfg, limit_studies=5):
    ocfg = cfg.get("optuna") or {}
    storage_spec = ocfg.get("storage")
    if not storage_spec:
        return None
    try:
        import optuna  # type: ignore
    except Exception as e:  # noqa: BLE001
        return {"error": f"optuna not importable by {sys.executable} ({type(e).__name__}); run expctl with the "
                         f"project interpreter, e.g. 'uv run python <expctl.py> status'"}
    try:
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except Exception:  # noqa: BLE001
        pass
    try:
        if storage_spec.startswith("journal:"):
            path = storage_spec.split(":", 1)[1]
            path = str(Path(path) if Path(path).is_absolute() else root / path)
            if not Path(path).exists():
                return {"storage": storage_spec, "studies": [], "note": "journal file does not exist yet"}
            try:
                backend = optuna.storages.journal.JournalFileBackend(path)
            except AttributeError:
                backend = optuna.storages.JournalFileStorage(path)  # Optuna < 4.0
            storage = optuna.storages.JournalStorage(backend)
        else:
            if storage_spec.startswith("sqlite:///") and not storage_spec.startswith("sqlite:////"):
                dbp = storage_spec[len("sqlite:///"):]
                if not (root / dbp).exists():
                    return {"storage": storage_spec, "studies": [], "note": "database file does not exist yet"}
                storage_spec = "sqlite:///" + str((root / dbp).resolve())
            storage = storage_spec
        names = ocfg.get("studies") or optuna.get_all_study_names(storage=storage)
    except Exception as e:  # noqa: BLE001
        return {"storage": storage_spec, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    out = []
    for name in list(names)[-limit_studies:]:
        try:
            study = optuna.load_study(study_name=name, storage=storage)
            trials = study.get_trials(deepcopy=False)
            counts = {}
            for tr in trials:
                counts[tr.state.name] = counts.get(tr.state.name, 0) + 1
            entry = {"name": name, "n_trials": len(trials), "counts": counts,
                     "directions": [d.name.lower() for d in study.directions],
                     "contract": study.user_attrs.get("contract") if hasattr(study, "user_attrs") else None}
            complete = [tr for tr in trials if tr.state.name == "COMPLETE"]
            if len(study.directions) == 1:
                if complete:
                    bt = study.best_trial
                    entry["best"] = {"trial": bt.number, "value": bt.value, "params": bt.params,
                                     "run_dir": bt.user_attrs.get("run_dir"), "ckpt": bt.user_attrs.get("ckpt")}
                else:
                    entry["best"] = None
            else:
                entry["pareto_size"] = len(study.best_trials) if complete else 0
            fails = [tr for tr in trials if tr.state.name == "FAIL"][-3:]
            if fails:
                entry["recent_failures"] = [
                    {"trial": tr.number,
                     "reason": str((getattr(tr, "user_attrs", None) or {}).get("fail_reason")
                                   or (getattr(tr, "system_attrs", None) or {}).get("fail_reason") or "")[:200]}
                    for tr in fails]  # system_attrs was removed in Optuna 5.0; keep fail reasons in user_attrs
            out.append(entry)
        except Exception as e:  # noqa: BLE001
            out.append({"name": name, "error": f"{type(e).__name__}: {str(e)[:200]}"})
    return {"storage": ocfg.get("storage"), "studies": out}


# ----------------------------------------------------------------------------- status

def journal_tail(root: Path, cfg, n=3):
    p = root / (cfg.get("journal") or "experiments/JOURNAL.md")
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # ignore the commented entry template
    heads = [ln.strip() for ln in text.splitlines() if ln.startswith("## ") and ln.strip().lower() != "## project card"]
    return {"path": rel_to(root, p), "entries": len(heads), "last_headings": heads[-n:]}


def build_status(root: Path, cfg, with_gpu=True):
    t = now()
    lim = cfg.get("limits") or {}
    runs = scan(root, cfg)
    counts = {s: 0 for s in ALL_STATES}
    for r in runs:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    counts = {k: v for k, v in counts.items() if v}
    mcfg = cfg.get("metric") or {}
    direction = (mcfg.get("direction") or "").lower() or None
    alerts, notes = [], []
    if cfg.get("_config_error"):
        alerts.append(f"config {CONFIG_REL} unreadable: {cfg['_config_error']}")
    if not mcfg.get("name"):
        notes.append(f"metric.name not set in {CONFIG_REL}: ranking disabled")
    elif direction not in ("maximize", "minimize"):
        notes.append(f"metric.direction must be 'maximize' or 'minimize' in {CONFIG_REL}: ranking disabled")

    active = [r for r in runs if r["state"] in ACTIVE_STATES]
    active.sort(key=lambda r: r.get("_created") or 0, reverse=True)
    stale = cfg.get("heartbeat_stale_seconds")
    for r in active:
        if r["state"] == "stalled":
            age = r.get("heartbeat_age_s")
            alerts.append(f"{r['run_id']}: process alive but heartbeat " +
                          (f"{fmt_secs(age)} old" if age is not None else "never written") +
                          f" (> {stale}s) - possible hang, I/O stall or dataloader deadlock")
        if is_num(r.get("deadline")) and t > r["deadline"]:
            alerts.append(f"{r['run_id']}: still running {fmt_secs(t - r['deadline'])} past its deadline")
    for r in runs:
        if r.get("nonfinite"):
            alerts.append(f"{r['run_id']} ({r['state']}): non-finite values in {', '.join(map(str, r['nonfinite'][:4]))}")
        if r.get("file_errors"):
            alerts.append(f"{r['run_id']}: unreadable run files ({'; '.join(r['file_errors'])[:160]})")
        if r.get("seed_mismatch"):
            sm = r["seed_mismatch"]
            alerts.append(f"{r['run_id']}: seed recorded by the run ({sm['recorded_by_run']}) differs from the launch "
                          f"--seed ({sm['launch']}); the training code must read --seed or $EXP_SEED")
    lost = [r for r in runs if r["state"] == "lost"]
    for r in lost[:3]:
        alerts.append(f"{r['run_id']}: {r.get('reason', 'process gone without result')}")

    # GPU contention: same GPU index declared by >1 active run, or GPU processes from >1 run
    gpus = gpu_info() if with_gpu else None
    gpu_users = {}
    for r in active:
        for g in (r.get("gpus") or []):
            gpu_users.setdefault(str(g), set()).add(r["run_id"])
    if isinstance(gpus, list):
        pid_to_run = {}
        for r in active:
            if r.get("pid"):
                pid_to_run[int(r["pid"])] = r["run_id"]
        for g in gpus:
            for gp in g.get("pids", []):
                owner = pid_to_run.get(gp) or next((pid_to_run[a] for a in ancestors(gp) if a in pid_to_run), None)
                if owner:
                    gpu_users.setdefault(str(g["index"]), set()).add(owner)
                    for r in active:
                        if r["run_id"] == owner:
                            r.setdefault("gpus_observed", [])
                            if g["index"] not in r["gpus_observed"]:
                                r["gpus_observed"].append(g["index"])
    for g, users in gpu_users.items():
        if len(users) > 1:
            alerts.append(f"GPU {g} shared by {len(users)} active runs: {', '.join(sorted(users))}")

    free_gb, free_pct = disk_free(runs_root(root, cfg))
    if free_gb is not None and (free_gb < float(cfg.get("min_free_disk_gb") or 0) or (free_pct or 100) < 5):
        alerts.append(f"low disk: {free_gb} GB ({free_pct}%) free on runs filesystem")

    # top eligible completed runs
    top, ineligible = [], 0
    if mcfg.get("name") and direction in ("maximize", "minimize"):
        for r in runs:
            if r["state"] != "completed":
                continue
            m = r["metric"]
            if not finite(m.get("value")):
                ineligible += 1
                continue
            if m.get("ckpt") and m.get("ckpt_exists") is False:
                ineligible += 1
                alerts.append(f"{r['run_id']}: recorded checkpoint missing: {m['ckpt']}")
                continue
            top.append(r)
        top.sort(key=lambda r: r["metric"]["value"], reverse=(direction == "maximize"))
    top_out = [{"run_id": r["run_id"], "value": r["metric"]["value"], "source": r["metric"]["source"],
                "step": r["metric"].get("step"), "ckpt": r["metric"].get("ckpt"), "seed": r.get("seed"),
                "study": r.get("study"), "trial": r.get("trial"), "source_hash": r.get("source_hash"),
                "note": r.get("note"), "dir": r["dir"]} for r in top[: int(lim.get("top_k", 5))]]

    failures = [r for r in runs if r["state"] in ("failed", "lost", "incomplete", "interrupted", "timeout")]
    failures.sort(key=lambda r: r.get("_created") or 0, reverse=True)
    fail_out = [{"run_id": r["run_id"], "state": r["state"], "reason": r.get("reason"), "dir": r["dir"]}
                for r in failures[: int(lim.get("failures", 5))]]

    def active_view(r):
        keep = ("run_id", "state", "pid", "step", "total_steps", "progress", "epoch", "phase", "heartbeat_age_s",
                "elapsed_s", "eta_s", "throughput_steps_per_s", "latest", "gpu_mem_gb", "gpus", "gpus_observed",
                "note", "study", "trial", "seed", "source_hash", "dir")
        v = {k: r[k] for k in keep if r.get(k) not in (None, [], {})}
        lat = v.get("latest")
        if isinstance(lat, dict) and len(lat) > 12:
            v["latest"] = dict(list(lat.items())[:12])
        if is_num(r.get("deadline")):
            v["deadline_in_s"] = round(r["deadline"] - t, 1)
        m = r.get("metric") or {}
        if m.get("value") is not None:
            v["best_so_far"] = {"value": m["value"], "step": m.get("step")}
        return v

    recent = sorted(runs, key=lambda r: r.get("_created") or 0, reverse=True)[: int(lim.get("recent", 5))]
    opt = optuna_summary(root, cfg)
    if isinstance(opt, dict):
        running_trials = sum((s.get("counts") or {}).get("RUNNING", 0) for s in opt.get("studies", []))
        if running_trials and not active:
            alerts.append(f"Optuna reports {running_trials} RUNNING trial(s) but no live run process "
                          f"(possible zombie trials from a crash)")
    max_alerts = int(lim.get("alerts", 12))
    if len(alerts) > max_alerts:
        alerts = alerts[:max_alerts] + [f"(+{len(alerts) - max_alerts} more alerts)"]
    status = {
        "schema": SCHEMA_STATUS,
        "generated_at": iso(t),
        "root": str(root),
        "runs_dir": cfg["runs_dir"],
        "metric": {"name": mcfg.get("name"), "direction": direction, "select": mcfg.get("select", "best")},
        "counts": counts,
        "total_runs": len(runs),
        "active": [active_view(r) for r in active[: int(lim.get("active", 10))]],
        "top": top_out,
        "ineligible_completed": ineligible,
        "recent_failures": fail_out,
        "recent": [{"run_id": r["run_id"], "state": r["state"], "created_at": r.get("created_at"),
                    "value": (r.get("metric") or {}).get("value")} for r in recent],
        "alerts": alerts,
        "notes": notes,
        "optuna": opt,
        "resources": {"disk_free_gb": free_gb, "disk_free_pct": free_pct,
                      "gpus": [{k: g.get(k) for k in ("index", "name", "util_pct", "mem_used_mb", "mem_total_mb")}
                               for g in gpus] if isinstance(gpus, list) else gpus},
        "journal": journal_tail(root, cfg),
    }
    if not runs:
        status["notes"].append(f"no runs under {cfg['runs_dir']}/ yet")
    return status


def brief_text(st) -> str:
    c = st.get("counts") or {}
    m = st.get("metric") or {}
    parts = [f"{v} {k}" for k, v in c.items()]
    lines = [f"[expctl {st['generated_at']}] runs: {', '.join(parts) if parts else 'none'}"
             + (f" | metric {m['name']} ({m.get('direction') or 'direction?'}, {m.get('select')})" if m.get("name")
                else " | metric not configured")]
    for a in st.get("active", []):
        prog = f"{a.get('step', '?')}/{a.get('total_steps', '?')}"
        if a.get("progress") is not None:
            prog += f" ({100 * a['progress']:.0f}%)"
        lat = a.get("latest") or {}
        show = {k: v for k, v in lat.items() if m.get("name") and k == m["name"]} or dict(list(lat.items())[:2])
        mets = " ".join(f"{k}={fmt_val(v)}" for k, v in show.items())
        lines.append(f"  {a['state'].upper():8s} {a['run_id']} pid={a.get('pid')} step {prog} hb {fmt_secs(a.get('heartbeat_age_s'))}"
                     f" {mets} ETA {fmt_secs(a.get('eta_s'))}")
    if st.get("top"):
        tops = " | ".join(f"{fmt_val(t['value'])} {t['run_id']}" for t in st["top"][:3])
        lines.append(f"  TOP: {tops}")
    for f in st.get("recent_failures", [])[:2]:
        lines.append(f"  {f['state'].upper()}: {f['run_id']}: {f.get('reason') or ''}"[:220])
    for a in st.get("alerts", [])[:5]:
        lines.append(f"  ALERT: {a}"[:240])
    opt = st.get("optuna")
    if isinstance(opt, dict):
        if opt.get("error"):
            lines.append(f"  OPTUNA: {opt['error'][:160]}")
        for s in opt.get("studies", [])[:3]:
            b = s.get("best") or {}
            lines.append(f"  STUDY {s.get('name')}: {s.get('counts')}" + (f" best#{b.get('trial')}={fmt_val(b.get('value'))}" if b else ""))
    j = st.get("journal")
    if j and j.get("last_headings"):
        lines.append(f"  JOURNAL ({j['entries']} entries): last = {j['last_headings'][-1][:120]}")
    elif j:
        lines.append(f"  JOURNAL: no experiment entries yet ({j['path']})")
    for n in st.get("notes", [])[:2]:
        lines.append(f"  note: {n}")
    return "\n".join(lines)


def cmd_status(args):
    root = find_root(args.root)
    cfg = load_config(root)
    if args.run:
        d = resolve_run(root, cfg, args.run)
        r = load_run_safe(root, d, cfg, now())
        r.pop("_created", None)
        r["files"] = sorted(p.name for p in d.iterdir())[:40]
        r["manifest"] = read_json(d / "manifest.json")
        r["result"] = read_json(d / "result.json")
        r["exit"] = read_json(d / "exit.json")
        logt = tail_bytes(d / "stdout.log", 4000).splitlines()[-25:]
        r["log_tail"] = logt
        print(json.dumps(clean(r), indent=1, default=str))
        return 0
    st = build_status(root, cfg, with_gpu=not args.no_gpu)
    if args.brief:
        print(brief_text(st))
    else:
        print(json.dumps(clean(st), indent=None if args.compact else 1, default=str))
    return 0


# ----------------------------------------------------------------------------- launch / supervise / stop

def parse_deadline(s):
    if not s:
        return None
    s = s.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smhd])", s, re.I)
    if m:
        mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2).lower()]
        return now() + float(m.group(1)) * mult
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return time.mktime(time.strptime(s, fmt))
        except ValueError:
            pass
    raise SystemExit(f"expctl: cannot parse deadline '{s}' (use 90m, 6h, 2d or YYYY-MM-DDTHH:MM local time)")


def parse_duration(s, default):
    if s is None:
        return default
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smhd]?)", str(s).strip(), re.I)
    if not m:
        raise SystemExit(f"expctl: cannot parse duration '{s}'")
    return float(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2).lower()]


def slug(s):
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", s or "run").strip("-.")
    return (s or "run")[:40]


def fail(code, msg, **extra):
    print(json.dumps(clean({"ok": False, "error": msg, **extra}), indent=1))
    return code


def changed_source(run_id, was, is_now, tool):
    """Why a resume is refused: the run would go on with other code than it began with, under one name."""
    return (f"the source has changed since {run_id} was launched (source hash {was[:12]} then, {is_now[:12]} now), so a "
            f"resume would continue its checkpoint with other code. Bring back the code of that launch (its manifest "
            f"names the commit, and files that git neither tracks nor ignores count as source), or, if the change is "
            f"meant, resume with `{tool} resume {run_id} --allow-code-change`: the new run then records both hashes.")


def cmd_launch(args):
    root = find_root(args.root)
    cfg = load_config(root)
    cmd = list(args.cmd or [])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        return fail(2, "no command given; usage: expctl launch --name NAME -- python train.py ...")
    rdir = runs_root(root, cfg)
    rdir.mkdir(parents=True, exist_ok=True)
    free_gb, free_pct = disk_free(rdir)
    if free_gb is not None and free_gb < float(cfg.get("min_free_disk_gb") or 0) and not args.force:
        return fail(3, f"only {free_gb} GB free on the runs filesystem (< min_free_disk_gb); free space or pass --force")
    gpus = [g.strip() for g in args.gpus.split(",")] if args.gpus else None
    files, is_git, prov = provenance(root, cfg)
    resume_of = getattr(args, "resume_of", None)  # set by `expctl resume`: the run directory this run continues
    was_hash = ((read_json(resume_of / "manifest.json") or {}).get("snapshot") or {}).get("source_hash") if resume_of else None
    if was_hash and was_hash != prov["source_hash"] and not getattr(args, "allow_code_change", False):
        return fail(2, changed_source(resume_of.name, was_hash, prov["source_hash"], "expctl.py"))
    active = [r for r in scan(root, cfg) if r["state"] in ACTIVE_STATES]
    for r in active:
        same_code = (r.get("source_hash") or "") == prov["source_hash"][:12]
        if r.get("cmd") == cmd and same_code and not args.allow_duplicate:
            return fail(4, f"the same command on the same source snapshot is already active as {r['run_id']} "
                           f"(pass --allow-duplicate if a replicate is intended, e.g. a different seed via env)",
                        active_run=r["run_id"])
        if gpus and set(map(str, r.get("gpus") or [])) & set(gpus) and not args.share_gpu:
            return fail(5, f"GPU(s) {sorted(set(map(str, r['gpus'])) & set(gpus))} already used by active run {r['run_id']}"
                           f" (pass --share-gpu if intended)", active_run=r["run_id"])
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{slug(args.name)}-{secrets.token_hex(2)}"
    run_dir = rdir / run_id
    run_dir.mkdir(parents=False, exist_ok=False)
    if is_git:
        patch = run_git(root, "diff", "HEAD", "--binary")
        if patch:
            if len(patch) <= 5_000_000:
                (run_dir / "src.patch").write_bytes(patch)
                prov["patch"] = "src.patch"
            else:
                prov["patch"] = f"omitted ({len(patch)} bytes > 5 MB)"
    mode = args.snapshot or (cfg.get("snapshot") or {}).get("mode", "copy")
    here = Path.cwd().resolve()
    try:
        rel_here = here.relative_to(root)
    except ValueError:
        rel_here = None
    snap = None
    if mode == "copy":
        snap = make_snapshot(root, run_dir, files, is_git, cfg)
        if snap["failure_count"]:
            shutil.rmtree(run_dir, ignore_errors=True)
            return fail(6, "snapshot failed: a link could not be created (on native Windows without the symlink "
                           "privilege the fallback is a junction or a hard link, which need a local NTFS volume and, "
                           "for files, the volume of the runs directory); retry with --snapshot none",
                        details=snap["failures"])
        cwd = run_dir / "src" / (rel_here if rel_here is not None else Path("."))
    else:
        cwd = here
    deadline = parse_deadline(args.deadline)
    grace = parse_duration(args.grace, 600.0)
    t = now()
    manifest = {
        "schema": SCHEMA_MANIFEST,
        "run_id": run_id,
        "name": args.name,
        "note": args.note,
        "tags": dict(kv.split("=", 1) for kv in (args.tag or []) if "=" in kv),
        "created_at": iso(t),
        "created_ts": t,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "user": os.environ.get("USER") or os.environ.get("USERNAME"),
        "cmd": cmd,
        "cwd": str(cwd),
        "root": str(root),
        "gpus": gpus,
        "seed": args.seed,
        "study": args.study,
        "trial": args.trial,
        "deadline": deadline,
        "deadline_at": iso(deadline),
        "grace_s": grace,
        "kill_after_s": float(cfg.get("kill_after_s") or 120),
        "snapshot": {"mode": mode, **prov, **({"src": snap} if snap else {})},
        "launched_by": "expctl",
        "via": args.via or "setsid",
    }
    if resume_of:
        manifest["resume_of"] = resume_of.name
        manifest["resume_of_source_hash"] = was_hash
    write_json_atomic(run_dir / "manifest.json", manifest)
    env = os.environ.copy()
    env.update({"EXP_RUN_DIR": str(run_dir), "EXP_RUN_ID": run_id, "PYTHONUNBUFFERED": "1",
                "EXP_SOURCE_HASH": prov["source_hash"], "EXP_PROJECT_ROOT": str(root)})
    if resume_of:
        env["EXP_RESUME_FROM"] = str(resume_of)
    if args.seed is not None:
        env["EXP_SEED"] = str(args.seed)
    if deadline:
        env["EXP_DEADLINE"] = repr(deadline)
    if gpus:
        env["CUDA_VISIBLE_DEVICES"] = ",".join(gpus)
    if mode == "copy":
        # make imports resolve to the immutable copy even when the project is pip-installed in editable mode
        snap_root = run_dir / "src"
        front = [str(snap_root)] + ([str(snap_root / "src")] if (snap_root / "src").is_dir() else [])
        env["PYTHONPATH"] = os.pathsep.join(front + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    sup_cmd = [sys.executable, os.path.abspath(__file__), "_supervise", str(run_dir)]
    sup_log = open(run_dir / "supervisor.log", "ab")
    via = args.via or "setsid"
    if via == "tmux":
        tmux = shutil.which("tmux")
        if not tmux:
            shutil.rmtree(run_dir, ignore_errors=True)
            return fail(8, "--via tmux requested but tmux is not installed")
        # The full environment goes through a private file (0600) that the supervisor reads and deletes, so the run
        # sees exactly what a setsid launch would see (tokens, HF_HOME, NCCL/OMP settings) without putting secrets
        # on a command line.
        env_file = run_dir / ".launch-env.json"
        fd = os.open(str(env_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(env, f)
        session = re.sub(r"[^A-Za-z0-9_-]", "-", f"exp-{run_id}")[:80]
        shell_cmd = shlex.join([*sup_cmd, "--env-file", str(env_file)]) + \
            f" >> {shlex.quote(str(run_dir / 'supervisor.log'))} 2>&1"
        r = subprocess.run([tmux, "new-session", "-d", "-s", session, "-c", str(cwd), shell_cmd],
                           capture_output=True, text=True)
        if r.returncode != 0:
            shutil.rmtree(run_dir, ignore_errors=True)
            return fail(8, f"tmux new-session failed: {(r.stderr or r.stdout).strip()[:300]}")
        manifest["via"], manifest["tmux_session"] = "tmux", session
        write_json_atomic(run_dir / "manifest.json", manifest)
        sp = None
    else:
        kw = dict(stdin=subprocess.DEVNULL, stdout=sup_log, stderr=subprocess.STDOUT, cwd=str(cwd), env=env,
                  close_fds=True)
        if os.name == "nt":
            kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        else:
            kw["start_new_session"] = True
        try:
            sp = subprocess.Popen(sup_cmd, **kw)
        except OSError as e:
            return fail(7, f"could not start supervisor: {e}", run_dir=rel_to(root, run_dir))
    pid, start_error = None, None
    for _ in range(50):
        pj = read_json(run_dir / "pid.json")
        if isinstance(pj, dict) and pj.get("pid"):
            pid = pj["pid"]
            break
        ex = read_json(run_dir / "exit.json")
        if isinstance(ex, dict):
            if ex.get("returncode") is None:
                start_error = ex.get("error") or "the command could not start"
            break
        time.sleep(0.1)
    me = Path(os.path.abspath(__file__))
    try:
        me_rel = me.relative_to(root).as_posix()
    except ValueError:
        me_rel = str(me)
    out = {
        "ok": start_error is None,
        "run_id": run_id,
        "run_dir": rel_to(root, run_dir),
        "pid": pid,
        "supervisor_pid": (sp.pid if sp else (read_json(run_dir / "pid.json") or {}).get("supervisor_pid")),
        "via": via,
        "cwd": rel_to(root, cwd),
        "snapshot": mode,
        "source_hash": prov["source_hash"][:12],
        "git_dirty": (prov.get("git") or {}).get("dirty"),
        "deadline_at": iso(deadline),
        "log": rel_to(root, run_dir / "stdout.log"),
        "next": {
            "status": f"{py_cmd(cfg)} {me_rel} status --brief",
            "detail": f"{py_cmd(cfg)} {me_rel} status --run {run_id}",
            "curve": f"{py_cmd(cfg)} {me_rel} curve {run_id}",
            "watch": f"{py_cmd(cfg)} {me_rel} watch {run_id} --until terminal --max-time 25m",
        },
    }
    if resume_of:
        out["resume_of"] = resume_of.name
    if start_error:
        out["error"] = start_error
    elif pid is None:
        out["warning"] = "child pid not reported yet; check status in a few seconds"
    if mode == "copy" and optuna_storage_file(cfg):
        out["note"] = ("relative Optuna storage paths resolve inside the snapshot; build the storage URL from "
                       "$EXP_PROJECT_ROOT so every run writes to the shared study")
    print(json.dumps(clean(out), indent=1))
    return 0 if start_error is None else 9


def cmd_resume(args):
    """A new run that continues an ended one: same command, seed, GPUs, tags and working directory. The training
    script finds the earlier run directory in $EXP_RESUME_FROM and loads its last checkpoint (references/resume.md)."""
    root = find_root(args.root)
    cfg = load_config(root)
    d = resolve_run(root, cfg, args.run)
    r = load_run_safe(root, d, cfg, now())
    man = read_json(d / "manifest.json")
    man = man if isinstance(man, dict) else {}
    if man.get("remote"):
        return fail(2, f"{r['run_id']} ran on a remote target: resume it with nnremote.py resume {r['run_id']}")
    if r["state"] in ACTIVE_STATES:
        return fail(4, f"{r['run_id']} is {r['state']}; resume continues a run that has ended", active_run=r["run_id"])
    if not man.get("cmd") or man.get("launched_by") != "expctl":
        return fail(2, f"{r['run_id']} was not started by expctl launch, so no command is recorded to repeat")
    mode = (man.get("snapshot") or {}).get("mode")
    try:  # run from the directory the first launch ran from, wherever this command was typed
        was = Path(man.get("cwd") or "")
        os.chdir(root / (was.relative_to(d / "src") if mode == "copy" else was.relative_to(root)))
    except (ValueError, OSError):
        pass
    gpus = man.get("gpus")
    return cmd_launch(argparse.Namespace(
        root=str(root), cmd=list(man["cmd"]), name=man.get("name") or "run", note=args.note or f"resume of {d.name}",
        snapshot=mode if mode in ("copy", "none") else None, deadline=args.deadline, grace=args.grace,
        gpus=",".join(map(str, gpus)) if gpus else None, seed=man.get("seed"), study=man.get("study"),
        trial=man.get("trial"), tag=[f"{k}={v}" for k, v in (man.get("tags") or {}).items()], force=args.force,
        allow_duplicate=args.allow_duplicate, share_gpu=args.share_gpu,
        via=man.get("via") if man.get("via") in ("setsid", "tmux") else None, resume_of=d,
        allow_code_change=args.allow_code_change))


def cmd_supervise(args):
    run_dir = Path(args.run_dir)
    if getattr(args, "env_file", None):
        try:
            with open(args.env_file, encoding="utf-8") as f:
                os.environ.clear()
                os.environ.update({str(k): str(v) for k, v in json.load(f).items()})
        except (OSError, ValueError) as e:
            sys.stderr.write(f"expctl supervisor: could not read env file: {e}\n")
        finally:
            try:
                os.remove(args.env_file)
            except OSError:
                pass
    man = read_json(run_dir / "manifest.json") or {}
    cmd, cwd = man.get("cmd"), man.get("cwd")
    if not cmd:
        write_json_atomic(run_dir / "exit.json", {"returncode": None, "error": "manifest has no cmd", "ended_ts": now()})
        return 1
    log = open(run_dir / "stdout.log", "ab", buffering=0)
    t0 = now()
    env = dict(os.environ, EXP_LAUNCH_TS=repr(t0))  # RunLog ignores a stop.json older than this launch
    kw = dict(stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, cwd=cwd, env=env)
    if os.name == "nt":
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW: without it every run opens a console window
    else:
        kw["start_new_session"] = True  # own process group so stop/deadline can signal the whole tree
    try:
        child = subprocess.Popen(cmd, **kw)
    except OSError as e:
        write_json_atomic(run_dir / "exit.json", {"returncode": None, "error": f"could not start: {e}",
                                                  "ended_ts": now(), "ended_at": iso(now())})
        return 1
    write_json_atomic(run_dir / "pid.json", {"pid": child.pid, "pgid": child.pid, "supervisor_pid": os.getpid(),
                                             "started_at": t0, "proc_start": proc_start_time(child.pid)})
    state = {"stop_at": None, "why": None, "killed": False}

    def on_signal(signum, _frame):
        if state["stop_at"] is None:
            state["stop_at"], state["why"] = now(), "stop requested"
            signal_leader(child.pid, signal.SIGTERM)

    for sname in ("SIGTERM", "SIGINT", "SIGHUP"):
        sig = getattr(signal, sname, None)
        if sig is not None:
            try:
                signal.signal(sig, on_signal if sname != "SIGHUP" else signal.SIG_IGN)
            except (ValueError, OSError):
                pass
    deadline, grace = man.get("deadline"), float(man.get("grace_s") or 600)
    kill_after_default = float(man.get("kill_after_s") or 120)
    while True:
        try:
            rc = child.wait(timeout=2)
            break
        except subprocess.TimeoutExpired:
            pass
        t = now()
        if is_num(deadline) and state["stop_at"] is None and t > deadline + grace:
            state["stop_at"], state["why"] = t, "deadline + grace exceeded"
            signal_leader(child.pid, signal.SIGTERM)
        kill_after = kill_after_default
        req = read_json(run_dir / "stop.json")
        if isinstance(req, dict) and is_num(req.get("requested_ts")) and req["requested_ts"] >= t0:
            if is_num(req.get("kill_after_s")):
                kill_after = float(req["kill_after_s"])
            if os.name == "nt" and state["stop_at"] is None:  # elsewhere `expctl stop` signals this process
                state["stop_at"], state["why"] = t, "stop requested"
        if state["stop_at"] is not None and not state["killed"] and t > state["stop_at"] + kill_after:
            state["killed"] = True
            signal_group(child.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
    t1 = now()
    write_json_atomic(run_dir / "exit.json", {
        "returncode": rc, "signal": (-rc if is_num(rc) and rc < 0 else None),
        "ended_ts": t1, "ended_at": iso(t1), "duration_s": round(t1 - t0, 1),
        "stopped_for": state["why"], "escalated_to_sigkill": state["killed"]})
    return 0


def cmd_stop(args):
    root = find_root(args.root)
    cfg = load_config(root)
    d = resolve_run(root, cfg, args.run)
    r = load_run_safe(root, d, cfg, now())
    if r["state"] not in ACTIVE_STATES:
        print(json.dumps(clean({"ok": False, "run_id": r["run_id"], "state": r["state"], "error": "run is not active"})))
        return 1
    pj = read_json(d / "pid.json") or {}
    if not isinstance(pj, dict):
        pj = {}
    sup, pid = pj.get("supervisor_pid"), r.get("pid")
    req = {"requested_ts": now()}
    if args.kill_after:
        req["kill_after_s"] = parse_duration(args.kill_after, 120)
    # RunLog.should_stop() polls this file, so the request also reaches a trainer behind a wrapper that does not
    # forward signals, and a trainer on Windows, where it is the only graceful route.
    write_json_atomic(d / "stop.json", req)
    sent, via, killed = bool(sup) and pid_alive(sup), "supervisor", None
    if os.name == "nt":
        if not sent:  # no supervisor is left to escalate: give the loop its time to save and exit, then kill the tree
            sent, via = True, "process"
            t_end = now() + float(req.get("kill_after_s") or cfg.get("kill_after_s") or 120)
            while pid_alive(pid) and now() < t_end:
                time.sleep(0.5)
            killed = pid_alive(pid) and signal_group(pid, signal.SIGTERM)
    else:
        if sent:
            try:
                os.kill(int(sup), signal.SIGTERM)
            except OSError:
                sent = False
        if not sent:
            sent, via = signal_leader(pid, signal.SIGTERM), "process"
    out = {"ok": sent, "run_id": r["run_id"], "signal": None if os.name == "nt" else "SIGTERM", "via": via,
           "killed": killed or None}
    if args.wait and sent:
        t_end = now() + parse_duration(args.wait, 300)
        while now() < t_end:
            if (d / "exit.json").exists() or (d / "result.json").exists() and not pid_alive(r.get("pid")):
                break
            if via == "process" and not pid_alive(r.get("pid")):
                break
            time.sleep(1)
        time.sleep(0.5)
        out["final_state"] = load_run_safe(root, d, cfg, now())["state"]
    print(json.dumps(clean(out)))
    return 0 if sent else 1


def cmd_watch(args):
    root = find_root(args.root)
    cfg = load_config(root)
    interval = max(1.0, parse_duration(args.interval, 30.0))
    max_time = parse_duration(args.max_time, 1500.0)
    hb_every = parse_duration(args.heartbeat, 300.0)
    metric = (cfg.get("metric") or {}).get("name")
    targets = None
    if args.run and args.run != "all":
        targets = {resolve_run(root, cfg, args.run).name}
    t_start, last_emit, first = now(), 0.0, True
    prev = {}

    def emit(obj):
        obj["t"] = iso(now())
        print(json.dumps(clean(obj), separators=(",", ":"), default=str)[:600], flush=True)

    while True:
        runs = scan(root, cfg)
        if targets is None:
            watch_set = {r["run_id"] for r in runs if r["state"] in ACTIVE_STATES} | set(prev)
        else:
            watch_set = set(targets)
        cur = {r["run_id"]: r for r in runs if r["run_id"] in watch_set}
        events = []
        for rid, r in cur.items():
            mval = (r.get("latest") or {}).get(metric) if metric else None
            snap = {"state": r["state"], "metric": mval, "nonfinite": tuple(r.get("nonfinite") or ())}
            p = prev.get(rid)
            if p is None:
                events.append({"event": "watching" if first else "new_run", "run": rid, "state": r["state"],
                               "step": r.get("step"), "progress": r.get("progress")})
            else:
                if snap["state"] != p["state"]:
                    events.append({"event": "state", "run": rid, "from": p["state"], "to": snap["state"],
                                   "reason": r.get("reason")})
                if mval is not None and mval != p["metric"]:
                    events.append({"event": "metric", "run": rid, "step": r.get("step"), "metric": metric,
                                   "value": mval, "best_so_far": (r.get("metric") or {}).get("value")})
                if snap["nonfinite"] and snap["nonfinite"] != p["nonfinite"]:
                    events.append({"event": "alert", "run": rid, "alert": "non-finite " + ",".join(snap["nonfinite"])})
            prev[rid] = snap
        for e in events:
            emit(e)
        if events:
            last_emit = now()
        elif now() - last_emit >= hb_every:
            emit({"event": "progress", "runs": [{"run": rid, "state": r["state"], "step": r.get("step"),
                                                 "progress": r.get("progress"), "eta_s": r.get("eta_s")}
                                                for rid, r in list(cur.items())[:5]]})
            last_emit = now()
        first = False
        active_left = [rid for rid, r in cur.items() if r["state"] in ACTIVE_STATES]
        alertish = [e for e in events if e["event"] == "alert" or
                    (e["event"] == "state" and e.get("to") in ("stalled", "failed", "lost"))]
        done = None
        if not watch_set:
            done = "no active runs to watch"
        elif args.until == "terminal" and not active_left:
            done = "all watched runs are terminal"
        elif args.until == "any-terminal" and any(e["event"] == "state" and e.get("to") not in ACTIVE_STATES
                                                  for e in events):
            done = "a watched run finished"
        elif args.until == "alert" and alertish:
            done = "alert"
        elif now() - t_start >= max_time:
            done = "max-time reached; run watch again to keep waiting"
        if done:
            emit({"event": "done", "reason": done, "states": {rid: r["state"] for rid, r in list(cur.items())[:10]}})
            return 0
        time.sleep(interval)


# ----------------------------------------------------------------------------- curve / hash / env

def cmd_curve(args):
    root = find_root(args.root)
    cfg = load_config(root)
    d = resolve_run(root, cfg, args.run)
    path = d / "metrics.jsonl"
    if not path.exists():
        print(json.dumps({"run_id": d.name, "error": "metrics.jsonl not found (does the training code use RunLog?)"}))
        return 1
    want = [k.strip() for k in args.keys.split(",")] if args.keys else None
    since = args.since_step
    counts, all_keys = {}, {}

    def records():
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(rec, dict):
                    continue
                if since is not None and is_num(rec.get("step")) and rec["step"] < since:
                    continue
                yield rec

    for rec in records():
        for k, v in rec.items():
            if k in ("t", "step", "epoch") or not is_num(v):
                continue
            all_keys[k] = all_keys.get(k, 0) + 1
    metric = (cfg.get("metric") or {}).get("name")
    if not want:
        pri = [k for k in all_keys if metric and k == metric]
        pri += [k for k in all_keys if "loss" in k.lower() and k not in pri]
        want = (pri or list(all_keys))[:4]
    want = [k for k in want if k in all_keys]
    counts = {k: all_keys[k] for k in want}
    n_pts = max(5, min(int(args.points), 200))
    picks = {}
    for k, n in counts.items():
        step = max(1, n / n_pts)
        picks[k] = {min(n - 1, int(i * step)) for i in range(n_pts)} | {n - 1}
    seen = {k: 0 for k in want}
    series = {k: {"points": [], "n": counts[k], "nonfinite": 0, "first": None, "last": None,
                  "min": None, "max": None, "argmin_step": None, "argmax_step": None} for k in want}
    tail_vals = {k: [] for k in want}
    tail_start = {k: int(counts[k] * 0.8) for k in want}
    for rec in records():
        st = rec.get("step")
        for k in want:
            v = rec.get(k)
            if not is_num(v):
                continue
            i = seen[k]
            seen[k] += 1
            s = series[k]
            v = float(v)
            if not math.isfinite(v):
                s["nonfinite"] += 1
            else:
                if s["first"] is None:
                    s["first"] = [st, v]
                if s["min"] is None or v < s["min"]:
                    s["min"], s["argmin_step"] = v, st
                if s["max"] is None or v > s["max"]:
                    s["max"], s["argmax_step"] = v, st
                if i >= tail_start[k]:
                    tail_vals[k].append(v)
            s["last"] = [st, v]
            if i in picks[k]:
                s["points"].append([st, round(v, 6) if math.isfinite(v) else v])
    for k in want:
        tv = tail_vals[k]
        if len(tv) >= 4:
            h = len(tv) // 2
            a, b = sum(tv[:h]) / h, sum(tv[h:]) / (len(tv) - h)
            rel = (b - a) / (abs(a) + 1e-12)
            series[k]["last20pct_trend"] = "flat" if abs(rel) < 0.005 else ("rising" if rel > 0 else "falling")
            series[k]["last20pct_rel_change"] = round(rel, 5)
    out = {"run_id": d.name, "metric": metric, "available_keys": sorted(all_keys)[:60], "series": series}
    print(json.dumps(clean(out), indent=None if args.compact else 1))
    return 0


def cmd_hash(args):
    root = find_root(args.root)
    cfg = load_config(root)
    _files, is_git, prov = provenance(root, cfg)
    prov["root"] = str(root)
    prov["git_repo"] = is_git
    print(json.dumps(clean(prov), indent=1))
    return 0


FINAL_DIR = ".claude/state/final-eval"
FINAL_SHARED = "nn-training-final-eval.jsonl"  # in git's common folder, which outlives a removed worktree


def chained(path: Path, row):
    """Append a row to a record of the kind ledger_rows() reads."""
    lines = path.read_bytes().splitlines() if path.is_file() else []
    prev = hashlib.sha256(lines[-1]).hexdigest() if lines else ""
    with open(path, "ab") as f:
        f.write(json.dumps(clean(dict(row, prev=prev)), sort_keys=True).encode("utf-8") + b"\n")


def final_uses(root: Path):
    """(the start rows of every use of the final evaluation, a record of them that was edited or None, the copy all
    checkouts share or None, this project's path inside the repository). Every checkout of the repository looks at
    the same test split, so a use in another one counts here. A worktree that is removed takes its receipt along,
    so each row is also kept in git's common folder; rows of a checkout's receipt that this copy lacks (written
    before it existed) are added to it here."""
    sub = (run_git(root, "rev-parse", "--show-prefix", text=True) or "").strip()
    common = (run_git(root, "rev-parse", "--git-common-dir", text=True) or "").strip()
    shared = (root / common / FINAL_SHARED).resolve() if common else None
    tops = [x[9:] for x in (run_git(root, "worktree", "list", "--porcelain", text=True) or "").splitlines()
            if x.startswith("worktree ")]
    rows, ok = ledger_rows(shared) if shared else ([], True)
    edited = None if ok else shared
    seen = {(r.get("event"), r.get("use"), r.get("ts")): r for r in rows if r.get("sub") == sub}
    for p in dict.fromkeys([(root / FINAL_DIR / "receipt.jsonl").resolve()]
                           + [(Path(t) / sub / FINAL_DIR / "receipt.jsonl").resolve() for t in tops]):
        rows, ok = ledger_rows(p)
        edited = edited or (None if ok else p)
        for r in rows:
            if seen.setdefault((r.get("event"), r.get("use"), r.get("ts")), r) is r and shared:
                chained(shared, dict(r, sub=sub))
    uses = sorted((r for r in seen.values() if r.get("event") == "start"), key=lambda r: str(r.get("ts")))
    return uses, edited, shared, sub
ENV_PREFIX = re.compile(r"\s*([A-Za-z_]\w*)=(\"[^\"]*\"|'[^']*'|\S*)\s+")
NEEDS_SHELL = re.compile(r"[;&|<>$`^%\r\n]")  # also what cmd.exe would act on if the program is a batch file


def cmd_final_eval(args):
    """Run the configured final evaluation and keep a receipt. A test split that is looked at twice is no longer a
    test split, so the first use is recorded before the command starts and a further one needs a stated reason."""
    root = find_root(args.root)
    cfg = load_config(root)
    cmds = [re.sub(r"\s+", " ", str(c).strip()) for c in cfg.get("final_eval_commands") or [] if str(c).strip()]
    if not cmds or not 1 <= (args.which or 1) <= len(cmds) or (len(cmds) > 1 and not args.which):
        return fail(2, f"{CONFIG_REL} must hold one final_eval_commands entry, or --which N must name one of several",
                    final_eval_commands=cmds)
    configured, extra = cmds[(args.which or 1) - 1], list(args.args or [])
    if extra and extra[0] == "--":
        extra = extra[1:]
    bad = next((m for m in map(NEEDS_SHELL.search, [configured, *extra]) if m), None)
    if bad:
        return fail(2, f"The final evaluation is started without a shell, and {bad.group(0)!r} would need one. Put what "
                       "needs a shell into a script and name that script in final_eval_commands.")
    env, rest = dict(os.environ), configured
    while ENV_PREFIX.match(rest):  # leading NAME=value pairs, as a shell would take them
        m = ENV_PREFIX.match(rest)
        env[m.group(1)], rest = m.group(2).strip("\"'"), rest[m.end():]
    try:
        words = shlex.split(rest, posix=os.name != "nt")
    except ValueError as e:
        return fail(2, f"the final_eval_commands entry cannot be split into words: {e}")
    os.chdir(root)  # the command is the project's: its program and its paths are relative to the project root
    if not words or not shutil.which(words[0].strip('"')):
        return fail(2, f"the final evaluation's program was not found: {words[0] if words else '(none)'}")
    d = root / FINAL_DIR
    receipt = d / "receipt.jsonl"
    before, edited, shared, sub = final_uses(root)
    if (before or edited) and not args.again:
        why = (f"its receipt {rel_to(root, edited)} was edited, so earlier uses cannot be counted" if edited else
               f"it was already used {len(before)} time(s), other checkouts of the repository included, first on "
               f"{before[0].get('ts')}")
        return fail(2, f"The final evaluation is single-use, and {why}. A further look at the test split is a new "
                       "selection step: the user decides on it, and the report states every use. If it is justified "
                       '(the first attempt failed before it scored anything, say), run it with --again "the reason"; '
                       "the receipt and the journal record that reason.", uses=len(before))
    d.mkdir(parents=True, exist_ok=True)

    def note(**row):
        row = dict(row, ts=iso(now()))
        chained(receipt, row)
        if shared:
            chained(shared, dict(row, sub=sub))

    use, prov = len(before) + 1, provenance(root, cfg)[2]
    git, log = prov.get("git") or {}, d / f"{time.strftime('%Y%m%d-%H%M%S')}-use{use}.log"
    note(event="start", use=use, configured=configured, args=extra, reason=args.again, commit=git.get("commit"),
         dirty=git.get("dirty"), source_hash=prov["source_hash"], log=rel_to(root, log))
    t0, err = now(), None
    try:
        with open(log, "wb") as f:  # Windows takes the command line as one string; elsewhere it is a word list
            code = subprocess.run(rest + " " + subprocess.list2cmdline(extra) if os.name == "nt" else words + extra,
                                  cwd=str(root), env=env, stdin=subprocess.DEVNULL, stdout=f,
                                  stderr=subprocess.STDOUT).returncode
    except OSError as e:
        code, err = None, f"could not start: {e}"
    out = tail_bytes(log, 2000)
    digest = hashlib.sha256(log.read_bytes()).hexdigest() if log.is_file() else None
    note(event="end", use=use, exit_code=code, error=err, seconds=round(now() - t0, 1), output_sha256=digest, output_tail=out)
    jpath = root / (cfg.get("journal") or "experiments/JOURNAL.md")
    jpath.parent.mkdir(parents=True, exist_ok=True)
    with open(jpath, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"\n## {time.strftime('%Y-%m-%d')} - final evaluation, use {use}\n\n"
                f"- Command: `{' '.join([configured, *extra])}`\n"
                f"- Code: commit {git.get('commit') or 'none'}{' with uncommitted changes' if git.get('dirty') else ''}, "
                f"source hash {prov['source_hash'][:12]}\n"
                + (f"- Reason given for this further use: {args.again}\n" if args.again else "")
                + f"- Exit code {code}{' (' + err + ')' if err else ''}; output in {rel_to(root, log)}, receipt in "
                f"{FINAL_DIR}/receipt.jsonl\n"
                f"- Last line of output: `{(out.strip().splitlines() or [''])[-1][:300]}`\n")
    print(json.dumps(clean({"ok": code == 0, "use": use, "exit_code": code, "error": err, "log": rel_to(root, log),
                            "receipt": f"{FINAL_DIR}/receipt.jsonl", "journal": rel_to(root, jpath), "output_tail": out}),
                     indent=1))
    return 0 if code == 0 else 1


PROBE = r"""
import json, sys, platform, importlib
out = {"python": sys.version.split()[0], "executable": sys.executable}
try:
    from importlib import metadata as md
except Exception:
    md = None
pk = {}
for name in ["torch","torchvision","torchaudio","lightning","pytorch-lightning","transformers","accelerate","peft","trl",
             "datasets","deepspeed","optuna","optuna-dashboard","optuna-integration","trackio","mlflow","wandb",
             "tensorboard","torchmetrics","torchinfo","ray","unsloth","liger-kernel","torchao","numpy","safetensors",
             "tensorflow","keras","jax","flax"]:
    try:
        pk[name] = md.version(name) if md else None
    except Exception:
        pass
out["packages"] = pk
try:
    import torch
    t = {"version": torch.__version__, "cuda_available": torch.cuda.is_available(), "cuda": torch.version.cuda,
         "cudnn": (torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None),
         "devices": [], "mps_available": bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())}
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            p = torch.cuda.get_device_properties(i)
            t["devices"].append({"index": i, "name": p.name, "mem_gb": round(p.total_memory / 1e9, 1),
                                 "capability": f"{p.major}.{p.minor}"})
        try:
            t["bf16_supported"] = torch.cuda.is_bf16_supported()
        except Exception:
            pass
    out["torch"] = t
except Exception as e:
    out["torch_error"] = f"{type(e).__name__}: {e}"
print(json.dumps(out))
"""


def cmd_env(args):
    root = find_root(args.root)
    cfg = load_config(root)
    rel = platform.release().lower()
    info = {
        "root": str(root),
        "os": platform.platform(),
        "wsl": ("microsoft" in rel or "wsl" in rel),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "expctl_python": sys.version.split()[0],
        "expctl_executable": sys.executable,
        "tools": {n: shutil.which(n) for n in ("uv", "pip", "conda", "mamba", "micromamba", "pixi", "poetry", "git",
                                               "nvidia-smi", "nvcc", "tmux", "screen", "docker", "sbatch")},
    }
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    info["ram_gb"] = round(int(line.split()[1]) / 1e6, 1)
                elif line.startswith("MemAvailable"):
                    info["ram_available_gb"] = round(int(line.split()[1]) / 1e6, 1)
    except OSError:
        pass
    g = gpu_info()
    info["gpus"] = g
    if shutil.which("nvidia-smi"):
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                               capture_output=True, text=True, timeout=6)
            info["nvidia_driver"] = (r.stdout.strip().splitlines() or [None])[0]
        except (OSError, subprocess.SubprocessError):
            pass
    fg, fp = disk_free(runs_root(root, cfg))
    info["disk_free_gb"], info["disk_free_pct"] = fg, fp
    head = run_git(root, "rev-parse", "--short", "HEAD", text=True)
    info["git"] = {"head": head.strip() if head else None,
                   "branch": (run_git(root, "rev-parse", "--abbrev-ref", "HEAD", text=True) or "").strip() or None}
    for f in ("uv.lock", "pyproject.toml", "requirements.txt", "environment.yml", "pixi.toml", "poetry.lock", "setup.py"):
        if (root / f).exists():
            info.setdefault("env_files", []).append(f)
    py = args.python
    if py:
        try:
            r = subprocess.run([py, "-c", PROBE], capture_output=True, text=True, timeout=180, cwd=str(root))
            info["interpreter"] = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() \
                else {"error": (r.stderr or r.stdout)[-400:]}
        except (OSError, subprocess.SubprocessError, ValueError, IndexError) as e:
            info["interpreter"] = {"error": f"{type(e).__name__}: {e}"}
    else:
        info["hint"] = "pass --python <project interpreter> (e.g. .venv/bin/python) for framework versions"
    print(json.dumps(clean(info), indent=1))
    return 0


def cmd_selftest(args):
    """Verify the harness is wired up: config, hook registration, guard decisions, session hook, protocol."""
    root = find_root(args.root)
    cfg = load_config(root)
    checks = []

    def add(name, ok, detail="", required=True):
        checks.append({"check": name, "ok": bool(ok), "required": required, "detail": str(detail)[:300]})

    add("config readable", not cfg.get("_config_error"), cfg.get("_config_error") or CONFIG_REL)
    # one registration file per agent the installer set up (its manifest names them; an older install is Claude Code)
    agents = (read_json(root / ".claude" / "nn-training.manifest.json") or {}).get("agents") or ["claude"]
    hook_files = {"claude": (".claude/settings.json", ".claude/settings.local.json"),
                  "codex": (".codex/hooks.json",), "cursor": (".cursor/hooks.json",)}

    def hooks_text(base, agent):
        txt = ""
        for rel in hook_files.get(agent, ()):
            sj = read_json(base / rel)
            if isinstance(sj, dict) and "_error" not in sj:
                txt += json.dumps(sj.get("hooks") or {})
        return txt

    for agent in agents:
        txt = hooks_text(root, agent)
        where = "project settings" if agent == "claude" else hook_files.get(agent, ("?",))[0]
        add(f"guard hook registered in {where}", "nn_guard.py" in txt, f"{agent}: -> .claude/hooks/nn_guard.py")
        add(f"session-status hook registered ({agent})", "nn_session_status.py" in txt,
            f"{agent}: -> .claude/hooks/nn_session_status.py")
    # a session reads the settings of the checkout it starts in, so the seals bind it only where the guard is registered
    sub = (run_git(root, "rev-parse", "--show-prefix", text=True) or "").strip()
    others = [Path(b.split("\n")[0][9:]) / sub for b in
              (run_git(root, "worktree", "list", "--porcelain", text=True) or "").strip().split("\n\n")
              if b.startswith("worktree ") and "\nbare" not in b]
    others = [p for p in others if p.is_dir() and p.resolve() != root.resolve()]
    if "claude" in agents and others:
        bare = [str(p) for p in others if "nn_guard.py" not in hooks_text(p, "claude")]
        add("guard hook registered in the repository's other checkouts", not bare,
            f"{len(bare)} of {len(others)} without it: a Claude Code session started there is not bound by the seals. "
            f"`install.py --target <this project> --worktrees` registers the guard in them (again after you add a "
            f"worktree). First: {bare[0]}" if bare else f"{len(others)} checked", required=False)
    guard = root / ".claude" / "hooks" / "nn_guard.py"
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    env.pop("NN_UNATTENDED", None)  # the canaries below test the attended answers

    def run_guard(text, *flags):
        return subprocess.run([sys.executable, str(guard), *flags], input=text, capture_output=True, text=True,
                              timeout=30, env=env)

    def ask_guard(tool, tool_input):
        payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(root), "session_id": "expctl-selftest",
                   "permission_mode": "default"}
        try:
            r = run_guard(json.dumps(payload))
            return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else "allow"
        except Exception as e:  # noqa: BLE001
            return f"error: {type(e).__name__}: {e}"

    def refuses(name, text, *flags):
        """A refusal for an agent that cannot be asked is exit code 2 with the reason on stderr."""
        try:
            r = run_guard(text, *flags)
            add(name, r.returncode == 2 and r.stderr.strip(), f"exit {r.returncode}: {r.stderr.strip()[:120]}")
        except Exception as e:  # noqa: BLE001
            add(name, False, f"{type(e).__name__}: {e}")

    def literal(pattern):
        lit = re.split(r"[*?\[]", str(pattern).replace("\\", "/"))[0].rstrip("/")
        return lit[2:] if lit.startswith("./") else lit

    if guard.exists():
        got = ask_guard("Bash", {"command": "kill 2147480000"})
        add("guard asks before kill commands", got == "ask", f"decision: {got}")
        refuses("guard refuses hook input it cannot read", "not json")
        kill = {"cwd": str(root), "session_id": "expctl-selftest"}
        if "codex" in agents:
            refuses("guard refuses for Codex what it would ask (kill)", json.dumps(dict(
                kill, hook_event_name="PreToolUse", tool_name="Bash", tool_input={"command": "kill 2147480000"})),
                "--agent", "codex")
        if "cursor" in agents:
            refuses("guard refuses for Cursor what it would ask (kill)", json.dumps(dict(
                kill, hook_event_name="beforeShellExecution", command="kill 2147480000")), "--agent", "cursor")
        sealed = cfg.get("sealed_paths") or []
        if sealed:
            lit = literal(sealed[0]) or str(sealed[0])
            probe = lit if path_matches(lit, sealed) else lit + "/__selftest_probe__"
            got = ask_guard("Read", {"file_path": str(root / probe)})
            add(f"guard denies reading sealed data ({probe})", got == "deny", f"decision: {got}")
            # the guard checks the paths a command names; git prints a tracked file without being given its name
            held = [f for f in (run_git(root, "ls-files", "-z", text=True) or "").split("\0") if path_matches(f, sealed)]
            add("sealed data is not tracked in git", not held, f"{len(held)} tracked file(s), e.g. {held[0]}: git log -p "
                "and git show <commit> print them. Untrack them (git rm --cached, .gitignore), or add '<pattern> -diff' "
                "to .gitattributes" if held else "", required=False)
        else:
            add("sealed test paths configured", False, "set sealed_paths in .claude/nn-training.json (Phase 2)",
                required=False)
        frozen = cfg.get("frozen_paths") or []
        if frozen:
            lit = literal(frozen[0]) or str(frozen[0])
            got = ask_guard("Edit", {"file_path": str(root / lit), "old_string": "a", "new_string": "b"})
            add(f"guard asks before editing frozen evaluator ({lit})", got == "ask", f"decision: {got}")
        else:
            add("frozen evaluator files configured", False, "set frozen_paths (Phase 2)", required=False)
    else:
        add("guard hook script present", False, str(guard))
    sess = root / ".claude" / "hooks" / "nn_session_status.py"
    if sess.exists():
        try:
            r = subprocess.run([sys.executable, str(sess)], input='{"source":"startup"}', capture_output=True,
                               text=True, timeout=60, env=env)
            ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
            add("session hook produces status", "nn-training harness" in ctx, ctx.splitlines()[0] if ctx else "")
        except Exception as e:  # noqa: BLE001
            add("session hook produces status", False, f"{type(e).__name__}: {e}")
    m = cfg.get("metric") or {}
    add("primary metric configured", m.get("name") and m.get("direction") in ("maximize", "minimize"),
        f"{m.get('name')} / {m.get('direction')}", required=False)
    add("final-eval command configured", bool(cfg.get("final_eval_commands")), "", required=False)
    try:  # this also brings receipts of an earlier version into the copy that every checkout shares
        uses, edited = final_uses(root)[:2]
        add("final-evaluation uses on record", edited is None,
            f"{len(uses)} use(s)" + (f"; edited: {rel_to(root, edited)}" if edited else ""), required=False)
    except OSError as e:
        add("final-evaluation uses on record", False, f"{type(e).__name__}: {e}", required=False)
    uses = run_git(root, "grep", "-l", "-E", r"(from|import) runlog", text=True)
    add("training code uses runlog", bool(uses and uses.strip()),
        (uses or "").strip()[:200] or "not found yet (Phase 1)", required=False)
    ok = all(c["ok"] for c in checks if c["required"])
    print(json.dumps(clean({"ok": ok, "root": str(root), "checks": checks}), indent=1))
    return 0 if ok else 1


# ----------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog="expctl", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", help="project root (default: $CLAUDE_PROJECT_DIR or nearest dir with .claude/nn-training.json / .git)")
    sub = ap.add_subparsers(dest="command")

    s = sub.add_parser("status", help="overview of runs/studies/alerts (JSON by default)")
    s.add_argument("--brief", action="store_true", help="short human/LLM-readable text")
    s.add_argument("--json", action="store_true", help="JSON output (default)")
    s.add_argument("--compact", action="store_true", help="single-line JSON")
    s.add_argument("--run", help="details for one run")
    s.add_argument("--no-gpu", action="store_true", help="skip nvidia-smi")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("launch", help="start a background run with provenance and snapshot")
    s.add_argument("--name", required=True)
    s.add_argument("--note", help="one-line hypothesis / purpose (recorded in manifest)")
    s.add_argument("--snapshot", choices=("copy", "none"), help="copy: run from an immutable source copy (default from config)")
    s.add_argument("--deadline", help="soft deadline exposed to the run as EXP_DEADLINE (90m, 6h, 2d or local YYYY-MM-DDTHH:MM)")
    s.add_argument("--grace", help="after deadline+grace the supervisor sends SIGTERM (default 10m)")
    s.add_argument("--gpus", help="comma-separated GPU indices; sets CUDA_VISIBLE_DEVICES and enables contention checks")
    s.add_argument("--seed", type=int)
    s.add_argument("--study")
    s.add_argument("--trial")
    s.add_argument("--tag", action="append", help="key=value (repeatable)")
    s.add_argument("--force", action="store_true", help="launch despite low disk space")
    s.add_argument("--allow-duplicate", action="store_true")
    s.add_argument("--share-gpu", action="store_true")
    s.add_argument("--via", choices=("setsid", "tmux"),
                   help="process detachment: setsid (default) or tmux (survives the Claude Code session ending)")
    s.add_argument("cmd", nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_launch)

    s = sub.add_parser("_supervise")
    s.add_argument("run_dir")
    s.add_argument("--env-file")
    s.set_defaults(fn=cmd_supervise)

    s = sub.add_parser("stop", help="graceful stop of an active run (requires user approval)")
    s.add_argument("run")
    s.add_argument("--wait", help="wait up to this long for exit (e.g. 5m)")
    s.add_argument("--kill-after", help="grace before SIGKILL for this stop (default: kill_after_s from config)")
    s.set_defaults(fn=cmd_stop)

    s = sub.add_parser("resume", help="continue an ended run as a new run (EXP_RESUME_FROM names the old run directory)")
    s.add_argument("run")
    s.add_argument("--note")
    s.add_argument("--deadline", help="as for launch")
    s.add_argument("--grace")
    s.add_argument("--force", action="store_true", help="launch despite low disk space")
    s.add_argument("--allow-duplicate", action="store_true")
    s.add_argument("--share-gpu", action="store_true")
    s.add_argument("--allow-code-change", action="store_true",
                   help="resume although the source differs from what the run was launched with")
    s.set_defaults(fn=cmd_resume)

    s = sub.add_parser("watch", help="block and print one JSON line per run event (for the Monitor tool)")
    s.add_argument("run", nargs="?", default="all")
    s.add_argument("--until", choices=("terminal", "any-terminal", "alert"), default="terminal")
    s.add_argument("--interval", default="30s", help="poll interval (default 30s)")
    s.add_argument("--max-time", default="25m", help="exit after this long (default 25m, under Monitor's 30m cap)")
    s.add_argument("--heartbeat", default="5m", help="emit a progress line at least this often (default 5m)")
    s.set_defaults(fn=cmd_watch)

    s = sub.add_parser("curve", help="downsampled metric series from metrics.jsonl")
    s.add_argument("run")
    s.add_argument("--keys")
    s.add_argument("--points", type=int, default=30)
    s.add_argument("--since-step", type=float, dest="since_step")
    s.add_argument("--compact", action="store_true")
    s.set_defaults(fn=cmd_curve)

    s = sub.add_parser("final-eval", help="run the configured final evaluation once, with a receipt (requires user approval)")
    s.add_argument("--again", metavar="REASON", help="reason for a further use; recorded in the receipt and the journal")
    s.add_argument("--which", type=int, metavar="N", help="which final_eval_commands entry (from 1), when several are configured")
    s.add_argument("args", nargs=argparse.REMAINDER, help="after --: arguments appended to the configured command")
    s.set_defaults(fn=cmd_final_eval)

    s = sub.add_parser("hash", help="source hash + git state of the working tree")
    s.set_defaults(fn=cmd_hash)

    s = sub.add_parser("selftest", help="verify hooks, guard decisions and protocol configuration")
    s.set_defaults(fn=cmd_selftest)

    s = sub.add_parser("env", help="environment report")
    s.add_argument("--python", help="project interpreter to probe for framework/package versions")
    s.set_defaults(fn=cmd_env)

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    return args.fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())
