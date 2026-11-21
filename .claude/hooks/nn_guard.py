#!/usr/bin/env python3
"""Tool-call guard for the nn-training harness (stdlib only). One rule set for Claude Code, Codex and Cursor.

Deterministic seatbelts for the failure modes that matter most when an agent runs training
campaigns. It never edits tool input; it answers "deny", "ask" (the user is prompted) or allows.

  deny  paths that resolve to sealed test data (file tools and shell arguments, resolved against
        the session's working directory) and test-unsealing tokens. The rules of every checkout of
        the repository are combined and hold in each; a protected folder that is a link to storage
        elsewhere is protected at both ends
  deny  Edit/Write inside an active run's directory or code snapshot
  deny  a hook input it cannot read (not JSON, nested too deeply to parse, no tool name, a shell
        call without a command, a file call without a path): an unread call is refused, never
        let through
  deny  writes, signals and launches by the read-only subagents (experiment-reviewer, run-analyst)
  ask   anything else that mentions a sealed path (e.g. inside a python -c string, in the text
        an edit writes, in an MCP tool's arguments)
  ask   recursive or wildcard sweeps over the folder that holds sealed data (find, grep -r,
        ls -R, cp -r, tar, rsync, rg, du -a, a tree walk in code on the line, an MCP tool that is
        handed the folder, or globs such as data/*/...), and a forced `git add` or
        `git stash --all` there
  deny  the configured final-evaluation command itself, however its interpreter and script are
        spelled: it runs through `expctl final-eval`, which keeps a receipt of every use
  ask   `expctl final-eval` (each test-set access is a human decision)
  ask   `expctl audit-splits` where the config seals anything (it prints counts only, but each
        count of records shared with a sealed split is a small look at that split)
  ask   edits to frozen evaluation/protocol files, to the harness itself or to git's own files,
        and git settings that make git start a program (core.hooksPath, core.fsmonitor, an alias,
        `git -c`, the GIT_* variables for them)
  ask   kill/stop commands (always: jobs outside the harness are protected too); deleting run
        directories or checkpoints; shell writes into an active run's directory; destructive git;
        any git push; branch switches/pulls while a run executes from the working tree;
        dependency changes (and syncing `uv run`) while harness runs or listed external jobs are live
  ask   commands that start paid compute directly (outside the remote module's spending cap) and
        commands that pipe a download into a shell
  ask   text the guard cannot read before it runs: decoded text that reaches a shell or an
        interpreter (base64 -d | sh, a decoder inside $( ), code that decodes its own text), and
        a notes file (.md, .mdx, .rst) run as code

A command line is read as written and as a POSIX shell and PowerShell would take it (a backslash
inside a name, $'..', a brace list, an escape character). Code behind -c, in PowerShell's
-EncodedCommand and on a runner's standard input is read like a command, from every folder the
line may be in.

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
import errno
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
from urllib.parse import unquote

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
PLACE_KEY = re.compile(r"path|dir|folder|root|cwd|ur[il]|file|location", re.I)  # an MCP tool's argument that names a place
PATCH_FILE = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+?)\s*$|^\*\*\* Move to: (.+?)\s*$", re.M)
QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")
# A redirection writes its target, also behind a descriptor or an & (2> f, &> f) unless that target is the null
# device, and as >& f, which is no copy of a descriptor (>&2, >&-). sed's in-place option counts wherever it stands
# in the command (perl's and ruby's too: perl -p -i -e), git's checkout and restore put a file back as a commit has
# it, and find deletes with -delete. A program's name counts in any case: Windows and a Mac find RM and Sed as well.
_INPLACE = (r"\b(?i:sed)\b[^;&|]*?\s(?:-[a-zA-Z]*[iI]|--in-place)|"
            r"\b(?i:perl|ruby)\b[^;&|]*?\s-[a-zA-Z0-9]*i\b")
# git restore --staged alone changes the index, not the files
_GIT_BACK = (r"\bgit\s+(?:checkout\b|restore\b(?:(?![^;&|]*\s--staged\b)|"
             r"(?=[^;&|]*\s(?:--worktree\b|-[a-zA-Z]*W))))")
# a forced clean deletes what git does not track below the paths it names, and a kept file may be among that. The -f
# counts wherever it stands among the options, and written out (-fd, -d -f, --force). GIT_DESTRUCTIVE asks about the
# same spelling, so that as a write verb this adds a reason to an ask and no ask of its own
_GIT_CLEAN = r"\bgit\s+clean\b(?=[^;&|]*?\s(?:-[a-zA-Z]*f|--force\b))"
_REDIRECT =r"(?<![0-9&])>{1,2}(?!&)|(?<=[0-9&])>(?![>&])(?!\s*(?:/dev/null\b|(?i:\$null|nul)\b))|>&(?!\s*[0-9-])"
# the verbs behind which any path of the line may be the one written
VERBS = re.compile(
    r"\b(?i:mv|cp|rm|rmdir|unlink|chmod|chown|truncate|ln|dd|rsync)\b|" + _INPLACE +
    r"|" + _GIT_BACK + r"|" + _GIT_CLEAN + r"|\b(?i:find)\b[^;&|]*?\s-delete\b|open\([^)]*['\"][wax+]|write_text|"
    r"write_bytes|"
    r"shutil\.(?:rmtree|move|copy)|os\.(?:remove|unlink|rename|replace)")
WRITE_VERBS = re.compile(_REDIRECT + r"|\b(?i:tee|sponge)\b|" + VERBS.pattern)
# A redirection and a tee that starts a command name the file they write: > f, 2>> f, &> f, >| f, | tee -a f g.
# The third group is a tee that stands elsewhere (sudo -D eval tee f): what it writes this does not read. moreutils'
# sponge names its file as tee does (| sponge -a f), and is read as one
_TEE = r"(?i:tee|sponge)"
SAVES = re.compile(r"(?:" + _REDIRECT + r")\|?[ \t]*([^\s;&|<>()]*)|"
                   r"(?:^|[;&|(])[ \t]*" + _TEE + r"(?:\.exe)?((?:[ \t]+[^\s;&|<>()]+)*)(?![^\s;&|<>()])|\b" + _TEE
                   + r"\b()", re.M)
# What follows a tee's first words on its command: a blank, a redirection with its target (< f, <<< "text",
# 2>/dev/null, >&2), or a further word, which is a file that the tee writes as well (tee >/dev/null f, tee <<< "{}" f).
# Until 19 November 2026 the reading of a tee ended at its first redirection, and the files behind it passed unseen
TEE_REST = re.compile(r"[ \t]+|\d*(?:<<<|<>|>\||&>>?|[<>]{1,2}&?)[ \t]*[^\s;&|<>()]*|([^\s;&|<>()]+)")
KILL = re.compile(
    r"(?:^|[\s;&|(`])(?:sudo\s+)?(?:kill|pkill|killall|taskkill)\b|Stop-Process|"
    r"tmux\s+kill-(?:session|server|window|pane)|tmux\s+send-keys\b[^;&|]{0,200}?\bC-[cd]\b|"
    r"screen\s+[^;&|]{0,200}?-X\s+quit|nvidia-smi\s+[^;&|]{0,200}?(?:--gpu-reset|\s-r\b)|\bfuser\b[^;&|]{0,200}?\s-k\b|"
    r"systemctl\s+(?:stop|kill|restart)|docker\s+(?:stop|kill|rm)\b|podman\s+(?:stop|kill|rm)\b|\bscancel\b|"
    r"\bqdel\b|\bbkill\b|\bray\s+stop\b|expctl(?:\.py)?\s+stop\b", re.I)
# git's own options, which stand between `git` and its subcommand: those with a value (which may hold a quoted
# blank), then any other one (-P, --no-pager, --bare, --no-advice ...), so that none hides the subcommand
_GV = r"(?:\"[^\"]*\"|'[^']*'|[^\s'\"])+"
GIT_WORD = re.compile(r"\bgit(?:\.exe)?(?=\s)", re.I)  # GIT and git.exe are git: plain() writes them so
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
# A checkout discards work where it is forced, where -- ends its options, and where a path of it stands for the
# tree or a part of it (., ./, :/, '*.py', which git matches in every folder), wherever its options stand
GIT_DESTRUCTIVE = re.compile(
    _GIT_CLEAN + r"|\bgit\s+(?:reset\s+--hard|"
    r"checkout\b(?=[^;&|]*?\s(?:-[a-zA-Z]*f[a-zA-Z]*(?=[\s;&|)]|$)|--force\b|--(?=[\s;&|)]|$)|"
    r"['\"]?(?:\.\.?/?|:[/(!^][^\s'\"]*|[^\s;&|'\"]*[*?\[][^\s;&|'\"]*)['\"]?(?=\s|$|[;&|)}\"'`])))|"
    r"restore\b(?:(?![^;&|]*\s--staged\b)|(?=[^;&|]*\s(?:--worktree\b|-[a-zA-Z]*W)))|"
    r"stash\s+(?:drop|clear)\b|switch\s+(?:-f\b|--discard-changes)|"
    r"push\b[^;&|]*(?:--force\b|--force-with-lease\b|\s-f\b)|branch\s+-D\b)")
# a forced clean that takes along what git ignores: data, run folders and checkpoints are usually ignored, so this
# is more than an undo of the session's own work (see ROUTINE). Its -x is read on the command's own line and on the
# lines that continue it: chmod -x on the next line is no option of the clean. A ` or ^ before the line's end
# continues it here; a backslash does in the reading that joins such lines (readings), and none stands in the form
# that the rules read. A backslash before \r\n continues a line in no shell
GIT_CLEAN_IGNORED = re.compile(_GIT_CLEAN + r"(?=(?:[^;&|\n]|(?<=[`^])\r?\n)*?(?<=\s)-[a-zA-Z]*[xX])")
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
RM_ANY = re.compile(r"(?:^|[\s;&|(])(?:sudo\s+)?(?i:rm)\s")
FIND_DELETE = re.compile(r"\b(?i:find)\b[^;&|]*\s-delete\b|\bshutil\.rmtree\b|\bos\.(?:remove|unlink)\b")
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
        r"(?<![\w/.-])for\s+/r(?=\s)|"  # cmd's loop over every file of a tree: for /r data %f in (*) do type %f
        r"\b(?:Compress-Archive|robocopy|xcopy|AllDirectories)\b))|"  # AllDirectories: .NET's word for the whole tree
        # a program's name in any case (GREP -r), which Windows and a Mac find as well
        r"\b(?i:find|tree|tar|zip|rsync|rg|ag|rgrep)\b|"
        r"\b(?i:grep|egrep|fgrep|cp|scp|diff)\b[^;|&]{0,200}?\s(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(?=[\s;|&)]|$)|"
        r"\bgit\s+diff\b[^;|&]{0,200}?\s--no-index\b|"  # compares two folders, whatever git ignores
        r"\b(?i:cp)\b[^;|&]{0,200}?\s(?:-[a-zA-Z]*a[a-zA-Z]*|--archive)(?=[\s;|&)]|$)|"  # cp -a copies the tree as well
        # ls -ltr sorts in reverse and chmod -r takes a permission away: there only -R recurses
        r"\b(?i:ls|dir|chmod|chown)\b[^;|&]{0,200}?\s(?:-[a-zA-Z]*R[a-zA-Z]*|--recursive)(?=[\s;|&)]|$)|"
        r"\b(?i:du)\b[^;|&]{0,200}?\s(?:-[a-zA-Z]*a[a-zA-Z]*|--all)(?=[\s;|&)]|$)")  # du -a lists every file of the tree


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
PY_WRITES = re.compile(  # open() counts with a complete write mode ('w', "ab", 'r+'), not with a path that starts with w.
    # Its path may be a call in a call: open(os.path.join(os.getcwd(), name), 'w').
    # pathlib's .rename(x) and .replace(x) count with their one argument (str.replace(a, b) has two), and like
    # .touch( not where a quote and a blank follow the bracket, which is a search for the word: grep "\.replace(" src
    r"open\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*?['\"](?=[rbtU]*[wax+])[rwaxbtU+]{1,4}['\"]|write_text|write_bytes|"
    r"shutil\.(?:rmtree|move|copy)|"
    r"os\.(?:remove|unlink|rename|replace|makedirs|mkdir|truncate|link|symlink)|"
    r"\.(?:(?:rename|replace)\((?![^()]*,)|(?:touch|symlink_to|hardlink_to|link_to)\()(?![\"']?(?:\s|$))|"
    r"\.to_(?:csv|parquet|json)\(|torch\.save|np\.save|\.savefig\(|"
    # since 19 November 2026: a file opened below the built-in open(), a mode that the text gives by a name
    # (open(f, m)), fileinput's edit in place, and an archive that the standard library unpacks
    r"os\.open\(|\bFileIO\(|open\([^(),]*,\s*(?:mode\s*=\s*)?(?!['\"\d])[A-Za-z_][\w.]*\s*[,)]|"
    r"\bfileinput\b[^;\n]*?\binplace\b|(?<!\.str)\.extractall\(|unpack_archive")
# the call with which program text unpacks an archive, and its arguments where they hold no call of their own
# (pandas has a .str.extractall of its own)
PY_UNPACK = re.compile(r"((?<!\.str)\.extractall|unpack_archive)(?:\(([^()]*)\))?")
# A database file is written by what is done with it after this call. The main session is asked where the line names
# a kept file; a read-only agent may open one, as it reads a study's database
PY_OPENS = re.compile(r"sqlite3\.connect")
# Program text in a language whose write calls this guard keeps no list of (node -e, perl -e, ruby -e, php -r): on a
# line that runs one, a call whose name has a word of writing in it counts as a write verb (fs.writeFileSync(...),
# File.write "f", unlink $f, file_put_contents(...), FileUtils.rm_rf(...), write.csv(...)), and so do a call that
# starts a command (system "...", execSync(...)) and a file opened to be written (perl's open(F, ">f"), a mode
# given as , 'w' or = "a+"). The word alone is none (perl -ne 'print if /saved/' reads), and neither is one that
# ends a quoted text (scripts['save']), a write to the screen as a call on its stream (process.stdout.write(...),
# $stderr.write "x"), or node's createHash(, createHmac(, createInterface(, createRequire( and createReadStream(,
# which make no file. Two that read stay refused: a stream given as an argument (PHP's fwrite(STDERR, ...), julia's
# write(stdout, x)), which a variable of that name could be as well, and a regular expression's .exec( in node,
# which in perl and PHP, where a dot joins two texts, is the call that starts a command.
# The language's name is the program's: with a version (lua5.4, julia-1.10, nodejs) or .exe, not a folder or a file
# of that name (grep -rn "writeFile(" node/, perl.pl), nor a file's ending (web/index.php, --include=*.php). A word
# of its own does count, whatever it is there (grep -v node), and so does an ending in a list in braces
# (--include=*.{php,rb}): a brace opens a block of PowerShell too, where the program stands right behind it.
# The name that a word of writing stands in is read to its end once and not given back letter by letter: a call's
# bracket, blank or quote can only follow the whole name
_CALL = r"(?:\s*\(|\s+[\"'$@])"
LANG = re.compile(r"(?<![.*])\b(?:node(?:js)?|deno|bun|perl|ruby|php|lua(?:jit)?|Rscript|julia)(?:-?\d[\d.]*)?(?:\.exe)?"
                  r"(?![\w./\\:-])", re.I)
LANG_WRITES = re.compile(
    r"(?<!(?i:std(?:out|err))\.)(?i:write|append|delet|link|remov|renam|truncat|cop[yi]|mov[ei]|mk(?:dir|path|dtemp)|"
    r"creat(?!e(?:Read|Hash|Hmac|Interface|Require))|save|chmod|chown|touch|put_contents)(?=([\w.]*))\1" + _CALL +
    r"|(?<![a-zA-Z])(?:rm|mv|cp|ln)(?:Sync|dir|_\w+)?" + _CALL +
    r"|\b(?:exec\w*|spawn\w*|system|popen|shell_exec|passthru)" + _CALL +
    r"|\bopen\b[^;\n]*?['\"]\s*(?:\+?>|\+<)|[,=:]\s*['\"][wax]\+?b?t?['\"]|\bsink\s*\(")
# awk writes by a redirection inside its program (print > "f"), into a command it starts (print | "cmd",
# system(...)), and gawk in place. A comparison stands in front of the print, not behind it ($3 > 5 {print}), and a
# > inside a text that it prints is none (printf "%d -> %s\n", NR, $0), nor one inside the text that the shell's
# own printf is given in front of the pipe (printf 'epoch -> loss\n' | awk '{print $1}'). The shell's pipe into awk
# ends a statement as well, so that a printf in front of it does not lend awk the redirections behind its program
# (printf 'x\n' | awk '{print $1}' f 2>&1 | tail -5). The screen and the void
# are no files: print "bad row" > "/dev/stderr", where that name is the whole target and ends the statement (in a
# program in single quotes: in one in double quotes, where the name's own quotes are escaped, it still counts)
AWK = re.compile(r"\b[gmn]?awk\b", re.I)
AWK_WRITES = re.compile(r"\bprintf?\b(?:[^;}|\n\"']|\|(?!\s*[^\s;&|]*awk\b)|\"[^\"\n]*\"|'[^'\n]*')*?"
                        r"(?:>(?!>?\s*\"/dev/(?:stderr|stdout|null|tty)\"\s*(?:[;}\n']|$))|\|&?\s*[\"'])|\bsystem\s*\(|"
                        r"\s-i\s*inplace\b|--include[= ]inplace\b")
# PowerShell and cmd.exe forms of the write, delete and kill rules. Case is ignored; the short aliases count only
# where a command starts (line start, after ; & | ( {, or after cmd's /c).
_AT = r"(?:^|[;&|({`]|\s/[ck]\s)\s*"
PS_WRITE = re.compile(
    r"\b(?:(?:Set|Add|Clear)-Content|Out-File|Tee-Object|(?:Copy|Move|Remove|New|Rename|Set|Clear)-Item(?:Property)?|"
    r"Export-(?:Csv|Clixml)|Expand-Archive|xcopy|robocopy)\b|::(?:Write|Append|Delete|Move|Copy|Create|Replace)\w*\(|"
    # .NET's streams, as a type is written ([IO.StreamWriter], [FileStream], New-Object IO.FileStream), not as a
    # file's name (src/io/filestream.py); ::OpenRead( and ::OpenText( read
    r"::Open(?:Write)?\(|(?:\bIO\.|\[|\bNew-Object\s+)(?:(?:Stream|Binary)Writer|FileStream)\b|"
    r"\.(?:Delete|MoveTo|CopyTo)\(|"  # a file object's own calls: (Get-Item f).Delete()
    + _AT + r"(?:sc|ac|clc|ri|del|erase|rd|copy|move|ren|rename|cpi|mi|ni|rni)\b", re.I | re.M)
PS_DELETE = re.compile(r"\b(?:Remove-Item|Clear-Content)\b|::Delete\(|" + _AT + r"(?:ri|del|erase|rd|rmdir|clc)\b",
                       re.I | re.M)
PS_KILL = re.compile(r"\b(?:Stop-Process|spps|taskkill)\b|\bwmic\b[^;&|]{0,200}?\bterminate\b|\bos\.kill(?:pg)?\(|"
                     r"\.(?:kill|terminate)\(\)", re.I)
# a command that hands text to a nested shell or an interpreter (bash -c "...", python -c "...", cmd /c "...")
SHELLS = re.compile(r"\b(?:(?:ba|z|da|k)?sh|cmd|powershell|pwsh|python[0-9.]*|py|node|perl|ruby|eval|trap|iex|"
                    r"Invoke-Expression|scriptblock|wsl|ssh)\b", re.I)
POSIX_SHELL = re.compile(r"\b(?:(?:ba|z|da|k)?sh|eval|trap|wsl|ssh)\b", re.I)
# the word behind which the text stands: a flag, also in a group of letters (sh -ce, bash -xc, perl -ne) and cut
# short as PowerShell allows (-com), or the command itself (eval "...", trap '...' EXIT)
CODE_FLAG = re.compile(r"^(?:-[a-z]{0,4}c[a-z]{0,6}|-[a-z]{0,4}e|-commandwithargs|--command|--eval|/c|/k|eval|trap|iex|"
                       r"invoke-expression)$", re.I)
# a command whose output the line takes in: $(cat f), `cat f`. Its text is read as a command of its own, because
# quoting starts anew inside it: in "$(cat dat""a/x)" the two quotes are an empty string, not the end of one
SPLICED = re.compile(r"\$\(|`([^`]*)`")
# A call in program text that hands its arguments to a shell or starts them as a program, with the arguments up to
# the bracket that closes the call, past string literals and one pair of brackets inside
_PY_LIT = r"(?:'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")"
PY_CALL = re.compile(r"\b(?:system|popen|Popen|run|call|check_call|check_output|getoutput|exec[lv]p?e?|spawn\w*)\s*\("
                     r"((?:" + _PY_LIT + r"|[^()'\"]|\((?:" + _PY_LIT + r"|[^()'\"])*\))*)", re.S)
# ${name:-word}, ${name-word}, ${name:=word}, ${name:+word}: the shell may read the word in the name's place. The
# name may be a sign (${@:-word}, ${1-word}), and zsh takes none at all (${:-word})
PARAM_WORD = re.compile(r"\$\{[\w@*#?!$\[\]]*?:?[-+=]([^{}]*)\}")
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
# what a shell takes out of a name before it runs the line: see readings()
ANSI_C =re.compile(r"\$'((?:\\.|[^'\\])*)'", re.S)
C_ESCAPE = re.compile(r"\\(x[0-9a-fA-F]{1,2}|u[0-9a-fA-F]{1,4}|U[0-9a-fA-F]{1,8}|[0-7]{1,3}|.)", re.S)
POSIX_PART = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"|\\(.)", re.S)
BRACE_WORD = re.compile(r"[^\s;&|<>()]*\{[^{}\s]*,[^{}\s]*\}[^\s;&|<>()]*")
WIN_ESCAPE = re.compile(r"[`^](?=[\w./\\:-])")
# PowerShell's quoted texts, its comment that ends on the line, and its escape character with what it escapes
PS_PART = re.compile(r"'[^']*'|\"(?:`.|[^\"`])*\"|<#.*?#>|`.", re.S)
PS_LINE = re.compile(PS_PART.pattern + r"|#[^\n]*", re.S)  # and, in the same pass, a comment to the end of the line
# patterns of zsh and ksh that no rule here knows: see wild(). $(..), <(..) and =(..) are no groups: they run commands
GLOB_GROUP = re.compile(r"(?<![$<>=])([@!+?*]?)\(([^()\s]*)\)")
GLOB_FLAG = re.compile(r"\(#[^()\s]*\)[^\s;&|<>()]*")
GLOB_NOT = re.compile(r"(?<=/)\^[^/\s;&|<>()]*|(?<![^\s;&|<>()])\^[^/\s;&|<>()]*(?=/)")
GLOB_BUT = re.compile(r"([^\s;&|<>()~]*[*?\[][^\s;&|<>()~]*)~[\w./*?\[\0][^\s;&|<>()]*")
# text that joins paths from string literals: the gap between two of them, and the calls in which a comma joins
GAP = re.compile(r"[\s()\[\]]*([/,+])[\s()\[\]]*(?:[A-Za-z_][\w.]*\()?\s*|\s*")  # the second: nothing but blanks
JOINER = re.compile(r"(?:\bjoin|joinpath|Path|Combine)\s*\([^()\n;]{0,80}$")
WORDS = re.compile(r"[^\s\x00-\x1f'\"`()\[\]{},;=<>|]+")
WALK, WALK_S = 20000, 5  # files a walk looks at for sure, and the seconds a hook call may spend on the files beyond
# (these seconds, like LIMIT's, are counted on the clock that is never set: until 19 November 2026 on the system's)
GLOB = 200  # matches of a wildcard that are looked up one by one; each one behind them costs a look at its folder
# a change of folder: where a command starts (after blanks too): behind a separator, the ) of a case pattern, a
# shell keyword, a wrapper such as `time` or zsh's noglob, an assignment (X=1 cd data) or a redirection that stands
# first (>log cd data). PowerShell takes -Path:data and a parameter's name cut short
_CD_WORD = r"(?:cd|pushd|chdir|sl|Set-Location|Push-Location)"
_CD_AT = (r"(?:^|[;&|({)])\s*(?:(?:if|then|else|elif|while|until|do|time|command|builtin|eval|noglob|nocorrect|!"
          r"|[a-z_]\w*=\S*|\d*[<>][<>&|]*\s*[^\s;&|()<>]+)\s+)*")
# The folder ends at a redirection (cd data</dev/null), and a shell lets one splice it from pieces (d"at"a, 'da'ta)
CD = re.compile(_CD_AT + _CD_WORD + r"\s+(?:-[lpe]\w*(?::|\s+)|(?:/d|--)\s+)*((?:\"[^\"]*\"|'[^']*'|[^\s;&|)<>'\"]+)+)",
                re.I | re.M)
# MAY_CD: one of these words stands where a word begins. A text without one holds nothing for CD or for what saves()
# asks about a change of folder, and is not searched for it: such a search begins at every separator and reads a
# variable's value on to the next blank, which takes the square of the length of a=1;b=2;c=3;... (see _lead)
MAY_CD = re.compile(r"(?<![\w./-])(?:popd|Pop-Location|" + _CD_WORD + ")", re.I)
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
_WRAP = "sudo|time|timeout|nice|command|exec|env|nohup|setsid|caffeinate|if|then|else|elif|while|until|do|!"
# a wrapper's options, of which some take a value (conda run -n ml, uv run --with black, sudo -u me, xargs -I {},
# and since 19 November 2026 env -C <folder>: a program that counts where a command starts stood unseen behind it)
_LEAD = (r"%(gap)s*(?:(?:(?:%(wrap)s)(?:\s+(?:-[npuIC]|--(?:name|prefix|with|from|python|project|directory|chdir|cd))"
         r"\s+[^\s;&|]+|\s+-\S+|\s+\d\S*)*|[A-Za-z_]\w*=%(blank)s%(value)s)%(gap)s+)*")


def _lead(wrap: str, signs: str = "") -> str:
    """The pattern of what leads to a command's word, with these wrappers. It reads a variable's value (X=1 cmd) up
    to the next blank, with every sign in it, and the blanks behind each of its words with the line breaks in them.
    So in a=1;b=2;c=3 ... cmd each `;` begins a lead that runs on to that one blank, and in a text of lines that each
    set a variable each line begins one that runs on to the last: a search that finds nothing took the square of the
    text's length (0.06 s for 2,000 of a=1; and 6.2 s for 20,000, in each of a dozen patterns, 21 November 2026).
    signs: for a pattern that is only asked whether a command stands somewhere in the text, never where its lead
    begins or what it holds. The signs are those at which that pattern starts by itself, and it must start at a
    line's beginning (^ with re.M) as well. Then a value ends in front of a sign that a blank or another variable
    follows, and the blanks in front of the lead and behind each variable or wrapper in it hold no line break (the
    one behind a variable's `=`, those among a wrapper's options and inside a wrapper of two words, uv run, still
    do): what stands behind such a place is found from there, with the same words behind it, so the answer is the
    one it was, and a row of variables is read once and no longer again from each of its signs.
    And a blank behind a variable's `=` (X= cmd, which the lead also reads as X set to the next word) is taken only
    in front of a word that sets no variable itself. In a= b= c= ... cmd each word was a variable of its own or the
    value of the one before it, both with the same words behind them, so a search that found nothing took 1.6 times
    as long with each word: thirty of them in front of echo 'x' took the guard past its limit (21 November 2026).
    Not so where the lead itself is read (the text a match holds, where it begins, how many there are): the lead
    without signs stays for that, behind a search with signs that says whether it has anything to find.
    What still takes the square: a wrapper's options, which run over the signs in both forms (env -i;env -i;...),
    and the lead without signs on a row of variables in a text that has what it reads (a=1;a=1;... cd sub), which
    for a command word in quotes is every place where one could begin (a=1;a=1;... echo "r${i}": see WORD_ANY). And
    what still grows by a factor with each word: variables set to nothing with a wrapper's word between them (a= env
    a= env ...), a wrapper's options that read in two ways (sudo -u -u -u ...), and the lead without signs on a row
    of variables set to nothing in such a text (a= b= c= ... echo x and black . on the next line)."""
    return _LEAD % ({"wrap": wrap, "gap": r"\s", "blank": r"\s?", "value": r"\S*"} if not signs else
                    {"wrap": wrap, "gap": r"[^\S\n]", "blank": r"(?:\s(?=\S)(?![A-Za-z_]\w*=))?",
                     "value": r"(?:(?![%s](?:[A-Za-z_]\w*=|\s))\S)*" % signs})


COMMAND_START = re.compile(r"(?:^|.*[({`])" + _lead(_WRAP) + r"(?:\S*/)?$", re.S)
# a command word in quotes ("grep" -r x ., $'grep', behind xargs too) is the same command. Not one with a blank in
# it: unquoted it would be two (that one, and a word put together from quoted pieces, is read by named()).
# QUOTED_ANY: is there one? (see _lead)
_QUOTED_AT = r"((?:^|[;&|({`])%s)\$?(['\"])([\w./:-]+)\2(?=[\s;&|)]|$)"
QUOTED_COMMAND = re.compile(_QUOTED_AT % _lead(_WRAP + "|xargs"), re.M)
QUOTED_ANY = re.compile(_QUOTED_AT % _lead(_WRAP + "|xargs", ";&|({`"), re.M)
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
_WRAPS = (_WRAP + r"|xargs|builtin|winpty|stdbuf|wsl|uvx|(?:uv|conda|mamba|micromamba|poetry|pipenv|pixi|"
          r"pipx|pdm|hatch|rye)\s+run|uv\s+tool\s+run|(?:python[0-9.]*|py)\s+-m")
_LEADS, _LEADS_ANY = _lead(_WRAPS), _lead(_WRAPS, ";&|({`")
# _GO: where a command starts, for a pattern that is asked whether its command stands in a text (see _lead).
# _GO_EACH: the same with all that leads to the command, for one whose matches are counted or read
_GO = _START + _LEADS_ANY + r"(?:" + _W1 + "*/)?"
_GO_EACH = _START + _LEADS + r"(?:" + _W1 + "*/)?"
_PROG = (r"(?:(?:ba|z|da|k|c|tc|fi)?sh|cmd|python[0-9.]*|pypy[0-9.]*|py|node|deno|bun|perl|ruby|php|lua|Rscript|julia|"
         r"pwsh|powershell)(?:\.exe)?")
# the word ends there: `source: notes.md` in a configuration file and `cmd = [...]` in a program are no commands
_RUNNER = r"(?:" + _PROG + r"|source|\.)(?=\s|<|$|[;&|)])"
# The program whose flag a text stands behind, by the end of its word, since lex() takes a path's backslashes off
# (eval, trap and iex are their own flag). And those of them that are a shell, which reads the text as a line:
# sh, bash, zsh, dash, ksh, csh, tcsh, fish, pwsh, cmd, powershell and the three.
# shortcut: the last word before the flag that ends like one counts, so a word that only ends so (publish -c) is
# taken for a shell, and behind bash --rcfile x.py -c the text counts as python's; that takes each command's words
FLAG_PROG = re.compile(r"(?:" + _PROG + r"|eval|trap|iex|invoke-expression)$", re.I)
SHELL_PROG = re.compile(r"\w{0,2}sh|cmd|powershell|eval|trap|iex|invoke", re.I)
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
    + r"[ \t]*(?:[<=]\(|\"[^\"\n]*?(?:\$\(|`)|'?(?:\$\(|`)|\()[^)`\n]*?)(?<!" + _W1 + ")" + _NOTE, re.I | re.M)
# Where a word ends: at a space, at the line's end, or at a sign that ends a command or opens a redirection (tar x;
# patch<fix.patch). Not at "(": patch(x) is a call in program text, and install() { a function of the shell
_WEND = r"(?=[\s;&|)<>]|$)"
# A command word with a quote or a backslash in it, as a shell takes it where a command may start: the whole word,
# with the pieces of it that stand in quotes. Or a quoted text anywhere else, which named() passes over, so that it
# looks at no word inside one. A bracket right behind a name, a ")", a "]" or a "=" opens the arguments of a call
# or a list in program text (d.get("patch"), $s.Contains('rm'), steps=("install" "train")), and no command. And
# /c or /k starts a command behind cmd alone: find /c "install" log.txt counts lines
_WORD_GO = (r"((?:^|[;&|{`]|(?<![\w)\]=])\(|(?i:(?<=\bcmd)|(?<=\bcmd\.exe))(?:\s+/\w+)*?\s/[ck]\s)%s"
            r")(?=[^\s;&|<>()'\"`\\]*['\"\\])")
_WORD_AT = _WORD_GO + "((?:" + QUOTED.pattern + "|" + _W1 + ")+)" + _WEND
COMMAND_WORD = re.compile(_WORD_AT % _LEADS + "|" + QUOTED.pattern, re.M)
# WORD_ANY: may there be such a command word? (see _lead) It reads up to where the word would begin (_WORD_GO), and
# not the word. COMMAND_WORD passes over a quoted text; a search has nothing that does, so it begins inside one as
# well, at the { of "r${i}", and from there the word ran on over one quoted piece after the other to the text's
# end: the square of the length of a loop whose lines hold two quoted texts (3,000 such lines took this search 6 s,
# and a read-only agent's call went to the timer's question, 21 November 2026). So it says yes where no such word
# stands (echo "r${i}"), and never no where one does: what it finds is the beginning of every such word. Behind
# such a yes named() reads the text as it did before this search stood here: a long row of variables in it with
# the square, and variables set to nothing with a factor for each (see _lead; 39 of a= in front of echo x "r${i}"
# went to the timer's question). And a run of { in a quoted text is read on from each of them (20,000: one second)
WORD_ANY = re.compile(_WORD_GO % _lead(_WRAPS, ";&|{`"), re.M)
# Programs that write the file they name, where a command starts ("install" and "patch" are also plain words), and
# formatters, which rewrite a file unless they are told to check only, to print, or to say what they are. Each with
# .exe too, in any case, as a shell on Windows may name it (was until 20 November 2026: touch.exe, install.exe and
# black.exe on a kept file passed unasked, and a read-only agent was let run them and patch.exe)
WRITE_CMDS = re.compile(_GO + r"(?i:(?:touch|patch|install)(?:\.exe)?)" + _WEND, re.M)
# A patch changes the files that it names, and the line shows none of them: git apply unless it only checks or
# describes the patch (--apply behind such an option applies it after all, and git takes --ap for it, so any
# option that starts with --a counts as that one), git am unless it shows the patch it stopped at, and patch unless
# it is a dry run: --dry-run, and BSD's -C and --check (also in a group behind letters that take no value: -NC),
# which GNU patch does not know and stops at (tried on 19 November 2026, GNU patch 2.7.6). One that is asked for
# its help or its version applies nothing either (git's -h ends it wherever it stands, tried with git 2.52). Such an
# option's name ends where no letter, digit or hyphen follows: patch --version-control=numbered is another option,
# and applies the patch (was until 20 November 2026: read as --version). git's --help-all is its help too (was
# asked about that day, for the name's new end), and git apply takes each of its four back with --no-: behind
# --check --no-check it applies the patch, so any option that starts with --no- counts as --apply does (was: let
# through. Both tried with git 2.43 and 2.52)
PATCHES = re.compile(
    r"\bgit\s+(?:am\b(?![^;&|\n]*?\s(?:--(?:show-current-patch|help(?:-all)?)(?![\w-])|-h(?=[\s;&|)]|$)))|"
    r"apply\b(?:(?=[^;&|\n]*?\s--(?:a|no-))|"
    r"(?![^;&|\n]*?\s(?:--(?:check|stat|numstat|summary|help(?:-all)?)(?![\w-])|-h(?=[\s;&|)]|$)))))|"
    + _GO + r"(?i:patch(?:\.exe)?)" + _WEND +
    r"(?![^;&|\n]*?\s(?:--(?:dry-run|check|help|version)(?![\w-])|-[bcEeflNnRstuv]*C\S*))", re.M)
# An archive may hold a file of any name, and unpacked into a folder it writes that file below it: tar with -x (as
# its first word of letters too: tar xzf), unzip unless it lists, tests or prints, 7z x and e, cpio -i unless it
# lists (-it), PowerShell's Expand-Archive. A program's name counts in any case, its options as they are written
# (tar's -X is another one), but for 7z's command, which it takes in either case (7z X).
# One that prints what it unpacks writes no file: tar's -O and --to-stdout (tar -xOf
# a.tar config.json), cpio's --to-stdout, 7z's -so. A letter that lists or prints counts where no letter that
# takes a value stands in front of it in its group: in unzip -deval and tar -COUT the letters are a folder's name
_TO_OUT = (r"(?![^;&|\n]*?\s(?:--to-stdout\b|-[xvzjJkmpPaU]*O[a-zA-Z]*" + _WEND + r"))"
           r"(?!\s+[xvzjJkmpPaU]*O[a-zA-Z]*" + _WEND + ")")
EXTRACT = re.compile(
    _GO + r"(?:(?i:(?:bsd|g)?tar(?:\.exe)?)(?=\s)" + _TO_OUT + r"(?:\s+[a-zA-Z]*x[a-zA-Z]*" + _WEND + "|"
    r"(?=[^;&|\n]*?\s(?:-[a-zA-Z]*x|--extract\b|--get\b)))"
    r"|(?i:unzip(?:\.exe)?)(?=\s)(?![^;&|\n]*?\s-[a-ce-zA-OQ-Z]*[lptvZzc])"
    r"|(?i:7z[arz]?(?:\.exe)?)\s+[xeXE](?=\s)(?![^;&|\n]*?\s-so" + _WEND + r")|(?i:Expand-Archive)\b"
    r"|(?i:cpio)\b(?=[^;&|\n]*?\s(?:-[a-zA-Z]*i|--extract\b))"
    r"(?![^;&|\n]*?\s(?:-[a-zABLSV]*t|--list\b|--to-stdout\b)))", re.M)
_NO_WRITE = r"(?![^;&|\n]*\s(?:--(?:check(?:-only)?|diff|version|help)|(?-i:-[cdhV]))(?=[\s;&|)]|$))"
_VER = r"(?:\.exe)?(?:@[\w.]+)?"  # black.exe, and the version that uvx takes: ruff@0.6
_FORMATS = (r"(?:(?:(?:black|isort)" + _VER + r"|ruff" + _VER + r"\s+format)(?=\s|$)" + _NO_WRITE +
            r"|ruff" + _VER + r"(?:\s+check)?(?=\s)(?=[^;&|\n]*\s--(?:fix|unsafe-fixes)\b)"
            r"(?![^;&|\n]*\s--(?:diff|help)\b))")
FORMATS = re.compile(_GO + _FORMATS, re.I | re.M)  # is there one?
FORMATS_EACH = re.compile(_GO_EACH + _FORMATS, re.I | re.M)  # each one, to where its arguments begin
PY_FILES = ("*.py", "*.pyi", "*.ipynb")  # what they rewrite below a folder
# Commands that change a folder as a whole when they are given one: a move, a removal, a copy onto it, a link,
# git's checkout of it and its forced clean. PowerShell's and cmd's follow, the short names where a command starts
TREE_VERBS = re.compile(
    r"\b(?i:mv|cp|rm|rmdir|rsync|ln)\b|" + _GIT_BACK + r"|" + _GIT_CLEAN + r"|shutil\.(?:rmtree|move|copy)|"
    r"os\.(?:rename|replace|removedirs|rmdir)|\.(?:rename|replace)\(|(?i:\b(?:Remove|Move|Rename|Copy)-Item\b|"
    r"\b(?:xcopy|robocopy)\b)|" + _AT + r"(?i:ri|del|erase|rd|copy|move|ren|rename|cpi|mi|rni)\b", re.M)
# Commands that change the files they find themselves: find with -delete, and an edit whose list of files a search
# of the same line makes (find ... -exec, a pipe into xargs or into a loop that reads names, a command's output put
# into the line)
FIND_DELETES = re.compile(r"\b(?i:find)\b[^;&|]*?\s-delete\b")
FED = re.compile(r"\b(?i:find)\b[^;&|]*?\s-(?:exec|execdir|ok|okdir)\s|\|\s*(?:xargs|while)\b|\$\(|<\(|`")
# PowerShell's way: a pipe hands the files that a search found to the command that changes them, which may stand
# anywhere in the block that takes them (| % { $t = gc $_; Set-Content $_ $t }), and foreach (...) { } does the same
_PS_EDIT = (r"(?:Remove-Item|Clear-Content|Set-Content|Add-Content|Out-File|Move-Item|Rename-Item|Copy-Item|ri|rm|del|"
            r"erase|clc|sc|ac|mi|mv|rni|ren|cp|cpi|copy)(?=[\s;|})]|$)")
PS_FED = re.compile(r"(?:\|\s*(?:(?:%|foreach(?:-object)?)\s*\{(?:[^}]*?[\s;{(])?)?|"
                    r"\bforeach\s*\([^)]*\)\s*\{(?:[^}]*?[\s;{(])?)(?:" + _PS_EDIT + r"|>\s*\$(?!null\b))", re.I)
MASS_EDIT = re.compile(r"\b(?i:rm|mv|cp|dd|truncate|unlink|black|isort)\b|"
                       r"\b(?i:ruff)\s+(?:format\b|(?:check\s[^;&|\n]*)?--fix\b)|" + _INPLACE)
# A loop over such a list writes by a redirect into its variable too: | while read f; do echo x > "$f"; done
LOOP_OUT = re.compile(r"(?:\|\s*while|\bfor\s+\w+\s+in)\b[^\n]*?>\s*[\"']?\$\{?\w")
# The word that an output option names is written, whatever the program is called: sort -o FILE, curl -o FILE,
# wget -O FILE, --output FILE, --out=FILE, -oFILE, PowerShell's -OutFile FILE, also where the letter ends a group
# of them (sort -uo FILE, curl -sSLo FILE, wget -qO FILE). Behind python and ls the letter is another option
OUT_FLAG = re.compile(r"^(?:-[a-z]{0,5}o|--out[\w-]*|-OutFile)$", re.I)
OUT_JOINED = re.compile(r"^(?:--out[\w-]*=|-OutFile:|-o)(.+)$", re.I)
NO_OUT = re.compile(r"(?:^|/)(?:python[\d.]*|pypy[\d.]*|py|ls)(?:\.exe)?$", re.I)
# zsh runs the text of the glob qualifier e as a command: ls *(e:'rm -rf runs':), ls *(e:rm\ -rf\ runs:)
ZSH_E = re.compile(r"\((?:#q)?[^()\s'\"]*?e([^\s()'\"\\])(?:(['\"])(.*?)\2|((?:[^\s'\"()\\]|\\.)*\\.(?:[^\s'\"()\\]|\\.)*))")
# the file as the command itself (./notes.md with a first line that names its interpreter)
NOTES_CMD = re.compile(_START + _LEADS_ANY + _W1 + "*/" + _NOTE + r"(?=\s|$|[;&|)])", re.I | re.M)
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
_HERE = _PROG + r"(?=[\s<])(?:[^;&|\n<]|<(?!<))*<<(<?)"
HERE_RUN = re.compile(_GO + _HERE, re.I | re.M)  # is there one?
HERE_RUN_EACH = re.compile(_GO_EACH + _HERE, re.I | re.M)  # each one, with its group
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
    r"--all-types|--all-text|--follow)(?=[\s=;|&)]|$)|\bgit\s+grep\b[^;|&]*?\s--no-(?:index|exclude-standard)\b|"
    r"\bgit\s+ls-files\b(?:(?![^;|&]*--exclude-standard)[^;|&]*?\s(?:-[a-zA-Z]*o[a-zA-Z]*|--others)|"
    r"[^;|&]*?\s(?:-[a-zA-Z]*i[a-zA-Z]*|--ignored))(?=[\s;|&)]|$)")  # -i lists the ignored files, whatever excludes
# git's own readers of the checkout: grep reads the files git tracks, ls-files lists them (and a pipe hands that list
# to the next command); told to take the untracked or ignored files as well, they reach what any other tool does
GIT_READS = re.compile(r"\bgit\s+(?:grep|ls-files)\b")
_V = r"(?:\"[^\"]*\"|'[^']*'|[^\s;&|,]+)"
PS_GLOB = re.compile(r"\s-(?:Filter|Include)\s+(" + _V + r"(?:\s*,\s*" + _V + r")*)", re.I)  # PowerShell's: a list
# with no folder named, these take the cwd
GREPS = {"grep", "egrep", "fgrep", "rgrep"}  # rgrep is grep -r
CWD_SEARCH = GREPS | {"rg", "ag", "find", "tree", "ls", "du", "get-childitem", "gci", "dir", "findstr", "alldirectories",
                      "for"}
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
    """Anchored literal fragments used to spot sealed/frozen paths anywhere in a shell command (fuzzy). A path counts
    where a word may begin with it: at the start, behind a blank, a quote or one of = / : (, behind the < of
    "$(<file)", the [ of zsh's $mapfile[file], the @ of curl's -d @file, the comma of a list of files, and behind
    an option's letter (xargs -afile)."""
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
            out.append((p, re.compile(r"(?:^|(?<=[\s'\"=/:(<\[@,])|(?<=\s-[A-Za-z]))" + re.escape(s)
                                      + r"(?=$|[^A-Za-z0-9_.\-])", _CASE)))
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


def there(p: Path, how="exists"):
    """p.exists(), p.is_file() or p.is_dir() for a name taken from a call. They raise where the filesystem cannot
    hold the name (Linux and macOS: a part of more than 255 bytes, which the program behind -c or a commit message
    is). That ended the whole check as an internal error: a question for a harmless line, and a question where a
    refusal was due. Such a word names nothing on disk."""
    try:
        return getattr(p, how)()
    except OSError as e:
        if e.errno != errno.ENAMETOOLONG:
            raise
        return False


def walk(top: Path):
    if there(top, "is_file"):
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
        if sr not in shut and top is not None and there(top):
            walks.setdefault((top, root, s, sr), []).append(pat)
    # found: the sealed files that the search's filters let through, by the folder they really lie in, with their pattern
    found, real, plain = {}, {}, not (globs or typ)
    for (top, root, s, sr), pats in walks.items():
        # A folder sealed as a whole (data/test/**) is walked to its end, as long as the hook's time allows: every
        # file in it is sealed, so one that the search's filters let through anywhere in it counts. Where the time
        # runs out first, the search counts as reading it. A pattern with a wildcard is walked as long, and a walk
        # that the time cuts short counts as reading what the pattern seals: files that it did not reach may be
        # among those the search reads. (Until 14 November 2026 such a walk ended after WALK files and the search
        # passed.) Searching a named folder that holds no sealed file needs no walk.
        whole = [p for p in pats if not re.search(r"[*?\[]", re.sub(r"/\*\*$", "", norm_pattern(p)))]
        for n, f in enumerate(walk(top)):
            if n >= WALK and time.monotonic() >= ctx.t0 + WALK_S:
                return (whole or pats)[0]
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


def below(ctx, rel, patterns, globs=(), typ=None):
    """The first of the patterns that keeps a file in the folder rel or below it ('.': the project), or None. globs,
    typ: the file filters of the command that walks the folder, as passes() reads them; with them only a file on
    disk that they let through counts.
    shortcut: by the pattern's text, so one that starts with a wildcard (**/metrics.py) counts for the project
    folder only, not for a named subfolder, and behind WALK files of a pattern's folder the rest counts unseen;
    walk the named folder if such patterns come into use"""
    low = (rel.lower() if NOCASE else rel).rstrip("/") or "."  # '': the top of a copy of the tree (a snapshot)
    for p in patterns or []:
        p2 = norm_pattern(p)
        lead = re.split(r"[*?\[]", p2)[0]
        if low != "." and not (lead.lower() if NOCASE else lead).startswith(low + "/"):
            continue
        if not (globs or typ):
            return p
        top = ctx.root / (lead if lead == p2 else lead.rpartition("/")[0])
        for n, f in enumerate(walk(top) if there(top) else ()):
            r = f.relative_to(ctx.root).as_posix()
            if n >= WALK or (matches(r, [p]) and passes(f, r if low == "." else r[len(low) + 1:], globs, typ)):
                return p
    return None


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


def wild(text: str, lists) -> str:
    """A POSIX line with the patterns of zsh and ksh that no rule here knows written as ones they do. A group inside
    a name: (a|b) and @(a|b) with plain names become the brace list {a,b}, which `lists` writes out, (a) becomes
    a, and any other group (!(a), +(a), a pattern inside) becomes *. The line also holds parentheses that are no
    group (a subshell (ls|head), a case pattern, and in program text the call Path('eval').rglob('*.py')), so
    one counts only where more of the name follows right behind it, where it lists alternatives or is !(..) and a
    name touches it, or where it holds a plain name in front of a / or behind one. A zsh flag such as (#i) or
    (#a1) loosens the match of all that follows it in the word: each folder name there becomes *. Then [^a]
    becomes [!a], zsh's ^name in a path becomes *, and of pattern~other the pattern stays. zsh, the shell of a
    Mac, knows the group and [^a] with no option set, and bash knows [^a].
    shortcut: x# (repeats), a ^name that is a whole word or stands inside a name (te^x), a group without | that
    ends a word (te(st)) and a pattern under a shell option that ignores case are read as the characters they are;
    each needs a shell option that the line or the user's shell settings change. That takes a sandbox"""
    def group(m):
        s, (op, inside) = m.string, m.groups()
        before, after = s[m.start() - 1:m.start()] if m.start() else "", s[m.end():m.end() + 1]
        plain = all(re.fullmatch(r"[\w.-]*", a) for a in inside.split("|"))
        near = re.match(r"[\w\0]", after)  # no call and no subshell ends so
        if "|" in inside or op == "!":
            near = near or re.match(r"[./*?\[-]", after) or re.match(r"[\w./\0*?\]-]", before)
        elif before == "/" or (after == "/" and not op):
            near = near or plain or re.search(r"[*?\[]", inside)  # a folder as a pattern: dat?/(tes?)/lab*
        if not near:
            return m.group()
        if op in ("", "@") and plain:
            return inside if "|" not in inside else "{" + inside.replace("|", ",") + "}"
        return "*"

    text = GLOB_FLAG.sub(lambda m: re.sub(r"[^/]+", "*", m.group()), text)
    for _ in range(8):  # a group inside a group
        was, text = text, GLOB_GROUP.sub(group, text)
        if was == text:
            break
    return GLOB_BUT.sub(r"\1", GLOB_NOT.sub("*", lists(text).replace("[^", "[!")))


def uncommented(text: str) -> str:
    """A POSIX line without its comments: a # that starts a word outside quotes, up to the end of its line. The rules
    pair quotes over the whole text, so an apostrophe in a comment would pair with one further down and hide the
    commands in between (echo a # it's <newline> cp x.py eval/metrics.py # it's)."""
    out, i, n = [], 0, len(text)
    while i < n:
        ch, j = text[i], i + 1
        if ch == "\\":
            j = i + 2
        elif ch == "'":
            j = text.find("'", j) + 1 or n
        elif ch == '"':
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j += 1
        elif ch == "#" and (i == 0 or text[i - 1] in " \t\n;&|()<>"):
            i = text.find("\n", i)
            if i < 0:
                break
            continue
        out.append(text[i:j])
        i = j
    return "".join(out)


# where a here-document starts, with the word that ends it as a shell puts it together (<<EOF, <<-'EOF', << "EOF",
# <<\EOF, <<E"O"F, <<EOF+; not <<<, a here-string, whose word is an ordinary one), and PowerShell's here-string (@' or
# @" at the end of a line, closed by '@ or "@)
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*((?=[A-Za-z_'\"\\])(?:[^\s;&|<>()'\"\\`]|\\.|'[^'\n]*'|\"[^\"\n]*\")+)"
                     r"|@(['\"])\s*$")
LONE_QUOTE = re.compile(QUOTED.pattern + r"|(['\"])")  # a quoted text as the rules pair it, or a quote left over


def unquoted_bodies(text: str, paired: bool = False) -> str:
    """A line without the quote characters of its here-documents that pair with nothing there. What stands in a
    document is text, in which an apostrophe pairs with nothing (don't). The rules pair quotes over the whole line,
    so that one paired with a quote further down and hid the commands in between (cat <<EOF <newline> don't <newline>
    EOF <newline> cp x.py eval/metrics.py; echo 'done'). Quotes that pair inside the document stay, so that a program
    in it is read as on the line as it came: print('a -> b') holds no redirection. PowerShell's here-string loses
    all of them, because its text then stands between the quotes of its own @' and '@. So does a document that
    nothing on the line closes: a closing word that the guard reads otherwise than the shell looks the same. And so
    does a document with a backslash in front of a quote, an escaped quote (print("a \\" b")) or a quote behind an
    escaped backslash ("C:\\\\"): the rules, for which a backslash is a folder separator, pair that quote, and
    LONE_QUOTE and the readings of a POSIX shell do not, so that no pairing of such a text holds for all of them.
    With paired, that last kind keeps the quotes that pair in it, as it was read from 16 November 2026 to the 17th:
    readings() takes the line both ways, so that neither way takes a question of the other away.
    Like every reading this may name more than the shell would: a << in quoted text counts as a document's start,
    and then a quote left over in the lines below it is taken out.
    shortcut: a closing word that starts with anything but a letter, _, a quote or a backslash (<<1, <<+x, <<$x) is
    not read as one, so such a document keeps its quotes; that takes the shell's own reading of words"""
    lines, ends, first = text.split("\n"), [], 0
    for k, ln in enumerate(lines + [None]):  # None: the text's end, which closes a document left open
        if not ends:  # what closes each document that this line opens, in their order: the word alone, behind tabs
            # for <<-, as strictly as a shell takes it, so that no document ends here before the shell ends it
            ends = [(m.group(3) + "@", True) if m.group(3) else (("\t*" if m.group(1) else "") + re.escape(re.sub(
                r"\\(.)|'([^']*)'|\"([^\"]*)\"", lambda q: q.group(1) or q.group(2) or q.group(3) or "", m.group(2)))
                + r"\r?$", False) for m in HEREDOC.finditer(ln or "")]
            first = k + 1
        elif ln is None or re.match(ends[0][0], ln):
            if first < k:
                body = "\n".join(lines[first:k])
                lines[first:k] = (re.sub(r"['\"]", "", body)
                                  if ends[0][1] or ln is None or not paired and re.search(r"\\['\"]", body)
                                  else LONE_QUOTE.sub(lambda q: "" if q.group(1) else q.group(), body)).split("\n")
            del ends[0]
            first = k + 1
    return "\n".join(lines)


def named(text: str) -> str:
    """The text with each command word that stands in quotes, is put together from quoted pieces or is written with
    backslashes as its program's bare name, which is how the rules know a program:
    "C:/Program Files/Git/usr/bin/touch.exe" x and C:\\msys64\\usr\\bin\\touch.exe x are touch.exe x, and t'ou'ch x
    is touch x. Until 21 November 2026 no rule saw the first, whose quotes plain() leaves for the blank in them, or
    the third, and a read-only agent's rules, which do not read the plain form, saw none of the three. Only a whole
    command word changes, into a name without quotes, so every other quote of the text pairs as it did, and a quoted
    word in a program's text stays one: print(\\"a > b\\"), d.get("patch"). A word that sets a variable (X="a/b") or
    stands in a list that one is set to (steps=(train "install")) stays as well, and so does one whose last part is
    no name ("my notes", "$tool").
    Like every reading this may name more than the shell would: a quoted word where a command may start is a
    command's name to a POSIX shell and a text to PowerShell ('install' -in $steps, a switch's case 'patch'), and
    on a line of its own in a here-document it may be a program's text. Each is read as the bare word is read there.
    shortcut: one pass, so behind a wrapper that is itself quoted ("sudo" "rm" x) the command word stays in its
    quotes here (plain() takes them off a name without a blank, for the main session's rules); a blank that a
    backslash escapes (/c/Program\\ Files/Git/usr/bin/touch.exe) and a quoted blank in what leads to the word
    (X="a b" 'touch' x) end the word or the search early, and a word that stays is passed over with all that leads
    to it (a=1;'touch' "my notes"). Those take the shell's own splitting of words"""
    def bare(m):
        w = m.group(2) or ""
        path = QUOTED.sub(lambda q: q.group()[1:-1], re.sub(r"\$(?=['\"])", "", w)).replace("\\", "/")
        name = path.rsplit("/", 1)[-1]
        return m.group(1) + name if w and "=" not in QUOTED.sub("", w) and "=(" not in m.group(1) \
            and re.fullmatch(r"[\w.@+-]+", name) else m.group()

    return COMMAND_WORD.sub(bare, text) if re.search(r"['\"\\]", text) and WORD_ANY.search(text) else text


def readings(cmd: str):
    """The line as another shell reads it, where that is another text, and whether a word of it was too long to
    write out. check_bash reads a backslash as a folder separator, as PowerShell and cmd do. A POSIX shell leaves
    its comments out (read here both ways), takes a backslash
    off the character behind it (te\\st is test, also across the end of a line), reads \\" inside "..." as a quote
    that ends nothing (echo "a \\" b"; the rules would end the string there, and the reading of before, which
    keeps "..." as it came, is made beside this one), reads $'te\\x73t' and $"test" as
    test, may put the word of ${name:-word} in the name's place, and writes a word with {a,b} out; zsh and ksh have
    patterns of their own, which wild() writes as plain
    wildcards in a reading of its own; PowerShell and cmd take their own escape characters off (te`st, te^st).
    PowerShell reads `" as a quote that opens and ends nothing, inside "..." too, and a quote inside <# #> as a part
    of that comment (echo "a `" b"; <# it's #>): the rules would pair both, so the line is read once more as
    PowerShell pairs its quotes, also without its other comments and the lone quotes of its here-documents.
    Each reading may name more than the shell would (an escape that stands for a control character is read as its
    letter; a POSIX line with a command in backticks right before a closing quote, "`date`", is paired otherwise
    in PowerShell's reading): it is checked in addition to the line as it came.
    The line and each of these readings is read once more with its command words named plainly, where that is
    another text: see named().
    shortcut: text only, so a name put together from variables, {a..b} or a command's output passes; that takes
    running the line in a sandbox"""
    held, long, loose = [], [], []  # loose: the "..." of this form of the line that a substitution reaches out of

    def hold(s, came=None):  # quoted text is no escape and no brace list; came: as it stood on the line
        held.append((s, s if came is None else came))
        return "\0%d\0" % (len(held) - 1)

    def c_char(m):
        e = m.group(1)
        return chr(min(int(e[1:], 16), 0x10FFFF)) if e[0] in "xuU" and len(e) > 1 else \
            chr(int(e, 8) % 256) if e[0] in "01234567" else e

    def reaches(s):  # does a $( ), a ` ` or a ${ } that this stretch of a "..." opens go on behind it? (The stretch
        # as part() gets it: the word of a default, ${X:-\"d\"}, stands in the name's place by then, and is read as such.)
        # shortcut: ` and ${ are counted, not followed as closes() follows a $( (a ` or a ${ in quotes inside a $( )
        # counts as one that opens, a } left over in front of a ${ as its end), and an escaped \$( counts as a $(. All
        # but the } keep the form of 17 November where the other would do; a walk like closes() for each, where it matters
        i, bare = s.find("$("), re.sub(r"\\.", "", s, flags=re.S)
        while i >= 0:
            i = closes(s, i + 2)
            if i >= len(s):
                return True
            i = s.find("$(", i)
        return bare.count("`") % 2 or bare.count("${") > bare.count("}") or bare.rfind("${") > bare.rfind("}")

    def part(m):
        x, t = m.group(1), m.group()
        if x is None:  # a quoted string. In "..." an escaped quote ends nothing, and the rules, for which a backslash
            # is a folder separator, would end the string there: written as the shell's own splice of the fewest pieces,
            # 'a " b'. A text between two such quotes that "..." would expand, or that '...' cannot hold, stays in "..."
            # as it came: "$x"'" b'. (The form of 17 November 2026 spliced at every such quote, "a "'"'" b": a JSON body
            # of 1.4 KB was 800 pieces, of which joined() made 170,000 paths to look up on disk, 22 seconds on Windows.)
            # That form stays from the first "..." on in which a $( ), a ` ` or a ${ } reaches across such a quote
            # ("$(echo \"x\")") or past the text's end ("$(echo "x")"), to the end of the line: from there on the pairs
            # of this reading and the shell's may part ways, neither form is the shell's word, what the shell runs is
            # read from the line as it came, by spliced(), and the other form gave some of those lines another answer
            # than that day's.
            # shortcut: such a line keeps that form's cost too (400 escaped quotes in one text from that point on: the
            # timer's question); that takes finding where the substitution ends and keeping the old form up to there
            if t[0] == "'":
                return hold(t)
            segs = t[1:-1].split('\\"')
            if loose or any(map(reaches, segs)):
                loose.append(t)
                return hold('"%s"' % "\"'\"'\"".join(segs), t)
            out = run = ""
            for i, s in enumerate(segs if len(segs) > 1 else ()):
                run += '"' * (i > 0)
                if re.search(r"[\\$`']", s):
                    out, run = out + ("'%s'" % run if run else "") + '"%s"' % s, ""
                else:
                    run += s
            return hold((out + ("'%s'" % run if run else "")) or t, t)
        if not re.match(r"[\w./:@%+=~^-]", x):  # a character that stays quoted
            return hold("" if x == "\n" else shlex.quote(x))
        return x

    def written_out(m):
        names = braces(m.group())
        long.append(names is None)
        return " ".join(names or [m.group()])

    def ps_part(m):  # a comment is a blank, 'text' stays, and an escaped quote, in "text" too, is taken out
        t = m.group()
        return " " if t[0] in "<#" else t if t[0] == "'" else re.sub(
            r"`(.)", lambda e: "" if e.group(1) in "\"'" else e.group(), t, flags=re.S)

    def ps(parts, t):  # behind the last #> no <# is closed. Marked there, so that the search for its end, which ran
        # from each of them to the text's end and took a long line past the guard's time limit, is not made
        cut = t.rfind("#>") + 1
        return parts.sub(ps_part, t[:cut] + t[cut:].replace("<#", "<\0#")).replace("\0", "")

    text, out = cmd.replace("\0", ""), []
    bodies = unquoted_bodies(text)
    # with its comments and without: what stands behind a # may be a zsh pattern (data/(#i)TEST), and no comment.
    # And without the quotes of its here-documents that pair with nothing there, in both forms of unquoted_bodies().
    # Each of these twice (k): with an escaped quote in "..." as the splice, and with every "..." as it came. The
    # second, and the document's second form, are how the versions before 17 November 2026 read the line. They pair
    # quotes as no shell does, and they stay because they asked about lines that no other reading asks about
    # (echo it\'s "a \" > eval/metrics.py" 'x'): a reading may add a question, and a change of one could take one away
    for posix in dict.fromkeys((text, uncommented(text), uncommented(bodies), uncommented(unquoted_bodies(text, True)))):
        for _ in range(4):  # a default inside a default
            posix = PARAM_WORD.sub(r"\1", posix)
        posix = ANSI_C.sub(lambda m: shlex.quote(C_ESCAPE.sub(c_char, m.group(1)).replace("\0", "")), posix)
        loose.clear()
        posix = POSIX_PART.sub(part, re.sub(r"\$(?=\")", "", posix))
        out += [re.sub(r"\0(\d+)\0", lambda m: held[int(m.group(1))][k], t) for t in (
            BRACE_WORD.sub(written_out, posix), wild(posix, lambda t: BRACE_WORD.sub(written_out, t))) for k in (0, 1)]
    # PowerShell and cmd: the line as it came, the line as PowerShell pairs its quotes, and that one without the
    # quotes of its here-documents that pair with nothing there and without its comments to the line end: once where
    # a POSIX shell starts one (no # inside a word), once from every # that PowerShell's own pairing leaves outside
    # a text, so that a quote in a comment misleads neither the pairing behind it nor the search for the comment
    for win in dict.fromkeys((text, ps(PS_PART, text), uncommented(ps(PS_PART, bodies)), ps(PS_LINE, bodies))):
        win = re.sub(r"`u\{([0-9a-fA-F]{1,6})\}", lambda m: chr(min(int(m.group(1), 16), 0x10FFFF)), win)
        out.append(WIN_ESCAPE.sub("", win).replace("\0", ""))
    out += [named(t) for t in dict.fromkeys([text] + out)]
    return [t for t in dict.fromkeys(out) if t != cmd], any(long)


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


def out_words(lx):
    """The words that an output option names among the words of a line."""
    return [after for before, t, after in zip([""] + lx, lx, lx[1:]) if OUT_FLAG.match(t) and not NO_OUT.search(before)] \
        + [m.group(1) for m in map(OUT_JOINED.match, lx) if m]


def unpacks(seg):
    """The folders into which the words of one command may unpack an archive, [] where they unpack none: the word
    behind tar's -C or --directory (also -Craw, --directory=raw), behind unzip's -d (-draw) and behind PowerShell's
    -DestinationPath (also -DestinationPath:raw), and 7z's -o<folder>. Each program's own option only: unzip's -C
    and cpio's -d name no folder.
    Where the command names none in these forms, the folder that it runs in and each of its words, of which one may
    be the folder (Expand-Archive x.zip raw, tar -xzC raw). None stands for a folder that a variable, a command's
    output or a bracket names (tar -C "$DEST", -DestinationPath (Join-Path $x raw)), which may be any one."""
    if not EXTRACT.search(" ".join(seg)):
        return []

    def prog(rx):
        return any(re.fullmatch(rx + r"(?:\.exe)?", t.rsplit("/", 1)[-1], re.I) for t in seg)
    tar, zp = prog(r"(?:bsd|g)?tar"), prog("unzip")
    opt = r"-C|--directory|--cd" if tar else "-d" if zp else r"(?i:-dest\w*)"
    glued = r"--directory=|-C(?=.)" if tar else "-d(?=.)" if zp else "-o(?=.)" if prog("7z[arz]?") else r"(?i:-dest\w*:)"
    to = [b for a, b in zip(seg, seg[1:]) if re.fullmatch(opt, a)]
    to += [m.group(1) for m in (re.match(r"(?:" + glued + r")(.+)", t) for t in seg) if m]
    return [None if re.search(r"[$`(]", t) else t for t in to] or ["."] + [t for t in seg if t[:1] != "-"]


def py_unpacks(c: str):
    """The folders into which program text unpacks an archive: extractall's first argument or path=, and
    unpack_archive's second or extract_dir=, where that is one word in quotes, and "." (the folder that the program
    runs in) where the call names none. Another argument given by its name is no folder (format='zip',
    filter='data'). None stands for a folder that this does not read (a variable, a joined path, a call, or the
    function under another name), which may be any one, as in unpacks()."""
    out = []
    for m in PY_UNPACK.finditer(c):
        args = [a.strip() for a in (m.group(2) or "").split(",")]
        at = m.group(1) == "unpack_archive"  # its first argument is the archive
        named = [a for a in args if re.match(r"(?:path|extract_dir)\s*=", a)]
        dest = (named or [a for a in args if not re.match(r"\w+\s*=(?!=)", a)][at:at + 1] or [""])[0]
        lit = re.fullmatch(r"(?:\w+\s*=\s*)?[rRuU]?(['\"])([^'\"]+)\1", dest)
        out.append(lit.group(2) if lit else None if dest or m.group(2) is None else ".")
    return out


def saves(cmd: str, c: str):
    """The files that a line writes by its redirections and by tee, where each one names its file in plain letters.
    None where the line cannot be read so: a variable, a command's output, a backslash or a ~ stands in it (each
    can splice a name or a folder that this does not see), it holds a here-document (text, in which a quote pairs
    with nothing, so that the quoted words after it cannot be told), it goes to a folder that it does not name
    (cd -, popd, pushd +1 anywhere on the line; a cd or pushd with no folder or with options alone, cd -P, which
    goes home or to the folder before, where a command starts, so that an argument named sl is none), or it may go
    where CD does not follow it: what CD takes for the folder is an option that it does not know (zsh's cd -q data),
    or a cd with a word behind it stands where CD finds none (time -p cd .., and the same words as arguments). Also
    None where a target is missing or is a pattern, or a tee stands where no command starts. A tee's files are read
    to the end of its command, past the redirections that stand among them (tee >/dev/null f, tee <<< "{}" f); a
    descriptor's digit in front of one counts as a file of that name, which adds a name and hides none."""
    if re.search(r"[$`\\~]|(?<!<)<<(?!<)", cmd) or (MAY_CD.search(c) and (re.search(
            r"(?:^|[\s;&|({])(?:popd|Pop-Location|" + _CD_WORD + r"\s+[-+]\d*)(?=[\s;&|)}]|$)|" + _CD_AT
            + _CD_WORD + r"(?:[ \t]+-[^\s;&|)}<>:]*)*(?=[ \t]*(?:[;&|)}<>]|\d+[<>]|$))", c, re.I | re.M)
            or any(m.group(1)[:1] in "-+" for m in CD.finditer(c))
            or re.search(r"(?<![\w./-])" + _CD_WORD + r"[ \t]+[^\s;&|)}<>]", CD.sub(";", c), re.I))):
        return None
    quoted, out = [], []
    masked = QUOTED.sub(lambda q: quoted.append(q.group()[1:-1]) or "\0%d\0" % (len(quoted) - 1), c)
    for m in SAVES.finditer(masked):
        if m.group(3) is not None:
            return None
        ws, at = ([m.group(1)], len(masked)) if m.group(2) is None else (m.group(2).split(), m.end())
        while at < len(masked):  # a tee's words go on behind a redirection of its own, to the end of its command
            x = TEE_REST.match(masked, at)
            if not x:
                if masked[at] not in ";&|)\r\n":  # <(...) and >(...): what stands behind them is not read
                    return None
                break
            ws += [x.group(1)] * bool(x.group(1))  # in place: a copy for each word took a long line's square
            at = x.end()
        for w in ws if m.group(2) is None else [w for w in ws if w[:1] != "-"]:
            w = re.sub(r"\0(\d+)\0", lambda x: quoted[int(x.group(1))], w)
            if not re.fullmatch(r"[\w ./@%+,:=-]+", w):
                return None
            out.append(w)
    return out


def closes(s: str, i: int) -> int:
    """Where the $( ends whose text starts at s[i]: the index of its closing bracket as a POSIX shell finds it, past
    quoted text, an escaped character and the brackets in between. len(s) where nothing closes it."""
    depth = 1
    while i < len(s):
        ch = s[i]
        if ch == "\\":
            i += 1
        elif ch == "'":
            i = s.find("'", i + 1)
            if i < 0:
                break
        elif ch == '"':
            i += 1
            while i < len(s) and s[i] != '"':  # a $( in it has quotes of its own
                i = closes(s, i + 2) if s.startswith("$(", i) else i + (s[i] == "\\")
                i += 1
        else:
            depth += (ch == "(") - (ch == ")")
            if not depth:
                return i
        i += 1
    return len(s)


def spliced(text: str):
    """The commands whose output a text takes in: $(...) and `...`. A here-document that no runner reads is data
    (git commit -m "$(cat <<'EOF' ... EOF)"): of such a command there count the part in front of the document with
    the rest of that line (a pipe, a redirection), where the delimiter has no quotes the commands that the document
    takes in itself, and what follows the document's last line, which is a command again."""
    def commands(s):
        if not re.search(r"<<(?!<)", s) or HERE_RUN.search(s) or PIPED.search(QUOTED.sub(" '' ", s)):
            return [s] if s.strip() else []
        head, body = re.split(r"<<(?!<)", s, 1)
        m = re.match(r"-?[ \t]*([/\\'\"]*)([\w.-]+)['\"]?([^\n]*)\n?(.*)$", body, re.S)
        if not m:  # no delimiter that this reads: all of it may be commands
            return [s]
        quoted, word, line, below = m.groups()
        doc = re.split(r"^[ \t]*" + re.escape(word) + r"[ \t]*$", below, 1, flags=re.M)
        return [x for x in [head + " " + line] if x.strip()] + ([] if quoted else list(spliced(doc[0]))) \
            + commands("".join(doc[1:]))

    # What single quotes make plain text, as a shell pairs them: not those inside "..." or inside a $(...), whose
    # words the nested command needs as they are (echo "$(python -c "open('f', 'w')")")
    lit, i, dq = [], 0, False
    while i < len(text):
        if text[i] == "\\":
            i += 1
        elif text.startswith("$(", i):
            i = closes(text, i + 2)
        elif text[i] == '"':
            dq = not dq
        elif text[i] == "'" and not dq:
            j = text.find("'", i + 1)
            if j < 0:  # an apostrophe: nothing is taken for plain text behind it
                break
            lit.append((i, j))
            i = j
        i += 1
    pos = 0
    for m in SPLICED.finditer(text):
        # inside a text that is read as a whole (the check of that text finds it), or inside plain text
        if m.start() < pos or any(a < m.start() < b for a, b in lit):
            continue
        s, pos = m.group(1), m.end()
        if s is None:
            pos = closes(text, m.end())
            if re.search(r"\bcase\s", text[m.end():pos]):  # a pattern of case ends with a bracket of its own
                pos = max(pos, text.rfind(")"))
            s = text[m.end():pos]
        yield from commands(s)


# where a command starts with a variable: $c, "$c", ${c}, also as zsh splits or changes it (${=c}, ${(z)c})
_VAR_AT = _GO + r"[\"']?\$\{?(?:\([^)]*\))?[=~^]*"


def run_vars(c: str) -> tuple:
    """The names of the variables that a line may run from where they stand: one where a command starts (_VAR_AT),
    and one that zsh reads with flags anywhere, of which (e) runs the text: echo ${(e)c}. The line is searched for
    all of them at once. Until 21 November 2026 every word that sets a variable had two searches of the line to itself,
    each with a pattern built for its name: 1,500 lines that each set one took ten seconds so, and a thousand of
    a=1; without a blank took the guard past its own limit of time, to a question that told of no rule.
    A place where a command starts can be read in more than one way (X= $c $d runs $c with an empty X, or $d with X
    set to $c), and a search shows one name for each place: so the line is searched again without the names that
    are found, until a search finds no new one. Four times at most, because a place can be made up that reads in
    as many ways as it has words (X0= $a0 X1= $a1 ...): with a search for each way, 1,600 of them would take ten
    seconds. Returns the names, and whether they are all of them: where they are not, the caller gives a name
    that is not among them a search of its own, as every name had before."""
    found, new, left = set(), True, 4
    while new and left:
        rest = r"(?!(?:%s)\b)" % "|".join(sorted(found)) if found else ""
        new = {m.group(1) for m in re.finditer(r"(?=" + _VAR_AT + rest + r"(\w+)\b)", c, re.M)}
        found |= new
        left -= 1
    return found | {m.group(1) for m in re.finditer(r"\$\{\([^)]*\)[=~^]*(\w+)\b", c)}, not new


def inner_code(c: str, shell=None):
    """Text a command hands to a nested shell or an interpreter as one argument (bash -c '...', python -c "...",
    cmd /c "...", powershell -Command "...", eval "...", trap '...' EXIT), also where its flag stands in a group of
    letters or options come first (sh -ec '...', bash -c -- '...'), where it is attached to its flag
    (bash -c"...") or encoded (powershell -EncodedCommand <base64>), where PowerShell makes a script block of it
    ([scriptblock]::Create('...')) or program text hands it to a shell (os.system('...')), the text of a zsh glob
    qualifier e, and a
    command whose output the line takes in ($(...), `...`), unless single quotes make it plain text, and a text
    that the line keeps in a variable and may run from there (c='rm x'; $c  and  $c = 'del x'; iex $c). The caller
    checks it like a command of its own. Not read: a qualifier e whose text is one bare word or a variable, and
    (+name), which run what the line does not show, as a script does.
    shell, a list, takes those of the texts that a shell reads as a line: a command whose output the line takes in,
    and the text behind the flag of a program that is a shell (bash -c, cmd /c, powershell -Command, eval, trap,
    iex). Not a program's text in another language (python -c), where a quoted word at a statement's start is no
    command, and not what reaches a shell from a variable, from standard input or by zsh's qualifier."""
    out = [m.group(3) if m.group(2) else re.sub(r"\\(.)", r"\1", m.group(4)).rstrip(m.group(1) + "]}>")
           for m in ZSH_E.finditer(c)]
    shell, taken = [] if shell is None else shell, list(spliced(c))
    shell += taken
    out += taken
    toks, run = lex(c), SHELLS.search(c)
    # a text that the line keeps in a variable (c='rm x'; $c = 'del x') counts where the line may run it: the
    # variable stands where a command starts, also as zsh splits it (${=c}), or zsh reads it with flags (run_vars()
    # finds both, for all the line's variables at once; where it stopped before it had them all, a name that it
    # has not found is searched for by itself), or the text has more than one word and the line has a runner
    # (eval "$c", iex $c, $c | sh). A variable set from another one has its text: d=$c
    kept, may_run, whole = {}, None, True
    for i, t in enumerate(toks):
        m = re.match(r"\$?(\w+)=(.+)", t, re.S)
        name, text = m.groups() if m else ("", "")
        if t == "=" and 0 < i < len(toks) - 1 and re.search(r"\$\w+$", toks[i - 1]):  # PowerShell's: $c = '...'
            name, text = toks[i - 1].rpartition("$")[2], toks[i + 1]
        if not name:
            continue
        text = kept[name] = re.sub(r"\$\{?(\w+)\}?", lambda v: kept.get(v.group(1), v.group()), text)
        if text and may_run is None:
            may_run, whole = run_vars(c)
        if text and (name in may_run or (not whole and re.search(_VAR_AT + name + r"\b", c, re.M))
                     or (run and re.search(r"\s", text))):
            out.append(text)
    # PowerShell makes code of a text: [scriptblock]::Create('...'), with its namespace too, and so do the engine's
    # own calls. Program text hands a command to a shell: os.system('...'), subprocess.run(['rm', 'x'])
    out += [t for m in re.finditer(r"(?:scriptblock\]\s*::\s*create|\.(?:InvokeScript|NewScriptBlock|AddScript))\s*\(\s*(.+)",
                                   c, re.I | re.S) for t in lex(m.group(1))[:1]]
    for m in PY_CALL.finditer(c):  # the literals are Python's: a backslash escapes a quote and itself, \n ends a line
        lits = [q.group()[1:-1] for q in re.finditer(_PY_LIT, m.group(1), re.S)]
        read = " ".join(re.sub(r"\\(.)", lambda e: {"n": "\n", "t": "\t"}.get(e.group(1), e.group(1)), x, flags=re.S)
                        for x in lits)
        out += [x for x in dict.fromkeys([read, " ".join(lits)]) if x]  # and as they stand, which a raw string means
    if not run:
        return out
    prog = ""  # the program whose flag a text stands behind, up to the sign that ends its command
    for i, t in enumerate(toks):
        p = FLAG_PROG.search(t[-24:])
        prog = "" if re.fullmatch(r"[;&|()]+", t) else p.group() if p else prog
        after, n = "".join(toks[i + 1:i + 2]), len(out)
        m = ATTACHED.match(t)
        out += [m.group(1)] if m else []
        flag = re.split(r"[{(]", t)[-1]  # PowerShell's block may hold the runner: &{iex '...'}, try{iex '...'}catch{}
        if CODE_FLAG.match(flag):
            # The text is the flag's next word. A shell takes the first word that is no option (sh -c -- '...',
            # trap -- '...' EXIT), before which an option's value may stand (bash -c -o pipefail '...'), and eval
            # runs all its words as one line, unless eval is the folder that an option names (env -C eval ls)
            args = list(itertools.takewhile(lambda x: not re.fullmatch(r"[;&|<>()]+", x), toks[i + 1:]))
            texts = [after if flag == t else re.sub(r"[})][^\s'\"]*$", "", after)]
            if flag.lower() == "eval" and not re.fullmatch(r"-C|--(?:chdir|directory|cwd)", "".join(toks[max(i - 1, 0):i])):
                # a separator that the line escapes is one of eval's words (eval : \; 'rm x'), and lex shows no
                # difference: there all that follows counts
                texts = [" ".join(toks[i + 1:] if re.search(r"\\[;&|<>()]", c) else args)]
            elif after[:1] in ("-", "+"):
                texts += [x for x in args if x[:1] not in ("-", "+", "")][:3]
            out += [x for x in texts if x]
        out += [decoded(after)] if ENCODED.match(t) and decoded(after) else []
        shell += out[n:] if SHELL_PROG.match(prog) else []
    # a runner without a script takes its code from standard input (echo "..." | sh, bash <<< "..."): there every
    # argument of the line that is more than a plain word or path may be that code
    bare = QUOTED.sub(" '' ", c)
    if PIPED.search(bare) or (HERE_RUN.search(bare) and any(m.group(1) for m in HERE_RUN_EACH.finditer(bare))):
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
            # PowerShell closes a block without a blank, which leaves the bracket on the path: &{del eval\m*.py}
            out += [t.rstrip("}")] if t.endswith("}") and t.count("}") > t.count("{") and t.strip("}") else []
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
        # and a folder that it is handed it may list or read whole: an argument under a key that names a place, or
        # one written as a path. Not any word: a query for "data" names no folder
        places = [p for k, v in ti.items() if PLACE_KEY.search(str(k)) for p in path_strings(v)]
        places += [p for p in path_strings(ti) if re.search(r"[/\\]", p)]
        calls += [("Other", {"folder": p}) for p in dict.fromkeys(places)]
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
        self._links, self.searched, self.t0, self._real = None, {}, time.monotonic(), {}
        self.cut, self._globs = None, {}  # the wildcard whose matches expand() could not read to the end; its answers

    def _abs(self, p):
        # Looked up on disk once per run of the hook and working folder. Every reading of a line names the same words
        # again: a here-document that holds a script of 1,500 lines took 23 s on Windows (the timer's answer), now 8 s
        key = (str(self.cwd), str(p))
        if key not in self._real:
            pp = Path(os.path.expanduser(winpath(p)))  # not Path.expanduser(): it raises for a user it does not know
            if not pp.is_absolute():
                pp = self.cwd / pp
            try:
                self._real[key] = pp.resolve(strict=False)
            except ValueError:
                # Windows takes no path of more than 32,767 characters, which the program behind -e can be. It ended
                # the whole check as an internal error, a question for a harmless line; such a word names nothing
                # on disk, now and at the next lookup
                self._real[key] = pp
            except (OSError, RuntimeError):
                return pp  # not kept: a lookup that failed is made again at the next one, as before
        return self._real[key]

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
                if time.monotonic() >= self.t0 + WALK_S:  # >=: this clock moves in steps of 15 ms on Windows
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
            if time.monotonic() >= ctx.t0 + WALK_S:
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
    folder = ti.get("folder")  # handed to an MCP tool, which may list or read everything below it. The project root
    if folder:  # stays unasked: tools are given it all the time, as the folder they work in
        if folder[:7].lower() == "file://":
            folder = unquote(re.sub(r"(?i)^file://(?:localhost)?", "", folder))
        hit = reaches_sealed(ctx, folder) if there(ctx._abs(folder), "is_dir") and ctx.rel(folder) != "." else None
        if hit:
            results.append((ASK, f"This call hands an MCP tool the folder '{ctx.rel(folder)}', which holds sealed test "
                                 f"data (pattern '{hit}'): the tool may list or read every file below it. Give it a "
                                 f"folder without sealed files (data/train, say), or approve only if the tool cannot "
                                 f"read or expose sealed content."))
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
            out.append("@" + str(ctx.resolve_token(t)) if t[:1] != "-" and there(ctx._abs(t), "is_file") else t)
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
    raw = QUOTED_COMMAND.sub(r"\1\3", raw) if QUOTED_ANY.search(raw) else raw
    return GIT_WORD.sub("git", re.sub(r"(?i)(['\"])(AllDirectories)\1", r"\2", raw))


def check_bash(ctx: Ctx, cmd: str, depth=0, alt=True, sh=True, lang=False):
    """alt: also check the line as another shell reads it. sh: the text may be a POSIX shell's (the line of a tool
    call, or text handed to a shell), where a brace list stands for names. lang: the line that this text comes from
    runs a program of a language in LANG, so the text may be such a program."""
    cfg = ctx.cfg
    raw = plain(cmd)
    c = GIT_GLOBAL.sub("git", raw)
    c_noq = QUOTED.sub(" '' ", c)
    lang = lang or bool(LANG.search(c_noq))
    results, walked = [], []  # walked: the folders that a command of the line walks, each with its file filters
    unpacked = []  # the folders into which a command of the line unpacks an archive
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
    moves += [(m.start(), True, [re.sub(r"[\"']", "", m.group(1))])
              for m in (CD.finditer(raw) if MAY_CD.search(raw) else ())]
    for _, cd, ds in sorted(moves):  # a cd earlier in the line: what follows is relative to it
        for d in ds:
            ctx.cwd = cur if d is ds[0] else dirs[-1]
            dirs.append(ctx._abs(d))
        cur = dirs[-1] if cd else cur
    dirs = list(dict.fromkeys(dirs))
    resolved, outs, lx = [], [], lex(c)  # lx: the line's words with its options, which toks leaves out
    outw = out_words(lx)
    for d in dirs:
        ctx.cwd = d
        outs += [(t, ctx.resolve_token(t)) for t in outw if len(t) < 4096]
        outs += [(t, r) for t in outw if any(ch in t for ch in "*?[") for r in ctx.expand(t)]  # sort -o ev*/m.py
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
            recursive = bool(ctx.recursive_re.search(c_noq) or GIT_READS.search(c_noq)
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
                    or EXTRACT.search(c_noq) or (prog and "**" in c)) and not hit else []
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
                for d in runs if EXTRACT.search(sq) else []:  # an archive: where it is unpacked to, see below
                    ctx.cwd = d  # env's own -C is no option of the program: runs has that folder already
                    unpacked += ["." if t is None else ctx.resolve_token(t)  # any folder: counts as the project
                                 for t in unpacks(lex(ENV_C.sub(r"\1", seg))) or ["."]]
                if x or re.match(r"(?:popd|Pop-Location)\b", seg, re.I):
                    to = []
                    for d in curs if x else []:
                        ctx.cwd = d
                        to += [t for t in [ctx._abs(re.sub(r"[\"']", "", x.group(1)))] if there(t, "is_dir")]
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
                elif found or GIT_READS.search(sq):
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
                    if found:
                        walked += [(b, globs, type_exts(typ)) for b in dict.fromkeys(bases)]
                    else:  # git's own reader lists the tracked files below the folders it names, or below the one
                        # it runs in. ls-files takes its other words as patterns for the whole of that folder
                        specs = [t for t, _ in args if re.search(r"[*?\[]", t)] if "ls-files" in sq else []
                        wide = [str(d) for d in runs] if specs or not bases else []
                        walked += [(b, [] if bases or any(t[:1] == ":" for t in specs) else specs, None)
                                   for b in dict.fromkeys(wide or bases)]
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
                        if there(b, "is_dir"):  # what follows the ** is a filter on the files below that folder
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
    # The text that the line hands to a shell counts with it: in f=eval/metrics.py sh -c 'rm "$f"' the verb stands
    # in the text and the path in front of it. cmd: a quoted word behind a bracket lost its quotes above, .open('w'),
    # and so did one behind a bar, awk's print | "sh"
    inner = inner_code(c)
    flat = c_noq + "".join(" ; " + QUOTED.sub(" '' ", plain(s)) for s in inner)
    # an output option whose word is a variable or a command's output (sort -o "$f", curl -o `echo f`) may write any
    # path that the line names, as a verb does
    verb = bool(VERBS.search(flat) or PS_WRITE.search(flat) or WRITE_CMDS.search(flat)
                or FORMATS.search(flat) or EXTRACT.search(flat) or PATCHES.search(flat)
                or (code and (PY_WRITES.search(c) or PY_WRITES.search(cmd) or PY_OPENS.search(c)))
                or (lang and LANG_WRITES.search(c))
                or (AWK.search(flat) and (AWK_WRITES.search(c) or (cmd != c and AWK_WRITES.search(cmd))))
                or any(re.search(r"[$`]", w) for s in [c] + inner for w in out_words(lex(s))))
    # A redirection writes the file it names, and so does tee: python eval/evaluate.py > score.json reads the frozen
    # file. Where they are all that the tool call's own line writes with, only the files they name count as written.
    # Not in a text handed on (depth, and the rest of flat): there > may be a comparison in a program
    saved = None if verb or depth or WRITE_VERBS.search(flat[len(c_noq):]) else saves(cmd, c)
    verb = verb or bool(saved is None and WRITE_VERBS.search(flat))
    # A command that changes a folder as a whole (mv eval old, rm -r .claude, git checkout HEAD eval), and one that
    # picks the files it changes itself: find with -delete, an edit of the files that a search of the line lists
    # (find -exec, | xargs, $(...)), a formatter given a folder
    kept, whole = [*ctx.frozen(), *(cfg.get("harness_paths") or [])], []
    went = {d for _, cd, ds in moves if cd for d in ds}  # where a cd goes is no folder that the line changes
    if TREE_VERBS.search(flat):
        # the shell's own eval is no folder of that name
        own = (len(re.findall(_GO_EACH + r"eval(?=\s)", c_noq, re.M))
               if re.search(_GO + r"eval(?=\s)", c_noq, re.M) else 0)
        whole += [(rel, (), None) for t, rel in resolved
                  if rel and rel != "." and rel[:1] != "/" and ":" not in rel and t not in went
                  and not (t == "eval" and lx.count("eval") <= own)]
    if FIND_DELETES.search(c_noq) or (FED.search(c_noq) and (MASS_EDIT.search(flat) or LOOP_OUT.search(c))) \
            or PS_FED.search(c_noq):
        whole += [(ctx.rel(b), globs, typ) for b, globs, typ in walked]
    n = len(whole)  # from here on: what a formatter is given, which gets its own words (ROUTINE)
    # a formatter's own arguments, or the folder it runs in
    for m in FORMATS_EACH.finditer(c_noq) if FORMATS.search(c_noq) else ():
        args = [t for t in itertools.takewhile(lambda t: t.strip(";&|()<>"), lex(c_noq[m.end():])) if t[:1] != "-"]
        for d in dirs:
            ctx.cwd = d
            whole += [(ctx.resolve_token(t), PY_FILES, None) for t in args or ["."]]
    ctx.cwd = here
    for part, what, do in ((whole[:n], "Command changes a whole folder, or the files that it finds there itself, and "
                                       "files that this guard keeps lie in it", "change"),
                           (whole[n:], "A formatter would rewrite files that this guard keeps", "format")):
        over = next((p for rel, globs, typ in part for p in [below(ctx, rel, kept, globs, typ)] if p), None)
        if over:
            results.append((ASK, f"{what} (pattern '{over}': frozen evaluation/protocol files or the harness). Name "
                                 f"the files or folders to {do}, or approve only if these files stay as they are."))
    # An archive is unpacked into a folder, and the names of its files stand in the archive, not on the line. Above,
    # each command of the line gave the folder it unpacks to, seen from the folders it may run in (cd raw && tar -xf
    # ../x.tar). Here: program text, which names the folder in the call (extractall('raw'), unpack_archive('x.tar',
    # 'raw')), and a line whose commands were not read one by one; both from every folder that the line goes to.
    # The sealed files count too: unpacking reads none of them, and may put another file in the place of one. So do
    # git's own files that the write rules below keep. A folder above the project counts as the project: an archive
    # unpacked there may hold a path that leads into it. cmd: a quoted word behind a bracket lost its quotes above,
    # and extractall('raw') would name a variable, which may be any folder
    late = (py_unpacks(cmd.replace("\\", "/")) if code else []) + ["."] * bool(EXTRACT.search(c_noq) and not unpacked)
    unpacked += ["."] * (None in late)  # a folder that the text does not let this read: counts as the project
    for d in dirs if late else []:
        ctx.cwd = d
        unpacked += [ctx.resolve_token(t) for t in late if t is not None]
    ctx.cwd = here
    above = {p.as_posix() for p in ctx.root.parents}
    over = next((p for rel in unpacked if rel for p in [below(ctx, "." if rel in above else rel, [
        *kept, *(sealed or []), ".git/hooks/**", ".git/config", ".git/worktrees/**"])] if p), None)
    if over:
        results.append((ASK, f"Unpacks an archive into a folder in which files that this guard keeps lie (pattern "
                             f"'{over}': frozen evaluation/protocol files, the harness, sealed test data or git's own "
                             f"files), and an archive may hold a file of any name. Unpack it into a folder of its own "
                             f"(tar -C <folder>, unzip -d <folder>) and move over what is needed, or approve only if "
                             f"these files stay as they are."))
    for d in dirs if saved else []:  # read from every folder that the line goes to, as an output option's word is
        ctx.cwd = d
        outs += [(t, ctx.resolve_token(t)) for t in saved]
    ctx.cwd = here
    if verb or outs:
        # with a write verb every path of the line may be the one written; without one, only the word that an
        # output option, a redirection or tee names is: grep -o def eval/metrics.py reads the file, sort -o
        # eval/metrics.py x writes it
        named = resolved if verb else outs
        # the search by name reads the whole line, or the written words that are not placed inside the project: in
        # another spelling (Git Bash's /c/Users/..., a mounted drive) such a path may still be a kept file
        fuzzy = c if verb else " ".join(t for t, rel in outs if not rel or rel[:1] == "/" or ":" in rel)
        if any(matches(rel, cfg.get("harness_paths")) for _, rel in named) or \
                any(rx.search(fuzzy) for _, rx in fragments(cfg.get("harness_paths"))):
            results.append((ASK, "Command may modify harness guardrail files (hooks, settings, guard config, skill, "
                                 "agents, CLAUDE.md, .mcp.json). Approve only if intended."))
        if any(matches(rel, ctx.frozen()) for _, rel in named) or \
                any(rx.search(fuzzy) for _, rx in fragments(ctx.frozen())):
            results.append((ASK, "Command may modify frozen evaluation/protocol files: that creates a new protocol "
                                 "version and requires re-baselining."))
        if any(rel and re.search(r"(?:^|/)\.git/(?:worktrees/|hooks/|config$|nn-training-final-eval\.jsonl$)", rel, _CASE)
               for _, rel in named):
            results.append((ASK, "Command may modify files in git's own folder: its list of worktrees, from which this "
                                 "guard reads the repository's other checkouts, its hooks or its configuration, which "
                                 "make git run programs that this guard does not see, or the record of the final "
                                 "evaluation's uses that every checkout shares. Approve only if intended."))
        for r in ctx.active():
            rd = (r.get("dir") or "").rstrip("/")
            if rd and any(rel == rd or rel.startswith(rd + "/") for _, rel in named):
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
    if PATCHES.search(c_noq):  # ROUTINE: where the line names a kept file as well, the write rules add their reason
        results.append((ASK, "Applies a patch: it changes the files that the patch names, and this guard reads the "
                             "command, not the patch (`git apply --stat <patch>` lists them). Approve only if no "
                             "frozen file and no harness file is among them, or make the change with the edit tools."))
    if GIT_CLEAN_IGNORED.search(c):  # a reason of its own: with it the refusal is not marked routine
        results.append((ASK, "A forced git clean with -x or -X also deletes what git ignores, and data, run folders "
                             "and checkpoints are usually among that."))
    if GIT_PUSH.search(c):  # a forced push is both
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
    if depth >= 3 and not is_final and (inner_code(GIT_GLOBAL.sub("git", cmd)) or inner_code(c)):
        results.append((ASK, "Command hands text to a shell or an interpreter more than three levels deep (a shell in "
                             "a shell in a shell ...), deeper than this guard reads. Run the inner command by itself, "
                             "or approve only if you know what it does."))
    if depth < 3 and not is_final:  # what it hands to a nested shell or interpreter obeys the same rules, in every
        # folder the line moves to: after `cd data`, the code's test/labels.csv is data/test/labels.csv.
        # First from the line as it came: there the text still has the backslashes that readings() looks at and the
        # quotes of walk('data'). Then from the line as the rules read it, where that gives another text
        seen = set()
        for s in dict.fromkeys(inner_code(GIT_GLOBAL.sub("git", cmd)) + inner_code(c)):
            if plain(s) not in seen:
                seen.add(plain(s))
                for d in dirs:
                    ctx.cwd = d
                    results += check_bash(ctx, s, depth + 1, sh=bool(POSIX_SHELL.search(c_noq)), lang=lang)
        ctx.cwd = here
    others, long = readings(cmd) if alt else ([], False)
    if long and sh:  # program text (python -c "...") has braces of its own
        results.append((ASK, "A word of this command stands for more than 64 names (a brace list such as "
                             "{a,b}{c,d}...), more than this guard writes out to check them. Name the files one by "
                             "one, or approve only if none of them is sealed test data."))
    for other in others:  # every rule above, for the line as another shell reads it
        results += check_bash(ctx, other, depth, False, sh, lang)
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
    """Extra rules for the read-only subagents. They read the line as it stands and as each shell may read it, and
    since 21 November 2026 each of those, and each text that the line hands to a shell, once more with its command
    words named plainly (see named()): until then a program in quotes or behind a path with backslashes was not
    seen as that program here ('touch' notes.md, C:\\msys64\\usr\\bin\\touch.exe notes.md).
    shortcut: not in the form that plain() gives the main session's rules, which turns every backslash into a slash
    and takes the quotes off a word behind a bracket, and would refuse harmless program text here
    (print(\\"a > b\\"), d.get("patch") in single quotes). So a quoted program is seen here where named() sees one
    and no further: see its shortcut (a kept file is asked about all the same, because the main rules read the line
    too). Upgrade with the shell's own splitting of words"""
    if tool in EDIT_TOOLS:
        return [(DENY, "Read-only agent: it may not edit files. Report what needs changing to the main session.")]
    if tool != "Bash":
        return []
    why, lines = None, [ti["command"]] + readings(ti["command"])[0]  # r\m is rm to a POSIX shell, "rm" is rm
    for cmd in lines:
        c, shell = GIT_GLOBAL.sub("git", GIT_WORD.sub("git", cmd)), []
        texts = [QUOTED.sub(" '' ", t) for t in [c] + inner_code(c, shell)]
        # a text that the line hands to a shell (bash -c "'touch' notes.md") is a line too, where named() changes it
        lines += [t for t in dict.fromkeys(map(named, shell)) if t not in shell and t not in lines]
        if any(WRITE_VERBS.search(t) or PS_WRITE.search(t) or WRITE_CMDS.search(t) or FORMATS.search(t)
               or EXTRACT.search(t) for t in texts) or PY_WRITES.search(c) \
                or (any(LANG.search(t) for t in texts) and LANG_WRITES.search(c)) \
                or (any(AWK.search(t) for t in texts) and AWK_WRITES.search(c)):
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


# Asks about a session's own work and nothing else: git that discards work or rewrites history (all of
# GIT_DESTRUCTIVE: a hard reset, a forced checkout or clean, a dropped stash, a deleted branch, also of committed
# work), a formatter given a folder in which kept files lie, a patch, and an archive unpacked into such a folder:
# the last two are asked about for what the line does not show, and where it names a kept file the write rules add
# a reason of their own. A forced clean that takes ignored files along has a second reason and is not among them.
# Where nobody can be asked they are refused like every ask. The unattended loop takes a refused call as a sign of
# tampering and drops the session's change; not these, which the beacon marks
ROUTINE = ("Destructive git operation", "A formatter would rewrite", "Applies a patch", "Unpacks an archive")


def beacon(payload, calls, decision, reason="", routine=False):
    """For the unattended loop: one line per checked call in the file NN_GUARD_BEACON names, allows included, so
    that the harness can tell that the guard ran in a session and what it refused. routine: every reason of the
    refusal is one of ROUTINE (the reason is cut short here, so the loop could not tell)."""
    path = os.environ.get("NN_GUARD_BEACON")
    if path:
        ti = calls[0][1] if calls else {}
        try:
            append_line(path, dict({"tool": calls[0][0] if calls else str(payload.get("tool_name") or "")[:80],
                                    "decision": decision, "reason": reason[:300],
                                    "input": str(ti.get("command") or ti.get("file_path") or ti.get("path")
                                                 or ti.get("pattern") or "")[:300]}, **({"routine": True} if routine else {})))
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
    routine = decision == ASK and all(r.startswith(ROUTINE) for r in reasons)
    if decision == ASK:
        why = nobody_to_ask(payload, agent)
        if why:
            decision = DENY
            reason += (f" | ({why}, so nobody can be asked: denied. If the action is intended, the user runs it "
                       f"themselves or approves it in an interactive Claude Code session.)")
    beacon(payload, calls, decision, reason, routine)
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
    # A thread that sleeps, not threading.Timer. A Timer waits on a lock, and before Python 3.11 (and since, where the
    # C library has no sem_clockwait(): bpo-41710) that wait goes by the system's clock: one that was set forward ended
    # these seconds at once, and one that was set back made them longer than the hook's own. In WSL on 19 November
    # 2026 a Timer of 12 s took 3.2 s and 15.0 s under Python 3.8 (12.0 s under 3.12); a sleep took 12.0 s under both
    timer = threading.Thread(target=lambda: (time.sleep(LIMIT), late()), daemon=True)
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
