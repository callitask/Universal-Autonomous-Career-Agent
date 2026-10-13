# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [SECTION_AGENT_DISPATCHER_HIERARCHICAL_ROUTING]
# Timestamp: 2026-10-09 22:47:00 +05:30
# Issue / Context: Needed granular routing supporting both top-level sections and surgical sub-agents.
# Changes Made: Updated SectionAgentDispatcher to register top-level section coordinators and all 9 granular sub-agents.
# Rationale: Enables single-subagent execution (e.g. heal preferred_location, heal dropdown_questions, heal documents)
#            with zero side effects on sister sections.
# Preventative Notes: Always preserve subagent boundaries.
# ==============================================================================

import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent
from CompanySiteApply.section_agents.profile_section_agent import ProfileSectionAgent
from CompanySiteApply.section_agents.questionnaire_section_agent import QuestionnaireSectionAgent
from CompanySiteApply.section_agents.education_section_agent import EducationSectionAgent
from CompanySiteApply.section_agents.experience_section_agent import ExperienceSectionAgent
from CompanySiteApply.section_agents.review_section_agent import ReviewSectionAgent

# Granular Sub-Agents
from CompanySiteApply.section_agents.sub_agents.personal_details_subagent import PersonalDetailsSubAgent
from CompanySiteApply.section_agents.sub_agents.preferred_location_subagent import PreferredLocationSubAgent
from CompanySiteApply.section_agents.sub_agents.binary_question_subagent import BinaryQuestionSubAgent
from CompanySiteApply.section_agents.sub_agents.technical_competency_subagent import TechnicalCompetencySubAgent
from CompanySiteApply.section_agents.sub_agents.dropdown_question_subagent import DropdownQuestionSubAgent
from CompanySiteApply.section_agents.sub_agents.education_subagent import EducationSubAgent
from CompanySiteApply.section_agents.sub_agents.experience_subagent import ExperienceSubAgent
from CompanySiteApply.section_agents.sub_agents.documents_subagent import DocumentsSubAgent
from CompanySiteApply.section_agents.sub_agents.diversity_subagent import DiversitySubAgent
from CompanySiteApply.section_agents.sub_agents.signature_subagent import SignatureSubAgent
from CompanySiteApply.section_agents.sub_agents.visual_verifier_subagent import VisualVerifierSubAgent

logger = logging.getLogger(__name__)


class SectionAgentDispatcher:
    """
    Central Brain Dispatcher for Section-Wise and Sub-Section Mini-Agents.
    Maintains the registry of all specialist section and sub-section agents, resolves
    which agent is required, and executes isolated micro-repairs without full-page restarts.
    """

    def __init__(self, agents: Optional[List[BaseSectionAgent]] = None):
        if agents is not None:
            self._agents = {a.section_name.lower(): a for a in agents}
        else:
            # Granular Sub-Agents
            pers_sub = PersonalDetailsSubAgent()
            loc_sub = PreferredLocationSubAgent()
            bin_sub = BinaryQuestionSubAgent()
            comp_sub = TechnicalCompetencySubAgent()
            drop_sub = DropdownQuestionSubAgent()
            edu_sub = EducationSubAgent()
            exp_sub = ExperienceSubAgent()
            doc_sub = DocumentsSubAgent()
            div_sub = DiversitySubAgent()
            sig_sub = SignatureSubAgent()
            vis_sub = VisualVerifierSubAgent()

            # Top-level Section Coordinators sharing underlying subagents
            prof_coord = ProfileSectionAgent(personal_subagent=pers_sub, location_subagent=loc_sub)
            quest_coord = QuestionnaireSectionAgent(binary_subagent=bin_sub, competency_subagent=comp_sub, dropdown_subagent=drop_sub)
            edu_coord = EducationSectionAgent()
            exp_coord = ExperienceSectionAgent()
            rev_coord = ReviewSectionAgent(docs_subagent=doc_sub, diversity_subagent=div_sub, signature_subagent=sig_sub, visual_subagent=vis_sub)

            default_agents = [
                prof_coord,
                quest_coord,
                edu_coord,
                exp_coord,
                rev_coord,
                pers_sub,
                loc_sub,
                bin_sub,
                comp_sub,
                drop_sub,
                edu_sub,
                exp_sub,
                doc_sub,
                div_sub,
                sig_sub,
                vis_sub
            ]
            self._agents = {a.section_name.lower(): a for a in default_agents}

    def register_agent(self, agent: BaseSectionAgent):
        """Registers a custom or platform-specific section/sub-section agent."""
        self._agents[agent.section_name.lower()] = agent

    def get_agent(self, name: str) -> Optional[BaseSectionAgent]:
        """Retrieves a specific section or sub-section agent by name."""
        return self._agents.get(name.lower())

    def list_available_agents(self) -> List[str]:
        """Returns the list of all registered section and sub-agent names."""
        return list(self._agents.keys())

    def list_available_sections(self) -> List[str]:
        """Returns top-level section names."""
        return ["profile", "questionnaire", "education", "experience", "review"]

    def list_available_subagents(self) -> List[str]:
        """Returns granular sub-agent names."""
        return [
            "personal_details",
            "preferred_location",
            "binary_questions",
            "technical_competency",
            "dropdown_questions",
            "education",
            "experience",
            "documents",
            "diversity",
            "signature",
            "visual_verifier"
        ]

    def resolve_agents_for_page(self, page: Any) -> List[BaseSectionAgent]:
        """
        Determines which section agents are applicable to the current browser page.
        """
        matching = []
        for agent in self._agents.values():
            try:
                if agent.can_handle(page):
                    matching.append(agent)
            except Exception as e:
                logger.warning(f"Error checking can_handle for {agent.section_name}: {e}")
        return matching

    def dispatch_heal(self, name: str, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Surgically dispatches a single named section or sub-agent to heal its domain.
        Guarantees complete isolation from other sections.
        """
        agent = self.get_agent(name)
        if not agent:
            return {
                "success": False,
                "error": f"Unknown section agent '{name}'. Available: {self.list_available_agents()}"
            }

        logger.info(f"[SectionAgentDispatcher] Dispatched '{agent.section_name}' for surgical healing...")
        return agent.heal(page, candidate_data)

    def dispatch_audit(self, name: str, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches a single named section or sub-agent to audit its domain.
        """
        agent = self.get_agent(name)
        if not agent:
            return {
                "success": False,
                "error": f"Unknown section agent '{name}'. Available: {self.list_available_agents()}"
            }

        return agent.audit(page, candidate_data)

    SECTION_TO_SUBAGENTS = {
        "profile": ["personal_details", "preferred_location"],
        "section_1": ["personal_details", "preferred_location"],
        "questionnaire": ["binary_questions", "technical_competency", "dropdown_questions"],
        "section_2": ["binary_questions", "technical_competency", "dropdown_questions"],
        "section_3": ["education", "experience"],
        "education": ["education"],
        "experience": ["experience"],
        "review": ["documents", "diversity", "signature", "visual_verifier"],
        "section_4": ["documents", "diversity", "signature", "visual_verifier"],
    }

    def evaluate_and_heal_section(
        self,
        section_name: str,
        page: Any,
        candidate_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI Brain Cognitive Dispatcher:
        1. Identifies which granular sub-agents map to the active section.
        2. Pre-audits every sub-agent to discover precisely which domains require healing.
        3. If all sub-agents are valid, cleanly bypasses redundant execution.
        4. If anomalies exist, surgically dispatches ONLY the required sub-agents.
        5. Verifies healed sub-agents with empirical post-execution audits.
        """
        sec_key = section_name.lower().strip()
        sub_names = self.SECTION_TO_SUBAGENTS.get(sec_key)

        # Fallback to top-level section coordinator if no sub-agents mapped
        if not sub_names:
            agent = self.get_agent(sec_key)
            if agent:
                logger.info(f"[AI Brain] Dispatching top-level agent '{agent.section_name}' for section '{sec_key}'...")
                heal_res = agent.heal(page, candidate_data)
                audit_res = agent.audit(page, candidate_data)
                return {
                    "section": sec_key,
                    "success": audit_res.get("is_valid", False),
                    "subagents_evaluated": [agent.section_name],
                    "subagents_healed": [agent.section_name],
                    "audit": audit_res,
                    "heal_result": heal_res
                }
            return {
                "section": sec_key,
                "success": False,
                "error": f"Unknown section '{sec_key}'"
            }

        logger.info(f"[AI Brain] Cognitive Dispatch: Evaluating section '{sec_key}' across sub-agents: {sub_names}...")
        sub_agents = [self.get_agent(name) for name in sub_names if self.get_agent(name)]

        pre_audits = {}
        agents_needing_heal = []

        # 1. Pre-audit Phase: Evaluate health of each sub-agent
        for agent in sub_agents:
            try:
                res = agent.audit(page, candidate_data)
                pre_audits[agent.section_name] = res
                if not res.get("is_valid", False):
                    logger.info(f"[AI Brain] -> Sub-Agent '{agent.section_name}' reports ANOMALY / ACTION_REQUIRED: {res}")
                    agents_needing_heal.append(agent)
                else:
                    logger.info(f"[AI Brain] -> Sub-Agent '{agent.section_name}' verified VALID (skipping).")
            except Exception as e:
                logger.warning(f"[AI Brain] Pre-audit error on '{agent.section_name}': {e}")
                agents_needing_heal.append(agent)

        healed_results = {}
        # 2. Targeted Healing Phase: Surgically invoke only the failing sub-agents
        if not agents_needing_heal:
            logger.info(f"[AI Brain] All sub-agents for '{sec_key}' are already 100% valid! No healing required.")
        else:
            for agent in agents_needing_heal:
                logger.info(f"[AI Brain] Surgically healing '{agent.section_name}'...")
                try:
                    h_res = agent.heal(page, candidate_data)
                    healed_results[agent.section_name] = h_res
                except Exception as e:
                    logger.error(f"[AI Brain] Error healing '{agent.section_name}': {e}")
                    healed_results[agent.section_name] = {"success": False, "error": str(e)}

        # 3. Post-Audit Verification Phase: Empirical verification
        post_audits = {}
        all_valid = True
        for agent in sub_agents:
            try:
                ver_res = agent.audit(page, candidate_data)
                post_audits[agent.section_name] = ver_res
                if not ver_res.get("is_valid", False):
                    all_valid = False
            except Exception as e:
                post_audits[agent.section_name] = {"is_valid": False, "error": str(e)}
                all_valid = False

        # 3b. Cascading second passes (Rank 1, 2026-10-13): healing one
        # sub-agent can reveal conditional questions owned by another
        # (incident 210765001: binary heal revealed the competency tier pill
        # AFTER pre-audit). Re-heal newly-invalidated agents, up to 3 passes.
        cascade_pass = 1
        while not all_valid and cascade_pass < 3:
            cascade_pass += 1
            newly_invalid = [
                a for a in sub_agents if not post_audits.get(a.section_name, {}).get("is_valid", False)
            ]
            if not newly_invalid:
                break
            logger.info(
                f"[AI Brain] Cascade pass {cascade_pass}/3 for '{sec_key}': "
                f"re-healing {[a.section_name for a in newly_invalid]}..."
            )
            for agent in newly_invalid:
                try:
                    h_res = agent.heal(page, candidate_data)
                    healed_results[f"{agent.section_name}_cascade_{cascade_pass}"] = h_res
                except Exception as e:
                    logger.error(f"[AI Brain] Cascade heal error on '{agent.section_name}': {e}")
                    healed_results[f"{agent.section_name}_cascade_{cascade_pass}"] = {"success": False, "error": str(e)}
            all_valid = True
            for agent in sub_agents:
                try:
                    ver_res = agent.audit(page, candidate_data)
                    post_audits[agent.section_name] = ver_res
                    if not ver_res.get("is_valid", False):
                        all_valid = False
                except Exception as e:
                    post_audits[agent.section_name] = {"is_valid": False, "error": str(e)}
                    all_valid = False

        return {
            "section": sec_key,
            "success": all_valid,
            "subagents_evaluated": sub_names,
            "subagents_healed": [a.section_name for a in agents_needing_heal],
            "cascade_passes": cascade_pass,
            "pre_audits": pre_audits,
            "healed_results": healed_results,
            "post_audits": post_audits
        }

    def auto_heal_current_page(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inspects active page, identifies top-level section coordinators, audits each,
        and heals only those sections that report anomalies.
        """
        # Only run top-level coordinators for auto-page healing to prevent redundant passes
        top_level_names = self.list_available_sections()
        applicable = [self._agents[name] for name in top_level_names if name in self._agents and self._agents[name].can_handle(page)]

        if not applicable:
            return {
                "success": False,
                "error": "No matching section agents found for current page state."
            }

        report = {
            "success": True,
            "applicable_agents": [a.section_name for a in applicable],
            "audit_reports": {},
            "healed_sections": []
        }

        for agent in applicable:
            audit_res = agent.audit(page, candidate_data)
            report["audit_reports"][agent.section_name] = audit_res

            if not audit_res.get("is_valid", False):
                logger.info(f"[SectionAgentDispatcher] Anomaly detected in '{agent.section_name}'. Healing...")
                heal_res = agent.heal(page, candidate_data)
                if heal_res.get("success", False):
                    report["healed_sections"].append(agent.section_name)
                else:
                    report["success"] = False

        return report
