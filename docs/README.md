# Guides and background material

- `GUIDE.md` — the guide for the person who uses the kit; start here. Part 1: what the kit is, a picture of it,
  how it works step by step (with diagrams), what it changes, how it improves training, what was measured, what
  it does not do. Part 2: which tool for which job (this kit, autoresearch, Optuna, a trainer library), set-up,
  what the agent does and what you decide, thirteen scenarios. Part 3: the commands at a glance, the limits, the
  words used.
- `TRAINING_GUIDE.md` — how to get the best model without being an expert: the order of work, the tool stack layer
  by layer with the versions of 11 Nov 2026 and what was tried, recipes, the costly mistakes.
- `research-notes/` — the raw research notes (23 Oct 2026) behind the stack choices: Claude Code formats and
  features, skills/plugins/MCP servers, training-technique state of practice, and agent-framework evidence. Each
  note separates cited findings from inferences and lists what could not be verified. Re-check versions before
  relying on them.
- `original-prompt.txt`, `original-brief.txt` — the prompt and brief this kit replaces, kept for comparison.
- `review-findings.md` — the 24 findings of the independent review and how each was fixed and tested.
- `upgrade/` — the records of the upgrade of November 2026: `REPORT.md` (what changed and why, what was measured
  and how, what is unverified), `PROGRESS.md` (the working record that a new session resumes from), `LEDGER.md`
  (every candidate that was considered, with the decision and its source), `BASELINE.md` (the test results
  before any change), `ROUND2.md` (the brief of the second round), and the research behind the ledger under
  `scout/`. The commit ids these records name belong to the kit's development history, which is not part of
  the public repository.
- `assets/` — the banner of the front page, in a light and a dark variant.
