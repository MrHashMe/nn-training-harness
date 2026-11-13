# Third report: claim verification

Date: 12 November 2026. All pages opened on that date (versions as shown on that day). Fetched summaries came from a small model reading the pages, so every quoted number should be re-checked at the URL before it is cited. Limits: about 40 page reads; the tails of three long HTML pages were not read (noted per claim).

## 1. e-means (arXiv 2611.09501)
1. Exists. "e-means: outperforming k-means (in one-tenth the epochs)", Bessa, Mazare, Szilvasy, Touvron, Picard, Douze, Jegou. v1 only, submitted 6 Nov 2026. https://arxiv.org/abs/2611.09501 (12 Nov 2026). Meta FAIR affiliation not checked.
2. Abstract: "1.4 to 2.6 epochs" to beat Lloyd at 25 epochs (report says 1.2: 1.2 appears only in Table 10 for one dataset, N = 1e5); "10-45x GPU wall-clock speedups" matches. Cosine from alpha0 down to 0.1 alpha0: matches (Eq. 5, floor 0.1). Finalisation: paper has "last-epoch-mean" (default) and "slow-EMA" (hyphenated names, not the snake_case strings of the report). "0.3 % against 26.3 %" dead clusters at k = 16,384: figure not found in the paper text read (first 100k of 167k characters; the paper has a revival rule, threshold 0.1) and not in the README. Tail not read.
3. Code: facebookresearch/faiss, `contrib/e_means/` (MIT per file header). FAISS v1.16.0, published 10 Nov 2026, lists e-means commits (https://github.com/facebookresearch/faiss/releases/tag/v1.16.0). README gives no minimum FAISS version. API is a class, not a function: `from faiss.contrib.e_means import Emeans`; `Emeans(d, k, nepochs=5, batch_size=None, alpha0=None, batch_law="auto", ...)`, then `.train(x, init_centroids=None)`, `.assign(x)`; also `NumpyEmeans`, `QuantizedEmeans`, `DistributedEmeans`. `unused_threshold` controls revival (default 0.1 of mean count; 0 for d <= 2). Strings `last_epoch_mean` / `slow_ema` not found in `e_means.py`. https://github.com/facebookresearch/faiss/tree/main/contrib/e_means
4. Conditions: H100 80GB GPUs, CPU runs on Xeon 8462Y+; datasets 1M to 1B (DINO10B 10B embeddings, 16M clusters in 2.5 epochs); scaling laws fitted on DEEP only. Self-noted weaknesses: "No hyperparameter is tuned" while baselines were tuned on validation; small ablation effects; conclusion says "1 to 3 epochs" and "11 million to 11 billion", inconsistent with abstract and tables; a few high-dimension cases where test MSE ends above Lloyd. No independent replication searched (paper is 6 days old).
5. Verdict: partly. Real, code released; epochs lower bound is 1.4 not 1.2; dead-cluster numbers not found; API name wrong (`Emeans`, not a function).

## 2. Complete(d)P (arXiv 2512.22382)
1. Exists. "Completed Hyperparameter Transfer across Modules, Width, Depth, Batch and Duration", Mlodozeniec, Ablin, Bethune, Busbridge, Klein, Ramapuram, Cuturi. v1, 26 Dec 2025, no later version. https://arxiv.org/abs/2512.22382. Parameterisation is called Complete^(d). ICLR 2026 acceptance not verified (not on abs page).
2. "27 %": found in text, Section 3.3: 27 % speed-up to reach equal loss (Figure 1 caption says 1.32x). Not in abstract.
3. Code: no link on the abs page or in the HTML. No repository found (search for one not done).
4. Conditions: per-module search at 50M params, 1.6B tokens; transfer to 1.3B params, 26B tokens; A100, about 6,730 GPU-hours for the search. HTML tail (4k chars) not read. No replication searched.
5. Verdict: confirmed for the figure (27 % at 1.3B/26B only); code not found.

## 3. arXiv 2610.37842
1. Exists. "Improving Data-Constrained Scaling with Hyperparameter Transfer and Ensembling", Baron, Berman, Satheesh, Vegesna, Dahal, Wilson. v1, 27 Oct 2026. https://arxiv.org/abs/2610.37842
2. Abstract: "over 0.15 nats" lower validation loss on 100M FineWeb tokens: matches. Body: M* about 2 + C/C3 with C3 about 4.8e4 x U^1.9; ensembling worthwhile (M* >= 2) above C2 about 1.4e4 x U^1.9. So the report's "threshold C > 1.4e4 x U^1.9" is C2, correct.
3. Code: https://github.com/qlabs-eng/data-constrained-scaling (link stated in paper; repo, licence and release not opened).
4. Conditions: decoder-only transformers 30M to 398M non-embedding params; extrapolation checked 458M to 2.52B and up to 12x compute; fitted on small runs. No replication searched (one week old).
5. Verdict: confirmed.

## 4. FOREAGENT (arXiv 2601.05930)
1. Exists. "Can We Predict Before Executing Machine Learning Agents?", Zheng et al. (8 authors, last Ningyu Zhang). v1 9 Jan 2026, v2 7 Apr 2026; listed as ACL 2026. https://arxiv.org/abs/2601.05930
2. Abstract: 61.5 % accuracy (given a verified data-analysis report; the abstract does not say "pairwise" in the part read, the task is Data-centric Solution Preference over 18,438 pairwise comparisons), "6x faster convergence", "+6 %" over execution-based baselines (abstract does not say points or relative).
3. Code: not checked.
4. Conditions/replication: not opened (full text); no replication searched.
5. Verdict: confirmed on figures; "+6 %" unit unspecified; "pairwise accuracy" wording is the report's reading.

## 5. AgentX-Model (arXiv 2609.30001)
1. Exists. "Advancing Model Research in AgentX: Long-Horizon Autonomy for Industrial Recommender Systems", 23 authors (Shuang Yang first, Wenwu Ou last). v1, 24 Sep 2026 (report says September, fine). https://arxiv.org/abs/2609.30001
2. Abstract: four actions Reproduce, Follow-up, Composition, Diagnose; "560 of 636" completed model-changing experiments had AUC above business baselines (560/636 = 88.05 %, "88.1 %" is the report's arithmetic). Caveat: the criterion is AUC above baseline, not "beat production baselines" in online terms; online A/B gains are reported separately for five tests.
3. Code: none seen on abs page.
4. Conditions: industrial recommender (ads/video platform), proprietary; not reproducible. No replication.
5. Verdict: confirmed with a caveat (offline AUC criterion, proprietary setting).

## 6. Rank confidence sequences (arXiv 2609.32211)
1. Exists. "Rank Confidence Sequences: Anytime-valid Leaderboards", Khosravi and Huo, stat.ME. v1, 26 Sep 2026. https://arxiv.org/abs/2609.32211
2. "30 %" and "51 %": found in body, in a simulation with six equally accurate models inspected 200 times at nominal 5 %: at least one false statement in 30 % of runs, 51 % in the other setting. Not in abstract. Finite benchmark: paper draws one random permutation of the N items, i.e. effectively sampling without replacement (the phrase itself not present). HTML tail (106k chars) not read.
3. Code: https://github.com/HamedKhosravi99/rank-confidence-sequences-supplement (supplement repo, licence not opened).
4. Conditions: simulations plus public leaderboard data. Abstract: little power loss relative to fixed-sample methods when looking at or after the halfway point. No replication.
5. Verdict: confirmed.

## 7. Dion3 (arXiv 2608.11612, microsoft/dion)
1. Exists. "Dion3: Full-Stack Orthogonal Updates", Amsel, Zhang, Ahn, Naeimi, Feng, Chen, Dao, Langford. v1, 12 Aug 2026. https://arxiv.org/abs/2608.11612 ; repo https://github.com/microsoft/dion
2. "26x to 4x of AdamW": found in the paper's Figure 1 / abstract-level text (HTML): Muon cost from 26x AdamW to 4x, for a 7B model on four GH200. The arXiv abstract itself says "up to 6x" less optimizer step time versus Muon, which is a different figure. Paper says Dion3 is still slower than AdamW. Not in the repo README.
3. Code: MIT licence; no releases or tags; README says `nordion2.py` is exported as `Dion3`; last commit date not shown (249 commits).
4. Conditions: 7B on 4 GH200 (Fig. 1); 1B and 14B on 8 or 32 GPUs (Table 1). Second half of the HTML not read. No replication searched.
5. Verdict: confirmed (figure is in the paper, not the abstract; "drop-in replacement" claim is the authors').

## 8. ZClip
1. Paper is arXiv 2504.02507, "ZClip: Adaptive Spike Mitigation for LLM Pre-Training", Kumar, Owen, Chowdhury, Gura (BluOrion), submitted 3 Apr 2025. https://arxiv.org/abs/2504.02507 (via search results; abs page itself not opened). 2502.11034 is AdaGC (Wang et al., adaptive gradient clipping, v1 16 Feb 2025, v4 19 Jul 2026), a different paper. https://arxiv.org/abs/2502.11034
2. Defaults: README table `z_thresh=2.5`, `alpha=0.97` (also `mode="zscore"`, `clip_option="adaptive_scaling"`, `max_grad_norm=1.0`, `warmup_steps=25`). https://github.com/bluorion-com/ZClip
3. Code: Apache-2.0; no release/commit date read (install via git URL, no PyPI claim checked).
4. Conditions/criticism: third-party summaries disagree on sensitivity to z_thresh; no independent study opened.
5. Verdict: partly (wrong arXiv ID in the report; defaults confirmed).

## 9. Cut Cross-Entropy
1. Package `cut-cross-entropy` on PyPI: latest 25.1.1, uploaded 2025-01-07 (earlier 24.12.2, 24.12.3). PyPI licence field empty. Repo https://github.com/apple/ml-cross-entropy has no GitHub releases or tags. (PyPI JSON read; project page not opened.)
2. Variants (`impl`): `cce` (recommended start), `torch_compile`, `cce_kahan`, `cce_kahan_full_c`, `cce_kahan_full_c_full_e` (alias `cce_exact`). The three the report names exist.
3. Licence: LICENSE file is an Apple-specific text ("Copyright (C) 2024 Apple Inc."), not a named standard licence; read it before use.
4. Last release is about 22 months old by 12 Nov 2026 (last commit date not read).
5. Verdict: confirmed (names), with the note that no release since Jan 2025 was found.

## 10. Liger-Kernel
1. Latest release v0.8.5, published 21 Oct 2026 (PyPI 0.8.5; BSD 2-Clause per PyPI). Requires Transformers >= 5.0.0. https://github.com/linkedin/Liger-Kernel/releases/tag/v0.8.5
2. README: "increase throughput by more than 20% and reduce memory usage by 60%". "47 %" not found in README. Example table: LLaMA 3-8B about 20 % faster with over 40 % less memory (4 A100, FSDP); benchmark setup LLaMA 3-8B, bs 8, bf16, AdamW, gradient checkpointing, FSDP1, 8 A100. The paper (arXiv) was not opened, so the 47 % may come from there.
3. Replication: none searched.
4. Verdict: partly ("47 to 60 %" range not found; README says 60 % and 40 %+ depending on example).

## 11. CVE-2026-39861
1. Exists. Anthropic, Claude Code (npm `@anthropic-ai/claude-code`). Sandbox escape via symlink following: sandboxed processes could create symlinks pointing outside the workspace, and Claude Code's unsandboxed process then followed them on write. Affected: all versions before 2.1.64. Fixed in 2.1.64. CWE-22, CWE-61. CVSS 4.0 7.7 (High); GitHub lists CVSS 3.1 10.0. Published 21 Apr 2026. Exploitation generally needs prompt injection.
2. Sources: https://cveawg.mitre.org/api/cve/CVE-2026-39861 ; GitHub advisory GHSA-vp62-r36r-9xqp https://github.com/advisories/GHSA-vp62-r36r-9xqp . NVD page itself did not load (not opened).
3. Verdict: confirmed (best wording: "sandbox escape through symlink following, fixed in 2.1.64"; "workspace escape" is the report's paraphrase).

## 12. Claude Code changelog and hooks
Sources: https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md (top entry 2.1.322, no dates); https://code.claude.com/docs/en/hooks (first 100k of 293k characters read).
- `CLAUDE_CODE_DISABLE_ULTRATHINK`: added in 2.1.316 (turns the `ultrathink` keyword off). Confirmed.
- "From 2.1.318 ultrathink runs at xhigh": wrong version. 2.1.311 changed terminal `ultrathink` to run its turn at xhigh (listed for Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1); 2.1.316 did the same for the VS Code extension; 2.1.317 fixed a VS Code bug. 2.1.318 has no ultrathink entry. Keyword was re-introduced in 2.1.68 (high effort).
- Hook events: all four exist in the docs table (33 events): `PostToolBatch` (after a parallel tool batch, before the next model call; exit 2 stops the loop), `StopFailure` (turn ended by API error; cannot block), `PostToolUseFailure` (after a failed tool call), `PreCompact` (before compaction, matcher manual/auto; exit 2 blocks). Changelog: `StopFailure` added in 2.1.78; `PostToolUseFailure` already present at 2.1.119 (earlier addition not found by name); `PreCompact` appears in a 2.1.314 fix (older); `PostToolBatch` has no changelog entry by that name in the text searched, so its first version is not established.
- Verdict: partly (events and env var confirmed; xhigh version wrong: 2.1.311, VS Code 2.1.316).

## 13. Optuna
1. Major version 5 exists: v5.0.0 published 7 Sep 2026 (rc1 3 Aug 2026). https://github.com/optuna/optuna/releases/tag/v5.0.0 Highlights: multivariate TPE with constant liar default; TPESampler default for multi-objective; `trial.set_constraint()`; PED-ANOVA default importance; GPSampler stable; UTC timestamps (breaking).
2. `WilcoxonPruner`: "Added in v3.6.0 as an experimental feature", still experimental in the stable docs (https://optuna.readthedocs.io/en/stable/reference/generated/optuna.pruners.WilcoxonPruner.html). Signature `WilcoxonPruner(*, p_threshold=0.1, n_startup_steps=2)`. v5.0.0 notes do not list it as stabilised.
3. MCP server: official repo https://github.com/optuna/optuna-mcp, MIT, tags v0.2.0 and v0.1.2 (latest tag v0.2.0; release date and PyPI version not opened). Tools: create_study, ask, tell, best_trial, plot_*, launch_optuna_dashboard, etc.
4. Verdict: confirmed.

## 14. arXiv 2606.05250
1. Exists. "Towards Persistent Case-Based Memory for Autonomous Data Science: A CBR-Augmented R&D-Agent with a Locally Deployable Small Language Model", Felix Stocker, single author, cs.SE. v1, 3 Jun 2026. https://arxiv.org/abs/2606.05250
2. Evidence is thin: Gemma 4 31B Dense on one Kaggle task (Spaceship Titanic), 0.8147 vs 0.8098, described by the author as directional.
3. Code and replication: not checked.
4. Verdict: confirmed as to topic; weak evidence, do not cite for effect size.

## 15. Thresholdout and Guess and Check
1. Thresholdout: Dwork, Feldman, Hardt, Pitassi, Reingold, Roth, "The reusable holdout: Preserving validity in adaptive data analysis", Science 2015 (venue and year from memory, not opened); NeurIPS 2015 companion "Generalization in Adaptive Data Analysis and Holdout Reuse", https://arxiv.org/abs/1506.02629 (listed in search, not opened). Guess and Check: Rogers, Roth, Smith, "Guaranteed Validity for Empirical Approaches to Adaptive Data Analysis", AISTATS 2020 (PMLR 108), https://arxiv.org/abs/1906.09231 (full author list not opened beyond search text, which names Rogers, Roth, Smith). Both references exist.
2. 2024 to 2026 use in ML model selection with small validation sets: not found. Closest: "Program Analysis for Adaptive Data Analysis" (Liu, Qu, Gaboardi, Garg, Ullman), arXiv 2608.19575, 20 Aug 2026 (abs page lists PLDI 2024 journal reference, inconsistent with the date); about program analysis, no ML model selection, does not mention Thresholdout or GnC on the abs page. Older material: a Zillow engineering post notes Thresholdout can overestimate when the train-holdout gap is under the threshold; arXiv 1706.07581 notes small samples give unreliable accuracy estimates whatever the reuse scheme. Neither is 2024 to 2026.
3. Verdict: references confirmed; recent practical evidence not found (two searches only).

## Summary table

| # | Claim | Verdict | What to correct |
|---|---|---|---|
| 1 | e-means | partly | Lower bound 1.4 epochs (1.2 only Table 10); dead-cluster 0.3/26.3 % not found; API is class `Emeans` with `train`, not a function; FAISS 1.16.0 (10 Nov 2026) does contain it; finalisation names are "last-epoch-mean" and "slow-EMA" |
| 2 | Complete(d)P | confirmed (code not found) | 27 % is in Sec. 3.3 (1.3B, 26B tokens), not abstract; no code link; ICLR 2026 not verified |
| 3 | 2610.37842 | confirmed | Title: "Improving Data-Constrained Scaling with Hyperparameter Transfer and Ensembling"; threshold is C2; C3 about 4.8e4 x U^1.9; code at qlabs-eng repo |
| 4 | FOREAGENT | confirmed | "+6 %" unit unspecified; 61.5 % is accuracy given a data-analysis report |
| 5 | AgentX-Model | confirmed with caveat | 560/636 is offline AUC above business baseline, proprietary recommender setting |
| 6 | Rank CS | confirmed | 30 %/51 % are in the body (six equal models, 200 looks), not the abstract |
| 7 | Dion3 | confirmed | 26x to 4x is in Fig. 1 of the paper, not the abstract (abstract: up to 6x vs Muon); 7B on 4 GH200; still slower than AdamW |
| 8 | ZClip | partly | Paper is 2504.02507; 2502.11034 is AdaGC; defaults 0.97 and 2.5 confirmed |
| 9 | Cut Cross-Entropy | confirmed | Latest PyPI 25.1.1 (7 Jan 2025); custom Apple licence; no GitHub releases |
| 10 | Liger-Kernel | partly | v0.8.5, 21 Oct 2026; README says 20 % and 60 %; "47 %" not found |
| 11 | CVE-2026-39861 | confirmed | Claude Code sandbox escape via symlinks, fixed in 2.1.64; published 21 Apr 2026 |
| 12 | Claude Code changelog | partly | xhigh for ultrathink since 2.1.311 (VS Code 2.1.316), not 2.1.318; env var 2.1.316 ok; four hook events exist; PostToolBatch first version unknown |
| 13 | Optuna | confirmed | v5.0.0 on 7 Sep 2026; WilcoxonPruner since 3.6.0, still experimental; optuna/optuna-mcp tag v0.2.0 |
| 14 | 2606.05250 | confirmed (weak evidence) | Single author, one Kaggle task, small effect |
| 15 | Thresholdout / GnC | references confirmed; practice evidence not found | No 2024 to 2026 ML model-selection study found in two searches |

## Not opened
Faiss/Optuna/Liger PyPI project pages (read via API or summaries), NVD page, Complete(d)P and Dion3 and e-means HTML tails, arXiv abs for ZClip and 1506.02629 / 1906.09231 (from search results), FOREAgent and AgentX code, the Liger-Kernel paper, license text of Cut Cross-Entropy beyond its first lines.

## Redirection
No instruction aimed at the reader was found in the pages opened.
