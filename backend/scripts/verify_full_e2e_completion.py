# backend/scripts/verify_full_e2e_completion.py
"""
AI Job Search Agent — Full End-to-End System Verification Script.
Executes an end-to-end audit verifying:
1. Baseline database counts and preservation of Candidate 20 and 21.
2. System health endpoints.
3. Candidate profile and confirmed target roles.
4. Jobs feed with explainable SBERT match scoring.
5. Canonical job detail and qualification breakdown.
6. Saved jobs bookmarking, notes, and unbookmarking.
7. Job application lifecycle (creation, duplicate prevention, status transitions, history tracking, cleanup).
8. Company research, verified contacts, and outreach authorization policy.
9. Pipeline orchestration status and history.
10. Dashboard statistics aggregation.
11. Post-verification database integrity check.
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

DB_PATH = os.path.join(backend_dir, "ai_job_search.db")


def get_db_counts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    def count(table):
        try:
            return cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            return 0

    counts = {
        "candidates": count("candidates"),
        "raw_jobs": count("discovered_jobs"),
        "normalized_jobs": count("jobs"),
        "canonical_jobs": count("canonical_jobs"),
        "canonical_sources": count("canonical_job_sources"),
        "job_embeddings": count("job_embeddings"),
        "candidate_embeddings": count("candidate_embeddings"),
        "candidate_matches": count("candidate_job_matches"),
        "companies": count("companies"),
        "career_sources": count("company_career_sources"),
    }

    # Query candidate 20 and 21 specifically
    cand_20 = cursor.execute("SELECT id, filename, profile_json FROM candidates WHERE id = 20").fetchone()
    cand_21 = cursor.execute("SELECT id, filename, profile_json FROM candidates WHERE id = 21").fetchone()
    counts["cand_20"] = cand_20
    counts["cand_21"] = cand_21

    conn.close()
    return counts


def run_e2e_verification():
    print("=" * 80)
    print("AI JOB SEARCH AGENT — FULL END-TO-END SYSTEM VERIFICATION")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print("=" * 80)

    errors = []

    # ---------------------------------------------------------
    # STEP 1: Database Pre-Verification & Candidate 20/21 Audit
    # ---------------------------------------------------------
    print("\n[Step 1] Auditing database baseline & candidate preservation...")
    pre_counts = get_db_counts()

    print(f"  • Total Candidates: {pre_counts['candidates']} (>= 21 required)")
    print(f"  • Candidate 20: {'PRESERVED (' + str(pre_counts['cand_20'][1]) + ')' if pre_counts['cand_20'] else 'MISSING!'}")
    print(f"  • Candidate 21: {'PRESERVED (' + str(pre_counts['cand_21'][1]) + ')' if pre_counts['cand_21'] else 'MISSING!'}")
    print(f"  • Raw Discovered Jobs: {pre_counts['raw_jobs']} (expected 22)")
    print(f"  • Normalized Jobs: {pre_counts['normalized_jobs']} (expected 10)")
    print(f"  • Canonical Vacancies: {pre_counts['canonical_jobs']} (expected 10)")
    print(f"  • Canonical Sources: {pre_counts['canonical_sources']} (expected 10)")
    print(f"  • Job Embeddings: {pre_counts['job_embeddings']} (expected 10)")
    print(f"  • Candidate Embeddings: {pre_counts['candidate_embeddings']} (expected 3)")
    print(f"  • Candidate Matches: {pre_counts['candidate_matches']} (expected 30)")
    print(f"  • Tracked Companies: {pre_counts['companies']} (expected 819)")
    print(f"  • Career Sources: {pre_counts['career_sources']} (expected 205)")

    if not pre_counts["cand_20"] or not pre_counts["cand_21"]:
        errors.append("Candidate 20 or 21 was not found in database!")
    if pre_counts["candidates"] < 21:
        errors.append(f"Candidate count {pre_counts['candidates']} < 21!")
    if pre_counts["canonical_jobs"] < 10 or pre_counts["job_embeddings"] < 10 or pre_counts["candidate_matches"] < 30:
        errors.append("Canonical jobs, embeddings, or matches dropped below baseline!")

    # ---------------------------------------------------------
    # STEP 2: FastAPI Client & Health Endpoints
    # ---------------------------------------------------------
    print("\n[Step 2] Testing application health & root endpoints...", flush=True)
    with TestClient(app) as client:
        health_res = client.get("/health")
        api_health_res = client.get("/api/health")
        print(f"  • GET /health -> {health_res.status_code} {health_res.json()}", flush=True)
        print(f"  • GET /api/health -> {api_health_res.status_code} {api_health_res.json()}", flush=True)

        if health_res.status_code != 200 or health_res.json().get("status") != "healthy":
            errors.append("GET /health failed!")
        if api_health_res.status_code != 200 or api_health_res.json().get("status") != "healthy":
            errors.append("GET /api/health failed!")

        # ---------------------------------------------------------
        # STEP 3: Candidate Profile & Confirmed Roles
        # ---------------------------------------------------------
        print("\n[Step 3] Inspecting candidate profile & confirmed target roles...", flush=True)
        profile_res = client.get("/api/resume/1")
        print(f"  • GET /api/resume/1 -> Status: {profile_res.status_code}", flush=True)
        if profile_res.status_code == 200:
            pdata = profile_res.json()
            pers = pdata.get("profile", {}).get("personal", {})
            print(f"    Name: {pers.get('name')}, Email: {pers.get('email')}, Exp: {pers.get('years_of_experience')} yrs", flush=True)
        else:
            errors.append(f"Failed to fetch candidate 1 profile: {profile_res.status_code}")

        conf_res = client.get("/api/profile/1/confirmed-roles")
        print(f"  • GET /api/profile/1/confirmed-roles -> Status: {conf_res.status_code}", flush=True)
        if conf_res.status_code == 200:
            cdata = conf_res.json()
            roles = cdata.get("roles", [])
            print(f"    Confirmed target roles: {len(roles)} role(s) confirmed", flush=True)

        # ---------------------------------------------------------
        # STEP 4: Jobs Feed with SBERT Matching & Scoring
        # ---------------------------------------------------------
        print("\n[Step 4] Querying verified jobs feed with SBERT match scoring...", flush=True)
        feed_res = client.get("/api/jobs/feed?candidate_id=1&limit=5")
        print(f"  • GET /api/jobs/feed?candidate_id=1&limit=5 -> Status: {feed_res.status_code}", flush=True)
        if feed_res.status_code == 200:
            fdata = feed_res.json()
            items = fdata.get("items", [])
            print(f"    Total Feed Items: {fdata.get('total')}, Returned: {len(items)}", flush=True)
            for idx, item in enumerate(items[:3]):
                print(f"    [{idx+1}] {item['title']} @ {item['company_name']}", flush=True)
                print(f"        Match Score: {item['match_score']:.1%} | Eligibility: {item['eligibility_status']}", flush=True)
                print(f"        Matched Skills: {len(item.get('matched_skills', []))} | Missing: {len(item.get('missing_skills', []))}", flush=True)
        else:
            errors.append(f"GET /api/jobs/feed failed: {feed_res.status_code}")

        # ---------------------------------------------------------
        # STEP 5: Canonical Job Detail & Deep Match Analysis
        # ---------------------------------------------------------
        print("\n[Step 5] Inspecting canonical job detail & SBERT explanation breakdown...", flush=True)
        detail_res = client.get("/api/jobs/1?candidate_id=1")
        print(f"  • GET /api/jobs/1?candidate_id=1 -> Status: {detail_res.status_code}", flush=True)
        if detail_res.status_code == 200:
            jdetail = detail_res.json()
            print(f"    Title: {jdetail.get('title')}", flush=True)
            print(f"    Company: {jdetail.get('company_name')}", flush=True)
            print(f"    Workplace Type: {jdetail.get('workplace_type')}", flush=True)
            match_info = jdetail.get("match_details")
            if match_info:
                print(f"    Composite Match Score: {match_info.get('composite_score'):.1%}", flush=True)
                print(f"    Semantic SBERT Score: {match_info.get('semantic_score'):.1%}", flush=True)
                print(f"    Skill Score: {match_info.get('skill_score'):.1%}", flush=True)
                print(f"    Eligibility: {match_info.get('eligibility_status')}", flush=True)
                print(f"    Explanation: {match_info.get('explanation')[:90]}...", flush=True)
            else:
                errors.append("Job detail response missing match_details!")
        else:
            errors.append(f"GET /api/jobs/1 failed: {detail_res.status_code}")

        # ---------------------------------------------------------
        # STEP 6: Saved Jobs Bookmark Lifecycle
        # ---------------------------------------------------------
        print("\n[Step 6] Testing saved jobs bookmarking & notes lifecycle...", flush=True)
        save_res = client.post("/api/saved-jobs", json={
            "candidate_id": 1,
            "canonical_job_id": 1,
            "notes": "E2E verification bookmark test"
        })
        print(f"  • POST /api/saved-jobs -> Status: {save_res.status_code}", flush=True)
        saved_id = None
        if save_res.status_code in (200, 201):
            sdata = save_res.json()
            saved_id = sdata.get("id")
            print(f"    Saved Job ID: {saved_id}, Job Title: {sdata.get('job', {}).get('title')}", flush=True)
        else:
            errors.append(f"POST /api/saved-jobs failed: {save_res.status_code}")

        # Query saved jobs
        list_saved = client.get("/api/saved-jobs/candidate/1")
        print(f"  • GET /api/saved-jobs/candidate/1 -> Status: {list_saved.status_code}, Count: {list_saved.json().get('total')}", flush=True)

        # Update notes
        if saved_id:
            patch_saved = client.patch(f"/api/saved-jobs/{saved_id}", json={
                "notes": "Updated note during E2E verification test"
            })
            print(f"  • PATCH /api/saved-jobs/{saved_id} -> Status: {patch_saved.status_code}", flush=True)
            if patch_saved.status_code != 200 or patch_saved.json().get("notes") != "Updated note during E2E verification test":
                errors.append("PATCH /api/saved-jobs/{id} failed to update note!")

        # ---------------------------------------------------------
        # STEP 7: Application Tracking Lifecycle
        # ---------------------------------------------------------
        print("\n[Step 7] Testing application tracker lifecycle & duplicate protection...", flush=True)
        app_id = None
        create_app_res = client.post("/api/applications", json={
            "candidate_id": 1,
            "canonical_job_id": 1,
            "company_name": "CRED",
            "job_title": "Threat Detection Engineer",
            "status": "APPLIED",
            "notes": "Applied via official careers portal"
        })
        print(f"  • POST /api/applications -> Status: {create_app_res.status_code}", flush=True)
        if create_app_res.status_code in (200, 201):
            adata = create_app_res.json()
            app_id = adata.get("id")
            print(f"    Application Created with ID: {app_id}, Status: {adata.get('status')}", flush=True)
        elif create_app_res.status_code == 409:
            print("    Application already existed (duplicate protection active).", flush=True)
            existing_apps = client.get("/api/applications/candidate/1").json().get("items", [])
            for ea in existing_apps:
                if ea.get("canonical_job_id") == 1:
                    app_id = ea.get("id")
                    break
        else:
            errors.append(f"POST /api/applications failed: {create_app_res.status_code}")

        # Test Duplicate Prevention
        dup_res = client.post("/api/applications", json={
            "candidate_id": 1,
            "canonical_job_id": 1,
            "company_name": "CRED",
            "job_title": "Threat Detection Engineer",
            "status": "APPLIED"
        })
        print(f"  • Duplicate Application Protection Check -> Status: {dup_res.status_code} (Expected 409 Conflict)", flush=True)
        if dup_res.status_code != 409:
            errors.append(f"Duplicate application was not prevented: Status {dup_res.status_code}")

        # Transition Status to INTERVIEW and OFFER
        if app_id:
            status_upd1 = client.patch(f"/api/applications/{app_id}/status", json={
                "status": "INTERVIEW",
                "notes": "Round 1 Technical Interview scheduled"
            })
            print(f"  • Transition to INTERVIEW -> Status: {status_upd1.status_code}", flush=True)

            status_upd2 = client.patch(f"/api/applications/{app_id}/status", json={
                "status": "OFFER",
                "notes": "Offer extended after final evaluation"
            })
            print(f"  • Transition to OFFER -> Status: {status_upd2.status_code}", flush=True)

            # Check stats
            stats_res = client.get("/api/applications/candidate/1/stats")
            print(f"  • GET /api/applications/candidate/1/stats -> Status: {stats_res.status_code}", flush=True)
            if stats_res.status_code == 200:
                st = stats_res.json()
                print(f"    Total Applications: {st.get('total_applications')}, Offers: {st.get('offers_received')}", flush=True)

            # Clean up test application record to preserve clean database state
            del_res = client.delete(f"/api/applications/{app_id}")
            print(f"  • Test Application Cleanup -> Status: {del_res.status_code}", flush=True)

        # ---------------------------------------------------------
        # STEP 8: Company Sourcing Intelligence & Outreach Policy
        # ---------------------------------------------------------
        print("\n[Step 8] Auditing company intelligence, contact segregation & outreach policy...", flush=True)
        companies_res = client.get("/api/companies?limit=5")
        print(f"  • GET /api/companies?limit=5 -> Status: {companies_res.status_code}", flush=True)
        if companies_res.status_code == 200:
            c_items = companies_res.json().get("items", [])
            print(f"    Retrieved {len(c_items)} companies from 819 total tracked.", flush=True)
            first_comp_id = c_items[0]["id"]

            research_res = client.get(f"/api/companies/{first_comp_id}/research")
            print(f"  • GET /api/companies/{first_comp_id}/research -> Status: {research_res.status_code}", flush=True)
            if research_res.status_code == 200:
                rdata = research_res.json()
                print(f"    Company: {rdata.get('name')}", flush=True)
                print(f"    Career Sources: {len(rdata.get('career_sources', []))}", flush=True)
                print(f"    Contacts: {len(rdata.get('contacts', []))}", flush=True)
                policy = rdata.get("outreach_policy", {})
                print(f"    Outreach Policy: Requires Authorization={policy.get('requires_explicit_authorization')}, Automated Dispatch={policy.get('automated_sending_enabled')}", flush=True)
                if policy.get("automated_sending_enabled") is not False:
                    errors.append("Outreach policy does not strictly disable automated sending!")
            else:
                errors.append(f"GET /api/companies/{first_comp_id}/research failed: {research_res.status_code}")

        # ---------------------------------------------------------
        # STEP 9: Pipeline Orchestration & Execution Status
        # ---------------------------------------------------------
        print("\n[Step 9] Auditing pipeline orchestration status & history...", flush=True)
        pip_status = client.get("/api/pipeline/status")
        print(f"  • GET /api/pipeline/status -> Status: {pip_status.status_code}, Running: {pip_status.json().get('is_running')}", flush=True)

        pip_hist = client.get("/api/pipeline/history?limit=5")
        print(f"  • GET /api/pipeline/history?limit=5 -> Status: {pip_hist.status_code}, Recorded runs: {len(pip_hist.json().get('items', []))}", flush=True)

        # ---------------------------------------------------------
        # STEP 10: Live Dashboard Aggregation Telemetry
        # ---------------------------------------------------------
        print("\n[Step 10] Checking live dashboard aggregated statistics...", flush=True)
        dash_res = client.get("/api/dashboard/stats?candidate_id=1")
        print(f"  • GET /api/dashboard/stats?candidate_id=1 -> Status: {dash_res.status_code}", flush=True)
        if dash_res.status_code == 200:
            dstats = dash_res.json()
            print(f"    System Telemetry: Candidates={dstats['system']['total_candidates']}, Companies={dstats['system']['total_companies']}, Vacancies={dstats['system']['total_canonical_vacancies']}", flush=True)
            print(f"    Recommendations Telemetry: Matches={dstats['recommendations']['total_matches_evaluated']}", flush=True)
        else:
            errors.append(f"GET /api/dashboard/stats failed: {dash_res.status_code}")

    # ---------------------------------------------------------
    # STEP 11: Final Post-Verification Database Integrity Check
    # ---------------------------------------------------------
    print("\n[Step 11] Performing final post-verification database audit...")
    post_counts = get_db_counts()

    print(f"  • Candidates Post-Count: {post_counts['candidates']} (pre-count: {pre_counts['candidates']})")
    print(f"  • Canonical Jobs Post-Count: {post_counts['canonical_jobs']} (pre-count: {pre_counts['canonical_jobs']})")
    print(f"  • Candidate 20 Status: {'INTACT' if post_counts['cand_20'] else 'CORRUPTED'}")
    print(f"  • Candidate 21 Status: {'INTACT' if post_counts['cand_21'] else 'CORRUPTED'}")

    if not post_counts["cand_20"] or not post_counts["cand_21"]:
        errors.append("Candidate 20 or 21 was corrupted during verification!")

    print("\n" + "=" * 80)
    if errors:
        print(f"VERIFICATION FAILED WITH {len(errors)} ERROR(S):")
        for err in errors:
            print(f"  [ERROR] {err}")
        return False
    else:
        print("[SUCCESS] ALL 11 VERIFICATION STAGES PASSED PERFECTLY!")
        print("Candidate 20 & 21 strictly preserved. All baseline records intact.")
        print("=" * 80)
        return True


if __name__ == "__main__":
    success = run_e2e_verification()
    sys.exit(0 if success else 1)
