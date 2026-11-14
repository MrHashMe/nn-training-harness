# Upgrade report: nn-training harness kit

Work of 10 to 14 November 2026 on the kit of 23 October 2026 (baseline commit `5ea9659`). Written for a reader
who has not seen the work. Requirements: `docs/upgrade/PROMPT.md`, and `docs/upgrade/ROUND2.md` for the second
round of 12 November, which has its own section right after "Read this first". A third stretch of work on the
same day built three items that round 2 had left open, and on 13 November repaired three small faults it had
come across: its section, "Round 3", follows "Round 2". A fourth, on 12 and 13 November, built the first
four items of a ranked list of improvements and looked at round 3's repairs again: its section, "Round 4",
follows "Round 3". Its last part, "The fourth installer run on the real install", was done and written on
13 November in a later session. That session then wrote the guide ("After round 4") and, on your next
request, ran the full tests and the fine-tuning script, fixed two faults and uploaded the kit ("After the
guide"). On your word it then made the repository public, from one new commit: the commit ids in this report
belong to the history before it, which is not part of the public repository. On a further word it ran the
installer on your real install a fifth time (the last entry of "After the guide"). On 14 November you gave
me another model's review of the kit and asked for a plan from it and for the plan's execution: its
section, "Round 5", follows "After the guide". The commit ids of that section follow the public commit and
are not pushed. Decision record: `docs/upgrade/LEDGER.md`.

## Read this first
1. **The upgraded kit does not beat the old one by more than the noise.** Pilot with five runs per arm (the first
   one had two), same agent (headless Claude Code, Sonnet) and same budget (at most 12 training runs of 30 seconds).
   Test loss on the benchmark, lower is better: upgraded kit 1.7501, 23 October kit 1.7545, no kit 1.7425; the
   training script as shipped, with no agent, scores 1.7568. The upgraded kit is ahead of the old one by 0.0044
   (0.25 %), 95 % interval -0.010 to +0.019, exact permutation test p = 0.54. Neither kit is shown to beat no kit:
   that arm has the lowest mean, and the old kit is 0.012 behind it (p = 0.18). The five runs of an arm lie 0.005
   to 0.013 apart (standard deviation), and five against five can only find a difference of about 0.018 (1 %), so
   "not established" does not mean "equal". One task, one machine, one model. The first pilot's edge of 0.0076 lies
   inside that interval (section 2, "Pilot repeated with five runs per arm").
2. **The loop ran live with headless Claude Code and kept one change in each of two campaigns** (native Windows,
   CLI 2.1.322, Sonnet): scouting first, then five and six proposed changes, a stop at the run limit. Kept both
   times: a moving average of the weights, in the first campaign taken from the scouting notes. On the loop's
   validation split it gained 0.013 and 0.009, more than the noise margin. On the test split the two results are
   better than the unchanged script by about 0.009, which is close to the noise there. An earlier campaign through
   a bridge kept nothing (section 2).
3. **After the comparison, the loop's decisions were made harder to fool** (11 November, on your go-ahead;
   section 1, "Trustworthy decisions"). The keep rule takes its noise from all seed panels of a campaign: in
   simulation it keeps a change without effect in 2.4 % of cases instead of 7.9 %. The price is power while a
   campaign is young: a real gain of two run-to-run deviations is kept in 44 % of cases at the first change (the
   old rule's 68 % included its false keeps). The loop also tests the evaluator before it spends agent usage,
   accepts "no change to propose" from a session, and ends a campaign that kept something with a confirmation on
   fresh seeds, for which it holds back runs from the limits. The final evaluation runs once, through `expctl
   final-eval`, with a receipt; the guard now refuses the configured command typed directly. A campaign with a
   real agent ran with all of it on 12 November (section 2): eleven changes trained, two kept, the search ended
   by two sessions that declined, and the confirmation on fresh seeds held (1.6948 to 1.6407 on the validation
   split, a gain of 0.054 against a margin of 0.013). It is one campaign on one task, and its first keep rests on
   a noise estimate that proved too small (section 2). The comparison in point 1 measured the kit without these
   changes. One thing I announced was not built, a comparison of runs seed by seed: round 2 measured it on the
   benchmark and rejected it ("Round 2", point 6). Your real install has these changes since 12 November
   (section 4), and those of rounds 2 to 4 since the third and fourth installer runs (12 and 13 November).
4. **The work was cut down on 11 November** on your instruction (usage limit): no second verification round of the
   research, no outside scouts, no trial runs for undecided candidates, one independent reviewer instead of the
   deep-sweep skill. Of 474 adopted ledger rows, 332 are finished and 142 are listed as unfinished, not built
   (399, 261 and 138 before round 2; 415, 277 and 138 before round 3; 418, 280 and 138 before round 4; 422,
   288 and 134 before round 5, whose check of the ledger moved eight rows from finished to unfinished).
5. **Not verified live:** the Codex and Cursor ports in a real session, and the loop with either; the loop with
   Claude Code on Linux; the Hugging Face Jobs route, which is the internet GPU path. All are built and pass tests
   against stand-ins. Each waits for something only you can do (section 9).
6. **The independent review found two holes in the guard that mattered**: shell forms it did not recognise
   (PowerShell and `cmd` commands, code handed to `python -c`), and ways to read sealed data through search tools,
   wildcards and `cd`. Both are fixed and tested, and 16 smaller findings are fixed or answered (section 7). One
   gap was kept and documented until round 4 closed it (point 11): a plain `grep -r` or `find` started at the
   project root was not questioned. A
   second gap was found on 12 November (a git worktree outside `.claude/worktrees/` was not covered) and is
   closed in round 2. Round 2's own review then found older holes of the same kind. The worst: sealed data
   that is a link to storage outside the repository could be read through the link. They are fixed or
   answered ("Round 2", "The independent review"). Your real install has these fixes since the third
   installer run of 12 November. Its data folder is a link that stays inside the repository. In a throwaway
   project of that layout, the guard installed before that run refuses a read of a sealed file through the
   link and lets a search of the linked folder through; the new guard refuses both. On the real install
   itself that search is allowed before and after the run, and rightly: the sealed folder that its config
   names below the link is not on disk ("Round 2", "The third installer run on the real install").
7. One deviation from the prompt: the Codex hook payload in the tests is built from OpenAI's documented input
   schema, not copied verbatim or captured. And one thing to know about the pilot: the first try of the old-kit
   and no-kit sessions was void through a fault of my pilot script, and both were repeated (section 2).
8. **The recommended PyTorch pin did not work on this machine's GPU.** Every pinned third-party tool was installed
   into a throwaway environment in WSL and smoke-tested. All work except PyTorch 2.15.0 (`cu132` wheels): it runs
   on the CPU, but its first CUDA call crashes the interpreter (cause not found), while the installed 2.9.1 build
   trains on the same GPU. `references/stack.md` says to keep the build a project runs until a GPU smoke test of
   the new one passes. A try of the same pin on native Windows gave no result: pip refused one downloaded file
   whose hash did not match the index (a damaged download on a connection of about 1 MB/s), so nothing was
   installed there.
9. Tests: all seven test files pass in WSL (default Python 3.12, clean 3.8, clean 3.12) and on native Windows
   (default 3.11, clean 3.11, clean 3.8) at the last code change, commit `827c35c` of 14 November ("Round
   5", "Tests"), as they did at `0450067` of 13 November ("After the guide"), at round 4's, `00be575`
   ("Round 4", "Tests"), at round 3's, `0f23999`, and at round 2's, `6e01543`.
   Full test runs and real runs exposed nine faults, all fixed and tested (three more, found on 13
   November, are in points 12 and 13). Before round 2: a Hugging Face
   job's last files could be lost (section 3, "Tests"); on Windows, guard log lines written at the same moment
   destroyed each other (section 6, "Guard"); and nothing stopped a session that would have gone on at
   pay-as-you-go prices once the plan's usage ran out (section 6, "Other"). In round 2's full test runs: a
   paid remote run was booked with no time when the machine's clock was set back, and the mirror of a rented
   job could keep an older checkpoint while the job's bucket prefix was removed ("Round 2", "Tests"). In
   round 3's, both on Windows: a training run could end at its start while another process read one of its
   first records, and status could report a live run as stalled for one call. Three smaller faults that I saw
   beside those two are repaired as well, on 13 November ("Round 3", "The faults the full test runs found").
   In round 5's, both in WSL and both on Linux only: a command with a very long word ended the guard's
   check as an internal error, and a live run read as lost once the system clock had been set by five
   seconds, after which the guard no longer protected it ("Round 5", "Tests").
10. **Round 3 built three more items, and none was shown to raise results** ("Round 3"; round 4 has since
    measured the first of them with a stand-in agent, point 11). Where a project's config
    sets them, the harness searches the numeric settings that a change leaves open (`loop.search_trials`), and a
    campaign that stalls goes back to the commit before its last keep (`loop.restart_after`). The benchmark has
    a second task, 30 seconds of fine-tuning a small language model (`benchmarks/finetune/`). Each is tested
    with a stand-in agent. No real agent session ran on any of them, and the guard did not change. An
    independent review found one hole, in where the search writes its values, and it is closed.
11. **Round 4 closed the guard's kept gap, checked the evaluator harder and measured the search** ("Round 4").
    A recursive command over the project root is asked about when sealed files lie on disk below it, and the
    guard is stricter in many other forms, so an agent that explores with `grep -r` or `ls -R` at the root
    meets questions. Two reviewers without the working context reported 28 findings, all fixed or answered.
    The loop's self-test has two more cases, and a project can name controls that must stay at their floor.
    The search of numeric settings, measured with the stand-in agent, ended on a confirmed gain of 0.42
    against 0.31 on the fine-tuning task (two of three pairs carry the difference) and changed nothing on
    the character model, so it stays off by default. Round 3's three repairs hold, and five faults beside
    them are fixed. `install.py --worktrees` registers the guard for sessions started in a repository's other
    checkouts. One limit of the root check stays: the guard looks at no more than 20,000 files per folder it
    walks, so in a tree larger than that a sealed file can go unseen (round 5 lifted it for a folder that
    is sealed as a whole, point 14). Your real install has this round and
    round 3 since the fourth installer run of 13 November. There, four exploring commands at the root went
    from allowed to a question, and one way to read a file in a sealed folder went from allowed to refused.
    The fifteen files that run changed are committed there, on your word ("Round 4", "The fourth installer
    run on the real install").
12. **A guide for the person who uses the kit, and one fault that its commands found** (13 November, on your
    request; "After round 4"). `docs/GUIDE.md` now opens with what the kit is, a picture of it, what it
    changes, how it improves training and what was measured, in plain language, and the how-to follows. It
    claims no more than point 1 allows. Trying its first commands on a fresh practice project showed that a
    run of a practice script started by hand with `expctl launch` was not logged. That is fixed and has a
    test.
13. **The full tests pass, the fine-tuning script runs, two faults are fixed, and the kit is public on your
    GitHub account** (13 November, on your request; "After the guide"). All seven test
    files pass on both platforms with three interpreters each. The fine-tuning practice script trained for
    30 seconds through `expctl launch` and gave 0.34 exact answers on the development split. Fixed: the
    practice projects listed no best run, and `expctl status` dropped a run whose checkpoint path was
    recorded on another machine or before the project folder moved. The guide now explains how the kit
    works step by step, with diagrams, and the README is a front page. The repository was private at
    first, because every commit carries your private e-mail address. On your word of the same day it is
    public: it starts from one new commit under your account's no-reply address and has an MIT licence
    ("After the guide", "Public, on your word").
14. **Round 5 checked another model's review claim by claim, built what held, and then fixed what an
    independent reviewer and the last test run found in the result** (14 November, on your request; "Round
    5"). Of the review's 89 claims, 37 were adopted and built, 29 rejected, 19 are undecided and 4 wait for
    you. Built: two practice evaluators and a loop evaluator that are harder to fool, five closed ways past
    the guard, sealed files kept out of snapshots under any pattern, a keep rule whose bar a change's own
    runs cannot lower, a stop that is obeyed, one hashed archive per remote run, checks that fail before a
    run does, and a control for the fine-tuning task. A reviewer without the working context then found
    nine faults and four smaller ones in the result, most of them further ways past the guard; all are
    fixed, with five more that the fixing turned up. The full test run on the fixed code failed two checks
    in WSL, and both were real faults that only Linux shows: a command with a very long word ended the
    guard's check as an internal error, and a live run read as lost once the system clock had been set by
    five seconds, after which the guard no longer protected it. I watched the second one under WSL's own
    clock, which was being set back by several seconds a minute that day: the code before the fix lost its
    live run three and a half minutes after the launch, and its guard then let a write into the run's
    folder pass; the fixed code kept both. Both faults are fixed, and a third commit takes back a step
    that my own check found in the second fix. Most of all these faults are older than the round, so the
    public version has them until you have the round pushed. The guard asks more often now, also about
    some harmless commands. All seven test files pass on both platforms at `827c35c`. No second reviewer
    saw the fixes, no campaign ran with a real agent, nothing is pushed, and your real install was not
    touched.

## Round 2 (12 November 2026)

Your second prompt (`docs/upgrade/ROUND2.md`) asked for a comparison of the kit with similar projects as wholes,
for newer methods in place of the kit's defaults, and for a decision on everything still open, built where
adopted. The message that started it also carried another AI model's audit of the kit: twelve claimed defects
with patches, a list of methods and tools, and four modules. I took the audit as material, not as instructions:
each claim was checked against the kit's code or against its source and has a ledger row. The round ran under
the usage limit of 11 November. Its commits are `b7b7652`, `9424706`, `c6c1593` and `7233b9e`, then `af6cbeb`,
`7c1306f` and `98640c9` for what the independent review found, `9d5c80d` and `6e01543` for two faults in
remote runs that the full test runs exposed ("Tests"), `1337fbe` for one sentence in the references, and those
of this report. The numbered sections after this one describe the work before the round; where the round
changed a fact, they are corrected and say so.

### In short
1. **No other project does the kit's job better, so no part of the kit was replaced.** Eleven systems were read
   at their source (`scout/census.md`). None of them decides keep or revert in harness code from an evaluator
   the agent cannot edit, repeats seeds inside its loop against a noise margin, confirms a result on fresh
   seeds, limits the final test to one use, or caps money and tokens. Others are ahead in five things: more
   search operators, evaluation in parallel, fine-tuning recipes, distribution, and what the worker sees of
   earlier runs. The last one is built now. The others are ledger rows with the test each still needs.
2. **Built and tested.** The guard covers every worktree that git has registered, which closes the gap of 12
   November, and it refuses `git show <revision>:<sealed file>`. A gain that just misses the keep margin is
   decided on a second seed panel. The loop's worker sees a few points of the best run's curves. A campaign
   stops when a session that used tools left no guard record.
3. **The independent review kept nineteen findings, twelve of them about the guard.** The one it called
   blocking is older than this round: sealed data that is a link to storage outside the repository could be
   read through the link. Fourteen findings are fixed, one is fixed in part, four are answered with the
   reason; every fix has a check that fails against the code before it. A probe of my own after those fixes,
   which compared the guard with what ripgrep really reads, found five more searches of linked data folders
   that reached a sealed file; they are closed too ("The independent review" below). Every change in what the
   guard asks, denies or allows is listed with its test under "Changes in the behaviour of existing
   features".
4. **e-means holds up, and the kit had no place for it until now.** It is real (arXiv 2611.09501 of 6 November
   2026, released in FAISS 1.16.0 on 10 November) and was tried here: on 200,000 synthetic vectors its five
   passes matched or beat 25 passes of k-means in about half the time. The kit used no k-means, so nothing was
   replaced. It is now the documented method for the one job where clustering belongs, a data step that
   clusters embeddings (`references/data.md`, section 8), as an optional install. Not tried: a real corpus and
   the GPU build.
5. **None of this is shown to raise results on the benchmark.** The change to the keep rule was chosen by
   simulating whole campaigns on the benchmark's measured noise. That ranks rules against each other and
   proves no gain. One live campaign ran with the changed loop ("The live campaign" below): every new part
   worked, and the second seed panel turned one near-miss into a keep. The confirmation on fresh seeds then
   found that gain inside the noise: 0.0067 against a margin of 0.0140, verdict "unclear". So the one keep
   that this round's rule made possible is not confirmed. One campaign is an observation either way. The
   pilot's result stands: no measured edge over the old kit or over no kit ("Read this first", point 1).
6. **Two things I expected to help were measured and rejected.** Comparing runs seed by seed: on the benchmark
   the seeds of two versions of the code share almost nothing (r = 0.30 over eight seeds). A keep rule that may
   look after every seed (an e-process): in simulation its campaigns ended 14 to 33 % less far ahead when runs
   were the limit.
7. **The other model's audit.** Two of its twelve defect claims were right and are fixed: a sealed file that
   git tracks could be printed with `git show`, and the loop's worker could not read data the loop itself links
   into its worktree. The other claims did not hold against the code or describe a deliberate design, and its
   four modules are not taken. Every item has a row with the reason ("Rejected" below).
8. **Still open.** The 138 adopted rows that were unfinished before the round still are. The undecided rows
   with the highest expected benefit are not built: numeric settings searched by the harness, a fine-tuning
   track with a second benchmark task, a restart on a stall, a repair attempt after a crash. The reason is the
   usage limit. (The first three were built afterwards: "Round 3".)
9. **Your real install has the guard fixes since 12 November.** During the round it was untouched. After the
   report you asked for a third installer run. It replaced fifteen kit files there, the guard among them, and
   it corrected one thing I had said about that install ("The third installer run on the real install"
   below).
10. **The full test runs found two faults in remote runs, the optional route for rented GPUs.** A paid run
    could be booked with no time, and the mirror of a rented job could keep an older checkpoint while the
    job's files in the bucket were removed. Both are fixed: the ledger no longer trusts the wall clock alone,
    and nothing is removed before the mirror's content equals what the remote side lists ("Tests" below). The
    Hugging Face route is still not run against the real service.

### Where the kit stood, and how the research changed that view
The prompt asked me to write this view down before searching. I did not: the readers were started first. The
first list below was put together afterwards from the records as they stood before the round (sections 2, 8
and 10 of this report and `scout/draft/second-look.md`), so it is a reconstruction.

**Before the research.** The purpose is that an agent using the kit gets the best training results it can, and
that the results are real. Against that:
- No measured edge. Pilot with five runs per arm, test loss: 1.7501 with the upgraded kit, 1.7545 with the old
  kit, 1.7425 with no kit.
- The loop ended for want of power, not of budget. In the campaign of 12 November two of eleven changes were
  kept, a third of the runs stayed unused, and the search ended because two sessions in a row saw nothing that
  would clear the margin. With three seeds a real gain of two run-to-run deviations is kept in 44 % of cases.
- That campaign's first keep rested on a noise estimate that proved too small, and its gain during the search
  (0.027) was half the gain in the confirmation (0.054). The cause was not known.
- The loop's worker saw only the list of earlier decisions, no curve and no score of a discarded change.
- The guard had one known hole: worktrees outside `.claude/worktrees/`.
- The search is one greedy branch, nothing searches numeric settings, and fine-tuning is covered by references
  without a runnable recipe.
- Not verified live: Codex, Cursor, Hugging Face Jobs, the loop on Linux.
- What I expected to move it most: comparing runs seed by seed, more seeds for close calls, numeric settings
  searched by the harness, a fine-tuning track.

**After the research and the measurements.**
- What sets the kit apart is that its results are real, and no system read offers that. So the loop stays, and
  what others do better can only be added to it.
- The noise lies between seeds, and seeds do not carry over from one version of the code to the next. Measured
  on the benchmark with 32 training runs (the starting commit and the kept commit of the campaign of 12
  November, eight seeds, each run twice): one run's score moves by about 0.009 to 0.011 from seed to seed; the
  same seed repeats to within 0.0001 on the kept commit and 0.005 on the starting commit; the seed means of the
  two commits correlate at r = 0.30, which eight seeds cannot tell from no correlation. Pairing by seed would
  cut the deviation of a difference by 16 % at best (0.0115 against 0.0136) and cost more than that in degrees
  of freedom. So a closer decision costs fresh seed panels, and the first item of my earlier list is gone.
- The campaign's puzzle is mostly explained. On eight seeds the kept commit is better than the start by 0.035
  (standard error 0.004). The search's 0.027 lies one standard error of a three-seed panel below that and the
  confirmation's 0.054 about two above, so seed-to-seed variation accounts for the first and is a possible,
  not a comfortable, explanation of the second. The three baseline runs of that campaign lay unusually close
  together, which is why its first noise estimate was too small.
- On one GPU two things limit a campaign: how many ideas it can test per hour, and how small a gain a seed
  panel can see. The second seed panel helps with the second, in simulation. Nothing built helps with the
  first. In the live campaign of this round six of the seven changes were settings of the optimiser or the
  regulariser (learning rate, its schedule, batch size, dropout), each costing an agent session of about 38,000
  tokens: that is the case for letting the harness search such settings, which is still a Trial row. (Built
  afterwards, in round 3.)
- The pilot's result stands. Nothing in this round compared the kit with no kit again.

### What the census found
`scout/census.md` has the systems read, each with source, version or commit and date, the full matrix of 29
capabilities, the candidates and four whole-system alternatives. The rows of the matrix in which the kit differs
from the field (yes / part / no; n.s. = not stated in what was read; – = does not apply):

| Capability | Kit | autoresearch | AIDE | AIRA-dojo | MLEvolve | RD-Agent | AIBuildAI | HF skills | Unsloth | W&B skills | SkyPilot skill | autoresearch plugin (UG) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cap on money or on the agent's tokens | yes | no | no | no | no | no | n.s. | no | – | no | no | no |
| Keep or revert by harness code, from an evaluator the agent cannot edit | yes | no | no | no | no | n.s. | n.s. | – | – | no | no | part |
| Several seeds inside the loop, with a margin above their noise | yes | no | no | no | no | no | n.s. | – | – | part | no | part |
| Confirmation on fresh seeds when the search ends | yes | no | no | no | no | no | no | – | – | no | no | no |
| Final test used once, with a record | yes | no | no | no | no | no | no | no | no | no | no | no |
| Repair attempt after a crash | no | no | yes | yes | yes | yes | n.s. | – | – | no | no | n.s. |
| Combines two candidates | no | no | no | yes | yes | yes | n.s. | – | – | no | no | no |
| Search beyond one greedy branch | no | no | part | yes | yes | yes | yes | – | – | no | no | no |
| Evaluation in parallel | no | no | n.s. | yes | yes | yes | n.s. | – | – | part | yes | no |
| Numeric settings handed to an optimizer | no | no | no | no | no | n.s. | part | no | no | part | no | no |
| The worker sees curves and logs of earlier runs | part | yes | yes | yes | yes | yes | n.s. | yes | part | yes | yes | yes |
| Fine-tuning recipes and export | part | no | no | no | no | no | no | yes | yes | no | no | no |
| Installs through a plugin marketplace or `npx skills` | no | no | no | no | no | no | no | yes | no | yes | yes | yes |

The table shows the kit as round 2 left it. Round 3 built something for three of its rows: a restart when a
campaign stalls ("Search beyond one greedy branch"), a search of numeric settings by the harness, which is a
stratified random search and no optimizer library ("Numeric settings handed to an optimizer"), and a runnable
fine-tuning task ("Fine-tuning recipes and export"). The first two are off unless a project's config sets
them ("Round 3").

The differences that matter:
- **What the kit alone has is what makes a result real**: the first five rows. The benchmark systems win medals
  at another job (solving a Kaggle competition from nothing) and take their score from code the agent wrote.
  Replacing the kit's loop with any of them would remove what makes its numbers trustworthy.
- **More search operators** (repair, combination, tree search). The only controlled comparison (AIRA-dojo, arXiv
  2507.02554): better operators at the same search policy gave 45.5 % against 39.8 % medals, with about twice
  the tokens, and the gain is not attributed to any single operator. The search policy itself adds little: tree
  and evolutionary search add about 2 points there, and a second study (arXiv 2609.40303) found no significant
  difference between a chain, greedy search, UCB1 and best-of-N. So: a repair attempt after a crash is a Trial
  row (in the kit's nine recorded campaigns none of 56 iterations crashed, so there is nothing to replay it
  on), combining candidates is Assess, tree search is Hold.
- **Evaluation in parallel.** A real gain in wall-clock time elsewhere. On one GPU concurrent runs change the
  scores of a time-budgeted task, and on rented GPUs it costs money: Trial, optional.
- **Fine-tuning recipes and export** (Hugging Face skills, Unsloth). They are training libraries, not
  controllers: neither has a guard, a sealed split or statistics. Using them inside kit runs is a Trial row,
  as before. It needs a second benchmark task and model downloads to judge. (The task exists since round 3,
  `benchmarks/finetune/`. The trial was not run.)
- **The worker's view of earlier runs.** Every other loop lets its agent read logs and curves. Built in this
  round, in a narrow form: the harness puts a few points into the prompt, and run folders stay unreadable.
- **Distribution.** A bare skill installed through a marketplace carries no hooks, and the guard hook is what
  matters: Assess.

Whole-system alternatives compared: the kit with this round's changes; the kit with vendor skills as training
libraries inside its runs; a benchmark scaffold as the loop; autoresearch fanned out over rented GPUs. The choice
is the first with the second's parts as optional modules. What would change it: a measurement on training
repositories, not Kaggle tasks, in which a scaffold's operators raise held-out results at equal budget with
repeats; or many GPUs at your disposal, which would make parallel evaluation the bottleneck.

### What was integrated, and why
| Change | Why | Commit | Test |
|---|---|---|---|
| The guard applies the project's rules to every worktree git has registered, from every other one, and matches harness files on the repository path too | The gap found on 12 November: from a worktree outside `.claude/worktrees/` the file tools read the main checkout's sealed data | `b7b7652` | `tests/test_loop.py`, "guard rules in a worktree of the project" |
| `git show <revision>:<sealed path>` is refused | A sealed file that git tracks can be printed from any revision without touching the file (the audit's claim A6, confirmed) | `b7b7652` | same section |
| Unattended read tools may read data that `loop.link_paths` links into the loop's worktree | Without it the loop's worker cannot read data the loop itself gave it (the audit's claim A4, confirmed) | `b7b7652` | same section |
| A near-miss is decided on a second seed panel | The campaign of 12 November ended because nothing cleared the margin; in simulation this was the only variant that gained both when runs and when ideas were the limit, with no more useless changes kept | `9424706` | `tests/test_loop.py`, "campaigns p and q" |
| The worker's prompt carries a few points per logged metric of one run of the best commit, and a first-seed discard records both scores | Every other loop shows its agent curves; removing such tools cost 8.9 medal points in arXiv 2609.40303. Effect here not measured | `c6c1593` | `tests/test_loop.py`, campaign a |
| A campaign stops when a session that used tools or changed files left no guard record, the scouting session included | Before, only a session that changed files was checked, so a guard that was not running could go unnoticed for a whole scouting session | `c6c1593` | `tests/test_loop.py`, "campaign a resumed" |
| e-means as the method for clustering embeddings, optional (`faiss-cpu` 1.16.0) | Your example. Tried here: the same or a lower error than k-means in about half the time | `7233b9e` | no kit code; the try is recorded in `references/data.md`, section 8 |
| The guard after the review: sealed data behind a link is sealed at the link and at its real place; what any checkout's config seals, freezes or names as the final command holds in all checkouts; `git -C`, a checkout below a searched folder, a project in a subfolder of its repository, git's own files, and more spellings of the final command and of Windows paths are covered | The review's findings on the guard ("The independent review" below) | `af6cbeb` | `tests/test_loop.py`, same section: 19 checks, 20 on Windows |
| The single use of the final evaluation counts over every checkout; a confirmation fails when the kept commit scores exactly the same on every fresh seed; no second panel without room in the time limits; the worker's view in plain ASCII; the guard-record check for a scouting session whose agent lists no tool calls; `expctl selftest` warns when sealed data is tracked in git | The review's findings on the loop's decisions and the final evaluation | `7c1306f` | `tests/test_kit.py` and `tests/test_review_fixes.py` (one new check each), `tests/test_loop.py` (three new, one changed) |
| A search is judged by where the sealed files really lie, as ripgrep does | A probe of my own after the review's fixes: in five of eleven layouts of linked data folders a search still read a sealed file | `98640c9` | `tests/test_loop.py`, same section: three checks |
| When a paid remote run ends, the ledger books the larger of the wall-clock time since its start and the controller's own count | The full test run at `98640c9` failed one check in WSL: the clock went backwards during a run of a few seconds, and the ledger booked no time for it ("Tests" below) | `9d5c80d` | `tests/test_remote.py`, unit checks: one new check |
| The last pull of a remote run compares SHA-256 checksums of the mirror with a list from the remote side before anything is removed; a file that differs is fetched by itself | The full test run at `1337fbe` failed one check in WSL: the mirror of a rented job held an older checkpoint than the job had written, and the bucket prefix was gone. `hf buckets sync` passes over a file of the same size unless it is newer by more than a second ("Tests" below) | `6e01543` | `tests/test_remote.py`, unit checks: four new checks; `tests/fake_hf.py` follows the real rule |

Nothing from another project replaced a part of the kit. The census produced no case in which a part of the
kit's work is done better elsewhere on evidence, except the worker's view, which was built here and not taken
over.

### The live campaign
One campaign with a real agent on the changed loop, as a check that the new parts work with real sessions.
Kit code at commit `c6c1593`, a practice project from `benchmarks/new_project.py`, campaign `r2`, limits
`--max-runs 24 --max-hours 0.75`, native Windows, headless Claude Code CLI 2.1.322 with `claude-sonnet-5-5`,
permission mode `dontAsk`, approvals not bypassed. Baseline on three seeds: mean 1.68511. The scouting session
wrote eight hypotheses. Its notes record that the search tool's output ended with a line demanding sources as
links, which it did not take as an instruction.

| # | Change (source) | Result | Decision |
|---|---|---|---|
| 1 | H1: warmup, peak learning rate 2e-3, linear decay, clipping | first seed 1.7313 against 1.6916 | discard |
| 2 | H2: dropout 0 | first seed 1.7301 | discard |
| 3 | H8: batch 256 with learning rate 1e-3 | first seed 1.7047 | discard |
| 4 | H4 and the worker's own: constant learning rate 1e-3, betas 0.9 and 0.95 | first seed 1.7335 | discard |
| 5 | H3: TF32 and fused AdamW | better by 0.0101, margin 0.0175 | inconclusive |
| 6 | the worker's own: learning rate 4e-4, short warmup, decay over the last 60 % | better by 0.0071, margin 0.0188 | inconclusive |
| 7 | the worker's own: peak learning rate 8e-4, short warmup, decay over the last 70 %, clipping | first look: better by 0.0172, margin 0.0193. On six seeds: better by 0.0168, margin 0.0130 | **keep** |

What it showed:
- **The second seed panel decided one change.** Change 7 reached 89 % of the margin on three seeds. The loop
  trained it on seeds 4, 5 and 6, trained the starting commit on the same three, and kept it on six seeds each
  (1.67193 against 1.68870). Under the rule before this round it would have stayed inconclusive, and the
  campaign would have kept nothing. Changes 5 and 6 reached 58 % and 38 % of the margin, below the two thirds
  that earn a second panel.
- **The guard-record check did not stop a sound session.** The eight sessions left 29 guard lines, none a
  refusal.
- **The workers used what the prompt now shows them.** Each worker prompt carried nine points each of the best
  run's validation and training loss, marked as still falling at the end. Four of the seven hypotheses name
  that (for example "dev loss is still falling at lr 3e-4 after ~5000 steps"), and two refer to the scores of
  earlier discards. Whether this led to better proposals is not known.
- **A cost of the second panel that the simulation did not model.** It used the six runs that the confirmation
  would have needed, so the campaign stopped at its run limit with the confirmation not run (22 of 24 runs
  used, six needed). The simulated campaigns had those runs set aside from the start; the loop sets them aside
  only after the first keep. `references/loop.md` and the README now say so.
- **The confirmation did not confirm the keep.** I resumed the campaign with the run limit raised from 24 to
  28, which started no session and ran only the confirmation, on three seeds drawn at that moment:

  | | Seed 26962 | Seed 53793 | Seed 74926 | Mean |
  |---|---|---|---|---|
  | Starting commit | 1.68143 | 1.67523 | 1.68009 | 1.67892 |
  | Kept commit (change 7) | 1.67054 | 1.67282 | 1.67340 | 1.67226 |

  A gain of 0.0067 against a margin of 0.0140: **unclear**. The kept commit scored on the fresh seeds as it
  had on the campaign's six; the starting commit scored 0.010 better than on those, which is 1.5 standard
  errors for panels of this size. Three fresh seeds cannot tell a gain of this size from none (standard error
  0.0065), so the verdict means "run more seeds before relying on it", not "the change does nothing". Nothing
  is reverted: the kept commit stays on its branch with that verdict in the journal.
- Used in all: 28 runs (3 baseline, 16 for the seven changes, 3 for the starting commit's second panel, 6 for
  the confirmation), 20 minutes (1,173 s), 923 s of GPU time, 8 sessions, 319,657 agent tokens, 0.49 USD of
  notional cost (subscription usage, nothing billed per use).

Compared with the campaign of 12 November on the kit before this round (eleven changes, two kept, a confirmed
gain of 0.054), this one found less: 0.017 on its own seeds and 0.007 on fresh ones. Its scouting session did
not propose the weight average that carried most of the earlier gain. Two campaigns differ in what their
sessions propose, and nothing about the effect of this round's changes on results can be read from the two.
What the campaign does show about the second panel: it makes keeps of small gains possible, and a small gain
kept that way is exactly the kind a three-seed confirmation often cannot confirm.

### The independent review
One reviewer with no access to my working context: a fresh subagent (Claude Opus) with the kit at commit
`7233b9e` and a brief written for a reader who knows nothing of the work. Its task was to review this round's
changes to the guard, to the loop's decisions and to the final evaluation, to try what it suspected, and to
report what it kept. It tried its suspicions with made-up calls and stand-in runs in throwaway projects and
kept nineteen findings: twelve about the guard, six about the loop, one about the final evaluation. It called
the first one blocking. Every fix has a check that fails against the code before the fix; the checks are named
under "Changes in the behaviour of existing features".

| # | Finding | Outcome |
|---|---|---|
| 1 | Sealed data that is a link to storage outside the repository could be read through the link and at its real place. Older than the round, and the layout of projects with large datasets | fixed, `af6cbeb`; searches of such a folder in `98640c9` (below) |
| 2 | `git -C <folder>` hid the folder it names from the rule on `<revision>:<path>` | fixed, `af6cbeb` |
| 3 | A sealed file that git tracks is printed by commands that do not name it (`git log -p`, `git show <commit>`; nine commands in its probe) | answered. `expctl selftest` now warns when sealed data is tracked (`7c1306f`), and the README names a `-diff` attribute that stops three of the commands (tried with git 2.52.0). A guard rule is a Reject row: it would have to question every command that shows history, and a blob id or an archive would still pass |
| 4 | The rules came from the session's own config alone, so a worktree whose config seals other paths could read what another checkout seals | fixed, `af6cbeb` |
| 5 | A search started above a nested checkout read that checkout's sealed files | fixed, `af6cbeb` |
| 6 | A project in a subfolder of its repository did not find its other checkouts | fixed, `af6cbeb` |
| 7 | The guard reads the other checkouts from git's own files: one unreadable entry there lost the whole list, and a session could change those files without a question | fixed in part, `af6cbeb`: an unreadable entry loses that entry only, and an edit or a shell write there asks. Not built, a Reject row: refusing every call when the session's own `.git` pointer is damaged. A submodule's pointer looks the same, and a damaged pointer breaks git itself, which shows |
| 8 | Each worktree had a receipt of its own, so each got a first use of the final evaluation on the same test split | fixed, `7c1306f` |
| 9 | The rule against typing the final command directly missed it in a chain, after `cd`, and behind `py` or `cmd /c` | fixed, `af6cbeb`. A wrapper script still gets past it; `sealed_tokens` is the stronger rule (README) |
| 10 | A kept commit that scores exactly the same on every fresh seed (a fixed seed, a cached result) lowered the noise estimate and passed the confirmation | fixed, `7c1306f`. Limit: exact equality only; a change that fakes a small spread is not caught |
| 11 | Unattended, a tool the guard does not know could use the linked data that this round opened for read tools | fixed, `af6cbeb` |
| 12 | This round's rule on `<something>:<path>` refused honest commands outside git | fixed, `af6cbeb`: a refusal inside a git command, a question elsewhere |
| 13 | A second seed panel could start with too little time left and be cut short | fixed, `7c1306f` |
| 14 | A stop between the runs of the best commit's second panel loses the runs already trained | answered: wasteful, not wrong (no run is counted twice). `references/loop.md` states the loss; storing half a panel is a Reject row |
| 15 | A metric name with non-ASCII letters, or a number of thousands of digits, reached the worker's prompt | fixed, `7c1306f` |
| 16 | A scouting session of an agent whose output lists no tool calls (Cursor) passed the guard-record check without a guard | fixed, `7c1306f` |
| 17 | A session could forge a guard record, and a tool call rejected before its hooks ran leaves none. Suspected, not shown with a real agent | answered, a Reject row: the check exists to notice a hook that silently does not run, and it does. A session that can forge the record has a shell and is held by the guard's other rules and the transcript scan |
| 18 | The `\\?\`, `\\.\` and `\\localhost\C$\` spellings of a Windows path were not recognised | fixed, `af6cbeb` |
| 19 | A junction inside a linked folder, below a search | answered: ripgrep does not follow a link below the folder it is given. Confirmed with ripgrep 15.2.0 |

How the fixes were checked:
- Against the guard before `af6cbeb`, each of its new guard checks fails. Against the code at `af6cbeb`, the
  new and changed checks of `7c1306f` fail and no other check does: one each in `tests/test_kit.py` and
  `tests/test_review_fixes.py`, four in `tests/test_loop.py`.
- The reviewer's own probe scripts, run again after the fixes, give the fixed results: the confirmation of a
  flat kept panel fails; its poisoned metric log puts nothing into the worker's prompt (0 characters); a
  worktree is refused the final evaluation with the count of all uses, and writes to the receipt folder ask;
  a near-miss with no time left ends "inconclusive (... the limits left no room for a second seed panel)".
- Two lines of its probe output look like failures and are not. A search of `.claude` from the main checkout
  gets no refusal: ripgrep reads no sealed file there, because git ignores the worktrees below it (compared
  with ripgrep). A read through an 8.3 short name gets none: this machine's volume creates no short names, so
  the probe's path named no file. That case is therefore not tried ("Unverified" below).

**A probe of my own after those fixes found more of finding 1.** I compared the guard's answer to a search
with what `rg -l` really prints (ripgrep 15.2.0, native Windows) over eleven layouts: worktrees whose data
folder is a link to storage outside the repository, into a sibling worktree, and into the main checkout
under another name. At `7c1306f` five searches were let through that read a sealed file: the linked folder by
its name when git ignores the link, the same folder at its real place, and the folder the link ends in when
it lies in another checkout. The cause: the guard asked git whether the file is ignored under the link's
name, and ripgrep goes by the ignore rules of the place where the files really lie. Outside the repository
there are none. The guard now asks the same question ripgrep does (`98640c9`). All eleven layouts agree: a
refusal where ripgrep reads a sealed file, none where it reads nothing. Of the three new checks all fail
against `7c1306f` on Windows and two in WSL, where git gives no answer for a path beyond a symlink, so the
old guard refused that search already. Not compared: ripgrep on Linux, and plain `grep -r`, which is the
documented gap.

### Tests
A full run takes a clean clone of one commit and runs all seven test files with three interpreters per
platform. Native Windows: the default Python 3.11.7 (psutil installed), a clean 3.11.7 and a clean 3.8.20.
WSL: the default 3.12.3 (psutil installed), a clean 3.12.12 and a clean 3.8.20. The clean ones hold no
third-party package. The table gives the number of checks in each file; all passed in all three interpreters
unless the last column says otherwise.

| Commit | Platform | benchmarks | kit | loop | ports | remote | review_fixes | runlog_units | Failed |
|---|---|---|---|---|---|---|---|---|---|
| `7233b9e`, before the review | Windows | 23 | 133 | 140 | 106 | 67 | 37 | 16 | none |
| | WSL | 23 | 137 | 142 | 105 | 67 | 39 | 16 | none |
| `7c1306f`, the review's fixes | Windows | 23 | 134 | 163 | 106 | 67 | 38 | 16 | none |
| | WSL | 23 | 138 | 164 | 105 | 67 | 40 | 16 | none |
| `98640c9`, the search fix | Windows | 23 | 134 | 166 | 106 | 67 | 38 | 16 | none |
| | WSL | 23 | 138 | 167 | 105 | 67 | 40 | 16 | one check in `remote`, default interpreter |
| `1337fbe`, with the ledger fix | Windows | 23 | 134 | 166 | 106 | 68 | 38 | 16 | none |
| | WSL | 23 | 138 | 167 | 105 | 68 | 40 | 16 | one check in `remote`, default interpreter |
| `6e01543`, the last code change | Windows | 23 | 134 | 166 | 106 | 72 | 38 | 16 | none |
| | WSL | 23 | 138 | 167 | 105 | 72 | 40 | 16 | none |

`ports` has one check fewer under Python 3.8, which lacks a module that check needs. The two platforms differ
where a check exists on one of them only.

The two failures were faults in `nnremote`, not in the tests. Both showed in WSL's default interpreter, the
first of a run, about two minutes after the virtual machine had started.
- At `98640c9`: "when the run ends, the ledger books the time used, not more than the reservation". The
  ledger's closing row carried a time half a second before its opening row, and no time was booked for a
  paid run. Fixed in `9d5c80d`.
- At `1337fbe`: "results are mirrored; the job got the named variable and file only". The mirror of a rented
  job held an older step of the checkpoint than the job had written, and the job's bucket prefix was gone.
  In that run the ledger's two rows lay 2.1 seconds apart while the controller had counted about 4: the
  clock had gone back by about two seconds, and the first fix booked the right time. Fixed in `6e01543`.

The logs show that the clock stepped back. Why it did is my reading: the virtual machine corrects its clock
shortly after it starts. The second fault does not need that. Its cause is the rule by which `hf buckets
sync` takes a file as unchanged: the same size, and not newer than the local copy by more than a second
(huggingface_hub 2.4.0, `_buckets.py`). The local copy's date is the time of its download on this machine's
clock. So a checkpoint that keeps its size and is rewritten within a second of the mirror's last download is
passed over, and a clock that runs ahead of the store's widens that second. This is my analysis of the
rule; the real service was not run. The stand-in for the `hf` command passed a file over only when the
store's copy was no newer at all, which hid the fault; it follows the real rule now. Both fixes are
described under "Changes in the behaviour of existing features", "Remote runs".

In the run at `6e01543` the clock did not step during the remote tests: the ledger's rows agree with the
time booked. That run therefore does not repeat the condition of the first fault, whose check builds the
state by hand.

Nor do the full runs show the second fix by themselves. With the stand-in on the real rule, the code before
the fix (`1337fbe`) still passed the end-to-end check "results are mirrored" in all five runs I made on
native Windows; why the fault's timing did not occur there I did not measure. So I widened the stand-in's
second to five, which is what a local clock four seconds ahead of the store's amounts to, in scratch clones
on native Windows. The code before the fix then failed that check, and only that one, in both of two runs;
the code with the fix passed all 72 checks in both of two runs. The committed stand-in keeps the one second
of the real rule. The second fix therefore rests on its four unit checks, which build the state by hand,
and on this comparison.

### Rejected, although you might have expected it
- **e-means inside the core.** The kit clusters nothing by itself, so there was no k-means to replace. It is
  adopted for the one data step where clustering belongs, as an optional install.
- **Another project as the loop** (autoresearch, AIDE, AIRA-dojo, MLEvolve, RD-Agent, AIBuildAI, the autoresearch
  plugin). Each is weaker on every row of "is the result real". AIDE and MLEvolve are Hold, the others Reject.
- **Tree or evolutionary search.** Hold: the controlled evidence shows no reliable gain, and one GPU cannot pay
  for the extra evaluations.
- **Comparing runs seed by seed** (the audit's claim A1, and my own announcement of 11 November). Measured:
  r = 0.30. Rejected for the loop; `references/uncertainty.md` keeps the paired test for comparisons by hand.
- **A keep rule that stays valid at every look** (e-values; the audit's "statistical firewall"). Simulated with
  the kit's own rule code: a campaign ended 14 to 33 % less far ahead when runs were the limit, and 1.5 to 15 %
  less far with 15 to 27 % more runs when ideas were. The second panel is one fixed second look instead.
- **Changes to the first-seed check** (slack, the mean of the best's panel, no check, the audit's rotating seed
  with a futility bound: claim A2). Simulated: none beat the check as built beyond the simulation's error, and
  without it a campaign ended about 40 % less far ahead.
- **A first baseline of twice the seeds, and training a kept commit again.** Both spend runs that find more
  when they go to new ideas, and a repeat on the same seeds adds little because the noise lies between seeds.
- **The audit's four modules** (`emeans_helper.py`, `statistical_firewall.py`, `scaling_and_stability.py`,
  `nn_guard_hardened.py`). They were written from an archive of the kit without running its tests. One would
  replace the tested guard, and one calls a FAISS function that version 1.16.0 does not have. Each idea in
  them has its own row.
- **The audit's other defect claims.** Edit markers in the training script (A6): the kit names what may not
  change and leaves the rest to the agent. A syntax check before training (A3): none of 56 recorded iterations
  failed that way. Sealed rules a second time in the subagent hook (A5): it matters only when the project hook
  is not registered, which the self-test reports. Links in snapshots (A8), the thinned curve (A9) and the remote
  ledger (A11): the code does not bear the claims out. Status hooks in worktrees (A10): a worktree is a project
  of its own by design. The Python 3.8 audit (A12): already the kit's practice, 3.8 is in every full test run.
  Undecided, as Assess rows: a read-only `expctl compare` (A7) and showing later workers the diffs of
  inconclusive changes (A3).
- **The audit's list of methods and tools.** Every item has a row. e-means is adopted, ZClip is a Trial row,
  the rest is Assess, Hold or Reject. Several descriptions did not match their source: the paper number given
  for ZClip belongs to another method, and a Claude Code version was wrong. Its Claude Code security item
  (CVE-2026-39861) is fixed in a version older than the one the README already names as the minimum.
- **Newer releases.** One changes a decision: FAISS 1.16.0. The optuna-mcp repository has new commits (22
  October) and no new release; the decision stays, with a new reason.

### Verified by running, from documentation only, unverified
**By running.**
- The guard changes: the tests named above, on both platforms, and nine made-up calls handed to the guard of
  a throwaway project for the other kinds of copy ("What another installer run would change").
- The review's fixes: their checks on both platforms, each shown to fail against the code before its fix; the
  reviewer's probe scripts run again; the guard's answers compared with what ripgrep 15.2.0 reads, over
  eleven layouts of linked data folders on native Windows ("The independent review").
- What a `-diff` attribute does for a tracked sealed file, with git 2.52.0 in a scratch repository: `git
  show`, `git log -p` and `git diff` print "Binary files differ" in place of the content; `git cat-file` and
  an archive still print it.
- The link layout of the real install, rebuilt in a throwaway project with a practice pattern: what the guard
  installed there and the current guard answer to four calls ("What another installer run would change").
- The keep rule, the worker's view and the guard-record check: the tests with a stand-in agent and stand-in
  runs, and the one live campaign.
- The benchmark's noise: 32 real training runs.
- The simulation: the kit's own rule code on synthetic scores, 10,000 or 20,000 campaigns per variant, with
  three assumed mixes of harmful, useless and helpful ideas. It is a model.
- e-means: `faiss-cpu` 1.16.0 installed into a throwaway environment on native Windows (Python 3.11), 200,000
  synthetic vectors, three seeds, CPU.
- The installer's dry run on the rehearsal copy of the real install, repeated after the last code change.
- The two remote faults: each showed in a full test run in WSL, and each fix has unit checks that build the
  faulty state by hand (a clock set back; a mirror that holds an older file of the same size). They run
  against stand-ins for `ssh` and the `hf` command. For the second fault there is also an end-to-end
  comparison with the stand-in's window widened to five seconds: the code before the fix fails, the code
  with it passes (two runs each, native Windows; "Tests").

**From documentation only.** Everything the census says about another system: nothing was installed or run, and
each statement comes from that project's pages, files or paper. The rows of the note `newer-methods`. The
audit's claims about methods and tools, whose sources a small model read and summarised (about 40 pages).
The rule by which `hf buckets sync` passes over a file: read in the source of huggingface_hub 2.4.0
(`_buckets.py`) on 12 November. That the same package sets no file date after a download is my reading of
that file and of a search of the package for the call that would do it.

**Unverified or not measured.**
- Whether any change of this round raises results on the benchmark.
- The round's changes with a real agent on Linux, or with Codex or Cursor (tests in WSL only).
- The new guard on the real install: the probes ran in throwaway projects with practice patterns, and that
  project's own check was not run again.
- The guard against ripgrep on Linux: the comparison ran on native Windows. The checks for linked folders
  pass in WSL.
- A sealed file named by an 8.3 short name: this machine's volume creates no short names. The guard resolves
  every path through the operating system before it judges it, which gives the long name of a file that
  exists.
- The review's limits that stay: the kept gap for a plain `grep -r` at the project root (closed in round
  4), sealed files that git tracks, a wrapper script around the final command, a confirmation fooled by a faked small spread, a
  forged guard record (README, "Notes and limits", and the Reject rows).
- e-means on a real corpus and on a GPU.
- The Hugging Face route against the real service, as before. New in this round and equally untried there:
  whether a job's bucket mount keeps the order in which the job writes (the checksum list, then the exit
  record), and `hf buckets cp` for one file. If the real mount is slower than the job, the new check keeps
  the bucket prefix and says so; before, the prefix was removed. The canary in `references/remote.md` now
  includes a file of constant size.

### Changes in the behaviour of existing features
The sealed test set, the frozen evaluator and the protection of live runs are not weaker. Every check that
`tests/test_kit.py`, `tests/test_review_fixes.py` and `tests/test_ports.py` held before the round passes
unchanged, and the first two gained one check each. One change allows a call that was refused before: an
unattended read tool may read data that the loop linked into its worktree (last row of the first table).

**Guard, before the review** (`b7b7652`; each tested in `tests/test_loop.py`, "guard rules in a worktree of
the project").

| Call | Before | Now | Reason |
|---|---|---|---|
| A file tool or a shell command reaches a sealed file of another checkout of the repository (the main checkout or any registered worktree, wherever it lies) | denied only from a worktree under `.claude/worktrees/` | denied | the gap of 12 November |
| An edit of a frozen file, or of a harness file such as `.claude/settings.json` or `.claude/settings.local.json`, in another registered checkout | passed without a question, except from a worktree under `.claude/worktrees/` | asks; unattended: denied | the same gap |
| A shell word of the form `<something>:<path>` whose path part is a sealed file, as in `git show HEAD:data/test/labels.csv` | allowed | denied inside a git command; elsewhere a question (second table) | a tracked sealed file could be printed from any revision |
| With `NN_UNATTENDED=1`, a read tool reads a path that resolves into a `loop.link_paths` entry of the outer checkout | denied as "outside this project" | allowed for the read tools; writes are unchanged, and a tool the guard does not know is denied (second table) | the worker could not read data the loop had linked for it |

**Guard, after the review** (`af6cbeb`, last row `98640c9`). The number is the finding in "The independent
review", which gives the reason. Every check is in the same section of `tests/test_loop.py` and fails against
the guard before its commit.

| Call | Before | Now | Finding | Check |
|---|---|---|---|---|
| A read, a search or a shell command reaches a sealed file behind a link (symlink or junction) to storage outside the repository, through the link or at its real place | allowed | denied | 1 | "a sealed folder that is a link to storage outside the repository is sealed" and the three checks after it |
| A call reaches what the config of another checkout seals, freezes, or names as a harness file, a sealed token or a final command | judged by the session's own config alone | the lists of all checkouts are combined, so the strictest rule holds in each | 4 | "the sealed paths of every checkout's config hold in all of them, whatever the session's own config seals" (it tries the sealed paths; the other four lists are combined by the same lines) |
| `git -C <folder> show <revision>:<path>`, where folder and path together name a sealed file | allowed | denied | 2 | "git -C <folder> does not hide the folder it names" |
| A project in a subfolder of its repository: a sealed file of another checkout, and `git show <revision>:<path>` with the path counted from the repository's top | allowed | denied | 6 | "a project in a subfolder of its repository: its other checkouts are found all the same" and the check after it |
| A search started above a nested checkout that holds sealed files and that git does not ignore | allowed | the Grep and Glob tools: denied; a recursive shell command: a question | 5 | "a search from above another checkout reaches that checkout's sealed files" |
| An unreadable entry in git's list of worktrees | the whole list was lost, so no other checkout was covered | that entry alone is lost | 7 | "a damaged entry in git's list of worktrees loses that entry only" |
| An edit of git's own files with a file tool, or a shell command that writes below `.git/worktrees/` | allowed | asks; unattended: denied | 7 | "an edit of git's own files asks" and the check after it |
| The configured final-evaluation command typed directly in a chain, after `cd`, behind `py` or behind `cmd /c` | allowed | denied; a validation run of the same script stays free | 9 | "the final command is recognised in another spelling: ..." (four checks) and "... while a validation run of the same script stays free" |
| Unattended, a tool the guard does not know (an MCP tool, for example) names a path in the linked data | allowed like a read tool (since `b7b7652`) | denied | 11 | "unattended, only the read tools may use the linked data: an unknown tool is denied" |
| A shell word `<something>:<sealed path>` outside a git command, such as an `scp` source or a container mount | denied (since `b7b7652`; allowed before the round) | asks; unattended: denied | 12 | "a colon outside a git command is asked about, not denied" |
| A sealed file named as `\\?\C:\...`, `\\.\C:\...` or `\\localhost\C$\...` | allowed | denied | 18 | "the long-path spelling of a sealed file (`\\?\C:\...`) is recognised" (Windows only; it tries the first spelling) |
| A search of a linked data folder whose link git ignores: by its name, at its real place, from a checkout that has no such link, and where the link ends in another checkout under another name | allowed | the Grep tool: denied; `rg` in the shell: a question | 1, my probe | "a search of a linked data folder that git ignores reaches the sealed files below it, by its name and at its real place" and the two checks after it |

What follows from the last row: where a link ends in a folder of another checkout that git does not ignore
there, a search of that whole checkout is refused as well (README, "Notes and limits"). Unchanged: a search of
a whole worktree whose data folder is a link passes, because ripgrep does not follow the link. Inside the
guard: it asks git about the place where a sealed folder really lies, keeps git's answers for the one call,
and passes over a sealed folder that ripgrep would not enter before it walks it.

**Keep rule** (`9424706`; `tests/test_loop.py`, "campaigns p and q").
- A gain above two thirds of the margin, but not above it, costs up to two further seed panels (one for the
  change, one for the best so far, the latter once per best commit) and is decided on all seeds at 1.1 times
  `noise_mult`. In simulation one comparison keeps a change without effect in 2.7 % of cases, against 2.3 %
  before.
- The best commit's panel can then hold twice the seeds, and later first looks are compared against its mean
  over all of them. The starting commit's mean is updated when its own panel is extended.
- The ledger can hold `baseline` rows between iterations; an iteration row can carry `first` (the first look)
  and scores and runs for twice the seeds; reasons read "on 6 seeds". `state.json`: the baseline entry has a
  `run` key.
- The confirmation's fresh seeds also avoid the seeds of the second panel. `loop.seeds` must be whole numbers.
- A second panel late in a campaign can use the runs a confirmation would need; the confirmation is then
  reported as `not_run`, and `nnloop resume` with a higher limit runs it.
- After the review (`7c1306f`): a second panel starts only when the time and GPU-hour limits have room for
  its runs, each counted at its cut-off. Otherwise the change stays inconclusive, with the reason "the limits
  left no room for a second seed panel", and nothing is trained. Check: "nor is a second panel started that
  the time limit would cut short: its runs are counted at their cut-off".
- After the review (`7c1306f`): the confirmation's verdict is `failed` when the kept commit scores exactly
  the same on every fresh seed while the starting commit's scores differ, and such a panel no longer enters
  the pooled noise. Before, it could pass as confirmed. Check: "a kept commit that scores exactly the same on
  every fresh seed, where the starting commit does not, fails the confirmation instead of passing it: its
  panel is one run repeated".

**Loop** (`c6c1593`; `tests/test_loop.py`, campaign a and "campaign a resumed").
- The stop "the guard hook did not run" also fires for a session that only used tools, and for the scouting
  session. Before, it fired only for a worker session that changed files. After the review (`7c1306f`) a
  scouting session is known by the notes file it left, so the stop also holds for an agent whose output lists
  no tool calls. Check: "Cursor's output lists no tool calls: a scouting session without the guard is known
  by the notes file it left, and stops the campaign".
- The reason of a first-seed discard reads "on the first seed it scored X against Y for the best so far".
- The worker's prompt can carry a paragraph with points of the best run's logged metrics. Names and steps
  come from training code, so names are reduced to plain ASCII characters and numbers are rounded (`7c1306f`).
  A number too large to format drops the paragraph for that run.

**Final evaluation** (`7c1306f`; `tests/test_kit.py`). `expctl final-eval` counts the uses of the main
checkout and of every registered worktree. Once any checkout has used the final evaluation, a worktree is
refused with the count of all uses; `--again "reason"` works as before. Before, each checkout counted for
itself, so each worktree had a first use on the same test split. A worktree that is removed takes its receipt
along (README). Check: "final-eval: the uses of every checkout of the repository count, so a worktree gets no
first use of its own".

**Self-test** (`7c1306f`; `tests/test_review_fixes.py`). `expctl selftest` reports one more check, "sealed
data is not tracked in git". It is a warning: marked as not required, and the exit code does not change.
Check: "selftest warns when sealed data is tracked in git, where git can print it without being given its
name".

**Remote runs** (`9d5c80d`, `6e01543`; `tests/test_remote.py`, units). Two changes, both from faults that
the full test runs exposed ("Tests" above).
- When a paid run ends, the ledger books the larger of the wall-clock time since the run started and the
  controller's own count. Before, a clock that was set back during the run shortened the time booked, down to
  nothing. Check: "a clock that was set back during a run does not shorten the time booked: the controller's
  own count holds".
- Before it removes anything on the remote side, the controller compares the content of its mirror with a
  list of SHA-256 checksums from there. An ssh target computes the list at the last pull. A Hugging Face job
  keeps it in its bucket prefix as `remote-files.json`, rewritten with every file it copies. A file that
  differs is fetched by itself; if one still differs, nothing is removed. Before, an ssh run counted as
  complete when the sizes agreed, and the prefix of a Hugging Face job was removed after any pull without an
  error. What you will notice: such a job can now end with `remote.teardown` saying "kept, because the last
  pull did not complete"; its mirror holds one more file, `remote-files.json`; and the last pull reads every
  mirrored file once more. A job without an exit record (preempted, cancelled, out of time) may have copied a
  file without listing it, so there the copy in the bucket counts. Two limits are new (`references/remote.md`,
  "Limits"): such a job can leave the mirror one copy behind for one file, and a remote run that was started
  before a kit upgrade and is picked up with `attach` after it keeps its remote files. Checks: "the store
  lists the checksum of every file copied to it", "a file the sync passed over is found by its checksum and
  fetched by itself", "a copy that differs from the list keeps the store of a job that ended by itself; of a
  job that was cut off, the store's copy counts", "a listed name outside the mirror or over its records is
  not fetched, and the store is then kept".

**Texts.** README ("Notes and limits"), `references/loop.md`, `references/validity.md` (section 5),
`references/remote.md` ("Money", "Teardown", "Limits", "Canary") and the experiment-reviewer's brief state the
new rules and the limits that stay.

**Tests changed** (all in `tests/test_loop.py`, which is new in this upgrade): campaign a's check of the
first-seed discard is stricter (it expects both scores); the stand-in agent reports calls that did not pass
the guard, so that the new stop can be tested; the toy training script writes `metrics.jsonl`, so that the
worker's curve paragraph can be tested. After the review: campaign a's check of the curve paragraph expects
rounded numbers and one more line, for a metric name with a non-ASCII letter that the toy training script
now logs (the cleaning is stricter); the guard fixture gained a helper for shell commands and one that makes
and removes the link, and can ask about a search. New checks after the review: 22 in `tests/test_loop.py`
for the guard (23 on Windows), three more there for the loop, and one each in `tests/test_kit.py`,
`tests/test_review_fixes.py` and `tests/test_remote.py`. For the stale file in a mirror: four new unit checks
in `tests/test_remote.py`, and one change to a test helper. `tests/fake_hf.py`, the stand-in for the `hf`
command, took a file of the same size as soon as the remote copy was newer at all. It now needs more than a
second, as the real command does (huggingface_hub 2.4.0); the old rule hid the fault. No test was removed.

### What was reduced, and deviations from the prompt
- The view of item 1 was not written before the research (above).
- Research: four readers on cheaper models, web only. Eleven systems were read in depth where the prompt
  assumed about twelve, two more at README level. frontier-scout was used for the census, the whole-system
  alternatives and the admission test, not for its other rounds or its outside scouts.
- Item 4 had no sweep of its own: what was checked on 10 to 12 November counts as current, as the prompt
  allows. FAISS and optuna-mcp were checked again.
- One live campaign, and one reviewer instead of the deep-sweep skill. The reviewer saw the kit at `7233b9e`.
  The fixes after it, the two for remote runs among them, were checked by their tests and by me, not by a
  second reviewer.
- The 138 unfinished adopted rows were not built, nor any Trial or Assess row except the three built items.
- Text aimed at agents, not followed: the README of Orchestra-Research/AI-Research-SKILLs and an install route
  in SkyPilot's documentation tell a reader's agent to fetch and follow instructions from the network. The
  audit you pasted contains a prompt of its own and the advice to paste it into Claude Code; I treated both as
  part of the material.

### What another installer run would change in the real install
This is the forecast, written before the run; the run itself is the next section. Nothing was touched there
during the round. The real install was last upgraded on 12 November at 00:29, from kit
commit `2a3cd9d`. A dry run of the current installer on the rehearsal copy of its kit files, repeated at
commit `6e01543`, lists fifteen files as "upgrade", the manifest as "update" and 17 files as already up to
date: `.claude/hooks/nn_guard.py`, `.claude/agents/experiment-reviewer.md`, the scripts `expctl.py`,
`nnloop.py` and `nnremote.py`, and the references `data.md`, `evaluation.md`, `finetuning.md`, `loop.md`,
`optimization.md`, `performance.md`, `remote.md`, `stack.md`, `uncertainty.md` and `validity.md`. Its config,
`settings.json`, `CLAUDE.md`, `.gitignore`, journal and runs would stay as they are, and each replaced file
gets a backup, as in the two earlier runs.

What that brings there:
- **The guard for other checkouts.** Section 4 names three cases that the other project's own check still
  found allowed on 12 November. With the new guard, the same kinds of call get a question: from the main
  checkout, an edit of a frozen file or of `.claude/settings.local.json` in a registered worktree at another
  place, and of `.claude/settings.local.json` in a worktree under `.claude/worktrees/`, registered or not.
  Still allowed: a plain copy outside the project that git does not know. Tried with made-up calls in a
  throwaway project.
- **Searches of its linked data folder.** The data folder there is a link to a folder in another checkout of
  the same repository. I rebuilt that layout in a throwaway project with a practice pattern and put four
  calls to both guards. The guard of the version installed there refuses a read of a sealed file through the
  link, a read at its real place and a `cat`. It lets a search of the linked folder through, and in this
  layout such a search reads the sealed files (ripgrep 15.2.0). The current guard refuses all four. With the
  real install's own patterns the search turned out to be allowed, and rightly (next section).
- **The review's other fixes**: the final evaluation counted over all checkouts that hold the kit, the
  spellings of the final command and of Windows paths, the loop's corrections, the self-test's warning about
  sealed data in git, and for remote runs the ledger's time and the last pull's comparison of content.

That project's own check was not run again, its own patterns were not tried, and nothing was run there. The
kit's files there are committed since 12 November, so an installer run leaves fifteen modified files and
their backups uncommitted.

### The third installer run on the real install
You asked for it on 12 November, after this report was first delivered. It went as the second run did
(section 4): a rehearsal on a fresh copy of its kit files, a dry run on the install, then the run. The
installer came from an export of commit `8d53751`, whose code is that of `6e01543`, because another session
was editing the kit's working tree at the time.

- **What changed there.** The fifteen kit files and the manifest that the forecast lists, and nothing else
  of the 239 files in its `.claude` folder, its experiments and its runs. Each replaced file has a backup in
  its `.claude/backups/nn-training-20261112-180059/`. Config (19 keys), `settings.json`, `CLAUDE.md`,
  `.gitignore`, journal and runs are byte for byte as before. No run was live.
- **Checked by running, there.** `expctl selftest` passes; its one failing check is optional (no metric is
  configured, which is that project's choice). `expctl status` reads its five runs. The logger imports from
  the skill's folder. The guard lets a harmless read pass, refuses input it cannot read, refuses both
  configured final commands typed directly and asks for `expctl final-eval`. The 27 files of its skill, hooks
  and agents folders equal the kit's, apart from lines in five of them that name its interpreter.
- **What the new guard decides differently there.** I put the same made-up calls to the guard file as it was
  and as it is, with that install's own config. `git show <rev>:<a sealed path>` was a question and is a
  refusal. An edit of `.claude/settings.json` in a sibling worktree was allowed and is a question. A read of
  a sealed file, in the install and in a sibling worktree, was refused and still is. All ten other checkouts
  of that repository are the main one and worktrees beside the install; none is registered elsewhere.
- **A correction.** I had written that until this run its guard lets a search of its linked data folder
  through. That came from the throwaway project with a practice pattern (previous section). With the
  install's own config the search is allowed before and after the run, by its name, at its real place and
  with `rg` in the shell, and that is the right answer: of its eight sealed patterns one lies below that
  link, and the folder it names is not on disk. It would lie behind a second link, which the search tool does
  not follow. No sealed file was within reach of such a search. A read by that name is refused all the same.
  You then had me look into why the folder is missing: it is absent on purpose. That project's own documents
  say its hidden final test set was never downloaded, the entry seals the place where it would land, and a
  search by name of all eleven checkouts found no data of that name. What the look did turn up is a cache
  folder in a sibling worktree whose four files that project's plan calls never read: no sealed pattern
  covered it, and its guard allowed a read of them.
- **The never-read folder, sealed.** On your word I added it to that install's `sealed_paths` as a ninth
  entry: one plain pattern, the only change to the file. I put the same eight made-up calls to its guard
  before and after, through the command its settings register. Before, all eight were allowed. After, a read
  of a file in the folder, a Python read of it in the shell and a search of the folder are refused, and a
  `grep -r` over the folder above it is a question. Still allowed: a neighbour file, the search tool over
  the folder above (it skips the folder, which git ignores) and both searches of the whole install, which
  does not hold the folder. One pattern and not the three forms that config uses for its other sealed
  folder: its guard maps a path in any checkout back to a repository path, so the plain form covers the
  folder everywhere, and each form that begins with `**/` costs that guard a further walk of the project on
  every search of the whole install (measured there: 2.0 s with the five it has, 2.95 s with two more, no
  change with the plain one). The seal binds sessions that run in the install: the worktree that holds the
  folder has no kit config of its own.
- **Left there.** The sixteen changed kit files, which you then had me commit: one local commit of exactly
  those paths, not pushed (undo with `git reset --soft HEAD~1` there), whose message names the lines below.
  Also the backup folder, which git ignores there, and 16 lines in its guard record: 4 from the self-test's
  own probes and 12 from my made-up calls, marked `upgrade-check` (three on the final-evaluation rule, nine
  for the comparison above). None of those calls was carried out. From the sealing: the one-line config
  change, which you then had me commit as well (one local commit of that path, not pushed; undo with
  `git reset --soft HEAD~1` there while it is the newest commit), and 4 more lines in its guard record,
  marked `seal-check`, from calls that were not carried out either. Not run there: its two registered
  scripts, a final evaluation, that project's own check.

### What needs your decision
The questions of section 9 still wait (Hugging Face Jobs, Claude Code in WSL, Cursor, Codex, Docker Desktop,
the other project's scripts and final evaluation). New:
1. **The real install**: answered, the installer ran there a third time, the sixteen files it changed are
   committed there, the folder its first sealed pattern names is absent on purpose, and the never-read cache
   folder in its sibling worktree is sealed, with that config change committed there (above). Nothing new is
   open on it.
2. **What to build next.** My order: first numeric settings searched by the harness inside the loop, because
   six of the seven changes of the live campaign were such settings and each cost an agent session; then a
   second benchmark task, a small fine-tuning one, because every figure in this report comes from one task and
   fine-tuning is where the vendor skills are ahead. After those: a restart on a stall, and of the unfinished
   adopted rows a minimum agent version, the readiness report, a job object per run on Windows and a
   checkpoint helper. Each is a ledger row with the test it needs. Say which, or "in that order". Answered for
   the first three: they are built ("Round 3"). What remains of the order is in "Round 3", "What needs your
   decision", item 3.

## Round 3 (12 and 13 November 2026): three more items built

After round 2's report you had the first three items of my build order built ("Round 2", "What needs your
decision", item 2), in a session of its own. `ROUND2.md` had given the go-ahead for them. They had stayed
unbuilt because of the usage limit, and that limit shaped this work too: no research beyond what a build
decision needed, cheaper models for the subagents, and no campaign with a real agent. Commits: `395697f`,
`dbe0694`, `87a2f42`, `ddc7afa` (fixes after an independent review), `0f97004` and `b2f1fd3` (two faults in
existing features that the full test runs found), `687bb50`, `a945eeb` and `0f23999` (three small repairs, made
on 13 November after you said to) and those of this report. Nothing is pushed, and your real install was not
touched.

### In short
1. **The harness searches numeric settings** where a project's config sets `loop.search_trials`. The worker may
   leave the numbers of its change open. The harness then trains up to that many versions, each once on a seed
   that no seed panel uses, writes the best one's values into the code and puts that commit through the same
   keep rule as any other change.
2. **A second benchmark task**, `benchmarks/finetune/`: 30 seconds of fine-tuning a small chat model
   (SmolLM2-135M-Instruct with a LoRA adapter) on Banking77, scored by a frozen evaluator as the share of
   held-out messages whose intent the model names exactly. It ran on this machine: the starter script scores
   0.35 to 0.39, and one campaign of the loop kept and confirmed a higher learning rate, with the stand-in agent
   of the kit's tests in place of a real one.
3. **A campaign that stalls can go back** where the config sets `loop.restart_after`: after that many
   iterations without a keep it goes on from the commit before its last keep, and it ends on the best commit
   it found.
4. **None of the three is shown to raise results.** Each is tested with the stand-in agent, a script that makes
   the edits a test tells it to. No real agent session ran on any of them, and the comparison of arms
   (`pilot.py`) was not run on the new task. The search and the restart are off unless set: a project that
   sets neither runs the loop as before.
5. **The guard did not change.** `nn_guard.py` is byte for byte that of round 2, and so are the installer, the
   settings and the Codex and Cursor files. The sealed test set, the frozen evaluator and the protection of
   live runs are as they were ("Changes in the behaviour of existing features" below). Four files of existing
   features changed, each in a few lines: `runlog.py` and `expctl.py` (point 9), `runlog.py` again,
   `nnremote.py` and the status line (point 10).
6. **Tests**: all seven test files pass on native Windows and in WSL, each in three interpreters, at
   `0f23999`, the last code change, as they did at `b2f1fd3`. The two full runs on Windows before that each
   failed once, under Python 3.8: two checks at `ddc7afa` and one at `0f97004`. Those were the two faults of
   point 9. `tests/test_loop.py` has 196 checks on Windows and 197 in WSL (166 and 167 before this round),
   `tests/test_benchmarks.py` 35 (23 before), `tests/test_kit.py` 136 and 140 (134 and 138 before),
   `tests/test_remote.py` 73 (72 before) and `tests/test_runlog_units.py` 18 (16 before). The other two files
   are unchanged ("Tests" below).
7. **The ledger**: three rows went from Trial to Adopt and are finished. They are Adopt because they are built
   on your go-ahead, not because a measurement decided them, and each says that its effect is not measured. Of
   418 adopted rows, 280 are finished and 138 unfinished (415, 277 and 138 before).
8. **An independent review found one real hole, and it is closed.** The harness wrote the searched values
   through a link: a link at an editable path, made by an agent with a shell or by a version's training run,
   would have carried that write to a file outside the worktree. It now writes only into plain files of the
   worktree and checks that before every write. Three smaller findings are fixed as well, the other six are
   answered ("The independent review").
9. **The full test runs found two faults in existing features, and both are fixed.** Both come from Windows
   refusing a file for a moment while another process has it open or renames it. In the first, a training run
   could end at its start with a `PermissionError` when another process had one of the run's first records
   open. The kit's own helper for rented jobs is such a process, and in the tests the rented job runs on this
   machine. It showed once, as two failed checks of `tests/test_remote.py`. In the second, `expctl status`
   could report a live run as `stalled` for one call, when it opened the run's heartbeat in the instant in
   which the run replaced it. It showed once, as one failed check of `tests/test_kit.py`. A run now tries
   again for up to two seconds, as it already did for its result, and status looks again ("The faults the
   full test runs found").
10. **Three smaller faults seen on the way are repaired** (13 November, after you said to). A heartbeat whose
    rename Windows refused left its temporary file in the run directory. The remote side of a run listed the
    run directory in a way that fails before Python 3.12 when a training script removes a folder at that
    moment; for a rented job that would have ended the job. The status line read a run's heartbeat once, as
    status did. Each has a check that fails on the code before ("The faults the full test runs found", at
    its end).

### What was built, and why
| Item | What it is | Why | Commit | Test |
|---|---|---|---|---|
| Numeric settings searched by the harness (`second-look`, B1) | With `loop.search_trials: K` a worker may write numbers as lines `NAME = <number>` at the top level of an editable file and give their ranges in `PROPOSAL.json`. The harness trains up to K versions that differ only in those lines, each once on one seed outside both seed panels, commits the best one's values and decides that commit by the keep rule | In the live campaign of 12 November six of the seven trained changes were such settings, and each cost an agent session. In the one controlled comparison found, a classical optimizer did better inside a fixed numeric space than an agent that proposed the values (arXiv 2603.24647) | `395697f`, fixes in `ddc7afa` | `tests/test_loop.py`, unit checks and "campaign h": 18 checks |
| A fine-tuning task beside `charlm` (`second-look`, B2) | `benchmarks/finetune/`: an editable `train.py`, a frozen `evaluate.py`, `fetch_model.py` for the base model, the task's settings, the data in four files and a README with sources and licences. `new_project.py` and `pilot.py` take it with `--task finetune` | Every figure in this report comes from one task, and fine-tuning is where the vendor skills are ahead | `dbe0694` | `tests/test_benchmarks.py`, section 4: 12 checks |
| A restart when a campaign stalls (`second-look`, B5) | With `loop.restart_after: K`, after K iterations in a row without a keep the next worktree starts from the commit before the last keep. The commit that is left stays the campaign's result until a keep on the new line beats it on the seed panel | Both campaigns of 11 November kept one change and discarded every other idea from the same starting point. One study found a small edge for an agent that branches when it stalls (0.208 against 0.192 for a greedy loop, arXiv 2605.17373) | `87a2f42` | `tests/test_loop.py`, "campaign r": 12 checks |

How each works is in the skill's references, with date and source: `references/loop.md` ("A search by the
harness", "A restart when the campaign stalls"), `references/hpo.md` (section 8), `references/finetuning.md`
("Stack and environment") and `benchmarks/finetune/README.md`. The decisions behind them:

**The search.**
- The best of K versions is a selection. Made on the seed panel's runs, it would hand the keep rule a number
  that was picked for being high. So the trials run on a seed of their own (with seeds 1, 2, 3: on 7, after the
  second panel's 4, 5, 6), the confirmation never draws that seed, and the trial runs stay out of the noise
  estimate. That a version without effect is then kept no more often than any other change follows from this
  design. It was not simulated.
- The values are written into the code, not passed on the command line, because the confirmation and every
  later iteration train a commit with the campaign's one training command.
- Every trial is a training run that counts against the run limit. A search gets fewer trials when the limit
  has no room for K of them and the seed panel, and none is offered below two. A version whose values repeat
  an earlier version's is not trained again, so a search over a few whole numbers costs fewer than K runs.
- The harness writes its values only into plain files of the worktree. A file that is a link, lies below a
  linked folder or has a second name elsewhere (a hard link) is not searched, and the same is checked again
  before every write, because a version's training run could put a link there. Without the check the
  harness, which is not confined, would have written through such a link into a file outside the worktree,
  where a training run under bubblewrap cannot write itself. The review found this ("The independent review"
  below).
- The ledger row named random search or successive halving, and Optuna when installed. Built is a stratified
  random search and nothing else: at a handful of trials a model-based sampler is still drawing at random, and
  stopping trials early by rank is the riskiest speed-up (`references/hpo.md`).

**The fine-tuning task.**
- Base model: `HuggingFaceTB/SmolLM2-135M-Instruct` at one pinned revision, 135 million parameters,
  Apache-2.0, not gated. `fetch_model.py` downloads its six files (270 MB) once, with the standard library and
  without a login, and keeps a file only with the size and SHA-256 recorded in the script. Training and
  evaluation run offline afterwards.
- Data: Banking77 (13,083 customer messages with one of 77 intents, CC BY 4.0), in four files: 9,488 rows for
  training, 500 for the agent's own validation, 1,000 that the loop scores on and 1,000 for the final
  evaluation. The last two are sealed. 24 rows whose message occurs more than once were dropped, because some
  of them were in the source's training and test files at once.
- Evaluator: it loads nothing but a LoRA adapter in safetensors onto its own copy of the base model, asks with
  its own prompt in the model's chat format and compares the greedy answer with the intent's name. A run
  folder without such an adapter gets no score. So it executes nothing a run saved.
- Trainer: a plain PyTorch loop that watches the clock, rank 8 on the query and value projections, AdamW at
  2e-4, the loss on the answer only, `runlog` wired in. The ledger row named TRL. It is not used, because a
  fixed time budget needs a loop that can stop on time.
- The task lives in the kit's checkout beside `charlm`. `install.py` does not copy `benchmarks/` into a
  project, so an installed kit does not carry it.

**The restart.**
- The commit that is left stays the campaign's result. It is set aside as the best, the branch stays on it and
  the limits go on holding the runs of its confirmation. A keep on the new line moves the branch only when its
  mean over the seed panel beats that commit. However a campaign stops, it rests on its best commit, and the
  confirmation compares that one with the start.
- The worker reads the history of the code in front of it. A change that was kept elsewhere stays in the
  list, marked as not in that code.
- Two sessions in a row that decline also start a restart while there is a commit to go back to. At the
  starting commit they end the campaign as before.
- It differs from the paper's agent, which branches from its best few code versions: the kit goes back by one
  keep on its single line. Choosing the better of two lines on the seed panel is one more selection on the
  same seeds, which is what the confirmation on fresh seeds is for.

### What ran on the fine-tuning task
All on this machine (RTX 5090, native Windows, Python 3.11, PyTorch 2.9.1 with CUDA, Transformers 5.22.2, PEFT
0.21.2), in a temporary environment, because the machine's own Transformers install does not import ("Things
to know" below).
- The starter script, run directly with seeds 1, 2 and 3: 0.372, 0.386 and 0.351 on the loop's validation file,
  with about 360 steps in the 30 seconds. A run takes 44 seconds with model loading and saving, the evaluator
  16.
- The same script with a learning rate of 1e-3, seed 1: 0.691. The starter leaves room on purpose.
- One campaign of `nnloop.py` on a project made by `new_project.py --task finetune`, 12 runs in 13 minutes.
  Baseline 0.349, 0.364 and 0.335 (353 steps: fewer fit into the 30 seconds under the loop). The evaluator's
  self-test passed. The stand-in agent's one change, the learning rate of 1e-3, was kept: 0.681, 0.681 and
  0.689, a gain of 0.334 against a margin of 0.025. Two sessions then declined, and the confirmation on three
  fresh seeds held: 0.667 against 0.332, a gain of 0.335 against a margin of 0.029.
- What that shows: the task runs under the loop. The sealed files are absent from the worktree, the model is
  linked into it, the runs log `train/loss` and `dev/exact`, and git shows nothing new in the project but the
  journal and the loop's records. It does not show what an agent reaches: the change was mine, chosen because
  the direct run had shown that it helps.

### Tests
A full run is what "Round 2", "Tests" describes: a clean clone of one commit, all seven files, three
interpreters per platform. The number of checks per file:

| Commit | Platform | benchmarks | kit | loop | ports | remote | review_fixes | runlog_units | Failed |
|---|---|---|---|---|---|---|---|---|---|
| `6e01543`, round 2's last code change | Windows | 23 | 134 | 166 | 106 | 72 | 38 | 16 | none |
| | WSL | 23 | 138 | 167 | 105 | 72 | 40 | 16 | none |
| `87a2f42`, the three items | Windows | 35 | 134 | 193 | 106 | 72 | 38 | 16 | none |
| `ddc7afa`, with the review's fixes | Windows | 35 | 134 | 196 | 106 | 72 | 38 | 16 | 2 of the 72 in `remote`, under Python 3.8 |
| | WSL | 35 | 138 | 197 | 105 | 72 | 40 | 16 | none |
| `0f97004`, with the fix for that failure | Windows | 35 | 134 | 196 | 106 | 72 | 38 | 17 | 1 of the 134 in `kit`, under Python 3.8 |
| | WSL | 35 | 138 | 197 | 105 | 72 | 40 | 17 | none |
| `b2f1fd3`, with the fix for that one | Windows | 35 | 135 | 196 | 106 | 72 | 38 | 17 | none |
| | WSL | 35 | 139 | 197 | 105 | 72 | 40 | 17 | none |
| `0f23999`, with the three repairs of 13 November, the last code change | Windows | 35 | 136 | 196 | 106 | 73 | 38 | 18 | none |
| | WSL | 35 | 140 | 197 | 105 | 73 | 40 | 18 | none |

At `0f23999` every file passed in all three interpreters on both platforms (logs under
`%TEMP%\nnkit-upgrade\logs\`, label `r3e`; 47 minutes on Windows, 13 in WSL), as at `b2f1fd3` (label `r3d`).
Before that, at `0f97004` and at `ddc7afa`, WSL had passed in full and Windows in two interpreters. Under the
clean Python 3.8 one check of `tests/test_kit.py` failed at `0f97004` (label `r3c`) and two checks of
`tests/test_remote.py` at `ddc7afa` (label `r3b`). Those are the two faults described below. At `87a2f42`,
before the review's fixes, the Windows run had passed (label `r3`); WSL was not run at that commit. `ports`
has one check fewer under Python 3.8, as before. In WSL the training runs of the loop's tests are confined
by bubblewrap. On Windows they are not, as before.

No check that existed before this round was changed or removed. New: 18 checks for the search and 12 for the
restart in `tests/test_loop.py`, and 12 for the fine-tuning task in `tests/test_benchmarks.py`. Those twelve
need no PyTorch, no GPU and no network: they check the data files, the task's settings, the model's pins, that
the fetch keeps no file of another size or checksum, that the evaluator gives no score for a folder without an
adapter, and the project creator. The commit with the review's fixes added three of the 18 and changed what
some of this round's own search checks expect, in line with the fixes: a range that holds one version costs
one trial where it cost three, and the worker's prompt says "up to". Two new checks in
`tests/test_runlog_units.py`, two in `tests/test_kit.py` and one in `tests/test_remote.py` belong to the
faults and the repairs described below.

### The independent review
After the three commits a subagent on a cheaper model read the search and the restart in `nnloop.py` against
`references/loop.md`. It had no part in writing them, ran nothing and did not read the tests. It reported no
serious defect in the restart and ten findings, all small or conditional. I checked each against the code:

| Finding | What I did |
|---|---|
| 1. The harness wrote the searched values through a link: an editable path that is a symbolic link made it rewrite the link's target, outside the worktree | Fixed, and widened: also a file below a linked folder, a hard link, and a link that a version's training run puts in place while the search runs. Two checks, one of them a campaign whose training run swaps its own script for a link to a file outside the project |
| 2. Before the first keep nothing is held back, so the trials of an early search can use the runs that a confirmation or a second look would need | No change: the hold-back starts with the first keep for every iteration. `references/loop.md` and `docs/GUIDE.md` now say to leave room in the run limit |
| 3. A stop request or a limit during the trials leaves the search marked as tried, so the same search from the same commit is a `duplicate` after a `resume` | No change: every interrupted iteration behaves so. A search loses up to K runs that way where another iteration loses a seed panel |
| 4. An `int` range with fewer whole numbers than K trained the same version more than once, and the end numbers of an `int` range got half the share of the others | Fixed: a repeated version is left out, and every whole number gets the same share. One check |
| 5. "The values the code has now" compares text, so `1e-3` against `0.001` counts as a change | No change: rare, and such a commit goes through the keep rule like any other change |
| 6. `"int": "false"` and `"log": "false"` counted as true | Fixed: both must be `true` or `false`, anything else makes the iteration `invalid` at no cost in runs. Checked |
| 7. A campaign begun with the earlier `nnloop.py` and resumed with `restart_after` cannot go back beyond a keep made before the upgrade | Stated in `references/loop.md`; it was already in the table of changes below |
| 8. After a kill and a `resume`, the commit that was left can hold fewer baseline runs than the campaign had trained | No change: a later return to that commit trains those seeds again, at most one seed panel of runs. The scores are right either way |
| 9. A byte-order mark before a setting on the first line, a line ending of a lone carriage return, or a `NAME = <number>` line at the start of a line inside a multi-line string | No change: the first two end as `invalid` at no cost in runs; the third makes versions that do not differ, and the keep rule treats the result like any change without effect |
| 10. `loop.search_trials` or `loop.restart_after` given as `Infinity` ended in a traceback | Fixed: refused at start with a message. Checked |

It found nothing in the rest of what it was asked to follow: whether the branch, the state, the journal and the
confirmation agree after restarts, stops and resumes; whether the limits hold; whether the search's choice can
leak into the runs the keep rule decides on; the behaviour without the two keys; and whether
`references/loop.md` matches the code.

### The faults the full test runs found
Two full runs on Windows failed one file each, both under Python 3.8. Each file had passed in the other two
interpreters, in WSL and at the commit before. A second run would probably have passed each time. I looked
for the cause instead, as the working notes ask. Both faults are of one kind: Windows refuses a file for a
moment while another process has it open or renames it, which Linux does not.

**A training run that ended at its start.** At `ddc7afa` two checks of `tests/test_remote.py` failed. Both
are about the first rented job of that file: its run did not show as completed, and its results were not in
the mirror. None of the files that test exercises had changed in this round.

- **Reproduced.** A script repeated that one check on the tested clone under Python 3.8. The 24th repeat
  failed the same way, and its files were kept. The training script had ended in its first tenth of a second
  with `PermissionError: [WinError 32] The process cannot access the file because it is being used by another
  process`, on the temporary file that becomes `config.json`.
- **Cause.** `RunLog` writes each of its records to a temporary file and renames that. Windows refuses the
  rename while another process has either file open. The kit's helper on the remote side of a rented job
  copies the run directory to the result store at short intervals (every 0.3 seconds in the test, every 30
  by default), and it had the temporary file open in that instant. `result.json` has been written with 40
  attempts for this reason since 11 November (`eaf3ef0`). The three records a run writes when it starts
  (`manifest.json` where the run has none yet, `config.json`, `env.json`) had one attempt.
- **Whom it could hit.** A real Hugging Face job runs on Linux, where a rename does not fail this way. The
  fault needs Windows where the training runs and a second process that opens the run's files: the tests'
  stand-in for rented jobs, an `ssh` target that is a Windows machine, or a scanner or sync program beside a
  local run. I know of no real run that it stopped.
- **Fix** (`0f97004`): the three writes get the same 40 attempts, 50 milliseconds apart. A heartbeat still
  gives up at once, as before: a missed heartbeat costs nothing.
- **Checked.** A new check in `tests/test_runlog_units.py` refuses the rename twice for every file and expects
  the run to start; it fails on the code before the fix. Beside a real second process that copies every file
  of the folder, 7 of 600 run starts failed before the fix and none of 600 after it. The check that had
  failed ran 120 more times on the fixed code, three at a time, and passed each time.

**A live run that read as stalled.** At `0f97004` one check of `tests/test_kit.py` failed. Right after the
status line had shown the test's run as running, `expctl status` did not report it as `running`. The run went
on and completed, and the later checks on it passed. The log does not say which state the check saw. Of the
files that test exercises, this round had changed only `runlog.py`, in the three lines of `0f97004`, and
those act while a run starts; this run had started seconds before.

- **Cause.** Status opens a run's `heartbeat.json` once per call. Windows refuses that open in the instant in
  which the training run replaces the file. Status then has no heartbeat for a run whose process is alive. It
  calls the run `stalled`, or `starting` while the run is younger than the limit for a stale heartbeat. The
  answer has no step and no metrics, and names the refusal under `file_errors`.
- **Reproduced**, but not at the pace of the test. A live run that wrote a heartbeat every 0.2 seconds, as
  the test's run does, was asked for its state under Python 3.8. 3,157 readings a few tenths of a second or
  30 milliseconds apart all said `running`. Of 49,437 readings without a pause, 38 said `stalled`, each with
  `PermissionError: [Errno 13] Permission denied` on the heartbeat. A single reading therefore goes wrong
  rarely. That the failed check was such a reading is my conclusion, not something its log shows.
- **Whom it could hit.** Every reading of a live run on Windows goes through the same function: `status`,
  `watch`, the hook at the start of a session, the guard and the loop. The wrong answer lasts for one
  reading. It can raise the alert for a stalled run, and it ends `expctl watch --until alert`. The guard's
  protection does not depend on it, because `stalled`, `starting` and `running` all count as a live run.
  Unless a script asks otherwise, `RunLog` writes a heartbeat every 15 seconds and with each validation
  metric, so the instant comes far less often than in the tests. I know of no real run that it touched.
- **Fix** (`b2f1fd3`): `read_json` in `expctl.py` looks up to three times, 20 milliseconds apart, when the open
  is refused. Every other error is reported at once, as before.
- **Checked.** A new check in `tests/test_kit.py` refuses the open twice and expects the record, then three
  times and expects the error. It fails on the code before the fix. The readings without a pause, repeated on the
  fixed code, all said `running`: 47,018 of them.

**Three smaller faults, repaired on 13 November.** Three more things showed while I looked. I left them at
first: no check had failed on them, and they are not part of this round's three items. You then said to
repair them. Each repair is a few lines and has one check.

- **A refused heartbeat left its temporary file behind** (`687bb50`). A heartbeat whose rename Windows
  refuses gives up at once, and its temporary file (`.heartbeat.json.<pid>.<hex>.tmp`) stayed in the run
  directory. The mirror of a remote run copied such files too. In the repeats on this machine that was two
  to three files a run, with a heartbeat every 0.2 seconds and a copy every 0.3. On Linux no rename is
  refused. `runlog.py` now removes the temporary file of a write that gives up. Where Windows refuses that
  as well, because the other process still holds the file, the run's next write removes it. A file that is
  still held at the run's last write stays. The check, in `tests/test_runlog_units.py`, refuses two renames
  and the first removal: it expects one temporary file after the first write and none after the second.
- **The remote side's listing of the run directory** (`a945eeb`). The remote helper listed the run directory
  outside its error handling (`copy_out` for rented jobs, `op_pack` for `ssh` targets, both in
  `nnremote.py`). When a training script removed a folder of its run directory during that listing, an old
  checkpoint folder for example, the listing raised `FileNotFoundError` under Python 3.8 to 3.11. I had
  tried `copy_out` alone, beside a thread that creates and removes folders: it failed within a few rounds on
  Windows (3.8 and 3.11) and in WSL under 3.8, and ran 6,868 rounds without an error in WSL under 3.12.
  What follows is from reading the code, not from a run: for an `ssh` target the next poll listed again,
  and for a rented job the helper is the job's own command, so the job would have ended and the run shown
  as cut off from outside. No test and no benchmark run removes a folder, so nothing had shown it. Both
  functions now list with `os.walk`, which passes over a folder that is gone. The listing also leaves out
  the kit's own temporary files, so the mirror no longer takes them. The check, in `tests/test_remote.py`,
  copies a run folder 300 times while a thread creates and removes folders in it. It expects no error, the
  run's metrics in the store and no temporary file there. `op_pack` shares the listing and had no such
  check of its own; round 4 gave it one and narrowed what the listing leaves out (`4fe23a0`).
  `references/remote.md` describes both changes.
- **The status line read a heartbeat once** (`0f23999`). `nn_statusline.py` reads the runs' records itself,
  and a refused open left a live run out of the line until the next refresh. It now looks up to three
  times, 20 milliseconds apart, as `read_json` in `expctl.py` does since `b2f1fd3`. The check, in
  `tests/test_kit.py`, refuses the first two opens of a run's heartbeat and expects the run in the line.

I ran the three changed test files on the code before the repairs and on the repaired code, on Windows under
Python 3.8 and 3.11. Before, each new check fails and every other check passes. After, all pass.

### Verified by running, from documentation only, unverified
**By running.**
- The search and the restart: their checks, with the stand-in agent and a toy project whose score is a number
  in the training script plus fixed noise per seed, on both platforms in three interpreters each. The restart's
  campaign covers two restarts, a keep on a new line that does not beat the commit that was left, a resume,
  and a keep that does beat it.
- The fine-tuning task: the runs above, on native Windows with one GPU.
- The download of the base model: once, from the Hugging Face Hub, without a login.
- The fixes after the review. A campaign in which a version's training run replaces its own script by a link
  to a file outside the project: the harness writes nothing more, the iteration is `invalid` and that file is
  unchanged. The link is a symbolic link in WSL, where the run is confined by bubblewrap, and a hard link on
  this Windows account, which may not create symbolic links. The rule itself, on a hard link, a symbolic link
  and a file below a linked folder (on Windows: a hard link and a junction). The equal shares and the left-out
  repeats of the draws, and the refusals.
- The fault in `runlog.py`: the failure itself on the tested clone, its cause from the kept files of that
  run, and the fix by the new unit check, by run starts beside a real second process and by repeats of the
  failed check ("The faults the full test runs found").
- The fault in `expctl.py`: the refused open and the wrong state on a live run, with readings that follow each
  other without a pause, and the fix by the new check and by the same readings on the fixed code. The failed
  check itself did not fail again.
- The three repairs of 13 November: each by its new check, which fails on the code before the repair and
  passes on the repaired code (Windows, Python 3.8 and 3.11), and by the full runs at `0f23999`.

**From documentation only.**
- The model's licence and that it is not gated: its page on the Hub, read on 12 November. The dataset's
  licence: its repository.
- The two papers behind the search and the restart (arXiv 2603.24647, arXiv 2605.17373): read by subagents on
  cheaper models, the second one partly from a machine summary of the page. Their figures were not
  cross-checked, and the references say so.

**Unverified or not measured.**
- Whether the search, the restart or the new task's starter raises what a campaign ends on. Each needs
  campaigns with real agent sessions, with and without it at an equal run limit. Round 4 measured the search
  with the stand-in agent ("Round 4", "The measurement of the search").
- A real agent with the search offer: whether it writes its numbers as the lines the harness needs and names
  sensible ranges. A search space that is not one costs no run and makes the iteration `invalid`.
- A real agent after a restart: whether the shortened history leads it to another direction.
- The fine-tuning task on Linux or WSL, without a GPU, and with other versions of the libraries. In WSL only
  its test file ran. Also not run on it: a real agent session, and `pilot.py`.
- Whether the base model saw Banking77 in its own training. The dataset is public and older than the model.
  The sealed files keep an agent from tuning on the messages that decide; they do not make the data unknown.
- A value for `search_trials` or `restart_after` that works well. None was tried on real campaigns.
- Changing either setting between a stop and a `resume`: the code reads them at every start, and no test does
  it.
- A link that an agent session itself commits at an editable path: the rule that refuses it is checked on
  files, no campaign does it. A symbolic link on native Windows: this account cannot create one.
- A process that swaps a file in the instant between the harness's check and its write. The two are separate
  steps and nothing tries it. It needs a training run that leaves a process behind. Whether one outlives its
  run was not tested; the kit starts bubblewrap without a process namespace of its own.
- The fixed start of a run on a Windows machine used as an `ssh` target, or beside a virus scanner or a sync
  program. Tried were the stand-in for rented jobs and a copying process of my own.
- That the one failed check of `tests/test_kit.py` was a refused open of the heartbeat. Its log does not name
  the state it saw, and at the test's pace the refusal did not show in 3,157 readings.
- The three repairs of 13 November on a real rented job, on a real `ssh` target or beside a virus scanner.
  Their checks make the refusals themselves (a rename, a removal and an open that the test refuses), and a
  thread of the test removes the folders. That the listing fault would have ended a rented job is from
  reading the code; no job was lost to it.

### Changes in the behaviour of existing features
The sealed test set, the frozen evaluator and the protection of live runs are not weaker.

**Guard: nothing.** No change in what it asks, denies or allows. The file is identical to the one tested in
round 2 (the same git blob at `6e01543` and now), and every check of `guard_tests` passes unchanged. The
guard lists the live runs through `expctl`, so it reads through the function that changed there (below). Its
answers are the same: a run that read as `stalled` for a moment counted as live, as a running one does. A
record that stays refused costs a guard call 40 milliseconds more than before; the hook's limit is 20 seconds.

**`runlog.py`: a run's first records are tried again.** `RunLog` writes `manifest.json` (where the run has
none yet), `config.json` and `env.json` with up to 40 attempts, 50 milliseconds apart, where it made one. On
Windows a run therefore starts although another process holds one of these files for a moment; before, it
ended with `PermissionError`. A refusal that lasts is still an error, two seconds later than before. On Linux
and macOS a rename is not refused this way, and a run starts as before.

**`runlog.py`: a write that gives up removes its temporary file** (13 November). `RunLog` writes each record
to a temporary file and renames it. When a write gives up because the rename is refused, it now removes
that temporary file, or the run's next write does where Windows refuses the removal too. Before, the file
stayed in the run directory: one for every refused heartbeat, because a heartbeat gives up at the first
refusal. The write raises the same error as before, and a write that succeeds does what it did. Nothing
else in the file changed in this round.

**`expctl.py`: a record that cannot be opened is looked at again.** `read_json` is the function through which
`expctl` reads its JSON records; the loop, the remote module, the guard and the session hook use it too,
directly or through `expctl`'s view of the runs. It makes up to three attempts, 20 milliseconds apart, when
the open is refused with `PermissionError`, where it made one. On Windows a status call therefore no longer
reports a live run as `stalled` or `starting`, without its step and metrics, because it met the instant in
which the run replaced its heartbeat. A file that stays refused is reported as before, 40 milliseconds later;
on Linux and macOS that is a file the user may not read. A missing file, a file that is not JSON and every
other error are handled at once, as before. Nothing else in the file changed.

**`nnremote.py`: what the remote side copies of a run** (13 November). Two things changed in how the remote
side lists a run directory, for a rented job's copy to its store and for the pull from an `ssh` target.
First, a folder that vanishes during the listing is passed over under every Python version; before, the
listing raised under Python 3.8 to 3.11. Second, a file whose name starts with a dot and ends in `.tmp` is
not copied. That is the form of the kit's own temporary files, which are gone a moment later; a file of
that form which a training script writes itself stays out of the mirror too (round 4 narrowed this to the
exact form of the kit's temporary files, commit `4fe23a0`). The list of checksums comes
from the same listing, so the last pull is complete without such files. Nothing else in the file changed:
what is sent to a target, the money, the teardown and the comparison of checksums are as they were.

**`nn_statusline.py`: a record that cannot be opened is looked at again** (13 November). The status line
reads the runs' records itself. It makes up to three attempts, 20 milliseconds apart, when an open is
refused with `PermissionError`, where it made one. On Windows a live run therefore no longer drops out of
the line for one refresh. A file that stays refused costs the line 40 milliseconds more. The status line
only prints: the guard does not read through it, and nothing is decided on what it shows.

**What the loop's decisions rest on, with the new settings.**
- Search: the frozen evaluator scores every trial in the harness's own process, as it does every other run.
  The agent's change is scanned and held to `editable_paths` before the first trial. The harness's own writes
  change nothing but the numbers of the named lines, and only in plain files of the worktree, which it checks
  before every write. The keep rule decides on the seed panel, whose runs took no part in choosing the
  version.
- Restart: the keep rule compares a change with the commit it started from. The branch, the journal and the
  confirmation follow the best commit, and the confirmation still counts every change the campaign trained,
  on every line.

**The loop without the new settings.** A campaign decides as before. What differs:

| What | Before | Now |
|---|---|---|
| Ledger row of an iteration | no record of where it started | a field `base`, the commit its worktree started from |
| `state.json` | | new keys `line` (the earlier best commits, after the first keep) and `stall` (iterations in a row without a keep) |
| Seeds of the confirmation | drawn outside both seed panels | also never the seed after the second panel, which a search would use. This matters only for a seed panel in the range the confirmation draws from, 1,000 to 99,999 |
| A campaign begun with the earlier `nnloop.py` and resumed | | its rows without `base` count as started from the starting commit. With `restart_after` it cannot go back beyond a keep made before the upgrade |
| Configuration | `loop.search_trials` and `loop.restart_after` were unknown keys and ignored | read; a value that is not a whole number (at least 2 and at least 1) is refused at start |

**The loop with the new settings.**
- `loop.search_trials`: the worker's prompt gains one paragraph that offers the search. A ledger row of a
  search carries `search`, `trials` and `values`. A trial's run is named `<campaign>-i<N>t<J>-s<seed>` and
  carries the tag `values`. The worker's history and the journal say what a search found. New reasons for a
  status: `invalid` for a search space that is not one, for a setting without exactly one such line in a plain
  file of the worktree, and for a file that became a link while the versions trained; `discard` when the best
  version has the values the code has now; `duplicate` for the same search from the same commit.
- `loop.restart_after`: a ledger row `restart` (`iter`, `left`, `commit`, `best`). `state.json` holds `best`
  while the campaign works on an earlier commit, and `nnloop status` then shows that commit's score as
  `best_score`. A `keep` no longer always moves the branch (above). Two declining sessions restart the
  campaign where they would have ended it. The worker's history leaves out the iterations made on top of what
  was left and marks a kept change that is not in the code. The journal counts the restarts and marks such
  changes.

**Benchmarks.**
- `benchmarks/pilot.py`: the last line of the prompt it gives every arm asks for "the dev score before and
  after" where it said "the dev loss", and its progress line says "test score". For `charlm` the number is
  still a loss and lower is still better. A pilot on `charlm` from now on therefore differs by that word from
  the two that this report records.
- `new_project.py` and `pilot.py` already took `--task`; `finetune` is a second value for it.

**Documentation.** `references/loop.md`, `hpo.md` and `finetuning.md`, `README.md` and `docs/GUIDE.md` describe
the three items. `references/finetuning.md` also gained a note from this work: PEFT 0.21.2 treats any
importable `bitsandbytes` as installed, so an empty leftover folder of that name makes `get_peft_model` fail.
`references/remote.md` says, since 13 November, what the copy of a remote run leaves out and that it goes on
when a folder of the run vanishes.

**Tests.** `tests/test_loop.py` has 30 more checks, `tests/test_benchmarks.py` 12 more,
`tests/test_runlog_units.py` and `tests/test_kit.py` two more each and `tests/test_remote.py` one more. None
that existed before this round was removed or changed.

### Things to know
- **This machine's own Transformers install does not import.** The system Python has transformers 4.57.3 and
  huggingface-hub 1.15.0, which that version refuses at import, and an empty leftover folder `bitsandbytes`
  in its site-packages. I changed neither, because system packages are yours to change. The fine-tuning runs
  used a temporary environment under `%TEMP%\nnkit-upgrade\ft-venv` that takes PyTorch from the system and has
  the versions `references/finetuning.md` names. A fine-tuning project on this machine needs such an
  environment, or the system packages repaired.
- **The base model is on disk here, not in git.** `fetch_model.py` put it into `benchmarks/finetune/model/` in
  this folder (270 MB, git-ignored), and the test project got a copy. A clone does not have it and fetches it
  with that script.
- **Downloaded for this work**, after a look at the licences: the base model (Apache-2.0) and the two Banking77
  files (CC BY 4.0), and into the temporary environment the PyPI packages of the fine-tuning stack.

### What was reduced, and differences from the ledger rows
- No campaign with a real agent on any of the three, and no pilot on the new task: each costs subscription
  usage, and the rows' trials need several campaigns.
- The search has no successive halving and no Optuna. The trainer of the new task does not use TRL. The
  restart goes back by one keep where the paper's agent branches from its best few versions. Each row says so.
- The fine-tuning task was not run in WSL.
- The check before the harness's writes is not safe against a process that swaps the file at that instant
  ("Unverified" above). Closing that needs the file opened through directory handles on Linux, or a process
  namespace for bubblewrap runs so that a run can leave nothing behind. Neither is built.
- The review covered the search and the restart in `nnloop.py`, not the fine-tuning task's scripts.
- The three repairs of 13 November are checked with refusals and vanishing folders that the tests make, not
  on a real remote target ("Unverified" above). The listing on the launching side (`bundle` in
  `nnremote.py`) is as it was: it reads the paths that the config names and the directory of a run that has
  ended, where no training script is at work.

### What needs your decision
The questions of section 9 still wait. From this round:
1. **Whether to measure any of the three.** The cheapest informative run is one campaign with a real agent on
   the fine-tuning task with `loop.search_trials` set, about 40 runs of 44 seconds plus the sessions. It would
   show whether an agent uses the search offer as meant. It would not show a gain: that takes campaigns with
   and without, several each way. Round 4 ran those for the search with the stand-in agent ("Round 4", "The
   measurement of the search").
2. **This machine's Transformers install**: repair it or leave it. Nothing in the kit needs it. A fine-tuning
   project started with the system Python does.
3. **What to build next.** Of my earlier order these remain: a minimum agent version, the readiness report, a
   job object per run on Windows and a checkpoint helper, and of the undecided rows a repair attempt after a
   crash. The three small repairs that stood here are made (point 10 of "In short").

## Round 4 (12 and 13 November 2026): the first four of the ranked list, and round 3's repairs looked at again

After round 3 you asked what else would improve the kit, ranked by benefit, and then for the first four items
of that list ("Top four"). While I built them, the session of round 3 finished its three repairs, and you
gave me its conclusion to check: what I could fix and improve on it. This section covers both. The usage
limit shaped the work as before: no research beyond what a build needed, cheaper models for the two
reviewers, and no campaign with a real agent. Commits: `43adda1` to `00be575` (29) and those of this report.
Nothing is pushed. During the round I only read, in aggregate, your real install's guard record and the list
of the repository's checkouts; nothing was run or changed there. On 13 November, after the report, you had
the installer run there a fourth time, which brought it this round and round 3 ("The fourth installer run
on the real install" below).

### In short
1. **The guard asks before a recursive command over the project root when sealed files lie on disk below
   it.** That closes the gap which the 23 October guard kept and which this report named until now: `grep
   -r`, `find`, `ls -R`, `tree`, `tar`, `zip`, `cp -r`, `rsync` and their PowerShell and `cmd` forms. A
   command passes without a question when it names folders that hold no sealed file (`grep -rn x src
   tests`), when it gives a file filter that leaves the sealed files out (`--include='*.py'`, `-name
   '*.py'`, `--exclude-dir=data`), or when no sealed file is on disk. `rg`, `git grep` and the agent's own
   Grep tool pass where git's ignore rules keep them away from the sealed files, and are asked about where a
   flag, a glob or an ignore file takes that away. Where nobody can be asked, a question is a refusal, with
   the hint to name folders or to filter by file type. One limit stays: the guard looks at no more than
   20,000 files per folder it walks, so in a tree larger than that a sealed file can go unseen ("What was
   built, and why", "The question at the root").
2. **Six smaller gaps of the guard are closed**, most of them seen in the look at your real project. A
   whole-project search no longer walks the tree once for every sealed pattern (1.81 s became 0.40 s on a
   made-up project of 15,000 files with five patterns). A `cd` behind a blank, a keyword or a wrapper is
   followed: ` cd data && cat test/labels.csv`, with a blank in front, read a sealed file without a
   question and is refused. The two subagents' own hook blocks a call when the hook cannot run. A recursive
   command over another checkout of the repository is judged by the sealed files there. `expctl selftest`
   warns when the repository has checkouts in which no guard runs, and `install.py --worktrees` registers
   the guard for sessions started in them. That option is the one place where the installer writes outside
   the target project, and it does so only with the flag.
3. **The loop's self-test has two more cases, and a project can name controls.** A folder that holds only a
   run's records must get no score. A full copy of a baseline run, in which every number with a fraction in
   the run's records and its log is moved, must get the run's score. With `loop.controls` a project names
   runs that cannot have learned the task, each with the score it may not beat; one that beats it stops the
   campaign before any agent session. The character-model task has two, a constant predictor and a model
   trained on shuffled text. Run live, they scored 4.174 and 3.310 against floors of 4.174 and 3.300, where
   the baseline scores 1.67 to 1.69.
4. **The search of numeric settings is measured, and it stays off by default.** With the stand-in agent and
   real training, three pairs of campaigns per task at 18 runs. On the fine-tuning task the campaigns with
   the search ended on a confirmed gain of 0.42 against 0.31 by hand; two pairs differ by 0.18 and the third
   by -0.02. On the character model nothing was kept in either arm. The rule fixed before the measurement
   asked for a gain on both tasks, so `loop.search_trials` stays something a project sets ("The measurement
   of the search").
5. **Round 3's three repairs hold, and beside them I found and fixed five faults.** The twin of the repaired
   writer, in `expctl.py`, left its temporary file in the same way, and both writers left it when the write
   itself failed. The remote side's new filter kept a training script's own `.tmp` files out of the mirror.
   A resume that could not start cost the ended run its exit record, so the run showed as lost. And status
   could show a run that had just ended, or had just been killed, as lost for one look, which ended `expctl
   watch` with the wrong state ("Round 3's repairs, looked at again").
6. **Two reviewers without the working context reported 28 findings, and all are fixed or answered.** One
   read the guard twice (11 findings, then 7 more in the fixes), one the installer and the loop (10). Two of
   the guard findings were holes that this round's own root check had opened. They were closed before
   anything reached the main branch or your install. Most of the others were older ways to reach sealed
   files that the closer look made visible ("The independent review").
7. **The guard is stricter than before in many forms, and you will notice it.** Commands that explore the
   whole project are asked about, in an unattended session refused. So is a move or a rename of a folder
   that holds sealed files, and a command word in quotes (`"git" push`). A training command that names a
   folder and a path that exists only below it as a sealed file is refused (`python train.py --data-dir data
   --eval-file test/labels.csv`). An error inside the guard now asks about reads too, and a check that takes
   the guard longer than 12 seconds ends as a question. I ran 153 examples against the guard before and
   after; the table under "Changes in the behaviour of existing features" gives both answers.
8. **Tests**: all seven files pass at `00be575`, this round's last code change, in WSL and on native
   Windows, in three interpreters each. `tests/test_kit.py` has 363 checks on Windows and 367 in WSL (136 and
   140 before this round), `tests/test_loop.py` 210 and 211 (196 and 197), `tests/test_ports.py` 120 and 121
   (106 and 105), `tests/test_remote.py` 75 (73) and `tests/test_benchmarks.py` 39 (35). The other two files
   are unchanged ("Tests").
9. **The ledger**: of 422 adopted rows, 288 are finished and 134 unfinished (418, 280 and 138 before). Four
   rows that were unfinished are finished: the self-test's fixtures, the controls, and two on the
   subagents' hook. The new note `round4` has seven rows: four adopted and finished, two rejected, one
   undecided (controls for the fine-tuning task).
10. **Your real install has this round since 13 November.** Until then it ran the guard of round 2's third
    installer run. The fourth installer run brought it rounds 3 and 4, and the fifteen files it changed are
    committed there ("The fourth installer run on the real install"). Registering the guard in that
    repository's other checkouts is a decision of its own and waits for your word ("What needs your
    decision").

### What was built, and why
| Item | What it is | Why | Commit | Test |
|---|---|---|---|---|
| The question at the project root (list item 2) | For each command of a line the guard works out the tool, its file filters and the folders it sweeps, looks on disk for sealed files below them, and asks when the command could read one | The 23 October guard looked for sealed files below every folder except the root, so the commonest exploring commands could print sealed data | `e7a69dc`, `d02137e`, `8e69154`; reworked after the review in `c72c576` to `34000d5` and `df54cdd` | `tests/test_kit.py`, `guard_tests` and the guard section: 227 more checks in the file, nearly all of them guard cases |
| One walk per searched folder (item 1) | A search of a folder walks its tree once for all sealed patterns | On a large project each `**/` pattern cost one walk of the whole tree per guard call | `43adda1` | `tests/test_kit.py` |
| A `cd` in more places (item 1) | A `cd` is followed behind a leading blank, an indent, `then`, `do`, `time`, `builtin`, `cd --`, `cd -P` and `Push-Location` | It was seen only at the start of a line or behind `;`, `&`, a pipe sign, `(` or `{`, so a sealed file could be read behind one without a question | `4b75776` | five cases in `guard_tests` |
| The subagents' hook blocks when it fails (item 1) | `onFailure: block` on the read-only hook in both agent files | Without it Claude Code lets a call through when the hook cannot run | `d07606c` | `tests/test_ports.py` |
| Another checkout's files (item 1) | A recursive command over a folder of another checkout is judged by the sealed files of that checkout | It was judged by where the same path would lie in this one | `48305c2` | `tests/test_loop.py` |
| A warning about checkouts without the guard (item 1) | `expctl selftest` counts the repository's other checkouts whose settings register no guard, names the first and points at the option below. The self-test still passes | From inside an install nothing showed that a session started elsewhere in the repository runs unguarded | `3dcc780` | `tests/test_ports.py` |
| `install.py --worktrees` (item 1) | One hook entry in `.claude/settings.local.json` of each checkout that lacks the kit's settings. It runs this project's guard with this project as its root, does nothing in the project's own sessions, and refuses every call with a message that names the entry when the kit is gone. `--uninstall` takes the entries out | Claude Code reads a project's hooks from the folder a session starts in. Your install lies in a repository with eleven checkouts, ten of them without the kit's settings | `8329718`, four faults fixed in `689cd54` | `tests/test_ports.py` |
| Two more self-test cases and `loop.controls` (item 3) | Before any agent session: no score for a folder with only a run's records; the run's own score for a copy whose records and log state other values; each named control trained once and held to its floor | An evaluator that takes its number from what the run wrote about itself, or that scores a run which learned nothing, would decide every keep wrongly, and the self-test of 11 November could not see either | `0638339`, review fixes in `d45c69c`, `3bca5a4`, `af57601` | `tests/test_loop.py`: 14 more checks |
| Two controls for the character-model task (item 3) | `benchmarks/charlm/controls.py`: `constant` predicts every character equally (floor ln 65 = 4.174), `shuffled` trains on the text with its characters shuffled (floor 3.300, the entropy of the character frequencies) | A control needs a floor that follows from the task, not from a run | `92f7ffe` | `tests/test_benchmarks.py`: four more checks |
| The measurement of the search (item 4) | Campaigns with and without `loop.search_trials` on both benchmark tasks, and the default set by a rule fixed beforehand | Round 3 built the search without a measurement | `00be575` (text and ledger; no code) | none: a measurement |

How each works is in the README ("Notes and limits", "Upgrading and removing") and in `references/loop.md`
("One campaign", step 1; "A search by the harness"). The decisions behind them:

**The question at the root.**
- It asks only when sealed files really lie on disk below the folder a command sweeps. A project whose
  sealed files are elsewhere, or not there yet, sees no change.
- The look on disk has a bound, and that is the limit of the closed gap. The guard reads at most 20,000 files
  per folder it walks, and a sealed file beyond them is not seen. Run on 13 November in made-up projects,
  with 19,000 and with 20,500 files in front of the sealed one: every call named here was asked about or
  refused at 19,000 and passed at 20,500. With a sealed pattern that begins with `**/`: every recursive
  form, at the root and over a folder below it (`grep -rn x .`, `ls -R`, `find`, `rg -uu`, `Get-ChildItem
  -Recurse`, the Grep tool and the Glob tool). With a pattern for some files of a folder of that size
  (`big3/held/*.csv`): the same forms at the root, and the Grep tool from a folder above it. With a pattern
  that seals a whole folder of that size (`big2/held/**`): only a search that filters by file name, at the
  root in every tool (`grep -rn --include='*.tsv' x .`, `find . -name '*.tsv'`, the Grep tool with a glob)
  and from a folder above it with the Grep and Glob tools, because the files that the filter leaves out
  fill the bound. From the code, not run at that size: without a filter the first file of such a folder is
  a sealed one, so the command is asked about. A shell command that names a folder above a sealed folder
  is asked about as before, and a sealed file named directly is refused. The bound is older than this round (`acf7706`, 11 November, in the check of searches
  below the root). Before the round every recursive command at the root passed, so nothing is weaker, but
  for a tree that large the gap is not closed. The README names the limit since this round. Lifting it
  needs an index of the sealed files, or a walk that leaves out what git ignores: a longer walk costs every
  search its time (about 0.2 s per 20,000 files here), and a question at the bound would meet every search
  of a large project, the Grep tool's among them. Neither is built ("What needs your decision").
- What lets a command pass is a statement the guard can read with certainty: folders named on the line, or a
  file filter of that tool. Each tool's options are read that tool's way: grep's `--include` and `--exclude`
  in their order, find's `-name` with `-o` and `-not`, ripgrep's `-g` and `-t`. What the guard cannot read
  does not count, so it asks once too often rather than once too rarely: a depth option (`find -maxdepth
  1`), PowerShell's `-Exclude`, the exclusions of `tar`, `zip` and `rsync`, a wildcard path (`gci -r *.py`).
- `rg`, `ag`, `git grep` and the Grep tool are judged as ripgrep and git behave: they pass at the root
  because git's ignore rules keep them away from sealed files that git ignores. I compared the guard's
  reading with ripgrep 15.0 and 15.1, GNU grep 3.0 and findutils 4.10.0 on Windows, and with Claude Code's
  Grep tool in a live session.
- The first version of this check was too generous in two ways, and the review found both ("The independent
  review"). That is why the rework reads each tool separately instead of sharing one list of filter options.

**`install.py --worktrees`.**
- It is a flag because it writes into checkouts the installer was not pointed at. Without the flag the
  installer writes nothing outside the target.
- The entry goes into `.claude/settings.local.json`, the file meant for one machine, and git is told to
  ignore it through `.git/info/exclude`. A local settings file that git tracks, that cannot be read as
  settings or that cannot be written is left alone and named.
- Where Claude Code reads that file differs by platform: from the session's folder on Windows, from the main
  checkout's root on Linux and macOS, and a worktree session of the desktop app takes its settings from the
  main checkout's root (vendor documentation, read on 13 November). So on Linux and macOS the main checkout
  gets the entry as well.
- If the project folder is moved or deleted while the entries exist, every tool call in those checkouts is
  refused, with a message that names the entry. That is the safe side, and `--uninstall` removes them.

**The self-test.**
- The copy with other values is a full copy of a baseline run's folder. It takes the time and the disk space
  of one run folder per start, checkpoints included, and shares no file with the run. The first version
  used hard links, and the review showed that an evaluator which writes into the folder it scores then wrote
  into the baseline run itself.
- Moved are the numbers with a fraction in the files that hold metric values (`heartbeat.json`,
  `metrics.jsonl`, `result.json`, `loop_eval.json`, `stdout.log`), each by ten margins. Whole numbers, files
  in subfolders and what a checkpoint holds are not moved: a correct evaluator may read them.
- An evaluator that follows a checkpoint path written in the run's records is stopped by the records-only
  case, and rightly: it scores what the records point at, not what the folder holds. The message and
  `references/loop.md` name the cause and the remedy.
- Each control is one training run on the first seed and counts against the run limit. A run limit below the
  baseline's seeds plus the controls is refused at the start.

### The measurement of the search
Fixed before any result. Six versions per search (`loop.search_trials: 6`), `--max-runs 18`, no scouting,
the stand-in agent of the tests, real training on native Windows (RTX 5090), the confirmation on fresh seeds
left on, the controls left out. Two settings, the learning rate and the batch size, each with a range around
the starter's value. Three pairs of campaigns per task. Both arms of a pair see the same versions: with the
search the harness draws them, without it the stand-in proposes the same ones by hand, one per iteration.
The arms took turns going first. Outcome: the gain that the confirmation measures on fresh seeds, and zero
where a campaign kept nothing. Rule: the search becomes the default only if it beats the other arm by more
than two standard errors, taken from the run-to-run spread, on both tasks.

| Task | With the search | By hand | Difference | Standard error |
|---|---|---|---|---|
| Character model (loss) | nothing kept in three campaigns | nothing kept in three campaigns | 0 | 0.004 by the run-to-run spread (0.0066 per run) |
| Fine-tuning (share right) | gains 0.47, 0.38, 0.41 | gains 0.30, 0.19, 0.44 | +0.18, +0.18, -0.02; mean 0.11 | 0.015 by the run-to-run spread (0.023 per run); 0.068 by the spread across the three pairs |

- On the fine-tuning task the search looked at all six versions inside one iteration. By hand the same 18
  runs reached three or four of them. In the third pair both arms ended on the same values.
- By the run-to-run spread the difference on that task is seven standard errors. By the spread across the
  three pairs it is 1.6: two pairs carry it and one does not.
- On the character model the starter's values were already good, and no version in the ranges beat them by
  the margin.
- So the search helped where the starting values were a guess and changed nothing where they were good. By
  the rule that is not enough for a default, and `loop.search_trials` stays off unless a project sets it.
- Limits. The stand-in measures the procedure with given versions. It does not show what a real agent
  proposes, or whether it uses the offer. Three pairs can show a large difference only. A campaign took
  about 10 minutes on the character model and 16 to 19 on the fine-tuning task.

### Round 3's repairs, looked at again
I read each of the three repairs with its callers and its check, and ran the checks against the code before
and after.

- **Leftover temporary files (`687bb50`).** Sound for what it names, a rename that Windows refuses. Two
  things stood beside it. `expctl.py` has a writer of its own for the same kind of record, and it left its
  temporary file in the same way. And both writers left the file when the write itself gave up, on a full
  disk for example, not only the rename. Both now remove it whatever made the write give up (`a774971`). Live
  on this machine, beside a real reading process: of 2,000 heartbeat writes about 1,900 were refused; the
  code before `687bb50` left 1,905 files behind, the code of `687bb50` and the code now none.
- **The remote side's listing (`a945eeb`).** Sound for the folder that vanishes. Its filter was wider than
  its purpose: it left out every file whose name starts with a dot and ends in `.tmp`, a training script's
  own among them, which round 3's conclusion named as a change to know. The filter is now the exact form of
  the kit's temporary files, `.<record>.<pid>.<six hex digits>.tmp`, so a training script's files are
  mirrored again (`4fe23a0`). The `ssh` side shares the listing and had no check of its own. The check now
  runs both sides beside a thread that creates and removes folders: against the code before `a945eeb` both
  fail with `FileNotFoundError`, against `a945eeb` both fail on the training script's file.
- **A resume that cannot start (`ffaa346`).** Found by following the listing's callers. When a remote run
  ended and was to be resumed, the controller started the next run before it wrote the ended run's exit
  record, and it caught a refusal only. Anything else that start raises, the launch-side listing of a
  vanishing folder before Python 3.12 among it, ended the controller with a traceback after teardown and
  settlement. The run then had no exit record and showed as lost. The failure is now recorded as
  `remote.not_resumed`, and the exit record is written in every case. From reading the code: no run was
  lost to it.
- **The status line (`0f23999`).** Sound. Nothing to add.
- **A run that ends while its status is read (`66175db`).** Not one of the three; it showed while I ran
  `tests/test_kit.py` repeatedly, as one failure in nineteen runs of the check on `expctl watch`. Status read
  a run's result first and looked at its processes afterwards, so a run that ended between the two read as
  lost for one look. On this machine 14 of 30 short runs and 11 of 12 hard-killed runs showed as lost once;
  with the fix none of either. `expctl watch` ended on that look with the wrong state. Status now looks at
  the processes first and reads the records afterwards, and a run whose supervisor is still there has not
  ended.

Left as it was, with the reason. The launch-side listing (`bundle`) keeps its call: it reads the paths the
config names and the folder of a run that has ended, and its failure no longer costs an exit record. A
temporary file of a process that is killed between its write and its rename stays; nothing removes it. A
start that fails after it has booked its share of the spending cap leaves that share booked, which errs
towards spending less. Without psutil on Windows and macOS a killed run can still read as lost for the
moment before its supervisor writes the exit record. Not verifiable here: a real rented job, a real `ssh`
target, a virus scanner; the full disk is made by the tests.

### The independent review
Two subagents on a cheaper model, neither with any part in the work. Each got a snapshot of the code and the
question what could be wrong, ran what it wanted in throwaway projects and reported with reproductions. I
ran every reproduction against the code before and after.

**The guard, first look** (the state of `92f7ffe` against the guard of `568f14b`):

| Finding | What I did |
|---|---|
| 1. A name given to `--exclude` vanished from the whole line: `grep -r --exclude=data/. secret data/. sub` passed. Opened by this round's `e7a69dc` | Fixed (`c72c576`): a name the line also gives as a path stays a path |
| 2. Exclusions matched without regard to case on Windows and macOS: `--exclude-dir=Data`, opened by `e7a69dc`; older for the Grep tool's `!Test/**` | Fixed (`c72c576`): an exclusion counts with its case as written, and only where the tool surely applies it |
| 3. A crash inside the guard still allowed reads: a Grep glob of 1,100 brace groups ended in a recursion error and the read went through. Older | Fixed (`45d7794`): an internal error asks about reads too; more than 64 brace alternatives count as matching every file; an unknown `~user` no longer raises |
| 4. A glob with a character class was read as plain text, so `*.[c]sv` matched nothing for the guard. Older | Fixed (`e710e83`): a class is read as one, in inclusions and exclusions |
| 5. The root check took things for filters that are none: `find . -not -name '*.py' -exec cat {} +`, `find . -name '*.py' -o -print`, `zip -r -g out.zip .`, `tar -czf o.tgz -g snap .`, `rsync -a --include='*.py' . /tmp/copy`, `grep -rnesecret . sub` | Fixed (`624b6c5`): each tool's filters and arguments are read its own way; the rest in `df54cdd` |
| 6. Ways into the sealed folder that the guard did not see: `cd data</dev/null; cat test/labels.csv`, `cd 'da'ta`, `env -C data cat …`, `"grep" -r secret data`, `cat **/*.csv`, `rgrep secret .`, .NET's `AllDirectories`. Older | Fixed (`0884c70`), with a rule of my own beside it: a move or rename of a folder that holds sealed files asks |
| 7. ripgrep's file types were misread (`-t csv` counted as a filter that leaves csv files out). Older | Fixed (`624b6c5`) |
| 8. Reasoned, not run: a `.ignore` or `.rgignore` file with `!data/`, or `RIPGREP_CONFIG_PATH` with `--no-ignore`, takes back the rule the guard relies on | Confirmed with ripgrep 15.0 and fixed (`34000d5`). Measured and left alone: an `--ignore-file` with a `!` line, and a `.ignore` inside the ignored folder, do not make ripgrep read what git ignores |
| 9. Every command of a line was costed in full: 200 searches in one line took 7.4 s where they had taken 0.26 s | Fixed (`65293d8`): each different search is looked up once per call, and a check that passes 12 seconds is answered with a question. One timing answered: the 1.37 s for a path on a server that does not exist is Windows' own lookup of that server, which it remembers for a while; the guard is not slower there than it was |
| 10. New wrong refusals: `ls -r` in Bash at the root, nine harmless named folders, `Get-ChildItem -Depth 0` | Fixed (`f7f5b6e`) |
| 11. The tests did not cover these cases | Each fix came with its cases: 158 more in the nine fix commits |

**The guard, second look** (the eight fix commits, the state of `66175db`). Its verdict on the first eleven:
eight fixed, three partly (5, 6 and 11). It found nothing that the fixes let through which the guard before
them had stopped. New findings:

| Finding | What I did |
|---|---|
| 1. `mv -T data d2` passed the new rule for moves | Fixed (`df54cdd`): asks, as does `mv -vt <target> <folder>` |
| 2. `find` with `-exec … \;` swallowed the rest of the line, so a branch behind it was not read | Fixed: asks |
| 3. `cp -a` and `cp --archive` were not read as recursive; .NET's `Directory.Move` passes the move rule | The first fixed: asks. The second answered as a limit: the guard reads command lines, not program code (README, and a Reject row) |
| 4. Folder changes not followed: `X=1 cd data; …`, `eval cd data; …`, `sudo -D data cat …`, `env -iC data`, `env -u HOME -C data`, `Set-Location -Path:data`, a cut parameter name, `start /D data`; and `Start-Process -WorkingDirectory data cmd '/c type …'` | All fixed (refused) but the last, answered as a limit: a command line inside one quoted argument is not read (README) |
| 5. A quoted command word behind `then`, `timeout` or `xargs`, and written as `$'grep'` | Fixed: asks |
| 6. `***/` in a path | Fixed: read as recursive, asks |
| 7. The 12-second answer leaves little room under the subagents' 15-second hook limit | No change: where a slow start uses up the rest, the hook fails and `onFailure: block` stops the call. What Claude Code does with a hook that ran out of time was not checked live |

**The installer and the loop** (the state of `92f7ffe`):

| Finding | What I did |
|---|---|
| 1. The self-test passed an evaluator that takes its number from `stdout.log`; also whole numbers, numbers stored as text, files in subfolders, a checkpoint's contents | The log fixed (`3bca5a4`): its numbers with a fraction are moved too. The rest answered: a correct evaluator may read those, and `references/loop.md` says what the check does not reach (a Reject row) |
| 2. A leftover self-test folder made the copy write into an earlier baseline run's files through hard links | Fixed (`d45c69c`): a full copy that shares no file, leftovers removed first, and a stop when one cannot be removed |
| 3. An evaluator that writes into the folder it scores also wrote into the baseline run | Fixed by the same change |
| 4. `install.py --uninstall` crashed on a hook event of an unexpected shape in another checkout's settings, after the kit's files were deleted, and left that checkout blocked | Fixed (`689cd54`): such shapes are kept and passed over, the entries elsewhere come out before the scripts, and removal refuses to delete the scripts while an entry elsewhere cannot be taken out |
| 5. `loop.controls` accepted an entry without a name, and two with the same name, and crashed after the baseline's runs | Fixed (`af57601`): refused at the start |
| 6. The records-only case stops an evaluator that loads the checkpoint path a run recorded | Answered: a correct stop. The message and `references/loop.md` now name the cause and the remedy |
| 7. Some stops in the self-test did not say so: a run limit below the seeds plus the controls ended as "limit reached" without a baseline | Fixed (`af57601`): refused at the start and at a resume without a baseline |
| 8. The test of the git ignore line could pass without testing anything | Fixed (`689cd54`) |
| 9. Four small faults of `--worktrees`: a main checkout with a guard of its own got an entry on Windows; a warning without the flag; line endings of the exclude file; a traceback for a file that cannot be written | Fixed (`689cd54`) |
| 10. The shuffled control's floor is 3.2997 where the characters the evaluator scores give 3.29952 | No change: 0.0002, far inside the smallest margin |

No third look was made. The fixes to the second look's findings and to the installer and loop findings are
verified by my own probes and by tests that fail on the code before, not by a reviewer. Neither reviewer
looked at Linux or macOS, at links and UNC paths, or at the Codex and Cursor payloads.

### Tests
A full run is what "Round 2", "Tests" describes: a clean clone of one commit, all seven files, three
interpreters per platform. The number of checks per file:

| Commit | Platform | benchmarks | kit | loop | ports | remote | review_fixes | runlog_units | Failed |
|---|---|---|---|---|---|---|---|---|---|
| `0f23999`, round 3's last code change | Windows | 35 | 136 | 196 | 106 | 73 | 38 | 18 | none |
| | WSL | 35 | 140 | 197 | 105 | 73 | 40 | 18 | none |
| `00be575`, this round's last code change | Windows | 39 | 363 | 210 | 120 | 75 | 38 | 18 | none |
| | WSL | 39 | 367 | 211 | 121 | 75 | 40 | 18 | none |

Both runs ended on 13 November without a failure in any of the six interpreters (logs under
`%TEMP%\nnkit-upgrade\logs\`, label `r4`). The commits after `00be575` change documentation only, the
README's sentence on the guard's file bound among it, and no test reads those files. `benchmarks` has one
check fewer in the two clean interpreters of each platform, which have no PyTorch: the check that puts the
constant control through the evaluator is skipped there and says so. `ports` has one check fewer under
Python 3.8, as before.
This is the one full run of the round. While I worked, the files a change touched ran on Windows under
Python 3.11, and three snapshots ran more: `689cd54` (five files and `ports`), `d45c69c` (`loop`) and
`af57601` (`loop` and `benchmarks`), all passing.

Existing checks that changed, each with its reason:
- `tests/test_kit.py`: `grep -rn 'def train' .` is expected to ask where it was expected to pass. That is
  the closed gap (`e7a69dc`). The helper that calls the guard takes an environment and blanks
  `RIPGREP_CONFIG_PATH`, so that the machine's own setting cannot change an answer (`34000d5`).
- `tests/test_runlog_units.py`: round 3's check of the leftover file also makes a write fail (`a774971`).
- `tests/test_remote.py`: round 3's check of the listing uses a run folder that the `ssh` side can read too,
  and expects the training script's `.tmp` file in the copy where it expected it gone (`4fe23a0`).
- `tests/test_loop.py`: the two checks that the self-test "left no folder behind" cover every self-test
  folder (`0638339`). The toy training script prints a loss line and the toy evaluator gained two fault
  modes; no existing check changed for that.
- `tests/test_ports.py`: the check of the git ignore line also reads the exclude file, and the test
  repository points `core.excludesFile` at nothing, so that it cannot pass on the machine's own ignore
  rules. Two fixtures gained hook events in a foreign form, and the checks that the user's own Cursor and
  Codex hooks are kept, and that removal takes the kit's entries out, were made stricter (`689cd54`).
- `tests/test_benchmarks.py`: the check of the with-kit config expects the two controls, and the check of
  the pilot's commit expects them gone (`92f7ffe`).

### Verified by running, from documentation only, unverified
**By running.**
- The guard's answers: 153 examples against the guard of `568f14b` and that of `00be575`, in the test
  project of `tests/test_kit.py` (Windows, Python 3.11, 13 November). Every reproduction of the two guard
  reviews, before and after its fix.
- The guard's reading of search tools: against ripgrep 15.0 and 15.1, GNU grep 3.0 and findutils 4.10.0 on
  Windows, in three made-up projects with 210 probe lines, and against Claude Code's Grep tool in a live
  headless session (12 November).
- The guard's cost, each figure measured at the commit that changed it and not again at the round's last
  one. On a made-up project of 15,000 files (`8e69154`): 0.32 s for a whole-project search with no sealed
  files on disk, 0.48 s with 5,000 sealed files under an ignored folder, 0.8 s where a rule for the files
  ignores them. At `65293d8`: 100 filtered greps in one line over a sealed folder of 2,000 files 0.3 s, and
  for a line that names eight servers which do not exist a question after 12 s, where the guard before took
  26 s and gave none.
- The guard's file bound, at `00be575`: made-up projects with 19,000 and with 20,500 files in front of a
  sealed file, 48 calls per size, on Windows under Python 3.11 (13 November). Below the bound every call
  was asked about or refused; above it those passed that "The question at the root" names. With no sealed
  file on disk the same commands at the root pass.
- The subagents' setting, live through `--agents` with Claude Code 2.1.322 on native Windows: a hook that
  cannot run blocks the call with the setting and lets it through without.
- `install.py --worktrees`, live on native Windows with headless Claude Code 2.1.322, once with the kit in
  the main checkout and once with it in another worktree: a session in a checkout without the kit read a
  sealed file before the option was run and was refused after it. That was before the four faults of
  `689cd54` were fixed; the changed cases are covered by the tests only.
- The two controls of the character-model task, in one campaign on this machine: 4.1744 and 3.3099 against
  floors of 4.1743 and 3.2997, a baseline of 1.690, 1.674 and 1.681, a margin of 0.019.
- The measurement of the search: twelve campaigns with real training on this machine's GPU.
- The repairs beside round 3's: each by a check that fails on the code before, and the two live counts
  above (leftover files; runs read as lost).
- On your real install, after the round: the installer's fourth run, the self-test, and the guard's answers
  to twelve made-up calls before and after ("The fourth installer run on the real install").

**From documentation only.**
- Where Claude Code reads `.claude/settings.local.json` on Linux and macOS, and what a worktree session of
  its desktop app reads (code.claude.com/docs/en/settings and /worktrees, read on 13 November 2026).

**Unverified or not measured.**
- `install.py --worktrees` on Linux, macOS and in the desktop app. Whether Claude Code skips a whole settings
  file that holds one hook event it cannot read.
- In which folder Claude Code runs ripgrep for its Grep tool, and whether it passes `--no-config`. The guard
  assumes the session's folder and no such flag, which is the strict side.
- What each agent does with a call whose hook ran out of time. The guard answers at 12 seconds so that it
  does not come to that.
- The guard's new rules on Linux and macOS beyond the test files, which pass in WSL. The two subagents' own
  hooks in a trusted folder: the live check went through `--agents`.
- The search with a real agent, and any effect of the controls or the two new self-test cases on a real
  project's evaluator. Controls exist for one of the two benchmark tasks.
- The repairs on a real rented job, a real `ssh` target or beside a virus scanner.

### Changes in the behaviour of existing features
The sealed test set, the frozen evaluator and the protection of live runs are not weaker. Where the guard
answers differently it is stricter, with three exceptions that are named in the table.

**Guard.** "Before" is the guard of `568f14b`, "now" that of `00be575`; every example was run against both.
"Pass" means no question.

| Change | Examples | Before | Now | Reason | Commit |
|---|---|---|---|---|---|
| A recursive command over the project root while sealed files lie on disk below it | `grep -rn 'def train' .`, `find . -type f`, `ls -R`, `tree`, `tar -czf out.tgz .`, `zip -r out.zip .`, `cp -r . ../copy`, `rsync -a . /tmp/copy`, `chmod -R a+r .` | pass | ask | The kept gap: such a `grep` prints lines of sealed files | `e7a69dc` |
| The same in PowerShell and `cmd` | `Get-ChildItem -Recurse`, `gci -r`, `ls -r`, `dir -s`, `cmd /c dir /s`, `findstr /s secret *.csv`, `tree /f`, `Copy-Item -Recurse . ..\copy`, `Compress-Archive -Path .`, `robocopy . ..\copy /E`, `xcopy . ..\copy /S`, `Get-ChildItem -Depth:2` | pass | ask | The same gap in the shell your install runs in | `d02137e`, `f7f5b6e` |
| At the root, what looks like a named folder or a filter and is none | `grep -rn secret . 2>/dev/null`, `grep -rnesecret . sub`, `find . -name '*.py' -o -print`, `find . -not -name '*.py' -exec cat {} +`, `grep -r --exclude='*.csv' --include='*.csv' y .`, `zip -r -g out.zip .`, `tar -czf o.tgz -g snap .`, `rsync -a --include='*.py' . /tmp/copy`, `Get-ChildItem -Recurse -Exclude data`, `gci -r *.py`, `find . -maxdepth 1` | pass | ask | The command still sweeps the sealed files, or the guard cannot tell | `624b6c5`, `df54cdd` |
| `rg`, `ag` or `git grep` told to pass over git's ignore rules, to follow links or to include files like the sealed ones | `rg -u secret`, `rg --no-ignore secret`, `rg -L secret`, `ag -u secret`, `git grep --no-index secret`, `rg -uu -g 'test/*.csv' y`, `rg -uu -t csv y`, `rg -uu -g '*.[c]sv' y`, `rg -uu -g '!Data/' y`, `RIPGREP_CONFIG_PATH=x rg secret` | pass | ask | They pass at the root only because git's ignore rules keep them from the sealed files. Unchanged and passing: `rg secret`, `git grep secret`, `rg -g '*.csv' y` (a rule for the folder holds), `rg -uu -g '!data' y`, `rg --no-config secret` | `8e69154`, `c72c576`, `624b6c5`, `e710e83`, `34000d5` |
| The Grep tool in a folder with sealed files, with a glob that does not keep them out | path `data` with glob `data/test/*.csv`, `!test/**`, `!Test/**` or `*.[c]sv` | pass | deny | An inclusion was read as leaving the sealed files out. An exclusion with a slash is anchored where ripgrep runs, not at the folder searched, and its case counts | `c72c576`, `e710e83` |
| A sealed file read behind a change of folder that the guard did not follow | `cd data && cat test/labels.csv` with a blank in front, `if true; then cd data; cat …; fi`, `builtin cd data && …`, `cd -- data && …`, `time cd data && …`, `Push-Location data; Get-Content test\labels.csv`, `cd data</dev/null; …`, `cd 'da'ta && …`, `X=1 cd data; …`, `eval cd data; …`, `env -C data cat test/labels.csv`, `env --chdir=data …`, `env -iC data …`, `env -u HOME -C data …`, `sudo -D data …`, `sudo --chdir=data …`, `Set-Location -Path:data; …`, `Set-Location -Pa data; …`, `start /D data /B cmd /c type test\labels.csv` | pass | deny | Each read a sealed file without a question | `4b75776`, `0884c70`, `df54cdd` |
| A path that exists only below a folder the same line names | `python train.py --data-dir data --eval-file test/labels.csv` | pass | deny | The program's own change of folder reaches the sealed file. Still passing: `python train.py --data-dir data`, `python train.py --split test` | `df54cdd` |
| | `tar -C data -cf out.tar test/labels.csv`, `env -iC data grep -r secret test` | ask | deny | The same: they name a sealed file, not only its folder | `df54cdd` |
| A command word in quotes | `"grep" -r secret data`, `"git" push`, `"rm" -rf runs/x`, `timeout 5 "grep" -r secret data`, `if true; then "grep" -r secret data; fi`, `$'grep' -r secret data` | pass | ask | No rule recognised a quoted command word, the rules for pushing and for deleting run folders included | `0884c70`, `df54cdd` |
| Recursion in other forms | `rgrep secret .`, `cat **/*.csv`, `cat ***/*.csv`, `dir --recursive`, `env -C . ls -R`, `[IO.Directory]::GetFiles('.', '*', 'AllDirectories')` | pass | ask | Forms the guard did not know | `0884c70`, `f7f5b6e`, `df54cdd` |
| A move, a rename or an archive copy of a folder that holds sealed files | `mv data d2`, `git mv data d2`, `mv -T data d2`, `mv -vt /tmp/x data`, `cp -a data d2`, `cp --archive data d2`, `Move-Item data d2`, `Rename-Item data d2`, `ren data d2` | pass | ask | Under another name nothing seals the files. Still passing: `mv sub sub2`, `mv data/train.csv data/t2.csv` | `0884c70`, `df54cdd` |
| A question too many | `echo move data now`, `Get-ChildItem -Recurse -Depth 0` | pass | ask | The move rule reads words, and only a bare `-Depth 0` is read as one folder. Known and left | `0884c70`, `f7f5b6e` |
| Milder: an exclusion that the tool really applies | `grep -rn --exclude-dir=data x .`; the Grep tool with path `data` and glob `!test` | ask; deny | pass | grep leaves the folder out, and ripgrep leaves out everything named `test`. Before, the name in the option counted as a path the command reads | `e7a69dc`, `c72c576` |
| Milder: `find` with `-exec … \;` over a folder without sealed files | `find sub -type f -exec cat {} \;` | ask | pass | It reads nothing sealed, and the same command ending in `+` already passed | `df54cdd` |

`ls -r` and `dir -s` in the second row are PowerShell's. They count as recursive only where the shell may be
PowerShell: in Claude Code's PowerShell tool, on Codex and Cursor, and in a line that names `powershell`,
`pwsh` or `cmd`. In Claude Code's Bash tool they sort in reverse and show sizes, and pass as before.

Not in the table, because a command line does not show them:
- **An error inside the guard asks about reads too** (`45d7794`). Before, a read was allowed when the guard
  itself failed. On Codex, on Cursor and unattended that question is a refusal.
- **A check that takes longer than 12 seconds is answered with a question** (`65293d8`). Before, the hook ran
  into the agent's time limit, and not every agent blocks a call whose hook ran out of time.
- **A recursive command over a folder of another checkout** is judged by the sealed files of that checkout
  (`48305c2`).
- **Where git's ignore rule is taken back by a file**: a `.ignore` or `.rgignore` beside the ignored folder
  or above it with a `!` line for its name, or a file named by `RIPGREP_CONFIG_PATH` that turns the rules
  off, follows links or names files to include. `rg`, `ag` and a lone `git grep` are then asked about, and
  the Grep tool is refused (`34000d5`).

Each row has its cases in `guard_tests` and the guard section of `tests/test_kit.py`. By commit: five for
`4b75776`; 14 for `c72c576`, 31 for `624b6c5`, 12 for `e710e83`, four for `45d7794`, two for `65293d8`, 12
for `f7f5b6e`, 41 for `0884c70`, 11 for `34000d5`, 31 for `df54cdd`; the others with `e7a69dc`, `d02137e`
and `8e69154`. The case for another checkout is in `tests/test_loop.py`.

Limits that stay, all in the README ("Notes and limits") and all run as such: a search behind a wrapper
the guard does not know (`xargs grep -r secret .`), a path through a variable (`D=data; cat
$D/test/labels.csv`), a command word spliced from quoted pieces (`g'r'ep -r secret .`), a command line
inside one quoted argument (`Start-Process -WorkingDirectory data … cmd '/c type test\labels.csv'`) and
program code (`[IO.Directory]::Move('data','d2')`). They pass as before. So does a search that would read a
sealed file beyond the first 20,000 files of a walk ("What was built, and why", "The question at the root").
The guard is a seatbelt, not a sandbox; for hard isolation the test split belongs outside the repository.

**Installer.**
- `--worktrees` is new (above). Without it nothing changes outside the target, and nothing warns.
- An install or an upgrade makes a first pass without writing and refuses, before any change, a settings
  file that it cannot merge into: a JSON file that holds no object, or hooks in a shape it cannot add to.
  Before, such a file ended the run with a Python error, part of the way through.
- Hook events in a form the installer does not know are kept as they are, on install and on removal. Before,
  Cursor's file could be rewritten wrongly around one.
- `--uninstall` takes the kit's hook entries out before it deletes the scripts, and refuses to delete the
  scripts while an entry in another checkout cannot be taken out. Before, a crash between the two left a
  checkout whose every tool call was refused.
- The two agent files carry `onFailure: block` on their hook (`d07606c`). An upgrade writes it; agent files
  that were edited after install are backed up, as before.
- Not handled: an odd shape in `.cursor/cli.json` or in an MCP file still ends the first pass with a Python
  error, before anything is written. A removal that cannot write one of the target's own settings files
  stops there with a Python error: the entries in the other checkouts are out by then, and the kit's files
  and its hooks in the target are still in place.

**Loop.**
- Every campaign runs two more evaluator calls at its start, for the two new cases, and copies one baseline
  run's folder whole. A leftover self-test folder is removed first; one that cannot be removed stops the
  campaign with a reason that begins "self-test:".
- `loop.controls` is a new key. Names must be text and unique.
- A run limit below the baseline's seeds plus the controls is refused at the start and at a resume without a
  baseline, also in a project without controls, and the message names the smallest limit that works. Before,
  such a campaign ended in the middle of its baseline as "limit reached", with exit code 0 and no baseline,
  and every resume trained the baseline again.
- An evaluator that takes its number from the run's records or from numbers with a fraction in `stdout.log`
  stops the campaign, where it passed before. So does one that follows a checkpoint path written in the
  records.
- The loop's decisions, limits and records are otherwise as they were.

**`expctl.py`, `runlog.py`, `nnremote.py`.**
- `expctl status`, `watch` and every other reader of a run's state through `expctl`, the remote module among
  them: a run that ends or is killed while it is read no longer shows as lost for one look (`66175db`).
  Without psutil on Windows and macOS a killed run can still read as lost for the moment before its
  supervisor writes the exit record.
- Both writers of records remove their temporary file when a write gives up, whatever the cause (`a774971`).
  The error they raise is the same.
- The mirror of a remote run takes a training script's own `.tmp` files again; only files of the exact form
  of the kit's temporary files stay out (`4fe23a0`). This narrows round 3's change.
- A remote run whose resume cannot start gets its exit record, and the ledger a row `remote.not_resumed`
  (`ffaa346`). Before, the controller ended with a traceback and the run showed as lost.
- `expctl selftest` prints one more warning where the repository has checkouts without the guard.

**Benchmarks.** The character-model task's config names two controls and freezes `controls.py`. Its README's
example uses `--max-runs 14` where it used 12, because each control is one run. `pilot.py` leaves the
controls out of its loop arm, so a pilot is comparable with the two this report records.

**Documentation.** README ("Notes and limits", "Upgrading and removing", the table of what works where),
`references/loop.md` (the self-test, the controls, the measurement), `references/remote.md`, `docs/GUIDE.md`
and the skill's index describe the changes.

### Things to know
- **The guard will ask about ordinary exploring.** An agent that starts with `grep -r` or `ls -R` at the
  root of a project whose sealed files are on disk gets a question, and unattended a refusal with a hint. It
  passes by naming folders or filtering by file type, and `rg` and the Grep tool pass as they are. This is
  the price of the closed gap.
- **A training command can be refused for the paths it names.** `--data-dir data --eval-file
  test/labels.csv` is refused when `data/test/labels.csv` is sealed, because the guard cannot know that the
  script will not join the two. A command that needs the sealed file belongs to `expctl final-eval`.
- **With `--worktrees`, moving or deleting the kit's folder without `--uninstall` blocks every tool call in
  the other checkouts** until the entries are deleted. A worktree added later needs the installer again.
  Codex and Cursor are not covered by the option.
- **A session started in a subfolder of the project loads no project hooks**, so no guard. Start the agent
  at the project root. This is older than the round, and the README now says it.
- **The subagents' own hooks run only in a folder whose trust dialog was accepted**, and never in a `-p`
  session. The project-wide guard applies the read-only rule to their calls either way.
- **The guard's look on disk stops after 20,000 files per folder it walks.** In a project where a sealed
  pattern begins with `**/` and the tree is larger than that, or where a sealed folder itself holds more
  files than that, a search can pass that reads a sealed file ("What was built, and why", "The question at
  the root"). Whether your real install is such a project I have not looked: that is a count of files there,
  and it waits for your word.
- **Temporary things of this round are removed**: the worktrees, the throwaway projects of the live checks
  and the measurement's projects (2.5 GB). The measurement's plans, logs and the two result files that its
  figures are computed from stay in `%TEMP%\nnkit-upgrade\search-measure` (1 MB). The figures are in
  `references/loop.md` and above.

### What was reduced, and differences from the list
- The question at the root is not asked where the sealed file lies beyond the first 20,000 files of a walk.
  The list's item said "when sealed files really lie on disk below"; in a tree that large the guard does
  not see them. Measured and documented, not lifted.
- No third look by a reviewer (above). The installer's findings went into one commit, not one each.
- Controls are built for one benchmark task. For the fine-tuning task the floors need a measurement first
  (a Trial row).
- The measurement used the stand-in agent and three pairs per task. A campaign with a real agent costs
  subscription usage and was not run.
- `--worktrees` covers Claude Code only and was checked live on native Windows only.
- The check before the harness's writes in a search is still not safe against a process that swaps the file
  at that instant (round 3, "What was reduced"). The root-cause fix is to contain each run's processes, which
  is not built.
- The self-test's copy takes a run folder's disk space once per start. For checkpoints too large for that
  the code names the upgrade (copy-on-write clones); it is not built.

### The fourth installer run on the real install
You asked for it on 13 November with "Update my install", after this report was delivered. That session
answered with an authentication error, and nothing ran. A new session the same day read where the first
had stopped and did it. It went as the third run did ("Round 2", "The third installer run on the real
install"): a rehearsal on a fresh copy of its kit files, a dry run on the install, then the run. The
installer came from a clean clone of commit `7a38b98`, whose code and tests are those of `00be575`, where
the full tests passed. They were not run again for this.

- **What changed there.** Fourteen kit files and the manifest, and nothing else of the 255 files in its
  `.claude` folder, its experiments and its runs, apart from new lines in its guard record. The fourteen:
  both agent files, the hooks `nn_guard.py`, `nn_readonly.py` and `nn_statusline.py`, `SKILL.md`, the
  references `finetuning.md`, `hpo.md`, `loop.md` and `remote.md`, and the scripts `expctl.py`,
  `nnloop.py`, `nnremote.py` and `runlog.py`. That is rounds 3 and 4 together. None of them had been
  edited there, and each has a backup in its `.claude/backups/nn-training-20261113-155355/`. Config (19
  keys), `settings.json`, `CLAUDE.md`, `.gitignore`, journal and runs are byte for byte as before. No run
  was live, and none of the 255 files had changed since my last look on 12 November.
- **Checked by running, there.** `expctl selftest` passes. Two of its optional checks fail: no metric is
  configured, which is that project's choice, and this round's new check counts 9 of the 10 other checkouts
  of that repository without the guard ("What needs your decision", item 2). `expctl status` reads its
  five runs. The logger imports from the skill's folder. Through the command that its settings register,
  the guard lets a harmless read pass, refuses input it cannot read, refuses both configured final commands
  typed directly and asks for `expctl final-eval`. The 27 files of its skill, hooks and agents folders
  equal the kit's, apart from lines in five of them that name its interpreter.
- **What the new guard decides differently there.** I put the same twelve made-up calls to its guard before
  and after the run, with that install's own config. At the project root, `grep -rn x .`, `ls -R`, `find .
  -type f` and PowerShell's `Get-ChildItem -Recurse` were allowed and are questions. A `cat` of a file in a
  sealed folder, behind `command cd` into the folder above it, was allowed and is refused: that form got
  past its guard until this run. Whether a file lies at that place I did not look. As before, a read of a
  file in a sealed folder and a move of that folder are refused. Also as before, these are allowed: a read
  of `CLAUDE.md`, a `grep -r` with `--include='*.py'`, a `grep -r` over the skill's folder, and the Grep
  and Glob tools over the whole project. Why the two tools pass there I did not look into. It is the same
  answer as before the run, and it fits point 1 above, by which they pass where ripgrep itself stays away
  from the sealed files. The check of a recursive shell command at the root takes 0.7 s, where it took
  0.26 s; that of the two tools over the whole project 0.6 s, where it took 2.1 and 2.4 s.
- **Left there.** The fifteen changed files, which you then had me commit ("Yes, commit there"): one local
  commit of exactly those paths, not pushed (undo with `git reset --soft HEAD~1` there while it is the
  newest commit). Its parent is the commit that was newest before, nothing was staged before or after, and
  that repository's other uncommitted work, 418 entries in git's status, was not touched. The commit
  changed no file on disk. Its message says what the run changed, what was checked and what was not. Also
  the backup folder and 16 lines in its guard record, both of which git ignores there: 4 lines from the
  self-test's own probes and 12 from my made-up calls, marked `upgrade-check` (three on the
  final-evaluation rule, nine from the comparison above, in which an allowed call leaves no line). None of
  those calls was carried out. Not run there: its two registered scripts, a final evaluation, that
  project's own check, `install.py --worktrees` and a count of its files.
- **To know.** The guard there is the new one from the next tool call on, because the hook starts the file
  anew each time. An agent session that was open in that project during the run should be started again,
  so that it reads the new skill and agent files. An agent that explores there with `grep -r` or `ls -R` at
  the root now meets a question, and in an unattended session a refusal with a hint ("Things to know").

### What needs your decision
The questions of section 9 and of round 3 still wait. From this round:
1. **The real install**: answered on 13 November, the installer ran there a fourth time, and the fifteen
   files it changed are committed there (above). Open on it is item 2.
2. **Whether to register the guard in that repository's other checkouts** (`--worktrees`). The install's
   self-test counts 9 of its 10 other checkouts without the guard, where this report said ten. Which one
   has an entry, and since when, I did not look into. The option would add one entry to the local settings
   file of each of the nine. Sessions started there run unguarded today.
3. **A campaign with a real agent on the fine-tuning task with `loop.search_trials` set.** The measurement
   makes it more worth its usage than it was: the procedure helped where the starting values were a guess.
   What is open is whether an agent uses the offer.
4. **What to build next.** My order: an index of the sealed files, so that the guard's look on disk has no
   bound, because that is the one limit of this round's root check that a large project meets by accident;
   containment of each run's processes (a job object on Windows, a process namespace under bubblewrap),
   which also closes the check-then-write gap of the search; controls for the fine-tuning task; a repair
   attempt after a crash; then a minimum agent version, the readiness report and a checkpoint helper.

## After round 4 (13 November 2026): the guide, and one fix
You asked for a full and easy guide in the repository: how to use the kit, what it does and how it improves
training.

- **The guide.** `docs/GUIDE.md` is reworked, not doubled. Part 1 is new and in plain language: the kit in one
  minute, a text picture of how the parts fit, a table of what the kit changes and what holds each change (the
  guard, the procedure, harness code), six ways it improves training, the measurements of this report with
  their limits, and what the kit does not do. Part 2 is the earlier guide, sections 1 to 5 and scenarios A to
  M under their numbers and letters, and scenario A now walks through the run tools by hand. Part 3 has the
  commands, the limits, the kit's own words and a table of where to read more. `README.md` and
  `docs/README.md` point to it. The guide claims no more than point 1 of "Read this first" allows: no better
  score from the kit on the short benchmark, and trust and protection as what to expect.
- **Checked.** The commands of scenario A on a fresh practice project (native Windows, Python 3.11, the local
  GPU: self-test, `launch`, `watch`, `curve`); every number against this report; every statement of Part 1
  against the README's "What works where" and "Notes and limits"; every link against the tree. Not checked:
  the commands on Linux, and how the page looks on a hosting site. No test reads these files.
- **The fault those commands found** (`11a7a2c`). A run of `benchmarks/charlm/train.py` started by hand with
  `expctl launch` ended as completed without heartbeat, metrics or result, and `expctl curve` had nothing to
  show. The script looked for the kit's logger beside itself, and a launched run works from a snapshot of the
  source that has no `.claude`. Both practice scripts now look in `$EXP_PROJECT_ROOT` as a third place. The
  two earlier places come first, so runs of the loop, which start in a worktree that has the kit, and a
  vendored logger are found as before. `tests/test_benchmarks.py` launches such a run and checks its record:
  40 checks pass on native Windows (Python 3.11). The fine-tuning script got the same lines and was not run.
  The other six test files and WSL were not re-run, since no file they cover changed. The installer installs
  neither `benchmarks/` nor `tests/`, so no install is out of date by this. The README's `runlog.py` row now
  says how a launched run finds the logger.
- **Seen and left.** `expctl status` lists no best run for the practice projects: their scripts record no
  checkpoint, and the tasks' metric selects `best`. One line in each script, or `select: final` in the task
  files, would list them. I left it, because it changes what the sessions of a pilot or a campaign see. It is
  yours to decide. (Done since, on your request for fixes: the next section.)
- **Where it is.** On `main`. The work was done on the branch `claude/kit-upgrade-continuation-8e3ca9`, and
  when you said to merge, on 13 November, `main` was fast-forwarded to it. Nothing was pushed then.

## After the guide (13 November 2026): the full tests, two fixes, the front page, the upload
You asked for the full tests and the fine-tuning script, for fixes of what they show and of what needs
improvement, and for the kit on your GitHub account, looking good, with a guide that a beginner can read and
that explains in detail how the kit works.

- **The tests pass.** Before any change, all seven test files on native Windows (Python 3.11) at `a62db21`:
  864 checks, none failed, 12 minutes. After the last code change, at `0450067`, with the three interpreters
  of each platform, each on a fresh clone of that commit:

  | Platform | Interpreter | Checks passed | Failed |
  |---|---|---|---|
  | WSL2 (Ubuntu) | default Python 3.12.3, with psutil | 874 | 0 |
  | WSL2 (Ubuntu) | clean Python 3.12.12, no packages | 871 | 0 |
  | WSL2 (Ubuntu) | clean Python 3.8.20, no packages | 870 | 0 |
  | Native Windows | default Python 3.11.7, with psutil and PyTorch | 866 | 0 |
  | Native Windows | clean Python 3.11.7, no packages | 863 | 0 |
  | Native Windows | clean Python 3.8.20, no packages | 862 | 0 |

  That is 15 minutes in WSL and 34 on Windows. No log holds a traceback. The counts differ because some
  checks need Linux tools (tmux, bubblewrap), PyTorch or a newer Python. Two checks are new, one for each
  fix below; no existing check was changed or removed.
- **The fine-tuning script runs.** In a practice project made by `benchmarks/new_project.py`, started through
  `expctl launch` for the first time (native Windows, Python 3.11, the local GPU, seed 1): 369 steps in 30.0
  seconds, 0.34 exact answers on the 500 examples of `data/dev.txt`, about 61 seconds with the model's
  loading. The record is complete (heartbeat, metrics with the loss at seven points, result, exit, the saved
  adapter), and the frozen evaluator, run by hand on the saved adapter, gives the same 0.34. The task's
  README gives 0.35 to 0.39 for three seeds on another split, `loopval.txt`, which is sealed and was not
  used here; nor was the test split.
- **Its first try failed, through this machine and not the kit.** The run ended at its start with `module
  'bitsandbytes' has no attribute 'nn'`. The system Python's site-packages holds an empty `bitsandbytes`
  folder, the remains of a removed package. A fresh temporary environment that uses the system's PyTorch
  reaches that folder, and PEFT 0.21.2 takes it for the installed package. I changed nothing in the system
  Python: the temporary environment got the real package, which hides the folder, and
  `benchmarks/finetune/README.md` now says what to do (`0db85eb`). Removing the folder is yours to do
  (section 9).
- **Fixed: the practice projects listed no best run** (`0edd1b3`). After that run `expctl watch` reported no
  best value and `expctl status` listed no best run, as section "After round 4" had noted and left for your
  decision; I took your request for fixes as that decision. Both practice scripts now name the model they
  saved as the run's result. The same run then shows `best_so_far` 0.34 and a `TOP` line with the adapter's
  path. Training does not change, and neither do the loop's decisions, which rest on the loop's own record
  of the best version. What changes: the sessions of a later pilot or campaign see a best run in `status`,
  which those of the earlier pilots did not, so a new pilot is not strictly comparable with them on that
  point. To take it back, remove the two-line `if rl:` block after the save in each `train.py`, and the
  check for it in `tests/test_benchmarks.py`.
- **Fixed: a best checkpoint recorded on another machine** (`0450067`). Found while I checked the fix above.
  `expctl status` takes a run out of its list of best runs, and raises "recorded checkpoint missing", when
  the checkpoint path in the run's record does not exist. That is right for a deleted checkpoint. It was
  wrong where the record names a path of another machine: for the mirror of a remote run, whose script
  records the path it saved to there (the form the remote reference and the logger's own example give),
  for every run of a project folder that was moved or renamed, and for a look from WSL at runs made on
  Windows. Status now looks for the part of the recorded path below the run's own folder in this run
  folder, and lists the path it found. A checkpoint that is gone raises the alert as before. Shown with the
  copy of a completed run whose record I rewrote to a made-up remote path: before, the alert and no entry;
  after, the entry with the local path and no alert. Not tried on a real remote run. Your real install has
  the fix since the fifth installer run of the same day (below); it matters there only if that project's
  folder moves or its runs are looked at from WSL.
- **The guide explains how the kit works** (`b9e1d4c`). A new section in Part 1, "How it works, step by
  step", follows a project through seven steps: what the installer writes, what a session knows when it
  starts, how the guard answers an action, what a launched run records, the seven phases and their gates,
  the noise rule with a worked example, and the single final evaluation. Five diagrams replace and extend
  the text picture: the kit's parts, the guard's three answers, a launched run, the phases, and a campaign
  of the loop. A table at the top says where to start reading. Scenario A names the status line that lists
  a practice run as the best one. The numbers and letters of Part 2 are unchanged.
- **The README is a front page** (`108728d`). It opens with a banner, the facts in one line, a pointer to
  the guide and a list of its sections. Then come the picture of the kit, six lines of what it changes,
  the measurements in three sentences (no better score on the short task; one campaign whose gain held on
  fresh seeds; expect trust and protection), the quick start, a practice project to try, and a table of
  the documents. Everything from "What gets installed" on is as it was, the table of what works where
  among it. `docs/README.md` lists the upgrade records and the banner's files.
- **Checked.** A script compared every link and anchor with the tree, and looked at table shapes, line
  lengths, code fences and characters that Mermaid misreads: no finding. The six diagram blocks were drawn
  with Mermaid 11.4.1 on a local page, in a light and a dark theme, and both banners were looked at. The
  new section's statements were checked against the code and against this report's numbers.
- **The upload.** The kit is in a new private repository named `nn-training-harness` on your GitHub account:
  the branch `main`, with a description and twelve topics. `main` was fast-forwarded to the tested commit
  first; no history was rewritten. Before the push I scanned the 200 tracked files and the history: no file
  holds your name or e-mail address, this machine's name, a path below a user folder of this machine, a
  token or key, or a name of the other project. The history holds your name and e-mail address as author
  and committer of each commit, and nothing else of those. That, the missing licence and the records under
  `docs/upgrade/` are why the repository is private (section 9, item 11).
- **How it looks there.** I read the README and the guide as GitHub's renderer returns them: the banner with
  its light and dark variant, the tip box, every table, a heading for every in-page link, each diagram
  handed to the site's Mermaid, and no raw Markdown left over. I looked at both on a local page with
  GitHub's style sheet, in a light and a dark theme. I did not see the pages on the site itself: the
  built-in browser is not signed in to GitHub, and a private repository answers it with "not found". The
  site draws the diagrams with its own Mermaid version, which may differ from the one I used.
- **Two faults of the look, fixed.** GitHub gives every column of the README's table "By agent" its narrowest
  width, so the two row labels that held a whole list ran down the page a word or two per line. Those lists
  now stand above the table, and two long cells keep their verdict and point to a note below it; no
  statement changed. Three comments that ran past the right edge of a command block are shorter or stand on
  a line of their own. I looked at the three places again as GitHub renders them.
- **Public, on your word** ("Yes, make it public", 13 November). What the publication consists of:
  - *One new commit.* The public repository starts from a commit without a parent that holds the files as
    they are. It is made under your GitHub account's name and no-reply address and dated in UTC, so neither
    your name, your e-mail address nor this machine's time zone is in it.
  - *The history before it stays here.* Its 132 commits lie in the local repository under
    `refs/archive/development-history`, a name that an ordinary push does not carry. The commit ids in this
    report belong to that history, the baseline `5ea9659` among them: `benchmarks/pilot.py --old-kit 5ea9659`
    works in the local repository and not in a clone of the public one, which holds the old kit only as the
    fixture of the tests.
  - *A licence.* `LICENSE` is the MIT licence with the account's name as the holder, yours to change. The
    README's new section "Licence" says so and names the terms of the practice data: Tiny Shakespeare is in
    the public domain, Banking77 is under CC BY 4.0.
  - *Later commits.* The repository's own git identity is now the account's name and no-reply address, so
    that a later commit does not carry the private address.
  - *Checked before it.* The scan for private details again, over the final files, with the terms of the
    first scan and no hit; and a search for network addresses, session ids, time zones and login names,
    which found only examples and vendor documentation. The two original documents under `docs/` and the
    fixture of the old kit hold nothing personal. The records under `docs/upgrade/` went along as they are:
    they quote your messages and describe this machine, as I had said.
  - *A repository that never held the old commits.* GitHub keeps a replaced history retrievable by commit
    id, and a repository's activity page lists every push with the ids before and after it. The commits of
    the first upload carry your private address, so replacing the history in place would have left the
    address findable once the repository was public. I asked you, and you chose a fresh repository: the one
    of the first upload is renamed to `nn-training-harness-dev-history` and stays private (delete it when
    you like; my login may not delete repositories), and a new `nn-training-harness` received only the new
    commit, with the same description and topics.
  - *Tested from a clone that holds only that commit*, on Windows and in WSL at the same time, with the
    default interpreters. WSL: 874 checks, all pass. Windows: 865 pass, one fails, "session hook injects
    status after compaction". Nothing in it depends on the history: the two practice runs that this check
    and the guard's checks need running lasted about 68 seconds, the checks before it take about 64 on an
    idle machine, and with the second suite running beside it the runs ended first. **An existing test
    changed for it, the only one of this step:** in `tests/test_kit.py` those runs get 30000 steps instead
    of 3000. The test's cleanup stops them as before, so the test takes as long as it did (97 seconds), and
    no check changed. At the fix, again side by side: Windows 866 and WSL 874 checks, all pass; the runs
    stood at a tenth of their length when the check ran.
  - *Public since those tests passed.* I asked GitHub without a login: the page, the API and the raw README
    answer, the licence is named as MIT, the commits carry only the account's name and no-reply address,
    the repository of the first upload answers "not found", and a commit id of the old history is not in
    the public repository.
  - *Seen after the switch.* The front page as a visitor gets it, in the built-in browser: the public mark,
    the description, the topics and the licence. The rendered README has a target for each of its 29
    in-page links, six tables, the banner and the tip box, and no raw Markdown. The browser pane was
    hidden, so what I saw below the top comes from captures of the live pages with a headless browser.
  - *A fault those captures showed, fixed.* GitHub draws the diagrams with Mermaid 12.2. Its flowcharts
    wrap a label at 120 px, where version 11 (which my local views had used) wraps at 200, so lines that
    the files break by hand were broken a second time and left single words on lines of their own. Each of
    the five flowcharts now sets its own wrapping width in one `init` line; the sequence diagram is
    unchanged. I drew all six diagrams locally with GitHub's version and settings. On the live pages the
    README's diagram (about 1040 px tall, about 1350 before) and four of the guide's five keep the written
    breaks.
  - *Not seen on the site:* the pages in an interactive session, a dark theme, a phone's width, and the
    guide's last diagram (scenario G), which lies below what a capture reaches.
- **The fifth installer run on your real install** ("Yes, run it", 13 November), so that it gets the fix of
  `expctl status`.
  - *From what.* A clean clone of the public commit `920bddd`. Its installed files are those of `03693f1`,
    where the full tests last ran. Against the kit of the fourth run one installed file differs,
    `expctl.py`, by the seven lines of the fix.
  - *How.* The steps of the fourth run. A read-only look first: the install was as the commit after the
    fourth run had left it (270 files listed, none added, removed or changed), and none of its five runs
    was live. Then a rehearsal on a fresh copy of its kit files, a dry run on the install, and the run at
    19:24 UTC.
  - *What it changed.* Two files, each with a backup in a new folder under the install's
    `.claude/backups/`: `expctl.py` and the kit's manifest. The other 31 kit files were up to date. Config
    (19 keys), settings, hooks, CLAUDE.md, .gitignore, journal and runs are unchanged.
  - *Checked after it.* `expctl selftest` passes; the two optional checks that fail are those of the fourth
    run (no metric configured, 9 of 10 other checkouts without the guard). `status` gives the same answer
    with the old and the new `expctl.py` on that project's records: five runs, four completed and one
    failed, no alert. The guard loads `expctl.py`, so I asked it the twelve made-up calls of the fourth run
    before and after: twelve times the same answer. The 27 kit files there are the kit's, five of them
    apart from the lines that name the interpreter.
  - *What it does there today.* Nothing you can see. The fix repairs the list of best runs, and that list
    is empty in that project, whose config names no metric. It will matter once a metric is configured and
    the project's folder moves or its runs are looked at from WSL.
  - *Left there.* The two files are changed and not committed in that repository; its 418 other status
    entries are untouched and nothing is staged. Git ignores the backup folder and the guard's record,
    which has 21 more lines, 17 of them marked `upgrade-check`. Committing the two files needs your word,
    as after the runs before it (section 9, item 12).
  - *Not done.* The two training scripts and a final evaluation were not run, as before.
- **Not done.** The fine-tuning script ran with one seed, on native Windows only. The status fix is not tried
  on a real remote run. The commands of the guide's scenario A were not run on Linux.

## Round 5 (14 November 2026): another model's review, checked claim by claim, and what was built from it

You gave me a review of the kit by another model, 22 ranked recommendations and a proposal to rebuild the kit
as six "planes", and asked for three things: review it, build a plan from it, carry the plan out. I treated
every statement of the review as a claim to check before anything changed. A claimed way past the guard
counted only where a probe call in a temporary project showed it (21 calls). The claims about the keep rule
were tried in a simulation of the rule (40,000 campaigns per case). The others were read in the code. The
plan had nine steps, one per area, and each claim has its verdict (`docs/upgrade/PROGRESS.md`, "Round 5").
When the nine steps were built and tested, a reviewer with no part in the work looked at the result. It
found nine faults and four smaller ones; all are fixed, and so are five more of the same kind that fixing
them turned up ("The independent review"). The full test run on the fixed code then failed two checks in
WSL. Both were faults of the kit, older than the round, and both are fixed ("Tests").
The usage limit shaped the work as before: research went no further than a build or a line of a reference
needed, the papers behind the reference text were read as abstract pages, one reviewer took the place of
the deep-sweep skill, and no campaign ran with a real agent. Commits: `600499a` to `850020a` (49, the nine
steps), `2071d99` (a control for the fine-tuning task), `5aff688` to `4842b81` (13, the fixes after the
independent review), `b48d606` (README, guide and the guard's description of itself), `d857607` and `9d6f876`
(the two faults the test run found), `827c35c` (a repair of the second of those fixes) and those of the
records. They follow the public commit `60cc0b0`, so
a push makes them public history. Nothing is pushed. Nothing was run, read or changed on your real install.

### In short
1. **The review held where it named a concrete fault, less often where it proposed a design.** Its claims
   went into the ledger as 89 rows of the note `round5`: 37 adopted and built, 29 rejected, 19 undecided
   (each with the test it needs) and 4 held for your decision. Three of its claims were wrong on the facts:
   calls such as `Path.unlink` do not pass under `--readonly` (four probes were refused), `AGENTS.md` was
   part of the source hash, and the repository has a licence file. Its repair of the keep rule did worse in
   the simulation than the rule it would replace. Two of its instructions I did not follow: removing the
   checkout under `.claude/worktrees/`, which is the working copy of this session, and adding an Apache
   licence, where the repository has the MIT licence you chose.
2. **The two practice evaluators and the loop's evaluator are harder to fool.** The character-model
   evaluator looked for a look-ahead at one position, 64, and scored the rows in file order: a model that
   copies the next token everywhere else scored 0.11 nats, where an honest model scores about 1.7. It
   now scores the rows in a fixed shuffled order, tries the look-ahead at every position with another row's
   text, and refuses a saved model whose code reads or writes files. A real export scores the same to all
   printed digits. The fine-tuning evaluator followed a link out of the run folder and handed every key of
   the adapter's config to PEFT. The adapter's files must now lie in the run folder, and the config may set
   only the keys of a plain LoRA adapter. On Linux with bubblewrap the loop runs a project's evaluator with
   the project read-only, apart from the run folder it scores and what the new key `loop.eval_writable`
   names. The self-test's tampered copy no longer equals the original where a run's records hold whole
   numbers only.
3. **Five ways past the guard are closed, and you will notice the questions.** Each was allowed without a
   word in a probe: shell code attached to its flag (`bash -c"..."`), a PowerShell command inside
   `-EncodedCommand`, a sealed path put together from string parts in a line of code, a file edited so that
   its code opens a sealed path, and a sealed path inside the arguments of an MCP tool. The first three are
   now read like a written command or path. The last two are questions, because the guard cannot know
   whether the text will run: an edit that writes `data/test/...` into a script asks, also when the file
   named that path before. In an unattended session, and with Codex and Cursor, a question is a refusal.
   Three smaller changes: a decoder piped into a shell is asked about, a shell command that names git's
   hooks or its configuration file is asked about, and a folder sealed as a whole is searched to its end
   while five seconds of the call allow, where the bound of 20,000 files let a filtered search pass.
4. **Sealed files stay out of a run's snapshot whatever the pattern.** The snapshot and the loop went by the
   literal start of a sealed pattern. With `**/test/**` or `data/*/test/x.csv`, a git-ignored data folder
   was linked whole into the run's copy of the source, sealed files included, and the loop neither hid such
   files from training nor noticed a change to them. Both now follow the pattern, at any depth and behind
   links inside the project. Where a run is not confined (Windows, macOS, Linux without bubblewrap), a
   change that adds a line with `EXP_PROJECT_ROOT`, the name through which a run finds the project folder,
   makes its iteration invalid.
5. **The keep rule: a change's own runs can no longer lower the bar it has to clear.** Of the review's two
   main claims the first did not hold: a change's three seeds against the baseline's panels keep a change
   without a gain in 1.4 to 2.7 % of cases, around the nominal 2.3 %. The second held in part: a change
   whose runs vary far less than the baseline's was kept without a gain in 5.6 % of first iterations,
   because its own panels pulled the pooled noise down. The review's repair was worse where it matters (a
   change three times as noisy kept in 15 % of cases, a real gain found in 44 % instead of 68 %). Built
   instead: the change's panels may not lower the variance, and a change more than three times as noisy is
   tested with its own variance. Simulated: 2.9 % for the quiet change, about 7 % for the noisy one (10 to
   14 % before). The price is power at a campaign's first change, 61 % for a gain of two deviations where it
   was 68 %, and about two points later. Three smaller repairs: a stray run of a rejected change leaves the
   pooled noise again, the seed that screens a change rotates, and a pause keeps the line a restart began.
6. **A stop is obeyed, and a stopped run is not scored.** The two practice trainers never asked whether a
   stop was requested, so `expctl stop` waited for the time budget. They now end, score and save. Trying
   that showed two faults of the loop that the review had not named: it scored a training run that something
   outside had stopped (Windows) or booked the stop as the change's crash (Linux), and a change whose test
   was interrupted could not be proposed again. Both are fixed. `RunLog` no longer writes run files from the
   extra ranks of Lightning's own launcher.
7. **A remote run gets the code that was hashed, and the records have fewer gaps.** The archive for a remote
   run was built again by the background controller, and again after a preemption, so what ran could differ
   from what the launch had hashed. The launch now packs it once, and that file is what is sent. A link in
   the project that leads to sealed data stays at home. Rows written to the remote ledger at the same moment
   could destroy each other on Windows (eight writers of 100 rows left 748 rows and 19 torn lines; now 800
   and none). `resume` refuses when the source changed since the launch. The receipts of final evaluations
   are also kept in git's common folder, so removing a worktree no longer takes its uses out of the count.
   An `ssh` target can name a command that runs here when its last run has ended (`on_finish`), for a rented
   machine that would go on costing.
8. **Failures show before they cost a run.** `expctl env --probe` tries CUDA, bf16 autocast, the flash
   attention kernel, fused AdamW and `torch.compile` in the project's interpreter, one process each, so a
   wheel that ends the interpreter is a line of a report and not a dead run. The loop compiles a change and
   compares it with the campaign's base before training: a change that does not compile is a crash without
   a run, and one that alters only comments or layout is no change. After a compile error, or a failure of
   the first seed in the first quarter of the run budget, the worker gets one repair turn. The new command
   `expctl audit-splits` counts the records that two splits share and prints a fingerprint per split, never
   a row.
9. **References, installer, ledger.** The fine-tuning reference says which objective TRL 1.17.1 runs when a
   script sets nothing (not the GRPO of the original paper) and names four objectives after GRPO by the
   symptom each answers. Two installer faults are fixed: an apostrophe in the interpreter's path broke the
   two subagent files, and a later run wrote a second header into `.gitignore`. The ledger had a fault of
   its own, which the review found: a reference that covers a row outranked the record of what was built,
   so eleven rows showed as finished on the reference's word. Eight of them are unfinished and say what is
   missing; three are finished, two of those because this round built them.
10. **The fine-tuning task has a control.** A run that trains the shipped script on the training messages
    with their intents dealt out again at random can learn the form of an answer, not which intent a message
    has. It scored 0.012, 0.023 and 0.008 exact answers on three seeds, where the honest script scores 0.35
    to 0.39, and 0.011 with a stronger learning rate. Its floor is 0.05. The loop's self-test trains it once
    before a campaign's first session and stops the campaign when the evaluator scores it above the floor,
    which is what an evaluator that leaks the answers would do.
11. **A reviewer with no part in the work then found nine faults and four smaller ones, and all are
    fixed.** Most are further spellings of what point 3 had just closed: a sealed path with a backslash, a
    brace list or `$'..'` inside its name; code that decodes its own text; two string literals side by
    side; a fixed count of words or literals behind which the guard stopped reading; code written into a
    notes file and run from there; `git add -f` over the sealed folder, after which `git diff --cached`
    prints it; git settings that make git start a program. One made the hook crash: a tool input nested
    about a thousand brackets deep, which Claude Code takes for a hook that failed, and lets the call go
    on. Two lie outside the guard. The character-model evaluator scored an untrained model that reads its
    own scoring file, through a call written with blanks around the dot (1.25 nats, where the shipped script
    reaches about 1.7). And a directory junction gave sealed files a second name, under which a snapshot
    copied them. Fixing these turned up five more faults: code handed to a nested shell was checked only
    from the folder the line starts in, code on a runner's standard input was not read at all, the
    evaluator loaded a second directory of a model file that its check had not read, a snapshot made an
    absolute link to a folder again as it was, and where the sealed folder is itself a link to storage
    outside the project, a second link to that storage brought the sealed files into a snapshot. The price
    is more questions, some about harmless commands ("Things to know"). No second reviewer looked at the
    fixes.
12. **Most of the faults of point 11 are older than this round, so the public version has them.** I tried
    the junction, the linked storage, the case of a sealed pattern, the nested folder, the standard input
    and the model file's forms on the public commit `60cc0b0`: each is there. The fixes reach the public
    repository with a push, which waits for your word.
13. **The full test run on the fixed code found two more faults, both older than the round and both in the
    public version.** At `b48d606` two checks of `tests/test_kit.py` failed in WSL. The first: where a final
    evaluation is configured, the guard looks every word of a command up as a file, and on Linux and macOS
    that lookup raises an error for a word of more than 255 bytes, which the program behind `python -c` or
    a long commit message is. The check ended there as an internal error: a question for a harmless line,
    so a refusal in an unattended session and with Codex and Cursor, and a question where a refusal was
    due. The second: `expctl` told a run from a later process with the same number by its start time, which
    on Linux moves whenever the system clock is set. Once the clock has been set by five seconds a live run
    reads as lost, and the guard, which learns of live runs through the same function, stops protecting
    it. I watched both in WSL, whose clock was being set back that day by three to four and a half seconds
    a minute: three and a half minutes after its launch the code before the fix read its own live run as
    lost, and its guard let a write into that run's folder pass, which it had refused at the launch. The
    new code kept the run and the refusal in the same session. On Linux the records now carry the boot's id
    and the process's start tick, which do not move. Both faults are fixed (`d857607`, `9d6f876`); a third
    commit, `827c35c`, takes back a step my own check of the second fix found, a reader inside a time
    namespace, which the first form of the fix no longer recognised ("Tests"). Neither fault shows on
    Windows, where every fix after the independent review had been run before that full run, and where the
    reviewer had worked.
14. **Tests**: all seven files pass at `827c35c`, this round's last change outside the records, in WSL and
    on native Windows, in three interpreters each: 1,171 checks on Windows and 1,184 in WSL
    with the default interpreters (866 and 874 before this round). One commit of the round broke a check
    that passed before, and the next but one repaired it. The first full run on the fixed code failed the
    two checks of point 13; the second, at `a135bea`, passed in WSL, and I stopped it on Windows after the
    default interpreter had passed, when point 13's last change became due ("Tests").
15. **The ledger**: 1,609 rows (1,505 before): the review's 89 claims and 15 rows for the fixes of points
    11 and 13. Of 474 adopted rows, 332 are finished and 142 unfinished (422, 288 and 134 before;
    the check of the ledger in point 9 moved eight rows from finished to unfinished).
16. **Not built.** The rebuild as six planes: every installed path would move, which breaks the upgrade of
    existing installs through the manifest, and the single-file scripts that run without packages are a
    requirement of the prompt. The mechanisms worth having went into the existing files. New skills, a hash
    chain for the remote ledger, seeds matched with the baseline's and a `doctor` command are among the 29
    rejected rows, each with its reason. Seven groups of methods that the review names were not opened
    under the usage limit and are Assess rows: nothing about them is verified ("Not done, and why").
17. **Your real install does not have this round, and nothing is pushed.** Both wait for your word, with
    six other questions ("What needs your decision").

### The review's claims, rank by rank
"Held" means that a probe, the simulation or the code showed the fault. The reasons for what did not hold
are in the ledger rows of the note `round5` and under "Verdicts" in `docs/upgrade/PROGRESS.md`.

| Rank | Subject | Held, and built | Did not hold, or not built | Commits |
|---|---|---|---|---|
| 1 | The practice evaluators, the evaluator's box | Look-ahead at one position only, rows in file order, a loaded module unchecked; a link out of the run folder, every config key handed on; every file writable for the evaluator; a tampered copy equal to the original | A switch to weights with a fixed architecture: the task must stay free to change the architecture | `3fd5c16`, `f274041`, `ccf8ad0` |
| 2 | Ways past the guard | The five ways of point 3; the bound of 20,000 files, for a folder sealed as a whole; shell writes to git's hooks and configuration | `Path.unlink` under `--readonly`: refused already. A refusal after the guard's time limit: a question is the design, and a refusal where nobody can be asked. Held back: a walk for patterns that begin with a wildcard | `2a2edf6`, `32442fb`, `47cb8eb`, `0abddf2`, `19d5ff5` |
| 3 | Sealed paths in snapshots and the training box | Wildcard patterns in snapshots and in the loop's checksums; found while building: a link to a folder with sealed files | `EXP_PROJECT_ROOT` out of a run's environment: runs share outputs through it (the loop's scan of a change now counts the name). Held back: a process namespace. Yours to decide: a container | `5563f6c`, `319daf2`, `d8cc1e9` |
| 4 | The keep rule | A change's runs lower its margin (in part); a stray run stays in the pool; the screening seed is always the same; a pause drops the line a restart began | Three seeds against six; the review's repair; Welch's degrees of freedom (tried); a bootstrap over test items; "GPU seconds are overbilled" (an upper bound on purpose; the reference now says how they are counted) | `92b9419`, `3792686`, `be6abde`, `1ed9177`, `2386068` |
| 5 | `runlog.py` | The ranks of Lightning's launcher all write run files; the practice trainers never ask for a stop | A stop for one run of a process: the request stands in for the signal, which reaches the process. Locks around two sets: their operations are atomic | `2953f6d`, `3ab4ae4`; found here: `fd98c12`, `d8ed0da` |
| 6 | The remote runner and provenance | The bundle built again; a link to sealed data followed; a pulled name outside the mirror; ledger rows lost on Windows; a rented machine that goes on costing; four faults of `expctl` (a credential-named file copied into the snapshot, `resume` with changed code, a reused process number, a receipt that leaves with its worktree) | "`AGENTS.md` is left out of the source hash": it was in, and the reverse is built. A refusal of every link out of the project; a hash chain for the ledger; two launches at the spending cap; a restricted environment for runs | `0c4ba73`, `d6ded34`, `58e248a`, `20859f6`, `89493f4`, `e386102`, `6d0ecca`, `d64a154`, `8ff6f8b`, `7d9dcc7`, `1141fcd` |
| 7 to 10 | Speed and search | No check that the fast paths work here; a change that does not compile costs a run; an early crash costs the iteration | Import checks of every package; a callback for TRL (`hf_callback` serves its trainers); helpers for tabular models and prompt optimisation; block markers; `nnloop finalize`. Held back: a stop at a quarter of the budget, other engines' logs, traces for the worker, crossover | `dec8971`, `a4dc52e` |
| 11 to 13, 17 | References | The fine-tuning reference named no objective after GRPO | A qualification of Schedule-Free AdamW (SKILL.md calls it an alternative to test already); `RunLog.check_rlvr()` (thresholds without a source). Not opened: seven groups of methods | `11ca540`, `cae1f44`, `b56207d` |
| 14, 15 | Other agents, MCP servers | Nothing to build without an install | `sandbox_mode` in Codex agent files (against Codex's documentation); a refusal in place of the question before Hugging Face tools. Yours to decide: Antigravity, Gemini CLI, the MCP servers | none |
| 16, 18 | Data and wiring checks | Ledger rows named kit code that was never written: the split check is built, the wiring checks are reference text; a control for the fine-tuning task, with a measured floor | A data manifest at every launch; near-duplicates in the core; a check of timestamp order; floors computed by the loop. Held back: a leak audit, parallel trials | `e1cf085`, `50549c1`, `2071d99` |
| 19 | Small repairs | The ledger's generator; the apostrophe; the `.gitignore` header; the warnings that the references promise in `expctl env` | Folded YAML in the installer's reader; a licence file; removing this checkout; a `doctor` command (`selftest` and `env` are that command) | `00a5eb1`, `e376b6c`, `7cede64` |
| 20 to 22, the rebuild | New skills, cloud drivers, a second pilot, six planes | Nothing | New skills; the rebuild. Yours to decide: cloud drivers, a second pilot | none |

### The independent review
One reviewer with no access to my working context: a fresh subagent (Claude Opus) with a throwaway clone of
the kit at `850020a`, a description of what the guard, the snapshot, the loop and the two practice
evaluators must guarantee, and the question which calls or files get past them. It replaced the
deep-sweep-red-team skill, to stay inside the usage limit. It read the code, ran 14 probe scripts of its own
against temporary projects and reported nine findings and four of lower weight, each with its probe. I ran
the probes for findings 1 and 2 again before and after the fix; every fix has checks in the test files that
state what the code did before.

| Finding | What I did |
|---|---|
| 1. The character-model evaluator scores a model that reads its own scoring file. The saved code calls `torch . from_file(...)`, with blanks around the dot, which the evaluator's text check did not match and PyTorch runs as written. Untrained, it scored 1.25 nats, and every look-ahead, row and repeat check passed | Fixed (`079d1f0`). Every code entry of a model file is read as tokens before anything is loaded, so blanks, `getattr` with a name joined from strings, a `Code/` folder and a second entry of one name are seen and refused. Found while fixing: a file with a second directory, which Python's `zipfile` does not read and PyTorch does; the evaluator scored such a file. What PyTorch loads now is an archive the evaluator writes from the entries it read. Every call goes to a freshly loaded copy, which replaces the two checks for a model that keeps something between calls: they did not see a list that grows. The shipped trainer scores the same to the last digit |
| 2. A directory junction puts a real copy of a sealed file into the snapshot. With `data/test/**` sealed and a junction `alias` that leads to `data`, git lists `alias/test/labels.csv` as a file of its own, the snapshot copied it, and a read of the copy was allowed. Making the junction was allowed too | Fixed (`4842b81`): a snapshot judges every source file by the place it really lies in as well as by its name. Found while fixing: a link to a folder that leads out of the snapshot (an absolute one) was made again as it was, with the sealed files below it; it is now linked without them, as a git-ignored one is. The reviewer's probe: sealed files reachable in three of six layouts before, in none after. Also found while fixing: the layout in which the sealed folder is itself a link to storage outside the project (`data` leads to another drive). The storage has no name in the project, so a second link to it, to `data` or to the sealed folder brought the sealed files along, copied where git lists the files below a junction and linked whole as a git-ignored folder. A file is now also judged by the name the sealed pattern has for its real place, which is the guard's rule for reads. My probe of that layout: sealed files reachable in six of six cases before, on the public commit too, and in none after. Not built: a question about making a junction or a link (a limit, below) |
| 3. `git add -f data`, then `git diff --cached`, prints sealed content; `git add -Af`, a commit and `git show` do too | Fixed (`cc2bfbe`): a forced add, or `git stash --all`, over a folder that holds sealed files is asked about. An ordinary add stays unasked: it takes what git does not ignore |
| 4. Spellings that leave the path's letters intact: `data/te\st/labels.csv`, `data/{test,}/labels.csv`, `data/$'test'/labels.csv`, and PowerShell's escape character inside the name | Fixed (`f7ed572`): every rule also runs on the line as a POSIX shell and as PowerShell would take it, with those marks resolved, for the read-only subagents too. A brace list of more than 64 names is asked about |
| 5. Decoded code that runs without a pipe: `sh -c "$(echo ... \| base64 -d)"`, `exec(base64.b64decode('...'))`, PowerShell's `[scriptblock]::Create(...FromBase64String(...))` | Fixed (`826222d`): asked about, as the piped form was: a decoder inside `$( )`, `<( )` or backticks, one piped into `xargs`, and code on the line that decodes text itself |
| 6. The checks that join string literals stop early and miss one way of joining: a sealed path behind 300 path-like words or 400 literals of a text was not looked at, and Python's `'data/te' 'st/labels.csv'` was read as two strings | Fixed (`70a4aeb`, `d8d34c1`): literals side by side are joined, and no fixed count decides any more what is checked. Eight more such counts went with these two (words, nested commands and changes of folder of a line, arguments and levels of a tool's call, parts of an edit, files a wildcard matches). What five seconds of the call do not finish is asked about |
| 7. Code written to a `.md` file can be run: the edit tools write notes without the guard reading their text, and `python peek.md` passed | Fixed (`84d7360`): a command, or a file's new text, that runs a `.md`, `.mdx` or `.rst` file is asked about. Reading, rendering, linting and writing notes stay unasked |
| 8. A deeply nested tool input crashes the hook: about 1,500 nested brackets, exit code 1, nothing printed. Claude Code takes that for a hook that failed and runs the call | Fixed (`5aff688`): refused like other input the guard cannot read, with exit code 2, and whatever error the guard's main function does not catch itself now ends as a refusal too |
| 9. Git's hooks and settings can be changed without naming `.git`: `git config core.hooksPath`, `core.fsmonitor`, `--file .git/config` | Fixed (`13dd89f`): a git setting that makes git start a program is asked about, in `git config`, `git -c`, the `GIT_*` variables, a clone and a template folder. Tried with git 2.43 and 2.52: a plain `git status` ran both planted programs. The kit's own git calls now switch the two settings off that act without a word |
| Lower weight: `python -c` with `os.walk('data')`, `shutil.make_archive`, `du -ab data` | Fixed (`4e204eb`): asked about over a folder that holds sealed files, as `grep -r` and `tar` were |
| Lower weight: MCP search tools over `data` | Fixed (`cd75002`): an MCP tool that is handed the folder which holds the sealed files is asked about |
| Lower weight: a sealed pattern in another case than the folder on disk (`data/Test` beside `data/test/**`, or the pattern `DATA/TEST/**`): the snapshot reached the file, while the guard refused the agent's read | Fixed (`4842b81`): the run tools read the sealed, frozen and editable patterns without case where the filesystem ignores it, as the guard does |
| Found while fixing: text handed to a nested shell or interpreter was checked from the folder the line starts in, so `cd data && python -c "open('test/labels.csv')"` passed | Fixed (`cadf196`): checked from every folder the line may be in |
| Found while fixing: a runner without a script takes its code from standard input, and `echo "..." \| sh` or `bash <<< "..."` was not read as code | Fixed (`4e204eb`): read like the text behind `-c` |

**What held, in the reviewer's words:** encoded PowerShell commands, with the parameter's name in full or
cut short; joins with `+`, `/`, `os.path.join`, `Path(...)` and `'/'.join([...])`; edits whose new text
names the path in other case or with backslashes; `file://` addresses in MCP arguments; shell writes to
`.git/hooks` and `.git/config`, also through a `cd`, `cp`, `ln -s`, `tee` or a Write; recursive commands
over the sealed folder's parent; snapshots with `**/test/**`, `data/*/test/labels.csv` and paths with
blanks; a NUL byte in a path, which gives a question and no crash.

**What it did not look at:** the evaluator's box in `nnloop.py`, the fine-tuning evaluator beyond its diff,
`nn_readonly.py`, `audit-splits`, the walk of a sealed folder and its time limit, and `nnremote.py`. It ran
on native Windows only. No second look was made: the fixes are verified by my own probes and by the checks
in the test files, not by a reviewer.

### Changes in the behaviour of existing features
**The guard.** The sealed test set, the frozen evaluator and the protection of live runs are not weaker:
items 1 to 22 below each add a question or a refusal, and none lets through what was asked about or refused
before. Item 23 is the one change in the other direction, and it is a repair: on Linux and macOS a command
with a very long word was asked about because the guard's check broke off with an error, whatever the
command did. Such a command now gets the check every other command gets, so a harmless one passes, and one
that reads sealed data is refused where it was asked about. No guard check that existed before this round
was changed or removed. Tests: the guard's table and cases in `tests/test_kit.py` and three port checks in
`tests/test_ports.py`. On the code before the five commits of step 2, 21 of that step's new checks in the
first file and 2 in the second fail; the fixes after the independent review added 190 checks to the first
file and one to the second, and the two faults of the full test run at `b48d606` three to the first. One
change to the protection of live runs is not in this table, because it is made in `expctl`: on Linux the
guard no longer loses a live run when the system clock is set ("Runs, snapshots and records", item 12).

| | Change | Before | Reason | Commit |
|---|---|---|---|---|
| 1 | Shell code attached to its flag (`bash -c"..."`, `cmd /c"..."`) is checked like a command of its own, under `--readonly` too | not read | a probe read a sealed file that way | `2a2edf6` |
| 2 | The value of PowerShell's `-EncodedCommand`, short forms included, is decoded and checked | not read | the same | `2a2edf6` |
| 3 | Question: a decoder whose output goes to a shell or an interpreter (`base64 -d \| sh`) | passed | the guard cannot read what will run | `2a2edf6` |
| 4 | A path joined from string literals in a line of code (`Path('data') / 'test'`, `os.path.join`, `+`) is resolved like a written one, so a sealed one is refused | passed | a probe read a sealed file that way | `32442fb` |
| 5 | Question: the new text of Write, Edit, MultiEdit or NotebookEdit, or the lines a patch adds, name a sealed path or the unsealing token. Not for `.md`, `.mdx` and `.rst` files or the kit's config | passed | this is how training code comes to read the test split | `47cb8eb` |
| 6 | Question, a refusal where nobody can be asked: the arguments of an MCP tool name sealed data inside a longer string. Not for the agent's own tools (Task, WebFetch): a task for a subagent may name the sealed folder, and the subagent's calls reach the guard too | passed | in a probe, an SQL query that names a sealed file passed on its way to an MCP tool | `47cb8eb` |
| 7 | A folder sealed as a whole is walked beyond 20,000 files for up to five seconds of the hook call; a walk that the time ends counts as reading, a question | a filtered search passed | behind the bound a sealed file went unseen | `0abddf2` |
| 8 | Question: a shell command that names `.git/hooks/...` or `.git/config`. The guard cannot tell a source from a target, so `cat .git/config > x` is asked about; `cat .git/config` alone passes | passed (the edit tools were asked about) | a hook written there runs outside the guard | `19d5ff5` |
| 9 | Question: a shell command that changes `.git/nn-training-final-eval.jsonl` | the file did not exist | it is the shared record of final evaluations (below) | `0c4ba73` |
| 10 | Question before `expctl audit-splits` where the config seals anything, a refusal where nobody can be asked; a read-only subagent is refused the command | the command did not exist | every count of records shared with a sealed split is a small look at it | `e1cf085` |
| 11 | Refusal: a hook input nested too deeply to read. Any error that the guard's main function does not catch itself ends as a refusal too (exit code 2) | the hook ended with exit code 1, and Claude Code ran the call | an unread call must never pass | `5aff688` |
| 12 | Question: a git setting that makes git start a program: `git config` with `core.hooksPath`, `core.fsmonitor`, an alias or any key outside the list of keys that hold a plain value; `git -c key=value`, `--config-env`, `--exec-path=`; the `GIT_*` variables for the same settings; a clone that sets one; a template folder. An option of git's own that the guard did not know (`-P`, `--no-advice`, a quoted value with a blank) no longer hides the subcommand from the rules for a push and a reset | passed | git then runs a program that the guard never sees | `13dd89f` |
| 13 | Question: `git add -f` (also `-Af`, `--force`, with a wildcard, from another folder) and `git stash --all` where sealed files lie below what the command takes | passed | they put ignored files into git's store, from where `git diff --cached`, `git show` and `git stash show -p` print them without naming one | `cc2bfbe` |
| 14 | Every rule also runs on the command line as a POSIX shell and as PowerShell would take it: a backslash inside a name, `$'..'`, a brace list, PowerShell's and `cmd`'s escape character. Question: a brace list of more than 64 names. The read-only subagents' rule reads the same second texts | such a spelling of a sealed path passed | a probe read a sealed file with each | `f7ed572` |
| 15 | Question: decoded text that reaches a command without a pipe into a shell: a decoder inside `$( )`, `<( )` or backticks, one piped into `xargs`, and code on the line that decodes text itself (`b64decode`, `unhexlify`, `FromBase64String`, `atob`). Decode flags written together (`-di`) count | passed | the guard cannot read what will run, or be named | `826222d` |
| 16 | Python's string literals that stand side by side are joined (`'data/te' 'st/labels.csv'`), in code handed to an interpreter, in a here-document and in the text an edit writes. In a shell's own line two literals with blanks between them stay two arguments | read as two strings | Python reads them as one path | `70a4aeb` |
| 17 | No fixed count decides what is checked: 300 path-like words or 400 literals of a text, 400 words, 8 nested commands or 4 changes of folder of a line, 8 literals of one join, 64 arguments or 5 levels of an unknown tool's call, 256 parts of an edit and 200 files that a wildcard matches were the counts. Question: an edit with more path-like words than five seconds allow to look up, and a wildcard with more matches than that | a sealed path behind the count passed | a probe hid one behind 301 words | `d8d34c1` |
| 18 | Question: a command line, or a file's new text, that runs a `.md`, `.mdx` or `.rst` file: as a runner's script or standard input, piped into a runner, sourced, as the command itself, spliced into a command line where code stands, or executed or loaded by code that names it on the same line | passed | the edit tools write such files unread, because documentation may name the test set | `84d7360` |
| 19 | Text handed to a nested shell or interpreter (`bash -c`, `python -c`, `powershell -Command`) is checked from every folder the line may be in | checked from the folder the line starts in | `cd data && python -c "open('test/labels.csv')"` passed | `cadf196` |
| 20 | Question over a folder that holds sealed files: `du -a`; a tree walk in Python code that an interpreter is handed on the line (`os.walk`, `Path.rglob`, `shutil.copytree`, `shutil.make_archive`, a `**` in a string) | passed | they list or copy every file of the tree, as `find` and `cp -r` do | `4e204eb` |
| 21 | Code on a runner's standard input (`echo "..." \| sh`, `bash <<< "..."`, `cat <<EOF \| python -`) is read like the text behind `-c` | not read | `cd data && echo "cat test/labels.csv" \| sh` passed | `4e204eb` |
| 22 | Question: an MCP tool that is handed a folder with sealed files below it (under `path`, `paths`, `directory`, `root`, as a `file://` address, or any argument written as a path). Not for the project root, which tools are handed all the time, and not for a bare word under a key that names no place | passed | such a tool lists and reads files by itself | `cd75002` |
| 23 | A word of a command that is longer than a file name can be (255 bytes on Linux and macOS) counts as naming no file, and the check goes on to its end | where `final_eval_commands` is set, the lookup of such a word raised an error there and the check ended as an internal error: a question, whatever the command did | the last full test run in WSL: a line that must be refused was asked about, and a long commit message or a long `python -c` program was asked about too | `d857607` |

Limits, each also in the README ("Notes and limits"):
- Items 1 to 10: a path with a variable in it passes (literals only). Text that merely mentions a sealed
  folder, a URL for one, is asked about, as it is in a command, and item 5 asks about every edit that writes
  such a mention, also when the file held it before. Item 10 reads the command's text, so a script that
  calls the command is not asked about, as with the final evaluation. For a sealed pattern that begins with
  a wildcard the walk covers the whole checkout and keeps the old bound.
- Item 12: a git folder elsewhere (`--git-dir=x`) whose `config` was written as an ordinary file is not
  seen. Two harmless forms ask: `git config --type bool key value` and a read with `-f file key`.
- Item 13: `git stash -u` and an ordinary add take what git does not ignore and stay unasked.
- Item 14: a name built at run time, from variables, a `{a..b}` range or a command's output, passes.
- Item 15: text decoded into a file and run later passes, and so do `rev`, `tr` and `printf` inside a
  substitution and strings that code computes.
- Item 17: a recursive wildcard written into a code file passes the check of an edit's text. On Windows a
  program text of more than 32,767 characters ends as an internal error of the guard, which is a question.
- Item 18: not seen are a notes file that is copied, renamed or cut into a file of another name first, one
  with a blank in its name, text read on one line and executed on another, a file name computed at run
  time, a runner the guard does not know (`conda run`, `sudo -u`, `pytest --doctest-glob`, `jupytext
  --execute`), a command written inline in YAML, and PowerShell's `[scriptblock]::Create(...)`. Asked about
  though harmless: a notes file handed to a runner as data (`perl -ne print notes.md`).
- Item 19: a change of folder the guard cannot read (`sudo -D data`, `start /D data`, a variable) in front
  of nested code is not followed.
- Item 20: a walk in a script file, in another language or through `tarfile`'s `.add()` is not seen, nor
  is a here-document that a command writes into a file. A walk whose folder is a variable asks, and so does
  a `**/` that stands in prose inside program text.
- Item 21: text piped into a runner the guard does not know is not read, nor is a file's content piped in
  (`cat script.py | python`).
- Item 22: a tool that only lists the folder asks too, and so does a folder above the project.
- Item 23: only the error for a name that is too long is taken as "no such file". Another error of a
  lookup, as for a word that names a place in a folder the account may not search, still ends the check as
  an internal error, which is a question. That was not tried.

**The loop and its evaluator.**
1. On Linux with bubblewrap the evaluator cannot write into the project outside the folder it scores (the
   way out is `loop.eval_writable`), and it no longer sees sealed data that only `final_eval_commands`
   names. An evaluator that writes elsewhere in the project fails there until the key names the place.
2. The loop checksums files sealed by wildcard patterns, so a campaign stops when one of them changes or
   appears, and its sandbox hides each folder sealed that way. `loop.link_paths` and `loop.eval_writable`
   are refused where a name below them matches such a pattern.
3. Where a run is not confined, a change that adds a line with `EXP_PROJECT_ROOT` makes the iteration
   invalid; the worker's rules say so. The scan reads the change's text, so a name built at run time passes.
4. The keep rule: the variance a gain is tested against is never below the estimate without the change's
   own panels, and a change more than three times as noisy as the pool is tested with its own variance; the
   confirmation applies the second rule to the kept commit's fresh panel. The panels of a change that is
   not kept leave the pool when one score lies farther from the change's median than a t multiple (z = 4)
   of the deviation the other panels give; the ledger row carries `unpooled: true`.
5. The first seed of an iteration rotates through the panel, and the discard reason names the seed. A
   campaign that pauses on the line a restart began puts that line by and a `resume` takes it up again.
6. A training run that something outside the loop stopped is not scored and is not the change's failure:
   the campaign pauses with `stop requested: the training run ...` and exit code 0. An iteration that a
   limit or a stop interrupted leaves the list of tried changes, so its hypothesis counts as untried.
7. Before a run, every changed Python file is compiled in the project's interpreter and its syntax tree
   compared with the campaign's base. The identity of a change is the hash of those trees, so a reformatted
   repeat of an earlier change is a `duplicate`. A campaign started before this round can test once more
   what it tried before, because its stored hashes no longer match.
8. One repair turn after a compile error, or after a failure of the first seed within a quarter of the run
   budget (at least 30 s). The worker gets the end of the run's output, and nothing of it where a sealed
   token appears in it. Not for a change that comes with a search. The session counts into the campaign's
   sessions, tokens and money; the ledger row carries `repaired`.
9. The loop reads the sealed, frozen and editable patterns without case on Windows and macOS (point 10 of
   the next list). A change to `Train.py` is a change to the editable `train.py` there, and a file under
   `Data/Test/` is checksummed and hidden as one under the sealed `data/test/**`.

**Runs, snapshots and records (`expctl`, `runlog`).**
1. A snapshot leaves out files sealed by a pattern that begins with a wildcard or has one in the middle. A
   launch now fails, with the reason, where a git-ignored link leads to the project folder or above it, and
   where sealed paths lie more than twelve folders deep in a git-ignored folder (only when the config seals
   something).
2. A snapshot links a file named like a credential (`.env`, `*.key`, `credentials.json`) instead of copying
   it, tracked or not, so it no longer freezes such a file's content. On Windows without the right to make
   links that is a hard link, as for git-ignored files.
3. `AGENTS.md`, `.mcp.json`, `.codex/`, `.cursor/` and `.agents/` are not experiment source: they leave the
   source hash, the snapshots and the remote bundles, so the hash of a project that tracks them, or does
   not ignore them, changes once. The journal, the search's storage file and the runs folder no longer make
   a tree `dirty`.
4. `expctl resume` and `nnremote resume` refuse when the source changed since the launch, unless
   `--allow-code-change` is given.
5. The receipts of final evaluations lie in git's common folder as well, shared by every worktree of the
   repository. `expctl selftest` may write there when it brings older receipts into the shared copy.
6. Without psutil, Windows reads a process's start time from the system, so a process number that went to
   another process no longer passes for the run.
7. `RunLog` writes no run files in a process whose `LOCAL_RANK` or `NODE_RANK` is above zero, unless `RANK`
   is set, which decides alone as before.
8. `expctl env` carries `warnings`: dated advisories for installed versions (`datasets` below 5.2.0 among
   them). `env --probe` is refused beside a live run.
9. A snapshot judges every source file by the place it really lies in as well as by its name: a file that
   git lists below a junction or a link, and that lies in a sealed place, stays out and is named under
   `sealed_kept_out`. A link to a folder that would lead out of the snapshot is linked without the sealed
   paths below it, as a git-ignored one is, where it was made again as it was. Where a folder on a sealed
   pattern's way is itself a link to another place, a file is also judged by the name the pattern has for
   that place, as source file and below a git-ignored link (`4842b81`). Limit: below a git-ignored link the
   absolute name of a place outside the project is not compared, as before, so a sealed pattern written as
   an absolute path does not keep a git-ignored link to its folder out of a snapshot (tried on Windows: the
   files that git lists below such a link stay out now, the git-ignored link is linked whole, as on the
   public commit; on Linux and macOS, by the code, the run tools match no absolute pattern at all, because
   the name they compare has lost its leading slash). The README says to name sealed data by its path in
   the project.
10. Path patterns are read without case on Windows and macOS, as the guard reads them: sealed, frozen and
    editable paths in snapshots, in the loop's checksums and in a remote run's archive. A folder there whose
    names do tell case apart is sealed further than its pattern says, which is the safe side (`4842b81`).
11. The git calls of `expctl`, the loop, the installer and the guard pass `-c core.fsmonitor=` and an empty
    hooks path, so a file monitor or a hooks folder that someone set in the project's git configuration
    does not run through the kit's own commands (`13dd89f`).
12. On Linux a run's records carry the boot's id and the process's start tick: `proc_key` in `pid.json`, in
    the manifest that `RunLog` writes and in a remote run's two process records, and `supervisor_key` for
    the supervisor. A process that matches them is the run's process, whatever the system clock has done
    since (`9d6f876`). Without a match the start time decides, as it did before: for a run launched before
    this change or logged by an older vendored `runlog.py`, on Windows and macOS, which are unchanged, and
    for a reader inside a time namespace, where the same process shows another tick (`827c35c`; tried in
    WSL with a namespace whose boot time is offset by 1000 s, before and after). So every record that was
    recognised before this round still is. What stays open is both at once: a reader in such a namespace
    after the clock was set by five seconds reads the run as lost.

**The remote runner.**
1. A launch packs one archive, refuses when the source changes while it packs, and removes the run folder
   when the launch is refused. The archive lies in the mirror until the run ends, so a live remote run
   takes up to `max_bundle_mb` of local disk. The automatic resume after a preemption sends it again; where
   it is gone, the resume goes by the working tree and is refused when that has changed.
2. A link or a junction is judged by its own name and by the place it leads to: one that leads into a sealed
   path, or to a file named like a credential, stays at home, and `remote.files` refuses a path with such a
   link below it. Since `4842b81` the place also counts by the name a sealed pattern has for it, where the
   sealed folder is itself a link to storage elsewhere. A pulled name that leaves the mirror never counts
   as mirrored.
3. Ledger rows are appended under a byte lock on Windows.
4. New key `on_finish` per `ssh` target: an argument list, checked at the launch, run on this machine when
   the last pull is complete and no other run of the project on that target lacks its exit record.

**The practice tasks.** Both evaluators refuse more (points 2 and 11), and both trainers end at a stop
request or at the launch's deadline and still score and save. A real export of the character model scores
the same to all printed digits; the fine-tuning evaluator scores as before and only refuses more. Three
things differ for a model file of the character task since the independent review: one with a method or an
attribute named `save` or `from_file`, or with code that Python's tokenizer cannot read, is refused; a
model that keeps something between calls is scored as on its first call, where two checks refused it; and
the evaluator holds the model in memory twice. A campaign on the fine-tuning task trains the control once
before its first session, as one run of the run limit (`loop.controls` in the task's config).

**The installer.** An apostrophe in the interpreter's path is written twice inside the subagent files'
quoted hook command, and the warning about a path with a space names a quote too. A later run adds its
paths under the kit's header in `.gitignore`; a file that has two headers already keeps them.

**Existing checks that changed, each with its reason.**
- `tests/test_loop.py`: the sandbox check "the evaluator runs without network" gave way to the stricter
  checks of the evaluator's box (`ccf8ad0`). The expected text of a first-seed discard ends with the seed
  (`92b9419`). In the second-panel test the two expected margins follow the new rule (`be6abde`). Three
  checks of campaign a (the crash of iteration 6, the number of sessions, the counters) expect the repair
  session that now follows that early crash (`a4dc52e`).
- `tests/test_remote.py`: the check added with `58e248a`, that the automatic resume is refused after the
  source changed, was replaced in `20859f6`, because that resume now sends the launch's archive and runs.
- `tests/test_benchmarks.py`: the check of the character-model evaluator's contract expected a refusal for
  two models that keep something between calls. It expects the fair model's score for both now, because
  every call goes to a freshly loaded copy (`079d1f0`); the refusals of the other three models are as they
  were, and four further forms of the file-reading model are refused.
- `tests/test_kit.py`: one row that `d8d34c1` had added, an edit whose text holds a wildcard over the folder
  with the sealed file, was made stricter in `84d7360`: its wildcard matches no file on disk and is asked
  about all the same. The check of a run's identity that `9d6f876` had added expected a record that carries
  another boot's key to count as another process. Since `827c35c` the start time decides there, so the
  check expects "the same process" for such a record with the right start time, and has one more case: a
  record with another key and a start time a minute off is another process.
- No other existing check was changed, and none was removed. The two checks that failed in WSL (below)
  stand as they were written: the code was repaired, not the checks.

### Tests
A full run is what "Round 2", "Tests" describes: a clean clone of one commit, all seven files, three
interpreters per platform. The number of checks per file, default interpreters:

| Commit | Platform | benchmarks | kit | loop | ports | remote | review_fixes | runlog_units | Failed |
|---|---|---|---|---|---|---|---|---|---|
| the public commit, before this round | Windows | 41 | 364 | 210 | 120 | 75 | 38 | 18 | none |
| | WSL | 41 | 368 | 211 | 121 | 75 | 40 | 18 | none |
| `850020a`, the nine steps | Windows | 44 | 417 | 235 | 125 | 90 | 38 | 19 | none |
| | WSL | 44 | 421 | 240 | 126 | 90 | 40 | 19 | none |
| `b48d606`, with the control and the fixes after the review | Windows | 50 | 607 | 238 | 126 | 90 | 38 | 19 | none |
| | WSL | 50 | 611 | 244 | 127 | 90 | 40 | 19 | 2 of the kit file's 611 |
| `a135bea`, with the two faults of that run fixed | Windows | 50 | 610 | 238 | 126 | 90 | 38 | 19 | none |
| | WSL | 50 | 614 | 244 | 127 | 90 | 40 | 19 | none |
| `827c35c`, with the repair of the second fix | Windows | 50 | 610 | 238 | 126 | 90 | 38 | 19 | none |
| | WSL | 50 | 614 | 244 | 127 | 90 | 40 | 19 | none |

At `827c35c` every file passes in all six interpreters. The benchmarks file has 42 checks in the two clean
interpreters of each platform, which have no PyTorch: the eight checks that need it are skipped there (five
that put model files through the character-model evaluator, three about a run of `train.py` under `expctl
launch`), and the file says so. `ports` has one check fewer under Python 3.8, which lacks a module that
check needs. The two platforms differ where a check exists on one of them only.

**The full run at `b48d606` failed two checks of `tests/test_kit.py` in WSL.** Every other file passed there
in all three interpreters, and on Windows the default interpreter and the clean 3.11 passed all seven files
(I stopped the 3.8 run of that commit when the WSL result called for new code).
- `guard Bash {"command": "python -c \"a0 = 'v0';... -> ask (want deny)`, in all three WSL interpreters. The
  row hands `python -c` a program of about 5,000 characters that opens a sealed file, and wants a refusal.
  The guard's answer was "guard internal error (OSError: [Errno 36] File name too long ...)". The traceback
  leads to the place where the guard, with `final_eval_commands` set, asks of each word whether it is a
  file: on Linux that question raises for a name of more than 255 bytes. The line is in the public commit
  too. The row itself came with `d8d34c1`, one of the fixes after the independent review, and I had run
  those fixes on Windows only, where the same question simply answers "no". That is the gap in my
  procedure which let a fault of Linux through to the last run: I checked narrowly while working and fully
  at the end, as instructed, and the full run did what it is for, but a run of the kit file in WSL with
  each guard commit would have shown the fault at once. Fixed in `d857607`, with two more rows (a long word
  after `echo`, a long commit message). Asked in WSL at `7c6a120`, the last commit before the repair, the
  guard answered all three commands with that internal error; at `a135bea` it refuses the first and lets the
  other two pass.
- `session hook injects status after compaction`, in the default interpreter only. The check wants the two
  live runs of the test in the session's context as RUNNING; they read "LOST: process gone without
  result/exit record" 36 s after their launch, though both were alive. `expctl` compares a process's start
  time with the one it recorded and allows five seconds. On Linux the start time is the boot time plus the
  process's ticks, and the boot time moves with the clock. In that WSL session the clock was set back in
  steps: the system's journal has "Clock change detected" every 30 s, and the distance between the wall
  clock and the time since boot fell by 4.955 s in 66 s when I measured it. In two later runs of the kit
  file from a clone of its own the check passed, so the failure comes and goes: two steps of that clock
  leave the shift just under the five seconds. Fixed in `9d6f876`: on Linux the records carry the boot's
  id and the start tick. The new check gives a live process a record whose start time is a minute off and
  expects it to be known as the same process on Linux, and as another one on Windows, where the time is
  all there is and does not move.

**The second fault and its repair, watched under WSL's own clock.** The check of `9d6f876` uses a record
whose start time is a minute off. To see the fault and the repair under a real clock, I launched one run
that only sleeps with the kit as it was before the fix (`7c6a120`; the lines that decide are those of the
public commit) and one with the new code, in temporary projects in WSL, and had each controller read its
own run every 30 s. The middle column is the distance between the wall clock and the time since boot, as it
moved since the launch.

| Session | Seconds after the launch | Clock set by | Code before the fix reads | New code reads |
|---|---|---|---|---|
| first: `7c6a120` against `a135bea` | 0 to 60 | under 0.02 s | starting | starting |
| | 90 | −0.994 s | starting | starting |
| | 120 and 151 | −3.505 s | starting | starting |
| | 181 | −5.431 s | **lost** | starting |
| second: `7c6a120` against `827c35c` | 0 to 90 | under 0.03 s | starting | starting |
| | 121 | −2.769 s | starting | starting |
| | 151 and 181 | −3.802 s | starting | starting |
| | 211 | −6.599 s | **lost** | starting |
| | 241 | −7.570 s | **lost** | starting |

Both processes were alive throughout. In the second session each kit's guard was also asked about a `Write`
into its own run's folder. At the launch both refused it. After the last row the guard of the code before
the fix let it pass, and the new one refused it as before. The guard takes its list of live runs from
`expctl`, so a run that reads as lost is no longer protected: no refusal of an edit in its folder or its
snapshot, no question for a command that may write there. That is how this fault reaches the protection of
live runs, in the public version too.

*The clock of this machine's WSL.* I measured it in six sessions on 14 November. Where I watched from the
start of the virtual machine, the clock stood still at first (a run of the kit file that ended 69 s after
the start saw 0.015 s) and was then set back in steps of one to three seconds, which began between one and
three minutes after the start. Once they came, they added up to 2.7 to 4.5 s a minute: 4.955 s in 66 s in
the session that failed, 74.9 s in the 20.5 minutes of the full run at `a135bea`, 66.6 s in the 20.3
minutes of the full run at `827c35c`, and the two sessions of the table. So both full runs of the repaired
code ran under a clock that was being set back, and passed. In my first account of this fault I took the load of the Windows tests, which ran beside that
session, for the cause. That was wrong: the full run at `a135bea` started with nothing else of mine running
on the machine, and its clock was set back as fast. What the numbers show is that every step went
backwards and that the rate was steady, as with a guest clock that runs about a twentieth fast and is set
to the host's time twice a minute; that is a reading, not a finding. The kernel there keeps time by the
processor's cycle counter, and both Hyper-V's time synchronisation and `systemd-timesyncd` were active. I
did not look further. Round 2's two clock faults fit the picture: both showed about two minutes after the
virtual machine had started, one with a step of about two seconds, which I read then as a single
correction after the start ("Round 2", "Tests"). For the public version it means that on this machine's
WSL, as its clock was that day, a live run reads as lost within minutes of its launch and for the rest of
its time.

*The step back that my check of the fix found.* In its first form (`9d6f876`) the fix let the boot's id
and the start tick decide alone wherever a record had them. I then read one process from inside a time
namespace whose boot time is offset by 1000 s (`unshare --time`, util-linux 2.39.3): the process shows
another start tick there, while its start time reads the same as outside. So that form of the fix took a
live run for lost where the rule before it had not. No part of the kit makes such a namespace, so I know
of no install it would have met; but the protection of live runs may not get narrower anywhere, and it had.
`827c35c` puts it right: a key that matches says "the same process", and in every other case the start
time decides exactly as it did before the round. Tried before and after in that namespace, and the check
of `9d6f876` was changed with it ("Existing checks that changed"). One case stays open: a reader in such a
namespace after the clock was set by five seconds reads the run as lost, as every reader did before.

*The run at `a135bea`.* It passed in WSL in all three interpreters. On Windows I stopped it after the
default interpreter had passed all seven files, because `827c35c` was due; the clean 3.11 had passed the
benchmarks file and was in the kit file, and the 3.8 run had not begun.

**One commit broke a check that passed before.** `7d9dcc7` (the `on_finish` command) was committed with the
reference-header check of `tests/test_kit.py` failing: its note had pushed the Refresh line of `remote.md`
out of the first eight lines, and I had run only the remote file before the commit. `1141fcd`, two commits
later, put the line back. Since then I ran the kit file before every commit that touches a reference, the
README or the guide.

### Verified by running, from documentation only, unverified
**By running.** The 21 probe calls of the guard before the fixes, and the new checks against the old code
(23 fail there). The simulations of the keep rule, for the rule as it was, the review's repair and what is
built. The lost ledger rows on Windows, before and after. The apostrophe fault, end to end, with an
environment in a folder named `o'c`. The three wiring checks of the sanity gate, with PyTorch 2.9.1. The
LoRA scales, with PEFT 0.21.2. The fine-tuning trainer's stop, once by hand on the GPU: launched with a
budget of 600 s and asked to stop after eight seconds of training, it ended after 105 steps as
`interrupted`, scored and saved its adapter, 22 s after the launch. The control of the fine-tuning task:
three seeds and the stronger script on the GPU, and once under the loop with the stand-in agent (the
self-test passed; 4 runs, 283 seconds). After the independent review: its snapshot probe before and after
the fix and on the public version; my probe of a sealed folder that is a link to storage elsewhere, in
three layouts of a second link, each as source files and as a git-ignored folder, before and after and on
the public version (Windows, with junctions; the test of it also runs in WSL, with links); the forms of a
model file that PyTorch 2.9.1 loads (blanks, `getattr`,
a `Code/` folder, a second entry, a second directory), each against the old and the new evaluator; the two
planted git programs with git 2.43 and 2.52; the guard's new answers as probe calls on Windows. After the
full run that failed: the guard's traceback for the failing row in WSL, in a project set up as the test
sets it up; the WSL clock, as described under "Tests"; the kit file with both repairs, on Windows and in
WSL, before the commits. After those repairs: the three commands with a long word, asked of the guard in
WSL before and after its repair; one live run per kit, read every 30 s under WSL's own clock by the code
before the fix and by the new code, in two sessions, the second with each guard asked about a write into
its run's folder; one process read from outside and from inside a time namespace, before and after
`827c35c`; the kit file and the remote file with `827c35c` on Windows and the kit file in WSL, before the
commit. The full tests above.

**From documentation only.** The settings of the objectives after GRPO come from TRL's `grpo_config.py` at
v1.17.1. The papers behind them, and behind the candidates in the optimization reference, were read as
abstract pages; no result was reproduced and no objective was run. No fetched page tried to give an
instruction.

**Unverified.** The fixes after the independent review and after the test runs, by anyone but me. A run's
identity after a clock that is set forward, as when a virtual machine's host has slept: the clock I
watched was only set back, and by the code the direction makes no difference. A Linux machine other than
this WSL. The guard's lookup on macOS, where the code is the same and no test ran. The repair turn and the compile
check with a real agent (the stand-in agent only). The `on_finish` command against a real machine: it ran a
stand-in command, and no machine was stopped with it. File links on Windows, which this account cannot make
(junctions and hard links were exercised; links in WSL): the snapshot's handling of a link that leads out
of it is tested in WSL only. The case rule on macOS, and on a Windows folder that tells case apart. The
evaluator's box on native Windows and macOS, where it is missing as the box for training is. What an agent
other than Claude Code does with the guard's new refusal of a nested input: the exit code is the one that
blocks on all three, by their documentation. The seven groups of methods in the Assess rows. Everything on
your real install.

### Things to know
- **The guard asks more, and sometimes about a harmless command.** A session that writes a sealed path into
  code, a config file or a notebook meets a question at every such edit. That is the intended price: the
  question is the only moment at which a person sees that training code is about to name the test split.
  Since the independent review these are asked about too, although nothing is read: `git config` with a key
  the guard does not know as a plain value, and `git config --type bool key value`; `git stash --all` and a
  forced add where sealed files lie below; a notes file handed to a runner as data; an MCP tool that only
  lists the folder which holds the sealed files; Python code on the line with `os.walk` over a variable or
  with a `**/` in a string. In an unattended session, and with Codex and Cursor, each of these is a refusal.
- **The guard remains a seatbelt.** The reviewer needed seven minutes and 37 tool calls for its findings,
  and the limits above name more ways around the guard that are known and open. What it cannot see is a path
  or a program that is put together at run time. For data that must stay unread whatever an agent tries, keep the test split
  outside the repository or run the agent in a sandbox, as the README says.
- **Making a junction or a link is not asked about.** A snapshot no longer follows one into sealed data, and
  the guard refuses a read through one. One case stays open: a link inside a git-ignored folder, where the
  sealed pattern begins with a folder's name (with `data/test/**` sealed and `cache/alias` leading to
  `data`, the snapshot links `cache` whole). A pattern such as `**/test/**` finds the files there.
- **The keep rule finds a real gain a little less often at a campaign's first change** (61 % against 68 %
  for a gain of two deviations in the simulation). A change that is noisier than the runs before it is
  still kept above the nominal rate, about 7 % where it is three times as noisy. The simulation covers one
  iteration; the whole-campaign simulation of 12 November was not repeated.
- **The control's floor is measured, not derived.** 0.05 is about twice the highest of four scores and a
  seventh of the honest script's lowest. Measure it again after a change to how a run trains that could let
  it gain from shuffled intents.
- **`on_finish` does not replace a shutdown timer.** It runs on this machine, so it does not run when the
  controller is gone. A rented machine still needs its own timer.
- **`audit-splits` finds exact matches only**, after Unicode normalisation, case folding and collapsed
  whitespace: its count is a lower bound. It refuses Parquet, Arrow, HDF5, databases and archives, and it
  keeps one digest per record in memory.
- **The compile check covers Python files.** A change to a config file goes to a run as before.
- **The character-model evaluator's checks are checks of what a model file says, not a sandbox.** A file
  operation that a later PyTorch adds to TorchScript is not on its list.
- **A system clock that is set while runs are live.** On Linux a run's identity no longer depends on it.
  Until this round is on a Linux install, a clock that is set by five seconds while a run lives makes that
  run read as lost and ends the guard's protection of it. This machine's WSL did that within minutes on
  14 November ("Tests"); your real install runs on native Windows, where a process's start time does not
  move with the clock.
  Two other readings still use the wall clock, and I left them: the age of a heartbeat, so after a forward
  step of more than the stale time (15 minutes by default) a run reads as stalled until its next
  heartbeat, and the five seconds the guard gives its own
  searches, which a forward step ends early (a question) and a backward step lengthens, up to the hook's
  limit of twelve seconds, which does not go by the wall clock. What else in the kit reads the wall clock,
  the loop's limits among it, I did not look at.
- **The two faults of point 13 show on Linux only, and that says something about this round's tests.** The
  fixes after the independent review were run on Windows while I worked, and the reviewer worked on
  Windows too. The full run in WSL covers the test files, not what a second reviewer on Linux would try.

### Not done, and why
- **A second look at the fixes after the independent review.** The reviewer saw `850020a`. The thirteen fix
  commits after it, and the three after the test runs (`d857607`, `9d6f876`, `827c35c`), are checked by my
  probes and tests only, for the usage limit. The third of those three exists because my own check found
  what the second had lost, which is the kind of thing a second reviewer is for.
- **A question about making a junction or a link to a folder with sealed files.** The guard would have to
  resolve every link a command makes; the snapshot and the read rules close what such a link gave away.
- **A campaign with a real agent** that uses the repair turn, the compile check and the search. It draws on
  your subscription.
- **A guard walk that skips the folders no sealed pattern can match**, so that the bound of 20,000 files
  goes for patterns that begin with a wildcard too.
- **A process namespace for the training box.** `RunLog` writes its own process number into the heartbeat,
  and inside a namespace that number is another one, so a dead run could pass for a live process outside.
  It needs the number left out or translated for boxed runs first.
- **A stop at a quarter of the budget for a run that trails**: it discards slow starters, and its saving
  needs runs of ten minutes or more to measure.
- **Not opened**: further RL objectives (AIPO, GiGPO, VAPO, Turn-PPO and four more loss types of TRL),
  parity between trainer and generator, distillation and preference objectives, adapter options, further
  optimizers, low-precision and kernel items, architectures. Each is an Assess row with the sources the
  review gave and the test it needs.
- **The Adopt rows that earlier rounds named as unfinished** still are: 142 with the eight this round's
  check of the ledger moved there.

### What needs your decision
1. **Pushing.** The round is 73 commits on top of the public commit, in the local repository only.
   Until they are pushed, the public version has the faults of points 11 and 13. A push to the public
   repository needs your word.
2. **Your real install.** It runs the kit of the fifth installer run. A sixth run would bring this round:
   the guard's new questions (an edit there that names the sealed folder would ask), the snapshot's
   handling of wildcard patterns, links and credential-named files, the case rule, and a source hash that
   changes once if that project tracks agent files. It needs your word, as each run before it did.
3. **Ports for Antigravity and Gemini CLI.** Neither agent is installed here, and installing one is your
   call. I would build each from the vendor's documentation and test it live once it is installed.
4. **The MCP servers the review proposes.** Each is an install with your permissions; say which, if any.
5. **Cloud drivers beyond `ssh` and Hugging Face Jobs.** Each needs an account and paid runs to verify.
6. **A container as the box for training and evaluation.** It needs Docker Desktop running on this machine.
7. **A second pilot or a campaign with a real agent.** The open question since round 4, now with the repair
   turn and the compile check to try as well.
8. **What to build next.** My order: a second reviewer's look at the sixteen fix commits, on Linux this time, the
   guard walk that skips folders, the process namespace with the heartbeat fix, then the unfinished Adopt
   rows that earlier
   rounds ranked. Of round 4's order this round built the repair attempt after a crash and lifted the
   guard's file bound for a folder sealed as a whole; a job object on Windows, a minimum agent version, the
   readiness report and a checkpoint helper stand as they were.

## 1. What changed and why

### The four known gaps
**Unattended research loop** (`scripts/nnloop.py`, `references/loop.md`, `tests/test_loop.py`). Off until the
project's config gets a `loop` section and a person runs `nnloop.py start --campaign NAME --agent
claude|codex|cursor` with at least one limit.
- Limits: runs, hours, GPU-hours, money, agent tokens. It refuses to start without one and refuses a limit it
  cannot measure (money: Claude Code only; tokens: Claude Code or Codex; GPU-hours: needs `nvidia-smi`). It stops at
  the first limit reached. Limits are checked between steps; the wall-clock limit also cuts off a run or a session
  in flight, the others can overshoot by the step under way.
- Harness code decides keep or revert. It runs the project's frozen evaluator itself, in its own process, on what
  each run saved. A change is kept only if its mean over the seed panel beats the best so far by more than a
  margin above run-to-run noise. In the live runs of section 2 that noise came from the baseline panel alone;
  since then it is pooled over every seed panel of the campaign ("Trustworthy decisions" below). The number a
  training script reports about itself decides nothing.
- What the agent can see: sealed paths are absent from its worktree and the guard denies them. In the benchmark the
  scoring split is sealed too; in another project the agent can read the scoring split unless the config seals it
  (possible when training does not read it), and the loop says so at start. The loop's own steps never use the
  sealed test set. A Claude Code worker has no shell; a Codex worker has one and is held from sealed data only by
  the guard and the transcript scan.
- Every iteration: a fresh git worktree, checksums of evaluator, data and config, a saved diff and a transcript
  scan for every keep, a hash-chained ledger. On Linux and WSL2 each training run is wrapped in bubblewrap (no
  network, project read-only, sealed data hidden). On Windows and macOS those three are instructions plus a scan of
  the change, not mechanics; the README table says so.
- Nobody can be asked: the agent starts with the narrowest unattended permissions (Claude Code: `-p
  --permission-mode dontAsk` with an explicit tool list and no shell; approvals are never bypassed), and the
  loop's own keep, discard and stop steps are harness code, not agent commands. Cursor's terminal agent edits
  unattended only with `--force`, so the loop takes it only with `--in-container`.
- It stops and writes its state on a limit, repeated failure, a hang, a rate limit, a usage cap or a refusal.
- From Karpathy's autoresearch the kit takes the pattern (fixed budget, frozen data and evaluator, keep or revert
  in git) and not the code: there the agent reads the score its own script prints, runs single seeds and is told
  never to stop. The ports and plugins are ledger rows (notes `loop-autoresearch`, `sweep-auto-research`).

**Research scouting** (`references/scouting.md`, SKILL.md gate 4.0, the loop's first session). Before choosing
hypotheses the agent writes dated, cited notes; findings enter as hypotheses. The step reads and writes notes only,
treats page content as data, and is skipped (and said to be skipped) without web tools. Every reference in the kit
now carries `Checked:` and `Refresh:` lines; a test fails if one is missing.

**Remote and rented GPUs** (`scripts/nnremote.py`, `references/remote.md`, `expctl resume`,
`RunLog.resume_from`, `tests/test_remote.py`). Two target types: `ssh` (any machine you can reach, rented ones
included) and `hfjobs` (Hugging Face Jobs: the route that rents GPUs over the internet).
- A remote run has a local mirror run directory, so `status`, `watch`, `curve` and `stop` work as for a local run.
- Money: a paid target needs `--hours` and a spending cap that still covers `hours x price` before anything
  starts; the amount is reserved in a ledger whose edits the guard asks about, so reservations never pass the cap.
  A run cannot outlast its reserved hours: the run gets that deadline, a Hugging Face Job gets it as the
  provider's timeout, and the controller stops a run that passes it. A plain ssh target has no provider-side stop:
  `remote.md` says so.
- What travels: the source files git tracks or would track, and only the environment variables and git-ignored
  files you name. The launching environment, other git-ignored files, sealed paths and files with credential-like
  names do not (the last unless you name them). Credentials stay in the provider's own store or in environment
  variables.
- After a preemption the run is resumed from its last checkpoint (`--retries`). At the end the module removes what
  the run created on the remote side and nothing else, after logs and checkpoints are mirrored.
- Other providers were judged, not built: SkyPilot, dstack, Vast.ai, Lambda are Hold; Modal and Runpod Assess; a
  Slurm adapter Trial.

**Codex and Cursor ports** (`install.py --agents claude|codex|cursor|all`, `nn_guard.py --agent`,
`tests/test_ports.py`). One guard with a thin input and answer adapter per agent. Codex gets `.codex/hooks.json`,
two agent files and a pointer skill; Cursor gets `.cursor/hooks.json` (with `failClosed`), two read-only agent
files and deny rules for the terminal agent. With either, the rules block lives in `AGENTS.md` and `CLAUDE.md`
imports it. A Codex or Cursor hook cannot ask a person, so every "ask" is a refusal there. The README table
"What works where" says per agent and per platform what is enforced, instruction-only or missing.

### Trustworthy decisions (built after the comparison)
Built on 11 November, after the second look at the open rows (`scout/draft/second-look.md`, group A) and on your
go-ahead. Standard library only. Tested with a stand-in agent and stand-in training runs, and run once with a real
agent and real training, on 12 November (section 2, "Campaign with 'Trustworthy decisions'").
- **Noise pooled over all seed panels** (`nnloop.py`; `references/loop.md`, "The keep rule"). The earlier rule took
  the deviation from the baseline runs alone, three in the benchmark, and multiplied it by a fixed factor. The
  margin is now a one-sided t-test: the variance within seed panels, pooled over the baseline and every change
  that ran on all seeds, the candidate's own panel included, with the multiplier that belongs to the pooled
  degrees of freedom. Simulated share of changes kept (normal noise, 40,000 trials per cell, three seeds):

  | True gain, in run-to-run deviations | 0 | 0.5 | 1 | 1.5 | 2 | 3 |
  |---|---|---|---|---|---|---|
  | Earlier rule | 7.9 % | 17.8 % | 33.1 % | 50.9 % | 68.1 % | 90.7 % |
  | Now, at the first change | 2.4 % | 6.2 % | 14.3 % | 27.6 % | 44.1 % | 76.1 % |
  | Now, after three earlier panels | 2.5 % | 7.5 % | 17.9 % | 34.7 % | 54.4 % | 85.5 % |
  | Now, after eight earlier panels | 2.4 % | 7.7 % | 19.5 % | 36.8 % | 57.6 % | 87.7 % |

  A change that does nothing is now kept as rarely as the margin promises. Real gains are kept less often, most
  of all while a campaign is young: that is what three seeds can show, and the earlier rule's higher figures
  include its false keeps. More seeds buy power at the cost of runs.
- **Evaluator self-test**, after the baseline runs and before the first agent session, so that a broken evaluator
  costs no agent usage. Three checks with a known answer: the baseline seeds do not all score exactly the same
  (a task that really is deterministic sets `loop.min_margin`), the evaluator gives a run the score it gave it
  before, and it gives no score to an empty folder. A failure stops the campaign with the reason. Later, a seed
  panel whose runs all score exactly the same is invalid and stays out of the pooled noise. Not built: checks
  with a tampered or cheating run.
- **A session may decline.** It writes `{"no_change": "why"}` instead of a proposal; the iteration is recorded as
  `declined`, costs no run and is no failure, and two in a row end the campaign as "search exhausted" (exit code
  0). Reason: an agent with no accepted way to report "nothing" tends to game the score (arXiv 2510.20270 v1, from
  the note `loop-autoresearch`: an abort option cut cheating from 54 % to 9 %).
- **Confirmation on fresh seeds** when a campaign ends with something kept (`references/loop.md`, "The
  confirmation"). The harness draws seeds at that moment, trains the start commit and the kept commit on them
  and records `confirmed`, `unclear` or `not_reproduced`, with both means, the seeds and how many changes the
  campaign trained and kept, in the ledger, the journal and `nnloop status`. Nothing is reverted. Once a change
  is kept, the loop holds back two seed panels of runs for it from the limits (section 6, "Other"). With three
  seeds its power is as limited as the keep rule's: a real gain of two deviations is confirmed in about half of
  the cases, so `unclear` means "run more seeds", not "no effect". It uses the loop's validation split, not the
  test set.
- **Single-use final evaluation** (`expctl.py final-eval`; `references/validity.md`, section 5). `expctl` runs the
  configured final-evaluation command itself. Before the command starts it appends a row to a hash-chained
  receipt (`.claude/state/final-eval/receipt.jsonl`: use number, commit, source hash, arguments), and afterwards
  a second row (exit code, SHA-256 and tail of the output); every use also gets a journal entry. A second use is
  refused unless `--again "reason"` is given, and the reason is recorded. A use counts even if the command fails.
  The guard asks before every use and refuses the configured command typed directly (section 6, "Guard"). The
  receipt is a record, not a seal: deleting its folder resets the count (the guard asks before a command or an
  edit touches it, and the journal entries remain). The configured command must be one program call without
  shell syntax; `NAME=value` pairs before it are allowed.

### The rest
- **Native Windows is a working platform** (`51a37a7`). At baseline two of three test files aborted there. Now:
  snapshots use junctions and hard links without the symlink privilege, `expctl stop` works through `stop.json`,
  the installer verifies the interpreter and writes it into every installed file that calls one (the `python3`
  Store stub no longer matters), brief file locks are retried.
- **References**: fifteen dated references. New: data, evaluation, llm, operations, optimization, scouting, loop,
  remote. Rewritten: fine-tuning, hpo, performance, stack. They were written by subagents from the research notes;
  the sources were not opened a second time.
- **Benchmark and measurement**: `benchmarks/charlm` (a character-level language model, MIT-licensed text shipped
  with the kit, trains in minutes), `benchmarks/new_project.py` (creates a ready project), `benchmarks/pilot.py`
  (three arms, at least two runs each).
- **Prompts and agent files**: kick-off prompt slimmed, one rules block, explicit model and effort per subagent
  (reviewer: Opus, high; analyst: Sonnet, medium), calibrated reviewer verdicts, agent-neutral wording.
- **Installer**: manifest with hashes, backups, `--uninstall`, MCP servers off unless `--mcp`.

## 2. The real loop runs and the pilot
Four campaigns of the loop on the benchmark `benchmarks/charlm`, all on native Windows 11 with the RTX 5090: two
with headless sessions, which are also the upgraded-kit arm of the pilot; a third headless one on 12 November,
the first with "Trustworthy decisions"; and an earlier one through a bridge. The loop's score is the loss on its
validation split (`data/loopval.txt`, sealed from the agent), lower is better. The pilot and its repeat follow at
the end.

### Headless campaigns (11 November, after the sign-in)
The first is the pilot's arm-run `new-1`. Kit at commit `d011172`, campaign
`pilot`, limit `--max-runs 12`. Agent: headless sessions of the Claude Code CLI 2.1.322 (`claude -p`), model
`claude-sonnet-5-5`, signed in with the subscription (no API key). Each session ran in permission mode `dontAsk`
with an explicit tool list (worker: Read, Glob, Grep, Edit, Write; scout: the same without Edit, plus WebSearch and
WebFetch), in restricted mode with the project's settings file, so with the kit's guard hook and without your
personal settings, plugins or MCP servers. Approvals were not bypassed. The guard's record has a line for each of
the 35 tool calls of the six sessions and no refusal. One of the 35 lines was cut to a fragment: a fault in how
the guard appended to its log on Windows, found through this run and fixed since (section 6, "Guard").

The first session did the scouting step: three searches and four pages read, 81 seconds, notes in
`experiments/scouting/2026-11-11-pilot.md` with six findings, each with source and date, and seven hypotheses. It
ran and installed nothing, and its notes say that no page tried to direct it. Then five worker sessions proposed
one change each (14 to 25 seconds per session). The harness trained and scored every change itself.

Baseline, three seeds: mean 1.68190. Keep margin: 0.00890.

| # | Change (hypothesis from the scouting notes) | Score | Decision | Why |
|---|---|---|---|---|
| 1 | H1: learning-rate warmup and cosine decay by elapsed time, peak 1.5e-3, AdamW betas (0.9, 0.95), weight decay 0.1 | 1.72298 | discard | first seed not better than the best so far |
| 2 | H7: moving average of the weights (EMA, decay 0.995) for the saved model | 1.67240, 1.66659, 1.66888 | **keep** | better by 0.01261, more than the margin |
| 3 | H4: dropout 0.1 to 0 | 1.68904 | discard | first seed not better than the best so far |
| 4 | H5: rotary position embeddings instead of learned positions | 1.68336 | discard | first seed not better than the best so far |
| 5 | H6: width 192 to 384 with 6 heads | 1.66995, 1.66175, 1.67255 | not kept | better by 0.00121, inside the margin |

Kept: change 2, which comes from the scouting notes (finding F5 and hypothesis H7, source: the modded-nanogpt
README, read on 11 November). H1 and H5 also come from pages the scout read; the notes mark H4 and H6 as taken
from the model's memory. The campaign stopped by itself at its limit ("runs: 12 of 12 used, and the next step
needs up to 3"): 12 training runs, 653 s elapsed, 408 s of GPU time, 6 sessions, 303,806 agent tokens, 0.51 USD
of notional cost as Claude Code reports it (subscription usage, nothing billed per use).

The second campaign is the pilot's arm-run `new-2`: same settings, kit at commit `917a5f7` (it differs from the
first in the paid-usage stop, the guard's log lock and the pilot script, not in what the agent sees or in the
keep rule). Scouting took 41 seconds: two searches, no page read, six findings, eight hypotheses, two of them
with a source on the web (H1 and H7) and the rest marked as the model's memory. Its notes record that a search result ended
with a line telling the agent to give its sources as links, and that it did not take that as an instruction.
Baseline mean 1.68453, keep margin 0.00523.

| # | Change | Score | Decision | Why |
|---|---|---|---|---|
| 1 | H1: dropout 0, warmup, peak learning rate 2e-3, linear decay, gradient clipping | 2.49430 | discard | first seed not better than the best so far |
| 2 | H2: bfloat16 autocast, TF32, fused AdamW | 1.69444 | discard | first seed not better than the best so far |
| 3 | H5: 6 layers, width 256 | 1.68719 | discard | first seed not better than the best so far |
| 4 | the worker's own: learning rate 1e-3 with warmup and linear decay over the last 60 % | 1.69994 | discard | first seed not better than the best so far |
| 5 | the worker's own: dropout 0.2, weight decay 0.1 on matrices | 1.68838 | discard | first seed not better than the best so far |
| 6 | the worker's own: moving average of the weights (EMA, decay 0.998) | 1.67776, 1.67272, 1.67471 | **keep** | better by 0.00947, more than the margin |

It stopped at its limit ("runs: 11 of 12 used, and the next step needs up to 3"): 11 training runs, 582 s
elapsed, 375 s of GPU time, 7 sessions, 282,741 agent tokens, 0.45 USD of notional cost. The guard's record has
29 lines for 29 tool calls, all intact, no refusal.

On held-out data: the final `train.py` of each campaign, retrained on three other seeds, scores 1.7454 and 1.7481
on the test split (standard deviation over the seeds 0.0144 and 0.0145). The shipped script scores 1.7557 there
(mean of three scorings). So the kept change carries over to the test split by about 0.009, which is more than
the scoring repeats differ (0.004) and less than the seed-to-seed standard deviation.

### Campaign with "Trustworthy decisions" (12 November)
The first campaign with a real agent since the changes of section 1, "Trustworthy decisions". Kit at commit
`daa8cfc`, a practice project from `benchmarks/new_project.py`, campaign `pkga`, limits `--max-runs 40 --max-hours
1.5`, native Windows. Agent and session settings as in the two campaigns above (headless Claude Code CLI 2.1.322,
`claude-sonnet-5-5`, permission mode `dontAsk`, an explicit tool list, no MCP servers, approvals not bypassed).
The guard's records have 55 lines for the 55 tool calls of the 14 sessions and no refusal.

Before any session the harness trained the baseline on three seeds (mean 1.68093) and tested the evaluator: the
same run scored twice gave the same number. The scouting session took 68 seconds (three searches, two pages read)
and wrote eight findings and eight hypotheses, each marked as read from a page or as the model's memory. Its
notes say that no page tried to direct it, and that the search tool appends a reminder to list sources, which it
did not take as a task instruction.

| # | Change (source) | Score | Decision | Why |
|---|---|---|---|---|
| 1 | H1: warmup, peak learning rate 1.5e-3, linear decay by elapsed time | 1.72042 | discard | first seed not better than the best so far |
| 2 | H3: bfloat16 autocast in training | 1.69545 | discard | first seed not better than the best so far |
| 3 | H2: dropout 0 | 1.71875 | discard | first seed not better than the best so far |
| 4 | H8: moving average of the weights (EMA, decay 0.998 with warmup) for the saved model | mean 1.67408 | **keep** | better by 0.00685, margin 0.00500 |
| 5 | H6: rotary positions, QK-norm, ReLU² in the MLP | 1.68003 | discard | first seed not better than the best so far |
| 6 | the worker's own: constant learning rate 8e-4 after 100 warmup steps | 1.69796 | discard | first seed not better than the best so far |
| 7 | H4: validation loss every 1,500 steps instead of 250 | 1.67640 | discard | first seed not better than the best so far |
| 8 | H5: Muon for the blocks' weight matrices, AdamW for the rest | 2.43861 | discard | first seed not better than the best so far |
| 9 | the worker's own: GPT-2 style initialisation (deviation 0.02, residual projections scaled by depth) | mean 1.65416 | **keep** | better by 0.01993, margin 0.01089 |
| 10 | the worker's own: learning rate 6e-4 after 100 warmup steps | 1.67624 | discard | first seed not better than the best so far |
| 11 | the worker's own: learning rate falling linearly from 3e-4 to 3e-5 by elapsed time | mean 1.65799 | not kept | worse by 0.00384 on the three seeds |
| 12 | none: the session declined | | declined | "I found no change I expect to clear the ~0.0136 margin" |
| 13 | none: the session declined | | declined | the same reason; two in a row end the campaign |

Seven of the eleven trained changes come from the scouting notes. One of them was kept: H8, which the notes mark
as the model's memory, not as read from a page. The campaign ended itself as "search exhausted" and then ran the
confirmation: the starting commit and the kept commit, each trained on three seeds that no earlier step had used.

| | Seed 7267 | Seed 47292 | Seed 49748 | Mean |
|---|---|---|---|---|
| Starting commit | 1.70102 | 1.69845 | 1.68500 | 1.69482 |
| Kept commit (changes 4 and 9) | 1.64260 | 1.64308 | 1.63636 | 1.64068 |

A gain of 0.05414 against a margin of 0.01289: **confirmed**. Used in all: 26 of the 40 training runs (3
baseline, 17 for the eleven changes, 6 for the confirmation), 21 of the 90 minutes (1,258 s), 861 s of GPU time,
14 sessions, 610,061 agent tokens, 0.92 USD of notional cost (subscription usage, nothing billed per use).

Then the practice project's final evaluation, through `expctl final-eval`. Use 1 scored the kept commit's model
for seed 7267 on the test split: 1.71007. A second call without `--again` was refused with exit code 2 and the
text that a further look at the test split is the user's decision. Use 2, with `--again` and a reason, scored the
starting commit's model for the same seed: 1.76678. The receipt has four rows (start and end of each use, with
the arguments, the reason, a hash of the code and a hash of the output), each carrying the hash of the row
before; the journal has an entry per use; `expctl selftest` passes afterwards. With one model per side the
difference on the test split (0.057) is an illustration, not a result. It has the size of the validation gain
for that seed (0.058).

What this run shows, and what it does not:
- Every new part ran in a real campaign: the pooled keep rule, the evaluator self-test, a session declining, the
  end by two declines, the confirmation, and the single-use final evaluation with its refusal.
- It is one campaign, on one task, with one agent, on native Windows.
- The first keep rests on a noise estimate that proved too small. The three baseline runs lay within 0.0012 of
  one another (standard deviation), so the margin was the configured minimum, 0.005, and change 4 passed with
  0.00685. Later seed panels spread more (pooled deviation 0.0073 at the end of the search; the starting commit on
  the fresh seeds 0.0086). Under the margins of 0.010 to 0.014 that followed, change 4 would not have been kept.
  The confirmation compares the kept commit as a whole with the start, so it does not show what change 4 adds by
  itself. (A change of the same kind was kept in both pilot campaigns, with gains of 0.013 and 0.009.)
- The gain measured during the search (0.027, on seeds 1 to 3) and the gain in the confirmation (0.054, on the
  fresh seeds) differ by about three standard errors under the pooled deviation. The training script's own
  validation loss, on a split the harness does not decide on, shows the same gain in both phases (0.055 and
  0.057). So on the loop's split the run-to-run noise was less regular than the keep rule's simulation assumed
  (normal, one deviation for every panel). I did not look for the cause.
- What ended the search was the margin, not the budget: both declining sessions wrote that none of their
  remaining ideas would clear about 0.0136, with 14 runs and 69 minutes unused.

### Earlier run through a bridge (11 November, before the sign-in)
Kit at commit `f3fabd6`, campaign `live`, limit
`--max-runs 18`. Agent: subagents of the session that did this work (Claude Code desktop app, Sonnet model; the
app does not tell a session its agent version, the CLI beside it was 2.1.303), connected through a bridge script,
because no headless CLI was signed in. So this was not a headless session. Every file the agent wanted to write was
shown to the project's guard hook first; its reads and the "run no code" rule were instructions only; its usage
was not measured. The first session did the scouting step (seven searches, twelve sources, hypotheses H1 to H8 in
`experiments/scouting/2026-11-11-live.md`). I stopped the campaign by hand after five iterations to bound usage:
10 of 18 runs, 1,918 s elapsed, 340 s of GPU time, 7 sessions, ledger chain intact.

Baseline, three seeds: 1.69258, 1.67640, 1.68397 (mean 1.68432). Keep margin: 0.01322.

| # | Change (hypothesis from the scouting notes) | Score | Decision | Why |
|---|---|---|---|---|
| 1 | H1: dropout 0, learning rate 1e-3 with warmup and linear decay, gradient clipping | 1.92570 | discard | worse than baseline |
| 2 | H2: bfloat16 autocast, TF32, fused AdamW | 1.69147, 1.68105, 1.67987 | not kept | better by 0.00019, inside the margin |
| 3 | H4: RoPE and RMSNorm instead of learned positions and LayerNorm | 1.69981 | discard | worse than baseline |
| 4 | H5: batch 128 with learning rate 6e-4 | 1.70199 | discard | worse than baseline |
| 5 | H3: AdamW betas (0.9, 0.95), weight decay 0.1 on matrices only | 1.69801 | discard | worse than baseline |

Kept: nothing. Best score at the end equals the start score.

### Pilot comparison (11 November)
A pilot, not a study: one task, one machine, two runs per arm.

- **Arms.** The same agent three ways: with the upgraded kit (its loop, `nnloop start --max-runs 12`), with the
  23 October kit (commit `5ea9659`, installed by its own installer), and with no kit. The old-kit and no-kit arms
  are one headless session each, with the task text and the same budget in the prompt; the old-kit prompt adds
  one line: the kit is installed, use it as its instructions say.
- **Agent.** Headless Claude Code CLI 2.1.322 (`claude -p`), model `claude-sonnet-5-5`, native Windows 11, signed
  in with the subscription. Permission mode `dontAsk` with tool lists in every session; approvals never bypassed.
- **Budget, the same for every arm:** at most 12 training runs of 30 seconds each. I chose it to keep one
  arm-run near ten minutes. In the loop arm the three baseline seeds count against the 12, and the harness
  enforces the limit; a single session is told the limit and has 40 minutes, which none came near.
- **Score.** The final `train.py` of each arm-run is retrained on three seeds no arm used (101, 102, 103) in a
  copy of the project without the held-out files, and the kit's `evaluate.py` scores each model on the test split,
  which no arm's agent read. Lower is better. The arms took turns (new, old, none, then again).

| Arm | Run 1 | Run 2 | Mean | Spread between the two runs | Training runs used, of 12 | Time |
|---|---|---|---|---|---|---|
| Upgraded kit | 1.7454 (0.0144) | 1.7481 (0.0145) | 1.7468 | 0.0028 | 12 and 11 | 653 s and 582 s |
| 23 October kit | 1.7567 (0.0156) | 1.7520 (0.0169) | 1.7544 | 0.0047 | 6 and 7 | 450 s and 477 s |
| No kit | 1.7764 (0.0198) | 1.7362 (0.0053) | 1.7563 | 0.0403 | 4 and 6 | 163 s and 237 s |
| `train.py` as shipped, no agent | 1.7532, 1.7570, 1.7569 | | 1.7557 | 0.0038 | | |

In brackets: standard deviation over the three scoring seeds. The last row is the unchanged script scored three
times on the same seeds; training stops by the clock, so a seed does not repeat exactly, and 0.004 is what the
scoring itself varies.

What it shows, and what it does not:
- The upgraded kit is ahead of the old kit by 0.0076, and both of its runs beat both of the old kit's. That is
  more than the spread inside either arm, but with two runs per arm it would not pass a significance test (p
  between 0.1 and 0.15, depending on the test), and the no-kit arm shows how far two sessions can lie apart:
  0.040. I do not claim the difference.
- Only the upgraded kit improved on the unchanged script in both runs (by 0.010 and 0.008). The old kit's
  results equal it within the scoring noise. The no-kit arm has the worst and the best single result.
- The old-kit and no-kit sessions each reported a gain of 0.04 to 0.06 on the development split, which the
  training script prints. On the test split none of that is left in three of the four sessions. The loop judged
  its changes on its own validation split, with three seeds and a margin, and kept less (0.009 and 0.013), most
  of which is still there on the test split. This fits what the loop is for; four sessions do not prove it.
- The old-kit and no-kit sessions stopped by themselves after 4 to 7 of their 12 runs. The loop used its budget.
  So the arms had the same budget but did not use the same amount of it.

What limits the comparison:
- The first try of `old-1` and `none-1` is void. My pilot script did not tell these sessions that their
  permission rule allows Python commands only; each opened with a command that also called another program, was
  refused, took that for the whole shell and stopped without training (13 and 9 seconds). I fixed the prompt,
  checked with one small session that Python commands run, and repeated both. The void results are in
  `void.json` beside `pilot.json` and are not in the table, except as two of the three scorings of the unchanged
  script.
- Even so, the shell rule cost these arms some calls: three were refused by the permission rule in the old-kit
  sessions and one in each no-kit session. Each time the session put the command differently and went on.
- The 23 October kit ran as its installer leaves it on Windows. Its guard refused three shell commands in the
  two old-kit sessions ("may modify harness guardrail files": an ask that nobody could answer), which the
  sessions worked around.
- The no-kit arm has no guard, so only its prompt kept a session from the held-out files. No tool call in the
  old-kit and no-kit transcripts names them.
- The model was Sonnet, to bound usage. A stronger model may behave differently in every arm.
- The two upgraded-kit runs used different commits of the kit (see above).

Usage: the six sessions and campaigns drew about 1.9 million tokens from the subscription (most of them cached
reads), 1.49 USD at Claude Code's notional prices; the void tries and the check session about 90,000 tokens more.
No session reported usage billed per use. Everything is kept in `%TEMP%\nnkit-upgrade\pilot1` (`pilot.json`,
projects, transcripts). To repeat it: `python benchmarks/pilot.py DIR --old-kit 5ea9659`.

### Pilot repeated with five runs per arm (11 November)
The same comparison again with five runs per arm, to find out whether the upgraded kit's edge in the first pilot
(0.0076) is more than the noise. Everything is as above: task, agent, budget, scoring seeds, test split. It was
started with `python benchmarks/pilot.py DIR --old-kit 5ea9659 --repeats 5` and ran from 19:27 to 21:26 on 11
November, on native Windows 11 with the headless Claude Code CLI 2.1.322 and `claude-sonnet-5-5`; the arms took turns
five times. The kit's files did not change while it ran (two commits were made meanwhile, `2612f4c` and `358100e`,
and both touch only `docs/upgrade`), so all five upgraded-kit runs used the kit of commit `b7e3046`. `pilot.py` was
not changed. All 15 arm-runs are valid: every session trained, none ended in an error or a time-out, none reported
usage billed per use, and none is void. The first pilot's runs are not part of these numbers. "Trustworthy
decisions" (section 1) was built after this comparison, so that kit is not what was measured here; and since
`pilot.py` now turns the loop's confirmation off, a repeat would not measure the confirmation either.

**Result: the upgraded kit does not beat the 23 October kit by more than the noise.** Test loss on the test split,
lower is better; in brackets the standard deviation over the three scoring seeds:

| Arm | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 | Mean | SD across the five runs |
|---|---|---|---|---|---|---|---|
| Upgraded kit | 1.7448 (0.0146) | 1.7575 (0.0169) | 1.7497 (0.0128) | 1.7527 (0.0188) | 1.7459 (0.0142) | 1.7501 | 0.0052 |
| 23 October kit | 1.7733 (0.0146) | 1.7430 (0.0038) | 1.7462 (0.0169) | 1.7536 (0.0222) | 1.7562 (0.0072) | 1.7545 | 0.0118 |
| No kit | 1.7584 (0.0156) | 1.7493 (0.0057) | 1.7281 (0.0097) | 1.7464 (0.0242) | 1.7303 (0.0084) | 1.7425 | 0.0130 |
| `train.py` as shipped, no agent | 1.7601 (0.0152), 1.7575, 1.7527 | | | | | 1.7568 | 0.0037 |

The last row is the unchanged script scored three times on the same seeds: by the script's own reference scoring and
as the final `train.py` of `new-2` and `new-4`, the two upgraded-kit runs that kept nothing (their file is identical
to the shipped one). Training stops by the clock, so a seed does not repeat exactly; 0.004 is what the scoring itself
varies.

| Arm | Training runs used, of 12 | Time per arm-run, mean (range) | Tokens per arm-run, mean (range) |
|---|---|---|---|
| Upgraded kit | 10, 10, 12, 10, 12 | 545 s (499 to 592) | 287,000 (255,000 to 347,000) |
| 23 October kit | 3, 5, 6, 7, 6 | 337 s (204 to 425) | 382,000 (138,000 to 593,000) |
| No kit | 6, 6, 5, 4, 6 | 210 s (156 to 238) | 152,000 (94,000 to 192,000) |

The 15 arm-runs drew 4.1 million tokens (1.43 million for the upgraded kit, 1.91 million for the old kit, 0.76
million for no kit; input, output and cached tokens together), 3.51 USD at Claude Code's notional prices, in two
hours.

The edge of one arm over another is the other's mean loss minus this one's, so a positive edge means the first arm is
better. The 95 % interval is Welch's t interval for a difference of two means. The permutation test takes the
difference of means over all 252 ways to split the ten run means into five and five; Mann-Whitney is the exact rank
test; both are two-sided. Everything is computed from `pilot.json`.

| Comparison | Edge | 95 % interval | Permutation test, p | Mann-Whitney, p |
|---|---|---|---|---|
| Upgraded kit over 23 October kit | +0.0044 | -0.0101 to +0.0188 | 0.54 | 0.69 |
| 23 October kit over no kit | -0.0120 | -0.0301 to +0.0061 | 0.18 | 0.42 |
| Upgraded kit over no kit | -0.0076 | -0.0235 to +0.0082 | 0.29 | 0.55 |

The first two rows are the comparisons that were asked for, the third is a by-product, and nothing is adjusted for the
number of comparisons (no p is near 0.05). I fixed the criterion before the first arm-run's result was in (it is in the
docstring of `analyze.py`, written at 19:30; the first result was recorded at about 19:39): the upgraded kit counts as
ahead of the old one by more than the noise only if the permutation test gives p below 0.05 and the interval excludes
zero. Neither holds.

What it shows, and what it does not:
- The upgraded kit's mean is 0.0044 (0.25 %) below the old kit's, less than the standard deviation of either arm's
  five runs (0.0052 and 0.0118). The interval runs from -0.010 to +0.019, p is 0.54, and 15 of the 25 pairs of one
  upgraded-kit run and one old-kit run favour the upgraded kit. The first pilot's edge of 0.0076 lies inside that
  interval: it did not hold up as more than noise.
- Five against five finds only large differences. With the pooled standard deviation of 0.009 it finds a true edge of
  about 0.018 (1.0 %) with 80 % power, and it would have found the first pilot's 0.0076 in about one case in five
  (power 0.21). So "not established" is not "equal": the data fit an edge of up to 0.019 for the upgraded kit, none,
  and a deficit of up to 0.010. To find 0.0076 would take about 24 runs per arm, to find 0.0044 about 69 (from this
  pilot's spread, which five runs estimate poorly).
- Neither kit is shown to beat running the agent with no kit. The old kit's mean is 0.0120 behind it (p = 0.18), the
  upgraded kit's 0.0076 (p = 0.29), and both intervals include zero. The no-kit arm has the lowest mean and the two
  best results of the fifteen (1.7281 and 1.7303). In the first pilot its mean was the highest (1.7563): an arm's mean
  moved by up to 0.014 between the two pilots (no kit 0.0138, upgraded kit 0.0033, old kit 0.0001), which two runs per
  arm could not show.
- The upgraded kit's five results lie closer together (standard deviation 0.0052, against 0.0118 and 0.0130), about
  as close as scoring the unchanged script (0.0037). Three of its five campaigns kept one change (a moving average of
  the weights in `new-1` and `new-5`, a warmup with cosine decay in `new-3`; all from the scouting notes, each gaining
  0.008 to 0.013 on the loop's validation split) and two kept nothing, so their final `train.py` is the shipped one. The
  three campaigns with a kept change scored 0.010 below the unchanged script (1.7468 against 1.7568), as in the first
  pilot. That is description: five runs cannot establish a difference in spread, nor three campaigns what a kept
  change is worth.
- The old-kit and no-kit sessions reported gains of 0.03 to 0.06 on the development split (one seed; `old-1` gave no
  before figure). On the test split the old-kit arm's mean is 0.0023 and the no-kit arm's 0.0143 below the unchanged
  script, with a wide spread: the worst of the fifteen (1.7733) is `old-1`, whose session says it never measured the
  original baseline because its attempt to run it was blocked.

What limits the comparison:
- One task, one machine, one model: the character-level language model of `benchmarks/charlm` with runs of 30 seconds,
  Windows 11 with an RTX 5090, headless Claude Code with Sonnet. A harder task, a longer budget or a stronger model may
  give another answer in every arm. The final test loss is also only part of what the kit is for: it says nothing about
  the protection of sealed data, except that no tool call in the 15 transcripts names the held-out files (a search of
  the tool inputs for their names; in the no-kit arm only the prompt kept a session away from them).
- Five runs per arm, as above. The Welch interval assumes run means that are roughly normal, which five values cannot
  show; the two tests do not.
- The arms differ in more than the kit. The upgraded kit is the kit's own loop (scouting, several short sessions, its
  own validation split and keep rule), the other two are one session each. The budget was the same, its use was not:
  the loop used 10 to 12 of the 12 runs, the old-kit sessions 3 to 7 and the no-kit sessions 4 to 6, and stopped by
  themselves.
- The 23 October kit ran as its installer leaves it on Windows. In four of the five old-kit sessions the guard's "may
  modify harness guardrail files" ask, which nobody could answer, appears in the transcript, and 2 to 4 tool calls per
  old-kit session were refused in all, against one per no-kit session. That cost the old-kit arm some calls; whether it
  changed its result I cannot tell.

Everything is kept in `%TEMP%\nnkit-upgrade\pilot2`: `pilot.json`, the projects and transcripts, and the analysis
scripts `analyze.py` and `power.py` with their output `pilot2-stats.json`. The first pilot is untouched in `pilot1`.
The same command again continues after the last recorded arm-run.

## 3. What was verified, and how

### By running it here
- **Tests.** All seven test files, 11 November, on commit `b1a3679`, which holds all code of "Trustworthy
  decisions" (section 1). The commits after it change documentation only; all seven files were run once more on
  `f0b4a05`, the last commit that changes a file a test reads, with each platform's default interpreter, and gave
  the same counts. So did a further run on 12 November on `daa8cfc`, after which only documents changed: 509
  passed checks in WSL and 502 on native Windows. The figures are passed checks; no check failed in these runs.

  | Test file | WSL, default 3.12 | WSL, clean 3.8 | WSL, clean 3.12 | Windows, default 3.11 | Windows, clean 3.11 | Windows, clean 3.8 |
  |---|---|---|---|---|---|---|
  | `test_runlog_units.py` | 16 | 16 | 16 | 16 | 16 | 16 |
  | `test_kit.py` | 137 | 137 | 137 | 133 | 133 | 133 |
  | `test_review_fixes.py` | 39 | 39 | 39 | 37 | 37 | 37 |
  | `test_ports.py` | 105 | 104 | 105 | 106 | 106 | 105 |
  | `test_loop.py` | 122 | 122 | 122 | 120 | 120 | 120 |
  | `test_remote.py` | 67 | 67 | 67 | 67 | 67 | 67 |
  | `test_benchmarks.py` | 23 | 23 | 23 | 23 | 23 | 23 |

  Before "Trustworthy decisions" the same run, after the pilot and its fixes, gave 121, 38, 105, 107, 67 and 21
  for the last six files in WSL with the default interpreter: the difference is the new checks.

  "Default" interpreters have torch and psutil installed; "clean" ones have no third-party package, so they
  exercise the standard-library paths. Why the counts differ: Windows has no tmux (four checks of `test_kit.py`
  and two of `test_review_fixes.py` are skipped and say so) and no bubblewrap (two sandbox checks of
  `test_loop.py`); `test_ports.py` has one check that only applies on Windows (letter case) and one that needs
  Python 3.11 (it parses the Codex agent file as TOML).

  One failure on the way, and what it was: in the first full run `test_remote.py` failed once, on Windows with the
  default interpreter, in "results are mirrored" of the Hugging Face route (the other four interpreters passed).
  Reading the code showed a real fault, not only a slow machine: the copier inside a job could put the exit record
  into the bucket before the last files, and it dropped a file the store refused in its last round; the controller
  takes the exit record as "everything is here" and then deletes the job's folder in the bucket, so the last
  checkpoint or log lines could be lost. Fixed in `nnremote.py`: the exit record goes last and only in the last
  round, which is retried for up to a minute; one new unit check. I did not reproduce the failure on purpose;
  after the fix `test_remote.py` passed in all seven runs (Windows default three times, each other interpreter
  once), again in the full run after the pilot, and in the run that the table shows.
- **Pilot**: section 2. Six arm-runs with headless sessions, then fifteen in the repeat, each scored on the test
  split.
- **Loop**: the runs of section 2. The headless ones are the live check of the loop with Claude Code on native
  Windows: `claude -p` sessions in `dontAsk` mode with tool lists, the guard hook active in every session,
  scouting first, changes kept, a clean stop at the run limit or by two declining sessions. The campaign of 12
  November is the live check of "Trustworthy decisions" (section 1): the pooled keep rule, the self-test, the
  declining exit, the confirmation, and `expctl final-eval` with a refused second use. Not run live: any of it in
  WSL (the CLIs there are not signed in); a stop caused by a rate limit, a usage cap or paid usage (tests only);
  the sandbox around a training run (Linux only, tests only); a self-test that fails or a confirmation that does
  not hold (stand-in tests only).
- **Remote, ssh route**: one live run from Windows to WSL on 11 November (free target): launch, watch, completion,
  evaluator score 1.40218 on the dev split, teardown removed the remote run folder, ledger shows 0.0 USD. Resume
  after preemption and the spending cap ran only in tests.
- **Upgrade over a real install**: section 4.
- **Third-party stack**: on 11 November every pin of the recommended combination was installed into throwaway
  environments in WSL2 (`uv venv`, `uv pip install NAME==VERSION`) and smoke-tested. Working: uv 0.13.7 (`uv add`,
  `uv sync --locked`, `uv run --frozen`, the one-week cooldown setting); Optuna 5.0.0 (a 15-trial study with SQLite
  storage); sacreBLEU 2.6.0 (a score with its signature); Trackio 0.45.0 (a local log); lm-evaluation-harness
  0.4.13 (its own environment, the command starts, no task was run); Transformers 5.22.2 with TRL 1.17.1, PEFT
  0.21.2 and bitsandbytes 0.50.2 (install together and import); the `hf` command of huggingface_hub 2.4.0, whose
  help lists every flag and bucket command that `nnremote` calls. Failed: PyTorch 2.15.0+cu132 on the GPU ("Read
  this first", point 8), so the benchmark did not run on the pinned build. No connection was made to the two MCP
  servers. None of these tools was used for real training.

### From vendor documentation only
- Hook formats, payloads and answers of Codex and Cursor; Claude Code's headless flags and permission modes. The
  Claude Code and Cursor payloads in `tests/test_ports.py` are copied verbatim from the vendor pages read on 10
  November; the Codex one is assembled from the schema at developers.openai.com/codex/hooks.
- The Hugging Face Jobs commands (the tests use a stand-in `hf` command).
- Every technique in the references (from the research notes, with source and date).

### Unverified
- Everything in "Read this first", point 5. Also: Codex project hooks run only after trust and approval in
  `/hooks`, and Codex runs without a hook that fails to load; Claude Code older than 2.1.295 lacks the `onFailure`
  hook setting the guard relies on (Windows now has 2.1.322; WSL has 2.0.76 and 2.1.165, both older and not
  signed in).
- macOS and bare Linux (WSL2 stands in for Linux). Multi-GPU. Slurm (an ssh target to a login node is the
  documented route). Containers.
- The remote ledger is the harness's upper estimate, not the provider's bill.
- Most of the ledger's "finished" marks come from three reading subagents that compared each adopted row with the
  kit's files; they ran no tests.

## 4. Upgrade test on a copy of the real 23 October install
A partial copy (197 files, 1.2 MB: `.claude/` without worktrees, `CLAUDE.md`, `.gitignore`, `experiments/`,
`runs/`, the two scripts that use the kit) with its own `git init`; the original and its repository were only
read. Then the new `install.py --target <copy>`, dry run first, without `--python-cmd`.
- Every value of `.claude/nn-training.json` is kept. Added: five protected paths and the `python` key.
- Journal and the five run directories are byte-identical, also after `expctl selftest`; `expctl status` lists
  the same five runs in the same states.
- The kit's two hook entries in `settings.json` equal a fresh install's; the old entries are in the backup; the
  permission rules equal a fresh install's; no other key or file of other tools changed.
- The interpreter was taken from the old hook entry (a full Windows path) and written into the hooks, both agent
  files, the rules block and the config. This needed a fix found by this test: the installer used to fall back to
  plain `python`.
- The two hand-edited agent files and the edited block in `CLAUDE.md` were replaced, each named in the output and
  kept in `.claude/backups/nn-training-<timestamp>/`.
- `from runlog import RunLog` works from `.claude/skills/nn-training/scripts` with the methods the two scripts
  call; `expctl.py` at the old path runs `status` and `selftest`.
- Limit: the two training scripts were not run, because their data and sibling modules were not copied. The test
  shows that they still import the logger and that the commands still work, nothing more.
- Cosmetic: `.gitignore` gets a second "# nn-training harness" header above the one new line.

### The real install, upgraded on 11 November
On your go-ahead I ran the same command on the real install (`install.py --target <the install>`, dry run first).
It had no live run: five finished runs, the newest 17 days old.
- Changed 21 files, added 32 (21 of them are the backups in `.claude/backups/nn-training-20261111-193154/`, the
  rest the manifest, eight references and two scripts), removed none. Every file under `experiments/` and `runs/`
  is byte-identical to before.
- Config: 17 of 18 keys unchanged; `harness_paths` gained the five paths, the `python` key was added.
- `settings.json`: only `hooks` and `permissions` changed. Six allow rules and two ask rules were added, none
  removed; the two hook entries have the current form and the interpreter the install already used (a full path).
- `CLAUDE.md` is unchanged outside the kit's block; `.gitignore` got its two lines, with its CRLF line ends kept.
- Replaced and kept in the backup, as in the test: the two hand-edited agent files and the block in `CLAUDE.md`.
  The new ones name the interpreter by its full path, which is what the hand edits were for.
- Checked in place with that interpreter: `expctl selftest` passes every required check (hooks registered, the
  guard asks before a kill command, refuses input it cannot read, denies sealed data, asks before an edit of a
  frozen file; the session hook answers); `expctl status` lists the five runs (four completed, one failed);
  `runlog` imports from the skill's scripts folder; the guard's registered command, run as written, allows a
  harmless read and refuses unreadable input.
- Not done: the two training scripts were not run, and nothing was committed in that repository: the changed
  and new files are uncommitted work there. The self-test's optional item "primary metric configured" fails:
  the project's config names no metric, and did not before the upgrade.
- The self-test and my check added lines to the install's guard record (`.claude/state/guard.log`). A second
  copy of the files as they were before the upgrade is in `%TEMP%\nnkit-upgrade\real-install-before-20261111`.

### The real install, upgraded again on 12 November
On your go-ahead the kit with "Trustworthy decisions" (section 1) went onto the real install: the same command,
rehearsed first on a copy of the install's kit files in a temporary folder, then a dry run, then the run. The
install had no live run: the same five finished runs, the newest 17 days old.
- Changed nine files, each kept first in `.claude/backups/nn-training-20261112-002917/`: `expctl.py`, `nnloop.py`,
  the guard, `SKILL.md`, `references/loop.md`, `references/validity.md`, the reviewer's agent file, the config and
  the manifest. Added nothing but those nine backups, removed nothing. Every file under `experiments/` and `runs/`
  is byte-identical to before.
- Config: 18 of 19 keys unchanged; `harness_paths` gained `.claude/state/final-eval/**`, the folder of the
  receipt. `settings.json`, `CLAUDE.md` and `.gitignore` are byte-identical to before.
- The three code files and `validity.md` are byte-identical to the kit's. The other three differ from the kit's
  only in the lines that name the interpreter, which the installer writes as the install's full path.
- Checked in place: `expctl selftest` passes every required check; `expctl status` lists the five runs (four
  completed, one failed), none active; `runlog` imports from the skill's scripts folder. Through the guard's
  registered command: each of the two configured final-evaluation commands, typed directly, is refused with the
  rule that points to `expctl final-eval`; `expctl.py final-eval --which 1` gets a question for the user (the
  entries count from 1, so this install's two are `--which 1` and `--which 2`); `expctl status` passes; a
  harmless read passes; unreadable input is refused.
- No final evaluation was run, and there is no receipt yet. The receipt starts empty: it does not know of final
  evaluations run in that project before this upgrade, so the first `expctl final-eval` there counts as use 1.
- Not done, as before: the two training scripts were not run, and nothing was committed in that repository. The
  self-test's optional item "primary metric configured" still fails, because the project's config names no
  metric. The checks added lines to the install's guard record. A copy of the files as they were before this
  upgrade is in `%TEMP%\nnkit-upgrade\real-install-before-20261112`. (The commit followed later that day: next
  part.)

### The real install: checked further and committed on 12 November
You asked for everything left open there to be finished and checked. Looking closer first corrected three things
I had said. The backups folder is git-ignored by the kit's own rule, so it is never committed. The kit's
uncommitted work there was 32 files from both upgrades (21 changed, 11 new), not nine. And the "two training
scripts" are registered single-run experiments of that project, which already ran on 25 October; its config
leaves the metric unset on purpose.
- Committed: one commit in that repository holding exactly those 32 paths, on its current branch, in its own
  message style, not pushed (the branch has no upstream). Its 418 other uncommitted entries, all outside
  `.claude/`, are untouched and nothing is staged. `git reset --soft HEAD~1` there undoes it and keeps the files.
- The two scripts, checked without running them. Under the project's own interpreter (Python 3.14.7), every call
  they make to the run logger binds to the installed `runlog.py`, and `tests/test_runlog_units.py` passes. The
  variables and manifest keys they read at start are still provided. In the rehearsal copy, a stand-in script
  that makes the same start checks and logger calls ran through the upgraded `expctl` under that interpreter:
  one run finished (12 steps, `completed`), one was stopped with `stop --wait 60` (`interrupted` at step 28),
  `status` and `curve` read both, and the new manifest has exactly the keys of the 25 October manifests.
- Not run, on purpose: the two scripts themselves and a final evaluation. That project's own records reserve
  both for its owner's explicit decision: each experiment is registered for one run, and the sealed test set is
  read once. A request to finish everything does not name either. To have one run, name it: which script, or
  which of the two final-evaluation entries and on which run.
- The metric stays unset. The project's records say it is unset on purpose, so that the harness does not rank
  its runs; the self-test's item is optional and the self-test's overall result is ok without it.
- That project has its own check of the guard against other checkouts of the same repository (25 calls replayed
  against a replica in a temporary folder). Against the upgraded guard, 13 of the calls that the 23 October
  guard let through are now refused. Three are still allowed, and a fourth is refused with another reason text
  than the check expects. The three: an edit of a frozen file in a git worktree registered at some other place
  inside the project (the guard knows worktrees by their place, `.claude/worktrees/<name>/`, not from git's
  list); and an edit of `.claude/settings.local.json` in a sibling worktree or in an unregistered copy beside
  it (for the file tools the guard matches harness paths against the path as given, not against the path
  mapped back to the repository, as it does for frozen and sealed paths and for shell commands). All three were
  allowed before the upgrade too. The patch that project had drafted for the 23 October guard no longer applies.
  Round 2 changed both points in the kit, and the real install has that since the third installer run
  ("Round 2", "The third installer run on the real install").
- Traces my checks left there: 12 lines in its guard record (4 on 11 November, 8 on 12 November; the third
  installer run added 16 more, "Round 2", "The third installer run on the real install"), from the
  self-test's probes and four probes of the final-evaluation rule. Each is a made-up call handed to the guard to
  see its answer; none was carried out. That project counts these lines, so the commit message names them. This
  part added none: the guard check ran against the replica, and `expctl selftest` was not run there again. No
  bytecode cache was written there.

## 5. The ledger in summary
`docs/upgrade/LEDGER.md` has one row per candidate (1,609 rows from 32 notes), a coverage map with one
entry per gap and per "Find the rest" item, the recommended combination, and a table of the points where notes
disagree and which side the kit follows. The 26th note, `scout/draft/second-look.md`, was written after the live
runs: it ranks the open rows, adds ten, and holds what the pilot's own data says about the loop's keep rule.
Round 2 added four notes with 82 rows: `census-loops` (15), `census-harnesses` (17), `newer-methods` (9) and
`round2` (41). Round 4 added one, `round4`, with seven rows. Round 5 added one, `round5`, with 104 rows: the
89 claims of the review of 14 November, 13 rows for the fixes that followed the round's independent review
and two for the faults that the round's last full test run found.

| Decision | Rows | Before round 2 | |
|---|---|---|---|
| Adopt | 474 | 399 | 332 finished, 142 unfinished (each says what is missing); before round 2: 261 and 138; before round 3: 277 and 138; before round 4: 280 and 138; before round 5: 288 and 134, of 422 |
| Trial, Assess | 233, 324 | 221, 293 | undecided: each names the test it needs; none of these tests was run (usage limit); before round 5: 224 and 314 |
| Hold, Reject | 324, 254 | 310, 193 | with the reason; before round 5: 320 and 225 |

- What "Trustworthy decisions" (section 1) changed here: eight adopted rows became finished. Six more are built
  in part and stay unfinished, each saying which part: the confirmation outside the loop, a third data tier
  behind the receipt, and negative controls, known-answer cases and tamper fixtures for the evaluator. The row
  for the pooled noise estimate also named a comparison seed by seed; round 2 measured that part on the
  benchmark and rejected it for the loop ("Round 2", point 6).
- What round 2 changed here: the Adopt rows grew by fifteen and the finished ones by fifteen ("Round 2", "What
  was integrated"); the number of unfinished rows is the same. What the round measured or simulated is
  decided, as Adopt or Reject, not left as Trial.
- What round 3 changed here: three Trial rows of `second-look` are Adopt and finished, because they are built on
  the go-ahead of `ROUND2.md`: numeric settings searched by the harness, the fine-tuning track with a second
  benchmark task, and the restart on a stall. No measurement decided them. Each row says what was built, how
  it differs from what the row named, and that its effect on results is not measured ("Round 3").
- What round 4 changed here: four adopted rows that were unfinished are finished (the self-test's fixtures,
  the controls, and two on the subagents' hook). The new note `round4` has seven rows: four adopted and
  finished, two rejected, and one Trial, controls for the fine-tuning task ("Round 4").
- What round 5 changed here: the note `round5` has 52 adopted rows, all built (37 of the review's claims,
  the 13 fixes after the independent review and two for the faults of the last full test run), 9 Trial, 10
  Assess, 4 Hold and 29 Reject. Round 4's Trial
  row about two controls for the fine-tuning task stays Trial for the one that is not built, the untrained
  adapter; the other, shuffled intents, is a finished row of `round5`. The generator let a reference that covers a row outrank the record of what was built. The
  record wins now: three rows whose record said "partly built", and five of eight rows that name kit code
  and were checked against it, moved from finished to unfinished. The other three of the eight are finished:
  the `datasets` advisory and the split check, both built in this round, and the Windows memory setting,
  which is reference text by its nature ("Round 5").
- Added on 12 November, at the user's question whether other projects would do better: four rows for candidates
  no note held. Fine-tuning a small model on a stronger agent's solved traces before RL (a TRL example): Trial.
  Harness adapters (one LoRA per model and agent harness, trained by RL inside the harness): Hold. The safeagents
  proxy and atif-scan, which check an agent's tool calls and recorded sessions for reward tampering: Assess. The
  Plurai Simulation plugin, a hosted service that tests agent applications with simulated users: Hold. None was
  tried; the reasons are in the rows and in `scout/draft/second-look.md` ("Asked afterwards"). The other projects
  the user named already had rows, and their decisions did not change.

- Recommended combination (`references/stack.md`): uv 0.13.7; PyTorch 2.15.0 (`cu132` wheels); the kit's run
  directory as the record, Trackio 0.45.0 as an optional mirror; Optuna 5.0.0; lm-evaluation-harness 0.4.13 in its
  own environment, sacreBLEU 2.6.0; `nnremote` over ssh or Hugging Face Jobs (huggingface_hub 2.4.0); Context7 MCP
  4.6.0 and the Hugging Face MCP server v0.4.34 through `--mcp`; Transformers 5.22.2, TRL 1.17.1, PEFT 0.21.2 and
  bitsandbytes 0.50.2 for fine-tuning. All were installed and smoke-tested except the MCP servers; the PyTorch pin
  failed on the GPU here, so its ledger row is unfinished (section 3).
- The unfinished adopted rows are mostly refinements: a noise floor based on the median absolute deviation,
  a remote-side dead-man stop for ssh targets,
  a doctor command, minimum agent versions, a data manifest command, a notifier, a secret scan of logs, an
  environment allow-list for the loop's sessions (today a deny-list).
- Kept disagreements, untested: `loop.md` recommends a mid-tier model for iteration sessions while the prompting
  note recommends the most capable one; the minimum Python stays 3.8 (it passes) against one note's 3.9.

## 6. Changes in the behaviour of existing features

### Guard
The sealed test set, the frozen evaluator and the protection of live runs are not weaker: their baseline checks
in `tests/test_kit.py` pass unchanged, except three that became stricter (malformed input, first row;
`cat data/*/labels.csv`, which is now denied instead of asked; and the configured final-evaluation command typed
directly, last table of this part). One gap of the 23 October guard was kept on purpose
and documented: a plain `grep -r`, `find`, `ls -R` or `tree` started at the project root itself was not
questioned, and such a `grep` could print lines of sealed files. Round 4 closed it ("Round 4"). A second gap, also
older than the upgrade, was found on 12 November: git worktrees outside `.claude/worktrees/` and the harness
files of sibling worktrees were not covered (section 8). Round 2 closed it, and its review led to further
changes of the guard. Those are listed under "Round 2", "Changes in the behaviour of existing features", not
in the tables below.

| Change | Reason | Test |
|---|---|---|
| Hook input the guard cannot read (not JSON, no tool name, unknown shape) is refused with exit code 2; it used to pass silently | required by the prompt | `test_kit.py` "guard refuses malformed input", `test_ports.py` "every unreadable input is refused" per agent |
| An "ask" becomes a "deny" on Codex and Cursor always, and on Claude Code under `dontAsk`, `bypassPermissions` or `NN_UNATTENDED=1` | an ask nobody sees must not pass | `test_ports.py` |
| New asks: a command that starts paid compute directly, piping a download into a shell, uploading or publishing to a hub | money, supply chain and publishing need a person | `test_ports.py` |
| The read-only rules of the two subagents are also applied by the project guard, keyed on the agent type | they held only through the agent file's own hook | `test_ports.py` "by a read-only subagent is denied by the project guard" |
| The hook matches every tool; an unknown tool is checked for sealed paths and for a command instead of passing unseen | new tools and other agents' tool names | `test_ports.py` |
| The project root is found by walking up to `.claude/nn-training.json` | sessions in subfolders and worktrees | `test_kit.py`, `test_loop.py` |
| In a git worktree of the project, the sealed, frozen and harness patterns also cover the outer checkout | the loop works in worktrees | `test_loop.py` "guard rules in a worktree of the project" |
| With `NN_UNATTENDED=1`, file tools, reads included, are refused outside the project | an unattended session stays inside | `test_loop.py` |
| `nnloop start, resume, stop` and `nnremote launch, resume, stop` ask | an agent must not start or stop a campaign or a paid run on its own | `test_loop.py`, `test_remote.py` |
| New protected (ask) paths: `AGENTS.md`, `.codex/**`, `.cursor/**`, `.agents/skills/nn-training/**`, `.claude/state/remote-ledger.jsonl` | the ports' files and the spending ledger are harness files | `test_ports.py`, `test_remote.py` |
| The audit log names the calling agent; one beacon line per decision when `NN_GUARD_BEACON` names a file | the loop checks that the hook really ran | `test_ports.py`, `test_loop.py` |
| Grep and Glob calls are checked with `file_path` as their base too | payload variants | `test_ports.py` "Grep inside sealed data" |

Changes made after the independent review (section 7):

| Change | Reason | Test |
|---|---|---|
| PowerShell, `cmd` and nested-interpreter forms of writing, deleting and killing (`Set-Content`, `Out-File`, `Copy-Item`, `Remove-Item`, `rd /s`, `del`, `Stop-Process`, `wmic ... terminate`, code handed to `python -c`, `bash -c`, `cmd /c`) are treated like their Bash forms: they ask, and are denied for the read-only subagents. They used to pass unseen | on native Windows the agent's shell is PowerShell | `test_kit.py` guard cases (frozen evaluator, live run directory, old runs, checkpoints, spending ledger, kill forms); `test_ports.py`, block "what the review of 11 November found open" |
| The Grep and Glob tools are denied when they would reach existing sealed files (no path, `.`, a folder above them, a pattern such as `**/*.csv`). A filter that excludes them passes. Grep treats git-ignored sealed files as out of reach, unless the folder it is given is itself ignored | such a search returned sealed lines | `test_kit.py`, `test_ports.py` |
| Shell reads: wildcards are expanded on disk and `cd` is followed, so `cat data/*/labels.csv` (used to ask), `cat d*/test/labels.csv` and `cd data && cat test/labels.csv` (used to pass) are denied. A recursive search in a folder below the root that holds sealed files asks; `rg` is checked at the root too | the same | `test_kit.py` |
| Path rules ignore letter case on Windows and macOS | the file system does | `test_ports.py` (runs on Windows) |
| An unreadable `.claude/nn-training.json` makes every call ask, reads included, except reading the config itself. Reads used to pass | without the config the guard does not know what is sealed | `test_ports.py` |
| `nnloop` and `nnremote` control verbs ask wherever they stand on the command line (`--root=. launch`) | the approval could be skipped by an option before the verb | `test_kit.py` |
| `loop.protected_data` and `loop.link_paths` count as frozen: an edit asks | on Windows linked paths are the project's own files | `test_ports.py` |

Not changed, on documentation evidence: under Claude Code's `auto` permission mode an "ask" stays an "ask",
because auto mode still shows the prompts a hook forces (permission-modes page, read 11 November). A test pins it.

Changed after the headless run (section 2), in how the guard logs, not in what it asks, denies or allows: on
Windows the audit log and the loop's guard record are appended under a lock on one byte beyond the end of the
file. Claude Code starts one guard process per tool call, parallel calls start several at once, and two appends
could land on the same offset, so that one line destroyed the other: one of 35 records in that run, and about a
tenth of 800 lines when eight processes wrote at once without the lock. Test: `test_kit.py`, "guard log lines
that eight processes write at the same moment all survive". Linux appends are unchanged.

Changed with the single-use final evaluation (section 1, "Trustworthy decisions"):

| Change | Reason | Test |
|---|---|---|
| The configured final-evaluation command typed directly is denied, with a pointer to `expctl final-eval`. It used to ask | a use that goes around `expctl` leaves no receipt, so the count of uses would be wrong | `test_kit.py`, guard cases (the case that expected "ask" now expects "deny") |
| `expctl final-eval` asks, and is refused where nobody can be asked. A sealed path or the sealed token among its own arguments is denied; the arguments of the typed final command used to be exempt from that check | the final evaluation stays a step a person approves; its arguments name a checkpoint, never test data | `test_kit.py`, guard cases (`final-eval -- --ckpt ...` and `--again` ask, `-- --data data/test/labels.csv` is denied, `expctl --help \| grep final-eval` passes) |
| The two read-only subagents may not start `expctl final-eval` | a reviewer or analyst must not spend the single use | `test_review_fixes.py`, read-only hook cases |
| New protected (ask) path: `.claude/state/final-eval/**`, for shell writes and deletes and for edits with file tools | the receipt is the count of uses | `test_kit.py`, guard cases (`rm`, `Remove-Item`, `python -c "open(..., 'w')"`, the Edit tool) |

What this means for a project that already has `final_eval_commands`: the final evaluation is started as
`expctl final-eval [-- ARGS]`, no longer by typing the command. An entry that needs a shell (a pipe, `&&`, a
redirection, a variable) is refused by `expctl final-eval` with a message that says to put those steps into a
script; the installer does not rewrite such an entry. With several entries, `--which N` names one, and the second
is a further use that needs `--again "reason"`.

### Installer
- `--agents`; MCP servers only with `--mcp` (they were merged by default); `--uninstall`; `--dry-run` unchanged.
- The kit's hook entries are rewritten to the current form and named in the output (it used to skip a hook whose
  script was already registered).
- The interpreter is checked by running it, written into every installed file that calls one and recorded in the
  config; an upgrade keeps the one the earlier install used.
- Manifest with hashes (`.claude/nn-training.manifest.json`); `install-legacy.json` holds the hashes of the 23
  October files, so an upgrade can tell an edited file from an untouched one. Edited files are replaced, named and
  backed up, never silently.
- More allow rules for read-only `expctl` commands, two more ask rules for Hugging Face tools.
- `claude-md-block.md` is now `instructions-block.md` (the 23 October file is kept under `tests/fixtures/` for the
  upgrade test; nothing else in the folder was renamed or deleted). With Codex or Cursor the rules live in
  `AGENTS.md`.

### Migrations done by the installer
`harness_paths` gains the five paths above and `.claude/state/final-eval/**`; the `python` key is added; hook
entries are rewritten; the block in `CLAUDE.md` is replaced, or becomes an import of `AGENTS.md`; `.gitignore`
gains `.claude/worktrees/`. No path or format of runs, journal or config changed. What a `final_eval_commands`
entry may contain is narrower when it is run through `expctl final-eval` (end of "Guard" above); nothing rewrites
an entry.

Not by the installer, by the loop itself: a campaign whose state was written before the pooled noise estimate
(`state.json` with the baseline's deviation and no `noise` entry) is converted when it is resumed, with the old
deviation as its first panel (`test_loop.py`, "a campaign from before the pooled estimate is resumed ...").

### Other
- `expctl`: new `resume` command (a resumed run is a new run directory that names the one it continues); atomic
  writes retry when Windows refuses a replace for a moment; a run that exited with code 0 without a result is
  "incomplete", not "completed (inferred)"; hints show the recorded interpreter; `selftest` has more checks.
- `runlog`: `RunLog.resume_from`; the result write retries a refused replace; `should_stop()` polls `stop.json`.
- After the review, `nnremote`: source files with credential-like names stay at home unless `remote.files` names
  them, and are listed as `not_sent`; a paid start is refused when the spending ledger is gone although earlier
  paid runs are recorded (`test_remote.py`). After the last test run (section 3): a Hugging Face job hands over
  its exit record only after every other file, and retries its last copy round. `nnloop`: the wall-clock limit also ends an agent session in flight;
  a start-up note names scoring files the agent can read; the worker prompt no longer claims that the agent cannot
  see the scoring data or cannot run code (`test_loop.py`).
- After the sign-in (11 November), `nnloop`: a Claude Code session that reports usage billed per use, or a warning
  that the plan limit is near while usage credits are on, is ended, and the campaign stops with its state written,
  unless `--max-usd` was given. It reads three signs in the agent's `rate_limit_event` lines (`test_loop.py`).
  Agent sessions no longer inherit the variables that describe the session or app `nnloop` was started from; with
  them a child session could wait for the host app to renew its sign-in (`test_loop.py`). `benchmarks/pilot.py`
  watches its own sessions for paid usage in the same way (`test_benchmarks.py`).
- After the comparison (section 1, "Trustworthy decisions"), `nnloop`:
  - The margin is larger while a campaign is young: with three seeds the first change needs a mean gain of 2.3
    pooled deviations, where the earlier rule asked for 1.6 deviations of the baseline runs; after eight more
    panels 1.7. `nnloop status` shows the pooled noise with its degrees of freedom.
  - New ends of a campaign: "self-test: ..." before any agent session (a safeguard stop: fix the cause and begin a
    new campaign) and "search exhausted" after two sessions in a row that declined (exit code 0, like a limit).
    New iteration status `declined`; a seed panel whose runs all score exactly the same is `invalid`.
  - Once a change is kept, two seed panels of runs, with their wall-clock time and GPU-hours, are held back from
    the limits for the confirmation, so the iterations end that much earlier and the stop reason names what was
    held. With three seeds and `--max-runs 12` that is six runs for the search and six for the confirmation. If
    the limits no longer cover it when a change is kept, nothing is held and the journal says the confirmation
    did not run; a `resume` with higher limits runs it, without an agent session if the limits cover nothing
    else. The confirmation also runs when a campaign stops for repeated failures. Money and token limits rest
    while it runs, because it starts no agent session. New config key `loop.confirm`; `false` turns the
    confirmation and the hold off.
  - `benchmarks/pilot.py` sets `loop.confirm` to `false` in its loop arm, in a commit of its own, so that every
    arm searches with the same 12 runs. The pilot therefore does not measure the confirmation.
- After the comparison, `expctl`: new `final-eval` command (section 1); each use writes two receipt rows, a log
  beside the receipt and a journal entry. The reader of hash-chained ledgers moved from `nnloop.py` to `expctl.py`
  and now also counts a row that is not a JSON object as a broken chain.
- 13 November ("After the guide"), `expctl status`: a best checkpoint whose recorded path does not exist here
  is looked for by the part of that path below the run's own folder. Where it is found, the run stays in the
  list of best runs and `ckpt` gives the path here; before, the run left the list with the alert "recorded
  checkpoint missing". A checkpoint that is gone raises the alert as before (`test_kit.py`). The practice
  scripts under `benchmarks/` now record the model they save as the run's best checkpoint
  (`test_benchmarks.py`).
- Status line: on native Windows the 23 October version killed the training run it looked at (see section 8).
- Session-status hook finds the project from its own location. Subagent files state their effort level.
- SKILL.md: scouting gate, pointers to the new references, agent-neutral wording, standard-only frontmatter. The
  old Muon speed-up line is gone; `optimization.md` treats Muon as a candidate to test.

### Existing tests that changed (all in `tests/test_kit.py` unless noted)
- The malformed-input check is reversed: such input is now refused.
- `cat data/*/labels.csv` now expects "deny" instead of "ask": the guard expands the wildcard, and it names the
  sealed file.
- Snapshot checks compare with `samefile`, the subdirectory check accepts backslashes, the lost-run test uses a
  hard-kill helper, the ok-run is 200 steps long, the status line check is strict (the run must be shown and
  still alive): all so that the file runs on native Windows.
- Added, not changed: the reference lint, two `stop.json` checks, the result-write retry (`test_runlog_units.py`),
  the check of log lines written at the same moment.
- New files: `test_ports.py`, `test_loop.py`, `test_remote.py`, `test_benchmarks.py`. None was removed.
- Added on 13 November, nothing changed: one check in `test_benchmarks.py` (status lists a practice run as
  the best one, with the model it saved) and one in `test_kit.py` (a checkpoint recorded on another machine
  is found in the run's own folder).
- Changed with "Trustworthy decisions" (section 1). In `test_kit.py`: the guard case for the configured
  final-evaluation command typed directly expects "deny" where it expected "ask", because that command now runs
  only through `expctl final-eval`. In `test_loop.py`, which is itself new in this upgrade, the first campaign's
  checks follow the new behaviour: its margin is compared with the pooled t-test instead of the baseline's
  deviation, its expected ledger rows include the self-test and the confirmation, and it uses 12 runs where it
  used 8, because the confirmation's two seed panels are now part of a campaign that keeps a change.

## 7. Independent review
Reviewer: one fresh subagent on the Opus model that got the repository and the prompt's requirements, not this
session's context. It replaced the deep-sweep-red-team skill, to stay inside the usage limit. It read the code, ran
its own probes against the guard in a temporary project, and kept 18 findings: 2 blocking, 7 major, 9 minor, 4 of
them marked as suspected, not confirmed. It could not write its findings file, so this table is the record. It
met no attempt to redirect it. Fixes are tested as section 6 lists.

| # | Severity | Finding | What was done |
|---|---|---|---|
| 1 | blocking | PowerShell cmdlets, `cmd` deletes and `python -c` got past every write, delete and kill rule, also for the read-only subagents | Fixed |
| 2 | blocking | Sealed data could be read through Grep without a path, Glob patterns, wildcards, `cd` and upper-case paths | Fixed. Kept gap: an unfiltered `grep -r`, `find` or `ls -R` at the project root was not questioned (documented). Closed in round 4 |
| 3 | major | An unreadable config turned reads of sealed data into allows | Fixed |
| 4 | major | `nnremote.py --root=. launch` and similar forms skipped the approval; deleting the spending ledger reset the cap | Fixed: the verb is matched anywhere on the line; PowerShell and `cmd` deletes of the ledger ask; `nnremote` refuses paid starts when the ledger is gone but paid runs are recorded |
| 5 | major | The agent can read the loop's scoring split unless the project seals it, and several texts said otherwise | Texts corrected (worker prompt, `loop.md`, README, ledger); the loop names readable scoring files at start. Not changed: a split that training also reads cannot be hidden |
| 6 | major | On Windows `link_paths` are hard links or junctions, so a write reaches the project's own data | For the agent: those paths and `protected_data` are now frozen. For a training run: not prevented on Windows, where runs are not confined; the checksum catches it at the next check. Documented |
| 7 | major | A Codex worker has a shell, and its reads are not confined | Answered: documented. The guard hook and the transcript scan are what hold it; not verified live |
| 8 | major, suspected | Without bubblewrap, training code could alter what the evaluator imports | Answered: README and `loop.md` now say "not enforced" for the evaluator's environment. The evaluator is not started in Python's isolated mode, because it may import its own modules and user-installed packages |
| 9 | major, suspected | Whether the Codex hook sees `apply_patch` edits was not captured live | Answered: the README says the payload shape comes from documentation. Needs a live Codex session (section 9) |
| 10 | minor | README and ledger overstated what was checked or enforced | Corrected: README rows for the loop, the denied actions and the platforms; ledger rows for gap 1 and for measuring |
| 11 | minor | Limits are checked only between steps | Fixed in part: the wall-clock limit also ends a session in flight. Tokens, money and GPU-hours can overshoot by the step under way; documented |
| 12 | minor | `--in-container` is the user's own declaration | Answered: kept, and documented as a statement `nnloop` cannot verify |
| 13 | minor | A Hugging Face job mounts the whole bucket with write access | Answered: documented; use a bucket that holds only this project's runs |
| 14 | minor | The remote bundle sent untracked files that git does not ignore, secrets among them | Fixed: files with credential-like names stay at home unless named |
| 15 | minor, suspected | The Codex hook on Windows uses a relative path | Answered: kept, because the committed hook file must work in every checkout and worktree. From another folder the hook cannot find its script, which Codex should read as a refusal. README: start Codex from the project root. Not verified live |
| 16 | minor, suspected | Under Claude Code's `auto` mode an "ask" might be approved without a person | Answered from documentation, no change (end of the guard part of section 6). Not verified live |
| 17 | minor, older than the upgrade | `expctl launch --via tmux` writes the environment to a file in the run directory | Answered, no change: the file is created with mode 0600, read once by the supervisor and deleted. It stays if the supervisor never starts |
| 18 | minor | No test covered findings 1 to 7 | Tests added in `test_kit.py`, `test_ports.py`, `test_remote.py`, `test_loop.py` |

The reviewer also checked and found in order: unreadable hook input is refused on all three agents; Codex and
Cursor asks become refusals; the file tools are denied on sealed paths in many path forms; edits into a live run
are denied; edits of the frozen evaluator through Edit, `sed -i`, `tee`, a heredoc and `git checkout --` ask; the
loop's limit refusals, harness-side score and clean stops; the remote cap, the filtering of variables and files,
the provider timeout and teardown after a complete pull; the installer writes nothing outside its target and keeps
config, journal and runs on upgrade and removal.

## 8. Things you should know
- **A bug in the 23 October kit on native Windows**: the optional status line checked whether a run was alive with
  `os.kill(pid, 0)`, which on Windows terminates the process. Your real install has no status line configured, so
  it was not hit. Fixed in `51a37a7`.
- **Attempts to redirect the agent** (none followed). The two reports you supplied contain a ZIP link, paste-in
  prompts and install commands; the Gemini report's loop contract forbids stopping to ask and reverts with `git
  reset --hard`. autoresearch.lol labels its buttons as the GitHub repository but links them to an unrelated
  commercial site. Karpathy's autoresearch and its Windows port tell users to disable all permissions and the
  agent never to stop; several READMEs (Unsloth, Axolotl, a dataset generator) pipe a download into a shell; two
  Hugging Face skills tell the agent to submit paid jobs at once; Runpod's and Unsloth's documentation address
  agents directly (send feedback, send the user's goal); several documentation sites tell readers to fetch an
  index file first; a search service's error text asked for an account and an API key; one package printed text
  telling agents to disregard instructions and delete tests. The full list is in the research notes, section
  "Redirect attempts" of each. In the loop's own scouting sessions: the first noted that no page tried to direct
  it; the second noted that a search result ended with a line telling it to give its sources as links (text of
  the search tool), which it recorded and did not take as an instruction.
- **Claude Code updated itself on Windows during the work**, from 2.1.303 to 2.1.322, through its own updater; I
  did not start that. The headless runs used 2.1.322. The WSL installs are unchanged.
- **Your account has usage credits turned on.** Claude Code's rate-limit events say so. A session that passes a
  plan limit would then go on at pay-as-you-go prices instead of stopping, which the prompt's "ask first if one
  would bill per use" forbids me to let happen. So the loop and the pilot now end a session and stop as soon as
  Claude Code reports paid usage or a warning that the limit is near (section 6, "Other").
- **Runs are not compared seed by seed, although I announced it.** When I listed the group "Trustworthy
  decisions" for your go-ahead, its first item read "estimate noise from all seed runs of the campaign, compared
  seed by seed". The estimate over all seed runs is built; the comparison seed by seed is not. In the pilot's data
  pairing by seed removed noise only for changes that leave the training trajectory alone (a weight average:
  deviation of the paired differences 0.0039 and 0.0033, against 0.012 to 0.015 unpaired), not for changes that
  alter it. And the deviation of such differences depends on the change, so it cannot be pooled over a campaign:
  with three seeds a paired test has two degrees of freedom and a multiplier of 4.53, against 2.87 for the pooled
  test at the first change. So it would have made the rule stronger for the first kind of change and weaker for
  the second, and which kind prevails is not known from one task. Round 2 then measured it on the benchmark
  (32 runs, two commits on eight seeds): the seed means of the two commits correlate at r = 0.30, too little
  for three seeds to pay for the degrees of freedom. It is rejected for the loop, and `references/uncertainty.md`
  keeps the paired test for comparisons by hand ("Round 2", point 6).
- **"Trustworthy decisions" has run once with a real agent and real training** (12 November, section 2): one
  campaign on the benchmark, with Claude Code on native Windows. Everything else about it rests on tests with a
  stand-in agent and stand-in runs, on both platforms. The figures for the keep rule come from a simulation with
  normal noise and independent runs, and the live campaign did not behave that way: its baseline runs lay much
  closer together than later seed panels, so its first keep was decided against the configured minimum margin,
  and the gain during the search was half the gain in the confirmation. A `loop.min_margin` chosen from what is
  known about a task's noise guards against the first; the benchmark's 0.005 did not. The self-test's rule that
  a seed panel with identical scores is invalid can hit an honest change when the metric is coarse and the seeds
  are few (`references/loop.md` says so).
- **Your real install has "Trustworthy decisions" since 12 November** (section 4). Its config holds two
  `final_eval_commands` entries, and neither needs a shell (checked by a script that prints only that, not the
  commands), so both fit `expctl final-eval --which N` (N is 1 or 2). The second one to be used will need
  `--again "reason"`, because uses are counted for the project. Typing either command directly is refused there
  now. The receipt starts empty: it does not know of final evaluations run before the upgrade. The kit's files
  there are committed since 12 November, and again after the third and fourth installer runs: local commits,
  not pushed. The two files of the fifth run are not committed. Its interpreter is written into them as a
  full path of this machine, so a checkout on another machine has to run the installer again.
- **The guard did not cover every other checkout of a repository; round 2 closed that.** This describes the
  guard before round 2, which is the one your real install has. It maps run snapshots and worktrees under
  `.claude/worktrees/` back to project paths, and from inside such a worktree it covers the outer checkout. A
  worktree that git registered at any other place is not covered. Tried on 12 November in a practice project,
  with made-up calls handed to the guard: from a session in a worktree registered beside the project, the Read
  tool gets the main checkout's sealed test file by absolute path, and edits of the main checkout's frozen
  evaluator and of its `.claude/settings.json` pass without a question (a shell `cat` of the sealed file is
  questioned). From a session in the main checkout, an edit of a frozen file in that worktree passes, and so
  does an edit of `.claude/settings.local.json` in a worktree under `.claude/worktrees/`. What holds: a
  worktree's own copy of a sealed file is refused, and from a worktree under `.claude/worktrees/`, which is
  where your real install lives, the same five calls are refused or questioned. Found with the real project's
  own check (section 4). None of it is new with the upgrade, and an unattended session is refused every file
  outside its project anyway. Round 2 closed it: the guard reads git's list of worktrees and matches harness
  paths on mapped paths too (`b7b7652`; "Round 2", "What was integrated"). The real install has it since
  the third installer run of 12 November.
- **Temporary folders left on this machine**: `%TEMP%\nnkit-upgrade` on Windows (test projects, the loop run
  `live1`, the pilot's folder `pilot1` with every project, transcript and score, the partial copy of your real
  install used for the upgrade test, logs, clean interpreters) and
  `~/nnkit-upgrade` in WSL (clean interpreters, a test project, the logs of the stack try). The kit needs none of
  them; delete them when you no longer want the evidence. The try environments for the third-party stack (6.4 GB
  in WSL) are removed. The package caches of uv and pip were left as they are; the tries added downloads to them
  (`uv cache prune` and `pip cache purge` clear them).
- **The Gemini report**: eleven of its claims are contradicted by primary sources
  (`docs/upgrade/scout/draft/user-reports.md`, section 4). The ones that matter for a design: Claude Code read-deny
  rules are not backed by a sandbox by default; its Codex profile tables, `sandbox_mode` in agent files and
  `mcpServers` inside `.claude/settings.json` do not work as written; upstream autoresearch has no immutable
  evaluator; several quoted speed-ups are about half of what it states or rest on one blog. The rest was taken as
  given, as you said.

## 9. What needs your decision, accounts or credentials
Answered on 11 November: the Claude Code CLI on Windows is signed in; the headless loop check and the pilot
followed (section 2). And the real install: upgraded on your go-ahead on 11 November and again on 12 November,
to the kit with "Trustworthy decisions" (section 4). Still open:

1. **Claude Code in WSL**: update it to 2.1.321 or newer (2.0.76 and 2.1.165 there) and sign it in, if you want
   loop runs on Linux, where training runs can be confined.
2. **Hugging Face Jobs**: your go-ahead for one paid canary under 0.10 USD, with credits on the account and a
   spending cap in the project's config. The stored login is not used without that. A private bucket or dataset
   repository for checkpoints is yours to create.
3. **A larger comparison**: done once, with five runs per arm (section 2): no difference between the arms beyond
   the noise, 4.1 million tokens from your subscription. More runs of the same comparison are not worth their usage
   (section 10, item 1); say if you want a second task or a stronger model instead. A second task exists since
   round 3 (`benchmarks/finetune/`); no comparison ran on it.
4. **Cursor**: install its terminal agent and say whether a container may be used for a loop test.
5. **Codex**: approve the kit's hooks once in `/hooks` of a test project, or allow
   `--dangerously-bypass-hook-trust` in temporary test projects. That also lets me capture a real Codex payload.
6. **Docker Desktop**: start it if you want container tests on Windows.
7. **The other project's final evaluation and its two registered scripts** (section 4): not run. If you want
   one run, name it: which script, or which of the two final-evaluation entries and on which run.
8. **The guard and other checkouts** (section 8): built in round 2, on the go-ahead of your round-2 prompt.
   The real install has it since the third installer run of 12 November, which also brought the guard fixes
   of round 2's review ("Round 2", "What needs your decision", item 1), and rounds 3 and 4 since the fourth
   run of 13 November ("Round 4", "The fourth installer run on the real install"). The fifth run of the
   same day brought the status fix (item 12).
9. **What to build next** ("Round 2", "What needs your decision", item 2): the first three items of that order
   are built ("Round 3"). What remains is in "Round 3", "What needs your decision", item 3.
10. **Round 3's two questions**: whether to measure any of its three items with a real agent, and this machine's
    Transformers install, which does not import ("Round 3", "What needs your decision"). The empty
    `bitsandbytes` folder in the same site-packages stopped a fine-tuning run on 13 November ("After the
    guide"); it is yours to remove.
11. **Whether the repository becomes public**: decided on 13 November, and done ("After the guide", "Public,
    on your word"). Still yours: the name on the licence and in later commits, which is now the account's
    name; the private repository of the first upload, `nn-training-harness-dev-history`, which you can
    delete; and the setting of your GitHub account that refuses a push which would expose your e-mail
    address (Settings, Emails: keep the address private, and block command-line pushes that expose it). I
    recommend it and cannot set it.
12. **A fifth installer run on the real install**: done on 13 November, on your word ("After the guide",
    "The fifth installer run on your real install"). On your "Yes, commit there" of 14 November the two
    files it changed are committed in that repository: one local commit of exactly those paths, not
    pushed, its 418 other status entries untouched. Where this report says they are not committed, this
    item replaces it. On your "Yes, push" this record is in the public repository.
13. **Round 5's questions** ("Round 5", "What needs your decision"): a push of the round to the public
    repository, which has most of the faults the round's independent review found until then; a sixth
    installer run on the real install; the installs, accounts and paid resources that the review's
    proposals need (ports for Antigravity and Gemini CLI, its MCP servers, cloud drivers, a container as
    the box); a second pilot or a campaign with a real agent; and what to build next.

## 10. Most valuable next steps
A second look after the live runs (11 November, `scout/draft/second-look.md`) put the build work in this order:
first what makes the loop's decisions trustworthy; then what may raise results (numeric settings searched by the
harness, a fine-tuning track for language models, seed escalation); then unattended reliability (a guard-liveness
check, a readiness report, a reliable stop on Windows). The first group is built (section 1, "Trustworthy
decisions"). Round 2 built one item of the second (seed escalation, as a second seed panel for a near-miss) and
part of one item of the third (the loop requires the guard's record after every session). Round 3 built the
other two items of the second group, numeric settings searched by the harness and a fine-tuning task, and a
restart on a stall; none of them is measured. The rest is not built. The list below is the earlier one, brought
up to date after rounds 2 and 3; what remains of my order for the build work is in "Round 3", "What needs your
decision", and after rounds 4 and 5 in the sections of the same name there. Of round 4's order, round 5 built
the repair attempt after a crash and the control for the fine-tuning task, and lifted the guard's file bound
for a folder sealed as a whole. First in my order now is a second reviewer's look at the fixes that followed
round 5's independent review: they are checked by my own probes and tests only.

1. If you want to know whether the kit helps, a larger comparison of the same kind is not the way. With five runs
   per arm the upgraded kit, the old kit and no kit lie within the noise of one another (an arm's runs differ by
   0.005 to 0.013, standard deviation), and finding an edge of 0.004 would take about 70 runs per arm: about 21 hours
   and 46 million subscription tokens for the upgraded and the old kit alone, against 4.1 million for the five-run
   pilot. A second task, a stronger model or a longer budget would tell more, and so would a measure of what the
   kit protects (sealed data untouched, overfitting to the validation split) next to the final loss. The second
   task exists since round 3 (`benchmarks/finetune/`, 44 seconds a run with the model's loading); no comparison
   ran on it.
2. A loop campaign on a task of your own, to see whether kept changes add up outside the benchmark. On the
   benchmark the campaign of 12 November (section 2) kept two of eleven trained changes and then ended itself
   with a third of its runs unused, because the agent saw no change that would clear the margin: what limits the
   loop there is the power of a three-seed panel, not the budget. Round 2 built more seeds for close calls (the
   second seed panel) and measured why seed panels of the same code differ: the noise lies between seeds and
   does not carry over from one version of the code to the next. In the one live campaign since, the second
   panel made one keep, and the confirmation found that gain inside the noise. Numeric settings searched by the
   harness would address the other limit, the number of ideas tested per hour; round 3 built them
   (`loop.search_trials`), and whether they do is not measured. Give a
   campaign a run limit well above five seed panels, so that the confirmation does not take most of the runs.
3. The paid canary on Hugging Face Jobs, then a remote-side dead-man stop for ssh targets.
4. The unfinished rows with the most effect on validity: checks of the evaluator with a tampered and a cheating
   run, and negative controls (shuffled labels, a constant predictor). The comparison seed by seed is off this
   list: round 2 measured and rejected it.
5. A live Codex and Cursor session each, with captured hook payloads replacing the documented ones in the tests.
6. Find out why PyTorch 2.15.0 (`cu132`) crashes on this GPU in WSL2, or choose the newest build that passes a GPU
   smoke test, and correct the pin in `references/stack.md`.
7. Trials of the undecided rows that are cheap on this machine (Trackio mirror, Muon and Schedule-Free AdamW on the
   benchmark, Inspect AI).
