#!/usr/bin/env python3
"""Negative control of the finetune benchmark: a run that cannot have learned which intent a message has. The
loop's self-test trains it before a campaign's first agent session, and stops if the evaluator scores it better
than its floor (loop.controls in nn-training.task.json; references/loop.md of the kit).

    python controls.py shuffled --seed 1 ...    train.py as it is, on the training messages with their intents
                                                dealt out again at random

It saves adapter/ where train.py does: in $EXP_RUN_DIR, else in out/.
"""
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import read  # noqa: E402


def shuffled(out, argv):
    """train.py in a copy of the task whose training messages carry each other's intents, so that all it can learn
    is the form of an answer and how often each intent occurs. The base model knew English before, so the score
    has no bound from theory: the floor in nn-training.task.json is measured (README.md)."""
    box = out / "shuffled"
    (box / "data").mkdir(parents=True)
    shutil.copy2(HERE / "train.py", box / "train.py")
    shutil.copy2(HERE / "data" / "dev.txt", box / "data" / "dev.txt")
    pairs = read(HERE / "data" / "train.txt")
    intents = [c for _, c in pairs]
    random.Random(0).shuffle(intents)
    with open(box / "data" / "train.txt", "w", encoding="utf-8", newline="\n") as f:
        f.writelines(f"{t}\t{c}\n" for (t, _), c in zip(pairs, intents))
    # the copy has no evaluate.py: train.py imports this folder's, which finds the base model in model/
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(HERE), os.environ.get("PYTHONPATH")])))
    code = subprocess.run([sys.executable, str(box / "train.py"), *argv, "--out", str(out)], cwd=str(box),
                          env=env).returncode
    shutil.rmtree(box, ignore_errors=True)
    return code


if __name__ == "__main__":
    if sys.argv[1:2] != ["shuffled"]:
        sys.exit(__doc__)
    out = Path(os.environ.get("EXP_RUN_DIR") or "out").resolve()
    out.mkdir(parents=True, exist_ok=True)
    sys.exit(shuffled(out, sys.argv[2:]))
