# Claude Code add-ons for NN training/fine-tuning: skills, plugins, MCP servers (as of 23 Oct 2026)

*Method: I checked existence, HEAD and tag dates with shallow `git clone`/`git ls-remote` on 23 Oct 2026; the GitHub API was blocked. Stars are GitHub's rounded display. "HEAD" means the latest commit on the default branch.*

## 1. Hugging Face: skills repo/marketplace, HF MCP server, blog

### Takeaway
Hugging Face has the most complete official training stack: `huggingface/skills` (25 skills) plus the remote HF MCP server. The install path has changed since the Dec-2025 blog. The Claude marketplace now exposes only `hf-cli`, and the other skills install with `hf skills add`.

### Cited Findings
- huggingface/skills: ~11.2k stars, HEAD 2026-10-08, no tags, Apache-2.0 — [GitHub](https://github.com/huggingface/skills)
- Training-relevant skills: **huggingface-llm-trainer**, **huggingface-vision-trainer**, **train-sentence-transformers**, **trl-training**, **huggingface-trackio**, **huggingface-community-evals** (inspect-ai/lighteval), huggingface-datasets, huggingface-papers, huggingface-paper-publisher, hf-mem (estimates weight memory), hf-cli. The rest cover Spaces/Gradio, local models, transformers-js and six `hf-cloud-*` SageMaker skills — [README](https://github.com/huggingface/skills/blob/main/README.md)
- `.claude-plugin/marketplace.json` (name `huggingface-skills`, v1.0.35) lists only `hf-cli`, which the README calls intentional — [marketplace.json](https://github.com/huggingface/skills/blob/main/.claude-plugin/marketplace.json)
- README install: `/plugin marketplace add huggingface/skills`, then `/plugin install hf-cli@huggingface/skills`, then `hf skills add <skill-name>`. The CLI also has `--global`, `--dest PATH`, `--force` and `hf skills list|update` — [README](https://github.com/huggingface/skills/blob/main/README.md), [hf-cli SKILL.md](https://github.com/huggingface/skills/blob/main/skills/hf-cli/SKILL.md)
- Also listed in Anthropic's official marketplace as `huggingface-skills`, pinned to commit c3ff942 (the current HEAD) — [claude-plugins-official](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json)
- huggingface-llm-trainer — [SKILL.md](https://github.com/huggingface/skills/blob/main/skills/huggingface-llm-trainer/SKILL.md):
  - Runs TRL or Unsloth on HF Jobs: SFT, DPO, GRPO, reward modeling, GGUF conversion.
  - Scripts for SFT/DPO/GRPO/Unsloth, plus `estimate_cost.py` and `dataset_inspector.py`.
  - Needs a **Pro/Team/Enterprise plan** ("Jobs require paid plan") and a **write-scoped HF_TOKEN** passed as a job secret.
  - Calls the 30-minute default timeout "TOO SHORT" and requires Trackio logging.
- `hf jobs run --flavor` ranges from t4-small to a100x8, h200x8 and rtx-pro-6000x8 — [hf-cli SKILL.md](https://github.com/huggingface/skills/blob/main/skills/hf-cli/SKILL.md)
- huggingface/hf-mcp-server: ~308 stars, tag v0.4.31 (2026-10-19) — [GitHub](https://github.com/huggingface/hf-mcp-server)
  - Claude Code with OAuth: `claude mcp add hf-mcp-server -t http https://huggingface.co/mcp?login`
  - With a token: `… https://huggingface.co/mcp -H "Authorization: Bearer <HF_TOKEN>"`
  - Tools are chosen at huggingface.co/settings/mcp.
  - Repo creation, Jobs, dynamic Space and sandbox tools need auth. Requests without a token get an anonymous tool set.
  - [README](https://github.com/huggingface/hf-mcp-server/blob/main/README.md)
- Built-in tools: `hub_repo_search`, `hub_repo_details`, `hf_fs`, `create_repo`, `hf_jobs`, `dynamic_space`, plus opt-in sandbox tools (`hf_sandbox`, `hf_sandbox_exec`, `hf_sandbox_fs`). A test asserts these are **retired**: `model_search`, `dataset_search`, `paper_search`, `hf_doc_search`, `hf_doc_fetch`, `space_search` — [tool-ids.ts](https://github.com/huggingface/hf-mcp-server/blob/main/packages/mcp/src/tool-ids.ts), [tool-ids.test.ts](https://github.com/huggingface/hf-mcp-server/blob/main/packages/mcp/src/tool-ids.test.ts)
- HF docs: `hf_fs` navigates the Hub, "including semantic searches of Documents and Spaces". Search covers models, datasets, Spaces and papers — [HF docs](https://huggingface.co/docs/hub/agents-mcp)
- Blog "We Got Claude to Fine-Tune an Open Source LLM" (4 Dec 2025) — [HF blog](https://huggingface.co/blog/hf-skills-training):
  - SFT of Qwen3-0.6B on t4-small took about 20 minutes and cost about $0.30.
  - Cost guidance: $5–15 for 1–3B models, $15–40 for 3–7B with LoRA.
  - Commands used: `/plugin install hf-llm-trainer@huggingface-skills` and `claude mcp add --transport http hf-skills https://huggingface.co/mcp?bouquet=skills --header "Authorization: Bearer $HF_TOKEN"`.
  - It claims 0.5B–70B support but also says 7B+ is "not suitable".

### Inferences
- The blog's commands are stale: the skill is now `huggingface-llm-trainer` and is no longer in the client marketplace.
- The README's `hf-cli@huggingface/skills` breaks the `plugin@marketplace-name` convention. `/plugin install hf-cli@huggingface-skills` is probably correct; verify it.
- The trainer SKILL.md still calls the retired `hf_doc_search`/`hf_doc_fetch`. Use `hf_fs` or the `hf` CLI instead.
- `hf_jobs` and `create_repo` spend money or write to the Hub, so use a fine-grained token.
- HF MCP and hf-cli overlap heavily; pick one as the primary path.

### Gaps
- Where `hf skills add` installs for Claude Code by default (versus `--dest .claude/skills`).
- Which MCP tools need a PRO plan.

## 2. ML research-engineering skill libraries and vendor skills/plugins

### Takeaway
Orchestra's AI-Research-SKILLs is the broadest training library (98 skills), but it has had no commits since 15 Jun 2026. anthropics/skills has nothing training-specific. Official vendor skills exist for HF, MLflow, NVIDIA, W&B, SkyPilot, Lightning AI, RunPod, Databricks, SageMaker, Together and DuckDB. I found none for Modal, PyTorch, Unsloth or Axolotl.

### Cited Findings
- Orchestra-Research/AI-Research-SKILLs (the old zechenzhangAGI URL redirects here): ~13.7k stars, tag v1.7.2, HEAD 2026-06-15, MIT, community-maintained. Categories include — [GitHub](https://github.com/Orchestra-Research/AI-Research-SKILLs):
  - fine-tuning (Axolotl, LLaMA-Factory, PEFT, Unsloth)
  - post-training (TRL, GRPO, OpenRLHF, SimPO, verl…)
  - distributed-training (Accelerate, DeepSpeed, Megatron-Core, FSDP2, Lightning, Ray Train)
  - optimization (FlashAttention, bitsandbytes, GPTQ/AWQ/GGUF)
  - evaluation (lm-eval-harness), mlops (W&B, MLflow, TensorBoard), infrastructure (Modal, Lambda, SkyPilot)
  - autoresearch, ml-paper-writing
- Orchestra install by category: `/plugin marketplace add orchestra-research/AI-research-SKILLs`, then `/plugin install fine-tuning@ai-research-skills`. Alternatively `npx @orchestra-research/ai-research-skills` (v1.7.2) installs all 98 and "starts autonomous research" — [README](https://github.com/Orchestra-Research/AI-Research-SKILLs)
- K-Dense "claude-scientific-skills" is **renamed Scientific Agent Skills** — [GitHub](https://github.com/K-Dense-AI/scientific-agent-skills):
  - ~53.9k stars, tag v2.72.0 (2026-10-01), HEAD 2026-10-19.
  - 177 skills, mostly life and physical sciences. ML-relevant: transformers, pytorch-lightning, torch-geometric, stable-baselines3, pufferlib, scikit-learn, shap, modal.
  - Install with `npx skills add K-Dense-AI/scientific-agent-skills`, or `gh skill install K-Dense-AI/scientific-agent-skills <skill> --agent claude-code` (pin with `--pin <tag|sha>`).
  - Ships SECURITY.md and automated skill-scan reports.
- anthropics/skills (~182.8k stars, HEAD 2026-10-09): documents, design, claude-api, mcp-builder, skill-creator. **No ML-training skills** — [GitHub](https://github.com/anthropics/skills)
- claude-plugins-official (HEAD 2026-10-21) — [marketplace.json](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json):
  - 315 plugins, installed with `/plugin install <name>@claude-plugins-official`; external entries are pinned to commit SHAs.
  - ML-relevant: huggingface-skills, context7, mlflow, nvidia-skills, sagemaker-ai, databricks, togetherai-skills, duckdb-skills, datarobot-agent-skills.
  - No W&B, Modal, SkyPilot, Lightning, RunPod or Jupyter entry.
- wandb/skills (HEAD 2026-10-12): wandb-primary, wandb-eval-tables, wandb-autoresearch, weave-instrument and others. `npx skills add wandb/skills`. Needs WANDB_API_KEY — [GitHub](https://github.com/wandb/skills)
- mlflow/skills (HEAD 2026-10-22): 13 skills, mostly GenAI-agent tracing and evaluation (including querying-mlflow-metrics). `npx skills add mlflow/skills` or `mlflow@claude-plugins-official` — [GitHub](https://github.com/mlflow/skills)
- NVIDIA/skills: ~3.2k stars, HEAD 2026-10-22, "Official, NVIDIA-verified" — [GitHub](https://github.com/NVIDIA/skills):
  - About 425 skills, including nemo-automodel-distributed-training, `nemo-mbridge-perf-*` (CUDA graphs, CPU offload, MoE comm overlap) and TAO trainers.
  - Install: `npx skills add nvidia/skills --skill <name> --agent claude-code` (skills CLI ≥1.5.16).
  - The official-marketplace plugin bundles only `nvidia-skill-finder`.
- Lightning-AI/skills: 5 stars, v1.2.0, HEAD 2026-10-14 — [GitHub](https://github.com/Lightning-AI/skills):
  - Covers jobs, studios, sandboxes, pipelines, deployments, litdata, billing and cost-estimation.
  - Install: `claude plugin marketplace add Lightning-AI/skills`, then `claude plugin install lightning@lightning-ai`.
  - Auth: `lightning login` or `LIGHTNING_API_KEY`.
- Unsloth's repo has only skills internal to its Studio app. Axolotl has AGENTS.md and CLAUDE.md but no skill or MCP — [unsloth](https://github.com/unslothai/unsloth), [axolotl](https://github.com/axolotl-ai-cloud/axolotl)

### Inferences
- Orchestra is the broadest library but four months stale on fast-moving libraries like TRL and verl. Install single categories, read each SKILL.md and pin a commit.
- K-Dense matters only for scientific-domain ML (GNNs, RL, chemistry).
- Unsloth, Axolotl and PyTorch are covered indirectly, through HF llm-trainer's Unsloth reference, Orchestra and Context7.

### Gaps
- Stars for wandb/skills and mlflow/skills were not captured.
- Unknown whether `querying-mlflow-metrics` handles classic training metrics.

## 3. Documentation/knowledge MCPs

### Takeaway
Context7 is the standard docs MCP. Its PyTorch and TRL corpora are large; its Optuna corpus is thin. DeepWiki is free and needs no auth for public repos. blazickjp/arxiv-mcp-server is the actively maintained arXiv option. I found no alphaXiv MCP.

### Cited Findings
- upstash/context7: ~63.5k stars, HEAD 2026-10-22; git tags stop at v1.0.30 (2025-11-24) — [README](https://github.com/upstash/context7):
  - Remote endpoint `https://mcp.context7.com/mcp` with `Authorization: Bearer <key>`. A free key raises rate limits.
  - `npx ctx7 setup --claude` runs OAuth, creates the key and installs a skill.
  - Tools: `resolve-library-id`, `query-docs`.
- Claude Code: `claude mcp add --scope user --header "Authorization: Bearer YOUR_API_KEY" --transport http context7 https://mcp.context7.com/mcp` — [all-clients.mdx](https://github.com/upstash/context7/blob/master/docs/resources/all-clients.mdx). Or `/plugin install context7@claude-plugins-official`, which prompts for auth — [plugin](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/context7)
- Coverage (each page shows only "Latest", no version list):

| Library | Tokens | Snippets | Updated | Source |
|---|---|---|---|---|
| pytorch/pytorch | 2.04M | 13,189 | "14 hours ago" | [link](https://context7.com/pytorch/pytorch) |
| huggingface/trl | 303,611 | 2,192 | "4 weeks ago" | [link](https://context7.com/huggingface/trl) |
| optuna/optuna | 24,309 | 290 | "3 months ago" | [link](https://context7.com/optuna/optuna) |

- DeepWiki (Cognition) — [Devin docs](https://docs.devin.ai/work-with-devin/deepwiki-mcp.md):
  - Endpoint `https://mcp.deepwiki.com/mcp`; no auth for public repos. Private repos need the Devin MCP plus an API key.
  - Tools: `read_wiki_structure`, `read_wiki_contents`, `ask_question`.
  - Setup: `claude mcp add -s user -t http deepwiki https://mcp.deepwiki.com/mcp`
- blazickjp/arxiv-mcp-server (community): ~3.1k stars, tag v0.8.2 (2026-10-08) — [GitHub](https://github.com/blazickjp/arxiv-mcp-server):
  - 19 tools, including search_papers, read_paper_section, get_paper_latex_section, citation_graph, export_citations, watch_topic and semantic_search.
  - Setup: `claude mcp add --transport stdio --scope user arxiv -- uvx arxiv-mcp-server`
- Semantic Scholar: smaniches/semantic-scholar-mcp is active (v1.2.2, HEAD 2026-10-19); zongmin-yu/semantic-scholar-fastmcp-mcp-server last changed 2026-03-20 — [smaniches](https://github.com/smaniches/semantic-scholar-mcp), [zongmin-yu](https://github.com/zongmin-yu/semantic-scholar-fastmcp-mcp-server)

### Inferences
- The thin Optuna corpus means Optuna API details may need direct doc fetches.
- HF papers are also reachable through HF MCP search and the huggingface-papers skill.

### Gaps
- Semantic Scholar MCP tools and stars not evaluated.
- Context7's version pinning untested.

## 4. Experiment-tool MCPs

### Takeaway
Three solid tracker MCPs:
- **W&B:** hosted, rich run analysis, read-only mode.
- **Trackio:** built into the library; local reads need no auth.
- **MLflow:** built in as `mlflow mcp run`, experimental, training toolset selected by env var.

optuna-mcp is official but rarely released. I found no TensorBoard MCP.

### Cited Findings
- wandb/wandb-mcp-server: ~69 stars, version 0.4.3, **no git tags**, HEAD 2026-10-22 — [README](https://github.com/wandb/wandb-mcp-server):
  - Hosted: `claude mcp add --transport http wandb https://mcp.withwandb.com/mcp --scope user --header "Authorization: Bearer <WANDB_API_KEY>"`
  - Local: `claude mcp add wandb -e WANDB_API_KEY=… -- uvx --from git+https://github.com/wandb/wandb-mcp-server@vX.Y.Z wandb_mcp_server`
  - Tools: query_wandb_tool, probe_project_tool, get_run_history_tool, compare_runs_tool, diagnose_run_tool ("Why did this run diverge?"), create_wandb_report_tool, search_wandb_docs_tool, plus registry/artifact and Weave-trace tools.
  - `WANDB_MCP_ACCESS_MODE=read-only` drops the write tools.
- MLflow docs: needs `mlflow[mcp]>=3.5.1`, labelled "experimental". Setup: `claude mcp add mlflow-mcp -e MLFLOW_TRACKING_URI=<uri> -- uv run --with "mlflow[mcp]>=3.5.1" mlflow mcp run`. The docs describe trace management — [MLflow docs](https://mlflow.org/docs/latest/genai/mcp/)
- MLflow source: tools are generated from MLflow CLI commands, and `MLFLOW_MCP_TOOLS` selects toolsets — [server.py](https://github.com/mlflow/mlflow/blob/master/mlflow/mcp/server.py):
  - `genai` (default): traces, scorers, experiments, runs
  - `ml`: experiments, runs, models, deployments
  - or a comma-separated list
- Trackio (gradio-app/trackio): ~1.7k stars, tag v0.5.0, HEAD 2026-10-20 — [docs](https://github.com/gradio-app/trackio/blob/main/docs/source/api_mcp_server.md):
  - Start: `pip install "trackio[mcp]"`, then `trackio show --mcp-server`. Endpoint `http://127.0.0.1:7860/mcp/`, or `https://<space>.hf.space/mcp/`.
  - 12 read tools (get_all_projects, get_runs_for_project, get_metric_values, get_run_summary, get_system_logs, get_alerts…).
  - delete_run, rename_run and trigger_sync need a write_token or hf_token.
- optuna/optuna-mcp (official): ~84 stars. Last release v0.2.0 (2025-10-30); HEAD 2026-10-22 is a CI change — [GitHub](https://github.com/optuna/optuna-mcp):
  - Tools: create_study, set_sampler, ask, tell, best_trial(s), 10 `plot_*` tools, launch_optuna_dashboard.
  - Run with `uvx optuna-mcp --storage sqlite:///optuna.db`, or via Docker.

### Inferences
- Claude Code commands derived from generic syntax (not in the READMEs):
  - `claude mcp add --transport http trackio http://127.0.0.1:7860/mcp/`
  - `claude mcp add optuna -- uvx optuna-mcp --storage sqlite:///optuna.db`
- For NN training, use `MLFLOW_MCP_TOOLS=ml` (or `experiments,runs`). Which MLflow release first shipped this is unverified.
- W&B's local install pins `@vX.Y.Z`, but the repo has no tags. Pin a commit SHA or use the hosted server.
- optuna-mcp's ask/tell loop suits agent-steered HPO. Batch sweeps are simpler as a plain Optuna script with sqlite storage.

### Gaps
- No official TensorBoard MCP (tensorflow/tensorboard-mcp does not exist); third-party ones not surveyed.
- Full MLflow MCP tool list not enumerated.

## 5. Compute/infra

### Takeaway
Official agent tooling exists for SkyPilot (skill/plugin, no MCP), RunPod (hosted MCP plus plugin), Lightning AI and HF Jobs. I found no official MCP or skill for Modal, Lambda, vast.ai or NVIDIA GPU monitoring.

### Cited Findings
- SkyPilot (HEAD 2026-10-22) — [INSTALL.md](https://github.com/skypilot-org/skypilot/blob/master/agent/INSTALL.md), [marketplace.json](https://github.com/skypilot-org/skypilot/blob/master/.claude-plugin/marketplace.json):
  - Official skill in the main repo at `agent/skills/skypilot`, with references for the CLI, YAML spec, Python SDK, job investigation, troubleshooting and Slurm migration, plus evals.
  - Plugin `skypilot@skypilot` v1.0.0 covers 25+ clouds, Kubernetes and Slurm.
  - Install: `claude plugin marketplace add skypilot-org/skypilot`, then `claude plugin install skypilot@skypilot`.
- runpod/runpod-mcp (official): ~83 stars, v4.5.0 (2026-10-20) — [GitHub](https://github.com/runpod/runpod-mcp):
  - Hosted at `https://mcp.runpod.io/` with OAuth ("no API key on disk"). Manages Pods, Serverless endpoints, templates and network volumes.
  - Hosted setup: `claude mcp add --transport http runpod -s user https://mcp.runpod.io/`
  - Local setup: `-e RUNPOD_API_KEY=… -- npx -y @runpod/mcp-server@latest`
  - The hosted server sends anonymous telemetry per call; opt out with the header `X-Runpod-Analytics: off`.
  - OAuth creates the key for whichever team is selected in the console.
- runpod/runpod-plugins-official (v1.8.0): `/plugin marketplace add runpod/runpod-plugins-official`, then `/plugin install runpod@runpod`. Skills include pod-deploy, pod-doctor, serverless-deploy, cost-audit, runpodctl and flash — [GitHub](https://github.com/runpod/runpod-plugins-official)
- Modal: modal-labs/modal-examples only shows how to *host* an MCP server on Modal. Community project george-bobby/mcp-modal (v0.5.0, 2026-09-09) exists but I did not evaluate it — [modal-examples](https://github.com/modal-labs/modal-examples), [mcp-modal](https://github.com/george-bobby/mcp-modal)
- GPU monitoring: community project mesutoezdil/mcp-gpu-server (v0.2.2, HEAD 2026-10-22). No NVIDIA-official MCP — [GitHub](https://github.com/mesutoezdil/mcp-gpu-server)

### Inferences
- GPU-monitoring MCPs add little over running `nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv` through Bash.
- RunPod tools create billable resources. Use a restricted key and local or project scope.
- The SkyPilot skill drives the `sky` CLI with the cloud credentials SkyPilot already has.

### Gaps
- vast.ai and Lambda: search surfaced only third-party integrations.
- Modal skills exist only through Orchestra and K-Dense.

## 6. Notebook & data

### Takeaway
Datalayer's Jupyter MCP is mature and ships a Claude Code plugin. MotherDuck's DuckDB MCP and DuckDB's official skills cover analysis of metrics and logs. Kaggle has an official MCP docs page, but I could not verify its details.

### Cited Findings
- datalayer/jupyter-mcp-server: ~1.3k stars, v2.2.4 (2026-10-11), HEAD 2026-10-18, BSD-3 — [GitHub](https://github.com/datalayer/jupyter-mcp-server):
  - Plugin: `/plugin marketplace add datalayer/jupyter-mcp-server`, then `/plugin install datalayer` (adds `/datalayer:notebook|run|status`).
  - Manual setup needs JupyterLab, jupyter-collaboration, jupyter-mcp-tools and the env vars `JUPYTER_URL`/`JUPYTER_TOKEN`.
  - Can execute in cloud sandboxes (Colab, Kaggle, Modal, E2B, CoreWeave).
- motherduckdb/mcp-server-motherduck (official): ~519 stars, v1.1.0 (2026-10-07) — [GitHub](https://github.com/motherduckdb/mcp-server-motherduck):
  - Setup: `claude mcp add --scope user duckdb --transport stdio -- uvx mcp-server-motherduck --db-path :memory: --read-write --allow-switch-databases`
  - DuckDB files open read-only unless `--read-write` is passed. MotherDuck needs `motherduck_token`. A remote MotherDuck MCP is also available.
- duckdb/duckdb-skills (DuckDB Foundation, HEAD 2026-04-14, in the official marketplace): read-file, query, attach-db, convert-file, duckdb-docs, s3-explore — [GitHub](https://github.com/duckdb/duckdb-skills)
- Kaggle: a page titled "MCP Server Documentation | Kaggle" exists at kaggle.com/docs/mcp, but its body did not render — [Kaggle](https://www.kaggle.com/docs/mcp). I found no Kaggle-org GitHub repo for it. Community project arrismo/kaggle-mcp last changed 2026-05-20 — [GitHub](https://github.com/arrismo/kaggle-mcp)

### Inferences
- An in-memory DuckDB with `read_csv`/`read_parquet` gives the agent SQL over exported training logs. Read-only file mode is the safer default.

### Gaps
- The Kaggle MCP's URL, auth and tools are unverified.

## 7. Security

### Takeaway
Real incidents in 2025–26 hit every layer: malicious MCP packages, MCP-client RCE, a compromised MCP host, malicious skills, and auto-approval bugs in Claude Code project files. Keep Claude Code current, prefer pinned official sources and use read-only or least-privilege tokens. Note that headless `claude -p` loads a project's `.mcp.json` servers without prompting.

### Cited Findings
- Check Point found three flaws in how Claude Code handles project files — [HackMag](https://hackmag.com/news/claude-code-flaws), [Check Point](https://research.checkpoint.com/2026/rce-and-api-token-exfiltration-through-claude-code-project-files/) (original not retrievable):

| Flaw | CVSS | Fixed in |
|---|---|---|
| Hooks ran commands on project open (no CVE) | 8.7 | v1.0.87 |
| CVE-2025-59536: project settings auto-approved MCP servers | 8.7 | v1.0.111 |
| CVE-2026-21852: a project-set `ANTHROPIC_BASE_URL` leaked the API key before the trust dialog | 5.3 | v2.0.65 |

- CVE-2026-47751: claude-code-action before 1.0.74 enabled a pull request's `.mcp.json`, allowing code execution on the runner and theft of secrets — [CIRCL](https://cve.circl.lu/cve/CVE-2026-47751)
- postmark-mcp (npm, Sep 2025): version 1.0.16 quietly BCC'd every email to an attacker — [Snyk](https://snyk.io/blog/malicious-mcp-server-on-npm-postmark-mcp-harvests-emails/)
- CVE-2025-6514 (CVSS 9.6): in mcp-remote 0.0.5–0.1.15, a malicious OAuth endpoint led to OS command execution. Fixed in 0.1.16 — [JFrog](https://jfrog.com/blog/2025-6514-critical-mcp-remote-rce-vulnerability/)
- Smithery: a path-traversal bug exposed a fly.io token that controlled 3,000+ hosted apps, mostly MCP servers. Fixed June 2025 — [SC Media](https://www.scworld.com/news/smithery-ai-fixes-path-traversal-flaw-that-exposed-3000-mcp-servers)
- Snyk ToxicSkills (5 Feb 2026) scanned 3,984 skills from ClawHub and skills.sh — [Snyk](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub):
  - 13.4% had critical issues and 36.8% had at least one issue.
  - 76 were confirmed malicious; 91% of those used prompt injection.
  - Recommended audit: `uvx mcp-scan@latest --skills`.
- Claude Code docs — [Claude Code docs](https://code.claude.com/docs/en/mcp):
  - Scopes: local (default, in `~/.claude.json`), project (`.mcp.json`), user.
  - Interactive sessions ask before using project servers. `claude -p`, the Agent SDK and cloud sessions **load them without a prompt**; block them with `disabledMcpjsonServers` or `--strict-mcp-config`.
  - A committed `enableAllProjectMcpServers` is ignored in untrusted folders.
  - Anthropic and cloud credential env vars expand to empty in remote URLs and headers.
  - MCP output is capped at 25k tokens by default (`MAX_MCP_OUTPUT_TOKENS`).
  - Org policy: `managedMcpServers`, `deniedMcpServers`.
  - The docs warn that servers fetching external content risk prompt injection.

### Inferences
- Recommended practice:
  - Pin versions: `gh skill install --pin` for skills, exact npx/uvx versions for MCP packages, never `@latest`.
  - Turn on read-only modes where offered (W&B, DuckDB).
  - Keep tokens in env vars, not committed headers. Give agents their own low-privilege HF, W&B and RunPod tokens.
  - Read each SKILL.md and its scripts before installing, since skills run with your shell's permissions.
- Context7, DeepWiki and arXiv return third-party text, so they are prompt-injection vectors.

### Gaps
- I found no incident involving the specific ML skills or MCPs listed here.
- The official MCP registry was not consulted.

## 8. Tiered recommendation

### Takeaway
Essential: Context7, your tracker's MCP and, for HF/TRL fine-tuning, the HF trainer skills. The rest depends on the setup.

### Cited Findings
- Synthesised from sections 1–7.

### Inferences
- **Essential**
  1. Context7 remote MCP, for version-accurate PyTorch, Transformers and TRL APIs.
  2. One tracker MCP in read-only mode: W&B hosted, Trackio local, or MLflow with `MLFLOW_MCP_TOOLS=ml`.
  3. For HF/TRL work: `hf-cli`, then `hf skills add` for `trl-training`, `huggingface-llm-trainer` and `huggingface-trackio`. Jobs need a paid plan.
- **Situational**
  - HF MCP server, for Hub discovery and Jobs over OAuth. Overlaps with hf-cli.
  - Orchestra, selected categories only (fine-tuning, post-training, distributed-training, optimization, evaluation), pinned.
  - SkyPilot plugin, for multi-cloud, Kubernetes or Slurm.
  - RunPod MCP and plugin.
  - Lightning plugin (new, 5 stars).
  - NVIDIA skills, for NeMo or Megatron.
  - optuna-mcp, for interactive HPO.
  - Jupyter MCP, for notebook-centric work.
  - DuckDB/MotherDuck, for log analytics.
  - DeepWiki, for unfamiliar training repos.
  - arXiv MCP, for reproducing papers.
  - wandb/skills.
  - K-Dense, for scientific ML.
- **Skip**
  - GPU-monitoring MCPs; use `nvidia-smi`.
  - anthropics/skills for training (skill-creator is still useful for writing your own).
  - mlflow/skills, unless tracing GenAI agents.
  - Unaudited community MCPs for Modal, Kaggle, vast.ai or Semantic Scholar.
  - Orchestra's all-in-one `npx` install, which launches an autonomous research loop.

### Gaps
#### Unverified / not found
- **Not found** (`git ls-remote` fails, 23 Oct 2026):
  - modal-labs/{modal-mcp, skills, modal-mcp-toolbox, agent-skills}
  - skypilot-org/skypilot-mcp
  - Kaggle/{kaggle-mcp, kaggle-mcp-server}
  - unslothai/{skills, unsloth-mcp, unsloth-skills}
  - pytorch/skills
  - axolotl-ai-cloud/axolotl-mcp
  - Lightning-AI/lightning-mcp
  - lambdal/{lambda-mcp, lambda-cloud-mcp}
  - vast-ai/{vast-mcp, mcp-server}
  - alphaxiv/alphaxiv-mcp
  - tensorflow/tensorboard-mcp
  - NVIDIA/nvidia-mcp
  - mlflow/mlflow-mcp
  - huggingface/trackio (Trackio is at gradio-app/trackio)
- **Unverified:**
  - Kaggle MCP details.
  - Any official vast.ai, Lambda, Modal or alphaXiv MCP.
  - Quality of community GPU, Modal and SkyPilot MCPs (e.g. slapglif/skymcp, last commit 2026-03-25).
