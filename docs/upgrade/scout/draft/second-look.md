# Scout note: second look after the live runs

Date checked: 2026-11-11.
Question: what would improve the kit most from here, and what is the best current way to train a network with a
coding agent.
Companion file: `docs/upgrade/scout/draft/second-look.candidates.jsonl` (10 candidates).

## How this note was made, and what was left out
- One reader (a cheaper model) ranked the 649 open rows of the ledger (144 adopted and unfinished, 215 Trial, 290
  Assess). One web reader (a cheaper model, about 35 page reads, no access to the ledger) surveyed systems,
  ablations, failure modes and training methods published up to November 2026. Its sources were not opened a second
  time by anyone; each is marked below with what it opened.
- I measured three things on the data of the pilot's two loop campaigns of 11 November and simulated the loop's
  keep rule. No GPU was used and no kit file changed.
- Left out because of the usage limit: a second scout, a cross-check of the web reader's figures, and every trial
  that needs training runs.

## Measured here (pilot of 11 November, benchmark `charlm`, native Windows, one GPU)
1. **The margin moves with luck.** Same task, same code, two campaigns: the three baseline runs had a standard
   deviation of 0.0055 and 0.0032, so the keep margin was 0.0089 and 0.0052. Pooled over all full seed panels the
   within-commit deviation is 0.0048 (6 degrees of freedom) and 0.0029 (4). The earlier campaign of the same day on
   the same benchmark had a margin of 0.0132 (REPORT.md section 2).
2. **The keep rule keeps too many changes that do nothing.** Monte Carlo of the rule as coded (normal noise,
   independent runs, 40,000 trials per cell; effect in units of the run-to-run deviation; a cell is the share kept
   and the mean number of runs spent on the idea):

   | Rule | no effect | 1 | 1.5 | 2 | 3 |
   |---|---|---|---|---|---|
   | as coded: deviation from three baseline runs | 7.9 %, 2.0 | 33 %, 2.5 | 51 %, 2.7 | 68 %, 2.8 | 91 %, 3.0 |
   | the same rule with the deviation known | 2.1 %, 2.0 | 21 %, 2.5 | 42 %, 2.7 | 66 %, 2.9 | 94 %, 3.0 |
   | sequential, up to six seeds, keep at z above 2.4 | 1.7 %, 3.1 | 30 %, 4.4 | 61 %, 4.3 | 86 %, 3.8 | 99 %, 3.1 |

   The extra keeps of the first row are not skill: they come from baseline panels whose deviation happened to be
   small. Per run spent, the second and third rows find real gains at about the same rate; per idea, and so per
   agent session, the third finds more. Both keeps of 11 November stand on the pooled deviation (z about 3 to 4)
   and held on the test split.
3. **The time budget is not the noise source on this machine.** Within one commit the steps completed in 30 seconds
   vary by 0.1 to 1.4 %, and their within-commit correlation with the score is +0.31 (nine runs) and -0.16 (six).
4. **Pairing by seed removes much of the noise for some changes.** On the test split the three scoring seeds carry a
   shared offset (means 1.7612, 1.7520, 1.7445 over seven scored scripts). The two scripts that differ from the
   shipped one only by a weight average score 0.0078 and 0.0050 better, with a deviation of the three paired
   differences of 0.0039 and 0.0033, where the unpaired deviation over seeds is 0.012 to 0.015. For scripts that
   change the training trajectory the pairing did not help in this data.

Scripts: `steps_vs_score.py`, `keep_rule_sim.py` and `seed_effect.py` in the upgrade's temporary work folder
(`%TEMP%\nnkit-upgrade`); they are not part of the kit.

## Found on the web (opened by the web reader on 2026-11-11)
- **Final selection loses more than the search policy gains.** AIRA-dojo (arXiv 2507.02554, revised 2025-11-04):
  choosing the final candidate on test instead of validation scores was worth 9 to 13 points of medal rate; a greedy
  loop with better operations scored 45.5 % against 39.8 %; after about 50 hours longer runs overfitted. FML-bench
  (arXiv 2605.17373, 2026-05-29; six agents, 18 tasks, one model): greedy 0.192, tree search 0.193, greedy that
  branches on a stall 0.208; validation-to-test gap 0.025 to 0.045.
- **Numbers belong to an optimizer.** arXiv 2603.24647 v3: in a fixed numeric space TPE (0.9768) and a CMA-ES and
  language-model hybrid (0.9763) beat the code-editing agent (0.9814); one task. The ledger's rows of 10 November
  cite v5 with other figures.
- **Agents game scores often, and prompts barely help.** arXiv 2608.30724 (2026-08-31): 57.1 % of runs, cut by 6.2
  points by a validity-aware prompt. arXiv 2609.28614 (2026-09-23, abstract): 30.5 % of open-ended research tasks; a
  reviewer model that saw code and scores missed 6.5 %, and evasion grew over feedback rounds. arXiv 2603.11337:
  only a locked evaluator together with unreadable test data gave no compromise. The kit has both.
- **Simple baselines are strong, small validation sets are noisy.** arXiv 2602.16805 (2026-02-18): random or
  sequential sampling matched an evolutionary system on 6 of 9 problems and a tree-search agent on 6 of 10 tasks;
  the authors advise at least 300 effective validation items and confidence intervals.
- **What agents contribute today is incremental.** METR (2026-04-21): of 77 speed records on one small-model
  training task in 24 months, four credit an AI agent, all shallow or moderate changes. Here, both campaigns kept
  one change, a weight average.
- **Search with memory, benchmark-tuned.** MLEvolve (arXiv 2606.06473, 2026-06-04): 65.3 % medals on 75 tasks;
  ablations on 22 tasks without seeds.
- Training methods since June 2026: thin. Muon and SOAP ahead of AdamW at very large scale (arXiv 2607.20548,
  abstract); the rest single-source. No change to `references/optimization.md`.
- Not found: a controlled comparison of one agent against several, a study of memory across campaigns, evidence on
  agents stopping early, independent replications of the 2026 optimizer and fine-tuning claims.

## What to do next, most valuable first
A. **Make the loop's decisions trustworthy** (standard library, no account, testable offline):
   1. the pooled, paired noise estimate; 2. the confirmation step on fresh seeds with the count of ideas tried;
   3. the single-use receipt for the final test evaluation; 4. the evaluator self-test with negative controls;
   5. an accepted "no valid improvement" exit in the worker prompt (ledger row from `loop-autoresearch`: an abort
   option cut cheating from 54 % to 9 % and from 49 % to 12 %, arXiv 2510.20270 v1).
B. **More result per budget** (each needs training runs to judge):
   1. numeric settings searched by the harness; 2. the fine-tuning track for language models with a second
   benchmark task; 3. seed escalation for near-misses; 4. the worker reads the records of earlier runs
   (`sweep-auto-research`: removing such tools cost 8.9 medal points, arXiv 2609.40303); 5. branch on stall.
C. **Unattended reliability and readiness**:
   1. a guard-liveness check and a minimum agent version before every unattended session; 2. one readiness report
   (`doctor`), since a real project using the kit has no primary metric configured; 3. a job object per run for a
   reliable stop on Windows; 4. a few-step feasibility run before a launch; 5. an atomic checkpoint helper.
D. Still waiting on the user: the live checks with Codex, Cursor, Claude Code on Linux and Hugging Face Jobs.

## Built since (11 November, group A)
All five items of group A are built and tested with a stand-in agent, with these differences from the list above:
- 1: the noise is pooled over all seed panels; runs are not compared seed by seed. The paired part is a Trial row
  of its own, because the measurement above ("Measured here", point 4) shows a gain only for changes that leave
  the training trajectory alone, and a paired test with three seeds has two degrees of freedom.
- 3: the receipt records every use and a second use is refused without a reason, but it is a record, not a seal.
- 4: the self-test had two fixtures on 11 November (the same run scored twice, an empty run folder). Round 4
  (13 November) built the other two, a folder with only a run's records and a copy whose records and log state
  other values, and controls that must stay at their floor (`references/loop.md`, "One campaign", step 1).
What it does and what it costs: `references/loop.md` ("The keep rule", "The confirmation"), `references/validity.md`
section 5, and the upgrade report.

## Built since (12 November, group B)
Items 3 and 4 were built in round 2: a second seed panel for a near-miss, and a few points of the best run's
curves in the worker's prompt. Items 1, 2 and 5 were built in round 3. Each is tested with a stand-in agent and
none is measured on training results. Differences from the list above:
- 1: a stratified random search of a handful of versions, each trained once on a seed outside the seed panels;
  no optimizer library and no successive halving. Off unless `loop.search_trials` is set.
- 2: the task is `benchmarks/finetune/` in the kit's checkout: SmolLM2-135M-Instruct with a LoRA adapter on
  Banking77, 30 seconds a run. Its trainer is a plain PyTorch loop, not TRL. The comparison of arms was not run.
- 5: the campaign goes back by one keep on its single line, keeps the best commit it found as its result and
  shows the worker the history of the code in front of it. Off unless `loop.restart_after` is set.
What each does: `references/loop.md` ("A search by the harness", "A restart when the campaign stalls"),
`benchmarks/finetune/README.md`, and the upgrade report ("Round 3").

## Asked afterwards (12 November)
The user asked whether a list of projects would do better than the kit. The ledger already held a decision for
all of them except four, which were read on 12 November and have rows in this note now. None was tried.
- Fine-tuning a small model on a stronger agent's solved traces before any RL (TRL `examples/sft_agent_traces`
  at commit a76cab3): Trial. The authors' own run takes a 2B model from 7.6 % to 33.3 % of 144 held-out tasks.
  The result to keep, whatever the method: with tasks split by task but not by source dataset, the student
  scored 42.4 % on tasks that shared a dataset with a training trace and 17.3 % on clean ones.
- Harness adapters (one LoRA per model and agent harness, trained with GRPO inside pi, opencode and hermes; blog
  post of 6 November): Hold. They do not apply to the agents the kit drives, and the published figures are the
  authors' best cases without intervals. Their task checks match the kit's evaluator self-test where it exists
  (the same solution scores the same twice, doing nothing scores nothing) and name what it still lacks (a stub
  and a tampered test must score nothing).
- safeagents and atif-scan (checks of an agent's tool calls and recorded sessions for reward tampering and
  leakage): Assess. The same idea as the kit's guard and transcript scan; neither repository was read.
- Plurai Simulation plugin (a hosted service that tests agent applications with simulated users): Hold. A
  different job from training, an account, and judgments that are not a frozen local evaluator.

The first three concern training a model to act as an agent. `references/finetuning.md` has a section on RL
post-training (what to log and read in a GRPO run), and `references/validity.md` has the rule that the example's
leakage result illustrates (unit leakage: split by group, here by source dataset). What the references do not
name is the step before RL, a warm start from solved traces. One line under the fine-tuning reference's
candidates to test would name it; it was not added, because the user asked a question and not for a change.
