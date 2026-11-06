"""
Cross-Provider Job Deduplication Engine (Phase 5).
Executes Stage 1 (Exact), Stage 2 (Normalized), and Stage 3 (Fuzzy) matching
with strict false-positive prevention safeguards.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from models.canonical_job import DuplicateType
from deduplication.url_normalizer import CanonicalUrlNormalizer
from deduplication.similarity import JobSimilarityCalculator


@dataclass
class MatchEvaluation:
    duplicate_type: str
    confidence_score: float
    reasons: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    can_auto_merge: bool = False


class JobDeduplicationEngine:
    """Multi-stage matcher classifying job pairs into exact, confident, or reviewable duplicates."""

    def __init__(
        self,
        auto_merge_threshold: float = 0.85,
        review_threshold: float = 0.60,
    ):
        self.auto_merge_threshold = auto_merge_threshold
        self.review_threshold = review_threshold

    def evaluate_pair(self, job1: Any, job2: Any) -> MatchEvaluation:
        """
        Evaluates a pair of job records (either Job models or Dicts) across the 3 matching stages.
        """
        # Helper getters
        def get_val(obj, key, default=None):
            if hasattr(obj, key):
                v = getattr(obj, key)
                return v if v is not None else default
            elif isinstance(obj, dict):
                return obj.get(key, default)
            return default

        id1 = get_val(job1, "id")
        id2 = get_val(job2, "id")

        if id1 and id2 and id1 == id2:
            return MatchEvaluation(
                duplicate_type=DuplicateType.EXACT_DUPLICATE.value,
                confidence_score=1.0,
                reasons=["same_database_record"],
                evidence={"job_id": id1},
                can_auto_merge=True,
            )

        # 0. Company Identity Check
        comp_id1 = get_val(job1, "company_id")
        comp_id2 = get_val(job2, "company_id")
        comp_name1 = (get_val(job1, "company") or get_val(job1, "company_name") or "").strip().lower()
        comp_name2 = (get_val(job2, "company") or get_val(job2, "company_name") or "").strip().lower()

        if comp_id1 and comp_id2 and comp_id1 != comp_id2:
            return MatchEvaluation(
                duplicate_type=DuplicateType.DISTINCT_JOB.value,
                confidence_score=0.0,
                reasons=["different_company_ids"],
                evidence={"company_id1": comp_id1, "company_id2": comp_id2},
                can_auto_merge=False,
            )

        if comp_name1 and comp_name2 and comp_name1 != comp_name2:
            return MatchEvaluation(
                duplicate_type=DuplicateType.DISTINCT_JOB.value,
                confidence_score=0.0,
                reasons=["different_company_names"],
                evidence={"company1": comp_name1, "company2": comp_name2},
                can_auto_merge=False,
            )

        # ====================================================================
        # STAGE 1: EXACT MATCHING
        # ====================================================================
        provider1 = get_val(job1, "provider")
        provider2 = get_val(job2, "provider")
        ext_id1 = get_val(job1, "external_job_id")
        ext_id2 = get_val(job2, "external_job_id")

        # 1.1 Same provider and external_job_id
        if provider1 and provider2 and ext_id1 and ext_id2:
            if provider1.lower().strip() == provider2.lower().strip() and str(ext_id1).strip() == str(ext_id2).strip():
                return MatchEvaluation(
                    duplicate_type=DuplicateType.EXACT_DUPLICATE.value,
                    confidence_score=1.0,
                    reasons=["matching_provider_and_external_job_id"],
                    evidence={"provider": provider1, "external_job_id": ext_id1},
                    can_auto_merge=True,
                )

        # 1.2 Canonical application URL
        app_url1 = get_val(job1, "application_url")
        app_url2 = get_val(job2, "application_url")
        norm_app1 = CanonicalUrlNormalizer.get_canonical_permalink(app_url1) if app_url1 else ""
        norm_app2 = CanonicalUrlNormalizer.get_canonical_permalink(app_url2) if app_url2 else ""

        if norm_app1 and norm_app2 and norm_app1 == norm_app2:
            return MatchEvaluation(
                duplicate_type=DuplicateType.EXACT_DUPLICATE.value,
                confidence_score=1.0,
                reasons=["matching_canonical_application_url"],
                evidence={"canonical_application_url": norm_app1},
                can_auto_merge=True,
            )

        # 1.3 Canonical source URL
        src_url1 = get_val(job1, "source_url")
        src_url2 = get_val(job2, "source_url")
        norm_src1 = CanonicalUrlNormalizer.get_canonical_permalink(src_url1) if src_url1 else ""
        norm_src2 = CanonicalUrlNormalizer.get_canonical_permalink(src_url2) if src_url2 else ""

        if norm_src1 and norm_src2 and norm_src1 == norm_src2:
            return MatchEvaluation(
                duplicate_type=DuplicateType.EXACT_DUPLICATE.value,
                confidence_score=1.0,
                reasons=["matching_canonical_source_url"],
                evidence={"canonical_source_url": norm_src1},
                can_auto_merge=True,
            )

        # 1.4 ATS Permalinks from either URL
        ats1 = CanonicalUrlNormalizer.extract_ats_key(app_url1 or "") or CanonicalUrlNormalizer.extract_ats_key(src_url1 or "")
        ats2 = CanonicalUrlNormalizer.extract_ats_key(app_url2 or "") or CanonicalUrlNormalizer.extract_ats_key(src_url2 or "")
        if ats1 and ats2 and ats1 == ats2:
            return MatchEvaluation(
                duplicate_type=DuplicateType.EXACT_DUPLICATE.value,
                confidence_score=1.0,
                reasons=["matching_ats_unique_identifier"],
                evidence={"ats_key": f"{ats1[0]}:{ats1[1]}:{ats1[2]}"},
                can_auto_merge=True,
            )

        # ====================================================================
        # SAFEGUARD CHECKS (Must pass before any fuzzy merging)
        # ====================================================================
        title1 = get_val(job1, "title") or ""
        title2 = get_val(job2, "title") or ""
        canon_title1 = get_val(job1, "canonical_job_title") or ""
        canon_title2 = get_val(job2, "canonical_job_title") or ""

        # S1. Requisition ID conflict
        req_conflict, req_reason = JobSimilarityCalculator.check_requisition_conflict(
            title1, ext_id1, title2, ext_id2
        )
        if req_conflict:
            return MatchEvaluation(
                duplicate_type=DuplicateType.DISTINCT_JOB.value,
                confidence_score=0.0,
                reasons=["requisition_id_conflict", req_reason],
                evidence={"safeguard_triggered": "requisition_id_conflict"},
                can_auto_merge=False,
            )

        # S2. Location distinction
        loc1 = get_val(job1, "location") or get_val(job1, "location_raw")
        loc2 = get_val(job2, "location") or get_val(job2, "location_raw")
        city1 = get_val(job1, "city")
        city2 = get_val(job2, "city")
        rem1 = bool(get_val(job1, "is_remote", False))
        rem2 = bool(get_val(job2, "is_remote", False))

        loc_compat, loc_reason = JobSimilarityCalculator.check_location_compatibility(
            loc1, city1, rem1, loc2, city2, rem2
        )
        if not loc_compat:
            return MatchEvaluation(
                duplicate_type=DuplicateType.DISTINCT_JOB.value,
                confidence_score=0.0,
                reasons=["location_distinction_conflict", loc_reason],
                evidence={"location1": loc1 or city1, "location2": loc2 or city2},
                can_auto_merge=False,
            )

        # S3. Employment type incompatibility
        emp1 = get_val(job1, "employment_type")
        emp2 = get_val(job2, "employment_type")
        emp_compat, emp_reason = JobSimilarityCalculator.check_employment_type_compatibility(emp1, emp2)
        if not emp_compat:
            return MatchEvaluation(
                duplicate_type=DuplicateType.DISTINCT_JOB.value,
                confidence_score=0.0,
                reasons=["employment_type_conflict", emp_reason],
                evidence={"employment_type1": emp1, "employment_type2": emp2},
                can_auto_merge=False,
            )

        # ====================================================================
        # STAGE 2 & 3: NORMALIZED & FUZZY MATCHING
        # ====================================================================
        desc1 = get_val(job1, "description") or ""
        desc2 = get_val(job2, "description") or ""

        title_sim = JobSimilarityCalculator.calculate_title_similarity(
            title1, title2, canon_title1, canon_title2
        )
        desc_sim = JobSimilarityCalculator.calculate_description_similarity(desc1, desc2)

        # Composite score
        composite_score = round((title_sim * 0.40) + (desc_sim * 0.60), 3)

        evidence = {
            "title_similarity": round(title_sim, 3),
            "description_similarity": round(desc_sim, 3),
            "composite_score": composite_score,
            "location_compatibility": loc_reason,
            "employment_type_compatibility": emp_reason,
        }

        # Rule 1: High title similarity AND high description similarity
        if title_sim >= 0.85 and desc_sim >= 0.75:
            return MatchEvaluation(
                duplicate_type=DuplicateType.HIGH_CONFIDENCE_DUPLICATE.value,
                confidence_score=composite_score,
                reasons=["high_title_and_description_similarity"],
                evidence=evidence,
                can_auto_merge=composite_score >= self.auto_merge_threshold,
            )

        # Rule 2: High title similarity but lower description overlap
        # SAFEGUARD: Never automatically merge jobs based on title similarity alone!
        if title_sim >= 0.80 and desc_sim < 0.40:
            return MatchEvaluation(
                duplicate_type=DuplicateType.NEEDS_MANUAL_REVIEW.value,
                confidence_score=composite_score,
                reasons=["high_title_similarity_but_low_description_overlap", "manual_review_required"],
                evidence=evidence,
                can_auto_merge=False,
            )

        # Rule 3: Moderate similarity
        if composite_score >= self.review_threshold:
            return MatchEvaluation(
                duplicate_type=DuplicateType.POSSIBLE_DUPLICATE.value,
                confidence_score=composite_score,
                reasons=["moderate_content_similarity"],
                evidence=evidence,
                can_auto_merge=False,
            )

        # Rule 4: Distinct jobs
        return MatchEvaluation(
            duplicate_type=DuplicateType.DISTINCT_JOB.value,
            confidence_score=composite_score,
            reasons=["low_similarity_below_threshold"],
            evidence=evidence,
            can_auto_merge=False,
        )

