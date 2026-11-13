# Scout note: cross-agent standards and other coding agents (keeping the agent-specific layer thin)

Checked 10 and 11 November 2026. Status tags: **[V]** Verified from a primary source on the date given,
**[I]** Inferred (primary source is silent or indirect, or the source is an AI-generated wiki or a third-party table),
**[U]** Unverified (user report, secondary source, or not re-checked). Dates are YYYY-MM-DD.
Builds on `docs/research-notes/claude_code_features.md` and `skills_plugins_mcp.md` (23 October 2026); it does not redo them.

## Summary (10 lines)

1. One rules file can serve all three target agents: write the kit's block into `AGENTS.md` and make `CLAUDE.md` import it with `@AGENTS.md`. A bare new `CLAUDE.md` silently stops Claude Code reading an existing `AGENTS.md`.
2. Agent Skills is a real cross-agent standard (46 listed clients, no version number). Two copies of the skill, in `.claude/skills/` and `.agents/skills/`, cover Claude Code, Codex, Cursor, Gemini CLI, OpenCode, Copilot, Amp and Droid. Use only the six standard frontmatter fields.
3. There is no common hook standard, but Claude Code's `PreToolUse` schema is the de facto one: Codex, Qwen Code, Droid and VS Code copy it; Cursor and Copilot CLI import Claude hook files; Gemini CLI, OpenCode, Amp and Kiro differ.
4. `deny` is portable everywhere. `ask` is not: Codex runs the tool anyway, Cursor `preToolUse` ignores it, Copilot denies it in autopilot. The guard needs one internal vocabulary and a per-agent mapping, with `ask` becoming `deny` whenever nobody can answer.
5. Failure defaults differ and are mostly fail-open: Claude Code needs `onFailure: "block"`, Cursor needs `failClosed: true`, Codex documents no switch and skips changed hooks until re-trusted, Copilot fails open on timeout.
6. Cursor and Copilot CLI already load the kit's existing `.claude/settings.json` hook today, unsupported and without a fail-closed option. The ports must own this (native config, duplicate-call handling), not ignore it.
7. The installer should write the few per-agent files itself. Sync tools (`rulesync` v43.8.0, `ruler` v0.3.46, `npx skills` v1.8.0) all need Node and the network, and none was seen to set fail-closed hook options or to handle hook trust.
8. A per-agent `doctor` check (hook wired, trusted, interpreter resolves, a canary command is denied) is the missing piece that makes "enforced here, advisory there" a stated fact rather than a hope.
9. Evidence on instruction files is negative: two 2026 studies found no measurable success gain from context files and one found more than 20% extra cost. Keep the block short and put protections in code, not prose.
10. Ledger candidates by port cost: Copilot CLI and Qwen Code and Droid are low (Claude-shaped hooks); Gemini CLI is medium (own schema); OpenCode, Amp and Kiro are medium to high (in-process TypeScript plugins or undocumented payloads).

## Method and coverage

- Sources read through the web only; nothing installed, cloned or executed. Local commands run: `opencode --version` (1.18.34), `opencode --help`, `opencode run --help` (2026-11-10).
- Query families used: latest release notes (six agents), state-of or survey (context-file studies, eleven-system source study), alternatives (common hook formats, plugin packaging, sync tools), limitations or postmortems (context files, skill conflicts), security or failure modes (issue trackers, two papers), awesome lists (seen in repository search results only), benchmarks or leaderboards (attempted; the public terminal benchmark leaderboard page returned no rows to the fetcher).
- Limits: the session's web-search budget ran out and the Exa search endpoint was rate-limited, so the benchmark and awesome-list families are thin. Long pages were read through a summarising fetcher, so field names below were extracted by a model from the page and should be confirmed during the build.
- Nothing was tested on the machine: every statement about agent behaviour comes from documentation, not from a run.
- Candidates: 40 recorded in `agent-standards.candidates.jsonl` (9 Adopt, 6 Trial, 9 Assess, 9 Hold, 7 Reject).

## Q1. AGENTS.md

**Governance and specification**
- Plain Markdown, no required fields, no numbered version. Nested files allowed; the file nearest the edited file wins; explicit user prompts override. Stewarded by the Agentic AI Foundation under the Linux Foundation. Repo 25,424 stars, MIT, created 2025-08-19. Source: https://agents.md/ and https://github.com/agentsmd/agents.md (checked 2026-11-10/11). **[V]**
- The foundation was announced in December 2025 with MCP, goose and AGENTS.md as founding projects. Source: search summary of https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation (page not opened, 2026-11-11). **[I]**
- Agent Skills is not described as a foundation project; its README says it was originally developed by Anthropic and is open to contributions. Source: https://github.com/agentskills/agentskills (2026-11-11). **[V]**

**Who reads it natively (November 2026)**

| Agent (version checked) | Reads `AGENTS.md` | Nesting and precedence | Other instruction files | Source, date, status |
|---|---|---|---|---|
| Claude Code 2.1.322 | Yes since 2.1.277, but by default only when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` exists in the working directory or above (setting `claude-md-or-agents-md`). `claude-md-and-agents-md` can only be set in user, `--settings` or managed settings, not in project settings. | Reads every `AGENTS.md` and `.claude/AGENTS.md` from cwd upward at start, subdirectory files on demand; `@path` imports (max four hops). Not read: `AGENTS.local.md`, `AGENTS.override.md`, anything under `.agents/`. | `CLAUDE.md`, `.claude/rules/` | https://code.claude.com/docs/en/memory, 2026-11-10 **[V]** |
| Codex CLI 0.167.0 | Yes | Root to cwd, one file per directory (`AGENTS.override.md`, then `AGENTS.md`, then `project_doc_fallback_filenames`), concatenated, closer wins; combined cap `project_doc_max_bytes` 32 KiB; built once per run. Global `~/.codex/AGENTS.md`. | fallback names via config | https://developers.openai.com/codex/guides/agents-md, 2026-11-10 **[V]** |
| Cursor (editor 3.5 docs, CLI 2026.10.22) | Yes, root and subdirectories | Nested files combine with parents, more specific wins. Rank against `.cursor/rules` not stated. Rule order: team, project, user. | `.cursor/rules/*.mdc` (frontmatter `alwaysApply`, `globs`, `description`; plain `.md` ignored); CLI also reads root `CLAUDE.md` | https://cursor.com/docs/rules, https://cursor.com/docs/cli/using, https://cursor.com/docs/cli/changelog, 2026-11-11 **[V]** |
| Gemini CLI 0.67.0 | Only if configured: `context.fileName: ["AGENTS.md", ...]` in `settings.json`; default name is `GEMINI.md` | Global, workspace and parents, plus just-in-time files near accessed paths; `@file.md` imports | `GEMINI.md` | https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md, 2026-11-11 **[V]** |
| OpenCode 1.19.5 | Yes | Walks up from cwd; first match wins per category; if both exist only `AGENTS.md` is used. Nested subdirectory files only via the `instructions` globs. | `CLAUDE.md` fallback, `~/.claude/CLAUDE.md`; `OPENCODE_DISABLE_CLAUDE_CODE*` switches | https://opencode.ai/docs/rules/, 2026-11-11 **[V]** |
| GitHub Copilot CLI 1.0.109 | Yes | Repo root, cwd, directories between, and directories of files being worked on; all applicable files are combined, identical copies de-duplicated; no general precedence order defined | `CLAUDE.md`, `.claude/CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md` | https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions, 2026-11-11 **[V]** |
| Kiro | Yes, always included, root and subdirectories | Inclusion modes do not apply to it | `.kiro/steering/*.md` | https://kiro.dev/docs/steering/, 2026-11-11 **[V]** |
| Amp, Droid | Yes (listed as originators or adopters) | not read | not read | https://agents.md/, 2026-11-10 **[I]** |
| Qwen Code | Configurable through `context.fileName`; default not stated on the page read | not read | `QWEN.md` | https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/, 2026-11-11 **[I]** |

**Relation to CLAUDE.md, GEMINI.md and Cursor rules, and what follows for the kit**
- Recommended single-source pattern from the Claude Code docs: `CLAUDE.md` containing `@AGENTS.md` plus any Claude-only lines; symlinks are discouraged on Windows. https://code.claude.com/docs/en/memory, 2026-11-10. **[V]**
- Hazard: if the installer creates `CLAUDE.md` in a repository that had only `AGENTS.md`, Claude Code stops reading that `AGENTS.md` by default. Rule for the installer: block goes in `AGENTS.md`; `CLAUDE.md` gets one marked `@AGENTS.md` line; existing installs have the old block moved, not duplicated. **[I]** (follows from the documented default)
- Cursor CLI and Copilot CLI read both `AGENTS.md` and `CLAUDE.md`; an import line avoids a doubled block there. **[I]**
- Size limits that bind: Codex 32 KiB combined; Claude Code advises under 200 lines per file; Cursor advises under 500 lines per rule. Sources above. **[V]**
- Evidence that instruction files are weak levers:
  - arXiv 2602.11988 v3 (2026-09-29): context files generally did not raise task success and raised inference cost by more than 20% on average. https://arxiv.org/abs/2602.11988, 2026-11-11. **[V]** (abstract only)
  - arXiv 2607.27250 (2026-07-28): two agents, 17 tasks, 288 runs; context-file strategy did not measurably change correctness (effect bounded to roughly 10 to 15 points). https://arxiv.org/abs/2607.27250, 2026-11-11. **[V]** (abstract only; small study)
  - Consequence: the block states rules briefly; enforcement belongs to the guard, the controller and the frozen evaluator. **[I]**

## Q2. Agent Skills (SKILL.md) as an open standard

**Specification** (https://agentskills.io/specification, 2026-11-10 **[V]**)
- No numbered version. Frontmatter: `name` (required, at most 64 characters, lowercase letters, digits and hyphens, must match the directory), `description` (required, at most 1024 characters), `license`, `compatibility` (at most 500 characters), `metadata` (string map), `allowed-tools` (experimental). Body under 500 lines advised. Folders `scripts/`, `references/`, `assets/`. Validator: `skills-ref validate <dir>`.
- Install locations are not mandated. The implementer guide calls `.agents/skills/` a widely adopted cross-client convention and recommends trust-gating project skills. https://agentskills.io/client-implementation/adding-skills-support, 2026-11-10. **[V]**
- 46 clients listed in `docs/snippets/clients.jsx`, including Claude Code, Codex, Cursor, Gemini CLI, OpenCode, GitHub Copilot, VS Code, Amp, Goose, Factory, Kiro, Roo Code, Junie, Mistral Vibe. Repo 27,140 stars, Apache-2.0 code, CC-BY-4.0 docs, created 2025-12-16. https://github.com/agentskills/agentskills, 2026-11-11. **[V]**
- A source-code study of eleven agents found skill files in 9 of 11 and MCP in 8 of 11. https://arxiv.org/abs/2609.00006 (2026-07-15), 2026-11-11. **[V]** (abstract only)

**Directories each agent scans (project level)**

| Agent | Project directories | Duplicate-name rule | Source, date, status |
|---|---|---|---|
| Claude Code 2.1.322 | `.claude/skills/` (also nested `<subdir>/.claude/skills`, `--add-dir` directories, plugins, managed, `~/.claude/skills`). `.agents/skills` appears nowhere on the page (whole page read). | managed wins over personal, personal wins over project: a user-level skill with the same name hides the project copy; plugin skills are namespaced | https://code.claude.com/docs/en/skills, 2026-11-11 **[V]** for the list and the rule, **[I]** for the absence |
| Codex CLI 0.167.0 | `.agents/skills/` from cwd up to repo root; `~/.agents/skills`; `/etc/codex/skills` | same-name skills are not merged, both appear | https://developers.openai.com/codex/skills, 2026-11-10 **[V]** |
| Cursor | `.agents/skills/`, `.cursor/skills/`, and for compatibility `.claude/skills/`, `.codex/skills/` (plus user-level equivalents); CLI the same since March 2026 | not stated | https://cursor.com/docs/context/skills, https://cursor.com/docs/cli/changelog, 2026-11-10/11 **[V]** |
| Gemini CLI 0.67.0 | `.gemini/skills/`, `.agents/skills/` | higher tier wins; within a tier `.agents/skills` wins. Activation asks the user for consent. | https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/skills.md, 2026-11-11 **[V]** |
| OpenCode 1.19.5 | `.opencode/skills/`, `.claude/skills/`, `.agents/skills/` | source registered later wins | https://opencode.ai/docs/skills/, 2026-11-11 **[V]** |
| GitHub Copilot | `.github/skills/`, `.claude/skills/`, `.agents/skills/`; personal `~/.copilot/skills`, `~/.agents/skills` | not stated | https://docs.github.com/en/copilot/concepts/agents/about-agent-skills, 2026-11-11 **[V]** |
| Amp, Droid | `.agents/skills/` | not read | https://github.com/vercel-labs/skills/blob/main/docs/agents.md, 2026-11-11 **[I]** (third-party table) |
| Kiro CLI, Qwen Code | `.kiro/skills/`, `.qwen/skills/` | not read | same table **[I]** |

- Claude Code and Codex share no skill directory, so a three-agent install needs two copies (no symlinks on Windows). Cursor, Copilot and OpenCode then see the same name twice. **[I]**
- Under the Codex `workspace-write` sandbox `.agents`, `.codex` and `.git` are read-only to the agent. Good for tamper resistance of the skill and guard; the kit's writable state must live elsewhere. https://learn.chatgpt.com/docs/agent-approvals-security, 2026-11-11. **[V]**
- Claude Code's own troubleshooting advice: a rule that must hold every time belongs in a hook, not in skill text; after compaction only the start of an invoked skill may be kept, so the most important instructions go at the top of `SKILL.md`; malformed frontmatter loads the body with empty metadata, so nothing matches the description. `claude plugin validate .claude/skills` checks frontmatter (2.1.233+). https://code.claude.com/docs/en/skills, 2026-11-11. **[V]**

**Frontmatter differences**
- Claude Code accepts many extra fields (`when_to_use`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell`, `disable-model-invocation`, `user-invocable` and more). https://code.claude.com/docs/en/skills, 2026-11-10. **[V]**
- Cursor: `name`, `description`, `paths`, `disable-model-invocation`, `icon`, `color`, `metadata`. https://cursor.com/docs/context/skills, 2026-11-10. **[V]**
- OpenCode: `name`, `description`, `metadata.opencode/autoinvoke`, `disable-model-invocation`; `license` and `compatibility` accepted but not interpreted; the skill ID comes from the path. https://opencode.ai/docs/skills/, 2026-11-11. **[V]**
- Codex: standard fields plus an optional `agents/openai.yaml`; list budget 2% of context or 8,000 characters. https://developers.openai.com/codex/skills, 2026-11-10. **[V]**
- Consequence: shared `SKILL.md` uses `name` and `description` only (plus `license`, `metadata` if wanted), repo-relative script paths, and no `${CLAUDE_SKILL_DIR}`. **[I]**

**Evidence on skill conflicts and poisoning**
- arXiv 2610.11647 v2 (2026-10-13): about one in four installed skills sits beside a similar one; across 6,368 runs a similar skill displaced the installed one in about one run in five without lowering task completion; install location, not listing order, decides; a pre-tool hook at the first skill read restored fidelity. https://arxiv.org/abs/2610.11647, 2026-11-11. **[V]** (abstract only)
- arXiv 2611.12155 (2026-11-09): procedural poisoning of third-party skills that keeps the advertised function; most payloads evaded the scanners tested. https://arxiv.org/abs/2611.12155, 2026-11-11. **[V]** (abstract only, two days old)

**Install and sync tools for skills**
- `npx skills` (vercel-labs/skills) v1.8.0, 2026-11-10; MIT; 38,866 stars; 740 open issues; 79 agents; canonical `.agents/skills/<name>`; `skills-lock.json` v2 with a SHA-256 `computedHash` per skill and `install --frozen-lockfile`; anonymous telemetry on by default (`DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1`). https://github.com/vercel-labs/skills, 2026-11-11. **[V]** Symlink or copy behaviour on Windows: not on the pages read. **[U]**
- `openskills` 10,828 stars; not examined. https://github.com/numman-ali/openskills, 2026-11-11. **[U]**
- `gh skill` exists for discovery and install per the Copilot docs; flags from the earlier note (`--agent`, `--pin`) not re-checked. https://docs.github.com/en/copilot/concepts/agents/about-agent-skills, 2026-11-11. **[U]** for flags
- `gemini skills install <git-url> --consent`, `--scope user|workspace`. Gemini CLI docs above. **[V]**

## Q3. Hooks and permission systems

**Comparison table**

| Agent (version) | Hook config files | Pre-tool events | Payload (stdin JSON unless noted) | Decision vocabulary and shape | Failure default | Trust gate |
|---|---|---|---|---|---|---|
| Claude Code 2.1.322 | `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude/settings.json`, plugins, managed | `PreToolUse`, `PermissionRequest` | `session_id`, `cwd`, `permission_mode`, `hook_event_name`, `tool_name`, `tool_input`, `tool_use_id` | `hookSpecificOutput.permissionDecision`: `allow`, `deny`, `ask`, `defer`; `permissionDecisionReason`; exit 2 blocks; precedence deny, defer, ask, allow | other non-zero exits do not block unless `onFailure: "block"` (2.1.295+) | workspace trust |
| Codex CLI 0.167.0 | `.codex/hooks.json`, `.codex/config.toml` `[hooks]`, `~/.codex/` equivalents, plugins, managed `requirements.toml` | `PreToolUse`, `PermissionRequest` | `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `model`, `permission_mode`, `turn_id`, `tool_name` (`Bash`, `apply_patch`, `mcp__server__tool`), `tool_use_id`, `tool_input.command` | Same shape as Claude Code; `allow` and `deny` honoured; legacy `{"decision":"block"}`; exit 2 blocks. `ask` is parsed but unsupported: the hook run is marked failed and the tool call continues. `PermissionRequest`: `decision.behavior` `allow` or `deny` | unsupported output continues the call; crash and timeout not stated; default timeout 600 s | project `.codex/` layer must be trusted and each hook definition is trusted by hash; new or changed hooks are skipped until reviewed in `/hooks`; `--dangerously-bypass-hook-trust` for one run |
| Cursor (editor 3.5, CLI 2026.10.22) | `.cursor/hooks.json` (`"version": 1`), `~/.cursor/hooks.json`, enterprise, team | `preToolUse`, `beforeShellExecution`, `beforeMCPExecution`, `beforeReadFile`, `subagentStart` | common `conversation_id`, `generation_id`, `model`, `hook_event_name`, `cursor_version`, `workspace_roots`, `user_email`, `transcript_path`; `preToolUse`: `tool_name` (`Shell`, `Read`, `Write`, `Grep`, `Delete`, `Task`, `MCP:<tool>`), `tool_input` (`command`, `working_directory`), `cwd`; `beforeShellExecution`: `command`, `cwd`, `sandbox` | `permission`: `allow`, `deny`, `ask`; `user_message`, `agent_message`, `updated_input`; exit 2 denies. `ask` is enforced only for `beforeShellExecution` and `beforeMCPExecution`; `preToolUse` accepts it but does not enforce it. Merge order deny, ask, allow | other exit codes fail open unless the hook has `failClosed: true` | project hooks need a trusted workspace |
| Gemini CLI 0.67.0 | `hooks` in `.gemini/settings.json`, `~/.gemini/settings.json`, `/etc/gemini-cli/settings.json`, extensions | `BeforeTool` (also `BeforeToolSelection`, `BeforeModel`) | `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp`, `tool_name` (`run_shell_command`, `read_file`, `mcp_<server>_<tool>`), `tool_input`, `mcp_context` | top-level `decision`: `allow` or `deny` (alias `block`) with `reason`; `hookSpecificOutput.tool_input` rewrites; `continue: false` stops the loop; exit 2 blocks. No ask in hooks. Policy engine (TOML): `allow`, `deny`, `ask_user`; `ask_user` is treated as deny when non-interactive | other exit codes are warnings and the CLI continues; timeout in milliseconds, default 60000 | project hooks are fingerprinted; a changed name or command is treated as new and the user is warned |
| OpenCode 1.19.5 (local 1.18.34) | plugins in `.opencode/plugins/` or `~/.config/opencode/plugins/` (TypeScript or JavaScript), `plugins` array in `opencode.json(c)` | `tool.execute.before` (in-process function) | function arguments: `tool`, `sessionID`, `agent`, `messageID`, `id`, `input` | throw an error to block. Separate permission rules: `effect` `allow`, `deny`, `ask`; last matching rule wins; default allow-all; `--auto` approves everything not explicitly denied | not applicable | `--pure` runs without external plugins |
| GitHub Copilot CLI 1.0.109 | `.github/hooks/*.json` (`"version": 1`), `~/.copilot/hooks/`, `hooks` in `.github/copilot/settings.json`, `settings.local.json`, `~/.copilot/settings.json`, plugins, policy directory | `preToolUse`, `permissionRequest` (camelCase names give the native payload; PascalCase names give the Claude and VS Code compatible payload) | native: `sessionId`, `timestamp`, `cwd`, `toolName`, `toolArgs`; compatible: `tool_name`, `tool_input` | `permissionDecision`: `allow`, `deny`, `ask`; `permissionDecisionReason`; `modifiedArgs`; exit 2 denies. `ask` is denied under autopilot and the cloud agent | `preToolUse` non-zero exit denies (fail-closed); timeout fails open (default 30 s); HTTP hooks fail open | folder trust |

Sources (all 2026-11-10 or 2026-11-11): Claude Code from the 23 October note plus https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md **[V]**; Codex https://learn.chatgpt.com/docs/hooks **[V]**; Cursor https://cursor.com/docs/hooks **[V]**; Gemini CLI https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/reference.md, `docs/hooks/index.md`, `docs/reference/policy-engine.md` **[V]**; OpenCode https://opencode.ai/docs/permissions/ **[V]**, plugin argument shape and error-to-block from the DeepWiki answer for `sst/opencode` **[I]**; Copilot https://docs.github.com/en/copilot/reference/hooks-configuration **[V]**.

**Other agents, briefly** (2026-11-11)
- Qwen Code: 22 events including `PreToolUse` and `PermissionRequest`; `hookSpecificOutput.permissionDecision` `allow`, `deny`, `ask`; exit 2 blocks, other codes continue; matchers accept Claude tool names; sets `CLAUDE_PROJECT_DIR` beside `QWEN_PROJECT_DIR`; timeout in seconds, default 60. https://qwenlm.github.io/qwen-code-docs/en/users/features/hooks/ **[V]**
- Factory Droid: Claude-style event names; `.factory/hooks.json`, `~/.factory/hooks.json`; `permissionDecision` `allow`, `deny`, `ask`; exit 2 blocks; tool names `Execute`, `Read`, `Edit`, `Create`, `ApplyPatch`; `FACTORY_PROJECT_DIR`. https://docs.factory.com/cli/configuration/hooks-guide **[V]**
- VS Code agent hooks: Claude-style events and output, most restrictive wins, exit 2 blocks, other codes warn and continue; the local parser ignores matcher values; page is titled as a legacy reference. https://code.visualstudio.com/docs/agents/reference/hooks-reference **[V]**
- Kiro: `.kiro/hooks/<id>.json` with `"version": "v1"`, triggers including `PreToolUse`; stdin fields and blocking rule not on the page read. https://kiro.dev/docs/hooks/ **[V]** for the file shape, **[U]** for blocking
- Amp: TypeScript plugins in `.amp/plugins/` run with Bun; `tool.call` handler returns `allow` or `reject-and-continue`; `ctx.ui.confirm` asks the user. https://ampcode.com/manual/plugin-api **[V]**

**Is there a common hook format or compatibility layer?**
- No adopted standard. The convergence point is Claude Code's schema. **[I]** from the table above
- Agent Plugins Specification 1.0.0 (independent steering committee; Amazon, Cursor, Microsoft, OpenAI, Vercel named; 1.1.0 in draft) packages Agent Skills and MCP servers only. Hooks, agents, commands and rules are not portable component types in 1.0. https://github.com/agentplugins/agent-plugins-spec (1,445 stars, created 2026-04-03) and https://aaif.io/blog/from-skills-and-tools-to-portable-agent-plugins (2026-08-06), checked 2026-11-11. **[V]**
- A personal draft of a shared hook profile exists (1 star, last push 2026-07-10). https://github.com/danielgerlag/harness-ext-std, 2026-11-11. **[V]** that it is immature
- Portable guards exist and all use the same pattern (one rule engine, per-agent installers, a `doctor` command): https://github.com/Dicklesworthstone/destructive_command_guard (Rust, 6,329 stars), https://github.com/kenryu42/cc-safety-net (TypeScript, MIT, 1,991 stars, 14 agents), 2026-11-11. **[V]** for existence and scope; their per-agent mechanics were not read. **[U]**
- Agent Client Protocol: the agent sends `session/request_permission` with options of kind `allow_once`, `allow_always`, `reject_once`, `reject_always`; the client may answer automatically from settings. 51 agents listed; Cursor, Gemini CLI, OpenCode, Copilot, Kiro CLI, Qwen Code, Droid native; Claude Code and Codex through adapters. https://agentclientprotocol.com/protocol/tool-calls and https://agentclientprotocol.com/get-started/agents, 2026-11-11. **[V]** It is the only vendor-neutral way found to answer approvals by policy instead of bypassing them. **[I]**

**Which agents load another agent's hook or settings files**
- Cursor, editor and CLI: loads Claude Code hooks from `.claude/settings.local.json`, `.claude/settings.json` and `~/.claude/settings.json`, on by default (setting "Include Third-Party Plugins, Skills, and Other Configs"). Maps `PreToolUse` to `preToolUse`, `Bash` to `Shell`, `Edit` to `Write`; `Glob`, `Notification`, `PermissionRequest` have no equivalent. Exit 2 denies, other exit codes fail open, and there is no `failClosed` for imported hooks. Priority: Cursor's own project hooks outrank imported ones; all matching hooks run. Handling of `ask`, the stdin format given to an imported hook and de-duplication are not stated. https://cursor.com/docs/reference/third-party-hooks, 2026-11-11. **[V]**
- Cursor sets `CLAUDE_PROJECT_DIR` as an alias beside `CURSOR_PROJECT_DIR`; on Windows the desktop app runs hook commands through PowerShell. https://cursor.com/docs/hooks, 2026-11-11. **[V]**
- Copilot CLI: also reads `.claude/settings.json` and `.claude/settings.local.json` in the repository. https://docs.github.com/en/copilot/reference/hooks-configuration, 2026-11-11. **[V]**
- Gemini CLI: no automatic loading; an explicit `gemini hooks migrate --from-claude` converts `.claude/settings.json` into `.gemini/settings.json` (seconds to milliseconds). Sets `CLAUDE_PROJECT_DIR` as an alias. https://github.com/google-gemini/gemini-cli/pull/29899 and `docs/hooks/index.md`, 2026-11-11. **[V]**
- Codex: own files only; sets `CLAUDE_PLUGIN_ROOT` for plugin compatibility. https://learn.chatgpt.com/docs/hooks, 2026-11-10/11. **[V]**
- OpenCode: `CLAUDE.md` and `.claude/skills` only, not hooks. DeepWiki answer, 2026-11-11. **[I]**
- Claude Code: reads `AGENTS.md`; `/init` and `/import` migrate other agents' configuration on request; no automatic loading of other agents' hooks. https://code.claude.com/docs/en/memory, 2026-11-10. **[V]**

**Coverage gaps and failure reports that the guard must assume**
- Codex: hosted tools such as web search are not hooked; `write_stdin` to an already running command does not trigger `PreToolUse` again; the docs call tool hooks a guardrail, not a complete enforcement boundary. https://learn.chatgpt.com/docs/hooks, 2026-11-11. **[V]**
- Codex has no read tool event: reads go through the shell, and edits arrive as `apply_patch` with the patch text in `tool_input.command`. Same source. **[V]** The guard needs an `apply_patch` path parser to protect frozen and sealed paths. **[I]**
- Open user reports, not confirmed by the vendors:
  - Codex issue 57184 (0.164.0, 2026-10-26): the hook receives the session `cwd`, not the call's `workdir`, and the command still runs in `workdir`. https://github.com/openai/codex/issues/57184 **[U]**
  - Codex issue 45293: hook skipped when the session directory no longer exists. Issue 49736: no hook for sub-agent spawn. Issue 54806: on Windows desktop a trusted hook did not block a nested command. Issue 59146: the agent rephrases a denied command. https://github.com/openai/codex/issues **[U]**
  - Claude Code issue 106395 (2.1.316, auto mode, 2026-10-31): a hook `ask` showed no prompt and the call went ahead. Issue 94362: a hook file without the executable bit fails open. https://github.com/anthropics/claude-code/issues/106395 **[U]**
- A hook or an approval sees the call, not what the call goes on to do. arXiv 2609.28586 v1 (2026-09-23) names the gap between the approved invocation and its transitive effects (package install scripts, network use behind an MCP call); on 111 approval and trace pairs, unrecorded effects fell from 40 to 17 with command semantics and to 13 with decision-time metadata; it includes a Claude Code `PreToolUse` integration. https://arxiv.org/abs/2609.28586, 2026-11-11. **[V]** (abstract only; measured by the paper's authors)
- Claude Code changelog since the earlier note: "mods" that Claude writes turn on without asking in auto and bypass modes, and their own tool calls raise no permission prompt (deny rules still apply). Whether `PreToolUse` hooks fire for them was not established. https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md, 2026-11-10. **[V]** for the changelog text, **[U]** for hook coverage

**Static permission layers (second line of defence, no hook needed)**
- Codex: sandbox modes `read-only`, `workspace-write`, `danger-full-access`; approval policies `on-request`, `never`, granular (`untrusted` retired); `codex exec` defaults to a read-only sandbox; `--full-auto` is gone, use `--sandbox workspace-write`; `--approve-for-me` routes approvals to an automatic reviewer that fails closed; network off by default in `workspace-write`; Windows sandbox "MXC" with elevated and unelevated fallbacks. https://learn.chatgpt.com/docs/agent-approvals-security and https://learn.chatgpt.com/docs/non-interactive-mode, 2026-11-11. **[V]**
- Codex rules (experimental): `.codex/rules/*.rules` (trusted projects) and `~/.codex/rules/`; `prefix_rule(pattern=[...], decision="allow"|"prompt"|"forbidden", justification=..., match=[...], not_match=[...])`; most restrictive wins; only simple chains are split, anything with redirection or substitution is judged as one `bash -lc` string; test with `codex execpolicy check --pretty --rules <file> -- <command>`. https://learn.chatgpt.com/docs/agent-configuration/rules, 2026-11-11. **[V]**
- Cursor CLI: `.cursor/cli.json` and `~/.cursor/cli-config.json`, `permissions.allow` and `permissions.deny` with `Shell(...)`, `Read(...)`, `Write(...)`, `WebFetch(...)`, `Mcp(server:tool)`; deny wins. https://cursor.com/docs/cli/reference/permissions, 2026-11-11. **[V]**
- Cursor run modes: Auto-review (default), Allowlist, Run Everything; sandbox on macOS (Seatbelt) and Linux (Landlock and seccomp, kernel 6.2+); Windows is not mentioned. https://cursor.com/docs/agent/security/run-modes, 2026-11-11. **[V]**; native Windows therefore has no documented sandbox. **[I]**
- Cursor headless: `agent -p`, `--force` (alias `--yolo`), `--output-format text|json|stream-json`, `CURSOR_API_KEY`. One page says changes are only proposed without `--force`; another says the CLI has full write access in non-interactive mode. https://cursor.com/docs/cli/headless and https://cursor.com/docs/cli/using, 2026-11-11. **[U]** (the two pages disagree)
- Gemini CLI policy files load from `~/.gemini/policies/*.toml` and admin directories; workspace-level policy files are currently disabled. `docs/reference/policy-engine.md`, 2026-11-11. **[V]**

## Q4. Config-sync tools and MCP configuration formats

**Tools that generate per-agent configuration from one source**

| Tool (version, date) | Covers | Runtime | Maturity signals | Verdict for a small stdlib installer |
|---|---|---|---|---|
| `rulesync` v43.8.0 (2026-11-08) | rules, ignore, MCP, commands, subagents, skills, hooks, permissions for Claude Code, Codex, Cursor, OpenCode, Copilot and about 60 more | Node CLI (also brew, single binary) | 1,597 stars, MIT, major version 43 in 17 months | Do not depend on it; useful as a cross-check of mappings |
| `ruler` v0.3.46 (2026-10-22) | rules, MCP propagation, skills (experimental); no hooks | Node 20+ | 2,967 stars, MIT, 0.x | Do not depend on it |
| `npx skills` v1.8.0 (2026-11-10) | skills only, 79 agents, lock file with hashes | Node, network, telemetry on by default | 38,866 stars, 740 open issues, ten months old | Not for the installer; possible optional distribution channel |
| `apm` v0.35.0 (2026-10-22) | agent package manager | Python package | 4,324 stars, 0.x; details not read | Hold |
| `dotagents` (263 stars), `ai-rules` (144 stars) | rules and skills | Node, Rust | small | Reject |

Sources: https://github.com/dyoshikawa/rulesync, https://github.com/intellectronica/ruler, https://github.com/vercel-labs/skills, https://github.com/microsoft/apm, https://github.com/getsentry/dotagents, https://github.com/block/ai-rules, all 2026-11-11. **[V]** for versions, stars and stated scope.

Recommendation: the installer writes the files itself. For three agents that is one `AGENTS.md` block, one `CLAUDE.md` import line, two skill copies, three hook files (`.claude/settings.json` merge, `.codex/hooks.json`, `.cursor/hooks.json`) and, only when the MCP module is on, per-agent MCP entries. All but Codex MCP are JSON or Markdown, which the standard library handles; Codex hooks can go in `.codex/hooks.json`, so no TOML writer is needed in core. A sync tool would add a runtime, a network fetch and a fast-moving dependency, and none was seen to set `failClosed` or `onFailure` or to handle hook trust (READMEs only; their generated output was not inspected). **[I]**

**MCP configuration formats** (2026-11-11 unless noted)

| Agent | File | Shape | Notes | Status |
|---|---|---|---|---|
| Claude Code | `.mcp.json` (project) | `mcpServers.<name>`: `command`, `args`, `env` or `type: "http"`, `url`, `headers` | as used by the kit's `mcp.json`; not re-read today | **[I]** |
| Codex | `~/.codex/config.toml`, `.codex/config.toml` (trusted projects) | TOML `[mcp_servers.<name>]`: `command`, `args`, `env`, `env_vars`, `cwd` or `url`, `bearer_token_env_var`, `http_headers`, `env_http_headers` | `enabled`, `required`, `startup_timeout_sec` (10), `tool_timeout_sec` (60), `enabled_tools`, `disabled_tools`; `codex mcp add` | https://learn.chatgpt.com/docs/extend/mcp?surface=cli **[V]** |
| Cursor | `.cursor/mcp.json`, `~/.cursor/mcp.json` | `mcpServers.<name>`: `command`, `args`, `env`, `envFile` or `url`, `headers`, `auth` | interpolation `${env:NAME}`, `${workspaceFolder}`, `${userHome}`; the CLI detects the same file | https://cursor.com/docs/mcp, https://cursor.com/docs/cli/using **[V]** |
| Gemini CLI | `.gemini/settings.json`, `~/.gemini/settings.json` | `mcpServers.<name>`: `command`, `args`, `env`, `cwd` or `httpUrl` (streamable HTTP) or `url` (SSE), `headers` | no `type` key; `timeout` ms (600000), `trust`, `includeTools`, `excludeTools`; `$VAR`, `${VAR}`, `%VAR%` | `docs/tools/mcp-server.md` **[V]** |
| OpenCode | `opencode.json(c)` | `mcp.servers.<name>` (V2; V1 put names directly under `mcp`): `type: "local"`, `command` array, `environment`, `cwd` or `type: "remote"`, `url`, `headers`, `oauth` | `disabled`, not `enabled` | https://opencode.ai/docs/mcp-servers/ **[V]** |
| Copilot CLI | `~/.copilot/mcp-config.json`, `.mcp.json` (cwd up to repo root), `.github/mcp.json` | `mcpServers.<name>`: `type: "local"`, `command`, `args`, `env`, `tools` or `type: "http"`, `url`, `headers` | project servers need folder trust; `.vscode/mcp.json` is not read | https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers **[V]** |

Differences that break naive copying: the top-level key and nesting, TOML against JSON, `type` values (`http` against `remote` against none), `url` against `httpUrl`, `command` as string against array, `env` against `environment`, three interpolation syntaxes, and different trust rules for project-level servers. MCP servers need the network, so this stays an optional module. **[I]**

## Q5. Other agents as ledger candidates (not required ports)

| Agent | Version or doc date | Instruction file | Skills | Hooks | Headless | Sandbox | Port effort |
|---|---|---|---|---|---|---|---|
| GitHub Copilot CLI | 1.0.109, 2026-11-10 | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` | `.claude/skills`, `.agents/skills`, `.github/skills` | native plus imports `.claude/settings.json` | `copilot -p`, autopilot | exists, details not read | Low: the Claude files may already work; add a native `.github/hooks/*.json`, test ask-to-deny and the timeout fail-open |
| Qwen Code | docs 2026-11-11 | `QWEN.md`, `context.fileName` | `.qwen/skills` | Claude-shaped, accepts Claude tool names | `-p`, `--max-wall-time`, `--max-tool-calls` | Docker or Podman, Seatbelt, bwrap or landlock | Low: reuse the Claude adapter; extra skill copy; default approval mode is `auto` |
| Factory Droid | docs 2026-11-11 | `AGENTS.md` | `.agents/skills` | Claude-shaped, own tool names | `droid exec --auto` with level low, medium or high; read-only by default, stops and exits non-zero above the level | none stated | Low to medium: Claude adapter plus a tool-name map |
| Gemini CLI | 0.67.0, 2026-11-04 | `GEMINI.md`; `AGENTS.md` by setting | `.gemini/skills`, `.agents/skills` | own schema (`BeforeTool`, `decision`) | `-p`, `--output-format`, `--approval-mode` (default, auto_edit, yolo, plan) | Docker or Podman, Seatbelt, gVisor, LXC, Windows native | Medium: new adapter, settings merge for hooks and `context.fileName`, millisecond timeouts, fail-open on crash |
| OpenCode | 1.19.5, 2026-10-28 (local 1.18.34) | `AGENTS.md` | `.opencode/skills`, `.claude/skills`, `.agents/skills` | TypeScript plugin only | `opencode run --format json`, `--auto` | none; permissions are not a sandbox | Medium to high: a TypeScript shim that calls the Python guard; config schema moved from V1 to V2 |
| Kiro CLI | docs 2026-11-11 | steering plus `AGENTS.md` | `.kiro/skills` | own JSON schema | not read | not read | Medium: payload and blocking rule undocumented on the page read |
| Amp | docs 2026-11-11 | `AGENTS.md` | `.agents/skills` | TypeScript plugin (Bun) | execute mode, not read | not stated | Medium to high |
| Newcomers seen in registries | Antigravity CLI, Pi, Kilo Code, Mistral Vibe, Junie, Hermes Agent | not evaluated | | | | | not estimated |

Sources: rows above cite the pages listed in Q1 to Q3; Droid headless from https://docs.factory.com/cli/droid-exec/overview; Qwen settings from https://qwenlm.github.io/qwen-code-docs/en/users/configuration/settings/; Gemini flags from `docs/cli/cli-reference.md` and `docs/cli/sandbox.md`; all 2026-11-11. **[V]** for the cells with a named mechanism, **[I]** for effort estimates.

## Changed since 23 October or wrong in the earlier notes

1. Claude Code is at 2.1.322, not 2.1.308. Since then: fixes for a read-only command that ran outside the sandbox without a prompt, for permission checks judging a write from the wrong folder, for deny rules not covering `cp` and `mv` into a directory, and for a hook `ask` lost when another hook's `defer` finished first; the new "mods" extension concept. https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md, 2026-11-10. **[V]**
2. The earlier notes do not mention that Claude Code reads `AGENTS.md` natively (2.1.277+) or the shadowing rule that goes with it. https://code.claude.com/docs/en/memory. **[V]**
3. The earlier notes treat the kit as Claude-only. In effect it is not: Cursor (default on) and Copilot CLI load `.claude/settings.json` hooks, and Cursor, Copilot and OpenCode load `.claude/skills`. The kit's hook command uses bash-only syntax (`${CLAUDE_PROJECT_DIR:-.}`), which is likely to misbehave where Cursor runs it through PowerShell on Windows. Sources in Q3. **[V]** for the loading, **[I]** for the Windows misbehaviour (untested)
4. The earlier notes rely on `ask` as a dependable middle decision. It is not portable (Q3 table), and there is an open report that it went ahead without a prompt in auto mode on 2.1.316. **[V]** for portability, **[U]** for the report
5. Codex documentation moved: `developers.openai.com/codex/...` now answers with permanent redirects to `learn.chatgpt.com/docs/...` (observed 2026-11-11). Codex also dropped `--full-auto` and the `untrusted` approval policy. **[V]**
6. New since the earlier notes or not covered there: Agent Plugins Specification 1.0.0 (August 2026), `npx skills` lock file with content hashes (v1.8.0, 2026-11-10), the skill-conflict study (October 2026) and the skill-poisoning paper (9 November 2026). **[V]**
7. Not re-checked: the earlier note's count of 33 hook events, the `gh skill --pin` flags and the Snyk skill-scan numbers. **[U]**

## Concerns any design must handle

- HOOK-ASK-NOT-PORTABLE: a middle decision runs the tool on some agents
- HOOK-FAIL-OPEN-DEFAULT: crash, timeout or bad output lets the call through
- HOOK-TRUST-SKIP-SILENT: a changed hook is skipped until re-approved
- HOOK-TIMEOUT-UNITS: seconds on some agents, milliseconds on others
- HOOK-PAYLOAD-SCHEMA-DRIFT: field and tool names differ and change per release
- HOOK-CWD-MISREPORTED: reported directory may not be where the command runs
- HOOK-COVERAGE-GAPS: hosted tools, stdin to running shells, sub-agent spawns, extension-made calls
- HOOK-DOUBLE-FIRE-IMPORT: one guard reached natively and through another agent's imported settings
- HOOK-INTERPRETER-RESOLUTION: shell and Python launcher differ per agent and operating system
- GUARD-EVASION-REPHRASE: agent rewrites a denied command until it passes
- GUARD-SELF-TAMPER: agent can edit guard, config or skill files unless they are protected
- GUARD-PATCH-FORMAT-PARSING: edits arriving as patch text need their own path extraction
- GUARD-TRANSITIVE-EFFECTS: an allowed command triggers effects the guard never saw
- INSTR-FILE-SHADOWING: creating one instruction file hides another
- INSTR-FILE-SIZE-CAP: combined instruction text is truncated past a limit
- INSTR-ADVISORY-ONLY: prose rules do not measurably change outcomes
- SKILL-DUPLICATE-NAME: the same skill name in two directories or at user level; which copy wins differs per agent
- SKILL-CONFLICT-DISPLACEMENT: a similar co-installed skill replaces the intended one unnoticed
- SKILL-FRONTMATTER-PORTABILITY: non-standard fields are ignored or rejected elsewhere
- SKILL-SUPPLY-CHAIN-POISONING: third-party skills altered while keeping their advertised function
- PORT-NO-SYMLINK-WINDOWS: sharing by link is unavailable, copies can drift
- PORT-STATE-DIR-READONLY: sandbox makes agent config directories read-only, state must live elsewhere
- PORT-PARITY-DISCLOSURE: users must be told what is enforced and what is advice on each agent
- UNATTENDED-APPROVAL-BYPASS-PRESSURE: headless modes push toward approve-everything flags
- UNATTENDED-NO-SANDBOX-PLATFORM: no documented sandbox on some agent and platform pairs
- MCP-CONFIG-FORMAT-DIVERGENCE: six formats for the same server entry
- MCP-PROJECT-AUTOLOAD-TRUST: project-level servers load with differing trust rules
- SYNC-TOOL-DEPENDENCY-CHURN: generators add a runtime and break often
- DOC-URL-DRIFT: vendor documentation moves and versions change weekly
- UPGRADE-CONFIG-MIGRATION: moving the rules block must not lose or duplicate user content
- SEC-PROMPT-INJECTION: fetched documentation carries text addressed to agents

## Open questions

1. What stdin format does Cursor give a hook imported from `.claude/settings.json`: Claude's or its own? Does it de-duplicate with `.cursor/hooks.json`? (Docs silent.)
2. How do Cursor and Copilot list a skill present in both `.claude/skills` and `.agents/skills`: once or twice?
3. Does Codex continue or block when a `PreToolUse` command hook crashes or times out? Do untrusted project hooks run in `codex exec`, and can trust be established without the interactive `/hooks` screen?
4. Do hooks run inside or outside the Codex sandbox (can the guard write its audit log)?
5. Does the Cursor CLI in print mode apply edits and run shell commands without `--force`, and is there any sandbox on native Windows?
6. Do Claude Code `PreToolUse` hooks fire for tool calls made by "mods"?
7. Which Python launcher string is reliable in each agent's hook shell on native Windows (`python`, `py -3`, absolute path)?
8. Is `ask` dependable in Claude Code auto mode (open report), or should every non-interactive mode map it to `deny`?
9. Not researched here: how each agent defines read-only sub-agents (the kit's two reviewer roles) and whether a shared definition is possible. It was outside this area's five questions.
10. Where should the shared guard file and the writable state live? Under `.claude/` (no migration, not sandbox-protected on Codex), or guard and skill under `.agents/` (read-only under the Codex sandbox) with state in a separate directory?
11. What does the existing hook command do on native Windows when another agent runs it through PowerShell: block every call (Python exits 2 on a missing script path) or pass every call (launcher not found)? Untested.

## Redirect attempts

- Banner text at the top of pages on code.claude.com and agentskills.io addressed to automated readers, telling them to fetch the documentation index (`llms.txt`) before exploring. Benign. Not treated as a command; an index file was used once as a navigation aid by my own choice.
- The Exa search endpoint's rate-limit error told the client to create an account and API key. Not done.
- Tool-generated text, not third-party content, recorded for completeness: the search tool appended a reminder to list sources, and the fetch tool asked for a second call on cross-host redirects. Redirects were followed only to the vendors' own hosts (developers.openai.com to learn.chatgpt.com, docs.factory.ai to docs.factory.com).
- No hostile or task-changing instruction was found in any fetched page, paper, repository file or issue.
