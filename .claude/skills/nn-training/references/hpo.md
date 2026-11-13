# Hyperparameter search playbook (Optuna-first)

Checked: 2026-11-11 (Optuna 5.0.0, released 2026-09-07; no newer release)
Refresh: check the Optuna release notes for sampler, pruner and storage names in the installed version
(`python -c "import optuna; print(optuna.__version__)"`); scout (`scouting.md`) for newer search methods.

Read when you propose or launch any search.

Every item here is a hypothesis to test under the project's protocol (one change, declared budget, paired seeds, a
margin above the noise floor), not a default to switch on. Optimizer and schedule choices are in
`optimization.md`.

## 1. Decide whether to search at all
- Search numerically only over parameterised choices whose effect you cannot reason out. Use reasoning for
  hypotheses, bug fixes, architecture ideas and search-space design.
- An agent may add proposals only as a capped minority inside a sampler-driven study (section 8); restricted to a
  fixed space it did worse than random search in one study.
- Classify every hyperparameter: scientific (what the round measures), nuisance (re-tune so the comparison is fair),
  fixed. (source: https://github.com/google-research/tuning_playbook, undated)
- Write the campaign estimate before launching (trials x pilot cost + baseline and confirmation seeds + retries).

## 2. What to tune first
- Learning rate first, log-uniform over 2 to 3 decades around a sensible default. The baseline gets an equally tuned LR.
- A change of batch size, GPU count or accumulation steps also moves weight decay, beta2 and any weight EMA: re-tune
  them, not LR alone (`optimization.md`). In LoRA comparisons treat batch size as a nuisance parameter (source:
  https://arxiv.org/abs/2602.09492, v2 2026-06-01, abstract).
- Adam-family trial budgets (Tuning Playbook): under 10 trials LR only; 10 to 25 also beta1; over 25 also epsilon;
  well over 25 also beta2. Weight decay, warmup and schedule length are nuisance parameters counted against the same
  budget. Never tune the maximum step count inside a study.
- Log-scale positive scale parameters (lr, weight_decay, eps). Make zero explicit (categorical on/off or a
  conditional) instead of a log range that cannot reach 0. Widths in multiples of 8 or 64 (tensor cores).
- Fine-tuning comparisons: sweep the LR separately for each arm at a fixed update count before comparing. Ten LoRA
  methods ended within 1 to 2 percent once tuned, each preferring a different LR range. Cost: more trials per arm.
  (source: https://arxiv.org/abs/2602.04998, v2 2026-05-19, abstract)

## 3. Samplers
`TPESampler` and `GPSampler` default to `n_startup_trials=10`, so at 10 to 30 trials they are mostly random search;
space design, the default-first rule and fresh-seed confirmation matter more than the sampler (source:
https://optuna.readthedocs.io/en/stable/reference/samplers/index.html, stable 5.0).
- Exploration up to about 30 trials: `QMCSampler(qmc_type="sobol", scramble=True, seed=S)` or `RandomSampler(seed=S)`.
- Mixed or conditional spaces, 100+ trials: `TPESampler` (Optuna 5: constant liar, multivariate on; 4.x: set them).
- Small continuous spaces: `GPSampler` (stable in 5.0, needs `scipy`, `torch`; section 9). 1000+ trials: `CmaEsSampler`.
- Official budgets: TPE 100 to 1000 trials, GP up to 500, CMA-ES 1000 to 10000. Pruning works poorly with GP,
  CMA-ES and AutoSampler; pair pruners with TPE, random or QMC.
- Seed a single-process study. With several workers use a different seed per worker (or `seed=None`): equal seeds
  propose duplicate points. Evaluate the incumbent first: `study.enqueue_trial(<baseline params>)`.
- Quasi-random search is reproducible, indifferent to parallelism and lets you change the objective afterwards; the
  playbook points to a scrambled Halton sequence. Validate every point against the declared space.
- Multi-objective studies default to TPE in Optuna 5; prefer one scalar objective plus hard constraints, recorded with
  `trial.set_constraint(name, value)` (feasible when <= 0). `constraints_func` is deprecated (removal planned for 7.0);
  TPE arguments `consider_prior`, `prior_weight`, `consider_magic_clip`, `consider_endpoints`, `gamma`, `weights` too
  (6.0). (source: https://github.com/optuna/optuna/releases/tag/v5.0.0, 2026-09-07)
- Failed trials are invisible to the sampler, so an always-OOM region keeps being proposed (inferred): tighten the range
  in a new study version; never score a failure with a fake value.

## 4. Pruning
- Default `NopPruner`. Always safe: `ThresholdPruner(upper=..., lower=...)` for diverged or NaN trials.
- Rank-based pruning is the riskiest speed-up: about 15 percent of learning curves are ill-behaved and short horizons
  bias towards small learning rates (source: https://arxiv.org/abs/2505.15657, NeurIPS 2025 D&B, abstract;
  https://arxiv.org/abs/1803.02021, ICLR 2018). Use `MedianPruner`/`PercentilePruner` only after a pilot shows the
  metric at the cut point predicts the final one (rank correlation over completed trials; no source gives a
  threshold). Set `n_startup_trials` (5+ completed), `n_warmup_steps` beyond LR warmup, `interval_steps`.
- A run cut at one third of its steps under a decaying schedule is not a short run of the same recipe: fit the
  schedule to each rung or use a horizon-free one (inferred).
- `SuccessiveHalvingPruner`/`HyperbandPruner` only with many trials and informative curves; `min_resource` at least the
  warmup; with TPE every bracket needs its startup trials. `WilcoxonPruner` for fold-averaged objectives;
  `PatientPruner(wrapped, patience=k)` for noisy plateaus. Report at comparable steps. Multi-objective: no pruning.

## 5. Study identity and storage
- Name: `<task>-<protocol vN>-<budget tag>-<space vK>`. Store the contract:
  `study.set_user_attr("contract", {...metric, direction, split/manifest hash, budget, evaluator hash, space,
  optuna_version})`. New study whenever objective, data, split, metric, evaluator or per-trial budget changes;
  `load_if_exists=True` only resumes the same contract. Resuming across 4.x to 5.0 changes sampler behaviour (inferred).
- Storage: `sqlite:///experiments/optuna.db` for one sequential process; `JournalStorage(JournalFileBackend(path))` for
  several processes on one machine; PostgreSQL/MySQL `RDBStorage` for distributed workers. Never point concurrent
  writers at SQLite. On native Windows the journal's default lock fails ("A required privilege is not held by the
  client"); use `JournalFileBackend(path, lock_obj=JournalFileOpenLock(path))` (source:
  https://optuna.readthedocs.io/en/stable/reference/generated/optuna.storages.JournalStorage.html, stable 5.0).
  `RDBStorage` heartbeat plus `RetryFailedTrialCallback` turns crashed trials into FAIL (not re-checked).
- Set `optuna.storage` in `.claude/nn-training.json`; build the URL from `$EXP_PROJECT_ROOT` (runs start in a snapshot).
- Store trial fields with `trial.set_user_attr(...)` (Optuna 5 has no public `set_system_attr`). From 5.0 timestamps are
  UTC and the storage upgrade does not convert old studies: back up first; GPU-hour sums over both need care.

## 6. Budgets across restarts
- Cap totals with `MaxTrialsCallback(N, states=(TrialState.COMPLETE, TrialState.PRUNED))`. `optimize(timeout=...)` is
  checked between trials only: launch the runner with `expctl launch --deadline ...` and stop in the loop via
  `RunLog.should_stop()`. `Study.stop()` does not reach other processes.
- Keep a ledger of runs, GPU-hours and wall time per study. Do not build stop rules on `optuna.terminator`
  (deprecated in 4.9.0, removal planned for 6.0.0).

## 7. Objective template (in-process trials)
```python
import os
import optuna
from runlog import RunLog

def objective(trial):
    params = {"lr": trial.suggest_float("lr", 1e-5, 3e-3, log=True),
              "wd": trial.suggest_float("wd", 1e-6, 0.3, log=True)}
    with RunLog.for_trial(trial, metric="val/acc", direction="maximize", config=params) as rl:
        best, step = float("-inf"), 0
        try:
            for epoch in range(E):
                train_one_epoch(...)
                acc = evaluate(...)
                rl.log(step, epoch=epoch, **{"val/acc": acc})
                if acc > best:  # selection rule: best validation checkpoint
                    best = acc
                    save(rl.path("ckpt", "best.pt"))
                    rl.checkpoint(rl.path("ckpt", "best.pt"), step=step, value=acc, is_best=True)
                trial.report(acc, epoch)
                if trial.should_prune():
                    raise optuna.TrialPruned()
                if rl.should_stop():               # deadline or `expctl stop`: never score a partial trial
                    trial.set_user_attr("fail_reason", f"stopped early: {rl.stop_reason()}")
                    trial.study.stop()              # no new trials after this one
                    raise RuntimeError("trial stopped before its budget was spent")
        except RuntimeError as e:          # e.g. CUDA OOM: record the reason, keep the failure a failure
            trial.set_user_attr("fail_reason", str(e)[:300])
            raise
        if rl.best is None:
            raise RuntimeError("no checkpoint was selected")  # a run without a kept checkpoint has no score
        trial.set_user_attr("ckpt", rl.best["ckpt"])
        return rl.best["value"]           # score of the checkpoint you keep

STORAGE = f"sqlite:///{os.environ.get('EXP_PROJECT_ROOT', '.')}/experiments/optuna.db"
study = optuna.create_study(study_name=NAME, storage=STORAGE, direction="maximize",
                            sampler=optuna.samplers.TPESampler(seed=0), load_if_exists=True)
study.optimize(objective, n_trials=N_THIS_SESSION, catch=(RuntimeError,),
               callbacks=[optuna.study.MaxTrialsCallback(
                   N_TOTAL, states=(optuna.trial.TrialState.COMPLETE, optuna.trial.TrialState.PRUNED))])
```
Use `catch=` only for failure types you want recorded as FAIL while the study continues; never convert a failure
into a fake finite score. A trial cut short by the deadline is recorded as FAIL with its reason (RunLog marks the run
`timeout` or `interrupted`), so it can never win on a partial budget. Launch the study runner itself with
`expctl launch --deadline ...`; trials log to sibling run directories and keep the runner's status alive.

## 8. Agent proposals and confirmation
- Evaluate the incumbent or default first; this captures most of the LLM warm-start benefit. The optimizer drives and
  holds state; the agent adds proposals via `enqueue_trial(params, user_attrs={"source": "agent"}, skip_if_exists=True)`
  up to a hard cap of 10 to 30 percent of trials; harness code rejects proposals outside the declared space. In the one
  study that tested it, a CMA-ES plus LLM hybrid at a 30 percent share was best (0.9739 against TPE 0.9768 bits per
  byte, 3 seeds, within about two standard deviations) and an 80 percent share collapsed. The right share for frontier
  models at small budgets is not established. (source:
  https://arxiv.org/abs/2603.24647, v3 2026-04-04; https://arxiv.org/html/2610.12183v1, 2026-10-08)
- Inside the unattended loop the harness runs a small search of this kind itself when `loop.search_trials` is set
  (`loop.md`, "A search by the harness", added 2026-11-12): a handful of stratified random trials of the settings a
  change leaves open, each on one seed outside the seed panels, and the best one decided by the loop's keep rule and
  its fresh-seed confirmation. It replaces no study: no sampler state, no pruning, one seed per trial.
- Fresh-seed confirmation: reserve the budget before searching (baseline seeds + top 3 configurations x 3 fresh seeds,
  about a third of a 30-run budget; the split is a hypothesis). The keep decision comes only from the confirmation runs,
  judged by the paired rule (`uncertainty.md`). About 10 percent of benchmark cases select a configuration worse than
  the default. (source: https://arxiv.org/abs/2506.19540, AutoML 2025, abstract)
- Best value on a range boundary or most trials infeasible: redesign the space as a new study version. After the
  study: `optuna.importance.get_param_importances` (PED-ANOVA default in 5.0); `optuna-dashboard` (0.21.0).

## 9. Candidates to test, not adopted
- Synchronous successive halving, off until the pilot rank gate passes (source: https://arxiv.org/abs/1810.05934, MLSys
  2020); feasibility probe of a few steps before a full trial; stop when the last k trials gain less than the noise
  floor (source: https://arxiv.org/abs/2104.08166, 2022); Centaur-style hybrid (https://arxiv.org/abs/2603.24647).
- `GPSampler` with lowered `n_startup_trials`: GP-BO 0.432 against TPE 0.344 at 30 evaluations, tabular models only
  (source: https://arxiv.org/html/2610.12183v1, 2026-10-08). NePS 0.17.0 (source:
  https://pypi.org/project/neural-pipeline-search/, 2026-10-02). Data-subset fidelity for LoRA search (source:
  https://arxiv.org/abs/2602.11171).
- Looked at only: AutoSampler (`optunahub.load_module` downloads code from branch main; pass a pinned `ref`) (source:
  https://optuna.github.io/optunahub/generated/optunahub.load_module.html, optunahub 0.5.0); Ax, SMAC3, Syne Tune,
  ifBO, decaying priors, optim-agent, autotune (self-reported), AgentHPOBench.

## 10. Held or rejected: do not reach for these
- Ray Tune (2.60.0): only for PBT, PB2 or several GPUs; Windows is beta, any client reaching a cluster can run code
  (source: https://docs.ray.io/en/latest/ray-security/index.html). Population methods give a lineage, not a re-runnable
  configuration (source: https://docs.ray.io/en/latest/tune/examples/pbt_guide.html, Ray 2.60).
- Rejected: OptunaHub LLAMBO (0.9882, worse than random 0.9873), Rustuna, DEHB (last release 2024-07-11), hyperopt,
  CARBS, `optuna.terminator`.
