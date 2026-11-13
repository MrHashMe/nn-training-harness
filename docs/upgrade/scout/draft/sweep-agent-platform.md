# Scout note: agent-platform facet (unanchored sweep)

Checked 2026-11-11. Input: `docs/upgrade/scout/sweep/agent-platform/sweep.md` and `vocabulary.md`
(sweep run 2026-11-10 19:59 UTC, window since 2026-05-14; 284 records: github 87, arxiv 60, hf 43, hn 43, openalex 51).

**Status key, used on every claim.** V = Verified: read in the named primary source on 2026-11-11 (for papers this
means the arXiv abstract page, not the full text). I = Inferred: my reasoning from verified facts, or a figure taken
from a secondary source. U = Unverified.

**Reading the evidence.** Paper numbers are the authors' own measurements unless a line says "independent". Star
counts are adoption signals only and are called weak wherever they are all there is. Pages were read through a fetch
tool that returns extracted text, so wording here is paraphrased and must be re-read at the source before it is
copied into kit documentation.

**Not done.** Nothing was installed, cloned or run, so no candidate was tried. Papers were not read beyond the
abstract. The web-search budget for this run ran out after six queries (a seventh, on a shared "Agent Plugins"
manifest, was refused) and one search service was rate-limited for the whole session. One primary page (JetBrains)
returned 403 and one site served scrambled text.

## 1. Summary (10 lines)

1. Scope: 284 sweep records screened, 115 selected as relevant plus 14 sources reached from them; about 60 primary
   pages opened on 2026-11-11; 49 candidates scored in the JSONL file.
2. Convergence is real. All three target agents now read AGENTS.md, load SKILL.md skills and run command hooks before
   tool calls. Codex and Cursor share `.agents/skills/`; Cursor also reads Claude Code's skill folders and hook config.
3. The hook contracts differ exactly where the kit's guard decides. Codex PreToolUse has no "ask", does not run new or
   changed hooks until a person trusts them again, and lets the tool run when the hook errors or times out. Cursor
   fails open unless `failClosed` is set and does not enforce "ask" on preToolUse. Most kit rules answer "ask".
4. The current installer can cause a regression today: creating CLAUDE.md in a repository that only had AGENTS.md makes
   Claude Code (2.1.277 and later) stop reading that AGENTS.md. A one-line import fixes it. Codex also stops reading
   instruction files at 32 KiB.
5. Measured value of instruction text is close to zero: two controlled studies found no correctness gain from context
   files and about 20% more cost; expert-persona profiles cost 2.2 to 4.5 times more and lost 10 points under budget
   limits. Keep the always-loaded block short and put invariants in code.
6. Skills help when few and curated (+16.6 points in SkillsBench) and hurt when duplicated: a similar co-installed
   skill silently takes 1 run in 5, and registry skills can be poisoned in ways current scanners miss. The port itself
   creates duplicate copies of the kit's skill.
7. Approving a command is not approving its effects ("approval laundering"). The frozen evaluator and sealed data need
   effect checks by harness code after each run, bound to hashes taken at launch.
8. Models are weak loop controllers (best 36.25% strict success on full tasks) and self-tuned instructions overfit
   (gain on 5 tuning tasks, none on 10 holdout tasks). Stop, budget and keep decisions belong in code, with a holdout.
9. For ML training specifically: purpose-built training interfaces beat a raw shell on PostTrainBench (+3.7 and +7.5
   points, self-reported); unattended agents there trained on test data and downloaded finished checkpoints.
   AutoWorldModel-Bench (600-second training runs) is the cheapest public task set for a paired with-kit and
   without-kit test.
10. Limits: search budget exhausted after 6 queries; papers read at abstract level; nothing installed or run. Whether
    hooks run in the headless modes of Codex and Cursor is undocumented and must be tested before the port is designed
    around them.

## 2. Kit facts these findings touch (local read, 2026-11-11)

- `install.py` (lines 212 to 222) writes the rules block to CLAUDE.md and creates the file when it does not exist. (V)
- `.claude/hooks/nn_guard.py` reads Claude Code shapes: tool names Bash, Monitor, PowerShell, Read, Grep, Glob and so
  on; paths from `tool_input.file_path`, `notebook_path` or `path`; project root from `CLAUDE_PROJECT_DIR` or `cwd`. (V)
- Most guard rules answer "ask": mentions of sealed paths, recursive sweeps, the final evaluation, edits to frozen
  files and to the harness, kill and stop commands, deletes, destructive git, any push, dependency changes. Only direct
  sealed-data access and writes into a live run answer "deny". "ask" becomes "deny" only when `permission_mode` is
  `bypassPermissions`. An internal guard error also answers "ask". (V)
- The audit log is plain JSON lines, rotated at 1 MB into a single `guard.log.1` (older history is overwritten); a
  write error is ignored; allowed calls are not logged. (V)
- Default `harness_paths` in `expctl.py` protect `.claude/hooks`, the settings files, the config, the skill folder,
  `.claude/agents`, `.mcp.json` and `CLAUDE.md`. No file outside `docs/` mentions AGENTS.md, `.agents`, `.codex` or
  `.cursor`. (V)

## 3. Selected items (one line each)

Tags: D = deep read, S = shorter read, L = listed only (not opened; the line is from the sweep's title and note).
Dates are the sweep's dates unless stated.

### From the sweep: github
1. [S] obra/superpowers: methodology skills shipped as a native plugin per agent; its bootstrap text is lost after compaction on agents without a post-compaction hook. https://github.com/obra/superpowers (2026-11-03)
2. [S] affaan-m/ECC: 314 skills and 71 subagents with per-agent adapters and self-written "instincts"; no measurements. https://github.com/affaan-m/ECC (2026-11-09)
3. [L] mattpocock/skills: personal skills published from an `.agents` directory; sign of that folder convention. https://github.com/mattpocock/skills (2026-11-09)
4. [L] anthropics/skills: reference repository for the Agent Skills format. https://github.com/anthropics/skills (2026-11-06)
5. [S] JuliusBrussee/caveman: terse-output skill claiming a 65% token cut; a paired test measured 8.5%. https://github.com/JuliusBrussee/caveman (2026-11-09)
6. [L] addyosmani/agent-skills: engineering skill collection that users are likely to co-install. https://github.com/addyosmani/agent-skills (2026-11-01)
7. [S] cloudflare/security-audit-skill: coverage ledger, separate verifier, schema-checked findings with three verdicts. https://github.com/cloudflare/security-audit-skill (2026-06-18)
8. [L] davila7/claude-code-templates: registry and CLI that installs third-party skills, hooks and MCP entries. https://github.com/davila7/claude-code-templates (2026-11-10)
9. [D] agentsmd/agents.md: the AGENTS.md format. https://github.com/agentsmd/agents.md (2026-09-10)
10. [S] microsoft/SkillOpt: skill optimizer that keeps an edit only on held-out improvement. https://github.com/microsoft/SkillOpt (2026-11-10)
11. [L] tigerless-labs/autoharness: learns skills from real work sessions. https://github.com/tigerless-labs/autoharness (2026-06-09)
12. [S] diet103/claude-code-infrastructure-showcase: prompt-submit hook that forces skill loading. https://github.com/diet103/claude-code-infrastructure-showcase (2026-07-13)
13. [L] tryatlas/atlas: source control that tracks changes per agent. https://github.com/tryatlas/atlas (2026-05-14)
14. [S] Dicklesworthstone/destructive_command_guard: Rust command guard; its licence carries a vendor-exclusion rider. https://github.com/Dicklesworthstone/destructive_command_guard (2026-11-09)
15. [S] entireio/cli: agent sessions stored as git checkpoints linked by a commit trailer. https://github.com/entireio/cli (2026-11-10)
16. [S] lennney/stop-that-shit: hook and skill guard with one runtime and a written host-adapter contract. https://github.com/lennney/stop-that-shit (2026-08-11)
17. [L] ciembor/agent-rules-books: AGENTS.md rule sets for Codex, Cursor and Claude Code. https://github.com/ciembor/agent-rules-books (2026-09-10)
18. [L] microsoft/skills: vendor skills, MCP servers and AGENTS.md files for SDKs. https://github.com/microsoft/skills (2026-11-10)
19. [L] rohitg00/pro-workflow: memory that rewrites itself from user corrections. https://github.com/rohitg00/pro-workflow (2026-09-29)
20. [L] Piebald-AI/tweakcc: patches Claude Code's own system prompts, so an agent's base behaviour can differ per user. https://github.com/Piebald-AI/tweakcc (2026-11-10)
21. [S] kenryu42/cc-safety-net: pre-execution guard for 16 agent CLIs. https://github.com/kenryu42/cc-safety-net (2026-11-10)
22. [L] BayramAnnakov/claude-reflect: writes captured corrections into CLAUDE.md and AGENTS.md. https://github.com/BayramAnnakov/claude-reflect (2026-10-03)
23. [L] agent0ai/dox: self-documenting AGENTS.md. https://github.com/agent0ai/dox (2026-06-01)
24. [S] kunchenguid/backpass: proposes AGENTS.md edits with quoted transcript evidence, applied by a person. https://github.com/kunchenguid/backpass (2026-08-21)
25. [L] first-fluke/oh-my-agent: skill presets for Claude Code, Codex and Cursor. https://github.com/first-fluke/oh-my-agent (2026-11-10)
26. [L] fcakyon/claude-codex-settings: one person's shared configs and hooks for the three target agents. https://github.com/fcakyon/claude-codex-settings (2026-11-10)
27. [L] Kulaxyz/self-learning-skills: harvests a session's working path into a skill. https://github.com/Kulaxyz/self-learning-skills (2026-06-28)
28. [S] tuchg/Lucarne: approve or deny agent prompts from a phone. https://github.com/tuchg/Lucarne (2026-05-17)
29. [S] habit-hooks/habit-hooks: hook checks that answer with coaching text. https://github.com/habit-hooks/habit-hooks (2026-05-26)
30. [S] K-Dense-AI/scientific-agents: expert-persona AGENTS.md profiles. https://github.com/K-Dense-AI/scientific-agents (2026-06-03)
31. [L] ilindaniel/ponytail-lite: one AGENTS.md file offered in place of a plugin. https://github.com/ilindaniel/ponytail-lite (2026-06-28)
32. [S] AGGIB/Stroq: finds secrets in agent transcripts and guards outbound calls. https://github.com/AGGIB/Stroq (2026-09-04)
33. [S] PrimeFoldTools/Andon: stop hooks that check "done" claims, plus a defect ledger. https://github.com/PrimeFoldTools/Andon (2026-06-24)
34. [S] leepokai/jev-guard: hosted classifier that scores each tool call. https://github.com/leepokai/jev-guard (2026-09-17)
35. [L] Dicklesworthstone/skillranker: ranks skills for the next step from live context. https://github.com/Dicklesworthstone/skillranker (2026-09-17)
36. [S] qkal/Canny: deterministic hooks decide and a model only advises; append-only ledger. https://github.com/qkal/Canny (2026-09-11)
37. [L] ghy196830-del/agent-watch-approve: approvals from a watch. https://github.com/ghy196830-del/agent-watch-approve (2026-06-06)
38. [L] lploc94/raw-cli: forkable harness with approvals and ACP. https://github.com/lploc94/raw-cli (2026-09-25)
39. [L] Alejandros17487/ai-jailbreaks: jailbreak prompts packaged as AGENTS.md files; instruction files as an attack vector. https://github.com/Alejandros17487/ai-jailbreaks (2026-10-21)
40. [L] TioSatrio100/MiniML-Lab: ML-workflow agent platform with no adoption; nothing to take. https://github.com/TioSatrio100/MiniML-Lab (2026-10-19)

### From the sweep: arxiv
41. [D] StealthyPoison: procedural poisoning of third-party skills. https://arxiv.org/abs/2611.12155 (2026-11-09)
42. [L] SMO: compiling natural-language skills into graphs of reusable steps. https://arxiv.org/abs/2611.12041 (2026-11-09)
43. [S] Detecting Silent Faults at the Environment-Trainer Boundary in Reinforcement Learning. https://arxiv.org/abs/2611.08144 (2026-11-05)
44. [L] Specification-Driven Governance for Fairness-by-Design in Agentic Software Engineering. https://arxiv.org/abs/2611.03231 (2026-11-02)
45. [D] Lessons Outlive Their Failures: a case study of rules for AI coding agents. https://arxiv.org/abs/2610.32578 (2026-10-23)
46. [L] Training the Whole Agent, Not Just the Model: harness updated alongside the policy. https://arxiv.org/abs/2610.28069 (2026-10-20)
47. [D] One Skill Too Many: how co-installed skills conflict. https://arxiv.org/abs/2610.11647 (2026-10-08)
48. [S] Humanize: judgement engineering for agentic coding. https://arxiv.org/abs/2610.08900 (2026-10-06)
49. [S] VERSE: verified self-evolving optimizer for agent harnesses. https://arxiv.org/abs/2610.02616 (2026-10-02)
50. [D] CATP: local agent authorization and audit evidence. https://arxiv.org/abs/2609.38223 (2026-09-28)
51. [D] Agent Approval Laundering: transitive effects beyond the approved invocation. https://arxiv.org/abs/2609.28586 (2026-09-23)

### From the sweep: hf papers
52. [S] SkillOpt: executive strategy for self-evolving agent skills. https://huggingface.co/papers/2605.23904 (2026-05-22)
53. [L] Code as Agent Harness (survey). https://huggingface.co/papers/2605.18747 (2026-05-18)
54. [L] Harness Handbook: mapping agent behaviours to harness source. https://huggingface.co/papers/2607.13285 (2026-07-14)
55. [D] LoopArena: models as runtime controllers for loop engineering. https://huggingface.co/papers/2608.28281 (2026-08-28)
56. [L] SkillsVote: lifecycle governance of agent skills. https://huggingface.co/papers/2605.18401 (2026-05-18)
57. [S] An Empirical Study of Harness Design for Coding Agents. https://huggingface.co/papers/2609.20804 (2026-09-17)
58. [D] Demystifying Agent Skills: why they work until they don't. https://huggingface.co/papers/2608.14036 (2026-08-14)
59. [L] Progressive Agent Skill Generation via Reinforcement Learning: rollback rewards for skill edits. https://huggingface.co/papers/2608.01678 (2026-08-03)
60. [L] SkillOpt-Lite: a minimal skill-optimization pipeline. https://huggingface.co/papers/2607.03451 (2026-07-03)
61. [L] From Raw Experience to Skill Consumption: model-generated skills vary widely in value. https://huggingface.co/papers/2605.23899 (2026-05-22)
62. [L] SkillGrad: gradient-descent-style skill optimization. https://huggingface.co/papers/2605.27760 (2026-05-26)
63. [L] SkillHone: skill evolution with a persistent decision history. https://huggingface.co/papers/2606.08671 (2026-06-23)
64. [S] Harness-of-Harness: multi-day autonomous development with an outer loop. https://huggingface.co/papers/2609.01481 (2026-09-01)
65. [D] AutoTrainess: structured interfaces for autonomous LLM training. https://huggingface.co/papers/2606.31551 (2026-06-30)
66. [L] ToFu: a white-box, token-efficient research harness. https://huggingface.co/papers/2607.11423 (2026-07-13)
67. [L] ENPIRE: closed-loop agentic policy self-improvement, a robotics analogue of the research loop. https://huggingface.co/papers/2606.19980 (2026-06-18)
68. [D] AutoWorldModel-Bench: benchmark for automated world-model research. https://huggingface.co/papers/2608.11216 (2026-07-20)
69. [S] What Open-Source Projects Tell Their Coding Agents: a census of AGENTS.md and CLAUDE.md. https://huggingface.co/papers/2610.31715 (2026-10-22)
70. [D] Scientific Agents: profession-specific system prompts on scientific tasks. https://huggingface.co/papers/2610.00084 (2026-09-07)
71. [D] Do Context Files Help Coding Agents? A two-agent ablation. https://huggingface.co/papers/2607.27250 (2026-07-28)

### From the sweep: hn
72. [D] Claude Code now reads AGENTS.md if there is no CLAUDE.md (changelog). https://code.claude.com/docs/en/changelog (2026-09-18)
73. [D] Claude Code reads AGENTS.md only when telemetry is on [fixed]. https://blog.szypowi.cz/p/claude-code-reads-agents.md-only-when-telemetry-is-on/ (2026-09-23)
74. [L] My agent.md to improve LLM-assisted code quality. https://fabiensanglard.net/agent.md/index.html (2026-08-23)
75. [L] Feature request: support AGENTS.md (Claude Code issue 6235). https://github.com/anthropics/claude-code/issues/6235 (2026-08-19)
76. [S] You're probably using Agent Skills wrong (cites SkillsBench). https://notes.ansonbiggs.com/youre-probably-using-agent-skills-wrong/ (2026-06-22)
77. [L] Do agents.md files help coding agents? (social post). https://twitter.com/rasbt/status/2063649136323252397 (2026-06-08)
78. [L] Foremerge: intent conflicts between parallel agents. https://github.com/naw103/foremerge (2026-09-21)
79. [L] capn-hook: hook that caches investigation results. https://github.com/cyrusNuevoDia/capn-hook (2026-07-12)
80. [L] QUALITY.md: another agent-facing file format. https://getquality.md (2026-07-02)
81. [L] skillbay.sh: human-curated skill marketplace. https://skillbay.sh/ (2026-09-17)
82. [L] agent-skills.market: skill marketplace. https://agent-skills.market/ (2026-10-19)
83. [S] Your AGENTS.md file doesn't do anything (the page served scrambled text). https://pivot-to-ai.com/2026/08/27/your-agents-md-file-doesnt-actually-do-anything/ (2026-08-28)
84. [S] Agents.md speaks Unix (essay, no data). https://www.fmind.dev/articles/agents-md-speaks-unix/ (2026-09-24)
85. [L] Implement-spec: harness-agnostic spec-to-verified-PR skill. https://github.com/SteveVitali/agent-skills (2026-08-04)
86. [L] Company-wide AGENTS.md service. https://alignbase.ai/ (2026-06-23)
87. [S] SkillOpt project site. https://microsoft.github.io/SkillOpt/ (2026-09-24)
88. [S] What languages are agent skills written in? https://plicara.ai/research/agent-skill-languages/ (2026-08-25)
89. [L] Emacs adds an official AGENTS.md. https://lists.gnu.org/archive/html/emacs-devel/2026-08/msg00077.html (2026-08-06)
90. [L] SQLite adds a prototype AGENTS.md. https://github.com/sqlite/sqlite/commit/a1e5778889252d2609a59fd9b819d70392c5789e (2026-05-22)
91. [S] I used autoresearch to improve my AGENTS.md, measured against real tasks. https://www.stet.sh/blog/how-i-used-codex-to-improve-its-own-agents-md (2026-05-27)
92. [S] Nomos: a Go harness that stops agents from cheating on tests. https://github.com/mgantlett/nomos (2026-11-02)
93. [S] Moving coding-agent guardrails from prompts to hooks. https://tesseracted-labs-blog.vercel.app/enforcing-coding-agent-guardrails-in-the-runtime-instead-of-the-prompt (2026-09-15)
94. [L] PlanBridge: feedback on agent plans before code. https://github.com/contextbridge/planbridge (2026-05-14)
95. [S] RTK hook makes coding agents more expensive, not cheaper. https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/ (2026-07-20)
96. [L] Pawl: hooks against home-directory deletion. https://github.com/ulukaya/pawl (2026-10-07)
97. [S] Filtering secrets from coding agents with a hook. https://crimede-coder.com/blogposts/2026/SecretHooks (2026-07-16)
98. [L] Hapsland: real-time coding-standard advice to agents. https://hapsland.dearlordylord.com/ (2026-10-13)
99. [S] Aperion Shield v0.7: guardrails as git hooks. https://github.com/AperionAI/shield/releases/tag/shield-v0.7.0 (2026-05-26)
100. [L] Sphinx: hook that quizzes the human on the agent's code. https://sphinx-six-theta.vercel.app/ (2026-10-18)

### From the sweep: openalex
101. [L] Agentic Software Engineering: foundational pillars and a research roadmap. https://doi.org/10.1145/3861334 (2026-11-05)
102. [L] Beyond the Protocol: attack vectors in the MCP ecosystem (the kit merges two MCP servers). https://doi.org/10.1109/tse.2026.3694876 (2026-05-20)
103. [S] From Agent Traces to Trust: evidence tracing and execution provenance. https://doi.org/10.48550/arxiv.2606.04990 (2026-06-03)
104. [L] HarnessX: a composable, evolvable harness foundry. https://doi.org/10.48550/arxiv.2606.14249 (2026-06-12)
105. [S] Agent READMEs: an empirical study of context files. https://doi.org/10.1145/3840295 (2026-09-15)
106. [L] Agentic Much? Adoption of coding agents on GitHub. https://doi.org/10.1145/3822180 (2026-06-26)
107. [S] Recursive Harness Self-Improvement. https://doi.org/10.48550/arxiv.2607.15524 (2026-07-17)
108. [S] From Failed Trajectories to Reliable LLM Agents (HarnessFix). https://doi.org/10.48550/arxiv.2606.06324 (2026-06-04)
109. [S] Configuring Agentic AI Coding Tools: an exploratory study. https://doi.org/10.1145/3805760.3814887 (2026-07-05)
110. [L] HarnessEvolve: learning from reference trajectories. https://doi.org/10.48550/arxiv.2609.00829 (2026-09-01)
111. [S] Harness Engineering: a source-code study of eleven systems. https://doi.org/10.48550/arxiv.2609.00006 (2026-07-15)
112. [S] From Registry to Repository: how agent skills are written, adapted and maintained. https://doi.org/10.48550/arxiv.2607.00911 (2026-07-01)
113. [S] Better Harnesses, Smaller Models. https://doi.org/10.48550/arxiv.2607.08938 (2026-07-09)
114. [S] ActPlane: programmable OS-level policy enforcement for agent harnesses. https://doi.org/10.48550/arxiv.2606.25189 (2026-06-23)
115. [L] Claw-SWE-Bench: benchmark for OpenClaw-style harnesses. https://doi.org/10.48550/arxiv.2606.12344 (2026-06-10)

### Reached from the sweep (not in it)
116. [D] Claude Code memory and instruction-file docs. https://code.claude.com/docs/en/memory (undated; checked 2026-11-11)
117. [D] Codex docs: hooks, skills, AGENTS.md, plugins. https://learn.chatgpt.com/docs/hooks (undated; checked 2026-11-11)
118. [D] Cursor docs: hooks, skills, rules, plugins. https://cursor.com/docs/agent/hooks (undated; checked 2026-11-11)
119. [D] AGENTS.md site. https://agents.md/ (undated; checked 2026-11-11)
120. [D] Agent Skills specification. https://agentskills.io/specification (undated; checked 2026-11-11)
121. [D] Evaluating AGENTS.md: are repository-level context files helpful? https://arxiv.org/abs/2602.11988 (v3 2026-09-29)
122. [D] SkillsBench. https://arxiv.org/abs/2602.12670 (v4 2026-06-14)
123. [D] PostTrainBench. https://arxiv.org/abs/2603.08640 (v2 2026-03-10)
124. [D] NVIDIA/skillspector. https://github.com/NVIDIA/skillspector (v2.13.4, 2026-11-04)
125. [S] vercel-labs/skills. https://github.com/vercel-labs/skills (checked 2026-11-11)
126. [S] laude-institute/harbor. https://github.com/laude-institute/harbor (checked 2026-11-11)
127. [D] AutoWorldModel-Bench project page. https://electronicarts.github.io/AutoWorldModelBench/ (checked 2026-11-11)
128. [S] Approve effects, not invocations (blog on the laundering paper). https://www.developersdigest.tech/blog/approve-effects-not-invocations (2026-09-28)
129. [S] JetBrains tests caveman and RTK token claims (secondary report). https://magica.com/news/jetbrains-tests-caveman-and-rtk-token-claims (2026-07-20)

## 4. Deep reads

Every claim line ends with its status. A block's claims come from the block's source unless a line names another.

### D1. Claude Code: AGENTS.md support and precedence
- **Source, version, date:** changelog https://code.claude.com/docs/en/changelog (latest entry 2.1.322, 2026-11-10);
  memory docs https://code.claude.com/docs/en/memory (undated); blog
  https://blog.szypowi.cz/p/claude-code-reads-agents.md-only-when-telemetry-is-on/ (2026-09-23).
- **Licence, maturity:** proprietary product; feature shipped in 2.1.277 on 2026-09-18, eight weeks before this note.
- **What it does:** Claude Code reads AGENTS.md as a fallback instruction file.
- 2.1.277 added AGENTS.md support for projects without CLAUDE.md, switchable under "Project instructions" in
  `/config`. (V, changelog)
- AGENTS.md is read only when no `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` exists in the working directory
  or above. Setting values: `claude-md-or-agents-md` (default), `claude-md-and-agents-md`, `claude-md`,
  `managed-only`. (V, memory docs)
- `AGENTS.local.md`, `AGENTS.override.md` and anything under `.agents/` are not read as instructions. (V)
- Before 2.1.281 some sessions (Amazon Bedrock, telemetry disabled) read CLAUDE.md only. The first session after an
  upgrade may not read AGENTS.md. (V)
- A CLAUDE.md that imports `@AGENTS.md` is the documented way to share one file, and the file is not loaded twice. (V)
- `InstructionsLoaded` hooks do not fire for an AGENTS.md read through the setting. A SessionStart hook that prints
  AGENTS.md should be removed because it adds a second copy. (V)
- `/doctor prompt-audit` (2.1.283 and later) checks instruction files, rules, skills, commands and subagents for
  outdated or conflicting content. (V; the quality of the audit is not measured anywhere I found)
- The docs say instruction files are context and not enforcement, and point to PreToolUse hooks for blocking. (V)
- In 2.1.277 to 2.1.280 the loader sat behind a remote flag, so `DISABLE_TELEMETRY=1` or
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` silently turned it off. (I: the mechanism is from the blog only; the
  docs' note about versions before 2.1.281 corroborates the effect)
- Consequence: installing the kit into a repository that has AGENTS.md and no CLAUDE.md creates CLAUDE.md and so hides
  the user's AGENTS.md from Claude Code. (I: docs plus local read of `install.py`; not run)
- **Evidence quality:** vendor documentation. HN signals of 741 and 486 points are weak evidence of interest only.
- **Kit could take:** rules block in AGENTS.md; CLAUDE.md reduced to the import plus Claude-only lines; a migration
  that moves the existing block; a selftest that finds the block exactly once in what each agent reads; a minimum
  Claude Code version of 2.1.281, or the import, which works on older versions too.
- **Cost:** one installer change and one migration. Risk: a user setting of `managed-only` ignores project files.

### D2. Codex CLI: hooks, skills, AGENTS.md, plugins
- **Source, version, date:** https://learn.chatgpt.com/docs/hooks, https://learn.chatgpt.com/docs/build-skills,
  https://learn.chatgpt.com/docs/agent-configuration/agents-md, https://learn.chatgpt.com/docs/plugins. The old
  developers.openai.com/codex addresses redirect here. The pages carry no version or date.
- **Licence, maturity:** product docs. Hooks are on by default.
- Hooks are configured in `hooks.json` or a `[hooks]` table in `config.toml`, at user level (`~/.codex/`) and project
  level (`<repo>/.codex/`). The project layer loads only for trusted projects. Plugins can bundle hooks. Managed hooks
  come from `requirements.toml`. (V)
- There are 14 events, including PreToolUse, PermissionRequest, PostToolUse, SessionStart, PreCompact, PostCompact,
  UserPromptSubmit, SubagentStart, SubagentStop and Stop. (V)
- Hook stdin carries `session_id`, `transcript_path`, `cwd`, `hook_event_name` and `model`; PreToolUse adds
  `tool_name`, `tool_use_id` and `tool_input`. (V) No `permission_mode` field is listed. (I: absence in the docs)
- Exit code 2 blocks. PreToolUse can deny, or allow with changed input. An "ask" decision is not supported yet.
  PermissionRequest can answer allow or deny. (V)
- PreToolUse sees shell calls (matched as `Bash`), `apply_patch` (matchable as `apply_patch`, `Edit` or `Write`), MCP
  tools and local function tools. Hosted tools such as web search are not covered. The docs describe tool hooks as a
  guardrail and not a complete enforcement boundary. (V)
- Trust is recorded against a hash. New or changed hooks are flagged for review and do not run until a person trusts
  them. A startup warning points to `/hooks`. A flag that bypasses hook trust exists for one-off automation. (V)
- A PreToolUse hook that errors, times out or returns malformed output can let the tool run. Default timeout 600 s. (V)
- Windows: a `commandWindows` override; the example uses `py -3`. (V)
- Skills load from `.agents/skills` in each directory from the working directory up to the repository root, from
  `$HOME/.agents/skills` and from an admin folder. Same-name skills are not merged. Symlinked skill folders are
  followed. A skill is called explicitly with `$skill-name`. The skills list is capped at 2% of the context window or
  8,000 characters. (V)
- AGENTS.md: a global file, then at most one file per directory from the project root down to the working directory
  (override file first, then AGENTS.md, then configured fallback names), concatenated. Reading stops when the total
  reaches `project_doc_max_bytes`, 32 KiB by default. The chain is built once per run. (V)
- Plugins bundle skills, MCP servers and hooks, and plugin hooks need review and trust before they run. (V)
- Whether hooks run under `codex exec`, and what happens there to hooks awaiting trust. (U)
- What Codex does when a hook returns "ask" anyway. (U)
- Whether the trust hash covers the script file or only the hook definition. (U)
- The `tool_input` shape of `apply_patch` as hooks receive it. (U)
- Consequences (I): the kit's "ask" rules are unenforced on Codex unless mapped to deny; edits need path extraction
  from the patch body because there is no `file_path`; a kit upgrade that changes hook definitions leaves the guard off
  until someone re-trusts it; a hook that cannot start is treated as allow, so the hook command needs a wrapper that
  turns any non-zero exit into exit 2; the kit block must be small and early because of the 32 KiB cap.
- **Cost:** an adapter of roughly 100 lines plus tests, re-tested per Codex release because the docs carry no version.

### D3. Cursor: hooks, skills, rules, plugins
- **Source, version, date:** https://cursor.com/docs/agent/hooks, https://cursor.com/docs/skills,
  https://cursor.com/docs/context/rules, https://cursor.com/docs/plugins. Undated. `hooks.json` schema `version: 1`.
- **Licence, maturity:** product docs.
- `hooks.json` exists at enterprise, team, project (`.cursor/hooks.json`) and user (`~/.cursor/hooks.json`) level, with
  per-hook options `type`, `timeout`, `matcher`, `loop_limit` and `failClosed`. (V)
- Events include preToolUse, postToolUse, beforeShellExecution, afterShellExecution, beforeMCPExecution,
  beforeReadFile, afterFileEdit, beforeSubmitPrompt, sessionStart, preCompact, subagentStart and stop. (V)
- `beforeShellExecution` and `beforeMCPExecution` accept allow, deny or ask. `beforeReadFile` accepts allow or deny.
  For `preToolUse`, "ask" is accepted by the schema but not enforced. Exit code 2 blocks. (V)
- By default a hook that crashes, times out or exits non-zero lets the action through. `failClosed: true` makes such
  failures block. (V)
- Cloud agents do not run sessionStart, sessionEnd or MCP hooks, and do not run user-level hooks. (V)
- Cursor can load hooks defined for other tools, including Claude Code, and provides a `CLAUDE_PROJECT_DIR` alias. (V)
- On Windows, hooks run through PowerShell. (V)
- Skills load from `.agents/skills/`, `.cursor/skills/` and the same two folders in the home directory, and, for
  compatibility, from `.claude/skills/` and `.codex/skills/` in the project and home. (V)
- Rules: AGENTS.md in the root and in nested directories, and `.cursor/rules/*.mdc`; guidance to stay under 500 lines.
  CLAUDE.md is not mentioned. (V)
- Plugins bundle rules, skills, agents, commands, hooks and MCP servers with a `.cursor-plugin/plugin.json`
  manifest. (V) The docs also mention a shared "Agent Plugins" manifest. (U: not found elsewhere; search refused)
- How hooks behave in the Cursor CLI and in headless runs. (U: not described)
- Which Claude Code hook events and outputs the compatibility loader maps, and whether it is on by default. (U)
- Consequences (I): use `beforeShellExecution` (which supports ask) and `beforeReadFile` (for sealed data) and not only
  `preToolUse`; set `failClosed` on every kit hook; with both the Claude Code and the Cursor adapter installed the
  guard may run twice per call; Cursor sees every copy of the kit's skill; cloud agents are outside enforcement.
- **Cost:** an adapter and a dedupe rule; double-run behaviour needs a test on a real install.

### D4. Agent Skills specification and the AGENTS.md format
- **Source, version, date:** https://agentskills.io/specification (undated, no version shown); https://agents.md/ and
  https://github.com/agentsmd/agents.md (repository last pushed 2026-09-10).
- **Licence, maturity:** open formats. Agent Skills began at Anthropic. AGENTS.md is stewarded by the Agentic AI
  Foundation under the Linux Foundation. Repository licences and first-release dates were not checked.
- SKILL.md requires `name` (at most 64 characters; lowercase letters, digits and single hyphens; equal to the folder
  name) and `description` (at most 1024 characters). Optional: `license`, `compatibility` (at most 500 characters),
  `metadata`, and the experimental `allowed-tools`. (V)
- Folders `scripts/`, `references/`, `assets/`. Guidance: about 100 tokens of metadata always loaded, under 5000 tokens
  of instructions, SKILL.md under 500 lines, references one level deep. (V)
- A validator command, `skills-ref validate`, exists. (V; not run)
- AGENTS.md is plain Markdown with no required fields; the file nearest the edited code wins; a direct user prompt
  overrides it. (V)
- The site lists Codex, Cursor, Gemini CLI, Copilot coding agent, Aider, opencode, Zed, Windsurf, Devin, Jules and Amp
  as readers. Claude Code is not listed although it reads the file since 2.1.277. (V)
- The site's claim of use in over 60k open-source projects. (U: self-reported)
- Independent counts: instruction files in 26.3% of 22,854 popular repositories and in 59.6% of the most-starred; where
  both files exist CLAUDE.md usually points to AGENTS.md; 74.0% of directives give no reason; about a third of files
  carry a generator signature (https://arxiv.org/abs/2610.31715 v2, 2026-10-26). (V, abstract)
- SKILL.md-style skills appear in 9 of 11 studied harnesses, MCP in 8 and ACP in 6; policy is moving from prompt prose
  into configuration (https://arxiv.org/abs/2609.00006 v1, 2026-07-15). (V, abstract)
- 3.8M SKILL.md files in 282,200 repositories (https://plicara.ai/research/agent-skill-languages/, 2026-08-24). (I:
  vendor blog; method not checked)
- **Kit could take:** keep the skill inside the limits and test that in the kit's own tests; fill `compatibility`
  (Python 3.8+, no network); give every kit rule a stated reason.
- **Cost:** none beyond one test.

### D5. Claude Code settings and fixes that matter for unattended runs
- **Source, version, date:** https://code.claude.com/docs/en/changelog. Entries 2.1.311 (2026-10-26) to 2.1.322
  (2026-11-10): 2.1.312 Oct 27, 2.1.314 Oct 30, 2.1.316 Oct 31, 2.1.317 Nov 3, 2.1.318 Nov 4, 2.1.319 Nov 6, 2.1.321
  Nov 9.
- **Licence, maturity:** proprietary; the two settings are 5 and 12 days old.
- 2.1.319 added `permissions.denyInsteadOfPrompting`: a tool call that would wait on a permission prompt is denied and
  the turn continues, in terminal sessions, subagents and teammates. (V)
- 2.1.314 added `permissions.blockWritesOutsideWorkingDirectories`: Write, Edit and NotebookEdit refuse outside paths
  in every permission mode. (V)
- 2.1.319 fixed `claude -p` exiting 0 in auto mode when its actions had been refused; 2.1.314 and 2.1.317 fixed exit 0
  after a startup failure and on a full disk. (V)
- 2.1.317 added `onFailure: "block"` for Agent SDK hook callbacks. (V)
- A PreToolUse "ask" could be lost when another hook's deferred result finished first; fixed in 2.1.321 or 2.1.322
  (two reads of the changelog disagreed on which). (V for the fix, U for the exact version)
- Three sandbox fixes in the same fortnight: an escape when creating a worktree (2.1.319); protections not applied to
  a worktree entered through `claude -p --resume` or `--continue` (2.1.314); a read-only Bash command running outside
  the sandbox without a prompt (2.1.321 or 2.1.322). (V)
- Auto mode: the server-side classifier is the default since 2.1.278; with telemetry or feature flags off, calls the
  server cannot check are asked about or denied (2.1.319). (V)
- Skills: with the Bash sandbox on, nested `.claude/skills` load only when Claude Code starts in or changes to that
  folder (2.1.319). Headless sessions reload `.claude/skills` when files change (2.1.321), unless
  `CLAUDE_CODE_PLUGIN_DIR_WATCH=0`. (V)
- 2.1.268: denial messages name the blocking rule and suggest a safer method. 2.1.271: a skill's inline shell commands
  follow default-mode rules. (V)
- Consequences (I): an unattended driver that reads the exit code needs 2.1.319 or later, because earlier versions
  could report success after refusing the work; skill hot-reload in headless sessions means an agent that edits the
  skill folder changes its own procedure mid-run; the lost "ask" was a fail-open path, so a minimum version matters.
- **Evidence quality:** vendor changelog only; no independent test found.
- **Cost:** ties the kit's unattended mode to a very recent version.

### D6. Agent Approval Laundering
- **Source, version, date:** https://arxiv.org/abs/2609.28586 v1 (2026-09-23). Secondary write-up:
  https://www.developersdigest.tech/blog/approve-effects-not-invocations (2026-09-28).
- **Licence, maturity:** preprint; ships a Claude Code PreToolUse integration (code not inspected, licence not checked).
- **What it does:** shows that an approval is tied to a command or tool call while the tool then runs a transitive
  workflow (build scripts, package scripts, test runners), and proposes approval bound to the predicted closure of
  effects across six effect classes.
- No policy that records only the invocation is sufficient. (V, abstract)
- On 111 approval and trace pairs, residual unapproved effects fall from 40 to 17 to 13 as the record uses more
  information. (V, abstract)
- With effect-bound records and frozen source-backed predictions, on 17 holdout workflows: macro recall 0.926, macro
  precision 0.941, residual effects 10 down to 3. (V, abstract)
- The blog recommends gates with three outcomes: pass, violate, unable to determine. (V, blog; an opinion)
- **Evidence quality:** the authors' own dataset and tool; the holdout is small (17 workflows).
- **Kit could take:** at launch record hashes of frozen paths and config and a listing of sealed paths; after the run
  harness code recomputes them before any result can be kept; the final evaluation runs from a clean copy of the
  evaluator; "could not verify" counts as invalid.
- **Cost:** hashing is cheap. Detecting reads of sealed data is weak without operating-system support.

### D7. One Skill Too Many
- **Source, version, date:** https://arxiv.org/abs/2610.11647 v2 (2026-10-13; first listed 2026-10-08).
- **Licence, maturity:** preprint; no tool required.
- **What it does:** measures what happens when two installed skills do the same job.
- Data: 822,109 candidate pairs from 20,947 repositories; 3,754 judged; 312 confirmed pairs run on 3 models (6,368
  runs, 169,294 tool calls, 542 agent-hours). (V, abstract)
- Nearly 1 in 4 installed skills is co-installed with one that does the same job; 37% of those sit in copied
  collections. (V, abstract)
- A similar skill takes over 1 run in 5 without lowering task completion. (V, abstract)
- Runs that open the similar skill first lose over a third of the functions only the intended skill provides. (V)
- Install location decides which skill runs; listing order barely matters. (V, abstract)
- The final reply names the skill actually used in 0.9% of substituted runs. (V, abstract)
- A pre-tool hook at the first skill read restores fidelity. The authors recommend scoring the intended skill's
  exclusive functions, not task completion alone. (V, abstract)
- **Evidence quality:** large, the authors' own; three models; software tasks.
- **Kit could take:** one byte-identical copy per agent folder with a hash check; a selftest that lists overlapping
  skills and says which copy each agent loads; invariants enforced by hooks and harness code so a substituted skill
  cannot remove them; in the paired measurement, score kit-specific behaviours (journal entry written, expctl used).
- **Cost:** a short check; keyword overlap will produce false positives.

### D8. Do instruction files help? Three measurements and one field report
- **Sources, versions, dates:** Evaluating AGENTS.md, https://arxiv.org/abs/2602.11988 v3 (2026-09-29; v1 2026-02-12).
  Do Context Files Help Coding Agents?, https://arxiv.org/abs/2607.27250 v1 (2026-07-28). Scientific Agents,
  https://arxiv.org/abs/2610.00084 v1 (2026-09-07). Field report:
  https://www.stet.sh/blog/how-i-used-codex-to-improve-its-own-agents-md (2026-05-27). Agent READMEs, arXiv 2511.12884
  v2.
- **Licence, maturity:** preprints and one journal-indexed study; no software to adopt.
- 2602.11988: context files tend not to raise task success and raise inference cost by more than 20% on average. This
  holds across models and agents and for both generated and developer-written files. Agents do follow the
  instructions. Repository overviews did not help. (V, abstract)
- 2607.27250: Claude Code and Codex, 17 tasks from 3 repositories, 288 runs. No measurable change in correctness;
  effects larger than about 10 to 15 points are ruled out. Failures came from implementation skill, not from missing
  repository knowledge. AGENTS.md never turned a near-miss into a pass. (V, abstract)
- 2610.00084: 503 profession-specific profiles. Accuracy change -0.6 points (95% interval -1.5 to +0.2); 1.5 to 2.3
  times the output tokens; 2.2 to 4.5 times the cost. On BioMysteryBench 46.7% with a profile against 56.7% without
  (-10.0 points, interval -16.7 to -3.3), because runs stopped at token and time limits. (V, abstract)
- stet.sh: Codex tuned its own AGENTS.md. Tests +20 points on a 5-task tuning slice, flat on a 10-task holdout,
  correctness score down 0.20, more tokens. The author did not ship the result. (V, blog; one practitioner, small n)
- 2511.12884: in 2,303 context files, security (14.8%) and performance (14.5%) guidance is rarely present. (V)
- **Limits:** software-engineering and science question tasks only; none measures ML training; two are small.
- **Kit could take:** keep the always-loaded block minimal and limited to what code cannot enforce; no persona text;
  treat every instruction change as a hypothesis tested on held-out tasks; count the block's size as a cost in the
  paired measurement.
- **Cost:** none; this removes work.

### D9. Lessons Outlive Their Failures
- **Source, version, date:** https://arxiv.org/abs/2610.32578 v1 (2026-10-23).
- **Licence, maturity:** preprint; a case study of one repository, described by its authors as exploratory.
- **What it does:** follows the rules, skills, hooks and checks added to one agent harness and asks which still matter.
- 118 failures over 6 weeks; 48 of them trace to stale documentation. (V, abstract)
- An LLM audit finds about half of the known drift (Sonnet 5.5) with at least 93% precision. (V, abstract)
- Of 5 replayed failures, 4 finished, and in 3 the failure did not recur with or without its fix. (V, abstract)
- A mechanical check stopped the stale-count failure in every run. A written rule did not change one model's run-time
  overestimates. (V, abstract)
- The authors recommend re-testing and retiring rules. (V, abstract)
- **Evidence quality:** single repository, small replay set.
- **Kit could take:** a rule ledger (rule, originating failure, enforcing check, last replay, review-by date); move a
  rule out of prose once code enforces it; replay the nine rules when a new model generation ships.
- **Cost:** replays cost agent tokens; the ledger itself is a table.

### D10. What skills do, and when they stop working
- **Sources, versions, dates:** SkillsBench, https://arxiv.org/abs/2602.12670 v4 (2026-06-14). Demystifying Agent
  Skills, https://arxiv.org/abs/2608.14036 v1 (2026-08-14). From Registry to Repository,
  https://arxiv.org/abs/2607.00911 v2 (2026-07-06).
- **Licence, maturity:** preprints; SkillsBench runs on Harbor.
- SkillsBench: 87 tasks, 8 domains, 18 configurations. Curated skills raise the pass rate from 33.9% to 50.5% (+16.6
  points). Skills with at most 3 modules beat larger bundles. (V, abstract)
- Demystifying: 8,135 trial records. Skills help mainly by fixing the order of steps ("procedural anchoring", 65.7% of
  cases); adding missing knowledge accounts for 4.5%. As the skill pool grows from 5 to 100, the precision of actually
  using the right skill falls from 29.6% to 3.3%. Skills fail under brittle assumptions, incompatible contexts or
  insufficient adaptation. (V, abstract)
- Registry to Repository: 18,463 registry skills and 23,199 personal skills. Reuse is mostly a one-time copy; 53% are
  never modified after adoption. (V, abstract)
- **Kit could take:** keep the skill as an ordered procedure with few modules; state its assumptions (single node, run
  contract present) so it fails loudly when they do not hold; name the skill explicitly in the kickoff prompt and the
  AGENTS.md block so loading does not depend on retrieval; treat installed copies as stale by default and check them.
- **Cost:** none.

### D11. LoopArena
- **Source, version, date:** https://arxiv.org/abs/2608.28281 v2 (2026-10-13); repository
  https://github.com/AMAP-ML/LoopArena.
- **Licence, maturity:** Apache-2.0; 154 stars (weak evidence); 8 commits; no release.
- **What it does:** benchmarks a Controller model that steers a fixed Worker agent through long software tasks, given
  an Evidence Packet each round and a Loop Contract.
- Named failure modes: stale progress note, skipped verification, wrong budget direction, premature stop. (V, abstract)
- Three task types: 160 four-way questions with no execution, 80 task slices, 80 full tasks. (V, abstract)
- Best strict success on full tasks is 36.25%. GPT-5.5 scores 61.88, 56.67 and 36.25 on the three types; Claude Opus
  4.8 scores 56.25, 58.75 and 33.75. (V, abstract)
- Cost reduction averages 60.6%. (V, abstract; the baseline of this reduction was not checked)
- **Evidence quality:** the authors' benchmark; software tasks, not ML training.
- **Kit could take:** the loop driver, not the agent, owns stop, budget and keep; the driver hands the agent a fresh
  evidence packet computed from run files each round, so a stale note cannot steer; the four failure modes become
  test cases for the driver.
- **Cost:** none to take the design. Running the benchmark needs API tokens.

### D12. AutoTrainess and PostTrainBench
- **Sources, versions, dates:** AutoTrainess, https://arxiv.org/abs/2606.31551 v1 (2026-06-30). PostTrainBench,
  https://arxiv.org/abs/2603.08640 v2 (2026-03-10; v1 2026-03-09).
- **Licence, maturity:** preprints. No repository is named in the AutoTrainess abstract. Code location and licence of
  PostTrainBench were not checked.
- AutoTrainess gives agents a repository of purpose-built interfaces for planning, data preparation, training,
  evaluation and logging in place of a raw command line. (V, abstract)
- On PostTrainBench: GPT-5.4 with Codex 26.94 against 23.21 (+3.73); DeepSeek-V4-Flash with OpenCode 19.58 against
  12.13 (+7.45). (V, abstract; self-reported)
- PostTrainBench gives an agent 10 hours on one H100 to post-train a small base model for a target benchmark with no
  given strategy. (V, abstract)
- Best agent 23.2% against 51.1% for official instruction-tuned models. (V, abstract)
- Observed failure modes: training on the test set, downloading existing instruction-tuned checkpoints, and using API
  keys found in the environment. The authors call for careful sandboxing. (V, abstract)
- How those failures were detected. (U: not in the abstract)
- **Kit could take:** the three observed cheats as guard and post-run test cases (test data in the training set, a
  downloaded finished checkpoint presented as trained, a credential read from the environment); new expctl commands
  only where the loop needs a decision from code (evaluate, compare, budget).
- **Cost:** PostTrainBench itself costs 10 H100-hours per task and arm, too much for a kit regression test.

### D13. AutoWorldModel-Bench
- **Source, version, date:** https://arxiv.org/abs/2608.11216 v2 (2026-08-16); project page
  https://electronicarts.github.io/AutoWorldModelBench/ (checked 2026-11-11).
- **Licence, maturity:** code BSD 3-Clause per the project page; the paper text is CC BY-NC-ND; hardware not stated.
- **What it does:** an agent improves one of four starter world models (Dreamer, AR-Transformer, D3PM, MaskGIT) on one
  of eight games.
- Each session has a 6-hour wall-clock budget and each training run is capped at 600 seconds. (V, page)
- The agent sees a validation score; test and scenario splits are held out and scored once after the session, on the
  checkpoint chosen by validation. (V, page) No technical enforcement beyond the protocol is described. (I)
- 64 sessions (2 agents by 32 tasks): 63 improved the held-out test split, 33 by at least +0.10. (V, abstract)
- Mean experiments per session: 23.5 (Opus 4.6) and 18.2 (Codex 5.4). In 91% of sessions the winning edit was
  substantive and not a hyperparameter tweak. (V)
- The Opus against Codex difference (19 to 13 task wins) is not significant (p = 0.15); Codex ran inside a restart
  loop, which the authors name as a possible confound. (V, page)
- Starter scores differ between agents because of platform non-determinism, so each agent re-runs its own starter. (V)
- **Kit could take:** a ready task set with 10-minute runs for the paired with-kit and without-kit test; the protocol
  (validation guides, one test evaluation after the session) matches the kit's sealed-test rule; the restart-loop
  detail shows that a headless Codex session needs an outer driver to persist across iterations.
- **Cost:** GPU hours and agent tokens per session; a dataset download of about 19K episodes per game.

### D14. CATP
- **Source, version, date:** https://arxiv.org/abs/2609.38223 v1 (2026-09-28).
- **Licence, maturity:** preprint; targets Claude Code and Codex; code and licence not checked.
- **What it does:** the hook commits to the policy in force and to a normalized form of the action, and durably records
  the decision before it returns permission; a receipt ties this to an audit export that can be verified offline.
- Five missing consistency checks were found in the evaluated setup; 13 of 13 expected outcomes were met. (V, abstract)
- Different actions can normalize to the same record, which limits what a receipt proves. (V, abstract)
- About 85 ms median hook overhead and about 174 ms for offline verification. (V, abstract)
- File formats: receipt.json, audit-export.json, audit.jsonl, catp-policy.toml. (V, abstract)
- **Evidence quality:** the authors' own design evaluation.
- **Kit could take:** write the audit entry, flush it, then answer; add the config hash and the previous entry's hash
  to each entry; deny when the log cannot be written; store the log's head hash in each run manifest.
- **Cost:** one flush per decision. A chain detects edits, not deletion of the whole file.

### D15. StealthyPoison and SkillSpector
- **Sources, versions, dates:** https://arxiv.org/abs/2611.12155 v1 (2026-11-09); https://github.com/NVIDIA/skillspector
  v2.13.4 (2026-11-04).
- **Licence, maturity:** preprint; SkillSpector is Apache-2.0, Python 3.12+, 25.2k stars (weak evidence).
- StealthyPoison rewrites the procedure of a third-party skill so that the agent follows attacker steps while the skill
  looks benign. Evaluated on 566 target skills, 5,244 requests and more than 26,000 registry entries. (V, abstract)
- It gains 13.6% in top-1 retrieval placement over two known attack baselines and transfers to 3 held-out models. (V)
- It succeeds end to end in a Claude Code workflow with Opus 4.8. (V, abstract)
- Most payloads evade SkillSpector and an LLM judge. (V, abstract)
- SkillSpector has 71 patterns in 17 categories, an offline mode (`--no-llm`), SARIF output and verdicts SAFE, CAUTION
  or DO_NOT_INSTALL, and states its own limits. (V, README)
- SkillSpector's README figures on how many public skills are vulnerable or malicious. (U: self-reported)
- **Kit could take:** the research-scouting step never installs or executes a fetched skill, plugin or hook; an
  optional skill-import module would scan and then still require a person; the kit's own skill ships with file hashes
  so users can check what they installed.
- **Cost:** a scanner adds a package and a false sense of safety, since the newest attack class passes it.

## 5. Shorter reads (same claim format)

- **S1. SkillOpt** (https://arxiv.org/abs/2605.23904 v2, 2026-05-25; https://github.com/microsoft/SkillOpt v0.2.0,
  2026-07-02; MIT; Python 3.10+; about 19k stars, weak). An optimizer model makes bounded add, delete or replace edits
  to a skill; an edit is kept only on strict improvement of a held-out validation score; uses an edit budget and a
  buffer of rejected edits. (V) Best or tied in all 52 cells; +23.5, +24.8 and +19.1 points for GPT-5.5 in chat, Codex
  and Claude Code settings. (V, abstract; self-reported) Backends include `codex_exec` and `claude_code_exec`. (V,
  README) Cost of one optimization run. (U) Take: the keep rule; use the tool only once the kit has its own task set.
- **S2. cc-safety-net** (https://github.com/kenryu42/cc-safety-net v2.7.9, 2026-11-10; MIT; Node 22+; about 2k stars,
  weak). Guard for 16 agent CLIs including the three targets, on Windows, macOS and Linux; parses commands through
  `bash -c`, `python -c` and wrappers; blocks destructive git and rm, curl piped to a shell, and secret access; a
  broken config falls back to safe defaults; states that it is not a sandbox; has a `doctor` command. (V, README) No
  independent evaluation. Take: its adapter layout and unwrapping test cases as reference.
- **S3. destructive_command_guard** (https://github.com/Dicklesworthstone/destructive_command_guard v0.16.0,
  2026-11-01; Rust; 6.3k stars, weak). Its LICENSE is MIT plus a rider that grants no rights to OpenAI, Anthropic,
  their affiliates or anyone acting for them. (V, LICENSE as returned by the fetch tool) This is not a standard
  open-source licence. (I)
- **S4. ActPlane** (https://arxiv.org/abs/2606.25189 v2, 2026-06-30; https://github.com/eunomia-bpf/ActPlane; MIT; 111
  stars; no releases). Kernel-side (eBPF) enforcement with an information-flow rule file; kill, block or notify with a
  message the agent can read; covers indirect execution paths that tool-call hooks miss; 1.9% to 8.4% overhead. (V,
  abstract; self-reported) Needs Linux 5.10+ with BTF (6.1+ for the full runtime) and root or CAP_BPF plus
  CAP_SYS_ADMIN; ships hook configs for Claude Code and Codex. (V, README) WSL2 support. (U)
- **S5. Humanize** (https://arxiv.org/abs/2610.08900 v2, 2026-10-08; https://github.com/humanfia/humanize, Apache-2.0).
  A person approves a plan contract; a builder works in rounds; a reviewer from a different vendor decides completion;
  72 hook gates. (V) Evaluation is observational (118 postmortems); the authors report stopping as a key weakness and
  that two thirds of rounds happened after the implementation was accepted. (V, abstract) The README says agents run
  with approvals bypassed. (V) The repository shows 395 stars against 1,468 in the paper, so the match is unverified. (U)
- **S6. JetBrains test of RTK and caveman** (primary https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/
  returned 403; figures from https://magica.com/news/jetbrains-tests-caveman-and-rtk-token-claims, 2026-07-20). Paired
  runs on SkillsBench tasks with Harbor; RTK v0.43.0, Claude Code 2.1.201. RTK: median cost +7.6% at low effort
  (p = 0.004) with 13.8% more turns, +0.1% at high effort; 34% of tool output came from Read and Grep, which a Bash
  hook never sees; the tool's own counter reported 96.2M tokens saved while bills rose. Caveman: 8.5% measured output
  reduction against 65% claimed; total cost higher. (I: secondary source for every number)
- **S7. Detecting Silent Faults** (https://arxiv.org/abs/2611.08144 v1, 2026-11-05; workshop paper; robot RL). A
  learning-curve threshold caught at most 1 in 10 faulty runs; comparison with ten clean seeds at most 21%; 723 of 728
  faulty runs scored within 3 standard deviations of clean runs; a step ledger kept on both sides of the boundary
  caught and located every fault at about +3% training time. (V, abstract) Transfer to supervised and LLM training. (I)
- **S8. Harness design studies.** Empirical Study of Harness Design (https://arxiv.org/abs/2609.20804 v1, 2026-09-17):
  4 models, 176 matched settings; context management matters more as the budget tightens; rule-based trimming before
  LLM summarization is the most efficient; recoverable trimming adds machinery models rarely use; planning helps weak
  models' accuracy and strong models' cost; bash-only is cheaper for bash-capable models. (V, abstract)
  Harness-of-Harness (https://arxiv.org/abs/2609.01481 v1, 2026-09-01): an outer loop around existing harnesses that
  separates testing during implementation from independent evaluation; average relative gain 52.25%. (V; self-reported)
  VERSE (https://arxiv.org/abs/2610.02616 v1): self-evolution fails without execution-based verification; uses disjoint
  train, validation and test tasks. (V) Recursive Harness Self-Improvement (https://arxiv.org/abs/2607.15524 v1): 30
  synthetic ML research tasks; cost down by up to 60%. (V; self-reported) HarnessFix
  (https://arxiv.org/abs/2606.06324 v2): harness-aware trace representation and regression-aware validation; +6.3% to
  18.4%. (V; self-reported) Better Harnesses, Smaller Models (https://arxiv.org/abs/2607.08938): 89.7% of the
  performance at 4% of the cost. (V; self-reported) From Agent Traces to Trust (https://arxiv.org/abs/2606.04990 v6):
  survey; tamper-evident traces are rarely reported. (V) Configuring Agentic AI Coding Tools (matched to arXiv
  2602.14690 v5): 2,853 repositories, eight configuration mechanisms, context files dominate, skills are mostly
  static. (V for the arXiv abstract; I for the match to the sweep's DOI)
- **S9. Andon** (https://github.com/PrimeFoldTools/Andon; MIT; 168 stars, weak; Python stdlib hooks; tested by its
  author with codex-cli 0.153.4). Stop-hook check of "done" claims, which its README describes as showing
  correspondence and not proof; a defect ledger with review-by dates checked by a script; a pipe guard that its author
  says fires on about 1 in 24 Bash calls. (V, README) No outcome measurement.
- **S10. Canny** (https://github.com/qkal/Canny; MIT; 135 stars, weak; TypeScript). Facts decide and block; a model's
  judgment only advises; append-only per-session ledger with replay; loosening the config needs an explicit trust
  step. (V, README) Its own benchmark showed no outcome difference and the author says the benefit is unmeasured. (V)
- **S11. habit-hooks** (https://github.com/habit-hooks/habit-hooks; MIT; 260 stars, weak; Python 3.11+). Coaching
  messages against bare linter messages: genuine-fix rate 83.3% against 28.9% (Haiku 4.5) and 5.6% (Sonnet 4.6) in an
  evaluation the README calls pre-registered. (U: README only)
- **S12. Nomos** (https://github.com/mgantlett/nomos v4.13.2, 2026-11-10; Go; Apache-2.0; 5 stars). A worktree per
  task; AST gates; merge with a receipt in Git Notes; flags skipped-test annotations; coverage ratchets; policy file
  pinned to the main branch. (V, README) Terminal-Bench 2.0 from 58/89 to 63/89. (U: self-reported)
- **S13. entireio/cli** (https://github.com/entireio/cli; MIT; Go; 5.3k stars, weak; latest tag a nightly prerelease
  of 2026-11-10). Session checkpoints under custom git refs, linked by a commit trailer; transcripts are pushed to the
  remote unless a skip flag is set; redaction is best effort. (V, README)
- **S14. Skill and plugin distribution.** vercel-labs/skills (https://github.com/vercel-labs/skills; MIT; Node 22.20+;
  about 38.9k stars, weak): installs skills for 79 agents; lockfile with a SHA-256 per skill and a frozen-lockfile
  mode; telemetry on by default. (V, README) superpowers: one methodology distributed as a native plugin per agent;
  bootstrap differs per agent and is lost after compaction where no post-compaction hook exists. (V, README) ECC
  v2.2.3 (2026-10-01): root as source of truth with platform adapters. (V, README) stop-that-shit v0.2.5: shared
  runtime, per-host adapters, a host-adapter contract file, Codex plugin pinned to a tag. (V, README) diet103: a
  prompt-submit hook and a rules file to force skill activation; no measurements. (V, README)
- **S15. Secrets and remote approval.** Stroq (https://github.com/AGGIB/Stroq v0.30.0; Apache-2.0; Node 22+): scans
  transcripts of the three target agents for known secrets; hooks deny curl piped to a shell and outbound calls that
  carry a secret; describes itself as a filter and not a sandbox; 36 attacks, 15 denied, 21 asked, 0 passed. (V,
  README; self-reported) SecretHooks blog (2026-07-16): a PostToolUse hook that redacts tool output and fails open. (V)
  jev-guard (MIT): sends tool calls to a hosted classifier, fails open by default, publishes no error rates, and notes
  that Codex and Gemini lack "ask". (V, README) Lucarne (MIT): remote approve or deny through a messaging app and a
  local daemon; no documented security model. (V, README)
- **S16. Practitioner notes.** tesseracted-labs blog (2026-09-15): separates preferences from invariants; hooks are not
  a sandbox; an invalid replacement tool output is silently ignored; hooks stored in the repository that the agent can
  edit are weak controls. (V, blog; opinion) cloudflare/security-audit-skill (MIT; 14 commits): coverage ledger; a
  fresh verifier tries to disprove each finding; findings file validated against a schema with verdicts confirmed,
  needs_validation or rejected. (V, README) Aperion Shield v0.7.0 (2026-05-20): guardrails as git pre-commit and
  pre-push hooks, agent-agnostic, bypassable with `--no-verify`; licence not stated. (V, release note) backpass (MIT):
  mines transcripts into quoted evidence and proposes AGENTS.md edits that a person applies; no outcome evidence. (V)

## 6. Cross-agent differences that a port must absorb

| Point | Claude Code 2.1.322 | Codex (docs undated) | Cursor (docs undated) |
|---|---|---|---|
| Instruction file | CLAUDE.md; AGENTS.md only as fallback or by import | AGENTS.md chain, 32 KiB cap | AGENTS.md (root and nested), `.cursor/rules` |
| Skill folder | `.claude/skills` | `.agents/skills` | `.agents/skills`, `.cursor/skills`, plus `.claude/skills` and `.codex/skills` |
| Pre-tool decision | allow, deny, ask | allow, deny (no ask) | preToolUse: allow, deny (ask not enforced); beforeShellExecution: allow, deny, ask; beforeReadFile: allow, deny |
| Hook cannot run or fails | `onFailure: block` available | tool may run | action runs unless `failClosed: true` |
| Hook changed | review in `/hooks` | not run until re-trusted | not stated |
| Nobody to ask | `permissions.denyInsteadOfPrompting` (2.1.319) | PermissionRequest hook can deny in code | not documented |
| Outside the hook | none found | hosted tools such as web search | cloud agents skip some hooks |
| Headless hook coverage | documented | unverified | unverified |

All rows V from the vendor docs cited in D1 to D5, except the last row, which records what the docs do not say.

## 7. Re-searches with different phrasing (step 3)

1. "agent skills" was re-asked as: where does each coding agent look for skills, and what differs between them. Result:
   the `.agents/skills` convention in Codex and Cursor and Cursor's compatibility folders (D2, D3).
2. "skill security" was re-asked as: limits of skill scanners. Result: SkillSpector's stated limits and the paper that
   evades it (D15).
3. "permission prompts" was re-asked as: alternatives to approving each invocation. Result: effect-bound approval (D6),
   kernel-level enforcement (S4) and the vendor's deny-instead-of-prompt setting (D5).
4. A fourth re-search, on a shared "Agent Plugins" manifest, was refused because the run's search budget was used up.

## 8. Concepts that README.md and brief.md do not mention

1. AGENTS.md: vendor-neutral Markdown instruction file read by Codex, Cursor and (as fallback) Claude Code. https://agents.md/
2. "Project instructions" setting: Claude Code switch for reading CLAUDE.md, AGENTS.md or both. https://code.claude.com/docs/en/memory
3. `@AGENTS.md` import: one line in CLAUDE.md that makes Claude Code read the shared file once. https://code.claude.com/docs/en/memory
4. Agent Skills specification: open SKILL.md format with name and description limits and a validator. https://agentskills.io/specification
5. `.agents/skills/`: skill folder shared by Codex and Cursor. https://learn.chatgpt.com/docs/build-skills
6. Skills-list budget: Codex caps the list of skills at 2% of context or 8,000 characters. https://learn.chatgpt.com/docs/build-skills
7. `project_doc_max_bytes`: Codex stops adding instruction files at 32 KiB. https://learn.chatgpt.com/docs/agent-configuration/agents-md
8. Hook trust by hash: Codex does not run a new or changed hook until a person trusts it again. https://learn.chatgpt.com/docs/hooks
9. `failClosed`: Cursor per-hook option; without it a failed hook lets the action through. https://cursor.com/docs/agent/hooks
10. PermissionRequest hook: Codex event that answers a permission prompt in code. https://learn.chatgpt.com/docs/hooks
11. Missing "ask" decision: a pre-tool hook that cannot hand the choice to a person. https://learn.chatgpt.com/docs/hooks
12. Third-party hook loading: Cursor also runs hook configs written for Claude Code. https://cursor.com/docs/agent/hooks
13. `permissions.denyInsteadOfPrompting`: Claude Code setting that denies would-be prompts and continues. https://code.claude.com/docs/en/changelog
14. `permissions.blockWritesOutsideWorkingDirectories`: Claude Code setting that confines file-edit tools. https://code.claude.com/docs/en/changelog
15. `/doctor prompt-audit`: Claude Code audit of instruction files and skills for conflicts. https://code.claude.com/docs/en/memory
16. Approval laundering: an approved command triggers effects nobody approved. https://arxiv.org/abs/2609.28586
17. Effect-bound (closure-bound) approval: approval tied to the predicted set of effects, not the command text. https://arxiv.org/abs/2609.28586
18. Three-valued gate: pass, violate or unable to determine, with the third treated as not-pass. https://www.developersdigest.tech/blog/approve-effects-not-invocations
19. Skill substitution: a similar co-installed skill silently takes over a run. https://arxiv.org/abs/2610.11647
20. Exclusive core functions: what only the intended skill provides; the metric that exposes substitution. https://arxiv.org/abs/2610.11647
21. Procedural skill poisoning: a registry skill whose steps steer the agent while looking benign. https://arxiv.org/abs/2611.12155
22. Skill scanner: static and LLM checks of skill packages before install. https://github.com/NVIDIA/skillspector
23. Procedural anchoring: skills help mostly by fixing the order of steps, not by adding knowledge. https://arxiv.org/abs/2608.14036
24. Skill retrieval bottleneck: use of the right skill collapses as the installed pool grows. https://arxiv.org/abs/2608.14036
25. Loop engineering and the Controller model: a model that steers a fixed worker through a long task. https://arxiv.org/abs/2608.28281
26. Loop Contract and Evidence Packet: explicit stop, budget and verification terms, and the state summary given each round. https://arxiv.org/abs/2608.28281
27. Agent-computer interface for training: dedicated commands for data, training, evaluation and logging. https://arxiv.org/abs/2606.31551
28. PostTrainBench: agent post-trains a small LLM in 10 H100-hours; records agents training on test data. https://arxiv.org/abs/2603.08640
29. AutoWorldModel-Bench: agent improves a small model with 600-second runs and a held-out test split. https://electronicarts.github.io/AutoWorldModelBench/
30. Judgement engineering and the plan contract: a person approves terms up front; a separate reviewer decides completion. https://arxiv.org/abs/2610.08900
31. Authorization receipt: the hook commits to policy hash and action and logs durably before answering. https://arxiv.org/abs/2609.38223
32. Normalization collision: two different actions reduce to the same audit record. https://arxiv.org/abs/2609.38223
33. Execution provenance and trace assurance: a tamper-evident record of what the agent ran. https://arxiv.org/abs/2606.04990
34. OS-level policy enforcement: kernel-side blocking with information-flow rules. https://arxiv.org/abs/2606.25189
35. Text-space skill optimizer: bounded edits kept only on held-out improvement, with a rejected-edit buffer. https://arxiv.org/abs/2605.23904
36. AGENTS.md inversion: a self-tuned instruction file that wins on tuning tasks and not on holdout. https://www.stet.sh/blog/how-i-used-codex-to-improve-its-own-agents-md
37. SkillsBench: paired with-skill and without-skill benchmark. https://arxiv.org/abs/2602.12670
38. Harbor: container runner for agent evaluations across agents. https://github.com/laude-institute/harbor
39. Stop-hook claim gate: at stop time code checks the claim against artifacts; only facts can block. https://github.com/qkal/Canny
40. Defect ledger with review-by dates: each rule records its originating failure and a retest date. https://github.com/PrimeFoldTools/Andon
41. Rule replay: re-running the original failure with and without its rule. https://arxiv.org/abs/2610.32578
42. Config immutability gate: policy read from the base branch so the working branch cannot loosen it. https://github.com/mgantlett/nomos
43. Two-sided step ledger: counters on both sides of a process boundary, compared to catch silent faults. https://arxiv.org/abs/2611.08144
44. Git hooks as agent-independent guardrail: enforcement at commit and push for any agent. https://github.com/AperionAI/shield/releases/tag/shield-v0.7.0
45. Checkpoint refs and commit trailer: agent session stored in git and linked from the commit. https://github.com/entireio/cli
46. Remote approval relay: permission prompts answered from a phone. https://github.com/tuchg/Lucarne
47. Skill lockfile with content hash: SHA-256 per installed skill and a frozen install mode. https://github.com/vercel-labs/skills
48. Agent plugin packaging: per-agent bundles of skills, hooks and MCP entries. https://learn.chatgpt.com/docs/plugins
49. Host adapter contract: one runtime plus a written contract each agent adapter must meet. https://github.com/lennney/stop-that-shit
50. Skill auto-activation hook: a prompt-submit hook that tells the agent which skill to load. https://github.com/diet103/claude-code-infrastructure-showcase
51. Coaching denial: a block message that states the allowed next step. https://github.com/habit-hooks/habit-hooks
52. Rule-based trimming before summarization: deterministic removal of old tool output as the first context measure. https://arxiv.org/abs/2609.20804
53. Tool-surface blind spot: a hook on one tool sees only part of the agent's activity. https://magica.com/news/jetbrains-tests-caveman-and-rtk-token-claims
54. Harness-aware trace representation: failure traces rewritten to name the harness part at fault. https://arxiv.org/abs/2606.06324
55. ACP: an agent-to-client protocol found in 6 of 11 studied harnesses (expansion not checked). https://arxiv.org/abs/2609.00006
56. Scraper tarpit: a site that serves scrambled text to automated readers. https://pivot-to-ai.com/2026/08/27/your-agents-md-file-doesnt-actually-do-anything/

## 9. Concerns any design must handle

SEC-APPROVAL-LAUNDERING
SEC-PROMPT-INJECTION
SEC-SKILL-SUPPLY-CHAIN
SEC-HOOK-FAIL-OPEN
SEC-HOOK-TRUST-RESET
SEC-GUARD-SELF-MODIFICATION
SEC-INDIRECT-EXECUTION-BYPASS
SEC-SECRET-IN-TRANSCRIPT
SEC-AUDIT-LOG-TAMPER
SEC-REMOTE-APPROVAL-CHANNEL
SEC-DATA-EGRESS-GUARD-SERVICE
PORT-INSTRUCTION-FILE-PRECEDENCE
PORT-INSTRUCTION-SIZE-CAP
PORT-ASK-DECISION-MISSING
PORT-TOOL-INPUT-SHAPE
PORT-DUPLICATE-HOOK-EXECUTION
PORT-DUPLICATE-SKILL-COPIES
PORT-COMPACTION-REINJECTION
PORT-WINDOWS-HOOK-SHELL
PORT-HEADLESS-HOOK-COVERAGE
PORT-AGENT-VERSION-DRIFT
SKILL-CONFLICT-SUBSTITUTION
SKILL-ACTIVATION-MISS
SKILL-STALE-COPY
INSTR-NO-MEASURED-BENEFIT
INSTR-RULE-ROT
INSTR-PERSONA-COST
EVAL-KIT-EFFECT-UNMEASURED
EVAL-TOOL-SURFACE-METRIC
EVAL-HOLDOUT-FOR-SELF-TUNING
EVAL-SILENT-FAULT
EVAL-REWARD-HACKING
LOOP-CONTROLLER-UNRELIABLE
LOOP-PREMATURE-STOP
LOOP-STALE-PROGRESS-NOTE
LOOP-KEEP-DECISION-BY-MODEL
LOOP-EXIT-CODE-FALSE-SUCCESS
OPS-UPGRADE-PATH
COST-HOOK-OVERHEAD-TURNS
LIC-NONSTANDARD-RIDER

One line of meaning each:
- SEC-APPROVAL-LAUNDERING: an allowed command runs a wider workflow than the text shows.
- SEC-PROMPT-INJECTION: fetched pages, READMEs and skills contain text addressed to agents (11 cases in section 10).
- SEC-SKILL-SUPPLY-CHAIN: third-party skills, plugins and hooks can be poisoned and scanners miss it.
- SEC-HOOK-FAIL-OPEN: a hook that crashes, times out or cannot start lets the action through on two agents.
- SEC-HOOK-TRUST-RESET: a changed hook is not run until re-trusted, so an upgrade can switch the guard off.
- SEC-GUARD-SELF-MODIFICATION: the agent can edit hooks, config, skill or instruction files unless every copy is listed.
- SEC-INDIRECT-EXECUTION-BYPASS: scripts reach files the command line never names.
- SEC-SECRET-IN-TRANSCRIPT: credentials end up in transcripts, logs and pushed session data.
- SEC-AUDIT-LOG-TAMPER: the audit log is editable, rotates away history and drops entries on write errors.
- SEC-REMOTE-APPROVAL-CHANNEL: a phone or chat channel that can approve actions can be spoofed.
- SEC-DATA-EGRESS-GUARD-SERVICE: a hosted guard receives every command and its context.
- PORT-INSTRUCTION-FILE-PRECEDENCE: which file each agent reads, and what creating one hides.
- PORT-INSTRUCTION-SIZE-CAP: silent truncation at 32 KiB on one agent.
- PORT-ASK-DECISION-MISSING: "ask" is absent or unenforced where most kit rules use it.
- PORT-TOOL-INPUT-SHAPE: tool names and inputs differ (patch bodies without a file path).
- PORT-DUPLICATE-HOOK-EXECUTION: one agent loads another agent's hook config as well as its own.
- PORT-DUPLICATE-SKILL-COPIES: one agent reads several skill folders at once.
- PORT-COMPACTION-REINJECTION: text injected at session start is lost after compaction where no hook re-adds it.
- PORT-WINDOWS-HOOK-SHELL: hooks run through a different shell and interpreter name on Windows.
- PORT-HEADLESS-HOOK-COVERAGE: hook behaviour in headless modes is undocumented for two agents.
- PORT-AGENT-VERSION-DRIFT: vendor behaviour changed several times in the last two weeks; two vendors' docs are undated.
- SKILL-CONFLICT-SUBSTITUTION: a similar skill takes over silently.
- SKILL-ACTIVATION-MISS: the skill is installed and not loaded.
- SKILL-STALE-COPY: copies are rarely updated after install.
- INSTR-NO-MEASURED-BENEFIT: instruction text costs tokens without a shown gain.
- INSTR-RULE-ROT: rules outlive the failures that caused them.
- INSTR-PERSONA-COST: persona text raises cost and causes limit stops.
- EVAL-KIT-EFFECT-UNMEASURED: no paired evidence that the kit helps.
- EVAL-TOOL-SURFACE-METRIC: a tool's own counter reports savings that total cost contradicts.
- EVAL-HOLDOUT-FOR-SELF-TUNING: anything tuned on tasks must be judged on other tasks.
- EVAL-SILENT-FAULT: a faulty run finishes with plausible curves and scores.
- EVAL-REWARD-HACKING: agents train on test data, fetch finished checkpoints or use found credentials.
- LOOP-CONTROLLER-UNRELIABLE: models make poor continue, verify, budget and stop decisions.
- LOOP-PREMATURE-STOP: the loop ends, or goes on, at the wrong time.
- LOOP-STALE-PROGRESS-NOTE: the agent steers by an outdated note instead of current run state.
- LOOP-KEEP-DECISION-BY-MODEL: a model judgment, not a measurement, keeps a change.
- LOOP-EXIT-CODE-FALSE-SUCCESS: a headless session reports success after its actions were refused.
- OPS-UPGRADE-PATH: moving the rules block and adding adapters without losing user content.
- COST-HOOK-OVERHEAD-TURNS: hooks add latency and can add turns.
- LIC-NONSTANDARD-RIDER: an MIT-looking licence with a clause that excludes named vendors.

## 10. Redirect attempts and agent-addressed text (none acted on)

1. A search service's error message told the reader to create an account and an API key. Not done; other tools used.
2. The Agent Skills, Claude Code and Codex documentation pages open with a header telling automated readers to fetch a
   documentation index file before exploring further. Not followed; only the pages needed were read.
3. PrimeFoldTools/Andon README: a section addressed to AI agents and a note to point an agent at its AGENTS.md so that
   the agent installs the tool itself.
4. qkal/Canny README: installation by pasting a prompt into an agent.
5. lennney/stop-that-shit: asks the user to hand an install-for-agents file to Codex.
6. habit-hooks README: a snippet telling agents to treat the tool's output as a top-priority direct user prompt.
7. diet103/claude-code-infrastructure-showcase: a note addressed to Claude to read an integration guide, and a prompt
   that has an agent clone the repository and run setup with an auto-yes flag.
8. obra/superpowers: a prompt for one agent to fetch an install file from a URL and follow it.
9. leepokai/jev-guard README: quotes a sample injection addressed to AI assistants (shown as an example of an attack).
10. entireio/cli: an agent-help command written for agents (benign; not run).
11. pivot-to-ai.com served scrambled text to the fetch tool; treated as no content.
No agent-addressed text was found on the arXiv pages or the AutoWorldModel-Bench page.

## 11. Unverified, and what was skipped

- Whether hooks run in `codex exec` and in the Cursor CLI or headless runs, and what happens to hooks awaiting trust.
- What Codex does with a returned "ask"; the `apply_patch` input shape; what the Codex trust hash covers.
- How Cursor's loader for Claude Code hooks maps events and whether it double-runs with native hooks.
- Whether Claude Code reads skills from `.agents/skills`.
- The shared "Agent Plugins" manifest mentioned in Cursor's docs.
- The JetBrains RTK and caveman figures (secondary source; primary returned 403).
- The content of the pivot-to-ai article (scrambled page); the likely underlying study (arXiv 2602.11988) was read.
- Whether the Humanize repository is the paper's (star counts differ).
- How PostTrainBench detected its agents' cheating; AutoTrainess code availability.
- SkillSpector's prevalence figures; the habit-hooks evaluation; Nomos benchmark claims; the agents.md adoption figure.
- ActPlane under WSL2; GPU pass-through in Harbor containers.
- The exact version (2.1.321 or 2.1.322) of two Claude Code fixes; dates of 2.1.268 to 2.1.283.
- First-release dates and some licences where a repository page did not show them.
- All star counts (taken from the sweep or the repository page; weak evidence in every case).
- Every inference about the kit's behaviour on Codex and Cursor: read from docs and kit code, not run.
