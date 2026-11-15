#!/usr/bin/env python3
"""Generated guard cases, judged by a live shell.

The guard's other tests ask about lines that somebody thought of. This one builds command lines from parts (what is
done, how the path is written, what the command is wrapped in), asks the guard about each, and gives every line that
the guard lets pass without a question to a real shell in a temporary project. A line that passed must not have
printed the sealed file's content, copied it into another file, or changed the frozen file. The shell is the judge,
so a form that the guard misreads shows up without anybody having thought of it.

Shells: bash (Git's bash on Windows), zsh where it is installed, PowerShell on Windows. The sample comes from a
fixed seed, so a run repeats. Another sample: python tests/test_guard_live.py SEED COUNT (lines of each kind).

Not generated, because the guard does not claim to stop it (docs/REFERENCE.md, "Notes and limits", names each with
the check that shows it afterwards): a path or a command that a program puts together while it runs, a script file
that the line only names, what a second line does with a link or a copy that an earlier line made, git commands
that replace the working tree as a whole (stash, a change of branch, pull, merge, rebase), an archive unpacked or
a download saved over a file, and formatters other than black, isort and ruff. Not judged: live runs, which need a
run to protect.
"""
import base64
import json
import os
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_kit as tk  # noqa: E402
import test_ports as tp  # noqa: E402

PY = sys.executable.replace("\\", "/")
FAILS, SHOW = [], 15
SEALED, FROZEN = "data/test/labels.csv", "eval/metrics.py"
# a second frozen file, which main() adds: the first one's name holds two words that the guard takes for a runner of
# code (eval, py), so a line that names it is read as code, and what the guard misses in a plain line stayed unseen
FROZEN2 = "scoring/rules.txt"
CANARY = "kq7vzcanary3x"
SEALED_BYTES = ("%s\n%s,1\n" % (CANARY, CANARY)).encode()
# the canary as a line may show it: as it is, reversed, in hex, or inside the base64 of the whole file
SHOWN = [CANARY, CANARY[::-1], CANARY.encode().hex(), base64.b64encode(SEALED_BYTES).decode().rstrip("=")]


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def shows(text):
    flat = "".join(text.split())
    return any(v in flat for v in SHOWN)


# ---- bash and zsh: the parts ----------------------------------------------------------------------------------------
# {p} is the path as one shell word
READ = ["cat {p}", "head -n 5 {p}", "tail -n 5 {p}", "nl {p}", "sort {p}", "uniq {p}", "cut -c1-80 {p}", "sed -n p {p}",
        "sed '' {p}", "awk '{{print}}' {p}", "awk 1 {p}", "grep -h . {p}", "grep -v zzzz {p}", "paste {p}", "rev {p}",
        "base64 {p}", "xxd -p {p}", "tac {p}", "fold {p}", "expand {p}", "strings {p}", "more {p}", "less {p}",
        "cat < {p}", "< {p} cat", "cat {p} | cat", "cat <(cat {p})", "tee /dev/null < {p}", "dd if={p} 2>/dev/null",
        "while read -r l; do echo \"$l\"; done < {p}", "read -r a < {p}; echo \"$a\"", "mapfile -t a < {p}; echo \"${{a[@]}}\"",
        "exec 3< {p}; cat <&3", "echo \"$(cat {p})\"", "echo \"$(< {p})\"", "echo `cat {p}`", "x=$(cat {p}); echo \"$x\"",
        "printf '%s\\n' \"$(head -n 1 {p})\"", "cp {p} sub/copy.txt", "cp {p} /dev/stdout", "mv {p} sub/moved.txt",
        "ln {p} sub/hard.txt && cat sub/hard.txt", "source {p}", ". {p}", "bash {p}", "sh {p}", "diff {p} /dev/null",
        "tar cf - {p} | tar xOf -", "git diff --no-index /dev/null {p}", "git hash-object -w {p} | xargs git cat-file -p",
        "xargs cat <<< {p}", "echo {p} | xargs cat", "find {p} -exec cat {{}} \\;", "find {p} -type f | xargs cat",
        "env cat {p}", "nice cat {p}", "timeout 10 cat {p}", "command cat {p}", "exec cat {p}", "nohup cat {p}",
        "LC_ALL=C cat {p}", "busybox cat {p}", "stdbuf -o0 cat {p}", "xargs -a {p} echo", "wc -l {p}", "ls -l {p}",
        "< {p}"]  # zsh prints the file for this line
WRITE = ["echo x > {p}", "echo x >> {p}", "echo x >| {p}", ": > {p}", "> {p}", "cat sub/hello.py > {p}", "echo x 1> {p}",
         "echo x &> {p}", "echo x 2> {p}", "echo x >& {p}", "echo x | tee {p}", "echo x | tee -a {p} > /dev/null",
         "exec 3> {p}; echo x >&3", "cp sub/hello.py {p}", "cp -f train.py {p}", "mv sub/hello.py {p}",
         "install -m 644 train.py {p}", "ln -f train.py {p}", "ln -sf \"$PWD/train.py\" {p}", "sed -i s/acc/bcc/ {p}",
         "sed -i.bak s/acc/bcc/ {p}", "sed --in-place s/acc/bcc/ {p}", "perl -pi -e s/acc/bcc/ {p}", "truncate -s 0 {p}",
         "dd if=train.py of={p} 2>/dev/null", "cat train.py | dd of={p} 2>/dev/null", "rm {p}", "rm -f {p}", "unlink {p}",
         "git checkout -- {p}", "git checkout HEAD {p}", "git restore {p}", "git rm -qf {p}", "git mv {p} sub/m.py",
         "mv {p} sub/moved.py", "env cp train.py {p}", "nice rm {p}", "timeout 10 cp train.py {p}", "command rm {p}",
         "echo {p} | xargs rm", "find {p} -delete", "find {p} -exec rm {{}} \\;", "xargs rm <<< {p}", "touch {p}",
         # an option in another place or in a group of letters, and a program by its name in capitals, which a file
         # system without case finds (Windows, a Mac as it comes)
         "perl -p -i -e s/acc/bcc/ {p}", "sort -uo {p} {p} train.py", "curl -sSLo {p} \"file://$PWD/train.py\"",
         "RM -f {p}", "CP train.py {p}", "SED -i s/acc/bcc/ {p}", "c=rm; $c {p}"]
# {s} is the path as a Python expression
PYREAD = ["print(open({s}).read())", "print(pathlib.Path({s}).read_text())", "shutil.copy({s}, 'sub/copy.txt')",
          "print(os.read(os.open({s}, 0), 999))", "print(list(open({s})))", "print(io.open({s}).read())",
          "shutil.copyfile({s}, 'sub/copy.txt')", "print(pathlib.Path({s}).read_bytes())", "os.replace({s}, 'sub/m.txt')",
          "f = open({s}); print(f.readline())", "print(subprocess.run(['cat', {s}], capture_output=True).stdout)"]
PYWRITE = ["open({s}, 'w').write('x')", "open({s}, 'a').write('x')", "pathlib.Path({s}).write_text('x')", "os.remove({s})",
           "os.unlink({s})", "shutil.copy('train.py', {s})", "shutil.move('sub/hello.py', {s})",
           "os.replace('sub/hello.py', {s})", "os.rename({s}, 'sub/m.py')", "os.truncate({s}, 0)",
           "pathlib.Path({s}).unlink()", "pathlib.Path('sub/hello.py').replace({s})", "open({s}, 'r+').truncate(0)",
           "pathlib.Path({s}).open('w').write('x')", "io.open({s}, 'w').close()", "shutil.copyfile('train.py', {s})"]
# lines that name the folder above the file, or nothing at all
READ_WIDE = ["cat data/*/*", "cat */*/*.csv", "head -n 3 data/*/labels.csv", "cat d*/t*/l*", "grep -r . data",
             "grep -rh '' data", "grep -r . .", "grep -R --include='*.csv' . .", "find data -type f -exec cat {} \\;",
             "find data -type f -exec cat {} +", "find . -name 'lab*' -exec cat {} \\;", "find data -type f | xargs cat",
             "find data -type f -print0 | xargs -0 cat", "find . -name '*.csv' | xargs head", "tar cf - data | tar xOf -",
             "cp -r data sub/d", "cp -r data/test sub/t", "ls data/test | xargs -I{} cat data/test/{}",
             "for f in data/*/*; do cat \"$f\"; done", "for f in data/test/*; do cat $f; done", "cat $(find data -type f)",
             "cat `ls -d data/*/*`", "git add -f . && git diff --cached", "git add -f data && git diff --cached -- data",
             "git grep --no-index . -- data", "git grep --no-index -h ''", "git ls-files -o | xargs cat",
             "git ls-files -oi --exclude-standard | xargs cat", "tar czf sub/d.tgz data && tar xOzf sub/d.tgz",
             "cd data && cat */*", "cd data && grep -r . .", "cd data/test && cat *", "cd data/test && cat ./*.csv",
             "cat data/test/*", "cat data/test/l*", "head data/tes?/*", "cat **/labels.csv", "cat data/**/labels.csv",
             "cat **/*.csv", "rsync -a data/ sub/d/", "diff -r data /dev/null", "cat data/*/* | head", "wc -l data/*/*",
             "diff -rN sub data", "git diff --no-index sub data"]
WRITE_WIDE = ["rm -r eval", "rm -rf eval/*", "mv eval eval2", "find eval -name '*.py' -delete",
              "find eval -type f -exec rm {} \\;", "find . -name 'metrics*' -delete", "sed -i s/acc/bcc/ eval/*.py",
              "git checkout .", "git checkout -- .", "git restore .", "git checkout HEAD .", "git reset --hard",
              "git reset --hard HEAD", "git checkout HEAD -- eval", "cd eval && echo x > metrics.py",
              "cd eval && rm *", "cd eval; sed -i s/acc/bcc/ *.py", "for f in eval/*; do echo x > \"$f\"; done",
              "for f in eval/*.py; do rm $f; done", "ls eval/*.py | xargs rm", "find eval -type f | xargs rm",
              "cp train.py eval/metrics.py", "echo x | tee eval/*.py", "truncate -s 0 eval/*", "git rm -rqf eval",
              "git mv eval eval2", "rsync -a sub/ eval/ --delete", "perl -pi -e s/acc/bcc/ eval/*",
              "git checkout -q .", "git checkout ./", "git checkout HEAD '*.py'", "git checkout HEAD :/", "git checkout --force",
              "grep -rl acc eval | while read -r f; do sed -i s/acc/bcc/ \"$f\"; done",
              "git ls-files '*.py' | while read f; do echo x > \"$f\"; done", "find . -name 'metrics*' -exec cp train.py {} \\;"]
# a command, wrapped: {c} is the command, {q} the command as one quoted word, {s} the same with a semicolon in front,
# {y} a Python program that hands the command to the system's shell
WRAPS = ["bash -ce {q}", "sh -xc {q}", "bash -c -- {q}", "bash -c -o pipefail {q}", "eval true {s}", "trap -- {q} EXIT",
         "c={q}; d=$c; $d", "echo \"$(echo ')' > /dev/null; {c})\"", "echo \"$(cat <<'EOF'\nmsg\nEOF\n{c})\"",
         '"%s" -c {y}' % PY,
         "({c})", "{{ {c}; }}", "true && {c}", "false || {c}", "{c}; true", "if true; then {c}; fi",
         "for i in 1; do {c}; done", "echo start; {c}", "true\n{c}", "{c} &\nwait", "f() {{ {c}; }}; f", "! {c}",
         "bash -c {q}", "sh -c {q}", "eval {q}", "bash <<< {q}", "echo {q} | bash", "echo {q} | sh", "printf %s {q} | bash -s",
         "bash <<'EOF'\n{c}\nEOF", "trap {q} EXIT", "env -i PATH=\"$PATH\" bash -c {q}", "timeout 10 bash -c {q}",
         "nice bash -c {q}", "nohup bash -c {q}", "exec bash -c {q}", "xargs -0 bash -c <<< {q}", "time {c}",
         "X=1 bash -c {q}", "command eval {q}", "builtin eval {q}", "bash -c {q} 2>&1 | cat", "$(echo bash) -c {q}",
         "c={q}; $c", "c={q}; eval \"$c\"", "c={q}; ${{=c}}"]  # the last one is zsh's way to split a text into words


def spellings(path, proj, zsh=False):
    """Ways to write one path so that a shell opens the same file. zsh: its own patterns as well."""
    d, name = path.rsplit("/", 1)
    last = d.rsplit("/", 1)[-1]
    out = [path, "./" + path, '"%s"' % path, "'%s'" % path, path.replace("/", "//", 1), "%s/./%s" % (d, name),
           "%s/../%s/%s" % (d, last, name), '"$PWD/%s"' % path, "$PWD/" + path, path[:3] + '""' + path[3:],
           path[:3] + "''" + path[3:], path[:2] + "\\" + path[2:], "$(echo %s)" % path, "`echo %s`" % path,
           "${NOTSET:-%s}" % path, path[:3] + "${@:-%s}" % path[3] + path[4:],
           "%s/*" % d, "%s/%s*" % (d, name[:3]), "%s/%s?%s" % (d, name[:2], name[3:]),
           "%s/[%s]%s" % (d, name[0], name[1:]), "%s/{%s,nothing}" % (d, name), d[:-1] + "?/" + name,
           d[:2] + "*/" + name, "*/" + path.split("/", 1)[1], "**/" + name, "%s/**/%s" % (d.split("/")[0], name),
           '"%s"' % (proj / path).as_posix(), "%s/%s" % (d, name.replace(".", "\\."))]
    if zsh:
        out += ["%s/(%s|nothing)" % (d, name), "%s/%s(.)" % (d, name), "%s/*(.)" % d, "**/%s(.)" % name,
                "%s/%s(N)" % (d, name), "%s/*(om[1])" % d, "%s(%s?)/%s" % (d[:len(d) - len(last)], last[:-1], name)]
    if (proj / path.upper()).exists():  # a file system that ignores case: Windows, and a Mac as it comes
        out += [path.upper(), "%s/%s" % (d.upper(), name), "%s/%s" % (d, name.capitalize())]
    if os.name == "nt":
        back = path.replace("/", "\\")
        out += ["'%s'" % back, back.replace("\\", "\\\\"), "'%s'" % str(proj / path), "%s./%s" % (d, name), path + ".",
                "/" + (proj / path).as_posix().replace(":", "", 1).lower()[0] + (proj / path).as_posix()[2:]]
    elif Path("/proc/self/cwd").exists():
        out += ["/proc/self/cwd/" + path, "/proc/$$/cwd/" + path, "/proc/self/root" + (proj / path).as_posix()]
    return out


def py_paths(path, proj):
    d, name = path.rsplit("/", 1)
    out = ["'%s'" % path, "'./%s'" % path, "'%s/./%s'" % (d, name), "'%s/' + '%s'" % (d, name),
           "os.path.join(%s)" % ", ".join("'%s'" % x for x in path.split("/")), "'%s/%%s' %% '%s'" % (d, name),
           "pathlib.Path('%s') / '%s'" % (d, name), "os.path.abspath('%s')" % path, "os.getcwd() + '/%s'" % path,
           "os.path.join(os.getcwd(), '%s')" % path, "'/'.join(['%s'])" % "', '".join(path.split("/")),
           "'%s'" % (proj / path).as_posix()]
    if (proj / path.upper()).exists():
        out += ["'%s'" % path.upper(), "'%s/%s'" % (d.upper(), name)]
    if os.name == "nt":
        out += ["r'%s'" % path.replace("/", "\\"), "'%s./%s'" % (d, name), "'%s.'" % path, "'%s '" % path]
    return out


def named(rng, verbs, pyverbs, path, proj, zsh=False):
    """One command on one path: a verb with the path spelled some way, or the path handed over some way."""
    d, name = path.rsplit("/", 1)
    roll = rng.random()
    if roll < 0.2:
        return '"%s" -c "import io, os, pathlib, shutil, subprocess; %s"' % (
            PY, rng.choice(pyverbs).format(s=rng.choice(py_paths(path, proj))))
    verb = rng.choice(verbs)
    if roll < 0.8:
        return verb.format(p=rng.choice(spellings(path, proj, zsh)))
    return rng.choice(["f=%s; %s" % (path, verb.format(p='"$f"')), "f=%s; %s" % (path, verb.format(p="$f")),
                       "d=%s; %s" % (d, verb.format(p='"$d/%s"' % name)), "d=%s; %s" % (d, verb.format(p="$d/" + name)),
                       "n=%s; %s" % (name, verb.format(p="%s/$n" % d)), "cd %s && %s" % (d, verb.format(p=name)),
                       "cd %s; %s" % (d, verb.format(p="./" + name)), "pushd %s > /dev/null && %s" % (d, verb.format(p=name)),
                       "(cd %s && %s)" % (d, verb.format(p=name)), "set -- %s; %s" % (path, verb.format(p='"$1"')),
                       "for f in %s; do %s; done" % (path, verb.format(p='"$f"')),
                       "export f=%s; bash -c %s" % (path, shlex.quote(verb.format(p='"$f"'))),
                       "a=(%s); %s" % (path, verb.format(p='"${a[0]}"')), "f=%s %s" % (path, "bash -c " + shlex.quote(verb.format(p='"$f"'))),
                       "cd %s && %s" % (d.split("/")[0], verb.format(p=path.split("/", 1)[1])),
                       "cd sub && %s" % verb.format(p="../" + path), "cd %s && cd .. && %s" % (d, verb.format(p=last_two(path)))])


def last_two(path):
    return "/".join(path.split("/")[-2:])


def wrapped(rng, c):
    for _ in range(rng.choice([0, 0, 0, 1, 1, 1, 1, 2])):
        c = rng.choice(WRAPS).format(c=c, q=shlex.quote(c), s=shlex.quote("; " + c),
                                     y=shlex.quote("import os; os.system(%r)" % c))
    return c


def bash_lines(rng, n, proj, zsh=False):
    out = []
    for _ in range(n):
        wide = rng.random() < 0.15
        out.append(("read", wrapped(rng, rng.choice(READ_WIDE) if wide else named(rng, READ, PYREAD, SEALED, proj, zsh))))
        out.append(("write", wrapped(rng, rng.choice(WRITE_WIDE) if wide else
                                     named(rng, WRITE, PYWRITE, rng.choice([FROZEN, FROZEN2]), proj, zsh))))
    for _ in range(n // 2):  # the same parts on files that nothing protects
        out.append(("free", wrapped(rng, named(rng, READ[:38], PYREAD[:2], rng.choice(["data/train.csv", "sub/hello.py"]), proj))))
        out.append(("free", wrapped(rng, named(rng, WRITE[:12], PYWRITE[:3], "sub/out.txt", proj))))
    return out


# ---- PowerShell: the parts ------------------------------------------------------------------------------------------
PS_READ = ["Get-Content {p}", "gc {p}", "cat {p}", "type {p}", "Get-Content -Path {p} -Raw", "Get-Content -LiteralPath {p}",
           "gc {p} | Select-Object -First 3", "Select-String -Pattern . -Path {p}", "sls . {p}", "Import-Csv {p}",
           "Import-Csv {p} | Format-List", "[IO.File]::ReadAllText((Resolve-Path {p}))", "[IO.File]::ReadAllLines((Convert-Path {p}))",
           "Copy-Item {p} sub\\copy.txt", "cp {p} sub\\copy.txt", "copy {p} sub\\copy.txt", "Move-Item {p} sub\\moved.txt",
           "Get-Item {p} | Get-Content", "gi {p} | gc", "Get-ChildItem {p} | Get-Content", "dir {p} | % {{ gc $_.FullName }}",
           "findstr . {p}", "Get-Content {p} | Out-String", "$x = Get-Content {p}; $x", "more {p}", "cmd /c type {p}",
           "certutil -encode {p} sub\\enc.txt", "Get-Content {p} -Encoding Byte", "Get-Content {p} -TotalCount 1",
           "Get-Content {p} -Tail 1", "[System.IO.File]::OpenText((Resolve-Path {p})).ReadToEnd()", "(Get-Content {p}).Length"]
PS_WRITE = ["Set-Content {p} x", "Set-Content -Path {p} -Value x", "sc {p} x", "Add-Content {p} x", "ac {p} x",
            "'x' | Out-File {p}", "'x' > {p}", "'x' >> {p}", "'x' | Set-Content {p}", "'x' | Tee-Object {p}", "'x' | tee {p}",
            "Clear-Content {p}", "clc {p}", "Remove-Item {p}", "del {p}", "rm {p}", "ri {p}", "erase {p}",
            "Copy-Item train.py {p}", "cp train.py {p} -Force", "copy train.py {p}", "Move-Item sub\\hello.py {p} -Force",
            "mv sub\\hello.py {p} -Force", "Rename-Item {p} m2.py", "ren {p} m2.py", "New-Item {p} -Force", "ni {p} -Force",
            "Out-File -FilePath {p} -InputObject x", "(Get-Content {p}) -replace 'acc', 'bcc' | Set-Content {p}",
            "cmd /c del {p}", "cmd /c copy /y train.py {p}", "cmd /c move /y sub\\hello.py {p}", "cmd /c ren {p} m2.py",
            "cmd /c \"echo x> {p}\"", "cmd /c \"type train.py > {p}\"", "git checkout -- {p}", "git restore {p}",
            "Set-Content -LiteralPath {p} -Value x", "Remove-Item -LiteralPath {p}", "Out-File -LiteralPath {p} -InputObject x",
            "(Get-Item {p}).Delete()", "RM {p}", "CP train.py {p}", "$c = 'del'; & $c {p}"]
PS_READ_WIDE = ["Get-ChildItem data -Recurse -File | Get-Content", "gci -r data -File | gc", "Get-Content data\\*\\*",
                "gc data\\*\\labels.csv", "Select-String -Path data\\*\\* -Pattern .", "gci -r -Filter *.csv | gc",
                "Get-ChildItem -Recurse -Include *.csv | Get-Content", "Copy-Item data sub\\d -Recurse",
                "cmd /c \"type data\\test\\*\"", "cmd /c \"for /r data %f in (*) do @type %f\"", "robocopy data sub\\d /s",
                "xcopy /s /i /q data sub\\d", "tar -cf - data | tar -xOf -", "findstr /s . data\\*",
                "cd data; gc test\\labels.csv", "Set-Location data\\test; Get-Content labels.csv", "pushd data; gc */*",
                "sl data\\test; cat *", "gci data\\test | % {{ gc $_.FullName }}", "dir -r *.csv | gc",
                "gci -r | ? {{ $_.Name -like 'lab*' }} | gc", "Get-Content (gci data\\test)[0].FullName"]
PS_WRITE_WIDE = ["Remove-Item eval -Recurse -Force", "Remove-Item eval\\* -Force", "del eval\\*.py", "Move-Item eval eval2",
                 "Rename-Item eval eval2", "Get-ChildItem eval | Remove-Item", "gci eval -File | % {{ Set-Content $_.FullName x }}",
                 "git checkout .", "git reset --hard", "git restore .", "cd eval; Set-Content metrics.py x",
                 "Set-Location eval; del *", "cmd /c \"del /q eval\\*\"", "cmd /c rmdir /s /q eval", "sl eval; 'x' > metrics.py",
                 "gci -r -Filter metrics.py | Remove-Item", "dir eval\\*.py | Clear-Content", "Rmdir eval -Recurse -Force",
                 "gci -r -Filter *.py | % {{ $t = gc $_.FullName -Raw; Set-Content $_.FullName ($t -replace 'acc','bcc') }}",
                 "foreach ($f in Get-ChildItem -Recurse -Filter metrics.py) {{ Set-Content $f.FullName 'x' }}"]
PS_WRAPS = ["& {{ {c} }}", ". {{ {c} }}", "if ($true) {{ {c} }}", "foreach ($i in 1) {{ {c} }}", "1 | % {{ {c} }}",
            "try {{ {c} }} catch {{}}", "$null = 1; {c}", "{c}; 'done'", "Write-Output start; {c}", "Invoke-Expression {q}",
            "iex {q}", "& ([scriptblock]::Create({q}))", "Invoke-Command -ScriptBlock {{ {c} }}", "icm {{ {c} }}",
            "function f {{ {c} }}; f", "&{{{c}}}", "powershell -NoProfile -Command {q}", "powershell -NoProfile -EncodedCommand {e}",
            "$c = {q}; iex $c", "{c} | Out-Host", "$(  {c}  )", "1..1 | ForEach-Object {{ {c} }}", "cmd /c powershell -NoProfile -Command {q}",
            "powershell -NoProfile -com {q}", "& ([Management.Automation.ScriptBlock]::Create({q}))",
            "$ExecutionContext.InvokeCommand.InvokeScript({q})"]


def ps_spellings(path, proj):
    back = path.replace("/", "\\")
    d, name = back.rsplit("\\", 1)
    full = str(proj / path)
    return [back, path, ".\\" + back, '"%s"' % back, "'%s'" % back, "%s\\*%s" % (d, name[-4:]), "%s\\%s?%s" % (d, name[:2], name[3:]),
            d[:-1] + "*\\" + name, "%s\\[%s]%s" % (d, name[0], name[1:]), back.upper(), back.title(), "%s\\.\\%s" % (d, name),
            "%s\\..\\%s\\%s" % (d, d.rsplit("\\", 1)[-1], name), back.replace("\\", "\\\\", 1), "%s.\\%s" % (d, name), back + ".",
            '"%s "' % back, "$PWD\\" + back, '"$PWD\\%s"' % back, "$pwd/" + path, "(Join-Path %s %s)" % (d, name),
            "('%s\\' + '%s')" % (d, name), back[:3] + "`" + back[3:], full, '"%s"' % full, "'%s'" % full.replace("\\", "/"),
            full[0].lower() + full[1:], "\\\\?\\" + full, "\\\\localhost\\%s$%s" % (full[0], full[2:]), "*\\" + back.split("\\", 1)[1],
            "$env:NOTSET%s" % back, '"${PWD}\\%s"' % back, "(Resolve-Path %s)" % back, "(gi %s).FullName" % back]


def ps_lines(rng, n, proj):
    def one(verbs, wide, path):
        c = rng.choice(wide) if rng.random() < 0.15 else rng.choice(verbs).format(p=rng.choice(ps_spellings(path, proj)))
        for _ in range(rng.choice([0, 0, 0, 1, 1, 1, 2])):
            enc = base64.b64encode(c.encode("utf-16-le")).decode()
            c = rng.choice(PS_WRAPS).format(c=c, q="'%s'" % c.replace("'", "''"), e=enc)
        return c
    out = []
    for _ in range(n):
        out += [("read", one(PS_READ, PS_READ_WIDE, SEALED)), ("write", one(PS_WRITE, PS_WRITE_WIDE, rng.choice([FROZEN, FROZEN2])))]
    for _ in range(n // 2):
        out += [("free", one(PS_READ[:13], ["gci sub"], rng.choice(["data/train.csv", "sub/hello.py"]))),
                ("free", one(PS_WRITE[:11], ["gci sub"], "sub/out.txt"))]
    return out


# ---- the guard's answer and the shell's ------------------------------------------------------------------------------
def answer(proj, tool, line):
    r = tk.sh([sys.executable, str(proj / ".claude/hooks/nn_guard.py")], cwd=proj,
              env={"CLAUDE_PROJECT_DIR": str(proj), "RIPGREP_CONFIG_PATH": ""},
              inp=json.dumps({"tool_name": tool, "tool_input": {"command": line}, "cwd": str(proj), "session_id": "t"}))
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else None


def raw(p):
    """The path as the file system has it. Windows cuts a dot or a blank off the end of a name unless the path
    starts like this, and Git's bash makes such names (echo x > out.txt.)."""
    return "\\\\?\\" + str(p) if os.name == "nt" else str(p)


def files(proj):
    """Every file outside git's folder and the kit's, with its content; a link counts by where it points."""
    out, top = {}, raw(proj)
    for d, dirs, names in os.walk(top):
        if d == top:
            dirs[:] = [x for x in dirs if x not in (".git", ".claude")]
        for n in names + [x for x in dirs if os.path.islink(os.path.join(d, x))]:
            p = os.path.join(d, n)
            rel = p[len(top) + 1:].replace(os.sep, "/")
            try:
                if os.path.islink(p):
                    out[rel] = b"link " + os.fsencode(os.readlink(p))
                else:
                    with open(p, "rb") as f:
                        out[rel] = f.read(1 << 20)
            except OSError:
                out[rel] = b"unreadable"
    return out


def put_back(proj, before):
    for n in os.listdir(raw(proj)):
        if n not in (".git", ".claude"):
            p = os.path.join(raw(proj), n)
            shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.unlink(p)
    for rel, data in before.items():
        (proj / rel).parent.mkdir(parents=True, exist_ok=True)
        (proj / rel).write_bytes(data)
    subprocess.run(["git", "reset", "-q"], cwd=proj, capture_output=True)


def judge(proj, before, argv, line):
    """Run one line. What it did that the guard is there to stop: a list, empty when it did none of it."""
    try:
        r = subprocess.run(argv + [line], cwd=proj, capture_output=True, stdin=subprocess.DEVNULL, timeout=30,
                           env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"})
        said = r.stdout + r.stderr
    except subprocess.TimeoutExpired as e:
        said = (e.stdout or b"") + (e.stderr or b"")
    now, did = files(proj), []
    if shows(said.decode("utf-8", "replace")) or shows(said.decode("utf-16-le", "replace")):
        did.append("printed the sealed file")
    if any(rel != SEALED and data != before.get(rel) and shows(data.decode("latin-1")) for rel, data in now.items()):
        did.append("copied the sealed file")
    if any(now.get(f) != before[f] for f in (FROZEN, FROZEN2)):
        did.append("changed the frozen file")
    if now != before:
        put_back(proj, before)
    return did


def main():
    seed, n = (int(x) for x in (sys.argv[1:3] + ["7", "150"][len(sys.argv) - 1:])[:2])
    global SHOW
    SHOW = 15 if len(sys.argv) < 4 else int(sys.argv[3])  # a third argument: how many of the lines to print
    tmp = Path(tempfile.mkdtemp(prefix="nnlive-"))
    proj = tk.setup(tmp)
    (proj / SEALED).write_bytes(SEALED_BYTES)
    cfgp = proj / ".claude/nn-training.json"  # the second frozen file: in git, and changed since, as the first one is
    cfgp.write_text(json.dumps(dict(json.loads(cfgp.read_text()), frozen_paths=[FROZEN, FROZEN2]), indent=1))
    (proj / FROZEN2).parent.mkdir()
    (proj / FROZEN2).write_bytes(b"the higher val/acc wins\n")
    for c in (["git", "add", "-A"], ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "rules"]):
        subprocess.run(c, cwd=proj, check=True)
    (proj / FROZEN2).write_bytes(b"the higher val/acc wins\na tie goes to the lower loss\n")
    before = files(proj)
    shells = [(name, argv) for name, argv in tp.shells() if name in ("bash", "Git Bash", "pwsh", "powershell")]
    if shutil.which("zsh"):
        shells.append(("zsh", ["zsh", "-f", "-c"]))

    def version(name, argv):  # which shell judged: a record of a run names it (macOS has bash 3.2, Linux bash 5)
        ask = "$PSVersionTable.PSVersion.ToString()" if name in ("pwsh", "powershell") else "echo $BASH_VERSION$ZSH_VERSION"
        try:
            return subprocess.run(argv + [ask], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                  timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    print("project:", proj, "seed", seed, "shells:", ", ".join(f"{name} {version(name, argv)}".strip() for name, argv in shells))
    for name, argv in shells:
        ps = name in ("pwsh", "powershell")
        if ps and os.name != "nt":
            continue
        tool = "PowerShell" if ps else "Bash"
        # the judge first: two lines that do the harm, given to the shell without asking the guard
        harm = [judge(proj, before, argv, x) for x in (("Get-Content %s" % SEALED, "Set-Content %s x" % FROZEN) if ps else
                                                       ("cat %s" % SEALED, "echo x > %s" % FROZEN))]
        check(harm == [["printed the sealed file"], ["changed the frozen file"]] and files(proj) == before,
              f"{name}: the judge sees a line that prints the sealed file and one that changes the frozen file, and the "
              f"project is as it was afterwards ({harm})")
        if ps:
            lines = ps_lines(random.Random(seed), max(n // 2, 1), proj)
        else:  # for zsh the same lines with zsh as the nested shell, and its own patterns among the spellings
            lines = [(kind, line.replace("bash", "zsh") if name == "zsh" else line)
                     for kind, line in bash_lines(random.Random(seed), n, proj, name == "zsh")]
        with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
            answers = list(pool.map(lambda kl: answer(proj, tool, kl[1]), lines))
        passed = [(kind, line) for (kind, line), a in zip(lines, answers) if a is None]
        missed = [(line, did) for kind, line in passed for did in [judge(proj, before, argv, line)] if did]
        for line, did in missed[:SHOW]:
            print("  MISS (%s): %s" % (", ".join(did), line.replace("\n", "\\n")))
        free = [a for (kind, _), a in zip(lines, answers) if kind == "free"]
        check(not missed, f"{name}: of {len(lines)} generated lines the guard let {len(passed)} pass, and none of them "
              f"printed or copied the sealed file or changed the frozen file ({len(missed)} did)")
        check(free.count(None) * 10 >= len(free) * 9, f"{name}: the same parts on files that nothing protects pass "
              f"without a question, nine in ten at least ({free.count(None)} of {len(free)})")  # was: half of them
    shutil.rmtree(tmp, ignore_errors=True)
    print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILURES")
    for f in FAILS:
        print("  -", f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
