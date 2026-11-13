#!/usr/bin/env python3
"""Frozen evaluator of the charlm benchmark: mean next-character cross-entropy (nats) of an exported model.

    python evaluate.py --run-dir DIR [--data data/dev.txt]

The run must have saved DIR/model.ts, a TorchScript module that maps token ids, LongTensor [EVAL_BATCH, BLOCK],
to logits, FloatTensor [EVAL_BATCH, BLOCK, len(VOCAB)]. The loss is computed here from the logits, and a probe
checks that the logits of a position do not depend on later tokens. A TorchScript file is loaded instead of the
run's Python code so that a model cannot open the held-out file itself.
Prints one JSON line. Exit code 0 only for a valid score; 3 when the model breaks the contract.
"""
import argparse
import json
import math
import sys
from pathlib import Path

VOCAB = "\n !$&',-.3:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"  # the 65 characters of the corpus
BLOCK, EVAL_BATCH = 128, 64
HERE = Path(__file__).resolve().parent
_STOI = {c: i for i, c in enumerate(VOCAB)}


def encode(text):
    return [_STOI[c] for c in text]


def refuse(msg):
    print(json.dumps({"error": msg}))
    sys.exit(3)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--data", default="data/dev.txt", help="text file to score on, relative to this file")
    a = ap.parse_args()
    import torch

    path = Path(a.run_dir) / "model.ts"
    if not path.is_file():
        refuse("the run saved no model.ts")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = torch.jit.load(str(path), map_location=dev).eval()
    ids = torch.tensor(encode((HERE / a.data).read_text(encoding="utf-8")), dtype=torch.long)
    n = (len(ids) - 1) // BLOCK
    if n < EVAL_BATCH:
        refuse(f"{a.data} is too short to evaluate on")
    x, y = ids[:n * BLOCK].view(n, BLOCK), ids[1:n * BLOCK + 1].view(n, BLOCK)
    total = 0.0
    with torch.no_grad():
        for i in range(0, n, EVAL_BATCH):
            xb = x[i:i + EVAL_BATCH]
            k = xb.shape[0]
            if k < EVAL_BATCH:  # the export has a fixed batch shape: fill up and ignore the filler rows
                xb = torch.cat([xb, x[:EVAL_BATCH - k]])
            logits = model(xb.to(dev))
            if tuple(logits.shape) != (EVAL_BATCH, BLOCK, len(VOCAB)) or not bool(torch.isfinite(logits).all()):
                refuse(f"logits must be finite with shape {(EVAL_BATCH, BLOCK, len(VOCAB))}, got {tuple(logits.shape)}")
            logp = torch.log_softmax(logits[:k].double().cpu(), -1)
            total -= logp.gather(-1, y[i:i + k].unsqueeze(-1)).sum().item()
        cut = BLOCK // 2
        xa = x[:EVAL_BATCH].clone()
        xb = xa.clone()
        xb[:, cut:] = torch.randint(0, len(VOCAB), (EVAL_BATCH, BLOCK - cut), generator=torch.Generator().manual_seed(0))
        leak = (model(xa.to(dev))[:, :cut] - model(xb.to(dev))[:, :cut]).abs().max().item()
    if not leak < 1e-3:
        refuse(f"logits before position {cut} change when later tokens change (max difference {leak:.3g}): "
               f"the model looks ahead")
    score = total / (n * BLOCK)
    if not math.isfinite(score):
        refuse("the loss is not finite")
    print(json.dumps({"score": score, "metric": "loss_nats_per_char", "data": a.data, "tokens": n * BLOCK,
                      "causal_max_diff": leak}))


if __name__ == "__main__":
    main()
