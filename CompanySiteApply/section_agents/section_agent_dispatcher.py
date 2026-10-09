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
            default_agents = [
                # Top-level Section Coordinators
                ProfileSectionAgent(),
                QuestionnaireSectionAgent(),
                EducationSectionAgent(),
                ExperienceSectionAgent(),
                ReviewSectionAgent(),

                # Granular Sub-Agents
                PersonalDetailsSubAgent(),
                PreferredLocationSubAgent(),
                BinaryQuestionSubAgent(),
                TechnicalCompetencySubAgent(),
                DropdownQuestionSubAgent(),
                EducationSubAgent(),
                ExperienceSubAgent(),
                DocumentsSubAgent(),
                DiversitySubAgent(),
                SignatureSubAgent(),
                VisualVerifierSubAgent()
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
