#!/usr/bin/env python3
"""Baseline trainer of the charlm benchmark: a small character-level transformer trained for a fixed time.

    python train.py --seed 1 --time-budget 30

Plain on purpose: it is the starting point that an agent improves. The contract it must keep (see README.md):
train on data/train.txt only, stop training after --time-budget seconds, and save model.ts into the run
directory ($EXP_RUN_DIR, else --out) in the form evaluate.py loads.
"""
import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import BLOCK, EVAL_BATCH, VOCAB, encode  # noqa: E402

# `expctl launch` runs a copy of the source that has no .claude: the project it was started from is looked at too
for _p in (HERE / ".claude" / "skills" / "nn-training" / "scripts", HERE / "tools",
           Path(os.environ.get("EXP_PROJECT_ROOT") or HERE) / ".claude" / "skills" / "nn-training" / "scripts"):
    if (_p / "runlog.py").is_file():  # the harness's run logger, when the kit is installed
        sys.path.insert(0, str(_p))
        break
try:
    from runlog import RunLog
except ImportError:
    RunLog = None


class Block(nn.Module):
    def __init__(self, dim, heads, dropout):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(dim), nn.LayerNorm(dim)
        self.qkv, self.proj = nn.Linear(dim, 3 * dim), nn.Linear(dim, dim)
        self.mlp = nn.Sequential(nn.Linear(dim, 4 * dim), nn.GELU(), nn.Linear(4 * dim, dim))
        self.heads, self.drop = heads, nn.Dropout(dropout)

    def forward(self, x):
        b, t, c = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(b, t, 3, self.heads, c // self.heads).permute(2, 0, 3, 1, 4).unbind(0)
        att = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.drop(self.proj(att.transpose(1, 2).reshape(b, t, c)))
        return x + self.drop(self.mlp(self.ln2(x)))


class LM(nn.Module):
    def __init__(self, vocab, dim=192, layers=4, heads=4, dropout=0.1):
        super().__init__()
        self.tok, self.pos = nn.Embedding(vocab, dim), nn.Embedding(BLOCK, dim)
        self.blocks = nn.ModuleList([Block(dim, heads, dropout) for _ in range(layers)])
        self.ln, self.head = nn.LayerNorm(dim), nn.Linear(dim, vocab)

    def forward(self, idx):
        x = self.tok(idx) + self.pos(torch.arange(idx.shape[1], device=idx.device))
        for blk in self.blocks:
            x = blk(x)
        return self.head(self.ln(x))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=int(os.environ.get("EXP_SEED") or 1))
    ap.add_argument("--time-budget", type=float, default=30.0, help="seconds of training")
    ap.add_argument("--out", default=os.environ.get("EXP_RUN_DIR") or "out")
    a = ap.parse_args()
    torch.manual_seed(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = {k: torch.tensor(encode((HERE / "data" / f"{k}.txt").read_text(encoding="utf-8")), device=dev)
            for k in ("train", "dev")}
    span = torch.arange(BLOCK, device=dev)

    def batch(split, size):
        d = data[split]
        ix = torch.randint(len(d) - BLOCK - 1, (size, 1), device=dev)
        return d[ix + span], d[ix + span + 1]

    model = LM(len(VOCAB)).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)

    @torch.no_grad()
    def dev_loss(batches=20):
        model.eval()
        gen = torch.Generator(device=dev).manual_seed(0)
        d = data["dev"]
        losses = []
        for _ in range(batches):
            ix = torch.randint(len(d) - BLOCK - 1, (EVAL_BATCH, 1), device=dev, generator=gen)
            losses.append(F.cross_entropy(model(d[ix + span]).flatten(0, 1), d[ix + span + 1].flatten()).item())
        model.train()
        return sum(losses) / len(losses)

    log = (RunLog(config=vars(a), seed=a.seed, metric="dev/loss", direction="minimize")
           if RunLog and os.environ.get("EXP_RUN_DIR") else contextlib.nullcontext())
    with log as rl:
        t0, step = time.time(), 0
        while time.time() - t0 < a.time_budget:
            x, y = batch("train", 64)
            loss = F.cross_entropy(model(x).flatten(0, 1), y.flatten())
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            step += 1
            if step % 250 == 0:
                dl = dev_loss()
                print(f"step {step}  train {loss.item():.4f}  dev {dl:.4f}  {time.time() - t0:.0f}s", flush=True)
                if rl:
                    rl.log(step, **{"train/loss": loss.item(), "dev/loss": dl})
        dl = dev_loss()
        if rl:
            rl.log(step, **{"dev/loss": dl})
        model.eval()
        example = torch.zeros(EVAL_BATCH, BLOCK, dtype=torch.long, device=dev)
        torch.jit.trace(model, example).save(str(out / "model.ts"))
        if rl:  # names the saved model as the run's result: without it `expctl status` lists no best run
            rl.checkpoint(out / "model.ts", step=step, value=dl, is_best=True)
        print(json.dumps({"dev_loss": dl, "steps": step, "seconds": round(time.time() - t0, 1)}), flush=True)


if __name__ == "__main__":
    main()
