# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [SECTION_AGENT_DISPATCHER_INIT]
# Timestamp: 2026-10-09 20:41:00 +05:30
# Issue / Context: Needed a central brain router to dynamically dispatch section-wise mini-agents on demand.
# Changes Made: Implemented SectionAgentDispatcher managing agent registry, stage-based lookup,
#               isolated heal routing, and autonomous page diagnosis.
# Rationale: Replaces all ad-hoc script writing with deterministic, surgical mini-agent dispatching.
# Preventative Notes: Always invoke agents with isolated execution boundaries.
# ==============================================================================

import logging
from typing import Any, Dict, List, Optional
from CompanySiteApply.section_agents.base_section_agent import BaseSectionAgent
from CompanySiteApply.section_agents.profile_section_agent import ProfileSectionAgent
from CompanySiteApply.section_agents.questionnaire_section_agent import QuestionnaireSectionAgent
from CompanySiteApply.section_agents.education_section_agent import EducationSectionAgent
from CompanySiteApply.section_agents.experience_section_agent import ExperienceSectionAgent
from CompanySiteApply.section_agents.review_section_agent import ReviewSectionAgent

logger = logging.getLogger(__name__)


class SectionAgentDispatcher:
    """
    Central Brain Dispatcher for Section-Wise Mini-Agents.
    Maintains the registry of all specialist section agents, resolves which agent
    is required based on page URL, DOM state, or diagnostic failure signatures,
    and executes isolated micro-repairs without full-page restarts.
    """

    def __init__(self, agents: Optional[List[BaseSectionAgent]] = None):
        if agents is not None:
            self._agents = {a.section_name.lower(): a for a in agents}
        else:
            default_agents = [
                ProfileSectionAgent(),
                QuestionnaireSectionAgent(),
                EducationSectionAgent(),
                ExperienceSectionAgent(),
                ReviewSectionAgent()
            ]
            self._agents = {a.section_name.lower(): a for a in default_agents}

    def register_agent(self, agent: BaseSectionAgent):
        """Registers a custom or platform-specific section agent."""
        self._agents[agent.section_name.lower()] = agent

    def get_agent(self, section_name: str) -> Optional[BaseSectionAgent]:
        """Retrieves a specific section agent by name."""
        return self._agents.get(section_name.lower())

    def list_available_sections(self) -> List[str]:
        """Returns the list of all registered section names."""
        return list(self._agents.keys())

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

    def dispatch_heal(self, section_name: str, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Surgically dispatches a single named section agent to heal its domain.
        Guarantees complete isolation from other sections.
        """
        agent = self.get_agent(section_name)
        if not agent:
            return {
                "success": False,
                "error": f"Unknown section agent '{section_name}'. Available: {self.list_available_sections()}"
            }

        logger.info(f"[SectionAgentDispatcher] Dispatched '{agent.section_name}' for surgical healing...")
        return agent.heal(page, candidate_data)

    def dispatch_audit(self, section_name: str, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatches a single named section agent to audit its domain.
        """
        agent = self.get_agent(section_name)
        if not agent:
            return {
                "success": False,
                "error": f"Unknown section agent '{section_name}'. Available: {self.list_available_sections()}"
            }

        return agent.audit(page, candidate_data)

    def auto_heal_current_page(self, page: Any, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inspects active page, identifies all applicable section agents, audits each,
        and heals only those sections that report anomalies.
        """
        applicable = self.resolve_agents_for_page(page)
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
