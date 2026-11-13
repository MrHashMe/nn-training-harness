#!/usr/bin/env python3
"""Fetch the base model of the fine-tuning task into model/: about 270 MB, once.

    python fetch_model.py

HuggingFaceTB/SmolLM2-135M-Instruct (Apache-2.0, not gated; checked 12 November 2026) at one pinned revision,
without a login. Every file is checked against the size and SHA-256 recorded here before it is kept, so the
weights are the same in every project. Standard library only; after this, training and evaluation run offline.
"""
import hashlib
import os
import shutil
import sys
import urllib.request
from pathlib import Path

REPO, REVISION = "HuggingFaceTB/SmolLM2-135M-Instruct", "12fd25f77366fa6b3b4b768ec3050bf629380bac"
FILES = {  # name: (bytes, SHA-256)
    "config.json": (861, "8eb740e8bbe4cff95ea7b4588d17a2432deb16e8075bc5828ff7ba9be94d982a"),
    "generation_config.json": (132, "87b916edaaab66b3899b9d0dd0752727dff6666686da0504d89ae0a6e055a013"),
    "model.safetensors": (269060552, "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c"),
    "special_tokens_map.json": (655, "2b7379f3ae813529281a5c602bc5a11c1d4e0a99107aaa597fe936c1e813ca52"),
    "tokenizer.json": (2104556, "9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c"),
    "tokenizer_config.json": (3764, "4ec77d44f62efeb38d7e044a1db318f6a939438425312dfa333b8382dbad98df"),
}


def matches(path, size, digest):
    if not path.is_file() or path.stat().st_size != size:
        return False
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == digest


def main(out=Path(__file__).resolve().parent / "model"):
    out.mkdir(exist_ok=True)
    for name, (size, digest) in FILES.items():
        dst, part = out / name, out / (name + ".part")
        if matches(dst, size, digest):
            print(f"have     {name}")
            continue
        req = urllib.request.Request(f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}",
                                     headers={"User-Agent": "fetch_model.py"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
        except OSError as e:
            sys.exit(f"{name}: the download failed ({e}); run this again when the network is back")
        if not matches(part, size, digest):
            part.unlink()
            sys.exit(f"{name}: what arrived does not have the recorded size and SHA-256; nothing was kept")
        os.replace(part, dst)
        print(f"fetched  {name}")
    print(f"the base model is in {out}")


if __name__ == "__main__":
    main()
