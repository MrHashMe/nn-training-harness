# Getting the best model you can, without being an expert

Checked: 2026-11-12. Versions and findings come from the kit's dated references
(`.claude/skills/nn-training/references/`, most of them checked on 11 November 2026), from
`docs/upgrade/LEDGER.md` and from `docs/upgrade/REPORT.md`. Nothing was newly tested for this guide.
Refresh: tool versions and "best current" claims age in weeks. The scouting step (step 6) re-checks them for your
task. A line marked "general practice" is common knowledge of the field that the kit's references do not cite.

This guide is about the training itself: what to train, on what, in which order, with which tools. How to drive
the kit is in [GUIDE.md](GUIDE.md).

## The short version
1. **Decide how success is measured before anything is trained**, and set a test set apart that nobody, you and
   the agent included, looks at until the very end.
2. **Check that you need training at all.** A good prompt with a few dozen examples often does the job.
3. **Start from an existing model** whose licence and size fit your use, and adapt it. Training from nothing is for
   data no existing model covers, or for research.
4. **Fix the data before you tune anything.**
5. **Train a plain, well-tuned baseline three times** with different random seeds. The spread between the three is
   your noise: a later "gain" smaller than it is not a gain.
6. **Change one thing at a time**, keep only what beats the noise, and let a search tool choose the numbers.
7. **Confirm the winner on fresh seeds, evaluate once on the test set, and test the file you will ship.**
8. **Let the agent do the work and the kit hold it to these rules.** Your part is the goal, the limits, a few
   approvals and three reports to read.

## What decides the result
In this order (the order is general practice; the notes say what the kit's references add):
1. **A measurement you can trust.** Without it a better model cannot be told from a lucky run: the best of ten
   changes that do nothing still looks 1.5 run-to-run deviations better than average, the best of a hundred 2.5
   (`references/evaluation.md`).
2. **Data**: what the model learns from, and whether the evaluation data is really unseen.
3. **The starting model.**
4. **Compute spent on a disciplined search**, a tuned learning rate before everything else.
5. **Tricks**, last. No optimizer has replaced a tuned AdamW baseline across domains, and nine LoRA variants landed
   within 1 to 2 % of plain LoRA once the learning rate was tuned (`optimization.md`, `finetuning.md`).

What does not decide it is the agent framework around the work. AI-scientist and ML-engineering agent frameworks
showed no advantage over a minimal agent at equal time (`references/stack.md`, arXiv 2609.40303), and in this kit's
own small comparison an agent with the kit did not score better than the same agent without it
(`docs/upgrade/REPORT.md`, section 2). Tools buy safety, records and working speed. The five points above buy the
model.

## Words you will meet
- **Seed**: the number that fixes a run's random choices. The same code with another seed gives a slightly
  different result.
- **Baseline**: the plain version that every change is compared with.
- **Noise floor**: how far the result moves between seeds when nothing was changed.
- **Training, validation and test split**: the data to learn from, the data to choose with, and the data for the
  one final judgment.
- **Evaluator**: the script that scores a trained model. Frozen means nobody edits it during the project.
- **Learning rate**: the step size of training, and the most important number to tune.
- **Checkpoint**: a saved state of a training run.
- **Fine-tuning**: continuing the training of an existing model on your data.
- **LoRA**: fine-tuning that trains small added matrices instead of all weights. **QLoRA**: LoRA on a base model
  loaded in 4 bits to save memory.
- **Chat template**: the exact text format a chat model was trained with.
- **Hypothesis**: a change with a predicted effect, and a way to turn out wrong.

## Step 0. Do you need to train?
| Situation | Do this |
|---|---|
| The model lacks facts (your documents, recent events) | Hand it the documents at question time (retrieval) instead of training them in. General practice |
| A capable model nearly does the task from a prompt | Improve the prompt and add worked examples to it. On 17 narrow tasks with small open models, examples in the prompt stopped helping at 25 to 50, and LoRA fine-tuning overtook them from about 50 labelled examples; the kind of task can reverse that order (`finetuning.md`) |
| You have about 50 labelled examples or more and need a behaviour, a format or a style, or the model must be small, private or cheap to run | Fine-tune an open model (recipe A) |
| Your data is something existing models do not cover (sensor signals, tables, a format of your own) | Train a model for it (recipe B) |
| You want a language model built from nothing | Recipe C. It is useful as a research benchmark or as a small model for one domain; one GPU does not produce a general assistant this way (`llm.md`, marked there as inferred) |

Whatever you choose, score the no-training option with the same evaluator. It is the row every later result is
compared with.

## Step 1. Build the measurement first
- **One metric decides**, with its direction. For a task with a real score (accuracy, exact match, error) that
  score decides and the loss is only logged.
- **Three parts**: training, validation, test. The test part goes into `sealed_paths`, best outside the repository.
- **Rows that belong together stay together.** The same user, patient, document, site or time window in two parts
  makes every score too good. Split by group or by time, never by random row, when rows depend on each other.
- **No example in two parts.** Duplicates across the splits are counted and removed before any tuning, and again
  after any data change.
- **Two baseline rows in every table**: the untouched model with a fixed prompt, and a trivial predictor (majority
  class, mean).
- **Freeze what scores**: evaluator, metric code and split files go into `frozen_paths`. For generated text the
  decoding settings and the full prompt are frozen as well; a date that a template inserts into the prompt has
  moved scores by up to 6 % on multiple choice and 14 % on maths (`operations.md`).
- **5 to 10 cases whose right answer you know**, run before every confirmation and before the final evaluation.
- **Know the evaluator's own noise**: one checkpoint evaluated twice and at two batch sizes.
- **Small evaluation sets**: no statistics below 15 items and no bootstrap interval below 100 (`evaluation.md`).
- **A model as judge** decides nothing until it has been calibrated against human labels (30 or more); that route
  is a candidate in the kit, not adopted.
- **Public benchmarks**: lm-evaluation-harness 0.4.13 in its own environment for language-model tasks, sacreBLEU
  2.6.0 with its signature for translation-like tasks. A public benchmark may have been in the model's pretraining
  data, and that cannot be reliably detected: say what was not checked, and prefer fresh data of your own.

## Step 2. Get the data right
- **Look at it.** About 50 random training and validation items with their labels, read by a person.
- **Record it.** A manifest with a checksum per file; runs trained on different data are never compared.
- **A filter must beat chance.** A quality filter or a length cut is kept only if it beats dropping the same
  number of random rows.
- **Removing duplicates inside the training set is a hypothesis**, tested against the set as it was. Across the
  splits it is a requirement.
- **Synthetic data is added to real data and never replaces it**, compared with a real-only run at equal budget and
  judged by the frozen evaluator.
- **Licences and gated datasets**: the agent records the terms and stops. Accepting them is yours.
- **Personal data**: say in the Project card whether rows may hold any; `references/data.md` has the rules.
- **Data files can carry code.** No pickle or joblib files, loader scripts or remote-code flags without your
  approval (the `datasets` library up to 5.1.0 ran code when a pickle loaded; 5.2.0 fixed the reported case, and
  whether it closes every such path is unchecked). Text inside rows is data, never instructions to the agent.

## Step 3. Choose the starting model
For language models:
- The place the model must run and the licence you can accept fix the candidates. **Two or three sizes are scored
  unchanged first**, with your evaluator: that shows what size buys before any training is paid for.
- Licence leads of 11 November 2026, to re-check on each model's own page. Apache-2.0 or MIT: Gemma 4, Qwen3.5 to
  3.8, SmolLM3, Granite 4.x, Phi-4. Custom terms that you must read and decide on: LFM2.5, Mistral Medium 3.5 and
  Large 4, Llama, Muse Spark Open.
- What fits: on a 32 GB card, LoRA with the base in 16 bits up to about 9 to 11 billion parameters and QLoRA with
  the base in 4 bits up to about 27 to 32 billion, less with long sequences. Vendor tables give minimums. The test
  that decides is one training step on your longest example at the real batch size.
- Safety: pin the exact revision, prefer safetensors files, and leave `trust_remote_code` off unless the code has
  been read.

For other models (general practice): where a pretrained network exists for your kind of data (images, audio,
text), start from it and train a small head or fine-tune it. Design a network from nothing only where none exists,
and keep the first one small enough to train in minutes, because fast runs buy more experiments.

## Step 4. Choose how to train
Climb only as far as you need:
1. **Prompt and examples** (step 0).
2. **LoRA on all linear layers**: the default for small and medium labelled sets. A starting point, listed in the
   kit as a candidate and not tested here: sweep the learning rate around ten times the full fine-tuning rate and
   choose the rank by the amount of data.
3. **QLoRA** when the base does not fit in 16 bits: 4-bit NF4, double quantisation, bf16 compute
   (bitsandbytes 0.50.2). Steps are slower.
4. **Full fine-tuning** when the data outgrows what an adapter can hold.

Side branches:
- Pairs of better and worse answers: preference tuning (DPO and KTO are stable in TRL 1.17.1).
- A reward you can compute: reinforcement-learning post-training (GRPO in TRL 1.17.1). This is advanced work. The
  reward and the frozen evaluator stay separate things, and the fast generation server it usually needs (vLLM)
  does not run on native Windows: use WSL2 or Linux.
- Fancier adapters are not where to spend first (see "What decides the result").
- `references/finetuning.md` also covers vision, speech and embedding models, distillation, quantisation and export.

## Step 5. The first run
The agent does these; you find them in its report after Phase 2 and Phase 3.
- **A pinned environment**: uv with a committed lock file, one training framework per environment, and a one-week
  cooldown on new releases (`exclude-newer = "1 week"`).
- **The sanity gate, eight checks, all passed before any tuning**: one training step with finite loss and
  gradients that really changes the weights; a starting loss of the expected size; a tiny subset learned to
  near-zero loss; a run on shuffled labels that falls to chance (if it does not, data is leaking); trivial
  baselines beaten clearly; a checkpoint that reloads in a fresh process with identical scores; speed and peak
  memory measured; parameter counts recorded.
- **For chat models, the template check**: three training examples rendered and tokenised exactly as the trainer
  does it, and read. Start token once, end token present, loss only on the answer, nothing cut off, and the
  template used for serving equal to the one used in training. Most silent failures of fine-tuning live here.
- **The memory test** from step 3.
- **A plain optimizer setup**: AdamW with a tuned learning rate and weight decay, a short linear warmup, then a
  linear decay to zero at the last step. A run stopped early therefore ends at a high learning rate: train to the
  planned end.
- **Speed settings worth having from the start** on a recent NVIDIA card: bf16 autocast,
  `torch.set_float32_matmul_precision("high")`, `AdamW(..., fused=True)`. Any further speed or memory change is
  adopted only if time improves by more than timing noise and the score stays inside the noise floor.
- **Checkpoints**: every 15 to 30 minutes of compute on long runs, written atomically, `best` and `last` kept.
  Resuming is proven once before a long run: stop, resume, compare with an uninterrupted run.
- **Then the baseline on three seeds**; five is better. Their spread is the noise floor.

## Step 6. Improve it
- **Scout first.** The agent surveys current methods for your task and writes dated notes with sources into
  `experiments/scouting/`, ending in hypotheses ordered by expected gain times probability, divided by cost.
  Nothing it finds is installed or run. A cited paper is not yet a result in your repository.
- **One hypothesis per change**, on the same seeds and the same budget as the baseline. It is kept when the mean
  improvement over the seed pairs exceeds the noise floor and every pair agrees in sign. Anything else is
  "inconclusive", which is a normal result.
- **Numbers go to a search tool** (Optuna 5.0.0). Learning rate first, on a log scale over two to three decades.
  With fewer than 10 trials tune nothing else. Up to about 30 trials use quasi-random or random sampling. No early
  stopping of trials by default. The training length is never tuned inside a search. The baseline gets the same
  tuning effort as its challenger.
- **The best trial of a search is biased upward.** The top three configurations are trained again on fresh seeds,
  and only those runs decide.
- **A new optimizer or schedule is a hypothesis**, not an upgrade: Muon, Schedule-Free AdamW, SOAP and
  warmup-stable-decay are tested against the tuned AdamW baseline with the same tuning budget, and a winner is
  retrained at full length on at least three seeds.
- **When batch size, GPU count or gradient accumulation changes**, weight decay is re-tuned, not the learning rate
  alone.
- **Cheap runs, seconds to minutes each**: the unattended loop runs this cycle overnight (GUIDE.md, scenario G).
- **When tuning stalls** (general practice): the larger steps are more or cleaner data, a larger starting model,
  or longer training.

## Step 7. More compute, if it pays
- It pays when one run takes hours locally and three seeds plus a search no longer fit your time. The cost of a
  run is measured in Phase 3; a campaign is trials times that cost, plus baseline and confirmation seeds, plus
  retries. Set the spending cap from that estimate.
- The kit's remote module runs the same commands on a machine you reach over ssh or on rented GPUs (GUIDE.md,
  scenario H). The rented route has not run against the real service yet: do its ten-cent canary first.
- Several GPUs in one run work on Linux and WSL2 only, not on native Windows.

## Step 8. Confirm, evaluate once, ship
- **Confirm** the final configuration against the original baseline on seeds that no run has used, as one
  comparison.
- **Freeze** the final procedure (configuration, seeds, training length, checkpoint rule), then run the **one final
  evaluation** through `expctl final-eval`.
- **Report** the mean and spread over seeds with the per-seed values, and keep failed runs in the record. The
  luckiest seed is never the result.
- **Test the file you ship.** A merged, quantised or converted model is a new model: score it with the frozen
  evaluator, check that serving uses the training chat template, and load base revision plus adapter once in a
  fresh process.

## The stack, layer by layer
Pins are the versions read on 11 November 2026. "Tried" means installed at that version in a throwaway
environment and smoke-tested; no row was used for real training there.

| Layer | Use | Status on 11 November 2026 |
|---|---|---|
| Agent | Claude Code with this kit; Codex and Cursor through the kit's ports | Claude Code ran live on native Windows; the two ports are built from documentation and not run live |
| Run control, records, guard, final evaluation | this kit (`expctl`, `runlog.py`, guard hook, journal) | tested on WSL2 and native Windows |
| Environment | uv 0.13.7 with a committed `uv.lock`; `uv sync --locked`, `uv run --frozen` | tried |
| Framework | PyTorch 2.15.0 (Python 3.11 or newer, CUDA 13.2 wheels, NVIDIA driver 580 or newer) | tried: it installs and runs on the CPU, but its first GPU call crashed in WSL2 on the test machine, cause not found; 2.9.1 with CUDA 12.8 trains there. Keep the build your project runs until `python -c "import torch; torch.zeros(1, device='cuda')"` passes on the new one |
| Fine-tuning language models | Transformers 5.22.2, TRL 1.17.1, PEFT 0.21.2, bitsandbytes 0.50.2 | tried: the four install and import together; no model was trained |
| Search | Optuna 5.0.0 | tried: a 15-trial study with SQLite storage |
| Evaluation | your frozen evaluator; lm-evaluation-harness 0.4.13 in its own environment; sacreBLEU 2.6.0 | lm-evaluation-harness installs and starts, no task was run; sacreBLEU gave a score |
| Tracking | the kit's run directories are the record; an existing tracker stays as a mirror; with none, Trackio 0.45.0 as an optional mirror | Trackio is a candidate: it logged locally, not tried as a mirror |
| Library documentation for the agent | Context7 MCP 4.6.0 through `install.py --mcp` | the installer's merge is tested; no connection was made |
| More GPU | `nnremote` over ssh, or Hugging Face Jobs (huggingface_hub 2.4.0) | ssh ran live once; the Jobs route is tested against a stand-in only |

Candidates the kit lists but has not adopted, each with the test it still needs: Unsloth 2026.11.3 (a trainer for
one GPU; the speed and memory figures are the vendor's), Liger Kernel 0.8.5, NePS 0.17.0, Inspect AI 0.3.289.

What not to add, with the kit's reason (`references/stack.md`, "Not recommended"; none of them was tried):
- A hosted tracker or sweep service (W&B, Comet, ClearML) as the authority: a service cannot be the one that
  decides keep or revert, and it showed no gain over local tracking.
- Ray Tune on top of Optuna: no gain on one GPU.
- SkyPilot, dstack, the RunPod MCP server, Vast.ai, Lambda: each puts spending, credentials or the time limit
  outside what the kit's cap, ledger and teardown can check.
- AI-scientist and ML-engineering agent frameworks on top of the coding agent: no advantage at equal time.
- torchtune: no longer maintained.
- A second tool for a job that already has one. The kit's rule is one tracker and one sweep controller.

## Recipes

### A. Fine-tune a chat model on your own examples
You need examples of input and wanted output (about 50 at the least; more is better), split by group into
training, validation and test files, and a rule that scores an answer.
1. Install the kit and fill the Project card (GUIDE.md, scenario D, has a filled one). State the metric, the
   licence limits and the card the model must run on.
2. The agent freezes the evaluator and scores the baseline rows: two or three candidate models untouched, and a
   trivial predictor.
3. It builds the pinned environment and runs the template check and the memory test.
4. LoRA baseline with a learning-rate sweep, then three seeds of the best setting.
5. Hypotheses, one at a time: cleaner or more data, the rank, the number of passes over the data, a larger base
   model in 4 bits against a smaller one in 16.
6. Confirmation on fresh seeds, the one final evaluation, export, and the score of the exported file.

Your decisions on the way: the licence of the base model, the budget, and the final evaluation.

### B. A classifier or a regressor on your own data
1. Split by group or by time, and score the trivial baselines first.
2. General practice: for tables try gradient-boosted trees before a neural network, which often does not beat them
   there; for images, audio or text start from a pretrained network (step 3).
3. The sanity gate; then AdamW with a tuned learning rate, warmup and linear decay, on three seeds.
4. A search over learning rate and weight decay, then the top three configurations on fresh seeds.
5. Decision thresholds and calibration are chosen on validation data only.
6. Confirmation, then the one final evaluation.

### C. A small language model from nothing
- Learn the method on the kit's practice project: a character-level model that trains in 30 seconds
  (`python benchmarks/new_project.py DIR`).
- Give every experiment the same wall-clock budget, keep data, tokenizer and evaluation in files the agent cannot
  edit, and let it edit the training file. The kit's loop does that on your own script; autoresearch does it on
  its own task (GUIDE.md, "Which tool for which job").
- A fixed budget favours changes that are fast, not changes that are best at convergence: test what was kept at
  the real training length before you rely on it.

### D. Further cases, briefly
- Answers ranked by people: preference tuning (step 4).
- A measurable reward: reinforcement-learning post-training (step 4), after supervised fine-tuning has stopped
  paying.
- A smaller or faster model for serving: distillation, quantisation and export are in `references/finetuning.md`;
  the exported file is scored like any other model.

## The mistakes that cost the most
- Looking at the test set more than once, or tuning on it.
- A random split of rows that belong together.
- Comparing two single runs.
- A tuned new method against an untuned baseline.
- A wrong chat template, or loss computed on the wrong tokens.
- Reporting the best trial of a search as the result.
- Several changes at once, so that nobody knows which one worked.
- Scoring the model before export and shipping the one after.
- Changing packages in the middle of a project.
- Loading a checkpoint or dataset file from an unknown source with code execution allowed.
- A rented machine left running: set the time limit and the cap before the start.

## What "the best possible" costs, and when to stop
- Three seeds triple the cost of every decision, and they still miss real gains: with three seeds the kit's loop
  keeps a real gain of two run-to-run deviations only about half the time, in exchange for keeping a useless
  change in about 2 % of cases. A close call that matters needs many more paired runs (about 29) or an honest
  "uncertain".
- Stop tuning when several changes in a row stay inside the noise, when the hypothesis list is used up and a new
  scouting pass finds nothing, or when the budget is spent. A spent budget is not a result.
- After that, the next real gain is rarely a setting. It is more or better data, a larger starting model, or more
  compute (general practice).

## What this guide rests on
- The kit's references with their dates, the admission ledger and the upgrade report. Each rule above is in one
  of them unless it is marked "general practice".
- The stack rows were tried as the table says, on one machine, on 11 November 2026. None was used for a real
  training project there, and the fine-tuning set has not trained a model in the kit's tests.
- No controlled comparison shows that any tool named here, this kit included, produces better models. What the
  evidence supports is the method: trusted measurement, clean data, a good starting model, tuned baselines, seeds.
- Versions, licences and "best current" claims age in weeks. Ask the agent for a fresh scouting pass on your task,
  and treat any reference older than about six months as a list of leads to verify.
