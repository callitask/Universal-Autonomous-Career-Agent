# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [TECHNICAL_COMPETENCY_SUBAGENT_INIT]
# Timestamp: 2026-10-09 22:43:30 +05:30
# Issue / Context: Isolating competency and experience bracket radio pills into a dedicated mini-agent.
# Changes Made: Built TechnicalCompetencySubAgent encapsulating mathematical experience tier resolution,
#               domain area scoring, specialization matching, and platform proficiency.
# Rationale: Guarantees zero hardcoded domain strings and eliminates interference with dropdown selectors.
# Preventative Notes: Never hardcode years of experience, skill names, or proficiency levels.
# ==============================================================================

import re
import time
import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent

logger = logging.getLogger(__name__)


class TechnicalCompetencySubAgent(BaseSectionAgent):
    """
    Sub-Agent for Page 2 Technical Competency Pills: Experience Tiers, Primary Domain,
    Specialization, and Tool/Cloud Proficiency ratings.
    """

    @property
    def section_name(self) -> str:
        return "technical_competency"

    @property
    def target_stage(self) -> str:
        return "section_2"

    def can_handle(self, page: Any, context: Optional[Dict[str, Any]] = None) -> bool:
        if context and context.get("subagent") == self.section_name:
            return True
        try:
            url = getattr(page, "url", "")
            return "/apply/section/2" in url or "questions" in url.lower()
        except Exception:
            return False

    def audit(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            unanswered = page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('.input-row, .app-form-item, .apply-flow-question-block, [class*="question-block"]'));
                const missing = [];
                for (const r of rows) {
                    if (r.offsetWidth === 0 && r.offsetHeight === 0) continue;
                    const btns = Array.from(r.querySelectorAll('button[role="radio"], button.cx-select-pill-section'));
                    // Look for competency questions (more than 2 pills, or specific keywords)
                    if (btns.length <= 2 || btns.length > 15) continue;
                    const hasSelected = btns.some(b => b.className.includes('selected') || b.getAttribute('aria-checked') === 'true' || b.getAttribute('aria-pressed') === 'true');
                    if (!hasSelected) {
                        const title = r.querySelector('legend, label, .cx-form-label, p, h3, h4')?.innerText.trim() || "Competency Question";
                        missing.push(title);
                    }
                }
                return missing;
            }''')

            return {
                "is_valid": len(unanswered) == 0,
                "unanswered_competency_questions": unanswered
            }
        except Exception as e:
            logger.error(f"[TechnicalCompetencySubAgent] Audit error: {e}")
            return {"is_valid": False, "error": str(e)}

    def heal(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
            total_exp = float(cand.get("total_experience_years") or 0.0)
            healed_count = 0

            questions = page.locator(".input-row, .app-form-item, .apply-flow-question-block, [class*='question-block']").all()
            for q in questions:
                if not q.is_visible():
                    continue
                pills = q.locator("button.cx-select-pill-section, button[role='radio']").all()
                if len(pills) <= 2 or len(pills) > 15:
                    continue

                has_selected = any("selected" in (p.get_attribute("class") or "") or p.get_attribute("aria-checked") == "true" for p in pills)
                if has_selected:
                    continue

                label_el = q.locator("legend, label, .cx-form-label, p, h3, h4").first
                q_text = label_el.inner_text().strip().lower() if label_el.count() > 0 else q.inner_text().strip().lower()

                # 1. Experience tiers
                if "years of work experience" in q_text or "experience you have" in q_text or "relevant work experience" in q_text:
                    target_pill = self._resolve_experience_tier(total_exp, pills)
                    if target_pill:
                        target_pill.click()
                        healed_count += 1
                        time.sleep(0.3)

                # 2. Tool / Cloud Proficiency
                elif "proficiency" in q_text:
                    target_pill = self._resolve_proficiency(q_text, pills, candidate_data)
                    if target_pill:
                        target_pill.click()
                        healed_count += 1
                        time.sleep(0.3)

                # 3. Domain or Specialization
                elif any(k in q_text for k in ["primary area", "area of expertise", "engineering focus", "technical area", "specialization"]):
                    target_pill = self._resolve_domain_or_specialization(q_text, pills, candidate_data)
                    if target_pill:
                        target_pill.click()
                        healed_count += 1
                        time.sleep(0.3)

            verified = self.verify(page, candidate_data)
            return {
                "success": verified,
                "subagent": self.section_name,
                "healed_count": healed_count,
                "verified": verified
            }
        except Exception as e:
            logger.error(f"[TechnicalCompetencySubAgent] Heal error: {e}")
            return {"success": False, "subagent": self.section_name, "error": str(e)}

    def verify(self, page: Any, candidate_data: Dict[str, Any]) -> bool:
        try:
            res = self.audit(page, candidate_data)
            return res.get("is_valid", False)
        except Exception:
            return False

    def _resolve_experience_tier(self, total_exp: float, pill_elements: List[Any]) -> Optional[Any]:
        best_pill = None
        highest_matched_low = -1.0

        for pill in pill_elements:
            txt = pill.inner_text().strip().lower()
            if not txt:
                continue

            low = 0.0
            high = 999.0
            is_range = False

            range_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)', txt)
            if range_match:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                is_range = True
            elif re.search(r'(?:at least|more than|above|\+)\s*(\d+(?:\.\d+)?)', txt) or re.search(r'(\d+(?:\.\d+)?)\s*\+', txt):
                m = re.search(r'(\d+(?:\.\d+)?)', txt)
                low = float(m.group(1)) if m else 0.0
                high = 999.0
            elif re.search(r'(?:less than|under|<)\s*(\d+(?:\.\d+)?)', txt):
                m = re.search(r'(\d+(?:\.\d+)?)', txt)
                low = 0.0
                high = float(m.group(1)) if m else 1.0
            else:
                nums = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', txt)]
                if nums:
                    low = nums[0]
                    high = nums[0]

            if low <= total_exp:
                if high == 999.0 or total_exp <= high or (not is_range and total_exp >= low):
                    if low > highest_matched_low:
                        highest_matched_low = low
                        best_pill = pill

        return best_pill

    def _resolve_proficiency(self, q_text: str, pill_elements: List[Any], candidate_data: Dict[str, Any]) -> Optional[Any]:
        cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
        ats_answers = candidate_data.get("ats_answers") or {} if isinstance(candidate_data, dict) else {}

        q_text_clean = q_text.lower()

        # 1. Match from ats_answers
        for k, v in ats_answers.items():
            if isinstance(v, str) and k.lower() in q_text_clean:
                val = str(v).lower()
                for p in pill_elements:
                    if val in p.inner_text().strip().lower() or p.inner_text().strip().lower() in val:
                        return p

        # 2. Check skill_years_experience (in ats_answers or cand)
        skills_exp = ats_answers.get("skill_years_experience") or cand.get("skill_years_experience") or {}
        found_skill = False
        target_years = 0.0
        for skill_name, years in skills_exp.items():
            if skill_name.lower() in q_text_clean:
                found_skill = True
                target_years = float(years)
                break

        if found_skill:
            if target_years >= 5.0:
                target_word = "advanced"
            elif target_years >= 2.0:
                target_word = "intermediate"
            else:
                target_word = "beginner"
            for p in pill_elements:
                p_txt = p.inner_text().strip().lower()
                if target_word in p_txt or ("beginner" in target_word and "fundamental" in p_txt):
                    return p
        else:
            # Skill is absent / not in candidate profile
            for p in pill_elements:
                p_txt = p.inner_text().strip().lower()
                if "beginner" in p_txt or "fundamental" in p_txt or "less than" in p_txt or "0" in p_txt:
                    return p

        # Fallback to beginner/fundamental or first pill
        for p in pill_elements:
            if "beginner" in p.inner_text().strip().lower() or "fundamental" in p.inner_text().strip().lower():
                return p
        return pill_elements[0] if pill_elements else None

    def _resolve_domain_or_specialization(self, q_text: str, pill_elements: List[Any], candidate_data: Dict[str, Any]) -> Optional[Any]:
        cand = candidate_data.get("candidate", candidate_data) if isinstance(candidate_data, dict) else {}
        ats_answers = candidate_data.get("ats_answers") or {} if isinstance(candidate_data, dict) else {}

        # 1. Check ats_answers
        for k, v in ats_answers.items():
            if isinstance(v, str) and k.lower() in q_text:
                val = str(v).lower()
                for p in pill_elements:
                    if val in p.inner_text().strip().lower() or p.inner_text().strip().lower() in val:
                        return p

        # 2. Tokenize and weight candidate profile and taxonomy skills
        weighted_terms: Dict[str, int] = {}
        tax = candidate_data.get("taxonomy_skills") or {}
        if isinstance(tax, dict):
            for cat, s_list in tax.items():
                w = 15 if "domain" in cat.lower() else 12
                for s in s_list:
                    weighted_terms[str(s).lower()] = w
                    for sub in str(s).lower().split():
                        if len(sub) > 2:
                            weighted_terms[sub] = max(weighted_terms.get(sub, 0), w - 2)

        for s in (cand.get("skills") or []):
            weighted_terms[str(s).lower()] = max(weighted_terms.get(str(s).lower(), 0), 10)
        for r in (cand.get("target_roles") or []):
            weighted_terms[str(r).lower()] = max(weighted_terms.get(str(r).lower(), 0), 10)

        headline = str(cand.get("resume_headline") or cand.get("headline") or cand.get("current_title") or "").lower()
        for token in headline.split():
            clean = token.strip("|,.-/")
            if len(clean) > 2:
                weighted_terms[clean] = max(weighted_terms.get(clean, 0), 8)

        summary = str(cand.get("profile_summary") or cand.get("summary") or "").lower()
        for token in summary.split():
            clean = token.strip("|,.-/")
            if len(clean) > 3:
                weighted_terms[clean] = max(weighted_terms.get(clean, 0), 2)

        best_pill = None
        best_score = -1.0

        for p in pill_elements:
            p_text = p.inner_text().strip().lower()
            score = 0.0
            for term, weight in weighted_terms.items():
                if term in p_text:
                    score += weight * (len(term) / 4.0)
            if score > best_score:
                best_score = score
                best_pill = p

        return best_pill if best_score > 0 else (pill_elements[0] if pill_elements else None)
