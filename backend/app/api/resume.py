import hashlib
import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from models.candidate import Candidate
from resume.parser import (
    parse_resume_bytes,
    UnsupportedFormatError,
    CorruptedFileError,
    EmptyFileError,
    ScannedPdfError,
    FileSizeExceededError,
)
from resume.profile_builder import build_candidate_profile
from resume.validator import validate_resume
from schemas.candidate import (
    ResumeUploadResponse,
    CandidateProfile,
    ValidationResult,
    ValidationStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["Resume"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """Upload, parse, validate, and extract candidate profile from a PDF or DOCX resume."""
    filename = file.filename or "unknown_resume"
    content_type = file.content_type or ""

    # ── Edge-case 1: missing or no extension ──────────────────────────────────
    dot_idx = filename.rfind(".")
    if dot_idx == -1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File has no extension. Only PDF (.pdf) and DOCX (.docx) resumes are accepted.",
        )

    # ── Edge-case 2: unsupported extension ───────────────────────────────────
    ext = filename[dot_idx:].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Only PDF (.pdf) and DOCX (.docx) resumes are accepted.",
        )

    # ── Edge-case: filename signals it's not a resume ─────────────────────────
    name_lower = filename.lower()
    REJECTED_FILENAME_PATTERNS = [
        "report", "project_report", "assignment", "thesis", "dissertation",
        "manual", "guide", "handbook", "syllabus", "brochure", "prospectus",
        "invoice", "receipt", "college_list", "institution", "installation",
        "notes", "lecture", "presentation", "proposal",
    ]
    if any(pat in name_lower for pat in REJECTED_FILENAME_PATTERNS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"The filename '{filename}' suggests this is not a resume. "
                "Please upload your personal CV or resume (PDF or DOCX)."
            ),
        )

    # ── Read file bytes ───────────────────────────────────────────────────────
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read uploaded file stream: {str(e)}",
        )

    # ── Edge-case 3: empty file ───────────────────────────────────────────────
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes). Please upload a valid resume.",
        )

    # ── Edge-case 4: file too large (> 5 MB) ─────────────────────────────────
    MAX_SIZE = 5 * 1024 * 1024
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the 5 MB limit ({len(file_bytes) / (1024*1024):.1f} MB uploaded).",
        )

    # ── Parse resume text ─────────────────────────────────────────────────────
    try:
        extracted_text = parse_resume_bytes(file_bytes, filename, content_type)
    except FileSizeExceededError as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e))
    except ScannedPdfError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Scanned/image-only PDF detected. Please upload a text-based resume. ({e})",
        )
    except (UnsupportedFormatError, CorruptedFileError, EmptyFileError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected parsing error for file {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the resume file.",
        )

    # ── Build structured profile ───────────────────────────────────────────────
    profile: CandidateProfile = build_candidate_profile(extracted_text)
    validation: ValidationResult = validate_resume(extracted_text, profile, filename=filename)

    # ── Reject non-resume documents early ─────────────────────────────────────
    if validation.status == ValidationStatus.INVALID:
        reason = validation.reasons[0] if validation.reasons else "Document does not appear to be a valid resume."
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Please upload a valid resume. {reason}",
        )

    # ── Deduplication via SHA-256 ──────────────────────────────────────────────
    resume_hash = hashlib.sha256(file_bytes).hexdigest()

    stmt = select(Candidate).where(Candidate.resume_hash == resume_hash)
    candidate_record = (await db.execute(stmt)).scalars().first()

    profile_payload = {
        "profile": profile.model_dump(),
        "validation": validation.model_dump(),
    }

    if candidate_record:
        candidate_record.profile_json = json.dumps(profile_payload)
        candidate_record.filename = filename
        await db.commit()
        await db.refresh(candidate_record)
        active_cand = candidate_record
    else:
        new_candidate = Candidate(
            resume_hash=resume_hash,
            filename=filename,
            profile_json=json.dumps(profile_payload),
        )
        db.add(new_candidate)
        await db.commit()
        await db.refresh(new_candidate)
        active_cand = new_candidate

    candidate_id = active_cand.id

    # ── SBERT role recommendations ────────────────────────────────────────────
    try:
        from intelligence.role_recommender import recommend_career_roles
        rec_res = recommend_career_roles(candidate_id=candidate_id, profile=profile)
        if rec_res and getattr(rec_res, "recommendations", None):
            active_cand.recommendations_json = json.dumps(rec_res.model_dump())
            await db.commit()
            await db.refresh(active_cand)
        else:
            logger.warning(f"No role recommendations generated for candidate {candidate_id}")
    except Exception as e:
        logger.warning(f"Could not generate career recommendations for candidate {candidate_id}: {e}")

    # ── Candidate embedding ───────────────────────────────────────────────────
    try:
        from matching.candidate_embedder import candidate_embedding_service
        await candidate_embedding_service.get_or_generate_embedding(db, active_cand, force=True)
    except Exception as e:
        logger.warning(f"Could not generate candidate embedding for candidate {candidate_id}: {e}")

    # ── Initial matching ──────────────────────────────────────────────────────
    try:
        from matching.matching_service import matching_service
        await matching_service.run_matching_for_candidate(db, candidate_id=candidate_id, force=True)
    except Exception as e:
        logger.warning(f"Could not run initial matching for candidate {candidate_id}: {e}")

    # ── Background discovery + full pipeline ─────────────────────────────────
    if background_tasks:
        async def run_discovery_pipeline(cid: int):
            try:
                from pipeline.orchestrator import pipeline_orchestrator
                await pipeline_orchestrator.execute_pipeline(
                    trigger_type="AUTO_RESUME_UPLOAD",
                    stages=["discovery", "extraction", "deduplication",
                            "verification", "embeddings", "matching"],
                    candidate_id=cid,
                    force_matching=True,
                    filter_targeting=True,
                )
            except Exception as ex:
                logger.error(f"Background discovery pipeline failed for candidate {cid}: {ex}")

        background_tasks.add_task(run_discovery_pipeline, candidate_id)

    logger.info(f"Processed resume: candidate_id={candidate_id}, status={validation.status}")

    return ResumeUploadResponse(
        candidate_id=candidate_id,
        resume_hash=resume_hash,
        filename=filename,
        validation=validation,
        profile=profile,
    )


@router.get("/{candidate_id}", response_model=ResumeUploadResponse)
async def get_candidate_profile(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve an extracted candidate profile and validation status by candidate ID."""
    stmt = select(Candidate).where(Candidate.id == candidate_id)
    candidate_record = (await db.execute(stmt)).scalars().first()

    if not candidate_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID {candidate_id} not found.",
        )

    data = json.loads(candidate_record.profile_json)
    profile = CandidateProfile(**data["profile"])
    validation = ValidationResult(**data["validation"])

    return ResumeUploadResponse(
        candidate_id=candidate_record.id,
        resume_hash=candidate_record.resume_hash,
        filename=candidate_record.filename,
        validation=validation,
        profile=profile,
    )
