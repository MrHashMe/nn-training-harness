# Unattended research loop (`nnloop`)

Checked: 2026-11-11 (Claude Code 2.1.303, Codex CLI 0.167, Cursor CLI docs of that date; keep rule, the
harness's search of numeric settings and the restart of a stalled campaign: 2026-11-12; the rotating first seed: 2026-11-14)
Refresh: re-read each agent's headless-mode and permission documentation and run `tests/test_loop.py`; the
start-up lines of `agent_argv` in `scripts/nnloop.py` are the only agent-specific part.

`nnloop` runs the hypothesis → change → run → keep-or-revert cycle with nobody watching. It is opt-in and it is
for cheap runs (seconds to minutes each). It does not replace Phases 0–3: the protocol must be frozen and the
evaluator trusted first, and what a campaign keeps is a candidate that still goes through Phase 5.

`nnloop` below means `python3 .claude/skills/nn-training/scripts/nnloop.py`, run from the project root.

## Who decides what
- The agent: one change per iteration, inside `editable_paths`, plus `PROPOSAL.json` (title, hypothesis, source);
  or no change and a `PROPOSAL.json` that says why, when it expects nothing to help. Where `search_trials` is
  set, it may leave the numbers of its change to a search by the harness.
  A Claude Code worker has no shell: it cannot run code, start runs or use git. A Codex worker has a shell inside
  its sandbox; it is told not to use it, and the guard and the transcript scan are what hold it to that.
- The harness: the worktree, the commit, every training run, the score (it runs the frozen evaluator itself, in
  its own process, on what the run saved; the number a training script prints about itself is ignored), the
  keep/revert decision, the limits and the records.
- The user: the limits, at start. Starting, resuming or stopping a campaign from an agent session asks for
  approval (the guard), because it commits compute and agent usage.

## Before the first campaign
1. The project is a git repository and the kit's files are committed (worktrees are checked out from git; without
   the committed guard an iteration would run unguarded, so `nnloop` refuses).
2. `.claude/nn-training.json` has a `loop` section (editing the file needs the user's approval):

| Key | Meaning |
|---|---|
| `task` | What to optimise, in words the agent reads. State what a run must save. |
| `train_command` | Argument list; `{python}`, `{seed}` are filled in. Runs in the iteration's worktree through `expctl launch`. |
| `eval_command` | Argument list; `{python}`, `{run_dir}` are filled in. Must print a last JSON line with a finite `score` (or `{"error": ...}` and a non-zero exit to refuse a run). Must name a file covered by `frozen_paths`, read a validation split, and not be a `final_eval_commands` entry. It reads what a run saved as data, never as code: no pickle (`torch.load` only with `weights_only=True`), no import of a file from the run folder, no option that lets a saved file name code to load. |
| `direction` | `minimize` or `maximize` (default: `metric.direction`). |
| `seeds` | The seed panel, at least two whole numbers. Every kept change was trained on all of them. A near-miss is also trained on the seeds that follow the largest one (with 1, 2, 3: on 4, 5, 6). |
| `run_budget_s` | Wall-clock budget of one run, start-up and saving included; a run that exceeds it is cut off and its iteration is invalid. |
| `editable_paths` | Globs the agent may change. They may not overlap frozen, sealed or harness paths. |
| `min_margin`, `noise_mult` | Keep rule: the mean improvement over the seed panel must exceed `max(min_margin, t × sd × sqrt(1/c + 1/b))`, with `c` runs of the change and `b` runs of the best so far (both the panel's size until a near-miss doubles them). `sd` is the run-to-run deviation pooled over every full seed panel of the campaign, the change's own included. `t` is the multiplier of Student's t-test that keeps a change without effect as rarely as `noise_mult` (default 2: about 2 %) would with a known deviation; see "The keep rule" below. |
| `confirm` | `false` turns off the confirmation on fresh seeds at the campaign's end (step 4 below) and the share of the limits held back for it. Default: on. |
| `search_trials` | A whole number of at least 2: a change may then leave numeric settings to the harness, which trains up to that many versions of it and tests the best one (see "A search by the harness" below). Left out: no search, and the worker is not told of one. |
| `restart_after` | A whole number of at least 1: after that many iterations in a row without a keep, the campaign goes back to the commit before its last keep and looks in another direction from there (see "A restart when the campaign stalls" below). Left out: no restart. |
| `controls` | A list of runs that cannot have learned the task, each `{"name": ..., "train_command": [...], "floor": number}`. The self-test trains each one once and stops the campaign if the evaluator scores it better than its floor by more than the margin (see "One campaign", step 1). Left out: no controls. |
| `protected_data`, `link_paths` | Git-ignored inputs: `protected_data` globs are checksummed with the evaluator each iteration; `link_paths` are linked into the worktree (each must be covered by `frozen_paths` or `protected_data`, none may be sealed). |
| `eval_writable` | Paths inside the project that the evaluator may write besides the folder it scores, for an evaluator that keeps a cache or its predictions there. They take effect where the evaluator runs in a sandbox (Linux with bubblewrap: see "What is enforced, and where"), may not be protected (frozen, sealed, harness, protected data) and may not hold anything protected. Left out: none. |
| `agent_timeout_s`, `max_failures`, `eval_timeout_s`, `max_hypotheses` | Session time limit (900 s), failed iterations in a row before the campaign stops (3), evaluator time limit (600 s), hypotheses the scout may list (8). |

3. `expctl selftest` passes.

## Commands
```
nnloop start  --campaign NAME --agent claude|codex|cursor --max-runs N [--max-hours H] [--max-gpu-hours G]
              [--max-usd D] [--max-tokens T] [--model M] [--effort E] [--no-scout] [--detach]
nnloop resume --campaign NAME [new totals]      nnloop status [--campaign NAME]      nnloop stop --campaign NAME
```
- It refuses to start without a limit, and refuses a limit it cannot measure: `--max-usd` needs Claude Code,
  `--max-tokens` needs Claude Code or Codex, `--max-gpu-hours` needs `nvidia-smi`. Cursor's terminal agent
  reports neither cost nor tokens. Limits are totals of the whole campaign; it stops at the first one reached.
  They are checked between steps (a session, a run). The wall-clock limit also cuts off a run or a session in
  flight; tokens, money and GPU-hours can overshoot by the one step that was under way.
- Once a change is kept, the loop holds back what the confirmation needs: two seed panels of runs, with their
  wall-clock time and GPU-hours at the full run budget. The iterations end that much earlier, and the stop reason
  names what was held. If the limits no longer cover it at the moment a change is kept, nothing is held, the
  search uses them up and the journal says that the confirmation did not run; `resume` with higher totals runs it.
  With a run limit below about five seed panels the hold takes a large share: raise the limit, or set
  `loop.confirm` to `false` and check the gain yourself.
- A subscription with usage credits (extra usage) turned on moves to pay-per-use when its included usage runs out.
  Without `--max-usd` the loop does not follow it there: it ends the session and stops as soon as Claude Code
  reports that credits are in use, or warns of a plan limit while credits are on. With `--max-usd` it goes on,
  and the limit counts the cost Claude Code reports for all sessions, which is at least what is billed.
- `--detach` returns at once; `status` and `experiments/loop/NAME/loop.log` show progress.
- `--model`/`--effort`: choose a mid-tier model and a moderate effort for the iteration sessions. Each one makes a
  single small edit; the most capable models cost several times more per iteration and are more often refused
  or rate-limited in unattended use.

## One campaign
1. Baseline: the current commit on every seed. This gives the starting score and the first estimate of the
   run-to-run spread. A task that does not run stops the campaign here, before any agent usage. So does the
   self-test that follows, checks whose answer is known beforehand:
   - the seeds must not all score exactly the same, unless `min_margin` is set: without spread the margin would
     be zero and any gain would be kept (the seed does not reach training, the evaluator does not read what
     the run saved, or the task is deterministic and needs `min_margin`);
   - the evaluator, run a second time on a baseline run, must give the score it gave before, within a tenth
     of the margin (a seed that is not fixed, dropout or sampling left on);
   - the evaluator must give no score for an empty folder (otherwise it measures something other than what
     a run saved);
   - nor for a folder that holds only a run's own records and nothing the run saved (otherwise a run could
     claim its score). The records are what expctl, RunLog and the loop write about a run: `stdout.log`,
     `metrics.jsonl`, `result.json`, `heartbeat.json`, `manifest.json`, `config.json`, `env.json`, `pid.json`,
     `exit.json` and `loop_eval.json`. What a run saves for the evaluator must not carry one of these names.
     An evaluator that opens a path it read from the records, such as the checkpoint path RunLog wrote, is
     stopped here too: that path leads into another folder than the one it was given, so a run could name
     another run's checkpoint. Such an evaluator takes the part of the path below the run's folder and opens it
     inside `{run_dir}`;
   - for a copy of a baseline run whose records state other metric values, the evaluator must give the run's
     score, within a tenth of the margin (the score comes from what the run saved, not from what it reports
     about itself). In the copy every number with a fraction in `metrics.jsonl`, `result.json`,
     `heartbeat.json`, `loop_eval.json` and `stdout.log` is moved by ten margins; in the log that is every
     number written with digits on both sides of a decimal point that is not a piece of a name, a path or a
     version. Whole numbers such as steps stay, except in a JSON record (a file, or a line of a JSON-lines
     file) that holds no number with a fraction at all: its values are whole numbers (`{"correct": 85}`), so
     they are moved, by at least 1. RunLog writes every metric as a number with a fraction, so this concerns
     records a script writes itself. Numbers inside text values of the JSON records stay as well, as do
     files in subfolders, what a checkpoint holds and log files of the project's own: the check catches an
     evaluator that takes a metric from the run's records or its log, not every way in which a run could
     hand it a score. The copy lies in the campaign's folder during the
     check and is a full copy, so that an evaluator that writes into the folder it scores cannot change the
     run: it takes the time and the disk space of the run's files once per start. A folder that an earlier
     attempt left there and that cannot be removed stops the campaign, and nothing is built into it;
   - each run in `loop.controls` must not score better than its floor by more than the margin. A control is a
     training command whose result cannot have learned the task: a constant predictor, an untrained model, a
     model trained on shuffled labels. Its floor is the best score such a run can reach, the bound and not the
     average: for chance-level accuracy on a small split, add the sampling error. A control that beats its
     floor means that the evaluator rewards something other than learning, that held-out data reaches
     training, or that the floor is wrong; one that scores worse passes. Each control is trained once, on the
     first seed, with the budget and sandbox of any run, and uses one run of the run limit. Each control has
     a name of its own.

   A run limit that does not cover one run for each seed and one for each control is refused at the start,
   and at a `resume` as long as the campaign has no baseline. A limit of another kind or a stop request that
   arrives during the baseline or the self-test ends the campaign under its own reason (`limit reached`,
   `stop requested`) and with exit code 0, not as a failed self-test. It leaves no baseline, so `resume`
   trains the baseline and the controls again.
2. Scouting (skip with `--no-scout`): one session with read, write and web tools only writes dated, cited notes to
   `experiments/scouting/DATE-NAME.md`, ending in a `## Hypotheses` list (`- H1: ...`). See `scouting.md`.
3. Iterations, each in a fresh worktree at the best commit so far (`.claude/worktrees/nnloop-NAME`):
   a fresh agent session gets the task, the score to beat, the history (for a change that failed on the first
   seed: both scores), the notes, the untried hypotheses and, when the training script logs with RunLog, a few
   points per metric of one run of the best commit (the session cannot read run folders), and makes one change. The harness commits it on branch `nnloop/NAME`, saves the diff, scans it, trains
   one seed, discards at once if that run is not better than the best so far's run on the same seed, otherwise
   trains the rest and applies the keep rule. The seed that comes first rotates through the panel from one
   iteration to the next, so that one seed on which the best so far was lucky does not turn away every change.
   A gain that just misses the margin is measured on a second seed panel before it is decided. Where
   `search_trials` is set and the change leaves numeric settings open, the harness first trains a few versions
   and goes on with the best one ("A search by the harness" below). Where `restart_after` is set, a campaign
   that keeps nothing for that many iterations goes on from an earlier commit ("A restart when the campaign
   stalls" below).
4. Confirmation, when the campaign ends by a limit, a finished search or repeated failure and something was
   kept: the starting commit and the kept commit are each trained on a fresh panel of as many seeds, drawn at
   that moment, so that no change could have been fitted to them. See "The confirmation" below.

| Status | Meaning |
|---|---|
| `keep` | Better than the best so far by more than the margin; the branch moves to this commit. After a restart (`restart_after`) the change is compared with the commit it started from, and the branch moves only when the new commit also beats the one that was left. |
| `inconclusive` / `discard` | Better within the noise margin (a near-miss: on both seed panels together) / not better. Reverted (the next worktree starts from the best commit). |
| `invalid` | Changed a file outside `editable_paths`, the guard refused a call, a sealed path or token appears in the change or the tool calls, the run exceeded its budget, the evaluator refused what the run saved, or every seed scored exactly the same although earlier panels had spread (the change took the seed's effect away; with a coarse metric and two seeds this can happen by chance, one more reason for three). |
| `crash`, `no_change`, `agent_error`, `duplicate` | The run or evaluator failed; the session changed nothing; the agent ended with an error; the same diff was tried before. |
| `declined` | The session proposed no change and said why. The prompt offers this as an accepted result, because an agent with no way to say "nothing" tends to game the score instead (arXiv 2510.20270 v1: an abort option cut cheating from 54 % to 9 %). It costs no run and is no failure; two in a row end the campaign (with `restart_after`: once there is no earlier commit to go back to). |
| `unfinished` | A limit or a stop arrived during the iteration. |

### The keep rule
A one-sided t-test of the change's mean against the best commit's mean. Its noise is the variance within seed
panels, pooled over the baseline and every change that ran on all seeds, so it steadies as the campaign goes on
(`nnloop status` shows it as `noise`). With three seeds the first change needs a mean gain of 2.3 pooled
deviations (`t` = 2.87); after eight more panels 1.7 (`t` = 2.13). With two seeds the first change needs 4.5:
use three or more.

A near-miss gets a second look. A gain above two thirds of the margin, but not above it, is trained on a second
seed panel, and so is the best so far (once per best commit: later near-misses reuse those runs). The decision
is then taken on all seeds of both, with `noise_mult` raised by a tenth because it is a second chance. It costs
one panel for the change and, the first time, one for the best so far; when the run, time or GPU-hour limits
have no room for that, each run counted at its cut-off, the change stays `inconclusive` and nothing is trained.
The ledger row keeps the first look (`first`), and later changes are compared
with the best so far's mean over all of its runs. A second look late in a campaign can use the runs the
confirmation needs: the confirmation is then `not_run` until a `resume` with a higher run limit. A stop that
arrives while the best so far is trained on the second panel loses those runs: the next near-miss trains them
again.

Simulated on 12 November 2026 (normal noise, three seeds). One comparison, 100,000 trials per cell: a change
without effect is kept in 2.7 % of cases (2.3 % without the second look), a gain of two deviations in 65 % of
cases at the first change and in 74 % after eight earlier panels (44 % and 58 % without). Whole campaigns of 34
runs, 20,000 per cell, ideas drawn from three assumed mixes of harmful, neutral and helpful changes: the true
gain of the commit a campaign ends on was 1.5 to 19 % higher when runs were the limit (the smallest figure is
within the simulation's error) and 14 to 38 % higher when ideas were, and changes without effect were kept no
more often (0.87 % of ideas against 0.90 %), because the best so far is then measured on twice the runs. No alternative did as well in both cases: no first-seed check
(42 % less gain when runs are the limit), slack in that check, a first baseline of twice the size, or training
a kept commit again. These are simulations on the benchmark's measured noise, not results of live campaigns,
and the simulated campaigns had the confirmation's runs set aside from the start. In the one live campaign
since (12 November 2026, 24 runs) a change at 89 % of the margin was kept on six seeds (a gain of 0.0168
against a margin of 0.0130); the confirmation on three fresh seeds, run after a resume, found 0.0067 against
0.0140: `unclear`. A small gain kept at the second look is the kind a three-seed confirmation often cannot
confirm.

Runs are not compared seed by seed. Measured on the benchmark on 12 November 2026 (two commits, eight seeds,
two repeats each): the seed means of the two commits correlated at r = 0.3, no more than runs of unrelated
seeds, so pairing would not shrink the margin. With weight averaging the same seed repeats to within 0.0001,
so training a kept commit again on its seeds adds nothing: only fresh seeds do.

### A search by the harness (`search_trials`)
Added 12 November 2026. Without it the worker picks every number by hand, one guess per iteration. With
`loop.search_trials: K` it may hand numbers to the harness instead: it writes each of them as one line
`NAME = <number>` at the top level of an editable file and adds a search space to `PROPOSAL.json`:

```json
{"title": "retune the optimiser", "hypothesis": "...", "source": "own",
 "search": {"LR": {"low": 1e-4, "high": 1e-2, "log": true}, "LAYERS": {"low": 2, "high": 8, "int": true}}}
```

One to six settings; `log` for a scale such as a learning rate, `int` for whole numbers, each `true` or `false`.
The change may be the search alone or a code change together with the settings it needs.

- The harness trains up to K versions that differ only in those lines. Each range is cut into K equal parts (on
  a log scale where asked) and each part is used once, in shuffled order, so that a handful of trials covers
  every range. On a linear scale every whole number of an `int` range gets the same share of the parts. A
  version whose values repeat an earlier version's is not trained again, so a search over a few whole numbers
  costs fewer than K trials. The values come from a generator seeded with the campaign's name and the
  iteration's number: the same campaign draws the same values again.
- Every version is trained once, on one seed outside both seed panels (with seeds 1, 2, 3: on 7), and scored by
  the frozen evaluator. The seed panel takes no part in the choice, so the best of K versions gets no head start
  in the runs the keep rule tests: a version without effect is kept as rarely as any other change without
  effect. That follows from the design (the choice and the test use different runs) and was not simulated. The
  trial runs do not enter the noise estimate.
- The harness writes the best version's values into the lines and commits them. That commit is the iteration's
  change: first-seed check, seed panel, keep rule, second look and confirmation as for any other change. The
  current values are not a trial of their own: they are the best so far that the winner has to beat.
- The harness reads and writes these lines only in plain files of the worktree. An editable file that is a
  link, lies below a linked folder (a symbolic link or a Windows junction) or has a second name elsewhere (a
  hard link) is not searched, so a setting whose line is only there is `invalid`. The same is checked before
  every write: a file that has become one of these while the versions trained ends the iteration as `invalid`,
  and nothing is written there. The check and the write are two steps; a process that swaps the file in the
  instant between them is not caught.
- The trials are training runs and count against the run limit. A search gets fewer trials when the limit has
  no room for K of them plus the seed panel, and none is offered below two. Until the first keep nothing is
  held back for the confirmation (as for every iteration), so the trials of an early search can use runs that
  the confirmation would need: give a campaign with `search_trials` a run limit with room for both.
- `invalid`, at no cost in runs: a setting without exactly one such line in a plain file, or a search space
  that is not one (more than six settings, a range without two numbers in order, a `log` or `int` that is not
  `true` or `false`). `invalid` after the trials that ran: a file that became a link meanwhile (above).
  `discard`: the best version has the values the code has now and nothing else changed. `duplicate`: the same
  search with the same code change from the same commit. A version that crashes or is cut off has no score; if
  none has one, the iteration ends with the last version's status.
- The ledger row holds `search` (the space), `trials` (values, status, score and run of each) and `values` (the
  best one's); a trial's run carries the tag `values`; later workers and the journal are told what the search
  found.

What it is not. The search is a stratified random search: no model-based optimizer, no pruning, no successive
halving, and Optuna is not used. At a handful of trials the model-based samplers are still in their random
start-up phase, and stopping trials early by rank is the riskiest speed-up (`hpo.md`). One run per version is a
noisy basis for the choice: the search finds a region, and the keep rule decides whether it is a gain. The
values live in the code, not on the command line, because the confirmation and every later iteration train a
commit with the campaign's one `train_command`: a kept commit must carry its numbers. For a search larger than
one iteration's handful of runs, follow `hpo.md` outside the loop.

Why: in the one controlled comparison found, classical optimizers did better inside a fixed numeric space than
a code-editing agent that proposed the values (0.9768 bits per byte for TPE against 0.9814 for the agent, from a
baseline near 0.991; one task, three seeds; see Sources).

Measured here on 13 November 2026: the kit's two benchmark tasks on native Windows with one GPU, the tests'
stand-in agent in the place of a real one, three pairs of campaigns per task, 18 runs each, K = 6 over a learning
rate and a batch size. The two campaigns of a pair got the same versions in the same order, one through the
search and one by hand, a version per iteration. The result of a campaign is the gain that its confirmation on
fresh seeds measured.
- Fine-tuning task (accuracy): every campaign ended with a confirmed gain. With the search 0.47, 0.38 and 0.41,
  by hand 0.30, 0.19 and 0.44; the mean difference is 0.11. That is seven standard errors by the run-to-run
  spread (0.023 per run, 0.015 for the mean difference) and 1.6 by the spread across the three pairs (0.068):
  two pairs differ by 0.18, and in the third both campaigns ended on the same values. At the same run limit
  the search looked at all six versions and the campaigns by hand at three or four, because by hand every
  version that passes the first seed costs a whole seed panel.
- Character model (loss): no campaign kept anything, with or without the search. The starter's values were
  already near the best of the space.

So the search helped where the starting values were a guess and changed nothing where they were already good.
It stays off by default: the rule fixed before the measurement asked for a gain on both tasks. Set it where a
task's numbers have not been tuned. The stand-in shows what the procedure does with given versions, not what a
real agent would have proposed by hand, and three pairs can show a large difference only.

### A restart when the campaign stalls (`restart_after`)
Added 12 November 2026. Without it a campaign is one greedy line: every iteration starts from the best commit
so far, and once the changes on top of that commit stop helping, the rest of the limits is spent there. With
`loop.restart_after: K` the campaign goes back and tries another direction:

- After K iterations in a row without a keep, whatever their status, the next worktree starts from the commit
  before the last keep: the kept change that the stalled iterations built on is left behind. Two sessions in a
  row that decline do the same, where they would otherwise end the campaign. Each restart goes back by one
  keep. At the starting commit there is nothing to go back to: there the campaign goes on until a limit, or
  ends when two sessions in a row decline. `max_failures` failed iterations in a row stop it as before. A
  campaign that was begun with a kit from before 12 November 2026 and is resumed with `restart_after` can go
  back only as far as the first keep after the resume: the earlier keeps were not recorded as steps to return
  to.
- The commit that was left stays the campaign's result until something beats it. The branch stays on it, and
  the limits go on holding the runs of its confirmation. A change on the new line is tested by the keep rule
  against the commit it started from. When it is kept, the branch moves to it only if its mean over the seed
  panel is also better than that of the commit that was left (the panel, because every kept commit has those
  runs). Otherwise it is the tip of a line of its own: later iterations build on it, and it is dropped when
  the campaign stops, with its `diff.patch` as the record.
- However a campaign stops, it rests on the best commit it found: the confirmation compares that commit with
  the start, the journal and `nnloop status` report it, and a `resume` goes on from it.
- The worker reads the history of the code in front of it: the iterations that started from a commit that is
  part of that code. A change that was kept elsewhere stays in the list, marked as not in the code, so that
  the session neither assumes it is there nor repeats it unknowingly. The same diff from the same commit is
  a `duplicate` as before.
- The ledger gets a row `restart` (`iter`, `left`, `commit`, `best`), and every iteration row names the commit
  it started from (`base`). The journal counts the restarts and marks kept changes that are not in the kept
  code.

What it is not. No tree search and no population: one line is worked on at a time, and the campaign returns
to a line it left only when it stops (then to the best one). Choosing the better of two lines on the seed
panel is one more selection on the same seeds; like every keep, it is what the confirmation on fresh seeds is
for. No value of K was tried on real campaigns: a small K gives up a line early, and a K near the number of
iterations that the limits allow never restarts.

Why: in one study of research agents (18 tasks, one model; see Sources) the mean normalised test improvement
was 0.192 for a greedy loop, 0.193 for tree search and 0.208 for an agent that is greedy until it stalls and
then branches: a small difference, in one study. That agent branches from its best few code versions; the kit
goes back one keep on its single line, which fits the loop's one branch and one best commit. Whether a restart
raises what a campaign ends on has not been measured: that needs campaigns long enough to stall, with real
agent sessions, with and without it at an equal run limit.

### The confirmation
Every keep is the best of several tries on the same seeds, so the gain a campaign reports is biased upward, the
more so the more changes it trained. The confirmation is one comparison that was fixed beforehand: start
against kept, both on seeds that no decision has seen, tested against the keep rule's margin. Its verdicts:

| Verdict | Meaning |
|---|---|
| `confirmed` | The gain on fresh seeds exceeds the margin. |
| `unclear` | A gain, within the margin. The confirmation is one look at one panel per commit: with three seeds it confirms a real gain of two deviations only in about half of the cases, so this says "run more seeds before relying on it", not "the change does nothing". |
| `not_reproduced` | No gain on fresh seeds. |
| `not_run`, `unfinished`, `failed` | The limits had no room for it; a limit or a stop arrived during it; one of its runs gave no score, or the kept commit scored exactly the same on every fresh seed while the starting commit did not (one run repeated cannot be tested against noise: read the kept diff). A `resume` runs it again, on newly drawn seeds (after `not_run`: with limits that have room for it). |

Nothing is reverted: the kept commit stays on its branch, and the journal entry and `nnloop status` carry the
verdict, both means, the seeds, and how many changes the campaign trained and kept. The fresh panels join the
pooled noise as the panels of the iterations do. During the confirmation the money and token limits rest,
because it starts no agent session. It uses the validation split like every other run of the loop and does not
replace Phase 5.

## It stops instead of working around
A reached limit · `nnloop stop` · two sessions in a row that decline to propose a change (`search exhausted`;
like a limit and a stop request, it ends with exit code 0; with `restart_after` only where there is no earlier
commit to go back to) · `max_failures` failed iterations in a row · a session with no result within
`agent_timeout_s` · a rate limit or usage cap · usage that would be billed per use when no money limit was given ·
an agent that is not signed in · a model refusal · and every
safeguard: a failed self-test (a new campaign is needed after the fix, since the evaluator and the settings
are frozen for a campaign), a protected file (evaluator, data, harness, dependency pins) whose checksum changed, a ledger that
something else edited, GPUs that differ from the start, a file of the main project that changed during an agent
session, or a session (scouting included) that used tools or changed files while the guard hook left no record
of running. Each stop writes
`state.json` (`stop_reason`), a ledger row and a journal entry; `resume` continues from there. `resume` refuses
when the commands, seeds, budget, interpreter, platform or GPUs differ from the start: begin a new campaign.

## Agents and what each start means
| Agent | Started as | Unattended permissions |
|---|---|---|
| Claude Code | `claude -p --permission-mode dontAsk --tools/--allowedTools Read,Glob,Grep,Edit,Write` (scout: `Write`, `WebSearch`, `WebFetch` instead of `Edit`), `--strict-mcp-config`, `--no-session-persistence`, and `--restricted --settings <worktree>/.claude/settings.json` where the version has it (2.1.303 does), else `--setting-sources project` | An explicit tool list; anything else is refused without a prompt. No shell. Approvals are never bypassed. |
| Codex CLI | `codex exec --json --ephemeral -s workspace-write` | Its sandbox confines writes to the worktree, not reads: it has a shell, so only the guard hook and the transcript scan keep it from files outside the worktree. The project's hooks must have been trusted once (`/hooks`), and Codex fails open when a hook does not load: the loop then stops with "the guard hook did not run". |
| Cursor terminal agent | `-p --force --trust` | Print mode applies edits only with `--force`, which bypasses its approvals. `nnloop` therefore refuses Cursor unless it is told `--in-container`: run it only inside a container that holds no credentials and has restricted network. The flag is your statement; `nnloop` cannot verify it. |

In every case the session runs with `NN_UNATTENDED=1`: the guard denies what it would otherwise ask about, and
denies every file tool aimed outside the project, reads included.

## What is enforced, and where
| Safeguard | Linux with bubblewrap | Windows, macOS, Linux without bubblewrap |
|---|---|---|
| Score from the harness's own evaluator run; evaluator self-test; keep rule; confirmation on fresh seeds; limits; fresh worktree; saved diff; hash-chained ledger | enforced | enforced |
| Evaluator, data, harness files, dependency pins unchanged | checksummed every run and session; main project mounted read-only for the run | checksummed every run and session: a change is caught at the next check, not prevented. On Windows without the symlink privilege `link_paths` are junctions or hard links, so a run that writes through one changes the project's own data |
| The evaluator's environment (interpreter, installed packages) unchanged by a run | not enforced: the run's sandbox keeps the rest of the file system writable; only the project is read-only | not enforced: only the protected paths are checksummed. Keep the evaluator's imports inside `frozen_paths` where a tampered package would matter |
| What the evaluator's process can reach, should a file that a run saved make it run code | no network; the project is read-only for it except the folder it scores and `loop.eval_writable`; sealed data that a `final_eval_commands` entry names and `loop.eval_command` does not (the test set) is hidden from it. The rest of the file system stays writable, as for a run | not confined. On every platform the first protection is the evaluator itself: it loads data formats only (safetensors, JSON, a TorchScript file whose code it has checked, as `benchmarks/charlm/evaluate.py` does) and never unpickles or imports what a run saved |
| Sealed test data out of reach, whatever the pattern that seals it (`data/test/**`, `**/test/**`, `data/*/test.csv`) | absent from the worktree and hidden from the run; guard denies the agent | absent from the worktree; guard denies the agent; a run could still open the main project's copy by absolute path. The change is scanned for that path, for sealed names and for `EXP_PROJECT_ROOT`, the variable that holds the path, and any of them makes the iteration invalid: training code reads its data by relative paths |
| The data the loop scores on, out of the agent's sight | only when `sealed_paths` lists it, which works for a split that training does not read: then it is absent from the worktree and the evaluator, which runs in the main project, still reads it. Otherwise the agent can read it, and `nnloop` says so at start | same |
| No network for the run | enforced (`--unshare-net`) | offline environment variables only, plus a scan of the change for network and process-starting code, which invalidates the iteration |
| Secrets | variables whose names look like secrets are not passed to runs | same |
| Agent stays inside its tool list and the worktree | agent's own permission system + guard hook | same |

Not enforced anywhere: that the agent's one change tests one hypothesis; that scouting notes are accurate.
Leave the project folder alone while a campaign runs: a changed file stops it.

## Records
`experiments/loop/NAME/`: `state.json`, `ledger.jsonl` (every baseline run, control, the self-test, scout, iteration, restart, confirmation and stop; each row
names the hash of the one before), `loop.log`, and per iteration the prompt, transcript, guard record and
`diff.patch`. Each run directory has `loop_eval.json` (the harness's evaluation). The journal gets one entry per
campaign stop. Kept code is on branch `nnloop/NAME`; nothing is merged for you.

## After a campaign
- A campaign's best score was selected among many tries on one validation split, so it is biased upward
  (`uncertainty.md`). Claim the gain that the confirmation measured on fresh seeds, not the one the iterations
  reported. If the journal says the confirmation was not run, unclear or not reproduced, do not claim a gain:
  resume with limits that cover it, or run both commits on more seeds yourself. Then have `experiment-reviewer`
  read the kept diffs and follow Phase 5. The loop never touches the sealed test set.
- Merge `nnloop/NAME` only after that check. Kept changes that only exploit the fixed budget (a smaller model
  that fits more steps into `run_budget_s`) may not transfer to a longer run: test at the real budget.

## Sources
- Keep/revert on a fixed time budget with one editable file: karpathy/autoresearch (README, read 2026-11-11).
- Seed panel with a noise margin, checksummed evaluator and data, fresh worktree, no network, saved diff,
  transcript scan: `docs/research-notes/agent_frameworks_patterns.md` in the kit's repository (sections 2 and 5).
- Agent start-up flags: each vendor's CLI reference, read 2026-11-11.
- Numbers by search, code changes by the agent: https://arxiv.org/abs/2603.24647 (v3, 2026-04-04), opened by a
  research subagent on 2026-11-11 and not cross-checked; `hpo.md` section 8 gives another figure from the same
  paper for its hybrid method (0.9739), and the two readings were not reconciled. Sampling: `hpo.md`
  (quasi-random or random search for up to about 30 trials).
  The design of the search itself (one seed outside the panels, values written into the code) is the kit's own
  and was tested with `tests/test_loop.py` on 2026-11-12. Its effect on training results was measured on the
  kit's two benchmark tasks on 2026-11-13 with a stand-in agent (figures in that section), not with a real one.
- Restart on a stall: https://arxiv.org/abs/2605.17373 (v2, 2026-05-29), opened by a research subagent on
  2026-11-11 and by a second one on 2026-11-12, which read the abstract and the first part of the page itself
  and the method details from a machine summary of the rest; not cross-checked. The design (back by one keep,
  the best commit set aside, a history of the code in front of the worker) is the kit's own and was tested
  with `tests/test_loop.py` on 2026-11-12 with a stand-in agent, not measured on training results.
