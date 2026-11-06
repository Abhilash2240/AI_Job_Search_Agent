# backend/matching/relevance_gate.py
"""
Technical-Role Relevance Gate for AI Job Search Agent.
Pre-evaluates canonical job vacancies prior to composite scoring to verify
that a vacancy belongs to a career direction genuinely supported by the candidate's profile.

Distinguishes:
1. Relevance: Career direction & role-family compatibility.
2. Eligibility: Experience, education, and vacancy status constraints.
3. Composite Match: Strength of alignment within relevant opportunities.
"""

import enum
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from embeddings.model_loader import get_model
from embeddings.embedding_service import embed_text

logger = logging.getLogger("relevance_gate")


class RoleFamily(str, enum.Enum):
    # Technical Families
    SOFTWARE_ENGINEERING = "SOFTWARE_ENGINEERING"
    DATA_AND_AI = "DATA_AND_AI"
    CLOUD_AND_DEVOPS = "CLOUD_AND_DEVOPS"
    CYBERSECURITY = "CYBERSECURITY"
    QA_AND_TESTING = "QA_AND_TESTING"
    PRODUCT_AND_TECHNICAL_MGMT = "PRODUCT_AND_TECHNICAL_MGMT"

    # Non-Technical / Business Families
    FINANCE_AND_ACCOUNTING = "FINANCE_AND_ACCOUNTING"
    SALES_AND_BUSINESS_DEV = "SALES_AND_BUSINESS_DEV"
    COLLECTIONS_AND_RECOVERIES = "COLLECTIONS_AND_RECOVERIES"
    PROCUREMENT_AND_OPERATIONS = "PROCUREMENT_AND_OPERATIONS"
    LEGAL_AND_COMPLIANCE = "LEGAL_AND_COMPLIANCE"
    CONTENT_AND_CREATIVE = "CONTENT_AND_CREATIVE"
    HUMAN_RESOURCES = "HUMAN_RESOURCES"
    OTHER_NON_TECHNICAL = "OTHER_NON_TECHNICAL"


TECHNICAL_FAMILIES = {
    RoleFamily.SOFTWARE_ENGINEERING.value,
    RoleFamily.DATA_AND_AI.value,
    RoleFamily.CLOUD_AND_DEVOPS.value,
    RoleFamily.CYBERSECURITY.value,
    RoleFamily.QA_AND_TESTING.value,
    RoleFamily.PRODUCT_AND_TECHNICAL_MGMT.value,
}

NON_TECHNICAL_FAMILIES = {
    RoleFamily.FINANCE_AND_ACCOUNTING.value,
    RoleFamily.SALES_AND_BUSINESS_DEV.value,
    RoleFamily.COLLECTIONS_AND_RECOVERIES.value,
    RoleFamily.PROCUREMENT_AND_OPERATIONS.value,
    RoleFamily.LEGAL_AND_COMPLIANCE.value,
    RoleFamily.CONTENT_AND_CREATIVE.value,
    RoleFamily.HUMAN_RESOURCES.value,
    RoleFamily.OTHER_NON_TECHNICAL.value,
}

# Regex and keyword patterns for role family classification
ROLE_FAMILY_PATTERNS = [
    # Collections & Recoveries
    (
        RoleFamily.COLLECTIONS_AND_RECOVERIES,
        [
            r"\bcollection(s)?\b",
            r"\brecover(y|ies)\b",
            r"\bdebt\b",
            r"\btelecalling\b",
            r"\bcredit control\b",
        ],
    ),
    # Finance & Accounting
    (
        RoleFamily.FINANCE_AND_ACCOUNTING,
        [
            r"\baccounts payable\b",
            r"\baccounts receivable\b",
            r"\baccounting\b",
            r"\baccountant\b",
            r"\bbookkeeper\b",
            r"\btaxation\b",
            r"\baudit(or|ing)?\b",
            r"\bwealth\b",
            r"\bportfolio\b",
            r"\bfunds?\b",
            r"\btreasury\b",
            r"\bfinance content\b",
        ],
    ),
    # Procurement & Operations
    (
        RoleFamily.PROCUREMENT_AND_OPERATIONS,
        [
            r"\bprocurement\b",
            r"\bsupply chain\b",
            r"\bpurchas(e|ing)\b",
            r"\bvendor management\b",
            r"\bfacilities\b",
            r"\bwarehouse\b",
            r"\blogistics\b",
        ],
    ),
    # Legal & Compliance
    (
        RoleFamily.LEGAL_AND_COMPLIANCE,
        [
            r"\bcompliance\b",
            r"\blegal\b",
            r"\bregulatory\b",
            r"\baml\b",
            r"\bgovernance\b",
            r"\bcompany secretary\b",
        ],
    ),
    # Content & Creative
    (
        RoleFamily.CONTENT_AND_CREATIVE,
        [
            r"\bcontent writer\b",
            r"\bwriter/editor\b",
            r"\bcopywriter\b",
            r"\billustrat(or|ion)\b",
            r"\bgraphic design(er)?\b",
            r"\bcreative director\b",
            r"\bcontent creator\b",
            r"\bvideo editor\b",
            r"\banimat(or|ion)\b",
        ],
    ),
    # Sales & Business Dev
    (
        RoleFamily.SALES_AND_BUSINESS_DEV,
        [
            r"\brelationship manager\b",
            r"\bsales\b",
            r"\bbusiness development\b",
            r"\bmerchant acquisition\b",
            r"\bpartnerships\b",
            r"\baccount executive\b",
            r"\btele-?sales\b",
        ],
    ),
    # HR & People
    (
        RoleFamily.HUMAN_RESOURCES,
        [
            r"\btalent acquisition\b",
            r"\brecruit(er|ing)\b",
            r"\bhuman resources\b",
            r"\bpeople partner\b",
            r"\bpayroll\b",
        ],
    ),
    # Cybersecurity
    (
        RoleFamily.CYBERSECURITY,
        [
            r"\bsecurity\b",
            r"\bthreat\b",
            r"\bsoc\b",
            r"\binfosec\b",
            r"\bcyber\b",
            r"\bpenetration\b",
            r"\bvulnerability\b",
        ],
    ),
    # Cloud & DevOps
    (
        RoleFamily.CLOUD_AND_DEVOPS,
        [
            r"\bdevops\b",
            r"\bcloud\b",
            r"\bsre\b",
            r"\bsite reliability\b",
            r"\bplatform\b",
            r"\binfrastructure\b",
            r"\bsysadmin\b",
            r"\bkubernetes\b",
        ],
    ),
    # Data & AI
    (
        RoleFamily.DATA_AND_AI,
        [
            r"\bdata engineer\b",
            r"\bdata scientist\b",
            r"\bmachine learning\b",
            r"\bml engineer\b",
            r"\bai engineer\b",
            r"\bapplied scientist\b",
            r"\banalytics engineer\b",
            r"\bbig data\b",
            r"\bnlp\b",
            r"\bcomputer vision\b",
            r"\bdeep learning\b",
        ],
    ),
    # QA & Testing
    (
        RoleFamily.QA_AND_TESTING,
        [
            r"\bqa\b",
            r"\bquality assurance\b",
            r"\bsdet\b",
            r"\bautomation test\b",
            r"\btest engineer\b",
            r"\bsoftware tester\b",
        ],
    ),
    # Software Engineering (Default technical umbrella)
    (
        RoleFamily.SOFTWARE_ENGINEERING,
        [
            r"\bsoftware engineer\b",
            r"\bsoftware developer\b",
            r"\bdeveloper\b",
            r"\bengineer\b",
            r"\bprogrammer\b",
            r"\bbackend\b",
            r"\bfrontend\b",
            r"\bfullstack\b",
            r"\bfull-?stack\b",
            r"\bpython\b",
            r"\bjava\b",
            r"\bapi\b",
            r"\bsde\b",
        ],
    ),
]


class TechnicalRelevanceGate:
    """Evaluates whether a job vacancy belongs to a candidate's valid career direction."""

    def classify_role_family(self, title: str, description: Optional[str] = None) -> RoleFamily:
        """Classifies a job into a standard RoleFamily based on title and description evidence."""
        t_clean = (title or "").lower()
        desc_clean = (description or "").lower()[:500] if description else ""

        # Check title first (highest precision)
        for family, patterns in ROLE_FAMILY_PATTERNS:
            for p in patterns:
                if re.search(p, t_clean):
                    return family

        # Fallback to description keyword density
        for family, patterns in ROLE_FAMILY_PATTERNS:
            for p in patterns:
                if re.search(p, desc_clean):
                    return family

        return RoleFamily.OTHER_NON_TECHNICAL

    def compute_title_similarity(
        self,
        job_title: str,
        target_roles: List[str],
    ) -> Tuple[float, str]:
        """
        Computes the maximum SBERT cosine similarity between a job title
        and the candidate's target roles.
        """
        if not target_roles:
            return 0.5, "No target roles provided"

        model = get_model()
        # Compute embeddings
        job_emb = embed_text(job_title)
        best_sim = -1.0
        best_role = target_roles[0]

        for role in target_roles:
            r_emb = embed_text(role)
            sim = float(np.dot(job_emb, r_emb) / (np.linalg.norm(job_emb) * np.linalg.norm(r_emb) + 1e-9))
            if sim > best_sim:
                best_sim = sim
                best_role = role

        return round(float(np.clip(best_sim, 0.0, 1.0)), 4), best_role

    def evaluate_relevance(
        self,
        job_title: str,
        job_description: Optional[str],
        job_required_skills: List[str],
        job_preferred_skills: List[str],
        candidate_target_roles: List[str],
        candidate_verified_skills: List[str],
        candidate_profile_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Complete technical relevance evaluation.
        Returns:
            Dict containing:
            - is_relevant: bool
            - relevance_status: "RELEVANT" | "IRRELEVANT"
            - role_family: str
            - relevance_score: float (0.0 - 1.0)
            - max_title_similarity: float
            - best_matching_target_role: str
            - supporting_skills: List[str]
            - relevance_reasons: List[str]
            - rejection_reasons: List[str]
        """
        relevance_reasons: List[str] = []
        rejection_reasons: List[str] = []

        # Normalize target roles to list of strings
        clean_target_roles = [
            r.get("role_title", r.get("title", str(r))) if isinstance(r, dict) else str(r)
            for r in candidate_target_roles
        ]

        # 1. Determine job role family
        role_family = self.classify_role_family(job_title, job_description)

        # 2. Check candidate target family direction
        # Assume candidate has a technical career orientation if any target role is technical
        cand_targets_lower = [r.lower() for r in clean_target_roles]
        candidate_is_technical = any(
            any(k in r for k in ["engineer", "developer", "software", "data", "cloud", "security", "backend", "frontend", "sde", "architect", "scientist", "ai", "ml"])
            for r in cand_targets_lower
        ) or len(candidate_verified_skills) > 0

        # 3. Check for Non-Technical Role Family Disqualification
        if candidate_is_technical and role_family.value in NON_TECHNICAL_FAMILIES:
            family_name = role_family.value.replace("_", " ").title()
            rejection_reasons.append(
                f"Non-technical role family: '{family_name}'. Unrelated to candidate technical target roles."
            )
            return {
                "is_relevant": False,
                "relevance_status": "IRRELEVANT",
                "role_family": role_family.value,
                "relevance_score": 0.10,
                "max_title_similarity": 0.0,
                "best_matching_target_role": clean_target_roles[0] if clean_target_roles else "None",
                "supporting_skills": [],
                "relevance_reasons": [],
                "rejection_reasons": rejection_reasons,
            }

        # 4. Compute SBERT semantic similarity between Job Title and Target Roles
        max_sim, best_role = self.compute_title_similarity(job_title, clean_target_roles)

        # 5. Identify Supporting Technical Skills
        clean_cand_skills = {s.lower().strip() for s in candidate_verified_skills}
        all_job_skills = {s.lower().strip() for s in (job_required_skills + job_preferred_skills)}
        supporting = [s for s in candidate_verified_skills if s.lower().strip() in all_job_skills]

        # 6. Evaluate Technical Evidence & Responsibilities
        t_clean = job_title.lower()
        has_direct_title_token = any(
            t in t_clean for t in ["engineer", "developer", "backend", "frontend", "data", "cloud", "security", "sde", "software", "scientist"]
        )

        # Calculate continuous relevance score
        # Base: 0.50 * title_sim + 0.30 * skill_support + 0.20 * direct_token
        skill_factor = min(1.0, len(supporting) / 3.0)
        relevance_score = round(0.50 * max_sim + 0.30 * skill_factor + (0.20 if has_direct_title_token else 0.0), 4)

        if max_sim >= 0.45:
            relevance_reasons.append(f"Title has strong semantic similarity ({max_sim:.1%}) to target role '{best_role}'.")
        elif max_sim >= 0.35:
            relevance_reasons.append(f"Title has moderate semantic similarity ({max_sim:.1%}) to target role '{best_role}'.")
        else:
            rejection_reasons.append(f"Low semantic similarity ({max_sim:.1%}) between title '{job_title}' and target roles.")

        if supporting:
            relevance_reasons.append(f"Shares {len(supporting)} technical skill(s): {', '.join(supporting[:4])}.")
        else:
            if not has_direct_title_token:
                rejection_reasons.append("No technical skills overlap with vacancy requirements.")

        # Final Relevance Decision Gate
        # A vacancy is relevant if:
        # - It is in a TECHNICAL family AND (max_sim >= 0.40 OR len(supporting) >= 2 OR (has_direct_title_token and max_sim >= 0.30))
        is_relevant = (
            role_family.value in TECHNICAL_FAMILIES
            and (
                max_sim >= 0.40
                or len(supporting) >= 2
                or (has_direct_title_token and max_sim >= 0.30)
            )
        )

        if not is_relevant and not rejection_reasons:
            rejection_reasons.append("Does not meet minimum technical role relevance threshold (score < 0.45).")

        return {
            "is_relevant": is_relevant,
            "relevance_status": "RELEVANT" if is_relevant else "IRRELEVANT",
            "role_family": role_family.value,
            "relevance_score": relevance_score,
            "max_title_similarity": max_sim,
            "best_matching_target_role": best_role,
            "supporting_skills": supporting,
            "relevance_reasons": relevance_reasons,
            "rejection_reasons": rejection_reasons,
        }


# Global singleton instance
relevance_gate = TechnicalRelevanceGate()
