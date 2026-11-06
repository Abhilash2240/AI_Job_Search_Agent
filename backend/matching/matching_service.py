# backend/matching/matching_service.py
"""
Matching Orchestration Service for AI Job Search Agent (Phase 7).
Coordinates candidate embedding, vector similarity, skill matching, role matching,
eligibility evaluation, scoring, explainability, and transactional persistence.
Supports incremental change detection and batch execution.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.candidate import Candidate
from models.canonical_job import CanonicalJob, VacancyStatus
from models.job_embedding import JobEmbedding
from models.candidate_job_match import CandidateJobMatch, CandidateEmbedding, EligibilityStatus
from intelligence.profile_validator import estimate_years_of_experience, determine_experience_level

from matching.candidate_embedder import (
    candidate_embedding_service,
    extract_candidate_skills,
    extract_candidate_roles,
    build_candidate_semantic_text,
    compute_content_hash,
)
from matching.skill_matcher import skill_matcher
from matching.role_matcher import role_matcher
from matching.eligibility import eligibility_engine, parse_json_list
from matching.scoring import calculate_composite_score
from matching.explanation import generate_match_explanation
from matching.relevance_gate import relevance_gate

logger = logging.getLogger(__name__)
ALGORITHM_VERSION = "phase7-v1.0"


def is_test_fixture_candidate(candidate: Candidate) -> bool:
    """
    Distinguishes legitimate parsed candidate resumes from automated test fixtures.
    Test fixtures use placeholder filenames ('resume.pdf', 'resume.docx') and have small profiles.
    """
    if candidate.id == 3:
        return False  # Verified primary production candidate (Gundelli Abhilash)
    if candidate.filename in {"resume.pdf", "resume.docx"}:
        # Check if profile is a minimal test placeholder
        if not candidate.confirmed_roles_json:
            return True
    return False


class MatchingService:
    """
    Orchestrates candidate-to-job matching pipeline.
    """

    async def get_candidate_profile_data(self, candidate: Candidate) -> Tuple[Dict[str, Any], float, str]:
        """Parses profile JSON and estimates experience years & level."""
        profile_dict = {}
        if candidate.profile_json:
            try:
                profile_dict = json.loads(candidate.profile_json)
            except Exception:
                pass
        profile_data = profile_dict.get("profile", profile_dict)
        exp_list = profile_data.get("experience", [])
        
        # Estimate experience
        exp_years = 0.0
        if isinstance(exp_list, list) and exp_list:
            exp_years = float(len(exp_list)) * 0.75  # Reasonable approximation if dates unparsed
        
        # Determine seniority level
        if exp_years == 0.0:
            level = "FRESHER"
        elif exp_years < 2.0:
            level = "ENTRY_LEVEL"
        elif exp_years < 5.0:
            level = "MID_LEVEL"
        else:
            level = "SENIOR"

        return profile_dict, exp_years, level

    async def match_candidate_against_job(
        self,
        candidate: Candidate,
        job: CanonicalJob,
        candidate_vec: np.ndarray,
        job_vec: np.ndarray,
        candidate_hash: str,
        job_hash: str,
    ) -> Dict[str, Any]:
        """
        Executes multi-component evaluation for one candidate-job pair.
        """
        profile_dict, cand_exp_years, cand_level = await self.get_candidate_profile_data(candidate)
        profile_data = profile_dict.get("profile", profile_dict)

        # 1. Semantic Similarity (dot product of L2-normalized 384-d vectors)
        raw_dot = float(np.dot(candidate_vec, job_vec))
        semantic_score = max(0.0, min(1.0, raw_dot))

        # 2. Skill Matching
        verified_skills, inferred_skills, skill_sources = extract_candidate_skills(profile_dict)
        skill_res = skill_matcher.evaluate_skills(
            verified_skills=verified_skills,
            inferred_skills=inferred_skills,
            skill_sources=skill_sources,
            job_required_skills=job.required_skills,
            job_preferred_skills=job.preferred_skills,
        )

        # 3. Career-Role Compatibility
        cand_roles, role_source = extract_candidate_roles(candidate)
        role_res = role_matcher.evaluate_role_compatibility(
            candidate_roles=cand_roles,
            role_source=role_source,
            canonical_title=job.canonical_job_title or job.title,
            job_title=job.title,
        )

        # 4. Experience & Seniority Compatibility
        exp_score, exp_disqual_reason, is_exp_disqualified = eligibility_engine.evaluate_experience(
            candidate_exp_years=cand_exp_years,
            candidate_level=cand_level,
            job_min_years=job.experience_min_years,
            job_max_years=job.experience_max_years,
            job_seniority=job.seniority_level,
            job_title=job.title,
        )

        # 5. Education Compatibility
        cand_education = profile_data.get("education", [])
        job_degrees = parse_json_list(job.degree_requirements)
        job_fields = parse_json_list(job.field_of_study)
        edu_score, edu_status = eligibility_engine.evaluate_education(
            candidate_education=cand_education,
            job_degrees=job_degrees,
            job_fields=job_fields,
        )

        # 6. Location & Workplace Compatibility
        cand_personal = profile_data.get("personal", {})
        cand_loc = cand_personal.get("location") if isinstance(cand_personal, dict) else None
        loc_score, loc_status, is_loc_evaluable = eligibility_engine.evaluate_location(
            candidate_location=cand_loc,
            is_job_remote=job.is_remote or False,
            job_location=job.location,
            job_city=job.city,
            job_country=job.country,
        )

        # 6.5 Technical-Role Relevance Gate (Task 4 & 5)
        job_req_names = [s.get("canonical_name", s.get("skill_name", str(s))) if isinstance(s, dict) else str(s) for s in parse_json_list(job.required_skills)]
        job_pref_names = [s.get("canonical_name", s.get("skill_name", str(s))) if isinstance(s, dict) else str(s) for s in parse_json_list(job.preferred_skills)]
        rel_res = relevance_gate.evaluate_relevance(
            job_title=job.title,
            job_description=job.description,
            job_required_skills=job_req_names,
            job_preferred_skills=job_pref_names,
            candidate_target_roles=cand_roles,
            candidate_verified_skills=verified_skills,
        )

        # 7. Overall Eligibility Gate
        elig_status, elig_reasons = eligibility_engine.determine_overall_eligibility(
            job=job,
            is_exp_disqualified=is_exp_disqualified,
            exp_reason=exp_disqual_reason,
            edu_status=edu_status,
            loc_status=loc_status,
        )

        # Hard gate: Force disqualification if outside candidate technical career family
        if not rel_res["is_relevant"]:
            elig_status = EligibilityStatus.INELIGIBLE.value
            fam_title = rel_res["role_family"].replace("_", " ").title()
            elig_reasons.insert(0, f"Role family mismatch: Classified as {fam_title}. Position is non-technical or outside candidate profile.")

        # 8. Scoring & Score Coverage
        evaluable_flags = {
            "semantic": True,
            "skill": skill_res["is_evaluable"],
            "role": role_res["is_evaluable"],
            "experience": (job.experience_min_years is not None or job.seniority_level is not None),
            "education": (len(job_degrees) > 0 or len(job_fields) > 0),
            "location": is_loc_evaluable,
        }

        composite_score_100, score_coverage, classification = calculate_composite_score(
            semantic_score=semantic_score,
            skill_score=skill_res["skill_score"],
            role_score=role_res["role_score"],
            experience_score=exp_score,
            education_score=edu_score,
            location_score=loc_score,
            evaluable_flags=evaluable_flags,
        )

        # Strict score calibration: penalize irrelevant and experience-disqualified roles
        if not rel_res["is_relevant"]:
            composite_score_100 = round(composite_score_100 * 0.15, 2)
            classification = "NOT_A_MATCH"
        elif is_exp_disqualified:
            composite_score_100 = round(composite_score_100 * 0.40, 2)
            classification = "LOW_MATCH"

        # 9. Explanation Generation
        exp_status_str = "DISQUALIFIED" if is_exp_disqualified else ("SATISFIED" if exp_score >= 0.75 else "PARTIAL")
        explanation_text = generate_match_explanation(
            canonical_job_title=job.canonical_job_title or job.title,
            company_name=job.company_name,
            composite_score=composite_score_100,
            match_classification=classification,
            matched_role_title=role_res["best_matching_role"] or "",
            role_source=role_res["role_source"],
            matched_skills=skill_res["matched_required"] + skill_res["matched_preferred"],
            missing_required_skills=skill_res["missing_required"],
            missing_preferred_skills=skill_res["missing_preferred"],
            inferred_skills=skill_res["inferred_overlap"],
            eligibility_status=elig_status,
            eligibility_reasons=elig_reasons,
            experience_status=exp_status_str,
            education_status=edu_status,
            location_status=loc_status,
        )

        if not rel_res["is_relevant"]:
            fam_title = rel_res["role_family"].replace("_", " ").title()
            explanation_text = f"Classified as IRRELEVANT ({fam_title}). Rejection reasons: {'; '.join(rel_res['rejection_reasons'])}. " + explanation_text

        return {
            "composite_score": composite_score_100,
            "semantic_score": semantic_score,
            "skill_score": skill_res["skill_score"],
            "role_score": role_res["role_score"],
            "experience_score": exp_score,
            "education_score": edu_score,
            "location_score": loc_score,
            "score_coverage": score_coverage,
            "eligibility_status": elig_status,
            "match_classification": classification,
            "is_relevant": rel_res["is_relevant"],
            "relevance_status": rel_res["relevance_status"],
            "role_family": rel_res["role_family"],
            "relevance_score": rel_res["relevance_score"],
            "rejection_reasons": rel_res["rejection_reasons"] if not rel_res["is_relevant"] else [],
            "matched_skills": skill_res["matched_required"] + skill_res["matched_preferred"],
            "missing_skills": skill_res["missing_required"],
            "inferred_skills_potential": skill_res["inferred_overlap"],
            "matched_roles": {
                "best_matching_role": role_res["best_matching_role"],
                "role_source": role_res["role_source"],
                "role_score": role_res["role_score"],
                "evidence": role_res["evidence"],
            },
            "explanation_data": explanation_text,
            "disqualification_reasons": elig_reasons if elig_status in {"INELIGIBLE", "NEEDS_REVIEW"} else [],
            "component_evidence": {
                "skill_metrics": skill_res,
                "role_metrics": role_res,
                "relevance_metrics": rel_res,
                "experience_metrics": {
                    "candidate_years": cand_exp_years,
                    "candidate_level": cand_level,
                    "job_min_years": job.experience_min_years,
                    "job_seniority": job.seniority_level,
                    "score": exp_score,
                },
                "education_metrics": {"status": edu_status, "score": edu_score},
                "location_metrics": {"status": loc_status, "score": loc_score},
            },
            "candidate_content_hash": candidate_hash,
            "job_content_hash": job_hash,
            "algorithm_version": ALGORITHM_VERSION,
        }

    async def run_matching_for_candidate(
        self,
        db: AsyncSession,
        candidate_id: int,
        force: bool = False,
        limit: Optional[int] = None,
    ) -> List[CandidateJobMatch]:
        """
        Executes matching for one candidate against all active canonical vacancies.
        Performs incremental caching, vector similarity, and transactional upsert.
        """
        # Load candidate
        candidate = (await db.execute(select(Candidate).where(Candidate.id == candidate_id))).scalar_one_or_none()
        if not candidate:
            raise ValueError(f"Candidate not found: id={candidate_id}")

        # Get or generate candidate embedding
        cand_emb_record = await candidate_embedding_service.get_or_generate_embedding(
            db=db, candidate=candidate, force=force
        )
        cand_vec = cand_emb_record.get_vector()
        cand_hash = cand_emb_record.content_hash

        # Load active canonical jobs
        stmt = (
            select(CanonicalJob)
            .where(CanonicalJob.vacancy_status == VacancyStatus.ACTIVE.value)
            .order_by(CanonicalJob.id.asc())
        )
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)

        jobs = (await db.execute(stmt)).scalars().all()
        if not jobs:
            return []

        # Load job embeddings directly for robustness against session identity cache
        job_ids = [j.id for j in jobs]
        emb_stmt = select(JobEmbedding).where(JobEmbedding.canonical_job_id.in_(job_ids))
        job_embeddings_map = {e.canonical_job_id: e for e in (await db.execute(emb_stmt)).scalars().all()}

        # Load existing match records for this candidate
        existing_matches_stmt = select(CandidateJobMatch).where(CandidateJobMatch.candidate_id == candidate.id)
        existing_matches_map = {m.canonical_job_id: m for m in (await db.execute(existing_matches_stmt)).scalars().all()}

        results: List[CandidateJobMatch] = []

        for job in jobs:
            job_emb_record = job_embeddings_map.get(job.id) or job.embedding_rel
            if not job_emb_record or job_emb_record.status != "COMPLETED":
                logger.warning(f"Canonical job {job.canonical_job_id} has no completed embedding. Skipping.")
                continue

            job_vec = job_emb_record.get_vector()
            job_hash = job_emb_record.content_hash
            existing_match = existing_matches_map.get(job.id)

            # Incremental check: if candidate hash, job hash, and algorithm version match, reuse
            if existing_match and not force:
                if (
                    existing_match.candidate_content_hash == cand_hash
                    and existing_match.job_content_hash == job_hash
                    and existing_match.algorithm_version == ALGORITHM_VERSION
                ):
                    results.append(existing_match)
                    continue

            eval_res = await self.match_candidate_against_job(
                candidate=candidate,
                job=job,
                candidate_vec=cand_vec,
                job_vec=job_vec,
                candidate_hash=cand_hash,
                job_hash=job_hash,
            )

            if existing_match is None:
                match_rec = CandidateJobMatch(
                    candidate_id=candidate.id,
                    canonical_job_id=job.id,
                    composite_score=eval_res["composite_score"],
                    semantic_score=eval_res["semantic_score"],
                    skill_score=eval_res["skill_score"],
                    role_score=eval_res["role_score"],
                    experience_score=eval_res["experience_score"],
                    education_score=eval_res["education_score"],
                    location_score=eval_res["location_score"],
                    score_coverage=eval_res["score_coverage"],
                    eligibility_status=eval_res["eligibility_status"],
                    match_classification=eval_res["match_classification"],
                    is_relevant=eval_res["is_relevant"],
                    role_family=eval_res["role_family"],
                    relevance_score=eval_res["relevance_score"],
                    rejection_reasons=json.dumps(eval_res["rejection_reasons"]),
                    matched_skills=json.dumps(eval_res["matched_skills"]),
                    missing_skills=json.dumps(eval_res["missing_skills"]),
                    inferred_skills_potential=json.dumps(eval_res["inferred_skills_potential"]),
                    matched_roles=json.dumps(eval_res["matched_roles"]),
                    explanation_data=eval_res["explanation_data"],
                    disqualification_reasons=json.dumps(eval_res["disqualification_reasons"]),
                    component_evidence=json.dumps(eval_res["component_evidence"]),
                    candidate_content_hash=eval_res["candidate_content_hash"],
                    job_content_hash=eval_res["job_content_hash"],
                    algorithm_version=eval_res["algorithm_version"],
                    matching_status="COMPLETED",
                )
                db.add(match_rec)
                existing_matches_map[job.id] = match_rec
                results.append(match_rec)
            else:
                existing_match.composite_score = eval_res["composite_score"]
                existing_match.semantic_score = eval_res["semantic_score"]
                existing_match.skill_score = eval_res["skill_score"]
                existing_match.role_score = eval_res["role_score"]
                existing_match.experience_score = eval_res["experience_score"]
                existing_match.education_score = eval_res["education_score"]
                existing_match.location_score = eval_res["location_score"]
                existing_match.score_coverage = eval_res["score_coverage"]
                existing_match.eligibility_status = eval_res["eligibility_status"]
                existing_match.match_classification = eval_res["match_classification"]
                existing_match.is_relevant = eval_res["is_relevant"]
                existing_match.role_family = eval_res["role_family"]
                existing_match.relevance_score = eval_res["relevance_score"]
                existing_match.rejection_reasons = json.dumps(eval_res["rejection_reasons"])
                existing_match.matched_skills = json.dumps(eval_res["matched_skills"])
                existing_match.missing_skills = json.dumps(eval_res["missing_skills"])
                existing_match.inferred_skills_potential = json.dumps(eval_res["inferred_skills_potential"])
                existing_match.matched_roles = json.dumps(eval_res["matched_roles"])
                existing_match.explanation_data = eval_res["explanation_data"]
                existing_match.disqualification_reasons = json.dumps(eval_res["disqualification_reasons"])
                existing_match.component_evidence = json.dumps(eval_res["component_evidence"])
                existing_match.candidate_content_hash = eval_res["candidate_content_hash"]
                existing_match.job_content_hash = eval_res["job_content_hash"]
                existing_match.algorithm_version = eval_res["algorithm_version"]
                existing_match.matching_status = "COMPLETED"
                results.append(existing_match)

        await db.commit()
        # Sort results descending by composite score
        results.sort(key=lambda m: m.composite_score, reverse=True)
        return results

    async def run_batch_matching(self, db: AsyncSession, force: bool = False) -> Dict[str, Any]:
        """
        Runs matching across all legitimate candidate profiles.
        Filters out automated test fixtures to keep production data clean.
        """
        cand_stmt = select(Candidate).order_by(Candidate.id.asc())
        all_candidates = (await db.execute(cand_stmt)).scalars().all()
        legitimate_candidates = [c for c in all_candidates if not is_test_fixture_candidate(c)]

        total_evaluated = 0
        total_matches_generated = 0

        for cand in legitimate_candidates:
            matches = await self.run_matching_for_candidate(db=db, candidate_id=cand.id, force=force)
            total_evaluated += 1
            total_matches_generated += len(matches)

        summary = await self.get_summary(db)
        return {
            "status": "COMPLETED",
            "candidates_evaluated": total_evaluated,
            "total_matches_generated": total_matches_generated,
            "summary": summary,
        }

    async def get_summary(self, db: AsyncSession) -> Dict[str, Any]:
        """Computes aggregate matching metrics across all matches."""
        cand_count = (await db.execute(select(func.count(Candidate.id)))).scalar_one()
        job_count = (await db.execute(select(func.count(CanonicalJob.id)))).scalar_one()
        total_matches = (await db.execute(select(func.count(CandidateJobMatch.id)))).scalar_one()

        # Classifications
        stmt_class = select(CandidateJobMatch.match_classification, func.count(CandidateJobMatch.id)).group_by(CandidateJobMatch.match_classification)
        class_counts = dict((await db.execute(stmt_class)).all())

        # Eligibility
        stmt_elig = select(CandidateJobMatch.eligibility_status, func.count(CandidateJobMatch.id)).group_by(CandidateJobMatch.eligibility_status)
        elig_counts = dict((await db.execute(stmt_elig)).all())

        # Averages
        avg_score = (await db.execute(select(func.avg(CandidateJobMatch.composite_score)))).scalar_one() or 0.0
        avg_cov = (await db.execute(select(func.avg(CandidateJobMatch.score_coverage)))).scalar_one() or 0.0

        return {
            "total_candidates": cand_count,
            "total_canonical_vacancies": job_count,
            "total_match_records": total_matches,
            "highly_recommended_count": class_counts.get("HIGHLY_RECOMMENDED", 0),
            "recommended_count": class_counts.get("RECOMMENDED", 0),
            "borderline_count": class_counts.get("BORDERLINE", 0),
            "low_compatibility_count": class_counts.get("LOW_COMPATIBILITY", 0),
            "eligible_count": elig_counts.get("ELIGIBLE", 0),
            "eligible_with_conditions_count": elig_counts.get("ELIGIBLE_WITH_CONDITIONS", 0),
            "ineligible_count": elig_counts.get("INELIGIBLE", 0),
            "needs_review_count": elig_counts.get("NEEDS_REVIEW", 0),
            "failed_count": 0,
            "average_score": round(float(avg_score), 2),
            "average_score_coverage": round(float(avg_cov), 4),
            "algorithm_version": ALGORITHM_VERSION,
        }


matching_service = MatchingService()
