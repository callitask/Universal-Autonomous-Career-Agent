# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [DOCUMENTS_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:45:00 +05:30
# Issue / Context: Outdated cover letters were not being removed before attaching new tailored ones.
# Changes Made: Built DocumentsSubAgent encapsulating active document inspection, removal of outdated files,
#               and upload of freshly generated tailored Resumes and Cover Letters.
# Rationale: Guarantees that every requisition receives the exact tailored document package with zero stale file retention.
# Preventative Notes: Always remove stale files before attaching freshly generated documents.
# ==============================================================================

import os
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class DocumentsSubAgent(BaseSectionAgent):
    """
    Sub-Agent for Document Attachments: Resume and Cover Letter.
    Audits currently uploaded documents; if stale/old or missing, surgically removes them
    and uploads the freshly tailored versions.
    """

    @property
    def section_name(self) -> str:
        return "documents"

    @property
    def target_stage(self) -> str:
        return "section_4"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("subagent") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/4" in url or "review" in url.lower() or "more-about-you" in url.lower() or "/apply/section/1" in url
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            attached_files = page.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('.attachment-upload-button__download, .cx-attachment-item, .apply-flow-profile-import-awli__file-name'));
                return els.map(e => e.innerText.trim()).filter(Boolean);
            }''')

            has_resume = any("resume" in f.lower() for f in attached_files)
            has_cover = any("cover" in f.lower() for f in attached_files)

            return {
                "is_valid": has_resume and has_cover,
                "attached_files": attached_files,
                "has_resume": has_resume,
                "has_cover_letter": has_cover
            }
        except Exception as e:
            logger.error(f"[DocumentsSubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            target_jobs = candidate_data.get("target_jobs") or {} if isinstance(candidate_data, dict) else {}

            resume_path = self._resolve_target_file(cand, "resume", candidate_data)
            cover_path = self._resolve_target_file(cand, "cover_letter", candidate_data)

            resume_updated = False
            cover_updated = False

            # -----------------------------------------------------------------
            # 1. RESUME ATTACHMENT
            # -----------------------------------------------------------------
            if resume_path and os.path.exists(resume_path):
                target_res_name = os.path.basename(resume_path)
                curr_res_btn = page.locator(".attachment-upload-button:has-text('Resume') .attachment-upload-button__download, .attachment-upload-button:has-text('RESUME') .attachment-upload-button__download").first
                
                needs_upload = False
                if curr_res_btn.count() == 0:
                    needs_upload = True
                else:
                    curr_name = curr_res_btn.inner_text().strip()
                    # If remove button exists, check if we need to freshen it
                    remove_res = page.locator("button:has-text('Remove Resume'), button:has-text('REMOVE RESUME')").first
                    if remove_res.count() > 0 and remove_res.is_visible():
                        logger.info(f"[DocumentsSubAgent] Refreshing resume to latest tailored: {target_res_name}")
                        remove_res.click()
                        time.sleep(1.0)
                        needs_upload = True

                if needs_upload:
                    res_input = page.locator(".attachment-upload-button--waiting input[type='file'], input[name='attachment-upload'], input[aria-label*='Resume' i]").first
                    if res_input.count() > 0:
                        res_input.set_input_files(resume_path)
                        resume_updated = True
                        time.sleep(1.5)

            # -----------------------------------------------------------------
            # 2. COVER LETTER ATTACHMENT
            # -----------------------------------------------------------------
            if cover_path and os.path.exists(cover_path):
                target_cl_name = os.path.basename(cover_path)
                logger.info(f"[DocumentsSubAgent] Ensuring latest tailored cover letter is attached: {cover_path}")

                remove_cl = page.locator("button:has-text('Remove Cover Letter'), button:has-text('REMOVE COVER LETTER')").first
                if remove_cl.count() > 0 and remove_cl.is_visible():
                    logger.info("[DocumentsSubAgent] Removing old cover letter...")
                    remove_cl.click()
                    time.sleep(1.0)

                # Find revealed file input
                cl_input = page.locator(".attachment-upload-button--waiting input[type='file'], input[name='attachment-upload']").last
                if cl_input.count() > 0:
                    logger.info(f"[DocumentsSubAgent] Uploading fresh tailored cover letter: {cover_path}")
                    cl_input.set_input_files(cover_path)
                    cover_updated = True
                    time.sleep(2.0)

            audit_res = self.audit(page, candidate_data)
            return {
                "success": audit_res.get("is_valid", False),
                "subagent": self.section_name,
                "resume_updated": resume_updated,
                "cover_updated": cover_updated,
                "audit": audit_res
            }
        except Exception as e:
            logger.error(f"[DocumentsSubAgent] Heal error: {e}")
            return {"success": False, "subagent": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False

    def _resolve_target_file(self, cand: Dict[str, Any], doc_type: str, candidate_data: Dict[str, Any]) -> Optional[str]:
        """Resolves target PDF path prioritizing job-specific tailored folders."""
        key_file = f"{doc_type}_path"
        target_path = cand.get(key_file) or cand.get(f"{doc_type}_filename")
        if target_path and os.path.isabs(target_path) and os.path.exists(target_path):
            return target_path

        # 1. Check candidate profile company_site_apply folder and candidate root
        try:
            from CompanySiteApply.utils.config_resolver import resolve_search_roots
            roots = resolve_search_roots(candidate_data)
        except Exception:
            roots = [os.getcwd()]

        for root in roots:
            # Check company_site_apply
            csa_dir = os.path.join(root, "company_site_apply")
            if os.path.exists(csa_dir):
                for fn in os.listdir(csa_dir):
                    if doc_type == "cover_letter" and "cover" in fn.lower() and fn.endswith(".pdf"):
                        return os.path.join(csa_dir, fn)
                    elif doc_type == "resume" and "resume" in fn.lower() and fn.endswith(".pdf"):
                        return os.path.join(csa_dir, fn)

            # Check APPLIED ON COMPANY WEBSITE for latest tailored job directory
            applied_dir = os.path.join(root, "APPLIED ON COMPANY WEBSITE")
            if os.path.exists(applied_dir):
                candidates = []
                for dirpath, _, filenames in os.walk(applied_dir):
                    for fn in filenames:
                        if doc_type == "cover_letter" and ("cover_letter" in fn.lower() or "cover" in fn.lower()) and fn.endswith(".pdf"):
                            full = os.path.join(dirpath, fn)
                            candidates.append((os.path.getmtime(full), full))
                        elif doc_type == "resume" and ("resume" in fn.lower()) and fn.endswith(".pdf"):
                            full = os.path.join(dirpath, fn)
                            candidates.append((os.path.getmtime(full), full))
                if candidates:
                    candidates.sort(key=lambda x: x[0], reverse=True)
                    return candidates[0][1]

            # Check candidate root directory
            for fn in os.listdir(root):
                if doc_type == "cover_letter" and "cover" in fn.lower() and fn.endswith(".pdf"):
                    return os.path.join(root, fn)
                elif doc_type == "resume" and "resume" in fn.lower() and fn.endswith(".pdf"):
                    return os.path.join(root, fn)

        return target_path
