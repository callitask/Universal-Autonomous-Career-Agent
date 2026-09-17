# AI CONTEXT & CHANGE LOG
# ==============================================================================
# [ENTRY #001]
# Term: [INIT]
# Timestamp: 2026-09-17 13:10:00 +05:30
# Issue / Context: Architectural separation of ATS Engines (Fingers) vs Company Variations (Nails).
# Changes Made: Created nails package for company-specific ATS customizations.
# Rationale: Direct company career sites (CompanySiteApply) share ATS engine cores (e.g., OracleCloudFinger),
#            but individual companies (JPMC, Bristlecone) have distinct questions, form fields, and workflows.
#            Nails encapsulate these company-specific variations on top of ATS Fingers.
# Preventative Notes: Never hardcode company-specific question logic in generic fingers; delegate to nails.
# ==============================================================================

from CompanySiteApply.nails.base_nail import BaseNail

__all__ = ["BaseNail"]
