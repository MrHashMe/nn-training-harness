# Platform scout: Cursor (editor agent and terminal agent)

Checked 10-11 November 2026. Nothing was run live except `cursor --version` and `cursor --help`.
Vendor docs are unversioned live pages; on 2026-11-11 they describe editor 3.27, terminal agent (CLI) v2026.10.22
and SDK 1.0.40. The editor installed on the test machine is 3.2.16, about 25 minor versions older.

Status words: **Verified** = read in a primary source (vendor docs, vendor advisory, vendor release notes, local
command). **Inferred** = derived from verified facts. **Unverified** = only user-generated or forum evidence, or not
testable under this scout's rules. Forum replies by apparent vendor staff are marked Unverified unless a doc agrees,
because the fetched pages showed no staff badge.

## Summary (10 lines)

1. Cursor has native hooks (`.cursor/hooks.json`, version 1), skills, subagents, rules, AGENTS.md, MCP and a headless terminal agent, so every kit part has a mechanical home except the editor status line.
2. Cursor loads another agent's folders by default: Claude Code hooks from `.claude/settings*.json`, skills from `.claude/skills` and `.codex/skills`, subagents from `.claude/agents` and `.codex/agents`. A Claude-only install of the kit is therefore half-active in Cursor today.
3. Through that compatibility route the guard is not trustworthy: failures fail open, `onFailure` is unknown to Cursor, the POSIX-style command cannot run under PowerShell, and the script is reported to receive `Shell` (not `Bash`), which today's guard passes as a silent allow.
4. A native port needs three events with three payload shapes: `beforeShellExecution` (allow/deny/ask), `beforeReadFile` (allow/deny, receives full file content) and `preToolUse` (allow/deny; "ask" accepted but not enforced).
5. "ask" is unreliable everywhere on Cursor (not enforced for `preToolUse`; not applied under the default Auto-review run mode; payload carries no run mode), so the port must answer deny where today's guard asks.
6. Hooks fail open by default; `failClosed: true` and exit code 2 exist. A vendor-acknowledged race can drop a hook's stdout, so a JSON-only deny can be lost; deny by exit code 2 and set `failClosed` on every guard hook.
7. The terminal agent is a separate, auto-updating binary (`agent`, alias `cursor-agent`); headless is `-p` with `--output-format json|stream-json`; `--force`/`--yolo` approves everything and must not be used outside a container.
8. Headless without `--force`: file writes still apply, non-allowlisted shell commands and deletes are rejected without a prompt, exit code can be 0 even when every tool call was rejected, and token usage fields are undocumented.
9. Native Windows has no native sandbox (vendor runs its Linux sandbox inside WSL2); hooks run through PowerShell in the editor and break when the terminal agent is started from Git Bash; `python3` cannot be the interpreter.
10. The installed editor (3.2.16) predates Auto-review, and probably predates strict hook-output validation; the port needs a minimum-version gate and an install-time self-test, and its README must state per version what is enforced and what is advice.

## Local facts

| Claim | Source | Version | Checked | Status |
|---|---|---|---|---|
| `cursor --version` prints `3.2.16`, commit `3e548838cf824b70851dd3ef27d0c6aae371b3f0`, `x64` | local command | 3.2.16 | 2026-11-10 | Verified |
| `cursor --help` lists subcommands `tunnel`, `serve-web`, `agent` ("Start the Cursor agent in your terminal.") and option `--add-mcp <json>` | local command | 3.2.16 | 2026-11-10 | Verified |
| What `cursor agent` does (launch an installed terminal agent, or download one) | not run (forbidden) | 3.2.16 | - | Unverified |
| The kit's guard (`.claude/hooks/nn_guard.py`) returns 0 with no output when `tool_name` is empty, when stdin is not JSON, and when `tool_name` is a name it does not know (for example `Shell`, `Delete`): `SHELL_TOOLS = ("Bash","Monitor","PowerShell")`, unknown names fall into `check_path_tool`, which yields no results | local file, lines 40-41, 267-283, 431-464 | kit of 23 Oct 2026 | 2026-11-11 | Verified |
| The kit's reviewer subagents rely on Claude-only frontmatter (`tools: Read, Grep, Glob, Bash`, `model: opus`, a `hooks:` block calling `python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/nn_readonly.py"`) | local file `.claude/agents/experiment-reviewer.md` | kit of 23 Oct 2026 | 2026-11-11 | Verified |

## Q1. Instruction files

Source versions: live docs, 2026-11-11, unless stated. The docs do not say which editor version introduced each item, so
"as of 3.2" cannot be confirmed for any of them (Unverified for 3.2.16 specifically).

| Claim | Source | Status |
|---|---|---|
| Project rules live in `.cursor/rules/` as `.mdc` files (subfolders allowed). "A plain `.md` file in `.cursor/rules` is ignored". | https://cursor.com/docs/rules | Verified |
| Frontmatter fields: `description`, `globs` (comma-separated), `alwaysApply`. Example: `---` / `description: "..."` / `alwaysApply: false` / `---`. | https://cursor.com/docs/rules | Verified |
| Selection: `alwaysApply: true` = always included (globs and description ignored); `false` + globs = attached when a matching file is in context; `false` + description only = agent decides; none = only on @-mention. | https://cursor.com/docs/rules | Verified |
| "Keep rules under 500 lines". `@file` mentions in a rule are not inlined. Rules do not affect Tab or Inline Edit. | https://cursor.com/docs/rules | Verified |
| `AGENTS.md` is read in the project root and in subdirectories; nested files combine with parents, more specific wins. | https://cursor.com/docs/rules | Verified |
| User Rules (settings) and Team Rules (dashboard) exist; precedence Team > Project > User. | https://cursor.com/docs/rules (fetched 2026-11-10) | Verified |
| The terminal agent reads `.cursor/rules`, plus `AGENTS.md` and `CLAUDE.md` at the project root "and applies them as rules". | https://cursor.com/docs/cli/using (2026-11-10) | Verified |
| The editor also reads `CLAUDE.md`: release notes "Week of Oct 12, 2026" say "agents no longer get duplicate AGENTS.md or CLAUDE.md instructions", which implies both are loaded; the rules page itself never mentions `CLAUDE.md`. | https://cursor.com/docs/release-notes | Inferred |
| Nested `AGENTS.md` now also applies when the terminal agent edits or creates a file in that directory. | https://cursor.com/docs/release-notes (CLI v2026.10.22) | Verified |
| Agent Skills: folders with `SKILL.md` in `.agents/skills/`, `.cursor/skills/` (project) and `~/.agents/skills/`, `~/.cursor/skills/` (user). | https://cursor.com/docs/skills | Verified |
| "For compatibility, Cursor also loads skills from Claude and Codex directories: `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, and `~/.codex/skills/`." | https://cursor.com/docs/skills | Verified |
| SKILL.md frontmatter: `name` (required; lowercase letters, numbers, hyphens; "Must match the parent folder name"), `description` (required), optional `paths`, `disable-model-invocation`, `icon`, `color`, `metadata`. Optional folders `scripts/`, `references/` ("loaded on demand"), `assets/`. | https://cursor.com/docs/skills | Verified |
| Skills are chosen by the agent from name and description, or invoked with `/skill-name` (attaches to one message). | https://cursor.com/docs/skills | Verified |
| Limits flagged by the product: name over 64 characters or not lowercase-hyphen, name different from folder, description over 1,024 characters, body over about 5,000 tokens (warning, skill still loads). | https://cursor.com/docs/cli/changelog (v2026.10.08), https://cursor.com/docs/release-notes (3.25) | Verified |
| What happens when the same skill name exists in two roots (for example `.claude/skills/nn-training` and `.cursor/skills/nn-training`) is not documented. | https://cursor.com/docs/skills | Unverified |
| Skills work in the terminal agent, including `/skill-name` in `-p` mode (since May 2026); discovery skips hidden directories (v2026.08.11). | https://cursor.com/docs/cli/changelog (2026-11-10) | Verified |
| Other agents' folders are read through one switch: "Include Third-Party Plugins, Skills, and Other Configs" under Cursor Settings > Agents > Third-Party Imports. "The setting is on by default." It covers Claude Code hooks, and the same compatibility lists cover skills and subagents. | https://cursor.com/docs/reference/third-party-hooks | Verified |
| Subagents are read from `.claude/agents/` and `.codex/agents/` as well as `.cursor/agents/`. | https://cursor.com/docs/subagents | Verified |

## Q2. Hooks

Source for everything in this section unless stated: https://cursor.com/docs/hooks (same page is listed as
`/docs/agent/hooks`), fetched as markdown on 2026-11-10 and re-read live on 2026-11-11. Status Verified for "the docs
say so"; behaviour on the installed 3.2.16 is Unverified throughout.

### Files, precedence, execution

- Project: `<project>/.cursor/hooks.json`. User: `~/.cursor/hooks.json`. Enterprise: `C:\ProgramData\Cursor\hooks.json`
  (Windows), `/etc/cursor/hooks.json` (Linux/WSL), `/Library/Application Support/Cursor/hooks.json` (macOS). Team hooks
  come from the dashboard (Enterprise).
- "Priority order (highest to lowest): Enterprise → Team → Project → User". "All matching hooks from every source run,
  and Cursor merges their responses: any `deny` wins over `ask`, and `ask` wins over `allow`, regardless of source."
- Project hooks run from the project root (so the command is `.cursor/hooks/x`, not `./hooks/x`); user hooks run from
  `~/.cursor/`. "Project hooks run in any trusted workspace". The file is watched and reloaded.
- "On Windows, the desktop app runs hook commands through PowerShell and pipes the JSON into the command, so a
  PowerShell script reads it from `$input` and other programs read it from stdin."
- Environment for hook scripts: `CURSOR_PROJECT_DIR`, `CURSOR_VERSION`, `CURSOR_USER_EMAIL`, `CURSOR_TRANSCRIPT_PATH`,
  `CURSOR_CODE_REMOTE`, `CURSOR_PLUGIN_ROOT`, and `CLAUDE_PROJECT_DIR` ("Alias for project dir (Claude compatibility)").

Config example, verbatim (https://cursor.com/docs/hooks, 2026-11-10):

```json
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./scripts/approve-network.sh",
        "timeout": 30,
        "matcher": "curl|wget|nc"
      }
    ]
  }
}
```

Per-hook options: `command` (required), `type` (`"command"` default, or `"prompt"`), `timeout` (seconds; default
"platform default", value not stated), `loop_limit` (default 5), `matcher` (regex), and `failClosed` (boolean, default
false): "When `true`, hook failures (crash, timeout, non-zero exit code, no output) block the action instead of
allowing it through. Permission hooks block on invalid JSON or an invalid response even when this is `false`."

### Events

Agent: `sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`,
`subagentStop`, `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`,
`beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`,
`afterAgentThought`. Tab: `beforeTabFileRead`, `afterTabFileEdit`. App: `workspaceOpen`.

Matchers: for `preToolUse`/`postToolUse`/`postToolUseFailure` "Values include `Shell`, `Read`, `Write`, `Grep`,
`Delete`, `Task`, and MCP tools using the `MCP:<tool_name>` format"; for `beforeShellExecution` the matcher runs
against the full command string.

### Exit codes and failure behaviour (verbatim)

"Exit code `0` - Hook succeeded, use the JSON output. For permission hooks (`beforeShellExecution`,
`beforeMCPExecution`, `beforeReadFile`, `beforeTabFileRead`, `subagentStart`, `preToolUse`), invalid JSON or a response
that doesn't match the hook's schema blocks the action. Exit code `2` - Block the action (equivalent to returning
`permission: "deny"`). Other exit codes - Hook failed, action proceeds (fail-open by default)".

So: crash, timeout, missing interpreter or any exit code other than 0 and 2 = **fail open** unless `failClosed: true`;
invalid output from a permission hook = block (in current versions).

History that matters for the installed 3.2.16 (all forum evidence, Unverified):
- Editor 2.5.17 (Feb 2026) silently allowed a command when a hook printed malformed JSON; apparent staff called it "a
  real issue" and on 2026-05-14 said it "has been addressed in a recent Cursor update" without a version.
  https://forum.cursor.com/t/beforeshellexecution-hook-malformed-json-response-silently-allows-command-instead-of-blocking/152669
- A user reports that from 3.4.17 "or maybe even earlier" a `null` hook response is treated as invalid and blocks.
  https://forum.cursor.com/t/hooks-no-longer-accept-null-and-failed-closed/160617
- Inference: 3.2.16 may still fail open on invalid hook output, and may not know `failClosed`. Needs a canary test.

### Payloads, verbatim from the vendor docs (https://cursor.com/docs/hooks, copied 2026-11-10)

Common input on every hook:

```json
{
  "conversation_id": "string",
  "generation_id": "string",
  "model": "string",
  "model_id": "string",
  "model_params": [{ "id": "string", "value": "string" }],
  "hook_event_name": "string",
  "cursor_version": "string",
  "workspace_roots": ["<path>"],
  "user_email": "string | null",
  "transcript_path": "string | null"
}
```

Generic pre-tool (`preToolUse`):

```json
// Input
{
  "tool_name": "Shell",
  "tool_input": { "command": "npm install", "working_directory": "/project" },
  "tool_use_id": "abc123",
  "cwd": "/project",
  "model": "claude-opus-4-7-thinking-max",
  "model_id": "claude-opus-4-7",
  "model_params": [
    { "id": "thinking", "value": "true" },
    { "id": "context", "value": "1m" },
    { "id": "effort", "value": "max" }
  ],
  "agent_message": "Installing dependencies..."
}

// Output
{
  "permission": "allow" | "deny",
  "user_message": "<message shown in client when denied>",
  "agent_message": "<message sent to agent when denied>",
  "updated_input": { "command": "npm ci" }
}
```

Docs table for `permission`: "`"allow"` to proceed, `"deny"` to block. `"ask"` is accepted by the schema but not
enforced for `preToolUse` today."

Shell and MCP execution (`beforeShellExecution` / `beforeMCPExecution`):

```json
// beforeShellExecution input
{
  "command": "<full terminal command>",
  "cwd": "<current working directory>",
  "sandbox": false
}

// beforeMCPExecution input
{
  "tool_name": "<tool name>",
  "tool_input": "<json params>",
  "mcp_server_name": "<server name from mcp.json>"
}
// Plus either (HTTP/SSE servers):
{ "url": "<server url>", "mcp_server_url": "<server url>" }
// Or (stdio servers):
{ "command": "<launch command and args>" }

// Output
{
  "permission": "allow" | "deny" | "ask",
  "user_message": "<message shown in client>",
  "agent_message": "<message sent to agent>"
}
```

Docs text: "Invalid JSON or a response that doesn't match the hook's schema blocks the action. Crashes, timeouts, and
non-zero exit codes other than `2` fail open by default: Cursor logs the failure and allows the action through. Set
`failClosed: true` on the hook definition to block on those failures too." Note that MCP `tool_input` is a JSON
*string*, not an object.

File reads (`beforeReadFile`):

```json
// Input
{
  "file_path": "<absolute path>",
  "content": "<file contents>",
  "attachments": [
    {
      "type": "file" | "rule",
      "file_path": "<absolute path>"
    }
  ]
}

// Output
{
  "permission": "allow" | "deny",
  "user_message": "<message shown when denied>"
}
```

File edits (`afterFileEdit`, after the fact, cannot block):

```json
// Input
{
  "file_path": "<absolute path>",
  "edits": [{ "old_string": "<search>", "new_string": "<replace>" }]
}
```

To block a write before it happens the only hook is `preToolUse` with matcher `Write` (and `Delete`). The docs show no
`tool_input` example for `Read`, `Write`, `Delete`, `Grep` or `Task`. One third-party capture (Windows, August 2026)
shows `Grep` with `tool_input` keys `pattern`, `file_path`, `output_mode`:
https://chrisnas.github.io/posts/2026-08-23_spying-on-cursor-hooks/ (Unverified; the same author never saw
`model_params`, `model_id` or `attachments`, and saw the editor put a leading `/` before Windows paths in
`workspace_roots`).

Session start and stop:

```json
// sessionStart input
{
  "session_id": "<unique session identifier>",
  "is_background_agent": true | false,
  "composer_mode": "agent" | "ask" | "edit"
}
// sessionStart output
{
  "env": { "<key>": "<value>" },
  "additional_context": "<context to add to conversation>"
}
// stop input
{ "status": "completed" | "aborted" | "error", "loop_count": 0 }
// stop output
{ "followup_message": "<message text>" }
```

`sessionStart` "runs as fire-and-forget; the agent loop does not wait for or enforce a blocking response."

Subagent start, verbatim input: `{"subagent_id": "abc-123", "subagent_type": "generalPurpose", "task": "Explore the
authentication flow", "parent_conversation_id": "conv-456", "tool_call_id": "tc-789", "subagent_model":
"claude-sonnet-4-20250514", "is_parallel_worker": false, "git_branch": "feature/auth"}`; output
`{"permission": "allow" | "deny", "user_message": "..."}`; "`"ask"` is not supported for `subagentStart` and is treated
as `"deny"`." Editor 3.27 adds `parent_agent_id` to hook payloads for subagents
(https://cursor.com/docs/release-notes, 2026-11-11, Verified).

No payload has a field for the approval or run mode (nothing like Claude Code's `permission_mode`). Verified by
reading every documented payload; apparent staff confirm the gap for the status-line payload
(https://forum.cursor.com/t/cursor-cli-custom-statusline-replaces-native-footer-and-cannot-preserve-auto-review-state/166364).

### allow / deny / ask in practice

| Claim | Source | Status |
|---|---|---|
| `preToolUse`: only `deny` is respected; `ask` is accepted and ignored. | docs (above); apparent staff 2026-05-23: "right now only `deny` is respected" https://forum.cursor.com/t/support-authoritative-allow-deny-and-ask-verdicts-from-hooks/161342 | Verified |
| `beforeShellExecution` `ask` is not applied in Auto-review mode (the command runs with no prompt); it prompts in Allowlist and Run Everything modes. Reported on 3.21.16, Windows; apparent staff on 2026-10-05: "the hook's "ask" answer currently isn't applied", flagged, no fix version. | https://forum.cursor.com/t/beforeshellexecution-hook-returning-ask-is-ignored-in-auto-review-mode-honoured-in-allowlist-and-run-everything-3-21-16/173694 | Unverified (forum, apparent staff) |
| Earlier regressions of `ask` (2.4.21; sandboxed shell in March 2026; allowlisted commands skipping a hook's `ask`). | https://forum.cursor.com/t/hooks-ask-permission-broken-in-2-4-21/150020 , https://forum.cursor.com/t/beforeshellexecution-returns-permission-ask-but-sandboxed-agent-shell-still-runs-the-command-sandbox-true/155438 | Unverified (forum) |
| A hook `allow` does not skip Cursor's own approval for a command that is not allowlisted. | https://forum.cursor.com/t/beforeshellexecution-hook-permissions-allow-ask-ignored-allow-list-takes-precedence/144244 | Unverified (forum) |
| Stdout race: Cursor can treat a hook process as finished before it has read all stdout; a JSON deny "gets dropped and the command runs". Apparent staff 2026-07-16: "This is a real bug on our side" and "please don't rely on a deny hook alone as a hard block for risky commands right now"; 2026-10-09 (3.24.10, Windows): still "a known issue", workaround is a short pause before exit (50-150 ms), with `failClosed: true` the empty read blocks instead. No fix announced. | https://forum.cursor.com/t/race-condition-silently-disables-hooks-that-exit-quickly/165818 , https://forum.cursor.com/t/pretooluse-hook-exit-0-but-empty-stdout-under-concurrent-tool-calls-failclosed-blocks/174214 | Unverified (forum, apparent staff, two threads) |
| Exit code 2 blocks without needing stdout. | https://cursor.com/docs/hooks | Verified (doc); its immunity to the race is Inferred |

### Claude Code hooks loaded by Cursor (https://cursor.com/docs/reference/third-party-hooks, 2026-11-11)

- Loaded from `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json`, after Cursor's own
  sources; "All matching hooks from every source run." Verified.
- Event mapping: PreToolUse→preToolUse, PostToolUse→postToolUse, UserPromptSubmit→beforeSubmitPrompt, Stop→stop,
  SubagentStop→subagentStop, SessionStart→sessionStart, SessionEnd→sessionEnd, PreCompact→preCompact. Notification and
  PermissionRequest: not supported. Verified.
- Tool mapping: Bash→Shell, Read→Read, Write→Write, Edit→Write, Grep→Grep, Task→Task, WebFetch, WebSearch; **Glob: not
  supported**. Verified. The kit's matcher also names `Monitor`, `PowerShell`, `MultiEdit`, `NotebookEdit`, which have
  no mapping (Inferred: never fire).
- Output: nested `hookSpecificOutput` (`permissionDecision`→`permission`, `permissionDecisionReason`→`user_message`,
  `updatedInput`→`updated_input`) and the flat format are both accepted. Exit code 2 blocks; "Other exit codes: Hook
  failed, action proceeds (fail-open)". Verified. `onFailure` and `CLAUDE_PROJECT_DIR` are not mentioned on the page.
- Because the event is `preToolUse`, a Claude-format `"ask"` decision is not enforced. Inferred from the two docs.
- Which `tool_name` the Claude-format script receives is not documented. One user (Windows, 2026-11-05) reports
  `Shell`, not `Bash` (thread 161342 above). Unverified, and decisive: with `Shell` the kit's guard exits 0 silently.
- SDK 1.0.40 release note: "Claude Code hooks that deny a tool call now block it in local agents." So before late
  October 2026 a Claude-format deny did not block in SDK-driven local agents. Verified (release notes).
- Security history: CVE-2026-48124 (GHSA-pc9j-3qc2-95wv, published 2026-05-21, affected 2.4.37, patched 3.0.0):
  "Cursor Desktop could execute workspace-defined Claude hook commands from" `.claude/settings.local.json` without
  dedicated approval; fix: "Workspace-sourced hook commands now require appropriate approval".
  https://github.com/cursor/cursor/security/advisories/GHSA-pc9j-3qc2-95wv Verified.

### Where hooks run

| Surface | Claim | Source | Status |
|---|---|---|---|
| Editor | All agent events. | https://cursor.com/docs/hooks | Verified |
| Terminal agent | Reads the same `.cursor/hooks.json` and `~/.cursor/hooks.json`; Claude Code `settings.json` hooks "are read and merged" (Jan 2026); hook payloads arrive on stdin (May 2026); "Hooks that fail or point at a command that can't be found are now reported as failed" (v2026.10.15); "Post-tool hooks now fire for subagents" (v2026.10.17). | https://cursor.com/docs/cli/changelog , https://cursor.com/docs/release-notes | Verified |
| Terminal agent | Events confirmed by apparent staff on 2026-04-12: `beforeShellExecution`, `afterShellExecution`, `afterFileEdit`, `postToolUse`, `stop`, `sessionStart`. | https://forum.cursor.com/t/cursor-cli-doesnt-send-all-events-defined-in-hooks/148316 | Unverified (forum, apparent staff) |
| Terminal agent | A third-party live test (2026-08-23) saw `sessionStart`, `sessionEnd`, `beforeSubmitPrompt`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `beforeShellExecution`, `afterShellExecution`, `beforeReadFile`, `afterFileEdit` in interactive and `agent -p` runs; `subagentStart`/`subagentStop` and `preCompact` never fired; MCP hooks untested. | https://github.com/pickypg/ai-agent-macropad/blob/main/cursor/README.md | Unverified |
| Terminal agent, Windows | Started from Git Bash, every hook fails and every tool call is marked rejected while the run "exits 0 with subtype=success"; apparent staff 2026-09-23: "the CLI builds the hook command for PowerShell, but when cursor-agent inherits the Git Bash environment, it passes that command to bash"; known issue, no date; workaround: start from PowerShell or cmd. | https://forum.cursor.com/t/cursor-agent-on-windows-launched-from-git-bash-rejects-every-hook-the-powershell-wrapper-is-run-with-bash-eval/172789 | Unverified (forum, apparent staff) |
| Terminal agent, Windows | One user: each hook blocks for the full configured `timeout`, and with a short timeout a deny hook is bypassed; apparent staff could not reproduce. | https://forum.cursor.com/t/cli-hooks-block-each-tool-call-for-the-full-timeout-lowering-it-silently-disables-deny-hooks-windows/169942 | Unverified |
| Cloud agents | Command hooks from the repository's `.cursor/hooks.json` run for: `beforeShellExecution`, `afterShellExecution`, `beforeReadFile`, `afterFileEdit`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`, `subagentStop`, `beforeSubmitPrompt`, `preCompact`, `afterAgentResponse`, `afterAgentThought`, `stop`. Not available: `sessionStart`, `sessionEnd`, MCP hooks, Tab hooks, `workspaceOpen`, user-level hooks, prompt hooks. "Cloud agents sometimes begin in a read-only environment for early exploratory turns. Hooks do not run during those turns." | https://cursor.com/docs/hooks | Verified |
| Windows encoding | "On Windows, hooks now get clean UTF-8 payloads" (3.27); "on Windows hooks receive non-ASCII text correctly" (3.26). Older builds, including 3.2.16, may deliver mis-encoded payloads. | https://cursor.com/docs/release-notes | Verified (fix); Inferred (older builds) |

## Q3. Terminal agent (Cursor CLI)

| Claim | Source | Status |
|---|---|---|
| It is a separate program. Install: `curl https://cursor.com/install -fsS \| bash` (macOS, Linux, WSL) or `irm 'https://cursor.com/install?win32=true' \| iex` (native Windows PowerShell). Binary `agent` in `~/.local/bin`; `agent --version`, `agent update`; auto-updates by default. | https://cursor.com/docs/cli/installation (2026-11-10) | Verified |
| "New `agent` command is now the primary CLI entrypoint. `cursor-agent` remains as a backward-compatible alias." | https://cursor.com/changelog/cli-jan-08-2026 | Verified |
| `agent` collides with other tools' binaries; apparent staff recommend `cursor-agent` as "the more stable option" (2026-07-21). | https://forum.cursor.com/t/cli-agent-binary-name-collision-with-grok-cli-login-goes-to-wrong-oauth-provider/166249 | Unverified (forum, apparent staff) |
| The official docs never mention `cursor agent`; an apparent staff forum reply (2026-03-12) used `cursor agent --print --trust --yolo "..."`. | https://forum.cursor.com/t/autoresearch-with-cursor-cli/154219 | Unverified |
| Versions are dates. Newest in release notes on 2026-11-11: v2026.10.22 (then v2026.10.17, v2026.10.15, v2026.10.08). | https://cursor.com/docs/release-notes | Verified |
| Sign-in: `agent login` (browser; `NO_OPEN_BROWSER=1` prints the URL), `agent status`/`whoami`, `agent logout`; or an API key in `CURSOR_API_KEY` or `--api-key`, created in the dashboard. | https://cursor.com/docs/cli/reference/authentication (2026-11-10) | Verified |
| Headless flags: `-p, --print` ("Has access to all tools, including write and shell."), `--output-format text\|json\|stream-json` (default `text`; print mode is also inferred from non-TTY stdout or piped stdin), `--stream-partial-output`, `--model <model>`, `--list-models`, `--mode plan\|ask`, `-f, --force` ("Force allow commands unless explicitly denied"), `--yolo` (alias), `--sandbox enabled\|disabled`, `--approve-mcps`, `--trust` ("Trust the workspace without prompting (headless mode only)"), `--workspace <path>`, `--resume`, `--continue`, `-w/--worktree`. | https://cursor.com/docs/cli/reference/parameters | Verified |
| `json` output on success has exactly: `type` ("result"), `subtype` ("success"), `is_error`, `duration_ms`, `duration_api_ms`, `result`, `session_id`, optional `request_id`. "On failure, the process exits with a non-zero code and writes an error message to stderr. No well-formed JSON object is emitted in failure cases." | https://cursor.com/docs/cli/reference/output-format (2026-11-11) | Verified |
| `stream-json` events: `system`/`init` (`apiKeySource`, `cwd`, `session_id`, `model`, `permissionMode`), `user`, `assistant`, `tool_call` (`started`/`completed`), terminal `result`. On failure "the stream may end early without a terminal event". | same | Verified |
| No token-usage field is documented on the output-format page. The CLI changelog (Feb 2026) says "Per-turn input/output/cache token totals and a `request_id` in `stream-json` output"; field names are not published. | https://cursor.com/docs/cli/reference/output-format , https://cursor.com/docs/cli/changelog | Verified (absence in reference); Unverified (field names) |
| Exit codes: only "non-zero" on failure is documented; no table. | https://cursor.com/docs/cli/reference/output-format | Verified |
| `permissionMode` in the init event is "just a fixed label, safe to ignore" (apparent staff, 2026-09-24). | https://forum.cursor.com/t/cli-allowlist-cannot-auto-approve-deletetoolcall-or-webfetch-skipapproval-stays-false-print-mode-user-rejected/172763 | Unverified (forum, apparent staff) |
| Permission config: global `~/.cursor/cli-config.json` (Windows `$env:USERPROFILE\.cursor\cli-config.json`; `CURSOR_CONFIG_DIR` overrides) and project `<project>/.cursor/cli.json`. "Only permissions can be configured at the project level. All other CLI settings must be set globally." | https://cursor.com/docs/cli/reference/configuration (2026-11-11) | Verified |
| Syntax: `permissions.allow` and `permissions.deny` arrays of `Shell(commandBase)` (also `Shell(curl:*)`), `Read(pathOrGlob)`, `Write(pathOrGlob)`, `WebFetch(domainOrPattern)`, `Mcp(server:tool)`. "Deny rules take precedence over allow rules". There is no ask list and no Delete token. | https://cursor.com/docs/cli/reference/permissions (2026-11-10) | Verified |
| Global-only settings: `approvalMode` ("`allowlist`, `auto-review`, or `unrestricted`"), `sandbox.mode`, `sandbox.networkAccess`, `sandbox.readBoundary` (`system` default or `workspace`). | https://cursor.com/docs/cli/reference/configuration | Verified |
| Headless and file writes: the headless page says "Without --force, changes are only proposed, not applied"; the using page says "Cursor has full write access in non-interactive mode."; apparent staff (2026-01-22): "`-p` gives the agent full access to write files and run bash. That's expected and documented behavior." | https://cursor.com/docs/cli/headless , https://cursor.com/docs/cli/using , https://forum.cursor.com/t/agent-p-without-force-modifies-txt-files/149583 | Verified (docs conflict); Unverified (which is true) |
| Headless and shell: apparent staff (2026-04-13): "In headless/print mode without --force, every command that isn't on the allowlist is silently denied (no prompt, the agent sees the failure and reacts). Combined with --sandbox enabled, sandboxed commands auto-execute and everything else just fails." Suggested command: `agent --print --trust --sandbox enabled "your prompt"`. | https://forum.cursor.com/t/disable-permissions-ask-in-sandbox/157243 | Unverified (forum, apparent staff) |
| Headless and other approvals: a missing approval is reported as `User Rejected`; Delete "always prompts and there's no allow token for it yet ... so in `--print` it's only auto-approved under `unrestricted` or `--force`"; `WebFetch(...)` allow rules were not honoured in `--print` (acknowledged bug, CLI 2026.09.18). | thread 172763 above | Unverified (forum, apparent staff) |
| Headless needs a trusted workspace: "Non-interactive runs in untrusted workspaces fail with guidance unless `--trust` (or `--force`) is passed." Admins can disable headless mode. Mode-switch approvals auto-reject after 15 seconds. | https://cursor.com/docs/cli/changelog (Jan 2026, v2026.06.09, v2026.08.11) | Verified |
| What a hook `"ask"` does when nobody can answer (headless, with or without `--force`) is documented nowhere. | https://cursor.com/docs/hooks | Unverified; treat as not reaching a person |
| Sandbox: `--sandbox enabled\|disabled`, `/sandbox`, `agent sandbox run`; "the CLI fails fast with a clear reason when sandboxing is enabled but unavailable" (Feb 2026). | https://cursor.com/docs/cli/changelog | Verified |
| Sandbox platforms: macOS Seatbelt; Linux Landlock + seccomp (kernel 6.2+, unprivileged user namespaces); Windows: "we run our Linux sandbox inside WSL2", native Windows needs primitives the vendor is "working with Microsoft" on (blog, 2026-02-18). The security page has no Windows section. | https://cursor.com/blog/agent-sandboxing , https://cursor.com/docs/agent/security | Verified (blog, Feb 2026); Inferred (still true in November) |
| "With Run Everything on, agents now run without the sandbox unless your permissions.json restricts that mode." (editor 3.24) | https://cursor.com/docs/release-notes | Verified |
| Status line: `statusLine` in the global `cli-config.json`, shape `{"type": "command", "command": "...", "padding": 2}`; the command gets JSON on stdin with at least `context_window.total_input_tokens`, `context_window.context_window_size` and `autorun`; it replaces the native footer. Not on the official configuration page; the CLI changelog (April 2026) announces "Custom status line"; a built-in `/statusline` skill configures it. | https://forum.cursor.com/t/cursor-cli-custom-statusline-replaces-native-footer-and-cannot-preserve-auto-review-state/166364 , https://cursor.com/docs/cli/changelog , https://cursor.com/docs/skills | Verified (exists); Unverified (schema) |
| Git safety: "Repository-controlled git configuration, including fsmonitor, hooks, attributes, and external diff programs, no longer runs during the agent's own git operations" (v2026.08.11). | https://cursor.com/docs/cli/changelog | Verified |

## Q4. MCP, subagents, auto-run, dot-folders, other surfaces

| Claim | Source | Status |
|---|---|---|
| MCP config: `.cursor/mcp.json` (project) and `~/.cursor/mcp.json` (global); `{"mcpServers": {"name": {"command", "args", "env", "envFile"}}}` or `{"url", "headers"}`; interpolation `${env:NAME}`, `${userHome}`, `${workspaceFolder}`; transports stdio, SSE, Streamable HTTP. | https://cursor.com/docs/mcp (2026-11-10) | Verified |
| "All MCP connections need your approval"; each tool call follows the run mode unless allowlisted. Terminal agent: `agent mcp list\|enable\|disable\|login`, `--approve-mcps`; global servers load without a prompt, project servers need approval (April 2026). | https://cursor.com/docs/mcp , https://cursor.com/docs/cli/changelog | Verified |
| Subagents: markdown files in `.cursor/agents/` (also `.claude/agents/`, `.codex/agents/`, and the same three under `~`). "When multiple locations contain subagents with the same name, `.cursor/` takes precedence over `.claude/` or `.codex/`." | https://cursor.com/docs/subagents (2026-11-11) | Verified |
| Frontmatter: `name`, `description`, `model` (`inherit` or a model ID), `readonly` ("If `true`, the subagent runs with restricted write permissions (no file edits, no state-changing shell commands)."), `is_background`. Nothing is said about `tools`, `hooks`, `color`. | same | Verified |
| "You can use subagents in the editor, CLI, and Cloud Agents." Subagents inherit all parent tools including MCP. One level of nesting. The `model` field can be overridden by plan or admin limits. | same | Verified |
| How strictly `readonly: true` stops a shell command that writes is not specified. | same | Unverified |
| Run modes (current editor): Auto-review (a classifier on the vendor backend; "not a security boundary"; "the recommended default" since 3.6, 2026-05-29), Allowlist (sandboxed on supported platforms), Run Everything. "Ask Every Time was deprecated" and "Run in Sandbox was folded into Allowlist" in 3.5 (2026-05-22). The installed 3.2.16 therefore still has the older set of modes. | https://cursor.com/docs/agent/security/run-modes (2026-11-10) | Verified; Inferred for 3.2.16 |
| Defaults: reading and searching need no approval; workspace file edits need no approval "except for configuration files"; terminal commands need approval by default. Workspace trust is "disabled by default". | https://cursor.com/docs/agent/security (2026-11-10) | Verified |
| `permissions.json` (`~/.cursor/` and `<project>/.cursor/`): `terminalAllowlist` (command prefixes), `mcpAllowlist` (`server:tool`), `autoRun` (`allow_instructions`, `block_instructions` for Auto-review). It "overrides" the in-app allowlist; "Not a security boundary". The reference says "CLI permissions are separate", while the CLI changelog (March 2026) says the CLI "reads the same terminal/MCP allowlist file as the IDE". | https://cursor.com/docs/reference/permissions , https://cursor.com/docs/cli/changelog | Verified (docs conflict) |
| There is no deny list and no ask list for the editor; blocking is done with hooks. | https://cursor.com/docs/reference/permissions | Verified |
| Dot-folder protection: "Cursor protects paths like `.git/config`, `.git/hooks`, `.vscode`, `.cursorignore`, and sensitive Cursor config files." The sandbox policy denies writes to most of `.cursor` but excepts its rules, commands, worktrees, skills and agents directories. Nothing protects `.claude/` or `.agents/`. | https://cursor.com/docs/agent/security , https://cursor.com/blog/agent-sandboxing | Verified; last point Inferred |
| `.cursorignore` in the project root: "Ignored files are blocked from Agent." "Terminal commands and MCP tools run outside of Cursor's file access controls." `.env` files, `.git/` and lock files are ignored by default; `.gitignore` is respected. In the Linux sandbox ignored files are "completely inaccessible to the sandboxed process". | https://cursor.com/help/customization/ignore-files , https://cursor.com/blog/agent-sandboxing | Verified |
| Other protections: File-Deletion Protection, External-File Protection, Browser Protection. | https://cursor.com/docs/agent/security | Verified |
| Allowlists have been bypassed repeatedly: CVE-2026-22708 (GHSA-82wg-qcm4-fp2w, 2026-01-14, "Terminal Tool Allowlist Bypass via Environment Variables"), GHSA-hf2x-r83r-qw5q (2026-03-09, "Arbitrary Code Execution via Prompt Injection and Whitelist Bypass"). | https://github.com/cursor/cursor/security/advisories?page=2 | Verified (titles and dates) |
| Sandbox escapes fixed in 2026: via `.git` settings (CVE-2026-26268, patched 2.5), agent-controlled working directory and symlinks (CVE-2026-50548, CVE-2026-50549, Critical, patched 3.0), a replaced virtual-environment Python executable later run outside the sandbox (CVE-2026-73217, macOS, patched 3.1.2), privileged containers when a container runtime is installed (CVE-2026-73218, patched versions "None"). Windows path tricks bypassed sensitive-file protection in 2025 (GHSA-2jr2-8wf5-v6pf, GHSA-6r98-6qcw-rxrw). | https://github.com/cursor/cursor/security/advisories | Verified |

Other surfaces, one paragraph. Cloud Agents ("formerly called Background Agents") "run in isolated VMs in the cloud",
are started from the desktop app, web, iOS, Slack, GitHub or Bitbucket comments, Linear or the API, need a paid plan
("Premium and higher, Teams, Enterprise, or a legacy paid plan"), take their environment from agent-led setup, a
snapshot or a Dockerfile in `.cursor/environment.json`, get secrets from the dashboard, and never ask for approval
("Cloud Agents do not use Run Modes"). They run only the repository's command hooks, without `sessionStart`. The docs
do not mention GPUs. Self-hosted workers (`agent worker start`) run cloud agents on the user's own machine (on Windows
this needs Git for Windows). A Cursor SDK (`cursor-sdk` for Python 3.10+, and TypeScript; changelog entry "Agent SDK",
2026-10-20) drives local or cloud agents with an API key and exposes `run.usage`; hooks for it are file-based only.
Plugins (`.cursor-plugin/plugin.json`) bundle rules, skills, agents, commands, MCP and hooks for a marketplace.
Sources: https://cursor.com/docs/cloud-agent , https://cursor.com/docs/agent/security/run-modes ,
https://cursor.com/docs/sdk/python , https://cursor.com/docs/plugins , https://cursor.com/changelog (all Verified,
2026-11-10/11). For the kit: a README line, no port.

## Q5. Kit feature by feature

"Mechanical" means the product enforces or performs it; "instruction" means it depends on the model obeying text.

| Kit feature | Editor agent | Terminal agent | Sources |
|---|---|---|---|
| Guard hook | Mechanical, with limits. Shell: `beforeShellExecution`. Reads: `beforeReadFile`. Writes, deletes, grep, task, MCP: `preToolUse` with a matcher. Deny works; "ask" does not hold (see Q2); fail-closed only with `failClosed: true`; stdout race open. On 3.2.16: Unverified. | Mechanical with larger gaps. Same file. Shell hooks are vendor-confirmed; `preToolUse` and `beforeReadFile` rest on one third-party test. Native Windows: broken when started from Git Bash; timeout bug reported. | https://cursor.com/docs/hooks ; forum threads 148316, 172789, 169942, 165818 |
| Read-only reviewer subagents | Mechanical through `readonly: true` in `.cursor/agents/<name>.md`. The existing `.claude/agents/*.md` are also discovered, but their `tools:` and `hooks:` fields are undocumented in Cursor, so there the read-only rule is instruction only. | Same per docs ("editor, CLI, and Cloud Agents"). `subagentStart` hooks did not fire in a third-party CLI test, so gating by hook is not available. | https://cursor.com/docs/subagents |
| Session-start status | Mechanical: `sessionStart` hook returning `additional_context` (fire-and-forget, cannot block). | Mechanical: `sessionStart` works in the CLI per changelog (Jan 2026) and apparent staff (Apr 2026). Not in cloud agents. | https://cursor.com/docs/hooks ; https://cursor.com/docs/cli/changelog |
| Status line | Not available (no such surface in the docs). | Mechanical but global only: `statusLine` in `~/.cursor/cli-config.json`, replaces the native footer, schema undocumented. The installer may not write there without an explicit flag. | forum thread 166364 ; https://cursor.com/docs/cli/reference/configuration |
| Skill with references | Mechanical: `SKILL.md` folder in `.cursor/skills/` or `.agents/skills/`; `.claude/skills/` is read too while third-party imports are on. `references/` load on demand. Loading the skill at the right moment is the model's choice (as on Claude Code). | Mechanical, same roots; `/skill-name` works in `-p`. | https://cursor.com/docs/skills ; https://cursor.com/docs/cli/changelog |
| Instruction block | Mechanical loading: root `AGENTS.md` (always), or `.cursor/rules/x.mdc` with `alwaysApply: true`. | Mechanical loading: `.cursor/rules`, root `AGENTS.md` and root `CLAUDE.md`. A block present in both files reaches the model twice in older builds (fixed "Week of Oct 12, 2026"). | https://cursor.com/docs/rules ; https://cursor.com/docs/cli/using ; https://cursor.com/docs/release-notes |
| MCP servers | Mechanical: `.cursor/mcp.json`; connection and tool calls need approval unless allowlisted; `beforeMCPExecution` hook can deny. | Mechanical: same file; project servers need approval or `--approve-mcps`; MCP hooks in the CLI untested. | https://cursor.com/docs/mcp |
| Permission rules | Partial. Allow only (`permissions.json` `terminalAllowlist`, `mcpAllowlist`); no deny or ask lists; "Not a security boundary"; a project file overrides the user's in-app list. Deny and ask rules must be hooks; secret-file read denies can also go in `.cursorignore`. | Mechanical allow and deny in `<project>/.cursor/cli.json` (`Shell()`, `Read()`, `Write()`, `WebFetch()`, `Mcp()`); no ask tier; no Delete token. Ask rules must be hooks, and a hook cannot ask reliably. | https://cursor.com/docs/reference/permissions ; https://cursor.com/docs/cli/reference/permissions |

## Changed since 23 October or wrong in the earlier notes

- The four research notes of 23 October contain no Cursor material (search of `docs/research-notes/` for "cursor"
  found nothing). Everything above is new, not a re-check.
- `docs/upgrade/PROMPT.md` says "there is no separate cursor-agent binary". For the product that is wrong: the
  terminal agent is a separately installed, auto-updating binary named `agent` with the alias `cursor-agent`
  (https://cursor.com/changelog/cli-jan-08-2026). The `agent` subcommand in the editor's `cursor --help` is real on
  this machine, but it is not in the official docs and was not run. Whether a terminal agent is installed here is unknown.
- The earlier Claude Code note treats `.claude/` as private to Claude Code. Cursor reads hooks, skills and subagents
  from it by default (https://cursor.com/docs/reference/third-party-hooks), so the Claude install is not inert when the
  repository is opened in Cursor.
- Releases after 23 October (release notes print no dates; order on the page gives the sequence): editor 3.27 (after
  CLI v2026.10.22): "On Windows, hooks now get clean UTF-8 payloads", hook payloads get `parent_agent_id`; SDK 1.0.40:
  "Claude Code hooks that deny a tool call now block it in local agents."; changelog entries "Build Live Apps in
  Cursor" (2026-11-05) and "Voice Chat with Agents" (2026-11-06), neither relevant.
  Just before the cut-off: editor 3.26 ("Always Run on terminal approvals now sticks when permissions.json manages your
  allowlist."; rules and skills match when paths differ only in drive-letter case; Windows hooks receive non-ASCII
  text correctly), CLI v2026.10.22 (nested `AGENTS.md` on edits; PowerShell commands use UTF-8), CLI v2026.10.17
  ("Post-tool hooks now fire for subagents."), CLI v2026.10.15 ("`.cursorignore` and Read deny rules still apply to
  files outside the workspace"; failed or missing hook commands are now reported as failed), "Agent SDK" (2026-10-20).
  Source: https://cursor.com/docs/release-notes , https://cursor.com/changelog (2026-11-11). Verified, dates Inferred.
- Caution for other scouts: one search provider served a stale copy of the release notes that ended at editor 3.24 and
  CLI v2026.10.08; the live page is at 3.27 and v2026.10.22.
- Vendor documentation contradicts itself in three places that matter: (1) headless writes without `--force` (headless
  page versus using page and staff); (2) whether the terminal agent reads `permissions.json` (reference page versus
  CLI changelog); (3) `ask` listed as supported for `beforeShellExecution` while staff say it is not applied in the
  default run mode.

## Concerns any design must handle

GUARD-FAIL-OPEN-DEFAULT
GUARD-STDOUT-RACE-DROPS-DENY
GUARD-ASK-NOT-ENFORCED
GUARD-ASK-UNANSWERABLE-HEADLESS
GUARD-RUN-MODE-INVISIBLE
GUARD-PAYLOAD-SHAPE-MISMATCH
GUARD-TOOL-NAME-ALIAS-SILENT-ALLOW
GUARD-EVENT-COVERAGE-GAP
GUARD-FAIL-CLOSED-LOCKOUT
GUARD-TIMEOUT-SEMANTICS
GUARD-SELF-PROTECTION-ALL-AGENT-FOLDERS
GUARD-READ-HOOK-RECEIVES-FILE-CONTENT
COMPAT-FOREIGN-CONFIG-AUTOLOAD
COMPAT-DOUBLE-HOOK-EXECUTION
COMPAT-DUPLICATE-SKILL-DISCOVERY
COMPAT-DUPLICATE-INSTRUCTION-BLOCK
COMPAT-SUBAGENT-FRONTMATTER-NOT-HONOURED
READONLY-REVIEWER-ENFORCEMENT-STRENGTH
PLATFORM-WINDOWS-HOOK-SHELL
PLATFORM-INTERPRETER-NAME
PLATFORM-WINDOWS-SHELL-INHERITANCE
PLATFORM-NO-NATIVE-WINDOWS-SANDBOX
PLATFORM-WINDOWS-PATH-CANONICALISATION
PLATFORM-HOOK-PAYLOAD-ENCODING
VERSION-SKEW-INSTALLED-VS-DOCUMENTED
VERSION-MINIMUM-GATE-AND-SELF-TEST
VERSION-AUTO-UPDATE-DRIFT
HEADLESS-BYPASS-FLAG-FORBIDDEN
HEADLESS-PROMPT-BECOMES-SILENT-REJECT
HEADLESS-WRITES-WITHOUT-APPROVAL
HEADLESS-EXIT-CODE-UNRELIABLE
HEADLESS-TOKEN-USAGE-UNMEASURABLE
HEADLESS-NO-DELETE-PERMISSION
HEADLESS-CREDENTIAL-HANDLING
HEADLESS-ADMIN-CAN-DISABLE
HEADLESS-BINARY-NAME-COLLISION
PERM-ALLOWLIST-NOT-BOUNDARY
PERM-NO-ASK-TIER
PERM-TWO-CONFIG-SYSTEMS
PERM-PROJECT-FILE-OVERRIDES-USER-LIST
PERM-CLASSIFIER-NONDETERMINISTIC
SANDBOX-ESCAPE-WRITABLE-INTERPRETER
SANDBOX-ESCAPE-CONTAINER-RUNTIME
SANDBOX-OFF-WHEN-EVERYTHING-AUTO-RUNS
SEC-PROMPT-INJECTION
SEC-REPO-CONFIG-EXECUTES-CODE
SEC-IGNORE-FILE-NOT-BINDING-FOR-SHELL
INSTALL-HOME-CONFIG-UNTOUCHED
INSTALL-MERGE-NOT-OVERWRITE
CLOUD-HOOKS-PARTIAL
CLOUD-NO-APPROVALS
DOC-VENDOR-CONFLICT
DOC-PAYLOAD-FIXTURES-WITH-SOURCE-AND-DATE
SKILL-SPEC-LIMITS
STATUS-SURFACE-MISSING
LOOP-OWNERSHIP-NOT-AGENT

## Open questions

1. On the installed editor 3.2.16: does `failClosed` exist, does invalid hook output block, do `preToolUse` matchers work, and what does a project hook need before it runs (trust prompt, approval)?
2. Which `tool_name` and `tool_input` keys does a Claude-format hook receive in Cursor (`Shell` or `Bash`; `file_path` or another key for Write and Delete)?
3. In the terminal agent's `-p` mode, on native Windows and under WSL2: do `beforeShellExecution`, `preToolUse` and `beforeReadFile` fire, and what happens to a hook `ask`, with and without `--force`?
4. Is a terminal agent installed on the test machine, and does `cursor agent` download one? (Running it was out of scope.)
5. What are the `stream-json` token-usage field names, and do they include subagent usage?
6. Which skill wins when the same name exists in `.claude/skills` and `.cursor/skills`; is it listed twice?
7. How strong is `readonly: true` against shell commands that write (redirection, `python -c`, `git checkout`)?
8. Does the hook stdout race still exist in editor 3.27 and CLI v2026.10.22, and does exit code 2 avoid it?
9. Does a project `.cursor/permissions.json` replace or extend a user's in-app allowlist in practice?
10. Is there a native Windows sandbox in any current build, or is WSL2 still required?
11. What is the default hook timeout ("platform default")?

## Redirect attempts

None found in any fetched page, forum thread, advisory or repository file.
One tool-level message was not acted on: the search provider's rate-limit error advised creating an account and an API
key. No account was created; the remaining lookups used other fetch and search tools.

## Sources (all read 2026-11-10 or 2026-11-11)

Vendor docs: https://cursor.com/docs/hooks · https://cursor.com/docs/reference/third-party-hooks ·
https://cursor.com/docs/rules · https://cursor.com/docs/skills · https://cursor.com/docs/subagents ·
https://cursor.com/docs/mcp · https://cursor.com/docs/plugins · https://cursor.com/docs/agent/security ·
https://cursor.com/docs/agent/security/run-modes · https://cursor.com/docs/reference/permissions ·
https://cursor.com/docs/cli/overview · https://cursor.com/docs/cli/installation · https://cursor.com/docs/cli/using ·
https://cursor.com/docs/cli/headless · https://cursor.com/docs/cli/reference/parameters ·
https://cursor.com/docs/cli/reference/authentication · https://cursor.com/docs/cli/reference/permissions ·
https://cursor.com/docs/cli/reference/configuration · https://cursor.com/docs/cli/reference/output-format ·
https://cursor.com/docs/cli/changelog · https://cursor.com/docs/release-notes · https://cursor.com/changelog ·
https://cursor.com/changelog/cli-jan-08-2026 · https://cursor.com/docs/cloud-agent ·
https://cursor.com/help/customization/ignore-files · https://cursor.com/docs/sdk/python ·
https://cursor.com/blog/agent-sandboxing (2026-02-18) · https://cursor.com/llms.txt

Vendor advisories: https://github.com/cursor/cursor/security/advisories (pages 1-2 of 4) and the individual GHSA pages cited above.

Forum threads (user-generated; apparent staff replies noted in the tables): cited inline.

Third-party (not decision-driving on their own): https://github.com/pickypg/ai-agent-macropad/blob/main/cursor/README.md ·
https://chrisnas.github.io/posts/2026-08-23_spying-on-cursor-hooks/ · https://github.com/1Password/agent-hooks (MIT,
pushed 2026-11-04) · https://github.com/eqtylab/cupcake (Apache-2.0, pushed 2026-03-02).

Query families used: vendor docs and release notes; limitations and bug reports; security advisories; headless and
unattended behaviour; alternatives (cross-agent hook engines); state-of comparisons of agent extension points;
benchmarks (terminal-agent leaderboards: only aggregator figures found, none used); curated lists (no dedicated hook
list found).
