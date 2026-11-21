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
        kills the process tree after kill_after_s. The run's supervisor acts on
        stop.json by itself; on Linux the signal goes only to a process that the
        system says was started for this run, whatever the run's records name, and
        elsewhere only to the process that status takes for the run's: the recorded
        number with the recorded start time, which on Windows is asked again before
        the kill. Stopping a run needs the user's explicit approval.
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
        Downsampled metric series + summary stats from RUN/metrics.jsonl, and under
        "findings" what the whole curve shows of the common faults (non-finite values, a
        loss that rose or never moved, a metric that peaked early or was still improving
        at the end, evaluation noise, a slowdown), each with its numbers. With
        --since-step the findings too read the part from that step on only.
  compare --a RUNS --b RUNS [--alpha 0.05] [--tried N] [--effect X] [--unpaired]
        Two groups of ended runs on the configured metric: the difference b - a, its
        interval and p, and a verdict. RUNS: run ids, name=<launch name> or <tag>=<value>,
        comma-separated. Paired by seed where both groups ran the same seeds once each
        (with the differences by seed and how far the two sides move together by seed),
        otherwise, or with --unpaired, Welch's test. It gives no verdict where the frozen
        files differ between the runs or each group has one run, and says how many seeds
        a difference would take. --tried: how many variants were tried before this one
        was picked. It reads the runs' records and writes nothing.
  final-eval [--again REASON] [--which N] [-- ARGS ...]
        Run the final_eval_commands entry of the config, with ARGS appended, from the
        project root and without a shell. Single-use: every use is a row in the
        hash-chained receipt .claude/state/final-eval/receipt.jsonl, written before the
        command starts, and a journal entry; the output goes to a log beside the receipt.
        The rows are also kept in git's common folder, so they outlive a removed worktree.
        A further use is refused unless --again gives the reason, which is recorded.
        Running it needs the user's explicit approval.
  audit-splits [--key FIELD]
        Counts for the splits the config names ("splits": name -> file or folder): records,
        distinct records and a fingerprint per split, and the distinct records each pair of
        splits shares. Records are compared after NFKC, casefold and whitespace collapsing;
        --key compares one field only (the input alone, or a group id). Prints counts, never
        a row, and appends each audit to .claude/state/final-eval/split-audits.jsonl. Exit
        code 1 when two splits share a record. Where the config seals anything, running it
        needs the user's explicit approval.
  hash  Source hash of the working tree (tracked + untracked, not ignored), and one hash
        over the frozen files, each of them read in full for it.
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
import calendar
import collections
import contextlib
import csv
import hashlib
import itertools
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
import statistics
import subprocess
import sys
import time
import unicodedata
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
    "splits": {},
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
        ".claude/state/frozen-hashes.json",
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


def in_env(program):
    """On Windows, the file to hand to Popen as `executable` where Windows would not find the program that a command
    names, or would find another; None where the name is left to the system (elsewhere, a batch file, no such
    file). The command line stays as the caller wrote it.
    A name without a folder: the .exe of that name beside this interpreter. Windows looks for such a name first in
    the folder of the program that is running. In a virtual environment that is the base interpreter, which the
    environment's python.exe only starts: until 20 November 2026 a launched `python train.py` ran in the base
    interpreter, without the environment's packages. Not the first on PATH instead: where the kit was not started by
    PATH's interpreter (the `py` launcher, a full path) that is another program than the one such a command started
    so far.
    A name with a folder: that .exe or .com, seen from the current directory as Windows sees it, `.exe` added to a
    name without an ending. Left to Windows, `venv/Scripts/python`, a relative path with forward slashes, did not
    start where the variable NoDefaultCurrentDirectoryInExePath is set. A batch file is not handed over: cmd.exe,
    which runs it, then no longer takes a quoted path that has a space. Nor is a name whose last part the full path
    does not keep: a dot at its end, by which Windows means the file without an ending, a space or a slash there,
    `.` or `..`. Handed over, `tools\\tool.` started tool.exe, and `tools\\..` the .exe that is named like the
    current directory and lies beside it."""
    folder = os.path.dirname(program)
    if os.name != "nt" or not (folder or sys.executable):
        return None
    exe = os.path.abspath(program) if folder else os.path.join(os.path.dirname(sys.executable), program)
    if os.path.basename(exe) != os.path.basename(program):
        return None
    exe += "" if os.path.splitext(exe)[1] else ".exe"
    return exe if exe.lower().endswith((".exe", ".com") if folder else ".exe") and os.path.isfile(exe) else None


def startable(program, env):
    """Whether a start without a shell, with `env` and from the current directory, finds `program`: `final-eval` asks
    before it records a use. Outside Windows the start reads the PATH of `env`. On Windows it reads the kit's own
    PATH, takes a name without an ending as its .exe and as nothing else, takes a batch file by its full name, and
    leaves out the current directory where NoDefaultCurrentDirectoryInExePath is set (measured 20 November 2026,
    Python 3.8 to 3.14). shutil.which, asked until then, said yes to more: the other endings of PATHEXT, the current
    directory in any case (Python 3.11 and older), a batch file by any path. Then the start failed, and the use was
    recorded."""
    if os.name != "nt":
        return bool(shutil.which(program, path=env.get("PATH")))
    if in_env(program):
        return True
    ext = os.path.splitext(program)[1].lower()
    if os.path.dirname(program):  # what is left to Windows here, and starts: a batch file. Not by a relative path with
        # a forward slash: cmd.exe reads an option there, and where the variable is set Windows does not find the file
        return (ext in (".bat", ".cmd") and bool("/" not in program or os.path.splitdrive(program)[0])
                and os.path.isfile(program))
    # shortcut: Windows also looks beside the running program (in a virtual environment, the base interpreter) and in
    # its own folders, before the PATH; a name that only they hold is refused here. Ask them too once that is met
    dirs = [] if "NoDefaultCurrentDirectoryInExePath" in os.environ else ["."]
    return ext in ("", ".exe", ".com", ".bat", ".cmd") and any(
        d and os.path.isfile(os.path.join(d, program + ("" if ext else ".exe")))
        for d in dirs + os.environ.get("PATH", "").split(os.pathsep))


def read_json(path):
    for attempt in (1, 2, 3):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except (OSError, ValueError, UnicodeDecodeError, RecursionError) as e:  # the last: a file nested too deep
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
    cfg = deep_merge(DEFAULT_CONFIG, raw or {})
    for k in ("sealed_paths", "frozen_paths", "harness_paths"):  # one form of them for every reader: in_project()
        if isinstance(cfg.get(k), list):
            cfg[k] = [in_project(root, p) if isinstance(p, str) else p for p in cfg[k]]
    return cfg


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
    if not sys.platform.startswith("linux"):  # macOS has no /proc, which left the same gap there
        return _ps_start(pid)
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


def _ps_start(pid):
    """A process's start time as `ps` gives it, in whole seconds (same_process allows five). Asked in UTC and in the C
    locale, and read by hand, so that neither a daylight-saving hour nor a locale of this process changes the answer."""
    try:
        out = subprocess.run(["ps", "-o", "lstart=", "-p", str(int(pid))], capture_output=True, text=True, timeout=10,
                             env=dict(os.environ, LC_ALL="C", TZ="UTC")).stdout
        _, mon, day, hms, year = out.split()  # Sat Nov 14 10:23:45 2026
        h, m, s = (int(x) for x in hms.split(":"))
        return float(calendar.timegm((int(year), "JanFebMarAprMayJunJulAugSepOctNovDec".index(mon) // 3 + 1, int(day), h, m, s)))
    except Exception:
        return None


def proc_key(pid):
    """On Linux, what tells a process from a later one with its number whatever the clock does: the id of the boot
    and the process's start in ticks since that boot. The start time above is the boot time plus those ticks, and the
    boot time moves whenever the system clock is set, which a VM's time sync does: once it had been set by five seconds
    in total, a live run read as lost. None elsewhere: Windows and macOS record a start time that stays."""
    try:
        with open(f"/proc/{int(pid)}/stat", "r") as f:
            data = f.read()
        with open("/proc/sys/kernel/random/boot_id", "r") as f:
            return f.read().strip() + ":" + data[data.rfind(")") + 2:].split()[19]
    except Exception:
        return None


def same_process(pid, expected_start, key=None) -> bool:
    if key and proc_key(pid) == key:
        return True
    # Otherwise by the start time, as before the key existed: a record without one (an older record, a vendored
    # runlog.py), a system without one, and a key that differs though the process is the one. A reader inside a time
    # namespace with a boot-time offset sees other ticks, while the boot time plus the ticks reads the same there
    if not is_num(expected_start):
        return True
    actual = proc_start_time(pid)
    if actual is None:
        return True
    return abs(actual - expected_start) < 5.0


def proc_words(pid, what):
    """Linux: the words a process was started with, its command line ("cmdline") or its environment ("environ"). [] when
    they cannot be read, None where there is no /proc to ask (macOS, Windows). A run's records name whatever pid their
    writer likes; these words come from the process's starter, and a run in a sandbox starts no process outside it."""
    if not os.path.isdir("/proc/self"):
        return None
    try:
        with open(f"/proc/{int(pid)}/{what}", "rb") as f:
            return f.read().decode("utf-8", "replace").split("\0")
    except (OSError, TypeError, ValueError):
        return []


def holds_open(pid, path) -> bool:
    """Linux: whether a process has this file open for writing, as a script with a RunLog has its run's metrics file
    (a viewer such as `tail -f` has it open for reading)."""
    want = os.path.realpath(path)
    try:
        fds = os.listdir(f"/proc/{int(pid)}/fd")
    except (OSError, TypeError, ValueError):
        return False
    for n in fds:
        try:
            if os.readlink(f"/proc/{pid}/fd/{n}") == want:
                with open(f"/proc/{pid}/fdinfo/{n}") as f:
                    if int(f.read().split("flags:")[1].split()[0], 8) & 3:  # the access mode: 0 is read-only
                        return True
        except (OSError, IndexError, ValueError):  # closed since the listing
            pass
    return False


def _win_parent(pid):
    """A Windows process's parent as the system records it, or None: psutil's ppid() where psutil is not installed.
    A run that a virtual environment's python.exe started trains in a child of the process the kit knows, and the
    GPU names that child: without its parent, status showed no run on the GPU."""
    try:
        import ctypes

        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return None
        info = (ctypes.c_size_t * 6)()  # PROCESS_BASIC_INFORMATION: six pointer-sized fields, the parent's id the last
        ok = ctypes.windll.ntdll.NtQueryInformationProcess(h, 0, info, ctypes.sizeof(info), None) == 0
        k32.CloseHandle(h)
        return int(info[5]) if ok else None
    except Exception:
        return None


def proc_parent(pid):
    try:
        import psutil  # type: ignore

        return psutil.Process(int(pid)).ppid()
    except Exception:
        pass
    if os.name == "nt":
        return _win_parent(pid)
    try:
        with open(f"/proc/{int(pid)}/stat", "r") as f:
            data = f.read()
        return int(data[data.rfind(")") + 2:].split()[1])
    except Exception:
        return None


def ancestors(pid, depth=25):
    """A process's parent, that one's parent and so on. Windows keeps the number of a parent that has ended, and a
    later process can hold it: one that began after the process below it is not its parent, and the walk ends there.
    Otherwise status put the GPU of a program that belongs to no run on the run whose process got such a number.
    On Windows a clock set back between a parent's start and its child's ends the walk there too: the GPU is then on
    no run, which can miss an alert and raises none."""
    win = os.name == "nt"
    out, cur, born = [], pid, proc_start_time(pid) if win else None
    for _ in range(depth):
        cur = proc_parent(cur)
        if not cur or cur <= 1 or cur in out:
            break
        began = proc_start_time(cur) if win else None
        if born and began and began > born:
            break
        out.append(cur)
        born = began or born
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


# A repository's settings can make git start a program by itself (core.fsmonitor on every status, a hook on every
# change of the index). The kit's own git calls run with the user's rights, outside the agent's session and its
# guard, so they switch both off. Checked with git 2.43 and 2.52: the empty value turns the monitor off
GIT = ["git", "-c", "core.fsmonitor=", "-c", "core.hooksPath=" + os.devnull]


def run_git(root, *args, timeout=30, text=False):
    try:
        r = subprocess.run([*GIT, "-C", str(root), *args], capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace") if text else r.stdout


# ----------------------------------------------------------------------------- path patterns

NOCASE = os.name == "nt" or sys.platform == "darwin"  # filesystems that ignore case: the patterns do too, as the guard's do


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
    return re.compile("^" + out + "$", re.I if NOCASE else 0)


def path_matches(rel: str, patterns):
    """First pattern matching a repo-relative path (a pattern 'a/b' or 'a/b/**' also covers everything below a/b).
    Where the filesystem ignores case (NOCASE), data/Test/x.csv is the file that data/test/** names.
    A path and a pattern may also be full paths (sealed data outside the project): both count without their first
    slash."""
    rel = (rel or "").replace("\\", "/").strip("/")
    if not rel:
        return None
    low = rel.lower() if NOCASE else rel
    for p in patterns or []:
        p2 = os.path.expanduser(str(p).strip()).replace("\\", "/")
        p2 = p2[2:] if p2.startswith("./") else p2.lstrip("/")  # was: /held/** matched no path, rel has no first slash
        base = p2[:-3] if p2.endswith("/**") else p2.rstrip("/")
        b = base.lower() if NOCASE else base
        if _glob_re(p2).match(rel) or low == b or (
                not any(ch in base for ch in "*?[") and low.startswith(b + "/")):
            return p
    return None


def in_project(root, pattern):
    """A path pattern of the config in the one form that every reader takes: `~` written out, and a full path that
    leads into the project as the name it has there (the project's folder by whatever spelling: a link, another
    case, macOS's /private). A full path to another place stays one, and a name in the project stays as written.
    Before, each reader had its own reading: a snapshot, a campaign's worktree and a remote run's archive took a
    folder of the project that was sealed by its full path for another place and held its files, and some readers
    did not write `~` out."""
    s = os.path.expanduser(str(pattern).strip()).replace("\\", "/")
    if not Path(s).anchor:
        return pattern
    head = re.split(r"[*?\[]", s)[0]
    a = (s if head == s else head.rpartition("/")[0]).rstrip("/")
    while True:
        try:
            if os.path.samefile(a + "/", root):
                return s[len(a):].lstrip("/") or pattern
        except (OSError, ValueError):
            pass  # no such folder (yet): the folders above it are asked
        up = os.path.dirname(a).rstrip("/")
        if up == a:
            return s
        a = up


def sealed_links(root, patterns):
    """(real place, name in the project) of each folder on a sealed pattern's way that is, or lies behind, a link to
    another place (data -> a folder on another drive). What lies at the real place is the sealed data, by whatever
    name it is reached: the guard's rule (its links())."""
    out, top = set(), Path(os.path.realpath(root))
    for p in patterns or []:
        name = re.split(r"[*?\[]", str(p).strip().replace("\\", "/"))[0].rstrip("/")
        while name:
            real = Path(os.path.realpath(top / name))
            if real != top / name and real.exists():
                out.add((real, name[2:] if name.startswith("./") else name))
            name = name.rpartition("/")[0]
    return sorted(out, key=lambda x: -len(x[0].parts))


def places(root, p, rel, links=()):
    """The names a file is judged by: its own and, where a link or a junction leads elsewhere, that of the place it
    really lies in (relative to the project when it is inside it), and the name a sealed pattern has for that place
    (`links`, from sealed_links()). A snapshot and a remote run's archive hold what a link leads to, so a link into
    sealed data, or to a credentials file, would otherwise carry it along under another name."""
    real, top = Path(os.path.realpath(p)), Path(os.path.realpath(root))
    try:
        names = {rel, real.relative_to(top).as_posix()}
    except ValueError:
        names = {rel, real.as_posix()}
    return names | {(Path(n) / real.relative_to(r)).as_posix() for r, n in links if r == real or r in real.parents}


def sealed_inside(rel: str, patterns, target=None) -> bool:
    """True if some sealed pattern names a path strictly below directory `rel`. A pattern whose wildcard stands at
    or above that directory (**/test/**, data/*/test/x.csv) is answered from the names below `target`, the
    directory on disk; without a target the answer for such a pattern is True. A full path (the place outside the
    project that a link leads to) is asked about the patterns that are full paths, as path_matches() reads them."""
    full = bool(Path(rel).anchor)
    rel, wild = rel.strip("/"), []
    rel = rel.lower() if NOCASE else rel
    for p in patterns or []:
        p2 = os.path.expanduser(str(p).strip()).replace("\\", "/")
        if full and not Path(p2).anchor:
            continue
        p2 = p2[2:] if p2.startswith("./") else p2.lstrip("/") if full else p2
        p2 = p2.lower() if NOCASE else p2
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
    end = time.monotonic() + secs
    for d, dirs, files in os.walk(target, followlinks=True):
        sub = os.path.relpath(d, target).replace("\\", "/")
        pre = rel if sub == "." else f"{rel}/{sub}"
        if sub.count("/") >= 40 or time.monotonic() > end or any(path_matches(f"{pre}/{n}", patterns) for n in dirs + files):
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


def files_matching(root: Path, patterns, runs=None):
    """Files under root that match the patterns, tracked or not (git-ignored data included). The search for a pattern
    starts at the folder before its first wildcard, which is the project for **/test/**. `runs`, the runs folder
    as the configuration names it, is left out: what the runs write there is not what a campaign protects.
    Files below a folder that is a link are not found: the walk does not follow links.
    A pattern may name a place outside the project (../held/**, a full path, ~/held/**): its files are found under
    the name the pattern gives them, which root / name opens."""
    rels = set((run_git(root, "ls-files", "-z", text=True) or "").split("\0"))
    for p in patterns:
        p2 = os.path.expanduser(str(p).strip()).replace("\\", "/")
        head = re.split(r"[*?\[]", p2)[0]
        lead = p2.rstrip("/") if head == p2 else head.rpartition("/")[0]
        base = root / lead
        if base.is_dir() and (lead or head != p2):
            for d, dirs, files in os.walk(base):
                here = Path(lead) / os.path.relpath(d, base)  # was: relative to root, an error for a full path outside it
                dirs[:] = [x for x in dirs if x not in (".git", "__pycache__", "worktrees") and (here / x).as_posix() != runs]
                rels.update((here / f).as_posix() for f in files)
        elif lead:
            rels.add(lead)
    return sorted(r for r in rels if r and path_matches(r, patterns) and (root / r).is_file()
                  and not finder_file(root / r))


def finder_file(p: Path) -> bool:
    """A folder's view settings, which macOS's Finder writes wherever a person opens a folder: told by the name and by
    the file's first bytes, so that another file given that name stays protected."""
    if p.name != ".DS_Store":
        return False
    try:
        with open(p, "rb") as f:
            return f.read(8) == b"\0\0\0\x01Bud1"
    except OSError:
        return False


def file_digest(p: Path, eol=False):
    """A file's SHA-256. With eol a text file (no NUL byte at its start, as git tells) counts with LF line ends, so
    that a checkout with CRLF gives the same hash."""
    fh, cr, text = hashlib.sha256(), b"", None
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            text = eol and b"\0" not in chunk if text is None else text
            if text:  # a \r that ends a chunk waits for the next one, whose \n it may belong to
                chunk = cr + chunk
                cr = chunk[-1:] if chunk.endswith(b"\r") else b""
                chunk = chunk[:len(chunk) - len(cr)].replace(b"\r\n", b"\n")
            fh.update(chunk)
    fh.update(cr)
    return fh.hexdigest()


def hash_files(root: Path, files, max_bytes, by_size=(), follow=False, eol=False, known=None):
    """One hash over the files. A file over max_bytes, or one named in by_size, counts by its size alone; a link
    counts by where it points, or with follow by the file behind it. eol: as file_digest has it. known: by name,
    the digests of files that are not to be read again."""
    h = hashlib.sha256()
    hashed, size_only = 0, []
    for rel in files:
        p = root / rel
        try:
            if p.is_symlink() and not follow:
                h.update(b"L\0" + rel.encode("utf-8", "surrogateescape") + b"\0" + os.readlink(p).encode() + b"\0")
                continue
            size = p.stat().st_size
            if size > max_bytes or rel in by_size:
                size_only.append(rel)
                h.update(b"S\0" + rel.encode("utf-8", "surrogateescape") + b"\0" + str(size).encode() + b"\0")
                continue
            digest = (known or {}).get(rel) or file_digest(p, eol)
            h.update(b"F\0" + rel.encode("utf-8", "surrogateescape") + b"\0" + digest.encode() + b"\0")
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


FROZEN_READ = 64 << 20
FROZEN_KEPT = ".claude/state/frozen-hashes.json"


def frozen_state(root: Path, cfg, big="read"):
    """The files that match frozen_paths as one hash, or None where nothing is frozen. A run's record keeps it, so
    that a later look can tell whether two runs were made under the same evaluator. The guard asks about a write to
    such a file only where it can name the write; the hash changes whatever made the change. Text counts with LF
    line ends: the same evaluator checked out with CRLF on another machine is no other evaluator.
    Every file counts with its content, and a launch, `expctl hash` and the final evaluation read every file
    (big="read"; 1 GiB takes about half a second from the system's file cache). `expctl status` is called often: for
    it (big="kept") the smallest files are read, FROZEN_READ bytes of them, and a file beyond those is read once and
    again when its size or one of its times has changed, its hash taken from FROZEN_KEPT meanwhile, which every full
    read puts right. big="size" counts a file beyond those by its size alone, which was the rule until 15 November
    2026: the hash that the records of older runs hold.
    shortcut: FROZEN_KEPT lies in the project, so with big="kept" a program that changes a file beyond FROZEN_READ
    and writes the old hash there, or sets the file's times back, is not seen by `status` until the next full read;
    keep the hashes where no run can write if `status` must not miss that."""
    pats = cfg.get("frozen_paths") or []
    files = files_matching(root, pats, cfg["runs_dir"].strip("/")) if pats else []
    if not files:
        return None
    stats, at = {}, time.time()
    for rel in files:
        try:
            stats[rel] = (root / rel).stat()
        except OSError:  # gone since it was listed, or a link to nothing: hash_files counts it as unread
            pass
    left, beyond, known = FROZEN_READ, [], {}
    for size, rel in sorted((stats[f].st_size if f in stats else 0, f) for f in files):
        if size > left:
            beyond.append(rel)
        else:
            left -= size
    if beyond and big != "size":
        kept, keep = read_json(root / FROZEN_KEPT), {}
        for rel in beyond:
            st = stats[rel]
            key, was = [st.st_size, st.st_mtime_ns, st.st_ctime_ns], (kept if isinstance(kept, dict) else {}).get(rel)
            try:  # a kept hash is taken only in a hash's form: any program may have written that file
                known[rel] = (was[1] if big == "kept" and isinstance(was, list) and len(was) == 2 and was[0] == key
                              and isinstance(was[1], str) and re.fullmatch("[0-9a-f]{64}", was[1])
                              else file_digest(root / rel, True))
            except OSError:
                continue  # hash_files counts it as unread
            if at - st.st_mtime > 2:  # written that moment, it may change again under the same time stamp
                keep[rel] = [key, known[rel]]
        if keep != (kept or {}):
            try:
                (root / FROZEN_KEPT).parent.mkdir(parents=True, exist_ok=True)
                write_json_atomic(root / FROZEN_KEPT, keep)
            except OSError:
                pass  # nothing is kept then, and the next call reads the files again
    digest, _hashed, size_only = hash_files(root, files, float("inf"), beyond if big == "size" else (), follow=True,
                                            eol=True, known=known)
    return {"frozen_hash": digest, "frozen_files": len(files), "frozen_size_only": len(size_only)}


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
    copied, to_link, failures, kept_out, here = 0, [], [], [], Path(os.path.realpath(src))
    links = sealed_links(root, sealed)
    for rel in files:
        # by its real place too: a junction or a link to a folder gives the sealed files below it a second name, and
        # git lists the files below a junction one by one
        if sealed and any(path_matches(n, sealed) for n in places(root, root / rel, rel, links)):
            kept_out.append(rel)
            continue
        s, d = root / rel, src / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        try:
            to = Path(os.path.realpath(d.parent / os.readlink(s))) if sealed and s.is_symlink() and s.is_dir() else here
            if here not in (to, *to.parents):  # a link to a folder that would lead out of the snapshot (an absolute
                to_link.append(rel)  # one): linked below, as a git-ignored one is, without the sealed paths under it
            elif s.is_symlink():  # Windows keeps a link to a folder and one to a file apart, and judges by what is there now
                os.symlink(os.readlink(s), d, target_is_directory=s.is_dir())
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
            if name in (runs_rel, ".git") or os.path.lexists(src / name) or excluded_from_provenance(name, cfg):
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
    so training runs cannot reach the test split even through a broad glob). `real` holds the names in the project
    of the place that a link on the way led to (data/latest -> data/2026-01, or a second link to the storage that
    data itself is a link to): the target is judged by those names as well."""
    if _is_link(link):  # never descend through a link: its children are the real files
        return
    if sealed and _is_link(target):
        top, to = Path(os.path.realpath(target.parents[rel.count("/")])), Path(os.path.realpath(target))
        if to == top or to in top.parents:
            failures.append(f"link {rel}: it leads to the project folder or above it, so it would bring the sealed "
                            f"paths into the snapshot under another name")
            return
        real = tuple(places(top, to, rel, sealed_links(top, sealed)) - {rel})
    # A full path (a link's place outside the project) is judged by the patterns that are full paths: a wildcard pattern
    # of the project would seal a link whose storage merely lies below a `test` folder. Until 15 November 2026 such a
    # place was judged by no pattern, so a git-ignored link into data sealed by its full path was linked whole
    names, full = [rel, *(real or ())], [p for p in sealed if Path(os.path.expanduser(str(p).strip())).anchor]
    if any(path_matches(n, full if Path(n).anchor else sealed) for n in names):
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
                           sealed=sealed, kept_out=kept_out, real=real and tuple(f"{r}/{child.name}" for r in real))
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
    alive = bool(pid) and pid_alive(pid) and same_process(pid, pidj.get("proc_start") or man.get("proc_start"),
                                                          (pidj if pidj.get("pid") else man).get("proc_key"))
    # (not for the mirror of a remote run: the pid in its heartbeat belongs to another machine. Nor for a run whose
    # command gave it a process namespace of its own, as the loop's sandbox does: that pid is the namespace's)
    # shortcut: only bubblewrap's flag in the run's command is recognised, not a namespace from docker or unshare;
    # upgrade when RunLog records the namespace it runs in
    if not alive and hb_ok and hb_age is not None and hb_age <= stale and hb.get("pid") and hb.get("pid") != pid \
            and not man.get("remote") and "--unshare-pid" not in (man.get("cmd") or []) and pid_alive(hb["pid"]):
        # a later process (e.g. an in-place resume) owns this run directory now
        pid, alive = hb["pid"], True
    # The supervisor writes the exit record a moment after the process has gone, so while it is there the run has not
    # ended. Only where its start time shows that the pid is still the supervisor's: a pid is given out again
    sup = pidj.get("supervisor_pid")
    sup_up = not alive and pid_alive(sup)
    ending = bool(sup_up and pidj.get("supervisor_key") and proc_key(sup) == pidj["supervisor_key"])
    sup_start = proc_start_time(sup) if sup_up and not ending else None  # the key first, then the time, as same_process
    ending = ending or (sup_start is not None and is_num(pidj.get("started_at"))
                        and abs(sup_start - pidj["started_at"]) < 5)
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
        "frozen_hash": str(man.get("frozen_hash") or "")[:12] or None,
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
                "frozen_hash": r.get("frozen_hash"),
                "note": r.get("note"), "dir": r["dir"]} for r in top[: int(lim.get("top_k", 5))]]
    if any(r["frozen_hash"] for r in top_out):  # a score compares only with scores made under the same frozen files
        def current(big):
            return ((frozen_state(root, cfg, big) or {}).get("frozen_hash") or "")[:12]

        cur = {current("kept")}
        if any(r["frozen_hash"] not in cur for r in top_out if r["frozen_hash"]):
            cur.add(current("size"))  # what a run made before 15 November 2026 holds for the same frozen files
        other = [r["run_id"] for r in top_out if r["frozen_hash"] and r["frozen_hash"] not in cur]
        if other:  # first, so that the cap on alerts below never cuts it
            alerts.insert(0, f"{len(other)} of the top runs (e.g. {other[0]}) were made under other frozen files than "
                             "the project holds now: their scores do not compare with new runs "
                             "(references/validity.md, section 6)")

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
    """(the time the deadline falls at, its seconds where it was given as a duration and else None)"""
    if not s:
        return None, None
    s = s.strip()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smhd])", s, re.I)
    if m:
        secs = float(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2).lower()]
        return now() + secs, secs
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return time.mktime(time.strptime(s, fmt)), None
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
    deadline, deadline_s = parse_deadline(args.deadline)
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
        "deadline_s": deadline_s,
        "grace_s": grace,
        "kill_after_s": float(cfg.get("kill_after_s") or 120),
        "snapshot": {"mode": mode, **prov, **({"src": snap} if snap else {})},
        "launched_by": "expctl",
        "via": args.via or "setsid",
    }
    manifest.update(frozen_state(root, cfg) or {})
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


def keep_awake(pid):
    """On a Mac, hold off idle sleep for as long as the process `pid` lives: a sleeping machine pauses a run while its
    deadline, a campaign's time limit and a rented machine's bill keep counting. The system's own `caffeinate` does it and
    ends by itself when that process does. None on other systems. A closed lid still puts a Mac to sleep."""
    exe = shutil.which("caffeinate") if sys.platform == "darwin" else None
    if not exe:
        return None
    try:
        return subprocess.Popen([exe, "-i", "-w", str(int(pid))], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    except OSError:
        return None


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
    # {run_dir} in a command is this run's folder, which no caller knows before the launch: the loop binds it into the
    # sandbox of its run. The manifest keeps the placeholder, so `resume` fills in the folder of the new run
    cmd = [str(c).replace("{run_dir}", os.path.abspath(run_dir)) for c in cmd]
    log = open(run_dir / "stdout.log", "ab", buffering=0)
    t0, m0 = now(), time.monotonic()
    env = dict(os.environ, EXP_LAUNCH_TS=repr(t0))  # RunLog ignores a stop.json older than this launch
    kw = dict(stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, cwd=cwd, env=env)
    if os.name == "nt":
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW: without it every run opens a console window
    else:
        kw["start_new_session"] = True  # own process group so stop/deadline can signal the whole tree
    try:
        child = subprocess.Popen(cmd, executable=in_env(cmd[0]), **kw)
    except OSError as e:
        write_json_atomic(run_dir / "exit.json", {"returncode": None, "error": f"could not start: {e}",
                                                  "ended_ts": now(), "ended_at": iso(now())})
        return 1
    awake = keep_awake(child.pid)
    write_json_atomic(run_dir / "pid.json", {"pid": child.pid, "pgid": child.pid, "supervisor_pid": os.getpid(),
                                             "started_at": t0, "proc_start": proc_start_time(child.pid),
                                             "proc_key": proc_key(child.pid), "supervisor_key": proc_key(os.getpid()),
                                             "supervisor_start": proc_start_time(os.getpid()),
                                             **({"keep_awake_pid": awake.pid} if awake else {})})
    state = {"stop_at": None, "late_at": None, "why": None, "killed": False}  # the two times: time.monotonic()

    def on_signal(signum, _frame):
        if state["stop_at"] is None:
            state["stop_at"], state["why"] = time.monotonic(), "stop requested"
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
    # Seconds from this start to the deadline. One given as a duration counts from here, so the launch's own reading
    # of the clock is not in it; and the time since is what the system's clock says or the one that is never set,
    # whichever is more, as for a campaign's hours: time asleep still counts, and a clock that was set back gives a
    # run no more time (was: the system's clock alone, and a run that such a clock gave more time and that then
    # ended by itself was scored like any other). The seconds that a run has to end in after its stop count on the
    # clock that is never set alone: one that is set forward does not cut them short while the run saves
    due = man["deadline_s"] if is_num(man.get("deadline_s")) else deadline - t0 if is_num(deadline) else None
    while True:
        try:
            rc = child.wait(timeout=2)
            break
        except subprocess.TimeoutExpired:
            pass
        m = time.monotonic()
        if due is not None and state["late_at"] is None and max(now() - t0, m - m0) > due + grace:
            state["late_at"] = m
            if state["stop_at"] is None:
                state["stop_at"], state["why"] = m, "deadline + grace exceeded"
                signal_leader(child.pid, signal.SIGTERM)
        kill_after = kill_after_default
        req = read_json(run_dir / "stop.json")
        if isinstance(req, dict):
            if finite(req.get("kill_after_s")):
                kill_after = float(req["kill_after_s"])
            # The file is the request on every system. `expctl stop` also signals this process where it can tell which
            # one it is; it cannot from records that the run rewrote, and Windows has no such signal. The folder is
            # this launch's own, so the request's time is not compared with the launch's (was: after a clock that was
            # set back in between, a request that came by the file alone was never taken)
            if state["stop_at"] is None:
                state["stop_at"], state["why"] = m, "stop requested"
                signal_leader(child.pid, signal.SIGTERM)
        # The run can write the request file, so the time that file names does not move the end its deadline sets
        if state["stop_at"] is not None and not state["killed"] and (
                m > state["stop_at"] + kill_after
                or state["late_at"] is not None and m > state["late_at"] + kill_after_default):
            state["killed"] = True
            signal_group(child.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
    if awake:  # it ends with the run by itself; this covers a child that left a process behind under its own pid
        awake.kill()
        awake.wait()
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
    # The supervisor's pid may by now belong to another program (after a restart, or a long time): signal it only
    # while it is the process that the launch recorded. A record without the supervisor's start time (an older
    # launch) has the launch's own, moments after it, as status compares; one with neither is taken as before.
    start = pj.get("supervisor_start") if is_num(pj.get("supervisor_start")) else pj.get("started_at")
    sent = bool(sup) and pid_alive(sup) and same_process(sup, start, pj.get("supervisor_key"))
    # A run can write its own records, so a pid that only they name may be any program of this account. On Linux a
    # signal goes only to a process that the system says was started for this run: the supervisor, and the controller of
    # a remote run, with the run's folder as an argument; a launched command with it in its environment; a script that
    # was run directly (a study's trial too) holds the run's metrics file open. The supervisor acts on the request file
    # by itself, so a run whose records prove nothing is stopped all the same
    here = os.path.realpath(d)

    def names_run(path):
        return bool(path) and os.path.realpath(path) == here

    words = proc_words(sup, "cmdline") if sent else None
    if words is not None:
        sent = bool({"_supervise", "_control"} & set(words)) and any(names_run(w) for w in words)
    via, killed, why = "supervisor", None, None
    if os.name == "nt":
        if not sent:  # no supervisor is left to escalate: give the loop its time to save and exit, then kill the tree
            # A pid is given out again, on Windows soon. The kill after the wait is for the process that status took
            # for this run's a moment ago: by the end of the wait its number may be another program's (was: whatever
            # had the number then, with its whole tree).
            # shortcut: this tells a number that went to another program, not a run that names another program in its
            # own records, which only /proc proves; upgrade when a launch on Windows puts its process into a job object
            born = proc_start_time(pid)

            def still_ours():
                return bool(r.get("alive")) and pid_alive(pid) and proc_start_time(pid) == born

            sent, via = True, "process"
            # these waits count on the clock that is never set, like the supervisor's: one that is set forward does
            # not cut short the seconds a run has to save in (was: the system's clock)
            t_end = time.monotonic() + float(req.get("kill_after_s") or cfg.get("kill_after_s") or 120)
            while still_ours() and time.monotonic() < t_end:
                time.sleep(0.5)
            killed = still_ours() and signal_group(pid, signal.SIGTERM)
    else:
        if sent:
            try:
                os.kill(int(sup), signal.SIGTERM)
            except OSError:
                sent = False
        if not sent:
            env = proc_words(pid, "environ")
            # where there is no /proc to ask (macOS), the process is at least the one that status took for the run's
            # (was: whatever had the recorded number)
            if (r.get("alive") if env is None else any(w.startswith("EXP_RUN_DIR=") and names_run(w[12:]) for w in env)
                    or holds_open(pid, d / "metrics.jsonl")):
                sent, via = signal_leader(pid, signal.SIGTERM), "process"
            else:
                via, why = "file", ("no process that this run's records name is provably the run's own, so none was "
                                    "signalled. The request is in stop.json, which the run's supervisor and RunLog act on")
    out = {"ok": sent, "run_id": r["run_id"], "signal": None if os.name == "nt" or why else "SIGTERM", "via": via,
           "killed": killed or None, **({"error": why} if why else {})}
    if args.wait and (sent or why):
        t_end = time.monotonic() + parse_duration(args.wait, 300)
        while time.monotonic() < t_end:
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

def curve_findings(loss, metric, direction, lname, mname):
    """What a run's whole curve shows of the common faults, each as one sentence with its numbers and what to look at
    next: signs to follow up, not verdicts. loss, metric: [(step, time, value)] of the training loss and of the
    selection metric as the run logged them, either of them None."""
    out, shape = [], []

    def mean(xs):
        return sum(xs) / len(xs)

    def noise(u):  # the scatter of one value around a smooth trend: a second difference has 6 times its variance
        d2 = sorted(abs(u[i - 1] - 2 * u[i] + u[i + 1]) for i in range(1, len(u) - 1))
        return 1.4826 * d2[len(d2) // 2] / math.sqrt(6) if d2 else 0.0

    def at(s, i):
        return f"step {s[i][0]}" if s[i][0] is not None else f"record {i + 1}"

    def broke(s):  # where a series is not finite for the first time, and its values before that
        i = next((i for i, x in enumerate(s or []) if not math.isfinite(x[2])), None)
        return i, [x[2] for x in s[:i]] if i is not None else []

    ok = broke(loss)[1]
    # A blow-up before the first value that is not finite: far above the lowest value, by the measure of what the loss
    # had gained or, where it rose from the first step on and had gained nothing, of where it began
    lo, high = (min(ok), 0.5 * max(ok[0] - min(ok), abs(ok[0]))) if ok else (0, 0)
    quick = len(ok) > 2 and ok[-1] - lo > high > 0
    rose = (lo, ok[-1]) if quick else None  # from where to where the loss climbed, where it did
    L = [x for x in loss or [] if math.isfinite(x[2])]
    if quick:  # the shape below is that of the run before the blow-up, whose few values would stand for a whole tenth
        del L[next(i for i in range(len(ok), -1, -1) if not i or ok[i - 1] - lo <= high):len(ok)]
    n, v = len(L), [x[2] for x in L]
    if n >= 20:
        c = [mean(v[i * n // 10:(i + 1) * n // 10]) for i in range(10)]  # tenths of the run: single steps are noisy
        low, gain, sig = min(c), c[0] - min(c), noise(v)
        far = 4 * sig / math.sqrt(n / 10)  # what two tenths differ by from the scatter of single steps alone
        if gain <= max(0.01 * abs(c[0]), far):  # <=: a gain of exactly 0 belongs here, the next branch divides by it
            up = c[9] - c[0] > max(0.1 * abs(c[0]), far)
            rose = rose or ((c[0], c[9]) if up else None)
            shape.append(f"{lname} rose from the start ({c[0]:.4g} to {c[9]:.4g}): the steps make the model worse. The "
                         "learning rate is far too high, or the sign of the loss or of the update is wrong" if up else
                         f"{lname} never moved (about {c[0]:.4g} throughout): the model does not learn. Check that the "
                         "optimizer steps these parameters and gradients reach them, that the learning rate is not 0 or "
                         "far off, and that inputs and labels line up; a classifier starts near ln(classes)")
        elif c[9] - low > max(0.5 * gain, far) and c.index(low) < 8:
            rose = rose or (low, c[9])
            shape.append(f"{lname} rose again: lowest around {at(L, c.index(low) * n // 10)} ({low:.4g}), {c[9]:.4g} at the "
                         f"end, which gives back {100 * (c[9] - low) / gain:.0f} % of what it had gained. A learning rate "
                         "too high for that stage, no decay, or no gradient clipping")
        jumps = [i for i in range(5, n) for med in [sorted(v[i - 5:i])[2]]
                 if v[i] - med > max(8 * sig, 0.5 * abs(med), 1e-12)]
        jumps = [i for k, i in enumerate(jumps) if not k or i - jumps[k - 1] > 1]  # a jump that lasts counts once
        if jumps and not rose:  # a loss that climbs is said above, and is no single step that went wrong
            i = jumps[0]
            shape.append(f"{lname} jumped {len(jumps)} time(s), first at {at(L, i)} ({sorted(v[i - 5:i])[2]:.4g} to "
                       f"{v[i]:.4g}): single steps that went wrong. Gradient clipping, a lower peak learning rate or a "
                       "longer warmup; or look at the batches of those steps")
        tt = [x for x in L if is_num(x[0]) and is_num(x[1])]
        # the usual pace between two records, so that one long gap (a pause, a sleeping machine) is not a slowdown
        pace = [(q[0] - p[0]) / (q[1] - p[1]) for p, q in zip(tt, tt[1:]) if q[0] > p[0] and q[1] > p[1]]
        k = len(pace) // 3
        if k >= 4:
            r1, r3 = statistics.median(pace[:k]), statistics.median(pace[-k:])
            if r3 < 0.7 * r1:
                shape.append(f"the run slowed down: {r1:.3g} steps/s in its first third, {r3:.3g} in its last. Data "
                             "loading, memory pressure or swapping, another process on the GPU, or thermal throttling")
    # Values that are not finite are said first and read last: whether the loss climbed before it broke is what its
    # shape says too, so the two sentences cannot disagree (was: "one step went wrong" beside "rose again"). A loss
    # that is finite again later did not end there: only a blow-up just before it is a divergence then
    first = {}
    for name, s in ((lname, loss), (mname, metric)) if lname != mname else ((lname, loss),):
        bad, ok = broke(s)
        if bad is None:
            continue
        first[name], back = s[bad][0], any(math.isfinite(x[2]) for x in s[bad:])
        when = f"from {at(s, bad)}, and finite again later" if back else f"from {at(s, bad)} on"
        if name == lname:
            out.append(f"{name} is not finite {when}" + (
                f", after it had risen from {rose[0]:.4g} to {rose[1]:.4g}: the training diverged. A lower learning "
                "rate, a warmup, or gradient clipping" if quick or rose and not back else
                f"; the values before it were ordinary ({ok[-1]:.4g}): one step went wrong. A bad value in a batch, a log "
                "or a division of zero in the loss, or an overflow under mixed precision" if ok else ""))
        else:  # the metric: with a loss that broke no later there is nothing more to say, otherwise the evaluation did it
            gone = is_num(first.get(lname)) and is_num(first[name]) and first[lname] <= first[name]
            out.append(f"{name} is not finite {when}" + (
                f": {lname} was not finite by then" if gone else
                f"; the values before it were ordinary ({ok[-1]:.4g}). Where the training loss is finite at that point, "
                "the fault lies in the evaluation: a division by zero where a class or a batch is empty" if ok else ""))
    out += shape
    M = [x for x in metric or [] if math.isfinite(x[2])]
    n = len(M)
    if n >= 8 and direction in ("maximize", "minimize"):
        u = [x[2] if direction == "maximize" else -x[2] for x in M]  # higher is better from here on
        sig, ib, m = noise(u), max(range(n), key=u.__getitem__), n // 3
        total, last, mid = u[ib] - u[0], mean(u[-m:]), mean(u[-2 * m:-m])
        own = (lambda x: f"{x:.4g}") if direction == "maximize" else (lambda x: f"{-x:.4g}")  # in the metric's own sign
        if ib < 0.7 * (n - 1) and mean(u[max(0, ib - 1):ib + 2]) - last > max(2 * sig, 0.02 * abs(total)):
            after = [x[2] for x in L if is_num(x[0]) and is_num(M[ib][0]) and x[0] >= M[ib][0]]
            fell = len(after) >= 10 and mean(after[-5:]) < mean(after[:5]) - 0.01 * abs(mean(after[:5]))
            out.append(f"{mname} peaked at {at(M, ib)} ({own(u[ib])}) and ended at {own(last)}" + (
                f", while {lname} still fell ({mean(after[:5]):.4g} to {mean(after[-5:]):.4g}): overfitting. Keep that "
                f"checkpoint; the {100 * (1 - ib / (n - 1)):.0f} % of the run after it bought nothing. To go further: "
                "weight decay, dropout, augmentation, or more data" if fell else
                ": it got worse without the training loss falling further, which points at the learning rate late in "
                "the run rather than at overfitting" if len(after) >= 10 else
                ": the checkpoint of that evaluation is the one to keep"))
        elif ib >= n - m and last - mid > max(2 * sig * math.sqrt(2 / m), 0.05 * abs(total)):
            out.append(f"{mname} was still improving when the run ended: the last third of its evaluations gained "
                       f"{abs(last - mid):.3g} and the best value is among the last. A longer run will likely score "
                       "better, so compare runs of equal length only")
        else:
            level, tail, j = last - max(2 * sig, 0.02 * abs(total)), 0.0, n - 1
            for i in range(n - 1, -1, -1):  # the first evaluation from which the average holds the final level
                tail += u[i]
                if tail / (n - i) >= level:
                    j = i
            if 0 < j < 0.67 * (n - 1):
                out.append(f"{mname} reached its final level at {at(M, j)}, {100 * j / (n - 1):.0f} % into the run: "
                           "what came after gained nothing beyond the noise of an evaluation. A shorter run would do, "
                           "or the learning rate is too low to go further")
        if total > 0 and sig > 0.15 * total:
            out.append(f"{mname} scatters by about {sig:.3g} from one evaluation to the next, {100 * sig / total:.0f} % "
                       "of all it gained in the run: the best value is partly a lucky evaluation, and differences of "
                       "that size between checkpoints or runs mean nothing. Evaluate on more examples")
    return out


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
    # the training loss and the selection metric in full, whatever --keys asks for: the findings read the whole curve
    # (from --since-step on, where that is given)
    loss = next((k for k in all_keys if "loss" in k.lower() and not re.search(r"(?i)val|eval|dev|test", k)), None)
    whole = {k: [] for k in (loss, metric) if k in all_keys}
    # A long run's series is thinned to some 20,000 values, so that a log of millions of steps is not held in memory:
    # the findings read tenths and medians, which do not feel it. Kept as they are: the first value that is not finite
    # with the 64 before it, in which a blow-up shows, and the last value, which says whether the series ended finite.
    # shortcut: a jump of one step can fall between the values that are kept, upgrade if single steps of such runs matter
    thin, nth, broke = {k: max(1, all_keys[k] // 20000) for k in whole}, dict.fromkeys(whole, 0), set()
    recent, final = {k: collections.deque(maxlen=64) for k in whole}, {}
    for rec in records():
        st = rec.get("step")
        for k, s in whole.items():
            if is_num(rec.get(k)):
                v, nth[k] = float(rec[k]), nth[k] + 1
                final[k], kept = (st if is_num(st) else None, rec.get("t"), v), nth[k] % thin[k] == 0
                if k not in broke and not math.isfinite(v):
                    broke.add(k)
                    del s[len(s) - sum(was for was, _ in recent[k]):]  # those of the 64 that are in the series already
                    s.extend(x for _, x in recent[k])
                    kept = True
                elif k not in broke:
                    recent[k].append((kept, final[k]))
                if kept:
                    s.append(final[k])
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
    for k, s in whole.items():
        if s and s[-1] is not final[k]:
            s.append(final[k])
    for k in want:
        tv = tail_vals[k]
        if len(tv) >= 4:
            h = len(tv) // 2
            a, b = sum(tv[:h]) / h, sum(tv[h:]) / (len(tv) - h)
            rel = (b - a) / (abs(a) + 1e-12)
            series[k]["last20pct_trend"] = "flat" if abs(rel) < 0.005 else ("rising" if rel > 0 else "falling")
            series[k]["last20pct_rel_change"] = round(rel, 5)
    out = {"run_id": d.name, "metric": metric, "available_keys": sorted(all_keys)[:60], "series": series,
           "loss_series": loss,  # the series that the findings took for the training loss
           "findings": curve_findings(whole.get(loss), whole.get(metric), (cfg.get("metric") or {}).get("direction"),
                                      loss, metric)}
    print(json.dumps(clean(out), indent=None if args.compact else 1))
    return 0


def t_tail(x, df):
    """P(T > x) for Student's t with a whole number of degrees of freedom (the finite series of Abramowitz and
    Stegun 26.7.3 and 26.7.4)."""
    th = math.atan(x / math.sqrt(df))
    c, odd = math.cos(th), df % 2
    term = total = (c if odd else 1.0) if df > 1 else 0.0
    for j in range(odd + 2, df - 1, 2):
        term *= (j - 1) / j * c * c
        total += term
    a = math.sin(th) * total
    return max(0.0, (1 - (2 / math.pi * (th + a) if odd else a)) / 2)  # far out the rounding can go a hair below 0


def t_quant(p, df):
    """The x that Student's t with df degrees of freedom exceeds with probability p (p below a half)."""
    lo, hi = 0.0, 2.0
    while t_tail(hi, df) > p and hi < 1e12:
        hi *= 2
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if t_tail(mid, df) > p else (lo, mid)
    return hi


def cmd_compare(args):
    """Two groups of ended runs on the selection metric: the difference b - a, its interval, and whether it is more
    than the run-to-run noise. It reads the runs' records: nothing is run and nothing is written."""
    root = find_root(args.root)
    cfg = load_config(root)
    name, direction = (cfg.get("metric") or {}).get("name"), (cfg.get("metric") or {}).get("direction")
    if not name or direction not in ("maximize", "minimize"):
        return fail(2, f"metric.name and metric.direction (maximize or minimize) must be set in {CONFIG_REL}")
    if not 0 < args.alpha < 1 or args.tried < 1:
        return fail(2, "--alpha lies between 0 and 1, and --tried is 1 or more")
    if args.alpha / args.tried < 1e-9:  # below it the quantiles are not exact any more, and no count of runs gets there
        return fail(2, "--alpha divided by --tried is below 1e-9: no number of runs holds a level that strict")
    if args.effect is not None and not (finite(args.effect) and args.effect):
        return fail(2, "--effect is the smallest difference that matters: a number other than 0")
    runs, left, warn = scan(root, cfg), [], []

    def group(g, sel):
        """(the runs that a selection names, those of them that can be compared: ended by themselves or at their
        deadline, with a finite value). The others are listed with the reason, never dropped unseen."""
        got = []
        for item in filter(None, (x.strip() for x in sel.split(","))):
            k, eq, val = item.partition("=")
            if eq:
                hit = [r for r in runs if val == (r.get("name") if k == "name" else str(
                    (r.get("tags") if isinstance(r.get("tags"), dict) else {}).get(k)))]
            else:
                one = rel_to(root, resolve_run(root, cfg, item))
                hit = [r for r in runs if r["dir"] == one]
            got += [r for r in hit if r not in got]
        use = [r for r in got if r["state"] in ("completed", "timeout") and finite(r["metric"]["value"])]
        left.extend({"group": g, "run": r["run_id"], "why": f"state {r['state']}" if r["state"] not in (
            "completed", "timeout") else r["metric"].get("why_missing") or f"{name} is not finite"}
            for r in got if r not in use)
        if len(use) < len(got):
            warn.append(f"{len(got) - len(use)} of the {len(got)} runs of {g} are left out (left_out says why): if the "
                        f"change is the reason that they failed or were cut short, {g} is worse than these numbers show")
        return got, use

    (all_a, a), (all_b, b) = group("a", args.a), group("b", args.b)
    twice = [r["run_id"] for r in all_a if r in all_b]
    if twice:
        return fail(2, "in both groups: " + ", ".join(twice[:6]))
    xa, xb = [r["metric"]["value"] for r in a], [r["metric"]["value"] for r in b]
    na, nb = len(xa), len(xb)

    def sig(x):
        return float(f"{x:.6g}") if finite(x) else x

    def side(rs, xs):
        return {"n": len(xs), "mean": sig(statistics.fmean(xs)) if xs else None,
                "sd": sig(statistics.stdev(xs)) if len(xs) > 1 else None,
                "runs": [{"run": r["run_id"], "seed": r.get("seed"), "value": x} for r, x in zip(rs, xs)]}

    def shares(tot, seen):
        """Of all arrangements of an exact test (tot: how far each lies from no difference): the share that lies as
        far as what was seen, and the share that lies as far as any can, which is the smallest p these runs can give.
        Counted, not taken as 2 in all of them: differences of 0 and equal scores make more arrangements lie that far."""
        return [sum(t >= lim * (1 - 1e-9) for t in tot) / len(tot) for lim in (seen, max(tot))]

    out = {"ok": True, "metric": name, "direction": direction, "a": side(a, xa), "b": side(b, xb), "test": None,
           "better": None}
    hashes = sorted({str(r.get("frozen_hash")) for r in a + b})
    for key, lim in (("duration_s", 1.25), ("step", 1.1)):  # an unequal budget is the commonest unfair comparison
        ma, mb = ([statistics.median(x)] if x else [] for x in ([r[key] for r in g if finite(r.get(key)) and r[key] > 0]
                                                               for g in (a, b)))
        if ma and mb and max(ma[0], mb[0]) / min(ma[0], mb[0]) > lim:
            warn.append(f"the groups did not train equally long: median {key} {ma[0]:.4g} (a) against {mb[0]:.4g} (b)")
    if {"completed", "timeout"} <= {r["state"] for r in a + b}:
        warn.append("some of these runs ended at their deadline and others by themselves: they may not have trained "
                    "equally long")
    if not na or not nb:
        out["verdict"] = "nothing to compare: a group has no ended run with a finite value of " + name
    elif len(hashes) > 1:
        out["verdict"] = (f"not comparable: the frozen evaluation files differ between these runs (hashes "
                          f"{', '.join(hashes)}), so their scores are not one measure. Evaluate both groups under one "
                          "state of the frozen files")
    elif na < 2 and nb < 2:
        out["verdict"] = (f"undecided: one run on each side shows no run-to-run spread, so the difference of "
                          f"{xb[0] - xa[0]:+.4g} (b - a) cannot be told from noise. Train each side on 3 seeds or more")
    elif all(max(x) - min(x) <= 1e-9 * max(map(abs, x)) for x in (xa, xb) if len(x) > 1):
        # no spread is not no noise: a seed that the training never reads hides it
        out["verdict"] = (f"undecided: every run of a side scored the same ({xa[0]:.6g} for a, {xb[0]:.6g} for b), so the "
                          "seed changes nothing in these runs and they show no run-to-run spread to hold a difference "
                          "against. Check that the training code reads its seed" + (
                              "" if abs(xb[0] - xa[0]) > 1e-9 * abs(xa[0]) else
                              ", and that the change reaches the training at all: both sides scored the same"))
    else:
        sa, sb = ({str(r.get("seed")): x for r, x in zip(g, xs)} for g, xs in ((a, xa), (b, xb)))
        match = na == nb == len(sa) == len(sb) and set(sa) == set(sb) and "None" not in sa
        paired, corr, by_seed = match and not args.unpaired, None, None
        if match:
            # Pairing gains only where a seed ties the two sides' scores together, and costs half the degrees of freedom
            # where it does not (on the kit's benchmark it did not: references/uncertainty.md section 2)
            ma, mb = statistics.fmean(xa), statistics.fmean(xb)
            den = math.sqrt(sum((x - ma) ** 2 for x in xa) * sum((x - mb) ** 2 for x in xb))
            corr = round(sum((sa[s] - ma) * (sb[s] - mb) for s in sa) / den, 3) if den > 0 else None
        for g, rs, seeds in (("a", a, sa), ("b", b, sb)):
            if sum(r.get("seed") is not None for r in rs) > len(seeds) - ("None" in seeds):
                warn.append(f"a seed occurs more than once in {g}: where the training repeats exactly by seed, such runs "
                            "are one measurement and not several, and the spread is understated")
        if paired:  # the same seeds on both sides, once each: the differences by seed carry the noise
            # seeds are matched as text and listed as numbers where they are whole numbers (was: 10 before 2)
            order = sorted(sa, key=lambda s: (0, float(s), s) if re.fullmatch(r"-?\d+", s) else (1, 0.0, s))
            d = [sb[s] - sa[s] for s in order]
            diff, df, var = statistics.fmean(d), na - 1, statistics.variance(d)
            se, how = math.sqrt(var / na), "paired by seed"
            won = sum((x > 0) == (direction == "maximize") for x in d if x)  # the seeds on which b did better
            by_seed = {"differences": dict(zip(order, map(sig, d))), "sd": sig(math.sqrt(var)), "b_better": won,
                       "a_better": sum(1 for x in d if x) - won}
            if corr is not None and corr < 0.5 and na < 10:
                warn.append(f"compared seed by seed, yet the two sides' scores hardly move together by seed here (r = "
                            f"{corr:.2f}, known poorly from {na} seeds). Where the seed does not tie the two sides together, "
                            "pairing only costs degrees of freedom, and --unpaired compares them as independent groups. "
                            "Choose by what is known of the benchmark (do repeats of one version move together by seed?), "
                            "not by which answer you prefer")
            exact, least = shares([abs(sum(x if m >> i & 1 else -x for i, x in enumerate(d))) for m in range(1 << na)],
                                  abs(sum(d))) if na <= 16 else (None, None)  # every way to give the differences signs
        else:
            diff = statistics.fmean(xb) - statistics.fmean(xa)
            va, vb = (statistics.variance(x) if len(x) > 1 else None for x in (xa, xb))
            if va is None or vb is None:
                va = vb = va if vb is None else vb
                df, how = max(na, nb) - 1, ("one run against a group, whose spread stands for both sides (if the "
                                            "change alters the noise, this is off)")
            else:
                wa, wb = va / na, vb / nb
                # rounded down, as is usual; the 1e-9 is for equal spreads, whose na + nb - 2 can come out a hair below
                df = max(1, int((wa + wb) ** 2 / (wa ** 2 / (na - 1) + wb ** 2 / (nb - 1)) + 1e-9)) if wa + wb else na + nb - 2
                how = "independent groups (Welch's test)" + (
                    ", as --unpaired asks" if match else
                    "" if "None" in sa or "None" in sb else ": the two sides did not run the same seeds once each")
            se, var, count = math.sqrt(va / na + vb / nb), va + vb, math.comb(na + nb, na)
            exact, least = shares([abs((sum(xa) + sum(xb) - s) / nb - s / na)  # every way to deal the runs to two groups
                                   for s in map(sum, itertools.combinations(xa + xb, na))],
                                  abs(diff)) if count <= 50000 else (None, None)
        alpha = args.alpha / args.tried
        same = se <= 1e-9 * max(map(abs, xa + xb))  # the same seeds, and each of them moved by exactly as much
        if same:  # no spread for a t test: the count of seeds alone speaks, as in the exact test, where only all seeds
            # one way and all the other way reach this far. It needs 6 seeds to say anything at 0.05
            se, half, p = 0.0, 0.0, 2 / (1 << na) if abs(diff) > 1e-9 * max(map(abs, xa + xb)) else 1.0
        else:  # the series tells no tail below some 1e-16 from 0: a p that small is given as 1e-15, which it is below
            p, half = max(2 * t_tail(abs(diff) / se, df), 1e-15), t_quant(alpha / 2, df) * se
        better = None if p >= alpha else "b" if (diff > 0) == (direction == "maximize") else "a"
        z, eff = statistics.NormalDist(), abs(diff if args.effect is None else args.effect)
        zz = z.inv_cdf(1 - alpha / 2)
        need = math.ceil((zz + z.inv_cdf(0.8)) ** 2 * var / eff ** 2 + zz ** 2 / (2 if paired else 4)) if eff and se else None
        span = f"{100 * (1 - alpha):g} % interval {diff - half:.4g} to {diff + half:.4g}, p = {p:.2g}"
        if same:
            moved = f"each of the {na} seeds moved by the same {diff:+.4g} (b - a), exact p = {p:.2g}"
            out["verdict"] = (
                f"no difference: b scored exactly what a did on each of the {na} seeds. Check that the change reaches "
                "the training" if p == 1.0 else f"{better} is better: {moved}" if better else
                f"undecided: {moved}, and so few seeds cannot tell that from chance. Run "
                f"{int(math.log2(2 / alpha)) + 1} seeds or more a side")
        elif better:
            out["verdict"] = f"{better} is better: {name} differs by {diff:+.4g} (b - a), {span}" + (
                f", and {better} did better on {by_seed[better + '_better']} of the {na} seeds" if by_seed else "") + (
                f". With so few runs this rests on the noise being roughly normal: an exact test cannot go below "
                f"p = {least:.2g} here" if least is not None and least >= alpha else "")
        else:
            out["verdict"] = (f"no difference shown: {name} differs by {diff:+.4g} (b - a), within the run-to-run "
                              f"noise ({span}). These runs could have shown a difference of {half:.3g} or more" + (
                                  f"; a difference of {eff:.3g} would take about {need} seeds a side" if need else ""))
        if min(na, nb) < 3:
            warn.append("fewer than 3 runs on a side: the spread is known poorly, so the interval is wide")
        out.update(better=better, test={
            "how": how, "diff": sig(diff), "se": sig(se), "df": df, "p": sig(p), "level": sig(1 - alpha),
            "interval": [sig(diff - half), sig(diff + half)], "exact_p": exact and sig(exact), "exact_p_floor": least,
            "seed_correlation": corr, "by_seed": by_seed,
            "seeds_needed": need, "for_difference": sig(eff) if need else None})
    out.update(left_out=left or None, warnings=warn or None)
    print(json.dumps(clean(out), indent=1))
    return 0


def cmd_hash(args):
    root = find_root(args.root)
    cfg = load_config(root)
    _files, is_git, prov = provenance(root, cfg)
    prov["root"] = str(root)
    prov["git_repo"] = is_git
    prov.update(frozen_state(root, cfg, "read") or {"frozen_hash": None})
    print(json.dumps(clean(prov), indent=1))
    return 0


FINAL_DIR = ".claude/state/final-eval"
FINAL_SHARED = "nn-training-final-eval.jsonl"  # in git's common folder, which outlives a removed worktree


@contextlib.contextmanager
def locked(path: Path):
    """The file, open to read and to append bytes, under a lock that other writers of it wait for: on Windows one
    byte far beyond the end of the file, where no reader meets it, elsewhere flock. Where no lock is to be had
    (after about 3 s on Windows, or on a file system without one) the caller goes on without it rather than lose
    its row. Not to be taken a second time inside: flock would wait for itself."""
    with open(path, "ab+") as f:
        if os.name == "nt":
            import msvcrt
            for _ in range(300):  # about 3 s
                try:
                    os.lseek(f.fileno(), 1 << 40, 0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as e:
                    if e.errno != 13:  # 13 (EACCES): another writer holds the lock; anything else: no locking here
                        break
                    time.sleep(0.01)
        else:
            try:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass
        yield f


def chained(path: Path, row):
    """Append a row to a record of the kind ledger_rows() reads. Two writers at the same moment would both read
    the same last line and the chain would break, so the writer holds the file's lock from its read to its write."""
    with locked(path) as f:
        f.seek(0)
        lines = f.read().splitlines()
        prev = hashlib.sha256(lines[-1]).hexdigest() if lines else ""
        f.seek(0, 2)
        f.write(json.dumps(clean(dict(row, prev=prev)), sort_keys=True).encode("utf-8") + b"\n")


def use_key(r):  # the nonce: two rows of the same second are two rows
    return r.get("event"), r.get("use"), r.get("ts"), r.get("nonce")


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
    seen = {use_key(r): r for r in rows if r.get("sub") == sub}
    for p in dict.fromkeys([(root / FINAL_DIR / "receipt.jsonl").resolve()]
                           + [(Path(t) / sub / FINAL_DIR / "receipt.jsonl").resolve() for t in tops]):
        rows, ok = ledger_rows(p)
        edited = edited or (None if ok else p)
        for r in rows:
            if seen.setdefault(use_key(r), r) is r and shared:
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
    program = words[0].strip('"') if words else ""
    if not program or not startable(program, env):
        # a hint: the file Python finds for the name, which is not the same in every version (up to 3.11 it looks in
        # the current folder whatever the variable says, from 3.12 it adds an ending to a name with a folder too)
        there = os.name == "nt" and program and shutil.which(program)
        return fail(2, f"the final evaluation's program was not found: {words[0] if words else '(none)'}"
                       + (". Without a shell Windows starts an .exe, whose ending may be left out where the last part "
                          "of the name has no dot, and a .com or a batch file by its full name (a batch file by a "
                          "relative path: with backslashes); a name without a folder it looks for in the current "
                          "folder only where the variable NoDefaultCurrentDirectoryInExePath is not set. "
                          f"There is {there}"
                          if there else ""))
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

    use, prov, fz = len(before) + 1, provenance(root, cfg)[2], (frozen_state(root, cfg, "read") or {}).get("frozen_hash")
    git, log = prov.get("git") or {}, d / f"{time.strftime('%Y%m%d-%H%M%S')}-use{use}.log"
    nonce = os.urandom(8).hex()
    note(event="start", use=use, nonce=nonce, configured=configured, args=extra, reason=args.again,
         commit=git.get("commit"), dirty=git.get("dirty"), source_hash=prov["source_hash"], frozen_hash=fz,
         log=rel_to(root, log))
    # Two that start at the same moment both found no earlier use. The record that both write keeps its rows in the
    # order of their writing: whoever finds a start there, before its own, that it did not know gives way
    starts = [r for r in ledger_rows(shared or receipt)[0]
              if r.get("event") == "start" and (not shared or r.get("sub") == sub)]
    ahead = set(map(use_key, itertools.takewhile(lambda r: r.get("nonce") != nonce, starts)))
    if len(ahead) > len(before) and not args.again:
        note(event="end", use=use, nonce=nonce, exit_code=None, error="gave way: another use started at the same moment")
        return fail(2, "The final evaluation is single-use, and another one was started at the same moment: that one "
                       "runs, and this one gave way before it looked at anything. The receipt records both.",
                    uses=len(ahead))
    t0, err = now(), None
    try:
        with open(log, "wb") as f:  # Windows takes the command line as one string; elsewhere it is a word list
            code = subprocess.run(rest + " " + subprocess.list2cmdline(extra) if os.name == "nt" else words + extra,
                                  executable=in_env(program), cwd=str(root), env=env,
                                  stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT).returncode
    except OSError as e:
        code, err = None, f"could not start: {e}"
    out = tail_bytes(log, 2000)
    digest = hashlib.sha256(log.read_bytes()).hexdigest() if log.is_file() else None
    note(event="end", use=use, nonce=nonce, exit_code=code, error=err, seconds=round(now() - t0, 1), output_sha256=digest,
         output_tail=out)
    jpath = root / (cfg.get("journal") or "experiments/JOURNAL.md")
    jpath.parent.mkdir(parents=True, exist_ok=True)
    with open(jpath, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"\n## {time.strftime('%Y-%m-%d')} - final evaluation, use {use}\n\n"
                f"- Command: `{' '.join([configured, *extra])}`\n"
                f"- Code: commit {git.get('commit') or 'none'}{' with uncommitted changes' if git.get('dirty') else ''}, "
                f"source hash {prov['source_hash'][:12]}, frozen files {fz[:12] if fz else 'none configured'}\n"
                + (f"- Reason given for this further use: {args.again}\n" if args.again else "")
                + f"- Exit code {code}{' (' + err + ')' if err else ''}; output in {rel_to(root, log)}, receipt in "
                f"{FINAL_DIR}/receipt.jsonl\n"
                f"- Last line of output: `{(out.strip().splitlines() or [''])[-1][:300]}`\n")
    print(json.dumps(clean({"ok": code == 0, "use": use, "exit_code": code, "error": err, "log": rel_to(root, log),
                            "receipt": f"{FINAL_DIR}/receipt.jsonl", "journal": rel_to(root, jpath), "output_tail": out}),
                     indent=1))
    return 0 if code == 0 else 1


# ----------------------------------------------------------------------------- split audit

SPLIT_AUDITS = FINAL_DIR + "/split-audits.jsonl"  # beside the final evaluation's receipt, under the same protection
SPLIT_FORM = "NFKC, casefold, whitespace collapsed"
ROW_FILES = {".jsonl": "json", ".ndjson": "json", ".csv": ",", ".tsv": "\t", ".txt": "line"}
# Many records in one file that the standard library cannot read one by one. Counted whole, such a file would
# report that nothing is shared without a look at a single record.
PACKED = (".parquet", ".arrow", ".feather", ".h5", ".hdf5", ".npz", ".tfrecord", ".lmdb", ".mdb", ".sqlite", ".db",
          ".zip", ".tar", ".gz", ".bz2", ".xz", ".zst")


def split_digests(path: Path, key=None):
    """(one digest per record, records per kind, rows without `key`) for a split: a file, or every file below a
    folder (links followed, names that start with a dot left out). A .jsonl row counts by its parsed value with
    sorted keys, a .csv or .tsv row by its cells (the first row is the header), a .txt file by its lines, any other
    file whole, by its bytes. Text is compared in the form SPLIT_FORM names. key: only that field or column of each
    row. ValueError: a file that packs records the standard library cannot read, or one without fields where a key
    is asked for."""
    csv.field_size_limit(2 ** 31 - 1)  # a long text column is one field
    files = [path]
    if path.is_dir():
        files = []
        for d, dirs, names in os.walk(path, followlinks=True):
            if os.path.relpath(d, path).count(os.sep) >= 40:
                raise ValueError(f"{d}: more than 40 folders deep (a link that leads back up?)")
            dirs[:] = [x for x in dirs if not x.startswith(".")]
            files += [Path(d) / n for n in names if not n.startswith(".")]
    out, units, without = [], {}, 0

    def add(kind, text):
        text = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        out.append(hashlib.sha256(text.encode("utf-8", "backslashreplace")).digest()[:16])
        units[kind] = units.get(kind, 0) + 1

    for f in files:
        ext = f.suffix.lower()
        kind = ROW_FILES.get(ext)
        if ext in PACKED:
            raise ValueError(f"{f.name}: a {ext} file packs many records, and the standard library cannot read them one "
                             "by one. Audit it with a script that uses the project's own loader (references/data.md, "
                             "section 2)")
        if key is not None and kind not in ("json", ",", "\t"):
            raise ValueError(f"{f.name}: --key needs rows with fields (.jsonl, .csv or .tsv)")
        if kind is None:
            h = hashlib.sha256()
            with open(f, "rb") as fh:
                for block in iter(lambda: fh.read(1 << 20), b""):
                    h.update(block)
            out.append(h.digest()[:16])
            units["files"] = units.get("files", 0) + 1
            continue
        with open(f, encoding="utf-8", errors="replace", newline="") as fh:
            if kind == "line":
                for line in fh:
                    if line.strip():
                        add("lines", line)
            elif kind == "json":
                for line in fh:
                    if not line.strip():
                        continue
                    try:
                        v = json.loads(line)
                    except ValueError:
                        v = line
                    if key is not None:
                        if not isinstance(v, dict) or key not in v:
                            without += 1
                            continue
                        v = v[key]
                    add("rows", v if isinstance(v, str) else json.dumps(v, sort_keys=True, ensure_ascii=False))
            else:
                rows = csv.reader(fh, delimiter=kind)
                head = next(rows, None) or []
                if key is not None and key not in head:
                    raise ValueError(f"{f.name}: its first row names no column {key!r}")
                at = head.index(key) if key is not None else None
                for row in rows:
                    if not row:
                        continue
                    if at is None:
                        add("rows", json.dumps(row, ensure_ascii=False))
                    elif at < len(row):
                        add("rows", row[at])
                    else:
                        without += 1
    return out, units, without


def cmd_audit_splits(args):
    """Per split the records and the distinct ones, per pair of splits the distinct records both hold. Counts and
    fingerprints only, never a row: where a split is sealed the guard asks the user, and each audit is recorded."""
    root = find_root(args.root)
    cfg = load_config(root)
    splits = cfg.get("splits")
    if not isinstance(splits, dict) or not splits:
        return fail(2, f'{CONFIG_REL} names no splits. Add them there, for example "splits": {{"train": '
                       '"data/train.jsonl", "val": "data/val.jsonl", "test": "data/test"}} (a file or a folder each, '
                       "from the project root). That file belongs to the harness: the user edits it or approves the edit.")
    out, sets = {}, {}
    for name, rel in splits.items():
        p = Path(os.path.expanduser(str(rel)))
        try:
            if not (root / p).exists():
                raise ValueError("the path does not exist")
            digs, units, without = split_digests(root / p, args.key)
            if not digs:
                raise ValueError("no records" + (f" with the field {args.key!r}" if args.key else ""))
        except (ValueError, OSError, csv.Error) as e:
            return fail(2, f"split {name!r} ({rel}): {e}")
        # shortcut: one digest per record stays in memory (about 150 bytes each), fine for millions of records;
        # a larger split needs its digests sorted on disk
        sets[name] = set(digs)
        out[name] = {"path": str(rel), "records": len(digs), "unique": len(sets[name]), "counted": units,
                     "fingerprint": hashlib.sha256(b"".join(sorted(digs))).hexdigest()}
        if without:
            out[name]["rows_without_key"] = without
    names = list(sets)
    pairs = [{"splits": [a, b], "shared": len(sets[a] & sets[b])} for i, a in enumerate(names) for b in names[i + 1:]]
    res = {"ok": not any(p["shared"] for p in pairs), "form": SPLIT_FORM, "key": args.key, "splits": out, "shared": pairs}
    rec = root / SPLIT_AUDITS
    rec.parent.mkdir(parents=True, exist_ok=True)
    chained(rec, dict(res, ts=iso(now())))
    print(json.dumps(clean(dict(res, record=SPLIT_AUDITS, note="exact matches in that form: a lower bound, because a copy "
                                "that differs in more than case, spacing or Unicode form is not found")), indent=1))
    return 0 if res["ok"] else 1


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

# What training code relies on for speed, each tried in a process of its own with a time limit: a wheel that does
# not fit the GPU or its driver ends the interpreter instead of raising (seen with a cu132 build in WSL2), and a
# kernel that is missing gives way to a slow one without a word. Rows: name, needs a CUDA device, seconds, code.
FAST_PATHS = [
    ("cuda", True, 120, """
import torch
x = torch.randn(256, 256, device="cuda")
assert bool(torch.isfinite((x @ x).sum())), "a matrix product on the GPU gave no finite number"
torch.cuda.synchronize()
"""),
    ("bf16_autocast", True, 120, """
import torch
x = torch.randn(256, 256, device="cuda")
with torch.autocast("cuda", dtype=torch.bfloat16):
    y = x @ x
torch.cuda.synchronize()
assert y.dtype == torch.bfloat16 and bool(torch.isfinite(y.float()).all()), "bf16 autocast gave a wrong type or value"
"""),
    ("flash_attention", True, 120, """
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
q = torch.randn(2, 4, 64, 32, device="cuda", dtype=torch.bfloat16)
with sdpa_kernel(SDPBackend.FLASH_ATTENTION):  # no other kernel may answer
    torch.nn.functional.scaled_dot_product_attention(q, q, q, is_causal=True)
torch.cuda.synchronize()
"""),
    ("fused_adamw", True, 120, """
import torch
m = torch.nn.Linear(64, 64).cuda()
opt = torch.optim.AdamW(m.parameters(), lr=1e-3, fused=True)
m(torch.randn(8, 64, device="cuda")).sum().backward()
opt.step()
torch.cuda.synchronize()
"""),
    ("compile", False, 300, """
import time, torch
dev = "cuda" if torch.cuda.is_available() else "cpu"
m = torch.nn.Sequential(torch.nn.Linear(64, 64), torch.nn.GELU(), torch.nn.Linear(64, 8)).to(dev)
x = torch.randn(16, 64, device=dev)
t = time.time()
y = torch.compile(m)(x)
assert torch.allclose(y, m(x), atol=1e-4), "the compiled module's output differs from eager"
print(f"{dev}, first call {time.time() - t:.0f} s")
"""),
]


def fast_paths(py, root, cuda):
    """What each FAST_PATHS row did in the interpreter `py`: "ok", "failed: <error>", "crashed: <exit code>",
    "timeout ..." or "skipped ...". `cuda`: what that interpreter's torch said about a CUDA device (None: unknown)."""
    out = {}
    for name, needs_cuda, limit, code in FAST_PATHS:
        if needs_cuda and cuda is False:
            out[name] = "skipped: torch reports no CUDA device"
            continue
        try:
            r = subprocess.run([py, "-c", code], capture_output=True, text=True, errors="replace", timeout=limit,
                               cwd=str(root))
        except subprocess.TimeoutExpired:
            out[name] = f"timeout after {limit} s"
            continue
        except OSError as e:
            out[name] = f"failed: {type(e).__name__}: {e}"
            continue
        said = ((r.stdout or "").strip().splitlines() or [""])[-1][:300]
        lines = (r.stderr or "").strip().splitlines()  # the exception's own line, not a hint that follows it
        err = ([x for x in lines if re.match(r"[A-Za-z_][\w.]*: ", x)] or lines or [""])[-1][:300]
        if r.returncode == 0:
            out[name] = f"ok ({said})" if said else "ok"
        elif r.returncode < 0 or r.returncode > 255:  # ended by a signal, or by a Windows exception such as 0xC0000005
            out[name] = f"crashed: exit code {r.returncode}" + (f" (0x{r.returncode:08X})" if r.returncode > 255 else "")
        else:
            out[name] = "failed: " + (err or said or f"exit code {r.returncode}")
    return out


# Dated advice about installed versions; the reference each row names gives the source. Rows: package, first
# version affected, first version fixed, what is wrong, where to read.
ADVISORIES = [
    ("datasets", (0, 0, 0), (5, 2, 0), "runs code when a pickle loads (CVE-2026-57845)",
     "references/data.md, checked 2026-11-11"),
    ("torch", (2, 13, 0), (2, 15, 0), "torch.compile with dropout and activation checkpointing can give silently "
     "wrong gradients (pytorch issue 198333)", "references/performance.md, checked 2026-11-11"),
]


def advisories(packages):
    """The ADVISORIES rows that apply to these installed versions, one sentence each."""
    out = []
    for name, first, fixed, what, where in ADVISORIES:
        ver = (packages or {}).get(name)
        v = (tuple(int(x) for x in re.findall(r"\d+", ver or "")[:3]) + (0, 0, 0))[:3]
        if ver and first <= v < fixed:
            out.append(f"{name} {ver}: {what}; fixed in {'.'.join(map(str, fixed))} ({where})")
    return out


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
    if sys.platform == "darwin":  # no /proc and no nvidia-smi: the chip's one GPU shares this memory with the processor
        for key, name in (("ram_gb", "hw.memsize"), ("chip", "machdep.cpu.brand_string")):
            try:
                v = subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=6).stdout.strip()
                info[key] = round(int(v) / 2**30, 1) if key == "ram_gb" else v or None
            except (OSError, ValueError, subprocess.SubprocessError):
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
    py = args.python and (in_env(args.python) or args.python)
    if py:
        try:
            # a path after --python is read from the folder the command is typed in, as Windows reads it. Until
            # 21 November 2026 the start below, which is given the project root, read it from there elsewhere
            if os.name != "nt" and os.path.dirname(py) and not os.path.isabs(py):
                py = os.path.join(os.getcwd(), py)
            r = subprocess.run([py, "-c", PROBE], capture_output=True, text=True, timeout=180, cwd=str(root))
            info["interpreter"] = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() \
                else {"error": (r.stderr or r.stdout)[-400:]}
        except (OSError, subprocess.SubprocessError, ValueError, IndexError) as e:
            info["interpreter"] = {"error": f"{type(e).__name__}: {e}"}
        if args.probe:  # not beside a live run: it would share the GPU with it
            live = [r["run_id"] for r in scan(root, cfg) if r["state"] in ACTIVE_STATES]
            info["interpreter"]["fast_paths"] = {"skipped": f"a run is live ({', '.join(live[:3])}): try when it has ended"} \
                if live else fast_paths(py, root, (info["interpreter"].get("torch") or {}).get("cuda_available"))
        warn = advisories(info["interpreter"].get("packages"))
        if warn:
            info["warnings"] = warn
    else:
        info["hint"] = ("pass --python <project interpreter> (e.g. .venv/bin/python) for framework versions, "
                        "and --probe to try the fast paths there")
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
    inst = (read_json(root / ".claude" / "nn-training.manifest.json") or {}).get("files")
    if isinstance(inst, dict) and inst:
        def as_written(rel):  # install.py hashes a file with its line endings normalised
            try:
                return hashlib.sha256((root / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == inst[rel]
            except OSError:
                return False

        off = sorted(rel for rel in inst if not as_written(rel))
        add("kit files are as the installer wrote them", not off,
            f"{len(off)} of {len(inst)} differ or are missing, e.g. {off[0]}: unless somebody edited them on purpose, "
            "run install.py again (it keeps a copy of a file that was edited)" if off else f"{len(inst)} files",
            required=False)
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
    s.add_argument("--grace", help="after deadline+grace the supervisor sends SIGTERM (default 10m). A deadline given as a "
                                "duration counts from the run's start, by the system's clock or by the one that "
                                "is never set, whichever is more")
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

    s = sub.add_parser("compare", help="two groups of ended runs on the selection metric: the difference, its interval "
                                       "and whether it is more than run-to-run noise")
    s.add_argument("--a", required=True, help="the baseline's runs: run ids, name=<launch name> or <tag>=<value>, comma-separated")
    s.add_argument("--b", required=True, help="the change's runs, named the same way")
    s.add_argument("--alpha", type=float, default=0.05, help="the error rate of the verdict (default 0.05)")
    s.add_argument("--tried", type=int, default=1,
                   help="how many variants were tried before this one was picked: the rate is divided by it")
    s.add_argument("--effect", type=float, help="the smallest difference that matters, for the number of seeds it would take")
    s.add_argument("--unpaired", action="store_true",
                   help="compare as independent groups even where both ran the same seeds once each: for a benchmark on "
                        "which the seed does not tie the scores of two versions together")
    s.set_defaults(fn=cmd_compare)

    s = sub.add_parser("final-eval", help="run the configured final evaluation once, with a receipt (requires user approval)")
    s.add_argument("--again", metavar="REASON", help="reason for a further use; recorded in the receipt and the journal")
    s.add_argument("--which", type=int, metavar="N", help="which final_eval_commands entry (from 1), when several are configured")
    s.add_argument("args", nargs=argparse.REMAINDER, help="after --: arguments appended to the configured command")
    s.set_defaults(fn=cmd_final_eval)

    s = sub.add_parser("audit-splits", help="count the records that the configured splits share: counts only, never a "
                                            "row (requires user approval where the config seals anything)")
    s.add_argument("--key", metavar="FIELD", help="compare only this field of each .jsonl row or this column of each "
                                                  ".csv/.tsv row: the input alone, or a group id")
    s.set_defaults(fn=cmd_audit_splits)

    s = sub.add_parser("hash", help="source hash + git state of the working tree")
    s.set_defaults(fn=cmd_hash)

    s = sub.add_parser("selftest", help="verify hooks, guard decisions and protocol configuration")
    s.set_defaults(fn=cmd_selftest)

    s = sub.add_parser("env", help="environment report")
    s.add_argument("--python", help="project interpreter to probe for framework/package versions")
    s.add_argument("--probe", action="store_true",
                   help="with --python: try CUDA, bf16 autocast, flash attention, fused AdamW and torch.compile there, "
                        "each in a process of its own (minutes at most; not while a run is live)")
    s.set_defaults(fn=cmd_env)

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    return args.fn(args) or 0


if __name__ == "__main__":
    sys.exit(main())
