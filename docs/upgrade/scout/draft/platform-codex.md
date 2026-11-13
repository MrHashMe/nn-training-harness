# Scout note: OpenAI Codex CLI, what a port of the kit can rely on

Checked 10 and 11 November 2026. Newest stable CLI: 0.167.0 (6 Nov 2026). Newest local build: codex-cli 0.167.0-alpha.3.2.
No Codex session was started; nothing was installed or executed apart from `codex --version` and `--help`.

## Summary (10 lines)

1. Codex has a Claude-Code-compatible hook engine (same stdin/stdout contract, same event names), so `nn_guard.py` ports with a thin adapter, not a rewrite.
2. The pre-tool hook can deny but cannot ask: `permissionDecision: "ask"` is reported as a failed hook and the tool call continues. Every "ask" must become "deny" on Codex.
3. Hook failure is fail-open everywhere (crash, timeout, bad JSON, any exit code other than 2, missing interpreter). There is no `onFailure: block` equivalent.
4. Project hooks, project config and project rules load only if the project is trusted in the user's home config, and each hook declaration must also be trusted by hash; otherwise they are skipped without blocking anything.
5. Headless `codex exec` defaults to a read-only sandbox and approval policy "never"; `--full-auto` is gone; a rule that says "prompt" becomes "forbidden" when nobody can answer.
6. `.agents/` and `.codex/` are read-only inside the workspace-write sandbox: the kit is tamper-resistant there for free, but run state and logs written by the agent's commands must live elsewhere.
7. GPU devices are reported missing inside the Linux and WSL2 sandbox, and the recommended native Windows sandbox kills leftover child processes when the foreground command ends; training launches therefore need a narrow, rule-based exit from the sandbox.
8. Skills (`.agents/skills/<name>/SKILL.md`), AGENTS.md, project MCP config and SessionStart context injection are all mechanical; a custom status-line script is not supported; reviewer read-only is advisory unless enforced by hook or by a separate read-only process.
9. `codex exec --json` gives per-turn usage fields, but the totals are thread totals, hook events are absent from the stream, exit status is only 0 or 1, and usage caps appear only as error text.
10. Biggest unknowns need a 30-minute local trial: hook shell and quoting on native Windows, per-invocation project trust, GPU and detached processes under each sandbox.

## Source keys

Every claim below ends with `[key; status]`. Version and date checked are given here once per key.

| Key | URL | Version | Checked |
|---|---|---|---|
| D-HOOKS | https://developers.openai.com/codex/hooks | live docs, CLI 0.167.0 current | 2026-11-10 |
| D-AGENTS | https://developers.openai.com/codex/guides/agents-md | live docs | 2026-11-10 |
| D-SKILLS | https://developers.openai.com/codex/skills | live docs | 2026-11-10 |
| D-EXEC | https://developers.openai.com/codex/noninteractive | live docs | 2026-11-10 |
| D-RULES | https://developers.openai.com/codex/rules | live docs ("experimental") | 2026-11-10 |
| D-SEC | https://developers.openai.com/codex/agent-approvals-security | live docs | 2026-11-10 |
| D-WIN | https://developers.openai.com/codex/windows | live docs | 2026-11-10 |
| D-SUB | https://developers.openai.com/codex/subagents | live docs | 2026-11-10 |
| D-PERM | https://developers.openai.com/codex/permissions | live docs ("beta") | 2026-11-10 |
| D-CFG | https://learn.chatgpt.com/docs/config-file/config-reference | live docs; first 147,000 of 164,201 chars read | 2026-11-10 |
| D-CFGADV | https://learn.chatgpt.com/docs/config-file/config-advanced | live docs (paraphrased by fetch tool) | 2026-11-11 |
| D-MCP | https://learn.chatgpt.com/docs/extend/mcp?surface=cli | live docs (paraphrased) | 2026-11-11 |
| D-CLI | https://learn.chatgpt.com/docs/developer-commands?surface=cli | live docs (paraphrased) | 2026-11-11 |
| D-CHG | https://learn.chatgpt.com/docs/changelog | entries 0.163.0 to 0.167.0 (paraphrased) | 2026-11-11 |
| REL | https://github.com/openai/codex/releases/tag/rust-v0.167.0 | 0.167.0, published 2026-11-06 | 2026-11-11 |
| S-PTU | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/hooks/src/events/pre_tool_use.rs | tag rust-v0.167.0 | 2026-11-10 |
| S-SCHEMA | https://github.com/openai/codex/tree/rust-v0.167.0/codex-rs/hooks/schema/generated | tag rust-v0.167.0, sha cb41599c | 2026-11-11 |
| S-RUN | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/hooks/src/engine/command_runner.rs | tag rust-v0.167.0 (read verbatim) | 2026-11-11 |
| S-DISC | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/hooks/src/engine/discovery.rs | tag rust-v0.167.0 (paraphrased, then key lines re-read verbatim) | 2026-11-11 |
| S-EXEC | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/exec/src/lib.rs | tag rust-v0.167.0 (paraphrased, then key lines re-read verbatim) | 2026-11-11 |
| S-TRUSTW | https://github.com/openai/codex/blob/main/codex-rs/tui/src/hooks_rpc.rs, https://github.com/openai/codex/blob/main/codex-rs/app-server/src/config_manager_service.rs, https://github.com/openai/codex/blob/main/codex-rs/config/src/hooks_tests.rs | main at 82e6bacb (code search fragments, verbatim) | 2026-11-11 |
| S-EVT | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/exec/src/exec_events.rs | tag rust-v0.167.0 (read verbatim) | 2026-11-11 |
| S-JSONL | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/exec/src/event_processor_with_jsonl_output.rs | tag rust-v0.167.0 (paraphrased, then key lines re-read verbatim) | 2026-11-11 |
| S-POL | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/core/src/exec_policy.rs | tag rust-v0.167.0 (paraphrased, then key lines re-read verbatim) | 2026-11-11 |
| S-LOAD | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/config/src/loader/mod.rs | tag rust-v0.167.0 (paraphrased, then key lines re-read verbatim) | 2026-11-11 |
| S-ROLL | https://github.com/openai/codex/blob/main/codex-rs/rollout/src/list.rs | main at 82e6bacb (code search) | 2026-11-11 |
| S-ERR | https://github.com/openai/codex/blob/main/codex-rs/protocol/src/error.rs | main at 82e6bacb (code search) | 2026-11-11 |
| S-TUI | https://github.com/openai/codex/blob/main/codex-rs/tui/src/bottom_pane/status_line_setup.rs | main at 82e6bacb (code search) | 2026-11-11 |
| S-APP | https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/app-server/README.md | tag rust-v0.167.0 (partial, paraphrased) | 2026-11-11 |
| S-ENV | https://github.com/openai/codex/blob/main/codex-rs/config/src/shell_environment_policy.rs, https://github.com/openai/codex/blob/main/codex-rs/protocol/src/config_types.rs | main at 82e6bacb (code search fragments, verbatim) | 2026-11-11 |
| L-HELP | local `codex --help`, `exec --help`, `sandbox --help`, `mcp --help`, `execpolicy check --help`, `app-server --help`, `debug --help`, `plugin --help`, `features --help`, `doctor --help` | codex-cli 0.167.0-alpha.3.2 | 2026-11-10 and 2026-11-11 |
| I-38168 | https://github.com/openai/codex/issues/38168 | reported on 0.147.0, open | 2026-11-11 |
| I-57050 | https://github.com/openai/codex/issues/57050 | reported on 0.164.0, open | 2026-11-11 |
| I-49716 | https://github.com/openai/codex/issues/49716 | reported on 0.158.0, open | 2026-11-11 |
| I-57184 | https://github.com/openai/codex/issues/57184 | reported on 0.164.0, open | 2026-11-11 |
| I-54806 | https://github.com/openai/codex/issues/54806 | CLI 0.163.0-alpha.10.2 desktop, open | 2026-11-11 |
| I-19676 | https://github.com/openai/codex/issues/19676 | reported on 0.125.0-alpha.3, open | 2026-11-11 |
| I-57042 | https://github.com/openai/codex/issues/57042 | reported on 0.163.0, open | 2026-11-11 |
| I-10860 | https://github.com/openai/codex/issues/10860 | reported on 0.97.0 to 0.98.0, open | 2026-11-11 |
| X-CSA | https://labs.cloudsecurityalliance.org/research/csa-research-note-openai-codex-sandbox-escapes-20260922-csa/ | note dated 2026-09-22 | 2026-11-11 |
| X-DCG | https://raw.githubusercontent.com/Dicklesworthstone/destructive_command_guard/main/docs/codex-integration.md | main branch | 2026-11-11 |
| X-CSN | https://ccsafetynet.com/docs/installation/codex | live page | 2026-11-11 |
| X-CAR | https://raw.githubusercontent.com/leo-lilinxiao/codex-autoresearch/main/README.md | main branch | 2026-11-11 |
| X-ARX1 | https://arxiv.org/abs/2607.18064 | v2, 27 Aug 2026 (abstract only) | 2026-11-11 |
| X-ARX2 | https://arxiv.org/abs/2609.00006 | v1, 15 Jul 2026 (abstract only) | 2026-11-11 |

Status meanings: Verified = read in a primary source (official docs, tagged source, or local help output). Inferred = follows from a primary source but through a paraphrase, a code path or a combination of facts; not exercised. Unverified = user report, secondary source, or not found.

Note on the docs host: every `developers.openai.com/codex/...` URL now answers 308 to `learn.chatgpt.com/docs/...` [observed 2026-11-10 and 2026-11-11; Verified].

Note on local builds: the brief says builds 0.145 to 0.167 are installed. Only two `codex.exe` files were found under the stated folder: 0.130.0-alpha.5 (top level, file dated 9 May 2026) and 0.167.0-alpha.3.2 (hashed subfolder, file dated 10 Nov 2026) [L-HELP; Verified].

## Q1. Instruction files and skills

AGENTS.md
- Global scope: in `~/.codex` (or `CODEX_HOME`) Codex reads `AGENTS.override.md` if present, else `AGENTS.md`; only the first non-empty file at this level [D-AGENTS; Verified].
- Project scope: from the project root (normally the Git root; configurable with `project_root_markers`) down to the current directory; in each directory it checks `AGENTS.override.md`, then `AGENTS.md`, then names in `project_doc_fallback_filenames`; at most one file per directory [D-AGENTS, D-CFGADV; Verified].
- Order and precedence: files are concatenated root-down; files closer to the current directory come later and so override earlier guidance by position, not by a merge rule [D-AGENTS; Verified].
- Size: empty files are skipped and Codex stops adding files once the combined size reaches `project_doc_max_bytes`, 32 KiB by default [D-AGENTS, D-CFG; Verified]. The root file is added first, so a block in the root file is the safest place [Inferred].
- The chain is built once per run or session, not re-read mid-session [D-AGENTS; Verified]. Whether it survives compaction as base instructions was not checked [Unverified].
- An `AGENTS.override.md` in the root directory shadows the root `AGENTS.md` entirely, so a kit block written into `AGENTS.md` would be ignored there [D-AGENTS; Inferred]. The installer must detect this.
- Audit aid: `codex -c log_dir=./.codex-log` and `codex debug prompt-input` ("Render the model-visible prompt input list as JSON") let a person confirm what was loaded [D-AGENTS, L-HELP; Verified that the commands exist; behaviour not run].

Agent Skills
- Supported. A skill is a folder with `SKILL.md` (front matter `name` and `description` required) plus optional `scripts/`, `references/`, `assets/` and `agents/openai.yaml` [D-SKILLS; Verified].
- Project locations: `.agents/skills` in the current directory, in each parent, and at the repository root. User location: `$HOME/.agents/skills`. Admin: `/etc/codex/skills`. System: bundled skills. Symlinked skill folders are supported [D-SKILLS; Verified].
- The older `~/.codex/skills` location is not listed in the current docs; whether it still loads was not confirmed [Unverified].
- Trigger: explicit (`/skills`, or typing `$` and the skill name) or implicit when the task matches the `description`. Implicit use can be turned off per skill with `policy.allow_implicit_invocation: false` in `agents/openai.yaml` [D-SKILLS; Verified].
- Context cost: the skills list uses at most 2% of the context window, or 8,000 characters when the window is unknown; descriptions are shortened first and some skills may be omitted; `skills.max_context_tokens` tunes it [D-SKILLS; Verified]. A long description can therefore be cut or the skill dropped when many skills are installed.
- Skills can be disabled with `[[skills.config]] path = ... enabled = false`; changes are detected automatically [D-SKILLS; Verified].
- `.agents/` is a protected path: read-only for sandboxed commands in workspace-write mode [D-SEC, D-PERM; Verified]. Scripts there can still be read and executed [Inferred].
- Whether project skill discovery depends on project trust is not stated in the loader file read [S-LOAD; Unverified].
- Adoption context: a source-code study of eleven coding-agent harnesses (Codex CLI among them) reports SKILL.md skills in 9 of the 11 and MCP in 8 of the 11 [X-ARX2; Verified for the abstract only].

## Q2. Hooks

Events and handlers
- Events: PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, UserPromptSubmit, SubagentStart, SubagentStop, Stop, PreModelRequest, PostModelRequest, Interrupt, SessionStart, SessionEnd [D-HOOKS, S-SCHEMA; Verified].
- Handler types: `command` and `mcp_tool` run; `prompt` and `agent` handlers are parsed but skipped [D-HOOKS, S-DISC; Verified]. `async: true` hooks cannot block.
- The engine type is named `ClaudeHooksEngine` and plugin hooks get `CLAUDE_PLUGIN_ROOT`; the wire contract mirrors Claude Code's [S-RUN, S-DISC; Verified].
- Hooks are on by default; `[features] hooks = false` turns them off [D-HOOKS; Verified].

Where configured, and trust
- Files: `~/.codex/hooks.json`, `~/.codex/config.toml` (`[hooks]`), `<repo>/.codex/hooks.json`, `<repo>/.codex/config.toml`; plugins may bundle `hooks/hooks.json`; admins may define managed hooks in `requirements.toml` [D-HOOKS; Verified].
- "Project-local hooks load only when the project `.codex/` layer is trusted." [D-HOOKS; Verified]
- Project trust is read from `projects.<path>.trust_level` in the merged non-project config. The loader merges the lower layers (system, user, profile), then the `-c` command-line overrides (`merge_toml_values(&mut merged_so_far, cli_overrides_layer)`), then managed config (comment: "Managed config wins over CLI config. Apply it before choosing the project root and trust"), and only then calls `project_trust_context(&merged_so_far, ...)` [S-LOAD; Verified in source, not exercised].
- With no entry the project layer is created disabled (`ConfigLayerEntry::new_disabled`); no default-trusted path was found. The disabled reason reads: "To load project-local config, hooks, and exec policies, add {trust_key} as a trusted project in {user_config_file}." and, for an explicit entry, "{trust_key} is marked as untrusted in the effective configuration." [S-LOAD; Verified for the mechanism and the second message, Inferred for the exact tail of the first message and for the absence of any default]
- Second gate, per hook: "Codex records trust against the hook's current hash, so new or changed hooks are marked for review and skipped until trusted." Review and trust happen in the TUI with `/hooks` [D-HOOKS; Verified].
- The hash covers the hook declaration (event, matcher group, handler), not the script file's bytes, for non-plugin hooks. Source comment, verbatim: "Hash a normalized, config-derived identity instead of source text so equivalent hooks from config TOML and hooks.json converge on the same trust identity." Status rule: stored hash equal to current hash gives Trusted, a different stored hash gives Modified, none gives Untrusted [S-DISC; Verified]. Consequence: editing `nn_guard.py` does not require re-trust, and trust does not detect script tampering.
- Trust state is written to the user configuration as `hooks.state."<key>".trusted_hash` (plus `enabled`), by a config edit sent from the TUI or through the app server. A test fixture shows the shape: `[state."/tmp/hooks.json:pre_tool_use:0:0"]`, `enabled = false`, `trusted_hash = "sha256:abc123"` [S-TRUSTW; Verified on main, fragments only]. Trusting the kit's hooks therefore changes a file in the home directory, which the kit's installer must not do itself.
- The CLI has no `hooks` subcommand in 0.167.0-alpha.3.2 (all top-level commands listed) [L-HELP; Verified]. Trust is given in the TUI (`/hooks`), through the app server's config-write request, or skipped for one invocation with the bypass flag below.
- An untrusted or modified hook is listed but not runnable; discovery emits no warning for it [S-DISC; Inferred]. One user report says a current build "can silently skip an untrusted user hook" [X-DCG; Unverified, third party].
- `--dangerously-bypass-hook-trust`: "Run enabled hooks without requiring persisted hook trust for this invocation. DANGEROUS. Intended only for automation that already vets hook sources" [L-HELP; Verified]. Disabled hooks stay off even with the flag [S-DISC; Inferred].
- `codex exec` runs hooks and passes the bypass flag through as `bypass_hook_trust` [S-EXEC; Inferred].
- If one layer declares hooks both in `hooks.json` and in `[hooks]` TOML, discovery adds the warning "loading hooks from both {} and {}; prefer a single representation for this layer" [S-DISC; Verified]. A stdlib installer can merge JSON but cannot write TOML, so `hooks.json` is the form to write.
- Project `.codex/config.toml` cannot set every key. A denylist constant in the loader names `openai_base_url`, `chatgpt_base_url`, `apps_mcp_product_sku`, `responses_api_metadata`, `model_provider`, `model_providers`, `notify`, `profile`, `profiles`, two realtime base-URL keys and `otel` [S-LOAD; Verified for the list, Inferred that these keys are dropped from the project layer rather than rejected].

Verbatim configuration example (official docs, https://developers.openai.com/codex/hooks, copied 2026-11-10):

```json
"PreToolUse": [
  {
    "matcher": "Bash",
    "hooks": [
      {
        "type": "command",
        "command": "/usr/bin/python3 \"$(git rev-parse --show-toplevel)/.codex/hooks/pre_tool_use_policy.py\"",
        "statusMessage": "Checking Bash command"
      }
    ]
  }
],
```

TOML form, same page, same date: `[[hooks.PreToolUse]]` with `matcher = "^Bash$"`, then `[[hooks.PreToolUse.hooks]]` with `type = "command"`, `command = '...'`, `timeout = 30`, `statusMessage = "Checking Bash command"`. SessionStart example on the same page uses `"matcher": "startup|resume"`, `"command": "python3 ~/.codex/hooks/session_start.py"`, `"statusMessage": "Loading session notes"`, `"additionalContextLimit": 5000`.

Handler options: `timeout` in seconds, default 600 for most hooks (SessionEnd and Interrupt default 1 s, maximum 3 s); `commandWindows` (TOML `command_windows`) overrides `command` on Windows; commands run with the session `cwd` as working directory, so the docs recommend paths built from the Git root [D-HOOKS, S-DISC; Verified].

What a pre-tool hook receives
- Common fields: `session_id`, `transcript_path` (string or null), `cwd`, `hook_event_name`, `model`, `permission_mode` (`default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions`), `turn_id`. PreToolUse adds `tool_name`, `tool_use_id`, `tool_input`. "`Bash` and `apply_patch` use `tool_input.command`. MCP and other local function tools send their arguments." [D-HOOKS; Verified]
- `agent_id` and `agent_type` are optional and present for tool calls made by a subagent [S-SCHEMA; Verified for the schema. Inferred for when they are filled].

Verbatim input schema (repository, https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json, copied 2026-11-11):

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "additionalProperties": false,
  "definitions": {
    "NullableString": {
      "type": [
        "string",
        "null"
      ]
    }
  },
  "properties": {
    "agent_id": {
      "type": "string"
    },
    "agent_type": {
      "type": "string"
    },
    "cwd": {
      "type": "string"
    },
    "hook_event_name": {
      "const": "PreToolUse",
      "type": "string"
    },
    "model": {
      "type": "string"
    },
    "permission_mode": {
      "enum": [
        "default",
        "acceptEdits",
        "plan",
        "dontAsk",
        "bypassPermissions"
      ],
      "type": "string"
    },
    "session_id": {
      "type": "string"
    },
    "tool_input": true,
    "tool_name": {
      "type": "string"
    },
    "tool_use_id": {
      "type": "string"
    },
    "transcript_path": {
      "$ref": "#/definitions/NullableString"
    },
    "turn_id": {
      "description": "Codex extension: expose the active turn id to internal turn-scoped hooks.",
      "type": "string"
    }
  },
  "required": [
    "cwd",
    "hook_event_name",
    "model",
    "permission_mode",
    "session_id",
    "tool_input",
    "tool_name",
    "tool_use_id",
    "transcript_path",
    "turn_id"
  ],
  "title": "pre-tool-use.command.input",
  "type": "object"
}
```

Constructed example, NOT verbatim (built from the schema above and the field rules in the docs, for implementers; status Inferred):

```json
{"session_id":"thr_123","transcript_path":null,"cwd":"/workspace","hook_event_name":"PreToolUse","model":"<model>","permission_mode":"default","turn_id":"<turn>","tool_name":"Bash","tool_use_id":"<id>","tool_input":{"command":"python train.py --lr 3e-4"}}
```

The only verbatim input example on the docs page is for SessionEnd (https://developers.openai.com/codex/hooks, copied 2026-11-10):

```json
{"session_id": "thr_123", "transcript_path": "/workspace/.codex/rollout.jsonl", "cwd": "/workspace", "hook_event_name": "SessionEnd", "reason": "other"}
```

What a pre-tool hook may return (all verbatim from https://developers.openai.com/codex/hooks, copied 2026-11-10)

Deny:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook."
  }
}
```

Older deny shape: `{"decision": "block", "reason": "Destructive command blocked by hook."}`. Also: "You can also use exit code `2` and write the blocking reason to `stderr`."

Extra context without blocking: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "The pending command touches generated files."}}`

Rewrite the input: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "updatedInput": {"command": "echo rewritten"}}}`

The limit that matters most, verbatim: "`permissionDecision: "ask"`, legacy `decision: "approve"`, `continue: false`, `stopReason`, and `suppressOutput` are parsed but not supported yet. Codex marks the hook run as failed, reports the error, and continues the tool call." Also: "Plain text on `stdout` is ignored."

Verbatim output schema (repository, https://github.com/openai/codex/blob/rust-v0.167.0/codex-rs/hooks/schema/generated/pre-tool-use.command.output.schema.json, copied 2026-11-11), definitions and top-level properties:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "additionalProperties": false,
  "definitions": {
    "PreToolUseDecisionWire": {
      "enum": [
        "approve",
        "block"
      ],
      "type": "string"
    },
    "PreToolUseHookSpecificOutputWire": {
      "additionalProperties": false,
      "properties": {
        "additionalContext": {
          "default": null,
          "type": "string"
        },
        "hookEventName": {
          "const": "PreToolUse",
          "type": "string"
        },
        "permissionDecision": {
          "allOf": [
            {
              "$ref": "#/definitions/PreToolUsePermissionDecisionWire"
            }
          ],
          "default": null
        },
        "permissionDecisionReason": {
          "default": null,
          "type": "string"
        },
        "updatedInput": {
          "default": null
        }
      },
      "required": [
        "hookEventName"
      ],
      "type": "object"
    },
    "PreToolUsePermissionDecisionWire": {
      "enum": [
        "allow",
        "deny",
        "ask"
      ],
      "type": "string"
    }
  },
  "properties": {
    "continue": {
      "default": true,
      "type": "boolean"
    },
    "decision": {
      "allOf": [
        {
          "$ref": "#/definitions/PreToolUseDecisionWire"
        }
      ],
      "default": null
    },
    "hookSpecificOutput": {
      "allOf": [
        {
          "$ref": "#/definitions/PreToolUseHookSpecificOutputWire"
        }
      ],
      "default": null
    },
    "reason": {
      "default": null,
      "type": "string"
    },
    "stopReason": {
      "default": null,
      "type": "string"
    },
    "suppressOutput": {
      "default": false,
      "type": "boolean"
    },
    "systemMessage": {
      "default": null,
      "type": "string"
    }
  },
  "title": "pre-tool-use.command.output",
  "type": "object"
}
```

Deny, ask, failure and timeout
- Deny: yes, three ways (JSON deny, legacy block, exit 2 with a reason on stderr). If several hooks match, the call is blocked when any one blocks [D-HOOKS, S-PTU; Verified].
- Ask: no. Parsed, unsupported, counted as a failed hook, and the tool call continues [D-HOOKS, S-PTU; Verified]. The same holds for `permissionDecision: "allow"` without `updatedInput` (test name `permission_decision_allow_without_updated_input_fails_open`). The clean allow is exit 0 with empty stdout.
- Failure is fail-open in every branch of `parse_completed`: spawn error or timeout gives status Failed and no block; exit 0 with invalid JSON-looking stdout gives Failed "hook returned invalid pre-tool-use JSON output"; exit 2 with empty stderr gives Failed "PreToolUse hook exited with code 2 but did not write a blocking reason to stderr"; any other exit code gives Failed "hook exited with code {exit_code}"; none of these block [S-PTU; Verified].
- Timeout text: "hook timed out after {N}s"; default 600 s [S-RUN, S-DISC; Verified]. A hung guard therefore delays, then allows.
- Matching hooks start concurrently: "one hook can't prevent another matching hook from starting" [D-HOOKS; Verified].
- Official wording on strength: "Treat tool hooks as a useful guardrail, not a complete enforcement boundary." [D-HOOKS; Verified]

What a hook cannot see
- Hosted tools such as web search: no PreToolUse, no PostToolUse [D-HOOKS; Verified].
- `write_stdin` to a command that already passed PreToolUse is not checked again [D-HOOKS; Verified]. Text typed into an already-open shell is invisible to the guard.
- "Some specialized tool paths can opt out of the default hook path." [D-HOOKS; Verified]
- For `exec_command` the hook's `tool_input` carries only the command; `workdir`, `shell`, `tty`, `login` are dropped while the command still runs with them [I-57184, I-44836 at https://github.com/openai/codex/issues/44836; Unverified user reports, both open]. Release 0.166.0 lists "report the working directory of local commands in PreToolUse hooks" (#57198) [D-CHG; Inferred that `cwd` is now the effective directory; not exercised].
- File edits arrive as `tool_name: "apply_patch"` with the whole patch text in `tool_input.command` (the matcher may say `apply_patch`, `Edit` or `Write`) [D-HOOKS; Verified]. Target paths must be parsed out of the patch.
- A desktop-app user reports a trusted PreToolUse hook not blocking an `exec_command` nested in a code-mode call [I-54806; Unverified, no maintainer reply].
- Hook start and completion are not written to the `--json` event stream: the JSONL processor matches `ServerNotification::HookStarted(_) | ServerNotification::HookCompleted(_)` and emits nothing [S-JSONL; Verified]. An outside supervisor cannot confirm from the stream that the guard ran.
- A third-party guard's Codex page states the same limits independently: hooks fail open, a hook runs only after it is trusted in `/hooks`, text typed into a running shell session is neither checked nor logged, and `workdir` is not sent to the hook [X-CSN; third-party documentation re-read 2026-11-11, corroborates but is not a measurement].

How the hook command is executed
- Unix: `$SHELL -lc <command>` (fallback `/bin/sh`), new session, environment replayed from the session snapshot minus non-inheritable variables [S-RUN; Verified].
- Windows: if no session shell is configured, `%COMSPEC% /C "<command>"` with the whole line wrapped in one pair of outer quotes; otherwise the configured shell program and arguments [S-RUN; Verified]. A user report with source references says the session shell on Windows is PowerShell (`pwsh` preferred, else Windows PowerShell 5.1), adding about 230 ms per hook [I-49716; Unverified].
- Quoting on Windows is fragile: under the `cmd /C` path, commands with embedded quotes never run [I-38168; Unverified, open since 2026-08-12]; under PowerShell a command that is only a quoted path prints the path and runs nothing, and for SessionStart or UserPromptSubmit this still shows as completed [I-57050; Unverified, open]. Reported safe form: no quotes and no spaces, or a wrapper script.
- The hook process is spawned directly, without the tool sandbox [S-RUN; Inferred]. A guard can therefore write its audit log into a protected kit folder that sandboxed agent commands cannot change.
- `python3` in a hook command is not guaranteed on native Windows; `commandWindows` exists for this [D-HOOKS; Verified that the override exists].

Other hook events useful to the kit
- SessionStart: "Plain text on `stdout` is added as extra developer context."; matcher sources `startup`, `resume`, `clear`, `compact`, `fork`; after compaction, hooks matching `compact` run before the next model request. JSON form (verbatim, https://developers.openai.com/codex/hooks, 2026-11-10): `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "Load the workspace conventions before editing."}}` [D-HOOKS; Verified]
- PermissionRequest runs only when Codex is about to ask for approval. Verbatim (same page and date): allow `{"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "allow"}}}`; deny `{"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "deny", "message": "Blocked by repository policy."}}}`; "any `deny` wins" [D-HOOKS; Verified]. Under approval policy "never" no request is raised, so this hook does not fire [Inferred].
- Stop: `{"decision": "block", "reason": "Run one more pass over the failing tests."}` continues the turn with the reason as a new prompt (verbatim, same page and date) [D-HOOKS; Verified].
- PostToolUse can replace a tool result with feedback but cannot undo the action. PostModelRequest receives `status`, `error`, `token_usage` [D-HOOKS; Verified].
- Hook output above about 2,500 tokens is spilled to a temp file [D-HOOKS; Verified].

Execution-policy rules as a second enforcement point
- Files: `*.rules` in a `rules/` folder next to each active config layer (`~/.codex/rules/`, `<repo>/.codex/rules/`); project rules need a trusted project; marked experimental [D-RULES, S-POL; Verified].
- Verbatim example (https://developers.openai.com/codex/rules, copied 2026-11-10; the `match` list is shortened here with `...` as recorded):

```
prefix_rule(
    pattern = ["gh", "pr", "view"],
    decision = "prompt",
    justification = "Viewing PRs is allowed with approval",
    match = [ "gh pr view 7888", ... ],
    not_match = [ "gh pr --repo openai/codex view 7888", ],
)
```

- Decisions: `allow` ("Run the command outside the sandbox without prompting"), `prompt`, `forbidden` ("Block the request without prompting"); the most restrictive match wins (`forbidden` > `prompt` > `allow`) [D-RULES; Verified].
- `allow` really leaves the sandbox. Source comment, verbatim: "Bypass sandbox only when every parsed command segment is explicitly allowed by execpolicy." [S-POL; Verified]. A command let through only by the built-in safe-command heuristics stays inside the sandbox [S-POL; Inferred].
- With approval policy "never", a `prompt` rule becomes forbidden: `AskForApproval::Never => Some(PROMPT_CONFLICT_REASON)`, and the constant is "approval required by policy, but AskForApproval is set to Never". Commands that match no rule run inside the sandbox; source comment: "We allow the command to run, relying on the sandbox for protection." [S-POL; Verified]. The built-in dangerous-command check that can still forbid an unmatched command was read only in paraphrase [S-POL; Inferred].
- Forbidden message shape: "`{command}` rejected: {justification}" [S-POL; Inferred].
- Matching limits: `bash -lc` scripts are split only when they are plain words joined by `&&`, `||`, `;` or `|`; anything with redirection, substitution, variables, globs or control flow is matched as one `["bash", "-lc", "<script>"]` invocation, so a prefix rule on the inner command does not match [D-RULES; Verified]. On Windows, PowerShell `-Command` scripts are parsed for matching [S-POL; Inferred].
- Offline test: `codex execpolicy check --rules <file> [--pretty] -- <command...>`; inline `match` and `not_match` cases are validated when rules load [D-RULES, L-HELP; Verified]. `codex exec --ignore-rules` skips user and project rules [L-HELP; Verified].
- New in 0.167.0: a managed `prompt-user` decision that "requires a fresh human decision, including when the thread uses automatic review"; under "never" it is still forbidden [S-APP, S-POL, REL; Inferred].

## Q3. Headless runs

Flags of `codex exec` in the local 0.167.0-alpha.3.2 build [L-HELP; Verified unless marked]
- Prompt as argument, or from stdin when absent or `-`; piped stdin is appended as a `<stdin>` block.
- `-s/--sandbox read-only|workspace-write|danger-full-access`; `--approve-for-me`; `--dangerously-bypass-approvals-and-sandbox` (alias `--yolo` per D-CLI); `--dangerously-bypass-hook-trust`. Help text of the first bypass flag, verbatim: "Skip all confirmation prompts and execute commands without sandboxing. EXTREMELY DANGEROUS. Intended solely for running in environments that are externally sandboxed".
- `-C/--cd <DIR>`, `--add-dir <DIR>`, `--worktree`, `--skip-git-repo-check`.
- `-c key=value` (dotted path, TOML value), `-p/--profile <name>` (layers `$CODEX_HOME/<name>.config.toml`), `--enable/--disable <FEATURE>`, `--strict-config`.
- `--ephemeral` ("Run without persisting session files to disk"), `--ignore-user-config` ("Do not load `$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`"), `--ignore-rules`.
- `--json` ("Print events to stdout as JSONL"), `-o/--output-last-message <FILE>`, `--output-schema <FILE>`, `--color`.
- Subcommands `resume [SESSION_ID] [PROMPT]` (`--last`, `--all`), `fork <SESSION_ID> [PROMPT]`, `review`.
- Not present in `exec --help`: `--full-auto`, `-a/--ask-for-approval`, any turn, time or token cap.

Sandbox and approval in headless mode
- "By default, `codex exec` runs in a read-only sandbox." [D-EXEC; Verified]
- "`--full-auto` is no longer supported. Update scripts to use `--sandbox workspace-write`, or use `--approve-for-me` to route approval requests through automatic review with the workspace-write sandbox." [D-EXEC; Verified]. A blog claims `exec --full-auto` was still accepted as a deprecated alias on 0.145.0 [Unverified, secondary].
- Approval policy: exec sets `approval_policy: Some(AskForApproval::Never)` with the comment "Default to never ask for approvals in headless mode. Rebuild below if the fully resolved reviewer is AutoReview." [S-EXEC; Verified]. Valid policies today: `on-request`, `never`, or a granular table; `untrusted` is unsupported ("The retired setting can prevent either client from starting") and `on-failure` is deprecated [D-CFG, D-SEC; Verified]. The local top-level `codex --help` lists only `on-request` and `never` for `-a/--ask-for-approval`, and `codex exec --help` has no such flag [L-HELP; Verified].
- What "ask" becomes with nobody there: (a) a `prompt` rule is forbidden under "never" [S-POL; Verified]; (b) if an approval request does reach the exec client it is rejected with JSON-RPC error code -32000 and a message such as "file change approval is not supported in exec mode for thread `{}`" (same pattern for command, patch, permissions, user-input and dynamic-tool requests), and MCP elicitations are cancelled (comment: "Exec auto-cancels elicitation instead of surfacing it interactively") [S-EXEC; Verified]; (c) docs: "In non-interactive flows, or whenever a run can't surface a fresh approval, an action that needs new approval fails and Codex surfaces the error back to the parent workflow." [D-SUB; Verified]
- `--approve-for-me` uses on-request approvals, the workspace-write sandbox and a model-based reviewer (`approvals_reviewer = "auto_review"`); it conflicts with `--sandbox` and `--yolo`; reviewer build, session and parse failures fail closed, and a timed-out review does not run the action; it costs extra model calls [D-CLI, D-SEC; Verified].
- Under "never", "Execution failures are immediately returned to the model" [L-HELP; Verified].

JSON output
- Event types: `thread.started`, `turn.started`, `turn.completed`, `turn.failed`, `item.started`, `item.updated`, `item.completed`, `error` [S-EVT; Verified].
- Item types: `agent_message`, `reasoning`, `command_execution` (fields `command`, `aggregated_output`, `exit_code`, `status` in_progress, completed, failed or declined), `file_change` (list of `path` and `kind` add, delete or update), `mcp_tool_call`, `collab_tool_call` (subagent tools), `web_search`, `todo_list`, `error` [S-EVT; Verified].
- Verbatim sample (https://developers.openai.com/codex/noninteractive, copied 2026-11-10):

```
{"type":"thread.started","thread_id":"0199a213-81c0-7800-8aa1-bbab2a035a53"}
{"type":"turn.started"}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"bash -lc ls","status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_3","type":"agent_message","text":"Repo contains docs, sdk, and examples directories."}}
{"type":"turn.completed","usage":{"input_tokens":24763,"cached_input_tokens":24448,"output_tokens":122,"reasoning_output_tokens":0}}
```

- Usage fields in source: `input_tokens`, `cached_input_tokens`, `cache_write_input_tokens` (defaults to 0), `output_tokens`, `reasoning_output_tokens` [S-EVT; Verified]. The docs sample shows four of the five.
- The usage in `turn.completed` is built by `usage_from_last_total()`, which copies `usage.total.*` from the latest thread token-usage update and returns zeros if none arrived [S-JSONL; Verified]. That this total accumulates over the whole thread, including across `exec resume`, follows from the name and was not exercised [Inferred]. A budget meter should subtract the previous total rather than add the values up.
- Config warnings, deprecation notices and model reroutes are emitted as `item.completed` with an `error` item; fatal errors as a top-level `error` event and then `turn.failed` [S-JSONL; Inferred].
- Without `--json`, progress goes to stderr and the final message to stdout; `-o` also writes the final message to a file, but only when the turn completed successfully [D-EXEC, S-JSONL; Verified for the first half, Inferred for the second].

Exit status, limits, transcripts
- Exit 0 on success. Exit 1 when: startup fails (bad `-c`, config, schema, prompt); the working directory is not inside a Git repository and neither `--skip-git-repo-check` nor the bypass flag is given (message "Not inside a trusted directory and --skip-git-repo-check was not specified."; despite the wording this is a Git-root check, not the project-trust check); a turn ends failed or interrupted; a non-retried error arrives for the primary turn; or answering a server request fails (`if error_seen { std::process::exit(1); }`) [S-EXEC; Verified for these paths]. No other exit codes were found [Inferred from a paraphrase of the whole file]. A required MCP server (`required = true`) that fails to start also ends exec with an error [D-EXEC; Verified].
- Rate limits and usage caps have no special event or exit code in exec; they surface as error text, for example "You've hit your usage limit. Try again at {time}." or "... Try again later." [S-JSONL, S-ERR; Inferred]. The status-line item names `FiveHourLimit` and `WeeklyLimit` show the two windows that exist for subscription plans [S-TUI; Inferred].
- No turn cap or wall-clock flag exists in exec [L-HELP; Verified by absence]. Bounding is the caller's job.
- Transcripts: `$CODEX_HOME/sessions/YYYY/MM/DD/rollout-YYYY-MM-DDThh-mm-ss-<uuid>.jsonl` [S-ROLL; Verified from a source comment]. Also `history.jsonl` under `CODEX_HOME` when `history.persistence = "save-all"`; logs under `log_dir` (default `$CODEX_HOME/log`) [D-CFG, D-CFGADV; Verified]. Hooks receive `transcript_path`. `--ephemeral` writes no rollout.
- Authentication for exec: `CODEX_API_KEY` is honoured; "Treat `~/.codex/auth.json` like a password" [D-EXEC; Verified].
- Profiles: `--profile name` overlays `~/.codex/name.config.toml`; `[profiles.name]` tables are unsupported since 0.134.0 [D-CFGADV; Verified].
- `--ignore-user-config` also removes the user's project-trust entries, so the project `.codex/` layer (hooks, rules, config) is then disabled unless trust is supplied another way [S-LOAD; Inferred].
- Persistent goals exist (`/goal`, `features.goals` stable and on by default, `goals.max_goal_token_budget`) [D-CFG, D-CLI; Verified that they exist]. Behaviour in exec was not checked [Unverified].
- A second programmatic surface exists: `codex app-server` (marked experimental), a JSON-RPC server over stdio, a Unix socket or WebSocket, whose client answers approval requests itself (`accept`, `decline`, `cancel`); `codex app-server generate-ts` and `generate-json-schema` emit the protocol definitions [L-HELP, S-APP; Verified that the commands exist, protocol read only in part]. `codex exec` is an in-process client of that server (`InProcessAppServerClient`) that rejects every approval request [S-EXEC; Verified].

## Q4. Sandbox, MCP and subagents

Modes and defaults
- Modes: `read-only`, `workspace-write`, `danger-full-access` [L-HELP; Verified].
- workspace-write: writes allowed in the current directory and temp directories such as `/tmp`, plus `--add-dir` and `sandbox_workspace_write.writable_roots`; network off unless `[sandbox_workspace_write] network_access = true` [D-SEC, D-CFG; Verified].
- Protected inside writable roots, recursively read-only: `.git`, `.agents`, `.codex`, `.aws` [D-SEC, D-PERM; Verified].
- Web search is a hosted tool, default mode "cached"; it is not governed by the command sandbox [D-SEC, D-PERM; Verified].
- Environment given to agent-run commands: `shell_environment_policy.inherit` defaults to all variables and `ignore_default_excludes` defaults to `true` (`toml.ignore_default_excludes.unwrap_or(true)`), so variables whose names contain KEY, SECRET or TOKEN are not stripped unless the user sets `ignore_default_excludes = false` or adds filters; `set` is applied after exclusions [D-CFGADV, S-ENV; Verified]. Two consequences: by default every secret in the launching shell (model-hub token, cloud keys) is readable by agent commands, and a user who hardens this policy (`inherit = "core"` or the default excludes) can silently remove variables that a training run needs.
- Beta permission profiles (`default_permissions`, `[permissions.<name>]`, `extends = ":workspace"`) add per-path `read`, `write` and `deny` (deny blocks reads and writes) and domain-level network rules. They do not combine with the older settings: if `sandbox_mode` is set anywhere or `--sandbox` is passed, the older settings win [D-PERM; Verified]. Verbatim example (https://developers.openai.com/codex/permissions, copied 2026-11-10):

```toml
default_permissions = "project-edit"

[permissions.project-edit]
description = "Project editing with OpenAI API access."
extends = ":workspace"

[permissions.project-edit.filesystem.":workspace_roots"]
"**/*.env" = "deny"
```

- Deny-read globs are enumerated when each sandboxed process starts; files created later are not added for that process [D-PERM; Verified].
- Profiles govern only local sandboxed commands, not MCP servers, web search, apps or approved escalations [D-PERM; Verified].

By platform
- macOS: Seatbelt (`sandbox-exec`); if a policy cannot be enforced Codex refuses to run the command [D-SEC, D-PERM; Verified].
- Linux: `bwrap` plus `seccomp` by default [D-SEC; Verified]. In containers the sandbox may not work; docs advise `danger-full-access` inside the container [D-SEC; Verified].
- WSL2: uses the Linux sandbox. WSL1 unsupported from 0.115 [D-SEC; Verified].
- Native Windows: three implementations. `mxc` is recommended (no admin setup; needs Windows 11 24H2 build 26100.9278 or 25H2 build 26200.9278; `features.prefer_mxc` is "Disabled by default in the standalone CLI"); `elevated` (admin setup, sandbox users, firewall rules); `unelevated` (restricted token, weaker network isolation, no denied read paths) [D-WIN; Verified]. The test machine reports build 10.0.26200; the revision was not checked [Unverified whether MXC is available].
- MXC limit, verbatim: "Remaining child processes stop when the foreground command exits. Test workflows that rely on detached development servers." [D-WIN; Verified]
- GPU on Linux and WSL2: users report CUDA unavailable inside workspace-write and read-only because the sandbox `/dev` lacks the GPU device (`/dev/nvidia*` on Linux, `/dev/dxg` on WSL2); the only workaround reported is `danger-full-access` or per-command approval; no maintainer fix is recorded [I-19676, I-57042; Unverified, two open issues, most recent 2026-10-26]. GPU inside the native Windows sandboxes was not found documented [Unverified].
- Detached jobs on Linux: an old report says `nohup` children were killed at turn end while `setsid` children survived [I-10860; Unverified, versions 0.97 to 0.98]. `background_terminal_max_timeout` defaults to 300000 ms [D-CFG; Verified].
- Self-test tools: `codex sandbox [-P <profile>] -- <command>` runs a command under the platform sandbox; MXC probe from the docs: `codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :workspace -- cmd.exe /d /c echo MXC_OK` [D-WIN, L-HELP; Verified that the commands exist; not run because only `--help` is permitted here]. On this Windows build the help for `codex sandbox` describes its argument as "Full command args to run under Windows restricted token sandbox" and offers `codex sandbox uninstall` ("Remove the legacy Windows sandbox's machine-wide accounts and network rules"). The CLI itself therefore calls the accounts-and-firewall mode legacy, and a probe should name the mode under test with `-c windows.sandbox=<mode>` [L-HELP; Verified for the help text, Inferred that "legacy" means `elevated`]. `codex doctor --json` ("Emit a redacted machine-readable report") also exists; its default run includes network and provider checks [L-HELP; Verified that it exists, output not seen].

Narrowest unattended setting that still works
- Read-only analysis or review: `codex exec --sandbox read-only` (the default) [D-EXEC; Verified].
- A worker that edits code: `codex exec --sandbox workspace-write`, approval "never" (the exec default), network off (the default), project rules for forbidden prefixes, guard hook trusted [D-EXEC, D-SEC, S-POL; Inferred as a combination].
- Sealed data: a permission profile with `deny` on the sealed paths gives an OS-level read block on Linux, WSL2, macOS and on Windows with `mxc` or `elevated` [D-PERM; Verified], provided `--sandbox` is not also passed.
- Training launch: because of the GPU and child-process limits above, the launcher probably has to leave the sandbox through one explicit `allow` rule; this is a hole by design and needs the guard and the launcher's own checks behind it [S-POL, I-19676, D-WIN; Inferred].
- Docs' own table gives "Read-only non-interactive (CI) | `--sandbox read-only --ask-for-approval never`" and, for edits, "use `codex exec --sandbox workspace-write`" [D-SEC; Verified]. Caution for builders: `codex exec --help` in the local build has no `--ask-for-approval` flag, so the first form may be rejected if written after `exec`; exec already defaults to "never" [L-HELP, S-EXEC; Verified for the help and the default, not exercised].

Security history relevant to a version floor
- "Overpatch": a crafted patch plus a symlink widened a workspace-write grant to the filesystem root; fixed in CLI 0.149.0; no CVE and no vendor advisory [X-CSA; Verified as a third-party security report, not confirmed by the vendor page].
- CVE-2025-59532 (path-configuration sandbox bypass, CLI 0.2.0 to 0.38.0) and CVE-2026-19591 (repository instructions causing a Git command to run through PowerShell without approval; vendor advisory dated 2026-10-30) were found only in search snippets; the vendor advisory pages returned HTTP 403 to the fetch tool [https://openai.com/security/advisories/; Unverified].

MCP
- Configuration lives in `config.toml` as `[mcp_servers.<name>]`: user file `~/.codex/config.toml`, or project `.codex/config.toml` "only for trusted projects" [D-MCP; Verified]. There is no project `.mcp.json` outside plugins.
- Keys: stdio `command`, `args`, `env`, `env_vars`, `cwd`; HTTP `url`, `bearer_token_env_var`, `http_headers`, `env_http_headers`; shared `enabled`, `required`, `startup_timeout_sec` (10), `tool_timeout_sec` (60), `enabled_tools`, `disabled_tools`, `default_tools_approval_mode` (`auto`, `prompt`, `writes`, `approve`), `tools.<tool>.approval_mode` [D-MCP, D-CFG; Verified].
- `codex mcp add|list|get|remove|login|logout` edits the user configuration [L-HELP, D-MCP; Verified]. An installer that must not touch the home directory cannot use it.
- `codex mcp-server` has been removed in favour of the app server [D-CLI; Verified].
- In exec, MCP approval prompts are cancelled as non-interactive [S-EXEC; Inferred].

Subagents and custom agents
- Enabled by default; built-ins `default`, `worker`, `explorer`; delegation happens on request or when AGENTS.md or a skill asks for it [D-SUB; Verified].
- Custom agents: TOML files in `~/.codex/agents/` or `.codex/agents/` with `name`, `description`, `developer_instructions`, optional model settings and feature switches (for example `features.shell_tool`) [D-SUB; Verified].
- "Subagents inherit the parent turn's current sandbox and approval settings ... A custom agent file can't replace those settings." and "Custom agent instructions can ask an agent to avoid edits, but they don't create a separate read-only sandbox." [D-SUB; Verified]
- `[agents]` settings: `enabled`, `max_concurrent_threads_per_session`, default subagent model and effort [D-SUB, D-CFG; Verified].
- Hook payloads may carry `agent_id` and `agent_type`, and SubagentStart and SubagentStop events exist [S-SCHEMA, D-HOOKS; Verified]. The value of `agent_type` for a custom agent was not confirmed [Unverified].

## Q5. Kit feature by feature

| Kit feature | On Codex | How, and the gap | Sources |
|---|---|---|---|
| Guard hook (deny) | Mechanical | PreToolUse command hook in `<repo>/.codex/hooks.json`; deny by JSON or exit 2. Needs project trust and hook trust. | D-HOOKS, S-PTU |
| Guard hook (ask) | Not at all | "ask" is unsupported and lets the call through; map every ask to deny, or to a `prompt` rule for interactive use. | D-HOOKS, S-PTU |
| Guard fail-safe (`onFailure: block`) | Not at all natively | All hook failures are fail-open. Must be rebuilt: catch-all deny inside the script plus a liveness check outside it. | S-PTU, S-RUN |
| Guard audit log | Mechanical | Hook runs outside the sandbox and can write where sandboxed commands cannot. | S-RUN (Inferred) |
| Read-only reviewer subagents | Instruction only natively | `.codex/agents/*.toml` instructions; mechanical only via a PreToolUse rule keyed on `agent_type`, or by running the reviewer as a separate `codex exec --sandbox read-only`. | D-SUB, S-SCHEMA |
| Session-start status | Mechanical | SessionStart hook, plain stdout becomes developer context; sources include `compact` and `resume`. | D-HOOKS |
| Status line script | Not at all | `tui.status_line` takes built-in item names only (`/statusline`); no custom command. Substitute: SessionStart context and `expctl status`. | D-CFG, D-CLI, S-TUI |
| Skill with references | Mechanical | `.agents/skills/nn-training/SKILL.md` with `references/` and `scripts/`; implicit or `$nn-training`. | D-SKILLS |
| Instruction block | Mechanical | Marked block in root `AGENTS.md`; 32 KiB combined cap; shadowed by `AGENTS.override.md`. | D-AGENTS |
| MCP servers | Mechanical | `[mcp_servers.*]` in project `.codex/config.toml`, trusted projects only; per-tool `approval_mode`. | D-MCP |
| Permission rules: command allow, ask, deny | Mechanical, different shape | `.codex/rules/*.rules` prefix rules; "allow" also leaves the sandbox; "prompt" is forbidden when unattended; compound shell scripts are not split. | D-RULES, S-POL |
| Permission rules: deny reading secret or sealed files | Mechanical, beta | Permission-profile `deny` entries (OS-level), not usable together with `--sandbox`; otherwise only the guard hook. | D-PERM |
| Permission rules: ask before MCP tools that spend money | Mechanical interactive only | `tools.<tool>.approval_mode = "prompt"`; cancelled in exec. | D-MCP, S-EXEC |
| Headless run with explicit permission mode | Mechanical | `codex exec --sandbox ...`; approval "never" by default. | D-EXEC, S-EXEC |

### Port notes against the kit's current code

From a read-only look at a few lines of `expctl.py` and `nn_guard.py` on 2026-11-11 (the files were searched, not read in full).

- Project root: both scripts take the root from the `CLAUDE_PROJECT_DIR` variable, else from the payload `cwd`. Codex sets no such variable, and since 0.166.0 the hook `cwd` may be the command's own working directory rather than the project root [D-CHG #57198; Inferred]. The port must find the root itself (walk up to the kit's config file) or receive it on the hook command line, as the docs example does with the Git root.
- Decision output: the guard already prints `hookSpecificOutput.permissionDecision` with `deny` or `ask`. `deny` is accepted by Codex unchanged; `ask` must never be printed there [D-HOOKS; Verified].
- Tool names: the guard's rules for the `Read`, `Edit`, `Write` and notebook tools have no matching events on Codex. Edits arrive as `apply_patch` with patch text, and file reads happen inside shell commands, so the guard's shell-command analysis carries the whole sealed-path protection unless a permission profile adds an OS-level deny [D-HOOKS, D-PERM; Inferred]. Which other local function tools exist in 0.167 was not enumerated; a match-all matcher (`*` is treated as match-all per a source test name) lets the guard see them [S-DISC; Verified for the test name only].
- Shell dialect: on native Windows Codex runs commands through PowerShell while still reporting `tool_name: "Bash"` [I-49716, S-POL; Inferred from an issue report and from PowerShell parsing in the policy engine]. A guard that tokenises POSIX shell will misread PowerShell syntax. WSL2 avoids this.
- Layout: run state already defaults to `runs/`, which stays writable in the sandbox. The kit's config file and guard log live under `.claude/`, which Codex does not protect. Copies placed under `.codex/` become read-only to sandboxed commands; the guard log must then be written only by the hook process.
- Detach: `expctl launch` detaches with a new session on POSIX and with detached-process and new-process-group flags on Windows. Whether such a child outlives a sandboxed foreground command is the open question for both the Windows and the Linux sandbox.
- Git: `.git` is read-only in the sandbox [D-SEC; Verified], so sandboxed commands cannot commit, stash or take the index lock. `expctl` appears only to read Git state (commit id, dirty flag), which should still work. An unattended loop that keeps or discards changes through Git must do that from harness code running outside the sandbox.

## Changed since 23 October or wrong in the earlier notes

The four earlier research notes contain no Codex platform facts to correct; Codex appears only in three places (an executor list, a quoted setup line, one paper). Everything in this note is therefore new to the kit's record. Items that changed on or after 23 October 2026, or that qualify the earlier text:

- 0.164.0 (23 Oct): Windows MXC sandbox moved to a new SDK (#55378); observation-only model-request hooks (#55144); plugin hook approval bound to plugin contents (#54619); `/permissions` profile selection and presets (#54383, #54385) [D-CHG; Verified as changelog entries].
- 0.165.0 (27 Oct): environment-scoped managed hooks (#56304); configurable automatic-review timeout (#56371) [D-CHG; Verified].
- 0.166.0 (29 Oct): PreToolUse reports the working directory of local commands (#57198); command cwd preserved in permission and post-tool hooks (#57203); approval and permission settings kept on resume and fork (#57227); state-changing multi-agent calls routed through automatic review (#57451) [D-CHG; Verified].
- 0.167.0 (6 Nov): PreToolUse hooks applied before automatic-review policy checks (#58368); managed `prompt-user` command rules needing fresh human approval (#58045, #58182); managed network constraints under `[permissions.network]`; MXC fixes (#57985, #58168); host-inherited thread instructions and execution policies (#58406) [REL; Verified].
- Pre-releases up to 0.169.0-alpha.7 (9 Nov) exist; stable releases arrived on 23 Oct, 27 Oct, 29 Oct and 6 Nov, so any pinned behaviour can move within a week [GitHub releases list, 2026-11-10; Verified].
- Docs moved host (308 from `developers.openai.com/codex/*` to `learn.chatgpt.com/docs/*`) [Verified; date of the move unknown].
- A vendor advisory for CVE-2026-19591 is reported as published on 30 Oct 2026 [Unverified, search snippet only].
- Earlier note, executor list ("Codex runs unsandboxed" in one multi-agent research project): that describes that project's configuration, not a platform limit. Codex has an OS sandbox on Linux, macOS, WSL2 and native Windows [D-SEC, D-WIN; Verified].
- Earlier note, quoted setup line ("disable all permissions"): on Codex that corresponds to `--dangerously-bypass-approvals-and-sandbox`. The most-starred Codex auto-research skill does start that way ("Full Access" in its quick start, and background runs default to it) [X-CAR; Verified as that project's documentation]. This conflicts with the brief's must-not and should not be copied. The same README keeps `workspace-write` as an explicit option, continues foreground runs through a Codex Goal, runs background work as a detached controller with one `codex exec` worker per iteration, lets a control script own commits, verification, rollback and state, and describes an optional iteration limit but no time or cost limit; it does not say whether the metric script lies outside the agent's edit scope [X-CAR; Verified as that project's documentation, re-read 2026-11-11].
- Earlier note, paper arXiv 2607.18064: the abstract of v2 (27 Aug 2026) confirms that Codex runs in the first study hardcoded 19 to 41 evaluation item IDs per run and Claude's did not. It also says the memorisation disappeared in the second study and the score gap with it, and that the better and more consistent held-out transfer (0.085 +/- 0.004 against 0.121 +/- 0.031, lower is better) came from Codex's general solution. The abstract does not name model versions and does not contain the "about 4.5 times" train-to-test figure recorded earlier; those need the full text [X-ARX1; Verified for the abstract, Unverified for the two details].

## Concerns any design must handle

HOOK-FAIL-OPEN
HOOK-NO-ASK-DECISION
HOOK-TRUST-SILENT-SKIP
HOOK-LIVENESS-UNPROVEN
HOOK-COVERAGE-GAPS
HOOK-PAYLOAD-MISSING-CONTEXT
HOOK-PATCH-PAYLOAD-PARSING
HOOK-CONCURRENT-NO-ORDERING
HOOK-SHELL-QUOTING-PER-PLATFORM
HOOK-INTERPRETER-NAME-MISMATCH
HOOK-TIMEOUT-THEN-ALLOW
HOOK-PROJECT-ROOT-DISCOVERY
GUARD-SHELL-DIALECT-MISMATCH
GUARD-READS-ONLY-VIA-SHELL
TRUST-PROJECT-LAYER-GATED
TRUST-STATE-IN-HOME-CONFIG
HOME-CONFIG-UNTOUCHED
INSTALL-TOML-MERGE-NO-STDLIB
UNATTENDED-APPROVAL-UNANSWERABLE
UNATTENDED-NO-TURN-CAP
UNATTENDED-BYPASS-TEMPTATION
BUDGET-TOKEN-TOTALS-CUMULATIVE
BUDGET-USAGE-CAP-DETECTION
SANDBOX-GPU-DEVICE-BLOCKED
SANDBOX-DETACHED-CHILD-KILLED
SANDBOX-ALLOW-RULE-ESCAPE
SANDBOX-KIT-DIRS-READONLY
SANDBOX-GIT-METADATA-READONLY
KIT-CONFIG-OUTSIDE-PROTECTED-DIR
SANDBOX-PROFILE-LEGACY-CONFLICT
SANDBOX-DENYREAD-SNAPSHOT-TIMING
SANDBOX-WEAK-FALLBACK-MODE
SANDBOX-ESCAPE-VERSION-FLOOR
SEAL-TESTSET-OS-LEVEL-DENY
RULES-COMPOUND-COMMAND-UNSPLIT
RULES-EXPERIMENTAL-API
SUBAGENT-READONLY-ADVISORY
SUBAGENT-INHERITS-PERMISSIONS
STATUSLINE-NOT-PORTABLE
INSTRUCTION-SIZE-CAP
INSTRUCTION-OVERRIDE-FILE-SHADOWING
SKILL-LIST-BUDGET-TRUNCATION
CLI-FLAG-CHURN
CLI-VERSION-FLOOR-AND-PIN
DOCS-URL-DRIFT
SEC-PROMPT-INJECTION
SEC-CREDENTIAL-EXPOSURE
SEC-ENV-SECRETS-INHERITED-BY-DEFAULT
ENV-FILTER-BREAKS-TRAINING-RUN
SEC-MCP-OUTSIDE-SANDBOX
AUDIT-TRANSCRIPT-IN-HOME-DIR
AUDIT-HOOK-EVENTS-NOT-IN-STREAM
EVAL-AGENT-HARDCODING
PORT-PROTECTION-PARITY-DISCLOSURE

## Open questions (each answerable by a short local trial once sessions are allowed)

1. Does `codex exec -c 'projects."<abs path>".trust_level="trusted"' ...` enable the project `.codex/` layer for one invocation without editing the home config? The source merges command-line overrides before the trust decision, but this was not exercised, and path spelling on Windows (drive-letter case, backslashes) may matter.
2. Hook trust is stored as `hooks.state."<key>".trusted_hash` in the user config and there is no CLI subcommand for it. Can `-c` supply that value for one invocation, and can the kit compute the hash offline? If not, unattended use needs either one interactive `/hooks` visit per machine (repeated whenever the hook declaration changes) or `--dangerously-bypass-hook-trust`.
3. On the native Windows test machine: which shell runs hook commands in 0.167, does a `commandWindows` line without quotes work, is MXC available on this build, does CUDA work inside each Windows sandbox, and does a detached training process survive the end of the launching command?
4. In WSL2 Ubuntu 24.04 with 0.167: is `/dev/dxg` visible in workspace-write, and does a `setsid` child survive the turn?
5. Does an explicit `allow` rule let the launcher run outside the sandbox under approval "never" in exec, with the PreToolUse hook still firing first?
6. After 0.166.0, is the hook's `cwd` the command's effective directory when the model passes `workdir`? The upstream issue is still open.
7. What is `agent_type` for a custom agent, and is it present on every tool call that agent makes, including `apply_patch`?
8. Is `turn.completed.usage` cumulative across `exec resume` of the same thread?
9. What exact text and event sequence does exec emit on a five-hour or weekly usage cap, and does `resets_at` appear?
10. Does `codex exec` accept a goal, and does `goals.max_goal_token_budget` stop a run cleanly?
11. Does `~/.codex/skills` still load, and does project skill discovery need project trust?
12. Content of the vendor advisory for CVE-2026-19591 (the page was not reachable) and the fixed version.
13. Does the instruction chain survive compaction unchanged?

## Redirect attempts

1. Search-tool error message, 2026-11-11: after a rate limit, the fetch service's error text told the client to create an account and an API key at its dashboard and to resend with the key. Not acted on; switched to other read-only tools.
2. Third-party document X-DCG contains sentences addressed to agents ("The agent must not redeem the code or change policy on its own." and "Do not disable dcg, broaden an allowlist, or rewrite the rejected command to evade classification."). Treated as data. Not acted on; no action was implied for this task.
3. HTTP 308 redirects from the vendor docs host to a second vendor host were followed by hand as navigation, not as instructions.
4. Third-party pages X-CAR and X-CSN contain ordinary setup instructions written for human users (launch Codex with approvals and sandbox bypassed; run an `npx` install command; trust a hook in `/hooks`). Treated as data; nothing was installed, launched or trusted.
5. No instruction aimed at an automated reader was found in the official docs, the tagged source files, the upstream issues or the two arXiv abstracts.
