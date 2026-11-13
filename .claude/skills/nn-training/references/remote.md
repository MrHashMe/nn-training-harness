# Remote and rented GPUs (`nnremote`)

Checked: 2026-11-11 (Hugging Face Jobs and Buckets documentation and price list of that date, `hf` CLI of
huggingface_hub 2.4.0; OpenSSH). The Hugging Face route is built from documentation and tested against a
stand-in CLI: **it has not been run against the real service.** The ssh route is tested against a stand-in and
was run once for real on 2026-11-11: a 30-second GPU training run launched from native Windows into WSL
(`"exec": ["wsl.exe", "-d", "Ubuntu", "--cd", "~", "--exec", "bash", "-lc"]`), mirrored, scored locally, torn down.
Refresh: run `tests/test_remote.py`; compare the `hf jobs run`, `hf jobs inspect` and `hf buckets` commands in
`scripts/nnremote.py` (class `HfJobs`) with the current CLI reference; read `https://huggingface.co/api/jobs/hardware`
for prices. Before trusting the Hugging Face route with money, run the canary at the end of this file.

`nnremote` below means `python3 .claude/skills/nn-training/scripts/nnremote.py`, run from the project root.
It is optional and does nothing until `.claude/nn-training.json` has a `remote` section.

## What it does
A remote run has an ordinary run directory under `runs/` on this machine (the mirror). A small local controller
process keeps it in step with the run directory on the remote side. So the run contract is the one you know:

    nnremote launch --name NAME --on TARGET [--hours H] [--retries K] [--seed S] [--tag k=v] -- {python} train.py ...
    expctl status | detail RUN | watch RUN | curve RUN | stop RUN        (unchanged)
    nnremote resume RUN [--on TARGET] [--hours H] [--retries K]          continue an ended remote run
    nnremote attach RUN                                                  take control of a run shown as "lost"
    nnremote status                                                      cap, committed dollars, open runs

`{python}` becomes the target's interpreter. From an agent session `launch`, `resume` and `stop` ask for the
user's approval (the guard), and are refused where nobody can be asked. Read-only subagents may run `status` only.

## Enabling it (one step, the user's)
Add a `remote` section to `.claude/nn-training.json`. The file is a guardrail: an agent's edit of it asks.

```json
"remote": {
  "cap_usd": 5.0,
  "env": ["WANDB_API_KEY"],
  "files": ["data/train.bin", "data/val.bin"],
  "targets": {
    "box": {"type": "ssh", "exec": ["ssh", "-o", "BatchMode=yes", "gpu-box"], "dir": "nnremote", "python": "python3"},
    "a10g": {"type": "hfjobs", "flavor": "a10g-small", "image": "<docker image with python and your packages>",
             "bucket": "<your-name>/<bucket>"}
  }
}
```

| Key | Meaning | Default |
|---|---|---|
| `cap_usd` | Most dollars all remote runs of this project may commit, ever. Raise it to allow more. | none: nothing paid starts |
| `env` | Names of the environment variables a remote run receives. Values are read at launch and never stored. | none |
| `files` | Git-ignored files or folders a remote run receives besides the source. Sealed paths are refused. | none |
| `targets.<name>.type` | `ssh` (a machine you can already reach) or `hfjobs` (rented by the hour). | |
| ssh: `exec` | Argument list that runs one command line on the machine. The remote side needs a POSIX shell and Python 3.8+. | required |
| ssh: `dir`, `python` | Where run folders are created (relative to the login directory, or absolute); the interpreter there. | `nnremote`, `python3` |
| ssh: `usd_per_hour` | Set it when the machine costs money: then `--hours` and the cap apply. | 0 (free) |
| hfjobs: `flavor`, `image`, `bucket` | Hardware flavor, Docker image, and a private storage bucket you own. | required |
| hfjobs: `usd_per_hour` | Your own price figure. The higher of this and the provider's listed price is used. | listed price |
| hfjobs: `hf`, `python`, `copy_every_s` | The CLI's argument list, the interpreter in the image, seconds between result copies. | `["hf"]`, `python`, 30 |
| `poll_s`, `unreachable_s`, `max_bundle_mb` | Seconds between syncs; seconds of silence before the controller gives up; size limit of what is sent. | 30, 600, 500 |

For Hugging Face Jobs the user also does, once and outside the kit: install the CLI (`huggingface_hub==2.4.0`)
where `nnremote` can call it, sign in with `hf auth login` on an account that may run Jobs, and create the bucket
(`hf buckets create NAME --private`). The kit never signs in, creates accounts or buckets, or stores a token.

## Money
- A target with a price needs `--hours`. Before anything starts, hours × price is reserved in
  `.claude/state/remote-ledger.jsonl` (a guarded file). If the cap does not cover what is already committed plus
  the reservation, nothing starts and the refusal gives the numbers.
- The job cannot outlive its hours: a Hugging Face job is started with the provider's own `--timeout` of that
  length, the run gets a deadline a little earlier so that it can save, and the controller cancels what is left.
  A run can therefore never cost more than its reservation, and the sum of reservations never passes the cap.
- When a run ends, the ledger books the time used (never more than the reservation). A clock that was set back
  during the run does not shorten it: the controller's own count holds. If the end could not be confirmed, the
  full reservation stays booked.
- The ledger is this harness's upper bound from the listed price, not the provider's invoice. Storage in the
  bucket during a run, and anything started outside `nnremote`, is not in it.
- The cap counts from the ledger. If the file is gone while run directories record earlier paid runs, nothing paid
  starts until the user restores it, or creates an empty one to start the count anew.
- An ssh target has no provider-side time limit: if the controller and the network both fail, the remote process
  runs until its own deadline (set from `--hours`) or its end. Put a shutdown timer on rented machines yourself.

## What travels, and what never does
Sent: the files git tracks or would track (not ignored), the kit's scripts, the config without its `remote`
section, the paths named in `files`, and for a resume the earlier run's directory. Variables: only those named in
`env` (ssh: over the connection's stdin; Hugging Face: as job secrets, by name).
Never sent: sealed paths (naming one in `files` is refused), other git-ignored files such as `.env`, the rest of
`.claude/`, the launching environment. Files git has not been told to ignore still stay at home when their name
looks like a credential (`.env*`, `.netrc`, `*.pem`, `*.key`, `id_rsa*`, `credentials*`, `*secret*`, `*_token.*`,
`service-account*.json`): the launch output and the manifest list them under `not_sent`, and naming one in `files`
sends it. This goes by name only; a secret inside an ordinary source file travels with it. Values of the named variables are not written to the run directory, the
ledger, a log or a command line; the manifest records their names (`remote.sent_env`).
The final evaluation does not run remotely: sealed data stays on this machine. Evaluate the mirrored checkpoint here.

## Preemption and resume
A training script survives preemption when it (1) saves its checkpoint into the run directory (`rl.path(...)`,
then `rl.checkpoint(...)`) and (2) on start continues from `rl.resume_from` when that is set (see `resume.md`).
The mirror receives changed files every `poll_s` seconds, so at most that much work is lost.
- Job gone without an exit record (preempted, cancelled from outside, machine died): the run ends as
  `interrupted`, and with `--retries K` left a new run starts from the mirrored directory, with its own
  reservation. Its manifest names the run it continues (`resume_of`).
- Hours used up: not retried. `nnremote resume RUN --hours H` continues it if you decide to pay for more.
- Target unreachable for `unreachable_s`: the controller exits **without** tearing down or settling, the run shows
  as `lost`, and `supervisor.log` says so. When the target answers again: `nnremote attach RUN`.
- Whole files are copied when they change. Keep few and small checkpoints in the run directory (last and best);
  multi-gigabyte checkpoints make every sync and every resume slow, and count against `max_bundle_mb`.
- The kit's own temporary files (`.<record>.<pid>.<six hex digits>.tmp`) are not mirrored; each is gone a moment
  later. Every file a training script writes is mirrored, whatever its name. A training script may remove a
  folder of its run directory at any time, a rotated checkpoint
  for instance: the copy goes on. Before 2026-11-13 the listing raised under Python 3.8 to 3.11 when a folder
  vanished while it was listed (seen here beside a thread that creates and removes folders), and for a rented
  job that error would have ended the helper and with it the job.

## Teardown
When a run ends (completed, failed, stopped, preempted), the controller pulls a last time and removes what it
created: the run's folder under `dir` on an ssh target, the run's prefix in the bucket for Hugging Face. Nothing
else is touched, and nothing is removed before the last pull is complete. The outcome is in the mirror's
`exit.json` (`remote.teardown`, `remote.usd`, `remote.resumed_as`).

Complete means equal content, not equal size and date: the remote side lists a SHA-256 for every file (an ssh
target computes them at the last pull; a Hugging Face job keeps the list in the bucket as `remote-files.json`,
updated with every file it copies), and the controller compares its mirror with that list. A file that differs is
fetched again; if one still differs, nothing is removed and `remote.teardown` says where it was kept. The reason:
`hf buckets sync` passes over a file of the same size that is not newer than the local copy by more than a second
(huggingface_hub 2.4.0, read at the source on 2026-11-12), and the two dates come from two clocks, so a checkpoint
that keeps its size can stay stale in the mirror. During a run such a file can lag; the last pull corrects it.
One exception: a Hugging Face job without an exit record was cut off (preempted, cancelled, out of time), perhaps
between copying a file and listing it. Its list only says which files to fetch by themselves; the copy in the
bucket is the last there is, so it counts.

## Limits
- A Hugging Face job mounts the whole bucket with write access, not only its run's prefix: the job's code can read
  and change everything in it. Use a bucket that holds nothing but this project's runs.
- Not built: Slurm (`sbatch`) as its own target type, SkyPilot, Modal, machine-shaped rentals (Runpod, Vast.ai,
  Lambda). An ssh target reaches a Slurm login node or a rented VM, but then you manage the allocation or the VM.
- A stop requested while the controller was down is not carried over by `attach`: stop again afterwards.
- A Hugging Face job that is cut off between copying a file and listing its checksum leaves a list that is one
  copy behind. If the sync passed over that same file, the mirror keeps the copy before it (one `copy_every_s`
  older) and the bucket prefix is removed all the same.
- A remote run that was started before a kit upgrade and is picked up with `attach` after it has no checksum list
  (Hugging Face) or does not know the question (ssh): its last pull fails and its remote files are kept. Let
  remote runs end before you upgrade the kit.
- Heartbeat age in `expctl status` includes the sync delay and any clock difference between the machines.
- If `hf jobs run` fails in a way that hides whether a job exists, the reservation stays booked and the job is
  bounded only by its provider timeout. Look for the label `kit_run=<run id>` in your account.
- One network: the controller must stay up on this machine (it is a detached process and survives the session,
  not a reboot or a stopped WSL distro).

## Canary before the first paid run (needs the user's account and authorization)
Cap of $0.10, flavor `cpu-basic`, `--hours 0.05`, a script that logs ten steps and rewrites one file of constant
size at every step. Check: the job shows the label and the timeout in the provider's console, results arrive in
the mirror, that file holds its last content, `expctl stop` ends it, the bucket prefix is gone afterwards, and the
ledger row matches the console's bill within a cent.
