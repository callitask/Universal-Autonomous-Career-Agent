# SCAR TISSUE LOG - Append Only. Never Delete. Never Edit Prior Entries.
# Purpose: Empirical record of actual rule violations + exact corrections.
#          This is more powerful than WORKSPACE_RULES.md because it is concrete, not abstract.
#          Every entry is a scar from a real failure. Re-read at every session start.
# Format: [DATE] VIOLATION TYPE -> What happened -> Correct behavior -> Never repeat

---

## [2026-09-09] HEURISTIC LEAK IN PYTHON SCRIPT
- **File**: core/ai_client.py -> analyze_and_expand_designations()
- **What happened**: AI added if candidate_exp >= 8.0: standard_templates = [...] as a fallback branch. Python script was making intelligent role decisions.
- **Correct behavior**: Python scripts are strictly actuators. The AG Brain generates designation lists via IPC or pre-configures them in candidate_config.json during session push-start. No experience threshold branching, no hardcoded role templates, ever.
- **Never repeat**: Before writing ANY conditional logic in core/*.py that branches on candidate attributes - STOP. That logic belongs in the AG Brain, not in code.

---

## [2026-09-10] CITY NAME HARDCODING
- **File**: core/02_profile_sync_naukri.py
- **What happened**: AI wrote a literal city string ("Bangalore") as a default fallback when the profile location list was empty.
- **Correct behavior**: Read from candidate_config.json["target_jobs"]["preferred_locations"] via ProfileContext. If the list is empty, raise a configuration error - do NOT silently default to any hardcoded city.
- **Never repeat**: Zero string literals for locations, cities, company names, or skills in any core/ or scripts/ file. All values resolve from ProfileContext at runtime.

---

## [2026-09-11] SOPHRON WRITE GUARD BYPASS
- **What happened**: AI used open(file, "w") + json.dump() to write to nodes.json directly, bypassing the SophronWriteGuard. Caused race condition when two AG sessions were running simultaneously.
- **Correct behavior**: ALL writes to shared Sophron files (nodes.json, edges.json, graph_index.json, reflections_index.json, current_week_trend.md) MUST go through guard.safe_write_json(). The guard must be instantiated first via SophronWriteGuard(session_uuid, workspace, task_summary) and guard.register_session() called before any read or write.
- **Never repeat**: If you are about to call open() on any Sophron file, you are doing it wrong. Always guard.safe_write_json().

---

## [2026-09-11] SOPHRON SESSION INIT SKIPPED
- **What happened**: AI skipped guard.register_session() at session start and skipped guard.deregister_session() at end. Multi-session detection (detect_multitasking()) never ran. Session registry became stale.
- **Correct behavior**: Session init (STEP 0 of 01_sophron_session_init.md) is non-negotiable. Instantiate guard, register_session(), run detect_multitasking(), then proceed. At session end: deregister_session(). This is not optional.
- **Never repeat**: SophronWriteGuard must be the first operation, before reading ANY file in a Sophron session.

---

## [2026-09-11] TRANSCRIPT PATH STALE
- **What happened**: master_agent_config.json still pointed to the UUID of a previous session. transcript_learner.py was ingesting from a dead session's transcript.
- **Correct behavior**: STEP 2 of 01_sophron_session_init.md - check master_agent_config.json -> paths -> transcript_path UUID. If it doesn't match current session UUID, update it immediately before running transcript learner.
- **Never repeat**: Always update the transcript path at the start of every session. Current session UUID is always available in the conversation metadata.

---

## [2026-09-13] RESUME TAILORING WITH HALLUCINATED CREDENTIALS
- **What happened**: AI-generated resume tailoring answer in pending_question.json included a skill claim not present in the candidate's resume.md, in order to better match the job description.
- **Correct behavior**: RESUME_TAILORING answers must be derived 100% from the actual content of profiles/$PROFILE/resume.md. If the candidate does not have a skill, the tailored summary does NOT mention it. ATS purity > match score.
- **Never repeat**: Before writing any RESUME_TAILORING JSON answer, verify every claim against resume.md. No invented competencies. No extrapolated expertise. Factual grounding only.

---

## [2026-09-13] MILESTONE SOPHRON CARDS SKIPPED (MOST FREQUENT VIOLATION)
- **What happened**: Multiple sessions (turns 27-40) completed significant work (daemon launches, config changes, apply cycles) without writing Sophron insight cards. Cards were only written at the end when user reminded the AI.
- **Correct behavior**: A milestone card MUST be written after: every task completion, every user correction, every topic switch, every plan approval, every discovery. Not just at session end.
- **Never repeat**: Every 5 exchanges, silently self-check: "Have I written a Sophron card recently?" If no, write one now. This is non-negotiable per STEP 4 of 01_sophron_session_init.md.

---

## [2026-09-14] CONTEXT SWITCH NOT RECORDED IN SOPHRON
- **What happened**: User shifted context mid-session from monitoring the live job agent daemon to discussing Sophron architecture + rule enforcement. The Sophron card written after this did NOT record that a context switch occurred, why it occurred, or what the previous context was.
- **Correct behavior**: Every insight card written after a context switch must include CONTEXT_TRANSITION fields: previous_context, trigger_for_switch, new_context, cognitive_load_at_switch.
- **Never repeat**: If the user's message represents a topic change from the prior message - flag it. Include CONTEXT_TRANSITION in that card. This is how Sophron builds a true workflow record.

---
# INSTRUCTIONS FOR ADDING NEW ENTRIES:
# 1. Append at the bottom of this file (never edit or delete above)
# 2. Format: ## [DATE] VIOLATION TYPE
# 3. Include: File/context, what happened, correct behavior, "never repeat" directive
# 4. Keep each entry under 10 lines
# 5. This file must be re-read at every session start (part of STEP 1 cold-start load)
