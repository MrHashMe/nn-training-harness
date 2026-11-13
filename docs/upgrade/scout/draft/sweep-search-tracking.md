# Sweep scout: search-tracking (hyperparameter optimization, experiment tracking, reproducibility)

Checked 11 November 2026. Input: `docs/upgrade/scout/sweep/search-tracking/` (213 records: github 83, arxiv 45,
hf 40, hn 17, openalex 28; window 14 May to 10 November 2026). Status words: **Verified** = I read the primary
source and it says this (most results are still measured by the authors themselves, and I say so); **Inferred** =
my conclusion from verified facts; **Unverified** = not confirmed from a primary source.

## Summary (10 lines)

1. About 75 of 213 records bear on the goals; 38 candidates were evaluated and 20 read in depth from primary sources.
2. Agent-driven search, long budget: on a 24 h single-GPU small-LM tuning task (about 290 to 630 trials), TPE and CMA-ES beat pure LLM agents in a fixed space; several pure-LLM methods were worse than random; a code-editing agent matched TPE only with a frontier model; a hybrid in which the LLM sees the optimizer's internal state and proposes a minority of trials was best (one task, 3 seeds, authors' measurement, lead of about two standard deviations).
3. Agent-driven search, small budget (5 to 25 evaluations): agents with task semantics beat TPE, GP and random search in three author-run benchmarks; on 30 repository-level training tasks with five changes each, the best agent beat a validated baseline on 76.7% of tasks against 40 to 49% for TPE, random search and a BOHB variant, while the four smallest models stayed near a coin flip (44 to 56%). Caveats: TPE's first 10 trials are random by default, wrong priors erase the gain, the API agents were run once, none of the three reports a hidden test set, and some tasks are classic ones a model may have memorised. Design consequence: the search policy must depend on the budget, and a classical optimizer should hold the search state.
4. Failed trials shape outcomes: out-of-memory rates were 56% for random search against 11% for TPE and 1 to 5% for the best agents, yet a low failure rate alone was not enough (the fixed-space agent failed 1% of trials, converged early and ended below random search). Feasibility handling and failed-trial accounting belong in the loop controller.
5. Procedure drift is measured, and prompts do not fix it: an external state machine enforced by a PreToolUse gate, guarded transitions and a Stop gate raised procedure compliance from 27.8% to 94.8% (pre-registered, one task), at 3.5 to 11 times the cost; the Stop gate alone was worse than no enforcement.
6. Validity gap seen in three sources: many keep-or-revert decisions against one validation set (adaptive reuse) bias the kept score; the mature remedy is a confirmation holdout with limited feedback, which standard-library code can implement.
7. Noise: retraining with a new seed moved a headline metric 3.2 times more than re-sampling, the spread (1 to 2%) did not shrink with compute, and a lucky seed was worth up to 2 times compute. A measured noise floor must gate every "keep".
8. Provenance ideas that need no dependency: claims bound to run ids and evidence hashes ("claim drift" was 3.6 to 16.7% even in a purpose-built harness), a four-part reproduction artifact (76.4% to 92.6% reproduction success), an append-only journal with per-event SHA-256, and a run hash over commit, diff, command and inputs.
9. Tools: Trackio 0.45.0 is the only tracker in the sweep that is local-first, agent-oriented and actively released (optional module candidate; it has hard third-party dependencies). Optuna 5.0.0 changed default sampler behaviour and timestamp semantics, which touches the kit's HPO reference and upgrade path.
10. Nothing "newer than Optuna-style Bayesian optimization" in this sweep has evidence on single-GPU neural-network training strong enough to adopt (tabular-foundation-model surrogates, performance representations, importance-aware scheduling, optimizer foundation models, LLM universal searcher: all Hold).

## Selected items (one line each)

Dates are the sweep record dates (last push for active repositories, creation or submission date otherwise).

### Agent-driven search and its evidence
- Can LLMs Beat Classical HPO Algorithms? (arXiv 2603.24647, discussed 2026-06-09) https://arxiv.org/abs/2603.24647 : head-to-head of TPE, CMA-ES, SMAC, random, LLM agents and a hybrid on small-LM training; the main evidence for how the kit should split work between agent and optimizer.
- Optim-Agent/optim-agent (2026-07-07) https://github.com/Optim-Agent/optim-agent : coding-agent-as-sampler library and skill for Claude Code, Codex and OpenCode; bounded proposals with validation and fallback.
- RobertTLange/autotune (2026-06-26) https://github.com/RobertTLange/autotune : agent proposes the search space, Optuna searches it, user confirms; a cleaner division of labour.
- OpenMOSS/AgentHPOBench (2026-07-27) https://github.com/OpenMOSS/AgentHPOBench : 30 executable repository-level tasks, baseline plus five interventions; candidate task source for measuring whether the kit helps.
- A Closer Look at Agentic BBO (2026-10-08) https://huggingface.co/papers/2610.12183 : cross-domain benchmark, 25 HPO tasks; evidence on tools, priors and agent-to-optimizer handoff.
- LLMs as a Universal Searcher for Open-World AutoML (2026-11-09) http://arxiv.org/abs/2611.12791v1 : trained LLM searcher over architecture, hyperparameters and data ratios; 896 GPU-days at the top end, so evidence only.
- Agentic Auto-Research is Fuzz Testing (2026-08-10) https://huggingface.co/papers/2608.09855 : argues for dense progress signals and a final validation shielded from adaptive reuse.
- WhatWorkedBench (2026-09-23) https://huggingface.co/papers/2609.27490 : shows that finding the best configuration does not mean the agent understood which change caused it.
- Predictive Credit (2026-09-29) https://huggingface.co/papers/2610.00314 : test (one part pre-registered) of whether an agent's explanations improve outcome forecasts; inconclusive.
- InfraRSI (2026-11-08) http://arxiv.org/abs/2611.11558v1 : agentic tuning of training throughput under a fixed task contract with invariants, noise calibration and re-verification.
- Agentic Design of Compositional Descriptors via Autoresearch (2026-05-14) https://huggingface.co/papers/2605.14671 : autoresearch loop outside deep learning; reports its own limits.
- Apodex Discovery (2026-08-11) https://huggingface.co/papers/2608.11341 : benchmarks and harness for long, verifiable AI investigations (listed, not read in depth).
- Modeling Authentic Research Trajectories (2026-10-19) https://huggingface.co/papers/2610.27337 : research-progress graph for ideation; bears on the scouting step (listed only).
- SkillOpt (2026-05-22) https://doi.org/10.48550/arxiv.2605.23904 : optimizes a skill document against a held-out validation set; bears on how the kit's own skill text is maintained and measured.
- kumizeod/AgentForeman (2026-10-19) https://github.com/kumizeod/AgentForeman : overnight experiment orchestration across agent CLIs with durable quota waiting, exit receipts and a hashed archive.
- Keeping LLM Agents on Procedure (2026-11-07) http://arxiv.org/abs/2611.10884v1 : measured procedure drift and an enforced state machine built on Claude Code hooks.
- Show HN: Claude's innerworkings, turn 170 costs 2.1x turn 20 (2026-09-03) https://news.ycombinator.com/item?id=49552931 : single-user measurement of per-turn cost growth with session length.
- Externalizing Research Synthesis and Validation / Xcientist (2026-06-17) https://huggingface.co/papers/2606.18874 : evidence graph, validation contracts and the "claim drift" measure.
- Artifact-centered Claim-aware Observability (2026-08-18) https://huggingface.co/papers/2608.18312 : proposes claim-to-evidence lineage as the audit layer; names OpenTelemetry, PROV-O and RO-Crate.

### Classical and newer search methods
- optuna/optuna (2026-11-09) https://github.com/optuna/optuna : the kit's current HPO backend; v5.0.0 released 2026-09-07 with changed defaults.
- automl/SMAC3 (2026-11-09) https://github.com/automl/SMAC3 : Bayesian optimization package, v2.4.1 (2026-09-10); had a 36% out-of-memory rate in the study above.
- syne-tune/syne-tune (2026-11-06) https://github.com/syne-tune/syne-tune : asynchronous multi-fidelity search, v0.16.0 (2026-08-03).
- google/vizier (2026-10-20) https://github.com/google/vizier : black-box optimization research interface (listed only).
- automl/ConfigSpace (2026-11-05) https://github.com/automl/ConfigSpace : configuration-space description language with conditions (listed only).
- hyperopt/hyperopt (2026-11-09) https://github.com/hyperopt/hyperopt : legacy TPE implementation (listed only).
- polyaxon/hypertune (2026-11-09) https://github.com/polyaxon/hypertune : small HPO library (listed only).
- AgileRL/AgileRL (2026-11-10) https://github.com/AgileRL/AgileRL : population-based hyperparameter evolution inside one run, including LLM post-training.
- LUH-AI/Efficient-Risk-Averse-BO (2026-07-07) https://github.com/LUH-AI/Efficient-Risk-Averse-BO : optimizes a risk-aware objective over seeds rather than a single-seed score.
- Simple Meta-Learning for HPO and CASH (2026-11-05) http://arxiv.org/abs/2611.07659v1 : configurations represented by past performance; about half the trials on a tabular benchmark.
- Out-of-the-Box Tabular Foundation Models for BO (2026-11-09) http://arxiv.org/abs/2611.12491v1 : TabPFN and TabICL as surrogates instead of Gaussian processes.
- An Open-Source Training Dataset for Foundation Models for BBO (2026-05-22) https://huggingface.co/papers/2605.23417 : BBO-Pile, 500K trajectories for learned optimizers.
- Importance-Aware Scheduling for High-Dimensional HPO (2026-06-08) https://huggingface.co/papers/2606.10068 : spend trials on the important hyperparameters first.
- Leveraging AutoML for Sustainable Deep Learning (2026-06-22) https://huggingface.co/papers/2606.23208 : multi-fidelity, multi-objective search with energy as an objective (listed only).
- BiMuon (2026-11-06) http://arxiv.org/abs/2611.10188v1 : bilevel optimization for hyperparameter learning (listed only).
- Heavy tails in Gaussian-process surrogates (2026-11-08) http://arxiv.org/abs/2611.11188v1 : surrogate behaviour under outliers such as diverged runs (listed only).
- Bandits in Prod / Tiime-Software/IMABO (2026-09-03) https://arxiv.org/abs/2609.01335 : bandit tuning at inference time (listed only).
- Moazzam9/fair-hpo-tabular-benchmark (2026-08-21) https://github.com/Moazzam9/fair-hpo-tabular-benchmark : small controlled-budget comparison of HPO methods (listed only).
- BBOmix (2026-06-03) https://huggingface.co/papers/2606.05139 and BOCoDe (2026-08-15) https://huggingface.co/papers/2608.15073 : HPO and BO benchmarks outside the kit's domain (listed only).

### Experiment tracking and provenance
- gradio-app/trackio (2026-11-10) https://github.com/gradio-app/trackio : local-first tracker with a wandb-compatible API, JSON CLI, alerts and an MCP option.
- aimhubio/aim (2026-11-07) https://github.com/aimhubio/aim : open-source tracker; last release v3.29.1 on 2025-05-08, so release cadence has stalled.
- cneuralnetwork/oplogs (2026-08-15) https://github.com/cneuralnetwork/oplogs : checksummed append-only journal plus rebuildable index; a design to copy, not a tool to install.
- NovelAI/kymo (2026-09-25) https://github.com/NovelAI/kymo : tracker needing PostgreSQL and ClickHouse; no Windows support.
- luml-ai/luml (2026-11-10) https://github.com/luml-ai/luml : "agent-native" MLOps platform; platform-scale, out of scope.
- umynameislove/projmem (2026-05-14) https://github.com/umynameislove/projmem : local experiment memory with a failure taxonomy and "avoid" notes.
- MarkD1Zzz/workflow-tracker (2026-06-14) https://github.com/MarkD1Zzz/workflow-tracker : skill that lets the agent write "SUCCESS" conclusions; an anti-pattern for validity.
- SwanHubX/SwanLab-Skill (2026-06-25) https://github.com/SwanHubX/SwanLab-Skill : tracker skill packaged once for several agents through `.agents/skills`.
- DLR-Institute-of-Future-Fuels/rair (2026-06-04) https://github.com/DLR-Institute-of-Future-Fuels/rair : run record with commit, diff patch, command and content-hashed inputs and outputs; tested on Windows.
- Mltrackr / NaiaLorente/datalog (2026-06-30) https://github.com/NaiaLorente/datalog : two-line local tracker (listed only).
- Esha-Mirza/skitrack (2026-08-01) https://github.com/Esha-Mirza/skitrack : small local tracker (listed only).
- No More Results_final_v3.csv (2026-10-06) https://gquetel.fr/misc/mlflow-ml-research/ : practitioner account of MLflow for research (listed only).
- treeverse/vscode-dvc (2026-11-10) https://github.com/treeverse/vscode-dvc : DVC now lives under a new organisation; DVC 3.67.1 (2026-03-31).
- kedro-org/kedro-viz (2026-11-09) https://github.com/kedro-org/kedro-viz : pipeline visualisation with tracking (listed only).
- JuliaAI/MLFlowClient.jl (2026-07-13) https://github.com/JuliaAI/MLFlowClient.jl : shows MLflow's REST protocol as a de facto interchange (listed only).
- truera/trulens (2026-11-10) https://github.com/truera/trulens : evaluation and tracing for LLM applications, not for training (listed only).
- ReproBridge (2026-11-05) https://huggingface.co/papers/2611.08452 : four-part reproduction artifact and an auditor; measured gains for coding agents.

### Reproducibility, evaluation validity and noise
- The FID Lottery (2026-06-18) https://huggingface.co/papers/2606.20536 : seed variance of a headline metric measured over several hundred trainings.
- Adversarial Multiplicity (2026-11-05) http://arxiv.org/abs/2611.07378v1 : harmless-looking hyperparameter choices can steer results and pass a full code-and-data audit.
- What the Loss Curve Misses (2026-11-09) http://arxiv.org/abs/2611.12832v1 : near-equal validation loss hid a 1.3 to 1.5 times slower acquisition of rare facts.
- Dating the Model (2026-09-29) https://huggingface.co/papers/2609.36931 : a date silently placed in the system prompt moved LLM benchmark scores by up to 14%.
- Excess Separability (2026-08-16) https://huggingface.co/papers/2608.12652 : probe-based contamination detection is unreliable (listed only).
- Reassessing Dataset Quality and Fine-Tuning Practices on PrimeVul (2026-11-04) http://arxiv.org/abs/2611.06373v1 : fine-tuning results that depend on dataset quality (listed only).
- Generalization or Memorization? (2026-05-17) https://huggingface.co/papers/2605.17565 : brittleness tests for a small trained language model (listed only).
- Diminishing Returns of Data in Sparse Autoencoders (2026-10-14) https://huggingface.co/papers/2610.20680 : matching function does not imply reproducible internals across seeds (listed only).
- bytemonkk/I-Failed-With-BioMistral (2026-06-11) https://github.com/bytemonkk/I-Failed-With-BioMistral : a published negative fine-tuning result (listed only).
- JayYu686/TinyLLM-System (2026-07-13) https://github.com/JayYu686/TinyLLM-System : exact-resume state list and pre-registered promotion gates.
- mojolearn/mojolearn (2026-08-20) https://github.com/mojolearn/mojolearn : bitwise-identical training across GPU vendors (listed only).
- Modalities/modalities (2026-10-12) https://github.com/Modalities/modalities : reproducible foundation-model training framework (listed only).
- stepfun-ai/SteptronOss (2026-09-04) https://github.com/stepfun-ai/SteptronOss : LLM training framework that ships an AGENTS.md and validated config-as-code.
- Dbp-dev12/vla-preflight (2026-09-26) https://github.com/Dbp-dev12/vla-preflight : data diagnostics before training (listed only).
- Fully Open Meditron (2026-05-15) https://huggingface.co/papers/2605.16215 and NebulaExp-8B (2026-06-25) https://huggingface.co/papers/2606.26671 : auditable and ablation-driven LLM post-training pipelines (listed only).
- Practical Lessons from RL Post-Training Experiments (2026-07-09) https://zenodo.org/records/21115798 : failure-indexed field guide for RL post-training on 1 to 8 GPUs; only the record page was read.

### Cheap benchmark tasks and remote resources
- pochenai/nano-llm-posttraining (2026-08-01) https://github.com/pochenai/nano-llm-posttraining : 135M-parameter SFT, DPO and GRPO runs on an 8 GB GPU, about 20 minutes each.
- yangqi0/petitgpt (2026-10-11) https://github.com/yangqi0/petitgpt : 124.6M LLM trained from scratch on one RTX 4090 (listed only).
- DLR-RM/rl-baselines3-zoo (2026-10-27) https://github.com/DLR-RM/rl-baselines3-zoo : tuned-hyperparameter zoo with Optuna integration (listed only).
- AI-Hypercomputer/gpu-recipes (2026-10-26) https://github.com/AI-Hypercomputer/gpu-recipes : reproducible cloud training recipes (listed only; remote-GPU facet).
- Launch HN: Expanse (2026-06-01) https://news.ycombinator.com/item?id=48356312 : marketplace for idle GPU capacity (listed only; remote-GPU facet).
- Show HN: Ridge (2026-09-10) https://github.com/vasinov/ridge-core : connects coding agents to SSH, Docker and S3 resources; the repository returned 404 on 2026-11-11.

## Deep reads

Format: claim | source | version or date | status. All checked 2026-11-11.

### D1. Classical optimizers against LLM agents, and the Centaur hybrid
- Task: about 50M-parameter language model, 5-minute trials, 24 h of GPU training per method, 3 seeds, 14 hyperparameters, one H200 with memory capped at 80 GB | https://arxiv.org/html/2603.24647v5 | v5, 17 Apr 2026 | Verified.
- Mean best validation bits-per-byte (lower is better): Centaur with a frontier model 0.9739 +/- 0.0012; TPE 0.9768 +/- 0.0019; code-editing agent with the same frontier model 0.9770 +/- 0.0027; SMAC 0.9778; CMA-ES 0.9785; random 0.9873; fixed-space LLM agent 0.9904 | same | v5 | Verified (authors' measurement).
- Out-of-memory rates: random 56%, SMAC 36%, TPE 11%, CMA-ES 16%, LLAMBO 48 to 64%, fixed-space agent 1% (16% with a 0.8B model), code-editing agent 3 to 19% (3 and 5% with the two frontier models), hybrid 13 to 20%; one small model failed 87 to 94% of code edits | same, Tables 3 and 5 | v5 | Verified.
- A low failure rate was not sufficient: the fixed-space agent failed 1% of trials, had the lowest diversity, converged to a narrow region early and ended below random search. Methods with many failures completed more trials (289 to 668 per seed) because failures are fast | same | v5 | Verified.
- Centaur shares the CMA-ES mean, step size and covariance plus the top 5 and last 20 trials; the LLM proposes 30% of trials by default; in the ratio ablation (0.1, 0.2, 0.3, 0.5 and 0.8, 2 seeds per ratio) results were close from 0.1 to 0.5 and clearly worse at 0.8, and the 0.8B model did best at 0.1, so the supported conclusion is only that the optimizer keeps majority control; a 0.8B model inside the hybrid scored 0.9766 +/- 0.0008, level with TPE within noise | same, and https://github.com/ferreirafabio/autoresearch-automl (MIT) | v5 | Verified.
- Limits: one task; no tools or retrieval for the LLM methods; the study optimizes and reports validation loss only, with no held-out test | same | v5 | Verified.
- The gap between the best hybrid and TPE (0.0029) is about two standard deviations with 3 seeds; treat the ranking of the top five as suggestive | my reading | - | Inferred.
- What the kit can take: (a) rule for the HPO reference: for a fixed space and more than a few dozen trials, a classical optimizer runs the search and the agent contributes the space, feasibility limits and occasional proposals; (b) the agent must not be the only holder of search state; (c) count failed trials against budget. Cost: documentation plus an ask/tell wrapper around the existing Optuna helper.

### D2. optim-agent 0.1.1
- Library and skill in which a coding-agent CLI proposes values; the library validates them against the declared space and falls back to safe sampling when the reply is invalid; JSON or SQLite study storage; ask/tell interface; mock backend for offline tests | https://github.com/Optim-Agent/optim-agent (README at commit 39e5f94) | PyPI 0.1.1, 13 Jul 2026; MIT; "zero runtime deps" badge | Verified.
- Reported results (10 trials, 5 seeds): agent with context beats TPE on MNIST and CIFAR-10; without context it is 24.3% worse than TPE on MNIST and about equal to random on CIFAR-10 | same | - | Verified (self-reported).
- The classification metric is built from test error, and the tabular benchmark's README states that the retained configuration was selected using validation and test loss | same | - | Verified.
- Optuna's TPE uses random sampling for its first 10 trials by default, so a 10-trial comparison against TPE is a comparison against random search | https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html | docs for v5.x | Verified for the default; Inferred for the consequence (whether the benchmark changed that setting was not checked).
- Troubleshooting note: nested agent sessions inherit the API key environment variable | README | - | Verified.
- Take: the bounded-proposal contract (declared space, validation, fallback, measured objective stays authoritative). Do not take: its benchmarks as evidence, or the pattern of launching a nested agent per trial.

### D3. autotune (agent-assisted HPO)
- The agent reads the training script and proposes parameters, direction, sampler and pruner; the user confirms; Optuna runs the trials; the original script is untouched; optional refinement rounds revise the space | https://github.com/RobertTLange/autotune | 224 commits, pushed 2026-08-02 (sweep metadata); MIT | Verified.
- A cap on active search parameters is enforced (one correction request, then failure); user guidance cannot override schema, metric comparability or objective measurement | same | - | Verified.
- No numeric evidence on the page; requires Node.js 22 and network on first run; only Codex is named as agent | same | - | Verified.
- Take: "agent designs the space, optimizer searches it" plus a hard parameter cap and non-overridable measurement constraints. Cost: none as an idea; the tool itself adds Node.js.

### D4. AgentHPOBench
- 30 repository-level tasks in seven categories, each a pinned upstream repository with a validated baseline run, a constrained intervention space and five sequential interventions; baselines are random search, TPE and a BOHB-style adapter; seeds 0, 1 and 42; includes a no-feedback ablation | https://github.com/OpenMOSS/AgentHPOBench and https://arxiv.org/abs/2607.29626 | v1, 31 Jul 2026; Apache-2.0; one commit | Verified.
- Authors' qualitative finding: agents optimize measurably but struggle with sustained refinement, log diagnosis and reaching reference performance | abstract | v1 | Verified.
- Results after the fifth intervention, limited budget (about 10% of the original training budget), 30 tasks; mean bounded normalized score and share of tasks where the validated baseline was beaten: random search -0.034 and 48.9%; TPE -0.113 and 40.0%; BOHB variant 0.018 and 45.6%; six open-weight agents -0.001 to 0.148 and 44.4 to 63.3%; six API agents 0.080 to 0.407 and 56.7 to 76.7% (best two: 0.407 with 76.7%, and 0.305 with 66.7%) | https://ar5iv.labs.arxiv.org/html/2607.29626 (rendering of v1) | v1 | Verified (authors' measurement).
- No-feedback ablation on one open model: score 0.148 with feedback and 0.052 without; win rate 60.0% and 50.0% | same | v1 | Verified.
- Without feedback that agent still scored above the three classical baselines, so prior knowledge alone beats classical search at five trials; feedback then roughly triples its score (one model, so the split is indicative only) | my reading | - | Inferred.
- On the four LLM-training tasks (best-so-far score): best agent 0.206, second 0.119, random search -0.097, TPE -0.090, BOHB variant -0.061 | same, Table 12 | v1 | Verified.
- Caveats stated by the authors: API agents were run once (not a seed replicate; open models and baselines used 3 seeds); the score is taken after the fifth intervention, not the best one, and several agents lost earlier gains; there is no separate hidden test set, so generalization after adaptive selection is not estimated; results compare whole pipelines (prompts, parsing, retries), not models | same | v1 | Verified.
- The best agent still failed to beat the baseline on 7 of 30 tasks, and classical methods and small models beat it about half the time, which is what noise around a tuned baseline would produce | my reading | - | Inferred.
- How the TPE, random and BOHB baselines were configured (startup trials, source of the search space), cost per task, and failure or fallback rates | - | - | Unverified (not found in the parts read).
- Take: the protocol (validated baseline, fixed number of interventions, no-feedback control) as the kit's own cheap evaluation design; candidate tasks such as the CIFAR-10 speed-run; the lost-gain trajectories support keep-or-revert decided by harness code, and the near-coin-flip win rates support a noise gate. Cost: datasets and upstream repositories must be fetched; the full suite is compute-heavy.

### D5. AgenticBBO-Bench
- 77 tasks in five domains; HPO part is 25 Bayesmark tasks with 5 shared initial and 25 new evaluations; agents run in a persistent Codex session inside an isolated Docker workspace (codex-cli 0.153.4) | https://github.com/lamda-bbo/agentic-bbo (MIT) and https://arxiv.org/abs/2610.12183 | v1, 8 Oct 2026 | Verified.
- HPO mean scores: agentic 0.554, direct LLM 0.519, GP-BO 0.432, TuRBO 0.387, CMA-ES 0.361, TPE 0.344, random 0.273 | https://arxiv.org/html/2610.12183v1 | v1 | Verified (authors' measurement; variance not seen in the part read).
- Giving the agent Gaussian-process tools did not help (0.589 base, 0.574 and 0.538 with tools); task semantics helped (0.465 to 0.595); a wrong prior removed the benefit (0.872 with a correct one, 0.682 with a wrong one, 0.685 without) | same | v1 | Verified.
- Handoff: a trust-region optimizer continuing from the agent's trajectory scored 0.570 against 0.475 from the initial points alone and 0.569 for the agent alone | same | v1 | Verified.
- The protocol forbids the agent from reaching the evaluator and rejects invalid candidates without spending budget | same | v1 | Verified.
- Bayesmark tasks are classic models on classic datasets, so strong priors may be memorised | my reading | - | Inferred.
- Take: agent first, numerical optimizer continues from its trajectory; record priors as hypotheses that can be wrong; isolate the evaluator.

### D6. Executable finite-state control for long unattended procedures
- A daemon outside the model's context keeps workflow state on disk; a PreToolUse hook checks each tool call against the current state's permissions; transitions pass hard shell checks (optionally a second-model review) and commit atomically; a Stop hook blocks ending the turn unless the state is a declared pause point; built on Claude Code run headless plus an MCP server | https://arxiv.org/html/2611.10884v1 | v1, 7 Nov 2026 | Verified.
- Pre-registered experiment, 200-item procedure batches: correct-and-faithful items out of 200 for a small model were 9.4 plain, 17.1 with a system prompt, 48.4 with reminders and resume, 139.2 with the state machine (8 seeds; +90.9, 95% CI 46.2 to 130.2); compliance 11.9%, 27.8% and 94.8% | same | v1 | Verified (authors' measurement).
- Ablation (3 seeds): reminders with resume 76.3, Stop gate only 5.7, tool gates only 104.0, full machine 128.0 | same | v1 | Verified.
- Cost per session: 0.96, 3.01 and 10.64 US dollars (plain, reminders with resume, state machine); a small model with the machine beat a larger plain model at 38% of the cost | same | v1 | Verified.
- A larger model drifted less; its gain was positive in only 1 of 3 seeds. On open-ended coding the machine helped on a harder subset (69 against 62 of 100, subset not pre-registered), changed nothing on an easy subset (+23% time), and on one customer-service domain it lost because checks were too strict | same | v1 | Verified.
- Residual hole: static permissions could not bind an action to the current item (3 of 8 sessions acted on another item). No code release is stated | same | v1 | Verified.
- Take: implement the unattended loop as a state machine in harness code, with state on disk, the existing guard hook consulting it, transition guards as hard checks (run terminal, evaluator hash unchanged, budget left, active experiment id matches) and a Stop gate. Never ship a Stop gate without the tool gate. Cost: 3.5 to 11 times agent spend on procedure-heavy work in the paper; platform ports need an equivalent of both hooks.

### D7. Auto-research as fuzz testing (position paper)
- Argues that optimizing only a final score makes agents overfit to test conditions and sample blindly; asks for a cheap, dense progress measure that directs the next experiment, and a final validation that uses evidence shielded from adaptive reuse | https://arxiv.org/abs/2608.09855 | v2, 24 Aug 2026 | Verified.
- Evidence is one simulated-physics environment; no quantitative results in the abstract | same | v2 | Verified. Weak evidence; useful as framing.

### D8. Reusable holdout (found by re-searching "adaptive reuse")
- Adaptive selection can bias a holdout estimate by about sqrt(k/n) for k adaptive steps on n holdout examples; a thresholded, noise-added access mechanism keeps the holdout valid for many adaptive queries | https://arxiv.org/abs/1506.02629 | 2015, mature; outside the freshness window but a mathematical result | Verified (via search extract of the paper).
- Applied to the loop: with 50 keep-or-revert decisions on a 2,000-example validation set the worst-case bias is about 0.16 in accuracy units; real bias is usually smaller, but the kept score is still optimistic | my arithmetic | - | Inferred.
- Take: split validation into a search split and a confirmation split that only harness code reads; report the confirmation score for kept changes; cap the number of confirmation reads; round or threshold what the agent sees. Standard library only.

### D9. ReproBridge
- Four-part artifact (refined codebase, environment setup, experiment launchers, reproduction guide); agents reproduce in a fresh session and a separate auditor checks execution evidence | https://arxiv.org/abs/2611.08452 | v1, 5 Nov 2026 | Verified.
- 1,029 tasks from 387 experiments in 36 papers; reproduction success rose from 76.4% to 92.6% across four models; downstream API spend fell 19.7%; the spread between models shrank from 21.6 to 3.9 points; removing code or environment hurt most | same | v1 | Verified (authors' measurement; no code link).
- Take: at the end of a loop, harness code emits the launcher command, environment record and a short reproduction guide per kept result, and the read-only reviewer re-runs from those alone. Cost: template and a few fields in the run record.

### D10. Claim drift and claim-aware lineage
- "Claim drift" is an unresolved gap between an accepted claim and the sources, code or experiments it cites; a purpose-built harness still showed 3.6 to 16.7% drift, lower than three comparison systems in all nine comparisons, mostly through fewer unverifiable records | https://arxiv.org/abs/2606.18874 | v4, 27 Sep 2026 | Verified (authors' retrospective audit).
- Proposal: emit claims as first-class records with explicit evidence bindings and verification records; keep execution traces in OpenTelemetry and export to PROV-O or RO-Crate | https://arxiv.org/abs/2608.18312 | v1, 18 Aug 2026 | Verified (position paper, no experiment).
- RO-Crate 1.3 was released 23 June 2026; run-level profiles were at versions 0.3 to 0.4 and due for update | https://www.researchobject.org/ro-crate/blog/2026-06-23/announcing-ro-crate-1-3 | 1.3 | Verified.
- Take: each journal claim carries run ids and the hash of the metrics file it rests on; a claim without a binding is flagged by `expctl`; the reviewer subagent checks bindings. An RO-Crate export is optional and has no evidence of improving results.

### D11. WhatWorkedBench and Predictive Credit
- With eight purchased measurements a simple model found the exact optimum on 15 of 22 sources, yet in 13 of those 15 at least one estimated component effect was off by more than 10% of the range | https://arxiv.org/abs/2609.27490 | v2, 28 Sep 2026 | Verified.
- Test (one part pre-registered) of whether agent explanations improve forecasts of experiment outcomes: inconclusive; full explanation cards widened 80% intervals by 21% with no better coverage (49.3% against 51.4%) | https://arxiv.org/abs/2610.00314 | v1, 29 Sep 2026 | Verified.
- Take: the journal may record "kept configuration" from a measurement, but a causal sentence ("X helped because Y") needs its own ablation run; agent explanations are not evidence.

### D12. The FID Lottery (seed noise)
- Several hundred trainings of one recipe: retraining with a new seed changes the metric 3.2 times more than re-sampling from a fixed network; sources are initialisation, data order and per-step noise; the coefficient of variation stays at 1 to 2% with more compute or a larger model; a lucky seed reaches the same score with up to 2 times less compute; differences under about 1.3% should be called inconclusive and error bars reported over training seeds | https://arxiv.org/abs/2606.20536 | v1, 18 Jun 2026 | Verified (authors' measurement, one model family).
- Take: before the loop starts, harness code runs the baseline with k seeds and stores the spread; the keep rule requires a gain larger than that spread (or repeated seeds); evaluation-time seeds alone understate noise.

### D13. InfraRSI
- Five stages: lock the editable scope and fix a task contract (workload, loss and timing invariants) against reward hacking; profile the baseline and calibrate noise; search launch settings and code patches and re-verify the top candidates against the baseline in fresh runs; report with source audit and the cost of failed trials; apply | https://arxiv.org/abs/2611.11558 | v1, 8 Nov 2026 | Verified.
- Fits models of time and of peak memory that include out-of-memory trials as censored data; reports up to 2.75 times speed-up and utilisation from 17.4% to 30.0% on four multi-GPU workloads | same | v1 | Verified (authors' measurement).
- Repository is a Python CLI with agent back ends; no license stated on the page; one commit | https://github.com/TokenRhythm/InfraRSI | - | Verified.
- Take: when the loop optimizes speed or memory, the contract must pin loss and step count; re-verify winners in a fresh run; keep an out-of-memory boundary record per machine. Code cannot be reused without a license.

### D14. Experiment trackers
- Trackio: local SQLite store, wandb-compatible calls, CLI with `--json` and read-only SQL, alerts with severity and `since` polling, optional MCP server, optional sync to hosted Spaces | https://github.com/gradio-app/trackio and https://huggingface.co/docs/trackio/main/en/ml_agents | 0.45.0, 2 Nov 2026; MIT; beta with possible schema changes | Verified.
- Trackio hard dependencies: huggingface-hub, an HTTP client, starlette, uvicorn, numpy, pillow, orjson, brotli; default store under the user's cache directory, outside the repository | https://raw.githubusercontent.com/gradio-app/trackio/main/pyproject.toml | main, 2026-11-11 | Verified.
- Its agent guide has the agent write its own alert thresholds and save the best checkpoint on validation loss; nothing in it protects held-out data or handles noise | docs page above | - | Verified.
- oplogs: canonical record is append-only JSONL with a SHA-256 per event; SQLite is a rebuildable index; content-addressed file store; loopback-only daemon with a 0600 capability token | https://github.com/cneuralnetwork/oplogs | 16 commits, not on PyPI; MIT | Verified.
- kymo: needs PostgreSQL and ClickHouse (about 700 MB), no Windows, every viewer is admin, described by its author as machine-written and unreviewed | https://github.com/NovelAI/kymo | Apache-2.0 | Verified.
- Aim: last release v3.29.1, 8 May 2025 | GitHub releases | - | Verified.
- Take: Trackio as an optional module behind a `runlog` adapter with sync off; the oplogs record design for the kit's own run files (all standard library). The kit's `status`, `watch` and `curve` already cover what the agent needs, so a tracker mainly serves the human.

### D15. Run identity and experiment memory
- rair: per run it stores the commit hash, the uncommitted diff as a patch, the command line, captured output, content hashes of inputs and outputs, and restore steps; a run hash covers commit, diff, command and input content; tested on Windows and Unix | https://github.com/DLR-Institute-of-Future-Fuels/rair | 72 commits, MIT, no release | Verified.
- projmem: local SQLite memory of runs and failures with a failure taxonomy; "avoid" notes for a setting shared by confirmed failures are withheld when successful runs contradict them; redacts secret-like keys; MCP and loopback REST adapters; one self-run 30-run example | https://github.com/umynameislove/projmem | 0.4.0a1 (alpha), MIT | Verified (self-reported evidence).
- DVC stores experiments as custom git references without branch commits; untracked files are skipped unless asked; restoring replaces the workspace | https://doc.dvc.org/user-guide/experiment-management | DVC 3.67.1, 31 Mar 2026 | Verified.
- Take: add input content hashes and a single run hash to the kit's existing snapshot; add a structured failure index to the journal so the loop does not retry known failures.

### D16. AgentForeman
- Orchestrator for several agent CLIs: SQLite state, worker leases, process identity and exit receipts; quota waits are persisted only for recognised reset signals; uncertain process state is never accepted as success; finished runs keep source snapshot, patches, logs, a SHA-256 manifest and a replay script, checked by a verify command | https://github.com/kumizeod/AgentForeman | 53 commits, pushed 2026-11-04, MIT, no release | Verified.
- States its own limits: not a sandbox; no hard token budgets; local cancel does not prove upstream billing stopped; the test matrix was not fully green on Windows at the cited commit; model replies in tests are scripted | same | - | Verified.
- Uses multi-model councils and peer review, which the kit's own evidence base argues against | same and brief | - | Inferred.
- Take: durable quota waiting, exit receipts, hashed archive with replay script, and "completed is not the same as improved". Leave the multi-agent machinery.

### D17. Exact resume and promotion gates
- Checkpoint contents listed as model, optimizer, scheduler, scaler, step, RNG state, sampler cursor, data version, config hash, commit, environment, world size and per-file SHA-256; atomic write and atomic "latest" pointer; resume modes named exact, warm and transfer | https://github.com/JayYu686/TinyLLM-System | 83 commits, pushed 2026-09-02, Apache-2.0 | Verified (self-reported; linked reports not read).
- Promotion gates fixed in advance: improvement of at least 3 points with the bootstrap 95% lower bound above zero, regression on general tasks within 2 points, format validity thresholds, complete lineage | same | - | Verified (self-reported).
- Take: the checklist for the kit's resume reference, and pre-declared keep rules with a confidence bound rather than a point comparison.

### D18. Other validity findings
- Hyperparameter and feature choices ("soft manipulation") can steer a model's individual and aggregate conclusions and still pass an audit with full code and data access; recommended remedies are pre-registration, sensitivity analysis, several metrics and proof of training | https://arxiv.org/abs/2611.07378 | v1, 5 Nov 2026 | Verified.
- A hidden date in the system prompt moved scores by up to 6% (multiple choice), 14% (maths), 7% (code) across 9 models, more than batch size or precision; chain-of-thought amplified it | https://arxiv.org/abs/2609.36931 | v1, 29 Sep 2026, accepted at a main conference | Verified.
- 4-bit pretraining matched validation loss within 0.5 to 2% yet needed 1.32 to 1.52 times as many exposures to recall rare facts | https://arxiv.org/abs/2611.12832 | v1, 9 Nov 2026 | Verified (synthetic data).
- Take: the keep rule and all guard metrics are declared before the loop starts; LLM evaluation pins the full prompt including any date; a change to numeric precision needs a capability check beside the loss.

### D19. Optuna 5.0.0 (the kit's current backend)
- Released 7 Sep 2026: multivariate TPE and constant-liar are on by default; TPE is the default multi-objective sampler; GPSampler is stable with batch acquisition; constraints are set inside the objective; importance uses PED-ANOVA by default; storages record timestamps in UTC and the upgrade command does not convert old ones; several legacy modules removed | https://github.com/optuna/optuna/releases/tag/v5.0.0 | v5.0.0 | Verified.
- A study resumed across the 4.x to 5.0 boundary changes sampler behaviour mid-study | my reading | - | Inferred.
- Take: record the Optuna version in each study's run record; back up storage before upgrade; set `n_startup_trials` on purpose for small budgets.

### D20. Skill optimization and skill packaging
- SkillOpt edits one skill document with bounded add, delete or replace steps and keeps an edit only if a held-out validation score strictly rises; best or tied in all 52 model, benchmark and harness cells; gains of about 19 to 25 points over no skill; skills transfer between two agent harnesses | https://arxiv.org/abs/2605.23904 | v2, 25 May 2026 | Verified (authors' measurement; optimization cost not given).
- A tracker vendor ships one skill directory installed into `.agents/skills` with links for several agents; its install text asks the user to tell the agent to fetch a remote guide and follow it | https://github.com/SwanHubX/SwanLab-Skill | 11 commits, MIT | Verified.
- Take: measure changes to the kit's own skill text on held-out tasks before shipping them; one skill source with per-agent links is a portability pattern to check with the platform scouts; never install by remote instruction.

### Second-phrasing searches
- "LLM agents versus TPE or CMA-ES, limitations, small budget": returned only D1 and summaries of it; no independent study of the tens-of-trials regime was found. The small-budget advantage rests on D2, D4 and D5, each measured by its own authors | search 2026-11-11 | Unverified beyond those.
- "Enforcing agent workflow with a state machine and hooks, alternatives": found Statewright, a state-machine product with hook-based enforcement for several agents; its benchmark harness is unpublished, its licenses are mixed (Apache-2.0 and a source-available license) and a provisional patent covers the method | https://news.ycombinator.com/item?id=48108778 | 2026 | Verified (discussion thread; claims self-reported). Practitioner posts repeat "rules in hooks, judgment in prompts" without methodology | Unverified.
- "Validation overfitting, adaptive reuse, many experiments": no agent-specific study; the reusable-holdout result in D8 is the usable prior art.
- "Recording uncommitted changes per experiment, alternatives": DVC experiments as git references (D15).

## New concepts (not in README.md or brief.md)

1. Centaur hybrid: a classical optimizer shares its internal state with an LLM that proposes a minority of trials. https://arxiv.org/abs/2603.24647
2. CMA-ES: evolution strategy that adapts a mean, step size and covariance over the search space. https://arxiv.org/abs/2603.24647
3. LLAMBO: an LLM acting as the surrogate and sampler of Bayesian optimization; worse than random in D1. https://arxiv.org/abs/2603.24647
4. Out-of-memory rate as a search metric: share of trials lost to memory failure, which dominated method ranking. https://arxiv.org/html/2603.24647v5
5. Agent sampler with bounded proposals: agent values are validated against a declared space with a safe fallback. https://github.com/Optim-Agent/optim-agent
6. Agent pruner: an agent decides to stop a trial from its learning curve; agent errors never prune. https://github.com/Optim-Agent/optim-agent
7. Agent-designed search space with a parameter cap: the agent picks what to tune, a classical optimizer tunes it. https://github.com/RobertTLange/autotune
8. Sequential-intervention benchmark: validated baseline plus a fixed number of result-informed changes. https://github.com/OpenMOSS/AgentHPOBench
9. No-feedback ablation: withhold results from the agent to separate prior knowledge from evidence use. https://github.com/OpenMOSS/AgentHPOBench
10. Agent-to-optimizer handoff: a numerical optimizer continues from the agent's trajectory. https://arxiv.org/abs/2610.12183
11. TuRBO: trust-region Bayesian optimization, strong in the handoff study. https://arxiv.org/abs/2610.12183
12. Prior misdirection: a wrong prior given to the agent removes the benefit of having one. https://arxiv.org/html/2610.12183v1
13. Procedure drift: agents abandon a stated procedure over long runs, and reminders move the drift elsewhere. https://arxiv.org/abs/2611.10884
14. Executable finite-state control: workflow state held outside the model and enforced at tool calls and transitions. https://arxiv.org/abs/2611.10884
15. Stop gate: a hook that refuses to end the agent's turn outside declared pause points. https://arxiv.org/html/2611.10884v1
16. Transition guard: a hard shell check that must pass before workflow state advances. https://arxiv.org/html/2611.10884v1
17. Pre-registration of an experiment: design, metric, predictions and analysis code frozen before the runs. https://arxiv.org/html/2611.10884v1
18. Greybox-fuzzing view of auto-research: dense progress signal steers search; the verdict comes from protected evidence. https://arxiv.org/abs/2608.09855
19. Adaptive reuse and the reusable holdout: repeated decisions on one holdout bias it; thresholded access limits the bias. https://arxiv.org/abs/1506.02629
20. Reproduction artifact design: refined code, environment setup, launchers and a reproduction guide. https://arxiv.org/abs/2611.08452
21. Execution-evidence auditor: a separate role that checks what was actually run, not what was reported. https://arxiv.org/abs/2611.08452
22. Claim drift: a claim no longer matches the code, sources or experiments it cites. https://arxiv.org/abs/2606.18874
23. Validation contract: a per-stage statement of required implementation, comparisons and artifacts. https://arxiv.org/abs/2606.18874
24. Claim-aware artifact lineage: claims as records with evidence bindings and verification records. https://arxiv.org/abs/2608.18312
25. RO-Crate and its run profiles: JSON-LD packaging of research objects and of process or workflow runs. https://www.researchobject.org/ro-crate/blog/2026-06-23/announcing-ro-crate-1-3
26. PROV-O: the W3C provenance ontology named as an export target. https://arxiv.org/abs/2608.18312
27. OpenTelemetry for experiment and agent traces: spans as the execution layer under provenance. https://arxiv.org/abs/2608.18312
28. Effect recovery against optimum finding: an agent can find the best configuration and still misattribute why. https://arxiv.org/abs/2609.27490
29. Predictive credit: what an explanation adds to a forecast of an experiment's outcome. https://arxiv.org/abs/2610.00314
30. Training-seed against sampling-seed variance, with a coefficient-of-variation threshold for "inconclusive". https://arxiv.org/abs/2606.20536
31. Predictive multiplicity and soft manipulation: equally accurate models that differ, steerable by innocent-looking choices. https://arxiv.org/abs/2611.07378
32. Proof of model training: evidence that a released model came from the declared procedure. https://arxiv.org/abs/2611.07378
33. Hidden date injection: a date silently added to the system prompt changes benchmark scores. https://arxiv.org/abs/2609.36931
34. Rare-fact acquisition as a guard metric beside validation loss. https://arxiv.org/abs/2611.12832
35. Task contract with invariants: workload, loss and timing fixed so that a speed-up cannot come from doing less. https://arxiv.org/abs/2611.11558
36. Noise calibration stage: profile the baseline and measure machine jitter before comparing candidates. https://arxiv.org/abs/2611.11558
37. Censored memory model: out-of-memory trials used as data to learn the feasible region. https://arxiv.org/abs/2611.11558
38. Experience bank: verified findings stored for reuse across hardware and runs. https://github.com/TokenRhythm/InfraRSI
39. Model FLOPs utilisation: achieved share of theoretical throughput, a training-efficiency metric. https://arxiv.org/abs/2611.11558
40. Trackio: local-first tracker with a wandb-compatible API, JSON CLI, alerts and optional MCP server. https://github.com/gradio-app/trackio
41. Structured alerts with `since` polling: severity-levelled run events an agent reads instead of raw curves. https://huggingface.co/docs/trackio/main/en/ml_agents
42. Checksummed append-only journal with a rebuildable index and content-addressed store. https://github.com/cneuralnetwork/oplogs
43. Run hash: one identifier over commit, uncommitted diff, command line and input content. https://github.com/DLR-Institute-of-Future-Fuels/rair
44. Experiment memory with a failure taxonomy and evidence-scoped "avoid" notes. https://github.com/umynameislove/projmem
45. Experiments as custom git references, outside branch history. https://doc.dvc.org/user-guide/experiment-management
46. Durable quota waiting: persisted waits only on recognised quota signals, never on arbitrary failures. https://github.com/kumizeod/AgentForeman
47. Exit receipts and a hashed archive with a replay script and a verify command. https://github.com/kumizeod/AgentForeman
48. Exact, warm and transfer resume as separately validated modes, with a sampler cursor in the checkpoint. https://github.com/JayYu686/TinyLLM-System
49. Pre-registered promotion gates with a bootstrap lower bound. https://github.com/JayYu686/TinyLLM-System
50. SkillOpt: text-space optimization of a skill document gated by a held-out validation score. https://arxiv.org/abs/2605.23904
51. Tabular foundation models (TabPFN, TabICL) as optimization surrogates. https://arxiv.org/abs/2611.12491
52. Performance representations: describe a configuration by its past scores on other tasks. https://arxiv.org/abs/2611.07659
53. Greedy Importance First: schedule trials by estimated hyperparameter importance. https://arxiv.org/abs/2606.10068
54. BBO-Pile and optimizer foundation models: models trained to imitate optimizers from 500K trajectories. https://arxiv.org/abs/2605.23417
55. PED-ANOVA: Optuna 5's default hyperparameter-importance evaluator. https://github.com/optuna/optuna/releases/tag/v5.0.0
56. GPSampler with batch acquisition: Gaussian-process sampler, now stable, that proposes several parallel trials. https://github.com/optuna/optuna/releases/tag/v5.0.0
57. Risk-averse heteroscedastic Bayesian optimization: optimize a risk-aware objective over seeds. https://github.com/LUH-AI/Efficient-Risk-Averse-BO
58. In-run evolutionary hyperparameter optimization for LLM post-training. https://github.com/AgileRL/AgileRL
59. Session aging: per-turn agent cost grows with session length (2.1 times after turn 141 in one user's data). https://news.ycombinator.com/item?id=49552931
60. Shared skill directory (`.agents/skills`) linked into several agent products. https://github.com/SwanHubX/SwanLab-Skill
61. Baseline win rate and anchor attainment: share of tasks where a validated baseline is beaten, and progress toward the published reference score. https://ar5iv.labs.arxiv.org/html/2607.29626

## Concerns any design must handle

- EVAL-ADAPTIVE-OVERFIT
- EVAL-SEED-NOISE
- EVAL-NOISE-FLOOR-UNMEASURED
- EVAL-TEST-SELECTION
- EVAL-EVALUATOR-REACHABLE
- EVAL-PROXY-METRIC-GAP
- EVAL-HIDDEN-CONTEXT-NONDETERMINISM
- EVAL-WEAK-BASELINE
- EVAL-POST-HOC-KEEP-RULE
- EVAL-SOFT-MANIPULATION
- EVAL-BENCHMARK-MEMORISATION
- EVAL-CAUSAL-MISATTRIBUTION
- EVAL-AGENT-AUTHORED-THRESHOLDS
- SEARCH-BUDGET-REGIME-MISMATCH
- SEARCH-STATE-LOSS
- SEARCH-OOM-WASTE
- SEARCH-INVALID-PROPOSAL
- SEARCH-PRIOR-MISDIRECTION
- SEARCH-SPACE-TOO-WIDE
- SEARCH-OPTIMIZER-VERSION-DRIFT
- SEARCH-PREMATURE-CONVERGENCE
- SEARCH-REGRESSION-AFTER-GAIN
- AGENT-PROCEDURE-DRIFT
- AGENT-PREMATURE-STOP
- AGENT-STOP-GATE-WITHOUT-TOOL-GATE
- AGENT-ENFORCEMENT-OVERHEAD
- AGENT-OVERSTRICT-GUARD
- AGENT-ACTION-TARGET-BINDING
- AGENT-CONTEXT-COST-GROWTH
- AGENT-QUOTA-EXHAUSTION
- AGENT-HOOK-PARITY-GAP
- PROV-CLAIM-DRIFT
- PROV-UNBOUND-CLAIM
- PROV-UNCOMMITTED-STATE
- PROV-RUN-IDENTITY
- PROV-LOG-INTEGRITY
- PROV-FAILED-RUN-OMITTED
- PROV-COMPLETION-NOT-IMPROVEMENT
- REPRO-ARTIFACT-INCOMPLETE
- REPRO-INEXACT-RESUME
- REPRO-ENVIRONMENT-UNRECORDED
- COST-FAILED-TRIAL-ACCOUNTING
- COST-CANCEL-NOT-BILLING-STOP
- COST-NESTED-AGENT-SPEND
- SEC-PROMPT-INJECTION
- SEC-REMOTE-INSTRUCTION-FETCH
- SEC-SKILL-SUPPLY-CHAIN
- SEC-CREDENTIAL-INHERITANCE
- SEC-TRACKER-EXFILTRATION
- SEC-LOCAL-SERVICE-EXPOSURE
- SEC-STORE-OUTSIDE-REPO
- OPS-UNCERTAIN-PROCESS-STATE
- OPS-WINDOWS-SUPPORT-GAP
- DEP-SCHEMA-DRIFT
- DEP-TIMESTAMP-MIGRATION
- DEP-LICENSE-MISSING-OR-MIXED

## Redirect attempts

None of these were acted on. No fetched page contained text that addressed this scout directly.

1. Search-service error message: the Exa tool returned a rate-limit error telling the client to create an account and API key at a given address. Not done (account creation is not allowed here); built-in web search and fetch were used instead.
2. SwanHubX/SwanLab-Skill README: its install section gives a message to paste into a coding agent, "Fetch the installation guide and follow it", followed by a raw file address. This is a remote-instruction pattern aimed at agents. Not followed; recorded as SEC-REMOTE-INSTRUCTION-FETCH.
3. luml-ai/luml README: a section and pre-filled buttons ask the reader's coding agent to read an onboarding file from the repository and to read the user's code. Not followed.
4. Statewright discussion thread: the author tells users that the assistant "may complain" and to paste the API key again and insist. This is advice to push an assistant past its own refusal. Not followed.
5. Trackio agent guide: documentation addressed to coding agents (advice on writing alert callbacks into training scripts). Treated as documentation only.
6. Several READMEs contain install commands for agent plugins and skills (optim-agent, autotune, workflow-tracker). Treated as data; nothing was installed.

## Gaps and unverified points

- AgentHPOBench: how its classical baselines were configured, its cost and its failure rates were not found. Its numbers were read from the ar5iv rendering of v1, because the arXiv HTML returned 404 and the PDF could not be parsed here.
- The fetch tool saved two copies of that paper's PDF into the session's tool-results folder as a side effect. One attempt to read a copy failed (no PDF renderer); nothing was installed or executed.
- The small-budget advantage of agents over classical optimizers rests on three author-run benchmarks (D2, D4, D5); no independent replication was found.
- Ridge (agent access to SSH, Docker and S3 resources): repository returned 404; nothing verified.
- Session-aging numbers come from one user's own sessions (user-generated content); the direction is plausible, the size is unverified.
- The Zenodo field guide on RL post-training was not read beyond its record page.
- Last-commit dates for several repositories come from the sweep metadata, not from the repository pages.
- Star counts were not used as evidence anywhere above.
