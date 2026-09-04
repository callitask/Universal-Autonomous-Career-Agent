# Gemini Web AI Multi-Step Onboarding Prompts

This guide contains the official 3-step prompt sequence to initialize Gemini Web AI with full context, operational boundaries, and all 12 bug prevention guardrails.

---

## Step 1: Upload `docs/WORKSPACE_RULES.md`
**Prompt to accompany upload:**
```text
I am uploading the WORKSPACE RULES document for my Universal Autonomous Career Agent project. This document contains 8 mandatory directives and 12 known bug prevention guardrails that govern ALL code you write in this session.

CRITICAL INSTRUCTIONS:
1. Read the entire document thoroughly — every directive, every appendix, every bug guardrail.
2. These rules are ABSOLUTE and OVERRIDE your default coding patterns.
3. Key constraints you MUST internalize:
   - DIRECTIVE 1: Always output 100% complete files or complete contiguous blocks. Never use placeholder comments like "rest of code remains the same".
   - DIRECTIVE 2 (CLAUSE 8): Strict Developer Boundary. In this development session, you are strictly the Principal Agent Developer (editing core/, docs/, and tests). You must NEVER manually edit files inside the profiles/ folder. The runtime agent must autonomously inspect resumes, synthesize cognitive_profile.json, and maintain candidate sandboxes at runtime.
   - DIRECTIVE 3: Antigravity 2.0 Dual-Brain Architecture — AG 2.0 is the primary brain. AI failures must gracefully fall back to File-Based IPC (pending_question.json). NEVER use terminal stdin (input() or readline()), as it freezes the background daemon.
   - DIRECTIVE 4: Method signatures and contracts are immutable. evaluate_job_match() executes deterministic factual scoring first in Zero-API mode and strictly gates Antigravity 2.0 IPC evaluation to the borderline window (40% <= score <= 65%). High-fit (>= 60%) qualifies immediately; out-of-domain drops at Stage 1 (0%); clear rejections (< 40%) resolve without IPC. MatchResult supports full tuple unpacking, attribute access, and dict methods.
   - DIRECTIVE 5: Naukri and LinkedIn handlers are strictly decoupled. Modals require container-isolated scrolling and React synthetic event dispatch for contenteditable elements. Guardrail H1 strictly prohibits blind options[0] or valid_opts[0] fallbacks in LinkedInApplyHandler, requiring IPC resolution and automated modal dismissal with 'Discard application' confirmation on failure or max steps.
   - DIRECTIVE 7: Canonical CSV tracker schema, deduplication logic, and status codes are strictly enforced. ctx.load_processed_ledger() returns ProcessedLedger (a hybrid dictionary with set API parity) supporting O(1) deduplication and structured metadata dicts (status, company, title, score, timestamp).
   - DIRECTIVE 8: There are 12 specific critical bug guardrails (C1, C2, C3, C4, C6, C9, H1, H2, H3, H4, H5, H6) that were fixed — you must NEVER reintroduce them. Specifically, C9 mandates immediate abort on platform rejection banners or premature drawer closure.

4. After reading, confirm you understand by listing:
   - The 8 directive names (including Directive 2 Clause 8 developer boundaries)
   - The 12 bug guardrail IDs (C1, C2, C3, C4, C6, C9, H1, H2, H3, H4, H5, H6) and what each prevents
   - The canonical CSV tracker header schema
   - The method signature, borderline IPC gating window (40-65%), and hybrid MatchResult contract for evaluate_job_match()

Do NOT write any code yet. Just confirm your understanding.
```

---

## Step 2: Upload `docs/ARCHITECTURE_REFERENCE.md`
**Prompt to accompany upload:**
```text
I am uploading the ARCHITECTURE REFERENCE document for the same project. This provides the complete technical blueprint — every module, data schema, execution pipeline, DOM interaction patterns, failure modes, and cognitive engine specifications.

CRITICAL INSTRUCTIONS:
1. Read the entire document thoroughly — all 8 sections.
2. Cross-reference this with the WORKSPACE_RULES you already loaded.
3. Key technical details you MUST internalize:
   - Section 2: The exact subprocess execution chain (continuous_career_agent -> 04_job_discovery -> generate_factual_tailored -> 02b upload -> 05_apply_jobs).
   - Section 3: Dual-Brain, IPC & Ledger contracts:
     * AIClient dynamically synthesizes profiles/<profile>/output/cognitive_profile.json (zero hardcoding).
     * Multi-cycle designation search (Cycle 1 exact, Cycle 2 adjacent, Cycle 3 senior/specialist).
     * Multi-session persistent ledger deduplication via ctx.load_processed_ledger() -> ProcessedLedger (hybrid dict with O(1) lookup and set API parity) and ctx.add_to_processed_ledger() storing structured metadata (status, company, title, score, timestamp).
     * Two-stage cognitive evaluation with Stage 2 deterministic factual scoring executing first and IPC gated strictly to 40-65% borderline roles.
     * LinkedInApplyHandler native modal automation with Guardrail H1 remediation, zero blind fallbacks, IPC option arbitration, and automated discard_and_close_modal() cleanup.
     * Chatbot screening questions route to pending_question.json and log to ques_ans_chatbot.json.
   - Section 4: All data schemas (candidate_config.json, cognitive_profile.json, search_manifest.json, tracker CSV, processed_ledger.json, pending_question.json, ques_ans_chatbot.json).
   - Section 5: Naukri chatbot drawer DOM anatomy — container-isolated scrolling (.chatbot_MessageContainer), radio/chip discovery, and C9 premature drawer closure / platform rejection detection.
   - Section 6: Anti-detection timing parameters (30ms typing, 2500ms post-answer, domcontentloaded navigation, non-blocking profile sync).
   - Section 7 & 8: Failure mode matrix and guardrails H1-H6.

4. After reading, confirm you understand by listing:
   - The full pipeline execution sequence.
   - The IPC and ledger contract (which JSON files connect which scripts, and the ProcessedLedger metadata schema).
   - The ChatbotResolver and LinkedInApplyHandler modal handling protocols (including discard_and_close_modal).
   - The multi-cycle search keyword progression and deduplication chain in 04_job_discovery.py.
   - Guardrail C9's detection criteria and exit states.

Do NOT write any code yet. Just confirm your understanding.
```

---

## Step 3: Upload Codebase Files (`core/`, `README.md`, `UNIVERSAL_AGENT_SETUP.md`)
**Prompt to accompany upload:**
```text
I am uploading the current production codebase files for the Universal Autonomous Career Agent. You now have:
1. ✅ WORKSPACE_RULES.md (8 directives + 12 bug guardrails) — loaded
2. ✅ ARCHITECTURE_REFERENCE.md (complete technical blueprint) — loaded
3. ✅ Production source code files — attached above

WORKING PROTOCOL FOR THIS SESSION:
1. You are operating strictly as the Principal Agent Developer.
2. Every code change you produce must comply with ALL 8 directives in WORKSPACE_RULES.md.
3. Never manually touch or modify files inside the profiles/ folder. All runtime sandbox adaptation must be performed autonomously by the running agent code.
4. Every file you output must be 100% complete — no truncation, no placeholder comments.
5. Before modifying any function, verify it doesn't break callers listed in APPENDIX B of the rules.
6. In 04_job_discovery.py, ensure ctx.load_processed_ledger() is handled via ProcessedLedger (supporting O(1) dictionary key lookups, structured metadata, and set operations).
7. After proposing changes, run through the DIRECTIVE 8 bug guardrail checklist (C1-C6, C9, H1-H6) and confirm no guardrail is violated.
8. ALWAYS respect the AG 2.0 File-Based IPC architecture (pending_question.json). NEVER reintroduce terminal stdin or input() blocking.

READY STATE:
- Confirm you have loaded all documents and source files.
- Confirm the file names and line counts of the code files you received.
- Ask me what task I'd like to work on.
```
