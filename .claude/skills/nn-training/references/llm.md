# Language models: from-scratch pretraining, tokenizer and template, instruction tuning, text evaluation

Checked: 2026-11-11
Refresh: reread the transformers chat-templating guide, the TRL SFT and chat-template docs with their release notes, and
the lm-evaluation-harness docs against the installed versions; scout (`scouting.md`) for pretraining recipes.

Read when the project pretrains a small language model, formats chat or instruction data, tunes on instructions or
preferences, or scores generated text. Read `finetuning.md` for base model, LoRA, RL, distillation and export.

Every item here is a hypothesis to test under the project's protocol (one change, declared budget, paired seeds, a
margin above the noise floor), not a default to switch on. Versions are from 2026-11-11 and age in weeks.

## Pretraining a small model from scratch
- Useful as a research benchmark or a small domain model, not as a route to a general assistant on one GPU (inferred).
- Fixed-budget loop. Applies: iterating on a training recipe. Do: give every experiment the same wall-clock budget
  (autoresearch uses 5 minutes); keep data, tokenizer and evaluation in one file the agent may not edit; the agent edits
  one training file. Risk: a fixed budget favours fast changes, not the best at convergence. Its README advises
  running the agent with all permissions off; the kit's rules forbid that outside an isolated container. The kit's
  `nnloop` runs this pattern with harness-side scoring (`loop.md`).
  (source: https://github.com/karpathy/autoresearch, 2026-11-11)
- torchtitan is the PyTorch-native reference for large-scale pretraining (status not re-checked on 2026-11-11).

## Tokenizer and chat-template preflight
Before any long run, render three training examples, tokenise them as the trainer does, and read them verbatim. Record:
BOS count, last token, all end ids (including `generation_config.json`), pad id and side, decoded loss tokens,
truncated-example count, packing strategy. The standard library cannot render Jinja; run a short snippet in the
project's own training environment and store its output with the run. Risk: false comfort from short examples only.
(source: https://github.com/huggingface/transformers/blob/main/docs/source/en/chat_templating.md, 2026-11-11)

| Check | Detail |
|---|---|
| Template | use the tokenizer's own template; tokenise its text with `add_special_tokens=False` (no doubled BOS) |
| Generation prompt | `add_generation_prompt=False` to train, `True` to infer; never with `continue_final_message` |
| End token | each target ends with the template's end-of-turn token; some models need `eos_token` in `SFTConfig` |
| End ids | read every id; Gemma 4 has three, some only in `generation_config.json` (TRL before 1.14.2 ran past them) |
| Pad | a pad token exists and is recorded; pads get label -100; pad = end token unmasked is a risk (inferred) |
| Padding side | left for batched generation; right padding is worse for state-space and hybrid models |
| Loss mask | `assistant_only_loss=True` needs `{% generation %}` markers; decode the tokens with label != -100 |
| Prompt-completion | completion-only loss is default; completion starts where tokenisations diverge (fixed 1.14.2) |
| Reasoning | inference templates may drop reasoning (DeepSeek-R1-Distill, original Qwen3): lost from the target |
| Tool calls (RL) | appending a tool message must not change how earlier messages render |
| Packing | record it: `bfd` (default) drops tokens past `max_length`; `wrapped` mixes examples and hurts |
| Truncation | count examples over `max_length`; answer and end token must survive; keep image tokens in vision data |
| New tokens | resize embeddings; `trainable_token_indices` or `modules_to_save=["embed_tokens","lm_head"]` |
| Serving | the template at serving or export equals the training one (compare strings; see `finetuning.md`) |

(source: https://github.com/huggingface/trl/blob/main/docs/source/sft_trainer.md, 2026-11-11)
(source: https://github.com/huggingface/trl/blob/main/docs/source/chat_templates.md, 2026-11-11)
(source: https://github.com/huggingface/trl/releases, 2026-10-30)

## Instruction and preference tuning
- Supervised: `SFTTrainer`, the model's template, `assistant_only_loss=True`; correctness rests on the table above.
- Preference: DPO and KTO are stable TRL 1.17.1 trainers; Online DPO and ORPO are experimental. No fresh comparative
  evidence was found, so compare methods with your own frozen evaluator.
  (source: https://raw.githubusercontent.com/huggingface/trl/main/docs/source/_toctree.yml, 2026-11-11)
- Check contamination between tuning data and evaluation sets (`validity.md`).

## Evaluating generated text
- Freeze the generation settings with the evaluator: decoding parameters, chat template, stop ids, max new tokens, seed,
  engine and version, hardware. A mismatch makes scores incomparable. Repository configs can turn sampling on (Gemma 4:
  temperature 1.0, top-k 64, top-p 0.95); `generate` returns at most 20 new tokens unless told; decoder-only output
  includes the prompt. vLLM is reproducible only on the same hardware and version, and needs
  `VLLM_ENABLE_V1_MULTIPROCESSING=0` or batch invariance.
  (source: https://docs.vllm.ai/en/latest/usage/reproducibility/, 2026-10-08)
  (source: https://huggingface.co/google/gemma-4-E4B-it/raw/main/generation_config.json, 2026-04-02)
- lm-evaluation-harness 0.4.13 (extras such as `lm_eval[hf]`): pin harness and task versions; report few-shot layout and
  decoding with each number; it saves the chat template with results.
  (source: https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/model_guide.md, 2026-11-11)
- Baseline rows in every comparison: the untuned model and a trivial predictor, scored with the frozen prompt. The task
  metric decides; loss is logged, not decisive. In one three-model QLoRA study bits per byte separated the models in
  every seed while chrF++ did not (30.51 vs 30.61). Read generations, not only likelihood. Risk: you must define the
  trivial predictor. (source: https://arxiv.org/abs/2611.12628, 2026-11-09; abstract level)
- Version the evaluator and keep 5 to 10 known-answer cases; run them before each confirmation and the final evaluation,
  and force a new baseline when the version changes. The PEFT maintainers shipped a wrong metric in their own benchmark.
  (source: https://github.com/huggingface/peft/releases, 2026-07-28)

## Candidates to test, not adopted
- Packing plus completion-only loss: -49% wall-clock, 59.4 to 61.1% on GSM8K, 1.5B LoRA, one task
  (source: https://github.com/Saivineeth147/lora-speedrun, 2026-08-04)
- Significance rule for keeping a change: several runs, one-sided test, p < 0.01 as in modded-nanogpt
  (source: https://github.com/KellerJordan/modded-nanogpt, 2026-08-30)
- nanochat (MIT, last commit 2026-07-03): `--depth` dial; its leaderboard was recorded inconsistently (3.04 h to
  1.65 h, or 2.02 h to 1.80 h to 1.65 h): read the repository; README warns the metric is noisy
  (source: https://github.com/karpathy/nanochat, 2026-11-11)
- modded-nanogpt record 39.9 s: recipe fitted to one target; adopt its method, not its tricks
  (source: https://github.com/KellerJordan/modded-nanogpt, 2026-08-30)
- lora-speedrun task as a cheap benchmark for the kit itself
  (source: https://github.com/Saivineeth147/lora-speedrun, 2026-08-04)
- Short-example pruning with one high-rate epoch: one task
  (source: https://github.com/Saivineeth147/lora-speedrun, 2026-08-04)
- Muon via `torch.optim.Muon` for pretraining 2D weights only; embeddings and heads stay on AdamW
  (source: https://docs.pytorch.org/docs/2.15/generated/torch.optim.Muon.html, 2026-11-11)
- Pretraining optimizer reused when fine-tuning (source: https://arxiv.org/abs/2605.06654, 2026-05-07; preprint)
- inspect-ai 0.3.289 for generative and agentic evaluations (source: https://pypi.org/project/inspect-ai/, 2026-11-10)
- Out-of-domain probe set scored before and after tuning
  (source: https://arxiv.org/abs/2611.12864, 2026-11-09; preprint)
- Dated shortlist of small open-weight families with a licence column
  (source: https://huggingface.co/api/models, 2026-11-11)

## Held or rejected
- lighteval 0.13.0: no release since 2025-11-24. gradian: alpha, one commit, pipe-to-shell installer; use its check
  list as a spec, not the tool.
- Packing with completion-only loss is not a fault when the mask covers the loss tokens: test mask coverage, do not
  ban it.
