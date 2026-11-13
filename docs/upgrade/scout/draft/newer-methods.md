# Newer methods against the kit's defaults

Date: 2026-11-12. Method: 17 web searches (dated queries) and 17 primary pages opened (arXiv abstract pages, GitHub
READMEs). Page text was treated as data; no page contained text addressed to an agent. Search-engine summaries were
wrong at least once (one summary called arXiv 2604.11554 a replication of the FP16 paper; the page says nothing of
the kind), so every claim below is marked "opened" or "not opened". Nothing was installed or run.

Result in one line: no newer method has displaced a default on evidence that meets the Adopt rule. One reference
sentence is wrong (gradient clipping), one internal inconsistency needs a decision (pairing by seed), and eight
candidates deserve a test.

## Defaults the files give (one line each, file and section)

- Optimizers and schedules: tuned AdamW + short linear warmup + linear decay to zero (optimization.md, Adopted
  practices); Muon, Schedule-Free, SOAP, WSD held as candidates (optimization.md, Candidates); Lion, AdEMAMix, MARS
  held (optimization.md, Held).
- Scaling and transfer: AdamW timescale rule; sqrt batch rule; muP/CompleteP as candidates (optimization.md).
- Clipping and stability: no clipping default; "log pre-clip norm and clipped fraction"; "nothing new found"
  (optimization.md, intro and Held).
- Precision, compile, memory, throughput: bf16 autocast, TF32, fused AdamW, compile behind a numerics gate,
  adoption rule = end-to-end time-to-target (performance.md, sections 3, 4, 8).
- Fine-tuning: LoRA on all linear layers, LR tuned per arm, variants not defaults (finetuning.md, LoRA); GRPO in TRL
  with mismatch diagnostics (finetuning.md, RL post-training); DPO/KTO stable, compare on own evaluator (llm.md,
  Instruction and preference tuning); template preflight table (llm.md).
- Hyperparameter search: Optuna 5, QMC/random up to ~30 trials, TPE 100+, pruners only after a rank gate, fresh-seed
  confirmation of top 3 (hpo.md, sections 2 to 8).
- Data: exact cross-split audit, report-only dedup, random-drop control, synthetic = add to real, frozen data gate
  (data.md, sections 2, 3, 7); embedding tools are optional candidates (SemHash) (data.md, Candidates).
- Evaluation: frozen evaluator, settings manifest, no judge adopted, judge behind a calibration gate (evaluation.md,
  sections 3 and "Model judges"; llm.md, Evaluating generated text).
- Statistics: k = 3 to 5 seeds, paired differences, retain if mean gain > noise floor and all signs agree, 3-pair
  retain is only a candidate, confirm on fresh seeds (uncertainty.md, section 2; evaluation.md, section 1).
  Unattended loop: gain > t x pooled sd x sqrt(2/n), then confirmation on fresh seeds (loop.md, The keep rule).
- Distributed: DDP if it fits, FSDP2 with DCP, rank-0 files, all-reduced stop flag (performance.md, section 6;
  resume.md, section 2); single-worker DiLoCo held (optimization.md, Held).
- Reproducibility: determinism as a measured hypothesis, hash the rendered prompt, vLLM reproducible only on same
  hardware and version (operations.md, section 1; llm.md).

## Optimizers and schedules, scaling and transfer

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| Muon as controlled alternative (optimization.md, Candidates) | None newer found; the 2026 papers the kit cites remain the evidence | Search found original-author and vendor numbers only; one small independent blog check says stay with AdamW below 8 GPUs (search-level, not opened). 2607.20548 (SOAP, Muon, beyond; 24 Jul 2026) reports AdamW unstable at large batch; kit already cites it. No independent large-scale reproduction found | no change | none |
| AdamW timescale and sqrt batch rules (optimization.md) | 2608.20061 MoE hyperparameter transfer (Aug 2026): Muon LR scaled by 0.2 sqrt(max(A,B)) to reuse AdamW values | search snippet only, not opened; MoE | no change (note it) | none |
| Linear decay, WSD (optimization.md) | nothing newer found | not applicable | no change | none |

## Gradient clipping and stability

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| "nothing new on ... gradient clipping: keep what the project does and log the pre-clip norm and the clipped fraction" (optimization.md, intro); global-norm clipping not a blanket default (Held) | AdaGC, per-tensor clipping against a tensor-wise EMA of past clipped norms | arXiv 2502.11034, v1 16 Feb 2025, v4 19 Jul 2026, ICML 2026 (opened). Llama-2 7B, Mixtral 8x1B, ERNIE 10B-A1.4B; spike score to zero; downstream accuracy +1.32, +1.27, +2.48 points over global clipping; also with Muon and Lion. Authors only; code in PaddleFleet (PaddlePaddle). No independent replication seen; review note says runs were short | name it as a candidate to test | In optimization.md intro replace "nothing new on initialization, normalization or gradient clipping" with "nothing new on initialization or normalization; for gradient clipping see AdaGC below". Add under Candidates: "AdaGC: per-tensor adaptive clipping, ICML 2026, authors' runs at 7B to 10B-A1.4B on PaddlePaddle only; test against global-norm clipping on a run that shows clipped-fraction spikes. (source: https://arxiv.org/abs/2502.11034, v4 2026-07-19)" |

## Precision, compilation, memory and throughput

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| bf16 autocast + TF32 (performance.md, section 3); low-bit only torchao optimizers (section 8) | NVFP4 / MXFP8 training | NVFP4: 2509.25149 v2 4 Mar 2026 (opened): 12B on 10T tokens, "comparable to FP8", no code or hardware stated, no replication. Full-Stack FP4 2607.04422 v2 7 Aug 2026 (opened): 3B, 64B tokens, loss gap 0.838% to BF16, code not linked, authors say longer horizons not shown. MXFP8: torchao and PyTorch blogs, 1.2x to 1.3x on B200/GB200, vendor-measured (search-level, not opened) | name it as a candidate to test, Blackwell-class GPU only | Add to performance.md section 8: "Low-precision training (MXFP8 via torchao, NVFP4): vendor-measured 1.2x to 1.3x on B200-class GPUs, convergence checks short, needs Blackwell; run only behind the numerics gate and the end-to-end adoption rule. (source: https://arxiv.org/abs/2509.25149, v2 2026-03-04; https://arxiv.org/abs/2607.04422, v2 2026-08-07)" |
| Deterministic mode costs speed (performance.md, section 7) | Batch-invariant ops (Thinking Machines) | GitHub README opened: MIT, torch.Library overrides for mm, addmm, log_softmax, mean; inference proof of concept; no training use stated. Overhead figures (about 34 to 61%) are from search results, not opened | no change; assess for RL rollout/eval reproducibility | none |
| PyTorch 2.15 FSDP2 / NCCL rewrite | search-level only | not opened | no change | none |

## Fine-tuning of language models

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| GRPO diagnostics incl. `sampling_logp_difference`; mismatch "can destabilise" (finetuning.md, RL post-training) | FP16 instead of BF16 for trainer and rollout | 2510.26788, 30 Oct 2025, v1 only, no venue (opened): authors report mismatch about 24x lower and stable runs where BF16 collapsed; models and scale not on the abstract page; no code link; no independent replication found | name it as a candidate to test | Add to finetuning.md RL section: "If `sampling_logp_difference` is large or training collapses, test FP16 for trainer and rollout against BF16 (single preprint, no replication). (source: https://arxiv.org/abs/2510.26788, 2025-10-30)" |
| same | "Fair Cast": stochastic rounding or error feedback when exporting bf16 rollout weights | 2610.41073, 29 Oct 2026, v1 (opened): Qwen3-0.6B to 4B, 25 seed pairs, wins 18 / ties 6 / loses 1, mean +6.1 points; zebra puzzles 0.57 +- 0.16 vs 0.33 +- 0.10 over 4 runs; no code link; two weeks old | name it as a candidate to test (low confidence) | Add one line under finetuning.md Candidates: "bf16 rollout copy rounds away most small updates; stochastic rounding of the exported copy (2610.41073, v1, no code, no replication)." |
| LoRA variants not defaults (finetuning.md) | Hybrid-LoRA (full tune of few modules + LoRA) | 2605.18822: Qwen-2.5 1.5B, GRPO and GSPO, self-reported +4.36% over best PEFT baseline (search-level, not opened) | no change | none |
| DPO/KTO stable, compare on own evaluator (llm.md) | SimPO and other DPO variants | Independent benchmark described by PORT (2406.16061) found DPO not beaten after tuning (search-level, not opened); no 2026 controlled comparison found | no change | none |

## Hyperparameter search

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| TPE/QMC/random; LLM share capped (hpo.md, sections 3, 8) | LLM-guided HPO | 2606.21641 (search-level, not opened): budget-matched, 8 tabular sets, the warm start was the default configuration; 2603.24647 already cited. Nothing found that beats TPE at 30 trials | no change | none |

## Data

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| Report-only dedup; MinHash optional; SemHash candidate (data.md, sections 3, Candidates) | embedding clustering / diversity selection | Findings of EMNLP 2025 (search-level, not opened): random selection hard to beat at scale; diversity usually beats quality scoring, costly. H3D benchmark 2607.08382 (not opened): MinHash best set-overlap fidelity. No paper found that beats MinHash and SemDeDup on held-out accuracy | no change | none |
| Synthetic data: add, never replace (data.md, section 7) | accumulate-not-replace literature | Gerstgrasser et al. 2024 as summarised by 2026 blogs (not opened); "10% / 20-30% real" thresholds are blog heuristics, not evidence | no change; do not add thresholds | none |

## Evaluation of models and generated text

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| Judge only behind a calibration gate: 30+ human labels, squared correlation 0.4+, one preprint (evaluation.md, Candidates; llm.md) | Sensitivity/specificity-corrected intervals with calibration-set uncertainty (2511.21140, ICML 2026, v4 31 May 2026, opened: no code link on the page, no numbers on the abstract) and PPI/efficient-influence-function estimators (2601.05420, v1 8 Jan 2026, opened: code at yiqunchen/debias-llm-as-a-judge) | Methods papers by the authors; no independent replication seen; 2601.05420 reports narrower intervals than plain PPI only in the search snippet (35 to 55%, not opened) | name it as a candidate to test | Replace the last Candidates line of evaluation.md with: "LLM judge reported only as a bias-corrected estimate with a human-labelled calibration set (30+), interval covering both test and calibration uncertainty; raw judge scores are never a keep rule. (source: https://arxiv.org/abs/2511.21140, v4 2026-05-31; https://arxiv.org/abs/2601.05420, 2026-01-08)" |

## Statistics for comparing runs (three to six seeds)

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| "Compare with paired designs", same seeds (uncertainty.md, section 2); but the keep rule is unpaired and "runs are not compared seed by seed ... seeds did not shift scores consistently" (loop.md, The keep rule) | Paired seeds as common random numbers | 2512.24145 (opened): single author, simulator, strict variance reduction only when seed-level outcomes correlate positively, no numbers on the page, no code, no replication. 2609.24144 (opened, 21 Sep 2026): paired rollouts need not lower gradient variance; 2B agent, 3 seeds, learning-curve criterion missed; code at TheDeadcoder/paired-rollouts. Net: gain depends on cross-arm seed correlation, which nobody has shown for neural-net training | no change to the rule; resolve the inconsistency by measuring the correlation | In uncertainty.md section 2 after the report line add: "Pairing by seed helps only when baseline and candidate scores correlate across seeds. Measure that correlation once on the baseline panel (A/A split) before relying on pairing; if it is near zero, use the unpaired rule in `loop.md`. (source: https://arxiv.org/abs/2512.24145, v3 2026-01-31; https://arxiv.org/abs/2609.24144, 2026-09-21)" |
| 3-pair retain is a candidate; staged seed escalation "inferred, no source" (evaluation.md, Candidates) | Anytime-valid t-test / e-process on per-seed differences, so 3 seeds can be extended to 6 without inflating the error | Wang and Ramdas, arXiv 2310.03722 v5 6 Nov 2024, Sequential Analysis (opened): closed-form e-process with unknown variance; width polynomial in alpha, "unavoidable". Pérez-Ortiz et al., Annals of Statistics 52(4), Aug 2024 (search-level): group-invariance basis. Python packages `savvi`, `ville` exist (not opened). Nothing found on power at n = 3 to 6, none on neural-net seeds. Expected: an e-value cannot reject at 0.05 with 3 pairs unless the effect is large | name it as a candidate to test | Replace "Staged seed escalation, error level split across looks: (source: none; inferred...)" in evaluation.md with: "Staged seed escalation with an anytime-valid t-test on per-seed differences (e-process, valid under extension from 3 to 6 seeds); power at n = 3 to 6 not shown, simulate before use. (source: https://arxiv.org/abs/2310.03722, v5 2024-11-06)" |
| Pooled variance across panels (loop.md) | Variance carried across experiments by other means (empirical Bayes, hierarchical) | Searched; nothing for neural-network training with few seeds found. The kit's own pooled estimate stands | no change | none |
| Seed vs item uncertainty (uncertainty.md, section 2 last line) | RecSys '26 "More Test Users, More Overconfidence" | Search-level, not opened: item-level paired tests reached 80% rejection on null comparisons, run-level tests stayed near 5%. Supports the kit's existing line | no change | none |
| Seed counts for RL post-training | 2610.04928 (not opened): two seeds of one variant differed as much as the variants | Supports existing "at least 3 seeds" | no change | none |

## Distributed training and reproducibility

| Kit today | Newer candidate | Evidence | Verdict | Exact text change |
|---|---|---|---|---|
| DDP/FSDP2; single-worker DiLoCo lowest score (optimization.md, Held) | Streaming / Decoupled DiLoCo (2501.18512, 2604.21428) | search-level only; multi-datacentre aim, not single-box | no change | none |
| Determinism = measured hypothesis (operations.md, section 1) | Batch-invariant kernels, DeepSeek-V4 end-to-end deterministic kernels (2606.19348) | not opened (V4 claim); batch_invariant_ops opened, inference only | no change | none |

## Areas where nothing newer was found

- Optimizer ranking (no independent evidence moved Muon, SOAP or Schedule-Free); learning-rate schedules; warmup.
- Hyperparameter search methods and pruners.
- Deduplication and embedding-based selection (nothing beats exact/MinHash/SemHash on held-out accuracy).
- Synthetic-data mixing thresholds.
- Preference tuning (no 2026 controlled comparison against DPO found).
- Chat-template and tokenizer preflight; PEFT variants (kit's own 1 to 2 percent finding stands).
- Distributed training beyond one machine; carrying variance estimates across experiments with few seeds.

## Not opened or not verified

- All search-level items marked above: 2605.18822, 2606.21641, 2607.08382, 2406.16061, 2610.04928, 2606.19348,
  2604.21428, 2501.18512, 2608.20061, the RecSys '26 paper (DOI page redirected to ACM, not fetched), EMNLP 2025
  data-selection paper, Gerstgrasser et al., torchao/PyTorch MXFP8 blogs, PyTorch 2.15 blog, Pérez-Ortiz et al.
- `savvi` and `ville` on PyPI: names seen in search results only; contents, licences and maintenance unchecked.
- AlgoPerf leaderboard entries: the README points to a separate repository (mlcommons/submissions_algorithms),
  which was not opened; v1.0 is the active version.
- Paper bodies: only abstract pages were read, so scale, seeds and baselines beyond the abstract are unverified for
  every opened arXiv item (notably 2510.26788, whose models were not on the page).
- The kit's own cited papers (2610.13036, 2609.23055, 2607.16169, 2512.22382 and others) were not re-checked.
- Skipped by instruction: e-means, Complete(d)P, FOREAGENT, Dion3, ZClip, Cut Cross-Entropy, Liger-Kernel, rank
  confidence sequences, Thresholdout, AgentX-Model, WilcoxonPruner, Trackio.
- Anything under docs/upgrade/scout/scouts/ was not read. The 15 reference files were not all read in full:
  scouting.md, stack.md, remote.md and validity.md were only grepped or not read; docs/TRAINING_GUIDE.md was grepped.
