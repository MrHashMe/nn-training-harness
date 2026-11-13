## Neural-network training rules (nn-training harness)

Use the `nn-training` skill for any training, fine-tuning, tuning, monitoring, diagnosis or evaluation work.
When rules conflict: protect existing work > validity > honesty > the user's instructions and budget > better metrics > speed.

- **State comes from the harness, not from memory.** Before acting on runs: `python3 .claude/skills/nn-training/scripts/expctl.py status --brief` (JSON without `--brief`).
- **Launch training through `expctl launch`** (background, logged, with provenance and a source snapshot; pass the seed to both `--seed` and the trainer). Long training does not run in the foreground. Wait with `expctl watch` instead of sleep loops, and check the wiring with `expctl selftest`.
- **A live run is work in progress that cannot be redone for free.** Stopping, restarting or changing a running job, and deleting or overwriting a run's snapshot, logs or checkpoints, need the user's go-ahead in chat; with it, stop gracefully with `expctl stop`. Launching, reading and comparing runs need no approval.
- **Test data is sealed and the evaluator is frozen** (see `.claude/nn-training.json`), so that a better score always means a better model. Do not change what is measured to make a candidate win: evaluation code, metrics, splits, data, budgets, timers. If the evaluator has a real bug: stop, explain, and continue under a new protocol version once the user approves and the baseline is re-run.
- **One controller, one source of truth:** one search controller per study and one primary tracker. Compare only at equal, declared budgets; a changed objective is a new study.
- **Every experiment goes into `experiments/JOURNAL.md`** (hypothesis, change, budget, runs, measured result, decision). Failures stay in, with their reasons; past entries are not edited.
- **Claims need evidence:** number of seeds, spread and the noise floor; no luckiest-seed claims; measured results kept apart from hypotheses. Have `experiment-reviewer` check a claimed improvement, and the plan for the final test evaluation, before you report the one or run the other.
- **Keep the context clean:** read curves with `expctl curve`, not raw logs; give log, trace and error deep-dives to `run-analyst`.
- **Get the user's go-ahead before:** new or paid compute, a larger budget, deleting data or results, changing dependencies while runs or studies are active (use `uv run --frozen` or `--no-sync` meanwhile), changing the protocol or a split, pushing or publishing.
- **When nobody can be asked** (a headless or unattended session): take none of the actions that need a go-ahead. Finish the work that needs none, write what is waiting and why into the journal, and stop.
- **The guard hook enforces part of these rules.** A refusal from it is a decision, not an obstacle: do not reach the same effect another way (another tool, a script, a copy of the file).
