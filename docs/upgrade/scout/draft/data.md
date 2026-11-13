# Scout note - Data: quality, deduplication, versioning, licences, privacy, synthetic data

- Written 11 November 2026 for the kit upgrade. Kit baseline read: commit `5ea9659` (the 23 October 2026 kit).
- Every source below was checked on 11 November 2026 (written "chk" on each line).
- Status key. **Verified**: primary source (paper page, official docs, licence or terms text, release page, GitHub
  API) opened in this session. **Inferred**: my reasoning from verified facts, or a primary source seen only through
  a search-engine summary, or recalled without re-reading today. **Unverified**: secondary or user-generated source
  only, or not reached.
- Method: seven query families (survey, alternatives, limitations and postmortems, benchmarks, awesome lists,
  security and failure modes, release notes). Nothing was installed, cloned or run. One search service hit its rate
  limit part-way; the rest used a second search tool. A fetch tool saved a copy of one terms PDF in its own cache
  folder outside the repository; it was not opened or run. The workflow's shared web-search budget then ran out, so
  the agent skill and the MCP server in Q3 were read from their repository files through the GitHub API only.
- Legal items are context for what an agent should record. They are not legal advice.

## Summary (10 lines)

1. The kit's data guidance is one section of `references/validity.md` plus one line in `references/finetuning.md`. It is sound, but it is advice only: no harness code builds, checks or records the data manifest that validity.md says "every run records".
2. `expctl hash` does not reliably cover data: data ignored by git is never hashed, a project without git skips directories named `data` or `datasets` and every non-source file type, and any file above 50 MB is hashed by size only. Two runs on different data can carry the same provenance hash. A standard-library data manifest and split fingerprint, recorded per run and checked when runs are compared, is the highest-value core addition.
3. Duplicates across splits are common and inflate scores (CIFAR-100: 10% of test images; language-model corpora: over 4% of validation). The guard forbids the agent to read the sealed test set, so the duplicate audit must be run by harness code that prints counts only.
4. Deduplication across splits is a validity requirement. Deduplication inside the training set is a hypothesis: FineWeb found that more aggressive global deduplication gave no gain or was worse, and hash-based tools change their output between versions (datasketch 2.0.0).
5. Dataset files and rows are an attack surface. CVE-2026-57845 (published 23 October 2026, fixed in `datasets` 5.2.0 on 9 November 2026) is code execution through a pickle-backed loader. Rows are untrusted text that the agent reads, and every row the agent reads is sent to the agent's model provider.
6. Licence metadata on hubs is unreliable (licence missing for about 70% of audited datasets; hub label more permissive than the source for 27% on the largest hub). The agent should record what it found and where, never infer permission, and leave gated-terms acceptance to the user.
7. Personal-data and secret scanners are tripwires, not guarantees: the best exact-span F1 was 0.47 on one 2026 benchmark and 0.14 on another, and 11,908 live secrets were found in one web-crawl snapshot.
8. Synthetic data helps mainly when real data is scarce and when it is added to real data. It harms when it replaces real data or is unfiltered. Three large providers forbid training competing models on their outputs. Per-row provenance and generation from the training split only are the necessary controls.
9. Leakage evidence says selection leakage, duplicates and group leakage matter most. Leakage through normalisation statistics was negligible in one large tabular study (a hypothesis for neural networks). The kit should order its checks accordingly.
10. The tool landscape is churning (cleanlab dormant since January 2026, lakeFS now source-available, DVC and Presidio moved organisations, distilabel and synthetic-data-kit stale). Keep hashing, manifests, exact-duplicate checks and group splits in the standard-library core; everything else optional and version-pinned.

## Q1. What the kit says about data today, and what is missing

What exists (all Verified by reading the files at the baseline; chk 11 Nov 2026):

- `.claude/skills/nn-training/references/validity.md` section 1: the Project card must state the unit of independence, the split method, and "permitted data and pretraining sources (licences, contamination concerns)"; preprocessing is fitted on training data only.
- validity.md section 2: unit leakage (group or chronological splits), exact duplicates across splits by hashing normalised records, near-duplicates by perceptual hash or MinHash or embeddings with the threshold reported, temporal, target and preprocessing leakage (including synthetic samples derived from validation or test items), pretraining contamination by n-gram overlap, a 50-item label inspection, and a manifest `experiments/data_manifest.json` with "Every run records the manifest hash."
- validity.md section 4 item 4: shuffled-label control. Sections 5 and 6: sealed test set and frozen evaluator.
- `references/finetuning.md` section 3: chat template, loss masking, truncation counts and one line on overlap between fine-tuning data and evaluation sets.
- `references/resume.md` and `references/hpo.md` refer to a "data manifest hash" and a "split/manifest hash".
- `templates/JOURNAL.md` Project card has one line: "Data (sources, permitted use) and split protocol (unit of separation: random / group / time)".
- `references/stack.md` lists no data-quality, versioning or privacy tool. `docs/research-notes/training_techniques.md` has no data-quality content (it only notes that data sampling is a large source of run-to-run variance).

What is missing or not enforced:

- **No tool builds or records the manifest.** `scripts/expctl.py` has `hash` (source provenance only) and no data command; `scripts/runlog.py` records `EXP_SOURCE_HASH` but no data hash. The sentence "Every run records the manifest hash" is not true of the shipped code. (Verified, local read.)
- **Data is mostly outside provenance.** In a git project `source_files` (`expctl.py` lines 579-609) lists tracked files and untracked files that git does not ignore, so data that is git-ignored, or that lives outside the project, is never hashed. Without git it skips `NONGIT_SKIP_DIRS` (lines 107-111, which include `data` and `datasets`) and keeps only source-like extensions, so `.csv`, `.jsonl`, `.parquet` and `.npy` files are never hashed. In both cases `hash_files` (lines 612-634) hashes a file above `snapshot.max_file_mb` (default 50) by path and size only, and a symbolic link by its target path. A changed large data file of the same size, or any change to ignored data, leaves `source_hash` unchanged. (Verified, local read on 11 Nov 2026.)
- **Sealed-audit paradox.** Section 2 tells the agent to hash-compare splits; section 5 and the guard deny the agent any access to sealed test paths. For the test split the instruction cannot be followed as written. (Inferred from the two sections.)
- **Native Windows.** Copy-mode snapshots link ignored and large paths (data included) into the run's source copy. Without the symlink privilege `_link` (`expctl.py` lines 710-723) falls back to a directory junction or a file hard link. When that also fails (the error text names a volume that is not local NTFS and, for files, a volume other than that of the runs directory) the launch stops and tells the user to retry with `--snapshot none` (lines 1384-1386). `sha256sum` in validity.md section 1 is not a PowerShell command. (Verified, local read; the PowerShell point is Inferred.)
- No guidance on: recording licence, terms, revision and retrieval date; gated datasets; personal data, secrets and memorisation; synthetic data; over-deduplication and tool-version drift; label-error tooling; dataset files as executable content; dataset rows as untrusted text; rows leaving the machine through the agent's context.

## Q2. Data quality and cleaning

### Duplicates across splits (evidence)

- CIFAR: 3.25% of CIFAR-10 and 10% of CIFAR-100 test images have near-duplicates in the training set or the test set itself; a ResNet-110 had 0% and 2.9% error on the duplicated subset against 5.3% and 26.1% overall; on the duplicate-free test sets error rose by 0.41 and 2.73 points on average. https://www.mdpi.com/2313-433X/6/6/41 (J. Imaging, 2 June 2020; chk 11 Nov 2026; Verified, authors measured).
- "Data Leakage in Visual Datasets": identical images below 3% and near-identical up to 7% between splits of every dataset analysed; when a leaked image carries a different label, accuracy on it falls instead of rising. https://arxiv.org/abs/2508.17416 (24 Aug 2025; chk 11 Nov 2026; Verified, authors measured).
- Language-model corpora: train-test overlap affects over 4% of the validation set of standard datasets; over 1% of unprompted output is copied from training data; deduplicated models emit memorised text about ten times less often and reach the same or better accuracy in fewer steps. https://aclanthology.org/2022.acl-long.577/ (ACL, May 2022; chk 11 Nov 2026; Verified).
- A sequence that appears 10 times in the training data is generated about 1000 times more often than one that appears once; deduplication makes extraction attacks much less effective. https://arxiv.org/abs/2202.06539 (ICML 2022; chk 11 Nov 2026; Verified).

### Deduplication inside the training set (a hypothesis, not a default)

- FineWeb: MinHash on word 5-grams, 112 hashes in 14 buckets of 8 (about 75% similarity). Global deduplication over 96 crawl snapshots kept 4T tokens with little gain; per-snapshot deduplication (20T tokens) matched the best earlier dataset; lighter global URL or line deduplication was consistently worse. https://proceedings.neurips.cc/paper_files/paper/2024/file/370df50ccfdf8bde18f8f9c2d9151bda-Paper-Datasets_and_Benchmarks_Track.pdf (NeurIPS 2024; chk 11 Nov 2026; Verified, authors measured).
- Semantic deduplication of a LAION subset removed 50% of the data with minimal loss. https://arxiv.org/abs/2303.09540 (2023; chk 11 Nov 2026; Inferred: abstract seen through a search summary). D4 numbers were not reached (Unverified).
- datasketch 2.0.0 changed the default MinHash scheme to `affine32`; hash values differ from earlier versions and `scheme="legacy"` is needed to match old sketches. https://github.com/ekzhu/datasketch/releases (5 July 2026; chk 11 Nov 2026; Verified). Consequence: a near-duplicate count is reproducible only with the tool name, version, parameters and normalisation recorded. (Inferred.)
- Starting thresholds seen in a handbook chapter: Jaccard 0.7-0.8, cosine 0.9-0.95. https://datascale-ai.github.io/data_engineering_book/en/part2/ch05_cleaning_dedup/ (chk 11 Nov 2026; Unverified: secondary source, treat as a starting point to test).

### Label errors and outliers

- Ten widely used test sets carry at least 3.3% label errors on average (about 6% of ImageNet validation). About half of the items flagged by confident learning were confirmed as errors by people (51%). Model ranking is unchanged on the full corrected sets but changes on the mislabelled subset as its share grows. https://datasets-benchmarks-proceedings.neurips.cc/paper_files/paper/2021/file/f2217062e9a397a1dca429e7d70bc6ca-Paper-round1.pdf (NeurIPS 2021 datasets track; chk 11 Nov 2026; Verified). Consequence: flagged items are review candidates, never an automatic deletion list. (Inferred.)
- A 2025 benchmark of noisy-label detectors reports that in-sample methods, confident learning included, tend to do best. https://arxiv.org/abs/2510.16211 (chk 11 Nov 2026; Inferred: search summary only).
- cleanlab 2.9.0 (13 Jan 2026), Apache-2.0 after relicensing from AGPL-3.0; the company was acquired on 28 Jan 2026; the default branch has had no commit since 13 Jan 2026. https://github.com/cleanlab/cleanlab and https://cleanlab.ai/blog/handshake-acquires-cleanlab/ (chk 11 Nov 2026; Verified through the GitHub API and the company post).
- A standard-library alternative for a first pass: have the run write per-example loss, then rank the highest-loss training items for review. Two training-dynamics methods support the idea: area under the margin tracks each sample's margin through training and separates mislabelled samples (https://arxiv.org/abs/2001.10528, v4 23 Dec 2020), and dataset cartography uses per-example confidence and its variability over epochs from one run (https://arxiv.org/abs/2009.10795, v2 15 Oct 2020). (chk 11 Nov 2026; abstracts Verified; that a plain loss ranking does as well as either is Inferred.)
- Selection quality over quantity: filtering 52k instruction examples to 9k with a model judge beat the full set and cut training from 80 to 14 minutes for a 7B model. https://arxiv.org/abs/2307.08701 (v5 13 Feb 2024; chk 11 Nov 2026; Verified, authors measured with a model judge).

### Filtering pipelines and tools (versions and licences Verified through the GitHub API unless noted; chk 11 Nov 2026)

| Tool | Version, date | Licence | Notes |
|---|---|---|---|
| datasketch | 2.0.0, 5 Jul 2026 | MIT | MinHash and LSH building blocks; pure Python plus NumPy; hash change in 2.0.0 |
| semhash | 0.5.0, 30 Sep 2026 | MIT | Embedding-based deduplication across two sets; no independent evidence found |
| text-dedup | release 2023.09.20; last push 9 Mar 2026 | Apache-2.0 | Stale releases |
| datatrove | 0.10.1, 30 Sep 2026 | Apache-2.0 | The pipeline library behind FineWeb; filters, MinHash, exact dedup |
| data-juicer | 1.6.2, 4 Nov 2026 | Apache-2.0 | Large operator library (includes a personal-data redaction mapper) |
| NeMo Curator | 1.4.0, 9 Oct 2026 | Apache-2.0 | Docs recommend Ubuntu, Python 3.11-3.13, extras `text_cpu` and `text_cuda12` (CUDA 12); Windows and WSL2 are not mentioned |
| DataFlow (OpenDCAI) | 1.0.13, 26 Oct 2026 | Apache-2.0 | Model-driven operators; release note pins pandas 2.3.3 for NumPy 1.26.4 |
| imagededup | 0.3.3.post2, 15 Aug 2025 | Apache-2.0 | Perceptual hashes and CNN embeddings for images |
| fastdup | last push 23 Aug 2026 | non-standard ("Other") | Core reported to be closed (recalled, not re-checked); not suitable as a kit module |
| deepchecks | 0.19.1, 15 Dec 2024 | non-standard ("Other") | Stale |
| pandera | 0.36.0, 10 Nov 2026 | MIT | Dataframe schema checks; not a gap for this kit |
| DuckDB | 2.0.0, 21 Oct 2026 | MIT | One-binary SQL over Parquet; convenient for cross-split hash joins |

- NeMo Curator installation facts: https://docs.nvidia.com/nemo/curator/latest/admin/installation.html (docs "v1.4.0 (26.09)"; chk 11 Nov 2026; Verified). The test machine has PyTorch with CUDA 13; whether the CUDA 12 extras work there is unknown. (Inferred.)
- Evidence that pipelines help comes from their authors (FineWeb ablations for datatrove-style filters). No independent comparison of the pipeline tools was found. (Verified absence only within the searches run.)
- Surveys: ACM "Data Optimization for LLMs: A Survey", doi 10.1145/3859244 (16 Oct 2026); https://jcst.ict.ac.cn/en/article/pdf/preview/10.1007/s11390-026-5948-8 (Jan 2026); https://github.com/alon-albalak/data-selection-survey (list). Awesome lists: https://github.com/Renumics/awesome-open-data-centric-ai (tool-oriented), https://github.com/daochenzha/data-centric-AI (reading list, last updated mid-2024). (chk 11 Nov 2026; surveys Verified earlier in the session; list status Inferred from search summaries.)

## Q3. Data versioning and provenance

### Current options

- Hub revisions. `load_dataset(path, revision=...)` accepts a tag, branch or commit hash, and the library's README asks users to pin the revision. https://github.com/huggingface/datasets/blob/main/docs/source/loading.mdx (datasets 5.2.0, 9 Nov 2026; chk 11 Nov 2026; Verified).
- Hub REST lookup: `GET https://huggingface.co/api/datasets/{repo_id}` or `.../revision/{revision}` returns the commit `sha`, card data, `gated`, `tags` and file list. https://github.com/huggingface/hub-docs/blob/8577fc77/docs/hub/api.md (chk 11 Nov 2026; Verified).
- `hf cache verify REPO_ID --repo-type dataset --revision <sha> --fail-on-missing-files --fail-on-extra-files` checks local files against Hub checksums and exits non-zero on mismatch. https://github.com/huggingface/huggingface_hub/blob/v2.4.0/docs/source/en/package_reference/cli.md (huggingface_hub 2.4.0, 29 Oct 2026; chk 11 Nov 2026; Verified).
- Dataset viewer API, base `https://datasets-server.huggingface.co`: `/is-valid`, `/splits`, `/size`, `/statistics`, `/parquet`, `/croissant`; gated and private datasets need a bearer token. https://huggingface.co/docs/dataset-viewer/quick_start (chk 11 Nov 2026; Verified).
- Croissant metadata format 1.1.1 (5 Oct 2026), Apache-2.0. https://github.com/mlcommons/croissant (chk 11 Nov 2026; Verified).
- DVC 3.67.1 (31 Mar 2026), Apache-2.0, repository now `treeverse/dvc`, last commit 6 Nov 2026; lakeFS acquired DVC on 18 Nov 2025. https://dvc.org/blog/dvc-joins-lakefs-your-questions-answered/ (chk 11 Nov 2026; Verified).
- lakeFS 1.88.0 (1 Oct 2026): the community edition moved to the Business Source License from 1.87.0; it needs a server. https://lakefs.io/blog/lakefs-business-source-license/ (22 Sep 2026; chk 11 Nov 2026; Verified).
- Oxen 0.67.1 (10 Nov 2026), Apache-2.0, Windows binaries; small adoption (about 1,200 stars). https://github.com/Oxen-AI/Oxen (chk 11 Nov 2026; Verified).
- datachain 0.62.4 (9 Nov 2026), Apache-2.0; now positioned as a typed, versioned layer over cloud object stores. https://github.com/datachain-ai/datachain (chk 11 Nov 2026; Verified).
- Why content hashes and not URLs: datasets distributed as URL lists can change after indexing; hashes of the content are the defence. https://arxiv.org/abs/2302.10149 (2023; chk 11 Nov 2026; Inferred: abstract seen through a search summary).

### What a standard-library core can do by itself (Inferred design, to be tested)

- **Manifest.** For each configured data path: relative POSIX path, size, sha256 of the full content. One root hash over the sorted lines. Reuse the chunked loop already in `hash_files`, without the size-only shortcut. Cache digests by (path, size, mtime in ns) and say in the manifest which digests came from the cache. `hashlib.file_digest` exists from Python 3.11 (https://docs.python.org/3/library/hashlib.html; chk 11 Nov 2026; Verified) but the existing loop needs no version floor.
- **Hub or streamed data with no local files.** Record repository id, commit sha, config, split names and row counts. This trusts the hub's revision; the optional verify command above closes the gap.
- **Split fingerprint.** sha256 over the sorted (split, record hash) pairs, plus counts per split and class. Record hash = sha256 of a stated canonical form, for text: Unicode NFKC, casefold, whitespace collapsed, UTF-8. The canonical form gets an identifier in the manifest.
- **Per-run recording and a comparison gate.** `expctl launch` writes the manifest hash into the run record (and exports it for `runlog`); status and comparison output flag runs whose data hashes differ, the way protocol versions are not mixed.
- **Cross-split exact-duplicate audit.** Run by `expctl` so that the agent's command line never names a sealed path. Output: counts per pair of splits. Listing the colliding training rows is a separate, logged step, because a list of training rows that equal test rows discloses test content.
- **Deterministic group split.** Bucket = sha256(salt + group id) mod N. Stable when data grows, needs no package, and the salt goes in the manifest.
- **Limits.** Full hashing costs time on very large or network-mounted data (throughput not measured here). Text files checked out with different line endings on Windows and Linux hash differently. Parquet and Arrow rows cannot be read without a package, so row-level checks for those formats need the repository's own loader to emit record hashes, or an optional module.

### What should be optional

- Anything that needs the network (hub lookups, cache verification), a package (near-duplicate search, Parquet row access, DuckDB) or a server (lakeFS). If a repository already uses DVC, its small pointer files are ordinary git-tracked files and are already inside `source_hash`; the kit only needs to say so and ask for a clean `dvc status`. (Inferred.)

### Agent-facing packaging of hub data access (a skill and an MCP server)

- `huggingface/skills` (Apache-2.0; created 24 Nov 2025; last push 30 Oct 2026; about 11,300 stars) ships a `huggingface-datasets` skill. It wraps the dataset viewer endpoints listed above for read-only exploration. The same file also describes upload flows (one through an unpinned `npx` package) and uploading raw agent session folders to a hub dataset, private by default. The repository's `.mcp.json` adds the hosted MCP server with a login step. https://github.com/huggingface/skills/blob/main/skills/huggingface-datasets/SKILL.md (read at commit 25910b3; chk 11 Nov 2026; Verified).
- `huggingface/hf-mcp-server` 0.4.34 (10 Nov 2026; MIT; created 6 May 2025; about 310 stars), hosted at `https://huggingface.co/mcp`. Its source has tools for repository search, dataset detail, dataset viewer inspection, hub file reading and writing, repository creation, Jobs and a sandbox. The README says repository creation, Jobs and sandbox tools need authentication, and that a self-hosted server can hide tools with `DISABLE_TOOLS`. https://github.com/huggingface/hf-mcp-server (README and `packages/mcp/src` at commit 16ebc95; chk 11 Nov 2026; Verified).
- Consequence (Inferred): both suit a person exploring datasets, and both need an account and the network, so they can only be optional. For the kit they have two costs. They hand the agent actions the kit otherwise keeps away from it (uploading local files, creating repositories, starting paid jobs), and they bring hub text and rows into the agent's context. Facts that go into the manifest (commit sha, licence fields, row counts) are better fetched by deterministic harness code than by agent tool calls. No measurement of either tool's effect on training results was found.

## Q4. Licences and privacy

### Reading a licence programmatically or from the card

- Card and API fields: `license` (may be absent; not limited to SPDX identifiers), `license_name` and `license_link` when the value is `other`, `gated` (false, "auto" or "manual"), `tags`, `source_datasets`, `annotations_creators`. https://huggingface.co/docs/huggingface_hub/en/package_reference/cards and https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/hf_api.py (huggingface_hub 2.4.0; chk 11 Nov 2026; Verified). The same lookup works with `urllib` alone; it needs the network, so it is optional.
- Hub licence labels are often wrong. In an audit of 1,858 datasets the licence was unspecified for 72%, 69% and 70% on three aggregators, and the aggregator's label was more permissive than the original for 29%, 27% and 16%; 85% of licences ask for attribution and 30% have share-alike terms. https://www.nature.com/articles/s42256-024-00878-8 (Nature Machine Intelligence, 2024; chk 11 Nov 2026; Verified; single annotation pass).
- Consequence (Inferred): record the licence identifier, where it was read (card or original source), the URL and the revision; write "unspecified" or "unverified" when that is the case; never treat silence as permission. Accepting the terms of a gated dataset or model is the user's act, not the agent's.

### Common restrictive terms

- Non-commercial, share-alike, no-derivatives and research-only data licences; custom model licences; per-user gated terms; attribution duties. (Inferred: general knowledge plus the audit above.)
- Llama 3.1 Community License (23 July 2024): outputs may be used to train other models, but a distributed model trained on Llama materials or outputs must carry a name beginning with "Llama" and the "Built with Llama" notice; there is a clause for very large user counts. https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE (chk 11 Nov 2026; Verified).
- Provider terms on outputs: see Q5.
- Regulation and case law (context only). EU AI Act Article 53(1)(d): providers of general-purpose models publish a summary of training content using the AI Office template (24 July 2025); a party that modifies a model reports only on its own modification, and Commission guidelines use one third of the original training compute as the indicative line for becoming a provider. Law-firm summaries: https://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/20250724-european-commission-issues-guidelines-for-providers-of-general-purpose-ai-models and https://thelens.slaughterandmay.com/post/102kyy4/just-in-time-eu-ai-office-publishes-template-for-summarising-gpai-training-conte ; official page, not opened: https://digital-strategy.ec.europa.eu/en/library/explanatory-notice-and-template-public-summary-training-content-general-purpose-ai-models (chk 11 Nov 2026; Inferred: secondary sources seen through search summaries.) A United States appeals court affirmed on 29 Sep 2026 that training a non-generative legal search tool on a competitor's editorial summaries was not fair use; two 2025 district rulings on generative models went partly the other way. https://www.jw.com/news/insights-ai-copyright-fair-use-case/ (law-firm summary; chk 11 Nov 2026; Inferred: search summaries only, the opinions were not read.) What this means for the kit: it records provenance and leaves the judgement to the user.

### Personal data and secrets

- Detector accuracy is low on independent tests. Exact-match span F1 on one benchmark: 0.471, 0.391, 0.384, 0.373 and 0.368 for five current open detectors. https://arxiv.org/abs/2605.09973 (2026; chk 11 Nov 2026; Verified). On another, the best of eight systems reached 0.1385 (Presidio; its regular-expression recognisers carried the result). https://arxiv.org/abs/2604.15776 (17 Apr 2026, single author; chk 11 Nov 2026; Verified). A follow-up says that test subset was flawed and reports 0.65 for a fine-tuned model. https://arxiv.org/abs/2605.25816 (chk 11 Nov 2026; Inferred: search summary only).
- A vendor-run test reported leak rates between 11% and 67% for four other tools. https://getshadow.dev/benchmarks/ (page dated 31 Oct 2026; chk 11 Nov 2026; Unverified: measured by the vendor of a competing product.)
- Presidio 2.2.366 (27 Oct 2026), MIT, repository now `data-privacy-stack/presidio`, Python 3.11 to 3.14. GLiNER 0.2.30 (2 Nov 2026), Apache-2.0. https://github.com/data-privacy-stack/presidio and https://github.com/urchade/GLiNER (chk 11 Nov 2026; Verified).
- OpenAI Privacy Filter: open weights under Apache-2.0, eight label categories including secrets, 128,000-token context; the model card says it is "not an anonymization, compliance, or a safety guarantee". https://huggingface.co/openai/privacy-filter (chk 11 Nov 2026; Verified; release date of 22 April 2026 and the vendor's F1 claims are Unverified).
- Secrets: a scan of the December 2024 Common Crawl snapshot (400 TB, 2.67 billion pages) found 11,908 live, verified secrets of 219 types on about 2.76 million pages. https://trufflesecurity.com/blog/research-finds-12-000-live-api-keys-and-passwords-in-deepseek-s-training-data (27 Feb 2025; chk 11 Nov 2026; Verified, vendor measured). Scanners: TruffleHog 3.99.8 (2 Nov 2026, AGPL-3.0), gitleaks 8.30.1 (21 Mar 2026, MIT), detect-secrets 1.5.0 (6 May 2024, Apache-2.0, stale). (GitHub API; chk 11 Nov 2026; Verified.)
- Consequence (Inferred): a scan is a tripwire that reports counts by category and never prints matches. A clean scan is not evidence of absence.

### Memorisation

- Training data can be extracted at scale from open, semi-open and closed models; alignment does not remove memorisation. https://arxiv.org/abs/2311.17035 (28 Nov 2023; chk 11 Nov 2026; Verified).
- Fine-tuned models memorise personal data that appears only in the inputs, not in the targets; differential privacy reduced leakage in some settings but could make training unstable; post-training methods gave steadier trade-offs. https://aclanthology.org/2026.eacl-long.304 (EACL, March 2026; chk 11 Nov 2026; Verified).
- Duplication drives memorisation (Q2). Opacus 1.6.0 (5 May 2026, Apache-2.0, needs torch 2.6 or later) implements DP-SGD. https://github.com/meta-pytorch/opacus (chk 11 Nov 2026; Verified). Canary insertion with an exposure measure tests how readily a model memorises rare training sequences. https://arxiv.org/abs/1802.08232 (v3 16 July 2019; chk 11 Nov 2026; abstract Verified).

### What a careful agent should record before it trains on a dataset (Inferred checklist)

1. Source id or URL, immutable revision or content hash, retrieval date.
2. Licence identifier, licence link, where it was read (card or original source), and "unspecified" when missing.
3. Access terms: gated or not, who accepted the terms and when (the user).
4. Permitted use as the user understands it: commercial, research only, unknown. Attribution and share-alike duties.
5. Personal data: yes, no or unknown; scan tool, version and counts; who approved use.
6. Secrets scan: tool, version, counts.
7. Synthetic share: generator model, provider terms URL and date, prompt hash, seed rows.
8. Deduplication: method, tool version, parameters, counts removed, counts of cross-split collisions.
9. Split: unit of independence, method, salt or seed, split fingerprint.
10. Preprocessing: what was fitted, on which split.
11. Contamination statement for pretrained models: checked how, or cannot be checked.
12. Whether raw rows may be shown to the agent (they then leave the machine).

## Q5. Synthetic data, splitting and preprocessing leakage

### Generation and curation toolkits (GitHub API; chk 11 Nov 2026; Verified)

| Tool | Version, date | Licence | Notes |
|---|---|---|---|
| NeMo Data Designer | 0.10.0, 2 Nov 2026 | Apache-2.0 | `data-designer==0.10.0`, Python 3.11 or later; repository created 16 Oct 2025; about 2,400 stars; active |
| Bespoke Curator | 0.1.31, 25 Oct 2026 | Apache-2.0 | Batch generation with caching; about 1,760 stars; active |
| distilabel | 1.5.3, 28 Jan 2025 | Apache-2.0 | No release for 21 months; last default-branch commit 15 Dec 2025 |
| synthetic-data-kit | no GitHub releases; last commit 25 Oct 2025 | MIT | Stale |
| DataFlow (OpenDCAI) | 1.0.13, 26 Oct 2026 | Apache-2.0 | Also covers synthesis; heavy pins |

- Autodata (24 June 2026): an agent writes examples, a weak and a strong solver and a judge keep those the strong solver gets right and the weak one does not. A 4B model trained on that data scored 0.632 on the harder test set against 0.500 with plain self-instruct data and 0.366 untrained. https://huggingface.co/papers/2606.25996 (chk 11 Nov 2026; Verified paper, authors measured on their own benchmarks; code and licence not stated on the page).

### When synthetic data helps or harms

- Replacing real data with synthetic data each generation leads to collapse; accumulating synthetic data next to the real data keeps test loss bounded; in supervised fine-tuning of a 2B model synthetic data helped only when real data was about 1,024 examples or fewer. https://proceedings.mlr.press/v267/kazdan25a.html (ICML 2025; chk 11 Nov 2026; Verified). Accumulation bound: https://arxiv.org/abs/2404.01413 (Verified).
- Fine-tuning on synthetic rationales hurt (ROC-AUC 0.734 with labels only against 0.604 and 0.592). https://arxiv.org/abs/2606.10279 (2026; Verified, authors measured).
- Synthetic fine-tuning improved in-distribution retrieval and caused forgetting on real and out-of-distribution data. https://aclanthology.org/2026.emnlp-industry.172/ (2026; Verified).
- One single-author preprint reports stability up to about 20% synthetic share and clear degradation from 30%, calibration first. https://arxiv.org/abs/2510.05133 (Verified as a source; weak evidence). Mixing several generators reduces distribution collapse. https://arxiv.org/abs/2511.01490 (Verified).
- Consequence (Inferred): synthetic data enters as a hypothesis with a real-only baseline at equal budget, a stated share, and accumulation rather than replacement.

### Terms-of-service limits on using model outputs as training data (chk 11 Nov 2026)

- OpenAI Terms of Use (effective 1 Jan 2026): outputs may not be used to develop models that compete with the provider, and automated extraction of output is barred. https://openai.com/policies/row-terms-of-use/ (Verified). The business Services Agreement (effective 1 Jan 2026) has the same bar "except for a Permitted Exception". https://openai.com/policies/services-agreement/ (Verified for the clause; the definition of the exception was not read: Unverified).
- Anthropic Commercial Terms (effective 17 June 2025), section D.4: no use of the services to build a competing product or to train competing models unless expressly approved. https://www.anthropic.com/legal/commercial-terms (Verified).
- Gemini API Additional Terms (effective 23 March 2026): the services may not be used to develop competing models. https://aistudio.google.com/docs/terms (Verified through a summarising fetch tool; wording not seen verbatim).
- Open-weight generators carry their own licences (Llama naming rule above). The agent records the generator, the terms URL and the date; it does not decide what "competing" means.

### Keeping synthetic and evaluation data separate (Inferred rules)

- Generate only from training-split rows; never from validation or test rows (validity.md already says this for augmentation).
- Tag every synthetic row: synthetic flag, generator, prompt hash, seed row ids. Keep the tag through every transformation; the manifest records the synthetic share.
- Run the cross-split duplicate audit on synthetic rows too: a generator can reproduce public benchmark items it memorised.
- Keep evaluation sets real. If a synthetic evaluation set is unavoidable, use a different generator from the one that made training data and say so in the Project card.
- Paid generation counts against the user's money and token limits.

### Splitting practice and leakage through preprocessing

- A living survey lists 41 papers from 30 fields in which leakage affected 648 published papers, with an eight-type taxonomy (no test set, preprocessing or feature selection on all data, duplicates, illegitimate features, temporal leakage, dependent train and test samples, sampling bias). https://reproducible.cs.princeton.edu/ (table updated May 2024; chk 11 Nov 2026; Verified) and https://doi.org/10.1016/j.patter.2023.100804 (Patterns, 2023).
- scikit-learn 1.9.1 "Common pitfalls": on random data, selecting features before the split gives 0.76 accuracy; fitting the selector on the training set only gives 0.5; a Pipeline inside cross-validation gives 0.43 +/- 0.05. https://scikit-learn.org/stable/common_pitfalls.html (1.9.1, 11 Sep 2026; chk 11 Nov 2026; Verified).
- "Which Leakage Types Matter?" (2,047 tabular datasets, single author): fitting scalers on all data changed AUC by at most 0.005; selection leakage (peeking, picking seeds) was the largest effect; at 10% duplication the effect grew with model capacity. https://arxiv.org/abs/2604.04199 (v2 29 May 2026; chk 11 Nov 2026; Verified as a source; tabular only, so a hypothesis for neural networks).
- Identity overlap between train and test in face recognition gives an optimistic bias that is larger on harder test sets. https://arxiv.org/abs/2405.09403 (chk 11 Nov 2026; Verified abstract).
- Consequence (Inferred): order the kit's checks by measured effect. First selection leakage (already handled by the sealed test set and the frozen evaluator), then duplicates and group or time leakage (needs the tools above), then feature selection or learned preprocessing on all data, and last normalisation statistics. Group and time splitters in scikit-learn remain the optional route; the hash-bucket split is the core route.

## Changed since 23 October or wrong in the earlier notes

- **New on the day the kit was built:** CVE-2026-57845 (published 23 Oct 2026; CVSS 4.0 8.7): `datasets` up to 5.1.0 executes code when the packaged pandas builder loads a pickle file; fixed by pull request 8879, released in 5.2.0 on 9 Nov 2026. https://nvd.nist.gov/vuln/detail/cve-2026-57845 and https://github.com/huggingface/datasets/releases/tag/5.2.0 (Verified). `expctl env` prints the installed `datasets` version but nothing flags it, and the references say nothing about dataset files as executable content.
- **Wrong in the kit:** validity.md section 2 says every run records the manifest hash; no shipped code builds or records one. resume.md and hpo.md refer to the same missing hash.
- **Cannot be followed as written:** validity.md asks for a cross-split hash comparison that the guard forbids for the sealed test split.
- **Portability nit:** `sha256sum` in validity.md section 1 is absent from PowerShell.
- **Releases after 23 October 2026:** datasets 5.2.0 (9 Nov), pandera 0.36.0 (10 Nov), Oxen 0.67.1 (10 Nov), datachain 0.62.4 (9 Nov), data-juicer 1.6.2 (4 Nov), Data Designer 0.10.0 (2 Nov), GLiNER 0.2.30 (2 Nov), TruffleHog 3.99.8 (2 Nov), huggingface_hub 2.4.0 (29 Oct), Presidio 2.2.366 (27 Oct), DataFlow 1.0.13 (26 Oct), Bespoke Curator 0.1.31 (25 Oct), hf-mcp-server 0.4.34 (10 Nov).
- **Older facts absent from the earlier notes:** cleanlab acquisition, relicence and dormancy (Jan 2026); lakeFS licence change (22 Sep 2026); DVC under lakeFS (18 Nov 2025); datasketch 2.0.0 hash change (5 July 2026); removal of dataset loading scripts in datasets 4.0.0 (9 July 2025); the 2026 detector benchmarks; the 2025 and 2026 synthetic-data results; the 29 Sep 2026 appeals ruling.
- `docs/research-notes/training_techniques.md` has no data-quality content, so nothing there is contradicted. The gap is the finding.

## Concerns any design must handle

DATA-MANIFEST-UNENFORCED: the manifest is advised but nothing builds or records it
DATA-HASH-EXCLUDES-DATA: provenance hash leaves out git-ignored data, non-source file types and the content of large files
DATA-HASH-COST-LARGE-FILES: full hashing of large or remote data needs caching and honest labelling
DATA-HASH-EOL-PLATFORM-DRIFT: the same text data hashes differently across line-ending conventions
DATA-REVISION-DRIFT: a dataset loaded by name changes under the run
DATA-URL-LIST-CONTENT-DRIFT: datasets shipped as links can change after indexing
DATA-CROSS-SPLIT-DUPLICATES: exact and near duplicates across splits inflate scores
EVAL-SEALED-AUDIT-PARADOX: the audit needs test data the agent may not read
EVAL-SEALED-AUDIT-ORACLE: audit outputs or repeated audits can reveal test membership or content
DATA-OVER-DEDUP: aggressive deduplication inside the training set can hurt
DATA-DEDUP-HASH-VERSION-DRIFT: near-duplicate results change with tool version and parameters
DATA-GROUP-TIME-SPLIT: dependent rows split at random
DATA-SELECTION-LEAKAGE: choices made after looking at held-out results
DATA-PREPROCESSING-LEAKAGE: learned preprocessing or feature selection fitted on all data
DATA-LABEL-NOISE: label errors in training and evaluation sets
DATA-LABEL-AUTO-DELETE: flagged items removed without review, half of flags are false
DATA-PRETRAIN-CONTAMINATION: evaluation items inside pretraining or fine-tuning data
DATA-LICENSE-METADATA-UNRELIABLE: hub licence labels missing or too permissive
DATA-GATED-TERMS-ACCEPTANCE: an agent must not accept terms for the user
DATA-TERMS-OUTPUT-RESTRICTION: provider and model licences limit training on outputs
DATA-SYNTHETIC-EVAL-CONTAMINATION: synthetic rows derived from, or reproducing, evaluation items
DATA-SYNTHETIC-RATIO-COLLAPSE: synthetic data replacing real data degrades the model
DATA-SYNTHETIC-PROVENANCE-LOSS: synthetic rows lose their tag after merging
COST-PAID-GENERATION-UNBOUNDED: paid data generation outside the user's limits
PRIV-PII-RECALL-LIMITS: detectors miss much personal data, a clean scan proves little
PRIV-MEMORIZATION: fine-tuned models reproduce training rows
PRIV-ROWS-SENT-TO-AGENT-PROVIDER: rows the agent inspects leave the machine
PRIV-PII-IN-LOGS: samples and scan matches copied into journals and logs
SEC-DATA-SECRETS-IN-CORPUS: live credentials inside training text
SEC-DATA-FILE-CODE-EXEC: pickle-backed or script-backed datasets run code on load
SEC-DATA-PROMPT-INJECTION: instructions inside dataset rows or cards the agent reads
SEC-DATA-POISONING: tampered or substituted training data
SEC-AGENT-UPLOAD-EXFILTRATION: third-party skills or connectors give the agent upload, repository-creation or paid-job actions
PLATFORM-WINDOWS-DATA-LINK-FALLBACK: on native Windows snapshot links to data fall back to junctions and hard links, which fail for network, non-NTFS or cross-volume data
PLATFORM-GPU-TOOL-LINUX-ONLY: GPU data tools documented for Linux and CUDA 12 only
DEP-TOOL-MAINTENANCE-CHURN: data tools go dormant or move organisations
DEP-LICENSE-CHANGE: a dependency changes licence between releases
ADVICE-UNDATED-DATA-TECHNIQUE: thresholds and mixing ratios presented as defaults without date and source

## Open questions

- Should a file of test-record hashes exist outside the sealed area at all? Plain hashes allow membership tests; a keyed hash needs a key the agent cannot read.
- Who may see the list of training rows that collide with test rows, and how is each audit run logged or limited in unattended mode?
- What should the unattended loop do when the data manifest hash changes mid-campaign: stop, or open a new protocol version?
- How large are typical users' datasets? This decides the caching policy for full hashing. No throughput was measured here.
- Is a network-using optional module allowed to call the hub API with the user's token, and where does the token live?
- Near-duplicate thresholds per modality need a small local trial before any number is written into the references.
- Does 5.2.0 close every pickle path in `datasets`, or only the pandas builder?
- Do the GPU extras of NeMo Curator work under WSL2 with a CUDA 13 PyTorch build?
- The definition of the "Permitted Exception" in one provider's business terms was not read.
- How should the kit word "permitted use: unknown" so that the agent neither blocks work nor implies permission?
- Should the kit warn about, or deny by default, third-party skills and connectors that add upload, repository-creation or paid-job tools to the agent?

## Redirect attempts

No fetched page, paper or model card contained text that tried to redirect this scout. Two repository files read at the end are written for agents and are reported here for that reason. Neither was acted on:

- `skills/huggingface-datasets/SKILL.md` in `huggingface/skills` is, by design, a set of instructions to a coding agent: call the dataset viewer endpoints, upload Parquet folders to a hub repository, and upload raw agent session folders to a hub dataset. It was treated as data about the candidate.
- The README of `huggingface/hf-mcp-server` gives commands that add the server to several agent products, and has one sentence addressed to security researchers and bots saying that its management-page password gate is deliberately lightweight. Nothing was installed or connected.

Five ordinary prompts from tools and documentation were also seen and not acted on:

- A search service's rate-limit error told the client to create an account and set an API key. Not done; another search tool was used.
- The dataset-viewer documentation invites readers to sign up for an account and supply a token. Not done.
- A fetch tool, given a PDF it could not read, asked for the text to be pasted or uploaded. Not done.
- A search tool appends a reminder to list sources. Sources are cited throughout this note.
- The same tool, when the shared search budget was used up, suggested asking the user to raise a limit. No workaround was tried; the gap is listed under "Sources not reached".

## Sources not reached

- The vendor announcement page for the privacy filter and one court-news page returned HTTP 403; the model card and other outlets were used instead.
- EU primary texts, the full text of the appeals opinion, the D4 paper, and the second detector benchmark's follow-up were not opened.
- The workflow's shared web-search budget (200 calls) ran out before a search for other agent skills, plugins or MCP servers in this area could be run. Only the two found through the GitHub API were evaluated.
