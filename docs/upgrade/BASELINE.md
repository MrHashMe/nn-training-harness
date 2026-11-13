# Baseline test results (23 October kit, commit 5ea9659)

Run on 10 November 2026, before any change, against a clone of the baseline commit. "Clean" environments are
uv-created virtual environments with no third-party packages, so they exercise the standard-library-only paths
(the default interpreters have psutil and torch installed, and expctl prefers psutil whenever it imports).

| Platform | Environment | test_kit | test_review_fixes | test_runlog_units |
|---|---|---|---|---|
| WSL2 Ubuntu 24.04 | default `python3` 3.12.3, psutil 5.9.8 | 88 pass | 38 pass | 13 pass |
| WSL2 Ubuntu 24.04 | clean 3.12.12, no psutil | 88 pass | 38 pass | 13 pass |
| WSL2 Ubuntu 24.04 | clean 3.8.20, no psutil | 88 pass | 38 pass | 13 pass |
| Windows 11 | default `python` 3.11.7, psutil 7.2.2 | 5 pass, 1 fail, then abort | abort, 0 checks | 13 pass |
| Windows 11 | clean 3.11.7, no psutil | 5 pass, 1 fail, then abort | abort, 0 checks | 13 pass |
| Windows 11 | clean 3.8.20, no psutil | 5 pass, 1 fail, then abort | abort, 0 checks | 13 pass |

So on Linux (WSL) all 139 checks pass in every environment, including the claimed minimum Python 3.8.

On native Windows only the 13 logger unit checks and the first 5 controller checks (empty status, hash, env) pass.
Both other files stop at their first `expctl launch`:

- `test_kit.py`: `FAIL launch ok-run returns pid`, then `KeyError: 'run_id'` at line 163.
- `test_review_fixes.py`: `KeyError: 'run_id'` at line 105, before any check.

Cause: `expctl launch` defaults to a copy snapshot that links git-ignored paths with symbolic links, and this
Windows account cannot create them (no Developer Mode, no SeCreateSymbolicLinkPrivilege), so launch exits with
code 6. The tests never reach their later POSIX-only parts (tmux, SIGKILL, process groups), which would fail too.

Also seen on Windows: git in the temporary test projects warns "LF will be replaced by CRLF" for every kit file,
because system git has `core.autocrlf=true` and the kit's files use LF.

Any later failure of a check that passes in this table is caused by the upgrade.

How to rerun (scripts live outside the repository, in the temporary work folder named in PROGRESS.md):
`wsl-tests.sh <label> <commit>` and `win-tests.sh <label> <commit>`; logs are written beside them under `logs/`.
