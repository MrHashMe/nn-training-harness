# Census of similar projects (round 2, 12 November 2026)

What this is: the comparison of the kit with other systems as wholes, which the research of 10 and 11 November did
not reach. "Similar" means a current project whose purpose overlaps the kit's: loops in which an agent runs ML
experiments by itself, and harnesses, skills and plugins that make a coding agent train or fine-tune models.

How it was made: two reading agents searched for what exists now and then read the strongest systems at their
source (repository, documentation, paper) on 12 November 2026. Web only: nothing was installed or run. Their full
notes are `draft/census-loops.md` and `draft/census-harnesses.md`; they say for every system what was opened and
what was not. The readers had only a short description of the kit, so the kit's column below was filled in
afterwards from the kit's own code at commit `c6c1593`. The candidates and their decisions are rows of the ledger
(`../LEDGER.md`, notes `census-loops`, `census-harnesses` and `round2`).

## Systems read at their source

| System | Kind | Source | Version or commit | Date | Licence |
|---|---|---|---|---|---|
| karpathy/autoresearch (AR) | loop | https://github.com/karpathy/autoresearch | commit `228791f` | 2026-03-26 (nothing since) | MIT per README, no licence file |
| AIDE (WecoAI/aideml) | loop | https://github.com/WecoAI/aideml | no release; default branch as pushed | 2026-10-16 | MIT |
| AIRA-dojo | loop | https://github.com/facebookresearch/aira-dojo, arXiv 2507.02554 | no release; as pushed | 2026-04-14 | CC BY-NC 4.0 |
| MLEvolve (MLEv) | loop | https://github.com/InternScience/MLEvolve | commit `f4a37b96` | 2026-10-16 | Apache-2.0 |
| RD-Agent (RD) | loop | https://github.com/microsoft/RD-Agent | no release listed; as pushed | 2026-10-21 | MIT |
| AIBuildAI (AIB) | loop | https://github.com/aibuildai/AI-Build-AI, arXiv 2604.14455 | editions V1 to V2.5 and Science; as pushed | 2026-11-11 | MIT |
| Hugging Face skills (HF) | skills | https://github.com/huggingface/skills | commit `25910b3` | 2026-10-29 | Apache-2.0 |
| Unsloth and Unsloth Studio (Uns) | library, app | https://github.com/unslothai/unsloth | v0.1.917-beta, commit `2d3deb5` | 2026-11-11 | Apache-2.0, Studio AGPL-3.0 |
| Weights & Biases skills (W&B) | skills | https://github.com/wandb/skills | commit `10aac21` | 2026-11-06 | Apache-2.0 |
| SkyPilot agent skill (Sky) | skill | https://github.com/skypilot-org/skypilot, https://docs.skypilot.ai/en/latest/getting-started/skill.html | master, commit `f6df9e5` | 2026-11-11 | Apache-2.0 (licence file not opened) |
| uditgoenka/autoresearch (UG) | plugin | https://github.com/uditgoenka/autoresearch | v2.3.0, commit `7bddd05` | 2026-10-31 | MIT |

Read at README level only, because they publish no results: AI Scientist-v3 (https://github.com/SakanaAI/AI-Scientist-v3,
Apache-2.0, pushed 2026-10-18: sealed evaluator and rubric, a container per phase, drives six headless agent
programs) and Arbor (https://github.com/RUC-NLPIR/Arbor, Apache-2.0: executors in git worktrees, a change is merged
only if a held-out gain clears a margin). These two are the closest to the kit in design.

Why these: the MLE-bench leaderboard (https://github.com/openai/mle-bench, note of 2026-04-24, closed to new
entries) is the only place where such loops are measured with repeats, so the open systems on it were read
(AIBuildAI 63.11 ± 0.44, MLEvolve 61.33 ± 1.33 "any medal"), with AIDE as the field's common baseline, AIRA-dojo
for the only controlled comparison of search operators and policies (20 seeds), RD-Agent and autoresearch for
adoption. The harness group was chosen by vendor backing, adoption and activity. Medal rates measure solving a
Kaggle competition from nothing, which is a different job from the kit's (improving a given training repository
under an evaluator that stays fixed); five of the benchmark's tasks have leaking test data.

## Capability matrix

yes / part / no; n.s. = not stated in what was read; – = does not apply (the project is not a loop, or rents no
compute). "Kit" is this kit at commit `c6c1593`. Built after that commit, on the same day, and not entered in
the matrix: for row 15 a restart when a campaign stalls, for row 20 a search of numeric settings by the harness
(a stratified random search, no optimizer library), both off unless a project's config sets them, and for row 27
a runnable fine-tuning task in `benchmarks/finetune/` (REPORT.md, "Round 3").

| # | Capability | Kit | AR | AIDE | AIRA | MLEv | RD | AIB | HF | Uns | W&B | Sky | UG |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | **The loop and its limits** | | | | | | | | | | | | |
| 1 | Runs experiments unattended in a loop | yes | yes | yes | yes | yes | yes | yes | no | no | part | part | yes |
| 2 | Stops at limits enforced by code | yes | part | part | part | part | part | part | – | – | no | no | part |
| 3 | Cap on money or on the agent's tokens | yes | no | no | no | no | no | n.s. | no | – | no | no | no |
| | **Is the result real** | | | | | | | | | | | | |
| 4 | Keep or revert decided by harness code, from an evaluator the agent cannot edit | yes | no | no | no | no | n.s. | n.s. | – | – | no | no | part |
| 5 | Several seeds inside the loop, with a margin above their noise | yes | no | no | no | no | no | n.s. | – | – | part | no | part |
| 6 | Confirmation on fresh seeds when the search ends | yes | no | no | no | no | no | no | – | – | no | no | no |
| 7 | Scoring data hidden from the agent | yes | no | part | part | part | part | part | no | no | no | no | no |
| 8 | Final test used once, with a record | yes | no | no | no | no | no | no | no | no | no | no | no |
| 9 | Evaluator and data checksummed or read-only | yes | no | no | no | no | part | n.s. | no | no | no | no | part |
| 10 | Mechanical guard on destructive or costly commands | yes | no | no | no | no | no | n.s. | no | no | no | no | part |
| 11 | Independent reviewer role | yes | no | no | no | no | no | no | no | no | no | no | no |
| | **Search** | | | | | | | | | | | | |
| 12 | Repair attempt after a crash | no | no | yes | yes | yes | yes | n.s. | – | – | no | no | n.s. |
| 13 | Combines two candidates | no | no | no | yes | yes | yes | n.s. | – | – | no | no | no |
| 14 | Search beyond one greedy branch | no | no | part | yes | yes | yes | yes | – | – | no | no | no |
| 15 | Restart or branch on a plateau | no | no | no | n.s. | yes | n.s. | n.s. | – | – | no | no | yes |
| 16 | Evaluation in parallel | no | no | n.s. | yes | yes | yes | n.s. | – | – | part | yes | no |
| 17 | Memory across campaigns, retrieved by similarity | no | no | no | no | part | part | yes | no | no | part | no | no |
| 18 | Check of the code before it runs | part | no | no | no | yes | part | n.s. | no | no | no | no | no |
| 19 | Web or literature scouting | yes | no | no | no | part | part | no | no | no | no | no | n.s. |
| 20 | Numeric settings handed to an optimizer | no | no | no | no | no | n.s. | part | no | no | part | no | no |
| 21 | The worker sees curves and logs of earlier runs | part | yes | yes | yes | yes | yes | n.s. | yes | part | yes | yes | yes |
| | **Running and tooling** | | | | | | | | | | | | |
| 22 | Local run lifecycle: detached start, status, stop, resume | yes | part | no | no | no | part | n.s. | part | part | no | no | no |
| 23 | Remote compute | yes | no | no | yes | no | no | no | yes | no | yes | yes | no |
| 24 | Cost known before a paid launch | yes | – | – | – | – | – | – | yes | – | part | no | – |
| 25 | Short trial run before a long or paid one | yes | no | no | no | no | yes | n.s. | part | no | yes | no | no |
| 26 | Tracking service the agent can query | part | no | no | no | no | part | no | yes | part | yes | no | no |
| 27 | Fine-tuning recipes and export (SFT, DPO, GRPO, GGUF) | part | no | no | no | no | no | no | yes | yes | no | no | no |
| 28 | Installs through a plugin marketplace or `npx skills` | no | no | no | no | no | no | no | yes | no | yes | yes | yes |
| 29 | Published measurement of itself, with repeats | part | no | yes | yes | yes | yes | yes | no | no | part | part | no |

Notes on the kit's column and on cells that need words:
- 2, 3: the kit refuses to start without a limit and stops at the first one reached (runs, hours, GPU-hours, money,
  agent tokens). The others cap steps or time; none caps money or tokens.
- 4: autoresearch's agent reads its own log and runs git; in AIDE a model call extracts the metric from the output;
  AIRA-dojo and MLEvolve rank by a number that agent-written code printed. UG keeps or reverts mechanically, but on
  the number of a command the agent itself runs.
- 5: the benchmark systems repeat seeds only to report their own benchmark score. W&B asks by prompt for one rerun
  of the winner; UG has a Mann-Whitney test in a separate command.
- 7: in the kit, where the project seals the split; otherwise the loop says at start that the agent can read it.
- 12 to 17: the kit's search is one greedy branch: one change per session, kept or reverted, and it stops after
  repeated failure or when two sessions in a row propose nothing.
- 18: the kit scans the diff and the session's transcript by rule before any training; there is no review session.
- 21: since 12 November the worker's prompt carries both scores of a first-seed discard and a few points per
  logged metric of one run of the best commit. Run folders stay unreadable for it by design.
- 23: ssh targets and Hugging Face Jobs, one run at a time; the Jobs route has not run against the real service.
- 24: `nnremote` books hours × price against the user's cap before anything paid starts, or refuses.
- 25: a step of the procedure (SKILL.md gate 1; `hpo.md`), not enforced by code.
- 26, 27: the kit's own run records, with Trackio as an optional mirror; fine-tuning is covered by references
  (`finetuning.md`, `llm.md`), with no runnable recipe.
- 29: the kit's pilot of 11 November (three arms, repeats) found no edge over the old kit or over no kit.

## What the census found

**No whole project does the kit's job better.** The kit is alone in rows 3 to 6, 8 and 11: keep or revert by
harness code on an evaluator the agent cannot edit, seed repeats with a noise margin inside the loop, a
confirmation on fresh seeds, a final test that can be used once, and caps on money and tokens. The benchmark
systems win medals at a different job and take their score from code the agent wrote. For a training repository
whose owner needs the improvement to be real, replacing the kit's loop with any of them would remove what makes
its numbers trustworthy.

**Where others are ahead**, with the evidence:
- More search operators (rows 12 to 15). The only controlled comparison (AIRA-dojo, arXiv 2507.02554): better
  operators at the same search policy gave 45.5 % against 39.8 % medals, with about twice the tokens, and the gain
  is not attributed to any single operator. Search policy itself adds little: MCTS and evolutionary search add
  about 2 points; a second study (arXiv 2609.40303) found no significant difference between a chain, greedy,
  UCB1 and best-of-N.
- Throughput by parallel evaluation (row 16): SkyPilot's published run reached the same loss about nine times
  faster on 16 GPUs, single measurements, about $300.
- Recipes for language-model fine-tuning and export (row 27): Hugging Face skills and Unsloth.
- Distribution (row 28) and a published measurement of the product itself (row 29).
- The worker's view of earlier runs (row 21): every other loop lets its agent read logs and curves; the kit's
  worker saw only the list of earlier decisions until this round.

**Where the kit already has what a reader took for a gap:** a cost known before launch (row 24), a short trial run
before a long one (row 25).

## Candidates the census produced

Every row is in the ledger with its source and date; decisions as of 12 November 2026.

| Candidate | Shared by | Decision | Reason in short |
|---|---|---|---|
| The worker sees run records | all six loops | Adopt, built (`c6c1593`) | removing such tools cost 8.9 medal points in arXiv 2609.40303; effect here not measured |
| Repair attempt after a crash | AIDE, AIRA-dojo, MLEvolve, RD-Agent | Trial | no ablation anywhere; in the kit's nine recorded campaigns 0 of 56 iterations crashed, so there is nothing to replay it on |
| Combining two candidates | AIRA-dojo, MLEvolve, RD-Agent | Assess | the one measured gain bundles several changes |
| Search beyond one greedy branch | five loops | Hold | the controlled evidence shows no reliable gain, and one GPU cannot pay for the extra evaluations |
| Restart or branch on a plateau | MLEvolve, UG | Adopt, built in round 3 as `loop.restart_after`, off unless set (second-look B5) | no measured gain, here or elsewhere beyond one study's small difference; the stall seen here on 12 November was a margin no idea could clear, which the second seed panel addresses |
| Parallel evaluation | AIRA-dojo, MLEvolve, RD-Agent, SkyPilot | Trial, optional | real wall-clock gain; on one GPU concurrent runs change scores under a time budget, on rented GPUs it costs money |
| Retrieval memory across campaigns | MLEvolve, AIBuildAI | Assess | the only ablation (AIRA-dojo) shows almost no effect |
| Review of the diff before training | MLEvolve, RD-Agent | Assess | no measured effect; the kit's rule scan and checksums exist |
| Confirming the best two commits | AIRA-dojo | Assess | measured on Kaggle submissions, not on a keep-or-revert chain |
| Fine-tuning recipes and export | Hugging Face skills, Unsloth | A fine-tuning task: Adopt, built in round 3 as `benchmarks/finetune/` (second-look B2); the vendor skills inside kit runs: Trial; GGUF: Assess | the task ran here with a stand-in agent only; what the kit or a vendor skill adds on it is not measured |
| Hugging Face skills, Unsloth beside the kit | – | Trial (as before) | training libraries inside kit runs, not controllers; neither has a guard, a sealed split or statistics |
| Marketplace or `npx skills` distribution | HF, W&B, SkyPilot, UG | Assess | a bare skill carries no hooks, and the guard hook is what matters |
| A task-set benchmark of the skill | W&B | Assess | the kit has a pilot comparison; a task set needs paid model calls |
| SkyPilot agent skill | – | Reject (as before) | its cost guards are prompt text and it lets the agent launch paid resources past the kit's cap |
| W&B skills | – | Hold (as before) | needs an account the user has not set up; its loop has no fixed evaluator or sealed data |
| Short trial run; cost before launch | W&B, HF, RD-Agent | already in the kit | rows 24 and 25 |
| autoresearch, AIDE, AIRA-dojo, MLEvolve, RD-Agent, AIBuildAI, UG as a replacement | – | Reject or Hold | each is weaker on every row of "Is the result real" |

## Whole-system alternatives

| | What it is | Fails when |
|---|---|---|
| A | The kit, with this round's changes | many ideas per hour are wanted: one GPU, one run at a time |
| B | A plus vendor skills as training libraries inside kit runs (Hugging Face trainer scripts, Unsloth) | nothing new fails; adds accounts, downloads and packages |
| C | A benchmark scaffold as the loop (MLEvolve, AIDE, RD-Agent) | "a gain seen on one seed must not be kept" and "the agent must not edit what scores it": both fail; Linux and containers assumed |
| D | autoresearch fanned out over rented GPUs with SkyPilot | the same two, and money is controlled by prompt text only |

The choice is A, with B's parts as optional modules, which is what the ledger already says. What would change
it: a measurement on training repositories (not Kaggle tasks) in which a scaffold's operators raise held-out
results at equal budget with repeats; or many GPUs at the user's disposal, which makes row 16 the bottleneck.

## Others considered, one line each

- MLE-STAR (arXiv 2506.15692): web search for a first solution, ablation-guided refinement; code and licence not verified.
- AI Scientist-v2: stale (last push 2025-12-19), custom licence. Agent Laboratory: stale (2025-08-20). MLGym: archived 2026-10-01.
- evo (https://github.com/evo-hq/evo): parallel subagents in worktrees, no noise handling stated, no results.
- OpenEvolve, ShinkaEvolve: general code evolution, not ML training; not opened on 12 November.
- ML-Master 2.0, MARS+, PiEvolve, Famou-Agent 2.0, LoongFlow, Disarray: leaderboard entries; source unavailable or not opened.
- Prime Intellect's speedrun harness: a method and a result, not a toolkit; its fixed verifier with eight seeds is the closest outside precedent for the kit's rules.
- Ports of the autoresearch pattern (leo-lilinxiao/codex-autoresearch, TheGreenCedar/codex-autoresearch, pi-autoresearch, junjunjunbong/research-loop, drivelineresearch/autoresearch-claude-code): covered by the note `loop-autoresearch`; none publishes results.
- proyecto26/autoresearch-ai-plugin: a hook that protects one file and 27 end-to-end tests; 12 stars, no dates.
- Orchestra-Research/AI-Research-SKILLs: 98 documentation skills, last commit 2026-06-16.
- huggingface/ml-intern: archived 2026-10-22. alchaincyf/darwin-skill: optimises skills, not models. CORAL: general multi-agent evolution.
- optuna-mcp, MLflow MCP, wandb-mcp-server: rows of their own in the ledger; MLflow's documented tools do not cover run metrics.
- Operand Quant, FM Agent, ScienceFlow, EurekAgent, GEAR, AlphaLab, AutoScientists, Argus: titles and snippets only.
- Agent integrations of GPU providers (RunPod, Modal, Lambda, Together): searched for, nothing found beyond the rows the ledger has.

## Limits of this census

- Nothing was installed or run; every statement about another system comes from its pages, files or paper.
- Commit dates are GitHub's "pushed" date, which also counts pushes to other branches.
- AIBuildAI: README and paper abstract only. RD-Agent: README and one documentation page. AIRA-dojo: the paper's
  later appendices were not read. Their "n.s." cells are unknown, not absent.
- Figures quoted from a project about itself (MLEvolve 65.3 %, AIBuildAI 70.7 %, Unsloth's speed and memory, UG's
  claims) are that project's own.
- Text aimed at agents: two projects tell a reader's agent to fetch and follow instructions from the network
  (the README of Orchestra-Research/AI-Research-SKILLs, and an install route in SkyPilot's documentation). The
  readers did not follow them. No other page tried to direct the readers.
