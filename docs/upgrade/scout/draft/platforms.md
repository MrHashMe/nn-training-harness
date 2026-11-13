# Scout note: platforms and portability

Date: 2026-11-11. Area: native Windows, WSL2, macOS, Slurm, containers, minimum Python version, interpreter
resolution. Builds on `docs/upgrade/BASELINE.md`, `docs/upgrade/PROMPT.md` and the sibling drafts
`platform-codex.md` and `platform-cursor.md`.

Conventions. Every claim was checked on 2026-11-11. Tags read `[Status | source key]`; the source table at the end
gives the URL and the version or page date for each key. Verified = read in the primary source today; Inferred = my
reasoning from verified facts; Unverified = not confirmed in a primary source today (memory, user-generated content,
an AI-generated wiki, or a failed fetch). Source text is paraphrased. `KIT` = the kit's own files at baseline commit
5ea9659, read locally.

Limits. The shared web-search budget was exhausted early in my task (my search calls were refused), so the
six-family search sweep the brief asks for was not done. The findings come from direct fetches of primary
documentation, the PyPI JSON API, distribution package indexes, GitHub releases and issues, and one AI-generated
repository wiki (always tagged Inferred or Unverified). No local trial was run: my area permits four version checks
only (`python --version` 3.11.7; `git --version` 2.52.0.windows.1; `nvidia-smi` RTX 5090, driver 596.49, 32607 MiB;
`wsl.exe -d Ubuntu --exec python3 --version` 3.12.3). Every "trial" named below is still to do.

## Summary (10 lines)

1. Native Windows is broken in four independent ways and psutil fixes none of them: the snapshot needs symbolic
   links (launch exits 6), the stop signal cannot reach the run, there is no start-time identity (PID reuse goes
   undetected), and hooks, agent files and instructions hardcode `python3` plus POSIX shell syntax.
2. A console control event only reaches processes that share the sender's console. The supervisor must therefore own
   a hidden console that the training process inherits, receive stop requests through a file, and send CTRL_BREAK
   itself; forced stop of the whole tree is `TerminateJobObject` on a named job object (ctypes, no admin).
3. Liveness and identity without psutil: `OpenProcess` + `WaitForSingleObject`/`GetExitCodeProcess` +
   `GetProcessTimes` creation time on Windows; `/proc/<pid>/stat` start ticks on Linux; `ps -o lstart=` on macOS.
4. Snapshots without symbolic links: copy tracked files, junction for linked directories, hard link (else copy) for
   linked files. Both link kinds are live views, not isolation. Cleanup must never follow links; junction-safe
   `shutil.rmtree` exists from Python 3.8, which makes 3.8 the hard floor. `git worktree` adds nothing here.
5. `os.replace` is atomic when it succeeds but fails while another process holds the target without delete sharing:
   add a bounded retry on writers and tolerant readers. Pass `encoding="utf-8"` everywhere; Python 3.15 changed the
   default, older versions still use the Windows code page.
6. WSL2 stops an idle distribution after 15 s by default and the VM 60 s later; systemd services do not keep it
   alive. The documented fix is the user-level setting `instanceIdleTimeout=-1` (WSL 2.5.4 or newer). Whether a
   detached run alone keeps WSL 3.0.5 alive is untested: needs a doctor check and one local trial.
7. macOS, Slurm and containers each need a different identity, liveness probe and stop channel: no `/proc` and no
   NVIDIA tools on macOS; the job ID, a pre-limit signal and same-ID requeue on Slurm; PID 1 signal rules, a 10 s
   default stop grace, small `/dev/shm` and a separate PID namespace in containers.
8. Minimum Python: 3.8, 3.9 and 3.10 are end-of-life; PyTorch 2.15 needs 3.11 and NumPy 2.5 needs 3.12. My
   recommendation is to claim "3.9+ tested, 3.11+ recommended", add a runtime version check, and test floor and
   ceiling on all three OS families. The user should confirm the floor.
9. No bare command name finds Python everywhere. The installer should validate candidates by running them, store
   the absolute path in a machine-local file, and write hooks without a shell where the agent allows it (Claude Code
   exec form, Codex `commandWindows`, Cursor PowerShell-safe command with `failClosed`).
10. Not done: no local trials (detach survival per agent, WSL keep-alive, junction creation on this account), no
    search sweep, and several defaults quoted from memory are tagged Unverified.

## Q1. Native Windows without admin and without symbolic links

### 1.1 What the kit does today and why it fails

- The supervisor is started with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (0x8 | 0x200) and starts the training
  process with `CREATE_NEW_PROCESS_GROUP` only. `[Verified | KIT expctl.py]`
- A detached process has no console, and a console program started by a parent without a console gets a new console
  of its own. `[Verified | MS-CON]` So the training process sits in a new, visible console window that nothing else
  shares; closing that window kills the run. `[Inferred | MS-CON]`
- `expctl stop` calls `os.kill(pid, signal.CTRL_BREAK_EVENT)` from its own process. Console control events are
  delivered only to processes that share the console of the caller. `[Verified | MS-GCE, PY-OS]` The caller is in
  the agent's console (or none), the run is in another, so the graceful stop cannot arrive and the code falls through
  to `taskkill /T /F`. `[Inferred | KIT expctl.py, MS-GCE]`
- On Windows `cmd_stop` skips the supervisor, and the supervisor handles only SIGTERM and SIGINT, which nothing can
  deliver to it there: any signal number other than the two console events makes `os.kill` call `TerminateProcess`.
  `[Verified | KIT expctl.py, PY-OS]`
- Start time comes from psutil or `/proc` only, so on Windows and macOS without psutil `same_process` returns true
  for any live process with a recycled PID. `[Verified | KIT expctl.py]`
- `write_json_atomic` calls `os.replace` once, with no retry. `[Verified | KIT expctl.py]`
- The default snapshot links ignored paths with `os.symlink`; the test account has neither Developer Mode nor the
  symbolic-link privilege, so `launch` exits 6 and only 18 of 139 baseline checks pass before the tests abort.
  `[Verified | KIT BASELINE.md]`
- The README advice for Windows ("install psutil and pass `--python-cmd python`") addresses none of the snapshot,
  stop-signal and hook-syntax defects. `[Inferred | KIT README.md, BASELINE.md]`

### 1.2 Starting a detached process that survives the launching shell

- Flag values, all exposed as `subprocess` constants since Python 3.7: `DETACHED_PROCESS` 0x00000008,
  `CREATE_NEW_PROCESS_GROUP` 0x00000200, `CREATE_NO_WINDOW` 0x08000000, `CREATE_NEW_CONSOLE` 0x00000010,
  `CREATE_BREAKAWAY_FROM_JOB` 0x01000000. `CREATE_NO_WINDOW` is ignored when combined with `DETACHED_PROCESS` or
  `CREATE_NEW_CONSOLE`; a new process group has CTRL+C disabled. `[Verified | MS-FLAGS, PY-SUB]`
- Recommended shape: start the supervisor with `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP` (it gets a console of
  its own with no window) and all three standard streams redirected; the supervisor starts the training process with
  `CREATE_NEW_PROCESS_GROUP` only, so it inherits the hidden console. Supervisor and run then share a console and the
  supervisor can deliver CTRL_BREAK to the run's group without receiving it itself. `[Inferred | MS-CON, MS-GCE,
  MS-FLAGS]`
- Windows has no "die with parent" rule: a process started this way outlives the shell unless it shares a console
  that is closed or belongs to a job object that kills on close. `[Inferred | MS-JOB, MS-CJO]`
- Agent tool runners are the real threat. Child processes join the parent's job by default; leaving it needs
  `CREATE_BREAKAWAY_FROM_JOB` and a job that allows breakaway, otherwise process creation fails. `[Verified | MS-JOB,
  MS-FLAGS]` The Codex Windows sandbox kills leftover children when the foreground command ends. `[Verified in the
  sibling note | platform-codex.md]` An AI-generated wiki says Codex also tree-kills hook and shell children through
  a job object. `[Unverified | DW-CODEX]` Whether a detached supervisor survives the end of a tool call was not
  tested for any of the three agents.
- Consequences for the design: try breakaway and fall back to a normal start when it is refused; at launch, check
  whether the launcher is inside a job that kills on close (`IsProcessInJob`, `QueryInformationJobObject`; API names
  from memory) and say so in the launch result; verify survival once per agent in a trial. `[Inferred]`
- Escape hatches if the trial shows that a tool runner kills the tree: processes created through WMI
  (`Win32_Process.Create`) are not associated with the caller's job `[Verified | MS-JOB]`; a per-user scheduled task
  is another route `[Unverified]`. Both add moving parts; hold them until needed.

### 1.3 Stopping gracefully and forcibly

- Graceful: `CTRL_BREAK_EVENT` sent with `os.kill` or `Popen.send_signal` to a process started with
  `CREATE_NEW_PROCESS_GROUP`, from a process that shares its console. `CTRL_C_EVENT` cannot be limited to one group.
  `[Verified | PY-SUB, PY-OS, MS-GCE]`
- On the receiving side Python accepts a handler for `SIGBREAK`; handlers run in the main thread between bytecodes,
  so a long call into C code delays them for an arbitrary time. `[Verified | PY-SIGNAL]` The kit's run-side logger
  already registers `SIGBREAK`. `[Verified | KIT runlog.py]` A graceful stop therefore always needs a deadline and a
  forced second stage.
- `os.kill(pid, 0)` is not a liveness probe on Windows: 0 is the value of `CTRL_C_EVENT`, and any value other than
  the two console events terminates the target. `[Verified | PY-OS, MS-GCE]`
- CTRL_BREAK reaches every process in the group that shares the console, so data-loader worker processes receive it
  too, and the default action for a process without a handler is to exit. The main process may then see dead workers
  before it reaches its checkpoint. `[Inferred | MS-GCE; not tested]` A cooperative first stage avoids this: the
  run-side logger polls the stop-request file at each logging call, and the console event is the second stage for
  scripts that do not cooperate. `[Inferred]`
- Forced, whole tree: a job object through ctypes. `CreateJobObjectW(NULL, name)` returns the existing job when the
  name exists (`ERROR_ALREADY_EXISTS`); only named jobs can be reopened by another process; all members must be in
  the same session; the job lives until its last handle is closed and all members have exited. `[Verified | MS-CJO,
  MS-JOB]` Limit flags live in `JOBOBJECT_EXTENDED_LIMIT_INFORMATION`: `KILL_ON_JOB_CLOSE` 0x2000, `BREAKAWAY_OK`
  0x800, `SILENT_BREAKAWAY_OK` 0x1000. `[Verified | MS-JBLI]` Nested jobs need Windows 8 or newer. `[Verified |
  MS-JOB]`
- Race-free membership with the standard library: the supervisor creates the named job and assigns itself before it
  starts the run, so the run and every descendant are members from birth. A later `expctl stop --force` opens the job
  by name and calls `TerminateJobObject`, which works even when the supervisor has died, as long as any member is
  alive. `[Inferred | MS-JOB, MS-CJO]`
- `KILL_ON_JOB_CLOSE` would kill the run when the supervisor crashes. Recommended default: off, so that a run
  outlives a supervisor crash and is reported as unsupervised; the design may choose otherwise for unattended mode.
  `[Inferred | MS-JBLI]`
- Fallback when job creation fails: the existing `taskkill /PID <pid> /T /F`, which follows parent links and misses
  descendants whose parent has already exited. `[Inferred | KIT expctl.py]`
- ctypes hygiene: declare `argtypes` and `restype` for every call (handles are pointer-sized) and load the library
  with `use_last_error=True`. `[Inferred]`

### 1.4 Liveness and start time without psutil

- Windows: `OpenProcess` with `PROCESS_QUERY_LIMITED_INFORMATION` (0x1000), then `GetProcessTimes`; the creation time
  is a FILETIME in 100 ns units since 1601-01-01 UTC and, together with the PID, identifies the process. `[Verified
  | MS-GPT]` The kit tests `GetExitCodeProcess == 259`, which misreads a process that really exits with 259;
  `WaitForSingleObject(handle, 0)` is exact but needs the `SYNCHRONIZE` right. `[Inferred | KIT expctl.py; constants
  from memory]`
- "Access denied" on `OpenProcess` means the process exists; "invalid parameter" means it does not. `[Unverified |
  memory]`
- Linux: field 22 of `/proc/<pid>/stat` (start time in clock ticks since boot), parsed after the last `)` because
  the command name may contain spaces. `[Unverified today | memory; the kit already reads /proc]`
  `os.pidfd_open` (Python 3.9, Linux 5.3) is race-free but does not survive across separate controller calls.
  `[Verified | PY-OS]`
- macOS: no `/proc`. `ps -o lstart= -p <pid>` with `LC_ALL=C` gives a one-second start time; `ps -o stat=` shows
  zombies. `[Unverified | memory]`
- Store the raw kernel start value and compare exactly on the same machine; the kit's 5 s tolerance exists only
  because psutil rounds. `[Inferred | KIT expctl.py]`
- Launcher shims: on Windows a virtual-environment `python.exe` is a redirector that runs the base interpreter as a
  child, so `Popen.pid` is the shim. Group signals and job membership still reach the real interpreter; the PID
  recorded for the run should be the one the run reports about itself. `[Unverified | DW-CPYTHON, AI-generated]`
- `os.getppid` can return a stale value on Windows. `[Verified | PY-OS]`

### 1.5 Atomic replace when other processes hold the file

- `os.replace` overwrites the destination on every platform and is atomic when it succeeds. `[Verified | PY-OS]`
  On Windows it maps to a move with `MOVEFILE_REPLACE_EXISTING`; the API page says nothing about destinations that
  are open elsewhere. `[Verified | MS-MOVE]`
- A destination opened by another process without delete sharing (Python's `open` does not request it) makes the
  replace fail with a permission error; scanners and indexers also lock new files briefly. `[Unverified in a primary
  source | Windows sharing rules from memory]` Precedent: a widely used Node.js file-system library retries rename on
  access-denied, permission and busy errors with backoff for up to 60 s, citing antivirus locks. `[Verified | GFS]`
- Design: temporary file in the same directory, flush and fsync, `os.replace` with bounded retry (short backoff, a
  few seconds in total for small state files), readers that open, read and close quickly and retry on permission
  errors. Never fall back to delete-then-rename. Since the replace is atomic, readers never see partial JSON.
  `[Inferred | PY-OS, GFS]`
- A file in use cannot be removed on Windows `[Verified | PY-OS]`, so deleting or rotating the log or the directory
  of a live run fails; cleanup must check liveness first and report, not half-delete. `[Inferred]`
- The same retry is needed on Linux when state sits on a Windows drive seen from WSL, or on NFS. `[Inferred]`

### 1.6 Snapshot or isolated copy of a working tree without symbolic links

| Method | Privilege | Works for | Isolation | Limits | Status / source |
|---|---|---|---|---|---|
| Symbolic link | Developer Mode or the symbolic-link privilege | files, directories | none (live view) | not available on the test account | Verified / PY-OS, KIT BASELINE.md |
| Hard link (`os.link`) | none | files only, same volume | none: both names are one file | fails across volumes; a write through either name changes both | Verified / MS-HL, PY-OS |
| Junction | none (to be confirmed on this account) | directories only, local volumes | none (live view) | not for network shares; absolute target; creation needs `mklink /J` or a private API | Verified scope / MS-HL; privilege Inferred |
| `git worktree` | none | tracked files at a commit | real copy of tracked files | no ignored or untracked files; submodule support incomplete; writes into `.git/worktrees`; dirty trees need a commit | Verified / GIT-WT; "no ignored files" Inferred |
| Plain copy | none | everything | full | time and disk in proportion to size | Verified / PY-SHUTIL |
| Copy-on-write copy | file system dependent | everything | full | Windows block cloning needs ReFS or a Dev Drive (Windows 11 24H2; creating one needs local admin); Linux reflink needs Btrfs or XFS and Python 3.14 | Verified / PY-SHUTIL, MS-DEVDRIVE |

- Recommended snapshot on Windows: copy tracked files as today; for each path that today gets a symbolic link, make
  a junction if it is a directory, a hard link if it is a file on the same volume, otherwise copy under a size cap
  or fail with a clear message. Never start a run with a silently missing input. `[Inferred]`
- Links are live views. The run sees later edits to linked data and can damage the original through the link; the
  journal should record which paths were linked, and evaluation inputs that must stay frozen need a hash, not just a
  link. `[Inferred | MS-HL]`
- Cleanup must not follow links. `shutil.rmtree` stopped deleting junction contents in Python 3.8 `[Verified |
  PY-SHUTIL]`; `os.path.isjunction` and `Path.is_junction` exist only from 3.12 `[Verified | PY-312]`; on 3.8 to
  3.11 test the reparse attribute from `os.lstat` (`st_file_attributes`, `st_reparse_tag`, both 3.8) `[Unverified
  today | memory]`. Any code that walks a snapshot (hashing, size accounting, copying it again) needs the same
  check. Whether `os.walk` descends into junctions differs by version `[Unverified]`.
- `shutil.copy2` uses the native Windows copy call, which can clone blocks where the file system supports it, so
  copies become cheap on such volumes with no code. `[Verified | PY-SHUTIL; the Python version that introduced it
  was not confirmed]`
- `git worktree` duplicates what the kit already does for tracked files and changes the user's repository metadata.
  `[Verified | GIT-WT; Inferred conclusion]`

### 1.7 Text encoding, newlines and long paths

- Encoding: Python 3.15 turns UTF-8 mode on by default (PEP 686); before 3.15 text files opened without `encoding=`
  use the Windows code page. `[Verified | PY-315, PY-WIN]` A kit that supports several versions must pass
  `encoding="utf-8"` on every text open and decode hook input from `sys.stdin.buffer`; the logger already does the
  former. `[Inferred | KIT runlog.py]` For training children set `PYTHONUTF8=1` so that printing non-ASCII text into
  a redirected log does not raise. `[Unverified today | memory of PEP 540]`
- Output of Windows tools (`taskkill`, `cmd`) arrives in an OEM code page: use exit codes, do not parse text.
  `[Inferred]`
- Newlines: system git with `core.autocrlf=true` rewrites the kit's LF files as CRLF in a user's repository.
  `[Verified | KIT BASELINE.md]` Python tolerates that; shell shims run under WSL or Git Bash and byte-level upgrade
  checks do not. Write with `newline="\n"`, compare with newlines normalised, and consider a `.gitattributes` entry
  scoped to the kit's own folders (an edit to a user file, so opt-in). `[Inferred]`
- Long paths: the limit is 260 characters (248 for directories) unless `LongPathsEnabled=1` is set under
  `HKEY_LOCAL_MACHINE`, which needs elevation. `[Verified | MS-PATH, PY-WIN]` The `\\?\` prefix lifts the limit for
  absolute backslash paths without that setting, but many tools reject such paths. `[Verified prefix rules |
  MS-PATH; tool behaviour Inferred]` Without admin: short run IDs, shallow run folders, and a doctor warning when
  repository path plus snapshot depth nears the limit.
- File names: no `:` (so no ISO timestamps in run IDs), no reserved device names, no trailing dot or space; paths
  compare case-insensitively on Windows and on default macOS volumes. `[Unverified today | memory]`
- PyTorch on Windows starts workers with spawn, needs the `__main__` guard and has no CUDA tensor sharing between
  processes. `[Verified | PT-WIN]`
- The NVIDIA Windows driver can spill GPU memory into system memory instead of failing, which shows up as a large
  silent slowdown; a per-program driver setting turns it off. `[Unverified | vendor page returned HTTP 429]`
- A sleeping machine pauses training; `SetThreadExecutionState` from the supervisor prevents idle sleep without
  admin. `[Unverified | memory]`

## Q2. WSL2

### 2.1 Lifetime with no `wsl.exe` session attached

- `.wslconfig` has `[general] instanceIdleTimeout` (default 15000 ms; -1 disables automatic shutdown of an idle
  distribution) and `[wsl2] vmIdleTimeout` (default 60000 ms for the VM once no distribution runs). `[Verified |
  MS-WSLCFG]` The first setting arrived in WSL 2.5.4. `[Verified | WSL-REL]` The 3.0.1 release notes mention raising
  a VM termination timeout to 30 s, which does not match the documented 60000 ms; I could not tell which timer is
  meant. `[Verified texts, meaning Unverified | WSL-REL, MS-WSLCFG]`
- Current stable WSL is 3.0.5 (2026-11-03). `[Verified | WSL-REL]`
- Microsoft's systemd announcement states: "systemd services will NOT keep your WSL instance alive". `[Verified |
  MS-SYSTEMD, 2022]` A Microsoft engineer wrote in 2022 that daemonised children of a `wsl.exe` session are
  re-parented to a relay process that persists while they live, and that systemd user-session processes do not
  count. `[Verified statement, old | WSL-8854]` Whether a `setsid`/`nohup` child keeps WSL 3.0.5 alive is not
  documented. `[Unverified]` The open issue about background jobs being killed carries only user workarounds; one
  contributor (2026-04-28) names `instanceIdleTimeout=-1` plus `vmIdleTimeout=-1`. `[Unverified | WSL-9968]`
- Local observation: the distribution stops within minutes of the last `wsl.exe` command; not tested with a detached
  run. `[Verified | KIT PROMPT.md]`
- What the controller must do: detect WSL; keep the existing new-session detach; in `doctor` and in the launch
  result, warn that an idle shutdown can kill the run and name the user-level setting (no admin; takes effect after
  the user restarts WSL, which stops every distribution, so the kit must never do it itself); classify a run that
  ends without an exit record as "interrupted by host", distinct from "failed". `[Inferred | MS-WSLCFG]`
- Lingering and user services are not a keep-alive under WSL. `[Verified for services | MS-SYSTEMD; lingering
  Inferred | WSL-8854]`
- Other host events also end runs: Windows sleep or restart, `wsl --shutdown`, WSL updates. `[Inferred]`
- `/tmp` is emptied at every start of the distribution, so state must not live there. `[Verified | KIT PROGRESS.md]`

### 2.2 GPU access limits

- Only the Windows driver is installed; no Linux NVIDIA driver inside the distribution. Documented limits: no
  unified memory, limited pinned memory, some NVML queries unsupported (GPU utilisation and the list of compute
  processes among them), containers accept "all GPUs" only, and root finds the tool at
  `/usr/lib/wsl/lib/nvidia-smi`. `[Verified through a summarising fetch | NV-WSL]`
- Consequences: telemetry parsers must accept "not supported" values; "who is using the GPU" cannot be answered by
  PID inside WSL, and Windows programs share the same GPU memory invisibly; fall back to total memory in use.
  `[Inferred | NV-WSL]`
- The Codex Linux sandbox hides GPU devices, so training must leave the sandbox by an explicit rule. `[Verified in
  the sibling note | platform-codex.md]`

### 2.3 File-system performance across the Windows boundary

- Microsoft recommends keeping files in the Linux file system when working with Linux tools and advises against
  working across the two systems. `[Verified | MS-WSLFS]` I found no primary measurement of the slowdown today.
  `[Unverified]`
- Consequences: `doctor` warns when the repository or run folder is under `/mnt/`; the retry wrapper of 1.5 also
  applies there; a tree reached from Windows through the `\\wsl.localhost` share cannot use junctions (no network
  targets) or hard links across the boundary, so the snapshot falls back to copies. `[Inferred | MS-WSLFS, MS-HL]`
- One repository driven from both sides is the dangerous case: a Windows-side controller cannot probe a WSL PID and
  the reverse. Run state must record the environment that started the run, and a controller in another environment
  must answer "unknown, started elsewhere" rather than "dead", and must not clean or reuse that run's folder.
  `[Inferred]`

### 2.4 Memory behaviour

- The VM is capped at 50% of Windows memory by default, with swap of 25%. `[Verified | MS-WSLCFG]` Data-loader
  workers and page cache can hit the cap; the Linux out-of-memory killer then ends training with SIGKILL and no
  traceback. The supervisor should label "killed by signal 9" as "probably out of memory or external kill" and
  point to the cap. `[Inferred]`
- `autoMemoryReclaim` defaults to `dropCache`, so cached data is dropped when the VM is idle and the next epoch
  re-reads from disk. `[Verified default | MS-WSLCFG; effect Inferred]`
- WSL containers (`wslc.exe`, generally available since WSL 3.0.1) have their own settings file and a session idle
  timeout of 30 s; `.wslconfig` does not apply to them. GPU support there was not checked. `[Verified | MS-WSLC,
  MS-WSLCFG, WSL-REL]`

## Q3. macOS, Slurm and containers: what the controller must do differently

### 3.1 macOS on Apple silicon

- No NVIDIA tools. PyTorch 2.15.0 ships macOS wheels for arm64 only, tagged for macOS 14. `[Verified | PYPI-TORCH]`
  The MPS backend has no 64-bit floats or 128-bit complex numbers, and the CPU fallback switch does not cover that.
  `[Verified | PT-MPS]`
- GPU telemetry without root is not available from the controller; memory is shared with the system. The run-side
  logger can record backend memory itself. `[Unverified | memory]`
- Process control is POSIX and works as on Linux, with three differences: no `/proc` (see 1.4), no `setsid` command
  (use Python's `start_new_session`, as the kit already does by default), and spawn as the multiprocessing default.
  `[Verified for spawn | PY-314; the rest Unverified, memory]`
- Sleep suspends training; `caffeinate -i -w <pid>` ships with the system. `[Unverified | memory]`
- The system interpreter from the command-line tools is 3.9.6. `[Unverified | memory]`
- Advice written for CUDA (mixed precision, compilation, pinned memory) does not transfer, and scores measured on
  MPS are not comparable with CUDA runs. The journal should record device and backend, and a comparison should not
  mix them. `[Inferred | PT-MPS]`

### 3.2 Slurm (documentation version 26.05)

- Identity is the job ID, not a PID; processes run on another node, so PID probes on the login node are
  meaningless. State comes from the queue while the job is known to it and from accounting afterwards. States to
  map: PENDING, RUNNING, SUSPENDED, COMPLETED, FAILED, CANCELLED, TIMEOUT, PREEMPTED, NODE_FAIL, OUT_OF_MEMORY,
  BOOT_FAIL, DEADLINE, plus flags such as REQUEUED and COMPLETING. `[Verified | SL-STATE]` Exit codes are reported
  as `exit:signal`. `[Verified | SL-EXIT]`
- `sbatch --parsable` prints the job ID, followed by `;cluster` on multi-cluster sites. `--export` defaults to the
  whole submitting environment, so secrets in that shell travel with the job. `[Verified | SL-SBATCH]`
- Time limit: resolution is one minute; at the limit the job gets SIGTERM and, after the cluster's `KillWait`,
  SIGKILL. `[Verified | SL-SBATCH; the 30 s default of KillWait is Unverified]`
- Advance warning: `--signal=[R|B:]<signal>[@seconds]`. Without `B:` the signal goes to job steps and not to the
  batch shell; with `B:` only to the batch shell. It may arrive up to 60 s early; the default lead is 60 s.
  `[Verified | SL-SBATCH]` So the batch script must `exec` the supervisor (or trap and forward), and the lead must
  exceed checkpoint time plus that slack. The supervisor turns the signal into the normal graceful stop with reason
  "time limit". `[Inferred]`
- Requeue: `--requeue` lets the job restart from the beginning of the batch script under the same job ID after
  preemption or node failure; the cluster default is a site setting. `[Verified | SL-SBATCH]` Runs must therefore be
  resumable by construction, one run may have several segments, budgets must add the segments up, and wall-clock
  comparisons across requeued runs are invalid. `[Inferred]`
- `scancel` sends SIGCONT and SIGTERM, then SIGKILL after `KillWait`, and by default does not signal the batch step
  with anything but SIGKILL; `--batch` and `--full` change that. `[Verified | SL-SCANCEL]` Graceful stop is thus
  "signal the batch step", forced stop is a plain cancel.
- Job arrays: `--array=0-15%4` runs 16 tasks, four at a time. `[Verified | SL-SBATCH]` They suit seed replicates;
  each task needs its own run folder and the state parser must understand array IDs. `[Inferred]`
- Shared file systems: node-local scratch disappears with the job, so checkpoints go to shared storage; network
  file systems weaken locking and add latency to replace-then-read. `[Unverified | memory]`
- Many sites forbid long-running programs on login nodes, so an unattended agent loop there is a policy question
  for the user; the controller should only submit and poll. `[Unverified | memory]`
- Helper: submitit 1.5.4 (MIT, uploaded 2025-12-17, Python 3.8+, needs cloudpickle and typing_extensions) submits
  Python callables and requeues on preemption or timeout through a checkpoint method. `[Verified | PYPI-SUBMITIT]`
  It pickles code and adds two packages for what a template plus four commands does. `[Inferred]`
- Other schedulers expose the same four verbs (submit, state, signal, cancel); the backend interface should be
  those verbs, with Slurm as the only implementation. `[Inferred]`

### 3.3 Containers

- GPU runtime: NVIDIA Container Toolkit 1.20.1, configured with `nvidia-ctk runtime configure`; installation needs
  root. Podman is steered towards CDI. `[Verified | NV-CTK]` Docker accepts `--gpus all` and CDI device names; CDI
  is on by default since Docker Engine 28.3.0. `[Verified | DK-RUN]`
- Rootless Docker needs a per-user daemon configuration and a no-cgroups switch in the NVIDIA runtime
  configuration, which is itself a root step. `[Verified | NV-CTK]` Ownership of files written to bind mounts under
  user-namespace mapping was not checked. `[Unverified]`
- Cluster runtime: Apptainer 1.5 `--nv` binds the host's NVIDIA devices and libraries (the host driver is
  required), exposes all GPUs unless limited through the environment, and has an experimental alternative flag.
  `[Verified | APPT]` It runs as the calling user without a daemon, so signals and scheduler integration behave as
  for a normal process. `[Unverified | memory]` Other cluster runtimes were not evaluated.
- What changes for the controller:
  - PID namespace: PIDs inside and outside differ. Controller and run must be on the same side, or the identity is
    the container ID and liveness and stop go through the runtime. `[Inferred]`
  - PID 1: the main process needs explicit signal handlers and must reap children; `--init` adds a small init that
    forwards signals and reaps. `[Verified | DK-RUN]` A shell-form entry point swallows the stop signal.
    `[Unverified | memory]`
  - Grace period: stopping a container sends SIGTERM and then SIGKILL after 10 s by default for Linux containers
    (configurable). `[Verified | DK-STOP]` That is shorter than most checkpoint writes.
  - Shared memory: data-loader workers need more than the small default `/dev/shm`; use host IPC or a larger size.
    `[Verified that the options exist | DK-RUN; the 64 MB default is Unverified]`
  - Storage: the container file system is ephemeral, so run folder, journal and checkpoints sit on a mount.
    Mounting evaluator code and held-out data read-only is the one place where "the agent cannot change the
    evaluator" is enforced by the operating system instead of by a hook. `[Inferred | DK-RUN]`
  - Network: running without network enforces the offline default but breaks downloads; opt-in. `[Inferred]`
- The brief allows approvals to be bypassed only inside an isolated container. On native Windows Claude Code has no
  sandbox (WSL2 is supported) `[Verified | CC-SETUP]` and Cursor has none either `[Verified in the sibling note |
  platform-cursor.md]`, so a container or WSL2 recipe is the precondition for that mode there. `[Inferred]`
- On Windows the options are Docker Desktop (not evaluated; licence and admin install to be checked) and WSL
  containers (new, see 2.4). `[Unverified]`

## Q4. Minimum Python version to claim in November 2026

Lifecycle `[Verified | PY-VERS]`:

| Version | Status on 2026-11-11 | End of life |
|---|---|---|
| 3.8 | end-of-life | 2024-10-07 |
| 3.9 | end-of-life | 2025-10-31 |
| 3.10 | end-of-life | 2026-10 |
| 3.11 | security fixes only | 2027-10 |
| 3.12 | security fixes only | 2028-10 |
| 3.13 | security fixes only | 2029-10 |
| 3.14 | bug fixes | 2030-10 |
| 3.15 | bug fixes (released 2026-10-09) | 2031-10 |

Minimum versions required by current ML libraries `[Verified | PyPI JSON API, keys PYPI-*]`:

| Package | Version (upload) | `requires_python` |
|---|---|---|
| torch | 2.15.0 (2026-10-28) | >=3.11; wheels for 3.11 to 3.15 and free-threaded 3.14 and 3.15 |
| numpy | 2.5.4 (2026-10-10) | >=3.12 |
| transformers | 5.22.2 | >=3.11 |
| jax | 0.12.0.1 (2026-10-21) | >=3.12 |
| lightning | 2.6.6 | >=3.10 |
| tensorflow | 2.21.0 | >=3.10 |
| psutil | 7.2.2 | >=3.6 |
| submitit | 1.5.4 (2025-12-17) | >=3.8 |

Default interpreters:

| System | `python3` | Status / source |
|---|---|---|
| Ubuntu 22.04 / 24.04 / 26.04 / 26.10 | 3.10.6 / 3.12.3 / 3.14.3 / 3.14.7 | Verified / DIST-UBUNTU |
| Debian 11 / 12 / 13 | 3.9.2 / 3.11.2 / 3.13.5 | Verified / DIST-DEBIAN |
| RHEL family 8 / 9 / 10 | 3.6 / 3.9 / 3.12 | Unverified (vendor page returned HTTP 403) |
| macOS command-line tools | 3.9.6 | Unverified (memory) |
| Windows 11 | none; `python` and `python3` are Store stubs until Python is installed | Verified / PY-WIN, KIT PROMPT.md |
| Test machine | Windows 3.11.7; WSL Ubuntu 24.04 3.12.3 | Verified / local version checks |

Standard-library differences that matter to this kit:

- 3.8: junction-safe `rmtree`, symbolic links without elevation in Developer Mode, junction support in
  `os.readlink`, `copytree(dirs_exist_ok=)`. This is the hard safety floor. `[Verified | PY-SHUTIL, PY-OS]`
- 3.9: `os.pidfd_open`. `[Verified | PY-OS]`
- 3.11: `tomllib` (read-only) and `Popen(process_group=)` (POSIX only). `[process_group Verified | PY-SUB; the
  version that introduced tomllib is from memory]`
- 3.12: `os.path.isjunction`, `Path.is_junction`, `Path.walk`, `os.listdrives`, `rmtree(onexc=)`; `distutils`
  removed. `[Verified | PY-312]`
- 3.13: `os.process_cpu_count`. `[Verified | PY-OS]`
- 3.14: forkserver becomes the default start method on Linux (spawn stays on Windows and macOS); `pathlib` copy and
  move; copy-on-write copies on Linux; free-threaded build supported. `[Verified | PY-314, PY-SHUTIL]`
- 3.15: UTF-8 mode by default; `Popen.wait(timeout)` no longer polls; `tomllib` reads TOML 1.1. `[Verified |
  PY-315]`
- All Windows creation flags the design needs exist since 3.7, and `ctypes` is in every version. `[Verified |
  PY-SUB]`

Assessment `[Inferred]`:

- The kit runs in two roles. Hooks and the controller run under whatever interpreter the installer found, often a
  system one. The run-side logger is imported into the training process and must run on the training interpreter,
  which is 3.11 or newer for current PyTorch but older where users pin older stacks.
- Nothing in the planned fixes needs more than 3.8. Raising the floor to 3.11 buys `tomllib` (avoidable: Codex hooks
  can be written as JSON) and `process_group` (not needed), and would exclude the system interpreters of the RHEL 9
  family, macOS and Ubuntu 22.04, which is exactly where "no install rights" users are.
- A version claim is a test claim. Today 3.8 passes on WSL only. `[Verified | KIT BASELINE.md]`
- Recommendation: claim "Python 3.9 or newer; tested on 3.9 and 3.15 on Windows, Linux and macOS; 3.11 or newer
  recommended", and say plainly that 3.9 and 3.10 are end-of-life upstream. Keeping "3.8+" is defensible only with a
  tested 3.8 row on all three OS families. A 3.11 floor is the choice if the user prefers "supported upstream only".
  This is a product decision: see open questions.
- Whatever the floor: add a runtime check at the top of every entry point (none exists today `[Verified | KIT]`),
  written so that an older parser reaches the message instead of a syntax error, and keep a Windows test row on a
  pre-3.15 interpreter, because 3.15 hides missing `encoding=` arguments.

## Q5. Finding a working interpreter and writing it into hooks and instructions

### 5.1 Facts

- Windows: with nothing installed, `python` and `python3` on `PATH` are app-execution aliases that open the Store.
  `[Verified | PY-WIN]` On the test machine `python` is real and `python3` is such a stub. `[Verified | KIT
  PROMPT.md]` A stub exists as a file, so finding it on `PATH` proves nothing; only running it does. `[Inferred]`
- The new Python install manager installs per user without admin and provides `python`, `py` and `pymanager`, plus
  a `python3` alias that the documentation itself does not recommend relying on; `py -3` and `py -3.13` still work;
  its alias folder may not be on `PATH`. The old launcher is deprecated since 3.14 and the traditional installer
  ends with 3.15. `[Verified | PY-WIN]` Store, conda and uv-only setups have no `py`. `[Unverified | memory]`
- `python` is absent by default on Debian and Ubuntu. `[Unverified today | memory]` So no single bare name works on
  every platform. `[Inferred]`
- uv finds interpreters in this order: its managed installs, `PATH`, then the Windows registry and Store.
  `uv python find` prints the path of the first match. uv downloads interpreters automatically unless told not to.
  `[Verified | UV-PY]` So uv is usable as a lookup source only with downloads disabled, and `uv run` is unsuitable
  inside hook commands (start-up cost on every tool call, possible network access). `[Inferred]`
- Two interpreters with different lifetimes are involved: the hook and controller interpreter should be a stable
  system or user-level one; the training interpreter is the project environment, which is rebuilt and moved.
  `[Inferred]`
- Claude Code (documentation mentions versions up to 2.1.314): a hook with `args` is spawned directly with no shell,
  each element being one argument, and `${CLAUDE_PROJECT_DIR}` is substituted in both forms; without `args` the
  command runs through `sh -c` on macOS and Linux, Git Bash on Windows, or PowerShell when Git Bash is absent
  (`shell` selects `bash` or `powershell`). On Windows the exec form needs a real executable, not a `.cmd` or `.bat`
  shim. `onFailure: "block"` needs 2.1.295 or newer and also blocks when the hook cannot start. `[Verified |
  CC-HOOKS]` Without Git for Windows there is no Bash tool at all, only the PowerShell tool. `[Verified | CC-HOOKS,
  CC-SETUP]` Which version introduced `args`, and whether hooks in agent or skill front matter accept it, I could
  not find. `[Unverified]`
- Codex: hooks are on by default; project hooks load only when the project's `.codex/` layer is trusted;
  `commandWindows` (TOML `command_windows`) overrides the command on Windows and the documentation's example uses
  `py -3`; commands run in the session's working directory; an error, timeout or malformed answer from a
  pre-tool hook lets the tool run. `[Verified | CX-HOOKS]` On Windows the command is run through
  `%COMSPEC% /C "<command>"`, and quoting inside it is fragile. `[Verified in the sibling note | platform-codex.md]`
- Cursor: on Windows the desktop app runs hook commands through PowerShell and pipes the JSON in; project hooks run
  from the project root; exit code 2 denies; other failures fail open unless `failClosed: true`; both
  `CURSOR_PROJECT_DIR` and `CLAUDE_PROJECT_DIR` are set. `[Verified | CU-HOOKS]` Hook support in the terminal agent
  is stated for one event only. `[Unverified]` The hook input names the shell tool differently from Claude Code.
  `[Verified in the sibling note | platform-cursor.md]`
- The kit today: hook commands are `python3 "${CLAUDE_PROJECT_DIR:-.}/..."` (a POSIX-shell default expansion);
  `install.py` replaces only a leading `python3 ` in settings hooks and the status line; agent front matter, skill
  text, the instruction block and the kick-off prompt keep `python3`; allow rules exist only for `Bash(...)`.
  `[Verified | KIT install.py, settings.fragment.json, agents, SKILL.md]`

### 5.2 What the installer should write `[Inferred]`

1. Resolve once, by execution. Candidates in order: an explicit option; the interpreter running the installer
   (mapped to its base interpreter when that is a temporary environment); then names on `PATH`; optionally `py` and
   `uv python find` with downloads disabled. Accept a candidate only if a short probe run exits 0 within a timeout
   and reports a version at or above the floor. This rejects Store stubs and broken shims.
2. Store the absolute path in a machine-local, git-ignored place and write hook entries that contain it into the
   agent's machine-local settings layer. Shared, committed files must not contain absolute interpreter paths: they
   reveal a user name and break for every other machine. The price is that each machine must run the installer, and
   a fresh clone has no guard until it does; the session-start check should say so.
3. Per agent: Claude Code exec form, `command` = interpreter path, `args` = [`${CLAUDE_PROJECT_DIR}/.claude/hooks/
   nn_guard.py`], keeping the timeout and `onFailure: "block"`; Codex `command` for POSIX plus `commandWindows`,
   written without embedded quotes where the path allows; Cursor a command that PowerShell accepts (a quoted path
   in first position needs the call operator) with `failClosed: true`.
4. Instruction text should not name an interpreter. A session-start hook can print the exact controller command for
   this machine and shell, and the skill, agent bodies and instruction block refer to "the controller command shown
   at session start". Where a literal command is unavoidable (agent front-matter hooks), the installer substitutes
   it, as `PROMPT.md` requires. Substituting bare names into committed files makes them flip between `python` and
   `python3` across teammates' machines; this trade-off needs a decision.
5. Permission rules: generate PowerShell equivalents of the existing Bash allow rules; otherwise every controller
   call prompts on a Windows machine without Git Bash and an unattended loop stalls. The guard's command patterns
   were written for Bash and need a PowerShell review (owned by the guard notes).
6. Failure handling: a missing interpreter means lock-out where failures block (every guarded tool call, including
   the repair) and a silently absent guard where failures are ignored (Codex, Cursor by default). Provide a repair
   command the user runs in their own terminal, and let the controller refuse to launch when the guard
   configuration points at a missing interpreter.
7. Optional hardening to trial: run hooks with `-I` (isolated mode: no `PYTHON*` variables, no user site) plus
   `-X utf8`, so that a `PYTHONPATH` pointing into the repository cannot shadow a standard-library module. One hook
   imports a sibling module after adjusting `sys.path` itself, which should still work. `[KIT nn_readonly.py]`

## Changed since 23 October or wrong in the earlier notes

- PyTorch 2.15.0 was uploaded on 2026-10-28 and requires Python 3.11; `docs/research-notes/training_techniques.md`
  says 2.14 supports 3.10 to 3.15. macOS wheels are arm64 only. `[Verified | PYPI-TORCH]`
- WSL 3.0.5 became the stable release on 2026-11-03. `[Verified | WSL-REL]` `PROMPT.md` records only "stops within
  minutes"; the mechanism is two documented timers with a user-level off switch. `[Verified | MS-WSLCFG]`
- The NVIDIA guide for CUDA on WSL was updated on 2026-11-02. `[Verified | NV-WSL]`
- Python 3.10 reached end of life in October 2026 and 3.15.0 was released on 2026-10-09 with UTF-8 mode on by
  default; the kit's "3.8+" claim names a version that has been end-of-life for two years and is tested on WSL
  only. `[Verified | PY-VERS, PY-315, KIT BASELINE.md]`
- The README says native Windows works with psutil and `--python-cmd python`. It does not: the snapshot, the stop
  signal and the hook syntax fail regardless. `[Verified | KIT BASELINE.md; Inferred for stop and hooks]`
- The kit's graceful stop on Windows cannot work as written (console scope), and the forced stop relies on parent
  links instead of a job object. `[Inferred | MS-GCE, KIT expctl.py]`
- The kit's start flags give the training process a visible console window of its own. `[Inferred | MS-CON]`
- `install.py` rewrites the interpreter in two places only; five other installed files call `python3`. `[Verified |
  KIT]`
- `${CLAUDE_PROJECT_DIR:-.}` works only in a POSIX shell, while Claude Code now runs shell-form hooks through
  PowerShell when Git Bash is absent and offers a no-shell exec form. `[Verified | CC-HOOKS]`
- Claude Code documentation now refers to versions up to 2.1.314 (the kit was built against 2.1.x; the WSL installs
  on the test machine are older than the version that introduced `onFailure`). `[Verified | CC-HOOKS, KIT
  PROMPT.md]`
- Codex hook documentation moved to a new host (server redirect) and documents hooks as on by default with a
  Windows command override. `[Verified | CX-HOOKS]`
- Ubuntu 26.04 ships Python 3.14.3 as `python3`; Slurm documentation is at 26.05; NVIDIA Container Toolkit is at
  1.20.1; Apptainer documentation is at 1.5. `[Verified | DIST-UBUNTU, SL-SBATCH, NV-CTK, APPT]`

## Concerns any design must handle

PROC-DETACH-SURVIVAL: a run must outlive the shell, tool call and session that launched it
PROC-TOOL-RUNNER-TREE-KILL: an agent's tool runner may kill every descendant when a command ends
PROC-CONSOLE-SIGNAL-SCOPE: a graceful stop signal only reaches processes sharing the sender's console
PROC-GROUP-SIGNAL-FANOUT: a group-wide stop signal also hits worker processes that have no handler
PROC-GRACEFUL-STOP-LATENCY: signal handlers wait for native code, so every graceful stop needs a deadline
PROC-ORPHAN-TREE: forced stop must reach descendants whose parent has already exited
PROC-PID-REUSE: a recycled PID must not be mistaken for the run
PROC-LAUNCHER-SHIM-PID: the PID returned at start may belong to a launcher shim, not the interpreter
PROC-PID-NAMESPACE-MISMATCH: a controller in another OS environment or namespace cannot probe the run
PROC-VISIBLE-CONSOLE-WINDOW: a run in a visible console dies when a person closes the window
PROC-SUPERVISOR-CRASH-POLICY: decide whether a run survives the death of its supervisor
FS-NO-SYMLINK-PRIVILEGE: symbolic links are unavailable to ordinary accounts
FS-SNAPSHOT-LIVE-LINK: linked inputs are live views, so a snapshot is not isolation
FS-SNAPSHOT-CLEANUP-FOLLOWS-LINK: cleanup or traversal that follows a link destroys or miscounts the original
FS-CROSS-VOLUME-LINK-FAILURE: links fail across volumes and network shares and need a safe fallback
FS-ATOMIC-REPLACE-SHARING: replacing a file fails while another process holds it open
FS-INUSE-DELETE-FAILS: files of a live run cannot be deleted or rotated
FS-LONG-PATH: deep run folders exceed the path limit and the fix needs admin
FS-NAME-PORTABILITY: reserved characters, reserved names and case-insensitive paths
FS-CROSS-BOUNDARY-SLOW: state or data on the other operating system's file system is slow and lock-prone
FS-EPHEMERAL-STORAGE: temporary folders, container layers and node-local scratch vanish
TEXT-ENCODING-DEFAULT-DRIFT: default text encoding differs by platform and interpreter version
TEXT-NEWLINE-CONVERSION: version control rewrites line endings of installed files
HOST-GUEST-IDLE-SHUTDOWN: the guest environment is shut down when judged idle although a run is alive
HOST-SLEEP-INTERRUPTS-RUN: sleep, restart or update of the host ends or pauses a run
RUN-INTERRUPTED-CLASSIFICATION: a run that ends without an exit record must be labelled interrupted, not failed
MEM-GUEST-CAP-OOM: a memory cap kills training with no traceback
GPU-TELEMETRY-GAPS: utilisation and per-process GPU queries are missing on some platforms
GPU-SHARED-INVISIBLE-USERS: other programs use the same GPU memory without being visible
GPU-SYSMEM-FALLBACK-SLOWDOWN: GPU memory spills into system memory and slows training silently
GPU-BACKEND-CAPABILITY-GAPS: a backend lacks data types or features that the advice assumes
EVAL-BACKEND-COMPARABILITY: scores from different devices or backends must not be compared as equal
SCHED-TIME-LIMIT-SIGNAL: the warning before a time limit must reach the process that checkpoints
SCHED-REQUEUE-IDENTITY: a requeued job is one run with several segments, and budgets add them up
SCHED-NO-PID-LIVENESS: under a scheduler, state comes from the scheduler, not from PIDs
SCHED-ENV-LEAK: the submitting shell's environment, secrets included, travels with the job
CONTAINER-PID1-SIGNALS: the main process of a container must handle signals and reap children
CONTAINER-STOP-GRACE-TOO-SHORT: the default grace period is shorter than a checkpoint write
CONTAINER-SHM-LIMIT: default shared memory is too small for data-loader workers
RUNTIME-MIN-VERSION-DRIFT: the claimed minimum interpreter version must be tested, enforced and dated
RUNTIME-INTERPRETER-RESOLUTION: no command name finds a working interpreter on every platform
RUNTIME-INTERPRETER-VANISHES: the recorded interpreter is removed or moved after installation
RUNTIME-TWO-INTERPRETERS: hook interpreter and training interpreter differ and have different lifetimes
HOOK-SHELL-SYNTAX-PORTABILITY: a hook command is parsed by different shells on different platforms
HOOK-FAIL-OPEN-SILENT: a hook that cannot start disables the guard without notice
HOOK-FAIL-CLOSED-LOCKOUT: a hook that cannot start blocks every action, including the repair
GUARD-SHELL-TOOL-COVERAGE: guard patterns and permission rules must cover every shell tool an agent exposes
INSTALL-MACHINE-SPECIFIC-PATHS: absolute paths in shared files leak user names and break other machines
INSTALL-UNGUARDED-FRESH-CLONE: a clone that has not run the installer has no guard
SEC-HOOK-MODULE-SHADOWING: environment variables or planted files change what a hook imports
SEC-SANDBOX-UNAVAILABLE: no native sandbox exists on some platforms, so bypassing approvals needs a container
TEST-PLATFORM-MATRIX-GAP: claims about a platform or version that is not in the test matrix

## Open questions

1. Does a detached supervisor survive the end of a tool call and of the session in each agent on native Windows
   (Claude Code Bash tool, Claude Code PowerShell tool, Codex with each sandbox mode, Cursor)? Trial: launch a
   60-second dummy run, end the session, check the exit record.
2. Does a new-session child keep WSL 3.0.5 alive with no `wsl.exe` attached? Trial: start a 10-minute sleeper that
   writes a heartbeat file, close every `wsl.exe`, wait 3 minutes, read the heartbeat.
3. Can the test account create junctions and hard links, and on which volumes? Trial in a temporary folder.
4. Does CTRL_BREAK kill data-loader workers before the main process checkpoints? Trial with a two-worker loader.
5. Which interpreter floor does the user want: 3.9 (recommended), 3.8 with a tested row, or 3.11?
6. Machine-local hook entries or shared ones: is "each machine runs the installer" acceptable?
7. Do hooks in Claude Code agent and skill front matter accept `args`, and from which version?
8. Does the Cursor terminal agent run hooks, and through which shell on Windows?
9. Does isolated mode (`-I`) break either hook?
10. Should a run survive a supervisor crash (default proposed: yes), or be killed with it in unattended mode?
11. Do agent tool runners place commands in a job that forbids breakaway?

## Redirect attempts

- `https://code.claude.com/docs/en/setup`: the page opens with a line telling readers to fetch a documentation index
  file at another URL and to use it to discover all pages before going further. Treated as page content; not acted
  on.
- A third-party fetch tool answered a request with a rate-limit error whose text suggested creating an API key for
  that service. Not acted on; no account was created and no key was requested.
- For transparency, not an instruction: `https://developers.openai.com/codex/hooks` answered with a server redirect
  to `https://learn.chatgpt.com/docs/hooks`, which I followed as an ordinary redirect.
- No other text in fetched pages, repositories or tool results addressed instructions to the reader.

## Sources

All read on 2026-11-11.

| Key | URL | Version or page date |
|---|---|---|
| MS-GCE | https://learn.microsoft.com/en-us/windows/console/generateconsolectrlevent | current page |
| MS-CON | https://learn.microsoft.com/en-us/windows/console/creation-of-a-console | current page |
| MS-FLAGS | https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags | page date 2025-07-14 |
| MS-JOB | https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects | page date 2025-07-14 |
| MS-CJO | https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-createjobobjectw | current page |
| MS-JBLI | https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information | current page |
| MS-GPT | https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes | current page |
| MS-MOVE | https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw | current page |
| MS-HL | https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions | page date 2025-07-08 |
| MS-PATH | https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation | page date 2024-07-15 |
| MS-DEVDRIVE | https://learn.microsoft.com/en-us/windows/dev-drive/ | updated 2026-06-01 |
| MS-WSLCFG | https://learn.microsoft.com/en-us/windows/wsl/wsl-config | page date 2026-10-16 |
| MS-WSLFS | https://learn.microsoft.com/en-us/windows/wsl/filesystems | updated 2026-06-02 |
| MS-WSLC | https://learn.microsoft.com/en-us/windows/wsl/wsl-container-settings | page date 2026-10-16 |
| MS-SYSTEMD | https://devblogs.microsoft.com/commandline/systemd-support-is-now-available-in-wsl/ | 2022-09-21 |
| WSL-REL | https://github.com/microsoft/WSL/releases | 3.0.5 (2026-11-03), 3.0.1 (2026-09-29), 2.5.4 (2025-03-26) |
| WSL-8854 | https://github.com/microsoft/WSL/issues/8854 | maintainer comment, 2022-11 |
| WSL-9968 | https://github.com/microsoft/WSL/issues/9968 | open; comment of 2026-04-28 (user-generated) |
| NV-WSL | https://docs.nvidia.com/cuda/wsl-user-guide/index.html | updated 2026-11-02 |
| PY-SUB | https://docs.python.org/3/library/subprocess.html | Python 3.15.2 docs |
| PY-OS | https://docs.python.org/3/library/os.html | Python 3.15.2 docs |
| PY-SHUTIL | https://docs.python.org/3/library/shutil.html | Python 3.15.2 docs |
| PY-SIGNAL | https://docs.python.org/3/library/signal.html | Python 3.15.2 docs |
| PY-WIN | https://docs.python.org/3/using/windows.html | Python 3.15.2 docs |
| PY-315 | https://docs.python.org/3/whatsnew/3.15.html | 3.15, released 2026-10-09 |
| PY-314 | https://docs.python.org/3/whatsnew/3.14.html | 3.14, released 2025-10-07 |
| PY-312 | https://docs.python.org/3/whatsnew/3.12.html | 3.12 |
| PY-VERS | https://devguide.python.org/versions/ | current page |
| CC-HOOKS | https://code.claude.com/docs/en/hooks | mentions versions up to 2.1.314; first part of the page read |
| CC-SETUP | https://code.claude.com/docs/en/setup | current page |
| CX-HOOKS | https://learn.chatgpt.com/docs/hooks | current page (redirect target of developers.openai.com/codex/hooks) |
| CU-HOOKS | https://cursor.com/docs/agent/hooks | current page |
| DW-CODEX | https://deepwiki.com/openai/codex | AI-generated wiki; never Verified |
| DW-CPYTHON | https://deepwiki.com/python/cpython | AI-generated wiki; never Verified |
| PYPI-TORCH | https://pypi.org/pypi/torch/2.15.0/json | 2.15.0, uploaded 2026-10-28 |
| PYPI-NUMPY | https://pypi.org/pypi/numpy/2.5.4/json | 2.5.4, uploaded 2026-10-10 |
| PYPI-other | https://pypi.org/pypi/<package>/<version>/json | transformers 5.22.2, jax 0.12.0.1, lightning 2.6.6, tensorflow 2.21.0, psutil 7.2.2 |
| PYPI-SUBMITIT | https://pypi.org/pypi/submitit/1.5.4/json | 1.5.4, uploaded 2025-12-17 |
| DIST-UBUNTU | https://packages.ubuntu.com/ (package `python3`) | 22.04, 24.04, 26.04, 26.10 |
| DIST-DEBIAN | https://packages.debian.org/ (package `python3`) | 11, 12, 13 |
| SL-SBATCH | https://slurm.schedmd.com/sbatch.html | Slurm 26.05 |
| SL-SCANCEL | https://slurm.schedmd.com/scancel.html | Slurm 26.05 |
| SL-STATE | https://slurm.schedmd.com/job_state_codes.html | Slurm 26.05 |
| SL-EXIT | https://slurm.schedmd.com/job_exit_code.html | Slurm 26.05 |
| NV-CTK | https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html | 1.20.1 |
| DK-STOP | https://docs.docker.com/reference/cli/docker/container/stop/ | current page |
| DK-RUN | https://docs.docker.com/reference/cli/docker/container/run/ | current page |
| APPT | https://apptainer.org/docs/user/latest/gpu.html | Apptainer 1.5 user guide |
| PT-MPS | https://docs.pytorch.org/docs/2.15/notes/mps.html | PyTorch 2.15 |
| PT-WIN | https://docs.pytorch.org/docs/2.15/notes/windows.html | PyTorch 2.15 |
| UV-PY | https://docs.astral.sh/uv/concepts/python-versions/ | page footer 2026-10-14 |
| GIT-WT | https://git-scm.com/docs/git-worktree | git 2.56.0 |
| GFS | https://github.com/isaacs/node-graceful-fs/blob/main/polyfills.js | commit f7a4370 |
