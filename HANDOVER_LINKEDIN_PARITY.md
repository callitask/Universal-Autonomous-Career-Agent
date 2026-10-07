# Handover — Complete Session Record: Enterprise Audit, Live Operations, LinkedIn Parity, Tailoring
> Status: implemented, verified, pushed (see §12 for commits). For the incoming agent: read this first, then the files it cites.
> Conventions: no candidate PII, secrets, or machine-specific values appear in this document. All tunables resolve from `profiles/<profile>/candidate_config.json` or environment at runtime. Paths are repo-relative.

## 1. Mandate this session ran under
Dual-engine preservation (API engine + Integrity 2.0 file-IPC engine; never remove either); docs-first comprehension of the whole repo; verification of a supplied third-party audit report claim-by-claim with independent `file:line` evidence; library-style short code over god-file growth; enterprise production-ready organization with portal-separated execution paths (company-direct vs LinkedIn vs Naukri); zero hardcoded values with runtime resolution from profile JSON; no secrets ever pushed; plan-then-approve workflow for large work; append-only history everywhere.

## 2. Method (keep working this way)
Todo-gated phases (discover → map → verify → audit → implement → prove). Verify-first: working-tree diffs inspected before new edits so prior-pass fixes were confirmed, not redone. Every code edit minimal, platform-scoped, with append-only `AI CONTEXT` log entries. Live DOM probes settled every selector dispute. UI fixes proven by resulting state (modal text, tracker rows), never by click success. Profile JSON edits only on explicit principal order (backups first, atomic tmp+replace). Never commit/push without approval. Never read live profiles except for directly requested diagnosis; never copy live values into code, docs, or memory stores. Temp probe scripts deleted after use.

## 3. Architecture map (as verified, not as documented)
- `core/continuous_career_agent.py` — daemon loop; fresh `04_job_discovery.py` subprocess per cycle, so profile/ledger/config edits apply next cycle with no restart (only `.py` edits need restarts).
- `core/04_job_discovery.py` — batched discovery (ARM collect → BRAIN batch triage → EXECUTE deep-scan/apply), one designation per cycle via `core/utils/search_state_manager.py`.
- `core/ai_client.py` — dual-brain reasoning, batch inline evaluators (Colab chunk 10, Gemini chunk 40, both config-driven), two-stage scoring (deterministic Stage 1 gates, LLM Stage 2, 60-point apply bar, 40–65 borderline IPC window covering LLM-failure fallback; in API mode a parsed verdict IS the borderline arbitration).
- `core/05_apply_jobs.py` — `ChatbotResolver` (Naukri drawer), `LinkedInApplyHandler` (Easy Apply modal), `ApplicationEngine` dispatcher with explicit per-platform branches; unknown platforms never fall into the Naukri path.
- `core/02_profile_sync_naukri.py` / `core/03_profile_sync_linkedin.py` — 5-step selective profile syncs, fully decoupled; runs are search-first, syncs only under the opt-in flag.
- `core/generate_factual_tailored.py` — factual tailoring + AI reframe pass + PDF render (see §8).
- `core/utils/` — shared libs only: `profile_context` (sandbox, purity enforcer, ledger incl. batch API), `browser_manager` (CDP lifecycle), `search_state_manager`, `sanitize`, `url_filters`, `apply_status`, `ai_rate_manager` (pacing floor, model bans).
- `CompanySiteApply/` — fully decoupled on-demand company-site engine (finger registry pattern); never imports `core/` job loops.
- `scripts/build_knowledge_index.py` — local graph+vector index; excludes secrets and live profiles; `--check` must exit 0.

## 4. Prior audit verification (the supplied report, independently re-derived)
Working tree already contained staged-but-uncommitted fixes for: missing stdlib import in the browser manager, sync key mismatch, scraper context crashes, empty-LLM-response handling, IPC gating, learned-truth poisoning, ATS bigram filter, batch ID types, preflight abort, CSV BOM, stale external-repo test path. Each was diff-verified before acceptance. Rejected/stale claims were listed explicitly rather than implemented. Remaining gaps found genuine and fixed are recorded below and in the commit messages.

## 5. Shared libraries created (import, never fork)
- `core/utils/sanitize.py` — formula-injection-safe CSV cells, untrusted-portal-text wrappers for LLM prompts, safe filenames.
- `core/utils/url_filters.py` — portal query-param builders (collapsed identical CTC/WFH branch forests).
- `core/utils/apply_status.py` — canonical status constants with verified-success helpers.
- `CompanySiteApply/utils/config_resolver.py` — dynamic candidate-config resolution (explicit path → candidate hint → immutable default blueprint only).
- `requirements.txt` — pinned runtime deps.

## 6. Correctness fixes applied (Naukri path + shared core)
- Target-keyword property reads the real schema keys (scrapers were silently receiving empty lists).
- Premature success eliminated: no applied-status without explicit DOM evidence; drawer-close alone is not completion; inactivity/timeout paths stay reachable.
- Heuristic and blind first-option answers never persisted as learned truths — including the chatbot radio path (last refuge found later by audit).
- CSV formula injection neutralized; portal JD text wrapped as untrusted prompt data; prompt-injection boundary documented.
- Colab batch ID types normalized; preflight aborts honestly without browser; CSV BOM handled; diagnostic timeouts made finite.
- Company blacklist matching is word-boundary in discovery Gate 2 and the apply-loop gate (substring matching had blacklisted an unrelated company).
- Poisoned/generic exclusion terms removed where they killed in-domain roles; a truncated exclusion slice (first-30) that silently neutered triage arming was widened to the full list.
- CDP endpoint literals purged from all code sites (config → environment resolution, explicit errors when unset).
- Batch chunk sizes and fallback model order are config-driven (reliable lite model first).
- Intra-batch URL dedupe (location double-passes no longer double-evaluate).
- Engine toggles honored; credentials never tracked or indexed; test isolation scoped to the correct repo.

## 7. Secrets, hygiene, cleanup
- Untracked: portal DOM captures, regenerable knowledge artifacts, credentials, live profiles, logs, caches, scratch dumps, temp scripts. Staged deletions verified secret-free before every commit.
- Removed: bytecode caches, scan leftovers, OS artifacts, scratch dumps.
- Knowledge index rebuilt fresh after every code change; privacy tests assert zero live-profile leakage and blueprint-only indexing.

## 8. Resume tailoring program (reorder → reframe, both guaranteed)
- Forensic verdict: tailored outputs carry 100% of master bullets with identical text and equal page budgets — tailoring was reorder-only (summary rewrite + skills/bullet reordering), so "shorter" impressions are reorder perception plus the fixed page squeeze.
- AI reframe pass (default ON, per-profile toggle): each employment role sent to the AI brain under a same-count/same-order/no-new-facts contract; Python validates per role (count equality, every number pre-existed, distinctive tech tokens ⊆ master+JD) and keeps originals atomically on any violation; returned sentences normalized back to bullet markers (models strip them — caught live); novel Capitalized words tripwire-logged for owner audit; offline mode keeps originals silently.
- Structural zero-omission guardrail runs after every build. Poisoned learned truths (mislabelled experience phrasing, empties) and principal-ordered factual corrections handled with backups first.
- Docs: tailoring guide versioned with the Zero-Omission Guarantee + reframe contract; architecture algorithm extended.

## 9. Live operations record (evidence, not claims)
- Free-tier API behavior: burst models rate-limit, the manager bans them 120s, the lite fallback carries the load; per-process bans reset on fresh runs; sleeps occur only under true exhaustion.
- Funnel forensics method: scan the outcome ledger (status distribution, near-miss band, blacklist hits) before re-reading logs; audit exclusion lists against the immutable blueprint set whenever matches dry up.
- Seniority calibration is the highest-leverage lever: an overstated seniority label starved triage; retuning to the evidence-backed band restored flow with same-session applications.
- Keyword tuning per C23 (dead designations replaced with resume-grounded terms, backups kept) delivered same-session results; rotation parking used to test new terms within cycle budgets.
- Chatbot path fills every control every iteration with per-question audit logs; all exits explicit. Chatbot completions fail at portals (drawer drops, rejection banners) while 1-click applies succeed — portal friction, not scoring, binds chatbot applies.
- LinkedIn applies flow end-to-end (first Easy Apply commit observed with pre-filled profile modal; further commits after).
- LinkedIn session-health caveat: bot-detection artifacts plus armed captcha observed with swallowed apply clicks while reads worked — treat as soft-throttle (cooldown with zero LinkedIn automation, governors on, never hammer dead buttons); one human click-test distinguishes session flag from posting-level issues.

## 10. LinkedIn parity program (LinkedIn-scoped; Naukri provably unchanged via live regression)
1. Transport: per-iteration shared rate-limiter pacing; LLM calls already chain rotation with no hardcoded model.
2. Armed triage: shared batch prompt carries exclusions + bar; advisory line for thin-metadata cards.
3. Score plumbing: platform-neutral alias into the single shared calibration path; dict actually passed at the call site; LinkedIn adapter returns empty until pane parsing lands.
4. Card enrichment: metadata classification, location/posted extraction, honest empties; chunk sizes config-driven.
5. Timeouts: two-stage navigation from config defaults; experience-band gating on explicit numeric bands only.
6. Solver: event dispatch after fills; local numeric formatter with single adapt-retry; per-job modal QA audit on every exit; no shared calls into the Naukri solver.
7. Proficiency tiers: config-gated lowest-tier mapping; dormant without both keys; identity/health never tier-mapped.
8. Coupling removed: LinkedIn-internal keys renamed with old-key fallbacks; unknown platforms explicitly rejected.
9. Selector repair (live-DOM proven, twice): current title-link/company/location selectors with legacy fallbacks; URL absolutization; missing-href fallback via container job IDs; verified map stored in platform heuristics config. Root-caused two stacked silent blackouts (dead selector + None-href TypeError inside bare `except: continue`).
10. Search-pane apply flow (live-proven): exact job-ID card match only across fallback queries; pane-scoped button; render polling. The standalone view-page button is inert.
11. Numeric validation retry (bidirectional): portal red-text demanding digits strips answers to digits and resubmits once, then aborts honestly.
12. Step-progression tracking: per-iteration modal fingerprint; repeated stuck steps trigger broad error collection, one adapt-retry, then evidence-logged abort; pre-filled blockers logged read-only.
13. Control coverage: hidden file inputs, per-option checkbox confirmation, custom div/combobox dropdowns (expand → match → click → log), all H1-safe.
14. Velocity governors: daily LinkedIn cap with in-run counting; in-modal challenge detector that discards and human-gates (never auto-solved).
15. Chatbot honesty backport: blind first-option submit removed (honest abort with manual-review log).

## 11. Profile operations performed (principal-ordered, all backed up)
- Exclusion-list surgery (domain terms that blocked own-domain roles removed; generic-word traps removed).
- Seniority retune to the evidence-backed band.
- Learned-truth poisoning purge (mislabelled phrasing, empties) and factual corrections.
- Ledger resets scoped to wrongly-killed entries (re-evaluated under fixed rules on subsequent cycles).
- New-profile readiness audit method: schema keys, heuristics completeness, keyword domain-fit, cognitive-profile domain/seniority, truth-store scan, ledger/rotation state — fix only what is proven wrong.

## 12. Commit record (repos pushed separately, never jointly)
- Enterprise hardening batch (shared libs, correctness fixes, secrets hygiene).
- Doc remediation batch (17-item update list) plus purity follow-ups.
- LinkedIn parity implementation batch (items above + live-debug repairs).
- Tailoring reframe batch (AI pass, validation, guardrail, docs).
- Memory repo: sequential session turns with reflection cards, insight cards with evolved-thinking references, graph nodes/edges kept in sync with counts, milestone ledger, rewritten boot summaries — append-only throughout, history never rewritten.

## 13. Verification gates (run all after any change)
Compile touched files; purity check pure with zero violations; index rebuild fresh; both test suites green; one live discovery cycle with zero errors and unchanged sibling-platform behavior; UI fixes proven by resulting state (modal text, tracker rows), never by click success; generative features proven by output diffs plus validator behavior.

## 14. Known-open items (do not regress, fix with approval)
- Rotation list oscillates as cognitive cycles and search state re-merge (dedup absorbs; stabilize with a single union list if desired).
- Portal match-signal scraping and detail-pane seniority parsing need live-DOM implementation.
- Chatbot single-retry on premature drawer close (proposed, unimplemented).
- Unverified blacklist memberships (confirm before extending).
- LinkedIn cooldown state and pending human click-test outcome (see §9, last bullet).
