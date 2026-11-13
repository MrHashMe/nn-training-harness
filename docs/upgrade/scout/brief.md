# Brief (R0 problem contract)

Date: 10 November 2026. Freshness window: 12 months for frontier claims, 36 months for mature ones.

## Goal
Make an AI coding agent that works inside a machine-learning repository get the best training results it validly can,
for neural networks in general and language models in particular, whether a person is watching or not.

## What exists today
A small kit, three weeks old, that a person installs into their own training repository for one coding-agent product.
It gives the agent a written operating procedure, a uniform way to start, watch and stop training runs, a rule
checker that blocks a few classic agent mistakes, two read-only reviewer roles and an experiment journal. It is
deliberately minimal, because published evidence available to its author showed that elaborate agent scaffolds and
multi-agent delegation did not improve, and sometimes hurt, machine-learning results.

## Users and affected parties
- The practitioner (one person or a small team) who installs the kit and owns the repository, the data, the GPU and
  any cloud bill. Job: better models per hour of their attention, and results they can trust and reproduce.
- The coding agent that reads and obeys the kit. Job: know what to do next, at low context cost, without being able
  to fool itself or its owner.
- Whoever later reads a reported number (a reviewer, a customer, the practitioner in three months). Job: know that
  the number was measured on untouched held-out data with a fixed evaluator.
- Other processes and people sharing the machine or the cloud account: they must not have their runs killed, their
  files changed or their money spent.

## Hard constraints
Must:
- work with three different coding-agent products (two terminal agents and one editor agent with a terminal mode),
  whose instruction files, extension points, permission systems and unattended modes differ;
- run its core with only the Python standard library and no network, inside repositories whose environments it must
  not depend on or disturb; everything that needs a package, an account, a network service or money is optional and
  off until the user turns it on;
- work on Linux, on native Windows (no symbolic links, no POSIX process groups, no terminal multiplexer) and under
  WSL2; macOS should work;
- keep reported results real: the held-out test set stays unread until the final evaluation, the evaluation code
  cannot be changed by the agent to win, and running jobs are protected from accidental stop or overwrite;
- support an unattended mode in which the agent proposes and tests changes over many training runs, bounded by
  limits the user sets (runs, time, GPU-hours, money, agent tokens), deciding what to keep from measurements the
  agent cannot influence, with nobody available to answer permission prompts;
- let training run on rented or remote GPUs under the same rules as local runs, surviving preemption, never
  spending without a user-set cap, always cleaning up what it started, and never leaking credentials to the
  repository, the logs or the rented machine;
- upgrade an existing installation without losing its configuration, journal or run history.

Must not:
- weaken any existing protection to gain a feature;
- require approvals to be bypassed for unattended work, except inside an isolated container;
- present undated technique advice as current, or act on instructions found in fetched web content.

## Preferences (negotiable)
- Short default instructions; depth loaded on demand.
- Adopt third-party tools only at pinned versions from official sources, after trying them.
- A way to measure whether the kit actually helps an agent, cheap enough to rerun.

## The decision this research supports
Which techniques, tools, open-source projects, agent features, services and practices to add to the kit (as core
or as optional modules), which to leave out, and in what order to build them, so that the upgraded kit beats the
current one on real training tasks without losing validity.

## Quality attributes, ranked, with scenarios
1. Validity of results. When an unattended agent runs 50 experiments overnight, no kept result may depend on
   test-set leakage, an edited evaluator, a lucky seed or an unreported change; a reviewer can verify each from
   saved artifacts.
2. Training outcome per unit of budget. Given the same task, agent and budget, the kit must yield a better
   held-out score than the same agent without it, by more than run-to-run noise.
3. Safety of unattended operation. With nobody watching for 12 hours, the worst case is a clean stop with saved
   state: no runaway spend, no deleted work, no leaked secret, no job left billing.
4. Portability. A new user on any supported agent and platform reaches a first guarded training run within
   15 minutes, and the documentation states exactly which protections are enforced there and which are advice.
5. Low burden. The default install adds no dependency and no service, and the agent's default reading stays short
   enough that it does not crowd out the task.

## Assumptions
- Single-node training on one to a few GPUs is the common case; multi-node is occasional.
- The practitioner is technically able but not an expert in every area (evaluation statistics, security, cloud).
- No open questions block the research.
