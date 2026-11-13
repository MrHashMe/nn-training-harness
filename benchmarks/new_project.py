#!/usr/bin/env python3
"""Create a fresh git project from a benchmark task and, unless --no-kit is given, install the kit into it.

    python benchmarks/new_project.py TARGET [--task charlm] [--agents claude] [--python-cmd PY] [--no-kit]
                                            [--kit-dir DIR]

--kit-dir installs another checkout of the kit (for example an older version, to compare against); its
install.py is called with --target and --python-cmd only, and the task's settings are merged into the config
it wrote. Standard library only; writes only inside TARGET.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def git(target, *args):
    return subprocess.run(["git", "-C", str(target), *args], capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target")
    ap.add_argument("--task", default="charlm")
    ap.add_argument("--agents", default="claude")
    ap.add_argument("--python-cmd", default=sys.executable.replace("\\", "/"),
                    help="interpreter that runs the kit and the training (default: the one running this script)")
    ap.add_argument("--no-kit", action="store_true")
    ap.add_argument("--kit-dir", help="kit checkout to install instead of this one")
    a = ap.parse_args()
    task, target = HERE / a.task, Path(a.target).resolve()
    if not (task / "nn-training.task.json").is_file():
        sys.exit(f"new_project: no task named '{a.task}' under {HERE}")
    if target.exists() and any(target.iterdir()):
        sys.exit(f"new_project: {target} exists and is not empty")
    shutil.copytree(task, target, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("nn-training.task.json", "__pycache__", "out", "runs"))
    git(target, "init", "-q")
    if not git(target, "config", "user.email").stdout.strip():  # a repository-local identity, nothing global
        git(target, "config", "user.name", "benchmark")
        git(target, "config", "user.email", "benchmark@localhost")
    if not a.no_kit:
        kit = Path(a.kit_dir).resolve() if a.kit_dir else HERE.parent
        cmd = [sys.executable, str(kit / "install.py"), "--target", str(target), "--python-cmd", a.python_cmd]
        if not a.kit_dir:
            cmd += ["--agents", a.agents]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"new_project: install.py failed:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
        cfg_path = target / ".claude" / "nn-training.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        py = f'"{a.python_cmd}"' if " " in a.python_cmd else a.python_cmd
        over = json.loads((task / "nn-training.task.json").read_text(encoding="utf-8"))
        over["final_eval_commands"] = [c.replace("{python}", py) for c in over["final_eval_commands"]]
        for k, v in over.items():
            cfg[k] = {**cfg[k], **v} if isinstance(cfg.get(k), dict) and isinstance(v, dict) else v
        with open(cfg_path, "w", encoding="utf-8", newline="\n") as f:  # Path.write_text takes newline only from 3.10
            f.write(json.dumps(cfg, indent=2) + "\n")
    git(target, "add", "-A")
    r = git(target, "commit", "-q", "-m", f"{a.task} benchmark project" + ("" if a.no_kit else " with the nn-training kit"))
    if r.returncode != 0:
        sys.exit(f"new_project: git commit failed: {r.stderr.strip()[:500]}")
    print(f"Created {target}" + ("" if a.no_kit else f" (kit installed for: {a.agents if not a.kit_dir else 'see ' + str(a.kit_dir)})"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
