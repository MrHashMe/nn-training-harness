#!/usr/bin/env python3
"""Optional Claude Code status line for the nn-training harness (stdlib only, fast).

Shows the model, then the most recent active run with progress, the configured metric and ETA,
plus a warning when a run looks stalled. Reads heartbeat files only (no nvidia-smi, no Optuna).
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path


def fmt_secs(s):
    if not isinstance(s, (int, float)) or not math.isfinite(s):
        return "?"
    s = int(max(0, s))
    h, rem = divmod(s, 3600)
    m = rem // 60
    return f"{h}h{m:02d}m" if h else f"{m}m"


def alive(pid):
    try:
        pid = int(pid)
        if os.name == "nt":  # never os.kill(pid, 0) here: on Windows it terminates the process instead of probing it
            import ctypes

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return ctypes.get_last_error() == 5  # access denied: it exists, under another account
            code = ctypes.c_ulong()
            ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
            k32.CloseHandle(h)
            return bool(ok) and code.value == 259  # STILL_ACTIVE
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def read(p):
    for attempt in (1, 2, 3):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError) as e:
            # Windows refuses the open in the instant in which the writer replaces the file. With a single look a
            # live run was missing from the line until the next refresh, when the file was its heartbeat
            if not isinstance(e, PermissionError) or attempt == 3:
                return None
            time.sleep(0.02)


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    model = ((payload.get("model") or {}).get("display_name")) or ""
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or (payload.get("workspace") or {}).get("project_dir")
                or payload.get("cwd") or os.getcwd())
    cfg = read(root / ".claude" / "nn-training.json") or {}
    runs = root / (cfg.get("runs_dir") or "runs")
    metric = (cfg.get("metric") or {}).get("name")
    stale = float(cfg.get("heartbeat_stale_seconds") or 900)
    now = time.time()
    active, stalled = [], 0
    try:
        dirs = sorted((d for d in runs.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))),
                      key=lambda d: d.stat().st_mtime, reverse=True)[:40]
    except OSError:
        dirs = []
    for d in dirs:
        if (d / "result.json").exists() or (d / "exit.json").exists():
            continue
        pid = (read(d / "pid.json") or {}).get("pid") or (read(d / "manifest.json") or {}).get("pid")
        if pid and not alive(pid):
            continue  # process gone: that run is "lost", not running or stalled
        hb = read(d / "heartbeat.json")
        if not hb or not isinstance(hb.get("ts"), (int, float)):
            continue
        age = now - hb["ts"]
        if age > 6 * 3600:
            continue
        if age > stale:
            stalled += 1
            continue
        active.append((d.name, hb))
    prefix = f"[{model}] " if model else ""
    if not active and not stalled:
        print(f"{prefix}train: idle")
        return 0
    parts = [f"train: {len(active)} running"]
    if active:
        rid, hb = active[0]
        prog = hb.get("progress")
        seg = rid[-28:]
        if isinstance(prog, (int, float)):
            seg += f" {100 * prog:.0f}%"
        lat = hb.get("latest") or {}
        if metric and metric in lat:
            v = lat[metric]
            seg += f" {metric}={v:.4g}" if isinstance(v, (int, float)) else f" {metric}={v}"
        thr, step, tot = hb.get("throughput_steps_per_s"), hb.get("step"), hb.get("total_steps")
        if all(isinstance(x, (int, float)) for x in (thr, step, tot)) and thr > 0:
            seg += f" ETA {fmt_secs((tot - step) / thr)}"
        if hb.get("nonfinite"):
            seg += " NaN!"
        parts.append(seg)
    if stalled:
        parts.append(f"{stalled} STALLED")
    print(prefix + " | ".join(parts))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        print("train: status unavailable")
        sys.exit(0)
