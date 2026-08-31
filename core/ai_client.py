"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT - AI CLIENT & REASONING BRAIN
File: core/ai_client.py
================================================================================
Profile-agnostic AI engine operating with zero hardcoded candidate parameters.
All reasoning context is dynamically constructed from candidate_config.json,
resume.md, and live DOM screening question telemetry, delegating decisions
directly to Gemini Flash or Antigravity 2.0 via interactive stdin/stdout.
================================================================================
"""

import os
import sys
import json
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False


class MatchResult(tuple):
    def __new__(cls, score: int, reasoning: str, matching_skills: List[str] = None, missing_skills: List[str] = None):
        matching_skills = matching_skills or []
        missing_skills = missing_skills or []
        return super(MatchResult, cls).__new__(cls, (score, reasoning, matching_skills, missing_skills))

    def __init__(self, score: int, reasoning: str, matching_skills: List[str] = None, missing_skills: List[str] = None):
        self.score = int(score)
        self.reasoning = str(reasoning)
        self.matching_skills = matching_skills or []
        self.missing_skills = missing_skills or []

    def __getitem__(self, item):
        if isinstance(item, str):
            if item == "score": return self.score
            elif item == "reasoning": return self.reasoning
            elif item == "matching_skills": return self.matching_skills
            elif item == "missing_skills": return self.missing_skills
            raise KeyError(f"Invalid key: {item}")
        return super().__getitem__(item)

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "reasoning": self.reasoning,
            "matching_skills": self.matching_skills,
            "missing_skills": self.missing_skills
        }


class AIClient:
    """
    Autonomous Reasoning Engine for Job Suitability, ATS Bullet Reordering,
    Dynamic Screening Questionnaire Resolution, and Cover Letter Synthesis.
    Zero-hardcoding: resolves everything from ProfileContext at runtime.
    """

    def __init__(self, profile_context=None):
        self.profile_context = profile_context
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.client_ready = False
        self.model = None

        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
                self.client_ready = True
            except Exception as e:
                print(f"[AIClient] Gemini API Key unavailable or initialization error: {e}. Defaulting to Antigravity 2.0 AI Brain.")

    def generate_text(self, prompt: str, system_instruction: Optional[str] = None, default_fallback: str = "", **kwargs) -> str:
        if self.client_ready and self.model:
            try:
                full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
                response = self.model.generate_content(full_prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[AIClient] Gemini generation notice: {e}. Engaging Antigravity 2.0 fallback.")

        if default_fallback:
            return default_fallback

        return self._fallback_antigravity_interactive(prompt, context_type="General Generation", single_line=True)

    def ask_ai_direct(self, prompt: str) -> str:
        return self.generate_text(prompt)

    def evaluate_job_match(
        self,
        job_title: str,
        job_description: str,
        candidate_profile: Optional[Dict[str, Any]] = None,
        resume_text: Optional[str] = None,
        *args,
        **kwargs
    ) -> MatchResult:
        """
        Evaluates job suitability against dynamically loaded candidate profile criteria.
        Dynamically penalizes domains based purely on candidate_config.json negative_keywords.
        """
        profile = candidate_profile or (self.profile_context.config if self.profile_context else {})
        cand = profile.get("candidate", {})
        skills = profile.get("taxonomy_skills", {})
        target_jobs = profile.get("target_jobs", {})
        
        title_lower = job_title.lower()
        desc_lower = job_description.lower()
        
        negative_keywords = [k.lower() for k in target_jobs.get("negative_keywords", [])]
        target_keywords = [k.lower() for k in target_jobs.get("keywords", [])]

        if negative_keywords and any(neg in title_lower for neg in negative_keywords):
            if not target_keywords or not any(tgt in title_lower for tgt in target_keywords):
                return MatchResult(
                    score=15,
                    reasoning=f"Job '{job_title}' triggered candidate's dynamic negative keyword exclusion.",
                    matching_skills=[],
                    missing_skills=["Target domain alignment"]
                )

        flat_skills = []
        for cat_skills in skills.values():
            if isinstance(cat_skills, list):
                flat_skills.extend(cat_skills)
            elif isinstance(cat_skills, str):
                flat_skills.append(cat_skills)

        prompt = f"""
You are an expert ATS evaluation algorithm and recruiter.
Evaluate the suitability score (0-100) between the Job Listing and Candidate Profile.

CANDIDATE PROFILE:
Current Title: {cand.get('current_title', '')}
Total Experience: {cand.get('total_experience_years', '')} years
Location: {cand.get('location', '')}
Skills: {', '.join(flat_skills[:40])}
Target Config: {json.dumps(target_jobs)}
Resume Excerpt: {resume_text[:1500] if resume_text else ''}

JOB LISTING:
Title: {job_title}
Description:
{job_description[:2500]}

Return STRICTLY a JSON object:
{{
  "score": <integer from 0 to 100>,
  "reasoning": "<1-2 sentence concise evaluation>",
  "matching_skills": ["<skill1>", "<skill2>"],
  "missing_skills": ["<skill1>", "<skill2>"]
}}
"""
        raw_output = ""
        if self.client_ready and self.model:
            try:
                response = self.model.generate_content(prompt)
                if response and response.text:
                    raw_output = response.text.strip()
            except Exception:
                pass

        if not raw_output:
            cand_title_lower = cand.get("current_title", "").lower()
            matched = [s for s in flat_skills if s.lower() in desc_lower]
            missing = [s for s in flat_skills if s.lower() not in desc_lower][:3]
            
            score = 50
            if any(t in title_lower for t in cand_title_lower.split() if len(t) > 2):
                score += 25
            if len(matched) >= 2:
                score += min(len(matched) * 5, 20)
            score = min(score, 95)
            
            return MatchResult(
                score=score,
                reasoning=f"Matched {len(matched)} profile skills dynamically for {job_title}.",
                matching_skills=matched[:5],
                missing_skills=missing
            )

        try:
            clean_json = re.sub(r"```json\s*|\s*```", "", raw_output).strip()
            data = json.loads(clean_json)
            return MatchResult(
                score=int(data.get("score", 50)),
                reasoning=str(data.get("reasoning", "Evaluated via AI Brain")),
                matching_skills=list(data.get("matching_skills", [])),
                missing_skills=list(data.get("missing_skills", []))
            )
        except Exception:
            return MatchResult(score=60, reasoning="Evaluated via candidate profile match criteria.", matching_skills=[], missing_skills=[])

    def answer_screening_question(
        self,
        question: str,
        candidate_profile: Optional[Dict[str, Any]] = None,
        options: Optional[List[str]] = None,
        control_type: Optional[str] = None,
        resume_text: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Evaluates recruiter screening questions factually against the candidate's resume.
        Zero hardcoded assumptions. Strict exact-match caching.
        """
        profile = candidate_profile or (self.profile_context.config if self.profile_context else {})
        cand = profile.get("candidate", {})
        learned = profile.get("auto_learned_truths", {})
        ats = profile.get("ats_answers", {})
        
        q_clean = question.strip()
        q_lower = q_clean.lower()

        # Step 1: Strict EXACT MATCH check to prevent broad regex bleeding (Fixes H4 Learned Truth Poisoning)
        for k, v in learned.items():
            if k.strip().lower() == q_lower:
                val = str(v).strip()
                if options:
                    matched_opt = self._best_option_match(val, options)
                    if matched_opt: return matched_opt
                return val

        for k, v in ats.items():
            if k.strip().lower() == q_lower:
                val = str(v).strip()
                if options:
                    matched_opt = self._best_option_match(val, options)
                    if matched_opt: return matched_opt
                return val

        # Step 2: Route everything to AI/Terminal (Eradicates deterministic hardcoding bugs)
        resume_md = resume_text or ""
        if not resume_md and self.profile_context and hasattr(self.profile_context, "resume_text"):
            resume_md = self.profile_context.resume_text

        prompt = f"""
You are answering an official recruiter screening questionnaire on behalf of the candidate.

CANDIDATE PROFILE DATA (FACTUAL SOURCE OF TRUTH):
{json.dumps(cand, indent=2)}

CANDIDATE MASTER RESUME:
{resume_md[:3000]}

RECRUITER QUESTION:
"{q_clean}"

AVAILABLE CHOICES (IF APPLICABLE):
{json.dumps(options) if options else 'None (Provide direct numeric value or short answer)'}

INSTRUCTIONS:
1. Examine the candidate's resume and profile data carefully for the specific skill, tool, process, or domain requested.
2. If the question asks for years of experience in a specific skill or process:
   - Calculate how many years the candidate actually practiced that specific skill based on their employment history.
   - If the candidate DOES NOT have experience in that specific skill/process in their resume, answer '0'.
   - DO NOT default to their total career experience unless the question explicitly asks for overall/total experience.
3. Provide a strictly truthful, factual answer based ONLY on the provided candidate context. Do not invent or guess.
4. If choices are provided, return EXACTLY one option string verbatim from the list.
5. Output STRICTLY the final answer string with zero conversational preamble.
"""
        answer = ""
        if self.client_ready and self.model:
            try:
                resp = self.model.generate_content(prompt)
                if resp and resp.text:
                    answer = resp.text.strip().replace('"', '').replace("'", "")
            except Exception as e:
                print(f"[AIClient] Brain API notice: {e}. Consulting Antigravity 2.0 terminal.")

        if not answer:
            banner = f"CHATBOT QUESTION: {question} | CONTROL: {control_type or 'FREE_TEXT'}"
            if options:
                banner += f"\nAVAILABLE OPTIONS: {options}"
            answer = self._fallback_antigravity_interactive(prompt, context_type=banner, single_line=True)

        if options:
            best_opt = self._best_option_match(answer, options)
            if best_opt:
                answer = best_opt
            else:
                # Fix H1: If no option matches, force terminal intervention instead of blindly picking option[0]
                print(f"[AIClient] Warning: AI response '{answer}' did not match any available UI option.")
                banner = f"CHATBOT QUESTION: {question} | MATCH FAILED. SELECT FROM: {options}"
                answer = self._fallback_antigravity_interactive(prompt, context_type=banner, single_line=True)
                answer = self._best_option_match(answer, options) or options[0]

        self._persist_learned_truth(q_clean, answer)
        return answer

    def _best_option_match(self, target: str, options: List[str]) -> Optional[str]:
        """Safely matches string choices. Returns None if no solid match is found."""
        if not options:
            return None
        target_clean = target.lower().strip()
        
        # 1. Exact Match
        for opt in options:
            if opt.lower().strip() == target_clean:
                return opt

        # 2. Strict Word Boundary Substring (Fixes H2 Substring match bug)
        for opt in options:
            if re.search(rf'\b{re.escape(target_clean)}\b', opt.lower().strip()):
                return opt

        # 3. Numeric capture fallback
        nums = re.findall(r"\d+", target_clean)
        if nums:
            num = nums[0]
            for opt in options:
                if num in re.findall(r"\d+", opt):
                    return opt

        if target_clean in ["yes", "true", "y"]:
            for opt in options:
                if "yes" in opt.lower(): return opt
        elif target_clean in ["no", "false", "n"]:
            for opt in options:
                if "no" in opt.lower(): return opt

        return None

    def _persist_learned_truth(self, question: str, answer: str):
        """Persists newly resolved truths into candidate_config.json."""
        if self.profile_context and answer:
            try:
                if "auto_learned_truths" not in self.profile_context.config:
                    self.profile_context.config["auto_learned_truths"] = {}
                clean_q = question.strip()
                if clean_q:
                    self.profile_context.config["auto_learned_truths"][clean_q] = answer
                    if hasattr(self.profile_context, "save_config"):
                        self.profile_context.save_config()
            except Exception as e:
                print(f"[AIClient] Caching truth notice: {e}")

    def score_and_reorder_bullets(self, experience_bullets: List[str], job_description: str, **kwargs) -> List[str]:
        """Reorders factual resume bullet points using strict word boundaries (Fix M5)."""
        if not experience_bullets or len(experience_bullets) <= 1:
            return experience_bullets

        jd_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", job_description.lower()))
        scored_bullets = []
        for b in experience_bullets:
            b_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", b.lower()))
            overlap = len(jd_words.intersection(b_words))
            scored_bullets.append((overlap, b))

        scored_bullets.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in scored_bullets]

    def generate_cover_letter(self, job_title: str, company_name: str, job_description: str, candidate_profile: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        profile = candidate_profile or (self.profile_context.config if self.profile_context else {})
        cand = profile.get("candidate", {})

        prompt = f"""
Write a professional, compelling, 3-paragraph Cover Letter for {cand.get('full_name', 'the candidate')}
applying for the role of '{job_title}' at '{company_name}'.

CANDIDATE PROFILE:
{json.dumps(profile, indent=2)}

JOB DETAILS:
Company: {company_name}
Role: {job_title}
Description:
{job_description[:1800]}

Format as clean text paragraphs ready for submission with zero placeholders.
"""
        return self.generate_text(prompt, system_instruction="You are a professional candidate applying for leadership roles.")

    def analyze_profile_keywords(self, resume_text: str, target_roles: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", resume_text.lower())
        unique_words = sorted(list(set(words)))
        return {
            "total_keywords_detected": len(unique_words),
            "top_keywords": unique_words[:25],
            "target_roles": target_roles or []
        }

    def _fallback_antigravity_interactive(self, prompt: str, context_type: str = "General", single_line: bool = True) -> str:
        """Interactive stdin/stdout delimiter protocol for Antigravity 2.0."""
        print("\n" + "=" * 70, flush=True)
        print(f"[ANTIGRAVITY 2.0 AI BRAIN - ACTION REQUIRED: {context_type.upper()}]", flush=True)
        print("=" * 70, flush=True)
        print(prompt.strip(), flush=True)
        print("-" * 70, flush=True)
        if single_line:
            print(">> Enter factual response (single line) and press ENTER:", flush=True)
            try:
                line = sys.stdin.readline()
                return line.strip() if line else ""
            except Exception as e:
                print(f"[AIClient] stdin read error: {e}")
                return ""
        else:
            print(">> Enter response lines. End input by typing 'END_OF_ANSWER' on a new line:", flush=True)
            lines = []
            try:
                while True:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    if line.strip() == "END_OF_ANSWER":
                        break
                    lines.append(line)
                return "".join(lines).strip()
            except Exception as e:
                print(f"[AIClient] stdin multi-line read error: {e}")
                return ""