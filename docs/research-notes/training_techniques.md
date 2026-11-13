# PyTorch training & fine-tuning: state of practice (as of 23 Oct 2026)

## 1. PyTorch core: versions, Muon, compile, FSDP2, DCP, torchao, torchdata, determinism, profiling, torchtune

### Takeaway
The latest stable release is PyTorch 2.14.1 (30 Sep 2026). 2.15 GA is planned for 28 Oct 2026 and requires Python ≥3.11. `torch.optim.Muon` has shipped since 2.9 (Oct 2025) and accepts only 2D parameters; support for FSDP2/DTensor-sharded parameters is unconfirmed. FSDP2 plus DCP (async save) is the native distributed default. torchtune is unmaintained, and PyTorch is consolidating its LLM training in torchtitan.

### Cited Findings
**Versions**
- torch 2.14.1 was released on PyPI 30 Sep 2026 — [PyPI](https://pypi.org/project/torch/). 2.14.0 GA was announced 2 Sep 2026 — [dev-discuss](https://dev-discuss.pytorch.org/t/pytorch-2-14-0-general-availability/3431).
- 2.15: RC1 on 8 Oct and GA planned for 28 Oct 2026 — [key dates](https://dev-discuss.pytorch.org/t/pytorch-release-2-15-key-dates/3434), [RC1](https://dev-discuss.pytorch.org/t/pytorch-2-15-rc1-produced-for-pytorch-torchvision-torchaudio/3464). "From 2.15, the minimum supported Python is 3.11" — [notice](https://dev-discuss.pytorch.org/t/notice-python-3-10-support-is-being-removed-from-pytorch-2-15-2-14-is-the-last-release-with-3-10-wheels/3440).
- Releases since 2.9.0 (15 Oct 2025, [GA](https://dev-discuss.pytorch.org/t/pytorch-2-9-0-general-availability/3251.md)) have come roughly every two months — [releases](https://github.com/pytorch/pytorch/releases).
- 2.14 ships wheels for CUDA 12.6, 13.0 and 13.2, with 13.0 the default. It supports Python 3.10–3.15, but `torch.compile` raises on 3.15. Most features are tagged "API Unstable" — [2.14 blog](https://pytorch.org/blog/pytorch-2-14-release-blog/).

**Optimizers**
- The 2.9.0 notes say: "Introduce Muon optimizer to PyTorch" — [notes](https://newreleases.io/project/pypi/torch/release/2.9.0).
- 2.14 API — [2.14 docs](https://docs.pytorch.org/docs/2.14/generated/torch.optim.Muon.html):
  - Signature: `Muon(params, lr=1e-3, weight_decay=0.1, momentum=0.95, nesterov=True, ns_steps=5, adjust_lr_fn=None)`.
  - Scope: "for 2D parameters of neural network hidden layers. Other parameters, such as bias, and embedding, should be optimized by a standard method such as AdamW."
  - `"match_rms_adamw"` scales by 0.2·√max(A,B), which lets you "directly reuse the learning rate and weight decay tuned for AdamW."
- `"spectral_unclamped"` is new in 2.14; the 2.13 docs list only two options — [2.13 docs](https://docs.pytorch.org/docs/2.13/generated/torch.optim.Muon.html).
- From the source: non-2D parameters raise `ValueError`. Complex parameters, sparse gradients, `foreach` and `fused` are not supported — [_muon.py](https://raw.githubusercontent.com/pytorch/pytorch/main/torch/optim/_muon.py).
- Distributed use: a torchtitan issue says `torch.optim.Muon` in 2.9 "does not support distributed training." The PyTorch tracking issue shows FSDP2 support as planned but not confirmed merged — [torchtitan#2494](https://github.com/pytorch/torchtitan/issues/2494), [pytorch#148819](https://github.com/pytorch/pytorch/issues/148819).
- Other `torch.optim` details — [optim docs](https://raw.githubusercontent.com/pytorch/pytorch/main/docs/source/optim.md):
  - Classes include Adafactor, NAdam and RAdam, among others.
  - There is no WSD scheduler; compose one from LinearLR, ConstantLR and SequentialLR.
  - The default implementation is foreach. The docs say "fused > foreach > for-loop," but fused is not the default.
  - EMA is available through `AveragedModel` plus `get_ema_multi_avg_fn`.

**torch.compile**
- Caveats — [troubleshooting](https://docs.pytorch.org/docs/main/user_guide/torch_compiler/torch.compiler_troubleshooting.html):
  - Graph breaks come from data-dependent control flow and `.item()`.
  - A guard failure triggers a recompile; past `recompile_limit` the function runs eagerly.
  - Wrap scalar LRs in tensors to avoid recompiles.
  - A cold compile takes seconds to minutes.
  - Debug with `TORCH_TRACE` plus `tlparse`, or `TORCH_LOGS=graph_breaks,recompiles`, and ablate backends in the order eager, aot_eager, inductor.
- 2.13 added `nn.LinearCrossEntropyLoss`, which cuts peak memory up to 4x — [releases](https://github.com/pytorch/pytorch/releases).

**FSDP2 and DCP**
- FSDP2 — [fully_shard docs](https://raw.githubusercontent.com/pytorch/pytorch/main/docs/source/distributed.fsdp.fully_shard.md):
  - "If you are currently using FSDP1, consider migrating to FSDP2." I found no FSDP1 deprecation notice.
  - Each parameter is sharded on dim 0 as a DTensor.
  - There is no direct full state dict; use `full_tensor()` or DCP.
  - Apply `fully_shard` bottom-up and build the optimizer afterward.
- Accelerate still defaults to `fsdp_version=1` — [Accelerate](https://huggingface.co/docs/accelerate/concept_guides/fsdp1_vs_fsdp2).
- DCP provides `save`, `load` and `async_save` with load-time resharding. It also has `get_state_dict`/`set_state_dict` (experimental), the `Stateful` protocol, `dcp_to_torch_save`, and `HuggingFaceStorageReader`/`Writer` for safetensors — [DCP docs](https://raw.githubusercontent.com/pytorch/pytorch/main/docs/source/distributed.checkpoint.md).
- Async recipe — [recipe](https://docs.pytorch.org/tutorials/recipes/distributed_async_checkpoint_recipe.html):
  - Keep one save in flight at a time.
  - `FileSystemWriter(cache_staged_state_dict=True)` keeps a pinned buffer.
  - `DefaultStager` arrived in 2.9.
  - Expect about one checkpoint's worth of CPU RAM per rank.

**torchao and torchdata**
- torchao 0.18.0 (3 Aug 2026) needs torch ≥2.11 and adds an NVFP4 training prototype — [releases](https://github.com/pytorch/ao/releases).
- torchao features — [PyPI](https://pypi.org/project/torchao/):
  - Float8 via `convert_to_float8_training`: up to 1.5x at 512 GPUs.
  - MXFP8: about 1.28x on B200.
  - `AdamW8bit`, `AdamW4bit` and `AdamWFp8` cut optimizer state 2–4x.
  - `CPUOffloadOptimizer` can "reduce your VRAM requirements by 60%."
- torchdata's latest is still 0.11.0 (20 Feb 2025). `StatefulDataLoader` is a drop-in DataLoader with `state_dict`, labelled Beta — [PyPI](https://pypi.org/project/torchdata/), [repo](https://github.com/meta-pytorch/data).

**Determinism and profiling**
- Determinism steps — [2.14 notes](https://docs.pytorch.org/docs/2.14/notes/randomness.html):
  - Seed torch, random and numpy.
  - Call `use_deterministic_algorithms(True)` and set `cudnn.benchmark=False`.
  - Give the DataLoader a `seed_worker` and a seeded `generator`.
  - The notes warn: "Completely reproducible results are not guaranteed across PyTorch releases," nor between CPU and GPU.
- On CUDA ≥10.2, set `CUBLAS_WORKSPACE_CONFIG=:4096:8` (or `:16:8`) — [docs](https://docs.pytorch.org/docs/2.2/generated/torch.use_deterministic_algorithms.html).
- Memory snapshots: call `torch.cuda.memory._record_memory_history()`, then `_dump_snapshot()`, then open the file in pytorch.org/memory_viz. It runs locally and shows the Active Memory Timeline and Allocator State History. NCCL allocations are invisible — [docs](https://raw.githubusercontent.com/pytorch/pytorch/main/docs/source/torch_cuda_memory.md).
- HTA 0.5.0 (29 May 2025) is not archived. It covers idle and kernel breakdowns, communication/compute overlap and trace diff — [PyPI](https://pypi.org/project/HolisticTraceAnalysis/), [repo](https://github.com/facebookresearch/HolisticTraceAnalysis).

**torchtune and torchtitan**
- The torchtune README says: "Torchtune is no longer actively maintained: torchtune development wound down in 2025." Its last release is 0.6.1 (7 Apr 2025) — [repo](https://github.com/meta-pytorch/torchtune), [PyPI](https://pypi.org/project/torchtune/).
- The successor, torchforge, says: "Development in Forge has paused. LLM training at PyTorch is being consolidated in torchtitan" — [torchforge](https://github.com/meta-pytorch/torchforge).
- torchtitan 0.3.0 (3 Sep 2026) supports FSDP2, TP, PP, CP, Float8/MXFP8, async checkpointing, compile and TorchFT — [PyPI](https://pypi.org/project/torchtitan/).

### Inferences
- Pin torch 2.14.x with cu130; moving to 2.15 means Python ≥3.11.
- Use `torch.optim.Muon` on a single GPU or with DDP; under FSDP2, use microsoft/dion (§2).
- Don't use torchtune for new work.

### Gaps
- I didn't retrieve the full 2.14 release notes on FSDP2 and DCP changes.

## 2. Optimizers and schedules: evidence

### Takeaway
Under equal, careful tuning, matrix optimizers (Muon, SOAP, Kron, Shampoo) beat AdamW by about 1.1–1.4x, and the gain shrinks with scale (about 1.1x at 1.2B). Moonlight's "~2x" comes from scaling-law fits, and Moonlight still uses AdamW for embeddings, the LM head and norms. The default stays AdamW/NAdamW with tuned LR and weight decay and decay to about zero. WSD's practical value is branching several decays off one stable run.

### Cited Findings
**Muon**
- Keller Jordan (8 Dec 2024) — [post](https://kellerjordan.github.io/posts/muon/):
  - Muon orthogonalizes the momentum update with Newton-Schulz, for 2D hidden weights only.
  - Embeddings, the head and scalar parameters go to AdamW.
  - It gave a 1.35x speedup on the NanoGPT speedrun.
  - Scale and fine-tuning were left as open questions.
- Moonlight (Feb 2025) — [abs](https://arxiv.org/abs/2502.16982), [html](https://arxiv.org/html/2502.16982):
  - Scaling Muon needed weight decay plus a 0.2·√max(A,B) update scale.
  - It "only requires about 52% training FLOPs" of AdamW, based on fits to dense models of 399M–1.5B.
  - Moonlight itself is a 3B/16B MoE trained on 5.7T tokens.
  - "AdamW is used ... to handle non-matrix based parameters, like RMSNorm, LM head, and embedding parameters."
- Optimizer mismatch — [pdf](https://arxiv.org/pdf/2502.16982):
  - A Muon-pretrained model fine-tuned with Muon scored best (GSM8K 68.0, vs 62.1 with AdamW fine-tuning).
  - Muon fine-tuning of AdamW-pretrained Qwen2.5-7B was no better (GSM8K 85.8 vs 89.8).
- Kimi K2: a 1T/32B MoE trained on 15.5T tokens with MuonClip, with "zero loss spike" — [arXiv](https://arxiv.org/abs/2507.20534).
- 2026 skepticism:
  - In agentic RL, Muon's gain disappears when update RMS is matched; the authors call it a "recipe-level operating regime" — [2607.16169](https://arxiv.org/abs/2607.16169).
  - On matrix factorization, Muon doesn't consistently beat a tuned AdamW — [2607.13246](https://arxiv.org/abs/2607.13246).

**Fair comparisons**
- Wen et al. (Sep 2025; 11 optimizers, 130M–1.2B, 1–8x Chinchilla) — [abs](https://arxiv.org/abs/2509.02046), [html](https://arxiv.org/html/2509.02046):
  - Speedup falls from 1.4x at 0.1B to about 1.1x at 1.2B. Scalar methods stay under 1.2x.
  - Muon is best at 1x Chinchilla; SOAP and Kron lead at 8x.
  - Retuning only the LR of the GPT-3 recipe gives about 2x, so weak baselines inflate claims.
  - The best weight decay differs by optimizer: AdamW about 0.1, Lion about 0.6.
  - Loss curves cross during the decay phase, so compare final checkpoints.
- Semenov et al. (Sep 2025; 124M–720M plus a MoE, about 2,900 runs) — [html](https://arxiv.org/html/2509.01440):
  - AdEMAMix was the most consistent.
  - D-Muon (weight decay on all parameters) clearly beat basic Muon.
  - Lion, Signum and MARS are sensitive to batch size; Schedule-Free AdamW is weak at small batch.
  - β2=0.999 beat 0.95, and they decay to 0.01× peak LR.
- AlgoPerf (ICLR 2025): Distributed Shampoo won external tuning, about 28% faster than NAdamW. Schedule-Free AdamW won self-tuning, about 8% over its baseline. No submission hit every target — [html](https://arxiv.org/html/2502.15015), [ICLR](https://proceedings.iclr.cc/paper_files/paper/2025/hash/6bdde0373d53d4a501249547084bed43-Abstract-Conference.html).
- Authors' own claims:
  - SOAP: over 40% fewer iterations and over 35% less wall-clock than AdamW at 360M/660M, large batch — [arXiv](https://arxiv.org/abs/2409.11321).
  - AdEMAMix: 1.3B on 101B tokens matches AdamW on 197B — [arXiv](https://arxiv.org/abs/2409.03137).
- Dion uses power iteration so it works with sharded weights — [arXiv](https://arxiv.org/abs/2504.05295). Dion3 (Aug 2026) matches or beats Muon's loss with up to a 6x faster step — [arXiv](https://arxiv.org/abs/2608.11612). microsoft/dion ships Muon, NorMuon and Dion2/3 for FSDP2. Its README warns that embeddings give "poor performance" under Dion and that the LM head needs its own AdamW group — [repo](https://github.com/microsoft/dion).

**Schedules**
- MiniCPM introduced WSD for continual training and cheaper scaling-law studies — [arXiv](https://arxiv.org/abs/2404.06395).
- Hägele et al. — [html](https://arxiv.org/html/2405.18392):
  - Constant LR plus a cooldown matches cosine.
  - The cooldown benefit plateaus at about 20% of steps; 5% is often enough for long runs.
  - A 1-sqrt cooldown beats linear.
  - SWA helps but doesn't replace the cooldown.
  - Branching cooldowns off one run roughly halved the compute of a scaling sweep.
- "Straight to Zero" — [arXiv](https://arxiv.org/abs/2502.15938):
  - Linear decay to zero beats cosine decay to 10% of peak.
  - A 610M model at 80 tokens/param with decay to zero beat one at 200 tokens/param with the 10x schedule, about 60% compute saved.
  - The gain grows with tokens per parameter.
- Schedule-Free caveats — [repo](https://github.com/facebookresearch/schedule_free):
  - Call `optimizer.train()`/`eval()` alongside the model, and switch to eval before checkpointing.
  - BatchNorm needs recalibration.
  - Warmup is still recommended.
  - The LR should be 1–10x AdamW's; β defaults to 0.9, with 0.95–0.98 for long runs.
- In Hägele et al., a cooldown matched or beat Schedule-Free — [html](https://arxiv.org/html/2405.18392).
- HF `get_wsd_schedule` supports linear, cosine and 1-sqrt decay plus `min_lr_ratio` — [docs](https://huggingface.co/docs/transformers/main_classes/optimizer_schedules).

### Inferences
- Default baseline: AdamW with weight decay about 0.1, warmup and a tuned LR. For a fixed budget, decay linearly to about zero. For a variable budget or continued training, use WSD with a 10–20% 1-sqrt or linear cooldown branched off the stable checkpoint.
- Controlled alternative: Muon.
  - Apply it to hidden 2D matrices, with AdamW for embeddings, the head, norms and biases.
  - Use `match_rms_adamw` and weight decay on all groups.
  - Expect at most 1.1–1.4x.
  - Don't switch optimizers when fine-tuning an AdamW checkpoint.
- Other alternatives: SOAP/Shampoo, Schedule-Free (when the training length is unknown), AdEMAMix (long runs).
- Comparison protocol: equal tuning budget per optimizer, final checkpoints only, at least two scales.

### Gaps
- I found no results from a later AlgoPerf round, and no independent Muon-vs-AdamW comparison above 3B.

## 3. Hyperparameter transfer (μP, u-μP, CompleteP)

### Takeaway
μP transfers hyperparameters across width. CompleteP adds depth, and Complete(d)P (ICLR 2026) adds batch size, duration and per-module hyperparameters. Tooling is thin: microsoft/mup was archived in Sep 2026. Transfer pays off for from-scratch pretraining across a large scale-up, not for fine-tuning.

### Cited Findings
- microsoft/mup was archived 21 Sep 2026. It provides `MuReadout`, `set_base_shapes`, `MuAdam` and coordinate checks. Its README advises a zero-init readout and 1/d attention — [repo](https://github.com/microsoft/mup).
- Cerebras guide: use a proxy width of 256 at the target depth, trained at about 20 tokens/param. Random-search 4 hyperparameters with batch at or above the critical size, and run a coordinate check first. It cites 3.3x fewer FLOPs at 3B — [guide](https://cerebras.ai/blog/the-practitioners-guide-to-the-maximal-update-parameterization).
- u-μP combines μP with unit scaling, giving near-optimal defaults and FP8 out of the box — [arXiv](https://arxiv.org/abs/2407.17465). The `unit-scaling` library is labelled "beta" — [repo](https://github.com/graphcore-research/unit-scaling).
- CompleteP transfers across depth and width, with a 12–34% compute-efficiency gain over the prior state of the art. The reference is the EleutherAI nanoGPT-mup `completep` branch — [arXiv](https://arxiv.org/abs/2505.01618).
- Complete(d)P: per-module hyperparameters tuned at about 50M parameters and 1.6B tokens transfer to a FLOP budget about 14,000x larger. At 50M, a single global setting needs about 2.3x longer training to match — [Apple](https://machinelearning.apple.com/research/completed-hyperparameter).
- Everett et al.: all four parameterizations they tested can transfer with the right per-layer LRs. Adam ε must scale with the model; Adam-atan2 removes it — [arXiv](https://arxiv.org/abs/2407.05872).

### Inferences
- Default: standard parameterization with an LR sweep. Use μP or CompleteP as a controlled alternative when scaling a model family, and always run a coordinate check.

### Gaps
- I found no maintained general-purpose μP library for 2026.

## 4. LLM fine-tuning stack and evaluation harnesses

### Takeaway
The HF stack is current and fast-moving, with Unsloth and Axolotl releasing monthly or more. lm-eval and inspect_ai are active; lighteval hasn't released since Nov 2025.

### Cited Findings
| Package | Latest | Date | Notes |
|---|---|---|---|
| [transformers](https://pypi.org/project/transformers/) | 5.20.2 | 19 Oct 2026 | v5.0.0 came out 26 Jan 2026 |
| [TRL](https://pypi.org/project/trl/) | 1.16.0 | 15 Oct 2026 | [1.0.0](https://pypi.org/project/trl/1.0.0/) came out 30 Mar 2026; Python ≥3.11; SFT, DPO, GRPO, KTO, Reward |
| [PEFT](https://pypi.org/project/peft/) | 0.21.2 | 1 Oct 2026 | |
| [Accelerate](https://pypi.org/project/accelerate/) | 1.15.0 | 9 Sep 2026 | |
| [Unsloth](https://pypi.org/project/unsloth/) | 2026.10.7 | 19 Oct 2026 | Claims "2× faster with 70% less VRAM" |
| [Axolotl](https://pypi.org/project/axolotl/) | 0.21.0 | 16 Oct 2026 | FSDP2, DeepSpeed, Ulysses/Ring sequence parallelism, GRPO, QAT |
| [LLaMA-Factory](https://pypi.org/project/llamafactory/) | 0.9.5 | 30 May 2026 | |
| [Liger Kernel](https://pypi.org/project/liger-kernel/) | 0.8.4 | 30 Sep 2026 | Claims +20% throughput and −60% memory, measured with FSDP1 on 8×A100 |
| [DeepSpeed](https://pypi.org/project/deepspeed/) | 0.19.7 | 16 Sep 2026 | |
| [lm-eval](https://pypi.org/project/lm-eval/) | 0.4.13 | 31 Aug 2026 | |
| [lighteval](https://pypi.org/project/lighteval/) | 0.13.0 | 24 Nov 2025 | |
| [inspect-ai](https://pypi.org/project/inspect-ai/) | 0.3.282 | 19 Oct 2026 | |

- PEFT — [guide](https://huggingface.co/docs/peft/developer_guides/lora):
  - DoRA supports only Linear and Conv2D and has a "bigger overhead," so merge it for inference.
  - rsLoRA scales by alpha/√r.
  - Alternative initializations: PiSSA, OLoRA, EVA, LoftQ, CorDA.
  - LoRA+ claims fine-tuning "up to 2x" faster.
  - `target_modules="all-linear"` gives QLoRA-style coverage.
- DeepSpeed vs FSDP: DeepSpeed can offload parameters and optimizer state separately, and to NVMe. But it upcasts to fp32 when preparing the model, which costs memory on small GPU counts, and consolidating ZeRO-3 to one rank is slow — [Accelerate](https://huggingface.co/docs/accelerate/concept_guides/fsdp_and_deepspeed).
- lm-eval: since Dec 2025 the CLI has subcommands and YAML configs, and backends are installed as extras (`lm_eval[hf]`, `[vllm]`). HF is the reference implementation — [repo](https://github.com/EleutherAI/lm-evaluation-harness).
- lighteval prefers the inspect-ai backend (`lighteval eval`) and lists 1000+ tasks — [repo](https://github.com/huggingface/lighteval).

### Inferences
- Default stack: TRL + PEFT + Accelerate with FSDP2. Unsloth is the speed option for single-GPU LoRA/QLoRA; Axolotl and LLaMA-Factory suit config-driven runs; Liger is the memory lever.
- Eval: lm-eval for log-likelihood benchmarks, inspect_ai for generative and agentic evals. Pin harness and task versions.

### Gaps
- The Unsloth, Liger and LoRA+ speed claims come from their authors.

## 5. Experimental-rigor references

### Takeaway
Hold the test set out. Tune nuisance hyperparameters equally for every arm and explore with quasi-random search. Compare arms on paired seeds using intervals and P(improvement), not single runs.

### Cited Findings
- Google tuning playbook — [repo](https://github.com/google-research/tuning_playbook):
  - Scientific hyperparameters are "those whose effect on the model's performance we're trying to measure." Nuisance hyperparameters are optimized "to fairly compare" them. Fixed hyperparameters are held constant.
  - "prefer to use quasi-random search in the exploration phase," and use Bayesian optimization for exploitation.
  - Batch size "should not be treated as a tunable hyperparameter for validation set performance."
  - The baseline "should also have its learning rate equally well tuned."
  - "The best checkpoint is often not the last checkpoint."
  - Adam tuning by budget: under 10 trials, LR only; 10–25 trials, add β1; over 25, add ε; well over 25, add β2.
  - Seed-to-seed spread was about ±0.1% on about 23% error, smaller than the gap between lucky and unlucky 20-trial studies.
- Bouthillier et al. (MLSys 2021) — [proceedings](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html), [pdf](https://arxiv.org/pdf/2103.03098):
  - Data sampling is the largest source of variance; hyperparameter choice is about as large as initialization.
  - "As many sources of variation as possible should be randomized."
  - Prefer out-of-bootstrap resampling over fixed test sets.
  - Test P(A>B) against γ=0.75 with about 29 paired runs.
  - Their biased estimator is 51x cheaper.
- Agarwal et al. (NeurIPS 2021 Outstanding Paper): use IQM, stratified-bootstrap CIs, performance profiles, P(improvement) and optimality gap. The rliable library was archived 15 Oct 2025 — [arXiv](https://arxiv.org/abs/2108.13264), [rliable](https://github.com/google-research/rliable).
- Dodge et al. (EMNLP-IJCNLP 2019): report expected validation performance as a function of the number of tuning trials, because rankings flip with budget — [arXiv](https://arxiv.org/abs/1909.03004), [ACL](https://aclanthology.org/D19-1224/).
- Henderson et al. (AAAI 2018): 10 same-hyperparameter TRPO runs split 5/5 differed significantly (p=0.0016). They recommend bootstrap CIs, power analysis, reporting all hyperparameters and releasing code — [pdf](https://arxiv.org/pdf/1709.06560).

### Inferences
- Agent protocol:
  - Select on validation only and evaluate on test once.
  - Pair arms on seeds and data order.
  - Screen with 3–5 seeds; for close calls, scale toward about 29 pairs.
  - Report a CI and P(improvement), or IQM across tasks.
  - Give each arm an equal tuning budget and compare final checkpoints.

### Gaps
- The playbook gives no general rule for seed count.

## 6. Environment management

### Takeaway
Use uv with an explicit PyTorch index and `uv sync --locked` in CI. Use pixi with conda-forge `pytorch-gpu` for stacks that need a conda-level CUDA toolchain. PyTorch's own conda channel is legacy.

### Cited Findings
- uv 0.13.5 was released 22 Oct 2026 — [PyPI](https://pypi.org/project/uv/).
- Lock and sync semantics — [sync](https://docs.astral.sh/uv/concepts/projects/sync/), [CLI](https://docs.astral.sh/uv/reference/cli/):
  - `uv lock --check` is equivalent to `--locked`.
  - `uv run` locks and syncs automatically.
  - `--locked`: "If the lockfile is missing or needs to be updated, uv will exit with an error."
  - `--frozen` skips the check.
  - `uv sync` is exact by default.
  - Export formats: requirements.txt, pylock.toml and CycloneDX.
- CI example: `uv sync --locked --all-extras --dev` with setup-uv v9.0.0 — [guide](https://docs.astral.sh/uv/guides/integration/github/).
- PyTorch index config — [uv PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/):
  - `[[tool.uv.index]] name="pytorch-cu130" url="https://download.pytorch.org/whl/cu130" explicit=true`
  - `[tool.uv.sources] torch=[{index="pytorch-cu130", marker="sys_platform == 'linux' or sys_platform == 'win32'"}]`
  - For CPU vs GPU builds, use extras plus `[tool.uv] conflicts`.
  - `--torch-backend=auto` works only in `uv pip`.
- pixi v0.81.0 was released 15 Sep 2026 — [releases](https://github.com/prefix-dev/pixi/releases).
- pixi PyTorch guidance — [docs](https://pixi.prefix.dev/latest/python/pytorch/):
  - conda-forge `pytorch-gpu` is recommended.
  - Declare CUDA per platform (`{ platform = "linux-64", cuda = "12.0" }`) or you get CPU builds.
  - `[system-requirements]` is deprecated.
  - The legacy `pytorch` channel conflicts with conda-forge.
  - Installing torch from PyPI forces its dependents onto PyPI.
- PyTorch stopped publishing conda packages that depend on Anaconda defaults, and conda nightlies ended 18 Nov 2024. The recommended route is pip wheels or conda-forge — [dev-discuss](https://dev-discuss.pytorch.org/t/pytorch-deprecation-of-conda-nightly-builds/2590).

### Inferences
- Commit `uv.lock` and pin `torch==2.14.*` from the cu130 index. Use `--locked` in CI and `--frozen` offline.

### Gaps
- I couldn't retrieve the exact `uv sync --locked` wording; the quoted text is from `uv run`.

## Unverified
- **Memory snapshot argument.** The 2.14 blog names `record_host=True`, while the main-branch docs use `record_pinned_host_memory=True`. I couldn't confirm `max_entries`.
- **TRL v1.0 details.** The stable-core vs `trl.experimental` split (e.g. ORPO) comes only from a secondary source, which is inconsistent on where KTO sits — [MarkTechPost](https://www.marktechpost.com/2026/04/01/hugging-face-releases-trl-v1-0-a-unified-post-training-stack-for-sft-reward-modeling-dpo-and-grpo-workflows/).
- **NCCL default.** The 2.14 blog says the new NCCL backend becomes the default "in 2.15+"; the 2.15 posts don't confirm it.
- **Muon on FSDP2.** I couldn't establish whether `torch.optim.Muon` supports DTensor/FSDP2 in 2.14 or 2.15.
- **Stale or odd sources.** PyPI lists lm-eval 0.5.0.dev1 dated 11 May 2026. LLaMA-Factory's GitHub page shows stale releases. The pixi docs have outdated Python 3.13 and cu124 notes.
- **Venues and details not confirmed from fetched pages.** Schedule-Free (reportedly a NeurIPS 2024 oral), Hägele et al., Moonlight, and the MiniCPM decay length.
