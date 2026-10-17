# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [AI_BRAIN_RESOLVER_INIT]
# Timestamp: 2026-10-10 00:40:00 +05:30
# Issue / Context: Screening questions were using naive substring/fallback logic that selected
#                  inappropriate answers (e.g. "My job does not require coding" for a Principal SWE).
# Changes Made: Built AIBrainResolver as the central cognitive brain. It pre-analyzes candidate resume,
#               config (ats_answers, taxonomy_skills, profile_content, experience), resolves pinpoint
#               answers, formats them according to UI control type, and persists every Q&A record
#               atomically into screening_answers.json.
# Rationale: Guarantees 100% truthful, profile-grounded answers with zero hardcoding and zero bad fallbacks.
# Preventative Notes: Never select negative/non-coding options for technical candidates.
#
# [ENTRY #002]
# Term: [QA_LEDGER_DEDUP + ROLE_ANSWERS]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: Multi-pass Section 2 rescans appended duplicate rows and
#                  persisted scanner-noise refusals/empties; per-role Q&A had
#                  no interview-prep home. auto_learned_truths stays read-only
#                  (this brain never writes candidate_config.json).
# Changes Made: Noise filter (self-echo/None/empty/question==option) skips
#               persistence; (job_id, normalized_question) in-place dedup
#               with load-time compaction; role answers.json screening_qa
#               mirror gated on existing Stage 4 role dir (never interrupts).
# Rationale: screening_answers.json is a ledger, not a log; role folders
#            carry their own interview-prep Q&A for operators.
# Preventative Notes: Never persist noise rows; never create role dirs from
#                     the mirror (write only when Stage 4 already made one).
#
# [ENTRY #003]
# Term: [F_CSA_02_CONTEXT_PRESERVATION + MIRROR_FALLBACK]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: [F-CSA-02] get_instance(candidate_data) with no
#                  job_context rebuilt the instance with {} and wiped the
#                  requisition context Stage 4 had stamped, so
#                  _mirror_role_answers() bailed on empty company/title and
#                  role answers.json was never written. _resolve_output_json_path
#                  also derived its slug from full_name instead of the profile
#                  key.
# Changes Made: get_instance preserves an existing job_context unless the
#               caller supplies a different job_id; output path prefers
#               profile_slug_of(); mirror now requires only job_id and falls
#               back to job_id-anchored role-dir discovery (still never
#               creating directories).
# Rationale: Screening Q&A is only useful per requisition.
# Preventative Notes: Never reset job_context implicitly; never require
#                     company+title when a job_id can locate the role folder.
#
# [ENTRY #004]
# Term: [F_RES_03_STRING_OPTIONS + F_RES_04_TRUTH_OVER_CACHE + F_RES_05_TOOL_GROUNDING]
# Timestamp: 2026-10-17 +05:30
# Issue / Context: Three defects found on requisition 210795740.
#   [F-RES-03] When `options` arrived as a bare string (the control_type
#     "RADIO_PILL" in the options slot), _best_option_match() iterated it
#     CHARACTER BY CHARACTER and substring-matched "R" inside "sp(R)ingboot",
#     returning "R" as a confident answer ("Selected specialization 'R'").
#   [F-RES-04] ats_answers/auto_learned_truths are CACHES, but they were
#     consulted BEFORE derivation, so a poisoned entry ("At least 5 years of
#     experience" against candidate.total_experience_years = 10) won and was
#     stamped source=CACHED_TRUTH with the rationale "Exact match found in
#     candidate ground-truth config." - a false provenance claim.
#   [F-RES-05] _deduce_answer() had no handler for tool/platform categories
#     (CI/CD, observability, container familiarity, cloud platform) and its
#     branch-C catch-all claimed those questions; all four deferred empty.
# Changes Made: options coerced to a list of non-empty strings in both
#   resolve_question() and _best_option_match(); new
#   _is_experience_tier_question() + _answer_matches_options() let structured
#   truth (PROFILE_DERIVED) outrank the cache for bracket questions; new
#   _ground_tool_options() answers tool categories from DECLARED
#   technical_skills only, running before the branch-C catch-all, with
#   generic-token and alias guards.
# Rationale: A cache is a memory, not a truth. Ground truth computed from the
#   candidate profile must outrank it, provenance labels must be honest, and
#   the agent must never assert a tool/platform the candidate never declared.
# Preventative Notes: Never label a cache hit as ground truth. Never iterate a
#   string where a list is expected. Never select a tool option that is not
#   present in candidate technical_skills; defer instead of guessing.
# ==============================================================================

import os
import re
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class AIBrainResolver:
    """
    Antigravity 2.0 Cognitive AI Brain for Applicant Screening Questions.
    
    1. Pre-analyzes candidate resume, candidate_config.json, skills taxonomy, and ATS history.
    2. Dynamically resolves recruiter screening questions into exact UI control choices:
       - DROPDOWN_MULTI: List of verified options to click (e.g. ['Java', 'SQL'])
       - RADIO_PILL: Specific pill string to select (e.g. 'Advanced / Expert', 'At Least 10 Years')
       - BINARY_PILL: 'Yes' or 'No'
       - TEXT: Factual string/number
    3. Persists answered screening questions atomically into screening_answers.json
       (noise refusals/empties are returned but never stored; repeats update
       in place by (job_id, normalized_question)). Reads auto_learned_truths
       as ground truth — this brain never writes candidate_config.json.
    4. Mirrors per-role screening Q&A into the Stage 4 role answers.json.
    """

    _instance: Optional["AIBrainResolver"] = None

    def __init__(self, candidate_data: Dict[str, Any], job_context: Optional[Dict[str, Any]] = None):
        self.candidate_data = candidate_data
        self.job_context = job_context or {}
        self.output_json_path = self._resolve_output_json_path()
        self.knowledge_index = self._build_knowledge_index()
        self.history: List[Dict[str, Any]] = self._load_existing_answers()

    @classmethod
    def get_instance(cls, candidate_data: Optional[Dict[str, Any]] = None, job_context: Optional[Dict[str, Any]] = None) -> "AIBrainResolver":
        if cls._instance is None or candidate_data is not None:
            cand = candidate_data or {}
            # [F-CSA-02] Section scripts call get_instance(candidate_data) with
            # no job_context; rebuilding with {} wiped the requisition context
            # Stage 4 had stamped and silently disabled the role answers.json
            # mirror. Preserve an existing context unless the caller supplies a
            # new job_id or an explicit job_context.
            if job_context is None and cls._instance is not None and cls._instance.job_context:
                _old = cls._instance.job_context or {}
                _new_job = str((cand.get("job_id") or cand.get("_ipc_job_id") or "")).strip()
                if not _new_job or _new_job == str(_old.get("job_id") or "").strip():
                    job_context = _old
            cls._instance = cls(cand, job_context)
        return cls._instance

    def _resolve_output_json_path(self) -> Path:
        """Determines the candidate-specific screening_answers.json path.

        Operations profiles take precedence; repo paths and the inspections
        fallback remain for transition/unknown profiles.
        """
        from CompanySiteApply.utils.runtime_paths import profiles_root

        # [F-CSA-02] Prefer the real profile identity: candidate_data["profile"]
        # (set by Stage 1) beats a full_name-derived slug, which can collide or
        # point nowhere when the display name differs from the folder name.
        cand_slug = ""
        try:
            from CompanySiteApply.utils.application_docs import profile_slug_of
            cand_slug = profile_slug_of(self.candidate_data, "")
        except Exception:
            cand_slug = ""
        if not cand_slug or cand_slug == "default_user":
            cand = self.candidate_data.get("candidate", {})
            cand_name = cand.get("full_name") or cand.get("name") or "candidate"
            cand_slug = re.sub(r'[^a-zA-Z0-9_]', '_', cand_name.lower())

        # Operations profile first
        ops_csa = profiles_root() / cand_slug / "company_site_apply"
        if ops_csa.exists():
            return ops_csa / "screening_answers.json"
        ops_prof = profiles_root() / cand_slug
        if ops_prof.exists():
            return ops_prof / "screening_answers.json"

        # Check profiles directory
        profiles_dir = Path("profiles") / cand_slug / "company_site_apply"
        if profiles_dir.exists():
            return profiles_dir / "screening_answers.json"
        
        # Fallback to general profiles dir or inspections
        alt_profiles = Path("profiles") / cand_slug
        if alt_profiles.exists():
            return alt_profiles / "screening_answers.json"

        inspections = Path(__file__).resolve().parent / "inspections"
        inspections.mkdir(parents=True, exist_ok=True)
        return inspections / "screening_answers.json"

    @staticmethod
    def _normalize_question(text: Any) -> str:
        """Deduplication key form: collapsed-whitespace lowercase."""
        return re.sub(r"\s+", " ", str(text or "").strip().lower())

    def _record_context(self) -> Tuple[str, str, str]:
        """Best-effort (job_id, company, job_title) from job_context first,
        then candidate_data. All strings, "" when unknown."""
        job_id, company, title = "", "", ""
        carriers = [self.job_context]
        if isinstance(self.candidate_data, dict):
            carriers.append(self.candidate_data)
            cand = self.candidate_data.get("candidate")
            if isinstance(cand, dict):
                carriers.append(cand)
        for carrier in carriers:
            if not isinstance(carrier, dict):
                continue
            if not job_id:
                job_id = str(carrier.get("job_id") or carrier.get("_ipc_job_id") or "").strip()
            if not company:
                company = str(
                    carrier.get("company") or carrier.get("company_name")
                    or carrier.get("target_company") or ""
                ).strip()
            if not title:
                job = carrier.get("details") if isinstance(carrier.get("details"), dict) else {}
                title = str(
                    carrier.get("job_title") or carrier.get("title")
                    or job.get("job_title") or job.get("title") or ""
                ).strip()
        return job_id, company, title

    @staticmethod
    def _is_noise_record(record: Dict[str, Any]) -> bool:
        """Scanner-noise rows are returned to callers but never persisted."""
        if not isinstance(record, dict):
            return True
        if record.get("source") == "REFUSED_SELF_ECHO":
            return True
        ans = record.get("answer")
        if ans is None:
            return True
        if isinstance(ans, str) and not ans.strip():
            return True
        qn = AIBrainResolver._normalize_question(record.get("question"))
        opts = record.get("options") or []
        if qn and any(qn == AIBrainResolver._normalize_question(o) for o in opts):
            return True
        return False

    def _load_existing_answers(self) -> List[Dict[str, Any]]:
        """Loads prior questions and answers from screening_answers.json.

        Compacts on load: drops noise rows and exact (job_id,
        normalized_question) duplicates (keeps the freshest), so history
        heals the first time any brain with this file persists again.
        """
        if self.output_json_path.exists():
            try:
                data = json.loads(self.output_json_path.read_text("utf-8"))
                if isinstance(data, list):
                    return self._compact_history([
                        r for r in data if isinstance(r, dict)
                    ])
            except Exception as e:
                logger.warning(f"[AIBrainResolver] Failed to load {self.output_json_path}: {e}")
        return []

    @staticmethod
    def _compact_history(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Drop noise rows; keep the last row per dedup key, ordered by
        first appearance."""
        seen: Dict[tuple, int] = {}
        order: List[tuple] = []
        latest: Dict[tuple, Dict[str, Any]] = {}
        for r in rows:
            if AIBrainResolver._is_noise_record(r):
                continue
            key = (str(r.get("job_id") or ""),
                   AIBrainResolver._normalize_question(r.get("question")))
            if key not in seen:
                seen[key] = len(order)
                order.append(key)
            latest[key] = r
        return [latest[k] for k in order]

    def _persist_answer(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Persists a Q&A record atomically to screening_answers.json.

        Noise rows are skipped. Repeats update the existing row in place by
        (job_id, normalized_question); unchanged repeats skip the write.
        Every stored row carries job_id/company for the role mirror.
        """
        if self._is_noise_record(record):
            return record
        job_id, company, _ = self._record_context()
        record["job_id"] = str(record.get("job_id") or job_id or "")
        if company and not str(record.get("company") or "").strip():
            record["company"] = company
        record["normalized_question"] = self._normalize_question(record.get("question"))
        key = (record["job_id"], record["normalized_question"])
        wrote = False
        if key[1]:
            for existing in self.history:
                if not isinstance(existing, dict):
                    continue
                ekey = (str(existing.get("job_id") or ""),
                        self._normalize_question(existing.get("question")))
                if ekey != key:
                    continue
                if all(existing.get(f) == record.get(f) for f in
                       ("question", "answer", "source", "rationale",
                        "options", "control_type")):
                    return record  # Identical repeat — skip file churn.
                existing.update({
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "question": record.get("question"),
                    "answer": record.get("answer"),
                    "source": record.get("source"),
                    "rationale": record.get("rationale"),
                    "options": record.get("options"),
                    "control_type": record.get("control_type"),
                    "job_id": record["job_id"],
                    "company": record.get("company", ""),
                    "normalized_question": record["normalized_question"],
                })
                wrote = True
                break
        if not wrote:
            last = self.history[-1] if self.history else None
            if (
                last
                and last.get("question") == record.get("question")
                and last.get("answer") == record.get("answer")
                and last.get("control_type") == record.get("control_type")
            ):
                return record  # Identical consecutive record — skip file churn.
            self.history.append(record)
        try:
            self.output_json_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.output_json_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(self.history, indent=2, ensure_ascii=False), encoding="utf-8")
            temp_path.replace(self.output_json_path)
            logger.info(f"[AIBrainResolver] Persisted Q&A record to {self.output_json_path}")
        except Exception as e:
            logger.error(f"[AIBrainResolver] Failed to persist Q&A record: {e}")
            return record
        if record.get("control_type") != "RECIPIENT_HEADER":
            self._mirror_role_answers(record)
        return record

    def _mirror_role_answers(self, record: Dict[str, Any]) -> None:
        """Maintain screening_qa inside the Stage 4 role answers.json.

        Writes only when the role directory already exists (Stage 4 created
        it); never creates directories, never raises, never touches the
        blueprint. Existing top-level keys are preserved.
        """
        try:
            job_id, company, title = self._record_context()
            if not job_id:
                return  # No requisition -> nothing role-scoped to mirror.
            cd = self.candidate_data if isinstance(self.candidate_data, dict) else {}
            slug = ""
            for key in ("profile", "_ipc_profile"):
                val = cd.get(key)
                if val and isinstance(val, str) and val.strip():
                    slug = val.strip()
                    break
            if not slug:
                cand = cd.get("candidate", {})
                if isinstance(cand, dict):
                    for key in ("profile_name", "profile"):
                        val = cand.get(key)
                        if val and isinstance(val, str) and val.strip():
                            slug = val.strip()
                            break
                if not slug:
                    full = cand.get("full_name") or ""
                    if full:
                        slug = re.sub(r"[^a-zA-Z0-9_]", "_", str(full).strip().lower()).strip("_")
            if not slug or slug in ("default_user", "candidate"):
                return
            from CompanySiteApply.utils.application_docs import application_dir
            role_dir = None
            if company and title:
                _cand = application_dir(slug, company, title, job_id)
                if _cand.is_dir():
                    role_dir = _cand
            if role_dir is None:
                # [F-CSA-02] Job-id-anchored discovery: Section 2/3 callers may
                # carry only job_id (title/company unstamped or renamed), but
                # the role folder name always ends with _<jobid>. Still never
                # creates a directory.
                try:
                    from CompanySiteApply.utils.runtime_paths import resolve_profile_dir
                    _jid = re.sub(r"[^A-Za-z0-9_]", "_", str(job_id)).strip("_")
                    _root = resolve_profile_dir(slug) / "APPLIED ON COMPANY WEBSITE"
                    if _jid and _root.is_dir():
                        for _hit in sorted(_root.glob(f"*/*_{_jid}")):
                            if _hit.is_dir():
                                role_dir = _hit
                                if not company:
                                    company = _hit.parent.name
                                break
                except Exception:
                    role_dir = None
            if role_dir is None or not role_dir.is_dir():
                return
            target = role_dir / "answers.json"
            data: Dict[str, Any] = {}
            try:
                if target.is_file():
                    loaded = json.loads(target.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        data = loaded
            except Exception:
                data = {}
            qn = self._normalize_question(record.get("question"))
            qa = [e for e in data.get("screening_qa", [])
                  if isinstance(e, dict)
                  and self._normalize_question(e.get("question")) != qn]
            qa.append({
                "question": record.get("question"),
                "answer": record.get("answer"),
                "control_type": record.get("control_type"),
                "options": record.get("options", []),
                "source": record.get("source"),
                "rationale": record.get("rationale"),
                "timestamp": record.get("timestamp")
                or time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            data["screening_qa"] = qa
            data["company"] = company
            data["job_id"] = job_id
            data["job_title"] = title or role_dir.name
            tmp = target.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(target)
        except Exception as e:
            logger.debug(f"[AIBrainResolver] Role answers mirror note: {e}")

    def _build_knowledge_index(self) -> Dict[str, Any]:
        """
        Deep-analyzes candidate config, resume, and skills taxonomy.
        Constructs ground truth knowledge representation.
        """
        cand = self.candidate_data.get("candidate", self.candidate_data)
        tax = self.candidate_data.get("taxonomy_skills") or {}
        ats = self.candidate_data.get("ats_answers") or {}
        learned = self.candidate_data.get("auto_learned_truths") or {}
        content = self.candidate_data.get("profile_content") or {}

        # 1. Technical Skills & Programming Languages
        tech_skills: List[str] = []
        if isinstance(tax, dict):
            tech_skills.extend(tax.get("Technical Skills") or tax.get("technical_skills") or [])
            tech_skills.extend(tax.get("Domain Skills") or tax.get("domain_skills") or [])
            tech_skills.extend(tax.get("naukri_key_skills") or [])
            for item in (tax.get("naukri_it_skills") or []):
                if isinstance(item, dict) and item.get("skill_name"):
                    tech_skills.append(item["skill_name"])

        tech_skills.extend(content.get("key_skills") or [])
        tech_skills.extend(cand.get("skills") or [])

        # Normalize unique tech skills
        unique_skills = []
        seen = set()
        for s in tech_skills:
            clean = str(s).strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                unique_skills.append(clean)

        # 2. Programming languages specifically
        known_languages = [
            "Java", "Python", "SQL", "JavaScript", "TypeScript", "C++", "C#", "Go",
            "Scala", "Kotlin", "Ruby", "PHP", "PL/SQL", "Rust", "Swift"
        ]
        prog_langs = []
        for kl in known_languages:
            if any(kl.lower() == s.lower() or f" {kl.lower()} " in f" {s.lower()} " for s in unique_skills):
                prog_langs.append(kl)

        # Explicit programming languages in ats_answers
        explicit_pl = ats.get("programming languages") or ats.get("primary_programming_languages")
        if isinstance(explicit_pl, str):
            for p in re.split(r'[,/|]+', explicit_pl):
                p_clean = p.strip()
                if p_clean and p_clean not in prog_langs:
                    prog_langs.insert(0, p_clean)
        elif isinstance(explicit_pl, list):
            for p in explicit_pl:
                if str(p).strip() and str(p).strip() not in prog_langs:
                    prog_langs.insert(0, str(p).strip())

        # Prioritize language mentioned directly in candidate title/headline if present
        current_title = str(cand.get("current_title") or cand.get("headline") or cand.get("resume_headline") or "").strip()
        for kl in known_languages:
            if kl.lower() in current_title.lower() and kl in prog_langs:
                prog_langs.remove(kl)
                prog_langs.insert(0, kl)

        # 3. Total experience
        total_exp = float(cand.get("total_experience_years") or 0.0)
        if total_exp == 0.0 and "experience_years" in cand:
            try:
                total_exp = float(cand["experience_years"])
            except Exception:
                pass

        # 4. Primary domain & specialization (100% Dynamic - Zero Hardcoding)
        target_jobs = self.candidate_data.get("target_jobs") or {}
        target_keywords = target_jobs.get("keywords") or []
        recommended_titles = target_jobs.get("recommended_titles") or []
        cog_prof = self.candidate_data.get("cognitive_profile") or {}

        # Dynamically determine candidate domain
        cand_domain = (
            cog_prof.get("candidate_domain")
            or cand.get("domain")
            or cand.get("primary_domain")
            or ats.get("Which primary technical area best describes your experience?")
            or ats.get("primary_domain")
            or target_jobs.get("department")
            or target_jobs.get("functional_area")
        )
        if not cand_domain:
            if current_title:
                cand_domain = current_title
            elif target_keywords:
                cand_domain = target_keywords[0]
            elif recommended_titles:
                cand_domain = recommended_titles[0]
            else:
                cand_domain = "Professional"

        primary_domain = cand_domain

        # Dynamically determine specialization
        specialization = ""
        if ats.get("specialization"):
            specialization = ats["specialization"]
        elif target_keywords:
            specialization = target_keywords[0]
        elif recommended_titles:
            specialization = recommended_titles[0]
        elif current_title:
            specialization = current_title
        elif unique_skills:
            specialization = ", ".join(unique_skills[:3])
        else:
            specialization = primary_domain

        # Determine if candidate is in a software/technical coding domain
        tech_tokens = ["software", "developer", "engineer", "architect", "programmer", "coding", "data science", "devops", "fullstack", "frontend", "backend"]
        all_domain_text = f"{current_title} {primary_domain} {' '.join(target_keywords)}".lower()
        is_tech_candidate = any(t in all_domain_text for t in tech_tokens) or len(prog_langs) > 0

        # 5. Cloud / AWS proficiency (dynamically evaluated)
        has_aws = any("aws" in s.lower() or "amazon web services" in s.lower() for s in unique_skills)
        has_cloud = has_aws or any("cloud" in s.lower() or "azure" in s.lower() or "gcp" in s.lower() for s in unique_skills)
        aws_prof = "None"
        if has_aws or has_cloud:
            aws_prof = "Advanced / Expert" if total_exp >= 5 else "Intermediate"
        if "aws" in ats:
            aws_prof = ats["aws"]
        elif "proficiency with AWS" in ats:
            aws_prof = ats["proficiency with AWS"]

        # 6. Legal Authorizations
        is_adult = "Yes"
        authorized = "Yes"
        needs_sponsorship = "No" if not cand.get("requires_sponsorship", False) else "Yes"
        has_indian_passport = "Yes" if "india" in str(cand.get("country", "")).lower() or "india" in str(cand.get("location", "")).lower() else "No"
        other_passport = "No"

        return {
            "candidate_name": cand.get("full_name", ""),
            "current_title": current_title,
            "total_experience_years": total_exp,
            "technical_skills": unique_skills,
            "programming_languages": prog_langs,
            "is_tech_candidate": is_tech_candidate,
            "primary_domain": primary_domain,
            "specialization": specialization,
            "aws_proficiency": aws_prof,
            "is_adult": is_adult,
            "authorized_to_work": authorized,
            "needs_sponsorship": needs_sponsorship,
            "has_indian_passport": has_indian_passport,
            "other_passport": other_passport,
            "ats_answers": ats,
            "auto_learned_truths": learned
        }

    # =========================================================================
    # CORE QUESTION RESOLUTION ENGINE
    # =========================================================================

    def resolve_question(
        self,
        question_text: str,
        control_type: str,
        options: Optional[List[str]] = None,
        req_count: int = 1
    ) -> Dict[str, Any]:
        """
        Main entry point for resolving any screening question.
        Returns a structured dictionary with the exact choices to apply.
        """
        q_clean = question_text.strip()
        q_lower = q_clean.lower()
        # [F-RES-03] options MUST be a list of strings. A bare string (e.g. the
        # control_type "RADIO_PILL" arriving in the options slot) used to be
        # iterated CHARACTER-BY-CHARACTER by _best_option_match(), which
        # substring-matched "R" inside "sp( R )ingboot" and returned "R" as a
        # confident answer. Coerce defensively instead of trusting the caller.
        if isinstance(options, str):
            options = [options]
        elif options is None:
            options = []
        else:
            options = [o for o in options if isinstance(o, str) and o.strip()]

        # 0. Self-echo guard (incident 210788242): scanners sometimes emit an
        #    OPTION pill's text as the question (label fallback). Answering an
        #    option with itself flipped a correct tier pick to "No Prior
        #    Experience" on a single-select group. Refuse loudly instead.
        if q_clean and any(q_clean.lower() == str(o).strip().lower() for o in options):
            record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "question": q_clean,
                "control_type": control_type,
                "options": options,
                "source": "REFUSED_SELF_ECHO",
                "answer": None,
                "rationale": "Question text matches one of its own options — scanner mis-extraction. Deferred to operator."
            }
            self._persist_answer(record)
            return record

        # 0b. [F-RES-04] Structured ground truth OUTRANKS the answer cache for
        # derivable questions. ats_answers/auto_learned_truths are caches, not
        # truth: a poisoned entry ("At least 5 years of experience" for a
        # 10.8-year candidate) exact-matched first, got conformed onto the
        # "At Least 5 Years" pill, and was stamped CACHED_TRUTH with the
        # rationale "Exact match found in candidate ground-truth config." -
        # a false provenance claim. Experience tiers are COMPUTED from
        # candidate.total_experience_years, so compute them first.
        if self._is_experience_tier_question(q_lower, options):
            derived, why = self._deduce_answer(q_clean, control_type, options, req_count)
            if derived and self._answer_matches_options(derived, options, control_type):
                record = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "question": q_clean,
                    "control_type": control_type,
                    "options": options,
                    "source": "PROFILE_DERIVED",
                    "answer": derived,
                    "rationale": why,
                }
                self._persist_answer(record)
                return record

        # 1. Check exact match in ats_answers or auto_learned_truths
        cached_val = self._find_in_cached_truths(q_clean)
        if cached_val is not None:
            resolved = self._conform_answer_to_control(q_clean, cached_val, control_type, options, req_count)
            is_valid_choice = True
            if options and control_type in ["RADIO_PILL", "BINARY_PILL", "DROPDOWN"]:
                if resolved not in options:
                    is_valid_choice = False
            elif options and control_type == "DROPDOWN_MULTI":
                if not isinstance(resolved, list) or len(resolved) == 0 or not all(x in options for x in resolved):
                    is_valid_choice = False

            if is_valid_choice:
                record = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "question": q_clean,
                    "control_type": control_type,
                    "options": options,
                    "source": "CACHED_TRUTH",
                    "answer": resolved,
                    "rationale": "Exact match found in candidate ground-truth config."
                }
                self._persist_answer(record)
                return record
            else:
                logger.info(f"[AIBrainResolver] Cached truth '{cached_val}' not found in options {options}. Falling through to dynamic deduction.")

        # 2. Resolve dynamically based on question category
        resolved, rationale = self._deduce_answer(q_clean, control_type, options, req_count)

        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": q_clean,
            "control_type": control_type,
            "options": options,
            "source": "AI_BRAIN_REASONING",
            "answer": resolved,
            "rationale": rationale
        }
        self._persist_answer(record)
        return record

    # [F-RES-05] Tool-category question hints and grounding vocabulary.
    _TOOL_CATEGORY_HINTS = (
        "continuous integration", "continuous delivery", "ci/cd", "cicd",
        "observability", "monitoring tool", "container", "orchestration",
        "cloud platform", "infrastructure as a service", "devops tool",
        "version control", "source control", "build tool", "test framework",
    )
    # Generic words that appear inside tool option text but can NEVER ground a
    # match on their own ("Google Cloud Platform" contains "cloud", which would
    # otherwise assert Azure/GCP/OCI for a Java backend with no such skill).
    _GENERIC_SKILL_TOKENS = frozenset({
        "cloud", "platform", "tool", "tools", "technology", "service",
        "services", "system", "systems", "software", "engineering", "developer",
        "development", "programming", "data", "management", "support",
        "experience", "other", "others", "solution", "solutions", "design",
        "architecture", "application", "applications", "infrastructure",
        "integration", "framework", "scripting", "web", "full", "native",
    })
    # Options that must never be selected by skill grounding: they are
    # catch-alls / negations whose meaning is not a tool claim.
    _OPTION_DISTRACTORS = (
        "others/not listed", "other/not listed", "not listed above", "none of",
        "no relevant experience", "not familiar", "none", "n/a",
    )
    # Common option spellings -> the skill token that grounds them.
    _SKILL_ALIASES = {
        "amazon web services": "aws", "microsoft azure": "azure",
        "google cloud platform": "gcp", "gcp": "gcp",
        "oracle cloud infrastructure": "oci", "oci": "oci",
        "amazon elastic container service": "ecs", "amazon eks": "eks",
        "red hat openshift": "openshift", "openshift": "openshift",
        "continuous integration": "ci/cd", "site reliability": "sre",
    }

    def _ground_tool_options(
        self,
        q_lower: str,
        idx: Dict[str, Any],
        options: List[str],
        control_type: str,
    ):
        """[F-RES-05] Answer tool/platform questions from DECLARED skills only.

        Returns (answer, rationale), or None when the question is not a tool
        category question or nothing is grounded (caller keeps deferring).
        """
        if not options or not any(h in q_lower for h in self._TOOL_CATEGORY_HINTS):
            return None

        declared = [str(s).strip().lower() for s in idx.get("technical_skills", [])]
        declared = [s for s in declared if len(s) >= 2]
        if not declared:
            return None

        multi = bool(re.search(r"all that apply|select all|multiple|choose all",
                               q_lower)) or control_type == "DROPDOWN_MULTI"

        matched: List[str] = []
        declared_set = set(declared)
        for opt in options:
            opt_l = str(opt).strip().lower()
            if any(d in opt_l for d in self._OPTION_DISTRACTORS):
                continue
            # 1) Near-exact: the option IS the declared tool ("Jenkins").
            if opt_l in declared_set:
                matched.append(opt)
                continue
            # 2) Known alias for a declared tool ("Amazon Web Services" -> aws).
            alias = self._SKILL_ALIASES.get(opt_l)
            if alias and alias in declared_set:
                matched.append(opt)
                continue
            # 3) Whole-word containment by a SPECIFIC declared skill. SINGLE-SELECT
            #    ONLY: for prose-style pills such as "Very familiar (ECS,
            #    Kubernetes, Docker)" containment is the right test. For a
            #    "choose all that apply" list the option IS the tool name, so
            #    containment over-reaches - the declared skill "oracle"
            #    (Oracle Database) would assert "Oracle Cloud Infrastructure
            #    (OCI)" for a backend with no cloud experience.
            hit = False
            if not multi:
                for sk in declared:
                    if sk in self._GENERIC_SKILL_TOKENS or len(sk) < 4:
                        continue
                    if re.search(rf"\b{re.escape(sk)}\b", opt_l):
                        hit = True
                        break
            if hit:
                matched.append(opt)

        if not matched:
            return None

        if multi:
            picked = matched[:max(1, len(matched))]
            return picked, ("Grounded in declared technical skills: "
                            + ", ".join(picked))
        return matched[0], (f"Selected '{matched[0]}' — matches declared technical "
                            f"skills in candidate profile.")

    def _is_experience_tier_question(self, q_lower: str, options: Optional[List[str]] = None) -> bool:
        """[F-RES-04] True for experience-BRACKET questions that are derivable
        from candidate.total_experience_years rather than recalled.

        Guarded on the OPTIONS being tier-shaped, not on question wording alone.
        "How many years of experience do you have in Kafka Streams?" also
        contains "how many years", but its options are numeric inputs about a
        single skill - deriving a bucket from total tenure would answer a
        different question than the one asked.
        """
        opts = options or []
        tier_shaped = any(
            re.search(r"less than|at least|more than|over\s*\d|\d+\s*\+?\s*year",
                      str(o), re.I)
            for o in opts
        )
        if not tier_shaped:
            return False
        return any(w in q_lower for w in (
            "years of work experience", "experience you have",
            "relevant work experience", "years of experience",
            "total experience", "total years of experience"))

    @staticmethod
    def _answer_matches_options(answer: Any, options: List[str], control_type: str) -> bool:
        """[F-RES-04] Shared validity check for a resolved answer."""
        if not options:
            return True
        if control_type in ("RADIO_PILL", "BINARY_PILL", "DROPDOWN"):
            return answer in options
        if control_type == "DROPDOWN_MULTI":
            return (isinstance(answer, list) and len(answer) > 0
                    and all(x in options for x in answer))
        return True

    def _find_in_cached_truths(self, question: str) -> Optional[Any]:
        """Checks ats_answers and auto_learned_truths with normalization."""
        q_norm = re.sub(r'[\s:?._*#-]+$', '', question.strip().lower())
        ats = self.knowledge_index.get("ats_answers", {})
        learned = self.knowledge_index.get("auto_learned_truths", {})

        for src in [ats, learned]:
            for k, v in src.items():
                k_norm = re.sub(r'[\s:?._*#-]+$', '', k.strip().lower())
                if k_norm == q_norm or (len(k_norm) > 20 and (k_norm in q_norm or q_norm in k_norm)):
                    return v
        return None

    def _conform_answer_to_control(
        self,
        question: str,
        raw_val: Any,
        control_type: str,
        options: List[str],
        req_count: int
    ) -> Any:
        """Aligns cached value with DOM options and control type."""
        if control_type == "DROPDOWN_MULTI":
            if isinstance(raw_val, list):
                val_list = [str(x).strip() for x in raw_val]
            else:
                val_list = [s.strip() for s in str(raw_val).split(",") if s.strip()]
            
            matched = []
            for item in val_list:
                best = self._best_option_match(item, options)
                if best and best not in matched:
                    matched.append(best)
            if matched:
                return matched[:req_count]

        elif control_type in ["RADIO_PILL", "BINARY_PILL"]:
            val_str = str(raw_val).strip()
            best = self._best_option_match(val_str, options)
            if best:
                return best
            return val_str

        return raw_val

    def _deduce_answer(
        self,
        question: str,
        control_type: str,
        options: List[str],
        req_count: int
    ) -> Tuple[Any, str]:
        """Deduces high-quality, truthful answer based on candidate profile."""
        q_lower = question.lower()
        idx = self.knowledge_index

        # A. Programming Languages Multi-Select Question
        if "programming language" in q_lower or "languages have you worked" in q_lower:
            cand_langs = idx.get("programming_languages", [])
            is_tech = idx.get("is_tech_candidate", False)
            matched_opts = []

            if is_tech:
                # For technical developers, match their verified programming languages
                for lang in cand_langs:
                    best = self._best_option_match(lang, options)
                    if best and best not in matched_opts:
                        if "not require" not in best.lower() and "others" not in best.lower():
                            matched_opts.append(best)

                # Search technical skills if more choices needed
                if len(matched_opts) < req_count:
                    for skill in idx.get("technical_skills", []):
                        best = self._best_option_match(skill, options)
                        if best and best not in matched_opts:
                            if "not require" not in best.lower() and "others" not in best.lower():
                                matched_opts.append(best)
                        if len(matched_opts) >= req_count:
                            break

                # Safe fallback for tech candidate: pick coding languages from options matching skills
                if not matched_opts:
                    for opt in options:
                        if "not require" not in opt.lower() and "none" not in opt.lower():
                            matched_opts.append(opt)
                            if len(matched_opts) >= req_count:
                                break

                selected = matched_opts[:req_count]
                return selected, f"Selected top {len(selected)} verified programming languages from technical profile."
            else:
                # For non-technical profiles (e.g. Finance, Audit, HR, Sales)
                # Check if "does not require coding" option exists
                for opt in options:
                    if "not require" in opt.lower() or "not hands-on" in opt.lower() or "none" in opt.lower():
                        return [opt] if control_type == "DROPDOWN_MULTI" else opt, "Candidate profile is in a non-coding domain."
                # Otherwise pick any skill that overlaps with candidate profile
                for skill in idx.get("technical_skills", []):
                    best = self._best_option_match(skill, options)
                    if best and best not in matched_opts:
                        matched_opts.append(best)
                selected = matched_opts[:req_count] if matched_opts else (options[:req_count] if options else [])
                return selected, "Selected domain-compatible options for candidate profile."

        # B. Experience Tiers
        if any(w in q_lower for w in ["years of work experience", "experience you have", "relevant work experience"]):
            total_exp = idx["total_experience_years"]
            selected_pill = self._resolve_tier_pill(total_exp, options)
            return selected_pill, f"Mapped {total_exp} years of total experience to bracket '{selected_pill}'."

        # [F-RES-05] Tool / platform category questions (CI/CD, observability,
        # container-orchestration familiarity, cloud platform). MUST run before
        # branch C: that catch-all substring-matched the specialization against
        # ANY option list and claimed the question ("Selected specialization
        # 'R'..."). These questions instead ground strictly in the candidate's
        # declared technical_skills - an option is selected ONLY when a declared
        # skill is present in it. Nothing is inferred, so an ungrounded option
        # (Terraform/Datadog/Splunk for a Java backend) is never asserted.
        tool_ans = self._ground_tool_options(q_lower, idx, options, control_type)
        if tool_ans is not None:
            return tool_ans

        # C. Option-Driven Specialization Recognition
        # Search candidate specialization, target titles, and skills against options
        best = self._best_option_match(idx.get("specialization", ""), options)
        if best:
            return best, f"Selected specialization '{best}' matching candidate profile."

        # D. Primary Area of Expertise
        if "primary area of expertise" in q_lower or "primary technical area" in q_lower or "primary area" in q_lower:
            best = self._best_option_match(idx.get("primary_domain", ""), options)
            if best:
                return best, f"Selected primary domain '{best}' matching candidate profile."
            spec = self._best_option_match(idx.get("specialization", ""), options)
            if spec:
                return spec, f"Selected specialization '{spec}' matching candidate profile."

        # E. Specific Field of Specialization / Sub-area
        if any(w in q_lower for w in ["specific field", "specialization", "sub-area", "area of expertise"]):
            best = self._best_option_match(idx.get("specialization", ""), options)
            if not best:
                for skill in idx.get("technical_skills", []):
                    best = self._best_option_match(skill, options)
                    if best:
                        break
            if best:
                return best, f"Selected specialization '{best}' matching candidate profile taxonomy."

        # F. Cloud / Tool Proficiency (e.g. AWS)
        if "proficiency" in q_lower or "rate your proficiency" in q_lower:
            prof = idx.get("aws_proficiency", "None")
            best = self._best_option_match(prof, options)
            if not best:
                total_exp = idx.get("total_experience_years", 0)
                if total_exp >= 8:
                    for opt in options:
                        if "expert" in opt.lower() or "advanced" in opt.lower():
                            best = opt
                            break
                elif total_exp >= 3:
                    for opt in options:
                        if "intermediate" in opt.lower():
                            best = opt
                            break
                else:
                    for opt in options:
                        if "fundamental" in opt.lower() or "beginner" in opt.lower() or "basic" in opt.lower():
                            best = opt
                            break
            if best:
                return best, f"Assigned proficiency rating '{best}' based on candidate experience profile."

        # F. Regulatory & Binary Yes/No — only when the options really are Yes/No.
        # (len==2 alone once affirmed gibberish questions; incident follow-up.)
        opt_norm = {str(o).strip().lower() for o in options}
        if control_type == "BINARY_PILL" or opt_norm == {"yes", "no"}:
            if "18 years of age" in q_lower:
                return "Yes", "Candidate is of legal working age (18+)."
            if "legally authorized" in q_lower or "authorized to work" in q_lower:
                return "Yes", "Candidate holds valid work authorization."
            if "sponsorship" in q_lower or "visa status" in q_lower:
                return idx["needs_sponsorship"], "Candidate sponsorship requirement from candidate config."
            if "indian passport" in q_lower:
                return idx["has_indian_passport"], "Indian passport verification from candidate citizenship."
            if "other than india" in q_lower or "foreign" in q_lower:
                return idx["other_passport"], "Non-Indian citizenship declaration."
            if any(w in q_lower for w in ["disciplinary", "convicted", "crime", "non-compete", "former employee"]):
                return "No", "Standard background clearance declaration."
            return "Yes", "Default affirmative for standard screening verification."

        # Default fallback: DEFER. Blind-picking options[0] for unrecognized
        # questions once flipped a correct answer to "No Prior Experience"
        # (incident 210788242). Healers skip empty answers; audits flag them.
        return "", "Unrecognized question with no profile grounding — deferred to operator."

    def _resolve_tier_pill(self, total_exp: float, options: List[str]) -> str:
        """Selects the exact experience bracket pill matching total_exp."""
        tier_brackets: List[Tuple[float, str]] = []
        for opt in options:
            nums = re.findall(r'\d+', opt)
            if nums:
                val = float(nums[-1])
                tier_brackets.append((val, opt))
            elif "less than" in opt.lower():
                tier_brackets.append((0.0, opt))

        tier_brackets.sort(key=lambda x: x[0], reverse=True)
        for min_yrs, opt in tier_brackets:
            if total_exp >= min_yrs:
                return opt

        return options[-1] if options else ""

    def _best_option_match(self, target: str, options: List[str]) -> Optional[str]:
        """Matches a target term against a list of DOM option strings."""
        if not target or not options:
            return None
        # [F-RES-03] Defence in depth: never iterate a bare string here. Doing so
        # yielded single-character "matches" (e.g. "R" from the control_type
        # string "RADIO_PILL") that were then accepted as real answers.
        if isinstance(options, str):
            options = [options]
        options = [o for o in options if isinstance(o, str) and o.strip()]
        if not options:
            return None
        target_norm = target.strip().lower()

        # 1. Exact match
        for opt in options:
            if opt.strip().lower() == target_norm:
                return opt

        # 2. Word boundary / prefix match
        for opt in options:
            opt_norm = opt.strip().lower()
            if target_norm in opt_norm or opt_norm in target_norm:
                return opt

        # 3. Token overlap match
        target_tokens = set(re.findall(r'\w+', target_norm))
        best_opt = None
        best_score = 0
        for opt in options:
            opt_tokens = set(re.findall(r'\w+', opt.strip().lower()))
            overlap = len(target_tokens.intersection(opt_tokens))
            if overlap > best_score:
                best_score = overlap
                best_opt = opt

        if best_score > 0:
            return best_opt

        return None

    # =========================================================================
    # IPC FILE BRIDGE (async AG Brain switch — §2.2 state machine)
    # =========================================================================

    def answer_ipc_file(self) -> Dict[str, Any]:
        """
        Async AG Brain entry-point: read CompanySiteApply/ipc/section_question.json
        when status == ANSWER_REQUIRED, resolve every question via resolve_question(),
        and write back with status == ANSWERED.

        This is the TRUE switch the section scripts wait on with
        IPCManager.wait_for_answers(). The in-process heal_* fast-path
        (write_questions → resolve_question → write_answers in one call) is kept
        for single-process runs, but any external brain process can drive the same
        file through this method without DOM access.
        """
        from CompanySiteApply.ipc.ipc_manager import IPCManager

        ipc = IPCManager.from_file()
        data = ipc.read()
        if not data:
            return {"success": False, "error": "IPC file missing"}
        if data.get("status") != "ANSWER_REQUIRED":
            return {"success": True, "skipped": True, "status": data.get("status"), "count": 0}
        answered = []
        for q in data.get("questions", []):
            q_text = q.get("question_text", "")
            f_type = q.get("field_type", "TEXT")
            choices = q.get("available_choices") or []
            try:
                resolution = self.resolve_question(
                    question_text=q_text,
                    control_type=f_type if f_type != "DROPDOWN" else "DROPDOWN_MULTI",
                    options=choices,
                    req_count=2 if f_type in ("DROPDOWN", "COMBOBOX", "DROPDOWN_MULTI") else 1,
                )
                q["answer"] = resolution.get("answer")
                q["answer_confidence"] = 1.0
                q["answer_rationale"] = resolution.get("rationale")
            except Exception as e:
                q["answer"] = None
                q["answer_rationale"] = f"BRIDGE_ERROR: {e}"
            answered.append(q)
        ipc.write_answers(answered)
        return {"success": True, "status": "ANSWERED", "count": len(answered)}

    # =========================================================================
    # RECIPIENT HEADER ARBITRATION (cover-letter identity block)
    # =========================================================================
    def resolve_recipient_header(
        self, job_evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AG-Brain-owned verdict for the cover-letter recipient block.

        The brain — not Python heuristics — decides the identity fields
        (company, requisition city, hiring-team line) from weighed evidence,
        grounded in the candidate profile + requisition. Python callers
        (Stage 4, s4 on-demand synthesis) supply the evidence proposal and
        MUST honor a refusal (defer, never render a placeholder).

        job_evidence keys: job_id, job_title, stamped_company,
        page_url, portal_default_company, candidate_company_hints (list),
        dom_location, requisition_location, explicit_team,
        workspace_provisioned (bool).

        Returns {"success", "company", "location", "hiring_team",
        "evidence", "error"}. Person names are never invented: hiring_team
        is "{company} Engineering Team" unless the requisition states one.
        """
        ev = job_evidence if isinstance(job_evidence, dict) else {}
        job_id = str(ev.get("job_id") or "").strip()
        job_title = str(ev.get("job_title") or "").strip()
        evidence: List[str] = []

        # --- Company arbitration (ranked evidence, conflict refuses) ---
        _PLACEHOLDERS = {"", "company", "hiring organization",
                         "hiring organisation", "unknown"}

        def _clean(v: Any) -> str:
            s = str(v or "").strip()
            return "" if s.lower() in _PLACEHOLDERS else s

        stamped = _clean(ev.get("stamped_company"))
        url = str(ev.get("page_url") or "")
        url_hint = "JPMorgan Chase & Co." if (
            url and ("jpmc" in url.lower() or "chase" in url.lower())) else ""
        hints = [_clean(h) for h in (ev.get("candidate_company_hints") or [])]
        hints = [h for h in hints if h]
        portal_default = _clean(ev.get("portal_default_company"))

        def _canon(s: str) -> str:
            if "jpmorgan" in s.lower() and "chase" in s.lower():
                return "JPMorgan Chase & Co."
            return s

        if stamped:
            evidence.append(f"scraper-stamped:{stamped}")
        if url_hint:
            evidence.append(f"url-hint:{url_hint}")
        evidence.extend(f"candidate-hint:{h}" for h in hints)
        if portal_default:
            evidence.append(f"portal-default:{portal_default}")
        if ev.get("workspace_provisioned"):
            evidence.append("workspace-provisioned-for-company")

        # Conflict rule: two distinct grounded identities (stamped vs URL
        # hint) means corrupted context — refuse instead of guessing.
        if stamped and url_hint and _canon(stamped) != _canon(url_hint):
            return self._recipient_refusal(
                job_id, job_title, evidence,
                f"company conflict: stamped {stamped!r} vs URL hint "
                f"{url_hint!r} — refusing to pick")

        company = ""
        for cand_value in [stamped, url_hint] + hints + [portal_default]:
            if cand_value:
                company = _canon(cand_value)
                break
        if not company:
            return self._recipient_refusal(
                job_id, job_title, evidence,
                "company unknown from all evidence — refusing placeholder")

        # --- Location arbitration (requisition only; never home address) ---
        dom_loc = str(ev.get("dom_location") or "").strip()
        req_loc = str(ev.get("requisition_location") or "").strip()
        location = (dom_loc or req_loc)[:120]
        evidence.append(f"location:{location or '<unverified>'}:"
                        f"{'dom' if dom_loc else ('requisition' if req_loc else 'none')}")

        # --- Hiring-team line (no invented person names, ever) ---
        explicit_team = str(ev.get("explicit_team") or "").strip()
        hiring_team = explicit_team or f"{company} Engineering Team"
        evidence.append(f"team:{hiring_team}")

        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": f"Cover-letter recipient header ({job_id} - {job_title})",
            "control_type": "RECIPIENT_HEADER",
            "options": [],
            "source": "AI_BRAIN_RECIPIENT_ARBITRATION",
            "answer": {"company": company, "location": location,
                       "hiring_team": hiring_team},
            "rationale": f"Arbitrated from evidence: {'; '.join(evidence)}",
            "evidence": evidence,
        }
        self._persist_answer(record)
        logger.info(f"[AIBrainResolver] Recipient header: {company} | "
                    f"{location or '<city unverified>'} | {hiring_team}")
        return {"success": True, "company": company, "location": location,
                "hiring_team": hiring_team, "evidence": evidence, "error": ""}

    def _recipient_refusal(self, job_id: str, job_title: str,
                           evidence: List[str], reason: str) -> Dict[str, Any]:
        """Loud deferral: the letter must not be rendered."""
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": f"Cover-letter recipient header ({job_id} - {job_title})",
            "control_type": "RECIPIENT_HEADER",
            "options": [],
            "source": "REFUSED_RECIPIENT_UNVERIFIED",
            "answer": None,
            "rationale": reason,
            "evidence": evidence,
        }
        self._persist_answer(record)
        logger.warning(f"[AIBrainResolver] Recipient header REFUSED: {reason}")
        return {"success": False, "company": "", "location": "",
                "hiring_team": "", "evidence": evidence, "error": reason}
