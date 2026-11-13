#!/usr/bin/env python3
"""Frozen evaluator of the fine-tuning task: the share of held-out messages whose intent a run's adapter names
exactly, in text the model generates.

    python evaluate.py --run-dir RUN [--data data/dev.txt]   ->  one JSON line with "score" (higher is better)

Contract for RUN/adapter (a run that breaks it is refused: exit 3, an "error" line, no score):
- a LoRA adapter saved by PEFT for the base model in model/: adapter_config.json and adapter_model.safetensors.
  Weights in another format are not loaded, so nothing a run saved is executed.
- the base model, its tokenizer and its chat template are the files in model/ (fetch_model.py); a run cannot
  replace them.
- every message is put into PROMPT, rendered with the chat template and answered greedily in at most MAX_NEW
  tokens; an answer counts when it is the intent's name, blanks around it removed.
train.py takes the prompt from here, so training and evaluation ask in the same words.
"""
import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # everything is read from model/ and the run folder
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

HERE = Path(__file__).resolve().parent
MODEL = HERE / "model"
PROMPT = "Which intent does this message to a bank's support have? Answer with the intent's name only.\n\n{text}"
MAX_NEW = 24  # tokens per answer; the longest intent name takes 17
EVAL_BATCH = 100


def refuse(msg):
    print(json.dumps({"error": msg}))
    sys.exit(3)


def read(path):
    """[(message, intent)] of a data file: one pair per line, a tab between the two."""
    with open(path, encoding="utf-8") as f:
        return [tuple(line.rstrip("\n").split("\t")) for line in f if line.strip()]


def prompt(tok, text):
    """The text the model answers: the message in PROMPT, in the model's own chat format."""
    return tok.apply_chat_template([{"role": "user", "content": PROMPT.format(text=text)}], tokenize=False,
                                   add_generation_prompt=True)


def answer_part(tok, text, intent):
    """What a training text adds to prompt(): the answer and the template's end of turn. This is the chat-template
    check: a template that renders the two differently would train one format and be asked in another."""
    chat = [{"role": "user", "content": PROMPT.format(text=text)}, {"role": "assistant", "content": intent}]
    full, start = tok.apply_chat_template(chat, tokenize=False), prompt(tok, text)
    if not full.startswith(start) or not full[len(start):].startswith(intent):
        raise ValueError("the chat template in model/ does not render a training text as the prompt followed by the "
                         "answer")
    return full[len(start):]


def load_base():
    """The base model in float32 and its tokenizer, from model/ alone."""
    if not (MODEL / "model.safetensors").is_file():
        sys.exit(f"{MODEL} holds no base model: run `python fetch_model.py` once (about 270 MB)")
    from transformers import AutoModelForCausalLM, AutoTokenizer
    return AutoModelForCausalLM.from_pretrained(str(MODEL)).float(), AutoTokenizer.from_pretrained(str(MODEL))


def answers(model, tok, texts, device):
    """The model's greedy answers to the messages, in order."""
    import torch
    tok.padding_side = "left"  # the answer must follow the prompt directly
    out = []
    for i in range(0, len(texts), EVAL_BATCH):
        enc = tok([prompt(tok, t) for t in texts[i:i + EVAL_BATCH]], return_tensors="pt", padding=True,
                  add_special_tokens=False).to(device)
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False, pad_token_id=tok.pad_token_id,
                                 eos_token_id=tok.eos_token_id)
        out += [s.strip() for s in tok.batch_decode(gen[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)]
    return out


def exact(model, tok, pairs, device):
    """Share of the pairs whose intent the model names exactly."""
    got = answers(model, tok, [t for t, _ in pairs], device)
    return sum(g == c for g, (_, c) in zip(got, pairs)) / len(pairs)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--data", default="data/dev.txt", help="file to score on, relative to this file")
    a = ap.parse_args()
    adapter = Path(a.run_dir) / "adapter"
    if not (adapter / "adapter_config.json").is_file() or not (adapter / "adapter_model.safetensors").is_file():
        refuse(f"{adapter} does not hold adapter_config.json and adapter_model.safetensors: a run must save a PEFT "
               f"LoRA adapter there")
    try:
        kind = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8")).get("peft_type")
    except (ValueError, AttributeError):
        kind = None
    if kind != "LORA":
        refuse(f"the adapter is not a LoRA adapter (peft_type {kind!r})")
    model, tok = load_base()
    import torch
    from peft import PeftModel
    try:
        model = PeftModel.from_pretrained(model, str(adapter))
    except Exception as e:  # whatever a broken adapter raises: the run has no score
        refuse(f"the adapter does not load onto the base model: {type(e).__name__}: {str(e)[:300]}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pairs = read(HERE / a.data)
    score = exact(model.float().to(device).eval(), tok, pairs, device)
    print(json.dumps({"score": score, "metric": "exact match of the generated intent", "data": a.data,
                      "examples": len(pairs)}))


if __name__ == "__main__":
    main()
