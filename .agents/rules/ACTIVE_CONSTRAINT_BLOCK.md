# ACTIVE CONSTRAINT BLOCK - Read Before Every Action (Non-Negotiable)
# Version: 1.1 | Updated: 2026-09-17 | Loaded: auto (global + workspace)
# Token budget: ~200 tokens. Purposely minimal. Do NOT expand.

## 10 HARD GATES - Verify ALL before proceeding with any action:

[GATE 1 - CODEBASE PURITY]
Zero candidate PII in core/*.py or scripts/*.py. Names, emails, phones, CTCs, cities, model IDs, Windows user paths - ALL must resolve from candidate_config.json via ProfileContext. ALSO: Zero inline question-detection keyword lists (any `for k in ["notice period", ...]` or `for k in ["describe", ...]` literal lists in ai_client.py). ALL keyword lists live in candidate_config.json["screening_heuristics"] — read via sh.get(). If you are about to write any literal keyword list, STOP and add it to screening_heuristics config instead.

[GATE 2 - FILE WRITE PRE-CHECK]
Before editing ANY file in core/ or scripts/, read that file's # AI CONTEXT & CHANGE LOG header first. Then append a new entry when done. Never delete prior entries.

[GATE 3 - DEVELOPER GATEKEEPING]
You are forbidden from editing production code without: Report -> Review -> Manual Approval -> Execution. Propose the diff. Wait for explicit approval. Do not self-authorize.

[GATE 4 - GIT COMMAND SAFETY]
Never run git commit or git push without: (a) --no-gpg-sign, (b) git pull --rebase origin main FIRST. Use guard.safe_git_push() in Sophron context. Never raw git in Career Agent context.

[GATE 5 - PROFILES DIRECTORY ISOLATION]
profiles/ is the runtime sandbox. During development or code editing, you NEVER touch profiles/ files. The reference schema is profiles/default_user only.

[GATE 6 - SOPHRON WRITE PROTOCOL]
All Sophron file writes use guard.safe_write_json() or guard.safe_append_line(). Never open()+json.dump(). The SophronWriteGuard must be instantiated and guard.register_session() called BEFORE any Sophron read or write.

[GATE 7 - PURITY CHECK BEFORE SCRIPTS]
Before running any python core/... command: run ProfileContext.verify_codebase_purity(). If it fails, fix the violation before running the script.

[GATE 8 - IPC ANSWER FORMAT]
For numeric/experience questions from pending_question.json: answer is a clean integer string ("1", "2", "0"). NEVER a sentence. For open-ended questions: derive strictly from resume.md. Never invent credentials.

[GATE 9 - SUBSYSTEM ISOLATION]
Career Agent (core/, scripts/, profiles/, docs/) and Sophron (Sophron/) are completely separate. Zero cross-imports. Zero cross-writes.

[GATE 10 - SOPHRON MILESTONE WRITING]
Write a Sophron card at every milestone. A milestone is: task completed, user corrects AI, topic switches, plan approved/rejected, a-ha moment. Not just at session end. Use guard.safe_write_json(). Include CONTEXT_CLASSIFICATION fields.

---
## ACTIVE GUARDRAILS REFERENCE (C-Series)
[C24] Card-Level Experience Band Gating: exp_text from SRP card MUST be parsed before deep scan. If card min_exp > candidate.total_experience_years + target_jobs.max_experience_gap_years → reject [experience_gap_gated]. ALL thresholds read from candidate_config.json — zero hardcoding in Python.
[C32] Two-Stage Page Navigation Timeout Recovery.
[C34] Radio Chip Option-Constrained Resolution.

---
## QUICK REMINDER: The AG Brain is the SOLE talent strategist.
## Python scripts = dumb actuators. Zero heuristics, zero templates, zero branches on experience.
