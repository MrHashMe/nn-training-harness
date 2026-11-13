# Independent review: findings and fixes (23 Oct 2026)

A separate reviewer agent (no access to the build history) audited the kit against the Claude Code docs and
probed it in temporary repositories. All 24 findings were fixed; each fix has a regression test in
`tests/test_review_fixes.py` unless noted.

| # | Severity | Finding | Fix |
|---|---|---|---|
| 1 | critical | kill / scancel / GPU reset only guarded while harness runs were live, so jobs outside the harness were unprotected | kill-type commands always ask; `external_jobs` in the config also guards dependency changes |
| 2 | critical | an unparseable `nn-training.json` or a guard exception silently disabled the guard | both now make the guard ask before every non-read action (reads stay allowed so the file can be fixed) |
| 3 | critical | `launch --seed` was recorded but never reached the run | `EXP_SEED` exported; RunLog records it; status alerts on a mismatch; docs pass the seed to the trainer too |
| 4 | major | one corrupt run directory crashed status, the session hook and the guard's live-run checks | per-run error isolation and type checks; the run shows as `unknown` with an alert |
| 5 | major | a launched study runner looked stalled while its trials logged to sibling directories | trials write `study_heartbeat.json` into the runner's directory |
| 6 | major | resuming in place left the old `result.json`, so a live run showed as completed | RunLog archives old result/exit records; a fresh heartbeat's pid establishes liveness |
| 7 | major | `--via tmux` passed only a whitelist of environment variables | full environment via a private 0600 file the supervisor reads and deletes |
| 8 | major | git submodules and editable installs broke snapshot immutability | submodule files included; the snapshot is first on `PYTHONPATH` (submodules not tested here) |
| 9 | major | sealed files reachable through run snapshots and `.claude/worktrees` copies; `~` patterns never matched | paths mapped back to repository paths, `~` expanded, sealed data left out of snapshots |
| 10 | major | shell paths ignored the session's working directory (`cd data; cat test/x`) | arguments resolved against the payload `cwd` |
| 11 | major | false positives: quoted `--note` text counted as writes; glob fragments denied unrelated commands | quoted text stripped for write detection; anchored fragments; fuzzy matches ask instead of deny |
| 12 | major | `git -C . push --force`, `git checkout HEAD -- f`, `tmux send-keys C-c`, `fuser -k`, `conda env update`, syncing `uv run` slipped through | git global options normalised; patterns extended; any `git push` asks |
| 13 | major | shell writes into a live run directory were not guarded | asks when a write command names an active run's directory |
| 14 | major | every DDP rank wrote the same run files | RunLog writes on global rank 0 only; docs show the all-reduced stop flag (unit test) |
| 15 | major | graceful stop signalled the whole process group, killing DataLoader workers first | SIGTERM goes to the trainer only; the group gets SIGKILL only on escalation |
| 16 | major | journal edits and Optuna DB writes changed the source hash; relative study storage pointed into snapshots | harness and bookkeeping files excluded from provenance; `EXP_PROJECT_ROOT` exported and documented |
| 17 | major | guard "ask" is meaningless under bypassPermissions | under bypassPermissions every "ask" becomes "deny" |
| 18 | minor | launch reported ok for commands that could not start; `stop --wait` could report `lost`; no per-stop kill grace; tmux names with dots | start errors reported; waits for the exit record; `stop --kill-after`; names sanitised |
| 19 | minor | numpy step values crashed `log()`; the primary metric could drop out of the heartbeat | steps coerced, JSON default added, metric always kept (unit tests) |
| 20 | minor | docs: Monitor's default 5-minute timeout, no `expctl resume`, "ten" rules, final-eval matched as a substring | docs corrected; final-eval command must match exactly with nothing chained after it |
| 21 | minor | unsupported or loose claims in references (`hf skills add a b c`, MLflow toolsets, tuning-playbook trial counts, `MaxTrialsCallback` states, partial trials scored as complete) | corrected; deadline-cut trials now fail with a reason and stop the study |
| 22 | minor | kickoff prompt: hooks unverifiable, Phase 0 vs journal, reports without "continue", Optuna mandated over an existing controller | `expctl selftest`; wording fixed |
| 23 | minor | no allow rules for read-only commands; Hugging Face MCP spend tools unguarded; "read-only" subagents could launch runs | allow rules for read-only `expctl`; ask rules for HF Jobs/repo/Space/sandbox tools; read-only hook in subagent frontmatter |
| 24 | minor | Windows interpreter paths broke the installer; status line counted dead runs as stalled; regex cost on huge commands; harness paths incomplete | quoting fixed; pid check; bounded patterns; skill, agents, CLAUDE.md and `.mcp.json` protected |

Note: the reviewer said `trackio skills add --claude` appeared nowhere; it exists in Trackio's CLI source
(`trackio/cli.py`, `skills add` with `--claude`), checked before publishing.
