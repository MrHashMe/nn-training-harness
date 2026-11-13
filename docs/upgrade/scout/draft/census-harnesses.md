# Census: projects that let a coding agent train or fine-tune models

Date: 2026-11-12. Method: web searches (standard mode, about 12) to find what exists in 2026, then primary-source reads of GitHub pages, raw skill files and docs (about 30 reads, via WebFetch and the GitHub API for commit and release dates). Star counts come from GitHub pages as fetched today. "Not opened" marks anything I only saw in a search snippet or an aggregator. Nothing was installed or run. No instruction in any fetched page was followed.

## The six strongest, by evidence

| # | Project | URL | Version or commit (date) | License | Last activity seen |
|---|---|---|---|---|---|
| 1 | Hugging Face skills (llm-trainer, trl-training, trackio, hf-cli, jobs and 20 more; 11.3k stars) | https://github.com/huggingface/skills | commit 25910b3 (2026-10-29); no releases | Apache-2.0 | 2026-10-29, bot sync of the HF CLI skill; human commits not checked |
| 2 | Unsloth and Unsloth Studio (79.3k stars) | https://github.com/unslothai/unsloth | v0.1.917-beta (2026-11-11), commit 2d3deb5 (2026-11-11) | Apache-2.0 core, AGPL-3.0 for Studio UI | 2026-11-11 |
| 3 | Karpathy autoresearch (99.8k stars) | https://github.com/karpathy/autoresearch | commit 228791f (2026-03-26) | MIT | 2026-03-26, nothing after in 7.5 months |
| 4 | Weights & Biases skills (75 stars; Skill Bench) | https://github.com/wandb/skills | commit 10aac21 (2026-11-06) | Apache-2.0 (CoreWeave SPDX headers) | 2026-11-06 |
| 5 | SkyPilot agent skill (inside the SkyPilot repo) | https://github.com/skypilot-org/skypilot , docs https://docs.skypilot.ai/en/latest/getting-started/skill.html | master commit f6df9e5 (2026-11-11) | Apache-2.0 (not opened) | 2026-11-11 |
| 6 | uditgoenka/autoresearch (6.8k stars, 14 commands) | https://github.com/uditgoenka/autoresearch | v2.3.0, commit 7bddd05 (2026-10-31) | MIT | 2026-10-31 |

Why these: vendor backing (Hugging Face, Unsloth, CoreWeave/W&B, SkyPilot), adoption (stars), maintenance (commits within two weeks, except Karpathy's), and published numbers (W&B Skill Bench, SkyPilot's 8-hour run, Unsloth vendor claims). Karpathy's repo is included for adoption and because most other loops copy it, though it is stale.

## Capability matrix

Abbreviations: HF = Hugging Face skills; Uns = Unsloth/Studio; AR = Karpathy autoresearch; W&B = wandb/skills; SP = SkyPilot skill; UG = uditgoenka/autoresearch. "?" in the harness column = the brief does not say. "n.d." = I could not determine from what I opened.

| # | Capability | Harness | HF | Uns | AR | W&B | SP | UG |
|---|---|---|---|---|---|---|---|---|
| 1 | Install, agents | Own installer: Claude Code, Codex, Cursor (block, skill, hooks, subagents, MCP) | Plugin marketplace, `hf skills add`, AGENTS.md fallback; Claude Code, Codex, Gemini CLI, Cursor | Desktop app, scripts, Docker, pip; `unsloth start <agent>` points Claude Code, Codex, OpenCode, Hermes etc. at a local Unsloth model (agent uses Unsloth, not the reverse) | A repo plus `program.md`; any agent | `npx skills add wandb/skills`; Claude Code and Codex named | Claude Code plugin marketplace, `npx skills add`, INSTALL.md; Claude Code, Codex "etc." | `npx skills add`, plugin, install.sh; Claude Code, OpenCode, Codex, pi, Muse |
| 2 | What it automates | Launch, monitor, evaluate, final test; data prep and script writing left to the agent (?) | Writes TRL/Unsloth script from templates, estimates cost, submits to HF Jobs, Trackio, Hub push, GGUF | Training UI, data recipes (PDF/CSV to dataset), export, local inference | Edit `train.py`, train 5 min, keep or revert | Tracked runs, Launch queue, trial comparison, resumable state; no model publishing | Cluster launch, job fan-out, cleanup; no training logic | Generic modify-verify loop on any measurable goal |
| 3 | Local run lifecycle | Yes: detached start, status, watch, curve, stop, resume | Partly: a macOS local-training reference; jobs run remote | Partly: Studio runs training locally with live loss/GPU view, history; agent-level stop/resume n.d. | Partly: foreground `uv run train.py`, fixed 5 min | No (remote Launch) | No (remote, managed jobs) | No: agent runs the verify command |
| 4 | Remote compute, cost control | Yes: SSH, HF Jobs, spending cap, resume after preemption | HF Jobs; `estimate_cost.py`; timeout advice ("default 30 min too short"); no cap found | Colab notebooks; no cost control (local) | None (one GPU) | W&B Launch queues; agree compute budget before first non-smoke launch, serial trials (prompt-level) | Multi-cloud, spot recovery, autostop and `--down` by prompt; docs page lists no cost guard; example capped clusters in the prompt | None; iteration cap 25 by default |
| 5 | Tracking the agent can read | Own metrics file, journal, curve (?) | Trackio mandatory in every script; trackio skill | Studio dashboard (loss, grad norm, GPU) for humans; agent access n.d. | `results.tsv` | Strong: runs, artifacts, Weave, reports via skill and hosted MCP (MCP not opened) | `results.tsv` in the example only | TSV/JSONL log |
| 6 | Hyperparameter search | Optuna as optional module (?) | No | No (page describes none) | Agent hill-climbs | Launch-queue serial search; Sweeps reference exists (not opened) | Agent-driven grid across clusters (example) | Agent-driven |
| 7 | Held-out data and evaluator protection | Yes: guard hook denies reading sealed test data, editing frozen evaluator/data | No (not described) | No | Instruction only: `prepare.py` "do not modify" (no hook seen) | No | No | Partly: guard command must keep passing; guard and test files "never modified" (instruction); hooks block `.env`, force-push, `rm -rf` |
| 8 | Statistical care | Yes: seed panels, noise margin, fresh-seed confirmation | No | No | No | Partly: prompt says rerun the winner with another seed when gap is within noise | No | Partly: Mann-Whitney U, 7 samples, noise band, only in the `regression` subcommand |
| 9 | Unattended loop, who decides | Opt-in, limits set by the user, harness runs the frozen evaluator and decides keep/revert | Not a loop | Not a loop | Agent decides via git; runs until stopped | Serial trials, agent decides, user-agreed budget | Agent decides; example says never pause until stopped | Mechanical keep/revert on the metric; bounded 25 iterations default; fork-and-flush on plateau |
| 10 | LM fine-tuning recipes | Names PEFT, TRL, Unsloth as optional modules | SFT, DPO, GRPO, reward modeling; Unsloth reference; chat-format rules per method; GGUF conversion; VLM trainer; eval skill | LoRA, QLoRA, full, FP8, GRPO, DPO; GGUF and safetensors export | Pretraining only | `LLM finetuning & RL analysis` benchmark category; no recipes | None | None |
| 11 | Guard rails for costly or destructive actions | Yes: guard hook asks before destructive commands, protects live runs, spending cap | Prompt advice (timeout, Hub push); no hook seen | Sandbox restricting model file access (for local agent) | None | Prompt-level: confirm budget, smoke-test first | Prompt-level | Hook blocks risky commands (Claude Code only; no parity elsewhere) |
| 12 | Knowledge files | 15 dated reference files, scouting step with cited notes | Dated by sync: bot syncs the CLI skill from huggingface_hub v2.4.0; reference files undated | Docs and changelog (dated) | One `program.md` | References synced from "current agent skills" (commit 2026-10-12) | n.d. | Changelog; cites two arXiv papers |
| 13 | Subagents, roles | Experiment reviewer, log analyst | None found | Local model as subagent (`--as-subagent`, from search snippet, not opened) | None | None | None | Autonomous orchestrator since v2.2.0 (per README; files not opened) |
| 14 | Memory across sessions | Journal in run directories | None | Training history | `results.tsv`, git history | Local state file, optional sync to a W&B Artifact for resume | n.d. | TSV log, git history |
| 15 | Own tests, platforms | ? | None seen; Linux/macOS/Windows via the agents | `tests/` and CI (a commit shows 76 tests passing); Windows, Linux, macOS, WSL, AMD, Intel, NVIDIA | None; Linux plus NVIDIA only (forks for Mac, Windows, AMD) | `tests/`, `skillbench/`, package validation on PRs; Python 3.13+ | Core repo has CI and tests (commit logs); skill-specific tests n.d. | `tests/`; commit says cross-platform matrix "not tested" |
| 16 | Evidence it helps | A small LM benchmark (?) | None found | Vendor claim "2x faster, 70% less VRAM" (no independent check) | About 700 changes, about 20 kept in a 2-day run (third-party blog, not opened at source) | Skill Bench: model training 8 tasks, 90% Claude Code / 85% Codex; finetuning and RL analysis 14 tasks, 72% / 86% (+-3%) | 16 GPUs, 8 h, about 910 experiments, val_bpb 1.003 to 0.974 (2.87%), about $300 GPU + $9 API, same best loss 9x faster than 1 GPU | Author claims only (token reduction, 100 experiments per night) |
| 17 | License, activity | ? | Apache-2.0; 352 commits | Apache-2.0 / AGPL-3.0; daily releases | MIT; stale since 2026-03-26 | Apache-2.0; experimental | Apache-2.0 (not opened); daily | MIT; v2.3.0 2026-10-31 |

## Shared by two or more strong projects and missing in the harness

1. **Pre-flight smoke test on a tiny setting before any paid or long run.** W&B (`search.md`: run the real job at a deliberately tiny setting first, report GPU vs CPU) and HF (demo sizes of 50-100 examples on small hardware, cost estimate first). The harness brief names no such stage.
2. **Pre-launch cost estimate.** HF ships `estimate_cost.py`; W&B requires an agreed compute budget. The harness has a cap, which is a different control (it stops spending, it does not forecast it). Partly missing.
3. **Multi-cloud or queue-based remote compute with parallel fan-out.** SkyPilot (multi-cloud, spot recovery, 16 parallel GPUs in its example) and W&B Launch (queues of agents). The harness has SSH and HF Jobs only, one run at a time (parallel: ?).
4. **Agent-readable tracking through a standard service.** HF makes Trackio mandatory in every script; W&B exposes runs, sweeps and reports via skill plus hosted MCP; Optuna and MLflow publish MCP servers. The harness reads its own metrics file; Trackio is only a named optional module. Partly missing.
5. **Distribution as Agent Skills through `npx skills add` and plugin marketplaces.** HF, W&B, SP and UG all install this way and work across Claude Code and Codex; the harness uses its own installer. Missing as a channel, not as content.
6. **A benchmark of the skill itself.** W&B Skill Bench (task pass rates per agent, +-3%); UG and proyecto26 ship end-to-end tests. Whether the harness has equivalents is "?".
7. **GGUF/safetensors export and quantization as a step.** HF (`gguf_conversion.md`) and Unsloth (Studio export). The harness only names the libraries.

## Jobs another project does better, with the evidence

- **Remote GPU orchestration at scale:** SkyPilot. Evidence: its 8-hour example (about 910 experiments, 9x faster to the same loss than one GPU, $300 + $9, per docs.skypilot.ai autoresearch example). The page does not give a date, and its guard text is inconsistent (16 GPUs vs "maximum 4 clusters"). Harness: one remote run at a time (?).
- **Language-model fine-tuning recipes and export:** HF llm-trainer (SFT/DPO/GRPO/reward, per-method data formats, GGUF) and Unsloth (speed and VRAM, vendor claims, many model families, AMD/Intel/Mac support). Harness only points to them.
- **Experiment tracking, reports and queries:** W&B (runs, artifacts, reports, automations, Launch) and Trackio via HF. The harness's metrics file and `curve` are simpler and local.
- **Hyperparameter search engine:** Optuna with the official `optuna-mcp` (91 stars, ask/tell, study and plot tools, SQLite storage, commit 2026-10-22). The harness has Optuna as an optional module, so this is a delivery gap, not a method gap. Pruners are not documented on the page.
- **Plateau handling in a long loop:** UG's fork-and-flush (fresh-context branches at 33% and 66% of budget or after 5 non-keeps). Evidence is the author's, citing two arXiv papers (not opened).
- **Skill evaluation:** W&B Skill Bench. Harness: ?.

## Where the harness is stricter

- Sealed test data: no other project stops the agent from reading it. AR and UG rely on instructions or a protect-files hook (proyecto26, not among the six, blocks edits to `prepare.py` with a hook).
- Frozen evaluator run by the harness itself, with a receipt: single-use final test evaluation, hash-chained. None of the six has anything like it.
- Statistical discipline inside the loop: seed panels, noise margin, confirmation on fresh seeds. W&B asks for one rerun by prompt; UG applies Mann-Whitney only in a separate command; AR and SP have none.
- Cost: a spending cap enforced by the harness. SP and W&B rely on prompt text; HF gives a pre-estimate.
- Guard hook covering reads and edits plus destructive commands, across three agents. UG's hooks cover Claude Code only and name `.env`, force-push and `rm -rf`.
- Independent reviewer subagent. None of the six has one.

## Other projects considered

- Orchestra-Research/AI-Research-SKILLs, https://github.com/Orchestra-Research/AI-Research-SKILLs : 98 skills, about 11k stars, MIT, v1.7.2 on 2026-06-16; not top six because the last commit is five months old and it is a documentation library (Axolotl, LLaMA-Factory, PEFT, Unsloth, TRL, lm-eval-harness, W&B, MLflow); README read.
- huggingface/ml-intern, https://github.com/huggingface/ml-intern : 10.8k stars, an agent, not a skill; archived 2026-10-22, moved into HuggingChat.
- proyecto26/autoresearch-ai-plugin, https://github.com/proyecto26/autoresearch-ai-plugin : plugin with a PreToolUse protect-files hook, MAD confidence, 27 end-to-end tests; only 12 stars and no dates.
- drivelineresearch/autoresearch-claude-code, https://github.com/drivelineresearch/autoresearch-claude-code : 350 stars, port of pi-autoresearch; small; only the search listing seen.
- alchaincyf/darwin-skill, https://github.com/alchaincyf/darwin-skill : 6.9k stars, optimizes skills, not models.
- Human-Agent-Society/CORAL, https://github.com/Human-Agent-Society/CORAL : 1.1k stars, multi-agent evolution (COLM 2026 per description); general-purpose, not training-specific; only the listing seen.
- optuna/optuna-mcp, https://github.com/optuna/optuna-mcp : single-purpose MCP server (read; see above).
- MLflow MCP, https://mlflow.org/docs/latest/genai/mcp/ : experimental, documented tools are trace and assessment operations, no run-metrics tools documented.
- wandb/wandb-mcp-server, hosted MCP : not opened (part of the W&B entry by search only).
- kkruglik/mlflow-mcp, community MLflow MCP : not opened.
- ScientiaCapital Unsloth MCP, funsloth, unsloth-buddy, other community Unsloth skills: not opened; community, low install counts.
- Hugging Face Hub skills docs, https://huggingface.co/docs/hub/agents-skills : not opened.
- Cloud GPU providers (RunPod, Modal, Lambda, Together) agent integrations: searched for, nothing found; not covered.

## Not opened or not verified

- Karpathy `program.md` text; the 700-changes figure is from third-party blogs.
- HF `train_*.py` and `estimate_cost.py` source, `reliability_principles.md`, `hardware_guide.md`; whether any HF script enforces a limit in code. HF latest human commits and any numbers on results.
- W&B Sweeps reference, `launch_helpers.py`, hosted MCP; Skill Bench is the vendor's own harness.
- SkyPilot: license, INSTALL.md, skill reference text; whether autostop is set by the skill by default (blog snippet says so; docs page does not).
- Unsloth Studio MCP details, Agent Skills claim (changelog snippet), `--as-subagent`; any independent benchmark.
- UG subcommand files, hooks code, arXiv papers.
- Optuna MCP samplers and pruners, release tags.
- Full file contents of any repository tests; I only saw directory names or commit messages.
- Where the harness column says "?": the brief does not say.
- The W&B skills list is "experimental" per the repo.
