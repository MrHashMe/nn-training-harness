# Checkpointing and resumption contract

Checked: 2026-11-11 for the resume commands (section 4); 2026-10-23 for the PyTorch claims (DCP, FSDP2,
StatefulDataLoader, determinism flags).
Refresh: run `tests/test_remote.py` (it covers `expctl resume`); check the PyTorch and torchdata release notes
for `torch.distributed.checkpoint` and `StatefulDataLoader` before relying on sections 1 and 2.

Read before implementing or changing checkpointing, before any run longer than ~1 hour, and before resuming anything.
Resuming an Optuna study or a tracker run only continues bookkeeping; it does not resume training.

## 1. What a resumable checkpoint contains (single process / DDP)
- model `state_dict` (plus EMA/SWA averaged weights if used), optimizer, LR scheduler, `GradScaler` (fp16 only; bf16 needs none)
- counters: global step, epoch, samples/tokens seen, best metric so far and its step (the selection state)
- RNG states: `random.getstate()`, `np.random.get_state()`, `torch.get_rng_state()`, `torch.cuda.get_rng_state_all()`
- data position: `torchdata.stateful_dataloader.StatefulDataLoader.state_dict()` for mid-epoch resume (beta); otherwise resume at epoch boundaries and record the sampler seed/epoch
- provenance: resolved config, source hash (`EXP_SOURCE_HASH`), data manifest hash, torch/CUDA versions
- Save deployment weights separately (e.g. safetensors) when useful; keep the training checkpoint complete.

## 2. Distributed (FSDP2 / multi-node)
- FSDP2 (`fully_shard`) has no direct full state dict: use `torch.distributed.checkpoint` (DCP) `save`/`load`, the `get_state_dict`/`set_state_dict` helpers, and `async_save` with at most one save in flight. DCP reshards on load, so the world size can change.
- DDP: save on rank 0 only, then barrier; load with `map_location` to the local device.
- Stopping distributed runs: RunLog's `should_stop()` is true on every rank after SIGTERM or the deadline, but ranks
  can observe it at different steps. All-reduce the flag each step
  (`f = torch.tensor(int(rl.should_stop()), device=dev); dist.all_reduce(f, op=dist.ReduceOp.MAX)`) and break
  together, then save.

## 3. Safety and retention
- Write atomically: save to a temporary name in the same directory, flush/fsync, then rename. DCP writes a directory: write a small completion sentinel last.
- Use per-run paths (`RunLog.path("ckpt", ...)` or `$EXP_RUN_DIR/ckpt/`) so concurrent runs never overwrite each other.
- Keep `best` (by the declared selection rule), `last` (for resume) and a bounded number of periodic checkpoints. Never delete `best`. Deleting artifacts outside the retention policy needs the user's approval.
- Check free disk space before saving. Checkpoint frequency follows step time and interruption risk (typically every 15–30 minutes of compute for long runs), and always when `should_stop()` turns true.

## 4. Resume procedure
- Resume as a new run: `expctl resume <run id>` repeats the ended run's command, seed, GPUs, tags and snapshot
  mode as a new run and hands it the parent's run directory (`EXP_RESUME_FROM`). The parent stays intact, and the
  new run's manifest and result name it (`resume_of`). It refuses a run that is still active.
- In the script: `if rl.resume_from: state = load(rl.resume_from / "ckpt" / "last.pt")`. Restore every item in
  section 1, continue the step counter, and log `resumed_from` (path, step) as the first metrics event. A script
  written this way also survives preemption on a remote target, where `nnremote` resumes it (`remote.md`).
- The resumed run executes the working tree as it is now. If the code changed since the parent, the source hashes
  differ: say so in the journal entry, because the result is then not a pure continuation.
- Resuming in place (same `EXP_RUN_DIR`) also works: RunLog moves the old `result.json`/`exit.json` aside as
  `*.prev-<time>.json` so the live run is not reported as finished.

## 5. Verify the resume boundary you promise
Run A: 2N steps uninterrupted. Run B: N steps, `expctl stop`, resume to 2N. Compare loss and metric curves.
- Exact equality is expected only with deterministic settings (`torch.use_deterministic_algorithms(True)`, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `cudnn.benchmark=False`, seeded DataLoader workers and generator) on the same hardware and versions.
- Otherwise state the guarantee you verified: "statistically equivalent continuation" or "epoch-boundary resume only".
- Reproducibility is not guaranteed across PyTorch releases, CPU vs GPU, different GPU models, different world sizes, or with non-deterministic kernels.

## 6. Pretrained-model adaptation
- Pin the base model by immutable revision (commit hash), not a branch name, and record it.
- Save the tokenizer/processor files and the chat template used for formatting; record packing and loss-masking choices.
- PEFT: save `adapter_config.json` + adapter weights; record target modules, rank, alpha, dropout.
- Quantisation (e.g. 4-bit NF4, double quantisation, bf16 compute dtype): record the exact config; evaluate adapters the way they will be deployed (quantised base or merged).
- Verify in a fresh process: base@revision + adapter reproduces the evaluation; if you merge adapters, merged and unmerged evaluations agree within tolerance.

## 7. Studies and crashed trials
- A trial whose process died is not resumable inside Optuna (it ends as FAIL or a stale RUNNING trial). If its checkpoint is valid, enqueue the same parameters as a new trial with a `resume_from` user attribute and record the link in the journal.
