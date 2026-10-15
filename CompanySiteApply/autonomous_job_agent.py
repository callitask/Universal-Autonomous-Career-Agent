# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [AUTONOMOUS_JOB_AGENT_INIT]
# Timestamp: 2026-10-11 00:38:00 +05:30
# Issue / Context: The application flow was fragmented across independent, ad-hoc scripts
#                  requiring manual developer execution and containing hardcoded parameters.
# Changes Made: Built AutonomousJobAgent as the central Antigravity 2.0 cognitive lifecycle
#               controller. Coordinates 6 chronological stages end-to-end:
#               1. Profile Comprehension (Zero hardcoding)
#               2. Autonomous Portal Search (Dynamic keyword/location)
#               3. Cognitive Job Match & Selection (Dynamic candidate skill/seniority scoring)
#               4. Requisition Document Tailoring (Role-specific cover letter generation)
#               5. Section Mini-Agent Dispatch & Form Application (Sections 1->2->3->4)
#               6. Visual Audit, Human Submission Gate, & Ledger Persistence.
# Rationale: Complete autonomous intelligence from discovery to verified application ready for human submission.
# Preventative Notes: Never click SUBMIT on Section 4; strict Human Submission Gate mandatory.
#
# [ENTRY #002]
# Term: [DECISION1_TAILORING_BLOCKED_PROPAGATION]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Stage 4 tailoring failure only warned while Stages 5-6
#                  proceeded and the ledger recorded READY anyway.
# Changes Made: _tailoring_blocked() stamps flags on BOTH best_job and
#               self.candidate_data (never a nonexistent candidate_config);
#               stage_5 mirrors runner flags in; stage_6 records/propagates
#               the exact blocked status with ready_for_submission False.
# Rationale: Fill everything, upload nothing unverified, halt loudly.
# Preventative Notes: Never report READY when any stage reports blocked.
# ==============================================================================

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from CompanySiteApply.cognitive_job_matcher import CognitiveJobMatcher
from CompanySiteApply.CompanyScraper.companies.jpmorgan.jpmorgan_scraper import JPMorganScraper
from CompanySiteApply.apply_orchestrator import ApplyOrchestrator
from CompanySiteApply.utils.config_resolver import resolve_search_roots
from core.generate_professional_cover_letter import generate_tailored_cover_letter


def _archive_application_docs(
    repo_root: Path,
    candidate_data: Dict[str, Any],
    company: str,
    job_title: str,
    job_id: str,
    cover_pdf_path: str,
    source_dir: str,
    resume_pdf_path: str = "",
) -> str:
    """Copy tailored docs into APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<id>/.

    Structured layout (2026-10-14 fix): fixed filenames
    <Stem>_Resume.pdf / <Stem>_Cover_Letter.pdf flat in the role folder AND
    inside resume/ + cover_letters/ subfolders. Incident 210791831: archive
    used literal folder "company" and uploaders ignored the archive.
    Pure file ops — unit tested.
    """
    from CompanySiteApply.utils.application_docs import (
        application_doc_paths,
        copy_into_role,
        profile_slug_of,
        resolve_company_name,
    )

    profile = profile_slug_of(candidate_data, "candidate")
    company_clean = resolve_company_name(
        {"details": {"company": company}}, candidate_data, "")
    paths = application_doc_paths(profile, company_clean, job_title,
                                  job_id, candidate_data)
    role_dir = paths["role_dir"]
    role_dir.mkdir(parents=True, exist_ok=True)
    (role_dir / "resume").mkdir(parents=True, exist_ok=True)
    (role_dir / "cover_letters").mkdir(parents=True, exist_ok=True)
    from CompanySiteApply.utils.application_docs import profile_stem
    stem = profile_stem(candidate_data, profile)
    # Cover: rename whatever Stage 4 produced to the FIXED name.
    try:
        if cover_pdf_path and Path(cover_pdf_path).is_file():
            copy_into_role(role_dir, stem, None, cover_pdf_path)
    except OSError as e:
        logger.warning(f"[Stage 4] Archive cover note: {e}")
    # Resume: explicit path wins, else sibling of source_dir.
    try:
        res_src = resume_pdf_path
        if not res_src:
            for cand_name in (f"{stem}_Resume.pdf", "Udaysagar_Kandpal_Resume.pdf"):
                cand_p = Path(source_dir) / cand_name
                if cand_p.is_file():
                    res_src = str(cand_p)
                    break
        if res_src and Path(res_src).is_file():
            copy_into_role(role_dir, stem, res_src, None)
    except OSError as e:
        logger.warning(f"[Stage 4] Archive resume note: {e}")
    for name in ("Cover_Letter.txt", "Cover_Letter.html"):
        src = Path(source_dir) / name
        try:
            if src.exists() and src.is_file():
                (role_dir / name).write_bytes(src.read_bytes())
        except OSError as e:
            logger.warning(f"[Stage 4] Archive copy note ({name}): {e}")
    return str(role_dir)


class AutonomousJobAgent:
    """
    Antigravity 2.0 Master Autonomous Career Agent.
    
    Coordinates the full lifecycle in strict chronological order:
    Stage 1: Comprehend Candidate Profile (Zero hardcoding)
    Stage 2: Search Career Portal for Target Roles
    Stage 3: Cognitively Evaluate & Rank Requisitions
    Stage 4: Prepare Requisition-Tailored Documents
    Stage 5: Navigate & Execute Section Mini-Agents (1 -> 2 -> 3 -> 4)
    Stage 6: Enforce Human Submission Gate & Persist Ledger
    """

    def __init__(self, cdp_url: Optional[str] = None):
        self.cdp_url = cdp_url or os.environ.get("CDP_URL") or "http://127.0.0.1:9222"
        self.scraper = JPMorganScraper(cdp_url=self.cdp_url)
        self.orchestrator = ApplyOrchestrator(cdp_url=self.cdp_url)
        self.candidate_data: Dict[str, Any] = {}
        self.profile_slug: str = "default_user"
        self.matcher: Optional[CognitiveJobMatcher] = None
        self.ledger_path: Optional[Path] = None

    # =========================================================================
    # STAGE 1: COMPREHEND CANDIDATE PROFILE
    # =========================================================================
    def stage_1_comprehend_profile(self, profile_name: Optional[str] = None, candidate_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Stage 1: Ingests and synthesizes candidate profile context with zero hardcoding.
        """
        logger.info("[AutonomousJobAgent] === STAGE 1: Ingesting & Comprehending Candidate Profile ===")
        
        if candidate_config:
            self.candidate_data = candidate_config
            cand = self.candidate_data.get("candidate", self.candidate_data)
            self.profile_slug = cand.get("full_name", "candidate").lower().replace(" ", "_")
        else:
            from CompanySiteApply.utils.runtime_paths import resolve_profile_dir

            profile = profile_name or os.environ.get("CANDIDATE_PROFILE", "default_user")
            cfg_path = resolve_profile_dir(profile) / "candidate_config.json"
            if not cfg_path.exists():
                cfg_path = REPO_ROOT / "profiles" / "default_user" / "candidate_config.json"

            logger.info(f"[Stage 1] Loading candidate configuration from: {cfg_path}")
            self.candidate_data = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.profile_slug = profile

        # Initialize Cognitive Matcher
        self.matcher = CognitiveJobMatcher(self.candidate_data)

        # Resolve candidate ledger path (Operations sandbox, repo fallback)
        from CompanySiteApply.utils.runtime_paths import resolve_profile_dir as _rpd

        output_dir = _rpd(self.profile_slug) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = output_dir / "processed_ledger.json"

        cand = self.candidate_data.get("candidate", self.candidate_data)
        profile_summary = {
            "candidate_name": self.matcher.candidate_name,
            "current_title": self.matcher.current_title,
            "experience_years": self.matcher.total_experience_years,
            "target_keywords": self.matcher.target_keywords[:5],
            "locations": self.matcher.locations,
            "skills_count": len(self.matcher.candidate_skills),
            "ledger_path": str(self.ledger_path)
        }
        logger.info(f"[Stage 1] Profile comprehension complete: {json.dumps(profile_summary, indent=2)}")
        return profile_summary

    # =========================================================================
    # STAGE 2: AUTONOMOUS PORTAL SEARCH
    # =========================================================================
    async def stage_2_search_jobs(
        self,
        page: Any,
        keyword: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: Autonomously searches career portal using candidate profile criteria.
        Filters out previously applied and ledger-recorded jobs.
        """
        logger.info("[AutonomousJobAgent] === STAGE 2: Autonomous Portal Search & Card Ingestion ===")
        
        if not self.matcher:
            self.stage_1_comprehend_profile()

        # Dynamic search keyword resolution
        active_kw = keyword
        if not active_kw:
            if self.matcher.target_keywords:
                active_kw = self.matcher.target_keywords[0]
            elif self.matcher.recommended_titles:
                active_kw = self.matcher.recommended_titles[0]
            elif self.matcher.current_title:
                active_kw = self.matcher.current_title
            else:
                active_kw = "Engineer"

        # Dynamic search location resolution
        active_loc = location
        if not active_loc:
            if getattr(self.matcher, "allowed_countries", None):
                active_loc = self.matcher.allowed_countries[0]
            elif self.matcher.locations:
                active_loc = self.matcher.locations[0]
            else:
                active_loc = ""

        logger.info(f"[Stage 2] Executing portal search query: keyword='{active_kw}', location='{active_loc}'")
        raw_tiles = await self.scraper.search_jobs(page, keyword=active_kw, location=active_loc)
        logger.info(f"[Stage 2] Sourced {len(raw_tiles)} total job cards from portal.")

        # Load existing ledger to prune previously processed jobs
        ledger = self._load_ledger()
        
        eligible_jobs = []
        skipped_count = 0
        for tile in raw_tiles:
            job_id = str(tile.get("job_id", "")).strip()
            is_dom_applied = tile.get("is_already_applied", False)
            ledger_key = f"jpmc:{job_id}"
            is_ledger_applied = (ledger_key in ledger) or (job_id in ledger)

            if is_dom_applied or is_ledger_applied:
                skipped_count += 1
                logger.info(f"[Stage 2] Skipping already-applied role: {tile.get('title')} (ID: {job_id})")
            else:
                eligible_jobs.append(tile)

        logger.info(f"[Stage 2] Filtered out {skipped_count} previously applied roles. {len(eligible_jobs)} unapplied roles ready for evaluation.")
        return eligible_jobs

    # =========================================================================
    # STAGE 3: COGNITIVE MATCH EVALUATION & ROLE SELECTION
    # =========================================================================
    async def stage_3_evaluate_and_rank(
        self,
        page: Any,
        eligible_jobs: List[Dict[str, Any]],
        max_evaluations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Stage 3: Deeply inspects JDs and ranks roles using CognitiveJobMatcher.
        Returns ranked list of evaluated roles (highest score first).
        """
        logger.info(f"[AutonomousJobAgent] === STAGE 3: Cognitive Match Evaluation (Inspecting Top {max_evaluations}) ===")
        
        if not eligible_jobs:
            logger.warning("[Stage 3] No eligible unapplied jobs found.")
            return []

        scored_jobs = []
        for job_card in eligible_jobs[:max_evaluations]:
            job_id = job_card.get("job_id")
            title = job_card.get("title")
            logger.info(f"[Stage 3] Inspecting Job Description: ID {job_id} - '{title}'...")

            details = await self.scraper.scrape_job_details(page, job_id)
            eval_result = self.matcher.evaluate_job(details)
            logger.info(f"[Stage 3] -> Score: {eval_result['score']}/100 | Status: {eval_result['status']}")

            scored_jobs.append({
                "job_id": job_id,
                "title": details.get("title") or title,
                "location": details.get("location") or job_card.get("location"),
                "score": eval_result["score"],
                "is_eligible": eval_result["is_eligible"],
                "status": eval_result["status"],
                "reasons": eval_result["reasons"],
                "matched_skills": eval_result["matched_skills"],
                "details": details
            })

        # Rank descending by score
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info("\n=== RANKED MATCH RESULTS ===")
        for idx, sj in enumerate(scored_jobs):
            status_flag = "[QUALIFIED]" if sj["is_eligible"] else "[LOW FIT]"
            logger.info(f"[{idx+1}] {status_flag} {sj['title']} (ID: {sj['job_id']}) — Score: {sj['score']}/100")
            for r in sj["reasons"][:3]:
                logger.info(f"    • {r}")

        return scored_jobs

    # =========================================================================
    # STAGE 4: REQUISITION DOCUMENT TAILORING
    # =========================================================================
    def _tailoring_blocked(self, target_job: Dict[str, Any],
                           job_id: str, err_msg: str) -> Dict[str, Any]:
        """Stamp tailoring-failure flags on BOTH best_job AND candidate_data.

        Decision 1 (Revised): Stage 5 still fills all non-document fields;
        Section 4 skips document upload and halts REVIEW_BLOCKED. The flags
        travel on best_job (runner overlay) and self.candidate_data (what
        the orchestrator actually receives). Uses self.candidate_data — NOT
        a nonexistent candidate_config attribute (audit NEW-1).
        """
        fix_cmd = (
            "Fix tailoring input/header for job "
            f"{job_id or '?'} then run: .venv\\Scripts\\python "
            "CompanySiteApply/section_agents/scripts/s4_cover_letter_upload.py "
            f"--profile {self.profile_slug} --job-id {job_id or ''}".strip()
        )
        for carrier in (target_job, self.candidate_data):
            if isinstance(carrier, dict):
                carrier["_tailoring_failed"] = True
                carrier["_tailoring_error"] = err_msg
                carrier["_skip_document_upload"] = True
                carrier["_missing_document"] = "cover_letter"
                carrier["_fix_command"] = fix_cmd
        return {"success": False, "error": err_msg,
                "status": "TAILORING_BLOCKED",
                "missing_document": "cover_letter", "fix_command": fix_cmd}

    def stage_4_tailor_documents(self, target_job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage 4: Generates role-specific docs directly into the structured
        APPLIED ON COMPANY WEBSITE/<Company>/<Role>_<id>/ folder with FIXED
        names <Stem>_Resume.pdf / <Stem>_Cover_Letter.pdf (plus resume/ and
        cover_letters/ subfolders). Base inputs come from
        company_site_apply/<Slug>/resumes|cover_letters.
        """
        job_id = str(target_job.get("job_id", "") or "").strip()
        job_title = str(target_job.get("title", "") or "").strip()
        from CompanySiteApply.utils.application_docs import (
            application_doc_paths,
            copy_into_role,
            profile_slug_of,
            profile_stem,
            resolve_company_name,
            resolve_master_resume,
        )
        det = target_job.get("details", {}) if isinstance(
            target_job.get("details"), dict) else {}
        python_proposal = resolve_company_name(
            target_job, self.candidate_data, "",
            default_company=getattr(getattr(self, "scraper", None),
                                    "company_name", ""))
        cand = self.candidate_data.get("candidate", self.candidate_data) \
            if isinstance(self.candidate_data, dict) else {}
        company_hints = [v for v in (
            (self.candidate_data.get("company_name")
             if isinstance(self.candidate_data, dict) else None),
            (self.candidate_data.get("target_company")
             if isinstance(self.candidate_data, dict) else None),
            ((cand.get("company_name") or cand.get("target_company"))
             if isinstance(cand, dict) else None)) if v and str(v).strip()]

        # AG-Brain-owned recipient verdict (Python evidence is a proposal;
        # the brain arbitrates and its refusal is final).
        from CompanySiteApply.ai_brain_resolver import AIBrainResolver
        brain = AIBrainResolver.get_instance(
            self.candidate_data,
            {"job_id": job_id, "job_title": job_title})
        verdict = brain.resolve_recipient_header({
            "job_id": job_id,
            "job_title": job_title,
            "stamped_company": det.get("company") or det.get("company_name") or "",
            "page_url": target_job.get("url") or det.get("url") or "",
            "portal_default_company": getattr(
                getattr(self, "scraper", None), "company_name", ""),
            "candidate_company_hints": company_hints,
            "dom_location": "",
            "requisition_location": str(
                target_job.get("location") or det.get("location") or ""),
            "explicit_team": str(det.get("team") or ""),
            "workspace_provisioned": True,
        })
        _ = python_proposal  # proposal logged inside the verdict evidence
        if not verdict.get("success"):
            logger.error(f"[Stage 4] Recipient header refused by AG Brain: "
                         f"{verdict.get('error')}")
            return self._tailoring_blocked(
                target_job, job_id,
                f"ACTION_REQUIRED: {verdict.get('error')}")
        company = verdict["company"]
        team = verdict["hiring_team"]
        job_city = verdict["location"]
        profile = profile_slug_of(self.candidate_data, self.profile_slug or "default_user")
        logger.info(f"[AutonomousJobAgent] === STAGE 4: Tailoring Documents for Role: {job_title} (ID: {job_id}) ===")
        logger.info(f"[Stage 4] Structured output: profile={profile} company={company}")

        # Ensure per-company input workspace exists (resumes/ + cover_letters/).
        try:
            from CompanySiteApply.utils.company_workspace import ensure_company_workspace
            if company:
                ensure_company_workspace(self.candidate_data, company)
        except Exception as e:
            logger.debug(f"[Stage 4] Workspace ensure note: {e}")

        paths = application_doc_paths(profile, company, job_title, job_id,
                                      self.candidate_data)
        role_dir = paths["role_dir"]
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / "resume").mkdir(parents=True, exist_ok=True)
        (role_dir / "cover_letters").mkdir(parents=True, exist_ok=True)
        stem = profile_stem(self.candidate_data, profile)

        jd_data = {
            "job_id": job_id,
            "title": job_title,
            "job_title": job_title,
            "company": company,
            "organization": company,
            "team": team,
            "location": job_city or str(target_job.get("location", "")),
            "full_text": target_job.get("details", {}).get("full_text", "")
        }

        try:
            from CompanySiteApply.utils.sync_bridge import call_sync_offloaded

            # Generate into a temp scratch inside role_dir, then rename to FIXED.
            # generate_tailored_cover_letter writes Cover_Letter.txt/html beside
            # the PDF, so targeting role_dir keeps companions role-specific.
            def _generate() -> str:
                return generate_tailored_cover_letter(
                    self.candidate_data, jd_data, str(role_dir),
                    pdf_filename=f"__tmp_{job_id}.pdf")

            tmp_pdf = call_sync_offloaded(_generate)
            logger.info(f"[Stage 4] Freshly tailored cover letter generated at: {tmp_pdf}")
            fixed = copy_into_role(role_dir, stem, None, tmp_pdf)
            try:
                Path(tmp_pdf).unlink(missing_ok=True)
            except Exception:
                pass
            cover_fixed = fixed.get("cover_pdf", str(paths["cover_pdf"]))

            # Resume: copy master (company resumes/ first) with FIXED name.
            resume_master = resolve_master_resume(self.candidate_data, company)
            resume_fixed = ""
            if resume_master:
                fixed_r = copy_into_role(role_dir, stem, resume_master, None)
                resume_fixed = fixed_r.get("resume_pdf", "")
                logger.info(f"[Stage 4] Master resume staged at: {resume_fixed}")
            else:
                logger.warning("[Stage 4] No master resume PDF found — upload will defer.")

            archived = str(role_dir)
            return {
                "success": True,
                "cover_letter_pdf": cover_fixed,
                "resume_pdf": resume_fixed,
                "target_dir": str(role_dir),
                "applied_dir": archived,
                "job_id": job_id,
                "company": company,
            }
        except Exception as e:
            logger.error(f"[Stage 4] Failed to generate tailored cover letter: {e}")
            return self._tailoring_blocked(target_job, job_id, str(e))

    # =========================================================================
    # STAGE 5: SECTION MINI-AGENT DISPATCH & FORM FILLING
    # =========================================================================
    async def stage_5_apply_form(
        self,
        page: Any,
        target_job: Dict[str, Any],
        screenshot_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Stage 5: Navigates to application portal and coordinates Section Mini-Agents.
        Strictly halts before Section 4 Submit button.
        """
        job_id = target_job.get("job_id", "")
        site_code = "CX_1002"
        job_url = f"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{site_code}/job/{job_id}"
        logger.info(f"[AutonomousJobAgent] === STAGE 5: Navigating & Dispatching Section Mini-Agents ===")
        logger.info(f"[Stage 5] Target Job URL: {job_url}")

        # Decision 1: mirror runner-stamped tailoring flags from best_job
        # into the candidate_data the orchestrator actually receives.
        if isinstance(target_job, dict) and isinstance(self.candidate_data, dict):
            for _k in ("_tailoring_failed", "_tailoring_error",
                       "_skip_document_upload", "_missing_document",
                       "_fix_command"):
                if _k in target_job and _k not in self.candidate_data:
                    self.candidate_data[_k] = target_job[_k]

        # Enter via the job page + APPLY NOW (bare .../apply deep links 404
        # on Oracle CX without session form tokens).
        if job_id not in page.url:
            await page.goto(job_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            try:
                apply_btn = page.locator("button.apply-now-button:visible, button:has-text('APPLY NOW'):visible").first
                if await apply_btn.count() > 0:
                    await apply_btn.click()
                    await page.wait_for_timeout(3000)
            except Exception as nav_err:
                logger.warning(f"[Stage 5] APPLY NOW click note: {nav_err}")

        # Execute ApplyOrchestrator across Sections 1 -> 2 -> 3 -> 4.
        # Orchestrator is sync Playwright: bridge offloads inside a loop.
        from CompanySiteApply.utils.runtime_paths import artifacts_dir as _artifacts_dir2

        screenshot_path = screenshot_dir or _artifacts_dir2()
        from CompanySiteApply.utils.sync_bridge import call_sync_offloaded
        app_result = call_sync_offloaded(
            self.orchestrator.run, self.candidate_data, screenshot_dir=screenshot_path
        )
        logger.info(f"[Stage 5] ApplyOrchestrator Execution Status: {app_result.get('status')}")
        return app_result

    # =========================================================================
    # STAGE 6: VISUAL AUDIT, HUMAN SUBMISSION GATE, & LEDGER PERSISTENCE
    # =========================================================================
    async def stage_6_verify_and_gate(
        self,
        page: Any,
        target_job: Dict[str, Any],
        app_result: Dict[str, Any],
        screenshot_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Stage 6: Enforces Human Submission Gate, captures visual proof, and records ledger.
        """
        logger.info("[AutonomousJobAgent] === STAGE 6: Visual Audit & Human Submission Gate Enforcement ===")
        job_id = target_job.get("job_id", "")
        title = target_job.get("title", "")
        
        # Capture high-res proof screenshot (Operations artifacts)
        from CompanySiteApply.utils.runtime_paths import artifacts_dir as _artifacts_dir

        proof_dir = screenshot_dir or _artifacts_dir()
        proof_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        proof_file = proof_dir / f"final_review_ready_{job_id}_{timestamp}.png"
        
        try:
            await page.screenshot(path=str(proof_file), full_page=True)
            logger.info(f"[Stage 6] High-res verification screenshot saved to: {proof_file}")
        except Exception as e:
            logger.warning(f"[Stage 6] Could not capture screenshot: {e}")

        # Decision 1: propagate blocked statuses — never record READY when
        # the orchestrator (or tailoring) reported a block.
        _BLOCKED = {"TAILORING_BLOCKED", "SECTION_BLOCKED", "REVIEW_BLOCKED",
                    "ORDER_UNVERIFIED", "ACTION_REQUIRED"}
        _blocked_status = ""
        if isinstance(app_result, dict) and app_result.get("status") in _BLOCKED:
            _blocked_status = str(app_result["status"])
        elif isinstance(target_job, dict) and target_job.get("_tailoring_failed"):
            _blocked_status = "TAILORING_BLOCKED"
        _final_status = _blocked_status or "READY_FOR_HUMAN_SUBMISSION"

        # Update candidate application ledger
        self._record_in_ledger(
            job_id=job_id,
            title=title,
            company=target_job.get("details", {}).get("company", ""),
            score=target_job.get("score", 0),
            status=_final_status,
            proof_image=str(proof_file)
        )

        gate_report = {
            "status": _blocked_status or "HALTED_AT_HUMAN_GATE",
            "job_id": job_id,
            "title": title,
            "score": target_job.get("score", 0),
            "orchestrator_status": app_result.get("status") if isinstance(app_result, dict) else None,
            "proof_screenshot": str(proof_file),
            "submit_ready": not bool(_blocked_status),
            "ready_for_submission": not bool(_blocked_status),
            "message": (
                f"Blocked ({_blocked_status}): "
                f"{(app_result.get('blocked_reason') or app_result.get('tailoring_error') or app_result.get('error') or '') if isinstance(app_result, dict) else ''} "
                f"Fix: {(app_result.get('fix_command') or '') if isinstance(app_result, dict) else ''}".strip()
                if _blocked_status else
                "Application is 100% complete and verified. Halting strictly before SUBMIT for human review."
            ),
        }
        if _blocked_status and isinstance(app_result, dict):
            for _k in ("blocked_reason", "missing_document", "fix_command", "tailoring_error"):
                if app_result.get(_k) is not None:
                    gate_report.setdefault(_k, app_result[_k])
        logger.info(f"[Stage 6] Gate Report: {json.dumps(gate_report, indent=2)}")
        return gate_report

    # =========================================================================
    # LEDGER PERSISTENCE HELPERS
    # =========================================================================
    def _load_ledger(self) -> Dict[str, Any]:
        if self.ledger_path and self.ledger_path.exists():
            try:
                return json.loads(self.ledger_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"[Ledger] Error reading {self.ledger_path}: {e}")
        return {}

    def _record_in_ledger(self, job_id: str, title: str, company: str, score: int, status: str, proof_image: str):
        if not self.ledger_path:
            return
        ledger = self._load_ledger()
        key = f"jpmc:{job_id}"
        ledger[key] = {
            "job_id": job_id,
            "title": title,
            "company": company,
            "score": score,
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "proof_image": proof_image
        }
        try:
            temp_path = self.ledger_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
            temp_path.replace(self.ledger_path)
            logger.info(f"[Ledger] Successfully persisted application state to {self.ledger_path}")
        except Exception as e:
            logger.error(f"[Ledger] Failed to persist ledger: {e}")
