# Scout note: search (hyperparameters, multi-fidelity, population methods)

Date: 2026-11-11. Area: search-hpo. Builds on `.claude/skills/nn-training/references/hpo.md`, `references/uncertainty.md`,
`docs/research-notes/` and `docs/review-findings.md` (kit built 2026-10-23).

Conventions. Every claim was checked on 2026-11-11. Tags read `[Status | source | version or date]`. Verified = read in
the primary source today; Inferred = my reasoning from verified facts; Unverified = not confirmed. "abstract" = paper read
at abstract level only. Source text is paraphrased. No local commands were run (none were allowed for this area).

## Summary (10 lines)

1. Optuna 5.0.0 (2026-09-07) is still the latest release; every version-specific claim in hpo.md checks out, but the file has one native-Windows bug and several omissions.
2. Windows bug: the journal storage's default lock needs symlinks and fails on native Windows without privilege; the documented fix is `JournalFileOpenLock`.
3. At the budgets one GPU affords (10 to 30 trials) model-based samplers are mostly still in their 10-trial random start-up phase, so space design, a seeded default and fresh-seed confirmation matter more than the sampler.
4. 2026 evidence refines "never let the LLM pick trial values": agent proposals help as a capped minority (about 10 to 30 percent) injected into a classical optimizer and as search-space design; agent-only search over a fixed space was worse than random in one study, and high agent shares collapse.
5. No alternative library displaces Optuna as the default optional module; NePS (prior-guided multi-fidelity, coordinated through a shared directory) is the one worth a trial; Ray Tune stays for PBT or multi-GPU only; DEHB and CARBS are stale.
6. Pruning is the riskiest speed-up: about 15 percent of learning curves are ill-behaved in a 2025 database, short horizons bias towards small learning rates, and horizon-tied schedules do not transfer; require a pilot rank check first.
7. Population methods (PBT, evolutionary code search) do not fit a slow, noisy single-GPU scorer: they need many concurrent or cheap evaluations and give results that cannot be replayed exactly.
8. For LoRA fine-tuning the learning rate dominates, variants prefer different learning-rate ranges and batch size matters, so every compared arm needs its own learning-rate sweep.
9. A standard-library core can provide seeded quasi-random search, a default-first and agent-proposal queue, synchronous successive halving, a budget ledger, stop rules and fresh-seed confirmation; Bayesian optimisation, importance analysis, priors and PBT stay optional.
10. Not done: no local trials; many papers at abstract level; Ray Tune with Optuna 5 and native-Windows behaviour of SMAC3, Syne Tune and NePS unverified.

## Q1. Re-check of references/hpo.md against Optuna today

Still correct
- Latest release is v5.0.0, 2026-09-07; nothing newer. Companion releases: optuna-integration v5.0.0 (2026-09-07), optuna-dashboard v0.21.0 (2026-09-10), optunahub v0.5.0 (2026-09-09). [Verified | https://github.com/optuna/optuna/releases/tag/v5.0.0 and the three repos' release lists | 5.0.0]
- The 5.0 claims in hpo.md all hold: multivariate TPE and constant liar on by default for single-objective studies, TPE as the multi-objective default, `trial.set_constraint` with `constraints_func` deprecated, PED-ANOVA as default importance evaluator, GPSampler stable with batch acquisition, public `system_attrs` setters removed. [Verified | same release notes | 5.0.0]
- The Adam trial-budget ladder (under 10 trials: learning rate only, and so on) is still what the Tuning Playbook says. [Verified | https://github.com/google-research/tuning_playbook | undated repository]
- Not re-checked today: RDB heartbeat and `RetryFailedTrialCallback`, `MaxTrialsCallback` wording. [Unverified]

Wrong or risky today
- W1. Section 5 recommends `JournalStorage(JournalFileBackend(path))` for several processes. On Windows the default lock can fail with the error "A required privilege is not held by the client" (Optuna docs); the documented fix is `JournalFileBackend(path, lock_obj=JournalFileOpenLock(path))`. hpo.md, SKILL.md (`journal:` config form) and `expctl.py` line 1003 (`JournalFileBackend(path)`) carry no Windows branch. [Verified for the docs | https://optuna.readthedocs.io/en/stable/reference/generated/optuna.storages.JournalStorage.html | stable 5.0] Whether a read-only summary in expctl also trips the lock is untested. [Unverified]
- W2. "Always seed the sampler" combined with several worker processes: the samplers page says to use `seed=None` or a different seed per process in distributed optimisation, and that results are hard to reproduce when `n_jobs != 1`. Identical seeds across workers suggest duplicate points. [Verified | https://optuna.readthedocs.io/en/stable/reference/samplers/index.html | stable 5.0]
- W3. The AutoSampler line uses `optunahub.load_module("samplers/auto_sampler")`. `load_module` defaults to `ref="main"` of the registry repository and downloads code at run time; a tag or commit SHA can be passed. Unpinned, this conflicts with the kit's pinned-version and offline rules. It also needs `optunahub cmaes torch scipy`. [Verified | https://optuna.github.io/optunahub/generated/optunahub.load_module.html and https://hub.optuna.org/samplers/auto_sampler/ | optunahub 0.5.0]
- W4. Rustuna is listed as 0.1; it is now python-v0.2.1 (2026-10-30, v0.2.0 on 2026-10-26), still self-described as experimental, aimed at tens of thousands of trials, MIT. [Verified | https://github.com/optuna/rustuna | 0.2.1]
- W5. DEHB is listed as a controlled alternative; its last release is v0.1.2 (2024-07-11) and last commit 2025-04-25. [Verified | https://github.com/automl/DEHB | 0.1.2]

Missing
- M1. Start-up phase. `TPESampler` and `GPSampler` both default to `n_startup_trials=10`; the first 10 trials are random. With the "under 10 trials" and "10 to 25 trials" budgets in section 2, TPE is random search for all or most of the study. [Verified signatures | TPESampler and GPSampler reference pages | stable 5.0; consequence Inferred]. A budget-matched tabular study makes the same point: the surrogate only engages at trial 11. [Verified | https://arxiv.org/abs/2606.21641 | 2026-06-19]
- M2. Official trial-budget guidance: TPE 100 to 1000 trials, GP up to 500, CMA-ES 1000 to 10000, random and QMC any number. hpo.md's "CmaEsSampler for hundreds+" is low. Pruning works only inefficiently with GP, CMA-ES and AutoSampler, so pair pruners with TPE, random or QMC. [Verified | samplers index | stable 5.0]
- M3. GPSampler needs `scipy` and `torch` (CPU build suffices) and models observation noise by default (`deterministic_objective=False`). [Verified | GPSampler page | stable 5.0]
- M4. `optuna.terminator` was deprecated in 4.9.0 and is scheduled for removal in 6.0.0, with its function moving to OptunaHub. Do not build stop rules on it. [Verified | https://optuna.readthedocs.io/en/stable/reference/terminator.html | stable 5.0]
- M5. From 5.0 trial timestamps in RDB and journal storages are UTC; studies created earlier can show shifted times and the storage upgrade command does not convert them. Back up before upgrading; GPU-hour sums that mix old and new trials need care. [Verified | 5.0.0 release notes, PR 6776 | 5.0.0]
- M6. Deprecations to avoid in new advice: TPE arguments `consider_prior`, `prior_weight`, `consider_magic_clip`, `consider_endpoints`, `gamma`, `weights` (removal planned for 6.0); `constraints_func` (removal planned for 7.0). New in 5.0: QMC supports categorical parameters; a warning against CMA-ES in constrained problems. [Verified | TPESampler page and release notes | 5.0.0]
- M7. `enqueue_trial(params, user_attrs=None, skip_if_exists=False)`: duplicates can still occur when several processes enqueue at once. `Study.stop()` does not affect parallel or later study processes. `n_jobs` is thread-based. [Verified | https://optuna.readthedocs.io/en/stable/reference/generated/optuna.study.Study.html | stable 5.0]
- M8. Failed trials are invisible to the sampler, so a region that always runs out of memory keeps being proposed. hpo.md rightly forbids fake scores, but offers no way to steer away. [Inferred from Optuna trial-state semantics]. The playbook asks for tools that handle diverging trials. [Verified | Tuning Playbook]
- M9. Open issue: TPE resident memory grows with trial count in long-running studies. Only relevant to very long unattended studies. [Verified | https://github.com/optuna/optuna/issues/6777 | opened 2026-07-28]
- M10. Optuna's own tutorial says Hyperband pairs best with TPE and the median rule with random search, but states that benchmark excludes deep learning. hpo.md's caution on pruning is the better fit for NN training (see Q2, Q4). [Verified | https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/003_efficient_optimization_algorithms.html | stable 5.0]

## Q2. Alternatives and complements, November 2026

Libraries (the "beats Optuna when" column is Inferred from documented features unless tagged otherwise)

| Tool | Version, date, licence | Status facts | Beats Optuna when | Decision |
|---|---|---|---|---|
| Ray Tune | Ray 2.60.0, 2026-11-04, Apache-2.0 | Windows support is beta, multi-node on Windows untested; ASHA recommended over HyperBand; schedulers ASHA, HyperBand, median rule, PBT, PBT replay, PB2, BOHB; `OptunaSearch` requires optuna>=3.0; by design any client that can reach the cluster can execute code on it; token authentication on by default for local clusters since 2.59 and announced for all clusters in 2.61 | PBT or PB2, several GPUs or nodes, fractional-GPU trial packing | Hold, optional |
| Ax + BoTorch | Ax 1.3.1 (2026-06-09, MIT); BoTorch 0.18.1 (2026-06-08) | Python 3.11+, PyTorch 2.4+, JAX now required (NumPyro), legacy `ax/service` API deprecated, `Scheduler` removed for `Orchestrator`, transfer-learning stack opened in 1.3 | noisy objectives with explicit noise models, outcome constraints, transfer across studies | Assess, optional |
| SMAC3 | 2.4.1, 2026-09-10, BSD-3 | scikit-learn random forest is the default surrogate since 2.4.0 (compiled `pyrfr` now optional); racing of configurations across seeds is the core mechanism; docs call Windows via WSL experimental and give no native-Windows path | noisy objectives where seeds are instances; categorical-heavy conditional spaces | Assess, optional |
| Syne Tune | 0.16.0, 2026-08-03, Apache-2.0 | local backend runs trials as separate processes; methods include ASHA, BOHB, BORE, CQR, PBT, median rule, zero-shot transfer; ask/tell exists; now under its own GitHub organisation | asynchronous multi-fidelity over script launches | Assess, optional |
| NePS | 0.17.0, 2026-10-02, Apache-2.0 | Python 3.11 to 3.14; Windows listed in classifiers; optimizers: random, grid, BO, successive halving, ASHA, Hyperband, async HB, ifBO, piBO, PriorBand, PriMO; automatic choice: fidelity plus prior gives PriorBand, prior only gives piBO; workers coordinate through a shared results directory with no server; 89 stars | the user or agent has a prior and a cheap fidelity exists | Trial, optional |
| OSS Vizier | 0.1.24, 2025-02-01, Apache-2.0 | commits continue (2026-10-20) but no release for 21 months; JAX-based GP bandit; has the scrambled-Halton quasi-random search the playbook points to | none on one GPU | Hold |
| DEHB | 0.1.2, 2024-07-11 | no commit since 2025-04-25 | none | Reject |
| HEBO | repository commit 2026-10-12 | research code; PyPI state not confirmed | none shown | Hold |
| Nevergrad | 1.0.12, 2025-04-23, MIT | no release for 18 months | none shown | Hold |
| FLAML | 2.8.0, 2026-11-06 | cost-frugal search (CFO, BlendSearch); not examined further | not shown | Hold |
| hyperopt | 0.3.0, 2026-07-24 | releases resumed; TPE reference implementation | none | Reject |
| CARBS | last commit 2024-06-27 | stale | none | Reject |
| W&B Sweeps | docs now redirect to docs.coreweave.com | grid, random, Bayes; Hyperband early termination (eta default 3); hosted controller | the user already tracks runs there | Hold, optional |

Sources: Ray https://github.com/ray-project/ray/releases , https://docs.ray.io/en/latest/ray-overview/installation.html , https://docs.ray.io/en/latest/tune/api/schedulers.html , https://docs.ray.io/en/latest/ray-security/index.html ; Ax https://github.com/facebook/Ax/releases/tag/1.3.0 and https://pypi.org/project/ax-platform/ ; SMAC3 https://github.com/automl/SMAC3 and https://automl.github.io/SMAC3/latest/1_installation/ ; Syne Tune https://pypi.org/project/syne-tune/ and https://syne-tune.readthedocs.io/en/latest/getting_started.html ; NePS https://pypi.org/project/neural-pipeline-search/ and https://automl.github.io/neps/latest/reference/optimizers/ ; Vizier https://github.com/google/vizier ; DEHB https://github.com/automl/DEHB ; HEBO https://github.com/huawei-noah/HEBO ; Nevergrad https://pypi.org/project/nevergrad/ ; FLAML, hyperopt, CARBS: GitHub release and commit lists; W&B https://docs.coreweave.com/guides/sweeps/sweep-config-keys/ . [All Verified for version, date and the listed facts]

Benchmarks
- carps: 3,336 tasks from 5 benchmark collections, 28 optimizer variants from 9 families, with representative subsets of 10 to 30 tasks. Per-optimizer rankings not read. [Verified abstract | https://arxiv.org/abs/2506.06143 | v2 2025-09-18]
- AgenticBBO-Bench, HPO family (Bayesmark, 5 initial plus 25 new evaluations, 2 runs per task): GP-BO 0.432, TuRBO 0.387, CMA-ES 0.361, TPE 0.344, Sobol 0.302, random 0.273 (normalised score, higher is better). Supports a GP sampler over TPE at about 30 evaluations; tabular models, not NN training. [Verified | https://arxiv.org/html/2610.12183v1 | 2026-10-08]

Multi-fidelity
- ASHA: asynchronous successive halving with aggressive early stopping; scales linearly with workers (shown at 500 workers). Its advantage is parallel workers; on one GPU synchronous successive halving is the same idea without the asynchrony. [Verified abstract | https://arxiv.org/abs/1810.05934 | MLSys 2020; one-GPU remark Inferred]
- PASHA (ICLR 2023) raises the maximum resource only as needed and reports much lower compute than ASHA. Mechanism details not read. [Verified abstract | https://arxiv.org/abs/2207.06940]
- Freeze-thaw with a prior-fitted network: ifBO's FT-PFN extrapolates learning curves in one forward pass, 10 to 100 times faster and more accurate than deep-GP and deep-ensemble surrogates, state of the art on three deep-learning HPO benchmark families (ICML 2024). The `ifBO` package (MIT, 20 stars) limits context to 1,000 configurations and 10 hyperparameter dimensions, with all values normalised to [0,1]; it is exposed in NePS as `ifbo`. No evidence found for LLM fine-tuning curves. [Verified | https://arxiv.org/abs/2404.16795 , https://github.com/automl/ifBO]
- Limits. About 15 percent of learning curves in LCDB 1.1 show significant ill-behaviour, roughly twice earlier estimates (NeurIPS 2025 Datasets and Benchmarks; sample-size curves of tabular learners). [Verified abstract | https://arxiv.org/abs/2505.15657]. That crossing curves make successive halving miss the best configuration more often comes from a search summary of the same paper. [Unverified]. Short horizons bias meta-optimisation towards learning rates that are too small, by orders of magnitude in the paper's experiments. [Verified abstract | https://arxiv.org/abs/1803.02021 | ICLR 2018, older than the 36-month window, foundational]. The playbook advises tuning in rounds with increasing step limits, warns that learning-rate schedules are unlikely to transfer between rounds, and says never to tune the maximum step count inside a study. [Verified | Tuning Playbook]

Population methods
- PBT is greedy; MF-PBT (RL Conference 2025) reports that PBT can fall behind plain random search over long horizons and proposes sub-populations with different evolution frequencies. [Verified abstract | https://arxiv.org/abs/2506.03225]
- Ray Tune's PBT requires checkpoint save and load in the trainable, runs the population as parallel trials (examples use 4 to 8), and its replay utility does not reproduce the original result exactly because only the hyperparameter schedule is replayed. [Verified | https://docs.ray.io/en/latest/tune/examples/pbt_guide.html | Ray 2.60 docs]
- Consequence for this kit: a PBT result is a schedule plus a lineage of checkpoints, not a configuration that can be re-run with fresh seeds, so it conflicts with paired-seed confirmation and the frozen-evaluator keep rule. [Inferred]
- AgileRL offers evolutionary hyperparameter optimisation during a single run, including for LLM post-training; speed claims are the project's own. [Verified README | https://github.com/AgileRL/AgileRL | Apache-2.0]
- Evolutionary search over code: OpenEvolve v0.4.1 (2026-11-02, Apache-2.0, about 7.8k stars; MAP-Elites with islands; examples run 50 to 460 iterations) and ShinkaEvolve v0.0.7 (2026-06-02, Apache-2.0, about 1.5k stars). Neither README shows a neural-network-training example. [Verified | https://github.com/algorithmicsuperintelligence/openevolve , https://github.com/SakanaAI/ShinkaEvolve]. At 5 minutes or more per noisy evaluation, a population cannot be both diverse and replicated inside a 50-run budget; the earlier note's inference stands. [Inferred]

## Q3. Evidence on agent-driven search

- Ferreira et al., "Can LLMs Beat Classical Hyperparameter Optimization Algorithms? A Study on autoresearch": about 50M-parameter language model, 5-minute trials, 24 GPU-hours per method, 3 seeds, 14 hyperparameters. Best validation bits-per-byte (lower is better): hybrid CMA-ES plus LLM ("Centaur", LLM proposes on 30 percent of trials) with Opus 4.6 0.9739; TPE 0.9768; code-editing agent with Opus 4.6 0.9770; SMAC 0.9778; CMA-ES 0.9785; random 0.9873; LLAMBO via its OptunaHub port 0.9882; agent restricted to the fixed 14-parameter space with a 27B local model 0.9904 (worse than random). Classical methods reached a similar configuration about 4 times faster than the code-editing agent. Share ablation with local models: best at 10 to 50 percent, collapse at 80 percent (0.9902, worse than CMA-ES alone). Out-of-memory rate ranged from 1 to 61 percent across methods and mattered more than diversity. Limits: one task, n=3, top methods within one to two standard deviations, LLM time not counted, no multi-fidelity baseline. [Verified | https://arxiv.org/abs/2603.24647 | v3 2026-04-04; code https://github.com/ferreirafabio/autoresearch-automl , MIT]
- Rodrigues et al.: on 8 tabular tasks with 5 seeds the LLM advisor's strong first point is the default configuration; against classical search seeded with that default the LLM leads at 2 evaluations, ties by 5 and trails by 12; a rule-based filter removed out-of-space proposals and about a third of wasted compute. [Verified | https://arxiv.org/abs/2606.21641 | 2026-06-19; tabular, small preprint]
- AgenticBBO-Bench: an agent with code execution beat a direct-prompt LLM in all five domains and the best numerical optimizer in four (HPO included) at 25 to 30 evaluations; adding GP tools did not help on average (0.589 base, 0.574 with GP suggestions, 0.538 with full GP tools); task semantics helped (0.465 anonymous to 0.595), detailed priors were unreliable, and an incorrect prior erased the gain (0.872 with a correct prior, 0.682 with a wrong one, 0.685 baseline); handing the agent's trajectory to a numerical optimizer matched staying agentic (0.570 versus 0.569; the same optimizer from scratch 0.475). Two runs per task; only objective evaluations count towards budget. [Verified | https://arxiv.org/html/2610.12183v1 | 2026-10-08]
- AgentHPOBench: 30 repository-level tasks, one baseline run plus five sequential interventions, 12 agents; qualitative conclusion is measurable ability with clear limits in sustained refinement and log diagnosis. Numbers not read. [Verified README | https://github.com/OpenMOSS/AgentHPOBench | arXiv 2607.29626, Apache-2.0]
- Sara and the `lenz` backend (agent as decision maker over a BoTorch backend) claim BO-level reliability without priors and gains from natural-language priors. [Verified abstract | https://arxiv.org/abs/2608.00316 | v2 2026-08-11; no repository confirmed]
- DynaBO: priors injected at any time, decaying, with a surrogate-based safeguard that can reject misleading priors. [Verified abstract | https://arxiv.org/abs/2511.02570 | v3 2026-07-31]
- LLAMBO reproduction: warm-starting helps early regret; surrogate weaker than GP or SMAC; small backbones unstable. [Verified abstract | https://arxiv.org/abs/2511.18891 | 2025-11-24]
- New tools. optim-agent (MIT, created 2026-07-07, about 800 stars): agent as sampler with ask/tell, validation against the declared space and random fallback; self-reported wins over TPE and random at 10 to 20 trials with 5 seeds, and its own README notes one benchmark's test split was used in selection. At 10 trials the TPE baseline is still in random start-up. [Verified README | https://github.com/Optim-Agent/optim-agent ; start-up remark Inferred]. autotune (MIT, 20 stars): the agent proposes the space, sampler and pruner and revises the space between rounds, Optuna runs the trials, and agent guidance cannot override schema or measurement constraints. [Verified README | https://github.com/RobertTLange/autotune]
- arXiv 2611.12791 (2026-11-09): an LLM trained as a universal searcher; one experiment cost 896 GPU-days. Out of scope for this kit. [Verified abstract]

How to combine an agent with a principled method (design reading of the above; Inferred unless tagged)
1. Evaluate the incumbent or default configuration first; this captures most of the LLM warm-start benefit.
2. Keep the optimizer as the driver and state holder. Let the agent add proposals to a queue (`enqueue_trial` with a `source` attribute) under a hard cap of roughly 10 to 30 percent of trials; the optimizer learns from every result.
3. Validate every proposal against the declared space in harness code; reject or replace invalid ones.
4. Use the agent for what it is measurably good at: reading the code, naming the hyperparameters, proposing ranges, and revising the space between rounds. A revised space is a new study version.
5. Treat agent priors as fallible: prefer methods that decay or reject priors, and never narrow the space on a prior alone.
6. Option for token budgets: agent-led first few trials, then hand the whole history to the sampler.
7. Count agent tokens and latency against the user's limits; the cited studies do not.

## Q4. Practice at small budgets on one GPU

Search-space design
- Few dimensions, log scales for scale parameters, learning rate first, then the playbook's ladder. Check the best point is not on a boundary and that the infeasible share is small; otherwise redesign. [Verified | Tuning Playbook]
- Quasi-random search for exploration: reproducible, interpretable, indifferent to parallelism, allows changing the objective after the fact; the playbook's implementation pointers are a shifted, scrambled Halton sequence. [Verified | Tuning Playbook]

Splitting a fixed budget between configurations and seeds
- With 20 trials on the playbook's ImageNet example, the gap between lucky and unlucky studies exceeds retraining variance (about plus or minus 0.1 percent at 23 percent error). [Verified | Tuning Playbook]
- Overtuning: in a large reanalysis of HPO benchmark data, about 10 percent of cases select a configuration that generalises worse than the default or first configuration; usually mild, worst with small data (AutoML Conference 2025; tabular benchmarks). [Verified abstract | https://arxiv.org/abs/2506.19540]
- Repeating every configuration during search did not reliably find configurations that are better across seeds, and pruning could hurt, in a small 2020 deep-RL study. [Verified abstract | https://arxiv.org/abs/2007.14604 | 2020, older than the window]
- Hypothesis to test, not a default: noise floor from 3 baseline seeds; one seed per configuration during search; then the top 3 re-run with 3 fresh seeds each and judged by the existing paired rule. With a 30-run budget that is 3 + 18 + 9. [Inferred]

Pruning under noisy metrics
- Default to no pruning at these budgets; keep the divergence threshold. [hpo.md, unchanged]
- Before enabling any rank-based pruning, compute the rank correlation between the metric at the intended cut point and the final metric over the completed trials of a pilot; prune only if it is high and the gap being acted on exceeds the noise floor. No primary source gives a threshold. [Inferred]
- Rungs must be comparable: with a decaying schedule, a run cut at one third of its steps is not a short run of the same recipe. Either re-launch each rung with its schedule fitted to that rung's length or use a horizon-free schedule; otherwise low rungs favour small learning rates. [Inferred from https://arxiv.org/abs/1803.02021 and the playbook]

Fine-tuning language models
- Ten LoRA methods re-evaluated with broad searches over learning rate, batch size, rank and duration: methods prefer different learning-rate ranges and end within 1 to 2 percent of each other once the learning rate is tuned. [Verified abstract | https://arxiv.org/abs/2602.04998 | v2 2026-05-19]
- Batch size explains much of the conflicting evidence between LoRA variants; tuned vanilla LoRA often matches them. [Verified abstract | https://arxiv.org/abs/2602.09492 | v2 2026-06-01]. This sits against hpo.md's line that batch size is not a validation-performance knob: record it as dated advice and treat batch size as a nuisance parameter in fine-tuning comparisons. [Inferred]
- LoRA performance on a data subset correlates strongly with full-data performance, which makes a data-subset fidelity plausible for LoRA search. [Verified abstract, read before context compaction | https://arxiv.org/abs/2602.11171]
- Seed effects in LLM fine-tuning: aggregate scores can look stable while per-example predictions differ (10 seeds, IJCNLP 2025); one 2026 study saw outcomes from no degradation to collapse across three extra seeds. [Unverified, search-result level | https://arxiv.org/abs/2503.07329 , https://arxiv.org/abs/2604.12469]

Stopping rules
- Hard caps on runs, wall time and GPU-hours enforced by harness code; `optimize(timeout=)` is checked between trials only. [hpo.md, unchanged]
- Principled rule: stop when the remaining optimisation gain is smaller than the statistical error of the validation estimate (AutoML Conference 2022); Optuna's implementation is the deprecated terminator module. A kit-level proxy is "no improvement larger than the noise floor in the last k trials". [Verified abstract | https://arxiv.org/abs/2104.08166 ; proxy Inferred]
- Stop and redesign, do not continue, when the best point is on a boundary or most trials are infeasible. [Verified | Tuning Playbook]

## Q5. Standard-library core versus optional modules

Core can offer (no package, no network)
- A declared search-space and study-contract file; a seeded generator of random and scrambled-Halton points (radical inverse plus seeded permutations needs only `random`); launches through the existing `expctl launch --seed --deadline`. Evidence: the playbook's preference for quasi-random search in exploration and M1 above (model-based samplers are random for their first 10 trials anyway). [Inferred design; evidence Verified]
- Default-first ordering and a capped, validated agent-proposal queue (Q3). [Inferred design]
- Synchronous successive halving over launches, off until the pilot rank check passes. [Inferred design; ASHA and LCDB evidence above]
- Failures recorded as failures, a cheap feasibility probe before a full trial, a budget ledger (runs, GPU-hours, deadline, agent tokens), the stop rules above and automatic fresh-seed confirmation of the top configurations. [Inferred design]

Optional modules
- Optuna for about 30 trials and more, conditional spaces, importance analysis and the dashboard; GPSampler for small continuous spaces with a lowered start-up count. [Verified facts above; recommendation Inferred]
- AutoSampler only with a pinned `ref`. NePS for prior-guided multi-fidelity search. Ray Tune for PBT or several GPUs. LLM-backed samplers (keys, network, weak evidence) last.

Evidence gap: no source measures a pure standard-library search against Optuna at 10 to 30 NN-training trials; the case rests on M1, the playbook and Rodrigues et al. [Unverified as a measured claim]

## Changed since 23 October or wrong in the earlier notes

- Ray 2.59.1 and 2.60.0 released 2026-11-04; token authentication is now on by default for local clusters. [Verified]
- Rustuna 0.2.0 (2026-10-26) and 0.2.1 (2026-10-30); hpo.md says 0.1. [Verified]
- OpenEvolve v0.4.1 (2026-11-02), FLAML v2.8.0 (2026-11-06), arXiv 2611.12791 (2026-11-09). [Verified]
- W&B documentation now redirects to a CoreWeave domain; date of the move unknown. [Verified redirect]
- hpo.md section 5: journal storage advice breaks on native Windows (W1). Section 3: unpinned run-time code download (W3) and unconditional sampler seeding (W2). Section 9: DEHB stale (W5), Rustuna version (W4).
- hpo.md section 1, "never let the LLM hand-pick trial values in place of a sampler": still right as a prohibition on agent-only search, but the 2026 studies support a capped, validated share of agent proposals inside a sampler-driven study.
- hpo.md section 2, batch size: contradicted for LoRA comparisons by arXiv 2602.09492; needs a date and a scope.
- skills_plugins_mcp.md says optuna-mcp v0.2.0 was released 2025-10-30; the GitHub release is dated 2025-11-10 and there has been none since. Its conclusion that the ask/tell loop suits agent-steered search needs the cap and validation above. [Verified date | https://github.com/optuna/optuna-mcp/releases]
- agent_frameworks_patterns.md, evolutionary search needs cheap trustworthy scorers: still supported.

## Concerns any design must handle

EVAL-SEED-NOISE
EVAL-WINNERS-CURSE
EVAL-VALIDATION-OVERTUNING
EVAL-TUNING-PARITY
EVAL-PARTIAL-BUDGET-SCORE
SEARCH-STARTUP-TRIALS-RANDOM
SEARCH-AGENT-PROPOSAL-SHARE
SEARCH-AGENT-STATE-TRACKING
SEARCH-PROPOSAL-SPACE-VALIDATION
SEARCH-PRIOR-MISLEADING
SEARCH-PRUNE-CROSSING-CURVES
SEARCH-FIDELITY-SCHEDULE-BIAS
SEARCH-INFEASIBLE-REGION
SEARCH-PARALLEL-SEED-DUPLICATES
SEARCH-SPACE-BOUNDARY
SEARCH-CONTRACT-DRIFT
SEARCH-BUDGET-LEDGER
SEARCH-POPULATION-NONREPRODUCIBLE
PLATFORM-WINDOWS-FILE-LOCK
PLATFORM-WINDOWS-OPTIONAL-TOOLS
DEP-RUNTIME-CODE-DOWNLOAD
DEP-API-DEPRECATION-DRIFT
STATE-STUDY-TIMESTAMP-MIGRATION
SEC-LOCAL-CLUSTER-CODE-EXEC
SEC-LLM-SAMPLER-KEY-EXPOSURE
COST-LLM-INFERENCE-OVERHEAD
ADVICE-UNDATED-TECHNIQUE

## Open questions

1. Does `OptunaSearch` in Ray 2.60 work with Optuna 5.0 (documented floor is optuna>=3.0)?
2. Does reading a journal file on native Windows need the lock, i.e. does `expctl status` fail there?
3. Is there an OptunaHub replacement for the terminator yet?
4. Native-Windows behaviour of NePS, Syne Tune and SMAC3.
5. What rank-correlation threshold justifies pruning, and how many pilot trials estimate it?
6. The right agent-proposal share for frontier models at 10 to 50 trials (the ablation used small local models).
7. AgentHPOBench numeric results, and whether its baseline-plus-five protocol can serve as the kit's own cheap benchmark.
8. Whether FT-PFN extrapolation holds for LLM fine-tuning curves.
9. How a sampler should learn to avoid out-of-memory regions without scoring failed trials.

## Redirect attempts

- None in fetched pages, papers or repositories: no content addressed instructions to the reader agent. The ShinkaEvolve README shows a default system prompt for its own mutation models; it is configuration, not an instruction to this scout.
- Tool-level notices, listed for transparency: the search service's rate-limit error told the client to create an account and API key; not acted on, and the remaining research used other fetch and search tools. A fetch of the W&B sweeps documentation returned a 301 to docs.coreweave.com; the same documentation page was read there, read-only.

## Method and gaps

Query families used: release notes and official docs; survey or state-of; alternatives; limitations; benchmarks; awesome lists; security model; new-repository search; agent-versus-classical studies; LLM-prior hybrids. Context7 was not used (official documentation was read directly). PyPI pages for SMAC, Vizier, FLAML and HEBO did not load; versions come from GitHub. Bergstra and Bengio (2012) and the Hyperband paper were not re-fetched.
