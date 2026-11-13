# Check of the two user-supplied research reports (ChatGPT and Gemini)

Dated 11 November 2026. Scout note. All sources were read on 11 November 2026 unless a row says otherwise.
Verification was closed early on the owner's instruction (relayed by the coordinator): a claim that was not reached carries the status "not checked (accepted as given by the user)".
Nothing found was installed, downloaded or run. No instruction inside a report, page or repository was followed.
C = ChatGPT report (`scouts/user-chatgpt.md`), G = Gemini report (`scouts/user-gemini.md`). Candidate rows: `user-reports.candidates.jsonl`.

## 1. Summary (ten lines)

1. The projects both reports name are real and mostly carry the licence stated. The errors sit in the details an implementer would copy: configuration syntax, what is enforced, statistics and versions.
2. Wrong on enforcement (G): Claude Code Read deny rules are not backed by a sandbox by default. The sandbox is off by default and does not exist on native Windows.
3. Wrong on configuration (G): Codex `[profiles.*]` tables, `sandbox_mode` in agent files and `mcpServers` inside `.claude/settings.json` do not work as written.
4. Wrong on loop mechanics (G): upstream autoresearch has no immutable evaluator; the pi-autoresearch MAD score is advisory, unscaled and mixes experiments; Codex `/goal` has no separate evaluator model.
5. Exaggerated numbers (G): AIDE "4x" is about 2x at equal model; the "316-run" ROCm study is one person's blog with single runs and misquoted figures; issue #22 says nothing about an "RLHF creativity ceiling".
6. Outdated versions (mostly G): TRL "v1.0, April 2026" (now 1.17.1), ms-swift 4.4 (now 4.6.0), AutoGluon 1.4 (now 1.6.3), Codex model names. The kit's own notes of 23 October are behind on five versions.
7. Confirmed and useful (mostly C): `hf skills add` links skills into `.claude/skills`; two Hugging Face skills publish or submit paid jobs by default; AGENTS.md handling in Claude Code; `codex exec` defaults; the one-shot holdout with a hash-chained ledger.
8. Consequences for the design: the harness must own timer, evaluator, seed and the keep decision; the loop must be driven from outside the agent session; the docs must say per agent and OS what is enforced and what is advice.
9. Suspicious: autoresearch.lol labels buttons as the GitHub repository but links them to mirofish.my, a commercial sign-in site. Both reports and several READMEs contain run-this commands and "never stop" or "disable all permissions" instructions.
10. Not checked: see section 6, with the status the owner chose.

## 2. Checked claims

| # | Rep. | Claim | Verdict | Source | Checked |
|---|---|---|---|---|---|
| 1 | G | Upstream autoresearch: 9-step loop, 5-minute budget, example val_bpb 0.997900, about 12 experiments per hour | Verified | karpathy/autoresearch README and program.md @228791fb | 11 Nov |
| 2 | G | Its evaluator is immutable | Contradicted: prepare.py is read-only by instruction only; the budget check, the evaluation call and the seed sit in the editable train.py | program.md; train.py of a fork | 11 Nov |
| 3 | C, G | autoresearch is MIT-licensed | Unverified: the README says MIT, but there is no LICENSE file and no licence in the API metadata | GitHub API | 11 Nov |
| 4 | G | "RLHF creativity ceiling (Issue #22)"; switch strategy after 15 discards | Contradicted: issue #22 is titled "Low creativity" (7 Mar 2026), one comment pointing to PR #80; no RLHF, no measurement, no such rule | GitHub issue API | 11 Nov |
| 5 | C, G | jsegov/autoresearch-win-rtx runs on native Windows with consumer RTX cards, including the 50 series | Verified with limits: tested only on an RTX 3080 10 GB; eager mode, no torch.compile; floors 8 or 10 GB; last push 14 Mar 2026 | fork README, GitHub API | 11 Nov |
| 6 | G | pi-autoresearch MAD gate: after 3+ baseline runs, re-test below 1.0x, lock in at 2.0x | Contradicted: MAD over all metric values of the session (any 3+ experiments), raw MAD without 1.4826, "Advisory only — never auto-discards" | README and index.ts, v1.9.0 (7 Oct 2026) | 11 Nov |
| 7 | G | marcelopazzo plugin offers MCP tools init_experiment, run_experiment, log_experiment | Verified (v0.1.3, 19 Apr 2026; 1 star) | plugin README | 11 Nov |
| 8 | G | The plugin shows live metrics in the status line | Contradicted: status line is not shipped; a dashboard runs on localhost:8765 | plugin README | 11 Nov |
| 9 | G | autoresearch-mlx reached 1.294 val_bpb on an M4 Max | Verified (1.294526, from 1.596971) | fork README | 11 Nov |
| 10 | C | AMD fork detects ROCm through `torch.version.hip` and disables torch.compile | Verified | andyluo7/autoresearch train.py | 11 Nov |
| 11 | G | "316-run AMD ROCm study": 20.0% MFU, +43% steps, 40 controlled runs | Source found (personal blog, 10 Apr 2026). Contradicted in detail: sessions of 231, 25 and 15 experiments; MFU 19.0%; +43% is against default compile; the "40 runs" are 25 + 15 single runs. As general rules: Unverified (one blog) | hectorhernandez.dev post | 11 Nov |
| 12 | G | OpenEvolve uses MAP-Elites with islands | Verified; "cascade evaluators" not found in the README | OpenEvolve README (Apache-2.0) | 11 Nov |
| 13 | G | AIDE wins 4x more medals than the best linear agent | Contradicted: AIDE gpt-4o 8.7 ± 0.5 against OpenHands gpt-4o 4.4 ± 1.4, about 2x at equal model | MLE-bench, arXiv 2410.07095 v6, Table 2 | 11 Nov |
| 14 | G | AI-Scientist-v2 paper passed workshop review and appeared in Nature | Verified from the vendor page only (26 Mar 2026); repository has a custom licence, last push 19 Dec 2025 | sakana.ai, GitHub API | 11 Nov |
| 15 | C | FT-Dojo: 13 tasks, 5 domains; FT-Agent best on 10 of 13 | Verified (authors' claim; ICML 2026, PMLR 306) | arXiv 2603.01712 | 11 Nov |
| 16 | C | Agent Lightning quick start needs one A100 | Verified | docs/01-quick-start.md, v1.0 | 11 Nov |
| 17 | C | `hf skills add` installs to `.agents/skills` and links into `.claude/skills` | Verified: symlink unless `--dest`; no `--claude` flag | huggingface_hub v2.4.0 CLI reference and cli/skills.py | 11 Nov |
| 18 | C | train-sentence-transformers skill publishes the model at the end | Verified: "Public Hub push at end-of-run" | huggingface/skills SKILL.md | 11 Nov |
| 19 | C | huggingface-llm-trainer skill uses paid HF Jobs with a write token | Verified; it also tells the agent to submit "immediately" | huggingface/skills SKILL.md | 11 Nov |
| 20 | C | trl-training skill is local only | Verified | huggingface/skills SKILL.md | 11 Nov |
| 21 | C | Claude Code reads AGENTS.md; `@AGENTS.md` import | Verified with conditions: native from v2.1.277, and only when no CLAUDE.md or CLAUDE.local.md exists | code.claude.com/docs/en/memory | 11 Nov |
| 22 | G | Keep CLAUDE.md under 80 lines ("instruction slots") | Unverified (blog source); the official page says "target under 200 lines" | code.claude.com/docs/en/memory | 11 Nov |
| 23 | G | Hook exit code 2 blocks tool calls and Stop | Verified; the report omits the cap of 8 consecutive Stop continuations | code.claude.com/docs/en/hooks | 11 Nov |
| 24 | G | `permissions.deny` Read rules are sandbox-backed, so shell commands inherit them | Contradicted as stated: true only with the sandbox on (off by default, none on native Windows); otherwise a Python script can read the path | permissions and sandboxing pages | 11 Nov |
| 25 | G | `mcpServers` block in `.claude/settings.json` | Contradicted: project servers go in `.mcp.json`; settings.json holds approval keys only | code.claude.com/docs/en/mcp | 11 Nov |
| 26 | C | `--allowedTools` approves automatically and is no security boundary | Verified | headless and permissions pages | 11 Nov |
| 27 | G | `claude -p` flags (`--allowedTools`, `--max-budget-usd`, JSON output) | Verified; from v2.1.302 `-p` starts in Manual mode, and `--bare` skips hooks | code.claude.com/docs/en/headless | 11 Nov |
| 28 | G | `/output-style concise` from v2.1.237 | Unverified: docs give v2.1.269 for `/output-style` in `-p` | headless page | 11 Nov |
| 29 | G | Subagent `isolation: worktree` | Verified | sub-agents page | 11 Nov |
| 30 | C, G | `codex exec`: read-only by default, `--sandbox workspace-write`, `--ephemeral`, `--json`, `--full-auto` removed | Verified | learn.chatgpt.com/docs/non-interactive-mode | 11 Nov |
| 31 | G | `[profiles.autoresearch]` table in config.toml | Contradicted: since Codex 0.134.0 `--profile` overlays `~/.codex/<name>.config.toml` and no longer reads `[profiles.*]` | Codex config docs | 11 Nov |
| 32 | G | Agent TOML with `sandbox_mode = "read-only"` | Contradicted: agent files cannot override the sandbox and "don't create a separate read-only sandbox" | Codex subagents page | 11 Nov |
| 33 | G | `[agents]` keys `enabled`, `max_concurrent_threads_per_session` | Verified | Codex config reference | 11 Nov |
| 34 | G | `/goal` calls a separate evaluator model after every turn | Contradicted: the working model itself calls `update_goal` | openai/codex ref c9bbed2d, codex-rs/ext/goal | 11 Nov |
| 35 | G | Subagents cost 2.6x the tokens | Unverified (forum only); official pages give no multiplier | Codex and Claude Code subagent pages | 11 Nov |
| 36 | G | Codex models gpt-5.3-codex, gpt-5.4-mini | Outdated: the docs use gpt-6.1-sol, gpt-6-luna, gpt-6-astra | Codex config docs | 11 Nov |
| 37 | C | Split before preprocessing; group splits for dependent samples | Verified | scikit-learn 1.9.1 docs | 11 Nov |
| 38 | C | One-shot holdout behind a receipt, hash-chained ledger, "model proposes, trusted code decides" | Verified as described (single-author preprint, finance) | arXiv 2611.06607 v1 (4 Nov 2026) | 11 Nov |
| 39 | C | Reusing a holdout overfits it | Verified | arXiv 1502.04585 | 11 Nov |
| 40 | C, G | Throughput first under a fixed wall-clock budget | Partly verified: tuning playbook and one fork README support it; no controlled study | tuning_playbook README; autoresearch-mlx README | 11 Nov |
| 41 | G | TRL v1.0, April 2026 | Outdated: v1.0.0 is dated 31 Mar 2026; current is v1.17.1 (30 Oct 2026) | GitHub releases API | 11 Nov |
| 42 | C, G | Liger Kernel 0.8.5; Axolotl 0.21.1; DeepSpeed 0.19.9; Optuna 5.0.0; TorchTitan 0.4.0 | Verified (21 Oct, 27 Oct, 29 Oct, 7 Sep, 28 Oct 2026) | GitHub releases API | 11 Nov |
| 43 | C | Axolotl recommends WSL2 or Docker on Windows | Unverified: the README has no Windows statement | Axolotl README | 11 Nov |
| 44 | G | TorchTitan TFLOPs figures | Unverified: not on the release page | v0.4.0 release notes | 11 Nov |
| 45 | G | ms-swift v4.4 | Outdated: v4.6.0 (13 Oct 2026) | GitHub releases API | 11 Nov |
| 46 | G | lm-evaluation-harness "September 2026 zero-fork plugin system" | Unverified: not in v0.4.13 (31 Aug 2026); entry-point discovery exists on main | release notes; lm_eval/api/registry.py | 11 Nov |
| 47 | G | Trackio MCP: `trackio show --mcp-server`, `trackio[mcp]` | Verified (0.45.0); the server now has 12 read and 3 mutation tools | trackio docs | 11 Nov |
| 48 | G | Unsloth: `unsloth start`, Apache-2.0 core, AGPL Studio, Windows support | Verified; "2x faster, 70% less VRAM" is a vendor claim | Unsloth README, release 6 Nov 2026 | 11 Nov |
| 49 | C, G | FAISS 1.16.0 with e-means | Verified: changelog 9 Nov, GitHub release and PyPI 10 Nov 2026 (G's "9 November" is the changelog date); "10-45x" is the authors' claim; blog and forum figures Unverified | FAISS changelog, PyPI, arXiv 2611.09501 | 11 Nov |
| 50 | G | GEPA: ICLR 2026 oral; "6%-10% on average" | Venue verified; figure imprecise (GRPO by 6% on average, MIPROv2 by over 10%) | arXiv 2507.19457 v2 | 11 Nov |
| 51 | C, G | TabPFN: Apache-2.0 code, non-commercial newer weights | Verified (v9.2.0); first use opens a browser login | TabPFN README | 11 Nov |
| 52 | G | AutoGluon 1.4 "extreme" preset as current | Outdated: current v1.6.3 (18 Sep 2026); the preset is from v1.4.0 and experimental | GitHub releases | 11 Nov |
| 53 | C | torchao 0.18.0 with reduced feature work; torchtune unmaintained | Verified; G's "July 2025" for torchtune is Unverified | READMEs | 11 Nov |
| 54 | G | `flash-attn-4` package exists | Verified (4.0.0b38, beta, 4 Nov 2026) | PyPI, arXiv 2603.05451 | 11 Nov |
| 55 | G | LightGBM moved to lightgbm-org | Verified; verl and LLaMA-Factory also moved or were renamed | GitHub API | 11 Nov |
| 56 | C | autoresearch.lol links its "GitHub repo" button to another product | Verified: four buttons link to https://mirofish.my/ | page text | 11 Nov |

Kit notes of 23 October 2026 that are now behind: TRL 1.16.0 (now 1.17.1), Liger 0.8.4 (0.8.5), Axolotl 0.21.0 (0.21.1), DeepSpeed 0.19.7 (0.19.9), TorchTitan 0.3.0 (0.4.0), Trackio tag v0.5.0 (release 0.45.0), Trackio MCP "12 read tools" (plus 3 mutation tools now), TRL 1.0.0 dated 30 March (GitHub timestamp 31 March 14:15 UTC). The open question in the notes on where `hf skills add` installs is answered by row 17.

## 3. What the kit could take

Core (standard library only):

- Keep rule. Before the loop, repeat the unchanged baseline at least five times with harness-assigned seeds and store mean and spread `s`. Keep a candidate only if `mean(baseline) - mean(candidate) >= m` for a lower-is-better metric, with `m` declared before the loop and `m >= 2 * s * sqrt(1/k_candidate + 1/k_baseline)`. The formula is this scout's starting point, not taken from a source.
- Bootstrap gate as a second option, after `rigor.py`: flags `--seeds 3 --confidence 0.95`, 20,000 resamples, ledger fields hash, desc, samples, mean, std, status, p_better. Unlike `rigor.py`, vary the seed.
- Display only: scaled MAD (1.4826 x MAD) of baseline repeats. Never "improvement divided by the MAD of all experiments".
- The harness owns the timer, the evaluator call (separate process, protected file) and the seed.
- Final-test ledger: write and flush a receipt before the test set is opened, refuse a second open, store the SHA-256 of the previous line in every record.
- Refuse a launch whose hash of change plus configuration is already in the ledger.
- Checks gate: a protected checks command with its own timeout after every run that exits 0; state `checks_failed`; no keep on failure; checks time is not part of the metric.
- Loop bounds: iteration cap, stop after a set number of failures in a row, next to the user's budget limits.
- Loop state in files (goal, append-only log, ideas) and a fixed resume prompt that names them.
- Git: revert inside a loop branch; no `git reset --hard` or `git clean` on the user's tree.
- File layout: `AGENTS.md` holds the rules; `CLAUDE.md` contains `@AGENTS.md`; no symbolic links; each file under 200 lines.
- Claude Code launcher: `claude -p` without `--bare`, explicit `--permission-mode` and `--allowedTools`, `--permission-prompts none`, `--output-format json` (read `total_cost_usd`), `--max-budget-usd`, an explicit MCP configuration, and a canary call that the guard hook must deny before any training starts.
- Codex launcher: `codex exec --sandbox workspace-write --ephemeral --json`, approval policy `never` as an override, token use from `turn.completed` events, no `[profiles.*]` table. Reviewer and analyst as `.codex/agents/*.toml`, documented as advice-only read-only.
- Guard rules for `push_to_hub`, `hf jobs`, the `hf_jobs` tool and tracker deletion.
- Docs: one table per agent and OS that says what is enforced and what is advice.
- Rule texts: split before preprocessing; group split for dependent samples; profile throughput before the search; new baseline when budget, hardware or batch size changes.

Optional modules:

- Claude Code sandbox with `sandbox.filesystem.denyRead` for sealed data and `allowUnsandboxedCommands: false` (WSL2, Linux, macOS only).
- MCP servers written to `.mcp.json`; Trackio MCP at `http://127.0.0.1:7860/mcp/` with read tools only and no write token.
- Benchmark fixtures: jsegov/autoresearch-win-rtx on Windows (`--smoke-test`; `AUTORESEARCH_DISABLE_AUTOTUNE=1` for comparable runs), autoresearch-mlx on macOS.
- Config-only loop mode with JSON proposals; branching search under the same gate; finalize into independent branches.
- Reference stack with corrected versions: TRL 1.17.1, Liger Kernel 0.8.5, Optuna 5.0.0, lm-evaluation-harness 0.4.13, Unsloth (trial), trl-training skill (trial).

## 4. Wrong, exaggerated or unverifiable

- Contradicted by a primary source: table rows 2, 4, 6, 8, 11, 13, 24, 25, 31, 32, 34.
- Outdated: rows 36, 41, 45, 52, and the kit-note versions listed under the table.
- Exaggerated or imprecise: row 11 (figures), row 13 (4x), row 50 (6%-10%), row 49 (G's release date), Unsloth "2x faster, 70% less VRAM" (vendor claim without conditions), e-means "10-45x" (authors' claim, paper five days old).
- Unverifiable from primary sources: rows 3, 22, 28, 35, 43, 44, 46, torchtune "July 2025", the blog and forum speed figures for e-means, and every technique rule that rests only on the ROCm blog.
- Design advice in the Gemini report that conflicts with the brief: a contract with "NEVER STOP to ask permission once the loop begins", `git reset --hard HEAD~1` as revert, `--allowedTools "Bash(*)"`, `approval_policy = "never"` in a 60-iteration shell loop, and `docker run --net=host ... :latest` for an MCP server.

## 5. Redirect attempts and suspicious content

None of the following was followed.

- ChatGPT report: a ZIP download link (a chatgpt.com library link and a `sandbox:` path); prompts meant to be pasted into an agent; commands (`hf skills add ...`, `codex exec ...`, `claude -p ...`); `?utm_source=chatgpt.com` on links.
- Gemini report: install and run commands (`uv pip install "trackio[mcp]" unsloth trl faiss-gpu==1.16.0`, `/plugin marketplace add https://github.com/marcelopazzo/claude-code-autoresearch`, `/plugin install ...`, `pip install flash-attn-4`, `docker run ... --net=host ... ghcr.io/optuna/optuna-mcp:latest`, `unsloth start claude --model ...`, a 60-iteration `codex exec --ephemeral` loop) and the contract text quoted in section 4.
- karpathy/autoresearch: README "(and disable all permissions)"; program.md "LOOP FOREVER" and "NEVER STOP ... do NOT pause to ask the human".
- jsegov/autoresearch-win-rtx: the same permission line and `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
- pi-autoresearch: a README section "Picking a free chord (guidance for agents)" and `pi install npm:pi-autoresearch`.
- marcelopazzo/claude-code-autoresearch: Stop-hook text "Don't stop until the user runs /autoresearch off or the iteration cap is hit."
- huggingface/skills: "you MUST create the training script AND submit the job immediately."; "Do NOT save to local files unless the user explicitly requests it."; "Do not synthesize a training script from this file alone."
- Unsloth and Axolotl READMEs: install one-liners that pipe a download into a shell (`curl ... | sh`, `irm ... | iex`). AIDE README: "Try Weco". ROCm blog: advice to the reader such as "Try `torch.compile` again."
- Claude Code docs pages open with "Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt"; some fetch-tool answers suggested further URLs or running `hf skills --help` locally.
- Misleading links: on autoresearch.lol the header "GitHub" button, "One-click deploy", "View the GitHub repo" and "Read the full explainer" all lead to `https://mirofish.my/`, a commercial site with sign-in and pricing that does not name an operator. The GitHub project MiroFish lists a different domain (mirofish.ai) as its homepage. Real repository links appear only under "Primary sources" and in the footer. Nothing was downloaded or run from either site.

## 6. Not checked

Status of every item below: not checked (accepted as given by the user).

- train.py "630 lines"; "overnight" for the M4 Max result; the miolini/autoresearch-macos README.
- The Nature article page itself (only the vendor's page was read).
- Versions of the remaining projects (Megatron-Core, XGBoost, LightGBM, Triton, SLIME, SkyRL, Flax, Equinox, MLX and others); for these only existence and licence were confirmed through the GitHub API.
- Optuna 5.0 feature claims and the optuna-mcp container image.
- The Transformer Engine claim about consumer Blackwell cards; FlashAttention-4 support on the user's GPU and on Windows.
- Third-party reproductions of the e-means speed-ups.
- Behaviour of `/goal` under `codex exec`.
- Whether `hf skills add` falls back to copying on native Windows, where symbolic links need extra rights.
- Facts quoted from other scouts' notes (arXiv 2610.10491, modded-nanogpt record 92, Codex CLI 0.167.0) were not re-read.
- No candidate was tried: every Trial and Assess row still lacks its test.
