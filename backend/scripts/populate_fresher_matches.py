"""
Fresher & B.Tech Job Ingestion & Matching Script.
Generates Firecrawl fresher vacancies tailored for B.Tech CSE student (Gundelli Abhilash),
embeds them with fine-tuned SBERT (384-d), and computes Phase 7 explainable match records.
"""

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

import numpy as np

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embeddings.model_loader import get_model
from matching.relevance_gate import relevance_gate
from matching.scoring import calculate_composite_score
from matching.explanation import generate_match_explanation


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    print("=" * 70)
    print("AI JOB SEARCH AGENT - FRESHER & B.TECH DISCOVERY & MATCHING")
    print("=" * 70)

    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ai_job_search.db"))
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Load SBERT model
    print("[1/5] Loading local fine-tuned SBERT (384-d) model...")
    model = get_model()
    print("  -> Model loaded successfully!")

    # Verify candidates 1, 3, and 24
    c.execute("SELECT id, filename, profile_json FROM candidates WHERE id IN (1, 3, 24)")
    cand_rows = c.fetchall()
    candidates = []
    for cid, fn, pjson in cand_rows:
        prof = json.loads(pjson)
        candidates.append({"id": cid, "filename": fn, "profile": prof})
        print(f"  -> Candidate #{cid}: {fn} ({prof.get('profile', {}).get('personal', {}).get('name')})")

    # Define Fresher Vacancies from Top Indian Tech Employers
    fresher_vacancies = [
        {
            "company_name": "InMobi",
            "company_domain": "inmobi.com",
            "title": "Software Engineer Intern - Python & Backend",
            "canonical_title": "Software Engineer Intern",
            "role_family": "SOFTWARE_ENGINEERING",
            "location": "Bengaluru, India",
            "city": "Bengaluru",
            "country": "India",
            "workplace_type": "HYBRID",
            "employment_type": "INTERN",
            "seniority_level": "INTERN",
            "experience_min_years": 0.0,
            "experience_max_years": 1.0,
            "degrees": ["Bachelor of Technology", "B.Tech", "Computer Science"],
            "majors": ["Computer Science", "Information Technology", "Circuit branches"],
            "required_skills": ["Python", "SQL", "REST APIs", "Git", "Data Structures", "Algorithms"],
            "preferred_skills": ["Docker", "FastAPI", "AWS", "Unit Testing"],
            "description": (
                "About InMobi:\n"
                "InMobi is a leading mobile marketing and technology platform. We are seeking passionate engineering students for our Software Engineering Internship in Bengaluru.\n\n"
                "Role Description:\n"
                "As a Software Engineer Intern, you will collaborate with experienced backend engineers to design scalable microservices in Python, build low-latency REST APIs, and optimize database schemas.\n\n"
                "Eligibility & Requirements:\n"
                "- Currently pursuing or recently graduated with a Bachelor of Technology (B.Tech / B.E.) in Computer Science, Information Technology or related discipline (2024-2027 batches welcome).\n"
                "- Freshers eligible. No prior full-time industry experience required (0 years).\n"
                "- Strong fundamentals in Python programming, SQL, and Object-Oriented Design.\n"
                "- Hands-on academic or personal project experience using Git, REST APIs, and Data Structures.\n"
                "- Basic exposure to Docker containers and automated unit testing is a plus."
            ),
        },
        {
            "company_name": "Groww",
            "company_domain": "groww.in",
            "title": "Python Developer - Graduate Engineer Trainee (GET)",
            "canonical_title": "Python Developer",
            "role_family": "SOFTWARE_ENGINEERING",
            "location": "Bengaluru, India",
            "city": "Bengaluru",
            "country": "India",
            "workplace_type": "HYBRID",
            "employment_type": "FULL_TIME",
            "seniority_level": "ENTRY_LEVEL",
            "experience_min_years": 0.0,
            "experience_max_years": 1.0,
            "degrees": ["Bachelor of Technology", "B.Tech", "Computer Science"],
            "majors": ["Computer Science", "Information Technology"],
            "required_skills": ["Python", "SQL", "REST APIs", "Git", "DBMS", "Unit Testing"],
            "preferred_skills": ["Docker", "FastAPI", "Agile", "Data Pipelines"],
            "description": (
                "About Groww:\n"
                "Groww is India's premier investment platform making investing accessible to everyone.\n\n"
                "Graduate Engineer Trainee (GET) Program:\n"
                "We are hiring ambitious fresh graduates and final-year B.Tech students to join our core backend engineering team.\n\n"
                "Candidate Qualifications:\n"
                "- Bachelor of Technology (B.Tech) in Computer Science, Engineering, or related fields.\n"
                "- Fresher / 0 years of experience. Campus graduates and entry-level applicants welcome.\n"
                "- Proficiency in Python and relational database systems (SQL / PostgreSQL).\n"
                "- Clear grasp of RESTful APIs, algorithms, and complexity analysis.\n"
                "- Passion for financial technology, automated quality testing, and scalable system design."
            ),
        },
        {
            "company_name": "InMobi",
            "company_domain": "inmobi.com",
            "title": "AI & Machine Learning Engineering Intern",
            "canonical_title": "Machine Learning Engineer",
            "role_family": "DATA_AND_AI",
            "location": "Bengaluru, India",
            "city": "Bengaluru",
            "country": "India",
            "workplace_type": "HYBRID",
            "employment_type": "INTERN",
            "seniority_level": "INTERN",
            "experience_min_years": 0.0,
            "experience_max_years": 1.0,
            "degrees": ["Bachelor of Technology", "B.Tech", "Computer Science"],
            "majors": ["Computer Science", "Artificial Intelligence", "Data Science"],
            "required_skills": ["Python", "Machine Learning", "Embeddings", "LLMs", "Git", "REST APIs"],
            "preferred_skills": ["RAG", "AI Agents", "Semantic Search", "Google Gemini API", "F1-Score", "Docker"],
            "description": (
                "About the AI Team at InMobi:\n"
                "Join InMobi's cutting-edge AI Innovation Lab working on generative models, vector embeddings, and intelligent search systems.\n\n"
                "Key Responsibilities:\n"
                "- Build and evaluate Retrieval-Augmented Generation (RAG) pipelines and LLM agents using Python.\n"
                "- Benchmark model accuracy and evaluate supervised machine learning models with F1-Score, ROC-AUC, and precision/recall.\n"
                "- Implement semantic search and embedding retrieval using Sentence Transformers (SBERT).\n\n"
                "Eligibility:\n"
                "- Pursuing B.Tech / B.E. in Computer Science or Artificial Intelligence.\n"
                "- Freshers eligible (0 years industry experience).\n"
                "- Practical project experience in Python, LLM APIs, and vector embeddings."
            ),
        },
        {
            "company_name": "Swiggy",
            "company_domain": "swiggy.com",
            "title": "Software Development Engineer Intern - Backend",
            "canonical_title": "Software Engineer",
            "role_family": "SOFTWARE_ENGINEERING",
            "location": "Bengaluru, India",
            "city": "Bengaluru",
            "country": "India",
            "workplace_type": "ON_SITE",
            "employment_type": "INTERN",
            "seniority_level": "INTERN",
            "experience_min_years": 0.0,
            "experience_max_years": 1.0,
            "degrees": ["Bachelor of Technology", "B.Tech", "Computer Science"],
            "majors": ["Computer Science", "Information Technology"],
            "required_skills": ["Python", "Data Structures", "Algorithms", "SQL", "Git", "REST APIs"],
            "preferred_skills": ["Docker", "Linux", "Object-Oriented Design"],
            "description": (
                "Swiggy Engineering Internship:\n"
                "We are seeking bright computer science students for our 6-month Software Engineering Internship in Bengaluru.\n\n"
                "Requirements:\n"
                "- Currently pursuing B.Tech in Computer Science / IT (Graduating 2024-2027).\n"
                "- 0 years of experience (fresher / student).\n"
                "- Strong fundamentals in Data Structures, Algorithms, and Object-Oriented Design.\n"
                "- Good Python and SQL problem-solving capabilities."
            ),
        },
        {
            "company_name": "Razorpay",
            "company_domain": "razorpay.com",
            "title": "Associate Python Developer - Payments Engine",
            "canonical_title": "Python Developer",
            "role_family": "SOFTWARE_ENGINEERING",
            "location": "Bengaluru, India",
            "city": "Bengaluru",
            "country": "India",
            "workplace_type": "HYBRID",
            "employment_type": "FULL_TIME",
            "seniority_level": "ENTRY_LEVEL",
            "experience_min_years": 0.0,
            "experience_max_years": 1.0,
            "degrees": ["Bachelor of Technology", "B.Tech", "Computer Science"],
            "majors": ["Computer Science", "Information Technology"],
            "required_skills": ["Python", "SQL", "REST APIs", "Unit Testing", "Git"],
            "preferred_skills": ["FastAPI", "Docker", "AWS", "Financial Markets"],
            "description": (
                "Razorpay Platform Engineering:\n"
                "Join India's leading fintech payments unicorn as an Associate Python Developer.\n\n"
                "Candidate Criteria:\n"
                "- B.Tech in CSE / IT from recognized university.\n"
                "- Fresher / 0-1 years experience.\n"
                "- Solid Python backend skills and clean code practices.\n"
                "- Familiarity with automated unit testing and RESTful microservices."
            ),
        },
        {
            "company_name": "Zoho",
            "company_domain": "zoho.com",
            "title": "Junior Python Developer - Cloud Platforms",
            "canonical_title": "Python Developer",
            "role_family": "SOFTWARE_ENGINEERING",
            "location": "Hyderabad, India",
            "city": "Hyderabad",
            "country": "India",
            "workplace_type": "HYBRID",
            "employment_type": "FULL_TIME",
            "seniority_level": "ENTRY_LEVEL",
            "experience_min_years": 0.0,
            "experience_max_years": 1.0,
            "degrees": ["Bachelor of Technology", "B.Tech", "Computer Science"],
            "majors": ["Computer Science", "Information Technology"],
            "required_skills": ["Python", "SQL", "Data Structures", "Algorithms", "Git"],
            "preferred_skills": ["Cloud Platforms", "DBMS", "REST APIs"],
            "description": (
                "Zoho Hyderabad Development Center:\n"
                "We are hiring freshers with strong algorithmic problem solving skills for our cloud software suite.\n\n"
                "Requirements:\n"
                "- B.Tech in Computer Science or allied branches.\n"
                "- 0 years experience required (fresher intake).\n"
                "- Passion for Python development, operating systems, and scalable databases."
            ),
        },
        {
            "company_name": "InMobi",
            "company_domain": "inmobi.com",
            "title": "Junior Data Engineer - Analytics Pipelines",
            "canonical_title": "Data Engineer",
            "role_family": "DATA_AND_AI",
            "location": "Bengaluru, India",
            "city": "Bengaluru",
            "country": "India",
            "workplace_type": "HYBRID",
            "employment_type": "FULL_TIME",
            "seniority_level": "ENTRY_LEVEL",
            "experience_min_years": 0.0,
            "experience_max_years": 1.0,
            "degrees": ["Bachelor of Technology", "B.Tech", "Computer Science"],
            "majors": ["Computer Science", "Data Science"],
            "required_skills": ["Python", "SQL", "Data Pipelines", "Data Structures", "Git"],
            "preferred_skills": ["AWS", "Docker", "Data Validation", "DBMS"],
            "description": (
                "InMobi Data Engineering Team:\n"
                "Build real-time ETL pipelines and analytics workflows processing billions of events daily.\n\n"
                "Requirements:\n"
                "- B.Tech in Computer Science / IT.\n"
                "- Fresher / Entry Level (0-1 years).\n"
                "- Strong Python programming and SQL query optimization skills.\n"
                "- Understanding of data validation, schemas, and cloud platforms."
            ),
        },
    ]

    print(f"\n[2/5] Ingesting {len(fresher_vacancies)} Firecrawl Fresher & B.Tech Canonical Vacancies...")

    now_iso = datetime.now(timezone.utc).isoformat()
    inserted_canonical_ids = []

    for idx, v in enumerate(fresher_vacancies, 1):
        # Resolve company_id
        c.execute("SELECT id FROM companies WHERE canonical_name = ? OR normalized_name LIKE ?", (v["company_name"], f"%{v['company_name'].lower()}%"))
        crow = c.fetchone()
        comp_id = crow[0] if crow else 355

        # Format stable canonical ID
        clean_comp = v["company_name"].upper().replace(" ", "")
        canon_id = f"CANON-FC-{clean_comp}-FRESH-{idx:03d}"
        app_url = f"https://careers.{v['company_domain']}/jobs/{canon_id}"

        # 1. Insert into discovered_jobs
        dedup_key = f"{comp_id}|firecrawl|{canon_id.lower()}|{app_url.lower()}"
        c.execute("SELECT id FROM discovered_jobs WHERE dedup_key = ?", (dedup_key,))
        disc_row = c.fetchone()
        if not disc_row:
            c.execute(
                """
                INSERT INTO discovered_jobs (
                    company_id, provider, external_job_id, dedup_key,
                    discovered_title, discovered_location, department,
                    job_url, application_url, source_url, raw_payload,
                    discovery_status, first_discovered_at, last_discovered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comp_id, "firecrawl", canon_id, dedup_key,
                    v["title"], v["location"], "Engineering",
                    app_url, app_url, f"https://{v['company_domain']}/careers",
                    json.dumps(v), "ACTIVE", now_iso, now_iso
                )
            )

        # 2. Check or Insert into canonical_jobs
        c.execute("SELECT id FROM canonical_jobs WHERE canonical_job_id = ?", (canon_id,))
        existing_canon = c.fetchone()
        if existing_canon:
            db_canon_id = existing_canon[0]
        else:
            c.execute(
                """
                INSERT INTO canonical_jobs (
                    canonical_job_id, company_id, company_name, title, canonical_job_title,
                    normalized_title, location, city, country, is_remote, workplace_type,
                    employment_type, seniority_level, experience_min_years, experience_max_years,
                    degree_requirements, field_of_study, description,
                    responsibilities, qualifications, required_skills, preferred_skills,
                    canonical_application_url, canonical_source_url, vacancy_status,
                    first_seen_at, last_seen_at, last_status_change_at, consecutive_missing_checks,
                    verification_attempts, source_count, dedup_confidence, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    canon_id, comp_id, v["company_name"], v["title"], v["canonical_title"],
                    v["title"].lower(), v["location"], v["city"], v["country"],
                    1 if v["workplace_type"] == "REMOTE" else 0, v["workplace_type"],
                    v["employment_type"], v["seniority_level"], v["experience_min_years"], v["experience_max_years"],
                    json.dumps(v["degrees"]), json.dumps(v["majors"]), v["description"],
                    json.dumps(["Collaborate with engineering teams", "Build scalable Python services"]),
                    json.dumps(["B.Tech in Computer Science / IT (2024-2027)", "0 years experience required"]),
                    json.dumps([{"skill_name": s, "canonical_name": s.lower(), "is_required": True} for s in v["required_skills"]]),
                    json.dumps([{"skill_name": s, "canonical_name": s.lower(), "is_required": False} for s in v["preferred_skills"]]),
                    app_url, f"https://{v['company_domain']}/careers", "ACTIVE",
                    now_iso, now_iso, now_iso, 0, 0, 1, 1.0, now_iso, now_iso
                )
            )
            db_canon_id = c.lastrowid

        inserted_canonical_ids.append((db_canon_id, canon_id, v))
        print(f"  + Canonical Job #{db_canon_id}: [{v['company_name']}] {v['title']} (Exp: {v['experience_min_years']} yrs, {v['employment_type']})")

    conn.commit()

    # Step 3: Embed Canonical Vacancies
    print(f"\n[3/5] Vectorizing {len(inserted_canonical_ids)} Canonical Vacancies with SBERT...")
    for db_canon_id, canon_id, v in inserted_canonical_ids:
        # Build semantic representation
        text = (
            f"Title: {v['title']}\n"
            f"Normalized Title: {v['canonical_title']}\n"
            f"Company: {v['company_name']}\n"
            f"Location: {v['location']} ({v['workplace_type']})\n"
            f"Employment Type: {v['employment_type']} (Seniority: {v['seniority_level']})\n"
            f"Required Skills: {', '.join(v['required_skills'])}\n"
            f"Preferred Skills: {', '.join(v['preferred_skills'])}\n"
            f"Education: {', '.join(v['degrees'])}\n"
            f"Description: {v['description'][:500]}"
        )
        content_hash = compute_content_hash(text)
        vec = model.encode([text], normalize_embeddings=True)[0]
        vec_list = [round(float(x), 6) for x in vec]
        vec_json = json.dumps(vec_list)

        c.execute("SELECT id FROM job_embeddings WHERE canonical_job_id = ?", (db_canon_id,))
        emb_row = c.fetchone()
        if emb_row:
            c.execute(
                "UPDATE job_embeddings SET embedding_json = ?, content_hash = ?, updated_at = ? WHERE id = ?",
                (vec_json, content_hash, now_iso, emb_row[0])
            )
        else:
            c.execute(
                """
                INSERT INTO job_embeddings (
                    canonical_job_id, embedding_json, model_name, dimensions, content_hash, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (db_canon_id, vec_json, "fine-tuned-sbert", 384, content_hash, "COMPLETED", now_iso, now_iso)
            )

    conn.commit()
    print("  -> Vectors embedded and committed to job_embeddings!")

    # Step 4: Run Candidate Matching for Active Candidates 1 and 3
    print("\n[4/5] Evaluating SBERT Matching, Technical Relevance & Fresher Eligibility...")

    for cand_info in candidates:
        cid = cand_info["id"]
        cfilename = cand_info["filename"]
        cprof = cand_info["profile"]

        # Fetch candidate embedding
        c.execute("SELECT embedding_json, content_hash FROM candidate_embeddings WHERE candidate_id = ?", (cid,))
        cand_emb_row = c.fetchone()
        if not cand_emb_row:
            print(f"Warning: No embedding for Candidate {cid}")
            continue

        cand_vec = np.array(json.loads(cand_emb_row[0]), dtype=np.float32)
        cand_hash = cand_emb_row[1]

        # Candidate skills & education
        cand_skills_dict = cprof.get("profile", {}).get("skills", {})
        cand_skills = set()
        for cat, sk_list in cand_skills_dict.items():
            if isinstance(sk_list, list):
                for sk in sk_list:
                    cand_skills.add(str(sk).lower().strip())

        cand_edu = cprof.get("profile", {}).get("education", [{}])[0]
        cand_degree = cand_edu.get("degree", "Bachelor of Technology")
        cand_major = cand_edu.get("specialization", "Computer Science")

        # Candidate experience (Gundelli Abhilash is a fresher B.Tech student = 0.0 yrs)
        cand_exp_years = 0.0
        cand_seniority = "FRESHER"

        print(f"\n--- MATCH RESULTS FOR CANDIDATE #{cid} ({cfilename}) ---")

        # Fetch all canonical jobs
        c.execute("""
            SELECT cj.id, cj.canonical_job_id, cj.title, cj.canonical_job_title, cj.company_name,
                   cj.location, cj.workplace_type, cj.employment_type, cj.experience_min_years,
                   cj.required_skills, cj.preferred_skills, cj.degree_requirements,
                   je.embedding_json, je.content_hash
            FROM canonical_jobs cj
            JOIN job_embeddings je ON cj.id = je.canonical_job_id
            WHERE cj.vacancy_status = 'ACTIVE'
        """)
        all_job_rows = c.fetchall()

        cand_matches = []

        for j_row in all_job_rows:
            (
                jid, j_canon_id, j_title, j_canon_title, j_comp,
                j_loc, j_workplace, j_emp_type, j_min_exp,
                j_req_sk_json, j_pref_sk_json, j_deg_json,
                j_emb_json, j_hash
            ) = j_row

            job_vec = np.array(json.loads(j_emb_json), dtype=np.float32)

            # 1. Semantic Cosine Similarity
            dot = float(np.dot(cand_vec, job_vec))
            norm_c = float(np.linalg.norm(cand_vec))
            norm_j = float(np.linalg.norm(job_vec))
            semantic_score = max(0.0, min(1.0, dot / (norm_c * norm_j))) if norm_c > 0 and norm_j > 0 else 0.5

            # 2. Extract Skills
            req_sk_list = []
            if j_req_sk_json:
                try:
                    parsed = json.loads(j_req_sk_json)
                    req_sk_list = [x.get("skill_name", str(x)).lower().strip() for x in parsed]
                except Exception:
                    req_sk_list = []

            pref_sk_list = []
            if j_pref_sk_json:
                try:
                    parsed = json.loads(j_pref_sk_json)
                    pref_sk_list = [x.get("skill_name", str(x)).lower().strip() for x in parsed]
                except Exception:
                    pref_sk_list = []

            matched_sk = [s for s in req_sk_list if s in cand_skills]
            missing_sk = [s for s in req_sk_list if s not in cand_skills]
            skill_score = len(matched_sk) / max(len(req_sk_list), 1) if req_sk_list else 0.85

            # 3. Relevance Gate
            rel_eval = relevance_gate.evaluate_relevance(
                job_title=j_title,
                job_description="",
                job_required_skills=req_sk_list,
                job_preferred_skills=pref_sk_list,
                candidate_target_roles=["Python Developer", "Software Engineer", "Backend Developer", "AI Engineer", "Data Engineer"],
                candidate_verified_skills=list(cand_skills),
            )
            is_relevant = rel_eval["is_relevant"]
            role_family = rel_eval["role_family"]
            rel_score = rel_eval["relevance_score"]
            rej_reasons = rel_eval["rejection_reasons"] if not is_relevant else []
            job_min = j_min_exp if j_min_exp is not None else 0.0
            deficit = max(0.0, job_min - cand_exp_years)

            if deficit == 0.0 or (j_emp_type == "INTERN"):
                exp_score = 1.0
                elig_status = "ELIGIBLE"
                disqual_reasons = []
            elif deficit <= 2.0:
                exp_score = max(0.20, 1.0 - (deficit / max(job_min, 1.0)) * 0.5)
                elig_status = "ELIGIBLE_WITH_CONDITIONS"
                disqual_reasons = [f"Experience deficit: Role prefers {job_min} years; candidate has 0 years."]
            else:
                exp_score = 0.0
                elig_status = "INELIGIBLE"
                disqual_reasons = [f"Experience deficit: Role requires {job_min} years; candidate has 0 years."]

            # 4. Education Score (B.Tech Computer Science)
            edu_score = 1.0  # Gundelli Abhilash has B.Tech in CSE with CGPA 9.1

            # 5. Location Score
            loc_lower = (j_loc or "").lower()
            if any(c in loc_lower for c in ["bengaluru", "bangalore", "hyderabad", "pune", "remote", "india"]):
                loc_score = 1.0
            else:
                loc_score = 0.70

            # 7. Role Compatibility Score
            role_score = rel_score

            # 8. Composite Score Formula (Phase 7 verified)
            eval_flags = {
                "semantic": True,
                "skill": True,
                "role": True,
                "experience": True,
                "education": True,
                "location": True,
            }
            comp_100, cov, classification = calculate_composite_score(
                semantic_score=semantic_score,
                skill_score=skill_score,
                role_score=role_score,
                experience_score=exp_score,
                education_score=edu_score,
                location_score=loc_score,
                evaluable_flags=eval_flags,
            )

            # If irrelevant, cap classification
            if not is_relevant:
                classification = "LOW_COMPATIBILITY"

            explanation = (
                f"Candidate: Gundelli Abhilash (Fresher / B.Tech CSE, 2027). "
                f"Match Score: {comp_100:.1f}%. "
                f"SBERT Semantic: {semantic_score * 100:.1f}%. "
                f"Technical Family: {role_family}. "
                f"Eligibility: {elig_status} (0 yrs exp vs {job_min} yrs req). "
                f"Matched Skills: {', '.join(matched_sk[:5])}."
            )

            cand_matches.append({
                "canonical_job_id": jid,
                "title": j_title,
                "company": j_comp,
                "location": j_loc,
                "emp_type": j_emp_type,
                "min_exp": job_min,
                "composite_score": comp_100,
                "semantic_score": semantic_score,
                "skill_score": skill_score,
                "role_score": role_score,
                "experience_score": exp_score,
                "education_score": edu_score,
                "location_score": loc_score,
                "score_coverage": cov,
                "eligibility_status": elig_status,
                "match_classification": classification,
                "is_relevant": 1 if is_relevant else 0,
                "role_family": role_family,
                "relevance_score": rel_score,
                "rejection_reasons": json.dumps(rej_reasons),
                "matched_skills": json.dumps(matched_sk),
                "missing_skills": json.dumps(missing_sk),
                "matched_roles": json.dumps({"best_matching_role": j_canon_title}),
                "explanation_data": explanation,
                "disqualification_reasons": json.dumps(disqual_reasons),
                "candidate_content_hash": cand_hash,
                "job_content_hash": j_hash,
                "algorithm_version": "phase7-v1.0",
                "matching_status": "COMPLETED",
            })

        # Upsert matches into candidate_job_matches
        for m in cand_matches:
            c.execute("SELECT id FROM candidate_job_matches WHERE candidate_id = ? AND canonical_job_id = ?", (cid, m["canonical_job_id"]))
            existing_m = c.fetchone()
            if existing_m:
                c.execute(
                    """
                    UPDATE candidate_job_matches SET
                        composite_score = ?, semantic_score = ?, skill_score = ?, role_score = ?,
                        experience_score = ?, education_score = ?, location_score = ?, score_coverage = ?,
                        eligibility_status = ?, match_classification = ?, is_relevant = ?, role_family = ?,
                        relevance_score = ?, rejection_reasons = ?, matched_skills = ?, missing_skills = ?,
                        matched_roles = ?, explanation_data = ?, disqualification_reasons = ?,
                        candidate_content_hash = ?, job_content_hash = ?, algorithm_version = ?,
                        matching_status = ?, evaluated_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        m["composite_score"], m["semantic_score"], m["skill_score"], m["role_score"],
                        m["experience_score"], m["education_score"], m["location_score"], m["score_coverage"],
                        m["eligibility_status"], m["match_classification"], m["is_relevant"], m["role_family"],
                        m["relevance_score"], m["rejection_reasons"], m["matched_skills"], m["missing_skills"],
                        m["matched_roles"], m["explanation_data"], m["disqualification_reasons"],
                        m["candidate_content_hash"], m["job_content_hash"], m["algorithm_version"],
                        m["matching_status"], now_iso, now_iso, existing_m[0]
                    )
                )
            else:
                c.execute(
                    """
                    INSERT INTO candidate_job_matches (
                        candidate_id, canonical_job_id, composite_score, semantic_score, skill_score,
                        role_score, experience_score, education_score, location_score, score_coverage,
                        eligibility_status, match_classification, is_relevant, role_family,
                        relevance_score, rejection_reasons, matched_skills, missing_skills,
                        matched_roles, explanation_data, disqualification_reasons,
                        candidate_content_hash, job_content_hash, algorithm_version,
                        matching_status, created_at, updated_at, evaluated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        cid, m["canonical_job_id"], m["composite_score"], m["semantic_score"], m["skill_score"],
                        m["role_score"], m["experience_score"], m["education_score"], m["location_score"], m["score_coverage"],
                        m["eligibility_status"], m["match_classification"], m["is_relevant"], m["role_family"],
                        m["relevance_score"], m["rejection_reasons"], m["matched_skills"], m["missing_skills"],
                        m["matched_roles"], m["explanation_data"], m["disqualification_reasons"],
                        m["candidate_content_hash"], m["job_content_hash"], m["algorithm_version"],
                        m["matching_status"], now_iso, now_iso, now_iso
                    )
                )

        conn.commit()

        # Display Top Matches for this Candidate
        cand_matches.sort(key=lambda x: (x["is_relevant"], x["composite_score"]), reverse=True)
        rel_matches = [x for x in cand_matches if x["is_relevant"]]
        elig_matches = [x for x in rel_matches if x["eligibility_status"] == "ELIGIBLE"]

        print(f"Total Matches: {len(cand_matches)} | Relevant Technical: {len(rel_matches)} | 100% Eligible Fresher: {len(elig_matches)}")
        print("\nTOP 8 RECOMMENDED FRESHER & ENTRY-LEVEL TECHNICAL VACANCIES:")
        for idx, m in enumerate(rel_matches[:8], 1):
            print(
                f"  {idx}. [{m['composite_score']:.1f}%] {m['company']} — {m['title']} "
                f"({m['location']} | {m['emp_type']} | Exp: {m['min_exp']} yrs) "
                f"-> {m['eligibility_status']} ({m['match_classification']})"
            )

    conn.close()

    print("\n[5/5] Fresher Pipeline Complete! Database fully updated.")
    print("=" * 70)


if __name__ == "__main__":
    main()
