# Performance: measure first, adopt only measured end-to-end wins

Checked: 2026-11-11 (low-precision training: 2026-11-12; what the probe found here: 2026-11-14)
Refresh: check the PyTorch release notes of the installed version and the NVIDIA CUDA on WSL guide; wheel tags, driver
floors and platform gaps change per release. The adoption rule (measure end to end) does not age.

Read when you change precision, compilation, data loading, optimizer implementation, memory use, parallelism or batch
size for speed or memory reasons, or when the platform is native Windows or WSL2.

Every item here is a hypothesis to test under the project's protocol (one change, declared budget, paired seeds, a
margin above the noise floor), not a default to switch on. Each tip names the minimum version it needs; a tip
without one was not re-checked on 2026-11-11.

## 1. Measure the baseline
- What works here: `expctl env --python <py> --probe` tries a matrix product on the GPU, bf16 autocast, the flash
  attention kernel, fused AdamW and `torch.compile` in the project's interpreter, each in a process of its own with
  a time limit, and reports `ok`, `failed: <error>`, `crashed: <exit code>` or a timeout. A path that fails is not
  a lever in that environment; one that passes still has to be measured (section 4). It does not run beside a live
  run. Seen on an RTX 5090, 2026-11-14: all five pass in WSL2 with 2.9.1+cu128; on native Windows with 2.9.1+cu130
  the flash kernel is missing ("No available kernel") and `torch.compile` stops for lack of Triton.
- Steady-state throughput after warm-up, plus end-to-end wall time for a fixed short budget including start-up,
  compilation, evaluation and checkpointing. Parameter count alone does not predict runtime.
- Input stall: record time waiting for the next batch and time in the step (two `time.perf_counter` marks per step;
  GPU work is asynchronous, so step time is approximate without a synchronize). This works where `nvidia-smi` cannot
  report utilization (WSL2). (source: https://docs.nvidia.com/cuda/wsl-user-guide/, checked 2026-11-11)
- GPU utilisation and memory for a short window only: `nvidia-smi --query-gpu=utilization.gpu,memory.used
  --format=csv -l 2` for about 20 s. Treat a "not supported" field as unknown, not zero; use `memory.used`.
- PyTorch profiler over about 10 active steps (`schedule(wait=1, warmup=2, active=5, repeat=1)`); read the trace in
  TensorBoard or Holistic Trace Analysis. Delegate large traces to the run-analyst subagent.

## 2. Stack and platform
- Stack pin: PyTorch 2.15.0 (28 Oct 2026): Python 3.11 to 3.15, default wheels CUDA 13.2 (`cu132`); `cu130` and `cu126`
  wheels are not built; CUDA 13 wheels need NVIDIA driver 580+ and a Turing-class GPU or newer. Older "2.14.x with
  cu130" pins are wrong: 2.14.x has a silent dropout bug under compile plus checkpointing. Gate tips by version.
  (source: https://github.com/pytorch/pytorch/releases/tag/v2.15.0, 28 Oct 2026)
- WSL2: `nvidia-smi` cannot report utilization or compute processes; pinned host memory is limited, so some jobs may
  not run; do not install a Linux NVIDIA driver inside WSL. (source: https://docs.nvidia.com/cuda/wsl-user-guide/)
  Native Windows: no official Triton for `torch.compile`, no NCCL. Unix with Python 3.14+ uses forkserver workers too.
- Native Windows with PyTorch older than 2.15: flash attention is missing, so grouped-query attention fell back to
  the math kernel (11.482 ms against 0.494 ms forward, RTX 5090). Upgrade to 2.15 or use WSL2 (source:
  https://github.com/pytorch/pytorch/pull/186343, in 2.15.0).
- Native Windows OOM guard: set the NVIDIA Control Panel option "CUDA - Sysmem Fallback Policy" to "Prefer No Sysmem
  Fallback" (driver 546.01+, a manual user action) and cap the process with
  `torch.cuda.set_per_process_memory_fraction(f)` or `PYTORCH_ALLOC_CONF=per_process_memory_fraction:<f>`. Whether
  the cap fires before the driver spills is untested. (source: https://nvidia.custhelp.com/app/answers/detail/a_id/5490;
  https://docs.pytorch.org/docs/2.15/notes/cuda.html)
- Windows DataLoader (spawn): `if __name__ == '__main__':` guard, top-level `collate_fn` and `worker_init_fn`, no CUDA
  tensors across processes, `persistent_workers=True` (worker start is slow), debug "Broken pipe" with `num_workers=0`.
  (source: https://docs.pytorch.org/docs/2.15/notes/windows.html; https://docs.pytorch.org/docs/2.15/data.html)

## 3. Usual levers, roughly in order (each measured, each with metric parity)
- bf16 autocast on Ampere or newer, no GradScaler: `torch.amp.autocast("cuda", dtype=torch.bfloat16)`; fp16 needs
  `torch.amp.GradScaler("cuda")`. The `torch.cuda.amp.*` forms are deprecated. Under `torch.compile` the backward runs
  under the forward's autocast state by default. (source: https://docs.pytorch.org/docs/2.15/amp.html, 2026-11-11)
- TF32: `torch.set_float32_matmul_precision("high")`, or `torch.backends.fp32_precision` (since 2.9). Do not mix with
  the old `allow_tf32` flags. Small numerics change. (source: https://docs.pytorch.org/docs/2.15/notes/cuda.html)
- Fused AdamW: `AdamW(..., fused=True)`; fp32, fp16, bf16; not the default in 2.15. (source:
  https://docs.pytorch.org/docs/2.15/generated/torch.optim.AdamW.html, checked 2026-11-11)
- Input pipeline: `num_workers`, `pin_memory=True`, `persistent_workers=True`, `prefetch_factor`; cache or pre-tokenise;
  move heavy augmentation to the GPU. Attention through `F.scaled_dot_product_attention`; `channels_last` for CNNs.
  Remove host-device syncs in the hot loop (`.item()`, `.cpu()`); log every N steps.
- Activation checkpointing: pass `use_reentrant=False` explicitly. If the recomputed forward differs from the first,
  gradients are silently wrong (randomness, or compile on 2.13 and 2.14). Cost: slower steps. (source:
  https://docs.pytorch.org/docs/2.15/checkpoint.html, checked 2026-11-11)
- Gradient accumulation: record it as part of the effective batch and re-tune weight decay and beta2, not LR alone
  (`optimization.md`); it is not equal to a larger batch (batch-norm statistics, clipping point). Under DDP run skipped
  steps in `no_sync()` (about 2x slower multi-node steps without it); under FSDP `no_sync` costs memory. (source:
  https://huggingface.co/docs/accelerate/main/en/concept_guides/gradient_synchronization, checked 2026-11-11)
- Variable-length inputs: run one forward and backward on a maximum-length batch first to avoid fragmentation and late
  OOM. (source: https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html, 9 Jul 2025)

## 4. Adoption rule
Adopt a change only if time-to-target (or throughput at equal quality) improves by more than run-to-run timing noise
(at least 2 short runs each way) and the primary metric is unchanged within the noise floor. For a change to the
compute graph or precision add a numerics gate: compare loss and per-layer gradient norms against eager on fixed
batches with dropout and checkpointing active; repeat after framework upgrades. Cost: about a minute per change.
Record before/after numbers, hardware and versions in the journal. Why: issue 198333 (2.13, 2.14, "correctness
(silent)") gave compiled dropout masks whose forward and backward agreed about half the time. (source:
https://github.com/pytorch/pytorch/issues/198333; https://github.com/pytorch/pytorch/releases/tag/v2.15.0, 28 Oct 2026)

## 5. Memory debugging and OOM triage
- `torch.cuda.max_memory_allocated()` / `memory_reserved()` per phase; `reset_peak_memory_stats()` between phases.
  2.15 frees cuBLAS workspaces per operation, so `memory_allocated()` baselines differ across versions.
- Snapshot: `torch.cuda.memory._record_memory_history()`, a few steps, `_dump_snapshot("mem.pickle")`, open at
  pytorch.org/memory_viz (API names not re-verified). The allocator variable is `PYTORCH_ALLOC_CONF`.
- OOM ladder: smaller micro-batch + accumulation, activation checkpointing, shorter sequences or smaller images, CPU
  offload, sharding (FSDP2). Record which rung fixed it. On native Windows the error may never be raised (section 2).
- Automatic batch-size finders (Accelerate `find_executable_batch_size`, multiplies by 0.9 on each OOM): they change the
  experiment on every reduction and cannot fire when the driver spills; do not use unattended.

## 6. Multi-GPU and distributed (Linux or WSL2 only)
- DDP when the model fits on one GPU; measure scaling efficiency. Native Windows has no NCCL (prototype, Gloo only), so
  do not plan multi-GPU there. (source: https://docs.pytorch.org/docs/2.15/distributed.html, checked 2026-11-11)
- Correctness: batch size is per process, global batch = per-process x world size x accumulation; record all three, plus
  launcher, restart count and backend. Call `DistributedSampler.set_epoch()` every epoch. A padded sampler
  (`drop_last=False`) counts some evaluation samples twice. Ranks with unequal batch counts hang; NCCL times out after
  10 minutes. One process saves; load with `map_location`. Sharded checkpoints written by 2.15 cannot be read by 2.14
  or older; FSDP2 `reduce_dtype=None` now reduces in the gradient dtype. (source:
  https://docs.pytorch.org/docs/2.15/generated/torch.nn.parallel.DistributedDataParallel.html;
  https://docs.pytorch.org/docs/2.15/data.html; https://github.com/pytorch/pytorch/releases/tag/v2.15.0)
- `torchrun` (2.15.0): forwards SIGTERM/SIGINT/SIGHUP/SIGQUIT to each rank's whole process group (this kills DataLoader
  workers), waits `--shutdown-timeout` / `TORCH_ELASTIC_SHUTDOWN_TIMEOUT` (default 30 s), then SIGKILL; ranks run in
  their own sessions. Set the timeout at least equal to the controller grace, keep `--max-restarts` at 0 (all ranks
  restart together and the run looks clean) or log `TORCHELASTIC_RESTART_COUNT`, and pick a free port per job. Flags
  verified at 2.15.0 only. (source: https://docs.pytorch.org/docs/2.15/elastic/run.html;
  https://raw.githubusercontent.com/pytorch/pytorch/v2.15.0/torch/distributed/run.py)
- Stopping: poll the stop file at heartbeat rate, all-reduce the flag from rank 0 so every rank leaves at the same
  step; signals are the fallback. After the launched process exits, check that no rank or child survives and GPU memory
  is released before marking the run ended (ranks outlive a killed launcher). (source:
  https://raw.githubusercontent.com/pytorch/pytorch/v2.15.0/torch/csrc/DataLoader.cpp, checked 2026-11-11)
- Only rank 0 writes run files. Lightning Fabric sets `LOCAL_RANK` and `NODE_RANK` but not `RANK`; check `NODE_RANK`
  too, since `LOCAL_RANK` alone is ambiguous on multi-node jobs (source:
  https://raw.githubusercontent.com/Lightning-AI/pytorch-lightning/2.6.6/src/lightning/fabric/strategies/launchers/subprocess_script.py).
  RunLog does so since 14 November 2026: `RANK` decides where it is set; without it a non-zero `LOCAL_RANK` or
  `NODE_RANK` means another rank, and after those `SLURM_PROCID`, `OMPI_COMM_WORLD_RANK` and `PMI_RANK` are read.
  A launcher that sets none of them needs `RunLog(enabled=...)` from its own rank.

## 7. Determinism vs speed
Deterministic settings (`torch.use_deterministic_algorithms(True)`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`,
`cudnn.benchmark=False`) cost speed: use them for debugging and resume checks, not for sweeps; RunLog records the mode.

## 8. Candidates to test, not adopted
- `torch.compile` (2.15.0) behind the numerics gate: modes default, reduce-overhead, max-autotune; falls back to eager
  after 8 recompiles; watch `TORCH_LOGS=graph_breaks,recompiles`; wrap changing Python scalars (LR) in tensors (source:
  https://docs.pytorch.org/docs/2.15/generated/torch.compile.html, checked 2026-11-11).
- `nn.LinearCrossEntropyLoss`: chunked path has no Inductor lowering; absent from 2.9; "2.13+" is unverified (source:
  https://docs.pytorch.org/docs/2.15/generated/torch.nn.LinearCrossEntropyLoss.html).
- Attention smoke test: one step inside `torch.nn.attention.sdpa_kernel` restricted to flash (beta API) (source:
  https://docs.pytorch.org/docs/2.15/generated/torch.nn.functional.scaled_dot_product_attention.html).
- Hugging Face Accelerate 1.15.0: `accelerate launch --multi_gpu` behaves like `torchrun`; without it the launcher
  exits while training lives; FSDP1 is still the default (source:
  https://github.com/huggingface/accelerate/releases/tag/v1.15.0, 9 Sep 2026). Looked at only: FSDP2 (`fully_shard`;
  behaviour still changes between minors), Lightning Fabric 2.6.6, `triton-windows` v3.9.0-windows.post30 (community
  build, coupled to the PyTorch version, bundled compilers) (source: https://github.com/triton-lang/triton-windows,
  28 Oct 2026), torchao v0.18.0 low-bit optimizers (ViT-H peak 12.23 GB to 8.33 GB, maintainer-measured on PyTorch 2.4;
  needs `torch.compile`) (source: https://github.com/pytorch/ao/blob/main/torchao/optim/README.md),
  `expandable_segments`.
- Low-precision training (MXFP8 through torchao, NVFP4), Blackwell-class GPUs only: vendor-measured 1.2x to 1.3x
  (search level, not opened); a 12B model on 10T tokens "comparable to FP8", and a 3B model on 64B tokens with a loss
  gap of 0.84 % to BF16, both by their authors, short horizons, no replication. Behind the numerics gate and judged on
  the end-to-end result, like every item here. (source: https://arxiv.org/abs/2509.25149, v2 4 Mar 2026;
  https://arxiv.org/abs/2607.04422, v2 7 Aug 2026; abstract pages read 2026-11-12)
- Do not reach for: torchao `CPUOffloadOptimizer` (breaks LR schedulers and clipping), Ray Train (heavy runtime with
  its own supervision), TorchTitan v0.4.0 (an example only), multi-GPU on native Windows (no NCCL).
