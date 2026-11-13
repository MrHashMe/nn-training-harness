#!/usr/bin/env python3
"""Stand-in for `ssh HOST` in tests/test_remote.py: runs the one command line it is given on this machine, with the
small environment a fresh login on another machine would have (nothing else of the caller's environment arrives).

$FAKE_SSH_LOG names a file that receives every command line; while the file $FAKE_SSH_DOWN names exists, the
"machine" refuses connections."""
import os
import shlex
import subprocess
import sys

KEEP = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "PATHEXT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG")


def main():
    line = sys.argv[1]
    if os.environ.get("FAKE_SSH_LOG"):
        with open(os.environ["FAKE_SSH_LOG"], "a", encoding="utf-8") as f:
            f.write(line + "\n")
    if os.path.exists(os.environ.get("FAKE_SSH_DOWN") or os.devnull + "-none"):
        sys.stderr.write("ssh: connect to host box port 22: Connection refused\n")
        return 255
    return subprocess.run(shlex.split(line), env={k: os.environ[k] for k in KEEP if k in os.environ}).returncode


if __name__ == "__main__":
    sys.exit(main())
