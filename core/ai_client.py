"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT - AI CLIENT & REASONING BRAIN
File: core/ai_client.py
================================================================================
Profile-agnostic AI engine operating with zero hardcoded candidate parameters.
Features File-Based IPC (pending_question.json) for Antigravity 2.0 autonomous handshake.
Completely removes terminal blocking (input/stdin).
Zero-baseline evaluation engine to strictly prevent irrelevant job matching.
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
    Factual Candidate Job Scoring, and General Text Generation Tasks.
    Zero-hardcoding: resolves everything from ProfileContext at runtime.
    Relies on AG 2.0 File-Based IPC as primary brain; uses Gemini API if available.
    Zero terminal stdin blocking.
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

        # 2. File-Based IPC Handshake for Antigravity 2.0 / AI Assistant
        ipc_res = self._fallback_antigravity_ipc(
            prompt=prompt,
            question=kwargs.get("question", prompt.split("\n")[0][:120].strip()),
            options=kwargs.get("options", None),
            control_type=kwargs.get("control_type", "TEXT"),
            max_characters=kwargs.get("max_characters", None)
        )

        if ipc_res and ipc_res.strip():
            return ipc_res.strip()

        return default_fallback

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
          - Experience Band Filter (gap > 3 years auto-rejects)
        Stage 2: Precision Semantic & Factual Scoring (Dual-Brain + Local Fallback)
          - Operational Gemini Client Evaluation (0-100 JSON)
          - Ambiguous Score IPC Handshake (40-65) if enabled
          - High-Precision Local Heuristics (0-35 Title, 0-45 Skills [min 2], 0-20 Exp)
          - 60% Qualification Bar (eliminates 40% false positives)
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

        # 1.2 Domain Title Alignment: Gating out out-of-domain roles (e.g. Software Engineer for Accountant)
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
            "general", "global", "regional", "assistant", "deputy", "group", "team"
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

        # 1.3 Experience Band Filter: Reject if JD minimum experience exceeds candidate by > 3 years
        cand_exp = float(cand.get("total_experience_years", target_jobs.get("experience_years", 0)) or 0)
        exp_matches = re.findall(r'(\d+)\s*(?:-\s*(\d+))?\s*(?:years?|yrs?)(?:\s*(?:of)?\s*(?:experience|exp))?', desc_lower)

        if exp_matches:
            min_req_exp = float(exp_matches[0][0])
            if min_req_exp > cand_exp + 3:
                return MatchResult(
                    score=0,
                    reasoning=f"Rejected: Experience gap too wide for '{job_title}'. Role requires minimum {int(min_req_exp)} years, but candidate has {cand_exp} years (exceeds +3 year limit).",
                    matching_skills=[],
                    missing_skills=[f"Minimum {int(min_req_exp)} years experience"]
                )

        # =========================================================================
        # STAGE 2: PRECISION SEMANTIC & FACTUAL SCORING
        # =========================================================================

        # Flatten candidate taxonomy skills and resume skills
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

        # 2.1 Dual-Brain LLM Route (If Gemini API is initialized and operational)
        if self.gemini_client:
            try:
                llm_prompt = f"""
You are an expert technical recruiter evaluating whether a candidate is genuinely qualified for a job.
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
2. Factual Skill Match (0-45 points, require real overlap with candidate's actual skills)
3. Experience & Seniority Compatibility (0-20 points)
4. Passing threshold is strictly 60 points. A score below 60 means candidate should NOT apply.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object:
{{
  "score": <integer 0-100>,
  "reasoning": "<concise 1-2 sentence explanation>",
  "matching_skills": ["<skill1>", "<skill2>"],
  "missing_skills": ["<skill1>", "<skill2>"]
}}
"""
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
                print(f"[AI CLIENT] Gemini evaluation unavailable ({e}). Proceeding with deterministic engine.", flush=True)

        # 2.2 Deterministic Factual Scoring (Heuristic Engine)
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
        # Strict requirement: Require at least 2 distinct skill matches to award any skill points
        if len(matched_skills) >= 6:
            skill_score = 45
        elif len(matched_skills) >= 4:
            skill_score = 35
        elif len(matched_skills) >= 2:
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

        # 2.3 Antigravity 2.0 IPC Handshake for Ambiguous Scores (40 - 65) if enabled
        enable_ipc_eval = kwargs.get("enable_ipc") or kwargs.get("use_ipc") or profile.get("candidate", {}).get("ipc_job_evaluation", False)
        if (40 <= total_score <= 65) and enable_ipc_eval:
            ipc_prompt = f"""
Evaluate job suitability for candidate.
JOB TITLE: {job_title}
CANDIDATE CURRENT TITLE: {cand.get('current_title', '')}
TOTAL EXPERIENCE: {cand_exp} years
MATCHED SKILLS: {matched_skills}
JOB DESCRIPTION:
{job_description[:2000]}

Score from 0 to 100 in strict JSON:
{{"score": <int>, "reasoning": "<str>", "matching_skills": [<str>], "missing_skills": [<str>]}}
"""
            ipc_res = self._fallback_antigravity_ipc(
                prompt=ipc_prompt,
                question=f"Evaluate job match for: {job_title}",
                control_type="JSON",
                max_characters=1000
            )
            parsed_ipc = self._parse_json_match_result(ipc_res)
            if parsed_ipc:
                return parsed_ipc

        # 2.4 Final Qualification Bar: >= 60% required to qualify
        if total_score >= 60:
            reasoning = (
                f"Qualified fit ({total_score}%): Title score {title_score}/35, "
                f"matched {len(matched_skills)} core skills ({skill_score}/45), exp fit {exp_score}/20."
            )
        else:
            reasoning = (
                f"Rejected fit ({total_score}% < 60% threshold): Insufficient domain/skill density for '{job_title}'. "
                f"Matched {len(matched_skills)} skills ({skill_score}/45), title score {title_score}/35."
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
        Resolves screening questions by:
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

        prompt = f"""
You are answering an official recruiter screening questionnaire on behalf of the candidate.
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
1. Examine the candidate's resume and profile data carefully for the specific skill, tool, process, or domain requested.
2. If choices/options are provided, your answer MUST match one of the available choices EXACTLY verbatim.
3. If the question asks for years of experience in a specific skill or process:
   - Calculate how many years the candidate actually practiced that specific skill based on their employment history.
   - If the candidate DOES NOT have experience in that specific skill/process in their resume, answer '0'.
   - DO NOT default to their total career experience unless the question explicitly asks for overall/total experience.
4. Provide a strictly truthful, factual answer based ONLY on the provided candidate context. Keep answers under 250 characters. Do not invent or guess.
5. Output STRICTLY the final answer string with zero conversational preamble.
"""
        # Dispatch to File IPC for AG 2.0 to resolve
        answer = self._fallback_antigravity_ipc(
            prompt=prompt,
            question=q_clean,
            options=options,
            control_type=control_type,
            max_characters=250
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

        # Return None if no safe match exists (H1 Guardrail Compliance)
        return None

    def _persist_learned_truth(self, question: str, answer: str):
        """
        Caches novel verified Q&A entries atomically to candidate_config.json.
        """
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
        max_characters: Optional[int] = None
    ) -> str:
        """
        File-Based IPC Handshake Protocol optimized strictly for AG 2.0.
        Never freezes on terminal stdin. Endlessly polls pending_question.json until AG fills the file.
        Supports both questionnaire items and arbitrary text generation tasks (profile summaries, ATS bullets).
        """
        output_dir = getattr(self.profile_context, "output_dir", Path("."))
        output_dir.mkdir(parents=True, exist_ok=True)
        ipc_file = output_dir / "pending_question.json"

        resolved_max_chars = max_characters
        if resolved_max_chars is None and (options or control_type in ["CONTENTEDITABLE", "RADIO_CHIP", "DROPDOWN"]):
            resolved_max_chars = 250

        is_questionnaire = bool(options or control_type in ["CONTENTEDITABLE", "RADIO_CHIP", "DROPDOWN"])

        ipc_payload = {
            "status": "PENDING",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "task_type": "QUESTIONNAIRE" if is_questionnaire else "TEXT_GENERATION",
            "question": question,
            "options": options,
            "control_type": control_type or ("CONTENTEDITABLE" if is_questionnaire else "TEXT"),
            "max_characters": resolved_max_chars,
            "prompt": prompt.strip(),
            "answer": ""
        }

        try:
            with open(ipc_file, "w", encoding="utf-8") as f:
                json.dump(ipc_payload, f, indent=2)
        except Exception as e:
            print(f"[ERROR] IPC Write Failed: {e}", flush=True)

        task_label = "QUESTIONNAIRE RESOLUTION" if is_questionnaire else "TEXT GENERATION TASK"
        print("\n" + "=" * 70, flush=True)
        print(f"[AG 2.0 IPC] WAITING FOR AG TO RESOLVE {task_label}", flush=True)
        print("=" * 70, flush=True)
        print(f"TASK / QUESTION: {question}", flush=True)
        print(f"CONTROL TYPE:    {ipc_payload['control_type']}", flush=True)
        if options:
            print(f"CHOICES:         {options}", flush=True)
        if resolved_max_chars:
            print(f"MAX CHARS:       {resolved_max_chars}", flush=True)
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