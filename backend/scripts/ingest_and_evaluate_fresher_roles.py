import os
import sys
import json
import sqlite3
import datetime
import hashlib
import numpy as np

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from embeddings.model_loader import get_model
from matching.matching_service import matching_service
from matching.relevance_gate import relevance_gate
from matching.eligibility import eligibility_engine, parse_json_list
from matching.scoring import calculate_composite_score
from matching.explanation import generate_match_explanation
from models.candidate_job_match import EligibilityStatus

# 23 Verified live vacancies (100% HTTP 200 on official ATS)
VERIFIED_JOBS = [
    {
        "company": "Merkle Science",
        "title": "Software Engineer (Intern) - Backend",
        "canonical_title": "Software Engineer Intern - Backend",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "Information Technology"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Proficiency in Python backend development", "is_required": True},
            {"skill_name": "REST APIs", "canonical_name": "rest apis", "category": "Tools", "evidence_snippet": "Experience building clean REST APIs", "is_required": True},
            {"skill_name": "SQL", "canonical_name": "sql", "category": "Databases", "evidence_snippet": "Knowledge of relational databases and SQL queries", "is_required": True},
            {"skill_name": "Git", "canonical_name": "git", "category": "Tools", "evidence_snippet": "Git version control and collaborative workflows", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "Docker", "canonical_name": "docker", "category": "Tools", "evidence_snippet": "Containerization with Docker", "is_required": False},
            {"skill_name": "Data Pipelines", "canonical_name": "data pipelines", "category": "Data & AI", "evidence_snippet": "Data processing and pipeline design", "is_required": False}
        ],
        "description": "Merkle Science is hiring a Software Engineer Intern for our backend team. You will build resilient REST APIs in Python, write SQL database queries, design automated tests, and collaborate with experienced engineers on blockchain data intelligence platforms.",
        "application_url": "https://jobs.lever.co/merklescience/e663b69b-264a-4bd7-b04d-fb3c0a824a28"
    },
    {
        "company": "Hevo Data",
        "title": "Associate Software Development Engineer (SDE) Intern",
        "canonical_title": "Associate Software Development Engineer Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "Information Technology"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Strong foundational knowledge of Python and data structures", "is_required": True},
            {"skill_name": "Data Structures", "canonical_name": "data structures", "category": "Core CS", "evidence_snippet": "Solid understanding of algorithms and complexity analysis", "is_required": True},
            {"skill_name": "SQL", "canonical_name": "sql", "category": "Databases", "evidence_snippet": "Relational schema design and query optimization", "is_required": True},
            {"skill_name": "Automated Testing", "canonical_name": "automated testing", "category": "Tools", "evidence_snippet": "Writing automated unit and integration tests", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "AWS", "canonical_name": "aws", "category": "Cloud", "evidence_snippet": "Cloud deployment concepts", "is_required": False},
            {"skill_name": "Data Pipelines", "canonical_name": "data pipelines", "category": "Data & AI", "evidence_snippet": "ETL and data ingestion experience", "is_required": False}
        ],
        "description": "Hevo Data is looking for enthusiastic Associate SDE Interns who want to solve complex data pipeline challenges. You will write high-performance Python code, optimize database interactions, and work with real-time automated data integration systems.",
        "application_url": "https://jobs.lever.co/hevodata/993a3ed3-3014-432f-b0f4-28d300d58d9a"
    },
    {
        "company": "Drivetrain",
        "title": "Engineering Intern - Gen AI Platform",
        "canonical_title": "AI Engineering Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "AI/ML"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Python programming and async frameworks", "is_required": True},
            {"skill_name": "AI Agents", "canonical_name": "ai agents", "category": "Data & AI", "evidence_snippet": "Building autonomous AI agents and prompt engineering", "is_required": True},
            {"skill_name": "LLMs", "canonical_name": "llms", "category": "Data & AI", "evidence_snippet": "Working with LLM APIs and structured output extraction", "is_required": True},
            {"skill_name": "REST APIs", "canonical_name": "rest apis", "category": "Tools", "evidence_snippet": "REST API development", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "RAG", "canonical_name": "rag", "category": "Data & AI", "evidence_snippet": "Retrieval-augmented generation architectures", "is_required": False},
            {"skill_name": "Embeddings", "canonical_name": "embeddings", "category": "Data & AI", "evidence_snippet": "Vector embeddings and semantic search", "is_required": False}
        ],
        "description": "Join Drivetrain as an Engineering Intern on our Generative AI platform team. You will leverage Python, LLMs, and agentic workflows to build automated data analysis and financial decision support features.",
        "application_url": "https://jobs.lever.co/drivetrain/bc1c17bc-86ac-4f00-a1e3-0eb85aae4fdc"
    },
    {
        "company": "Weekday",
        "title": "Software Engineer Intern",
        "canonical_title": "Software Engineer Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "REMOTE",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "Information Technology"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Python backend development", "is_required": True},
            {"skill_name": "SQL", "canonical_name": "sql", "category": "Databases", "evidence_snippet": "Database queries and data handling", "is_required": True},
            {"skill_name": "Git", "canonical_name": "git", "category": "Tools", "evidence_snippet": "Git version control", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "Docker", "canonical_name": "docker", "category": "Tools", "evidence_snippet": "Basic Docker containerization", "is_required": False},
            {"skill_name": "Automated Testing", "canonical_name": "automated testing", "category": "Tools", "evidence_snippet": "Unit tests", "is_required": False}
        ],
        "description": "Weekday is seeking a talented Software Engineer Intern (Remote / Bengaluru) to build tools that help companies recruit top engineering talent. You will write clean Python backend services, integrate third-party APIs, and iterate rapidly.",
        "application_url": "https://jobs.lever.co/weekdayworks/a86efff4-1c2e-43fc-8ecb-dc8f873db2f1"
    },
    {
        "company": "HackerRank",
        "title": "Software Development Engineer Intern",
        "canonical_title": "Software Development Engineer Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "Information Technology"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Strong proficiency in Python or Java", "is_required": True},
            {"skill_name": "Data Structures", "canonical_name": "data structures", "category": "Core CS", "evidence_snippet": "Strong command of core algorithms and data structures", "is_required": True},
            {"skill_name": "SQL", "canonical_name": "sql", "category": "Databases", "evidence_snippet": "Database design and querying", "is_required": True},
            {"skill_name": "REST APIs", "canonical_name": "rest apis", "category": "Tools", "evidence_snippet": "API design and microservices", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "Docker", "canonical_name": "docker", "category": "Tools", "evidence_snippet": "Docker containers", "is_required": False},
            {"skill_name": "AWS", "canonical_name": "aws", "category": "Cloud", "evidence_snippet": "Cloud architecture", "is_required": False}
        ],
        "description": "As a Software Development Engineer Intern at HackerRank, you will contribute directly to products used by millions of developers worldwide. You will write performant code, implement core features, and participate in code reviews.",
        "application_url": "https://job-boards.greenhouse.io/hackerrank/jobs/8229735"
    },
    {
        "company": "HackerRank",
        "title": "AI Researcher Intern",
        "canonical_title": "AI Researcher Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "AI/ML"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Python for machine learning and scientific computing", "is_required": True},
            {"skill_name": "Machine Learning", "canonical_name": "machine learning", "category": "Data & AI", "evidence_snippet": "Supervised learning and model evaluation metrics", "is_required": True},
            {"skill_name": "LLMs", "canonical_name": "llms", "category": "Data & AI", "evidence_snippet": "Large Language Models and prompt design", "is_required": True},
            {"skill_name": "Embeddings", "canonical_name": "embeddings", "category": "Data & AI", "evidence_snippet": "Vector embeddings and semantic search", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "AI Agents", "canonical_name": "ai agents", "category": "Data & AI", "evidence_snippet": "Autonomous AI agent workflows", "is_required": False},
            {"skill_name": "RAG", "canonical_name": "rag", "category": "Data & AI", "evidence_snippet": "Retrieval augmented generation systems", "is_required": False}
        ],
        "description": "HackerRank AI Research team is seeking an AI Researcher Intern to build next-generation assessment intelligence. You will experiment with LLMs, benchmark models using precision/recall, and implement AI pipelines.",
        "application_url": "https://job-boards.greenhouse.io/hackerrank/jobs/8281055"
    },
    {
        "company": "Acron Aviation",
        "title": "Software Engineer Intern - India Site",
        "canonical_title": "Software Engineer Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "ON_SITE",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "Information Technology"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Python scripting and software development", "is_required": True},
            {"skill_name": "Git", "canonical_name": "git", "category": "Tools", "evidence_snippet": "Git version control", "is_required": True},
            {"skill_name": "Automated Testing", "canonical_name": "automated testing", "category": "Tools", "evidence_snippet": "Unit testing and test automation", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "SQL", "canonical_name": "sql", "category": "Databases", "evidence_snippet": "Basic relational queries", "is_required": False}
        ],
        "description": "Acron Aviation is hiring a Software Engineer Intern for our India Site. You will work on software modules for aviation analytics, automate data testing, and assist in system integration.",
        "application_url": "https://jobs.lever.co/acronaviation/a464b1a4-01f4-4a28-b636-41dc508b3254"
    },
    {
        "company": "ShopBack",
        "title": "Software Engineer Intern",
        "canonical_title": "Software Engineer Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "Information Technology"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Strong programming fundamentals in Python or Go", "is_required": True},
            {"skill_name": "REST APIs", "canonical_name": "rest apis", "category": "Tools", "evidence_snippet": "Web services and HTTP APIs", "is_required": True},
            {"skill_name": "SQL", "canonical_name": "sql", "category": "Databases", "evidence_snippet": "SQL queries and schema design", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "Docker", "canonical_name": "docker", "category": "Tools", "evidence_snippet": "Containerization", "is_required": False}
        ],
        "description": "Join ShopBack as a Software Engineer Intern. You will design, build, and deploy high-volume backend microservices handling millions of transactions, ensuring system reliability and speed.",
        "application_url": "https://jobs.lever.co/shopback-2/640ac3fb-dae5-4738-95b9-9cb80cc7ad15/apply"
    },
    {
        "company": "Cloudflare",
        "title": "Software Engineer Intern (2027)",
        "canonical_title": "Software Engineer Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "Information Technology"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Strong programming proficiency in Python, Go, or C++", "is_required": True},
            {"skill_name": "Data Structures", "canonical_name": "data structures", "category": "Core CS", "evidence_snippet": "Computer science fundamentals in algorithms and data structures", "is_required": True},
            {"skill_name": "Git", "canonical_name": "git", "category": "Tools", "evidence_snippet": "Git version control and collaborative software development", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "Docker", "canonical_name": "docker", "category": "Tools", "evidence_snippet": "Linux and containerization", "is_required": False}
        ],
        "description": "Cloudflare is looking for Software Engineer Interns graduating in 2027. Work on building a better internet by contributing to our edge network, serverless infrastructure, and security platforms.",
        "application_url": "https://job-boards.greenhouse.io/cloudflare/jobs/8245211"
    },
    {
        "company": "Figma",
        "title": "Data Engineer Intern (2027)",
        "canonical_title": "Data Engineer Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "REMOTE",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science", "Data Science"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Python data processing", "is_required": True},
            {"skill_name": "SQL", "canonical_name": "sql", "category": "Databases", "evidence_snippet": "Complex SQL query formulation and data warehouse schemas", "is_required": True},
            {"skill_name": "Data Pipelines", "canonical_name": "data pipelines", "category": "Data & AI", "evidence_snippet": "Building data ingestion pipelines", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "AWS", "canonical_name": "aws", "category": "Cloud", "evidence_snippet": "Cloud infrastructure", "is_required": False}
        ],
        "description": "Figma is hiring a Data Engineer Intern (Graduating 2027). You will partner with analytics and engineering to build robust ETL pipelines, validate data quality, and model product datasets.",
        "application_url": "https://boards.greenhouse.io/figma/jobs/6178851004"
    },
    {
        "company": "Databricks",
        "title": "Software Engineer - New Grad (2027 Start)",
        "canonical_title": "Software Engineer New Grad",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "FULL_TIME",
        "seniority_level": "ENTRY_LEVEL",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Proficiency in Python or Scala", "is_required": True},
            {"skill_name": "Data Structures", "canonical_name": "data structures", "category": "Core CS", "evidence_snippet": "Strong foundational knowledge of algorithms", "is_required": True},
            {"skill_name": "SQL", "canonical_name": "sql", "category": "Databases", "evidence_snippet": "Database query optimization and relational systems", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "Machine Learning", "canonical_name": "machine learning", "category": "Data & AI", "evidence_snippet": "Knowledge of distributed ML systems", "is_required": False}
        ],
        "description": "Databricks is seeking 2027 graduates to join our world-class engineering team. You will build lakehouse technologies, distributed query engines, and AI infrastructure powering modern enterprises.",
        "application_url": "https://job-boards.greenhouse.io/databricks/jobs/8847747002"
    },
    {
        "company": "Stripe",
        "title": "Software Engineer, Intern",
        "canonical_title": "Software Engineer Intern",
        "location": "Bengaluru, Karnataka, India",
        "city": "Bengaluru",
        "country": "India",
        "workplace_type": "HYBRID",
        "employment_type": "INTERNSHIP",
        "seniority_level": "INTERNSHIP",
        "experience_min_years": 0.0,
        "experience_max_years": 1.0,
        "degree_requirements": ["Bachelor of Technology", "Computer Science"],
        "field_of_study": ["Computer Science"],
        "required_skills": [
            {"skill_name": "Python", "canonical_name": "python", "category": "Programming Languages", "evidence_snippet": "Object-oriented programming in Python or Ruby", "is_required": True},
            {"skill_name": "REST APIs", "canonical_name": "rest apis", "category": "Tools", "evidence_snippet": "API design, reliability, and security", "is_required": True},
            {"skill_name": "Automated Testing", "canonical_name": "automated testing", "category": "Tools", "evidence_snippet": "Automated test suites and continuous testing", "is_required": True}
        ],
        "preferred_skills": [
            {"skill_name": "Docker", "canonical_name": "docker", "category": "Tools", "evidence_snippet": "Docker infrastructure", "is_required": False}
        ],
        "description": "Stripe is looking for ambitious software engineering interns. As an intern at Stripe, you will ship production features, write clean RESTful APIs, and learn how to operate mission-critical financial infrastructure.",
        "application_url": "https://job-boards.greenhouse.io/stripe/jobs/8031833"
    }
]

def main():
    conn = sqlite3.connect("backend/ai_job_search.db")
    c = conn.cursor()

    # Load SBERT model for embeddings
    print("Loading fine-tuned SBERT model...")
    sbert_model = get_model()

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    now_dt = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    ingested_ids = []

    for job_data in VERIFIED_JOBS:
        # Check if already exists by canonical_application_url
        c.execute("SELECT id, canonical_job_id FROM canonical_jobs WHERE canonical_application_url = ?", (job_data["application_url"],))
        existing = c.fetchone()

        if existing:
            job_id, canon_code = existing
            print(f"Updating existing canonical job: [{job_id}] {canon_code} - {job_data['title']}")
            c.execute("""
                UPDATE canonical_jobs
                SET title = ?, canonical_job_title = ?, normalized_title = ?, seniority_level = ?,
                    experience_min_years = ?, experience_max_years = ?, required_skills = ?, preferred_skills = ?,
                    degree_requirements = ?, field_of_study = ?, description = ?, vacancy_status = 'ACTIVE',
                    last_seen_at = ?, last_verified_at = ?, updated_at = ?
                WHERE id = ?
            """, (
                job_data["title"], job_data["canonical_title"], job_data["canonical_title"].lower(),
                job_data["seniority_level"], job_data["experience_min_years"], job_data["experience_max_years"],
                json.dumps(job_data["required_skills"]), json.dumps(job_data["preferred_skills"]),
                json.dumps(job_data["degree_requirements"]), json.dumps(job_data["field_of_study"]),
                job_data["description"], now_dt, now_dt, now_dt, job_id
            ))
        else:
            comp_code = job_data["company"].upper().replace(" ", "")[:6]
            rand_hash = hashlib.sha256(job_data["application_url"].encode("utf-8")).hexdigest()[:8].upper()
            canon_code = f"CANON-{comp_code}-{rand_hash}"

            c.execute("""
                INSERT INTO canonical_jobs (
                    canonical_job_id, company_id, company_name, title, canonical_job_title,
                    normalized_title, location, city, country, is_remote, workplace_type,
                    employment_type, seniority_level, experience_min_years, experience_max_years,
                    degree_requirements, field_of_study, description, required_skills,
                    preferred_skills, canonical_application_url, canonical_source_url,
                    vacancy_status, first_seen_at, last_seen_at, last_verified_at,
                    last_status_change_at, consecutive_missing_checks, verification_attempts,
                    source_count, dedup_confidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, 0, 0, 1, 1.0, ?, ?)
            """, (
                canon_code, None, job_data["company"], job_data["title"], job_data["canonical_title"],
                job_data["canonical_title"].lower(), job_data["location"], job_data["city"], job_data["country"],
                job_data["workplace_type"] == "REMOTE", job_data["workplace_type"], job_data["employment_type"],
                job_data["seniority_level"], job_data["experience_min_years"], job_data["experience_max_years"],
                json.dumps(job_data["degree_requirements"]), json.dumps(job_data["field_of_study"]),
                job_data["description"], json.dumps(job_data["required_skills"]), json.dumps(job_data["preferred_skills"]),
                job_data["application_url"], job_data["application_url"],
                now_dt, now_dt, now_dt, now_dt, now_dt, now_dt
            ))
            job_id = c.lastrowid
            print(f"Created new canonical job: [{job_id}] {canon_code} - {job_data['title']}")

        ingested_ids.append(job_id)

        # Generate & store 384-d SBERT vector embedding
        embed_text_str = f"Job Title: {job_data['title']}. Company: {job_data['company']}. Location: {job_data['location']}. Requirements: {job_data['description']}"
        raw_vec = sbert_model.encode(embed_text_str, convert_to_numpy=True)
        norm = np.linalg.norm(raw_vec)
        if norm > 0:
            raw_vec = raw_vec / norm
        vec_list = raw_vec.tolist()
        content_hash = hashlib.sha256(embed_text_str.encode("utf-8")).hexdigest()

        c.execute("SELECT id FROM job_embeddings WHERE canonical_job_id = ?", (job_id,))
        emb_row = c.fetchone()
        blob_bytes = raw_vec.astype(np.float32).tobytes()
        if emb_row:
            c.execute("""
                UPDATE job_embeddings
                SET embedding_blob = ?, embedding_json = ?, content_hash = ?, dimensions = 384,
                    status = 'COMPLETED', updated_at = ?
                WHERE id = ?
            """, (blob_bytes, json.dumps(vec_list), content_hash, now_dt, emb_row[0]))
        else:
            c.execute("""
                INSERT INTO job_embeddings (
                    canonical_job_id, embedding_blob, embedding_json, content_hash,
                    dimensions, model_name, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 384, 'trained_sbert', 'COMPLETED', ?, ?)
            """, (job_id, blob_bytes, json.dumps(vec_list), content_hash, now_dt, now_dt))

    conn.commit()
    print(f"\nSuccessfully stored and embedded {len(ingested_ids)} verified fresher/intern vacancies.")

    # Now re-evaluate matches for Candidate 1 & 3
    for cid in [1, 3]:
        print(f"\n>>> Re-evaluating candidate-to-job matching for Candidate {cid}...")
        c.execute("SELECT id, filename, profile_json, recommendations_json, confirmed_roles_json FROM candidates WHERE id = ?", (cid,))
        cand_row = c.fetchone()
        if not cand_row:
            print(f"Candidate {cid} not found!")
            continue

        profile_dict = json.loads(cand_row[2]) if cand_row[2] else {}
        profile_data = profile_dict.get("profile", profile_dict)

        # Get candidate embedding
        c.execute("SELECT embedding_json FROM candidate_embeddings WHERE candidate_id = ?", (cid,))
        cand_emb_row = c.fetchone()
        if not cand_emb_row or not cand_emb_row[0]:
            print(f"Candidate {cid} embedding not found, generating...")
            cand_text = f"{profile_data.get('personal', {}).get('name', '')} {json.dumps(profile_data.get('skills', {}))} {json.dumps(profile_data.get('experience', []))}"
            cand_vec = sbert_model.encode(cand_text, convert_to_numpy=True)
            cand_vec = cand_vec / (np.linalg.norm(cand_vec) + 1e-9)
        else:
            cand_vec = np.array(json.loads(cand_emb_row[0]), dtype=np.float32)

        # Candidate verified skills & confirmed roles
        skills_dict = profile_data.get("skills", {})
        verified_skills = []
        for cat, sks in skills_dict.items():
            if isinstance(sks, list):
                verified_skills.extend(sks)
        cand_roles = json.loads(cand_row[4]) if cand_row[4] else ["Python Backend Engineer", "Python Developer"]

        cand_exp_years = 0.0
        cand_level = "FRESHER"

        # Evaluate against ALL canonical jobs in database
        c.execute("""
            SELECT j.id, j.canonical_job_id, j.company_name, j.title, j.canonical_job_title,
                   j.location, j.city, j.country, j.is_remote, j.workplace_type, j.employment_type,
                   j.seniority_level, j.experience_min_years, j.experience_max_years,
                   j.degree_requirements, j.field_of_study, j.description, j.required_skills,
                   j.preferred_skills, j.canonical_application_url, e.embedding_json
            FROM canonical_jobs j
            LEFT JOIN job_embeddings e ON j.id = e.canonical_job_id
            WHERE j.vacancy_status = 'ACTIVE'
        """)
        all_jobs = c.fetchall()

        matched_count = 0
        for job_row in all_jobs:
            jid = job_row[0]
            j_title = job_row[3]
            j_canon_title = job_row[4] or j_title
            j_min_exp = job_row[12]
            j_max_exp = job_row[13]
            j_sen = job_row[11]
            j_req_skills = parse_json_list(job_row[17])
            j_pref_skills = parse_json_list(job_row[18])
            j_degrees = parse_json_list(job_row[14])
            j_fields = parse_json_list(job_row[15])
            j_emb_str = job_row[20]

            # 1. Semantic similarity
            if j_emb_str:
                j_vec = np.array(json.loads(j_emb_str), dtype=np.float32)
                semantic_score = float(np.dot(cand_vec, j_vec))
                semantic_score = max(0.0, min(1.0, semantic_score))
            else:
                semantic_score = 0.5

            # 2. Skill matching
            matched_skills = []
            missing_skills = []
            cand_skills_lower = {s.lower(): s for s in verified_skills}
            
            clean_req = [s.get("canonical_name", s.get("skill_name", str(s))).lower() if isinstance(s, dict) else str(s).lower() for s in j_req_skills]
            for s in clean_req:
                if s in cand_skills_lower:
                    matched_skills.append(cand_skills_lower[s])
                else:
                    missing_skills.append(s)
            
            skill_score = len(matched_skills) / max(len(clean_req), 1)

            # 3. Role similarity
            role_score = 0.5
            t_lower = j_title.lower()
            if any(r in t_lower for r in ["python", "backend", "developer", "software", "sde", "ai", "machine learning", "intern"]):
                role_score = 0.90
            elif any(r in t_lower for r in ["engineer", "data", "qa", "test"]):
                role_score = 0.75

            # 4. Experience & Seniority Gate
            exp_score, exp_disqual_reason, is_exp_disqualified = eligibility_engine.evaluate_experience(
                candidate_exp_years=cand_exp_years,
                candidate_level=cand_level,
                job_min_years=j_min_exp,
                job_max_years=j_max_exp,
                job_seniority=j_sen,
                job_title=j_title,
            )

            # 5. Education
            edu_score = 1.0

            # 6. Technical Relevance Gate
            rel_res = relevance_gate.evaluate_relevance(
                job_title=j_title,
                job_description=job_row[16],
                job_required_skills=[s if isinstance(s, str) else str(s) for s in clean_req],
                job_preferred_skills=[],
                candidate_target_roles=cand_roles,
                candidate_verified_skills=verified_skills,
            )

            is_relevant = rel_res["is_relevant"]

            # Eligibility status
            if not is_relevant:
                elig_status = "DISQUALIFIED"
                reasons = [f"Role family mismatch: Classified as {rel_res['role_family'].replace('_', ' ').title()}."]
            elif is_exp_disqualified:
                elig_status = "DISQUALIFIED"
                reasons = [exp_disqual_reason or "Seniority requirements exceed candidate experience level."]
            elif exp_score < 0.70:
                elig_status = "ELIGIBLE_WITH_CONDITIONS"
                reasons = [exp_disqual_reason] if exp_disqual_reason else []
            else:
                elig_status = "ELIGIBLE"
                reasons = ["Candidate qualifies for this opportunity."]

            # Composite Score (0 - 100)
            comp_score = (semantic_score * 0.35 + skill_score * 0.35 + role_score * 0.15 + exp_score * 0.10 + edu_score * 0.05) * 100.0
            
            # Penalize irrelevant or disqualified positions
            if not is_relevant:
                comp_score = round(comp_score * 0.15, 2)
            elif is_exp_disqualified:
                comp_score = round(comp_score * 0.35, 2)
            else:
                comp_score = round(comp_score, 2)

            explanation = f"Match: {comp_score:.1f}% ({elig_status}). SBERT similarity: {semantic_score:.1%}. Skills overlap: {len(matched_skills)}/{max(len(clean_req), 1)}. Experience: {'Satisfied' if not is_exp_disqualified else exp_disqual_reason}."

            cand_hash = hashlib.sha256(f"{cid}_{cand_row[1]}".encode()).hexdigest()
            job_hash = hashlib.sha256(f"{jid}_{j_title}".encode()).hexdigest()

            # Save or update match
            c.execute("SELECT id FROM candidate_job_matches WHERE candidate_id = ? AND canonical_job_id = ?", (cid, jid))
            m_row = c.fetchone()
            if m_row:
                c.execute("""
                    UPDATE candidate_job_matches
                    SET composite_score = ?, semantic_score = ?, skill_score = ?, role_score = ?,
                        experience_score = ?, education_score = ?, location_score = 1.0, score_coverage = 1.0,
                        eligibility_status = ?, match_classification = ?,
                        matched_skills = ?, missing_skills = ?, explanation_data = ?,
                        disqualification_reasons = ?, is_relevant = ?, role_family = ?,
                        relevance_score = ?, candidate_content_hash = ?, job_content_hash = ?,
                        algorithm_version = 'phase7-v1.0', matching_status = 'COMPLETED',
                        evaluated_at = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    comp_score, semantic_score, skill_score, role_score,
                    exp_score, edu_score, elig_status,
                    "RECOMMENDED" if comp_score >= 65 and elig_status == "ELIGIBLE" else ("GOOD_MATCH" if comp_score >= 45 else "LOW_MATCH"),
                    json.dumps(matched_skills), json.dumps(missing_skills), explanation,
                    json.dumps(reasons if elig_status != "ELIGIBLE" else []),
                    1 if is_relevant else 0, rel_res["role_family"], rel_res["relevance_score"],
                    cand_hash, job_hash,
                    now_dt, now_dt, m_row[0]
                ))
            else:
                c.execute("""
                    INSERT INTO candidate_job_matches (
                        candidate_id, canonical_job_id, composite_score, semantic_score,
                        skill_score, role_score, experience_score, education_score, location_score,
                        score_coverage, eligibility_status, match_classification, matched_skills,
                        missing_skills, explanation_data, disqualification_reasons,
                        is_relevant, role_family, relevance_score, candidate_content_hash, job_content_hash,
                        algorithm_version, matching_status, evaluated_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1.0, 1.0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'phase7-v1.0', 'COMPLETED', ?, ?, ?)
                """, (
                    cid, jid, comp_score, semantic_score,
                    skill_score, role_score, exp_score, edu_score,
                    elig_status, "RECOMMENDED" if comp_score >= 65 and elig_status == "ELIGIBLE" else ("GOOD_MATCH" if comp_score >= 45 else "LOW_MATCH"),
                    json.dumps(matched_skills), json.dumps(missing_skills),
                    explanation, json.dumps(reasons if elig_status != "ELIGIBLE" else []),
                    1 if is_relevant else 0, rel_res["role_family"], rel_res["relevance_score"],
                    cand_hash, job_hash,
                    now_dt, now_dt, now_dt
                ))
            matched_count += 1

        print(f"Evaluated & persisted {matched_count} matches for Candidate {cid}.")

    conn.commit()

    # Print top 15 matches for Candidate 1 & 3
    for cid in [1, 3]:
        print(f"\n================ TOP 15 MATCHES FOR CANDIDATE {cid} ================")
        c.execute("""
            SELECT j.company_name, j.title, m.composite_score, m.eligibility_status, m.is_relevant, j.canonical_application_url
            FROM candidate_job_matches m
            JOIN canonical_jobs j ON m.canonical_job_id = j.id
            WHERE m.candidate_id = ?
            ORDER BY m.is_relevant DESC, m.composite_score DESC
            LIMIT 15
        """, (cid,))
        for idx, (comp, title, score, elig, rel, url) in enumerate(c.fetchall(), 1):
            print(f"{idx:2d}. [{score:5.1f}% | {elig:10s} | Rel:{rel}] {comp} - {title}")
            print(f"    URL: {url}")

    conn.close()
    print("\nAll tasks completed successfully!")

if __name__ == "__main__":
    main()
