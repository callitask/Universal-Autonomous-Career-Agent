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
    Autonomous Reasoning Engine for Dynamic Screening Questionnaire Resolution
    and Factual Candidate Job Scoring.
    Zero-hardcoding: resolves everything from ProfileContext at runtime.
    Relies entirely on AG 2.0 File-Based IPC. No API Key required.
    """
    def __init__(self, profile_context=None):
        self.profile_context = profile_context

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
        Evaluates job suitability locally with 0-baseline multi-factor scoring:
        - Absolute Negative Keyword Exclusion (C6 Guardrail)
        - Title & Domain Alignment (0-40 pts)
        - Factual Skill Match via Word-Boundary Regex (0-40 pts)
        - Experience & Seniority Compatibility (0-20 pts)
        """
        profile = candidate_profile or (self.profile_context.config if self.profile_context else {})
        cand = profile.get("candidate", {})
        skills_dict = profile.get("taxonomy_skills", {})
        target_jobs = profile.get("target_jobs", {})

        title_lower = job_title.lower().strip()
        desc_lower = job_description.lower().strip()

        negative_keywords = [k.lower().strip() for k in target_jobs.get("negative_keywords", []) if k.strip()]
        target_keywords = [k.lower().strip() for k in target_jobs.get("keywords", []) if k.strip()]
        recommended_titles = [t.lower().strip() for t in target_jobs.get("recommended_titles", []) if t.strip()]

        # 1. C6 Check: Negative Keywords are Absolute
        for neg in negative_keywords:
            if re.search(rf'\b{re.escape(neg)}\b', title_lower):
                return MatchResult(
                    score=0,
                    reasoning=f"Job '{job_title}' rejected due to explicit negative keyword match: '{neg}'.",
                    matching_skills=[],
                    missing_skills=["Target domain alignment"]
                )

        # Flatten candidate skills from config
        flat_skills = []
        for cat_skills in skills_dict.values():
            if isinstance(cat_skills, list):
                flat_skills.extend([s.strip() for s in cat_skills if s.strip()])
            elif isinstance(cat_skills, str):
                flat_skills.append(cat_skills.strip())

        # Also extract any distinct capitalized skill names or tech tags from resume_text
        resume_md = resume_text or (self.profile_context.resume_text if self.profile_context else "")
        if resume_md and not flat_skills:
            words = re.findall(r'[A-Za-z0-9#+.\-]+', resume_md)
            flat_skills = list(set([w for w in words if len(w) > 3]))

        # Deduplicate skills
        unique_skills = []
        seen_skills = set()
        for s in flat_skills:
            if s.lower() not in seen_skills:
                seen_skills.add(s.lower())
                unique_skills.append(s)

        # 2. Title & Role Alignment (0 - 40 points)
        title_score = 0
        all_targets = target_keywords + recommended_titles
        clean_cand_title = cand.get("current_title", "").lower().strip()
        if clean_cand_title:
            all_targets.append(clean_cand_title)

        matched_target_phrase = False
        for target in all_targets:
            target_clean = target.lower().strip()
            if not target_clean:
                continue
            # Exact or full-phrase match in title
            if re.search(rf'\b{re.escape(target_clean)}\b', title_lower):
                title_score = 40
                matched_target_phrase = True
                break

        if not matched_target_phrase:
            # Token-level overlap
            domain_tokens = set()
            for t in all_targets:
                for token in re.split(r'[\s/,-]+', t.lower()):
                    if len(token) > 2 and token not in ["and", "for", "the", "with", "lead", "senior", "junior", "manager", "executive", "officer", "associate", "specialist"]:
                        domain_tokens.add(token)

            title_tokens = [tok for tok in re.split(r'[\s/,-]+', title_lower) if len(tok) > 2]
            matched_tokens = [tok for tok in title_tokens if tok in domain_tokens]

            if len(matched_tokens) >= 2:
                title_score = 30
            elif len(matched_tokens) == 1:
                title_score = 20
            else:
                title_score = 0

        # 3. Factual Skill Match via Word-Boundary Regex (0 - 40 points)
        matched_skills = []
        missing_skills = []
        for s in unique_skills:
            s_clean = s.strip()
            if re.search(rf'\b{re.escape(s_clean.lower())}\b', desc_lower):
                matched_skills.append(s_clean)
            else:
                missing_skills.append(s_clean)

        if len(matched_skills) >= 6:
            skill_score = 40
        elif len(matched_skills) >= 4:
            skill_score = 30
        elif len(matched_skills) >= 2:
            skill_score = 20
        elif len(matched_skills) >= 1:
            skill_score = 10
        else:
            skill_score = 0

        # 4. Experience & Domain Alignment (0 - 20 points)
        exp_score = 0
        cand_exp = float(cand.get("total_experience_years", target_jobs.get("experience_years", 0)) or 0)
        exp_matches = re.findall(r'(\d+)\s*(?:-\s*(\d+))?\s*(?:years?|yrs?)', desc_lower)

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

        # Total Calculation (0 - 100)
        total_score = title_score + skill_score + exp_score
        total_score = max(0, min(total_score, 100))

        # Build reasoning
        if total_score >= 40:
            reasoning = f"Qualified fit ({total_score}%): Title score {title_score}/40, matched {len(matched_skills)} core skills ({skill_score}/40), exp fit {exp_score}/20."
        else:
            reasoning = f"Rejected fit ({total_score}%): Insufficient domain/skill alignment for '{job_title}'. Matched only {len(matched_skills)} skills."

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
            control_type=control_type
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
        control_type: Optional[str] = None
    ) -> str:
        """
        File-Based IPC Handshake Protocol optimized strictly for AG 2.0.
        Never freezes on terminal stdin. Endlessly polls pending_question.json until AG fills the file.
        """
        output_dir = getattr(self.profile_context, "output_dir", Path("."))
        output_dir.mkdir(parents=True, exist_ok=True)
        ipc_file = output_dir / "pending_question.json"

        ipc_payload = {
            "status": "PENDING",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "options": options,
            "control_type": control_type or "CONTENTEDITABLE",
            "max_characters": 250,
            "prompt": prompt.strip(),
            "answer": ""
        }

        try:
            with open(ipc_file, "w", encoding="utf-8") as f:
                json.dump(ipc_payload, f, indent=2)
        except Exception as e:
            print(f"[ERROR] IPC Write Failed: {e}", flush=True)

        print("\n" + "=" * 70, flush=True)
        print(f"[AG 2.0 IPC] WAITING FOR AG TO RESOLVE QUESTIONNAIRE", flush=True)
        print("=" * 70, flush=True)
        print(f"QUESTION:     {question}", flush=True)
        print(f"CONTROL TYPE: {control_type or 'CONTENTEDITABLE'}", flush=True)
        if options:
            print(f"CHOICES:      {options}", flush=True)
        print(f"IPC FILE:     {ipc_file.resolve()}", flush=True)
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
                        print(f"\n[AG 2.0 IPC] Answer received from AG: '{ans}'", flush=True)
                        try:
                            ipc_file.unlink()
                        except Exception:
                            pass
                        return ans
                except Exception:
                    # File is being written to by AG, pass to next poll tick
                    pass