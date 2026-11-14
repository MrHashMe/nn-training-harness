# Validity: protocol, leakage, sanity checks, sealed test, evaluator freeze

Checked: 2026-10-23 (section 5, the single-use final evaluation: 2026-11-12; the split audit command and the wiring checks of section 4: 2026-11-14)
Refresh: principles, not versions; re-read when the guard's sealed or frozen mechanics change
(`tests/test_kit.py` covers them) or when a new contamination or leakage route becomes known.

Read this before any tuning (Phase 2) and whenever data, splits, metrics or evaluation code change.
Goal: every number you report measures what the Project card says it measures.

## 1. Protocol contract (write it in the journal's Project card before tuning)
- Primary metric, direction, and how it is aggregated (micro/macro, per-sample vs per-batch, decoding settings for generative models).
- Selection rule: which checkpoint represents a run (best-by-validation at eval interval X, or final) — the trial score you return and the checkpoint you keep must follow the same rule.
- Budget unit for comparisons: equal steps / tokens / epochs / samples seen / wall-clock / GPU-hours. Count compile, data loading, evaluation and checkpointing explicitly for wall-clock budgets.
- Splits: unit of independence (example / user / patient / session / document / site / time) and the split method; permitted data and pretraining sources (licences, contamination concerns).
- Preprocessing fitted on training data only (normalisation stats, vocabularies/tokenizers trained here, feature selection, imputation, PCA).
- Protocol version (v1, v2, ...) and the evaluator file hashes (`sha256sum <evaluator files>`; in PowerShell `Get-FileHash <file> -Algorithm SHA256`).

## 2. Split and leakage audit (record counts in the journal)
- Unit leakage: the same user/patient/document/scene/time-window in more than one split. Fix with group-aware or chronological splits (GroupKFold, StratifiedGroupKFold, time cut-offs) — never random row splits when rows are dependent.
- Exact duplicates across splits: hash normalised records (text: lower-cased, whitespace-normalised; images: file hash). `expctl audit-splits` does this for the splits named in the config and prints counts only, never a row; where anything is sealed it needs the user's approval each time, because every count is a small look at the sealed split (`data.md` section 2). Near-duplicates: perceptual hashes for images, MinHash/embedding similarity for text; report counts and the threshold used.
- Temporal leakage: features computed with future information; training data later than validation/test data when the task predicts forward in time.
- Target leakage: features derived from the label or from post-outcome data; IDs that encode the label; file paths/folder names that reveal classes.
- Preprocessing leakage: statistics, tokenizers, vocabularies or augmentation policies fitted on all data; synthetic or augmented samples derived from validation/test items.
- Pretraining contamination (pretrained models and LLM benchmarks): n-gram overlap or exact-match checks against the evaluation set where feasible (they miss paraphrased copies: `evaluation.md` section 4); state when it cannot be checked.
- Label quality: sample and inspect ~50 random training and validation items with their labels; check class balance per split; note label-noise estimates if available.
- Persist a dataset/split manifest (`experiments/data_manifest.json`): file list or dataset id + revision, sizes, content hashes or fingerprints, split assignment hash, counts per split/class. Pass the manifest hash in every run's config so that the run records it (`data.md` section 1); the harness does not add it for you.

## 3. Metric implementation checks
- Unit-test the metric against a reference implementation (scikit-learn, TorchMetrics, the benchmark's official scorer) on a fixed batch, including edge cases (empty classes, ties, all-one-class).
- Aggregation: per-batch averaging with an uneven last batch biases results — accumulate sums/counts or use TorchMetrics; reset state between evaluations.
- Distributed evaluation: `DistributedSampler` pads with duplicate samples to equal shards — de-duplicate or evaluate on one rank; gather before computing global metrics.
- Evaluation mode: `model.eval()` + `torch.inference_mode()` (dropout off, BatchNorm running stats); for Schedule-Free optimizers also `optimizer.eval()`; for EMA models evaluate the EMA weights explicitly and say so.
- Thresholds, calibration and decoding parameters are chosen on validation only and recorded.

## 4. Sanity gate before any tuning (all must pass; record results)
1. One forward/backward/optimizer step on a real batch: finite loss, finite gradients, non-zero gradient norm for every trainable parameter (catches frozen or unused layers), parameter update actually changes weights.
   - Every trainable parameter is in an optimizer group: `held = {id(p) for g in opt.param_groups for p in g["params"]}`, then list each parameter with `requires_grad` whose `id` is not in `held`. A module created after the optimizer is not in it.
   - A gradient of `None` means the parameter is not in the graph of the loss, and the optimizer skips it. A gradient of exactly zero is in the graph and still moves under weight decay, so "the weights changed" proves nothing there: judge by the gradient.
   - Adapters: with LoRA's standard zero-initialised B, the gradient of A is exactly zero on the first step and non-zero on the second, so judge adapters after two steps. (These three: tried on 2026-11-14 with torch 2.9.1.)
2. Initial loss matches expectation (e.g. ln(C) for balanced C-class cross-entropy with a fresh head).
3. Overfit a tiny subset (1–2 batches) to near-zero training loss when the task allows it.
4. Shuffled-label control (cheap, short): validation performance should fall to chance; if not, suspect leakage.
5. Trivial baselines: majority class / mean predictor / linear probe on frozen features. The model must beat them clearly.
6. Checkpoint round trip in a fresh process: save, reload, re-evaluate — identical metrics within numerical tolerance and identical outputs on a fixed batch.
7. Throughput and peak memory of the baseline configuration (steps/s, samples or tokens/s, `torch.cuda.max_memory_allocated`).
8. Record total and trainable parameter counts (`sum(p.numel() for p in model.parameters())`, `... if p.requires_grad`). Enforce a size cap only if the project requires one.

## 5. Sealed test set
- Configure `.claude/nn-training.json`: `sealed_paths` (test files), ideally `sealed_tokens` (an unlock variable such as `NN_UNSEAL_TEST`) and exactly one `final_eval_commands` entry: one program call with its arguments, optionally after `NAME=value` pairs, without shell syntax (a pipe or a redirection goes into a script that the entry names; a path with spaces is quoted). The guard hook then denies other access, the configured command typed directly included, and asks the user before every `expctl final-eval`.
- Strongest practical setup: the test loader refuses to load unless `NN_UNSEAL_TEST=1`; only the final-eval command sets it. Hard isolation: keep the test split outside the repository and mount it only for the final evaluation.
- Final evaluation happens once, after the model, seed, training duration and checkpoint rule are frozen and written in the journal. Run it with `expctl final-eval [-- ARGS]`: it starts the configured command from the project root, with ARGS appended, and records the use before the command starts, in the hash-chained receipt `.claude/state/final-eval/receipt.jsonl` (command, arguments, commit, source hash; afterwards the exit code and the SHA-256 of the output, which is kept in a log beside the receipt) and in the journal. Add the checkpoint and the result to that journal entry. Never tune on what you see.
- A use is spent even if the command then fails: the test data may have been read. A second use is refused unless `--again "reason"` states why, and the reason is recorded. It is another look at the test data, so the user decides on it and the report states every use with its reason. A project with several `final_eval_commands` entries names one with `--which N` (counted from 1); the uses are counted for the project, not per entry, so the second entry is a further use and needs `--again` as well. Source of the pattern (the holdout opens only after a receipt is written, and a crash still consumes it): arXiv 2611.06607, checked 2026-11-11.
- The receipt is a record, not a seal. It counts what went through `expctl final-eval` in this checkout and in every worktree that git has registered (each keeps its own receipt), and every row is also kept in git's common folder (`nn-training-final-eval.jsonl` there), so a worktree that is removed leaves its uses in the count. Deleting the receipt folders and that copy takes the uses out of the count (the guard asks before a shell command or an edit touches any of them, and the journal entries remain), and it cannot see a program that reads the test files by a path it builds at run time.
- If someone wants repeated test checks, that set has become a validation set: say so and propose a new held-out set.

## 6. Frozen evaluator and protocol versions
- Put evaluator/metric/split files in `frozen_paths`; record their hashes in the Project card.
- A genuine evaluator bug: stop, explain, get approval, fix it as protocol v(N+1), re-evaluate the baseline and candidates under the new version (from saved checkpoints when possible), and never mix numbers across versions.

## 7. Baselines
- Reuse an existing baseline only if its provenance matches: code hash/commit, config, data manifest/split identity, metric/protocol version, budget and seed are known. Otherwise establish the strongest baseline the budget allows (tuned learning rate at least — an untuned baseline inflates every later gain).
- Label partial results honestly ("baseline at 30% of budget"); never compare a partial run with a completed one as if budgets matched.

## 8. Specification gaming — structural rules
Agents game metrics far more often in ML-optimisation tasks than in general coding, and "please do not cheat" instructions do little; structure does. Therefore:
- Never change the evaluator, metric, data, splits, budget accounting, timers, seeds of the comparison, or the comparison itself to make a candidate win.
- Never special-case evaluation items, read labels from evaluation outputs, or cache predictions across runs.
- The score comes from the harness (frozen evaluator + run files), never from numbers typed into the journal.
- Every retained change gets a diff review (experiment-reviewer subagent) that looks specifically for evaluation-path edits, monkeypatching (timers, `sys.exit`, operator overloading), symlinks to reference outputs, and data-path changes.
