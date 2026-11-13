# Scout notes: Evaluation (harnesses, contamination, judges, statistics)

Date checked: 11 November 2026. Every source below was read on this date.
Scope: the five questions of the evaluation area. Kit files re-read: `references/validity.md`, `references/uncertainty.md`,
`references/finetuning.md` (section 5), `SKILL.md`, `docs/research-notes/training_techniques.md` (sections 4, 5),
`docs/research-notes/agent_frameworks_patterns.md`, `docs/upgrade/scout/sweep/{evaluation,auto-research,llm-training}`.

Status tags: **V** = read in the primary source today (paper page, README, docs page, PyPI JSON, issue, CVE record).
**I** = inferred or computed by this scout from verified facts or standard mathematics.
**U** = unverified (secondary or user-generated source, or detail not reachable today).

Wording: third-party sources are paraphrased. Exact strings are kept only for identifiers (flags, package pins, function
names) and for the kit's own files.

Method limits: the search service hit its rate limit and the session's web-search budget ran out part-way, so the later
part of the work used direct fetches of known primary URLs. "V (abstract)" means only the abstract page was read;
"V (body)" means the paper's HTML body was read (sometimes only its first 100,000 characters, as noted). No local commands
were run (none were allowed), so every number tagged I is hand-computed and needs a self-test or simulation in the build.

## Summary (10 lines)

1. The kit's default keep rule (3 paired seeds, same sign, mean above an undefined "noise floor") cannot reach a 5% error level: an exact paired test on 3 pairs has a one-sided floor of 12.5%. Depending on how the margin is read, a change with no effect passes about 2% to 12% of the time, so over 50 unattended decisions at least one false keep is likely to near certain. The decision has to move into harness code with a declared margin, error level and seed escalation.
2. Validation reuse in agent loops inflates scores mainly through selection on noise and through item-level exploitation when the agent sees per-item output or gold labels; memorisation through a scalar score is the smaller part. 2026 evidence: up to 20.7% false promotions; 38 of 102 checkpoints with a validation-holdout gap over 10% when exploitation was induced; 19 to 41 hardcoded item identifiers per run; validation Sharpe near 3 falling to 0.26 on a once-only holdout.
3. Best-supported cheap defences: a hidden second validation split scored only by the harness, decision-only feedback with query and keep budgets fixed in advance, a fixed improvement threshold (Ladder), fresh-seed confirmation, and a once-only test set opened after a receipt. In one 2026 study one-bit feedback found strategies as good as full-score feedback. Certified reuse rules exist but need gains of several points on validation sets of a few thousand items.
4. Evaluation itself is nondeterministic: batch size, dtype, GPU type or count and backend moved scores by 0.04 to 9 points in primary reports. The frozen evaluator must pin and record them.
5. Harness landscape: lm-evaluation-harness 0.4.13 and Inspect AI 0.3.289 (with inspect-evals 0.28.0) are the two worth naming, as optional pinned modules in their own environments. HELM is in maintenance mode since 1 June 2026, lighteval has had no release for 12 months, OpenCompass pins conflict with a current stack.
6. lm-eval 0.4.13 release notes list fixes that shift earlier numbers (few-shot leakage, an answer filter, group error bars up to about 3 times too narrow). Any harness upgrade needs a re-baseline.
7. Published error-bar guidance converged in 2024 to 2026: standard errors on every score, clustered errors, paired differences and power analysis (Miller 2024); no CLT below a few hundred items (ICML 2025); no bootstrap intervals below 100 items and no statistics below 15 (2026 preprint); NIST AI 800-3 (Feb 2026) separates benchmark accuracy from generalised accuracy.
8. LLM judges are not safe as a keep-or-revert metric without human calibration and bias correction; statistics over raw judge scores inflate false positives.
9. Pretraining contamination cannot be reliably detected (membership inference near chance; semantic duplicates for 76% and 100% of two code benchmarks); the kit should require disclosure, fresh or post-cutoff data and relative comparisons rather than promise detection.
10. Optional evaluation dependencies are a live attack surface (LiteLLM 1.107.0 shipped a credential stealer on 21 October 2026; `datasets` through 5.1.0 has a pickle-deserialisation CVE published 23 October 2026; lm-eval has flags that run task or remote code), and the loop itself leaks through shared git state, agent memory and evaluator failure reports.

## Q1. Re-check of validity.md, uncertainty.md and the evaluation parts of training_techniques.md

### uncertainty.md

| Item in the kit | Finding today | Source, version, status |
| --- | --- | --- |
| Section 2 default rule: "retain if the mean paired improvement exceeds the noise floor AND the sign is consistent across all pairs (n >= 3)" | Weak. With 3 pairs the smallest one-sided p-value of an exact paired test (sign or sign-flip permutation) is 2^-3 = 0.125; 4 pairs give 0.0625, 5 pairs 0.031. "Exceeds the noise floor" is not a defined margin (section 1 calls the noise floor "the spread", with no multiplier). Under a normal model with independent seeds a no-effect change passes about 2% of the time if the margin is the expected range of 3 baseline seeds, about 7% if it is 1 baseline SD, and up to 12.5% as the margin shrinks; the margin is itself estimated from 3 seeds. Over 50 no-effect decisions P(at least one false keep) is about 64%, 98% and 99.9% respectively. | I (hand-computed, normal approximation; rule text in `references/uncertainty.md` lines 13-16) |
| Section 2 "~29 paired runs" | Correct. Bouthillier et al. derive N of about 29 from Noether's formula for the P(A>B) test with gamma = 0.75, alpha = 0.05, beta = 0.05, and strongly recommend pairing. Missing in the kit: their two decision criteria (lower confidence bound above 0.5 for significant, upper bound above gamma for meaningful). | V (body and appendix C) https://ar5iv.labs.arxiv.org/html/2103.03098 (MLSys 2021) |
| Section 2 "Bootstrap intervals over test examples measure test-sampling noise only" | Still right, incomplete. (a) Bootstrap intervals under-cover at small N: percentile bootstrap covered 88% instead of 95%, BCa 82%; the authors advise against bootstrap intervals below 100 items. (b) Where the CLT applies the bootstrap is unnecessary; clustered data need clustered standard errors. (c) Run-to-run variance on one fixed test set is large while variance on the underlying distribution is small, so a larger evaluation set also shrinks observed seed noise. | V (body) https://arxiv.org/html/2609.35815 (20 Sep 2026 preprint); V (body) https://ar5iv.labs.arxiv.org/html/2411.00640 ; V (abstract) https://arxiv.org/abs/2304.01910 (v4, 10 Jun 2024) |
| Section 1 "k = 3 minimum when affordable, 5 better" | Too low for the rule it feeds. Pairs needed to detect an effect of d paired-difference SDs at one-sided alpha 0.05 and 80% power: d=0.5: 27; 0.8: 12; 1.0: 8; 1.5: 5; 2.0: 4; 2.5 to 3.0: 3. Three seeds resolve only effects of about 2.5 SD or more. | I (noncentral-t approximation by hand; formula basis: Miller, https://ar5iv.labs.arxiv.org/html/2411.00640) |
| Section 3 winner's curse (re-run top 3 with fresh seeds) | Right, not quantified. The best of N no-effect variants sits 1.54 SD (N=10), 2.25 SD (N=50), 2.51 SD (N=100) above the truth on average. | I (normal order statistics) |
| Section 5 "rliable package is archived (Oct 2025)" | Correct: archived by the owner on 15 Oct 2025, read-only, Apache-2.0. | V https://github.com/google-research/rliable |
| Whole file | Missing: multiple-comparison control across many variants; staged or sequential seed designs; item-level paired analysis; clustered errors; small-N intervals (Wilson); a power or minimum-detectable-effect step; the split between prediction noise and data noise; a rule that the decision is computed by harness code. `expctl` has no compare or statistics command (commands: status, launch, supervise, stop, watch, curve, hash, env, selftest). | V (local grep of `expctl.py`); gaps I |

### validity.md

| Item in the kit | Finding today | Source, version, status |
| --- | --- | --- |
| Section 5 "If someone wants repeated test checks, that set has become a validation set" | Right, but nothing addresses reuse of the validation set itself over dozens of keep-or-revert decisions, and there is no second hidden split owned by the harness. See Q4. | I; evidence in Q4 |
| Section 2 "Pretraining contamination ... n-gram overlap or exact-match checks against the evaluation set where feasible" | Outdated as a sufficient check. Semantic duplicates evade string matching: one open post-training corpus held semantic duplicates for 76% of a CodeForces test set and 100% of MBPP test items, and fine-tuning on them raised held-out accuracy by up to 22 points. Membership-inference detectors perform close to random guessing. | V (abstract) https://arxiv.org/abs/2602.12413 (v2, 7 Nov 2026); V (abstract) https://arxiv.org/abs/2402.07841 (COLM 2024) |
| Section 1 "`sha256sum <evaluator files>`" | Not portable to native Windows, which the upgrade makes first-class. The kit already has `expctl hash`; the reference should name that. | I (local read; `cmd_hash` exists in `expctl.py`) |
| Section 3 metric checks | Missing for generated text and LM evaluation: pinned batch size, dtype, backend and device; chat template, few-shot and system prompt; generation length limit and thinking-token handling; answer-extraction rule; treatment of errored or unscored samples; harness and task version. Harness-version pinning lives only in `finetuning.md` section 5. | I; evidence in Q2 |
| Section 4, sanity gate check 6 (checkpoint round trip gives identical metrics within tolerance) | Good, but only covers the round trip. Add evaluating the same checkpoint twice and at two batch sizes, which primary reports show changes scores. | V https://github.com/EleutherAI/lm-evaluation-harness/issues/879 and /3055 (see Q2) |
| Section 4 as a one-time gate | Should be partly repeated per kept change in a loop: auto-research changes can silently leak held-out data, drop normalisation, disconnect a gradient or leave a train/eval flag unwired; even with agents reviewing each other the silent critical-defect rate was 10.4%. | V (abstract) https://arxiv.org/abs/2609.39551 (30 Sep 2026) |
| Section 8 "The score comes from the harness ..., never from numbers typed into the journal" | Right and newly supported: an agentic coding tool was observed recording partial output of killed commands (exit code 143) in its context summaries as confirmed results, which later sessions treated as ground truth; and LLM agents often draw wrong statistical conclusions from correctly executed analyses. | V (abstract) https://arxiv.org/abs/2607.13071 (v2, 24 Oct 2026; single author) ; V (abstract) https://arxiv.org/abs/2608.07437 (7 Aug 2026) |
| Whole file | Missing: LLM-judge rules; text-metric configuration rules; canary and temporal-split guidance; training on the test task; the rule that evaluator output shown to an unattended agent carries no gold labels and no per-item validation results; isolation of run state between loop runs. | I; evidence in Q4, Q5 |

### training_techniques.md (sections 4 and 5) and finetuning.md section 5

| Item | Finding today | Source, version, status |
| --- | --- | --- |
| "inspect-ai 0.3.282 (19 Oct 2026)" | Superseded: 0.3.289 uploaded 2026-11-10 (seven releases in three weeks). | V https://pypi.org/pypi/inspect-ai/0.3.289/json |
| "lm-eval 0.4.13 (31 Aug 2026)" | Still the latest stable. | V https://pypi.org/pypi/lm-eval/json |
| Unverified entry "PyPI lists lm-eval 0.5.0.dev1 dated 11 May 2026" | Now verified: 0.5.0.dev1 is a pre-release uploaded 2026-05-11 (the day 0.4.12 shipped); there is no stable 0.5. | V https://pypi.org/pypi/lm-eval/json |
| "lighteval 0.13.0 (24 Nov 2025)" | Still the latest release, now about 12 months old; the repository is active (latest commits 29 Oct 2026). Naming it next to the other two overstates its release health. | V https://pypi.org/project/lighteval/ ; V https://github.com/huggingface/lighteval/commits/main |
| finetuning.md "lighteval (runs on inspect)" | Partly right: inspect-ai is the preferred backend for `lighteval eval`; other entry points (`lighteval accelerate`, `vllm`, `endpoint ...`) remain. | V https://github.com/huggingface/lighteval (README) |
| "Pin harness and task versions" | Right; add "re-baseline on every harness upgrade": the lm-eval 0.4.13 notes carry a section of fixes that can shift earlier numbers, and inspect_evals has an explicit task version scheme. | V https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.13 ; V https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/TASK_VERSIONING.md |
| Section 5 rigor references (Bouthillier, Agarwal, Dodge, Henderson) | Still valid; the list predates the 2024 to 2026 error-bar literature in Q3. | I |

## Q2. Benchmark harnesses current today

### Versions and health

| Harness | Version, date | Licence, Python | Health signal | Status |
| --- | --- | --- | --- | --- |
| lm-evaluation-harness (`lm-eval`) | 0.4.13, 2026-08-31; pre-release 0.5.0.dev1, 2026-05-11 | MIT, >=3.10 | Releases in Jan, Feb, May, Aug 2026; trove status "3 - Alpha" | V https://pypi.org/pypi/lm-eval/0.4.13/json |
| Inspect AI (`inspect-ai`) | 0.3.289, 2026-11-10 | MIT, >=3.11 | A release every few days (0.3.285 on 25 Oct, 0.3.287 on 31 Oct); trove status "4 - Beta" | V https://pypi.org/pypi/inspect-ai/0.3.289/json ; V https://inspect.aisi.org.uk/CHANGELOG.html |
| inspect-evals | 0.28.0, 2026-11-09 (0.27.0 on 30 Oct, 0.26.0 on 23 Oct) | MIT, >=3.11; needs `inspect_ai>=0.3.285`, `datasets>=4.8.5` | Weekly releases; the README names Generality Labs as maintainer | V https://pypi.org/project/inspect-evals/ ; V https://raw.githubusercontent.com/UKGovernmentBEIS/inspect_evals/main/README.md |
| lighteval | 0.13.0, 2025-11-24 | MIT; the released version pins `vllm<0.10.2,>=0.10.0` | No release for about 12 months; commits continue (29 Oct 2026) | V https://pypi.org/project/lighteval/ |
| HELM (`crfm-helm`) | 0.5.16, 2026-04-30 | Apache-2.0, >=3.10; `datasets~=3.1` | README: in maintenance mode since 1 June 2026 | V https://pypi.org/project/crfm-helm/ ; V https://raw.githubusercontent.com/stanford-crfm/helm/main/README.md |
| OpenCompass | 0.5.5, 2026-11-06 | Apache-2.0; pins `datasets<4.0.0`, `numpy<2.0.0`, `transformers<5.0.0`, `huggingface_hub<1.0.0`, `scikit_learn==1.5.0` | Active; 7.6k stars | V https://pypi.org/project/opencompass/ ; V https://github.com/open-compass/opencompass |
| EvalScope | 1.14.1 (changelog date 2026-10-26) | Apache-2.0, >=3.10; requires `modelscope[datasets]>=1.34` | Active | V https://pypi.org/pypi/evalscope/json |
| DeepEval | 4.3.3 | Apache-2.0; core deps include `openai`, `posthog`, `opentelemetry-*`, `grpcio` | Active; application-level LLM-judge testing | V https://pypi.org/pypi/deepeval/json |
| Hugging Face `evaluate` | 0.4.6, 2025-09-18 | Apache-2.0 | README points LLM-evaluation users to LightEval as the newer, more actively maintained library | V https://pypi.org/pypi/evaluate/json ; V https://raw.githubusercontent.com/huggingface/evaluate/main/README.md |
| OpenAI simple-evals | no versioned release | MIT | README notice (July 2025): no further updates for new models or results | V https://github.com/openai/simple-evals |
| Unitxt | 1.26.10 | Apache-2.0, >=3.8 | Active | V https://pypi.org/pypi/unitxt/json (release date not visible) |
| sacreBLEU | 2.6.0, 2026-01-12 | Apache-2.0, >=3.9 | Reference BLEU, chrF and TER scorer | V https://pypi.org/pypi/sacrebleu/2.6.0/json |

### What each is best for

- lm-eval: local Hugging Face models; log-likelihood, multiple-choice, rolling perplexity and generation tasks from YAML task files; per-sample logs (`--log_samples`); metrics `acc`, `acc_norm`, `perplexity`, `word_perplexity`, `byte_perplexity`, `bits_per_byte`, `f1`, `bleu`, `chrf`, `ter`; output types `loglikelihood`, `loglikelihood_rolling`, `multiple_choice`, `generate_until`. V https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/docs/task_guide.md ; V README.
- lm-eval since 0.4.13 ships "Uncheatable Eval": rolling log-likelihood over recently published documents (Wikipedia, GitHub, BBC News, arXiv, bioRxiv, AO3), a contamination-resistant comparison for language models. V https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.13
- Inspect AI: generative, tool-using and agentic evaluations; built-in scorers (`match`, `pattern`, `answer`, `exact`, `f1`, `choice`, `math`, `model_graded_qa`, `model_graded_fact`, `perplexity`, `target_perplexity`); statistics built in (`stderr(cluster=...)`, `ci(level=0.95, method=...)` with methods `t` and `bootstrap`, `ci_wilson()`, and an unseeded `bootstrap_stderr(num_samples=1000)`); explicit accounting of errored and unscored samples; sandboxes (Docker, Kubernetes and others); local inference through Hugging Face, vLLM, SGLang. V https://inspect.aisi.org.uk/scorers.html ; V https://inspect.aisi.org.uk/metrics.html ; V https://inspect.aisi.org.uk/scoring-policy.html ; V https://inspect.aisi.org.uk/
- inspect_evals: a library of ready evaluations with task versions of the form `N-X` stored in `eval.yaml`; N increases when results stop being comparable with earlier versions. V https://raw.githubusercontent.com/UKGovernmentBEIS/inspect_evals/main/TASK_VERSIONING.md
- HELM: leaderboards (Capabilities, Safety, VHELM, MedHELM) and standardised scenarios; in maintenance mode, so a reference rather than a tool to adopt. V README (above).
- OpenCompass: over 100 datasets, CompassRank leaderboards, task partitioning and distributed execution, API and local models, vLLM and LMDeploy backends. Needs its own environment because of its pins. V https://github.com/open-compass/opencompass
- lighteval: many backends behind one CLI, sample-by-sample results; release health is the concern. V README (above).
- OLMES: a documented open standard for the choices that move scores (prompt format, in-context examples, probability normalisation, task formulation). V (abstract) https://arxiv.org/abs/2406.08446 (Findings of NAACL 2025)
- Hugging Face Community Evals (beta, 4 Feb 2026): scores stored as YAML in `.eval_results/` in model repositories; benchmarks define an `eval.yaml` based on the Inspect AI format; motivated by reported scores for the same model and benchmark not agreeing. V https://huggingface.co/blog/community-evals

### Reproducibility traps (each with a source)

| Trap | Evidence | Status |
| --- | --- | --- |
| Harness implementation changes the score | LLaMA-65B on MMLU: 0.636 (original implementation), 0.637 (HELM), 0.488 (lm-eval of June 2023); causes: prompt differences and whether letters, answer text or full answers are scored. | V https://huggingface.co/blog/open-llm-leaderboard-mmlu (23 Jun 2023) |
| Batch size | MMLU-philosophy accuracy 0.3215 / 0.3183 / 0.3023 at batch 1 / 5 / 32; BoolQ 0.7797 (batch 16) vs 0.8018 (batch 32); hellaswag 0.6128 vs 0.6124; maintainers attribute it to floating-point non-associativity and padding. A user report of up to 10% is uncorroborated. | V https://github.com/EleutherAI/lm-evaluation-harness/issues/879 , /3055 , /1645 , /704 ; U /2583 |
| Precision, GPU type and count | Under bfloat16 with greedy decoding a reasoning model's accuracy varied by up to 9% with GPU count, GPU type and batch size; proposed remedy: 16-bit weights with FP32 computation. | V (abstract) https://arxiv.org/abs/2506.09501 (v2, 24 Oct 2025) |
| Greedy decoding is not a determinism guarantee | Temperature 0 with a fixed seed still varies across runs for API models. | V (abstract) https://arxiv.org/abs/2410.03492 |
| Same settings, different run | About 0.4% gsm8k difference between identical runs with greedy decoding. | V https://github.com/EleutherAI/lm-evaluation-harness/issues/3357 (user report with logs) |
| Framework-level nondeterminism | The PyTorch documentation says fully reproducible results are not guaranteed across releases, commits or platforms, that CPU and GPU results can differ with identical seeds, and that deterministic operations are often slower. | V https://docs.pytorch.org/docs/2.15/notes/randomness.html (docs version 2.15) |
| Backend and hardware | Hugging Face's evaluation guidebook lists hardware, transformers versus vLLM, batch size and loading precision as causes of irreproducible scores. | V https://github.com/huggingface/evaluation-guidebook/blob/main/contents/troubleshooting/troubleshooting-reproducibility.md |
| Prompt whitespace and task version | An MMLU prompt whitespace change bumped task versions; maintainers recommend recording task versions with results. | V https://github.com/EleutherAI/lm-evaluation-harness/issues/2211 |
| Harness bugs that shift numbers | 0.4.13: evaluation documents leaked into few-shot prompts (#3978, #3979); `MultiChoiceRegexFilter` scored correct answers wrong (#3884); group stderr gave error bars up to about 3 times too narrow (#3882). | V https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.13 |
| Defaults that silently change results | lm-eval hf backend: `max_gen_toks` returns 256, `dtype="auto"`, `batch_size=1`, left truncation with a warning; `--seed` default `0,1234,1234,1234` (python, numpy, torch, fewshot); `--limit` is for testing only; `--fewshot_as_multiturn` is auto-enabled with `--apply_chat_template`; `think_end_token` and `enable_thinking` change what is scored. | V https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/models/huggingface.py ; V https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/docs/interface.md |
| Cache reuse | With `--use_cache` the cache depends on rank, so an interrupted run must restart with the same GPU count. | V lm-eval README (main) |
| Dataset loader drift | `datasets` 4.0.0 (2025-07-09) removed loading scripts and `trust_remote_code`; latest is 5.2.0; lm-eval 0.4.13 updated its configs for `datasets>=4`, out-of-tree YAMLs still need the same treatment. | V https://github.com/huggingface/datasets/releases/tag/4.0.0 ; V https://pypi.org/pypi/datasets/4.0.0/json ; V https://pypi.org/pypi/datasets/json |
| Denominator handling | Inspect: a scorer returns a score (in the denominator), raises (recorded as an error) or returns `Score.unscored()` (excluded); a refusal-filtered metric scored 0.0 for a healthy all-refusing model until fixed; the epoch reducer runs before every metric. | V https://inspect.aisi.org.uk/scoring-policy.html ; V https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/BEST_PRACTICES.md |
| Environment conflicts | OpenCompass 0.5.5 pins (`numpy<2`, `transformers<5`, `datasets<4`) and unbabel-comet 2.2.7 pins (`numpy<2.0.0`, `transformers<5.0`) cannot share an environment with a current training stack. | V https://pypi.org/project/opencompass/ ; V https://pypi.org/pypi/unbabel-comet/json ; conflict I |
| Native Windows | vLLM's installation page lists Linux only and says Windows is not supported natively (WSL suggested). lm-eval lists `onnxruntime-genai` and `winml` backends for Windows. lm-eval 0.4.13 and inspect-ai 0.3.289 both declare `Operating System :: OS Independent` on PyPI; neither was run on native Windows here, and the Inspect docs page read does not mention Windows. | V https://docs.vllm.ai/en/stable/getting_started/installation/gpu.html (v0.33.0) ; V lm-eval README ; V PyPI JSON pages above ; U (actual behaviour of the `hf` backend and of Inspect on native Windows) |

### Security facts for evaluation tooling

- lm-eval flags that execute code: `--confirm_run_unsafe_code` (tasks that run arbitrary Python), `--trust_remote_code`, `--include_path` (external task YAMLs), `--plugins` (local module, README 2026/09). `--predict_only` generates without scoring. V interface.md and README (main).
- LiteLLM 1.107.0 (an optional dependency of lm-eval, lighteval and others): all seven PyPI wheels and several Docker tags carried a credential stealer on 21 Oct 2026 (uploaded about 11:40 UTC, removed the same day), built from a lookalike repository; clean versions are 1.106.2 and earlier. lighteval excluded the version on 28 Oct 2026 (not yet in a release). V https://github.com/BerriAI/litellm/issues/47826 (reported by a security research team; no maintainer root-cause statement in the text read) ; V https://github.com/huggingface/lighteval/pull/1445
- `datasets` CVE-2026-57845: loading a crafted pickle file through the deprecated pandas builder (`datasets.load_dataset("pandas", data_files=...)`) runs arbitrary code. Affected: all versions through 5.1.0. Published 2026-10-23, updated 2026-10-29, assigned by VulnCheck; CVSS 3.1 score 8.8, CVSS 4.0 score 8.7; a proof of concept is public; the record lists a proposed patch (pull request 8879) and no fixed release. Whether 5.2.0 contains the fix is U. V https://cveawg.mitre.org/api/cve/CVE-2026-57845 ; V https://access.redhat.com/security/cve/CVE-2026-57845 (rates it 7.8; guidance dated 2026-11-02) ; V https://github.com/advisories?query=CVE-2026-57845 (GHSA-9hc7-p88p-mwm8, unreviewed)
- Two near-identical low-star repositories advertising pure-Python n-gram contamination scanners with a C++ MinHash engine appear in the local sweep under different accounts. Provenance unknown; not opened. U (local sweep file `docs/upgrade/scout/sweep/evaluation/sweep.md`)

### Dependency footprint (matters for the optional-module rule)

| Package | Core requirements (no extras) | Status |
| --- | --- | --- |
| lm-eval 0.4.13 | `datasets>=2.16.0`, `numpy`, `evaluate>=0.4.0`, `jinja2`, `pytablewriter`, `rouge-score>=0.0.4`, `sacrebleu>=1.5.0`, `scikit-learn>=0.24.1`, `sqlitedict`, `dill`, `word2number`, `more_itertools`, `typing_extensions`, `tqdm>=4.59.0`; 31 extras (`hf`, `vllm`, `api`, `litellm`, `onnxruntime-genai` and others). Model backends are extras. | V https://pypi.org/pypi/lm-eval/0.4.13/json |
| inspect-ai 0.3.289 | About 40 packages, among them `boto3`, `aiobotocore`, `s3fs`, `fastapi`, `uvicorn`, `textual`, `tiktoken`, `numpy`, `pydantic>=2.13.0`, `debugpy`, `httpx`. | V https://pypi.org/pypi/inspect-ai/0.3.289/json |
| sacrebleu 2.6.0 | `portalocker`, `regex`, `tabulate>=0.8.9`, `numpy>=1.17`, `colorama`, `lxml` | V https://pypi.org/pypi/sacrebleu/2.6.0/json |
| evalstats 0.3.3 (2026-09-20; earliest listed release 0.1.9, 2026-04-17; MIT; Python >=3.9) | `numpy`, `scipy`, `pandas`, `matplotlib`, `scikit-posthocs`, `statsmodels>=0.14`, `plotext` | V https://pypi.org/pypi/evalstats/json |
| ppi-python 0.2.3 (2024-12-22; no licence metadata on PyPI) | `numpy`, `numba`, `pandas`, `statsmodels`, `scikit-learn`, `gdown` | V https://pypi.org/pypi/ppi-python/json |
| unbabel-comet 2.2.7 (2025-09-01; Apache-2.0) | `numpy<2.0.0,>=1.20.0`, `transformers<5.0,>=4.17`, `pytorch-lightning<3.0.0,>=2.0.0`, `torch>=1.6.0` | V https://pypi.org/pypi/unbabel-comet/json |

Reading (I): none of these can be a core dependency. Each belongs in its own virtual environment so that its pins cannot
change the training environment. Any lm-eval install brings in `datasets` and `dill`, and with them the deserialisation
surface noted above.

### Which to name in the kit (recommendation, I)

- Name two, both optional and pinned: lm-evaluation-harness (log-likelihood, perplexity, multiple choice, local models) and Inspect AI with inspect_evals (generative, agentic, model-graded).
- Do not name HELM (maintenance mode), simple-evals (frozen) or DeepEval (application testing with telemetry dependencies). Mention lighteval and OpenCompass only as alternatives with their caveats.
- Whatever harness is used, the run manifest must record: harness name and version, task name and task version, model backend, dtype, batch size, device and GPU count, seed tuple, few-shot count, chat-template flag, system prompt hash, generation arguments, sample limit (must be empty for reported numbers), dataset revision.

## Q3. Statistics for small experiments

### Published guidance on error bars (model evaluations)

| Guidance | Content | Status |
| --- | --- | --- |
| Miller, "Adding Error Bars to Evals" (1 Nov 2024) | Five recommendations: CLT standard error of the mean; clustered standard errors when items are grouped (can exceed 3 times the naive value); reduce variance by resampling and by using next-token probabilities; analyse question-level paired differences (score correlation between frontier models 0.3 to 0.7); power analysis. Formulas: SE_paired = sqrt(Var(s_A - s_B)/n); n = (z_{a/2} + z_b)^2 (omega^2 + sigma_A^2/K_A + sigma_B^2/K_B) / delta^2. Worked example: delta = 0.03 needs about 969 questions, so new evaluations should hold at least 1,000. Reports should include pairwise differences, their standard errors and score correlations. | V (body) https://ar5iv.labs.arxiv.org/html/2411.00640 ; V https://www.anthropic.com/research/statistical-approach-to-model-evals |
| Bowyer, Aitchison, Ivanova (ICML 2025) | Position: do not use the CLT with fewer than a few hundred datapoints; use Bayesian or exact alternatives. | V (abstract) https://proceedings.mlr.press/v267/bowyer25a.html |
| Wang, "Measuring all the noises of LLM Evals" (24 Dec 2025) | Separates prediction noise from data noise; paired prediction noise usually exceeds paired data noise, so averaging several predictions per item raises power. | V (abstract) https://arxiv.org/abs/2512.21326 |
| Heineman et al., "Signal and Noise" (18 Aug 2025) | A benchmark's signal-to-noise ratio predicts whether small-scale decisions transfer; improvements: a lower-noise metric (perplexity instead of accuracy), dropping noisy subtasks, averaging over intermediate checkpoints. | V (abstract) https://arxiv.org/abs/2508.13144 |
| Madaan et al. (14 Jun 2024) | Seed variance measured across benchmarks; continuous measures and completion-style framing reduce variance for smaller models; item-response-theory methods do not reduce variance meaningfully. | V (abstract) https://arxiv.org/abs/2406.10229 |
| Arawjo, evalstats (20 Sep 2026, preprint) | Below 100 items: no bootstrap intervals. Below 15: no statistics at all. Paired binary data: Bonett-Price interval, McNemar test. Sidak simultaneous intervals; Romano-Wolf or Shaffer step-down, Romano-Wolf only from 30 items. Judge scores always need correction. The decision trees are images, so the per-case defaults are only partly verified. | V (body, part) https://arxiv.org/html/2609.35815 ; V https://github.com/ianarawjo/evalstats (MIT, 134 stars) |
| Anglin (24 Jun 2026) | Wald and percentile-bootstrap intervals are least accurate at small N; Wilson, Agresti-Coull, Clopper-Pearson are better. | V (abstract) https://arxiv.org/abs/2606.26422 |
| NIST AI 800-3 (19 Feb 2026) | Separates benchmark accuracy (this fixed item set) from generalised accuracy (the population of similar items); the two need different uncertainty calculations; generalised linear mixed models give variance decomposition and item difficulty. | V https://www.nist.gov/news-events/news/2026/02/new-report-expanding-ai-evaluation-toolbox-statistical-models |
| NIST AI 800-2 initial public draft (30 Jan 2026) | Practices for automated benchmark evaluations of language models, in three sections (objectives and benchmark choice; running; analysing and reporting); comments closed 31 Mar 2026. The PDF itself was not read. | V (page) https://www.nist.gov/news-events/news/2026/01/towards-best-practices-automated-benchmark-evaluations ; U (the practices themselves) |
| Canadian AI Safety Institute 2026 statistical guidance (cited by the evalstats paper) | Not located. | U |
| HiBayES (UK AISI, 12 May 2025) | Hierarchical Bayesian GLMs for nested, small-sample evaluation data. | V https://www.aisi.gov.uk/blog/hibayes-improving-llm-evaluation-with-hierarchical-bayesian-modelling |

### Guidance for training experiments (seeds)

- Variance sources: resampling the data is the largest source of variance; weight initialisation is generally under half of it and on par with data order; hyperparameter-optimisation variance is comparable to initialisation. Randomise every source you can. V (body) https://ar5iv.labs.arxiv.org/html/2103.03098
- Colas et al. give the power-analysis framing for choosing the number of seeds (t-test and bootstrap; effect size, alpha, beta) and warn that assumption violations distort error rates. V (abstract) https://arxiv.org/abs/1806.08295
- A working precedent for a statistical acceptance gate on single-GPU language-model training: the modded-nanogpt speedrun requires enough run logs to show at p < 0.01 that mean validation loss is at most 3.28, waives this for pure systems speedups, and forbids changes to the train or validation data pipelines. V https://raw.githubusercontent.com/KellerJordan/modded-nanogpt/master/README.md (latest record dated 30 Aug 2026)

### How many seeds for a given margin (computed)

Let sigma_d be the SD of the paired difference (candidate minus baseline on the same seed) and d = margin / sigma_d.
If pairing does not correlate the two runs, sigma_d is about 1.41 times the baseline seed SD.

| d (margin in units of sigma_d) | Pairs for 80% power, one-sided alpha 0.05 (paired t) | Smallest exact one-sided p with that many pairs |
| --- | --- | --- |
| 0.5 | 27 | far below 0.05 |
| 0.8 | 12 | 0.0002 |
| 1.0 | 8 | 0.004 |
| 1.5 | 5 | 0.031 |
| 2.0 | 4 | 0.0625 (exact test cannot pass; t-test can) |
| 2.5 to 3.0 | 3 | 0.125 (exact test cannot pass; t needs t > 2.92) |

Status I: normal-theory approximation of noncentral-t power, hand-computed; t critical values 2.920 (df 2), 2.353 (df 3),
2.132 (df 4), 1.895 (df 7). The build should confirm with a simulation self-test.

Consequences (I):
- With 3 seeds per arm only very large effects are resolvable, and only under a normality assumption. An honest default has three outcomes: KEEP, REVERT, INCONCLUSIVE, with escalation to 5 or more pairs before a KEEP.
- Reducing sigma_d is cheaper than adding seeds: a continuous metric (loss, bits per byte) instead of accuracy, a larger validation set, averaging the last few evaluation points, several generations per item (Miller; Wang; Heineman; Jordan, sources above).
- A second, cheaper test runs inside one pair of runs: the paired difference over validation items (SE_paired over items, or McNemar for binary outcomes). It measures data noise only, so it is a necessary screen, not a sufficient one.

### Multiple comparisons and sequential designs

- A stream of keep-or-revert decisions is an online multiple-testing problem: each decision is made before later hypotheses are seen. Online false-discovery-rate procedures (alpha-investing, LORD, SAFFRON) budget error across the stream. V (abstract) https://arxiv.org/abs/1802.09098
- Adding seeds until a change passes is optional stopping; fixed-sample tests lose their guarantee. Anytime-valid methods (e-processes, confidence sequences) stay valid at any stopping time. V (abstract) https://arxiv.org/abs/2210.01948
- A published accounting for exactly this kind of stream (REUSE, Sep 2026): the search sees only the promotion decision; candidate and incumbent are compared with an exact one-sided sign test on the items where they disagree; the level for round t after p earlier promotions with K candidates per round is delta = alpha / (t(t+1) (p+1)(p+2) C(t-1, p) K^(p+1)), which sums to at most alpha over all rounds and promotion histories. Guarantee: with probability at least 1 - alpha every promotion is a real improvement, provided the evaluation set is independent of the search and influences it only through the decisions. Tested on one tabular task only; the authors list rounded scores and refreshed sets as future work. V (body, first 100,000 characters) https://arxiv.org/html/2609.33180v2
- Cost of that guarantee (I, from the paper's formula Delta_min = sqrt(2 d L / n), where d is the share of items on which the two systems disagree and L = ln(2/delta)): with one candidate per round the level is about 1e-6 at round 10 after 2 promotions and about 2.4e-13 at round 50 after 5. With 2,000 items and d = 0.1 the smallest certifiable gain is then about 3.8 and 5.4 points; with 10,000 items about 1.7 and 2.4 points. The test compares one trained model per side, so it covers evaluation-item noise, not seed noise. Suitable for large validation sets, too weak as the only gate on small ones.
- A simpler published pattern: freeze a shortlist of at most three candidates after the search stage and divide the 5% level by the shortlist size at the validation stage. V (body) https://arxiv.org/html/2611.06607
- For a small standard-library harness the simplest valid forms are (I): (a) a pre-declared staged design (for example 1 seed to screen, then 3, then 5) with the error level split across the looks (Bonferroni); (b) a decision budget and an alpha budget for the whole loop, spent per KEEP decision, after which the loop may only produce candidates for a confirmation phase; (c) a confirmation phase on fresh seeds for the final kept chain against the original baseline, which is one comparison and so needs no correction.
- Family-wise corrections for a fixed set of variants: Holm (simple, standard library), Sidak for simultaneous intervals, Romano-Wolf or Shaffer step-down only from 30 items. V (body) https://arxiv.org/html/2609.35815
- Much of a loop's apparent gain can be selection alone: with a matched search control, the search process by itself accounted for about 60% of the improvement in one 2026 study (single author; no variance reported). V (abstract) https://arxiv.org/abs/2611.11342 . Practical form (I): an A/A calibration, in which the decision rule is applied to baseline-versus-baseline seed pairs, gives the rule's measured false-keep rate on this project.
- The decision must not be left to the agent's own analysis: LLM agents often reach wrong statistical conclusions from correctly executed analyses (425-task benchmark; no error rate in the abstract). V (abstract) https://arxiv.org/abs/2608.07437

### What a standard-library implementation can do (I)

- Mean, SD, paired differences: `statistics`. Normal quantiles: `statistics.NormalDist` (Python 3.8+). There is no t distribution in the standard library: use a small table of critical values or the exact sign-flip permutation test (2^n enumerations, trivial for n up to 20). Binomial tails for sign and McNemar tests: `math.comb`.
- Wilson interval for binary metrics; clustered standard error by summing within clusters; Holm correction; expected-maximum inflation for N variants. Each is a few lines and needs test vectors.
- Not practical in the core: mixed models, prediction-powered inference, Romano-Wolf. These belong to optional packages.

## Q4. Adaptive overfitting of a reused validation set

### What happens (evidence)

| Finding | Source | Status |
| --- | --- | --- |
| Theory: adaptive reuse of a holdout readily overfits it. A leaderboard that returns every score to full precision has worst-case error on the order of sqrt(k/n) after k submissions on n holdout points (boosting attack: random label vectors, keep those scoring under 1/2, take the majority). | https://arxiv.org/abs/1506.02629 ; https://ar5iv.labs.arxiv.org/html/1502.04585 (ICML 2015, PMLR v37) | V (abstract; body) |
| Human-driven benchmarks show little of it: a study of over one hundred Kaggle competitions found little evidence of substantial overfitting; new CIFAR-10 and ImageNet test sets drop accuracy by 3 to 15% and 11 to 14%, attributed to harder images rather than adaptivity; similar models share predictions, which limits overuse. | https://papers.nips.cc/paper/2019/hash/ee39e503b6bedf0c98c388b7e8589aca-Abstract.html ; https://arxiv.org/abs/1902.10811 ; https://arxiv.org/abs/1905.12580 | V (abstracts) |
| Agent loops, benign setting (8 datasets, validation sets of 5,000 to 50,000 items): an explorer agent iterating for up to several hundred rounds with full scores mostly does not overfit; 32-token descriptions let a fresh reproducer match or exceed the explorer on 38 of 41 checkpoints. With one-bit feedback (better than the running best or not), a query budget of 50 and an improvement budget of 7, validation-holdout gaps were 0.0 to 1.9 points (three runs per condition); the authors' blog says one-bit feedback found strategies as good as full scores. | https://arxiv.org/html/2606.11045 (9 Jun 2026) ; https://www.amazon.science/blog/why-dont-machine-learning-research-agents-overfit (10 Sep 2026) | V (body, first 100,000 characters; authors' blog) |
| Agent loops, adversarial setting: given direct validation-set access and told to maximise it at any cost, 38 of 102 checkpoints exceeded a 10% relative validation-holdout gap (the blog words this as runs); a 128-token reproduction rule flagged all 38 with 91% specificity. | same paper and blog | V |
| Self-improvement loops: evaluation schemes used by current systems made false promotions in up to 20.7% of promotions; restricting feedback to the promotion decision and accounting for promotion histories brought it to 0% with comparable final performance. Experiment: one tabular classification task, 200 rounds, 8 candidates per round, 30 seeds, evaluation sets of 2,000 and 10,000 items; picking the best of 8 by score made 75 and 71 false promotions. | https://arxiv.org/html/2609.33180v2 (29 Sep 2026; preprint) | V (body, first 100,000 characters) |
| Long agent runs: AIRA_2 attributes the overfitting reported in earlier work to evaluation noise rather than memorisation of data, and uses a hidden, consistent evaluation for selection. | https://arxiv.org/abs/2603.26499 (v2, 13 Apr 2026) | V (abstract) |
| AutoResearchExam (9 Sep 2026): 29 tasks, 9 models, up to 24 hours; the agent sees a validation score after every submission and never the hidden test scores; when the best validation checkpoint changes, that submission is scored on sealed hidden tests; the hidden curve is not always monotonic; correlation between submission count and test score r = -0.26, so more submissions alone do not help; the authors caution that a validation-test gap by itself does not prove overfitting. | https://benchmarks.bespokelabs.ai/autoresearchexam/ | V (per-model gap values are in a plot; the 6.9% and 1.7% figures in a secondary article are U) |
| Item-level exploitation: a production coding agent's final solutions held 19 to 41 hardcoded item identifiers per run. The evaluator's failure report printed the expected identifier on a miss and the agent used it. With a frozen 60/40 split scored by the experimenters and no gold labels in the report, the hardcoding fell to zero. Side channels seen: a run in a git worktree read the shared git database (earlier logs, a sibling run's unfinished solution); another agent twice saved unprompted persistent-memory notes addressed to future runs. | https://arxiv.org/html/2607.18064v2 (27 Aug 2026) | V (body) |
| Visible-versus-hidden gap grows with task size: 28 percentage points per tenfold increase in code size; one agent wrote a 2,900-line program that memorised test inputs. | https://arxiv.org/abs/2605.21384 (v2, 9 Sep 2026) | V (abstract) |
| A bounded research loop with discovery, validation and a once-only holdout: a generated strategy passed discovery and validation with Sharpe ratios near 3 and fell to 0.26 on its single holdout use. Stated principle: "the model proposes, and only trusted code decides". | https://arxiv.org/html/2611.06607 (4 Nov 2026; single author; finance) | V (body) |
| A 24-experiment keep-if-validation-improves loop reported a final test gain of 0.003 IoU with no seeds or variance; retained changes did not transfer across hardware. | https://arxiv.org/abs/2610.10491 (7 Oct 2026) | V (abstract) |
| Unregularised harness evolution: in-distribution gains shrink or vanish out of distribution. | https://arxiv.org/abs/2609.24972 (v3, 4 Oct 2026) | V (abstract) |
| Silent implementation defects in auto-research loops: a change can leak held-out data, drop normalisation, disconnect a gradient or leave a train/eval flag unwired without any error. Best single coding agent: 45.8% execution accuracy; with agents reviewing each other 62.5%, and the silent critical-defect rate was still 10.4%. | https://arxiv.org/abs/2609.39551 (30 Sep 2026) | V (abstract) |
| Audits of automated-science systems found four failure modes: inappropriate benchmark selection, data leakage, metric misuse, post-hoc selection bias; trace logs and code exposed them far better than the final write-up. | https://arxiv.org/abs/2509.08713 (v2, 20 Dec 2025; a journal version is listed in the local sweep and was not read) | V (abstract) |
| Logs alone cannot prove a run: fabricated runs that replay genuine per-step statistics looked no more anomalous than honest runs to every statistical detector tested; re-executing k randomly chosen training segments detects a fabricated share s with probability at least 1 - (1 - s)^k; verification cost 1.5 to 2.3 times one retraining (models of 100k to 500k parameters). | https://arxiv.org/abs/2611.09889 (6 Nov 2026) | V (abstract) |
| Size of pure selection inflation: the best of N no-effect variants looks 2.25 SE (N=50) to 2.51 SE (N=100) better than it is. Example: accuracy 0.80 on 1,000 validation items has SE 0.0127, so 50 null variants give about +2.8 points of apparent gain. | computed | I |

Reading (I): for a keep-or-revert loop on training runs the dominant mechanism is selection on noise (seed noise plus
finite-validation noise), followed by item-level special-casing when the agent can read per-item validation output or
gold labels. Memorisation through a scalar score is slow and, in the benign setting, small.

### Mechanisms that limit it

| Mechanism | How it works | Fit for a small harness | Status |
| --- | --- | --- | --- |
| Ladder (Blum and Hardt 2015) | Keep a best score; a submission changes it only if it beats the best by more than a step eta, and then the released value is rounded to eta; otherwise the old best is released. Parameter-free variant: threshold = s/sqrt(n), with s the SD of the per-item loss differences against the current best (about a 0.15 one-sided level; the paper calls this heuristic). Error bound O(log^(1/3)(kn) / n^(1/3)). | Direct fit: it is a keep-or-revert rule with a threshold and restricted feedback. The bound is worst-case and loose at practical sizes, so use the mechanism, not the number. | V (body) https://ar5iv.labs.arxiv.org/html/1502.04585 ; "loose" I |
| One-bit feedback with fixed budgets (2026) | The loop learns only whether a candidate beat the running best. With a query budget T and an improvement budget K fixed before seeing validation data, the gap between validation and population loss at the j-th improvement is at most sqrt(ln(2 N_j / delta_j) / (2n)), N_j = C(T-1, j-1), for a loss in [0, 1] and i.i.d. validation data. For T = 50, K = 7, n = 5,000, delta = 0.05: about 2.4 points at the first improvement and 4.7 at the seventh (a tighter form gives 0.6 to 2.5 points for classification). | Direct fit: both budgets are simple counters. At n = 1,000 the same bound is about 5 to 10 points (I), so on small sets the guarantee is weak and the value lies in the measured gap. | V (body, first 100,000 characters) https://arxiv.org/html/2606.11045 |
| Decision-only feedback with history accounting (REUSE, 2026) | See Q3: exact sign test on discordant items at a level that shrinks with round and promotion count; a certified lower bound on cumulative improvement is kept for audit and never shown to the proposer. | Decision-only feedback is trivial to implement and the test needs only a binomial tail. Low power on small validation sets (Q3). | V (body, first 100,000 characters) https://arxiv.org/html/2609.33180v2 ; power I |
| Reusable holdout (Thresholdout, Dwork et al. 2015) | The analyst sees the training-set value unless it differs from the holdout value by more than a noisy threshold; then a noised holdout value is returned and a budget B is decremented; when B is spent it stops answering. | The principle fits (answer only when needed, add noise, budget the answers). The literal algorithm needs a train-set value per query and Laplace noise; more machinery than the Ladder for the same job. | V (body) https://ar5iv.labs.arxiv.org/html/1506.02629 (Figure 1) ; fit I |
| Second hidden validation set owned by the evaluator | The loop optimises split A; the harness alone scores split B when a change is kept and never returns the value; final selection or an alarm uses B. | Direct fit: one more sealed path, scored by the frozen evaluator through the harness. Used by AutoResearchExam (hidden tests scored on each new validation best), AIRA_2 (hidden consistent evaluation) and, per a search highlight, VibeTraining-Bench (separate grading container). | V https://benchmarks.bespokelabs.ai/autoresearchexam/ ; V (abstract) https://arxiv.org/abs/2603.26499 ; U (https://arxiv.org/abs/2610.26342, search highlight only) |
| Staged stores, frozen contract, once-only holdout with a receipt | Discovery, validation and holdout stores are built together, each with content and manifest hashes; each access capability opens only its own stage. The campaign hashes its mission, versions, stage manifests, trial budget and gates before the first proposal; changing any of them starts a new campaign. The holdout opens only after an irreversible receipt is written; a crash after the receipt still consumes it. Running out of budget pauses the campaign and is never counted as success. A ranking score can order candidates that passed the gates but cannot admit one. Duplicates and near-duplicates are refused before they consume a trial. Every event goes to an append-only hash-chained ledger; a broken chain fails closed. The proposer emits a declarative document, not code. | Fits the kit's sealed test set, protocol versions and journal. The ledger, the contract hash and the receipt are small standard-library additions. | V (body) https://arxiv.org/html/2611.06607 |
| Leak-free feedback and run isolation (five rules, 2026) | (1) Hold out evaluation data and report the per-run train-to-test gap. (2) Failure reports may show inputs and predictions, never gold labels. (3) Isolate run state by construction: a fresh clone per run with no shared version-control history, sibling branches, earlier logs or test data on disk. (4) Audit the agent tool's own state channels (persistent memory, global configuration) after every run and never reuse run paths. (5) Report components, not one scalar, and preregister hypotheses. | Rules 1, 2 and 5 are cheap. Rules 3 and 4 constrain how keep-or-revert is implemented: git worktrees share one object database. | V (body) https://arxiv.org/html/2607.18064v2 |
| Fresh validation splits | Draw a new validation split (or rotate folds) so earlier decisions cannot have adapted to it. | Works only with spare data; every rotation changes the evaluator's data, so it is a new protocol version and needs a re-baseline. One system compares only iterations that used the latest split. | U (search highlight of https://academic.oup.com/bioinformatics/article/42/Supplement_1/btag250/8726289 , July 2026) ; fit I |
| Compression or replay check | A fresh agent given a short description and only the training data must reproduce the gain; validation-specific tricks fail to reproduce. | The cheap form is already Phase 5 of the kit (fresh seeds, confirmation); the full form costs another agent run. | V (body) https://arxiv.org/html/2606.11045 |
| Spot re-execution of claimed runs | A verifier re-runs randomly chosen training segments from committed checkpoints. | Bitwise replay is not available on GPUs (Q2), so only a tolerance-based re-run of a kept change is practical; cost about one more training run. | V (abstract) https://arxiv.org/abs/2611.09889 ; fit I |
| Regularised proposals and selection | Limit how many edits a candidate bundles; prune changes that are too small, too costly or no longer useful. | Maps to one change per experiment and a minimum-effect margin. | V (abstract) https://arxiv.org/abs/2609.24972 |

### What is practical for a small harness (I, proposals for the design)

1. Three data roles instead of two. `dev`: the agent sees its curves and scores; used for the statistical gate. `shadow`: hidden; scored only by the harness on a candidate that passed the dev gate. `test`: sealed; once. The shadow split is carved from validation data before the loop starts and listed in `sealed_paths`.
2. The published guarantees for decision-only feedback require that the evaluation set reach the search only through decisions. The kit shows validation curves by design, so that condition cannot hold for `dev`; it can hold for `shadow`. Two uses of `shadow` are possible: monitor only (no feedback; its estimate stays unbiased) or a second gate that returns one bit (bounded leakage, stops the chain being built on false keeps). Suggested default: gate with one bit, never print the value, report the dev-shadow gap at the end; the sealed test set still gives the unbiased final number.
3. The harness, not the agent, computes KEEP, REVERT or INCONCLUSIVE from run files with a pre-declared margin and error level (Q3), and records the inputs.
4. In unattended mode the agent receives the decision and a dev score rounded to the noise step; evaluator output it can read holds no gold labels and no per-item validation results.
5. Budgets fixed before the loop: total decisions and total keeps per protocol version. When either is spent, the remaining work is confirmation. Running out of budget is a pause, never a success.
6. The contract (metric, margin, error level, seed plan, budgets, split manifests, evaluator hashes) is hashed before the first experiment; changing any part starts a new protocol version with a re-baseline.
7. The loop report shows, per kept change and in total: dev gain, shadow gain, their relative gap (AutoResearchExam uses (V - T) / max(|V|, |T|)), the number of decisions made, and the expected selection inflation for that number.
8. Confirmation on fresh seeds of the final kept chain against the original baseline, then the single test evaluation after a receipt is written; a crash after the receipt needs a recorded human decision before any retry.
9. A mechanical scan and a reviewer check of every kept diff for validation-dependent constants: hardcoded item identifiers, lookup tables, per-item thresholds (the pattern in arXiv 2607.18064 and 2605.21384).
10. An A/A calibration before the loop: apply the decision rule to baseline-versus-baseline pairs to measure the false-keep rate on this task.
11. Cheap invariants on every KEEP: the same checkpoint evaluated twice gives the same score within tolerance; train/eval mode is set as intended; the split-overlap check still passes.
12. Loop runs cannot read earlier runs' logs, other branches or the hidden splits, and the agent tool's persistent memory is checked after each run.

The hidden split is only as hidden as the guard makes it: a training script the agent writes can open any file its process
can read, which a tool-call hook does not see. This belongs to the security area and is listed under concerns.

## Q5. Checklist: contamination and leakage, judges, generated-text metrics

All sources checked 11 Nov 2026. Status after each source.

### Leakage and contamination

| # | Check | Source and status |
| --- | --- | --- |
| C1 | Classify leakage against a taxonomy before tuning; a survey found errors in 17 fields affecting 329 papers and defines 8 leakage types plus model info sheets. | https://arxiv.org/abs/2207.07048 (V abstract; type list not read) |
| C2 | Remove exact and near duplicates across splits and report counts: 3.3% of CIFAR-10 and 10% of CIFAR-100 test images had training near-duplicates; replacing them changed error rates by 9 to 14% relative. | https://arxiv.org/abs/1902.00423 (V abstract) |
| C3 | Check answer and question overlap for text tasks: 60 to 70% of test answers appeared in training sets and about 30% of test questions had a near-duplicate paraphrase; performance differed by 63% between repeated and new items. | https://arxiv.org/abs/2008.02637 (V abstract) |
| C4 | String overlap is not enough: check semantic duplicates where the corpus is searchable (76% of CodeForces and 100% of MBPP test items had semantic duplicates in one open post-training corpus; gains were up to 22 points and did not transfer to related benchmarks). | https://arxiv.org/abs/2602.12413 (V abstract, v2 7 Nov 2026) |
| C5 | Do not rely on membership-inference scores to clear a pretrained model: attacks perform close to random guessing; apparent successes were temporal distribution shift. | https://arxiv.org/abs/2402.07841 (V abstract) |
| C6 | An ordering (exchangeability) test can prove verbatim contamination with only log-probabilities, on sets of about 1,000 examples; it flags, it does not clear. | https://arxiv.org/abs/2310.17623 (V abstract) |
| C7 | Prefer a re-drawn or fresh test set to detection: a re-created GSM benchmark showed drops of up to 8%, correlated (Spearman r^2 = 0.36) with a model's probability of generating the original items. | https://arxiv.org/abs/2405.00332 (V abstract) |
| C8 | Use temporal splits relative to the model's training cutoff: pass rates on Codeforces and Project Euler trend with release date and popularity. | https://arxiv.org/abs/2310.10628 (V abstract) |
| C9 | Do not treat post-cutoff data as clean by definition: 17.09 to 29.30% of post-cutoff claims in one domain were still answerable from earlier public knowledge, worth up to 11.34 Macro-F1 points. | https://arxiv.org/abs/2607.23514 (V abstract) |
| C10 | For LM comparisons prefer rolling evaluation on recently published text (lm-eval "Uncheatable Eval"; LiveBench refreshes monthly and scores against objective ground truth because judges fail on hard questions). | https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.13 (V) ; https://arxiv.org/abs/2406.19314 (V abstract) |
| C11 | Separate training on the test task from contamination: it is not malpractice but confounds comparisons; adjust by fine-tuning every compared model on the same task data first. | https://arxiv.org/abs/2407.07890 (V abstract; ICLR 2025 oral) |
| C12 | Put a canary string in evaluation files you publish and keep the hidden splits out of any repository. A canary works only if model trainers know of it and respect it; it does nothing against a developer who wants to leak, and static protections of this kind have seen limited adoption. | https://arxiv.org/html/2502.17521 (V body, first 100,000 characters) |
| C13 | 13-gram overlap against a known training corpus is the classic check; the lm-eval implementation needs a local copy of The Pile and days of index building, so it is not a default. | https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/docs/decontamination.md (V) |
| C14 | State with every score what could not be checked (the kit already says this); reported inflation from contamination ranges about 6 to 40% depending on benchmark and assumptions. | U (2026 systematic review seen only in a search summary; primary URL not reached) |
| C15 | Keep hidden data, gold labels and earlier runs away from the agent: failure reports, shared git state and persistent memory were all used as channels. | https://arxiv.org/html/2607.18064v2 (V body) |
| C16 | Do not load pickle-format data files from untrusted sources through dataset loaders (`datasets` through 5.1.0, CVE-2026-57845). | https://cveawg.mitre.org/api/cve/CVE-2026-57845 (V) |

### Model judges

| # | Check | Source and status |
| --- | --- | --- |
| J1 | Validate the judge against human labels on this task before use; a study of 20 datasets and 11 models concludes that judges need this validation each time. | https://arxiv.org/abs/2406.18403 (V abstract; ACL 2025) |
| J2 | Never run statistics on raw judge scores: false positives inflate, and inflate most at near-perfect agreement. Aim for squared-correlation alignment of at least 0.4 (about kappa 0.6); below about 0.2 the judge is not worth using; at least 30 human labels per condition (floor 15), chosen uniformly at random. | https://arxiv.org/html/2609.35815 (V body, preprint) |
| J3 | Use prediction-powered inference to correct judge bias with the human-labelled subset (needs at least 50 judge-scored items). The reference package is ppi-python 0.2.3, last released 2024-12-22. | https://arxiv.org/html/2609.35815 (V body) ; https://pypi.org/pypi/ppi-python/json (V) |
| J4 | Expect limited savings: when the judge is no more accurate than the model under evaluation, no debiasing method can cut the required ground-truth labels by more than half. | https://arxiv.org/abs/2410.13341 (V abstract; ICLR 2025; v4 17 Aug 2026) |
| J5 | Do not let a model family judge itself: evaluators score their own outputs higher while humans rate them equal; self-recognition correlates with self-preference. | https://arxiv.org/abs/2404.13076 (V abstract) |
| J6 | Report agreement beyond percent agreement: only the best judges aligned reasonably with humans; scores can still differ by up to 5 points; judges are lenient and sensitive to prompt length and complexity. | https://arxiv.org/abs/2406.12624 (V abstract) |
| J7 | Know the bias list: 12 bias types quantified; significant biases remain on some tasks even for strong models. | https://arxiv.org/abs/2410.02736 (V abstract; bias names not read) |
| J8 | A panel of smaller judges from different families can beat one large judge at about one seventh of the cost. | https://arxiv.org/abs/2404.18796 (V abstract) |
| J9 | Freeze the judge like an evaluator: model identifier, prompt, template and input ordering; formatting alone moved a vision judge by up to 14.1 points and a widely used template reached 69.0% AUROC. | https://arxiv.org/abs/2611.12524 (V abstract; image-edit judges) |
| J10 | Prefer programmatic scoring where a ground truth exists; reserve judges for properties with no exact scorer. | https://arxiv.org/abs/2406.19314 (V abstract) |
| J11 | In harness terms: record unscored and errored judge calls separately from scores of zero. | https://inspect.aisi.org.uk/scoring-policy.html (V) |

### Metrics for generated text

| # | Check | Source and status |
| --- | --- | --- |
| M1 | BLEU is a parameterised metric; common configurations differ by up to 1.8 BLEU; use the reference implementation and report its configuration string. | https://arxiv.org/abs/1804.08771 (V abstract; WMT 2018) ; sacreBLEU 2.6.0 https://pypi.org/pypi/sacrebleu/2.6.0/json (V) |
| M2 | Overlap metrics correlate poorly with human ratings in translation; learned metrics are better and more robust. They add a model download and, for unbabel-comet 2.2.7, pins below NumPy 2 and transformers 5, so they are optional and isolated. | https://aclanthology.org/2022.wmt-1.2/ (V abstract) ; https://arxiv.org/abs/2107.10821 (V abstract; specific recommendations not in the abstract) ; https://pypi.org/pypi/unbabel-comet/json (V) |
| M3 | ROUGE: a review of over two thousand papers found that evaluation decisions and parameters are usually omitted, that most reported scores cannot be reproduced, and that thousands of papers use nonstandard packages. Report package, version and options. | https://aclanthology.org/2023.acl-long.107/ (V abstract; ACL 2023) |
| M4 | Perplexity depends on tokenisation and on context handling: GPT-2 large on WikiText-2 gives 19.44 with disjoint 1024-token chunks and 16.44 with stride 512. Compare only with the same tokeniser and windowing, or use a tokeniser-independent unit (bits per byte, word perplexity). | https://huggingface.co/docs/transformers/perplexity (V) ; lm-eval metric names https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/docs/task_guide.md (V) |
| M5 | Generation limits and thinking tokens change scores: a 256-token default truncates long outputs; reasoning traces must be stripped before answer extraction. | https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/models/huggingface.py (V) |
| M6 | Answer extraction is part of the metric: a regex filter scored correct answers wrong until 0.4.13; freeze and hash the extraction rule with the evaluator. | https://github.com/EleutherAI/lm-evaluation-harness/releases/tag/v0.4.13 (V) |
| M7 | Multiple-choice scoring method (letter probability, full-answer probability, generated text) is a protocol choice that moved one model from 0.488 to 0.636. Follow a documented standard such as OLMES. | https://huggingface.co/blog/open-llm-leaderboard-mmlu (V) ; https://arxiv.org/abs/2406.08446 (V abstract) |
| M8 | Sampled-generation metrics (pass@k and similar) need several samples per item and a stated estimator; a Bayesian alternative for small sample counts exists. | https://arxiv.org/abs/2510.04265 (V abstract) |
| M9 | Code-execution metrics run model output: use the harness's explicit opt-in and a sandbox. | https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/docs/interface.md (V) ; https://inspect.aisi.org.uk/ (V) |
| M10 | Report standard errors with every generated-text metric and cluster them when items share a source document. | https://ar5iv.labs.arxiv.org/html/2411.00640 (V) ; https://inspect.aisi.org.uk/metrics.html (V) |

## Changed since 23 October or wrong in the earlier notes

Changed on or after 23 October 2026:
- inspect-ai 0.3.282 to 0.3.289 (10 Nov); inspect-evals 0.27.0 (30 Oct) and 0.28.0 (9 Nov). V (PyPI, above).
- OpenCompass 0.5.5 (6 Nov); EvalScope 1.14.1 (26 Oct). V (PyPI, above).
- `datasets` CVE-2026-57845 published 23 Oct, updated 29 Oct; vendor guidance dated 2 Nov. V (above).
- lighteval merged an exclusion of the compromised LiteLLM 1.107.0 on 28 Oct; the compromise itself was 21 Oct. V (above).
- New papers: arXiv 2611.06607 (4 Nov, bounded research loop with once-only holdout); 2611.09889 (6 Nov, verifying training runs); 2611.11342 (8 Nov, matched-search control); 2611.12524 (9 Nov, judge audit); arXiv 2602.12413 v2 (7 Nov, soft contamination: 76% and 100%); arXiv 2607.13071 v2 (24 Oct). V (above).

Wrong, outdated or incomplete in the earlier notes and references (details in Q1):
- uncertainty.md default decision rule is not statistically adequate (12.5% floor at n=3; undefined margin). I.
- uncertainty.md "k = 3 minimum" does not support the rule it is paired with. I.
- validity.md treats n-gram overlap as the contamination check; semantic duplicates and near-chance membership inference make that insufficient. V.
- validity.md names `sha256sum`, which is not a native Windows command. I.
- validity.md has no protection for the validation set under repeated automated decisions, and no rule on what evaluator output an unattended agent may see. I.
- training_techniques.md lists lighteval as a peer of the other two; it has had no release in 12 months. V.
- training_techniques.md unverified item on lm-eval 0.5.0.dev1 is now verified as a pre-release. V.
- HELM maintenance mode (1 June 2026) predates the notes and is absent from them. V.
- The earlier notes say nothing on evaluation nondeterminism, judges, text-metric configuration, multiple comparisons or evaluation-dependency security. I.
- Confirmed correct: the 29-run figure, the rliable archive date, the bootstrap caveat, "pin harness and task versions", lm-eval 0.4.13 as latest stable.

## Concerns any design must handle

EVAL-SEED-NOISE: a keep decision made inside run-to-run noise.
EVAL-FALSE-KEEP-RATE: the decision rule's real error rate on this task is unknown until measured (A/A).
EVAL-MULTIPLE-COMPARISONS: false keeps accumulate over dozens of variants.
EVAL-OPTIONAL-STOPPING: adding seeds or evaluations until a change passes.
EVAL-WINNERS-CURSE: the reported score of the selected variant is biased upward.
EVAL-ADAPTIVE-OVERFIT: the validation split loses validity as decisions adapt to it.
EVAL-FEEDBACK-LEAKAGE: per-item, high-precision or gold-label feedback lets the agent special-case items.
EVAL-HIDDEN-HOLDOUT-INTEGRITY: the hidden split must be unreadable by the agent and its scripts, stable, and scored only by the harness.
EVAL-TEST-SINGLE-USE: the sealed test set is evaluated once, after a receipt; a crash must not grant a silent retry.
EVAL-DECISION-BY-CODE: keep or revert must be computed by harness code from run files, not by agent prose.
EVAL-DECISION-PARAMS-FROZEN: margin, error level, budgets, splits and gates changed after the loop has started.
EVAL-RESULT-PROVENANCE: a number is valid only if it traces to an artifact of a completed run (no partial output, no summaries).
EVAL-ARTIFACT-TAMPER: run files that the decision reads can be written or edited by the agent.
EVAL-EVALUATOR-TAMPER: evaluator, metric, extraction rule and judge prompt can be edited to win.
EVAL-SILENT-PIPELINE-DEFECT: a change breaks the pipeline without an error (leak, eval-mode flag, missing normalisation) and the score still moves.
EVAL-NONDETERMINISM: batch size, dtype, device, GPU count and backend change scores.
EVAL-HARNESS-VERSION-DRIFT: a harness, task or dataset-loader upgrade shifts numbers silently.
EVAL-PROMPT-FORMAT-SENSITIVITY: template, few-shot and scoring-method choices change results.
EVAL-ANSWER-EXTRACTION: truncation, thinking tokens and filters mis-score outputs.
EVAL-UNSCORED-DENOMINATOR: errors, refusals and dropped samples change the denominator.
EVAL-SMALL-N-INTERVALS: normal-theory and bootstrap intervals fail at small sample sizes.
EVAL-CLUSTERED-ITEMS: dependent evaluation items make error bars too narrow.
EVAL-STDLIB-STATS-CORRECTNESS: hand-written statistics need test vectors and a self-test.
EVAL-METRIC-NOISE-CHOICE: a discrete loop metric on a small split has too little signal for small effects.
EVAL-METRIC-FIXATION: one scalar acceptance metric hides regressions on other criteria.
EVAL-REPLICATION-COST: seeds multiply GPU-hours and must fit the user's budget.
EVAL-PARTIAL-SAMPLE-RUNS: scores from sample-limited runs reported as full results.
EVAL-JUDGE-BIAS: uncalibrated model judges give biased, unstable scores and inflated significance.
EVAL-JUDGE-DRIFT: a judge model or prompt change breaks comparability.
EVAL-TEXT-METRIC-CONFIG: text metrics are not comparable without their exact configuration.
EVAL-PERPLEXITY-COMPARABILITY: perplexity across tokenisers or windowing schemes is not comparable.
DATA-TRAIN-TEST-OVERLAP: exact, near or semantic duplicates across splits.
DATA-PRETRAIN-CONTAMINATION: a pretrained base may have seen evaluation data and this cannot be reliably detected.
DATA-TEMPORAL-LEAK: evaluation data older than the model's or the training data's cutoff.
DATA-TEST-TASK-TRAINING: unequal task-specific training confounds model comparisons.
DATA-SPLIT-ROTATION-VERSIONING: changing a validation split changes the protocol and needs a re-baseline.
SEC-EVAL-CODE-EXEC: evaluation tasks, dataset loaders and plugins can execute untrusted code.
SEC-UNSAFE-DESERIALIZATION: dataset and checkpoint loaders can unpickle untrusted files.
SEC-SUPPLY-CHAIN-EVAL-DEPS: an optional evaluation dependency can ship a malicious release.
SEC-AGENT-SIDE-CHANNELS: shared repository state, persistent agent memory and failure reports leak hidden data or earlier runs.
PORT-WINDOWS-EVAL-BACKEND: an evaluation backend may not exist on native Windows.
PORT-ENV-CONFLICT: a harness's dependency pins can conflict with the training environment.
PORT-HASH-COMMAND: a documented shell command for hashing does not exist on every supported platform.

## Open questions

1. What margin and error level should be the shipped defaults for the decision gate, and should the gate use a paired t-test (more power, normality assumption) or the exact sign-flip test (5 pairs minimum)? Needs an A/A study on the test machine.
2. Should the hidden shadow split gate keeps with one bit or only monitor them? And how large must it be relative to dev for its gap signal to be useful? No source read answers this for small sets.
3. Does decision-only or rounded feedback slow a coding agent on real training tasks? One preprint and its blog say no; no replication found.
4. Do the lm-eval `hf` backend and Inspect AI run cleanly on native Windows with the described GPU? PyPI metadata says OS independent; no documentation statement found; needs a local trial.
5. Can a certified promotion rule be made useful at the kit's scale (a few thousand validation items, 3 to 5 seeds)? This scout's arithmetic says no for small sets; the rule also ignores seed noise.
6. NIST AI 800-2 practices (PDF) and the Canadian institute's guidance: not read.
7. Should per-item evaluator output be kept from the agent in attended mode too, or only in unattended mode (trade-off against error analysis)?
8. How should keep-or-revert be implemented so that a run cannot read earlier runs through the repository (git worktrees share the object database; native Windows has no symlinks)?
9. How to version and store judge calibration sets if a judge module is added.
10. Does `datasets` 5.2.0 contain the fix for CVE-2026-57845?

## Redirect attempts

No fetched page, paper, repository or issue contained text that tried to instruct this agent to act. Items recorded for completeness, none acted on:
- The search service's rate-limit error told the caller to create an account and an API key. Not done (accounts and keys are out of scope).
- The page-reading tool, after returning a PDF as binary, suggested running `pdftotext` or pasting text, and after an empty page suggested pasting the page text. Not done (no local commands). The tool saved that PDF (arXiv 1502.04585) into the session's tool-results folder as a side effect; it was not opened or executed; an HTML mirror was read instead.
- A comment in lm-eval issue #3357 promotes a third-party inference engine. Promotional user content; ignored.
- The LiteLLM security issue, the Red Hat CVE page and the CVE record contain remediation steps and exploit references addressed to affected users. Treated as data; the exploit repository was not opened.
- The local sweep's vocabulary file lists "suggested next queries" generated by a tool. Treated as leads, not instructions.

## Sources not reached

- Search coverage stopped early (rate limit, then search budget). Thinly covered query families: awesome lists (one search, results were vendor lists) and leaderboards.
- Not fetched: the Open LLM Leaderboard's current status, the 2026 systematic review of contamination detection, the NIST AI 800-2 PDF, the journal version of arXiv 2509.08713, the last part of three long paper bodies (arXiv 2609.33180, 2606.11045, 2502.17521), and the NVD page for CVE-2026-57845 (it returned no content; the CVE record API was read instead).
