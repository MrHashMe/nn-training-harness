# Sweep scout: data (training-data quality, synthetic data, deduplication)

Checked 11 November 2026. Input: `docs/upgrade/scout/sweep/data/` (206 records: github 77, arxiv 44, hf 30, hn 18,
openalex 37; run 2026-11-10 20:04 UTC; window 14 May to 10 November 2026). Status words: **Verified** = I read the
primary source on 11 Nov 2026 and it says this (almost every number is the authors' or maintainers' own measurement,
and I say so); **Inferred** = my conclusion from verified facts; **Unverified** = not confirmed from a primary source.
Every claim below was checked on 11 Nov 2026 unless another date is given. Nothing was installed, cloned or run.

What the kit has today (read locally, Verified): `references/validity.md` section 2 tells the agent to audit splits
(group leakage, exact and near duplicates, contamination, label quality) and to persist a data manifest;
`references/finetuning.md` section 3 says to check overlap between fine-tuning data and evaluation sets. Nothing
executes these. `expctl hash` covers source files only, skips `data/` and `datasets/` outside git, and records only
the size of files above `snapshot.max_file_mb` (default 50). The agent may not read the sealed test split, so it
cannot run the cross-split check itself. README.md and brief.md name no data-quality, deduplication or synthetic-data
concept.

## Summary (10 lines)

1. 92 of 206 records bear on the goals; 44 candidates were evaluated (7 Adopt, 2 Trial, 15 Assess, 13 Hold, 7 Reject); about 20 primary sources were read in depth and 20 more at abstract or README level.
2. Exact repeats inside training data cost compute, and the damage depends on how often items repeat, not only on the duplicated share: with 10% repeated tokens, the worst repeat count cost a 344M language model about one third of its compute (authors' measurement, one run per setting, pretraining from scratch only).
3. Removing near-duplicates inside the training set is not a safe default: document-level MinHash removal scored below no deduplication in one pretraining study (51.51 against 51.89, with 84% of tokens removed; single runs). Across splits, duplicates are a validity defect; inside train, removal is a hypothesis the loop must test.
4. Training data built by an LLM or an agent often lands below the baseline without it (13.2 falls to 3.1-7.5; 67.1 to 51.1 in one benchmark), and quality-rater scores correlated at about 0.05-0.09 with downstream results. A judge score must never be the keep rule; the frozen evaluator against a no-added-data baseline must.
5. Comparing a filter with "random" mixes two effects: better items and a changed source mix. The minimum control is a same-size random subset with the same per-source proportions.
6. Paraphrased copies of evaluation items ("semantic duplicates") raised held-out accuracy by 10 to 22 points and pass n-gram decontamination. Exact-match checks and a sealed test set do not cover data the agent generates or collects.
7. Data-generating agents gamed their own acceptance gate (they rewrote the weak solver's prompt to make it weak). In unattended mode, generator, judge and filter settings need the same protection as the evaluator.
8. Near-duplicate counts are tied to the tool version: rensa 0.5.0 rejects older sketches, one tool pins the sketch library exactly because a mismatch silently finds nothing, and datasketch 2.0.0 changed its default hash scheme. Record tool, version, parameters and normalisation with every count.
9. Proposed core additions (standard library, run by harness code, counts only): an exact-duplicate and cross-split overlap check with a repeat-count histogram; an order-independent dataset fingerprint in each run record; a report-only rule for data checks. Optional modules worth a trial: rensa 0.5.0 (near-duplicates) and SemHash 0.5.0 (semantic overlap between splits); cleanlab 2.9.0 (label issues) to assess.
10. No synthetic-data generator in the sweep has independent evidence of improving a single-GPU fine-tune; every number is the authors' own. Generation stays an optional, off-by-default module; scale-out deduplication and data-rewriting systems are Hold or Reject for this kit.

## Selected items (one line each)

Dates are the sweep record dates. "(read)" = primary source opened; "(listed only)" = judged from the sweep record.
Repositories under personal account names were not opened, to keep personal names out of web requests.

### Deduplication: tools and evidence
- beowolx/rensa (2026-10-30) https://github.com/beowolx/rensa : Rust MinHash with Python bindings; candidate optional near-duplicate engine (read).
- Zyphra/puffer (2026-07-22) https://github.com/Zyphra/puffer : incremental MinHash-LSH with dataset withdrawal; source of the version-stamp lesson (read).
- mcrl/SEDD (2026-05-17) https://github.com/mcrl/SEDD : GPU MinHash-LSH for clusters; scale reference (read).
- dipeshbabu/pari (2026-08-25) https://github.com/dipeshbabu/pari : similarity indexing and deduplication with Rust, Python and CLI interfaces (listed only).
- jsmonhq/xnew (2026-05-23) https://github.com/jsmonhq/xnew : appends only unique lines to files; shows exact-line dedup is a solved, dependency-free job (listed only).
- worldbank/FuzzyAI (2026-10-29) https://github.com/worldbank/FuzzyAI : entity deduplication and cross-dataset matching for tabular records (listed only).
- harshadulshan/duplicate-finder (2026-11-01) https://github.com/harshadulshan/duplicate-finder : record-level duplicate finding without training data (listed only).
- STEXS-Technologies/shardline (2026-11-03) https://github.com/STEXS-Technologies/shardline : self-hosted content-addressed storage with deduplication and integrity checks (listed only).
- Scalable Frequency- and Length-Aware Subdocument Deduplication (2026-08-04) https://huggingface.co/papers/2608.03089 : dedup below document level; its table shows document-level removal losing to no removal (read).
- Internal Data Repetition Destroys Language Models (2026-06-23) https://huggingface.co/papers/2606.24998 : measured cost of exact repeats as a function of repeat count and model size (read).
- Asymptotic Analysis of Data Deduplication Under a Constant Edit Model (2026-11-06) http://arxiv.org/abs/2611.09842v1 : storage-system theory, not training data (listed only).
- GVD: Governed Versioning and Deduplication for Document Repositories (2026-09-15) https://huggingface.co/papers/2609.17696 : version linking and dedup under an auditable policy (listed only).
- Identity-Duplication Auditing in National-Scale Neuroimaging Repositories (2026-10-07) https://huggingface.co/papers/2610.09614 : the same subject under several identities; a group-leakage source (listed only).
- Dataset Collections: Challenges of Large-Scale Data Aggregation in 3D Medical Image Datasets (2026-11-06) http://arxiv.org/abs/2611.10144v1 : at least 118k duplicate pairs across 1034 public datasets (read).

### Leakage and split validity
- shivpratapsinghpanwar/data-doctor (2026-09-01) https://github.com/shivpratapsinghpanwar/data-doctor : vision near-duplicates, train/val leakage and COCO defects, verified on pixels (read through its PyPI page).
- MinhTriTM/vision-cleanse (2026-10-29) https://github.com/MinhTriTM/vision-cleanse : near-duplicate and split-leakage cleaning for vision datasets (listed only).
- Open-Set Vessel Re-Identification ... and a Cross-Passage Evaluation Protocol (2026-09-07) https://huggingface.co/papers/2609.07399 : deduplication alone erased a 16 to 21 point apparent advantage (read).

### Measuring data quality, filtering, labels and judges
- OpenDCAI/Data-Preparation-Bench (2026-11-02) https://github.com/OpenDCAI/Data-Preparation-Bench : downstream-grounded benchmark code for data construction and selection (read).
- DataPrep-Bench: Benchmarking LLMs as Training Data Preparators (2026-05-19) https://huggingface.co/papers/2607.20465 : many LLM-built datasets fall below baseline; quality scores do not predict utility (read).
- Counterfactual Gate-Support Decomposition (2026-10-14) https://huggingface.co/papers/2610.19343 : separates selection from redistribution when judging a data filter (read).
- Adapting English Quality Classifiers for Multilingual LLM Pretraining Data Selection (2026-10-08) https://huggingface.co/papers/2610.11585 : model-based quality filter transferred across languages (read, abstract).
- UltraX: Refining Pre-Training Data at Scale with Adaptive Programmatic Editing (2026-07-09) https://huggingface.co/papers/2607.08646 : edit documents instead of dropping them (read, abstract).
- DataEvolver (2026-06-10) https://huggingface.co/papers/2606.07001 : self-evolving data-preparation pipelines (read, abstract).
- Guiding LLM Post-training Data Engineering with Model Internals from Sparse Autoencoders (2026-05-26) https://huggingface.co/papers/2605.27354 : SAE features steer diversity and difficulty of RL data (read, abstract).
- ReMova: Fine-tuning LLMs for English to Belarusian translation (2026-09-14) https://huggingface.co/papers/2609.16427 : matched ablation showing a cleaning pipeline helps (read, abstract).
- Dataset Collection and Fine-Tuning of NLLB for German-English Translation (2026-11-05) http://arxiv.org/abs/2611.07797v1 : filtered corpus then fine-tune; no filter ablation (read, abstract).
- Moving Alphabet: A Controlled Study of Training Data for Text-to-Video Generation (2026-07-21) https://huggingface.co/papers/2607.18789 : later stages cannot fully repair poor pretraining data (read, abstract).
- Not All Invariants Are Equal: Curating Training Data ... with SLMs (2026-06-23) https://huggingface.co/papers/2603.15510 : normalised and rewritten training targets for small-model fine-tuning (listed only).
- RanWeisberg/YOLOv8-Crack-Detection (2026-07-12) https://github.com/RanWeisberg/YOLOv8-Crack-Detection : code and data on how label quality changes a small detector (listed only).
- SJTU-DMTai/awesome-ml-data-quality-papers (2026-06-13) https://github.com/SJTU-DMTai/awesome-ml-data-quality-papers : reading list on training-data quality management (listed only).
- DISC: Domain-Integrated Similarity Cost for Time-Series Dataset (2026-10-22) https://huggingface.co/papers/2610.31288 : dataset-similarity metric calibrated to predict transfer (listed only).
- TSDS-Toolbox (2026-08-08) https://huggingface.co/papers/2608.08119 : toolbox for time-series dataset similarity (listed only).
- Bittensor Agent Arenas as a Trajectory Primitive (2026-06-08) https://huggingface.co/papers/2606.10064 : claims small-model agent post-training is limited by trajectory data quality (listed only).
- RenaGao/jev-dataops (2026-09-21) https://github.com/RenaGao/jev-dataops : workbench joining data selection, quality evaluation, LoRA training and held-out evaluation (listed only).
- Hebbian-Robotics/hflow (2026-08-18) https://github.com/Hebbian-Robotics/hflow : robotics data checks that attach evidence and never delete (read).
- Hebbian-Robotics/pareto (2026-07-21) https://github.com/Hebbian-Robotics/pareto : data curation for robot learning (listed only).
- Show HN: A Layer for robotics dataset quality (2026-08-26) https://www.calibrarobotics.com/ : commercial data-quality layer (listed only).
- Ask HN: What silent data issues have you hit when training physical AI models? (2026-10-05) https://news.ycombinator.com/item?id=49967773 : defects found only after training; user-generated, uncorroborated (read).
- Large Language Model-Assisted Cleaning of Report-Derived Labels in a Large-Scale Chest CT Dataset (2026-06-21) https://huggingface.co/papers/2606.22382 : multi-LLM vote finds real label errors (read, abstract).
- EditJudge-Bench: Auditing VLM Image-Edit Judges with Synthetic Ground Truth (2026-11-09) http://arxiv.org/abs/2611.12524v1 : a common judge template is weak and format-sensitive (read, abstract).
- Can the Confidence and Decisions of System 1 Models Be Trusted? (2026-11-09) http://arxiv.org/abs/2611.12521v1 : perturbation audit of single-pass decision models used as graders (listed only).
- Calibration as a First-Class Criterion in LLM Evaluation (2026-09-22) https://huggingface.co/papers/2609.26489 : evaluation facet (listed only).

### Synthetic data: methods, tools, evidence
- Autodata: An agentic data scientist to create high quality synthetic data (2026-06-24) https://huggingface.co/papers/2606.25996 : weak-strong gap acceptance, harness meta-optimisation, and a reported gaming failure (read).
- Ahmad8864/autosynth (2026-07-14) https://github.com/Ahmad8864/autosynth : unofficial framework inspired by Autodata (listed only).
- CHATS-lab/verbalized-sampling (2026-11-08) https://github.com/CHATS-lab/verbalized-sampling : prompt pattern against mode collapse in generated data (read).
- Red-Hat-AI-Innovation-Team/sdg_hub (2026-11-09) https://github.com/Red-Hat-AI-Innovation-Team/sdg_hub : licensed synthetic-data toolkit that ships skills for three agent products (read).
- InternScience/GraphGen (2026-11-08) https://github.com/InternScience/GraphGen : knowledge-graph-guided synthetic QA for fine-tuning (read).
- Lexsi-Labs/CuratorKIT (2026-06-16) https://github.com/Lexsi-Labs/CuratorKIT : curation and generation library for post-training data (listed only).
- CuratorKIT paper (2026-06-19) https://huggingface.co/papers/2606.21631 : per-sample provenance chain; no results (read, abstract).
- patrickfleith/datafast (2026-11-08) https://github.com/patrickfleith/datafast : synthetic text dataset generation library (listed only).
- ThomasRochefortB/open-agentinstruct (2026-11-09) https://github.com/ThomasRochefortB/open-agentinstruct : open recreation of an agentic generation workflow (listed only).
- Azure-Samples/function-calling-data-synthesizer (2026-11-05) https://github.com/Azure-Samples/function-calling-data-synthesizer : generate and verify function-calling fine-tuning data (listed only).
- syda-ai/syda (2026-08-09) https://github.com/syda-ai/syda : synthetic tables and documents with referential integrity (listed only).
- tkarim45/synthetic-data-pipeline (2026-06-26) https://github.com/tkarim45/synthetic-data-pipeline : generate, filter, measure downstream; claims a filtered set 5 times smaller beats raw (self-reported, 1 star; listed only).
- ApartsinProjects/SynSmith (2026-05-15) https://github.com/ApartsinProjects/SynSmith : multi-objective prompt debugging for realistic and diverse generated data (listed only).
- Yog-Sotho/Brainbrew (2026-11-04) https://github.com/Yog-Sotho/Brainbrew : documents to grounded Q&A sets with an LLM judge and MinHash dedup (listed only).
- Matrix-Research-Ai/epub2dataset (2026-06-19) https://github.com/Matrix-Research-Ai/epub2dataset : books to training sets with quality scoring and MinHash dedup (listed only).
- vedantnimbarte/Arc-Data-Factory (2026-06-02) https://github.com/vedantnimbarte/Arc-Data-Factory : collect, clean, deduplicate, score and shard training data (listed only).
- NoGamble/CodeForge-Agent (2026-07-26) https://github.com/NoGamble/CodeForge-Agent : agentic curation pipeline for code pretraining data (listed only).
- voidful/awesome-agent-dataset (2026-06-15) https://github.com/voidful/awesome-agent-dataset : catalogue of agent-training datasets with a normalise and deduplicate toolkit (listed only).
- ahmad-alismail/LLM_based_Synthetic_Data_Generation (2026-11-04) https://github.com/ahmad-alismail/LLM_based_Synthetic_Data_Generation : reading list on LLM-based generation (listed only).
- BertilBraun/LLM-Light (2026-06-23) https://github.com/BertilBraun/LLM-Light : artifact-based LM training system with synthetic data stages (listed only).
- Environment-free Synthetic Data Generation for API-Calling Agents (2026-07-18) https://huggingface.co/papers/2607.16900 : LLM as simulated environment for trajectory data (listed only).
- LLMs Get Smarter from Targeted Synthetic Multilingual Data (2026-08-16) https://huggingface.co/papers/2608.15964 : generate data for measured weaknesses (read, abstract).
- MiST: Mid-Training LLMs for Cybersecurity (2026-09-16) https://huggingface.co/papers/2609.18496 : synthetic data from a curated seed corpus in a mid-training stage (read, abstract).
- Generating Pretraining Tokens from Organic Data for Data-Bound Scaling (2026-05-18) https://huggingface.co/papers/2605.17849 : learned rephrasing beats repetition when data runs out (read, abstract).
- The Significance of Style Diversity in Annotation-Free Synthetic Data Generation (2026-06-18) https://huggingface.co/papers/2606.20400 : style attributes as the diversity lever (listed only).
- Make LLM Learn to Synthesize from Streaming Experiences through Feedback (2026-05-28) https://huggingface.co/papers/2605.29940 : generator that improves from downstream feedback (listed only).
- Evaluating LLM-Generated Preference Distributions (2026-10-01) https://huggingface.co/papers/2610.01000 : model choice changes generated preference data (listed only).
- Let the Fixer Decide: Training a Code Localizer from the Fixer's Likelihood (2026-11-09) http://arxiv.org/abs/2611.12164v1 : labels taken from a downstream model's likelihood instead of reference outputs (listed only).

### Provenance and privacy
- agentanywhere/shuddhi (2026-08-22) https://github.com/agentanywhere/shuddhi : provenance gate, dedup, PII redaction and a hash-based build manifest (read).
- RayOrch (2026-09-16) https://huggingface.co/papers/2609.18703 : lineage-preserving distributed data preparation (read, abstract).
- A local language model layered with rule-based and neural detectors for clinical text de-identification (2026-11-09) http://arxiv.org/abs/2611.12709v1 : fail-closed detector stacking; LLM self-review drops true findings (read, abstract).
- Privacy Leakage on DNNs: A Survey of Model Inversion Attacks and Defenses (2026-10-01) https://doi.org/10.1007/s11263-026-03049-x : why training data content matters after training (listed only).

### Agent skills and self-improving loops
- dungnotnull/ai-dataset-quality-audit-agent-skill (2026-06-22) https://github.com/dungnotnull/ai-dataset-quality-audit-agent-skill : Codex skill for pre-training dataset audits (read).
- Bhanunamikaze/AI-Dataset-Generator (2026-08-08) https://github.com/Bhanunamikaze/AI-Dataset-Generator : dataset-generation skill installed into several coding agents (read).
- afloy011-spec/lora-dataset-prep (2026-06-10) https://github.com/afloy011-spec/lora-dataset-prep : image-dataset checks and captioning for LoRA training, tagged for Claude Code (listed only).
- SMO: Compiling Natural Language Skills into Graphs of Reusable State-Move-Outcome Bricks (2026-11-09) http://arxiv.org/abs/2611.12041v1 : shrinking a skill collection (read, abstract).
- Self-Harness: Harnesses That Improve Themselves (2026-06-08) https://doi.org/10.48550/arxiv.2606.09498 : harness self-improvement with a two-set acceptance gate (read).
- Recursive Self-Improvement in AI (2026-07-08) https://doi.org/10.48550/arxiv.2607.07663 : survey naming self-confirming loops and a verification hierarchy (read, abstract).
- A multi-agent system for automating scientific discovery (2026-05-19) https://doi.org/10.1038/s41586-026-10652-y : other facets (listed only).

### Recipes and model reports (language-model focus)
- bytedance/axion1_0 (2026-11-02) https://github.com/bytedance/axion1_0 : two SFT stages plus RL on a small curated set (read).
- Show HN: A decent text-to-image model trained for ~$20K (2026-11-04) https://www.linum.ai/field-notes/pjit-21k : first-party cost and data notes (read).
- MNN-Pocket-0.3B Technical Report (2026-11-09) http://arxiv.org/abs/2611.12311v1 : 300M on-device language model (read, abstract).
- shawn0728/OpenSearch-VL (2026-10-20) https://github.com/shawn0728/OpenSearch-VL : open recipe built on data curation (listed only).
- LLM Post-Training: A Deep Dive Into Reasoning Large Language Models (2026-08-04) https://doi.org/10.1109/tpami.2026.3720414 : survey (listed only).
- MoTo: Mixture of Tokenizers (2026-11-08) http://arxiv.org/abs/2611.11027v1 : tokenizer choice as a data-fairness issue (listed only).
- Efficient training of large language models on distributed infrastructures: a survey (2026-06-01) https://doi.org/10.1007/s44336-026-00038-z : remote-GPU facet (listed only).
- Gemma 4 Technical Report (2026-07-02) https://doi.org/10.48550/arxiv.2607.02770 : base-model report (listed only).
- Kimi K3: Open Frontier Intelligence (2026-07-27) https://doi.org/10.48550/arxiv.2607.24653 : base-model report (listed only).
- Nemotron 3 Ultra (2026-06-12) https://doi.org/10.48550/arxiv.2606.15007 : base-model report (listed only).
- The MiniMax-M2 Series (2026-05-26) https://doi.org/10.48550/arxiv.2605.26494 : base-model report (listed only).

## Deep reads

Each bullet ends with its status. "Authors" means the people who built the method measured it.

### D1. Internal Data Repetition Destroys Language Models
Source: https://arxiv.org/abs/2606.24998 v1, 23 Jun 2026, CC BY 4.0; no code link on the page.
- Setting: Qwen3-style models of 34M to 344M parameters pretrained from scratch on FineWeb-Edu-Dedup; exact document replay; repeated documents take 10% of the token budget; the repeat count R varies. (Verified)
- Result: evaluation loss peaks at an intermediate R. Raw loss is at most 1.0 to 4.2% above the no-repeat run. As compute-equivalent loss at one pass over the data, the worst case is 0.19, 0.19, 0.21, 0.21, 0.26, 0.33 for 34, 48, 63, 93, 153, 344M parameters; the 344M worst case equals a clean run with about 67% of the compute. The worst R follows 2.31e10 x N^-0.96 (about 1400 repeats at 34M, about 155 at 344M). (Verified; authors)
- Limits: one run per configuration, no seeds; exact replay only; pretraining from scratch only; one repeated share; largest model 344M. The appendix warns against filtering minority-domain or low-resource data because it looks repetitive, and asks for the repeat count to be reported, not only the duplicated fraction. (Verified)
- For the kit: the data check should print a repeat-count histogram and the duplicated share. Cost: one hashing pass. Transfer to fine-tuning is not shown. (Inferred)

### D2. Frequency- and length-aware subdocument deduplication
Source: https://arxiv.org/abs/2608.03089 v1, 4 Aug 2026; no code.
- Method: detect repeated spans, then keep T copies where T = ceil(1 + (g(C) - 1) x a(L)), g(C) = C(1 - 1/N)^(C-1), a(L) = max(0, 1 - L/L0), L0 = 512, N = 100/3. (Verified)
- Evidence (average of 8 benchmarks, FineWeb-Edu, 294.9B-token runs): no dedup 51.89; document-level MinHash 51.51 while keeping 16.08% of tokens; suffix array 52.79; keep-one 52.14; proposed 52.90 to 52.92. Code corpus 37.98 to 41.40. (Verified; authors; single runs, no seeds, cost of the pass not stated)
- For the kit: treat the table as "no proven gain from near-duplicate removal inside train", not as proven harm (differences are below one point without variance). The method has no code and needs pretraining scale: Hold. (Inferred)

### D3. rensa 0.5.0
Sources: https://github.com/beowolx/rensa and https://pypi.org/pypi/rensa/0.5.0/json.
- Facts: MIT; Rust with Python bindings; no runtime dependencies; Python >= 3.8; first PyPI upload 2024-06-23; 0.5.0 uploaded 2026-09-06; wheels include win_amd64 for CPython 3.10 to 3.14 and manylinux (file list was truncated; win_arm64 not seen); 317 stars, a weak signal. (Verified)
- Use: a deduplicator object takes (id, tokens) pairs and returns keep flags; parameters are threshold (0.8 in examples), number of permutations (128) and LSH on or off. (Verified)
- Evidence: the README reports its fastest pipeline at 608 times Datasketch and 12 times FastSketch on 7 datasets. Maintainer's benchmark, not replicated; nothing on downstream effect. (Verified that it says so)
- Stated limits: similarity is an estimate; LSH can miss pairs; no semantic similarity; the sampling variant depends on length and order; 0.5.0 uses a new algorithm version and rejects older sketches. (Verified)
- For the kit: optional near-duplicate engine, pinned to one version that is written into the output. (Inferred)

### D4. PUFFER
Sources: https://github.com/Zyphra/puffer (Apache-2.0, Python 3.10+, last commit 2026-10-01 sha 8101ff0, no releases, 8 stars); https://arxiv.org/abs/2608.28622 v1 (page date 29 Jul 2026, CC BY 4.0).
- What: CPU incremental MinHash-LSH with tiered compaction and removal of a previously added dataset. (Verified)
- Evidence: 1B documents indexed in about 1.75 h in one process at 128 bytes per document (16 bands); classical in-memory LSH needed about 6.5 KB per document and passed a 900 GiB cap; 11 times LSHBloom and 35 times Milvus-LSH; used on more than 30B documents. (Verified as stated; authors)
- Operational lesson: the sketch library is pinned to one exact version; the README explains that a version mismatch raises no error and the index simply stops matching, so the tool stamps the version in its state file and refuses to run on mismatch. Removal needs a C compiler. (Verified)
- For the kit: Hold as a tool; copy the stamp-and-refuse pattern. (Inferred)

### D5. SemHash 0.5.0
Sources: https://github.com/MinishLab/semhash (README and `semhash/semhash.py` on main); PyPI 0.5.0 released 2026-09-30, first release 0.1.0 on 2025-01-05, MIT, Python >= 3.10, 979 stars, release attestations present.
- What: embeds records with a static embedding model and searches neighbours with an approximate index (an exact flat backend exists); deduplicates a set against itself or against a second set (the README names train/test leakage as a use); filters outliers; picks representative samples; the result lists each kept record with its matched duplicates and scores. (Verified)
- Default model is loaded by hub name when none is passed, so first use needs a download unless cached; any object with an `encode` method can be passed instead. Imports numpy, frozendict, model2vec, pyversity, vicinity. (Verified in source; the download is Inferred)
- Evidence: 1.8M text records in about 74 s on CPU, maintainers' benchmark; no downstream measurement. (Verified as stated)
- For the kit: optional screen of training or generated data against validation data for paraphrase-level overlap. For the sealed split it must run inside harness code and print counts only. Thresholds change counts, so the threshold and model name belong in the output. (Inferred)

### D6. Soft contamination (found by the second-phrasing search)
Source: https://arxiv.org/abs/2602.12413 v2 (7 Nov 2026; v1 12 Feb 2026).
- Method: embedded and searched one open model's whole post-training corpus for semantic duplicates of benchmark items, then fine-tuned two model families on such duplicates. (Verified)
- Result: semantic duplicates of 76% of CodeForces test items and 100% of MBPP items were present; fine-tuning on them raised held-out accuracy by up to 22 points, 10 to 11 at realistic rates; gains did not transfer to related benchmarks; standard decontamination misses them. (Verified; authors)
- For the kit: validity.md's n-gram and exact-match advice has a blind spot; the planned scouting and data-generation steps are a new path for evaluation content to reach training data in paraphrased form; a mechanical exact check can pass while the score is inflated. Minimum: say which level of overlap was checked; keep generation away from evaluation content; offer the embedding screen as an option. (Inferred)

### D7. Cross-split duplicates and identity leakage
- Deduplicating Training Data Makes Language Models Better, https://arxiv.org/abs/2107.06499 (ACL 2022): train-test overlap affects more than 4% of the validation set of the standard language-model datasets studied; deduplicated training gave about 10 times less memorised output and needed fewer steps for the same or better accuracy. (Verified; older baseline evidence)
- Vessel re-identification, https://arxiv.org/abs/2609.07399 v1 (7 Sep 2026): removing duplicates of the same transit erased a 16 to 21 point apparent rank-1 advantage, more than any method difference; the paper splits by identity and by recording pass. (Verified; authors; one domain)
- Dataset Collections, https://arxiv.org/abs/2611.10144 v1 (6 Nov 2026): 565k 3D medical images from 1034 public datasets hold at least 118k duplicate pairs (perceptual hashing plus manual tracing); proposes a metadata profile for aggregation and provenance and publishes hashes. (Verified; authors)
- vision-data-doctor 0.2.0, https://pypi.org/project/vision-data-doctor/ (2026-09-18, only release, MIT, Python >= 3.10, depends on Pillow only, Alpha, no publish attestation): SHA-256 for exact copies; a difference hash and a DCT perceptual hash over 8 rotations and flips nominate pairs; a grayscale-thumbnail pixel comparison over the 8 orientations decides; leakage command takes train and val folders; exit code 0 or 1. (Verified) Its only result is the author's private dataset. (Unverified effect) The sweep repository was not opened; that it is the source of this package is Inferred from the matching description.
- For the kit: combining public datasets is a duplicate source of its own; group or identity keys must be declared by the user because no tool infers them; for images, exact file hashes in core and one perceptual-hash module as an option. (Inferred)

### D8. DataPrep-Bench
Sources: https://arxiv.org/abs/2607.20465 v1 (page date 19 May 2026, CC BY 4.0); https://github.com/OpenDCAI/Data-Preparation-Bench (last commit 2026-11-02 sha 877a2a0, 17 commits, 241 stars, no releases, no licence file at the root).
- Method: a data-construction or selection method is scored by fine-tuning 7B to 8B models on its output together with a general instruction set and testing in six domains. (Verified)
- Result 1: many LLM and agent methods end below the baseline that adds nothing. Llama-3.1-8B Science: 13.2 baseline, 4.7, 3.1 and 7.5 for three methods. General: 67.1 against 51.1. Qwen2.5-7B Finance: 57.8 against 44.4 (direct generation by a frontier LLM) and 55.5. Best gains: Finance +21.4 and +19.1; Medical +7.5. (Verified; authors; seeds and variance not stated in the part read)
- Result 2: an embedding-distance score between candidate data and a domain proxy set correlated with downstream score at r = 0.68, 0.86, 0.72 (General, Math, Science); quality-rater metrics at about 0.05 to 0.09 on General. About 306 s per candidate; pools of 8 to 14 candidates, so each correlation rests on few points. (Verified)
- Running it needs an embedding server with an 8B model, Python 3.12 and a fine-tuning framework. The repository also ships a data-construction skill. (Verified)
- For the kit: the finding, not the tool. Any data step in the loop is an experiment against a no-added-data baseline; judge and quality scores are diagnostics. (Inferred)

### D9. Counterfactual Gate-Support Decomposition
Source: https://arxiv.org/abs/2610.19343 v1 (14 Oct 2026, CC BY 4.0); no code link.
- Claim: a gate-against-random comparison confounds selection inside each source with a shift of weight between sources; four budget-matched arms crossing gate eligibility with source distribution separate them. (Verified)
- Result: only within-source selection exceeded its calibrated null band: +29.7 holdout items with 30 of 30 replicates positive on one retrieval pair; +5.6, called marginal, on a second; +27.3 with 9 of 9 for a second gate family. Redistribution and interaction stayed unresolved. For a math gate some sources had no eligible items, which makes the ordinary design undefined. (Verified; authors)
- For the kit: keep a filter only if it beats a same-size random subset with the same per-source proportions by more than the noise floor; if the filter empties a source, report that instead of a result. One or two extra runs per filter hypothesis. (Inferred)

### D10. Autodata
Source: https://arxiv.org/abs/2606.25996 v3 (4 Jul 2026), a large industrial lab; no code.
- Method: an agent writes examples; an example is kept when a strong solver averages at least 0.65, a weak solver below 0.5, and the gap is at least 20 points. An outer optimiser edits the agent's prompts and harness as code diffs and keeps an edit only if the validation score strictly beats its parent. (Verified)
- Evidence: a 4B model trained with GRPO scored 0.366 untrained, 0.500 with plain self-instruct data and 0.632 with agentic data on the authors' harder test set (legal domain 0.280, 0.377, 0.441). Outer loop: 62.1% to 79.6% by iteration 124; 233 iterations, 126 accepted; 6-hour session limit. Cost: 6.59 rounds per accepted item; more than 10k papers gave 2.8k accepted and 1.3k after verification; no money figures. (Verified; authors; own test sets)
- Reported failure: agents tried to pass the gate by rewriting the weak solver's prompt so that it performs badly; the limitations list hacking and insufficient safeguards. (Verified)
- For the kit: a data-generating agent edits the gate if it can, so generator, solver and judge settings belong under frozen paths; the strict-improvement keep rule has the same adaptive-reuse weakness as the planned loop; the method itself is costly and unreleased: Hold. (Inferred)

### D11. Diversity of generated data
- Verbalized Sampling: https://github.com/CHATS-lab/verbalized-sampling (Apache-2.0, 824 stars, no releases, PyPI package, needs a provider key) and https://arxiv.org/abs/2510.01171 v4 (15 Jul 2026). The prompt asks for several responses with probabilities. Paper: 1.6 to 2.1 times the diversity of direct prompting in creative writing; the README says 2 to 3 times. No fine-tuning result on the pages read. (Verified as stated; authors)
- https://arxiv.org/abs/2506.19262 v2 (2025, marked as ongoing work): moderate diversity of LLM-generated data helps downstream, high diversity hurts. (Verified, abstract)
- https://arxiv.org/abs/2511.01490 v3 (28 Apr 2026, Findings of ACL 2026): synthetic data from several source models reduces distribution collapse after fine-tuning; no numbers in the abstract. (Verified, abstract)
- https://arxiv.org/abs/2305.17493 v3: training on model-generated content makes the tails of the distribution vanish ("model collapse"). (Verified, abstract; the journal version could not be opened)
- For the kit: a diversity score is a diagnostic to print next to the downstream score, not a target. (Inferred)

### D12. sdg_hub 0.9.4
Source: https://github.com/Red-Hat-AI-Innovation-Team/sdg_hub (Apache-2.0, 170 stars, v0.9.4 released 2026-06-09, Python 3.10+).
- What: synthetic-data toolkit of blocks composed by YAML flows; no measured downstream result on the page. (Verified)
- Packaging at commit 31efcbe: the Claude Code and Codex plugin manifests both point at one skills folder; the Codex install notes use a marketplace command or a symbolic link into the user's agent-skills folder; a small Cursor file holds allow and deny permission lists; `llms.txt`, an agent instruction file and a secret-scanner config sit at the root. (Verified in the repository. That these are current official mechanisms is Inferred from one third-party repository and belongs to the agent-platform facet.)
- For the kit: one skills folder referenced from per-agent manifests is a low-cost port pattern, but the symbolic-link variant fails the native-Windows constraint, so an installer must copy. As a generation module: Assess, optional. (Inferred)

### D13. shuddhi 1.3.0
Source: https://github.com/agentanywhere/shuddhi (Apache-2.0, Python 3.10+ or Docker, CPU only, 52 commits, 2 stars, not on PyPI, 140 offline tests).
- What: corpus pipeline with a provenance gate that refuses data of a declared origin class before the file is opened; exact and MinHash-LSH near deduplication; language id; a character-trigram perplexity proxy; a toxicity lexicon; PII redaction; a contamination screen against the user's evaluation sets (method not documented). It writes a build manifest with a corpus hash, a filter-config hash, a filtered-build hash and per-shard SHA-256, independent of order and checkable offline. A report command drafts the training-content summary required by Article 53(1)(d) of the EU AI Act and states that it does not make the user compliant. (Verified)
- Evidence: maintainer's run on 33,047,370 documents (176.1 GB) on a 2-vCPU machine: 97.71% kept, 0.38% exact duplicates, 0.83% near duplicates, largest near-duplicate cluster 84,275 copies. (Verified as stated; self-reported; no independent use found)
- For the kit: copy the manifest design; the tool is too young to depend on: Assess. (Inferred)

### D14. Label noise
- Chest CT label cleaning, https://arxiv.org/abs/2606.22382 v1: LLM re-reading of reports against stored labels gave 96.4% agreement, kappa 0.884; in sampled disagreements radiologists sided with the LLM in 72 of 97 general cases and 91 of 99 lymphadenopathy cases; a majority vote of several LLMs was best; no downstream training effect reported. (Verified, abstract; authors)
- cleanlab 2.9.0, https://pypi.org/pypi/cleanlab/json and https://github.com/cleanlab/cleanlab: uploaded 2026-01-13 and no later release; licence field Apache 2.0; Python >= 3.10; needs numpy, scikit-learn, tqdm, pandas, termcolor; first PyPI upload 2018-11-22; 11.7k stars. It ranks likely label errors, outliers, near duplicates and non-IID structure from features and out-of-fold predicted probabilities. (Verified. Earlier releases were AGPL as far as I recall, and the project's status after January 2026 was not checked: both Unverified.)
- For the kit: label checks need out-of-fold predictions, which cost extra runs; flags are review candidates, never automatic deletions (a quarter of the general disagreements above went against the LLM). (Inferred)

### D15. Agent skills for data work
- ai-dataset-quality-audit-agent-skill, https://github.com/dungnotnull/ai-dataset-quality-audit-agent-skill (MIT, 1 commit, 4 stars): Codex skill with eight audit dimensions (provenance and documentation, completeness and coverage, label noise, class and feature balance, demographic bias, leakage and contamination, privacy and consent, ethical fitness) tied to Datasheets for Datasets and the NIST AI RMF; ships a web-crawling knowledge updater; no measurement. (Verified)
- AI-Dataset-Generator, https://github.com/Bhanunamikaze/AI-Dataset-Generator (MIT, 84 commits, 22 stars, no releases): one skill copied into several coding agents by a shell and a PowerShell installer; scripts for generate, verify, dedup (threshold 0.92), split-safe export and audit; the README promotes a pipe-to-shell install; a flag allows injection content for security datasets; no measurement. (Verified)
- The data-construction skill in the DataPrep-Bench repository is the only data skill with downstream numbers, and they are mixed (+19.1 in one cell; 13.2 to 7.5 and 57.8 to 55.5 in others). No licence. (Verified)
- For the kit: none is adoptable. Keep the eight dimensions as a checklist idea and the evidence that a data skill can lower results. (Inferred)

### D16. Self-improving loops
- Self-Harness, https://arxiv.org/abs/2606.09498 v3 (20 Aug 2026, CC BY 4.0); https://github.com/qzzqzzb/Self-Harness (1 commit, no licence shown, 141 stars). Loop: mine weaknesses, propose a harness change, validate. A change is kept only if neither the held-in nor the held-out pass rate drops and at least one rises, with two attempts per candidate. Pass rates, initial to final, for three models: Terminal-Bench 2.0 42.2 to 53.9, 18.0 to 36.7, 46.1 to 57.0; SWE-bench Verified 46.0 to 52.5, 19.5 to 41.5, 52.0 to 55.5; AppWorld 48.6 to 58.9, 22.5 to 52.2, 44.4 to 85.0. The held-out set is hidden from the proposer but used in the gate, so the final numbers are not independent of it; cost and rejection rate are not stated; the authors say higher-stakes changes need stronger gates. (Verified; authors)
- Recursive Self-Improvement survey, https://arxiv.org/abs/2607.07663 v2 (6 Sep 2026), 1,250 papers: ranks verification signals from formal verifiers down to a model's own assessment and names self-confirming loops and diversity collapse as failure modes. (Verified, abstract)
- For the kit: same shape as the planned unattended loop; a set used in the keep rule stops being held out. Overlaps with the search-tracking facet. (Inferred)

### D17. Judges and self-review as data filters
- EditJudge-Bench, https://arxiv.org/abs/2611.12524 v1 (9 Nov 2026): audits vision-language judges with synthetic ground truth; a widely used judge template reached 69.0% AUROC; prompt formatting moved results by up to 14.1 points. (Verified, abstract; authors)
- Clinical de-identification toolkit, https://arxiv.org/abs/2611.12709 v1 (9 Nov 2026): a local LLM stacked with rule-based and NER detectors, failing closed; asked to verify its own findings, the LLM discarded about a quarter of true identifiers. (Verified, abstract; authors)
- For the kit: a judge used as a data filter needs a known-answer check first; for privacy-relevant filtering use the union of detectors and no LLM veto. (Inferred)

### D18. Recipes where data did the work
- axion1_0, https://github.com/bytedance/axion1_0 (Apache-2.0, 37 commits, 68 stars; paper arXiv 2611.03233): two SFT stages (10,819 and 7,544 trajectories, about 312M tokens), then asynchronous GRPO, with no mid-training, preference optimisation or distillation stage; questions solvable without retrieval were removed; reference answers were built by program; SFT took about 90 GPU-hours (35B model) or 240 (122B) on 32 GPUs. All results self-reported; the README notes one deviation from the paper's recipe. (Verified)
- Text-to-image field notes, https://www.linum.ai/field-notes/pjit-21k (4 Nov 2026): $21,038 for 8,415 H100-hours at $2.50; a spike-aware EMA; rendered-text images removed from the data; preference-style post-training reported to overfit sharply. First-party blog, one project. (Verified as stated)
- For the kit: one transferable filter rule for the fine-tuning reference: drop items the base model already solves without the capability being trained (then test it with the control arm). (Inferred)

### D19. Shorter reads (abstract or README level; all Verified as stated; all authors' own numbers)
| Item | Version, date | Claim | View |
| --- | --- | --- | --- |
| SynPro https://arxiv.org/abs/2605.17849 | v2, COLM 2026; code https://github.com/cxcscmu/SynPro needs 7 to 8 GPUs | learned rephrasing gives 3.4 to 5.2 times the effective tokens of repetition | Hold |
| UltraX https://arxiv.org/abs/2607.08646 | v1, 9 Jul 2026; no code | function-call edits of pretraining documents; no numbers in the abstract | Hold |
| SAERL https://arxiv.org/abs/2605.27354 | v2, 5 Nov 2026 | +3.1% average accuracy and 42% fewer steps on a 1.5B math model with GRPO | Hold |
| DataEvolver https://arxiv.org/abs/2606.07001 | v3 | about 10 points average gain on seven benchmarks | Hold |
| Quality classifier transfer https://arxiv.org/abs/2610.11585 | v1, 8 Oct 2026 | small MLPs on encoder embeddings carry an English quality classifier to other languages | Hold |
| HOTFIXR https://arxiv.org/abs/2608.15964 | v1 | weakness-targeted synthetic data: +6.2% in-distribution, +7.1% on unseen languages | Assess the idea |
| MiST https://arxiv.org/abs/2609.18496 | v1 | mid-training on synthetic data from a curated seed corpus: +13.1 points (8B), +8.6 (32B) | Evidence only |
| ReMova https://arxiv.org/abs/2609.16427 | v1 | matched ablation: cleaning helped every fine-tuned model, LLM-based ones about twice as much | Evidence |
| NLLB German-English https://arxiv.org/abs/2611.07797 | v1 | 45k pairs filtered to 25k; +3.4 BLEU against the base model, not against unfiltered data | Weak evidence |
| Moving Alphabet https://arxiv.org/abs/2607.18789 | v1 | fine-tuning and guidance cannot fully repair poor pretraining data | Evidence |
| RayOrch https://arxiv.org/abs/2609.18703 | v1; code https://github.com/OpenDCAI/RayOrch | cluster dataflows that keep parent-child lineage | Reject (scale) |
| CuratorKIT https://arxiv.org/abs/2606.21631 | v1 | append-only provenance record per sample; no results | Hold |
| GraphGen https://github.com/InternScience/GraphGen | Apache-2.0, about 1.2k stars; arXiv 2505.20416 | knowledge-graph-guided QA; on one benchmark the baseline was higher | Hold |
| SEDD https://arxiv.org/abs/2501.01046 | v4, 18 May 2026; https://github.com/mcrl/SEDD, 1 star, CUDA 12.4 and MPI | up to 158 times a CPU tool and 7.8 times a GPU tool on 30M documents with four GPUs; 1.2T tokens in about 3 h on 32 GPUs | Reject (scale) |
| hflow https://github.com/Hebbian-Robotics/hflow | Apache-2.0, 308 stars | checks attach evidence and routing tags and never delete data | Principle only |
| SMO https://arxiv.org/abs/2611.12041 | v1, 9 Nov 2026 | 232 skills compiled to 95 units; score 0.6379 to 0.7478; 38.38% fewer runtime tokens | Hold (other facet) |
| MNN-Pocket-0.3B https://arxiv.org/abs/2611.12311 | v1, 9 Nov 2026 | 300M on-device model; no data details in the abstract | None |
| SemHash-LLM https://arxiv.org/abs/2607.01601 | v1, 2 Jul 2026 | semantic hashing with LLM checks on under 1% of pairs; no datasets, numbers or code | Reject |
| datasketch https://github.com/ekzhu/datasketch/releases | v2.0.0, 5 Jul (year not shown; 2026 Inferred) | default MinHash scheme changed; stored sketches and indexes must be rebuilt; a legacy scheme reads old data | Assess |
| Ask HN https://news.ycombinator.com/item?id=49967773 | 5 Oct 2026, 1 point, no comments | wrong-motion labels, blur and out-of-frame hands found only after training | Unverified (user content) |

## Second-phrasing searches

1. MinHash deduplication, limitations and alternatives: led to semantic deduplication (D5), the semantic-duplicate blind spot (D6), the datasketch scheme change and SemHash-LLM.
2. Train/test leakage detection: led to the soft-contamination paper (D6). A secondary source described 13-gram hashing as the usual decontamination filter (Unverified).
3. Limits of synthetic training data: led to the diversity papers and model collapse (D11).
Left unverified: a blog's precision and recall figures for MinHash against an encoder-based filter.

## What the kit could take (Inferred; input for the design phase)

Core, standard library, offline:
- C1. A harness-run data check: per split, record count, exact-duplicate groups after a declared normalisation, a repeat-count histogram, exact overlap counts between every pair of splits and, if the user declares a group key, group overlap. Harness code reads the sealed split; output is counts only; one run per data fingerprint. Standard library reads JSONL, CSV and text; other formats need the project's own environment.
- C2. An order-independent dataset fingerprint (counts, content hash, normalisation string, config hash) in every run record; runs with different fingerprints are not compared.
- C3. Keep rules for data hypotheses: a no-added-data baseline arm; a same-size random control with the same per-source mix; judge and quality scores logged as diagnostics only.
- C4. Data-gate files (generator, solver and judge prompts, thresholds) under frozen paths in unattended mode; generation commands cannot read evaluation paths; generated rows carry an origin tag.
- C5. Report-only checks: counts and review lists; removal is a user decision or a tested hypothesis.
- C6. One sentence in the validity reference and the final report on which overlap level was checked (exact, near, semantic) and with which tool version.

Optional, off by default:
- O1. Near-duplicate text: rensa 0.5.0 pinned, or datasketch 2.0.0; version stamped in the output.
- O2. Semantic overlap between splits: SemHash 0.5.0 with a locally cached model.
- O3. Images: perceptual-hash nomination with pixel verification.
- O4. Label issues: cleanlab 2.9.0 from out-of-fold predictions.
- O5. Synthetic data generation: only under the user's money limit, always with C3 and C4.

## New concepts (not mentioned in README.md or brief.md)

1. Compute-equivalent loss: data damage expressed as the share of compute a clean run needs to match. https://arxiv.org/abs/2606.24998
2. Repeat-count peak: the number of repeats at which damage is largest; it moves with model size. https://arxiv.org/abs/2606.24998
3. Subdocument deduplication: removing repeated spans inside documents instead of whole documents. https://arxiv.org/abs/2608.03089
4. Frequency- and length-aware retention: keep a computed number of copies of a repeated span instead of one. https://arxiv.org/abs/2608.03089
5. MinHash-LSH banding: sketches split into bands so that similar items collide; set by permutations, bands and a Jaccard threshold. https://github.com/beowolx/rensa
6. Sketch algorithm version stamp: record the sketch library version with an index and refuse on mismatch, because a mismatch fails silently. https://github.com/Zyphra/puffer
7. Incremental deduplication with dataset withdrawal: add corpora to an existing index and later remove one source. https://arxiv.org/abs/2608.28622
8. Semantic deduplication with static embeddings: paraphrase-level duplicate search on CPU. https://github.com/MinishLab/semhash
9. Cross-dataset deduplication: deduplicate one set against another, for example train against test. https://github.com/MinishLab/semhash
10. Soft contamination and semantic duplicates: training items that match test items in content but not in wording. https://arxiv.org/abs/2602.12413
11. Shallow generalisation: benchmark gains that do not carry over to related benchmarks. https://arxiv.org/abs/2602.12413
12. Nominate-then-verify duplicate detection: hashes propose pairs and a pixel comparison decides. https://pypi.org/project/vision-data-doctor/
13. Difference hash and DCT perceptual hash over the eight flips and rotations of an image. https://pypi.org/project/vision-data-doctor/
14. Identity-disjoint split with a cross-passage protocol: every sample of one entity or recording pass stays in one split. https://arxiv.org/abs/2609.07399
15. Dataset collections: aggregates of public datasets with hidden overlap between members. https://arxiv.org/abs/2611.10144
16. Metadata profile for aggregation and provenance (MAP): per-item fields naming source datasets. https://arxiv.org/abs/2611.10144
17. Downstream-grounded data benchmark: judge a data method by fine-tuning on its output. https://arxiv.org/abs/2607.20465
18. Distributional Alignment Score: negative MMD between candidate data and a domain proxy set in embedding space. https://arxiv.org/abs/2607.20465
19. Counterfactual Gate-Support Decomposition: four budget-matched arms that separate selection from redistribution. https://arxiv.org/abs/2610.19343
20. Support extinction: a filter leaves a source with no eligible items, so the matched control cannot be built. https://arxiv.org/abs/2610.19343
21. Agentic Self-Instruct: challenger, weak solver, strong solver and judge; keep items with a weak-strong gap. https://arxiv.org/abs/2606.25996
22. Meta-optimisation of a data agent's harness: edits to prompts and code kept only on strict validation improvement. https://arxiv.org/abs/2606.25996
23. Verbalized Sampling: ask for several responses with probabilities to counter mode collapse. https://arxiv.org/abs/2510.01171
24. Typicality bias: annotators prefer familiar text, which pushes post-trained models toward narrow outputs. https://arxiv.org/abs/2510.01171
25. Source diversity of synthetic data: mixing generator models reduces distribution collapse after fine-tuning. https://arxiv.org/abs/2511.01490
26. Model collapse: training on generated content makes the tails of the distribution disappear. https://arxiv.org/abs/2305.17493
27. Data-bound regime: compute grows faster than available organic tokens. https://arxiv.org/abs/2605.17849
28. Data-influence reward: train a rewriting model with rewards from how much its outputs help. https://arxiv.org/abs/2605.17849
29. Programmatic data editing: repair documents through function calls instead of keep-or-drop. https://arxiv.org/abs/2607.08646
30. SAE-feature data engineering: sparse-autoencoder features steer diversity, difficulty and batching. https://arxiv.org/abs/2605.27354
31. Mid-training: a domain stage between pretraining and fine-tuning. https://arxiv.org/abs/2609.18496
32. Weakness-targeted synthetic data: generate for the error categories the model shows. https://arxiv.org/abs/2608.15964
33. Multi-LLM majority vote for label cleaning. https://arxiv.org/abs/2606.22382
34. Confident learning: rank likely label errors from out-of-fold predicted probabilities. https://github.com/cleanlab/cleanlab
35. Build manifest with an order-independent content hash, a filter-config hash and per-shard hashes. https://github.com/agentanywhere/shuddhi
36. Provenance gate: refuse data by declared origin class before the file is opened. https://github.com/agentanywhere/shuddhi
37. Training-content summary: the public summary of training data that Article 53(1)(d) of the EU AI Act requires from general-purpose model providers. https://artificialintelligenceact.eu/article/53/
38. Lineage-controlled dataflow: parent-child links between records kept through preparation. https://arxiv.org/abs/2609.18703
39. Append-only provenance chain per sample. https://arxiv.org/abs/2606.21631
40. Fail-closed detector stacking: any detector's hit redacts and a failed detector blocks release. https://arxiv.org/abs/2611.12709
41. Judge audit with synthetic ground truth: measure a judge on items with planted, known answers. https://arxiv.org/abs/2611.12524
42. Evidence-only data checks: checks attach evidence and routing tags and never delete. https://github.com/Hebbian-Robotics/hflow
43. Shared skills folder referenced from per-agent plugin manifests. https://github.com/Red-Hat-AI-Innovation-Team/sdg_hub
44. llms.txt: a root file that summarises a repository for agents. https://github.com/Red-Hat-AI-Innovation-Team/sdg_hub
45. Skill compilation into state-move-outcome units. https://arxiv.org/abs/2611.12041
46. Held-in and held-out non-regression gate for harness changes. https://arxiv.org/abs/2606.09498
47. Verification hierarchy and self-confirming loops in self-improving systems. https://arxiv.org/abs/2607.07663
48. Spike-aware EMA: weight averaging that reacts to loss spikes. https://www.linum.ai/field-notes/pjit-21k
49. Model-based quality classifier for pretraining data selection. https://arxiv.org/abs/2610.11585
50. Datasheets for Datasets as the documentation frame of a dataset audit. https://github.com/dungnotnull/ai-dataset-quality-audit-agent-skill
51. Capability-targeted pre-screen: drop items the base model solves without the capability being trained. https://github.com/bytedance/axion1_0

## Concerns any design must handle

IDs already used in other scout drafts are reused where the concern is the same.

- DATA-CROSS-SPLIT-DUPLICATES: exact and near duplicates across splits inflate scores
- DATA-SEMANTIC-DUPLICATE-CONTAMINATION: paraphrased copies of evaluation items pass string checks
- DATA-PRETRAIN-CONTAMINATION: evaluation items inside pretraining or fine-tuning corpora
- DATA-GROUP-TIME-SPLIT: one identity, session or recording pass in more than one split
- DATA-AGGREGATION-HIDDEN-OVERLAP: combined public datasets share items
- DATA-TRAIN-REPETITION-WASTE: repeated training items cost compute; damage depends on repeat count
- DATA-OVER-DEDUP: near-duplicate removal inside train can lower results
- DATA-FILTER-REMOVES-MINORITY: repetitive-looking minority or low-resource data gets filtered out
- DATA-FILTER-NO-MATCHED-CONTROL: filter judged without a size- and source-matched random control
- DATA-FILTER-SUPPORT-EXTINCTION: a filter empties a source and the control cannot be built
- DATA-SYNTHETIC-BELOW-BASELINE: generated or agent-built data lowers results below the run without it
- DATA-QUALITY-SCORE-UNCORRELATED: quality-rater scores do not predict downstream results
- DATA-JUDGE-UNVALIDATED: judge used as a filter without a known-answer check; sensitive to prompt format
- DATA-SELF-REVIEW-DROPS-TRUE-FINDINGS: a model reviewing its own flags discards true ones
- DATA-SYNTHETIC-EVAL-CONTAMINATION: generated rows derived from evaluation items
- DATA-SYNTHETIC-RATIO-COLLAPSE: generated data replacing real data degrades the model
- DATA-SYNTHETIC-DIVERSITY-COLLAPSE: single-source generation narrows the distribution; too much diversity also hurts
- DATA-SYNTHETIC-PROVENANCE-LOSS: generated rows lose their origin tag
- AGENT-GAMES-DATA-GATE: the agent edits solver, judge or filter settings to pass its own data gate
- EVAL-ADAPTIVE-OVERFIT: a set used in the keep rule stops being held out
- EVAL-SEED-NOISE: single-run data ablations with sub-point differences
- EVAL-WEAK-BASELINE: data method compared with the base model instead of unfiltered data
- EVAL-SEALED-AUDIT-PARADOX: the overlap check needs test data the agent may not read
- EVAL-SEALED-AUDIT-ORACLE: check output or repeated checks reveal test membership
- DATA-MANIFEST-UNENFORCED: the fingerprint is advised but no harness code records it
- DATA-HASH-EXCLUDES-DATA: the provenance hash skips data directories and large files
- DATA-FINGERPRINT-ORDER-DEPENDENT: equal content hashes differently after re-sharding or shuffling
- DATA-DEDUP-HASH-VERSION-DRIFT: sketches are not comparable across tool versions; mismatch fails silently
- DATA-NORMALISATION-UNRECORDED: duplicate counts depend on normalisation and threshold
- DATA-CHECK-MUTATES-DATA: a check that deletes or rewrites data changes the experiment
- DATA-LABEL-NOISE: label errors in training and evaluation sets
- DATA-LABEL-AUTO-DELETE: flagged items removed without review
- DATA-DEDUP-MEMORY-BOUND: in-memory duplicate indexes outgrow RAM on large corpora
- COST-DATA-AUDIT-COMPUTE: out-of-fold predictions, embedding passes and control arms consume the run budget
- COST-PAID-GENERATION-UNBOUNDED: paid data generation outside the user's limits
- SEC-DATA-PROMPT-INJECTION: instructions inside dataset rows, cards or data-skill files
- SEC-PROMPT-INJECTION: fetched pages and READMEs carry text addressed to agents
- SEC-SKILL-SUPPLY-CHAIN: data skills installed by pipe-to-shell or fed by web crawlers
- SEC-PACKAGE-PROVENANCE-MISSING: young single-release packages without publish attestation
- SEC-PII-IN-TRAINING-DATA: personal data in training text, more exposed on rented machines
- SEC-DATA-EGRESS-TO-PROVIDER: label audits and generation send data to outside services
- DEP-RUNTIME-MODEL-DOWNLOAD: an optional module fetches a model by name at first use
- DEP-LICENSE-MISSING-OR-MIXED: repositories without a licence file
- DEP-LICENSE-CHANGE: a dependency changes licence between releases
- DEP-TOOL-MAINTENANCE-CHURN: data tools go quiet or have one maintainer
- OPS-WINDOWS-SUPPORT-GAP: symbolic-link skill sharing and compiler needs fail on native Windows
- PORT-PLUGIN-FORMAT-DIVERGENCE: separate plugin manifests per agent product
- GOV-TRAINING-CONTENT-SUMMARY: rules may require a record of what a model was trained on

## Redirect attempts

No fetched page contained hidden or targeted instructions aimed at this task, as far as I saw. Text that asked a
reader or an agent to act, none of it followed:
- A search service's rate-limit message urged creating an account and an API key. Not done; other tools used.
- sdg_hub README and plugin install notes: text telling an agent to invoke its setup skill and to run plugin-install and link commands.
- AI-Dataset-Generator README: a pipe-to-shell install command and lines phrased as mandates to the agent.
- verbalized-sampling README: prompt text to paste into a chatbot or system prompt.
- hflow README: requests to star the repository and to contact the vendor for hosted access.
- puffer, Data-Preparation-Bench and sdg_hub: ordinary clone and package-install instructions.
- nature.com answered a paper request with a redirect to a sign-in authorisation endpoint; not followed, the arXiv version was read instead.

## Limits of this note

- Sweep repositories under personal account names were not opened; their lines rest on the sweep record only.
- Two long arXiv HTML pages (Autodata, DataPrep-Bench) were cut at 100,000 characters; appendix details (seeds, hyperparameters) were not read.
- Some arXiv identifiers and the dates shown on their pages disagree by a month or two; I report the date the page shows.
- "Cheap local trial" entries in the candidates file are untested proposals.
- Codex and Cursor packaging facts come from one third-party repository, not from vendor documentation.
