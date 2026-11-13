# Scout note - Language-model training practice as of late 2026

- Written 11 November 2026 for the kit upgrade. Kit baseline read: the 23 October 2026 kit
  (`.claude/skills/nn-training/references/finetuning.md`, `resume.md`, `validity.md`, `stack.md`,
  `docs/research-notes/training_techniques.md`).
- Every source below was checked on 11 November 2026 ("chk" = date checked; it is 2026-11-11 for every source key
  in the table at the end unless that row says otherwise).
- Each claim ends with a status and source keys, for example `[V S3]`. **V = Verified**: primary source (official
  docs, release notes, licence text, package index, hub API, paper page) opened in this session. **I = Inferred**:
  my reasoning from verified facts, or recalled without re-reading today. **U = Unverified**: secondary or
  user-generated source only, search-engine summary only, or not reached.
- Limits of the method. Most pages were read through a fetch tool that returns a small model's summary, so quoted
  wording can be slightly off; the TRL, PEFT and Transformers release pages were cut at 100,000 characters (older
  releases unread). Nothing was installed, cloned or run (no local commands were allowed), so nothing here was
  measured on the test machine. Licence items are context for what an agent should record, not legal advice.
- Query families used: latest release notes; benchmarks and leaderboards; limitations and postmortems; state-of
  and surveys; alternatives; awesome lists; security and failure modes; plus licence texts and hub metadata.

## Summary (10 lines)

1. `finetuning.md` is sound in direction but thin for language models: no licence check, no model-choice guidance, five lines on data formatting where current primary docs describe about fifteen separate silent failure points, and nothing on RL post-training, distillation, export or from-scratch pretraining.
2. In the 19 days since 23 October: torch 2.15.0 shipped (28 Oct), transformers went 5.20.2 to 5.22.2, TRL 1.16.0 to 1.17.1, Unsloth 2026.10.7 to 2026.11.3, Axolotl 0.21.0 to 0.21.1. Version tables age in weeks, so core must not hard-code versions and every table needs a date and a "verify installed version" rule.
3. The frameworks pin each other incompatibly: Unsloth caps transformers at 5.17.0 and TRL at 1.15.0; Axolotl needs torch 2.13 or newer and Python 3.12; the LLaMA-Factory package caps transformers at 5.6.0; TRL 1.17.1's vLLM extra excludes the current vLLM 0.33.0. One framework per environment, with the lock recorded.
4. LoRA evidence has firmed up: which layers are adapted (all linear layers, MLP included) and the learning rate (about 10 times the full fine-tuning rate) matter more than rank or variant; with a tuned learning rate nine LoRA variants land within 1-2% of plain LoRA; LoRA falls behind full fine-tuning when the data exceeds adapter capacity or the batch is large. The kit's "rank 16-64, alpha = rank or 2x rank" line is not supported as a general rule.
5. On 17 narrow tasks with 0.6B-4B models, LoRA overtook in-context prompting at about 50 labelled examples on average (NeurIPS 2026). "Baseline first" stays; fine-tuning is worth testing early, and prompt optimisation is not a safe default baseline.
6. Tokenizer and chat-template mistakes are still the main silent failure, and 2026 library release notes show them hitting real users (end-of-turn ids present only in the generation config, EOS not appended, inference templates that drop reasoning, packing that duplicated data). A mechanical render-and-decode check before any long run is the highest-value language-model addition.
7. Scores from generated text are reproducible only if decoding settings, template, stop ids, engine and engine version are frozen: Gemma 4 ships with sampling on by default, and vLLM is not reproducible by default and only on the same hardware and version.
8. RL post-training (GRPO) is a stable TRL trainer, but fast rollouts need vLLM, which has no native Windows support (WSL2 on the test machine). Named failure modes: no reward signal, reward exploitation, loss of exploration, misleading evaluation, and mismatch between the rollout engine and the trainer. Keep it an optional module with a health checklist.
9. Licences of current small open-weight models differ a lot: Apache-2.0 (Gemma 4, Qwen3.5-3.8, SmolLM3, Granite 4.x, gpt-oss), MIT (Phi-4, DeepSeek V4.x), and custom terms for LFM2.5 (US$10M revenue threshold), Mistral Medium 3.5 and Large 4 (service clause), Llama (naming, attribution, use policy), Nemotron and Muse Spark Open (gated, personal-data form). A standard-library licence-and-gating preflight that answers "ask" on `other`, `unknown`, missing or gated belongs in core.
10. Loading a model can run code: 31 malicious hub repositories reported on 29 October 2026 executed through `trust_remote_code=True` while hub scanners reported them clean, and transformers 5.22.2 (6 Nov) hardened its template sandbox. Default-deny remote code, prefer safetensors, pin revisions, and treat templates and agent-instruction files in third-party repositories as untrusted. Public small-GPT speed records (39.9 s) are benchmark-specific: adopt their method (frozen data and target, significance test), not their tricks.

## Q1. Re-check of finetuning.md and training_techniques.md

`finetuning.md` (line numbers from the 23 October file):

| Line | What it says | Today | Status |
|---|---|---|---|
| 4 | "Versions below were current on 23 Oct 2026" | Out of date for transformers, TRL, Unsloth, Axolotl, torch (see Q4). The "verify installed versions" rule is right and should be the only version rule in core. | V S1 |
| 7 | TRL 1.x "(SFT, DPO, GRPO, KTO, reward modelling)" | Incomplete. Stable trainers in 1.17.1: Distillation, DPO, GRPO, KTO, Reward, RLOO, SFT. Experimental section: A2PO, Async Distillation, Asynchronous GRPO, CPO, GKD, GMPO, GOLD, IW-OPD, Online DPO, ORPO, SDFT, SDPO. Removed in the last six months: `PPOTrainer` (1.13.0), `trl.losses` and several experimental trainers (1.14.0), MiniLLM (1.15.0), SSD (1.16.0), TPO (1.17.0). | V S3 S8 |
| 7-8 | PEFT initialisations and variants listed without ranking | Variants are not defaults: tuned plain LoRA is within 1-2% of nine variants. AutoGPTQ is deprecated in PEFT (0.20.0); the GPTQ and AWQ path is GPTQModel (0.19.0). | V S13 S16 |
| 8-9 | "Accelerate still defaults to FSDP1" | Not re-checked; irrelevant on one GPU. | U |
| 10 | Unsloth "fastest single-GPU LoRA/QLoRA path" | Still a vendor claim ("2x faster with 70% less VRAM"). Missing: it supports native Windows, it lags the Hugging Face stack (transformers <=5.17.0, trl <=1.15.0, torch <2.15), and its Studio UI is AGPL-3.0 while the core is Apache-2.0. | V S1 S27 |
| 11 | Axolotl / LLaMA-Factory as config-driven alternatives | Axolotl 0.21.1 needs Python >=3.12 and torch >=2.13 (the test machine has torch 2.9) and has telemetry on by default. LLaMA-Factory's last package and tagged release is 0.9.5 (30 May 2026) with transformers <=5.6.0, although the repository had commits on 10 Nov 2026. | V S1 S28 S30 |
| 12 | Liger Kernel "memory/throughput lever" | Still true, but TRL deprecated `use_liger_kernel` in DPO, KTO, GRPO and RLOO in 1.15.0 in favour of `model_init_kwargs={"use_kernels": True}` (removal planned for 2.0.0). Liger is 0.8.5 (21 Oct 2026); the earlier note's 0.8.4 was already stale on 23 October. | V S1 S3 |
| 13-14 | torchtune unmaintained | Confirmed: README says "no longer actively maintained", wound down in 2025. torchtitan not re-checked. | V S29 |
| 17-19 | Baseline first; record decoding parameters | Holds. Add: check whether the repository's `generation_config.json` turns sampling on (Gemma 4 does), and add the 50-example crossover evidence. | V S18 S40 |
| 21-26 | Five formatting checks | All correct, all still needed. Missing items are listed in Q3 (special-token duplication, generation prompt, end-of-turn ids, pad token and side, reasoning content, generation markers for the loss mask, packing strategy names, new-token embeddings, template at serving and export). | V S4 S5 S6 S11 S12 |
| 29 | "Target modules `all-linear`" | Supported by current evidence. | V S15 S10 |
| 29 | "rank 16-64, alpha = rank or 2x rank" | Not supported as a general rule. The cited experiments fixed alpha at 32 with 1/r scaling and swept rank 1-512; TRL's reproduction uses r=256, alpha=16 for large supervised sets and r=1-32 for RL. Rank should follow the amount of information in the data. | V S15 S10 |
| 29-30 | LoRA LR about ten times the full fine-tuning LR | Confirmed (about 15x for runs under about 100 steps, anecdotal in the source). Missing: LoRA tolerates large batches less well than full fine-tuning. | V S15 |
| 31 | QLoRA: 4-bit NF4, double quantisation, bf16 | Still the standard recipe. New: transformers 5.22.0 lets FP8-quantised models be used for adapter training; torchao merging is only correct for LoRA with `int8_weight_only`. | V S2 S14 |
| 32 | "DoRA supports Linear/Conv2d only" | PEFT docs now say embedding, linear and Conv2d. Overhead and merge advice unchanged. | V S14 |
| 33-34 | Optimizer-family note (Moonlight) | Not re-checked. | U |
| 37-38 | lm-evaluation-harness, inspect_ai, lighteval | lm-eval 0.4.13 (31 Aug 2026) unchanged; inspect-ai 0.3.289 (10 Nov 2026); lighteval 0.13.0 has had no release since 24 Nov 2025. "lighteval runs on inspect" not re-checked. | V S1 |
| 45-47 | Save and reload contract | Holds. Add: eos and pad ids, generation config, which template was saved (training or inference version), and evaluation of the exported artefact. | I |

`docs/research-notes/training_techniques.md`:

- "PyTorch 2.14.1 latest, 2.15 planned for 28 Oct 2026": 2.15.0 was released on 28 October 2026 (Python >=3.11). `[V S1]`
- Section 4 version table: transformers 5.20.2 is now 5.22.2 (6 Nov); TRL 1.16.0 is now 1.17.1 (30 Oct); Unsloth 2026.10.7 is now 2026.11.3 (6 Nov); Axolotl 0.21.0 is now 0.21.1 (27 Oct); Liger 0.8.4 should have read 0.8.5 (21 Oct); inspect-ai 0.3.282 is now 0.3.289. PEFT 0.21.2, Accelerate 1.15.0, LLaMA-Factory 0.9.5, lm-eval 0.4.13 and lighteval 0.13.0 are unchanged. `[V S1]`
- Its Unverified item "TRL stable core versus experimental split": confirmed by the 1.17.1 documentation index, which has a stable Trainers section and a separate Experimental section. `[V S8]`
- Its Unverified item "lm-eval 0.5.0.dev1": the newest stable release on the package index is still 0.4.13. `[V S1]`
- LoRA+ "up to 2x" and the PEFT initialisation notes: not re-checked. `[U]`
- Missing in both files: any licence or gating check; model choice; RL post-training failure modes; distillation; export formats; remote-code risk; telemetry of the training libraries.

## Q2. Training regimes and when each wins

All of this is dated technique advice: it should enter the kit as hypotheses to test against the project's own frozen evaluator.

**Prompting and in-context baseline (no training).** In-context learning stopped improving at 25-50 examples; LoRA fine-tuning kept improving up to the 200-example budget and overtook every in-context strategy at about 50 labelled examples on average (17 narrow tasks; Qwen3 0.6B, 1.7B, 4B; per-task hyperparameter search; crossover earlier for the smaller models). The automatic prompt optimiser tested (GEPA) was "not competitive" in that configuration; task category can reverse the ordering. `[V S18]` Vendor and blog advice to run prompt optimisation before any fine-tuning is user-generated. `[U]`

**Pretraining a small LM from scratch.** Useful as a research benchmark or for a small domain model, not as a route to a general assistant on one GPU. `[I]`
- modded-nanogpt: target 3.28 validation loss on FineWeb on 8 H100s; record 39.9 s (0.665 min, 30 Aug 2026), from 73.9 s for the record before it. The step combined sampled softmax, FP8 forward and backward in the MLPs, a hashed n-gram embedding table with 84.6M rows, a new optimizer stack, depth reduction and capture of the whole step as a CUDA graph; the submission's ablation attributes 3-8 s to each. Rules: data pipeline untouched; enough runs to show mean validation loss <= 3.28 at p < 0.01; the record is deliberately held 0.001-0.002 below the target. Five records are credited to AI systems. `[V S24]`
- These recipes are fitted to one target, one data set and one hardware class. An author's write-up claims a further drop to 6.7 s with retrieval-style n-gram hints, which shows how far a fixed benchmark can be specialised. `[U S50]` The transferable parts are the method (frozen data and target, significance rule, ablation per change) and, as hypotheses only, the optimizer and precision ideas. `[I]`
- nanochat (MIT): one `--depth` dial, AdamW plus Muon, explicit compute dtype, a "time to GPT-2 quality" leaderboard on 8 H100s that fell from 3.04 h (29 Jan 2026) to 1.65 h (14 Mar 2026). Two of the steps are credited to an automated research loop; the largest single step (2.76 h to 2.02 h) came from changing the data set, not the model. The README warns that its headline metric is noisy and reports validation bits per byte as well. Short depth-12 runs are its iteration unit; it runs on one GPU with gradient accumulation. `[V S25]`
- autoresearch: the loop that produced those two steps keeps data, tokenizer and evaluation in one file the agent may not edit, lets the agent edit one training file, and gives every experiment a fixed 5-minute wall-clock budget. Its README tells the user to run the agent with all permissions disabled, which the kit's constraints forbid outside an isolated container. `[V S26]`

**Full fine-tuning.** Wins when the data carries more information than the adapter can hold, when large batches are needed, and for continued pretraining. `[V S15]` On 32 GB it is limited to roughly 2-3B parameters in bf16 with AdamW (about 8 bytes per parameter for weights, gradients and two moments, before activations). `[I]`

**LoRA.** Matches full fine-tuning on small and medium supervised sets and in policy-gradient RL (even rank 1 in the source's experiments, because RL carries about one bit per episode). Apply it to all weight matrices: attention-only LoRA at rank 256 lost to MLP-only LoRA at rank 128 with matched parameter count. Optimal LR about 10 times the full fine-tuning LR and roughly independent of rank. LoRA degrades faster than full fine-tuning as batch size grows. Vendor compute claim: about two thirds of the FLOPs per pass. `[V S15]` One lab produced these results and the Hugging Face reproduction is qualitative (curves, no numbers, inconsistent example settings); a community reproduction disagreed on MLP-only versus MLP plus attention. `[V S10; the disagreement is U]`
- Variants (DoRA, PiSSA, MiLoRA and others): different variants need different LR ranges (up to 10x apart); once LR is tuned all peak within 1-2% of each other and plain LoRA "remains a competitive baseline". `[V S16]`
- Retention: under equal parameter budgets orthogonal fine-tuning gave the best trade-off between target gain and retained general ability, and final supervised checkpoints often overshoot a better stopping point. `[V S17]`

**Quantised adapters.** QLoRA (4-bit base through bitsandbytes 0.50.2) is the route when the 16-bit base does not fit. Vendor minimum table: 4-bit needs about 22 GB for 27B and 26 GB for 32B parameters; 16-bit LoRA needs about 22 GB for 8B, 24 GB for 9B and 29 GB for 11B ("the absolute minimum"). `[V S27 S1]` PEFT caveats: with torchao only linear layers, no `int4_weight_only`, merging correct only for LoRA with `int8_weight_only`; DoRA on bitsandbytes layers works but had problems with DeepSpeed ZeRO-2. `[V S14]`

**Instruction tuning (supervised chat fine-tuning).** `SFTTrainer` with the model's chat template and `assistant_only_loss=True`; correctness depends on the items in Q3. `[V S4]` A published open eight-stage recipe (supervised stage first, then RL stages ordered from verifiable rewards to judge-based ones) reports that a diverse supervised stage sets the capability floor and that difficulty filtering keeps RL prompts in a useful range; it gives no numbers in the abstract and concerns a 106B model. `[V S22]`

**Preference tuning.** DPO and KTO are stable TRL trainers; Online DPO and ORPO are in the experimental section. Axolotl lists DPO, IPO, KTO and ORPO. No fresh comparative evidence was found. `[V S8 S28]`

**RL post-training.** GRPO and RLOO are stable in TRL 1.17.1; Asynchronous GRPO is experimental. `[V S8]`
- Loss variants documented: `grpo`, `dapo`, `dr_grpo`, `sapo`. Defaults that matter: `beta=0.0` (no KL term); `entropy_target=0.2` "almost never triggers". Metrics to watch: `reward_std`, `frac_reward_zero_std` (groups with no learning signal), `completions/clipped_ratio`, `entropy`, `clip_ratio/*`, and `sampling_logp_difference`. `[V S7]`
- Rollouts: vLLM colocated with the trainer or as a server on other GPUs, or continuous batching inside transformers for one GPU. With vLLM, sequence-level importance-sampling correction is on by default because trainer and engine give different probabilities to the same tokens. Since 1.17.0 GRPO raises if `top_p < 1.0` or `min_p > 0.0` is used without `top_k > 0` while that correction is on; groups with zero advantage are filtered. `[V S3 S7]`
- A separate paper names this engine mismatch as a cause of instability and collapse, and argues that improving the trainer-side policy does not guarantee improving the policy that is served. `[V S21]`
- A practical book-length report (7 Nov 2026) lists the common failures: no useful reward, reward exploitation, loss of exploration, and evaluation that looks better while the task is not solved. `[V S19]`
- "Sharpening tax": across 14 base and post-trained pairs, post-training raised single-attempt accuracy but often reduced the share of tasks solved within K attempts. Report pass@K next to pass@1. `[V S20]`
- Tool-calling RL needs templates in which appending a tool message does not change how earlier messages render; TRL patches known families only. Environments: OpenEnv (0.12.0, 5 Nov 2026), Harbor and OpenReward integrations. `[V S5 S7 S47]`
- Other libraries: verl 0.9.1 (20 Sep 2026), verifiers (development builds only, 0.4.2.dev30 on 10 Nov), ART 0.5.24 (4 Nov). Not compared here. `[V S1 S47]`
- TRL's own quick start takes about a day on 8 GPUs. `[V S7]`

**Distillation.** `DistillationTrainer` is stable in TRL; GOLD (with cross-tokenizer distillation since 1.17.0) and Async Distillation with multiple teacher servers are experimental; since 1.14.0 the teacher is not quantised by default. `[V S3 S8]` Licence or service terms of the teacher need the same check as the base model (see Q5 and the data scout's note on provider terms). `[I]`

**Quantisation and export.**
- GGUF: llama.cpp (MIT, rolling builds, b12255 on 10 Nov 2026) keeps `convert_hf_to_gguf.py` and `convert_lora_to_gguf.py` in the repository root. `[V S33]`
- AutoAWQ is "officially deprecated"; its README points to llm-compressor (0.15.0, 28 Oct 2026, with backport patch lines still being published) and MLX-LM. GPTQModel 7.10.0 (6 Nov) is the PEFT-supported GPTQ and AWQ path. torchao 0.18.0 (3 Aug). `[V S1 S13 S34]`
- transformers 5.20.0 says its exporters "now support quantization directly during export"; Axolotl added `axolotl export` to GGUF (September 2026); Unsloth exports GGUF, NVFP4 and FP8; Google publishes quantisation-aware Gemma 4 checkpoints. `[V S2 S27 S28 S35]`
- An exported file is a new model: it carries its own copy of the chat template and its own numerics, so the frozen evaluator must be run on the exported artefact. `[I]` Templates inside GGUF files have been shown to carry hidden instructions (vendor research). `[U S44]`

## Q3. Pitfalls that silently ruin language-model results (checklist)

| # | Check | Source and status |
|---|---|---|
| 1 | Build training text with the tokenizer's own chat template; read rendered examples verbatim. | Transformers chat-templating guide. V S11 |
| 2 | No doubled special tokens: text from `apply_chat_template(tokenize=False)` already has them; tokenize it with `add_special_tokens=False`. Count BOS tokens in one tokenised example. | "adding additional special tokens is often incorrect or duplicated, hurting model performance". V S11 |
| 3 | `add_generation_prompt=False` for training text, `True` for inference; never together with `continue_final_message`. | V S11 |
| 4 | Every training target ends with the token that ends a turn in this template, and generation stops on it. Some models need `eos_token` set in `SFTConfig` (example given: `<|im_end|>` for Qwen2.5). | TRL SFT docs; fix in 1.15.0 for EOS not being appended. V S3 S4 |
| 5 | Read the full list of end-of-sequence ids, including those only in `generation_config.json` (Gemma 4: three ids). Before TRL 1.14.2 such models "kept generating past the end of turn". | V S3 S40 |
| 6 | A pad token exists, is recorded, and pad positions are excluded from the loss (label -100). TRL writes eos and pad ids to the model config since 1.14.0. If pad equals the end-of-turn token and pads are not masked, the model learns wrong stopping behaviour. | First two parts V S3 S4; last sentence I |
| 7 | Padding side: left for batched generation at evaluation time. Right padding is worse still for state-space and hybrid models, whose state keeps updating over trailing pads (the Qwen3.5 family is a hybrid). | Transformers LLM tutorial. V S12 S41 |
| 8 | Assistant-only loss needs `{% generation %}` markers in the template. TRL patches bundled model families only; "for other models, check". Decode the tokens whose label is not -100 for one example and read them. | V S4 S5; the decode step is I |
| 9 | Prompt-completion data: completion-only loss is the default; the completion must start where prompt and prompt-plus-completion tokenisations diverge (fixed in 1.14.2). | V S3 S4 |
| 10 | Reasoning content: inference templates may drop earlier or final reasoning (DeepSeek-R1-Distill; the original Qwen3 template), which "would silently remove the reasoning from the training target". | TRL chat-template guide. V S5 |
| 11 | Tool calling in RL: adding a tool message must not change how earlier messages render. | V S5 S7 |
| 12 | Packing: record the strategy. `bfd` (default) discards tokens beyond `max_length`; `wrapped` can mix unrelated examples and hurts; wrapped packing duplicated data on sliced tables before 1.14.0. | V S3 S6 |
| 13 | Truncation: count examples longer than `max_length` and check that the answer and its end token survive; for vision-language data truncation must not remove image tokens. | Image-token warning V S4; counting rule I (already in the kit) |
| 14 | New tokens: resize embeddings, then either `trainable_token_indices` or `modules_to_save=["embed_tokens", "lm_head"]`; save with `save_embedding_layers=True` when names are non-standard. A LoRA adapter on `lm_head` raises in TRL since 1.15.0. | V S3 S14 |
| 15 | The template used at serving or after export equals the one used in training. TRL swaps in its own training template at start-up for some settings, so check which template was saved with the checkpoint by rendering the same conversation both ways. | Swap is V S5; the comparison step is I |
| 16 | Evaluation of generated text: state whether a chat template was applied, how few-shot examples were laid out, the system instruction, stop sequences and maximum new tokens. `generate` returns at most 20 new tokens unless told otherwise, and decoder-only output includes the prompt. lm-eval saves the template with results. | V S12 S32 |
| 17 | Decoding settings are part of the evaluator: repository configs can turn sampling on (Gemma 4: temperature 1.0, top-k 64, top-p 0.95). Set and record them explicitly. | V S40 |
| 18 | Engine reproducibility: vLLM "does not guarantee" reproducible results by default; it needs `VLLM_ENABLE_V1_MULTIPROCESSING=0` or batch invariance, and holds only "on the same hardware and the same vLLM version". Record engine, version and hardware. | V S31 |
| 19 | Read generations, not only likelihood: in one small study the tokenizer that split words least and the model with better likelihood did not give the outputs closest to the references. For RL-trained models also report pass@K. | V S20 S23 (single-language study, weak) |
| 20 | Fine-tuning data versus evaluation sets, and pretraining contamination. | Already in `validity.md`; not re-researched here |

## Q4. Frameworks and versions on 11 November 2026

| Package | Latest (date) | Licence | Notes for the kit | Status |
|---|---|---|---|---|
| torch | 2.15.0 (28 Oct 2026) | BSD-3 (not re-read) | Python >=3.11. The test machine's 2.9 satisfies transformers and TRL (>=2.6) and Unsloth (<2.15), not Axolotl (>=2.13). | V S1 |
| transformers | 5.22.2 (6 Nov 2026) | Apache-2.0 | Python >=3.11. Breaking items since 5.19: deprecated cache methods removed and nested-config setup changed (5.20.0), `kernels` >=0.17.2 (5.20.0), distributed checkpointing needs torch >=2.8 (5.20.1), parallel-plan changes (5.21.0), remote-code loading regression fixed in 5.21.1, template sandbox hardened (5.22.2). Name it. | V S1 S2 |
| trl | 1.17.1 (30 Oct 2026) | Apache-2.0 | Python >=3.11, torch >=2.6, accelerate >=1.11. Fast removals of experimental trainers; `pad_to_multiple_of` default "auto" (1.16.0). Sends one usage ping per trainer creation unless `HF_HUB_DISABLE_TELEMETRY=1` or `HF_HUB_OFFLINE=1`. Ships an agent skill file (`skills/trl-training/SKILL.md`). Name it. | V S1 S3 S9 |
| peft | 0.21.2 (1 Oct 2026) | Apache-2.0 | `add_adapter` raises on missing target layers (0.21.0); AutoGPTQ deprecated (0.20.0). Name it. | V S1 S13 |
| accelerate | 1.15.0 (9 Sep 2026) | Apache-2.0 | Unchanged. | V S1 |
| bitsandbytes | 0.50.2 (27 Aug 2026) | MIT | 4-bit and 8-bit bases for QLoRA. Native Windows status not re-checked. | V S1; Windows U |
| unsloth | 2026.11.3 (6 Nov 2026) | Apache-2.0 core; AGPL-3.0 Studio UI | "Works on Windows, Linux, WSL and macOS". Several releases a week. Pins torch <2.15, transformers <=5.17.0, trl <=1.15.0. Studio exposes server-side tools by default. Its docs pages carry instructions addressed to agents (see Redirect attempts). Name it as optional, with the pin warning. | V S1 S27 |
| axolotl | 0.21.1 (27 Oct 2026) | Apache-2.0 | Python >=3.12, torch >=2.13; exact pins on transformers 5.20.1, trl 1.14.1, datasets 5.0.1 (older than the 5.2.0 fix the data scout reports). Telemetry on by default; `AXOLOTL_DO_NOT_TRACK=1` turns it off. Native Windows not mentioned; Docker recommended. Name it only for projects that already use it. | V S1 S28; the datasets remark is I |
| llamafactory | 0.9.5 (30 May 2026) | Apache-2.0 | Package pins transformers <=5.6.0, trl <=0.24.0, peft <=0.18.1; repository still active. Do not name as current. | V S1 S30 |
| litgpt | 0.5.13 (3 Jul 2026) | Apache-2.0 | No release for four months. Do not add. | V S1 |
| mlx-lm | 0.32.2 (16 Oct 2026) | MIT | Apple-first; package extras named cuda12, cuda13 and cpu exist (meaning not checked). Not relevant to the test machine. | V S1; extras I |
| torchtune | none | BSD-3 (not re-read) | "No longer actively maintained." Keep the warning. | V S29 |
| liger-kernel | 0.8.5 (21 Oct 2026) | BSD-2 | See Q1 for the TRL flag change. | V S1 S3 |
| vllm | 0.33.0 (2 Nov 2026) | Apache-2.0 (not re-read) | "Does not support Windows natively"; Python 3.11-3.14. TRL 1.17.1 supports >=0.22,<0.33. | V S1 S31 |
| lm-eval | 0.4.13 (31 Aug 2026) | MIT (not re-read) | Name it; saves the chat template with results. | V S1 S32 |
| inspect-ai | 0.3.289 (10 Nov 2026) | MIT (not re-read) | Weekly releases. | V S1 |
| lighteval | 0.13.0 (24 Nov 2025) | MIT (not re-read) | No release for almost a year. Demote. | V S1 |
| datasets | 5.2.0 (9 Nov 2026) | Apache-2.0 | TRL needs >=4.7.0. | V S1 |
| tokenizers | 0.23.3 stable; 1.0.0rc4 (9 Nov 2026) | Apache-2.0 | transformers pins <0.24, so the 1.0 line is not yet in use. | V S1 |
| llm-compressor, GPTQModel, torchao | 0.15.0 (28 Oct), 7.10.0 (6 Nov), 0.18.0 (3 Aug) | not re-read | Export-time quantisation; optional. | V S1 |
| oumi, verl, verifiers, ART, OpenEnv | 0.9 (16 Sep), 0.9.1 (20 Sep), 0.4.2.dev30 (10 Nov), 0.5.24 (4 Nov), 0.12.0 (5 Nov) | not re-read | Seen, not evaluated in depth. | V S1 S47 |

Worth naming in the kit's references: transformers, TRL, PEFT, bitsandbytes, lm-eval (core references, with dates); Unsloth and vLLM as optional with their platform and pin limits; llama.cpp conversion scripts for export. Everything else: one line or nothing.

Other facts that affect the kit:
- The kit's tools run on Python 3.8+, but every current language-model stack needs Python 3.11 or newer (3.12 for Axolotl). The training environment and the kit's interpreter must stay separate. `[V S1; consequence I]`
- A survey organises post-training by where trajectories come from (off-policy versus on-policy) and treats distillation as part of it; the fine-tuning "awesome" list found by search was last pushed in February 2024, and the post-training lists are paper lists. Neither changes the design. `[U S48 S49]`

## Q5. Model choice for a task and a 32 GB GPU; licences

How to choose (hypotheses, in order):
1. Fix the deployment target and the licence constraints before looking at scores; they remove most candidates. `[I]`
2. Pick two or three candidates of different sizes and run the frozen evaluator on the unmodified checkpoints first (existing kit rule). `[I]`
3. Fit the method to memory: on 32 GB roughly full fine-tuning up to 2-3B, 16-bit LoRA up to 9-11B, 4-bit QLoRA up to 27-32B, all before long sequences are considered. The vendor table is a minimum; a published estimator admitted 46% mean error against four measured runs and "no demonstrated accuracy gain", so measure one worst-case batch (longest sequence, real batch size) instead of trusting an estimate. `[V S27 S46; limits I]`
4. Base or instruction-tuned checkpoint: both exist for Gemma 4 and for Qwen3.5 (`-Base`); the RL experiments cited above used base models. `[V S35 S40 S15]`
5. Architecture details change the checklist: Qwen3.5 and later are hybrids (gated linear-recurrence layers plus attention) and multimodal by default (`image-text-to-text`); several small models are mixture-of-experts (Gemma 4 26B-A4B, LFM2.5 8B-A1B, Qwen 35B-A3B), where adapter coverage of expert layers matters. `[V S35 S41 S15]`
6. Framework support lags new models: check that the installed stack lists the family (TRL bundles patched templates for a fixed list). `[V S5]`

Current small open-weight families (sizes that fit a 32 GB card with one of the methods above):

| Family | Sizes seen | Licence (hub id) | Restrictions to record | Status |
|---|---|---|---|---|
| Gemma 4 (2 Apr 2026) | E2B, E4B, 12B, 26B-A4B, 31B | Apache-2.0 | None beyond the licence. Earlier Gemma versions use the Gemma Terms of Use (`gemma`) and are gated. | V S35 S40 |
| Qwen3.5 / 3.6 / 3.8 (Feb-Aug 2026) | 0.8B, 2B, 4B, 9B, 27B, 35B-A3B | Apache-2.0 | None beyond the licence. | V S35 S41 |
| SmolLM3 (Jul 2025) | 3B | Apache-2.0 | None beyond the licence. | V S35 |
| Phi-4 family (2025-2026) | mini, reasoning, 15B vision | MIT | None beyond the licence. | V S35 |
| Granite 4.1 / 4.2 (Sep-Oct 2026) | 8B, 30B | Apache-2.0 | None beyond the licence. | V S35 |
| gpt-oss (Aug 2025) | 20B | Apache-2.0 | Any separate usage policy not checked. | V S35 |
| DeepSeek V4.x (Jul-Oct 2026) | sizes not checked | MIT | Some repositories of the same organisation list no licence at all. | V S35 |
| LFM2.5 | 1.2B, 2.6B, 8B-A1B, 24B-A2B | LFM Open License v1.0 (`other`) | Commercial use only below US$10M annual revenue; ends automatically on breach; says nothing about outputs. | V S37 |
| Mistral Medium 3.5, Large 4 | too large for the card | Mistral Ecosystem Open-Weight License (`other`) | Offering the model or a derivative to third parties for inference or post-training needs a separate commercial licence; internal use exempt. Mistral Small 4 is Apache-2.0. | V S35 S38 |
| Llama 3.2 / 3.3 / 4 (last hub release Apr 2025) | 1B-70B | Llama community licences (`llama3.2`, `llama3.3`, `other`) | "Built with Llama" notice; a distributed model trained or improved with the materials must have a name starting with "Llama"; acceptable use policy; separate licence above 700M monthly users. The 3.3 text has no ban on improving other models. | V S39 |
| NVIDIA Nemotron 3 / 3.5 | 4B-120B | NVIDIA licence (`other`) | Text not read in full. | U |
| Meta Muse Spark Open (15 Oct 2026) | 816B, far too large | `muse-model-license` (`other`), `gated: manual` | Access form asks for name, date of birth, country, affiliation and job title; licence file returns HTTP 401 without access. Reported threshold (US$20M or US$25M for hosting) and attribution wording come from secondary sources that disagree. | Gate V S35; terms U S51 |

Recalled, not re-read today: the Llama 2 and Llama 3.0 licences forbade using outputs to improve other large models. `[U]`

How the kit should make an agent check a licence:
1. Trigger: first use of any base model, teacher model or downloaded adapter, and again before anything is published or exported. `[I]`
2. Record in the run provenance and the Project card: repository id, revision hash, licence id, licence name and link, gated status, where each fact was read, the date, and the verdict. `[I]`
3. Verdict from a user-editable list: allow, ask or deny per licence id. `other`, `unknown`, missing, a `-nc` id, or any gated repository gives "ask". Hub labels can be wrong, so "allow" means "recorded", not "cleared". `[V S36 for the ids; rule I]`
4. Offline path (core): read the model card front matter and any `LICENSE*` file in the local model folder or cache snapshot. Loaders usually fetch only the files they need, so the card is often absent; absent means "ask". `[I]`
5. Network path (optional, off by default): `GET https://huggingface.co/api/models/<repo>` and read `sha`, `gated`, `cardData.license`, `cardData.license_name`, `cardData.license_link` and `tags`. Field shapes confirmed on four repositories today. `[V S35]`
6. The agent never accepts a gate or licence click-through: it is an agreement and it submits personal data; it is the user's action. `[V S35 for the form; rule from the security rules]`
7. If the result will be distributed, print the duties found (name prefix, notice text, use policy) next to the save-and-reload contract. `[I]`

Security when choosing and loading a model:
- 31 malicious repositories in two waves, more than 32,000 downloads including linked models; execution path `trust_remote_code=True` plus `auto_map` in `config.json`, which imports and runs a repository Python file; the weights file held no tensors; payload was a miner with persistence, SSH keys and reverse shells; hub scanners returned clean results; second-wave repositories were still up eight days after the report. `[V S42, vendor research]`
- Hugging Face's own page: pickle files can run code on load, the scanner "is not 100% foolproof", and safetensors is the format without code. `[V S43]`
- transformers 5.22.2 is a security patch that hardens the Jinja sandbox used for chat templates. `[V S2]` Reports of poisoned templates in GGUF files and of a template-driven remote-code CVE in a serving engine were seen through search summaries only. `[U S44]`
- A detector for backdoored LoRA adapters from weights alone reports 97% accuracy on 500 synthetic adapters; not evidence about real ones. `[U S45]`
- Third-party repositories now ship agent-instruction files (llama.cpp's root has `AGENTS.md`, `CLAUDE.md` and `skills/`); cloning one into a workspace can put those files where an agent product loads them. `[V S33; consequence I]`

## Changed since 23 October or wrong in the earlier notes

Changed after 23 October 2026:
- torch 2.15.0 released 28 Oct (was "planned"). `[V S1]`
- transformers 5.21.0 (26 Oct), 5.21.1 and 5.22.0 (29 Oct), 5.22.1 (30 Oct), 5.22.2 (6 Nov: security patch, template sandbox). `[V S1 S2]`
- TRL 1.17.0 (29 Oct) and 1.17.1 (30 Oct): new sampling constraint for GRPO with importance-sampling correction, zero-advantage groups filtered, TPO removed, cross-tokenizer distillation, new Asynchronous GRPO defaults. `[V S3]`
- Unsloth 2026.11.3 (6 Nov), Axolotl 0.21.1 (27 Oct), inspect-ai 0.3.289 (10 Nov), datasets 5.2.0 (9 Nov), vLLM 0.33.0 (2 Nov, outside TRL's supported range), llm-compressor 0.15.0 (28 Oct), GPTQModel 7.10.0 (6 Nov), OpenEnv 0.12.0 (5 Nov), tokenizers 1.0.0rc4 (9 Nov). `[V S1 S47]`
- Malicious-repository campaign through remote code, published 29 Oct. `[V S42]`
- New papers: RL post-training lessons (7 Nov), tokenizer fertility versus output quality (9 Nov). `[V S19 S23]`

Wrong or stale on 23 October:
- Liger Kernel was already 0.8.5 (21 Oct), not 0.8.4. `[V S1]`
- "DoRA supports Linear/Conv2d only": embedding layers are supported too. `[V S14]`
- "rank 16-64, alpha = rank or 2x rank" presented as a starting point without evidence; current evidence points to rank by data size and LR tuning first. `[V S15 S16]`
- TRL trainer list incomplete; the Liger line does not mention that the TRL flag is deprecated in four trainers since 1.15.0. `[V S3 S8]`
- LLaMA-Factory and Axolotl named as equal alternatives although one package is five months stale and the other cannot be installed on the test machine's torch. `[V S1]`
- lighteval listed as current although it had no release for eleven months. `[V S1]`
- Not mentioned at all: Meta's 15 October open-weight release and its gated custom licence; the licence split among small models; telemetry of TRL and Axolotl; the native-Windows gap of vLLM. `[V S9 S28 S31 S35]`

## Concerns any design must handle

- LM-CHAT-TEMPLATE-MISMATCH
- LM-SPECIAL-TOKEN-DUPLICATION
- LM-EOS-STOP-MISCONFIG
- LM-PAD-TOKEN-AND-SIDE
- LM-LABEL-MASK-UNVERIFIED
- LM-REASONING-CONTENT-DROPPED
- LM-TRUNCATION-SILENT
- LM-PACKING-CROSS-CONTAMINATION
- LM-EMBEDDING-RESIZE-NOT-SAVED
- LM-FORGETTING-UNMEASURED
- LM-BASE-MODEL-REVISION-UNPINNED
- EVAL-GENERATION-SETTINGS-UNRECORDED
- EVAL-GENERATION-NONDETERMINISM
- EVAL-EXPORTED-ARTIFACT-UNTESTED
- EVAL-PROXY-METRIC-MISLEADS
- EVAL-BENCHMARK-SPECIFIC-RECIPE
- EVAL-SEED-NOISE
- RL-NO-REWARD-SIGNAL
- RL-REWARD-HACKING
- RL-EXPLORATION-COLLAPSE
- RL-ENGINE-POLICY-MISMATCH
- RL-ROLLOUT-ENGINE-PLATFORM-GAP
- DEP-VERSION-PIN-CONFLICT
- DEP-FAST-RELEASE-DRIFT
- DEP-TELEMETRY-DEFAULT-ON
- DEP-UNMAINTAINED-FRAMEWORK
- DEP-PYTHON-FLOOR-SPLIT
- LIC-MODEL-LICENCE-UNCHECKED
- LIC-CUSTOM-LICENCE-OPAQUE
- LIC-GATED-ACCEPTANCE-BY-AGENT
- LIC-DERIVATIVE-NAMING-AND-ATTRIBUTION
- LIC-REVENUE-OR-HOSTING-THRESHOLD
- LIC-TEACHER-OUTPUT-TERMS
- SEC-REMOTE-CODE-EXECUTION-ON-LOAD
- SEC-UNSAFE-WEIGHT-FORMAT
- SEC-TEMPLATE-INJECTION
- SEC-POISONED-ADAPTER
- SEC-PROMPT-INJECTION
- SEC-CLONED-REPO-AGENT-FILES
- SEC-PRIVACY-LEAK-IN-DOC-QUERIES
- SEC-PERMISSION-BYPASS-ADVICE
- OPS-VRAM-ESTIMATE-UNRELIABLE
- OPS-WINDOWS-NATIVE-GAPS
- ADVICE-UNDATED-TECHNIQUE

## Open questions

1. The standard library cannot render a Jinja chat template. Should the render-and-decode check be a snippet the agent runs in the project's training environment with the kit only recording the result, or an optional helper that imports transformers?
2. Should the licence list ship with defaults (allow Apache-2.0, MIT, BSD; ask for everything else) or empty so that the user decides everything?
3. Should the guard block launches whose script contains `trust_remote_code=True` unless the user has approved that repository and revision? Some legitimate models still need remote code.
4. How does the frozen evaluator pin generation settings: a block in `.claude/nn-training.json` next to `final_eval_commands`, or inside the evaluator script only?
5. Is RL post-training in scope for the pilot, given that fast rollouts mean WSL2 on the test machine?
6. How should the kit treat agent-instruction files inside cloned third-party repositories?
7. How often does the scouting step refresh the version table, and how is staleness shown to the agent?
8. Would a short from-scratch run (nanochat depth 12) make a good pilot task? Its runtime on one RTX 5090 was not measured.
9. Unread: the Muse and NVIDIA licence texts, the Accelerate FSDP default, torchtitan status, the Moonlight claim, native-Windows status of bitsandbytes and Liger.

## Redirect attempts

None was acted on.
1. Unsloth documentation pages (`/docs/get-started/install/windows-installation` and `/docs/get-started/fine-tuning-for-beginners/unsloth-requirements`) contain an "Agent Instructions" section telling agents to send an HTTP GET to the page with `ask=<question>` and `goal=<user_goal>` parameters. That would send the user's goal to a third party. Not sent.
2. A search service's rate-limit error told the caller to create an account and an API key. Not done; another search tool was used.
3. The autoresearch README tells users to start the agent with all permissions disabled. Addressed to humans; recorded as a design conflict, not followed.
4. The Axolotl README has an "AI Agent Support" section advertising `axolotl agent-docs` commands for coding agents. Informational; nothing run.
5. The llama.cpp repository root contains `AGENTS.md`, `CLAUDE.md` and a `skills/` folder. Not opened.
6. The search tool appends a reminder to include source links in the reply. Tool boilerplate; sources are listed below.

## Sources (chk 2026-11-11 for all)

| Key | Source | Version or date |
|---|---|---|
| S1 | https://pypi.org/rss/project/NAME/releases.xml and https://pypi.org/project/NAME/ for transformers, trl, peft, accelerate, torch, unsloth, axolotl, llamafactory, litgpt, mlx-lm, liger-kernel, bitsandbytes, lm-eval, lighteval, inspect-ai, vllm, verifiers, datasets, tokenizers, gptqmodel, torchao, llmcompressor, oumi, openpipe-art | versions and dates as written in Q4 |
| S2 | https://github.com/huggingface/transformers/releases | v5.19.0 (6 Oct) to v5.22.2 (6 Nov 2026) |
| S3 | https://github.com/huggingface/trl/releases | v1.11.0 to v1.17.1 (30 Oct 2026) |
| S4 | https://github.com/huggingface/trl/blob/main/docs/source/sft_trainer.md | docs for v1.16.0 and v1.17.1 |
| S5 | https://github.com/huggingface/trl/blob/main/docs/source/chat_templates.md | v1.17.1 |
| S6 | https://github.com/huggingface/trl/blob/main/docs/source/reducing_memory_usage.md | v1.17.1 |
| S7 | https://raw.githubusercontent.com/huggingface/trl/main/docs/source/grpo_trainer.md | main, v1.17.1 |
| S8 | https://raw.githubusercontent.com/huggingface/trl/main/docs/source/_toctree.yml | main, v1.17.1 |
| S9 | https://github.com/huggingface/trl/blob/main/docs/source/usage_stats.md | main |
| S10 | https://raw.githubusercontent.com/huggingface/trl/main/docs/source/lora_without_regret.md | main |
| S11 | https://github.com/huggingface/transformers/blob/main/docs/source/en/chat_templating.md | v5.19.0 |
| S12 | https://github.com/huggingface/transformers/blob/main/docs/source/en/llm_tutorial.md | main |
| S13 | https://github.com/huggingface/peft/releases | v0.19.0 (14 Apr) to v0.21.1 (2026) |
| S14 | https://github.com/huggingface/peft/blob/main/docs/source/developer_guides/troubleshooting.md ; .../package_reference/lora.md ; .../package_reference/lora_variant_dora.md ; .../developer_guides/quantization.md | main |
| S15 | https://thinkingmachines.ai/blog/lora/ | 29 Sep 2025 |
| S16 | https://arxiv.org/abs/2602.04998 | v2, 19 May 2026 |
| S17 | https://arxiv.org/abs/2605.28819 | 27 May 2026 |
| S18 | https://neurips.cc/virtual/2026/170044 | NeurIPS 2026 |
| S19 | https://arxiv.org/abs/2611.10844 | 7 Nov 2026 |
| S20 | https://arxiv.org/abs/2610.01509 | 1 Oct 2026 |
| S21 | https://arxiv.org/abs/2606.29526 | 28 Jun 2026 |
| S22 | https://arxiv.org/abs/2609.29421 | v2, 25 Sep 2026 |
| S23 | https://arxiv.org/abs/2611.12628 | 9 Nov 2026 |
| S24 | https://raw.githubusercontent.com/KellerJordan/modded-nanogpt/master/README.md ; https://github.com/KellerJordan/modded-nanogpt/pull/360 | record 92, 30 Aug 2026 |
| S25 | https://github.com/karpathy/nanochat (README, dev/LEADERBOARD.md) | last commit 3 Jul 2026 |
| S26 | https://github.com/karpathy/autoresearch | README, March 2026 |
| S27 | https://raw.githubusercontent.com/unslothai/unsloth/main/README.md ; https://unsloth.ai/docs/get-started/install/windows-installation ; https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements | main; pages undated |
| S28 | https://raw.githubusercontent.com/axolotl-ai-cloud/axolotl/main/README.md | main, highlights to 2026/10 |
| S29 | https://raw.githubusercontent.com/meta-pytorch/torchtune/main/README.md | main |
| S30 | https://github.com/hiyouga/LlamaFactory/releases | v0.9.5, 30 May 2026 |
| S31 | https://docs.vllm.ai/en/latest/getting_started/installation/gpu/ ; https://docs.vllm.ai/en/latest/usage/reproducibility/ | developer docs dated 8 Oct 2026 |
| S32 | https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/model_guide.md ; .../docs/python-api.md | main |
| S33 | https://github.com/ggml-org/llama.cpp | build b12255, 10 Nov 2026 |
| S34 | https://raw.githubusercontent.com/casper-hansen/AutoAWQ/main/README.md | main |
| S35 | https://huggingface.co/api/models/REPO for Qwen/Qwen3.5-4B, google/gemma-3-4b-it, mistralai/Mistral-Large-4-1T-A52B, meta-models/Muse-Spark-Open-816B-A42B ; https://huggingface.co/api/models?author=ORG for mistralai, meta-llama, microsoft, ibm-granite, HuggingFaceTB, openai, google, nvidia, deepseek-ai | live on 11 Nov 2026 |
| S36 | https://huggingface.co/docs/hub/repositories-licenses | live |
| S37 | https://huggingface.co/LiquidAI/LFM2.5-2.6B/raw/main/LICENSE | LFM Open License v1.0 |
| S38 | https://huggingface.co/mistralai/Mistral-Large-4-1T-A52B/raw/main/LICENSE | "2026 - Mistral", no version |
| S39 | https://dev.meta.ai/llama/llama3_3/license (redirected from llama.com) | release date 6 Dec 2024 |
| S40 | https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/ ; https://huggingface.co/blog/gemma4 ; https://huggingface.co/google/gemma-4-E4B-it/raw/main/generation_config.json | 2 Apr 2026 |
| S41 | https://github.com/QwenLM/Qwen3.8 | README, Aug 2026 |
| S42 | https://pluto.security/blog/hugging-face-malware-campaign-load-mine/ | 29 Oct 2026 |
| S43 | https://huggingface.co/docs/hub/security-pickle | live |
| S44 | https://www.pillar.security/blog/llm-backdoors-at-the-inference-level-the-threat-of-poisoned-templates ; https://labs.cloudsecurityalliance.org/research/csa-research-note-sglang-cve-2026-5760-gguf-rce-20260422-csa/ | search summaries only |
| S45 | https://arxiv.org/abs/2602.15195 | search summary only |
| S46 | https://raw.githubusercontent.com/DaoyuanLi2816/can-i-finetune-this/main/README.md | v0.4.1 |
| S47 | https://github.com/volcengine/verl/releases ; https://github.com/meta-pytorch/OpenEnv/releases | v0.9.1 (20 Sep 2026); v0.12.0 (5 Nov 2026) |
| S48 | https://arxiv.org/abs/2604.07941 ; https://arxiv.org/abs/2503.06072 | search summaries only |
| S49 | https://github.com/mbzuai-oryx/Awesome-LLM-Post-training ; https://github.com/Curated-Awesome-Lists/awesome-llms-fine-tuning | search summaries only |
| S50 | https://brunborg.com/n-gram-hinted-lm | 28 Oct 2026, author's claim |
| S51 | https://thenewstack.io/meta-muse-spark-open/ | Oct 2026, secondary |
