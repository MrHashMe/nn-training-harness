#!/usr/bin/env python3
"""Baseline trainer of the fine-tuning benchmark: a LoRA adapter for the small chat model in model/, trained for a
fixed time to name the intent of a message to a bank's support.

    python train.py --seed 1 --time-budget 30

Plain on purpose: it is the starting point that an agent improves. The contract it must keep (see README.md):
train on data/train.txt only, stop training after --time-budget seconds, and save a PEFT LoRA adapter for the
base model into adapter/ of the run directory ($EXP_RUN_DIR, else --out), in the form evaluate.py loads. The
prompt comes from evaluate.py, which also checks the chat template.
"""
import argparse
import contextlib
import json
import os
import random
import sys
import time
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import answer_part, exact, load_base, prompt, read  # noqa: E402

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

LR = 2e-4
BATCH = 32


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--seed", type=int, default=int(os.environ.get("EXP_SEED") or 1))
    ap.add_argument("--time-budget", type=float, default=30.0, help="seconds of training")
    ap.add_argument("--out", default=os.environ.get("EXP_RUN_DIR") or "out")
    a = ap.parse_args()
    random.seed(a.seed)
    torch.manual_seed(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    model, tok = load_base()
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "v_proj"],
                                             task_type="CAUSAL_LM")).to(dev)
    params = [p for p in model.parameters() if p.requires_grad]
    if not params:
        sys.exit("nothing to train: the adapter matched no module of the base model")
    print(f"trainable parameters: {sum(p.numel() for p in params):,}", flush=True)
    opt = torch.optim.AdamW(params, lr=LR)

    # a training text is the prompt's tokens followed by the answer's; the loss counts the answer only
    pairs = read(HERE / "data" / "train.txt")
    heads = tok([prompt(tok, t) for t, _ in pairs], add_special_tokens=False)["input_ids"]
    tails = tok([answer_part(tok, t, c) for t, c in pairs], add_special_tokens=False)["input_ids"]
    train = [(h + t, [-100] * len(h) + t) for h, t in zip(heads, tails)]
    order = []

    def batch():
        if len(order) < BATCH:
            order.extend(random.sample(range(len(train)), len(train)))
        rows = [train[order.pop()] for _ in range(BATCH)]
        width = max(len(x) for x, _ in rows)
        ids = torch.tensor([x + [tok.pad_token_id] * (width - len(x)) for x, _ in rows], device=dev)
        labels = torch.tensor([y + [-100] * (width - len(y)) for _, y in rows], device=dev)
        mask = torch.tensor([[1] * len(x) + [0] * (width - len(x)) for x, _ in rows], device=dev)
        return ids, mask, labels

    log = (RunLog(config=dict(vars(a), lr=LR, batch=BATCH), seed=a.seed, metric="dev/exact", direction="maximize")
           if RunLog and os.environ.get("EXP_RUN_DIR") else contextlib.nullcontext())
    with log as rl:
        model.train()
        t0, step = time.time(), 0
        # `expctl stop` or the launch's deadline ends the loop early; what follows still scores and saves the adapter
        while time.time() - t0 < a.time_budget and not (rl and rl.should_stop()):
            ids, mask, labels = batch()
            loss = model(input_ids=ids, attention_mask=mask, labels=labels).loss
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            step += 1
            if step % 50 == 0:
                print(f"step {step}  train {loss.item():.4f}  {time.time() - t0:.0f}s", flush=True)
                if rl:
                    rl.log(step, **{"train/loss": loss.item()})
        seconds = round(time.time() - t0, 1)
        model.eval()
        score = exact(model, tok, read(HERE / "data" / "dev.txt"), dev)
        if rl:
            rl.log(step, **{"dev/exact": score})
        model.save_pretrained(str(out / "adapter"))
        if rl:  # names the saved adapter as the run's result: without it `expctl status` lists no best run
            rl.checkpoint(out / "adapter", step=step, value=score, is_best=True)
        print(json.dumps({"dev_exact": score, "steps": step, "seconds": seconds}), flush=True)


if __name__ == "__main__":
    main()
