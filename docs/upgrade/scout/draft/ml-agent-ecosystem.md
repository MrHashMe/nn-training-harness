# ML-agent ecosystem: skills, plugins and MCP servers for ML training work

Scout draft. Checked 10–11 November 2026 (rows carry `11-10` or `11-11`, year 2026).
Baseline re-checked: `docs/research-notes/skills_plugins_mcp.md` and `.claude/skills/nn-training/references/stack.md` (both 23 Oct 2026).

Status codes: **V** Verified on a primary page, repository or package index. **I** Inferred (search-engine summary of a primary
page, a secondary report, or reasoning from verified facts). **U** Unverified.

Method: read-only web research (search, page fetch, GitHub API). Nothing was installed, cloned or executed. Query families used:
latest release notes; security and failure modes; alternatives; pricing and limits; benchmarks and leaderboards; state-of and
surveys; limitations and postmortems; awesome lists.

## Summary (10 lines)

1. Both default MCP servers (Context7, Hugging Face) are remote network services, so under the adoption rule they must become optional and off by default; today `install.py` adds them unless `--no-mcp` is passed.
2. Context7 4.6.0 is healthy and cheap (free 1,000 calls/month with a key) but was the delivery channel of a real registry-borne prompt injection (ContextCrush, CVE-2026-75130); its output is untrusted data.
3. Hugging Face MCP 0.4.34 can spend money (Jobs need only pre-paid credits, not a paid plan), create repos and Spaces, run sandboxes and write or delete repo files; its settings page only hides tools, and the kit's ask rules miss `hf_sandbox_fs` and `hf_fs_write`.
4. Vendor skill catalogs (Hugging Face, NVIDIA, W&B, MLflow, SkyPilot, Lightning) now ship one SKILL.md tree for Claude Code, Codex and Cursor. None replaces the kit's guard and controller; the useful take is mostly ideas (trust pipeline, skill bench, bounded research loop).
5. Research scouting works without accounts through the arXiv API (one request per 3 s) and the Hugging Face Papers API, using only the standard library. OpenAlex now requires a key; Semantic Scholar's keyless pool is shared and throttled.
6. Built-in web tools differ per agent (Claude Code WebSearch/WebFetch with domain rules; Codex `web_search` cached by default; Cursor web tools with auto-accept off), so the scouting step needs a per-agent table and a no-web fallback.
7. `stack.md` is stale or incomplete in several rows after 19 days (PyTorch 2.15.0 shipped, HF Jobs claim wrong, `mcp-scan` renamed and now account-bound, tracker MCP mutation tools not mentioned).
8. Two supply-chain events the earlier notes missed change installer design: Plugin4Shell (pinned commit SHAs were not verified until Claude Code 2.1.179 / Codex 0.146.0) and the skills.sh typosquat campaign (benign skills turned malicious after listing).
9. Skill efficacy evidence: curated skills help (+16.2 points on SkillsBench), self-generated skills do not (−1.3), similar co-installed skills displace each other in about one run in five, and the same skills score differently per agent. The kit needs a cheap with/without check per agent.
10. Recommended: optional stdlib scout module, deny-by-default MCP permission template, hash-manifest and minimum-client-version checks in the installer, and no third-party skill installed by default.

## Q1. The two default MCP servers

What the kit does now (local read, 11-10, V): `mcp.json` holds `context7` (`https://mcp.context7.com/mcp`) and `huggingface`
(`https://huggingface.co/mcp?login`); `install.py` merges them into the target `.mcp.json` unless `--no-mcp`;
`settings.fragment.json` has ask rules for `mcp__huggingface__hf_jobs`, `create_repo`, `dynamic_space`, `hf_sandbox`, `hf_sandbox_exec`.

### Context7

| Claim | Status | Checked | Source |
|---|---|---|---|
| `@upstash/context7-mcp` 4.6.0 and `ctx7` CLI 0.11.0 released 2026-11-09 (4.5.1/0.10.0 on 11-06, 4.5.0/0.9.0 on 11-03). Three releases in a week. | V | 11-10 | https://github.com/upstash/context7/releases |
| Two tools: `resolve-library-id` (query, libraryName) and `query-docs` (libraryId, query, optional language). Endpoint `https://mcp.context7.com/mcp`, optional `Authorization: Bearer` key. MIT client; backend private. | V | 11-10 | https://github.com/upstash/context7/blob/master/README.md |
| A second mode exists without MCP: "CLI + Skills" (`ctx7 library`, `ctx7 docs`), set up by `npx ctx7 setup` (OAuth, creates a key, installs a skill; needs Node.js 22.13+). | V | 11-10 | same README |
| Free plan: 1,000 API calls/month with a free account and key, then blocked with 20 bonus calls/day. Pro $10/seat/month, 2,000 calls, then $5 per 1,000. | V | 11-10 | https://context7.com/plans , https://context7.com/docs/plans-pricing |
| Keyless (no account) quota is not published. | U | 11-10 | only a third-party guide gives a number |
| Only the query text and library name are sent; the vendor runs an LLM on every request (reason given for the January 2026 free-tier cut). | I | 11-10 | vendor statements quoted in pricing pages and coverage |
| ContextCrush: library "Custom Rules" were served verbatim to agents. Demo read `.env` files, exfiltrated through a GitHub issue and deleted files; trust signals were gameable. Found 18 Feb 2026, server-side fix 23 Feb, disclosed 5 Mar. | V | 11-10 | https://noma.security/noma-labs/contextcrush |
| Vendor write-up (2026-10-22): rules, titles and descriptions are now injection-checked; CVE-2026-75130 (GHSA-97r6-3rgm-v39r); vendor agrees the structural risk (open registry plus trusted delivery) remains. README says content is community-contributed and its security is not guaranteed. | V | 11-10 | https://context7.com/guides/contextcrush |
| Tool-schema overhead is small (two tools). Large MCP servers cost tens of thousands of tokens up front unless the client loads tools lazily; figures come from vendor blogs with different methods. | I | 11-11 | https://www.checklyhq.com/blog/mcp-vs-cli-token-efficiency/ , https://getunblocked.com/blog/mcp-token-budget-autopsy/ |

### Hugging Face MCP server

| Claim | Status | Checked | Source |
|---|---|---|---|
| v0.4.34 (2026-11-10), v0.4.33 (11-04: validates owner and repo names in `hf://` URIs), v0.4.32 (10-26: Space hardware option in `create_repo`), v0.4.31 (10-19). | V | 11-10 | https://github.com/huggingface/hf-mcp-server/releases |
| Built-in tool IDs: repo search, `create_repo`, repo details, `hf_fs`, `hf_jobs`, `dynamic_space`; sandbox group `hf_sandbox`, `hf_sandbox_exec`, `hf_sandbox_fs`. | V | 11-11 | https://github.com/huggingface/hf-mcp-server/blob/main/packages/mcp/src/tool-ids.ts |
| A write tool `hf_fs_write` exists (`put`, `rm`; model, dataset, Space and bucket repos; `destructiveHint: true`; needs a token). It is not in the tool-ID constants file, so how and when it is advertised is unclear. | V (existence), U (exposure) | 11-11 | https://github.com/huggingface/hf-mcp-server/blob/main/packages/mcp/src/hf-fs-write.ts |
| The settings page controls which tools are advertised, "not whether a direct `tools/call` to a known tool may execute". Token scope and client permission rules are the only real boundary. | V | 11-10 | https://github.com/huggingface/hf-mcp-server/blob/main/README.md |
| Requests without a token get an anonymous tool set; the server also serves Agent Skills over MCP (`skills/list`, `skills/get`), with manifest size verification "not yet implemented". | V | 11-10 | same README |
| HF Jobs are available to any account with a positive credit balance, billed per minute; PRO is not required. Examples per hour: cpu-basic $0.01, t4-small $0.40, a10g-small $1.00, a10g-large $1.50, a100-large $2.50, h200 $5.00, h200x8 $40.00. | V | 11-10 | https://huggingface.co/docs/hub/en/jobs-pricing |
| Hub rate limits per 5 minutes: anonymous (per IP) 500 API / 3,000 resolver / 100 page requests; free user 1,000 / 5,000 / 200; PRO 2,500 / 12,000 / 400. | V | 11-10 | https://huggingface.co/docs/hub/rate-limits |
| Optional capabilities in account settings: "Contribute Repos", "Sandboxes", "Run and Manage Jobs", Dynamic Spaces. | V | 11-10 | https://huggingface.co/docs/hub/agents-mcp |
| Which tool now serves paper search (stack.md says the server offers it) was not confirmed in the current tool list. | U | 11-11 | — |
| A third-party wiki answer about this server was stale (old tool names). | V (observed) | 11-10 | DeepWiki query in this session |

### Verdict

- **Both leave the default install and become optional modules, off by default.** Reason 1: the adoption rule (network service, account for full use). Reason 2: unattended runs. `claude -p` loads project MCP servers without asking (stack.md, not re-checked: I), and the proposed research loop runs with nobody to answer prompts. Reason 3: both are channels for third-party text.
- **Context7 (optional, interactive use):** keep as the docs module. Recommend a key (the keyless quota is unknown), state that results are untrusted data, and keep the Optuna caveat. Assess the CLI + Skills mode as a lighter alternative; it needs Node and an OAuth setup step.
- **Hugging Face MCP (optional):** offer two profiles. (a) Anonymous, read-only (`https://huggingface.co/mcp` without `?login`) for search and repo details. (b) Logged in with a fine-grained read token. Spending and writing tools stay behind ask rules in interactive mode and deny rules in unattended mode.
- **Permission template must be deny-by-default per server**, with a short allow list of named read tools. A name-by-name ask list went stale in three weeks (`hf_sandbox_fs`, `hf_fs_write`, generated Space tools). Wildcard rule syntax for MCP tools was not re-checked today (U).
- **Upgrade path:** existing installations already have both servers in `.mcp.json`. The upgrade must not delete user configuration; it should report the entries and offer removal.

## Q2. Official skills and plugins for ML work (November 2026)

All are Agent Skills (SKILL.md) trees unless noted. "Executes" lists what a skill makes the agent run, as stated by the source.

| Source | Version / HEAD | License | What it does | Executes | Pin | Take | Status, checked, source |
|---|---|---|---|---|---|---|---|
| huggingface/skills | HEAD 25910b3 (2026-10-29, synced from huggingface_hub v2.4.0); 25 skills | not re-checked | `hf-cli`, six `hf-cloud-*`, `trl-training`, `huggingface-llm-trainer`, `-vision-trainer`, `-papers`, `-trackio`, `-datasets`, `-community-evals`, `-local-models`, others | `hf` CLI, HF Jobs (paid compute), uploads | commit SHA; client marketplaces expose only `hf-cli`, the rest via `hf skills add <name>` | Optional per-skill for HF/TRL projects. Idea: the papers skill documents keyless HF Papers endpoints. Correct plugin id is `hf-cli@huggingface-skills`. The standalone `hf` installer adds the CLI skill globally unless `--exclude-skill`. | V, 11-10, https://github.com/huggingface/skills , https://huggingface.co/docs/hub/agents-cli |
| anthropics/skills | HEAD 2c5958e (2026-11-06); 19 skills | mixed, not re-checked | No ML-training skill. `skill-creator` (create, eval and benchmark skills), `mcp-builder` | local scripts | commit SHA | `skill-creator` as a development-time tool to test the kit's own skill | V (list), I (eval features, from the installed skill's description), 11-10, https://github.com/anthropics/skills |
| openai/skills, openai/plugins | pushed 2026-10-28 and 2026-11-06 | not checked | Codex skills catalog and plugins directory. No ML-training skill; has `jupyter-notebook`, `nvidia`, `plugin-eval` | `plugin-eval benchmark` runs real `codex exec` sessions in isolated temp workspaces | commit SHA | `plugin-eval` as the Codex-side efficacy and token-budget check for the port | V, 11-11, https://github.com/openai/skills , https://github.com/openai/plugins/tree/main/plugins/plugin-eval |
| NVIDIA/skills | HEAD 47d179c (2026-11-10); about 425 skills (count from 23 Oct note) | per skill card | NVIDIA product skills (NeMo, CUDA-X, Blueprints). "NVIDIA-verified": cataloged, scanned, evaluated, signed, documented | product CLIs and APIs | `npx skills add nvidia/skills --skill <name> --agent claude-code\|codex\|cursor\|kiro-cli`, needs skills CLI ≥ 1.5.16; detached `skill.oms.sig` verifiable with `model_signing verify certificate` | Content: situational only (NeMo, Megatron). Idea worth taking: the release gate (scan, with/without-skill benchmark published as `BENCHMARK.md`, skill card, detached signature over the whole directory). "Signing does not prove a skill is safe." | V, 11-11, https://docs.nvidia.com/skills , https://docs.nvidia.com/skills/signing-agent-skills , https://docs.nvidia.com/skills/agent-skill-trust-pipeline , https://developer.nvidia.com/blog/nvidia-verified-agent-skills-provide-capability-governance-for-ai-agents/ (2026-05-19) |
| wandb/skills | HEAD 10aac21 (2026-11-06); 5 skills, all marked experimental | Apache-2.0 (SPDX header in SKILL.md) | `wandb-primary`, `wandb-eval-tables`, `wandb-autoresearch`, `weave-instrument`, `agentlens-tracing-instrument` | W&B API with `WANDB_API_KEY`; `wandb-autoresearch` runs training through W&B Launch queues with `uv` | commit SHA; `npx skills add wandb/skills` | Only if the project uses W&B. Ideas: (1) in-repo Skill Bench, reported pass rates Claude Code 31/34 and Codex 25/34 for the same skills; (2) `wandb-autoresearch` confirms queue, metric direction, search axis and budget before the first real launch, keeps a state file, re-runs a likely winner with another seed. It names no frozen evaluator, keep rule or stop condition. | V, 11-11, https://github.com/wandb/skills , https://github.com/wandb/skills/blob/main/skills/wandb-autoresearch/SKILL.md |
| mlflow/skills | HEAD 6303169 (2026-11-04); 10 skills; MLflow ≥ 3.8 | Apache-2.0 | Mostly GenAI tracing and evaluation; onboarding and docs lookup. No classic training skill. Optional `UserPromptSubmit` hook that suggests a skill | `python3` hook from user settings; MLflow CLI | commit SHA; `npx skills add mlflow/skills` or manual copy | Nothing for training. Do not install the prompt hook next to the kit's hooks without a conflict check. | V, 11-11, https://github.com/mlflow/skills |
| Orchestra AI-Research-SKILLs | v1.7.2 (2026-06-16), no commits since | not re-checked | Broad framework know-how (Megatron, DeepSpeed, vLLM and others) | varies | tag v1.7.2 | Hold: about five months without updates in a fast-moving area | V, 11-10, GitHub API (repo named in stack.md) |
| K-Dense scientific-agent-skills | v2.72.0 (2026-10-01), unchanged | not re-checked | Broad science skills | varies | tag | Nothing for training runs | V (version), 11-10, GitHub API |
| Lightning-AI/skills | v1.2.0 (2026-10-14), unchanged | not re-checked | Lightning platform and framework skills | Lightning CLI | tag | Assess only for Lightning projects | V (version), 11-10, https://github.com/Lightning-AI/skills |
| SkyPilot plugin | plugin 1.0.0 in repo HEAD b53ef2b; SkyPilot v0.14.2 (2026-10-28) | Apache-2.0 | One skill for launching VMs, Kubernetes pods and Slurm jobs on 25+ clouds | `sky` CLI, creates billable resources | `claude plugin marketplace add skypilot-org/skypilot` at a commit; plugin source is `./agent` | Optional, for the remote-GPU module; needs spend caps outside the skill | V, 11-11, https://github.com/skypilot-org/skypilot/blob/master/.claude-plugin/marketplace.json |
| Optuna | optuna-mcp only (see Q4) | — | No official skill | — | — | Nothing | V, 11-11, GitHub org search |
| Modal | none found in the vendor's GitHub organisation | — | Only examples (sandboxes for agents) | — | — | Nothing | V (search), 11-11, GitHub org search |
| Unsloth | none found | — | — | — | — | Nothing | V (search), 11-11, GitHub org search |
| Official Claude Code marketplace | HEAD dceb15d (2026-11-10); 315 plugins on 23 Oct, count not re-checked | per plugin | ML-relevant entries on 23 Oct: huggingface-skills, context7, mlflow, nvidia-skills, sagemaker-ai, databricks, togetherai-skills, duckdb-skills | per plugin | marketplace commit | Discovery only | V (HEAD), I (entries), 11-11, https://github.com/anthropics/claude-plugins-official |

Community collections and loop skills:

| Item | Facts | Take | Status, checked, source |
|---|---|---|---|
| karpathy/autoresearch | Created 2026-03-06, about 99.7k stars. Agent edits one training file, fixed time budget per run, one metric, keep or revert. | Pattern only (the dominant analog for the unattended loop). Details from general knowledge, not re-read today. | V (repo facts), I (mechanism), 11-11, https://github.com/karpathy/autoresearch |
| Community "autoresearch" skills (Claude Code, Codex, pi variants; 3k–8k stars each) | Descriptions say "repeat forever" or "indefinitely". | Reject as installs. They are exactly the "skill that starts an autonomous loop" that stack.md skips; they have no frozen evaluator or budget enforced by code. | V (descriptions), 11-11, GitHub search |
| Mega-collections (2,955+ skills, 49k stars; 1000+ skills, 37k stars) | Aggregators of third-party skills. | Reject as install sources; discovery only. | V, 11-11, GitHub search |
| huggingface/ml-intern | Archived: "no longer maintained. Continue with HuggingChat." 10.8k stars. | Reject. Signal that a vendor-run ML agent product was dropped. | V, 11-11, https://github.com/huggingface/ml-intern |

Efficacy evidence that applies to every row above:

| Claim | Status | Checked | Source |
|---|---|---|---|
| SkillsBench (7 agent-model configurations, 7,308 trajectories): curated skills +16.2 points average pass rate; self-generated skills −1.3 points. | I (search summary of the abstract) | 11-11 | https://arxiv.org/abs/2602.12670 |
| "One Skill Too Many" (2026-10-08): in 6,368 runs over three models, a similar co-installed skill replaced the intended skill in about one run in five without lowering task completion; when read first, runs lost over a third of the functions only the intended skill provides. | V (abstract) | 11-11 | https://arxiv.org/abs/2610.11647 |
| The same skill set scores 91% on one agent and 74% on another in the vendor's own bench. | V | 11-11 | https://github.com/wandb/skills |
| PostTrainBench (arXiv 2603.08640) is the public yardstick for agents doing LLM post-training; third-party trackers disagree on the current leader. | I | 11-11 | https://arxiv.org/pdf/2603.08640 , https://github.com/aisa-group/posttrainbench |

## Q3. Research-scouting sources usable without extra accounts

| Source | Access and limits | Fit | Status, checked, source |
|---|---|---|---|
| arXiv API | No key. At most one request every three seconds, one connection at a time, counted across all your machines. Metadata is CC0; do not re-serve e-prints. | Core source for the scout module. Stdlib `urllib` plus Atom parsing. | V, 11-10, https://info.arxiv.org/help/api/tou.html |
| Hugging Face Papers | No key for public reads. `GET /api/papers/search?q=&limit=` (hybrid search, limit ≤ 120), `/api/daily_papers?date=&sort=trending`, `/api/papers/{id}`, `/papers/{id}.md`, `/api/models?filter=arxiv:{id}` (linked models). Subject to Hub rate limits (anonymous 500 API requests per 5 minutes per IP). | Second source: adds trending signal and links from paper to code and models. | V (endpoints as documented in the vendor skill), 11-10, https://github.com/huggingface/skills/blob/main/skills/huggingface-papers/SKILL.md , https://huggingface.co/docs/hub/rate-limits |
| Semantic Scholar API | Keyless use shares one pool (1,000 requests/second across all anonymous users) and may be throttled; a key starts at 1 request/second and needs a request form. | Optional citation graph. Must tolerate HTTP 429. | V, 11-10, https://www.semanticscholar.org/product/api |
| OpenAlex | Keys required since 13 Feb 2026; no polite pool. Free key gives $1/day of usage (search $0.001, list $0.0001, single lookup free). Keyless budget is one tenth with no cursor paging. A key needs an account with a verified email. | Not usable "without extra accounts" in practice. | V, 11-10, https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/ , https://help.openalex.org/api/authentication/ |
| Papers with Code | Original site shut down 24–25 July 2025. Revived by Hugging Face at paperswithcode.co in May 2026 with leaderboards and external evals. No documented API found. | Browse through an agent's web tool only. | V (revival), U (API), 11-10 and 11-11, https://huggingface.co/blog/nielsr/paperswithcode-launch , https://paperswithcode.co/ |
| Other successors (CodeSOTA, Wizwand, Hyper.ai, CatalyzeX, OpenCodePapers, ORKG) | Named only in non-primary sources; quality and terms not checked. | Hold. | U, 11-10 |

MCP servers and CLIs for these sources:

| Tool | Facts | Take | Status, checked, source |
|---|---|---|---|
| arxiv-mcp-server (community) | v0.8.2 (2026-10-08), unchanged; 19 tools; downloads papers locally. | Hold. A 60-line stdlib client covers search and abstract fetch without a package. | V, 11-10, https://github.com/blazickjp/arxiv-mcp-server |
| alphaXiv MCP (hosted) | `https://api.alphaxiv.org/mcp/v1`; 21 tools including library and follow mutations; account required (OAuth 2.1 or API key); search and analysis count against a quota. | Hold: account, write tools, another third-party text channel. | V, 11-11, https://alphaxiv.org/docs/mcp |
| Semantic Scholar MCP servers | Only community servers found; no official one. | Reject. | I, 11-11, directory listings |
| `hf` CLI and `huggingface-papers` skill | Vendor-maintained; skill is instructions over the public endpoints above. | Idea source; no install needed. | V, 11-10, same skill file |

Built-in web tools per agent:

| Agent | Built-in web capability | Controls | Status, checked, source |
|---|---|---|---|
| Claude Code (v2.1.322, 2026-11-10) | `WebSearch` and `WebFetch` tools (WebSearch is US-only in this session's tool description). | Permission rules `WebFetch(domain:example.com)`; bare `WebSearch` rule only; a deny rule removes the tool. Hosted search and fetch run on the vendor's servers, not in the sandbox. | V (tools observed in this session), I (rule syntax, search summary), 11-11, https://code.claude.com/docs/en/tools-reference , https://code.claude.com/docs/en/permissions |
| Codex CLI | Hosted `web_search`: `disabled`, `cached` (default), `indexed`, `live`; `--search` for live; defaults to live under full access. | `tools.web_search.allowed_domains`; independent of sandbox networking. | V, 11-10, https://learn.chatgpt.com/docs/web-search |
| Cursor (editor and `agent` CLI) | Web search and fetch tools in both. | `autoAcceptWebSearch` in `cli-config.json` is off by default; Auto-review mode covers Shell, MCP and Fetch. | V, 11-10, https://cursor.com/docs/cli/changelog , https://cursor.com/docs/agent/overview , https://cursor.com/docs/cli/reference/parameters |

Design reading: a scout step can be (a) a stdlib script the harness runs under its own rate limiter and budget, writing a dated,
source-tagged notes file, or (b) instructions to use the agent's web tools. Option (a) is identical on all three agents and is
testable offline with recorded responses; option (b) differs per agent and per permission mode. Either way the output is data.

## Q4. `stack.md` re-check (23 Oct 2026 tables)

Core rows:

| Row | Then | Now | Status, checked, source |
|---|---|---|---|
| uv | 0.13.x | 0.13.7 (2026-11-03). Claim holds. | V, 11-11, https://github.com/astral-sh/uv/releases |
| PyTorch | 2.14.x; 2.15 GA planned 28 Oct | 2.15.0 released 2026-10-28. Row needs a decision (stay on 2.14.1 or move). Python ≥ 3.11 claim not re-checked. | V (release), U (Python floor), 11-11, https://github.com/pytorch/pytorch/releases |
| Optuna | 5.0.0 (7 Sep 2026) | Still latest. | V, 11-11, https://github.com/optuna/optuna/releases |
| Trackio | default tracker when none exists | 0.45.0 (2026-11-02; 0.43.0 on 10-20); Python ≥ 3.10; about 308k downloads/month. `trackio skills add --claude` confirmed (also `--codex`, `--cursor`, `--opencode`, `--pi`). New "Logbooks" feature (see below). The earlier note's "tag v0.5.0" was wrong. | V, 11-10 and 11-11, https://pypi.org/project/trackio/ , https://huggingface.co/docs/trackio/logbooks |
| Docs MCP, Hub MCP | default | Become optional (Q1). | — |

Situational rows:

| Row | Re-check | Disposition | Status, checked, source |
|---|---|---|---|
| Tracker MCP: Trackio | Commands confirmed: `pip install "trackio[mcp]"`, `trackio show --mcp-server`, `http://127.0.0.1:7860/mcp/` (streamable HTTP); `mcp` extra needs `mcp>=1.30.0,<3`. Not in stack.md: 12 read tools plus 3 mutation tools (`delete_run`, `rename_run`, `trigger_sync`) gated by a write token that is printed in the terminal at startup. An agent that started the dashboard can read that token. | Keep situational; add deny rules for the three mutation tools. | V, 11-11, https://huggingface.co/docs/trackio/api_mcp_server |
| Tracker MCP: W&B | Official server is the GitHub repo, tags v0.4.4 (HEAD 7a1f9f6, 2026-11-06) and v0.4.3. Read-only mode (`WANDB_MCP_ACCESS_MODE=read-only`) removes report creation, logging and messaging tools; tool profiles; bounded responses; release attestation. The PyPI name `wandb-mcp-server` (0.0.1, uploaded 29 Jun 2026 by an unrelated account) is a quarantined empty placeholder. Hosted URL not re-checked. | Keep situational; install only from the vendor repo at a tag; say so explicitly. | V, U (hosted URL), 11-10, https://github.com/wandb/wandb-mcp-server , https://pypi.org/project/wandb-mcp-server/ |
| Tracker MCP: MLflow | Needs MLflow ≥ 3.5.1 (current 3.19.0). Official docs list trace tools only; a vendor cookbook shows `MLFLOW_MCP_TOOLS=genai` exposing 26 tools including `create_experiment` and `create_run`. The value `ml` used in stack.md was not found in the docs. | Mark experimental and unconfirmed. | I, U (`ml` value), 11-11, https://mlflow.org/docs/latest/genai/mcp/ , https://mlflow.org/cookbook/mlflow-mcp-server |
| optuna-mcp | Still v0.2.0, published 2025-11-10 (earlier note said 10-30): no release in a year. Python ≥ 3.12; depends on torch ≥ 2.7.0, kaleido 0.2.1, pandas, plotly, optuna ≥ 4.2.1; 207 downloads last month. Optuna 5 compatibility untested. | Demote to Hold. The Optuna CLI and dashboard against the same SQLite file do the job. | V, U (Optuna 5), 11-10, https://pypi.org/project/optuna-mcp/ |
| Hugging Face skills | "HF Jobs need a paid plan" is wrong: credits only. Correct plugin id `hf-cli@huggingface-skills`. Standalone `hf` installer adds a global skill by default. | Keep situational; fix the text. | V, 11-10, https://huggingface.co/docs/hub/en/jobs-pricing , https://huggingface.co/docs/hub/agents-cli |
| Orchestra AI-Research-SKILLs | Still v1.7.2 (June 2026). | Hold. | V, 11-10 |
| NVIDIA skills | Command confirmed; needs skills CLI ≥ 1.5.16 (CLI is at v1.8.0, 2026-11-10); skills are signed and carry skill cards. | Keep situational. | V, 11-11, https://github.com/NVIDIA/skills , https://github.com/vercel-labs/skills/releases |
| SkyPilot plugin | Commands and version 1.0.0 confirmed. | Keep; belongs to the remote-GPU module. | V, 11-11 |
| RunPod MCP | `@runpod/mcp-server` 4.10.1 (2026-11-06); it was 4.5.0 on 10-20. Fast-moving; creates billable resources. | Keep situational with an exact version pin and ask rules. | V, 11-10, npm registry |
| Jupyter MCP (Datalayer) | v2.2.5 (2026-11-05). | Keep. | V, 11-10 |
| DeepWiki MCP | Gave a stale answer about a fast-moving repository in this session; the hosted server now also carries account-bound agent-management tools in a private mode. | Keep situational with a staleness warning. | V (observed), 11-10 |
| arXiv MCP | v0.8.2 unchanged. | Replace with the stdlib scout (Q3). | V, 11-10 |
| DuckDB/MotherDuck MCP | v1.1.0 (2026-10-07) unchanged. | Keep. | V, 11-10 |
| Ray Tune with `OptunaSearch` | Not re-checked; compatibility with Optuna 5 unknown. | Keep, flagged. | U, 11-11 |
| Anthropic `skill-creator` | Present at HEAD 2c5958e. | Keep; also useful to benchmark the kit's own skill. | V, 11-10 |
| Claude Science (beta) | Public beta since 30 June 2026; runs jobs on local kernels, Slurm over SSH or Modal; sources conflict on Windows support. Still no NN-training-specific feature found. | Keep as a note. | I, 11-11, https://claude.com/product/claude-science |

Skip rows:

| Row | Re-check | Status, checked, source |
|---|---|---|
| Harness² | arXiv 2610.14224, submitted 9 Oct 2026. Abstract: evaluated on WorkBuddy-Bench, JobBench and LAB with GLM-5 and Gemini 3.5 Flash. The "Google", "OpenCode/Codex executors" and "needs Vertex AI" details in stack.md are not in the abstract. Still not an ML-training tool: Skip stands. | V (abstract), U (those three details), 11-11, https://arxiv.org/abs/2610.14224 |
| Layering AI-scientist / MLE frameworks | The study is "How Much of a Harness Does a Strong Agent Need for Autonomous ML Engineering?" (arXiv 2609.40303; EPFL authors, one at Apple during the work). Verified: with equal time and the same model, state-of-the-art open harnesses gave no advantage over one session of a minimal read/write/bash agent. The multi-agent numbers (55.7% to 33.3%) come from secondary summaries only. Skip stands; the archived vendor ML agent supports it. | V (headline), U (multi-agent numbers), 11-11, https://machinelearning.apple.com/research/harness-autonomous-ml-engineering |
| torchtune | README notes the wind-down (commit bd2a0fc, 2026-04-23); repo is not archived and nightly builds continue. "No longer maintained" is close enough: Skip stands. | V, 11-11, https://github.com/meta-pytorch/torchtune |
| GPU-monitoring MCP servers; more than one tracker or sweep controller; agent teams | Not re-checked. No new evidence against the Skip. | I, 11-11 |
| All-in-one skill installers that start autonomous loops | Skip stands and is strengthened (skills.sh campaign; "repeat forever" skills). | V, 11-11 |

Security section of stack.md:

- `uvx mcp-scan --skills` is out of date. The tool is now `snyk-agent-scan` 0.6.11 (2026-11-06, Apache-2.0, Python ≥ 3.10). It requires `SNYK_TOKEN`, sends tool descriptions and skill content to the vendor's API, and starts configured stdio servers to read their tool lists (per-server consent when interactive). V, 11-11, https://pypi.org/project/snyk-agent-scan/
- "Pin versions or commits" is necessary but was not sufficient before Claude Code 2.1.179 and Codex 0.146.0 (Q5). Add minimum client versions.

New since the table was written: Trackio Logbooks (`trackio logbook open`, `trackio logbook run -- <cmd>` records the exact command,
detected scripts and configs, output, exit code, duration and output artifacts; `trackio logbook read --json`; `attach trace`
attaches the agent transcript with default secret scrubbing; `publish` creates a static Space). It overlaps the kit's journal and
controller. Stored in `.trackio/logbook`. Publishing traces is a privacy risk the vendor itself flags. V, 11-11,
https://huggingface.co/docs/trackio/logbooks

## Q5. Distribution and security

How such kits are distributed today:

| Channel | Facts | Status, checked, source |
|---|---|---|
| Claude Code plugin marketplace | A repo with `.claude-plugin/marketplace.json` (`name`, `owner`, `plugins[]`). Plugin `source` can be a relative path, `github`, `git-subdir`, `url`, `archive` (zip over HTTPS), `npm` or `command`. Git-based sources can be pinned to a `ref` or `sha`. `claude plugin validate <dir>`, `claude plugin marketplace add <owner>/<repo>`, `claude plugin install <name>@<marketplace>` (default scope: user). A plugin can also be shared as a directory or zip, or loaded with `--plugin-dir`. Plugins can ship hooks and MCP server configuration. | V, 11-11, https://code.claude.com/docs/en/plugin-marketplaces |
| Codex plugins | Plugins bundle skills, MCP servers, browser extensions and hooks; `/plugins` browser groups by marketplace; "Review and trust plugin hooks before they run." CLI reference lists `codex plugin marketplace add` with `--ref` and `codex plugin marketplace upgrade`. Auto-update default not stated in the docs read. | V (contents), I (CLI flags), 11-11, https://learn.chatgpt.com/docs/plugins , https://developers.openai.com/codex/cli/reference |
| Cursor plugins | `.cursor-plugin/plugin.json` manifest; components: rules, skills, agents, commands, hooks (`hooks/hooks.json`), `mcp.json`; multi-plugin repos use `.cursor-plugin/marketplace.json`; local testing in `~/.cursor/plugins/local`; team marketplaces with "Default On" and "Required" modes; public listing needs review. | I (search summary of the docs), 11-11, https://cursor.com/docs/plugins , https://cursor.com/docs/reference/plugins |
| `npx skills` (open skills CLI) and skills.sh | v1.8.0 (2026-11-10). Installs from GitHub, GitLab, any git URL or a local path; `owner/repo#ref` records a ref, but refs are optional. Project lock `skills-lock.json` stores a SHA-256 of installed files; as of 1.7.4 restore did not refuse a hash mismatch (a frozen-lockfile option landed later). Anonymous telemetry by default (`DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1`, which also disables audit lookups). Shows Gen, Socket and Snyk audit results before install since 1.4.0; audits are advisory. | V (version, audits), I (lock details, secondary guide), 11-11, https://github.com/vercel-labs/skills , https://vercel.com/changelog/automated-security-audits-now-available-for-skills-sh , https://github.com/vercel-labs/skills/issues/500 |
| `gh skill` (GitHub CLI ≥ 2.90.0, public preview since 2026-04-16) | `gh skill install OWNER/REPO SKILL[@tag\|sha] --agent claude-code\|codex\|cursor --scope project\|user --pin <tag\|sha>`; `gh skill preview`; writes repository, ref and tree SHA into SKILL.md frontmatter; `gh skill publish` can enable immutable releases. Several agents share `.agents/skills` at project scope. "Not verified by GitHub." | V, 11-11, https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/ , https://cli.github.com/manual/gh_skill_install |
| Vendor CLIs that install their own skill | `hf skills add`, `trackio skills add --claude\|--codex\|--cursor`, `npx ctx7 setup`. Some install globally by default. | V, 11-10 and 11-11, sources in Q1, Q2, Q4 |
| Signed skills | NVIDIA signs each skill directory with a detached OpenSSF Model Signing bundle; verification needs `pip install model-signing` and the vendor root certificate. | V, 11-11, https://docs.nvidia.com/skills/signing-agent-skills |
| Plain installer (this kit) | Copy files plus settings merge; no network. Still the only channel that works offline on all three agents. | V (local read), 11-10 |

Incidents and research, 2025–2026:

| Event | Facts | Status, checked, source |
|---|---|---|
| Plugin4Shell (AIR; found May, reported to vendors June, public 17–18 Sep 2026) | Plugin installers passed a pinned commit SHA to Git but did not verify the checked-out commit, so a repository owner could serve other code under the pinned SHA (for example through a branch named like the SHA). Affected Claude Code, Codex, GitHub Copilot and Gemini CLI. Fixed in Claude Code 2.1.179 and Codex 0.146.0; Copilot had no fixed release when reported; Gemini CLI will not be fixed. No CVE listed. Plugin auto-update made it zero-click. | I (reputable press and a CSA note; the researchers' own post was not read), 11-11, https://www.csoonline.com/article/4223909/a-zero-click-rce-flaw-in-ai-coding-agents-could-have-exposed-enterprise-systems-2.html |
| skills.sh typosquat campaign (Zenity Labs, 2026-08-06) | Skills impersonating two popular projects were listed with benign content on 5 July, got a malicious loader in the repo on 6 July and weaponised setup documents on 11 July; related malicious PyPI packages followed. Agents were told to install from the attacker's checkout and run a remote script that harvested credentials. Over 1.7M displayed installs (not unique users). Removed 2 Aug after outreach. The report does not say whether registry audits flagged them. | V, 11-11, https://labs.zenity.io/post/attackers-target-agents-via-the-skill-supply-chain |
| ContextCrush (Q1) | Registry-delivered instructions through a docs MCP server. | V, 11-10 |
| PyPI name squat on a tracker vendor's MCP server name | Quarantined placeholder under the name an agent would guess. | V, 11-10, https://pypi.org/project/wandb-mcp-server/ |
| ToxicSkills (Snyk, 5 Feb 2026) | 3,984 skills scanned, 13.4% with critical issues, 76 confirmed malicious. Figures from the 23 Oct note; page not re-read. | I, 11-11, https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/ |
| Ecosystem studies | 238,180 skills across three marketplaces and GitHub: flagged-malicious share ranges from 6.0% to 46.8% by platform and scanner; 121 skills pointed at hijackable abandoned repositories (arXiv 2603.16572). skills.sh grew about 18.5x in 20 days, about 30% of skills carry state-changing operations (arXiv 2602.08004). | I (search summaries of abstracts), 11-11, https://arxiv.org/abs/2603.16572 , https://arxiv.org/abs/2602.08004 |
| Attack papers | StealthyPoison (arXiv 2611.12155, 2026-11-09): procedural poisoning of third-party skills, tested on 566 target skills against 26,000+ registry entries. PoisonedSkills (arXiv 2604.03081): camouflaged payloads in skill documents reached up to 33.5% direct execution. BadSkill (arXiv 2604.09378): backdoored model bundled in a skill. | V (2611.12155 abstract), I (others), 11-11, https://arxiv.org/abs/2611.12155 , https://arxiv.org/abs/2604.03081 , https://arxiv.org/abs/2604.09378 |
| Approval laundering (arXiv 2609.28586, 2026-09-23) | Effects of an approved invocation extend beyond what the approval showed; adding command semantics and decision-time metadata reduced unexplained residual effects from 40 to 13 across 111 cases. | V (abstract), 11-11, https://arxiv.org/abs/2609.28586 |
| Earlier incidents in the 23 Oct note (project-file CVEs in Claude Code, a compromised mail MCP package, a remote-MCP proxy CVE, a registry breach) | Not re-verified today. | I, 11-11 |

What a careful installer should do (derived from the above):

1. Default install touches no network and adds no MCP server, plugin or third-party skill. Optional modules are named, off, and each lists what it contacts, what account it needs and what it can spend.
2. Vendor, do not fetch at run time: any third-party text the kit ships is copied into the release at a recorded commit, with license and source URL. The installer never runs `npx`, `uvx` or `pip` on the user's behalf.
3. Ship a SHA-256 manifest of the kit's own files and a `verify` command (stdlib `hashlib`). Print what will be written, which hooks will run and which settings change before writing; support a dry run.
4. When documentation tells the user to add a third-party tool, give the exact source (repository URL and tag or commit, or registry name and exact version), never a bare package name and never `@latest`.
5. Check client versions and refuse plugin-based installation below Claude Code 2.1.179 or Codex 0.146.0; recommend turning plugin auto-update off for third-party marketplaces.
6. Permission template: ask or deny by default for every MCP server the kit configures, allow only named read tools, and in unattended mode load only an explicit MCP configuration (strict mode), empty unless the user lists servers.
7. Least privilege for tokens: read-only fine-grained Hub token, tracker read-only mode, restricted cloud key; tokens only in the environment.
8. Detect overlap: warn when other skills covering training, tracking or autonomous loops are installed next to the kit's skill, and when another tool has registered prompt or tool hooks.
9. Record provenance of every optional module that was enabled (name, version, source, date, hash) in a file the upgrade reads, so an upgrade can re-verify and never silently change sources.
10. Treat scanners as optional helpers, not gates: the main one needs an account, uploads skill content and starts stdio servers.

## Changed since 23 October or wrong in the earlier notes

1. PyTorch 2.15.0 shipped on 2026-10-28 (stack.md: "planned"). uv is at 0.13.7. Claude Code is at v2.1.322.
2. "HF Jobs need a paid plan and a write token" is wrong: any account with a positive credit balance can run Jobs (true since at least May 2026).
3. The kit's ask rules for the Hub MCP server miss `hf_sandbox_fs` and the write tool `hf_fs_write`; the server's own settings only hide tools.
4. Hub MCP server moved 0.4.31 to 0.4.34 with new capability each release (Space hardware in `create_repo`, skills over MCP).
5. Context7: the note said "git tags stop at v1.0.30"; releases are package-scoped tags and current is 4.6.0 with CLI 0.11.0. The ContextCrush incident, its CVE and the vendor's 22 Oct write-up are not in the earlier note.
6. Trackio: "tag v0.5.0" was wrong; current is 0.45.0. Logbooks are new. The MCP server exposes mutation tools.
7. optuna-mcp v0.2.0 was published 2025-11-10, not 2025-10-30, and has had no release since.
8. wandb-mcp-server now has git tags (v0.4.3, v0.4.4); the earlier note said none. The PyPI name is a squat.
9. `uvx mcp-scan --skills` no longer matches the tool (renamed, account required, uploads content).
10. Missed incidents: Plugin4Shell (September 2026) and the skills.sh typosquat campaign (August 2026).
11. huggingface/skills HEAD moved to 2026-10-29; the correct plugin id is `hf-cli@huggingface-skills`.
12. mlflow/skills lists 10 skills (the note said 13). wandb/skills gained an in-repo skill bench and an autoresearch skill.
13. RunPod MCP 4.5.0 to 4.10.1 and Jupyter MCP 2.2.4 to 2.2.5 in three weeks.
14. Harness²: affiliation, executors and cloud dependency stated in stack.md are not supported by the abstract.
15. The Apple/EPFL result has a primary page and arXiv ID (2609.40303); its multi-agent numbers are still secondary-only.
16. alphaXiv's hosted MCP has 21 tools and needs an account; OpenAlex has needed a key since February 2026 (check whether any earlier note assumed keyless use).
17. Hugging Face archived its ML agent repository.

## Concerns any design must handle

- SEC-PROMPT-INJECTION: fetched docs, papers, skill text and tool output can carry instructions
- SEC-REGISTRY-DELIVERED-INSTRUCTIONS: trusted delivery channel serving third-party text verbatim
- SEC-TOOL-VISIBILITY-NOT-AUTHZ: hiding a tool in server settings does not block calls to it
- SEC-PACKAGE-NAME-SQUAT: guessed package names resolve to the wrong publisher
- SEC-UNPINNED-REMOTE-CODE: run-time fetch of latest code through package runners
- SEC-PIN-NOT-VERIFIED-BY-CLIENT: old client versions did not check the pinned commit
- SEC-BENIGN-THEN-MALICIOUS-UPDATE: content changes after trust was established
- SEC-HEADLESS-MCP-AUTOLOAD: project MCP servers load without a prompt in non-interactive runs
- SEC-TOKEN-OVERSCOPE: one broad token enables spend, writes and deletion
- SEC-SCANNER-DATA-EGRESS: security scanners upload skill content and start servers
- SEC-TRANSCRIPT-PUBLISH-LEAK: publishing run logbooks or agent traces exposes paths, prompts and secrets
- PERM-RULE-COVERAGE-GAP: name-by-name tool rules go stale when a server adds tools
- PERM-APPROVAL-SCOPE-DRIFT: an approved call has effects beyond what the approval showed
- COST-UNBOUNDED-REMOTE-SPEND: credit-funded jobs and cloud resources reachable from tool calls
- COST-FREE-TIER-EXHAUSTION: docs or search quota runs out mid-run
- NET-DEFAULT-OFFLINE-VIOLATION: default install must not add network services
- SCOUT-RATE-LIMIT-COMPLIANCE: source terms cap request rate and connections
- SCOUT-SOURCE-ACCOUNT-REQUIRED: sources that need a key or verified email
- SCOUT-STALE-OR-WRONG-SOURCE: stale wiki answers and unverified state-of-the-art claims
- SCOUT-OUTPUT-IS-DATA: scouting results must never trigger actions without a harness-checked experiment
- SKILL-STALENESS: third-party skills unmaintained for months
- SKILL-CONFLICT-COINSTALLED: similar skills displace the intended one
- SKILL-GLOBAL-INSTALL-SIDE-EFFECT: vendor installers write user-level skills
- SKILL-EFFICACY-UNMEASURED: benefit differs by agent and self-written skills do not help
- CTX-TOOL-SCHEMA-OVERHEAD: tool definitions consume context before any work
- VALID-TRACKER-MUTATION: tracker tools can delete, rename or re-sync runs
- VALID-EVALUATOR-NOT-FROZEN: borrowed loop skills name no protected evaluator or keep rule
- PORT-AGENT-WEB-TOOL-DIFFERENCES: web search and fetch defaults differ per agent
- PORT-PLUGIN-FORMAT-DIVERGENCE: three plugin manifest formats and install scopes
- PORT-HOOK-COLLISION: other tools register prompt or tool hooks next to the kit's
- UPGRADE-EXISTING-MCP-CONFIG: changing the default must not delete entries users already have
- DOC-VERSION-DRIFT: a dated stack table is wrong within weeks

## Open questions

1. What is Context7's keyless quota, and what does the agent see when the quota runs out mid-session?
2. Under which account settings is `hf_fs_write` advertised, and which Hub MCP tool serves paper search now?
3. Does each agent accept a wildcard rule for all tools of one MCP server, and how does an ask rule behave in each unattended mode?
4. Does paperswithcode.co expose an API or a machine-readable view?
5. Do optuna-mcp 0.2.0 and Ray Tune's `OptunaSearch` work with Optuna 5?
6. Are Codex and Cursor plugin installs pinned to a commit, and is auto-update on by default in each?
7. Which `MLFLOW_MCP_TOOLS` values exist, and which expose write tools?
8. Did the skills.sh audits flag the August campaign before removal?
9. Is Claude Science available on Windows?
10. How large is the per-agent difference for the kit's own skill, measured with and without it on a fixed small task?

## Redirect attempts

No fetched page, repository file or skill file tried to change this task. Instruction-like text that was seen and not acted on:

1. A search-service rate-limit error told the client to create an account and API key. Not done; switched to another search tool.
2. A scholarly index's help pages invite coding agents to request an API key with the user's email address. Not done.
3. The Hub MCP server README has a line addressed to "security researchers and bots". Informational; ignored.
4. A tracker's documentation contains a block of instructions meant to be pasted to a coding agent (install its skill, open a logbook, wrap every command). Read as documentation only.
5. A vendor docs page opens with a line telling readers to fetch its documentation index first. Ignored.
6. A vendor skill file (bounded research loop) contains agent directives. Summarised as data; not followed.
