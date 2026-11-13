# Scout note: optimizers, schedules, scaling rules, performance, memory, multi-GPU

Date: 11 November 2026. Area: optimization and performance. Builds on `docs/research-notes/training_techniques.md` (23 Oct 2026) and `.claude/skills/nn-training/references/performance.md`.

Conventions. Each claim ends with `[status | source version or date | checked | URL]`. Status is Verified (read in a primary source), Inferred (my reasoning from verified facts, not tested) or Unverified. Nothing was installed or run. Numbers taken from long pages were extracted through a fetch summariser; re-read the table before quoting a number externally.

Limits of this pass. The shared web-search budget ran out before I finished. Not searched: fresh (2026) evidence on gradient clipping, initialization and normalization; RTX 50-series driver problems; the AlgoPerf rolling leaderboard after the v1 paper. The "awesome list" query family was covered only by direct look-ups of two optimizer collections. These gaps are repeated under Open questions.

## Summary (10 lines)

1. PyTorch 2.15.0 shipped on 28 Oct 2026, after the earlier note. Default wheels are CUDA 13.2 (`cu132`), `cu130` and `cu126` are no longer built, and CUDA 13 wheels need NVIDIA driver 580+. The kit's "2.14.x with cu130" pin is stale.
2. Native Windows was much slower than Linux before 2.15: the flash attention kernel was compiled out of Windows wheels, so grouped-query attention fell back to the math kernel (about 23x slower forward on an RTX 5090). The test machine's PyTorch 2.9 is affected.
3. `torch.compile` returned silently wrong gradients in 2.13 and 2.14 (dropout masks under compiled activation checkpointing, mixed-order reductions). `performance.md` has no compiled-versus-eager numerics check. On native Windows with CUDA, `torch.compile` still needs a community Triton build.
4. On native Windows the NVIDIA driver can spill into system memory instead of raising out-of-memory, so OOM ladders and batch-size finders never trigger and training just slows down. Under WSL2, `nvidia-smi` cannot report GPU utilization or compute processes, so the kit's `gpu_info` and "check utilization" advice fail there.
5. No optimizer has replaced a tuned AdamW or NAdamW baseline across domains. AlgoPerf v1 (9 Oct 2026, self-tuning rules) was won by Schedule-Free AdamW v2; an independent diffusion benchmark (Sep 2026) ranked Schedule-Free last.
6. For language-model pretraining, Muon and SOAP now have several sources: about 1.3x to 1.4x fewer steps when hyperparameters are scaled correctly, and vendor-reported gains up to a 72B mixture-of-experts model. Gains vanish under wrong scaling, and in some settings an update-size-matched AdamW removes them.
7. Scaling rules converged on one AdamW invariant: keep the weight-decay timescale `1/(lr*wd)` fixed in data terms. When batch size changes, retune weight decay (or scale both LR and WD by the square root of the factor), not LR alone. Longer runs want a shorter normalized timescale, and beta2 should keep a constant half-life in tokens.
8. Schedules: linear decay to zero and warmup-stable-decay with a square-root style cooldown both have support, and the best schedule changes with training length. Warmup stays. Schedule-free is a hypothesis to test.
9. Multi-process jobs break three controller assumptions. `torchrun` starts each rank in its own session, forwards the stop signal to each rank's whole process group (which kills DataLoader workers, the fault the kit already fixed for single-process runs), and gives ranks 30 s by default before SIGKILL.
10. Launchers differ in who the launched process is (`torchrun` and `accelerate launch` are supervisors; with Lightning Fabric the launched process is rank 0). The controller needs a cooperative stop path, launcher-aware grace, restart and port handling. Native Windows has no NCCL, so multi-GPU should be documented as Linux and WSL2 only.

## Q1. Re-check of `performance.md` and `training_techniques.md`

### `references/performance.md`

- Section 1 tells the agent to read GPU utilization with `nvidia-smi --query-gpu=utilization.gpu,...` or `dmon`. Under WSL2, NVIDIA states that GPU utilization and active compute process queries are not supported. The kit's `expctl.py gpu_info()` uses the same two query types. Missing: an in-process fallback (time waiting for data versus time in the step). [Verified | CUDA on WSL User Guide, current | checked 2026-11-11 | https://docs.nvidia.com/cuda/wsl-user-guide/]
- Section 2 has no platform notes. Missing for native Windows: system-memory fallback, attention kernel availability, Triton, spawn-based DataLoader workers, no NCCL. Missing for WSL2: telemetry gaps and the pinned-memory limit. Details in Q4 and Q5. [Verified | see Q4 sources | checked 2026-11-11]
- Mixed precision advice (bf16 autocast, no GradScaler) is still right. The API names should be `torch.amp.autocast("cuda", dtype=torch.bfloat16)` and `torch.amp.GradScaler("cuda")`; the `torch.cuda.amp.*` forms are deprecated. With `torch.compile`, the backward pass is traced under the forward's autocast state by default (`torch._functorch.config.backward_pass_autocast = "same_as_forward"`), which differs from the usual eager pattern. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/amp.html]
- `torch.set_float32_matmul_precision("high")` still works. A newer API exists since 2.9 (`torch.backends.fp32_precision`, per-backend variants); the old `allow_tf32` flags are announced for deprecation and must not be mixed with the new ones. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/notes/cuda.html]
- `torch.compile` advice lacks a numerics gate. Evidence: issue 198333 (2.13 and 2.14, label "correctness (silent)"): compiled dropout masks duplicated across channels; with activation checkpointing the forward and backward masks agreed about half the time, giving wrong gradients without an error. Disabled in 2.15 (PR 198680). 2.15 also fixed wrong gradients from mixed-order reductions and from reused nested compile regions. [Verified | PyTorch 2.13 to 2.15 | checked 2026-11-11 | https://github.com/pytorch/pytorch/issues/198333 and https://github.com/pytorch/pytorch/releases/tag/v2.15.0]
- `nn.LinearCrossEntropyLoss` is listed as a memory lever "(PyTorch 2.13+)". The class exists in the 2.15 docs; its chunked path does not support Inductor lowering, forward-mode or higher-order differentiation, and a second `backward()` needs `allow_retain_graph=True`. It is not available on the test machine's 2.9. The "2.13+" version comes from the earlier note; the doc page has no version note. [Verified for existence and limits, Unverified for "2.13+" | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/generated/torch.nn.LinearCrossEntropyLoss.html]
- torchao low-bit optimizers: the README states they require `torch.compile`. On native Windows that means the optional Triton build as well. `CPUOffloadOptimizer` does not work with built-in LR schedulers or gradient clipping. [Verified for the README, Inferred for Windows | torchao v0.18.0, 3 Aug 2026 | checked 2026-11-11 | https://github.com/pytorch/ao/blob/main/torchao/optim/README.md]
- Activation checkpointing: the docs now say `use_reentrant` "should be passed explicitly" and recommend `False`. If the recomputed forward differs from the first forward, the result can be "silently incorrect gradients". [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/checkpoint.html]
- Section 4 (OOM ladder) assumes an out-of-memory error is raised. On native Windows it may not be (Q4). The allocator variable is now `PYTORCH_ALLOC_CONF` (`PYTORCH_CUDA_ALLOC_CONF` is an alias). [Verified | PyTorch 2.15 docs and NVIDIA KB 5490 | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/notes/cuda.html]
- Section 3 (adoption rule: beat timing noise with two short runs each way and keep the primary metric within the noise floor) still holds. It should add the numerics check above for changes that alter the compute graph or precision. [Inferred | checked 2026-11-11]
- Memory-snapshot API names (`_record_memory_history`, `_dump_snapshot`) were not re-verified. [Unverified]

### `docs/research-notes/training_techniques.md`

- "Latest stable is 2.14.1, 2.15 planned for 28 Oct": 2.15.0 is released. [Verified | published 2026-10-28 | checked 2026-11-11 | https://github.com/pytorch/pytorch/releases/tag/v2.15.0]
- "No results from a later AlgoPerf round": the v1 results paper is dated 9 Oct 2026 and was missed. [Verified | arXiv 2610.13036v1 | checked 2026-11-11 | https://arxiv.org/abs/2610.13036]
- "No Muon versus AdamW comparison above 3B": one now exists at 8B to 72B (vendor-measured). [Verified | arXiv 2607.20548v1, 13 Jul 2026 | checked 2026-11-11 | https://arxiv.org/abs/2607.20548]
- "Muon gain shrinks to about 1.1x at larger scale": needs a qualifier. With correct width scaling of LR and weight decay the gain held at about 1.4x from 190M to 1.4B; it "vanishes rapidly with scale under incorrect scaling". [Verified | arXiv 2512.05620v2, 18 Jan 2026 | checked 2026-11-11 | https://arxiv.org/abs/2512.05620]
- "NCCL default in 2.15 (unverified)": resolved. The rewritten NCCL backend is the default in 2.15; the rollback switch `TORCH_DIST_USE_NCCL2=0` is announced for removal. [Verified | PyTorch 2.15.0 | checked 2026-11-11 | https://github.com/pytorch/pytorch/releases/tag/v2.15.0]
- "Pin torch 2.14.x with cu130": 2.15 does not build `cu130`; and 2.14.x carries the silent dropout bug when compile, dropout and checkpointing are combined. [Verified | PyTorch 2.15.0 | checked 2026-11-11 | same URL]
- "Accelerate still defaults to FSDP1": still true. [Verified | Accelerate docs main, v1.15.0 of 9 Sep 2026 | checked 2026-11-11 | https://huggingface.co/docs/accelerate/main/en/concept_guides/fsdp1_vs_fsdp2]
- "Muon with FSDP2" stays open: the 2.15 Muon page says nothing about sharded parameters. [Unverified | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/generated/torch.optim.Muon.html]

## Q2. Optimizers and schedules

### Benchmarks

- AlgoPerf v1, self-tuning rules only, 13 submissions, nine workloads including a new decoder-only language-model workload, 4xA100. Order as extracted: Schedule-Free AdamW v2 (PyTorch) 0.568, AdEMAMix configured as an AdamW equivalent 0.519, Schedule-Free AdamW 0.467, NAdamW baseline 0.451, Muon (PyTorch) 0.423, Cautious NAdamW 0.314, Lion 0.278, canonical AdEMAMix 0.246, single-worker DiLoCo 0.130. [Verified, numbers via summariser | arXiv 2610.13036v1, 9 Oct 2026 | checked 2026-11-11 | https://arxiv.org/abs/2610.13036]
- Same paper: Muon had the best per-workload (oracle) score but kept only 47% of it under one fixed configuration (NAdamW 65.5%). Both PyTorch Schedule-Free submissions missed the language-model target. Schedule-Free needed a batch-norm fix (recompute statistics at the averaged weights). The AdEMAMix entry that ranked second had effectively become a tuned AdamW. Learning rate and momentum were the most influential settings. [Verified | same source]
- The benchmark has moved to a rolling leaderboard. Current entries were not checked. [Verified for the move, Unverified for content | checked 2026-11-11 | https://github.com/mlcommons/algorithmic-efficiency]
- Diffusion: seven optimizers under one search protocol, winners retrained at full budget with three seeds. Tuned AdamW is a strong default; Schedule-Free was worst on all four tasks; Muon, MARS-M and SOAP each beat AdamW on at least one task; Lion diverged on one. [Verified | arXiv 2609.23055, 19 Sep 2026 | checked 2026-11-11 | https://arxiv.org/abs/2609.23055]
- Tabular MLPs: 15 optimizers on 17 datasets; Muon consistently beat AdamW at a compute overhead; a weight EMA helped AdamW. [Verified | arXiv 2604.15297, Apr 2026 | checked 2026-11-11 | https://arxiv.org/abs/2604.15297]
- Language-model pretraining benchmark with per-method tuning across model size, batch size and duration exists; I read only its abstract in this pass. [Verified for existence | arXiv 2509.01440v1, 1 Sep 2025 | checked 2026-11-11 | https://arxiv.org/abs/2509.01440]

### Muon, SOAP and successors (language models)

- NVIDIA trained 8B dense and 30B and 72B mixture-of-experts models on 1T to 3T tokens. SOAP and Muon "consistently outperform AdamW"; AdamW degraded at large batch; SOAP loss spikes came from a stale eigenbasis and were fixed by per-step updates; Muon used 16 Newton-Schulz iterations in bf16; one downstream regression is reported; convolution weights in a hybrid model did better with AdamW. Measured by the vendor, not by the optimizers' authors, and not reproduced elsewhere. [Verified | arXiv 2607.20548v1, 13 Jul 2026 | checked 2026-11-11 | https://arxiv.org/abs/2607.20548]
- Along the "overtraining" axis (1x to 256x tokens per parameter, 51M to 253M) Muon and SOAP kept a roughly constant token-efficiency edge; best weight decay grew about with the square root of overtraining; the preferred LR schedule can reverse along the axis. [Verified | arXiv 2609.04577v1, 4 Sep 2026 | checked 2026-11-11 | https://arxiv.org/abs/2609.04577]
- Counter-evidence: in agentic reinforcement learning an update-size (RMS) matched AdamW removed Muon's gain; a matrix-factorization reassessment found similar limits. [Verified | arXiv 2607.16169v4, 2 Aug 2026 and 2607.13246v2, 1 Aug 2026 | checked 2026-11-11 | https://arxiv.org/abs/2607.16169 and https://arxiv.org/abs/2607.13246]
- `torch.optim.Muon` in 2.15: `Muon(params, lr=0.001, weight_decay=0.1, momentum=0.95, nesterov=True, ns_coefficients=(3.4445, -4.775, 2.0315), eps=1e-07, ns_steps=5, adjust_lr_fn=None)`; 2-D parameters only; `adjust_lr_fn` accepts "original", "match_rms_adamw", "spectral_unclamped". [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/generated/torch.optim.Muon.html]
- 2.15 fixed a Muon bug where bf16 gradients aliased the momentum buffer (PR 194664). Versions before 2.15, including 2.9, are affected when parameters (and so gradients) are bf16; fp32 parameters under autocast should not be. [Verified for the fix, Inferred for the scope | PyTorch 2.15.0 | checked 2026-11-11 | https://github.com/pytorch/pytorch/releases/tag/v2.15.0]
- Dion3 reports matching or better loss than Muon with up to 6x lower optimizer step time in distributed settings; single source (authors). SAMuon reports 13% to 24% fewer tokens than Muon; single source. [Verified for the claims, not independently confirmed | arXiv 2608.11612, 12 Aug 2026; arXiv 2608.25990 | checked 2026-11-11 | https://arxiv.org/abs/2608.11612]
- Implementations: NVIDIA Emerging-Optimizers v0.5.0 (10 Nov 2026, Apache-2.0, "All APIs are experimental", install from source, Python 3.12+); pytorch_optimizer v4.1.0 (25 Oct 2026); HeavyBall v3.2.1 (29 Aug 2026); `schedulefree` 1.4.1 on PyPI (24 Mar 2025, Apache-2.0). [Verified | checked 2026-11-11 | https://github.com/NVIDIA-NeMo/Emerging-Optimizers, https://github.com/kozistr/pytorch_optimizer/releases, https://github.com/HomebrewML/HeavyBall/releases, https://pypi.org/project/schedulefree/]

### AdamW tuning

- Setting beta1 equal to beta2 keeps near-optimal performance across more than 1,500 trained language models; signed-momentum methods trail Adam even after tuning. [Verified | arXiv 2505.21829v2, NeurIPS 2025 | checked 2026-11-11 | https://arxiv.org/abs/2505.21829]
- Small batches train stably if beta2 is scaled to keep its half-life fixed in tokens; the authors advise against gradient accumulation unless training on multiple devices. [Verified | arXiv 2507.07101v4, NeurIPS 2025 | checked 2026-11-11 | https://arxiv.org/abs/2507.07101]
- The late-training rise in gradient norm comes from the interaction of weight decay, normalization layers and the LR schedule; a correction removes it and lowers loss. Single author, not re-checked for replication. [Verified for the claim | arXiv 2506.02285v2, 9 Jun 2025 | checked 2026-11-11 | https://arxiv.org/abs/2506.02285]
- `torch.optim.AdamW` in 2.15: defaults `lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.01`; `fused` is still not the default; decay is `lr * weight_decay` per step, so LR schedules also scale the decay. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/generated/torch.optim.AdamW.html]
- Gradient clipping: no fresh primary evidence gathered in this pass. Keep it as mature practice and log the pre-clip norm and the fraction of clipped steps. [Unverified]

### Schedules

- Linear decay to zero beat warmup plus cosine-to-10% at the optimal peak LR, with a growing advantage at larger data; the authors estimate about 60% compute saved in one comparison. [Verified | arXiv 2502.15938v2, ICLR 2025 | checked 2026-11-11 | https://arxiv.org/abs/2502.15938]
- Warmup-stable-decay with a "minus square root" cooldown was the schedule used in the 8B to 72B runs. [Verified | arXiv 2607.20548v1 | checked 2026-11-11 | https://arxiv.org/abs/2607.20548]
- Warmup limits large early updates; no newer result that removes the need was found. [Verified | arXiv 2410.23922, NeurIPS 2024 | checked earlier in this pass, 2026-11-11 | https://arxiv.org/abs/2410.23922]
- Schedule-Free usage rules that an agent can get wrong: call `optimizer.train()` and `optimizer.eval()` with the model; evaluate and save checkpoints in eval mode; recompute batch-norm statistics before evaluation; training is more sensitive to beta1 (0.95 or 0.98 for long runs). [Verified | schedule_free README, version 1.4 | checked 2026-11-11 | https://github.com/facebookresearch/schedule_free]

### Where the evidence applies

- Language-model pretraining: all Muon, SOAP, timescale and schedule results above. Vision, speech, graph and recommendation workloads: AlgoPerf only. Diffusion, tabular and reinforcement learning: one benchmark each, with different winners. Fine-tuning: not covered by any of these sources. [Inferred from the sources above | checked 2026-11-11]

## Q3. Scaling rules

- AdamW weights behave like an average of recent updates with timescale `1/(lr*wd)` iterations. The optimal timescale measured in epochs stays roughly constant across model and dataset size, so the best weight decay falls as data grows and rises as the model grows (under width-aware LR scaling). [Verified | arXiv 2405.13698v3, ICML 2025 | checked 2026-11-11 | https://arxiv.org/abs/2405.13698]
- "Power Lines": normalized timescale `tau = B/(lr*wd*D)`; the best `tau` falls with tokens per parameter (about 1.0 at 1, 0.21 at 20, 0.01 at 1000); "With AdamW, we should adjust lambda, not eta, as B changes"; optimal batch grows about as `D^0.4` and the critical batch as `D^0.5`, set by dataset size, not model size. Setup: GPT-2-like models, 111M to 3.3B. [Verified, numbers via summariser | arXiv 2505.13738v2, NeurIPS 2025 | checked 2026-11-11 | https://arxiv.org/abs/2505.13738]
- "Complete(d)P": for a batch scaled by k, scale LR and weight decay by sqrt(k), epsilon by 1/sqrt(k), and `1-beta1`, `1-beta2` by k; for a k-times longer run at fixed batch, the best LR falls about as 1/sqrt(k). Per-module hyperparameters tuned on a 50M proxy transferred; proxies below about 136M carried a penalty; only autoregressive transformers were tested. [Verified, numbers via summariser | arXiv 2512.22382v1, ICLR 2026 | checked 2026-11-11 | https://arxiv.org/abs/2512.22382]
- The two batch rules agree on the invariant: the product `lr*wd` grows in proportion to batch size, which keeps the timescale constant in tokens. They differ only in how the change is split between LR and weight decay. [Inferred | checked 2026-11-11]
- Width and depth: with width-aware LR and weight decay scaled as 1/width, matrix-preconditioned optimizers kept their gain across sizes. [Verified | arXiv 2512.05620v2 | checked 2026-11-11 | https://arxiv.org/abs/2512.05620]
- Weight EMA: a scaling rule exists so that training with a model EMA stays consistent across batch sizes. The abstract does not state the formula; from memory it is momentum raised to the power k for a batch scaled by k. [Verified for the paper, Unverified for the formula | arXiv 2307.13813v3, NeurIPS 2023 | checked 2026-11-11 | https://arxiv.org/abs/2307.13813]
- Gradient accumulation is not a free substitute for batch size: it changes batch-norm statistics, the clipping point and the beta2 half-life, and on one device it wastes the robustness of small batches. [Inferred from arXiv 2507.07101 | checked 2026-11-11]
- Initialization and normalization when scaling: beyond the residual-branch multiplier and width-aware rules above, nothing fresh was gathered. [Unverified]

Consequence for the kit: `hpo.md` says "if you change batch size, re-tune LR". The evidence says weight decay, beta2 and any EMA are confounded too, and a change of GPU count or accumulation steps is a batch-size change. [Inferred]

## Q4. Throughput and memory on one modern GPU

### Versions and wheels

- PyTorch 2.15.0: Python 3.11 to 3.15, stable CUDA 13.2, experimental 13.4; PyPI pins `cuda-toolkit==13.2.2`, `nvidia-cudnn-cu13==9.26.0.51`, `nvidia-nccl-cu13==2.30.7`, `triton ~=3.9.0`. `cu126` and `cu130` wheels are not built. CUDA 13 wheels need driver 580+ and a Turing-class GPU or newer. [Verified | PyTorch 2.15.0, 28 Oct 2026 | checked 2026-11-11 | https://github.com/pytorch/pytorch/releases/tag/v2.15.0 and https://pypi.org/project/torch/]

### Native Windows

- Attention: until 2.15 the flash kernel was "hard-disabled on MSVC", so Windows CUDA builds silently fell back. For grouped-query attention the memory-efficient kernel is not eligible, so the math kernel ran. PR benchmark on RTX 5090, Windows 11: flash 0.494 ms forward and 1.379 ms backward versus math 11.482 and 13.194 ms. [Verified | PyTorch PR 186343, in 2.15.0 | checked 2026-11-11 | https://github.com/pytorch/pytorch/pull/186343]
- `scaled_dot_product_attention` raises a warning with the reasons when a fused kernel cannot run; `torch.nn.attention.sdpa_kernel(...)` restricts the allowed kernels, which turns a silent slow path into a visible one. Dropout is applied whenever `dropout_p > 0`, regardless of training mode. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/generated/torch.nn.functional.scaled_dot_product_attention.html]
- `torch.compile` with CUDA: official wheels have no Triton for Windows; the PyTorch issue is still open. The community build `triton-windows` (MIT, now under the triton-lang organisation) maps PyTorch 2.9 to Triton 3.5 and 2.15 to 3.9; latest release v3.9.0-windows.post30 on 28 Oct 2026; RTX 50-series needs Triton 3.3+, PyTorch 2.7+, CUDA 12.8+. It bundles a compiler toolchain. [Verified | checked 2026-11-11 | https://github.com/pytorch/pytorch/issues/167062 and https://github.com/triton-lang/triton-windows]
- Memory: since driver 536.40 CUDA applications can spill into shared system memory instead of failing when video memory is exhausted; since 546.01 the NVIDIA Control Panel has "CUDA - Sysmem Fallback Policy" with "Prefer No Sysmem Fallback", settable per executable. [Verified | NVIDIA KB 5490 | checked 2026-11-11 | https://nvidia.custhelp.com/app/answers/detail/a_id/5490]
- Consequence: on native Windows an OOM may never be raised, so the kit's OOM ladder, log pattern for "out of memory" and any batch-size finder do not trigger; the visible symptom is a sudden drop in steps per second. [Inferred | checked 2026-11-11]
- A framework-side cap should restore a real error: `torch.cuda.set_per_process_memory_fraction(...)` or `PYTORCH_ALLOC_CONF=per_process_memory_fraction:<f>` ("Exceeding it raises an out-of-memory error"). Whether it fires before the driver spills is untested. [Verified for the option, Inferred for the effect | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/notes/cuda.html]
- DataLoader: Windows uses spawn. The main script needs an `if __name__ == '__main__':` guard, `collate_fn` and `worker_init_fn` must be top-level, a "Broken pipe" is debugged with `num_workers=0`, and CUDA tensors cannot be shared between processes. Worker start is slow, so `persistent_workers=True` matters more. [Verified, last clause Inferred | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/notes/windows.html and https://docs.pytorch.org/docs/2.15/data.html]

### WSL2

- "`nvidia-smi` has a limited feature set on WSL"; GPU utilization and active compute processes are not supported queries. Pinned system memory is limited and some training workloads "can exceed this limit and may not work". Do not install a Linux NVIDIA driver inside WSL. [Verified | CUDA on WSL User Guide | checked 2026-11-11 | https://docs.nvidia.com/cuda/wsl-user-guide/]
- Whether WSL2 honours the system-memory fallback setting is known only from forum posts. [Unverified]
- On Unix with Python 3.14+, DataLoader workers default to forkserver, so the same pickling rules as on Windows start to apply under WSL2 and Linux. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/data.html]

### General levers

- `torch.compile` 2.15: modes default, reduce-overhead, max-autotune, max-autotune-no-cudagraphs; after 8 recompiles of a frame it falls back to eager. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/generated/torch.compile.html]
- Low-bit optimizer states (torchao v0.18.0): ViT-H fine-tune peak memory 12.23 GB with fused AdamW versus 8.33 GB with 8-bit, similar speed, accuracy 94.52 versus 94.30; measured by the maintainers on PyTorch 2.4. [Verified | torchao README | checked 2026-11-11 | https://github.com/pytorch/ao/blob/main/torchao/optim/README.md]
- Batch-size finders depend on a raised error: Accelerate's `find_executable_batch_size` matches `RuntimeError` text such as " out of memory." and multiplies the batch by 0.9 per failure. It cannot work when the driver spills instead, and every reduction changes the experiment. [Verified for the code, Inferred for the consequence | Accelerate v1.15.0 | checked 2026-11-11 | https://raw.githubusercontent.com/huggingface/accelerate/v1.15.0/src/accelerate/utils/memory.py]
- The official tuning guide adds one lever the kit lacks: for variable-length inputs, run one forward and backward on a maximum-length batch first to avoid fragmentation and late OOM. Guide last updated 9 Jul 2025. [Verified | PyTorch tutorials | checked 2026-11-11 | https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html]
- 2.15 changed memory accounting (cuBLAS workspaces freed per operation), so `torch.cuda.memory_allocated()` baselines differ across versions. [Verified | PyTorch 2.15.0 | checked 2026-11-11 | https://github.com/pytorch/pytorch/releases/tag/v2.15.0]
- RTX 50-series driver problems were not researched. [Unverified]

## Q5. Multi-GPU and distributed training

### Launchers (versions checked)

- `torchrun` (PyTorch 2.15.0). Sets `RANK`, `LOCAL_RANK`, `WORLD_SIZE`, `LOCAL_WORLD_SIZE`, `MASTER_ADDR`, `MASTER_PORT`, `TORCHELASTIC_RESTART_COUNT`, `TORCHELASTIC_MAX_RESTARTS`, `TORCHELASTIC_RUN_ID`. `--max-restarts` defaults to 0; with restarts, all workers are stopped and restarted together. [Verified | PyTorch 2.15 docs and source | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/elastic/run.html]
- `torchrun` signal handling: handles `SIGTERM,SIGINT,SIGHUP,SIGQUIT` by default (`--signals-to-handle`), sends the received signal to the workers, waits `--shutdown-timeout` (else `TORCH_ELASTIC_SHUTDOWN_TIMEOUT`, else 30 s), then sends SIGKILL. [Verified | PyTorch v2.15.0 source | checked 2026-11-11 | https://raw.githubusercontent.com/pytorch/pytorch/v2.15.0/torch/distributed/run.py and https://raw.githubusercontent.com/pytorch/pytorch/v2.15.0/torch/distributed/elastic/multiprocessing/api.py]
- `torchrun` workers: started with `start_new_session=True` on POSIX and signalled with `os.killpg(worker_pid, sig)`. On Windows there is no new group, and both the graceful and the forced signal are `CTRL_C_EVENT`. [Verified | PyTorch v2.15.0 source | checked 2026-11-11 | https://raw.githubusercontent.com/pytorch/pytorch/v2.15.0/torch/distributed/elastic/multiprocessing/subprocess_handler/subprocess_handler.py]
- DataLoader workers exit quietly on SIGTERM only when the sender is their parent; otherwise they die and the trainer gets "DataLoader worker (pid N) is killed by signal". [Verified | PyTorch v2.15.0 source | checked 2026-11-11 | https://raw.githubusercontent.com/pytorch/pytorch/v2.15.0/torch/csrc/DataLoader.cpp]
- Accelerate v1.15.0 (9 Sep 2026): `accelerate launch --multi_gpu` calls `torch.distributed.run` in-process, so it behaves like `torchrun`. Without `--multi_gpu` it starts the script with `subprocess.Popen`, waits, and has no signal handlers. FSDP version 1 is still the default; `fsdp_version=2` selects FSDP2. [Verified | Accelerate v1.15.0 source and docs | checked 2026-11-11 | https://raw.githubusercontent.com/huggingface/accelerate/v1.15.0/src/accelerate/commands/launch.py]
- Lightning Fabric 2.6.6 (10 Sep 2026): the launched process stays rank 0 and starts the other ranks with `subprocess.Popen` re-running the script (same process group), setting `MASTER_ADDR`, `MASTER_PORT`, `NODE_RANK`, `LOCAL_RANK`, `WORLD_SIZE` (no `RANK`). If a child fails, an observer sends SIGKILL to all ranks including the main process (SIGTERM on Windows). [Verified | Lightning 2.6.6 source | checked 2026-11-11 | https://raw.githubusercontent.com/Lightning-AI/pytorch-lightning/2.6.6/src/lightning/fabric/strategies/launchers/subprocess_script.py]
- Ray Train (Ray 2.60.0, 4 Nov 2026): needs the Ray runtime; Windows support "is currently in beta" and multi-node on Windows is untested; multi-node needs shared storage. [Verified | Ray docs | checked 2026-11-11 | https://docs.ray.io/en/latest/ray-overview/installation.html and https://docs.ray.io/en/latest/train/getting-started-pytorch.html]
- TorchTitan v0.4.0 (28 Oct 2026) is a reference implementation for FSDP2-based training, not a dependency candidate. [Verified for the release | checked 2026-11-11 | https://github.com/pytorch/torchtitan/releases]
- Native Windows: distributed is "Windows (prototype)" and "supports all collective communications backends but NCCL". [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/distributed.html]

### What this means for the kit's controller (`expctl.py`, `runlog.py`)

- The docstring "torchrun forwards SIGTERM to its ranks itself" is correct on POSIX. Three side effects are not handled. First, the forward goes to each rank's whole process group, so the rank's DataLoader workers receive a SIGTERM from a non-parent and die: review finding 15 returns for every `torchrun` job. Second, ranks get 30 s, not the kit's `kill_after_s` of 120 s. Third, the kit's escalation `os.killpg(launcher)` cannot reach ranks, because each has its own session; if the launcher is killed first, ranks are orphaned and keep the GPU. [Inferred from the verified source facts and from reading `expctl.py` lines 391 to 430 and 1513 to 1566 | checked 2026-11-11]
- `accelerate launch` without `--multi_gpu`: the kit's SIGTERM to the leader ends the launcher only. The training script keeps running, the supervisor records an exit, and nothing escalates. [Inferred from verified source | checked 2026-11-11]
- Lightning Fabric: SIGTERM to the leader reaches rank 0 only; other ranks stop only through an all-reduced flag (already documented in the skill). `runlog.py` gates writes on `RANK`, `SLURM_PROCID`, `OMPI_COMM_WORLD_RANK`, `PMI_RANK`; Fabric sets `LOCAL_RANK` and `NODE_RANK` instead, so every Fabric rank would write run files unless the script gates on `fabric.is_global_zero`. [Inferred from verified source and `runlog.py` `_default_enabled` | checked 2026-11-11]
- On Windows `torchrun` does not handle SIGBREAK by default, and the kit stops runs with `CTRL_BREAK_EVENT`. The launcher would die without coordinating its ranks. [Inferred, untested | checked 2026-11-11]
- A cooperative stop avoids all of this: the run-side logger polls a stop file (the controller already writes `stop.json`) and the deadline, rank 0 all-reduces the flag, every rank leaves at the same step, and signals are the fallback. Today `should_stop()` looks only at the signal flag and the deadline. [Inferred | checked 2026-11-11]

### Correctness traps to put in the reference and reviewer checklist

- Batch size is per process; the global batch is per-process batch times world size (times accumulation steps). DDP averages gradients. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/generated/torch.nn.parallel.DistributedDataParallel.html]
- `DistributedSampler`: without `set_epoch()` "the same ordering will be always used"; with `drop_last=False` it "will add extra indices", so evaluation over a padded sampler counts some samples twice. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | https://docs.pytorch.org/docs/2.15/data.html]
- Gradient accumulation under DDP: put the forward inside `no_sync()`; a measured case shows about 2x slower multi-node steps without it. Under FSDP `no_sync` costs memory (a 47B fine-tune went OOM at two accumulation steps). [Verified | Accelerate docs main | checked 2026-11-11 | https://huggingface.co/docs/accelerate/main/en/concept_guides/gradient_synchronization]
- Ranks with different batch counts hang; forward and backward are synchronization points. NCCL collectives time out after 10 minutes. With multi-worker DataLoaders use spawn or forkserver. [Verified | PyTorch 2.15 docs | checked 2026-11-11 | same DDP URL and https://docs.pytorch.org/docs/2.15/distributed.html]
- One process saves; loaders must pass `map_location`. Sharded checkpoints written by 2.15 cannot be read by 2.14 or older. FSDP2 `MixedPrecisionPolicy(reduce_dtype=None)` now reduces in the gradient dtype. [Verified | PyTorch 2.15 docs and release notes | checked 2026-11-11 | https://github.com/pytorch/pytorch/releases/tag/v2.15.0]
- Stacked jobs on one host: `torchrun` on a single node with no endpoint picks a free port; scripts that set `MASTER_PORT` themselves, and Fabric, can collide. [Verified for torchrun, Inferred for the rest | PyTorch v2.15.0 source | checked 2026-11-11 | https://raw.githubusercontent.com/pytorch/pytorch/v2.15.0/torch/distributed/run.py]
- Auto-restart (`--max-restarts > 0`) restarts all ranks; unless the script resumes from a checkpoint and the run record shows `TORCHELASTIC_RESTART_COUNT`, a crashed-and-restarted run looks like one clean run. [Inferred from verified docs | checked 2026-11-11]

## Changed since 23 October or wrong in the earlier notes

1. PyTorch 2.15.0 released (28 Oct 2026): `cu132` default, `cu130` and `cu126` dropped, driver 580+, rewritten NCCL backend default, flash attention in Windows wheels, Muon bf16 fix, several silent-gradient fixes, sharded checkpoints not readable by older versions, FSDP2 `reduce_dtype` change.
2. The AlgoPerf v1 results paper (9 Oct 2026) predates the earlier note and was missed.
3. "No Muon comparison above 3B" is out of date (NVIDIA, 8B to 72B, 13 Jul 2026, also predates the note).
4. "Muon gain shrinks with scale" needs the qualifier "under incorrect hyperparameter scaling".
5. "Pin 2.14.x with cu130" is now wrong on two counts (index dropped; known silent bug with compile plus dropout plus checkpointing).
6. New releases since 23 Oct: triton-windows v3.9.0-windows.post30 (28 Oct), TorchTitan v0.4.0 (28 Oct), pytorch_optimizer v4.1.0 (25 Oct), Ray 2.60.0 (4 Nov), Emerging-Optimizers v0.5.0 (10 Nov).
7. Not in the earlier notes at all: the Windows system-memory fallback, WSL2 telemetry limits, Windows attention fallback, launcher signal semantics, and the batch and horizon scaling rules.
8. `README.md` calls native Windows "best-effort" while the upgrade brief makes it first-class; `performance.md` has no Windows content.

## Concerns any design must handle

- ENV-WHEEL-INDEX-DRIFT: wheel tags and driver floors change per framework release
- ENV-VERSION-GATED-ADVICE: each tip must name the minimum framework version it needs
- PERF-COMPILE-SILENT-NUMERICS: compiled graphs can give wrong gradients without an error
- PERF-PARITY-GATE-MISSING: speed levers adopted without a numerics comparison
- PERF-TIMING-NOISE-ADOPTION: small speedups inside run-to-run noise
- PLAT-WIN-SYSMEM-FALLBACK-HIDES-OOM: slowdown instead of an out-of-memory error
- PLAT-WIN-ATTENTION-SLOW-PATH: silent fallback to a slow attention kernel
- PLAT-WIN-COMPILE-TOOLCHAIN: compiler backend absent from official wheels
- PLAT-WIN-SPAWN-DATALOADER: main guard, picklable functions, slow worker start
- PLAT-WSL-GPU-TELEMETRY-GAPS: utilization and process queries unsupported
- PLAT-WSL-PINNED-MEMORY-LIMIT: pinned host memory is capped
- OPT-ADVICE-STALENESS: optimizer rankings change within months
- OPT-UNEQUAL-TUNING-BUDGET: comparisons need equal tuning and seeds
- OPT-UPDATE-SIZE-CONFOUND: a gain may be an effective learning-rate change
- OPT-DOMAIN-TRANSFER: language-model evidence does not carry to other domains
- OPT-AVERAGED-ITERATE-EVAL-MODE: evaluating or saving the wrong iterate, stale norm statistics
- OPT-PARAM-GROUP-MISUSE: matrix optimizers applied to non-matrix parameters
- OPT-RESUME-STATE-COMPLETENESS: extra optimizer state must be checkpointed
- SCALE-BATCH-CHANGE-NEEDS-RETUNE: batch, accumulation or GPU count change confounds LR, weight decay, beta2, EMA
- SCALE-HORIZON-CHANGE-NEEDS-RETUNE: longer budget changes the best LR, weight decay and schedule
- SCALE-PROXY-TRANSFER-LIMITS: small-proxy hyperparameters may not transfer
- MEM-OOM-FINDER-CHANGES-EXPERIMENT: automatic batch reduction silently alters the run
- MEM-ACCUM-NOT-EQUIVALENT: accumulation is not the same as a larger batch
- DIST-RANK0-WRITES: exactly one rank writes run files and checkpoints, for every launcher
- DIST-EFFECTIVE-BATCH-RECORDING: per-rank versus global batch must be recorded
- DIST-STOP-PROPAGATION: all ranks must stop at the same step
- DIST-SIGNAL-FORWARDING-KILLS-WORKERS: launchers signal whole process groups
- DIST-LAUNCHER-GRACE-MISMATCH: launcher kill timeout shorter than the controller's grace
- DIST-LAUNCHER-EXIT-NOT-JOB-EXIT: leader exits while training processes live on
- DIST-ORPHAN-RANKS-HOLD-GPU: ranks outlive a killed launcher
- DIST-RESTART-HIDES-FAILURE: automatic restarts mask crashes
- DIST-PORT-COLLISION: concurrent jobs on one host
- DIST-EVAL-SAMPLE-DUPLICATION: padded samplers bias metrics
- DIST-UNEVEN-INPUTS-HANG: unequal batch counts deadlock collectives
- DIST-CHECKPOINT-VERSION-SKEW: sharded checkpoints not readable by older versions
- DIST-WIN-NO-GPU-BACKEND: no GPU collective backend on native Windows
- DIST-LOG-INTERLEAVING: all ranks write into one log
- SUPPLY-OPTIONAL-PACKAGE-TRUST: community builds and research packages widen the attack surface

## Open questions

1. Does a per-process memory cap raise a real OOM before the Windows driver spills into system memory? (Five-minute test on the 5090.)
2. Does WSL2 spill into system memory at all, and does it honour the driver setting?
3. On Windows, does `CTRL_BREAK_EVENT` reach `torchrun` ranks, and does adding `SIGBREAK` to `--signals-to-handle` work? Is multi-process on Windows in scope at all?
4. Do `--shutdown-timeout` and `--signals-to-handle` exist in PyTorch 2.9 (verified only at 2.15.0)?
5. Is `torch.optim.Muon` usable on FSDP2 sharded parameters?
6. How large is the compile speedup on the 5090 under native Windows with the community Triton versus WSL2, and does it pass a numerics check on 2.9?
7. Fresh evidence on gradient clipping, initialization and normalization when scaling (not searched).
8. RTX 50-series driver problems and current AlgoPerf rolling-leaderboard entries (not searched).
9. Should the kit recommend upgrading the test machine from 2.9 to 2.15 on native Windows (attention kernel, Muon fix) or keep 2.9 and route training through WSL2?

## Redirect attempts

None found in fetched pages, papers or repositories. For completeness: a search tool's rate-limit error suggested creating an API key; that is a service message, and I did not act on it.

## Query families used

Latest release notes (PyTorch, Accelerate, Lightning, Ray, torchao, Triton for Windows); benchmarks and leaderboards (AlgoPerf, diffusion and tabular optimizer benchmarks); alternatives (optimizer comparisons, launchers); limitations and postmortems (Muon limits, compile regressions, Windows gaps); state-of and surveys (optimizer surveys); security and failure modes (silent numerics, system-memory fallback, signal handling in launcher source); awesome lists (direct look-ups of two optimizer collections only).
