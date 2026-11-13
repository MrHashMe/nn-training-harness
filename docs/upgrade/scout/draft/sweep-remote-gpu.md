# Scout note: remote-gpu sweep

Facet: GPU cloud training, spot instances and serverless GPUs (orchestration tools, preemption handling, cost
controls, teardown). Unanchored look at the sweep of 2026-11-10 20:01 UTC (106 records, window since 2026-05-14).
Written 2026-11-11. Every web source below was checked on 2026-11-11 unless a line says otherwise.

Status words used on every claim:
- Verified: read on the primary source (vendor docs, release notes, repository, package index, or the paper).
  For a paper it means "the authors report this"; nobody independent reproduced it.
- Inferred: my conclusion from verified facts, or from a feature being absent in the pages I read.
- Unverified: only a vendor claim, user-generated content, a search summary, a title, or my memory.

Decisions (Adopt, Trial, Assess, Hold, Reject) are my assessment, one line per candidate in
`sweep-remote-gpu.candidates.jsonl` (41 lines).

## Summary (10 lines)

1. On-topic yield is small: about 20 of 106 records concern remote GPU work; the rest are agent-evaluation and training papers, several of which bear on goals 1 and 5.
2. Strongest tool: dstack 0.22.7 (MPL-2.0, weekly releases). It has spot policy, retry on interruption, a price-per-hour ceiling, max duration, idle and low-utilisation termination, tags and orphan detection. It needs a server process, which runs on Windows only through WSL2.
3. Neither dstack nor SkyPilot v0.14.2 has a total-spend cap; limits are per hour or per duration, and dstack's max duration is off by default. The kit must own the money ledger.
4. Preemption notice is not portable: 2 minutes on AWS, none by default on GCP (up to 30 s shutdown), 30 s on Azure, undocumented at the marketplace and serverless providers read. All are best effort.
5. Both orchestrators restart a recovered job from scratch unless the training code checkpoints to storage that outlives the machine. Signal handling alone cannot be the preemption contract.
6. A control-plane crash can leave billable resources behind (the vendor's own release notes), and idle retention defaults reach 3 days. Teardown must work without the agent session.
7. Vendor docs, agent skills and MCP servers now address agents directly and assume a person confirms spending. That assumption fails in unattended mode.
8. Preflight has the largest base rate behind it: 63% of 30,920 fine-tuning configurations gave no valid run; an industry report lost about 2,000 USD to one duplicate execution.
9. For the frozen-evaluator loop: research agents select on test results when they can, and reward-hacking rates differ about fifty-fold between agent models, which matters for the Codex and Cursor ports.
10. 41 candidates evaluated, 61 new concepts listed. The shared web-search budget ran out before the last re-search, so marketplace spot notice and several items stay Unverified (section 7).

## 1. Selected sweep items (one line each)

Date is the date in the sweep record. "(opened)" means I read the primary source; "(abstract)" means the
abstract or summary page only; "(title only)" and "(not opened)" mean the sweep record only.

GitHub
- 2026-11-10 | dstackai/dstack | https://github.com/dstackai/dstack | Open control plane for GPU clouds, Kubernetes and own hosts; closest fit for the optional remote module (opened).
- 2026-11-04 | AI-Hypercomputer/xpk | https://github.com/AI-Hypercomputer/xpk | Training-job orchestrator for one cloud's Kubernetes; now deprecated, a warning about tool lifetime (opened).
- 2026-10-28 | hyper-cluster-ops/spot-instance-gpu-training-budget | https://github.com/hyper-cluster-ops/spot-instance-gpu-training-budget | Spot budget estimator that is referral marketing; example of content the scouting step must discount (opened).
- 2026-10-28 | jiayi-wu-3150/databricks-gpu-training-playbook | https://github.com/jiayi-wu-3150/databricks-gpu-training-playbook | Demo of a managed-platform GPU lifecycle; the managed alternative to rented machines (not opened).
- 2026-10-22 | shriyashekatkar25-byte/keep-it-warm | https://github.com/shriyashekatkar25-byte/keep-it-warm | Monte Carlo sizing of a warm GPU pool; names the cold-start versus idle-billing trade-off (not opened).
- 2026-08-17 | snoussimakrem/AI-Software-Engineer-Cloud-Trained-Locally-Running-Coding-Agent | https://github.com/snoussimakrem/AI-Software-Engineer-Cloud-Trained-Locally-Running-Coding-Agent | Local machine orchestrates, free notebook GPUs train; the same split the remote module needs, early stage (opened).
- 2026-07-23 | skyphusion-labs/vivijure-wan-train | https://github.com/skyphusion-labs/vivijure-wan-train | Serverless LoRA training worker; patterns: fail-fast setting validation, image pinned by tag and digest, per-job storage credentials (opened).
- 2026-07-14 | runcomfy-com/runcomfy-mcp | https://github.com/runcomfy-com/runcomfy-mcp | Remote MCP server with 31 tools, some of which spend money; the paid-tool risk for unattended agents (opened).
- 2026-07-08 | hojjad3/Image-Captioning | https://github.com/hojjad3/Image-Captioning | LoRA fine-tuning deployed on serverless GPUs; example only (not opened).
- 2026-06-22 | Amarel-Taylor-Scott/ai-gpu-cloud-directory | https://github.com/Amarel-Taylor-Scott/ai-gpu-cloud-directory | Provider directory with a stdlib script; possible index for the scouting step (not opened).
- 2026-06-18 | vini2309/OpenClaw-RL-Tutorial | https://github.com/vini2309/OpenClaw-RL-Tutorial | RL fine-tuning on rented pods with deployment scripts; example only (not opened).
- 2026-06-16 | mehtadevenn/mehtadevenn | https://github.com/mehtadevenn/mehtadevenn | Profile repository claiming a multi-cluster training orchestrator; no signal beyond the claim (not opened).
- 2026-06-10 | edwardtay/awesome-ai-infrastructure | https://github.com/edwardtay/awesome-ai-infrastructure | Curated list of GPU clouds and orchestration tools; index only (not opened).
- 2026-06-09 | exalsius/exalsius-cli | https://github.com/exalsius/exalsius-cli | CLI for short-lived multi-cloud clusters and GPU price scans; needs a hosted account (opened).
- 2026-06-09 | jyswee/computegpu-cli | https://github.com/jyswee/computegpu-cli | GPU rental CLI with an MCP server; can store the API key in a project-local file (opened).
- 2026-06-08 | skyphusion-labs/vivijure-backend | https://github.com/skyphusion-labs/vivijure-backend | Render and LoRA-training engine on rented pods; sibling of the worker above (not opened).
- 2026-05-25 | TheFloatingString/transformer-speedrun | https://github.com/TheFloatingString/transformer-speedrun | GPT-2 pretraining on serverless GPUs; a language-model example with no reported numbers (opened).
- 2026-05-25 | api-evangelist/modal-com | https://github.com/api-evangelist/modal-com | Third-party profile of a serverless platform's API; I read the platform's own docs instead (not opened).
- 2026-05-23 | arielcohen4/flex_ai_training | https://github.com/arielcohen4/flex_ai_training | Serverless fine-tuning engine (SFT, DPO, LoRA); volume checkpoints, no time or cost caps documented (opened).

arXiv
- 2026-11-05 | Closed-Loop Physics-Based Manipulation Evaluation at a Commodity Price | http://arxiv.org/abs/2611.07441v1 | 200 evaluation rollouts for about 3.50 USD on eight serverless GPU shards; worked example of cheap, sharded, reproducible evaluation (opened).
- 2026-10-29 | LLM Fine-Tuning Workloads: Characterization, Challenges, and Opportunities for Serverless AI | http://arxiv.org/abs/2610.40983v1 | 30,920 fine-tuning experiments; most configurations fail, many before launch; evidence for a preflight gate (opened).
- 2026-09-24 | Event-Driven ML Pipeline Orchestration for Manufacturing: An AWS Industry Experience | http://arxiv.org/abs/2610.06890v1 | Three years and over 40,000 training jobs; concrete failure causes and cost lessons (opened).
- 2026-05-21 | LiveR: Fine-Grained Elasticity via Live Reconfiguration for Model Training | http://arxiv.org/abs/2605.22014v1 | Resizes a running multi-node job without restart; shows restart cost can exceed the spot notice window (opened).

Hugging Face papers
- 2026-10-11 | Scaling Repeated-Data Pretraining | https://huggingface.co/papers/2610.15965 | Small batches win when data repeats; GPU-time trade-offs; language-model recipe evidence (opened).
- 2026-10-01 | Keyword Harnesses Fail Open | https://huggingface.co/papers/2610.02142 | A lenient scorer hid a total failure; evidence for a fail-closed evaluator (opened).
- 2026-09-29 | Trajectory Soup | https://huggingface.co/papers/2609.37169 | Branch and merge checkpoints mid-training; a compute-for-quality trade (opened).
- 2026-09-27 | QwenGyre | https://huggingface.co/papers/2609.33848 | Elastic RL training for very long agent tasks; elasticity idea only (abstract).
- 2026-09-16 | RayOrch | https://huggingface.co/papers/2609.18703 | Data-preparation engine that keeps lineage between records; idea for data provenance (abstract).
- 2026-09-15 | NanoForecast v0.5 | https://huggingface.co/papers/2609.31669 | Pipeline fixes alone cut error 44%; supports auditing the pipeline before tuning (opened).
- 2026-09-13 | Flattening Every Memory Peak in Long-Context Mixture-of-Experts Training | https://huggingface.co/papers/2609.14306 | Scheduling techniques that cut memory peaks (dispatch peak -59.3%); relevant to out-of-memory avoidance (abstract).
- 2026-08-30 | CUDA-Harness | https://huggingface.co/papers/2609.00058 | Agentic code generation checked by separately synthesised tests to resist reward hacking (abstract).
- 2026-08-22 | Training Agents to Evolve with Their Harness | https://huggingface.co/papers/2608.15763 | Fine-tuning on one fixed harness cost 7.7 points of instruction following; warning on agent and harness coupling (abstract).
- 2026-07-28 | Mapping CVEs to MITRE ATT&CK Techniques | https://huggingface.co/papers/2607.25572 | Reported gains vanished once checkpoints were selected on validation instead of test (opened).
- 2026-07-22 | SLAI T-Rex | https://huggingface.co/papers/2607.20145 | Large post-training report with a utilisation figure (34.22% MFU); a metric the kit could log (abstract).
- 2026-07-17 | JoyNexus | https://huggingface.co/papers/2607.16074 | Multi-tenant training service that shares GPUs; scheduling idea only (abstract).
- 2026-07-01 | GPUAlert | https://huggingface.co/papers/2607.01409 | Wrapper that classifies training failures and guarantees a log; four ideas fit the stdlib core (opened).
- 2026-06-18 | Rethinking Shrinkage Bias in LLM FP4 Pretraining (UFP4) | https://huggingface.co/papers/2606.20381 | 4-bit training recipe; a frontier technique to date-stamp, not adopt (abstract).
- 2026-06-10 | Libra | https://huggingface.co/papers/2606.03077 | GPU allocation for agentic RL post-training; scheduling idea only (abstract).
- 2026-05-18 | LongLive-2.0 | https://huggingface.co/papers/2605.18739 | NVFP4-based training and inference stack; low-precision training signal (abstract).

Hacker News
- 2026-06-01 | Launch HN: Expanse | https://news.ycombinator.com/item?id=48356312 | Closed-source predictor of memory and run time before job submission; vendor numbers only (opened).
- 2026-05-14 | Show HN: Velda | https://velda.io | Runs a command on a cloud GPU with the local environment mirrored, no container image; needs its own cluster (repository opened).

OpenAlex
- 2026-11-05 | Agentic Software Engineering: Foundational Pillars and a Research Roadmap | https://doi.org/10.1145/3861334 | Roadmap paper; background for the ports (title only).
- 2026-10-05 | The more you automate, the less you see: Hidden pitfalls of autonomous AI scientists | https://doi.org/10.1073/pnas.2610214123 | Four validity failures of autonomous research systems with measured rates; direct evidence for goal 1 (arXiv version opened).
- 2026-10-03 | Agentic Software Issue Resolution with Large Language Models: A Survey | https://doi.org/10.1145/3849702 | Survey; background (title only).
- 2026-10-01 | Denario Project | https://doi.org/10.1103/kk55-gc95 | Multi-agent scientific discovery system; analog for the research loop (title only).
- 2026-09-09 | AI-coupled HPC Workflow Applications, Middleware and Performance | https://doi.org/10.1145/3844499 | Survey of workflow middleware; background for remote execution (title only).
- 2026-08-13 | Systematization of Knowledge: Security and Safety in the Model Context Protocol Ecosystem | https://doi.org/10.1007/978-3-032-32726-0_29 | Threat survey for the tool protocol the kit uses; publisher page needs sign-in (title only).
- 2026-08-04 | LLM Post-Training: A Deep Dive Into Reasoning Large Language Models | https://doi.org/10.1109/tpami.2026.3720414 | Survey of fine-tuning and RL post-training; reference for the fine-tuning notes (title only).
- 2026-07-30 | Agentic Coding in the Wild | https://doi.org/10.48550/arxiv.2608.00101 | Production traces of a coding agent (13M sessions, 95T tokens); scale evidence on token use (abstract).
- 2026-07-14 | Self-Improvements in Modern Agentic Systems: A Survey | https://doi.org/10.48550/arxiv.2607.13104 | Survey of self-improving agents; background for the unattended loop (abstract).
- 2026-07-10 | SurGE | https://doi.org/10.1145/3805712.3808598 | Benchmark for generated literature surveys; possible yardstick for the scouting step (title only).
- 2026-07-06 | GaP | https://doi.org/10.48550/arxiv.2607.05369 | Multi-agent self-learning harness; analog only (abstract).
- 2026-06-24 | The Red Queen Godel Machine | https://doi.org/10.48550/arxiv.2606.26294 | Agents and evaluators evolve together; the opposite of a frozen evaluator (opened).
- 2026-06-15 | CacheWise | https://doi.org/10.48550/arxiv.2606.16824 | Cache management for serving coding agents; token-cost background (title only).
- 2026-06-05 | SWE-Marathon | https://doi.org/10.48550/arxiv.2606.07682 | Long-horizon agent benchmark with measured reward hacking, loops and token blow-up (opened).
- 2026-06-03 | Agents' Last Exam | https://doi.org/10.48550/arxiv.2606.05405 | Hard agent benchmark, under 1% pass on its hardest tier; a limit on what unattended agents finish (abstract).
- 2026-06-01 | Efficient training of large language models on distributed infrastructures: a survey | https://doi.org/10.1007/s44336-026-00038-z | Survey; reference for the performance notes (title only).
- 2026-06-01 | Parameter-Efficient Fine-Tuning for Pre-Trained Vision Models: A Survey and Benchmark | https://doi.org/10.1007/s11263-026-02864-6 | Reference for the fine-tuning notes (title only).
- 2026-05-25 | Empowering Scientific Workflows with Federated Agents | https://doi.org/10.1109/ipdps65963.2026.00114 | Agents across remote compute sites; analog for remote execution (title only).
- 2026-05-22 | SkillOpt | https://doi.org/10.48550/arxiv.2605.23904 | Optimises an agent skill document against a held-out gate; a method for tuning the kit's own skill per agent (opened).
- 2026-05-21 | DeltaBox | https://doi.org/10.48550/arxiv.2605.22781 | Millisecond sandbox checkpoint and rollback; rollback idea for agent state (opened).
- 2026-05-14 | Orchard | https://doi.org/10.48550/arxiv.2605.15040 | Open-source framework for training agent models; background (abstract).

## 2. Deep reads

Each claim ends with (source label, status). Source labels are defined at the top of each read. All checked
2026-11-11. "Kit could take" and "Cost" lines are my assessment (Inferred).

### D1. dstack 0.22.7 (tool) - Trial, optional

Version 0.22.7, released 2026-11-04. License MPL-2.0.
S1 https://github.com/dstackai/dstack | S2 https://github.com/dstackai/dstack/releases/tag/0.22.7 |
S3 https://github.com/dstackai/dstack/releases/tag/0.22.6 | S4 https://dstack.ai/docs/reference/dstack.yml/task/ |
S5 https://dstack.ai/docs/concepts/tasks/ | S6 https://dstack.ai/docs/concepts/fleets/ |
S7 https://dstack.ai/docs/guides/protips/ | S8 https://raw.githubusercontent.com/dstackai/dstack/master/skills/dstack/SKILL.md

- One YAML format and CLI to run dev environments, tasks and services on GPU clouds, Kubernetes and on-prem hosts. (S1, Verified)
- Repository created 2022-01-04; 0.22.6 on 2026-10-29 and 0.22.7 on 2026-11-04, about weekly releases. (S2, S3, Verified) 2,310 stars in the sweep is a weak signal.
- A dstack server must run. The server supports Linux, macOS and Windows through WSL2; the CLI also runs on native Windows. Starting the server prints an admin token to the terminal. (S1, Verified)
- `max_price` is the maximum instance price per hour in dollars. (S4, Verified)
- `max_duration` defaults to off (no limit); `stop_duration` defaults to 5m. (S4, Verified)
- `spot_policy` defaults to on-demand; `spot` and `auto` are the other values. (S4, S5, Verified)
- `retry` is off by default; it can cover `no-capacity`, `interruption` and `error` events within a time window. (S4, Verified)
- `utilization_policy` ends a run whose GPU utilisation stays under a threshold for a window of at least 5m. (S4, Verified)
- `idle_duration` defaults to 5m for runs and 3d for fleets and applies to VM-based backends only; container-based backends release at once. (S4, S6, Verified)
- `creation_policy` can forbid creating new instances (`reuse`); `tags` are passed to backend resources. (S4, Verified)
- An interrupted run fails unless retry is configured. The page does not describe resuming from a checkpoint. (S5, Verified) So resume is left to the training code. (Inferred)
- No budget or total-spend cap appears in the task reference or the protips guide. (S4, S7, Inferred from absence)
- Release 0.22.6 adds detection of resources left behind when a server bug or crash loses track of them, for five backends. The default mode only reports; deletion needs `DSTACK_SERVER_ORPHAN_CLEANUP_MODE=delete`; volumes and gateways are not covered. 0.22.7 adds Kubernetes. (S3, S2, Verified)
- SSH fleets (own or rented machines) need Linux with systemd, Docker, NVIDIA Container Toolkit, passwordless sudo and TCP forwarding enabled in sshd. (S6, Verified)
- The README advertises use by coding agents and gives an install command for three agent skills. (S1, Verified)
- The main skill (about 480 lines, no tool allow-list) has the agent preview the plan, show offers and cost, and wait for explicit user confirmation before `dstack apply -f <config> -y -d`. (S8, Verified)
- The same skill has the agent run attach in the background, allows edits to the SSH config, tells it to ask for permission outside the sandbox if attach fails, and never mentions `max_price`. (S8, Verified)
- Kit could take: an optional backend adapter in which harness code, not the agent, writes max_duration, max_price, retry, utilization_policy and tags into every task file. (Inferred)
- Cost: a server and its state (WSL2 on Windows), Docker images, cloud credentials held by the server, an admin token in terminal output, weekly release churn, and a vendor skill that is new attack surface. (Inferred)

### D2. gpuhunt 0.1.35 (library) - Assess, optional

S1 https://github.com/dstackai/gpuhunt | S2 https://github.com/dstackai/dstack/releases/tag/0.22.6

- Python library that aggregates GPU offers and prices from 18 providers into offline, versioned catalogs; query by memory, GPU count, price ceiling and spot. MPL-2.0. (S1, Verified)
- 59 stars and 293 commits (weak signal). (S1, Verified)
- 0.1.35 is the version named in the dstack 0.22.6 notes; its own release date was not seen. (S2, Verified for the number; date Unverified)
- Kit could take: a price source for the pre-launch cost bound. Cost: a package, catalog staleness, list price differs from the bill. (Inferred)

### D3. SkyPilot v0.14.2 (tool; found as the alternative to dstack, not in the sweep) - Assess, optional

S1 https://github.com/skypilot-org/skypilot/releases/tag/v0.14.2 |
S2 https://docs.skypilot.ai/en/latest/examples/managed-jobs.html |
S3 https://docs.skypilot.ai/en/latest/reference/auto-stop.html

- v0.14.2 was published 2026-10-28. (S1, Verified) License Apache-2.0 and first release in 2022 are from memory. (Unverified)
- Managed jobs recover from spot preemption automatically, but the job restarts from scratch unless the user's code checkpoints to a bucket or volume. (S2, Verified)
- `max_restarts_on_errors` bounds restarts after user-code failures; the job's cloud resources are cleaned up when it ends. (S2, Verified)
- A jobs controller is required. A dedicated controller machine costs about 0.25 USD per hour; recent versions run it inside the API server by default (consolidation mode). (S2, Verified) The 10-minute controller autostop figure came from older docs. (Unverified for v0.14.2)
- No cost limit or budget feature on the pages read. (S2, S3, Inferred from absence)
- Autostop defaults to 5 idle minutes; `sky autostop <cluster> -i <minutes>`; `--down` deletes instead of stopping. (S3, Verified)
- The autostop check runs on the remote cluster, so the local machine does not need to stay on. `wait_for` selects what counts as activity; hooks can run before stop. (S3, Verified)
- Kit could take: the remote-side autostop design; a second backend adapter. Cost: a package with many cloud SDKs, an API server, cloud credentials on the launching machine. (Inferred)

### D4. GPUAlert 0.1.6 and its evaluation corpus - Reject the package, Adopt four ideas (core), Trial the corpus

S1 https://arxiv.org/abs/2607.01409 (v1, 2026-07-01, preprint, not peer reviewed; HF page https://huggingface.co/papers/2607.01409) |
S2 https://github.com/Parv-01/gpualert | S3 https://pypi.org/project/gpualert/ | S4 https://github.com/Parv-01/gpualert-eval

- Command-line wrapper that runs a training command with no code changes, classifies the failure, and emails a report. MIT. (S1, S2, Verified)
- Package: 0.1.0 on 2026-05-26, 0.1.6 on 2026-10-27; Python 3.10 or newer; Linux and macOS only; depends on typer, rich, pydantic, psutil, cryptography and keyring; needs an SMTP account. (S2, S3, Verified)
- Classifier: 15 regular-expression rules, one per class, first match wins, specific before generic, bare traceback last. (S1, Verified)
- Result: macro-F1 0.997 on 12 hardware-reproduced classes, against 0.830 for the same patterns without ordering and 0.133 for exit-code inspection. (S1, Verified, author-measured)
- Corpus: 474 logs in 15 classes; 360 from one V100 GPU; 3 classes (CUDA out of memory, NCCL error, kernel OOM-killer) are synthetic; 24 logs come from public issue trackers. (S1, Verified)
- On the 24 real-world logs: 95.8% accuracy against 70.8% for unordered matching; the 95% interval is 0.79 to 1.00. (S1, Verified, author-measured)
- Log created before launch: a log existed in 20 of 20 exec-failure trials, against 0 of 20 with shell redirection. (S1, Verified, author-measured)
- Notifier isolation: with the mail relay unreachable the wrapper returned the child's exit code in 15 of 15 cases. (S1, Verified, author-measured)
- Files over the 25 MB report budget are listed as skipped, never dropped silently. (S1, Verified)
- Overhead: +3.78 ms on a no-op and +2.61 ms on a short script, 30 trials each. (S1, Verified, author-measured)
- Limits stated by the author: one GPU model, PyTorch only, no multi-node failures; unknown errors fall to the generic rule. The paper gives no mapping for exit codes or signals and does not state supported operating systems. (S1, Verified)
- Corpus repository: `corpus/labels.jsonl`, `inject/`, `baselines/`, `eval/`; MIT; 12 commits, 0 stars. (S4, Verified)
- Kit could take: the four properties as stdlib code in expctl and runlog; the corpus as a development-time test fixture. (Inferred)
- Cost of the package itself: six dependencies, no native Windows, an SMTP credential, overlap with expctl. (Inferred)

### D5. LLM fine-tuning workload study and LLMFineTuningBench - Adopt preflight (core); Assess the dataset

S1 https://arxiv.org/abs/2610.40983 (v1, 2026-10-29, workshop paper at Middleware 2026) |
S2 https://huggingface.co/datasets/ibm-research/LLMFineTuningBench

- 30,920 experiments over 33 models (0.35B to 405B parameters), 4 GPU types and 1 to 32 GPUs. (S1, Verified)
- 63% (19,539) gave no valid run: 9,144 were rejected before launch and 10,395 failed at run time. (S1, Verified, author-measured)
- Failure share by batch size: 86% at 1, 42% at 8, 95% at 1,024. (S1, Verified) The abstract's figure for batch 16 to 64 differs from the body. (Verified inconsistency)
- Long sequences raise run-time failures from 21% to 46%. (S1, Verified)
- Throughput grows roughly logarithmically with batch size: 2,847, 6,616 and 9,627 tokens per second at batch 1, 8 and 128 on one A100. (S1, Verified)
- LoRA was 9% faster than full fine-tuning; scaling efficiency inside one node was 0.94 to 1.00. (S1, Verified)
- The authors recommend a memory check, pre-launch feasibility checks and admission control. (S1, Verified)
- Caveat: failures are frequent partly because the sweep was built to probe limits; failure causes are inferred by the authors, not all diagnosed. (S1, Verified)
- Dataset: Apache-2.0, about 30.9k rows, with validity flag, peak GPU memory and tokens-per-second columns. (S2, Verified)
- Kit could take: a preflight gate before every launch; dated rules of thumb for the fine-tuning reference. Cost: a minute per configuration; a short run misses late failures. (Inferred)

### D6. Event-driven ML pipeline orchestration, industry report - Adopt three practices (core)

S1 https://arxiv.org/abs/2610.06890 (v1, 2026-09-24)

- Over 40,000 training jobs since 2023 on container GPU instances that scale between zero and two machines, with one dispatcher function limited to a concurrency of one, queues and dead-letter queues. (S1, Verified)
- About 2% of messages reach a dead-letter queue. Causes: data quality 65%, GPU out of memory 18%, no capacity 12%, timeout 5%. (S1, Verified, authors' account)
- A queue visibility timeout shorter than the job caused duplicate execution that wasted about 2,000 USD. (S1, Verified, authors' account)
- A race once started 4 GPU tasks on a cluster limited to 2 instances. (S1, Verified)
- Lessons: timeout about 1.5 times the longest job; a single writer admits jobs; orchestration limits and infrastructure limits come from one shared variable; separate cloud accounts limit blast radius. (S1, Verified)
- Spot plus a checkpoint to object storage on the two-minute warning; resume overhead under 15 minutes. (S1, Verified)
- Cost per facility-month fell from about 3,200 to 910 to 760 USD. (S1, Verified, self-reported, one organisation)
- Kit could take: launch lock, idempotent launch key, one limits file read by loop and launcher. Cost: stale-lock handling. (Inferred)

### D7. LiveR - Reject (not applicable)

S1 https://arxiv.org/abs/2605.22014 (v1, 2026-05-21; page partly read)

- Changes the GPU count of a running multi-node job without restart; 14 to 23 times faster than checkpoint and restart, 2 to 6 s downtime, up to 99% goodput. (S1, Verified, author-measured; baselines partly modelled)
- Restart baseline: 127.1 s on 32 GPUs, of which 54.6 s is checkpoint load and 70.1 s is initialisation and warm-up; about 150 s for a 30B model. (S1, Verified)
- Needs a fast cluster interconnect; no code released. (S1, Verified)
- For the kit: evidence that restart cost alone can exceed a two-minute notice; nothing to adopt for single-node work. (Inferred)

### D8. Hidden pitfalls of autonomous AI scientists - Adopt three practices (core)

S1 https://arxiv.org/abs/2509.08713 (v2; page partly read) | S2 https://doi.org/10.1073/pnas.2610214123 (2026-10-05; returned 403)

- That S1 and S2 are the same work rests on the matching title only. (Inferred)
- Four pitfalls: inappropriate benchmark selection, data leakage, metric misuse, post-hoc selection bias. (S1, Verified)
- One system picked the first four listed benchmarks about 80% of the time; another chose easy benchmarks 47.1% of the time and hard ones 9.0%. (S1, Verified, author-measured)
- Undisclosed dataset subsampling or synthesis occurred in some runs. (S1, Verified)
- Inverted-result test: the top candidate was chosen 78.5% of the time with real test results and 43.5% with inverted ones in one system; 82.0% and 31.5% in another. (S1, Verified, author-measured)
- An LLM auditor reached 55% accuracy from the paper alone and 82% with logs and code. (S1, Verified, author-measured)
- The authors recommend submitting full trace logs and code. (S1, Verified)
- Kit could take: a ledger of every candidate, a selection-invariance selftest, retention of traces and code per candidate. Cost: disk, and a way to feed fake test scores without touching the sealed set. (Inferred)

### D9. SWE-Marathon - Adopt protections (core)

S1 https://arxiv.org/abs/2606.07682 (v1, 2026-06-05; page truncated, appendix not read)

- 20 tasks, 1,300 rollouts. Reward-hacking attempts in 13.8% of rollouts, shipped exploits in 10.2%, none succeeded against hidden verifiers. (S1, Verified, author-measured)
- Exploit rate by agent model: 26.0%, 22.0% and 0.5% for the three models reported. (S1, Verified)
- Failures (n=526): implementation 41.6%, timeout 31.4%, reward hacking 15.4%, premature termination 7.6%, poor self-verification 4.0%. (S1, Verified)
- Up to 877 identical consecutive tool calls in one trial. (S1, Verified)
- With context compaction 0 of 71 trials passed, against 8.9% without, on one scaffold. (S1, Verified; one scaffold only)
- Tokens per trial: median 7.6 million, mean 27.2 million, maximum 877.4 million; up to 12 times variation by scaffold. (S1, Verified)
- Protections used: hidden verifiers, tripwires, guard tests, restricted network egress. (S1, Verified)
- Kit could take: canaries in sealed paths, a repeated-call counter, token caps in the ledger, and per-agent testing of the guard. (Inferred)

### D10. Keyword Harnesses Fail Open - Adopt negative controls (core)

S1 https://huggingface.co/papers/2610.02142 (October 2026; page partly read)

- A lenient keyword scorer gave 0.660 and 0.650 to two models; a strict structural check gave 6 of 6 and 0. (S1, Verified, author-measured, single seed)
- The paper proposes a four-level diagnostic ladder; the repair cost about 3.3 GPU-hours. (S1, Verified)

### D11. CVE-to-ATT&CK classifier - Adopt a validation-only selection check (core)

S1 https://huggingface.co/papers/2607.25572 (arXiv 2607.25572 v1, 2026-07-28)

- Apparent gains were an artifact of selecting checkpoints on small test splits, with recall-at-5 differences up to 0.05. (S1, Verified, authors' own correction)
- With selection on a validation split the result was 0.673 plus or minus 0.019. (S1, Verified)

### D12. Scaling Repeated-Data Pretraining - Assess as a dated reference note

S1 https://huggingface.co/papers/2610.15965 (October 2026; page partly read; no code yet)

- Models of 153M, 474M and 1.5B parameters trained for many passes over limited data. (S1, Verified)
- Validation loss is U-shaped in batch size with the best value near 64 sequences; the 1.5B model went from 3.124 to 2.977 against the best batch-512 run. (S1, Verified, author-measured)
- Repacking sequences each epoch beats reshuffling; weight tying plus embedding weight decay was best (2.971 to 2.946). (S1, Verified)
- At long deadlines a smaller batch on fewer GPUs can beat a larger batch on more GPUs. (S1, Verified)
- Single preprint, not replicated. (Inferred)

### D13. Closed-loop evaluation at commodity price - Assess sharded evaluation (optional)

S1 https://arxiv.org/abs/2611.07441 (v1, 2026-11-05, workshop paper)

- One replication of 200 rollouts ran as eight parallel shards on L4 GPUs of a serverless platform: 4.36 GPU-hours at 0.80 USD per hour, 3.49 USD, 37.7 minutes wall clock. (S1, Verified, author-measured)
- The whole study cost about 34 USD. The 3.50 USD in the title is per replication. (S1, Verified)
- Per-rollout seeds are derived from the scenario index, so the union of shards reproduces the unsharded run. (S1, Verified)
- Completions under one second are excluded: five scenes succeed before the policy acts. Every claimed success is inspected visually. (S1, Verified)
- 95% Wilson intervals over 195 scenes; most configurations have one checkpoint; no significance tests. (S1, Verified)
- The abstract and a table disagree on the number of checkpoints. (S1, Verified inconsistency)
- The authors disclose that an LLM coding assistant drafted code and manuscript. (S1, Verified)
- No retry behaviour, image digest or commit hash is described. (S1, Verified absence)

### D14. SkillOpt - Assess (optional, development time)

S1 https://arxiv.org/abs/2605.23904 (v2; page partly read) | S2 https://aka.ms/SkillOpt (not opened)

- Edits one skill document and accepts an edit only when the selection-split score is strictly higher; ties are rejected; the test split is for reporting only. (S1, Verified)
- Reported average gains: +24.8 points with one terminal agent and +19.1 with another. (S1, Verified, author-measured)
- Resulting skills are 379 to 1,995 tokens; training used 20.8 to 213.8 million tokens. (S1, Verified)
- No seeds or confidence intervals are reported. (S1, Verified absence) Code license not seen. (Unverified)
- 232 citations in the sweep record. (weak signal, Unverified)

### D15. Short reads: Trajectory Soup, NanoForecast v0.5, Red Queen Godel Machine, DeltaBox

- Trajectory Soup: branching mid-training and merging selected checkpoints scored 68.96 against 68.55 for merging along one trajectory; selection by validation loss; storage and validation cost not counted; no code. (https://huggingface.co/papers/2609.37169, 2026-09-29, Verified, author-measured) Hold.
- NanoForecast v0.5: three pipeline fixes cut MASE from 3.030 to 1.704 (-43.8%); single seed, fixes not isolated; repository Apache-2.0. (https://huggingface.co/papers/2609.31669, Verified, self-reported) Hold.
- Red Queen Godel Machine: a co-evolved evaluator gave 82.1% against 75.0% for a fixed-evaluator baseline on held-out tasks; marked preliminary; no code. (https://arxiv.org/abs/2606.26294, v3, 2026-10-08, Verified, author-measured) Hold; it conflicts with a frozen evaluator.
- DeltaBox: sandbox checkpoint in 14 ms and rollback in 5 ms for files and process state, no GPU state; no code. (https://arxiv.org/abs/2605.22781, v2, 2026-06-08, Verified, author-measured) Reject.

### D16. Velda v1.1.4 - Hold

S1 https://github.com/velda-io/velda | S2 https://news.ycombinator.com/item?id=48140339

- `vrun` and `vbatch` run a command on a cloud instance that mirrors the development environment through a streaming filesystem, with no container image. Apache-2.0. (S1, Verified)
- v1.1.4 was released 2026-04-06; 82 stars, 314 commits. (S1, Verified; weak signal)
- A Velda cluster must first be deployed on a cloud account. (S1, Verified)
- The launch thread has 2 points. (S2, Verified; no adoption signal)

### D17. Small or rejected items

- Expanse: closed-source prediction of memory and run time before submission to cluster schedulers; the 59% wasted-compute figure across 122,000 jobs is the vendor's. (https://news.ycombinator.com/item?id=48356312, 2026-06-01, Unverified: vendor and forum content only) Reject.
- exalsius-cli: Apache-2.0, Python 3.12 or newer, 2 stars, no releases; needs a vendor account and hosted API. (https://github.com/exalsius/exalsius-cli, Verified) Reject.
- computegpu-cli: proprietary, one commit; the API key is stored in a file in the home folder or in the project folder; no spending limits described. (https://github.com/jyswee/computegpu-cli, Verified) Its 5-minute spot warning is a vendor claim. (Unverified) Reject.
- spot-instance-gpu-training-budget: 2 commits, no license; shortened referral links to one marketplace and an unsourced price table; content is a flat 5% overhead sum and generic checkpoint advice. (https://github.com/hyper-cluster-ops/spot-instance-gpu-training-budget, Verified) Reject.
- xpk: Apache-2.0; its maintainers declare maintenance mode and planned archiving. (https://github.com/AI-Hypercomputer/xpk, Verified) Reject.
- runcomfy-mcp: MIT, 12 commits; 31 tools including job submission and deployment; no spend limit or confirmation step described. (https://github.com/runcomfy-com/runcomfy-mcp, Verified) Reject.
- vivijure-wan-train: AGPL-3.0; validates job settings before GPU work, pins its image by tag and digest, uses per-job storage credentials. (https://github.com/skyphusion-labs/vivijure-wan-train, Verified) Assess the patterns only.
- flex_ai_training: volume checkpoints; no timeout or caps documented; a tracking-service key may sit in the job description. (https://github.com/arielcohen4/flex_ai_training, Verified) Reject.
- transformer-speedrun: scripts only, no results. (https://github.com/TheFloatingString/transformer-speedrun, Verified) Reject.
- Local control centre with free notebook GPUs: early phase, no measurements. (https://github.com/snoussimakrem/AI-Software-Engineer-Cloud-Trained-Locally-Running-Coding-Agent, Verified) Reject.

## 3. Second search with different phrasing

Three term clusters were searched again as limitations and alternatives. The shared search budget ran out during
the third; the remaining facts come from direct reads of official pages.

R1. Orchestrator limits and alternatives (terms: orchestration, cost cap, budget)
- The alternative to dstack is SkyPilot (D3). Neither documents a total-spend cap. (Inferred from absence, D1 and D3 sources)
- AWS budget data is refreshed at least once a day, and budget actions can stop instances. (https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-best-practices.html, search summary only, Unverified)

R2. Serverless GPU limits (terms: serverless gpus, container images)
- Modal: function timeout defaults to 300 s and has a 24 h maximum. (https://modal.com/docs/guide/timeouts, Verified)
- Modal: GPU functions are always preemptible; the non-preemptible option does not apply to GPU functions; the grace period on preemption is not given as a number. (https://modal.com/docs/guide/preemption, Verified)
- Modal: long training is done with checkpoints on a volume plus retries (maximum 10), which gives up to 10 days at a 24 h timeout; detached runs survive client disconnect; blocking remote calls expire after 24 h. (https://modal.com/docs/examples/long-training, Verified)
- Vast.ai: prepaid balance; at zero or below, instances stop; storage is billed while stopped; without a saved card, data is deleted after a grace period. (https://docs.vast.ai/guides/reference/billing.md, Verified)
- Vast.ai: interruptible instances are won by bidding, pause when outbid and resume later; no notice period is documented. (https://docs.vast.ai/documentation/instances/choosing/instance-types, Verified; absence Inferred)
- RunPod: credits are non-refundable; at zero balance pods stop, and pods without a network volume are terminated with data loss; default spend limit is 80 USD per hour. (https://docs.runpod.io/get-started/billing-information, Verified)
- RunPod: a stopped pod's volume disk is billed at 0.20 USD per GB per month. (https://docs.runpod.io/pods/pricing, Verified)
- RunPod spot pod interruption notice: not found on the pricing or FAQ pages. (Unverified)

R3. Preemption notice and checkpoint timing (terms: spot instance, checkpoint)
- AWS: two-minute interruption notice through instance metadata and an event bus; best effort; poll about every 5 s; with hibernation there is no usable window. (https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html, Verified)
- GCP: preemption is signalled through a metadata value; no advance notice by default, an optional 120 s notice, and a shutdown period of up to 30 s, best effort. (https://docs.cloud.google.com/compute/docs/instances/spot, Verified)
- Azure: up to 30 s notice through Scheduled Events, best effort; the deallocate eviction policy keeps disks, which keep billing; a maximum price can be set. Page updated 2026-06-24. (https://learn.microsoft.com/en-us/azure/virtual-machines/spot-vms, Verified)
- Young/Daly rule: interval near the square root of 2 times checkpoint cost times mean time between failures. (search summary only, for example arXiv 1310.8456, Unverified)
- A large reliability study of GPU clusters (arXiv 2410.21680). (search summary only, Unverified)

## 4. New concepts (not mentioned in README.md or brief.md)

1. Per-hour price ceiling versus total-spend cap - a price setting bounds the hourly rate, nothing bounds the bill. https://dstack.ai/docs/reference/dstack.yml/task/
2. Orphaned-resource detection with report and delete modes - a control plane scanning the account for resources it lost track of. https://github.com/dstackai/dstack/releases/tag/0.22.6
3. Remote-side autostop and autodown - idle shutdown logic that runs on the rented machine, independent of the client. https://docs.skypilot.ai/en/latest/reference/auto-stop.html
4. Utilisation-based termination - end a run whose GPU utilisation stays under a threshold for a window. https://dstack.ai/docs/reference/dstack.yml/task/
5. Idle retention window - how long a machine is kept and billed after a run ends (minutes for runs, days for fleets). https://dstack.ai/docs/concepts/fleets/
6. Retry-on-event policy - automatic resubmission on no capacity, interruption or error within a time window. https://dstack.ai/docs/reference/dstack.yml/task/
7. Spot policy with fallback - spot only, on-demand only, or automatic choice. https://dstack.ai/docs/concepts/tasks/
8. Creation policy - forbid a run from provisioning new machines (reuse only). https://dstack.ai/docs/reference/dstack.yml/task/
9. Offline versioned GPU price catalog - provider offers and prices as queryable local data. https://github.com/dstackai/gpuhunt
10. SSH fleet - registering an existing machine as a backend over SSH. https://dstack.ai/docs/concepts/fleets/
11. Managed-job controller and consolidation mode - the always-on component that watches and relaunches jobs, itself a cost and a failure point. https://docs.skypilot.ai/en/latest/examples/managed-jobs.html
12. Restart bound on user-code errors - a cap on automatic restarts after a crash. https://docs.skypilot.ai/en/latest/examples/managed-jobs.html
13. Instance-metadata preemption signal - a local HTTP endpoint on the rented machine that announces termination. https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html
14. Best-effort notice window - 120 s, 30 s or none depending on provider, never guaranteed. https://docs.cloud.google.com/compute/docs/instances/spot
15. Eviction policy, deallocate versus delete - whether a preempted machine's disks stay and keep billing. https://learn.microsoft.com/en-us/azure/virtual-machines/spot-vms
16. Interruptible bid instance - a machine that pauses when outbid and resumes later. https://docs.vast.ai/documentation/instances/choosing/instance-types
17. Prepaid balance as a hard spend ceiling, with zero-balance behaviour (stop, then deletion). https://docs.vast.ai/guides/reference/billing.md
18. Provider-side hourly spend limit - an account-level rate limit on spending. https://docs.runpod.io/get-started/billing-information
19. Storage billing after stop - disks and volumes bill while the machine is off. https://docs.runpod.io/pods/pricing
20. Serverless timeout ceiling and retry chaining - long training as a chain of 24 h functions that resume from a volume. https://modal.com/docs/examples/long-training
21. Always-preemptible serverless GPU functions - no non-preemptible option for GPU work. https://modal.com/docs/guide/preemption
22. Detached remote run - a remote run that continues after the client disconnects. https://modal.com/docs/examples/long-training
23. Process-boundary monitor - observing a training job from outside the process with no code changes. https://arxiv.org/abs/2607.01409
24. Pre-launch log guarantee - the log exists before the child starts, so an exec failure still leaves evidence. https://arxiv.org/abs/2607.01409
25. Notifier isolation - failure of the alert channel must not change the job's exit status. https://arxiv.org/abs/2607.01409
26. Non-silent artifact budget - anything left out of a report for size is listed by name. https://arxiv.org/abs/2607.01409
27. Ordered-rule failure classifier - first-match-wins patterns from specific to generic, each with a fix hint. https://arxiv.org/abs/2607.01409
28. Labelled failure-log corpus with fault injection - a test set for failure classifiers. https://github.com/Parv-01/gpualert-eval
29. Pre-launch feasibility check and admission control for training configurations. https://arxiv.org/abs/2610.40983
30. Workload-characterisation dataset - per-run validity, peak memory and throughput records. https://huggingface.co/datasets/ibm-research/LLMFineTuningBench
31. Single-writer dispatcher - one admitting process, so two launches cannot race. https://arxiv.org/abs/2610.06890
32. Dead-letter queue and visibility-timeout sizing - a timeout shorter than the job causes duplicate execution. https://arxiv.org/abs/2610.06890
33. Scale-to-zero capacity group - GPU machines exist only while jobs are queued. https://arxiv.org/abs/2610.06890
34. Blast-radius separation by cloud account. https://arxiv.org/abs/2610.06890
35. One shared variable for orchestration and infrastructure limits. https://arxiv.org/abs/2610.06890
36. Live reconfiguration - changing a running job's GPU count without restart. https://arxiv.org/abs/2605.22014
37. Goodput - the share of paid compute that becomes training progress under interruptions. https://arxiv.org/abs/2605.22014
38. Young/Daly checkpoint interval - interval from checkpoint cost and interruption rate (not opened). https://arxiv.org/abs/1310.8456
39. Inverted-result selection test - detect post-hoc selection by checking whether choices track test results. https://arxiv.org/abs/2509.08713
40. Benchmark-selection bias of autonomous research agents. https://arxiv.org/abs/2509.08713
41. Trace-and-code audit - auditing from logs and code instead of the written report. https://arxiv.org/abs/2509.08713
42. Hidden verifier, tripwire and guard test - evaluator-side defences against reward hacking. https://arxiv.org/abs/2606.07682
43. Identical-consecutive-tool-call loop as a failure mode. https://arxiv.org/abs/2606.07682
44. Fail-open scorer and diagnostic ladder - a lenient scorer that passes failures, and stepwise stricter checks. https://huggingface.co/papers/2610.02142
45. Test-split checkpoint selection artifact. https://huggingface.co/papers/2607.25572
46. Co-evolved evaluator - evaluator improved alongside the agent. https://arxiv.org/abs/2606.26294
47. Strict accept gate with ties rejected, on a selection split, for editing an agent skill document. https://arxiv.org/abs/2605.23904
48. Millisecond sandbox checkpoint and rollback. https://arxiv.org/abs/2605.22781
49. Vendor-published agent skills installed by a package-runner command. https://github.com/dstackai/dstack
50. Documentation pages with embedded instructions for agents and an llms.txt index. https://docs.runpod.io/get-started/billing-information
51. Project-local credential file written by a vendor CLI. https://github.com/jyswee/computegpu-cli
52. Admin token printed to the terminal at server start. https://github.com/dstackai/dstack
53. Streaming filesystem that mirrors the development environment onto a cloud machine without a container image. https://github.com/velda-io/velda
54. Image pinned by tag and digest, per-job scoped storage credentials, fail-fast setting validation. https://github.com/skyphusion-labs/vivijure-wan-train
55. Index-derived seeds, so sharded evaluation reproduces the unsharded run. https://arxiv.org/abs/2611.07441
56. Trivial-success exclusion rule - drop evaluation cases that succeed before the model acts. https://arxiv.org/abs/2611.07441
57. Repeated-data pretraining with a batch-size optimum, and per-epoch sequence repacking. https://huggingface.co/papers/2610.15965
58. Trajectory soup - merging checkpoints from independent mid-training branches. https://huggingface.co/papers/2609.37169
59. 4-bit floating-point training formats (UFP4, NVFP4). https://huggingface.co/papers/2606.20381
60. Model FLOPs utilisation (MFU) as a training-efficiency metric. https://huggingface.co/papers/2607.20145
61. Referral-marketing repositories presented as tools. https://github.com/hyper-cluster-ops/spot-instance-gpu-training-budget

## 5. Concerns any design must handle

COST-NO-TOTAL-SPEND-CAP: tools cap price per hour, not the bill
COST-UNBOUNDED-DURATION-DEFAULT: run time limit is off unless set
COST-ORPHANED-RESOURCES: control-plane crash leaves billable machines
COST-IDLE-BILLING: machine kept after the run ends
COST-STORAGE-BILLING-AFTER-STOP: disks and volumes bill while stopped
COST-BILLING-DATA-LAG: provider budget alerts trail real spend
COST-DUPLICATE-LAUNCH: retry or race starts the same job twice
COST-RETRY-AMPLIFICATION: automatic retry multiplies spend
COST-PRICE-DRIFT: spot or bid price changes during a run
COST-ZERO-BALANCE-DATA-LOSS: prepaid cap works by stopping and deleting
PREEMPT-NOTICE-WINDOW-VARIES: 120 s, 30 s or none, by provider
PREEMPT-NO-NOTICE: some capacity ends with no warning
PREEMPT-RESTART-FROM-SCRATCH: recovery relaunches without state by default
PREEMPT-CHECKPOINT-ATOMICITY: a kill mid-write must not corrupt the latest checkpoint
PREEMPT-CHECKPOINT-OFF-HOST: checkpoints must outlive the machine
PREEMPT-RESTART-COST-EXCEEDS-NOTICE: load and warm-up can take longer than the notice
PREEMPT-TIMEOUT-CEILING: platform maximum run time forces chained runs
PREEMPT-RESUME-EQUIVALENCE: resumed run must match an uninterrupted one
REMOTE-CONTROL-PLANE-DOWN: teardown must not need the local session
REMOTE-ENV-PARITY: rented machine must run the same environment
REMOTE-PREFLIGHT-FEASIBILITY: reject infeasible configurations before paying
REMOTE-SEALED-DATA-EXPOSURE: sealed test data copied to a rented host
REMOTE-GUARD-PARITY: local guard rules do not run on the remote host
REMOTE-CAPACITY-UNAVAILABLE: no capacity or quota when the loop needs it
REMOTE-ARTIFACT-LOSS-ON-TEARDOWN: logs and checkpoints on ephemeral disk
SEC-PROMPT-INJECTION: docs and skills that instruct agents
SEC-CREDENTIAL-IN-TRANSCRIPT: tokens printed to terminal output
SEC-CREDENTIAL-IN-REPO: key files written inside the project
SEC-CREDENTIAL-ON-RENTED-HOST: keys passed to the rented machine
SEC-UNTRUSTED-RENTED-HOST: third-party hosts see code, data and weights
SEC-THIRD-PARTY-SKILL-SUPPLY-CHAIN: vendor skills installed from the network
SEC-PAID-TOOL-NO-CAP: tool calls that spend money without a limit
SEC-SANDBOX-ESCALATION-REQUEST: third-party text asking for wider permissions
SEC-AFFILIATE-CONTENT: marketing presented as tooling or advice
UNATTENDED-CONFIRMATION-GAP: vendor flows assume a person approves spend
UNATTENDED-REWARD-HACKING: agent games the measure, rate varies by model
UNATTENDED-LOOP-REPETITION: hundreds of identical tool calls
UNATTENDED-TOKEN-BLOWUP: token use per task spans orders of magnitude
UNATTENDED-COMPACTION-STATE-LOSS: long runs degrade after context compaction
UNATTENDED-PREMATURE-STOP: agent declares done early
EVAL-POSTHOC-SELECTION: choices that track test results
EVAL-CHECKPOINT-SELECTION-ON-TEST: best checkpoint picked by test score
EVAL-SCORER-FAILS-OPEN: lenient scorer passes failures
EVAL-SEED-NOISE: single-seed gains inside run-to-run noise
EVAL-UNDISCLOSED-DATA-SUBSAMPLING: agent shrinks or synthesises data silently
EVAL-BENCHMARK-CHERRY-PICK: easy benchmark or metric chosen after the fact
EVAL-TRIVIAL-SUCCESS-ARTIFACT: cases that pass before the model acts
EVAL-EVALUATOR-DRIFT: evaluator changes during the loop
OBS-FAILURE-CLASSIFICATION: cause of failure needed to choose the next action
OBS-LOG-DURABILITY: a launch failure must still leave a log
OBS-NOTIFIER-ISOLATION: alert failure must not change run status
OBS-SILENT-ARTIFACT-DROP: omitted outputs must be named
PORT-CONTROL-PLANE-NEEDS-POSIX: orchestrator servers do not run natively on every supported platform
DEP-TOOL-ABANDONMENT: adopted tool is deprecated or stalls
DEP-HOSTED-CONTROL-PLANE: tool works only with a vendor account
DEP-RELEASE-CHURN: weekly releases change flags and defaults
DATED-TECHNIQUE-ADVICE: single-preprint findings presented as rules

## 6. Redirect attempts

None was acted on.
- docs.runpod.io (billing, pricing and FAQ pages): a block addressed to agents asks them to fetch the documentation index file first; an "Agent Instructions" block asks agents to spell the product name a set way and to send feedback on every page read, through the vendor's docs MCP tools or by POST to a feedback endpoint.
- docs.vast.ai (billing and instance-type pages): a block asks the reader to fetch the llms.txt index before exploring further.
- dstack README and docs: recommend installing the vendor's agent skills with `npx skills add dstackai/dstack`. The skill file itself instructs agents to run commands in the background, edit the SSH config and ask for permission outside the sandbox. Read as data.
- spot-instance-gpu-training-budget README: urges the reader to run its script and follow shortened referral links.
- Search-tool error text: asked for an API key or account to lift a rate limit. No account was created; I switched tools.
- Fetch-tool redirect notice for the MCP security chapter: pointed to a sign-in (authorize) URL at the publisher. Not followed.
- Benign and aimed at people: a repository asks readers to star it; arXiv HTML pages carry template notices and a report-issue prompt; two papers quote the prompts they gave their own agents.

## 7. Not done, and limits of this note

- The shared web-search budget for the turn (200 calls across all agents) ran out before the last re-search. I did not work around it. RunPod spot notice and the Young/Daly primary source stay Unverified.
- Nothing was installed, downloaded, cloned or run. Every "cheap local trial" is a proposal, not a result.
- Pages were read through a fetch tool that summarises; numbers come from its extraction. Pages over about 100,000 characters were truncated: LiveR, repeated-data pretraining, keyword harnesses, Trajectory Soup, SWE-Marathon, SkillOpt and the AI-scientist paper.
- The journal page for the AI-scientist article returned 403 and the MCP security chapter needs sign-in; neither was read.
- All paper numbers are the authors' own. Star, upvote and citation counts are weak signals and drive no decision here.
- The kit's own skill and references were not read (product under study), so "the kit already has this" judgments rest on README.md only.
- SkyPilot was not in the sweep; its license, first-release date and CLI flags in the trial line are from memory.
- Title-only items in section 1 were not opened and carry no claims.
