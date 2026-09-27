# Handover — Enterprise Audit + LinkedIn Parity + Tailoring Programs
> Status: implemented, verified, uncommitted (27 changed files). For the incoming agent: read this first, then the files it cites.
> Conventions: no candidate PII, secrets, or machine-specific values appear in this document. All tunables resolve from `profiles/<profile>/candidate_config.json` or environment at runtime. Paths are repo-relative.

## 1. What this agent is
Autonomous job-application system with two preserved engines: an API engine (multi-key round-robin Gemini client + Colab-compatible GPU gateway + inline batch evaluator) and an Integrity 2.0 engine (file-based IPC answered by an external brain/cron). Priority is always Colab → Gemini inline → file IPC → deterministic fallback. Three cooperating loops exist: continuous discovery/apply, IPC signal relay, and the answering side. Never remove an engine; degradation must always fall through, never crash.

## 2. How work was done across these sessions (keep working this way)
Verify-first, plan-approved execution. Every claim was re-derived with `file:line` evidence before editing; working-tree diffs were inspected before new changes; live DOM probes settled every selector dispute; all edits are minimal, platform-scoped, and carry append-only `AI CONTEXT` log entries in file headers. Never edit `profiles/` except the single live profile's JSON when the principal explicitly orders profile-data changes (always back up first, atomic tmp+replace writes). Never commit or push without explicit approval. Never read live profiles for any reason other than a directly requested diagnosis, and never copy live values into code, docs, or memory stores. Prefer tiny inline probes over throwaway scripts; delete every temp script after use.

## 3. Architecture map (as verified, not as documented)
- `core/continuous_career_agent.py` — daemon loop; spawns a fresh `04_job_discovery.py` subprocess per cycle, so profile/ledger/config edits apply next cycle with no restart (only `.py` edits need restarts).
- `core/04_job_discovery.py` — batched discovery (ARM collect → BRAIN batch triage → EXECUTE deep-scan/apply), one designation per cycle via `core/utils/search_state_manager.py`.
- `core/ai_client.py` — dual-brain reasoning, batch inline evaluators, two-stage job scoring (deterministic Stage 1 gates, LLM Stage 2, 60-point apply bar, 40–65 borderline IPC window for LLM-failure fallback). In API mode a parsed verdict IS the borderline arbitration (early return); the file-IPC gate covers LLM failure only.
- `core/05_apply_jobs.py` — `ChatbotResolver` (Naukri drawer), `LinkedInApplyHandler` (Easy Apply modal), `ApplicationEngine` dispatcher (explicit per-platform branches; unknown platforms must never fall into the Naukri path).
- `core/02_profile_sync_naukri.py` / `core/03_profile_sync_linkedin.py` — 5-step selective profile syncs, fully decoupled. Entry is search-first; syncs run only under the opt-in flag.
- `core/generate_factual_tailored.py` — factual tailoring + AI reframe pass + PDF render (see §8).
- `core/utils/` — shared libs only: `profile_context` (sandbox, purity enforcer, ledger incl. batch API), `browser_manager` (CDP lifecycle), `search_state_manager`, `sanitize` (CSV safety, untrusted-text wrapping, filename safety), `url_filters` (portal query params), `apply_status` (canonical statuses), `ai_rate_manager` (pacing floor, model bans).
- `CompanySiteApply/` — fully decoupled on-demand company-site engine (finger registry pattern); never imports `core/` job loops.
- `scripts/build_knowledge_index.py` — rebuilds the local graph+vector index; excludes secrets and live profiles; `--check` must exit 0.

## 4. Shared libraries created (import, never fork)
- `core/utils/sanitize.py` — formula-injection-safe CSV cells, untrusted-portal-text wrappers for LLM prompts, safe filenames.
- `core/utils/url_filters.py` — portal query-param builders (collapsed identical CTC/WFH branch forests).
- `core/utils/apply_status.py` — canonical status constants with verified-success helpers.
- `CompanySiteApply/utils/config_resolver.py` — dynamic candidate-config resolution (explicit path → candidate hint → immutable default blueprint only; no live profile names anywhere).
- `requirements.txt` — pinned runtime deps.

## 5. Correctness fixes applied (all verified live unless noted)
- Scraper interface crash: scrapers referenced context attributes that did not exist; added config-derived properties plus graceful fallbacks.
- Profile-sync key mismatch: one sync consumed wrong AI-result keys and force-overwrote everything; aligned to the canonical action/decision/description contract.
- Empty LLM responses no longer masquerade as success (rotation continues); IPC gating no longer suppresses fallback when configured clients are failing.
- Heuristic and blind first-option answers are never persisted as learned truths — eliminated on all solvers including the chatbot radio path (last refuge found by audit).
- Premature success eliminated: no applied-status without explicit DOM evidence; drawer-close alone returns drawer-closed; inactivity/timeout paths stay reachable.
- CSV formula injection neutralized at all tracker writes; portal JD text wrapped as untrusted data in prompts.
- Colab batch ID type mismatch fixed (string-normalized decision keys).
- Preflight aborts honestly when the browser endpoint is unreachable.
- CSV ledger reads handle BOM; test-connection diagnostics use finite timeouts.
- Company blacklist matching is word-boundary everywhere (substring matching had blacklisted an unrelated company whose name merely contained a blacklisted string); same fix applied to the apply-loop gate.
- Bare generic-word negatives removed where they killed in-domain roles; full exclusion list (not a truncated slice) now reaches batch triage.
- Target-keyword property reads the real schema keys; CDP URL resolves from context with environment fallback.
- CDP endpoint literals purged from all 7 code sites (config → environment resolution, explicit errors when unset).
- Batch model chunk sizes are config-driven; fallback order puts the reliable lite model first.
- Intra-batch URL dedupe (location double-passes no longer double-evaluate cards).
- Colab/Gemini engine toggles honored; credentials files stay untracked and are never indexed.

## 6. Secrets, hygiene, cleanup
- Untracked via version control: portal DOM captures, regenerable knowledge artifacts, credentials, live profiles, logs, caches, scratch dumps. Verification scripts confirm none of these are tracked.
- Removed: bytecode caches, scan leftovers, OS artifacts, scratch analysis dumps, temp probe scripts.
- Knowledge index rebuilt fresh after every code change; privacy tests assert zero live-profile leakage and blueprint-only indexing.

## 7. Live operations record (evidence, not claims)
- Free-tier API behavior observed: burst models return rate-limit/overload errors and are banned 120s by the rate manager; the lite fallback carries the load; sleeps occur only under true exhaustion.
- Funnel forensics method that works: scan the outcome ledger (status distribution, near-miss band, blacklist hits) before re-reading logs; audit exclusion lists against the 4-term immutable blueprint whenever matches dry up.
- Seniority calibration is the highest-leverage lever: an overstated seniority label starved triage of level-appropriate roles; retuning to the evidence-backed band restored flow (multiple same-session applications after the retune).
- Chatbot path fills every control every iteration with per-question audit logs; all exits are explicit (stuck-loop breaker, silence timeout, drawer-vanish, platform rejection, zero-experience circuit breaker, manual-review logging).
- Chatbot completions fail at portals (drawer drops, rejection banners) while 1-click applies succeed — portal friction, not scoring, is the binding constraint on chatbot applies.
- LinkedIn applies now flow end-to-end (first Easy Apply commit observed with pre-filled profile modal). LinkedIn session health caveat (§9, last bullet).

## 8. Resume tailoring program (reorder → reframe, both guaranteed)
- Forensic verdict: tailored outputs carry 100% of master bullets with identical text (equal counts, equal average length, equal page budgets) — tailoring was reorder-only (summary rewrite + skills/bullet reordering), so "shorter" impressions are reorder perception plus the fixed page squeeze.
- AI reframe pass (default ON, per-profile toggle `target_jobs.resume_bullet_reframing`): each employment role sent to the AI brain under a same-count/same-order/no-new-facts contract; Python validates per role before accepting — count equality (nothing skipped), every number pre-existed in the originals (no invented metrics), distinctive tech tokens ⊆ master+JD (no new stack → interview-safe); violations keep originals atomically. Silent skip when no API brain exists (offline runs never stall). Returned sentences normalized back to bullet markers (models strip them — caught live by the guardrail).
- Structural zero-omission guardrail runs after every build (text-match mode normally, count mode when reframed); residual single-common-word tech gap is covered by terminal tripwire logging for owner audit, not false rejects.
- Poisoned learned truths (mislabelled experience phrasing, empties) and factually corrected answers (principal-ordered) are handled with backups first.
- Docs: tailoring guide v1.1 (Zero-Omission Guarantee + reframe contract), architecture algorithm extended.

## 9. LinkedIn parity program (LinkedIn-scoped; Naukri provably unchanged via live regression)
1. Transport: per-iteration shared rate-limiter pacing in the modal loop; all LLM calls already chain rotation with no hardcoded model.
2. Armed triage: shared batch prompt carries exclusions + qualification bar; LinkedIn advisory line for thin-metadata cards.
3. Score plumbing: platform-neutral score alias resolved into the single shared calibration path; discovery passes the dict; LinkedIn adapter returns empty (zero bonus fabricated) until pane parsing lands.
4. Card enrichment: all metadata items classified (experience-band regex wins; location/posted extracted); empties stay honest; chunk sizes config-driven.
5. Timeouts: navigation is two-stage from config defaults; experience-band gating fires only on explicit numeric bands.
6. Solver: input/change event dispatch after fills; LinkedIn-local numeric formatter with single adapt-retry; per-job modal QA audit on every exit; no shared calls into the Naukri solver.
7. Proficiency tiers: config-gated lowest-tier mapping before IPC fallback; dormant without both config keys; identity/health never tier-mapped.
8. Coupling removed: LinkedIn-internal card/headline keys renamed with old-key read fallbacks; unknown platforms explicitly rejected instead of falling into the Naukri path.
9. Selector repair (live-DOM proven, twice): current title-link, company-subtitle, location-caption selectors with legacy fallbacks; relative view URLs absolutized; missing-href fallback via container job IDs; verified selector map stored in platform heuristics config. Root-caused two stacked silent blackouts (dead selector + None-href TypeError inside bare `except: continue`).
10. Search-pane apply flow (live-proven with profile-prefilled modal in ~2s): exact job-ID card match only (multi-query search, never a nearby job); pane-scoped apply button; render polling instead of fixed delays. The standalone view-page button is inert — never use it.
11. Numeric validation retry (bidirectional): portal red-text demanding digits strips answers to digits and resubmits once, then aborts honestly.
12. Step-progression tracking: per-iteration modal fingerprint; 3×-stuck steps trigger broad error collection, one adapt-retry, then evidence-logged abort; pre-filled blockers logged read-only.
13. Control coverage: hidden file inputs handled (set + change dispatch, never visibility-gated); checkbox groups resolved per-option with Yes/No confirmation; custom div/combobox dropdowns expanded, matched (brain → tier → IPC → abort), clicked, and logged.
14. Velocity governors: daily LinkedIn apply cap from config with in-run counting; in-modal verification-challenge detector that discards and human-gates (challenges are never auto-solved).
15. Chatbot honesty backport: blind first-option submit removed from the radio path (honest abort with manual-review log instead).

## 10. Verification gates (run all after any change)
Compile all touched files; purity check must print pure with zero violations; knowledge index rebuild must report fresh; both test suites must pass; one live discovery cycle must complete with zero errors and unchanged Naukri behavior; any UI-action fix must be proven by resulting state (modal text, tracker status), never by click success.

## 11. Known-open items (do not regress, fix with approval)
- Rotation list oscillates in size as cognitive cycles and search state re-merge; harmless to quota (dedup absorbs) but noisy — stabilize with a single union list if desired.
- Actual portal match-signal scraping and detail-pane seniority parsing need live-DOM implementation.
- Chatbot single-retry on premature drawer close (proposed, unimplemented).
- Rotation parking on new search terms to test keyword swaps within a cycle budget (operator technique, used successfully).
- LinkedIn session health: bot-detection iframe plus armed captcha observed with swallowed apply clicks while reads worked — treat as soft-throttle (cooldown with zero LinkedIn automation, governors on, never hammer dead buttons); one human click-test distinguishes session flag from posting-level issues.
- Unverified company-blacklist membership (confirm before adding more names).
