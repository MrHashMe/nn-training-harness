# Round 2: compare the kit with the best current projects and integrate what is better

This continues the upgrade of the nn-training harness kit in this folder. docs/upgrade/PROMPT.md stays in force: what "best" means, the adoption rule (consider everything, adopt on evidence, build what you adopt), core and optional, "results must be real", how to work, and Authority. This prompt adds one round; where the two disagree, this one wins for this round. Written on 12 November 2026: "latest" means as of the day you run it.

Make the changes yourself; I am not asking for a plan.

## Read first
- docs/upgrade/PROGRESS.md and docs/upgrade/REPORT.md ("Read this first" and sections 2, 8, 9, 10): what exists, what the live runs and the pilot showed, what is open.
- docs/upgrade/LEDGER.md and docs/upgrade/scout/draft/second-look.md: the decisions already taken and the ranking of what is unbuilt. Their decisions stand unless this round's evidence changes them: update rows, do not repeat the research behind them.

## The work
1. Where the kit stands. Before you search, write down in a few lines where the kit falls short of its purpose (an agent that uses it gets the best training results it can, and the results are real) and what would move it most, with the evidence for each point. Start from facts such as these: the pilot found no edge over the old kit or over no kit, and the campaign of 12 November ended because no idea could clear the keep margin. Revise this view after the research; the report shows both versions.

2. Census of similar projects. The research of 10 and 11 November was cut before it compared the kit with other systems as wholes. Do that now. "Similar" means a current project whose purpose overlaps the kit's: loops in which an agent runs ML experiments by itself (autoresearch and what followed it, "AI scientist" systems, agents and scaffolds built for ML-engineering benchmarks), and harnesses, skills, plugins and MCP servers that make a coding agent train or fine-tune models, vendor-published ones included. Search for what exists now before you look at the names in the ledger, so that the census is not limited to what the earlier notes knew. Read the strongest systems at their source (repository, documentation, paper), each at a version or commit, with the date. [ASSUMPTION: about twelve read in depth; the others you considered get one line each.] Build a matrix of capabilities by system with the kit as one column. Each capability that two or more strong systems share and the kit lacks, and each job of the kit that another system does better, is a candidate.

3. Newer methods in place of older defaults. Go through what the kit does and what its references and docs/TRAINING_GUIDE.md recommend, the kit's own statistics included (keep rule, seed panels, confirmation). For each default, check whether a newer method has replaced it on evidence. Your knowledge and the notes of 10 to 12 November can both be behind, so search by date for what was published or released in recent weeks and months in each area the kit covers. My example: e-means in place of k-means (arXiv 2611.09501, November 2026, reported as released in FAISS; not yet read here, so verify it at the source). The kit uses no k-means today: find out whether clustering belongs anywhere in it (deduplicating and selecting data, analysing embeddings), adopt e-means there if that place exists and the evidence holds, and give it a ledger row either way.

4. Tools as of today. For the open-source tools, plugins, MCP servers and skills that the kit uses, recommends or rejected: is there a newer release, or a new tool, that changes a decision in the ledger or in references/stack.md? What was checked on 10 to 12 November counts as current if you run this within days of it.

5. Decide and build. Every candidate from 1 to 4 gets a ledger row. So do the items already open, on equal terms: the unfinished Adopt rows, groups B and C of second-look.md, the guard's gap for worktrees outside .claude/worktrees/ (README, "Notes and limits"), and what the campaign of 12 November showed about the keep rule (REPORT.md section 2). [ASSUMPTION: this request is my go-ahead for all of these; none waits for a separate word.] Build what you adopt, highest expected benefit first. Where another project does a part of the kit's work better, replace that part and list the change. If a whole project does the kit's job better for my use, say so at the top of the report, and still integrate what can be integrated.

## Limits for this round
- Usage. [ASSUMPTION: the limit I set on 11 November still binds.] Most important first, cheaper models for subagents and headless sessions, depth where a build decision depends on it and one line per candidate elsewhere. Commit after each integration, so that the kit is better wherever the work stops.
- Evidence. A claim that a change improves training results or the loop's decisions is measured on the benchmark against its run-to-run noise, or reported as not measured. PROMPT.md's rule for headless sessions covers this round's live checks: no more than a check needs.
- My frontier-scout skill fits items 2 and 5 (analog census, whole-system alternatives, admission test). Use it as far as it changes decisions, not to the letter. The research connectors of this session may be used; send them nothing private.
- The real install and its repository stay untouched in this round. At the end, tell me what another installer run would change there.
- The open questions in PROGRESS.md still wait for me. Add new ones to that batch and ask at the end.

## Done when
- docs/upgrade/scout/ holds the census: the systems read, each with source, version or commit and date; the capability matrix; the candidates it produced.
- Every candidate and every open item named in item 5 has a ledger row with decision, reason, source and date; LEDGER.md is rebuilt and references/stack.md agrees with it.
- Each adopted row is finished as PROMPT.md's "Build what you adopt" defines, or listed as unfinished with the reason.
- These conditions of PROMPT.md hold for this round's changes: the sealed test set, the frozen evaluator and the protection of live runs are not weaker, and every change to what the guard asks, denies or allows is listed with its reason and its test; the core runs with only the Python standard library and no network; all tests, old and new, pass in WSL and on native Windows.
- One reviewer with no access to your working context has reviewed this round's changes to the guard, the loop's decisions and the final evaluation, and every finding it kept is fixed or answered.

## Report
Update docs/upgrade/REPORT.md and PROGRESS.md for a reader who has not seen the work, most important first: where the kit stood and how the research changed that view; what the census found (the matrix, and the few differences that matter); what you integrated and why, and what you rejected that I might have expected; what you verified by running it, what only from documentation, and what is unverified; every change in the behaviour of existing features; what needs my decision.

Effort for the run: ultrathink.
