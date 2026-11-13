# Sweep scout: unattended-security (coding-agent sandboxes, prompt injection, unattended agents)

Checked 11 November 2026. Input: `docs/upgrade/scout/sweep/unattended-security/` (212 records: github 74, arxiv 39,
hf 30, hn 34, openalex 35; sweep run 10 November 2026; window 14 May to 10 November 2026). Status words:
**Verified** = I read the primary source (paper abstract page, repository README, vendor documentation, issue
thread or release metadata) and it says this; most numbers are still the authors' own measurements, and I say so;
**Inferred** = my conclusion from verified facts; **Unverified** = not confirmed from a primary source (secondary
press, forum comments, search summaries, or a page I could not open). Source text is paraphrased, not quoted.
Candidate decisions are in `sweep-unattended-security.candidates.jsonl` (60 lines).

## Summary (10 lines)

1. About 130 of 212 records bear on the goals; 60 candidates were evaluated and about 55 sources were read from primary pages, grouped into 31 deep reads below.
2. No agent's built-in shell sandbox is a sufficient boundary for unattended work, and the vendors say so. Claude Code's sandbox covers shell commands only (file tools, web tools, hooks and MCP servers run outside it), falls back to unsandboxed execution by default when it cannot start, and does not exist on native Windows; Cursor documents its sandbox for macOS and Linux only and calls its default classifier mode not a security boundary; Codex is the only one of the three that documents a native Windows sandbox.
3. The GPU is not reachable inside the bubblewrap sandbox (feature request open since 5 December 2025, no maintainer fix; a WSL2 variant exists; Codex reports its equivalent fixed). Training therefore needs either a narrow harness-owned launch path outside the agent's sandbox or a container or VM with GPU passthrough. The README's current advice to exclude the launcher gives that launcher full access.
4. Most measured sandbox escapes break no configured rule: in a cross-sandbox conformance study 61 of 79 escapes were on the default side, and the largest class (37) is "trust handoff", where the agent writes a git hook or a configuration file that a trusted tool later runs outside the sandbox. A standard-library guard rule can cover those paths on every platform, including native Windows.
5. Injection against coding agents is real, rare, targeted and growing: 47 attacks in 145 million GitHub items with a 2.2 times rise from June to September 2026; a test library shipped an agent-directed deletion instruction concealed in its output; in one benchmark, code comments and agent-rule files were the carriers local models followed most, and susceptibility rose with model size.
6. Prompt-level defences are the ones the evidence shows failing; deterministic enforcement outside the model held in the one study that tested both (static results on small open models, adaptive results simulated). Content can also mislead without instructing (task tampering, trust built up over several helpful rounds), which is exactly what a web-scouting step is exposed to. Consequence: scout in a separate tool-restricted process whose output is validated data, and let only experiments decide.
7. Keep-or-revert validity: keeping any change whose score went up, repeatedly against one noisy estimate, produced 30 to 42% false commits in one study and 13 to 21 spurious commits per run when no real gain existed. Remedies that need only the standard library: a paired sequential or fixed-budget paired gate, a single-use holdout released only after a durable receipt, a hash-chained ledger, a falsifier recorded before each run, and refusal of duplicate hypotheses.
8. Independent unattended-run projects converge on the same control rules: a question to an absent user becomes a parked item, state changes only on fresh mechanical evidence (a reviewer that advises without gating performed far worse than one that gates), stop on target, no progress or budget, a fresh agent process per iteration, a watchdog with capped restarts, and an evidence log that is never truncated.
9. ML auto-research agents collapse into narrow loops and rarely pivot or reopen abandoned work; a short planning prompt taken from human practice helps without closing the gap. Strict hardening has a measured price (up to 18.3 points of task success and up to 167% more spend) because blocked agents grind instead of stopping, so denials must be explained and counted toward a stop condition.
10. Tools: nothing heavy is worth adopting. Trial sandbox-runtime 0.0.82 (which now has an alpha Windows backend) and a GPU container route as optional isolation modules; assess the conformance corpus, RepoGuardBench, Boundary-Bench and SkillSpector as test instruments; reject auto-approve wrappers, a hosted-model guard that fails open, a copyleft rule engine and a licence-restricted context plugin.

## Selected items (one line each)

Dates are the sweep record dates (last push for active repositories, creation or submission date otherwise).
"Listed only" means the line rests on the sweep record; the page was not opened.

### Sandboxes and isolation, by platform
- carlostapiacl/sandbox-conformance (2026-10-28) https://github.com/carlostapiacl/sandbox-conformance : each agent sandbox's own tests run against the others; source of the trust-handoff finding.
- boundary-bench/boundary-bench (2026-08-05) https://github.com/boundary-bench/boundary-bench : agents evaluated under real sandbox policies; measures what hardening costs.
- Tracekit Box (2026-10-28) http://arxiv.org/abs/2610.38458v1 : micro-VM per job where every exit is decided and signed on the host; reference design for a launch broker.
- Sandbox AI coding agents with microVMs on Fedora Linux (2026-06-15) https://fedoramagazine.org/sandbox-ai-coding-agents-with-microvms-on-fedora-linux/ : libkrun route to VM-level isolation; says nothing about GPUs.
- Sandboxing Coding Agents (2026-08-28) https://micahflee.com/sandboxing-coding-agents/ : practitioner setup with per-sandbox scoped tokens and a separate agent identity.
- Fire the slop cannons (safely) (2026-09-23) https://www.latacora.com/blog/2026/09/18/fire-the-slop-cannons-safely-on-coding-agents-and-sandboxing/ : security-firm guidance on default-deny reads, consistent egress and VM-level isolation.
- Why coding agents belong in remote sandboxes (2026-08-04) https://www.superconductor.com/blog/remote-sandboxes-agent-security : vendor argument for remote isolation (listed only).
- getkern/kern (2026-07-18) https://github.com/getkern/kern : rootless, daemonless container runtime with WSL2 support; no GPU support.
- OpenCoworkAI/open-cowork (2026-10-20) https://github.com/OpenCoworkAI/open-cowork : desktop app that routes the agent's shell into a WSL2 VM on Windows.
- perplexityai/SPACE (2026-10-01) https://github.com/perplexityai/SPACE : pluggable-runtime sandboxes for agent code (listed only).
- clawkwork/clawk (2026-07-06) https://github.com/clawkwork/clawk : disposable Linux VM per agent (listed only).
- devvmhq/devvm (2026-11-06) https://github.com/devvmhq/devvm : one VM per project with its toolchain (listed only).
- brig-sh/brig (2026-08-12) https://github.com/brig-sh/brig : microVM sandbox CLI and session daemon (listed only).
- Trivo25/code-airlock (2026-07-01) https://github.com/Trivo25/code-airlock : unattended agent in a disposable microVM, work returned as git commits for review (listed only).
- boringcomputers/nehemiah (2026-06-30) https://github.com/boringcomputers/nehemiah : on-demand Firecracker machines for agents (listed only).
- mattpocock/sandcastle (2026-11-10) https://github.com/mattpocock/sandcastle : TypeScript orchestration of sandboxed coding agents (listed only).
- cloudflare/sandbox-sdk (2026-11-10) https://github.com/cloudflare/sandbox-sdk : hosted edge sandboxes; a network service with no GPU (listed only).
- davidondrej/cloudroom (2026-09-17) https://github.com/davidondrej/cloudroom : cloud sandboxes for several agent CLIs (listed only).
- Pi pod (2026-10-02) https://pipod.dev/ : self-hosted sandboxes for one agent CLI (listed only).
- Runtime (2026-05-21) https://www.runtm.com/ : hosted team sandboxes for coding agents (listed only).
- SCH (2026-09-13) https://c-daniele.github.io/en/posts/2026-09-07-close-the-lid-serverless-coding-harness/ : agent sandbox in the user's own cloud account (listed only).
- agent-run (2026-07-12) https://github.com/sin-ack/agent-run : run a coding agent in a sandboxed environment (listed only).
- DiscoBox (2026-09-22) https://github.com/discobox-ai/discobox : disposable sandboxes for coding agents (listed only).
- VT Code (2026-10-21) https://github.com/vinhnx/VTCode : terminal agent with sandboxed tools (listed only).
- mistle (2026-05-21) https://github.com/mistlehq/mistle : platform for automating sandboxed agents (listed only).
- MiniMax-AI/OpenAgentCore (2026-09-21) https://github.com/MiniMax-AI/OpenAgentCore : self-hosted API in front of several agent CLIs (listed only).
- langgenius/mosoo (2026-06-13) https://github.com/langgenius/mosoo : managed runtime with isolation for several agent CLIs (listed only).
- omnigent-ai/omnigent (2026-06-11) https://github.com/omnigent-ai/omnigent : meta-harness across the three target agents; relevant to the ports (listed only).
- bytedance/deer-flow (2026-11-10) https://github.com/bytedance/deer-flow : long-horizon agent harness with sandboxes (listed only).
- HarnessMD/munder-difflin (2026-05-31) https://github.com/HarnessMD/munder-difflin : local multi-agent workspace with sandboxing (listed only).
- machine0 (2026-08-18) https://machine0.io : persistent CPU and GPU VMs from a CLI; a remote-GPU candidate for another scout (listed only).
- Firepool (2026-11-07) http://arxiv.org/abs/2611.10832v1 : brokering warm GPU capacity for short isolated jobs (listed only).
- Sandman (2026-10-29) http://arxiv.org/abs/2610.39711v2 : sandbox service that keeps cleanup responsibility after the caller dies; lesson for remote cleanup.

### Credentials, secrets and egress
- OneCLI (2026-07-23) https://github.com/onecli/onecli : gateway that injects credentials so agents never hold them; heavy.
- Coding Agent Sandboxes Don't Solve Credential Authorization (2026-06-15) https://www.permit.io/blog/coding-agent-sandboxes-credentials : isolation limits reach, not what a held credential can do.
- AVP (2026-06-11) https://github.com/inflightsec/agent-vault-proxy : proxy so the agent never holds the secret (listed only).
- AnYejun/blind-vault (2026-07-10) https://github.com/AnYejun/blind-vault : secrets an agent can use but not see, on one operating system's keychain (listed only).
- Ask HN: How do you gate an autonomous coding agent's shell access? (2026-09-03) https://news.ycombinator.com/item?id=49556858 : practitioner answers; forum content, used only as leads.

### Documented attacks and attack measurements
- Undisclosed addition in jqwik instructed AI coding agents to delete app output (2026-05-29) https://arstechnica.com/security/2026/05/fed-up-with-vibe-coders-dev-sneaks-data-nuking-prompt-injection-into-their-code/ : a dependency's own output as an injection carrier.
- Google: attackers are using prompt injection against coding agents (2026-09-09) https://cloud.google.com/blog/topics/threat-intelligence/from-prompting-to-autonomy-the-evolution-of-adversarial-ai : threat-intelligence report (primary not readable; Unverified).
- rdwr-gabin/github-ipi-in-the-wild (2026-10-26) https://github.com/rdwr-gabin/github-ipi-in-the-wild : GitHub-scale census of hidden agent-directed text, with a local detector.
- DaoyuanLi2816/RepoGuardBench (2026-06-29) https://github.com/DaoyuanLi2816/RepoGuardBench : which repository carriers local agents follow, and which light defences work.
- The Long Con on the Web (2026-10-31) http://arxiv.org/abs/2611.00725v1 : a web source earns trust with real help, then exploits it; bears on scouting.
- Beyond Instruction Override (2026-11-05) http://arxiv.org/abs/2611.07640v1 : injection that tampers with the task without issuing instructions.
- compass-group-tue/prompt_injections_so_back (2026-05-14) https://github.com/compass-group-tue/prompt_injections_so_back : argument and data that separating data from instructions cannot be complete.
- From Prompt Injection to Persistent Control (2026-05-29) https://huggingface.co/papers/2605.31042 : injection stored in workspace state and executed later.
- Appreciation Teaches Unauthorized Execution (2026-10-29) http://arxiv.org/abs/2610.39122v1 : agents that learn from feedback become easier to inject.
- Same Bytes, Different Authority (2026-09-28) https://huggingface.co/papers/2609.35932 : chat-template markers encoded as reserved tokens carry far more authority; bears on fine-tuning data.
- When Neither Side Confirms (2026-11-02) http://arxiv.org/abs/2611.02527v1 : destructive MCP tools usually run with no approval on either side.
- jiaxiaojunQAQ/SkillJect (2026-06-11) https://github.com/jiaxiaojunQAQ/SkillJect : automated, stealthy skill-based injection (listed only).
- A prompt injection nearly hijacked my coding agent mid-task (2026-07-01) https://senthex.com/en/blog/prompt-injection-hijacked-my-coding-agent/ : practitioner incident report (listed only).
- Agents of Chaos (2026-11-07) http://arxiv.org/abs/2611.10843v1 : systematisation of attacks on agent systems (listed only).
- Agent Against Agent / PIMiner (2026-08-05) https://huggingface.co/papers/2608.05108 : automated injection red-teaming that transfers to unseen agents (listed only).
- PISmith (2026-07-23) https://huggingface.co/papers/2603.13026 : reinforcement-learned attacks on injection defences (listed only).
- microsoft/llmail-inject-challenge (2026-11-01) https://github.com/microsoft/llmail-inject-challenge : code of an adaptive injection challenge (listed only).
- xhOwenMa/AutoDojo (2026-06-11) https://github.com/xhOwenMa/AutoDojo : generated benchmark for injection defences (listed only).
- Flooding spread of manipulated knowledge in LLM-based multi-agent communities (2026-06-11) https://doi.org/10.1007/s11432-024-4663-2 : planted claims spread through shared agent memory (listed only).

### Defences and enforcement outside the model
- Treating the Model as an Untrusted Component (2026-11-08) http://arxiv.org/abs/2611.11571v1 : deterministic policy, approval and taint tracking against injection, tested on open models.
- "Shall We Approve?" (2026-10-29) http://arxiv.org/abs/2610.40753v1 : approve commands from their observed effects in a snapshot, not from their text.
- brave/bravebot (2026-08-20) https://github.com/brave/bravebot : agent built so untrusted content never reaches the planner.
- SECBLOK/belay (2026-07-03) https://github.com/SECBLOK/belay : local rule engine with hooks for the three target agents; overlaps the kit's guard.
- leepokai/jev-guard (2026-09-17) https://github.com/leepokai/jev-guard : hosted-model risk scoring of tool calls; fails open.
- tenet-security/agent-jackstop (2026-06-15) https://github.com/tenet-security/agent-jackstop : hardening for two of the target agents against injection through tool output (listed only).
- magicmadeint/wipedown (2026-05-25) https://github.com/magicmadeint/wipedown : local proxy that neutralises injections in scraped pages (listed only).
- Hannay001/lockkeeper (2026-08-24) https://github.com/Hannay001/lockkeeper : skill router and injection firewall (listed only).
- ax128/AegisGate (2026-09-14) https://github.com/ax128/AegisGate : security gateway for model API traffic (listed only).
- arcjet/arcjet-js and arcjet/arcjet-py (2026-11-10) https://github.com/arcjet/arcjet-js : runtime security library tied to a hosted service (listed only).
- DashClaw (2026-09-07) https://github.com/ucsandman/DashClaw : policy and approval layer for unattended agents (listed only).
- Bounded Agents (2026-08-16) https://huggingface.co/papers/2608.15888 : session-aware authorization for delegated agents (listed only).
- AgentDoG 1.5 (2026-05-28) https://doi.org/10.48550/arxiv.2605.29801 : guard model for agent actions (listed only).
- SecPO (2026-10-30) http://arxiv.org/abs/2610.41998v1 : adversarial training against injection; a model-side defence a kit cannot apply (listed only).
- SecOPD (2026-08-21) https://huggingface.co/papers/2608.21500 : fine-tuning defence against adaptive injection (listed only).
- Virtue-Research/guard-eval-harness (2026-06-26) https://github.com/Virtue-Research/guard-eval-harness : one-command benchmark of guardrails and coding agents (listed only).

### Skill, plugin and MCP supply chain
- NVIDIA/SkillSpector (2026-11-10) https://github.com/NVIDIA/SkillSpector : static scanner for agent skills with an offline mode.
- The Devil Wears Markdown (2026-11-07) http://arxiv.org/abs/2611.10830v1 : measured false-positive rates of skill scanners; hybrid analysis does better.
- enkryptai/skill-sentinel (2026-09-19) https://github.com/enkryptai/skill-sentinel : multi-agent skill scanner (listed only).
- AgentLatch/agent-latch (2026-10-01) https://github.com/AgentLatch/agent-latch : local scanner and MCP traffic monitor (listed only).
- inkog-io/inkog (2026-11-01) https://github.com/inkog-io/inkog : static scanner that also flags runaway loops and missing oversight (listed only).
- sinewaveai/agent-security-scanner-mcp (2026-10-18) https://github.com/sinewaveai/agent-security-scanner-mcp : scanner with package-hallucination detection (listed only).
- SkillOpt (2026-05-22) https://doi.org/10.48550/arxiv.2605.23904 : self-evolving skills; read together with the self-evolution finding above (listed only).

### Unattended loops: governance, verification and operations
- Proof-or-Stop (2026-07-16) http://arxiv.org/abs/2607.14890v1 : state changes only on mechanically verifiable evidence; ablation of gating against advising.
- TokonoMix/agents-never-sleep (2026-07-05) https://github.com/TokonoMix/agents-never-sleep : standard-library governance for unattended backlogs; source of the park-instead-of-ask contract.
- gregce/deadreckon (2026-08-21) https://github.com/gregce/deadreckon : supervision harness with a two-key acceptance gate and keyed receipts.
- qingqingpi/loop-engineering-skill (2026-06-21) https://github.com/qingqingpi/loop-engineering-skill : checklist for agent loops built on verifier fidelity.
- jooray/night-agent (2026-07-17) https://github.com/jooray/night-agent : bounded overnight sessions with scheduling anchored to usage-limit resets.
- Hours unattended: the memory bugs that broke my autonomous coding agent (2026-08-30) https://eltoncherrington.github.io/memctl-shop/essay.html : four concrete failures of a 72-hour run.
- shaahink/conductor (2026-07-07) https://github.com/shaahink/conductor : event-sourced orchestrator that verifies gates independently of the agent (listed only).
- axocoatl/axocoatl (2026-06-04) https://github.com/axocoatl/axocoatl : the host, not the agent, writes the receipt for sandboxed unattended runs (listed only).
- lucasfcosta/backpressured (2026-05-29) https://github.com/lucasfcosta/backpressured : skills for long unattended sessions (listed only).
- stone16/harness-engineering-skills (2026-09-07) https://github.com/stone16/harness-engineering-skills : multi-agent orchestration with cross-model review (listed only).
- mosonlab/anneal (2026-08-19) https://github.com/mosonlab/anneal : unattended plan, review, implement, verify chain (listed only).
- fabrodz/milestoner (2026-08-20) https://github.com/fabrodz/milestoner : milestone state machine for long unattended plans (listed only).
- toolshedlabs-hash/nightshift (2026-07-23) https://github.com/toolshedlabs-hash/nightshift : patterns for overnight agent runs (listed only).
- aeonfun/aeon (2026-11-10) https://github.com/aeonfun/aeon : unattended agents on a hosted CI service (listed only).
- Drix10/agent-flow (2026-09-26) https://github.com/Drix10/agent-flow : guardrails for unattended runs that end in a reviewed pull request (listed only).
- elflodge/elflodge (2026-10-24) https://github.com/elflodge/elflodge : local job interface for many sandboxed agents (listed only).
- zdavison/deer (2026-10-13) https://github.com/zdavison/deer : minimal unattended orchestrator (listed only).
- HiQS-Labs/XYZ-forge (2026-08-15) https://github.com/HiQS-Labs/XYZ-forge : local coordination of several agent CLIs (listed only).
- Relay (2026-09-29) https://relayevals.com : harness for agents that recover and verify (listed only).
- claude-yolo/claude-yolo (2026-10-27) https://github.com/claude-yolo/claude-yolo : automatic permission approval; an anti-pattern under the brief.
- snomiao/agent-yes (2026-11-10) https://github.com/snomiao/agent-yes : auto-answers prompts across agents; same anti-pattern.
- Harness-of-Harness (2026-09-01) https://huggingface.co/papers/2609.01481 : multi-day autonomous development loops (listed only).
- ReLiveGym (2026-09-30) http://arxiv.org/abs/2610.00710v1 : evaluating long-lived agents over weeks (listed only).
- mll-lab-nu/embodied-first-exam (2026-09-18) https://github.com/mll-lab-nu/embodied-first-exam : frozen tasks verified in a separate sandbox; an analog for a verifier outside the agent's reach (listed only).
- Code as Agent Harness (2026-05-18) https://huggingface.co/papers/2605.18747 : survey of harness designs (listed only).
- Agentic Coding in the Wild (2026-07-30) https://doi.org/10.48550/arxiv.2608.00101 : production traces of a coding agent (listed only).
- One Success Isn't Reliability / Thinkingbox (2026-08-20) https://huggingface.co/papers/2608.19741 : reliability over repeated runs, not single successes (listed only).

### Keep-or-revert validity and auto-research evidence
- PACE (2026-06-06) https://doi.org/10.48550/arxiv.2606.08106 : anytime-valid acceptance tests for agents that keep their own changes.
- Hard to Fool (2026-11-04) http://arxiv.org/abs/2611.06607v1 : bounded research loop in which trusted code decides and the holdout opens once.
- TraceML (2026-08-26) http://arxiv.org/abs/2608.26086v4 : what auto-research agents miss in long ML development compared with humans.
- Agentic Autoresearch for Cell-Edge Power Control (2026-08-26) http://arxiv.org/abs/2608.26093v1 : 81 unattended ML experiments under a hash-pinned evaluator and pre-registered falsifiers.
- AutoMegaKernel (2026-06-08) http://arxiv.org/abs/2606.09682v1 : frozen validator that rejects unsafe agent proposals before launch.
- ATTUNE (2026-10-13) http://arxiv.org/abs/2610.17528v3 : agentic throughput tuning for LLM training with a correctness gate outside the agent.
- AdaPRA (2026-10-23) https://huggingface.co/papers/2610.33245 : process audits of data-science agents by executing checks.
- FARS (2026-06-30) https://doi.org/10.48550/arxiv.2606.31651 : fully automated research at scale and how its papers fail review.
- Agora (2026-09-16) https://huggingface.co/papers/2609.18094 : Git as an append-only research record shared by many agents.
- SoL-Pi (2026-09-17) http://arxiv.org/abs/2609.20519v1 : recursive research loops that cut token traffic.
- Enmo Safety (2026-11-06) http://arxiv.org/abs/2611.10099v1 : keep-on-holdout rule in a safety harness; mostly null results.
- Can LLM Agents Improve Imperfect Earth System Model Parameterizations? (2026-11-02) http://arxiv.org/abs/2611.03543v1 : agent research loop in another scientific domain (listed only).
- An AI system to help scientists write expert-level empirical software (2026-05-19) https://doi.org/10.1038/s41586-026-10658-6 : score-driven code search at scale (listed only).
- Where Do Reported Long-Video QA Gains Come From? (2026-11-05) http://arxiv.org/abs/2611.07329v1 : controlled audit of where reported gains come from; an analog for attribution (listed only).
- Control-Data Flow Separation (2026-09-01) https://huggingface.co/papers/2609.00621 : keep execution protocol apart from optimisable text (listed only).
- KAPPA (2026-10-26) http://arxiv.org/abs/2610.35596v1 : agents checking statistical proofs with a proof assistant; an analog for mechanical verification (listed only).

### Cost and context
- mksglu/context-mode (2026-11-10) https://github.com/mksglu/context-mode : keeps tool output out of the context window; licence and runtime problems.
- Austin1serb/agents-md (2026-07-15) https://github.com/Austin1serb/agents-md : instruction-file patterns, including byte-capped command output.
- TokenEconomizer (2026-10-15) https://huggingface.co/papers/2610.22732 : cost control for coding agents across sequential tasks (listed only).
- SkillZip (2026-08-11) https://huggingface.co/papers/2608.11079 : compressing skills; bears on short default instructions (listed only).
- I track LLM API prices daily, found a 33x cost gap in the same model (2026-09-06) https://news.ycombinator.com/item?id=49586810 : a token cap is not a money cap (forum post, listed only).

### Outside this facet, left to other scouts (listed only)
- LLM Post-Training: A Deep Dive Into Reasoning Large Language Models (2026-08-04) https://doi.org/10.1109/tpami.2026.3720414 : survey of post-training methods.
- MOPD (2026-06-29) https://doi.org/10.48550/arxiv.2606.30406 : multi-teacher on-policy distillation.
- What Drives the Zero-to-One Jump? (2026-11-02) http://arxiv.org/abs/2611.02747v1 : hard-prompt learning under verifiable rewards.
- Beyond Efficiency (2026-09-15) https://doi.org/10.1145/3845797 : survey of resource-efficient language models.
- AI4Research (2026-09-28) https://doi.org/10.1007/s11432-025-5000-y : survey of AI for scientific research; background for the scouting step.
- Transforming Science with Large Language Models (2026-09-05) https://doi.org/10.1145/3845596 : survey of AI-assisted discovery and evaluation.

## Deep reads

Format: claim | source | version or date | status. All checked 2026-11-11. "Take" lines say what the kit could use
and at what cost.

### D1. Claude Code built-in sandbox
- Mechanism: Seatbelt on macOS; bubblewrap plus socat on Linux and WSL2; WSL1 unsupported; on native Windows commands run unsandboxed | https://code.claude.com/docs/en/sandboxing | newest version named on the page is 2.1.310 | Verified.
- Off by default. If the sandbox cannot start, commands run unsandboxed unless `sandbox.failIfUnavailable` is set | same | - | Verified.
- Inside the sandbox: Bash, PowerShell and Monitor commands and their child processes. Outside it: Read, Edit, Write, WebFetch and WebSearch (a read deny does not stop the Read tool and the domain allowlist does not limit WebFetch), command hooks, local MCP servers, plugin monitors, language servers, the status line, the key-helper script and every entry in `excludedCommands` | same | - | Verified.
- Default read scope is the whole machine, credential files included; narrowing it needs `sandbox.filesystem.denyRead`, `sandbox.credentials` or `permissions.blockReadsOutsideWorkingDirectories` | same | - | Verified.
- Write-protected by default: agent settings, `.mcp.json`, shell startup files, `.gitconfig`, `.vscode`, `.idea`, git hooks and git config | same | - | Verified.
- Network goes through a proxy; `network.allowedDomains` starts empty; an unlisted host follows the permission mode (allowed under bypassPermissions, refused under dontAsk); the proxy does not inspect TLS, so domain fronting can pass; allowing Unix sockets can expose the container daemon socket | same | - | Verified.
- A command that fails in the sandbox can be retried outside it unless `allowUnsandboxedCommands` is false; `autoAllowBashIfSandboxed` defaults to true; container tooling does not work inside and must be excluded, and excluded commands run with full access | same | - | Verified.
- GPU access is not mentioned on the page | same | - | Verified (absence).
- Take: (a) an optional settings fragment that fails closed; (b) the kit's Read and Edit deny rules stay necessary, because file tools are outside the sandbox; (c) the kit's hooks run outside the sandbox, so the guard is trusted code and its own files need write protection. Cost: two system packages on Linux and WSL2; no effect on native Windows.

### D2. Whole-process isolation: vendor guidance and sandbox-runtime 0.0.82
- The sandboxed Bash tool alone is described as not sufficient for fully unattended runs; sessions that skip permissions should run inside a container, a VM or the sandbox runtime; the auto-mode classifier is a per-action control, not an isolation boundary; for a native Windows host the advice is a container or VM, or the Bash sandbox inside WSL2 | https://code.claude.com/docs/en/sandbox-environments | page undated | Verified.
- A sandboxed session that can write agent or git configuration can persist hooks, permission rules or MCP servers that run unsandboxed at the next launch; the page advises reviewing the writable paths after unattended runs; on Linux and WSL2 the protected-path list is built at launch and does not cover repositories created afterwards | same | - | Verified.
- The vendor's reference dev container with a default-deny firewall is a documented place to skip permissions; Docker Sandboxes is described as a microVM with its own container daemon | same | - | Verified.
- sandbox-runtime (`srt`): wraps an arbitrary process under file and network restrictions; Apache-2.0; labelled beta research preview; latest release v0.0.82, published 2026-11-09; repository is now `anthropics/sandbox-runtime` | https://github.com/anthropics/sandbox-runtime (README and release metadata) | v0.0.82 | Verified.
- Mechanisms: macOS sandbox profiles; Linux bubblewrap with the network namespace removed, host proxies reached over bind-mounted sockets and a seccomp filter for Unix sockets on two CPU architectures; Windows (alpha): a dedicated local account, a write-restricted token, explicit file ACL entries and a Windows Filtering Platform egress filter keyed to that account, installed once per machine with one elevation prompt; an experimental container backend on Windows needs Node 24 and does not run Git Bash or other MSYS2 programs | same | v0.0.82 | Verified.
- Always write-denied, even inside allowed write paths: shell startup files, `.gitconfig`, `.gitmodules`, `.ripgreprc`, `.mcp.json`, `.vscode/`, `.idea/`, `.claude/commands/`, `.claude/agents/`, `.git/hooks/`, `.git/config`. On Linux this uses read-only bind mounts found to a default search depth of 3, with placeholder files for paths that do not exist yet; a process killed hard can leave placeholders behind | same | v0.0.82 | Verified.
- Stated limits: filtering is by domain only, so a broad allowed domain such as a code host permits exfiltration and domain fronting may pass; Linux enforcement relies on proxy environment variables; on Windows, system-TLS clients fail inside the sandbox, DNS through the system resolver is not filtered, SMB and WSL traffic is not matched, some token-switching cases escape the filter, and per-command read or write overrides are unsupported | same | v0.0.82 | Verified.
- Device nodes and GPUs are not mentioned in the README; a search of the repository's issues for GPU terms returned nothing | same; GitHub issue search | 2026-11-11 | Verified (absence).
- Whether CUDA works under the Windows backend | - | - | Unverified (Inferred likely, because that backend restricts by account and token and does not replace the device namespace; needs a trial).
- Independent Linux test of v0.0.81: 141 contained, 14 escaped, 1 control broken, 18 unsupported (D6) | https://github.com/carlostapiacl/sandbox-conformance | run of 2026-11-08 | Verified (third party with a disclosed conflict of interest).
- Take: `srt` is the only whole-process boundary found that covers Linux, macOS and Windows without an account or money. It stays optional (needs Node.js, an npm package and, on Linux, three system packages; on Windows an administrator prompt and a new local account). Pin the version; test GPU and network behaviour before recommending it.

### D3. GPU inside the agent sandbox
- Feature request for GPU device passthrough in sandbox mode: open since 2025-12-05; labels include security and Linux; no maintainer reply beyond labelling and no setting; the sandbox mounts a fresh `/dev` and does not bind GPU device nodes, so `nvidia-smi` and framework GPU checks fail; latest version-specific confirmation is on 2.1.89 (2026-04-13) | https://github.com/anthropics/claude-code/issues/13108 | thread read 2026-11-11 | Verified (the reports are user-written but consistent and include direct bubblewrap tests).
- A second report was closed as its duplicate on 2026-06-01: device nodes are bound without device semantics and NVML reports insufficient permissions; the only workarounds named are running that command unsandboxed or disabling the sandbox | https://github.com/anthropics/claude-code/issues/64530 | - | Verified.
- WSL2 report of 2026-07-14, closed as not planned by automation: `nvidia-smi` says the operating system blocks GPU access; the reporter's hypothesis is that `/dev/dxg` is not exposed | https://github.com/anthropics/claude-code/issues/77393 | - | Verified that the report exists; cause Unverified.
- Codex had the same WSL2 defect (opened 2026-05-13 against 0.130.0; seen again on 0.141.0); a maintainer said on 2026-06-21 that it was fixed; no fixed version or configuration key is named; the workaround had been full-access mode | https://github.com/openai/codex/issues/22469 | - | Verified (thread); fix version Unverified.
- A community workaround places a wrapper named `bwrap` earlier on PATH to add device binds | issue 13108 thread | - | Unverified (user-written, depends on internals, widens the sandbox; not run).
- Consequence: with Claude Code on Linux or WSL2, training cannot be launched from inside the built-in sandbox today. The README's advice ("exclude the launcher if needed") makes the launcher, and anything the agent can make it run, a full-access path | my reading | - | Inferred.
- Take: the launcher is a security boundary. Options, cheapest first: a harness-owned launch broker outside the sandbox that accepts only validated requests (candidate, Trial); a container with GPU passthrough around the whole agent (candidate, Trial). Cost: one extra long-lived process or one container engine.

### D4. Codex CLI sandbox and approvals
- Three sandbox modes (`read-only`, `workspace-write`, `danger-full-access`); approval policy `on-request` or `never` (an older value is no longer supported); an optional automatic reviewer (`approvals_reviewer`) | https://learn.chatgpt.com/docs/sandboxing (reached by redirect from the developer documentation address) | page undated | Verified.
- Platforms: Seatbelt on macOS; a native Windows sandbox when run from PowerShell; bubblewrap required on Linux and WSL2, with an AppArmor profile involved on one current Ubuntu release | same | - | Verified.
- `sandbox_workspace_write.writable_roots` extends the writable set | same | - | Verified.
- Not covered on that page: headless execution, protected paths, GPU | same | - | Verified (absence).
- Independent Linux test of CLI 0.167.0: 97 contained, 24 escaped, 29 controls broken, 24 unsupported (D6) | sandbox-conformance | run of 2026-11-08 | Verified (third party).
- Strength of the native Windows sandbox | - | - | Unverified (the only cross-sandbox lab found is Linux only).
- Take: for the Codex port, `workspace-write` with a non-prompting approval policy is the unattended baseline, and it is the one native Windows sandbox among the three agents. The port's documentation must say that broken controls are common on Linux (legitimate commands may fail) and that Windows strength is untested.

### D5. Cursor run modes and sandbox
- Run modes: Auto-review (default since 3.6; an LLM classifier which the documentation says is not a security boundary), Allowlist, and Run Everything; the older ask-every-time mode is deprecated | https://cursor.com/docs/agent/security/run-modes | changelog entries 3.5 (2026-05-22), 3.6 (2026-05-29), 3.23 (2026-10-01) | Verified.
- Sandbox: Seatbelt on macOS; Landlock plus seccomp on Linux kernels 6.2 or later; Windows and WSL2 are not mentioned; on an older kernel Cursor falls back to asking for approval before running commands | same | - | Verified.
- Protected paths: `.git/config`, `.git/hooks`, `.vscode`, `.cursorignore`. Network policy from `sandbox.json` (user or project level) with three modes; `permissions.json` holds auto-run allow and block instructions; environment markers such as `CURSOR_SANDBOX` show that a command runs sandboxed | same | - | Verified.
- Headless behaviour is not described; cloud agents never ask for approval | same | - | Verified.
- Take: Allowlist mode plus a project `sandbox.json` is the candidate unattended baseline for the Cursor port; a fallback to asking means an unattended run can stall, so the loop controller needs a time limit per step and a parked outcome; `CURSOR_SANDBOX` is a cheap preflight probe. The Windows gap must appear in the protection table.

### D6. Cross-sandbox conformance corpus and the trust-handoff class
- Corpus v1.1 (2026-10-26): 196 contracts, each made of an attack that must first work unsandboxed, a control that must keep working and an expected effect; harvested from the test suites of six sandbox and agent projects; lab is one Linux release with Landlock ABI 4 | https://github.com/carlostapiacl/sandbox-conformance | v1.1 | Verified.
- Run of 2026-11-08 (contained / escaped / control broken / unsupported): sandbox-runtime 0.0.81: 141 / 14 / 1 / 18; Codex CLI 0.167.0: 97 / 24 / 29 / 24; nono 0.81.0: 50 / 37 / 5 / 83; landrun 0.1.17: 41 / 42 / 1 / 91; the maintainer's own sandbox (alpha): 170 / 3 / 0 / 0 | same | - | Verified (the maintainer builds a competing sandbox and discloses it).
- Earlier write-up over 168 contracts and three sandboxes: 79 escapes, of which 61 broke no configured rule and 18 broke a configured rule; by class: trust handoff 37, isolation 19, filesystem 9, network 5, lifecycle 5, secrets 3, inter-process 1; one agent CLI had 27 broken controls | https://carlostapia.cl/notes/sandbox-escapes-no-rule-broken/ | 2026-10-15 | Verified.
- Trust handoff means the agent writes a file that a trusted tool later runs or obeys outside the sandbox, such as a git hook or an editor configuration file | same | - | Verified.
- Vendor reports filed as of 2026-10-27: four for one runtime (one open), two for another (one open) | repository | - | Verified.
- Limits: one author, weeks old, Linux only, conflict of interest | my reading | - | Inferred.
- Take: (a) add trust-handoff paths and the kit's own control files to the guard's write denies on all platforms; (b) after each unattended run, list protected files whose hashes changed; (c) port a handful of the contracts into the kit's guard tests instead of running the corpus. Cost: patterns and tests only.

### D7. What hardening costs (Boundary-Bench)
- 12 agents on a terminal benchmark under nested hardening policies; under the strictest policy success fell by up to 18.3 points and cost rose by up to 167.3%; blocked runs tended to run into timeouts or wrong solutions instead of stopping early | https://arxiv.org/abs/2608.02670 | 2026-08-02 | Verified (authors' measurement).
- Repository: 89 tasks, three policies, verifier running outside the hardening boundary, packaged for a common evaluation framework; one commit, 28 stars | https://github.com/boundary-bench/boundary-bench | MIT | Verified (stars are a weak signal).
- Strictest-policy leaderboard rows cost roughly 59 to 375 dollars per agent | same | - | Verified (self-reported).
- Take: every new deny must come with a reason the agent can act on, and repeated denials must feed a stop condition; the kit's own evaluation should include a guard-on against guard-off comparison. Cost: counters in the controller.

### D8. MicroVM and container routes
- Docker Sandboxes: `sbx` CLI; local use free including commercial use; sign-in required; the documentation index lists GPU passthrough, credentials, an upstream proxy and an MCP gateway as topics | https://docs.docker.com/ai/sandboxes.md | read 2026-11-11 | Verified (index only).
- GPU passthrough limited to supported Linux hosts, and the Windows requirements | search summary; the GPU page address I tried returned not found | - | Unverified.
- Tracekit Box v0: each job in a Firecracker micro-VM with no network interface; commands, egress, secrets, model calls and the workspace patch go through host-side channels; a signer the agent cannot reach decides and signs each action; secrets stay on the host and are substituted by a proxy for bound hosts; private and metadata addresses are refused; changes come back as a patch applied after approval; 13 end-to-end checks, 15 fuzz targets with 9 findings fixed; limits listed by the authors include an unexercised jailer, a co-located signer and a KVM requirement | https://arxiv.org/abs/2610.38458 and https://github.com/Cygnux-Labs/Tracekit-box | v1, 2026-10-28; MIT | Verified (authors' tests).
- libkrun through Podman: microVM containers that start in hundreds of milliseconds; the article says it is not a bulletproof boundary and does not address GPUs | https://fedoramagazine.org/sandbox-ai-coding-agents-with-microvms-on-fedora-linux/ | 2026-06-15 | Verified. A reader comment about firewall bypass in one networking mode | same | - | Unverified.
- kern: rootless, daemonless runtime with WSL2 support; README says GPU is not currently supported; benchmarks are its own | https://github.com/getkern/kern | Apache-2.0 | Verified.
- open-cowork: routes shell commands to a WSL2 VM with a two-way synced workspace on Windows and to a Lima VM on macOS; falls back to native execution with path restrictions; no network isolation described | https://github.com/OpenCoworkAI/open-cowork | MIT | Verified.
- GPU passthrough into a container on Windows through WSL2 | - | - | Unverified (not checked in this session; needs the local trial).
- Take: no microVM product has a verified GPU path on the Windows and WSL2 target, so the practical optional routes are a container with a default-deny firewall, or WSL2 with the built-in sandbox plus a launch broker. Ideas worth reusing from Tracekit Box: host-side decisions, secrets that never enter the agent's environment, changes returned as a patch.

### D9. Practitioner guidance on isolation and credentials
- Security-firm essay: private data, untrusted content and an outbound channel together are the dangerous combination; default-deny reads and block credential directories; protect agent settings and git config; keep egress rules the same for the web-fetch tool and the shell; use mock or scoped development credentials and an injecting proxy outside the sandbox; classifier modes do not replace deterministic sandboxing; prefer VM-level isolation because containers were not designed as a hard boundary | https://www.latacora.com/blog/2026/09/18/fire-the-slop-cannons-safely-on-coding-agents-and-sandboxing/ | 2026-09-18, updated 2026-10-29 | Verified (expert opinion, no measurements). Its quoted 11% miss rate for one auto mode | same | - | Unverified (secondary).
- One practitioner's setup: a fine-grained token per sandbox limited to chosen repositories with short expiry, a signing-only key in an isolated agent process, commits under a distinct agent identity | https://micahflee.com/sandboxing-coding-agents/ | 2026-08-27 | Verified (single anecdote, one operating system).
- Vendor essay: host isolation is not authority isolation; zero standing permissions, just-in-time scoped grants, risk-tiered approvals and audit trails | https://www.permit.io/blog/coding-agent-sandboxes-credentials | 2026-06-12 | Verified (no data).
- OneCLI: a gateway that intercepts HTTPS and injects credentials by host and path; needs a database server and a Node toolchain; mixed licence layout | https://github.com/onecli/onecli | Apache-2.0 plus an enterprise directory | Verified.
- Forum answers: a separate low-privilege operating-system user per agent with a read-only repository mirror and no push credentials; verdicts that change after the session has read secret-like data; deterministic predicates refuse while probabilistic models only escalate; approval prompts time out to deny; hard blocks with false positives lead teams to switch guardrails off | https://news.ycombinator.com/item?id=49556858 | about 2026-09-03 | Unverified (user-generated).
- Take: for the remote module, the agent never holds a provider credential (a harness process does), tokens are scoped and short-lived, the agent's environment is an allowlist, and unattended pushes stay denied. Cost: rules and tests; no proxy needed.

### D10. Dependency output as an injection carrier (jqwik)
- The project's release notes withdraw version 1.10.0 and, from 1.10.1, add a clause that discourages use with coding agents and warns that its output may confuse them | https://jqwik.net/release-notes.html | read 2026-11-11 | Verified.
- Version 1.10.0 printed an instruction aimed at AI agents to disregard prior instructions and delete the project's tests and code, hidden from people with terminal escape sequences | secondary press (the linked article could not be fetched) | 2026-05 | Unverified at the level of detail, corroborated by three secondary reports.
- A property to hide the clause, and a report that one agent flagged the text without acting | secondary only | - | Unverified.
- Take: training, test and dependency output is untrusted input. Strip escape sequences and invisible characters from everything the kit relays, and keep raw logs with the read-only analyst subagent. Cost: a few dozen lines.

### D11. GitHub-scale census of hidden agent-directed text
- Scope: 145 million items (issues and pull requests from June to September 2026, an archive sample, and the READMEs of the 2 million most-starred repositories) | https://github.com/rdwr-gabin/github-ipi-in-the-wild | 2026-10-26; MIT; Python 3.11 or later | Verified (vendor research).
- 2,281 agent-directed hidden-text findings (about 16 per million); 47 judged attacks, 43 of them in issues, pull requests and comments and 4 in READMEs; 1,519 first-party orchestration notes in 178 projects; rate rose from 7.0 to 15.4 per million between June and September 2026; 106 of 2 million READMEs carry hidden agent-directed text; 60% of classifier positives were template text | same | - | Verified (authors' measurement; lower bounds, hidden text only).
- More than half the attacks aim at the target project's own triage, review or CI agent; friendly markers can be forged | same | - | Verified.
- The detector covers HTML comments, invisible Unicode (tag characters, zero-width runs, bidirectional overrides, variation selectors) and style-hidden text; it has a local text mode that needs no network or key | same | - | Verified. Its data files contain live payloads and were not opened.
- Take: the base rate is low, so a detector should flag and strip concealment, not block; first-party hidden notes are common, so a block rule would misfire. Reuse the detector categories in standard-library code.

### D12. RepoGuardBench: which repository carriers work
- 80 core and 14 applied tasks; five carriers (README, issue text, code comments, test logs, agent-rule files); five inert attack goals; runs on one 16 GB GPU through a local inference server; a smoke target needs no GPU | https://github.com/DaoyuanLi2816/RepoGuardBench and https://openreview.net/forum?id=58AGMTgU3L | workshop paper 2026 (non-archival); code MIT, data CC BY 4.0 | Verified.
- Proposed-attempt rate by carrier: code comment 50.9%, rule file 45.8%, issue text 13.7%, README and test log 0% | same | - | Verified (authors' measurement, local open models).
- Susceptibility rose with model size in one family: 0% at 1.5B parameters, 22% at 3B, 58% at 7B, 83% at 14B | same | - | Verified.
- Completion under the strict sandbox was 2.1%, mostly rule file leading to test deletion; a path-prefix action gate permits writes under the tests directory, so that attack completed in 15.4% of cases on the 7B model | same | - | Verified.
- Limits: non-adaptive attacks, simple tasks, small local models | same | - | Verified.
- Take: the files an agent treats as instructions (rule files, and comments in code it edits) are the carriers that matter; test logs were not followed in this benchmark, so D10 is a real but less common path. A path-prefix gate is not enough: deleting or weakening tests and evaluation code needs its own rule, which the kit's frozen paths already provide for the evaluator.

### D13. Content that misleads without instructing, and the limits of separation
- Earn-then-Exploit: a site gives several rounds of real, checkable help and then issues out-of-bounds instructions; 56 environments; average attack success 71.4% across three agent and model pairs (60.7% to 85.7%); separating action authorization from content gave 0% attack success at 100% task completion in the authors' test | https://arxiv.org/abs/2611.00725 | v1, 2026-10-31 | Verified (self-reported).
- Task-tampering benchmark: injection defined by authority (content that tries to influence a decision its source is not entitled to make); 90 cases; detection-and-removal defences leave observation attacks at 9.5% and state attacks at 12.1% (objective attacks 2.4%); a tool-policy defence gave 15.4% against 17.0% undefended | https://arxiv.org/abs/2611.07640 | v1, 2026-11-05 | Verified (authors' measurement; code published).
- Impossibility argument from contextual integrity: separating data from instructions both misses attacks and degrades appropriate behaviour; 96.7% attack success for one attack class | https://github.com/compass-group-tue/prompt_injections_so_back | conference paper 2026 | Verified (repository and paper summary).
- Take: a scouted page can bias hypothesis choice with a false claim and no instruction at all. So: scout in a separate tool-restricted process, validate its output as data with sources, and let only harness-run experiments decide. No filter is expected to close this.

### D14. Persistence and model-side findings
- Multi-step trojan: an injection is read, stored in workspace state and executed in a later step; 95.5% attack success on one frontier model against near zero for single-turn attacks; per-step defences miss the planting write; the proposed defence scans control-like text in sensitive local files and traces where it came from | https://arxiv.org/abs/2605.31042 | 2026-05-29; code published | Verified (authors' measurement).
- Self-evolution (skill updates or reinforcement from user feedback) raised injection success by 14.0 to 48.8 points and 3.0 to 39.3 points respectively | https://arxiv.org/abs/2610.39122 | v1, 2026-10-29 | Verified (authors' measurement).
- Reserved-token injection: forged chat-template markers are 39 to 66 points more effective when encoded as reserved tokens than as ordinary subwords in three of four model families; instruction tuning strengthens the effect; the tokenizer-level mitigation covers only declared special tokens, and in 33 of 67 tokenizer configurations (255 of the 400 most-downloaded chat models) tool-protocol tokens are left intact | https://arxiv.org/abs/2609.35932 | v1, 2026-09-28; code and dataset published | Verified (authors' measurement).
- Take: (a) the journal, notes and any memory file the loop writes are places where injected text can wait, so harness code, not the agent, should write the ledger, and free-text fields the agent later re-reads should be short and typed; (b) the kit should not let the agent rewrite its own skill or rules from experience; (c) for language-model fine-tuning, check datasets for raw template markers that would be encoded as control tokens (my inference from the paper's mechanism).

### D15. Threat-intelligence report on attacks in the wild
- Reported: a tracked group placed adversarial text in script loader comments to defeat LLM-based scanners; backdoored MCP tools; poisoned package metadata; malicious configuration files in coding-assistant project directories that push assistants to run scripts | trade-press coverage of a vendor threat report dated 2026-09-08; the primary page could not be fetched | - | Unverified.
- Take: nothing rests on this alone; it agrees with D6, D11 and D12 on configuration files and comments as carriers.

### D16. Destructive MCP tools without approval
- About 90% (95% interval 82 to 95) of destructive tools in a 1,000-repository registry sample have no server-side confirmation; 32 of 41 popular hosts and SDKs have no approval step by default; 60.7% of tool and host pairs have no enforced human approval; an injected deletion executed in 479 of 960 runs; prompting for every tool not annotated read-only or non-destructive would cut the unapproved share to 5.4% | https://arxiv.org/abs/2611.02527 | v1, 2026-11-02 | Verified (authors' measurement).
- Take: in unattended mode load only an explicit MCP configuration and allow only tools on a pinned read-only list; the kit's existing ask rules for repository, Space and paid-job tools become denies. Cost: generated settings and guard cases.

### D17. Skill scanners
- SkillSpector: 71 static patterns in 17 categories, syntax-tree and taint analysis, signature rules, vulnerability lookups, optional model stage; offline mode; JSON, Markdown and SARIF output; exit codes for CI; Python 3.12 or later; no tagged releases; no accuracy figures | https://github.com/NVIDIA/SkillSpector | Apache-2.0; 2,440 commits | Verified (about 25k stars is a weak signal).
- Measured on 140 skills (80 malicious, 60 benign): one static scanner in default mode reached 0.91 recall while flagging 33 of 60 benign skills, and 0.85 recall with 40 false positives when its model stage was on; static plus sandboxed dynamic evidence reached F1 0.89 with 5 false positives; the full pipeline reached 0.93 precision and 0.85 recall | https://arxiv.org/abs/2611.10830 | v1, 2026-11-07 | Verified (authors' measurement; the scanner measured is not SkillSpector).
- Take: static skill scanners over-flag heavily, and the kit legitimately ships hooks and shell commands, so a scanner is at most a release-time check for the kit's own ports, read by a person. Not a default.

### D18. Treating the model as an untrusted component
- Setup: 13 tasks, 12 tools, two small open models, 156 attack episodes per defence and model | https://arxiv.org/abs/2611.11571 and https://github.com/nawaralseelawi/untrusted-model-agentsec | v1, 2026-11-08 | Verified.
- The models proposed the attacker's call in 64% and 84% of episodes; a task-bound monitor admitted 1.3% and 7.7%; a prompt guardrail moved obedience from 67% to 65% and from 86% to 55%; spotlighting plus a detector left 12% and 0% | same | - | Verified (authors' measurement; static attacks).
- Simulated adaptive attacks under an assumed erosion law: guardrail stacks reached 100% attack success; the task-bound monitor held severe actions at 0%; residual harm 0.69 on a 10-point scale, cut 62% by taint-triggered human review | same | - | Verified as reported; the adaptive part is a simulation, not a measurement.
- Attack variants admitted: 18 of 33 by a naive monitor, 6 by a hardened one, 1 by a capability-bound one | same | - | Verified.
- Take: put the decision in code that the model cannot talk to. For the kit: an allowlist mode for the guard during unattended runs, bound to the declared task (run-controller verbs, tests, commits in the work tree). Cost: template matching and tests; too strict a list triggers the grinding measured in D7.

### D19. Consequence-aware approval (Caper)
- Approvers that read only the command text miss effects hidden in the code a command invokes. The system runs each command in a snapshotted sandbox, gives an independent approver a bounded report of observed effects, commits allowed commands and rolls back blocked ones with a reason | https://arxiv.org/abs/2610.40753 | v1, 2026-10-29 | Verified.
- Harmful-outcome rate 6.7% against 14.8% or more for six other systems on one benchmark, and 7.8% against 35.3% or more on the authors' own benchmark; 1.0% of safe twins blocked | same | - | Verified (self-reported; no code address).
- Take: the principle (judge effects, not text) is what the kit's frozen evaluator and git revert already do for code changes. The snapshot machinery is not worth building; training runs have effects that do not roll back cheaply.

### D20. Structural and rule-engine designs
- bravebot: untrusted content never enters the planner's context (references only); tool-less processors return one immutable data slot; a manifest mode writes the full plan before reading anything, with one approval and no model in the control path; experimental, no benchmarks | https://github.com/brave/bravebot | MPL-2.0 | Verified.
- belay v0.2.2: native hooks for the three target agents; deterministic deny, ask and allow, with ask denied on timeout; states it is pattern-based, not a full sandbox, and that an interpreter-wrapped call can slip through; no test corpus | https://github.com/SECBLOK/belay | AGPL-3.0-or-later | Verified.
- jev-guard: depends on a hosted model service and a key; fails open by default; sends tool calls to the provider; evidence is a 21-call calibration; notes that two other agent CLIs have no native ask decision | https://github.com/leepokai/jev-guard | MIT | Verified (the last point is that README's claim about other products: Unverified).
- Take: the planner and processor split is the pattern behind the quarantined scout. The two guard products are rejected (licence and overlap; data export and fail-open). Their admissions confirm that pattern guards can be bypassed by wrapping a command in an interpreter.

### D21. Greedy keep rules and anytime-valid acceptance (PACE)
- Claim: keeping an edit whenever the score went up, applied repeatedly against the same noisy development estimate, is adaptive multiple testing | https://arxiv.org/abs/2606.08106 | v1, 2026-06-06; single author; no code | Verified.
- Method: candidate against incumbent on identical instances; a testing-by-betting process over discordant pairs; early stopping; per-decision false-commit probability at a user-set level; a candidate is rejected if the budget runs out | same | - | Verified.
- Results on three question-answering sets with small open models: greedy commits were 30 to 42% false and 10 to 33% harmful; with no real gain available greedy made 13 to 21 spurious commits per run (72 to 100% false) and degraded the most fragile agent by 4.9 points; the gated loop stayed at baseline and used about 18% less evaluation | same | - | Verified (self-reported).
- Limits found by a second search: other preprints report materially lower power for anytime-valid tests than for fixed-sample or group-sequential designs, and a need for burn-in | search summaries of three preprints, not opened one by one | - | Unverified at the level of detail.
- Take: the loop needs a keep gate with a stated error rate. Ship a fixed-budget paired test first (simplest), and trial the sequential gate against it on saved per-example outputs. Cost: standard-library arithmetic; the evaluator must emit per-instance results.

### D22. "Hard to Fool": a bounded research loop
- The model proposes and trusted code decides; proposals are strict declarative JSON over a fixed vocabulary; data sits in immutable chronological stores for discovery, validation and final holdout; the holdout opens exactly once and only after a durable receipt is written; acceptance is a conjunction of absolute gates; duplicate hypotheses are refused before they consume a trial; a hash-chained append-only ledger records every formulation, refusal, crash and result | https://arxiv.org/abs/2611.06607 and https://github.com/henryzhangpku/autonomous-quant-researcher | v1, 2026-11-04 | Verified.
- Across about two dozen campaigns two results survived the pre-registered bars; the survivor proposed by the language model had a Sharpe ratio near 3 in discovery and validation and 0.26 on its single holdout use | same | - | Verified (single author, self-reported, finance domain).
- Take: four mechanisms transfer directly and need only the standard library: single-use holdout with a receipt, hash-chained ledger, duplicate refusal, conjunction of pre-declared gates. The declarative vocabulary fits configuration changes but not code changes (Trial).

### D23. Pinned evaluators and pre-registered falsifiers
- An autoresearch protocol for a wireless ML problem used a hash-pinned evaluator, an enforced inference contract and a falsifier registered before each experiment; 81 unattended experiments in 26 hours reached 99.5% of the reference at far lower inference cost | https://arxiv.org/abs/2608.26093 | v1, 2026-08-26; no code address | Verified (authors' report).
- A frozen validator rejects unsafe agent-proposed schedules before launch: 7,160 adversarial schedules with zero false accepts; the unattended loop improved its own baseline 1.25 to 1.72 times | https://arxiv.org/abs/2606.09682 and https://github.com/RightNow-AI/AutoMegaKernel | v1, 2026-06-08 | Verified (authors' measurement).
- Take: the kit already hashes frozen paths. Add: the evaluator hash is checked by harness code at every keep decision and written to the ledger; each run records its falsifier before launch.

### D24. Correctness gate for throughput tuning (ATTUNE)
- An agent tunes language-model training throughput within a one GPU-hour budget, one setting at a time; a correctness gate outside the agent rejects changes known to alter training; the paper says earlier tuners can ship changes that silently change what the model learns | https://arxiv.org/abs/2610.17528 | v3, 2026-10-30 (v1 2026-10-13); code and a public leaderboard announced | Verified.
- Reported speed-ups: 1.7 times on average and up to 3.9 times over expert recipes; 7 to 26% on vendor recipes; up to 2.6 times on held-out public recipes | same | - | Verified (authors' measurement).
- Take: a change declared as performance-only must pass an equivalence check (same seed, short run, losses within a tolerance set from repeated reference runs) before speed counts. Cost: doubles the cost of each performance experiment. The code and its licence were not read.

### D25. Where auto-research agents fall short (TraceML, AdaPRA, FARS)
- TraceML: 4,465 human trajectories from 134 competitions; on 7 competitions two agent systems were also run, giving 430 paired human and 207 agent trajectories; agents collapse into narrow loops (one re-weights ensembles and tunes submissions, the other mutates one model in place), pivot less than humans and do not reopen abandoned work; a short planning prompt taken from human practice shifts behaviour and raises scores without closing the gap; a toolkit converts any command-line agent run into a trajectory (no address in the abstract) | https://arxiv.org/abs/2608.26086 | v4, 2026-11-06 (v1 2026-08-26) | Verified (authors' measurement).
- AdaPRA: a process reward agent audits the trajectory and workspace by executing checks with adaptive rubrics; named process errors are insufficient exploration, unsound validation, coding bugs and budget wasted on repeated exploratory analysis and baselines; gains of 24.5 and 14.8 leaderboard percentile points on two task sets | https://arxiv.org/abs/2610.33245 | 2026-10-23; no code address on the page | Verified (authors' measurement).
- FARS: 166 machine-written papers across 67 topics; 282 volunteer reviews of 140 papers; main failure modes are narrow experimental scope, methodological limits and integrity issues | https://arxiv.org/abs/2606.31651 | v2, 2026-07-13 | Verified.
- Take: (a) a planning step at fixed intervals that asks for a change of approach family or a return to a parked branch, triggered by counters in the ledger; (b) four process checks for the reviewer subagent; (c) duplicate refusal (D22). Cost: prompt text and counters.

### D26. Other loop designs read and set aside
- Agora: Git as an append-only graph of results, insights, hypotheses, verifications and reports; 13 workers, about 12 days, 1,703 contributions; development evaluator from 3.39 to 1.899 bits per byte; 165 cross-account verifications of 95 targets with no failures; the authors say there is no matched comparison | https://arxiv.org/abs/2609.18094 | v4, 2026-09-30 | Verified.
- SoL-Pi: token traffic down 44.7 to 49.0% and interface cost down about a third on a 51-task benchmark at comparable performance | https://arxiv.org/abs/2609.20519 and https://github.com/NVlabs/SoL-Pi | v1, 2026-09-17 | Verified (authors' measurement).
- Enmo Safety: an update is kept only if it helps on a held-out split without raising benign refusals; null results on most models; one run per cell | https://arxiv.org/abs/2611.10099 | v1, 2026-11-06 | Verified.
- Take: nothing to adopt. Agora supports the typed append-only record; SoL-Pi is a reminder to measure agent tokens per kept improvement.

### D27. Evidence-gated lifecycle control (Proof-or-Stop)
- Lifecycle states change only on fresh, mechanically verifiable evidence bound to the current source state; agent outputs are treated as claims | https://arxiv.org/abs/2607.14890 | v1, 2026-07-16; no code link on the page | Verified.
- Unattended-loop engine: 10 of 10 scenarios with zero false completion; receipt bundles rejected 18 tamper classes with zero false accepts | same | - | Verified (authors' measurement).
- 9,240-cell ablation: cases that pass visible checks but fail hidden ones fell from 31 of 1,800 in a naive loop to 2 of 1,800 when gated (1.6 points, 95% interval 0.8 to 2.5); a reviewer that was added but did not gate gave 14 of 1,800 | same | - | Verified. Limits: one model family, 24 tasks, self-hosted corpus.
- Take: the kit's reviewer subagent should feed a gate implemented in code, and evidence should carry the commit, evaluator hash and run id so stale evidence is rejected. Cost: a parseable verdict format and a check in the controller.

### D28. agents-never-sleep v1.5.0
- Contract: proceed on a logged, revertible assumption; park only the affected item with the reason and the person's next action; halt on irreversible danger; asking is forbidden while unattended and converted to parking | https://github.com/TokonoMix/agents-never-sleep | v1.5.0; MIT; Python standard library; 228 commits; no tagged releases | Verified.
- Typed outcomes: done, done with low confidence, parked for a decision, parked as foundational, blocked by environment, failed and retryable, failed by agent bug | same | - | Verified.
- Mechanics: a two-command loop where each call is a fresh process over persisted state; the gate is a shell exit code; a red result is classified by snapshot comparison (introduced by the change: revert to last green; pre-existing or flaky: lower confidence); a gate timeout means blocked by environment; git snapshot before edits; heartbeat watchdog with capped restarts; child processes reaped by parent lineage, with an admission that a hard-killed supervisor leaks children; attempt cap per item, forced parking on loops, a low-yield circuit breaker, a fresh session every N items; a ranked morning report | same | - | Verified.
- Only one agent product is verified live; others are built to documented hook contracts; it notes that subagent calls in one other agent bypass its deny hook; POSIX-centred; says its benchmarks are not claimed results; 4 stars | same | - | Verified. Its claim that sessions degrade around a specific item count | same | - | Unverified.
- Take: the contract, the outcome states, the red-result classification and the capped-restart watchdog, re-implemented inside the kit's controller with Windows process handling. Check on each target agent whether subagent tool calls pass through the guard hook.

### D29. Other unattended-run tools
- deadreckon: freezes goal, contract, policy, source digest and launch plan before detaching; two-key gate of deterministic checks in a real sandbox plus a fresh read-only judge that cannot overrule a failed check; an unavailable judge yields needs-review; keyed receipt; macOS and Linux only; live validation described as incomplete | https://github.com/gregce/deadreckon | 1,131 commits, 15 stars | Verified.
- loop-engineering-skill: a loop is limited by its verifier; triage on verifier fidelity, verifier cost, reversibility and decomposability; three stop conditions (target met, no progress on a real signal, budget); the maker must not be able to edit the acceptance contract, locked tests, budgets or stop conditions; escalate on observable events, not self-reported confidence; prefer independent evidence over a different model; a failure taxonomy that includes reward hacking, stop-condition thrash, false done and token black holes | https://github.com/qingqingpi/loop-engineering-skill | MIT, 7 stars | Verified (no measurements).
- night-agent: hour and iteration limits, a gate command before each iteration, scheduling anchored to a usage-limit reset time the user states; invokes the agent headlessly with JSON output, a dedicated settings file and a refusing permission mode, and warns against skipping permissions; notes that the agent exposes no usage interface, so it stops on a limit message; dedicated branch in an isolated work tree; never pushes | https://github.com/jooray/night-agent | MIT, Node 20 or later, 3 commits | Verified.
- Take: freeze the campaign contract before detaching; control-plane files are not writable by the agent; a dedicated work tree and no pushes in unattended mode; usage-limit windows need their own handling (Assess).

### D30. Operations: failures of a 72-hour run, and cleanup ownership
- Four failures reported: saved state silently dropped; a ring-buffer log that overwrote the critical line with a heartbeat; a timezone error that made the queue believe it had already done the work; an empty string that matched the success pattern. Fixes: an evidence log that is never truncated, separate critical and heartbeat streams, one time unit, success decided from the real response, explicit failure outcomes | https://eltoncherrington.github.io/memctl-shop/essay.html | undated essay that promotes a product | Verified as reported (single practitioner).
- A production sandbox service keeps cleanup responsibility after callers time out or cancel; 3.1 million sandboxes over two weeks with none left at client exit | https://arxiv.org/abs/2610.39711 | v2, 2026-10-29 | Verified (operator's own measurement).
- Take: four selftest cases for the run controller; for the remote module, every resource gets a lifetime limit that does not depend on the local controller surviving, plus a reconciliation sweep at start.

### D31. Output and context control
- Instruction-file pattern: cap command output by bytes, not lines, because one long line defeats a line cap | https://github.com/Austin1serb/agents-md | 167 stars | Verified as a pattern; its 50% token-saving figure is an anecdote (Unverified).
- context-mode: hooks plus an MCP server with a per-project full-text index of tool output; median 99.4% bytes saved on outputs of 10 kB or more in its own benchmark; its execute tool runs on the host as the user, so its sandbox wording is not security isolation; hook errors exit silently; Elastic License 2.0; Node 24.15 or later | https://github.com/mksglu/context-mode | active 2026-11-10 | Verified (self-benchmark; about 33.8k stars is a weak signal).
- Take: byte caps inside the run controller's print path (Trial, measure first). The plugin is rejected: licence, runtime, overlap, silent hook failure.

### Second-phrasing searches
- "Anytime-valid or e-process tests, limitations, power": several preprints report lower power than fixed-sample or group-sequential tests and a need for burn-in | search summaries, 2026-11-11 | Unverified at the level of detail. Consequence: offer a fixed-budget paired test as the default keep gate and treat the sequential gate as a trial.
- "MicroVM sandbox for coding agents, limitations, GPU": no product with a verified GPU path on Windows with WSL2 was found; one vendor's documentation lists GPU passthrough as a topic but the page could not be opened | https://docs.docker.com/ai/sandboxes.md | Unverified beyond the index.
- "GPU inside the agent sandbox, bubblewrap device passthrough, alternatives": found the three issue threads in D3 and the equivalent Codex thread; no vendor setting exists for the Claude Code case | D3 sources | Verified.
- "Whole-process sandbox on Windows": found the alpha Windows backend in sandbox-runtime 0.0.82 (D2), which the main documentation pages do not mention | https://github.com/anthropics/sandbox-runtime | Verified.
- One further search (GPU support of one microVM product) was not run because the session's web-search budget was exhausted.

## New concepts (not in README.md or brief.md)

67 terms. Each line: term : one-line meaning | source. All checked 2026-11-11.

1. Trust-handoff escape : the agent writes a file (git hook, editor or agent configuration) that a trusted tool later runs outside the sandbox, so no configured rule is broken | https://carlostapia.cl/notes/sandbox-escapes-no-rule-broken/
2. Sandbox conformance contract : a test made of an attack that must work unsandboxed, a control that must keep working and an expected effect; "control broken" is a verdict of its own | https://github.com/carlostapiacl/sandbox-conformance
3. Whole-process sandbox runtime (`srt`) : wraps the entire agent process, not only its shell tool, under file and network rules | https://github.com/anthropics/sandbox-runtime
4. Fail-closed sandbox start (`sandbox.failIfUnavailable`) : refuse to run commands when the sandbox cannot start; the default is to run them unsandboxed | https://code.claude.com/docs/en/sandboxing
5. Unsandboxed retry (`allowUnsandboxedCommands`, `dangerouslyDisableSandbox`) : a command that fails inside the sandbox may be retried outside it unless this is switched off | https://code.claude.com/docs/en/sandboxing
6. Excluded commands as full-access holes : commands configured to skip the sandbox run with the user's full access | https://code.claude.com/docs/en/sandboxing
7. Mandatory deny paths and the late-created-path gap : a fixed list of files that stay unwritable inside allowed directories; on Linux it is computed at launch and misses repositories created later | https://code.claude.com/docs/en/sandbox-environments
8. Landlock plus seccomp : unprivileged Linux kernel mechanisms used for a sandbox without containers (kernel 6.2 or later in one product) | https://cursor.com/docs/agent/security/run-modes
9. Seatbelt profiles : the macOS `sandbox-exec` policy mechanism behind the macOS sandboxes of all three agents | https://github.com/anthropics/sandbox-runtime
10. `--dev` against `--dev-bind` in bubblewrap : a fresh device directory hides GPU device nodes; binding them back is what CUDA needs | https://github.com/anthropics/claude-code/issues/13108
11. `/dev/dxg` : the device through which WSL2 exposes the GPU; hidden by a fresh device directory | https://github.com/openai/codex/issues/22469
12. Restricted-account sandbox on Windows : a dedicated local account, a write-restricted token, file ACL entries and a Windows Filtering Platform egress filter | https://github.com/anthropics/sandbox-runtime
13. MicroVM per agent job : each job in a small virtual machine with its own kernel (Firecracker, libkrun) | https://fedoramagazine.org/sandbox-ai-coding-agents-with-microvms-on-fedora-linux/
14. Host-side doors with an unreachable signer : every action leaves the VM through a narrow channel and is decided and signed by a process the agent cannot reach | https://arxiv.org/abs/2610.38458
15. Patch-return workspace : the agent's changes come back as a patch applied per file after approval, not as direct writes | https://github.com/Cygnux-Labs/Tracekit-box
16. Docker Sandboxes (`sbx`) : a vendor's microVM sandboxes for coding agents with their own container daemon | https://docs.docker.com/ai/sandboxes.md
17. Domain fronting past a domain allowlist : a proxy that filters by hostname without inspecting TLS can be bypassed through a shared front domain | https://code.claude.com/docs/en/sandboxing
18. Masked credentials (`network.tlsTerminate`) : the sandboxed process sees placeholders and a TLS-terminating proxy substitutes real secrets for bound hosts (experimental) | https://code.claude.com/docs/en/sandboxing
19. Credential-injecting egress proxy : a gateway outside the sandbox adds credentials by host and path, so the agent never holds them | https://github.com/onecli/onecli
20. Host isolation against authority isolation; zero standing permissions : a sandbox limits where code runs, not what its credentials may do; grants should be scoped and just-in-time | https://www.permit.io/blog/coding-agent-sandboxes-credentials
21. Per-sandbox scoped token, signing-only key, distinct agent identity : limits what a leaked credential can do and makes agent commits attributable | https://micahflee.com/sandboxing-coding-agents/
22. Lethal trifecta : private data, untrusted content and an outbound channel together make exfiltration possible | https://www.latacora.com/blog/2026/09/18/fire-the-slop-cannons-safely-on-coding-agents-and-sandboxing/
23. Auto-review classifier : an LLM that approves or blocks each action; vendors state it is not a security boundary | https://cursor.com/docs/agent/security/run-modes
24. Consequence-aware approval : approve from effects observed in a snapshot, not from command text | https://arxiv.org/abs/2610.40753
25. Reference monitor, task-bound and capability-bound : code outside the model that admits only actions consistent with the declared task or the granted capabilities | https://arxiv.org/abs/2611.11571
26. Taint tracking with taint-triggered review : once untrusted content has been read, later sensitive actions need extra review | https://arxiv.org/abs/2611.11571
27. Spotlighting : marking untrusted text so the model can tell it from instructions; weak under adaptive attack in the study read | https://arxiv.org/abs/2611.11571
28. Action-authorization separation : content may inform, but only the user or policy can authorize an action | https://arxiv.org/abs/2611.00725
29. Earn-then-Exploit : a source builds trust with real help over several rounds and then issues harmful instructions | https://arxiv.org/abs/2611.00725
30. Task-tampering injection : content that changes the agent's decision without containing an instruction (injection defined by authority) | https://arxiv.org/abs/2611.07640
31. Contextual-integrity impossibility argument : no separation of data from instructions can be both complete and harmless to legitimate use | https://github.com/compass-group-tue/prompt_injections_so_back
32. Repository-borne injection carriers : README, issue text, code comments, test logs and agent-rule files, with very different success rates | https://github.com/DaoyuanLi2816/RepoGuardBench
33. Hidden-text injection : instructions concealed in HTML comments, invisible Unicode, style-hidden text or terminal escapes | https://github.com/rdwr-gabin/github-ipi-in-the-wild
34. First-party orchestration notes : hidden agent-directed text a project writes for its own bots; common, and forgeable by an attacker | https://github.com/rdwr-gabin/github-ipi-in-the-wild
35. Dependency-output injection : a library prints agent-directed text at run time | https://jqwik.net/release-notes.html
36. Multi-step trojan : an injection is stored in workspace state and executed in a later step | https://arxiv.org/abs/2605.31042
37. Self-evolution eroding robustness : agents that update their own skills or learn from feedback become easier to inject | https://arxiv.org/abs/2610.39122
38. Reserved-token injection : forged chat-template markers that the tokenizer encodes as control tokens | https://arxiv.org/abs/2609.35932
39. Planner and processor separation; manifest mode : the planner never sees untrusted content, and the whole plan can be fixed before anything is read | https://github.com/brave/bravebot
40. Session-state-dependent gating : the guard's verdict changes after the session has read secret-like data | https://news.ycombinator.com/item?id=49556858 (user-generated)
41. MCP tool annotations and the missing-confirmation gap : read-only and destructive hints exist, but most hosts do not enforce approval from them | https://arxiv.org/abs/2611.02527
42. Skill security scanning with SARIF output : static and taint analysis of skill bundles, reported in a standard findings format | https://github.com/NVIDIA/SkillSpector
43. Hybrid static, dynamic and agentic skill analysis : combining evidence types cuts scanner false positives | https://arxiv.org/abs/2611.10830
44. Adaptive multiple testing under a greedy commit rule : repeated keep-if-better decisions against one noisy estimate inflate false keeps | https://arxiv.org/abs/2606.08106
45. Anytime-valid acceptance test (e-process, testing by betting) : a sequential test whose error bound holds at any stopping time | https://arxiv.org/abs/2606.08106
46. Paired evaluation with discordant-pair counting : compare candidate and incumbent on identical instances and count only the disagreements | https://arxiv.org/abs/2606.08106
47. Single-use holdout with a durable receipt : the final set opens exactly once, after a record is written that it is about to open | https://arxiv.org/abs/2611.06607
48. Hash-chained append-only ledger : each record carries the hash of the previous one, so edits and deletions are detectable | https://arxiv.org/abs/2611.06607
49. Declarative proposal vocabulary : the model proposes in strict JSON over a fixed set of operations and code executes | https://arxiv.org/abs/2611.06607
50. Conjunction of absolute acceptance gates : a result is kept only if it passes every pre-declared bar | https://arxiv.org/abs/2611.06607
51. Duplicate-hypothesis refusal : an equivalent proposal is rejected before it spends a trial | https://github.com/henryzhangpku/autonomous-quant-researcher
52. Pre-registered falsifier, hash-pinned evaluator, inference contract : each experiment states in advance what would refute it; the evaluator's hash and call contract are enforced | https://arxiv.org/abs/2608.26093
53. Frozen validator as a launch gate : fixed code rejects unsafe agent proposals before any run starts | https://arxiv.org/abs/2606.09682
54. Correctness gate for throughput tuning : a speed-up counts only if training behaviour is unchanged | https://arxiv.org/abs/2610.17528
55. Evidence-gated lifecycle, false-DONE, receipt bundles : states change only on fresh machine-checkable evidence; agent statements are claims | https://arxiv.org/abs/2607.14890
56. PROCEED, PARK, HALT with typed outcome states : unattended work never asks; it proceeds on a logged assumption, parks the item or halts | https://github.com/TokonoMix/agents-never-sleep
57. Low-yield circuit breaker and forced park : stop or park when recent iterations produce little | https://github.com/TokonoMix/agents-never-sleep
58. Two-key gate with a keyed receipt : deterministic checks plus an independent judge that cannot overrule a failed check; the result is signed with an HMAC | https://github.com/gregce/deadreckon
59. Verifier fidelity and control-plane protection : a loop is limited by how well its check reflects the goal; the maker must not edit the contract, tests, budgets or stop rules | https://github.com/qingqingpi/loop-engineering-skill
60. Reset-anchored scheduling : plan iterations around the time a subscription usage limit resets | https://github.com/jooray/night-agent
61. Narrow-loop collapse, pivot rate, reopen rate : agents keep tuning one thing, seldom change approach and do not return to abandoned branches | https://arxiv.org/abs/2608.26086
62. Process reward agent with adaptive rubrics : an auditor that executes checks on the trajectory and workspace, not only on the final score | https://arxiv.org/abs/2610.33245
63. Git as an append-only research graph with cross-account verification : results, hypotheses and verifications as typed commits, checked by a different worker | https://arxiv.org/abs/2609.18094
64. Policy-graded agent evaluation and the hardening tax : measure task success and cost under nested security policies | https://arxiv.org/abs/2608.02670
65. Service-owned cleanup : the service, not the caller, stays responsible for deleting resources after a timeout or cancel | https://arxiv.org/abs/2610.39711
66. Byte-capped command output : cap by bytes, because one long line defeats a line cap | https://github.com/Austin1serb/agents-md
67. Separate critical and heartbeat log streams : a shared ring buffer can overwrite the one line that matters | https://eltoncherrington.github.io/memctl-shop/essay.html

## Concerns any design must handle

One canonical ID per line, with a few words and the deep read that supports it. IDs name risks, requirements and
failure modes, never products.

Reused from other scouts' drafts with the same meaning (36):

- SEC-PROMPT-INJECTION : untrusted text steering the agent (D10 to D14)
- SEC-INSTRUCTION-FILE-POISONING : rule files and code comments are the most effective carriers (D12)
- SEC-AGENT-DIRECTED-DOC-TEXT : pages and READMEs with text addressed to agents, friendly or not (D11)
- SCOUT-OUTPUT-IS-DATA : scouted claims can bias choices without any instruction (D13)
- SEC-HOOKS-OUTSIDE-SANDBOX : hooks, including the kit's guard, run unsandboxed (D1)
- SEC-MCP-OUTSIDE-SANDBOX : local MCP servers run unsandboxed (D1)
- SEC-HEADLESS-MCP-AUTOLOAD : unattended sessions loading project MCP servers without approval (D16)
- SEC-BYPASSED-APPROVALS : skipping permissions outside an isolated environment (D2)
- SEC-CREDENTIAL-EXPOSURE : default read scope includes credential files (D1, D9)
- SEC-ENV-SECRETS-INHERITED : child processes inherit secrets from the environment (D1, D9)
- SEC-TOKEN-OVERSCOPE : broad or long-lived tokens inside the agent's reach (D9)
- SEC-NETWORK-ISOLATION-UNENFORCED : domain-only filtering, fronting, broad allowed domains (D1, D2)
- SEC-SKILL-SUPPLY-CHAIN : third-party skills, plugins and MCP servers as an attack path (D15 to D17)
- SEC-SCANNER-DATA-EGRESS : guard or scanner tools that send tool calls or code to a hosted service (D17, D20)
- EVAL-EVALUATOR-TAMPER : evaluator changed between runs (D23)
- EVAL-EVALUATOR-REACHABLE : evaluator or verifier inside the agent's write scope (D7, D29)
- EVAL-HOLDOUT-SINGLE-USE : final set consulted more than once (D22)
- EVAL-ADAPTIVE-OVERFIT : repeated selection against one development estimate (D21)
- EVAL-MULTIPLE-COMPARISONS : many keep decisions without error control (D21)
- EVAL-OPTIONAL-STOPPING : stopping an evaluation when it looks good (D21)
- EVAL-SEED-NOISE : differences inside run-to-run variance (D21, D24)
- EVAL-AGENT-REPORTED-METRIC : agent statements treated as results (D27)
- EVAL-POST-HOC-KEEP-RULE : acceptance criteria chosen after seeing results (D22, D23)
- EVAL-AGENT-AUTHORED-THRESHOLDS : the maker can edit thresholds, budgets or stop rules (D29)
- EVAL-ARTIFACT-TAMPER : ledger, receipts or logs edited after the fact (D22, D27)
- LOOP-STAGNATION : many iterations with no real progress (D25, D28)
- LOOP-DUPLICATE-PROPOSALS : the same hypothesis spent twice (D22, D25)
- LOOP-ORPHANED-OR-KILLED-TRAINING : child runs outliving or dying with the supervisor (D28)
- LOOP-STATE-CORRUPTION : saved loop state silently lost or stale (D30)
- BUDGET-USAGE-CAP-DETECTION : no interface to read subscription usage limits (D29)
- AGENT-CONTEXT-COST-GROWTH : tool output and long sessions inflating token cost (D26, D31)
- AGENT-OVERSTRICT-GUARD : false-positive blocks leading to disabled guards or wasted runs (D7, D9)
- AGENT-HOOK-PARITY-GAP : hook decisions and coverage differ between agents (D20, D28)
- PORT-PROTECTION-PARITY-DISCLOSURE : each port must state which protections it lacks (D4, D5)
- OPS-WINDOWS-SUPPORT-GAP : sandboxes and loop tools absent or weaker on native Windows (D1, D5, D29)
- COST-CONTROLLER-CRASH-ORPHAN : paid resources left running when the local controller dies (D30)

New in this note (36):

- SEC-TRUST-HANDOFF-ESCAPE : agent-written hook or configuration later executed by a trusted tool (D6)
- SEC-CONTROL-PLANE-WRITABLE : guard, settings, budgets, ledger or contract writable by the agent (D2, D29)
- SEC-FILE-TOOLS-OUTSIDE-SANDBOX : read, edit and web tools not covered by the shell sandbox (D1)
- SEC-SANDBOX-FAIL-OPEN : commands run unsandboxed when the sandbox cannot start (D1)
- SEC-UNSANDBOXED-RETRY : failed sandboxed command retried outside; excluded commands with full access (D1)
- SEC-SANDBOX-GPU-DEVICE-ACCESS : GPU devices hidden inside the sandbox, forcing a full-access launcher (D3)
- SEC-SANDBOX-PLATFORM-GAP : sandbox strength differs by operating system and agent, untested on Windows (D4 to D6)
- SEC-SANDBOX-LATE-CREATED-PATHS : protected-path list computed at launch misses repositories created later (D2)
- SEC-INJECTION-HIDDEN-TEXT : instructions concealed with comments, invisible characters or escapes (D10, D11)
- SEC-INJECTION-TOOL-OUTPUT : training, test or dependency output carrying agent-directed text (D10)
- SEC-TASK-TAMPERING-CONTENT : false or slanted content that changes decisions without instructing (D13)
- SEC-SOURCE-TRUST-ACCUMULATION : a source that earns trust and then exploits it (D13)
- SEC-INJECTION-PERSISTED-STATE : injected text stored in journal, notes or memory and acted on later (D14)
- SEC-SELF-EVOLUTION-EROSION : self-modified skills or rules weakening protections over time (D14)
- SEC-CAPABILITY-RAISES-SUSCEPTIBILITY : larger models followed injections more often in one benchmark (D12)
- SEC-TOKENIZER-CONTROL-TOKENS : raw template markers in data encoded as control tokens (D14)
- SEC-CLASSIFIER-NOT-BOUNDARY : LLM approval modes treated as isolation (D2, D5)
- SEC-GUARD-PATTERN-BYPASS : pattern guards evaded by wrapping a command in an interpreter (D12, D20)
- SEC-GUARD-FAIL-OPEN : a guard that allows on error or timeout (D20, D31)
- SEC-APPROVAL-TEXT-ONLY : approval from command text misses effects hidden in invoked code (D19)
- SEC-MCP-DESTRUCTIVE-UNAPPROVED : destructive MCP tools executing without confirmation (D16)
- SEC-EGRESS-TOOL-INCONSISTENCY : web-fetch tool and shell under different network rules (D1, D9)
- SEC-SUBAGENT-HOOK-BYPASS : subagent tool calls may not pass through the guard hook (D28; Unverified, needs a test per agent)
- EVAL-SEQUENTIAL-TEST-POWER : anytime-valid gates can reject real improvements at small budgets (D21)
- TRAIN-PERF-CHANGE-ALTERS-LEARNING : a speed change that silently changes what is learned (D24)
- LOOP-ASK-WHILE-UNATTENDED : a prompt or an approval fallback stalling a run nobody watches (D5, D28)
- LOOP-DENIAL-GRIND : a blocked agent burning budget instead of stopping (D7)
- LOOP-NO-PIVOT-OR-REOPEN : narrow tuning loops, no change of approach, no return to parked branches (D25)
- LOOP-FALSE-COMPLETION : work marked done on visible checks while hidden ones fail (D27)
- LOOP-REVIEWER-NOT-GATING : a reviewer whose verdict does not block (D27)
- OPS-FALSE-SUCCESS-MATCH : success detected from an empty or loosely matched string (D30)
- OPS-LOG-RING-OVERWRITE : critical log line overwritten by heartbeats or truncation (D30)
- OPS-CLOCK-TIMEZONE-MIX : mixed time units or zones corrupting deadlines and schedules (D30)
- OPS-WATCHDOG-RESTART-STORM : uncapped restarts repeating a failing step (D28)
- OPS-SANDBOX-RESIDUE-AFTER-KILL : placeholder files or mounts left after a hard kill (D2)
- COST-HARDENING-TAX : stricter policy lowering success and raising spend (D7)

## Redirect attempts

None was acted on, except item 4 as stated.

1. A search tool's rate-limit error told the client to create an account and an API key. Ignored; other tools were used.
2. The agents-never-sleep README contains text addressed to AI agents (never build your own loop or stop early; look to a named other product for verification; a section telling an AI system when to reach for the tool). Treated as data.
3. The vendor documentation pages for one agent open by telling the reader to fetch a complete documentation index file first. Not followed.
4. A fetch tool's redirect notice asked for the Codex sandbox page to be fetched again at a different host. Followed, as a read-only redirect of vendor documentation; recorded here because it is an instruction that arrived in tool output.
5. The night-agent README tells users to have an agent perform its set-up. Ignored; nothing was installed.
6. Search results end with a boilerplate reminder to cite sources, and the budget-exhausted message suggests asking the user to raise a setting. Noted only; no setting was changed and the user was not asked.
7. The jev-guard README quotes sample injection strings. Treated as data.
8. The jqwik hidden output instruction (D10) is reported as a finding. It was never encountered live, because nothing was installed or run.
9. The data files of the GitHub census repository contain live injection payloads. They were not opened.
10. The GPU feature-request thread contains a wrapper script that users are told to place on PATH. Not run; recorded as an unverified workaround.

## Gaps and unverified points

- The threat-intelligence report in D15 (primary page not fetchable; trade press only).
- The jqwik details beyond the project's own release notes: the hidden instruction text, the hide property, and the report that one agent flagged it.
- The quoted 11% miss rate for one auto mode (secondary).
- Docker Sandboxes GPU passthrough and its Windows requirements (the GPU page address returned not found; the follow-up search was not run because the web-search budget was used up).
- GPU passthrough into a container on Windows through WSL2: not checked from a primary source in this session; the local trial decides it.
- Whether CUDA works under sandbox-runtime: on Linux it is likely blocked for the same reason as D3, on the Windows backend it is likely to work; both are untested.
- The Codex version that fixed the WSL2 GPU defect; the cause of the third Claude Code GPU report; the community `bwrap` wrapper.
- Strength of the Codex native Windows sandbox, and whether Cursor has any sandbox on Windows (the documentation is silent; the only cross-sandbox lab is Linux only).
- Power figures for anytime-valid tests (search summaries only).
- All star counts, and all self-reported benchmarks (kern, context-mode, belay, jev-guard, SoL-Pi, Caper, Earn-then-Exploit, PACE, ATTUNE, Tracekit Box).
- Single-source claims: sessions degrading after a certain number of items; a 50% token saving from byte caps; the forum practices in D9; a reader comment on firewall bypass in D8; that subagent calls bypass hooks on one agent; that two agents have no native ask decision.
- TraceML toolkit availability; ATTUNE licence and single-GPU behaviour (code not read).
- Items under "Outside this facet, left to other scouts" were listed from the sweep record only and not opened.
- The kit-native candidates (launch broker, allowlist guard mode, preflight, sanitiser, ledger, keep gate) are designs inferred from the evidence; none was built or run here.

Skipped or not checked, and risk: nothing was installed, downloaded or executed, so every "works" claim about a tool rests on its documentation or its authors; the candidates file was written by hand and not machine-validated; three results that most affect the isolation design (GPU under sandbox-runtime, GPU in a container on WSL2, Docker Sandboxes on Windows) need the local trials named in the candidates file before any of them is recommended.
