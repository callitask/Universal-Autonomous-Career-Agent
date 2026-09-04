"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT - AI CLIENT & REASONING BRAIN
File: core/ai_client.py
================================================================================
Profile-agnostic cognitive engine operating with zero hardcoded candidate parameters.
Features the Universal Zero-API Antigravity 2.0 Cognitive IPC Bridge (pending_question.json).
Empowers Google Antigravity 2.0 as the primary reasoning model for:
  1. Dynamic Candidate Profile & Taxonomy Synthesis (Zero-Hardcoding)
  2. Precision Two-Stage Job Qualification & Semantic JD Scoring (>= 60% threshold)
  3. Factual ATS Resume Content Tailoring & Competency Prioritization
  4. Portal Screening Questionnaire Resolution & Continuous Self-Learning
  5. Search Starvation Auto-Healing & Seniority Designation Expansion
Completely eliminates terminal stdin/input blocking (Guardrail H6).
Anchors experience parsing to prevent company-age false rejections.
Eliminates cross-functional false positives on incompatible verticals.
================================================================================
"""

import os
import sys
import json
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Optional Gemini SDK support (supports both new google-genai and legacy google-generativeai)
try:
    from google import genai
    HAS_GENAI_NEW = True
except ImportError:
    HAS_GENAI_NEW = False

try:
    import google.generativeai as legacy_genai
    HAS_GENAI_LEGACY = True
except ImportError:
    HAS_GENAI_LEGACY = False


class MatchResult(tuple):
    """
    Hybrid match result supporting:
    - Tuple unpacking: score, reasoning, matching, missing = result
    - Attribute access: result.score, result.reasoning
    - Dict-style lookup: result['score'], result.get('score', 0)
    """
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
            if item == "score":
                return self.score
            elif item == "reasoning":
                return self.reasoning
            elif item == "matching_skills":
                return self.matching_skills
            elif item == "missing_skills":
                return self.missing_skills
            raise KeyError(f"Invalid key: {item}")
        return super().__getitem__(item)

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class AIClient:
    """
    Autonomous Reasoning Engine for Dynamic Screening Questionnaire Resolution,
    Factual Candidate Job Scoring, Dynamic Cognitive Profile Synthesis,
    and Factual ATS Resume Content Optimization.
    Zero-hardcoding: resolves all candidate parameters dynamically at runtime.
    Operates with Google Antigravity 2.0 (File-Based IPC) as the primary brain,
    supplemented by Gemini API when configured. Zero terminal stdin blocking.
    """
    def __init__(self, profile_context=None):
        self.profile_context = profile_context
        if not self.profile_context:
            try:
                from core.utils.profile_context import ProfileContext
                self.profile_context = ProfileContext()
            except Exception:
                self.profile_context = None

        # Resolve Gemini API client if API key is present in environment or candidate config
        self.gemini_client = None
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key and self.profile_context and hasattr(self.profile_context, "config"):
            api_key = self.profile_context.config.get("candidate", {}).get("gemini_api_key", "").strip()

        if api_key:
            if HAS_GENAI_NEW:
                try:
                    self.gemini_client = genai.Client(api_key=api_key)
                except Exception as e:
                    print(f"[AI CLIENT] Notice: Could not initialize google-genai client: {e}", flush=True)
            elif HAS_GENAI_LEGACY:
                try:
                    legacy_genai.configure(api_key=api_key)
                    self.gemini_client = legacy_genai.GenerativeModel("gemini-1.5-flash")
                except Exception as e:
                    print(f"[AI CLIENT] Notice: Could not initialize legacy genai client: {e}", flush=True)

    def synthesize_cognitive_profile(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Synthesizes a candidate-specific, profile-bound Cognitive Profile Model
        and persists it to profiles/<profile>/output/cognitive_profile.json.
        Zero hardcoded assumptions: derives domain, technical skills, soft skills,
        incompatible verticals, acronyms, and multi-cycle designation queues
        dynamically from resume.md and candidate configuration at runtime.
        Routes to Antigravity 2.0 File-Based IPC when Gemini API is unconfigured.
        """
        if not self.profile_context:
            return {}

        if not force_refresh:
            cached = self.profile_context.load_cognitive_profile()
            if cached and cached.get("candidate_domain") and cached.get("search_cycles"):
                return cached

        resume_md = getattr(self.profile_context, "resume_text", "") or ""
        config = getattr(self.profile_context, "config", {}) or {}
        cand = config.get("candidate", {})
        cand_exp = float(cand.get("total_experience_years", 0) or 0)
        target_jobs = config.get("target_jobs", {})
        target_keywords = list(target_jobs.get("keywords") or [])
        recommended_titles = list(target_jobs.get("recommended_titles") or [])
        cand_title = cand.get("current_title", "")

        prompt = f"""You are an elite talent strategist and executive recruiter. Analyze this candidate's factual resume and configuration to synthesize a complete, profile-bound Cognitive Profile Model.
CANDIDATE CONFIG:
Current Title: {cand_title}
Total Experience: {cand_exp} years
Configured Target Keywords: {target_keywords}

RESUME:
{resume_md[:4000]}

Return STRICTLY a JSON object with this exact schema:
{{
  "candidate_domain": "<e.g. Financial Services & Accounting Operations, Software Engineering, Supply Chain Management, Corporate Legal, etc.>",
  "primary_title": "<most representative senior title matching experience>",
  "years_of_experience": {cand_exp},
  "seniority_level": "<e.g. Fresher / Associate / Specialist / Assistant Manager / Senior Manager / Director / C-Level>",
  "core_domain_skills": ["<20-30 specific technical domain skills, software tools, systems, frameworks, processes from resume>"],
  "generic_soft_skills": ["<behavioral and communication skills like analytical, problem solving, teamwork, leadership>"],
  "domain_acronyms": {{
    "<acronym>": "<expansion and meaning>"
  }},
  "incompatible_verticals": {{
    "<out_of_domain_vertical_name>": ["<specific_job_title_marker1>", "<specific_job_title_marker2>"]
  }},
  "search_cycles": [
    ["<5-8 primary core target designations for Cycle 1>"],
    ["<5-8 seniority or lateral designations for Cycle 2>"],
    ["<5-8 specialized or functional designations for Cycle 3>"]
  ],
  "active_cycle_index": 0
}}"""

        # 1. Try synthesis via Gemini LLM if available
        if self.gemini_client:
            try:
                raw_text = self.generate_text(prompt, default_fallback="")
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    model_data = json.loads(json_match.group(0))
                    if model_data.get("candidate_domain") and model_data.get("search_cycles"):
                        model_data["active_cycle_index"] = 0
                        model_data["last_synthesized"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        self.profile_context.save_cognitive_profile(model_data)
                        return model_data
            except Exception as e:
                print(f"[AI CLIENT] Notice: Gemini cognitive profile synthesis failed ({e}).", flush=True)

        # 2. Antigravity 2.0 File-Based IPC Handshake (Zero-API Primary Engine)
        ipc_res = self._fallback_antigravity_ipc(
            prompt=prompt,
            question="Synthesize Cognitive Profile Model from Resume",
            control_type="JSON",
            task_type="PROFILE_SYNTHESIS"
        )
        if ipc_res:
            try:
                json_match = re.search(r'\{.*\}', ipc_res, re.DOTALL)
                if json_match:
                    model_data = json.loads(json_match.group(0))
                    if model_data.get("candidate_domain") and model_data.get("search_cycles"):
                        model_data["active_cycle_index"] = 0
                        model_data["last_synthesized"] = time.strftime("%Y-%m-%d %H:%M:%S")
                        self.profile_context.save_cognitive_profile(model_data)
                        return model_data
            except Exception as e:
                print(f"[AI CLIENT] Notice: Parsing AG 2.0 synthesized profile JSON failed: {e}", flush=True)

        # 3. Resilient Dynamic NLP Heuristic Fallback (Zero Static Industry Dictionaries)
        # Extracts skills, sections, and titles dynamically from resume.md
        GENERIC_SOFT_SKILLS = [
            "analytical", "problem solving", "conceptual", "communication", "written", "verbal",
            "teamwork", "leadership", "management", "documentation", "presentation",
            "process improvement", "automation", "reporting", "planning",
            "strategy", "strategic planning", "due diligence", "recruitment", "risk mitigation",
            "internal controls", "accuracy", "detail", "reasoning", "prioritization",
            "negotiation", "organizational", "interpersonal", "coordination"
        ]

        # Extract all skills from taxonomy_skills config
        skills_dict = config.get("taxonomy_skills", {})
        extracted_skills = []
        for cat_skills in skills_dict.values():
            if isinstance(cat_skills, list):
                extracted_skills.extend([s.strip() for s in cat_skills if s and s.strip()])
            elif isinstance(cat_skills, str):
                extracted_skills.append(cat_skills.strip())

        # Extract competency lines from resume markdown
        comp_match = re.search(r'##\s*(?:CORE\s+COMPETENCIES|SKILLS|TECHNICAL\s+SKILLS)(.*?)(?=##|\Z)', resume_md, re.DOTALL | re.IGNORECASE)
        if comp_match:
            for line in comp_match.group(1).split("\n"):
                if "|" in line:
                    for part in line.split("|"):
                        for s in re.split(r'[,;()]+', part):
                            clean_s = s.strip()
                            if len(clean_s) > 2 and not clean_s.startswith("*") and not clean_s.startswith("-"):
                                extracted_skills.append(clean_s)
                elif line.strip().startswith("-") or line.strip().startswith("*"):
                    for s in re.split(r'[,;]+', line.lstrip("-* ")):
                        clean_s = s.strip()
                        if len(clean_s) > 2:
                            extracted_skills.append(clean_s)

        core_domain_skills = []
        generic_soft_skills = list(GENERIC_SOFT_SKILLS)
        soft_set = set(s.lower() for s in GENERIC_SOFT_SKILLS)
        seen_core = set()

        for s in extracted_skills:
            s_clean = s.strip()
            s_lower = s_clean.lower()
            if s_lower in soft_set:
                if s_clean not in generic_soft_skills:
                    generic_soft_skills.append(s_clean)
            elif s_lower not in seen_core and len(s_clean) > 2:
                seen_core.add(s_lower)
                core_domain_skills.append(s_clean)

        # Derive domain dynamically from target keywords or resume headline
        inferred_domain = "Professional Operations"
        if target_keywords:
            inferred_domain = f"{target_keywords[0]} Domain"
        elif cand_title:
            inferred_domain = f"{cand_title} Field"

        # Seniority tier assignment
        if cand_exp >= 12.0:
            seniority_level = "Director / Practice Lead / Senior Executive"
            senior_prefix = "Director"
        elif cand_exp >= 8.0:
            seniority_level = "Lead / Assistant Manager / Senior Manager"
            senior_prefix = "Assistant Manager"
        elif cand_exp >= 5.0:
            seniority_level = "Mid-Senior / Specialist"
            senior_prefix = "Senior"
        elif cand_exp >= 2.0:
            seniority_level = "Associate / Executive"
            senior_prefix = ""
        else:
            seniority_level = "Fresher / Entry Level"
            senior_prefix = "Junior"

        base_targets = list(target_keywords) if target_keywords else [cand_title or "Professional"]
        cycle1 = [t.strip() for t in base_targets[:8] if t and t.strip()]

        cycle2_candidates = []
        for kw in cycle1:
            clean_kw = re.sub(r'\b(Senior|Lead|Assistant Manager|Junior)\b', '', kw, flags=re.IGNORECASE).strip("- ")
            if clean_kw:
                c2_a = f"{senior_prefix} - {clean_kw}".strip("- ") if senior_prefix else clean_kw
                c2_b = f"Senior {clean_kw}".strip()
                if c2_a not in cycle1 and c2_a not in cycle2_candidates:
                    cycle2_candidates.append(c2_a)
                if c2_b not in cycle1 and c2_b not in cycle2_candidates:
                    cycle2_candidates.append(c2_b)
        for rec in recommended_titles:
            if rec not in cycle1 and rec not in cycle2_candidates:
                cycle2_candidates.append(rec)
        cycle2 = cycle2_candidates[:8] if cycle2_candidates else list(cycle1)

        cycle3_candidates = []
        for skill in core_domain_skills[:6]:
            if len(skill.split()) <= 3:
                f_title = f"{skill} Specialist"
                if f_title not in cycle1 and f_title not in cycle2 and f_title not in cycle3_candidates:
                    cycle3_candidates.append(f_title)
        cycle3 = cycle3_candidates[:8] if cycle3_candidates else list(cycle2)

        search_cycles = [c for c in [cycle1, cycle2, cycle3] if c]
        if not search_cycles:
            search_cycles = [[cand_title or "Specialist"]]

        cognitive_profile = {
            "candidate_domain": inferred_domain,
            "primary_title": cand_title or (cycle1[0] if cycle1 else "Specialist"),
            "years_of_experience": cand_exp,
            "seniority_level": seniority_level,
            "core_domain_skills": core_domain_skills[:30],
            "generic_soft_skills": generic_soft_skills,
            "domain_acronyms": {},
            "incompatible_verticals": {},
            "search_cycles": search_cycles,
            "active_cycle_index": 0,
            "last_synthesized": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.profile_context.save_cognitive_profile(cognitive_profile)
        return cognitive_profile

    def get_active_search_cycle(self) -> List[str]:
        """
        Retrieves the active batch of 5-8 search designations for the current cycle.
        If cognitive profile is missing, synthesizes it automatically.
        """
        if not self.profile_context:
            return []
        cog_prof = self.profile_context.load_cognitive_profile()
        if not cog_prof:
            cog_prof = self.synthesize_cognitive_profile()

        cycles = cog_prof.get("search_cycles", [])
        if not cycles:
            return self.profile_context.config.get("target_jobs", {}).get("keywords", [])

        idx = cog_prof.get("active_cycle_index", 0)
        if idx >= len(cycles):
            idx = 0
            cog_prof["active_cycle_index"] = 0
            self.profile_context.save_cognitive_profile(cog_prof)

        return cycles[idx]

    def advance_search_cycle(self) -> int:
        """
        Advances the search cycle to the next batch of designations and persists state.
        Returns the new active_cycle_index.
        """
        if not self.profile_context:
            return 0
        cog_prof = self.profile_context.load_cognitive_profile()
        if not cog_prof:
            cog_prof = self.synthesize_cognitive_profile()

        cycles = cog_prof.get("search_cycles", [])
        if not cycles:
            return 0

        cur_idx = cog_prof.get("active_cycle_index", 0)
        new_idx = (cur_idx + 1) % len(cycles)
        cog_prof["active_cycle_index"] = new_idx
        self.profile_context.save_cognitive_profile(cog_prof)
        print(f"[COGNITIVE BRAIN] Advanced search cycle to Cycle {new_idx + 1}/{len(cycles)}: {cog_prof.get('search_cycles', [])[new_idx]}", flush=True)
        return new_idx

    def generate_text(self, prompt: str, default_fallback: str = "", **kwargs) -> str:
        """
        Generates text using Gemini if initialized and operational; if unavailable
        or rate-limited, falls back to the File-Based IPC handshake (_fallback_antigravity_ipc)
        or default_fallback without crashing.
        Never uses terminal stdin (input/readline) to prevent daemon blocking (H6 Guardrail).
        """
        # 1. Attempt generation via operational Gemini API client if available
        if self.gemini_client:
            try:
                if hasattr(self.gemini_client, "models"):
                    model_name = kwargs.get("model", "gemini-2.5-flash")
                    response = self.gemini_client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if response and response.text:
                        return response.text.strip()
                elif hasattr(self.gemini_client, "generate_content"):
                    response = self.gemini_client.generate_content(prompt)
                    if response and response.text:
                        return response.text.strip()
            except Exception as e:
                print(f"[AI CLIENT] Gemini API unavailable or rate-limited ({e}). Falling back to AG 2.0 File IPC.", flush=True)

        # 2. File-Based IPC Handshake for Antigravity 2.0
        ipc_res = self._fallback_antigravity_ipc(
            prompt=prompt,
            question=kwargs.get("question", prompt.split("\n")[0][:120].strip()),
            options=kwargs.get("options", None),
            control_type=kwargs.get("control_type", "TEXT"),
            max_characters=kwargs.get("max_characters", None),
            task_type=kwargs.get("task_type", "TEXT_GENERATION")
        )

        if ipc_res and ipc_res.strip():
            return ipc_res.strip()

        return default_fallback

    def tailor_resume_content(self, jd_text: str, master_resume_text: str) -> Dict[str, Any]:
        """
        Synthesizes a targeted professional summary and prioritized core competencies
        specifically tailored to the target Job Description while strictly preserving
        100% factual accuracy from the candidate's master resume (Zero Hallucinations).
        """
        prompt = f"""You are an elite executive resume strategist.
Analyze the target Job Description and the candidate's Master Resume.
TARGET JOB DESCRIPTION:
{jd_text[:3000]}

CANDIDATE MASTER RESUME:
{master_resume_text[:3500]}

INSTRUCTIONS:
1. Synthesize an ATS-optimized Professional Summary (3-4 sentences) that directly highlights the candidate's real, factual background in relation to this specific job's core responsibilities and tech stack.
2. Extract the top 12-16 most relevant Core Competencies / Technical Skills from the candidate's resume, ordered with the skills most demanded by this JD first.
3. CRITICAL: PRESERVE ABSOLUTE FACTUAL TRUTH. DO NOT INVENT, FABRICATE, OR EXAGGERATE ANY DEGREE, COMPANY, TOOL, OR METRIC.

Return STRICTLY a JSON object:
{{
  "tailored_summary": "<polished 3-4 sentence factual summary>",
  "prioritized_skills": ["<skill1>", "<skill2>", "<skill3>"]
}}"""

        # Try Gemini or AG 2.0 IPC
        raw = self.generate_text(prompt=prompt, task_type="RESUME_TAILORING")
        if raw:
            try:
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            except Exception:
                pass
        return {}

    def _parse_json_match_result(self, raw_text: str) -> Optional[MatchResult]:
        """Extracts and validates structured MatchResult JSON from LLM or IPC responses."""
        if not raw_text:
            return None
        try:
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                score = int(data.get("score", 0))
                score = max(0, min(score, 100))
                reasoning = str(data.get("reasoning", "")).strip()
                matching = list(data.get("matching_skills", []))
                missing = list(data.get("missing_skills", []))
                if score < 60 and not reasoning.startswith("Rejected") and not reasoning.startswith("Disqualified"):
                    reasoning = f"Rejected fit ({score}% < 60% threshold): {reasoning}"
                return MatchResult(
                    score=score,
                    reasoning=reasoning,
                    matching_skills=matching,
                    missing_skills=missing
                )
        except Exception:
            pass
        return None

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
        Two-Stage Cognitive Job Qualification Engine:
        Stage 1: Deterministic Hard Filter (Gatekeeper)
          - C6 Absolute Negative Title & JD Gating (word boundary)
          - Domain Title Alignment (phrase & token overlap gating)
          - Anchored Experience Band Filter (checks requirement context, ignores company age >20 yrs)
          - Incompatible Industry Gate with Domain Override (prevents cross-tooling false rejections)
        Stage 2: Precision Semantic & Factual Scoring (Dual-Brain + Local Fallback)
          - Operational Gemini Client Evaluation (0-100 JSON)
          - Antigravity 2.0 File-Based IPC Semantic Scoring (Zero-API primary engine)
          - Calibrated Factual Fallback (0-35 Title, 0-45 Skills [min 2], 0-20 Exp, >=60% threshold)
        """
        profile = candidate_profile or (self.profile_context.config if self.profile_context else {})
        cand = profile.get("candidate", {})
        skills_dict = profile.get("taxonomy_skills", {})
        target_jobs = profile.get("target_jobs", {})

        title_lower = job_title.lower().strip()
        desc_lower = job_description.lower().strip()

        negative_keywords = [k.lower().strip() for k in (target_jobs.get("negative_keywords") or []) if k and k.strip()]
        target_keywords = [k.lower().strip() for k in (target_jobs.get("keywords") or []) if k and k.strip()]
        recommended_titles = [t.lower().strip() for t in (target_jobs.get("recommended_titles") or []) if t and t.strip()]
        current_title = cand.get("current_title", "").lower().strip() if cand.get("current_title") else ""

        # =========================================================================
        # STAGE 1: DETERMINISTIC HARD FILTER (GATEKEEPER)
        # =========================================================================

        # 1.1 C6 Check: Negative Keywords are Absolute in Title and Core JD Headings
        for neg in negative_keywords:
            if re.search(rf'\b{re.escape(neg)}\b', title_lower):
                return MatchResult(
                    score=0,
                    reasoning=f"Rejected: Negative keyword '{neg}' detected in job title '{job_title}' (C6 Guardrail).",
                    matching_skills=[],
                    missing_skills=["Non-negative domain title"]
                )

        # Check prominent headings / opening of JD (first 800 chars)
        jd_intro = desc_lower[:800]
        for neg in negative_keywords:
            if re.search(rf'\b(?:role|position|hiring for|seeking a|looking for)\s+[^.\n]*\b{re.escape(neg)}\b', jd_intro):
                return MatchResult(
                    score=0,
                    reasoning=f"Rejected: Negative keyword '{neg}' detected in job description header (C6 Guardrail).",
                    matching_skills=[],
                    missing_skills=["Target domain alignment"]
                )

        # 1.2 Domain Title Alignment: Gating out completely out-of-domain roles
        all_targets = list(target_keywords) + list(recommended_titles)
        if current_title:
            all_targets.append(current_title)

        matched_target_phrase = False
        for target in all_targets:
            target_clean = target.lower().strip()
            if target_clean and re.search(rf'\b{re.escape(target_clean)}\b', title_lower):
                matched_target_phrase = True
                break

        generic_title_stopwords = {
            "and", "for", "the", "with", "lead", "senior", "junior", "manager",
            "executive", "officer", "associate", "specialist", "staff", "principal",
            "head", "director", "vp", "intern", "trainee", "expert", "consultant",
            "general", "global", "regional", "assistant", "deputy", "group", "team",
            "operations", "analyst", "professional", "representative", "coordinator",
            "administrator", "services", "service", "sr", "jr"
        }

        domain_tokens = set()
        for t in all_targets:
            for token in re.split(r'[\s/,-]+', t.lower()):
                if len(token) > 2 and token not in generic_title_stopwords:
                    domain_tokens.add(token)

        title_tokens = set()
        for token in re.split(r'[\s/,-]+', title_lower):
            if len(token) > 2 and token not in generic_title_stopwords:
                title_tokens.add(token)

        # Exact and stem/prefix matching (e.g. account/accounts <-> accountant; audit <-> auditor)
        matched_tokens = set()
        for dt in domain_tokens:
            for tt in title_tokens:
                if dt == tt:
                    matched_tokens.add(tt)
                elif len(dt) >= 4 and len(tt) >= 4 and (dt.startswith(tt[:5]) or tt.startswith(dt[:5])):
                    matched_tokens.add(tt)

        # Out-of-domain rejection: zero phrase and zero token overlap with candidate target domains
        if not matched_target_phrase and len(matched_tokens) == 0 and domain_tokens:
            return MatchResult(
                score=0,
                reasoning=f"Rejected: Out-of-domain role '{job_title}'. Zero phrase or token overlap with candidate target domains {target_keywords[:3]}.",
                matching_skills=[],
                missing_skills=["Target domain title alignment"]
            )

        # 1.3 Anchored Experience Band Filter (Defect 2 Fix)
        # Prevents matching company age statements (e.g., "in business for 25 years")
        cand_exp = float(cand.get("total_experience_years", target_jobs.get("experience_years", 0)) or 0)
        
        # Priority A: Check explicit requirements sections
        req_section_match = re.search(r'(?:requirements|specifications|qualifications|eligibility|profile|who you are)(.*?)(?=(?:responsibilities|perks|benefits|about us|company overview|\Z))', desc_lower, re.DOTALL)
        req_text = req_section_match.group(1) if req_section_match else desc_lower

        # Context-anchored experience regex (requires experience keywords in proximity)
        anchored_exp_pattern = r'(?:minimum|min\.?|at least|overall|relevant|total|requires?|with)?\s*(\d+)(?:\s*[-–to]+\s*(\d+))?\s*(?:years?|yrs?)(?:\s*(?:of)?\s*(?:experience|exp|relevant experience|industry experience))'
        exp_matches = re.findall(anchored_exp_pattern, req_text)

        if not exp_matches:
            # Fallback: search anywhere in JD, but strictly require the word "experience" or "exp" immediately following
            exp_matches = re.findall(r'\b(\d+)(?:\s*[-–to]+\s*(\d+))?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)\b', desc_lower)

        if exp_matches:
            # Filter out obvious company age statements (> 20 years unless candidate has > 20 years)
            valid_exp_matches = [m for m in exp_matches if float(m[0]) <= max(20.0, cand_exp + 5.0)]
            if valid_exp_matches:
                min_req_exp = float(valid_exp_matches[0][0])
                if min_req_exp > cand_exp + 3:
                    return MatchResult(
                        score=0,
                        reasoning=f"Rejected: Experience gap too wide for '{job_title}'. Role requires minimum {int(min_req_exp)} years, but candidate has {cand_exp} years (exceeds +3 year limit).",
                        matching_skills=[],
                        missing_skills=[f"Minimum {int(min_req_exp)} years experience"]
                    )

        # 1.4 Incompatible Industry Gate with Domain Override (Defect 3 Fix)
        # Bypasses vertical exclusion if candidate domain function is present in job title
        cog_prof = self.profile_context.load_cognitive_profile() if self.profile_context else None
        if not cog_prof and self.profile_context:
            cog_prof = self.synthesize_cognitive_profile()

        incompatible_verticals = cog_prof.get("incompatible_verticals", {}) if cog_prof else {}
        cand_domain = cog_prof.get("candidate_domain", "target domain") if cog_prof else "target domain"

        cand_domain_words = set()
        for kw in target_keywords:
            for w in re.findall(r'[a-zA-Z]{4,}', kw.lower()):
                if w not in generic_title_stopwords:
                    cand_domain_words.add(w)

        title_has_cand_domain = any(
            (cdw in title_lower or (len(cdw) >= 4 and any(tw.startswith(cdw[:5]) for tw in title_tokens)))
            for cdw in cand_domain_words
        )

        # If title has candidate domain, NEVER reject due to cross-functional tooling in JD!
        if not title_has_cand_domain:
            for vertical_name, v_markers in incompatible_verticals.items():
                title_marker = next((vm for vm in v_markers if re.search(rf'\b{re.escape(vm)}\b', title_lower)), None)
                if title_marker:
                    return MatchResult(
                        score=0,
                        reasoning=f"Rejected: Out-of-domain vertical '{vertical_name}' ('{title_marker}') detected in job title with no candidate domain ({cand_domain}) function.",
                        matching_skills=[],
                        missing_skills=[f"Target domain alignment (Not {vertical_name})"]
                    )

        # =========================================================================
        # STAGE 2: PRECISION SEMANTIC & FACTUAL SCORING
        # =========================================================================

        # Flatten candidate skills
        flat_skills = []
        for cat_skills in skills_dict.values():
            if isinstance(cat_skills, list):
                flat_skills.extend([s.strip() for s in cat_skills if s.strip()])
            elif isinstance(cat_skills, str):
                flat_skills.append(cat_skills.strip())

        resume_md = resume_text or (self.profile_context.resume_text if self.profile_context else "")
        if resume_md and not flat_skills:
            words = re.findall(r'[A-Za-z0-9#+.\-]+', resume_md)
            flat_skills = list(set([w for w in words if len(w) > 3]))

        unique_skills = []
        seen_skills = set()
        for s in flat_skills:
            if s.lower() not in seen_skills:
                seen_skills.add(s.lower())
                unique_skills.append(s)

        matched_skills = []
        missing_skills = []
        for s in unique_skills:
            s_clean = s.strip()
            if re.search(rf'\b{re.escape(s_clean.lower())}\b', desc_lower):
                matched_skills.append(s_clean)
            else:
                missing_skills.append(s_clean)

        # 2.1 Dual-Brain LLM Route (If Gemini API client is operational)
        if self.gemini_client:
            try:
                llm_prompt = f"""You are an elite talent recruiter evaluating whether a candidate genuinely qualifies for this job.
CANDIDATE PROFILE:
Current Title: {cand.get('current_title', '')}
Total Experience: {cand_exp} years
Key Skills: {json.dumps(skills_dict)}
Master Resume Excerpt:
{resume_md[:1800]}

JOB TO EVALUATE:
Title: {job_title}
Job Description:
{job_description[:2500]}

EVALUATION CRITERIA:
1. Title & Domain Alignment (0-35 points)
2. Factual Skill Match (0-45 points, strictly requiring real overlap with candidate actual skills)
3. Experience & Seniority Compatibility (0-20 points)
4. Passing threshold is strictly 60 points. A score below 60 means candidate should NOT apply.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer 0-100>,
  "reasoning": "<concise 1-2 sentence explanation>",
  "matching_skills": ["<skill1>", "<skill2>"],
  "missing_skills": ["<skill1>", "<skill2>"]
}}"""
                raw_llm = ""
                if hasattr(self.gemini_client, "models"):
                    resp = self.gemini_client.models.generate_content(
                        model=kwargs.get("model", "gemini-2.5-flash"),
                        contents=llm_prompt
                    )
                    if resp and resp.text:
                        raw_llm = resp.text.strip()
                elif hasattr(self.gemini_client, "generate_content"):
                    resp = self.gemini_client.generate_content(llm_prompt)
                    if resp and resp.text:
                        raw_llm = resp.text.strip()

                if raw_llm:
                    parsed_match = self._parse_json_match_result(raw_llm)
                    if parsed_match:
                        return parsed_match
            except Exception as e:
                print(f"[AI CLIENT] Gemini evaluation notice ({e}). Checking AG 2.0 IPC.", flush=True)

        # 2.2 Zero-API Antigravity 2.0 Cognitive IPC Route
        # If enabled or in zero-API mode, let AG 2.0 evaluate with human-level reasoning
        enable_ipc_eval = kwargs.get("enable_ipc", True)
        if enable_ipc_eval and not self.gemini_client:
            ipc_eval_prompt = f"""Evaluate candidate qualification for this job posting.
CANDIDATE:
Title: {cand.get('current_title', '')}
Experience: {cand_exp} years
Domain Skills: {matched_skills[:10]}
Resume Excerpt:
{resume_md[:1500]}

JOB:
Title: {job_title}
Description:
{job_description[:2000]}

Score from 0 to 100 in strict JSON:
{{"score": <int 0-100>, "reasoning": "<1-2 sentence rationale>", "matching_skills": [<skills>], "missing_skills": [<skills>]}}"""

            ipc_res = self._fallback_antigravity_ipc(
                prompt=ipc_eval_prompt,
                question=f"Evaluate Job Fit: {job_title}",
                control_type="JSON",
                task_type="JOB_EVALUATION"
            )
            parsed_ipc = self._parse_json_match_result(ipc_res)
            if parsed_ipc:
                return parsed_ipc

        # 2.3 Calibrated Deterministic Factual Scoring (Local Fallback)
        # Component A: Title/Domain Alignment (0 - 35 points)
        if matched_target_phrase:
            title_score = 35
        elif len(matched_tokens) >= 2:
            title_score = 25
        elif len(matched_tokens) == 1:
            title_score = 15
        else:
            title_score = 0

        # Component B: Core Skill Matches (0 - 45 points)
        profile_soft_skills = set(s.lower().strip() for s in (cog_prof.get("generic_soft_skills", []) if cog_prof else []))
        matched_core_skills = [s for s in matched_skills if s.lower().strip() not in profile_soft_skills]

        # Require at least 2 distinct core domain skills to award points
        if len(matched_core_skills) >= 6:
            skill_score = 45
        elif len(matched_core_skills) >= 4:
            skill_score = 35
        elif len(matched_core_skills) >= 2:
            skill_score = 20
        else:
            skill_score = 0

        # Component C: Experience & Seniority Compatibility (0 - 20 points)
        if exp_matches:
            min_e = float(exp_matches[0][0])
            max_e = float(exp_matches[0][1]) if exp_matches[0][1] else min_e + 3
            if min_e - 1 <= cand_exp <= max_e + 2:
                exp_score = 20
            elif cand_exp >= min_e - 2:
                exp_score = 10
            else:
                exp_score = 0
        else:
            exp_score = 10

        total_score = max(0, min(title_score + skill_score + exp_score, 100))

        if total_score >= 60:
            reasoning = (
                f"Qualified fit ({total_score}%): Title score {title_score}/35, "
                f"matched {len(matched_core_skills)} core skills ({skill_score}/45), exp fit {exp_score}/20."
            )
        else:
            reasoning = (
                f"Rejected fit ({total_score}% < 60% threshold): Insufficient domain/skill density for '{job_title}'. "
                f"Matched {len(matched_core_skills)} core skills ({skill_score}/45), title score {title_score}/35."
            )

        return MatchResult(
            score=total_score,
            reasoning=reasoning,
            matching_skills=matched_skills[:8],
            missing_skills=missing_skills[:5]
        )

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
        Resolves recruiter screening questions by:
        1. Checking strict exact-match cached answers (auto_learned_truths & ats_answers).
        2. Routing unlearned questions to the AG 2.0 File-Based IPC protocol.
        3. Persisting verified answers atomically back to candidate_config.json.
        """
        profile = candidate_profile or (self.profile_context.config if self.profile_context else {})
        cand = profile.get("candidate", {})
        learned = profile.get("auto_learned_truths", {})
        ats = profile.get("ats_answers", {})

        q_clean = question.strip()
        q_lower = q_clean.lower()

        # Step 1: Strict EXACT MATCH check from previous agent answers (Directive 3.5)
        for k, v in learned.items():
            if k.strip().lower() == q_lower:
                val = str(v).strip()
                if options:
                    matched_opt = self._best_option_match(val, options)
                    if matched_opt:
                        return matched_opt
                return val

        for k, v in ats.items():
            if k.strip().lower() == q_lower:
                val = str(v).strip()
                if options:
                    matched_opt = self._best_option_match(val, options)
                    if matched_opt:
                        return matched_opt
                return val

        # Step 2: Route dynamically to AG 2.0 IPC Handshake
        resume_md = resume_text or ""
        if not resume_md and self.profile_context and hasattr(self.profile_context, "resume_text"):
            resume_md = self.profile_context.resume_text

        prompt = f"""You are answering an official recruiter screening questionnaire on behalf of the candidate.
CANDIDATE PROFILE DATA (FACTUAL SOURCE OF TRUTH):
{json.dumps(cand, indent=2)}

CANDIDATE MASTER RESUME:
{resume_md[:3500]}

RECRUITER QUESTION:
"{q_clean}"

CONTROL TYPE:
{control_type or 'CONTENTEDITABLE'}

AVAILABLE CHOICES (IF APPLICABLE):
{json.dumps(options, indent=2) if options else 'None (Provide direct concise factual text or numeric value. Maximum 250 characters.)'}

INSTRUCTIONS:
1. Examine the candidate resume and profile data carefully for the specific skill, tool, process, or domain requested.
2. If choices/options are provided, your answer MUST match one of the available choices EXACTLY verbatim.
3. If the question asks for years of experience in a specific skill or process:
   - Calculate how many years the candidate actually practiced that specific skill based on their employment history.
   - If the candidate DOES NOT have experience in that specific skill/process in their resume, answer '0'.
   - DO NOT default to their total career experience unless the question explicitly asks for overall/total experience.
4. Provide a strictly truthful, factual answer based ONLY on the provided candidate context. Keep answers under 250 characters. Do not invent or guess.
5. Output STRICTLY the final answer string with zero conversational preamble."""

        # Dispatch to File IPC for AG 2.0 to resolve
        answer = self._fallback_antigravity_ipc(
            prompt=prompt,
            question=q_clean,
            options=options,
            control_type=control_type,
            max_characters=250,
            task_type="QUESTIONNAIRE"
        )

        if options:
            best_opt = self._best_option_match(answer, options)
            if best_opt:
                answer = best_opt

        if not options and len(answer) > 250:
            answer = answer[:250].strip()

        # Persist truthful answer to auto_learned_truths
        if answer:
            self._persist_learned_truth(q_clean, answer)

        return answer

    def _best_option_match(self, target: str, options: List[str]) -> Optional[str]:
        """
        Maps a target value to the best matching option in options list.
        H1 Fix: Returns None if no match is found (never blindly falls back to options[0]).
        H2 Fix: Uses word-boundary matching to prevent substring collision.
        """
        if not options or not target:
            return None

        target_clean = target.lower().strip()

        # 1. Exact string match (case-insensitive)
        for opt in options:
            if opt.lower().strip() == target_clean:
                return opt

        # 2. H2 Word-boundary match
        for opt in options:
            if re.search(rf'\b{re.escape(target_clean)}\b', opt.lower().strip()):
                return opt

        # 3. Numeric extraction match
        nums = re.findall(r"\d+", target_clean)
        if nums:
            target_num = nums[0]
            for opt in options:
                opt_nums = re.findall(r"\d+", opt)
                if target_num in opt_nums:
                    return opt

        # 4. Boolean normalization
        if target_clean in ["yes", "true", "y"]:
            for opt in options:
                if re.search(r'\byes\b', opt.lower()):
                    return opt
        elif target_clean in ["no", "false", "n"]:
            for opt in options:
                if re.search(r'\bno\b', opt.lower()):
                    return opt

        return None

    def _persist_learned_truth(self, question: str, answer: str):
        """Caches novel verified Q&A entries atomically to candidate_config.json."""
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
                print(f"[AI BRAIN] Warning: Could not persist learned truth: {e}", flush=True)

    def _fallback_antigravity_ipc(
        self,
        prompt: str,
        question: str,
        options: Optional[List[str]] = None,
        control_type: Optional[str] = None,
        max_characters: Optional[int] = None,
        task_type: str = "QUESTIONNAIRE",
        payload_extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Universal File-Based IPC Handshake Protocol optimized strictly for Antigravity 2.0.
        Never freezes on terminal stdin (Guardrail H6). Endlessly polls pending_question.json
        until Antigravity 2.0 fills the answer key.
        Supports QUESTIONNAIRE, JOB_EVALUATION, PROFILE_SYNTHESIS, and RESUME_TAILORING tasks.
        """
        output_dir = getattr(self.profile_context, "output_dir", Path("."))
        output_dir.mkdir(parents=True, exist_ok=True)
        ipc_file = output_dir / "pending_question.json"

        resolved_max_chars = max_characters
        if resolved_max_chars is None and (options or control_type in ["CONTENTEDITABLE", "RADIO_CHIP", "DROPDOWN"]):
            resolved_max_chars = 250

        ipc_payload = {
            "status": "PENDING",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "task_type": task_type,
            "question": question,
            "options": options,
            "control_type": control_type or ("CONTENTEDITABLE" if task_type == "QUESTIONNAIRE" else "TEXT"),
            "max_characters": resolved_max_chars,
            "prompt": prompt.strip(),
            "answer": ""
        }

        if payload_extra and isinstance(payload_extra, dict):
            ipc_payload.update(payload_extra)

        try:
            with open(ipc_file, "w", encoding="utf-8") as f:
                json.dump(ipc_payload, f, indent=2)
        except Exception as e:
            print(f"[ERROR] IPC Write Failed: {e}", flush=True)

        print("\n" + "=" * 70, flush=True)
        print(f"[AG 2.0 COGNITIVE IPC] AWAITING AG 2.0 RESOLUTION: {task_type}", flush=True)
        print("=" * 70, flush=True)
        print(f"TASK / QUESTION: {question}", flush=True)
        if options:
            print(f"CHOICES:         {options}", flush=True)
        print(f"IPC FILE:        {ipc_file.resolve()}", flush=True)
        print("-" * 70, flush=True)
        print(">> AG Brain: Please write the answer to the 'answer' key in pending_question.json.", flush=True)

        while True:
            time.sleep(0.5)
            if ipc_file.exists():
                try:
                    with open(ipc_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    ans = str(data.get("answer", "")).strip()
                    if ans:
                        preview = ans if len(ans) <= 80 else ans[:80] + "..."
                        print(f"\n[AG 2.0 IPC] Answer received from AG: '{preview}'", flush=True)
                        try:
                            ipc_file.unlink()
                        except Exception:
                            pass
                        if resolved_max_chars and len(ans) > resolved_max_chars:
                            ans = ans[:resolved_max_chars].strip()
                        return ans
                except Exception:
                    # File is being written to by AG, pass to next poll tick
                    pass

    def arbitrate_card_fit(
        self,
        title: str,
        card_skills: list = None,
        exp_text: str = "",
        candidate_profile: dict = None
    ) -> tuple[bool, str]:
        """
        Tier 2B Cognitive Card Arbitration:
        Evaluates whether an unfamiliar, abbreviated, or creative job role seen on the
        search results page conceptually aligns with the candidate's domain, skills,
        and experience tier.
        Returns (is_relevant: bool, reasoning: str).
        """
        profile = candidate_profile or (self.profile_context.config if self.profile_context else {})
        cand = profile.get("candidate", {})
        cand_exp = float(cand.get("total_experience_years", 0) or 0)
        skills_dict = profile.get("taxonomy_skills", {})
        all_skills = [s.lower() for s in skills_dict.keys()]
        for v in skills_dict.values():
            if isinstance(v, list):
                all_skills.extend([s.lower() for s in v if isinstance(s, str)])
            elif isinstance(v, dict):
                all_skills.extend([s.lower() for s in v.keys() if isinstance(s, str)])

        target_jobs = profile.get("target_jobs", {})
        negative_keywords = [k.lower().strip() for k in (target_jobs.get("negative_keywords") or []) if k and k.strip()]

        title_lower = title.lower().strip()
        card_skills_lower = [s.lower().strip() for s in (card_skills or [])]

        # 1. Hard check: Negative keywords are absolute (C6 Guardrail)
        for neg in negative_keywords:
            if re.search(rf'\b{re.escape(neg)}\b', title_lower):
                return False, f"Negative keyword '{neg}' in card title (C6 Guardrail)."

        # 2. Check card skills against candidate skills
        matching_card_skills = []
        for cs in card_skills_lower:
            for cand_s in all_skills:
                if cs == cand_s or (len(cs) >= 4 and len(cand_s) >= 4 and (cs in cand_s or cand_s in cs)):
                    matching_card_skills.append(cs)
                    break

        if matching_card_skills:
            return True, f"Card skills match candidate taxonomy: {', '.join(matching_card_skills[:3])}"

        # 3. Domain abbreviations and technical role mapping
        cog_prof = self.profile_context.load_cognitive_profile() if self.profile_context else None
        if not cog_prof and self.profile_context:
            cog_prof = self.synthesize_cognitive_profile()

        domain_acronyms = cog_prof.get("domain_acronyms", {}) if cog_prof else {}
        cand_domain = cog_prof.get("candidate_domain", "Candidate Domain") if cog_prof else "Candidate Domain"
        incompatible_verticals = cog_prof.get("incompatible_verticals", {}) if cog_prof else {}

        words = re.findall(r'[a-zA-Z0-9&]+', title_lower)
        for w in words:
            if w in domain_acronyms:
                return True, f"Domain acronym '{w.upper()}' ({domain_acronyms[w]}) matches candidate domain."

        # 4. Check for obvious incompatible verticals in title
        for vert_name, vert_markers in incompatible_verticals.items():
            for bad_kw in vert_markers[:6]:
                if re.search(rf'\b{re.escape(bad_kw)}\b', title_lower):
                    cand_domain_tokens = [w for w in re.split(r'[\s/,-]+', cand_domain.lower()) if len(w) > 3]
                    has_domain = any(re.search(rf'\b{re.escape(d)}\b', title_lower) for d in cand_domain_tokens)
                    if not has_domain:
                        return False, f"Card title belongs to incompatible vertical '{vert_name}' without {cand_domain} function."

        # 5. Token stem matching against target keywords
        target_keywords = [k.lower().strip() for k in (target_jobs.get("keywords") or []) if k and k.strip()]
        recommended_titles = [t.lower().strip() for t in (target_jobs.get("recommended_titles") or []) if t and t.strip()]
        all_targets = target_keywords + recommended_titles

        LEVEL_STOPWORDS = {
            "executive", "manager", "officer", "associate", "specialist", "lead",
            "senior", "junior", "assistant", "deputy", "head", "director", "vp",
            "intern", "trainee", "consultant", "professional", "staff", "principal",
            "expert", "coordinator", "representative", "analyst", "general", "group",
            "team", "operations", "service", "services", "backend", "frontend", "sr", "jr"
        }

        for target in all_targets:
            target_tokens = [t for t in re.split(r'[\s/,-]+', target) if len(t) >= 4 and t not in LEVEL_STOPWORDS]
            if not target_tokens:
                continue
            for tt in target_tokens:
                for w in words:
                    if w not in LEVEL_STOPWORDS and len(w) >= 4 and (w.startswith(tt[:5]) or tt.startswith(w[:5])):
                        return True, f"Stem match between title domain token '{w}' and target token '{tt}'."

        return False, f"Title '{title}' does not match candidate domain, skills, or target keywords."

    def analyze_and_expand_designations(
        self,
        resume_text: str,
        candidate_exp: float,
        current_keywords: list,
        market_seen_titles: list = None
    ) -> list[str]:
        """
        Tier 4 Autonomous Starvation Recovery:
        Inspects resume, actual years of experience, and observed portal titles
        to infer 5-8 high-yield designations matching candidate seniority tier.
        """
        market_titles_sample = list(market_seen_titles or [])[:25]
        cog_prof = self.profile_context.load_cognitive_profile() if self.profile_context else None
        if not cog_prof and self.profile_context:
            cog_prof = self.synthesize_cognitive_profile()
        cand_domain = cog_prof.get("candidate_domain", "Candidate Domain") if cog_prof else "Candidate Domain"
        core_skills = cog_prof.get("core_domain_skills", []) if cog_prof else []

        prompt = f"""You are an executive career strategist.
A candidate with {candidate_exp} years of total experience in {cand_domain} yielded 0 results or had narrow search keywords.
Candidate Resume Excerpt:
{resume_text[:2000] if resume_text else cand_domain}

Current Search Keywords: {current_keywords}
Sample Titles Seen on Portal:
{market_titles_sample}

Generate a list of 6 to 10 high-yield, senior-level Job Titles / Designations that strictly match:
1. The candidate's {candidate_exp} years seniority tier (e.g., Senior, Lead, Assistant Manager, Specialist level).
2. The candidate's primary domain ({cand_domain}).
3. Standard portal search designations used on Naukri and LinkedIn.

Respond with ONLY a JSON array of title strings:
["Title 1", "Title 2", ...]"""

        raw = self.generate_text(prompt=prompt, task_type="STARVATION_EXPANSION")
        if raw:
            try:
                match = re.search(r'\[\s*".*?"\s*\]', raw, re.DOTALL)
                if match:
                    titles = json.loads(match.group(0))
                    cleaned = [str(t).strip() for t in titles if isinstance(t, str) and len(t.strip()) > 3]
                    if len(cleaned) >= 3:
                        return cleaned
            except Exception:
                pass

        # Dynamic rule-based seniority expansion fallback
        manager_level = "Assistant Manager" if candidate_exp >= 7.0 else "Executive"
        lead_level = "Lead" if candidate_exp >= 8.0 else "Specialist"
        senior_prefix = "Senior" if candidate_exp >= 4.0 else ""

        fallback_expanded = []
        for kw in current_keywords[:5]:
            clean_kw = re.sub(r'\b(Senior|Lead|Assistant Manager|Executive)\b', '', kw, flags=re.IGNORECASE).strip("- ")
            if clean_kw:
                if candidate_exp >= 7.0:
                    fallback_expanded.append(f"{manager_level} - {clean_kw}")
                    fallback_expanded.append(f"{lead_level} {clean_kw}")
                if senior_prefix:
                    fallback_expanded.append(f"{senior_prefix} {clean_kw}")

        for skill in core_skills[:4]:
            if len(skill.split()) <= 3:
                fallback_expanded.append(f"{senior_prefix} {skill} Specialist".strip())

        cur_set = set(str(k).lower().strip() for k in current_keywords)
        seen_expanded = set()
        result = []
        for t in fallback_expanded:
            t_clean = t.strip()
            if t_clean.lower() not in cur_set and t_clean.lower() not in seen_expanded:
                seen_expanded.add(t_clean.lower())
                result.append(t_clean)
        return result[:10]
