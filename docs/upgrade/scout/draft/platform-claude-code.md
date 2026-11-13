# Platform scout: Claude Code

Area: Claude Code capabilities the kit depends on or could use.
Written 2026-11-11 (task date 2026-11-10). Installed here: Claude Code 2.1.303 (`claude --version`, run 2026-11-10). Newest release: 2.1.322 (2026-11-10).

## Summary (10 lines)

1. Newest Claude Code is 2.1.322 (2026-11-10). This machine runs 2.1.303 (2026-10-18), 16 releases behind; the 23 October notes stop at 2.1.308, 11 releases behind.
2. Fixes that matter to a guard landed after 2.1.303: Windows hooks failing open (2.1.309, 2.1.310, 2.1.316), Bash rule misses and an environment-prefix bypass (2.1.319), a `cp`/`mv` deny gap and a lost hook "ask" (2.1.321). The kit needs a version floor and a check.
3. The PreToolUse contract keeps its shape: stdin JSON with `permission_mode` (`default`, `plan`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`), output `permissionDecision` (`allow`, `deny`, `ask`, `defer`), exit code 2 blocks, and `onFailure: "block"` needs 2.1.295 or later.
4. The docs now recommend exec-form hooks (`command` plus `args`, no shell). The kit's shell-form `python3 "${CLAUDE_PROJECT_DIR:-.}/..."` depends on Git Bash on Windows and is not valid under PowerShell.
5. `claude -p` in a never-trusted folder runs project hooks and connects `.mcp.json` servers without asking, but ignores project `permissions.allow` rules and project-subagent frontmatter hooks. An unattended launcher must pass its own rules and cannot rely on the read-only subagent hook.
6. Narrowest unattended setup found: `--permission-mode dontAsk` with an explicit allowlist, `--permission-prompts none`, `--strict-mcp-config`, and never `--bare` (it disables hooks and is announced as the future default for `-p`).
7. The caps are soft: `--max-budget-usd` is a client-side estimate that spend can pass; background commands in a `-p` run stop after 10 minutes by default (2 hours maximum). Harness code must own the budget and must launch training detached.
8. The sandbox covers shell commands only and exists on macOS, Linux and WSL2. Native Windows runs unsandboxed. GPU access inside the sandbox is not documented.
9. A hook guard is not a boundary: scripts that open files themselves, `@`-mentions, tools outside the matcher and in-process plugin code ("mods") pass it. Without managed settings or a Team or Enterprise login, a mod can approve a call the guard blocked.
10. Packaging the kit as a plugin would lose permission rules, the status line, the CLAUDE.md block and subagent hooks, so `install.py` stays the main path. Not done: the web search budget for this run was used up, so the six query families were not run (see Open questions).

## How to read the citations

- `docs/<page>` means `https://code.claude.com/docs/en/<page>`. Every docs page was fetched on 2026-11-10 (hooks) or 2026-11-11 (all others) and describes the documentation live on that date, when the newest release was 2.1.322. A version inside a claim is the minimum version the docs or changelog state for it.
- `CHANGELOG` = https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md (fetched 2026-11-10, entries 2.1.302 to 2.1.322).
- `RELEASES` = https://github.com/anthropics/claude-code/releases (GitHub API, checked 2026-11-11).
- `ADVISORIES` = https://github.com/anthropics/claude-code/security/advisories (fetched 2026-11-11, page 1 of 4, four advisories opened).
- `LOCAL` = `claude --version`, `claude --help`, `claude <subcommand> --help` on this machine, version 2.1.303, run 2026-11-10 and 2026-11-11.
- `C7` after a docs page means I read it as a Context7 snippet of that page (library `/websites/code_claude`), not the whole page.
- Status: **V** Verified (read in the source on that date), **I** Inferred (my reasoning from verified facts, not tested), **U** Unverified (not found or not checked).
- Nothing here was tested by running Claude Code. The allowed local commands were help and version only.

## Q1. Hooks

### Events and handlers

- 33 events: SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse, PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure, PostToolBatch, Notification, MessageDisplay, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, InstructionsLoaded, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, PreModelSwitch, PostModelSwitch, Elicitation, ElicitationResult, SessionEnd. [docs/hooks; V]
- Handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`. Plugins can also ship in-process JavaScript hooks called mods. [docs/hooks, docs/plugins/mods/overview; V]
- PreToolUse fires on every tool call except `EndConversation`. Hooks from settings, managed policy and plugins also run inside subagents, and the input then carries `agent_id` and `agent_type`. [docs/hooks; V]
- SessionStart matchers: `startup`, `resume`, `clear`, `compact`, `fork`. Only `command` and `mcp_tool` handlers. Output keys: `additionalContext`, `initialUserMessage` (`-p` only), `sessionTitle`, `watchPaths`, `reloadSkills`. `CLAUDE_ENV_FILE` is not available to a hook that runs in PowerShell. [docs/hooks; V]
- ConfigChange hooks can block a changed settings file from applying mid-session (not policy settings). [docs/hooks; V]
- StopFailure `error` values: `rate_limit`, `overloaded`, `authentication_failed`, `oauth_org_not_allowed`, `account_on_hold`, `billing_error`, `invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`, `cloud_credential_error`, `unknown`. [docs/hooks; V]

### What a PreToolUse hook receives

- Common fields: `session_id`, `prompt_id`, `transcript_path`, `cwd`, `scratchpad_dir` (2.1.257+), `permission_mode`, `effort.level`, `hook_event_name`; inside agents `agent_id`, `agent_type`. PreToolUse adds `tool_name`, `tool_input`, `tool_use_id`, and for MCP tools `mcp_server` with `name` and `source` (2.1.274+). [docs/hooks; V]
- `permission_mode` values: `"default"`, `"plan"`, `"acceptEdits"`, `"auto"`, `"dontAsk"`, `"bypassPermissions"`. The mode the interface labels Manual arrives as `"default"`, never as `"manual"`. [docs/hooks; V]
- On Windows `tool_input.file_path` arrives with backslashes, also under Git Bash. [docs/hooks; V]

Verbatim from https://code.claude.com/docs/en/hooks, fetched 2026-11-10. PreToolUse stdin for a Bash call:

```json
{
  "session_id": "abc123",
  "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/my-project",
  "scratchpad_dir": "/tmp/claude-1000/-home-user-my-project/abc123/scratchpad",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test",
    "description": "Run test suite",
    "timeout": 120000,
    "run_in_background": false
  },
  "tool_use_id": "toolu_01ABC123..."
}
```

### What a PreToolUse hook may return

- `hookSpecificOutput.permissionDecision`: `allow`, `deny`, `ask`, `defer`. Across several hooks the precedence is deny, then defer, then ask, then allow. Deny and ask rules in settings are still evaluated after a hook returns allow. [docs/hooks; V]
- `permissionDecisionReason`: shown to the user for `ask`; in a `-p` run where nobody can answer, Claude Code denies the call and Claude reads the reason in the tool result. [docs/hooks; V]
- `updatedInput` replaces the whole tool input. `additionalContext` is capped at 10,000 characters. [docs/hooks; V]
- `defer` works only in `-p` and only when the turn has a single tool call; the run ends with `stop_reason: "tool_deferred"` and can be resumed. [docs/hooks; V]

Verbatim from https://code.claude.com/docs/en/hooks, fetched 2026-11-10. Full output form:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "My reason here",
    "updatedInput": {
      "field_to_modify": "new value"
    },
    "additionalContext": "Current environment: production. Proceed with caution."
  }
}
```

Deny form:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook"
  }
}
```

Headless result when a hook defers (same page, same date):

```json
{
  "type": "result",
  "subtype": "success",
  "stop_reason": "tool_deferred",
  "session_id": "abc123",
  "deferred_tool_use": {
    "id": "toolu_01abc",
    "name": "AskUserQuestion",
    "input": { "questions": [{ "question": "Which framework?", "header": "Framework", "options": [{"label": "React", "description": "Component library"}, {"label": "Vue", "description": "Progressive framework"}], "multiSelect": false }] }
  }
}
```

### Exit codes, onFailure, timeouts

- Exit 0: success; stdout is parsed as JSON only when it is exactly one JSON object. Exit 2: blocking error, stderr is the reason. Any other code: non-blocking error, and the action proceeds unless `onFailure` is `"block"`. [docs/hooks; V]
- A hook that exits 2 stops the tool call before permission rules are evaluated. [docs/permissions; V]
- `onFailure`: `"continue"` or `"block"`, for command and HTTP hooks. "Requires Claude Code v2.1.295 or later." Introduced in 2.1.295 (2026-10-08). With `block`, these count as failures: cannot start, exit code other than 0 or 2, HTTP error, timeout, invalid JSON output. No effect on Stop, SubagentStop, TaskCompleted, TeammateIdle or async hooks. Agent SDK callbacks got it in 2.1.317. [docs/hooks, RELEASES, CHANGELOG; V]
- What versions before 2.1.295 do with the key: not documented. The settings docs say an invalid individual entry is skipped with a warning and a file whose top-level shape fails validation is rejected as a whole, and `claude --help` says invalid settings files are silently ignored in `-p`. Either way an older version gives no fail-closed behaviour. [docs/settings C7, LOCAL; U for the exact behaviour, I for the consequence]
- Timeouts in seconds: 600 by default for `command`, `http` and `mcp_tool`; 30 for `prompt`; 60 for `agent`; 30 on UserPromptSubmit and the model-switch events; 10 on MessageDisplay; SessionEnd hooks share 1.5 seconds. A timed-out PreToolUse command hook does not block unless `onFailure` is `"block"`. [docs/hooks; V]
- Async hooks are killed when a `-p` run tears down. [docs/hooks; V]

Verbatim `onFailure` example from https://code.claude.com/docs/en/hooks, fetched 2026-11-10 (it is also the exec form):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "node",
            "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/check-command.js"],
            "onFailure": "block"
          }
        ]
      }
    ]
  }
}
```

### How hook commands run on native Windows

- Exec form runs when `args` is present: Claude Code resolves `command` as an executable on `PATH` and spawns it directly, with no shell tokenization on any platform. On Windows `command` must resolve to a real executable such as a `.exe`; `.cmd` and `.bat` shims cannot be spawned. The docs say to prefer exec form for any hook that references a path placeholder. [docs/hooks; V]
- Shell form (no `args`): `sh -c` on macOS and Linux; Git Bash on Windows; PowerShell when Git Bash is not installed. The `shell` field accepts `"bash"` or `"powershell"`. [docs/hooks; V]
- In PowerShell shell form `${CLAUDE_PROJECT_DIR}` is rewritten to the PowerShell environment form. The kit's `${CLAUDE_PROJECT_DIR:-.}` default expansion is bash-only, so the kit's command string is not valid there. [docs/hooks for the rewrite, V; the kit consequence, I]
- "On Windows without Git Bash, a shell-form PreToolUse or PermissionRequest command hook that fails with onFailure unset can instead block the tool call." [docs/hooks; V]
- On Windows without Git Bash, Claude Code does not register the Bash tool at all, so a hook that matches only `Bash` never fires; the PowerShell tool is used. Monitor is available on Windows only with Git Bash. [docs/hooks, docs/tools-reference; V]
- Matchers: a string of letters, digits, `_`, `-`, spaces, `,` and `|` means exact tool names; anything else is an unanchored regular expression. A `Bash` matcher also runs on Monitor shell commands from 2.1.314 (it can block or ask, not approve or rewrite). [docs/hooks, CHANGELOG; V]
- Calling Python portably: write exec form with an interpreter the installer has resolved to a real executable (for example the absolute path of the interpreter that runs `install.py`), and pass the script path in `args`. `python3` is usually absent on Windows, and the Microsoft Store `python.exe` is an app alias, not a normal executable. [I; not tested. The release that introduced exec form was not found, U. The hooks page describes a 2.1.207 change to shell-form plugin hooks next to exec form, so exec form is very likely present at a 2.1.295 floor, I]
- The kit's two subagent files hard-code `python3` in their frontmatter hook and `install.py` does not rewrite it, so on Windows that hook cannot start. It has no `onFailure`, so it fails open. [repository files read 2026-11-10; V for the files, I for the effect]

### Trust and where hooks run

- In a `-p` or SDK session Claude Code never shows the trust dialog and treats the folder as trusted for settings hooks, so hooks committed in `.claude/settings.json` run in a folder nobody trusted. [docs/hooks, docs/permissions; V]
- Frontmatter hooks in a project subagent run only after the trust dialog was accepted; a `-p` session does not count. Hooks from `~/.claude/agents/` and from `--agents` definitions run without the trust step. [docs/hooks, docs/sub-agents; V]
- PermissionRequest hooks still run in sessions that cannot prompt; with no decision the call is denied. [docs/hooks; V]

## Q2. Headless and unattended use

### Flags

- `-p/--print`; `--output-format text|json|stream-json`; `--include-hook-events`; `--json-schema`; `--max-budget-usd`; `--max-turns`; `--permission-mode`; `--permission-prompts host|none`; `--permission-prompt-tool`; `--allowedTools`; `--disallowedTools`; `--tools`; `--settings`; `--setting-sources`; `--mcp-config`; `--strict-mcp-config`; `--bare`; `--safe-mode`; `--restricted`; `--session-id`; `--no-session-persistence`; `--fallback-model`; `--effort low|medium|high|xhigh|max`; `--agents`; `--plugin-dir`. [LOCAL for all except `--max-turns` and `--permission-prompt-tool`, docs/cli-reference for all; V]
- `--max-turns`: "Limit the number of agentic turns (print mode only). No limit by default." It is not listed by `claude --help` on 2.1.303 but is in the CLI reference. [docs/cli-reference, LOCAL; V]
- `--max-budget-usd`: stops the run once estimated spend reaches the amount (print mode only). It is checked against a client-side estimate, subagent spend counts, "Spend can pass the cap, so leave headroom", totals restored by `--continue` or `--resume` do not count, and reaching it stops remaining background work. Needs 2.1.217+. [docs/cli-reference, docs/headless; V]
- `--permission-mode` accepts `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`, and `manual` as an alias (2.1.200+). [docs/cli-reference, LOCAL; V]
- `--permission-prompts none` (2.1.259+): anything that would prompt is denied unless a PermissionRequest hook allows it, Claude is told that nobody can approve and not to retry, the run continues, and tools that need a person (such as AskUserQuestion) are removed. [docs/cli-reference; V]
- `permissions.denyInsteadOfPrompting` setting added in 2.1.319. Only the changelog line was read. [CHANGELOG; V that it exists, U for exact semantics]
- `--settings`: a file or inline JSON, overrides the same keys in settings files, file at most 2 MiB. `--setting-sources user,project,local` selects which files load. `--strict-mcp-config` uses only servers from `--mcp-config`. [docs/cli-reference; V]
- `--bare`: skips hooks, skills, custom commands, subagents, installed plugins, MCP servers, auto memory and CLAUDE.md. Hooks do not run in bare mode even when passed with `--settings`. "`--bare` is the recommended mode for scripted and SDK calls, and will become the default for `-p` in a future release." No date given. [docs/headless; V]
- `--safe-mode`: disables hooks and all customizations; permissions work normally. [docs/cli-reference; V]
- `--restricted` (2.1.248+): removes command-running tools and WebFetch unless named in `--tools`, loads only managed settings and `--settings`, confines file tools to the working directories, refuses bypassPermissions. [docs/cli-reference; V]
- `--fallback-model sonnet,haiku` (at most 3) triggers on overload or unavailability, "not auth, billing, or rate-limit errors". [docs/cli-reference; V]

### What each mode does when nobody can answer

- From 2.1.302, `claude -p` and Agent SDK runs with no permission mode set start in Manual (`default`) mode. Before that they could start in auto mode when feature flags were not fetched. [docs/permission-modes, CHANGELOG; V]
- Manual or acceptEdits in `-p`: "a call that needs approval is denied unless something approves it". A hook `ask` is therefore a denial, and Claude reads the hook's reason. [docs/permission-modes, docs/hooks; V]
- dontAsk: file reads inside the working directories and pre-approved tools run; anything that would prompt is denied. Protected-path writes are denied. Mods written by Claude do not load. [docs/permission-modes, CHANGELOG 2.1.321; V]
- auto: a classifier (default model Sonnet 5, `CLAUDE_CODE_AUTO_MODE_MODEL` from 2.1.302) checks calls. In `-p`, "When repeated blocks reach a threshold, the action doesn't run and Claude keeps working. Claude Code doesn't stop the run." It blocks by default, among others, download-and-execute, sending sensitive data out, force push, mass deletion and launching an autonomous agent loop. From 2.1.319 a `-p` run in auto mode exits 1 when no safety check is available. [docs/permission-modes, CHANGELOG; V]
- bypassPermissions: everything runs; allow rules have no effect; deny rules still block; documented for "Isolated containers and VMs only"; refused under root or sudo on Linux and macOS outside a recognised sandbox; removal of critical paths is still denied in `-p` unless a PermissionRequest hook allows it. [docs/permission-modes; V]
- With `--output-format stream-json`, denials appear as `permission_denied` system messages and the final result lists them in `permission_denials`. [docs/headless; V]

### Output and result fields

- `json` gives one result object; `stream-json` gives events and a final result. [docs/headless; V]
- Result fields: `subtype` (`success`, `error_during_execution`, `error_max_turns`, `error_max_budget_usd`, `error_max_structured_output_retries`), `is_error`, `num_turns`, `duration_ms`, `duration_api_ms`, `session_id`, `stop_reason`, `terminal_reason` (such as `completed`, `max_turns`, `api_error`, `aborted_streaming`, `aborted_tools`), `api_error_status`, `total_cost_usd`, `usage`, `modelUsage`, `result`, `structured_output`, `permission_denials`, `deferred_tool_use`, `errors`, `credential_expires_at` (2.1.318). [docs/agent-sdk/python C7, docs/headless, CHANGELOG; V. The list comes from the SDK type; I did not print a real `-p` result]
- `is_error` can be true on `subtype: "success"`: with `stop_reason: "refusal"` (the model declined; text in `result`), with `"tool_deferred_unavailable"`, or when the turn ended on an API error (read `terminal_reason`, `result`, `api_error_status`). [docs/agent-sdk/python C7; V]
- `usage` covers only the main loop; `modelUsage` and `total_cost_usd` include subagents. On `error_max_budget_usd`, `usage` leaves out the response that crossed the budget. Costs are client-side estimates. [docs/agent-sdk/cost-tracking C7; V]
- Stream events: `system/init` (model, tools, `mcp_servers`, `plugins`, `plugin_errors`, `mcp_server_errors`, `capabilities`), `system/api_retry` (`attempt`, `max_retries`, `retry_delay_ms`, `error_status`, `error`), `hook_started`, `hook_progress`, `hook_response` (with `--include-hook-events`), `rate_limit_event`. [docs/headless, CHANGELOG 2.1.295; V for the names, U for the `rate_limit_event` schema]

### Exit codes

- "Claude Code exits with code 0 on success and a non-zero code when the run fails". SIGTERM gives 143; on SIGTERM Claude Code terminates the process tree of any running Bash command, then runs SessionEnd hooks. [docs/headless; V]
- Exit 1 cases added recently: startup failure (2.1.314), transcript loss on a full disk (2.1.317), auto mode with no safety check (2.1.319). 2.1.321 fixed a Linux case that exited 0 after a storage quota loss. [CHANGELOG; V]
- Which exit code a max-turns or budget stop gives was not found. Read `subtype` instead. [U]

### Rate limits, usage caps, refusals

- Transient API failures are retried up to 10 times with exponential backoff (`CLAUDE_CODE_MAX_RETRIES`, capped at 15). `CLAUDE_CODE_RETRY_WATCHDOG=1` retries 429 and 529 errors indefinitely for unattended sessions; `CLAUDE_CODE_RETRY_WATCHDOG_MAX_WAIT_MS` (2.1.295+) bounds the wait per request; `CLAUDE_CODE_RETRY_WATCHDOG_MAX_USAGE_LIMIT_WAIT_MS` (2.1.301+) bounds the wait for a plan usage limit to reset. A 429 that reports a spend limit or exhausted credits fails at once. [docs/errors, first 100,000 characters; V]
- Usage-cap messages: "You've hit your session limit", "You've hit your weekly limit". Whether a plain `-p` run waits or exits at a cap, and with which result fields, was not in the part read. [docs/errors; V for the text, U for the behaviour]
- Refusal: a flagged request in `-p` with `switchModelsOnFlag` false "ends the turn with a refusal"; a subagent fails with `Agent terminated early due to an API error`. `CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK=1` exists (2.1.312). [docs/model-config, CHANGELOG; V]
- The status line input carries `rate_limits.five_hour` and `rate_limits.seven_day` with `used_percentage` and `resets_at` for Pro, Max and Ultra subscribers, after the first API response. Interactive sessions only. [docs/statusline; V]

### Background work and time limits

- After the last turn a `-p` run waits for background work and stops what is still running "after 10 minutes of continuous idle waiting by default" (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`, 0 means no cap). [docs/headless; V]
- In unattended sessions (2.1.285+), a background Bash or PowerShell command gets 30 minutes, or the `timeout` Claude passes, up to 2 hours. In a `-p` run with a text prompt both defaults are 10 minutes. `BASH_DEFAULT_TIMEOUT_MS` and `BASH_MAX_TIMEOUT_MS` raise them. A foreground command that reaches its timeout is moved to the background, except in bare mode or with `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`. [docs/tools-reference; V]
- Foreground Bash timeout: 2 minutes by default, 10 minutes ceiling. A command whose output passes 5 GB is killed. [docs/tools-reference; V]
- Consequence: a training run started as a Claude Code background command dies with the limit or with SIGTERM. Training must be detached by the harness, as `expctl` does today. [I]

### Isolation and transcripts

- Without `--bare`, a `-p` session runs the hooks in the project's `.claude/settings.json` and connects the servers in its `.mcp.json`, even in a folder nobody trusted. [docs/headless; V]
- Transcripts: `~/.claude/projects/<project>/<session-id>.jsonl`, where `<project>` is the working directory path with non-alphanumeric characters replaced by `-`. "The entry format is internal to Claude Code and changes between versions, so scripts that parse these files directly can break on any release." Kept 30 days (`cleanupPeriodDays`). `--no-session-persistence` turns saving off. [docs/sessions; V]
- `claude -p --resume` starts in the mode a new `-p` run would start in; `--mcp-config`, `--settings`, `--plugin-dir`, `--fallback-model` and `--add-dir` must be passed again; background commands are not restored. [docs/sessions; V]

## Q3. Permission rules and sandboxing

### Rule syntax and its limits

- Bash rules match the whole command text with `*` for any text. Claude Code splits on `&&`, `||`, `;`, `|`, `|&`, `&` and newlines, and every subcommand must be allowed; deny and ask rules apply to any subcommand, also in subshells and loops. Wrappers stripped before matching: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, `command`, `builtin`, `noglob`, bare `xargs`. Not stripped: `direnv exec`, `devbox run`, `mise exec`, `npx`, `docker exec`. [docs/permissions; V]
- "a deny or ask rule covers the invocation Claude usually produces and isn't a security boundary around the program." Example from the docs: `Bash(git push *)` does not stop `git -C . push origin main`. The kit's ask rule for `git push` has this gap. [docs/permissions; V]
- A fixed read-only command set (`ls`, `cat`, `head`, `tail`, `grep`, `find`, `wc`, `diff`, `stat`, read-only `git` and similar) runs without a prompt in every mode. Commands over 10,000 characters always prompt. [docs/permissions; V]
- PowerShell rules have the same shape, are case-insensitive, and aliases are canonicalised. [docs/permissions; V]
- Read and Edit path anchors: `//path` absolute, `~/path` home, `/path` relative to the settings source, `path` or `./path` relative to the working directory. On Windows paths are normalised to POSIX form first (`C:\Users\alice` becomes `/c/Users/alice`). `Write(...)`, `Glob(...)` and `Grep(...)` path rules do not match; use `Edit` and `Read`. [docs/permissions; V]
- Read and Edit deny rules cover the built-in file tools, file commands Claude Code recognises in Bash (`cat`, `head`, `tail`, `sed`, `tee`) and redirect targets. "They don't apply to ... arbitrary subprocesses that read or write files indirectly, like a Python or Node script that opens files itself." [docs/permissions; V]
- MCP rules: `mcp__<server>`, `mcp__<server>__*`, `mcp__<server>__<tool>`. Agent rules: `Agent(<name>)`. [docs/permissions; V]
- `permissions.blockReadsOutsideWorkingDirectories` (2.1.257+) and `permissions.blockWritesOutsideWorkingDirectories` (2.1.314+) make the file tools refuse outside paths in every mode; the write key "doesn't limit shell commands, MCP tools, or the programs hooks run". [docs/permissions; V]
- `"auto"` or `"bypassPermissions"` as `defaultMode` in project or local settings does not take effect. [docs/permission-modes; V]
- Settings precedence, highest first: managed policy, `--settings`, `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json`. Lists such as `permissions.allow` merge across files. [docs/settings C7; V]

### What an untrusted folder gets in `claude -p`

- Used: settings hooks, `env`, helpers, project-skill hooks and skill `allowed-tools`. Not used: `permissions.allow` rules and `additionalDirectories` from `.claude/settings.json` (a "this workspace has not been trusted" warning goes to stderr), project-subagent frontmatter hooks, project `extraKnownMarketplaces`. `.mcp.json` servers are "Connected without asking, approved or not". Deny and ask rules always apply. [docs/permissions; V]
- Trust is recorded as `projects["<path>"].hasTrustDialogAccepted` in `~/.claude.json`. [docs/permissions; V]
- Consequence for the kit: its `expctl` allow rules silently drop out of an unattended run in a folder that was never opened interactively, and the read-only subagent hook does not run. [I]

### Protected paths

- Directories: `.git`, `.config/git`, `.vscode`, `.idea`, `.husky`, `.cargo`, `.devcontainer`, `.yarn`, `.mvn`, `.claude` (with exceptions such as `.claude/worktrees/`), a `--plugin-dir` directory, `~/.claude/dev-mods/`. Files include `.gitconfig`, `.gitmodules`, shell rc files, `.envrc`, `.npmrc`, `.pre-commit-config.yaml`, `pyrightconfig.json`, `.ripgreprc`, `.mcp.json`, `.claude.json`, and files passed to `--settings`, `--mcp-config`, `--agents`. [docs/permission-modes; V]
- Writes there prompt in default and acceptEdits, go to the classifier in auto, are denied in dontAsk and allowed in bypassPermissions. Allow rules in settings do not pre-approve them. [docs/permission-modes; V]
- This protection is on Claude Code's file tools and recognised shell commands. A script can still write `.claude/settings.json`, and settings hot-reload; a ConfigChange hook is the documented way to refuse such a change. [docs/permissions and docs/hooks, V; the combination, I]

### Sandbox

- "The sandbox runs on macOS, Linux, and WSL2. On native Windows, Claude Code runs commands unsandboxed." Linux and WSL2 need `bubblewrap` and `socat`. WSL1 is unsupported. [docs/sandboxing; V]
- Scope: Bash, PowerShell and Monitor commands and the processes they start. Claude's file tools, MCP servers, hooks, the status line command and mods run outside it. [docs/sandboxing; V]
- Defaults: writes to the working directory, a per-user temp directory and added directories; protected paths stay write-denied; reads are allowed on most of the machine, "including credential files such as ~/.ssh". Network goes through a proxy whose allowed domains start empty; a new domain is refused in dontAsk, prompts in Manual and acceptEdits, and is allowed in bypassPermissions. [docs/sandboxing; V]
- Per-project settings: `sandbox.enabled`, `sandbox.filesystem.allowWrite|denyWrite|denyRead|allowRead`, `sandbox.network.allowedDomains|deniedDomains|allowLocalBinding|allowUnixSockets`, `autoAllowBashIfSandboxed` (default true), `allowUnsandboxedCommands`, `excludedCommands`, `failIfUnavailable`, `enableWeakerNestedSandbox`, `allowNestedUserNamespaces` (2.1.305+). Sandbox paths use ordinary conventions, unlike permission-rule paths. [docs/sandboxing; V]
- "By default, when the platform doesn't support the sandbox ... Claude Code runs commands without sandboxing"; `sandbox.failIfUnavailable` changes that. [docs/sandboxing; V]
- `excludedCommands` run with no restriction and "Exclusion is a convenience, not a security boundary". `docker` is incompatible with the sandbox. [docs/sandboxing, docs/settings-reference C7; V]
- Ubuntu's AppArmor restriction on unprivileged user namespaces can stop bubblewrap (relevant to Ubuntu 24.04); a startup check exists from 2.1.310. [docs/sandboxing, CHANGELOG; V]
- "Sandboxing reduces risk but is not a complete isolation boundary." Domain fronting is possible. [docs/sandboxing; V]
- GPU, CUDA and device access inside the sandbox: not mentioned on the sandboxing page or in the settings reference snippets, and a code search of the sandbox runtime repository returned nothing. [U]

### Narrowest unattended permissions (assembled)

- `--permission-mode dontAsk`, an explicit allowlist passed by the launcher (`--allowedTools` or `--settings`), `--permission-prompts none`, `--strict-mcp-config`, `--disallowedTools` for web tools, the guard hook with `onFailure: "block"`, and on Linux or WSL2 the sandbox with `failIfUnavailable: true` and `denyRead` on sealed data. bypassPermissions only inside a container or VM. [I, from the verified facts above; the docs give no single recipe]

## Q4. Skills, subagents, plugins, models, scheduling

### Skills

- Frontmatter fields: `name`, `description`, `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context` (`fork`), `agent`, `background`, `hooks`, `paths`, `shell` (`bash` or `powershell`). Accepted but unused: `metadata`, `license`, `compatibility`. [docs/skills; V at field-name level, read through the fetch tool's summary]
- Size and loading: the combined `description` and `when_to_use` text is truncated at 1,536 characters in the skill listing; "Keep SKILL.md under 500 lines"; after compaction Claude Code re-attaches the most recent invocation of each skill, keeping the first 5,000 tokens of each, within a combined 25,000 tokens. [docs/skills; V]
- Skill hooks: at most 1,024 hooks and 16,384 matcher characters per source (2.1.304+). [CHANGELOG; V]
- 2.1.295 fixed a skill's `allowed-tools` and `effort` being dropped in `-p`. [CHANGELOG; V]
- The skill-listing budget figure was in an unread part of the page. [U]

### Subagents

- Frontmatter fields: `name`, `description`, `tools`, `disallowedTools`, `model` (`sonnet`, `opus`, `haiku`, `fable`, a full ID, or `inherit`), `permissionMode`, `maxTurns` (2.1.246+), `autoCompactWindow` (2.1.296+), `skills`, `mcpServers`, `hooks`, `memory`, `background`, `omitClaudeMd` (2.1.271+), `effort`, `isolation` (`worktree`), `color`, `initialPrompt`. [docs/sub-agents; V]
- Subagents can set an effort level: frontmatter `effort` (`low`, `medium`, `high`, `xhigh`, `max`). `CLAUDE_CODE_SUBAGENT_EFFORT` exists from 2.1.316. From 2.1.317 a subagent on a different model uses that model's saved effort or default, not the session's. [docs/sub-agents, CHANGELOG; V]
- "For security reasons, plugin subagents don't support the hooks, mcpServers, or permissionMode frontmatter fields." `initialPrompt` is ignored there too. [docs/sub-agents, docs/plugins/components; V]
- A parent in bypassPermissions, acceptEdits or auto passes that mode to the subagent. Nesting up to three layers. [docs/sub-agents; V]

### Models and effort

- Aliases now: `opus` is Opus 5.5, `sonnet` is Sonnet 5.5, `haiku` is Haiku 5.5, `fable` is Fable 5.2 (needs 2.1.321, so not on the installed 2.1.303), `best` equals `opus`, plus `opusplan` and `[1m]` forms. Full IDs include `claude-opus-5-5`, `claude-haiku-5-5`, `claude-fable-5-2`. [docs/model-config, CHANGELOG; V]
- Effort levels `low`, `medium`, `high`, `xhigh`, `max`; default `medium` for the four current models. Precedence: `CLAUDE_CODE_EFFORT_LEVEL`, in-session choice, `--effort`, settings, model default. [docs/model-config; V]
- Fable 5.2 list price from the changelog: $8 input and $40 output per million tokens, $0.20 per million for cache reads. Other prices were not re-checked. [CHANGELOG; V for Fable 5.2, U for the rest]

### Plugins and marketplaces

- A plugin can carry skills, commands, agents, hooks (`hooks/hooks.json`, same shape as settings hooks), monitors, output styles, `bin/` (added to the Bash tool PATH), `.mcp.json`, `settings.json`, and mods. [docs/plugins/components; V]
- Plugin `settings.json`: "Two keys take effect, agent and subagentStatusLine, and every other key is dropped." So a plugin cannot ship permission rules, a `statusLine`, `env` or sandbox settings. Claude Code does not load a `CLAUDE.md` at the plugin root. [docs/plugins/components; V]
- `${CLAUDE_PLUGIN_ROOT}` changes on every update ("Don't write state there"); `${CLAUDE_PLUGIN_DATA}` persists. Plugin monitors do not start with `-p`. [docs/plugins/components; V]
- Marketplace: a directory with `.claude-plugin/marketplace.json` (`name`, `owner`, `plugins`). Sources: relative path, `github`, `git-subdir`, `url`, `archive` (zip over HTTPS, `sha256` pin), `npm`, `command`. A marketplace added from a local directory loads plugins in place with no network and no version bump. [docs/plugin-marketplaces, docs/plugins/host-marketplace; V]
- Updates: background auto-update is off by default for a third-party marketplace; a user or admin turns it on; users get a new copy only when the plugin's `version` changes, or on each commit when `version` is omitted. `ref` and `sha` pin a git source. [docs/plugins/host-marketplace; V]
- Scopes: user (`~/.claude/settings.json`), project (`.claude/settings.json`, each collaborator still installs once), local (`.claude/settings.local.json`); recorded under `enabledPlugins`. In `-p` and CI, plugins install in the background and can be missing from the first turn unless `CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1`. `CLAUDE_CODE_PLUGIN_SEED_DIR` points at a pre-populated plugins directory for images that cannot clone. [docs/plugins/install C7, docs/plugins/org C7; V]
- Could the kit ship as a plugin? Skills, the guard hook, the agents and `expctl` on `bin/` could. Lost or changed: permission rules, status line, the CLAUDE.md block, the `.mcp.json` approval flow, subagent frontmatter hooks, and a stable install path. The guard hook would then be removable by disabling the plugin. [I]
- `claude plugin eval` (2.1.269+, present on 2.1.303): runs cases from `evals/` with graders (`regex`, `tool_used`, `tool_order`, `file_exists`, `llm`, `baseline`), three runs per case by default, a no-plugin baseline arm, `--threshold`, `--max-cost-usd`, `-j` 1 to 8, exit code 0, 1 or 2, an HTML report; it resolves installed plugins and skills-directory plugins. Hooks and real MCP servers run outside the run's sandbox. [docs/plugin-evals, LOCAL; V]
- `claude plugin validate` checks plugin and marketplace files. [docs/plugin-marketplaces, LOCAL; V]

### Mods (in-process plugin code)

- On by default from 2.1.287. "A mod can approve many tool calls that your deny or ask rules or your PreToolUse hooks would stop, unless the built-in guard prevents it." [docs/plugins/mods/overview; V]
- The built-in guard (`sec-default@builtin`, shown as `cc-plugin-sec-default`) loads only when the machine has managed settings or a `managed-mcp.json`, or the session runs on a Team or Enterprise login. An API key, a cloud-provider login or a long-lived OAuth token does not count. With the guard, a user's mod cannot approve a call that a deny rule, an ask rule or a PreToolUse hook stopped. [docs/plugins/mods/admin C7; V]
- "Permission rules and PreToolUse hooks apply to Claude's tool calls, not to a mod's $.fs and $.process calls." [docs/plugins/mods/admin C7; V]
- A mod Claude writes does not load in `claude -p`, in dontAsk mode, in an untrusted workspace, or with `--safe-mode`, `--bare` or `disableAllHooks`. From 2.1.321 such mods turn on without asking in auto and bypass modes. From 2.1.321 a mod's own tool calls raise no permission prompt, even under ask rules, in dontAsk and in `-p`; deny rules still apply. [docs/plugins/mods/create C7, CHANGELOG; V]
- `--bare`, `--safe-mode` and `disableAllHooks` do not stop built-in mods. `disableAllHooks` also stops settings hooks and the status line. [docs/plugins/mods/overview; V]

### Instruction files

- AGENTS.md is read natively from 2.1.277, through a built-in plugin (`cc-plugin-agents-md@builtin`), but by default only when there is no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` in the working directory or above it. The setting value `claude-md-and-agents-md` loads both. A CLAUDE.md can import it with `@AGENTS.md`. [docs/memory; V]
- CLAUDE.md: target under 200 lines per file; imports nest to four hops; auto memory loads its first 200 lines or 25 KB. [docs/memory; V]
- The kit writes a CLAUDE.md block, so a shared AGENTS.md written for the other agent ports is not read by Claude Code in that repository unless CLAUDE.md imports it. [I]

### Scheduled and background runs

- `/loop` and the cron tools (`CronCreate`, `CronList`, `CronDelete`) are session-scoped: they fire only while the session is open and idle, recurring tasks expire after 7 days, at most 50 tasks, minimum interval 1 minute, with jitter. A self-paced loop ends when an iteration neither reschedules nor stops (after one fallback wakeup). `CLAUDE_CODE_DISABLE_CRON=1` disables them. [docs/scheduled-tasks; V]
- Cloud scheduled tasks run on a fresh clone in the cloud, minimum interval 1 hour, auto mode by default. Desktop scheduled tasks run on the user's machine and need the desktop app. [docs/scheduled-tasks comparison table; V. The two detail pages were not read]
- `claude --bg` starts a session under a local supervisor; it survives closing the terminal and sleep, not shutdown; a session that needs a permission decision waits ("Needs input"); unattached finished or waiting sessions are stopped after about an hour; `--bg` with `-p` is rejected; agent view is a research preview. Native Windows support was not stated in the part read. [docs/agent-view, first 100,000 characters; V, platform support U]
- None of these lets harness code decide what is kept. A plain process that starts one `claude -p` per iteration does. [I]

## Q5. Changes 2.1.295 to 2.1.322 and what a guard cannot see

### Changes that matter (from CHANGELOG and RELEASES, V)

| Version (date) | Change |
|---|---|
| 2.1.295 (2026-10-08) | `onFailure: "block"` added. Fixed a skill's `allowed-tools` and `effort` dropped in `-p`; `--tools` and `--restricted` not applying to late-registered tools; an async SessionStart hook's context re-added on every resume. |
| 2.1.302 (2026-10-16) | `-p` and SDK sessions with no permission mode start in `default` mode. |
| 2.1.304 (2026-10-19) | Fixed a plugin keeping a headless run going past `--max-turns`. Skill hook limits. |
| 2.1.305 (2026-10-20) | `sandbox.allowNestedUserNamespaces`. |
| 2.1.309 (2026-10-22) | Fixed PowerShell hooks not blocking on exit code 2, and Windows PreToolUse and PermissionRequest hooks with `"shell": "powershell"` failing open without Git for Windows. Fixed sandboxed Bash running shell startup files outside the sandbox, and an `Edit(path)` deny rule missing some redirects. |
| 2.1.310 (2026-10-23) | Fixed Windows PreToolUse and PermissionRequest hooks letting a call through when Git Bash is missing and the hook command is only quoted strings, such as a quoted path. Ubuntu AppArmor sandbox check. |
| 2.1.311 (2026-10-26) | JSON output escapes control characters. `CLAUDE_CODE_EVEN_MORE_DANGEROUSLY_SKIP_PERMISSIONS`. |
| 2.1.312 (2026-10-27) | Removed the `claude_code.safety_event` telemetry event added in 2.1.307. At most 24 prompt or agent hooks at a time. |
| 2.1.314 (2026-10-30) | `permissions.blockWritesOutsideWorkingDirectories`. Bash-matcher hooks now run on Monitor shell commands. `-p` exits 1 on startup failure. A settings file excluded with `--setting-sources` no longer supplies some settings. |
| 2.1.316 (2026-10-31) | `CLAUDE_CODE_SUBAGENT_EFFORT`. Fixed PowerShell hooks not blocking on exit code 2 in some command forms. |
| 2.1.317 (2026-11-03) | `onFailure: "block"` for SDK callbacks. Settings edits in the first second after launch now apply. Windows fixes for some volumes and long scratchpad paths. |
| 2.1.318 (2026-11-04) | `credential_expires_at` in `-p` JSON. `claude mcp add` and `remove` take the config lock. A non-interactive launch fails on an invalid `~/.claude.json` instead of replacing it. |
| 2.1.319 (2026-11-06) | `permissions.denyInsteadOfPrompting`. Fixed Bash deny and ask rules missing commands with quoted words, a `sed` permission skip, an environment-prefix permission bypass, a sandbox escape when creating a worktree, and settings edits ignored within seconds of Claude Code writing the file. |
| 2.1.321 (2026-11-09) | Fixed a read-only Bash command running outside the sandbox without a prompt, deny rules not applying to `cp` or `mv` into a directory, a hook `ask` lost when another hook's `defer` finished first, and NotebookEdit reporting success to hooks on failure. Mod changes listed under Q4. |
| 2.1.322 (2026-11-10) | Newest release. Its single entry adds fast mode on one cloud provider; nothing guard-relevant. |

- Status line: no breaking change found by keyword search of the changelog in this range. Facts that matter: it runs through Git Bash on Windows or PowerShell when Git Bash is absent, paths in the command must use forward slashes, updates are debounced at 300 ms, a running script is cancelled when a new update starts, `refreshInterval` has a 1 second minimum, and `disableAllHooks` turns it off. The kit's status line command uses the same bash-only expansion as its hooks. [docs/statusline, V; "no breaking change" is from keyword search only]
- Installer: lists merge across settings files, so merged allow rules add up; a malformed entry is skipped with a warning; a file that fails validation is rejected whole and, in `-p`, silently. `.mcp.json` is a protected file and its servers connect without asking in `-p`. `install.py` adds two network MCP servers unless `--no-mcp` is given and tells the user "Claude Code asks you to approve them", which is not true for `-p` runs. [docs/settings C7, docs/permissions, LOCAL, install.py lines 157 and 198 to 208; V]
- `install.py` skips a hook group when the script name is already present, so an upgrade keeps the old command form. [install.py, read 2026-11-10; V]

### Security advisories checked

- GHSA-5xjx-9qx6-jcrv (High, 2026-10-26): race in the Edit tool allowed writes outside the workspace from code running in the macOS sandbox; fixed in 2.1.251.
- GHSA-pq7j-f95f-qfcv (High, 2026-10-09): plugin commit pin bypass; fixed in 2.1.179.
- GHSA-fg94-h982-f3mm (Moderate, 2026-06-13): data exfiltration through a pre-approved model-hub domain in WebFetch; fixed in 2.1.163.
- GHSA-4p2j-qj3c-6x84 (High, 2026-10-13): the desktop app on Windows ran a `git.exe` found in the opened project; fixed in desktop 1.8089.0.
- Listed but not opened: GHSA-5j29-h97v-84ch (write-time symlink following, High, 2026-10-05), GHSA-7835-87q9-rgvv (sandbox escape through worktree paths, High, 2026-06-25). Pages 2 to 4 were not read.
- All four opened are fixed below 2.1.295, so a 2.1.295 floor covers them. [ADVISORIES; V]

### What a PreToolUse guard cannot see

- Files added with an `@`-mention: no tool call. Mitigate with Read deny rules or `CLAUDE_CODE_DISABLE_FILE_MENTIONS=1` (2.1.299+). [docs/hooks; V]
- `EndConversation`, and `/skill` invocations typed by the user (those go to UserPromptExpansion). [docs/hooks; V]
- Tools outside the kit's matcher: Agent, Workflow, WebFetch, WebSearch, Skill, every MCP tool. [settings.fragment.json; V]
- Anything a permitted program does itself: a Python or Node script that opens, writes or uploads files. Only a sandbox or operating-system permissions stop that. A preprint measured the same gap for approvals in general: approval records name the entry command and miss the effects it triggers (arXiv 2609.28586 v1, 2026-09-23, 111 approval-trace pairs, authors' own measurement). [docs/permissions, https://arxiv.org/abs/2609.28586 abstract; V]
- Mods: their `$.fs` and `$.process` calls are outside rules and hooks; without the built-in guard a mod can approve a call the hook blocked. Whether a mod's `$.tool.call` passes PreToolUse hooks was not found. [docs/plugins/mods/admin C7, V; last sentence U]
- Runs with `--bare`, `--safe-mode` or `disableAllHooks`, and a settings file that failed validation in `-p`. [docs/headless, docs/cli-reference, LOCAL; V]
- MCP servers, plugin monitors, the status line command and other hooks: they run outside PreToolUse and outside the sandbox. [docs/sandboxing; V]
- Monitor WebSocket watches: they follow deny and ask rules from 2.1.319, but a `Bash` matcher does not run for them. [CHANGELOG, docs/hooks; V]
- Versions before 2.1.295 (no fail-closed hooks) and, on Windows, versions before 2.1.310 and 2.1.316 (hooks that fail open). [CHANGELOG; V]

## Changed since 23 October or wrong in the earlier notes

1. Newest version: the notes say 2.1.308 (2026-10-22). It is 2.1.322 (2026-11-10); 11 releases followed. [RELEASES; V]
2. "-p with no mode denies calls needing approval from v2.1.302" is imprecise. From 2.1.302 such runs start in Manual (`default`) mode, where a call that needs approval is denied when nothing approves it. Before that they could start in auto mode. [docs/permission-modes; V]
3. The protected-path list is longer than in the notes: add `.config/git`, `.idea`, `.cargo`, `.yarn`, `.mvn`, `~/.claude/dev-mods/` and more files. [docs/permission-modes; V]
4. `claude_code.safety_event` (2.1.307) was removed in 2.1.312. [CHANGELOG; V]
5. New since the notes: `permissions.denyInsteadOfPrompting` (2.1.319), `permissions.blockWritesOutsideWorkingDirectories` (2.1.314), `CLAUDE_CODE_SUBAGENT_EFFORT` (2.1.316), subagent effort no longer inherited across models (2.1.317), `credential_expires_at` (2.1.318), Fable 5.2 (2.1.321), mod behaviour in 2.1.321, Bash-matcher hooks on Monitor commands (2.1.314). [CHANGELOG; V]
6. `--bare` is now announced as the future default for `-p`. A launcher that relies on project hooks loading by default will lose the guard when that ships. [docs/headless; V]
7. In `-p`, auto mode's repeated blocks do not stop the run. [docs/permission-modes; V]
8. `--max-turns` is missing from `claude --help` on 2.1.303 though the CLI reference documents it. [LOCAL, docs/cli-reference; V]
9. Plugin subagents also ignore `initialPrompt`, not only `permissionMode`, `hooks` and `mcpServers`. [docs/plugins/components; V]
10. Project `permissions.allow` rules are not used by `-p` in an untrusted folder. The notes and README advise an explicit `--permission-mode` but do not mention this. [docs/permissions; V]
11. `install.py` tells the user that Claude Code asks for approval of the added MCP servers. In `-p` they connect without asking. [docs/permissions, install.py; V]
12. The Windows review fix (#24, interpreter path quoting) addressed quoting. The underlying dependence on a shell remains; 2.1.309 and 2.1.310 fixed fail-open bugs in exactly that path, and the installed 2.1.303 predates both. [CHANGELOG; V]
13. Background commands in unattended sessions have had a time limit since 2.1.285 (10 minutes by default in a text-prompt `-p` run). I did not find this in the earlier notes. [docs/tools-reference; V]

## Concerns any design must handle

VERSION-DRIFT-MIN-VERSION
HOOK-FAIL-OPEN-OLD-VERSION
HOOK-TIMEOUT-FAIL-OPEN
HOOK-WINDOWS-SHELL-DEPENDENCE
INTERPRETER-RESOLUTION-WINDOWS
STATUSLINE-SHELL-DEPENDENCE
PATH-SEPARATOR-NORMALIZATION
HOOK-MATCHER-COVERAGE-GAP
HOOK-BYPASS-FILE-MENTION
HOOK-BYPASS-SCRIPT-INDIRECTION
APPROVAL-TRANSITIVE-EFFECTS
HOOK-BYPASS-INPROCESS-EXTENSION
HOOK-OVERRIDE-BY-INPROCESS-EXTENSION
AGENT-WRITTEN-EXTENSION-AUTO-ENABLE
HOOK-DISABLE-BY-FLAG
HOOK-DISABLE-BY-FUTURE-DEFAULT
GUARD-LIVENESS-UNVERIFIED-AT-START
SUBAGENT-HOOK-TRUST-GAP
HEADLESS-ASK-BECOMES-DENY
HEADLESS-TRUST-DIALOG-SKIPPED
HEADLESS-ALLOW-RULES-DROPPED-UNTRUSTED
HEADLESS-INVALID-SETTINGS-IGNORED
HEADLESS-EXIT-CODE-AMBIGUITY
PERM-RULE-TEXT-MATCH-NOT-BOUNDARY
PERM-READ-DENY-SCRIPT-BYPASS
SANDBOX-PLATFORM-GAP
SANDBOX-GPU-UNVERIFIED
SANDBOX-SCOPE-SHELL-ONLY
SEALED-DATA-NEEDS-OS-BOUNDARY
CONFIG-HOT-RELOAD-TAMPER
SETTINGS-MERGE-UPGRADE-MIGRATION
MCP-AUTOLOAD-HEADLESS
EXFIL-PREAPPROVED-DOMAIN
BACKGROUND-JOB-LIFETIME
SIGTERM-KILLS-CHILD-TREE
COST-CAP-SOFT-ESTIMATE
RATE-LIMIT-STALL
USAGE-CAP-MID-LOOP
CREDENTIAL-EXPIRY-UNATTENDED
MODEL-REFUSAL-ENDS-TURN
MODEL-FALLBACK-CONFOUNDS-COMPARISON
AUTO-MODE-CLASSIFIER-DEPENDENCE
COMPACTION-RULE-LOSS
SKILL-DISPLACEMENT-BY-SIMILAR-SKILL
INSTRUCTION-FILE-PRECEDENCE-ACROSS-AGENTS
PLUGIN-PACKAGING-HOOK-LOSS
PLUGIN-ROOT-PATH-CHANGES
TRANSCRIPT-FORMAT-UNSTABLE
SEC-PROMPT-INJECTION

## Related evidence read (abstracts only)

- arXiv 2610.11647 v2 (2026-10-13), "One Skill Too Many": a similar co-installed skill displaced the installed skill in about one in five of 6,368 runs without lowering task completion; a pre-tool hook at the first skill read restored fidelity. Authors' measurement, three unnamed models. Relevant because machines with many skills installed can displace the kit's skill silently. https://arxiv.org/abs/2610.11647 [V at abstract level]
- arXiv 2609.20804 v1 (2026-09-17), harness design study: 176 matched settings on two public benchmarks; context management matters more as the context budget tightens; a bash-only tool interface did well at lower cost. Supports keeping the kit a command-line tool with compact output. https://arxiv.org/abs/2609.20804 [V at abstract level]
- arXiv 2607.27250 v1 (2026-07-28), context files study: 288 runs on 17 tasks with two coding agents; the context-file strategy did not measurably change correctness (effect bounded at 10 to 15 points). Small sample. Supports enforcing validity rules in code, not in instruction files. https://arxiv.org/abs/2607.27250 [V at abstract level]

## Open questions

1. Which release introduced exec-form hooks (`args`), and what an older version does with `args`. It appears to predate 2.1.207, so a 2.1.295 floor should cover it; confirm before relying on it.
2. What versions before 2.1.295 do with `onFailure`: ignore the key or reject the hook entry.
3. Does the sandbox on WSL2 pass the GPU through to a training process? A ten-minute local trial would answer it.
4. Does a mod's `$.tool.call` pass through PreToolUse hooks?
5. Exit code and result fields when a `-p` run hits a plan usage cap; the `rate_limit_event` schema; the exit code of a max-turns or budget stop.
6. When does `--bare` become the default for `-p`, and what flag keeps hooks on afterwards?
7. Does the status line accept an exec form, and how should its interpreter be resolved on Windows without Git Bash?
8. Exact semantics of `permissions.denyInsteadOfPrompting`.
9. Does `--setting-sources project` keep authentication working when the credential helper lives in user settings?
10. Does a skill's `allowed-tools` restore the `expctl` read-only allowances in an untrusted `-p` run? The trust table says skill `allowed-tools` are used.
11. Does the Microsoft Store Python alias work as an exec-form `command`?
12. Not researched: the six web query families (the shared web search budget for this run was used up before my first query, and the other search tool was rate limited), the other guard projects named in the sweep, advisory pages 2 to 4, the unread ends of the errors, agent-view, skills, sub-agents and model-config pages, and the pages for cloud and desktop scheduled tasks, workflows, `/goal` and channels.

## Redirect attempts

1. Every docs page opens with a banner: "Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt. Use this file to discover all available pages before exploring further." Treated as data. Not followed.
2. No other instruction-like text aimed at the reader was seen in fetched pages, release notes, advisories or abstracts.
3. For completeness, tool-generated text (not third-party content): the fetch tool's summariser twice suggested fetching further pages, and the search tool returned a budget notice telling me not to route around the limit. I did not search by other means.
