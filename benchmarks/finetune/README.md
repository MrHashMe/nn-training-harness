# finetune: a small fine-tuning benchmark for a language model

Fine-tune a small chat model for 30 seconds so that it names the intent of a customer's message to a bank, and
get the highest share of held-out messages answered with exactly the right name. It is the second task beside
`../charlm/`: the same kit, loop and pilot (`../pilot.py --task finetune`) on a fine-tuning run instead of a model
trained from scratch. It is not a research benchmark: 30 seconds on one GPU, one small model, one dataset.

| | |
|---|---|
| Needs | PyTorch, Transformers and PEFT in the Python that runs it (the kit's core needs none of them), and the base model: `python fetch_model.py`, 270 MB, once |
| Train | `python train.py --seed 1 --time-budget 30` (a GPU is used when there is one) |
| Score | `python evaluate.py --run-dir RUN [--data data/dev.txt]`: share of the messages whose intent the model names exactly, higher is better |
| Contract | a run saves `RUN/adapter/`: a LoRA adapter in PEFT's format (`adapter_config.json`, `adapter_model.safetensors`) for the base model in `model/`. The evaluator puts it on its own copy of the base model, asks with its own prompt in the model's chat format and compares the greedy answer with the intent's name. It loads no other weight format, refuses an adapter whose files lie outside the run folder (a link) and a config that sets keys beyond a plain LoRA adapter's (some name a library for PEFT to import), so it executes nothing a run saved |
| Baseline | `train.py` as shipped: LoRA of rank 8 on the query and value projections, AdamW 2e-4, batch 32, the loss on the answer only. A plain PyTorch loop, because a fixed time budget needs a loop that watches the clock |

Measured on 12 November 2026 (RTX 5090, Windows 11, Python 3.11, PyTorch 2.9.1, Transformers 5.22.2, PEFT 0.21.2,
the versions `references/finetuning.md` names): the baseline makes about 360 steps and scores 0.372, 0.386 and
0.351 on `loopval.txt` with seeds 1, 2 and 3. A run takes 44 seconds in all, the evaluator 16. The same script
with a learning rate of 1e-3 scored 0.691 with seed 1, so the baseline leaves room. The score moves with the
number of steps that fit into the 30 seconds: under the loop, with 353 steps, the same three seeds scored 0.349,
0.364 and 0.335.

One campaign of `nnloop.py` ran on a project made from this folder, with the stand-in agent of the kit's tests in
place of a real one (12 runs, 13 minutes): the learning rate of 1e-3 was kept (0.684 against 0.349 over the three
seeds, a margin of 0.025) and confirmed on three fresh seeds (0.667 against 0.332). That shows that the task runs
under the loop, not what an agent reaches on it: no real agent session and no run of `pilot.py` has been made on
this task. Not run on Linux, on other versions of the libraries or without a GPU.

If a run fails at once with `module 'bitsandbytes' has no attribute 'nn'`, the Python that runs it holds the
remains of a removed `bitsandbytes` (an empty folder in its site-packages), and PEFT takes that for the installed
package. Use a fresh virtual environment, or remove the folder. Seen on 13 November 2026 with PEFT 0.21.2.

## Data

`data/` holds Banking77 in four files, one message per line with its intent after a tab:

| File | Rows | Bytes | Use |
|---|---|---|---|
| `train.txt` | 9,488 | 782,175 | training |
| `dev.txt` | 500 | 42,539 | the agent's own validation; `train.py` prints its score |
| `loopval.txt` | 1,000 | 75,721 | sealed; the loop's evaluator scores here, so the agent cannot tune on the number that decides |
| `test.txt` | 1,000 | 78,455 | sealed; final evaluation only |

Source: Banking77, 13,083 messages with one of 77 intents, from github.com/PolyAI-LDN/task-specific-datasets at
commit `9d081458ff52e53cf7e848f414e6e9344e4e6696`: `banking_data/train.csv` (10,003 rows, SHA-256
`b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`) and `banking_data/test.csv` (3,080 rows,
SHA-256 `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d`). Licence: CC BY 4.0. Fetched
12 November 2026. Cite it as: Casanueva, Temcinas, Gerz, Henderson, Vulic, "Efficient Intent Detection with Dual
Sentence Encoders", 2020, arXiv 2003.04807.

Changes made to it: runs of whitespace in a message became one blank. The 24 rows whose message occurs more than
once were dropped (12 messages, 7 of them in both source files, so in training and test at once). The rows of
each source file were shuffled with Python's `random.Random(77)`. `dev.txt` is the first 500 rows of the shuffled
`train.csv` and `train.txt` the other 9,488; `loopval.txt` is the first 1,000 rows of the shuffled `test.csv` and
`test.txt` the next 1,000; its last 1,071 rows are not used. Every file has all 77 intents.

The dataset is public and older than the base model, which may have seen it in training. The sealed files keep an
agent from tuning on the messages that decide; they do not make the dataset unknown.

## Base model

`HuggingFaceTB/SmolLM2-135M-Instruct` at revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`: 135 million
parameters, Apache-2.0, not gated (checked on the Hugging Face Hub on 12 November 2026). `fetch_model.py` downloads
its six files into `model/` without a login, using the standard library only, and keeps a file only when its size
and SHA-256 are the ones recorded in the script. Training and evaluation then run offline.

`model/` is git-ignored. In a project it is frozen (`frozen_paths`), so the agent cannot change it, and the loop
links it into its worktree (`loop.link_paths`) and checksums it with the evaluator. The prompt is the one in
`evaluate.py`, rendered with the model's chat template; `evaluate.py` also checks that the template renders a
training text as that prompt followed by the answer, and `train.py` builds its training texts through that check.

## Use

```bash
python benchmarks/finetune/fetch_model.py
```

```bash
python benchmarks/new_project.py ~/finetune-demo --task finetune
```

The first command fetches the base model into this folder; a project created afterwards gets a copy of it (in a
project created before, run its own `fetch_model.py`). Use the Python that has the three libraries: the
interpreter that runs `new_project.py` is the one the project's kit and its training runs use, unless
`--python-cmd` names another. The project is made as for charlm (`../charlm/README.md`), and the loop and the
final evaluation are started with the same two commands:

```bash
python .claude/skills/nn-training/scripts/nnloop.py start --campaign first --agent claude --max-runs 12
```

```bash
python .claude/skills/nn-training/scripts/expctl.py final-eval -- runs/RUN
```

`python benchmarks/pilot.py WORKDIR --task finetune` compares arms on this task. It needs the model fetched into
this folder, and `python` on PATH, which the agent sessions call, must have the three libraries too.
