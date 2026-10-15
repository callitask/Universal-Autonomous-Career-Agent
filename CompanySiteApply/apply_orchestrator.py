# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [APPLY_ORCHESTRATOR_INIT]
# Timestamp: 2026-10-09 22:15:00 +05:30
# Issue / Context: LLM agents in new chats were improvising ad-hoc scripts on page 2 instead of executing a unified pipeline.
# Changes Made: Built ApplyOrchestrator to autonomously drive the end-to-end ATS application lifecycle
#               across Section 1 (Profile), Section 2 (Questionnaire), Section 3 (Education & Experience),
#               and Section 4 (Review). Enforces strict human submission gate on Section 4.
# Rationale: Eliminates all ad-hoc script generation. Provides a single, deterministic CLI command for any profile.
# Preventative Notes: ABSOLUTELY NEVER CLICK SUBMIT ON SECTION 4.
# ==============================================================================
# [ENTRY #002]
# Term: [PHASE1_MODAL_FIX + PHASE0_IPC_SESSION_INIT]
# Timestamp: 2026-10-12 19:56:00 +05:30
# Issue / Context: #applyFlowLegalDisclaimer full-page Terms modal blocks form elements when section 1
#                  mini-agents are dispatched. detect_current_section() sees /apply/section/1 URL
#                  correctly but form is invisible under the modal. PreferredLocationSubAgent.heal()
#                  times out on toggle button with offsetWidth:0. Scar entry 2026-10-12.
# Changes Made: Added modal pre-check at top of every while loop iteration (before section dispatch).
#               Detects #applyFlowLegalDisclaimer → clicks AGREE → waits for modal to detach → continue.
#               Also initialises IPC session_id at run() start (Phase 0 integration).
# Rationale: Guarantees form elements are interactable before any section sub-agent runs.
# Preventative Notes: NEVER move the modal check BELOW section detection — must run FIRST every iteration.
#
# [ENTRY #004]
# Term: [DECISION1_SKIP_RETRY + NEW-4_LOGIN_WALL]
# Timestamp: 2026-10-15 +05:30
# Issue / Context: Intentionally skipped steps were retried 3x; expired
#                  sessions looped as unknown sections to MAX_STEPS.
# Changes Made: skip_retry short-circuits the heal loop; _is_login_wall()
#               halts SECTION_BLOCKED/SESSION_EXPIRED_OR_LOGIN_REQUIRED.
# Rationale: Don't retry refusals; don't heal login screens as forms.
# Preventative Notes: Login walls are never form sections.
# ==============================================================================
# [ENTRY #003]
# Term: [SECTION_DETECTION_ORDER_AND_PREVIEW_COLLISION_FIX]
# Timestamp: 2026-10-12 22:08:00 +05:30
# Issue / Context: Oracle HCM URLs containing /jobs/preview/... collided with 'review' in path_only,
#                  causing Section 1 to misclassify as Section 4 Review prematurely.
# Changes Made:
#   1. Prioritized explicit section numbers (/section/1 -> /section/4) before keyword checks.
#   2. Enforced strict boundary / leading slash on '/review' to prevent matching 'preview'.
#   3. Added dynamic fallback extraction of job_id from page.url if omitted in candidate config.
# Rationale: Guarantees deterministic section progression and requisition ID attribution.
# Preventative Notes: Never match naked 'review' substring against full URL paths.
# ==============================================================================

import re
import time
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from CompanySiteApply.ats_arm import ATSArm
from CompanySiteApply.section_agents.section_agent_dispatcher import SectionAgentDispatcher
from CompanySiteApply.ipc.ipc_manager import IPCManager, new_session_id, STATUS_IDLE

logger = logging.getLogger(__name__)


class ApplyOrchestrator:
    """
    Master Autonomous Orchestrator for Company Site Job Applications.
    Coordinates the stage detection, section mini-agent healing, verification,
    and step transitions until Section 4 Review is reached.
    """

    def __init__(self, cdp_url: Optional[str] = None):
        self.arm = ATSArm(cdp_url=cdp_url)
        self.dispatcher = SectionAgentDispatcher()

    def advance(self, page: Any) -> bool:
        """Clicks NEXT / Save and Continue to advance to the next step."""
        try:
            # 1. Direct JS click on visible pagination button, strictly avoiding modal/dialog buttons
            clicked = page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button.apply-flow-pagination__button, button.navigation-button, button'));
                for (const b of btns) {
                    const text = (b.innerText || b.textContent || '').trim().toUpperCase();
                    const isVisible = b.offsetWidth > 0 && b.offsetHeight > 0 && window.getComputedStyle(b).visibility !== 'hidden';
                    if (isVisible && !b.disabled && (text === 'NEXT' || text.includes('SAVE AND CONTINUE') || text === 'CONTINUE')) {
                        if (!b.closest('.app-dialog') && !b.classList.contains('app-dialog__footer-button')) {
                            b.click();
                            return true;
                        }
                    }
                }
                return false;
            }""")

            if not clicked:
                # Fallback to visible pagination button locator with short timeout
                next_btn = page.locator("button.apply-flow-pagination__button:visible").first
                if next_btn.count() > 0 and not next_btn.is_disabled():
                    next_btn.click(timeout=3000)
                    clicked = True

            if clicked:
                time.sleep(2.0)
                # Wait for loading overlay to disappear
                try:
                    page.wait_for_selector(".cx-loading, .oj-busy, .spinner", state="detached", timeout=5000)
                except Exception:
                    pass
                time.sleep(1.0)
                return True
            return False
        except Exception as e:
            logger.error(f"[ApplyOrchestrator] Advance error: {e}")
            return False

    def detect_current_section(self, page: Any) -> str:
        """Determines the active ATS section from URL or DOM structure.

        Rank 5 (2026-10-13): the Oracle SPA can keep .../apply/email in the
        URL while Step 1 is mounted (incident 210765001: 12 iterations stuck
        in the email branch). The on-page stepper is consulted FIRST; the URL
        is the fallback. Non-string probe results (mocks, detached DOM) fall
        through to URL logic.
        """
        url = (getattr(page, "url", "") or "").lower()
        # Sanitize common portal path segments that contain 'experience' (e.g. /candidateexperience/)
        path_only = re.sub(r'/candidateexperience/', '/', url)

        try:
            step_hint = page.evaluate("""() => {
                const active = document.querySelector(
                    '.apply-flow-stepper__step--active, .cx-train-item[aria-current="step"], [aria-current="step"]'
                );
                if (active) return (active.innerText || active.getAttribute('aria-label') || '').trim();
                const h1 = document.querySelector('h1');
                const t = (h1 && h1.innerText) || '';
                const m = t.match(/step\\s*(\\d)\\s*of\\s*4/i);
                return m ? m[1] : '';
            }""")
        except Exception:
            step_hint = ""
        if isinstance(step_hint, str) and step_hint.strip():
            hint = step_hint.strip().lower()
            if hint.startswith("1") or "step 1" in hint or "personal" in hint:
                return "profile"
            if hint.startswith("2") or "step 2" in hint or "question" in hint:
                return "questionnaire"
            if hint.startswith("3") or "step 3" in hint or "timeline" in hint or "experience" in hint:
                return "section_3"
            if hint.startswith("4") or "step 4" in hint or "review" in hint:
                return "review"
            if "email" in hint or "terms" in hint or "consent" in hint:
                return "email"

        # 1. Prioritize unambiguous numerical section paths
        if "/section/1" in path_only or "/apply/section/1" in path_only:
            return "profile"
        elif "/section/2" in path_only or "/apply/section/2" in path_only:
            return "questionnaire"
        elif "/section/3" in path_only or "/apply/section/3" in path_only:
            return "section_3"
        elif "/section/4" in path_only or "/apply/section/4" in path_only:
            return "review"

        # 2. Semantic keywords with strict boundary (avoiding 'preview' false positives)
        if "/apply/review" in path_only or "/review" in path_only or "more-about-you" in path_only:
            return "review"
        elif "timeline" in path_only:
            return "section_3"
        elif "questions" in path_only:
            return "questionnaire"
        elif "personal" in path_only:
            return "profile"
        elif "/apply/email" in path_only or "email" in path_only:
            return "email"
        return "unknown"

    def _capture_section_shot(
        self, page: Any, screenshot_dir: Optional[Path], section: str
    ) -> Optional[str]:
        """Capture per-section visual proof (every section, not just Review).

        Incident 2026-10-12: only Section 4 was screenshotted, so Section 2/3
        failures were invisible in the handover. Every healed section now
        leaves a timestamped artifact.
        """
        if not screenshot_dir:
            return None
        try:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            shot_path = screenshot_dir / f"{section}_audited_{int(time.time())}.png"
            page.screenshot(path=str(shot_path), full_page=True)
            logger.info(f"[ApplyOrchestrator] Section proof captured: {shot_path}")
            return str(shot_path)
        except Exception as e:
            logger.warning(f"[ApplyOrchestrator] Section screenshot failed ({section}): {e}")
            return None

    def _heal_section_with_gate(
        self,
        section_key: str,
        page: Any,
        candidate_data: Dict[str, Any],
        screenshot_dir: Optional[Path],
        proof_key: str,
        section_proofs: Dict[str, str],
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """Heal one section with a hard advance gate (Rank 2, 2026-10-13).

        Incident 210765001: post-audit flagged an unanswered required pill
        question and the orchestrator logged "Retrying..." but advanced
        anyway. A failing section must NEVER be advanced past: retry the
        heal loop, capture proof, and return a BLOCKED verdict instead.
        """
        eval_res: Dict[str, Any] = {"success": False}
        for attempt in range(1, max_attempts + 1):
            eval_res = self.dispatcher.evaluate_and_heal_section(section_key, page, candidate_data)
            if eval_res.get("success", False):
                if attempt > 1:
                    logger.info(f"[ApplyOrchestrator] Section '{section_key}' healed on attempt {attempt}.")
                break
            # Decision 1: intentionally skipped steps (e.g. deferred document
            # upload) must NOT be retried — one pass, then halt loudly.
            if eval_res.get("skip_retry"):
                logger.info(
                    f"[ApplyOrchestrator] Section '{section_key}' reports skip_retry "
                    f"({eval_res.get('blocked_reason')}) — no further attempts."
                )
                break
            logger.warning(
                f"[ApplyOrchestrator] Section '{section_key}' attempt {attempt}/{max_attempts} "
                f"reported anomalies: {eval_res}. Retrying..."
            )
            time.sleep(1.0)

        if eval_res.get("success", False):
            # Last-moment independent sweep: Oracle's rendered error text is
            # ground truth even when every subagent audit passed.
            gate_errors = self._section_has_visible_errors(page)
            if gate_errors:
                logger.warning(
                    f"[ApplyOrchestrator] Section '{section_key}' audits passed but "
                    f"visible errors remain: {gate_errors}"
                )
                eval_res = {
                    "success": False,
                    "section": section_key,
                    "gate_errors": gate_errors,
                    "post_audits": eval_res.get("post_audits", {}),
                }

        shot = self._capture_section_shot(page, screenshot_dir, proof_key)
        if shot:
            section_proofs[proof_key] = shot
        eval_res["attempts"] = attempt
        return eval_res

    def _section_has_visible_errors(self, page: Any) -> List[str]:
        """Independent last-moment error sweep before advancing.

        Subagent audits can miss widgets outside their selectors (incident
        210788242: a late-revealed required combobox). Oracle's own rendered
        error text is ground truth — if it is visible, the section is not done.
        """
        try:
            return page.evaluate("""() => {
                const out = [];
                const body = (document.body && document.body.innerText) || '';
                const req = body.match(/This information is required\\.?/gi) || [];
                req.forEach(() => out.push('This information is required.'));
                const errs = Array.from(document.querySelectorAll(
                    '.cx-message--error, .cx-form-control__error-message, .oj-form-control-error-message, .input-row--error [class*="error"], [aria-invalid="true"]'
                )).filter(el => el.offsetWidth > 0 || el.offsetHeight > 0)
                    .map(el => (el.innerText || '').trim())
                    .filter(t => t && !/saved|all set|successfully/i.test(t));
                return out.concat(errs).slice(0, 10);
            }""") or []
        except Exception:
            return []

    def _write_transcript(
        self,
        screenshot_dir: Optional[Path],
        result: Dict[str, Any],
        visited_stages: Any,
        section_proofs: Dict[str, str],
    ) -> Optional[str]:
        """Persist the run transcript for engineer forensics.

        Every section verdict, gate error, proof path, and visited URL is
        recorded to artifacts/run_transcript_<ts>.json so the next session
        never reconstructs behavior from memory. Best-effort: never fails run.
        """
        try:
            import json as _json
            from CompanySiteApply.utils.runtime_paths import artifacts_dir as _adir

            target = screenshot_dir or _adir()
            target.mkdir(parents=True, exist_ok=True)
            safe_status = str(result.get("status", "unknown")).replace(" ", "_")
            path = target / f"run_transcript_{safe_status}_{int(time.time())}.json"
            payload = {
                "status": result.get("status"),
                "success": result.get("success"),
                "section": result.get("section"),
                "url": result.get("url", result.get("last_url")),
                "eval_result": result.get("eval_result"),
                "audit_result": result.get("audit_result"),
                "blocked_details": result.get("blocked_details"),
                "visited_stages": visited_stages,
                "section_proofs": section_proofs,
                "screenshot_path": result.get("screenshot_path"),
                "submit_clicked": result.get("submit_clicked", False),
            }
            path.write_text(_json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
            logger.info(f"[ApplyOrchestrator] Run transcript saved: {path}")
            return str(path)
        except Exception as e:
            logger.debug(f"[ApplyOrchestrator] Transcript note: {e}")
            return None

    def _is_login_wall(self, page: Any, url: str) -> bool:
        """Detect mid-run login/session-expiry walls (NEW-4).

        Oracle CX drops expired sessions to sign-in / PIN / email-verify
        screens. Healing those as form sections loops to MAX_STEPS — halt.
        """
        try:
            u = (url or "").lower()
            if any(k in u for k in ("login", "signin", "sign-in", "auth",
                                    "verify-email", "pin-code", "challenge")):
                return True
            found = page.evaluate("""() => {
                const t = ((document.body && document.body.innerText) || '').toLowerCase();
                const hasPwd = !!document.querySelector('input[type="password"]');
                const keys = ['sign in to continue', 'session has expired', 'session expired',
                              'please sign in again', 'verify it is you', 'enter verification code'];
                return hasPwd || keys.some(k => t.includes(k));
            }""")
            # Strict identity: MagicMock pages in unit tests return truthy
            # non-bool objects from evaluate() — never treat those as walls.
            return found is True
        except Exception:
            return False

    def _blocked_result(
        self,
        section: str,
        url: str,
        eval_res: Dict[str, Any],
        visited_stages: Any,
        section_proofs: Dict[str, str],
        screenshot_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Terminal verdict for a section that failed its hard gate.

        The orchestrator halts instead of advancing past unhealed required
        fields. The caller (or operator) sees exactly what failed.
        """
        logger.error(f"[ApplyOrchestrator] HALTED on '{section}': hard gate failed after retries.")
        result = {
            "success": False,
            "status": "SECTION_BLOCKED",
            "section": section,
            "url": url,
            "eval_result": eval_res,
            "blocked_details": eval_res.get("post_audits", eval_res),
            "visited_stages": visited_stages,
            "section_proofs": section_proofs,
            "human_gate_active": True,
            "submit_clicked": False,
            "message": (
                f"Section '{section}' failed verification after retries. "
                "Advance blocked — fix flagged questions/fields and re-run."
            ),
        }
        result["transcript_path"] = self._write_transcript(screenshot_dir, result, visited_stages, section_proofs)
        return result

    def run(self, candidate_data: Dict[str, Any], max_steps: int = 10, screenshot_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Executes the autonomous application loop until Section 4 Review is reached and validated.
        STRICTLY HALTS ON SECTION 4 REVIEW BEFORE CLICKING SUBMIT.
        """
        page = self.arm.connect()
        # Initialise IPC session context for this run
        session_id = new_session_id()
        job_id = str(candidate_data.get("job_id") or candidate_data.get("candidate", {}).get("job_id") or "")
        if not job_id and getattr(page, "url", None):
            m_jid = re.search(r'/(?:jobs?/preview/|job/|requisitions?/|preview/)(\d+)', page.url)
            if m_jid:
                job_id = m_jid.group(1)
        profile = str(candidate_data.get("profile") or candidate_data.get("candidate", {}).get("profile_name") or "")
        self._ipc_session_id = session_id
        self._ipc_job_id = job_id
        self._ipc_profile = profile
        # Propagate session to every downstream script via candidate_data.
        # Scripts resolve via get_effective_session_id(candidate_data, explicit).
        # This preserves existing heal(page, candidate_data) signatures (Directive 4 parity).
        try:
            candidate_data["_ipc_session_id"] = session_id
            candidate_data["_ipc_job_id"] = job_id
            candidate_data["_ipc_profile"] = profile
        except Exception:
            pass
        logger.info(f"[ApplyOrchestrator] IPC session: {session_id} | job={job_id} | profile={profile}")

        try:
            step_count = 0
            visited_stages = []
            section_proofs: Dict[str, str] = {}

            while step_count < max_steps:
                step_count += 1

                # ------------------------------------------------------------------
                # MODAL PRE-CHECK (PHASE 1 FIX — runs EVERY iteration before anything)
                # Detects Oracle HCM full-page Terms & Conditions overlay and dismisses it.
                # Scar entry: 2026-10-12 TERMS MODAL BLOCKS SECTION 1 SUB-AGENTS.
                # ------------------------------------------------------------------
                try:
                    modal = page.locator(
                        "#applyFlowLegalDisclaimer, "
                        ".apply-flow-full-page-agreement, "
                        "[class*='legal-disclaimer']:not([style*='display: none'])"
                    )
                    if modal.count() > 0 and modal.first.is_visible():
                        logger.info("[ApplyOrchestrator] ⚠ Full-page Terms modal detected — dismissing before section dispatch.")
                        agree_btn = page.locator(
                            "button:has-text('AGREE'), button:has-text('Agree'), button:has-text('I Agree')"
                        )
                        if agree_btn.count() > 0 and agree_btn.first.is_visible():
                            agree_btn.first.click()
                            time.sleep(1.5)
                            try:
                                page.wait_for_selector(
                                    "#applyFlowLegalDisclaimer, .apply-flow-full-page-agreement",
                                    state="detached",
                                    timeout=6000
                                )
                            except Exception:
                                pass  # Modal may have already disappeared
                        logger.info("[ApplyOrchestrator] Terms modal dismissed. Re-detecting section...")
                        step_count -= 1  # Don't count this as a real step
                        continue  # Re-enter loop to detect section with clean DOM
                except Exception as modal_err:
                    logger.debug(f"[ApplyOrchestrator] Modal check skipped: {modal_err}")

                curr_url = page.url
                # NEW-4: expired session walls are not form sections — halt now.
                if self._is_login_wall(page, curr_url):
                    logger.error("[ApplyOrchestrator] Login/session wall detected — halting.")
                    return self._blocked_result(
                        "login_wall", curr_url,
                        {"success": False, "status": "SECTION_BLOCKED",
                         "blocked_reason": "SESSION_EXPIRED_OR_LOGIN_REQUIRED",
                         "error": "SESSION_EXPIRED_OR_LOGIN_REQUIRED: sign-in or "
                                  "verification screen mid-run. Re-authenticate in "
                                  "the CDP browser and re-run.",
                         "skip_retry": True},
                        visited_stages, section_proofs, screenshot_dir,
                    )
                section = self.detect_current_section(page)
                visited_stages.append((section, curr_url))
                logger.info(f"[ApplyOrchestrator] Step {step_count}: Section='{section}' | URL={curr_url}")

                # -------------------------------------------------------------
                # EMAIL & TERMS STEP
                # -------------------------------------------------------------
                if section == "email":
                    logger.info("[ApplyOrchestrator] Handling Email & Terms entry step...")
                    email_selector = "input[name='primary-email'], input#primary-email-0"
                    email = candidate_data.get("candidate", {}).get("email") or candidate_data.get("email")
                    if email and page.locator(email_selector).count() > 0:
                        page.locator(email_selector).first.fill(email)
                        time.sleep(0.5)
                    cb = page.locator("input#legal-disclaimer-checkbox, input[type='checkbox']").first
                    if cb.count() > 0 and not cb.is_checked():
                        cb.check(force=True)
                        time.sleep(0.5)
                    agree = page.locator("button:has-text('AGREE'), button:has-text('Agree')")
                    if agree.count() > 0 and agree.first.is_visible():
                        agree.first.click()
                        time.sleep(0.5)
                    # Gap 4 (PIN parity with oracle_cloud_finger._fill_pin_step):
                    # if the gate transitioned to OTP/PIN verification, fill a
                    # provided PIN or halt loudly as OTP_PIN_REQUIRED.
                    try:
                        _pin_boxes = page.locator("input[id^='pin-code-']")
                        _pin_n = _pin_boxes.count() if _pin_boxes else 0
                    except Exception:
                        _pin_n = 0
                    if _pin_n == 6:
                        _pin_val = str(candidate_data.get("verification_pin") or "").strip()
                        if _pin_val:
                            try:
                                for _i in range(6):
                                    page.locator(f"#pin-code-{_i+1}").first.fill(_pin_val[_i] if _i < len(_pin_val) else "")
                                time.sleep(0.5)
                            except Exception:
                                pass
                        else:
                            return self._blocked_result(
                                section, curr_url,
                                {"success": False, "status": "SECTION_BLOCKED",
                                 "blocked_reason": "OTP_PIN_REQUIRED",
                                 "error": "ACTION_REQUIRED: OTP/PIN verification required — "
                                          "provide candidate_data['verification_pin'] and re-run.",
                                 "skip_retry": True},
                                visited_stages, section_proofs, screenshot_dir,
                            )
                    # Gate: never advance past an unaccepted email/terms step.
                    try:
                        _email_ok = (
                            page.locator(email_selector).count() == 0
                            or (email and page.locator(email_selector).first.input_value().strip() == email)
                        )
                        _cb_ok = cb.count() == 0 or cb.is_checked()
                    except Exception:
                        _email_ok, _cb_ok = False, False
                    if not (_email_ok and _cb_ok):
                        return self._blocked_result(
                            section, curr_url,
                            {"success": False, "error": "email/terms not accepted", "post_audits": {}},
                            visited_stages, section_proofs, screenshot_dir,
                        )
                    self.advance(page)

                # -------------------------------------------------------------
                # SECTION 4: REVIEW (HUMAN GATE - NEVER SUBMIT)
                # -------------------------------------------------------------
                elif section == "review":
                    logger.info("[ApplyOrchestrator] Arrived at Section 4 Review. Running AI Brain Cognitive Dispatch...")
                    eval_res = self.dispatcher.evaluate_and_heal_section("review", page, candidate_data)
                    audit_res = self.dispatcher.dispatch_audit("review", page, candidate_data)

                    # Capture visual audit screenshot
                    shot_path = None
                    if screenshot_dir:
                        screenshot_dir.mkdir(parents=True, exist_ok=True)
                        shot_path = screenshot_dir / f"section_4_review_ready_{int(time.time())}.png"
                        try:
                            page.screenshot(path=str(shot_path), full_page=True)
                            logger.info(f"[ApplyOrchestrator] Review screenshot saved: {shot_path}")
                        except Exception as e:
                            logger.warning(f"Screenshot failed: {e}")

                    verified = bool(audit_res.get("is_valid", False))
                    result = {
                        "success": verified,
                        "status": "READY_FOR_HUMAN_SUBMISSION" if verified else "REVIEW_BLOCKED",
                        "section": "review",
                        "url": curr_url,
                        "eval_result": eval_res,
                        "audit_result": audit_res,
                        "screenshot_path": str(shot_path) if shot_path else None,
                        "section_proofs": section_proofs,
                        "human_gate_active": True,
                        "submit_clicked": False,
                        "message": (
                            "Section 4 Review is completely verified and ready for human submission. Halted at Human Gate."
                            if verified else
                            "Section 4 Review FAILED verification (see audit_result). "
                            "Not ready — fix flagged items and re-run. Halted at Human Gate."
                        ),
                    }
                    result["transcript_path"] = self._write_transcript(
                        screenshot_dir, result, visited_stages, section_proofs
                    )
                    return result

                # -------------------------------------------------------------
                # SECTION 1: PROFILE
                # -------------------------------------------------------------
                elif section == "profile":
                    logger.info("[ApplyOrchestrator] Arrived at Section 1 Profile. Running AI Brain Cognitive Dispatch...")
                    eval_res = self._heal_section_with_gate(
                        "profile", page, candidate_data, screenshot_dir,
                        "section_1_profile", section_proofs,
                    )
                    if not eval_res.get("success", False):
                        return self._blocked_result(section, curr_url, eval_res, visited_stages, section_proofs, screenshot_dir)
                    self.advance(page)

                # -------------------------------------------------------------
                # SECTION 2: QUESTIONNAIRE
                # -------------------------------------------------------------
                elif section == "questionnaire":
                    logger.info("[ApplyOrchestrator] Arrived at Section 2 Questionnaire. Running AI Brain Cognitive Dispatch...")
                    eval_res = self._heal_section_with_gate(
                        "questionnaire", page, candidate_data, screenshot_dir,
                        "section_2_questionnaire", section_proofs,
                    )
                    if not eval_res.get("success", False):
                        return self._blocked_result(section, curr_url, eval_res, visited_stages, section_proofs, screenshot_dir)
                    self.advance(page)

                # -------------------------------------------------------------
                # SECTION 3: EDUCATION & WORK EXPERIENCE
                # -------------------------------------------------------------
                elif section == "section_3":
                    logger.info("[ApplyOrchestrator] Arrived at Section 3 Education & Experience. Running AI Brain Cognitive Dispatch...")
                    eval_res = self._heal_section_with_gate(
                        "section_3", page, candidate_data, screenshot_dir,
                        "section_3_experience", section_proofs,
                    )
                    if not eval_res.get("success", False):
                        return self._blocked_result(section, curr_url, eval_res, visited_stages, section_proofs, screenshot_dir)
                    self.advance(page)

                else:
                    # Attempt generic auto-heal on page
                    logger.info(f"[ApplyOrchestrator] Unknown section '{section}'. Attempting auto_heal_page...")
                    self.arm.auto_heal_page(candidate_data)
                    time.sleep(1.0)
                    advanced = self.advance(page)
                    if not advanced:
                        logger.warning("[ApplyOrchestrator] Unable to advance from unknown step.")
                        break

                time.sleep(1.5)

            result = {
                "success": False,
                "status": "MAX_STEPS_EXCEEDED",
                "visited_stages": visited_stages,
                "section_proofs": section_proofs,
                "last_url": page.url
            }
            result["transcript_path"] = self._write_transcript(
                screenshot_dir, result, visited_stages, section_proofs
            )
            return result
        finally:
            self.arm.disconnect()
