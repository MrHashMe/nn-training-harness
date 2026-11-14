# Optimization: optimizers, schedules, warmup, weight decay and scaling rules

Checked: 2026-11-11 (gradient clipping: 2026-11-12; cautious weight decay and the two Muon variants: 2026-11-14)
Refresh: re-read the cited papers and the PyTorch optimizer docs of the installed version; scout the AlgoPerf rolling
leaderboard (https://github.com/mlcommons/algorithmic-efficiency) for newer optimizer results.

Read when you choose or change an optimizer, learning-rate schedule, warmup, weight decay or AdamW betas, or when
batch size, GPU count, accumulation steps or training length changes.

Every item here is a hypothesis to test under the project's protocol (one change, declared budget, paired seeds,
a margin above the noise floor) against a tuned AdamW baseline, not a default to switch on. Rankings change within
months and differ by domain: Schedule-Free AdamW ranked first in AlgoPerf v1 and last on all four diffusion tasks
(source: https://arxiv.org/abs/2610.13036, 9 Oct 2026; https://arxiv.org/abs/2609.23055, 19 Sep 2026). No optimizer
has replaced a tuned AdamW or NAdamW baseline across domains. Most evidence is language-model pretraining; the
research for this file found no fine-tuning evidence for optimizers and nothing new on initialization or
normalization. Gradient clipping: keep what the project does and log the pre-clip norm and the clipped fraction; two
adaptive schemes are candidates below.

## Adopted practices
- Tuned AdamW baseline. When: always, as the reference every challenger must beat. How: `torch.optim.AdamW` (PyTorch
  2.15.0; defaults lr 1e-3, betas (0.9, 0.999), eps 1e-8, weight_decay 0.01); tune LR, weight decay, warmup and decay;
  give it the same tuning budget and seeds as the challenger. Decay per step is `lr * weight_decay`, so an LR schedule
  also scales the decay; `fused` is not the default in 2.15. The second-ranked AlgoPerf v1 entry was effectively a
  tuned AdamW. Cost: tuning runs. (source: https://arxiv.org/abs/2610.13036, 9 Oct 2026;
  https://docs.pytorch.org/docs/2.15/generated/torch.optim.AdamW.html, 2026-11-11)
- Linear decay to zero. When: fixed step budget. How: warmup, then decay linearly to 0 at the last step. It beat
  warmup plus cosine-to-10% at the best peak LR; about 60% compute saved in one comparison, language models only.
  Risk: needs the total step count; a run stopped early ends at a high LR.
  (source: https://arxiv.org/abs/2502.15938, ICLR 2025)
- Short linear warmup. When: AdamW-family and matrix optimizers. How: keep a warmup phase; no newer result removes the
  need. Risk: none found. (source: https://arxiv.org/abs/2410.23922, NeurIPS 2024)
- AdamW timescale rule. When: batch size, GPU count, accumulation steps or the data budget changes. How: weights average
  the last `1/(lr*wd)` steps; with `tau = B/(lr*wd*D)` (B batch, D data) the best tau falls as tokens per parameter
  grow. When batch changes, adjust weight decay, not LR alone; for a longer budget, shorten tau. Beta2, epsilon and any
  weight EMA are confounded by a batch change too (inferred). Risk: GPT-2-like models, 111M to 3.3B only; numbers came
  through a summariser, so re-read before quoting. (source: https://arxiv.org/abs/2505.13738, NeurIPS 2025;
  https://arxiv.org/abs/2405.13698, ICML 2025)
- Equal-budget comparison. When: any optimizer or schedule claim. How: same tuning budget and seeds for baseline and
  challenger; retrain winners at full budget with at least 3 seeds; add an AdamW run with matched update RMS, because
  that control removed Muon's gain in agentic RL. In AlgoPerf, LR and momentum were the most influential settings.
  Cost: more runs per claim. (source: https://arxiv.org/abs/2609.23055, 19 Sep 2026;
  https://arxiv.org/abs/2607.16169, 2 Aug 2026)
- AlgoPerf rolling leaderboard. When: scouting only. How: read it, no dependency; current entries were not checked.
  (source: https://github.com/mlcommons/algorithmic-efficiency, checked 2026-11-11)

## Candidates to test, not adopted
Run each as one change under the protocol above.
- Muon, `torch.optim.Muon` (PyTorch 2.9+; bf16 momentum-aliasing fix in 2.15.0, scope inferred): 2-D hidden weights
  only, AdamW for embeddings, heads, norms, biases. About 1.4x with correct width scaling of LR and weight decay
  (190M to 1.4B), vanishes under wrong scaling; vendor-measured at 8B to 72B; kept 47% of its per-workload score under
  one fixed configuration in AlgoPerf; convolution weights did better with AdamW. FSDP2 use is undocumented
  (unverified). `Muon(params, lr=0.001, weight_decay=0.1, momentum=0.95, ns_steps=5, adjust_lr_fn=None)`;
  `"match_rms_adamw"` eases LR transfer. (source: https://arxiv.org/abs/2512.05620, 18 Jan 2026;
  https://arxiv.org/abs/2607.20548, 13 Jul 2026; https://docs.pytorch.org/docs/2.15/generated/torch.optim.Muon.html)
- Muon variants, each its authors' result with no replication found. Polar Express replaces the fixed Newton-Schulz
  coefficients with ones chosen per step (GPT-2 on 1B to 10B tokens, lower validation loss across learning rates).
  NorMuon normalises each row after the orthogonalisation with a second-moment estimate (at 1.1B: 21.74 % better
  training efficiency than Adam and 11.31 % than Muon, by its abstract). `torch.optim.Muon` has neither: in 2.9.1
  it takes one coefficient triple, `ns_coefficients`, for all `ns_steps`. (source: https://arxiv.org/abs/2505.16932,
  v5 4 May 2026; https://arxiv.org/abs/2510.05491, 7 Oct 2025; abstract pages read 2026-11-14)
- Cautious weight decay: the decay acts only on the coordinates where its direction agrees with the optimizer's
  update, and the authors argue that the unmodified loss is then what gets optimised. A one-line change to AdamW,
  Lion or Muon; they report better final loss and accuracy in language-model pretraining and on ImageNet, millions
  to billions of parameters. No code on the page read, no replication found. It is not the masked update of the
  Cautious optimizers held below. (source: https://arxiv.org/abs/2510.12402, v2 24 Feb 2026; abstract page read
  2026-11-14)
- Warmup-stable-decay with a square-root-style cooldown: used for 8B to 72B runs; the preferred schedule can reverse
  with training length. (source: https://arxiv.org/abs/2607.20548, 13 Jul 2026; https://arxiv.org/abs/2609.04577,
  4 Sep 2026)
- Square-root batch rule for Adam: batch x k means LR and weight decay x sqrt(k), epsilon / sqrt(k), (1-beta1) and
  (1-beta2) x k; autoregressive transformers only. (source: https://arxiv.org/abs/2512.22382, ICLR 2026)
- Beta2 with a constant half-life in tokens for small batches; the authors advise against accumulation on one device.
  (source: https://arxiv.org/abs/2507.07101, NeurIPS 2025)
- Weight EMA with batch-aware momentum (the formula is from memory, unverified); state which weights the evaluator
  scored. (source: https://arxiv.org/abs/2307.13813, NeurIPS 2023; https://arxiv.org/abs/2604.15297, Apr 2026)
- SOAP and KL-Shampoo (NVIDIA Emerging-Optimizers v0.5.0; all APIs experimental, source install). (source:
  https://github.com/NVIDIA-NeMo/Emerging-Optimizers, 10 Nov 2026)
- Schedule-Free AdamW (`schedulefree` 1.4.1): call `optimizer.train()` and `.eval()` with the model, evaluate and save
  in eval mode, recompute batch-norm statistics, beta1 0.95 or 0.98 for long runs.
  (source: https://github.com/facebookresearch/schedule_free, 1.4)
- Adam with beta1 equal to beta2. (source: https://arxiv.org/abs/2505.21829, NeurIPS 2025)
- Width and depth aware transfer (muP, CompleteP, Complete(d)P); proxies below about 136M carried a penalty.
  (source: https://arxiv.org/abs/2512.22382, ICLR 2026)
- Adaptive gradient clipping, for a run whose log shows loss spikes or bursts in the clipped fraction; compare with
  the project's global-norm clipping on the same seeds. AdaGC clips each tensor against a moving average of its own
  past norms: the authors report no spikes and 1.3 to 2.5 points over global clipping at 7B to 10B, in short runs,
  with code for PaddlePaddle only and no independent replication. ZClip clips when the global norm is an outlier
  against its moving statistics (`z_thresh=2.5`, `alpha=0.97`, 25 warmup steps); authors' runs only.
  (source: https://arxiv.org/abs/2502.11034, v4 19 Jul 2026, ICML 2026; https://arxiv.org/abs/2504.02507, 3 Apr 2025;
  https://github.com/bluorion-com/ZClip, read 2026-11-12)

## Held or rejected: do not reach for these
- Lion: near the bottom in AlgoPerf v1, diverged on one diffusion task, trails Adam after tuning.
  (source: https://arxiv.org/abs/2610.13036, 9 Oct 2026)
- AdEMAMix, Cautious optimizers (the masked update of C-AdamW and its kin), MARS and MARS-M, Dion3, SAMuon and
  similar: single-source or no better than plain NAdamW in AlgoPerf v1. Single-worker DiLoCo had the lowest score.
- Global-norm clipping as a blanket default: it can hide a too-high LR unless the clipped fraction is logged.
- Optimizer collections (pytorch_optimizer v4.1.0, HeavyBall v3.2.1): extra supply-chain surface; individual
  implementations not checked. (source: https://github.com/kozistr/pytorch_optimizer/releases, 25 Oct 2026)
