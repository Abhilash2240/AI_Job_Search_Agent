import pytest
from matching.relevance_gate import relevance_gate, RoleFamily

def test_relevance_gate_classifications():
    target_roles = ["Python Backend Engineer", "Python Developer", "Platform Reliability Architect"]
    cand_skills = ["Python", "SQL", "Django", "Docker", "AWS", "Linux", "REST APIs"]

    # 1. Non-technical jobs MUST be rejected as IRRELEVANT
    irrelevant_jobs = [
        "Accounts Payable Manager",
        "Regional Collection Manager",
        "Procurement Specialist",
        "Portfolio Specialist - Wealth",
        "Relationship Manager",
        "Long Form Content Writer/Editor",
        "Manager - Compliance (PMS)",
        "Creative Illustrator",
        "Finance Content Creator",
        "Area Collections Manager",
    ]

    for title in irrelevant_jobs:
        res = relevance_gate.evaluate_relevance(
            job_title=title,
            job_description=None,
            job_required_skills=[],
            job_preferred_skills=[],
            candidate_target_roles=target_roles,
            candidate_verified_skills=cand_skills,
        )
        assert res["is_relevant"] is False, f"Expected {title} to be IRRELEVANT, got RELEVANT"
        assert res["relevance_status"] == "IRRELEVANT"
        assert len(res["rejection_reasons"]) > 0

    # 2. Genuine technical roles MUST be accepted as RELEVANT
    relevant_jobs = [
        ("Python Backend Engineer", ["Python", "SQL"]),
        ("Backend Developer", ["REST APIs", "SQL"]),
        ("Machine Learning Engineer II - Backend", ["Python", "Docker"]),
        ("SDE II - Data Engineer", ["Python", "SQL"]),
        ("Cloud Security Engineer", ["AWS", "Linux", "Python"]),
        ("Threat Detection Engineer", ["Python", "Linux"]),
    ]

    for title, skills in relevant_jobs:
        res = relevance_gate.evaluate_relevance(
            job_title=title,
            job_description="Build distributed backend services and data pipelines using Python.",
            job_required_skills=skills,
            job_preferred_skills=[],
            candidate_target_roles=target_roles,
            candidate_verified_skills=cand_skills,
        )
        assert res["is_relevant"] is True, f"Expected {title} to be RELEVANT, got IRRELEVANT"
        assert res["relevance_status"] == "RELEVANT"
        assert len(res["supporting_skills"]) > 0 or res["max_title_similarity"] >= 0.40

