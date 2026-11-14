"""runlog - tiny run logger for the nn-training harness (stdlib only; torch optional).

Copy this single file into the project (for example tools/runlog.py) and import it
from the training entry point. It writes the run-directory contract that
`expctl status`, the SessionStart hook and the status line read:

    heartbeat.json  liveness, step/epoch, latest metrics, best + last checkpoint
    metrics.jsonl   append-only metric events (one JSON object per line)
    env.json        interpreter / framework / device facts
    config.json     the resolved configuration you pass in
    result.json     final state: completed | failed | pruned | timeout | interrupted | incomplete

Plain PyTorch loop:

    from runlog import RunLog
    with RunLog(config=cfg, seed=cfg["seed"], total_steps=total, metric="val/acc", direction="maximize") as rl:
        for step in range(start_step, total):
            loss = train_step()                       # log Python floats; .item() every step forces a GPU sync
            if step % 50 == 0:
                rl.log(step, epoch=epoch, **{"train/loss": loss, "lr": lr})
            if step % eval_every == 0:
                acc = evaluate()
                rl.log(step, epoch=epoch, **{"val/acc": acc})
                save_checkpoint(rl.path("ckpt", "last.pt")); rl.checkpoint(rl.path("ckpt", "last.pt"), step=step)
                if acc > best:
                    best = acc; save_checkpoint(rl.path("ckpt", "best.pt"))
                    rl.checkpoint(rl.path("ckpt", "best.pt"), step=step, value=acc, is_best=True)
            if rl.should_stop():                      # `expctl stop` or EXP_DEADLINE reached
                save_checkpoint(rl.path("ckpt", "last.pt")); rl.checkpoint(rl.path("ckpt", "last.pt"), step=step)
                break
    # Leaving the block -> "completed"; "interrupted"/"timeout" if the loop stopped because should_stop()
    # returned True; "failed" (with the exception) if one escaped; "pruned" for optuna.TrialPruned.

Optuna objective (one sibling run directory per trial, visible to `expctl status`):

    def objective(trial):
        with RunLog.for_trial(trial, metric="val/acc", direction="maximize", config=params) as rl:
            ...                                       # report() / should_prune() as usual
            return rl.best["value"]                   # the score of the checkpoint you selected

When launched by `expctl launch`, the run directory comes from $EXP_RUN_DIR and the deadline from
$EXP_DEADLINE. Otherwise a new directory is created under <project>/<runs_dir>/.
Adapters (verify in your environment): hf_callback(rl) for transformers.Trainer,
lightning_callback(rl) for Lightning.
"""
from __future__ import annotations

import atexit
import json
import math
import os
import platform
import signal
import socket
import sys
import threading
import time
from pathlib import Path

__all__ = ["RunLog", "hf_callback", "lightning_callback"]
_RESULT_STATES = ("completed", "failed", "pruned", "timeout", "interrupted", "incomplete")
_RESERVED = ("t", "step", "epoch")

# Process-wide state shared by all RunLog instances (one SIGTERM handler, one excepthook, one atexit).
_STOP = {"signal": None, "installed": False, "terms": 0}
_HOOKS = {"installed": False, "uncaught": None}
_LIVE = set()
_STRAY = set()  # temporary files of writes that gave up: removed at once, or with a later write


def _iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts))


def _write_json(path, obj, default=str, tries=1):
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{os.urandom(3).hex()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, default=str)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        for attempt in range(tries):
            try:
                return os.replace(tmp, path)
            except PermissionError:  # Windows: a status poll or a virus scan holds the file for a moment
                if attempt == tries - 1:
                    raise
                time.sleep(0.05)
    except BaseException:
        # the rename was refused to the end, or the write itself failed (a full disk): else every such heartbeat
        # left its temporary file in the run directory
        _STRAY.add(tmp)
        raise
    finally:
        for old in list(_STRAY):
            try:
                os.unlink(old)
            except FileNotFoundError:
                pass
            except OSError:
                continue  # whoever kept the rename from happening still holds it: the next write tries again
            _STRAY.discard(old)


def _to_float(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    item = getattr(v, "item", None)
    if callable(item):
        try:
            return float(item())
        except Exception:  # noqa: BLE001
            return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _jsonable(obj, depth=0):
    if depth > 8:
        return str(obj)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v, depth + 1) for v in obj]
    for attr in ("to_dict", "_asdict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return _jsonable(fn(), depth + 1)
            except Exception:  # noqa: BLE001
                pass
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _jsonable(getattr(obj, k), depth + 1) for k in obj.__dataclass_fields__}
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        return {k: _jsonable(v, depth + 1) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def _proc_start_time(pid):
    try:
        import psutil  # type: ignore

        return psutil.Process(pid).create_time()
    except Exception:  # noqa: BLE001
        pass
    try:
        if os.name == "nt":  # as expctl reads it without psutil: the creation time the system records
            import ctypes
            from ctypes import wintypes

            k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return None
            t = [wintypes.FILETIME() for _ in range(4)]
            ok = k32.GetProcessTimes(h, *[ctypes.byref(x) for x in t])
            k32.CloseHandle(h)
            return ((t[0].dwHighDateTime << 32) | t[0].dwLowDateTime) / 1e7 - 11644473600 if ok else None  # 100 ns from 1601
        with open(f"/proc/{pid}/stat", "r") as f:
            data = f.read()
        ticks = int(data[data.rfind(")") + 2:].split()[19])
        with open("/proc/stat", "r") as f:
            btime = next(int(ln.split()[1]) for ln in f if ln.startswith("btime"))
        return btime + ticks / os.sysconf("SC_CLK_TCK")
    except Exception:  # noqa: BLE001
        return None


def _project_root(root=None) -> Path:
    return Path(root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _runs_dir(root: Path) -> str:
    try:
        with open(root / ".claude" / "nn-training.json", "r", encoding="utf-8") as f:
            return json.load(f).get("runs_dir") or "runs"
    except (OSError, ValueError):
        return "runs"


def _slug(s):
    out = "".join(c if c.isalnum() or c in "._-" else "-" for c in (s or "run")).strip("-.")
    return (out or "run")[:40]


def _install_process_hooks(handle_signals):
    if not _HOOKS["installed"]:
        _HOOKS["installed"] = True
        prev_hook = sys.excepthook

        def hook(et, ev, tb):
            _HOOKS["uncaught"] = f"{et.__name__}: {ev}"[:500]
            prev_hook(et, ev, tb)

        sys.excepthook = hook
        atexit.register(_finalize_all)
    if handle_signals and not _STOP["installed"] and threading.current_thread() is threading.main_thread():
        prev = signal.getsignal(signal.SIGTERM)

        def on_term(signum, frame):
            # First SIGTERM: request a graceful stop (the loop sees should_stop() == True).
            # Second SIGTERM: fall back to the previous/default behaviour (terminate).
            # Counted apart from the flag: `expctl stop` writes stop.json and then signals, and a loop that saw
            # the file first must not take that signal for the second one.
            _STOP["terms"] += 1
            if _STOP["terms"] == 1:
                _STOP["signal"] = _STOP["signal"] or "SIGTERM"
                return
            if callable(prev):
                prev(signum, frame)
            else:
                signal.signal(signal.SIGTERM, signal.SIG_DFL)
                os.kill(os.getpid(), signal.SIGTERM)

        try:
            signal.signal(signal.SIGTERM, on_term)
            if hasattr(signal, "SIGBREAK"):  # Windows: Ctrl+Break in the trainer's own console
                signal.signal(signal.SIGBREAK, on_term)
            _STOP["installed"] = True
        except (ValueError, OSError):
            pass


def _default_enabled():
    """Only the global rank-0 process writes run files in distributed jobs (torchrun, Slurm, MPI, and Lightning's own
    launcher, which gives no RANK: there the rank on the node and the node's rank must both be 0)."""
    def rank(var):
        try:
            return int(os.environ.get(var) or "")
        except ValueError:
            return None

    if rank("RANK") is not None:  # torchrun's global rank decides, whatever an enclosing Slurm step left behind
        return rank("RANK") == 0
    if rank("LOCAL_RANK") or rank("NODE_RANK"):
        return False
    for var in ("SLURM_PROCID", "OMPI_COMM_WORLD_RANK", "PMI_RANK"):
        if rank(var) is not None:
            return rank(var) == 0
    return True


def _finalize_all():
    for rl in list(_LIVE):
        if not rl._finished:
            if _HOOKS["uncaught"]:
                rl.finish("failed", reason=_HOOKS["uncaught"])
            else:
                rl.finish("incomplete",
                          reason="process exited without RunLog.finish() and outside a `with RunLog(...)` block")


class RunLog:
    """Writes heartbeat/metrics/result files for one training run (or one Optuna trial)."""

    def __init__(self, run_dir=None, *, name=None, config=None, seed=None, total_steps=None, metric=None,
                 direction=None, heartbeat_every=15.0, deadline=None, root=None, study=None, trial=None,
                 handle_signals=True, extra=None, enabled=None):
        """enabled=None writes files only on global rank 0; other ranks get a no-op logger whose should_stop()
        still works (all-reduce that flag across ranks so every rank stops at the same step)."""
        self.t0 = time.time()
        self.enabled = _default_enabled() if enabled is None else bool(enabled)
        if seed is None and os.environ.get("EXP_SEED") not in (None, ""):
            try:
                seed = int(os.environ["EXP_SEED"])
            except ValueError:
                seed = os.environ["EXP_SEED"]
        root = _project_root(root)
        env_dir = os.environ.get("EXP_RUN_DIR")
        rd = run_dir or env_dir
        if not rd:
            rid = f"{time.strftime('%Y%m%d-%H%M%S')}-{_slug(name or Path(sys.argv[0] or 'run').stem)}-{os.urandom(2).hex()}"
            rd = root / _runs_dir(root) / rid
        self.dir = Path(rd)
        if self.enabled:
            self.dir.mkdir(parents=True, exist_ok=True)
        same_as_env = bool(env_dir) and Path(env_dir).resolve() == self.dir.resolve()
        self._runner_dir = Path(env_dir) if (env_dir and not same_as_env) else None
        self.run_id = (os.environ.get("EXP_RUN_ID") if same_as_env else None) or self.dir.name
        self.metric = metric
        self.direction = (direction or "").lower() or None
        self.total_steps = total_steps
        self.heartbeat_every = float(heartbeat_every)
        dl = deadline if deadline is not None else os.environ.get("EXP_DEADLINE")
        try:
            self.deadline = float(dl) if dl not in (None, "") else None
        except ValueError:
            self.deadline = None
        self.meta = {"seed": seed, "study": study, "trial": trial, "metric": metric, "direction": self.direction}
        rf = os.environ.get("EXP_RESUME_FROM")  # set by `expctl resume` / `nnremote resume`
        self.resume_from = Path(rf) if rf else None  # run directory to load the last checkpoint from, or None
        if rf:
            self.meta["resume_of"] = Path(rf).name
        self.step = None
        self.epoch = None
        self.latest = {}
        self.best = None
        self.best_seen = None
        self.last_ckpt = None
        self.nonfinite = []
        self.extra = dict(extra or {})
        self._finished = False
        self._stop_observed = False
        self._stop_poll = 0.0
        try:  # a stop.json older than this launch (an earlier life of the directory) is not a request to stop
            self._life = float(os.environ["EXP_LAUNCH_TS"]) if env_dir else self.t0
        except (KeyError, ValueError):
            self._life = self.t0
        self._last_hb = 0.0
        self._rate = []
        self._lock = threading.Lock()
        if not self.enabled:
            self._mfile = None
            _install_process_hooks(handle_signals)
            return
        archived = []
        for fname in ("result.json", "exit.json"):  # resuming in place: keep the old record, but not as current
            old = self.dir / fname
            if old.exists():
                dest = self.dir / f"{old.stem}.prev-{int(self.t0)}.json"
                try:
                    os.replace(old, dest)
                    archived.append(dest.name)
                except OSError:
                    pass
        if archived:
            self.meta["resumed_in_place"] = archived
        self._mfile = open(self.dir / "metrics.jsonl", "a", encoding="utf-8")
        man = self.dir / "manifest.json"
        # tries: a run must not fail to start because a reader (a virus scan, the mirror of a remote run on a
        # Windows target) holds one of these files, or its temporary file, for a moment
        if not man.exists():
            pid = os.getpid()
            _write_json(man, {"schema": "expctl.manifest/v1", "run_id": self.run_id, "name": name,
                              "created_at": _iso(self.t0), "created_ts": self.t0, "pid": pid,
                              "proc_start": _proc_start_time(pid), "host": socket.gethostname(),
                              "cmd": list(sys.argv), "cwd": os.getcwd(), "seed": seed, "study": study,
                              "trial": trial, "launched_by": "runlog"}, tries=40)
        if config is not None:
            _write_json(self.dir / "config.json", _jsonable(config), tries=40)
        _write_json(self.dir / "env.json", self._env(), tries=40)
        _LIVE.add(self)
        _install_process_hooks(handle_signals)
        self.heartbeat(phase="start")

    @classmethod
    def for_trial(cls, trial, *, study_name=None, root=None, **kw):
        """RunLog for one Optuna trial, in a sibling directory '<runs_dir>/<study>-tNNNN'."""
        study_name = study_name or getattr(getattr(trial, "study", None), "study_name", None) or "study"
        env_dir = os.environ.get("EXP_RUN_DIR")
        if env_dir:
            parent = Path(env_dir).parent
        else:
            r = _project_root(root)
            parent = r / _runs_dir(r)
        run_dir = parent / f"{_slug(study_name)}-t{int(trial.number):04d}"
        kw.setdefault("study", study_name)
        kw.setdefault("trial", int(trial.number))
        rl = cls(run_dir=run_dir, root=root, **kw)
        try:
            trial.set_user_attr("run_dir", str(run_dir))
        except Exception:  # noqa: BLE001
            pass
        return rl

    def path(self, *parts):
        """Per-run artifact path inside the run directory (parents created), e.g. rl.path("ckpt", "best.pt").
        Use it for checkpoints so concurrent runs never overwrite each other's files."""
        p = self.dir.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # ------------------------------------------------------------------ logging
    def log(self, step=None, epoch=None, **metrics):
        """Record metrics at a step. Keys like 'train/loss', 'val/acc'. Values: numbers or 0-d tensors."""
        if not self.enabled:
            return
        if step is not None and not isinstance(step, int):
            fs = _to_float(step)
            step = int(fs) if fs is not None and math.isfinite(fs) else None
        t = time.time()
        rec = {"t": round(t, 3), "step": step}
        if epoch is not None:
            rec["epoch"] = epoch if isinstance(epoch, int) else _to_float(epoch)
        is_eval = False
        for k, v in metrics.items():
            fv = _to_float(v)
            if fv is None or k in _RESERVED:
                continue
            rec[k] = fv
            self.latest[k] = fv
            if not math.isfinite(fv) and k not in self.nonfinite:
                self.nonfinite.append(k)
            if k.lower().startswith(("val", "eval", "valid", "dev")):
                is_eval = True
            if k == self.metric and math.isfinite(fv) and self.direction in ("maximize", "minimize"):
                prev = self.best_seen["value"] if self.best_seen else None
                if prev is None or (fv > prev if self.direction == "maximize" else fv < prev):
                    self.best_seen = {"value": fv, "step": step}
        with self._lock:
            if not self._mfile.closed:
                self._mfile.write(json.dumps(rec, default=str) + "\n")
                self._mfile.flush()
        if step is not None:
            self.step = step
            self._rate.append((t, step))
            if len(self._rate) > 64:
                self._rate = self._rate[-64:]
        if epoch is not None:
            self.epoch = rec.get("epoch")
        if is_eval or (t - self._last_hb) >= self.heartbeat_every:
            self.heartbeat()

    def log_dict(self, step, metrics, epoch=None):
        """Like log() but takes a dict (framework logs often contain 'epoch'/'step' keys, which are used/ignored)."""
        metrics = dict(metrics or {})
        if epoch is None:
            epoch = metrics.get("epoch")
        self.log(step, epoch=epoch, **{k: v for k, v in metrics.items() if k not in _RESERVED})

    def checkpoint(self, path, *, step=None, value=None, is_best=False, metric=None):
        """Record a saved checkpoint. With is_best=True it becomes the run's selected checkpoint."""
        if not self.enabled:
            return
        step = self.step if step is None else step
        self.last_ckpt = {"path": str(path), "step": step, "ts": round(time.time(), 3)}
        if is_best:
            self.best = {"metric": metric or self.metric, "value": _to_float(value), "step": step, "ckpt": str(path)}
        self.heartbeat(phase="checkpoint")

    def set_best(self, value, *, step=None, ckpt=None, metric=None):
        if not self.enabled:
            return
        self.best = {"metric": metric or self.metric, "value": _to_float(value),
                     "step": self.step if step is None else step, "ckpt": str(ckpt) if ckpt else None}
        self.heartbeat()

    def heartbeat(self, phase=None, **extra):
        if not self.enabled:
            return
        t = time.time()
        self._last_hb = t
        latest = dict(list(self.latest.items())[:40])
        if self.metric in self.latest:
            latest[self.metric] = self.latest[self.metric]
        hb = {"ts": round(t, 3), "run_id": self.run_id, "pid": os.getpid(), "started_ts": self.t0,
              "step": self.step, "epoch": self.epoch, "total_steps": self.total_steps, "phase": phase or "train",
              "latest": latest, "best": self.best, "best_seen": self.best_seen,
              "last_ckpt": self.last_ckpt, "throughput_steps_per_s": self._throughput(),
              "nonfinite": self.nonfinite, "deadline": self.deadline,
              "stop_requested": _STOP["signal"] is not None, "meta": self.meta}
        if self.total_steps and isinstance(self.step, (int, float)):
            hb["progress"] = round(min(1.0, self.step / float(self.total_steps)), 4)
        mem = self._gpu_mem()
        if mem:
            hb["gpu_mem_gb"] = mem
        if extra or self.extra:
            hb["extra"] = _jsonable({**self.extra, **extra})
        try:
            _write_json(self.dir / "heartbeat.json", hb, default=str)
        except OSError:
            pass
        if self._runner_dir is not None and self._runner_dir.is_dir():
            # keep the launched study runner visibly alive while its trials log to sibling directories
            try:
                _write_json(self._runner_dir / "study_heartbeat.json",
                            {"ts": round(t, 3), "pid": os.getpid(), "study": self.meta.get("study"),
                             "current_trial": self.meta.get("trial"), "trial_run_dir": str(self.dir)})
            except OSError:
                pass

    # ------------------------------------------------------------------ stopping
    def deadline_passed(self):
        return self.deadline is not None and time.time() >= self.deadline

    def _stop_file(self):
        """True when `expctl stop` left a request in the run directory (stop.json) since this launch."""
        for d in filter(None, (self.dir, self._runner_dir)):
            try:
                with open(d / "stop.json", encoding="utf-8") as f:
                    if float(json.load(f).get("requested_ts")) >= self._life:
                        return True
            except (OSError, ValueError, TypeError, AttributeError):
                pass
        return False

    def should_stop(self):
        """True after a stop request (`expctl stop`: stop.json in the run directory, read about once a second, and
        SIGTERM where the platform has it) or once EXP_DEADLINE has passed. Check it every step. A request holds for
        the process, like the signal it stands in for: the runs that follow in it (the trials of a search) stop too."""
        t = time.time()
        if _STOP["signal"] is None and t - self._stop_poll >= 1.0:
            self._stop_poll = t
            if self._stop_file():
                _STOP["signal"] = "stop request"
        stop = _STOP["signal"] is not None or self.deadline_passed()
        if stop:
            self._stop_observed = True
        return stop

    def stop_reason(self):
        if _STOP["signal"]:
            return f"received {_STOP['signal']}"
        if self.deadline_passed():
            return "deadline reached"
        return None

    def finish(self, state="completed", reason=None, metrics=None, **extra):
        """Write result.json once. state: completed|failed|pruned|timeout|interrupted|incomplete."""
        if self._finished or not self.enabled:
            self._finished = True
            return
        self._finished = True
        _LIVE.discard(self)
        state = str(state).lower()
        if state not in _RESULT_STATES:
            reason = f"(unrecognised state {state!r}) {reason or ''}".strip()
            state = "incomplete"
        final = dict(self.latest)
        for k, v in (metrics or {}).items():
            fv = _to_float(v)
            if fv is not None:
                final[k] = fv
                if not math.isfinite(fv) and k not in self.nonfinite:
                    self.nonfinite.append(k)
        t = time.time()
        res = {"state": state, "reason": reason, "ended_ts": round(t, 3), "ended_at": _iso(t),
               "duration_s": round(t - self.t0, 1), "final_step": self.step, "epoch": self.epoch,
               "metrics": final, "best": self.best, "best_seen": self.best_seen, "last_ckpt": self.last_ckpt,
               "nonfinite": self.nonfinite, "meta": self.meta}
        if extra:
            res["extra"] = _jsonable(extra)
        _write_json(self.dir / "result.json", res, tries=40)  # a run must not lose its result to a busy file
        self.heartbeat(phase="finished")
        with self._lock:
            try:
                self._mfile.close()
            except OSError:
                pass

    # ------------------------------------------------------------------ context manager
    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if self._finished:
            return False
        if et is None:
            if self._stop_observed and _STOP["signal"]:
                self.finish("interrupted", reason=self.stop_reason())
            elif self._stop_observed and self.deadline_passed():
                self.finish("timeout", reason="deadline reached")
            else:
                self.finish("completed")
        elif issubclass(et, KeyboardInterrupt):
            self.finish("interrupted", reason="KeyboardInterrupt")
        elif et.__name__ == "TrialPruned":
            self.finish("pruned", reason=str(ev)[:300] or "pruned by Optuna")
        elif self._stop_observed and _STOP["signal"]:
            self.finish("interrupted", reason=f"{self.stop_reason()}; then {et.__name__}: {ev}"[:500])
        elif self._stop_observed and self.deadline_passed():
            self.finish("timeout", reason=f"deadline reached; then {et.__name__}: {ev}"[:500])
        else:
            self.finish("failed", reason=f"{et.__name__}: {ev}"[:500])
        return False

    # ------------------------------------------------------------------ internals
    def _throughput(self):
        if len(self._rate) < 2:
            return None
        (t0, s0), (t1, s1) = self._rate[0], self._rate[-1]
        try:
            if t1 > t0 and s1 > s0:
                return round((s1 - s0) / (t1 - t0), 4)
        except TypeError:
            return None
        return None

    @staticmethod
    def _gpu_mem():
        torch = sys.modules.get("torch")
        if torch is None:
            return None
        try:
            if torch.cuda.is_available() and torch.cuda.is_initialized():
                return {"max_allocated": round(torch.cuda.max_memory_allocated() / 1e9, 2),
                        "reserved": round(torch.cuda.memory_reserved() / 1e9, 2)}
        except Exception:  # noqa: BLE001
            return None
        return None

    def _env(self):
        env = {"python": sys.version.split()[0], "executable": sys.executable, "platform": platform.platform(),
               "host": socket.gethostname(), "pid": os.getpid(), "argv": list(sys.argv),
               "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
               "source_hash": os.environ.get("EXP_SOURCE_HASH")}
        torch = sys.modules.get("torch")
        if torch is not None:
            try:
                env["torch"] = {"version": torch.__version__, "cuda": torch.version.cuda,
                                "cuda_available": torch.cuda.is_available(),
                                "cudnn": torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None,
                                "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                                "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
                                "float32_matmul_precision": torch.get_float32_matmul_precision()}
                if torch.cuda.is_available():
                    env["torch"]["devices"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
            except Exception as e:  # noqa: BLE001
                env["torch_error"] = f"{type(e).__name__}: {e}"
        return env


# ---------------------------------------------------------------------- framework adapters (verify in your env)

def hf_callback(rl):
    """transformers.Trainer callback: logs train/eval metrics, records checkpoints, honours should_stop().
    Set metric= to the Trainer's key, e.g. 'eval_accuracy' or 'eval_loss'."""
    from transformers import TrainerCallback  # type: ignore

    def nums(d):
        return {k: v for k, v in (d or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}

    class RunLogCallback(TrainerCallback):
        def on_train_begin(self, args, state, control, **kwargs):
            if getattr(state, "max_steps", 0):
                rl.total_steps = state.max_steps

        def on_log(self, args, state, control, logs=None, **kwargs):
            vals = nums(logs)
            if vals:
                rl.log_dict(state.global_step, vals, epoch=state.epoch)

        def on_evaluate(self, args, state, control, metrics=None, **kwargs):
            vals = nums(metrics)
            if vals:
                rl.log_dict(state.global_step, vals, epoch=state.epoch)

        def on_save(self, args, state, control, **kwargs):
            path = os.path.join(args.output_dir, f"checkpoint-{state.global_step}")
            best = getattr(state, "best_model_checkpoint", None)
            is_best = bool(best) and os.path.normpath(best) == os.path.normpath(path)
            metric = getattr(args, "metric_for_best_model", None)
            if metric and not metric.startswith("eval_"):
                metric = "eval_" + metric
            rl.checkpoint(path, step=state.global_step, value=getattr(state, "best_metric", None) if is_best else None,
                          is_best=is_best, metric=metric)

        def on_step_end(self, args, state, control, **kwargs):
            if rl.should_stop():
                control.should_save = True
                control.should_training_stop = True

    return RunLogCallback()


def lightning_callback(rl, every_n_steps=50):
    """Lightning callback: logs callback_metrics, mirrors ModelCheckpoint paths (may lag one validation,
    synced again at fit end) and requests a graceful stop when should_stop() is True."""
    try:
        from lightning.pytorch.callbacks import Callback  # type: ignore
    except ImportError:
        from pytorch_lightning.callbacks import Callback  # type: ignore

    def metrics(trainer):
        out = {}
        for k, v in dict(getattr(trainer, "callback_metrics", {}) or {}).items():
            fv = _to_float(v)
            if fv is not None:
                out[k] = fv
        return out

    def sync_ckpts(trainer):
        for cb in getattr(trainer, "checkpoint_callbacks", []) or []:
            best = getattr(cb, "best_model_path", "")
            if best:
                rl.checkpoint(best, step=trainer.global_step, value=_to_float(getattr(cb, "best_model_score", None)),
                              is_best=True, metric=getattr(cb, "monitor", None))
            last = getattr(cb, "last_model_path", "")
            if last:
                rl.last_ckpt = {"path": last, "step": trainer.global_step, "ts": round(time.time(), 3)}

    class RunLogCallback(Callback):
        def on_fit_start(self, trainer, pl_module):
            try:
                est = trainer.estimated_stepping_batches
                if est and math.isfinite(float(est)):
                    rl.total_steps = int(est)
            except Exception:  # noqa: BLE001
                pass

        def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
            if trainer.global_step % max(1, every_n_steps) == 0:
                rl.log_dict(trainer.global_step, metrics(trainer), epoch=trainer.current_epoch)
            if rl.should_stop():
                trainer.should_stop = True

        def on_validation_end(self, trainer, pl_module):
            if getattr(trainer, "sanity_checking", False):
                return
            rl.log_dict(trainer.global_step, metrics(trainer), epoch=trainer.current_epoch)
            sync_ckpts(trainer)

        def on_train_epoch_start(self, trainer, pl_module):
            sync_ckpts(trainer)

        def on_fit_end(self, trainer, pl_module):
            sync_ckpts(trainer)

    return RunLogCallback()
