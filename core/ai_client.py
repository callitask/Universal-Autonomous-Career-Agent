"""
================================================================================
UNIVERSAL AUTONOMOUS CAREER AGENT - AI CLIENT & REASONING BRAIN
File: core/ai_client.py
================================================================================
Profile-agnostic AI engine operating with zero hardcoded candidate parameters.
Features File-Based IPC (pending_question.json) for Antigravity 2.0 autonomous
handshake. Completely removes terminal blocking.
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


class AIClient:
    """
    Autonomous Reasoning Engine for Dynamic Screening Questionnaire Resolution.
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
        Evaluates job suitability locally without external API dependencies.
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
        Routes the question to the file-based IPC for AG 2.0 to resolve.
        Checks exact-match cache first to avoid asking AG the same question twice.
        """
        profile = candidate_profile or (self.profile_context.config if self.profile_context else {})
        cand = profile.get("candidate", {})
        learned = profile.get("auto_learned_truths", {})
        ats = profile.get("ats_answers", {})
        
        q_clean = question.strip()
        q_lower = q_clean.lower()

        # Step 1: Strict EXACT MATCH check from previous agent answers
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

        # Step 2: Route dynamically to AG 2.0 IPC
        resume_md = resume_text or ""
        if not resume_md and self.profile_context and hasattr(self.profile_context, "resume_text"):
            resume_md = self.profile_context.resume_text

        prompt = f"""
You are answering an official recruiter screening questionnaire on behalf of the candidate.

CANDIDATE PROFILE DATA (FACTUAL SOURCE OF TRUTH):
{json.dumps(cand, indent=2)}

CANDIDATE MASTER RESUME:
{resume_md[:3000]}

RECRUITER QUESTION: "{q_clean}"
AVAILABLE CHOICES (IF APPLICABLE): {json.dumps(options) if options else 'None (Provide direct concise factual text or numeric value. Maximum 250 characters.)'}

INSTRUCTIONS:
1. Examine the candidate's resume and profile data carefully for the specific skill, tool, process, or domain requested.
2. If the question asks for years of experience in a specific skill or process:
   - Calculate how many years the candidate actually practiced that specific skill based on their employment history.
   - If the candidate DOES NOT have experience in that specific skill/process in their resume, answer '0'.
   - DO NOT default to their total career experience unless the question explicitly asks for overall/total experience.
3. Provide a strictly truthful, factual answer based ONLY on the provided candidate context. Keep answers under 250 characters. Do not invent or guess.
4. If choices are provided, return EXACTLY one option string verbatim from the list.
5. Output STRICTLY the final answer string with zero conversational preamble.
"""
        
        # Dispatch to File IPC for AG 2.0 to resolve
        answer = self._fallback_antigravity_ipc(prompt=prompt, question=q_clean, options=options, control_type=control_type)

        if options:
            best_opt = self._best_option_match(answer, options)
            if best_opt:
                answer = best_opt
            else:
                answer = self._best_option_match(answer, options) or options[0]

        if not options and len(answer) > 250:
            answer = answer[:250].strip()

        self._persist_learned_truth(q_clean, answer)
        return answer

    def _best_option_match(self, target: str, options: List[str]) -> Optional[str]:
        if not options:
            return None
        target_clean = target.lower().strip()
        
        for opt in options:
            if opt.lower().strip() == target_clean:
                return opt

        for opt in options:
            if re.search(rf'\b{re.escape(target_clean)}\b', opt.lower().strip()):
                return opt

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
        if self.profile_context and answer:
            try:
                if "auto_learned_truths" not in self.profile_context.config:
                    self.profile_context.config["auto_learned_truths"] = {}
                clean_q = question.strip()
                if clean_q:
                    self.profile_context.config["auto_learned_truths"][clean_q] = answer
                    if hasattr(self.profile_context, "save_config"):
                        self.profile_context.save_config()
            except Exception:
                pass

    def _fallback_antigravity_ipc(self, prompt: str, question: str, options: Optional[List[str]] = None, control_type: Optional[str] = None) -> str:
        """
        File-Based IPC Handshake Protocol optimized strictly for AG 2.0.
        Never freezes on terminal stdin. Endlessly polls until AG fills the file.
        """
        output_dir = getattr(self.profile_context, "output_dir", Path("."))
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
        print(f"QUESTION: {question}", flush=True)
        if options:
            print(f"CHOICES:  {options}", flush=True)
        print(f"IPC FILE: {ipc_file.resolve()}", flush=True)
        print("-" * 70, flush=True)
        print(">> AG Brain: Please write the answer to the 'answer' key in pending_question.json.", flush=True)

        while True:
            time.sleep(1.0)
            if ipc_file.exists():
                try:
                    with open(ipc_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # IF AG 2.0 WRITES ANY ANSWER, PROCEED IMMEDIATELY
                    ans = str(data.get("answer", "")).strip()
                    if ans:
                        print(f"\n[AG 2.0 IPC] Answer received from AG: '{ans}'", flush=True)
                        try:
                            ipc_file.unlink()
                        except Exception:
                            pass
                        return ans
                except Exception:
                    # Ignore JSON decode errors if AG is actively writing to the file
                    pass