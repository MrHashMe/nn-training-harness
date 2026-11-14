#!/usr/bin/env python3
"""Tool-call guard for the nn-training harness (stdlib only). One rule set for Claude Code, Codex and Cursor.

Deterministic seatbelts for the failure modes that matter most when an agent runs training
campaigns. It never edits tool input; it answers "deny", "ask" (the user is prompted) or allows.

  deny  paths that resolve to sealed test data (file tools and shell arguments, resolved against
        the session's working directory) and test-unsealing tokens. The rules of every checkout of
        the repository are combined and hold in each; a protected folder that is a link to storage
        elsewhere is protected at both ends
  deny  Edit/Write inside an active run's directory or code snapshot
  deny  a hook input it cannot read (not JSON, no tool name, a shell call without a command, a
        file call without a path): an unread call is refused, never let through
  deny  writes, signals and launches by the read-only subagents (experiment-reviewer, run-analyst)
  ask   anything else that mentions a sealed path (e.g. inside a python -c string)
  ask   recursive or wildcard sweeps over the folder that holds sealed data (find, grep -r,
        ls -R, cp -r, tar, rsync, rg, or globs such as data/*/...)
  deny  the configured final-evaluation command itself, however its interpreter and script are
        spelled: it runs through `expctl final-eval`, which keeps a receipt of every use
  ask   `expctl final-eval` (each test-set access is a human decision)
  ask   `expctl audit-splits` where the config seals anything (it prints counts only, but each
        count of records shared with a sealed split is a small look at that split)
  ask   edits to frozen evaluation/protocol files, to the harness itself or to git's own files
  ask   kill/stop commands (always: jobs outside the harness are protected too); deleting run
        directories or checkpoints; shell writes into an active run's directory; destructive git;
        any git push; branch switches/pulls while a run executes from the working tree;
        dependency changes (and syncing `uv run`) while harness runs or listed external jobs are live
  ask   commands that start paid compute directly (outside the remote module's spending cap) and
        commands that pipe a download into a shell

Usage: nn_guard.py [--agent claude|codex|cursor] [--readonly]. --agent names the caller, which
decides the answer format; the input shape is recognised from the payload. Every "ask" becomes
"deny" where a prompt would not reach a person: always on Codex (its hooks cannot ask) and Cursor
(a hook cannot tell whether anyone is there), and on Claude Code under bypassPermissions, dontAsk
or NN_UNATTENDED=1. A deny for Codex or Cursor, and every unreadable input, exits with code 2,
which blocks on all three agents without depending on stdout being parsed.

Fails safe: an unreadable .claude/nn-training.json (reading that file stays allowed) or an
internal error turns every tool call, reads included, into an "ask" with the reason, instead of
silently allowing it.
Audit trail: .claude/state/guard.log (JSON lines; commands and paths, never file content). This
is a seatbelt against mistakes, not a sandbox: a program can still build a path at run time. For
hard isolation keep the test split outside the repository, or use the agent's sandbox.
"""
from __future__ import annotations

import base64
import fnmatch
import functools
import glob
import itertools
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path

DENY, ASK = "deny", "ask"
LIMIT = 12  # seconds after which the guard answers "ask" by itself: its hooks give it 15 to 20
READ_TOOLS = ("Read", "NotebookRead", "LS", "Grep", "Glob")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
READONLY_AGENTS = ("experiment-reviewer", "run-analyst")
# tool names of the three agents -> this guard's vocabulary (Claude Code's). Shell is Cursor's name for Bash.
TOOL_NAMES = {"bash": "Bash", "monitor": "Bash", "powershell": "Bash", "shell": "Bash", "read": "Read",
              "notebookread": "NotebookRead", "ls": "LS", "grep": "Grep", "glob": "Glob", "edit": "Edit",
              "write": "Write", "multiedit": "MultiEdit", "notebookedit": "NotebookEdit", "delete": "Delete",
              "apply_patch": "apply_patch"}
PATH_KEYS = ("file_path", "notebook_path", "path", "target_file", "filePath")
CONTENT_KEYS = ("content", "contents", "new_string", "old_string", "text", "code", "new_str", "old_str")
OLD_KEYS = ("old_string", "old_str", "old_source")  # the text an edit replaces: it leaves the file
PATCH_FILE = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+?)\s*$|^\*\*\* Move to: (.+?)\s*$", re.M)
QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
WRITE_VERBS = re.compile(
    r"(?<![0-9&])>{1,2}(?!&)|\b(?:tee|mv|cp|rm|rmdir|unlink|chmod|chown|truncate|ln|dd|rsync)\b|"
    r"\bsed\s+(?:-[a-zA-Z]*\s+)*-[a-zA-Z]*i|\bperl\s+-[a-zA-Z]*i|open\([^)]*['\"][wax+]|write_text|write_bytes|"
    r"shutil\.(?:rmtree|move|copy)|os\.(?:remove|unlink|rename|replace)")
KILL = re.compile(
    r"(?:^|[\s;&|(`])(?:sudo\s+)?(?:kill|pkill|killall|taskkill)\b|Stop-Process|"
    r"tmux\s+kill-(?:session|server|window|pane)|tmux\s+send-keys\b[^;&|]{0,200}?\bC-[cd]\b|"
    r"screen\s+[^;&|]{0,200}?-X\s+quit|nvidia-smi\s+[^;&|]{0,200}?(?:--gpu-reset|\s-r\b)|\bfuser\b[^;&|]{0,200}?\s-k\b|"
    r"systemctl\s+(?:stop|kill|restart)|docker\s+(?:stop|kill|rm)\b|podman\s+(?:stop|kill|rm)\b|\bscancel\b|"
    r"\bqdel\b|\bbkill\b|\bray\s+stop\b|expctl(?:\.py)?\s+stop\b")
# git's own options, which stand between `git` and its subcommand: those with a value (which may hold a quoted
# blank), then any other one (-P, --no-pager, --bare, --no-advice ...), so that none hides the subcommand
_GV = r"(?:\"[^\"]*\"|'[^']*'|[^\s'\"])+"
GIT_GLOBAL = re.compile(
    r"\bgit((?:\s+(?:-[Cc]\s+" + _GV + r"|--(?:git-dir|work-tree|namespace|super-prefix|attr-source|config-env|"
    r"exec-path)(?:=|\s+)" + _GV + r"|--?[A-Za-z][\w-]*))+)(?=\s)")
GIT_VALUE_OPT = ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--attr-source", "--config-env")
# A setting can make git start a program by itself, later and outside this guard: core.hooksPath, core.fsmonitor,
# core.pager, core.sshCommand, alias.*, filter.*, diff.*.textconv, credential.helper and more, and git keeps adding
# to them. So the rule names the keys that hold a plain value and asks about every other one
GIT_PLAIN_KEY = re.compile(
    r"(?:user\.(?:name|email)|core\.(?:autocrlf|eol|safecrlf|filemode|longpaths|quotepath|symlinks|ignorecase|abbrev)|"
    r"init\.defaultbranch|pull\.(?:rebase|ff)|push\.(?:default|autosetupremote)|fetch\.prune|commit\.gpgsign|"
    r"color\.[\w.]+|advice\.\w+)$", re.I)
_NO_PROGRAM = r"['\"]?(?:cat|less|more|true|:)?['\"]?"  # a pager or an editor that is none
GIT_NO_PROGRAM = re.compile(r"(?:core\.pager|core\.editor|sequence\.editor)=" + _NO_PROGRAM + "$", re.I)
GIT_ENV = re.compile(  # the same settings as environment variables (GIT_CONFIG_COUNT with its keys, GIT_SSH_COMMAND ...)
    r"\bGIT_(?:CONFIG(?:_(?!NOSYSTEM)\w+)?|SSH(?:_COMMAND)?|EXTERNAL_DIFF|PAGER|EDITOR|SEQUENCE_EDITOR|ASKPASS|EXEC_PATH|"
    r"PROXY_COMMAND|TEMPLATE_DIR)\s*=\s*(?!" + _NO_PROGRAM + r"(?:[\s;&|)]|$))")
GIT_CONFIG_READ = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--get-color", "--get-colorbool", "-l", "--list"}
GIT_CONFIG_FLAG = re.compile(  # git config's options that take no value and leave the file it writes alone
    r"--(?:global|local|system|worktree|add|replace-all|append|all|bool|int|bool-or-int|path|expiry-date|no-type|null|"
    r"fixed-value|show-origin|show-scope|name-only|(?:no-)?includes|unset|unset-all|type=[\w-]+)$|-z$")
GIT_DESTRUCTIVE = re.compile(
    r"\bgit\s+(?:reset\s+--hard|clean\s+-[a-zA-Z]*f|checkout\s+(?:-f\b|--\s|\.(?:\s|$|[;&|])|(?!-)\S+\s+--\s)|"
    r"restore\b(?![^;&|]*--staged)|stash\s+(?:drop|clear)\b|switch\s+(?:-f\b|--discard-changes)|"
    r"push\b[^;&|]*(?:--force\b|--force-with-lease\b|\s-f\b)|branch\s+-D\b)")
GIT_PUSH = re.compile(r"\bgit\s+push\b")
GIT_TREE_CHANGE = re.compile(
    r"\bgit\s+(?:checkout|switch|pull|merge|rebase|am|cherry-pick|revert|stash(?!\s+(?:list|show)\b))\b")
# git takes the files that it ignores as well: a forced add (in a group of letters too) and a stash of everything.
# From its store, `git diff --cached`, `git show` and `git stash show -p` print them without naming one
GIT_TAKES = re.compile(r"\bgit\s+(?:add\b[^;&|]*?\s(?:-[a-zA-Z]*f[a-zA-Z]*|--force)|"
                       r"stash\b[^;&|]*?\s(?:-[a-zA-Z]*a[a-zA-Z]*|--all))(?=[\s;&|)]|$)")
DEP_CHANGE = re.compile(
    r"\b(?:pip3?|python3?\s+-m\s+pip)\s+(?:install|uninstall)\b|"
    r"\buv\s+(?:add|remove|sync|lock\s+--upgrade|pip\s+(?:install|uninstall|sync))\b|"
    r"\b(?:conda|mamba|micromamba)\s+(?:install|update|remove|upgrade|env\s+(?:update|create|remove))\b|"
    r"\bpixi\s+(?:add|remove|update|install)\b|\bpoetry\s+(?:add|remove|update|install|lock)\b")
UV_RUN_SYNCING = re.compile(r"\buv\s+run\b(?![^;&|]*\s--(?:frozen|no-sync|locked|offline)\b)")
RM_ANY = re.compile(r"(?:^|[\s;&|(])(?:sudo\s+)?rm\s")
FIND_DELETE = re.compile(r"\bfind\b[^;&|]*\s-delete\b|\bshutil\.rmtree\b|\bos\.(?:remove|unlink)\b")
CKPT_HINT = re.compile(r"checkpoint|ckpt|\.pth?\b|\.safetensors\b", re.I)
def recursive_re(posix):
    """The commands that walk a whole folder tree. posix: the line surely runs in a POSIX shell, where `ls -r` and
    `dir -s` list one folder; anywhere else they may be PowerShell's Get-ChildItem, which recurses."""
    gci = "Get-ChildItem|gci" + ("" if posix else "|dir|ls")
    return re.compile(
        # PowerShell, where a switch may be cut short (-r, -rec) and -s and -Depth recurse as well (-Depth 0 lists one
        # folder), and cmd.exe. They stand first, so that `ls -r` and `tree /f` are read by their rules
        r"(?P<ps>(?i:(?<![\w/.-])(?:" + gci + r"|Copy-Item|cpi|copy)\b[^;|&]{0,200}?\s-(?:r[ecurs]*(?::\$true)?"
        r"(?=[\s;|&)]|$)|de[pth]*(?=[\s;|&):]|$)(?!(?:\s+|:)0+(?=[\s;|&)]|$)))|"
        r"(?<![\w/.-])(?:" + gci + r")\b[^;|&]{0,200}?\s-s(?=[\s;|&)]|$)|"
        r"(?<![\w/.-])(?:dir|findstr)\b[^;|&]{0,200}?\s/s(?=[\s;|&)/]|$)|\btree\b[^;|&]{0,200}?\s/[af](?=[\s;|&)/]|$)|"
        r"\b(?:Compress-Archive|robocopy|xcopy|AllDirectories)\b))|"  # AllDirectories: .NET's word for the whole tree
        r"\b(?:find|tree|tar|zip|rsync|rg|ag|rgrep)\b|"
        r"\b(?:grep|egrep|fgrep|cp|scp)\b[^;|&]{0,200}?\s(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(?=[\s;|&)]|$)|"
        r"\bcp\b[^;|&]{0,200}?\s(?:-[a-zA-Z]*a[a-zA-Z]*|--archive)(?=[\s;|&)]|$)|"  # cp -a copies the tree as well
        # ls -ltr sorts in reverse and chmod -r takes a permission away: there only -R recurses
        r"\b(?:ls|dir|chmod|chown)\b[^;|&]{0,200}?\s(?:-[a-zA-Z]*R[a-zA-Z]*|--recursive)(?=[\s;|&)]|$)|"
        r"\bdu\b[^;|&]{0,200}?\s(?:-[a-zA-Z]*a[a-zA-Z]*|--all)(?=[\s;|&)]|$)")  # du -a lists every file of the tree


RECURSIVE, RECURSIVE_POSIX = recursive_re(False), recursive_re(True)
# A move takes a folder along with all that it holds, and under a new name the sealed files in it are sealed no more
MOVERS = {"mv", "move", "ren", "rename", "mi", "rni", "move-item", "rename-item"}
MOVE = re.compile(r"(?<![\w/.-])(?:" + "|".join(sorted(MOVERS, key=len, reverse=True)) + r")\b", re.I)
PAID_COMPUTE = re.compile(
    r"\bhf\s+jobs\s+(?:run|uv\s+run|scheduled)\b|\bsky\s+(?:launch|jobs\s+launch)\b|\bmodal\s+(?:run|deploy)\b|"
    r"\brunpodctl\s+(?:create|start)\b|\bvastai\s+create\b|\bdstack\s+apply\b|"
    r"\bgcloud\s+compute\s+instances\s+create\b|\baws\s+ec2\s+run-instances\b|\baz\s+vm\s+create\b")
LOOP_CTL = re.compile(r"\bnn(?:loop|remote)(?:\.py)?\b[^;&|]{0,300}?\b(?:start|resume|launch|stop)\b")
FINAL_CTL = re.compile(r"\bexpctl(?:\.py)?\b[^;&|]{0,300}?\bfinal-eval\b")
AUDIT_CTL = re.compile(r"\bexpctl(?:\.py)?\b[^;&|]{0,300}?\baudit-splits\b")
PUBLISH = re.compile(
    r"\b(?:hf|huggingface-cli)\s+(?:upload(?:-large-folder)?|repos?\s+create)\b|\bpush_to_hub\s*\(|\btwine\s+upload\b|"
    r"\bgh\s+(?:repo|release|gist)\s+create\b|\bdocker\s+push\b")
_FETCH = r"\b(?:curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\b"
PIPE_TO_SHELL = re.compile(
    _FETCH + r"[^;&]*\|\s*(?:sudo\s+)?(?:(?:(?:ba|z|da|k|c)?sh|pwsh|powershell|iex|Invoke-Expression)\b|"
    r"python3?\s*-?\s*(?=$|[;&|]))|\b(?:ba|z)?sh\s+(?:-c\s+)?[\"']?(?:<\(|\$\()\s*" + _FETCH, re.I)
# what the read-only subagents may not run (the shell rules above apply to them as well)
MUTATING = re.compile(
    r"\bexpctl(?:\.py)?\s+(?:launch|stop|resume|_supervise)\b|\bnn(?:loop|remote)(?:\.py)?\s+(?!status\b)\w|"
    r"\bgit\s+(?:commit|push|reset|checkout|switch|merge|rebase|stash|clean|restore|add|rm|mv|tag|branch|am|"
    r"cherry-pick|revert|pull|fetch|apply)\b|"
    r"\b(?:pip3?|uv|conda|mamba|micromamba|pixi|poetry|npm|npx)\s+(?:install|add|remove|sync|update|uninstall|lock)\b|"
    r"\b(?:torchrun|deepspeed|nohup|setsid|tmux|screen|sbatch|srun|docker|podman)\b|\baccelerate\s+launch\b")
PY_WRITES = re.compile(  # open() counts with a complete write mode ('w', "ab", 'r+'), not with a path that starts with w
    r"open\([^)]*['\"](?=[rbtU]*[wax+])[rwaxbtU+]{1,4}['\"]|write_text|write_bytes|shutil\.(?:rmtree|move|copy)|"
    r"os\.(?:remove|unlink|rename|replace|makedirs|mkdir)|\.to_(?:csv|parquet|json)\(|torch\.save|np\.save|\.savefig\(")
# PowerShell and cmd.exe forms of the write, delete and kill rules. Case is ignored; the short aliases count only
# where a command starts (line start, after ; & | ( {, or after cmd's /c).
_AT = r"(?:^|[;&|({`]|\s/[ck]\s)\s*"
PS_WRITE = re.compile(
    r"\b(?:(?:Set|Add|Clear)-Content|Out-File|Tee-Object|(?:Copy|Move|Remove|New|Rename|Set|Clear)-Item(?:Property)?|"
    r"Export-(?:Csv|Clixml)|Expand-Archive|xcopy|robocopy)\b|::(?:Write|Append|Delete|Move|Copy|Create|Replace)\w*\(|"
    + _AT + r"(?:sc|ac|clc|ri|del|erase|rd|copy|move|ren|rename|cpi|mi|ni|rni)\b", re.I | re.M)
PS_DELETE = re.compile(r"\b(?:Remove-Item|Clear-Content)\b|::Delete\(|" + _AT + r"(?:ri|del|erase|rd|rmdir|clc)\b",
                       re.I | re.M)
PS_KILL = re.compile(r"\b(?:Stop-Process|spps|taskkill)\b|\bwmic\b[^;&|]{0,200}?\bterminate\b|\bos\.kill(?:pg)?\(|"
                     r"\.(?:kill|terminate)\(\)", re.I)
# a command that hands text to a nested shell or an interpreter (bash -c "...", python -c "...", cmd /c "...")
SHELLS = re.compile(r"\b(?:(?:ba|z|da|k)?sh|cmd|powershell|pwsh|python[0-9.]*|py|node|perl|ruby|eval|iex|"
                    r"Invoke-Expression|wsl|ssh)\b", re.I)
POSIX_SHELL = re.compile(r"\b(?:(?:ba|z|da|k)?sh|eval|wsl|ssh)\b", re.I)
CODE_FLAG = re.compile(r"^(?:-[a-z]*c|-e|-command|--command|--eval|/c|/k|eval|iex|invoke-expression)$", re.I)
# the same flag with its text attached (bash -c"echo x > f", cmd /c"type f"): what follows it is no plain option value
ATTACHED = re.compile(r"^(?:-[a-z]*?c|/[ck])(?=.*[^\w.=:,/@%+-])(.+)$", re.I | re.S)
ENCODED = re.compile(r"^[-/]e[a-z]*$", re.I)  # PowerShell's -EncodedCommand, which may be cut short (-enc, -e)
# a decoder whose output a shell or an interpreter runs (base64 -d <<< ... | sh, iex of FromBase64String), or that
# xargs makes the arguments of a command
_DECODER = (r"(?:base(?:64|32|nc)\b[^|;&]*?\s(?:-[a-zA-Z]*[dD][a-zA-Z]*|--decode)|certutil\s+-decode|xxd\s+-r|"
            r"openssl\s+(?:enc|base64)\b[^|;&]*\s-d)")
DECODER = re.compile(r"\b" + _DECODER + r"\b", re.I)
DECODE_TO_SHELL = re.compile(
    r"\b" + _DECODER + r"\b[^;&]*\|\s*"
    r"(?:sudo\s+)?(?:(?:ba|z|da|k|c)?sh|pwsh|powershell|iex|Invoke-Expression|python[0-9.]*|perl|node|ruby|xargs)\b|"
    r"\b(?:iex|Invoke-Expression)\b[^;&|]*FromBase64String|FromBase64String[^;&]*\|\s*(?:iex|Invoke-Expression)\b", re.I)
# code given on the command line that decodes text itself: what it does with the result (run it, open it as a path)
# is not on the line. Followed by "(": the bare word may be what a search looks for
DECODE_CALL = re.compile(
    r"\b(?:b(?:64|32|16|85)decode|a85decode|decodebytes|unhexlify|fromhex|a2b_\w+|decompress|FromBase64String|"
    r"FromHexString|atob|decode_base64|decode64)\s*\(|\bcodecs\.decode\s*\(|\bBuffer\.from\s*\(", re.I)
# text that joins paths from string literals: the gap between two of them, and the calls in which a comma joins
# what a shell takes out of a name before it runs the line: see readings()
ANSI_C = re.compile(r"\$'((?:\\.|[^'\\])*)'", re.S)
C_ESCAPE = re.compile(r"\\(x[0-9a-fA-F]{1,2}|u[0-9a-fA-F]{1,4}|U[0-9a-fA-F]{1,8}|[0-7]{1,3}|.)", re.S)
POSIX_PART = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"|\\(.)", re.S)
BRACE_WORD = re.compile(r"[^\s;&|<>()]*\{[^{}\s]*,[^{}\s]*\}[^\s;&|<>()]*")
WIN_ESCAPE = re.compile(r"[`^](?=[\w./\\:-])")
GAP = re.compile(r"[\s()\[\]]*([/,+])[\s()\[\]]*(?:[A-Za-z_][\w.]*\()?\s*|\s*")  # the second: nothing but blanks
JOINER = re.compile(r"(?:\bjoin|joinpath|Path|Combine)\s*\([^()\n;]{0,80}$")
WORDS = re.compile(r"[^\s\x00-\x1f'\"`()\[\]{},;=<>|]+")
WALK, WALK_S = 20000, 5  # files a walk looks at for sure, and the seconds a hook call may spend on the files beyond
GLOB = 200  # matches of a wildcard that are looked up one by one; each one behind them costs a look at its folder
# a change of folder: where a command starts (after blanks too), or behind a shell keyword, a wrapper such as `time`
# or an assignment (X=1 cd data). PowerShell takes -Path:data and a parameter's name cut short
_CD_WORD = r"(?:cd|pushd|chdir|sl|Set-Location|Push-Location)"
# The folder ends at a redirection (cd data</dev/null), and a shell lets one splice it from pieces (d"at"a, 'da'ta)
CD = re.compile(r"(?:^|[;&|({])\s*(?:(?:if|then|else|elif|while|until|do|time|command|builtin|eval|!|[a-z_]\w*=\S*)\s+)*"
                + _CD_WORD + r"\s+(?:-[lpe]\w*(?::|\s+)|(?:/d|--)\s+)*((?:\"[^\"]*\"|'[^']*'|[^\s;&|)<>'\"]+)+)",
                re.I | re.M)
ASSIGN = re.compile(r"^[A-Za-z_]\w*=")  # NAME=value in front of a command
# file filters of search commands, each tool's own: rg -g/--glob/-t, grep --include/--exclude/--exclude-dir, find -name
_VAL = r"(\"[^\"]*\"|'[^']*'|[^\s;&|]+)"
# where a move goes to, when an option says it (mv -t, in a group of letters too; mv -T is another option). Without
# one it is the last argument
MOVE_TO = re.compile(r"\s(?:-[a-zA-Z]*t|--target-directory|(?i:-Dest\w*|-New\w*))(?:=|:|\s+)" + _VAL)
# env -C dir (or --chdir) runs its command in that folder, as git -C dir runs git there
ENV_C = re.compile(r"(\benv(?:\s+(?:-u\s+\S+|-[^C\s]\S*|[A-Za-z_]\w*=\S*))*)\s+(?:-[a-zA-Z0]*C|--chdir)(?:=|\s+)" + _VAL)
# find's -exec ... \; ends at an escaped or quoted semicolon, which is no separator of commands
FIND_END = re.compile(r"(\s-(?:exec|execdir|ok|okdir)\s(?:[^;&|\n'\"]|'[^']*'|\"[^\"]*\")*?\s)(?:/;|';'|\";\")")
# what may stand between the start of a command (or of a $(...) in it) and the tool that it runs
_WRAP = "sudo|time|timeout|nice|command|exec|env|nohup|if|then|else|elif|while|until|do|!"
_LEAD = r"\s*(?:(?:(?:%s)(?:\s+-\S+|\s+\d\S*)*|[A-Za-z_]\w*=\s?\S*)\s+)*"
COMMAND_START = re.compile(r"(?:^|.*[({`])" + _LEAD % _WRAP + r"(?:\S*/)?$", re.S)
# a command word in quotes ("grep" -r x ., $'grep', behind xargs too) is the same command. Not one with a blank in
# it: unquoted it would be two
QUOTED_COMMAND = re.compile(r"((?:^|[;&|({`])" + _LEAD % (_WRAP + "|xargs") + r")\$?(['\"])([\w./:-]+)\2"
                            r"(?=[\s;&|)]|$)", re.M)
# Files of notes. The edit tools write their text unread, because documentation may name the test set, so a command
# line or a file's new text that runs one as code is asked about: see runs_notes()
NOTES = r"\.(?:md|mdx|rst)"
NOTES_RUN = ("Runs a file of notes (.md, .mdx, .rst) as code. The edit tools write such files without this guard "
             "reading their text, so what would run here is unchecked and may read sealed test data. Put the code "
             "into a code file, or approve only if you know what the notes file runs.")
NOTE_RX = re.compile(NOTES + r"(?![\w.-])", re.I)
_W1 = r"[^\s;&|<>()'\"`]"  # a character of a word
_NOTE = _W1 + "*" + NOTES + r"(?![\w.-])"
# where a runner takes its script, a wildcard too that may name such a file (peek.*, pee*), but not run_*.py
_SCRIPT = r"(?:" + _NOTE + r"|(?!" + _W1 + r"*\.\w+(?=[\s;&|<>()]|$))(?=" + _W1 + r"*[*?\[])" + _W1 + "+)"
_START = r"(?:^|[;&|({`]|\s/[ck]\s)"
_LEADS = _LEAD % (_WRAP + r"|xargs|builtin|winpty|stdbuf|wsl|(?:uv|conda|poetry|pipenv|pixi)\s+run")
_GO = _START + _LEADS + r"(?:" + _W1 + "*/)?"
_PROG = (r"(?:(?:ba|z|da|k|c|tc|fi)?sh|cmd|python[0-9.]*|pypy[0-9.]*|py|node|deno|bun|perl|ruby|php|lua|Rscript|julia|"
         r"pwsh|powershell)(?:\.exe)?")
# the word ends there: `source: notes.md` in a configuration file and `cmd = [...]` in a program are no commands
_RUNNER = r"(?:" + _PROG + r"|source|\.)(?=\s|<|$|[;&|)])"
# a runner's options and their values, on its line: words without a dot or a slash, and none that was quoted text
# with blanks in it (the code behind -c or -e, whose next argument is data). -m counts only with a module that runs
# the file it is given
_OPTS = (r"(?:[ \t]+(?!-m(?![ \t]*(?:runpy|pdb|cProfile|profile|trace|doctest|coverage)\b))"
         r"(?:-[^\s;&|<>]*|[^\s;&|<>./=:,\[\]{}()'\"-][^\s;&|<>./]*))*")
_DASH = r"(?:[ \t]+-[^\s;&|<>]*)*"
RUNS_NOTES = re.compile(_GO + _RUNNER + _OPTS + r"[ \t]*(?:[ \t]|<)[ \t]*" + _SCRIPT,  # python notes.md, . ./notes.md,
                        re.I | re.M)                                                    # bash -s < notes.md
# a pipe into a runner that has no script of its own (cat notes.md | python -, gc notes.md | iex): runs_notes() looks
# for the file in front of it
PIPED = re.compile(r"(?<!\|)\|" + _LEADS + r"(?:" + _W1 + r"*/)?(?:" + _RUNNER + _OPTS
                   + r"|(?:iex|Invoke-Expression)\b)[ \t]*(?=$|[;&|)])", re.I | re.M)
# text put into a command line where code stands: eval "$(cat notes.md)", iex (gc notes.md -Raw),
# bash -c "$(cat notes.md)", sh <(sed -n 2,5p notes.md), python $(ls *.md)
SPLICES_NOTES = re.compile(
    _GO + r"(?:(?:eval|iex|Invoke-Expression)(?![\w.-])[^;&>\n]*?|" + _RUNNER + _DASH
    + r"[ \t]*(?:<\(|\"[^\"\n]*?(?:\$\(|`)|'?(?:\$\(|`)|\()[^)`\n]*?)(?<!" + _W1 + ")" + _NOTE, re.I | re.M)
# the file as the command itself (./notes.md with a first line that names its interpreter)
NOTES_CMD = re.compile(_START + _LEADS + _W1 + "*/" + _NOTE + r"(?=\s|$|[;&|)])", re.I | re.M)
# in program text, a call that executes text or a file, on a line that also holds a literal with such a file's name
EXECS =re.compile(r"(?<![\w.])(?:exec|eval|compile|Function)\s*\(|\b(?:execfile|run_path|SourceFileLoader|"
                   r"spec_from_file_location|load_source|loadfile)\s*\(")
_LIT = r"['\"][^'\"\n]*[^'\"\n./\\*]" + NOTES + r"['\"]"  # a literal that ends as a notes file's name does
NOTE_LIT = re.compile(_LIT, re.I)
# a loader called on the file itself (require('./notes.md'), source("notes.md"), do 'notes.md'), or a program's
# argument list that starts with a runner (["python", "-u", "notes.md"])
LOADS = re.compile(r"(?<![\w.])(?:require|import|load|dofile|do|include|include_once|require_once|source)\s*\(?\s*"
                   + _LIT + r"|(?:['\"](?:[^'\"\s]*/)?" + _PROG + r"['\"]|\bsys\.executable)\s*,\s*"
                   r"(?:['\"]-[^'\"\n]*['\"]\s*,\s*)*" + _LIT, re.I)
# In program text that an interpreter runs (python -c "...", python - <<EOF, cat <<EOF | python: not a here-document
# that a command writes into a file): Python's calls that walk, copy or pack a whole tree (os.walk, Path.rglob,
# shutil.copytree, shutil.make_archive). Not ast.walk, which walks no folder
PY_WALK = re.compile(r"(?<!\w)(?:(?<!ast\.)walk|fwalk|rglob|copytree|make_archive)(?=\s*\()")
# a runner that takes a here-document, or a here-string (group 1), as its code
HERE_RUN = re.compile(_GO + _PROG + r"(?=[\s<])(?:[^;&|\n<]|<(?!<))*<<(<?)", re.I | re.M)
# ** (zsh's *** too) as a whole part of a path outside quotes: a shell that reads it so (bash's globstar, zsh, fish)
# walks the tree. Not a ** that stands alone, which in a line of program text is a power
_W = r"[^\s;&|<>()'\"]*"
STARS = re.compile(r"(?<![^\s;&|<>()])(?:" + _W + r"/\*{2,}(?:/" + _W + r")?|\*{2,}/" + _W + r")(?![^\s;&|<>()])")
# the short options that take a value, by tool. The other letters may stand in front of one in one group (-ig)
VALUE_OPTS = {"grep": "ABCDdefm", "rg": "ABCdEefgjMmrTt", "ls": "ITw", "tree": "HILPTo", "du": "BdtX"}
VALUE_OPTS.update(egrep=VALUE_OPTS["grep"], fgrep=VALUE_OPTS["grep"], rgrep=VALUE_OPTS["grep"])
_RG = r"\s-[^\W" + VALUE_OPTS["rg"] + "]*"
RG_GLOB = re.compile(r"(?:" + _RG + r"g(?:=|\s*)|--(i)?glob(?:=|\s+))" + _VAL)
GREP_FILTER = re.compile(r"--(include|exclude-dir|exclude)(?:=|\s+)" + _VAL)
FIND_NAME = re.compile(r"\s-i?name\s+" + _VAL)
SEARCH_EXCL = re.compile(r"--exclude(-dir)?(?:=|\s+)" + _VAL)
SEARCH_TYPE = re.compile(r"(?:" + _RG + r"t(?:=|\s*)|\s--type(?:=|\s+))([a-z0-9]+)\b")
# -e and -f give the text to look for, so that every argument is a path (rg --files looks for none)
TEXT_OPT = {t: re.compile(r"\s-[^\W" + v + r"]*[ef]|\s--(?:regexp|files?)(?=[\s=]|$)") for t, v in VALUE_OPTS.items()}
# an option that surely takes no value: what follows it is an argument. Any other one may take what follows it
PLAIN = {t: re.compile(
    r"-[^\W" + v + r"]+$|--(?:recursive|line-number|ignore-case|colou?r|hidden|files|files-with(?:out)?-match(?:es)?|"
    r"count|fixed-strings|word-regexp|extended-regexp|perl-regexp|invert-match|(?:no-)?heading|json|smart-case|"
    r"only-matching|with-filename|no-filename|no-messages|null|text|follow|no-ignore[\w-]*|unrestricted|no-config)$")
    for t, v in VALUE_OPTS.items()}
PLAIN["find"] = re.compile(r"-[HLP]$")
PS_PLAIN = re.compile(r"-(?:r[ecurs]*|s|fo(?:rce)?|file|directory|name|hidden|path|literalpath|lp)$", re.I)
# what makes ripgrep, ag or git grep read the files that git ignores, or follow a link out of the searched folder
UNRESTRICTED = re.compile(
    r"\brg\b[^;|&]*?\s(?:-(?![tTgefABCmMjEr])[a-zA-Z]*[uL][a-zA-Z]*|--no-ignore[\w-]*|--unrestricted|--follow)"
    r"(?=[\s=;|&)]|$)|\bag\b[^;|&]*?\s(?:-(?![GgABCmpW])[a-zA-Z]*[atuUf][a-zA-Z]*|--unrestricted|--skip-vcs-ignores|"
    r"--all-types|--all-text|--follow)(?=[\s=;|&)]|$)|\bgit\s+grep\b[^;|&]*?\s--no-(?:index|exclude-standard)\b")
_V = r"(?:\"[^\"]*\"|'[^']*'|[^\s;&|,]+)"
PS_GLOB = re.compile(r"\s-(?:Filter|Include)\s+(" + _V + r"(?:\s*,\s*" + _V + r")*)", re.I)  # PowerShell's: a list
# with no folder named, these take the cwd
GREPS = {"grep", "egrep", "fgrep", "rgrep"}  # rgrep is grep -r
CWD_SEARCH = GREPS | {"rg", "ag", "find", "tree", "ls", "du", "get-childitem", "gci", "dir", "findstr", "alldirectories"}
PATTERN_FIRST = GREPS | {"rg", "ag"}  # their first argument is the text to look for, not a path
SEPARATOR = re.compile(r"(&&|\|\||[;|&\n])")  # between the commands of one line
RG_TYPES = {  # the file endings of ripgrep's types, each no less than `rg --type-list` gives (ripgrep 15.0.0)
    "py": ("py", "pyi"), "md": ("markdown", "md", "mdown", "mdwn", "mdx", "mkd", "mkdn"), "yaml": ("yaml", "yml"),
    "js": ("cjs", "js", "jsx", "mjs", "vue"), "ts": ("cts", "mts", "ts", "tsx"), "json": ("json", "sarif", "lock"),
    "csv": ("csv",), "txt": ("txt",), "c": ("c", "h", "in", "cats"),
    "cpp": ("c", "h", "in", "cpp", "hpp", "cxx", "hxx", "cc", "hh", "inl")}
RG_TYPES.update(python=RG_TYPES["py"], markdown=RG_TYPES["md"], typescript=RG_TYPES["ts"])
CLASS = re.compile(r"\[([!^]?)(\]?(?:\[:\w+:\]|[^\]])*)\]")  # [abc], [!a-z], [[:alpha:]] in a file filter
NOCASE = os.name == "nt" or sys.platform == "darwin"  # filesystems that ignore case: the path rules do too
_CASE = re.I if NOCASE else 0


class Unreadable(Exception):
    """The hook input has a shape this guard does not know: the call is refused."""


def load(root: Path):
    scripts = root / ".claude" / "skills" / "nn-training" / "scripts"
    if scripts.is_dir():
        sys.path.insert(0, str(scripts))
    try:
        import expctl  # type: ignore

        return expctl, expctl.load_config(root)
    except Exception:  # noqa: BLE001
        cfg = {"runs_dir": "runs", "sealed_paths": [], "frozen_paths": [], "final_eval_commands": [],
               "harness_paths": [".claude/hooks/**", ".claude/settings.json", ".claude/nn-training.json"]}
        try:
            with open(root / ".claude" / "nn-training.json", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as e:
            cfg["_config_error"] = f"{type(e).__name__}: {e}"
        return None, cfg


@functools.lru_cache(maxsize=None)  # a search asks about every file below a folder
def glob_re(pat: str, narrow=False, deep=False, classes=False):
    """narrow: for a filter that leaves files out, where case counts as written on every platform.
    deep: the pattern may start at any folder of the path it is matched against.
    classes: [abc], [a-z] and [!a] stand for one character, as in the search tools' filters (the config's patterns
    keep their brackets as text). One that cannot be read, or that leaves characters out in a filter told to
    include, stands for any character there; in a filter told to exclude, one that cannot be read matches nothing."""
    pat = pat.strip().replace("\\", "/")
    nocase = pat.startswith("(?i)")  # a filter that ignores case (find -iname, rg --iglob)
    pat = pat[4:] if nocase else pat
    if pat.startswith("./"):
        pat = pat[2:]
    pat, out, i = (pat.lstrip("/"), "(?:.*/)?", 0) if deep else (pat, "", 0)
    while i < len(pat):
        c = pat[i]
        if c == "*":
            if pat.startswith("**/", i):
                out, i = out + "(?:.*/)?", i + 3
                continue
            if pat.startswith("**", i):
                out, i = out + ".*", i + 2
                continue
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c == "[" and classes and CLASS.match(pat, i):
            m = CLASS.match(pat, i)
            no, body = bool(m.group(1)), m.group(2)
            cls = "(?!/)[" + "^" * no + "".join(x if x == "-" else re.escape(x) for x in body) + "]"
            try:
                re.compile(cls)
                clear = "[" not in body and (narrow or not no)  # [[:alpha:]] is not read
            except re.error:  # a range the wrong way round
                clear = False
            out, i = out + (cls if clear else "(?!)" if narrow else "[^/]"), m.end() - 1
        else:
            out += re.escape(c)
        i += 1
    return re.compile("^" + out + "$", re.I if nocase else 0 if narrow else _CASE)


def norm_pattern(p: str) -> str:
    p2 = os.path.expanduser(str(p).strip()).replace("\\", "/")
    return p2[2:] if p2.startswith("./") else p2


def matches(rel: str, patterns) -> str | None:
    if not rel:
        return None
    rel = rel.replace("\\", "/").rstrip("/")
    low = rel.lower() if NOCASE else rel
    for p in patterns or []:
        p2 = norm_pattern(p)
        base = p2[:-3] if p2.endswith("/**") else p2.rstrip("/")
        b = base.lower() if NOCASE else base
        if glob_re(p2).match(rel) or low == b or (not any(ch in base for ch in "*?[") and low.startswith(b + "/")):
            return p
    return None


def fragments(patterns):
    """Anchored literal fragments used to spot sealed/frozen paths anywhere in a shell command (fuzzy)."""
    out = []
    for p in patterns or []:
        p2 = norm_pattern(p)
        if p2.endswith("/**"):
            p2 = p2[:-3]
        lead = re.split(r"[*?\[]", p2)[0].rstrip("/")
        cands = [lead] if len(lead) >= 4 else []
        last = p2.rsplit("/", 1)[-1]
        if last and last != lead and not any(ch in last for ch in "*?[") and len(last) >= 6 and not last.startswith("."):
            cands.append(last)
        for s in cands:
            out.append((p, re.compile(r"(?:^|(?<=[\s'\"=/:(]))" + re.escape(s) + r"(?=$|[^A-Za-z0-9_.\-])", _CASE)))
    return out


def sealed_parents(patterns):
    """(pattern, parent dir, sealed child) for sealed paths nested below a directory of the repo,
    e.g. 'data/test/**' -> ('data/test/**', 'data', 'test'). Top-level sealed dirs are skipped: their parent is
    the repository root, where check_bash looks at the files on disk instead of at the folder's name."""
    out = []
    for p in patterns or []:
        lit = re.split(r"[*?\[]", norm_pattern(p))[0].rstrip("/")
        if "/" not in lit or lit.startswith("/"):
            continue
        parent, child = lit.rsplit("/", 1)
        if parent and child:
            out.append((p, parent, child))
    return out


def sweeps_sealed(c: str, root: Path, patterns, recursive: bool):
    """Pattern whose parent directory the command sweeps (recursively or with a matching wildcard), else None."""
    for pat, parent, child in sealed_parents(patterns):
        body = "(?:" + "|".join(map(re.escape, (parent, root.as_posix().rstrip("/") + "/" + parent))) + ")"
        rx = re.compile(r"(?:^|[\s'\"=])(?:\./)?" + body + r"(/[^\s'\";|&)]*)?/?(?=$|[\s'\";|&)])", _CASE)
        for m in rx.finditer(c):
            rest = (m.group(1) or "").strip("/")
            if not rest:
                if recursive:
                    return pat
                continue
            seg = rest.split("/")[0]
            if any(ch in seg for ch in "*?[") and (fnmatch.fnmatchcase(child.lower(), seg.lower()) if NOCASE
                                                   else fnmatch.fnmatchcase(child, seg)):
                return pat
    return None


def under(a: Path, b: Path) -> bool:
    try:
        a.relative_to(b)
        return True
    except ValueError:
        return False


@functools.lru_cache(maxsize=None)  # a search asks about every file below a folder
def braces(g: str):
    """The globs that g stands for with its {a,b} written out. None when they are more than 64: no real filter has
    that many, and writing them all out would take the guard past its time limit."""
    out = [g]
    while True:
        nxt = []
        for x in out:
            m = re.search(r"\{([^{}]*)\}", x)
            nxt += [x[:m.start()] + a + x[m.end():] for a in m.group(1).split(",")] if m else [x]
        if len(nxt) > 64:
            return None
        if nxt == out:
            return out
        out = nxt


def rg_glob(g: str, nocase=False):
    """One of ripgrep's globs in the form passes() reads. One that leaves out a name with no folder in it stands
    for a file of that name and for a folder of that name with all that it holds."""
    no = g.startswith("!")
    g, pre = g[no:], ("!" if no else "") + ("(?i)" if nocase else "")
    if no and "/" not in g.rstrip("/"):
        return [pre + x for x in ([] if g.endswith("/") else [g]) + ["**/" + g.rstrip("/") + "/**"]]
    return [pre + g]


def find_globs(toks):
    """find's -name tests as globs for passes(). They limit what it lists only when each -o branch has one that is
    not negated; any other grouping or negation reads as no filter at all. A folder that matches and goes to a
    command (-exec) goes there with all that it holds, unless -prune keeps find out of it."""
    execs = ("-exec", "-execdir", "-ok", "-okdir")
    handed = any(t in execs for t in toks)
    globs, alts, neg, cmd = [], [False], False, False
    for i, t in enumerate(toks):
        if cmd or t in execs:  # the command's own words, up to the + that ends it
            cmd = t != "+"
        elif t in ("-o", "-or", ","):
            alts.append(False)
        elif t in ("!", "-not"):
            neg = True
        elif t in ("-name", "-iname") and i + 1 < len(toks):
            no, pre = toks[i - 1] in ("!", "-not"), "(?i)" * (t == "-iname")
            whole = handed and not no and toks[i + 2:i + 3] != ["-prune"]
            globs += ["!" * no + pre + toks[i + 1]] + [pre + "**/" + toks[i + 1] + "/**"] * whole
            alts[-1] = alts[-1] or not no
    if (len(alts) > 1 or "(" in toks) and (neg or not all(alts)):
        return []
    return sorted(globs, key=lambda g: g.startswith("!"))  # find joins them with "and": what leaves out comes last


def file_filters(seg, sq, tools, ps):
    """The file filters of one search command as globs for passes(), and the command without them. Each tool has
    its own: what filters for one is another kind of option elsewhere (tar -g, zip -g) or filters nothing there
    (rsync --include). A filter that the guard cannot read (a variable) limits nothing."""
    if ps:  # PowerShell's take a list, and none of them leaves out
        globs = ["*" if v.startswith("!") else v for y in PS_GLOB.finditer(seg)
                 for v in (v.strip("\"'@()") for v in re.findall(_V, y.group(1)))]
        cut = PS_GLOB.sub(" ", seg)
    elif tools == {"rg"}:
        every = "--glob-case-insensitive" in sq
        globs = [x for y in RG_GLOB.finditer(seg) for x in rg_glob(y.group(2).strip("\"'"), every or bool(y.group(1)))]
        cut = SEARCH_TYPE.sub(" ", RG_GLOB.sub(" ", seg))
    elif tools <= GREPS:
        opts = [(y.group(1), y.group(2).strip("\"'")) for y in GREP_FILTER.finditer(seg)]
        files = ["!" * (o == "exclude") + v for o, v in opts if o != "exclude-dir"]
        # grep reads a file that none of them matches, unless the first of them is --include. And it leaves out by
        # a file's or a folder's own name: a name with a folder in it leaves out nothing
        globs = (["*"] if files and files[0].startswith("!") else []) + \
            [g for g in files if not (g.startswith("!") and "/" in g)] + \
            ["!**/" + v + "/**" for o, v in opts if o == "exclude-dir" and "/" not in v]
        cut = GREP_FILTER.sub(" ", seg)
    elif tools == {"find"}:
        globs, cut = find_globs(lex(seg)), FIND_NAME.sub(" ", seg)
    else:
        globs, cut = [], seg
    return [g for g in ("*" if re.search(r"[$`]", g) and g[:1] != "!" else g for g in globs)
            if not re.search(r"[$`]", g)], cut


def type_exts(types):
    """The file endings of these ripgrep types; None, which is no filter, when one of them is not known here."""
    exts = [RG_TYPES.get(str(t)) for t in (types if isinstance(types, list) else [types] if types else [])]
    return {e for x in exts for e in x} if exts and None not in exts else None


def search_args(toks, plain):
    """What follows a search tool on its line, as (argument, sure) pairs. sure: it is an argument for certain, and
    not what may be the value of the option in front of it (plain matches the options that take none). The value in
    --opt=value is listed as unsure too, and the target of a redirection is left out: neither is a path the tool
    was given, so neither keeps it from searching the folder it runs in."""
    out, sure, skip = [], True, False
    for t in toks:
        if skip or t[:1] in ";&|<>()":
            skip = not skip and t[:1] in ("<", ">")
        elif t in ("-", "--") or not t.startswith("-"):
            out += [(t, sure)] * (t != "--")
            sure = True
        else:
            if "=" in t:
                out.append((t.split("=", 1)[1], False))
            sure = "=" in t or bool(plain and plain.match(t))
    return out


def passes(f: Path, rr: str, globs, typ, cr=None) -> bool:
    """Would a search limited to these file globs (ripgrep's form: no slash means any folder, a leading ! excludes,
    (?i) after it ignores case; the last glob that matches a file decides) and these file endings look at file
    f? rr is its path below the searched folder, cr its path below the folder the tool runs in, where ripgrep
    anchors a glob with a folder in it (None: not known). A glob told to include counts under every reading of it:
    from whichever folder of the file's path it may start. One told to exclude counts only where it surely leaves
    the file out: with case as written, by the file's own name, by its path from the folder the tool runs in, or
    at any depth when it starts with **/."""
    if typ and f.suffix[1:].lower() not in typ:
        return False

    def inc(g):  # one with more {a,b} than the guard writes out counts as matching every file
        return braces(g) is None or any(glob_re(a, False, True, True).match(f.as_posix()) for a in braces(g))

    def exc(g):  # and such a one as leaving out none
        return any(glob_re(a, True, False, True).match(f.name) if "/" not in a else
                   glob_re(a, True, False, True).match(cr) if cr is not None else
                   a.startswith(("**/", "(?i)**/")) and glob_re(a, True, False, True).match(rr) for a in braces(g) or [])
    read = not any(not g.startswith("!") for g in globs)  # with no glob told to include, every file is read
    for g in (g.replace("\\", "/") for g in globs):
        read = (read and not exc(g[1:])) if g.startswith("!") else (read or inc(g))
    return read


# A repository's settings can make git start a program by itself (core.fsmonitor on every status, a hook on every
# change of the index). The guard's own git call runs with the user's rights and before the call it checks, so it
# switches both off. Checked with git 2.43 and 2.52: the empty value turns the monitor off
GIT = ["git", "-c", "core.fsmonitor=", "-c", "core.hooksPath=" + os.devnull]


def git_ignored(root: Path, rels) -> set:
    """Those of the paths below root that git's ignore rules exclude, by themselves or with a folder above them."""
    try:  # --no-index: by the ignore rules alone, which is how ripgrep decides. One call for all the paths
        out = subprocess.run([*GIT, "-C", str(root), "check-ignore", "--no-index", "--stdin", "-z"],
                             input="\0".join(rels).encode(errors="surrogateescape"), capture_output=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        return set(out.decode(errors="surrogateescape").split("\0")) - {""}
    except (OSError, ValueError, subprocess.SubprocessError):
        return set()


@functools.lru_cache(maxsize=None)  # the files of one folder share it
def taken_back(d: Path) -> tuple:
    """What the .ignore and .rgignore files in folder d take back from the ignore rules: of each of their lines
    that starts with !, the last part of its path."""
    out = []
    for n in (".ignore", ".rgignore"):
        try:
            with open(d / n, encoding="utf-8-sig", errors="replace") as f:
                out += [x.strip().rstrip("/").rsplit("/", 1)[-1].lstrip("!").lower()
                        for x in f if x.lstrip().startswith("!")]
        except OSError:
            pass
    return tuple(out)


@functools.lru_cache(maxsize=None)
def let_in(d: Path) -> bool:
    """Does a .ignore or .rgignore file take back the ignore rule that keeps ripgrep away from d? ripgrep reads
    those files in the folder that holds d and in every folder above it, and they outrank git's rules (compared
    with ripgrep 15.0, 13 November 2026). Read wide: the last part of such a line's path has to match d's name,
    and with ** or a backslash in it the line counts for every name."""
    name = d.name.lower()
    return any("**" in g or "\\" in g or fnmatch.fnmatchcase(name, g) for x in d.parents for g in taken_back(x))


@functools.lru_cache(maxsize=None)
def rg_config() -> bool:
    """Does the configuration file that RIPGREP_CONFIG_PATH names make ripgrep read what git ignores, or follow
    links? It holds one option or value per line, and # starts a comment. A file that is not there changes
    nothing; a relative path is read from the folder ripgrep runs in, which is not known here, so it counts."""
    p = os.environ.get("RIPGREP_CONFIG_PATH")
    if not p or not os.path.isabs(p):
        return bool(p)
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            text = "rg " + re.sub(r"[;|&]", ",", " ".join(x.strip() for x in f if not x.lstrip().startswith("#")))
    except OSError:
        return False
    return bool(UNRESTRICTED.search(text)) or any(not g.strip("\"'").startswith("!") for _, g in RG_GLOB.findall(text))


def walk(top: Path):
    if top.is_file():
        yield top
        return
    for dp, dns, fns in os.walk(top):
        dns[:] = [d for d in dns if d not in (".git", "node_modules", ".venv", "__pycache__")]
        for fn in fns:
            yield Path(dp, fn)


def reaches_sealed(ctx, base, globs=(), typ=None, skips_ignored=False, cwd=None):
    """Sealed pattern with a file on disk that a recursive search of the folder `base` would read or list, given
    the search's file globs and ripgrep types; None if there is none. skips_ignored: the tool is ripgrep-like, so
    files that git ignores where they really lie, or that sit behind a link out of the searched folder, do not
    count. cwd: the folder ripgrep runs in, where that is known (see passes)."""
    @functools.lru_cache(maxsize=None)
    def home(p):  # the checkout that p lies in, the deepest one
        return max((x for x in ctx.bases if under(p, x)), key=lambda x: len(x.parts), default=None)

    b, tops, typ = ctx._abs(base or "."), set(ctx.bases), type_exts(typ)
    cw = ctx._abs(cwd) if cwd and any(g.startswith("!") and "/" in g for g in globs) else None
    own = home(b) or ctx.root
    rgish = skips_ignored
    inc = [g for g in globs if not g.startswith("!")]
    # ripgrep searches a folder it is given by name even when git ignores that folder: the ignore rules do not help
    if rgish and b != own and under(b, own) and git_ignored(own, [b.relative_to(own).as_posix()]):
        skips_ignored = False

    def kept_out(root, paths):
        """Those of the paths in the checkout root that its ignore rules keep ripgrep away from. What does is the
        first ignored folder on the way from the searched folder down to a path, or the rule for the path itself,
        unless a glob told to include matches it: such a glob overrides the ignore rules (`-g '*.csv'` reads a csv
        file that git ignores, `-g '*'` enters an ignored folder). So does a .ignore file that takes the rule back."""
        lo = b if under(b, root) else root

        @functools.lru_cache(maxsize=None)  # the files of one folder share it
        def above(d):  # d's path below root, and the paths of the folders from below `lo` down to d
            r = d.relative_to(root).parts
            n = len(lo.relative_to(root).parts) if under(d, lo) else len(r)
            return "/".join(r), ["/".join(r[:i]) for i in range(n + 1, len(r) + 1)]
        ways = {}  # for each path the paths to look up: those of the folders on its way, then its own
        for p in paths:
            if p != root:
                at, way = above(p.parent)
                ways[p] = way + [(at + "/" if at else "") + p.name]
        gone = git_ignored(root, {r for w in ways.values() for r in w}) if ways else set()
        out = set()
        for p, w in ways.items():
            d = next((root / r for r in w if r in gone), None)
            if d and not let_in(d) and \
                    not (inc and passes(d, d.relative_to(b).as_posix() if under(d, b) else d.name, inc, None)):
                out.add(p)
        return out

    def unread(paths):
        """Those of the paths that ripgrep passes over. It goes by the ignore rules of the checkout in which a path
        really lies (behind a link out of the repository there are none), and it does not enter a checkout below
        the searched folder that git ignores from there, as .claude/worktrees/ is."""
        if not skips_ignored:
            return set()
        at = {p: home(p if p in tops else p.parent) for p in paths}
        shut = kept_out(own, {x for x in at.values() if x and x != own and under(x, b) and under(x, own)})
        return {p for p in paths if at[p] in shut}.union(
            *(kept_out(root, [p for p in paths if at[p] == root]) for root in {x for x in at.values() if x} - shut))

    spots = []
    for root, pat in itertools.product(ctx.bases, ctx.cfg.get("sealed_paths") or []):
        s = root / re.split(r"[*?\[]", norm_pattern(pat))[0].rstrip("/")
        if not s.exists():
            s = s.parent
        sr = ctx._abs(s)  # where the sealed folder really is, when it is or lies behind a link
        # the search's own checkout counts, and those below its folder (a worktree in a subfolder), and any other
        # whose sealed folder is a link: its real place can lie where the search goes
        if root == own or under(root, b) or sr != s:
            spots.append((root, pat, s, sr))
    shut = unread({sr for _, _, _, sr in spots})
    walks = {}  # the patterns that look in the same folder share one walk of it
    for root, pat, s, sr in spots:
        if under(s, b):  # the search starts above it; ripgrep does not follow a link that leaves the searched folder
            top = None if rgish and not under(sr, b) else s
        else:  # the search starts inside it, or at or above its real place
            top = b if under(b, s) or under(b, sr) else sr if under(sr, b) else None
        if sr not in shut and top is not None and top.exists():
            walks.setdefault((top, root, s, sr), []).append(pat)
    # found: the sealed files that the search's filters let through, by the folder they really lie in, with their pattern
    found, real, plain = {}, {}, not (globs or typ)
    for (top, root, s, sr), pats in walks.items():
        # A folder sealed as a whole (data/test/**) is walked to its end, as long as the hook's time allows: every
        # file in it is sealed, so one that the search's filters let through anywhere in it counts. Where the time
        # runs out first, the search counts as reading it.
        # shortcut: any other pattern's walk looks at WALK files, so a filtered search passes when the sealed files
        # that it would read lie beyond them; index the sealed files once if projects that large turn up
        whole = [p for p in pats if not re.search(r"[*?\[]", re.sub(r"/\*\*$", "", norm_pattern(p)))]
        for n, f in enumerate(walk(top)):
            if n >= WALK and not (whole and time.time() < ctx.t0 + WALK_S):
                if whole:
                    return whole[0]
                break
            rel = ctx.canon((f.relative_to(root) if under(f, root) else s.relative_to(root) / f.relative_to(sr)
                             if under(f, sr) and under(s, root) else f).as_posix())
            pat = matches(rel, pats)
            if pat and (plain or passes(f, f.relative_to(b).as_posix() if under(f, b) else f.name, globs, typ,
                                        f.relative_to(cw).as_posix() if cw and under(f, cw) else None)):
                d = real.get(f.parent)
                if d is None:
                    d = real[f.parent] = ctx._abs(f.parent)
                # the first one is looked up at once: where ripgrep reads the sealed files, it mostly tells
                if not (found or unread([d / f.name])):
                    return pat
                found.setdefault(d, {}).setdefault(f.name, pat)
    # a folder that ripgrep does not enter holds nothing it reads, so the folders are asked about first: that spares
    # the look at each file below data/. Not with a glob told to include: it can open a file whose folder it does not
    shut = set() if inc else unread(found)
    left = {d / n: pat for d, names in found.items() if d not in shut for n, pat in names.items()}
    gone = unread(left)  # the others together: a file that git ignores says nothing about the one beside it
    return next((pat for p, pat in left.items() if p not in gone), None)


def searched(ctx, *search):
    """What reaches_sealed says to these arguments, looked up on disk once per hook call for each different search:
    a line may repeat one many times."""
    key = repr(search)
    if key not in ctx.searched:
        ctx.searched[key] = reaches_sealed(ctx, *search)
    return ctx.searched[key]


def lex(c: str):
    try:
        lx = shlex.shlex(c, posix=True, punctuation_chars=";&|<>()")
        lx.whitespace_split = True
        return list(lx)
    except ValueError:
        return c.split()


def git_runs(c: str):
    """What on a line could make git start a program by itself, or None: a setting given for one call (git -c
    key=value, --config-env, --exec-path=), a `git config` that writes a key outside GIT_PLAIN_KEY or that this
    guard cannot read as a plain write, a clone that sets such a key, or a template folder, whose hooks git copies
    into its own. Reading a setting, and unsetting one, pass."""
    toks = lex(c)
    for i, t in enumerate(toks):
        if re.sub(r"\.exe$", "", t.rsplit("/", 1)[-1].lower()) != "git":
            continue
        j = i + 1
        while j < len(toks) and toks[j][:1] == "-":  # git's own options, up to its subcommand
            o, val = toks[j], "".join(toks[j + 1:j + 2])
            if o == "-c" and not GIT_PLAIN_KEY.match(val.split("=", 1)[0]) and not GIT_NO_PROGRAM.match(val):
                return "-c " + val
            if o.startswith(("--config-env", "--exec-path=")):
                return o
            j += 2 if o in GIT_VALUE_OPT else 1
        sub = "".join(toks[j:j + 1])
        rest = list(itertools.takewhile(lambda x: x.strip(";&|()<>"), toks[j + 1:]))
        for o, val in zip(rest, rest[1:] + [""]) if sub in ("clone", "init") else ():
            key = val if o in ("-c", "--config") else o[9:] if o.startswith("--config=") else None
            if o.startswith("--template") or (key is not None and not GIT_PLAIN_KEY.match(key.split("=", 1)[0])):
                return f"{sub} {o} {val if key == val else ''}".strip()
        opts, pos = [x for x in rest if x[:1] == "-"], [x for x in rest if x[:1] != "-"]
        if sub != "config" or set(opts) & GIT_CONFIG_READ or pos[:1] in (["get"], ["list"]):
            continue
        if pos[:1] in (["set"], ["unset"]):
            pos = pos[1:]
        plain = all(GIT_CONFIG_FLAG.match(o) for o in opts)
        if len(pos) == 1 and plain:  # one key and no value: it prints the key's value, or unsets it
            continue
        if not (pos and plain and GIT_PLAIN_KEY.match(pos[0])):
            return "config " + " ".join(rest)
    return None


def readings(cmd: str):
    """The line as another shell reads it, where that is another text, and whether a word of it was too long to
    write out. check_bash reads a backslash as a folder separator, as PowerShell and cmd do. A POSIX shell takes it
    off the character behind it (te\\st is test, also across the end of a line), reads $'te\\x73t' and $"test" as
    test, and writes a word with {a,b} out; PowerShell and cmd take their own escape characters off (te`st, te^st).
    Each reading may name more than the shell would (an escape that stands for a control character is read as its
    letter): it is checked in addition to the line as it came.
    shortcut: text only, so a name put together from variables, {a..b} or a command's output passes; that takes
    running the line in a sandbox"""
    held, long = [], []

    def hold(s):  # quoted text is no escape and no brace list
        held.append(s)
        return "\0%d\0" % (len(held) - 1)

    def c_char(m):
        e = m.group(1)
        return chr(min(int(e[1:], 16), 0x10FFFF)) if e[0] in "xuU" and len(e) > 1 else \
            chr(int(e, 8) % 256) if e[0] in "01234567" else e

    def part(m):
        x = m.group(1)
        if x is None or not re.match(r"[\w./:@%+=~^-]", x):  # a quoted string, or a character that stays quoted
            return hold(m.group() if x is None else "" if x == "\n" else shlex.quote(x))
        return x

    def written_out(m):
        names = braces(m.group())
        long.append(names is None)
        return " ".join(names or [m.group()])

    text = cmd.replace("\0", "")
    posix = ANSI_C.sub(lambda m: shlex.quote(C_ESCAPE.sub(c_char, m.group(1)).replace("\0", "")), text)
    posix = BRACE_WORD.sub(written_out, POSIX_PART.sub(part, re.sub(r"\$(?=\")", "", posix)))
    posix = re.sub(r"\0(\d+)\0", lambda m: held[int(m.group(1))], posix)
    win = re.sub(r"`u\{([0-9a-fA-F]{1,6})\}", lambda m: chr(min(int(m.group(1), 16), 0x10FFFF)), text)
    win = WIN_ESCAPE.sub("", win).replace("\0", "")
    return [t for t in dict.fromkeys((posix, win)) if t != cmd], any(long)


def runs_notes(c: str, cmd: bool, code: bool) -> bool:
    """Does a text run a file of notes (.md, .mdx, .rst) as code? As a runner's script or standard input, piped into
    a runner, sourced, or spliced into a command line where code stands. cmd: c is a command line, where the file
    may be the command itself. code: c is program text (a file's new text, code handed to an interpreter, a
    here-document), where a call may execute or load the file it names on the same line, and a string may hold a
    command. There c is the text as it came: check_bash takes the quotes off a word where a command may start.
    shortcut: the text only, so a notes file that was copied, renamed or cut into another file first passes, as
    does one with a blank in its name, and one whose text is read on one line and executed on another; that takes
    a sandbox, which sees what runs"""
    c = re.sub(r"[/\\]\n", " ", c)  # a line that goes on (check_bash has turned its backslash into a slash)
    # a quoted word is the word ("notes.md", notes.m""d); quoted text with blanks is no command and no file name
    words = QUOTED.sub(lambda m: m.group()[1:-1] if re.fullmatch(r"[^\s;&|<>()`]*", m.group()[1:-1]) else " '' ", c)
    if not (NOTE_RX.search(c) or NOTE_RX.search(words) or re.search(r"[*?\[]", words)):
        return False
    if RUNS_NOTES.search(words) or SPLICES_NOTES.search(c) or (cmd and NOTES_CMD.search(c.split("<<")[0])) or any(
            NOTE_RX.search(words, max(words.rfind(s, 0, m.start()) for s in (";", "\n", "&&", "||")) + 1, m.start())
            for m in PIPED.finditer(words)):  # the pipe's own command, from where it starts
        return True
    return code and (
        any((EXECS.search(ln) and NOTE_LIT.search(ln)) or LOADS.search(ln) for ln in c.split("\n") if NOTE_RX.search(ln))
        or any(runs_notes(q.group()[1:-1], False, True) for q in QUOTED.finditer(c) if NOTE_RX.search(q.group())))


def decodes_into_line(c: str) -> bool:
    """A decoder (base64 -d ...) inside $( ), <( ) or backticks: its output becomes part of a command line, as the
    text a shell runs (sh -c "$(...)", eval) or as an argument (cat "$(...)")."""
    for d in DECODER.finditer(c):
        stack, ticks = [], 0
        for m in re.finditer(r"[$<]?\(|\)|`", c[:d.start()]):
            if m.group() == "`":
                ticks += 1
            elif m.group() == ")":
                stack[-1:] = []
            else:
                stack.append(len(m.group()) > 1)
        if ticks % 2 or any(stack):
            return True
    return False


def decoded(t: str):
    """The text PowerShell reads from the value of -EncodedCommand (base64 of UTF-16), or None if t is no such value."""
    try:
        s = base64.b64decode(t, validate=True).decode("utf-16-le")
    except ValueError:
        return None
    return s if s.strip() and all(ch.isprintable() or ch in "\r\n\t" for ch in s) else None


def inner_code(c: str):
    """Text a command hands to a nested shell or an interpreter as one argument (bash -c '...', python -c "...",
    cmd /c "...", powershell -Command "..."), also where it is attached to its flag (bash -c"...") or encoded
    (powershell -EncodedCommand <base64>). The caller checks it like a command of its own."""
    if not SHELLS.search(c):
        return []
    toks, out = lex(c), []
    for t, after in zip(toks, toks[1:] + [""]):
        m = ATTACHED.match(t)
        out += [m.group(1)] if m else []
        out += [after] if after and CODE_FLAG.match(t) else []
        out += [decoded(after)] if ENCODED.match(t) and decoded(after) else []
    # a runner without a script takes its code from standard input (echo "..." | sh, bash <<< "..."): there every
    # argument of the line that is more than a plain word or path may be that code
    bare = QUOTED.sub(" '' ", c)
    if PIPED.search(bare) or any(m.group(1) for m in HERE_RUN.finditer(bare)):
        out += [t for t in toks if re.search(r"\w", t) and re.search(r"[^\w./:@%+,-]", t)]
    return out


def joined(c: str, depth=0, blank=True):
    """Paths that a text puts together from string literals, as far as that shows without running it:
    Path('data') / 'test' / 'x.csv', os.path.join('data', 'test', 'x.csv'), 'data/' + 'test/x.csv', and Python's
    literals side by side ('data/te' 'st/x.csv'). A comma joins only inside a call that joins paths. blank=False:
    c is the line of a shell, where two literals with blanks between them are two arguments, so only literals
    that touch are one. c is the text as it came, with its backslashes. depth below 2: a literal that holds code
    (python -c "open('a' + 'b')", bash -c 'python -c "..."') is read as well.
    shortcut: literals only, so a path with a variable in it passes; that takes running the code in a sandbox"""
    lits, out = list(QUOTED.finditer(c)), []
    for i, first in enumerate(lits):
        path = first.group()[1:-1]
        if depth < 2 and re.search(r"['\"]", path):  # in double quotes, one level of \" and \\ comes off
            out += joined(path if first.group()[0] == "'" else re.sub(r"\\([\\'\"])", r"\1", path), depth + 1)
        comma = JOINER.search(c[max(0, first.start() - 100):first.start()])
        for j in range(i, len(lits) - 1):  # as far as the joins go
            a, b = lits[j], lits[j + 1]
            g = GAP.fullmatch(c[a.end():b.start()])
            if not g or (g.group(1) == "," and not comma) or (g.group() and not g.group(1) and not blank):
                break
            nxt = b.group()[1:-1]
            path = path + nxt if g.group(1) in ("+", None) else path.rstrip("/\\") + "/" + nxt.lstrip("/\\")
            if len(path) >= 300:  # no path, and it only grows
                break
            out += [path] if nxt else []
    out = dict.fromkeys(re.sub(r"\\+", "/", p) for p in out)
    return [p for p in out if p and not re.search(r"\s", p)]


def strings(obj, skip=(), out=None):
    """Every string among a call's arguments, however long, however many and however deep, except under the keys
    `skip`. Values nested too deeply to walk end it with a RecursionError, which main() turns into a refusal."""
    out = [] if out is None else out
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k not in skip:
                strings(v, skip, out)
    elif isinstance(obj, list):
        for v in obj:
            strings(v, skip, out)
    return out


def shell_tokens(c: str):
    """Path-like arguments of a shell command (best effort): values of --opt=value and VAR=value included."""
    toks = lex(c)
    out = []
    for t in toks:
        if not t or t[0] in ";&|<>()":
            continue
        if "=" in t and not t.startswith(("/", ".", "~")):
            t = t.split("=", 1)[1]
        if t and not t.startswith("-") and len(t) < 4096:
            out.append(t)
    return out


def winpath(p) -> str:
    """Forward slashes; '/c:/Users/x' (the form Cursor reports on Windows) becomes 'c:/Users/x', and so do the
    long-path and own-machine spellings of a drive ('//?/c:/', '//./c:/', '//localhost/c$/')."""
    s = str(p).replace("\\", "/")
    s = re.sub(r"^//[?.]/(UNC/)?", lambda m: "//" if m.group(1) else "", s, flags=re.I)
    s = re.sub(r"^//(?:localhost|127\.0\.0\.1)/([a-z])\$/", r"\1:/", s, flags=re.I)
    return s[1:] if re.match(r"^/[A-Za-z]:/", s) else s


def find_root(payload) -> Path:
    """Project root: the agent's project variable, else the nearest directory above the session's working
    directory that holds .claude/nn-training.json (Codex runs hooks from wherever the session started)."""
    for k in ("CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR"):
        if os.environ.get(k):
            return Path(os.environ[k]).resolve()
    roots = payload.get("workspace_roots")
    start = roots[0] if isinstance(roots, list) and roots and isinstance(roots[0], str) else payload.get("cwd")
    p = Path(winpath(start or os.getcwd())).resolve()
    for d in (p, *p.parents):
        if (d / ".claude" / "nn-training.json").is_file():
            return d
    return p


def git_top(root: Path):
    """The folder that holds .git: the project itself, or a folder above it when the project is a subfolder."""
    return next((d for d in (root, *root.parents) if (d / ".git").exists()), None)


def checkouts(root: Path):
    """This project's folder in the other working trees of its repository (the main checkout and the registered
    worktrees), read from git's own files: sealed, frozen and harness files are the same files in every one."""
    top = git_top(root)
    if top is None:
        return []
    out, dot, off = [], top / ".git", root.relative_to(top)
    try:
        if dot.is_file():  # a worktree's pointer: "gitdir: <main>/.git/worktrees/<name>"
            gd = top / winpath(dot.read_text(encoding="utf-8").split(":", 1)[1].strip())
            common = (gd / (gd / "commondir").read_text(encoding="utf-8").strip()).resolve()
        else:
            common = dot.resolve()
        entries = list(common.glob("worktrees/*/gitdir"))
    except (OSError, IndexError, ValueError):
        return []
    if common.name == ".git":
        out.append(common.parent / off)
    for f in entries:
        try:  # a damaged entry loses that one worktree, not the others
            out.append((f.parent / winpath(f.read_text(encoding="utf-8").strip())).resolve().parent / off)
        except (OSError, ValueError):
            pass
    return [p for p in out if p != root]


def path_strings(obj, out=None):
    """Short single-line string arguments of a call whose keys this guard does not know: all of them, at any depth
    (a tool that reads many files takes a list of any length)."""
    out = [] if out is None else out
    if isinstance(obj, str):
        if 0 < len(obj) <= 1024 and "\n" not in obj:
            out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k not in CONTENT_KEYS:
                path_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            path_strings(v, out)
    return out


def command_text(v) -> str:
    if isinstance(v, list) and all(isinstance(x, str) for x in v):
        v = " ".join(v)
    if not isinstance(v, str) or not v.strip():
        raise Unreadable("a shell call without a command")
    return v


def patch_calls(text: str):
    """File headers of a Codex apply_patch body, each checked as a write (and a delete as an rm) of the lines that
    the patch adds below it."""
    calls, heads = [], list(PATCH_FILE.finditer(text))
    for m, nxt in zip(heads, heads[1:] + [None]):
        p = m.group(2) or m.group(3)
        body = text[m.end():nxt.start() if nxt else len(text)]
        calls.append(("Write", {"file_path": p, "text": "\n".join(x[1:] for x in body.splitlines() if x[:1] == "+")}))
        if m.group(1) == "Delete":
            calls.append(("Bash", {"command": "rm " + shlex.quote(p)}))
    return calls


def calls_from(payload):
    """One hook payload of Claude Code, Codex or Cursor -> [(tool, tool_input)] in Claude Code's vocabulary.
    Raises Unreadable for a shape it does not know."""
    event = str(payload.get("hook_event_name") or "")
    name = payload.get("tool_name")
    if not name:  # Cursor's shell and file-read events carry no tool name
        if event == "beforeShellExecution":
            return [("Bash", {"command": command_text(payload.get("command"))})]
        if event == "beforeReadFile":
            p = payload.get("file_path")
            if not isinstance(p, str) or not p:
                raise Unreadable("beforeReadFile without file_path")
            return [("Read", {"file_path": x}) for x in [p] + path_strings(payload.get("attachments"))]
        raise Unreadable("no tool_name" + (f" in event {event[:40]}" if event else ""))
    if not isinstance(name, str):
        raise Unreadable("tool_name is not a string")
    tool = TOOL_NAMES.get(name.lower(), name)
    ti = payload.get("tool_input")
    if isinstance(ti, str):  # some hook events carry the arguments as JSON text
        try:
            ti = json.loads(ti)
        except ValueError:
            ti = ti if tool == "apply_patch" else None
    if tool == "apply_patch":
        text = ti if isinstance(ti, str) else next(
            (ti[k] for k in ("command", "input", "patch") if isinstance(ti, dict) and isinstance(ti.get(k), str)), "")
        calls = patch_calls(text)
        if not calls:
            raise Unreadable("apply_patch without file headers")
        return calls
    if ti is None and tool not in TOOL_NAMES.values():
        ti = {}
    if not isinstance(ti, dict):
        raise Unreadable(f"tool_input of {name[:40]} is not an object")
    if tool == "Bash":
        cmd = command_text(ti.get("command"))
        return [("Bash", {"command": cmd})] + (patch_calls(cmd) if "*** Begin Patch" in cmd else [])
    if tool in ("Grep", "Glob"):
        return [(tool, ti)]
    if tool in TOOL_NAMES.values():  # the file tools: one path under a known key, else any short string argument
        paths = [ti[k] for k in PATH_KEYS if isinstance(ti.get(k), str) and ti[k]][:1] or path_strings(ti)
        if not paths:
            raise Unreadable(f"a {name[:40]} call without a file path")
        if tool == "Delete":
            return [c for p in paths for c in (("Write", {"file_path": p}), ("Bash", {"command": "rm " + shlex.quote(p)}))]
        calls = [(tool, {"file_path": p}) for p in paths]
        if tool in EDIT_TOOLS:  # what the call would put into the file: every string but the path and the text it replaces
            calls[0][1]["text"] = "\n".join(strings(ti, PATH_KEYS + OLD_KEYS))
        return calls
    # any other tool (MCP tools, Task, ...): its arguments are checked as paths it might read, and a command as shell
    calls = [("Other", {"file_path": p}) for p in path_strings(ti)]
    if isinstance(ti.get("command"), str) and ti["command"].strip():
        calls.append(("Bash", {"command": ti["command"]}))
    # an MCP tool reads files by itself, so a sealed path inside a longer argument (a query, a script) counts too.
    # Not for the agent's own tools: a task for a subagent may name the sealed folder, and its calls come here as well
    if re.match(r"mcp(?:__|:)", name, re.I) or payload.get("mcp_server_name") or event == "beforeMCPExecution":
        calls.append(("Other", {"text": "\n".join(strings(ti))}))
    return calls


class Ctx:
    posix = False  # the call surely runs in a POSIX shell: main() knows that of Claude Code's Bash tool alone

    def __init__(self, payload, root=None):
        self.payload = payload
        self.root = root or find_root(payload)
        ti = payload.get("tool_input")
        wd = ti.get("working_directory") if isinstance(ti, dict) else None  # Cursor's Shell tool
        self.cwd = Path(winpath(wd or payload.get("cwd") or self.root))
        self.expctl, self.cfg = load(self.root)
        self.runs_dir = (self.cfg.get("runs_dir") or "runs").strip("/")
        self._active = None
        # a session inside <checkout>/.claude/worktrees/<name>: the checkout's own files are protected alike
        up = self.root.parents
        self.outer = up[2] if len(up) > 2 and (up[0].name, up[1].name) == ("worktrees", ".claude") else None
        # so are the files of every other checkout of the repository: this one first, then the deepest
        others = sorted({p for p in [self.outer, *checkouts(self.root)] if p}, key=lambda p: -len(p.parts))
        self.bases = [self.root] + others
        nested = [re.escape(p.relative_to(self.root).as_posix()) for p in others if under(p, self.root)]
        self._snap_prefix = re.compile(r"^(?:" + "|".join(
            [re.escape(self.runs_dir) + r"/[^/]+/src", r"\.claude/worktrees/[^/]+"] + nested) + ")/")
        for other in others:  # a worktree's config may differ: the strictest rules of any checkout hold in all
            try:
                with open(other / ".claude" / "nn-training.json", encoding="utf-8") as f:
                    theirs = json.load(f)
            except (OSError, ValueError):
                continue
            for k in ("sealed_paths", "sealed_tokens", "frozen_paths", "harness_paths", "final_eval_commands"):
                if isinstance(theirs, dict) and isinstance(theirs.get(k), list):
                    mine = list(self.cfg.get(k) or [])
                    self.cfg[k] = mine + [x for x in theirs[k] if isinstance(x, str) and x not in mine]
        self._links, self.searched, self.t0 = None, {}, time.time()
        self.cut, self._globs = None, {}  # the wildcard whose matches expand() could not read to the end; its answers

    def _abs(self, p):
        pp = Path(os.path.expanduser(winpath(p)))  # not Path.expanduser(): that one raises for a user it does not know
        if not pp.is_absolute():
            pp = self.cwd / pp
        try:
            pp = pp.resolve(strict=False)
        except (OSError, RuntimeError):
            pass
        return pp

    def links(self):
        """(real place, repository name) of each protected folder or file that is, or lies behind, a link (data ->
        a folder on another drive): a file at the real place is the protected file, however it was reached."""
        if self._links is None:
            self._links = []
            for base in self.bases:
                for pat in self.protected():
                    name = re.split(r"[*?\[]", norm_pattern(pat))[0].rstrip("/")
                    while name and not (base / name).exists():
                        name = name.rpartition("/")[0]
                    real = self._abs(base / name) if name else None
                    if real and real != base / name:
                        self._links.append((real, name))
            self._links.sort(key=lambda x: -len(x[0].parts))
        return self._links

    def rel(self, p):
        if not p:
            return None
        pp = self._abs(p)
        for real, name in self.links():
            if under(pp, real):
                return (Path(name) / pp.relative_to(real)).as_posix()
        raw = Path(os.path.expanduser(winpath(p)))
        # last: a path that some other link takes out of the project keeps the name it was given inside the project
        for q in (pp, Path(os.path.normpath(raw if raw.is_absolute() else self.cwd / raw))):
            for base in self.bases:
                try:
                    return q.relative_to(base).as_posix()
                except ValueError:
                    pass
        return pp.as_posix()

    def outside(self, p):
        try:
            self._abs(p).relative_to(self.root)
            return False
        except ValueError:
            return True

    def linked(self, p):
        """Is p data that the loop linked into this worktree (loop.link_paths)? Its runs read it, so its session may."""
        loop = self.cfg.get("loop") if isinstance(self.cfg.get("loop"), dict) else {}
        pp = self._abs(p)
        return bool(self.outer) and any(under(pp, self._abs(self.outer / lp)) for lp in loop.get("link_paths") or [])

    def canon(self, rel):
        """Map copies of the tree (run snapshots, Claude Code worktrees) back to repository paths."""
        return self._snap_prefix.sub("", rel) if rel else rel

    def resolve_token(self, t):
        t = winpath(t)
        if not any(ch in t for ch in "*?["):
            return self.canon(self.rel(t))
        lead = re.split(r"[*?\[]", t, maxsplit=1)[0]
        head = lead.rsplit("/", 1)[0] if "/" in lead else ""
        tail = t[len(head) + 1:] if head else t
        base = self.rel(head) if head else self.rel(".")
        if base in (None, "", "."):
            return self.canon(tail)
        return self.canon(base.rstrip("/") + "/" + tail)

    def protected(self):
        return [*(self.cfg.get("sealed_paths") or []), *self.frozen(), *(self.cfg.get("harness_paths") or [])]

    def expand(self, t):
        """Paths a wildcard word names on disk now, as repository paths: the first GLOB of them, and of those behind
        them each one that a rule of this guard keeps (sealed, frozen, harness, a run's, git's own), so that no
        number of other files hides it. Behind the first GLOB a file costs no look of its own, only its folder does,
        so a wildcard over a large data folder stays quick. Where WALK_S seconds do not reach the last match,
        self.cut is the word: the rest is unread, and main() asks."""
        key = (self.cwd, t)
        if key in self._globs:  # a line is read several times over, and from each folder it changes to
            return self._globs[key]
        out, seen, n = self._globs.setdefault(key, []), {}, 0
        pats = self.protected()
        leads = [re.split(r"[*?\[]", norm_pattern(p).lower() if NOCASE else norm_pattern(p))[0] for p in pats]

        def near(folder):  # may a kept file lie in it or below? None matches a pattern without starting as it does
            low = folder.lower() if NOCASE else folder
            return any(low.startswith(x) or x.startswith(low) for x in leads)
        try:
            for n, f in enumerate(glob.iglob(str(self._abs(t)))):
                if n < GLOB:
                    out.append(self.canon(self.rel(f)))
                    continue
                if time.time() > self.t0 + WALK_S:
                    self.cut = t
                    break
                d, name = os.path.split(f.rstrip("/\\"))
                if d not in seen:  # folder -> its repository path, its folders and links, can a rule keep a file in it
                    with os.scandir(d) as es:
                        links = {os.path.normcase(e.name) for e in es if e.is_symlink() or e.is_dir()}
                    at = self.rel(d)
                    at = self.canon("" if at in ("", ".") else at.rstrip("/") + "/")
                    seen[d] = at, links, at.startswith(self.runs_dir + "/") or "/.git/" in "/" + at or near(at)
                at, links, kept = seen[d]
                if os.path.normcase(name) in links:  # may lead elsewhere: looked up in full, like the first ones
                    rel = self.canon(self.rel(f))
                    above = near(rel.rstrip("/") + "/")  # a folder that holds kept files: a recursive command enters it
                elif kept:
                    rel, above = at + name, False
                else:
                    continue
                if above or matches(rel, pats) or re.search(r"(?:^|/)\.git(?:/|$)", rel, _CASE) or \
                        (rel + "/").startswith(self.runs_dir + "/"):
                    out.append(rel)
        except (OSError, ValueError, re.error):
            if n >= GLOB:  # a folder that cannot be listed: what lies behind it is unread
                self.cut = t
        return out

    def frozen(self):
        """frozen_paths plus what the loop checksums or links into its worktrees: none of it is the agent's to edit."""
        loop = self.cfg.get("loop") if isinstance(self.cfg.get("loop"), dict) else {}
        return [p for k in (self.cfg.get("frozen_paths"), loop.get("protected_data"), loop.get("link_paths"))
                for p in (k or [])]

    def active(self):
        if self._active is None:
            self._active = []
            if self.expctl:
                try:
                    self._active = [r for r in self.expctl.scan(self.root, self.cfg)
                                    if r.get("state") in self.expctl.ACTIVE_STATES]
                except Exception:  # noqa: BLE001
                    self._active = []
        return self._active

    def external_jobs(self):
        return [j for j in (self.cfg.get("external_jobs") or []) if j]

    def live_desc(self):
        parts = [f"{r['run_id']} (pid {r.get('pid')}, {r['state']})" for r in self.active()[:5]]
        parts += [json.dumps(j)[:80] for j in self.external_jobs()[:3]]
        return ", ".join(parts) or "none recorded"


def names_sealed(ctx: Ctx, text: str, dirs):
    """(the words, what they are) for the first thing in a text that names sealed data: an unsealing token, or a
    sealed path, written out or joined from literals, or a wildcard over the sealed folder's parent, as seen from
    one of the folders `dirs`. None if nothing does. The whole text is read; where it has more path-like words than
    WALK_S seconds allow to look up, the answer is (None, why): the rest is unchecked, and the caller asks."""
    sealed = ctx.cfg.get("sealed_paths")
    came, text = text, re.sub(r"\\+", "/", text)
    for tok in ctx.cfg.get("sealed_tokens") or []:
        if tok and tok in text:
            return tok, "the test-unsealing token"
    for pat, rx in fragments(sealed):
        m = rx.search(text)
        if m:
            return m.group(), f"sealed path pattern '{pat}'"
    pat = sweeps_sealed(text, ctx.root, sealed, False)  # glob('data/*/x.csv'), whatever lies on disk today
    if pat:
        return pat, "a wildcard over the folder that holds this sealed path pattern"
    words = dict.fromkeys(WORDS.findall(text) + [q.group()[1:-1] for q in QUOTED.finditer(text)] + joined(came))
    words = [w for w in words if "/" in w.strip("/") and len(w) < 300]
    here = ctx.cwd
    try:
        for n, w in enumerate(words):
            if time.time() > ctx.t0 + WALK_S:
                return None, (f"This text has {len(words)} path-like words, more than this guard could look up in "
                              f"{WALK_S:g} seconds: {len(words) - n} are unchecked, and one of them may name sealed "
                              f"test data. Approve only if none does, or write the text in smaller parts.")
            for d in dict.fromkeys(dirs):
                ctx.cwd = d
                for rel in [ctx.resolve_token(w)] + (ctx.expand(w) if any(ch in w for ch in "*?[") else []):
                    hit = matches(rel, sealed) if rel and not any(ch in rel for ch in "*?[") else None
                    if hit:
                        return w, f"sealed path pattern '{hit}'"
    finally:
        ctx.cwd = here
    return None


def check_path_tool(ctx: Ctx, tool, ti):
    cfg = ctx.cfg
    paths, search = [], None
    if tool in ("Read", "NotebookRead", "LS", "Other"):
        paths = [ti.get("file_path") or ti.get("notebook_path") or ti.get("path")]
    elif tool in ("Grep", "Glob"):
        base = ti.get("path") or ti.get("file_path")  # Cursor names the search base file_path
        paths = [base] if base else []
        pat = ti.get("pattern") if tool == "Glob" else ti.get("glob")
        pats = [pat] if isinstance(pat, str) and pat else []
        if tool == "Grep":  # Claude Code hands rg each part between blanks, and between commas where it has no braces
            pats = [g for part in pat.split() for g in ([part] if "{" in part and "}" in part else part.split(",")) if g] \
                if pats else []
        search = (base, pats)
        for g in pats:
            lit = re.split(r"[*?\[]", (str(base).rstrip("/") + "/" + g) if base else g)[0]
            if lit:
                paths.append(lit)
    elif tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        paths = [ti.get("file_path") or ti.get("notebook_path")]
    results = []
    for p in [x for x in paths if x]:
        if os.environ.get("NN_UNATTENDED") == "1" and ctx.outside(p) and not (tool in READ_TOOLS and ctx.linked(p)):
            results.append((DENY, f"'{p}' is outside this project, and this session runs unattended "
                                  f"(NN_UNATTENDED=1): its file tools stay inside the project folder."))
            continue
        raw = ctx.rel(p)
        rel = ctx.canon(raw)
        hit = matches(rel, cfg.get("sealed_paths")) or matches(raw, cfg.get("sealed_paths"))
        if hit:
            results.append((DENY, f"'{raw}' is sealed by the nn-training protocol (pattern '{hit}'): final test data "
                                  f"stays outside all tuning feedback. Use `expctl final-eval` once the "
                                  f"selection procedure is frozen, and ask the user first."))
            continue
        if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            for r in ctx.active():
                rd = (r.get("dir") or "").rstrip("/")
                if rd and (raw == rd or raw.startswith(rd + "/")):
                    results.append((DENY, f"'{raw}' belongs to active run {r['run_id']}; its files and code snapshot "
                                          f"are immutable while it runs. Change code for the NEXT run in the working "
                                          f"tree (or a git worktree) instead."))
                    break
            hit = matches(rel, ctx.frozen())
            if hit:
                results.append((ASK, f"'{raw}' is a frozen evaluation/protocol file (pattern '{hit}'). Changing it "
                                     f"creates a new protocol version: results before and after are not comparable "
                                     f"and the baseline must be re-established. Approve only if this is intended."))
            hit = matches(rel, cfg.get("harness_paths")) or matches(raw, cfg.get("harness_paths"))
            if hit:
                results.append((ASK, f"'{raw}' is part of the training harness guardrails (pattern '{hit}'). "
                                     f"Approve only if you intend to change the harness configuration."))
            if re.search(r"(?:^|/)\.git(?:/|$)", raw, _CASE):
                results.append((ASK, f"'{raw}' is one of git's own files; this guard reads the repository's "
                                     f"worktrees from them. Approve only if you intend to change them by hand."))
    if search and not results:  # a search names no sealed file, yet may sweep the folder that holds them
        grep = tool == "Grep"  # its globs are ripgrep's; the folder it runs ripgrep in is not known here
        hit = reaches_sealed(ctx, search[0], [x for g in search[1] for x in rg_glob(g)] if grep else search[1],
                             ti.get("type") if grep else None, grep and not rg_config())
        if hit:
            results.append((DENY, f"This search would {'read' if tool == 'Grep' else 'list'} sealed test data "
                                  f"(pattern '{hit}'), which stays outside all tuning feedback. Narrow it: give a "
                                  f"path that leaves the sealed files out (the source folder, say), or a glob they "
                                  f"do not match (such as '*.py')."))
    # What a call writes into a file, or hands to an MCP tool, is read as well: code or a query that names the sealed
    # data would read it later, outside this guard. Not notes, and not the guard's own configuration, which names it
    file = str(ti.get("file_path") or "")
    if ti.get("text") and not any(k == DENY for k, _ in results) and not (
            tool != "Other" and re.search(NOTES + r"$|(?:^|/)\.claude/nn-training\.json$", winpath(file), re.I)):
        hit = names_sealed(ctx, ti["text"], [ctx.root, ctx.cwd] + ([ctx._abs(file).parent] if file else []))
        if hit and hit[0] is None:
            results.append((ASK, hit[1]))
        elif hit and tool == "Other":
            results.append((ASK, f"This call's arguments name sealed test data: '{hit[0][:80]}' ({hit[1]}). Approve only "
                                 f"if the tool cannot read or expose sealed content."))
        elif hit:
            results.append((ASK, f"The new text of '{ctx.rel(file)}' names sealed test data: '{hit[0][:80]}' ({hit[1]}). "
                                 f"Code and configuration that a run reads before the final evaluation must not point at "
                                 f"the test split. Approve only if nothing would read sealed data through this file "
                                 f"before `expctl final-eval`."))
        if runs_notes(ti["text"], False, True):
            results.append((ASK, NOTES_RUN))
    return results


def words(ctx: Ctx, toks):
    """A command's words in a form that compares: an interpreter by its plain name, a file by its project path."""
    out = []
    for t in toks:
        if re.fullmatch(r"python[\d.]*|py", re.sub(r"\.exe$", "", t.rsplit("/", 1)[-1].lower())):
            out.append("python")
        else:
            out.append("@" + str(ctx.resolve_token(t)) if t[:1] != "-" and ctx._abs(t).is_file() else t)
    return out


def runs_final(seg, fin):
    """Does the command `seg` run the final-evaluation command `fin` (both as words() gives them)? Another spelling
    of the interpreter or of the script, wrappers in front, interpreter options and further arguments still count.
    A rail against running it by mistake, not a wall: a wrapper script passes (sealed_tokens is the stronger rule)."""
    env = list(itertools.takewhile(ASSIGN.match, fin))  # NAME=value in front: the command must carry them too
    core = fin[len(env):]
    core = core[core.index("python"):] if "python" in core else core
    first = next((i for i, t in enumerate(seg) if not ASSIGN.match(t)), len(seg))  # where the command's program is
    if not core or any(t not in seg for t in env):
        return False
    if len(core) == 1:
        return seg[first:first + 1] == core
    for j in range(first, len(seg)):  # the script, right after its interpreter or run by itself, then the rest
        before = [t for t in seg[first:j] if t[:1] != "-"]
        if seg[j] == core[1] and (before[-1:] == core[:1] or (j == first and seg[j][:1] == "@")) \
                and all(t in seg[j + 1:] for t in core[2:]):
            return True
    return False


def plain(cmd: str) -> str:
    """A command line in the form the rules of check_bash read: a backslash is a folder separator, find's two ends
    of a command are one, a command word in quotes is the same command, and .NET's AllDirectories, which mostly
    comes as a string, stands bare."""
    raw = FIND_END.sub(r"\1+", cmd.replace("\\", "/"))
    return re.sub(r"(?i)(['\"])(AllDirectories)\1", r"\2", QUOTED_COMMAND.sub(r"\1\3", raw))


def check_bash(ctx: Ctx, cmd: str, depth=0, alt=True, sh=True):
    """alt: also check the line as another shell reads it. sh: the text may be a POSIX shell's (the line of a tool
    call, or text handed to a shell), where a brace list stands for names."""
    cfg = ctx.cfg
    raw = plain(cmd)
    c = GIT_GLOBAL.sub("git", raw)
    c_noq = QUOTED.sub(" '' ", c)
    results = []
    if depth == 0:  # a POSIX line may hand text to PowerShell or cmd: then their reading holds for the whole line
        ctx.recursive_re = RECURSIVE_POSIX if ctx.posix and not re.search(r"\b(?:powershell|pwsh|cmd)\b", c, re.I) \
            else RECURSIVE
    code = depth > 0 or bool(SHELLS.search(c_noq))  # program text may be in here: its string literals can be paths
    toks = shell_tokens(c)
    # git -C <dir> runs git in that folder, and env -C <dir> its command: the folder counts as named, and the
    # command's paths are relative to it
    moves = [(g.start(), False, [d.strip("\"'") for d in re.findall(r"-C\s+(\S+)", g.group(1))])
             for g in GIT_GLOBAL.finditer(raw)] + [(y.start(), False, [y.group(2).strip("\"'")]) for y in ENV_C.finditer(raw)]
    toks += [d for _, _, ds in moves for d in ds]
    # git's <rev>:<path> (git show HEAD:data/x) names a repository file: checked from this folder and from git's top
    parts = [t.rsplit(":", 1)[1] for t in toks if ":" in t] if re.search(r"\bgit\b", c) else []
    top = git_top(ctx.root) or ctx.root if parts else None
    for part in parts:
        if part[:1] not in ("", "/"):
            toks += [part, (top / part).as_posix()]
    if code:
        toks += [q for q in (m.group(0)[1:-1] for m in QUOTED.finditer(c)) if 0 < len(q) < 300 and not re.search(r"\s", q)]
    # Path('data') / 'test', os.path.join('data', 'test'): the path they build counts as named. Read from the line as
    # it came: above, a quoted word where a command may start lost its quotes. Text inside a literal is read only
    # where the line hands text to an interpreter: a commit message may quote such code. A here-document is code too
    toks += joined(cmd, 0 if code else 2, "<<" in cmd)
    here = cur = ctx.cwd
    dirs = [here]
    moves += [(m.start(), True, [re.sub(r"[\"']", "", m.group(1))]) for m in CD.finditer(raw)]
    for _, cd, ds in sorted(moves):  # a cd earlier in the line: what follows is relative to it
        for d in ds:
            ctx.cwd = cur if d is ds[0] else dirs[-1]
            dirs.append(ctx._abs(d))
        cur = dirs[-1] if cd else cur
    dirs = list(dict.fromkeys(dirs))
    resolved = []
    for d in dirs:
        ctx.cwd = d
        for t in toks:
            resolved.append((t, ctx.resolve_token(t)))
            if any(ch in t for ch in "*?["):  # a wildcard: also what it names on disk now
                resolved += [(t, r) for r in ctx.expand(t)]

    def on_disk(d, t):  # what the path t names on disk, seen from the folder d
        ctx.cwd = d
        return ctx.expand(t) if any(ch in t for ch in "*?[") else [ctx.resolve_token(t)] * os.path.exists(ctx._abs(t))

    # A folder that the line names where the guard reads no change of folder (sudo -D data, start /D data, a
    # program's own option): a path that leads nowhere from the folders above, and to something below that folder,
    # is read from there as well
    lost = [t for t in toks if "/" in t.strip("/") and t[:1] not in "/~" and ":" not in t
            and not any(on_disk(d, t) for d in dirs)]
    also = []
    for d in dirs if lost else []:
        ctx.cwd = d
        also += [ctx._abs(t) for t in toks if not t.startswith("//")]
    for d in [d for d in dict.fromkeys(also) if d not in dirs and os.path.isdir(d)]:
        resolved += [(t, rel) for t in lost for rel in on_disk(d, t)]
    is_final = False
    finals = [str(x).replace("\\", "/") for x in cfg.get("final_eval_commands") or [] if str(x).strip()]
    if finals:  # compared command by command (a chain, cmd /c ...), from every folder the line moves to
        ctx.cwd = ctx.root
        fins = [words(ctx, lex(x)) for x in finals]
        segs = [list(g) for sep, g in itertools.groupby(lex(c), lambda t: not t.strip(";&|()")) if not sep]
        for d in dirs:
            ctx.cwd = d
            is_final = is_final or any(runs_final(words(ctx, s), f) for s in segs for f in fins)
    ctx.cwd = here
    sealed = cfg.get("sealed_paths")
    if is_final:
        results.append((DENY, "This is the configured FINAL evaluation command. It runs only through `expctl.py "
                              "final-eval` (further arguments after `--`), which keeps a receipt of every use of the "
                              "test split; the guard then asks the user."))
    else:
        for tok, rel in resolved:
            hit = matches(rel, sealed) if rel and not any(ch in rel for ch in "*?[") else None
            if hit:
                results.append((DENY, f"'{tok}' resolves to sealed path pattern '{hit}' (final test data). Only the "
                                      f"configured final evaluation may touch it, started with `expctl final-eval` "
                                      f"and the user's approval."))
                break
        for tok in cfg.get("sealed_tokens") or []:
            if tok and tok in c:
                results.append((DENY, f"Command uses the test-unsealing token '{tok}'. Only the configured final "
                                      f"evaluation may use it, started with `expctl final-eval` and the user's approval."))
                break
        if not results:
            for pat, rx in fragments(sealed):
                if rx.search(c):
                    results.append((ASK, f"Command mentions sealed path pattern '{pat}' (final test data). Approve only "
                                         f"if it cannot read or expose sealed content."))
                    break
        if not results:
            # program text that an interpreter runs: a call in it may walk a tree, and so may a ** in one of its strings
            prog = bool(HERE_RUN.search(c) or PIPED.search(c_noq)) if "<<" in cmd else depth > 0
            recursive = bool(ctx.recursive_re.search(c_noq) or re.search(r"\bgit\s+grep\b", c_noq)
                             or (prog and PY_WALK.search(c_noq)))
            # a name that a search leaves out is not swept, unless the line names it as a path as well
            rest = SEARCH_EXCL.sub(" ", c)
            left = {y.group(2).strip("\"'") for y in SEARCH_EXCL.finditer(c)} - set(shell_tokens(rest))
            pseudo = " ".join(rel for t, rel in resolved if rel and t not in left)
            hit = swept = sweeps_sealed(rest, ctx.root, sealed, recursive) or \
                sweeps_sealed(pseudo, ctx.root, sealed, recursive)
            # then each command of the line by itself, with its own tool, file filters and folder: do sealed files
            # lie below a folder that it names, or below the one it runs in?
            curs, chain, stack, moved = [here], None, [], False  # curs: the folders in which the next command may run
            taken = None
            parts = SEPARATOR.split(QUOTED.sub(lambda q: SEPARATOR.sub(" ", q.group()), raw)) \
                if (recursive or MOVE.search(c_noq) or STARS.search(c_noq) or GIT_TAKES.search(c_noq)
                    or (prog and "**" in c)) and not hit else []
            for i in range(0, len(parts), 2):
                seg, before, after = parts[i].lstrip(), "".join(parts[i - 1:i]), "".join(parts[i + 1:i + 2])
                sq = QUOTED.sub(" '' ", ENV_C.sub(r"\1", GIT_GLOBAL.sub("git", seg)))
                stack += [curs] * sq.count("(")  # a subshell: a cd in it ends with it
                chain = chain if before == "&&" else None  # the folders behind a cd that && joins this command to
                x = CD.match(seg)
                py = list(PY_WALK.finditer(sq)) if prog else []
                found = list(ctx.recursive_re.finditer(sq)) + py or list(MOVE.finditer(sq))
                runs = curs if chain is None else chain  # the folders in which this command may run
                for d in re.findall(r"-C\s+(\S+)", " ".join(g.group(1) for g in GIT_GLOBAL.finditer(seg))) + \
                        [y.group(2) for y in ENV_C.finditer(seg)]:  # git -C dir, env -C dir: this one runs in dir
                    was, runs = runs, []
                    for r in was:
                        ctx.cwd = r
                        runs.append(ctx._abs(d.strip("\"'")))
                if x or re.match(r"(?:popd|Pop-Location)\b", seg, re.I):
                    to = []
                    for d in curs if x else []:
                        ctx.cwd = d
                        to += [t for t in [ctx._abs(re.sub(r"[\"']", "", x.group(1)))] if t.is_dir()]
                    # it replaces the folder when it surely runs (first, or after ; or a new line) and surely works:
                    # a redirection to a file that cannot be opened keeps cd from running.
                    # Otherwise the folders before it stay possible, and with a target the guard cannot follow
                    # (a variable, cd -, popd) every folder that the line visits.
                    # shortcut: follows 8 possible folders, the earliest first; raise it if lines with more turn up
                    holds = len(to) == len(curs) and before in ("", ";", "\n") and after in ("", ";", "\n", "&&", "||") \
                        and re.match(r"[({\s]*(?:(?:time|command|builtin)\s+)*" + _CD_WORD + r"\s", seg, re.I) \
                        and not re.search(r"[<>](?!\s*/dev/null\b)", sq)
                    chain = to if to and after == "&&" else None
                    curs = list(dict.fromkeys(to if holds else curs + (to or dirs)))
                elif GIT_TAKES.search(sq):  # the folders it names, or the whole checkout: no path, a stash, :(magic)
                    lx = lex(GIT_GLOBAL.sub("git", seg))
                    k = next((j for j, t in enumerate(lx) if t in ("add", "stash")), len(lx))
                    args = [t for t in lx[k + 1:] if t[:1] != "-"]
                    whole = lx[k:k + 1] == ["stash"] or not args or any(t[:1] == ":" for t in args)
                    for d in runs:
                        ctx.cwd = d
                        for t in ["."] if whole else args:
                            own = max((x for x in ctx.bases if under(ctx._abs(t), x)), key=lambda x: len(x.parts),
                                      default=ctx.root)
                            for rel in [""] if whole else [ctx.resolve_token(t)] + (
                                    ctx.expand(t) if any(ch in t for ch in "*?[") else []):
                                if rel is not None and not any(ch in rel for ch in "*?[") and os.path.isdir(own / rel):
                                    taken = taken or searched(ctx, str(own / rel), [], None, False, None)
                elif found or re.search(r"\bgit\s+grep\b", sq):
                    names = [m.group(0).split()[0] for m in found]
                    tools = {re.sub(r"\.exe$", "", n.lower()) for n in names}
                    ps = any(m.groupdict().get("ps") for m in found)  # written PowerShell's or cmd's way
                    rg = tools <= {"rg", "ag"}  # so is a `git grep` alone: it reads what git tracks
                    # told to pass over the ignore rules or to follow links, on the line or in ripgrep's configuration
                    # file, it reads what any other tool reads. A line that names that file's variable may set another
                    rgish = rg and not UNRESTRICTED.search(sq) and not (
                        "rg" in tools and "--no-config" not in sq and ("ripgrep_config_path" in c.lower() or rg_config()))
                    tools = tools or {"grep"}
                    # a tool named where a command starts is a command for sure. Only then is the project root itself
                    # checked: the words find and tree also turn up in text that a line writes to a file
                    first = ps or py or any(COMMAND_START.match(sq[:m.start()]) and re.match(
                        r"(?:\.exe)?(?:\s+[^=\s]|\s*(?:[)}`]|$))", sq[m.start() + len(n):]) for m, n in zip(found, names))
                    tool = next(iter(tools)) if len(tools) == 1 else ""  # several in one command: each one's rules are off
                    globs, cut = file_filters(seg, sq, tools, ps)
                    typ = SEARCH_TYPE.findall(sq) if tool == "rg" and "--type-add" not in sq else None
                    # where a move goes to is not moved: an option names that place, or it comes last
                    dest = tools <= MOVERS and MOVE_TO.search(cut)
                    # its arguments: what follows the tool, without the file filters, which are cut out where they
                    # stand (a path may be spelled like one of them)
                    lx = lex(MOVE_TO.sub(" ", cut) if dest else cut)
                    k = next((j for j, t in enumerate(lx)
                              if re.sub(r"\.exe$", "", t.rsplit("/", 1)[-1].lower()) in tools), -1)
                    args = search_args(lx[k + 1:], PS_PLAIN if ps else PLAIN.get(tool))
                    if tools <= MOVERS:  # PowerShell moves a list: a,b
                        args = [(t, sure) for a, sure in (args if dest else args[:-1]) for t in a.split(",")]
                    if "alldirectories" in tools or py:  # a call in program text: its folder is a string in the call
                        args = [(q.group(0)[1:-1], True) for q in QUOTED.finditer(seg)
                                if not re.search(r"[*?\[$]", q.group(0))]
                        # the lone string of a call, walk('data'), lost its quotes in plain(): it counts where the
                        # text as it came has them
                        args += [(w, True) for w in re.findall(r"\(\s*([\w./:-]+)(?=[\s)])", sq)
                                 if re.search(r"\(\s*(['\"])" + re.escape(w) + r"\1", cmd.replace("\\", "/"))]
                    if "alldirectories" in tools:  # .NET's relative folder starts where the shell was started,
                        runs = list(dict.fromkeys([here] + runs))  # whatever Set-Location did since
                    k = next((j for j, a in enumerate(args) if a[1]), len(args))
                    if k < len(args) and tools <= PATTERN_FIRST and not (tool in TEXT_OPT and TEXT_OPT[tool].search(sq)):
                        # the text it looks for is its first argument, unless an option gives the text. Behind what
                        # may be the value of an option, that argument may be a path as well
                        args[k:k + 1] = [(args[k][0], False)] * bool(k)
                    if ps:  # there a,b is a list, /s, /mir and /s/b are switches, and a wildcard is a filter on the
                        # whole tree of its folder: the folder counts, not the filter
                        args = [((t.rsplit("/", 1)[0] if "/" in t else ".") if any(ch in t for ch in "*?[") else t, sure)
                                for a, sure in args for t in a.split(",")
                                if t and not re.match(r"(?:/[^/]*|(?:/[a-zA-Z?](?::[^/]*)?)+)$", t)]
                    bases, named = [], False  # named: the command gives a path of its own, so it does not take the cwd
                    for d in runs:
                        ctx.cwd = d
                        for t, sure in args:
                            # the folder in the checkout that the path lies in: what is on disk there decides
                            own = max((x for x in ctx.bases if under(ctx._abs(t), x)), key=lambda x: len(x.parts),
                                      default=ctx.root)
                            got = []
                            for rel in [ctx.resolve_token(t)] + (ctx.expand(t) if any(ch in t for ch in "*?[") else []):
                                if rel and not any(ch in rel for ch in "*?["):
                                    if os.path.isdir(own / rel):
                                        got.append(str(own / rel))
                                    named = named or sure and ("/" in t or os.path.exists(own / rel))
                            if len(got) > 8:  # a wildcard over many folders:
                                got = [os.path.commonpath(got)]  # the folder that holds them all
                            bases += got
                    if not named and (py or tools & CWD_SEARCH):
                        bases += [str(d) for d in runs]
                    for b in dict.fromkeys(bases):  # the folders a command names itself are looked at one by one
                        # a tool word that does not start a command: the project root stays unasked, as before.
                        # ripgrep-like tools are checked there as well, because they skip what git ignores.
                        if first or rg or ctx.rel(b) != ".":
                            s = searched(ctx, b, globs, typ, rgish, runs[0] if tool == "rg" and len(runs) == 1 else None)
                            moved, hit = moved or bool(s and not hit and tools <= MOVERS), hit or s
                # cat **/*.csv: a shell that reads ** so walks the tree by itself. In program text the ** stands in a
                # string: glob('**/*.csv', recursive=True), Path('.').glob('**/*')
                lits = " ".join(q.group(0)[1:-1] for q in QUOTED.finditer(seg)) if prog else ""
                for y in STARS.finditer(sq + " " + lits):
                    lead, rest = re.split(r"\*{2,}", y.group(0), 1)
                    lead, name = re.split(r"[*?\[]", lead)[0], rest.strip("/")
                    for d in runs:
                        ctx.cwd = d
                        b = ctx._abs(lead[:lead.rfind("/") + 1] or ".")
                        if b.is_dir():  # what follows the ** is a filter on the files below that folder
                            hit = hit or searched(ctx, str(b), [name, name + "/**"] if name else [], None, False, None)
                for _ in range(min(sq.count(")"), len(stack))):
                    curs, chain = stack.pop(), None
            ctx.cwd = here
            if hit and moved:
                results.append((ASK, f"Moves or renames a folder that holds sealed path '{hit}' (final test data): "
                                     f"under another name its files are sealed no longer. Approve only if "
                                     f"sealed_paths in .claude/nn-training.json follows the move."))
            elif hit:  # a file filter helps only where the files on disk decided, not where the folder's name did
                way = "" if swept else (", or give a file filter that leaves the sealed files out (--include='*.py', "
                                        "-name '*.py', -Filter '*.py')")
                results.append((ASK, f"Recursive or wildcard command over the folder that holds sealed path '{hit}': "
                                     f"it would read sealed test files indirectly. Name the folders to search instead "
                                     f"(e.g. data/train){way}, or approve only if no sealed content can reach the "
                                     f"output."))
            if taken:
                results.append((ASK, f"Puts files that git ignores into git's store (a forced add, or a stash of "
                                     f"everything) from a folder that holds sealed path '{taken}' (final test data): "
                                     f"`git diff --cached`, `git show` and `git stash show -p` would then print them. "
                                     f"Add the files you mean by name, or approve only if no sealed file is among "
                                     f"them."))
    if WRITE_VERBS.search(c_noq) or PS_WRITE.search(c_noq) or (code and PY_WRITES.search(c)):
        if any(matches(rel, cfg.get("harness_paths")) for _, rel in resolved) or \
                any(rx.search(c) for _, rx in fragments(cfg.get("harness_paths"))):
            results.append((ASK, "Command may modify harness guardrail files (hooks, settings, guard config, skill, "
                                 "agents, CLAUDE.md, .mcp.json). Approve only if intended."))
        if any(matches(rel, ctx.frozen()) for _, rel in resolved) or \
                any(rx.search(c) for _, rx in fragments(ctx.frozen())):
            results.append((ASK, "Command may modify frozen evaluation/protocol files: that creates a new protocol "
                                 "version and requires re-baselining."))
        if any(rel and re.search(r"(?:^|/)\.git/(?:worktrees/|hooks/|config$|nn-training-final-eval\.jsonl$)", rel, _CASE)
               for _, rel in resolved):
            results.append((ASK, "Command may modify files in git's own folder: its list of worktrees, from which this "
                                 "guard reads the repository's other checkouts, its hooks or its configuration, which "
                                 "make git run programs that this guard does not see, or the record of the final "
                                 "evaluation's uses that every checkout shares. Approve only if intended."))
        for r in ctx.active():
            rd = (r.get("dir") or "").rstrip("/")
            if rd and any(rel == rd or rel.startswith(rd + "/") for _, rel in resolved):
                results.append((ASK, f"Command may write into active run {r['run_id']}; its files and snapshot are "
                                     f"evidence and must not change while it runs."))
                break
    if KILL.search(c) or PS_KILL.search(c):
        results.append((ASK, f"Stop/kill command. Live work: {ctx.live_desc()}. Never stop a job without the user's "
                             f"explicit OK in chat; for harness runs prefer `expctl stop <run>` (graceful, checkpoints)."))
    if (RM_ANY.search(c) or FIND_DELETE.search(c) or PS_DELETE.search(c_noq)) and (
            any(rel == ctx.runs_dir or rel.startswith(ctx.runs_dir + "/") for _, rel in resolved if rel)
            or CKPT_HINT.search(c)):
        results.append((ASK, "Deletes run directories or checkpoints. Deleting experiment artifacts needs the user's "
                             "explicit approval (they are evidence for reported results)."))
    if GIT_DESTRUCTIVE.search(c):
        results.append((ASK, "Destructive git operation (may discard uncommitted work or rewrite history). Needs the "
                             "user's explicit approval."))
    elif GIT_PUSH.search(c):
        results.append((ASK, "git push publishes code; it needs the user's explicit approval."))
    setting = git_runs(raw) or "".join(m.group() for m in [GIT_ENV.search(c)] if m)
    if setting:
        results.append((ASK, f"Gives git a setting that can make it start a program by itself, later and outside this "
                             f"guard (a hooks folder, core.fsmonitor, an alias, a pager, an ssh command), or changes "
                             f"git's settings in a way this guard cannot read: '{setting[:80]}'. Approve only if you "
                             f"know what git would run."))
    if PUBLISH.search(c):
        results.append((ASK, "Publishes or uploads outside this machine (model hub, package index, registry or "
                             "GitHub). It needs the user's explicit approval."))
    elif GIT_TREE_CHANGE.search(c):
        live_tree = [r for r in ctx.active() if r.get("cwd")
                     and not (ctx.rel(r["cwd"]) or "").startswith(ctx.runs_dir + "/")]
        if live_tree:
            results.append((ASK, "Changes files in the working tree while run(s) execute directly from it (no "
                                 f"snapshot): {', '.join(r['run_id'] for r in live_tree[:5])}. Code edits can leak "
                                 f"into running jobs (spawned dataloader workers, lazy imports, resumes)."))
    if PAID_COMPUTE.search(c_noq):
        results.append((ASK, "Starts paid compute directly, outside the harness's spending cap. Use the remote "
                             "module (nnremote.py, which needs a cap set by the user) or get the user's explicit "
                             "approval."))
    if LOOP_CTL.search(c):
        results.append((ASK, "Starts, resumes or stops unattended or remote work, which spends agent usage, GPU time "
                             "or money on its own. It needs the user's explicit approval of its limits."))
    if FINAL_CTL.search(c):
        results.append((ASK, "Starts the FINAL evaluation on the sealed test split. It is single-use: every use goes "
                             "into a receipt and the journal. Approve only after the model-selection procedure, seed "
                             "and checkpoint rule are frozen and written in the journal; a repeated use (--again) is "
                             "another look at the test data."))
    if AUDIT_CTL.search(c) and (cfg.get("sealed_paths") or cfg.get("sealed_tokens")):
        results.append((ASK, "Counts the records that the configured splits share. It prints no row, but where a split "
                             "is sealed each count is a small look at it, and audits repeated on changed data could "
                             "probe which records it holds. Approve it when the data or the splits changed, not as a "
                             "routine; every audit is recorded in .claude/state/final-eval/split-audits.jsonl."))
    if PIPE_TO_SHELL.search(c):
        results.append((ASK, "Pipes a download straight into an interpreter. Save it, read it, then run it; approve "
                             "only if the source is trusted."))
    if DECODE_TO_SHELL.search(c) or decodes_into_line(c) or DECODE_CALL.search(c_noq):
        results.append((ASK, "Decodes text where this guard cannot read the result: handed to a shell or an "
                             "interpreter, put into a command line, or decoded by code given on the command line. "
                             "Run it as plain text, or approve only if you know what it says."))
    if runs_notes(c, True, False) or ((depth > 0 or "<<" in cmd) and runs_notes(cmd, False, True)):
        results.append((ASK, NOTES_RUN))
    live = bool(ctx.external_jobs()) or bool(ctx.active())
    if live and DEP_CHANGE.search(c):
        results.append((ASK, f"Dependency change while jobs are live ({ctx.live_desc()}). Changing the environment "
                             f"under a running job or study breaks comparability and resumes."))
    elif live and UV_RUN_SYNCING.search(c):
        results.append((ASK, f"`uv run` syncs the environment by default and jobs are live ({ctx.live_desc()}); use "
                             f"`uv run --frozen` (or --no-sync) while runs or studies are active."))
    if depth < 2 and not is_final:  # what it hands to a nested shell or interpreter obeys the same rules, in every
        # folder the line moves to: after `cd data`, the code's test/labels.csv is data/test/labels.csv.
        # First from the line as it came: there the text still has the backslashes that readings() looks at and the
        # quotes of walk('data'). Then from the line as the rules read it, where that gives another text
        seen = set()
        for s in dict.fromkeys(inner_code(GIT_GLOBAL.sub("git", cmd)) + inner_code(c)):
            if plain(s) not in seen:
                seen.add(plain(s))
                for d in dirs:
                    ctx.cwd = d
                    results += check_bash(ctx, s, depth + 1, sh=bool(POSIX_SHELL.search(c_noq)))
        ctx.cwd = here
    others, long = readings(cmd) if alt else ([], False)
    if long and sh:  # program text (python -c "...") has braces of its own
        results.append((ASK, "A word of this command stands for more than 64 names (a brace list such as "
                             "{a,b}{c,d}...), more than this guard writes out to check them. Name the files one by "
                             "one, or approve only if none of them is sealed test data."))
    for other in others:  # every rule above, for the line as another shell reads it
        results += check_bash(ctx, other, depth, False, sh)
    return results


def append_line(path, entry):
    """Append one JSON line to a log that several guard processes may write at the same moment (parallel tool
    calls). On Windows two such appends can land on the same offset, and one line then destroys the other (seen in
    a live session on 11 November 2026; in a test, eight writers at once lost a tenth of their lines). So the
    writer first locks one byte far beyond the end of the file, where no reader meets it; closing the file ends
    the lock."""
    with open(path, "a", encoding="utf-8") as f:
        if os.name == "nt":
            import msvcrt
            for _ in range(300):  # about 3 s; after that it writes unlocked rather than lose the line
                try:
                    os.lseek(f.fileno(), 1 << 40, 0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as e:
                    if e.errno != 13:  # 13 (EACCES): another writer holds the lock; anything else: no locking here
                        break
                    time.sleep(0.01)
            os.lseek(f.fileno(), 0, 2)
        f.write(json.dumps(entry) + "\n")


def audit(root: Path, entry):
    try:
        d = root / ".claude" / "state"
        d.mkdir(parents=True, exist_ok=True)
        log = d / "guard.log"
        if log.exists() and log.stat().st_size > 1_000_000:
            os.replace(log, d / "guard.log.1")
        append_line(log, entry)
    except OSError:
        pass


def check_readonly(tool, ti):
    """Extra rules for the read-only subagents."""
    if tool in EDIT_TOOLS:
        return [(DENY, "Read-only agent: it may not edit files. Report what needs changing to the main session.")]
    if tool != "Bash":
        return []
    why = None
    for cmd in [ti["command"]] + readings(ti["command"])[0]:  # r\m is rm to a POSIX shell
        c = GIT_GLOBAL.sub("git", cmd)
        texts = [QUOTED.sub(" '' ", t) for t in [c] + inner_code(c)]
        if any(WRITE_VERBS.search(t) or PS_WRITE.search(t) for t in texts) or PY_WRITES.search(c):
            why = why or "writes, moves or deletes files"
        elif KILL.search(c) or PS_KILL.search(c):
            why = why or "signals processes"
        elif MUTATING.search(c) or LOOP_CTL.search(c) or FINAL_CTL.search(c):
            why = why or "launches or stops work, or changes the repository or environment"
        elif AUDIT_CTL.search(c):
            why = why or "audits the data splits, which is the main session's step and the user's decision"
    return [(DENY, f"Read-only agent: this command {why}. Use bounded read commands, or report what needs doing "
                   f"to the main session.")] if why else []


def nobody_to_ask(payload, agent):
    """Why an "ask" would not reach a person here, or None when it would."""
    if agent == "codex":
        return "Codex hooks cannot ask"
    if agent == "cursor":
        return "a Cursor hook cannot tell whether a person would see the question"
    if os.environ.get("NN_UNATTENDED") == "1":
        return "this session runs unattended (NN_UNATTENDED=1)"
    # auto mode is not in this list: Claude Code still shows the person a prompt that a hook forces
    # (code.claude.com/docs/en/permission-modes, read 2026-11-11)
    mode = payload.get("permission_mode")
    return f"{mode} is active" if mode in ("bypassPermissions", "dontAsk") else None


def beacon(payload, calls, decision, reason=""):
    """For the unattended loop: one line per checked call in the file NN_GUARD_BEACON names, allows included, so
    that the harness can tell that the guard ran in a session and what it refused."""
    path = os.environ.get("NN_GUARD_BEACON")
    if path:
        ti = calls[0][1] if calls else {}
        try:
            append_line(path, {"tool": calls[0][0] if calls else str(payload.get("tool_name") or "")[:80],
                               "decision": decision, "reason": reason[:300],
                               "input": str(ti.get("command") or ti.get("file_path") or ti.get("path")
                                            or ti.get("pattern") or "")[:300]})
        except OSError:
            pass


def respond(root, payload, fmt, agent, calls, results, unreadable=False):
    if not results:
        beacon(payload, calls, "allow")
        if fmt == "cursor":
            print(json.dumps({"permission": "allow"}))
        return 0
    decision = DENY if any(k == DENY for k, _ in results) else ASK
    reasons = [r for k, r in results if k == decision]
    reason = "nn-training guard: " + " | ".join(dict.fromkeys(reasons))
    if decision == ASK:
        why = nobody_to_ask(payload, agent)
        if why:
            decision = DENY
            reason += (f" | ({why}, so nobody can be asked: denied. If the action is intended, the user runs it "
                       f"themselves or approves it in an interactive Claude Code session.)")
    beacon(payload, calls, decision, reason)
    ti = calls[0][1] if calls else {}
    audit(root, {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "via": agent,
                 "tool": str(payload.get("tool_name") or payload.get("hook_event_name") or "")[:80],
                 "decision": decision, "reason": reason[:600],
                 "input": str(ti.get("command") or ti.get("file_path") or ti.get("path") or ti.get("pattern") or "")[:400],
                 "session": payload.get("session_id") or payload.get("conversation_id"),
                 "agent": payload.get("agent_type")})
    reason = reason[:1500]
    out = ({"permission": decision, "user_message": reason, "agent_message": reason} if fmt == "cursor" else
           {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                   "permissionDecisionReason": reason}})
    if decision == DENY and (agent != "claude" or unreadable):
        sys.stderr.write(reason + "\n")
        if fmt != "codex":  # Codex reads the reason from stderr; its docs define no stdout for a blocking exit
            print(json.dumps(out))
        return 2
    print(json.dumps(out))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    fmt = argv[argv.index("--agent") + 1] if "--agent" in argv[:-1] else "claude"
    only_readonly = "--readonly" in argv
    payload, agent, root = {}, fmt, Path.cwd()
    try:
        try:
            payload = json.loads(sys.stdin.read())
        except (ValueError, RecursionError):  # the second: brackets nested a thousand deep
            payload = None
        if not isinstance(payload, dict):
            payload = {}
            raise Unreadable("it is not a JSON object")
        if "cursor_version" in payload:  # also when Cursor runs the hook it imported from .claude/settings.json
            agent = "cursor"
        try:
            root = find_root(payload)
            calls = calls_from(payload)
        except RecursionError:
            raise Unreadable("its values are nested too deeply") from None
    except Unreadable as e:
        return respond(root, payload, fmt, agent, [], [(DENY, (
            f"this hook input cannot be read ({e}), so the call is refused instead of passing unchecked. Run "
            f"`expctl.py selftest`; if the agent was updated, the kit needs an update too.")[:400])], unreadable=True)
    # The hook has 15 to 20 seconds, and not every agent program blocks a call whose hook did not answer in time. So a
    # check that takes too long (a path on a server that does not answer, a line with very many different searches)
    # is answered by a timer. Whoever takes `mine` first gives the answer
    mine = threading.Lock()

    def late():
        if mine.acquire(False):
            code = respond(root, payload, fmt, agent, calls, [(ASK, (
                f"the guard could not finish checking this call in {LIMIT:g} seconds (a path on a server that does "
                f"not answer, or a line with very many searches?). Approve only if the action is safe."))])
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(code)
    timer = threading.Timer(LIMIT, late)
    timer.daemon = True
    timer.start()
    try:
        ctx = Ctx(payload, root)
        # Codex and Cursor run PowerShell on Windows, and Claude Code has a PowerShell tool of its own
        ctx.posix = agent == "claude" and payload.get("tool_name") == "Bash"
        readonly = only_readonly or payload.get("agent_type") in READONLY_AGENTS
        results = []
        if ctx.cfg.get("_config_error") and not all(
                t == "Read" and ctx.rel(ti.get("file_path") or "") == ".claude/nn-training.json" for t, ti in calls):
            results = [(ASK, f".claude/nn-training.json is unreadable ({str(ctx.cfg['_config_error'])[:200]}), so "
                             f"the training guard cannot check this call, not even for sealed test data. Fix the "
                             f"file (reading it is allowed; edit it with approval) before continuing.")]
        else:
            for tool, ti in calls:
                if readonly:
                    results += check_readonly(tool, ti)
                if not only_readonly:
                    results += check_bash(ctx, ti["command"]) if tool == "Bash" else check_path_tool(ctx, tool, ti)
            if ctx.cut:
                results.append((ASK, f"The wildcard '{ctx.cut[:80]}' names more files than this guard could look at in "
                                     f"{WALK_S:g} seconds: the rest is unchecked, and one of them may be sealed test "
                                     f"data or another protected file. Approve only if none is, or name the files "
                                     f"more narrowly."))
    except Exception as e:  # noqa: BLE001 - fail safe: let the user decide instead of silently allowing
        # a read as well: reading is what the sealed files are kept from, and input can be made to raise an error
        results = [(ASK, f"guard internal error ({type(e).__name__}: {str(e)[:200]}); it could not check this "
                         f"call. Approve only if the action is safe.")]
    if not mine.acquire(False):
        timer.join()  # the timer is giving the answer and ends the process
    return respond(root, payload, fmt, agent, calls, results)


def run():
    """The last net. An agent program takes a hook that crashed (exit code 1) for a hook that failed and lets the
    call go on, so whatever main() did not catch becomes a refusal: exit code 2 with the reason on stderr."""
    try:
        return main()
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"nn-training guard: internal error ({type(e).__name__}: {str(e)[:200]}), so the call is "
                         f"refused instead of passing unchecked. Run `expctl.py selftest`.\n")
        return 2


if __name__ == "__main__":
    sys.exit(run())
