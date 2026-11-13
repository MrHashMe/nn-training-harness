# Experiment journal

Append-only research log maintained by the coding agent (newest entries at the bottom).
Machine state lives in the run directories (`expctl status`); this file holds the decisions and their reasons:
what was believed, what was tried under which budget, what was measured, and what was decided.
Never edit or delete past entries — add a correction entry instead.

## Project card
<!-- Filled in Phase 0. Keep it current; it is the contract every comparison refers to. -->
- Task / model family / regime:
- Data (sources, permitted use) and split protocol (unit of separation: random / group / time):
- Primary metric + direction; selection rule (best checkpoint by ... on ...):
- Secondary constraints (latency, memory, params, cost):
- Comparison budget (equal steps / tokens / epochs / wall-clock / GPU-hours):
- Compute authorised (devices, GPU-hours, $, deadline) and already committed to live jobs:
- Environment (OS/WSL, Python, framework, CUDA/driver, env manager + lockfile):
- Tracker + HPO controller (single source of truth for trial results):
- Protocol version: v1 (evaluator hash: ...)
- Live jobs at start (run id / pid / owner / may touch? yes/no):
- Open questions for the user:

<!--
Entry template (copy for each experiment or decision):

## E<n> - <short title> - <YYYY-MM-DD>
- Hypothesis (falsifiable): if we <change>, then <metric> improves by >= <effect> at <budget>, because <evidence>.
- Change: <files/commit/config>, scope: <what it can affect>
- Protocol: <protocol version>, budget <...>, seeds <...>, compared against <baseline run ids>
- Runs: <run ids / study name>
- Result: <numbers with n, mean +- sd, per-seed values>; noise floor <...>
- Decision: retain | revise | revert - because <...>
- Next: <highest-value next action>
-->
