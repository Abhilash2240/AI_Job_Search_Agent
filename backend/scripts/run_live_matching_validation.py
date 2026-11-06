# backend/scripts/run_live_matching_validation.py
"""
Phase 7 Controlled Live Validation:
Runs candidate-to-job matching on the verified legitimate candidate (Candidate 3)
against all 10 canonical job vacancies in `backend/ai_job_search.db`.
Audits component scoring, eligibility guardrails, explainability, and selectivity.
"""

import asyncio
import os
import sys
import json

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from db.database import AsyncSessionLocal, init, close
from models.candidate import Candidate
from models.canonical_job import CanonicalJob
from models.candidate_job_match import CandidateJobMatch
from matching.matching_service import matching_service
from matching.candidate_embedder import candidate_embedding_service, build_candidate_semantic_text
from sqlalchemy import select


async def run_live_audit():
    await init()
    print("=" * 80)
    print("PHASE 7: CANDIDATE-TO-JOB MATCHING ENGINE LIVE VALIDATION")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        # Step 1: Identify verified candidate
        cand = (await session.execute(select(Candidate).where(Candidate.id == 3))).scalar_one_or_none()
        assert cand is not None, "Candidate 3 not found in database!"
        profile_json = json.loads(cand.profile_json)
        confirmed_roles = json.loads(cand.confirmed_roles_json)
        name = profile_json.get("profile", {}).get("personal", {}).get("name", "Unknown")

        print(f"[1] Verified Candidate ID: {cand.id}")
        print(f"    Name: {name}")
        print(f"    Resume File: {cand.filename}")
        print(f"    Confirmed Roles ({len(confirmed_roles)}): {[r.get('role_title') for r in confirmed_roles]}")

        # Step 2: Candidate Embedding Generation
        print("\n[2] Generating Candidate Semantic Representation & Embedding...")
        cand_text, role_src = build_candidate_semantic_text(cand)
        print("--- Candidate Synthesized Semantic Text Snippet ---")
        print("\n".join(cand_text.split("\n\n")[:3]))
        print("---------------------------------------------------")
        cand_emb = await candidate_embedding_service.get_or_generate_embedding(
            db=session, candidate=cand, force=True
        )
        print(f"    Embedding ID: {cand_emb.id}")
        print(f"    Model: {cand_emb.model_name}")
        print(f"    Dimensions: {cand_emb.dimensions}")
        print(f"    Content SHA-256 Hash: {cand_emb.content_hash}")
        assert cand_emb.dimensions == 384
        print("    [PASS] Candidate embedding generated and persisted.")

        # Step 3: Run Candidate Matching across all 10 Canonical Vacancies
        print(f"\n[3] Executing Matching against Canonical Vacancies...")
        matches = await matching_service.run_matching_for_candidate(
            db=session, candidate_id=cand.id, force=True
        )
        print(f"    Total Vacancies Evaluated: {len(matches)}")
        assert len(matches) == 10, f"Expected 10 evaluated matches, got {len(matches)}"

        # Step 4: Inspect Ranked Results and Selectivity
        print("\n[4] Ranked Match Results Audit:")
        print("-" * 105)
        print(f"{'Rank':<5} {'Score':<8} {'Classification':<20} {'Eligibility':<24} {'Company':<10} {'Canonical Title'}")
        print("-" * 105)

        for i, m in enumerate(matches, 1):
            stmt = select(CanonicalJob).where(CanonicalJob.id == m.canonical_job_id)
            job = (await session.execute(stmt)).scalar_one()
            print(f"{i:<5} {m.composite_score:<8.1f} {m.match_classification:<20} {m.eligibility_status:<24} {job.company_name:<10} {job.canonical_job_title}")

        print("-" * 105)

        # Step 5: Detailed Component Inspection of Top Match
        top_match = matches[0]
        top_job = (await session.execute(select(CanonicalJob).where(CanonicalJob.id == top_match.canonical_job_id))).scalar_one()
        print(f"\n[5] Deep Breakdown of Top Match: '{top_job.canonical_job_title}' at {top_job.company_name}")
        print(f"    Composite Score: {top_match.composite_score}/100")
        print(f"    Component Scores:")
        print(f"     - Semantic Similarity (35%):  {top_match.semantic_score:.4f}")
        print(f"     - Skill Coverage (30%):      {top_match.skill_score:.4f}")
        print(f"     - Role Compatibility (15%):  {top_match.role_score:.4f}")
        print(f"     - Experience Seniority (10%):{top_match.experience_score:.4f}")
        print(f"     - Education Alignment (5%):  {top_match.education_score:.4f}")
        print(f"     - Location Alignment (5%):   {top_match.location_score:.4f}")
        print(f"    Score Coverage: {top_match.score_coverage:.2%}")
        print(f"    Eligibility Status: {top_match.eligibility_status}")
        print(f"    Matched Skills: {top_match.matched_skills}")
        print(f"    Missing Skills: {top_match.missing_skills}")
        print(f"\n[Explanation Text]:")
        print(f"    {top_match.explanation_data}")

        # Step 6: Verify Selectivity & Disqualification
        print("\n[6] Selectivity and Domain Discrimination Verification:")
        # Check non-technical and lead/staff roles
        for m in matches:
            job = (await session.execute(select(CanonicalJob).where(CanonicalJob.id == m.canonical_job_id))).scalar_one()
            if "Lead" in (job.seniority_level or "") or "LEAD_STAFF" in (job.seniority_level or ""):
                print(f"    [CHECK] Lead role '{job.canonical_job_title}': Eligibility={m.eligibility_status}, Disqual={m.disqualification_reasons}")
                assert m.eligibility_status == "INELIGIBLE", f"Expected LEAD_STAFF role to be INELIGIBLE, got {m.eligibility_status}"
            elif job.canonical_job_title in {"Procurement Specialist", "Relationship Manager"}:
                print(f"    [CHECK] Non-tech role '{job.canonical_job_title}': Score={m.composite_score:.1f}, RoleScore={m.role_score:.2f}")
                assert m.composite_score < 40.0, f"Expected non-tech role score < 40.0, got {m.composite_score}"

        print("[PASS] System correctly discriminates engineering vs non-engineering, and enforces seniority guardrails.")

        # Step 7: System Summary Metrics
        summary = await matching_service.get_summary(session)
        print("\n[7] System-wide Matching Summary:")
        print(json.dumps(summary, indent=2))
        assert summary["total_match_records"] >= 10
        print("[PASS] System summary metrics verified.")

    await close()
    print("\n" + "=" * 80)
    print("ALL PHASE 7 LIVE VALIDATION CHECKS COMPLETED [OK]")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_live_audit())

