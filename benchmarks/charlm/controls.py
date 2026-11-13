#!/usr/bin/env python3
"""Negative controls of the charlm benchmark: runs that cannot have learned the text. The loop's self-test trains
each one before a campaign's first agent session, and stops if the evaluator scores one better than its floor
(loop.controls in nn-training.task.json; references/loop.md of the kit).

    python controls.py constant                 a model that gives every character the same probability
    python controls.py shuffled --seed 1 ...    train.py as it is, on the training text with its characters shuffled

Each saves model.ts where train.py does: in $EXP_RUN_DIR, else in out/.
"""
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def constant(out):
    """The same logits everywhere: a loss of ln(65) = 4.174 nats on any text, whatever the evaluator reads."""
    import torch
    from evaluate import BLOCK, EVAL_BATCH, VOCAB

    class Constant(torch.nn.Module):
        def forward(self, idx):
            return (idx * 0).unsqueeze(-1).expand(-1, -1, len(VOCAB)).float()

    torch.jit.trace(Constant(), torch.zeros(EVAL_BATCH, BLOCK, dtype=torch.long)).save(str(out / "model.ts"))


def shuffled(out, argv):
    """train.py in a copy of the task whose training text has its characters in random order, so that all it can
    learn is how often each character occurs. No such predictor scores below the entropy of the scored text's own
    character frequencies: 3.300 nats on data/loopval.txt."""
    box = out / "shuffled"
    (box / "data").mkdir(parents=True)
    for n in ("train.py", "evaluate.py", "data/dev.txt"):
        shutil.copy2(HERE / n, box / n)
    chars = list((HERE / "data" / "train.txt").read_text(encoding="utf-8"))
    random.Random(0).shuffle(chars)
    with open(box / "data" / "train.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(chars))
    code = subprocess.run([sys.executable, str(box / "train.py"), *argv, "--out", str(out)], cwd=str(box)).returncode
    shutil.rmtree(box, ignore_errors=True)
    return code


if __name__ == "__main__":
    if sys.argv[1:2] not in (["constant"], ["shuffled"]):
        sys.exit(__doc__)
    out = Path(os.environ.get("EXP_RUN_DIR") or "out").resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.exit(constant(out) if sys.argv[1] == "constant" else shuffled(out, sys.argv[2:]))
