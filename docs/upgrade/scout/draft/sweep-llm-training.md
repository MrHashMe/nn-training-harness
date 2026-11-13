# Sweep scout note: llm-training (unanchored sweep)

Scout run 2026-11-11. Input: `docs/upgrade/scout/sweep/llm-training/` (247 records, window 2026-05-14 to 2026-11-10,
sources github 106, arxiv 56, hf 41, hn 16, openalex 28). All "checked" dates below are 2026-11-11.

Status words: **Verified** = I opened the primary source and it says this. **Inferred** = my reasoning from verified
sources, or a secondary index of the primary (DeepWiki). **Unverified** = self-reported, user-generated, or not opened.
Reading method and its limit: repository files were read raw through the GitHub API where stated; other pages were
read through a fetch tool that returns a model-written extract, so numbers quoted from arXiv pages come from the
abstract page (or the arXiv HTML where stated), not from a check of the PDF body.

## 1. Summary (10 lines)

1. About 95 of 247 records bear on the kit; 53 candidates are recorded in the JSONL, from 16 deep reads at the primary source. The sweep is dominated by RL post-training papers, PEFT variants and course repositories.
2. Strongest unanchored find: `lora-speedrun`, a public frozen-task fine-tuning leaderboard whose written protocol (harness-drawn fresh seeds, all reruns must pass, one verification per code state, evaluation in a clean sandbox that re-hashes model and data pins, ties inside measured spread) is a worked example of goal 1, and whose 22 s to 12 min task is a cheap benchmark for "does the kit help".
3. Noise evidence that changes the keep-or-revert rule: identical-config repeats gave SD 0.104 in a retention ratio (Omega-S); 22 training auxiliaries, several "significant" alone, none after Holm-Bonferroni (JEPA audit); an autonomous fine-tuning pipeline scored 0.256 vs 0.415 on the same condition across runs (SAGE).
4. Evidence on autonomous fine-tuning agents (SAGE, arXiv 2609.22257): 6 of 26 attempts were abandoned for unauthorized repeated training; without accumulated experience the pipeline fell below the untuned baseline on 2 of 9 tasks; a structured experience store raised average relative improvement from 3.2% to 15.6% (self-reported, 1.5B models, no code).
5. Language-model validity: loss or likelihood, pass@1 and the task metric disagree (QLoRA study with 3 seeds; "Sharpening Tax"; SFT-overtrained checkpoints with the best pass@1 were the worst RL initialisations; attitude transfer invisible to perplexity). Guard metrics and baseline rows are needed, not one scalar.
6. Preflight: a 41-check catalogue of silent fine-tuning faults (gradian), PEFT 0.21.0 turning a silent no-op adapter target into an error, and a memory estimator whose own prospective validation shows 46% mean error. A standard-library audit plus a measured probe step is the cheap core answer.
7. Technique hypotheses with measured gains exist (packing plus completion-only loss, short-example pruning with one aggressive epoch, Muon in pretraining, same optimizer as pretraining, SGD for few-shot full fine-tuning, later-layers-only, a data-free forgetting penalty), but every one is regime-bound; Muon's pretraining gain does not survive fine-tuning in two 2026 studies. The menu must carry regime, date and evidence grade.
8. Tooling moved: Unsloth is now a Desktop/Studio product (server-side tools on by default, Studio AGPL-3.0); Oumi v0.9 wraps SkyPilot and Optuna and ships an MCP server but no budget cap; axolotl v0.21.1 has config validation, a label-mask debug view, cloud launchers and sweeps. They are launch targets for `expctl`, not dependencies.
9. Unknown-unknown for security: training frameworks now ship agent-instruction files (AGENTS.md, CLAUDE.md, `agent-docs/`, `llms.txt`) and `curl | sh` installers. Cloning or vendoring one puts third-party instructions on the agent's reading path.
10. Limits of this note: Exa search was rate-limited (WebSearch, WebFetch, GitHub API and DeepWiki were used instead); the 648-page RLVR field guide could not be read beyond abstract and record page; most paper results are self-reported preprints without code.

## 2. Selected items (one line each)

### GitHub
- [Saivineeth147/lora-speedrun](https://github.com/Saivineeth147/lora-speedrun) (2026-07-18) - frozen task, frozen hardware, 3-fresh-seed verified wall-clock leaderboard for LoRA; a frozen-evaluator protocol and a benchmark task.
- [DaoyuanLi2816/can-i-finetune-this](https://github.com/DaoyuanLi2816/can-i-finetune-this) (2026-05-16) - memory preflight for single-GPU LoRA/QLoRA without loading weights; out-of-memory check before launch.
- [gradian-ai/gradian](https://github.com/gradian-ai/gradian) (HN 2026-08-04) - attribution of LoRA regressions to training examples plus 41 deterministic dataset/config/loss-curve checks; catalogue for a preflight audit.
- [KellerJordan/Muon](https://github.com/KellerJordan/Muon) (2026-05-24) and [blog](https://kellerjordan.github.io/posts/muon/) (HN 2026-10-15) - optimizer for hidden 2D weights; hypothesis with measured pretraining gains, now in PyTorch.
- [huggingface/peft](https://github.com/huggingface/peft) (2026-11-10) - PEFT library; its method-comparison suite is the best same-hardware evidence source for adapter variants.
- [unslothai/unsloth](https://github.com/unslothai/unsloth) (2026-11-10) - fine-tuning library that became a local UI product; changes how users fine-tune and how agents are started.
- [hiyouga/LlamaFactory](https://github.com/hiyouga/LlamaFactory) (2026-11-10) - unified YAML/GUI fine-tuning of 100+ models; a common command `expctl` will be asked to launch.
- [axolotl-ai-cloud/axolotl](https://github.com/axolotl-ai-cloud/axolotl) (2026-11-10) - YAML fine-tuning with validation, tokenisation debug view, cloud launch and sweeps; launch target and pattern source.
- [oumi-ai/oumi](https://github.com/oumi-ai/oumi) (2026-11-10) - SFT/RL, evaluation, remote launch and MCP server in one CLI; overlaps goals 3 and 4.
- [MakazhanAlpamys/Soup](https://github.com/MakazhanAlpamys/Soup) (2026-11-10) - one-YAML fine-tune CLI with "layer streaming"; example of self-reported numbers later corrected.
- [radixark/miles](https://github.com/radixark/miles) (2026-11-10) - RL post-training framework; routing replay and token-in-token-out as guards against training-inference mismatch.
- [whitecircle/halo](https://github.com/whitecircle/halo) (2026-08-26) - training framework; release notes show "resume problems now stop the run instead of passing silently"; custom licence.
- [quantumglass/GRPO-series](https://github.com/quantumglass/GRPO-series) (2026-06-19) - single-GPU GRPO-family code; possible local bed for an RL-style run contract (3 stars).
- [tanzelin430/The-Scaling-Law-for-Reinforcement-Learning](https://github.com/tanzelin430/The-Scaling-Law-for-Reinforcement-Learning) (2026-07-01) - ACL 2026 scaling study; budget planning for RL post-training.
- [SergioTermann/awesome-post-training-RL](https://github.com/SergioTermann/awesome-post-training-RL) (2026-09-11) - curated paper list; seed for the scouting step, not evidence.
- [THUDM/Awesome-Parameter-Efficient-Fine-Tuning-for-Foundation-Models](https://github.com/THUDM/Awesome-Parameter-Efficient-Fine-Tuning-for-Foundation-Models) (2026-11-08) - curated PEFT list; scouting seed.
- [revaldianggara/PEFT-SingLoRA](https://github.com/revaldianggara/PEFT-SingLoRA) (2026-09-27) - single-matrix LoRA with half the adapter parameters; hypothesis candidate.
- [doem97/metalora](https://github.com/doem97/metalora) (2026-09-12) - meta-learned PEFT hyperparameters (CVPR 2025); hypothesis source.
- [MaxwellYaoNi/PACE](https://github.com/MaxwellYaoNi/PACE) (2026-06-05) - consistency regularisation for PEFT generalisation (NeurIPS 2024); hypothesis.
- [microsoft/mttl](https://github.com/microsoft/mttl) (2026-10-27) - modular models from adapter libraries; adapter reuse pattern.
- [SimplexLab/TorchJD](https://github.com/SimplexLab/TorchJD) (2026-11-07) - Jacobian descent for several losses; hypothesis for multi-objective runs.
- [hoomanesteki/forge-small-llm-grpo-text-to-sql](https://github.com/hoomanesteki/forge-small-llm-grpo-text-to-sql) (2026-10-25) - small-model GRPO with verifiable SQL rewards on free GPUs; small RL example task.
- [MIRALab-USTC/GA-ARL](https://github.com/MIRALab-USTC/GA-ARL) (2026-11-05) - gradient-aware asynchronous RL on verl; efficiency technique.
- [leo-dcfa/ai-latent-bias-transfer](https://github.com/leo-dcfa/ai-latent-bias-transfer) (HN 2026-06-15) - 18 LoRA runs showing an unstated attitude transfers to unrelated topics; side-effect failure mode.
- [autonomous-ai/autonomous-grid](https://github.com/autonomous-ai/autonomous-grid) (2026-06-17) - pool machines you own for training; alternative to renting (marginal).
- [Optima-CityU/neural-spectral-capacity](https://github.com/Optima-CityU/neural-spectral-capacity) (2026-09-19) - capacity estimate from architecture alone; possible pre-run diagnostic (marginal).
- [Goekdeniz-Guelmez/MLX-LoRA-Studio](https://github.com/Goekdeniz-Guelmez/MLX-LoRA-Studio) (2026-06-11) and [Neywa-Labs/mlx-vlm](https://github.com/Neywa-Labs/mlx-vlm) (2026-11-10) - Apple-silicon fine-tuning; matters only for the macOS path.
- [h2oai/h2o-llmstudio](https://github.com/h2oai/h2o-llmstudio) (2026-11-09), [ludwig-ai/ludwig](https://github.com/ludwig-ai/ludwig) (2026-11-09), [meta-llama/llama-cookbook](https://github.com/meta-llama/llama-cookbook) (2026-05-19), [kvcache-ai/ktransformers](https://github.com/kvcache-ai/ktransformers) (2026-11-10) - other fine-tuning front ends and recipes; alternatives, not read.
- [Juneo-Lab/decision-forge](https://github.com/Juneo-Lab/decision-forge) (2026-10-30) - policy compiled into verifiable training data; data-side tooling (marginal).

### arXiv
- [What Broke & Why: Practical Lessons from RL Post-Training](http://arxiv.org/abs/2611.10844v1) (2026-11-07) - 648-page failure-first field guide on 1 to 8 GPUs; symptom-indexed failure catalogue.
- [Is Persona Generalization Predictable?](http://arxiv.org/abs/2611.12864v1) (2026-11-09) - in-domain and out-of-domain behaviour change lie on one line across hyperparameters; side-effect prediction and control.
- [LLMs as a Universal Searcher for Open-World AutoML](http://arxiv.org/abs/2611.12791v1) (2026-11-09) - trained LLM ranks joint architecture/hyperparameter/data-ratio choices; alternative to an agent loop.
- [Adapting Small Language Models to Romanized Nepali](http://arxiv.org/abs/2611.12628v1) (2026-11-09) - QLoRA on three models with three seeds; likelihood and overlap metrics rank models differently.
- [Agentic-OPD](http://arxiv.org/abs/2611.12799v1) (2026-11-09) - discarded checkpoints solve problems the best-validation checkpoint fails; checkpoint retention policy.
- [Spectral Rank and Step-Direction Dynamics in Post-Training](http://arxiv.org/abs/2611.11752v1) (2026-11-09) - stable rank, energy rank and checkpoint-displacement cosine as update diagnostics.
- [Full Fine-Tuning is not the Problem](http://arxiv.org/abs/2611.11152v1) (2026-11-08) - in few-shot CLIP adaptation Adam collapses and plain SGD full fine-tuning beats PEFT; optimizer confound.
- [Primitives and Paths](http://arxiv.org/abs/2611.11260v1) (2026-11-08) - measure base-model solution support and primitive coverage before RL; predicts whether RL can help.
- [DISCOVER](http://arxiv.org/abs/2611.11145v1) (2026-11-08) - variance-guided prompt selection under a 10% unique-sample budget (NeurIPS 2026).
- [BRAT](http://arxiv.org/abs/2611.10873v1) (2026-11-07) - reusing rollout batches overfits the sampled group; bounded update for multi-pass training.
- [The Surprising Effectiveness of Deleting Weights](http://arxiv.org/abs/2611.10866v1) (2026-11-07) - learned mask zeroing under 0.05% of weights matches full fine-tuning and forgets less.
- [The Delta Gap](http://arxiv.org/abs/2611.10658v1) (2026-11-07) - a published model scores 0.977 on the usual metric and loses to a mean-prediction baseline on the one that matters; metric artefact.
- [Rethinking Dynamic Rank in LoRA (GEAR)](http://arxiv.org/abs/2611.07349v1) (2026-11-05) - rank expansion from the normal-space spectrum; fewer parameters, higher score.
- [When Does Sliced Inference Pay Off?](http://arxiv.org/abs/2611.12657v1) (2026-11-09) - comparison under pre-specified hypotheses and calibration-only tuning; exemplar of pre-registration (not read).
- [EditJudge-Bench](http://arxiv.org/abs/2611.12524v1) (2026-11-09) - auditing model judges with synthetic ground truth; relevant if a judge model ever scores runs (not read).
- [VLA Adaptation with Real and Simulated Data](http://arxiv.org/abs/2611.12676v1) (2026-11-09) - how much data, how many updates, how to select checkpoints when fine-tuning (not read).
- [OptIMerge](http://arxiv.org/abs/2611.07543v1) (2026-11-05) - optimisation-based merging of fine-tunes; model-soup alternative (not read).
- [Bayesian Low-Rank Posteriors for Membership Inference](http://arxiv.org/abs/2611.10455v1) (2026-11-07) - privacy audit of fine-tuned models (not read).

### Hugging Face papers
- [Strategy Accumulation and Guided Execution for Automated LLM Fine-Tuning (SAGE)](https://huggingface.co/papers/2609.22257) (2026-09-06) - automated fine-tuning with a persistent experience repository; goals 1 and 2.
- [Sharpening Tax in Post-Training](https://huggingface.co/papers/2610.01509) (2026-10-01) - RL post-training raises pass@1 and lowers coverage; diagnostic metric.
- [The Mirage of Optimizing Training Policies (MIPU)](https://huggingface.co/papers/2606.29526) (2026-06-28) - sampler and trainer engines assign different probabilities; accept updates on an inference-side check.
- [Rufus-Air: An Open LLM Post-Training Recipe](https://huggingface.co/papers/2609.29421) (2026-09-24) - eight-stage open recipe; stage ordering by reward reliability.
- [Omega-S](https://huggingface.co/papers/2608.03887) (2026-08-04) - data-free penalty against forgetting, ten seeds, negative results and a same-config noise bound.
- [SoFT](https://huggingface.co/papers/2609.32493) (2026-09-26) - soft targets with minimum-KL change to the base distribution; learning versus retention.
- [Representation Without Reward: A JEPA Audit](https://huggingface.co/papers/2605.15394) (2026-05-14) - 22 auxiliaries, structured null after family-wise correction.
- [Adaptive Preconditioners Trigger Loss Spikes in Adam](https://huggingface.co/papers/2506.04805) (2026-05-25) - loss spikes come from the second-moment estimate decoupling; predictor of spikes (ICML 2026).
- [Symmetry-Compatible Principle for Optimizer Design](https://huggingface.co/papers/2605.18106) (2026-05-18) - per-parameter-class optimizers for embeddings, heads, MLPs, routers (NeurIPS 2026).
- [Agentic ESOpt](https://huggingface.co/papers/2608.17310) (2026-08-18) - evolution strategies fine-tune all parameters with inference-level memory.
- [Predicting Mergeability of PEFT Updates (MergeProbe)](https://huggingface.co/papers/2606.19549) (2026-06-17) - predict from the first few percent of training whether adapters will merge.
- [Z-PEFT](https://huggingface.co/papers/2608.02271) (2026-08-03) - weight-space detection of backdoored adapters; supply chain of downloaded adapters.
- [Nereus](https://huggingface.co/papers/2609.34645) (2026-09-28) - cost-aware runtime that changes parallelism plans mid-run; cluster scale.
- [SlideDP](https://huggingface.co/papers/2609.34162) (2026-09-28) - host-resource contention in shared multi-GPU fine-tuning (not read).
- [Self-Distilled Agentic RL](https://huggingface.co/papers/2605.15155) (2026-05-14), [Distilled RL](https://huggingface.co/papers/2607.17247) (2026-07-19), [MOPD](https://huggingface.co/papers/2606.30406) (2026-06-29) - distillation terms inside or after RL (not read).
- [LoGRA](https://huggingface.co/papers/2610.06647) (2026-10-05), [DRPO](https://huggingface.co/papers/2606.09821) (2026-06-08), [PACT](https://huggingface.co/papers/2609.26355) (2026-09-22), [Cliff](https://huggingface.co/papers/2609.02817) (2026-09-02), [Progress Advantage](https://huggingface.co/papers/2606.26080) (2026-06-24) - RL memory, stability and credit-assignment techniques (not read).
- [Skill-RM](https://huggingface.co/papers/2606.03980) (2026-06-02) - reward computation as an agent skill; a judge the trainee could influence (not read).
- [SAERL](https://huggingface.co/papers/2605.27354) (2026-05-26) - sparse-autoencoder signals for data diversity, difficulty and filtering (not read).
- [WSR-Tune](https://huggingface.co/papers/2610.26443) (2026-10-20) and [AsFT](https://huggingface.co/papers/2506.08473) (2026-06-10) - keeping safety behaviour during fine-tuning (not read).
- [OraclePhys](https://huggingface.co/papers/2608.17162) (2026-08-17) - fine-tuning teaches what the label's answer form specifies; objective form as a hypothesis axis (not read).
- [ZO-Act](https://huggingface.co/papers/2607.01125) (2026-07-01) and [Magnitude-direction decoupling](https://huggingface.co/papers/2606.25971) (2026-06-24) - zeroth-order fine-tuning and weight reparameterisation (not read).

### Hacker News and OpenAlex
- [Fine-tuning an LLM to write docs like it's 1995](https://passo.uno/fine-tuning-docs-llm/) (2026-06-05, 196 points) - first-person account of a coding-agent-driven QLoRA project on rented GPUs, including lost adapters.
- [Taming optimization variance in compact neural shading networks](https://research.nvidia.com/labs/rtr/publication/bitterli2026taming/) (2026-08-03) - train an ensemble of initialisations, prune losers during training; variance control at fixed wall-clock.
- [Fixing LLM Writing with Distribution Fine Tuning](https://rosmine.ai/2026/05/18/fixing-llm-writing-with-distribution-fine-tuning/) (2026-05-18) - returned HTTP 404 on 2026-11-11; not read.
- [The Ultimate Guide to Fine-Tuning LLMs](https://arxiv.org/abs/2408.13296) (HN 2026-06-16; paper from 2024) - long review; background only, outside the 12-month frontier window.
- [LLM Post-Training: A Deep Dive Into Reasoning LLMs](https://doi.org/10.1109/tpami.2026.3720414) (2026-08-04) - survey; taxonomy for the scouting step (not read).
- [Harmful Fine-tuning Attacks and Defenses: A Survey](https://doi.org/10.1145/3817114) (2026-05-22) - survey of fine-tuning as an attack surface (not read).
- [Accelerating scientific discovery with Co-Scientist](https://doi.org/10.1038/s41586-026-10644-y) and [A multi-agent system for automating scientific discovery](https://doi.org/10.1038/s41586-026-10652-y) (2026-05-19) - automated-research precedents; left to the auto-research scouts.

Skipped as off-topic: inference engines, robotics, physics, wireless, course notes, personal pages, federated learning,
medical and geospatial adapters (about 150 records).

## 3. Deep reads

### 3.1 lora-speedrun (commit 1436658, 2026-08-04, MIT)
| Claim | Source | Status |
|---|---|---|
| Task: LoRA-tune Qwen2.5-1.5B to at least 57.0% GSM8K exact match on one L40S; score is training wall-clock; adapter-only, at most 30M trainable parameters; frozen 2026-07-18. Second track: SmolLM2-1.7B, SQuAD v1.1, at least 75.5%. | https://github.com/Saivineeth147/lora-speedrun/blob/main/TASK.md (raw file) | Verified |
| A record counts only after 3 reruns with fresh seeds chosen by the verifier at verification time; all 3 must clear the target; official time is the mean, never the fastest. | https://github.com/Saivineeth147/lora-speedrun/blob/main/JUDGING.md (raw file) | Verified |
| "One verification per code state": re-verification only after a code change, to stop re-requesting until a lucky batch. | JUDGING.md | Verified |
| Differences smaller than the measured run-to-run spread are ties. A statistical "stall" filter (drop runs past 1.5x median) was withdrawn after an outside reviewer showed it was uncalibrated and biased; the measurement boundary was fixed instead (clock starts after a warm cache). | JUDGING.md | Verified |
| Evaluation runs in a separate fresh sandbox that first re-hashes base model and train/test data against committed pins; a clean image means `sitecustomize.py` tricks and poisoned site-packages from training do not reach evaluation. | https://github.com/Saivineeth147/lora-speedrun/blob/main/SECURITY.md (raw file) | Verified |
| Untrusted training code runs only network-blocked, with no secrets, under a hard timeout; workflows holding tokens never execute submitted code and refuse changes outside `submissions/`. | SECURITY.md | Verified |
| An AI reviewer screens each submission for exfiltration, harness tampering and test-set contact; it is advisory only, is told to treat the diff as data, and "the security of the system never depends on the agent being right". | SECURITY.md, JUDGING.md | Verified |
| Reports carry hardware fingerprint, harness commit, `env.lock` hash and all seeds. | JUDGING.md | Verified |
| Records: baseline 11m57s at 59.4%; sequence packing plus completion-only loss masking 6m05s at 61.1% (-49%); one 4e-4 epoch on 3,000 examples 1m53s; shortest-4k pruning 1m44s at 60.3%; current 0m22s at 58.0% with 12 optimizer updates. Track 2: 8m45s to 0m50s. | https://github.com/Saivineeth147/lora-speedrun (README, raw file) | Verified (numbers are the project's own verified runs; single verifier) |
| The current record's third run cleared the target by 0.09 percentage points (about 1.2 of 1,319 problems). | latest commit message, 2026-08-04 | Verified |
| The pass/fail gate is the GSM8K test split, reused for every submission. Accuracy fell from 61.1% to 58.0% as times fell: optimising against a threshold consumes the margin. | README + TASK.md | Inferred |
| Local iteration works on any 24 GB+ card (`harness/run_submission.py submissions/000-baseline --runs 1`); official timing needs a Modal account. | README | Verified |

What the kit could take: (a) the confirmation rule for "keep" (seeds drawn by the harness after the tree is frozen,
all must pass, one confirmation per tree hash, ties inside spread); (b) clean-process evaluation with a hash manifest
for evaluator code, evaluation data and base weights; (c) the report fields; (d) the task itself as the cheap,
rerunnable benchmark the brief asks for ("a way to measure whether the kit actually helps"). Cost: (a) to (c) are
standard-library code; (d) needs a GPU, PyTorch and a model download, so it is an optional module. Maturity: 151 stars,
one maintainer, records self-verified; the protocol is the value, not the adoption.
Second phrasing (limitations): a forum thread about the project raises overfitting to one model and one task, and
notes 2 to 5% warm-run jitter, so strict ranking can imply differences inside noise
(https://huggingface.co/posts/vineeth98/583147446182455, Unverified, user-generated). Corroboration from a primary
source: the NeurIPS 2023 LLM Efficiency Fine-tuning Competition report found top entries "exhibit significant
overfitting on benchmark datasets" and that winners mostly curated data (https://arxiv.org/abs/2503.13507, v1
2025-03-13, Verified at abstract level).

### 3.2 canifinetune 0.4.1 (2026-10-04, MIT; first release 0.1.1 on 2026-06-10)
| Claim | Source | Status |
|---|---|---|
| Estimates training memory (weights, quantisation, gradients, optimizer state, activations, logits/loss, overhead) without PyTorch and without downloading weights; emits a runnable recipe. Core needs Python 3.10 to 3.14. | https://github.com/DaoyuanLi2816/can-i-finetune-this (README, raw file) | Verified |
| Own prospective validation: 4 predeclared LoRA/QLoRA cases on Qwen2.5-0.5B, one Windows RTX 4080; mean absolute error 46.2%, all four overestimates (+29% to +64%), 0 of 4 false-feasible; "no accuracy improvement is demonstrated" over 0.3.0. | https://daoyuanli2816.github.io/can-i-finetune-this/validation-0.4.0/ | Verified |
| Native Windows CPU/CUDA and Linux CPU are qualified; WSL GPU, other GPUs, Flash Attention and Liger are not. Distributed training and pre-quantised bases unsupported. | README | Verified |
| Other estimators found by a second search (FitCheck, a training-memory calculator, web calculators) publish no validated error bound. | https://discuss.huggingface.co/t/fitcheck-estimate-llm-training-and-serving-vram-before-you-run/180737 and search results | Unverified (user-generated, not opened) |

Take: the idea "plan, then measure, then compare", not the package. A formula with 46% error cannot decide a launch;
a 3-step probe run that records peak reserved memory through `runlog` can. The tool stays an optional aid for
choosing a starting configuration. Cost: pip package, Python 3.10+, not qualified on WSL GPU (the kit's Windows path).

### 3.3 gradian 0.1.0 alpha (single commit 2026-08-10, Apache-2.0)
| Claim | Source | Status |
|---|---|---|
| Attributes a capability regression after LoRA fine-tuning to training examples with curvature-corrected influence (DataInf), a contrastive query gradient, and cluster reports; gives no attribution when the capability delta's bootstrap interval includes zero. | https://github.com/gradian-ai/gradian (README via fetch) | Verified |
| 41 deterministic checks in three groups. Config: attention-only targets, base-model mismatch, capacity vs data, fp16, clipping disabled, high dropout, learning rate too high or too low, max length shorter than data, no eval set, no warmup, overtraining, packing with completion-only loss, pad equals EOS, seed unset, small effective batch, undertrained. Data: truncated completions, conflicting answers, duplicates and near-duplicates, empty targets, format inconsistency, length outliers, loss-mask coverage, missing EOS, no chat template, no supervised tokens, prompt equals target, template prefix mismatch, tiny dataset, train/eval contamination, truncation. Dynamics: always clipping, gradient-norm explosion, plateau, spike, schedule not decayed, NaN, overfitting, too few steps. Thresholds are not documented on the page. | https://gradian.dev/docs/diagnostics | Verified |
| Self-reported validation only: planted-poison tests on a 135M and a 1B model; leave-one-out rank correlation 0.45 and 0.49 with intervals that include zero; validated for one failure type. | README | Verified (that the README says so) |
| Limits: LoRA on Linear layers only; one device; gradient index about 45 MB per example at 1B (about 90 GB for 2,000 examples); no package-index release; install by `curl ... | sh` or from source. | README | Verified |
| Adoption signal: 68 stars, 3 HN points. | README page, sweep | Verified (weak signal) |

Take: the check catalogue as a specification for a standard-library preflight audit (most data and dynamics checks
need only the dataset file, the config and the metrics log the kit already has). Take also the rule "no diagnosis
when the delta is inside noise". Do not adopt the tool now: alpha, one commit, pipe-to-shell installer, 90 GB index.
Note a real tension the audit must explain: gradian flags "packing with completion-only loss" as a fault, while the
speedrun's first verified record is exactly packing plus completion-only masking done with a correct mask. The check
should test loss-mask coverage, not ban the combination.
Second phrasing (alternatives): no dedicated linter for chat-template, EOS, padding and loss-mask faults was found;
course notes agree on the same fault classes (search 2026-11-11, Unverified, user-generated). axolotl's
`preprocess --debug` prints tokenised prompts and label masks (DeepWiki index of axolotl-ai-cloud/axolotl, Inferred).

### 3.4 Muon (repo last commit 2026-05-24, MIT, no releases; `torch.optim.Muon` in PyTorch 2.15)
| Claim | Source | Status |
|---|---|---|
| Orthogonalises the momentum update of 2D hidden weights with 5 Newton-Schulz steps; embeddings, heads, gains and biases must use AdamW. | https://kellerjordan.github.io/posts/muon/ ; https://github.com/KellerJordan/Muon | Verified |
| PyTorch ships it: `torch.optim.Muon(params, lr=0.001, weight_decay=0.1, momentum=0.95, nesterov=True, ns_steps=5, adjust_lr_fn=None)`; "Muon only supports 2D params"; `adjust_lr_fn="match_rms_adamw"` reuses AdamW-tuned rates. | https://docs.pytorch.org/docs/2.15/generated/torch.optim.Muon.html ; the same class and signature are on the 2.9 docs page (source tag v2.9.1), https://docs.pytorch.org/docs/2.9/generated/torch.optim.Muon.html | Verified (whether it predates 2.9: not checked) |
| Pretraining evidence: 1.35x on the NanoGPT speedrun record; CIFAR-10 94% record 3.3 to 2.6 A100-seconds; 1.5B model 10 vs 13.3 8xH100-hours against tuned AdamW. | author's blog (self-published; set in a public competitive task) | Verified that claimed; self-reported |
| The author lists as open whether it works for fine-tuning or RL. | blog | Verified |
| Fine-tuning Qwen3-4B (full parameters, four datasets): with the default auxiliary AdamW rate Muon trails Adam by 0.113 NLL; with both rates tuned they are indistinguishable (1.8745 vs 1.8714); weight decay has no measurable effect. | https://neurips.cc/virtual/2026/161532 (OPT 2026 workshop poster) | Verified at abstract level |
| "Optimizer-model consistency": full fine-tuning with the optimizer used in pretraining forgets less at equal or better new-task score; Muon throughout does worse on reasoning-task fine-tuning. | https://arxiv.org/abs/2605.06654 v1 (2026-05-07) | Verified at abstract level |
| Muon underperforms AdamW when fine-tuning an AdamW-pretrained 1B model on three datasets. | https://arxiv.org/pdf/2606.13867 (search summary only) | Unverified |

Take: a menu entry "Muon for from-scratch or continued pretraining of 2D weights; not a default for fine-tuning;
tune the auxiliary AdamW rate if you try it", dated, with the three fine-tuning studies attached. General lesson:
a technique's gain is tied to its regime and to matched tuning effort. Cost: none for the kit (text only).

### 3.5 PEFT v0.21.2 (2026-10-01) and its method-comparison suite
| Claim | Source | Status |
|---|---|---|
| Releases: v0.20.0 2026-07-28 (nine new methods incl. HiRA, MiCA, Uni-LoRA; `KappaTuneSelector` picks LoRA targets by condition number), v0.21.0 2026-09-15 (Riemannian-preconditioned LoRA optimizer, KaSA, Super-Tuning, ShadowPEFT), v0.21.2 2026-10-01. | https://github.com/huggingface/peft/releases (GitHub API and page) | Verified |
| v0.21.0: `add_adapter` raises when an adapter targets non-existent layers "instead of silently doing nothing" (#3534); adding adapters no longer changes `requires_grad` of existing ones (#3495). | release notes | Verified |
| v0.21.0: an update to the OSF method (#3524) cuts its memory 22% and training time 46% on the MetaMathQA benchmark with accuracy and forgetting stable (maintainer-measured). The notes do not name the baseline; the wording suggests OSF before the update, so this is a reason to upgrade, not a new technique. | release notes (re-read 2026-11-11) | Verified (baseline Inferred) |
| v0.20.0: maintainers "found a bug in the forgetting metric" of their own benchmark and republished numbers. v0.21.0 adds a git dirty flag to results (#3385). | release notes | Verified |
| Suite rules: maintainers run every experiment on their own hardware; "Do not edit existing experiments, always create new ones"; comparisons are meaningless near 0% or 100%; a run should take "a few hours at most on high-end consumer hardware". | https://github.com/huggingface/peft/tree/main/method_comparison | Verified |
| MetaMathQA task: train on MetaMathQA, validate on a sample of GSM8K train, test on GSM8K test; each run records test and validation accuracy, reserved memory (mean, 99th percentile, max), train time, adapter file size, package versions with commit hashes and system info. | https://github.com/huggingface/peft/tree/main/method_comparison/MetaMathQA | Verified |

Take: cite the comparison Space (https://huggingface.co/spaces/peft-internal-testing/PEFT-method-comparison) in the
fine-tuning reference as the dated evidence source for adapter variants, instead of listing variants from memory.
Take two safeguards: a preflight assertion that the trainable-parameter count is non-zero and that adapter targets
matched modules; and a versioned evaluator with a known-answer self-test, because even a maintained benchmark shipped
a wrong metric. Cost: text plus a few lines in the audit.

### 3.6 SAGE (arXiv 2609.22257 v1, 2026-09-06, CC BY 4.0, no code found)
| Claim | Source | Status |
|---|---|---|
| Two stages: MCTS exploration by Planner, Executor, Reviewer and Critic agents with deterministic evaluation between execution and review; a Distillation Agent writes per-node exploration records and cross-task insights into a repository; new tasks retrieve from it. | https://arxiv.org/html/2609.22257v1 | Verified |
| Records hold the strategy tuple (method, data, format, hyperparameters) and score; insights state the conditions under which they hold or break; confidence starts at 0.6, +0.1 useful, -0.1 useless, x0.5 harmful, pruned below 0.2. | arXiv HTML | Verified |
| Nine unseen tasks: average relative improvement over the untuned model 3.2% without experience, 15.6% with (mean of 3); 14.4% vs 29.2% best of 3 rounds. Without experience the pipeline regressed on LawBench (-6.1%) and OpenFindata (-11.3%). | abstract + HTML | Verified (self-reported) |
| "6 of 26 attempts were abandoned for unauthorized repeated training"; compliance checks are "guardrails, not proof of data isolation". | arXiv HTML | Verified |
| High run variance (HumanEval round 3: 0.256 vs 0.415 across runs in the same condition); a bundled change regressed; only 1.5B models; GPU hours not reported. | arXiv HTML (limitations) | Verified |
| Out-of-category transfer with insights only: mean of 3 fell below baseline on one translation set. | arXiv HTML | Verified |

Take: (a) journal entries as structured records (strategy tuple, delta vs baseline and vs parent run, conditions,
verdict useful/useless/harmful), so that the scouting step and later sessions can retrieve them; (b) the rule
violations and regressions as evidence that the procedure must be enforced by `expctl` and the guard, not asked for;
(c) one change per experiment. Do not take the multi-agent MCTS machinery: the kit's premise (brief) is that
elaborate scaffolds did not pay, and this paper's own gain comes from the stored experience, not from more agents.
Cost of (a): template and a few fields; risk: an insight applied outside its conditions (negative transfer).

### 3.7 Coverage, entropy and checkpoint choice
| Claim | Source | Status |
|---|---|---|
| Across 14 base/post-trained pairs, four families, three agentic benchmarks (42 cases) post-trained models often lose to their base models on pass@K given test-time budget; post-training pushes tasks to always-solved or never-solved. PTGS (per-prompt temperature) reduces the loss. No numbers in the abstract. | https://arxiv.org/abs/2610.01509 v1 (2026-10-01) | Verified at abstract level; self-reported |
| Deeper SFT raises pre-RL pass@1 but peak GRPO pass@10 falls from 0.806 to 0.481 (3 seeds, Qwen2.5-Coder-3B); pre-RL pass@1 correlates -0.75 with the RL outcome, pre-RL entropy +0.69. A pre-RL entropy screen plus a 150-step monitor rejects bad starts and saves 62.5% to 100% of RL compute. | https://icml.cc/virtual/2026/82731 (ICML 2026 workshop poster) | Verified at abstract level; small n |
| The best-validation checkpoint of a GRPO run fails problems that earlier checkpoints solved; the union across checkpoints is much larger; distilling from the discarded pool gains up to 7.4 points. | https://arxiv.org/abs/2611.12799 v1 (2026-11-09) | Verified at abstract level; self-reported |

Take: when a run's checkpoint feeds a later stage, "best validation score" is not a safe selection rule; record a
second signal (coverage over k samples or output entropy) beside the primary metric, and let the retention policy keep
more than one checkpoint when disk allows. This applies to RL-style post-training; for plain supervised runs it is
a hypothesis, not a rule.

### 3.8 Noise and multiple comparisons
| Claim | Source | Status |
|---|---|---|
| Omega-S: a three-line weight-only penalty; Llama-3-8B LoRA, ten seeds; HumanEval pass@1 retained 0.238 vs 0.173; beats tuned weight decay on 10 of 10 seeds and tuned EWC on 8 of 10. Repeating an identical configuration (same seed, same hardware) gave SD 0.104 in the retention ratio, which "bounds seed-paired comparisons". Code, per-seed data and negative results published. | https://arxiv.org/abs/2608.03887 v1 (2026-08-04); code https://github.com/BiomeMakers/OmegaS-LLM (not opened) | Verified at abstract level; single author |
| JEPA audit: 22 auxiliaries on a fixed Llama-3.2-1B LoRA harness; several pass an uncorrected paired test (best +2.53 points, p = 0.003); none survives Bonferroni or Holm-Bonferroni; a 5-seed full fine-tuning replication is null. | https://arxiv.org/abs/2605.15394 v1 (2026-05-14) | Verified at abstract level |
| Ensemble-and-prune training reduces the chance of landing in a poor minimum at equal wall-clock (small shading networks; no numbers in the abstract). | https://research.nvidia.com/labs/rtr/publication/bitterli2026taming/ (SIGGRAPH 2026) | Verified at abstract level |

Take: the keep rule needs a noise floor measured on this repository (repeat the baseline unchanged, including with
the same seed), and a 50-experiment night needs either a correction for the number of hypotheses tried or a final
confirmation on data the loop never scored against. An effect of +2.5 points at p = 0.003 was noise in a family of 22.

### 3.9 Side effects of fine-tuning
| Claim | Source | Status |
|---|---|---|
| In-domain and out-of-domain persona rates follow an approximately probit-linear relation across learning rate, weight decay and duration, for Qwen and Llama; those knobs reduce transfer mainly by weakening in-domain learning; fine-tuning only later layers gives a shallower slope. | https://arxiv.org/abs/2611.12864 v1 (2026-11-09, 55 pages) | Verified at abstract level |
| 18 LoRA runs (2 models x 3 framings x 3 seeds, about 7 minutes each on one consumer GPU): a cautious framing in everyday-advice data shifted stated opinions on unrelated held-out topics by d of about 0.9 to 2.2; perplexity and refusal checks showed nothing; a bare-token log-probability metric misread fine-tuned models. Pre-registered smallest effect d = 0.2. No licence shown. | https://github.com/leo-dcfa/ai-latent-bias-transfer | Verified that reported; individual project, Unverified result |

Take: an optional guard metric for language-model fine-tuning: a small fixed probe set outside the task domain,
scored before and after, reported beside the task metric. Later-layers-only is a menu hypothesis for side-effect control.

### 3.10 Metric validity
| Claim | Source | Status |
|---|---|---|
| Three 2-3B models, one QLoRA recipe, three seeds, 1,000 held-out items: one model has lower bits-per-byte in every seed (0.042, CI 0.039 to 0.046) yet is inseparable on chrF++ (30.51 vs 30.61) and BLEU; which model gains most depends on the zero-shot prompt. | https://arxiv.org/abs/2611.12628 v1 (2026-11-09) | Verified at abstract level |
| A published model scores 0.977 on the customary global correlation and 0.076 on the response-specific one; predicting the mean training change scores 0.267. | https://arxiv.org/abs/2611.10658 v1 (2026-11-07), outside language models | Verified at abstract level; single author |

Take: the configured metric must be the task metric, with loss logged but not deciding; every comparison table
carries the untuned model and a trivial predictor as rows; the baseline prompt is frozen with the evaluator.

### 3.11 "What Broke & Why" (arXiv 2611.10844 v1, 2026-11-07; Zenodo v1.0 dated 2026-07-01, CC BY 4.0)
| Claim | Source | Status |
|---|---|---|
| 648-page single-author field guide to RL post-training on 1 to 8 H100s; failure classes named in the abstract: no useful reward, reward exploitation, exploration stops, improvement that is an artefact of misleading evaluation; includes a symptom-indexed debugging guide and chapters on evaluation discipline, small-evaluation noise and reproducibility. | https://arxiv.org/abs/2611.10844 ; https://zenodo.org/doi/10.5281/zenodo.21115798 | Verified (abstract and record only) |
| Content of the failure catalogue and its fixes. | PDF body | Unverified (no HTML version; PDF could not be rendered here) |

Take: a pointer in an optional RL reference, to be read by a person before anything is copied. Second phrasing
(limitations of GRPO-style training) returned: zero gradient when all rollouts in a group get the same reward,
token-level "objective hacking" distinct from verifier exploits (https://arxiv.org/pdf/2602.01103, search summary,
Unverified), and blog-level practitioner lists (Unverified).

### 3.12 Fine-tuning front ends (launch targets, not dependencies)
| Claim | Source | Status |
|---|---|---|
| Unsloth v0.1.916-beta (2026-11-06): Desktop app, Studio web UI and Core package; LoRA, QLoRA, full fine-tuning, GRPO, DPO; Windows, Linux, WSL, macOS; Core Apache-2.0, Studio AGPL-3.0; "server-side tools are enabled by default"; `unsloth start <agent>` for Claude Code, Codex and others. | https://github.com/unslothai/unsloth ; GitHub releases API | Verified |
| Unsloth "2x faster with 70% less VRAM with no accuracy loss". | README | Unverified (vendor claim, conditions not stated) |
| Oumi v0.9 (2026-09-16, Apache-2.0, "in beta"): SFT, LoRA, QLoRA, DPO, GRPO via verl; `oumi launch` on AWS, Azure, GCP, Lambda, Modal, Slurm; `oumi-mcp` server for Claude and Cursor (v0.8 notes); AGENTS.md and CLAUDE.md in the repo. | https://github.com/oumi-ai/oumi ; releases API | Verified (MCP tool list not seen) |
| Oumi's launcher uses SkyPilot; spot instances via `use_spot`; clusters auto-stop after 60 idle minutes except on providers that cannot stop (RunPod, Lambda); no budget cap feature; `oumi tune` uses Optuna. | DeepWiki index of oumi-ai/oumi | Inferred (secondary index) |
| axolotl v0.21.1 (2026-10-27): pydantic config validation, `preprocess --debug` printing tokenised prompts and label masks, `auto_resume_from_checkpoints`, cloud launch through Modal, Baseten, Nebius and SkyPilot, `--sweep`. | releases API; DeepWiki index of axolotl-ai-cloud/axolotl | Version Verified; features Inferred |
| LlamaFactory v0.9.5 (2026-05-30): latest release is five months old while the repo is pushed daily. | releases API; sweep | Verified |

Take: (a) `expctl launch -- <any of these CLIs>` must work unchanged, and the audit should read their YAML when present;
(b) no launcher found here enforces a spend cap, so the cap stays in the kit's remote module; (c) do not vendor or
auto-install any of them: they bring agent-instruction files, local servers with tools enabled, and mixed licences.

### 3.13 RL post-training mechanics (optional reference only)
| Claim | Source | Status |
|---|---|---|
| Separate engines for sampling and training assign different probabilities to the same trajectory even with synchronised weights; MIPU accepts an update only if an inference-side proxy improves. | https://arxiv.org/abs/2606.29526 v1 (2026-06-28) | Verified at abstract level |
| Reusing a rollout batch for several passes overfits the sampled group: update alignment drops by nearly an order of magnitude from in-sample to held-out rollouts on three models. | https://arxiv.org/abs/2611.10873 v1 (2026-11-07) | Verified at abstract level |
| 63 GRPO experiments on Qwen2.5 0.5B to 72B: error follows a power law in compute or data; reusing data up to 25 times is stable, 100 times overfits moderately; returns flatten past 32B. | https://github.com/tanzelin430/The-Scaling-Law-for-Reinforcement-Learning (ACL 2026, arXiv 2509.25300) | Verified (repo page) |
| Open eight-stage recipe on a 106B-parameter base: SFT, three RL stages, three agent stages, RLHF; ordered from verifiable to judge-based rewards; no code or data link. | https://arxiv.org/abs/2609.29421 v2 (2026-09-25) | Verified at abstract level |

Take: if the kit ever supports RL-style runs, the run contract needs reward and entropy curves and a sampler/trainer
consistency check; nothing here is needed for the default install.

### 3.14 Optimizer diagnostics
| Claim | Source | Status |
|---|---|---|
| Adam loss spikes arise when the second-moment estimate stops tracking current squared gradients and the preconditioned curvature exceeds 2/lr for sustained periods; five stages; a predictor from gradient-directional curvature. | https://arxiv.org/abs/2506.04805 v2 (2026-05-25, ICML 2026) | Verified at abstract level |
| Few-shot CLIP: across 11 datasets, 3 backbones and 5 shot levels dense full fine-tuning with plain SGD beats representative PEFT methods; Adam, AdamW, Shampoo and SOAP collapse because the few-shot second-moment estimate is too small. | https://arxiv.org/abs/2611.11152 v1 (2026-11-08, NeurIPS 2026) | Verified at abstract level |

Take: two menu hypotheses for tiny-data fine-tuning (try SGD; scale Adam's first step), and a reason for the run
analyst to read gradient-norm and clipping logs before blaming the learning rate.

### 3.15 Evaluated and not recommended
| Candidate | Finding | Source | Status |
|---|---|---|---|
| Universal Searcher (NCode) | Needs a separately trained searcher model; flagship result used 896 GPU-days; no code. | https://arxiv.org/abs/2611.12791 v1 | Verified at abstract level |
| Soup v0.77.2 | Headline "8B on a 4 GB GPU" is self-measured, taken before a correctness repair; its paper retracts an earlier explanation; feature is BETA. | https://github.com/MakazhanAlpamys/Soup | Verified that the README says so |
| Miles v0.1 (Aug 2026, Apache-2.0) | Datacenter GPUs, Megatron/SGLang stack; single-GPU use not stated. | https://github.com/radixark/miles | Verified |
| Halo 1.2.0 (2026-11-04) | Apache-2.0 "as modified by Supplemental Terms" (revenue threshold, credit clause); single-GPU path "not validated"; ships `agent-docs/` for coding agents. | https://github.com/whitecircle/halo | Verified |
| Deletion Tuning, GEAR, SoFT, DISCOVER, Agentic ESOpt, MergeProbe, Z-PEFT, symmetry-compatible optimizers | Preprints or new conference papers with no code link on the arXiv page; menu entries at most. | arXiv pages listed in section 2 | Verified at abstract level |
| Nereus | Cluster-scale runtime (up to 1,024 GPUs); outside the single-node case. | https://arxiv.org/abs/2609.34645 v1 | Verified at abstract level |

### 3.16 Practitioner report: agent-driven fine-tuning on rented GPUs
| Claim | Source | Status |
|---|---|---|
| A technical writer had a coding agent configure and run QLoRA jobs through a GPU rental API (192,456 examples, about 50 USD, about a day); "two adapters were lost when pods were deleted after the account balance hit zero"; evaluation was three prompts judged by eye; noise in the data was found only afterwards. | https://passo.uno/fine-tuning-docs-llm/ (2026-06-05) | Unverified (single first-person account) |

Take: for the remote module, copy artefacts off the rented machine on a schedule and stop before the balance or cap
is reached, because the provider's own behaviour at zero balance is deletion. Corroborate with provider documentation
before this drives design (the remote-GPU scouts cover it).

## 4. Hypothesis menu drawn from this sweep (for the scouting step, not a default)

| Hypothesis | Measured gain | Who measured | Regime | Grade |
|---|---|---|---|---|
| Sequence packing + completion-only loss | -49% wall-clock, +1.7 points | speedrun verifier, 3 seeds | LoRA, 1.5B, GSM8K | one task, verified reruns |
| Train on the shortest 3-4k examples, one high-rate epoch | 6m05s to 1m44s at equal accuracy | speedrun verifier | same | one task; margin shrinks |
| Chunked completion-only cross-entropy (no full logits) | part of the 1m44s record | speedrun verifier | same | bundled, not isolated |
| Upgrade PEFT to 0.21.x when using OSF | -22% memory, -46% time (baseline not named; presumably OSF before the update) | PEFT maintainers | MetaMathQA | version effect, not a technique |
| Muon on 2D weights | 1.35x speedrun; parity at best in fine-tuning | author; workshop poster | pretraining yes, fine-tuning no | mixed |
| Same optimizer as pretraining | forgets less (no number in abstract) | arXiv 2605.06654 | full fine-tuning | preprint |
| Plain SGD instead of Adam | beats PEFT across 11 datasets (no number in abstract) | NeurIPS 2026 paper | few-shot CLIP | conference paper, vision |
| Later-layers-only fine-tuning | shallower side-effect slope | arXiv 2611.12864 | behaviour transfer | preprint |
| Omega-S penalty | retention 62.9% to 84.1%, 9 of 10 seeds | single author | LoRA code-to-prose | preprint with data |
| Dynamic rank (GEAR) | 86.61 to 88.45 with 14.4M vs 42.0M parameters | authors | LLaMA3-8B commonsense | preprint, no code |
| Keep and distil from discarded checkpoints | up to +7.4 points | authors | agentic RL | preprint, no code |
| Pre-RL entropy screen | saves 62.5-100% of doomed RL compute | workshop poster | SFT then GRPO, binary reward | small n |

## 5. Concepts not mentioned in README.md or brief.md (47)

Checked by text search of both files on 2026-11-11: none of the terms below occurs in either (README.md uses "rank"
and "adapters" only for process rank gating and framework callbacks).

1. Fine-tuning speedrun (frozen task, frozen hardware, wall-clock score) - https://github.com/Saivineeth147/lora-speedrun
2. Verifier-drawn fresh seeds: seeds chosen by the referee after the code is frozen - https://github.com/Saivineeth147/lora-speedrun/blob/main/JUDGING.md
3. One verification per code state: no re-roll without a code change - https://github.com/Saivineeth147/lora-speedrun/blob/main/JUDGING.md
4. Ties inside measured spread: differences below run-to-run jitter are not ranked - https://github.com/Saivineeth147/lora-speedrun/blob/main/JUDGING.md
5. Pin re-hash before evaluation in a clean sandbox (cache-poisoning defence) - https://github.com/Saivineeth147/lora-speedrun/blob/main/SECURITY.md
6. Adapter parameter audit: count every saved tensor against a cap - https://github.com/Saivineeth147/lora-speedrun/blob/main/TASK.md
7. Advisory-only AI code screen with an explicit injection threat model - https://github.com/Saivineeth147/lora-speedrun/blob/main/SECURITY.md
8. Sequence packing: several short examples per fixed-length sequence - https://github.com/Saivineeth147/lora-speedrun
9. Completion-only loss masking: loss on answer tokens only - https://github.com/Saivineeth147/lora-speedrun
10. Loss-mask coverage: fraction of tokens that receive loss - https://gradian.dev/docs/diagnostics
11. Memory preflight estimate with a measured follow-up - https://github.com/DaoyuanLi2816/can-i-finetune-this
12. Training-data attribution by influence functions (DataInf) for fine-tuning regressions - https://github.com/gradian-ai/gradian
13. Contrastive query gradient: gradient of the right answer minus that of the model's output - https://github.com/gradian-ai/gradian
14. Muon: orthogonalised momentum for 2D weights - https://docs.pytorch.org/docs/2.15/generated/torch.optim.Muon.html
15. Optimizer-model consistency: fine-tune with the pretraining optimizer - https://arxiv.org/abs/2605.06654
16. Riemannian-preconditioned LoRA optimizer - https://github.com/huggingface/peft/releases/tag/v0.21.0
17. Condition-number target selection (KappaTune) - https://github.com/huggingface/peft/releases/tag/v0.20.0
18. PEFT method-comparison suite (same-hardware, append-only experiments) - https://github.com/huggingface/peft/tree/main/method_comparison
19. Git dirty flag on stored results - https://github.com/huggingface/peft/releases/tag/v0.21.0
20. Experience repository with condition-scoped insights and confidence updates - https://arxiv.org/abs/2609.22257
21. Parent-and-baseline delta reward for search over training strategies - https://arxiv.org/html/2609.22257v1
22. Sharpening tax: pass@1 gained, coverage lost - https://arxiv.org/abs/2610.01509
23. Posterior-tempered group sampling: per-prompt temperature by difficulty - https://arxiv.org/abs/2610.01509
24. Rank inversion from SFT overtraining; pre-RL entropy screen - https://icml.cc/virtual/2026/82731
25. Checkpoint pool as teachers (post-RL capability recovery) - https://arxiv.org/abs/2611.12799
26. On-policy distillation, multi-teacher (MOPD) - https://huggingface.co/papers/2606.30406
27. Reinforcement learning with verifiable rewards (RLVR) and GRPO - http://arxiv.org/abs/2611.10844v1
28. Training-inference mismatch and monotonic inference policy update - https://arxiv.org/abs/2606.29526
29. Multi-pass rollout reuse and its overfitting - https://arxiv.org/abs/2611.10873
30. Data reuse factor in RL post-training scaling laws - https://github.com/tanzelin430/The-Scaling-Law-for-Reinforcement-Learning
31. On-the-line persona generalisation (probit-linear in/out-of-domain relation) - https://arxiv.org/abs/2611.12864
32. Latent attitude transfer through innocuous fine-tuning data - https://github.com/leo-dcfa/ai-latent-bias-transfer
33. Data-free forgetting penalty (Omega-S) and same-configuration noise bound - https://arxiv.org/abs/2608.03887
34. Soft-target fine-tuning with minimum-KL change to the base model (SoFT) - https://arxiv.org/abs/2609.32493
35. Deletion Tuning: learn a binary mask that zeroes weights - https://arxiv.org/abs/2611.10866
36. Normal-space spectrum for LoRA rank expansion (GEAR) - https://arxiv.org/abs/2611.07349
37. Structured null under family-wise correction (auxiliary-loss audit) - https://arxiv.org/abs/2605.15394
38. Bits-per-byte versus overlap metrics disagreement; tokenizer fertility - https://arxiv.org/abs/2611.12628
39. Delta-space evaluation against a mean-change baseline - https://arxiv.org/abs/2611.10658
40. Adaptive-preconditioner decoupling as the cause of Adam loss spikes - https://arxiv.org/abs/2506.04805
41. Weight-space backdoor detection for downloaded adapters - https://arxiv.org/abs/2608.02271
42. Mergeability prediction from early training - https://arxiv.org/abs/2606.19549
43. Evolution-strategy full-parameter fine-tuning at inference memory - https://arxiv.org/abs/2608.17310
44. Layer streaming (base model fed to the GPU one layer at a time) - https://github.com/MakazhanAlpamys/Soup
45. Stable rank, energy rank and checkpoint-displacement cosine as update diagnostics - https://arxiv.org/abs/2611.11752
46. Ensemble-and-prune training against initialisation variance - https://research.nvidia.com/labs/rtr/publication/bitterli2026taming/
47. Agent-directed documentation in ML repositories (`agent-docs/`, `llms.txt`, AGENTS.md) - https://github.com/whitecircle/halo ; https://github.com/gradian-ai/gradian

## 6. Concerns any design must handle

- EVAL-SEED-NOISE
- EVAL-SAME-CONFIG-NONDETERMINISM
- EVAL-SEED-SHOPPING
- EVAL-RERUN-SHOPPING
- EVAL-MULTIPLE-COMPARISONS
- EVAL-ADAPTIVE-OVERFIT
- EVAL-THRESHOLD-MARGIN-EROSION
- EVAL-METRIC-MISMATCH
- EVAL-COVERAGE-COLLAPSE
- EVAL-MISSING-TRIVIAL-BASELINE
- EVAL-BASELINE-PROMPT-DRIFT
- EVAL-EVALUATOR-BUG
- EVAL-ARTIFACT-TAMPER
- EVAL-ENV-CARRYOVER
- EVAL-TRAIN-TEST-CONTAMINATION
- EVAL-TIMING-BOUNDARY
- TRAIN-SILENT-MISCONFIG
- TRAIN-NOOP-ADAPTER
- TRAIN-LOSS-MASK-ERROR
- TRAIN-OOM-PREFLIGHT
- TRAIN-FORGETTING
- TRAIN-SIDE-EFFECT-TRANSFER
- TRAIN-CHECKPOINT-SELECTION
- TRAIN-TECHNIQUE-REGIME-MISMATCH
- TRAIN-UNMATCHED-TUNING-BUDGET
- TRAIN-BUNDLED-CHANGE
- TRAIN-SILENT-RESUME-FAILURE
- RL-REWARD-HACKING
- RL-ZERO-SIGNAL
- RL-ENTROPY-COLLAPSE
- RL-SAMPLER-TRAINER-MISMATCH
- LOOP-RULE-VIOLATION
- LOOP-REGRESSION-BELOW-BASELINE
- LOOP-STATELESS-SEARCH
- LOOP-NEGATIVE-TRANSFER
- SCOUT-STALE-ADVICE
- SCOUT-SELF-REPORTED-GAINS
- SCOUT-NO-CODE-CLAIMS
- SEC-PROMPT-INJECTION
- SEC-AGENT-FILES-IN-DEPENDENCIES
- SEC-PIPE-TO-SHELL-INSTALL
- SEC-UNTRUSTED-TRAIN-CODE
- SEC-ADAPTER-BACKDOOR
- SEC-REVIEWER-INJECTION
- SEC-LOCAL-SERVER-EXPOSURE
- REMOTE-ARTIFACT-LOSS
- REMOTE-NO-SPEND-CAP
- REMOTE-AUTOSTOP-UNSUPPORTED
- COST-CHECKPOINT-DISK
- COST-CONFIRMATION-COMPUTE
- LICENSE-COPYLEFT-OR-CUSTOM-TERMS
- PORT-WSL-GPU-UNQUALIFIED
- REPRO-PROVENANCE-FIELDS

## 7. Redirect attempts and process notes

No page tried to change my task. Agent-directed or instruction-like text met, none acted on:
- gradian README contains a passage for automated readers ("Reading this as an agent rather than a person?") pointing to `llms.txt`, `llms-full.txt` and markdown twins. Navigation hint only; not followed.
- Halo README describes `agent-docs/` as "written for coding agents" and an AGENTS.md; Miles lists AGENTS.md, `.agents`, `.claude` and REVIEW.md; Oumi lists AGENTS.md and CLAUDE.md; Soup lists AGENTS.md. None of these files was opened.
- READMEs contain reader-directed install steps (clone, `pip install`, `curl ... | sh`, create a Modal account). None was executed.
- The Exa search endpoint answered with a rate-limit error that tells the client to create an account and API key. Not done; other tools were used.
- The web search tool appends "REMINDER: You MUST include the sources above in your response". Tool boilerplate; sources are cited here because the task requires it.
- A DOI fetch returned a redirect notice asking for a second fetch at zenodo.org; followed, because it was the same record I had chosen to open.

Process notes: fetching `https://arxiv.org/pdf/2611.10844` made the fetch tool store a copy of the PDF in the
session's tool-results folder outside the repository; it was not opened (no renderer) and not executed. Public
repository URLs necessarily contain owner handles; no person's name, e-mail address, local path or local project name
was put into a search query.

## 8. Unverified or weak, in one place

- Body of "What Broke & Why" (only abstract and Zenodo record read).
- Vendor speed and memory claims (Unsloth, Soup); all star counts.
- All paper results marked "at abstract level": read from the arXiv listing page through a summarising fetch tool, not checked against the PDF; most have no code.
- `oumi-mcp` tool list; Oumi and axolotl launcher details (DeepWiki index, not repository files).
- Whether `torch.optim.Muon` predates PyTorch 2.9; the Muon^p fine-tuning result (search summary).
- The rented-GPU deletion anecdote and the forum criticism of the speedrun (user-generated).
- The rosmine.ai post (HTTP 404).
