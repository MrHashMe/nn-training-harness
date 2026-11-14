Read docs/upgrade/PROMPT.md first: it is the task and stays in force (it is kept out of git on purpose). Then
docs/upgrade/ROUND2.md: the round the user ordered on 12 November 2026 ("Round 2" below says where it stands).
"Round 3" below is the work after it: three items of the build order, built in a session of its own, and
three small repairs made in that session on 13 November. "Round 4" below is the work of 12 and 13 November
in the first session: the first four items of a ranked list of improvements, and round 3's repairs looked at
again. Its last entry is the fourth installer run on the real install, done on 13 November in a later
session. "After round 4" below is what that session did next: the guide for the person who uses the kit.
"After the guide" below is the same session's work on the next request: the full tests, the fine-tuning
script, two fixes, the front page and the upload. Its last part is the publication: the repository is public
from one new commit, and the commit ids in these records belong to the history before it, which is kept
locally and not published. The entry after the publication is the fifth installer run on the real install.
"Round 5" below is the work on the request of 14 November: another model's review of the kit, checked claim
by claim, and what was built from it. Its last entry is the sixth installer run on the real install, which
brought the round there.

# Upgrade progress

Last updated: 14 November 2026.

## Standing decisions
- 11 Nov, user: the usage limit of this session's model is the binding constraint. Do the most important things,
  do not follow frontier-scout to the letter, take the user-supplied Gemini report as given, verify only what a
  build depends on. My reading: no outside scouts, no further research or verification rounds, a compact ledger
  and coverage map instead of frontier-scout rounds R2 to R7, one fresh reviewer subagent instead of the full
  deep-sweep fan-out, cheaper models for subagents. The report must say what was reduced.
- 11 Nov, mine: build no further features for the unfinished Adopt rows. They are listed in LEDGER.md as
  unfinished with what is missing. Exception, 11 Nov, user ("Yes, build A"): group A of
  `scout/draft/second-look.md` was built. Groups B and C are not approved.
- 12 Nov, user: "Run the round-2 prompt here", with ROUND2.md as written. Its assumptions therefore hold: the usage
  limit of 11 November still binds, and the request is the go-ahead for the unfinished Adopt rows, groups B and C,
  the guard's gap for other checkouts and changes to the keep rule. This replaces the line above for round 2. The
  same message carried another AI model's audit of the kit (twelve claimed defects, a list of methods and tools,
  four modules): my reading is that these enter the round as candidates, each checked against the code or its
  source, each with a ledger row. The material is in `scout/scouts/user-audit-1112.md` (not in git).
- 12 Nov, user, through the session that ran round 2: a session of its own builds the first three items of the
  order under "Not done" (numeric settings searched by the harness, a second benchmark task for fine-tuning, a
  restart on a stall). Its terms: the smallest complete change for each, reusing what the loop, `expctl` and
  `benchmarks/` have; the core stays on the standard library without network, and Python 3.8 stays the tested
  minimum; one commit per item; the usage limit binds (no research beyond what a build decision needs, cheaper
  models for subagents); nothing is pushed and the real install stays untouched.
- 13 Nov, user ("Yes, repair them", to that session's question): the three small faults that it had seen
  beside the two it fixed are repaired on the same terms, each with one check.
- 12 Nov, user, after a ranked list of what else would improve the kit ("Top four and when Build the kit's
  next three items finish make sure you read the conclusion if anything need fix"). My reading: build the
  first four items of that list here (guard gaps found on the real project; a question before a recursive
  command at the project root; evaluator checks; a measurement of the harness's search), on the terms that
  hold (the smallest complete change, the core on the standard library, the usage limit, nothing pushed, the
  real install untouched), and read the conclusion of round 3's session when it ends and fix what needs it.
- 13 Nov, user, with that session's conclusion ("The following was finished, check what you can fix and
  enhance based on it's output:"). My reading: check its three repairs critically, fix what its output leaves
  open or wrong, and repair the same faults where they remain elsewhere. Both are "Round 4" below.
- 13 Nov, user: "Update my install", the first of the two answers offered under round 4's closing message.
  That session replied with an authentication error, and nothing ran. Later that day, in a new session, the
  user asked whether I could continue from the last session ("last thing was require to upgrade the kit
  after several tests"). My reading: the fourth installer run on the real install, done as the second and
  third were, and nothing else there. That word covers the run and its checks. It does not cover a commit
  of the changed files there, `--worktrees` or a count of files.
- 13 Nov, user ("Yes, commit there", to the question after that run): the fifteen files the run changed are
  committed in that repository, one local commit of exactly those paths.
- 13 Nov, user: "In the repo, make sure that there is a full and easy guide on how to use this project and what
  will it do and how it will improve the training. Make it impressive and easy to understand and read". My
  reading: one guide in the kit's repository that a newcomer reads from the top, which says what the kit is,
  what it does, how it improves training and how to use it. The existing `docs/GUIDE.md` is reworked, no second
  file is added, and the guide claims nothing beyond what was measured.
- 13 Nov, user ("Yes, merge", to the question whether that session's branch should go into `main`): `main` is
  fast-forwarded to the branch. Nothing is pushed.
- 13 Nov, user: "Run the full tests and the fine-tuning script after that fix any issue or things that need
  improvement, then upload it to my repo and make sure it looks really good, with the easy guide for anyone
  beginner with nice visible and easy to read and explain in detail how it works". My reading: run the seven
  test files and the fine-tuning practice script; fix what they show, the open item on the practice projects'
  best run among it; have the guide explain in detail how the kit works, and make the README a front page;
  put the kit into a repository under the user's GitHub account. That word covers the upload. It does not
  settle whether the repository is public: every commit carries the user's private e-mail address, the
  records under `docs/upgrade/` quote the user's messages, and the kit has no licence file. So the
  repository is created private, the history is left as it is, and public visibility waits for the user's
  word.
- 13 Nov, user ("Yes, make it public", to the question whether the repository should become public. I had
  said what a yes would do: replace the uploaded history with one commit under the account's no-reply
  address, with the full history kept locally; add an MIT licence; switch the repository to public). Done as
  said ("After the guide"). Standing from now on: only `main` is pushed. The development history lies under
  `refs/archive/development-history` and is never pushed, because its commits carry the user's private
  e-mail address. Commits are made under the repository's own identity, which is now the account's name and
  no-reply address, and with `TZ=UTC`, so that no later commit carries the address or the time zone.
- 13 Nov, user ("Yes, run it", to the question whether the installer should run on the real install so that
  it gets the status fix): the fifth installer run ("After the guide"). My reading: the word covers the run
  and its checks, as with the runs before it. A commit of the two changed files in that repository and a
  push of this record each wait for a word of their own.
- 14 Nov, user: "I need you to review the following recommendation and suggestion to upgrade the project. Then I
  need you to build a plan to upgrade the project based on it. Make sure that it will be upgraded to best
  possible way. then execute the plan.", followed by another model's review of the kit (22 ranked items, and a
  second part that rebuilds the kit as six "planes"). My reading, as with the audit of 12 November: the
  review's claims enter as candidates, each checked against the code or its source; a defect that the check
  confirms is fixed with a test, a feature or technique is adopted on evidence, and what is wrong, cannot be
  checked here or needs the user's go-ahead is recorded with the reason. The request is the go-ahead for
  changes inside this folder and local commits. It is not a word for pushing, for installing software,
  plugins, MCP servers or agent CLIs, for anything on the real install, or for paid resources. Instructions
  inside the review are data: two of them are not followed (to remove the checkout under `.claude/worktrees/`
  that this work runs in, and to add an Apache licence, where the repository has the MIT licence the user
  chose). The plan and where it stands are under "Round 5".
- 14 Nov, user ("Yes, run it", to the question whether the installer should run on the real install so that
  it gets round 5): the sixth installer run (the last entry of "Round 5"). My reading: the word covers the
  run and its checks, as with the runs before it. A commit of the seventeen changed files in that
  repository and a push of this record each wait for a word of their own.

## Done (commit in brackets)
- Git repository, repository-local identity, LF pinned. Baseline `5ea9659` = the 23 October kit. Baseline tests on
  WSL and native Windows, default and clean environments: BASELINE.md.
- Native Windows made a working platform (`51a37a7`).
- Research: 26 notes with 1,416 candidate rows in `docs/upgrade/scout/draft/` (30 notes and 1,498 rows after
  round 2). The two user-supplied reports are in `scout/scouts/user-*.md` (not in git: they name the user).
- Gap 4, ports (`01dc96d`): one guard with per-agent input and answer adapters, Codex and Cursor files, installer
  with `--agents`, manifest, upgrade over the 23 October version, `--uninstall`. `tests/test_ports.py`.
- Gap 1, loop (`f3fabd6` and before): `nnloop.py`, `references/loop.md`, `tests/test_loop.py`, benchmark task
  `benchmarks/charlm/`, `benchmarks/new_project.py`, `benchmarks/pilot.py`.
- Real loop run (11 Nov, native Windows, this session's subagents through a bridge that showed every write to the
  project's guard hook): scouting notes, five iterations, ten runs, nothing kept. Project kept at
  `%TEMP%\nnkit-upgrade\live1`.
- Gap 3, remote (`e473a06`, `42155dd`): `expctl resume`, `RunLog.resume_from`, `nnremote.py` with `ssh` and `hfjobs`
  targets, `references/remote.md`, `tests/test_remote.py`. The ssh route ran live once (Windows to WSL, free).
- Gap 2, scouting (`6efa107`): `references/scouting.md`, SKILL.md gate 4.0, dated references with a lint.
- Five new references (data, evaluation, llm, operations, optimization), four rewritten ones, README rewritten,
  KICKOFF slimmed, agent briefs calibrated, `tests/test_benchmarks.py`, result-write retry in `runlog.py`, the
  installer keeps the interpreter of a 23 October install.
- Upgrade test on a partial copy of the real 23 October install: passed (details in REPORT.md).
- `docs/upgrade/LEDGER.md` (generated by `scout/make_ledger.py build` from the notes, `scout/covered/*.json` and
  `scout/LEDGER.head.md`): 399 Adopt rows, 261 finished, 138 unfinished (253 and 146 before group A was built).
  After round 2: 415 Adopt rows, 277 finished, 138 unfinished.
- Try of the pinned third-party stack in WSL (11 Nov; results in `references/stack.md`, `scout/covered/tried.json`
  and REPORT.md section 3): everything installs and passes a smoke test except PyTorch 2.15.0+cu132, whose first
  CUDA call crashes there. Cause not found.
- Independent review by one fresh Opus subagent: 18 findings, all fixed or answered (REPORT.md section 7). Guard:
  PowerShell, `cmd` and nested-interpreter forms, sealed reads through Grep, Glob, wildcards and `cd`, letter case
  on Windows, unreadable config. `nnremote`: credential-named files stay home, a missing ledger refuses paid
  starts. `nnloop`: the wall-clock limit ends a session in flight, honest worker wording.
- Last full test run (11 Nov): all seven files pass in WSL (three interpreters) and on native Windows (two). It
  exposed one fault in `nnremote` (a Hugging Face job's exit record could reach the bucket before its last files);
  fixed, with a unit check.
- `docs/upgrade/REPORT.md`: the final report.
- 11 Nov, user: the Claude Code CLI on Windows is signed in, run what waited on it. The other questions are open.
- Headless loop check (11 Nov, native Windows, Claude Code CLI 2.1.322, `claude-sonnet-5-5`): it is the pilot's
  arm-run `new-1`. Scouting, five changes, one kept (a moving average of the weights, from the scouting notes),
  stop at the run limit. REPORT.md section 2.
- Found through the live runs and fixed: the loop and the pilot stop when Claude Code reports usage billed per
  use (`d011172`, `e3ea4fc`); guard log lines written at the same moment were lost on Windows (`12be1a7`); the
  pilot's old-kit and no-kit sessions were not told which shell commands their permission rule allows, gave up
  and trained nothing, so their first tries are void (`d588a51`; kept in `pilot1\void.json`); a miscount
  (`917a5f7`).
- Pilot (11 Nov, two runs per arm, headless Claude Code with Sonnet, at most 12 training runs of 30 s), test loss,
  lower is better: upgraded kit 1.7454 and 1.7481, old kit 1.7567 and 1.7520, no kit 1.7764 and 1.7362; the script
  as shipped 1.7557. The upgraded kit's edge over the old one (0.0076) is not established with two runs per arm.
  REPORT.md section 2; data in `%TEMP%\nnkit-upgrade\pilot1`.
- Final test run after the pilot (11 Nov): all seven files pass in WSL (three interpreters) and on native Windows
  (two). REPORT.md, README and the ledger's coverage rows are updated.
- 11 Nov, user: upgrade the real install. Done with `install.py --target`, dry run first: 21 files changed, 32
  added (21 of them backups in its `.claude/backups/nn-training-20261111-193154/`), journal and runs untouched,
  `expctl selftest` passes there. Nothing committed in that repository. REPORT.md section 4.
- 11 Nov, user: started the larger comparison (five runs per arm) in a separate session. Its work folder is
  `%TEMP%\nnkit-upgrade\pilot2`, and it writes its result into REPORT.md section 2 itself.
- 11 Nov, user: find what else would improve the kit, and the best current way to train with an agent. Done as a
  second look: a ranking of the 649 open ledger rows, one further web reader, and measurements on the pilot's loop
  data (the keep rule keeps a change that does nothing in about 8 % of cases, because it takes the noise from
  three baseline runs). Note `scout/draft/second-look.md`, ten new ledger rows, REPORT.md section 10. Nothing built.
- Larger comparison finished (11 Nov, 19:27 to 21:26, five runs per arm, 15 valid arm-runs, none void, same setup as
  the pilot, kit files unchanged during the run), test loss, lower is better: upgraded kit 1.7501, old kit 1.7545,
  no kit 1.7425; the script as shipped 1.7568. The upgraded kit's edge over the old one (0.0044, 95 % interval
  -0.010 to +0.019, exact permutation p = 0.54) is not more than the noise; neither kit was shown to beat no kit.
  Five against five finds only about 0.018. REPORT.md section 2 (also Read this first, sections 9 and 10), README
  and the ledger row state it; `tests/test_benchmarks.py` passes; data in `%TEMP%\nnkit-upgrade\pilot2`. 4.1
  million tokens, no usage billed per use.
- 11 Nov, user: build group A of the second look ("Trustworthy decisions" in REPORT.md section 1). Built in five
  code commits (subjects "Loop: ..." and "Final evaluation: ...") and three for the documents:
  the keep rule's noise pooled over all seed panels with a t multiplier; a session may decline to propose a
  change; a self-test of the evaluator before any agent session; a confirmation on fresh seeds when a campaign
  that kept something ends (`loop.confirm`, runs held back from the limits); `expctl final-eval`, single-use with
  a hash-chained receipt, and the guard changes that go with it (REPORT.md section 6). Not built from that group:
  the comparison seed by seed (measured and rejected in round 2) and tamper fixtures for the self-test. All seven test files pass
  on the commit with the last code change, in WSL (default 3.12, clean 3.8, clean 3.12) and on native Windows
  (default 3.11, clean 3.11, clean 3.8), and once more, with each platform's default interpreter, on the last
  commit that changes a file a test reads. It ran with a real agent on 12 November, and the real install got it
  the same day (both below).
- 12 Nov, user: would other projects (Unsloth's local-model command, the autoresearch forks and plugins, a
  ranked list of thirty training projects, skills for Claude Code, a simulation plugin, training on agent traces,
  harness adapters) do better than the kit? Answered from the ledger, which held a decision for all but four;
  those four were read and have rows in `scout/draft/second-look.md` ("Asked afterwards"). No decision changed,
  nothing was built or tried.
- 12 Nov, user: upgrade the real install again, to the kit with group A. Done the same way (rehearsal on a copy
  of its kit files, dry run, run; no live run there): nine files changed, each backed up in its
  `.claude/backups/nn-training-20261112-002917/`; settings, `CLAUDE.md`, journal and runs untouched; `expctl
  selftest` passes there; the guard there refuses both configured final commands typed directly and asks for
  `expctl final-eval`. No final evaluation was run. Nothing committed in that repository. REPORT.md section 4.
  Helper scripts: `%TEMP%\nnkit-upgrade\real2.sh` and the `real_*.py` files beside it.
- 12 Nov, user: which tool to use (the kit, autoresearch, both, something else), a full guide to the kit by
  scenario, and a guide to the best training approach and stack for a non-expert. Written as `docs/GUIDE.md` and
  `docs/TRAINING_GUIDE.md`, linked from `README.md` and `docs/README.md` (`a4f8dae`). Both restate the references,
  the ledger and the report; flags and commands were checked against the argument parsers and the references.
  Nothing was built, installed or tried for them: the stack rows stand as tried on 11 Nov, and the lines marked
  "general practice" have no source in the kit. No test reads the changed files; `test_kit` (133 checks) and
  `test_benchmarks` (23) pass on Windows at that commit, the other five and WSL were not re-run.
- 12 Nov, user: finish what was left and make sure it is tested, evaluated and checked. On the real install: the
  kit's files are committed (one local commit of exactly the kit's 32 paths, not pushed; the project's other
  uncommitted work untouched; undo with `git reset --soft HEAD~1` there). Its two registered scripts are shown to
  work with the upgraded kit without being run: their logger calls bind under its interpreter, the logger's unit
  tests pass there, and a stand-in script making the same calls was launched, finished and stopped through the
  upgraded `expctl` in the rehearsal copy. Not done there, on purpose: the two scripts themselves, a final
  evaluation (its test set is spent only when the user names the run), a metric in its config (unset by that
  project's own choice). Three things I had said about it were wrong and are corrected in REPORT.md section 4.
  Helper scripts: `%TEMP%\nnkit-upgrade\real3*.py` and `smoke\`.
- Found on the way (12 Nov): the guard does not cover a git worktree registered outside `.claude/worktrees/`
  (from a session there the file tools read the main checkout's sealed files), nor the harness files of a sibling
  worktree for the file tools. Tried in a practice project (`%TEMP%\nnkit-upgrade\gap_probe.py`). Not new with
  the upgrade. Documented in README "Notes and limits" and REPORT.md sections 6, 8 and 9. Fixed in round 2.
- Campaign with a real agent on the kit with group A (12 Nov, native Windows, headless Claude Code 2.1.322 with
  Sonnet, limits of 40 runs and 1.5 hours, practice project `%TEMP%\nnkit-upgrade\pkga1`): baseline, evaluator
  self-test, scouting, 13 worker sessions of which the last two declined, eleven changes trained, two kept (a
  moving average of the weights from the scouting notes; an initialisation of the worker's own), ended as "search
  exhausted", confirmed on three fresh seeds (1.6948 to 1.6407 against a margin of 0.0129). 26 runs, 21 minutes,
  610,061 tokens, nothing billed per use, no guard refusal. Then the practice project's final evaluation through
  `expctl final-eval`: use 1, a second use refused without `--again`, use 2 with a reason; receipt and journal as
  designed. Two observations: the first keep passed at the configured minimum margin because the baseline runs
  lay unusually close together, and the gain during the search (0.027) was half the gain in the confirmation
  (0.054); cause not looked for. REPORT.md section 2. Helper: `%TEMP%\nnkit-upgrade\pkga.py`.
- Full test run (12 Nov, `daa8cfc`, default interpreters): all seven files pass in WSL (3.12, 509 checks) and on
  native Windows (3.11, 502 checks). The commits after it change documents only.
- 12 Nov, user: a prompt for a further round (survey of the top similar projects and of newer techniques, tools,
  plugins, MCP servers and skills; integrate what is better). Delivered in the chat as a prompt, not run.

## Round 2 (ROUND2.md), done on 12 November; what it left open is under "Not done"
- Research, done by four readers on cheaper models (12 Nov): `scout/draft/census-loops.md`,
  `census-harnesses.md`, `newer-methods.md`, `third-report-claims.md`, with candidate rows beside them.
  `scout/census.md` holds the systems read (eleven in depth, each with source, version or commit and date), the
  capability matrix with the kit as one column, the candidates and four whole-system alternatives. No system
  read does the kit's whole job better, and no part of the kit was replaced.
- Guard, done (`b7b7652`): every registered worktree of the repository and the main checkout are covered from
  every other one (sealed denied, frozen and harness files ask), `git show <rev>:<sealed path>` is denied, and
  the loop's unattended session may read data the loop linked into its worktree. `tests/test_loop.py`,
  `guard_tests`.
- Noise on the benchmark, measured (two commits, eight seeds, two repeats, 30 s budget): seeds are not shared
  between commits (r = 0.3 between seed means, the level of unrelated pairs), the kept commit repeats to within
  0.0001 on the same seed, its true gain is 0.035 (the search's 0.027 and the confirmation's 0.054 lie on either
  side by seed-to-seed variation). So: no pairing by seed, no re-measuring on the same seeds.
- Keep rule, done (`9424706`): a gain above two thirds of the margin is trained on a second seed panel (the
  best so far once), then decided on all seeds at 1.1 x `noise_mult`. Chosen by simulating whole campaigns on
  the measured noise against the alternatives (first-seed check with slack or against the panel mean or absent,
  a first baseline of twice the size, re-measuring a kept commit): only this one gained in both regimes, with no
  more no-effect changes kept per campaign. `nnloop.py` (`second`, `extra`, `margin`), `tests/test_loop.py`
  (`second_panel`), `references/loop.md` "The keep rule". One live campaign since (below).
- Worker's view, done (`c6c1593`): a discard on the first seed records both scores, and the worker's prompt
  carries a few points per metric of one run of the best commit (from `expctl curve`; names and steps from
  training code are reduced to plain characters and numbers). Effect on results not measured.
- Guard liveness, done (`c6c1593`): a session, scouting included, that used tools or changed files and left no
  guard record stops the campaign (before: only when files were changed, and the scout was not checked). In the
  66 recorded real sessions none would have been stopped wrongly.
- e-means, done (`7233b9e`): checked at the source (arXiv 2611.09501, FAISS 1.16.0) and tried against FAISS
  k-means on 200,000 synthetic vectors. It is the documented optional method for the one job where clustering
  belongs, a data step that clusters embeddings (`references/data.md`, section 8). The kit adds no code.
- Ledger, done: 82 rows in four notes (`census-loops`, `census-harnesses`, `newer-methods`, `round2`), among
  them every claim of the other model's audit and every open item ROUND2.md names; `LEDGER.md` rebuilt (1,498
  rows); `references/stack.md` agrees with it.
- Live campaign `r2`, done (headless Claude Code 2.1.322 with Sonnet, native Windows): seven changes trained,
  one kept on six seeds through the second panel, and the confirmation on fresh seeds found that gain inside
  the noise (0.0067 against a margin of 0.0140: `unclear`). 28 runs, 8 sessions, 319,657 tokens, nothing billed
  per use. So the round's changes are not shown to raise results.
- Independent review, done: one fresh Opus subagent without the working context, kit at `7233b9e`. 19 findings
  (12 guard, 6 loop, 1 final evaluation): 14 fixed, 1 fixed in part, 4 answered with Reject rows. Commits
  `af6cbeb` (guard) and `7c1306f` (loop, final evaluation, self-test). A probe of my own afterwards compared
  the guard with what ripgrep 15.2.0 reads over eleven layouts of linked data folders and found five more
  searches that reached sealed files: closed in `98640c9`.
- Found by the full test run at `98640c9` and fixed (`9d5c80d`): a clock that went backwards during a paid
  remote run shortened the time the ledger booked, down to nothing. The ledger now books the larger of the
  wall-clock time and the controller's own count. `1337fbe` adds one sentence to `references/evaluation.md`.
- Found by the full test run at `1337fbe` and fixed (`6e01543`): the mirror of a rented job could keep an older
  file of the same size, because `hf buckets sync` passes over such a file unless it is newer by more than a
  second (read in the source of huggingface_hub 2.4.0), and teardown then removed the bucket prefix. The last
  pull now compares SHA-256 checksums on both routes (`_pack --sums` for ssh, `remote-files.json` in the bucket
  prefix for a job) and fetches a differing file by itself; nothing is removed while one differs. The stand-in
  `tests/fake_hf.py` follows the real rule now. Not run against the real service. End to end the fix shows
  only with the stand-in's window widened to 5 s (scratch clones on native Windows, two runs each: before
  the fix the check "results are mirrored" fails, with it all 72 pass); with the real second the code
  before the fix passed that check in five of five runs.
- Full tests at `6e01543`, the last code change (12 Nov): all seven files pass in WSL (default 3.12, clean
  3.12, clean 3.8) and on native Windows (default 3.11, clean 3.11, clean 3.8). Checks per file and the two
  earlier failures: REPORT.md, "Round 2", "Tests". Logs under `%TEMP%\nnkit-upgrade\logs\`, label `r2final4`.
- Report, done: REPORT.md has a section "Round 2" right after "Read this first"; the numbered sections are
  corrected where the round changed a fact.
- The real install was not touched during the round. A dry run on the rehearsal copy at `6e01543` listed
  fifteen kit files that another installer run would replace (REPORT.md, "What another installer run would
  change in the real install").
- 12 Nov, user, after the round's report: run the installer on the real install a third time. Done as the
  second time (rehearsal on a fresh copy of its kit files, dry run, run), from an export of `8d53751` (the code
  of `6e01543`), because another session was editing this working tree. Fifteen kit files and the manifest
  replaced, as forecast, each backed up in its `.claude/backups/nn-training-20261112-180059/`; config, settings,
  `CLAUDE.md`, `.gitignore`, journal, experiments and runs unchanged (223 of the 239 files listed before);
  `expctl selftest` passes there with one optional check failing (no metric configured, that project's
  choice); the 27 files of its skill, hooks and agents folders equal the kit's apart from lines that name its
  interpreter. The sixteen files are committed there since the same day, on the user's "Yes, commit them":
  one local commit of exactly those paths, not pushed (undo with `git reset --soft HEAD~1` there); the files
  on disk are as they were before it. Its guard, asked with the file as it was and as it is:
  `git show <rev>:<sealed path>` went from a question to a refusal, an edit of a sibling worktree's
  `.claude/settings.json` from allowed to a question. A search of its linked data
  folder is allowed before and after, and rightly: the one sealed pattern below that link names a folder that
  is not on disk and would lie behind a second link. So "until then its guard lets a search of its linked data
  folder through" was wrong for this install; REPORT.md is corrected ("The third installer run on the real
  install"). The checks left 16 lines in its guard record. Helper scripts: `%TEMP%\nnkit-upgrade\real4*`.

## Round 3 (three items of the build order), done on 12 November; three repairs on 13 November
- Numeric settings searched by the harness (`395697f`, fixes after the review in `ddc7afa`):
  `loop.search_trials: K` in a project's config. The worker may write numbers as top-level lines
  `NAME = <number>` in an editable file and name their ranges under `search` in `PROPOSAL.json` (one to six
  settings). The harness trains up to K stratified versions (a repeated one is left out), each once on one
  seed outside both seed panels, commits the best one's values and decides that commit by the keep rule. It
  reads and writes those lines only in plain files of the worktree (no link, no file below a linked folder,
  no hard link), checked before every write. Trials count against the run limit and stay out of the noise
  estimate. No Optuna, no successive halving. `nnloop.py` (`search_space`, `draws`, `setting`, `linked`,
  `Campaign.trials`, `Campaign.own`, `Campaign.search`), `references/loop.md` ("A search by the harness"),
  `references/hpo.md` section 8, `tests/test_loop.py` (unit checks and campaign h, 18 checks).
- A second benchmark task (`dbe0694`): `benchmarks/finetune/`, SmolLM2-135M-Instruct (Apache-2.0, one pinned
  revision, fetched by `fetch_model.py` with a size and SHA-256 check) with a LoRA adapter on Banking77 (CC BY
  4.0; 9,488 training rows, 500 for the agent, 1,000 sealed for the loop, 1,000 sealed for the final
  evaluation), 30 seconds a run, exact match of the generated intent by a frozen evaluator that loads only an
  adapter in safetensors. `new_project.py` and `pilot.py` take it with `--task finetune`.
  `tests/test_benchmarks.py` section 4 (12 checks, no PyTorch needed). Ran on native Windows (RTX 5090, a
  temporary environment with Transformers 5.22.2 and PEFT 0.21.2): the starter script 0.372, 0.386 and 0.351
  on seeds 1 to 3; with a learning rate of 1e-3 0.691; one loop campaign with the tests' stand-in agent, 12
  runs in 13 minutes, the higher learning rate kept (gain 0.334, margin 0.025) and confirmed on fresh seeds
  (0.667 against 0.332). Not run: a real agent session, `pilot.py`, WSL.
- A restart when a campaign stalls (`87a2f42`): `loop.restart_after: K`. After K iterations in a row without a
  keep, or two sessions in a row that decline, the next worktree starts from the commit before the last keep.
  The commit that is left stays the result (`best` in `state.json`, the branch stays on it) until a keep on
  the new line beats it on the seed panel; the campaign ends on and confirms its best commit; the worker reads
  the history of the code in front of it. `nnloop.py` (`Campaign.restart`, `lineage`, the keep branch of
  `iteration`, the end of `run`), `references/loop.md` ("A restart when the campaign stalls"),
  `tests/test_loop.py` (campaign r, 12 checks).
- Ledger: the three rows of `second-look` are Adopt and finished (`scout/covered/built-round3.json`): 418
  adopted rows, 280 finished, 138 unfinished. They are Adopt because they are built on ROUND2.md's go-ahead,
  not because a measurement decided them; each row says that its effect is not measured.
- Guard: no change. `nn_guard.py` is the same git blob as at `6e01543`; `install.py`, the settings and the
  Codex and Cursor files are unchanged too. Changed in existing features, each in a few lines: `runlog.py`
  (the attempts of a run's first records; the removal of a temporary file), `expctl.py` in one function,
  `read_json`, `nnremote.py` in the remote side's listing of a run directory, and `nn_statusline.py` in its
  `read` (the two faults and the three repairs below). The guard reads through `read_json`; a run that read
  as `stalled` for a moment counted as live, so its answers are the same. It does not read through the
  status line.
- Behaviour without the two new keys: iteration rows gain `base`, `state.json` gains `line` and `stall`, the
  confirmation never draws the seed after the second panel, and the two keys are validated at start. The
  worker's prompt and the journal are as before (REPORT.md, "Round 3", "Changes in the behaviour of existing
  features").
- Independent review (a subagent on a cheaper model, read-only, the search and the restart in `nnloop.py`
  against `references/loop.md`; it ran nothing and did not read the tests): no serious defect in the restart,
  ten findings. Fixed in `ddc7afa`: the harness wrote searched values through a link at an editable path
  (now plain files only, checked before every write); repeated versions and unequal shares in `int` ranges;
  `"log"` and `"int"` that are not true or false; `Infinity` for the two keys. Answered in `references/loop.md`:
  an early search can use the confirmation's runs (leave room in the run limit); a campaign begun with the
  earlier `nnloop.py` cannot go back beyond a keep made before the upgrade. Answered without a change: a
  search interrupted by a stop is a `duplicate` after a resume; values compared as text; a repeated second
  panel after a kill and resume; a byte-order mark, a lone carriage return, a setting line inside a string.
  Each with its reason in REPORT.md, "Round 3", "The independent review". Known limit: the check and the write
  are two steps, so a process that swaps the file in between is not caught.
- A fault in an existing feature, found by the full test run and fixed (`0f97004`). On Windows `RunLog` wrote
  the records of a run's start (`manifest.json`, `config.json`, `env.json`) with one attempt, so the run ended
  at once with `PermissionError` when another process had the file or its temporary file open at that moment.
  The remote helper of a rented job copies the run directory at short intervals, and with the tests' stand-in
  the job runs on this machine: there it showed, as two failed checks of `tests/test_remote.py` under Python
  3.8 at `ddc7afa`. The three writes now get the 40 attempts that `result.json` has. One new check in
  `tests/test_runlog_units.py`. Before the change the 24th repeat of that check failed, and so did 7 of 600 run
  starts beside a process that copies every file. After it: none of 600 starts and none of 120 repeats (the
  scripts are named in the working notes).
- A second fault in an existing feature, found by the next full test run and fixed (`b2f1fd3`). On Windows
  `expctl status` could report a live run as `stalled`, or as `starting` while it was young, for one call:
  it opened `heartbeat.json` once, and Windows refuses the open in the instant in which the run replaces the
  file. It showed as one failed check of `tests/test_kit.py` under Python 3.8 at `0f97004` ("statusline
  leaves the run alive"; the run itself completed). `read_json` in `expctl.py` now looks up to three times,
  20 ms apart, when the open is refused. One new check in `tests/test_kit.py`. Readings of a live run that
  follow each other without a pause: 38 of 49,437 said `stalled` before the change, each with the refusal on
  the heartbeat, and none of 47,018 after it. At the test's pace none of 3,157 did, and the failed check's
  log does not name the state it saw: that it was such a reading is a conclusion (`sl-try.py`, working
  notes).
- Three smaller faults, seen beside those two and repaired on 13 November on the user's go-ahead. Each has
  one check that fails on the code before it (run on Windows under Python 3.8 and 3.11).
  `687bb50`: `runlog.py` removes the temporary file of a write that gives up, at once or with the run's next
  write. Before, every heartbeat whose rename Windows refused left `.heartbeat.json.<pid>.<hex>.tmp` in the
  run directory (check in `tests/test_runlog_units.py`).
  `a945eeb`: `copy_out` and `op_pack` in `nnremote.py` list the run directory through `files_in`, with
  `os.walk`. A folder that a training script removes during the listing no longer raises under Python 3.8
  to 3.11; for a rented job that error would have ended the helper and the job (from the code, no job was
  lost). The kit's temporary files, a name that starts with a dot and ends in `.tmp`, are no longer copied
  to the store or packed for a pull. `references/remote.md` says both (check in `tests/test_remote.py`, on
  `copy_out`; `op_pack` shares the listing and had no such check: round 4 narrowed the filter to the exact
  form of the kit's temporary files and checks both sides, `4fe23a0`).
  `0f23999`: `read` in `nn_statusline.py` looks up to three times, 20 ms apart, when an open is refused, so a
  live run no longer drops out of the line for one refresh (check in `tests/test_kit.py`).
- Full tests at `0f23999`, the last code change (13 Nov): all seven files pass in WSL (default 3.12, clean
  3.12, clean 3.8) and on native Windows (default 3.11, clean 3.11, clean 3.8). `tests/test_loop.py` has 196
  checks on Windows and 197 in WSL, `tests/test_benchmarks.py` 35, `tests/test_kit.py` 136 and 140,
  `tests/test_remote.py` 73, `tests/test_runlog_units.py` 18; the rest as at `6e01543`. Checks per file:
  REPORT.md, "Round 3", "Tests". Logs under `%TEMP%\nnkit-upgrade\logs\`, label `r3e`. The same passed at
  `b2f1fd3` on 12 Nov (label `r3d`; kit 135 and 139, remote 72, runlog_units 17). Earlier runs, each passing
  in WSL and failing once on Windows under Python 3.8: `0f97004` one check of `tests/test_kit.py` (label
  `r3c`), `ddc7afa` two checks of `tests/test_remote.py` (label `r3b`). Those are the two faults above.
  `87a2f42` passed on Windows (label `r3`).
- Report, done: REPORT.md has a section "Round 3" after "Round 2"; `scout/census.md` and
  `scout/draft/second-look.md` say what was built.

## Round 4 (the first four of the ranked list; round 3's repairs looked at again), done on 12 and 13 November
- The question at the project root (list item 2; `e7a69dc`, `d02137e`, `8e69154`): a recursive command over the
  project root (`grep -r`, `find`, `ls -R`, `tree`, `tar`, `zip`, `cp -r`, `rsync`, their PowerShell and `cmd`
  forms) is asked about when sealed files lie on disk below it. It passes when it names folders without sealed
  files, gives a file filter of that tool that leaves them out, or no sealed file is on disk. `rg`, `git grep`
  and the Grep tool are judged as ripgrep and git behave. That closes the gap kept since 23 October, up to
  the file bound below. `nn_guard.py` (`reaches_sealed`, `searched`), `tests/test_kit.py` (`guard_tests`).
- Guard gaps found on the real project (item 1): one walk per searched folder for all sealed patterns
  (`43adda1`; 1.81 s became 0.40 s on 15,000 files with five patterns); a `cd` behind a blank, a keyword or a
  wrapper is followed (`4b75776`); the two subagents' own hook blocks a call when it cannot run (`d07606c`); a
  recursive command over another checkout is judged by the sealed files there (`48305c2`); `expctl selftest`
  warns about checkouts of the repository in which no guard runs (`3dcc780`); `install.py --worktrees`
  registers the guard in those checkouts' `.claude/settings.local.json`, and `--uninstall` takes the entries
  out (`8329718`). That option is the one place where the installer writes outside the target, and only with
  the flag. Checked live with headless Claude Code 2.1.322 on native Windows, before the four faults of
  `689cd54` were fixed.
- Evaluator checks (item 3; `0638339`, `92f7ffe`): two more self-test cases before any agent session (a folder
  with only a run's records must get no score; a full copy of a baseline run whose records and log state
  other numbers must get the run's score), and `loop.controls`: runs that cannot have learned the task, each
  with a floor it may not beat. `benchmarks/charlm/controls.py` has two (`constant`, `shuffled`); run live
  they scored 4.174 and 3.310 against floors of 4.174 and 3.300. Each control costs one run of the run limit,
  and the pilot leaves them out. `references/loop.md`, `tests/test_loop.py`, `tests/test_benchmarks.py`.
- The measurement of the search (item 4; `00be575`, text and ledger only): `loop.search_trials: 6` against the
  same versions proposed by hand, `--max-runs 18`, the stand-in agent, real training on native Windows, three
  pairs of campaigns per task. Fine-tuning task: confirmed gains of 0.47, 0.38 and 0.41 with the search, 0.30,
  0.19 and 0.44 by hand (differences +0.18, +0.18, -0.02; mean 0.11; standard error 0.015 by the run-to-run
  spread, 0.068 across the pairs). Character model: nothing kept in any of the six campaigns. The rule fixed
  beforehand asked for a gain on both tasks, so the key stays off by default. The campaigns' plans, logs and
  result files are in `%TEMP%\nnkit-upgrade\search-measure`; their projects are removed.
- Round 3's repairs, looked at again (the user's message of 13 November). The three hold. Fixed beside them:
  `expctl.py`'s own writer left its temporary file as `runlog.py`'s did, and both left it when the write
  itself failed (`a774971`); the remote side's filter kept a training script's own `.tmp` files out of the
  mirror and is now the exact form of the kit's temporary files, and `op_pack` has its check (`4fe23a0`); a
  resume that could not start cost the ended run its exit record (`ffaa346`); `expctl status` and `watch`
  could show a run that had just ended or been killed as lost for one look (`66175db`). Live on this machine:
  of 2,000 heartbeat writes about 1,900 were refused, with 1,905 leftover files on the code before `687bb50`
  and none since; 14 of 30 short runs and 11 of 12 killed runs read as lost once before `66175db`, none
  after. What was left, with the reasons: REPORT.md, "Round 4", "Round 3's repairs, looked at again".
- Independent review: two subagents on a cheaper model without the working context, 28 findings, all fixed
  or answered. The guard twice (11 findings in the state of `92f7ffe`, 7 more in the fixes): `c72c576`,
  `624b6c5`, `e710e83`, `45d7794`, `65293d8`, `f7f5b6e`, `0884c70`, `34000d5`, then `df54cdd`. The installer
  and the loop (10): `689cd54`, `d45c69c`, `3bca5a4`, `af57601`. Two of the guard findings were holes that
  `e7a69dc` had opened; they were closed before anything reached `main`. No third look: the fixes to the
  second look and to the installer and loop findings are verified by my own probes and by tests that fail on
  the code before them.
- The guard is stricter in many forms (REPORT.md, "Round 4", "Changes in the behaviour of existing features",
  with 153 examples asked before and after): exploring commands at the root, a move or rename of a folder
  that holds sealed files, a command word in quotes, a path that exists only below a named folder as a
  sealed file. An error inside the guard asks about reads too, and a check longer than 12 seconds ends as a
  question.
- The guard's file bound, measured on 13 November and not lifted. `reaches_sealed` looks at no more than
  20,000 files per folder it walks; a sealed file beyond them is not seen, and the command passes. In made-up
  projects with 19,000 and with 20,500 files in front of the sealed file (48 calls per size, Windows, Python
  3.11) every call was asked about or refused at 19,000, and at 20,500 these passed: with a pattern that
  begins with `**/`, every recursive command and search at the root and over a folder below it; with a
  pattern for some files of a folder, the same at the root, and the Grep tool from a folder above; with a
  pattern for a whole folder, only searches with a file filter. The bound dates from `acf7706` (11 Nov);
  before round 4 every recursive command at the root passed, so nothing is weaker. Not lifted: a question at
  the bound would meet every search of a large project, and a longer walk costs every search its time. The
  fix is an index of the sealed files or a walk that leaves out what git ignores. README "Notes and limits"
  and REPORT.md ("Round 4", "The question at the root") say so.
- Ledger: note `scout/draft/round4.candidates.jsonl` (seven rows) and `scout/covered/built-round4.json`; four
  older rows are finished. 422 adopted rows, 288 finished, 134 unfinished; 1,505 rows from 31 notes.
- Full tests at `00be575`, the last code change (13 Nov): all seven files pass in WSL (default 3.12, clean
  3.12, clean 3.8) and on native Windows (default 3.11, clean 3.11, clean 3.8). Checks on Windows and in WSL:
  `tests/test_kit.py` 363 and 367, `tests/test_loop.py` 210 and 211, `tests/test_ports.py` 120 and 121 (one
  fewer under Python 3.8), `tests/test_remote.py` 75, `tests/test_benchmarks.py` 39 (38 in the clean
  interpreters, which have no PyTorch), `tests/test_review_fixes.py` 38 and 40, `tests/test_runlog_units.py`
  18. Logs under `%TEMP%\nnkit-upgrade\logs\`, label `r4`. The commits after it change documents only, and
  no test reads those.
- Report, done: REPORT.md has a section "Round 4" after "Round 3", and the older sections say where round 4
  changed a fact.
- During the round the real install was not touched: I read, in aggregate, its guard record and the list of
  the repository's checkouts.
- The fourth installer run on the real install (13 Nov, a later session, on the user's "Update my install").
  From a clean clone of `7a38b98`, whose code and tests are those of `00be575`; the full tests were not run
  again. A rehearsal on a fresh copy of its kit files, a dry run, then the run at 15:53. Replaced, each with
  a backup under its `.claude/backups/nn-training-20261113-155355/`: fourteen kit files (both agent files,
  three hooks, SKILL.md, four references, four scripts) and the manifest. Config, settings, CLAUDE.md,
  .gitignore, journal and runs are unchanged, and no run was live. `expctl selftest` passes; its optional
  checks that fail are the missing metric and the new one, 9 of 10 other checkouts without the guard. The
  guard's answers to twelve made-up calls, asked before and after with its own config: four recursive
  commands at the root went from allowed to a question, a `cat` behind `command cd` from allowed to
  refused, the other seven are as before. Left there: the fifteen files, committed on the user's "Yes,
  commit there" (one local commit of exactly those paths, not pushed, its parent the commit that was newest
  before; that repository's 418 other status entries untouched and no file on disk changed), the backup
  folder, and 16 lines in its guard record, 12 of them marked `upgrade-check`. REPORT.md, "Round 4", "The
  fourth installer run on the real install".

## After round 4: the guide for the person who uses the kit (13 November)
- `docs/GUIDE.md` reworked on the user's request ("Standing decisions"). Part 1 is new and in plain language:
  the kit in one minute, a text picture of how the parts fit, a table of what the kit changes and what holds
  each change (the guard, the procedure, harness code), six ways it improves training, the measurements with
  their limits, what the kit does not do. Part 2 is the earlier guide (sections 1 to 5, scenarios A to M,
  numbers and letters unchanged, so the pointers in `TRAINING_GUIDE.md` hold), with scenario A extended by a
  walk through the run tools by hand. Part 3 has the commands, the limits, the kit's own words and a table of
  where to read more. `README.md` and `docs/README.md` point to it, and the README's `runlog.py` row says how a
  launched run finds the logger (`fd63f0f`).
- Checked: the commands of scenario A on a fresh practice project (native Windows, Python 3.11, the local GPU:
  self-test, `launch`, `watch`, `curve`); every number against REPORT.md; every statement of Part 1 against
  README "What works where" and "Notes and limits"; every link against the tree. Not checked: the commands on
  Linux, and how the page looks on a hosting site. No test reads these files.
- Found by that walk and fixed (`11a7a2c`): a run of a practice script started by hand with `expctl launch` left
  no heartbeat, metrics or result, because the script looked for the logger beside itself and a launched run
  works from a snapshot of the source that has no `.claude`. Both practice scripts now look in
  `$EXP_PROJECT_ROOT` as a third place; runs of the loop and a vendored logger are found as before.
  `tests/test_benchmarks.py` launches such a run and checks its record (40 checks pass on native Windows,
  Python 3.11). The fine-tuning script got the same lines and was not run. The other six test files and WSL
  were not re-run: no file they cover changed. The installer installs neither `benchmarks/` nor `tests/`, so
  no install is out of date by it.
- Where it is: on `main`. The work was done on the branch `claude/kit-upgrade-continuation-8e3ca9`, in a
  worktree of that session. On the user's word of 13 November `main` was fast-forwarded from `7a38b98` to the
  branch, which brought this work and the two commits on the fourth installer run. Nothing is pushed.
- REPORT.md: point 12 of "Read this first" and the section "After round 4".

## After the guide: the full tests, the fine-tuning script, two fixes, the front page, the upload (13 November)
- All seven test files on native Windows (Python 3.11) at `a62db21`, before any change: 864 checks, none
  failed, in 12 minutes. Three checks are skipped there as Linux-only (tmux twice, bubblewrap).
- The fine-tuning practice script, for the first time through `expctl launch`, in a practice project made by
  `benchmarks/new_project.py` (native Windows, the local GPU): 369 steps in 30.0 seconds, 0.34 exact answers
  on `data/dev.txt`, about 61 seconds with the model's loading. Its record is complete (heartbeat, metrics,
  result, exit, the saved adapter), and the frozen evaluator, run by hand on the saved adapter, gives the
  same 0.34. The sealed files were not used.
- The first try of that run ended at its start: `module 'bitsandbytes' has no attribute 'nn'`. The system
  Python's site-packages holds an empty leftover `bitsandbytes` folder, the temporary environment reaches
  it, and PEFT takes it for the installed package. Nothing in the kit is at fault and the system Python was
  not changed. The temporary environment got the real package, and `benchmarks/finetune/README.md` says
  what to do (`0db85eb`).
- Fixed (`0edd1b3`): the practice projects listed no best run. Both practice scripts now name the model
  they saved as the run's result, so `expctl status` lists the run under `top` and `watch` reports
  `best_so_far`. This was left for the user's decision on the same day ("After round 4"); the request for
  fixes is taken as that decision. Training and the loop's decisions do not change (the loop keeps its own
  best). What changes: the sessions of a later pilot or campaign see a best run in `status`, which earlier
  ones did not. `tests/test_benchmarks.py` has one more check (41).
- Found while checking that fix, and fixed (`0450067`): `expctl status` dropped a run from its list of best
  runs, with the alert "recorded checkpoint missing", when the record named the checkpoint by a path of
  another machine. That is the case for the mirror of a remote run, for a project folder that was moved or
  renamed, and for a look from WSL at runs made on Windows. Status now looks for the part of the recorded
  path below the run's own folder in this run folder. A checkpoint that is gone still raises the alert.
  Shown with the copy of a completed run whose record was rewritten to a made-up remote path;
  `tests/test_kit.py` has one more check (364). Not tried on a real remote run. The real install has the
  fix since the fifth installer run of the same day (below).
- The guide (`b9e1d4c`): a new section, "How it works, step by step", follows a project through seven steps
  (what the installer writes, what a session knows at its start, the guard's three answers, what a launched
  run records, the seven phases, the noise rule with a worked example, the single final evaluation). The
  picture of the kit, the guard's answers, a launched run, the phases and a campaign of the loop are Mermaid
  diagrams. A table at the top says where to start.
- The README (`108728d`) is a front page: a banner (light and dark, `docs/assets/`), the facts in one line,
  a pointer to the guide, the picture of the kit, six lines of what it changes, the measurements in three
  sentences, the quick start, a practice project to try, a table of the documents. Everything from "What
  gets installed" on is unchanged. `docs/README.md` lists the upgrade records and the assets.
- Checked: links, anchors across files, table shapes, line lengths and code fences by script, no finding;
  the six diagram blocks drawn with Mermaid 11.4.1 in a light and a dark theme on a local page, and both
  banners; the new section's statements against the code and this record.
- Before the upload, a scan of the 200 tracked files and of the history: no file holds the user's name or
  e-mail address, this machine's name, a path below a user folder of this machine, a token or key, or a name
  of the other project. The history holds the name and e-mail address as author and committer of each
  commit, and nothing else of those.
- Tests at `0450067`, the last code change: all seven files pass with the three interpreters of each
  platform. WSL: 874 checks (default Python 3.12), 871 (clean 3.12) and 870 (clean 3.8), in 15 minutes.
  Native Windows: 866 (default 3.11), 863 (clean 3.11) and 862 (clean 3.8), in 34 minutes. No check failed
  and no log holds a traceback. A first run of both at `108728d` was stopped when the status fault was
  found; the four files it had finished in WSL had passed.
- Uploaded, on the user's word: `main` is fast-forwarded to the branch and pushed to a new private
  repository named `nn-training-harness` under the user's GitHub account (`origin` of the main checkout),
  with a description and twelve topics. The first push carried 127 commits, up to `0450067`; the commit of
  this record followed. No history was rewritten and nothing is public.
- Checked after the upload: the README and the guide as GitHub's renderer returns them (the banner with its
  light and dark variant, the tip box, every table, every in-page link has its heading, each diagram is
  handed to the site's Mermaid, no raw Markdown is left over), and both looked at on a local page with
  GitHub's style sheet, in a light and a dark theme. Not seen: the pages on the site itself. The built-in
  browser is not signed in to GitHub, and a private repository answers it with "not found".
- Two faults of the look that those views showed, fixed and pushed after it. GitHub gives every column of
  the README's table "By agent" its narrowest width, so the two row labels that held a whole list ran down
  the page a word or two per line: the lists now stand above the table, and two long cells keep their
  verdict and point to a note below it. No statement changed. Three comments that ran past the right edge
  of a command block are shorter or stand on a line of their own. Looked at again as GitHub renders them.
- Public, on the user's word ("Standing decisions"). What the publication consists of:
  - One new commit without a parent holds the files as they are, under the account's name and no-reply
    address and dated in UTC. `main` and the session's branch now start from it.
  - The history before it (132 commits) stays in this repository under
    `refs/archive/development-history`. The commit ids in these records belong to it, the baseline `5ea9659`
    among them, so `benchmarks/pilot.py --old-kit 5ea9659` works here and not in a clone of the public
    repository.
  - Added for it: `LICENSE` (MIT, with the account's name as the holder) and a section "Licence" in the
    README, which also names the terms of the practice data (Tiny Shakespeare: public domain; Banking77:
    CC BY 4.0).
  - Checked before it: the scan for private details over the final files (the terms of the first scan, no
    hit), and a search for network addresses, session ids, time zones and login names (only examples and
    vendor documentation). `docs/original-brief.txt`, `docs/original-prompt.txt` and the fixture of the old
    kit hold nothing personal.
  - How the repository came about, on the user's answer to one question ("Fresh repo, rename old"). GitHub
    keeps a replaced history retrievable by commit id and lists every push in the repository's activity
    log, and the commits of the first upload carry the private e-mail address. So the repository of the
    first upload was renamed to `nn-training-harness-dev-history` and stays private, the user's to delete,
    and a new repository with the kit's name received the one commit, with the description and the twelve
    topics of the first.
  - Tested from a clone that holds only that commit, Windows and WSL at the same time, default
    interpreters. WSL: 874 checks, all pass. Windows: 865 pass, one fails, "session hook injects status
    after compaction" in `tests/test_kit.py`. The two practice runs that this check and the guard's checks
    need running lasted about 68 seconds and the checks before it take about 64 on an idle machine, so
    beside a second suite the runs ended first. An existing test changed for it, the only one: those runs
    get 30000 steps instead of 3000, and the test's cleanup stops them as before. No check changed. At the
    fix, side by side again: Windows 866, WSL 874, all pass.
  - Public since those tests passed. Asked without a login: the page, the API and the raw README answer,
    GitHub names the licence as MIT, the commits carry only the account's name and no-reply address, the
    repository of the first upload answers "not found", and a commit id of the old history is not in the
    public repository.
  - Seen after it. The front page as a visitor gets it, in the built-in browser: the public mark, the
    description, the topics, the licence. The rendered README has a target for each of its 29 in-page
    links, six tables, the banner and the tip box, and no raw Markdown. The browser pane was hidden, so
    the look below the top comes from captures of the live pages with a headless browser.
  - A fault those captures showed, fixed and pushed. GitHub draws the diagrams with Mermaid 12.2, whose
    flowcharts wrap a label at 120 px (200 in version 11, which my local views had used), so lines that
    the files break by hand were broken a second time. Each of the five flowcharts now sets its own
    wrapping width in one `init` line; the sequence diagram is unchanged. All six diagrams were drawn
    locally with GitHub's version and settings. On the live pages the README's diagram (about 1040 px
    tall, about 1350 before) and four of the guide's five keep the written breaks.
  - Not seen on the site: the pages in an interactive session, a dark theme, a phone's width, and the
    guide's last diagram (scenario G), which lies below what a capture reaches.
- The fifth installer run on the real install (13 Nov, on the user's "Yes, run it"), for the fix of
  `expctl status`. From a clean clone of the public commit `920bddd`; its installed files are those of
  `03693f1`, where the full tests last ran, and one of them differs from the kit of the fourth run:
  `expctl.py`, by the seven lines of the fix. The steps of the fourth run. A read-only look first: the
  install was as the commit after the fourth run had left it (270 files, none changed), and no run was
  live. Then a rehearsal on a fresh copy of its kit files, a dry run, and the run at 19:24 UTC. Replaced,
  each with a backup in a new folder under its `.claude/backups/`: `expctl.py` and the manifest; the other
  31 kit files were up to date. Config, settings, CLAUDE.md, .gitignore, journal and runs are unchanged.
  `expctl selftest` passes with the two optional checks failing that failed after the fourth run (the
  missing metric, 9 of 10 other checkouts without the guard). `status` gives the same answer with the old
  and the new `expctl.py` on that project's records: five runs, four completed, one failed, no alert. The
  guard loads `expctl`, and its answers to the twelve made-up calls are the same before and after. The 27
  kit files there are the kit's, five of them apart from the lines that name the interpreter. The fix
  shows nothing there today: the list of best runs that it repairs is empty in that project, whose config
  names no metric. Left there: the two files, changed and not committed (that repository's 418 other
  status entries untouched, nothing staged), the backup folder, and 21 lines in its guard record, 17 of
  them marked `upgrade-check`.

## Round 5 (another model's review, 14 November): done; what it left open is under "Not done"

The review's text is kept beside the other user reports (`scout/scouts/user-review-1114.md`, not in git). Its
line numbers fit the tree at `60cc0b0`. Each claim was checked there before anything was changed: a claimed
way past the guard counts only where a probe call showed it, the claims about the keep rule were tried in a
simulation of the rule (40,000 campaigns per case), the others were read in the code. Marks: R real, to
build; N not a defect, or wrong; H held, with the test it needs; U waits for the user. "Where it stands" at
the end of this section says what is built.

### Verdicts
Rank 1, the two evaluators and the box around an evaluator
- R `benchmarks/charlm/evaluate.py` looks for a look-ahead at one position only, scores the rows in file
  order and does not look at what the loaded module can do. Build: rows in a fixed shuffled order, a probe at
  every position, a probe with rows exchanged, a refusal of modules whose code touches files.
- N the review's switch of that file to weights plus a fixed architecture: the task must stay free to change
  the architecture, and `torch.jit.load` does not unpickle arbitrary objects.
- R `benchmarks/finetune/evaluate.py` follows a link out of the run folder and hands every key of
  `adapter_config.json` to PEFT. Build: both files must lie in the run folder, and a key outside a short
  list must hold PEFT's default.
- R the loop's box for the evaluator leaves every file writable. Build: the project read-only for it, apart
  from the scored run folder and what a new key `loop.eval_writable` names.
- R the self-test's tampered copy equals the original when every number in the file is an integer.

Rank 2, ways past the guard (21 probe calls in a temporary project)
- R shell code attached to its flag (`bash -c"..."`): allowed without a word, under `--readonly` too.
- R PowerShell `-EncodedCommand` and its short forms: allowed without a word.
- R a sealed path put together from parts in inline code (`Path('data')/'test'/...`, `os.path.join`):
  allowed without a word.
- R a file written or edited so that its code opens a sealed path: allowed without a word. The one that
  matters most: this is how training code comes to read the test split. Build: a question.
- R a sealed path inside a longer string handed to another tool (an SQL query to an MCP tool): allowed
  without a word, on one line too. Build: a question.
- N `Path.unlink` and its kind under `--readonly`: denied today (four probes).
- R, known: the bound of 20,000 files per walk. Built, the narrow part: a folder sealed as a whole is walked
  on beyond the bound for up to five seconds of the hook call, and a walk that the time ends counts as
  reading it. (Counting every walk that reaches the bound as a hit, the first design, would have questioned
  each filtered search in a project with a large sealed folder.) H for patterns that begin with a wildcard,
  whose walk covers the whole checkout: it needs a walk that skips folders no pattern can match (my order
  under "Not done", first item).
- N the answer "ask" after 12 s: as designed. Where nobody can be asked, the guard turns it into a denial.
- R, small: a shell write below `.git/hooks/` or to `.git/config` is not questioned (the edit tools are).

Rank 3, sealed paths in snapshots and in the training box
- R `expctl.sealed_inside` goes by the literal start of a pattern: with `**/test/**` or
  `data/*/test/x.csv` a git-ignored data folder is linked whole into the run's snapshot, sealed files
  included; a folder six levels down is linked whole in any case.
- R `nnloop.protected_files` has the same blind spot: such sealed files are neither hidden from training
  nor in the hashes that show a change to them.
- N `EXP_PROJECT_ROOT` in a run's environment: on purpose (outputs that runs share). Build: the loop's scan
  of a change counts the name as a hit where no box hides the sealed files.
- R, found while building: a link inside the project that leads to a folder with sealed files, or to the
  project folder itself, brings them into the snapshot under the link's name.
- H a process namespace for the training box (`--unshare-pid`): RunLog writes its own process number into
  the heartbeat, and `expctl status` takes that number for the run's when the launched process is gone.
  Inside a namespace the number is another one, so a dead run could pass for whatever process has that
  number outside. It needs the number left out or translated for boxed runs, and then the test: a run
  launched through the box, stopped and killed, with `expctl status` right each time.
- U a container as the box: needs Docker Desktop (question below).

Rank 4, the keep rule (simulation: `gate_sim.py`, kept outside the repository; one test's nominal rate of
keeping a change without a gain is 2.3 %)
- N "the change's three seeds against the baseline's six": the rate stays at or below 2.3 % in every case
  tried (1.4 to 2.7 %). Matched seeds would cost 4 points of power for 0.4 points fewer wrong keeps.
- R in part, "the change's own runs lower the margin": a change with a twentieth of the baseline's noise
  is kept without a gain in 5.6 % of first iterations. The review's fix (margin before pooling) is worse
  where it matters: a change three times as noisy is kept in 15 % (10 % today), and a real gain of two
  standard deviations is found in 44 % of first iterations instead of 68 %. Build: the change's panels may
  not lower the variance, and its mean is tested with its own variance where that is more than three times
  the pooled one. Simulated (`gate_sim2.py`, 40,000 trials per case): 2.9 % for the flat change, 7.1 to
  7.5 % for the one three times as noisy once several panels are behind the estimate (10.3 to 13.7 %
  today), 79 % power with history (81 % today), 61 % in the first iteration (68 % today). Welch's degrees
  of freedom for the noisy case were tried and not adopted: 5.7 % instead of 7.5 % there, for 1 to 2
  points of power and a multiplier of 13.9 where the panel has two seeds.
- R one diverged run of a change that is not kept stays in the pooled noise for the rest of the campaign.
  Build: such a panel leaves the pool again, where one of its scores lies farther from the change's median
  than a t multiple (z = 4) of the deviation the other panels give.
- R the first-seed screen always uses the same seed. Build: it rotates.
- R a pause drops the line that a restart began (`loop.restart_after`). Build: it is set aside and resumed.
- N a bootstrap over test items inside the keep rule: it compares two trained models, the rule tests a
  recipe across seeds. N "GPU seconds are overbilled": the count is the reservation's upper bound on purpose.

Rank 5, `runlog.py`
- N a stop request read from one run's folder stops every later run of the same process: as it should. The
  file stands in for the signal, which reaches the whole process. `expctl stop` of one trial signals the
  study's process on Linux; on Windows it waits `kill_after_s` and then ends the process tree, so trials
  that ran on would be killed without saving, where today they stop at once. `references/hpo.md` tells the
  objective to end the study at a stop. `should_stop()` now says that a request holds for the process.
- R ranks of Lightning's own launcher (`LOCAL_RANK`, `NODE_RANK`, no `RANK`) all write the run files, against
  what `references/performance.md` says.
- R the two benchmark trainers never ask `should_stop()`.
- N locks around the two module sets: additions and removals of a set are atomic in CPython.

Rank 6, the remote runner and provenance
- R the bundle is built again by the detached controller and by the resume after a preemption, so what runs
  can differ from what was hashed. Build: the launch writes the archive once, the controller sends that file,
  and the automatic resume sends it again.
- R a link inside the project that leads to a sealed file is followed into the bundle. Build: a link is
  judged by the place it leads to, so such a one stays at home and `remote.files` refuses it. N a refusal of
  every link that leads out of the project: shared code and data are linked that way on purpose.
- R `complete()` accepts a pulled name that leaves the run folder. R two appends to the remote ledger can
  land on one offset on Windows (measured with eight writers of 100 rows each: 748 rows left, 19 torn lines).
  N a hash chain for that ledger: the file is guarded already, and a chain would not have kept the lost rows.
  N the two launches at the cap that both lose: neither overspends. N `--hours` for a target without a
  price: there is nothing to cap.
- R a rented `ssh` machine keeps costing after the run. Build: an optional command per target, run after the
  last pull; the reference says what it is for and what it does not cover.
- R `expctl`: an untracked secret-like file is copied into the snapshot; `resume` takes the code of today's
  tree without a word; a reused process number passes for the run on Windows without psutil; the receipt of
  a final evaluation leaves with a removed worktree. Build each.
- N `AGENTS.md` is in the source hash already (the review says it is left out). Build the reverse: agent
  instruction files and the kit's own bookkeeping do not make a tree "dirty".
- N the environment handed to runs, and hard links as the fallback for links on Windows: as designed.

Ranks 7 to 10, speed and search
- R (7) no step checks that the fast paths work on this machine before runs use them; the report's own note
  of a crash with the pinned wheel in WSL shows why. Build: `expctl env --probe`, each probe in a process of
  its own; a short "make it fast first" step in SKILL.md with the measured checks; the pin in `stack.md`.
- R (8) a change that does not compile, or that changes nothing but comments, costs a run; a crash in the
  first seconds costs the iteration. Build: a compile and same-code check before training, one repair turn
  after an early crash. H the stop at a quarter of the budget: it discards slow starters, and its saving
  needs long runs to measure (test: replay on a campaign with runs of ten minutes or more).
- N (9) a callback for TRL: its trainers are `transformers.Trainer`s, which `hf_callback` serves. H a
  wrapper that reads other engines' logs: no engine in use here to test against. N the tabular and prompt
  optimisation helpers: outside training neural networks. N recipe mode: `loop.editable` takes any file.
- H (10) traces for the worker beyond the crash output, two lines of descent with crossover: each needs
  campaigns with and without, GPU hours. N block markers inside files (the ledger's earlier decision stands:
  paths are the unit the guard can enforce); N `nnloop finalize`: each kept change is one commit already.
  N the advice on worker models in `loop.md`: it is what the pilot measured here.

Ranks 11 to 13 and 17, references
- R the fine-tuning reference names no objective after GRPO. Build: a short section with the sources that
  can be checked (Dr. GRPO, DAPO, GSPO, CISPO; rsLoRA and DoRA where missing). H the items whose source
  could not be found or opened; each is listed in the ledger with what was looked for.
- N routing of tabular and prompt-optimisation tasks: outside the kit's purpose.

Rank 14 and 15, other agents and MCP servers
- U a plugin for Antigravity, a hook for Gemini CLI: neither is installed here, and installing an agent is
  the user's call. N `sandbox_mode` in Codex agent files: contradicted by Codex's documentation in the
  research of 11 November (`scout/draft/user-reports.md`, row 32). H more denials in `.cursor/cli.json`:
  Cursor's terminal agent is not installed, so the rule syntax cannot be tried. N "ask" to "deny" for the
  Hugging Face tools: a question is what the user chose, and headless sessions cannot answer one.
- U the MCP servers: each is an install.

Rank 16 and 18
- R the ledger counts as finished some adopted rows that name kit code which was never written (see rank
  19). Build: `expctl audit-splits` (duplicates inside a split, overlap between splits, a fingerprint per
  split; counts only). Decided in step 7: the wiring check became reference text, and the controls for the
  fine-tuning task are held (the record of step 7 below has the reason and the test).
- H parallel trials and other samplers for the search: need campaigns to compare.

Rank 19, small repairs
- R `make_ledger.py` lets a reference outrank the record of what was built: three rows marked "partly
  built" and eight that name kit code show as finished. Build: the build record wins; the eight are checked.
- R an apostrophe in the interpreter's path breaks the YAML of the two agent files. R the `.gitignore`
  header is written again by a later run. N folded YAML: the installer reads the kit's own two files.
- N a licence file (there is one, MIT) and the removal of `.claude/worktrees/...` (this checkout).
- R, as said under rank 7: the warnings that the references promise in `expctl env` (the `datasets`
  advisory) are not there. N a new `doctor` command: `selftest` and `env` are that command.

Ranks 20 to 22 and the second part
- N new skills beside this one; U cloud drivers (accounts, paid); H a second pilot (subscription use and GPU
  hours; the question stands under "Questions for the user").
- N the rebuild as six "planes" with a new package layout: every installed path would move, which breaks the
  upgrade of existing installs through the manifest, and the single-file scripts that run without packages
  are a requirement of PROMPT.md. The mechanisms worth having are built into the existing files, as above.

### Order of work
1 the evaluators and their box; 2 the guard; 3 snapshots and the training box; 4 the keep rule; 5 runlog;
6 the remote runner and provenance; 7 speed and search; 8 references, installer, ledger; 9 the full tests
on both platforms, REPORT.md, the ledger rows. One commit per idea, each with its test.

### Where it stands
- Done: the checks behind the verdicts above. Step 1 is built: the two benchmark evaluators (`3fd5c16`), the
  self-test's tampered copy for records of whole numbers (`f274041`), the evaluator's box on Linux with
  `loop.eval_writable` (`ccf8ad0`). Checked narrowly on Windows and in WSL; the full runs come in step 9.
- Done, step 2, the guard, one commit per idea: shell code attached to its flag, encoded for PowerShell or
  piped from a decoder (`2a2edf6`); paths joined from string literals (`32442fb`); the text that an edit
  writes or an MCP tool gets (`47cb8eb`); the walk of a folder sealed as a whole (`0abddf2`); shell writes to
  git's hooks and configuration (`19d5ff5`). Each of the five states passed `tests/test_kit.py` and
  `tests/test_ports.py` on Windows, the last one in WSL too, with `tests/test_review_fixes.py` and the loop's
  guard tests. On the code before them, 21 of the new checks in the first file and 2 in the second fail.
- For REPORT.md section 6 so far: on Linux with bubblewrap the loop's evaluator can no longer write into the
  project outside the folder it scores (the way out is `loop.eval_writable`) and no longer sees sealed data
  that only `final_eval_commands` names; the self-test's tampered copy moves whole numbers in a record that
  has no number with a fraction; the benchmark evaluators refuse more. Changed test: the sandbox check "the
  evaluator runs without network" gave way to the stricter checks of the evaluator's box.
- For REPORT.md section 6, the guard (tests: the guard cases of `tests/test_kit.py`; the two port checks in
  `tests/test_ports.py`). No existing test was changed or removed for it.
  1. Code attached to its flag (`bash -c"..."`, `cmd /c"..."`) is checked like a command of its own, under
     `--readonly` too. Was: unread.
  2. The value of PowerShell's `-EncodedCommand`, short forms included, is decoded and checked. Was: unread.
  3. New question: a decoder whose output goes to a shell or an interpreter (`base64 -d | sh`).
  4. A path joined from string literals in a line of code (`Path('data') / 'test'`, `os.path.join`, `+`) is
     resolved like a written one, so a sealed one is denied. Was: passed.
  5. New question: the new text of Write, Edit, MultiEdit, NotebookEdit, or the lines a patch adds, names a
     sealed path or the unsealing token. Not read so: `.md`, `.mdx`, `.rst` files and
     `.claude/nn-training.json`.
  6. New question (a denial where nobody can be asked, as in Cursor's hook): an MCP tool's arguments name
     sealed data inside a longer string. The agent's own tools (Task, WebFetch) are not read so, since a
     task for a subagent may name the sealed folder and the subagent's calls reach the guard as well.
  7. A folder sealed as a whole is walked beyond 20,000 files for up to 5 s of the hook call; a walk that the
     time ends counts as reading (a question). Was: a filtered search passed.
  8. New question: a shell command that names `.git/hooks/...` or `.git/config` (it cannot tell a source
     from a target, so `cat .git/config > x` is asked about as well; `cat .git/config` alone passes).
  Limits to name there: a path with a variable in it passes (literals only); text that merely contains the
  sealed folder's path, a URL for one, is asked about, as it is in a command; item 5 asks about every edit
  that writes such a mention, also when the file held it before.
- Done, step 3, snapshots and the training box: a snapshot keeps sealed files out under wildcard patterns,
  at any depth and behind links (`5563f6c`); the loop checksums such files and hides them from a run
  (`319daf2`); a change that reads `EXP_PROJECT_ROOT` is invalid where a run is not confined (`d8cc1e9`).
  The final state passed `tests/test_loop.py`, `tests/test_kit.py` and `tests/test_review_fixes.py` on
  Windows and in WSL (with bubblewrap); each of the three states passed the loop's unit and sandbox checks
  on Windows. New checks: five at the end of the loop's unit tests, two in its sandbox tests.
- For REPORT.md section 6, snapshots and the loop (no existing test was changed or removed for it):
  1. A snapshot leaves out files sealed by a pattern that begins with a wildcard or has one in the middle,
     and descends as deep as they lie. Was: the git-ignored folder was linked whole.
  2. A link inside the project is judged by the place it leads to. A launch now fails, with the reason,
     where a git-ignored link leads to the project folder or above it, and where sealed paths lie more
     than twelve folders deep in a git-ignored folder (only when the configuration seals something).
  3. The loop checksums the files such patterns seal, so a campaign stops when one of them changes or
     appears, and its sandbox hides each folder sealed that way as one. `loop.link_paths` and
     `loop.eval_writable` are refused where a name below them matches such a pattern. The runs folder is
     left out of that search.
  4. Where a run is not confined (Windows, macOS, Linux without bubblewrap), a change that adds a line
     with `EXP_PROJECT_ROOT` makes the iteration invalid; the worker's rules say so.
  Limits to name there: a tracked link with an absolute target inside the project is copied as it is; a
  launch looks at every file name below the fixed part of a wildcard pattern, for at most 20 s per folder,
  after which the folder's children are linked one by one; item 4 reads the change's text, so a variable
  name built at run time passes.
- Done, step 4, the keep rule, one commit per idea: the seed that screens a change rotates (`92b9419`); a
  pause keeps the line a restart began (`3792686`); a change's own runs cannot lower its margin, and a
  noisy change is tested with its own variance (`be6abde`); a change that is not kept leaves the pooled
  noise again when one of its runs went astray (`1ed9177`). The final state passed `tests/test_loop.py`,
  `tests/test_benchmarks.py`, `tests/test_kit.py` and `tests/test_review_fixes.py` on Windows and in WSL;
  each of the three states before it passed the parts of the loop's tests it touches on Windows.
- For REPORT.md, the keep rule:
  1. The variance a gain is tested against is never below the estimate without the change's own panels,
     and the change's mean is tested with its own variance where that is more than three times the pooled
     one (`OWN`). The confirmation applies the second rule to the kept commit's fresh panel.
  2. The panels of a change that is not kept leave the pool when one score lies farther from the change's
     median than a t multiple (z = 4) of the deviation the other panels give; the ledger row carries
     `unpooled: true`. Not applied where the other panels have no spread.
  3. The first seed of an iteration rotates through the panel; the discard reason names the seed.
  4. A campaign that pauses on the line a restart began puts that line by (`aside` in `state.json`) and a
     `resume` takes it up again; a campaign that ends drops it as before.
  Changed tests, with the reason: the expected first-seed discard text now ends with the seed; in the
  second-panel test the two expected margins follow item 1 (the change's four scores vary more than three
  times the pooled variance; the estimate without the change's panels is the larger one). New checks: the
  rotation, a pause and a resume on a restarted line (campaign r2), the margin's unit cases, `unpool`'s
  unit cases and campaign astray.
  Limits to name there: the simulation covers one iteration, without item 2 and the rotation, and the
  whole-campaign simulation of 12 November was not repeated; a change that is noisier than the runs before
  it is still kept above the nominal rate (7 % where it is three times as noisy, 10 to 14 % before); the
  rule costs 7 points of power at a campaign's first change (61 % for a gain of two deviations, 68 %
  before) and about 2 later.
- Done, step 5, runlog, one commit per idea: the ranks of Lightning's own launcher write no run files
  (`2953f6d`); the two benchmark trainers ask `should_stop()` and still score and save (`3ab4ae4`); a
  training run of the loop that was stopped from outside is not scored (`fd98c12`); a change whose test was
  interrupted can be proposed again (`d8ed0da`). The last two are not from the review: they came up when the
  trainers learned to obey a stop. `tests/test_loop.py` passed whole on Windows and in WSL on the final
  state; `tests/test_runlog_units.py` and `tests/test_benchmarks.py` passed on both with the first two.
- For REPORT.md, runlog and the loop:
  1. The two benchmark trainers end at a stop request or at the launch's deadline and still score and save.
     The fine-tuning trainer's line has no test of its own (the tests run without PEFT); it was run once by
     hand on 14 November, on Windows with the GPU, in a project made by `benchmarks/new_project.py`: launched
     with a budget of 600 s and asked to stop after eight seconds of training, it ended after 105 steps as
     `interrupted`, with `dev/exact` logged and the adapter saved, 22 s after the launch.
  2. `RunLog` writes no run files in a process whose `LOCAL_RANK` or `NODE_RANK` is above zero, unless
     `RANK` is set, which decides alone as before.
  3. The loop does not score a training run that something outside it stopped, whatever the run saved, and
     does not book its end as the change's failure: the campaign pauses with `stop requested: the training
     run ...` and exit code 0. Before, Windows scored the truncated run like a full one and Linux booked a
     crash of the change. The loop asks for the request's file as well, because the Windows supervisor reads
     it only between polls: a trainer that obeys within two seconds leaves `stopped_for` empty in
     `exit.json` there. That gap in the supervisor's record stays; the loop no longer relies on it.
  4. An iteration that a limit or a stop interrupted leaves the list of tried changes, and its hypothesis
     counts as untried (was: proposed again it was a `duplicate`, a failed status).
  New checks: both in campaign b; each was seen to fail on the code without its fix.
- Done, step 6, the remote runner and provenance, one commit per idea: the receipt of a final evaluation
  outlives a removed worktree (`0c4ba73`); the agent ports' files are not experiment source and bookkeeping
  is not a change (`d6ded34`); a resume refuses a changed source (`58e248a`); the launch packs what is sent,
  once, and the controller and the automatic resume send that archive (`20859f6`); a pulled name outside
  the mirror never counts (`89493f4`); a link is judged by where it leads (`e386102`); Windows without
  psutil reads a process's start time from the system (`6d0ecca`); ledger rows booked at the same moment
  all survive (`d64a154`); a snapshot links a file named like a credential (`8ff6f8b`); a target's
  `on_finish` command (`7d9dcc7`). Whole files on the tree of `7d9dcc7`: `tests/test_remote.py` 90 checks on both platforms; on Windows `tests/test_loop.py` 226, `tests/test_review_fixes.py` 38, `tests/test_ports.py` 122, `tests/test_runlog_units.py` 19 and `tests/test_benchmarks.py` 44; in WSL 231, 40, 123, 19 and 44; all pass. `tests/test_kit.py` had one failure there (405 checks pass on Windows, 409 in WSL): `7d9dcc7` was committed with the reference-header check failing, which passed before, because the note on `on_finish` had pushed the Refresh line of `remote.md` out of the first eight lines and only the remote file had been run before the commit. `1141fcd` put the line back, and the kit file passed whole on the next state (409 on Windows, 413 in WSL, three of them new with the probe).
- For REPORT.md, the remote runner and provenance:
  1. The receipts of final evaluations lie in git's common folder (`.git/nn-training-final-eval.jsonl`),
     shared by every worktree of the repository, so removing a worktree no longer takes its uses out of the
     count. The guard asks before a shell command changes that file (three rows of the guard's table in
     `tests/test_kit.py`). `expctl selftest` may write there when it brings older receipts into the shared
     copy.
  2. `AGENTS.md`, `.mcp.json`, `.codex/`, `.cursor/` and `.agents/` are not experiment source: they leave
     the source hash, the snapshots and the remote bundles, so the hash of a project that tracks them, or
     does not ignore them, changes once. The `dirty` list no longer counts the journal, the search's
     storage file, the runs folder or agent configuration, and names untracked files one by one.
  3. `expctl resume` and `nnremote resume` refuse when the source has changed since the launch, unless
     `--allow-code-change` is given; the new manifest carries `resume_of_source_hash`.
  4. A remote launch packs one archive (`remote.bundle_sha256`; `sent_files` counts its files), refuses when
     the source changes while it packs, makes the run folder before the reservation and removes it when the
     launch is refused. The controller sends only that archive. It lies in the mirror until the run ends (a
     `lost` run keeps it until `attach`), so a live remote run takes up to `max_bundle_mb` of local disk. The
     automatic resume after a preemption sends it again; where it is gone, the resume goes by the working
     tree and is refused when that has changed (`remote.not_resumed`). Unpacking uses tar's data filter
     where the Python has one.
  5. A link or a junction is judged by its own name and by the place it leads to: one that leads into a
     sealed path or to a file named like a credential stays at home, and `remote.files` refuses a path with
     such a link below it. A pulled name that leaves the mirror never counts as mirrored.
  6. Ledger rows are appended under a byte lock on Windows, the way the guard writes its log (eight writers
     of 100 rows each: 800 rows, no torn line).
  7. Without psutil, Windows reads a process's start time from the system, in `expctl` and in `runlog`, so
     a process number that went to another process no longer passes for the run.
  8. A snapshot links a file named like a credential (`.env`, `*.key`, `credentials.json`) instead of
     copying it, tracked or not. On Windows without the right to make links that is a hard link, as for
     git-ignored files. The snapshot no longer freezes such a file's content.
  9. New key `on_finish` per ssh target: an argument list, checked at the launch, run on this machine when
     the last pull is complete and no other run of the project on that target lacks its exit record. The
     outcome is in `remote.on_finish`.
  Changed test, with the reason: the check added with `58e248a` that the automatic resume is refused after
  the source changed was replaced in `20859f6`, because that resume now sends the launch's archive and runs.
  New checks: in `tests/test_remote.py` for items 3 to 6 and 9, in `tests/test_kit.py` for items 1, 2, 7
  and 8.
  Limits to name there: `on_finish` was tried with a stand-in command, and no machine was stopped with it;
  it does not run when the controller is gone, so a rented machine still needs its own shutdown timer; the
  Hugging Face route is tested against the stand-in only, as before; file links were exercised in WSL only,
  since this Windows account cannot make them (junctions and hard links were).
- Done, step 7, speed and search, one commit per idea: `expctl env --probe` tries each fast path in a process
  of its own, and `env` lists dated advisories under `warnings` (`dec8971`); the loop checks a change before
  it costs a run and gives an early failure one repair turn (`a4dc52e`); `expctl audit-splits` (`e1cf085`);
  the wiring checks of the sanity gate in `references/validity.md` (`50549c1`); how GPU-hours are counted,
  in `references/loop.md` (`2386068`). Whole files, all passing: on the tree of `a4dc52e`
  `tests/test_loop.py` 235 checks on Windows and 240 in WSL, `tests/test_kit.py` 409 and 413; on the tree of
  `e1cf085` `tests/test_kit.py` 417 and 421, `tests/test_ports.py` 123 and 124, `tests/test_review_fixes.py`
  38 and 40; `tests/test_kit.py` again on Windows after the two reference commits (417).
- For REPORT.md, speed and search:
  1. `expctl env --probe`: CUDA, bf16 autocast, the flash attention kernel, fused AdamW and `torch.compile`
     are tried in the project's interpreter, one process each with a time limit, so a wheel that ends the
     interpreter is a line of the report. It is refused beside a live run. `env` carries `warnings`: dated
     advisories for installed versions (`datasets` below 5.2.0 among them).
  2. Before a run, the loop compiles every changed Python file in the project's interpreter and compares
     syntax trees with the campaign's base. A change that does not compile is a `crash` without a run; one
     that alters only comments or layout is `no_change`.
  3. The identity of a change is the hash of those syntax trees, so a reformatted repeat of an earlier
     change is a `duplicate`. The hashes of a campaign started before this no longer match: such a campaign
     can test once more what it tried before.
  4. One repair turn: after a compile error, or a failure of the first seed within a quarter of the run
     budget (at least 30 s), the worker gets one more session with the end of the run's output (nothing of
     it where a sealed token appears in it). Not for a change that comes with a search. The session counts
     into the campaign's sessions, tokens and money; the ledger row carries `repaired`, the record is in
     `iter-NNN/repair/`. The keep rule is unchanged.
  5. New command `expctl audit-splits [--key FIELD]` and new config key `splits` (name to file or folder).
     It prints counts and a fingerprint per split, never a row; exit code 1 when two splits share a record;
     each audit is a row of the hash-chained `.claude/state/final-eval/split-audits.jsonl`.
  6. New guard rule, for section 6: where the config seals anything, the guard asks before each
     `expctl audit-splits` (a denial where nobody can be asked), because every count of records shared with
     a sealed split is a small look at it; a read-only subagent is denied the command. Tests: three rows of
     the guard's table and the audit's guard check in `tests/test_kit.py`, one row in `tests/test_ports.py`.
  7. The sanity gate of `references/validity.md` names three wiring checks (optimizer membership, the
     gradient and not the weights under weight decay, LoRA's A after two steps), each tried here with
     torch 2.9.1. No `RunLog` method: `RunLog` cannot make a script call a helper, and the gate already
     asked for a gradient on every trainable parameter.
  8. `references/loop.md` says how GPU-hours are counted (a run's duration times the GPUs `nvidia-smi`
     lists) and that the count is too high where a command uses one GPU of several.
  Changed tests, with the reason: three checks of campaign a in `tests/test_loop.py` (the crash of iteration
  6, the number of sessions, the counters), because a repair session now follows that early crash; the
  stand-in agent's plan has no step for it, so it changes nothing and the crash stands, one session, 5,000
  tokens and 0.5 USD later. New checks: nine in `tests/test_loop.py` (campaign f), five for the audit and
  three guard rows in `tests/test_kit.py`, one in `tests/test_ports.py`.
  Limits to name there: the repair turn was tried with the stand-in agent only, not with a live one; the
  compile check covers Python files, a change to a config file goes to a run as before; the audit finds
  exact matches after NFKC, casefold and collapsed whitespace, a lower bound; it refuses Parquet, Arrow,
  HDF5, databases and archives, and counts any other file that is not rows whole; it keeps one digest per
  record in memory; the guard's question reads the command's text, so a script that calls the command is
  not asked about, as with the final evaluation; the fingerprint of a sealed split is printed after the
  approval and identifies records only for a split of very few records drawn from a known pool.
- Decided without a build in step 7, each with its reason:
  - (7) N import checks of every installed package: the smoke run of Phase 1 shows a broken import in
    seconds. N a warning against regularisers in short runs: one campaign's finding in the SOTA report, and
    the keep rule discards what does not gain. A table of verified wheels per GPU class cannot be made on
    one machine: the stack reference names the two builds that passed here.
  - (8) H the stop at a quarter of the budget, as above. Sources read on 2026-11-14, abstracts only: AIDE
    (arXiv 2502.13138 v1) and ShinkaEvolve (arXiv 2509.19349 v1); the debugging step the review places in
    AIDE's method is not in the abstract and was not opened.
  - (9) N a callback for TRL, confirmed in the code: `hf_callback` logs every numeric key of the trainer's
    logs and evaluations and ends training at `should_stop()`, whatever the trainer's subclass.
  - (16) Not built: a data manifest file and a data hash per run at launch (a walk of the data at every
    launch, or a stale manifest that misleads; the fingerprint per split comes from the audit). N
    near-duplicates in the core: the thresholds are per dataset, and the data reference names the tools.
    H the single-feature leak audit: it needs a tabular task to try on, and its source was not verified.
    N a check of timestamp order: project-specific, and the validity reference's item on temporal leakage
    covers it.
  - (16) H controls for the fine-tuning task, against the verdict above. A floor at the majority share is
    wrong for a pretrained model: trained on shuffled labels it still learns the intent names and can beat
    that share through what it knew before, without any leak. The test it needs: three runs on shuffled
    labels (the GPU, about two minutes each in the fine-tuning environment) to set a measured ceiling.
    Not run: usage. N floors computed by the loop where `loop.controls` is missing, for the same reason.
  - (18) N "GPU seconds are overbilled", as under rank 4; the reference now says how they are counted.
- Done, step 8, references, installer and ledger, one commit per idea: the fine-tuning reference names the
  objectives after GRPO and the LoRA scale in a rank sweep (`11ca540`); the optimization reference names
  cautious weight decay and two Muon variants as candidates (`cae1f44`); the performance reference calls
  only the 64B-token run short (`b56207d`); the installer writes an apostrophe of the interpreter's path
  twice inside the agent files' quoted hook command (`00a5eb1`) and adds a later run's paths to the kit's
  block of `.gitignore` (`e376b6c`); the ledger's generator lets the record of what was built outrank a
  reference, and the review is the note `round5` (`7cede64`); README and guide say what the guard reads and
  asks since this round (`850020a`). Whole files, all passing: on the tree of `e376b6c` `tests/test_ports.py`
  125 checks on Windows and 126 in WSL, `tests/test_kit.py` 417 and 421, `tests/test_review_fixes.py` 40 in
  WSL; `tests/test_kit.py` again on Windows on the tree of `850020a` (417).
- For REPORT.md, references, installer and ledger:
  1. `references/finetuning.md`: which objective TRL 1.17.1 runs when a script sets nothing (`loss_type`
     defaults to `"dapo"`, not the GRPO of the original paper); Dr. GRPO, DAPO, GSPO and CISPO by the
     symptom each answers, with their settings in `GRPOConfig`; GDPO and on-policy self-distillation as
     candidates; the LoRA scale in a rank sweep (`lora_alpha/r`, measured with PEFT 0.21.2, and
     `use_rslora`).
  2. `references/optimization.md`: cautious weight decay, Polar Express and NorMuon as candidates, each its
     authors' result; the held line now says which "Cautious" it means (the masked update). The performance
     reference: wording only.
  3. Installer: an interpreter path with an apostrophe ended the single-quoted hook command of the two
     subagent files early, so their frontmatter did not parse. The apostrophe is written twice there, as
     YAML asks; tried end to end with an environment in a folder named `o'c`. The warning about a path with
     a space names a quote too.
  4. Installer: a run that added paths to `.gitignore` after an earlier one wrote the kit's header a second
     time. It adds them under the header that is there; a file that has two headers already keeps them.
  5. Ledger: a reference that covers a row outranked the record of what was built. The record wins now.
     Three rows whose record said "partly built" and five of eight rows that name kit code moved from
     finished to unfinished; the other three of the eight are finished (the `datasets` advisory and the
     split check, both built in this round; the Windows memory setting, reference text by its nature).
     Numbers: 1,505 rows before (Adopt 422, of them 288 finished and 134 not; Trial 224, Assess 314, Hold
     320, Reject 225), 1,594 after (Adopt 458, of them 316 finished and 142 not; Trial 234, Assess 324,
     Hold 324, Reject 254). The note `round5` has 89 rows: 36 adopted, all built; 10 Trial; 10 Assess; 4
     held for the user; 29 rejected.
  6. README and guide: the guard's new questions, what it reads in a call and where that ends, the walk of
     a folder sealed as a whole (the README still said that such a search passes), what counts as a run's
     source, and the platform row for the evaluator's read-only project.
  New checks: two in `tests/test_ports.py`; on the code before, both fail (123 pass). No existing test was
  changed or removed in step 8.
  Limits to name there: the papers were read as abstract pages and the settings come from TRL's config file
  at v1.17.1; no result was reproduced and no objective was run. The candidates in the two references are
  Trial rows. Seven Assess rows list what the review named and this round did not open (further RL
  objectives, trainer and generator parity, distillation and preference objectives, adapter options,
  optimizers, low-precision and kernel items, architectures): nothing about them is verified. No fetched
  page tried to give an instruction.
- Decided without a build in step 8, each with its reason:
  - (11 to 13, 17) N a qualification of Schedule-Free AdamW in SKILL.md: SKILL.md already calls it, Muon,
    SOAP, warmup-stable-decay and muP controlled alternatives to test against the baseline, not defaults.
    N `RunLog.check_rlvr()`: `hf_callback` logs those metrics already and the reference says what to read;
    the thresholds are the review's own, without a source. N routing for tabular models and prompt
    optimisation, as in the verdict.
  - (19) N folded YAML, a licence file, the removal of this checkout and a `doctor` command, as in the
    verdict; `env --probe` and the warnings of `env` are this round's addition to the last.
  - (14, 15, 20 to 22) U, four Hold rows: ports for Antigravity and Gemini CLI, the proposed MCP servers,
    cloud drivers, a container as the box. N new skills and the rebuild as six "planes", as in the verdict.
- Done, step 9: the full tests on the tree of `850020a`, all seven files in three interpreters per platform,
  all passing. Default interpreters: 968 checks on Windows (benchmarks 44, kit 417, loop 235, ports 125,
  remote 90, review_fixes 38, runlog_units 19) and 980 in WSL (44, 421, 240, 126, 90, 40, 19); 866 and 874
  at the public commit.
- Done after the nine steps: the control for the fine-tuning task (`2071d99`). `benchmarks/finetune/
  controls.py shuffled` trains the shipped script on the training messages with their intents dealt out
  again at random: 0.012, 0.023 and 0.008 exact answers on seeds 1 to 3 and 0.011 with a learning rate of
  1e-3, against 0.35 to 0.39 for the script as shipped. Floor 0.05, in `loop.controls` of the task's
  config; the loop's self-test trains it once before a campaign's first session, as one run of the run
  limit (tried with the stand-in agent: 4 runs, 283 s, passed).
- Done: the independent review. One fresh subagent (Opus) with a throwaway clone at `850020a` and a brief
  that says what the guard, the snapshot, the loop and the two practice evaluators must guarantee; it took
  the place of the deep-sweep-red-team skill (usage limit). It ran 14 probe scripts on native Windows and
  reported nine findings and four of lower weight. All are fixed, one commit per idea, each with checks
  that state what the code did before:
  1. a hook input nested too deeply to read ended the guard with exit code 1, which Claude Code takes for a
     hook that failed (`5aff688`): refused now, and any error the guard's main function does not catch ends
     as a refusal;
  2. git settings that make git start a program (`13dd89f`): asked about; the kit's own git calls switch
     `core.fsmonitor` and the hooks path off;
  3. `git add -f` and `git stash --all` over sealed files (`cc2bfbe`): asked about;
  4. spellings of a sealed path that a shell resolves, a backslash, `$'..'`, a brace list, PowerShell's
     escape character (`f7ed572`): every rule also runs on the line as each shell would take it;
  5. decoded text that reaches a command without a pipe (`826222d`): asked about;
  6. Python literals side by side, and fixed counts behind which the guard stopped reading (`70a4aeb`,
     `d8d34c1`): joined, and no count decides what is checked;
  7. a notes file run as code (`84d7360`): asked about;
  8. `du -a` and tree walks in code on the line (`4e204eb`), and an MCP tool handed a folder with sealed
     files (`cd75002`): asked about;
  9. the character-model evaluator scored a model that reads its own scoring file (`079d1f0`): every code
     entry of a model file is read as tokens, PyTorch loads an archive the evaluator wrote itself, and every
     call goes to a fresh copy;
  10. a junction gave sealed files a second name under which a snapshot copied them, and a sealed pattern in
      another case than the folder on disk did not match in the run tools (`4842b81`): a snapshot and a remote
      run's archive judge a file by its real place, and the run tools read path patterns without case where
      the filesystem ignores it.
- Found while fixing, and fixed in the same commits: text handed to a nested shell was checked only from the
  folder the line starts in (`cadf196`); code on a runner's standard input was not read (`4e204eb`); the
  evaluator loaded a second directory of a model file that its check had not read (`079d1f0`); a snapshot
  made an absolute link to a folder again as it was (`4842b81`); and where the sealed folder is itself a link
  to storage outside the project, a second link to that storage, to the first link or to the sealed folder
  brought sealed files into a snapshot, in six of six layouts of my probe (`4842b81`).
- The public version has most of these faults. Tried on `60cc0b0`: the junction, the linked storage, the
  case of a pattern, the nested folder, the standard input and the model file's forms.
- Changed checks since `850020a`: in `tests/test_benchmarks.py`, two models that keep something between
  calls are scored as the fair model, where they were refused (every call now goes to a fresh copy); one
  row of `tests/test_kit.py` that this series had added itself was made stricter. No guard check that
  existed before the round was changed or removed.
- Not done about the review: no second reviewer saw the fixes (usage limit). Limits kept and documented
  (README "Notes and limits"; REPORT.md "Round 5"): making a junction or a link is not asked about; a link
  inside a git-ignored folder is not looked into when the sealed pattern begins with a folder's name; a
  sealed pattern written as an absolute path does not keep a git-ignored link to its folder out of a
  snapshot; names and programs that are put together at run time.
- The full tests on `b48d606` (README, guide and the guard's description after the fixes) failed two checks
  of `tests/test_kit.py` in WSL. Every other file passed there in three interpreters, and on Windows the
  default interpreter (1,168 checks) and the clean 3.11 passed all seven files; the 3.8 run of that commit
  was stopped for the new code. Both failures were faults of the kit, older than the round and in the public
  version. Neither shows on Windows, where the fixes after the review had been run while they were made:
  1. `guard Bash {"command": "python -c \"a0 = 'v0';... -> ask (want deny)`, all three interpreters. Where
     `final_eval_commands` is set, the guard looks every word of a command up as a file, and on Linux and
     macOS that raises for a word of more than 255 bytes (OSError 36, File name too long): the check ended
     as an internal error, a question for a harmless line and for a line that must be refused. Fixed in
     `d857607`: such a word names no file (`there()` in `nn_guard.py`); two new rows in the guard's table.
     Only that error is taken so; another error of a lookup still ends as the internal-error question.
  2. `session hook injects status after compaction`, the default interpreter only, and not in two later
     runs. `expctl` told a run from a later process with its number by the start time, which on Linux is
     the boot time plus ticks and moves when the system clock is set. In that WSL session the clock was set
     back about 2.5 s every 30 s (the distance between wall clock and time since boot fell by 4.955 s in
     66 s), and the test's two live runs read as lost 36 s after their launch. Fixed in `9d6f876`: on Linux
     `pid.json`, the manifest that `RunLog` writes and a remote run's two process records carry the boot's
     id and the start tick (`proc_key`, `supervisor_key`), and those decide where a record and the system
     both have them; the time decides otherwise, as before. One new check, with a recorded start a minute
     off.
- After those two fixes, each was checked in WSL against the code before it, and the second one changed
  once more:
  1. The three commands with a long word, asked of the guard at `7c6a120` and at `a135bea`: before, the
     internal-error question for all three; after, a refusal for the `python -c` read of a sealed path, and
     the other two allowed.
  2. The full tests at `a135bea`: WSL passed in all three interpreters (1,184 checks in the default one).
     On Windows the default interpreter passed all seven files (1,171); I stopped the run in the clean 3.11
     for the change of item 5.
  3. The fix of a run's identity under WSL's own clock: one run that only sleeps per kit (`7c6a120` and
     the new code), each read by its own controller every 30 s. First session (new code `a135bea`): 181 s
     after the launch the clock had been set back by 5.431 s; the old code read its run as lost, the new
     one as starting. Second session (new code `827c35c`), with each guard asked about a `Write` into its
     run's folder: both refuse at the launch; after 211 s (6.599 s) the old code reads lost; at the end
     (7.570 s) the old guard lets the `Write` pass and the new one refuses it. The guard takes its live
     runs from `expctl.scan` (`Ctx.active()` in `nn_guard.py`), so the fault ended the protection of the
     run as well, in the public version too.
  4. The clock of this machine's WSL, measured in six sessions on 14 November: still at first, then set
     back in steps of one to three seconds, 2.7 to 4.5 s a minute, beginning one to three minutes after
     the virtual machine's start. Load is not the cause: the run at `a135bea` started with nothing else
     of mine running, and its clock was set back by 74.9 s in 20.5 minutes (in the run at `827c35c`: by
     66.6 s in 20.3 minutes). My earlier reading, also told to the user in chat,
     was wrong. Clock source `tsc`; Hyper-V's time synchronisation and `systemd-timesyncd` both active;
     not looked into further. Round 2's two clock faults fit: about two minutes after a start.
  5. A reader inside a time namespace with a boot-time offset (`unshare --time --boottime 1000`) sees
     another start tick for the same process, while the start time reads the same. With `9d6f876`, where
     the key decided alone, such a reader took a live run for lost, which the rule before the round did
     not: a narrow step back in the protection of live runs, found by my own check. Repaired in `827c35c`:
     a key that matches says "the same process"; in every other case the start time decides as before the
     round. The check that `9d6f876` had added was changed with it. Tried in that namespace before and
     after; `tests/test_kit.py` and `tests/test_remote.py` on Windows and the kit file in WSL passed with
     the change before the commit. Open: such a reader after a clock set of five seconds reads the run as
     lost. Not tried: a clock that is set forward.
- Done: the full tests on the final code, `827c35c`, all seven files in three interpreters per platform:
  no check failed. Default interpreters: 1,171 checks on Windows (benchmarks 50, kit 610, loop 238, ports
  126, remote 90, review_fixes 38, runlog_units 19) and 1,184 in WSL (50, 614, 244, 127, 90, 40, 19); 866
  and 874 at the public commit. The clean interpreters: 1,163 (3.11) and 1,162 (3.8) on Windows, 1,176
  (3.12) and 1,175 (3.8) in WSL: 42 checks in the benchmarks file without PyTorch, and one check of the
  ports file fewer under 3.8. The WSL run went under a clock that was set back by 66.6 s while it ran.
- Done: REPORT.md, "Round 5", and the ledger (`7c6a120`, `a135bea`, `a31f632`): 1,609 rows; Adopt 474, of which 332 are
  finished and 142 are not; Trial 233, Assess 324, Hold 324, Reject 254. The note `round5` has 104 rows: the
  review's 89 claims (37 adopted, 29 rejected, 9 Trial, 10 Assess, 4 Hold), 13 rows for the fixes after the
  independent review and two for the faults of the full test run, all adopted and finished. Round 4's Trial
  row about two controls for the fine-tuning task stays Trial for the untrained adapter; shuffled intents is
  the finished `round5` row.
- The sixth installer run on the real install (14 Nov, on the user's "Yes, run it"), which brought it
  round 5. From a clean clone of the public commit `2666faf`; its installed files are those of `827c35c`,
  where the full tests last ran, and sixteen of them differ from the kit of the fifth run. The steps of the
  fourth and fifth runs. A read-only look first: the install was as the fifth run had left it (272 files
  listed, none added or removed, one changed: the guard's record, by my own calls after that run), no run
  was live, and the guard's record had last been written at the time of those calls. New in the look: the
  `selftest` of round 5 copies receipts of final evaluations into git's common folder, which there lies
  outside the install. None of that repository's eleven checkouts holds a receipt, so it had nothing to
  write there, and the shared record does not exist after the run either. Then a rehearsal on a fresh copy
  of its kit files, a dry run, and the run at 14:55 UTC. Replaced, each with a backup in a new folder
  under its `.claude/backups/`: sixteen kit files (the guard, the four scripts, SKILL.md, nine references,
  one agent file) and the manifest; the installer's other sixteen files were up to date. Config, settings,
  CLAUDE.md, .gitignore, journal and runs are unchanged. `expctl selftest` passes with the two optional
  checks failing that failed before (the missing metric, 9 of 10 other checkouts without the guard); its
  new check of the final-evaluation record passes. `status` gives the same answer with the old and the new
  `expctl.py`: five runs, four completed, one failed, no alert. The guard's answers to twenty made-up
  calls, asked before and after with its own config: the twelve of the earlier runs are the same. Of eight
  new ones, four went from allowed to a question (a Write of a `.py` file whose text names a sealed
  folder, `git add -f .` at the root, `git -c core.hooksPath=hooks status`, `expctl audit-splits`), a
  `python -c` that joins a sealed path from literals went from allowed to refused, a `cat` of a sealed
  file in `bash -c"..."` from a question to refused, and two controls stayed allowed (the folder's name in
  a `.md` file, a harmless `.py` file). The 27 kit files there are the kit's, five of them apart from the
  lines that name the interpreter. Snapshots are off there, and none of the agent files that left the
  experiment source exists at its root. Left there: the seventeen files, changed and not committed (that
  repository's 418 other status entries untouched, nothing staged), the backup folder, and 28 lines in its
  guard record, 24 of them marked `upgrade-check`. Not done there: its scripts, a launch, a final
  evaluation, an agent session, `--worktrees`, a count of its files, and its source hash before and
  after. REPORT.md, "Round 5", "The sixth installer run on the real install".

## Not done, and why
- Live checks: Codex (hooks need trust in `/hooks`), Cursor terminal agent (not installed), Hugging Face Jobs
  (needs the user's go-ahead for a paid job), the loop with Claude Code in WSL (the CLIs there are old and not
  signed in).
- 142 adopted rows are unfinished (134 before round 5, whose check of the ledger moved eight rows there),
  and of the Trial and Assess rows only round 2's three built items were tried (usage limit). ROUND2.md gave
  the go-ahead for all of them; what was built first is what the live campaign and the review pointed at.
  The first three items of my order are built (round 3), and the first four of the ranked list of 12
  November (round 4). Of the order after round 4, round 5 built the repair attempt after a crash and lifted
  the guard's file bound for a folder sealed as a whole, and the control for the fine-tuning task. My order
  for what remains: a second reviewer's look at the fixes after round 5's independent review, on Linux
  this time (both faults of the round's last test run show only there); a
  guard walk that skips the folders no sealed pattern can match, so that the bound goes for patterns that
  begin with a wildcard too; containment of each run's processes (a process namespace under bubblewrap,
  which first needs the heartbeat's process number left out or translated for boxed runs; a job object on
  Windows); then a minimum agent version, the readiness report and a checkpoint helper.
- Round 5 with a real agent: the repair turn, the compile check and the rotation of the screening seed ran
  with the stand-in agent of the tests only. `on_finish` ran a stand-in command; no machine was stopped
  with it. The evaluator's box exists on Linux with bubblewrap only. File links were exercised in WSL only.
  The fixes after the independent review are checked by my own probes and tests, not by a reviewer, and
  the reviewer ran on native Windows only. The same holds for the three commits after the full test runs
  (`d857607`, `9d6f876`, `827c35c`). Not tried: a clock that is set forward, and a Linux machine other
  than this WSL. Left as they are, and not tried under a clock that is set: the age of a heartbeat and the
  guard's five seconds for its own searches, which both read the wall clock; what else in the kit reads it
  was not looked at.
- Round 5, not opened (usage limit), seven Assess rows of the note `round5`: further RL objectives, parity
  between trainer and generator, distillation and preference objectives, adapter options, further
  optimizers, low-precision and kernel items, architectures. The papers behind the new reference text were
  read as abstract pages, and no result was reproduced.
- On the real install, which has round 5 since the sixth installer run: the seventeen files that run
  changed are not committed in that repository, and the record of the run is not pushed ("Questions for
  the user"). The new guard was asked made-up calls there; no agent session, script, launch or final
  evaluation ran, and its source hash was not computed before and after.
- Round 3's three items are not shown to raise results with a real agent. Each ran with the stand-in agent
  of the tests only: no real agent session, no pilot on the fine-tuning task, and that task ran on native
  Windows only. Round 4 ran the trial that the search's ledger row names (campaigns with and without, at an
  equal run limit) with the stand-in: a gain on the fine-tuning task, none on the character model. The
  trials for the restart and for the new task's starter were not run.
- The harness's check before it writes searched values does not catch a process that swaps the file in the
  instant between the check and the write (REPORT.md, "Round 3", "What was reduced"). Closing it needs the
  file opened through directory handles on Linux, or a process namespace for bubblewrap runs. Not built.
- The three repairs of 13 November were not tried on a real rented job, on a real `ssh` target or beside a
  virus scanner: their checks make the refusals and the vanishing folders themselves. `bundle` in
  `nnremote.py`, the listing on the launching side, still uses `rglob`: it reads the paths that the config
  names and the directory of a run that has ended. The same holds for round 4's fixes beside them.
- Round 2's changes are not shown to raise results: one live campaign, whose confirmation ended `unclear`.
  The kit has run with a real agent on one task, with Claude Code on native Windows. Not run: a second task,
  another agent, WSL.
- Limits the review left, each documented (README "Notes and limits", Reject rows): sealed files that git
  tracks, a wrapper script around the final command, a confirmation fooled by a faked small spread, a forged
  guard record.
- On the real install: neither registered script and no final evaluation was run. The user names the run to have
  one. It has round 2's fixes since the third installer run, and those sixteen files are committed there.
  Its never-read cache folder is sealed since 12 Nov, and that config change is committed there too. It has
  rounds 3 and 4 since the fourth installer run of 13 Nov, and the fifteen files that run changed are
  committed there. It has the status fix since the fifth run of the same day; the two files that run
  changed are not committed there.
- The guard's kept gap (a plain `grep -r`, `find` or `ls -R` started at the project root was not questioned)
  is closed in round 4, and on the real install since the fourth installer run. What stays is the file
  bound: the guard looks at no more than 20,000 files per folder it walks, and a sealed file beyond them is
  not seen (README "Notes and limits"; "Round 4" above). Round 5 lifted it for a folder sealed as a whole,
  which is walked on for up to five seconds; it stays for patterns that begin with a wildcard, and the real
  install does not have round 5. The gap for other checkouts is closed in round 2,
  and on the real install since the third installer run.
- Found on the real install and built in round 4 (`43adda1`), installed there since the fourth installer
  run: for a search of the whole project by the search tool, the guard walked up to 20,000 files once per
  sealed pattern that begins with `**/` (`reaches_sealed`). That install has five, and the check took about
  2 s there against 0.3 s for other calls; two more brought it to 2.95 s. The kit's guard now walks each
  searched folder once: measured there after the run, that check takes 0.6 s.
- Not looked into on the real install: why its guard allows the Grep and Glob tools over the whole project
  while it asks about `grep -r` at the root (the same answer before and after the fourth run, and what the
  kit's rule gives where ripgrep itself stays away from the sealed files); and which of its ten other
  checkouts has a guard entry, which the self-test's count of nine without one implies.
- The PyTorch pin in `references/stack.md` is not shown to work on a GPU here; the reference says so.
- The repository on GitHub is public since 13 Nov ("After the guide"). Left with the user: the name on the
  licence and in later commits (now the account's name); the private repository of the first upload,
  `nn-training-harness-dev-history`, to delete or keep; and the setting of the GitHub account that refuses
  a push which would expose the private e-mail address (Settings, Emails). It is recommended, and only the
  user can turn it on.
- The fix for checkpoints recorded on another machine (`0450067`) is not tried on a real remote run or on a
  moved project, only on a rewritten record. The real install has it since the fifth installer run, where
  it shows nothing yet: that project's list of best runs is empty, because its config names no metric.
- The fine-tuning practice script ran on native Windows only, with one seed, and the commands of the guide's
  scenario A were not run on Linux.

## Questions for the user (one batch, with the report)
- Answered on 11 Nov: the Claude Code CLI on Windows is signed in; the real install is upgraded.
- Answered on 12 Nov: the real install is upgraded again, to the kit with group A.
- Hugging Face Jobs: account with credits, a spending cap, and a go-ahead for one paid canary under $0.10.
- Update Claude Code in WSL (2.0.76 and 2.1.165) to 2.1.321 or newer and sign it in, for loop runs on Linux
  (Windows updated itself to 2.1.322); install Cursor's terminal agent, and whether a container may be used for a
  Cursor loop test (Cursor edits unattended only with `--force`).
- Whether Docker Desktop should be started for container tests.
- Codex: approve the kit's hooks once in `/hooks` of a test project, or allow
  `--dangerously-bypass-hook-trust` in temporary test projects, for a live Codex check and a real hook payload.
- The real install: which registered script or which final-evaluation entry to run, on which run, if any.
- Answered on 12 Nov: the round-2 prompt is run here, and with it the guard covers every registered worktree.
- Answered on 12 Nov: the installer ran on the real install a third time; and the first three items of the
  order under "Not done" were built in a session the user started ("Build the kit's next three items"): round
  3 above.
- Answered on 12 Nov: the sixteen kit files that the third installer run changed are committed in that
  repository, as after the second run.
- Answered on 12 Nov, looked into on the user's "Yes, look into it": the folder that the first entry of its
  `sealed_paths` names is absent on purpose. That project's own documents say its hidden final test set was
  never downloaded, the entry seals the place where it would land, and a search by name of all eleven
  checkouts found no data of that name. Its other final test is a split label in files that training also
  reads, gated by its loader and a sealed token; no path pattern can seal that. Read-only look, nothing run
  or changed there, its guard record unchanged. Helper scripts: `%TEMP%\nnkit-upgrade\real5*`.
- New from that look: a git-ignored cache folder in a sibling worktree holds four files that the project's
  plan calls never read, and no sealed pattern covered it (its guard allowed a read, asked with a made-up
  call).
- Answered on 12 Nov, on the user's "Yes, seal it": that folder is the ninth entry of `sealed_paths` there,
  as one plain pattern (its guard maps a path in any checkout back to a repository path, and each `**/` form
  would cost that guard a further walk on every search of the whole project). Asked with eight made-up calls
  through the registered command before and after: a read of a file in the folder, a Python read in the
  shell and a search of the folder went from allowed to refused, a `grep -r` over the folder above it from
  allowed to a question, and the four controls stay allowed. Changed there: the config (one line) and four
  lines in its guard record, marked `seal-check`. Nothing else: no run, no self-test, no entry in its
  journal. The seal binds sessions that run in the install; the worktree that holds the folder has no kit
  config. Helper: `%TEMP%\nnkit-upgrade\real5_seal.py` (show, ask, match, cost, edit, check).
- Answered on 12 Nov, on the user's "Yes, commit it": that config change is committed in that repository,
  one local commit of that one path, not pushed (undo with `git reset --soft HEAD~1` there while it is the
  newest commit). The files on disk and the guard record are as they were before it. Helper:
  `%TEMP%\nnkit-upgrade\real5_commit.py`.
- Open, from round 3: whether to spend usage on a campaign with a real agent on the fine-tuning task with
  `loop.search_trials` set (about 40 runs of 44 seconds plus the sessions). It would show whether an agent
  uses the search offer as meant, not a gain.
- Open, from round 3: this machine's own Transformers install does not import (transformers 4.57.3 refuses the
  installed huggingface-hub 1.15.0, and an empty leftover folder `bitsandbytes` lies in its site-packages).
  Repair it or leave it; nothing in the kit needs it. On 13 Nov that folder stopped the first fine-tuning
  run of a fresh temporary environment ("After the guide"); removing it is the user's to do.
- Open, from round 3: what to build next (the rest of the order under "Not done").
- Answered on 13 Nov, on the user's "Yes, repair them": the three small faults seen beside round 3's two are
  repaired ("Round 3" above).
- Answered on 12 and 13 Nov: the first four items of the ranked list are built, and round 3's conclusion is
  checked ("Round 4" above).
- Answered on 13 Nov ("Update my install"): the fourth installer run on the real install is done ("Round 4"
  above). It brought rounds 3 and 4, the guard's question at the root among them, so an agent that explores
  with `grep -r` at the root meets questions there.
- Answered on 13 Nov, on the user's "Yes, commit there": the fifteen files that run changed are committed
  in that repository, one local commit of exactly those paths, not pushed (undo with `git reset --soft
  HEAD~1` there while it is the newest commit). The files on disk and the guard record are as they were
  before it. `runlog.py` was among the changed files this time: its 20 public names and their call
  signatures are those of the version it replaced, so the binding check of 12 November on that project's
  scripts was not repeated. Helper: `%TEMP%\nnkit-upgrade\real6_commit.py`; the message is
  `real6-commit-msg.txt` there.
- Open, from round 4, as a decision of its own: `install.py --worktrees` on the real install. The
  repository has eleven checkouts, and the install's self-test counts nine of the other ten without the
  guard.
- Open, from round 4: whether to build the index of sealed files that lifts the guard's file bound, and
  whether I may count the files of the real install (per checkout and below its sealed folders, nothing
  opened), which would say whether the bound matters there.
- Answered on 13 Nov by the request for fixes: the practice projects list a best run in `expctl status`
  ("After the guide").
- Answered on 13 Nov ("Yes, make it public"): the repository is public, from one new commit, with an MIT
  licence and with the records under `docs/upgrade/` ("After the guide").
- Answered on 13 Nov ("Yes, run it"): the installer ran on the real install a fifth time, for the fix of
  `expctl status` ("After the guide").
- Answered on 14 Nov ("Yes, commit there"): the two files that run changed are committed in that
  repository, one local commit of exactly those paths, not pushed, its parent the commit that was newest
  before (undo with `git reset --soft HEAD~1` there while it is the newest commit). That repository's 418
  other status entries are untouched and nothing is staged. Where these records say the two files are not
  committed, this entry replaces it.
- Answered on 14 Nov ("Yes, push"): the records of that run are pushed to the public repository.
- Answered on 14 Nov by the request itself (review the other model's recommendations, build a plan from
  them, carry it out): "Round 5" above. The request covers changes in this folder and local commits. It is
  not a word for a push, for an install, or for anything on the real install.
- Answered on 14 Nov ("Yes, push", to the question whether round 5 should be pushed to the public
  repository): `main` is pushed, 74 commits on top of `60cc0b0`, the one with this entry among them. Only
  `main` was pushed. Before the push every added line and every commit message of the round was looked
  through for private details (paths of this machine, addresses, time zones, times of day, the names on the
  real install's path): none found, and every commit carries the no-reply address and a date in UTC. The
  word covers this push; a later one needs a new word.
- Answered on 14 Nov ("Yes, run it"): the installer ran on the real install a sixth time, which brought it
  round 5 (the last entry of "Round 5"). An edit there whose text names a sealed folder now asks. None of
  the agent files that left the experiment source exists at its root.
- Open, from that run: committing the seventeen files it changed in that repository (helper:
  `%TEMP%\nnkit-upgrade\real8_commit.py check | commit MSGFILE`), and pushing the record of the run, which
  is in the local repository only.
- Open, from round 5, each an install, an account or a paid resource: ports for Antigravity and Gemini CLI
  (neither agent is installed here), the MCP servers the review proposes, cloud drivers beyond `ssh` and
  Hugging Face Jobs, and a container as the box for training and evaluation (Docker Desktop, asked before).
- Open, from round 5: whether to spend usage on a campaign or a second pilot with a real agent, now with the
  repair turn and the compile check to try as well, and on a second reviewer's look at the fixes after the
  independent review. (The control for the fine-tuning task, asked about here before, is built.)
- Open, from round 5: what to build next (the order under "Not done").

## Working notes
- Temporary work folder on Windows: `%TEMP%\nnkit-upgrade` (test scripts, clean virtual environments, logs, the
  loop run, the upgrade test). In WSL: `~/nnkit-upgrade` (not `/tmp`, which is emptied at every start).
- Run install.py and expctl only against temporary test projects, never against this folder.
- Tests: `python tests/<name>.py` for test_runlog_units, test_kit, test_review_fixes, test_ports, test_loop,
  test_remote, test_benchmarks; each prints PASS/FAIL lines and `RESULT: ALL PASS`. Wrapper scripts for the
  three interpreters per platform, each run as `<script> <label> <commit>` on a clean clone of that commit:
  `%TEMP%\nnkit-upgrade\win-tests.sh` and `wsl-tests.sh`; logs in `%TEMP%\nnkit-upgrade\logs\`.
- In two full runs in WSL the clock went back during `test_remote` of the first interpreter, by half a second
  and by about two seconds (my reading: the virtual machine corrects its clock a few minutes after it
  starts). Two faults in `nnremote` showed only there. Read a failure in WSL's first interpreter with that in
  mind, and do not dismiss it: both were real.
- Fine-tuning task: the system Python cannot import Transformers (see the questions above), so its runs use a
  temporary environment (Python 3.11, PyTorch from the system, Transformers 5.22.2, PEFT 0.21.2). Windows
  clears `%TEMP%`, and the one under `%TEMP%\nnkit-upgrade\ft-venv` had lost files by 13 Nov. To build it
  again: `uv venv --python 3.11 --system-site-packages DIR`, then, with `uv pip install --python
  DIR\Scripts\python.exe`, first `transformers==5.22.2` and then `--no-deps peft==0.21.2
  bitsandbytes==0.50.2`; `--no-deps` keeps a second PyTorch out, and the real `bitsandbytes` shadows the
  empty leftover folder of the system Python. The base model lies in `benchmarks/finetune/model/` in the main
  checkout (270 MB, git-ignored, fetched by `fetch_model.py`); a worktree needs its own copy. Work folders
  of round 3: `%TEMP%\nnkit-upgrade\ft` (direct runs) and `ft-loop` (the loop campaign's project and the
  stand-in agent's plan). Do not change the system packages.
- Since round 3 a full run takes about 40 to 50 minutes on Windows and 13 in WSL. `tests/test_loop.py` alone
  took 6 to 11 minutes on Windows; the wrappers allow 20 minutes per file. This Windows account may not create
  symbolic links, so the link checks of `tests/test_loop.py` use a hard link and a junction there; in WSL they
  use symbolic links, under bubblewrap.
- Both faults of round 3 showed in a full run on Windows under the clean Python 3.8 and nowhere else, once
  each. For a check that fails once in many runs: `%TEMP%\nnkit-upgrade\hf-try.py KIT N KEEP` repeats the
  first rented-job check of `tests/test_remote.py` up to N times and keeps the files of the first run that
  fails (the run's mirror, the stand-in's job folders and its call log). That is how the `runlog.py` fault
  was found: the kept run's `stdout.log` held the traceback. In the same folder: `rl-race.py SCRIPTS N`
  starts N RunLogs beside a process that copies every file; `co-race.py SCRIPTS SECONDS` calls `copy_out`
  while folders are created and removed; `sl-try.py KIT SECONDS CALLS [busy]` asks for the state of a live
  run of `tests/test_kit.py`'s project again and again, with `busy` without a pause, which is how the
  `expctl.py` fault showed; `rd-race.py SECONDS [PAUSE_MS] [busy]` counts refused reads of a file that
  another process keeps replacing.
- A check that compares a state with `running` prints nothing else when it fails: "statusline leaves the run
  alive" in `tests/test_kit.py` did not say which state it saw.
- To see a new check fail on the code before its fix: unpack the commit before it with `git archive` into a
  folder under `%TEMP%\nnkit-upgrade`, copy the changed test files over it and run them there.
  `%TEMP%\nnkit-upgrade\r3e-narrow.sh TREE LABEL PYTHON...` does those runs for the three test files that
  the repairs of 13 November changed, once per interpreter.
- Round 4's helpers are in `%TEMP%\nnkit-upgrade\top4-tools\`. `bound_probe.py KIT`, `bound_probe2.py KIT`
  and `bound_probe3.py KIT` build made-up projects with 19,000 and with 20,500 files in front of a sealed
  file and ask the guard (the file bound). `report_cases.py` asks the guard before and after with the
  report's 153 examples. `measure_stats.py WORK` computes the measurement's figures from `charlm.json` and
  `finetune.json` in `%TEMP%\nnkit-upgrade\search-measure`. `apply_edits.py FILE EDITS.py` applies exact
  replacements to a file, each of which must occur once, or writes nothing. The session records of the live
  `--worktrees` checks are there too (`live-wt2-stream-*.jsonl`, `live-wt3-stream-*.jsonl`); the throwaway
  projects themselves and this round's worktrees are removed.
- Since round 4 a full run takes about 53 minutes on Windows (`tests/test_loop.py` 8 to 12 minutes per
  interpreter). On 13 Nov, with nothing else running, it took 34 minutes on Windows and 15 in WSL. A
  wrapper run that is stopped leaves its test process behind on Windows (`timeout.exe` and `python.exe`
  with `kit/tests/test_*.py` in the command line): end that tree before the next run, which uses the same
  clone.
- git's notices about line endings ("LF will be replaced by CRLF") can fill the head of a command's output
  on Windows: filter them out by their text, not by cutting the output.
- The fourth installer run's helpers are in `%TEMP%\nnkit-upgrade`: `real6.sh STEP` (state, before,
  rehearse, dry, calls before|after, compare, install, verify, same, aftercommit), `real6_calls.py` (twelve
  made-up calls to the install's guard; it prints decisions and seconds only), `real6_logcount.py` and
  `real6_commit.py check | commit MSGFILE`. The results are `real6-*.json` and `real6-*.log` there, the copy
  of the install's kit files from before the run is `real-install-before-20261113`, and the kit clone that
  the installer ran from is `kit-7a38b98`.
- The session of the fourth installer run worked in a worktree of the kit under `.claude/worktrees/`. Such
  a worktree matches the pattern that PROMPT.md gives for the real install. The `real6*` helpers therefore
  take only a folder that has the kit's manifest and no `install.py`; the older `real4*` and `real5*`
  helpers stop with "installs found: 2" while such a worktree exists.
- The fifth installer run's helpers are in the same folder: `real7.sh STEP` (the steps of `real6.sh`),
  `real7_status.py BEFORE` (status with the old and the new `expctl.py` on the install's records, counts
  only) and `real7_commit.py check | commit MSGFILE` for its two files. The results are `real7-*.json` and
  `real7-*.log`, the copy of the install's kit files from before the run is
  `real-install-before-20261113-fifth`, and the kit clone that the installer ran from is `kit-920bddd`.
- The sixth installer run's helpers are in the same folder: `real8.sh STEP` (the steps of `real7.sh`; its
  `state` and `same` also run `real8_pre.py`, which counts the receipts of final evaluations in that
  repository's checkouts and says when the guard's record was last written), `real8_calls.py` (the twelve
  made-up calls and eight for round 5), `real8_clone.sh`, and `real8_commit.py check | commit MSGFILE` for
  its seventeen files, which finds the run's backup folder by itself. The results are `real8-*.json` and
  `real8-*.log`, the copy of the install's kit files from before the run is
  `real-install-before-20261114-sixth`, and the kit clone that the installer ran from is `kit-2666faf`.
- A session that ends on an error leaves its last exchange only in its saved transcript, under
  `~/.claude/projects/<this folder's path, with dashes>/<session id>.jsonl`. The first session's is 263 MB:
  read its tail with a script, not whole.
