# Reference

Everything the front page leaves out: install details, what gets installed, the optional modules, what works with
which agent and platform, upgrading and removing, the run commands, the protocol settings, the kit's tests and
every known limit. New to the kit? Start with the [README](../README.md), then [the guide](GUIDE.md).

**On this page:** [Install details](#install-details) ·
[What gets installed](#what-gets-installed) ·
[Optional modules](#optional-modules-each-is-one-step) ·
[What works where](#what-works-where) ·
[Upgrading and removing](#upgrading-and-removing) ·
[Using expctl yourself](#using-expctl-yourself) ·
[Configure the protocol](#configure-the-protocol-phase-2-does-this-with-your-approval) ·
[Testing the kit](#testing-the-kit) ·
[Notes and limits](#notes-and-limits)

## Install details
The core needs only Python 3.8+ (standard library, no network). Everything that needs a package, an account, a
network service or money is optional and off until you enable it. Last checked on 11 Nov 2026 against Claude Code
2.1.303, Codex CLI 0.167 and Cursor's documentation of that date; the first version is from 23 Oct 2026.

On native Windows call the installer with `python`. It checks the interpreter and writes it into every installed
file that calls one (`--python-cmd CMD` chooses another; prefer a path without spaces; an upgrade keeps the one the
earlier install used). After the install:
1. Restart the agent in the repository so the hooks load. Codex: trust the project and approve the two hooks once
   in `/hooks`. Claude Code: `/hooks` shows them.
2. Run `python3 .claude/skills/nn-training/scripts/expctl.py selftest` (hooks registered, guard deciding, status
   working).
3. Paste `KICKOFF_PROMPT.md` with the Project card filled in. For Claude Code set a high effort level first; the
   skill, not the prompt, carries the procedure.

## What gets installed
| Path in your repo | Purpose |
|---|---|
| `.claude/skills/nn-training/SKILL.md` + `references/` | The operating procedure (phases and gates) and 15 dated on-demand references: validity, data, evaluation, uncertainty, HPO, optimization, performance, resume, fine-tuning, LLM practice, operations, stack, scouting, loop, remote |
| `.claude/skills/nn-training/scripts/expctl.py` | Run controller: `status`, `launch`, `watch`, `curve`, `compare`, `stop`, `resume`, `final-eval`, `audit-splits`, `hash`, `env`, `selftest` |
| `.claude/skills/nn-training/scripts/runlog.py` | Run-side logger for your training code (heartbeat, metrics, checkpoints, graceful stop, resume, HF/Lightning/Optuna helpers). Vendor a copy, as the skill does, or import it from there with the path built from `$EXP_PROJECT_ROOT`: a launched run works from a snapshot of the source that has no `.claude` |
| `.claude/skills/nn-training/scripts/nnloop.py`, `nnremote.py` | Optional modules: the unattended research loop and remote GPUs (below). Inactive until you configure them |
| `.claude/hooks/nn_guard.py` | The guard for all three agents (deny/ask), audit log in `.claude/state/guard.log` |
| `.claude/hooks/nn_session_status.py` | Injects live run status at session start, on resume and after compaction |
| `.claude/hooks/nn_statusline.py`, `nn_readonly.py` | Optional Claude Code status line; read-only rule for the two subagents |
| `.claude/agents/experiment-reviewer.md`, `run-analyst.md` | Sceptical read-only reviewer (Opus, high effort); log and curve analyst (Sonnet, medium effort) |
| `.claude/nn-training.json` | Harness config: metric, sealed and frozen paths, final-eval command, runs dir, interpreter |
| `.claude/settings.json` (merged) | Claude Code: hooks, allow rules for read-only `expctl` commands, ask rules for `git push` and Hugging Face tools that create or spend, deny rules for common secret files |
| `CLAUDE.md` or `AGENTS.md` (one marked block) | Eleven rules that survive context compaction. With Codex or Cursor the block lives in `AGENTS.md` and `CLAUDE.md` imports it |
| `--agents codex`: `.codex/hooks.json`, `.codex/agents/*.toml`, `.agents/skills/nn-training/SKILL.md` | Codex hooks, the two subagents, and a pointer to the skill |
| `--agents cursor`: `.cursor/hooks.json`, `.cursor/agents/*.md`, `.cursor/cli.json` | Cursor hooks, the two subagents (`readonly: true`), deny rules for the terminal agent |
| `experiments/JOURNAL.md`, `.claude/nn-training.manifest.json` | Project card and append-only journal; the record of what the installer wrote |

The installer writes only inside the target project. It never touches `~/.claude`, `~/.codex` or `~/.cursor`. The
one exception is an option you ask for: `--worktrees` (next table) writes one hook entry into the local settings of
the repository's other checkouts and one line into the repository's `.git/info/exclude`.

## Optional modules (each is one step)
| Module | Enable | Needs |
|---|---|---|
| Codex and Cursor ports | `install.py --target DIR --agents all` (or `codex`, `cursor`) | the agent |
| Claude Code status line | `install.py --target DIR --statusline` | |
| Guard for Claude Code sessions started in the repository's other checkouts (worktrees, or the main checkout when the kit lives in a worktree) | `install.py --target DIR --worktrees`; again after you add a worktree | git; "Notes and limits" says what it writes and what it cannot cover |
| MCP servers (Context7 docs, Hugging Face hub) | `install.py --target DIR --mcp` | network; the agent asks you to approve them |
| Research scouting | nothing to install: a step of the skill (`references/scouting.md`) | the agent's own web tools; without them it is skipped and the agent says so |
| Unattended research loop | add a `loop` section to `.claude/nn-training.json`, then `nnloop.py start --campaign NAME --agent claude --max-runs N` (`references/loop.md`) | git; a signed-in agent CLI; at least one limit (runs, hours, GPU-hours, money, tokens) |
| Remote and rented GPUs | add a `remote` section with a target and a spending cap, then `nnremote.py launch --name NAME --on TARGET -- ...`; an ssh target's `on_finish` names the command that stops a rented machine once its run has ended and its files are here (`references/remote.md`) | ssh access to a machine, or a Hugging Face account that may run Jobs |
| Third-party stack (PyTorch, Optuna, lm-evaluation-harness, PEFT/TRL, Trackio) | per row in `references/stack.md`, in the project's own environment | packages, network |

The loop decides keep or revert in harness code, from a score it gets by running your frozen evaluator itself, and
stops at the first limit. Sealed test data is absent from the loop's worktree and the guard denies it; a Claude Code
worker has no shell, a Codex worker has one and is held from that data only by the guard and the transcript scan
(`references/loop.md` says what is enforced where). A remote run obeys the same commands as a local one,
starts nothing paid without a cap that covers it, gets only the environment variables and files you name, and is
resumed from its last checkpoint after a preemption.

## What works where
Words used: **enforced** = a hook or the harness refuses mechanically; **instructions** = the agent is told, nothing
checks; **missing** = not available. Two rows of the first table stand for a list each:

- **Denied outright:** reading sealed test data, the configured final-evaluation command typed directly (it runs
  through `expctl final-eval`, which keeps a receipt of every use), a file-tool edit inside an active run directory,
  unreadable hook input.
- **Steps that need a person:** stop or kill, deleting runs or checkpoints, destructive git, push, edits of frozen
  or harness files, the final evaluation (`expctl final-eval`), an audit of the splits where anything is sealed
  (`expctl audit-splits`), dependency changes under live runs, paid compute,
  starting a campaign or a remote run. A shell command that writes into an active run directory belongs here too,
  and since 14 November 2026 an edit whose new text names sealed data, an MCP tool call whose arguments do, a
  shell command that names git's hooks or its configuration file, and decoded text handed to a shell.

### By agent
| | Claude Code | Codex CLI | Cursor editor agent | Cursor terminal agent |
|---|---|---|---|---|
| How it was checked | documented hook payloads; two loop campaigns with headless `claude -p` sessions on native Windows (Claude Code 2.1.322, 11 November 2026), the guard hook active in every session; not run on Linux (see "Notes and limits") | payloads built from the documented input schema (`Bash` and `apply_patch` both carry `tool_input.command`); not captured live, not run live | documented hook payloads; not run live | documented; not installed on the test machine |
| Rules that survive compaction | `CLAUDE.md` block | `AGENTS.md` block | `AGENTS.md` block | `AGENTS.md` block |
| Skill and references | native skill | pointer skill in `.agents/skills/` | read from `.claude/skills/` | read from `.claude/skills/` |
| Denied outright | enforced | enforced after you approve the hooks in `/hooks` (note 1) | enforced (`failClosed`) | enforced (`failClosed`) |
| Steps that need a person | the guard asks you; refused under `dontAsk`, `bypassPermissions` or `NN_UNATTENDED=1` | refused (a Codex hook cannot ask): run the step yourself | refused (a hook cannot tell whether you are there): run the step yourself | refused |
| A session in another checkout that lacks the kit's settings | unguarded, unless `--worktrees` registered the guard there (run live on native Windows; Linux, macOS and the desktop app's worktree sessions rest on the documentation) | missing: unguarded | missing: unguarded | missing: unguarded |
| Read-only subagents | enforced | instructions | enforced by Cursor (`readonly`) | enforced by Cursor (`readonly`) |
| Run status at session start | works | works after hook approval | works | works |
| Rules for secret files and publishing | deny and ask rules in `.claude/settings.json` | missing: use Codex's sandbox and approval settings | missing | deny rules in `.cursor/cli.json` |
| Status line | `--statusline` | missing | missing | missing |
| MCP servers (`--mcp`) | `.mcp.json` | missing: Codex keeps them in `~/.codex/config.toml`, which the installer leaves alone | `.cursor/mcp.json` | `.cursor/mcp.json` |
| Unattended loop | built: explicit tool list, approvals never bypassed; run live on native Windows (note 2) | built, not run live; stops if the guard hook did not run | not applicable | only with `--in-container`: it edits unattended only with `--force`, so it needs a container without credentials |
| Loop limits it can measure | runs, hours, GPU-hours, money, tokens | runs, hours, GPU-hours, tokens | | runs, hours, GPU-hours |

- **Note 1, Codex:** if a hook does not load, Codex runs without it. On native Windows start Codex from the project
  root: the hook path is relative to it, and from another folder the interpreter cannot find the hook script and
  exits with the code Codex reads as a refusal, so every call is refused (not verified live).
- **Note 2, the loop with Claude Code:** tested with a stand-in CLI and run live with headless `claude -p` sessions
  on native Windows (three campaigns: two stopped at their run limit, the third ended itself when two sessions in a
  row proposed no change, and its kept changes held on fresh seeds); not run live on Linux, where the CLIs of the
  test machine were not signed in.

Other surfaces (cloud agents, Claude Code on the web, Codex cloud, Cursor background agents) run outside your
machine: the kit's hooks and local GPU are not there, so use them for reading and planning only. Gemini CLI and
OpenCode are not ported.

### By platform
| | Linux | WSL2 | macOS | native Windows |
|---|---|---|---|---|
| Tests of 15 and 16 Nov 2026, on one machine | not run on bare Linux; WSL2 Ubuntu 24.04 stands in | all pass: Python 3.8 and 3.15.0b3 without third-party packages, 3.12 with psutil | not run | all pass: Python 3.8 and 3.15.0rc3 without third-party packages, 3.11 with psutil |
| Tests of 16 Nov 2026, on GitHub's runners, without third-party packages | all pass: Ubuntu 26.04 with Python 3.15.2, Ubuntu 24.04 with 3.8.18 (that image has no bubblewrap, so the loop's sandbox checks ran on 26.04 only) | not a runner | all pass: macOS 26 on arm64, with Python 3.14.10 and with the system's own 3.9.6 | all pass: Windows Server 2025 with Python 3.8.10 and 3.15.2 |
| Run contract, guard, installer, session status | works | works | the tests pass; no agent session has run on a Mac | works |
| `launch --via tmux` | works | works | the tests pass, with tmux 3.8 from Homebrew | missing (no tmux): runs are detached processes |
| Graceful stop | SIGTERM and `stop.json`, which the run's supervisor acts on by itself. The signal goes only to a process that `/proc` shows was started for this run, whatever pid the run's own records name (since 15 Nov 2026) | same | SIGTERM and `stop.json`; the signal goes to the pid in the run's records (no `/proc` to ask) | `stop.json` only: a loop that does not poll `RunLog.should_stop()` is killed after `kill_after_s` |
| Source snapshot | symlinks | symlinks | symlinks | symlinks where the account may create them; junctions and hard links where it lacks that privilege (local NTFS) |
| Loop: no network for the run, sealed data hidden from the run, and the file system read-only for it apart from its worktree, its own run folder and a `/tmp` of its own | enforced with bubblewrap; the read-only file system (since 15 Nov 2026; before, only the project) ran on bare Linux on 16 Nov 2026, on GitHub's Ubuntu 26.04 runner | enforced with bubblewrap (tried on 15 Nov 2026) | missing: offline variables and a scan of the change only | missing: same |
| Loop: a run cannot see or signal processes outside it (another live run, the campaign) | enforced with bubblewrap where the system gives a process namespace; GitHub's Ubuntu 26.04 runner gave one on 16 Nov 2026 | enforced with bubblewrap (tried on 15 Nov 2026) | missing: a scan of the change for `os.kill` and for process-starting code only | missing: same |
| Loop: the evaluator cannot write the project or the rest of the file system, apart from the run folder it scores, `loop.eval_writable` and a `/tmp` of its own | enforced with bubblewrap | enforced with bubblewrap | missing | missing |
| Loop: harness-side score, keep rule, limits, fresh worktree, ledger | enforced | enforced | enforced | enforced |
| Loop: evaluator, data and harness files unchanged by a run | enforced with bubblewrap (the project is read-only for the run, and so is what the evaluator imports from outside it, an installed package for example), and checksummed | same | checked after the fact: a run is not confined, so a changed protected file is caught at the next checksum, and a change to something the evaluator imports from outside the protected paths (an installed package) is not caught | same as macOS; `link_paths` are junctions or hard links there, so a run can write the project's own data through them |
| Remote runs | works | works | the tests pass, against stand-in `ssh` and `hf` commands; not run from a Mac against a real machine | works as the controller; an ssh target needs a POSIX shell on the remote side |

macOS: what has run on a Mac is the kit's tests, on GitHub's macOS runner on 15 November 2026 (the second row
of the table). They include the checks that only a Mac can run (`caffeinate` beside a live run, the chip and
memory in `expctl env`), a process's start time from `ps`, the generated guard test under macOS's bash 3.2.57
and zsh 5.9, and `launch --via tmux`. Nothing else has run there: no agent session, no training (the runners
have no PyTorch, so nothing ran on the Apple GPU and the nine benchmark checks that need PyTorch were skipped
on every system), no sleep and no closed lid. No Mac was at hand: what a reading of the code found
missing was built on 14 November 2026. A process's start time comes from `ps` where there is no `/proc`; without
psutil, a process number that had gone to another process counted as the run before. A live run, the loop and
the controller of a remote run hold off idle sleep with the system's `caffeinate`; a closed lid still puts a Mac
to sleep. `expctl env` reports the chip and the memory, and a run's `env.json` says whether PyTorch's `mps` device
is available. Finder's `.DS_Store` is in the kit's block of `.gitignore` and does not count as a changed
protected file. The guard reads zsh's patterns ("Notes and limits"). Not built: a box for the loop's runs (the
table above), and the `mps` device in `expctl env --probe`, in the memory figures of a run's heartbeat and in the
two benchmark tasks, which train on the CPU there. The loop refuses `--max-gpu-hours` on a Mac, because it
measures them with `nvidia-smi`. Training on the Apple GPU: `references/performance.md`, section 9.
`.github/workflows/tests.yml` runs the eight test files on GitHub's Ubuntu, Windows and macOS runners when a
commit is pushed. Its first run, on 15 November 2026, failed in four of six jobs: a snapshot made a link to a
folder again as a link to a file on a Windows account that may create symlinks, which is fixed, and two tests
compared paths in a way that holds only where a temporary folder has one name. The second run is the row
above.

Slurm: there is no Slurm target type; an ssh target to a login node with your own `srun` line is the route, and it
is not tested. Containers: no image ships with the kit; `--in-container` is your statement that the loop already
runs inside one.

## Upgrading and removing
- Upgrade: run the new `install.py` over the old install (same command). It keeps the values in
  `.claude/nn-training.json` (new keys and new protected paths are added), the journal, the run directories and
  your own settings; rewrites the kit's hook entries to the current form and names what it changed; replaces kit
  files, including ones you edited after install, and names each of those with its backup in
  `.claude/backups/nn-training-<timestamp>/`. Training scripts that import `runlog` and commands that call
  `expctl.py` at the skill path keep working. An upgrade without `--worktrees` writes nothing in the other
  checkouts and names each entry there that an earlier `--worktrees` run left in an older form. A settings file
  of yours that is not valid JSON, or whose hooks are not in the form its agent documents, stops an install or an
  upgrade before anything is changed; hook events in a form of your own that the kit does not write are kept.
- Remove: `install.py --target DIR --uninstall` deletes what the install wrote (files you edited stay), strips the
  hooks and the marked block, and keeps your config, journal, runs, backups, permission rules and `.gitignore` lines.
  It also takes the `--worktrees` entries out of the other checkouts' local settings (a file that held nothing else
  is deleted; the line in `.git/info/exclude` stays). The hook entries go before the scripts they run, and an
  entry in another checkout that cannot be taken out stops the removal with the kit still in place, because an
  entry without its script blocks every tool call. Run it before you move or delete the project folder.

## Using expctl yourself
```bash
E="python3 .claude/skills/nn-training/scripts/expctl.py"
$E status --brief                                   # what is running, best runs, alerts
$E launch --name lr3e-4 --seed 1 --note "hypothesis" -- python train.py --lr 3e-4 --seed 1
$E watch <run> --until terminal                     # event stream until it finishes
$E curve <run> --keys train/loss,val/acc            # the series, and under "findings" what the whole curve shows
$E compare --a variant=base --b variant=wide        # is b better than a, or is it noise: difference, interval, verdict
$E stop <run> --wait 5m                             # graceful: checkpoint, then exit
$E resume <run>                                     # a new run from the old run's checkpoint
$E final-eval -- --ckpt runs/<run>/ckpt/best.pt     # once, with a receipt and a journal entry
$E audit-splits                                     # how many records the splits share: counts only, never a row
$E hash                                             # source hash, git state and the hash of the frozen files now; each run's manifest holds its own
$E env --python .venv/bin/python --probe            # hardware and versions; --probe tries the GPU features there
$E selftest                                         # are the hooks, the guard and the protocol wired up
```

## Configure the protocol (Phase 2 does this with your approval)
Edit `.claude/nn-training.json`: `metric` (`name`, `direction`, `select`), `sealed_paths` (e.g. `"data/test/**"`;
test data kept outside the project as `"../NAME/**"`, by its full path or under `~`; in `sealed_paths`,
`frozen_paths` and `harness_paths` a full path that leads into the project counts as the name it has there),
`sealed_tokens` (e.g. `"NN_UNSEAL_TEST"`), `frozen_paths` (evaluation, metric and split code),
`final_eval_commands` (e.g. `"NN_UNSEAL_TEST=1 python -m eval.final"`: one program call without shell syntax, which
`expctl final-eval` runs once and records in `.claude/state/final-eval/`), `splits` (name and path of each split,
for `expctl audit-splits`, which counts the records they share), `optuna.storage`. For Claude Code add
matching `Read(...)`/`Edit(...)` deny rules for the sealed paths in `.claude/settings.json`.

## Testing the kit
```bash
for t in test_runlog_units test_kit test_review_fixes test_ports test_loop test_remote test_benchmarks test_guard_live; do python3 tests/$t.py; done
```
Ten to fifteen minutes, CPU-only fake runs in temporary projects, no network, no accounts, no GPU. Each file prints
`PASS`/`FAIL` lines and `RESULT: ALL PASS`. `test_ports` covers the installer (install, upgrade over the 23 October
version, uninstall) and the guard's answers for each agent; `test_loop` the loop with a stand-in agent;
`test_remote` the remote module with stand-in `ssh` and `hf` commands; `test_benchmarks` the two benchmark tasks'
data and their project creator; `test_guard_live` asks the guard about command lines that it builds from parts
and runs those that pass in a real shell ("Notes and limits"; another sample:
`python3 tests/test_guard_live.py SEED COUNT`). `benchmarks/pilot.py` compares an agent with
this kit, with the 23 October kit and with no kit on the benchmark task (it uses your agent subscription, and
stops when the agent reports that further usage would be billed per use). Two pilots, with two and with five runs
per arm, on one task, one machine and one model, are in `docs/upgrade/REPORT.md`, section 2: this kit's edge over the
23 October kit (0.0044 in test loss with five runs per arm, p = 0.54) is not more than the run-to-run noise, and
neither kit was shown to beat running the agent with no kit. Since 15 November 2026 `references/optimization.md`
holds an optimizer result measured on this very task, so the kit's arm of a later pilot starts with knowledge of
the task that the other arms lack: read its edge with that in mind, or run the pilot on another task.

## Notes and limits
- The guard is a seatbelt, not a sandbox: a program can still build a path at run time. For hard isolation keep
  the test split outside the repository, or use the agent's own sandbox with read-deny rules (test GPU access
  inside it first).
- What the guard reads in a call, since 14 November 2026: shell code attached to its flag (`bash -c"..."`,
  `cmd /c"..."`), the value of PowerShell's `-EncodedCommand`, a path joined from string literals in a line of
  code (`Path('data') / 'test'`, `os.path.join`, `+`), the new text of an edit or the lines a patch adds, and
  the arguments of an MCP tool. Limits: a path with a variable in it passes (literals only). Text that merely
  mentions a sealed folder, a URL for one, is asked about, and so is every edit that writes such a mention, also
  when the file held it before. `.md`, `.mdx` and `.rst` files, the kit's own config and the agent's own tools
  (Task, WebFetch) are not read that way. A shell command that names `.git/hooks/` or `.git/config` is asked
  about when it could write there: the guard cannot tell a source from a target, so `cat .git/config > x` is
  asked about as well, while `cat .git/config` alone passes.
- More of the same, after an independent review on 14 November 2026. The guard reads a command line a second
  time, the way a POSIX shell and PowerShell would take it (a backslash inside a name, `$'..'`, a brace list,
  PowerShell's or cmd's escape character), and joins Python's string literals that stand side by side
  (`'data/te' 'st/x.csv'`) in code and in an edit's text. Code that a runner takes from standard input
  (`echo "..." | sh`, `bash <<< "..."`, `cat <<EOF | python -`) is read like the text behind `-c`, and nested
  code is checked from every folder the line moves to (`cd data && python -c "open('test/x.csv')"` passed
  before). No fixed count of words, literals, nested commands or wildcard matches decides what is checked any
  more: the call is read to its end, and where five seconds do not allow to look up every path-like word of an
  edit or every match of a wildcard, the call is asked about. Asked about as well, because the guard cannot
  read what will run: decoded text that reaches a command (a decoder piped into a shell or `xargs`, inside
  `$( )`, `<( )` or backticks, or code that decodes: `b64decode`, `unhexlify`, `FromBase64String`, `atob`); a
  `.md`, `.mdx` or `.rst` file that is run as code (as a runner's script or standard input, sourced, piped into
  a runner, spliced into a command line, or executed by code that names it on the same line), since the edit
  tools write such files unread; a brace list of more than 64 names; an MCP tool that is handed a folder with
  sealed files (under `path`, `paths`, `directory`, `root`, as a `file://` address or as any argument written as
  a path); and a git setting that makes git start a program (`core.hooksPath`, `core.fsmonitor`, an alias,
  `git -c key=value`, `--config-env`, `--exec-path=`, the `GIT_*` variables for them, a clone that sets one, a
  template folder), because such a program runs outside the guard. The kit's own git calls switch the two
  settings off that act without a word (the file monitor and the hooks path). Limits: a name built at run time
  from variables, a `{a..b}` range or a command's output passes, as do text that is decoded into a file and run
  later, `rev`, `tr` or `printf` in a substitution and a string that code computes. A notes file passes when it
  is copied, renamed or cut into a file of another name and run under that name, when its name has a blank,
  when its text is read on one line and executed on another, and behind a wrapper the guard does not know
  (`conda run`, `pytest --doctest-glob`, `jupytext --execute`). Text piped into a runner the guard does not
  know (php, lua, deno, bun, Rscript, julia) and a file's content piped in (`cat script.py | python`) are not
  read. An MCP tool that is handed the project root is not asked about, because tools are handed it all the
  time, nor is a bare word under a key that names no place (a query for `data`). A git folder elsewhere
  (`--git-dir=x`) whose `config` was written as an ordinary file is not seen; `git config --type bool key value`
  and a read with `-f file key` are asked about though they start nothing. A recursive wildcard written into a
  code file passes the check of the edit's text (the walk is seen only in code on the command line). A change
  of folder that the guard cannot read (`sudo -D data`, `start /D data`, a variable) in front of nested code is
  not followed. The other way round, some harmless calls are asked about: a notes file handed to a runner as
  data (`perl -ne print notes.md`, `python manage notes.md`), an MCP tool that only lists the folder with the
  sealed files, and on Windows a program text of more than 32,767 characters, on which the path lookup fails.
- The patterns of zsh and ksh, since 14 November 2026 (on a Mac the agent's shell is zsh). The guard reads a
  command line a third time, with these written as the wildcards they are: a group inside a name
  (`data/(test|x)/labels.csv`, `data/te(st)/labels.csv`, and ksh's `@(a|b)`, `!(a)`, `+(a)`, `?(a)`), `[^a]`,
  zsh's `^name` in a path, `pattern~other`, and a flag such as `(#i)`, behind which every folder name of the word
  counts as `*`. A line that reaches a sealed path this way is refused like its sh form. A sealed path also
  counts as mentioned behind `<`, `[`, `@`, a comma and an option's letter (`"$(<data/test/labels.csv)"`,
  `curl -d @data/test/labels.csv`, `--data a.csv,data/test/labels.csv`), which is asked about, and so does a
  frozen or harness path in a command with a write that the guard knows (the next point). What each pattern
  does was run in zsh 5.9 and bash 5.3.9 on Linux, not in a Mac's shell. There the generated test
  (`tests/test_guard_live.py`) ran, under bash 3.2.57 and zsh 5.9 on GitHub's runner on 15 November 2026: none
  of the lines that the guard let pass did harm (150 of 450 in bash, 148 of 450 in zsh).
  Limits, each behind a shell option that the line or your shell settings would have to switch on: zsh's `x#`
  (repeats), a `^name` that is a whole word or stands inside a name (`te^x`), a group without `|` at the end of a
  word (`data/te(st)`), and a pattern under an option that ignores case. The other way round, a flag makes the
  guard refuse more than the shell would match: `cat data/(#i)TRAIN.csv` is read as `cat data/*`.
- A shell command that names a frozen or harness file is asked about where the line holds a write that the
  guard knows. Since 14 November 2026 these are: a redirect, also behind a descriptor (`2> file`, `&> file`,
  `>& file`; not `2>&1`, not one to `/dev/null`); `tee`, `cp`, `mv`, `rm`, `ln`, `dd`, `rsync`, `truncate`,
  `touch`, `patch`, `install`; `sed -i` and `--in-place` wherever the option stands, BSD sed's `-I`, perl's and
  ruby's `-i` alone or in a group of letters (`perl -p -i -e`, `ruby -pi -e`); `find -delete`;
  `git checkout` with a path, also behind options and as `.`, `./`, `:/` or a wildcard, `git checkout --force`,
  and `git restore <path>` unless `--staged` stands alone; a formatter or fixer that rewrites files (`black`,
  `isort`, `ruff format`, `ruff --fix`; not with `--check`, `--diff`, `--version` or `--help`), also behind the
  runner that starts it (`uvx`, `pipx run`, `uv tool run`, `conda run -n env`, `python -m`, `black@24.1.0`); the
  word behind an output option (`-o`, `-O`, `--out…`, PowerShell's `-OutFile`, so `sort -o`, `curl -o` and
  `wget -O` count, also where the letter ends a group: `sort -uo`, `curl -sSLo`, `wget -qO`; a wildcard there
  counts as what it names on disk, and where it is a variable or a command's output, as in
  ``sort -o `echo f` ``, every path of the line may be the one written);
  Python's file calls in code on the line (`open(…, 'w')`, `write_text`, `os.replace`, pathlib's `.rename(`,
  `.touch(` and the link calls); and the PowerShell and cmd forms of all these, a file object's own calls among
  them (`(Get-Item f).Delete()`, `.MoveTo(`, `.CopyTo(`). A program's name counts in any case (`RM`, `SED`,
  `GIT`, `git.exe`), because Windows, and a Mac as it comes, find it so.
  Since 15 November 2026 a line whose only write is a redirect, or a `tee` at the start of a command, is asked
  about only where a target of it is such a file: `python eval/metrics.py > score.json` passes (it was asked
  about, and refused where nobody can be asked), `echo x > eval/metrics.py` is asked about as before. The
  targets are read as words with their quotes taken off, from every folder the line goes to. The older rule,
  any path of the line, stays wherever a target cannot be read that way: a variable, a command's output, a
  backslash or a home sign in the line, a target that is a pattern or is missing, `cd -` or `popd`, a second
  write verb that the guard lists, a `tee` that starts no command, a line inside `bash -c`; and since
  16 November 2026, when an independent reading found both passing, a line with a here-document (an apostrophe
  in its text paired with a quote further down and hid what stood between them) and a `cd` or `pushd` with no
  folder or with options alone (`cd --`, `cd -P`), which goes home or to the folder before; such a word counts
  where a command starts, so an argument named `sl` or `cd` is none where it is the last word before a
  redirection or the line's end (`--model sl > score.json`; with a word behind it, in quotes or in a comment
  too, it brings the rule for any path back, see below). A command starts, for the guard, at a
  line's start, behind `;`, `&`, `|` or a bracket (the `)` of a `case` pattern among them), and there behind a
  shell keyword, `time`, `command`, `builtin`, zsh's `noglob` or `nocorrect`, an assignment or a redirection
  that stands first. A `cd` with a word behind it that stands anywhere else (`time -p cd ..`, or the words `cd data` as
  arguments), and one with an option that the guard does not know (zsh's `cd -q data`), bring the rule for
  any path back as well, since the line may go where the guard does not follow it: from round 8 until the
  reading of its fixes such a line was read target by target from the folder it started in, and a write of a
  kept file by its name from the other folder passed. Since that day the guard also reads
  every line once more without the quote characters of its here-documents that pair with nothing there (the
  apostrophe of `don't`), so that a `cp` or an `rm` behind such an apostrophe is seen. Quotes that pair inside
  the document stay, so that a program or a message in one is read as on the line as it came:
  `print('loss -> 1')` holds no redirection and `"rm x"` no deletion (the first form of this reading, on `main`
  for some hours of that day, took those out too and refused such a program to a read-only subagent).
  PowerShell's here-string loses all of its quote characters, and only this extra reading covers it; a
  here-document that nothing on the line closes loses them all too, and since 17 November 2026 so does one
  with a backslash in front of a quote (`print("a \" b")`; a quote behind an escaped backslash, `"C:\\"`,
  counts as one): the rules read a backslash as a folder separator
  and end the quoted text there, so between 16 November and that day such a quote paired with one behind the
  document and hid the commands in between (found when that fix was read; the cost is that a quoted `->` or
  `rm` beside such a quote is refused to a read-only subagent again). For the same reason the guard reads
  every line once more as a POSIX shell does where `\"` stands inside double quotes (`echo "5\" wide"`): there
  it ends nothing, while the rules ended the quoted text and, with an odd number of such quotes, hid the
  commands up to the next quote; no version before 17 November 2026 read that, and a read-only subagent's
  `python -c "open(\"f\", \"w\")"` passed until then, because the program ended for the rules at its first
  escaped quote. Both readings first took the place of the ones before them (such a document with the quotes
  that pair in it, and `"..."` as it came), and two kinds of line that only those had asked about passed from
  17 to 18 November 2026: `echo it\'s "a \" > eval/metrics.py" 'x'` is one, which a POSIX shell only prints
  and which writes the file where its text reaches cmd. Since the reading of 18 November the older readings
  are made beside the newer ones, so that a line they asked about is asked about still. Each reading is one
  more pass of every rule over the line, and each pass looked every word up on disk again: a here-document
  that holds a script of 1,500 lines (69 KB, eight forms to read) took 23 seconds on Windows, more than the
  guard allows itself, and 10 before 17 November. Since the same day a word is looked up once per run of the
  hook and working folder (a lookup that failed, as on a server that does not answer, is not kept and is made
  again as before), and that document takes 8 seconds: about a second for each form, which is what stays.
  The text with the escaped quotes is read as the shell's own splice of the fewest pieces (`'5" wide'`; a part
  between two such quotes that double quotes would expand, or that holds a backslash or an apostrophe, stays
  in double quotes as it came). The form of
  17 November made a piece of every escaped quote, and the guard looks up every run of touching pieces on disk
  as a path: a JSON body of 1.4 KB with a hundred fields (`curl -d "{\"k\":\"v\",…}"`) took 22 seconds on
  Windows, more than the guard allows itself, so that such a line ended as a question; it passes in a tenth of
  a second again, as before that day (with the exception below). One answer of that form went with it: a
  sealed file named in such a text that the guard does not read as a command of its own (a message, the body
  of a request, a command for another host) was refused, for a path made of its name and the quote character
  behind it. It is asked about again, as in every version before, and as the same word written with
  apostrophes was on that day too. A text handed to a shell or an interpreter on this machine is read as a
  command as before, and a sealed file it reads is refused. The form of 17 November stays from the first text
  on in which a command substitution or a `${…}` reaches across an escaped quote (`"$(echo \"x\")"`) or past
  the text's end, as with quotes inside it (`"$(dirname "$0")"`), to the end of the command, its further lines
  included: from there on the guard's pairs of quotes and the
  shell's may part ways, and neither form is the word a shell makes of such a text; what the substitution runs
  is read from the line as it came, as in every version, and the newer form gave some such lines another
  answer than that day's. Such a line keeps that form's cost too: a text with some hundred escaped quotes
  behind that point ends as the timer's question, as on 17 November. And the guard reads every line once
  more as PowerShell pairs its quotes: there a backtick in front of a quote makes it end nothing, inside double
  quotes too (``echo "5`" wide"``), and a quote inside a comment `<# #>` belongs to the comment (`<# it's #>`);
  the rules paired both, in every version before that day, so that a redirection behind such a text passed for
  a read-only subagent too. A `<#` that nothing closes is no comment, and what stands behind it is read on;
  until 18 November the search for its end ran from each of them to the line's end, and a line of 120 KB with
  60,000 of them was answered after 27 seconds, later than an agent's hook waits (now 0.3 seconds). In that
  reading a comment to the end of the line
  is found by the same pairing, so that an apostrophe in one (`# don't`) misleads nothing behind it. The cost: on a
  POSIX line with a command in backticks
  right before a closing quote (``"`date`"``), that reading takes the backtick for an escape and reads text
  quoted behind it as commands: the main session is asked about a commit message there that quotes a command, and
  a read-only subagent is refused a quoted `->`. With `$( )` in place of the backticks nothing changes.
  It also takes every `#` outside a quoted text for the start of a comment, inside a word too (`${#a[@]}`); that
  can only add a question or, for a read-only subagent, a refusal, where a quoted text opens behind such a `#`
  and closes on a later line. Not read: a line as cmd reads it, where an apostrophe quotes nothing, so two
  apostrophes in text handed to `cmd /c` hide what stands between them from the rules. A
  here-document ends where a shell ends it: the closing word is put together as a shell does (`<<'EOF'`,
  `<<E"O"F`, `<<EOF+`), and a Windows line end behind it counts. A written word that the guard cannot
  place inside the project (Git Bash's `/c/Users/…`, a mounted drive) is searched by name, an output option's
  word among them. Three kinds of line are asked about although they name
  no such file. A line that changes a folder holding such files as a whole: `mv eval old`, `rm -r eval`,
  `git checkout HEAD eval`, a forced `git clean -fd eval`, `Remove-Item eval -Recurse`, and `cp -r` or `rsync`
  with such a folder on either side, because the guard does not tell a source from a target. A line that deletes or edits the files which a
  search of the same line finds in such a folder: `find … -delete`, `find … -exec rm` (or `cp`),
  `… | xargs sed -i`, `sed -i … $(git ls-files '*.py')`, a loop that reads the names
  (`… | while read f; do sed -i … "$f"; done`, `done < <(…)`, also where the loop writes by a redirect into its
  variable), `gci -r -Filter *.py | Remove-Item`, PowerShell's block with the write anywhere in it
  (`| % { $t = gc $_; Set-Content $_ $t }`) and `foreach (…) { … }`; the search's own file filter is
  respected, so `find . -name '*.pyc' -delete` passes. And a formatter that is given such a folder, or none
  (`black .`, `ruff check --fix`), where a frozen or harness `.py`, `.pyi` or `.ipynb` file lies below; since
  15 November 2026 with a reason of its own, which the unattended loop counts as routine like git that discards
  uncommitted work (`references/loop.md`, "Routine refusals"). A forced push carries both reasons, the
  destructive one and the push's. So does a forced `git clean` that names a frozen or harness file or a folder
  holding one (`git clean -f eval/metrics.py`, `git clean -fd eval`): it was asked about as destructive git
  alone and now carries the file's or the folder's reason beside it, so that the loop does not count its
  refusal as routine. Both rules read the `-f` wherever it stands among the options, and written out
  (`git clean -d -f`, `git clean --force`, which passed unasked before).
  Since 19 November 2026 two more kinds are asked about, each with a reason of its own that the loop counts as
  routine as well. A line that unpacks an archive into a folder in which a frozen or harness file, sealed data
  or git's own files lie, because an archive may hold a file of any name: `tar -xf x.tar` and `unzip x.zip` in
  the project folder, `unzip x.zip -d eval`, `7z x`, `cpio -i`, `Expand-Archive`, and Python's `extractall` and
  `shutil.unpack_archive` in code on the line; a folder that a variable or a command's output names counts as
  any folder. Unpacked into a folder of its own (`tar -xf x.tar -C raw`, `unzip x.zip -d raw`) it passes, and
  so does a line that only lists or prints (`tar -tf`, `tar -xOf`, `unzip -l`, `unzip -p`, `7z l`, `7z x -so`).
  And a line that applies a patch (`git apply`, `git am`, `patch`), whatever the patch names, because the
  guard reads the command and not the patch; `git apply --check`, `--stat`, `--numstat` and `--summary`,
  `patch --dry-run` (BSD's `-C` and `--check`), `git am --show-current-patch` and a call for help or the
  version pass. A word of these two rules ends at a blank or at the sign that ends its command
  (`(cat x.tar | tar x)`, `patch<fix.patch`, `tar -xf x.tar -O; echo done`), so a label `patch)` at the start
  of a line of a shell's `case` is asked about as the command.
  The same day the list of writes grew by program text in languages whose write calls the guard
  keeps no list of (`node -e`, `deno`, `bun`, `perl -e`, `ruby -e`, `php -r`, `lua -e`, `Rscript -e`,
  `julia -e`) and in awk: on a line that runs one, a call whose name holds a word of writing
  (`writeFileSync(`, `unlink(`, `file_put_contents(`, `write.csv(`), a call that starts a command (`system(`,
  `execSync(`), a file opened to be written, and awk's `print > "file"`, `print | "cmd"` and `system(` count
  as a write (a command that a variable holds, `print | cmd`, is not read); and in Python by `os.open(`,
  `FileIO(`, a mode that the text gives by a name (`open(f, mode)`), `fileinput` in place and the two calls
  that unpack; in PowerShell by .NET's streams where a type is written (`[IO.StreamWriter]`,
  `New-Object IO.FileStream`) and by `::Open(` and `::OpenWrite(`, while `::OpenRead(` and `::OpenText(`
  read; and by `gawk -i inplace`. `sponge` names its file as `tee` does and is read as one.
  `sqlite3.connect` in Python code is asked about in the main session where the line names such a file; a
  read-only subagent may open a database, as it reads a study's. A write to the screen is none
  (`process.stdout.write(`, awk's `print > "/dev/stderr"`), nor are node's `createHash(` and
  `createReadStream(`. The guard reads the word and not the language, so some lines that only read are asked
  about where they name such a file, and refused to a read-only subagent: a regular expression's `.exec(` in
  node, a stream given as an argument (PHP's `fwrite(STDERR, …)`, julia's `write(stdout, x)`),
  `Object.create(null)`, perl's `delete $h{k}`, awk's `print (a || "x")`. The shell's own `printf` in front of
  a pipe into awk is no print of awk's (`printf 'x\n' | awk '{print $1}' f 2>&1 | tail -5`); with a redirection
  of its own in front of that pipe, or with another word between the pipe and awk (`| LC_ALL=C awk`,
  `| busybox awk`), it is still read as one.
  A `tee` is read past its own redirections: `tee >/dev/null eval/metrics.py` and
  `tee <<< "{}" eval/metrics.py` passed unasked from 15 November 2026, when a `tee`'s files were first read one
  by one, until that day, because the reading ended at the first redirection. And a program
  that counts where a command starts (`touch`, `patch`, `install`, a formatter, a program that unpacks) is seen
  behind `env -C <folder>` too, as running in that folder: `env -C sub touch ../eval/metrics.py` and
  `env -C sub black ../eval` passed unasked before. What the command behind it reads was followed already.
  Text that runs counts wherever it stands: the text behind a code flag, also where the flag stands in a group
  of letters, is cut short or has options behind it (`sh -ce '…'`, `bash -c -- '…'`, `bash -c -o pipefail '…'`,
  `powershell -com "…"`), every word of an `eval`, the text of a `trap`, a command inside `$(…)` or backticks
  (inside a string in double quotes too, and closed where a shell closes it: a bracket in quotes, a pattern of
  `case` and a command behind a here-document do not end it), the word of `${name:-word}` and `${@:-word}`, a
  text that the line keeps in a variable and may run from there (`c='rm x'; $c`, `d=$c; $d`, `c=rm; $c file`,
  zsh's `${=c}` and `${(e)c}`, `$c = 'del x'; iex $c`), the text that PowerShell makes a script block of
  (`[scriptblock]::Create('…')`, the engine's `InvokeScript('…')`) or runs inside a block (`&{iex '…'}`), a
  command that program text hands to a shell (`os.system('…')`, `subprocess.run([…])`), and a shell inside a
  shell three levels deep; a fourth level is asked about, because the guard does not read it. A message in a
  here-document that no program runs (`git commit -m "$(cat <<'EOF' … EOF)"`) stays unread.
  Limits. Not seen as a write of a frozen file: a git command that replaces the working tree as a whole
  (`git stash`, a change of branch, `pull`, `merge`, `rebase`; `git reset --hard` is asked about as destructive,
  and a change of branch while a run executes from the working tree); the files that an archive or a patch
  holds (since 19 November 2026 the line that unpacks or applies one is asked about, see above, but which file
  it would write the guard cannot say); a download that names only its address (`curl -O`, `wget URL`); a formatter
  the guard does not know (`autopep8 -i`, `yapf -i`, `prettier --write`); a `git clean` without `-f` in a
  repository whose `clean.requireForce` is switched off; a `cd` that `CDPATH` sends to another folder than the
  one below the session's; a `cd` with no folder that stands where the guard knows no command to start
  (`time -p cd`); a write behind an apostrophe in a here-document whose closing word starts with anything
  but a letter, `_`, a quote or a backslash (`<<1`, `<<+x`, `<<$x`);
  the whole project removed under another spelling of its folder (`rm -rf ../proj`); a frozen pattern that
  starts with a wildcard, which counts for the project folder but not for a named folder below it; `tee`
  behind a search (`… | xargs tee`) and a PowerShell block with a block inside it; and any program or script
  that puts the path together while it runs, a script that a loop over a search starts among them. The same
  holds for reading sealed data: a wildcard that program text applies below a folder which it names apart from
  it passes (`Path('data').glob('*/*.csv')`, `os.chdir('data')` before `glob.glob('*/*.csv')`,
  `[IO.Directory]::GetFiles("$PWD\data", '*', 1)`). Deleting sealed data is not reading it: a line that removes
  a folder in which sealed files lie, and no frozen or harness file, is not asked about (`rm -rf data` with
  `data/test/**` sealed; an independent review on 15 November 2026 pointed it out), while a move, a rename or a
  recursive copy of that folder is, and a forced `git clean` of it is asked about as destructive git, which the
  unattended loop counts as routine. For the frozen files, every run's record holds one hash
  over them (`frozen_hash`; `expctl hash` prints the current one, `expctl status` warns when ranked
  runs were made under other frozen files, and the final evaluation's receipt carries it), the loop compares
  the checksums of its protected files at every iteration, and `git status` shows the change where git tracks
  the file. In that hash a text file counts with LF line ends, so that a checkout with CRLF on another machine
  gives the same value. Every frozen file counts with its content. (Until 15 November 2026 at most
  64 MB were read, the smallest files first, and what lay beyond counted by its size alone, so that a change
  inside a large file left the hash as it was.) `expctl launch`, `nnremote launch`, `expctl hash` and the final
  evaluation read every file, so the hash in a run's record depends on nothing that a program could have written
  beside the files. `expctl status` is called often: it reads the smallest files, 64 MB of them, and a file
  beyond those once, and again when its size or one of its times has changed; meanwhile it takes that file's
  hash from `.claude/state/frozen-hashes.json`, a harness file that every full read puts right. What remains: a
  program that changes such a large file and writes the file's old hash there, or sets the file's times back, is
  not seen by `status` until the next launch, `expctl hash` or final evaluation. Two runs made under different
  frozen files hold different hashes whatever was written there, so the alert comes with the next run at the
  latest. A run made before that day holds the older hash, which `status` still takes for the same frozen
  files. The loop reads its protected files by a rule of its own:
  one over 64 MB in full once in a campaign's process, again when its size, its times or its first or last MiB
  have changed (before, only the size and those two MiB counted), and in full before every keep, before a
  confirmation's verdict and, on Windows, where a file has no change time, after every evaluation
  (`references/loop.md`, "Large protected files"). A full read of 1 GiB took 0.65 s on
  Windows and 0.44 s in WSL on 15 November 2026, from the system's file cache; a first read takes as long as the
  disk needs. The time grows with the number of frozen files, not only with their bytes: on Windows, measured
  on 15 November 2026 with the tests running beside it, 64 MB in 64 files took 0.1 s, 5,000 small files 2 s and
  20,000 small files 9 s (in WSL, on its own file system: 0.2 s and 0.7 s). The two launch commands, `expctl
  hash` and the final evaluation pay for the bytes and for the files each time; `expctl status` and the status
  at a session's start pay for the files and for the 64 MB they read, once a ranked run carries a hash. That
  hook has 30 s:
  with a frozen data folder of some 60,000 files or more the status at a session's start may not arrive, while
  the guard's protection of those files does not depend on it. The edit tools are asked about. The other way
  round, harmless lines are asked about when they hold such a write anywhere: a redirect to another file beside
  a second write or where its target is not read (`cat eval/metrics.py > out.txt; cp out.txt x.py`,
  `bash -c "cat eval/metrics.py > out.txt"`, PowerShell's `python eval\metrics.py > score.json` with its
  backslash; alone and in sh's spelling it passes since 15 November 2026, above),
  `cp -r eval sub/copy`, `ruff check --fix .`, `ls *.py | xargs black`, a line that names such a file beside a
  word in capitals that is a program's name (`RM`, `CP`, `DD`, `TEE`) or beside a restore of another file, and
  a line whose variable holds a harmful-looking text beside a runner
  (`note='rm -rf runs/old'; python -c "print(1)"`).
  `tests/test_guard_live.py` checks a sample of this list at every test run: it builds command lines from parts
  (a verb, a way to write the path, a wrapper), asks the guard, and gives every line that passes to a real
  shell in a temporary project (bash, zsh where it is installed, PowerShell on Windows). A line that passed
  must not have printed or copied the sealed file or changed a frozen file. It finds what its parts can build
  and nothing else: an independent review on 15 November 2026 found forms that the parts did not hold, which
  the guard now reads and the parts now build.
- Recursive commands over the project root (`grep -r`, `rgrep`, `find`, `ls -R`, `tree`, `du -a`, `tar`, `zip`, `cp -r`,
  `cp -a`, `rsync`, `diff -r`, `git diff --no-index` with two folders, each in any case of its name, a path with `**`
  in it such as `cat **/*.csv`; in PowerShell and cmd.exe `Get-ChildItem -Recurse` with
  its short forms, `dir /s`, `findstr /s`, `tree /f`, cmd's `for /r`, `Copy-Item -Recurse`, `Compress-Archive`, `robocopy`, `xcopy`,
  a .NET call with `AllDirectories`) are asked about when sealed files lie below it on disk, as in every folder
  below the root. So is a move or a rename of a folder that holds sealed files (`mv`, `git mv`, `Move-Item`,
  `Rename-Item`, `ren`): under another name nothing would seal them. A recursive command passes when it names the folders it needs
  (`grep -rn x src tests`, `Get-ChildItem src,tests -Recurse`) or gives a file filter that leaves the sealed files
  out (`--include='*.py'`, `-name '*.py'`, `--exclude-dir=data`, `-Filter '*.py'`, `-Include '*.py','*.md'`). `rg`
  and the agent's own Grep tool pass where git's ignore rules keep ripgrep away from the sealed files. They do not
  when the command turns the rules off (`rg -u`, `--no-ignore`, `git grep --no-index`), follows links (`rg -L`) or
  names files to include that match the sealed files or their ignored folder: `rg -g '*.csv'` reads a csv file that
  git ignores by a rule for the file (`*.csv`), while a rule for the folder (`data/`) holds (compared with ripgrep
  15.1 and Claude Code's Grep tool on Windows, 12 November 2026). Nor do they pass where ripgrep's own files take
  the rule back: a `.ignore` or `.rgignore` file, beside the ignored folder or in a folder above it, with a `!`
  line for its name, or a configuration file named by `RIPGREP_CONFIG_PATH` that turns the rules off, follows
  links or names files to include (`rg --no-config` sets that file aside; compared with ripgrep 15.0, 13 November
  2026). The guard reads each command of a line by
  itself and follows `cd`, `pushd` and `popd`, subshells, `git -C` and `env -C`. A path that names nothing where
  the line runs is read from every folder the line names as well, so that a sealed file reached through a
  program's own change of folder is refused (`sudo -D data cat test/x.csv`, `tar -C data -c test/x.csv`,
  `python train.py --data-dir data --eval-file test/x.csv`). Each tool's filters are read that tool's way (grep's
  `--include` and `--exclude` in their order, find's `-name` with `-o` and `-not`, ripgrep's `-g` and `-t`), and
  the target of a redirection (`2>/dev/null`) or the value of an option does not count as a folder the command
  names. `ls -r` and `dir -s` count as recursive wherever the shell may be PowerShell (Claude Code's PowerShell
  tool, Codex, Cursor, a line that names `powershell`, `pwsh` or `cmd`), and not in Claude Code's Bash tool, which
  runs a POSIX shell. Limits: it does not read depth options (`find -maxdepth 1`, `tree -L 2`, `-Depth 1`; only
  `-Depth 0` is read as one folder), PowerShell's
  `-Exclude`, the exclusions of `tar`, `zip` and `rsync` or a wildcard path (`gci -r *.py`), so those are asked
  about at the root as well, as is a search with a long option the guard does not know in front of its folders;
  behind a wrapper it does not know (`xargs`, `wsl`, `ssh`) a search of the root with a Unix tool is not
  questioned, only one of a folder below it; a path given through a variable (`$DIR/data`) is not followed; a
  command word spliced from quoted pieces, quoted with a blank in its path or quoted behind a wrapper with a
  word for an option (`g'r'ep`, `"C:/Program Files/Git/usr/bin/grep.exe"`, `sudo -u me "grep"`), is not
  recognised, and a `**` that stands alone is not read as a
  path (`ls **` under bash's globstar); a link that one line makes and reads through (`ln -s data d2; cat d2/…`)
  is not followed, as it is in every later call; a heredoc line that starts with `find` or `tree` is read as a command;
  a command line inside one quoted argument (`Start-Process -WorkingDirectory data cmd '/c type test\x.csv'`) is
  not read; and program code that moves the tree (`shutil.move`, .NET's `Directory.Move`) is not parsed. A walk
  in program code is seen in two forms only: a .NET call with `AllDirectories`, and, since 14 November 2026,
  Python code that an interpreter is handed on the line (`python -c`, a here-document or standard input it
  reads) with `os.walk`, `Path.rglob`, `shutil.copytree`, `shutil.make_archive` or a `**` in a string; such a
  walk is asked about also where its folder is a variable or the `**` stands in prose. Not seen: a walk in a
  script file, in another language or through `tarfile`'s `.add()`, a here-document that a command writes into
  a file, and a shell command inside a string of program text (`os.system('find data -type f')`), which is
  checked only for the paths it names. One more limit, measured on 13 November 2026 with 19,000 and with
  20,500 files in front of a sealed one: the look on disk stops after 20,000 files per folder it walks, and a
  sealed file beyond them is not seen, so the command passes. Where a sealed pattern begins with `**/`, that is
  any recursive command or search over a folder, the project root included, in which more than 20,000 files come
  before the sealed one. Where a pattern names some files of a folder (`data/held/*.csv`), it is such a command at
  the project root, or the Grep tool from a folder above, when more than 20,000 other files of that folder come
  first. Where a pattern seals a whole folder (`data/test/**`), the guard walks that folder on beyond the 20,000
  files for up to five seconds of the hook call, and a walk that the time ends counts as reading it, so the
  search is asked about (since 14 November 2026; before, `grep -r --include='*.csv' x .` over a folder of 25,000
  images and a label file passed). A sealed file that a command names is refused at any size.
  Keep a test split of that size outside the repository.
- Other checkouts of the repository: the guard applies the project's rules to run snapshots, to the main checkout
  and to every worktree that git has registered, wherever it lies (it reads the list from git's own files), and
  it combines their configs: what any checkout seals or freezes is sealed or frozen in all of them (closed and
  tested on 12 November 2026). A plain copy of the project, or a second clone in another folder, is a
  different project to the guard: its files are not covered from here. Keep the test split outside the
  repository if copies exist.
- Sessions started in another checkout: those rules reach the other checkouts' files, but they bind only a session
  in which the guard runs. Claude Code reads `.claude/settings.json`, and with it the hooks, from the folder the
  session starts in. A session started in a checkout without the kit's settings (a worktree on a branch without
  the kit, or the main checkout when the kit lives in a worktree) therefore runs unguarded and can read what the
  project seals there; so does one started in a subfolder of the project, so start the agent at the project root.
  `expctl selftest` warns when the repository has checkouts without the guard. `install.py --target DIR
  --worktrees` registers it for them: one hook entry in `.claude/settings.local.json` of each such checkout, and on
  Linux and macOS of the main checkout as well, because Claude Code reads
  that file from the session's folder on Windows and from the main checkout's root on Linux and macOS, and a
  worktree session started from its desktop app takes settings, hooks, skills and agents from the main checkout's
  root (code.claude.com/docs/en/settings and /worktrees, read 13 November 2026). The entry runs this project's guard with this project's config and audit log and does
  nothing in the project's own sessions. Git is told to ignore that file (one line in `.git/info/exclude`); a
  local settings file that git tracks, that cannot be read as settings or that cannot be written is left alone
  and named. Checked live on native Windows with a headless
  session in a worktree without the kit, once with the kit in the main checkout and once with it in another
  worktree (Claude Code 2.1.322, 13 November 2026): the session read a sealed file before the option was run and
  was refused after it, with the refusal in the kit checkout's guard log. Not checked live: Linux and macOS, and
  the desktop app's worktree sessions. Limits: Claude Code only; a worktree
  added later needs the installer again; a desktop-app worktree session gets the guard this way but the skill and
  the subagents only if the main checkout has them; each tool call in those checkouts costs one guard run, and on
  Linux and macOS each call in the project's own sessions one interpreter start; and if the project folder is
  moved or deleted while the entries exist, every tool call in those checkouts is refused, with a message that
  names the entry, until the kit is back or the entries are deleted (`--uninstall` removes them).
- Sealed data behind a link (a symlink or a junction, to storage outside the repository or into another
  checkout) is sealed at the link and at its real place, for reads and for searches. The guard judges a search
  by where the files really lie, as ripgrep does: a search of a linked data folder is refused even where git
  ignores the link (compared with ripgrep 15.2 on Windows, 12 November 2026). So if a link ends in a folder of
  another checkout that git does not ignore there, a search of that whole checkout is refused as well: keep
  linked data in a folder that git ignores, or outside the repository. A hard link to a sealed file cannot be
  told from its path; making one names the sealed file, which the guard refuses. A run's snapshot judges every
  source file by its real place as well as by its name (since 14 November 2026): a sealed file that a junction
  or a link gives a second name (`alias` leads to `data`, and git lists `alias/test/x.csv`) stays out, where it
  was copied in under the link's name before, and a link to a folder that would lead out of the snapshot is
  linked without the sealed paths below it. Where the sealed folder is itself a link to storage elsewhere
  (`data` leads to another drive, `data/test/**` is sealed), a file is also judged by the name the sealed
  pattern has for that storage: a second link to the storage, to `data` or to its sealed folder brings no
  sealed file into a snapshot or a remote run's archive. Where the filesystem ignores case (Windows, macOS), the run tools
  read the sealed, frozen and editable patterns that way too, as the guard did already: `data/Test/x.csv` is
  the file that `data/test/**` names, in snapshots, in the loop's checksums and in a remote run's archive.
  Limits: making a junction or a link to a folder with sealed files is not asked about. A link inside a
  git-ignored folder is not looked into when the sealed pattern begins with a folder's name: with `data/test/**`
  sealed and `cache/alias` leading to `data`, the folder `cache` is linked whole, and a run's own code can reach
  the sealed files through it (a pattern such as `**/test/**` finds them there and keeps them out). And name
  sealed data by its path in the project (`data/test/**`): a sealed pattern written as an absolute path does
  not keep a git-ignored link to that folder out of a snapshot (tried on Windows, 14 November 2026).
- Sealed files that git tracks are a gap. The guard checks the paths a command names (`git show <rev>:<path>`
  is refused), and git prints a tracked file without being given its name: `git log -p`, `git show <commit>`.
  Keep the test split out of git. `expctl selftest` warns when sealed paths are tracked; a line
  `<pattern> -diff` in `.gitattributes` keeps those two commands and `git diff` from printing the content
  (checked with git 2.52), not `git cat-file` or an archive. The loop's Claude Code sessions have no shell.
  Files that git ignores get into its store by a forced add (`git add -f data`, `-Af`, `--force`, a wildcard) or
  a stash of everything (`git stash --all`), from where `git diff --cached`, `git show` and `git stash show -p`
  print them without naming one: the guard asks when sealed files lie below what such a command takes (since
  14 November 2026). An ordinary add and `git stash -u` take only what git does not ignore and stay unasked, so
  keep the sealed files ignored.
- The rule against starting the final evaluation directly compares commands. It knows the configured command
  after `cd`, in a chain and behind `py` or `cmd /c`; a wrapper script or an option with a value
  (`python -X dev ...`) gets past it. `sealed_tokens` is the stronger rule: a command that names the variable
  your evaluator needs for the test split is refused, however the rest of it is spelled.
- It fails safe: an unreadable hook input is refused, also one that is nested too deeply to read (since
  14 November 2026; before, the guard ended with an error there, which an agent program takes for a hook that
  failed); an unreadable config or an internal error turns every
  action, reads included, into a question (a refusal where nobody can be asked). So does a check that takes the
  guard longer than 12 seconds (a path on a server that does not answer, a line with very many different
  searches): its hooks give it 15 to 20, and not every agent blocks a call whose hook ran out of time. Claude Code
  older than 2.1.295 lacks the `onFailure` setting that blocks tool calls when the hook cannot run at all. Run
  `expctl selftest` after changes.
  The two subagents' own hook carries the same setting. Claude Code runs a project subagent's own hooks only in a
  folder whose trust dialog was accepted, and never in a `-p` session; the project-wide guard applies the
  read-only rule to their calls either way. That rule refuses the write verbs, redirects, formatters and code
  that writes; it does not read output options, so `sort -o notes.txt notes.txt` passes it (a frozen or harness
  file there is asked about by the guard's own rule). Checked live with the two agents passed through `--agents` (Claude
  Code 2.1.322, native Windows, 12 November 2026): a hook that cannot run blocks the call with the setting and
  lets it through without. Not checked live: the agent files themselves in a trusted folder.
- The receipt of the final evaluation is a record, not a seal: it counts the uses that went through
  `expctl final-eval` in this checkout and in every worktree that git has registered, and a copy of its rows in
  git's common folder (`.git/nn-training-final-eval.jsonl`) keeps the uses of a worktree that was removed.
  Deleting `.claude/state/final-eval/` and that copy resets the count (the guard asks before a command or an edit
  touches either; the journal entry of each use remains). Of two that are started at the same moment, one runs:
  the other finds the first one's row ahead of its own in the record, gives way before it starts the command,
  and stays in the receipt as an attempt, which counts as a use afterwards (since 15 November 2026; both ran
  before).
- A plain `expctl launch` hands the run your whole environment. The loop withholds variables whose names look like
  secrets, and a remote run gets only the variables you name.
- What counts as a run's source, since 14 November 2026: agent configuration (`AGENTS.md`, `.mcp.json`, `.codex/`,
  `.cursor/`, `.agents/`) is left out of the source hash, the snapshots and the remote bundles, so the hash of a
  project that tracks such files, or does not ignore them, changes once. The journal, the search's storage file
  and the runs folder no longer make a tree `dirty`.
- An interpreter path with spaces is quoted in hook commands; PowerShell and Codex on Windows cannot run that form.
- In a virtual environment on Windows, a program that a command names without a folder (`python` in a launched
  command, in a final evaluation command, in the loop's evaluator, in an `on_finish` command, and after
  `env --python`) is looked for first beside the interpreter that runs the kit, as `<name>.exe`. Where the
  interpreter of an environment made by `venv`, virtualenv or uv runs the kit, that is the environment's `Scripts`
  folder: `python` is the environment's interpreter, and so is every other program with an `.exe` there, which the
  commands that pip installs have (`transformers`, `tqdm`), whether or not the environment is activated and
  whatever `PATH` says. A conda environment has its interpreter in its own folder and those commands in its
  `Scripts` folder, so there only `python` and `pythonw` come from beside the interpreter and the commands from
  `PATH` as before (by conda's layout: no conda was at hand to run it). Until 20 November 2026 the base
  interpreter's folder came first instead: `python` and `pythonw` were the base interpreter, which has none of the
  environment's packages, and the environment's other programs were found through `PATH` only. A name with another
  ending than `.exe` and a name with no `.exe` beside the interpreter are found as before; a name with a folder is
  the file at its path (the next entry). Where another interpreter than the environment's runs the kit, `python` is
  that interpreter: name the environment's interpreter by its path. A run that began with the kit as it was before
  and is resumed with it as it is now has its first part from the base interpreter and its second from the
  environment's: where the run logger is used, the two parts' `env.json` name the two, and the kit records a run's
  interpreter nowhere else. A campaign of the loop that goes on across that change starts its later runs and its
  evaluator in the environment's interpreter, and nothing records the evaluator's. The programs of a remote target's
  `exec` and `hf` lists are found as before.
- On Windows the kit starts a command without a shell, and what Windows then finds is narrower than what a shell
  finds (measured on 20 November 2026 on Windows 11, under Python 3.8 to 3.14). A name without an ending is started
  as its `.exe` and as nothing else: a command that only a `.cmd` or `.bat` file answers to (`npm`, for one) needs
  that ending written, and `python3.12` needs its `.exe` written, because Windows takes the `.12` for an ending. A
  program named with a folder (`venv/Scripts/python`) is the `.exe` or `.com` file at that path, `.exe` where the
  name has no ending, and since 20 November 2026 the kit hands that file to Windows itself, so it starts whichever
  way its slashes point. Until then a relative path with forward slashes, and without `./` or `../` in front, was
  not started where the environment holds the variable `NoDefaultCurrentDirectoryInExePath`, which the shells of the
  Claude Code session of that day did. A relative path is read from the same folder on Windows and elsewhere since
  21 November 2026: from the project root for `final-eval`, for a remote target's `on_finish` command and for the
  loop's evaluator, which are settings of the project; for a launched run from the folder it works in; and from the
  folder the command is typed in for the path after `env --python` and after the loop's `--agent-exe`, which are
  typed there. Until then Windows read the evaluator from the folder the loop was called in, which only `--detach`
  made the project root; outside Windows the path after `env --python` was read from the project root; and the
  agent's program was read where the command was typed by the check before the start only: a session, which starts
  in the worktree, read it from there outside Windows and did not find a batch file on Windows, and a loop started
  with `--detach` read it from the project root. (Tried on Windows and in WSL, not on a Mac: `env --python`; the
  evaluator by the loop's own start of it, not by a whole campaign; the agent's program by campaigns with a stand-in
  agent, not with a real one.) A batch file stays Windows' to find and `cmd.exe`'s to run: name it with backslashes
  (`scripts\final.cmd`) or by its full path, because by a relative path with forward slashes it runs only in quotes,
  and only where that variable is not set. And `cmd.exe` reads the path it is given. Where the path has no space, so
  that nothing puts it in quotes, `cmd.exe` ends it at a `&`, a comma, `;`, `=`, an opening bracket and a space sign
  other than a space or a tab (a no-break space, for one), drops a `^` anywhere and an `@` in front, and reads an
  option at a `/` unless the path begins with a drive letter or with `/`. In quotes too it puts a value where a
  variable's name stands between two `%` signs: a variable of the start's environment, or one of seventeen that have
  a value in `cmd.exe` without being there (`CD`, `DATE`, `RANDOM`, `FIRMWARE_TYPE` and others). And in quotes too
  it finds no file by a path that ends in a dot, which Windows, for which dots and spaces at a path's end do not
  count, hands it as the batch file's. The batch file then does not start, or another file does: for `a^b\x.cmd` the
  one at `ab\x.cmd`. Since 21 November 2026 the kit refuses such a path before it starts anything, with a sentence
  that names the sign or the variable: `final-eval` before it records the use, where double quotes around the path
  in `final_eval_commands` make it start (a path that ends in a dot it refuses as not found, by its older check),
  and the loop for its evaluator and for the agent's program, each as the loop will hand it to Windows. (Measured on
  21 November 2026 on Windows 11 under Python 3.8 and 3.11, by 526 starts in each of three settings of that
  variable: set for the kit and for `cmd.exe`, set for the kit alone, and not set. Four of the seventeen names and
  the dot at the end were measured under Python 3.11 alone: `cmd.exe` was asked for 4,316 candidate words with an
  empty environment and for each name of one environment with that name taken out, and the rule agrees with each of
  696 further starts, with that variable set and not set. The refusal is not made for the programs of a launched
  run, of `on_finish`, of `env --python` and of a remote target's `exec` and `hf` lists, nor for the interpreter of
  the `python` setting where the loop starts it itself, to compare the Python files of a change. A path that begins
  `\\?\`, which `cmd.exe` took in no form, is not refused, and neither is one with `.` or `..` as a folder behind
  the file's name (`a\x.cmd\.`), which Windows takes as the file's and `cmd.exe` found in none of 148 starts. And
  `cmd.exe` was measured with delayed expansion off, as it is unless a machine's settings turn it on.) `cmd.exe`
  reads a batch file's arguments too, and they reach it in quotes only where they have a space or a tab, or are
  empty. Outside quotes it ends the command at a `&` and a `|`, reads a redirection at `<` and `>` and drops a `^`;
  every `"` is a quote for it, also one inside an argument, which Python writes as `\"`. In quotes too it ends the
  line at a line break and puts a value for a variable between two `%` signs: for its name, for the name with `:~`
  and numbers or with `:` and a text that has a `=` behind it (`%CD:~0,2%`), and for `%=C:%`, the folder `cmd.exe`
  stands in. The text in front of that `=` may itself hold a `%`, though not as its first sign (`%CD:a%b=c%`):
  `cmd.exe` reads on to the `=` and to the next `%` behind it, across words and quotes. A `%` right behind the colon
  ends a name instead, with the colon as its last letter: `%CD:%b=c%` arrives as written unless a variable is named
  `CD:`. The program behind the batch file then gets other arguments, or none, or another command runs. Since 21
  November 2026 the loop's check before a campaign refuses such arguments, with a sentence that names the sign or
  the variable: its evaluator's as `loop.eval_command` gives them, with a run's folder and with the self-test's for
  `{run_dir}`, and the agent's as a session hands them over, once the agent's `--help` has said whether the
  worktree's settings file is among them. By then the agent's batch file has been started once, for `--help`, and
  the evaluator's not at all. The self-test's folders and that file lie in the project, and so does a run's folder
  unless `runs_dir` names a place outside the project or a link to one; a batch file that gets one of them is
  refused where that path holds a variable's name between `%` signs, or a `&` or a `^` and no space. Three things
  are so since 24 November 2026, after a reader had gone through the check. The rule reads a text in front of a `=`
  that holds a `%`: until then it read that text to the first `%` and named nothing for such an argument. The
  sentence names such a variable as far as the `%` behind the `=`, which is the text `cmd.exe` acts on. A run's
  folder is asked by the path a launch reports, which for a link is the folder it leads to: until then it was asked
  by the link's own path, which shows nothing of a sign in that folder's name. Where the path a launch reports is
  not to be had (links that lead back to each other, a name that Windows refuses, a `runs_dir` that is no path), the
  folder is asked by its own path and the check passes it on, as it did before that day: the first launch is what
  ends then, with a traceback. And a variable in the agent's arguments is one of a session's environment, which is
  the loop's without the names of a session above the loop (`CLAUDECODE` and others) and with the two names the loop
  gives a session: until then those names were asked too, and a `--model` that names one was refused though it
  arrives as written. `final-eval` needed no change: its older check refuses each of those signs, as needing a
  shell, in its command and in the arguments behind it. (Measured on 21 November 2026 on Windows 11 under Python 3.8
  and 3.11, alike under both: 7,597 starts of three batch files, with 144 signs and words in up to nineteen forms of
  an argument list. 2,835 of them were of a batch file that hands on all its arguments (`%*`): the rule names
  something in each start where they did not arrive as written, and in 77 where they did, because it refuses
  whatever follows `:~` behind a name (`%CD:~x%`) and `%=D:%` for every drive. The rule as repaired answers each of
  those starts as before. On 22 November 2026, 83 further starts of such a batch file, alike under both Pythons, had
  a `%` in the text in front of the `=` and the other words a reader had asked about. In 21 of them the arguments
  were changed and the rule named nothing; it names each since the repair. In two the kit's rules still name
  nothing, one for an argument and one for a batch file's path: there the start inherits an environment with
  `=ExitCode`, a name that `cmd.exe` sets once it has run a program and that Python's `os.environ` does not show, so
  the environments the loop makes for its evaluator and for a session lack it. Of the starts read here only the
  agent's `--help` inherits the loop's environment: where the loop is called at such a prompt and the agent's batch
  file lies in a folder named with `%=ExitCode%` and a space, `--help` finds no file, the check says nothing and the
  loop takes the agent for one without `--restricted` (found that day, and left as it is). And the rule refuses nine
  that arrived as written: two with `:~` behind a name, one with a name that only an environment made for the trial
  had (`%=::%`), and six whose name has a letter that Python's capitals change and Windows' do not (`ß`, for one).
  It compares names by Python's capitals, which put together every pair of letters that Windows' own table does (973
  in the first plane, all tried), so no name is missed that way. A run's folder was put to the check as a full path
  outside the project and behind a junction; a symbolic link, which Windows did not let the trial make, and a share
  on another machine reach it by reading alone. On 24 November 2026, 18 further starts, alike under both Pythons,
  asked what may follow the colon (a `%` at once, a `*`, a `~`, a `=`); the rule fits each. And a runs folder whose
  path is not to be had was put to the check on Windows and in WSL, under four Pythons: two links that lead back to
  each other, a name with a NUL and a number in each, and on Windows names that Windows refuses. Not refused: a
  comma, `;`, `=` and a space sign other than a space, which change nothing there and part two arguments for a batch
  file that reads them by number (`%1`), which is that file's own affair; and the arguments of the other starts
  named above, which no check reads. The agent's arguments were put to the check for Claude Code, with a stand-in
  agent; Codex's and Cursor's lists were put to the rule alone, with and without a model, and hold no sign of their
  own. Delayed expansion was off here too.) The agent's program, and the loop's evaluator where the loop is called
  outside the project root, need
  no backslashes since 21 November 2026: the kit makes their relative path a full one, so the program, a batch
  file too, starts whichever way its slashes point, where the full path is none that is refused. Called in the
  project root, as a loop started with `--detach` is, the evaluator's path goes to Windows as written, so a
  batch-file evaluator named with forward slashes is refused there. `final-eval` checks its program before it
  records the use, and since 20 November 2026 the check asks as the start will. It refuses, with nothing recorded, a
  name that only a batch file answers to, a name with a dot that only an `.exe` stands behind, a script named
  without its interpreter (`eval.py`), a batch file by a relative path with forward slashes and, where that variable
  is set, a program named without a folder that lies in the project root only; where Python's own search
  (`shutil.which`) finds a file for the name, the refusal names that file and says what Windows starts. Which names
  get that hint differs with Python's version: only from 3.12 a name with a folder that needs an ending added
  (`tools\final`), only up to 3.11 the program in the project root where that variable is set. Until then those
  passed: the use was recorded, the start failed, and the next call needed `--again` with that reason; and under
  Python 3.11 and older the check refused `venv\Scripts\python`, which would have started. What the check leaves:
  Windows also looks beside the running program (in a virtual environment, the base interpreter's folder) and in its
  own folders before `PATH`, and the check does not, so a program that only they hold is refused (System32 and the
  Windows folder are on an ordinary `PATH`); it sees that a file is there and not whether Windows can start it, so a
  file that is no program under a program's ending fails at the start with the use recorded, and the Microsoft
  Store's `python3` alias on a machine without the Store's Python starts, prints a hint and ends; and a batch file
  that the kit's `PATH` holds is looked for once more by `cmd.exe`, by the `PATH` of the command. The check also
  refuses, before any use, three kinds of name that Windows starts: a name with a dot behind a folder, where the
  path is a full one or begins with `.\` or `..\` (`.\tools\tool3.11`) and Windows adds the `.exe` itself, so write
  the `.exe`; a program under another ending than `.exe`, `.com`, `.bat` or `.cmd` (tried with `.scr`); and a name
  with a dot or a space at its end, where `tools\tool.` is Windows' name for a program file without an ending. A
  `PATH=...` written in front of the command reaches the program that is started and not the search for it, which
  goes by the `PATH` the kit runs with. Outside Windows the start searches by that `PATH=...`, and since that day
  the check does too (tried on Linux); an empty `PATH=` it refuses, though the start then looks in the current
  folder.
- Not verified live: the loop with Claude Code on Linux (it ran live on native Windows only); a loop stop caused
  by a rate limit, a usage cap or paid usage (tests only); Codex and Cursor sessions; the Hugging Face Jobs route
  (it needs your account and a paid canary: `references/remote.md`); on macOS and bare Linux everything but
  the kit's tests ("By platform").
- A campaign's best score is selected among many tries on one validation split, so it is biased upward. A campaign
  that kept something therefore ends with a confirmation: the loop trains the start and the kept version on fresh
  seeds and reports whether the gain holds. Once a change is kept, the loop holds back the runs for that from the
  run and time limits (two seed panels), so a small run limit leaves fewer iterations; `"confirm": false` in the
  `loop` section turns it off. It uses the validation split, so follow Phase 5 before you claim a result.
- The loop's keep rule is strict when a campaign is young. With three seeds a change must gain 2.3 run-to-run
  deviations at first and 1.7 after eight seed panels. A gain above two thirds of that margin is measured on a
  second seed panel and decided on all seeds; late in a campaign that can use the runs the confirmation needs,
  which is then reported as not run until `nnloop resume` with a higher limit. In simulation one comparison keeps a change without effect in
  2.1 to 2.3 % of cases and a real gain of two deviations in about 60 % at a campaign's first change and about
  80 % once several panels are behind the noise estimate. The confirmation is a single look and
  confirms such a gain in about half of the cases. More seeds buy power, at the cost of runs
  (`references/loop.md`, "The keep rule").
