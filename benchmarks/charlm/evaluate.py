#!/usr/bin/env python3
"""Frozen evaluator of the charlm benchmark: mean next-character cross-entropy (nats) of an exported model.

    python evaluate.py --run-dir DIR [--data data/dev.txt]

The run must have saved DIR/model.ts, a TorchScript module that maps token ids, LongTensor [EVAL_BATCH, BLOCK],
to logits, FloatTensor [EVAL_BATCH, BLOCK, len(VOCAB)]. The loss is computed here from the logits. A TorchScript
file is loaded instead of the run's Python code, and the model must be a function of the token ids alone:
- its code may not read or write files (TorchScript can: torch.from_file). Before anything is loaded, every
  .py entry of the file is read as tokens, so that neither spacing nor a name put together from strings
  (getattr(torch, "from_" "file")) hides such a call; what is loaded is an archive written here from the entries
  that were read, and its graph is read as well;
- it keeps nothing between calls: every call goes to a freshly loaded copy, and the first batch must give the
  same logits when it is scored again;
- the logits of a row do not depend on the other rows of the batch;
- the logits before a position do not depend on the tokens from that position on, tried at every position.
Rows are scored in a fixed shuffled order, so that no row sits beside the text that follows it.
These are checks of what the file says and does, not a sandbox around it.
Prints one JSON line. Exit code 0 only for a valid score; 3 when the model breaks the contract.
"""
import argparse
import ast
import io
import json
import math
import re
import sys
import tokenize
import zipfile
from pathlib import Path

VOCAB = "\n !$&',-.3:;?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"  # the 65 characters of the corpus
BLOCK, EVAL_BATCH = 128, 64
TOL = 1e-3  # the largest difference between two logits that counts as none
HERE = Path(__file__).resolve().parent
_STOI = {c: i for i, c in enumerate(VOCAB)}
FILE_OPS = ("from_file", "save", "debugprims")  # TorchScript's ways to a file: torch.from_file, torch.save, ops.debugprims


def encode(text):
    return [_STOI[c] for c in text]


def refuse(msg):
    print(json.dumps({"error": msg}))
    sys.exit(3)


def file_op(code):
    """The way to a file that a code file of the model names, None when it names none, "" when it cannot be read as
    code. Read as tokens: `torch . from_file(` is the same call as `torch.from_file(`, and so is
    getattr(torch, "from_" "file"), whose literals TorchScript joins as Python does."""
    try:
        toks = [t for t in tokenize.generate_tokens(io.StringIO(code).readline)
                if t.type not in (tokenize.NL, tokenize.COMMENT)]
        text = ""
        for t, nxt in zip(toks, toks[1:] + [None]):
            if t.type == tokenize.ERRORTOKEN:  # text that Python cannot read, PyTorch may read in a way of its own
                return ""
            if t.type == tokenize.NAME and t.string in FILE_OPS:
                return t.string
            if t.type == tokenize.STRING:
                text += str(ast.literal_eval(t.string))
                if nxt is None or nxt.type != tokenize.STRING:
                    if text in FILE_OPS:
                        return text
                    text = ""
    except (tokenize.TokenError, SyntaxError, ValueError):
        return ""
    return None


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
            entries = [(i.filename, z.read(i)) for i in z.infolist()]  # every entry, also a second one of the same name
    except Exception:  # noqa: BLE001  whatever zipfile cannot take apart is no model
        refuse("model.ts is not a TorchScript file")
    # PyTorch finds an entry whatever the case of its name: code/ is Code/ to it, and .py is .PY
    ops = [file_op(d.decode("utf-8", "replace")) for n, d in entries if n.lower().endswith(".py")]
    if "" in ops:
        refuse("the model's code cannot be read as code: it must be what torch.jit.save writes")
    if any(ops):
        refuse(f"the model's code reads or writes files ({next(o for o in ops if o)}): a model must be a function of "
               f"the token ids alone")
    # What is loaded is an archive written here from the entries that were read: a file that PyTorch's reader would
    # take apart in another way than zipfile did (a second directory, another spelling of a name) cannot hand it code
    # that was not read. shortcut: the model is held in memory twice, fine for this task's few megabytes
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, d in entries:
            z.writestr(n, d)
    blob = buf.getvalue()
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    def load():
        return torch.jit.load(io.BytesIO(blob), map_location=dev).eval()

    if re.search(r"\baten::(?:from_file|save)\b|\bdebugprims::", str(load().inlined_graph)):
        refuse("the model's code reads or writes files: a model must be a function of the token ids alone")
    ids = torch.tensor(encode((HERE / a.data).read_text(encoding="utf-8")), dtype=torch.long)
    n = (len(ids) - 1) // BLOCK
    if n < EVAL_BATCH:
        refuse(f"{a.data} is too short to evaluate on")
    order = torch.randperm(n, generator=torch.Generator().manual_seed(0))
    x, y = ids[:n * BLOCK].view(n, BLOCK)[order], ids[1:n * BLOCK + 1].view(n, BLOCK)[order]

    def logits_of(xb):  # by a freshly loaded copy: whatever a model keeps (an attribute, a buffer, a list that grows)
        out = load()(xb.to(dev))  # does not reach its next call
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
    if not drift < TOL:
        refuse(f"the model does not answer the same batch the same way twice (max difference {drift:.3g}): a model "
               f"must be a function of the token ids alone")
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
