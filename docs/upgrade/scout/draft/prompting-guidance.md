# Prompting guidance for the newest models, applied to the kit's prompts and agent files

Scout area: vendor prompting guidance. Checked 10 and 11 November 2026. No local commands were run. Kit files were
read only; nothing outside the two scout output files was changed. A second agent finished the note on
11 November 2026 after the first one stopped; what it added or corrected is listed under "Completion pass" at the end.

Convention: every claim ends with `[source ID, status]`. The "Sources" table gives each source's URL, its version
or date, and the date checked. Status: **Verified** = read in the primary source in this session; **Inferred** = my
conclusion from verified facts; **Unverified** = secondary source, search summary, or not confirmed.
Caveat on reading method: pages marked "(summary)" in the table were read through a fetch tool that summarises with
a small model, so exact strings from them should be re-checked before they are hard-coded.

## Summary (10 lines)

1. Newest models: Claude Fable 5.2 (in Claude Code since v2.1.321, 9 Nov 2026), Opus 5.5 (Claude Code default on every plan), Sonnet 5.5, Haiku 5.5; OpenAI GPT-6 family (Astra, 6.1 Sol, 6.1 Terra, Luna). The kit predates Fable 5.2.
2. All three vendors now ask for short, specific, plainly worded instruction files. Anthropic says capital-letter emphasis makes current models over-apply a rule; rules that cannot bend belong in hooks or permissions.
3. Fable 5.2 applies rules as written: under a "never" rule it took an approved step in about 1 of 10 tries, under a "get a go-ahead first" rule in about 9 of 10. The kit's prompt files use "never" on 39 lines in 12 files; several of these rules have no reason and none says what to do when nobody can approve.
4. A safeguard category (`frontier_llm`) can refuse benign machine-learning work and is billed. The vendor names it for Sonnet 5.5 and Haiku 5.5 as well as for the Fable models, so the analyst subagent is exposed too. Claude Code's automatic model switch lists only biology and cybersecurity. The kit must treat a refusal as a clean stop and should not make Fable its default model.
5. Effort is the control for thinking depth, not prompt words. `ultrathink` raises one turn only. Since v2.1.317 a subagent on a different model no longer inherits the session's effort, so both kit agent files need an explicit `effort`.
6. The kit's rules exist in three near-copies (CLAUDE.md block, skill, kickoff prompt) that already differ. Vendors warn that conflicting copies are resolved arbitrarily. Keep one copy of each rule and point to it.
7. SKILL.md, the block and both agent files use Claude-Code-only and POSIX-only vocabulary (Monitor tool, `/loop`, `python3`, tmux, SIGTERM, `tail`, `sed`). Codex and Cursor read the same files and would have to guess.
8. Cursor loads `.claude/agents/` and `.claude/skills/` for compatibility but documents no `hooks` or `tools` field; a Codex agent file cannot set a read-only sandbox. The reviewer's read-only guarantee is Claude-Code-only unless each port adds its own, and it is weak in Claude Code too: on native Windows the hook probably fails open (agent files keep `python3` after install and their hook lacks `onFailure: block`), and in a non-interactive run in a folder nobody trusted Claude Code skips a project subagent's own hooks. Enforce read-only in the settings-level guard by agent type.
9. After compaction Claude Code re-injects the project-root CLAUDE.md and only the first 5,000 tokens of an invoked skill. SKILL.md is about that size, so its last sections (ask/stop list, references index) are at risk.
10. Roles: main agent and loop worker on Opus 5.5 at `high`; reviewer `opus` at `high` in a fresh context; analyst `sonnet` at `medium` (trial `haiku` at `medium`; `low` only if scored answers hold); research scout at `high`. Opus 5.5's default is `medium`, so `high` is a choice to confirm by comparison. Evidence on same-model judges is mixed, with verified reports of own-family bias in rubric judging, so keep/revert decisions must rest on harness code, not on a judge model.

## Sources

| ID | Source (URL) | Version or date of source | Checked |
|---|---|---|---|
| S1 | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices | living page; per-model table lists Fable 5.2 to Haiku 5.5 | 2026-11-10 |
| S2 | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2 | for `claude-fable-5-2` | 2026-11-10 |
| S3 | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1 | for `claude-fable-5-1` | 2026-11-11 |
| S4 | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5 | for `claude-opus-5-5` | 2026-11-10 |
| S5 | https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2 | for `claude-fable-5-2` | 2026-11-11 |
| S6 | https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback | billing rule dated "as of September 2026" | 2026-11-11 |
| S7 | https://platform.claude.com/docs/en/about-claude/pricing | living page | 2026-11-11 |
| S8 | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | living page, no date | 2026-11-11 |
| S9 | https://code.claude.com/docs/en/skills (summary, first 100K characters) | Claude Code docs at v2.1.322 | 2026-11-11 |
| S10 | https://code.claude.com/docs/en/sub-agents (summary, first 100K characters) | Claude Code docs at v2.1.322 | 2026-11-11 |
| S11 | https://code.claude.com/docs/en/memory | Claude Code docs at v2.1.322 | 2026-11-11 |
| S12 | https://code.claude.com/docs/en/model-config (first part summary, rest raw) | Claude Code docs at v2.1.322 | 2026-11-11 |
| S13 | https://code.claude.com/docs/en/context-window | Claude Code docs at v2.1.322 | 2026-11-11 |
| S14 | https://code.claude.com/docs/en/best-practices | Claude Code docs at v2.1.322 | 2026-11-11 |
| S15 | https://code.claude.com/docs/en/changelog (summary; entries 2.1.311 to 2.1.322 only) | newest entry 2.1.322, 2026-11-10 | 2026-11-11 |
| S16 | https://developers.openai.com/api/docs/guides/prompt-guidance (summary) | "Using GPT-6", undated | 2026-11-11 |
| S17 | https://learn.chatgpt.com/docs/agent-configuration/agents-md (summary; redirect target of developers.openai.com/codex/guides/agents-md) | undated | 2026-11-11 |
| S18 | https://learn.chatgpt.com/docs/agent-configuration/subagents (summary) | undated | 2026-11-11 |
| S19 | https://learn.chatgpt.com/docs/build-skills (summary) | undated | 2026-11-11 |
| S20 | https://learn.chatgpt.com/docs/prompting and https://learn.chatgpt.com/docs/model-selection (summaries) | undated | 2026-11-11 |
| S21 | https://cursor.com/docs/context/rules (summary) | undated | 2026-11-11 |
| S22 | https://cursor.com/docs/context/subagents (summary) | undated | 2026-11-11 |
| S23 | https://cursor.com/docs/context/skills (summary) | undated | 2026-11-11 |
| S24 | https://cursor.com/docs/cli/using (summary) | undated | 2026-11-11 |
| S25 | https://cursor.com/blog/agent-best-practices (summary) | 2026-01-09 | 2026-11-11 |
| S26 | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5 (added on completion) | for `claude-sonnet-5-5` | 2026-11-11 |
| S27 | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5 (added on completion) | for `claude-haiku-5-5` | 2026-11-11 |
| S28 | https://platform.claude.com/docs/en/build-with-claude/effort (added on completion) | living page with per-model starting levels | 2026-11-11 |
| S29 | https://code.claude.com/docs/en/hooks (added on completion; summary, first 100K of 293K characters, cross-checked against the quotes in `platform-claude-code.md` in this folder) | Claude Code docs at v2.1.322 | 2026-11-11 |
| S30 | https://code.claude.com/docs/en/settings-reference (added on completion; summary with quoted entries, characters 0 to 200K of 455K) and https://code.claude.com/docs/en/permissions | Claude Code docs at v2.1.322 | 2026-11-11 |
| S31 | https://code.claude.com/docs/en/scheduled-tasks (added on completion) | Claude Code docs at v2.1.322 | 2026-11-11 |
| P1 | https://arxiv.org/abs/2602.11988 "Evaluating AGENTS.md" (abstract) | v3, 2026-09-29 | 2026-11-11 |
| P2 | https://arxiv.org/abs/2607.27250 "Do Context Files Help Coding Agents?" (abstract) | v1, 2026-07-28 | 2026-11-11 |
| P3 | https://arxiv.org/abs/2610.31715 census of AGENTS.md and CLAUDE.md (abstract) | v2, 2026-10-26 | 2026-11-11 |
| P4 | https://arxiv.org/abs/2610.32578 "Lessons Outlive Their Failures" (abstract) | v1, 2026-10-23 | 2026-11-11 |
| P5 | https://arxiv.org/abs/2610.11647 "One Skill Too Many" (abstract) | v2, 2026-10-13 | 2026-11-11 |
| P6 | https://arxiv.org/abs/2602.12670 SkillsBench (abstract) | v4, 2026-06-14 | 2026-11-11 |
| P7 | https://arxiv.org/abs/2608.11888 "Agent Skills Can Be Harmful" (abstract) | v1, 2026-08-12 | 2026-11-11 |
| P8 | https://arxiv.org/abs/2610.00084 "Scientific Agents: profession-specific system prompts" (abstract; page showed 7 Sep 2026, which does not match the ID month) | v1 | 2026-11-11 |
| P9 | https://arxiv.org/abs/2606.20093 self-preference test, four model families (abstract) | v1, 2026-06-18 | 2026-11-11 |
| P10 | https://arxiv.org/abs/2610.08900 "Humanize: Judgement Engineering" (abstract) | v2, 2026-10-08 | 2026-11-11 |
| P11 | https://arxiv.org/abs/2609.20804 harness design study (abstract) | v1, 2026-09-17 | 2026-11-11 |
| P12 | https://arxiv.org/abs/2607.01456 SKILL.md smells (abstract) | v2, 2026-07-03 | 2026-11-11 |
| P13 | https://arxiv.org/abs/2608.14036 "Demystifying Agent Skills" (abstract) | v1, 2026-08-14 | 2026-11-11 |
| P14 | https://arxiv.org/abs/2404.13076 "LLM Evaluators Recognize and Favor Their Own Generations" (abstract; added on completion) | v1, 2024-04-15 | 2026-11-11 |
| P15 | https://arxiv.org/abs/2604.06996 "Self-Preference Bias in Rubric-Based Evaluation of Large Language Models" (abstract; added on completion) | v3, 2026-08-03 | 2026-11-11 |
| W1 | web search summaries only: judge self-preference papers (arXiv 2604.06996 and others; that paper was opened on completion, see P15), Cloud Security Alliance notes on instruction-file poisoning (2026-03-10, 2026-10-27), SKILL-INJECT benchmark, skill linters, instruction-file sync tools, SkillOpt | not opened | 2026-11-11 |
| W2 | https://www.pillar.security/blog/new-vulnerability-in-github-copilot-and-cursor-how-hackers-can-weaponize-code-agents (summary; added on completion) | 2025-03-18, the researchers' own report | 2026-11-11 |
| K | kit files in this repository (read 2026-11-10 and 2026-11-11) | commit 5ea9659 baseline | 2026-11-11 |

## Q1. Anthropic guidance that matters for the kit

### Models and defaults
- Current lineup: Fable 5.2 and Mythos 5.2 (newest), Fable 5.1, Fable 5, Opus 5.5, Opus 5, Opus 4.8, Sonnet 5.5, Sonnet 5, Haiku 5.5. [S1, S7, Verified]
- Fable 5.2: 1M context (default and maximum), 128k output tokens, adaptive thinking always on, forced tool choice unsupported, API default effort `high`. [S5, Verified]
- Anthropic's own positioning: start with the latest Opus model and move to Fable 5.2 only when evaluations on Opus at higher effort still fall short. [S5, Verified]
- Claude Code: default model is Opus 5.5 on every plan and on Bedrock and Google Cloud (Sonnet 4.5 on Foundry); no Fable model is a default. Default effort is `medium` for Fable 5.2, Opus 5.5, Sonnet 5.5 and Haiku 5.5. [S12, S14, Verified]

### Emphasis, reasons, length, structure, examples
- Plain wording beats emphasis. Capital letters and "IMPORTANT" make current models over-apply a rule; a rule that cannot bend should become a hook or deny rule, and a rule that gets lost means the file is too long. [S1, S14, Verified]
- Give the reason with the instruction; the model generalises from the reason. [S1, Verified]
- Say what to do, not only what not to do. [S1, Verified]
- XML tags help when a prompt mixes instructions, context and data; one sentence of role helps; 3 to 5 varied examples in tags when output format matters. [S1, Verified]
- CLAUDE.md: target under 200 lines per file; longer files lower adherence; contradictions are resolved arbitrarily; it is delivered as a user message, so compliance is not guaranteed. Describe only what the repository does not already show. [S11, S14, Verified]
- Skills: SKILL.md body under 500 lines; references one level deep; a table of contents for reference files over 100 lines; no time-sensitive content in the body (use a dated or "old patterns" section); one term per concept; third-person description; forward-slash paths; do not assume tools are installed; scripts should handle errors themselves. Build at least three evaluations and a no-skill baseline before writing more text. [S8, Verified]
- Skill content enters once and is not re-read, so write lasting guidance as standing instructions. [S9, Verified]

### Effort and thinking
- Effort replaces "think hard" wording. Those phrases are ordinary text; only `ultrathink` is a keyword, and it affects a single turn. [S14, Verified]
- Fable 5.2: `high` for hard coding, research, agentic work and long unattended runs; `low` for well-specified, high-volume work such as fast subagents; `medium` for interactive coding; `xhigh` only with a measured gain; `max` to measure a ceiling. Most of the gain is present at `high`. More early stopping at `low` and `medium`. [S2, S5, Verified]
- Effort names do not mean the same amount of thinking across models; re-run any effort comparison on a new model. [S3, Verified]
- Opus 5.5 at `medium` matches or exceeds Opus 5 at `high` in Anthropic's tests. [S4, S12, Verified]
- Starting levels are per model and override the generic effort table, which lists `low` for "subagents": Fable 5.2 start at `high`; Opus 5.5 defaults to `medium` and the page asks for a comparison of levels on your own tasks; Sonnet 5.5 start at `medium` for well-specified agentic multistep tool use and at `high` for harder or longer work; Haiku 5.5 start at `medium` for most work, `low` for chat, short tool tasks and simple high-volume requests. [S28, S26, Verified; added on completion]
- Prompts, skills or tool descriptions that ask the model to write out its thinking can be declined (`reasoning_extraction`); ask for a short explanation, the evidence, or a summary of actions instead. This category has no fallback model. [S6, Verified]
- Instructions to think less do not stop Fable 5.2 thinking at `medium` and above; lower the effort instead. [S5, Verified]

### Finishing work, approvals and caution
- Interactive use: "keep going, don't be lazy" lines now cause over-work; give a check to pass instead. For unwatched runs use a goal or a Stop hook. [S14, Verified]
- Autonomous use: Fable 5.1 and 5.2 can end a turn with a plan, a list of what remains, or a permission question. A system-prompt block that says the user is not watching, separates ordinary obstacles from deliberate blocks, and tells the model to do announced steps fixes most of it (about half as many sessions ended with doable work left, at about 30% more output tokens). [S2, S3, Verified]
- Opus 5.5 unattended: a text-only end of turn is a report, not proof of completion. Keep a checklist, send a continuation that names open items, optionally have a smaller model check a stated completion condition, and stop after two or three automatic continuations. [S4, Verified]
- Approvals: name the exact actions an approval rule covers; a broad rule held back about half of routine requests. Name steps that need no approval; a general "act more freely" line changed nothing. Write the exception into the rule. [S2, Verified]
- Caution accumulates: delete stale cautions from notes and memories; check what reviewer agents attach, because a reviewer's condition can stop the main agent (a "stop at the first error" condition stopped retries in about a third of tries). [S2, Verified]
- Ownership wording changes scope: telling the model the codebase is its own raised refactoring from under a tenth to about half of tasks, with 1.5 times the output tokens. Leave it out where the user owns the code. [S2, Verified]
- Instruction changes should be made in new conversations: on Fable 5.2 any edit to earlier turns, the system prompt or tools invalidates thinking blocks for every account. Claude Code builds requests itself, so this matters only to custom API callers. [S5, Verified]

### Delegation
- Delegation does not improve an answer; a fresh reviewer helps because it has not seen the author's reasoning. Subagents cost extra tokens and the context window is rarely the limit now. [S14, Verified]
- Fable 5.2 delegates readily where prompts invite it, and subagents can be a large share of session cost. Review standing delegation lines in system prompts, skills and agent files; describe cost first, when delegation is and is not worth it, and how to brief (about a third less delegation at equal task success). [S2, S5, Verified]
- Subagent system prompt: the Markdown body is the whole prompt (plus environment details); say what to do and what to return. Keep descriptions short; combined custom-agent descriptions over 15,000 tokens trigger a warning. [S10, Verified]

### What the newest models over-apply or ignore
- Over-apply: literal rules and style limits (Fable 5.2; a sentence-length cap makes prose choppy); delegation when invited (Fable 5.2, Opus 5); verification (Opus 5); initiative and scope (Sonnet 5.5); unrequested extras and test files (Fable 5.1). [S1, S2, S3, Verified]
- Ignore or under-do: think-less lines at `medium`+ (Fable 5.2); user-facing progress text during long tool chains (Fable 5.1, 5.2, Opus 5.5); search at `low` effort (Fable 5.1); long agent prompts cause early stopping on Haiku 5.5. [S1, S3, S5, Verified]
- The Opus 5 and Opus 4.8 per-model pages were not opened; the items above for those models come from the index table in S1. [S1, Verified for the table only]
- Sonnet 5.5 (the analyst's model), page opened on completion: at `low` it keeps its thinking short and can report work as done without a check that exercises it; at `low` and `medium` it is more likely to stop and check in on long tasks; it adds unrequested tests, documentation and small files at every effort level; at `xhigh` and `max` it can start its own review rounds, sometimes with subagents. Frequent harness text placed after tool results (a token countdown, or instructions or context added on every step) can be treated as a possible prompt injection and ignored; an occasional one-turn reminder is misread far less often. [S26, Verified]
- Haiku 5.5, page opened on completion: with a long coding-agent system prompt at `low` it stops early more often (moving to `medium` roughly halved early stopping and more than doubled output tokens), and reasoning-like text can appear in its replies at `low`. Its refusals are new for the Haiku tier and have no server-side fallback. [S27, S28, S6, Verified]

## Q2. OpenAI and Cursor guidance, and where vendors disagree

### OpenAI (Codex)
- Current family: GPT-6 Astra (`gpt-6-astra`), GPT-6.1 Sol (`gpt-6.1-sol`), GPT-6.1 Terra (`gpt-6.1-terra`), GPT-6 Luna (`gpt-6-luna`). [S16, Verified via summary]
- Astra asks more clarifying questions, is more sensitive to instructions in files and skills, delegates less than wanted, and may run broader tests than a small task needs. OpenAI recommends auditing AGENTS.md and skills for conflicting or silent guidance and stating that user instructions outrank skill text. [S16, Verified via summary]
- OpenAI supplies a persistence prompt (work until the goal is complete unless the action is destructive or irreversible) and autonomy prompts for when the model pauses too often. [S16, Verified via summary]
- Reasoning effort: `low`, `medium` (default on Sol and Terra), `high`, `xhigh`, `max`; `none` only on Terra and Luna. [S16, Verified via summary]
- AGENTS.md: global file in `~/.codex` (or `CODEX_HOME`), then one file per directory from the project root down to the working directory (`AGENTS.override.md` first); concatenated root-down, closer files win; combined cap `project_doc_max_bytes` = 32 KiB, after which later files are dropped; rebuilt at each run and session start. Behaviour after compaction is not documented on the page. [S17, Verified via summary]
- Codex prompt advice: name the behaviour, point to the code, keep constraints, say how to verify. [S20, Verified via summary]
- Codex subagents: TOML files in `.codex/agents/`; required `name`, `description`, `developer_instructions`; optional `model`, `model_reasoning_effort` (`low` to `max`, plus `ultra`). They spawn only on a direct request or when project or skill instructions ask for delegation. They inherit the parent's sandbox and approval settings, and an agent file cannot replace them. [S18, Verified via summary]
- Codex skills: `SKILL.md` with `name` and `description`; locations `.agents/skills` (repository), `~/.agents/skills` (user); list budget 2% of context or 8,000 characters; `agents/openai.yaml` with `policy.allow_implicit_invocation`. [S19, Verified via summary]

### Cursor
- Project rules live in `.cursor/rules/*.mdc` (plain `.md` there is ignored); frontmatter `description`, `globs`, `alwaysApply`; keep each rule under 500 lines; add a rule only after the agent repeats a mistake; point to files instead of copying them. [S21, S25, Verified via summary]
- AGENTS.md is supported at the root and in subdirectories. Precedence: Team, then Project, then User rules; earlier wins. [S21, Verified via summary]
- The Cursor CLI reads `.cursor/rules` and also root `AGENTS.md` and `CLAUDE.md`, applying both as rules. [S24, Verified via summary]
- Subagents: `.cursor/agents/*.md`, and for compatibility `.claude/agents/` and `.codex/agents/`; fields `name`, `description`, `model` (default `inherit`, or a model ID, with bracket options such as `effort=high`), `readonly`, `is_background`. `.cursor/` wins a name conflict. [S22, Verified via summary]
- Skills: `.agents/skills/`, `.cursor/skills/`, and for compatibility `.claude/skills/` and `.codex/skills/`; fields `name`, `description`, `paths`, `disable-model-invocation`. [S23, Verified via summary]

### Disagreements and what they mean for the kit

| Topic | Anthropic | OpenAI | Cursor | Consequence |
|---|---|---|---|---|
| Persistence text | Harmful in interactive use; add a block only for autonomous runs [S14, S2] | Supplies a persistence prompt [S16] | Stop-hook loop with an iteration cap [S25] | Keep persistence out of shared files; put it in each agent's loop-worker prompt. [Inferred] |
| Delegation | Model over-delegates when invited; say when not to [S2] | Model under-delegates; say when and how much [S16] | Delegates from the description [S22] | The same sentence has opposite effects. Delegation rules go in agent-specific files. [Inferred] |
| Verification | Fable verifies unprompted; reminders add cost [S12] | Astra over-tests; ask for proportionate tests [S16] | Tests as goals [S25] | Gates should name exact checks, not ask for "careful" checking. [Inferred] |
| Clarifying questions | Autonomy block reduces questions, at some risk on ambiguous tasks [S3] | Astra asks more; tell it to finish authorised work first [S16] | not addressed | Keep "one batched question"; add "state the assumption and continue" for reversible work. [Inferred] |
| Size limits | under 200 lines per CLAUDE.md [S11] | 32 KiB combined, silent drop [S17] | under 500 lines per rule [S21] | The always-loaded block stays far below all three. [Inferred] |
| Conflict order | arbitrary between files [S11] | closest directory wins [S17] | Team, Project, User [S21] | Never state one rule in two files. [Inferred] |
| Skill metadata | `when_to_use`, `model`, `effort`, `hooks`, `context` [S9] | `name`, `description` only documented [S19] | `name`, `description`, `paths`, `disable-model-invocation` [S23] | Put all trigger text in `description`; treat other fields as Claude-only. [Inferred] |
| Read-only subagent | `tools` list and frontmatter hooks [S10] | cannot be set per agent file [S18] | `readonly: true` [S22] | Three mechanisms; on Codex it is advice unless the review runs in its own read-only session. [Inferred] |
| Effort setting | frontmatter `effort`; default `medium` [S10, S12] | `model_reasoning_effort` in TOML [S18] | bracket option on `model` [S22] | Never write effort words into shared prose. [Inferred] |
| Emphasis and tags | no caps; XML tags useful [S1] | not addressed in the GPT-6 guide [S16] | not addressed [S21] | Plain wording everywhere; keeping tags in the kickoff is harmless. [Inferred] |

## Q3. Review of the kit's files, with concrete edits

General observations [K, Verified unless marked]:
- Shouted emphasis: one instance only ("ONE" in the `run-analyst` description).
- "never" appears 43 times on 39 lines in 12 files (recounted on completion; the first draft said 35). Most are sound; the problem is missing scope, reason and unattended branch, not tone.
- The ask-before list exists in three versions. The block omits stopping or restarting runs, evaluator changes and test-set evaluation; the skill says "test-set evaluation"; the kickoff says "the final test evaluation". The reviewer's description adds a fourth trigger ("before retaining a change that touches training or evaluation code") that no gate in the skill lists.
- No file asks the model to write out its reasoning, so none trips `reasoning_extraction` today. Keep it that way in new loop-worker output formats (no `reasoning` or `thinking` field). [S6, Inferred]

### `claude-md-block.md` (always loaded, survives compaction)
- B1. Line 7, live runs. Replace the absolute rule with a scoped one that carries its reason and exception: stop, restart, change or delete a running job, its snapshot, logs or checkpoints only after the user approves that action in chat, because another person or process may own it; when nobody can approve (unattended mode), skip the action, record it in the journal and continue with other work. Reason: Fable 5.2 applies "never" literally even after approval, and unattended mode has nobody to ask. [S2, Verified]
- B2. Lines 6 and 8, `python3 ...expctl.py`. `install.py` already takes `--python-cmd` (default `python` on native Windows), but `with_interpreter` rewrites only the hook commands and the status line in `settings.json`. The block, SKILL.md, the kickoff and both agent files are copied unchanged, and `nn_session_status.py` line 45 prints `Refresh with: python3 ...` into the context at every session start. Have the installer write the chosen interpreter into these texts too. Reason: on native Windows `python3` is a Store stub (docs/upgrade/PROMPT.md line 18), so the agent must guess; Anthropic says not to assume a tool is installed. [K, S8, Verified by reading the files; not run]
- B3. Line 8 and line 13, "Monitor tool", "`run-analyst` subagent". Make the block agent-neutral ("wait on `expctl watch` as a background command; the skill names the mechanism for your agent"). Reason: the Cursor CLI and Codex read this text and have no such tool. [S24, S17, Inferred]
- B4. Line 9, "with my approval". Say "with the user's approval". Reason: first-person voice is ambiguous in a file three products load as project rules. [Inferred]
- B5. Lines 10 and 11. Add the reason to "one controller" (two controllers on one study race and double-count budget) and to "never edit past entries" (the journal is the audit trail a reviewer checks). Reason: reasons improve generalisation; 74.0% of directives in public instruction files give none. [S1, P3, Verified]
- B6. Lines 12 and 13, standing delegation. Keep the reviewer gate, say when it is not needed (smoke runs, reverted changes) and that the verdict is recorded in the journal. Demote the analyst line to a size rule ("when the answer needs more raw log than about 200 lines"). Reason: standing delegation lines raise cost on Fable 5.2 and the context-protection argument is old advice. [S2, S14, Verified]
- B7. Line 14. Make this list the single ask-before list, complete, with exact actions; delete the copies in the skill and kickoff. [S2, S11, Verified]
- B8. Add one agent-neutral line: after any context summary, re-run `expctl status --brief` and re-open the skill before acting. Reason: Codex and Cursor document no re-injection of skill bodies. [S17, S24, Inferred]

### `KICKOFF_PROMPT.md`
- K1. Line 1, `ultrathink.` Delete. It raises only the first turn (to `xhigh` in the interactive terminal since v2.1.311), which is the read-only reconnaissance turn; it is a stray word for Codex and Cursor; it can be disabled by an environment variable. Tell the user to set session effort instead. [S12, S14, S15, Verified]
- K2. Line 39, "Run independent reads and checks in parallel." Delete; parallel tool calls are the default. [S1, Verified]
- K3. Lines 28 to 31, 41 to 46, 49, 50 and the `<autonomy>` block repeat the skill and the block. Reduce the kickoff to: role sentence, project card, priorities pointer, "open the nn-training skill and follow its phases", report cadence. Reason: duplicated rules drift and already differ. [K, S11, S16, Verified]
- K4. Line 63, "Report at the end of Phase 2 ... then continue". Ambiguous: a report as the final message ends the turn. Rewrite: write the Phase 2 and Phase 3 reports into the journal, summarise each in a short message, and keep working in the same turn; end the turn only when the campaign is complete, the budget is used, or a listed decision is needed. [S4, S3, Verified for the behaviour; edit is Inferred]
- K5. Add the ordinary-obstacle rule in two sentences: a guard denial or an item on the ask-before list is a deliberate block, so stop and explain; a missing package, wrong path or failing test is an ordinary obstacle, so solve it. [S2, Verified]
- K6. Add one ownership sentence: the repository belongs to the user; keep changes to what the experiments need and list other findings as follow-ups. [S2, S3, Verified]
- K7. Line 47, "Context7". Name it as optional ("a documentation server, if you enabled one"); it needs network and is off by default under the adoption rule. [Inferred]
- K8. "Load the skill now" needs an agent-specific form (Codex `$nn-training`, Cursor `/nn-training`), or neutral wording ("open the nn-training skill"). [S19, S23, Inferred]
- K9. Do not reuse this prompt for the unattended loop. The loop worker needs its own first-message prompt with the autonomy block from the first request. [S2, S3, S4, Verified]

### `.claude/skills/nn-training/SKILL.md`
- S1. Frontmatter. Merge `when_to_use` into `description` and write it in the third person ("Use when launching, watching ..."). Codex and Cursor document only `name` and `description`. [S8, S19, S23, Verified]
- S2. Lines 11 and 12, the claim that a strong model with a shell beats elaborate frameworks. Undated and uncited, and not an instruction. Move it to the README with its source and date; keep "spend effort on evaluation hygiene, measurement and plumbing". [S8, Inferred]
- S3. Line 14, fixed `python3`. Same as B2. [K, S8, Verified by reading the file; not run]
- S4. Table row "Wait for runs" and the "Waiting" bullet (lines 23, 42 to 47): Monitor tool, `timeout_ms`, `run_in_background`, `/loop`, "scheduled wake-up". Keep one agent-neutral rule with its reason in SKILL.md and move the mechanics to one reference per agent. The Claude Code details also need a version and date: self-paced `/loop` changed in v2.1.319, and a v2.1.321 fix note says background commands in `claude -p` are stopped after 10 minutes. [S15, Verified for the changelog lines; the 10-minute limit is Inferred from one line]
- S5. Lines 25, 53 to 59: SIGTERM, SIGKILL, process group, `exec`, `--via tmux`. Describe behaviour neutrally ("asks the run to checkpoint and exit, then force-stops it after `kill_after_s`") and move per-platform detail to a platform reference. Native Windows has none of these. [K, Inferred]
- S6. Table rows for the two subagents and the gates at lines 89, 102 and 107. State cost first and when not to delegate; say how to brief the reviewer (run ids, base and head commit, claim text, protocol version); say that the verdict is about the evidence and adds no rules beyond this skill. In unattended mode keep or revert is decided by harness code and the frozen evaluator; reserve the reviewer for promotion and final claims. [S2, S14, Verified; the loop rule follows the brief]
- S7. Section 4, lines 125 to 128: Muon, Schedule-Free AdamW, SOAP/Shampoo, WSD, CompleteP, "1.1 to 1.4x". Undated technique advice in the always-read body. Move to a dated reference with source and PyTorch version; keep only the rule to test alternatives as controlled experiments against a tuned AdamW baseline. [S8, brief hard constraint, Verified]
- S8. Line 129, "autoresearch-style keep/revert loops". Jargon the agent must guess, and it will conflict with the new loop module. Replace with a pointer to the loop reference. [Inferred]
- S9. Section 6. Rewrite the dot-separated paragraph as the numbered list now in the kickoff, keep only this copy, and add one line that the reader has little context, so results come first. [S2, Verified]
- S10. Section 7. Replace with a pointer to the single ask-before list (B7) plus two additions: actions that need no approval, named exactly; and the unattended branch. A broad approval rule holds back routine work. One case to settle with the guard owner: Gate 1 requires stopping the agent's own smoke run, while the tool table says stop "only with the user's OK". [S2, K, Verified]
- S11. Lines 40 and 41. Keep, and add the ordinary-obstacle distinction (K5). [S2, Verified for the guidance; the edit is Inferred]
- S12. Order and size. About 172 lines of about 105 characters is roughly 4,500 to 5,000 tokens (estimate, not measured). After compaction only the first 5,000 tokens come back and the start of the file is kept. Move the proceed/ask/stop rules and the references index to the top; move section 8 (config keys) and the run-contract detail to references; aim for about 3,500 tokens. [S13, Verified for the limit; size is Inferred]
- S13. Phase 0: "Read CLAUDE.md" becomes "read the project's agent instruction file"; `ps`, `tmux ls`, `squeue` need a Windows alternative or an `expctl` subcommand. Line 58 "Claude Code session" becomes "agent session". [Inferred]
- S14. "never hand-pick trial values" (line 100): add the reason (an untracked search that the budget and winner's-curse accounting cannot see). [S1, Verified for the guidance; the reason text is Inferred]

### `.claude/agents/experiment-reviewer.md`
- R1. Add `effort: high`. `model: opus` resolves to Opus 5.5 on the Anthropic API, Bedrock and Google Cloud and to Opus 4.6 on Foundry. Without `effort`, the reviewer runs at the session's effort only when the main model is the same; on a different main model it runs at Opus 5.5's saved or default level (`medium`) since v2.1.317. [S10, S12, S15, Verified]
- R2. Line 17, "your job is to find what is wrong". Rewrite: decide whether the evidence supports the claim; report only issues that would change the verdict or a reported number; say so when there are none; state findings as facts about the evidence, not as rules for the author. Reason: a reviewer told to find problems always finds some, and reviewer conditions can stop the main agent. [S14, S2, Verified]
- R3. Line 25, "Keep output under 400 words". Replace the cap with a content rule (verdict first, one line per issue with its evidence pointer, no restating of the checklist). Fable 5.2 follows hard style limits closely. [S2, Verified]
- R4. Define what each verdict permits (for example, APPROVE WITH CAVEATS means the claim may be recorded with the caveat text). The agent must currently guess. [Inferred]
- R5. Description. Keep it short and move the trigger list to the skill so there is one list. [S10, K, Verified for the guidance; the move is Inferred]
- R6. Lines 20 to 22: `sha256sum`, `tail -n`, `head -n`, `grep` are POSIX tools. Tell the reviewer to use its file-read and search tools with explicit limits, and the shell only for `expctl` and read-only `git`. [K, Inferred]
- R7. Frontmatter hook (lines 7 to 13, same in `run-analyst.md`): the command uses `python3` and POSIX `${VAR:-.}` syntax and has no `onFailure: block`, while the main guard in `settings.fragment.json` (line 62) has it. The installer copies agent files unchanged, so `--python-cmd` does not reach this command. The kit's own note (docs/research-notes/claude_code_features.md line 37) records that a hook ending with any code other than 2 is a non-blocking error unless `onFailure` is `block`. On native Windows the read-only layer of both subagents is therefore probably off, while the main guard still applies. Fix: write the chosen interpreter into this command at install time and add `onFailure: block`. This was not run, so it is Inferred. Cursor loads this file from `.claude/agents/` but documents no `hooks` or `tools` field, so there the reviewer would have a shell without the guard; ship `.cursor/agents/` versions with `readonly: true`. On Codex, read-only is advice unless the review runs in its own read-only session. [S22, S18, Verified for the documented fields; the Cursor behaviour for undocumented fields is Inferred]
- R7a (added on completion). The hooks and subagents pages change R7 in four ways. (1) `onFailure` (`continue` or `block`) is documented for command hooks from v2.1.295: a hook that cannot start, times out or ends with a code other than 0 or 2 does not block unless the value is `block`. Frontmatter hooks are described as using the same format as settings hooks; support for this one field in agent frontmatter is not stated, so it stays Unverified. (2) The direction of the failure depends on the shell. With Git Bash the failed hook lets the call through. On Windows without Git Bash a failing shell-form PreToolUse hook with `onFailure` unset "can instead block the tool call", and `${VAR:-.}` is not valid PowerShell, so there the subagent would lose its shell and with it `expctl` and `git`. (3) A project subagent's frontmatter hooks run only after the folder's trust dialog was accepted, and a `-p` session does not count as trusted; until then the subagent runs and the hook is skipped with only a debug-log entry. An unattended run in a fresh clone therefore has no read-only layer in either subagent. (4) Hooks from settings files also run inside subagents and receive `agent_id` and `agent_type`; `nn_guard.py` already records `agent_type` (line 425). Preferred fix, in place of the one in R7: deny write-type calls in the settings-level guard when `agent_type` is one of the kit's two read-only agents. That hook already runs with the installed interpreter and `onFailure: block`, and `platform-claude-code.md` in this folder records, from the hooks and headless pages, that settings hooks do run in an untrusted `-p` session; it proposes the same mechanism. Keep the frontmatter hook at most as a second layer. [S29, S10, K, Verified for the documented behaviour (the hooks page through a summary, cross-checked with that note's quotes); the effects on this kit are Inferred and were not run]

### `.claude/agents/run-analyst.md`
- A1. Description: "ONE" becomes "one". [S1, S14, Verified]
- A2. Add `effort: medium` (corrected on completion; the first draft said `low`). `model: sonnet` is Sonnet 5.5 on the Anthropic API but Sonnet 4.6 on Claude Platform on AWS and Sonnet 4.5 on Bedrock, Google Cloud and Foundry. The `low` advice for well-specified, high-volume subagent work comes from the Fable 5.2 page and the generic effort table; the per-model advice overrides it, and for Sonnet 5.5 it is `medium` for well-specified multistep tool use, with a warning that at `low` the model can skip a check. The main agent trusts the analyst's diagnosis, so start at `medium` and try `low` only against scored answers. Trial `haiku` on saved logs at `medium` with `omitClaudeMd` (20 times cheaper per token than Sonnet 5.5 for prompts up to 100,000 tokens; Haiku 5.5 stops early more often at `low` under a long agent prompt, and its refusals have no server-side fallback). [S26, S27, S28, S6, S7, S12, Verified; the choice is Inferred]
- A3. Line 23: `tail -n 200`, `grep -n -m 50`, `sed -n` are POSIX-only. Smallest fix: tell the analyst to use its file-read tool with a line range and its search tool with a result limit, which work on every platform. `expctl` has no log-reading subcommand today (`status`, `launch`, `stop`, `watch`, `curve`, `hash`, `selftest`, `env`); add one only if the bound must be enforced by code. [K, Inferred]
- A4. "at most 300 words": replace with the four-part content rule already present. [S2, Verified]
- A5. Add: answer the question asked; mention other anomalies in one closing line and do not investigate them. Sonnet 5.5 over-applies initiative and scope. [S1, S26, Verified]

### References and template
- F1. `validity.md`, `uncertainty.md`, `resume.md`, `performance.md` carry no verification date; `performance.md` names "PyTorch 2.13+" and FP8 formats without one. Add a "verified on, against versions" line to each. [K, S8, Verified]
- F2. `stack.md` contains Claude-Code-only commands (`claude mcp add`, `/plugin`); move them to the Claude Code agent reference. [K, Verified by reading the file]
- F3. Add a table of contents to every reference over 100 lines. [S8, Verified]
- F4. `templates/JOURNAL.md`: "maintained by Claude Code" becomes "maintained by the coding agent". [K, Verified by reading the file]

## Q4. Model and effort for each role

Valid values in Claude Code today:
- Subagent `model`: `sonnet`, `opus`, `haiku`, `fable`, a full model ID, or `inherit`. A per-call model parameter accepts only the four aliases. Resolution order: per-call value, frontmatter, `CLAUDE_CODE_SUBAGENT_MODEL`, main model. [S10, Verified]
- Subagent and skill `effort`: `low`, `medium`, `high`, `xhigh`, `max`; an unsupported level falls back to the highest supported one at or below it. `CLAUDE_CODE_EFFORT_LEVEL` overrides frontmatter. `CLAUDE_CODE_SUBAGENT_EFFORT` (v2.1.316) sets the level when nothing else names one. Skill `model` and `effort` apply to the current turn only. Settings key `effortLevel` does not accept `max`. [S9, S10, S12, S15, Verified]
- `fable` resolves to Fable 5.2 (needs v2.1.321); `opus` to Opus 5.5 (needs v2.1.280); `sonnet` to Sonnet 5.5 (v2.1.284) and `haiku` to Haiku 5.5 (v2.1.293) on the Anthropic API, and to older models on other providers. [S12, Verified]
- Added on completion: a user-level `effortLevel` is the older form and is ignored by Opus 5.5 and newer models, which keep a per-model level under `modelSettings`; in project, local and managed settings and with `--settings` the key applies to every model. In a `-p` run `/effort` applies to that session only, so an unattended launcher should pass `--effort` or set `CLAUDE_CODE_EFFORT_LEVEL`, which outranks every other source. [S30 through a summary with quoted text, S12, Verified]

Prices, USD per million tokens, input / output [S7, Verified]: Fable 5.2 8 / 40; Fable 5.1 10 / 50; Opus 5.5 4 / 20; Opus 5 5 / 25; Sonnet 5.5 2 / 10; Haiku 5.5 0.10 / 0.50 (prompts up to 100,000 tokens). Per token, Fable 5.2 costs 2 times Opus 5.5, 4 times Sonnet 5.5 and 80 times Haiku 5.5. Higher effort adds output tokens; the size of that increase for the kit's roles is not measured. [Inferred]

| Role | Recommendation | Where set | Why | Status |
|---|---|---|---|---|
| Main training agent (interactive) | Opus 5.5 (the default) at `high`. Fable 5.2 is the user's opt-in for long, ambiguous campaigns. | README advice; not in kit files | Anthropic says start with Opus; `high` when overlooked cases matter; Fable costs twice as much and can refuse ML work (`frontier_llm`, billed). | S5, S14, S6 Verified; choice Inferred |
| Sceptical reviewer | `model: opus`, `effort: high`, fresh context, read-only | agent frontmatter | Fresh context is what helps; Opus 5.5 finds more bugs with fewer false alarms than Opus 5 (early-tester report). Low volume, high stakes. | S14, S4 Verified; choice Inferred |
| Log analyst | `model: sonnet`, `effort: medium`; trial `haiku` at `medium`; `low` on either model only against scored answers (corrected on completion) | agent frontmatter | Well-specified, bounded reads; the per-model advice for Sonnet 5.5 and Haiku 5.5 is `medium` for multistep tool use, and at `low` both can skip a check or stop early. | S26, S27, S28 Verified; choice Inferred |
| Unattended loop worker | Opus 5.5 at `high` by default, user-configurable; a fresh session per iteration with state in files; harness decides completion; at most two or three automatic continuations | loop module config | Vendor advice for unattended runs; Fable guidance also names `high`; a flagged request in non-interactive mode ends the turn with a refusal. | S2, S4, S12 Verified; choice Inferred |
| Research scout (optional, needs network) | Opus 5.5 or Fable 5.2 at `high`; never `low` | optional module config | `high` is the research setting; at `low` Fable 5.1 searches less and answers from memory. | S2, S3 Verified; choice Inferred |

Notes added on completion:
- The `high` level for the Opus 5.5 roles is this note's choice. Opus 5.5 defaults to `medium`, and the effort page asks for a comparison of levels on your own tasks instead of carried-over settings; the Claude Code best-practices page supports `high` where overlooked cases matter. Keep `high` for the reviewer and the loop worker only if the planted-flaw comparison (candidate rows 5 and 11) shows a gain over `medium`. [S28, S4, S14, Verified; the choice is Inferred]
- Refusal exposure is not limited to Fable. `frontier_llm` is named on the Sonnet 5.5 and Haiku 5.5 pages; the Opus 5.5 page names biology, cybersecurity and reasoning extraction only. Haiku 5.5 has no server-side fallback. In Claude Code a flagged subagent request fails with `Agent terminated early due to an API error` under the ask-each-time setting, which the main agent can mistake for an ordinary failure and retry. [S26, S27, S6, S4, S12, Verified]

Codex and Cursor equivalents: Codex suggests Sol at medium for complex technical work and Astra for broad or demanding work [S20, Verified via summary]; set `model` and `model_reasoning_effort` in each `.codex/agents/*.toml` [S18]. Cursor: `model: inherit` plus `readonly: true` [S22].

Evidence on reviewer or judge model choice:
- Anthropic's documentation credits the fresh context, not a different model. [S14, Verified]
- One 2026 study with four model families found no detectable self-preference on verifiable revision tasks (gap -5.1 points, 95% interval -12.9 to +2.7), and cannot rule out effects under about 13 points. [P9, Verified from abstract]
- Other judge studies report self-preference (corrected on completion; the first draft had this as Unverified). An early study found that models score their own outputs higher and that the effect grows with their ability to recognise their own text. [P14, Verified from abstract] A 2026 study of rubric-based judging found bias towards a judge's own and own-family outputs even on objective criteria: judges were more than 50% more likely to mark a failed rubric item as satisfied, scores shifted by up to 10 points on one benchmark, and ensembles of judges reduced the effect without removing it. [P15, Verified from abstract]
- A cross-vendor builder and reviewer workflow reports that independent review caught unsupported builder claims; the authors call the evidence observational, and stopping was its weak point. [P10, Verified from abstract]
- Conclusion: same-model review in a fresh context is acceptable as a default; a different-family reviewer is an optional extra worth assessing; neither should decide what an unattended loop keeps. The reviewer's checklist is rubric judging of a same-family author, the setting in which P15 found the bias, so every checklist item that code can check (hashes, seed counts, evaluator version) should be checked by code and handed to the reviewer as a fact. [Inferred; second sentence added on completion]

## Q5. Context management for long training sessions

Claude Code facts:
- Always loaded: project-root CLAUDE.md (or AGENTS.md when no CLAUDE.md exists), unscoped `.claude/rules/`, auto memory (first 200 lines or 25 KB), skill descriptions (description plus `when_to_use` cut at 1,536 characters), subagent descriptions. [S11, S9, S10, Verified]
- On demand: skill body when invoked (stays in the conversation, not re-read), reference files when read, nested CLAUDE.md and path-scoped rules. [S9, S11, Verified]
- After compaction: project-root CLAUDE.md, unscoped rules and auto memory are re-injected from disk; skill descriptions are rebuilt (v2.1.304+); invoked skill bodies return capped at 5,000 tokens each and 25,000 in total, oldest dropped first, start of file kept; up to five recently modified files are re-read (a file over 5,000 tokens returns as a path only); context added earlier by hooks is summarised away; SessionStart hooks that match the `compact` source run again; background commands and subagents keep running; path-scoped rules and nested CLAUDE.md return only on demand. [S13, Verified]
- Limits: models with a native 1M window compact at about 967K tokens by default; `/autocompact`, `autoCompactWindow` and `CLAUDE_CODE_AUTO_COMPACT_WINDOW` accept 100,000 to 1,000,000; PreCompact hook output is cut at 10,000 characters (v2.1.314). [S12, S15, Verified]
- Guidance: aggressive context management is old advice; `/clear` between unrelated tasks is still worth doing; compacting early to save cost can cost intelligence. [S14, S3, Verified]
- Multi-window work: keep state in files (tests, progress notes, git) and let a fresh window read them. [S1, Verified]

Codex and Cursor facts: Codex rebuilds the AGENTS.md chain at each run or session start, capped at 32 KiB [S17]; Cursor always loads `alwaysApply` rules and AGENTS.md, and the CLI has `/summarize` [S21, S24]. Neither page says what happens to skill text after a summary. [Unverified]

Recommended split for the kit [Inferred from the facts above]:
- Always loaded, all agents: the rules block only, about 15 to 25 lines, one canonical text. Put it in `AGENTS.md` and give Claude Code a `CLAUDE.md` whose kit section is the line `@AGENTS.md` (an import, which works on Windows; a symlink does not). This avoids a second copy for the Cursor CLI, which reads both files.
- On demand: SKILL.md (procedure) and references, with the agent-specific and platform-specific mechanics in their own reference files.
- Re-injected: the block (automatic in Claude Code; start-of-session in Codex and Cursor); run state through the existing `nn_session_status.py` hook, which already handles the `compact` source and adds a reminder to re-read the latest journal entry (Claude Code only), and through rule B8 elsewhere; the first 5,000 tokens of SKILL.md in Claude Code, which is why its order matters (S12 above).
- The journal and `expctl` stay the memory across windows; auto memory is not a substitute because subagents do not receive it and it is per machine. [S11, Verified]

Evidence that argues for keeping all of this short:
- Repository context files did not generally improve task success and raised inference cost by over 20% on average. [P1, Verified from abstract]
- A two-agent ablation (Claude Code and Codex, 288 runs) found no measurable correctness change from context strategy, with the effect bounded to about 10 to 15 points. [P2, Verified from abstract]
- Curated skills raised average pass rate from 33.9% to 50.5% across 87 tasks; focused skills with at most three modules beat exhaustive bundles. [P6, Verified from abstract]
- 307 skill-induced failures were catalogued, including 67 cases of excessive verification. [P7, Verified from abstract]
- Long persona-style system prompts gave no accuracy gain, 2.2 to 4.5 times the cost per successful call, and a 10-point lower solve rate on tool-using tasks. [P8, Verified from abstract]
- In a six-week case study, stale documentation was the largest class of agent failure (48 of 118), and a written rule did not change one model's behaviour where a mechanical check did. [P4, Verified from abstract]
- A similar co-installed skill takes one in five runs from the intended skill, and the final reply names the substitution in 0.9% of those runs. [P5, Verified from abstract]

## Changed since 23 October or wrong in the earlier notes

1. Claude Fable 5.2 exists (Claude Code v2.1.321, 9 Nov 2026). The `fable` alias now resolves to it. It costs less than Fable 5.1 (8 / 40 against 10 / 50) and has its own prompting page. [S5, S7, S12, S15, Verified]
2. Claude Code is at v2.1.322 (10 Nov 2026); the notes describe v2.1.308. The upgrade prompt records Claude Code 2.1.303 on Windows, which is older than the documented minimum for Fable 5.2 (v2.1.321). This scout session nevertheless reports running on `claude-fable-5-2`, so re-check the installed version before relying on either number. [S15, S12, K, Verified for the documented versions; the mismatch is unexplained]
3. `ultrathink` now runs its turn at `xhigh` in the interactive terminal (v2.1.311) and can be turned off with `CLAUDE_CODE_DISABLE_ULTRATHINK` (v2.1.316). The note's one-turn description is still right; the kit's use of it as the kickoff's first word is not useful. [S12, S15, Verified]
4. Subagent effort changed: `CLAUDE_CODE_SUBAGENT_EFFORT` (v2.1.316); subagents on a different model use that model's saved or default effort instead of the session's (v2.1.317). The README's "/effort high" therefore no longer reaches the `sonnet` analyst, nor the `opus` reviewer when the main model is not Opus. [S15, S10, Verified]
5. Subagents now stop instead of switching models when the flagged-message setting is "Ask each time" (v2.1.318). [S15, Verified]
6. AGENTS.md support, which the notes took from forum posts, is now documented: direct reading needs v2.1.277 or later (v2.1.281 for sessions on Bedrock or with telemetry off) and happens only when no CLAUDE.md or CLAUDE.local.md exists in the working directory or above; a "Project instructions" setting changes this. [S11, Verified]
7. Skill descriptions are re-injected after compaction (v2.1.304+); on-demand instruction files over a size limit are truncated with a pointer (v2.1.309); PreCompact hook output is cut at 10,000 characters (v2.1.314). [S13, S11, S15, Verified]
8. Hooks that match Bash now also run on shell commands started by the Monitor tool (fix in v2.1.314). [S15, Verified]
9. Self-paced `/loop` now ends when a turn finishes without rescheduling (v2.1.319). The skill's advice to use `/loop` for long waits needs a re-test. [S15, Verified] Read on completion: a self-paced loop picks a delay between one minute and one hour; an iteration that neither reschedules nor stops gets one fallback wake-up about 20 minutes later, and the loop ends if that one does not reschedule either; tasks fire only while Claude Code is running and idle; a self-paced loop is not restored by `--resume`, background commands are not restarted on resume, and recurring tasks expire after 7 days. [S31, Verified]
10. New settings useful for unattended work: `permissions.denyInsteadOfPrompting` (v2.1.319) and `permissions.blockWritesOutsideWorkingDirectories` (v2.1.314). [S15, Verified] Read on completion: `denyInsteadOfPrompting` works only in user or managed settings or in a file passed with `--settings` ("A repository can't set it for you"), so the kit cannot ship it in project settings; the per-run form is `--permission-prompts none` with `-p`. With it Claude Code also leaves out `AskUserQuestion` and the plan-mode tools; in auto mode a turn ends after 20 refused calls in a row, which a `-p` run reports as `error_during_execution`. `blockWritesOutsideWorkingDirectories` can be set in any settings file, covers only the Write, Edit and NotebookEdit tools (not shell commands, MCP tools or programs run by hooks) and removes the worktree tools. [S30, Verified through a summary with quoted entries]
11. Missed by the earlier notes: the `frontier_llm` and `reasoning_extraction` refusal categories, both billed when the refusal comes before any output. The billing rule is dated September 2026, so it predates the kit. [S6, Verified]
12. The README labels the agents "Opus" and "Sonnet"; the aliases resolve to older models on Bedrock, Google Cloud, Claude Platform on AWS and Foundry. [S12, Verified]
13. Claude Code now ships `/doctor prompt-audit`, which checks instruction files, skills and subagents for wording written for older models, dead file references and contradictions. [S11, S14, Verified]
14. OpenAI's Codex documentation moved to learn.chatgpt.com, and the current family is GPT-6. [S16, S17, Verified]

## Concerns any design must handle

- SAFEGUARD-REFUSAL-ON-ML-WORK: a classifier refusal can end a turn on benign training work, is billed, and has no documented automatic switch in the agent for that category; it is documented for the subagents' cheaper models too, where it can surface as a generic agent error.
- PROMPT-REASONING-EXTRACTION-DECLINE: any prompt, skill or output schema that asks for written reasoning can be declined.
- RULE-ABSOLUTE-NEVER-BLOCKS-APPROVED-ACTION: "never" wording suppresses actions the user approved.
- APPROVAL-RULE-NO-UNATTENDED-BRANCH: ask-before rules do not say what to do when nobody can answer.
- APPROVAL-RULE-SCOPE-TOO-BROAD: category-level approval rules hold back routine work.
- RULE-DUPLICATION-DRIFT: the same rule in several files diverges and is resolved arbitrarily.
- RULE-WITHOUT-REASON: rules without reasons generalise badly and cannot be pruned safely.
- ADVICE-UNDATED: technique advice without date, source and version in always-read text.
- PROMPT-AGENT-SPECIFIC-VOCABULARY: tool names of one agent in files another agent reads.
- PROMPT-PLATFORM-SPECIFIC-COMMANDS: POSIX-only commands and signals in instructions used on Windows.
- INTERPRETER-NAME-GUESS: a fixed interpreter name in prompts and hook commands.
- REVIEWER-READONLY-NOT-PORTABLE: read-only enforcement of subagents differs per agent and is absent on one.
- READONLY-HOOK-FAIL-OPEN-WHEN-INTERPRETER-MISSING: a subagent guard hook that cannot start does not block the call.
- REVIEWER-CONDITIONS-LEAK-INTO-WORKER: reviewer wording becomes new restrictions for the main agent.
- REVIEWER-ALWAYS-FINDS-SOMETHING: a find-faults brief produces findings regardless of merit.
- JUDGE-SAME-MODEL-BIAS: evidence on same-model judging is mixed; a model verdict must not decide kept results.
- DELEGATION-OVERUSE-COST: standing delegation lines multiply token cost.
- DELEGATION-RULE-OPPOSITE-EFFECT-ACROSS-AGENTS: one delegation sentence over-triggers one model and under-triggers another.
- EARLY-STOP-UNATTENDED: a turn can end with a plan or a question while work remains.
- COMPLETION-CLAIM-NOT-PROOF: a final message is a report, not evidence that the work is done.
- EFFORT-NOT-INHERITED-BY-SUBAGENT: session effort no longer reaches subagents on another model.
- EFFORT-SETTING-NOT-PORTABLE: effort names and defaults differ per model and vendor.
- MODEL-ALIAS-RESOLVES-DIFFERENTLY: the same alias names different models per provider.
- CONTEXT-COMPACTION-SKILL-TAIL-LOSS: only the start of a skill returns after compaction.
- CONTEXT-COMPACTION-RULE-LOSS-OTHER-AGENTS: no documented re-injection of skill text outside one agent.
- INSTRUCTION-FILE-DOUBLE-LOAD: one agent loads two instruction files that another treats as alternatives.
- INSTRUCTION-FILE-SIZE-CAP-SILENT-DROP: a byte cap drops later instruction files without notice.
- SKILL-NAME-COLLISION: a similar co-installed skill silently replaces the intended one.
- SEC-INSTRUCTION-FILE-POISONING: instruction, rule and skill files are an injection path, including hidden characters.
- SEC-PROMPT-INJECTION: fetched content and logs can carry instructions to the scout, analyst or reviewer.
- PROMPT-STALE-FOR-NEW-MODEL: prompts tuned for one model generation misfire on the next; needs a repeatable audit.
- SKILL-VALUE-UNMEASURED: no evaluation shows that the kit's text improves outcomes over no kit.
- SUBAGENT-HOOK-TRUST-GAP: a project subagent's own guard hook is skipped without notice in a folder nobody trusted, which is the normal state of an unattended non-interactive run.
- HOOK-FAILURE-MODE-DEPENDS-ON-SHELL: the same failing hook command lets the call through under one shell setup and blocks the tool under another.
- HARNESS-TEXT-MISREAD-AS-INJECTION: text a harness adds after tool results on every step can be treated by the model as an injection attempt and ignored.
- NO-PROMPT-SETTING-IGNORED-IN-PROJECT-SETTINGS: the setting that turns permission prompts into denials cannot be shipped in a repository's settings; the launcher must pass it.
- WAIT-MECHANISM-NOT-DURABLE: a scheduled wake-up loop ends after one missed reschedule and is not restored when a session is resumed.

## Open questions

1. Does `frontier_llm` fire on Opus 5.5? Partly answered on completion: the Sonnet 5.5 and Haiku 5.5 pages name the category; for Sonnet 5.5 the API's server-side fallback (beta) retries it on Sonnet 5, and Haiku 5.5 has no server-side fallback. The Opus 5.5 prompting page names only biology, cybersecurity and reasoning extraction, and Claude Code's own switch list names only biology and cybersecurity, so what Claude Code does with a `frontier_llm` refusal on any model is still Unverified. [S26, S27, S6, S12]
2. How often does real kit use (fine-tuning scripts, optimiser changes) trip that classifier on Fable 5.2? Needs a measured trial.
3. Exact token count of SKILL.md under the current tokenizer, against the 5,000-token re-attach cap.
4. How does Cursor treat undocumented fields (`tools`, `hooks`, `model: opus`) in a `.claude/agents/` file?
5. What do Codex and Cursor keep of a loaded skill after their own summarisation?
6. Is the 10-minute stop for background commands in `claude -p` (from one changelog line) the general rule?
7. Does `/doctor prompt-audit` exist in the Claude Code version on the test machine, and from which version?
8. Token cost per wake-up when a session waits 25 minutes between events (prompt-cache lifetime against context size).
9. Whether AGENTS.md read in place of CLAUDE.md is re-injected after compaction exactly as CLAUDE.md is (the table names CLAUDE.md only).
10. OpenAI's guidance on capital-letter emphasis and on XML tags for the GPT-6 family (not on the page read).
11. Does the subagents' read-only hook start on native Windows after a default install, and is `onFailure: block` honoured in subagent frontmatter hooks? Partly answered on completion (R7a): `onFailure` is documented for command hooks and frontmatter hooks use the same format, but neither point was run; the question loses weight if read-only is enforced in the settings-level guard.
12. Which effort level do the reviewer and the analyst need? The per-model starting levels (Opus 5.5 `medium` by default, Sonnet 5.5 `medium` for multistep tool use) differ from the first draft of this note; only the planted-flaw and scored-answer comparisons can settle it. (Added on completion.)
13. Do the kit's own hook messages reach a `sonnet` subagent as trusted text? The Sonnet 5.5 page reports that frequent harness text after tool results can be read as an injection attempt, so a design that adds a budget or status line after every tool call needs a test. (Added on completion.)

## Redirect attempts

No third-party content tried to redirect the research. Three machine-directed instructions were seen in tool
output and not acted on:
- Claude Code documentation pages begin with a line telling the reader to fetch the documentation index file first. Treated as page boilerplate; not followed.
- The Exa search service returned a rate-limit error telling the client to create an account and an API key. Not acted on; remaining searches used the built-in search and fetch tools.
- The built-in search tool appends a reminder to list sources. Sources are listed in this note.
Sample prompt texts inside vendor documentation were read as documentation, not as instructions.

Completion pass, 11 November: the same two machine-directed instructions were seen again and not acted on (the
documentation-index line at the top of Claude Code documentation pages; the Exa rate-limit message telling the client
to create an account and an API key). The fetch tool's note that a long page can be read on from a character offset is
tool output, not page content; it was used once, for the settings reference. This note and the candidates file carry
suggested commands (cheap local trials); none was run. No fetched page, abstract or file tried to redirect the work.

## Not done

- The Opus 5 and Opus 4.8 prompting pages and the Fable 5 page were not opened. (The Sonnet 5.5 and Haiku 5.5 pages were opened on completion.)
- No kit file was edited and no proposed wording was tested against a model.
- Third-party tools in the candidates file (SkillOpt, linters, sync generators) were seen in search results only; their repositories, licences and release dates were not checked.
- Other scouts' draft notes in this folder were not read in full. On completion they were searched only for hooks, trust, refusals, concern IDs and the candidates named in the completion pass; other overlaps and contradictions are not reconciled.

## Completion pass (11 November 2026)

A second agent checked this note and the candidates file against the brief and filled gaps only. No local command was
run; the candidates file was checked line by line with a strict pattern match, not with a JSON parser.

Corrected:
- Analyst effort: `low` became `medium` (A2, role table, summary line 10, candidate rows 5 and 15). The `low` advice came from the Fable 5.2 page; the per-model advice for Sonnet 5.5 and Haiku 5.5 says `medium`. [S26, S27, S28]
- Scope of `frontier_llm`: named for Sonnet 5.5 and Haiku 5.5 too (summary line 4, open question 1, the concern line, candidate rows 9 and 10). [S26, S27, S6]
- Judge evidence: two self-preference papers were read at abstract level (Q4, candidate rows 11 and 14). [P14, P15]
- Count of "never": 43 occurrences on 39 lines in 12 files, not 35 (summary line 3, Q3, candidate row 3).

Added:
- R7a: documented hook failure behaviour, the trust condition for subagent hooks and the settings-level alternative (summary line 8, open question 11, candidate rows 21 and 48). [S29, S10]
- Findings from the Sonnet 5.5 and Haiku 5.5 pages in Q1, and the per-model starting levels for effort. [S26, S27, S28]
- The documented scope of the two permission keys, the limits of self-paced `/loop` and the scope of `effortLevel` (Changed items 9 and 10, Q4, candidate rows 38, 49 and 51). [S30, S31]
- A primary report on hidden characters in rule files (candidate row 26, now Trial). [W2]
- Status labels on edit lines S3, S11, S14, R5, A1, A4, F2 and F4.
- Five concern IDs: SUBAGENT-HOOK-TRUST-GAP, HOOK-FAILURE-MODE-DEPENDS-ON-SHELL, HARNESS-TEXT-MISREAD-AS-INJECTION, NO-PROMPT-SETTING-IGNORED-IN-PROJECT-SETTINGS, WAIT-MECHANISM-NOT-DURABLE.
- Candidate rows 48 to 55, for items this note discussed without a row.

Limits of this pass:
- Long Claude Code documentation pages (hooks, subagents, model configuration, settings reference) were read through summaries of 100,000-character slices, with quotes requested; the API documentation pages were read as raw text.
- Nothing was run, so every statement about how the kit behaves on Windows or in a `-p` session is Inferred.
- Concern IDs here appear to overlap, judged by their names only, with IDs in other draft notes, and were not renamed: SAFEGUARD-REFUSAL-ON-ML-WORK with MODEL-REFUSAL-ENDS-TURN and OPS-SAFETY-REFUSAL-UNDETECTED; SEC-INSTRUCTION-FILE-POISONING with SEC-SKILL-POISONING and SEC-HIDDEN-TEXT-IN-DOCUMENTS; READONLY-HOOK-FAIL-OPEN-WHEN-INTERPRETER-MISSING with HOOK-FAIL-OPEN-DEFAULT and HOOK-INTERPRETER-RESOLUTION; HOOK-FAILURE-MODE-DEPENDS-ON-SHELL with PORT-WINDOWS-HOOK-SHELL; SKILL-NAME-COLLISION with SKILL-CONFLICT-DISPLACEMENT; SKILL-VALUE-UNMEASURED with SKILL-EFFICACY-UNMEASURED and EVAL-KIT-EFFECT-UNMEASURED; EARLY-STOP-UNATTENDED with LOOP-PREMATURE-STOP; JUDGE-SAME-MODEL-BIAS with LOOP-KEEP-DECISION-BY-MODEL.
- Candidate rows 26, 38, 48 and 49 repeat candidates in the security and platform notes in this folder. The decisions agree with those notes, with one difference: the platform sweep has one row for both permission keys and marks it core, while rows 38 and 49 here are optional because they serve the opt-in loop.
