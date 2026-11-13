# Uncertainty: seeds, paired comparisons, winner's curse, honest reporting

Checked: 2026-10-23 (pairing by seed, measured: 2026-11-12)
Refresh: statistical practice, not versions; revise when scouting (`scouting.md`) finds a better-supported test
or reporting rule for small numbers of seeds.

Read before deciding whether a change "worked", before reporting results, and when planning budgets.

## 1. Establish the noise floor first
- Train the baseline with k seeds (k = 3 minimum when affordable, 5 better). Seeds should vary initialisation and data order (and dropout); keep the split fixed unless the project protocol uses cross-validation or resampled splits.
- The spread of the primary metric across these seeds is the noise floor. Record mean, sd, min, max and the per-seed values in the journal.
- Data sampling is typically the largest source of variance in benchmarks, and hyperparameter choice is about as large as initialisation (Bouthillier et al., MLSys 2021): randomise as many sources as you can afford, and say which ones you did not.

## 2. Compare with paired designs
- Candidate and baseline share the same seed list (same init and data order where the code allows it), the same protocol version and the same budget.
- Report: per-seed table, mean paired difference, sd of the differences, and the probability of improvement (fraction of pairs in which the candidate wins).
- Decision rule (default; adjust only with the user's agreement and write it down before running):
  - retain if the mean paired improvement exceeds the noise floor AND the sign is consistent across all pairs (n >= 3);
  - three pairs cannot reach p < 0.125 in an exact test, so a three-pair retain is a candidate: confirm it on fresh seeds before you build on it or report it as an improvement (`evaluation.md` section 1);
  - inconclusive if not — state it as inconclusive, not as "worse" or "better";
  - for close, high-stakes calls scale towards ~29 paired runs (the sample size Bouthillier et al. use for P(A > B) tests) or accept and state the uncertainty.
- A shared seed list does not by itself make runs comparable pair by pair: check whether the per-seed scores of two versions move together before you rely on a paired test. On the kit's benchmark they did not (two commits, eight seeds, two repeats, 2026-11-12: r = 0.3 between the seed means, no more than between unrelated seeds), so a paired test there only loses degrees of freedom; `nnloop` uses an unpaired test on pooled noise (`loop.md`, "The keep rule").
- Bootstrap intervals over test examples measure test-sampling noise only; they do not substitute for variation across training runs.

## 3. Winner's curse after a search
- The best trial of a search is optimistically biased. Re-run the top 3 configurations with fresh seeds (not the search seeds) and choose by the re-run mean under the declared selection rule.
- If the chosen configuration sits on the boundary of the search space, the search was too narrow: widen the range in a new study version rather than extrapolating.
- Report expected validation performance as a function of the number of trials when comparing methods with different tuning budgets (Dodge et al., 2019): rankings can flip with budget.

## 4. Expensive runs (no affordable replication)
- Say exactly what one run can establish: a single-seed result, not a significant improvement.
- Affordable evidence: seed variance measured on a cheaper proxy (smaller model, shorter schedule, data subset) used as a noise estimate; agreement of learning curves across checkpoints; stability across the last few evaluation points; consistency across multiple evaluation sets.
- Never select or advertise the luckiest seed.

## 5. Multi-task and RL settings
- Use robust aggregates: interquartile mean (IQM) with stratified bootstrap confidence intervals, performance profiles and probability of improvement (Agarwal et al., NeurIPS 2021). The `rliable` package is archived (Oct 2025); pin it or compute IQM/bootstrap directly with NumPy.

## 6. Reporting template
| config | protocol | budget | n seeds | mean +- sd | min / max | per-seed | P(improve vs baseline) | decision |
Separate measured results from hypotheses and proposals. Failed, pruned and timed-out runs stay in the record with reasons.
