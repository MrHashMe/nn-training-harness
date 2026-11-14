#!/usr/bin/env python3
"""Frozen evaluator of the charlm benchmark: mean next-character cross-entropy (nats) of an exported model.

    python evaluate.py --run-dir DIR [--data data/dev.txt]

The run must have saved DIR/model.ts, a TorchScript module that maps token ids, LongTensor [EVAL_BATCH, BLOCK],
to logits, FloatTensor [EVAL_BATCH, BLOCK, len(VOCAB)]. The loss is computed here from the logits. A TorchScript
file is loaded instead of the run's Python code, and the model must be a function of the token ids alone:
- its code may not read or write files (TorchScript can: torch.from_file); the code is read in the file as
  text, before anything is loaded;
- it keeps nothing between calls: it assigns to no attribute, no weight or buffer changes, and the first batch
  gives the same logits when it is scored again;
- the logits of a row do not depend on the other rows of the batch;
- the logits before a position do not depend on the tokens from that position on, tried at every position.
Rows are scored in a fixed shuffled order, so that no row sits beside the text that follows it.
Prints one JSON line. Exit code 0 only for a valid score; 3 when the model breaks the contract.
"""
import argparse
import json
import math
import re
import sys
import zipfile
from pathlib import Path

VOCAB = "\n !$&',-.3:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"  # the 65 characters of the corpus
BLOCK, EVAL_BATCH = 128, 64
TOL = 1e-3  # the largest difference between two logits that counts as none
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
    try:
        with zipfile.ZipFile(path) as z:
            code = "\n".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if "/code/" in n and n.endswith(".py"))
    except (zipfile.BadZipFile, OSError):
        refuse("model.ts is not a TorchScript file")
    if re.search(r"\btorch\.(?:from_file|save)\s*\(|\bops\.debugprims\b", code):
        refuse("the model's code reads or writes files: a model must be a function of the token ids alone")
    if re.search(r"^\s*self\.\w+\s*=[^=]", code, re.M):
        refuse("the model assigns to its own attributes when it is called: a model must keep nothing between calls")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = torch.jit.load(str(path), map_location=dev).eval()
    state = {k: v.clone() for k, v in model.state_dict().items()}
    ids = torch.tensor(encode((HERE / a.data).read_text(encoding="utf-8")), dtype=torch.long)
    n = (len(ids) - 1) // BLOCK
    if n < EVAL_BATCH:
        refuse(f"{a.data} is too short to evaluate on")
    order = torch.randperm(n, generator=torch.Generator().manual_seed(0))
    x, y = ids[:n * BLOCK].view(n, BLOCK)[order], ids[1:n * BLOCK + 1].view(n, BLOCK)[order]

    def logits_of(xb):
        out = model(xb.to(dev))
        if tuple(out.shape) != (EVAL_BATCH, BLOCK, len(VOCAB)) or not bool(torch.isfinite(out).all()):
            refuse(f"logits must be finite with shape {(EVAL_BATCH, BLOCK, len(VOCAB))}, got {tuple(out.shape)}")
        return out.double().cpu()

    total, first = 0.0, None
    with torch.no_grad():
        for i in range(0, n, EVAL_BATCH):
            xb = x[i:i + EVAL_BATCH]
            k = xb.shape[0]
            if k < EVAL_BATCH:  # the export has a fixed batch shape: fill up and ignore the filler rows
                xb = torch.cat([xb, x[:EVAL_BATCH - k]])
            logits = logits_of(xb)
            first = logits if first is None else first  # the probes below are compared with a batch that was scored
            total -= torch.log_softmax(logits[:k], -1).gather(-1, y[i:i + k].unsqueeze(-1)).sum().item()
        x0, rows, pos = x[:EVAL_BATCH], torch.arange(EVAL_BATCH), torch.arange(BLOCK)
        drift = (logits_of(x0) - first).abs().max().item()
        xr = x0.clone()
        xr[1::2] = x0[0::2].flip(0)  # every second row gives way to another row's text
        cross = (logits_of(xr)[0::2] - first[0::2]).abs().max().item()
        leak, donor = 0.0, x0.roll(1, 0)
        for p in (0, 1):  # each row has its own cut, and the two passes together try every position
            cuts = 1 + (2 * rows + p) % (BLOCK - 1)
            after = pos[None, :] >= cuts[:, None]
            xc = torch.where(after, donor, x0)  # from the cut on another row's text: a probe reads like any scored row
            xc[rows, cuts] = torch.where(xc[rows, cuts] == x0[rows, cuts], (x0[rows, cuts] + 1) % len(VOCAB), xc[rows, cuts])
            leak = max(leak, ((logits_of(xc) - first).abs() * ~after[..., None]).max().item())
    if not drift < TOL or any(not torch.equal(v, model.state_dict()[k]) for k, v in state.items()):
        refuse(f"the model does not answer the same batch the same way twice (max difference {drift:.3g}), or its "
               f"weights or buffers changed: a model must keep nothing between calls")
    if not cross < TOL:
        refuse(f"the logits of a row change when other rows of the batch change (max difference {cross:.3g})")
    if not leak < TOL:
        refuse(f"logits before a position change when the tokens from it on change (max difference {leak:.3g}): "
               f"the model looks ahead")
    score = total / (n * BLOCK)
    if not math.isfinite(score):
        refuse("the loss is not finite")
    print(json.dumps({"score": score, "metric": "loss_nats_per_char", "data": a.data, "tokens": n * BLOCK,
                      "causal_max_diff": leak, "row_max_diff": cross, "repeat_max_diff": drift}))


if __name__ == "__main__":
    main()
