#!/usr/bin/env python3
"""Install, upgrade or remove the nn-training harness in a project (stdlib only, Python 3.8+).

    python install.py --target /path/to/repo --dry-run      # show what would change
    python install.py --target /path/to/repo                # install / upgrade for Claude Code
    python install.py --target /path/to/repo --agents all   # also Codex and Cursor
    python install.py --target /path/to/repo --uninstall    # remove what an install wrote

Options:
    --agents LIST       claude, codex, cursor (comma separated) or all. Default: what the last install
                        chose, else claude. The kit's files always live in .claude/; a port adds only the
                        agent's own hook, agent and instruction files.
    --python-cmd CMD    interpreter written into every command the kit installs (default: the one the last
                        install recorded or wrote into its guard hook, else python3; python on native Windows).
                        It is run once to check it.
    --statusline        also set the Claude Code status line (training progress under the prompt)
    --mcp               also add the optional MCP servers of mcp.json (they need network; off by default)
    --runs-dir DIR      run directory to configure on first install (default: runs)
    --worktrees         also register the guard for Claude Code sessions in the repository's other checkouts
                        (the main checkout and the worktrees git has registered), which otherwise run without
                        it: one hook entry in each one's .claude/settings.local.json that runs this target's
                        guard. Run it again after you add a worktree; --uninstall takes the entries out.

Writes only inside the target project, except with --worktrees (those entries, and one line in the repository's
.git/info/exclude where git does not ignore that file yet). Your own settings are merged key by key, the
instruction file gets one marked block, and every file that changes is first copied to
.claude/backups/nn-training-<timestamp>/.
A kit file that was edited after install is replaced too, and named in the report with its backup.
A settings file of yours that is not valid JSON, or whose hooks are not in the form its agent documents, stops the
installer before anything is changed. Removal takes the hook entries out before the scripts they run.
Restart the agent afterwards so the hooks load.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parent
BEGIN = "<!-- nn-training-harness:begin -->"
END = "<!-- nn-training-harness:end -->"
GITIGNORE_MARK = "# nn-training harness"
COPY_TREES = [".claude/skills/nn-training", ".claude/agents", ".claude/hooks"]
MANIFEST = ".claude/nn-training.manifest.json"
AGENTS = ("claude", "codex", "cursor")
KIT_HOOKS = ("nn_guard.py", "nn_session_status.py")
LOCAL = ".claude/settings.local.json"
POINTER =("The files of this skill live in `.claude/skills/nn-training/`. Read "
           "`.claude/skills/nn-training/SKILL.md` now and follow it; the `references/` and `scripts/` paths it "
           "names are relative to that folder.\n")


def sha(data: bytes) -> str:
    """Hash with line endings normalised, so a CRLF checkout of an untouched file still counts as untouched."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def exe_text(py: str) -> str:
    """The interpreter as written into a command: forward slashes, quoted when it has spaces."""
    exe = py.replace("\\", "/")
    return '"' + exe.replace('"', '\\"') + '"' if any(ch in exe for ch in ' "\'') else exe


def with_interpreter(command: str, py: str) -> str:
    """Swap the leading 'python3 ' of a hook command for the chosen interpreter."""
    if py == "python3" or not command.startswith("python3 "):
        return command
    return exe_text(py) + command[len("python3"):]


def localize(text: str, py: str) -> str:
    """Kit files are written for `python3`; put the chosen interpreter into every command they show or run."""
    if py == "python3":
        return text
    exe = exe_text(py)

    def swap(m):  # in a YAML value in single quotes (the agent files' hook command) an apostrophe is written twice
        line = text[text.rfind("\n", 0, m.start()) + 1:m.start()]
        return exe.replace("'", "''") if re.match(r"\s*[\w-]+: '", line) else exe
    return re.sub(r"(?<![\w./-])python3(?= )", swap, text)


def legacy_python(target: Path):
    """The interpreter in the guard hook of an install that kept no other record of it (the 23 October version)."""
    for groups in (load_json(target / ".claude/settings.json").get("hooks") or {}).values():
        for g in groups if isinstance(groups, list) else []:
            for h in (g.get("hooks") or []) if isinstance(g, dict) else []:
                m = re.match(r'\s*("[^"]+"|\S+)\s.*nn_guard\.py', str(h.get("command", "")) if isinstance(h, dict) else "")
                if m and m.group(1).strip('"') not in ("python", "python3"):
                    return m.group(1).strip('"')
    return None


def check_python(py: str):
    try:
        r = subprocess.run([py, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                           capture_output=True, text=True, timeout=60)
        ver = tuple(int(x) for x in r.stdout.strip().split(".")) if r.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        ver = None
    if not ver or ver < (3, 8):
        sys.exit(f"install: the interpreter '{py}' does not run or is older than Python 3.8 (on Windows `python3` is "
                 f"often a Microsoft Store stub). Pass a working one with --python-cmd; nothing was changed.")


class Plan:
    def __init__(self, target: Path, dry: bool, old_manifest: dict):
        self.target, self.dry = target, dry
        self.backup_dir = target / ".claude" / "backups" / f"nn-training-{time.strftime('%Y%m%d-%H%M%S')}"
        self.log = []
        self.backed_up = 0
        self.old_files = old_manifest.get("files") or {}
        legacy = KIT / "install-legacy.json"  # hashes of the files earlier kit versions installed
        self.legacy = json.loads(legacy.read_text(encoding="utf-8")) if legacy.exists() else {}
        self.files = {}      # what this install owns: relative path -> hash of what it wrote
        self.replaced = []   # kit files that were not as any install left them

    def rel(self, path: Path) -> str:
        """The path below the target. A file elsewhere (--worktrees) gets a name of its own in the backup."""
        try:
            return path.relative_to(self.target).as_posix()
        except ValueError:
            return "outside-target/" + re.sub(r"[^\w.-]+", "_", path.as_posix()).strip("_")

    def note(self, kind, path, detail=""):
        if isinstance(path, Path):  # a file elsewhere is shown by its full path
            path = os.path.relpath(path, self.target) if self.target in (path, *path.parents) else str(path)
        self.log.append((kind, path, detail))

    def backup(self, path: Path):
        if self.dry or not path.exists():
            return
        dest = self.backup_dir / self.rel(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        self.backed_up += 1

    def put(self, path: Path, data, kind="update", owned=False):
        """Write one file (bytes, or text that keeps the file's CRLF if it has any). `owned` marks a file that is
        the kit's alone: it goes into the manifest, and a copy that no install wrote is reported when replaced."""
        old = path.read_bytes() if path.exists() else None
        if isinstance(data, str):
            data = data.replace("\r\n", "\n")
            data = (data.replace("\n", "\r\n") if old and b"\r\n" in old else data).encode("utf-8")
        rel = self.rel(path)
        if owned:
            self.files[rel] = sha(data)
        if old is not None and sha(old) == sha(data):
            self.note("same", path)
            return
        if old is None:
            kind = "create"
        elif owned:
            known = sha(old) in [self.old_files.get(rel)] + self.legacy.get(rel, [])
            kind = "upgrade" if known else "replace"
            if not known:
                self.replaced.append(rel)
        self.note(kind, path, "was edited after install, or is not from this kit; your copy is in the backup"
                  if kind == "replace" else "")
        if self.dry:
            return
        self.backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def remove(self, path: Path, detail=""):
        self.note("remove", path, detail)
        if not self.dry:
            self.backup(path)
            path.unlink()


def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except ValueError as e:
        sys.exit(f"install: {path} is not valid JSON ({e}); fix it first, nothing was changed.")
    if not isinstance(data, dict):
        sys.exit(f"install: {path} does not hold a JSON object; fix it first, nothing was changed.")
    return data


@contextlib.contextmanager
def shape_of(path: Path):
    """Around a merge of the kit's entries into a file of the user's: one whose hooks or rules are not in the form
    its agent documents stops the installer, because the entries cannot be put into it."""
    try:
        yield
    except (AttributeError, TypeError):
        sys.exit(f"install: the hooks or permission rules in {path} are not in the form its agent documents, so the "
                 "kit's entries cannot be merged into it; fix it first, nothing was changed.")


def dump(obj) -> str:
    return json.dumps(obj, indent=2) + "\n"


def fill_missing(dst: dict, src: dict):
    """Add keys from src that dst lacks (recursively); never overwrite user values."""
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
        elif isinstance(dst[k], dict) and isinstance(v, dict):
            fill_missing(dst[k], v)
    return dst


def swap_kit_hook(groups, script: str, new_group=None):
    """Hook groups (Claude Code and Codex share the shape) without the kit's entry for `script`, plus the fresh
    one. The user's own hooks stay, also when they share a group with the kit's, and so does whatever is not in
    that shape; a fresh entry cannot be added to an event that is no list. Returns (groups, old entries)."""
    if not isinstance(groups, list):
        if new_group:
            raise TypeError("the hooks of this event are not a list")
        return groups, []
    kept, old = [], []
    for g in groups:
        hs = g.get("hooks") if isinstance(g, dict) else None
        mine = [h for h in hs if script in json.dumps(h)] if isinstance(hs, list) else []
        old += mine
        rest = [h for h in hs if h not in mine] if mine else hs
        if rest or not mine:
            kept.append(dict(g, hooks=rest) if mine else g)
    return kept + ([new_group] if new_group else []), old


def merge_hooks(out: dict, frag_hooks: dict, notes: list):
    hooks = out.setdefault("hooks", {})
    for event, groups in frag_hooks.items():
        for g in groups:
            script = next(s for s in KIT_HOOKS if s in json.dumps(g))
            hooks[event], old = swap_kit_hook(hooks.get(event, []), script, g)
            if old and old != g["hooks"]:
                notes.append(f"{event} hook for {script} brought to the current form (the old entry is in the backup)")


def strip_hooks(out: dict, scripts=KIT_HOOKS):
    """Remove the kit's hook entries (uninstall). Hooks in a form of the user's own are left as they are."""
    hooks = out.get("hooks")
    for event in list(hooks) if isinstance(hooks, dict) else []:
        for script in scripts:
            hooks[event], _ = swap_kit_hook(hooks[event], script)
        if hooks[event] == []:
            del hooks[event]


def merge_settings(existing: dict, frag: dict, statusline: bool, py: str):
    out = json.loads(json.dumps(existing))
    frag = json.loads(json.dumps(frag))
    notes = []
    perms = out.setdefault("permissions", {})
    for key in ("allow", "ask", "deny"):
        for rule in frag.get("permissions", {}).get(key, []):
            lst = perms.setdefault(key, [])
            # the read-only expctl commands are also allowed in the form the installed files show them
            for r in (rule, rule.replace("Bash(python3 ", f"Bash({exe_text(py)} ")):
                if r not in lst:
                    lst.append(r)
    for groups in frag.get("hooks", {}).values():
        for g in groups:
            for h in g.get("hooks", []):
                h["command"] = with_interpreter(h["command"], py)
    merge_hooks(out, frag.get("hooks", {}), notes)
    sl = dict(frag["statusLine"], command=with_interpreter(frag["statusLine"]["command"], py))
    if "nn_statusline.py" in json.dumps(out.get("statusLine") or ""):
        out["statusLine"] = sl
    elif statusline and not out.get("statusLine"):
        out["statusLine"] = sl
    elif statusline:
        notes.append("statusLine already set by you; left unchanged (edit .claude/settings.json to switch).")
    return out, notes


def codex_hooks(py: str) -> dict:
    """Codex runs a hook from the session's directory: the POSIX form asks git for the root (as its docs do);
    the Windows form has no quotes, because Codex's Windows hook runner is unreliable with them."""
    unix, win = (py, "python") if os.name != "nt" else ("python3", py)
    win = exe_text(win).replace("/", "\\")  # cmd.exe reads a forward slash in the program path as a switch

    def h(script, extra, timeout):
        return {"type": "command", "timeout": timeout,
                "command": f'{exe_text(unix)} "$(git rev-parse --show-toplevel)/.claude/hooks/{script}"{extra}',
                "commandWindows": f"{win} .claude\\hooks\\{script}{extra}"}
    return {"PreToolUse": [{"hooks": [h("nn_guard.py", " --agent codex", 20)]}],
            "SessionStart": [{"hooks": [h("nn_session_status.py", "", 30)]}]}


def cursor_hooks(py: str) -> dict:
    """Cursor runs project hooks from the project root. failClosed: a crashed or timed-out guard blocks."""
    g = {"command": f"{exe_text(py)} .claude/hooks/nn_guard.py --agent cursor", "timeout": 20, "failClosed": True}
    return {"beforeShellExecution": [g], "beforeReadFile": [g], "preToolUse": [g],
            "sessionStart": [{"command": f"{exe_text(py)} .claude/hooks/nn_session_status.py --agent cursor",
                              "timeout": 30}]}


def merge_cursor_hooks(existing: dict, fresh: dict):
    out = json.loads(json.dumps(existing))
    out.setdefault("version", 1)
    hooks = out.setdefault("hooks", {})
    if not isinstance(hooks, dict) and not fresh:
        return out  # removal: hooks in a form of the user's own are left as they are (an install stops at them)
    for event in list(hooks):  # drop the kit's old entries wherever they are, keep the user's
        if isinstance(hooks[event], list):
            hooks[event] = [h for h in hooks[event] if not any(s in json.dumps(h) for s in KIT_HOOKS)]
    for event, entries in fresh.items():
        hooks[event] = hooks.get(event, []) + entries
    out["hooks"] = {k: v for k, v in hooks.items() if v != []}
    return out


def git_out(cwd: Path, *args):
    """What a git command prints, None when it fails."""
    try:
        r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def read_settings(path: Path):
    """A settings file of another checkout; None when it cannot be read, so that it is left as it is."""
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}") if path.exists() else {}
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def local_settings(target: Path):
    """Where a Claude Code session in another checkout of the target's repository reads settings of its own:
    .claude/settings.local.json in the folder it starts in (Windows, and versions before 2.1.211), or the one at the
    main checkout's root (other systems, and a worktree session of the desktop app on every system). Source:
    code.claude.com/docs/en/settings and /worktrees, read 13 November 2026.
    Returns (the files that need the guard, every such file)."""
    sub = (git_out(target, "rev-parse", "--show-prefix") or "").strip()
    blocks = [b for b in (git_out(target, "worktree", "list", "--porcelain") or "").strip().split("\n\n")
              if b.startswith("worktree ")]
    tops = [Path(b.split("\n")[0][9:]) for b in blocks if "\nbare" not in b]
    others = [p for p in (top / sub for top in tops) if p.is_dir() and p.resolve() != target]
    bare = [p for p in others
            if "nn_guard.py" not in json.dumps((read_settings(p / ".claude/settings.json") or {}).get("hooks") or {})]
    main = [tops[0] / LOCAL] if blocks and "\nbare" not in blocks[0] else []  # git lists the main checkout first
    # on Windows a session reads the file of its own folder, so the main checkout's file serves the main checkout
    # alone, and is among `bare` where that checkout has no guard of its own
    need = main if bare and os.name != "nt" else []
    return (list(dict.fromkeys([p / LOCAL for p in bare] + need)),
            list(dict.fromkeys([p / LOCAL for p in others] + main)))


def elsewhere_mark(target: Path) -> str:
    """What tells this target's entry in another checkout's settings from every other hook, as JSON spells it."""
    return json.dumps(f"'{target.as_posix()}/.claude/hooks/nn_guard.py'")[1:-1]


def guard_elsewhere(plan: Plan, frag: dict, py: str, every: bool):
    """--worktrees: register the guard for Claude Code sessions in the repository's other checkouts. The entry runs
    this target's guard with this target as the project, so a session there is held to the same rules, and does
    nothing in a session whose project is the target, where .claude/settings.json runs the guard. When the kit is
    gone from the target it blocks the call (exit code 2 does that in every version) and says how to end that.
    Without the flag nothing is written there: an entry of an earlier run that is out of date is named."""
    t = plan.target.as_posix()
    need, known = local_settings(plan.target)
    if every and re.search(r"""["'$`\\\x00-\x1f]""", t):
        return plan.note("warn", plan.target, "--worktrees: the project's path holds a character that a shell or "
                         "Python reads as its own (a quote, $, a backtick or a backslash): no guard was registered "
                         "in the other checkouts")
    group = json.loads(json.dumps(next(g for g in frag["hooks"]["PreToolUse"] if "nn_guard.py" in json.dumps(g))))
    group["hooks"][0]["command"] = (
        f"{exe_text(py)} -c \"import os,sys,runpy;t='{t}';g='{t}/.claude/hooks/nn_guard.py';"
        "os.path.isfile(g) or (sys.stderr.write('nn-training guard: '+g+' is missing, so tool calls are blocked here. "
        f"Put the kit back, or delete this hook entry from {LOCAL} of this checkout and of the main checkout.'),"
        "sys.exit(2));os.path.samefile(os.environ.get('CLAUDE_PROJECT_DIR') or '.',t)"
        " or (os.environ.update(CLAUDE_PROJECT_DIR=t),runpy.run_path(g,run_name='__main__'))\"")
    def put(path, data, kind, lost):  # a file outside the target that cannot be written does not end the install
        n = len(plan.log)
        try:
            plan.put(path, data, kind=kind)
            return True
        except OSError as e:
            del plan.log[n:]
            plan.note("warn", path, f"could not be written ({e.strerror}): {lost}")

    unignored = False
    for sp in need if every else known:
        cur = read_settings(sp)
        try:
            hooks = cur.setdefault("hooks", {})
            hooks["PreToolUse"], old = swap_kit_hook(hooks.get("PreToolUse", []), elsewhere_mark(plan.target), group)
        except (AttributeError, TypeError):
            if every:  # without the flag nothing was to be written there
                plan.note("warn", sp, "not a settings file in the form Claude Code documents: left as it is, and no "
                                      "guard is registered there")
            continue
        if not every:
            if old and old != group["hooks"]:
                plan.note("warn", sp, "holds the guard entry of an earlier --worktrees run in another form (the "
                                      "interpreter or the kit changed): run the installer with --worktrees")
            continue
        if git_out(sp.parent.parent, "ls-files", "--error-unmatch", LOCAL) is not None:
            plan.note("warn", sp, "tracked in git: an entry with this machine's paths could be committed and would "
                                  "block the agent wherever that commit goes, so no guard is registered there")
            continue
        if put(sp, dump(cur), "merge", "no guard is registered there"):
            unignored = unignored or git_out(sp.parent.parent, "check-ignore", "-q", LOCAL) is None
    common = (git_out(plan.target, "rev-parse", "--git-common-dir") or "").strip()
    if unignored and common:  # Claude Code keeps this file out of git only where it writes the file itself
        ex = plan.target / common / "info" / "exclude"
        was = ex.read_bytes() if ex.exists() else b""  # bytes: nothing says that this file is UTF-8
        line, nl = ("**/" + LOCAL).encode(), b"\r\n" if b"\r\n" in was else b"\n"
        if line not in was.splitlines() and put(ex, was + (nl if was and not was.endswith(b"\n") else b"") + line + nl,
                                                "append", f"keep {LOCAL} out of your commits yourself"):
            plan.note("note", ex, f"git now ignores {LOCAL} in this repository on this machine, so that the entry "
                                  "is not committed by accident")
    if every and not need:
        plan.note("note", plan.target, "--worktrees: no other checkout of this repository is without the guard")


def frontmatter(text: str):
    """(fields, body) of a Claude Code agent file; only the top-level `key: value` lines are read."""
    _, head, body = text.split("---", 2)
    fields = dict(m.groups() for m in re.finditer(r"^(\w+):[ \t]*(\S.*?)[ \t]*$", head, re.M))
    return fields, body.lstrip("\n")


def port_agents(plan: Plan, agents, py: str):
    """The two read-only subagents in each agent's own format, generated from the Claude Code files."""
    for src in sorted((KIT / ".claude" / "agents").glob("*.md")):
        f, body = frontmatter(localize(src.read_text(encoding="utf-8"), py))
        if "cursor" in agents:  # readonly: Cursor itself keeps the subagent from writing
            plan.put(plan.target / ".cursor" / "agents" / src.name,
                     f"---\nname: {f['name']}\ndescription: {f['description']}\nreadonly: true\n---\n\n{body}", owned=True)
        if "codex" in agents:  # a JSON string is a valid TOML basic string
            q = lambda s: json.dumps(s, ensure_ascii=False)  # noqa: E731
            plan.put(plan.target / ".codex" / "agents" / (src.stem + ".toml"),
                     f"name = {q(f['name'])}\ndescription = {q(f['description'])}\n"
                     f"developer_instructions = {q(body)}\n", owned=True)


def put_block(plan: Plan, path: Path, block: str, old_block_hash):
    """Insert or replace the kit's marked block in an instruction file, keeping everything else."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    block = f"{BEGIN}\n{block.strip()}\n{END}"
    if BEGIN in text and END in text:
        pre, rest = text.split(BEGIN, 1)
        old, post = rest.split(END, 1)
        known = [old_block_hash] + plan.legacy.get("block:" + path.name, [])
        if sha((BEGIN + old + END).encode("utf-8")) not in known + [sha(block.encode("utf-8"))]:
            plan.replaced.append(f"the kit's block in {path.name}")
        new = pre + block + post
    else:
        new = (text.rstrip() + "\n\n" if text.strip() else "") + block + "\n"
    plan.put(path, new, kind="merge")
    return sha(block.encode("utf-8"))


def strip_block(plan: Plan, path: Path):
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if BEGIN in text and END in text:
        pre, rest = text.split(BEGIN, 1)
        new = (pre.rstrip() + "\n" + rest.split(END, 1)[1].lstrip("\n")).strip()
        plan.put(path, new + "\n", kind="strip") if new else plan.remove(path, "held only the kit's block")


def ensure_gitignore(plan: Plan, runs_dir: str):
    path = plan.target / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = {ln.strip() for ln in text.splitlines()}
    want = [p for p in (".claude/state/", ".claude/backups/", ".claude/worktrees/", runs_dir.rstrip("/") + "/")
            if p not in lines and p.rstrip("/") not in lines and "/" + p not in lines]
    if not want:
        plan.note("same", path)
        return
    add = ("\n" if text and not text.endswith("\n") else "") + f"{GITIGNORE_MARK}\n" + "\n".join(want) + "\n"
    plan.put(path, text + add, kind="append")


def install(plan: Plan, a, agents, py: str, old: dict):
    target = plan.target
    if not (target / ".git").exists():
        plan.note("warn", target, "not a git repository: provenance falls back to source-file hashing")
    if exe_text(py).startswith('"'):
        plan.note("warn", target, "the interpreter path has a space or a quote, so hook commands quote it; PowerShell and "
                                  "Codex on Windows cannot run that form. Prefer a path without either.")

    for tree in COPY_TREES:  # the kit's home for every agent
        for src in sorted(p for p in (KIT / tree).rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            data = src.read_bytes()
            if src.suffix == ".md":
                data = localize(data.decode("utf-8"), py)
            plan.put(target / src.relative_to(KIT), data, owned=True)

    cfg_path = target / ".claude" / "nn-training.json"
    default_cfg = json.loads((KIT / ".claude" / "nn-training.json").read_text(encoding="utf-8"))
    cur = load_json(cfg_path)
    cfg = fill_missing(json.loads(json.dumps(cur)), default_cfg) if cur else dict(default_cfg, runs_dir=a.runs_dir)
    if a.python_cmd or not cfg.get("python"):
        cfg["python"] = py.replace("\\", "/")  # shown in suggested commands, which must also work in Git Bash
    added = [p for p in default_cfg["harness_paths"] if p not in cfg.get("harness_paths", [])]
    if cur and added:  # a list the user may have extended: new protected paths are added, none removed
        cfg["harness_paths"] = cfg.get("harness_paths", []) + added
        plan.note("note", cfg_path, "harness_paths gained: " + ", ".join(added))
    plan.put(cfg_path, dump(cfg), kind="add-missing-keys")

    frag = json.loads((KIT / "settings.fragment.json").read_text(encoding="utf-8"))
    if "claude" in agents:
        sp = target / ".claude" / "settings.json"
        with shape_of(sp):
            merged, notes = merge_settings(load_json(sp), frag, a.statusline, py)
        plan.put(sp, dump(merged), kind="merge")
        for n in notes:
            plan.note("note", sp, n)
    if "codex" in agents:
        hp = target / ".codex" / "hooks.json"
        merged, notes = load_json(hp), []
        with shape_of(hp):
            merge_hooks(merged, codex_hooks(py), notes)
        plan.put(hp, dump(merged), kind="merge")
        for n in notes + ["Codex runs project hooks only after you trust the project and approve each hook once "
                          "in /hooks (again whenever a hook entry changes)"]:
            plan.note("note", hp, n)
        fm, _ = frontmatter((KIT / ".claude/skills/nn-training/SKILL.md").read_text(encoding="utf-8"))
        plan.put(target / ".agents/skills/nn-training/SKILL.md",
                 f"---\nname: {fm['name']}\ndescription: {fm['description']}\n---\n\n{POINTER}", owned=True)
    if "cursor" in agents:
        hp = target / ".cursor" / "hooks.json"
        with shape_of(hp):
            merged = merge_cursor_hooks(load_json(hp), cursor_hooks(py))
        plan.put(hp, dump(merged), kind="merge")
        cp = target / ".cursor" / "cli.json"
        cli = load_json(cp)
        deny = cli.setdefault("permissions", {}).setdefault("deny", [])
        deny += [r for r in ("Read(.env*)", "Write(.claude/hooks/**)", "Write(.claude/nn-training.json)",
                             "Write(.cursor/hooks.json)") if r not in deny]
        plan.put(cp, dump(cli), kind="merge")
    port_agents(plan, agents, py)

    mcp = json.loads((KIT / "mcp.json").read_text(encoding="utf-8")).get("mcpServers", {})
    for name, mp in (("claude", target / ".mcp.json"), ("cursor", target / ".cursor" / "mcp.json")):
        cur = load_json(mp) if name in agents else {}
        have = [k for k in mcp if k in cur.get("mcpServers", {})]
        if a.mcp and name in agents:
            new = [k for k in mcp if k not in have]
            cur.setdefault("mcpServers", {}).update({k: mcp[k] for k in new})
            plan.put(mp, dump(cur), kind="merge")
            if new:
                plan.note("note", mp, "added MCP servers: " + ", ".join(new) + " (the agent asks you to approve them)")
        elif have:
            plan.note("note", mp, "MCP servers " + ", ".join(have) + " are configured and were left as they are; "
                                  "they are optional now (network access): remove them here if you do not use them")

    block = localize((KIT / "instructions-block.md").read_text(encoding="utf-8"), py)
    hashes = dict(old.get("blocks") or {})
    if agents == ["claude"]:
        hashes["CLAUDE.md"] = put_block(plan, target / "CLAUDE.md", block, hashes.get("CLAUDE.md"))
    else:  # one copy of the rules: AGENTS.md, which Codex and Cursor read and Claude Code imports
        hashes["AGENTS.md"] = put_block(plan, target / "AGENTS.md", block, hashes.get("AGENTS.md"))
        if "claude" in agents:
            hashes["CLAUDE.md"] = put_block(plan, target / "CLAUDE.md", "The nn-training harness rules are in "
                                            "AGENTS.md, imported here:\n\n@AGENTS.md", hashes.get("CLAUDE.md"))

    jp = target / "experiments" / "JOURNAL.md"
    if not jp.exists():
        plan.put(jp, (KIT / ".claude/skills/nn-training/templates/JOURNAL.md").read_bytes())
    else:
        plan.note("same", jp, "kept your journal")
    ensure_gitignore(plan, cfg.get("runs_dir") or a.runs_dir)

    for rel in sorted(set(plan.old_files) - set(plan.files)):  # installed earlier, no longer part of the kit
        p = target / rel
        if p.exists() and sha(p.read_bytes()) == plan.old_files[rel]:
            plan.remove(p, "no longer part of the kit")
        elif p.exists():
            plan.note("keep", p, "no longer part of the kit, but edited after install: left in place")
    plan.put(target / MANIFEST, dump({"installed": time.strftime("%Y-%m-%d"), "python": py, "agents": agents,
                                      "blocks": hashes, "files": plan.files}))
    if "claude" in agents:
        guard_elsewhere(plan, frag, py, a.worktrees)
    elif a.worktrees:
        plan.note("warn", target, "--worktrees registers the guard for Claude Code sessions only, and --agents "
                                  "does not name claude: nothing was registered in the other checkouts")


def uninstall(plan: Plan, old: dict):
    target = plan.target
    if not old:
        sys.exit(f"install: no {MANIFEST} in the target, so the kit's files cannot be told from yours. Run the "
                 f"installer once without --uninstall (it records what it writes), then remove.")
    # The hook entries go before the scripts they run: one that outlives its script blocks every tool call
    for sp in local_settings(target)[1]:  # what --worktrees registered in the repository's other checkouts
        data = read_settings(sp)
        if data and elsewhere_mark(target) in json.dumps(data.get("hooks") or {}):
            strip_hooks(data, (elsewhere_mark(target),))
            if not data["hooks"]:
                del data["hooks"]
            try:
                plan.put(sp, dump(data), kind="strip") if data else plan.remove(sp, "held only the kit's entry")
            except OSError as e:
                sys.exit(f"install: {sp} could not be changed ({e.strerror}), so the kit stays where it is: its guard "
                         "entry in that file would block every tool call there once the kit's files are gone. Make "
                         "the file writable and run --uninstall again.")
    for rel, strip in ((".claude/settings.json", strip_hooks), (".codex/hooks.json", strip_hooks),
                       (".cursor/hooks.json", lambda d: d.update(merge_cursor_hooks(d, {})))):
        p = target / rel
        if p.exists():
            data = load_json(p)
            strip(data)
            if "nn_statusline.py" in json.dumps(data.get("statusLine") or ""):
                del data["statusLine"]
            plan.put(p, dump(data), kind="strip")
    for rel, digest in sorted((old.get("files") or {}).items()):
        p = target / rel
        if p.exists() and sha(p.read_bytes()) == digest:
            plan.remove(p)
        elif p.exists():
            plan.note("keep", p, "edited after install: left in place")
    for name in ("CLAUDE.md", "AGENTS.md"):
        strip_block(plan, target / name)
    plan.remove(target / MANIFEST)
    if not plan.dry:  # bytecode caches of the removed scripts, then the folders that are empty now
        for d in sorted({(target / rel).parent for rel in old.get("files") or {}}, key=lambda p: -len(p.parts)):
            shutil.rmtree(d / "__pycache__", ignore_errors=True)
            while d != target and d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                d = d.parent
    plan.note("note", target, "kept: .claude/nn-training.json, the journal, run directories, backups, permission "
                              "rules and .gitignore lines. Delete them yourself if you want them gone.")


def main():
    ap = argparse.ArgumentParser(description="Install, upgrade or remove the nn-training harness.")
    ap.add_argument("--target", required=True, help="project repository root")
    ap.add_argument("--agents", help="claude, codex, cursor (comma separated) or all")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--statusline", action="store_true")
    ap.add_argument("--mcp", action="store_true")
    ap.add_argument("--no-mcp", action="store_true", help=argparse.SUPPRESS)  # the default now; kept for old commands
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--python-cmd")
    ap.add_argument("--worktrees", action="store_true")
    a = ap.parse_args()
    target = Path(a.target).expanduser().resolve()
    if not target.is_dir():
        sys.exit(f"install: target {target} is not a directory")
    if target == KIT:
        sys.exit("install: target is the kit itself; pass your project root")
    old = load_json(target / MANIFEST)
    plan = Plan(target, a.dry_run, old)
    if a.uninstall:
        def run(p):
            uninstall(p, old)
    else:
        agents = [x.strip() for x in (a.agents or ",".join(old.get("agents") or ["claude"])).split(",") if x.strip()]
        agents = list(AGENTS) if agents == ["all"] else [x for x in AGENTS if x in agents]
        if not agents or (a.agents and len(agents) != len(set(a.agents.replace("all", ",".join(AGENTS)).split(",")))):
            sys.exit(f"install: --agents takes {', '.join(AGENTS)} or all")
        py = a.python_cmd or old.get("python") or load_json(target / ".claude/nn-training.json").get("python") \
            or legacy_python(target) or ("python" if os.name == "nt" else "python3")
        check_python(py)

        def run(p):
            install(p, a, agents, py, old)
    if not a.dry_run:
        run(Plan(target, True, old))  # once without writing: a file that stops the installer stops it before any change
    run(plan)

    width = max(len(k) for k, _, _ in plan.log) if plan.log else 6
    print(("DRY RUN - nothing written\n" if a.dry_run else "") + f"Target: {target}")
    for kind, rel, detail in plan.log:
        if kind != "same":
            print(f"  {kind:<{width}}  {rel}" + (f"  - {detail}" if detail else ""))
    same = sum(1 for k, _, _ in plan.log if k == "same")
    if same:
        print(f"  ({same} files already up to date)")
    if plan.replaced:
        print(f"Replaced although edited after install (or not from this kit), {len(plan.replaced)}: "
              + ", ".join(plan.replaced) + ". Re-apply your changes from the backup if you still need them.")
    if not a.dry_run and plan.backed_up:
        print(f"Backups of {plan.backed_up} changed file(s): {os.path.relpath(plan.backup_dir, target)}")
    if not a.dry_run and not a.uninstall:
        print(f"\nInstalled for: {', '.join(agents)} (interpreter: {py}). Next: restart the agent in this repository, "
              f"run `{exe_text(py)} .claude/skills/nn-training/scripts/expctl.py selftest`, then paste "
              f"KICKOFF_PROMPT.md (fill in the Project card first).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
