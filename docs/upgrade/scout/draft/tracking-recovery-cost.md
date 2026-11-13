# Tracking, observability, notifications, reproducibility, failure recovery and cost

Scout draft. Checked 11 November 2026 (rows carry `11-11`, year 2026).
Baseline re-checked: the four notes in `docs/research-notes/`, `docs/review-findings.md`, and in the kit `SKILL.md`,
`references/resume.md`, `references/stack.md`, `references/performance.md`, `scripts/expctl.py`, `scripts/runlog.py` (all 23 Oct 2026).

Status codes: **V** Verified on a primary page, repository or package index today. **I** Inferred (search-engine summary of a
primary page, a secondary report, or reasoning from verified facts or from reading the kit's code). **U** Unverified.

Method: read-only web research (search, page fetch, GitHub API) and read-only reading of kit files. Nothing was installed, cloned
or executed, and no local command was run, so every statement about how the kit behaves on the test machine is I until tested.
Query families used: state-of and comparisons; alternatives; limitations and postmortems; benchmarks; awesome and self-hosted
lists; security and failure modes; latest release notes. The shared web-search budget ran out near the end; the last checks were
direct fetches of primary pages. Not read: lines 241 to 313 of `docs/upgrade/scout/sweep/agent-platform/sweep.md`.

## Summary (10 lines)

1. The kit's run directory already is a local-first tracker (manifest, environment, heartbeat, metrics, result, exit, logs). No external tracker showed a validity or reliability gain that justifies making it a default; keep the run directory as the record and let any tracker be an optional mirror that can never block or fail a run.
2. The tracker market moved since the earlier notes: Neptune's hosted service is gone, W&B is now sold as CoreWeave Forge with alerts on paid plans only, MLflow had an exploited server SSRF (fixed in 3.15.0), Aim has had no release for 18 months and ships no Windows wheels. Trackio 0.45.0 is the only local-first option that advanced, and it is still beta.
3. Notifications need about 30 lines of standard library: one POST to a user-supplied URL (ntfy topic, Slack or Discord webhook). The URL is the credential, so it must live outside the repository and outside the agent's write access, and the default message must carry no paths, code or metric names.
4. Agent-native notification differs per product: Claude Code has a `Notification` event and an `http` hook handler; Codex has `notify` (one event, and its payload contains the user's messages); Cursor hooks run commands only. Claude Code `--bare` skips hooks, so nothing safety-relevant may depend on a hook.
5. Agent spend can only be limited by harness code outside the agent, with one adapter per product: Claude Code reports estimated dollars and tokens and has `--max-budget-usd` (it can overshoot and ignores totals restored on resume); Codex reports tokens per turn and no cost; Cursor's headless output reports neither.
6. Probable native-Windows defect (inferred from code and Microsoft documentation, not tested): `expctl stop` sends CTRL_BREAK from a different console than the training process, which Windows does not deliver. A stop-request file polled by `runlog.should_stop()` fixes this on every platform and also serves budget cut-offs and preemption notices.
7. Other Windows and WSL2 facts that change design: the NVIDIA driver can spill into system RAM instead of raising out-of-memory (a silent slowdown), a driver timeout reset purges GPU memory, and WSL2 does not support all NVML queries (utilization and compute processes are named).
8. Per run the kit records code state and library versions, but no full environment lock, no data fingerprint, no driver version and no container digest. All can be captured with the standard library plus tools already present (`uv export`, `pip freeze`, `hashlib`, `nvidia-smi`). Checkpoint loading is a trust boundary (`weights_only`).
9. `references/resume.md` is still correct. Missing: safe loading, in-run disk checks, preemption notices, the Windows stop and replace behaviour, and a note that the `torchdata` release it names dates from February 2025.
10. Monitoring evidence favours few, duration-aware alerts plus a log-based failure classifier: curve-level detectors caught 2 of 20 reproduced silent training errors, exit codes alone classify failures badly (macro-F1 0.133 against 0.997 for ordered log rules in one preprint), and low GPU utilization is common and mostly fixable. Money limits should rest on wall-clock time times a recorded price; power readings are estimates.

## Q1. Trackers, dashboards and notifications

### 1.1 What the run directory already provides (local read, I, 11-11)

Per run the kit writes `manifest.json` (command, seed, snapshot hash, git commit and dirty flag, patch up to 5 MB, deadline),
`env.json` (Python, platform, argv, source hash, torch versions, determinism flags), `heartbeat.json` (step, latest metrics, best,
last checkpoint, `throughput_steps_per_s`, `gpu_mem_gb`, non-finite count), `metrics.jsonl`, `result.json`, `exit.json` and
`stdout.log`. `expctl status`, `watch --until alert` and `curve` (with `last20pct_trend`) read them. That is the storage half of a
tracker: offline, plain files, no vendor schema. Missing compared with a tracker: overlaid curves in a browser, system-metric time
series, media logging, remote viewing, and alerts that leave the terminal.

### 1.2 Trackers

| Claim | Status | Checked | Source |
|---|---|---|---|
| Trackio 0.45.0 (2 Nov 2026; 0.44.0 on 27 Oct), MIT, Python >= 3.10, local SQLite store, optional sync to a Hugging Face Space. README still says beta and that the database schema may change. 0.45.0 adds `TRACKIO_HANDLE_SIGTERM`, moves to `httpx2`, drops `gradio_client`, needs `huggingface-hub` >= 1.31.0. | V | 11-11 | https://github.com/gradio-app/trackio/releases , https://pypi.org/project/trackio/ |
| Trackio alerts (docs v0.45.0): `trackio.alert(title, text=None, level=AlertLevel.WARN, webhook_url=None)`; levels INFO, WARN, ERROR; printed, stored in the database, shown in the dashboard, optionally posted to a webhook (Slack, Discord or generic JSON) from a background thread; `TRACKIO_WEBHOOK_URL`, `TRACKIO_WEBHOOK_MIN_LEVEL`; read back with `trackio get alerts --project P --json --since <ts>`. Works with no network when no webhook is set. | V | 11-11 | https://huggingface.co/docs/trackio/alerts |
| MLflow 3.18.0 (3 Nov 2026), Apache-2.0, Python >= 3.10. Local file or SQLite store works offline; the UI is a server process. | V | 11-11 | https://pypi.org/project/mlflow/ |
| MLflow server security in 2026: CVE-2026-64849 (unauthenticated SSRF in webhook delivery, CVSS 9.3, listed as exploited on 19 Aug 2026, fixed in 3.15.0, no 2.x backport); CVE-2026-2033 (path traversal to code execution); CVE-2026-2652 (authentication bypass); CVE-2026-118626 fixed in 3.16.0. | I | 11-11 | https://www.securityweek.com/mlflow-vulnerability-exploited-for-cloud-credential-theft/ , https://access.redhat.com/security/cve/CVE-2026-2033 |
| W&B client `wandb` 0.31.0 (16 Oct 2026), MIT, Python >= 3.10. The W&B pricing URL now redirects (301) to CoreWeave; the product is sold as "CoreWeave Forge". Free: 5 seats, 5 GB/month storage. Pro from $60/month. Slack and email alerts are Pro and Enterprise only; private hosting is Enterprise only. | V | 11-11 | https://pypi.org/project/wandb/ , https://coreweave.com/forge-pricing |
| W&B offline: `WANDB_MODE=offline`, later `wandb sync DIR`; an online run retries while the program runs; `wandb.init()` contacts the service. Guidance: under 1,000 `log()` calls per minute. | V | 11-11 | https://docs.wandb.ai/support/models/articles/what-happens-if-internet-connection-is-l.md , https://docs.wandb.ai/guides/track/limits |
| Reports that `wandb.init()` or `wandb sync` can hang without a network. | U | 11-11 | third-party posts only |
| TensorBoard 2.21.0 (29 Jun 2026), Apache-2.0, Python >= 3.9. A viewer for event files: no alerts, no result table. | V | 11-11 | https://pypi.org/project/tensorboard/ |
| Aim 3.29.1 (8 May 2025), Apache-2.0. Wheels for Linux and macOS only, none for Windows; no release for 18 months. | V | 11-11 | https://pypi.org/project/aim/ |
| ClearML SDK 2.2.0 (3 Nov 2026), Apache-2.0. | V | 11-11 | https://pypi.org/project/clearml/ |
| ClearML's server is SSPL-licensed and needs several services. | I | 11-11 | secondary comparisons |
| Comet client `comet_ml` 3.58.11, MIT, Python >= 3.8; hosted service with an account. Release date not read. | V | 11-11 | https://pypi.org/pypi/comet-ml/json |
| DVCLive 3.49.1, Apache-2.0, Python >= 3.9; writes metrics as files beside the code. Release date not read. | V | 11-11 | https://pypi.org/pypi/dvclive/json |
| Neptune's hosted service was reported shut down on 5 Mar 2026 after its acquisition; today the site fails with an expired TLS certificate (direct observation). | I | 11-11 | https://neptune.ai/ (fetch failed), secondary reports |
| Small trackers seen only in listings (mlop, Guild AI, SwanLab). | U | 11-11 | listings |
| No independent benchmark of logging overhead covers Trackio. The one benchmark found (MLtraq, April 2024, written by the author of a competing tool) ranks W&B and MLflow slowest for scalar logging. | I | 11-11 | https://mltraq.com/benchmarks/speed/ |

Reading: an account-bound tracker can vanish (Neptune) or change owner and price tiers (W&B) inside a year, and a tracker server is
attack surface (MLflow). None of the trackers adds validity checks. The use that remains is viewing curves side by side. For that,
Trackio is the only candidate that is local, maintained and installs on Windows; its schema is not stable, so it must be a mirror
written from `runlog`, never the record. If a repository already uses MLflow, W&B or TensorBoard, mirror to it (the rule already in
`stack.md`), with MLflow pinned to 3.16.0 or later and bound to localhost, and W&B allowed to run offline.

### 1.3 Notification services

| Claim | Status | Checked | Source |
|---|---|---|---|
| ntfy server v2.37.2 (4 Nov 2026). Publishing is a plain HTTP PUT or POST to a topic URL with no sign-up; "topic names are public, so it's wise to choose something that cannot be guessed easily"; messages are cached 12 hours by default; a self-hosted server can restrict topics (`ntfy access`). | V | 11-11 | https://github.com/binwiederhier/ntfy/releases , https://docs.ntfy.sh/ |
| The hosted ntfy.sh service logs topic names and IP addresses (privacy policy dated 15 Jun 2026). | I | 11-11 | search summary of the policy |
| Slack incoming webhook: POST JSON with `text`; "Your webhook URL contains a secret"; Slack "actively searches out and revokes leaked secrets"; one URL is bound to one channel. | V | 11-11 | https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/ |
| Discord webhook: POST to `/webhooks/{webhook.id}/{webhook.token}`; webhooks "do not require a bot user or authentication to use"; content up to 2,000 characters. | V | 11-11 | https://docs.discord.com/developers/resources/webhook |
| Apprise 2.2.0 (8 Nov 2026), BSD-2-Clause, Python >= 3.9; one API for about 200 services (ntfy, Pushover, Slack, Discord, Telegram, email). | V | 11-11 | https://pypi.org/project/apprise/ |
| Pushover: POST to `https://api.pushover.net/1/messages.json` with `token`, `user`, `message`; HTTPS required; 1,024 characters per message; 10,000 messages per month free per user account. | V | 11-11 | https://pushover.net/api |
| Pushover app price and licence terms. | U | 11-11 | not checked |

### 1.4 Agent-native notification

| Claim | Status | Checked | Source |
|---|---|---|---|
| Claude Code v2.1.322 (10 Nov 2026). `Notification` hook event with matchers that include `permission_prompt`, `idle_prompt`, `agent_needs_input`, `agent_completed`, and three `quota_auto_resume_*` values. | V | 11-11 | https://github.com/anthropics/claude-code/releases , https://code.claude.com/docs/en/hooks |
| Claude Code `http` hook handler: `url`, `headers` (environment variables are interpolated only when named in `allowedEnvVars`), `onFailure` (`continue` by default, `block` from v2.1.295), `timeout` (default 600 s); the body is the hook's JSON input. Settings `allowedHttpHookUrls` and `httpHookAllowedEnvVars` restrict it. | V | 11-11 | https://code.claude.com/docs/en/hooks |
| `StopFailure` matchers include `rate_limit`, `overloaded` and `billing_error`; `SessionEnd` hooks share a 1.5 s budget by default. `--bare` skips hooks, and the documentation says it will become the default for `-p`. | V | 11-11 | https://code.claude.com/docs/en/hooks , https://code.claude.com/docs/en/headless |
| Whether `Notification` fires in `-p` (headless) runs. | U | 11-11 | not stated in the documentation |
| Claude Code mobile push through Remote Control: v2.1.110 or later, the mobile app signed in to the same account, and the `/config` option "Push when Claude decides". | V | 11-11 | https://code.claude.com/docs/en/remote-control |
| Reports of Remote Control pushes not arriving. | U | 11-11 | issue reports only |
| Codex CLI 0.167.0 (6 Nov 2026). `notify = ["python3", "/path/to/notify.py"]` runs a program on supported events, "currently only `agent-turn-complete`", with one JSON argument: `type`, `thread-id`, `turn-id`, `cwd`, `input-messages`, `last-assistant-message`. | V | 11-11 | https://github.com/openai/codex/releases , https://learn.chatgpt.com/docs/config-file/config-advanced |
| Codex `tui.notifications`, `tui.notification_condition` (`unfocused` by default, or `always`), `tui.notification_method` (`auto`, `osc9`, `bel`); hook events include `SessionEnd`, `Stop`, `PermissionRequest`; only command and MCP-tool handlers run. | V | 11-11 | https://learn.chatgpt.com/docs/config-file/config-reference |
| Whether `notify` runs under `codex exec`. | U | 11-11 | not stated |
| Cursor hooks: 21 events (among them `sessionEnd`, `stop`, `afterShellExecution`); handler types are `command` and `prompt` only, no HTTP type; `sessionEnd` input has `reason`, `duration_ms`, `final_status`, `error_message`; no hook payload carries token or cost fields. | V | 11-11 | https://cursor.com/docs/hooks |
| Reports that `stop` and `afterAgentResponse` do not fire reliably in the Cursor CLI. | U | 11-11 | forum posts only |

### 1.5 Privacy cost and what follows

- A notification leaves the machine and is stored by a third party (ntfy.sh caches 12 hours and logs topic and IP; Slack and
  Discord keep messages). Run names, tags, metric names and paths often reveal the project. Default message: run id, state and
  one number; richer text only by explicit setting. (I)
- The URL is the credential for ntfy topics, Slack and Discord webhooks. It must come from an environment variable or a file
  outside the repository and outside the snapshot, and must never be written to `manifest.json`, logs or the journal. (I, from V rows)
- In unattended mode a notifier is an outbound channel. If the agent can change the URL or the message body, it can send data
  out. The URL and the message template must be fixed by the user before the loop starts and not writable by the agent. (I)
- The Codex `notify` payload contains the user's messages and the last assistant message. A notifier script must not forward the
  payload as it is. (V for the payload, I for the consequence)
- A notifier must have a short timeout (a few seconds), run after state is saved, and never raise into the run or the
  controller. Claude Code's `http` hook default timeout is 600 s, so set it explicitly. (I)
- The controller, not the training script, should send notifications: it already holds the alert logic, and it keeps network
  code out of the training process. Events worth a push: run finished, run failed with a class, a limit reached, the loop
  stopped, a preemption. Everything else stays in `expctl status`. (I)

## Q2. Reproducibility and provenance

### 2.1 What to record per run

| Item | In the kit today (local read, I) | Gap | Cheapest capture |
|---|---|---|---|
| Code state | snapshot hash, git commit, dirty flag, patch up to 5 MB | flag when the patch was cut at 5 MB | none needed |
| Environment | Python, platform, torch versions, determinism flags | no full package list, no lock hash | `uv export --frozen --format requirements.txt` when `uv.lock` exists, otherwise `python -m pip freeze --all`; store the text and its SHA-256 |
| Data | nothing implemented | no fingerprint | hash of a sorted listing (relative path, size, modification time) for every run; full content hash once per dataset version, cached; dataset id and revision for hub datasets |
| Seeds | seed in manifest, seed-mismatch alert | none | none needed |
| Hardware and driver | host, platform and assigned GPUs in the manifest; torch device names in `env.json`; the driver version is read only by the environment report (`expctl.py` line 1884) | driver version, GPU memory size, CPU and RAM not stored per run | copy the fields the environment report already collects into the manifest at launch |
| Container | nothing | no image digest | record the image reference with digest (`name@sha256:...`) that the launcher used; from inside a container it cannot be read reliably |
| Parent run | `--tag parent=<run id>` on resume | none | none needed |

### 2.2 Environment capture

| Claim | Status | Checked | Source |
|---|---|---|---|
| PyTorch 2.15.0 was released on 28 Oct 2026 and needs Python >= 3.11; the "stable" documentation is 2.15. | V | 11-11 | https://pypi.org/project/torch/ |
| uv 0.13.7 (3 Nov 2026). `uv export --format` writes `requirements.txt`, `pylock.toml` or a CycloneDX 1.5 SBOM; `uv.lock` remains the source of truth. | V | 11-11 | https://pypi.org/project/uv/ , https://docs.astral.sh/uv/concepts/projects/export/ |
| pip 26.3: `pip lock` is still marked experimental and writes `pylock.toml` (PEP 751); `pip inspect` (since 22.2) prints a JSON report of the installed environment. | V | 11-11 | https://pip.pypa.io/en/stable/cli/pip_lock/ , https://pip.pypa.io/en/stable/cli/pip_inspect/ , https://peps.python.org/pep-0751/ |
| A lock file describes what should be installed; `pip freeze` or `pip inspect` describes what is installed. A run record needs the second, plus the hash of the first when it exists. | I | 11-11 | reasoning from the rows above |

### 2.3 Determinism

| Claim | Status | Checked | Source |
|---|---|---|---|
| `torch.use_deterministic_algorithms(True)` plus `CUBLAS_WORKSPACE_CONFIG=:4096:8` (or `:16:8`); deterministic operations "tend to have worse performance"; results can still differ across releases, platforms and devices. | V | 11-11 | https://pytorch.org/docs/stable/notes/randomness.html |
| A measured slowdown figure that can be trusted. None found; forum reports range from no cost to several times slower. | U | 11-11 | no primary measurement |
| DataLoader order is reproducible only with a seeded `generator` and `worker_init_fn`; on Windows workers are spawned, so the entry point needs `if __name__ == '__main__':`. | V | 11-11 | https://docs.pytorch.org/docs/2.15/data.html |

Consequence: record the determinism flags per run (already done) and treat "deterministic mode" as a hypothesis with a local cost
measurement on the user's model (two short runs, compare steps per second). Do not make it a default.

### 2.4 Checkpoint loading is a trust boundary

| Claim | Status | Checked | Source |
|---|---|---|---|
| `torch.load` defaults to `weights_only=True` in 2.15; the documentation says never to load data from an untrusted source; extra types are allowed with `torch.serialization.add_safe_globals()`. | V | 11-11 | https://docs.pytorch.org/docs/2.15/generated/torch.load.html |
| CVE-2025-32434: code execution through `torch.load` even with `weights_only=True` in torch <= 2.5.1, fixed in 2.6.0. | V | 11-11 | https://nvd.nist.gov/vuln/detail/CVE-2025-32434 |
| safetensors 0.8.0, Apache-2.0, Python >= 3.10: a weights-only file format without pickle. It stores tensors, not optimizer or random-generator state. Release date not read. | V (version), I (scope) | 11-11 | https://pypi.org/pypi/safetensors/json |

Consequence for the kit: resume checkpoints written by the kit's own runs may be loaded with `weights_only=True` plus an explicit
allow-list; a checkpoint from anywhere else (hub download, another user) is untrusted input. A resume that needs
`weights_only=False` is a finding the guard or reviewer should flag.

### 2.5 Provenance and signing standards

| Claim | Status | Checked | Source |
|---|---|---|---|
| `model-signing` 1.1.1 (10 Oct 2025), Apache-2.0, Python >= 3.9: CLI and API to sign and verify a model directory with Sigstore (default), a key or a certificate. No release for 13 months. | V | 11-11 | https://pypi.org/project/model-signing/ |
| OpenSSF Model Signing specification (June 2025) and adoption by a large model catalog (July 2025). | I | 11-11 | https://blog.sigstore.dev/model-transparency-v1.0 |
| SLSA v1.2 is the approved specification, with Build and Source tracks. | V | 11-11 | https://slsa.dev/spec/ |
| CycloneDX 1.7 (21 Oct 2025), published as ECMA-424 (10 Dec 2025), covers machine-learning models. | V | 11-11 | https://cyclonedx.org/specification/overview/ |
| Current versions of the SPDX AI profile and of Croissant. | U | 11-11 | not checked |

Reading: these standards answer "who built this artifact and from what" for people who receive a model. Inside one repository
on one machine the run directory already answers that. Signing becomes useful at the moment a model leaves the machine
(hub upload, hand-over). Keyless Sigstore signing needs a network identity, so it is optional by rule. A plain SHA-256 of
the final checkpoint in `result.json` costs nothing and gives the later signing step something to bind to.

## Q3. Failure recovery

### 3.1 Signals and preemption

| Claim | Status | Checked | Source |
|---|---|---|---|
| On Windows, `signal.signal()` accepts only SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM and SIGBREAK; handlers run in the main thread. | V | 11-11 | https://docs.python.org/3/library/signal.html |
| `os.kill` on Windows: CTRL_C_EVENT and CTRL_BREAK_EVENT "can only be sent to console processes which share a common console window"; any other value ends the process through TerminateProcess with no handler. | V | 11-11 | https://docs.python.org/3/library/os.html |
| `GenerateConsoleCtrlEvent`: "Only those processes in the group that share the same console as the calling process receive the signal." | V | 11-11 | https://learn.microsoft.com/en-us/windows/console/generateconsolectrlevent |
| `DETACHED_PROCESS`: "the new process does not inherit its parent's console". `CREATE_NEW_PROCESS_GROUP`: CTRL+C is disabled for the group; the group exists so CTRL+BREAK can be sent to it. | V | 11-11 | https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags |
| AWS Spot: interruption notice two minutes before stop or terminate, through instance metadata (`spot/instance-action`) and EventBridge, best effort; hibernation starts at once. | V | 11-11 | https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-termination-notices.html |
| Google Cloud Spot: `preempted` metadata value turns TRUE, then a soft-off signal; the shutdown period is best effort and up to 30 s; a longer notice (`--preemption-notice-duration=120s`) is in preview. | V | 11-11 | https://docs.cloud.google.com/compute/docs/instances/spot |
| Azure Spot: eviction "with 30-seconds notice"; Scheduled Events are "delivered on a best effort basis up to 30 seconds prior"; eviction policy Deallocate (default, disks keep billing) or Delete. Page dated 6 Feb 2026. | V | 11-11 | https://learn.microsoft.com/en-us/azure/virtual-machines/spot-vms |
| Slurm preemption: SIGCONT and SIGTERM, then SIGKILL after the grace time; an earlier warning with `--signal=B:USR1@120`. | I | 11-11 | https://slurm.schedmd.com/preempt.html (through summaries) |
| Claude Code headless on SIGTERM: exit code 143, stops the process tree of running shell commands, runs `SessionEnd` hooks; `-p` waits up to 10 minutes for background work and stops background work when `--max-budget-usd` is reached. | V | 11-11 | https://code.claude.com/docs/en/headless |

### 3.2 Probable defect: graceful stop on native Windows (I, needs a local test)

Code read: `expctl launch` starts the supervisor with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` (`expctl.py` line 1439); the
supervisor starts the training process with `CREATE_NEW_PROCESS_GROUP` (line 1516); on Windows `expctl stop` does not signal the
supervisor and calls `os.kill(pid, CTRL_BREAK_EVENT)` from its own process (lines 1584 to 1592 and 401 to 404);
`runlog.should_stop()` reads only the signal flag and the run's own deadline (`runlog.py` lines 431 to 436).

With the two Microsoft statements in 3.1, the training process cannot share the console of the `expctl stop` process, because
its parent has no console. Expected behaviour: `expctl stop` either fails or reports success while the run continues, and the
supervisor's own stop after deadline plus grace also cannot deliver CTRL_BREAK, so it ends with `taskkill /T /F` after
`kill_after_s`: no final checkpoint. The run's own deadline still works, because `should_stop()` checks the clock itself. A
second possible effect: the training process may open a visible console window, because the supervisor passes neither a hidden
console nor `CREATE_NO_WINDOW`. `BASELINE.md` shows these paths have never run on native Windows (launch fails earlier).

Smallest fix that also serves the other goals: a stop-request file. `expctl stop` already writes `stop.json` when `--kill-after`
is given. Make it always written, let `runlog.should_stop()` look for it at most once per second, and let the supervisor start
its kill timer when it appears. The same file is the single way to say "save and exit" for the user, a budget limit in the
unattended loop, a low-disk check and a cloud preemption notice, on Linux, Windows, WSL2 and inside containers with a shared
volume. Signals remain a faster path where they work.

### 3.3 Atomic checkpoint writes and retention

| Claim | Status | Checked | Source |
|---|---|---|---|
| `os.replace`: "If successful, the renaming will be an atomic operation (this is a POSIX requirement)"; it can fail across file systems. `os.rename` on Windows fails when the destination exists. `os.fsync` on Windows calls `_commit()`; flush first. | V | 11-11 | https://docs.python.org/3/library/os.html |
| On Windows `os.replace` can fail with a permission error while another process holds the destination open (a reader, an indexer, a virus scanner); the Python documentation promises atomicity for POSIX only. | I | 11-11 | reasoning; not in the documentation |
| `runlog._write_json` does tmp, flush, fsync, `os.replace`; heartbeat writes swallow `OSError`, so a failed replace does not stop a run, but the temporary file is left behind. `RunLog.checkpoint()` only records a path; saving and retention are left to the training script. | I | 11-11 | local read of `runlog.py` lines 74 to 84, 376, 414 to 417 |

What a helper in `runlog` should do (I): check free space against about twice the size of the last checkpoint; write to a
temporary name in the same directory; flush and fsync; replace `last`; retry the replace a few times on a permission error;
copy or hard-link to `best` when the metric improved; delete an older periodic checkpoint only after the new file is in place;
record path, step, size and SHA-256 in the heartbeat. Never delete `last` before the new `last` exists.

### 3.4 Exact resume

| Claim | Status | Checked | Source |
|---|---|---|---|
| The latest `torchdata` release is still v0.11.0 (21 Feb 2025), although the repository has commits up to 9 Nov 2026 and moved from `pytorch/data` to `meta-pytorch/data`. 0.11.0 fixed `StatefulDataLoader` restart behaviour at the end of an epoch. | V | 11-11 | https://github.com/meta-pytorch/data/releases/tag/v0.11.0 |
| `resume.md` lists the right contents (model, optimizer, scheduler, gradient scaler, counters, best metric, Python, NumPy, CPU and CUDA random states, data position) and the right procedure (resume as a new run with a parent tag, verify the boundary, exact equality only under deterministic settings). | I | 11-11 | local read; nothing found that contradicts it |

Without `torchdata`: seed the sampler from `(seed, epoch)`, checkpoint at epoch boundaries or store the number of batches
consumed and skip that many on resume. This reproduces the order but replays data loading for the skipped part. (I)

### 3.5 Disk

No external evidence was gathered beyond the kit's own rule. The kit checks free space at launch and in `status`
(`min_free_disk_gb: 20`), not during a run and not before a checkpoint write (local read, I). A full disk during `torch.save`
leaves a partial temporary file; with the write order in 3.3 the previous `last` survives. Add the check before each save and
in the controller's watch loop, and let it write the stop-request file when space falls below the limit. (I)

### 3.6 Out-of-memory

| Claim | Status | Checked | Source |
|---|---|---|---|
| The exception object holds a reference to the stack frame where the error was raised, so memory is not freed inside the handler: "move your OOM recovery code outside of the `except` clause". | V | 11-11 | https://docs.pytorch.org/docs/2.15/notes/faq.html |
| Windows: driver 536.40 introduced a fallback from GPU memory to system RAM instead of an out-of-memory error, much slower; from 546.01 the NVIDIA Control Panel has "CUDA - Sysmem Fallback Policy" with "Prefer No Sysmem Fallback". Article updated 31 Oct 2023. | V | 11-11 | https://nvidia.custhelp.com/app/answers/detail/a_id/5490 |
| Whether this policy can be read without the control panel, and its default on the test machine's driver. | U | 11-11 | not checked |

Consequence: on native Windows a batch that is too large can show up as a collapse in steps per second with GPU memory at the
limit, not as an error. The kit's memory ladder in `performance.md` assumes an error. A throughput-drop alert (Q5) covers it;
the kit must only advise the setting, never change it (system setting).

### 3.7 GPU faults

| Claim | Status | Checked | Source |
|---|---|---|---|
| NVIDIA Xid catalogue (page updated 4 Nov 2026). Kernel log form: `NVRM: Xid (PCI:0000:5a:00): 79, GPU has fallen off the bus.` Suggested actions: 13 and 31 restart the application (usually application faults); 43 ignore; 48 (double-bit ECC), 62, 64, 95, 109, 119, 120, 140 reset the GPU; 79 restart the machine; 94 restart the application. No Windows guidance on that page. | V | 11-11 | https://docs.nvidia.com/deploy/xid-errors/analyzing-xid-catalog.html |
| Windows timeout detection and recovery: default timeout two seconds; on recovery the video memory manager "purges all allocations from video memory"; the user sees "Display driver stopped responding and has recovered", logged in the Event Viewer. Page dated 5 Nov 2025. | V | 11-11 | https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery |
| PyTorch Windows FAQ: a "driver shut down" error calls for a driver update or changed timeout settings; CUDA IPC is "not supported on Windows". | V | 11-11 | https://docs.pytorch.org/docs/2.15/notes/windows.html |
| Event log provider and event numbers for a display driver reset, and whether `wevtutil` can read them without elevation. | U | 11-11 | not checked |
| CUDA on WSL guide v13.5 (2 Nov 2026): "Not all NVML queries are supported, including GPU utilization and active compute processes"; pinned memory is limited and "Some deep learning training workloads can exceed the limit and fail". | V | 11-11 | https://docs.nvidia.com/cuda/wsl-user-guide/index.html |
| A 2.5-year study of a large A100 and H100 cluster found GPU memory far more reliable than other GPU hardware (over 30 times by mean time between errors). | I | 11-11 | https://arxiv.org/abs/2503.11901 (through summaries) |

Consequence: after a GPU reset the CUDA context is gone; the only recovery is to end the process and resume from `last` in a
new run. The controller can attach a cause by scanning the kernel log (Linux) for `NVRM: Xid` lines near the failure time, read
only and best effort. On one workstation GPU the common codes are the application-level ones (13, 31, 43), so an Xid line is
first a hint to look at the code. `expctl gpu_info()` asks for utilization and compute-process ids; under WSL2 these may come back
empty, which would silence the "GPU shared by more than one run" check and any utilization alert (I, needs a local test).

### 3.8 Hung data loaders and watchdogs

| Claim | Status | Checked | Source |
|---|---|---|---|
| DataLoader `timeout`: "if positive, the timeout value for collecting a batch from workers" (default 0, wait forever). | V | 11-11 | https://docs.pytorch.org/docs/2.15/data.html |
| `faulthandler.dump_traceback_later(timeout, repeat, file, exit)` uses a watchdog thread and works on every platform; `faulthandler.register()` is "Not available on Windows"; `faulthandler.enable()` covers SIGSEGV, SIGFPE, SIGABRT, SIGBUS, SIGILL and Windows exceptions. | V | 11-11 | https://docs.python.org/3/library/faulthandler.html |
| py-spy 0.4.3 (2 Nov 2026), MIT, wheels for Linux, macOS and Windows; dumps the stack of a running process from outside. Privileges needed on Windows not checked. | V (version), U (privileges) | 11-11 | https://pypi.org/project/py-spy/ |

Consequence: the kit detects a stall (heartbeat older than `heartbeat_stale_seconds`) but cannot say where the process is stuck.
`runlog` can arm `faulthandler.dump_traceback_later(stale_seconds, file=<run dir>/hang.txt)` and re-arm it at every heartbeat; a
stall then leaves the stack of every thread in the run directory, with no dependency and no signal, on Windows too.

### 3.9 Failure classification

| Claim | Status | Checked | Source |
|---|---|---|---|
| GPUAlert preprint (July 2026, authors anonymous, not peer reviewed): a wrapper that watches output and exit status; 15 failure classes with ordered first-match patterns; macro-F1 0.997, against 0.830 for unordered keyword matching and 0.133 for exit-code inspection, on 360 logs from one V100 (three classes synthetic); 23 of 24 logs from the wild; about 3 ms overhead; mail credentials kept in plain text; no licence stated. | V (as reported) | 11-11 | https://huggingface.co/papers/2607.01409 |
| Microsoft study of 4,960 failed deep-learning jobs: 48.0 percent of failures arise in the interaction with the platform, not in the model logic; an earlier cluster study: about 30 percent of jobs fail, mostly early and from programming errors. | I | 11-11 | ICSE 2020 paper and https://arxiv.org/abs/1901.05758 (through summaries) |

Consequence: `exit.json` carries a return code and little else. A small ordered list of patterns over the last lines of
`stdout.log` (out of memory, CUDA device lost or Xid, disk full, killed, non-finite, import or attribute error, data-loader worker
died, timeout, file not found) gives the agent and the journal a failure class. The class also decides whether an automatic
retry makes sense (preemption, device lost) or not (code error). Retries need a cap, or they consume the budget. Log text is
data: a classifier matches patterns and must never treat log lines as instructions.

### 3.10 Re-check of `references/resume.md`

Still correct (see 3.4). To add, each with the source above:
1. Loading: `weights_only=True` with an allow-list; untrusted checkpoints; minimum torch 2.6.0 (2.4).
2. Stop requests through the stop file, and the Windows signal limits (3.1, 3.2).
3. The write order and the Windows replace retry; the free-space check before each save; never delete `last` first (3.3, 3.5).
4. Preemption notices: 30 s to 2 min, best effort, so the time-based checkpoint interval is what bounds the loss (3.1).
5. `StatefulDataLoader`: say that the release is 0.11.0 from February 2025 and that the repository moved; give the
   dependency-free alternative (3.4).
6. Out-of-memory recovery outside the `except` block, and the Windows fallback to system RAM (3.6).
7. A GPU reset or lost device cannot be recovered in the process: exit and resume (3.7).

## Q4. Cost accounting

### 4.1 GPU-hours and energy

| Claim | Status | Checked | Source |
|---|---|---|---|
| The kit records start and end times per run (`pid.json`, `exit.json` with `duration_s`) but keeps no total and enforces no limit; `SKILL.md` section 5 gives budget advice only. | I | 11-11 | local read |
| `nvidia-smi` reports average power (last second, Ampere or newer) and instantaneous power. Exact query field names were not confirmed without running the tool. | V (existence), U (names) | 11-11 | https://docs.nvidia.com/deploy/nvidia-smi/index.html |
| NVML has a total energy counter in millijoules since the driver was loaded. `nvidia-ml-py` 13.615.71 (25 Sep 2026), BSD, published by NVIDIA. | V | 11-11 | https://pypi.org/project/nvidia-ml-py/ , NVIDIA binding documentation |
| A measurement study on more than 70 GPU models: the error is about 5 percent of the reading, not 5 W; on some data-centre GPUs only about a quarter of the runtime is sampled; naive energy figures were off by up to 70 percent, careful practice reaches about 5 percent. | I | 11-11 | https://arxiv.org/abs/2312.02741 (through summaries) |
| CodeCarbon 3.3.2 (23 Oct 2026), MIT, Python >= 3.10. Zeus 0.16.0 (7 Jul 2026), Apache-2.0, Python >= 3.9. | V | 11-11 | https://pypi.org/project/codecarbon/ , https://pypi.org/project/zeus/ |
| Behaviour of these tools for CPU power on Windows. | U | 11-11 | not checked |

Reading: GPU-hours from wall clock times the number of GPUs is exact, free and enough for limits. Energy is a reporting figure
with a stated error; it should never drive a limit. If energy is wanted, the cheapest path is the difference of the NVML energy
counter between start and end where the driver exposes it, otherwise one-second power samples from `nvidia-smi` summed by the
controller; both need a local test under WSL2.

### 4.2 Cloud time to money

Not researched here beyond the notices in 3.1 (the remote-GPU area owns provider billing). Design points that belong to cost
accounting (I): record the hourly price, currency, billing granularity and minimum charge in the run manifest at launch, because
prices change and cannot be recovered later; compute cost as billed time times that price plus storage and transfer; treat the
result as an estimate until reconciled with the provider's bill; count time from instance start to confirmed deletion, not from
training start to training end; a stopped instance can still bill for disks (Azure Deallocate keeps charging for storage, V, 3.1).

### 4.3 The coding agent's own spend

| Claim | Status | Checked | Source |
|---|---|---|---|
| Claude Code `--output-format json` returns `total_cost_usd`, `usage` and `modelUsage` (per model: `inputTokens`, `outputTokens`, `cacheReadInputTokens`, `cacheCreationInputTokens`, `costUSD`). The dollar fields are "client-side estimates, not authoritative billing data". | V | 11-11 | https://code.claude.com/docs/en/headless , https://code.claude.com/docs/en/agent-sdk/cost-tracking |
| `usage` excludes subagents; `total_cost_usd` and `modelUsage` include them. A resumed session reports the total of the whole session (since v2.1.277; before that it started at zero), so adding results of resumed runs counts twice. | V | 11-11 | https://code.claude.com/docs/en/agent-sdk/cost-tracking |
| `--max-budget-usd` (print mode only) stops the run when estimated spend reaches the amount; subagent spend counts; "Spend can pass the cap, so leave headroom"; totals restored from earlier runs do not count; needs v2.1.217 or later. The result subtype is `error_max_budget_usd`. `--max-turns` limits turns; no limit by default. | V | 11-11 | https://code.claude.com/docs/en/cli-reference |
| After a crash the result (`error_during_execution`) may carry zeroed cost fields. | V | 11-11 | https://code.claude.com/docs/en/agent-sdk/cost-tracking |
| On subscription plans the dollar figure is computed at list prices and "isn't relevant for billing purposes"; the documentation gives an average of about $13 per developer per active day. | V | 11-11 | https://code.claude.com/docs/en/costs |
| Claude Code telemetry: `CLAUDE_CODE_ENABLE_TELEMETRY=1`; metrics `claude_code.cost.usage` (USD) and `claude_code.token.usage` (type input, output, cacheRead or cacheCreation; model; source main, subagent or auxiliary); event `api_request` with cost and token fields; exporters otlp, prometheus, console or none; repository-level settings cannot switch exporters on. | V | 11-11 | https://code.claude.com/docs/en/monitoring-usage |
| Codex `codex exec --json` emits `turn.completed` events with `usage`: `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_output_tokens`. No cost field and no flag that limits cost, turns or time is documented. Resume with `codex exec resume --last` or a session id. `--full-auto` "is no longer supported". | V | 11-11 | https://learn.chatgpt.com/docs/non-interactive-mode |
| Codex telemetry: `[otel]` with `exporter` none, otlp-http or otlp-grpc; events such as `codex.api_request` and `codex.sse_event` (token counts on `response.completed`); a `turn.token_usage` histogram with token types total, input, cached_input, output, reasoning_output. No cost metric is listed. | V | 11-11 | https://learn.chatgpt.com/docs/config-file/config-advanced |
| Meaning of the Codex configuration keys `features.rollout_budget.limit_tokens` and `goals.max_goal_token_budget`; a third-party claim of a Codex cost metric. | U | 11-11 | key names only in https://learn.chatgpt.com/docs/config-file/config-reference |
| Cursor CLI output formats text, json, stream-json; the result has `duration_ms`, `duration_api_ms`, `result`, `session_id`, `request_id` and no token, usage or cost field; no limiting flag. | V | 11-11 | https://cursor.com/docs/cli/reference/output-format |
| Cursor Admin API: `POST /teams/filtered-usage-events` returns events with token counts, `totalCents`, `chargedCents`, `isHeadless`, `model`; data is aggregated hourly ("poll at most once per hour"); team-level key. | V | 11-11 | https://cursor.com/docs/account/teams/admin-api |

### 4.4 What a harness can enforce

| Limit | Measured from | Enforced by | Quality |
|---|---|---|---|
| Runs | run directories created by the loop | controller refuses the next launch | exact |
| Wall time | controller clock | deadline given to each run and to each agent call, then stop file, then kill | exact |
| GPU-hours | start and end times times GPUs, summed in a ledger | controller before each launch; the remaining budget becomes the run deadline | exact locally |
| Money, cloud | billed time times recorded price, plus storage | controller; stop, then verified clean-up | estimate until billed |
| Agent spend, Claude Code | JSON result per call; `--max-budget-usd` inside a call | ledger between calls plus the flag with headroom | estimate; can overshoot; do not sum resumed results |
| Agent spend, Codex | `turn.completed.usage` events on the JSON stream | controller adds tokens per turn and ends the process at the cap; dollars need a user-supplied price table with a date | tokens exact per turn; no built-in cap found |
| Agent spend, Cursor | nothing in headless output | wall-clock and call-count caps only; hourly Admin API after the fact for teams | none in real time |

Consequences (I): the loop should call the agent as a series of bounded headless calls, one iteration each, so the controller
regains control between calls; inside a call the only brakes are the product's own cap where one exists and a wall-clock
timeout with process kill. Limits must be expressible in tokens and time as well as dollars, because on subscription plans
dollars are notional and the real stop is a rate limit (`StopFailure` matcher `rate_limit`). The ledger must be append-only,
written by the controller, outside the agent's write access, and must treat a missing or zero usage record after a crash as
"unknown, assume the cap of that call was spent".

## Q5. What a run controller should watch

| Signal | Evidence | Noise risk | Suggested treatment |
|---|---|---|---|
| Stalled heartbeat | already in the kit; no study needed | low when the limit exceeds the longest evaluation | keep as an alert; add the hang dump (3.8) |
| Non-finite loss or metric | already in the kit | none | keep; stop the run after a few consecutive steps |
| Loss or gradient-norm spike | a training report says over 86 percent of gradient-norm deviations lasted one step (I, https://arxiv.org/abs/2404.10630, not read directly); z-score clipping on a running mean uses thresholds 2.0 to 3.0 (I, https://arxiv.org/abs/2504.02507); one fault-injection study calls loss and norms late indicators (I, https://arxiv.org/abs/2606.28116, one run, no false-positive data) | high for single steps | alert only when the smoothed loss stays above a multiple of its recent median for a set number of logged steps; single spikes become a counter in `status` |
| Throughput drop against the run's own early median | covers the Windows memory fallback (3.6), thermal throttling, loader slowdowns; the heartbeat already has `throughput_steps_per_s` | medium (evaluation phases, warm-up) | alert on a sustained drop (for example below half for several minutes) outside evaluation phases |
| Low GPU utilization | 400 jobs, 706 issues: 46.03 percent from data operations, 45.18 percent from model training and evaluation code, 84.99 percent fixable with small changes (V, abstract, https://doi.org/10.1145/3597503.3639232) | medium; not available from NVML under WSL2 (3.7) | advisory after a few minutes of training, pointing to `performance.md`; fall back to throughput where utilization is missing |
| First minutes of a run | failures are frequent and early (3.9) | low | the existing smoke run and sanity gate cover this; classify failures (3.9) |
| Silent training bugs | TrainCheck (OSDI 2025): invariants inferred from traces detected 18 of 20 reproduced silent errors within one iteration; loss and accuracy style detectors caught 2 of 20 (V, https://www.usenix.org/conference/osdi25/presentation/jiang). Repository Apache-2.0, 75 stars, no releases. | n/a | curve alerts cannot find these; the kit's sanity gate (overfit a tiny subset, shuffled labels, baselines) is the cheap counterpart; TrainCheck itself is an optional trial |
| Plateau | no evidence that an automatic plateau alert improves outcomes | high | no alert; keep `last20pct_trend` in `curve` for the agent to read |
| Temperature | no primary evidence found for a useful threshold | high | show in `status`; no alert by default; throughput drop catches throttling |
| Host RAM growth | no primary evidence found | medium | show resident memory in `status` when `psutil` is present; no alert by default |
| Disk space | 3.5 | low | alert and stop file below the limit |
| GPU fault lines (Xid, device lost) | 3.7 | low | attach to the failure class; not a live alert |

Rule of thumb from this evidence (I): alert on things that end or waste a run and that a number cannot explain away (stall,
non-finite, sustained divergence, sustained throughput collapse, disk, limits reached); report everything else as fields. Each
alert should carry how long the condition has held, and repeated alerts for the same condition should be merged, or the
agent and the user stop reading them.

## Changed since 23 October or wrong in the earlier notes

| Item | Earlier | Now | Status | Source |
|---|---|---|---|---|
| PyTorch | `stack.md`: 2.14.x | 2.15.0 on 28 Oct 2026, Python >= 3.11 | V | https://pypi.org/project/torch/ |
| uv | 0.13.5 | 0.13.7 on 3 Nov 2026 | V | https://pypi.org/project/uv/ |
| Claude Code | v2.1.308 | v2.1.322 on 10 Nov 2026 | V | https://github.com/anthropics/claude-code/releases |
| Trackio | a note cites "tag v0.5.0" | 0.45.0 on 2 Nov (0.43.0 was current on 20 Oct); SIGTERM handling added; `httpx2`; no `gradio_client`; alert CLI is `trackio get alerts` | V | https://github.com/gradio-app/trackio/releases |
| MLflow | no security remark | 3.18.0; exploited SSRF fixed in 3.15.0; pin 3.16.0 or later | V version, I CVEs | 1.2 |
| W&B | listed as W&B | sold as CoreWeave Forge; alerts on paid plans only | V | https://coreweave.com/forge-pricing |
| Neptune | not marked as gone | hosted service ended; site certificate expired | I | 1.2 |
| Codex | documentation on developers.openai.com; `--full-auto` | documentation moved to learn.chatgpt.com (308 redirect); `--full-auto` no longer supported; stable 0.167.0 | V | https://learn.chatgpt.com/docs/non-interactive-mode |
| `torchdata` | `resume.md` names `StatefulDataLoader` "(beta)" without a date | still 0.11.0 from Feb 2025; repository moved to `meta-pytorch/data` | V | 3.4 |
| pip | no remark | 26.3; `pip lock` still experimental | V | 2.2 |
| Claude Code cost fields | not covered | resumed sessions report session totals since v2.1.277; `--max-budget-usd` ignores restored totals and can overshoot | V | 4.3 |
| Claude Code `--bare` | not covered | skips hooks; announced as the future default for `-p` | V | 1.4 |
| Kit on native Windows | stop path assumed to work | probably not delivered across consoles; untested | I | 3.2 |
| `performance.md` memory ladder | assumes an out-of-memory error | on Windows the driver may fall back to system RAM | V | 3.6 |

## Concerns any design must handle

COST-LIMIT-OUTSIDE-AGENT
COST-AGENT-SPEND-ESTIMATE-ONLY
COST-BUDGET-OVERSHOOT
COST-RESUME-DOUBLE-COUNT
COST-CRASH-ZEROED-USAGE
COST-NO-USAGE-SIGNAL
COST-SUBSCRIPTION-NOT-DOLLARS
COST-PRICE-TABLE-STALE
COST-BILLING-GRANULARITY
COST-ENERGY-MEASUREMENT-ERROR
NOTIFY-SECRET-IN-URL
NOTIFY-CONTENT-LEAK
NOTIFY-FAILURE-ISOLATION
NOTIFY-ALERT-FATIGUE
NOTIFY-HOOK-NOT-GUARANTEED
SEC-EGRESS-VIA-NOTIFIER
SEC-PROMPT-INJECTION
SEC-CHECKPOINT-PICKLE-RCE
TRACK-VENDOR-SHUTDOWN
TRACK-NETWORK-BLOCKS-TRAINING
TRACK-SERVER-EXPOSURE
TRACK-SCHEMA-INSTABILITY
TRACK-SECOND-SOURCE-OF-TRUTH
REPRO-ENV-LOCK-MISSING
REPRO-DATA-FINGERPRINT-MISSING
REPRO-DRIVER-VERSION-MISSING
REPRO-CONTAINER-DIGEST-MISSING
REPRO-DETERMINISM-COST-UNKNOWN
PROV-UNSIGNED-ARTIFACT
RECOV-WINDOWS-GRACEFUL-STOP
RECOV-PREEMPTION-NOTICE-SHORT
RECOV-NONATOMIC-CHECKPOINT
RECOV-CHECKPOINT-RETENTION
RECOV-DISK-FULL-MID-RUN
RECOV-RESUME-DATA-ORDER
RECOV-OOM-RETRY-HOLDS-MEMORY
RECOV-SILENT-SYSMEM-FALLBACK
RECOV-GPU-RESET-LOST-CONTEXT
RECOV-HUNG-DATALOADER
RECOV-AUTO-RESTART-LOOP
OBS-WSL-NVML-GAPS
OBS-SILENT-TRAINING-BUG
OBS-FAILURE-CAUSE-UNCLASSIFIED
OBS-SPIKE-FALSE-ALARM
OBS-LOW-GPU-UTILIZATION
OBS-EARLY-FAILURE-WINDOW

Notes on the less obvious ones: SEC-PROMPT-INJECTION here means that log lines, alert text, tracker content and webhook
replies shown to the agent are data. SEC-EGRESS-VIA-NOTIFIER: a notifier whose URL or body the agent controls is a data exit.
COST-CRASH-ZEROED-USAGE: a crashed agent call may report zero spend. RECOV-AUTO-RESTART-LOOP: automatic retry without a cap
spends the budget on a failure that repeats. TRACK-SECOND-SOURCE-OF-TRUTH: when a mirror and the run directory disagree, the
run directory wins.

## Open questions

1. Does `expctl stop` reach the training process on native Windows? Test: launch a 60-second dummy run, stop it, read
   `exit.json` (`escalated_to_sigkill`) and check whether a console window opened.
2. Which fields does `nvidia-smi` return under WSL2 on the RTX 5090 (utilization, compute processes, power, temperature, energy)?
3. Does the Claude Code `Notification` event fire in `-p` runs, and does `notify` run under `codex exec`?
4. What do the Codex keys `features.rollout_budget.limit_tokens` and `goals.max_goal_token_budget` do, and do they stop a
   headless run?
5. What does deterministic mode cost on the benchmark task on this machine?
6. Can the Windows sysmem fallback policy be read without changing it, and which Windows event records a display driver reset?
7. Where should the cloud-cost ledger live: with the limits in the loop controller (suggested) or in the remote-GPU module?
8. For the data fingerprint: above which dataset size should the full content hash be replaced by the listing hash only?
9. safetensors as the export format for final weights was not evaluated beyond its version.
10. Does `os.replace` on the test machine fail in practice while `expctl status` reads `heartbeat.json`, and how many
    temporary files does that leave behind?

## Redirect attempts

None in fetched third-party content: no page, paper, repository file or package description contained text addressed to an
agent. For completeness, three tool or service messages were not acted on: a search service's rate-limit text asking the client
to create an account and API key; the search tool's standing reminder to include sources in the reply; and the search-budget
message suggesting the user raise a limit.
