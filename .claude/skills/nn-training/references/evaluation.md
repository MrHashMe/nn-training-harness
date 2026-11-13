# Evaluation: harnesses, contamination, judges, comparing models, generated text

Checked: 2026-11-11 (judge estimates, seed escalation: 2026-11-12)
Refresh: re-check on PyPI the pinned versions (lm-eval, sacreBLEU, inspect-ai), the lm-eval release notes and the
open advisories for `datasets` and LiteLLM; re-run scouting (`scouting.md`) for error-bar and judge guidance.

Read when you add or change an evaluator or metric, pick a harness, compare variants beyond seed pairs, score
generated text, or must say whether a benchmark may be contaminated. Seeds, pairing and the noise floor stay in
`uncertainty.md`; the sealed test set and the evaluator freeze stay in `validity.md`; this file adds to both.

A new package needs the user's approval before it is installed. The project's frozen evaluator stays the judge of
record: a harness named here is added beside it, under a new protocol version, never swapped in silently.
Tags: (I) inferred during the research for this file, (U) unverified. Untagged claims were read in the cited source.

## 1. Deciding keep or revert
With 3 pairs the smallest exact one-sided p is 0.125; 4 pairs give 0.0625, 5 pairs 0.031 (I, hand-computed).
- Decision by code. When: any keep or revert from seed pairs. How: code, not your prose, prints KEEP, REVERT or
  INCONCLUSIVE from per-seed paired differences, a margin and error level declared before the runs, and logs its
  inputs (in a campaign `nnloop` decides this way: `loop.md`).
  Risk: wrong statistics get trusted blindly, so test the code on known vectors. Agents often misread statistics.
  (source: https://arxiv.org/html/2611.06607, 4 Nov 2026; single author)
- Exact sign-flip test plus t table. How: enumerate all 2^n sign flips; the t-test can pass at 3 pairs only if t > 2.92
  (I); say which test ran. Risk: t assumes near-normal differences; the exact test cannot pass below 5 pairs at 0.05.
  (source: https://ar5iv.labs.arxiv.org/html/2103.03098, MLSys 2021)
- A/A calibration. When: before a loop. How: split 6 or more baseline seeds into pseudo-candidates and count KEEPs
  from the rule; that is its false-keep rate here (I). Risk: needs the extra baseline runs.
  (source: https://arxiv.org/abs/2512.21326, 24 Dec 2025)
- Fresh-seed confirmation. When: before the test set. How: final kept configuration against the original baseline on
  unused seeds, one comparison. The best of N null variants sits 1.54 SD (N=10), 2.25 (N=50), 2.51 (N=100) high (I).
  Risk: doubles confirmation seeds. A matched search control explained about 60% of one gain (single author).
  (source: https://arxiv.org/abs/2611.11342, 8 Nov 2026)
- Small-sample intervals and Holm. How: Wilson interval for proportions; no bootstrap interval below 100 items, no
  statistics below 15 (preprint; percentile bootstrap covered 88%, BCa 82%); no normal interval below a few hundred;
  Holm step-down for a fixed set of variants; in a loop print the chance gain of the best of N null variants
  (SD figures above times the standard error; 0.80 on 1,000 items: +2.8 points at N=50, I). Risk: needs test vectors.
  (source: https://arxiv.org/html/2609.35815, 20 Sep 2026)

## 2. Reusing a validation set (adds to validity.md section 5)
- Ladder threshold. How: keep only if the candidate beats the best score by more than a step; step s/sqrt(n), s = SD of
  per-item loss differences against the current best (about 0.15 one-sided level; the paper calls it a heuristic).
  Risk: loose worst-case bound; too large a step blocks real gains. The mechanism was partly written from
  memory: check the paper before relying on the formula.
  (source: https://ar5iv.labs.arxiv.org/html/1502.04585, ICML 2015)
- Fixed budgets. How: cap decisions and keeps per protocol version before the loop; at the cap the loop pauses and only
  confirmation remains; a spent budget is never a success. The source tested 50 queries, 7 keeps.
  (source: https://arxiv.org/html/2606.11045, 9 Jun 2026)
- Hidden shadow split. How: a second validation split in `sealed_paths`, scored only by the harness on a candidate that
  passed the dev gate; never print its value; report the dev-to-shadow gap. Risk: costs validation data and one
  evaluation per keep; only as hidden as the guard makes it, since a script you write can open any file you can read.
  (source: https://benchmarks.bespokelabs.ai/autoresearchexam/, 9 Sep 2026)
- Three-way split (train / search / selection, 80/10/10). How: the harness holds the search and selection labels and
  alone scores; the agent never self-reports metrics. Risk: 20% of data held back; small parts are noisy; the paper's
  text and table disagree on the size of the gain; it ran on 8 large GPUs.
  (source: https://arxiv.org/abs/2603.26499, 13 Apr 2026)
- No gold labels or per-item validation results in evaluator output you can read (unattended mode). How: per-item
  detail goes to a sealed file; failure reports show inputs and predictions only; tell the agent a held-out set exists;
  fresh clone per replicate; audit agent memory after each run. One agent hardcoded 19 to 41 item ids per run when
  reports echoed expected ids. Risk: less error analysis; attended mode needs an explicit exception.
  (source: https://arxiv.org/html/2607.18064v2, 27 Aug 2026)
- Evaluator locking. How: the harness re-scores each candidate with a pristine evaluator copy outside the writable tree,
  records hash changes, compares trusted and reported scores. Scripted attacks: 1.00 unlocked, 0.00 with both defences;
  natural-tamper rate (about 0.5) comes from two weak models. Risk: +25 to 31% runtime; misses hash-preserving tricks.
  In a campaign `nnloop` checksums the frozen evaluator every iteration and scores in its own process (`loop.md`).
  (source: https://arxiv.org/abs/2603.11337, 11 Mar 2026)

## 3. Harnesses, settings, generated text
- Evaluation-settings manifest. How: record harness, task and task version, backend, dtype, batch size, device and GPU
  count, seeds, few-shot count, chat-template flag, system-prompt hash, generation arguments, answer-extraction rule,
  sample limit (empty for reported numbers), dataset revision; refuse to compare runs that differ, and likewise runs
  whose evaluator hash, data-manifest hash or protocol version differ. Batch 1/5/32 gave 0.3215/0.3183/0.3023 on one
  MMLU task; implementations gave 0.636 versus 0.488 for one model.
  (source: https://github.com/EleutherAI/lm-evaluation-harness/issues/879, checked 2026-11-11)
- Repeat and batch-size check (adds to validity.md section 4, check 6). How: evaluate one checkpoint twice and at two
  batch sizes; that spread is the evaluation noise; above tolerance, pin batch size and dtype first. Risk: 3 evals.
  (source: https://github.com/EleutherAI/lm-evaluation-harness/issues/3357, checked 2026-11-11; user report, about 0.4%)
- Re-baseline on upgrade. When: any change of harness, task or dataset-loader version. How: new protocol version, rerun
  the baseline. lm-eval 0.4.13 fixed few-shot leakage, a filter that mis-scored answers, and group error bars up to
  about 3 times too narrow; `datasets` 4.0.0 removed loading scripts and `trust_remote_code`.
  (source: https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.13, 31 Aug 2026)
- lm-evaluation-harness 0.4.13 (optional module). When: local Hugging Face models; log-likelihood, multiple choice,
  perplexity, generation. How: own venv, pin `lm-eval==0.4.13` (MIT, Python 3.10+), backend as an extra,
  `--log_samples`; set what the hf backend defaults (`max_gen_toks` 256, `dtype="auto"`, `batch_size=1`); no `--limit`
  for reported numbers; keep `--confirm_run_unsafe_code`, `--trust_remote_code`, `--include_path`, `--plugins`
  off. Risk: brings `datasets` and `dill`; trove status Alpha; native Windows untested (U); 0.5.0.dev1 is a pre-release.
  (source: https://pypi.org/pypi/lm-eval/0.4.13/json, 31 Aug 2026)
- Perplexity. How: compare only with the same tokenizer and windowing, or report bits per byte; record tokenizer hash
  and stride (GPT-2 large, WikiText-2: 19.44 disjoint chunks, 16.44 at stride 512).
  (source: https://huggingface.co/docs/transformers/perplexity, checked 2026-11-11)
- sacreBLEU 2.6.0 (optional) and ROUGE. How: report sacreBLEU's signature with every score (common BLEU configurations
  differ by up to 1.8 BLEU); record ROUGE package, version and options (most reported ROUGE was irreproducible).
  Risk: overlap metrics correlate poorly with human ratings.
  (source: https://pypi.org/pypi/sacrebleu/2.6.0/json, 12 Jan 2026)
  (source: https://aclanthology.org/2023.acl-long.107/, ACL 2023)

## 4. Contamination
Pretraining contamination cannot be reliably detected; disclose what was not checked and prefer fresh data.
- Split-overlap check (standard library). How: hash normalised items for exact matches, word n-gram shingle Jaccard
  for near matches, train against each evaluation split; counts and threshold go in the protocol record; rerun on every
  data change. Risk: quadratic without MinHash; misses semantic duplicates (76% of CodeForces and 100% of MBPP items
  had them in one corpus; gains up to 22 points).
  (source: https://arxiv.org/abs/2602.12413, 7 Nov 2026)
- Temporal split. When: data has dates. How: evaluate on data newer than the training data and the model's cutoff;
  state both dates. Risk: not a guarantee; 17 to 29% of post-cutoff claims in one domain were answerable earlier.
  (source: https://arxiv.org/abs/2607.23514, 26 Jul 2026)

## 5. Optional evaluation modules
- Isolation. How: one venv per module, exact pins with hashes, code-running flags off in unattended mode, no pickle
  data from untrusted sources. LiteLLM 1.107.0 carried a credential stealer on 21 Oct 2026 (1.106.2 and earlier clean);
  `datasets` through 5.1.0 has CVE-2026-57845 (code runs when a pickle loads; see `data.md` section 6).
  Risk: disk and install time; pins age.
  (source: https://cveawg.mitre.org/api/cve/CVE-2026-57845, 23 Oct 2026)

## Model judges and the tools agents reach for
- No judge is adopted: a model judge is not a keep-or-revert metric without human calibration, and statistics on raw
  judge scores inflate false positives. Where an exact scorer exists, use it. See the candidates below.
- Do not reach for: HELM (maintenance mode since 1 June 2026), simple-evals (frozen), DeepEval 4.3.3 (application
  testing, telemetry dependencies), lighteval 0.13.0 (no release in 12 months),
  OpenCompass 0.5.5 (pins `numpy<2`, `transformers<5`, `datasets<4`),
  LiteLLM-routed evaluation (compromised release), ppi-python 0.2.3 (last release Dec 2024).
- Nor: membership-inference detectors (near chance), lm-eval 13-gram decontamination (needs a local Pile copy),
  low-star contamination scanners (Bench-B, BenchBloom: look-alike clones), Thresholdout and rotating splits.

## Candidates to test, not adopted
- Decision-only or rounded feedback, unattended: (source: https://arxiv.org/html/2606.11045, 9 Jun 2026)
- Staged seed escalation: built into the loop on 2026-11-12 as one second seed panel for a near-miss, decided
  more strictly (`loop.md`, "The keep rule"; source: the kit's own simulation of that date; in the one live
  campaign since, the keep it made was `unclear` on fresh seeds).
  For comparisons by hand it stays a candidate.
- Per-item scores, McNemar, clustered error, power:
  (source: https://ar5iv.labs.arxiv.org/html/2411.00640, 1 Nov 2024)
- Contamination disclosure fields: (source: https://arxiv.org/abs/2608.29463, 6 Nov 2026)
- Inspect AI 0.3.289 with inspect-evals 0.28.0: (source: https://pypi.org/pypi/inspect-ai/0.3.289/json, 10 Nov 2026)
- Certified promotion accounting (REUSE): (source: https://arxiv.org/html/2609.33180v2, 29 Sep 2026)
- LLM judge behind a calibration gate (30+ human labels, squared correlation 0.4+, one preprint):
  (source: https://arxiv.org/html/2609.35815, 20 Sep 2026). If a judge is used at all, report it as a bias-corrected
  estimate from that human-labelled set, with an interval that covers the test items and the calibration set; a raw
  judge score is never a keep rule. Methods papers by their authors, no replication found.
  (source: https://arxiv.org/abs/2511.21140, v4 31 May 2026; https://arxiv.org/abs/2601.05420, 8 Jan 2026;
  read 2026-11-12)
