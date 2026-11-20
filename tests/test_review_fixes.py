#!/usr/bin/env python3
"""Regression tests for the issues found in the independent review (seeds, robustness, stop signalling,
snapshots, guard coverage, read-only subagents, selftest). Linux/macOS, CPU only, ~1 minute."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_kit as tk  # noqa: E402

PY = sys.executable
FAILS = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


WORKER_TRAIN = r'''
import os, subprocess, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from runlog import RunLog
# a stand-in for a DataLoader worker: a child process in the same process group that dies on SIGTERM
worker = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
with RunLog(metric="val/acc", direction="maximize", total_steps=10000, heartbeat_every=0.2) as rl:
    for step in range(10000):
        time.sleep(0.02)
        if worker.poll() is not None:
            raise RuntimeError("DataLoader worker (pid %d) exited unexpectedly" % worker.pid)
        rl.log(step, **{"train/loss": 1.0 / (step + 1)})
        if rl.should_stop():
            p = rl.path("ckpt", "last.pt"); p.write_text(str(step)); rl.checkpoint(p, step=step)
            break
worker.terminate()
'''

STUDY = r'''
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from runlog import RunLog
class Study: study_name = "sweep-v1"
class Trial:
    def __init__(self, n): self.number, self.study, self.attrs = n, Study(), {}
    def set_user_attr(self, k, v): self.attrs[k] = v
for n in range(2):
    with RunLog.for_trial(Trial(n), metric="val/acc", direction="maximize", heartbeat_every=0.2) as rl:
        for step in range(25):
            time.sleep(0.2)
            rl.log(step, **{"val/acc": step / 25})
'''

RESUME = r'''
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
from runlog import RunLog
d = sys.argv[1]; n = int(sys.argv[2])
with RunLog(run_dir=d, metric="val/acc", direction="maximize", heartbeat_every=0.2) as rl:
    for step in range(n):
        time.sleep(0.1)
        rl.log(step, **{"val/acc": 0.5})
'''


def guard(proj, tool, ti, cwd=None, mode=None):
    payload = {"tool_name": tool, "tool_input": ti, "cwd": str(cwd or proj), "session_id": "t"}
    if mode:
        payload["permission_mode"] = mode
    r = tk.sh([PY, str(proj / ".claude/hooks/nn_guard.py")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)},
              inp=json.dumps(payload))
    if not r.stdout.strip():
        return None
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]


def readonly(proj, cmd):
    r = tk.sh([PY, str(proj / ".claude/hooks/nn_readonly.py")], cwd=proj, env={"CLAUDE_PROJECT_DIR": str(proj)},
              inp=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": str(proj)}))
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else None


def main():
    # resolved, as expctl resolves the project folder: a temporary folder may be named in a short form (Windows) or
    # through a link (macOS), and the checks below compare paths that expctl hands to a run
    tmp = Path(tempfile.mkdtemp(prefix="nnfix-")).resolve()
    proj = tk.setup(tmp)
    (proj / "worker_train.py").write_text(WORKER_TRAIN)
    (proj / "study.py").write_text(STUDY)
    (proj / "resume.py").write_text(RESUME)
    (proj / "envprobe.py").write_text("import os, sys; print('SEED', os.environ.get('EXP_SEED')); "
                                      "print('ROOT', os.environ.get('EXP_PROJECT_ROOT')); "
                                      "print('PP', os.environ.get('PYTHONPATH', '').split(os.pathsep)[0]); "
                                      "print('FOO', os.environ.get('NNFIX_FOO'))\n")
    print("project:", proj)

    # 1. seed export + mismatch alert
    a = tk.jout(tk.expctl(proj, "launch", "--name", "seed-ok", "--seed", "5", "--", PY, "train.py", "--steps", "10", "--seed", "5"))
    b = tk.jout(tk.expctl(proj, "launch", "--name", "seed-bad", "--seed", "7", "--", PY, "train.py", "--steps", "10"))
    probe = tk.jout(tk.expctl(proj, "launch", "--name", "envprobe", "--seed", "3", "--", PY, "envprobe.py",
                              env={"NNFIX_FOO": "bar"}))
    tk.wait_for(lambda: all(tk.state_of(proj, x["run_id"])[0] == "completed" for x in (a, b, probe)), 30)
    st = tk.jout(tk.expctl(proj, "status", "--no-gpu"))
    check(any("seed recorded by the run" in al and b["run_id"] in al for al in st["alerts"]), "seed mismatch is alerted")
    check(not any("seed recorded by the run" in al and a["run_id"] in al for al in st["alerts"]), "matching seed is not alerted")
    log = (proj / probe["run_dir"] / "stdout.log").read_text()
    check("SEED 3" in log and f"ROOT {proj}" in log, "EXP_SEED and EXP_PROJECT_ROOT exported")
    check(f"PP {proj / probe['run_dir'] / 'src'}" in log, "snapshot copy is first on PYTHONPATH")

    # 2. tmux carries the full environment (if tmux exists)
    if shutil.which("tmux"):
        t = tk.jout(tk.expctl(proj, "launch", "--name", "tmux.env", "--via", "tmux", "--", PY, "envprobe.py",
                              env={"NNFIX_FOO": "bar"}))
        tk.wait_for(lambda: tk.state_of(proj, t["run_id"])[0] == "completed", 30)
        tlog = (proj / t["run_dir"] / "stdout.log").read_text()
        man = json.loads((proj / t["run_dir"] / "manifest.json").read_text())
        check("FOO bar" in tlog and not (proj / t["run_dir"] / ".launch-env.json").exists(),
              "tmux run sees the launch environment; env file removed")
        check("." not in man.get("tmux_session", ".") , "tmux session name sanitised")
    else:
        print("SKIP tmux not installed")

    # 3. corrupt run directory does not break status, guard or session hook
    bad = proj / "runs" / "zz-corrupt"
    bad.mkdir(parents=True)
    (bad / "manifest.json").write_text("[1, 2, 3]")
    (bad / "heartbeat.json").write_text(json.dumps({"ts": time.time(), "best": [1, 2], "latest": "x"}))
    r = tk.expctl(proj, "status", "--no-gpu")
    check(r.returncode == 0 and any("zz-corrupt" in al for al in json.loads(r.stdout)["alerts"]),
          "status survives a corrupt run directory and reports it")

    # 4. study runner stays alive through its trials' heartbeats (stale threshold is 3 s in tests)
    s = tk.jout(tk.expctl(proj, "launch", "--name", "study", "--", PY, "study.py"))
    time.sleep(6)
    stt, _ = tk.state_of(proj, s["run_id"])
    check(stt == "running", f"study runner reported running while trials log elsewhere (got {stt})")
    tk.wait_for(lambda: tk.state_of(proj, s["run_id"])[0] == "completed", 30)

    # 5. resume in place: the old result is archived, the live run is not "completed"
    rdir = proj / "runs" / "zz-resume"
    tk.sh([PY, "resume.py", str(rdir), "3"], cwd=proj)
    check(json.loads((rdir / "result.json").read_text())["state"] == "completed", "first segment completed")
    p2 = subprocess.Popen([PY, "resume.py", str(rdir), "40"], cwd=proj)
    time.sleep(1.5)
    stt, _ = tk.state_of(proj, "zz-resume")
    check(stt == "running" and list(rdir.glob("result.prev-*.json")), f"resumed run is live and old result archived ({stt})")
    p2.wait(timeout=30)

    # 6. graceful stop reaches the trainer only, not its worker processes
    w = tk.jout(tk.expctl(proj, "launch", "--name", "workers", "--", PY, "worker_train.py"))
    tk.wait_for(lambda: tk.state_of(proj, w["run_id"])[0] == "running", 20)
    time.sleep(1)
    stp = tk.jout(tk.expctl(proj, "stop", w["run_id"], "--wait", "30s", timeout=60))
    res = json.loads((proj / w["run_dir"] / "result.json").read_text())
    check(stp.get("final_state") == "interrupted" and res["state"] == "interrupted" and res.get("last_ckpt"),
          f"graceful stop with live worker processes -> interrupted with checkpoint ({stp.get('final_state')}, {res['state']})")

    # 7. sealed data never enters a snapshot
    snap = proj / a["run_dir"] / "src"
    check((snap / "data" / "train.csv").exists() and not (snap / "data" / "test").exists(),
          "snapshot contains training data but not the sealed test split")

    # 8. launch reports a command that cannot start
    bad_launch = tk.expctl(proj, "launch", "--name", "nostart", "--", "/nonexistent/binary")
    out = json.loads(bad_launch.stdout)
    check(bad_launch.returncode != 0 and not out["ok"] and "could not start" in out.get("error", ""),
          "launch reports a command that cannot start")

    # 9. guard coverage and false positives
    E = ".claude/skills/nn-training/scripts/expctl.py"
    cases = [
        ("kill with no harness runs live", "Bash", {"command": "kill 4242"}, None, None, "ask"),
        ("scancel always asks", "Bash", {"command": "scancel 1234"}, None, None, "ask"),
        ("cwd-relative sealed read", "Bash", {"command": "cat test/labels.csv"}, proj / "data", None, "deny"),
        ("cwd-relative sweep", "Bash", {"command": "find . -name '*.csv'"}, proj / "data", None, "ask"),
        ("git -C push --force", "Bash", {"command": "git -C . push --force origin main"}, None, None, "ask"),
        ("any git push asks", "Bash", {"command": "git push origin main"}, None, None, "ask"),
        ("git checkout rev -- path", "Bash", {"command": "git checkout HEAD -- train.py"}, None, None, "ask"),
        ("a change of branch writes no file that the guard keeps", "Bash",
         {"command": "git checkout main; git checkout -b eval-fix; git restore --staged train.py"}, None, None, None),
        # were None: the checkout of every file with an option in front or by another spelling of "all of them",
        # git by its other names, and restore where --staged does not stand alone
        *[(f"git puts files back: {c}", "Bash", {"command": c}, None, None, "ask") for c in (
            "git checkout -q .", "git checkout -q HEAD -- .", "git checkout ./", "git checkout HEAD '*.py'",
            "git checkout HEAD :/", "git checkout --force", "GIT checkout .", "git.exe reset --hard",
            "git restore -SW eval/metrics.py")],
        # the last three were None: a forced clean was read with its -f in the first group of letters only
        *[(f"git deletes what it does not track: {c}", "Bash", {"command": c}, None, None, "ask") for c in (
            "git clean -fd", "git clean -d -f", "git clean --force", "git clean -x -d --force src")],
        ("a clean that only lists", "Bash", {"command": "git clean -n -d; git clean --dry-run"}, None, None, None),
        ("a branch in brackets and behind an option, a branch that follows another", "Bash",
         {"command": "(git checkout main); git checkout -q main; git checkout -t origin/feature"}, None, None, None),
        ("the index alone", "Bash", {"command": "git restore --staged eval/metrics.py"}, None, None, None),
        # round 9 asks about a patch that is applied, not about git am's two forms that apply none
        ("git am shows the patch it is at, and its help", "Bash",
         {"command": "git am --show-current-patch; git am -h; git am --show-current-patch=diff"}, None, None, None),
        ("git am applies a patch", "Bash", {"command": "git am --show-current-patch; git am fix.mbox"}, None, None, "ask"),
        # From the second reading of 20 November 2026: git's --help-all is its help too (was "ask" for a day, when an
        # option's name got its end). An option that only starts like one of these is another one, a check that the
        # same line takes back applies the patch (were None), and patch.exe in capitals is patch
        ("git's --help-all applies nothing", "Bash", {"command": "git am --help-all; git apply --help-all"}, None, None, None),
        *[(f"a patch is applied: {c}", "Bash", {"command": c}, None, None, "ask") for c in (
            "git am --help-me fix.mbox", "git apply --check-only fix.patch", "git apply --check --no-check fix.patch",
            "git apply --stat --no-stat fix.patch", "Patch.Exe -p1 -i fix.patch")],
        ("chained command is not the final eval", "Bash",
         {"command": "NN_UNSEAL_TEST=1 python eval/final.py && cat data/test/labels.csv"}, None, None, "deny"),
        ("quoted note with -> is not a write", "Bash",
         {"command": f"python3 {E} launch --name a --note 'lr 3e-4 -> 1e-3' -- python train.py"}, None, None, None),
        ("worktree copy of sealed data", "Read",
         {"file_path": str(proj / ".claude/worktrees/w1/data/test/labels.csv")}, None, None, "deny"),
        ("bypassPermissions turns ask into deny", "Bash", {"command": "kill 4242"}, None, "bypassPermissions", "deny"),
        ("tmux send-keys C-c", "Bash", {"command": "tmux send-keys -t exp C-c"}, None, None, "ask"),
    ]
    for label, tool, ti, cwd, mode, want in cases:
        got = guard(proj, tool, ti, cwd=cwd, mode=mode)
        check(got == want, f"guard: {label} -> {got} (want {want})")
    live = tk.jout(tk.expctl(proj, "launch", "--name", "live", "--", PY, "train.py", "--steps", "3000", "--sleep", "0.02", "--seed", "9"))
    tk.wait_for(lambda: tk.state_of(proj, live["run_id"])[0] == "running", 20)
    for label, cmd, want in [
        ("uv run without --frozen while live", "uv run python x.py", "ask"),
        ("uv run --frozen while live", "uv run --frozen python x.py", None),
        ("shell write into a live run dir", f"echo x > {live['run_dir']}/notes.txt", "ask"),
        # was None: the file an output option names is written, whatever the program is called
        ("output option into a live run dir", f"python score.py --out {live['run_dir']}/score.json", "ask"),
        ("output option beside a live run dir", f"python score.py --ckpt {live['run_dir']}/last.pt --out score.json", None),
    ]:
        got = guard(proj, "Bash", {"command": cmd})
        check(got == want, f"guard: {label} -> {got} (want {want})")
    tk.expctl(proj, "stop", live["run_id"], "--wait", "30s", timeout=60)
    # unreadable config -> ask on writes, reads still allowed
    cfgp = proj / ".claude/nn-training.json"
    good = cfgp.read_text()
    cfgp.write_text("{ not json")
    check(guard(proj, "Bash", {"command": "ls"}) == "ask", "unreadable config: shell commands ask")
    check(guard(proj, "Read", {"file_path": str(cfgp)}) is None, "unreadable config: reads still allowed")
    cfgp.write_text(good)

    # 10. read-only subagent hook
    for cmd, want in [(f"python3 {E} status --brief", None), (f"python3 {E} launch --name x -- python t.py", "deny"),
                      (f"python3 {E} final-eval -- --ckpt runs/x/best.pt", "deny"),
                      ("tail -n 50 runs/x/stdout.log", None), ("echo hi > notes.md", "deny"),
                      ("python3 -c \"open('x.txt','w').write('1')\"", "deny"), ("git commit -m x", "deny"),
                      # were None: programs that write the file they name, and pathlib's one-argument forms
                      ("touch notes.md", "deny"), ("patch train.py fix.diff", "deny"),
                      ("python3 -c \"from pathlib import Path; Path('a').replace('b')\"", "deny"),
                      ("ls *(e:'rm x.txt':)", "deny"),
                      # were None (found by tests/test_guard_live.py): a redirection behind a descriptor, sed's long
                      # option, find's -delete, a formatter, the text of a trap
                      ("ls 2> err.txt", "deny"), ("sed --in-place s/a/b/ train.py", "deny"),
                      ("find . -name '*.pyc' -delete", "deny"), ("black .", "deny"), ("trap 'rm x.txt' EXIT", "deny"),
                      ("ls 2>/dev/null; python3 x.py 2>&1 | tail -n 3", None),
                      ("grep -n \"\\.replace(\" train.py", None), ("black --check .", None),
                      ("pip list | grep -o install", None),
                      # were None (the review of round 7): a program's name in capitals, perl's -i apart from its
                      # letters, a formatter behind a runner, the code flag in a group, a command that program text
                      # hands to a shell, git's checkout with an option in front
                      ("RM x.txt", "deny"), ("perl -p -i -e 's/a/b/' train.py", "deny"), ("uvx ruff format .", "deny"),
                      ("python3 -m black .", "deny"), ("bash -ce 'rm x.txt'", "deny"),
                      ("python3 -c \"import os; os.system('rm x.txt')\"", "deny"), ("git checkout -q .", "deny"),
                      ("black --version; isort -c .; python3 -O x.py; ls -lo train.py", None),
                      ("git diff --no-index a b; perl -ne 'print if /acc/' train.py", None),
                      # were None (round 9): an archive unpacked, a write from inside a program of awk or of a
                      # language that the guard keeps no list of, sponge, a command behind env -C <folder>
                      ("tar -xf bundle.tar -C sub", "deny"), ("unzip -o bundle.zip -d sub", "deny"),
                      ("awk '{print > \"out.txt\"}' train.py", "deny"),
                      ("node -e \"require('fs').writeFileSync('out.txt', 'x')\"", "deny"),
                      ("python3 x.py | sponge out.txt", "deny"), ("env -C sub touch notes.md", "deny"),
                      ("python3 -c \"import shutil; shutil.unpack_archive('b.zip', 'sub')\"", "deny"),
                      ("tar -tf bundle.tar; unzip -l bundle.zip; awk '{print $1}' train.py", None),
                      ("node -e \"console.log(require('fs').readFileSync('train.py','utf8'))\"", None),
                      ("python3 -c \"import sqlite3; print(sqlite3.connect('runs/s.db').execute('select 1').fetchall())\"",
                       None),
                      # were "deny" for a day (a fresh reader's reading of round 9): a file printed out of an archive,
                      # a write to the screen, a folder or a file with the name of a language or of a .NET stream, a >
                      # in the text that the shell's printf is given
                      ("tar -xOf runs/a.tar.gz config.json; 7z e -so runs/a.7z config.json", None),
                      ("tar -xf runs/a.tar.gz --to-stdout config.json | head -n 20", None),
                      ("node -e \"process.stdout.write(require('fs').readFileSync('train.py', 'utf8'))\"", None),
                      ("grep -rn \"writeFile(\" node/; cat src/io/filestream.py; grep -c StreamWriter train.py", None),
                      ("printf 'epoch -> loss\\n' | awk '{print $1}'", None),
                      ("ruby -e '$stderr.write \"x\"; STDOUT.write(File.read(\"train.py\"))'", None),
                      ("unzip -lv bundle.zip; cpio -itv < bundle.cpio; tar -O -xf bundle.tar a.txt", None),
                      ("tar -xof bundle.tar", "deny"), ("tar -xOf bundle.tar config.json; tar -xf bundle.tar", "deny"),
                      ("nodejs -e \"require('fs').writeFileSync('out.txt', 'x')\"", "deny"),
                      ("[IO.StreamWriter]::new('out.txt')", "deny"),
                      # the letters of a folder's name are no letters that list or print
                      ("tar -xf bundle.tar -COUT", "deny"), ("unzip -o bundle.zip -dout", "deny"),
                      ("cpio -i -Dout < bundle.cpio", "deny"),
                      # were "deny" for a day (a second fresh reader's reading of round 9): a file's ending that is a
                      # language's name, a call that makes no file, awk's write to the screen
                      ("grep -n \"copy(\" web/index.php; grep -rn \"unlink(\" --include=*.php src", None),
                      ("node -e \"console.log(require('crypto').createHash('md5').update('x').digest('hex'))\"", None),
                      ("awk '$3 > 5 {print \"high: \" $0 > \"/dev/stderr\"}' runs/x/stdout.log", None),
                      ("php -r \"copy('web/index.php', 'out.php');\"", "deny"),
                      ("awk '{print > \"/dev/stderr\"; print > \"out.txt\"}' train.py", "deny"),
                      ("7z X bundle.7z -osub", "deny"),
                      # were None until 19 November (a comparison of round 8's guard with this one): a word ends at
                      # the sign that ends its command as well as at a blank. And were "deny": a file printed out of
                      # an archive in front of such a sign, the shell's printf in front of a pipe into awk
                      ("cat bundle.tar | tar x; echo done", "deny"), ("(cat fix.patch | patch)", "deny"),
                      ("tar x<bundle.tar", "deny"), ("patch<fix.patch", "deny"), ("cat fix.patch | patch|tail -3", "deny"),
                      ("awk '{ print $1 |& \"sort\" }' train.py", "deny"),
                      ("tar -xf bundle.tar -O; echo done; 7z e bundle.7z -so|head -3", None),
                      ("printf 'x\\n' | awk '{print $1}' train.py 2>&1 | tail -5", None),
                      ("printf 'x\\n' | sort | awk '{print $1}' train.py 2>/dev/null", None),
                      # were None until 20 November (the reading of that day): a program's name with .exe, as a
                      # shell on Windows may write it, is that program
                      ("touch.exe notes.md", "deny"), ("patch.exe -p1 -i fix.patch", "deny"), ("black.exe .", "deny"),
                      ("install.exe -m 644 x.py sub/y.py; ruff.exe format .", "deny"),
                      ("ruff.exe format .", "deny"), ("isort.exe .", "deny"),  # each alone (the second reading)
                      ("black.exe --check .; ruff.exe format --diff .; ls touch.exe", None)]:
        got = readonly(proj, cmd)
        check(got == want, f"read-only hook: {cmd[:50]} -> {got} (want {want})")

    # 11. selftest
    frag = json.loads((tk.KIT / "settings.fragment.json").read_text())
    (proj / ".claude/settings.json").write_text(json.dumps({"hooks": frag["hooks"]}))
    r = tk.expctl(proj, "selftest")
    out = json.loads(r.stdout)
    check(r.returncode == 0 and out["ok"], "selftest passes on an installed project: " +
          ", ".join(f"{c['check']}={c['ok']}" for c in out["checks"] if c["required"]))
    subprocess.run(["git", "add", "-f", "data/test/labels.csv"], cwd=proj, check=True)
    r, name = tk.expctl(proj, "selftest"), "sealed data is not tracked in git"
    warn = [c for c in json.loads(r.stdout)["checks"] if c["check"] == name]
    check([c["ok"] for c in out["checks"] if c["check"] == name] == [True] and r.returncode == 0 and len(warn) == 1
          and not warn[0]["ok"] and not warn[0]["required"] and "data/test/labels.csv" in warn[0]["detail"],
          "selftest warns when sealed data is tracked in git, where git can print it without being given its name")
    (proj / ".claude/settings.json").write_text("{}")
    check(tk.expctl(proj, "selftest").returncode == 1, "selftest fails when hooks are not registered")

    print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES")
    for f in FAILS:
        print("  -", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
