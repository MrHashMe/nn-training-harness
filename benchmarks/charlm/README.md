# charlm: a small language-model benchmark

Train a character-level transformer on Tiny Shakespeare for 30 seconds and get the lowest next-character loss.
It exists to try the kit and its unattended loop on real training in minutes, and to compare agents with and
without the kit (`../pilot.py`). It is not a research benchmark: 30 seconds of training on one GPU, one small text.

| | |
|---|---|
| Train | `python train.py --seed 1 --time-budget 30` (needs PyTorch; a GPU is used when there is one) |
| Score | `python evaluate.py --run-dir RUN [--data data/dev.txt]`: mean cross-entropy in nats per character, lower is better |
| Contract | a run saves `RUN/model.ts`, a TorchScript module that maps token ids `[64, 128]` to logits `[64, 128, 65]`. The evaluator computes the loss itself and scores a model only as a function of each row's earlier tokens: it refuses one whose logits depend on later tokens (tried at every position) or on other rows of the batch, and one whose code reads or writes files (TorchScript can: every code entry of the file is read as tokens before anything is loaded, and what is loaded is an archive that the evaluator writes from the entries it read). Every call goes to a freshly loaded copy, so that nothing a model keeps reaches its next call. These are checks of what the file says and does, not a sandbox around it |
| Baseline | `train.py` as shipped: 4 layers, width 192, AdamW 3e-4, batch 64 |
| Controls | `controls.py`: two runs that cannot have learned the text. `constant` gives every character the same probability, a loss of ln 65 = 4.174. `shuffled` runs `train.py` on the training text with its characters in random order; what that learns cannot score below 3.300, the entropy of the character frequencies in `loopval.txt`. The loop trains both before a campaign's first agent session and stops if the evaluator scores one better than that (`loop.controls`) |

## Data

`data/` holds one text cut into four pieces by position (never shuffled, so no passage is in two pieces):

| File | Characters | Use |
|---|---|---|
| `train.txt` | 892,315 | training |
| `dev.txt` | 66,923 | the agent's own validation; `train.py` prints its loss |
| `loopval.txt` | 78,078 | sealed; the loop's evaluator scores here, so the agent cannot tune on the number that decides |
| `test.txt` | 78,078 | sealed; final evaluation only |

Source: Tiny Shakespeare, 1,115,394 characters, as distributed with char-rnn
(github.com/karpathy/char-rnn, `data/tinyshakespeare/input.txt`; repository under the MIT license, the text itself
is in the public domain). Fetched 11 November 2026; SHA-256 of the whole file
`86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed`.

## Use

```bash
python benchmarks/new_project.py ~/charlm-demo
```

creates a fresh git project from this folder with the kit installed and the settings of `nn-training.task.json`
merged into `.claude/nn-training.json` (sealed and frozen paths, the final evaluation command, the `loop` section).
`--no-kit` leaves the kit out, `--kit-dir DIR` installs another version of it. In that project:

```bash
python .claude/skills/nn-training/scripts/nnloop.py start --campaign first --agent claude --max-runs 14
```

runs the unattended loop: three baseline runs (seeds 1 to 3), the two control runs, a scouting session, then
iterations until fourteen runs are used. Once a change is kept, the loop holds back six of those runs, if the
limit still has them, for the confirmation on fresh seeds that ends the campaign (`references/loop.md`). The
final evaluation is yours to run, once, at the end:

```bash
python .claude/skills/nn-training/scripts/expctl.py final-eval -- runs/RUN
```

It runs `evaluate.py --data data/test.txt --run-dir runs/RUN` and writes a receipt; a second use is refused unless
`--again "reason"` says why.

## Faster training code and the model file

The model file is TorchScript because the evaluator must not run a run's Python code: it reads the file's code as
text, refuses what a model must not do, and only then loads it. What that means for speed-ups, tried with
PyTorch 2.9.1 on 15 November 2026:

- `torch.compile`: train with the compiled model, save the plain one. `torch.jit.trace` of a compiled model fails
  ("Detected that you are using FX to torch.jit.trace a dynamo-optimized function"), so `train.py` traces the
  module inside the wrapper, which holds the same weights and scored the same (`tests/test_benchmarks.py` saves
  one that way). Once compiled, the training step alone ran 16 % faster: 189.0 steps a second against 162.4 (WSL,
  one RTX 5090, a fixed batch of 64). Compiling comes first: the first call took 1.4 s in one session and 4.8 s
  in another, and the first 5 s after it ran at 125.6 steps a second, because the backward pass is compiled at
  its first use. For a 30 s run that works out at about 4 % more steps or 9 % fewer, by arithmetic from these
  figures and not by a timed run.
- A hand-written `torch.autograd.Function` (a kernel with a backward of its own) in the forward: saving the trace
  fails ("Could not export Python function call"). Call it while `self.training` only, and give the other branch
  the same arithmetic in plain operations: `train.py` traces after `model.eval()`. A model built that way is
  scored like the same model in plain code (`tests/test_benchmarks.py`).
- Code that TorchScript runs while a file is loaded (`__setstate__`): PyTorch runs it in `torch.jit.load`. The
  evaluator refuses such a file before it loads anything, if that code names a file operation (same test file).
- Not offered: a Python model definition beside a file of weights. The evaluator would have to run the run's own
  code, or the definition would be frozen and the architecture with it. `torch.export` took the model with a
  hand-written function in its forward, and the saved program gave the same logits after loading; PyTorch 2.9.1
  marks its file format as under active development ("saved files may not be usable in newer versions"), and
  the evaluator's checks have not been tried on it.

## Changes to the evaluator

14 November 2026. The check for file reads looked for the text `torch.from_file(` in the code folder of the
model file. PyTorch 2.9.1 also loads that call written with blanks (`torch . from_file(`), through `getattr` with
a name joined from two strings, from a folder named `Code/`, from a second entry of the same name, and from a
second directory of the file that Python's `zipfile` does not read; the evaluator scored such a file. It now
reads every code entry as tokens and loads an archive it writes itself from the entries it read. A model that
keeps something between calls was refused where the evaluator saw an assignment to an attribute or a changed
buffer; it is now scored as on its first call, because every call goes to a freshly loaded copy, which also
covers what those two checks did not see (a list or a dictionary that grows). The score of a model that passed
before is the same number: `train.py` as shipped, trained for three seconds, gave 2.1732656613119863 under both.
The pickle entries of a model file are no second way in: `torch.jit.load` reads them with a reader of its own,
and a pickle that creates a file when Python loads it created none in any entry (36 files, PyTorch 2.9.1, tried on
14 November 2026; `tests/test_benchmarks.py` repeats this with the PyTorch that runs the tests).
Not covered: a file operation that a later PyTorch adds to TorchScript, and a model with a method or attribute
named `save` or `from_file`, which is refused. A project created before this date keeps its own copy of the old
`evaluate.py`; copying the new one in changes a frozen file, so it starts a new protocol version
(`references/validity.md`, section 6).
