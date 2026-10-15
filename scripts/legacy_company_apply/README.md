# Legacy Company-Site Apply Scripts (Archived 2026-10-12)

> [!CAUTION]
> **DO NOT RUN THESE IN PRODUCTION.** They are preserved for forensic reference only.
> The canonical pipeline is `ApplyOrchestrator` + section sub-agents, launched via
> `run_universal_apply.py` / `search_and_evaluate_jpmc_jobs.py` from the repo root.

| Script | Why archived | Superseded by |
|---|---|---|
| `apply_jpmc_210793889.py` | Single-requisition one-off: hardcoded job ID `210793889`, profile paths, and fixed answers (`At least 5 years`, `Software Engineering`, `JAVA`/`Python`). Violates zero-hardcoding; cannot run for any other profile or role. | `CompanySiteApply/apply_orchestrator.py` + `run_universal_apply.py --autonomous` |
| `heal_all_experience_tiles.py` | Standalone tile healer with hardcoded resume path, fallback cities (`Noida`/`New Delhi`/`Bengaluru`), and a hardcoded employer keyword list. | `section_agents/scripts/s3_experience_tile.py` + `ExperienceSectionAgent`. Its only reusable asset — resume.md parsing + fuzzy matching — was extracted (de-hardcoded) to `CompanySiteApply/utils/experience_matcher.py` with tests in `CompanySiteApply/tests/test_experience_matcher.py`. |
| `run_full_visual_ai_audit.py` | Linear audit runner duplicating the orchestrator's section loop with the same hardcoded Section 2 answers as above. | `ApplyOrchestrator.run()` + `VisualVerifierSubAgent` (`section_agents/sub_agents/visual_verifier_subagent.py`) |
| `run_jpmc_flawless_flow.py` | Earlier linear Section 1→4 flow, same hardcoded answers, no IPC, no sub-agent isolation. | `ApplyOrchestrator.run()` + `SectionAgentDispatcher.evaluate_and_heal_section()` |
| `visual_ai_auditor.py` (moved from `core/`, 2026-10-13) | Gemini-Vision screenshot arbitration; superseded by deterministic readback + order gates. Moved here because its only callers are the archived runners above. | `VisualVerifierSubAgent` (structured readback, `ORDER_UNVERIFIED` gate) |

**Revival rule:** never copy-paste from these files into live code. If a technique here is needed, extract it as a profile-parameterized helper under `CompanySiteApply/utils/` with a unit test, following the `experience_matcher.py` precedent.

> Structured-layout note (2026-10-14): per-requisition outputs no longer use job-id filename suffixes (`{Name}_Cover_Letter_{jobid}.pdf`). The live contract is fixed names (`<Stem>_Resume.pdf` / `<Stem>_Cover_Letter.pdf`) inside `APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<jobid>/` (+ `resume/`/`cover_letters/` mirrors), resolved profile-agnostically under the Operations root. These archived scripts predate that contract — do not revive their flat/single-file naming.
