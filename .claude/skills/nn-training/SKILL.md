---
name: nn-training
description: Operating procedure and tools for training, fine-tuning, hyperparameter tuning, monitoring, diagnosing and evaluating neural networks in this repository. Use it whenever you launch, watch, stop or resume training runs, check run status, design experiments or searches, read learning curves, compare results, change checkpointing, or run the final evaluation. That covers any request that touches training runs, experiment results, hyperparameter search, the experiment journal, checkpoints, or the test set.
---

# nn-training — how training work is done in this repository

The harness around you is deliberately small: a guard hook that blocks dangerous or invalid actions, a status
injection at session start, a run controller (`expctl`), a run logger (`runlog.py`), a journal, and two read-only
subagents. A strong model with a shell, a filesystem, honest evaluation and good bookkeeping beats elaborate agent
frameworks; spend effort on evaluation hygiene, measurement and plumbing, not on more machinery.

In this skill, `expctl` means `python3 .claude/skills/nn-training/scripts/expctl.py` run from the project root
(use the project interpreter, e.g. `uv run python ...`, when you need the Optuna summary).

## 1. Your tools

| Need | Use |
|---|---|
| What is running / finished / failed, best runs, alerts, GPUs, disk, Optuna studies | `expctl status --brief` (JSON without `--brief`; one run: `--run <id>`) |
| Start a run (detached, logged, provenance, immutable source snapshot) | `expctl launch --name <n> --note "<hypothesis>" [--seed S] [--gpus 0] [--deadline 6h] [--via tmux] -- <cmd...>` |
| Wait for runs without burning context | `expctl watch <run|all> --until terminal --max-time 25m` (one JSON line per event); in Claude Code through the Monitor tool (`timeout_ms` 1800000) |
| Learning curves | `expctl curve <run> --keys train/loss,val/acc --points 40` (downsampled + trend) |
| Stop gracefully (only with the user's OK) | `expctl stop <run> --wait 5m` → RunLog turns SIGTERM into "checkpoint and exit" |
| Continue an ended run from its checkpoint (a new run that names its parent) | `expctl resume <run>` → the script loads from `rl.resume_from` (`references/resume.md`) |
| Final evaluation on the sealed test split: once, with a receipt (only with the user's OK) | `expctl final-eval [-- ARGS]` (Phase 5) |
| Provenance of the working tree | `expctl hash` |
| Is the harness wired up (hooks registered, guard deciding, protocol configured)? | `expctl selftest` |
| Environment facts | `expctl env --python <project interpreter>` |
| Log/trace/error deep dives | `run-analyst` subagent (keeps raw logs out of your context) |
| Methodology/claim review | `experiment-reviewer` subagent (sceptical, read-only) |
| Optional: unattended keep/revert campaign on cheap runs, within limits the user sets | `nnloop.py` in this skill's `scripts/` — read `references/loop.md` first |
| Optional: a run on a remote or rented GPU, under a spending cap the user sets | `nnremote.py` in this skill's `scripts/` — read `references/remote.md` first |

- `runlog.py` (in this skill's `scripts/`) is the run-side half of the contract. Vendor it into the project
  (e.g. `tools/runlog.py`) and wrap the training loop: `with RunLog(...) as rl: ... rl.log(...);
  rl.checkpoint(...); if rl.should_stop(): break`. It has adapters for `transformers.Trainer` (`hf_callback`) and
  Lightning (`lightning_callback`) and `RunLog.for_trial(trial)` for Optuna. Verify adapters in this project.
- The guard hook denies or asks for: sealed test paths/tokens, recursive or wildcard sweeps over a folder that
  holds sealed data, the project root included (name the folders you need, such as `data/train`, or at the root
  filter by file type, such as `--include='*.py'`), edits to frozen evaluation
  files or harness files, edits inside an active run's directory, kill/stop commands while runs are live, deleting
  runs/checkpoints, destructive git, branch switches while a run executes from the working tree, and dependency
  changes while runs are active. If it blocks you, do not look for a way around it: explain to the user what you
  wanted and why. Codex and Cursor hooks cannot ask a person, so there (and in any unattended session) what the
  guard would ask about is refused: give the user the exact command to run themselves.
- Waiting: never `sleep`-poll in the foreground. Use `expctl watch` (each output line is an event; `--until
  terminal` exits when the watched runs finish, `--until alert` also on stalls, failures and NaNs, and every form
  exits after `--max-time` — run it again to keep waiting). In Claude Code run it through the Monitor tool with
  `timeout_ms` 1800000 (its default is 5 minutes, its maximum 30). Without Monitor (Codex, Cursor), run it in the
  background where the agent offers that, or with a `--max-time` below its command timeout. For waits of hours, use
  `/loop` or a scheduled wake-up to run `expctl status --brief` periodically, or end the turn and give the user the
  monitoring commands.
- Seeds and paths: `--seed N` exports `EXP_SEED` (RunLog records it); the training code must actually use it
  (`--seed` argument or `$EXP_SEED`) — `expctl status` alerts when the recorded seed differs. Snapshot runs start in
  `runs/<id>/src` with that copy first on `PYTHONPATH` (so editable installs cannot leak live code in); build paths
  to shared files such as Optuna storage from `$EXP_PROJECT_ROOT`. Snapshots leave sealed test data out entirely,
  whatever the pattern that seals it (`data/test/**`, `**/test/**`, `data/*/test.csv`) and however deep it lies; a
  link inside the project is judged by the place it leads to, and a launch fails where one leads to the project
  folder itself. The final evaluation runs from the working tree (`expctl final-eval`).
- Stopping: `expctl stop` sends SIGTERM to the launched process only (DataLoader workers die on a stray SIGTERM), then
  SIGKILLs the whole group after `kill_after_s`. Launch Python, `torchrun` or `accelerate launch` directly — a shell
  wrapper must `exec` the trainer or forward SIGTERM.
- Distributed runs: RunLog writes files on global rank 0 only; every rank still sees `should_stop()`. All-reduce that
  flag (MAX) each step so all ranks stop at the same step, then checkpoint on rank 0 (or with DCP on all ranks).
- Runs longer than about an hour: launch with `--via tmux` when tmux exists, so the run survives the Claude Code
  session ending. Run directories hold everything needed to inspect a run later.

## 2. Phases and gates (do not skip a gate; record each gate's outcome in the journal)

**Phase 0 — Reconnaissance (read-only, except creating the journal).** Read CLAUDE.md, README/requirements, model, data pipeline, training,
evaluation, configs, dependency files and existing results. Run `expctl status --brief`, `expctl env --python <py>`,
`nvidia-smi` (once), and look for live jobs outside the harness (`ps`, `tmux ls`, `squeue` where relevant): record
pid, run directory, devices, owner, and whether you may touch them. Fill the Project card in `experiments/JOURNAL.md`:
task, regime (scratch / full fine-tune / PEFT / distillation / other), data and permitted use, split protocol,
primary metric + direction, selection rule, constraints, comparison budget unit, compute authorised and already
committed, environment, tracker, live jobs, open questions.
Jobs that run outside the harness (other people's runs, a training job you were not told about) go into
`external_jobs` in `.claude/nn-training.json` (the guard asks before that edit) so that dependency changes are
guarded while they live; kill commands always ask regardless.
*Gate 0:* Project card filled; unknowns that block correct execution collected into one batch of questions.

**Phase 1 — Harness integration.** Keep the existing framework, environment manager and tracker when they work.
Vendor `runlog.py` and wire it into the entry point (per-run checkpoint paths via `rl.path(...)`, loading from
`rl.resume_from` when it is set, `should_stop()` checks). Make sure the training entry point accepts a seed and a config and logs the configured
metric name. Smoke run via `expctl launch` on a tiny budget.
*Gate 1:* `expctl selftest` passes its required checks; the smoke run appears in `expctl status`, writes
heartbeat/metrics/result with the launch seed, saves a checkpoint that reloads in a fresh process with identical
evaluation, and stops gracefully via `expctl stop` (with DataLoader workers running, if the project uses them).

**Phase 2 — Validity audit and protocol freeze.** Follow `references/validity.md`: split/leakage audit, metric
checks, the sanity gate (finite step, initial loss, tiny-subset overfit, shuffled-label control, trivial baselines,
checkpoint round trip, throughput/memory, parameter counts). Then write the protocol into the Project card and
propose the guard configuration for `.claude/nn-training.json` — `metric` (name/direction/select), `sealed_paths`,
`sealed_tokens`, `frozen_paths`, `final_eval_commands`, `optuna.storage` — plus matching `Read(...)`/`Edit(...)` deny
rules for the sealed paths in `.claude/settings.json`. These edits require the user's approval (the guard asks).
*Gate 2:* experiment-reviewer approves the protocol; evaluator hashes recorded; protocol v1 frozen.

**Phase 3 — Baseline and noise floor.** Reuse a trustworthy baseline when provenance matches; otherwise train the
strongest affordable baseline (tuned learning rate at minimum). Measure seed-to-seed spread (`references/uncertainty.md`)
and cost per run (wall time, GPU-hours, peak memory). Present a finite campaign estimate and ask for budget once if
none is authorised.
*Gate 3:* baseline rows with n seeds, mean ± sd, cost per run; budget authorised.

**Phase 4 — Improvement loop.** Scout first: follow `references/scouting.md` to survey current methods for this
task with the web tools you have, and write dated, cited notes under `experiments/scouting/`. Their findings are
hypotheses to test, never defaults; the step installs and runs nothing. Without web tools, skip it and say so in
the journal. Then: one falsifiable hypothesis per change, ranked by expected gain × probability ÷ cost.
For each: scoped change (one idea per commit), smoke check, bounded pilot, comparison at the declared budget against
the paired baseline, decision (retain / revise / revert), journal entry. Use numerical search only for parameterised
nuisance choices (`references/hpo.md`); never hand-pick trial values. Prefer simpler changes at equal results.
Profile before any performance change (`references/performance.md`).
*Gate 4.0:* the journal links the scouting notes, or says why the step was skipped.
*Gate per experiment:* journal entry with numbers from artifacts; reviewer sign-off before claiming an improvement.

**Phase 5 — Confirmation and final evaluation.** Re-run the top configurations with fresh seeds. Freeze the final
procedure in the journal before looking at any test number: configuration, seed(s), training duration, checkpoint
rule. Train the final model if needed. Run the final evaluation once, with `expctl final-eval [-- ARGS]` (the guard
asks the user; the configured command typed directly is refused). Every use leaves a receipt and a journal entry,
even one that fails. A further use needs `--again "reason"`: it is another look at the test data, so the user
decides on it and the report states every use (`references/validity.md`, section 5).
*Gate 5:* reviewer approves; the test result is recorded once and never used for further tuning.

**Phase 6 — Handoff.** Final report (section 6), updated CLAUDE.md commands, journal "next experiments".

## 3. Run contract and states
Run directories live under `runs_dir` (default `runs/`): `manifest.json` (launch provenance: command, source hash,
git commit + uncommitted patch, seed, deadline), `pid.json`, `stdout.log`, `heartbeat.json`, `metrics.jsonl`,
`env.json`, `config.json`, `result.json` (authoritative final state), `exit.json` (exit code).
States: `starting`, `running`, `stalled` (alive but no heartbeat for `heartbeat_stale_seconds`), `completed`,
`failed`, `pruned`, `timeout`, `interrupted`, `incomplete` (exited without finish), `lost` (process gone without any
record), `unknown`. Alerts are observations, not diagnoses: confirm before acting.
Eligible for "top": completed, finite value of the configured metric under the selection rule, and the recorded
checkpoint exists. Nothing is ever invented for missing values.

## 4. Experiment design rules
- Hypothesis template: "If we <change>, then <metric> improves by ≥ <effect> at <budget>, because <evidence>."
- Classify hyperparameters per round as scientific / nuisance / fixed; tune nuisance ones fairly for every arm.
- Equal budgets; same protocol version; paired seeds; complete runs compared with complete runs.
- Optimizer and schedule: the baseline is AdamW with tuned learning rate and weight decay, a short linear warmup
  and, for a fixed budget, linear decay to zero. Muon, Schedule-Free AdamW, SOAP, WSD schedules and μP/CompleteP
  (when scaling width or depth) are controlled alternatives to test against that baseline, not defaults:
  `references/optimization.md` says when each is worth a run and what to expect.
- Keep/revert loops are fine for cheap runs, but need seeds, a noise-floor margin and the sealed test set —
  validation scores alone drift upward under many trials. `nnloop` (`references/loop.md`) runs such a loop
  unattended: the harness, not you, scores each run with the frozen evaluator and decides; what it keeps is a
  candidate that still goes through Phase 5.

## 5. Budget and cost accounting
Count pilots, baselines, seed reruns, retries, start-up/compilation, evaluation, checkpointing and final verification.
Track spent vs authorised GPU-hours (and money for cloud) in the journal after every batch of runs. Stop and ask
before exceeding the authorisation; never start paid resources without explicit authorisation that covers them
(`nnremote` refuses to start anything paid without a cap in the config that covers it, and books it in a ledger).

## 6. Final report (in chat and appended to the journal)
Detected task and constraints · chosen stack and why each component earned its place · protocol and baseline
provenance · what changed and why (retained/reverted) · commands actually executed and verification outcomes ·
measured quality (n, mean ± sd, per-seed), runtime, memory, cost · selected configuration and checkpoint path ·
final test result if run under the protocol · limitations and the next highest-value experiment. Measured results,
hypotheses and proposals are clearly separated. For a run still in progress: verified progress, run id, pid,
checkpoint path, the exact `expctl` watch/status commands and the training command that resumes it — never
imply completion.

## 7. When to proceed, ask or stop
- Proceed: reading, inspection, smoke checks, edits on the working tree for the next run, launches within the
  authorised budget, journal updates.
- Ask (one batched question): budget or new compute, paid resources, stopping/restarting runs, deleting anything,
  protocol/split/evaluator changes, dependency changes while runs are active, test-set evaluation, pushing code,
  starting, resuming or stopping an unattended campaign or a remote run (with the limits or cap you propose).
- Stop and report: repeated guard denials for the same goal, evidence of leakage or a broken evaluator, results that
  contradict the protocol, or budget exhaustion.

## 8. Harness config (`.claude/nn-training.json`; editing it needs approval)
`runs_dir`, `journal`, `metric.{name,direction,select}` (`select`: `best` = selected checkpoint's value, `final` =
final value), `heartbeat_stale_seconds`, `min_free_disk_gb`, `kill_after_s` (grace before SIGKILL on stop),
`snapshot.{mode,max_file_mb}` (`copy` runs from an immutable copy; ignored data/venv dirs, files over
`max_file_mb` and files named like a credential, such as `.env` or `*.key`, are linked, not copied; `none` runs
from the working tree), `sealed_paths` (globs), `sealed_tokens` (strings such as an unlock variable),
`frozen_paths`, `final_eval_commands` (one program call, optionally after `NAME=value` pairs, without shell syntax;
`expctl final-eval` runs it and appends its own arguments), `external_jobs` (live jobs outside the harness: pid,
owner, note),
`harness_paths`, `optuna.{storage,studies}` (`sqlite:///experiments/optuna.db` or `journal:experiments/optuna.log`,
relative to the project root), `limits`, `python` (the interpreter the installer recorded). Optional sections,
absent until the user adds them: `loop` (`references/loop.md`), `remote` (`references/remote.md`). An unreadable
config makes the guard ask before every non-read action.

## References (read when the phase needs them)
Each starts with a `Checked:` date and a `Refresh:` line. A version, price, API name or "best current" claim in a
reference older than about six months is a lead to verify, not a fact.
- `references/scouting.md` — surveying current methods before choosing hypotheses; notes format; refreshing references
- `references/loop.md` — the unattended research loop (`nnloop`): setup, limits, what the harness decides, records
- `references/remote.md` — remote and rented GPUs (`nnremote`): targets, spending cap, what travels, preemption
- `references/validity.md` — protocol, leakage audit, sanity gate, sealed test, evaluator freeze, anti-gaming rules
- `references/data.md` — data manifest, duplicates and split overlap, licences, unsafe dataset files, synthetic data
- `references/evaluation.md` — keep-or-revert decisions, reused validation sets, harnesses, contamination, judges
- `references/uncertainty.md` — noise floor, paired comparisons, winner's curse, reporting
- `references/hpo.md` — when and how to search (Optuna 5), samplers, pruners, study identity, budgets, objective template
- `references/optimization.md` — optimizer and schedule baseline, scaling rules, alternatives worth a controlled run
- `references/performance.md` — profiling, AMP/compile/data-loading levers, adoption rule, OOM triage, multi-GPU
- `references/resume.md` — checkpoint contents, DCP/FSDP2, retention, resume verification, pretrained-model specifics
- `references/finetuning.md` — base model and licence, regime ladder, LoRA/QLoRA, RL post-training, export and reload
- `references/llm.md` — small-model pretraining, tokenizer and chat-template preflight, instruction/preference tuning
- `references/operations.md` — reproducibility, failure recovery, cost, notifications, unattended sessions, supply chain
- `references/stack.md` — the recommended tool combination with pins, optional modules, MCP servers, security notes
