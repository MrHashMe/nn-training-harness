# Claude Code native capabilities and exact config formats for a long-running NN-training harness

*State: Claude Code v2.1.308 (released 2026-10-22). Sources: official docs at code.claude.com/docs/en/ (read 2026-10-23; long pages read through a verbatim GitHub mirror synced 2026-10-22 and spot-checked against the live pages) and the official CHANGELOG. "vX (date)" means the release that introduced the feature. All docs URLs below are canonical official pages.*

## Hooks: events, config shape, stdin/stdout contract, env, subagents, modes, reload

### Takeaway
There are 33 events and 5 handler types. `PreToolUse` decides through `hookSpecificOutput.permissionDecision` (`allow|deny|ask|defer`) and can rewrite input with `updatedInput`. Exit 2 plus stderr is the simplest hard block. Hooks also fire inside subagents, and edits to settings files hot-reload. A hook `deny` wins in every mode, but a hook `allow` never overrides deny or ask rules.

### Cited Findings
- Events: `SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse, PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure, PostToolBatch, Notification, MessageDisplay, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, InstructionsLoaded, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, PreModelSwitch, PostModelSwitch, Elicitation, ElicitationResult, SessionEnd` — [hooks](https://code.claude.com/docs/en/hooks)
- Shape. The same structure works in settings.json, in a plugin's `hooks/hooks.json`, and as YAML in skill or agent frontmatter: `{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","if":"Bash(rm *)","command":"${CLAUDE_PROJECT_DIR}/.claude/hooks/guard.sh","timeout":30}]}]}}` — [hooks](https://code.claude.com/docs/en/hooks)
- Matchers. `"*"`, `""` or omitting the field matches everything. A value made only of letters, digits, `_`, `-`, spaces, `,` and `|` is an exact name or list of names. Anything else is an unanchored JS regex, so `Edit.*` also matches `NotebookEdit` (use `^Edit$` for an exact match). For MCP tools use `mcp__memory__.*`; a bare `mcp__memory` matches nothing. A matcher on an event that has no matcher support is silently ignored — [hooks](https://code.claude.com/docs/en/hooks)
- Matcher values by event: SessionStart `startup|resume|clear|compact|fork`; PreCompact and PostCompact `manual|auto`; SessionEnd `clear|resume|logout|prompt_input_exit|other`; Setup `init|maintenance`. UserPromptSubmit, Stop, PostToolBatch and CwdChanged take no matcher — [hooks](https://code.claude.com/docs/en/hooks)
- Handler types are `command|http|mcp_tool|prompt|agent` (`agent` is experimental).
  - Fields common to all types: `type`; `if` (exactly one permission rule, evaluated on tool events only, "best-effort"); `timeout` in seconds (defaults: 600 for command/http/mcp_tool, 30 for prompt, 60 for agent; command/http/mcp_tool drop to 30 on UserPromptSubmit and the model-switch events); `statusMessage`; `once` (honoured in skill frontmatter only).
  - command: `command`, `args` (exec form, no shell), `async`, `asyncRewake`, `shell` (`bash|powershell`), `onFailure` (`continue|block`, v2.1.295).
  - http: `url`, `headers`, `allowedEnvVars`, `onFailure`.
  - mcp_tool: `server`, `tool`, `input`.
  - prompt and agent: `prompt` (with a `$ARGUMENTS` placeholder) and `model`. The model replies `{"ok":false,"reason":"…"}`.
  - Sources: [hooks](https://code.claude.com/docs/en/hooks); [hooks-guide](https://code.claude.com/docs/en/hooks-guide)
- Common stdin fields: `session_id, prompt_id, transcript_path, cwd, scratchpad_dir, permission_mode` (one of `default|plan|acceptEdits|auto|dontAsk|bypassPermissions`), `effort.level`, `hook_event_name`. Inside subagents, `agent_id` and `agent_type` are added — [hooks](https://code.claude.com/docs/en/hooks)
- PreToolUse stdin adds `tool_name, tool_input, tool_use_id`, plus `mcp_server` for MCP tools. `file_path` is always absolute. `tool_input` fields by tool:
  - Bash: `command, description, timeout` (ms), `run_in_background`
  - Write: `file_path, content`
  - Edit: `file_path, old_string, new_string, replace_all`
  - Read: `file_path, offset, limit`
  - Glob: `pattern, path`
  - Grep: `pattern, path, glob, output_mode, -i, multiline`
  - WebFetch: `url, prompt, offset`
  - Agent: `prompt, description, subagent_type, model`
  - Source: [hooks](https://code.claude.com/docs/en/hooks)
- The SDK input types add Bash `dangerouslyDisableSandbox`, and give NotebookEdit as `notebook_path, cell_id?, new_source, cell_type? ("code"|"markdown"), edit_mode? ("replace"|"insert"|"delete")` — [sdk-ts](https://code.claude.com/docs/en/agent-sdk/typescript). `MultiEdit` appears only as a "legacy" tool name — [permissions](https://code.claude.com/docs/en/permissions)
- Exit codes:
  - 0 = success. Stdout is parsed as JSON only when it is exactly one JSON object.
  - 2 = block. For PreToolUse, stderr becomes Claude's denial reason.
  - Any other code = non-blocking error and the action proceeds, unless the hook sets `onFailure:"block"`. The docs say: "If your hook is meant to enforce a policy, use `exit 2`".
  - Source: [hooks](https://code.claude.com/docs/en/hooks)
- PreToolUse output: `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"…","updatedInput":{…},"additionalContext":"…"}}`.
  - `updatedInput` replaces the whole input object, and permission rules are evaluated against the rewritten input.
  - Since v2.1.300, unknown keys are dropped and input the tool rejects denies the call.
  - With several hooks, precedence is `deny > defer > ask > allow`.
  - `defer` works only with `-p` and a single tool call.
  - The old top-level `decision: approve|block` is deprecated for this event.
  - Sources: [hooks](https://code.claude.com/docs/en/hooks); [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Fields every event accepts: `continue`, `stopReason`, `suppressOutput` (accepted but does nothing), `systemMessage`. `additionalContext`, `systemMessage` and plain stdout are each capped at 10,000 characters — [hooks](https://code.claude.com/docs/en/hooks)
- SessionStart. Input: `source, model?, agent_type?, session_title?`. Plain stdout, or `hookSpecificOutput.additionalContext`, is added to Claude's context. It can also return `initialUserMessage`, `sessionTitle`, `watchPaths` and `reloadSkills`, but it cannot block. `CLAUDE_ENV_FILE` (append `export K=V` lines) is available only to SessionStart, Setup, CwdChanged and FileChanged hooks — [hooks](https://code.claude.com/docs/en/hooks)
- Stop and SubagentStop. Input: `stop_hook_active, last_assistant_message, background_tasks[], session_crons[]`. Output `{"decision":"block","reason":"…"}` keeps Claude working, capped at 8 consecutive continuations (raise with `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`) — [hooks](https://code.claude.com/docs/en/hooks)
- PreCompact input is `trigger, custom_instructions`, and it can block compaction. PostCompact receives `compact_summary` — [hooks](https://code.claude.com/docs/en/hooks)
- PermissionRequest output: `{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow","updatedInput":{…}}}}`. Exit 2 is ignored for this event. It still runs in `-p` mode, except under `dontAsk` — [hooks-guide](https://code.claude.com/docs/en/hooks-guide)
- Environment variables:
  - `CLAUDE_PROJECT_DIR` stays at the session's starting root even after Claude enters a worktree; the `cwd` field follows Claude.
  - Also set: `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_CODE_REMOTE="true"` (web sessions only), `CLAUDE_EFFORT`.
  - There is no `$CLAUDE_MODEL`.
  - Source: [hooks](https://code.claude.com/docs/en/hooks)
- Subagents. Hooks from settings, managed policy and plugins fire on subagent tool calls, with `agent_id` and `agent_type` in the input. Hooks in an agent's frontmatter live only while that agent runs, and a `Stop` hook there becomes `SubagentStop` — [hooks](https://code.claude.com/docs/en/hooks)
- Hooks and permission modes:
  - PreToolUse hooks fire "before any permission-mode check, in every permission mode, including `dontAsk`".
  - A `deny` "blocks the tool even in `bypassPermissions` mode".
  - An `"allow"` "doesn't bypass deny rules", and ask rules still prompt.
  - In auto mode, a hook's `ask` forces a prompt.
  - In `-p` with no permission host, prompts are denied and Claude reads the `permissionDecisionReason`.
  - Sources: [hooks-guide](https://code.claude.com/docs/en/hooks-guide); [permissions](https://code.claude.com/docs/en/permissions)
- Reload. "Direct edits to hooks in settings files are normally picked up automatically by the file watcher." `/hooks` is a read-only browser. To turn hooks off for one run, use `--settings '{"disableAllHooks": true}'` — [hooks](https://code.claude.com/docs/en/hooks); [settings](https://code.claude.com/docs/en/settings)
- `async:true` runs the hook without blocking and delivers its result on the next turn; it is killed when a `-p` run tears down. `asyncRewake:true` wakes Claude with stderr when the hook exits 2. A `-p` run executes project hooks even in a folder that was never trusted — [hooks](https://code.claude.com/docs/en/hooks); [headless](https://code.claude.com/docs/en/headless)

### Inferences
- Guard hooks should exit 2 (or return deny) and set `onFailure:"block"` so that a crashed guard fails closed.
- On macOS, Linux and WSL, Glob and Grep are absent by default and searches arrive as `Bash` `find`/`grep` — [tools](https://code.claude.com/docs/en/tools-reference). Path guards must parse Bash commands rather than rely on `Grep|Glob` matchers.

### Gaps (Unverified)
- The docs don't say what a hook's `ask` does in `bypassPermissions` or `acceptEdits` mode.
- My memory of older (2025) docs is a startup "hook snapshot" that needed `/hooks` review; I did not re-verify this. Current docs describe file-watcher reload instead.

## Permissions, settings precedence and permission modes

### Takeaway
Rules are evaluated deny, then ask, then allow, and a deny at any scope always wins. `Bash(x:*)` and `Bash(x *)` are equivalent. Bash rules match command text, not programs, so they are not a security boundary. Pair them with the sandbox and hooks.

### Cited Findings
- Precedence: managed > `--settings` > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`. List keys such as `permissions.allow` merge across files. Schema: `"$schema": "https://json.schemastore.org/claude-code-settings.json"` — [settings](https://code.claude.com/docs/en/settings)
- Rules use `Tool` or `Tool(specifier)` and are evaluated deny → ask → allow; the first match wins. A bare deny such as `"Bash"` removes the tool from Claude's context. Keys: `permissions.allow|ask|deny`, `defaultMode`, `additionalDirectories`, `disableBypassPermissionsMode:"disable"`, `disableAutoMode:"disable"` — [permissions](https://code.claude.com/docs/en/permissions)
- Bash pattern details:
  - "The `:*` suffix is an equivalent way to write a trailing wildcard", but only at the end of the pattern.
  - A trailing ` *` also matches the bare command, and the space matters: `Bash(ls *)` doesn't match `lsof`.
  - `Tool(param:value)` works in deny and ask rules for scalar parameters, e.g. `Bash(run_in_background:true)`, `Bash(dangerouslyDisableSandbox:true)`, `Agent(isolation:worktree)`.
  - Source: [permissions](https://code.claude.com/docs/en/permissions)
- Compound commands. The separators are `&&`, `||`, `;`, `|`, `|&`, `&` and newline. An allow rule must match every subcommand. Deny and ask rules hit any subcommand, including ones inside `$()`, subshells and loop bodies.
  - Stripped before matching: `timeout, time, nice, nohup, stdbuf, command, builtin, noglob` and bare `xargs`.
  - Never prefix-approved: `watch, setsid, ionice, flock`, and `find -exec/-delete`.
  - Not caught by the rules: `/bin/rm`, `bash -c '…'`, `git -C . push`.
  - Source: [permissions](https://code.claude.com/docs/en/permissions)
- Read and Edit paths use gitignore syntax:
  - `//abs` is an absolute path; `~/x` is under the home directory.
  - `/x` is relative to the settings source (project root for project settings, `~/.claude` for user settings).
  - `x` or `./x` is relative to the current directory.
  - `Read(.env)` matches at any depth. `src/**` as an allow rule matches only `cwd/src`, but as a deny or ask rule it matches at any depth.
  - Source: [permissions](https://code.claude.com/docs/en/permissions)
- A Read deny also blocks Edit and Write on the same path, but not NotebookEdit, so add an `Edit` deny too. Path rules written for `Write`, `NotebookEdit`, `MultiEdit` or `Glob` are never consulted. Read and Edit denies cover the built-in tools, Bash file commands such as `cat, head, tail, sed, tee`, and redirect targets. They do not cover "a Python or Node script that opens files itself"; for that the docs say to use the sandbox — [permissions](https://code.claude.com/docs/en/permissions)
- Other rule forms: `WebFetch(domain:*.example.com)`, `mcp__server__*`, `Agent(Explore)`, `Skill(name *)`. Tool-name globs such as `mcp__*` are allowed only in deny and ask rules — [permissions](https://code.claude.com/docs/en/permissions)
- Modes:
  - `default` (labelled Manual; alias `manual`, v2.1.200)
  - `acceptEdits`: edits plus `mkdir/touch/mv/cp` inside working directories
  - `plan`
  - `auto`: a classifier reviews actions
  - `dontAsk`: denies anything that would prompt; allow rules and hook `allow` still run
  - `bypassPermissions`: deny rules still block and ask rules still prompt; refused when running as root or with sudo outside a recognized sandbox
  - Sources: [modes](https://code.claude.com/docs/en/permission-modes); [permissions](https://code.claude.com/docs/en/permissions)
- Starting mode: `--permission-mode` > `defaultMode` > built-in default.
  - The built-in default is `auto` for interactive terminal sessions (v2.1.283, 2026-09-25) and `default` for `-p` and the SDK.
  - From v2.1.302 (2026-10-16), a `-p` run with no mode set denies any call that needs approval.
  - `defaultMode` values `auto` and `bypassPermissions` are ignored in project and local settings.
  - Source: [modes](https://code.claude.com/docs/en/permission-modes)
- Auto mode:
  - On entry it drops broad allow rules: `Bash(*)`, `Bash(python*)`, package-manager run commands, `Agent` and `Monitor`.
  - It pauses after 3 consecutive or 20 total blocks. In `-p` with no prompt tool, the blocked action is skipped and Claude keeps working.
  - Boundaries you state in conversation ("don't push") can be lost to compaction; use a deny rule for a guarantee.
  - The `autoMode` keys (`environment, allow, soft_deny, hard_deny, classifyAllShell`) are read only from user and managed settings. Inspect with `claude auto-mode defaults|config`.
  - Sources: [modes](https://code.claude.com/docs/en/permission-modes); [auto-cfg](https://code.claude.com/docs/en/auto-mode-config)
- Protected paths (never auto-approved except in bypass mode; allow rules don't pre-approve them):
  - Directories: `.git`, `.claude` (except `.claude/worktrees`), `.vscode`, `.husky`, `.devcontainer`
  - Files: `.bashrc`, `.zshrc`, `.gitconfig`, `.mcp.json`, `.pre-commit-config.yaml`
  - Critical-path removals (`rm -rf /`, `rm -rf ~`) are never auto-approved.
  - Source: [modes](https://code.claude.com/docs/en/permission-modes)
- Project `permissions.allow` rules apply only after the workspace trust dialog, and a `-p` run never shows that dialog — [permissions](https://code.claude.com/docs/en/permissions)

### Inferences
- In headless runs, put allow rules in user settings or `--settings`. Project allow rules are skipped in folders that haven't been trusted.

### Gaps (Unverified)
- I found no full list of the "known-safe" environment variables that allow rules match past.

## Sandboxing

### Takeaway
The sandbox is OS-level (Seatbelt on macOS, bubblewrap+socat on Linux/WSL2) and wraps only shell commands (Bash, PowerShell, Monitor) and their children. Read and Edit permission rules are merged into it, which makes them OS-enforced for sandboxed commands. On Linux, networking runs in a separate namespace behind an HTTP proxy that checks a domain allowlist.

### Cited Findings
- Turn it on with `/sandbox` or `"sandbox":{"enabled":true}`.
  - Default writable: the working directory, a per-user `$TMPDIR` and added directories.
  - Default readable: "most of the machine", including `~/.ssh`.
  - Network: the allowlist starts empty.
  - Outside the sandbox: the Read/Edit/WebFetch tools, hooks, MCP servers, the status line, and commands you type with `!`.
  - Source: [sandbox](https://code.claude.com/docs/en/sandboxing)
- Keys: `enabled, failIfUnavailable, autoAllowBashIfSandboxed` (default `true`), `excludedCommands, allowUnsandboxedCommands, enableWeakerNestedSandbox, enableWeakerNetworkIsolation, allowNestedUserNamespaces, bwrapPath, socatPath, ignoreViolations`, plus `filesystem.{allowWrite, denyWrite, denyRead, allowRead, disabled}`, `network.{allowedDomains, deniedDomains, strictAllowlist, allowManagedDomainsOnly, allowUnixSockets, allowAllUnixSockets, allowLocalBinding, httpProxyPort, socksProxyPort, tlsTerminate}` and `credentials.{files, envVars}` — [settings-ref](https://code.claude.com/docs/en/settings-reference)
- Example: `{"sandbox":{"enabled":true,"allowUnsandboxedCommands":false,"failIfUnavailable":true,"excludedCommands":["docker *"],"filesystem":{"allowWrite":["/tmp/build"],"denyRead":["~/.aws/credentials"]},"network":{"allowedDomains":["github.com","*.npmjs.org"]}}}`. Sandbox paths use plain conventions: `/abs`, `~/x`, and `.` relative to the settings file's directory — [sandbox](https://code.claude.com/docs/en/sandboxing)
- Merging: `Edit` allow rules grant write access, "`Read` and `Edit` deny rules: Block access", and `WebFetch(domain:…)` rules feed the domain lists. "Paths and domains from both … are merged into the final sandbox configuration" — [sandbox](https://code.claude.com/docs/en/sandboxing)
- Under auto-allow, deny rules are still respected and content-scoped ask rules still prompt. Monitor commands are not auto-approved. `allowUnsandboxedCommands:false` disables Claude's `dangerouslyDisableSandbox` retry — [sandbox](https://code.claude.com/docs/en/sandboxing)
- `excludedCommands` uses `Bash(...)` pattern syntax, and every command in the call must match. A call containing `cd`, a redirect, `$()`, `sudo`, `eval` or `xargs` stays sandboxed. Excluded commands run "with your full access" — [settings-ref](https://code.claude.com/docs/en/settings-reference)
- Network limits:
  - Tools that ignore the proxy variables (ssh, database drivers) can't connect.
  - UDP and QUIC can't leave the sandbox.
  - On Linux, `localhost` is private to the command, and `allowLocalBinding` has no effect there.
  - In auto mode, hosts outside the allowlist are refused unless the classifier approves them; `dontAsk` refuses them.
  - No TLS inspection is done by default.
  - Source: [sandbox](https://code.claude.com/docs/en/sandboxing)
- Subagents use the parent's sandbox configuration — [sandbox](https://code.claude.com/docs/en/sandboxing)

### Inferences
- Multi-node NCCL or Gloo over raw TCP, and reaching a local TensorBoard or MLflow server on Linux, will likely fail inside the sandbox. Run the launcher through `excludedCommands` or outside Claude.

### Gaps (Unverified)
- The sandbox docs say nothing about GPU, `/dev/nvidia*` or CUDA. Test `nvidia-smi` inside the sandbox before relying on it.

## Skills

### Takeaway
A skill is `.claude/skills/<name>/SKILL.md`. Every frontmatter field is optional; `description` is recommended. Custom slash commands were merged into skills in v2.1.3 (2026-01-09). Supporting files load only when needed.

### Cited Findings
- Locations: personal `~/.claude/skills/<n>/SKILL.md`, project `.claude/skills/<n>/SKILL.md`, nested `<subdir>/.claude/skills`, plugin `<plugin>/skills/<n>` (invoked as `/plugin:skill`), and enterprise. Skills reload when their files change — [skills](https://code.claude.com/docs/en/skills)
- Frontmatter:
  - Fields: `name, description, when_to_use, argument-hint, arguments, disable-model-invocation, user-invocable, allowed-tools, disallowed-tools, model, effort, context` (`fork`), `agent, background` (v2.1.218), `hooks, paths, shell, metadata, license, compatibility`.
  - Unknown fields are silently ignored.
  - `description` and `when_to_use` together are truncated at 1,536 characters in the listing.
  - `allowed-tools` grants clear when the user sends the next message.
  - Source: [skills](https://code.claude.com/docs/en/skills)
- Size and loading:
  - "Keep `SKILL.md` under 500 lines". Reference files load only when needed, and `scripts/` files are "executed, not loaded"; refer to them via `${CLAUDE_SKILL_DIR}`.
  - The skill listing's budget is 1% of the context window (`skillListingBudgetFraction`).
  - After compaction, skills are re-attached at 5,000 tokens each, 25,000 tokens in total.
  - Source: [skills](https://code.claude.com/docs/en/skills)
- Invocation:
  - Users type `/name args`; Claude invokes a skill automatically unless `disable-model-invocation: true`.
  - Arguments: `$ARGUMENTS`, `$0`/`$ARGUMENTS[N]`, or named via `arguments`.
  - `` !`cmd` `` injects command output into the skill, and a failure aborts the invocation.
  - `.claude/commands/x.md` still works (no `name`/`paths` fields).
  - Permission rules: `Skill(name)`.
  - Sources: [skills](https://code.claude.com/docs/en/skills); [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Frontmatter `hooks` stay registered for the rest of the session after the skill is invoked — [hooks](https://code.claude.com/docs/en/hooks)

### Gaps (Unverified)
- None material.

## Subagents

### Takeaway
A subagent is `.claude/agents/NAME.md`; only `name` and `description` are required. Subagents run in the background by default in interactive sessions. To make one read-only, use a `tools` allowlist.

### Cited Findings
- Priority, highest first: managed, `--agents` JSON (adds a `prompt` field), `.claude/agents/`, `~/.claude/agents/`, plugin `agents/` — [subagents](https://code.claude.com/docs/en/sub-agents)
- Frontmatter:
  - `name` (≤256 characters, no `:`), `description`
  - `tools`, `disallowedTools`
  - `model`: `sonnet|opus|haiku|fable|<full ID>|inherit`
  - `permissionMode`: `default|acceptEdits|auto|dontAsk|bypassPermissions|plan|manual`
  - `maxTurns`, `autoCompactWindow`, `skills`, `mcpServers`, `hooks`
  - `memory`: `user|project|local`
  - `background`, `omitClaudeMd`
  - `effort`: `low|medium|high|xhigh|max`
  - `isolation: worktree`
  - `color`: `red|blue|green|yellow|purple|orange|pink|cyan`
  - `initialPrompt`, `experimental.cacheTtl`
  - Source: [subagents](https://code.claude.com/docs/en/sub-agents)
- `permissionMode` is ignored when the parent session is in `bypassPermissions`, `acceptEdits` or `auto`. Plugin subagents ignore `permissionMode`, `hooks` and `mcpServers` — [subagents](https://code.claude.com/docs/en/sub-agents)
- Read-only example: `tools: Read, Grep, Glob, Bash` ("can't edit files, write files, or use any MCP tools"). Alternatively `disallowedTools: Write, Edit` — [subagents](https://code.claude.com/docs/en/sub-agents)
- Background subagents:
  - They are the default where fork mode is on (interactive sessions). `background: true` forces background; Ctrl+B backgrounds a running task.
  - Their permission prompts surface in the main session, they get a smaller built-in tool set, and their results arrive as a completion notification.
  - Nesting is allowed up to 3 levels (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`).
  - Source: [subagents](https://code.claude.com/docs/en/sub-agents)
- Memory directories: user `~/.claude/agent-memory/<agent>/`, project `.claude/agent-memory/<agent>/`, local `.claude/agent-memory-local/<agent>/` — [subagents](https://code.claude.com/docs/en/sub-agents)

### Inferences
- A truly read-only agent should also leave out `NotebookEdit` and restrict `Bash`, since Bash can write files.

### Gaps (Unverified)
- The exact reduced tool set for background subagents isn't listed.

## Plugins and marketplaces

### Takeaway
The manifest is `.claude-plugin/plugin.json`; only `name` is required. Components live under `skills/`, `agents/`, `commands/`, `hooks/hooks.json` and `.mcp.json`. Anthropic's official marketplace `claude-plugins-official` is added automatically.

### Cited Findings
- Default layout: `.claude-plugin/plugin.json, skills/<n>/SKILL.md, commands/, agents/, hooks/hooks.json, .mcp.json, .lsp.json, output-styles/, monitors/monitors.json, bin/` (on the Bash PATH while enabled), `settings.json` — [manifest](https://code.claude.com/docs/en/plugins/manifest-reference)
- plugin.json fields: `name, version, description, author{name,email,url}, homepage, repository, license, keywords, dependencies, userConfig, skills, commands, agents, hooks, mcpServers, lspServers, outputStyles`. Path variables: `${CLAUDE_PLUGIN_ROOT}` (changes on update), `${CLAUDE_PLUGIN_DATA}` (`~/.claude/plugins/data/<id>/`, persistent), `${CLAUDE_PROJECT_DIR}` — [manifest](https://code.claude.com/docs/en/plugins/manifest-reference)
- Commands:
  - In a session: `/plugin marketplace add owner/repo` and `/plugin install name@marketplace`. `/plugin` works only in interactive terminals.
  - Shell: `claude plugin install <plugin> -s user|project|local`, `claude plugin marketplace add <source> --scope …`, `claude plugin validate`.
  - Load for one session: `--plugin-dir ./p`. Reload with `/reload-plugins`.
  - Source: [plugins-cli](https://code.claude.com/docs/en/plugins/cli-reference)
- Marketplaces:
  - `claude-plugins-official` (repo `anthropics/claude-plugins-official`) is added on the first interactive session unless `CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL` is set or managed policy blocks it.
  - Community `claude-community` and demo `claude-code-plugins` (`anthropics/claude-code`) must be added manually.
  - Source: [marketplaces](https://code.claude.com/docs/en/plugins/anthropic-marketplaces)
- Settings keys: `"enabledPlugins":{"name@mkt":true}` and `"extraKnownMarketplaces":{"acme":{"source":{"source":"github","repo":"acme/plugins"}}}` — [settings-ref](https://code.claude.com/docs/en/settings-reference)

## MCP

### Takeaway
Project servers go in `.mcp.json` under `mcpServers`. `${VAR}` and `${VAR:-default}` expand in `command, args, env, url, headers`. Tool search, which defers MCP tool definitions, is on by default.

### Cited Findings
- `.mcp.json` example: `{"mcpServers":{"api":{"type":"http","url":"${API_BASE_URL:-https://api.example.com}/mcp","headers":{"Authorization":"Bearer ${API_KEY}"}},"db":{"command":"/path/server","args":["--config","cfg.json"],"env":{"DB_URL":"${DB_URL}"}}}}`. Optional per-server fields: `"timeout"` in ms (overrides `MCP_TOOL_TIMEOUT`) and `alwaysLoad` — [mcp](https://code.claude.com/docs/en/mcp)
- CLI:
  - `claude mcp add --transport http <name> <url> --header "Authorization: Bearer …"`
  - `claude mcp add --env K=V --transport stdio <name> -- <cmd> [args]`
  - `-s/--scope local|project|user` (default `local`)
  - Also: `add-json`, `list`, `get`, `remove`, `reset-project-choices`. The `sse` transport is deprecated.
  - Source: [mcp](https://code.claude.com/docs/en/mcp)
- Approval. Interactive sessions prompt before connecting `.mcp.json` servers. "In `claude -p` runs … it loads project-scoped servers without asking"; block a server with `disabledMcpjsonServers`. Scope precedence: local > project > user > plugin > connectors — [mcp](https://code.claude.com/docs/en/mcp)
- Output limits. A warning appears above 10,000 tokens, and the default cap is 25,000 (`MAX_MCP_OUTPUT_TOKENS`). A tool can declare `_meta["anthropic/maxResultSizeChars"]` up to 500,000 characters — [mcp](https://code.claude.com/docs/en/mcp)
- Tool search: `ENABLE_TOOL_SEARCH` = `true|auto|auto:N|false` — [mcp](https://code.claude.com/docs/en/mcp)

## Long-running work: background jobs, Monitor, loops, headless mode, compaction, memory, checkpoints, worktrees, status line

### Takeaway
The building blocks for long runs are background Bash, the Monitor tool, `/loop` with the Cron tools, `/goal`, `-p` mode and worktrees. In unattended runs, background commands are capped at 30 minutes by default and 2 hours at most unless raised.

### Cited Findings
- Background Bash:
  - Claude sets `run_in_background: true` on a Bash call; list and stop tasks with `/tasks`. Output goes to a file, and Claude reads it with `Read` (`TaskOutput` is deprecated).
  - Foreground timeout defaults: 2 minutes (`BASH_DEFAULT_TIMEOUT_MS`), maximum 10 minutes (`BASH_MAX_TIMEOUT_MS`). A command that hits its timeout moves to the background.
  - Unattended sessions (v2.1.285): a background command gets 30 minutes, at most 2 hours, raised via those two variables. Local interactive sessions have no limit.
  - Output inline limit is about 30,000 characters (`BASH_MAX_OUTPUT_LENGTH` up to 150,000).
  - `CLAUDE_CODE_TOOL_MEMORY_LIMIT` places one cgroup cap over all commands combined.
  - Source: [tools](https://code.claude.com/docs/en/tools-reference)
- Monitor tool (v2.1.98, 2026-04-09). Input: `{description, timeout_ms, command?, ws?}`. Each output line becomes an event for Claude. A watch lasts 5 minutes by default, 30 minutes at most, and 10 minutes at most in single-prompt `-p` runs. It follows Bash permission rules — [tools](https://code.claude.com/docs/en/tools-reference); [sdk-ts](https://code.claude.com/docs/en/agent-sdk/typescript)
- `/loop` (v2.1.71, 2026-03-07):
  - `/loop 5m <prompt>` runs on a fixed schedule; without an interval Claude self-paces via `ScheduleWakeup` (`delaySeconds, reason, prompt, noop, stop`), between 1 minute and 1 hour.
  - Tools: `CronCreate{cron, prompt, recurring?, durable?}`, `CronList`, `CronDelete`.
  - Limits: 50 tasks per session; recurring tasks expire after 7 days; tasks fire only while the session is open and idle.
  - A default prompt can live in `.claude/loop.md`. Disable everything with `CLAUDE_CODE_DISABLE_CRON=1`.
  - Durable alternatives: Routines (cloud, minimum interval 1 hour) and Desktop scheduled tasks.
  - Sources: [sched](https://code.claude.com/docs/en/scheduled-tasks); [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- `/goal <condition>` (v2.1.139, 2026-05-11): conditions up to 4,000 characters; works in interactive mode, `-p` and Remote Control — [goal](https://code.claude.com/docs/en/goal); [changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)
- Headless flags:
  - `claude -p "…" --output-format text|json|stream-json` (stream-json is shown with `--verbose` in the docs)
  - Limits: `--max-turns N`, `--max-budget-usd`
  - Sessions: `--resume <id|name>`, `--continue`, `--fork-session`
  - Permissions: `--permission-mode`, `--allowedTools "Bash(git diff *),Read"`, `--disallowedTools`, `--permission-prompts none`
  - Startup: `--bare` (skips hooks, skills, MCP and CLAUDE.md), `--settings`, `--mcp-config --strict-mcp-config`, `--json-schema`
  - In the JSON result, `subtype` is one of `success|error_max_turns|error_during_execution|error_max_budget_usd|error_max_structured_output_retries`.
  - After its last turn, `-p` waits for background work, with a 10-minute idle ceiling (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`).
  - Sources: [cli](https://code.claude.com/docs/en/cli-reference); [headless](https://code.claude.com/docs/en/headless); [sdk-ts](https://code.claude.com/docs/en/agent-sdk/typescript)
- Compaction:
  - Set the window with `/autocompact 500k`, `autoCompactWindow`, `--autocompact` or `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (100K–1M tokens).
  - Survive compaction: the project-root CLAUDE.md and auto memory are re-injected, and SessionStart hooks with the `compact` matcher run.
  - Summarized away: earlier hook context and anything said only in conversation.
  - Sources: [model-config](https://code.claude.com/docs/en/model-config); [ctx](https://code.claude.com/docs/en/context-window)
- Memory:
  - `@path` imports resolve relative to the importing file, nest at most 4 hops deep, and are not expanded inside code spans.
  - Auto memory lives at `~/.claude/projects/<project>/memory/MEMORY.md`. The first 200 lines or 25KB load at start; disable with `autoMemoryEnabled:false` or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
  - Source: [memory](https://code.claude.com/docs/en/memory)
- Checkpoints: open with `/rewind` or Esc Esc. Changes made by Bash and edits made by subagents are not restored — [checkpointing](https://code.claude.com/docs/en/checkpointing)
- Worktrees (v2.1.49):
  - `claude -w <name>` creates `.claude/worktrees/<name>` on branch `worktree-<name>`.
  - Related: the `EnterWorktree`/`ExitWorktree` tools, `.worktreeinclude`, and `worktree.baseRef` (`fresh|head`).
  - Claude Code blocks edits and git commands that target the main checkout.
  - Source: [worktrees](https://code.claude.com/docs/en/worktrees)
- Status line: `"statusLine":{"type":"command","command":"~/.claude/statusline.sh","padding":2,"refreshInterval":5}`.
  - Stdin fields: `model.{id,display_name}, workspace.{current_dir,project_dir}, cost.total_cost_usd, context_window.used_percentage, rate_limits.five_hour.used_percentage, effort.level, session_id`, among others.
  - Updates are debounced at 300ms.
  - Source: [statusline](https://code.claude.com/docs/en/statusline)

### Inferences
- Launch multi-hour training outside Claude (tmux, systemd, Slurm) and observe it through Monitor, a Stop hook that reads `background_tasks`, or `asyncRewake` hooks.

### Gaps (Unverified)
- There is no documented way to make Claude-launched background jobs survive the end of a `-p` run. On SIGTERM, Claude Code kills the Bash process trees it started.

## New in 2026 that matters for autonomous experiment loops

### Takeaway
Since January 2026 Claude Code has added auto mode as the default for interactive sessions, agent teams, background agents, effort levels, Remote Control and cloud sessions.

### Cited Findings
- Agent teams (v2.1.32, 2026-02-05): enable with `"env":{"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS":"1"}`; interactive sessions only — [teams](https://code.claude.com/docs/en/agent-teams)
- Effort levels `low|medium|high|xhigh|max` via `--effort` or `/effort`. The Opus 5.5 default is `medium`. `ultrathink` in a prompt requests deeper reasoning for that one turn — [model-config](https://code.claude.com/docs/en/model-config)
- Background agents: `claude --bg "…"`, `claude agents`, `attach`, `logs`, `stop`, `respawn`. Remote Control: `claude remote-control` or `--rc`. Cloud: `--cloud`, `--teleport`. Cloud sessions ignore `defaultMode` `bypassPermissions` and `dontAsk` — [cli](https://code.claude.com/docs/en/cli-reference); [modes](https://code.claude.com/docs/en/permission-modes)
