## Neural-network training rules (nn-training harness)

Use the `nn-training` skill for any training, fine-tuning, tuning, monitoring, diagnosis or evaluation work.
Priorities when rules conflict: protect existing work > validity > honesty > the user's instructions and budget > better metrics > speed.

- **State comes from the harness, not from memory.** Before acting on runs: `python3 .claude/skills/nn-training/scripts/expctl.py status --brief` (JSON without `--brief`).
- **Live runs are untouchable without explicit OK in chat:** never stop, restart, modify, overwrite or delete a running job, its code snapshot, logs or checkpoints. Use `expctl stop` (graceful) only after approval.
- **Launch training only via `expctl launch`** (background, logged, provenance, immutable source snapshot; pass the seed to both `--seed` and the trainer). Never run long training in the foreground; never poll with sleep loops — wait with the Monitor tool on `expctl watch`, or re-check on a schedule. Check wiring with `expctl selftest`.
- **Test data is sealed and the evaluator is frozen** (see `.claude/nn-training.json`). Never improve a score by changing what is measured: no edits to evaluation code, metrics, splits, data, budgets or timers to make a candidate win. A real evaluator bug → stop, explain, new protocol version with my approval, re-baseline.
- **One controller, one source of truth:** one HPO controller per study and one primary tracker. Compare only at equal, declared budgets. New study when the objective contract changes.
- **Every experiment goes in `experiments/JOURNAL.md`** (hypothesis → change → budget → runs → measured result → decision). Failures stay failures, with reasons. Never edit past entries.
- **Claims need evidence:** report n seeds, spread and the noise floor; no luckiest-seed claims; separate measured results from hypotheses. Get `experiment-reviewer` sign-off before declaring an improvement or running the final test evaluation.
- **Keep the context clean:** read curves with `expctl curve`, not raw logs; delegate log/trace/error-analysis deep dives to the `run-analyst` subagent.
- **Ask before:** new or paid compute, budget increases, deleting anything, dependency changes while runs or studies are active (use `uv run --frozen`/`--no-sync` then), protocol or split changes, pushing code.
